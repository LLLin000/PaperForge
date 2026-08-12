/**
 * ManagedRuntime — single, machine-local PaperForge runtime (#174 / #143).
 *
 * Public seam (Issue #77):
 *   ManagedRuntime, RuntimeHealth, RuntimeRun,
 *   resolveRuntimeCommand, runtimeActionsForHealth
 *
 * Lifecycle states:
 *   not_installed → ensure() → needs_repair / ready
 *   ready → stale cache → unknown
 *   unknown → status() → ready / needs_repair
 *   needs_repair → ensure() → ready / needs_repair
 *
 * Post-cutover scope (#174 / #143 §3): the plugin is a READER of the
 * runtime only.  It keeps discovery, platform gates, consent UX, ONE
 * one-time venv + pinned install, pointer READ and handshake/spawn.
 * DELETED: version slots, rollback, slot ensure, runtime-health checks
 * and TS pointer writes — Python owns pointer publication
 * (`~/.paperforge/runtime/pointer.json`, written by `paperforge setup`
 * after a successful install).
 */

import * as fs from "fs";
import * as path from "path";
import {
  execFile as cpExecFile,
  execFileSync as cpExecFileSync,
} from "child_process";
import * as os from "os";

// ── Public types ──

export type RuntimeState =
  | "ready"
  | "not_installed"
  | "needs_repair"
  | "unknown"
  | "unavailable";

export interface ErrorInfo {
  readonly code: string;
  readonly message: string;
  readonly platformAction: string;
}
export interface WarningInfo {
  readonly code: string;
  readonly message: string;
  readonly platformAction?: string;
}

export interface RuntimeHealth {
  readonly state: RuntimeState;
  readonly pythonPath: string | null;
  readonly version: string | null;
  readonly source: "venv" | "system" | "manual" | "none";
  readonly error: ErrorInfo | null;
  readonly lastVerifiedAt: string | null;
  readonly stale: boolean;
  readonly warnings: readonly WarningInfo[];
}

export interface StatusOptions {
  readonly allowStale?: boolean;
}

export interface EnsureOptions {
  readonly version?: string;
  readonly force?: boolean;
  readonly signal?: AbortSignal;
}

export interface RuntimeRun {
  readonly command: string;
  readonly args: readonly string[];
}

export interface RuntimeUiAction {
  readonly verb: string;
  readonly label: string;
}

export interface RuntimeAction {
  readonly id: string;
  readonly label: string;
  readonly primary: boolean;
  readonly destructive: boolean;
}

// ── Internal DI types ──

export interface FsOps {
  existsSync(p: string): boolean;
  readFileSync(p: string, encoding?: string | null): string;
  mkdirSync(p: string, opts?: { recursive?: boolean }): string | undefined;
  rmSync(p: string, opts?: { recursive?: boolean; force?: boolean }): void;
}

export type ExecFileCallback = (
  error: Error | null,
  stdout: string,
  stderr: string
) => void;
export type ExecFileFn = (
  command: string,
  args: readonly string[],
  opts: { timeout?: number; encoding?: string; signal?: AbortSignal },
  cb: ExecFileCallback
) => void;
export type ExecFileSyncFn = (
  command: string,
  args: readonly string[],
  opts: { encoding: string; timeout: number }
) => string;

// ── Constants ──

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
const MIN_PYTHON = "3.11";
const POINTER_SCHEMA_VERSION = 1;
const POINTER_FILENAME = "pointer.json";
const VENV_DIR_NAME = "venv";

