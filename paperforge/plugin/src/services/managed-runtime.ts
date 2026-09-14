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
 * ONE one-time venv + ONE pinned install (installOnce), handshake, pointer
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
   * ONE consented one-time install into ~/.paperforge/runtime/venv:
   * venv + ONE pinned `paperforge[vector]==<expectedVersion>` + fresh-child
   * verify that the OBSERVED version equals the requested version.
   * NEVER writes the pointer (Python owns publication) and returns only an
   * ephemeral result — nothing is cached, nothing is usable until the
   * caller's handshake + `paperforge setup` succeed.
   *
   * `interpreterOverride` is the configured base interpreter (settings
   * `python_path`); omitted/empty falls back to discovery.
   */
  async installOnce(
    expectedVersion: string,
    signal?: AbortSignal,
    interpreterOverride?: string
  ): Promise<{ pythonPath: string; observedVersion: string }> {
    if (signal?.aborted) throw new AbortError("Operation was cancelled");

    const discovered = this._resolveBaseInterpreter(interpreterOverride);

    if (signal?.aborted) throw new AbortError("Operation was cancelled");

    const pythonExe = this.pythonExeFor(this.venvDir);
    const installKey = runtimeKey(this.rootDir);
    if (activeInstalls.has(installKey)) {
      throw new Error(
        "Another PaperForge runtime install is already running for this runtime directory"
      );
    }
    activeInstalls.add(installKey);
    try {
      this._fs.mkdirSync(this.venvDir, { recursive: true });
      await this._exec(
        discovered.path,
        ["-m", "venv", this.venvDir],
        { timeout: 60000, signal },
        "venv creation"
      );
      if (signal?.aborted) throw new AbortError("Operation was cancelled");
      await this._exec(
        pythonExe,
        ["-m", "pip", "install", `paperforge[vector]==${expectedVersion}`],
        // Vector dependencies are large; a cold download can exceed the
        // default two minutes while still making progress.
        { timeout: 600000, signal },
        "pip install"
      );
      if (signal?.aborted) throw new AbortError("Operation was cancelled");
      const observed = await this._probeVersion(pythonExe, signal);
      if (observed !== expectedVersion) {
        throw new Error(
          `installed version mismatch: observed ${observed!} != requested ${expectedVersion}`
        );
      }
    } catch (err) {
      // Terminate the child FIRST: deleting a venv out from under a live
      // pip leaves a process holding site-packages handles, and every
      // later attempt then fails with a Windows sharing violation.
      this._terminateActiveChild();
      // Clean the half-installed venv; nothing is published, nothing kept.
      try {
        this._fs.rmSync(this.venvDir, { recursive: true, force: true });
      } catch (cleanupErr) {
        // Never hide this: a venv that cannot be removed means the next
        // attempt will fail for a reason that is not the install itself.
        throw new Error(
          `${err instanceof Error ? err.message : String(err)}\n` +
            `Additionally, the previous runtime directory could not be removed (${
              cleanupErr instanceof Error ? cleanupErr.message : String(cleanupErr)
            }). Close any running PaperForge process and try again.`
        );
      }
      throw err;
    } finally {
      activeInstalls.delete(installKey);
      this._activeChild = null;
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
      if (observed !== expectedVersion) {
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
      (err) => {
        if (err) {
          reject(new Error(`${label} failed: ${err.message}`));
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
        this._execFileSync("taskkill", ["/PID", String(child.pid), "/T", "/F"], {
          encoding: "utf-8",
          timeout: 10000,
        });
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
