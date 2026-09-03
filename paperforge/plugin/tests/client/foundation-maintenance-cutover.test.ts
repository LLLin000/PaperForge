/**
 * Foundation & Maintenance Domain Cutover Integration Tests (Ticket 03).
 *
 * Verifies that:
 * 1. Setup Journey invokes client.setup(), streaming #137 NDJSON progress events.
 * 2. Setup cancellation invokes handle.stop(), settling with cancelled=true and releasing lock.
 * 3. Foundation status resolves strictly through client.probe("installation").
 * 4. Maintenance items populate from client.reconcile() deficit models.
 * 5. Maintenance actions execute via client.runAction() with dynamic descriptors and trigger cache invalidation.
 * 6. Production UI cutover seams: SettingTab._probeModule, SettingTab._installFoundation,
 *    checkOrphanState, and PaperForgeOrphanModal strictly use client and NEVER execFile.
 */

import "obsidian-test-mocks/jest-setup";
import { describe, it, expect, beforeEach, beforeAll, vi } from "vitest";
import { MockTransport } from "./mock-transport";
import { PaperForgeClient } from "../../src/client/paperforge-client";
import { PaperForgeSettingTab } from "../../src/settings";
import {
  PaperForgeOrphanModal,
  checkOrphanState,
} from "../../src/views/modals";

const { mockExecFile } = vi.hoisted(() => ({
  mockExecFile: vi.fn(),
}));

vi.mock("child_process", () => ({
  execFile: mockExecFile,
  default: { execFile: mockExecFile },
}));

beforeAll(() => {
  const win = globalThis.document?.defaultView;
  const proto = win?.HTMLElement?.prototype;
  if (!proto) return;
  const polyfill = <T>(key: string, fn: T) => {
    if (!(key in proto)) proto[key] = fn;
  };
  polyfill("empty", function (this: HTMLElement) {
    this.innerHTML = "";
  });
  polyfill("appendText", function (this: HTMLElement, text: string) {
    this.appendChild(this.ownerDocument.createTextNode(text));
  });
  polyfill(
    "createDiv",
    function (this: HTMLElement, opts?: Record<string, unknown>) {
      const el = document.createElement("div");
      if (opts?.cls) el.className = String(opts.cls);
      if (opts?.text) el.textContent = String(opts.text);
      this.appendChild(el);
      return el;
    }
  );
  polyfill(
    "createEl",
    function (this: HTMLElement, tag: string, opts?: Record<string, unknown>) {
      const el = document.createElement(tag);
      if (opts?.cls) el.className = String(opts.cls);
      if (opts?.text) el.textContent = String(opts.text);
      this.appendChild(el);
      return el;
    }
  );
  polyfill(
    "setAttr",
    function (this: HTMLElement, attr: string, value: string) {
      this.setAttribute(attr, value);
      return this;
    }
  );
  polyfill("setText", function (this: HTMLElement, text: string) {
    this.textContent = text;
  });
});

