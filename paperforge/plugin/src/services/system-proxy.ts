/**
 * Pure system-proxy parsing, Electron session proxy resolution, and child-env
 * overlay helpers.
 *
 * Intentionally contains ZERO `child_process` imports to preserve L4b
 * architecture boundaries (`child_process` stays strictly in `node-transport.ts`).
 */

export interface DetectedSystemProxy {
  proxyUrl: string | null;
  noProxy: string | null;
}

const DEFAULT_NO_PROXY = ["localhost", "127.0.0.1", "::1"];

export function mergeNoProxy(
  existing?: string | null,
  extra?: string | null
): string {
  const seen = new Set<string>();
  const out: string[] = [];
  const pushItem = (raw: string) => {
    const trimmed = raw.trim();
    if (!trimmed) return;
    const key = trimmed.toLowerCase();
    if (seen.has(key)) return;
    seen.add(key);
    out.push(trimmed);
  };
  for (const part of String(existing || "").split(",")) pushItem(part);
  for (const part of String(extra || "").split(",")) pushItem(part);
  for (const def of DEFAULT_NO_PROXY) pushItem(def);
  return out.join(",");
}

function normalizeProxyUrl(
  raw: string,
  defaultScheme: "http" | "https" | "socks5" | "socks4" = "http"
): string | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const candidate = /^[a-z0-9+.-]+:\/\//i.test(trimmed)
    ? trimmed
    : `${defaultScheme}://${trimmed}`;
  try {
    const parsed = new URL(candidate);
    if (
      parsed.protocol !== "http:" &&
      parsed.protocol !== "https:" &&
      parsed.protocol !== "socks5:" &&
      parsed.protocol !== "socks4:" &&
      parsed.protocol !== "socks:"
    ) {
      return null;
    }
    return parsed.toString().replace(/\/$/, "");
  } catch {
    return null;
  }
}

/**
 * Parse Chromium / Electron `session.resolveProxy()` strings such as:
 *   "DIRECT"
 *   "PROXY 127.0.0.1:7897; DIRECT"
 *   "HTTPS proxy.corp:8443"
 *   "SOCKS5 127.0.0.1:7897"
 *   "SOCKS4 127.0.0.1:1080"
 */
export function parseElectronProxyString(raw: string): string | null {
  for (const segment of String(raw || "").split(";")) {
    const entry = segment.trim();
    if (!entry) continue;
    // Honor a primary DIRECT rule instead of falling through to a secondary proxy.
    if (/^DIRECT$/i.test(entry)) return null;
    const parts = entry.split(/\s+/);
    if (parts.length < 2) continue;
    const keyword = parts[0].toUpperCase();
    const hostPort = parts[1];
    if (keyword === "PROXY" || keyword === "HTTP") {
      const normalized = normalizeProxyUrl(hostPort, "http");
      if (normalized) return normalized;
    } else if (keyword === "HTTPS") {
      const normalized = normalizeProxyUrl(hostPort, "https");
      if (normalized) return normalized;
    } else if (keyword === "SOCKS4") {
      const normalized = normalizeProxyUrl(hostPort, "socks4");
      if (normalized) return normalized;
    } else if (keyword === "SOCKS5" || keyword === "SOCKS") {
      const normalized = normalizeProxyUrl(hostPort, "socks5");
      if (normalized) return normalized;
    }
  }
  return null;
}

/**
 * Parse `reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings"` output.
 */
export function parseWindowsRegProxyOutput(
  stdout: string
): DetectedSystemProxy {
  let proxyEnable = false;
  let proxyServer = "";
  let proxyOverride = "";
  for (const line of String(stdout || "").split(/\r?\n/)) {
    const enableMatch = line.match(
      /^\s*ProxyEnable\s+REG_\w+\s+(0x[0-9a-fA-F]+|\d+)/i
    );
    if (enableMatch) {
      const val = enableMatch[1].toLowerCase().startsWith("0x")
        ? parseInt(enableMatch[1], 16)
        : parseInt(enableMatch[1], 10);
      proxyEnable = val === 1;
      continue;
    }
    const serverMatch = line.match(/^\s*ProxyServer\s+REG_\w+\s+(.+?)\s*$/i);
    if (serverMatch) {
      proxyServer = serverMatch[1].trim();
      continue;
    }
    const overrideMatch = line.match(
      /^\s*ProxyOverride\s+REG_\w+\s+(.+?)\s*$/i
    );
    if (overrideMatch) {
      proxyOverride = overrideMatch[1].trim();
    }
  }
  if (!proxyEnable || !proxyServer) {
    return { proxyUrl: null, noProxy: null };
  }

  let selectedProxy: string | null = null;
  if (proxyServer.includes("=")) {
    const kv = new Map<string, string>();
    for (const part of proxyServer.split(";")) {
      const eq = part.indexOf("=");
      if (eq <= 0) continue;
      kv.set(part.slice(0, eq).trim().toLowerCase(), part.slice(eq + 1).trim());
    }
    const httpsTarget = kv.get("https");
    const httpTarget = kv.get("http");
    const socksTarget = kv.get("socks");
    if (httpsTarget) {
      selectedProxy = normalizeProxyUrl(httpsTarget, "http");
    } else if (httpTarget) {
      selectedProxy = normalizeProxyUrl(httpTarget, "http");
    } else if (socksTarget) {
      selectedProxy = normalizeProxyUrl(socksTarget, "socks5");
    }
  } else {
    selectedProxy = normalizeProxyUrl(proxyServer, "http");
  }

  let noProxy: string | null = null;
  if (proxyOverride) {
    const items = proxyOverride
      .split(";")
      .map((s) => s.trim())
      .filter(Boolean)
      .flatMap((s) => (s.toLowerCase() === "<local>" ? DEFAULT_NO_PROXY : [s]));
    noProxy = mergeNoProxy(items.join(","));
  }

  return {
    proxyUrl: selectedProxy,
    noProxy: selectedProxy ? (noProxy ?? mergeNoProxy()) : null,
  };
}

