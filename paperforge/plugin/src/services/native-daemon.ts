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
import * as http from "http";
import * as https from "https";
import * as os from "os";
import * as path from "path";
import * as tls from "tls";
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
  checkedAt?: number;
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
        ...(typeof parsed.checkedAt === "number"
          ? { checkedAt: parsed.checkedAt }
          : {}),
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

/** Non-blocking streaming SHA-256 hash — keeps Electron UI main thread 100% responsive. */
async function sha256FileAsync(filePath: string): Promise<string | null> {
  return new Promise((resolve) => {
    try {
      const hash = crypto.createHash("sha256");
      const stream = fs.createReadStream(filePath);
      stream.on("data", (chunk) => hash.update(chunk));
      stream.on("end", () => resolve(hash.digest("hex").toLowerCase()));
      stream.on("error", () => resolve(null));
    } catch {
      resolve(null);
    }
  });
}

const REMOTE_CHECKSUM_TTL_MS = 12 * 60 * 60 * 1000; // 12h remote check throttle when local binary is intact

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

/**
 * Align the stable `~/.paperforge/bin/paperforge-daemon(.exe)` entry point with
 * the active content-addressed binary so external Agent MCP configs can bind to
 * one permanent path across upgrades without breaking on Windows `.exe` locks.
 */
export function syncStableDaemonEntry(
  targetPath: string,
  home: string = os.homedir(),
  platform: NodeJS.Platform = process.platform
): string {
  const stablePath = managedNativeDaemonPath(home, platform);
  try {
    if (!targetPath || !fs.existsSync(targetPath)) return stablePath;
    if (path.resolve(targetPath) === path.resolve(stablePath)) {
      return stablePath;
    }
    fs.mkdirSync(path.dirname(stablePath), { recursive: true });
    if (platform !== "win32") {
      const tmpLink = `${stablePath}.${process.pid}.${Date.now()}.lnk`;
      try {
        fs.symlinkSync(targetPath, tmpLink);
        fs.renameSync(tmpLink, stablePath);
        ensureExecutableMode(stablePath, platform);
      } catch {
        try {
          if (fs.existsSync(tmpLink)) fs.unlinkSync(tmpLink);
        } catch {
          // ignore
        }
      }
      return stablePath;
    }
    const tmpCopy = `${stablePath}.${process.pid}.${Date.now()}.tmp`;
    try {
      fs.copyFileSync(targetPath, tmpCopy);
      fs.renameSync(tmpCopy, stablePath);
    } catch {
      try {
        if (fs.existsSync(tmpCopy)) fs.unlinkSync(tmpCopy);
      } catch {
        // Stable exe may be held open by an active Agent MCP session; the shim
        // itself auto-forwards via `.daemon-meta.json` when launched next time.
      }
    }
  } catch {
    // Never fail daemon setup on best-effort stable shim sync
  }
  return stablePath;
}

const MAX_CHECKSUMS_BYTES = 256 * 1024;
const MAX_DAEMON_BINARY_BYTES = 32 * 1024 * 1024;

function realpathSafe(p: string): string {
  const resolved = path.resolve(p);
  try {
    return fs.realpathSync(resolved);
  } catch {
    // Walk up to the nearest existing ancestor so symlinked system prefixes
    // (e.g. `/var` -> `/private/var` on macOS) still resolve when the leaf
    // binary does not exist or was quarantined.
    const pending: string[] = [];
    let current = resolved;
    while (true) {
      const parent = path.dirname(current);
      if (parent === current) return resolved;
      pending.unshift(path.basename(current));
      current = parent;
      try {
        const realAncestor = fs.realpathSync(current);
        return path.join(realAncestor, ...pending);
      } catch {
        // Keep walking toward root until an ancestor exists.
      }
    }
  }
}

export function isManagedDaemonBinaryPath(
  binDir: string,
  candidatePath: string
): boolean {
  if (!binDir || !candidatePath) return false;
  try {
    if (fs.lstatSync(candidatePath).isSymbolicLink()) {
      return false;
    }
  } catch {
    // Non-existent file (e.g. quarantined/deleted): check canonical parent below.
  }
  const baseDir = realpathSafe(binDir);
  const resolved = realpathSafe(candidatePath);
  const rel = path.relative(baseDir, resolved);
  if (!rel || rel.startsWith("..") || path.isAbsolute(rel)) {
    return false;
  }
  const base = path.basename(resolved).toLowerCase();
  return base.startsWith("paperforge-daemon");
}