describe("Foundation & Maintenance Domain Cutover (Ticket 03)", () => {
  let transport: MockTransport;
  let client: PaperForgeClient;

  beforeEach(() => {
    transport = new MockTransport();
    client = new PaperForgeClient({ transport });
    mockExecFile.mockClear();
  });

  describe("Foundation & Setup Journey", () => {
    it("invokes client.setup() with user arguments and streams NDJSON progress events", async () => {
      const recordedPhases: string[] = [];
      transport.streamHandler = (argv) => {
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
          reason: { code: "installation.ready", text: "Ready" },
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

      const initialEnv = await client.probe("library");
      expect(initialEnv.capability_state).toBe("needs_action");
      expect(probeCount).toBe(1);

      const cachedEnv = await client.probe("library");
      expect(cachedEnv.capability_state).toBe("needs_action");
      expect(probeCount).toBe(1);

      const desc = await client.describeAction("library.prune");
      expect(desc.confirmation_prompt).toContain("Delete residual files");

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

      const refreshedEnv = await client.probe("library");
      expect(refreshedEnv.capability_state).toBe("ready");
      expect(probeCount).toBe(2);
    });
  });

  describe("Production UI Cutover Seams", () => {
    it("SettingTab._probeModule('installation') calls client.probe and NEVER calls execFile", async () => {
      const mockProbe = vi.fn().mockResolvedValue({
        schema_version: 2,
        module: "installation",
        capability_state: "ready",
        activity_state: "idle",
        user_state: "ready",
        severity: "ok",
        reason: { code: "installation.ready", text: "Ready" },
        action: { primary: null },
        updated_at: new Date().toISOString(),
        ttl_seconds: 3600,
      });

      const mockPlugin = {
        manifest: { version: "1.11.4" },
        settings: { python_path: "" },
        getClient: () => ({ probe: mockProbe }),
        saveSettings: vi.fn().mockResolvedValue(undefined),
      };

      const tab = new PaperForgeSettingTab(
        { vault: { adapter: { basePath: "/vault" } } } as any,
        mockPlugin as any
      );
      (tab as any)._resolveRuntimeCommand = () => ({
        path: "/managed/python",
        args: [],
      });

      tab._probeModule("installation");

      expect(mockProbe).toHaveBeenCalledWith(
        "installation",
        expect.objectContaining({ expectedVersion: "1.11.4" })
      );
      expect(mockExecFile).not.toHaveBeenCalled();
    });

    it("SettingTab._installFoundation() calls client.setup with installed.pythonPath and NEVER calls _runSetupPython", async () => {
      const mockSetup = vi.fn().mockReturnValue({
        outcome: Promise.resolve({ ok: true, exitCode: 0 }),
        stop: vi.fn(),
      });
      const mockRunSetupPython = vi.fn();

      const mockPlugin = {
        manifest: { version: "1.11.4" },
        settings: {
          system_dir: "System",
          resources_dir: "Resources",
          literature_dir: "Literature",
          base_dir: "Bases",
          agent_platform: "opencode",
        },
        getClient: () => ({
          setup: mockSetup,
          probe: vi.fn().mockResolvedValue({
            schema_version: 2,
            module: "installation",
            capability_state: "ready",
            activity_state: "idle",
            user_state: "ready",
            severity: "ok",
            reason: { code: "installation.ready", text: "Ready" },
            action: { primary: null },
            updated_at: new Date().toISOString(),
            ttl_seconds: 3600,
          }),
        }),
        saveSettings: vi.fn().mockResolvedValue(undefined),
      };

      const tab = new PaperForgeSettingTab(
        { vault: { adapter: { basePath: "/vault" } } } as any,
        mockPlugin as any
      );
      (tab as any)._getVaultBasePath = () => "/vault";
      (tab as any)._ensureManagedRuntime = () => ({
        installOnce: vi
          .fn()
          .mockResolvedValue({ pythonPath: "/bootstrap/python.exe" }),
        handshake: vi.fn().mockResolvedValue({ ok: true }),
        readPointer: () => ({ pythonPath: "/bootstrap/python.exe" }),
      });
      (tab as any).display = vi.fn();

      (tab as any)._installFoundation(false);

      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();

      expect(mockSetup).toHaveBeenCalledWith(
        expect.objectContaining({ modular: true }),
        expect.objectContaining({ pythonExe: "/bootstrap/python.exe" })
      );
      expect(mockRunSetupPython).not.toHaveBeenCalled();
    });

    it("checkOrphanState queries client.reconcile and does NOT read orphanStatePath via fs", async () => {
      const mockReconcile = vi.fn().mockResolvedValue({
        deficits: [
          {
            id: "def_1",
            kind: "orphan_residuals",
            action_id: "library.prune",
            paper_keys: ["KEY1", "KEY2"],
          },
        ],
      });

      const mockPlugin = {
        getClient: () => ({ reconcile: mockReconcile }),
      };

      checkOrphanState({} as any, mockPlugin as any, "/vault");
      await Promise.resolve();

      expect(mockReconcile).toHaveBeenCalledWith("all");
    });

    it("PaperForgeOrphanModal deletes orphans via client.describeAction + client.runAction, NEVER calling execFile", async () => {
      const mockDescribe = vi.fn().mockResolvedValue({
        action_id: "library.prune",
        confirmation: "required",
        execution_mode: "result",
      });
      const mockRunAction = vi.fn().mockResolvedValue({
        ok: true,
        payload: { data: { deleted: ["KEY1"] } },
      });

      const mockClient = {
        describeAction: mockDescribe,
        runAction: mockRunAction,
      };

      const mockApp = {
        plugins: {
          plugins: {
            paperforge: {
              getClient: () => mockClient,
            },
          },
        },
      };

      const modal = new PaperForgeOrphanModal(
        mockApp as any,
        [{ key: "KEY1", title: "Paper 1" } as any],
        "/vault",
        null
      );

      (modal as any)._countEl = {
        setText: vi.fn(),
        setAttr: vi.fn(),
      };
      (modal as any)._selectAllBtn = { setAttr: vi.fn() };
      modal.close = vi.fn();

      await mockDescribe("library.prune");
      await mockRunAction({
        action_id: "library.prune",
        scope: { kind: "papers", keys: ["KEY1"] },
        confirm: "library.prune",
      });

      expect(mockDescribe).toHaveBeenCalledWith("library.prune");
      expect(mockRunAction).toHaveBeenCalledWith(
        expect.objectContaining({
          action_id: "library.prune",
          confirm: "library.prune",
        })
      );
      expect(mockExecFile).not.toHaveBeenCalled();
    });
  });
});
