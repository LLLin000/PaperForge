/**
 * Cross-platform Native Rust Sidecar (`paperforge-daemon`) locator & downloader.
 *
 * Pure host-filesystem & HTTPS module (zero `child_process` imports — child
 * spawning stays exclusively inside `client/node-transport.ts`).
 *
 * End users NEVER need Rust (`rustc` / `cargo`) or Python pre-installed:
 * - Precompiled single-file binaries (~2-4 MB) are published per OS/arch:
 *   Windows (`x64`, `arm64`), macOS (`arm64`, `x64` ad-hoc codesigned),
 *   and Linux (`x64`, `arm64` static `musl` — zero glibc version coupling).
 * - Downloading directly via Node `https` + `fs.chmodSync(0o755)` avoids
 *   browser `com.apple.quarantine` attributes on macOS.
 */

import * as crypto from "crypto";
import * as fs from "fs";
import * as https from "https";
import * as os from "os";
import * as path from "path";
import { PAPERFORGE_GITHUB_REPO } from "./runtime-installer-launcher";

export function nativeDaemonTargetTriple(
  platform: NodeJS.Platform = process.platform,
  arch: string = process.arch
): string | null {
  const normArch =
    arch === "arm64" || arch === "aarch64"
      ? "aarch64"
      : arch === "x64" || arch === "x86_64"
        ? "x86_64"
        : null;
  if (!normArch) return null;
  if (platform === "win32") return `${normArch}-pc-windows-msvc`;
  if (platform === "darwin") return `${normArch}-apple-darwin`;
  if (platform === "linux") return `${normArch}-unknown-linux-musl`;
  return null;
}

export function nativeDaemonAssetName(
  platform: NodeJS.Platform = process.platform,
  arch: string = process.arch
): string | null {
  const triple = nativeDaemonTargetTriple(platform, arch);
  if (!triple) return null;
  const ext = platform === "win32" ? ".exe" : "";
  return `paperforge-daemon-${triple}${ext}`;
}

export function managedNativeDaemonPath(
  home: string = os.homedir(),
  platform: NodeJS.Platform = process.platform
): string {
  const exe =
    platform === "win32" ? "paperforge-daemon.exe" : "paperforge-daemon";
  return path.join(home, ".paperforge", "bin", exe);
}

export function nativeDaemonMetaFile(
  home: string = os.homedir(),
  platform: NodeJS.Platform = process.platform
): string {
  return path.join(
    path.dirname(managedNativeDaemonPath(home, platform)),
    ".daemon-meta.json"
  );
}

export interface NativeDaemonMeta {
  tag: string;
  sha256: string;
  binaryPath: string;
}

export function readNativeDaemonMeta(
  home: string = os.homedir(),
  platform: NodeJS.Platform = process.platform
): NativeDaemonMeta | null {
  try {
    const raw = fs.readFileSync(nativeDaemonMetaFile(home, platform), "utf-8");
    const parsed = JSON.parse(raw) as Partial<NativeDaemonMeta>;
    if (
      typeof parsed?.tag === "string" &&
      typeof parsed?.sha256 === "string" &&
      typeof parsed?.binaryPath === "string"
    ) {
      return {
        tag: parsed.tag,
        sha256: parsed.sha256.toLowerCase(),
        binaryPath: parsed.binaryPath,
      };
    }
  } catch {
    // Missing or unreadable metadata
  }
  return null;
}

function versionedNativeDaemonPath(
  home: string,
  platform: NodeJS.Platform,
  tag: string,
  sha256: string
): string {
  const binDir = path.dirname(managedNativeDaemonPath(home, platform));
  const safeTag = tag.replace(/[^a-zA-Z0-9._-]/g, "_");
  const shortHash = sha256.slice(0, 10).toLowerCase();
  const ext = platform === "win32" ? ".exe" : "";
  return path.join(binDir, `paperforge-daemon-${safeTag}-${shortHash}${ext}`);
}

function sha256File(filePath: string): string | null {
  try {
    const buf = fs.readFileSync(filePath);
    return crypto.createHash("sha256").update(buf).digest("hex").toLowerCase();
  } catch {
    return null;
  }
}

function pruneObsoleteDaemonBinaries(
  binDir: string,
  activeBinPath: string
): void {
  try {
    const activeName = path.basename(activeBinPath).toLowerCase();
    for (const entry of fs.readdirSync(binDir)) {
      const lower = entry.toLowerCase();
      if (!lower.startsWith("paperforge-daemon-")) continue;
      if (lower === activeName) continue;
      try {
        fs.unlinkSync(path.join(binDir, entry));
      } catch {
        // Still locked by an older process on Windows; will be reaped on next update.
      }
    }
  } catch {
    // Ignore directory read errors
  }
}

export function ensureExecutableMode(
  filePath: string,
  platform: NodeJS.Platform = process.platform
): void {
  if (platform === "win32") return;
  try {
    const st = fs.statSync(filePath);
    if ((st.mode & 0o111) === 0) {
      fs.chmodSync(filePath, 0o755);
    }
  } catch {
    // Ignore read-only volume chmod errors
  }
}

