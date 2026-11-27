/**
 * NodeProcessTransport — THE single child-process authority for PaperForge.
 *
 * Ticket 07 step 6 item 4: the LongTaskClient streaming/process engine was
 * merged here (`services/long-task-client.ts` tombstoned) so ALL
 * child-process authority lives at the transport root:
 * - Resolves the canonical Python interpreter via ManagedRuntime pointer.
 * - Sanitizes subprocess environment via paperforgeEnrichedEnv().
 * - Submits credentials strictly over stdin (never argv/env).
 * - execute(): single-result mode; stream(): #137 structured-stream mode
 *   with the frozen stateful protocol-fail-closed NDJSON parser.
 * - Cooperative cancellation via stdin `PAPERFORGE_STOP`, grace window,
 *   then hard escalation (Windows `taskkill /T /F`, POSIX process-group
 *   SIGKILL). shell:false everywhere.
 */

import { execFileSync, spawn, type ChildProcess } from "child_process";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import {
  type Transport,
  type ExecuteOptions,
  type StreamOptions,
  type StreamHandle,
  type NdjsonEvent,
  type LongTaskOutcome,
  type DaemonPushEvent,
  AsyncEventQueue,
} from "./transport";
import { stripCredentialEnv } from "../services/secret-storage";
import {
  readRuntimePointer,
  resolveRuntimeCommand,
} from "../services/managed-runtime";
import { resolveNativeDaemonBinary } from "../services/native-daemon";
import {
  buildProxyEnvOverlay,
  getCachedSystemProxy,
  hasExplicitProxyEnv,
} from "../services/system-proxy";
import {
  bootstrapPythonSource,
  installerLogPath,
  installerRun,
  installerShellCommand,
  posixInstallerScript,
  uvBinaryPath,
  uvInstallerRun,
  uvInstallerScript,
  windowsInstallerScript,
  type RuntimeInstallerAction,
} from "../services/runtime-installer-launcher";

const KNOWN_EVENTS: ReadonlySet<string> = new Set([
  "start",
  "preflight",
  "phase",
  "progress",
  "paper_settled",
  "heartbeat",
  "item_result",
  "result",
  "error",
  "cancelled",
]);
const TERMINAL_EVENTS: ReadonlySet<string> = new Set([
  "result",
  "error",
  "cancelled",
]);

/** Stateful, protocol-fail-closed NDJSON stream parser (#137 §5). */
export class NdjsonStreamParser {
  private _buffer = "";
  private _terminalSeen = false;
  private _protocolFailure: string | undefined;

  get protocolFailure(): string | undefined {
    return this._protocolFailure;
  }

  get terminalSeen(): boolean {
    return this._terminalSeen;
  }

  /** Feed a raw chunk; returns the parsed events (empty after failure). */
  feed(chunk: string): NdjsonEvent[] {
    if (this._protocolFailure) return [];
    const full = this._buffer + chunk;
    const lines = full.split("\n");
    this._buffer = lines.pop() ?? "";

    const out: NdjsonEvent[] = [];
    for (const line of lines) {
      if (!line.trim()) continue;
      let parsed: NdjsonEvent;
      try {
        parsed = JSON.parse(line) as NdjsonEvent;
      } catch {
        this._protocolFailure = `non-JSON stdout line: ${line.slice(0, 80)}`;
        break;
      }
      if (parsed.schema_version !== 1) {
        this._protocolFailure = `schema_version ${parsed.schema_version} != 1`;
        break;
      }
      if (typeof parsed.event !== "string" || !KNOWN_EVENTS.has(parsed.event)) {
        this._protocolFailure = `unknown event: ${String(parsed.event)}`;
        break;
      }
      if (this._terminalSeen) {
        this._protocolFailure = "event after terminal";
        break;
      }
      if (TERMINAL_EVENTS.has(parsed.event)) {
        this._terminalSeen = true;
      }
      out.push(parsed);
    }
    return out;
  }

  /** EOF without a terminal event is a protocol failure. */
  finishEOF(): void {
    if (!this._protocolFailure && !this._terminalSeen) {
      this._protocolFailure = "EOF without terminal event";
    }
  }
}

export interface LongTaskOptions {
  onEvent: (event: NdjsonEvent) => void;
  env?: Record<string, string | undefined>;
  /** Grace window after the stop token before hard escalation. */
  graceMs?: number;
  /** Close stdin for commands that do not support cooperative stop. */
  closeStdin?: boolean;
  /** Injection seam: the transport passes its own spawnFn through. */
  spawnFn?: typeof spawn;
}

export interface LongTaskHandle {
  /** Cooperative stop: stdin token, then grace, then hard escalation. */
  stop: () => void;
  promise: Promise<LongTaskOutcome>;
}

export function hardKill(child: ChildProcess): void {
  if (!child.pid) {
    try {
      child.kill("SIGKILL");
    } catch {
      // ignore
    }
    return;
  }
  if (process.platform === "win32") {
    try {
      spawn("taskkill", ["/T", "/F", "/PID", String(child.pid)], {
        stdio: "ignore",
      });
    } catch {
      child.kill("SIGKILL");
    }
  } else {
    try {
      // Process-group kill (detached children live in their own group).
      process.kill(-child.pid, "SIGKILL");
    } catch {
      child.kill("SIGKILL");
    }
  }
}

/**
 * THE single structured-stream client.  Spawns with shell:false, pipes
 * stdin for the cooperative stop token, parses stdout with the stateful
 * protocol-fail-closed parser, escalates hard after the grace window.
 * Env is the redacted paperforgeEnrichedEnv() unless explicitly provided —
 * never merged with process.env.
 */
