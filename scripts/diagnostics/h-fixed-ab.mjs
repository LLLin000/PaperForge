// Temporary fixed-host A/B diagnostic harness for renderer-crash triage.
// Runs 4 cells (old/new x plugin-on/off) in ONE Windows job under a shared
// hash-pinned host (app 1.14.4 / installer 1.5.8 / Chrome120 driver).
//
// Usage (CI, from the worktree root):
//   node scripts/diagnostics/h-fixed-ab.mjs prefetch   # network allowed
//   node scripts/diagnostics/h-fixed-ab.mjs run-all     # egress-gated env
//   node scripts/diagnostics/h-fixed-ab.mjs cell <name> # one supervised cell
//   node scripts/diagnostics/h-fixed-ab.mjs report      # print summary verdicts
//   node scripts/diagnostics/h-fixed-ab.mjs verify      # node --check x3
//
// Commands:
//   prefetch  — npm ci (plugin), download + hash-pin host binaries AND the
//               whole installer tree, record launcher/service/wdio/driver +
//               runner versions, git-archive old/new sources, build both
//               bundles, compare archived lockfiles.
//               MUST run before any egress gate is applied.
//   run-all   — supervisor: applies the egress gate (dead proxy + Windows
//               firewall program block, owned ephemeral CI only), then runs
//               each cell as a SEPARATE child process with a bounded 120s
//               deadline, killing the owned tree on timeout. Continues
//               through all 4 cells; rechecks the host tree afterwards.
//   cell <name> — run one cell in THIS process (the run-all supervisor spawns
//               one child per cell; direct use is for local debugging).
//
// Design constraints (do not weaken without owner approval):
// - Baseline sources are fetched via `git archive <ref>` into scratch dirs;
//   the checked-out baseline tree is never modified.
// - Same lockfile/deps for both bundles: npm ci from the archived tree.
// - plugin-on/off is the ONLY delta between same-ref cells.
// - Fresh generated empty synthetic vault (Welcome.md) + fresh profile/HOME
//   per cell. Never a guessed repo fixture path.
// - data.json autoSyncEnabled:false is seeded in the STAGE plugin dir BEFORE
//   startWdioSession (the service copies it into the vault during setupVault)
//   AND in the source vault seed; propagation is verified against the ACTUAL
//   copied vault path from the service API. Seed failure is recorded, never
//   swallowed. No PAPERFORGE_POLL_* overrides, no pointer/backend, no creds.
// - Standalone session only (startWdioSession); never imports production
//   wdio.conf.mts (which mutates the published runtime + reads prod pointer).
// - No paid APIs, no keyring (fail backend), no progress-bar journeys.
// - Diagnostic success = complete evidence for all 4 cells, even when a
//   crash cell can never be "green". Verdicts live in result.json.
// - Parent owns verification, commit, push, and publication. This script
//   never merges, pushes, or opens PRs. No gates/formatters here.

