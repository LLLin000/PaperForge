/**
 * ManagedRuntime — single, machine-local PaperForge runtime.
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
 * Design: immutable version slots under ~/.paperforge/runtime/{os-arch}/,
 *          one atomically-replaced active-runtime.json at the runtime root.
 *          Machine-local, shared across vaults. No credentials or vault paths.
 */

import * as fs from "fs";
import * as path from "path";
import { execFile as cpExecFile, execFileSync as cpExecFileSync } from "child_process";
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
  readonly previousVersion: string | null;
  readonly previousPythonPath: string | null;
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
  writeFileSync(p: string, data: string | NodeJS.ArrayBufferView, encoding?: string | null): void;
  renameSync(oldP: string, newP: string): void;
  mkdirSync(p: string, opts?: { recursive?: boolean }): string | undefined;
  rmSync(p: string, opts?: { recursive?: boolean; force?: boolean }): void;
  readdirSync(p: string, opts?: { withFileTypes?: boolean }): fs.Dirent[];
}

export type ExecFileCallback = (error: Error | null, stdout: string, stderr: string) => void;
export type ExecFileFn = (command: string, args: readonly string[], opts: { timeout?: number; encoding?: string; signal?: AbortSignal }, cb: ExecFileCallback) => void;
export type ExecFileSyncFn = (command: string, args: readonly string[], opts: { encoding: string; timeout: number }) => string;

// ── Constants ──

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
const MIN_PYTHON_NEW = "3.11";
const MIN_PYTHON_LEGACY = "3.10";

/** ES2018-compatible Promise.withResolvers polyfill. */
function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void; reject: (err: unknown) => void } {
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
    if (cgroup.includes("docker") || cgroup.includes("flatpak") || cgroup.includes("snap")) return true;
  } catch {
    // ignore
  }
  return false;
}

function detectFlatpak(): boolean {
  return process.env.FLATPAK_ID !== undefined ||
    (process.env.XDG_DATA_DIRS ?? "").includes("flatpak") ||
    false;
}

