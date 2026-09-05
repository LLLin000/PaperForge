/**
 * Knowledge & Retrieval Domain Cutover Integration Tests (Ticket 05).
 *
 * Verifies that:
 * 1. Dashboard search queries route through client.search(query, options).
 * 2. Dashboard deep retrieval queries (@ query) route through client.retrieve(query, { deep: true }).
 * 3. Search and retrieval fail closed with backend-unavailable when client is null.
 * 4. Neither search nor retrieve calls child_process.spawn or execFile.
 * 5. Smart Retrieval memory/embed build dispatches route through client.runAction().
 * 6. Streaming progress events update memory activity state and progress.
 * 7. Active embed build cancellation invokes client.cancelActiveOperation().
 */

import "obsidian-test-mocks/jest-setup";
import { describe, it, expect, beforeEach, beforeAll, vi } from "vitest";
import { MockTransport } from "./mock-transport";
import { PaperForgeClient } from "../../src/client/paperforge-client";
import { PaperForgeStatusView } from "../../src/views/dashboard";
import { PaperForgeSettingTab } from "../../src/settings";
import type { ActionPrimary } from "../../src/constants";

const { mockExecFile, mockSpawn } = vi.hoisted(() => ({
  mockExecFile: vi.fn(),
  mockSpawn: vi.fn(),
}));