import { execFileSync, spawn, spawnSync } from "node:child_process";
import {
  cpSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  openSync,
  closeSync,
  readFileSync,
  readdirSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { createHash } from "node:crypto";
import { release, tmpdir } from "node:os";
import { basename, dirname, join, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const PLUGIN_DIR = join(REPO_ROOT, "paperforge", "plugin");
const ARTIFACTS = join(REPO_ROOT, "h-fixed-ab-artifacts");
const PREFETCH_DIR = join(ARTIFACTS, "prefetch");
const CONF = await import("./h-fixed-ab.conf.mjs");

// Windows: absolute filesystem paths (D:\...) are not valid ESM specifiers.
// Every dynamic import of a filesystem path MUST go through fileUrl().
function fileUrl(p) {
  return pathToFileURL(p).href;
}
const SPEC_URL = fileUrl(join(dirname(fileURLToPath(import.meta.url)), "h-fixed-ab.spec.mjs"));

// Prefetch writes evidence incrementally so a failure mid-way still leaves
// receipts: prefetch-status.json (always) + summary.json (prefetch-blocked).
function writePrefetchStatus(partial) {
  mkdirSync(PREFETCH_DIR, { recursive: true });
  writeFileSync(join(PREFETCH_DIR, "prefetch-status.json"), JSON.stringify({ ...partial, ts: new Date().toISOString() }, null, 2));
  writeFileSync(
    join(ARTIFACTS, "summary.json"),
    JSON.stringify(
      {
        verdict: "prefetch-blocked",
        cells: [],
        prefetchStatus: partial,
        ts: new Date().toISOString(),
        notes: ["Prefetch failed before any cell ran; no product verdict is implied."],
      },
      null,
      2
    )
  );
}
const CELLS = [
  { cell: "old-on", ref: "old", refFull: CONF.OLD_REF, pluginOn: true },
  { cell: "old-off", ref: "old", refFull: CONF.OLD_REF, pluginOn: false },
  { cell: "new-on", ref: "new", refFull: CONF.NEW_REF, pluginOn: true },
  { cell: "new-off", ref: "new", refFull: CONF.NEW_REF, pluginOn: false },
];

const CRED_PREFIXES = [
  "PAPERFORGE_CREDENTIAL_",
  "PADDLEOCR_",
  "VECTOR_DB_",
  "OPENAI_",
  "OBSIDIAN_EMAIL",
  "OBSIDIAN_PASSWORD",
];

const WELCOME_MD =
  "# Welcome\n\n" +
  "Generated empty-vault seed note for the fixed-host A/B boot probe.\n" +
  "This vault is intentionally empty: one boot, one observation, no sync.\n";

function sha256File(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function sh(cmd, args, opts = {}) {
  return execFileSync(cmd, args, { encoding: "utf8", stdio: "pipe", ...opts }).trim();
}

// npm on Windows is npm.cmd: execFileSync("npm") fails without a shell.
// Run the resolved npm-cli.js under process.execPath instead. No shell,
// no string-built commands.
function resolveNpmCli() {
  if (process.env.npm_execpath && existsSync(process.env.npm_execpath)) {
    return process.env.npm_execpath;
  }
  const execDir = dirname(process.execPath);
  const candidates = [
    join(execDir, "node_modules", "npm", "bin", "npm-cli.js"),
    join(execDir, "..", "lib", "node_modules", "npm", "bin", "npm-cli.js"),
  ];
  for (const c of candidates) {
    if (existsSync(c)) return c;
  }
  throw new Error(
    `npm-cli.js not found (execPath=${process.execPath}, ` +
      `npm_execpath=${process.env.npm_execpath ?? "unset"}); refusing shell fallback`
  );
}

function npmSh(args, opts = {}) {
  return execFileSync(process.execPath, [resolveNpmCli(), ...args], {
    encoding: "utf8",
    stdio: "pipe",
    ...opts,
  }).trim();
}

function download(url, dest) {
  mkdirSync(dirname(dest), { recursive: true });
  const tryCurl = spawnSync(
    "curl",
    ["-fsSL", "--retry", "2", "--retry-all-errors", "-o", dest, url],
    { stdio: "inherit" }
  );
  if (tryCurl.status === 0) return;
  const res = spawnSync(
    "powershell",
    ["-NoProfile", "-Command", `Invoke-WebRequest -Uri '${url}' -OutFile '${dest}'`],
    { stdio: "inherit" }
  );
  if (res.status !== 0) throw new Error(`download failed: ${url}`);
}

// Hash an entire install tree (sorted relpath:hash manifest + digest).
function hashTree(root) {
  const files = [];
  const walk = (dir) => {
    for (const name of readdirSync(dir).sort()) {
      const full = join(dir, name);
      if (statSync(full).isDirectory()) walk(full);
      else files.push(full);
    }
  };
  walk(root);
  const entries = files.map((full) => ({
    rel: full.slice(root.length + 1),
    sha256: sha256File(full),
  }));
  const digest = createHash("sha256")
    .update(entries.map((e) => `${e.rel}:${e.sha256}`).join("\n"))
    .digest("hex");
  return { root, count: entries.length, entries, digest };
}

function installedVersion(pkg) {
  try {
    return readJson(join(PLUGIN_DIR, "node_modules", pkg, "package.json")).version ?? null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------- prefetch --

async function prefetch() {
  const status = { stage: "start", steps: {} };
  try {
    await prefetchInner(status);
    status.stage = "done";
    writePrefetchStatus({ ...status, ok: true });
  } catch (err) {
    status.stage = status.stage === "start" ? "failed" : status.stage;
    status.error = String(err?.stack ?? err);
    writePrefetchStatus({ ...status, ok: false });
    throw err;
  }
}

async function prefetchInner(status) {
  status.stage = "deps";
  mkdirSync(PREFETCH_DIR, { recursive: true });
  writePrefetchStatus({ ...status, ok: true, partial: true });
  console.log("[prefetch] installing harness deps (paperforge/plugin)...");
  npmSh(["ci", "--no-audit", "--no-fund"], { cwd: PLUGIN_DIR });
  status.steps.deps = true;

  // 2. Host binaries via the pinned service API (resolves to exact versions,
  //    asserts 1.14.4/1.5.8, then downloads installer + asar + chromedriver).
  console.log("[prefetch] resolving + downloading host binaries...");
  const launcherMod = await import("obsidian-launcher").catch(() =>
    import(fileUrl(join(PLUGIN_DIR, "node_modules", "obsidian-launcher", "dist", "index.js")))
  );
  // obsidian-launcher@3.2.0 exports the constructor as DEFAULT (a class),
  // NOT as a named ObsidianLauncher export (verified against installed
  // dist/index.js: keys ['default','minSupportedObsidianVersion']).
  const ObsidianLauncher = launcherMod.default ?? launcherMod.ObsidianLauncher;
  if (typeof ObsidianLauncher !== "function") {
    throw new Error(`obsidian-launcher has no constructor export (keys: ${Object.keys(launcherMod).join(",")})`);
  }
  const cacheDir = join(ARTIFACTS, ".obsidian-cache");
  const launcher = new ObsidianLauncher({ cacheDir });
  const [appVersion, installerVersion] = await launcher.resolveVersion(
    CONF.APP_VERSION,
    CONF.INSTALLER_VERSION
  );
  if (appVersion !== CONF.APP_VERSION || installerVersion !== CONF.INSTALLER_VERSION) {
    throw new Error(`host version mismatch: got ${appVersion}/${installerVersion}`);
  }
  const versionInfo = await launcher.getVersionInfo(appVersion);
  const installerInfo = await launcher.getInstallerInfo(installerVersion);
  const binaryPath = await launcher.downloadInstaller(installerVersion);
  const appPath = await launcher.downloadApp(appVersion);
  const driverPath = await launcher.downloadChromedriver(installerVersion);
  const installerTree = hashTree(dirname(binaryPath));
  let driverVersion = null;
  try {
    const out = spawnSync(driverPath, ["--version"], { encoding: "utf8", timeout: 15000 });
    driverVersion = String(out.stdout ?? "").trim().split("\n")[0] || null;
  } catch {
    driverVersion = null;
  }
  const pins = {
    appVersion,
    installerVersion,
    electron: installerInfo.electron ?? null,
    chrome: installerInfo.chrome ?? null,
    installerDigest: installerInfo.digest ?? null,
    binaryPath,
    binarySha256: sha256File(binaryPath),
    appPath,
    appSha256: sha256File(appPath),
    driverPath,
    driverSha256: sha256File(driverPath),
    installerTree,
  };
  if (!/^120\./.test(String(pins.chrome ?? ""))) {
    throw new Error(`installer chrome is not 120.x: ${pins.chrome}`);
  }
  const versions = {
    node: process.version,
    launcher: installedVersion("obsidian-launcher"),
    service: installedVersion("wdio-obsidian-service"),
    wdio: installedVersion("webdriverio"),
    electron: installerInfo.electron ?? null,
    chrome: installerInfo.chrome ?? null,
    driver: driverVersion,
    runnerImage: process.env.ImageOS ?? "unknown",
    osRelease: release(),
    platform: process.platform,
  };
  const missingVersions = Object.entries(versions)
    .filter(([, v]) => v == null)
    .map(([k]) => k);
  writeFileSync(join(PREFETCH_DIR, "host-pins.json"), JSON.stringify(pins, null, 2));
  writeFileSync(join(PREFETCH_DIR, "host-versions.json"), JSON.stringify(versions, null, 2));
  console.log(`[prefetch] host pinned: app=${appVersion} installer=${installerVersion} chrome=${pins.chrome}`);
  console.log(`[prefetch] installer tree: ${installerTree.count} files digest=${installerTree.digest.slice(0, 16)}...`);
  if (missingVersions.length > 0) {
    console.log(`[prefetch] NOTE unresolved versions recorded as null: ${missingVersions.join(",")}`);
  }
  status.steps.hostPins = true;
  status.stage = "bundles";
  writePrefetchStatus({ ...status, ok: true, partial: true });

  // 3. Old/new sources via git archive (baseline tree untouched) + bundle builds.
  //    Lockfiles are hashed and ACTUALLY compared, not just recorded.
  const lockHashes = {};
  for (const refFull of [CONF.OLD_REF, CONF.NEW_REF]) {
    const tag = refFull === CONF.OLD_REF ? "old" : "new";
    const srcDir = join(PREFETCH_DIR, `src-${tag}`);
    mkdirSync(srcDir, { recursive: true });
    console.log(`[prefetch] archiving ${tag} (${refFull.slice(0, 12)})...`);
    const head = sh("git", ["rev-parse", refFull], { cwd: REPO_ROOT });
    if (head !== refFull) throw new Error(`ref moved during prefetch: ${refFull} -> ${head}`);
    const tar = join(PREFETCH_DIR, `src-${tag}.tar`);
    // Portable: GNU tar on Windows treats a D:-absolute archive arg as a
    // remote (host D:) and BSD tar lacks --force-local, so pass both the
    // archive and the destination repo-relative with cwd=REPO_ROOT.
    sh("git", ["archive", refFull, "-o", relative(REPO_ROOT, tar)], { cwd: REPO_ROOT });
    sh("tar", ["-xf", relative(REPO_ROOT, tar), "-C", relative(REPO_ROOT, srcDir)], { cwd: REPO_ROOT });
    const tagPluginDir = join(srcDir, "paperforge", "plugin");
    console.log(`[prefetch] npm ci + build (${tag})...`);
    npmSh(["ci", "--no-audit", "--no-fund"], { cwd: tagPluginDir });
    npmSh(["run", "build"], { cwd: tagPluginDir });
    const mainJs = join(tagPluginDir, "main.js");
    const manifest = join(tagPluginDir, "manifest.json");
    const lockfile = join(tagPluginDir, "package-lock.json");
    lockHashes[tag] = existsSync(lockfile) ? sha256File(lockfile) : null;
    const rec = {
      ref: refFull,
      head,
      mainJsSha256: sha256File(mainJs),
      manifestSha256: sha256File(manifest),
      lockfileSha256: lockHashes[tag],
    };
    writeFileSync(join(PREFETCH_DIR, `bundle-${tag}.json`), JSON.stringify(rec, null, 2));
    console.log(`[prefetch] bundle-${tag}: main.js sha256=${rec.mainJsSha256.slice(0, 16)}...`);
    status.steps[`bundle-${tag}`] = true;
    writePrefetchStatus({ ...status, ok: true, partial: true });
  }
  const lockCompare = {
    old: lockHashes.old,
    new: lockHashes.new,
    match: lockHashes.old != null && lockHashes.old === lockHashes.new,
  };
  writeFileSync(join(PREFETCH_DIR, "lockfiles.json"), JSON.stringify(lockCompare, null, 2));
  console.log(`[prefetch] lockfiles match=${lockCompare.match}`);
  console.log("[prefetch] done.");
}

// ---------------------------------------------------------------- egress ---

function applyEgressGate() {
  // Dead proxy + loopback-only bypass. CDP talks to 127.0.0.1 chromedriver;
  // everything else fails fast instead of hanging. This is NOT the genuine
  // control: run-all additionally applies per-program Windows firewall
  // outbound blocks (owned ephemeral CI only). A path requiring WAN surfaces
  // as a boot failure here, which is itself signal, not a harness bug.
  for (const k of ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]) {
    process.env[k] = CONF.DEAD_PROXY;
  }
  process.env.NO_PROXY = "127.0.0.1,localhost";
  process.env.no_proxy = "127.0.0.1,localhost";
}

function scrubEnv() {
  // Fail-closed boot: no pointer, fail keyring backend, no credentials,
  // no PYTHONPATH/HOME leakage, no poll overrides.
  for (const key of Object.keys(process.env)) {
    if (
      CRED_PREFIXES.some((p) => key.startsWith(p)) ||
      key === "PAPERFORGE_KEYRING_BACKEND" ||
      key === "PAPERFORGE_E2E_KEYRING_FILE" ||
      key === "PYTHONPATH" ||
      key === "PYTHONHOME" ||
      key.startsWith("PAPERFORGE_POLL_")
    ) {
      delete process.env[key];
    }
  }
  process.env.PYTHON_KEYRING_BACKEND = "keyring.backends.fail.Keyring";
  process.env.PAPERFORGE_KEYRING_BACKEND = "keyring.backends.fail.Keyring";
  delete process.env.PAPERFORGE_RUNTIME_POINTER;
}

// Per-program outbound block for the pinned host binaries + this node.
// Loopback bypasses Windows Firewall, so the 127.0.0.1 CDP/driver channel
// is preserved while genuine non-loopback egress dies at the OS layer.
// HOSTED RUNNERS ONLY: refuses unless GITHUB_ACTIONS==true, so a local
// run-all can never touch the user's firewall.
function firewallEnsure(programs) {
  const status = { state: "unknown", rules: [], notes: [] };
  if (process.env.GITHUB_ACTIONS !== "true") {
    status.state = "refused";
    status.notes.push("firewall changes refused: GITHUB_ACTIONS!=true (local safety)");
    return status;
  }
  if (process.platform !== "win32") {
    status.state = "skipped";
    status.notes.push(`non-windows platform ${process.platform}: no firewall block applied`);
    return status;
  }
  let applied = 0;
  for (const { tag, program } of programs) {
    const name = `${CONF.FIREWALL_RULE_PREFIX}-${tag}`;
    try {
      // Clear a stale rule from a killed prior run, then add.
      spawnSync("netsh", ["advfirewall", "firewall", "delete", "rule", `name=${name}`], {
        stdio: "pipe",
        encoding: "utf8",
      });
      const add = spawnSync(
        "netsh",
        ["advfirewall", "firewall", "add", "rule", `name=${name}`, "dir=out", "action=block", `program=${program}`, "remoteip=any", "enable=yes"],
        { stdio: "pipe", encoding: "utf8" }
      );
      const show = spawnSync("netsh", ["advfirewall", "firewall", "show", "rule", `name=${name}`], {
        stdio: "pipe",
        encoding: "utf8",
      });
      const verified =
        add.status === 0 && show.status === 0 && /Enabled:\s+Yes/i.test(String(show.stdout ?? ""));
      status.rules.push({ name, program, verified });
      if (verified) applied += 1;
      else status.notes.push(`rule ${name} added but not verified`);
    } catch (err) {
      status.rules.push({ name, program, verified: false });
      status.notes.push(`rule ${name} failed: ${String(err?.message ?? err)}`);
    }
  }
  status.state = applied === programs.length ? "applied" : "partial";
  return status;
}

function firewallRemove() {
  if (process.env.GITHUB_ACTIONS !== "true") return;
  if (process.platform !== "win32") return;
  for (const tag of ["obsidian", "driver", "node"]) {
    try {
      spawnSync(
        "netsh",
        ["advfirewall", "firewall", "delete", "rule", `name=${CONF.FIREWALL_RULE_PREFIX}-${tag}`],
        { stdio: "pipe", encoding: "utf8" }
      );
    } catch {
      // Best-effort teardown on an ephemeral runner.
    }
  }
}

// Proves the loopback path the egress gate claims to preserve: starts the
// pinned chromedriver and makes a real TCP connection to its loopback
// listener. Run AFTER the firewall rules are applied; if loopback CDP is
// unreachable the gate is broken and any cell result would be a harness
// artifact (harness-blocked, never product-failure).
async function proveLoopbackCdp(driverPath) {
  const { spawn: spawnProc } = await import("node:child_process");
  const { default: net } = await import("node:net");
  const probe = await new Promise((resolveProbe) => {
    const child = spawnProc(driverPath, ["--port=9519", "--allowed-ips=127.0.0.1"], { stdio: "pipe" });
    let settled = false;
    const done = (result) => {
      if (settled) return;
      settled = true;
      try {
        child.kill();
      } catch {
        // Probe driver teardown is best-effort.
      }
      resolveProbe(result);
    };
    child.on("error", (err) => done({ ok: false, detail: `spawn failed: ${String(err?.message ?? err)}` }));
    setTimeout(() => {
      const sock = net.connect({ host: "127.0.0.1", port: 9519 }, () => {
        sock.write("GET /status HTTP/1.0\r\n\r\n");
      });
      let data = "";
      const timer = setTimeout(() => {
        sock.destroy();
        done({ ok: false, detail: "loopback connect timed out after 10s" });
      }, 10000);
      sock.on("data", (chunk) => {
        data += String(chunk);
        if (/200 OK/.test(data) && /ready|build/i.test(data)) {
          clearTimeout(timer);
          sock.destroy();
          done({ ok: true, detail: "real loopback /status 200 from pinned driver" });
        }
      });
      sock.on("error", (err) => {
        clearTimeout(timer);
        done({ ok: false, detail: `loopback connect failed: ${String(err?.message ?? err)}` });
      });
      sock.on("close", () => {
        clearTimeout(timer);
        if (data && !/200 OK/.test(data)) done({ ok: false, detail: `unexpected driver reply: ${data.slice(0, 120)}` });
      });
    }, 1500);
    setTimeout(() => done({ ok: false, detail: "driver produced no connectable listener within 15s" }), 15000);
  });
  return probe;
}

// ------------------------------------------------------------------- cell ---

function snapshotAppCrashEvents() {
  // Best-effort read of recent Windows Application Error events.
  // Absence is recorded as null (unknown), not zero.
  if (process.platform !== "win32") return null;
  try {
    const out = sh("powershell", [
      "-NoProfile",
      "-Command",
      "Get-WinEvent -FilterHashtable @{LogName='Application'; ID=1000,1002; StartTime=(Get-Date).AddHours(-6)} " +
        "-ErrorAction SilentlyContinue | Select-Object -First 20 TimeCreated,Id,Message | Format-List | Out-String",
    ]);
    return out.slice(0, 4000) || null;
  } catch {
    return null;
  }
}

// Best-effort kill of processes owned by this cell, scoped by the unique
// copied-vault path on their command line. Never broad imagename sweeps.
function killOwnedByVault(openVault) {
  if (!openVault) return "skipped: no copied vault path";
  const marker = basename(openVault);
  try {
    if (process.platform === "win32") {
      const res = spawnSync(
        "powershell",
        [
          "-NoProfile",
          "-Command",
          `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*${marker}*' } | Stop-Process -Force -ErrorAction SilentlyContinue; 'swept'`,
        ],
        { stdio: "pipe", encoding: "utf8", timeout: 30000 }
      );
      return `win32 sweep status=${res.status} out=${String(res.stdout ?? "").trim().slice(0, 80)}`;
    }
    const res = spawnSync("pkill", ["-f", marker], { stdio: "pipe", encoding: "utf8", timeout: 15000 });
    return `posix pkill status=${res.status}`;
  } catch (err) {
    return `sweep failed: ${String(err?.message ?? err)}`;
  }
}

function copyCrashEvidence(artifactsDir, configCandidates, realCrashDumps, cellStartMs) {
  // Crashpad under the service-created config dirs + WER CrashDumps.
  // Absent sources are recorded as explicitly unavailable, never silent null.
  const record = { crashpad: "unavailable: no Crashpad dir in candidate config dirs", crashDumps: "unavailable: no new dumps", mainLog: "unavailable: not found" };
  for (const dir of configCandidates) {
    const crashpad = join(dir, "Crashpad");
    if (existsSync(crashpad)) {
      try {
        cpSync(crashpad, join(artifactsDir, `Crashpad-${basename(dir)}`), { recursive: true });
        record.crashpad = `copied: Crashpad-${basename(dir)}`;
      } catch (err) {
        record.crashpad = `copy failed: ${String(err?.message ?? err)}`;
      }
    }
    const mainLog = join(dir, "main.log");
    if (existsSync(mainLog)) {
      try {
        if (statSync(mainLog).size <= 5 * 1024 * 1024) {
          cpSync(mainLog, join(artifactsDir, `main-${basename(dir)}.log`));
          record.mainLog = `copied: main-${basename(dir)}.log`;
        } else {
          record.mainLog = "unavailable: main.log exceeds 5MB cap";
        }
      } catch (err) {
        record.mainLog = `copy failed: ${String(err?.message ?? err)}`;
      }
    }
  }
  if (realCrashDumps && existsSync(realCrashDumps)) {
    try {
      const fresh = readdirSync(realCrashDumps).filter((f) => {
        if (!/obsidian|chromedriver|chrome|electron/i.test(f)) return false;
        try {
          return statSync(join(realCrashDumps, f)).mtimeMs >= cellStartMs;
        } catch {
          return false;
        }
      });
      if (fresh.length > 0) {
        mkdirSync(join(artifactsDir, "CrashDumps"), { recursive: true });
        for (const f of fresh.slice(0, 10)) {
          try {
            cpSync(join(realCrashDumps, f), join(artifactsDir, "CrashDumps", f));
          } catch {
            // Per-file best effort; the record below names what matched.
          }
        }
        record.crashDumps = `copied: ${fresh.slice(0, 10).join(",")}`;
      }
    } catch (err) {
      record.crashDumps = `read failed: ${String(err?.message ?? err)}`;
    }
  } else if (!realCrashDumps) {
    record.crashDumps = "unavailable: no real LOCALAPPDATA captured";
  }
  return record;
}

function writeCellResult(artifactsDir, result) {
  mkdirSync(artifactsDir, { recursive: true });
  writeFileSync(join(artifactsDir, "result.json"), JSON.stringify(result, null, 2));
}

async function runCellChild(cellDef) {
  const cellStartMs = Date.now();
  const artifactsDir = join(ARTIFACTS, "cells", cellDef.cell);
  mkdirSync(artifactsDir, { recursive: true });
  const realLocalAppData = process.env.LOCALAPPDATA ?? null;
  const tmpBefore = new Set(readdirSync(tmpdir()));
  const bundle = readJson(join(PREFETCH_DIR, `bundle-${cellDef.ref}.json`));
  const pins = readJson(join(PREFETCH_DIR, "host-pins.json"));
  const versions = readJson(join(PREFETCH_DIR, "host-versions.json"));

  // Re-verify shared host pins before the cell; drift blocks THIS cell with
  // evidence but never aborts the remaining mandatory cells.
  for (const [label, file, want] of [
    ["installer", pins.binaryPath, pins.binarySha256],
    ["asar", pins.appPath, pins.appSha256],
    ["driver", pins.driverPath, pins.driverSha256],
  ]) {
    const got = sha256File(file);
    if (got !== want) {
      writeCellResult(artifactsDir, {
        cell: cellDef.cell,
        verdict: "blocked",
        errorStage: "setup",
        ref: cellDef.ref,
        refFull: cellDef.refFull,
        pluginOn: cellDef.pluginOn,
        setupFailure: `shared host drift: ${label} ${got} != pinned ${want}`,
        error: null,
        ts: new Date().toISOString(),
      });
      console.log(`[cell ${cellDef.cell}] verdict=blocked (host drift)`);
      return;
    }
  }
  if (bundle.ref !== cellDef.refFull) {
    writeCellResult(artifactsDir, {
      cell: cellDef.cell,
      verdict: "blocked",
      errorStage: "setup",
      ref: cellDef.ref,
      refFull: cellDef.refFull,
      pluginOn: cellDef.pluginOn,
      setupFailure: `bundle ref mismatch: ${bundle.ref} != ${cellDef.refFull}`,
      error: null,
      ts: new Date().toISOString(),
    });
    console.log(`[cell ${cellDef.cell}] verdict=blocked (bundle ref)`);
    return;
  }

  // Fresh HOME (pointer-hostile) + fresh stage dir per cell.
  const freshHome = mkdtempSync(join(tmpdir(), `h-fixed-ab-home-${cellDef.cell}-`));
  const stageDir = mkdtempSync(join(tmpdir(), `h-fixed-ab-stage-${cellDef.cell}-`));
  const stagePluginDir = join(stageDir, "paperforge-plugin");
  mkdirSync(stagePluginDir, { recursive: true });
  const srcPluginDir = join(PREFETCH_DIR, `src-${cellDef.ref}`, "paperforge", "plugin");
  for (const f of ["main.js", "manifest.json", "styles.css"]) {
    const src = join(srcPluginDir, f);
    if (existsSync(src)) cpSync(src, join(stagePluginDir, f));
  }
  // Seed autoSyncEnabled:false in the STAGE plugin dir BEFORE the session:
  // the service's installPlugins copies stage data.json into the vault copy.
  const stagedManifest = readJson(join(stagePluginDir, "manifest.json"));
  const pluginId = stagedManifest.id ?? "paperforge";
  const seedData = { autoSyncEnabled: false };
  try {
    const prev = existsSync(join(stagePluginDir, "data.json"))
      ? readJson(join(stagePluginDir, "data.json"))
      : {};
    writeFileSync(join(stagePluginDir, "data.json"), JSON.stringify({ ...prev, ...seedData }, null, 2));
  } catch (err) {
    throw new Error(`cannot seed stage data.json: ${String(err?.message ?? err)}`);
  }

  // Fresh GENERATED empty synthetic vault: Welcome.md only. installPlugins
  // creates .obsidian itself during setupVault. Never a repo fixture path.
  const vaultSeed = mkdtempSync(join(tmpdir(), `h-fixed-ab-vaultsrc-${cellDef.cell}-`));
  writeFileSync(join(vaultSeed, "Welcome.md"), WELCOME_MD);

  const crashBefore = snapshotAppCrashEvents();
  const ctx = {
    cell: cellDef.cell,
    ref: cellDef.ref,
    refFull: cellDef.refFull,
    pluginOn: cellDef.pluginOn,
    artifactsDir,
    builtMainJs: join(stagePluginDir, "main.js"),
    builtManifest: join(stagePluginDir, "manifest.json"),
    versions,
    lockfileSha256: bundle.lockfileSha256 ?? null,
  };

  const tSetupStart = Date.now();
  let browser = null;
  let capabilities = null;
  try {
    applyEgressGate();
    scrubEnv();
    process.env.HOME = freshHome;
    process.env.USERPROFILE = freshHome;
    // Derive HOMEDRIVE/HOMEPATH from the actual freshHome root — never
    // hardcode C:\ as the effective HOME.
    const homeRoot = resolve(freshHome).slice(0, 3);
    const homeDrive = homeRoot.slice(0, 2).toUpperCase();
    const homeRemainder = resolve(freshHome).slice(3).replace(/\//g, "\\");
    process.env.HOMEDRIVE = homeDrive;
    process.env.HOMEPATH = homeRemainder ? `\\${homeRemainder}` : "\\";
    process.env.APPDATA = join(freshHome, "AppData", "Roaming");
    process.env.LOCALAPPDATA = join(freshHome, "AppData", "Local");

    // Fail-closed proof: no production pointer visible under the fresh HOME.
    const pointerProbe = join(freshHome, ".paperforge", "runtime", "pointer.json");
    ctx.pointerAbsent = !existsSync(pointerProbe);

    const { startWdioSession } = await import("wdio-obsidian-service").catch(() =>
      import(fileUrl(join(PLUGIN_DIR, "node_modules", "wdio-obsidian-service", "dist", "index.js")))
    );
    // ONLY delta between same-ref cells. Never imports production wdio.conf.
    // cacheDir points at the PREFETCHED cache so onPrepare needs no network
    // under the egress gate (all artifacts cached, atomicCreate replace:false
    // short-circuits re-download).
    capabilities = CONF.baseCapabilities();
    capabilities["wdio:obsidianOptions"].binaryPath = pins.binaryPath;
    capabilities["wdio:obsidianOptions"].appPath = pins.appPath;
    capabilities["wdio:obsidianOptions"].vault = vaultSeed;
    capabilities["wdio:obsidianOptions"].copy = true;
    // ONLY delta between same-ref cells: plugin present vs absent.
    capabilities["wdio:obsidianOptions"].plugins = cellDef.pluginOn ? [stagePluginDir] : [];
    capabilities["wdio:chromedriverOptions"].binary = pins.driverPath;

    const logDir = join(artifactsDir, "wdio-logs");
    mkdirSync(logDir, { recursive: true });
    browser = await startWdioSession(
      {
        capabilities,
        cacheDir: join(ARTIFACTS, ".obsidian-cache"),
        logLevel: "debug",
        connectionRetryCount: 0, // no retry: crash evidence must not be masked
        outputDir: logDir,
        mochaOpts: { ui: "bdd", timeout: CONF.BOOT_TIMEOUT_MS },
      },
      {}
    );

    // The actual copied vault path comes from the service API: our caps
    // object is mutated in place by onPrepare (openVault), with the browser
    // requestedCapabilities as fallback. A guessed path is never trusted.
    const openVault =
      capabilities?.["wdio:obsidianOptions"]?.openVault ??
      browser?.requestedCapabilities?.["wdio:obsidianOptions"]?.openVault ??
      null;
    if (!openVault || !existsSync(openVault)) {
      throw new Error(`copied vault path unavailable (openVault=${openVault ?? "null"})`);
    }
    ctx.copiedVault = openVault;
    ctx.copiedVaultIsFresh =
      resolve(openVault) !== resolve(vaultSeed) && resolve(openVault).startsWith(resolve(tmpdir()));
    if (!ctx.copiedVaultIsFresh) {
      throw new Error(`vault was not freshly copied (openVault=${openVault})`);
    }
    // Verify the pre-boot seed propagated into the REAL copy. Missing or
    // wrong seed is a setup failure with evidence, never silently tolerated.
    if (cellDef.pluginOn) {
      const dataPath = join(openVault, ".obsidian", "plugins", pluginId, "data.json");
      let seeded = null;
      try {
        seeded = existsSync(dataPath) ? readJson(dataPath) : null;
      } catch (err) {
        throw new Error(`cannot read propagated data.json: ${String(err?.message ?? err)}`);
      }
      ctx.dataJsonSeeded = seeded?.autoSyncEnabled === false;
      if (!ctx.dataJsonSeeded) {
        throw new Error(`seed did not propagate (data.json=${JSON.stringify(seeded)?.slice(0, 120)})`);
      }
    } else {
      ctx.dataJsonSeeded = null;
    }
    const tSetupEnd = Date.now();

    const { probe } = await import(SPEC_URL);
    await probe(browser, { ...ctx, setupMs: tSetupEnd - tSetupStart });
  } catch (err) {
    // Setup failure (service dies before/during boot, or seed verification
    // failed): distinct verdict + stage. If the spec already recorded a
    // failed verdict, PRESERVE it — never overwrite failed with blocked.
    const existing = existsSync(join(artifactsDir, "result.json"))
      ? readJson(join(artifactsDir, "result.json"))
      : null;
    if (!existing) {
      writeCellResult(artifactsDir, {
        cell: cellDef.cell,
        verdict: "blocked",
        errorStage: "setup",
        ref: cellDef.ref,
        refFull: cellDef.refFull,
        pluginOn: cellDef.pluginOn,
        setupFailure: String(err?.stack ?? err),
        error: null,
        windowsAppCrashEvents: snapshotAppCrashEvents(),
        windowsAppCrashEventsBefore: crashBefore ? crashBefore.slice(0, 1000) : null,
        ts: new Date().toISOString(),
      });
    } else {
      existing.windowsAppCrashEvents =
        existing.windowsAppCrashEvents ?? snapshotAppCrashEvents();
      writeCellResult(artifactsDir, existing);
    }
  } finally {
    try {
      if (browser) await browser.deleteSession();
    } catch {
      // Session teardown after a renderer crash is best-effort; the
      // result.json verdict + logs already captured the evidence.
    }
    // Owned-tree sweep so no orphan cell contaminates the next one.
    ctx.orphanSweep = killOwnedByVault(ctx.copiedVault ?? null);
  }

  // Crash-relevant host evidence next to result.json.
  const crashAfter = snapshotAppCrashEvents();
  if (crashAfter) {
    writeFileSync(join(artifactsDir, "appcrash-after.txt"), crashAfter);
  }
  if (crashBefore) {
    writeFileSync(join(artifactsDir, "appcrash-before.txt"), crashBefore);
  }
  const configCandidates = readdirSync(tmpdir()).filter(
    (n) => n.startsWith("obsidian-launcher-config-") && !tmpBefore.has(n)
  );
  const crashEvidence = copyCrashEvidence(
    artifactsDir,
    configCandidates.map((n) => join(tmpdir(), n)),
    realLocalAppData ? join(realLocalAppData, "CrashDumps") : null,
    cellStartMs
  );
  const result = readJson(join(artifactsDir, "result.json"));
  result.windowsAppCrashEvents =
    result.windowsAppCrashEvents ?? (crashAfter ? "see appcrash-after.txt" : null);
  result.crashEvidence = crashEvidence;
  result.orphanSweep = ctx.orphanSweep ?? null;
  result.egressGate = { deadProxy: process.env.HTTP_PROXY ?? null };
  writeCellResult(artifactsDir, result);
  console.log(`[cell ${cellDef.cell}] verdict=${result.verdict} stage=${result.errorStage ?? "-"}`);
}

// --------------------------------------------------------------- run-all ---

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runCellSupervised(cellDef, firewallStatus) {
  const artifactsDir = join(ARTIFACTS, "cells", cellDef.cell);
  mkdirSync(artifactsDir, { recursive: true });
  const logPath = join(artifactsDir, "child-output.log");
  const outFd = openSync(logPath, "w");
  const tStart = Date.now();
  const child = spawn(process.execPath, [join(REPO_ROOT, "scripts", "diagnostics", "h-fixed-ab.mjs"), "cell", cellDef.cell], {
    cwd: REPO_ROOT,
    env: { ...process.env },
    stdio: ["ignore", outFd, outFd],
  });
  let timedOut = false;
  let exited = false;
  let exitCode = null;
  let signal = null;
  const onExit = new Promise((resolve) => {
    child.on("exit", (code, sig) => {
      exited = true;
      exitCode = code;
      signal = sig;
      resolve();
    });
    child.on("error", () => {
      exited = true;
      resolve();
    });
  });
  const deadline = delay(CONF.BOOT_TIMEOUT_MS).then(() => {
    if (!exited) {
      timedOut = true;
      try {
        if (process.platform === "win32") {
          spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], {
            stdio: "pipe",
            encoding: "utf8",
            timeout: 30000,
          });
        } else {
          child.kill("SIGKILL");
        }
      } catch {
        // Kill failure is recorded below; the supervisor must continue.
      }
    }
  });
  await Promise.race([onExit, deadline.then(() => onExit)]);
  if (!exited) {
    await Promise.race([onExit, delay(10000)]);
  }
  try {
    closeSync(outFd);
  } catch {
    // Log fd teardown is best-effort.
  }
  const supervisedMs = Date.now() - tStart;

  // Collect the child-written verdict; synthesize blocked only when the child
  // left no result (timeout kill or harness crash). Never overwrite it.
  let result = null;
  try {
    result = readJson(join(artifactsDir, "result.json"));
  } catch {
    result = null;
  }
  if (!result) {
    result = {
      cell: cellDef.cell,
      verdict: "blocked",
      errorStage: timedOut ? "timeout" : "child-exit",
      ref: cellDef.ref,
      refFull: cellDef.refFull,
      pluginOn: cellDef.pluginOn,
      setupFailure: null,
      error:
        timedOut
          ? `cell exceeded ${CONF.BOOT_TIMEOUT_MS}ms boot deadline; owned tree killed`
          : `child exited without verdict (exitCode=${exitCode} signal=${signal})`,
      ts: new Date().toISOString(),
    };
  }
  result.exitCode = exitCode;
  result.signal = signal;
  result.timedOut = timedOut;
  result.supervisedMs = supervisedMs;
  result.killFailed = timedOut && !exited;
  result.childLog = "see child-output.log";
  result.egressFirewall = firewallStatus.state;
  writeCellResult(artifactsDir, result);
  console.log(
    `[supervisor ${cellDef.cell}] verdict=${result.verdict} exit=${exitCode} signal=${signal} timedOut=${timedOut}`
  );
  return result;
}

async function runAll() {
  mkdirSync(ARTIFACTS, { recursive: true });
  applyEgressGate();
  scrubEnv();
  const pins = readJson(join(PREFETCH_DIR, "host-pins.json"));
  const firewallStatus = firewallEnsure([
    { tag: "obsidian", program: pins.binaryPath },
    { tag: "driver", program: pins.driverPath },
    { tag: "node", program: process.execPath },
  ]);
  console.log(`[run-all] firewall: ${firewallStatus.state}`);
  for (const n of firewallStatus.notes) console.log(`[run-all] firewall note: ${n}`);
  // Prove the claimed loopback path BEFORE any cell runs: a real TCP
  // connection to the pinned driver on 127.0.0.1. If unreachable, the
  // egress gate is broken — record harness-blocked for all cells, never
  // product failure.
  let loopback = { ok: false, detail: "not probed" };
  if (firewallStatus.state === "applied" || firewallStatus.state === "partial") {
    loopback = await proveLoopbackCdp(pins.driverPath);
    console.log(`[run-all] loopback: ok=${loopback.ok} ${loopback.detail}`);
  } else {
    loopback = { ok: false, detail: `firewall ${firewallStatus.state}: no loopback gate to prove` };
  }
  if (firewallStatus.state === "applied" && !loopback.ok) {
    const harnessBlocked = CELLS.map((cellDef) => {
      const artifactsDir = join(ARTIFACTS, "cells", cellDef.cell);
      mkdirSync(artifactsDir, { recursive: true });
      const result = {
        cell: cellDef.cell,
        verdict: "blocked",
        errorStage: "harness-egress",
        ref: cellDef.ref,
        refFull: cellDef.refFull,
        pluginOn: cellDef.pluginOn,
        setupFailure: null,
        error: `egress gate blocks loopback CDP (${loopback.detail}); no cell attempted — harness artifact, not product failure`,
        ts: new Date().toISOString(),
      };
      writeCellResult(artifactsDir, result);
      return { ...result };
    });
    firewallRemove();
    const summary = {
      verdict: "harness-blocked",
      cells: harnessBlocked.map((r) => ({ cell: r.cell, verdict: r.verdict, errorStage: r.errorStage ?? null })),
      hostPins: readJson(join(PREFETCH_DIR, "host-pins.json")),
      hostVersions: readJson(join(PREFETCH_DIR, "host-versions.json")),
      lockfiles: readJson(join(PREFETCH_DIR, "lockfiles.json")),
      hostTreeRecheck: null,
      egressGate: { deadProxy: CONF.DEAD_PROXY, firewall: firewallStatus, loopback },
      ts: new Date().toISOString(),
      notes: ["Egress gate broke the loopback CDP path; cells not attempted. Fix the gate, not the product."],
    };
    writeFileSync(join(ARTIFACTS, "summary.json"), JSON.stringify(summary, null, 2));
    console.log(JSON.stringify(summary.cells));
    return;
  }
  const results = [];
  try {
    for (const cellDef of CELLS) {
      // Sequential: parallel pips deadlock on WinError32 install.lock.d.
      // Each cell is a separate child with a bounded deadline.
      results.push(await runCellSupervised(cellDef, firewallStatus));
    }
  } finally {
    firewallRemove();
  }
  // Recheck the shared host tree AFTER all cells ran.
  let hostTreeRecheck = null;
  try {
    const fresh = hashTree(dirname(pins.binaryPath));
    const changed = [];
    const want = new Map((pins.installerTree?.entries ?? []).map((e) => [e.rel, e.sha256]));
    for (const e of fresh.entries) {
      if (want.get(e.rel) !== e.sha256) changed.push(e.rel);
    }
    for (const rel of want.keys()) {
      if (!fresh.entries.some((e) => e.rel === rel)) changed.push(`${rel} (deleted)`);
    }
    hostTreeRecheck = {
      match: fresh.digest === pins.installerTree?.digest,
      digest: fresh.digest,
      pinnedDigest: pins.installerTree?.digest ?? null,
      changed: changed.slice(0, 20),
    };
  } catch (err) {
    hostTreeRecheck = { match: false, error: String(err?.message ?? err) };
  }
  const summary = {
    verdict: "evidence-complete",
    cells: results.map((r) => ({
      cell: r.cell,
      verdict: r.verdict,
      errorStage: r.errorStage ?? null,
      exitCode: r.exitCode ?? null,
      signal: r.signal ?? null,
      timedOut: r.timedOut ?? false,
    })),
    hostPins: readJson(join(PREFETCH_DIR, "host-pins.json")),
    hostVersions: readJson(join(PREFETCH_DIR, "host-versions.json")),
    lockfiles: readJson(join(PREFETCH_DIR, "lockfiles.json")),
    hostTreeRecheck,
    egressGate: { deadProxy: CONF.DEAD_PROXY, firewall: firewallStatus, loopback },
    ts: new Date().toISOString(),
    notes: [
      "All 4 cells executed; verdict failed/blocked is terminal evidence, not a retry signal.",
      "Fixed boot observation only: no full-H journey claims.",
    ],
  };
  writeFileSync(join(ARTIFACTS, "summary.json"), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary.cells));
}

function emergencyResult(cellDef, err) {
  try {
    const artifactsDir = join(ARTIFACTS, "cells", cellDef.cell);
    if (!existsSync(join(artifactsDir, "result.json"))) {
      writeCellResult(artifactsDir, {
        cell: cellDef.cell,
        verdict: "blocked",
        errorStage: "child-harness",
        ref: cellDef.ref,
        refFull: cellDef.refFull,
        pluginOn: cellDef.pluginOn,
        setupFailure: null,
        error: String(err?.stack ?? err),
        ts: new Date().toISOString(),
      });
    }
  } catch {
    // Last resort: nothing writable; the supervisor synthesizes blocked.
  }
}

const [cmd, arg] = process.argv.slice(2);
if (cmd === "prefetch") await prefetch();
else if (cmd === "run-all") await runAll();
else if (cmd === "cell") {
  const def = CELLS.find((c) => c.cell === arg);
  if (!def) throw new Error(`unknown cell: ${arg} (want ${CELLS.map((c) => c.cell).join("|")})`);
  try {
    await runCellChild(def);
  } catch (err) {
    emergencyResult(def, err);
    process.exitCode = 1;
  }
} else if (cmd === "report") {
  try {
    const summary = readJson(join(ARTIFACTS, "summary.json"));
    if (summary.verdict === "prefetch-blocked") {
      console.log(`prefetch-blocked at stage=${summary.prefetchStatus?.stage ?? "?"}: ${(summary.prefetchStatus?.error ?? "").slice(0, 300)}`);
      console.log(`steps done: ${Object.keys(summary.prefetchStatus?.steps ?? {}).join(",") || "(none)"}`);
    } else {
      for (const c of summary.cells) {
        console.log(`${c.cell}: verdict=${c.verdict} stage=${c.errorStage ?? "-"} exit=${c.exitCode ?? "-"} timedOut=${c.timedOut}`);
      }
      console.log(`hostTreeRecheck.match=${summary.hostTreeRecheck?.match ?? "unknown"}`);
    }
  } catch {
    console.log("no summary.json yet (run-all has not completed)");
    process.exitCode = 1;
  }
} else if (cmd === "verify") {
  for (const f of ["h-fixed-ab.mjs", "h-fixed-ab.conf.mjs", "h-fixed-ab.spec.mjs"]) {
    execFileSync(process.execPath, ["--check", join(REPO_ROOT, "scripts", "diagnostics", f)], { stdio: "pipe" });
    console.log(`ok: ${f}`);
  }
} else {
  throw new Error("usage: h-fixed-ab.mjs <prefetch|run-all|cell <name>|report|verify>");
}
