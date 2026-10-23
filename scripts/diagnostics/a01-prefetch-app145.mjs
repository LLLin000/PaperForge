// Paired app-version prefetch (network allowed): downloads ONLY the second
// app asar (1.14.5) via the EXISTING obsidian-launcher (default ctor +
// shared cache), reusing the pinned installer/driver. Records both hashes
// into a01-artifacts/host-pins-app145.json. No baseline/wheelhouse rebuild.
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const ART = join(REPO_ROOT, "a01-artifacts");
const H_PREFETCH = join(REPO_ROOT, "h-fixed-ab-artifacts", "prefetch");
const CACHE = join(REPO_ROOT, "h-fixed-ab-artifacts", ".obsidian-cache");
const APP_145 = "1.14.5";

function fileUrl(p) {
  return pathToFileURL(p).href;
}
function sha256File(p) {
  return createHash("sha256").update(readFileSync(p)).digest("hex");
}
function installedVersion(pkg) {
  try {
    return JSON.parse(readFileSync(join(REPO_ROOT, "paperforge", "plugin", "node_modules", pkg, "package.json"), "utf8")).version ?? null;
  } catch {
    return null;
  }
}

const out = { app145: APP_145, ok: false, stage: "start" };
try {
  mkdirSync(ART, { recursive: true });
  const base = JSON.parse(readFileSync(join(H_PREFETCH, "host-pins.json"), "utf8"));
  if (sha256File(base.binaryPath) !== base.binarySha256) throw new Error("installer drift");
  if (sha256File(base.driverPath) !== base.driverSha256) throw new Error("driver drift");
  const launcherMod = await import("obsidian-launcher").catch(() =>
    import(fileUrl(join(REPO_ROOT, "paperforge", "plugin", "node_modules", "obsidian-launcher", "dist", "index.js")))
  );
  const ObsidianLauncher = launcherMod.default ?? launcherMod.ObsidianLauncher;
  const launcher = new ObsidianLauncher({ cacheDir: CACHE });
  const [appVersion] = await launcher.resolveVersion(APP_145, base.installerVersion);
  if (appVersion !== APP_145) throw new Error(`resolved ${appVersion} != ${APP_145}`);
  const appPath = await launcher.downloadApp(APP_145);
  out.pins = {
    appVersion: APP_145,
    installerVersion: base.installerVersion,
    binaryPath: base.binaryPath,
    binarySha256: base.binarySha256,
    appPath,
    appSha256: sha256File(appPath),
    driverPath: base.driverPath,
    driverSha256: base.driverSha256,
    launcher: installedVersion("obsidian-launcher"),
    service: installedVersion("wdio-obsidian-service"),
  };
  writeFileSync(join(ART, "host-pins-app145.json"), JSON.stringify(out.pins, null, 2));
  out.stage = "done";
  out.ok = true;
} catch (err) {
  out.error = String(err?.message ?? err).slice(0, 500);
}
writeFileSync(join(ART, "prefetch-app145.json"), JSON.stringify({ ...out, ts: new Date().toISOString() }, null, 2));
console.log(JSON.stringify({ app145: APP_145, ok: out.ok, stage: out.stage, error: out.error ?? null }));
if (!out.ok) process.exit(1);
