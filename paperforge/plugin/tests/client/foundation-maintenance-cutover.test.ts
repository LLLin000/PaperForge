/**
 * Foundation & Maintenance Domain Cutover Integration Tests (Ticket 03).
 *
 * Verifies that:
 * 1. Setup Journey invokes client.setup(), streaming #137 NDJSON progress events.
 * 2. Setup cancellation invokes handle.stop(), settling with cancelled=true and releasing lock.
 * 3. Foundation status resolves strictly through client.probe("installation").
 * 4. Maintenance items populate from client.reconcile() deficit models.
 * 5. Maintenance actions execute via client.runAction() with dynamic descriptors and trigger cache invalidation.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { MockTransport } from "./mock-transport";
import { PaperForgeClient } from "../../src/client/paperforge-client";

describe("Foundation & Maintenance Domain Cutover (Ticket 03)", () => {
  let transport: MockTransport;
  let client: PaperForgeClient;

  beforeEach(() => {
    transport = new MockTransport();
    client = new PaperForgeClient({ transport });
  });

  describe("Foundation & Setup Journey", () => {
    it("invokes client.setup() with user arguments and streams NDJSON progress events", async () => {
      const recordedPhases: string[] = [];
      transport.streamHandler = (argv, opts) => {
        expect(argv).toContain("setup");
        expect(argv).toContain("--modular");
        expect(argv).toContain("--json");
        expect(argv).toContain("--system-dir");
        expect(argv[argv.indexOf("--system-dir") + 1]).toBe("CustomSystem");

        return {
          events: [
            {
              schema_version: 1,
              event: "start",
              operation: "foundation.setup",
            },
            {
              schema_version: 1,
              event: "phase",
              operation: "foundation.setup",
              phase: "checker",
            },
            {
              schema_version: 1,
              event: "phase",
              operation: "foundation.setup",
              phase: "config_writer",
            },
            {
              schema_version: 1,
              event: "phase",
              operation: "foundation.setup",
              phase: "vault_initializer",
            },
            {
              schema_version: 1,
              event: "result",
              operation: "foundation.setup",
              result: { ok: true },
            },
          ],
          outcome: { ok: true, exitCode: 0 },
        };
      };

      const handle = client.setup(
        {
          systemDir: "CustomSystem",
          resourcesDir: "Resources",
          literatureDir: "Literature",
          baseDir: "Bases",
          agent: "opencode",
          skipChecks: false,
          modular: true,
        },
        {
          onEvent: (ev) => {
            if (ev.event === "phase" && typeof ev.phase === "string") {
              recordedPhases.push(ev.phase);
            }
          },
        }
      );

      expect(client.isOperationActive()).toBe(true);
      const outcome = await handle.outcome;

      expect(outcome.ok).toBe(true);
      expect(outcome.exitCode).toBe(0);
      expect(recordedPhases).toEqual([
        "checker",
        "config_writer",
        "vault_initializer",
      ]);
      expect(client.isOperationActive()).toBe(false);
    });

    it("cancels Setup Journey cooperatively and releases OperationLock", async () => {
      transport.streamHandler = () => ({
        delayMs: 150,
        events: [
          { schema_version: 1, event: "start", operation: "foundation.setup" },
          {
            schema_version: 1,
            event: "phase",
            operation: "foundation.setup",
            phase: "checker",
          },
        ],
      });

      const handle = client.setup({ modular: true });
      expect(client.isOperationActive()).toBe(true);

      // Trigger cooperative stop
      handle.stop();
      const outcome = await handle.outcome;

      expect(outcome.cancelled).toBe(true);
      expect(outcome.exitCode).toBe(130);
      expect(client.isOperationActive()).toBe(false);
    });

    it("connects Foundation status strictly to client.probe('installation')", async () => {
      transport.executeHandler = (argv) => {
        expect(argv).toContain("probe");
        expect(argv).toContain("installation");
        expect(argv).toContain("--expected-version");
        expect(argv[argv.indexOf("--expected-version") + 1]).toBe("1.11.4");

        return JSON.stringify({
          schema_version: 2,
          module: "installation",
          capability_state: "ready",
          activity_state: "idle",
          user_state: "ready",
          severity: "ok",
          reason: { code: "installation.ready", text: "Runtime ready" },
          action: { primary: null },
          updated_at: new Date().toISOString(),
          ttl_seconds: 3600,
        });
      };

      const envelope = await client.probe("installation", {
        expectedVersion: "1.11.4",
      });
      expect(envelope.module).toBe("installation");
      expect(envelope.capability_state).toBe("ready");
      expect(envelope.severity).toBe("ok");
    });
  });

  describe("Maintenance & Deficit Remediation", () => {
    it("populates maintenance items directly from client.reconcile() deficit outputs", async () => {
      transport.executeHandler = (argv) => {
        if (argv.includes("reconcile")) {
          return JSON.stringify({
            deficits: [
              {
                id: "def_1",
                module: "library",
                kind: "orphan_residuals",
                severity: "warning",
                paper_keys: ["PAPER_A", "PAPER_B"],
              },
            ],
            next_actions: [
              {
                action_id: "library.prune",
                scope: { kind: "papers", keys: ["PAPER_A", "PAPER_B"] },
                reason: "Residual papers detected",
              },
            ],
          });
        }
        return "{}";
      };

      const report = (await client.reconcile("all")) as any;
      expect(report.deficits).toHaveLength(1);
      expect(report.next_actions).toHaveLength(1);
      expect(report.next_actions[0].action_id).toBe("library.prune");
      expect(report.next_actions[0].scope.keys).toEqual(["PAPER_A", "PAPER_B"]);
    });

    it("executes maintenance actions via client.runAction() and invalidates cache", async () => {
      let probeCount = 0;
      let pruneExecuted = false;

      transport.executeHandler = (argv) => {
        if (argv.includes("describe")) {
          return JSON.stringify({
            ok: true,
            command: "action.describe",
            version: "1.5.15",
            data: {
              action_id: "library.prune",
              label_code: "action.library.prune",
              execution_mode: "result",
              confirmation: "required",
              confirmation_prompt: "Delete residual files for 2 papers?",
            },
          });
        }
        if (
          argv.includes("action") &&
          argv.includes("run") &&
          argv.includes("library.prune")
        ) {
          expect(argv).toContain("--confirm");
          expect(argv[argv.indexOf("--confirm") + 1]).toBe("library.prune");
          expect(argv).toContain("--key");
          pruneExecuted = true;
          return JSON.stringify({
            ok: true,
            command: "action run",
            version: "1.5.15",
            data: { deleted: ["PAPER_A", "PAPER_B"] },
          });
        }
        if (argv.includes("probe") && argv.includes("library")) {
          probeCount++;
          return JSON.stringify({
            schema_version: 2,
            module: "library",
            capability_state: pruneExecuted ? "ready" : "needs_action",
            user_state: pruneExecuted ? "ready" : "action_required",
            severity: pruneExecuted ? "ok" : "warning",
            reason: {
              code: pruneExecuted ? "library.ready" : "library.residuals",
            },
            action: { primary: null },
            updated_at: new Date().toISOString(),
            ttl_seconds: 60,
          });
        }
        return "{}";
      };

      // 1. Initial probe shows needs_action
      const initialEnv = await client.probe("library");
      expect(initialEnv.capability_state).toBe("needs_action");
      expect(probeCount).toBe(1);

      // 2. Subsequent probe is cached within TTL
      const cachedEnv = await client.probe("library");
      expect(cachedEnv.capability_state).toBe("needs_action");
      expect(probeCount).toBe(1); // Cached!

      // 3. Inspect action descriptor
      const desc = await client.describeAction("library.prune");
      expect(desc.confirmation_prompt).toContain("Delete residual files");

      // 4. Run confirmed mutation action
      const result = await client.runAction({
        action_id: "library.prune",
        scope: { kind: "papers", keys: ["PAPER_A", "PAPER_B"] },
        confirm: "library.prune",
      });

      expect(result.ok).toBe(true);
      expect((result.payload?.data as any)?.deleted).toEqual([
        "PAPER_A",
        "PAPER_B",
      ]);

      // 5. Cache is invalidated by mutation -> next probe fetches fresh data
      const refreshedEnv = await client.probe("library");
      expect(refreshedEnv.capability_state).toBe("ready");
      expect(probeCount).toBe(2); // Fresh call made after cache invalidation!
    });
  });
});