function isValidSha256Hex(sha: string | undefined | null): sha is string {
  return typeof sha === "string" && /^[a-f0-9]{64}$/i.test(sha.trim());
}

function unlinkQuiet(filePath: string | null | undefined): void {
  if (!filePath) return;
  try {
    if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
  } catch {
    // Best-effort temp cleanup
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
  if (opts.vaultPath && process.env.PAPERFORGE_ALLOW_VAULT_DAEMON === "1") {
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
    const binDir = path.dirname(managedNativeDaemonPath(home, plat));
    const meta = readNativeDaemonMeta(home, plat);
    if (
      meta?.binaryPath &&
      isManagedDaemonBinaryPath(binDir, meta.binaryPath) &&
      isValidSha256Hex(meta.sha256)
    ) {
      try {
        if (
          fs.existsSync(meta.binaryPath) &&
          fs.statSync(meta.binaryPath).isFile() &&
          sha256File(meta.binaryPath) === meta.sha256.toLowerCase()
        ) {
          candidates.push(meta.binaryPath);
        }
      } catch {
        // Ignore unreadable/tampered meta target
      }
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

function matchesNoProxy(
  hostname: string,
  noProxyRaw: string | undefined
): boolean {
  if (!noProxyRaw) return false;
  const host = hostname.toLowerCase();
  for (const rawEntry of noProxyRaw.split(",")) {
    const entry = rawEntry.trim().toLowerCase();
    if (!entry) continue;
    if (entry === "*") return true;
    const clean = entry.replace(/:\d+$/, "");
    if (clean.startsWith(".")) {
      if (host.endsWith(clean) || host === clean.slice(1)) return true;
    } else if (host === clean || host.endsWith(`.${clean}`)) {
      return true;
    }
  }
  return false;
}

export function resolveProxyForUrl(
  targetUrl: string,
  env: Record<string, string | undefined> = process.env
): URL | null {
  let parsedTarget: URL;
  try {
    parsedTarget = new URL(targetUrl);
  } catch {
    return null;
  }
  const noProxy = env.NO_PROXY ?? env.no_proxy;
  if (matchesNoProxy(parsedTarget.hostname, noProxy)) {
    return null;
  }
  const rawProxy =
    env.PAPERFORGE_PROXY ||
    env.HTTPS_PROXY ||
    env.https_proxy ||
    env.HTTP_PROXY ||
    env.http_proxy ||
    "";
  const trimmed = rawProxy.trim();
  if (!trimmed) return null;
  try {
    const normalized = /^[a-z]+:\/\//i.test(trimmed)
      ? trimmed
      : `http://${trimmed}`;
    const proxyUrl = new URL(normalized);
    if (proxyUrl.protocol !== "http:" && proxyUrl.protocol !== "https:") {
      return null;
    }
    return proxyUrl;
  } catch {
    return null;
  }
}

function openProxyTunnel(
  proxyUrl: URL,
  targetHost: string,
  targetPort: number,
  timeoutMs: number
): Promise<tls.TLSSocket> {
  return new Promise((resolve, reject) => {
    const proxyPort =
      Number(proxyUrl.port) || (proxyUrl.protocol === "https:" ? 443 : 80);
    const headers: Record<string, string> = {
      Host: `${targetHost}:${targetPort}`,
    };
    if (proxyUrl.username || proxyUrl.password) {
      const creds = Buffer.from(
        `${decodeURIComponent(proxyUrl.username)}:${decodeURIComponent(proxyUrl.password)}`
      ).toString("base64");
      headers["Proxy-Authorization"] = `Basic ${creds}`;
    }
    const requester =
      proxyUrl.protocol === "https:" ? https.request : http.request;
    const req = requester({
      host: proxyUrl.hostname,
      port: proxyPort,
      method: "CONNECT",
      path: `${targetHost}:${targetPort}`,
      headers,
      timeout: timeoutMs,
    });
    req.on("connect", (res, socket) => {
      if (res.statusCode !== 200) {
        socket.destroy();
        reject(new Error(`Proxy CONNECT failed with HTTP ${res.statusCode}`));
        return;
      }
      const tlsSock = tls.connect({
        socket,
        servername: targetHost,
      });
      tlsSock.once("error", reject);
      resolve(tlsSock);
    });
    req.on("timeout", () => {
      req.destroy(new Error(`Proxy CONNECT timeout to ${proxyUrl.hostname}`));
    });
    req.on("error", reject);
    req.end();
  });
}

export async function httpsGetBuffer(
  url: string,
  redirectsLeft = 5,
  timeoutMs = 15000,
  maxBytes = MAX_DAEMON_BINARY_BYTES,
  env: Record<string, string | undefined> = process.env
): Promise<Buffer> {
  let parsedUrl: URL;
  try {
    parsedUrl = new URL(url);
  } catch {
    throw new Error(`Invalid URL: ${url}`);
  }
  if (parsedUrl.protocol !== "https:") {
    throw new Error(`Refusing non-HTTPS URL: ${parsedUrl.protocol}`);
  }

  const proxyUrl = resolveProxyForUrl(parsedUrl.toString(), env);
  const targetPort = Number(parsedUrl.port) || 443;
  const tunnelSocket = proxyUrl
    ? await openProxyTunnel(proxyUrl, parsedUrl.hostname, targetPort, timeoutMs)
    : null;

  return new Promise((resolve, reject) => {
    const reqOpts: https.RequestOptions = tunnelSocket
      ? {
          hostname: parsedUrl.hostname,
          port: targetPort,
          path: parsedUrl.pathname + parsedUrl.search,
          headers: {
            Host: parsedUrl.host,
            "User-Agent": "PaperForge-Obsidian-Plugin/2.0",
          },
          agent: false,
          createConnection: () => tunnelSocket,
          timeout: timeoutMs,
        }
      : {
          headers: { "User-Agent": "PaperForge-Obsidian-Plugin/2.0" },
          timeout: timeoutMs,
        };

    const handleResponse = (res: http.IncomingMessage) => {
      const code = res.statusCode ?? 0;
      if (
        (code === 301 || code === 302 || code === 307 || code === 308) &&
        res.headers.location
      ) {
        res.resume();
        tunnelSocket?.destroy();
        if (redirectsLeft <= 0) {
          reject(new Error("Too many redirects"));
          return;
        }
        let nextUrl: URL;
        try {
          nextUrl = new URL(res.headers.location, parsedUrl);
        } catch {
          reject(new Error("Invalid redirect URL"));
          return;
        }
        if (nextUrl.protocol !== "https:") {
          reject(
            new Error(`Refusing non-HTTPS redirect to ${nextUrl.protocol}`)
          );
          return;
        }
        httpsGetBuffer(
          nextUrl.toString(),
          redirectsLeft - 1,
          timeoutMs,
          maxBytes,
          env
        ).then(resolve, reject);
        return;
      }
      if (code !== 200) {
        res.resume();
        tunnelSocket?.destroy();
        reject(new Error(`HTTP ${code} for ${parsedUrl.toString()}`));
        return;
      }
      const contentLen = Number(res.headers["content-length"]);
      if (Number.isFinite(contentLen) && contentLen > maxBytes) {
        res.destroy();
        tunnelSocket?.destroy();
        reject(
          new Error(
            `Response size ${contentLen} exceeds maximum allowed ${maxBytes} bytes`
          )
        );
        return;
      }
      const chunks: Buffer[] = [];
      let totalBytes = 0;
      let aborted = false;
      res.on("data", (c: Buffer) => {
        if (aborted) return;
        totalBytes += c.length;
        if (totalBytes > maxBytes) {
          aborted = true;
          res.destroy();
          tunnelSocket?.destroy();
          reject(
            new Error(`Response exceeded maximum allowed ${maxBytes} bytes`)
          );
          return;
        }
        chunks.push(c);
      });
      res.on("end", () => {
        if (!aborted) resolve(Buffer.concat(chunks));
      });
      res.on("error", (err) => {
        tunnelSocket?.destroy();
        reject(err);
      });
    };

    const req = tunnelSocket
      ? https.get(reqOpts, handleResponse)
      : https.get(parsedUrl.toString(), reqOpts, handleResponse);
    req.on("timeout", () => {
      req.destroy(new Error(`Timeout fetching ${parsedUrl.toString()}`));
      tunnelSocket?.destroy();
    });
    req.on("error", (err) => {
      tunnelSocket?.destroy();
      reject(err);
    });
  });
}

function preferCnGithubMirrors(): boolean {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
    if (
      tz === "Asia/Shanghai" ||
      tz === "Asia/Chongqing" ||
      tz === "Asia/Urumqi" ||
      tz === "Asia/Harbin"
    ) {
      return true;
    }
  } catch {
    // ignore
  }
  return false;
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
    onReplace?: (swapFn: () => Promise<void> | void) => Promise<void>;
    onQuarantineSuspected?: (binDir: string) => void;
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
  const checksumFetcher =
    opts.fetchBuffer ??
    ((u: string) => httpsGetBuffer(u, 5, 10000, MAX_CHECKSUMS_BYTES));
  const binaryFetcher =
    opts.fetchBuffer ??
    ((u: string) => httpsGetBuffer(u, 5, 25000, MAX_DAEMON_BINARY_BYTES));

  const meta = readNativeDaemonMeta(home, plat);
  const metaPathValid = Boolean(
    meta?.binaryPath && isManagedDaemonBinaryPath(binDir, meta.binaryPath)
  );
  let existingPath: string | null = null;
  let installedSha: string | null = null;
  let installedTag = "";
  let suspectedQuarantine = false;

  try {
    if (meta?.binaryPath && metaPathValid) {
      if (
        fs.existsSync(meta.binaryPath) &&
        fs.statSync(meta.binaryPath).size > 0
      ) {
        ensureExecutableMode(meta.binaryPath, plat);
        existingPath = meta.binaryPath;
        installedTag = normalizeDaemonTag(meta.tag);
        // Async non-blocking hash of live bytes on disk — verifies integrity
        // without freezing Electron's UI thread on a 3MB synchronous read.
        installedSha = await sha256FileAsync(meta.binaryPath);
      } else if (plat === "win32") {
        // Metadata points to a binary we previously installed, yet the .exe vanished
        // (typical Windows Defender quarantine signature).
        suspectedQuarantine = true;
      }
    }
    if (
      !existingPath &&
      fs.existsSync(legacyDest) &&
      fs.statSync(legacyDest).size > 0
    ) {
      ensureExecutableMode(legacyDest, plat);
      existingPath = legacyDest;
      installedTag = fs.existsSync(verFile)
        ? normalizeDaemonTag(fs.readFileSync(verFile, "utf-8"))
        : "";
      installedSha = await sha256FileAsync(legacyDest);
    }
  } catch {
    if (plat === "win32" && meta?.binaryPath && metaPathValid) {
      suspectedQuarantine = true;
    }
  }

  const existingCorrupted = Boolean(
    meta &&
    metaPathValid &&
    existingPath &&
    path.resolve(existingPath) === path.resolve(meta.binaryPath) &&
    (!isValidSha256Hex(meta.sha256) ||
      !installedSha ||
      installedSha !== meta.sha256.toLowerCase())
  );

  if (suspectedQuarantine) {
    try {
      opts.onQuarantineSuspected?.(binDir);
    } catch {
      // Isolate UI notification callback errors
    }
  }

  if (
    existingPath &&
    !existingCorrupted &&
    (!opts.checkVersionUpdate || !wantTag)
  ) {
    return existingPath;
  }

  // Zero-network fast path: when tag matches, live binary SHA-256 matches
  // recorded metadata (proving local bytes are uncorrupted), and we verified
  // remotely within the last 12h, skip the startup GitHub HTTPS round-trip.
  if (
    !opts.fetchBuffer &&
    existingPath &&
    !existingCorrupted &&
    meta &&
    metaPathValid &&
    installedTag === wantTag &&
    installedSha &&
    installedSha === meta.sha256 &&
    typeof meta.checkedAt === "number" &&
    Date.now() - meta.checkedAt < REMOTE_CHECKSUM_TTL_MS
  ) {
    if (!fs.existsSync(legacyDest)) {
      syncStableDaemonEntry(existingPath, home, plat);
    }
    return existingPath;
  }

  const assetName = nativeDaemonAssetName(plat, arch);
  const tag = wantTag;
  if (!assetName || !tag) return existingCorrupted ? null : existingPath;

  const baseRelease = `https://github.com/${PAPERFORGE_GITHUB_REPO}/releases/download/${tag}`;
  const cnMirrors = [
    `https://ghfast.top/${baseRelease}`,
    `https://gh-proxy.com/${baseRelease}`,
  ];
  const bases = preferCnGithubMirrors()
    ? [...cnMirrors, baseRelease]
    : [baseRelease, ...cnMirrors];

  // PF-SEC-001: Authoritative checksums.txt MUST be fetched ONLY from official
  // github.com (never from third-party mirrors), failing closed if unreachable.
  let expectedSha: string | null = null;
  try {
    const checksumBuf = await checksumFetcher(`${baseRelease}/checksums.txt`);
    expectedSha = parseChecksumForAsset(
      checksumBuf.toString("utf-8"),
      assetName
    );
  } catch {
    expectedSha = null;
  }
  if (!expectedSha) {
    return existingCorrupted ? null : existingPath;
  }

  // Content-addressed short-circuit: only skip download when BOTH tag AND
  // actual binary SHA-256 match the official published checksums.txt!
  if (
    existingPath &&
    installedTag === tag &&
    installedSha &&
    installedSha === expectedSha
  ) {
    if (meta && metaPathValid) {
      try {
        const refreshed: NativeDaemonMeta = {
          ...meta,
          checkedAt: Date.now(),
        };
        const refreshTmp = `${metaFile}.${process.pid}.${Date.now()}.tmp`;
        try {
          fs.writeFileSync(
            refreshTmp,
            JSON.stringify(refreshed, null, 2),
            "utf-8"
          );
          fs.renameSync(refreshTmp, metaFile);
        } finally {
          unlinkQuiet(refreshTmp);
        }
      } catch {
        // Best-effort timestamp refresh
      }
    }
    return existingPath;
  }

  for (const base of bases) {
    let tmpPath: string | null = null;
    let metaTmp: string | null = null;
    try {
      const binBuf = await binaryFetcher(`${base}/${assetName}`);
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
      tmpPath = `${targetPath}.${process.pid}.${Date.now()}.tmp`;
      fs.writeFileSync(tmpPath, binBuf, { mode: 0o755 });
      ensureExecutableMode(tmpPath, plat);
      const repairingSamePath =
        existingPath !== null &&
        path.resolve(existingPath) === path.resolve(targetPath);

      const promoteBinary = () => {
        try {
          fs.renameSync(tmpPath!, targetPath);
        } catch {
          // Target already exists with identical content-addressed hash
          if (
            fs.existsSync(targetPath) &&
            sha256File(targetPath) === actualSha
          ) {
            unlinkQuiet(tmpPath);
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
          checkedAt: Date.now(),
        };
        metaTmp = `${metaFile}.${process.pid}.${Date.now()}.tmp`;
        fs.writeFileSync(metaTmp, JSON.stringify(nextMeta, null, 2), "utf-8");
        fs.renameSync(metaTmp, metaFile);
        metaTmp = null;
        try {
          fs.writeFileSync(verFile, tag, "utf-8");
        } catch {
          // Non-fatal legacy version marker write
        }
      };

      if (repairingSamePath && opts.onReplace) {
        await opts.onReplace(promoteBinary);
      } else {
        if (repairingSamePath && opts.onBeforeReplace) {
          try {
            await opts.onBeforeReplace();
          } catch {
            // Best-effort release before repairing same-path corrupted binary
          }
        }
        promoteBinary();
      }

      if (existingPath && !repairingSamePath && opts.onBeforeReplace) {
        try {
          await opts.onBeforeReplace();
        } catch {
          // Best-effort old daemon shutdown after atomic pointer flip
        }
      }
      syncStableDaemonEntry(targetPath, home, plat);
      pruneObsoleteDaemonBinaries(binDir, targetPath);
      return targetPath;
    } catch {
      // Try next mirror or fail closed if corrupted
    } finally {
      unlinkQuiet(tmpPath);
      unlinkQuiet(metaTmp);
    }
  }
  return existingCorrupted ? null : existingPath;
}
