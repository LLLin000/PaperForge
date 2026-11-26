/**
 * External runtime installer launcher.
 *
 * Authority split (unchanged): only the external installer creates/verifies
 * candidate environments and publishes the machine pointer. The plugin never
 * runs pip, never creates a venv, never writes the pointer — it runs the
 * installer script as a detached child and polls the published pointer.
 *
 * The script runs WITHOUT a console window: a terminal (`start`, `open -a
 * Terminal`, `x-terminal-emulator`) only exists in an interactive desktop
 * session, so headless hosts (CI, remote desktops, some sandboxes) could never
 * finish a first-use install. Output goes to `installer.log`, which the
 * wizard reads when the poll gives up.
 *
 * This module is pure command construction; the spawn itself stays in the
 * single child-process authority (`client/node-transport.ts`).
 */

import * as os from "os";
import * as path from "path";

export type RuntimeInstallerAction = "install" | "update" | "repair";

const PYTHON_PLACEHOLDER = "{{python}}";
const SAFE_VERSION_RE =
  /^[vV]?\d+(?:\.\d+){0,3}(?:[-.]?(?:alpha|beta|rc|a|b)\.?\d+)?(?:\.post\d+)?$/i;

export function assertSafeVersion(version: string): string {
  const trimmed = String(version || "").trim();
  if (!trimmed || !SAFE_VERSION_RE.test(trimmed)) {
    throw new Error(`Invalid PaperForge version string: ${String(version)}`);
  }
  return trimmed;
}

function assertSafeAction(action: RuntimeInstallerAction): RuntimeInstallerAction {
  if (action !== "install" && action !== "update" && action !== "repair") {
    throw new Error(`Invalid runtime installer action: ${String(action)}`);
  }
  return action;
}

export function quoteShellArg(
  value: string,
  platform: NodeJS.Platform = process.platform
): string {
  if (/[\r\n\0]/.test(value)) {
    throw new Error("Shell argument contains illegal control characters");
  }
  if (/^[A-Za-z0-9_./:\\-]+$/.test(value)) {
    return value;
  }
  if (platform === "win32") {
    if (value.includes('"')) {
      throw new Error("Windows shell argument cannot contain double quotes");
    }
    return `"${value.replace(/%/g, "%%")}"`;
  }
  return shSingleQuote(value);
}

function splitUnquotedAndAnd(cmd: string): [string, string | undefined] {
  let inSingle = false;
  let inDouble = false;
  for (let i = 0; i < cmd.length - 3; i++) {
    const ch = cmd[i];
    if (ch === "'" && !inDouble) {
      inSingle = !inSingle;
    } else if (ch === '"' && !inSingle) {
      inDouble = !inDouble;
    } else if (!inSingle && !inDouble && cmd.slice(i, i + 4) === " && ") {
      return [cmd.slice(0, i), cmd.slice(i + 4)];
    }
  }
  return [cmd, undefined];
}

/** The two steps the external installer runs, in order. */
export function runtimeInstallerSteps(
  action: RuntimeInstallerAction,
  version: string
): string[] {
  const safeAction = assertSafeAction(action);
  const safeVersion = assertSafeVersion(version);
  return [
    `${PYTHON_PLACEHOLDER} -m pip install --user --upgrade paperforge==${safeVersion}`,
    `${PYTHON_PLACEHOLDER} -m paperforge runtime ${safeAction} --expected-version ${safeVersion}`,
  ];
}

/** One shell line chaining the steps (fails fast on the first error). */
export function runtimeInstallerShellCommand(
  python: string,
  action: RuntimeInstallerAction,
  version: string,
  platform: NodeJS.Platform = process.platform
): string {
  const quoted = quoteShellArg(python, platform);
  return runtimeInstallerSteps(action, version)
    .map((step) => step.replace(PYTHON_PLACEHOLDER, quoted))
    .join(" && ");
}

/** The two-step installer command, with the bootstrap script in front. */
export function installerShellCommand(
  python: string,
  action: RuntimeInstallerAction,
  version: string,
  bootstrapPath: string,
  platform: NodeJS.Platform = process.platform
): string {
  const safeAction = assertSafeAction(action);
  const safeVersion = assertSafeVersion(version);
  const py = quoteShellArg(python, platform);
  const boot = quoteShellArg(bootstrapPath, platform);
  return [
    `${py} ${boot}`,
    `${py} -m paperforge runtime ${safeAction} --expected-version ${safeVersion}`,
  ].join(" && ");
}

/** Windows batch script — avoids every nested-quoting layer of `cmd /c`. */
export function windowsInstallerScript(shellCommand: string): string {
  const [first, second] = splitUnquotedAndAnd(shellCommand);
  const lines = [
    "@echo off",
    "@chcp 65001 >nul",
    first,
    "if errorlevel 1 goto :paperforge_failed",
  ];
  if (second) {
    lines.push(second, "if errorlevel 1 goto :paperforge_failed");
  }
  lines.push(
    "goto :paperforge_done",
    ":paperforge_failed",
    "echo.",
    "echo [PaperForge] Installer step failed. Fix the error above and retry.",
    "exit /b 1",
    ":paperforge_done",
    "echo [PaperForge] Installer finished.",
    ""
  );
  return lines.join("\r\n");
}