export function runLongTask(
  pythonExe: string,
  extraArgs: string[],
  vaultPath: string,
  argv: string[],
  opts: LongTaskOptions
): LongTaskHandle {
  const env = opts.env ?? paperforgeEnrichedEnv();
  const spawnImpl = opts.spawnFn ?? spawn;
  const child = spawnImpl(
    pythonExe,
    [...extraArgs, "-m", "paperforge", "--vault", vaultPath, ...argv],
    {
      cwd: vaultPath,
      shell: false,
      windowsHide: true,
      env,
      stdio: ["pipe", "pipe", "pipe"],
    }
  );
  executeChildRegistry.add(child);
  if (opts.closeStdin) child.stdin?.end();

  const parser = new NdjsonStreamParser();
  const events: NdjsonEvent[] = [];
  let hardKilled = false;
  let settled = false;
  // A stop the user asked for: the token may be ignored because the child is
  // inside a phase with no safe point (a cold native import in the embed
  // prepare, #330), so the kill escalation ends it without a terminal event.
  let stopRequested = false;
  let graceTimer: NodeJS.Timeout | undefined;
  // Always drain stderr: it is diagnostics for the caller, and an unread
  // stderr pipe fills (win32: ~4KB) and blocks the child mid-run.
  const STDERR_TAIL = 8000;
  let stderrTail = "";

  child.stdout?.setEncoding("utf-8");
  child.stdout?.on("data", (chunk: string) => {
    for (const ev of parser.feed(chunk)) {
      events.push(ev);
      try {
        opts.onEvent(ev);
      } catch {
        // Isolate UI listener errors so remaining NDJSON events & terminal survive.
      }
    }
  });
  if (typeof child.stderr?.setEncoding === "function") {
    child.stderr.setEncoding("utf-8");
  }
  child.stderr?.on("data", (chunk: string | Buffer) => {
    stderrTail = (stderrTail + chunk.toString()).slice(-STDERR_TAIL);
  });

  const outcome = new Promise<LongTaskOutcome>((resolve) => {
    child.on("close", (code: number | null) => {
      settled = true;
      executeChildRegistry.delete(child);
      clearTimeout(graceTimer);
      parser.finishEOF();
      // #269: the EOF signature must say HOW the child died, so a killed
      // stream is distinguishable from a silent one.
      const death =
        parser.protocolFailure === "EOF without terminal event"
          ? [
              typeof code === "number" ? `exit ${code}` : "",
              child.signalCode ? `signal ${child.signalCode}` : "",
            ]
              .filter(Boolean)
              .join(", ")
          : "";
      const terminal = events.find((event) => TERMINAL_EVENTS.has(event.event));
      resolve({
        ok:
          !parser.protocolFailure &&
          code === 0 &&
          terminal?.event === "result" &&
          terminal.result?.ok !== false,
        exitCode: code,
        // #330: a stop we wrote the token for stays a cancellation when the
        // child had to be killed before reaching a safe point (rc != 130). A
        // stop that lost the race must not relabel a finished build: it only
        // counts while no terminal event arrived.
        cancelled:
          code === 130 ||
          terminal?.event === "cancelled" ||
          (stopRequested && !parser.terminalSeen),
        events,
        protocolFailure: parser.protocolFailure
          ? death
            ? `${parser.protocolFailure} (${death})`
            : parser.protocolFailure
          : undefined,
        stderr: stderrTail,
      });
    });
    child.on("error", (err: Error) => {
      settled = true;
      executeChildRegistry.delete(child);
      clearTimeout(graceTimer);
      resolve({
        ok: false,
        exitCode: -1,
        cancelled: false,
        events,
        protocolFailure: `spawn error: ${err.message}`,
        stderr: stderrTail,
      });
    });
  });

  return {
    stop: () => {
      if (settled || stopRequested) return;
      stopRequested = true;
      try {
        child.stdin?.write("PAPERFORGE_STOP\n");
      } catch {
        // stdin closed — the exit path still settles.
      }
      if (graceTimer) return;
      const graceMs = opts.graceMs ?? 5000;
      graceTimer = setTimeout(() => {
        if (child.exitCode === null && !hardKilled) {
          hardKilled = true;
          hardKill(child);
        }
      }, graceMs);
    },
    promise: outcome,
  };
}

// ── Host env/PATH bootstrap (moved from python-bridge, step 6 item 5) ──────

let _gitDir: string | null = null;
let _gitDirResolved = false;

/** Locate git directory via pure-JS PATH + standard locations without blocking the main thread with execFileSync. */
function resolveGitDir(): string | null {
  if (_gitDirResolved) return _gitDir;
  _gitDirResolved = true;
  const exeName = process.platform === "win32" ? "git.exe" : "git";
  const pathEnv = process.env.PATH || "";
  const candidates: string[] = [];
  for (const dir of pathEnv.split(path.delimiter)) {
    const trimmed = dir.trim();
    if (trimmed) candidates.push(trimmed);
  }
  if (process.platform === "win32") {
    candidates.push(
      "C:\\Program Files\\Git\\cmd",
      "C:\\Program Files\\Git\\bin",
      "C:\\Program Files (x86)\\Git\\cmd"
    );
    const localAppData = process.env.LOCALAPPDATA;
    if (localAppData) {
      candidates.push(path.join(localAppData, "Programs", "Git", "cmd"));
    }
  } else {
    candidates.push("/usr/bin", "/usr/local/bin", "/opt/homebrew/bin");
  }
  for (const dir of candidates) {
    try {
      if (fs.existsSync(path.join(dir, exeName))) {
        _gitDir = dir;
        return _gitDir;
      }
    } catch {
      // ignore inaccessible directory entries
    }
  }
  return _gitDir;
}

/** Redacted child env: PATH enrichment + credential strip. Never merges
 * process.env secrets into the child.
 *
 * PYTHONPATH / PYTHONHOME are removed: an inherited value (a dev checkout
 * on PYTHONPATH, a foreign PYTHONHOME) redirects `-m paperforge` away from
 * the runtime being dispatched, which makes the CLI report another
 * installation's version. */
export function paperforgeEnrichedEnv(): Record<string, string | undefined> {
  const env: Record<string, string | undefined> = { ...process.env };
  delete env.PYTHONPATH;
  delete env.PYTHONHOME;
  if (!hasExplicitProxyEnv(env)) {
    const cachedProxy = getCachedSystemProxy();
    Object.assign(
      env,
      buildProxyEnvOverlay(cachedProxy.proxyUrl, env, cachedProxy.noProxy)
    );
  }
  const plat = process.platform;
  const home = os.homedir();
  const extras: string[] = [];
  const tailExtras: string[] = [];
  const gitDir = resolveGitDir();
  if (gitDir) extras.push(gitDir);
  if (plat === "darwin") {
    extras.push(
      "/opt/homebrew/bin",
      "/usr/local/bin",
      "/usr/bin",
      `${home}/.local/bin`,
      `${home}/.cargo/bin`,
      `${home}/.pyenv/shims`,
      `${home}/miniforge3/bin`,
      `${home}/miniconda3/bin`
    );
  } else if (plat === "linux") {
    extras.push(
      "/usr/local/bin",
      "/usr/bin",
      "/snap/bin",
      `${home}/.local/bin`,
      `${home}/.cargo/bin`,
      `${home}/.pyenv/shims`,
      `${home}/miniforge3/bin`,
      `${home}/miniconda3/bin`
    );
  } else if (plat === "win32") {
    const localAppData =
      env.LOCALAPPDATA ||
      process.env.LOCALAPPDATA ||
      (home ? path.join(home, "AppData", "Local") : "");
    const programFiles =
      env.ProgramFiles || process.env.ProgramFiles || "C:\\Program Files";
    for (const ver of ["Python313", "Python312", "Python311"]) {
      if (localAppData) {
        const pyDir = path.join(localAppData, "Programs", "Python", ver);
        tailExtras.push(pyDir, path.join(pyDir, "Scripts"));
      }
      const pfDir = path.join(programFiles, ver);
      tailExtras.push(pfDir, path.join(pfDir, "Scripts"));
      const rootDir = `C:\\${ver}`;
      tailExtras.push(rootDir, path.join(rootDir, "Scripts"));
    }
  }
  // Children resolve binaries through PATH only. A GUI host can start with a
  // PATH that is empty or stripped to nothing usable (menu-launched apps on
  // macOS/Linux, some sandboxes); the installer then fails with "not
  // recognized" even though probing from this process worked. Keep a floor.
  const floor =
    plat === "win32"
      ? "C:\\Windows\\System32;C:\\Windows"
      : "/usr/local/bin:/usr/bin:/bin";
  const cur = env.PATH || process.env.PATH || floor;
  env.PATH = [...extras, cur, ...tailExtras]
    .filter(Boolean)
    .join(path.delimiter);
  return stripCredentialEnv(env) as Record<string, string | undefined>;
}

