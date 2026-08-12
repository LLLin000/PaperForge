/**
 * OcrProcessController — single owner of OCR child-process lifecycles
 * (issue #126 PR B).
 *
 * One instance is owned by PaperForgePlugin; Settings and the OCR Workspace
 * share it. Duplicate starts are impossible by construction (singleton
 * busy-guard). Real stop via the OCR cooperative-stop stdin contract
 * (`PAPERFORGE_STOP`), mode-based credential policy (run/redo require the
 * Paddle credential and fail closed; rebuild never does), and full
 * START/PROGRESS/RESULT/DONE progress parsing.
 *
 * The embed-build control sidecar is a separate mechanism and stays outside
 * this controller.
 */
import { spawn, type ChildProcess } from "child_process";
import { NdjsonStreamParser, type NdjsonEvent } from "./long-task-client";

export type OcrMode = "run" | "rebuild" | "redo";

export interface OcrSkippedKey {
  key: string;
  reason: string;
}

export interface OcrProcessOutcome {
  ok: boolean;
  exitCode: number | null;
  stopped: boolean;
  successKeys: string[];
  failedKeys: string[];
  skippedKeys: OcrSkippedKey[];
  /** #137 protocol failure (non-JSON line, bad event, EOF w/o terminal). */
  protocolFailure?: string;
}

export interface OcrProcessCallbacks {
  onProgress?: (current: number, total: number, key: string) => void;
  onResult?: (key: string, status: string) => void;
  onNotice?: (message: string) => void;
}

export interface OcrProcessStartOptions {
  keys?: string[];
  all?: boolean;
  callbacks?: OcrProcessCallbacks;
}

export interface OcrProcessControllerOptions {
  vaultPath: string;
  resolveCommand: () => { path: string; args: string[] } | null;
  resolveEnv: () => Promise<Record<string, string | undefined>>;
  /** True when the mode requires the Paddle credential. */
  needsCredential: (mode: OcrMode) => boolean;
  /** Test seam: spawn implementation (defaults to child_process.spawn). */
  spawnFn?: typeof spawn;
}

const STOP_TOKEN = "PAPERFORGE_STOP\n";
const MAX_NOTICE_LENGTH = 500;

function modeToArgs(mode: OcrMode, opts: OcrProcessStartOptions): string[] {
  if (mode === "run") {
    return ["ocr", "run", ...(opts.keys ?? [])];
  }
  if (mode === "redo") {
    return ["ocr", "redo", ...(opts.keys ?? [])];
  }
  const keys = opts.keys ?? [];
  return keys.length > 0
    ? ["ocr", "rebuild", ...keys]
    : ["ocr", "rebuild", "--all"];
}

export class OcrProcessController {
  private _child: ChildProcess | null = null;
  private _stopRequested = false;
  private _parser = new NdjsonStreamParser();
  private _stderr = "";

  constructor(private readonly _opts: OcrProcessControllerOptions) {}

  get isRunning(): boolean {
    return this._child !== null;
  }

  /** Request a cooperative stop; idempotent. */
  stop(): void {
    if (!this._child) return;
    this._stopRequested = true;
    try {
      this._child.stdin?.write(STOP_TOKEN);
    } catch {
      // stdin may be closed already — the exit path still settles.
    }
  }

  /**
   * Start one OCR operation. Resolves exactly once with the aggregated
   * outcome (success/failed/skipped keys from RESULT events, exit code,
   * stop flag). Rejects when the runtime is unavailable, a credential is
   * required but missing, or another operation is already running.
   */
  start(
    mode: OcrMode,
    opts: OcrProcessStartOptions = {}
  ): Promise<OcrProcessOutcome> {
    if (this.isRunning) {
      return Promise.reject(new Error("OCR is already running"));
    }
    const command = this._opts.resolveCommand();
    if (!command?.path) {
      return Promise.reject(new Error("No Python runtime available"));
    }
    if (this._opts.needsCredential(mode)) {
      return this._opts
        .resolveEnv()
        .then((env) => this._spawn(mode, opts, command, env))
        .catch((err: unknown) =>
          Promise.reject(
            new Error(
              `OCR credential unavailable: ${err instanceof Error ? err.message : String(err)}`
            )
          )
        );
    }
    return this._spawn(mode, opts, command, {});
  }

