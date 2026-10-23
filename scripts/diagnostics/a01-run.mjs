// A01 launcher: ONE baseline A01 attempt under a REAL egress gate applied
// BEFORE wdio (dead proxy + per-program Windows firewall block, owned
// ephemeral CI only), then the ORIGINAL wdio testrunner against the overlay
// (ORIGINAL config module + ORIGINAL A01 body, timeouts untouched).
// No automatic retries. Failure evidence, never green acceptance.
//
//   node scripts/diagnostics/a01-run.mjs [new|old]   (default: new)
//
// Isolation: fresh HOME/USERPROFILE/APPDATA/LOCALAPPDATA (never the real
// user profile or production pointer); the contract-H initial pointer
// (matching .post1, via Python publish into the fresh HOME) is published
// BEFORE the original config import (whose module body copies the fixture
// keyring into the synthetic published runtime), and the UI-installed
// candidate must DIFFER from it. PIP_NO_INDEX + PIP_FIND_LINKS=<absolute
// wheelhouse>; missing deps => harness-blocked, not product failure.
import { spawn, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const ART = join(REPO_ROOT, "a01-artifacts");
const H_PREFETCH = join(REPO_ROOT, "h-fixed-ab-artifacts", "prefetch");
const TAG = process.argv[2] ?? "new";
const DEAD_PROXY = "http://127.0.0.1:9";
const FW_PREFIX = "a01-block";
// Diagnostic-only FULL-H single-host mode: original full suite (no grep),
// journey gate on, mocha bail. A01 mode (default) unchanged.
const FULL_MODE = process.env.PF_DIAGNOSTIC_H_FULL === "1";
// A01 mode keeps the original 600s bound; FULL mode is bounded by the
// ORIGINAL H 45min (test-level 600/540 and A06 timeouts untouched).
const WDIO_BUDGET_MS = FULL_MODE ? 45 * 60 * 1000 : 600000;

function sha256File(p) {
  return createHash("sha256").update(readFileSync(p)).digest("hex");
}
function listVenvRoots(home) {
  const rt = join(home, ".paperforge", "runtime");
  if (!existsSync(rt)) return [];
  return readdirSync(rt)
    .filter((n) => n.startsWith("venv-"))
    .map((n) => join(rt, n))
    .filter((p) => { try { return statSync(p).isDirectory(); } catch { return false; } });
}
function readLatest(file) {
  try {
    const ev = JSON.parse(readFileSync(file, "utf8"));
    const runs = Array.isArray(ev) ? ev : [ev];
    return runs[runs.length - 1] ?? null;
  } catch { return null; }
}
function countReporter(stdout) {
  // passed/pending from the raw mocha reporter; first independent error.
  const m = String(stdout).match(/(\d+)\s+passing/i);
  const p = String(stdout).match(/(\d+)\s+pending/i);
  const f = String(stdout).match(/(\d+)\s+failing/i);
  const i = String(stdout).search(/failing|AssertionError|Error:/);
  return {
    passing: m ? Number(m[1]) : null,
    pending: p ? Number(p[1]) : 0,
    failing: f ? Number(f[1]) : null,
    firstError: i >= 0 ? String(stdout).slice(Math.max(0, i - 200), i + 1200) : null,
  };
}
function scrubEnv() {
  for (const key of Object.keys(process.env)) {
    if (
      /^(PAPERFORGE_CREDENTIAL_|PADDLEOCR_|VECTOR_DB_|OPENAI_|OBSIDIAN_EMAIL|OBSIDIAN_PASSWORD)/.test(key) ||
      key === "PAPERFORGE_KEYRING_BACKEND" || key === "PAPERFORGE_E2E_KEYRING_FILE" ||
      key === "PYTHONPATH" || key === "PYTHONHOME" || key.startsWith("PAPERFORGE_POLL_")
    ) delete process.env[key];
  }
  process.env.PYTHON_KEYRING_BACKEND = "keyring.backends.fail.Keyring";
  process.env.PAPERFORGE_KEYRING_BACKEND = "keyring.backends.fail.Keyring";
  delete process.env.PAPERFORGE_RUNTIME_POINTER;
}
function firewallApply(programs) {
  const status = { state: "unknown", rules: [], notes: [] };
  if (process.env.GITHUB_ACTIONS !== "true") {
    status.state = "refused";
    status.notes.push("firewall changes refused: GITHUB_ACTIONS!=true (local safety)");
    return status;
  }
  if (process.platform !== "win32") {
    status.state = "skipped";
    status.notes.push(`non-windows platform ${process.platform}`);
    return status;
  }
  let applied = 0;
  for (const { tag, program } of programs) {
    const name = `${FW_PREFIX}-${tag}`;
    try {
      spawnSync("netsh", ["advfirewall", "firewall", "delete", "rule", `name=${name}`], { stdio: "pipe", encoding: "utf8" });
      const add = spawnSync("netsh", ["advfirewall", "firewall", "add", "rule", `name=${name}`, "dir=out", "action=block", `program=${program}`, "remoteip=any", "enable=yes"], { stdio: "pipe", encoding: "utf8" });
      const show = spawnSync("netsh", ["advfirewall", "firewall", "show", "rule", `name=${name}`], { stdio: "pipe", encoding: "utf8" });
      const verified = add.status === 0 && show.status === 0 && /Enabled:\s+Yes/i.test(String(show.stdout ?? ""));
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
  if (process.env.GITHUB_ACTIONS !== "true" || process.platform !== "win32") return;
  for (const tag of ["obsidian", "driver", "node", "venv-stage", "venv-base", "venv-sel"]) {
    try {
      spawnSync("netsh", ["advfirewall", "firewall", "delete", "rule", `name=${FW_PREFIX}-${tag}`], { stdio: "pipe", encoding: "utf8" });
    } catch { /* best-effort teardown */ }
  }
}
async function proveLoopbackCdp(driverPath) {
  const { spawn: spawnProc } = await import("node:child_process");
  const { default: net } = await import("node:net");
  return new Promise((resolveProbe) => {
    const receipt = { stdout: "", stderr: "", exitCode: null, spawnError: null };
    const child = spawnProc(driverPath, ["--port=9519", "--allowed-ips=127.0.0.1"], { stdio: "pipe" });
    let settled = false;
    const done = (r) => {
      if (settled) return;
      settled = true;
      try { child.kill(); } catch { /* best-effort */ }
      resolveProbe({ ...r, driver: receipt });
    };
    child.stdout.on("data", (c) => { receipt.stdout += String(c).slice(0, 2000); });
    child.stderr.on("data", (c) => { receipt.stderr += String(c).slice(0, 2000); });
    child.on("error", (err) => { receipt.spawnError = String(err?.message ?? err); });
    child.on("exit", (code) => { receipt.exitCode = code; });
    setTimeout(() => {
      const sock = net.connect({ host: "127.0.0.1", port: 9519 }, () => {
        sock.write("GET /status HTTP/1.1\r\nHost: 127.0.0.1:9519\r\nConnection: close\r\n\r\n");
      });
      let data = "";
      const timer = setTimeout(() => { sock.destroy(); done({ ok: false, detail: "loopback connect timed out after 10s" }); }, 10000);
      sock.on("data", (chunk) => {
        data += String(chunk);
        if (/200 OK/.test(data) && /ready|build/i.test(data)) { clearTimeout(timer); sock.destroy(); done({ ok: true, detail: "real loopback /status 200 from pinned driver" }); }
        else if (/40[034]/.test(data) || data.length > 4000) { clearTimeout(timer); sock.destroy(); done({ ok: false, detail: `driver replied without 200: ${data.slice(0, 160)}` }); }
      });
      sock.on("error", (err) => { clearTimeout(timer); done({ ok: false, detail: `loopback connect failed: ${String(err?.message ?? err)}` }); });
      sock.on("close", () => { clearTimeout(timer); if (data && !/200 OK/.test(data)) done({ ok: false, detail: `driver closed without 200: ${data.slice(0, 160)}` }); });
    }, 1500);
    setTimeout(() => done({ ok: false, detail: "driver produced no connectable listener within 15s" }), 15000);
  });
}

const out = { tag: TAG, ok: false, stage: "start", ts: new Date().toISOString() };
let fw = { state: "not-applied" };
let home = null;
const cellArt = join(ART, "cells", TAG);
try {
  const pre = JSON.parse(readFileSync(join(ART, `prefetch-${TAG}.json`), "utf8"));
  if (!pre.ok) throw new Error(`prefetch-${TAG} not ok (stage=${pre.stage}) — harness-blocked, not product failure`);
  out.boundBaseline = { tag: TAG, ref: pre.ref, wheelSha256: pre.wheelSha256, sourceArchive: `src-${TAG}.zip`, sourceArchiveSha256: pre.sourceArchiveSha256 ?? null };
  const pins = JSON.parse(readFileSync(join(H_PREFETCH, "host-pins.json"), "utf8"));
  for (const [label, file, want] of [["installer", pins.binaryPath, pins.binarySha256], ["asar", pins.appPath, pins.appSha256], ["driver", pins.driverPath, pins.driverSha256]]) {
    if (sha256File(file) !== want) throw new Error(`host drift before run: ${label}`);
  }
  out.hostRecheck = "match";

  // Fresh isolated HOME first; everything below binds to it.
  home = mkdtempSync(join(tmpdir(), `a01-home-${TAG}-`));
  process.env.HOME = home;
  process.env.USERPROFILE = home;
  process.env.APPDATA = join(home, "AppData", "Roaming");
  process.env.LOCALAPPDATA = join(home, "AppData", "Local");
  mkdirSync(process.env.APPDATA, { recursive: true });
  mkdirSync(process.env.LOCALAPPDATA, { recursive: true });
  out.isolatedHome = home;

  // Contract-H initial pointer (matching .post1) via Python publish into
  // the FRESH home, BEFORE the original config import.
  const pubScript = [
    `import sys; sys.path.insert(0, ${JSON.stringify(join(ART, `stage-${TAG}`))})`,
    "from paperforge.runtime_pointer import publish_pointer",
    `from pathlib import Path as _P`,
    `ptr = publish_pointer(python_path=${JSON.stringify(pre.venvPython)}, environment_root=${JSON.stringify(resolve(pre.venvPython, "..", ".."))}, home=_P(${JSON.stringify(home)}))`,
    `print(str(ptr))`,
  ].join("\n");
  const pub = spawnSync(pre.venvPython, ["-I", "-c", pubScript], {
    encoding: "utf8", timeout: 120000, stdio: "pipe",
    env: { ...process.env, HOME: home, USERPROFILE: home },
  });
  if (pub.status !== 0) throw new Error(`initial pointer publish failed: ${String(pub.stderr).slice(-500)}`);
  const ptrPath = join(home, ".paperforge", "runtime", "pointer.json");
  out.prePointer = JSON.parse(readFileSync(ptrPath, "utf8"));
  if (out.prePointer.paperforge_version !== "2.0.0rc5.post1") throw new Error(`initial pointer version ${out.prePointer.paperforge_version} != 2.0.0rc5.post1`);
  out.preVenvRoots = listVenvRoots(home);

  // REAL egress gate BEFORE wdio: dead proxy + firewall (host/driver/node/
  // staged venv python / actual selected base + selected executable).
  for (const k of ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]) process.env[k] = DEAD_PROXY;
  process.env.NO_PROXY = "127.0.0.1,localhost";
  process.env.no_proxy = "127.0.0.1,localhost";
  scrubEnv();
  fw = firewallApply([
    { tag: "obsidian", program: pins.binaryPath },
    { tag: "driver", program: pins.driverPath },
    { tag: "node", program: process.execPath },
    { tag: "venv-stage", program: pre.venvPython },
    ...(pre.interpreter?.base ? [{ tag: "venv-base", program: pre.interpreter.base }] : []),
    ...(pre.interpreter?.executable && pre.interpreter.executable !== pre.interpreter.base ? [{ tag: "venv-sel", program: pre.interpreter.executable }] : []),
  ]);
  out.egressFirewall = fw;
  // Fail-closed gate: ONLY 'applied' may run wdio. 'partial'/'refused'/
  // anything else throws here — a partial gate must never run unguarded.
  if (fw.state !== "applied") throw new Error(`egress gate not applied (state=${fw.state}): refusing to run wdio`);
  let loopback = { ok: false, detail: "not probed" };
  loopback = await proveLoopbackCdp(pins.driverPath);
  out.loopback = loopback;
  if (!loopback.ok) throw new Error(`egress gate blocks loopback CDP (${loopback.detail}) — harness artifact, not product failure`);

  // Offline pip + A01 opt-in for the UI install subprocesses.
  const stagedPluginDir = join(ART, `stage-${TAG}`, "paperforge", "plugin");
  process.env.PIP_NO_INDEX = "1";
  process.env.PIP_FIND_LINKS = pre.wheelhouse;
  process.env.PIP_CACHE_DIR = join(ART, `pip-cache-${TAG}`);
  mkdirSync(process.env.PIP_CACHE_DIR, { recursive: true });
  process.env.PF_E2E_SETUP_POSITIVE = "1";
  if (FULL_MODE) {
    process.env.PF_DIAGNOSTIC_H_FULL = "1";
    process.env.PF_E2E_JOURNEY_GATE = "1";
    delete process.env.PF_E2E_GREP;
  }
  process.env.PF_E2E_WHEEL_SHA256 = pre.wheelSha256;
  process.env.A01_HOST_PINS = join(H_PREFETCH, "host-pins.json");
  process.env.A01_CACHE_DIR = join(REPO_ROOT, "h-fixed-ab-artifacts", ".obsidian-cache");
  mkdirSync(cellArt, { recursive: true });
  process.env.A01_ARTIFACTS_DIR = cellArt;
  out.stagedPlugin = stagedPluginDir;
  cpSync(new URL("./a01-overlay.mjs", import.meta.url), join(stagedPluginDir, "wdio.a01.mts"));

  // Run DIRECTLY in the prefetched staged plugin (own isolated source:
  // stamped manifest + freshly built main.js + real vaults). cwd binds the
  // ORIGINAL resolvePluginDir to the staged artifact. Supervised async
  // spawn with the ORIGINAL 600s bound; on timeout the OWNED tree is
  // killed (taskkill /PID /T /F — children included), evidence not retry.
  // Firewall rules come off only AFTER children are stopped (see finally).
  out.stage = "wdio";
  const t0 = Date.now();
  const wdioMain = join(REPO_ROOT, "paperforge", "plugin", "node_modules", "@wdio", "cli", "bin", "wdio.js");
  if (!existsSync(wdioMain)) throw new Error(`wdio entry missing: ${wdioMain} — run npm ci in paperforge/plugin first`);
  const wdioLog = join(cellArt, "wdio-output.log");
  const run = await new Promise((resolveRun) => {
    const child = spawn(process.execPath, [wdioMain, "run", "./wdio.a01.mts"], {
      cwd: stagedPluginDir, env: { ...process.env }, stdio: ["ignore", "pipe", "pipe"],
    });
    out.wdioPid = child.pid ?? null;
    let stdout = "", stderr = "", done = false;
    child.stdout.on("data", (c) => { stdout += String(c); });
    child.stderr.on("data", (c) => { stderr += String(c); });
    let deadline = null;
    const finish = (r) => {
      if (done) return;
      done = true;
      clearTimeout(deadline);
      try { writeFileSync(wdioLog, `=== stdout ===\n${stdout}\n=== stderr ===\n${stderr}`); } catch { /* best-effort */ }
      resolveRun(r);
    };
    child.on("exit", (code, signal) => finish({ status: code, stdout, stderr, signal, timedOut: false }));
    child.on("error", (err) => finish({ status: null, stdout, stderr, signal: null, timedOut: false, spawnError: String(err?.message ?? err) }));
    deadline = setTimeout(() => {
      if (done) return;
      try {
        if (process.platform === "win32") spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], { stdio: "pipe", encoding: "utf8", timeout: 30000 });
        else child.kill("SIGKILL");
      } catch { /* kill failure recorded below */ }
      setTimeout(() => finish({ status: null, stdout, stderr, signal: null, timedOut: true }), 10000);
    }, WDIO_BUDGET_MS);
  });
  out.wdioMs = Date.now() - t0;
  out.wdioStatus = run.status;
  out.wdioSignal = run.signal ?? null;
  out.wdioTimedOut = run.timedOut ?? false;
  writeFileSync(join(cellArt, "wdio-stdout.log"), String(run.stdout ?? ""));
  writeFileSync(join(cellArt, "wdio-stderr.log"), String(run.stderr ?? ""));
  out.wdioFirstError = (() => {
    const txt = `${run.stderr ?? ""}\n${run.stdout ?? ""}`;
    const i = txt.search(/Error|FAILED|AssertionError/i);
    return i >= 0 ? txt.slice(Math.max(0, i - 200), i + 1200) : null;
  })();
  out.rendererFailure = /Unable to receive message from renderer|not connected to DevTools|disconnected.*renderer|renderer.*(crash|disconnect|died)/i.test(`${run.stderr ?? ""}\n${run.stdout ?? ""}`);

  // Post-state diff: the staged prefetch venv must NOT masquerade as UI
  // success — require a NEW candidate under the isolated HOME that differs
  // from the initial pointer. Original A01 assertions untouched.
  out.postPointer = existsSync(ptrPath) ? JSON.parse(readFileSync(ptrPath, "utf8")) : null;
  out.postVenvRoots = listVenvRoots(home);
  out.newVenvRoots = out.postVenvRoots.filter((p) => !out.preVenvRoots.includes(p));
  out.pointerChanged =
    !!out.postPointer &&
    !!out.prePointer &&
    out.postPointer.python_path !== out.prePointer.python_path &&
    out.postPointer.python_path !== pre.venvPython &&
    String(out.postPointer.environment_root ?? "").startsWith(String(home)) &&
    out.newVenvRoots.length > 0;

  out.a01Receipt = readLatest(join(stagedPluginDir, "test", "evidence", "a01-first-use.json"));
  // FULL-H gate: A01 VERIFIED + journey VERIFIED with all steps ok +
  // pointer-change proven from the A01 receipt's OWN pointer (case
  // completion), not the post-suite pointer later cases may rewrite.
  // Final runtime post-state recorded separately above.
  out.mode = FULL_MODE ? "full-h" : "a01";
  out.reporterCounts = countReporter(run.stdout ?? "");
  if (!FULL_MODE) {
    out.ok = run.status === 0 && !!out.a01Receipt && out.a01Receipt.status === "VERIFIED" && out.pointerChanged === true;
    out.stage = out.ok ? "verified" : "failed";
    if (!out.a01Receipt) out.note = "no A01 VERIFIED receipt: 0 tests/skipped/missing receipt cannot PASS";
    else if (out.a01Receipt.status !== "VERIFIED") out.note = `receipt status=${out.a01Receipt.status}: cannot PASS`;
    else if (!out.pointerChanged) out.note = "pointer unchanged or outside isolated HOME: staged venv masquerade blocked";
  } else {
    const journey = readLatest(join(stagedPluginDir, "test", "evidence", "first-use-journey.json"));
    out.journeyReceipt = journey;
    const steps = Array.isArray(journey?.steps) ? journey.steps : [];
    const stepsOk = steps.length > 0 && steps.every((s) => s.ok === true);
    const a01ptr = out.a01Receipt?.pointer ?? null;
    const a01PointerChanged =
      !!a01ptr &&
      !!out.prePointer &&
      a01ptr.pythonPath !== out.prePointer.python_path &&
      a01ptr.pythonPath !== pre.venvPython &&
      String(a01ptr.environmentRoot ?? "").startsWith(String(home));
    out.a01PointerChanged = a01PointerChanged;
    out.journeyStepsOk = stepsOk;
    out.ok =
      run.status === 0 &&
      !!out.a01Receipt && out.a01Receipt.status === "VERIFIED" &&
      !!journey && journey.status === "VERIFIED" && stepsOk && steps.length > 0 &&
      a01PointerChanged === true;
    out.stage = out.ok ? "verified" : "failed";
    if (!out.a01Receipt || out.a01Receipt.status !== "VERIFIED") out.note = "A01 receipt missing/not VERIFIED: full-H cannot be green";
    else if (!journey || journey.status !== "VERIFIED" || !stepsOk || steps.length === 0) out.note = "journey gate missing/not VERIFIED/steps not all ok: full-H cannot be green (pending/skipped is not a pass)";
    else if (!a01PointerChanged) out.note = "A01-case pointer unchanged: staged venv masquerade blocked";
  }
  // Preserve ALL original JSON evidence (not only the A01 embedded copy):
  // staged test/evidence -> own artifact cells/<tag>/original-evidence,
  // at finish even on failure.
  try {
    const src = join(stagedPluginDir, "test", "evidence");
    const dst = join(cellArt, "original-evidence");
    if (existsSync(src)) cpSync(src, dst, { recursive: true });
    out.originalEvidence = existsSync(dst) ? `original-evidence (${readdirSync(dst).length} files)` : "unavailable: staged evidence dir missing";
  } catch (err) {
    out.originalEvidence = `copy failed: ${String(err?.message ?? err).slice(0, 160)}`;
  }
} catch (err) {
  out.error = String(err?.stack ?? err).slice(0, 1000);
} finally {
  // Ordered teardown, owned paths only (never broad imagename kills):
  //  1. taskkill the OWNED wdio root PID /T /F (tree, children included).
  //  2. Sweep processes matching the BOUND service paths from the afterTest
  //     snapshot (actual --user-data-dir + openVault + HOME basename).
  //     The CIM query EXCLUDES this script's own PID and its parent node
  //     PID: our command line contains the bound markers and could match
  //     itself. Remaining matches are re-queried after Stop; nonzero
  //     remainder means cleanup is NOT confirmed.
  //  3. Firewall removal ONLY after children are confirmed stopped;
  //     fail-closed: rules stay when confirmation fails (the ephemeral job
  //     teardown resets the host). No green cleanup claims.
  const cleanup = { wdioTree: null, boundSweep: null, boundVerify: null, firewall: null };
  let childrenConfirmedStopped = false;
  try {
    if (out.wdioPid && process.platform === "win32") {
      const r = spawnSync("taskkill", ["/PID", String(out.wdioPid), "/T", "/F"], { stdio: "pipe", encoding: "utf8", timeout: 30000 });
      cleanup.wdioTree = `taskkill pid=${out.wdioPid} status=${r.status} out=${String(r.stdout ?? r.stderr ?? "").trim().slice(0, 120)}`;
    } else cleanup.wdioTree = `skipped: ${out.wdioPid ? "non-windows" : "no wdio pid (spawn failed before start)"}`;
  } catch (err) {
    cleanup.wdioTree = `kill failed: ${String(err?.message ?? err).slice(0, 160)}`;
  }
  try {
    let snap = null;
    try { snap = JSON.parse(readFileSync(join(cellArt, "a01-aftertest-snapshot.json"), "utf8")); } catch { snap = null; }
    const markers = [snap?.userDataDir, snap?.openVault, home ? home.slice(-24) : null].filter((m) => typeof m === "string" && m.length > 0);
    out.boundPaths = { userDataDir: snap?.userDataDir ?? null, openVault: snap?.openVault ?? null, snapshot: snap ? "a01-aftertest-snapshot.json" : "unavailable: hook never ran (NOT no-crash)" };
    if (markers.length > 0 && process.platform === "win32") {
      const selfPid = process.pid;
      const parentPid = process.ppid;
      const cond = markers.map((m) => `$_.CommandLine -like '*${String(m).replace(/'/g, "''")}*'`).join(" -or ");
      const excl = `$_.ProcessId -ne $PID -and $_.ProcessId -ne ${selfPid} -and $_.ProcessId -ne ${parentPid}`;
      const r = spawnSync("powershell", ["-NoProfile", "-Command", `$ErrorActionPreference='Stop'; Get-CimInstance Win32_Process | Where-Object { (${cond}) -and ${excl} } | Stop-Process -Force -ErrorAction SilentlyContinue; 'swept'`], { stdio: "pipe", encoding: "utf8", timeout: 30000 });
      cleanup.boundSweep = `markers=${markers.length} self=${selfPid} parent=${Number.isFinite(parentPid) ? parentPid : "?"} status=${r.status} out=${String(r.stdout ?? "").trim().slice(0, 80)}`;
      const v = spawnSync("powershell", ["-NoProfile", "-Command", `$ErrorActionPreference='Stop'; @(Get-CimInstance Win32_Process | Where-Object { (${cond}) -and ${excl} }).Count`], { stdio: "pipe", encoding: "utf8", timeout: 30000 });
      const countText = String(v.stdout ?? "").trim();
      const remaining = /^\d+$/.test(countText) ? Number(countText) : NaN;
      cleanup.boundVerify = `remaining=${Number.isFinite(remaining) ? remaining : "?"} status=${v.status}`;
      childrenConfirmedStopped = v.status === 0 && remaining === 0;
    } else cleanup.boundSweep = `skipped: ${markers.length === 0 ? "no bound markers (hook missing AND no home)" : "non-windows"}`;
  } catch (err) {
    cleanup.boundSweep = `sweep failed: ${String(err?.message ?? err).slice(0, 160)}`;
  }
  if (process.platform !== "win32") childrenConfirmedStopped = true;
  if (childrenConfirmedStopped) {
    firewallRemove();
    cleanup.firewall = "removed-own-rules-after-children-confirmed-stopped";
  } else {
    cleanup.firewall = "KEPT: children not confirmed stopped — ephemeral job teardown resets the host";
    out.ok = false;
    out.stage = "cleanup-blocked";
    out.note = [out.note, "cleanup unconfirmed: firewall rules kept"].filter(Boolean).join("; ");
  }
  out.cleanup = cleanup;
  out.cleanupOrder = "wdio-tree-then-bound-sweep-verify-then-conditional-firewall-remove";
}
out.egressFirewall = fw;
out.ts = new Date().toISOString();
mkdirSync(join(ART, "cells", TAG), { recursive: true });
writeFileSync(join(ART, `result-${TAG}.json`), JSON.stringify(out, null, 2));
console.log(JSON.stringify({ tag: TAG, ok: out.ok, stage: out.stage, rendererFailure: out.rendererFailure ?? false, note: out.note ?? out.error ?? null }));
if (!out.ok) process.exit(1);
