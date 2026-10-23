// A01 prefetch (network allowed): stage ONE baseline archive, mirror the
// formal-H metadata-only transform (2.0.0rc5 -> 2.0.0rc5.post1) inside the
// STAGED copy only, npm ci + build the STAGED plugin (tracked source is
// never modified), rebuild the wheel, and pre-download ALL dependencies for
// the ACTUAL discovery-selected interpreter into a per-baseline wheelhouse.
// Host binaries come from the EXISTING h-fixed-ab prefetch (host-pins.json);
// this script re-verifies their hashes and records the artifact binding.
//
//   node scripts/diagnostics/a01-prefetch.mjs [new|old]   (default: new)
//
// Writes a01-artifacts/prefetch-<tag>.json with: ref SHA, pre/post stamp
// hashes, wheel/source SHAs, host hash recheck, full Win driver set,
// interpreter identity (discovery selection + actual no-args probe:
// --version, sys.executable, sys._base_executable), staged bundle hashes,
// wheelhouse path. Tracked product source is never modified.
// No editable installs. Fixture-builder network calls are NONE outside this
// package-prefetch phase; the vault build runs with fail keyring +
// isolated HOME, never the user-global environment.
import { execFileSync, spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const ART = join(REPO_ROOT, "a01-artifacts");
const H_PREFETCH = join(REPO_ROOT, "h-fixed-ab-artifacts", "prefetch");
const TAG = process.argv[2] ?? "new";
const REF = TAG === "old"
  ? "ba666a57e81ca7094c46467547a34623b646890e"
  : "a856f84f6bac666cebe22226110530133f489e33";
const VERSION = "2.0.0rc5";
const STAMPED = "2.0.0rc5.post1";

function sh(cmd, args, opts = {}) {
  return execFileSync(cmd, args, { encoding: "utf8", stdio: "pipe", ...opts }).trim();
}
function sha256File(p) {
  return createHash("sha256").update(readFileSync(p)).digest("hex");
}
function resolveNpmCli(checkoutPluginDir) {
  if (process.env.npm_execpath && existsSync(process.env.npm_execpath)) return process.env.npm_execpath;
  const execDir = dirname(process.execPath);
  for (const c of [join(execDir, "node_modules", "npm", "bin", "npm-cli.js"), join(execDir, "..", "lib", "node_modules", "npm", "bin", "npm-cli.js")]) {
    if (existsSync(c)) return c;
  }
  throw new Error("npm-cli.js not found; refusing shell fallback");
}
function npmSh(args, opts = {}) {
  return execFileSync(process.execPath, [resolveNpmCli(), ...args], { encoding: "utf8", stdio: "pipe", ...opts }).trim();
}

// Product discovery (managed-runtime.ts discoverInterpreter, win32) returns
// only a path: installOnce executes `discovered.path` with `-m venv`, the
// per-candidate args are NOT propagated. So the REAL installer interpreter
// is `sel.cmd` WITHOUT args: probe THAT for >= 3.11 and record both the
// discovery selection and the actual executable identity.
function selectInterpreter() {
  const chain = process.platform === "win32"
    ? [["py", ["-3"]], ["py", ["-3.11"]], ["python", []]]
    : [["/usr/bin/python3", []], ["python3", []]];
  const probed = [];
  for (const [cmd, args] of chain) {
    let out = null;
    try {
      out = sh(cmd, [...args, "--version"]);
    } catch {
      probed.push({ selection: `${cmd} ${args.join(" ")}`.trim(), ok: false });
      continue;
    }
    probed.push({ selection: `${cmd} ${args.join(" ")}`.trim(), ok: true, version: out.trim() });
    let actual = null;
    try {
      actual = sh(cmd, ["--version"]);
    } catch {
      continue;
    }
    const m = actual.match(/(\d+)\.(\d+)\.(\d+)/);
    const ok = !!m && (Number(m[1]) > 3 || (Number(m[1]) === 3 && Number(m[2]) >= 11));
    if (ok) return { cmd, args, actualVersion: actual.trim(), probed };
  }
  throw new Error(`no python3.11+ installer interpreter: ${JSON.stringify(probed)}`);
}

const receipt = { tag: TAG, ref: REF, ok: false, stage: "start" };
try {
  mkdirSync(ART, { recursive: true });
  const head = sh("git", ["rev-parse", REF], { cwd: REPO_ROOT });
  if (head !== REF) throw new Error(`ref moved: ${REF} -> ${head}`);
  receipt.head = head;

  // 0. Host pins from the EXISTING h-fixed-ab prefetch: re-verify hashes
  //    (installer/app/driver) + record the full Win driver cache set.
  receipt.stage = "host-recheck";
  const pins = JSON.parse(readFileSync(join(H_PREFETCH, "host-pins.json"), "utf8"));
  receipt.hostRecheck = [];
  for (const [label, file, want] of [["installer", pins.binaryPath, pins.binarySha256], ["asar", pins.appPath, pins.appSha256], ["driver", pins.driverPath, pins.driverSha256]]) {
    const got = sha256File(file);
    if (got !== want) throw new Error(`host drift: ${label} ${got} != pinned ${want}`);
    receipt.hostRecheck.push({ label, file, sha256: got, match: true });
  }
  const cacheDir = join(REPO_ROOT, "h-fixed-ab-artifacts", ".obsidian-cache");
  receipt.winDriverCache = readdirSync(cacheDir);
  const noDrivers = receipt.winDriverCache.filter((n) => /chromedriver|driver/i.test(n));
  if (noDrivers.length === 0) throw new Error(`no cached Win drivers in ${cacheDir}: ${receipt.winDriverCache.join(",")}`);
  receipt.appVersion = pins.appVersion;
  receipt.installerVersion = pins.installerVersion;
  receipt.chrome = pins.chrome;

  // 1. Archive + extract with Python zipfile (native tar misses Unicode fixture).
  //    Assert the ACTUAL source hash covers the Chinese export + OCR + PDF
  //    fixtures BEFORE spending CI on the wheelhouse.
  receipt.stage = "archive";
  const stage = join(ART, `stage-${TAG}`);
  rmSync(stage, { recursive: true, force: true });
  mkdirSync(stage, { recursive: true });
  const archive = join(ART, `src-${TAG}.zip`);
  sh("git", ["archive", "--format=zip", REF, "-o", archive], { cwd: REPO_ROOT });
  receipt.sourceArchiveSha256 = sha256File(archive);
  const py0 = process.env.PF_DIAGNOSTIC_PYTHON ?? "python";
  sh(py0, ["-c", "import sys,zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])", archive, stage]);
  for (const f of ["tests/sandbox/exports/\u9aa8\u79d1.json", "paperforge/plugin/test/fixtures/build_e2e_vault.py"]) {
    if (!existsSync(join(stage, f))) throw new Error(`archived source fixture missing: ${f}`);
  }
  const ocrDir = join(stage, "tests", "sandbox", "ocr-complete", "TSTONE001");
  const pdfFile = join(stage, "tests", "sandbox", "TestZoteroData", "storage", "TSTONE001", "TSTONE001.pdf");
  if (!existsSync(ocrDir) || readdirSync(ocrDir).length === 0) throw new Error("archived OCR fixture missing/empty");
  if (!existsSync(pdfFile)) throw new Error("archived canonical PDF fixture missing");

  // 2. Metadata-only stamp in the STAGED copy (mirrors formal H; tracked
  //    source untouched). Record pre/post hashes of exactly these files.
  receipt.stage = "stamp";
  const stampFiles = [join(stage, "paperforge", "__init__.py"), join(stage, "paperforge", "plugin", "manifest.json")];
  receipt.stamp = { from: VERSION, to: STAMPED, files: [] };
  for (const f of stampFiles) {
    const before = sha256File(f);
    const text = readFileSync(f, "utf8");
    if (!text.includes(VERSION)) throw new Error(`stamp anchor missing in ${f}`);
    writeFileSync(f, text.replaceAll(VERSION, STAMPED));
    receipt.stamp.files.push({ file: f.slice(stage.length + 1), before, after: sha256File(f) });
  }
  for (const d of ["paperforge.egg-info", "build", "dist"]) rmSync(join(stage, d), { recursive: true, force: true });

  // 3. Interpreter identity: discovery selection + ACTUAL no-args probe.
  receipt.stage = "interpreter";
  const sel = selectInterpreter();
  receipt.discoveryChain = sel.probed;
  receipt.selectedCommand = `${sel.cmd} ${sel.args.join(" ")}`.trim();
  receipt.actualCommand = sel.cmd;
  receipt.actualVersion = sel.actualVersion;
  const probePy = spawnSync(sel.cmd, ["-c", "import sys,json; print(json.dumps({'executable':sys.executable,'base':sys._base_executable,'version':sys.version.split()[0]}))"], { encoding: "utf8" });
  if (probePy.status !== 0) throw new Error("actual interpreter probe failed");
  receipt.interpreter = JSON.parse(probePy.stdout.trim().split("\n").pop());

  // 4. npm ci + build the STAGED plugin (stamped source => fresh main.js
  //    bound to the archive, never the tracked stale bundle).
  receipt.stage = "plugin-build";
  const stagedPlugin = join(stage, "paperforge", "plugin");
  npmSh(["ci", "--no-audit", "--no-fund"], { cwd: stagedPlugin });
  npmSh(["run", "build"], { cwd: stagedPlugin });
  receipt.stagedBundle = {
    mainJsSha256: sha256File(join(stagedPlugin, "main.js")),
    manifestSha256: sha256File(join(stagedPlugin, "manifest.json")),
    manifestVersion: JSON.parse(readFileSync(join(stagedPlugin, "manifest.json"), "utf8")).version,
  };
  if (receipt.stagedBundle.manifestVersion !== STAMPED) throw new Error(`staged manifest ${receipt.stagedBundle.manifestVersion} != ${STAMPED}`);

  // 5. Wheels-only wheelhouse: first the package wheel (--no-deps), then
  //    the FULL dependency closure as wheels (`pip wheel`, never unresolved
  //    sdists that would need an online build during A01). Prefer
  //    --only-binary=:all: when the complete set is available; fall back to
  //    `pip wheel` (builds wheels NOW, while network is allowed). A final
  //    --no-index install into a SEPARATE fresh venv proves the closure.
  //    Separate wheelhouse per baseline (same filename collides).
  receipt.stage = "wheel";
  const wheelhouse = join(ART, `wheelhouse-${TAG}`);
  rmSync(wheelhouse, { recursive: true, force: true });
  mkdirSync(wheelhouse, { recursive: true });
  const wheelBuild = spawnSync(sel.cmd, ["-m", "pip", "wheel", "--no-deps", "-w", wheelhouse, stage], { encoding: "utf8", timeout: 600000 });
  if (wheelBuild.status !== 0) throw new Error(`pip wheel failed: ${String(wheelBuild.stderr).slice(-2000)}`);
  let wheels = readdirSync(wheelhouse).filter((f) => f.endsWith(".whl")).sort();
  if (wheels.length !== 1) throw new Error(`expected 1 wheel, got ${wheels.length}`);
  receipt.wheelFile = wheels[0];
  receipt.wheelSha256 = sha256File(join(wheelhouse, wheels[0]));
  if (!wheels[0].includes(STAMPED)) throw new Error(`wheel not stamped: ${wheels[0]}`);
  receipt.stage = "wheelhouse";
  const closure = spawnSync(sel.cmd, ["-m", "pip", "wheel", "--wheel-dir", wheelhouse, "--find-links", wheelhouse, "--only-binary=:all:", `paperforge[vector]==${STAMPED}`], { encoding: "utf8", timeout: 1200000 });
  if (closure.status !== 0) {
    const fallback = spawnSync(sel.cmd, ["-m", "pip", "wheel", "--wheel-dir", wheelhouse, "--find-links", wheelhouse, `paperforge[vector]==${STAMPED}`], { encoding: "utf8", timeout: 1200000 });
    if (fallback.status !== 0) throw new Error(`wheel closure failed: ${String(fallback.stderr).slice(-2000)}`);
    receipt.wheelClosureMode = "pip-wheel-build";
  } else receipt.wheelClosureMode = "only-binary";
  const leftovers = readdirSync(wheelhouse).filter((f) => !f.endsWith(".whl"));
  if (leftovers.length > 0) throw new Error(`wheelhouse has non-wheel files: ${leftovers.slice(0, 5).join(",")}`);
  receipt.wheelhouseManifest = readdirSync(wheelhouse).sort().map((f) => ({ file: f, sha256: sha256File(join(wheelhouse, f)) }));
  receipt.wheelhouse = wheelhouse;
  receipt.wheelhouseCount = receipt.wheelhouseManifest.length;

  // 6. Closure proof: SEPARATE fresh venv, --no-index offline install of
  //    the wheel, fresh-child version probe + initial .post1 pre-pointer.
  receipt.stage = "venv";
  const venvDir = join(ART, `venv-${TAG}`);
  rmSync(venvDir, { recursive: true, force: true });
  sh(sel.cmd, ["-m", "venv", venvDir]);
  const venvPy = join(venvDir, process.platform === "win32" ? "Scripts\\python.exe" : "bin/python");
  wheels = readdirSync(wheelhouse).filter((f) => f.startsWith(`paperforge-${STAMPED}-`) && f.endsWith(".whl")).sort();
  if (wheels.length !== 1) throw new Error(`expected 1 stamped package wheel, got ${wheels.length}`);
  const inst = spawnSync(venvPy, ["-m", "pip", "install", "--no-index", "--find-links", wheelhouse, `${join(wheelhouse, wheels[0])}[vector]`], { encoding: "utf8", timeout: 600000 });
  if (inst.status !== 0) throw new Error(`offline wheel install failed: ${String(inst.stderr).slice(-2000)}`);
  receipt.venvPython = venvPy;
  receipt.observedVersion = sh(venvPy, ["-c", "from importlib.metadata import version; print(version('paperforge'))"]);
  if (receipt.observedVersion !== STAMPED) throw new Error(`venv version ${receipt.observedVersion} != ${STAMPED}`);
  const childProbe = spawnSync(venvPy, ["-I", "-c", "import json; from paperforge.setup.runtime import ensure_runtime_dependencies, verify_runtime_in_child; s=ensure_runtime_dependencies(); v,o=verify_runtime_in_child(); print(json.dumps({'ok':s.ok,'verified':v,'observed':o}))"], { encoding: "utf8", timeout: 300000 });
  if (childProbe.status !== 0) throw new Error(`fresh-child probe failed: ${String(childProbe.stderr).slice(-500)}`);
  receipt.freshChildProbe = JSON.parse(childProbe.stdout.trim().split("\n").pop());
  if (!receipt.freshChildProbe.verified || receipt.freshChildProbe.observed !== STAMPED) throw new Error(`fresh-child probe not post1-verified: ${childProbe.stdout.slice(-300)}`);

  // 7. ORIGINAL vault build, no VAULT override, staged venv python, inside
  //    an isolated HOME with fail keyring (never user-global). Emits the
  //    staged test/vaults/{e2e,empty} the UI run later copies.
  receipt.stage = "vault";
  const buildHome = join(ART, `build-home-${TAG}`);
  rmSync(buildHome, { recursive: true, force: true });
  mkdirSync(buildHome, { recursive: true });
  const build = spawnSync(venvPy, [join(stage, "paperforge", "plugin", "test", "fixtures", "build_e2e_vault.py")], {
    encoding: "utf8", timeout: 900000, cwd: stage,
    env: { ...process.env, HOME: buildHome, USERPROFILE: buildHome, PYTHON_KEYRING_BACKEND: "keyring.backends.fail.Keyring", PAPERFORGE_KEYRING_BACKEND: "keyring.backends.fail.Keyring" },
  });
  if (build.status !== 0) throw new Error(`vault build failed: ${String(build.stderr ?? build.stdout).slice(-2000)}`);
  for (const v of ["test/vaults/e2e", "test/vaults/empty"]) {
    if (!existsSync(join(stage, "paperforge", "plugin", v))) throw new Error(`vault missing: ${v}`);
  }
  receipt.stage = "done";
  receipt.ok = true;
} catch (err) {
  receipt.error = String(err?.message ?? err).slice(0, 1000);
}
writeFileSync(join(ART, `prefetch-${TAG}.json`), JSON.stringify({ ...receipt, ts: new Date().toISOString() }, null, 2));
console.log(JSON.stringify({ tag: TAG, ok: receipt.ok, stage: receipt.stage, error: receipt.error ?? null }));
if (!receipt.ok) process.exit(1);