/** POSIX script: same fail-fast semantics and the same terminal markers. */
export function posixInstallerScript(shellCommand: string): string {
  return [
    "#!/bin/sh",
    `if ${shellCommand}; then`,
    '  echo "[PaperForge] Installer finished."',
    "else",
    '  echo "[PaperForge] Installer step failed. Fix the error above and retry."',
    "  exit 1",
    "fi",
    "",
  ].join("\n");
}

/** Markers the poll watches for, so a dead installer is detected at once. */
export const INSTALLER_FINISHED_MARKER = "[PaperForge] Installer finished.";
export const INSTALLER_FAILED_MARKER = "[PaperForge] Installer step failed.";

/**
 * Bootstrap step: make sure the PaperForge CLI that *owns* the runtime exists,
 * without reinstalling it on every launch.
 *
 * - Already importable at the requested version → no-op (the common case for
 *   anyone who installed the package with pip themselves).
 * - Externally managed interpreter (PEP 668: Debian/Ubuntu 24.04, Homebrew)
 *   → pass `--break-system-packages` for the `--user` install, which is the
 *   only documented way to install into the user site there.
 * - A source checkout or a private wheelhouse works by exporting
 *   `PIP_FIND_LINKS`; the child inherits it.
 */
export function normalizePep440Version(version: string): string {
  const cleaned = String(version || "")
    .trim()
    .replace(/^[vV]/, "");
  const m = cleaned.match(/^(\d+(?:\.\d+)*)[-.]?(alpha|beta|rc|a|b)\.?(\d+)$/i);
  if (!m) return cleaned;
  const rawPhase = m[2].toLowerCase();
  const phase =
    rawPhase === "alpha" || rawPhase === "a"
      ? "a"
      : rawPhase === "beta" || rawPhase === "b"
        ? "b"
        : "rc";
  return `${m[1]}${phase}${parseInt(m[3], 10)}`;
}

export const PAPERFORGE_GITHUB_REPO = "LLLin000/PaperForge";

export function releaseWheelFilename(version: string): string {
  const pep440 = normalizePep440Version(version);
  return pep440 ? `paperforge-${pep440}-py3-none-any.whl` : "";
}

export function releaseWheelUrl(version: string, useMirror = false): string {
  const cleanTag = version.trim().replace(/^[vV]/, "");
  const pep440 = normalizePep440Version(version);
  const tag = cleanTag || pep440;
  const whl = releaseWheelFilename(version);
  if (!tag || !whl) return "";
  const direct = `https://github.com/${PAPERFORGE_GITHUB_REPO}/releases/download/${tag}/${whl}`;
  return useMirror ? `https://ghfast.top/${direct}` : direct;
}

export function releaseChecksumsUrl(version: string): string {
  const cleanTag = assertSafeVersion(version).replace(/^[vV]/, "");
  const pep440 = normalizePep440Version(cleanTag);
  const tag = cleanTag || pep440;
  return tag
    ? `https://github.com/${PAPERFORGE_GITHUB_REPO}/releases/download/${tag}/checksums.txt`
    : "";
}

