/**
 * RuntimeBootstrap — PRE-runtime bootstrap adapter (#174 / #143 §7).
 *
 * Post-cutover the plugin holds NO runtime state machine.  The only
 * runtime truths are:
 *   - the pointer (`~/.paperforge/runtime/pointer.json`), published SOLELY
 *     by Python after a successful `paperforge setup`; and
 *   - Python's own installation probe (probe installation --json).
 *
 * TS keeps exactly: interpreter discovery, platform gates, consent UX,
 * ONE candidate venv + ONE pinned install (installOnce), handshake, pointer
 * READ and spawn.  DELETED: RuntimeHealth FSM / TTL cache / current() /
 * status() / ensure() / runtimeActionsForHealth policy / automatic
 * mismatch repair / any pointer write.
 */

import * as fs from "fs";
import * as path from "path";
import {
  execFile as cpExecFile,
  execFileSync as cpExecFileSync,
} from "child_process";
import * as os from "os";

// ── Public types ──

export interface PointerInfo {
  /** Absolute path to the runtime interpreter (schema v1). */
  readonly pythonPath: string;
  /** Absolute generic environment root (schema v1). */
  readonly environmentRoot: string;
  /** Installed PaperForge version (schema v1). */
  readonly paperforgeVersion: string;
}

export interface RuntimeRun {
  readonly command: string;
  readonly args: readonly string[];
}

export interface DiscoveredInterpreter {
  readonly path: string;
  readonly version: string;
}

export interface GateFailure {
  readonly ok: false;
  readonly code: string;
  readonly message: string;
  readonly platformAction: string;
}

export type PlatformGate = { readonly ok: true } | GateFailure;

// ── Internal DI types ──

export interface FsOps {
  existsSync(p: string): boolean;
  readFileSync(p: string, encoding?: string | null): string;
  mkdirSync(p: string, opts?: { recursive?: boolean }): string | undefined;
  rmSync(
    p: string,
    opts?: {
      recursive?: boolean;
      force?: boolean;
      maxRetries?: number;
      retryDelay?: number;
    }
  ): void;
  /** Optional: the real fs provides them; doubles may omit them. */
  statSync?(p: string): { mtimeMs: number };
  readdirSync?(p: string): string[];
}

export type ExecFileCallback = (
  error: Error | null,
  stdout: string,
  stderr: string
) => void;
export type ExecFileFn = (
  command: string,
  args: readonly string[],
  opts: {
    timeout?: number;
    encoding?: string;
    signal?: AbortSignal;
    cwd?: string;
    env?: Record<string, string | undefined>;
  },
  cb: ExecFileCallback
) => unknown;
export type ExecFileSyncFn = (
  command: string,
  args: readonly string[],
  opts: { encoding: string; timeout: number }
) => string;

// ── Constants ──

const MIN_PYTHON = "3.11";
const POINTER_SCHEMA_VERSION = 1;
const POINTER_FILENAME = "pointer.json";
const VENV_DIR_NAME = "venv";
/** An install lock older than this is debris from a killed process. */
const STALE_INSTALL_LOCK_MS = 15 * 60 * 1000;

/**
 * Install attempts in flight, keyed by normalized runtime root.
 *
 * ONE venv path is a shared, exclusively-written resource: two concurrent
 * `pip install` runs into it deadlock on Windows file locks (WinError 32),
 * neither exits, and every later attempt keeps failing while the stale
 * processes hold handles.  A second attempt therefore fails fast instead of
 * racing — this also covers a plugin reload while an install is running.
 */
const activeInstalls = new Set<string>();

/** Case-insensitive key on Windows (the same dir spelled differently). */
function runtimeKey(rootDir: string): string {
  const resolved = path.resolve(rootDir);
  return process.platform === "win32" ? resolved.toLowerCase() : resolved;
}

/**
 * True while a runtime install holds the cross-process lock for the runtime
 * `pythonPath` belongs to.
 *
 * Spawning that interpreter mid-install is a race Windows punishes: the UI
 * keeps probing modules (each probe imports the vector stack — chromadb
 * pulls kubernetes' thousands of files) while pip writes the same files, and
 * pip dies with WinError 32 against a handler the probe still holds.
 */
