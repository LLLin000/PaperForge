/**
 * Transport — Host-independent execution abstraction for PaperForgeClient.
 *
 * Implements the boundary established in ADR 0003: presentation views depend
 * only on PaperForgeClient; PaperForgeClient depends only on Transport.
 */

/** #137 structured-stream NDJSON event (frozen 10-event vocabulary). */
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

/** Terminal outcome of one structured-stream operation. */
export interface LongTaskOutcome {
  ok: boolean;
  exitCode: number | null;
  cancelled: boolean;
  events: NdjsonEvent[];
  protocolFailure?: string;
  /** Bounded tail of the child's stderr. Always drained: an unread stderr
   * pipe deadlocks a chatty child (win32 pipes are small). */
  stderr?: string;
  /** Unified Rust daemon job identifier when executed via `job.stream`. */
  jobId?: string;
  /** End-to-end correlation identifier for daemon jobs, notices, and logs. */
  traceId?: string;
}

/** Last completed (or failed) streamed operation, for failure diagnostics. */
export interface StreamDiagnostics {
  operationId: string;
  argv: string[];
  ok: boolean;
  exitCode: number | null;
  cancelled: boolean;
  protocolFailure?: string;
  stderr: string;
  eventCount: number;
  lastEvent: NdjsonEvent | null;
  finishedAt: number;
}

export interface ExecuteOptions {
  timeoutMs?: number;
  stdin?: string;
  env?: Record<string, string | undefined>;
  /** Explicit interpreter, bypassing the published runtime pointer. */
  pythonExe?: string;
}

export interface StreamOptions {
  graceMs?: number;
  env?: Record<string, string | undefined>;
  /** Explicit interpreter, bypassing the published runtime pointer. */
  pythonExe?: string;
  onEvent?: (event: NdjsonEvent) => void;
}

export interface StreamHandle {
  /** Asynchronous iterable yielding structured #137 NDJSON events. */
  events: AsyncIterable<NdjsonEvent>;
  /** Cooperative cancellation trigger. */
  stop: () => void;
  /** Settles at terminal/exit; startup failures reject with their machine code. */
  outcome: Promise<LongTaskOutcome>;
}

/** Asynchronous push event emitted by the warm ControlDaemon over duplex stdout. */
export interface DaemonPushEvent {
  event: "task.updated" | "notice.push" | "state.changed" | string;
  seq?: number;
  ts?: number;
  vault?: string | null;
  data?: Record<string, unknown>;
}

export interface Transport {
  /**
   * Execute a PaperForge subcommand to completion, returning raw stdout string.
   * Rejects on non-zero exit code, timeout, or spawn failure.
   */
  execute(argv: string[], options?: ExecuteOptions): Promise<string>;

  /**
   * Launch a PaperForge subcommand in streaming mode (#137 NDJSON).
   */
  stream(argv: string[], options?: StreamOptions): StreamHandle;

  /**
   * Optional direct control-plane RPC to the warm ControlDaemon (job.submit,
   * daemon.health, notice.list, etc.).
   */
  rpc?(payload: Record<string, unknown>, timeoutMs?: number): Promise<string>;

  /**
   * Optional subscription to server-pushed ControlDaemon events.
   */
  onDaemonEvent?(listener: (event: DaemonPushEvent) => void): () => void;

  /**
   * Open the external runtime installer in a terminal window. Optional: only
   * hosts that can spawn a visible console (desktop) implement it.
   */
  launchRuntimeInstaller?(
    action: "install" | "update" | "repair",
    version: string,
    options?: {
      allowUvDownload?: boolean;
      proxyUrl?: string;
      preferCnMirror?: boolean;
    }
  ): { ok: boolean; python?: string; error?: string; logPath?: string };
}

/**
 * Lightweight, dependency-free async queue implementing AsyncIterable.
 * Used by stream handles to allow `for await (const ev of handle.events)` loops.
 */
export class AsyncEventQueue<T> implements AsyncIterable<T> {
  private _queue: T[] = [];
  private _resolvers: {
    resolve: (value: IteratorResult<T>) => void;
    reject: (error: Error) => void;
  }[] = [];
  private _done = false;
  private _error: Error | null = null;

  push(item: T): void {
    if (this._done) return;
    if (this._resolvers.length > 0) {
      const pending = this._resolvers.shift()!;
      pending.resolve({ value: item, done: false });
    } else {
      this._queue.push(item);
    }
  }

  finish(): void {
    if (this._done) return;
    this._done = true;
    while (this._resolvers.length > 0) {
      const pending = this._resolvers.shift()!;
      pending.resolve({ value: undefined as unknown as T, done: true });
    }
  }

  fail(err: Error): void {
    if (this._done) return;
    this._error = err;
    this._done = true;
    while (this._resolvers.length > 0) {
      this._resolvers.shift()!.reject(err);
    }
  }

  [Symbol.asyncIterator](): AsyncIterator<T> {
    return {
      next: (): Promise<IteratorResult<T>> => {
        if (this._queue.length > 0) {
          return Promise.resolve({ value: this._queue.shift()!, done: false });
        }
        if (this._done) {
          if (this._error) return Promise.reject(this._error);
          return Promise.resolve({
            value: undefined as unknown as T,
            done: true,
          });
        }
        return new Promise<IteratorResult<T>>((resolve, reject) => {
          this._resolvers.push({ resolve, reject });
        });
      },
    };
  }
}