function detectSnap(): boolean {
  return process.env.SNAP !== undefined ||
    process.env.SNAP_NAME !== undefined ||
    false;
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
export function runtimeActionsForHealth(health: RuntimeHealth): readonly RuntimeAction[];
/** Return UI actions with verb/label. Used by settings rendering. */
export function runtimeActionsForHealth(health: RuntimeHealth, targetVersion: string, running: boolean): readonly RuntimeUiAction[];
export function runtimeActionsForHealth(health: RuntimeHealth, targetVersion?: string, running?: boolean): readonly RuntimeAction[] | readonly RuntimeUiAction[] {
  // 3-param UI path (settings rendering)
  if (targetVersion !== undefined || running !== undefined) {
    if (running) {
      return [{ verb: "stop", label: "Stop" }];
    }
    switch (health.state) {
      case "not_installed":
        return [{ verb: "install", label: "Install Runtime" }];
      case "needs_repair": {
        const actions: RuntimeUiAction[] = [
          { verb: "repair", label: "Repair Runtime" },
        ];
        if (health.pythonPath) {
          actions.push({ verb: "rollback", label: "Rollback" });
        }
        return actions;
      }
      case "ready": {
        const actions: RuntimeUiAction[] = [
          { verb: "status", label: "Check Status" },
          { verb: "update", label: "Update Runtime" },
        ];
        if (health.previousVersion) {
          actions.push({ verb: "rollback", label: "Rollback" });
        }
        return actions;
      }
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
      return [{ id: "install", label: "Install Runtime", primary: true, destructive: false }];
    case "needs_repair": {
      const actions: RuntimeAction[] = [
        { id: "repair", label: "Repair Runtime", primary: true, destructive: false },
      ];
      if (health.pythonPath) {
        actions.push({ id: "rollback", label: "Rollback", primary: false, destructive: false });
      }
      return actions;
    }
    case "ready":
      return [
        { id: "status", label: "Check Status", primary: false, destructive: false },
        { id: "update", label: "Update Runtime", primary: false, destructive: false },
      ];
    case "unknown":
      return [{ id: "probe", label: "Refresh Status", primary: true, destructive: false }];
    case "unavailable":
      return [{ id: "setup", label: "Manual Setup", primary: true, destructive: false }];
    default:
      return [{ id: "probe", label: "Refresh Status", primary: true, destructive: false }];
  }
}

// ── Resolve runtime command from health ──

export function resolveRuntimeCommand(health: RuntimeHealth): RuntimeRun | null {
  if (health.state !== "ready" || !health.pythonPath) return null;
  return { command: health.pythonPath, args: [] };
}

// ── ManagedRuntime class ──

export class ManagedRuntime {
  private readonly runtimeDir: string;
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
    // triplet is the raw platform-arch (e.g. "win32-x64"), not the getOsArch mapped value
    this.triplet = `${platform}-${arch}`;

    if (opts.runtimeDir) {
      this.runtimeDir = opts.runtimeDir;
      this.rootDir = path.dirname(opts.runtimeDir);
      this.pluginVersion = opts.pluginVersion ?? opts.version ?? "0.0.0";
    } else {
      const home = os.homedir();
      this.rootDir = path.join(home, ".paperforge", "runtime");
      // runtime dir uses getOsArch-mapped value (e.g. "windows-x64")
      this.runtimeDir = path.join(this.rootDir, getOsArch(platform, arch));
      this.pluginVersion = opts.version ?? opts.pluginVersion ?? "0.0.0";
    }

    // Pointer lives at the runtime root (parent of os-arch dir)
    this.pointerPath = path.join(this.rootDir, "active-runtime.json");
    this._fs = opts.fs ?? (fs as unknown as FsOps);
    this._execFile = opts.execFile ?? (cpExecFile as unknown as ExecFileFn);
    this._execFileSync = opts.execFileSync ?? (cpExecFileSync as unknown as ExecFileSyncFn);
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
        previousVersion: null,
        previousPythonPath: null,
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

    // Read pointer file to find active runtime
    let pointerVersion: string | null = null;
    let pointerPythonPath: string | null = null;
    let pointerPrevVersion: string | null = null;
    let pointerPrevPythonPath: string | null = null;
    let pointerWarnings: WarningInfo[] = [];
    try {
      const raw = this._fs.readFileSync(this.pointerPath, "utf-8");
      const ptr: Record<string, unknown> = JSON.parse(raw);
      pointerVersion = typeof ptr.version === "string" ? ptr.version : null;
      const pp = typeof ptr.pythonPath === "string" ? ptr.pythonPath : null;
      pointerPythonPath = pp ? path.resolve(path.dirname(this.pointerPath), pp) : null;
      pointerPrevVersion = typeof ptr.previousVersion === "string" ? ptr.previousVersion : null;
      pointerPrevPythonPath = typeof ptr.previousPythonPath === "string" ? ptr.previousPythonPath : null;
      pointerWarnings = Array.isArray(ptr.warnings) ? ptr.warnings as WarningInfo[] : [];
    } catch {
      // No pointer → not installed
      return this._setCache({
        state: "not_installed",
        pythonPath: null,
        version: null,
        source: "none",
        error: null,
        lastVerifiedAt: null,
        stale: false,
        warnings: [],
        previousVersion: null,
        previousPythonPath: null,
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
          message: "Active runtime pointer has no pythonPath",
          platformAction: "Reinstall runtime",
        },
        lastVerifiedAt: null,
        stale: false,
        warnings: pointerWarnings,
        previousVersion: pointerPrevVersion,
        previousPythonPath: pointerPrevPythonPath,
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
        warnings: pointerWarnings,
        previousVersion: pointerPrevVersion,
        previousPythonPath: pointerPrevPythonPath,
      });
    }

    // Run isolated import probe
    try {
      const result = await this._probe(pointerPythonPath);

      // Check Python version and add Release-N warning for 3.10
      const probeWarnings = [...pointerWarnings];
      try {
        const pyVerOut = this._execFileSync(pointerPythonPath, ["--version"], {
          encoding: "utf-8",
          timeout: 5000,
        });
        const pyVer = parsePythonVersion(pyVerOut);
        if (pyVer && isAtLeast(pyVer, MIN_PYTHON_LEGACY) && !isAtLeast(pyVer, MIN_PYTHON_NEW)) {
          // Only add if not already present
          if (!probeWarnings.some((w) => w.code === "PYTHON_310_DEPRECATED")) {
            probeWarnings.push({
              code: "PYTHON_310_DEPRECATED",
              message: `Python ${pyVer} is running. Python 3.10 support enters legacy phase in Release N — upgrade to Python ${MIN_PYTHON_NEW}+ recommended.`,
              platformAction: `Upgrade to Python ${MIN_PYTHON_NEW}+`,
            });
          }
        }
      } catch {
        // Version check is best-effort; ignore failures
      }

      return this._setCache({
        state: "ready",
        pythonPath: pointerPythonPath,
        version: result.version ?? pointerVersion,
        source: "venv",
        error: null,
        lastVerifiedAt: new Date().toISOString(),
        stale: false,
        warnings: probeWarnings,
        previousVersion: pointerPrevVersion,
        previousPythonPath: pointerPrevPythonPath,
      });
    } catch (probeErr: unknown) {
      const msg = probeErr instanceof Error ? probeErr.message : String(probeErr);
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
        warnings: pointerWarnings,
        previousVersion: pointerPrevVersion,
        previousPythonPath: pointerPrevPythonPath,
      });
    }
  }

  // ── Ensure a working runtime ──

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
            message: "Flatpak and Snap are not supported. Install Python 3.11+ natively.",
            platformAction: "Install Python 3.11+ from python.org or package manager",
          },
          lastVerifiedAt: null,
          stale: false,
          warnings: [],
          previousVersion: null,
          previousPythonPath: null,
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
            message: "No Python 3.11+ found. macOS auto-download disabled until signed/notarized artifacts exist.",
            platformAction: "Install Python 3.11+ from python.org or Homebrew",
          },
          lastVerifiedAt: null,
          stale: false,
          warnings: [],
          previousVersion: null,
          previousPythonPath: null,
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
          previousVersion: null,
          previousPythonPath: null,
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
          message: "No Python found and this platform has no validated fallback.",
          platformAction: "Install Python 3.11+ manually from python.org",
        },
        lastVerifiedAt: null,
        stale: false,
        warnings: [],
        previousVersion: null,
        previousPythonPath: null,
      });
    }

    if (signal?.aborted) return this._abortedHealth();

    // Step 2: Compatibility gate — version check
    const isExistingInstall = this._currentSlotExists(version);

    if (!isAtLeast(bootstrap.version, MIN_PYTHON_LEGACY)) {
      return this._setCache({
        state: "unavailable",
        pythonPath: null,
        version: bootstrap.version,
        source: "none",
        error: {
          code: "PYTHON_TOO_OLD",
          message: `Python ${bootstrap.version} is too old. Python 3.10+ required.`,
          platformAction: "Install Python 3.10+",
        },
        lastVerifiedAt: null,
        stale: false,
        warnings: [],
        previousVersion: null,
        previousPythonPath: null,
      });
    }

    // New installs / repairs require 3.11+
    if (!isExistingInstall && !isAtLeast(bootstrap.version, MIN_PYTHON_NEW)) {
      return this._setCache({
        state: "needs_repair",
        pythonPath: null,
        version: bootstrap.version,
        source: "none",
        error: {
          code: "PYTHON_VERSION_WARNING",
          message: `Python ${bootstrap.version} found. New installations require Python ${MIN_PYTHON_NEW}+.`,
          platformAction: `Upgrade to Python ${MIN_PYTHON_NEW}+`,
        },
        lastVerifiedAt: null,
        stale: false,
        warnings: [],
        previousVersion: null,
        previousPythonPath: null,
      });
    }

    // Step 2.5: Rollback/retained-slot fast path — if the version slot
    // already exists, we are not forcing a rebuild, AND the currently
    // active pointer points to a different version, verify the retained
    // immutable slot and atomically rewrite the pointer without creating
    // a new venv or running pip.  This preserves the slot exactly as it
    // was built and is never a bootstrap / venv / pip operation.
    if (isExistingInstall && !force) {
      // Determine whether this is a rollback (active version != requested)
      let isRollback = false;
      try {
        const curRaw = this._fs.readFileSync(this.pointerPath, "utf-8");
        const curPtr: Record<string, unknown> = JSON.parse(curRaw);
        const activeVer = typeof curPtr.version === "string" ? curPtr.version : null;
        isRollback = activeVer !== null && activeVer !== version;
      } catch {
        // No pointer — not a rollback
      }

      if (isRollback) {

        const rollbackSlotDir = path.join(this.runtimeDir, `v${version}`);
        const rollbackVenvDir = path.join(rollbackSlotDir, "venv");
        const rollbackPythonExe = this.osPlatform === "win32"
          ? path.join(rollbackVenvDir, "Scripts", "python.exe")
          : path.join(rollbackVenvDir, "bin", "python");

        // Verify the retained slot's Python can import paperforge
        try {
          await this._probe(rollbackPythonExe, signal);
        } catch (probeErr: unknown) {
          if (probeErr instanceof Error && probeErr.name === "AbortError") {
            return this._abortedHealth();
          }
          const msg = probeErr instanceof Error ? probeErr.message : String(probeErr);
          return this._setCache({
            state: "needs_repair",
            pythonPath: rollbackPythonExe,
            version,
            source: "venv",
            error: {
              code: "RETAINED_SLOT_PROBE_FAILED",
              message: `Retained slot v${version} failed verification: ${msg}`,
              platformAction: "Repair runtime",
            },
            lastVerifiedAt: null,
            stale: false,
            warnings: [],
            previousVersion: null,
            previousPythonPath: null,
          });
        }

        // Load old pointer for rollback info
        let prevVersion: string | null = null;
        let prevPythonPath: string | null = null;
        try {
          const oldRaw = this._fs.readFileSync(this.pointerPath, "utf-8");
          const oldPtr: Record<string, unknown> = JSON.parse(oldRaw);
          prevVersion = typeof oldPtr.version === "string" ? oldPtr.version : null;
          prevPythonPath = typeof oldPtr.pythonPath === "string" ? oldPtr.pythonPath : null;
        } catch {
          // No previous pointer — first install
        }

        // Atomically write pointer: write temp, rename
        const pointerDir = path.dirname(this.pointerPath);
        if (!this._fs.existsSync(pointerDir)) {
          this._fs.mkdirSync(pointerDir, { recursive: true });
        }

        const relativePyPath = path.relative(path.dirname(this.pointerPath), rollbackPythonExe);
        const pointerContent = JSON.stringify(
          {
            schema_version: 1,
            version,
            pythonPath: relativePyPath,
            activatedAt: new Date().toISOString(),
            previousVersion: prevVersion,
            previousPythonPath: prevPythonPath,
          },
          null,
          2,
        );

        const tmpPath = this.pointerPath + ".tmp";
        this._fs.writeFileSync(tmpPath, pointerContent, "utf-8");
        this._fs.renameSync(tmpPath, this.pointerPath);

        // Update cache
        const health: RuntimeHealth = {
          state: "ready",
          pythonPath: rollbackPythonExe,
          version,
          source: "venv",
          error: null,
          lastVerifiedAt: new Date().toISOString(),
          stale: false,
          warnings: [],
          previousVersion: prevVersion,
          previousPythonPath: prevPythonPath,
        };
        this._cache = health;
        this._cacheTime = Date.now();

        // Cleanup old slots (best-effort, keep 2)
        this._cleanupOldSlots(version);

        return health;
      }
    }

    if (signal?.aborted) return this._abortedHealth();


    // Step 3: Build immutable version slot
    const slotDir = force
      ? path.join(this.runtimeDir, `v${version}_build2`)
      : path.join(this.runtimeDir, `v${version}`);
    const venvDir = path.join(slotDir, "venv");
    const pythonExe = this.osPlatform === "win32"
      ? path.join(venvDir, "Scripts", "python.exe")
      : path.join(venvDir, "bin", "python");

    try {
      this._fs.mkdirSync(slotDir, { recursive: true });

      // Create venv
      const { promise: venvPromise, reject: venvReject, resolve: venvResolve } = deferred<void>();
      this._execFile(bootstrap.path, ["-m", "venv", venvDir], { timeout: 60000, signal }, (err) => {
        if (err) venvReject(err);
        else venvResolve();
      });
      await venvPromise;
    } catch (venvErr: unknown) {
      if (venvErr instanceof Error && venvErr.name === "AbortError") {
        try { this._fs.rmSync(slotDir, { recursive: true, force: true }); } catch {}
        return this._abortedHealth();
      }
      return this._slotFailed(version, "VENV_CREATION_FAILED", venvErr, slotDir);
    }

    if (signal?.aborted) return this._abortedHealth();

    try {
      // pip install paperforge
      const { promise: pipPromise, reject: pipReject, resolve: pipResolve } = deferred<void>();
      this._execFile(pythonExe, ["-m", "pip", "install", `paperforge==${version}`], { timeout: 120000, signal }, (err) => {
        if (err) pipReject(err);
        else pipResolve();
      });
      await pipPromise;
    } catch (pipErr: unknown) {
      if (pipErr instanceof Error && pipErr.name === "AbortError") {
        try { this._fs.rmSync(slotDir, { recursive: true, force: true }); } catch {}
        return this._abortedHealth();
      }
      return this._slotFailed(version, "PIP_INSTALL_FAILED", pipErr, slotDir);
    }

    if (signal?.aborted) return this._abortedHealth();

    try {
      // Verify with isolated import
      const { promise: verifyPromise, reject: verifyReject, resolve: verifyResolve } = deferred<void>();
      this._execFile(pythonExe, ["-I", "-c", `import paperforge; print(paperforge.__version__)`], { timeout: 30000, signal }, (err) => {
        if (err) verifyReject(err);
        else verifyResolve();
      });
      await verifyPromise;
    } catch (verifyErr: unknown) {
      if (verifyErr instanceof Error && verifyErr.name === "AbortError") {
        try { this._fs.rmSync(slotDir, { recursive: true, force: true }); } catch {}
        return this._abortedHealth();
      }
      return this._slotFailed(version, "VERIFY_FAILED", verifyErr, slotDir);
    }

    // Load old pointer for rollback info
    let prevVersion: string | null = null;
    let prevPythonPath: string | null = null;
    try {
      const oldRaw = this._fs.readFileSync(this.pointerPath, "utf-8");
      const oldPtr: Record<string, unknown> = JSON.parse(oldRaw);
      prevVersion = typeof oldPtr.version === "string" ? oldPtr.version : null;
      prevPythonPath = typeof oldPtr.pythonPath === "string" ? oldPtr.pythonPath : null;
    } catch {
      // No previous pointer — first install
    }

    // Atomically write pointer: write temp, rename
    const pointerDir = path.dirname(this.pointerPath);
    if (!this._fs.existsSync(pointerDir)) {
      this._fs.mkdirSync(pointerDir, { recursive: true });
    }

    const relativePyPath = path.relative(path.dirname(this.pointerPath), pythonExe);

    const pointerContent = JSON.stringify(
      {
        schema_version: 1,
        version,
        pythonPath: relativePyPath,
        activatedAt: new Date().toISOString(),
        previousVersion: prevVersion,
        previousPythonPath: prevPythonPath,
      },
      null,
      2,
    );

    const tmpPath = this.pointerPath + ".tmp";
    this._fs.writeFileSync(tmpPath, pointerContent, "utf-8");
    this._fs.renameSync(tmpPath, this.pointerPath);

    // Update cache
    const health: RuntimeHealth = {
      state: "ready",
      pythonPath: pythonExe,
      version,
      source: "venv",
      error: null,
      lastVerifiedAt: new Date().toISOString(),
      stale: false,
      warnings: [],
      previousVersion: prevVersion,
      previousPythonPath: prevPythonPath,
    };
    this._cache = health;
    this._cacheTime = Date.now();

    // Cleanup old slots (best-effort, keep 2)
    this._cleanupOldSlots(version);

    return health;
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
      error: { code: "ABORTED", message: "Operation was cancelled", platformAction: "Retry operation" },
      lastVerifiedAt: null,
      stale: false,
      warnings: [],
      previousVersion: null,
      previousPythonPath: null,
    };
  }

  private _slotFailed(version: string, code: string, err: unknown, slotDir: string): RuntimeHealth {
    // Clean up failed slot
    try {
      this._fs.rmSync(slotDir, { recursive: true, force: true });
    } catch {
      // best-effort
    }
    const msg = err instanceof Error ? err.message : String(err);
    return this._setCache({
      state: "needs_repair",
      pythonPath: null,
      version,
      source: "none",
      error: { code, message: msg, platformAction: "Retry installation" },
      lastVerifiedAt: null,
      stale: false,
      warnings: [],
      previousVersion: null,
      previousPythonPath: null,
    });
  }

  private _currentSlotExists(version: string): boolean {
    const slotDir = path.join(this.runtimeDir, `v${version}`);
    return this._fs.existsSync(slotDir);
  }

  private _resolveBootstrapPython(): { path: string; version: string } {
    const candidates: { path: string; args: readonly string[] }[] = [];

    if (this.osPlatform === "win32") {
      candidates.push(
        { path: "py", args: ["-3.11"] },
        { path: "py", args: ["-3.10"] },
        { path: "py", args: ["-3"] },
        { path: "python", args: [] },
      );
    } else if (this.osPlatform === "darwin") {
      candidates.push(
        { path: "/usr/bin/python3", args: [] },
        { path: "python3", args: [] },
        { path: "python", args: [] },
      );
    } else {
      // Linux
      candidates.push(
        { path: "/usr/bin/python3", args: [] },
        { path: "python3", args: [] },
        { path: "python", args: [] },
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

    throw new Error("No Python 3.10+ found on system");
  }

  private _probe(pythonPath: string, signal?: AbortSignal): Promise<{ version: string | null }> {
    const { promise, resolve, reject } = deferred<{ version: string | null }>();
    this._execFile(pythonPath, ["-I", "-c", "import paperforge; print(paperforge.__version__)"], { timeout: 30000, signal }, (err, stdout) => {
      if (err) {
        reject(err);
      } else {
        const version = (stdout ?? "").trim() || null;
        resolve({ version });
      }
    });
    return promise;
  }

  private _cleanupOldSlots(currentVersion: string, keepOldSlots: number = 2): void {
    try {
      const entries = this._fs.readdirSync(this.runtimeDir, { withFileTypes: true });
      const slots = entries
        .filter((e) => e.isDirectory() && e.name.startsWith("v"))
        .map((e) => {
          const baseVer = e.name.replace(/^v/, "").replace(/_build\d+$/, "");
          return { name: e.name, version: baseVer };
        })
        .filter((s) => s.version !== currentVersion)
        .sort((a, b) => compareVersions(b.version, a.version));

      // Keep at most keepOldSlots old slots
      for (let i = keepOldSlots; i < slots.length; i++) {
        this._fs.rmSync(path.join(this.runtimeDir, slots[i].name), { recursive: true, force: true });
      }
    } catch {
      // best-effort
    }
  }
}