export interface NodeProcessTransportOptions {
  vaultPath: string;
  /** Child process spawner (default: child_process.spawn). */
  spawnFn?: typeof spawn;
  /** Version probe (default: child_process.execFileSync). */
  execFileSyncFn?: typeof execFileSync;
  /** Installer log destination (tests point this at a temp file). */
  installerLogPath?: () => string;
  /** Keep a warm stdio daemon alive across short execute() RPCs (default: true unless custom spawnFn is injected). */
  useDaemon?: boolean;
  /** Optional explicit path to native Rust `paperforge-daemon` binary (auto-discovered when spawnFn is default). */
  nativeDaemonPath?: string | null;
}

/** Interpreter names to probe, most specific first. */
export function basePythonCandidates(
  platform: NodeJS.Platform = process.platform
): string[] {
  return platform === "win32"
    ? ["py", "python3", "python"]
    : ["python3", "python"];
}

export class ExecuteChildRegistry extends Set<ChildProcess> {
  get(child: ChildProcess): ChildProcess | undefined {
    return this.has(child) ? child : undefined;
  }
  set(child: ChildProcess, _value?: unknown): this {
    this.add(child);
    return this;
  }
}

const executeChildRegistry = new ExecuteChildRegistry();

function reapExecuteChildrenImpl(): void {
  for (const child of [...executeChildRegistry]) {
    if (child.exitCode == null && child.signalCode == null) hardKill(child);
    executeChildRegistry.delete(child);
  }
}

interface PendingDaemonRpc {
  resolve: (stdout: string) => void;
  reject: (err: Error) => void;
  timer: ReturnType<typeof setTimeout> | null;
}

interface ActiveDaemonStream {
  streamId: string;
  parser: NdjsonStreamParser;
  events: NdjsonEvent[];
  stopRequested: boolean;
  onEvent: (ev: NdjsonEvent) => void;
  resolve: (outcome: LongTaskOutcome) => void;
}

interface DaemonSession {
  key: string;
  child: ChildProcess;
  nextId: number;
  nextStreamSeq: number;
  buffer: string;
  settledAny: boolean;
  pending: Map<number, PendingDaemonRpc>;
  streams: Map<string, ActiveDaemonStream>;
}

export class NodeProcessTransport implements Transport {
  /** In-flight Python children from both result and stream execution. */
  static executeChildren: ExecuteChildRegistry = executeChildRegistry;
  static executeChildRegistry: ExecuteChildRegistry = executeChildRegistry;
  static children: ExecuteChildRegistry = executeChildRegistry;
  static childRegistry: ExecuteChildRegistry = executeChildRegistry;
  static _executeChildren: ExecuteChildRegistry = executeChildRegistry;
  static _childRegistry: ExecuteChildRegistry = executeChildRegistry;

  private readonly _vaultPath: string;
  private readonly _spawnFn: typeof spawn;
  private readonly _execFileSyncFn: typeof execFileSync;
  private readonly _installerLogPath: () => string;
  private readonly _useDaemon: boolean;
  private readonly _explicitNativeDaemonPath: string | null | undefined;
  private readonly _hasCustomSpawn: boolean;
  private _daemonSupported = true;
  private _daemon: DaemonSession | null = null;
  private _swapInFlight: Promise<void> | null = null;
  private readonly _daemonListeners = new Set<
    (event: DaemonPushEvent) => void
  >();

  constructor(options: NodeProcessTransportOptions) {
    this._vaultPath = options.vaultPath;
    this._hasCustomSpawn = options.spawnFn !== undefined;
    this._spawnFn = options.spawnFn ?? spawn;
    this._execFileSyncFn = options.execFileSyncFn ?? execFileSync;
    this._installerLogPath = options.installerLogPath ?? installerLogPath;
    this._useDaemon = options.useDaemon ?? options.spawnFn === undefined;
    this._explicitNativeDaemonPath = options.nativeDaemonPath;
  }

  private _resolveNativeDaemon(): string | null {
    if (this._explicitNativeDaemonPath === null) return null;
    if (this._explicitNativeDaemonPath) {
      return resolveNativeDaemonBinary({
        explicitPath: this._explicitNativeDaemonPath,
        vaultPath: this._vaultPath,
      });
    }
    // Preserve unit-test mock spawn expectations unless nativeDaemonPath is explicitly requested
    if (this._hasCustomSpawn) return null;
    return resolveNativeDaemonBinary({ vaultPath: this._vaultPath });
  }

  /** Resolve the interpreter from Python's published runtime pointer. */
  async resolvePython(): Promise<{ path: string; args: string[] }> {
    const cmd = resolveRuntimeCommand(readRuntimePointer());
    if (cmd) return { path: cmd.command, args: [...cmd.args] };

    // Expected setup state, not a failure: tag the existing NO_PYTHON
    // machine code (python-bridge taxonomy) so callers can suppress it from
    // the Console and offer setup recovery without parsing this message.
    const err = new Error(
      "PaperForge compute runtime is not installed yet. Open Settings → PaperForge and click Install (one-click setup, no terminal required)."
    ) as Error & { code: string };
    err.code = "NO_PYTHON";
    throw err;
  }

  /** First schooled interpreter that reports Python >= 3.11, returned as an
   * ABSOLUTE executable path.
   *
   * The name that probes successfully (`py`, a PATH shim) is not necessarily
   * resolvable by the installer's child `cmd`, which runs with the redacted
   * environment: on a hosted runner `py --version` works from Node while
   * `cmd /c ... py ...` answers "'py' is not recognized". Embedding
   * `sys.executable` keeps the script PATH-independent. */
  discoverBasePython(): string | null {
    const probes: Array<{ cmd: string; preArgs: string[] }> =
      basePythonCandidates().map((cmd) => ({ cmd, preArgs: [] }));
    if (process.platform === "win32") {
      // If `py` defaults to an older Python (<3.11), probe explicit 3.11+ py launcher tags.
      probes.push(
        { cmd: "py", preArgs: ["-3.13"] },
        { cmd: "py", preArgs: ["-3.12"] },
        { cmd: "py", preArgs: ["-3.11"] }
      );
    }
    const probeEnv = paperforgeEnrichedEnv() as NodeJS.ProcessEnv;
    for (const { cmd, preArgs } of probes) {
      try {
        const out = this._execFileSyncFn(cmd, [...preArgs, "--version"], {
          timeout: 5000,
          windowsHide: true,
          encoding: "utf-8",
          env: probeEnv,
        });
        const match = /Python\s+(\d+)\.(\d+)/.exec(String(out));
        if (!match || Number(match[1]) < 3 || Number(match[2]) < 11) continue;
        try {
          const exe = String(
            this._execFileSyncFn(
              cmd,
              [...preArgs, "-c", "import sys;print(sys.executable)"],
              {
                timeout: 5000,
                windowsHide: true,
                encoding: "utf-8",
                env: probeEnv,
              }
            )
          ).trim();
          // Skip Windows Microsoft Store app-execution aliases (they are zero-byte stubs).
          if (exe && exe.toLowerCase().includes("\\microsoft\\windowsapps\\")) {
            continue;
          }
          return exe || cmd;
        } catch {
          // Version probe worked but the path probe did not: the bare name is
          // still better than nothing (a PATH that worked for this process).
          return cmd;
        }
      } catch {
        // candidate absent — try the next one
      }
    }
    return null;
  }

