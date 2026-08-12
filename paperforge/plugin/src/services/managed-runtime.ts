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
  opts: { timeout?: number; encoding?: string; signal?: AbortSignal },
  cb: ExecFileCallback
) => void;
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
   * ONE consented one-time install into ~/.paperforge/runtime/venv:
   * venv + ONE pinned `paperforge[vector]==<expectedVersion>` + fresh-child
   * verify that the OBSERVED version equals the requested version.
   * NEVER writes the pointer (Python owns publication) and returns only an
   * ephemeral result — nothing is cached, nothing is usable until the
   * caller's handshake + `paperforge setup` succeed.
   */
  async installOnce(
    expectedVersion: string,
    signal?: AbortSignal
  ): Promise<{ pythonPath: string; observedVersion: string }> {
    if (signal?.aborted) throw new AbortError("Operation was cancelled");

    const discovered = this.discoverInterpreter();
    if (!discovered) {
      const gate = this.platformGate();
      throw new Error(
        `No Python ${MIN_PYTHON}+ found (${gate.ok ? "no interpreter" : gate.message})`
      );
    }

    if (signal?.aborted) throw new AbortError("Operation was cancelled");

    const pythonExe = this.pythonExeFor(this.venvDir);
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
        { timeout: 120000, signal },
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
      // Clean the half-installed venv; nothing is published, nothing kept.
      try {
        this._fs.rmSync(this.venvDir, { recursive: true, force: true });
      } catch {}
      throw err;
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
   * exceptions that PASS: installation.ready, installation.config_missing
   * and installation.config_corrupt (the later `paperforge setup` step
   * resolves config states; a version mismatch is not a pre-setup state).
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
        probe !== "installation.config_corrupt"
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
    this._execFile(command, args, { ...opts, encoding: "utf-8" }, (err) => {
      if (err) {
        reject(new Error(`${label} failed: ${err.message}`));
      } else {
        resolve();
      }
    });
    return promise;
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
      { timeout: 30000, signal },
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
    this._execFile(
      pythonPath,
      [
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
      { timeout: 30000, signal },
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
