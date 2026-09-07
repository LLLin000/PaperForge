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
    describe("Search & Retrieve Query Interface", () => {
      it("supports search with options and backward-compatible numeric limit", async () => {
        transport.executeHandler = (argv) => {
          return JSON.stringify({
            ok: true,
            data: { matches: [{ id: "1" }], argv },
          });
        };

        const res1 = await client.search("cancer", { limit: 10 });
        expect(transport.calls[transport.calls.length - 1].argv).toEqual([
          "search",
          "cancer",
          "--limit",
          "10",
          "--json",
        ]);
        expect(res1).toEqual([{ id: "1" }]);

        await client.search("cancer", 15);
        expect(transport.calls[transport.calls.length - 1].argv).toEqual([
          "search",
          "cancer",
          "--limit",
          "15",
          "--json",
        ]);
      });

      it("supports retrieve with options (deep, paper) and backward-compatible numeric limit", async () => {
        transport.executeHandler = (argv) => {
          return JSON.stringify({
            ok: true,
            data: { matches: [{ id: "2" }], argv },
          });
        };

        const res1 = await client.retrieve("quantum", {
          limit: 8,
          deep: true,
          paper: "P123",
        });
        expect(transport.calls[transport.calls.length - 1].argv).toEqual([
          "retrieve",
          "quantum",
          "--limit",
          "8",
          "--deep",
          "--paper",
          "P123",
          "--json",
        ]);
        expect(res1).toEqual([{ id: "2" }]);

        await client.retrieve("quantum", 3);
        expect(transport.calls[transport.calls.length - 1].argv).toEqual([
          "retrieve",
          "quantum",
          "--limit",
          "3",
          "--json",
        ]);
      });

      it("invalidates search and memory caches across generation epoch on build actions", async () => {
        let searchCallCount = 0;
        transport.executeHandler = (argv) => {
          if (argv[0] === "search") {
            searchCallCount++;
            return JSON.stringify({ ok: true, data: { matches: [] } });
          }
          if (argv[0] === "action" && argv[1] === "describe") {
            return JSON.stringify({
              ok: true,
              data: {
                action_id: argv[2],
                availability: "available",
                execution_mode: "result",
                confirmation: "none",
              },
            });
          }
          if (argv[0] === "action" && argv[1] === "run") {
            return JSON.stringify({ ok: true, data: { status: "ok" } });
          }
          return "{}";
        };

        await client.search("test");
        expect(searchCallCount).toBe(1);

        // Same search within TTL is cached
        await client.search("test");
        expect(searchCallCount).toBe(1);

        // Run action invalidates cache
        await client.runAction({ action_id: "memory.rebuild" });

        // Next search fetches fresh from transport
        await client.search("test");
        expect(searchCallCount).toBe(2);
      });
    });
  });

  /**
   * Configuration & Read-Model Contract (Ticket 07 Stage 2 step 2).
   *
   * Regression guard carried over from the deleted config-client.ts
   * (read-model-client.test.ts): the typed methods must emit exactly
   * `paperforge <subcommand> ... --json`; the client owns the only argv
   * assembly and the only PFResult unwrap. A structured ok:false PFResult is
   * an authority rejection — fail closed, never a null payload.
   */
  describe("Configuration & Read-Model Contract (#07 step 2)", () => {
    let transport: MockTransport;
    let client: PaperForgeClient;

    beforeEach(() => {
      transport = new MockTransport();
      client = new PaperForgeClient({ transport });
    });

    it("configList emits `config list --json` and unwraps the PFResult data", async () => {
      transport.executeHandler = () =>
        JSON.stringify({ ok: true, data: { fields: [{ key: "system_dir" }] } });
      const data = await client.configList();
      expect(transport.calls.map((c) => c.argv)).toEqual([
        ["config", "list", "--json"],
      ]);
      expect(data.fields).toEqual([{ key: "system_dir" }]);
    });

    it("configSet emits `config set <key> <value> --json` and invalidates the cache", async () => {
      let reads = 0;
      transport.executeHandler = (argv) => {
        if (argv[1] === "set")
          return JSON.stringify({ ok: true, data: { changed: true } });
        reads += 1;
        return JSON.stringify({ ok: true, data: { n: reads } });
      };
      const probed = await client.memoryStatus();
      await client.configSet("system_dir", "/vault/System");
      const probed2 = await client.memoryStatus();
      expect(transport.calls[0].argv).toEqual(["memory", "status", "--json"]);
      expect(transport.calls[1].argv).toEqual([
        "config",
        "set",
        "system_dir",
        "/vault/System",
        "--json",
      ]);
      expect(probed2).not.toEqual(probed);
    });

    it("configMigrate emits the dry-run flag in the right position and returns the real Python wire DTO", async () => {
      transport.executeHandler = () =>
        JSON.stringify({
          ok: true,
          data: {
            schema_version: 1,
            revision: "r1",
            unknown_keys: [],
            changed: false,
            dry_run: true,
            warnings: [],
          },
        });
      const result = await client.configMigrate(true);
      // Runtime returned DTO equals the real Python wire, not just the
      // transport fixture shape.
      expect(result).toEqual({
        schema_version: 1,
        revision: "r1",
        unknown_keys: [],
        changed: false,
        dry_run: true,
        warnings: [],
      });
      await client.configMigrate(false);
      expect(transport.calls.map((c) => c.argv)).toEqual([
        ["config", "migrate", "--dry-run", "--json"],
        ["config", "migrate", "--json"],
      ]);
    });

    it("configValidate and credentialAvailable emit their authority argv", async () => {
      transport.executeHandler = (argv) => {
        if (argv[0] === "auth")
          return JSON.stringify({
            ok: true,
            data: { credentials: [{ state: "available" }] },
          });
        return JSON.stringify({ ok: true, data: { state: "ok" } });
      };
      expect(await client.configValidate()).toEqual({ state: "ok" });
      expect(await client.credentialAvailable("ocr")).toBe(true);
      expect(transport.calls.map((c) => c.argv)).toEqual([
        ["config", "validate", "--json"],
        ["auth", "status", "ocr", "--json"],
      ]);
    });

    it("embedStatus and memoryStatus emit exact argv and cache within TTL", async () => {
      let calls = 0;
      transport.executeHandler = () => {
        calls += 1;
        return JSON.stringify({ ok: true, data: { model: "m" } });
      };
      await client.embedStatus();
      await client.embedStatus();
      await client.memoryStatus();
      await client.memoryStatus();
      expect(calls).toBe(2);
      expect(transport.calls.map((c) => c.argv)).toEqual([
        ["embed", "status", "--json"],
        ["memory", "status", "--json"],
      ]);
    });

    it("authSetSecret passes the secret ONLY via ExecuteOptions.stdin, never argv", async () => {
      transport.executeHandler = () =>
        JSON.stringify({ ok: true, data: { stored: true } });
      const saved = await client.authSetSecret("embedding", "sk-secret-123");
      expect(saved).toBe(true);
      const call = transport.calls[0];
      expect(call.argv).toEqual([
        "auth",
        "set",
        "embedding",
        "--stdin",
        "--replace",
        "--json",
      ]);
      expect(call.argv.join(" ")).not.toContain("sk-secret-123");
      expect(call.options?.stdin).toBe("sk-secret-123\n");
    });

    it("authSetSecret({replace:false}) — the legacy-migration shape — never overwrites a live keyring value", async () => {
      transport.executeHandler = () =>
        JSON.stringify({ ok: true, data: { stored: true } });
      await client.authSetSecret("ocr", "legacy-copy", { replace: false });
      expect(transport.calls[0].argv).toEqual([
        "auth",
        "set",
        "ocr",
        "--stdin",
        "--json",
      ]);
      expect(transport.calls[0].options?.stdin).toBe("legacy-copy\n");
    });

    it("authSetSecret invalidates cached credential/descriptor reads (mutation contract)", async () => {
      let available = false;
      transport.executeHandler = (argv) => {
        if (argv[0] === "auth" && argv[1] === "status") {
          return JSON.stringify({
            ok: true,
            data: {
              credentials: [{ state: available ? "available" : "missing" }],
            },
          });
        }
        return JSON.stringify({ ok: true, data: { stored: true } });
      };
      // First read: unavailable, cached for 60s.
      expect(await client.credentialAvailable("ocr")).toBe(false);
      // Save the key — the mutation must bump the epoch.
      await client.authSetSecret("ocr", "sk-1");
      available = true;
      // Second read MUST hit the transport again, not the stale cache.
      expect(await client.credentialAvailable("ocr")).toBe(true);
      const statusCalls = transport.calls.filter(
        (c) => c.argv[0] === "auth" && c.argv[1] === "status"
      );
      expect(statusCalls.length).toBe(2);
    });

    it("embedMigrate emits its authority argv and invalidates the cache", async () => {
      let reads = 0;
      transport.executeHandler = (argv) => {
        if (argv[0] === "embed" && argv[1] === "migrate")
          return JSON.stringify({ ok: true, data: { migrated: 3 } });
        reads += 1;
        return JSON.stringify({ ok: true, data: { n: reads } });
      };
      const before = await client.embedStatus();
      await client.embedMigrate();
      const after = await client.embedStatus();
      expect(transport.calls[1].argv).toEqual(["embed", "migrate", "--json"]);
      expect(after).not.toEqual(before);
    });

    it("memoryRestoreBackup and runtimeHealth emit their authority argv", async () => {
      transport.executeHandler = () => JSON.stringify({ ok: true, data: {} });
      await client.memoryRestoreBackup();
      await client.runtimeHealth();
      expect(transport.calls.map((c) => c.argv)).toEqual([
        ["memory", "restore-backup", "--json"],
        ["runtime-health", "--json"],
      ]);
    });

    it("backendVersion parses the plain version line from exact argv", async () => {
      transport.executeHandler = () => "paperforge 1.2.3\n";
      const v = await client.backendVersion();
      expect(transport.calls[0].argv).toEqual(["--version"]);
      expect(v).toBe("1.2.3");
    });

    it("doctor and repair emit their authority argv; repair invalidates", async () => {
      let reads = 0;
      transport.executeHandler = (argv) => {
        if (argv[0] === "repair") {
          return JSON.stringify({ ok: true, data: { fixed: 2 } });
        }
        reads += 1;
        return JSON.stringify({ ok: true, data: { n: reads } });
      };
      expect(await client.doctor()).toEqual({ n: 1 });
      await client.repair();
      expect(transport.calls.map((c) => c.argv)).toEqual([
        ["doctor", "--json"],
        ["repair", "--fix", "--fix-paths", "--json"],
      ]);
      // repair is a mutation — cached reads must refetch.
      const after = await client.embedStatus();
      expect(after).toEqual({ n: 2 });
    });

    it("dashboardStats emits its authority argv (single stats authority)", async () => {
      transport.executeHandler = () =>
        JSON.stringify({ ok: true, data: { stats: { papers: 3 } } });
      const body = await client.dashboardStats();
      expect(transport.calls[0].argv).toEqual(["dashboard", "--json"]);
      expect((body as any).stats.papers).toBe(3);
    });

    it("memoryRestoreBackup invalidates cached read models (mutation contract)", async () => {
      let version = 1;
      transport.executeHandler = (argv) => {
        if (argv[0] === "memory" && argv[1] === "status") {
          return JSON.stringify({
            ok: true,
            data: { paper_count_db: version },
          });
        }
        return JSON.stringify({ ok: true, data: {} });
      };
      const before = await client.memoryStatus();
      version = 2;
      await client.memoryRestoreBackup();
      const after = await client.memoryStatus();
      expect(after).not.toEqual(before);
      expect(after.paper_count_db).toBe(2);
    });

    it("rc=1 + structured ok:false stdout preserves the authority reason (real machine contract)", async () => {
      // The Python config contract emits a STRUCTURED ok:false PFResult on
      // stdout together with a non-zero exit code. NodeProcessTransport
      // rejects non-zero exits attaching err.stdout; the client must
      // recover the machine-readable authority reason from that stdout
      // instead of losing it to a generic "exit code 1" error (legacy
      // config-client behavior, preserved here).
      const transportErr: any = new Error(
        "PaperForge command failed (exit code 1): config validate"
      );
      transportErr.exitCode = 1;
      transportErr.stdout = JSON.stringify({
        ok: false,
        command: "config.validate",
        version: "1",
        data: null,
        error: {
          code: "validation_error",
          message: "config.migration_required",
          details: {},
        },
      });
      transport.executeHandler = () => {
        throw transportErr;
      };
      await expect(client.configValidate()).rejects.toThrow(
        "config.migration_required"
      );
    });

    it("rc=1 with ok:true stdout is a protocol contradiction — the transport error wins", async () => {
      const transportErr: any = new Error("exit 1");
      transportErr.exitCode = 1;
      transportErr.stdout = JSON.stringify({ ok: true, data: { state: "ok" } });
      transport.executeHandler = () => {
        throw transportErr;
      };
      await expect(client.configValidate()).rejects.toThrow("exit 1");
    });

    it("transport failure without structured stdout rethrows the transport error", async () => {
      transport.executeHandler = () => {
        throw new Error("spawn ENOENT");
      };
      await expect(client.configValidate()).rejects.toThrow("spawn ENOENT");
    });

    it("resolved ok:false PFResult is an authority rejection (fail closed)", async () => {
      transport.executeHandler = () =>
        JSON.stringify({
          ok: false,
          data: null,
          error: {
            code: "config.migration_required",
            message: "migrate first",
          },
        });
      await expect(client.configValidate()).rejects.toThrow("migrate first");
    });
  });
});