  static reapExecuteChildren(): void {
    reapExecuteChildrenImpl();
  }
  static reapAll(): void {
    reapExecuteChildrenImpl();
  }
  static reapAllExecuteChildren(): void {
    reapExecuteChildrenImpl();
  }
  static killExecuteChildren(): void {
    reapExecuteChildrenImpl();
  }
  static killAllExecuteChildren(): void {
    reapExecuteChildrenImpl();
  }
  static clearExecuteChildren(): void {
    reapExecuteChildrenImpl();
  }

  get executeChildren(): ExecuteChildRegistry {
    return executeChildRegistry;
  }
  get executeChildRegistry(): ExecuteChildRegistry {
    return executeChildRegistry;
  }
  get children(): ExecuteChildRegistry {
    return executeChildRegistry;
  }
  get childRegistry(): ExecuteChildRegistry {
    return executeChildRegistry;
  }
  get _executeChildren(): ExecuteChildRegistry {
    return executeChildRegistry;
  }
  get _childRegistry(): ExecuteChildRegistry {
    return executeChildRegistry;
  }

  reapExecuteChildren(): void {
    reapExecuteChildrenImpl();
  }
  reapAll(): void {
    reapExecuteChildrenImpl();
  }
  reapAllExecuteChildren(): void {
    reapExecuteChildrenImpl();
  }
  killExecuteChildren(): void {
    reapExecuteChildrenImpl();
  }
  killAllExecuteChildren(): void {
    reapExecuteChildrenImpl();
  }
  clearExecuteChildren(): void {
    reapExecuteChildrenImpl();
  }

  /** Discover portable or system-installed uv binary without spawning child processes. */
  discoverUv(): string | null {
    const localUv = uvBinaryPath(os.homedir(), process.platform);
    if (fs.existsSync(localUv)) return localUv;
    const pathVar = (paperforgeEnrichedEnv().PATH ?? "").split(path.delimiter);
    const exeName = process.platform === "win32" ? "uv.exe" : "uv";
    for (const dir of pathVar) {
      if (!dir) continue;
      const candidate = path.join(dir, exeName);
      if (fs.existsSync(candidate)) return candidate;
    }
    return null;
  }

  /**
   * Open the external installer in a terminal window: pip --user installs the
   * CLI, then the CLI creates/verifies the runtime and publishes the pointer.
   * When no system Python 3.11+ exists and uv is present or auto-download is
   * allowed, falls back to the portable uv zero-Python bootstrapper.
   * Obsidian only watches the pointer; it never installs anything itself.
   */
  launchRuntimeInstaller(
    action: RuntimeInstallerAction,
    version: string,
    options?: {
      allowUvDownload?: boolean;
      proxyUrl?: string;
      preferCnMirror?: boolean;
    }
  ): { ok: boolean; python?: string; error?: string; logPath?: string } {
    const logPath = this._installerLogPath();
    const extraEnv: Record<string, string> = {};
    if (options?.proxyUrl?.trim()) {
      const p = options.proxyUrl.trim();
      extraEnv.PAPERFORGE_PROXY = p;
      extraEnv.HTTP_PROXY = p;
      extraEnv.HTTPS_PROXY = p;
    }
    if (options?.preferCnMirror) {
      extraEnv.PAPERFORGE_PREFER_CN_MIRROR = "1";
    }
    const python = this.discoverBasePython();
    if (!python) {
      if (!options?.allowUvDownload) {
        return {
          ok: false,
          error:
            "No Python 3.11+ found. Install Python from python.org, then retry.",
        };
      }
      const nativeBin = this._resolveNativeDaemon();
      if (nativeBin) {
        return this._spawnDetachedInstaller(
          {
            command: nativeBin,
            args: ["install-runtime", "--action", action, "--version", version],
          },
          logPath,
          "rust-uv",
          extraEnv
        );
      }
      const uv = this.discoverUv();
      const scriptPath = this._writeInstallerScript(
        uvInstallerScript({
          action,
          version,
          uvPath: uv,
          logPath,
        }),
        process.platform === "win32" ? "ps1" : "sh"
      );
      const run = uvInstallerRun(process.platform, scriptPath);
      return this._spawnDetachedInstaller(run, logPath, uv ?? "uv", extraEnv);
    }
    // The bootstrap step makes the CLI exist (and skips pip when it already
    // does); the CLI then owns the runtime. A source checkout or a private
    // wheelhouse only needs PIP_FIND_LINKS in the environment.
    const bootstrapPath = this._writeInstallerScript(
      bootstrapPythonSource(version),
      "bootstrap.py"
    );
    const shellCommand = installerShellCommand(
      python,
      action,
      version,
      bootstrapPath,
      process.platform
    );
    const scriptPath = this._writeInstallerScript(
      process.platform === "win32"
        ? windowsInstallerScript(shellCommand)
        : posixInstallerScript(shellCommand),
      process.platform === "win32" ? "cmd" : "command"
    );
    const run = installerRun(process.platform, {
      comSpec: process.env.ComSpec,
      scriptPath,
    });
    return this._spawnDetachedInstaller(run, logPath, python, extraEnv);
  }

  private _spawnDetachedInstaller(
    run: { command: string; args: string[] },
    logPath: string,
    python: string,
    extraEnv: Record<string, string> = {}
  ): { ok: boolean; python?: string; error?: string; logPath?: string } {
    let log: number | undefined;
    try {
      fs.mkdirSync(path.dirname(logPath), { recursive: true });
      try {
        if (fs.statSync(logPath).size > 1_048_576) {
          fs.renameSync(logPath, `${logPath}.1`);
        }
      } catch {
        // No log yet, or a rename the antivirus held open: appending still works.
      }
      log = fs.openSync(logPath, "a");
      const child = this._spawnFn(run.command, run.args, {
        // Never cwd into the vault: a leftover shell holding the vault would
        // lock the user's notes directory.
        cwd: os.tmpdir(),
        shell: false,
        detached: true,
        stdio: ["ignore", log, log],
        windowsHide: true,
        env: { ...paperforgeEnrichedEnv(), ...extraEnv },
      });
      child.unref?.();
      return { ok: true, python, logPath };
    } catch (err) {
      return { ok: false, error: `Failed to start the installer: ${err}` };
    } finally {
      if (log !== undefined) fs.closeSync(log);
    }
  }