export function bootstrapPythonSource(version: string): string {
  const safeVersion = assertSafeVersion(version);
  const pepVersion = normalizePep440Version(safeVersion);
  const wheelName = releaseWheelFilename(safeVersion);
  const checksumsUrl = releaseChecksumsUrl(safeVersion);
  const ghWheelUrl = releaseWheelUrl(safeVersion, false);
  const mirrorWheelUrl = releaseWheelUrl(safeVersion, true);
  return `"""Bootstrap the PaperForge CLI; the CLI owns the runtime install itself.

Generated by the plugin. Prints human-readable progress to the installer log.
"""
import hashlib
import io
import os
import pathlib
import re
import subprocess
import sys
import sysconfig
import urllib.request
import zipfile

VERSION = ${JSON.stringify(pepVersion)}
WHEEL_NAME = ${JSON.stringify(wheelName)}
CHECKSUMS_URL = ${JSON.stringify(checksumsUrl)}
WHEEL_URLS = [u for u in (${JSON.stringify(ghWheelUrl)}, ${JSON.stringify(mirrorWheelUrl)}) if u]
if os.environ.get("PAPERFORGE_PREFER_CN_MIRROR") == "1" and len(WHEEL_URLS) > 1:
    WHEEL_URLS = list(reversed(WHEEL_URLS))


def _norm_ver(v):
    if v is None:
        return None
    s = str(v).strip().lstrip("vV")
    m = re.fullmatch(r"(\\d+(?:\\.\\d+)*)[-.]?(alpha|beta|rc|a|b)\\.?(\\d+)", s, re.IGNORECASE)
    if not m:
        return s
    phase = {"alpha": "a", "a": "a", "beta": "b", "b": "b", "rc": "rc"}[m.group(2).lower()]
    return f"{m.group(1)}{phase}{int(m.group(3))}"


def _fetch_official_wheel_sha(checksums_url, wheel_name):
    if not checksums_url or not wheel_name:
        return None
    try:
        req = urllib.request.Request(
            checksums_url, headers={"User-Agent": "PaperForge-Installer/2.1"}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read(262144).decode("utf-8", errors="replace")
        for line in text.splitlines():
            m = re.match(r"^([a-fA-F0-9]{64})\\s+\\*?(.+)$", line.strip())
            if m and pathlib.PurePosixPath(m.group(2).strip().replace("\\\\", "/")).name == wheel_name:
                return m.group(1).lower()
    except Exception as exc:
        print("[PaperForge] Official checksums fetch skipped (" + str(exc) + ")", flush=True)
    return None


try:
    import paperforge
except Exception:
    installed = None
else:
    installed = _norm_ver(getattr(paperforge, "__version__", None))

if installed == VERSION:
    print("[PaperForge] CLI already installed at " + VERSION)
    raise SystemExit(0)

extra = []
try:
    marker = pathlib.Path(sysconfig.get_path("stdlib"), "EXTERNALLY-MANAGED")
    if marker.exists():
        # PEP 668 interpreter: --user is still the right target, pip just needs
        # to be told that this is deliberate.
        extra.append("--break-system-packages")
except Exception:
    pass

wheel_dir = pathlib.Path.home() / ".paperforge" / "runtime" / "cache" / "wheels"
if WHEEL_NAME and WHEEL_URLS and not os.environ.get("PIP_INDEX_URL") and not os.environ.get("PIP_FIND_LINKS"):
    wheel_path = wheel_dir / WHEEL_NAME
    expected_sha = _fetch_official_wheel_sha(CHECKSUMS_URL, WHEEL_NAME)
    if wheel_path.is_file():
        cache_ok = zipfile.is_zipfile(wheel_path)
        if cache_ok and expected_sha:
            got_sha = hashlib.sha256(wheel_path.read_bytes()).hexdigest().lower()
            cache_ok = got_sha == expected_sha
        if not cache_ok:
            print("[PaperForge] Removing invalid/unverified cached wheel", flush=True)
            wheel_path.unlink(missing_ok=True)
    if (not wheel_path.is_file() or wheel_path.stat().st_size == 0) and expected_sha:
        wheel_dir.mkdir(parents=True, exist_ok=True)
        for u in WHEEL_URLS:
            try:
                print("[PaperForge] Downloading CLI wheel from " + u + " ...", flush=True)
                req = urllib.request.Request(u, headers={"User-Agent": "PaperForge-Installer/2.1"})
                with urllib.request.urlopen(req, timeout=45) as resp:
                    raw = resp.read()
                got_sha = hashlib.sha256(raw).hexdigest().lower()
                if got_sha != expected_sha:
                    print("[PaperForge] Release wheel SHA-256 mismatch from " + u, flush=True)
                    continue
                if not zipfile.is_zipfile(io.BytesIO(raw)):
                    print("[PaperForge] Release wheel is not a valid ZIP archive", flush=True)
                    continue
                tmp = wheel_path.with_suffix(".whl.tmp")
                tmp.write_bytes(raw)
                os.replace(tmp, wheel_path)
                break
            except Exception as exc:
                print("[PaperForge] Release wheel fetch skipped (" + str(exc) + ")", flush=True)
    if wheel_path.is_file() and expected_sha:
        extra.extend(["--find-links", str(wheel_dir)])

print("[PaperForge] Installing CLI " + VERSION + " ...", flush=True)
cmd = [
    sys.executable,
    "-m",
    "pip",
    "install",
    "--user",
    "--upgrade",
    "--default-timeout=60",
    *extra,
    "paperforge==" + VERSION,
]
rc = subprocess.call(cmd)
if rc != 0 and not os.environ.get("PIP_INDEX_URL") and not os.environ.get("PIP_FIND_LINKS"):
    for idx in (
        "https://pypi.tuna.tsinghua.edu.cn/simple",
        "https://mirrors.aliyun.com/pypi/simple",
    ):
        print("[PaperForge] Retrying CLI install with mirror " + idx + " ...", flush=True)
        rc = subprocess.call(cmd + ["-i", idx])
        if rc == 0:
            break
raise SystemExit(rc)
`;
}

/** Where the detached installer writes its output. */
export function installerLogPath(home = os.homedir()): string {
  return path.join(home, ".paperforge", "runtime", "installer.log");
}

export interface InstallerRun {
  command: string;
  args: string[];
}

/**
 * Run the script directly. No `start` / Terminal.app / terminal emulator:
 * those need an interactive session and fail silently elsewhere.
 */
export function installerRun(
  platform: NodeJS.Platform,
  options: { comSpec?: string; scriptPath: string }
): InstallerRun {
  if (platform === "win32") {
    return {
      command: options.comSpec || "C:\\Windows\\System32\\cmd.exe",
      args: ["/c", options.scriptPath],
    };
  }
  return { command: "/bin/sh", args: [options.scriptPath] };
}

// ── Zero-Python uv bootstrap installer (Phase 3) ─────────────────────────────