/** ES2018-compatible Promise.withResolvers polyfill. */
function deferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (err: unknown) => void;
} {
  let resolve!: (value: T) => void;
  let reject!: (err: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

// ── Version helpers ──

function parsePythonVersion(output: string): string | null {
  const m = output.match(/Python\s+(\d+\.\d+(?:\.\d+)?)/);
  if (m) return m[1];
  const m2 = output.match(/Python\s+(\d+\.\d+)/);
  if (m2) return m2[1] + ".0";
  return null;
}

function compareVersions(a: string, b: string): number {
  const ap = a.split(".").map(Number);
  const bp = b.split(".").map(Number);
  for (let i = 0; i < Math.max(ap.length, bp.length); i++) {
    const an = ap[i] ?? 0;
    const bn = bp[i] ?? 0;
    if (an !== bn) return an - bn;
  }
  return 0;
}

function isAtLeast(version: string, minVersion: string): boolean {
  return compareVersions(version, minVersion) >= 0;
}

// ── Platform helpers ──

function detectContainer(): boolean {
  try {
    if (fs.existsSync("/.dockerenv")) return true;
    if (fs.existsSync("/run/.containerenv")) return true;
    const cgroup = fs.readFileSync("/proc/1/cgroup", "utf-8");
    if (
      cgroup.includes("docker") ||
      cgroup.includes("flatpak") ||
      cgroup.includes("snap")
    )
      return true;
  } catch {
    // ignore
  }
  return false;
}

function detectFlatpak(): boolean {
  return (
    process.env.FLATPAK_ID !== undefined ||
    (process.env.XDG_DATA_DIRS ?? "").includes("flatpak") ||
    false
  );
}

function detectSnap(): boolean {
  return (
    process.env.SNAP !== undefined ||
    process.env.SNAP_NAME !== undefined ||
    false
  );
}

export function getOsArch(osPlatform: string, osArch: string): string {
  const platMap: Record<string, string> = {
    win32: "windows",
    darwin: "macos",
    linux: "linux",
  };
  return `${platMap[osPlatform] ?? osPlatform}-${osArch}`;
}

/** Determine whether the current environment is containerised. Exported for testing. */
export function isContainerEnv(): boolean {
  return detectContainer();
}

/** Determine whether the current environment is Flatpak. Exported for testing. */
export function isFlatpakEnv(): boolean {
  return detectFlatpak();
}

/** Determine whether the current environment is Snap. Exported for testing. */
export function isSnapEnv(): boolean {
  return detectSnap();
}

// ── Canonical actions per health state ──

/** Return internal actions with id/primary/destructive. Used by DI tests. */
export function runtimeActionsForHealth(
  health: RuntimeHealth
): readonly RuntimeAction[];
/** Return UI actions with verb/label. Used by settings rendering. */
export function runtimeActionsForHealth(
  health: RuntimeHealth,
  targetVersion: string,
  running: boolean
): readonly RuntimeUiAction[];
export function runtimeActionsForHealth(
  health: RuntimeHealth,
  targetVersion?: string,
  running?: boolean
): readonly RuntimeAction[] | readonly RuntimeUiAction[] {
  // 3-param UI path (settings rendering)
  if (targetVersion !== undefined || running !== undefined) {
    if (running) {
      return [{ verb: "stop", label: "Stop" }];
    }
    switch (health.state) {
      case "not_installed":
        return [{ verb: "install", label: "Install Runtime" }];
      case "needs_repair":
        return [{ verb: "repair", label: "Repair Runtime" }];
      case "ready":
        return [
          { verb: "status", label: "Check Status" },
          { verb: "update", label: "Update Runtime" },
        ];
      case "unknown":
        return [{ verb: "retry", label: "Retry" }];
      case "unavailable":
        return [{ verb: "setup", label: "Manual Setup" }];
      default:
        return [{ verb: "retry", label: "Retry" }];
    }
  }

  // 1-param internal path (unchanged, for DI tests)
  switch (health.state) {
    case "not_installed":
      return [
        {
          id: "install",
          label: "Install Runtime",
          primary: true,
          destructive: false,
        },
      ];
    case "needs_repair":
      return [
        {
          id: "repair",
          label: "Repair Runtime",
          primary: true,
          destructive: false,
        },
      ];
    case "ready":
      return [
        {
          id: "status",
          label: "Check Status",
          primary: false,
          destructive: false,
        },
        {
          id: "update",
          label: "Update Runtime",
          primary: false,
          destructive: false,
        },
      ];
    case "unknown":
      return [
        {
          id: "probe",
          label: "Refresh Status",
          primary: true,
          destructive: false,
        },
      ];
    case "unavailable":
      return [
        {
          id: "setup",
          label: "Manual Setup",
          primary: true,
          destructive: false,
        },
      ];
    default:
      return [
        {
          id: "probe",
          label: "Refresh Status",
          primary: true,
          destructive: false,
        },
      ];
  }
}

// ── Resolve runtime command from health ──

export function resolveRuntimeCommand(
  health: RuntimeHealth
): RuntimeRun | null {
  if (health.state !== "ready" || !health.pythonPath) return null;
  return { command: health.pythonPath, args: [] };
}

// ── ManagedRuntime class ──

export class ManagedRuntime {
  private readonly venvDir: string;
  private readonly pointerPath: string;
  private readonly pluginVersion: string;
  private readonly osPlatform: string;
  private readonly osArch: string;
  private _cache: RuntimeHealth | null = null;
  private _cacheTime: number = 0;

  // DI: injectable fs, execFile, execFileSync for testing
  private readonly _fs: FsOps;
  private readonly _execFile: ExecFileFn;
  private readonly _execFileSync: ExecFileSyncFn;

  // Public canonical root (Issue #77)
  public readonly rootDir: string;
  /** Kept for API compatibility; post-cutover there is ONE venv, no slots. */
  public readonly triplet: string;

  constructor(opts: {
    // Old path — DI-first, full control
    runtimeDir?: string;
    pluginVersion?: string;
    // New path — auto-compute canonical root (Issue #77)
    version?: string;
    platform?: string;
    arch?: string;
    // Common overrides
    osPlatform?: string;
    osArch?: string;
    fs?: FsOps;
    execFile?: ExecFileFn;
    execFileSync?: ExecFileSyncFn;
  }) {
    const platform = opts.osPlatform ?? opts.platform ?? process.platform;
    const arch = opts.osArch ?? opts.arch ?? process.arch;
    this.osPlatform = platform;
    this.osArch = arch;
    this.triplet = `${platform}-${arch}`;

    if (opts.runtimeDir) {
      // DI path: runtimeDir is the runtime root containing pointer.json.
      this.rootDir = opts.runtimeDir;
      this.venvDir = path.join(opts.runtimeDir, VENV_DIR_NAME);
      this.pluginVersion = opts.pluginVersion ?? opts.version ?? "0.0.0";
    } else {
      const home = os.homedir();
      this.rootDir = path.join(home, ".paperforge", "runtime");
      this.venvDir = path.join(this.rootDir, VENV_DIR_NAME);
      this.pluginVersion = opts.version ?? opts.pluginVersion ?? "0.0.0";
    }

    // #174: Python is the ONLY writer of pointer.json; the plugin READS it.
    this.pointerPath = path.join(this.rootDir, POINTER_FILENAME);
    this._fs = opts.fs ?? (fs as unknown as FsOps);
    this._execFile = opts.execFile ?? (cpExecFile as unknown as ExecFileFn);
    this._execFileSync =
      opts.execFileSync ?? (cpExecFileSync as unknown as ExecFileSyncFn);
  }

  // ── Sync: fails closed on cold/stale cache ──

  current(): RuntimeHealth {
    if (!this._cache) {
      return {
        state: "unknown",
        pythonPath: null,
        version: null,
        source: "none",
        error: null,
        lastVerifiedAt: null,
        stale: true,
        warnings: [],
      };
    }
    const isStale = Date.now() - this._cacheTime > CACHE_TTL_MS;
    if (isStale) {
      // Never return 'ready' from stale cache — fail closed
      return { ...this._cache, state: "unknown", stale: true };
    }
    return { ...this._cache, stale: false };
  }

  // ── Async probe ──

  async status(opts?: StatusOptions): Promise<RuntimeHealth> {
    // Fresh cache fast-path
    if (this._cache) {
      const isStale = Date.now() - this._cacheTime > CACHE_TTL_MS;
      if (!isStale && this._cache.state === "ready") {
        return { ...this._cache, stale: false };
      }
      if (isStale && opts?.allowStale) {
        return { ...this._cache, stale: true };
      }
    }

    // Read pointer.json (schema v1, published ONLY by Python).
    let pointerPythonPath: string | null = null;
    let pointerVersion: string | null = null;
    try {
      const raw = this._fs.readFileSync(this.pointerPath, "utf-8");
      const ptr: Record<string, unknown> = JSON.parse(raw);
      if (ptr.schema_version !== POINTER_SCHEMA_VERSION) {
        throw new Error("unsupported pointer schema");
      }
      const pp = typeof ptr.python_path === "string" ? ptr.python_path : null;
      pointerPythonPath = pp ? path.resolve(pp) : null;
      pointerVersion =
        typeof ptr.paperforge_version === "string"
          ? ptr.paperforge_version
          : null;
    } catch {
      // No pointer → not installed (interrupted install ⇒ no publication ⇒
      // next handshake fails ⇒ UI offers install again, consent required).
      return this._setCache({
        state: "not_installed",
        pythonPath: null,
        version: null,
        source: "none",
        error: null,
        lastVerifiedAt: null,
        stale: false,
        warnings: [],
      });
    }

    // Pointer exists but missing pythonPath
    if (!pointerPythonPath) {
      return this._setCache({
        state: "needs_repair",
        pythonPath: null,
        version: pointerVersion,
        source: "none",
        error: {
          code: "POINTER_MISSING_PATH",
          message: "Runtime pointer has no pythonPath",
          platformAction: "Reinstall runtime",
        },
        lastVerifiedAt: null,
        stale: false,
        warnings: [],
      });
    }

    // Interpreter file missing
    if (!this._fs.existsSync(pointerPythonPath)) {
      return this._setCache({
        state: "needs_repair",
        pythonPath: pointerPythonPath,
        version: pointerVersion,
        source: "none",
        error: {
          code: "PYTHON_NOT_FOUND",
          message: "Python executable not found at pointer path",
          platformAction: "Reinstall runtime",
        },
        lastVerifiedAt: null,
        stale: false,
        warnings: [],
      });
    }

    // Run isolated import probe
    try {
      const result = await this._probe(pointerPythonPath);
      return this._setCache({
        state: "ready",
        pythonPath: pointerPythonPath,
        version: result.version ?? pointerVersion,
        source: "venv",
        error: null,
        lastVerifiedAt: new Date().toISOString(),
        stale: false,
        warnings: [],
      });
    } catch (probeErr: unknown) {
      const msg =
        probeErr instanceof Error ? probeErr.message : String(probeErr);
      return this._setCache({
        state: "needs_repair",
        pythonPath: pointerPythonPath,
        version: pointerVersion,
        source: "venv",
        error: {
          code: "PROBE_FAILED",
          message: msg,
          platformAction: "Repair runtime",
        },
        lastVerifiedAt: null,
        stale: false,
        warnings: [],
      });
    }
  }

  // ── Ensure a working runtime (ONE one-time install) ──

  async ensure(opts?: EnsureOptions): Promise<RuntimeHealth> {
    const version = opts?.version ?? this.pluginVersion;
    const force = opts?.force ?? false;
    const signal = opts?.signal;

    if (signal?.aborted) return this._abortedHealth();

    // Quick path: if already ready and not forced, just re-probe
    if (!force) {
      const cur = this.current();
      if (cur.state === "ready" && !cur.stale) {
        const probeResult = await this.status();
        if (probeResult.state === "ready") return probeResult;
      }
    }

    if (signal?.aborted) return this._abortedHealth();

    // Step 1: Resolve bootstrap Python
    let bootstrap: { path: string; version: string };
    try {
      bootstrap = this._resolveBootstrapPython();
    } catch {
      // No Python found — check for containerised environments
      if (detectFlatpak() || detectSnap()) {
        return this._setCache({
          state: "unavailable",
          pythonPath: null,
          version: null,
          source: "none",
          error: {
            code: "FLATPAK_SNAP_UNSUPPORTED",
            message:
              "Flatpak and Snap are not supported. Install Python 3.11+ natively.",
            platformAction:
              "Install Python 3.11+ from python.org or package manager",
          },
          lastVerifiedAt: null,
          stale: false,
          warnings: [],
        });
      }

      const osArchStr = getOsArch(this.osPlatform, this.osArch);
      const isMac = this.osPlatform === "darwin";
      const macTriplets = ["macos-x64", "macos-arm64"];
      const validatedTriplets = ["windows-x64", "linux-x64"];

      if (isMac && macTriplets.includes(osArchStr)) {
        return this._setCache({
          state: "unavailable",
          pythonPath: null,
          version: null,
          source: "none",
          error: {
            code: "NO_PYTHON",
            message:
              "No Python 3.11+ found. macOS auto-download disabled until signed/notarized artifacts exist.",
            platformAction: "Install Python 3.11+ from python.org or Homebrew",
          },
          lastVerifiedAt: null,
          stale: false,
          warnings: [],
        });
      }

      if (validatedTriplets.includes(osArchStr)) {
        return this._setCache({
          state: "unavailable",
          pythonPath: null,
          version: null,
          source: "none",
          error: {
            code: "NO_PYTHON",
            message: "No Python 3.11+ found and automatic download failed.",
            platformAction: "Install Python 3.11+ manually",
          },
          lastVerifiedAt: null,
          stale: false,
          warnings: [],
        });
      }

      // Unsupported triplet
      return this._setCache({
        state: "unavailable",
        pythonPath: null,
        version: null,
        source: "none",
        error: {
          code: "FALLBACK_UNAVAILABLE",
          message:
            "No Python found and this platform has no validated fallback.",
          platformAction: "Install Python 3.11+ manually from python.org",
        },
        lastVerifiedAt: null,
        stale: false,
        warnings: [],
      });
    }

    if (signal?.aborted) return this._abortedHealth();

    // All installations require 3.11+
    if (!isAtLeast(bootstrap.version, MIN_PYTHON)) {
      return this._setCache({
        state: "unavailable",
        pythonPath: null,
        version: bootstrap.version,
        source: "none",
        error: {
          code: "PYTHON_TOO_OLD",
          message: `Python ${bootstrap.version} is too old. Python 3.11+ required.`,
          platformAction: "Install Python 3.11+",
        },
        lastVerifiedAt: null,
        stale: false,
        warnings: [],
      });
    }

    if (signal?.aborted) return this._abortedHealth();

    // Step 2: ONE one-time venv + ONE pinned install (#174).  No version
    // slots, no rollback, no TS pointer write — after install the caller
    // runs `paperforge setup` (NDJSON), which publishes pointer.json.
    const pythonExe =
      this.osPlatform === "win32"
        ? path.join(this.venvDir, "Scripts", "python.exe")
        : path.join(this.venvDir, "bin", "python");

    try {
      this._fs.mkdirSync(this.venvDir, { recursive: true });

      // Create venv
      const {
        promise: venvPromise,
        reject: venvReject,
        resolve: venvResolve,
      } = deferred<void>();
      this._execFile(
        bootstrap.path,
        ["-m", "venv", this.venvDir],
        { timeout: 60000, signal },
        (err) => {
          if (err) venvReject(err);
          else venvResolve();
        }
      );
      await venvPromise;
    } catch (venvErr: unknown) {
      if (venvErr instanceof Error && venvErr.name === "AbortError") {
        try {
          this._fs.rmSync(this.venvDir, { recursive: true, force: true });
        } catch {}
        return this._abortedHealth();
      }
      try {
        this._fs.rmSync(this.venvDir, { recursive: true, force: true });
      } catch {}
      const msg = venvErr instanceof Error ? venvErr.message : String(venvErr);
      return this._setCache({
        state: "needs_repair",
        pythonPath: null,
        version,
        source: "none",
        error: {
          code: "VENV_CREATION_FAILED",
          message: msg,
          platformAction: "Retry installation",
        },
        lastVerifiedAt: null,
        stale: false,
        warnings: [],
      });
    }

    if (signal?.aborted) return this._abortedHealth();

    try {
      // ONE pinned pip install: paperforge[vector] (vector extras REQUIRED
      // for the core feature — a bare install crashes on first Build Index).
      const {
        promise: pipPromise,
        reject: pipReject,
        resolve: pipResolve,
      } = deferred<void>();
      this._execFile(
        pythonExe,
        ["-m", "pip", "install", `paperforge[vector]==${version}`],
        { timeout: 120000, signal },
        (err) => {
          if (err) pipReject(err);
          else pipResolve();
        }
      );
      await pipPromise;
    } catch (pipErr: unknown) {
      if (pipErr instanceof Error && pipErr.name === "AbortError") {
        try {
          this._fs.rmSync(this.venvDir, { recursive: true, force: true });
        } catch {}
        return this._abortedHealth();
      }
      try {
        this._fs.rmSync(this.venvDir, { recursive: true, force: true });
      } catch {}
      const msg = pipErr instanceof Error ? pipErr.message : String(pipErr);
      return this._setCache({
        state: "needs_repair",
        pythonPath: null,
        version,
        source: "none",
        error: {
          code: "PIP_INSTALL_FAILED",
          message: msg,
          platformAction: "Retry installation",
        },
        lastVerifiedAt: null,
        stale: false,
        warnings: [],
      });
    }

    if (signal?.aborted) return this._abortedHealth();

    try {
      // Verify with isolated import (paperforge + vector stack, #119).
      const {
        promise: verifyPromise,
        reject: verifyReject,
        resolve: verifyResolve,
      } = deferred<void>();
      this._execFile(
        pythonExe,
        [
          "-I",
          "-c",
          "import paperforge, openai, sqlite_vec; print(paperforge.__version__)",
        ],
        { timeout: 30000, signal },
        (err) => {
          if (err) verifyReject(err);
          else verifyResolve();
        }
      );
      await verifyPromise;
    } catch (verifyErr: unknown) {
      if (verifyErr instanceof Error && verifyErr.name === "AbortError") {
        try {
          this._fs.rmSync(this.venvDir, { recursive: true, force: true });
        } catch {}
        return this._abortedHealth();
      }
      try {
        this._fs.rmSync(this.venvDir, { recursive: true, force: true });
      } catch {}
      const msg =
        verifyErr instanceof Error ? verifyErr.message : String(verifyErr);
      return this._setCache({
        state: "needs_repair",
        pythonPath: null,
        version,
        source: "none",
        error: {
          code: "VERIFY_FAILED",
          message: msg,
          platformAction: "Retry installation",
        },
        lastVerifiedAt: null,
        stale: false,
        warnings: [],
      });
    }

    // #174: NO pointer write here.  Python publishes pointer.json via
    // `paperforge setup` — the caller runs it after ensure() (handshake →
    // post-runtime setup → publication).
    const health: RuntimeHealth = {
      state: "ready",
      pythonPath: pythonExe,
      version,
      source: "venv",
      error: null,
      lastVerifiedAt: new Date().toISOString(),
      stale: false,
      warnings: [],
    };
    return this._setCache(health);
  }

  // ── Private helpers ──

  private _setCache(h: RuntimeHealth): RuntimeHealth {
    this._cache = h;
    this._cacheTime = Date.now();
    return h;
  }

  private _abortedHealth(): RuntimeHealth {
    return {
      state: "needs_repair",
      pythonPath: null,
      version: null,
      source: "none",
      error: {
        code: "ABORTED",
        message: "Operation was cancelled",
        platformAction: "Retry operation",
      },
      lastVerifiedAt: null,
      stale: false,
      warnings: [],
    };
  }

  private _resolveBootstrapPython(): { path: string; version: string } {
    const candidates: { path: string; args: readonly string[] }[] = [];

    if (this.osPlatform === "win32") {
      candidates.push(
        { path: "py", args: ["-3.11"] },
        { path: "py", args: ["-3.10"] },
        { path: "py", args: ["-3"] },
        { path: "python", args: [] }
      );
    } else if (this.osPlatform === "darwin") {
      candidates.push(
        { path: "/usr/bin/python3", args: [] },
        { path: "python3", args: [] },
        { path: "python", args: [] }
      );
    } else {
      // Linux
      candidates.push(
        { path: "/usr/bin/python3", args: [] },
        { path: "python3", args: [] },
        { path: "python", args: [] }
      );
    }

    for (const c of candidates) {
      try {
        const output = this._execFileSync(c.path, [...c.args, "--version"], {
          encoding: "utf-8",
          timeout: 5000,
        });
        const ver = parsePythonVersion(output);
        if (ver) {
          return { path: c.path, version: ver };
        }
      } catch {
        // try next candidate
      }
    }

    throw new Error("No Python 3.11+ found on system");
  }

  private _probe(
    pythonPath: string,
    signal?: AbortSignal
  ): Promise<{ version: string | null }> {
    const { promise, resolve, reject } = deferred<{ version: string | null }>();
    this._execFile(
      pythonPath,
      ["-I", "-c", "import paperforge; print(paperforge.__version__)"],
      { timeout: 30000, signal },
      (err, stdout) => {
        if (err) {
          reject(err);
        } else {
          const version = (stdout ?? "").trim() || null;
          resolve({ version });
        }
      }
    );
    return promise;
  }
}