  /** A script file keeps the platform terminal free of nested quoting. */
  private _writeInstallerScript(content: string, extension: string): string {
    const file = path.join(
      os.tmpdir(),
      `paperforge-runtime-${Date.now()}-${Math.random()
        .toString(36)
        .slice(2, 8)}.${extension}`
    );
    fs.writeFileSync(file, content, { encoding: "utf-8", mode: 0o755 });
    return file;
  }
  private _ensureDaemonSession(target: {
    path: string;
    args: string[];
    nativeBin?: string | null;
    pythonWorkerExe?: string | null;
  }): DaemonSession {
    const spawnCmd = target.nativeBin || target.path;
    const spawnArgs = target.nativeBin
      ? ["--stdio", "--idle-timeout", "300"]
      : [
          ...target.args,
          "-m",
          "paperforge",
          "daemon",
          "--stdio",
          "--idle-timeout",
          "300",
        ];
    const key = `${spawnCmd}\0${spawnArgs.join("\0")}\0${target.pythonWorkerExe ?? ""}`;
    if (
      this._daemon &&
      this._daemon.key === key &&
      this._daemon.child.exitCode == null &&
      this._daemon.child.signalCode == null
    ) {
      return this._daemon;
    }
    this.shutdownDaemon();

    const env = paperforgeEnrichedEnv();
    env.PAPERFORGE_PARENT_PID = String(process.pid);
    env.PAPERFORGE_DAEMON_PUSH = "1";
    if (target.pythonWorkerExe) {
      env.PAPERFORGE_PYTHON_EXE = target.pythonWorkerExe;
    }
    const child = this._spawnFn(spawnCmd, spawnArgs, {
      cwd: os.tmpdir(),
      shell: false,
      windowsHide: true,
      env,
      stdio: ["pipe", "pipe", "pipe"],
    });
    executeChildRegistry.set(child, null);

    const session: DaemonSession = {
      key,
      child,
      nextId: 1,
      nextStreamSeq: 1,
      buffer: "",
      settledAny: false,
      pending: new Map(),
      streams: new Map(),
    };
    this._daemon = session;

    if (typeof child.stdout?.setEncoding === "function") {
      child.stdout.setEncoding("utf-8");
    }
    child.stdout?.on("data", (chunk: string | Buffer) => {
      session.buffer += chunk.toString();
      const lines = session.buffer.split("\n");
      session.buffer = lines.pop() ?? "";
      for (const rawLine of lines) {
        const line = rawLine.trim();
        if (!line) continue;
        let msg: {
          id?: unknown;
          event?: unknown;
          seq?: unknown;
          ts?: unknown;
          vault?: unknown;
          data?: unknown;
          exit_code?: unknown;
          stdout?: unknown;
          stderr?: unknown;
          stream_id?: unknown;
          job_id?: unknown;
          trace_id?: unknown;
          line?: unknown;
          cancelled?: unknown;
        };
        try {
          msg = JSON.parse(line);
        } catch {
          continue;
        }
        if (
          msg.event === "stream.chunk" &&
          typeof msg.stream_id === "string" &&
          msg.id === undefined
        ) {
          const st = session.streams.get(msg.stream_id);
          if (st) {
            const rawChunk =
              typeof msg.line === "string" ? `${msg.line}\n` : "";
            for (const ev of st.parser.feed(rawChunk)) {
              st.events.push(ev);
              st.onEvent(ev);
            }
          }
          continue;
        }
        if (
          msg.event === "stream.end" &&
          typeof msg.stream_id === "string" &&
          msg.id === undefined
        ) {
          const st = session.streams.get(msg.stream_id);
          if (st) {
            session.streams.delete(msg.stream_id);
            st.parser.finishEOF();
            const exitCode =
              typeof msg.exit_code === "number" ? msg.exit_code : null;
            const cancelledFromDaemon = Boolean(msg.cancelled);
            const stderr = typeof msg.stderr === "string" ? msg.stderr : "";
            const death =
              st.parser.protocolFailure === "EOF without terminal event" &&
              typeof exitCode === "number"
                ? `exit ${exitCode}`
                : "";
            const terminal = st.events.find((e) =>
              TERMINAL_EVENTS.has(e.event)
            );
            st.resolve({
              ok:
                !st.parser.protocolFailure &&
                exitCode === 0 &&
                terminal?.event === "result" &&
                terminal.result?.ok !== false,
              exitCode,
              cancelled:
                cancelledFromDaemon ||
                exitCode === 130 ||
                terminal?.event === "cancelled" ||
                (st.stopRequested && !st.parser.terminalSeen),
              events: st.events,
              protocolFailure: st.parser.protocolFailure
                ? death
                  ? `${st.parser.protocolFailure} (${death})`
                  : st.parser.protocolFailure
                : undefined,
              stderr,
              jobId: typeof msg.job_id === "string" ? msg.job_id : undefined,
              traceId:
                typeof msg.trace_id === "string" ? msg.trace_id : undefined,
            });
          }
          continue;
        }
        if (typeof msg.event === "string" && msg.id === undefined) {
          const pushEv: DaemonPushEvent = {
            event: msg.event,
            seq: typeof msg.seq === "number" ? msg.seq : undefined,
            ts: typeof msg.ts === "number" ? msg.ts : undefined,
            vault: typeof msg.vault === "string" ? msg.vault : null,
            data:
              msg.data && typeof msg.data === "object"
                ? (msg.data as Record<string, unknown>)
                : {},
          };
          for (const listener of this._daemonListeners) {
            try {
              listener(pushEv);
            } catch {
              // Isolate UI listener errors from transport event loop
            }
          }
          continue;
        }
        const rpcId = typeof msg.id === "number" ? msg.id : Number(msg.id);
        const rpc = session.pending.get(rpcId);
        if (!rpc) continue;
        session.pending.delete(rpcId);
        if (rpc.timer) clearTimeout(rpc.timer);
        session.settledAny = true;

        const code = typeof msg.exit_code === "number" ? msg.exit_code : 0;
        const stdout = typeof msg.stdout === "string" ? msg.stdout : "";
        const stderr = typeof msg.stderr === "string" ? msg.stderr : "";
        if (code === 0) {
          rpc.resolve(stdout);
        } else {
          const err = new Error(
            `PaperForge command failed (exit code ${code}): ${stderr || "daemon rpc"}`
          ) as Error & { exitCode: number; stderr: string; stdout: string };
          err.exitCode = code;
          err.stderr = stderr;
          err.stdout = stdout;
          rpc.reject(err);
        }
      }
    });

    if (typeof child.stderr?.setEncoding === "function") {
      child.stderr.setEncoding("utf-8");
    }
    // Drain daemon stderr so OS pipe never fills on diagnostics.
    child.stderr?.on("data", () => {});

    const failPending = (reason: string): void => {
      executeChildRegistry.delete(child);
      if (this._daemon === session) {
        this._daemon = null;
      }
      for (const [id, rpc] of session.pending.entries()) {
        session.pending.delete(id);
        if (rpc.timer) clearTimeout(rpc.timer);
        rpc.reject(
          Object.assign(new Error(reason), {
            daemonUnavailable: !session.settledAny,
          })
        );
      }
      for (const [sid, st] of session.streams.entries()) {
        session.streams.delete(sid);
        st.parser.finishEOF();
        st.resolve({
          ok: false,
          exitCode: null,
          cancelled: st.stopRequested && !st.parser.terminalSeen,
          events: st.events,
          protocolFailure: st.parser.protocolFailure ?? reason,
          stderr: reason,
        });
      }
    };

    child.on("close", (code: number | null) => {
      failPending(`PaperForge daemon exited unexpectedly (code=${code})`);
    });
    child.on("error", (err: Error) => {
      failPending(`PaperForge daemon error: ${err.message}`);
    });

    return session;
  }