/**
 * Parse `scutil --proxy` output on macOS.
 */
export function parseMacScutilProxyOutput(stdout: string): DetectedSystemProxy {
  const fields = new Map<string, string>();
  const exceptions: string[] = [];
  let inExceptions = false;

  for (const line of String(stdout || "").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (/^ExceptionsList\s*:\s*<array>\s*\{/i.test(trimmed)) {
      inExceptions = true;
      continue;
    }
    if (inExceptions) {
      if (trimmed === "}") {
        inExceptions = false;
        continue;
      }
      const exMatch = trimmed.match(/^\d+\s*:\s*(.+)$/);
      if (exMatch) exceptions.push(exMatch[1].trim());
      continue;
    }
    const kvMatch = trimmed.match(/^([A-Za-z0-9_]+)\s*:\s*(.+)$/);
    if (kvMatch) {
      fields.set(kvMatch[1], kvMatch[2].trim());
    }
  }

  let proxyUrl: string | null = null;
  if (fields.get("HTTPSEnable") === "1" && fields.get("HTTPSProxy")) {
    const host = fields.get("HTTPSProxy")!;
    const port = fields.get("HTTPSPort");
    proxyUrl = normalizeProxyUrl(port ? `${host}:${port}` : host, "http");
  } else if (fields.get("HTTPEnable") === "1" && fields.get("HTTPProxy")) {
    const host = fields.get("HTTPProxy")!;
    const port = fields.get("HTTPPort");
    proxyUrl = normalizeProxyUrl(port ? `${host}:${port}` : host, "http");
  } else if (fields.get("SOCKSEnable") === "1" && fields.get("SOCKSProxy")) {
    const host = fields.get("SOCKSProxy")!;
    const port = fields.get("SOCKSPort");
    proxyUrl = normalizeProxyUrl(port ? `${host}:${port}` : host, "socks5");
  }

  return {
    proxyUrl,
    noProxy: proxyUrl ? mergeNoProxy(exceptions.join(",")) : null,
  };
}

export function hasExplicitProxyEnv(
  env: Record<string, string | undefined> = process.env
): boolean {
  return Boolean(
    env.PAPERFORGE_PROXY?.trim() ||
    env.HTTPS_PROXY?.trim() ||
    env.https_proxy?.trim() ||
    env.HTTP_PROXY?.trim() ||
    env.http_proxy?.trim()
  );
}

/**
 * Build child-process proxy env vars without overwriting explicit user config.
 */
export function buildProxyEnvOverlay(
  proxyUrl: string | null | undefined,
  existingEnv: Record<string, string | undefined> = process.env,
  noProxyExtra?: string | null
): Record<string, string> {
  if (hasExplicitProxyEnv(existingEnv)) {
    return {};
  }
  const normalized = proxyUrl ? normalizeProxyUrl(proxyUrl, "http") : null;
  if (!normalized) {
    return {};
  }
  const mergedNoProxy = mergeNoProxy(
    existingEnv.NO_PROXY ?? existingEnv.no_proxy,
    noProxyExtra
  );
  return {
    HTTP_PROXY: normalized,
    HTTPS_PROXY: normalized,
    http_proxy: normalized,
    https_proxy: normalized,
    NO_PROXY: mergedNoProxy,
    no_proxy: mergedNoProxy,
  };
}

let _cachedSystemProxy: DetectedSystemProxy = {
  proxyUrl: null,
  noProxy: null,
};

export function setCachedSystemProxy(
  proxyUrl: string | null,
  noProxy: string | null = null
): void {
  _cachedSystemProxy = {
    proxyUrl: proxyUrl ? normalizeProxyUrl(proxyUrl, "http") : null,
    noProxy: noProxy ?? null,
  };
}

export function getCachedSystemProxy(): DetectedSystemProxy {
  return _cachedSystemProxy;
}

/**
 * Best-effort probe of Electron's Chromium proxy resolver inside Obsidian.
 * Returns `null` outside Electron or when direct connection is active.
 */
export async function resolveElectronSessionProxy(
  targetUrl = "https://github.com"
): Promise<string | null> {
  try {
    const req = (
      globalThis as unknown as {
        require?: (id: string) => unknown;
      }
    ).require;
    if (typeof req !== "function") return null;
    const electron = req("electron") as {
      remote?: {
        session?: {
          defaultSession?: {
            resolveProxy?: (url: string) => Promise<string> | string;
          };
        };
      };
      session?: {
        defaultSession?: {
          resolveProxy?: (url: string) => Promise<string> | string;
        };
      };
    };
    const resolver =
      electron?.remote?.session?.defaultSession?.resolveProxy ??
      electron?.session?.defaultSession?.resolveProxy;
    if (typeof resolver !== "function") return null;
    const raw = await resolver(targetUrl);
    return parseElectronProxyString(String(raw || ""));
  } catch {
    return null;
  }
}