vi.mock("child_process", () => ({
  execFile: mockExecFile,
  spawn: mockSpawn,
  default: { execFile: mockExecFile, spawn: mockSpawn },
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

describe("Knowledge & Retrieval Domain Cutover (Ticket 05)", () => {
  let transport: MockTransport;
  let client: PaperForgeClient;

  beforeEach(() => {
    transport = new MockTransport();
    client = new PaperForgeClient({ transport });
    mockExecFile.mockClear();
    mockSpawn.mockClear();
  });

  describe("Dashboard Search & Retrieval Seams", () => {
    function makeDashboard(clientInstance: PaperForgeClient | null) {
      const leaf = {} as any;
      const view = new (PaperForgeStatusView as any)(leaf) as any;
      view.app = {
        vault: { adapter: { basePath: "/vault" } },
        plugins: {
          plugins: {
            paperforge: {
              getClient: () => clientInstance,
            },
          },
        },
      };
      view._searchInput = document.createElement("input");
      view._searchResultsEl = document.createElement("div");
      view._renderSearchState = vi.fn();
      return view;
    }

    it("routes standard search through client.search and never spawns a child process", async () => {
      transport.executeHandler = (argv) => {
        return JSON.stringify({
          ok: true,
          data: {
            matches: [{ id: "doc-1", title: "Test Document" }],
          },
        });
      };
      const view = makeDashboard(client);
      view._searchMode = "title";
      view._searchInput.value = "machine learning";

      await view.executeSearch();

      expect(transport.calls).toHaveLength(1);
      expect(transport.calls[0].argv).toEqual([
        "search",
        "machine learning",
        "--limit",
        "20",
        "--json",
      ]);
      expect(view._searchResults).toEqual([
        { id: "doc-1", title: "Test Document" },
      ]);
      expect(view._searchState).toBe("results");
      expect(mockSpawn).not.toHaveBeenCalled();
      expect(mockExecFile).not.toHaveBeenCalled();
    });

    it("routes deep search (@ prefix) through client.retrieve with --deep flag and never spawns", async () => {
      transport.executeHandler = (argv) => {
        return JSON.stringify({
          ok: true,
          data: {
            matches: [{ id: "unit-1", text: "Deep search snippet" }],
          },
        });
      };
      const view = makeDashboard(client);
      view._searchMode = "@";
      view._searchInput.value = "@ transformer architecture";

      await view.executeSearch();

      expect(transport.calls).toHaveLength(1);
      expect(transport.calls[0].argv).toEqual([
        "retrieve",
        "transformer architecture",
        "--limit",
        "5",
        "--deep",
        "--json",
      ]);
      expect(view._searchResults).toEqual([
        { id: "unit-1", text: "Deep search snippet" },
      ]);
      expect(view._searchState).toBe("results");
      expect(mockSpawn).not.toHaveBeenCalled();
      expect(mockExecFile).not.toHaveBeenCalled();
    });

    it("fails closed with backend-unavailable when PaperForgeClient is missing", async () => {
      const view = makeDashboard(null);
      view._searchInput.value = "test query";

      await view.executeSearch();

      expect(view._searchState).toBe("backend-unavailable");
      expect(transport.calls).toHaveLength(0);
      expect(mockSpawn).not.toHaveBeenCalled();
    });
  });

  describe("Smart Retrieval & Memory Action Seams", () => {
    function makeSettingTab(clientInstance: PaperForgeClient) {
      const app = {
        vault: { adapter: { basePath: "/vault" } },
      } as any;
      const plugin = {
        getClient: () => clientInstance,
        settings: {},
        _embedProgress: null,
      } as any;
      const tab = new (PaperForgeSettingTab as any)(app, plugin) as any;
      tab.containerEl = document.createElement("div");
      tab._capabilityState = {
        memory: {
          schema_version: 2,
          module: "memory",
          capability_state: "degraded",
          activity_state: "idle",
          user_state: "degraded",
          severity: "warn",
          reason: { code: "memory.index_stale", text: "Vector index is stale" },
          action: {
            primary: {
              verb: "rebuild_index",
              action_id: "embed.build",
              label: "构建索引",
            },
          },
          updated_at: new Date().toISOString(),
          ttl_seconds: 60,
        },
      };
      tab.display = vi.fn();
      tab._refreshAllReadModels = vi.fn();
      return tab;
    }

    it("dispatches embed.build through client.runAction with streaming progress", async () => {
      transport.executeHandler = (argv) => {
        if (argv[0] === "action" && argv[1] === "describe") {
          return JSON.stringify({
            ok: true,
            data: {
              action_id: argv[2],
              availability: "available",
              execution_mode: "stream",
              confirmation: "none",
            },
          });
        }
        return "{}";
      };
      transport.streamHandler = async () => ({
        events: [
          {
            schema_version: 1,
            event: "start",
            operation: "embed.build",
            total: 2,
          },
          {
            schema_version: 1,
            event: "phase",
            operation: "embed.build",
            phase: "embedding",
          },
          {
            schema_version: 1,
            event: "progress",
            operation: "embed.build",
            current: 1,
            total: 2,
            item_id: "P1",
          },
          {
            schema_version: 1,
            event: "paper_settled",
            operation: "embed.build",
            key: "P1",
            outcome: "succeeded",
          },
          {
            schema_version: 1,
            event: "progress",
            operation: "embed.build",
            current: 2,
            total: 2,
            item_id: "P2",
          },
          {
            schema_version: 1,
            event: "paper_settled",
            operation: "embed.build",
            key: "P2",
            outcome: "succeeded",
          },
          {
            schema_version: 1,
            event: "result",
            operation: "embed.build",
            result: { ok: true, data: { papers_embedded: 2 } },
          },
        ],
      });

      const tab = makeSettingTab(client);
      tab._dispatchMemoryBuild("embed", "force");

      // Wait for async task to complete
      await vi.waitFor(() => {
        expect(tab._refreshAllReadModels).toHaveBeenCalled();
      });

      const streamCall = transport.calls.find((c) => c.kind === "stream");
      expect(streamCall?.argv).toEqual([
        "action",
        "run",
        "embed.build",
        "--scope",
        "all",
        "--confirm",
        "embed.build",
        "--json",
      ]);
      expect(tab._capabilityState.memory.activity_state).toBe("idle");
      expect(mockExecFile).not.toHaveBeenCalled();
    });

    it("dispatches embed.resume with --confirm embed.resume through client.runAction", async () => {
      transport.executeHandler = (argv) => {
        if (argv[0] === "action" && argv[1] === "describe") {
          return JSON.stringify({
            ok: true,
            data: {
              action_id: argv[2],
              availability: "available",
              execution_mode: "stream",
              confirmation: "none",
            },
          });
        }
        return "{}";
      };
      transport.streamHandler = async () => ({
        events: [
          {
            schema_version: 1,
            event: "start",
            operation: "embed.resume",
            total: 1,
          },
          {
            schema_version: 1,
            event: "result",
            operation: "embed.resume",
            result: { ok: true, data: { papers_embedded: 1 } },
          },
        ],
      });

      const tab = makeSettingTab(client);
      tab._dispatchMemoryBuild("embed", "resume");

      await vi.waitFor(() => {
        expect(tab._refreshAllReadModels).toHaveBeenCalled();
      });

      const streamCall = transport.calls.find((c) => c.kind === "stream");
      expect(streamCall?.argv).toEqual([
        "action",
        "run",
        "embed.resume",
        "--scope",
        "all",
        "--confirm",
        "embed.resume",
        "--json",
      ]);
    });

    it("dispatches local memory.rebuild through client.runAction", async () => {
      transport.executeHandler = (argv) => {
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
          return JSON.stringify({ ok: true, data: { built: 10 } });
        }
        return "{}";
      };

      const tab = makeSettingTab(client);
      tab._dispatchMemoryBuild("build");

      await vi.waitFor(() => {
        expect(tab._refreshAllReadModels).toHaveBeenCalled();
      });

      const runCall = transport.calls.find(
        (c) =>
          c.argv[0] === "action" &&
          c.argv[1] === "run" &&
          c.argv[2] === "memory.rebuild"
      );
      expect(runCall?.argv).toEqual([
        "action",
        "run",
        "memory.rebuild",
        "--scope",
        "all",
        "--confirm",
        "memory.rebuild",
        "--json",
      ]);
      expect(tab._capabilityState.memory.activity_state).toBe("idle");
    });
    it("rejects cross-domain actions like ocr.run and library.prune and never dispatches runAction", async () => {
      const tab = makeSettingTab(client);

      // Attempt to dispatch ocr.run in embed domain
      tab._dispatchMemoryBuild("embed", undefined, "ocr.run");
      expect(transport.calls).toHaveLength(0);
      expect(tab._capabilityState.memory.activity_state).toBe("idle");

      // Attempt to dispatch library.prune in build domain
      tab._dispatchMemoryBuild("build", undefined, "library.prune");
      expect(transport.calls).toHaveLength(0);
      expect(tab._capabilityState.memory.activity_state).toBe("idle");
    });

    it("fail-closed: unknown memory action id is never substituted with memory.build", () => {
      const unknownPrimary = {
        verb: "run",
        action_id: "memory.some_new_action",
        label: "X",
        availability: "available",
        safety_class: "safe",
        preservation_facts: [],
        replacement_facts: [],
        interruptible: true,
        confirmation_required: false,
        confirmation_prompt: null,
        scope: "module",
        scope_count: 1,
      } satisfies ActionPrimary;
      const tab = makeSettingTab(client);
      tab._probeModule = vi.fn();
      tab._runAllowedDispatch(
        "memory",
        unknownPrimary,
        tab._capabilityState.memory
      );
      const runCalls = transport.calls.filter(
        (c) => c.argv[0] === "action" && c.argv[1] === "run"
      );
      expect(runCalls).toHaveLength(0);
      expect(tab._probeModule).toHaveBeenCalledWith("memory");
    });

    it.each(["memory.build", "memory.rebuild"] as const)(
      "production entry dispatches %s through client.runAction without substitution",
      async (legalId) => {
        transport.executeHandler = (argv) => {
          if (argv[0] === "action" && argv[1] === "describe") {
            return JSON.stringify({
              ok: true,
              data: {
                action_id: argv[2],
                availability: "available",
                execution_mode: "stream",
                confirmation: "none",
              },
            });
          }
          return "{}";
        };
        transport.streamHandler = async () => ({
          events: [
            {
              schema_version: 1,
              event: "start",
              operation: legalId,
              total: 1,
            },
            {
              schema_version: 1,
              event: "result",
              operation: legalId,
              data: { ok: true },
            },
          ],
        });
        const tab = makeSettingTab(client);
        tab._probeModule = vi.fn();
        tab._runAllowedDispatch(
          "memory",
          {
            verb: "run",
            action_id: legalId,
            label: "Build",
            availability: "available",
            safety_class: "safe",
            preservation_facts: [],
            replacement_facts: [],
            interruptible: true,
            confirmation_required: false,
            confirmation_prompt: null,
            scope: "module",
            scope_count: 1,
          } satisfies ActionPrimary,
          tab._capabilityState.memory
        );
        await vi.waitFor(() => {
          expect(
            transport.calls.some(
              (c) => c.argv[0] === "action" && c.argv[1] === "run"
            )
          ).toBe(true);
        });
        const runCall = transport.calls.find(
          (c) => c.argv[0] === "action" && c.argv[1] === "run"
        );
        expect(runCall?.argv.slice(0, 3)).toEqual(["action", "run", legalId]);
        expect(tab._probeModule).not.toHaveBeenCalled();
      }
    );

    it("enables Stop button only when client owns the active operation handle", () => {
      const tab = makeSettingTab(client);
      tab._capabilityState.memory.activity_state = "running";
      tab._capabilityState.memory.activity_label = "Running elsewhere";

      // 1. Client has no active operation -> Stop button is NOT rendered
      const el1 = document.createElement("div");
      tab._renderMemoryDetail(el1);
      const stopBtn1 = [...el1.querySelectorAll("button")].find(
        (b) => b.textContent === "Stop"
      );
      expect(stopBtn1).toBeUndefined();

      // 2. Client owns active operation -> Stop button is rendered and clickable
      vi.spyOn(client, "isOperationActive").mockReturnValue(true);
      const cancelSpy = vi
        .spyOn(client, "cancelActiveOperation")
        .mockImplementation(() => {});
      const el2 = document.createElement("div");
      tab._renderMemoryDetail(el2);
      const stopBtn2 = [...el2.querySelectorAll("button")].find(
        (b) => b.textContent === "Stop"
      );
      expect(stopBtn2).toBeDefined();
      stopBtn2?.click();
      expect(cancelSpy).toHaveBeenCalledOnce();
    });
  });
});