  onDaemonEvent(listener: (event: DaemonPushEvent) => void): () => void {
    this._daemonListeners.add(listener);
    return () => {
      this._daemonListeners.delete(listener);
    };
  }

  private async _resolveDaemonTarget(): Promise<{
    path: string;
    args: string[];
    nativeBin?: string | null;
    pythonWorkerExe?: string | null;
  }> {
    const nativeBin = this._resolveNativeDaemon();
    const ptrCmd = resolveRuntimeCommand(readRuntimePointer());
    if (nativeBin) {
      return {
        path: nativeBin,
        args: [],
        nativeBin,
        pythonWorkerExe: ptrCmd?.command ?? null,
      };
    }
    const py = await this.resolvePython();
    return {
      path: py.path,
      args: py.args,
      nativeBin: null,
      pythonWorkerExe: null,
    };
  }

  hasNativeDaemonRpc(): boolean {
    return Boolean(this._resolveNativeDaemon());
  }

  async rpc(
    payload: Record<string, unknown>,
    timeoutMs = 30000
  ): Promise<string> {
    if (this._swapInFlight) {
      await this._swapInFlight.catch(() => undefined);
    }
    try {
      return await this._rpcOnce(payload, timeoutMs);
    } catch (err: unknown) {
      if (
        err instanceof Error &&
        err.message === "PaperForge daemon shut down" &&
        this._swapInFlight
      ) {
        await this._swapInFlight.catch(() => undefined);
        return await this._rpcOnce(payload, timeoutMs);
      }
      throw err;
    }
  }

  private async _rpcOnce(
    payload: Record<string, unknown>,
    timeoutMs = 30000
  ): Promise<string> {
    const target = await this._resolveDaemonTarget();
    const session = this._ensureDaemonSession(target);
    const id = session.nextId++;
    const line =
      JSON.stringify({
        vault: this._vaultPath,
        ...payload,
        id,
      }) + "\n";

    return new Promise<string>((resolve, reject) => {
      let timer: ReturnType<typeof setTimeout> | null = null;
      if (timeoutMs > 0) {
        timer = setTimeout(() => {
          session.pending.delete(id);
          const timeoutErr = new Error(
            `PaperForge daemon RPC timed out after ${timeoutMs}ms`
          ) as Error & { timedOut: boolean };
          timeoutErr.timedOut = true;
          this.shutdownDaemon();
          reject(timeoutErr);
        }, timeoutMs);
      }

      session.pending.set(id, { resolve, reject, timer });
      try {
        session.child.stdin?.write(line);
      } catch (err) {
        session.pending.delete(id);
        if (timer) clearTimeout(timer);
        reject(err instanceof Error ? err : new Error(String(err)));
      }
    });
  }

  shutdownDaemon(force = false): void {
    const active = this._daemon;
    this._daemon = null;
    if (!active) return;
    executeChildRegistry.delete(active.child);
    for (const [id, rpc] of active.pending.entries()) {
      active.pending.delete(id);
      if (rpc.timer) clearTimeout(rpc.timer);
      rpc.reject(new Error("PaperForge daemon shut down"));
    }
    for (const [sid, st] of active.streams.entries()) {
      active.streams.delete(sid);
      st.parser.finishEOF();
      st.resolve({
        ok: false,
        exitCode: null,
        cancelled: st.stopRequested && !st.parser.terminalSeen,
        events: st.events,
        protocolFailure:
          st.parser.protocolFailure ?? "PaperForge daemon shut down",
        stderr: "PaperForge daemon shut down",
      });
    }
    if (active.child.exitCode == null && active.child.signalCode == null) {
      const canGraceful =
        !force &&
        this._spawnFn === spawn &&
        Boolean(active.child.stdin && !active.child.stdin.destroyed);
      if (canGraceful) {
        try {
          active.child.stdin?.write('{"id":0,"op":"shutdown"}\n');
          active.child.stdin?.end();
        } catch {
          hardKill(active.child);
          return;
        }
        const killer = setTimeout(() => {
          if (
            active.child.exitCode == null &&
            active.child.signalCode == null
          ) {
            hardKill(active.child);
          }
        }, 600);
        killer.unref?.();
      } else {
        hardKill(active.child);
      }
    }
  }

  /** Gracefully stop the warm daemon and await process exit before hot-update. */
  async shutdownDaemonAsync(force = false): Promise<void> {
    const active = this._daemon;
    if (!active) return;
    const child = active.child;
    if (child.exitCode != null || child.signalCode != null) {
      this.shutdownDaemon(force);
      return;
    }
    const hadOuterSwap = Boolean(this._swapInFlight);
    const swapWork = new Promise<void>((resolve) => {
      let settled = false;
      const done = () => {
        if (settled) return;
        settled = true;
        clearTimeout(fallbackTimer);
        resolve();
      };
      child.once("close", done);
      child.once("exit", done);
      const fallbackTimer = setTimeout(() => {
        if (child.exitCode == null && child.signalCode == null) {
          hardKill(child);
        }
        done();
      }, 1500);
      fallbackTimer.unref?.();
      this.shutdownDaemon(force);
    }).finally(() => {
      if (this._swapInFlight === swapWork) {
        this._swapInFlight = null;
      }
    });
    if (!hadOuterSwap) {
      this._swapInFlight = swapWork;
    }
    await swapWork;
  }

  /**
   * Hold the `_swapInFlight` barrier across both daemon shutdown AND the
   * replacement operation (e.g. `fs.renameSync` on Windows) so concurrent RPCs
   * cannot respawn and re-lock the binary mid-repair.
   */
  async runWithDaemonSwap<T>(fn: () => Promise<T> | T): Promise<T> {
    const prev = this._swapInFlight;
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    this._swapInFlight = gate;
    try {
      if (prev) {
        await prev.catch(() => undefined);
      }
      await this.shutdownDaemonAsync();
      return await fn();
    } finally {
      if (this._swapInFlight === gate) {
        this._swapInFlight = null;
      }
      release();
    }
  }

