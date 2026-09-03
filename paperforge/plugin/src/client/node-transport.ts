/**
 * NodeProcessTransport — Node.js child_process transport for PaperForgeClient.
 *
 * Consolidates existing subprocess and streaming mechanics (LongTaskClient,
 * ActionClient, ManagedRuntime):
 * - Resolves canonical Python interpreter via ManagedRuntime pointer.
 * - Sanitizes subprocess environment via paperforgeEnrichedEnv().
 * - Submits credentials strictly over stdin (never in process arguments or env).
 * - Implements cooperative cancellation via stdin PAPERFORGE_STOP and escalation.
 */

import { spawn, type ChildProcess } from "child_process";
import {
  type Transport,
  type ExecuteOptions,
  type StreamOptions,
  type StreamHandle,
  type NdjsonEvent,
  type LongTaskOutcome,
  AsyncEventQueue,
} from "./transport";
import { runLongTask } from "../services/long-task-client";
import { paperforgeEnrichedEnv } from "../services/python-bridge";
import {
  RuntimeBootstrap,
  resolveRuntimeCommand,
} from "../services/managed-runtime";

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
    const py = await this.resolvePython();
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
        py = await this.resolvePython();
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
