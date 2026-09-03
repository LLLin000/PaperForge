/**
 * Transport — Host-independent execution abstraction for PaperForgeClient.
 *
 * Implements the boundary established in ADR 0003: presentation views depend
 * only on PaperForgeClient; PaperForgeClient depends only on Transport.
 */

import type {
  NdjsonEvent,
  LongTaskOutcome,
} from "../services/long-task-client";

export type { NdjsonEvent, LongTaskOutcome };

export interface ExecuteOptions {
  timeoutMs?: number;
  stdin?: string;
  env?: Record<string, string | undefined>;
}

export interface StreamOptions {
  graceMs?: number;
  env?: Record<string, string | undefined>;
  onEvent?: (event: NdjsonEvent) => void;
}

export interface StreamHandle {
  /** Asynchronous iterable yielding structured #137 NDJSON events. */
  events: AsyncIterable<NdjsonEvent>;
  /** Cooperative cancellation trigger. */
  stop: () => void;
  /** Promise that resolves when the streaming task reaches terminal or exit. */
  outcome: Promise<LongTaskOutcome>;
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
}

/**
 * Lightweight, dependency-free async queue implementing AsyncIterable.
 * Used by stream handles to allow `for await (const ev of handle.events)` loops.
 */
export class AsyncEventQueue<T> implements AsyncIterable<T> {
  private _queue: T[] = [];
  private _resolvers: ((value: IteratorResult<T>) => void)[] = [];
  private _done = false;
  private _error: Error | null = null;

  push(item: T): void {
    if (this._done) return;
    if (this._resolvers.length > 0) {
      const resolve = this._resolvers.shift()!;
      resolve({ value: item, done: false });
    } else {
      this._queue.push(item);
    }
  }

  finish(): void {
    if (this._done) return;
    this._done = true;
    while (this._resolvers.length > 0) {
      const resolve = this._resolvers.shift()!;
      resolve({ value: undefined as unknown as T, done: true });
    }
  }

  fail(err: Error): void {
    if (this._done) return;
    this._error = err;
    this._done = true;
    while (this._resolvers.length > 0) {
      const resolve = this._resolvers.shift()!;
      resolve({ value: undefined as unknown as T, done: true });
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
        return new Promise<IteratorResult<T>>((resolve) => {
          this._resolvers.push(resolve);
        });
      },
    };
  }
}