  private async _executeDaemon(
    target: {
      path: string;
      args: string[];
      nativeBin?: string | null;
      pythonWorkerExe?: string | null;
    },
    argv: string[],
    options?: ExecuteOptions
  ): Promise<string> {
    const session = this._ensureDaemonSession(target);
    const id = session.nextId++;
    const timeout = options?.timeoutMs ?? 120000;
    const payload =
      JSON.stringify({
        id,
        vault: this._vaultPath,
        argv,
        stdin: options?.stdin ?? null,
      }) + "\n";

    return new Promise<string>((resolve, reject) => {
      let timer: ReturnType<typeof setTimeout> | null = null;
      if (timeout > 0) {
        timer = setTimeout(() => {
          session.pending.delete(id);
          const timeoutErr = new Error(
            `PaperForge command timed out after ${timeout}ms: ${argv.join(" ")}`
          ) as Error & { timedOut: boolean };
          timeoutErr.timedOut = true;
          // Kill the warm daemon so the wedged in-process request cannot leak state.
          this.shutdownDaemon();
          reject(timeoutErr);
        }, timeout);
      }

      session.pending.set(id, { resolve, reject, timer });
      try {
        session.child.stdin?.write(payload);
      } catch (err) {
        session.pending.delete(id);
        if (timer) clearTimeout(timer);
        reject(err instanceof Error ? err : new Error(String(err)));
      }
    });
  }

  async execute(argv: string[], options?: ExecuteOptions): Promise<string> {
    const canUseDaemon =
      this._useDaemon &&
      this._daemonSupported &&
      !options?.pythonExe &&
      !options?.env &&
      argv[0] !== "runtime" &&
      argv[0] !== "daemon";

    if (canUseDaemon) {
      if (this._swapInFlight) {
        await this._swapInFlight.catch(() => undefined);
      }
      const nativeBin = this._resolveNativeDaemon();
      if (nativeBin) {
        const ptrCmd = resolveRuntimeCommand(readRuntimePointer());
        const runNative = () => {
          const freshBin = this._resolveNativeDaemon() || nativeBin;
          return this._executeDaemon(
            {
              path: freshBin,
              args: [],
              nativeBin: freshBin,
              pythonWorkerExe: ptrCmd?.command ?? null,
            },
            argv,
            options
          );
        };
        try {
          return await runNative();
        } catch (err: unknown) {
          if (
            err instanceof Error &&
            err.message === "PaperForge daemon shut down" &&
            this._swapInFlight
          ) {
            await this._swapInFlight.catch(() => undefined);
            return await runNative();
          }
          const unavailable =
            err !== null &&
            typeof err === "object" &&
            "daemonUnavailable" in err &&
            Boolean((err as { daemonUnavailable?: unknown }).daemonUnavailable);
          if (!unavailable) {
            throw err;
          }
          this._daemonSupported = false;
        }
      }
    }

    const py = options?.pythonExe
      ? { path: options.pythonExe, args: [] as string[] }
      : await this.resolvePython();

    if (canUseDaemon) {
      try {
        return await this._executeDaemon(py, argv, options);
      } catch (err: unknown) {
        const unavailable =
          err !== null &&
          typeof err === "object" &&
          "daemonUnavailable" in err &&
          Boolean((err as { daemonUnavailable?: unknown }).daemonUnavailable);
        if (!unavailable) {
          throw err;
        }
        // Runtime binary might be older without `daemon` subcommand: fall back once cleanly.
        this._daemonSupported = false;
      }
    }
    return this._executeSpawn(py, argv, options);
  }

  private _executeSpawn(
    py: { path: string; args: string[] },
    argv: string[],
    options?: ExecuteOptions
  ): Promise<string> {
    const env = options?.env ?? paperforgeEnrichedEnv();
    const timeout = options?.timeoutMs ?? 120000;

    const fullArgs = [
      ...py.args,
      "-m",
      "paperforge",
      "--vault",
      this._vaultPath,
      ...argv,
    ];

    return new Promise<string>((resolve, reject) => {
      let child: ChildProcess;
      try {
        child = this._spawnFn(py.path, fullArgs, {
          cwd: this._vaultPath,
          shell: false,
          windowsHide: true,
          env,
          stdio: ["pipe", "pipe", "pipe"],
        });
      } catch (err) {
        return reject(new Error(`Failed to spawn Python process: ${err}`));
      }

      executeChildRegistry.set(child, null);

      const stdoutChunks: string[] = [];
      const stderrChunks: string[] = [];
      if (typeof child.stdout?.setEncoding === "function") {
        child.stdout.setEncoding("utf-8");
      }
      child.stdout?.on("data", (chunk: string | Buffer) => {
        stdoutChunks.push(chunk.toString());
      });

      if (typeof child.stderr?.setEncoding === "function") {
        child.stderr.setEncoding("utf-8");
      }
      child.stderr?.on("data", (chunk: string | Buffer) => {
        stderrChunks.push(chunk.toString());
      });

      let timer: ReturnType<typeof setTimeout> | null = null;
      if (timeout > 0) {
        timer = setTimeout(() => {
          try {
            hardKill(child);
          } catch {
            // ignore
          }
          const stderrSnap = stderrChunks.join("").trim();
          const stderrTail = stderrSnap.slice(-2000);
          const timeoutErr = new Error(
            `PaperForge command timed out after ${timeout}ms: ${argv.join(" ")}` +
              (stderrTail ? `\n\nstderr:\n${stderrTail}` : "")
          ) as Error & { stderr: string; timedOut: boolean };
          timeoutErr.stderr = stderrSnap;
          timeoutErr.timedOut = true;
          reject(timeoutErr);
        }, timeout);
      }

      if (options?.stdin) {
        try {
          child.stdin?.write(options.stdin);
          child.stdin?.end();
        } catch (err) {
          // ignore stdin write errors
        }
      } else {
        child.stdin?.end();
      }

      child.on("close", (code: number | null) => {
        clearTimeout(timer!);
        executeChildRegistry.delete(child);
        if (code === 0) {
          resolve(stdoutChunks.join(""));
        } else {
          const stderr = stderrChunks.join("").trim();
          const err: any = new Error(
            `PaperForge command failed (exit code ${code}): ${stderr || argv.join(" ")}`
          );
          err.exitCode = code ?? 1;
          err.stderr = stderr;
          err.stdout = stdoutChunks.join("");
          reject(err);
        }
      });

      child.on("error", (err: Error) => {
        clearTimeout(timer!);
        executeChildRegistry.delete(child);
        reject(err);
      });
    });
  }