export function uvInstallDir(home = os.homedir()): string {
  return path.join(home, ".paperforge", "runtime", "bin");
}

export function uvBinaryPath(
  home = os.homedir(),
  platform: NodeJS.Platform = process.platform
): string {
  return path.join(uvInstallDir(home), platform === "win32" ? "uv.exe" : "uv");
}

export function uvCacheDir(home = os.homedir()): string {
  return path.join(home, ".paperforge", "runtime", "cache", "uv");
}

export function uvWheelCacheDir(home = os.homedir()): string {
  return path.join(home, ".paperforge", "runtime", "cache", "wheels");
}

export function uvPythonInstallDir(home = os.homedir()): string {
  return path.join(home, ".paperforge", "runtime", "python");
}

export function uvBootstrapVenvDir(home = os.homedir()): string {
  return path.join(home, ".paperforge", "runtime", ".bootstrap-uv");
}

export interface UvInstallerOptions {
  action: RuntimeInstallerAction;
  version: string;
  home?: string;
  uvPath?: string | null;
  arch?: string;
  platform?: NodeJS.Platform;
  logPath?: string;
}

function psSingleQuote(value: string): string {
  return "'" + value.replace(/'/g, "''") + "'";
}

function shSingleQuote(value: string): string {
  return "'" + value.replace(/'/g, "'\"'\"'") + "'";
}

export const UV_VERSION = "0.13.9";

export const UV_ASSET_SHA256: Readonly<Record<string, string>> = {
  "uv-x86_64-pc-windows-msvc.zip":
    "edd61f7f5728a56cc62455386661860bdfc7bab65872f39b0c25bdcc1d8e1beb",
  "uv-aarch64-pc-windows-msvc.zip":
    "72eed595983a4d7d22d79f21065b0f4479cc7e5c7a89104bb410c8f47559a878",
  "uv-x86_64-apple-darwin.tar.gz":
    "617a3211261b0fc739562f0071aa34e9739797c510208ede8e2977c30903d041",
  "uv-aarch64-apple-darwin.tar.gz":
    "5aeca67f2283f75235de40d0bd9c0a5bbc5fce23b6d48b3bf9fa1b2db08382ca",
  "uv-x86_64-unknown-linux-gnu.tar.gz":
    "a7fbaff2b9a271d85c1bdb540941090fd1ce011797b4abeb48e4dcd39c2471d5",
  "uv-aarch64-unknown-linux-gnu.tar.gz":
    "0797542018e541a9288855df555c8077eed06f7a47d206362030480e8ecc9f3d",
};

function uvTargetTriple(platform: NodeJS.Platform, arch: string): string {
  const normArch =
    arch === "arm64" || arch === "aarch64" ? "aarch64" : "x86_64";
  if (platform === "win32") return `${normArch}-pc-windows-msvc`;
  if (platform === "darwin") return `${normArch}-apple-darwin`;
  return `${normArch}-unknown-linux-gnu`;
}

export function windowsUvInstallerScript(opts: UvInstallerOptions): string {
  const safeAction = assertSafeAction(opts.action);
  const safeVersion = assertSafeVersion(opts.version);
  const home = opts.home ?? os.homedir();
  const pep440 = normalizePep440Version(safeVersion);
  const spec = pep440 ? `paperforge[vector]==${pep440}` : "paperforge[vector]";
  const target = uvTargetTriple("win32", opts.arch ?? process.arch);
  const assetName = `uv-${target}.zip`;
  const expectedSha = UV_ASSET_SHA256[assetName] ?? "";
  const binDir = uvInstallDir(home);
  const uvDest = uvBinaryPath(home, "win32");
  const cacheDir = uvCacheDir(home);
  const wheelCacheDir = uvWheelCacheDir(home);
  const pyDir = uvPythonInstallDir(home);
  const bootDir = uvBootstrapVenvDir(home);
  const logFile = opts.logPath ?? installerLogPath(home);
  const uvSeed = opts.uvPath ?? "";
  const wheelName = releaseWheelFilename(safeVersion);
  const checksumsUrl = releaseChecksumsUrl(safeVersion);
  const wheelUrl1 = releaseWheelUrl(safeVersion, false);
  const wheelUrl2 = releaseWheelUrl(safeVersion, true);

  const lines = [
    "$ErrorActionPreference = 'Stop'",
    `New-Item -ItemType Directory -Force -Path ${psSingleQuote(path.dirname(logFile))} | Out-Null`,
    `$logFile = ${psSingleQuote(logFile)}`,
    `$env:UV_CACHE_DIR = ${psSingleQuote(cacheDir)}`,
    `$env:UV_PYTHON_INSTALL_DIR = ${psSingleQuote(pyDir)}`,
    "$env:UV_LINK_MODE = 'hardlink'",
    "$env:UV_PYTHON_DOWNLOADS = 'automatic'",
    "$preferCn = ($env:PAPERFORGE_PREFER_CN_MIRROR -eq '1')",
    `New-Item -ItemType Directory -Force -Path ${psSingleQuote(binDir)} | Out-Null`,
    `New-Item -ItemType Directory -Force -Path ${psSingleQuote(cacheDir)} | Out-Null`,
    `New-Item -ItemType Directory -Force -Path ${psSingleQuote(pyDir)} | Out-Null`,
    "try {",
    `  $uvBin = ${psSingleQuote(uvSeed)}`,
    `  if (-not $uvBin -or -not (Test-Path $uvBin)) { $uvBin = ${psSingleQuote(uvDest)} }`,
    "  if (-not (Test-Path $uvBin)) {",
    `    $expectedSha = ${psSingleQuote(expectedSha)}`,
    "    if (-not $expectedSha) { throw 'No pinned SHA-256 digest for uv archive.' }",
    `    $zipPath = Join-Path $env:TEMP ('uv-' + [guid]::NewGuid().ToString('N') + '.zip')`,
    `    $extDir = Join-Path $env:TEMP ('uv-ext-' + [guid]::NewGuid().ToString('N'))`,
    `    $uvDirect = 'https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${assetName}'`,
    `    $uvMirror = 'https://ghfast.top/' + $uvDirect`,
    "    $urls = if ($preferCn) { @($uvMirror, $uvDirect) } else { @($uvDirect, $uvMirror) }",
    "    $downloaded = $false",
    "    foreach ($u in $urls) {",
    "      try {",
    "        Invoke-WebRequest -UseBasicParsing -Uri $u -OutFile $zipPath",
    "        $actualSha = (Get-FileHash -Algorithm SHA256 -Path $zipPath).Hash.ToLowerInvariant()",
    '        if ($actualSha -ne $expectedSha) { Remove-Item -Force -ErrorAction SilentlyContinue $zipPath; throw "SHA-256 mismatch from $u" }',
    "        $downloaded = $true",
    "        break",
    "      } catch {}",
    "    }",
    "    if (-not $downloaded) { throw 'Failed to download and SHA-256 verify portable uv.' }",
    "    Expand-Archive -Path $zipPath -DestinationPath $extDir -Force",
    "    $found = Get-ChildItem -Path $extDir -Recurse -Filter 'uv.exe' | Select-Object -First 1",
    "    if (-not $found) { throw 'uv.exe not found inside archive.' }",
    "    Copy-Item -Force $found.FullName $uvBin",
    "    Remove-Item -Force -ErrorAction SilentlyContinue $zipPath",
    "    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $extDir",
    "  }",
    "  $pyOk = $false",
    "  try { & $uvBin python install 3.12 2>&1 | Tee-Object -FilePath $logFile -Append | Out-Host; if ($LASTEXITCODE -eq 0) { $pyOk = $true } } catch {}",
    "  if (-not $pyOk) {",
    "    $env:UV_PYTHON_INSTALL_MIRROR = 'https://registry.npmmirror.com/-/binary/python-build-standalone'",
    "    & $uvBin python install 3.12 2>&1 | Tee-Object -FilePath $logFile -Append | Out-Host",
    "    if ($LASTEXITCODE -ne 0) { throw 'uv python install 3.12 failed.' }",
    "  }",
    `  $bootDir = ${psSingleQuote(bootDir)}`,
    "  & $uvBin venv --clear --python 3.12 $bootDir 2>&1 | Tee-Object -FilePath $logFile -Append | Out-Host",
    "  if ($LASTEXITCODE -ne 0) { throw 'uv venv failed.' }",
    "  $bootPy = Join-Path $bootDir 'Scripts\\python.exe'",
    `  $wheelDir = ${psSingleQuote(wheelCacheDir)}`,
    "  New-Item -ItemType Directory -Force -Path $wheelDir | Out-Null",
    `  $wheelName = ${psSingleQuote(wheelName)}`,
    `  $checksumsUrl = ${psSingleQuote(checksumsUrl)}`,
    "  $wheelVerified = $false",
    "  if ($wheelName -and $checksumsUrl) {",
    "    $wheelSha = ''",
    "    try {",
    "      $csText = (Invoke-WebRequest -UseBasicParsing -Uri $checksumsUrl -TimeoutSec 20).Content",
    "      foreach ($line in ($csText -split \"`r?`n\")) {",
    "        if ($line.Trim() -match '^([a-fA-F0-9]{64})\\s+\\*?(.+)$') {",
    "          $leaf = ($Matches[2].Trim() -split '[\\\\/]')[-1]",
    "          if ($leaf -eq $wheelName) { $wheelSha = $Matches[1].ToLowerInvariant(); break }",
    "        }",
    "      }",
    "    } catch {}",
    "    $wheelFile = Join-Path $wheelDir $wheelName",
    "    Add-Type -AssemblyName System.IO.Compression.FileSystem",
    "    if (Test-Path $wheelFile) {",
    "      $cacheOk = $false",
    "      try {",
    "        $zf = [System.IO.Compression.ZipFile]::OpenRead($wheelFile); $zf.Dispose()",
    "        if ($wheelSha) {",
    "          $curSha = (Get-FileHash -Algorithm SHA256 -Path $wheelFile).Hash.ToLowerInvariant()",
    "          $cacheOk = ($curSha -eq $wheelSha)",
    "        }",
    "      } catch { $cacheOk = $false }",
    "      if (-not $cacheOk) { Remove-Item -Force -ErrorAction SilentlyContinue $wheelFile }",
    "      else { $wheelVerified = $true }",
    "    }",
    "    if (-not (Test-Path $wheelFile) -and $wheelSha) {",
    `      $wDirect = ${psSingleQuote(wheelUrl1)}`,
    `      $wMirror = ${psSingleQuote(wheelUrl2)}`,
    "      $wheelUrls = if ($preferCn) { @($wMirror, $wDirect) } else { @($wDirect, $wMirror) }",
    "      foreach ($wu in $wheelUrls) {",
    "        if (-not $wu) { continue }",
    "        $tmpWheel = $wheelFile + '.tmp'",
    "        try {",
    "          Invoke-WebRequest -UseBasicParsing -Uri $wu -OutFile $tmpWheel",
    "          $gotSha = (Get-FileHash -Algorithm SHA256 -Path $tmpWheel).Hash.ToLowerInvariant()",
    "          if ($gotSha -ne $wheelSha) { throw \"Wheel SHA-256 mismatch from $wu\" }",
    "          $zf = [System.IO.Compression.ZipFile]::OpenRead($tmpWheel); $zf.Dispose()",
    "          Move-Item -Force $tmpWheel $wheelFile",
    "          $wheelVerified = $true",
    "          break",
    "        } catch { Remove-Item -Force -ErrorAction SilentlyContinue $tmpWheel }",
    "      }",
    "    }",
    "  }",
    `  $spec = ${psSingleQuote(spec)}`,
    "  $installed = $false",
    "  foreach ($idx in @('', 'https://pypi.tuna.tsinghua.edu.cn/simple', 'https://mirrors.aliyun.com/pypi/simple/')) {",
    "    try {",
    "      $findArgs = if ($wheelVerified -and (Test-Path (Join-Path $wheelDir '*.whl'))) { @('--find-links', $wheelDir) } else { @() }",
    "      if ($idx) { & $uvBin pip install --python $bootPy --upgrade @findArgs --index-url $idx $spec 2>&1 | Tee-Object -FilePath $logFile -Append | Out-Host }",
    "      else { & $uvBin pip install --python $bootPy --upgrade @findArgs $spec 2>&1 | Tee-Object -FilePath $logFile -Append | Out-Host }",
    "      if ($LASTEXITCODE -eq 0) { $installed = $true; break }",
    "    } catch {}",
    "  }",
    "  if (-not $installed) { throw 'uv pip install failed across mirrors.' }",
    `  & $bootPy -m paperforge runtime ${safeAction} --expected-version ${psSingleQuote(pep440 || safeVersion)} 2>&1 | Tee-Object -FilePath $logFile -Append | Out-Host`,
    "  if ($LASTEXITCODE -ne 0) { throw 'paperforge runtime command failed.' }",
    `  $done = ${psSingleQuote(INSTALLER_FINISHED_MARKER)}`,
    "  $done | Out-File -FilePath $logFile -Append -Encoding utf8",
    "  Write-Host $done",
    "} catch {",
    "  $errMsg = $_.Exception.Message",
    "  $errMsg | Out-File -FilePath $logFile -Append -Encoding utf8",
    `  $fail = ${psSingleQuote(INSTALLER_FAILED_MARKER)}`,
    "  $fail | Out-File -FilePath $logFile -Append -Encoding utf8",
    "  Write-Host $errMsg",
    "  Write-Host $fail",
    "  exit 1",
    "}",
    "",
  ];
  return lines.join("\r\n");
}

export function posixUvInstallerScript(opts: UvInstallerOptions): string {
  const safeAction = assertSafeAction(opts.action);
  const safeVersion = assertSafeVersion(opts.version);
  const home = opts.home ?? os.homedir();
  const platform = opts.platform === "darwin" ? "darwin" : "linux";
  const pep440 = normalizePep440Version(safeVersion);
  const spec = pep440 ? `paperforge[vector]==${pep440}` : "paperforge[vector]";
  const target = uvTargetTriple(platform, opts.arch ?? process.arch);
  const assetName = `uv-${target}.tar.gz`;
  const expectedSha = UV_ASSET_SHA256[assetName] ?? "";
  const binDir = uvInstallDir(home);
  const uvDest = uvBinaryPath(home, platform);
  const cacheDir = uvCacheDir(home);
  const wheelCacheDir = uvWheelCacheDir(home);
  const pyDir = uvPythonInstallDir(home);
  const bootDir = uvBootstrapVenvDir(home);
  const logFile = opts.logPath ?? installerLogPath(home);
  const uvSeed = opts.uvPath ?? "";
  const wheelName = releaseWheelFilename(safeVersion);
  const checksumsUrl = releaseChecksumsUrl(safeVersion);
  const wheelUrl1 = releaseWheelUrl(safeVersion, false);
  const wheelUrl2 = releaseWheelUrl(safeVersion, true);

  return [
    "#!/bin/sh",
    "set -eu",
    `LOG_FILE=${shSingleQuote(logFile)}`,
    `mkdir -p "$(dirname "$LOG_FILE")" ${shSingleQuote(binDir)} ${shSingleQuote(cacheDir)} ${shSingleQuote(pyDir)}`,
    `export UV_CACHE_DIR=${shSingleQuote(cacheDir)}`,
    `export UV_PYTHON_INSTALL_DIR=${shSingleQuote(pyDir)}`,
    'export UV_LINK_MODE="hardlink"',
    'export UV_PYTHON_DOWNLOADS="automatic"',
    "on_exit() {",
    "  rc=$?",
    '  if [ "$rc" -ne 0 ]; then',
    `    printf '%s\\n' ${shSingleQuote(INSTALLER_FAILED_MARKER)} >> "$LOG_FILE"`,
    `    printf '%s\\n' ${shSingleQuote(INSTALLER_FAILED_MARKER)}`,
    "  fi",
    "}",
    "trap on_exit EXIT",
    "verify_sha256() {",
    '  file="$1"; want="$2"',
    '  if [ -z "$want" ]; then return 1; fi',
    "  if command -v sha256sum >/dev/null 2>&1; then",
    '    got="$(sha256sum "$file" | awk \'{print $1}\')"',
    "  elif command -v shasum >/dev/null 2>&1; then",
    '    got="$(shasum -a 256 "$file" | awk \'{print $1}\')"',
    "  else",
    "    return 1",
    "  fi",
    '  [ "$got" = "$want" ]',
    "}",
    `UV_BIN=${shSingleQuote(uvSeed)}`,
    `if [ -z "$UV_BIN" ] || [ ! -x "$UV_BIN" ]; then UV_BIN=${shSingleQuote(uvDest)}; fi`,
    'if [ ! -x "$UV_BIN" ]; then',
    `  EXPECTED_SHA=${shSingleQuote(expectedSha)}`,
    '  TMP_DIR="$(mktemp -d)"',
    '  ARC="$TMP_DIR/uv.tar.gz"',
    `  URL_DIRECT="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${assetName}"`,
    '  URL_MIRROR="https://ghfast.top/$URL_DIRECT"',
    '  if [ "${PAPERFORGE_PREFER_CN_MIRROR:-}" = "1" ]; then',
    '    URL1="$URL_MIRROR"; URL2="$URL_DIRECT"',
    "  else",
    '    URL1="$URL_DIRECT"; URL2="$URL_MIRROR"',
    "  fi",
    '  if ! (curl -fsSL "$URL1" -o "$ARC" && verify_sha256 "$ARC" "$EXPECTED_SHA"); then',
    '    rm -f "$ARC"',
    '    curl -fsSL "$URL2" -o "$ARC"',
    '    verify_sha256 "$ARC" "$EXPECTED_SHA"',
    "  fi",
    '  tar -xzf "$ARC" -C "$TMP_DIR"',
    '  FOUND="$(find "$TMP_DIR" -type f -name uv | head -n 1)"',
    '  cp "$FOUND" "$UV_BIN" && chmod +x "$UV_BIN"',
    '  rm -rf "$TMP_DIR"',
    "fi",
    'if ! "$UV_BIN" python install 3.12 >> "$LOG_FILE" 2>&1; then',
    '  UV_PYTHON_INSTALL_MIRROR="https://registry.npmmirror.com/-/binary/python-build-standalone" "$UV_BIN" python install 3.12 >> "$LOG_FILE" 2>&1',
    "fi",
    `BOOT_DIR=${shSingleQuote(bootDir)}`,
    '"$UV_BIN" venv --clear --python 3.12 "$BOOT_DIR" >> "$LOG_FILE" 2>&1',
    'BOOT_PY="$BOOT_DIR/bin/python"',
    `WHEEL_DIR=${shSingleQuote(wheelCacheDir)}`,
    'mkdir -p "$WHEEL_DIR"',
    `WHEEL_NAME=${shSingleQuote(wheelName)}`,
    `CHECKSUMS_URL=${shSingleQuote(checksumsUrl)}`,
    'WHEEL_SHA=""',
    'WHEEL_VERIFIED=0',
    'if [ -n "$WHEEL_NAME" ] && [ -n "$CHECKSUMS_URL" ]; then',
    '  WHEEL_SHA="$(curl -fsSL --max-time 20 "$CHECKSUMS_URL" 2>/dev/null | awk -v w="$WHEEL_NAME" \'{h=$1; sub(/^\\*/, "", $2); n=split($2, a, /[\\/\\\\]/); if (a[n]==w && h ~ /^[a-fA-F0-9]{64}$/) {print tolower(h); exit}}\')" || WHEEL_SHA=""',
    '  if [ -f "$WHEEL_DIR/$WHEEL_NAME" ]; then',
    '    if ! "$BOOT_PY" -m zipfile -t "$WHEEL_DIR/$WHEEL_NAME" >/dev/null 2>&1 || [ -z "$WHEEL_SHA" ] || ! verify_sha256 "$WHEEL_DIR/$WHEEL_NAME" "$WHEEL_SHA"; then',
    '      rm -f "$WHEEL_DIR/$WHEEL_NAME"',
    "    else",
    '      WHEEL_VERIFIED=1',
    "    fi",
    "  fi",
    '  if [ ! -f "$WHEEL_DIR/$WHEEL_NAME" ] && [ -n "$WHEEL_SHA" ]; then',
    `    WURL_DIRECT=${shSingleQuote(wheelUrl1)}`,
    `    WURL_MIRROR=${shSingleQuote(wheelUrl2)}`,
    '    if [ "${PAPERFORGE_PREFER_CN_MIRROR:-}" = "1" ]; then',
    '      WURL1="$WURL_MIRROR"; WURL2="$WURL_DIRECT"',
    "    else",
    '      WURL1="$WURL_DIRECT"; WURL2="$WURL_MIRROR"',
    "    fi",
    '    (curl -fsSL "$WURL1" -o "$WHEEL_DIR/$WHEEL_NAME.tmp" && verify_sha256 "$WHEEL_DIR/$WHEEL_NAME.tmp" "$WHEEL_SHA" && "$BOOT_PY" -m zipfile -t "$WHEEL_DIR/$WHEEL_NAME.tmp" >/dev/null 2>&1 && mv "$WHEEL_DIR/$WHEEL_NAME.tmp" "$WHEEL_DIR/$WHEEL_NAME") || \\',
    '    (rm -f "$WHEEL_DIR/$WHEEL_NAME.tmp" && curl -fsSL "$WURL2" -o "$WHEEL_DIR/$WHEEL_NAME.tmp" && verify_sha256 "$WHEEL_DIR/$WHEEL_NAME.tmp" "$WHEEL_SHA" && "$BOOT_PY" -m zipfile -t "$WHEEL_DIR/$WHEEL_NAME.tmp" >/dev/null 2>&1 && mv "$WHEEL_DIR/$WHEEL_NAME.tmp" "$WHEEL_DIR/$WHEEL_NAME") || \\',
    '    rm -f "$WHEEL_DIR/$WHEEL_NAME.tmp"',
    '    if [ -f "$WHEEL_DIR/$WHEEL_NAME" ]; then WHEEL_VERIFIED=1; fi',
    "  fi",
    "fi",
    `SPEC=${shSingleQuote(spec)}`,
    'FIND_LINKS_FLAG=""',
    'if [ "$WHEEL_VERIFIED" = "1" ] && [ -n "$WHEEL_NAME" ] && [ -f "$WHEEL_DIR/$WHEEL_NAME" ]; then FIND_LINKS_FLAG="--find-links"; fi',
    'if [ -n "$FIND_LINKS_FLAG" ]; then',
    '  "$UV_BIN" pip install --python "$BOOT_PY" --upgrade --find-links "$WHEEL_DIR" "$SPEC" >> "$LOG_FILE" 2>&1 || \\',
    '    "$UV_BIN" pip install --python "$BOOT_PY" --upgrade --find-links "$WHEEL_DIR" --index-url "https://pypi.tuna.tsinghua.edu.cn/simple" "$SPEC" >> "$LOG_FILE" 2>&1 || \\',
    '    "$UV_BIN" pip install --python "$BOOT_PY" --upgrade --find-links "$WHEEL_DIR" --index-url "https://mirrors.aliyun.com/pypi/simple/" "$SPEC" >> "$LOG_FILE" 2>&1',
    "else",
    '  "$UV_BIN" pip install --python "$BOOT_PY" --upgrade "$SPEC" >> "$LOG_FILE" 2>&1 || \\',
    '    "$UV_BIN" pip install --python "$BOOT_PY" --upgrade --index-url "https://pypi.tuna.tsinghua.edu.cn/simple" "$SPEC" >> "$LOG_FILE" 2>&1 || \\',
    '    "$UV_BIN" pip install --python "$BOOT_PY" --upgrade --index-url "https://mirrors.aliyun.com/pypi/simple/" "$SPEC" >> "$LOG_FILE" 2>&1',
    "fi",
    `"$BOOT_PY" -m paperforge runtime ${safeAction} --expected-version ${shSingleQuote(pep440 || safeVersion)} >> "$LOG_FILE" 2>&1`,
    `printf '%s\\n' ${shSingleQuote(INSTALLER_FINISHED_MARKER)} >> "$LOG_FILE"`,
    `printf '%s\\n' ${shSingleQuote(INSTALLER_FINISHED_MARKER)}`,
    "",
  ].join("\n");
}

export function uvInstallerScript(opts: UvInstallerOptions): string {
  const plat = opts.platform ?? process.platform;
  return plat === "win32"
    ? windowsUvInstallerScript(opts)
    : posixUvInstallerScript(opts);
}

export function uvInstallerRun(
  platform: NodeJS.Platform,
  scriptPath: string
): InstallerRun {
  if (platform === "win32") {
    return {
      command: "powershell.exe",
      args: ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", scriptPath],
    };
  }
  return {
    command: "/bin/sh",
    args: [scriptPath],
  };
}
