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
import * as os from "os";
import * as path from "path";
import {
  type Transport,
  type ExecuteOptions,
  type StreamOptions,
  type StreamHandle,
  AsyncEventQueue,
} from "./transport";
import { stripCredentialEnv } from "../services/secret-storage";
import {
  RuntimeBootstrap,
  resolveRuntimeCommand,
} from "../services/managed-runtime";

export interface NdjsonEvent {
  schema_version: number;
  event: string;
  operation: string;
  total?: number;
  current?: number;
  item_id?: string;
  status?: string;
  result?: Record<string, unknown> | null;
  [key: string]: unknown;
}

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
}

export interface LongTaskOutcome {
  ok: boolean;
  exitCode: number | null;
  cancelled: boolean;
  events: NdjsonEvent[];
  protocolFailure?: string;
}

export interface LongTaskHandle {
  /** Cooperative stop: stdin token, then grace, then hard escalation. */
  stop: () => void;
  promise: Promise<LongTaskOutcome>;
}

function hardKill(child: ChildProcess): void {
  if (!child.pid) return;
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
  const child = spawn(
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

  const parser = new NdjsonStreamParser();
  const events: NdjsonEvent[] = [];
  let hardKilled = false;
  let graceTimer: ReturnType<typeof setTimeout> | null = null;

  child.stdout?.setEncoding("utf-8");
  child.stdout?.on("data", (chunk: string) => {
    for (const ev of parser.feed(chunk)) {
      events.push(ev);
      opts.onEvent(ev);
    }
  });

  const outcome = new Promise<LongTaskOutcome>((resolve) => {
    child.on("close", (code: number | null) => {
      if (graceTimer) clearTimeout(graceTimer);
      parser.finishEOF();
      resolve({
        ok: !parser.protocolFailure && code === 0,
        exitCode: code,
        cancelled: code === 130,
        events,
        protocolFailure: parser.protocolFailure,
      });
    });
    child.on("error", (err: Error) => {
      if (graceTimer) clearTimeout(graceTimer);
      resolve({
        ok: false,
        exitCode: -1,
        cancelled: false,
        events,
        protocolFailure: `spawn error: ${err.message}`,
      });
    });
  });

  return {
    stop: () => {
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
 * process.env secrets into the child. */
export function paperforgeEnrichedEnv(): Record<string, string | undefined> {
  const env: Record<string, string | undefined> = { ...process.env };
  const plat = process.platform;
  const home = os.homedir();
  const extras: string[] = [];
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
  }
  const cur = env.PATH || "";
  env.PATH = [...extras, cur].filter(Boolean).join(path.delimiter);
  return stripCredentialEnv(env) as Record<string, string | undefined>;
}

export interface NodeProcessTransportOptions {
  vaultPath: string;
  /** Custom python executable path (e.g. from user settings). */
  customPythonPath?: string;
  /** Override for python runtime resolution (useful for tests or custom wrappers). */
  resolveRuntime?: () => Promise<{ path: string; args: string[] } | null>;
  /** Child process spawner (default: child_process.spawn). */
  spawnFn?: typeof spawn;
}

export class NodeProcessTransport implements Transport {
  private readonly _vaultPath: string;
  private readonly _customPythonPath?: string;
  private readonly _resolveRuntime?: () => Promise<{
    path: string;
    args: string[];
  } | null>;
  private readonly _spawnFn: typeof spawn;

  constructor(options: NodeProcessTransportOptions) {
    this._vaultPath = options.vaultPath;
    this._customPythonPath = options.customPythonPath?.trim();
    this._resolveRuntime = options.resolveRuntime;
    this._spawnFn = options.spawnFn ?? spawn;
  }

  /**
   * Resolve active python interpreter.
   * Priority: custom resolver > user setting path > managed runtime pointer.
   */
  async resolvePython(): Promise<{ path: string; args: string[] }> {
    if (this._resolveRuntime) {
      const res = await this._resolveRuntime();
      if (res?.path) return res;
      throw new Error(
        "PaperForge Python runtime not ready. Please complete setup or configure python_path."
      );
    }

    if (this._customPythonPath) {
      return { path: this._customPythonPath, args: [] };
    }
    const bootstrap = new RuntimeBootstrap();
    const ptr = bootstrap.readPointer();
    const cmd = resolveRuntimeCommand(ptr);
    if (cmd?.command) {
      return { path: cmd.command, args: [...cmd.args] };
    }

    throw new Error(
      "PaperForge Python runtime not ready. Please complete setup or configure python_path."
    );
  }
  async execute(argv: string[], options?: ExecuteOptions): Promise<string> {
    const py = options?.pythonExe
      ? { path: options.pythonExe, args: [] }
      : await this.resolvePython();
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
            child.kill();
          } catch {
            // ignore
          }
          reject(
            new Error(
              `PaperForge command timed out after ${timeout}ms: ${argv.join(" ")}`
            )
          );
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

      longTaskHandle = runLongTask(py.path, py.args, this._vaultPath, argv, {
        graceMs: options?.graceMs,
        env: options?.env,
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
      } catch (err: any) {
        queue.fail(err);
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