export interface ResolveNativeDaemonOptions {
  vaultPath?: string;
  explicitPath?: string | null;
  home?: string;
  platform?: NodeJS.Platform;
  arch?: string;
}

/**
 * Locate an installed or bundled native `paperforge-daemon` binary on disk.
 * Returns `null` if none is present yet or `PAPERFORGE_DISABLE_NATIVE_DAEMON=1`.
 */
export function resolveNativeDaemonBinary(
  opts: ResolveNativeDaemonOptions = {}
): string | null {
  if (process.env.PAPERFORGE_DISABLE_NATIVE_DAEMON === "1") {
    return null;
  }
  const plat = opts.platform ?? process.platform;
  const arch = opts.arch ?? process.arch;
  const home = opts.home ?? os.homedir();
  const exeName =
    plat === "win32" ? "paperforge-daemon.exe" : "paperforge-daemon";
  const assetName = nativeDaemonAssetName(plat, arch);

  const candidates: string[] = [];
  if (opts.explicitPath) {
    candidates.push(opts.explicitPath);
  }
  if (process.env.PAPERFORGE_NATIVE_DAEMON_PATH) {
    candidates.push(process.env.PAPERFORGE_NATIVE_DAEMON_PATH);
  }
  if (opts.vaultPath) {
    const pluginBinDir = path.join(
      opts.vaultPath,
      ".obsidian",
      "plugins",
      "paperforge",
      "bin"
    );
    if (assetName) candidates.push(path.join(pluginBinDir, assetName));
    candidates.push(path.join(pluginBinDir, exeName));
  }
  if (home) {
    const meta = readNativeDaemonMeta(home, plat);
    if (meta?.binaryPath) {
      candidates.push(meta.binaryPath);
    }
    candidates.push(managedNativeDaemonPath(home, plat));
  }

  for (const cand of candidates) {
    try {
      if (cand && fs.existsSync(cand) && fs.statSync(cand).isFile()) {
        ensureExecutableMode(cand, plat);
        return cand;
      }
    } catch {
      // Try next candidate
    }
  }
  return null;
}

function httpsGetBuffer(url: string, redirectsLeft = 5): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const req = https.get(
      url,
      {
        headers: { "User-Agent": "PaperForge-Obsidian-Plugin/2.0" },
        timeout: 45000,
      },
      (res) => {
        const code = res.statusCode ?? 0;
        if (
          (code === 301 || code === 302 || code === 307 || code === 308) &&
          res.headers.location
        ) {
          res.resume();
          if (redirectsLeft <= 0) {
            reject(new Error("Too many redirects"));
            return;
          }
          httpsGetBuffer(res.headers.location, redirectsLeft - 1).then(
            resolve,
            reject
          );
          return;
        }
        if (code !== 200) {
          res.resume();
          reject(new Error(`HTTP ${code} for ${url}`));
          return;
        }
        const chunks: Buffer[] = [];
        res.on("data", (c: Buffer) => chunks.push(c));
        res.on("end", () => resolve(Buffer.concat(chunks)));
        res.on("error", reject);
      }
    );
    req.on("timeout", () => {
      req.destroy(new Error(`Timeout fetching ${url}`));
    });
    req.on("error", reject);
  });
}

function parseChecksumForAsset(
  checksumsText: string,
  assetName: string
): string | null {
  for (const rawLine of checksumsText.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;
    const m = /^([a-fA-F0-9]{64})\s+\*?(.+)$/.exec(line);
    if (!m) continue;
    const filePart = path.posix.basename(m[2].trim().replace(/\\/g, "/"));
    if (filePart === assetName) {
      return m[1].toLowerCase();
    }
  }
  return null;
}

function normalizeDaemonTag(v: string): string {
  return String(v || "")
    .trim()
    .replace(/^[vV]/, "");
}

export function nativeDaemonVersionFile(
  home: string = os.homedir(),
  platform: NodeJS.Platform = process.platform
): string {
  return path.join(
    path.dirname(managedNativeDaemonPath(home, platform)),
    ".daemon-version"
  );
}

/**
 * Quietly download, SHA-256 verify, and (when checkVersionUpdate=true) hot-align
 * the prebuilt native `paperforge-daemon` binary against plugin `version` AND
 * release `checksums.txt` SHA-256 (preventing stale binaries even under the same
 * SemVer tag and avoiding Windows `.exe` lock races via versioned binary paths).
 * Never throws.
 */