  private async _streamViaDaemon(
    target: {
      path: string;
      args: string[];
      nativeBin?: string | null;
      pythonWorkerExe?: string | null;
    },
    argv: string[],
    options: StreamOptions | undefined,
    queue: AsyncEventQueue<NdjsonEvent>,
    registerCancel: (cancelFn: () => void) => void
  ): Promise<LongTaskOutcome> {
    const session = this._ensureDaemonSession(target);
    const streamId = `str_${process.pid}_${session.nextStreamSeq++}`;
    const parser = new NdjsonStreamParser();
    const events: NdjsonEvent[] = [];

    let resolveOutcome!: (outcome: LongTaskOutcome) => void;
    const outcomePromise = new Promise<LongTaskOutcome>((resolve) => {
      resolveOutcome = resolve;
    });

    const entry: ActiveDaemonStream = {
      streamId,
      parser,
      events,
      stopRequested: false,
      onEvent: (ev) => {
        queue.push(ev);
        options?.onEvent?.(ev);
      },
      resolve: resolveOutcome,
    };
    session.streams.set(streamId, entry);

    const rpcId = session.nextId++;
    const reqLine =
      JSON.stringify({
        id: rpcId,
        op: "job.stream",
        vault: this._vaultPath,
        argv,
        stream_id: streamId,
        close_stdin: argv[0] === "setup",
      }) + "\n";

    let rawAck: string;
    try {
      rawAck = await new Promise<string>((resolve, reject) => {
        const timer = setTimeout(() => {
          session.pending.delete(rpcId);
          reject(new Error("PaperForge job.stream RPC timed out"));
        }, 15000);
        session.pending.set(rpcId, { resolve, reject, timer });
        try {
          session.child.stdin?.write(reqLine);
          registerCancel(() => {
            entry.stopRequested = true;
            if (
              session.child.exitCode == null &&
              session.child.signalCode == null &&
              session.child.stdin &&
              !session.child.stdin.destroyed
            ) {
              const cancelId = session.nextId++;
              try {
                session.child.stdin.write(
                  JSON.stringify({
                    id: cancelId,
                    op: "job.cancel",
                    vault: this._vaultPath,
                    stream_id: streamId,
                    grace_ms: options?.graceMs ?? 4000,
                    wait: false,
                  }) + "\n"
                );
              } catch {
                // Daemon already closed; failPending settles the stream.
              }
            }
          });
        } catch (err) {
          session.pending.delete(rpcId);
          clearTimeout(timer);
          reject(err instanceof Error ? err : new Error(String(err)));
        }
      });
    } catch (err) {
      session.streams.delete(streamId);
      throw err;
    }

    let ack: {
      accepted?: boolean;
      reason?: string;
      error?: string;
      job_id?: string;
      trace_id?: string;
    };
    try {
      ack = JSON.parse(rawAck);
    } catch {
      session.streams.delete(streamId);
      return {
        ok: false,
        exitCode: -1,
        cancelled: false,
        events,
        protocolFailure: `Malformed job.stream ack: ${rawAck.slice(0, 120)}`,
      };
    }

    if (!ack.accepted) {
      session.streams.delete(streamId);
      return {
        ok: false,
        exitCode: -1,
        cancelled: false,
        events,
        protocolFailure: ack.error || ack.reason || "job.stream rejected",
        stderr: ack.error || ack.reason || "",
        traceId: ack.trace_id,
      };
    }

    return outcomePromise;
  }

  stream(argv: string[], options?: StreamOptions): StreamHandle {
    const queue = new AsyncEventQueue<NdjsonEvent>();
    let stopped = false;
    let longTaskHandle: {
      stop: () => void;
      promise: Promise<LongTaskOutcome>;
    } | null = null;
    let daemonStreamCancel: (() => void) | null = null;

    const outcomePromise = (async (): Promise<LongTaskOutcome> => {
      if (this._swapInFlight) {
        await this._swapInFlight.catch(() => undefined);
      }
      const canUseNativeDaemon =
        this._useDaemon &&
        this._daemonSupported &&
        !options?.pythonExe &&
        !options?.env &&
        Boolean(this._resolveNativeDaemon());

      if (canUseNativeDaemon) {
        const nativeBin = this._resolveNativeDaemon()!;
        let workerExe: string | null = null;
        const ptrCmd = resolveRuntimeCommand(readRuntimePointer());
        if (ptrCmd && ptrCmd.args.length === 0) {
          workerExe = ptrCmd.command;
        } else {
          try {
            const py = await this.resolvePython();
            if (py.args.length === 0) {
              workerExe = py.path;
            }
          } catch {
            workerExe = null;
          }
        }

        if (stopped) {
          queue.finish();
          return { ok: false, exitCode: null, cancelled: true, events: [] };
        }

        if (workerExe) {
          try {
            const outcome = await this._streamViaDaemon(
              {
                path: nativeBin,
                args: [],
                nativeBin,
                pythonWorkerExe: workerExe,
              },
              argv,
              options,
              queue,
              (cancelFn) => {
                daemonStreamCancel = cancelFn;
                if (stopped) {
                  cancelFn();
                }
              }
            );
            queue.finish();
            return outcome;
          } catch (err: unknown) {
            const unavailable =
              err !== null &&
              typeof err === "object" &&
              "daemonUnavailable" in err &&
              Boolean(
                (err as { daemonUnavailable?: unknown }).daemonUnavailable
              );
            if (!unavailable) {
              const e = err instanceof Error ? err : new Error(String(err));
              queue.fail(e);
              throw e;
            }
            this._daemonSupported = false;
          }
        }
      }

      let py: { path: string; args: string[] };
      try {
        py = options?.pythonExe
          ? { path: options.pythonExe, args: [] }
          : await this.resolvePython();
      } catch (err: any) {
        const failure = err?.message || String(err);
        queue.fail(err);
        return {
          ok: false,
          exitCode: -1,
          cancelled: false,
          events: [],
          protocolFailure: failure,
        };
      }

      // Stop arrived while the runtime was still resolving: never spawn.
      if (stopped) {
        queue.finish();
        return { ok: false, exitCode: null, cancelled: true, events: [] };
      }

      longTaskHandle = runLongTask(py.path, py.args, this._vaultPath, argv, {
        graceMs: options?.graceMs,
        env: options?.env,
        closeStdin: argv[0] === "setup",
        spawnFn: this._spawnFn,
        onEvent: (ev) => {
          queue.push(ev);
          options?.onEvent?.(ev);
        },
      });

      if (stopped) {
        longTaskHandle.stop();
      }

      try {
        const outcome = await longTaskHandle.promise;
        queue.finish();
        return outcome;
      } catch (err) {
        queue.fail(err instanceof Error ? err : new Error(String(err)));
        throw err;
      }
    })();

    return {
      events: queue,
      stop: () => {
        stopped = true;
        if (daemonStreamCancel) {
          daemonStreamCancel();
        }
        if (longTaskHandle) {
          longTaskHandle.stop();
        }
      },
      outcome: outcomePromise,
    };
  }
}

export const executeChildren = executeChildRegistry;
export const children = executeChildRegistry;
export const childRegistry = executeChildRegistry;
export const _executeChildren = executeChildRegistry;
export const _childRegistry = executeChildRegistry;
export function reapExecuteChildren(): void {
  reapExecuteChildrenImpl();
}
export function reapAll(): void {
  reapExecuteChildrenImpl();
}
export function reapAllExecuteChildren(): void {
  reapExecuteChildrenImpl();
}
export function killExecuteChildren(): void {
  reapExecuteChildrenImpl();
}
export function killAllExecuteChildren(): void {
  reapExecuteChildrenImpl();
}
export function clearExecuteChildren(): void {
  reapExecuteChildrenImpl();
}
