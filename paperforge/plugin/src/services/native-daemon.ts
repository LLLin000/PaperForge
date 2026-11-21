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
 * the prebuilt native `paperforge-daemon` binary against plugin `version`. Never throws.
 */
export async function ensureNativeDaemonDownloaded(
  version: string,
  opts: {
    home?: string;
    platform?: NodeJS.Platform;
    arch?: string;
    checkVersionUpdate?: boolean;
    onBeforeReplace?: () => void | Promise<void>;
  } = {}
): Promise<string | null> {
  const plat = opts.platform ?? process.platform;
  const arch = opts.arch ?? process.arch;
  const home = opts.home ?? os.homedir();
  const dest = managedNativeDaemonPath(home, plat);
  const verFile = path.join(path.dirname(dest), ".daemon-version");
  const wantTag = normalizeDaemonTag(version);

  let hasExisting = false;
  try {
    if (fs.existsSync(dest) && fs.statSync(dest).size > 0) {
      ensureExecutableMode(dest, plat);
      hasExisting = true;
      if (!opts.checkVersionUpdate || !wantTag) {
        return dest;
      }
      const installedTag = fs.existsSync(verFile)
        ? normalizeDaemonTag(fs.readFileSync(verFile, "utf-8"))
        : "";
      if (installedTag === wantTag) {
        return dest;
      }
    }
  } catch {
    // Continue to download/update
  }

  const assetName = nativeDaemonAssetName(plat, arch);
  const tag = wantTag;
  if (!assetName || !tag) return hasExisting ? dest : null;

  const baseRelease = `https://github.com/${PAPERFORGE_GITHUB_REPO}/releases/download/${tag}`;
  const bases = [baseRelease, `https://ghfast.top/${baseRelease}`];

  for (const base of bases) {
    try {
      const checksumBuf = await httpsGetBuffer(`${base}/checksums.txt`);
      const expectedSha = parseChecksumForAsset(
        checksumBuf.toString("utf-8"),
        assetName
      );
      if (!expectedSha) continue;

      const binBuf = await httpsGetBuffer(`${base}/${assetName}`);
      const actualSha = crypto
        .createHash("sha256")
        .update(binBuf)
        .digest("hex")
        .toLowerCase();
      if (actualSha !== expectedSha) continue;

      fs.mkdirSync(path.dirname(dest), { recursive: true });
      const tmpPath = `${dest}.${process.pid}.${Date.now()}.tmp`;
      fs.writeFileSync(tmpPath, binBuf, { mode: 0o755 });
      ensureExecutableMode(tmpPath, plat);
      if (hasExisting && opts.onBeforeReplace) {
        try {
          await opts.onBeforeReplace();
        } catch {
          // Best-effort release before rename
        }
      }
      fs.renameSync(tmpPath, dest);
      ensureExecutableMode(dest, plat);
      try {
        fs.writeFileSync(verFile, tag, "utf-8");
      } catch {
        // Non-fatal metadata marker write
      }
      return dest;
    } catch {
      // Try mirror or silently stay on existing / Python fallback when offline
    }
  }
  return hasExisting ? dest : null;
}
