/**
 * MockTransport — In-memory test transport for PaperForgeClient.
 *
 * Simulates execute responses, streaming events, cancellation triggers,
 * and failure conditions without launching child processes.
 */

import {
  type Transport,
  type ExecuteOptions,
  type StreamOptions,
  type StreamHandle,
  type NdjsonEvent,
  type LongTaskOutcome,
  AsyncEventQueue,
} from "../../src/client/transport";

export interface RecordedCall {
  kind: "execute" | "stream";
  argv: string[];
  options?: ExecuteOptions | StreamOptions;
  stopped?: boolean;
}

export type ExecuteHandler = (
  argv: string[],
  options?: ExecuteOptions
) => Promise<string> | string;

export interface MockStreamSpec {
  events?: NdjsonEvent[];
  outcome?: Partial<LongTaskOutcome>;
  delayMs?: number;
  failSpawn?: Error;
  failProtocol?: string;
}

export type StreamHandler = (
  argv: string[],
  options?: StreamOptions
) => MockStreamSpec | Promise<MockStreamSpec>;

export class MockTransport implements Transport {
  public readonly calls: RecordedCall[] = [];
  public executeHandler?: ExecuteHandler;
  public streamHandler?: StreamHandler;

  execute(argv: string[], options?: ExecuteOptions): Promise<string> {
    const call: RecordedCall = { kind: "execute", argv: [...argv], options };
    this.calls.push(call);
    if (this.executeHandler) {
      return Promise.resolve(this.executeHandler(argv, options));
    }
    return Promise.resolve("{}");
  }

  stream(argv: string[], options?: StreamOptions): StreamHandle {
    const call: RecordedCall = {
      kind: "stream",
      argv: [...argv],
      options,
      stopped: false,
    };
    this.calls.push(call);

    const queue = new AsyncEventQueue<NdjsonEvent>();
    let stopped = false;
    let stopResolver: (() => void) | undefined;
    const stopPromise = new Promise<void>((resolve) => {
      stopResolver = resolve;
    });

    const outcomePromise = (async (): Promise<LongTaskOutcome> => {
      let spec: MockStreamSpec = {};
      if (this.streamHandler) {
        spec = await this.streamHandler(argv, options);
      }

      if (spec.failSpawn) {
        queue.fail(spec.failSpawn);
        throw spec.failSpawn;
      }

      if (spec.delayMs && spec.delayMs > 0) {
        await new Promise((r) => setTimeout(r, spec.delayMs));
      }

      const emitted: NdjsonEvent[] = [];
      for (const ev of spec.events ?? []) {
        if (stopped) break;
        emitted.push(ev);
        queue.push(ev);
        options?.onEvent?.(ev);
      }

      queue.finish();

      if (stopped) {
        return {
          ok: false,
          exitCode: 130,
          cancelled: true,
          events: emitted,
          protocolFailure: spec.failProtocol,
        };
      }

      return {
        ok: spec.outcome?.ok ?? true,
        exitCode:
          spec.outcome?.exitCode ?? (spec.outcome?.ok === false ? 1 : 0),
        cancelled: spec.outcome?.cancelled ?? false,
        events: emitted,
        protocolFailure: spec.outcome?.protocolFailure ?? spec.failProtocol,
      };
    })();

    return {
      events: queue,
      stop: () => {
        stopped = true;
        call.stopped = true;
        stopResolver?.();
      },
      outcome: outcomePromise,
    };
  }

  findCalls(subcommand: string): RecordedCall[] {
    return this.calls.filter((c) => c.argv.includes(subcommand));
  }

  clearCalls(): void {
    this.calls.length = 0;
  }
}