  private _spawn(
    mode: OcrMode,
    opts: OcrProcessStartOptions,
    command: { path: string; args: string[] },
    env: Record<string, string | undefined>
  ): Promise<OcrProcessOutcome> {
    const callbacks = opts.callbacks ?? {};
    this._stopRequested = false;
    this._parser = new NdjsonStreamParser();
    this._stderr = "";

    const spawnFn = this._opts.spawnFn ?? spawn;
    const child = spawnFn(
      command.path,
      [...command.args, "-m", "paperforge", ...modeToArgs(mode, opts)],
      {
        cwd: this._opts.vaultPath,
        shell: false,
        windowsHide: true,
        env: { ...process.env, ...env },
        stdio: ["pipe", "pipe", "pipe"],
      }
    );
    this._child = child;

    const successKeys: string[] = [];
    const failedKeys: string[] = [];
    const skippedKeys: OcrSkippedKey[] = [];

    const settleOnce = (() => {
      let settled = false;
      return (
        exitCode: number | null,
        stopped: boolean,
        ok: boolean,
        protocolFailure?: string
      ): void => {
        if (settled) return;
        settled = true;
        this._child = null;
        if (this._stderr.trim()) {
          callbacks.onNotice?.(this._stderr.trim().slice(-MAX_NOTICE_LENGTH));
        }
        resolver({
          ok,
          exitCode,
          stopped,
          successKeys,
          failedKeys,
          skippedKeys,
          protocolFailure,
        });
      };
    })();

    let resolver!: (outcome: OcrProcessOutcome) => void;
    const promise = new Promise<OcrProcessOutcome>((resolve) => {
      resolver = resolve;
    });

    child.stdout?.setEncoding("utf-8");
    child.stdout?.on("data", (chunk: string) => {
      const events = this._parser.feed(chunk);
      for (const event of events) {
        this._handleEvent(
          event,
          callbacks,
          successKeys,
          failedKeys,
          skippedKeys
        );
      }
    });
    child.stderr?.setEncoding("utf-8");
    child.stderr?.on("data", (chunk: string) => {
      this._stderr = (this._stderr + chunk).slice(-MAX_NOTICE_LENGTH);
    });
    child.on("error", (err: Error) => {
      callbacks.onNotice?.(`OCR process error: ${err.message}`);
      settleOnce(null, this._stopRequested, false);
    });
    child.on("close", (code: number | null) => {
      this._parser.finishEOF();
      const protocolFailure = this._parser.protocolFailure;
      if (protocolFailure) {
        callbacks.onNotice?.(`OCR stream protocol failure: ${protocolFailure}`);
      }
      const stopped = this._stopRequested || code === 130;
      const failed =
        failedKeys.length > 0 || skippedKeys.length > 0 || !!protocolFailure;
      const ok = !stopped && !failed && (code === 0 || code === null);
      settleOnce(code, stopped, ok, protocolFailure);
    });

    return promise;
  }

  private _handleEvent(
    event: NdjsonEvent,
    callbacks: OcrProcessCallbacks,
    successKeys: string[],
    failedKeys: string[],
    skippedKeys: OcrSkippedKey[]
  ): void {
    switch (event.event) {
      case "progress":
        callbacks.onProgress?.(
          event.current ?? 0,
          event.total ?? 1,
          event.item_id ?? ""
        );
        break;
      case "item_result":
        if (event.status === "ok") {
          successKeys.push(event.item_id ?? "");
        } else if (event.status === "failed") {
          failedKeys.push(event.item_id ?? "");
        } else if (event.status === "skipped") {
          skippedKeys.push({
            key: event.item_id ?? "",
            reason: "backend_skip",
          });
        }
        callbacks.onResult?.(event.item_id ?? "", event.status ?? "");
        break;
      default:
        break;
    }
  }
}
