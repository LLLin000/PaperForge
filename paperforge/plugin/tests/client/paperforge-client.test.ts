/**
 * PaperForgeClient test suite.
 *
 * Tests the core client against MockTransport covering:
 * - In-memory caching with TTL
 * - In-flight read deduplication
 * - No deduplication on mutations
 * - Generation / epoch invalidation (Anti-Resurrection race guard)
 * - OperationLock execution ownership and deterministic release
 */

import { describe, it, expect, beforeEach } from "vitest";
import { MockTransport } from "./mock-transport";
import { PaperForgeClient } from "../../src/client/paperforge-client";
import type { NdjsonEvent } from "../../src/client/transport";

function mockEnvelope(mod: string, state = "ready"): string {
  return JSON.stringify({
    schema_version: 2,
    module: mod,
    capability_state: state,
    activity_state: "idle",
    user_state: state,
    capability_kind: "operational",
    maintenance_eligible: false,
    user_visible_failure: false,
    user_impact: null,
    activity_label: null,
    activity_progress: null,
    severity: "ok",
    reason: { code: `${mod}.ready`, message: "Ready" },
    action_primary: null,
    details: {},
    ttl_seconds: 60,
    updated_at: new Date().toISOString(),
  });
}

describe("PaperForgeClient", () => {
  let transport: MockTransport;
  let client: PaperForgeClient;
  let simulatedTime: number;

  beforeEach(() => {
    transport = new MockTransport();
    simulatedTime = 1000000;
    client = new PaperForgeClient({
      transport,
      clock: () => simulatedTime,
    });
  });

  describe("Observation & TTL Caching", () => {
    it("fetches and caches probe results within TTL", async () => {
      transport.executeHandler = (argv) => {
        if (argv.includes("ocr")) return mockEnvelope("ocr", "ready");
        return "{}";
      };

      const env1 = await client.probe("ocr");
      expect(env1.module).toBe("ocr");
      expect(transport.calls.length).toBe(1);

      // Subsequent call within TTL (60s = 60000ms)
      simulatedTime += 30000;
      const env2 = await client.probe("ocr");
      expect(env2.module).toBe("ocr");
      expect(transport.calls.length).toBe(1); // Served from cache!

      // After TTL expires
      simulatedTime += 35000; // Total 65s > 60s
      const env3 = await client.probe("ocr");
      expect(env3.module).toBe("ocr");
      expect(transport.calls.length).toBe(2); // Fresh call made!
    });
    it("passes OCR keys as separate CLI arguments", async () => {
      transport.executeHandler = (argv) => {
        expect(argv).toEqual(["ocr", "list", "--json", "--keys", "A", "B"]);
        return "[]";
      };

      await client.queryOcrPapers(["B", "A"]);
    });
  });

  describe("In-Flight Read Deduplication", () => {
    it("deduplicates concurrent reads into a single transport call", async () => {
      let callCount = 0;
      let resolvePromise: (val: string) => void;
      const deferred = new Promise<string>((res) => {
        resolvePromise = res;
      });

      transport.executeHandler = () => {
        callCount++;
        return deferred;
      };

      // Launch two concurrent probe reads
      const promise1 = client.probe("library");
      const promise2 = client.probe("library");

      expect(callCount).toBe(1); // Only 1 transport call dispatched!

      // Resolve the transport call
      resolvePromise!(mockEnvelope("library", "ready"));

      const [res1, res2] = await Promise.all([promise1, promise2]);
      expect(res1.module).toBe("library");
      expect(res2.module).toBe("library");
      expect(callCount).toBe(1);
    });

    it("never deduplicates mutation requests", async () => {
      let runCount = 0;
      transport.executeHandler = (argv) => {
        if (argv.includes("action") && argv.includes("run")) {
          runCount++;
          return JSON.stringify({ ok: true, data: { executed: runCount } });
        }
        return "{}";
      };

      const p1 = client.runAction({
        action_id: "test.mutation",
        scope: { kind: "all" },
      });
      const p2 = client.runAction({
        action_id: "test.mutation",
        scope: { kind: "all" },
      });

      await Promise.all([p1, p2]);
      expect(runCount).toBe(2); // Both mutations executed separately!
    });
  });

  describe("Machine Contract & Dynamic Execution Mode Routing", () => {
    it("routes execution_mode=result to execute and never calls stream", async () => {
      let executeCalls = 0;
      let streamCalls = 0;

      transport.executeHandler = (argv) => {
        if (argv.includes("describe")) {
          return JSON.stringify({
            ok: true,
            command: "action.describe",
            version: "1.5.15",
            data: {
              action_id: "any.result_action",
              execution_mode: "result",
            },
          });
        }
        if (argv.includes("run")) {
          executeCalls++;
          return JSON.stringify({ ok: true, data: { done: true } });
        }
        return "{}";
      };

      transport.streamHandler = () => {
        streamCalls++;
        return { events: [], outcome: { ok: true } };
      };

      const result = await client.runAction({
        action_id: "any.result_action",
        scope: { kind: "all" },
      });

      expect(result.ok).toBe(true);
      expect(executeCalls).toBe(1);
      expect(streamCalls).toBe(0); // Stream must never be called!
    });

    it("routes execution_mode=stream to stream and never executes action run directly", async () => {
      let actionRunExecuteCalls = 0;
      let streamCalls = 0;

      transport.executeHandler = (argv) => {
        if (argv.includes("describe")) {
          return JSON.stringify({
            ok: true,
            command: "action.describe",
            version: "1.5.15",
            data: {
              action_id: "any.stream_action",
              execution_mode: "stream",
            },
          });
        }
        if (argv.includes("run")) {
          actionRunExecuteCalls++;
          return JSON.stringify({ ok: true });
        }
        return "{}";
      };

      transport.streamHandler = (argv) => {
        streamCalls++;
        expect(argv).toEqual([
          "action",
          "run",
          "any.stream_action",
          "--scope",
          "all",
          "--json",
        ]);
        return {
          events: [
            {
              schema_version: 1,
              event: "start",
              operation: "action.any.stream_action",
            },
            {
              schema_version: 1,
              event: "result",
              operation: "action.any.stream_action",
              result: { ok: true, count: 42 },
            },
          ],
          outcome: { ok: true, exitCode: 0 },
        };
      };

      const result = await client.runAction({
        action_id: "any.stream_action",
        scope: { kind: "all" },
      });

      expect(result.ok).toBe(true);
      expect(result.payload).toEqual({ ok: true, count: 42 });
      expect(streamCalls).toBe(1);
      expect(actionRunExecuteCalls).toBe(0); // execute must never be called for running the action!
    });

    it("unwraps real PFResult envelope in describeAction", async () => {
      transport.executeHandler = (argv) => {
        if (argv.includes("describe") && argv.includes("ocr.run")) {
          return JSON.stringify({
            ok: true,
            command: "action.describe",
            version: "1.5.15",
            data: {
              schema_version: 1,
              action_id: "ocr.run",
              execution_mode: "stream",
              availability: "available",
            },
          });
        }
        return "{}";
      };

      const desc = await client.describeAction("ocr.run");
      expect(desc.action_id).toBe("ocr.run");
      expect(desc.execution_mode).toBe("stream");
    });

    it("unwraps real PFResult envelope in listActions", async () => {
      transport.executeHandler = (argv) => {
        if (argv.includes("list")) {
          return JSON.stringify({
            ok: true,
            command: "action.list",
            version: "1.5.15",
            data: {
              actions: [
                { action_id: "ocr.run", execution_mode: "stream" },
                { action_id: "memory.build", execution_mode: "result" },
              ],
            },
          });
        }
        return "{}";
      };

      const actions = await client.listActions();
      expect(Array.isArray(actions)).toBe(true);
      expect(actions.length).toBe(2);
      expect(actions[0].action_id).toBe("ocr.run");
      expect(actions[0].execution_mode).toBe("stream");
    });

    it("preserves confirm flag when running streaming action", async () => {
      transport.executeHandler = (argv) => {
        if (argv.includes("describe")) {
          return JSON.stringify({
            ok: true,
            command: "action.describe",
            version: "1.5.15",
            data: {
              action_id: "foundation.update",
              execution_mode: "stream",
            },
          });
        }
        return "{}";
      };

      let capturedArgv: string[] = [];
      transport.streamHandler = (argv) => {
        capturedArgv = argv;
        return {
          events: [
            {
              schema_version: 1,
              event: "start",
              operation: "action.foundation.update",
            },
            {
              schema_version: 1,
              event: "result",
              operation: "action.foundation.update",
              result: { ok: true },
            },
          ],
          outcome: { ok: true, exitCode: 0 },
        };
      };

      const res = await client.runAction({
        action_id: "foundation.update",
        scope: { kind: "all" },
        confirm: "foundation.update",
      });

      expect(res.ok).toBe(true);
      expect(capturedArgv).toContain("--confirm");
      expect(capturedArgv[capturedArgv.indexOf("--confirm") + 1]).toBe(
        "foundation.update"
      );
    });

    it("preserves follow auto flag when running streaming action", async () => {
      transport.executeHandler = (argv) => {
        if (argv.includes("describe")) {
          return JSON.stringify({
            ok: true,
            command: "action.describe",
            version: "1.5.15",
            data: {
              action_id: "ocr.run",
              execution_mode: "stream",
            },
          });
        }
        return "{}";
      };

      let capturedArgv: string[] = [];
      transport.streamHandler = (argv) => {
        capturedArgv = argv;
        return {
          events: [
            { schema_version: 1, event: "start", operation: "action.ocr.run" },
            {
              schema_version: 1,
              event: "result",
              operation: "action.ocr.run",
              result: { ok: true },
            },
          ],
          outcome: { ok: true, exitCode: 0 },
        };
      };

      const res = await client.runAction({
        action_id: "ocr.run",
        scope: { kind: "papers", keys: ["PAPER1"] },
        follow: "auto",
      });

      expect(res.ok).toBe(true);
      expect(capturedArgv).toContain("--follow");
      expect(capturedArgv[capturedArgv.indexOf("--follow") + 1]).toBe("auto");
      expect(capturedArgv).toContain("--key");
      expect(capturedArgv[capturedArgv.indexOf("--key") + 1]).toBe("PAPER1");
    });
  });

  describe("Generation / Epoch Invalidation & Anti-Resurrection Guard", () => {
    it("discards late-arriving reads across a mutation boundary so they never resurrect stale cache", async () => {
      let resolveSlowRead: (val: string) => void;
      const slowReadPromise = new Promise<string>((res) => {
        resolveSlowRead = res;
      });

      let readCallCount = 0;
      transport.executeHandler = (argv) => {
        if (argv.includes("probe") && argv.includes("ocr")) {
          readCallCount++;
          if (readCallCount === 1) {
            // First read is slow
            return slowReadPromise;
          }
          // Subsequent reads return fresh ready status
          return mockEnvelope("ocr", "ready");
        }
        if (argv.includes("action") && argv.includes("run")) {
          return JSON.stringify({ ok: true, data: {} });
        }
        return "{}";
      };

      // 1. Start Read A at generation 0
      const initialEpoch = client.getEpoch();
      const slowRead = client.probe("ocr");
      expect(readCallCount).toBe(1);

      // 2. Mutation B runs and commits, bumping generation to 1
      await client.runAction({
        action_id: "ocr.rebuild",
        scope: { kind: "all" },
      });
      expect(client.getEpoch()).toBe(initialEpoch + 1);

      // 3. Old Read A from generation 0 finally resolves with stale status
      resolveSlowRead!(mockEnvelope("ocr", "degraded"));
      const slowResult = await slowRead;
      expect(slowResult.capability_state).toBe("degraded");

      // 4. Critical check: assert stale Read A did NOT populate the generation 1 cache!
      const freshRead = await client.probe("ocr");
      expect(freshRead.capability_state).toBe("ready");
      expect(readCallCount).toBe(2); // Had to fetch fresh because stale result was NOT cached!
    });
  });

  describe("OperationLock & Execution Ownership", () => {
    it("locks client during active streaming operations and rejects concurrent long tasks", async () => {
      transport.streamHandler = () => ({
        delayMs: 50,
        events: [
          { schema_version: 1, event: "start", operation: "ocr" },
          { schema_version: 1, event: "result", operation: "ocr" },
        ],
        outcome: { ok: true, exitCode: 0 },
      });

      expect(client.isOperationActive()).toBe(false);

      const handle = client.streamOperation("ocr.task", ["ocr", "run"]);
      expect(client.isOperationActive()).toBe(true);
      expect(client.activeOperationId).toBe("ocr.task");

      // Second streaming operation must be rejected
      expect(() => {
        client.streamOperation("another.task", ["embed", "build"]);
      }).toThrow(/Another operation is already active/);

      const outcome = await handle.outcome;
      expect(outcome.ok).toBe(true);
      expect(client.isOperationActive()).toBe(false);
      expect(client.activeOperationId).toBeNull();
    });

    it("releases OperationLock on error, failure, or cancellation", async () => {
      // 1. Error release
      transport.streamHandler = () => ({
        events: [{ schema_version: 1, event: "error", operation: "test" }],
        outcome: { ok: false, exitCode: 1 },
      });

      const h1 = client.streamOperation("failing.task", ["test"]);
      await h1.outcome;
      expect(client.isOperationActive()).toBe(false);

      // 2. Cancellation release
      transport.streamHandler = () => ({
        delayMs: 200,
        events: [{ schema_version: 1, event: "start", operation: "test" }],
      });

      const h2 = client.streamOperation("cancellable.task", ["test"]);
      expect(client.isOperationActive()).toBe(true);
      client.cancelActiveOperation();
      const outcome = await h2.outcome;
      expect(outcome.cancelled).toBe(true);
      expect(client.isOperationActive()).toBe(false);
    });
  });
});