export function runtimeInstallInProgress(pythonPath: string): boolean {
  // …/runtime/venv-*/Scripts/python.exe → check the three enclosing levels.
  let dir = path.dirname(path.resolve(pythonPath));
  for (let level = 0; level < 3; level += 1) {
    if (fs.existsSync(path.join(dir, "install.lock.d"))) return true;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return false;
}

/** Minimal surface of a spawned child we need to terminate. */
interface TrackedChild {
  kill?: (signal?: string) => boolean;
  pid?: number;
}

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

interface VersionKey {
  nums: number[];
  phase: number[];
}

/**
 * PEP 440 ordering key for the spellings in play.
 *
 * `normalizeReleaseVersion()` is the single SemVer→PEP 440 entry; this
 * parser reads the canonical PEP 440 form only and returns null for
 * anything unrecognized so callers fail closed (NaN).
 *
 * Phase encoding (compared after the release numbers, per PEP 440):
 *   bare `.devN`    → [-3, devN]                    (below every pre-release)
 *   `aN`/`bN`/`rcN` → [rank, N, dev ? 0 : 1, devN]  (rank: a=-2, b=-1, rc=0;
 *                     an attached `.devN` sorts below its base)
 *   final           → [1, 0]
 *   `.postN`        → [2, postN, dev ? 0 : 1, devN, preRank, preNum]
 */
function versionKey(version: string): VersionKey | null {
  const normalized = normalizeReleaseVersion(version).trim().toLowerCase();
  const m = normalized.match(
    /^(\d+(?:\.\d+)*)(?:(a|b|rc)(\d+))?(?:\.post(\d+))?(?:\.dev(\d+))?$/
  );
  if (!m) return null;
  const nums = m[1].split(".").map(Number);
  const pre = m[2] ?? null;
  const preNum = m[3] !== undefined ? Number(m[3]) : 0;
  const post = m[4] !== undefined ? Number(m[4]) : null;
  const dev = m[5] !== undefined ? Number(m[5]) : null;
  const preRank = pre === "a" ? -2 : pre === "b" ? -1 : pre === "rc" ? 0 : null;
  let phase: number[];
  if (post !== null) {
    phase = [2, post, dev === null ? 1 : 0, dev ?? 0];
    if (preRank !== null) phase.push(preRank, preNum);
  } else if (preRank !== null) {
    phase = [preRank, preNum, dev === null ? 1 : 0, dev ?? 0];
  } else if (dev !== null) {
    phase = [-3, dev];
  } else {
    phase = [1, 0];
  }
  return { nums, phase };
}

/**
 * PEP 440 ordering across release spellings (SemVer releases go through
 * `normalizeReleaseVersion()` first): `dev < a < b < rc < final < post`,
 * with `.dev` sorting below whatever it attaches to. Unparseable input
 * returns NaN — callers treat that as fail-closed.
 */
export function compareVersions(a: string, b: string): number {
  const ka = versionKey(a);
  const kb = versionKey(b);
  if (!ka || !kb) return Number.NaN;
  const numLen = Math.max(ka.nums.length, kb.nums.length);
  for (let i = 0; i < numLen; i++) {
    const an = ka.nums[i] ?? 0;
    const bn = kb.nums[i] ?? 0;
    if (an !== bn) return an - bn;
  }
  const phaseLen = Math.max(ka.phase.length, kb.phase.length);
  for (let i = 0; i < phaseLen; i++) {
    const an = ka.phase[i] ?? 0;
    const bn = kb.phase[i] ?? 0;
    if (an !== bn) return an - bn;
  }
  return 0;
}

function isAtLeast(version: string, minVersion: string): boolean {
  return compareVersions(version, minVersion) >= 0;
}

/**
 * One release, two spellings: the release assets / tags carry SemVer
 * (`2.0.0-rc.2`, what Obsidian and BRAT want) while the package and the
 * runtime report PEP 440 (`2.0.0rc2`, what pip and PyPI want).  Every
 * version COMPARISON must look through the spelling — a raw string compare
 * failed the fresh-child check and rolled the install back.
 */
function normalizeReleaseVersion(version: string): string {
  const m = version.trim().match(/^(\d+(?:\.\d+)*)-(alpha|beta|rc)\.(\d+)$/i);
  if (!m) return version.trim();
  const phase = m[2].toLowerCase();
  const pep440 = phase === "alpha" ? "a" : phase === "beta" ? "b" : "rc";
  return `${m[1]}${pep440}${m[3]}`;
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

// ── Resolve runtime command from the pointer ──

export function resolveRuntimeCommand(
  ptr: PointerInfo | null
): RuntimeRun | null {
  if (!ptr) return null;
  return { command: ptr.pythonPath, args: [] };
}

// ── RuntimeBootstrap class ──

export class RuntimeBootstrap {
  private readonly osPlatform: string;
  private readonly osArch: string;

  // DI: injectable fs, execFile, execFileSync for testing
  private readonly _fs: FsOps;
  private readonly _execFile: ExecFileFn;
  private readonly _execFileSync: ExecFileSyncFn;

  /** Canonical runtime root: ~/.paperforge/runtime. */
  public readonly rootDir: string;

  /**
   * Cross-process install lock (atomic mkdir).  Returns the release function.
   * A lock older than STALE_INSTALL_LOCK_MS is treated as debris from a killed
   * process and reclaimed.
   */
  private _acquireInstallLock(): () => void {
    const lockDir = path.join(this.rootDir, "install.lock.d");
    const held = () => {
      const mtime = this._fs.statSync?.(lockDir)?.mtimeMs ?? 0;
      const stale = mtime > 0 && Date.now() - mtime > STALE_INSTALL_LOCK_MS;
      if (!stale) {
        throw new Error(
          "Another PaperForge runtime install is already running for this runtime directory"
        );
      }
      this._fs.rmSync(lockDir, { recursive: true, force: true });
    };
    try {
      this._fs.mkdirSync(this.rootDir, { recursive: true });
      this._fs.mkdirSync(lockDir);
    } catch {
      held();
      this._fs.mkdirSync(lockDir);
    }
    return () => {
      try {
        this._fs.rmSync(lockDir, { recursive: true, force: true });
      } catch {
        // best effort: a stale lock is reclaimed by the next install
      }
    };
  }

  /** Child process of the step currently in flight (see _terminateActiveChild). */
  private _activeChild: TrackedChild | null = null;

  constructor(opts?: {
    runtimeDir?: string;
    osPlatform?: string;
    osArch?: string;
    fs?: FsOps;
    execFile?: ExecFileFn;
    execFileSync?: ExecFileSyncFn;
  }) {
    this.osPlatform = opts?.osPlatform ?? process.platform;
    this.osArch = opts?.osArch ?? process.arch;
    this.rootDir =
      opts?.runtimeDir ?? path.join(os.homedir(), ".paperforge", "runtime");
    this._fs = opts?.fs ?? (fs as unknown as FsOps);
    this._execFile = opts?.execFile ?? (cpExecFile as unknown as ExecFileFn);
    this._execFileSync =
      opts?.execFileSync ?? (cpExecFileSync as unknown as ExecFileSyncFn);
  }

  private get venvDir(): string {
    return path.join(this.rootDir, VENV_DIR_NAME);
  }

  /** #260: unique final directory for one install attempt (never renamed). */
  private _candidateDir(expectedVersion: string): string {
    const safe = expectedVersion.replace(/[^A-Za-z0-9._-]+/g, "_");
    const suffix = Math.random().toString(36).slice(2, 8);
    return path.join(this.rootDir, `${VENV_DIR_NAME}-${safe}-${suffix}`);
  }

  /**
   * #260: remove every runtime environment except the activated one
   * (the legacy `venv` directory and older candidates).  Best-effort
   * housekeeping — call it only after a successful publish, so the pointer
   * already names `activeRoot`; a locked directory is retried next time.
   */
  retireUnusedRuntimes(activeRoot: string | null): string[] {
    if (!this._fs.readdirSync) return [];
    const keep = activeRoot ? path.resolve(activeRoot) : null;
    const removed: string[] = [];
    let entries: string[] = [];
    try {
      entries = this._fs.readdirSync(this.rootDir);
    } catch {
      return removed;
    }
    for (const name of entries) {
      if (!/^venv(-|$)/.test(name)) continue;
      const full = path.join(this.rootDir, name);
      if (keep && path.resolve(full) === keep) continue;
      try {
        this._fs.rmSync(full, { recursive: true, force: true });
        removed.push(name);
      } catch {
        // Locked by a running process — the next success retires it.
      }
    }
    return removed;
  }

  /** ONE canonical venv interpreter path (Windows vs POSIX). */
  private pythonExeFor(venvDir: string): string {
    return this.osPlatform === "win32"
      ? path.join(venvDir, "Scripts", "python.exe")
      : path.join(venvDir, "bin", "python");
  }

  // ── 1. Interpreter discovery (#143 §3 chain; >=3.11 required) ──

  /** Discover a system interpreter: py launcher latest, then python3.
   * Returns only a Python >= MIN_PYTHON (a py -3.x hit that is too old
   * must NOT block trying the newer py -3 / python3 candidates). */
  discoverInterpreter(): DiscoveredInterpreter | null {
    const candidates: { path: string; args: readonly string[] }[] =
      this.osPlatform === "win32"
        ? [
            { path: "py", args: ["-3"] },
            { path: "py", args: ["-3.11"] },
            { path: "python", args: [] },
          ]
        : this.osPlatform === "darwin"
          ? [
              { path: "/usr/bin/python3", args: [] },
              { path: "python3", args: [] },
            ]
          : [
              { path: "/usr/bin/python3", args: [] },
              { path: "python3", args: [] },
            ];

    for (const c of candidates) {
      try {
        const output = this._execFileSync(c.path, [...c.args, "--version"], {
          encoding: "utf-8",
          timeout: 5000,
        });
        const ver = parsePythonVersion(output);
        if (ver && isAtLeast(ver, MIN_PYTHON)) {
          return { path: c.path, version: ver };
        }
      } catch {
        // try next candidate
      }
    }
    return null;
  }

  // ── 2. Platform gates ──

  /** Platform/container gates: Flatpak/Snap unsupported, macOS no
   * auto-download, interpreter discovery must have succeeded. */
  platformGate(): PlatformGate {
    if (detectFlatpak() || detectSnap()) {
      return {
        ok: false,
        code: "FLATPAK_SNAP_UNSUPPORTED",
        message:
          "Flatpak and Snap are not supported. Install Python 3.11+ natively.",
        platformAction:
          "Install Python 3.11+ from python.org or package manager",
      };
    }
    const osArchStr = getOsArch(this.osPlatform, this.osArch);
    const isMac = this.osPlatform === "darwin";
    if (isMac && ["macos-x64", "macos-arm64"].includes(osArchStr)) {
      return {
        ok: false,
        code: "NO_PYTHON",
        message:
          "No Python 3.11+ found. macOS auto-download disabled until signed/notarized artifacts exist.",
        platformAction: "Install Python 3.11+ from python.org or Homebrew",
      };
    }
    if (["windows-x64", "linux-x64"].includes(osArchStr)) {
      return {
        ok: false,
        code: "NO_PYTHON",
        message: "No Python 3.11+ found and automatic download failed.",
        platformAction: "Install Python 3.11+ manually",
      };
    }
    return {
      ok: false,
      code: "FALLBACK_UNAVAILABLE",
      message: "No Python found and this platform has no validated fallback.",
      platformAction: "Install Python 3.11+ manually from python.org",
    };
  }

  // ── 3. ONE one-time install ──

  /**
   * Base interpreter for the managed venv: an explicit user-selected
   * executable when one is configured (the setup wizard's "Python
   * executable" field), else the discovery chain.  An explicit choice is
   * FAIL-CLOSED: a missing path, a non-interpreter, or a version below
   * MIN_PYTHON is reported by name — the install never silently switches
   * to a different interpreter than the one the user selected.
   */
  private _resolveBaseInterpreter(override?: string): DiscoveredInterpreter {
    const explicit = override?.trim();
    if (explicit) {
      if (!this._fs.existsSync(explicit)) {
        throw new Error(`Python executable not found: ${explicit}`);
      }
      let output: string;
      try {
        output = this._execFileSync(explicit, ["--version"], {
          encoding: "utf-8",
          timeout: 5000,
        });
      } catch {
        throw new Error(`Not a runnable Python interpreter: ${explicit}`);
      }
      const version = parsePythonVersion(output);
      if (!version) {
        throw new Error(
          `Could not read a Python version from: ${explicit} (${output.trim()})`
        );
      }
      if (!isAtLeast(version, MIN_PYTHON)) {
        throw new Error(
          `Python ${version} is older than the required ${MIN_PYTHON}: ${explicit}`
        );
      }
      return { path: explicit, version };
    }
    const discovered = this.discoverInterpreter();
    if (!discovered) {
      const gate = this.platformGate();
      throw new Error(
        `No Python ${MIN_PYTHON}+ found (${gate.ok ? "no interpreter" : gate.message})`
      );
    }
    return discovered;
  }

  /**
   * ONE consented install into a NEW candidate directory under
   * ~/.paperforge/runtime/ (`venv-<version>-<suffix>`): venv + ONE pinned
   * `paperforge[vector]==<expectedVersion>` + fresh-child verify that the
   * OBSERVED version equals the requested version.  The previously
   * activated environment is never modified or deleted here; a failure or
   * cancellation removes only the candidate (#260).  NEVER writes the
   * pointer (Python owns publication) and returns only an ephemeral
   * result — nothing is cached, nothing is usable until the caller's
   * handshake + `paperforge setup` succeed.
   *
   * `interpreterOverride` is the configured base interpreter (settings
   * `python_path`); omitted/empty falls back to discovery.
   */
  async installOnce(
    expectedVersion: string,
    signal?: AbortSignal,
    interpreterOverride?: string,
    onStage?: (stage: "venv" | "pip" | "verify") => void
  ): Promise<{ pythonPath: string; observedVersion: string }> {
    if (signal?.aborted) throw new AbortError("Operation was cancelled");

    const discovered = this._resolveBaseInterpreter(interpreterOverride);

    if (signal?.aborted) throw new AbortError("Operation was cancelled");

    // #260: every attempt targets its own candidate directory; the
    // currently activated environment is never touched, so a failed or
    // cancelled upgrade leaves it runnable.  Older directories are retired
    // only after a successful publish (retireUnusedRuntimes).
    const candidateDir = this._candidateDir(expectedVersion);
    const pythonExe = this.pythonExeFor(candidateDir);
    const installKey = runtimeKey(this.rootDir);
    if (activeInstalls.has(installKey)) {
      throw new Error(
        "Another PaperForge runtime install is already running for this runtime directory"
      );
    }
    // In-memory guard first (fast, same renderer), then a CROSS-PROCESS lock:
    // Obsidian's settings window and main window are separate renderers with
    // separate plugin instances, and two pips into one runtime directory
    // deadlock on Windows file locks — observed as two concurrent `pip
    // install` children.
    const releaseLock = this._acquireInstallLock();
    activeInstalls.add(installKey);
    try {
      // A brand-new directory is always clean: there is no stale dist-info
      // for pip to trust, so a damaged run can never survive.
      this._fs.mkdirSync(candidateDir, { recursive: true });
      onStage?.("venv");
      await this._exec(
        discovered.path,
        ["-m", "venv", candidateDir],
        { timeout: 60000, signal },
        "venv creation"
      );
      if (signal?.aborted) throw new AbortError("Operation was cancelled");
      onStage?.("pip");
      await this._exec(
        pythonExe,
        ["-m", "pip", "install", `paperforge[vector]==${expectedVersion}`],
        // Vector dependencies are large; a cold download can exceed the
        // default two minutes while still making progress.
        { timeout: 600000, signal },
        "pip install"
      );
      if (signal?.aborted) throw new AbortError("Operation was cancelled");
      onStage?.("verify");
      const observed = await this._probeVersion(pythonExe, signal);
      if (
        !observed ||
        normalizeReleaseVersion(observed) !==
          normalizeReleaseVersion(expectedVersion)
      ) {
        throw new Error(
          `installed version mismatch: observed ${observed!} != requested ${expectedVersion}`
        );
      }
    } catch (err) {
      // This attempt owns ONLY the candidate: terminate the child first
      // (deleting a venv out from under a live pip leaves Windows handles),
      // then drop the candidate.  The activated environment stays intact;
      // a candidate that cannot be removed yet is retired on the next
      // success by retireUnusedRuntimes.
      this._terminateActiveChild();
      this._terminateVenvProcesses(candidateDir);
      try {
        this._fs.rmSync(candidateDir, { recursive: true, force: true });
      } catch {
        // Best-effort — never mask the real install failure.
      }
      throw err;
    } finally {
      activeInstalls.delete(installKey);
      this._activeChild = null;
      releaseLock();
    }
    return { pythonPath: pythonExe, observedVersion: expectedVersion };
  }

  // ── 4. Handshake ──

  /**
   * Handshake after installOnce (#143 §7): TWO mandatory checks —
   *   1. the fresh interpreter reports the expected version, AND
   *   2. Python's OWN installation probe (`paperforge probe installation
   *      --json`) in a fresh process returns a KNOWN state.
   * Fail-closed: version mismatch, probe process failure, malformed JSON,
   * or an unexpected reason all FAIL the handshake.  Explicit pre-setup
   * exceptions that PASS: installation.ready, installation.config_missing,
   * installation.config_corrupt, and the runtime-pointer states emitted
   * before `paperforge setup` publishes the pointer.  A version mismatch is
   * not a pre-setup state.
   * vaultPath is REQUIRED — a handshake without the capability probe is
   * not a handshake.
   */
  async handshake(
    expectedVersion: string,
    opts: {
      pythonPath?: string;
      signal?: AbortSignal;
      vaultPath: string;
    }
  ): Promise<{ ok: boolean; observedVersion: string | null; reason?: string }> {
    const pythonPath = opts.pythonPath ?? this.pythonExeFor(this.venvDir);
    if (!this._fs.existsSync(pythonPath)) {
      return {
        ok: false,
        observedVersion: null,
        reason: "interpreter missing",
      };
    }
    try {
      const observed = await this._probeVersion(pythonPath, opts.signal);
      if (
        !observed ||
        normalizeReleaseVersion(observed) !==
          normalizeReleaseVersion(expectedVersion)
      ) {
        return {
          ok: false,
          observedVersion: observed,
          reason: `version mismatch: observed ${observed!} != expected ${expectedVersion}`,
        };
      }
      // Check 2 (mandatory): Python's installation probe in a fresh
      // process.  Null (probe failure / malformed JSON) FAILS closed.
      const probe = await this._probeInstallation(
        pythonPath,
        opts.vaultPath,
        expectedVersion,
        opts.signal
      );
      if (probe === null) {
        return {
          ok: false,
          observedVersion: observed,
          reason:
            "installation probe failed or returned an unparseable envelope",
        };
      }
      if (probe === "installation.version_mismatch") {
        return {
          ok: false,
          observedVersion: observed,
          reason: "installation probe reports version mismatch",
        };
      }
      if (
        probe !== "installation.ready" &&
        probe !== "installation.config_missing" &&
        probe !== "installation.config_corrupt" &&
        probe !== "installation.runtime_pointer_missing" &&
        probe !== "installation.runtime_pointer_stale" &&
        probe !== "installation.runtime_executable_missing"
      ) {
        return {
          ok: false,
          observedVersion: observed,
          reason: `unexpected installation probe state: ${probe}`,
        };
      }
    } catch (err) {
      return {
        ok: false,
        observedVersion: null,
        reason: err instanceof Error ? err.message : String(err),
      };
    }
    return { ok: true, observedVersion: expectedVersion };
  }

  // ── 5. Pointer READ (Python is the ONLY writer) ──

  /** Full schema-v1 validation — four fields, typed, absolute paths.
   * Returns null when absent or invalid (fail-closed; never guesses). */
  readPointer(): PointerInfo | null {
    const pointerPath = path.join(this.rootDir, POINTER_FILENAME);
    let raw: string;
    try {
      raw = this._fs.readFileSync(pointerPath, "utf-8");
    } catch {
      return null;
    }
    let ptr: Record<string, unknown>;
    try {
      ptr = JSON.parse(raw) as Record<string, unknown>;
    } catch {
      return null;
    }
    if (ptr.schema_version !== POINTER_SCHEMA_VERSION) return null;
    const {
      python_path: pp,
      environment_root: er,
      paperforge_version: pv,
    } = ptr;
    if (
      typeof pp !== "string" ||
      !pp ||
      typeof er !== "string" ||
      !er ||
      typeof pv !== "string" ||
      !pv
    ) {
      return null;
    }
    if (!path.isAbsolute(pp) || !path.isAbsolute(er)) return null;
    return {
      pythonPath: pp,
      environmentRoot: er,
      paperforgeVersion: pv,
    };
  }

  // ── Private helpers ──

  private _exec(
    command: string,
    args: readonly string[],
    opts: { timeout?: number; signal?: AbortSignal },
    label: string
  ): Promise<void> {
    const { promise, resolve, reject } = deferred<void>();
    const child = this._execFile(
      command,
      args,
      {
        ...opts,
        encoding: "utf-8",
        // Never inherit the app's CWD: a checkout in it would shadow the
        // module being installed/verified (`python -m paperforge` from a
        // repository root imports the source tree, not the runtime).
        cwd: os.tmpdir(),
      },
      (err, _stdout, stderr) => {
        if (err) {
          // `Command failed: …` alone says nothing actionable — carry the
          // tool's own last words (pip's ERROR line) into the message.
          const detail = String(stderr ?? "")
            .split(/\r?\n/)
            .map((line) => line.trim())
            .filter(Boolean)
            .slice(-3)
            .join(" | ");
          reject(
            new Error(
              `${label} failed: ${err.message}${detail ? ` — ${detail}` : ""}`
            )
          );
        } else {
          resolve();
        }
      }
    );
    // Remember the child so a failed install can terminate it BEFORE the
    // venv is deleted: on Windows a still-running pip keeps handles in
    // site-packages, and the next attempt then dies with WinError 32.
    if (child && typeof child === "object") {
      this._activeChild = child as TrackedChild;
    }
    return promise;
  }

  /**
   * Terminate processes executing INSIDE the managed venv (probe children
   * left over from a module refresh).  Best-effort, Windows only: the
   * platform needs an OS-level kill to release the directory.
   */
  private _terminateVenvProcesses(dir: string = this.venvDir): void {
    if (this.osPlatform !== "win32") return;
    const escaped = dir.replace(/'/g, "''");
    const script =
      "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | " +
      `Where-Object { $_.ExecutablePath -like '${escaped}\\*' } | ` +
      "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }";
    try {
      this._execFileSync("powershell", ["-NoProfile", "-Command", script], {
        encoding: "utf-8",
        timeout: 20000,
      });
    } catch {
      // best effort — the caller falls back to a precise failure message
    }
  }

  /**
   * Terminate the currently tracked install child (and, on Windows, its
   * process tree).  Best-effort: the caller is already on an error path.
   */
  private _terminateActiveChild(): void {
    const child = this._activeChild;
    this._activeChild = null;
    if (!child) return;
    try {
      child.kill?.();
    } catch {
      // ignore — a dead child is the goal, not the outcome
    }
    if (this.osPlatform === "win32" && child.pid) {
      try {
        this._execFileSync(
          "taskkill",
          ["/PID", String(child.pid), "/T", "/F"],
          {
            encoding: "utf-8",
            timeout: 10000,
          }
        );
      } catch {
        // taskkill is best-effort (the tree may already be gone)
      }
    }
  }

  /** Fresh-child probe: read and RETURN the observed version (never trust
   * the current process's module cache). */
  private _probeVersion(
    pythonPath: string,
    signal?: AbortSignal
  ): Promise<string | null> {
    const { promise, resolve, reject } = deferred<string | null>();
    this._execFile(
      pythonPath,
      ["-I", "-c", "import paperforge; print(paperforge.__version__)"],
      { timeout: 30000, signal, cwd: os.tmpdir() },
      (err, stdout) => {
        if (err) {
          reject(err);
        } else {
          const version = (stdout ?? "").trim() || null;
          resolve(version);
        }
      }
    );
    return promise;
  }

  /** Fresh-child `paperforge probe installation --json`; returns the reason
   * code when parseable, else null (probe unavailable). */
  private _probeInstallation(
    pythonPath: string,
    vaultPath: string,
    expectedVersion: string,
    signal?: AbortSignal
  ): Promise<string | null> {
    const { promise, resolve, reject } = deferred<string | null>();
    const env: Record<string, string | undefined> = { ...process.env };
    // The fresh child must import the runtime being verified.  PYTHONPATH /
    // PYTHONHOME inherited from the app would redirect the import (an
    // editable checkout on PYTHONPATH, for instance) and make this check
    // report a fake mismatch.
    delete env.PYTHONPATH;
    delete env.PYTHONHOME;
    this._execFile(
      pythonPath,
      [
        // -P: never prepend the working directory to sys.path (3.11+).
        "-P",
        "-m",
        "paperforge",
        "--vault",
        vaultPath,
        "probe",
        "installation",
        "--json",
        "--expected-version",
        expectedVersion,
      ],
      { timeout: 30000, signal, cwd: os.tmpdir(), env },
      (err, stdout) => {
        if (err) {
          // Probe unavailable is not itself a handshake failure — the
          // version check already ran; fail only on a parsed mismatch.
          resolve(null);
          return;
        }
        try {
          const envelope = JSON.parse(stdout) as {
            reason?: { code?: string };
          };
          resolve(envelope.reason?.code ?? null);
        } catch {
          resolve(null);
        }
      }
    );
    return promise;
  }
}

/** Minimal AbortError so callers can distinguish cancellation. */
export class AbortError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AbortError";
  }
}
