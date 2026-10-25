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
      const leaf = {};
      const view = new PaperForgeStatusView(leaf) as unknown as {
        app: unknown;
        _searchInput: HTMLInputElement;
        _searchResultsEl: HTMLElement;
        _searchState: string;
        _searchMode: string;
        _searchDeep: boolean;
        _host: HTMLElement;
        renderSearchSection: (host: HTMLElement) => void;
        executeSearch: (forceDeep?: boolean) => Promise<void>;
        _renderSearchState: () => void;
      };
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
      const host = document.createElement("div");
      document.body.appendChild(host);
      view.renderSearchSection(host);
      view._host = host;
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
      view._host.remove();
      const searchCalls = transport.calls.filter(
        (c: { argv: string[] }) => c.argv[0] === "search"
      );
      expect(searchCalls).toHaveLength(1);
      expect(searchCalls[0].argv).toEqual([
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
      view._host.remove();
      const retrieveCalls = transport.calls.filter(
        (c: { argv: string[] }) => c.argv[0] === "retrieve"
      );
      expect(retrieveCalls).toHaveLength(1);
      expect(retrieveCalls[0].argv).toEqual([
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
    it("renders deep labels for '@ ' and leading-whitespace '@' with real DOM and retrieve argv", async () => {
      transport.executeHandler = () => {
        return JSON.stringify({
          ok: true,
          data: { matches: [{ id: "unit-space", text: "At-space snippet" }] },
        });
      };
      for (const value of ["@ hello", "  @ hello"]) {
        const view = makeDashboard(client);
        view._searchInput.value = value;
        view._searchInput.dispatchEvent(new Event("input"));
        expect(
          view._host.querySelector(".paperforge-search-mode")?.textContent
        ).toBe("@");
        await view.executeSearch();
        const retrieveCalls = transport.calls.filter(
          (c: { argv: string[] }) => c.argv[0] === "retrieve"
        );
        expect(retrieveCalls.at(-1)?.argv).toEqual([
          "retrieve",
          "hello",
          "--limit",
          "5",
          "--deep",
          "--json",
        ]);
        // Real render seam: loading label then results header carry deep.
        const header = view._host.querySelector(
          ".paperforge-search-results-header .paperforge-search-mode"
        );
        expect(header?.textContent).toBe("@");
        view._host.remove();
      }
      expect(mockSpawn).not.toHaveBeenCalled();
      expect(mockExecFile).not.toHaveBeenCalled();
    });

    it("keeps forced deep request one-shot: forced deep once, plain Enter stays metadata, mode survives in-flight change", async () => {
      const seen: string[][] = [];
      transport.executeHandler = (argv: string[]) => {
        seen.push(argv);
        return JSON.stringify({
          ok: true,
          data: { matches: [{ id: "u", text: "t" }] },
        });
      };
      const view = makeDashboard(client);
      view._searchInput.value = "plain query";
      view._searchInput.dispatchEvent(new Event("input"));
      expect(
        view._host.querySelector(".paperforge-search-mode")?.textContent
      ).toBe("M");
      // Forced deep for this request only: argv is retrieve, input mode stays M.
      await view.executeSearch(true);
      expect(seen.at(-1)?.[0]).toBe("retrieve");
      expect(view._searchInput.value).toBe("plain query");
      expect(view._searchMode).toBe("M");
      // Plain Enter on the unchanged input is metadata again.
      await view.executeSearch();
      expect(seen.at(-1)?.[0]).toBe("search");
      // In-flight input-mode change does not rewrite the settled label.
      const p = view.executeSearch(true);
      view._searchMode = "M";
      await p;
      expect(
        view._host.querySelector(
          ".paperforge-search-results-header .paperforge-search-mode"
        )?.textContent
      ).toBe("@");
      // A real Retry click after a failed forced-deep replays retrieve while
      // plain Enter stays metadata. Fail the deep request through the
      // transport, then click the rendered retry button and await the
      // retried request's completion via the transport gate.
      transport.executeHandler = () => {
        const e = new Error("rc1") as Error & { exitCode?: number; stdout?: string };
        e.exitCode = 1;
        e.stdout = JSON.stringify({ ok: false, data: null, error: { code: "PATH_NOT_FOUND", message: "no db" } });
        throw e;
      };
      client.invalidateCache();
      const failP = view.executeSearch(true);
      await failP.catch(() => undefined);
      expect(view._searchState).toBe("backend-unavailable");
      expect(view._searchDeep).toBe(true);
      const gate = Promise.withResolvers<void>();
      transport.executeHandler = (argv: string[]) => {
        seen.push(argv);
        gate.resolve();
        return JSON.stringify({ ok: true, data: { matches: [] } });
      };
      const buttons = [...view._host.querySelectorAll("button")];
      expect(buttons.length).toBeGreaterThan(0);
      buttons.at(-1)?.click();
      await gate.promise;
      expect(seen.at(-1)?.[0]).toBe("retrieve");
      await view.executeSearch();
      view._host.remove();
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

    it("maps metadata-search PATH_NOT_FOUND to missing-memory-index and deep-retrieve PATH_NOT_FOUND stays backend-unavailable", async () => {
      const seen: unknown[][] = [];
      const origErr = console.error;
      console.error = (...a: unknown[]) => void seen.push(a);
      try {
        transport.executeHandler = (argv: string[]) => {
          if (argv[0] === "reading-log") {
            return JSON.stringify({ ok: true, data: { matches: [] } });
          }
          const e = new Error("rc1") as Error & { exitCode?: number; stdout?: string };
          e.exitCode = 1;
          e.stdout = JSON.stringify({ ok: false, data: null, error: { code: "PATH_NOT_FOUND", message: "no db" } });
          throw e;
        };
        const meta = makeDashboard(client);
        meta._searchMode = "M";
        meta._searchInput.value = "metadata query";
        await meta.executeSearch();
        expect(meta._searchState).toBe("missing-memory-index");

        client.invalidateCache();
        const deep = makeDashboard(client);
        deep._searchMode = "@";
        deep._searchInput.value = "@ vector query";
        await deep.executeSearch();
        expect(deep._searchState).toBe("backend-unavailable");

        const genuine = makeDashboard(client);
        genuine._searchMode = "M";
        genuine._searchInput.value = "genuine failure";
        transport.executeHandler = (argv: string[]) => {
          if (argv[0] === "reading-log") {
            return JSON.stringify({ ok: true, data: { matches: [] } });
          }
          return JSON.stringify({ ok: false, data: null, error: { code: "BACKEND_UNAVAILABLE", message: "down" } });
        };
        await genuine.executeSearch();
        expect(genuine._searchState).toBe("backend-unavailable");

        client.invalidateCache();
        transport.executeHandler = () =>
          JSON.stringify({ ok: true, data: { matches: [] } });
        const empty = makeDashboard(client);
        empty._searchMode = "M";
        empty._searchInput.value = "empty query";
        await empty.executeSearch();
        expect(empty._searchState).toBe("empty");

        // Genuine terminals log exactly once with fixed op/code metadata;
        // expected states (missing-memory card, empty) stay quiet; no query
        // or exception text ever reaches the console.
        expect(seen.length).toBe(2);
        expect(String(seen[0][0])).toContain("op=retrieve");
        expect(String(seen[0][0])).toContain("code=PATH_NOT_FOUND");
        expect(String(seen[1][0])).toContain("op=search");
        expect(String(seen[1][0])).toContain("code=BACKEND_UNAVAILABLE");
        expect(JSON.stringify(seen)).not.toMatch(
          /metadata query|vector query|genuine failure|empty query|no db|down|rc1|Error/
        );
        for (const v of [meta, deep, genuine, empty]) v._host.remove();
      } finally {
        console.error = origErr;
      }
    });

    it("missing-memory and vector-settings CTAs navigate without dispatching actions", async () => {
      const openModuleSettings = vi.fn(() => true);
      const view = makeDashboard(client);
      view.app = {
        vault: { adapter: { basePath: "/vault" } },
        plugins: { plugins: { paperforge: { getClient: () => client, openModuleSettings } } },
      };
      view._searchState = "missing-memory-index";
      view._renderSearchState();
      view._host.remove();
      const missingBtn = [...view._searchResultsEl.querySelectorAll("button")].find((b) =>
        (b.textContent ?? "").length > 0,
      );
      missingBtn?.click();
      expect(openModuleSettings).toHaveBeenCalledWith("memory");
      expect(transport.calls).toHaveLength(0);

      const vectors = makeDashboard(client);
      vectors.app = view.app;
      vectors._searchState = "vectors-not-built";
      vectors._renderSearchState();
      vectors._host.remove();
      const vectorBtn = [...vectors._searchResultsEl.querySelectorAll("button")].find((b) =>
        (b.textContent ?? "").length > 0,
      );
      vectorBtn?.click();
      expect(openModuleSettings).toHaveBeenCalledWith("memory");
      expect(transport.calls).toHaveLength(0);
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
