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
      opts.onEvent(ev);
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

/** Host bootstrap seam: locate git for the child PATH. This is a host
 * environment probe, NOT PaperForge process execution. */
function resolveGitDir(): string | null {
  if (_gitDirResolved) return _gitDir;
  _gitDirResolved = true;
  try {
    let out: string;
    if (process.platform === "win32") {
      const cmdExe = process.env.ComSpec || "C:\\Windows\\System32\\cmd.exe";
      out = execFileSync(cmdExe, ["/c", "where", "git"], {
        timeout: 5000,
        windowsHide: true,
        encoding: "utf-8",
      });
    } else {
      out = execFileSync("which", ["git"], {
        timeout: 5000,
        encoding: "utf-8",
      });
    }
    if (out) {
      const line = out.split("\n")[0].trim();
      if (line) _gitDir = path.dirname(line);
    }
  } catch (_) {}
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
      `${home}/.local/bin`
    );
  } else if (plat === "linux") {
    extras.push("/usr/local/bin", "/usr/bin", `${home}/.local/bin`);
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

interface DaemonSession {
  key: string;
  child: ChildProcess;
  nextId: number;
  buffer: string;
  settledAny: boolean;
  pending: Map<number, PendingDaemonRpc>;
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
  private _daemonSupported = true;
  private _daemon: DaemonSession | null = null;
  private readonly _daemonListeners = new Set<
    (event: DaemonPushEvent) => void
  >();

  constructor(options: NodeProcessTransportOptions) {
    this._vaultPath = options.vaultPath;
    this._spawnFn = options.spawnFn ?? spawn;
    this._execFileSyncFn = options.execFileSyncFn ?? execFileSync;
    this._installerLogPath = options.installerLogPath ?? installerLogPath;
    this._useDaemon = options.useDaemon ?? options.spawnFn === undefined;
  }

  /** Resolve the interpreter from Python's published runtime pointer. */
  async resolvePython(): Promise<{ path: string; args: string[] }> {
    const cmd = resolveRuntimeCommand(readRuntimePointer());
    if (cmd) return { path: cmd.command, args: [...cmd.args] };

    // Expected setup state, not a failure: tag the existing NO_PYTHON
    // machine code (python-bridge taxonomy) so callers can suppress it from
    // the Console and offer setup recovery without parsing this message.
    const err = new Error(
      "PaperForge runtime not ready. Run `paperforge runtime install` outside Obsidian."
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
    options?: { allowUvDownload?: boolean }
  ): { ok: boolean; python?: string; error?: string; logPath?: string } {
    const logPath = this._installerLogPath();
    const python = this.discoverBasePython();
    if (!python) {
      if (!options?.allowUvDownload) {
        return {
          ok: false,
          error:
            "No Python 3.11+ found. Install Python from python.org, then retry.",
        };
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
      return this._spawnDetachedInstaller(run, logPath, uv ?? "uv");
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
      bootstrapPath
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
    return this._spawnDetachedInstaller(run, logPath, python);
  }

  private _spawnDetachedInstaller(
    run: { command: string; args: string[] },
    logPath: string,
    python: string
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
        env: paperforgeEnrichedEnv(),
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
  private _ensureDaemonSession(py: {
    path: string;
    args: string[];
  }): DaemonSession {
    const key = `${py.path}\0${py.args.join("\0")}`;
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
    const child = this._spawnFn(
      py.path,
      [
        ...py.args,
        "-m",
        "paperforge",
        "daemon",
        "--stdio",
        "--idle-timeout",
        "300",
      ],
      {
        cwd: os.tmpdir(),
        shell: false,
        windowsHide: true,
        env,
        stdio: ["pipe", "pipe", "pipe"],
      }
    );
    executeChildRegistry.set(child, null);

    const session: DaemonSession = {
      key,
      child,
      nextId: 1,
      buffer: "",
      settledAny: false,
      pending: new Map(),
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
        };
        try {
          msg = JSON.parse(line);
        } catch {
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

  async rpc(
    payload: Record<string, unknown>,
    timeoutMs = 30000
  ): Promise<string> {
    const py = await this.resolvePython();
    const session = this._ensureDaemonSession(py);
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

  shutdownDaemon(): void {
    const active = this._daemon;
    this._daemon = null;
    if (!active) return;
    executeChildRegistry.delete(active.child);
    for (const [id, rpc] of active.pending.entries()) {
      active.pending.delete(id);
      if (rpc.timer) clearTimeout(rpc.timer);
      rpc.reject(new Error("PaperForge daemon shut down"));
    }
    if (active.child.exitCode == null && active.child.signalCode == null) {
      hardKill(active.child);
    }
  }

  private async _executeDaemon(
    py: { path: string; args: string[] },
    argv: string[],
    options?: ExecuteOptions
  ): Promise<string> {
    const session = this._ensureDaemonSession(py);
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
    const py = options?.pythonExe
      ? { path: options.pythonExe, args: [] as string[] }
      : await this.resolvePython();

    const canUseDaemon =
      this._useDaemon &&
      this._daemonSupported &&
      !options?.pythonExe &&
      !options?.env &&
      argv[0] !== "runtime" &&
      argv[0] !== "daemon";

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

  stream(argv: string[], options?: StreamOptions): StreamHandle {
    const queue = new AsyncEventQueue<NdjsonEvent>();
    let stopped = false;
    let longTaskHandle: {
      stop: () => void;
      promise: Promise<LongTaskOutcome>;
    } | null = null;

    const outcomePromise = (async (): Promise<LongTaskOutcome> => {
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