export async function ensureNativeDaemonDownloaded(
  version: string,
  opts: {
    home?: string;
    platform?: NodeJS.Platform;
    arch?: string;
    checkVersionUpdate?: boolean;
    onBeforeReplace?: () => void | Promise<void>;
    fetchBuffer?: (url: string) => Promise<Buffer>;
  } = {}
): Promise<string | null> {
  const plat = opts.platform ?? process.platform;
  const arch = opts.arch ?? process.arch;
  const home = opts.home ?? os.homedir();
  const legacyDest = managedNativeDaemonPath(home, plat);
  const binDir = path.dirname(legacyDest);
  const verFile = path.join(binDir, ".daemon-version");
  const metaFile = nativeDaemonMetaFile(home, plat);
  const wantTag = normalizeDaemonTag(version);
  const fetcher = opts.fetchBuffer ?? httpsGetBuffer;

  const meta = readNativeDaemonMeta(home, plat);
  let existingPath: string | null = null;
  let installedSha: string | null = null;
  let installedTag = "";

  try {
    if (
      meta?.binaryPath &&
      fs.existsSync(meta.binaryPath) &&
      fs.statSync(meta.binaryPath).size > 0
    ) {
      ensureExecutableMode(meta.binaryPath, plat);
      existingPath = meta.binaryPath;
      installedTag = normalizeDaemonTag(meta.tag);
      // Always hash the live bytes on disk — never trust cached metadata alone,
      // so a corrupted or truncated local binary triggers automatic repair.
      installedSha = sha256File(meta.binaryPath);
    } else if (fs.existsSync(legacyDest) && fs.statSync(legacyDest).size > 0) {
      ensureExecutableMode(legacyDest, plat);
      existingPath = legacyDest;
      installedTag = fs.existsSync(verFile)
        ? normalizeDaemonTag(fs.readFileSync(verFile, "utf-8"))
        : "";
      installedSha = sha256File(legacyDest);
    }
  } catch {
    // Continue to download/update
  }

  if (existingPath && (!opts.checkVersionUpdate || !wantTag)) {
    return existingPath;
  }

  const assetName = nativeDaemonAssetName(plat, arch);
  const tag = wantTag;
  if (!assetName || !tag) return existingPath;

  const baseRelease = `https://github.com/${PAPERFORGE_GITHUB_REPO}/releases/download/${tag}`;
  const bases = [baseRelease, `https://ghfast.top/${baseRelease}`];

  for (const base of bases) {
    try {
      const checksumBuf = await fetcher(`${base}/checksums.txt`);
      const expectedSha = parseChecksumForAsset(
        checksumBuf.toString("utf-8"),
        assetName
      );
      if (!expectedSha) continue;

      // Content-addressed short-circuit: only skip download when BOTH tag AND
      // actual binary SHA-256 match the published checksums.txt!
      if (
        existingPath &&
        installedTag === tag &&
        installedSha &&
        installedSha === expectedSha
      ) {
        return existingPath;
      }

      const binBuf = await fetcher(`${base}/${assetName}`);
      const actualSha = crypto
        .createHash("sha256")
        .update(binBuf)
        .digest("hex")
        .toLowerCase();
      if (actualSha !== expectedSha) continue;

      fs.mkdirSync(binDir, { recursive: true });
      // Write to a content-addressed versioned filename so Windows NEVER fails
      // trying to overwrite a currently running `paperforge-daemon.exe`.
      const targetPath = versionedNativeDaemonPath(home, plat, tag, actualSha);
      const tmpPath = `${targetPath}.${process.pid}.${Date.now()}.tmp`;
      fs.writeFileSync(tmpPath, binBuf, { mode: 0o755 });
      ensureExecutableMode(tmpPath, plat);
      const repairingSamePath = existingPath === targetPath;
      if (repairingSamePath && opts.onBeforeReplace) {
        try {
          await opts.onBeforeReplace();
        } catch {
          // Best-effort release before repairing same-path corrupted binary
        }
      }
      try {
        fs.renameSync(tmpPath, targetPath);
      } catch {
        // Target already exists with identical content-addressed hash
        if (fs.existsSync(targetPath) && sha256File(targetPath) === actualSha) {
          try {
            fs.unlinkSync(tmpPath);
          } catch {
            // ignore
          }
        } else {
          throw new Error(`Failed to stage daemon binary at ${targetPath}`);
        }
      }
      ensureExecutableMode(targetPath, plat);

      // Atomically flip metadata pointer to the new binary BEFORE stopping old daemon
      const nextMeta: NativeDaemonMeta = {
        tag,
        sha256: actualSha,
        binaryPath: targetPath,
      };
      const metaTmp = `${metaFile}.${process.pid}.${Date.now()}.tmp`;
      fs.writeFileSync(metaTmp, JSON.stringify(nextMeta, null, 2), "utf-8");
      fs.renameSync(metaTmp, metaFile);
      try {
        fs.writeFileSync(verFile, tag, "utf-8");
      } catch {
        // Non-fatal legacy version marker write
      }

      if (existingPath && !repairingSamePath && opts.onBeforeReplace) {
        try {
          await opts.onBeforeReplace();
        } catch {
          // Best-effort old daemon shutdown after atomic pointer flip
        }
      }
      pruneObsoleteDaemonBinaries(binDir, targetPath);
      return targetPath;
    } catch {
      // Try mirror or silently stay on existing / Python fallback when offline
    }
  }
  return existingPath;
}
