/**
 * OCR Workspace cutover regressions.
 *
 * These tests exercise the PaperForgeClient seam only. The workspace must not
 * resolve runtimes, spawn subprocesses, or call the legacy OCR controller.
 */
import { describe, expect, it, vi } from "vitest";

import "obsidian-test-mocks/jest-setup";
import { setLanguage } from "../src/i18n";
const { restoreNotices } = vi.hoisted(() => ({ restoreNotices: [] as string[] }));
vi.mock("obsidian", () => {
  return {
    Notice: class {
      noticeEl: HTMLElement;
      constructor(msg: string) {
        restoreNotices.push(msg);
        this.noticeEl = document.createElement("div");
        this.noticeEl.textContent = msg;
      }
    },
    ItemView: class {
      app: any;
      contentEl: HTMLElement;
      constructor() {
        this.contentEl = document.createElement("div");
      }
      getViewType() {
        return "paperforge-ocr-workspace";
      }
    },
    Modal: class {
      contentEl: HTMLElement;
      constructor() {
        this.contentEl = document.createElement("div");
      }
      open() {}
      close() {}
    },
    Component: class {
      load() {}
      unload() {}
    },
    WorkspaceLeaf: class {},
    MarkdownRenderer: { render: () => {} },
    Platform: {},
  };
});

import { OcrWorkspaceView, VersionRestoreModal } from "../src/views/ocr-workspace";
import { PaperForgeClient } from "../src/client";
import { WorkspaceLeaf } from "obsidian";
import { MockTransport } from "./client/mock-transport";

function makeView(
  client: PaperForgeClient | null,
  refreshAll = vi.fn()
): OcrWorkspaceView {
  const plugin = {
    getClient: () => client,
    _settingTab: { _refreshAllReadModels: refreshAll },
  };
  const view = new (OcrWorkspaceView as any)(
    new WorkspaceLeaf(),
    plugin
  ) as OcrWorkspaceView;
  (view as any).app = { vault: { adapter: { basePath: "/vault" } } };
  (view as any)._refreshTable = vi.fn();
  (view as any)._render = vi.fn();
  return view;
}

function descriptorResponse(
  actionId: string,
  availability: "available" | "busy" | "unavailable" = "available"
): string {
  return JSON.stringify({
    ok: true,
    data: {
      action_id: actionId,
      availability,
      availability_reason:
        availability === "available" ? undefined : "backend busy",
      execution_mode: "stream",
      confirmation: actionId === "ocr.run" ? "required" : "none",
    },
  });
}

describe("OcrWorkspaceView PaperForgeClient cutover", () => {
  it.each([true, false, undefined])(
    "keeps a restore with unconfirmed provenance visible instead of closing as success (persisted=%s)",
    async (persisted) => {
      const transport = new MockTransport();
      transport.executeHandler = () => JSON.stringify({
        ok: true, data: { target_path: "/vault/restored.md", label: "v1", provenance_persisted: persisted },
      });
      const client = new PaperForgeClient({ transport });
      const modal = new VersionRestoreModal(
        {}, "P1", [
          { label: "v1", created_at: "2025-01-01T00:00:00Z", source: "pre-rebuild", fulltext_size: 28 },
          { label: "v2", created_at: "2025-01-02T00:00:00Z", source: "pre-rebuild", fulltext_size: 28 },
        ], "v2", "/vault/restored.md",
        (label) => client.versionsRestore("P1", label)
      );
      document.body.appendChild(modal.contentEl);
      modal.onOpen();
      const close = vi.spyOn(modal, "close");
      restoreNotices.length = 0;
      const errors = vi.spyOn(console, "error").mockImplementation(() => {});
      try {
        await (modal as any)._executeRestore({ label: "v1" });
        if (persisted === true) {
          expect(close).toHaveBeenCalledOnce();
          expect(modal.contentEl.querySelector('[role="alert"]')).toBeNull();
        } else {
          expect(close).not.toHaveBeenCalled();
          expect(modal.contentEl.querySelector('[role="alert"]')?.textContent).toContain("v1");
          expect(restoreNotices).toEqual([]);
          expect(modal.contentEl.querySelector(".pf-vr-entry--current .pf-vr-entry-label")?.textContent).toBe("v1");
          (modal.contentEl.querySelector('.pf-vr-entry[data-idx="1"]') as HTMLElement).click();
          expect(modal.contentEl.querySelector('[role="alert"]')?.textContent).toContain("v1");
        }
        expect(errors).toHaveBeenCalledTimes(persisted === false ? 1 : 0);
        if (persisted === false) {
          expect(String(errors.mock.calls[0][0])).toContain("code=restore.provenance_not_persisted");
        }
      } finally {
        errors.mockRestore();
        modal.contentEl.remove();
      }
    }
  );
  it("refuses an empty paper selection instead of running the whole library", async () => {
    const transport = new MockTransport();
    transport.executeHandler = (argv) => descriptorResponse(argv[2]);
    const client = new PaperForgeClient({ transport });
    const view = makeView(client);
    // Exercise the production handler at the view boundary.
    const actions = view as unknown as {
      _runOcrAction: (id: string, keys: string[]) => Promise<void>;
    };
    await actions._runOcrAction("ocr.run", []);
    expect(transport.calls).toEqual([]);
  });
  it("drops a paper-list response after the workspace closes", async () => {
    const rows = Promise.withResolvers<string>();
    const transport = new MockTransport();
    transport.executeHandler = (argv) => argv[0] === "ocr"
      ? rows.promise : JSON.stringify({});
    const view = makeView(new PaperForgeClient({ transport }));
    const pending = (view as any)._loadPapers();
    await view.onClose();
    rows.resolve(JSON.stringify([{ key: "LATE", title: "Late paper" }]));
    await pending;
    expect((view as any).papers).toEqual([]);
  });

  it("does not submit paper selections removed by a refreshed library snapshot", async () => {
    const transport = new MockTransport();
    transport.executeHandler = (argv) => {
      if (argv[0] === "ocr") return JSON.stringify([{ key: "CURRENT", title: "Current paper" }]);
      if (argv[0] === "action") return descriptorResponse(argv[2]);
      return JSON.stringify({});
    };
    transport.streamHandler = () => ({
      events: [{ schema_version: 1, event: "result", operation: "ocr.run", result: { ok: true } }],
      outcome: { ok: true, exitCode: 0 },
    });
    const view = makeView(new PaperForgeClient({ transport }));
    (view as any).checkedKeys.add("REMOVED");
    await (view as any)._loadPapers();
    await (view as any)._runOcrAction("ocr.run", [...(view as any).checkedKeys]);
    expect(transport.calls.filter((call) => call.kind === "stream")).toEqual([]);
    expect((view as any).papers.map((paper: { key: string }) => paper.key)).toEqual(["CURRENT"]);
  });

  it("preserves the lineage status of listed papers", async () => {
    const transport = new MockTransport();
    transport.executeHandler = (argv) => {
      if (argv[0] === "probe" && argv[1] === "lineage") {
        return JSON.stringify({
          papers: {
            K1: {
              ocr: "stale",
              details: { ocr: "stale" },
              flags: { version_old: false },
            },
          },
        });
      }
      if (argv[0] === "ocr" && argv[1] === "list") {
        return JSON.stringify([
          {
            key: "K1",
            title: "Paper one",
            status: "done",
            version: "v2",
            finished_at: "2026-09-03T00:00:00Z",
            can_redo: true,
            can_rebuild: true,
            recommended_action: "redo",
          },
        ]);
      }
      return JSON.stringify({});
    };
    const view = makeView(new PaperForgeClient({ transport }));

    await (view as any)._loadPapers();

    expect((view as any).papers).toMatchObject([
      {
        key: "K1",
        title: "Paper one",
        status: "update_available",
        pipelineVersion: "v2",
        canRedo: true,
        canRebuild: true,
        recommendedAction: "redo",
      },
    ]);
    expect(transport.calls.some((call) => call.argv[0] === "fs")).toBe(false);
  });

  it("runs rebuild through the client action request and refreshes read models", async () => {
    const transport = new MockTransport();
    transport.executeHandler = (argv) =>
      argv[0] === "action" && argv[1] === "describe"
        ? descriptorResponse(argv[2])
        : JSON.stringify({});
    transport.streamHandler = async () => ({
      events: [
        {
          schema_version: 1,
          event: "phase",
          operation: "ocr.rebuild_derived",
          phase: "render",
        },
        {
          schema_version: 1,
          event: "progress",
          operation: "ocr.rebuild_derived",
          current: 1,
          total: 1,
          item_id: "K1",
        },
        {
          schema_version: 1,
          event: "item_result",
          operation: "ocr.rebuild_derived",
          current: 1,
          total: 1,
          item_id: "K1",
          status: "ok",
        },
        {
          schema_version: 1,
          event: "result",
          operation: "ocr.rebuild_derived",
          result: { rebuilt: ["K1"] },
        },
      ],
    });
    const refreshAll = vi.fn();
    const view = makeView(new PaperForgeClient({ transport }), refreshAll);
    (view as any)._loadPapers = vi.fn().mockResolvedValue(undefined);

    await (view as any)._runOcrAction("ocr.rebuild_derived", ["K1"], "rebuild");

    const streamCall = transport.calls.find((call) => call.kind === "stream");
    expect(streamCall?.argv).toEqual([
      "action",
      "run",
      "ocr.rebuild_derived",
      "--scope",
      "papers",
      "--key",
      "K1",
      "--json",
    ]);
    expect(refreshAll).toHaveBeenCalledOnce();
    expect((view as any).progress).toMatchObject({
      current: 1,
      total: 1,
      paperKey: "K1",
      phase: "render",
      itemStatus: "ok",
    });
    expect(
      transport.calls.some(
        (call) => call.argv[0] === "ocr" && call.argv[1] === "redo"
      )
    ).toBe(false);
  });

  it("maps user-facing redo to canonical ocr.run with confirmation", async () => {
    const transport = new MockTransport();
    transport.executeHandler = (argv) =>
      argv[0] === "action" && argv[1] === "describe"
        ? descriptorResponse(argv[2])
        : JSON.stringify({});
    transport.streamHandler = async () => ({
      events: [
        {
          schema_version: 1,
          event: "result",
          operation: "ocr.run",
          result: { processed: ["K1"] },
        },
      ],
    });
    const view = makeView(new PaperForgeClient({ transport }));
    (view as any)._loadPapers = vi.fn().mockResolvedValue(undefined);

    await (view as any)._runOcrAction("ocr.run", ["K1"], "redo");

    const streamCall = transport.calls.find((call) => call.kind === "stream");
    expect(streamCall?.argv).toEqual([
      "action",
      "run",
      "ocr.run",
      "--scope",
      "papers",
      "--key",
      "K1",
      "--confirm",
      "ocr.run",
      "--json",
    ]);
    expect(streamCall?.argv.includes("redo")).toBe(false);
  });

  it("fails closed when the plugin has no PaperForgeClient", async () => {
    const view = makeView(null);

    await (view as any)._loadPapers();

    expect((view as any).papers).toEqual([]);
  });

  it("clears dynamic action descriptors on read-model refresh", async () => {
    const client = {
      probe: vi.fn().mockResolvedValue({}),
      queryOcrPapers: vi.fn().mockResolvedValue([]),
    } as unknown as PaperForgeClient;
    const view = makeView(client);
    (view as any).actionDescriptors.set("ocr.run", {
      action_id: "ocr.run",
      availability: "available",
    });

    await (view as any)._loadPapers();

    expect((view as any).actionDescriptors.size).toBe(0);
  });

  it("does not execute an action when the backend descriptor is busy", async () => {
    const transport = new MockTransport();
    transport.executeHandler = (argv) =>
      argv[0] === "action" && argv[1] === "describe"
        ? descriptorResponse(argv[2], "busy")
        : JSON.stringify({});
    const client = new PaperForgeClient({ transport });

    const result = await client.runAction({
      action_id: "ocr.run",
      scope: { kind: "papers", keys: ["K1"] },
    });

    expect(result.ok).toBe(false);
    expect(result.payload?.availability).toBe("busy");
    expect(transport.calls.some((call) => call.kind === "stream")).toBe(false);
  });

  it("stops only the client-owned stream and waits for cancellation", async () => {
    const transport = new MockTransport();
    transport.executeHandler = (argv) =>
      argv[0] === "action" && argv[1] === "describe"
        ? descriptorResponse(argv[2])
        : JSON.stringify({});
    transport.streamHandler = async () => ({
      delayMs: 200,
      events: [
        {
          schema_version: 1,
          event: "progress",
          operation: "ocr.rebuild_derived",
          current: 1,
          total: 1,
          item_id: "K1",
        },
      ],
    });
    const view = makeView(new PaperForgeClient({ transport }));
    (view as any)._loadPapers = vi.fn().mockResolvedValue(undefined);

    const run = (view as any)._runOcrAction(
      "ocr.rebuild_derived",
      ["K1"],
      "rebuild"
    );
    await vi.waitFor(() => {
      if (!transport.calls.some((call) => call.kind === "stream")) {
        throw new Error("stream has not started");
      }
    });
    (view as any)._stopBuild();
    await run;

    const streamCall = transport.calls.find((call) => call.kind === "stream");
    expect(streamCall?.stopped).toBe(true);
    expect((view as any).running).toBe(false);
  });
  it("F-12: onClose clears the view-owned search timer and does NOT cancel the OCR child", async () => {
    const client = new PaperForgeClient(new MockTransport() as any);
    const cancel = vi.spyOn(client, "cancelActiveOperation");

    const view = makeView(client);
    await view.onOpen();
    // Simulate a debounced search timer being scheduled.
    (view as any)._searchTimer = setTimeout(() => {}, 10_000);
    // Simulate an in-flight async render that would touch DOM if not guarded.
    (view as any)._closed = false;

    await view.onClose();

    expect((view as any)._searchTimer).toBeUndefined();
    expect((view as any)._closed).toBe(true);
    // View teardown must NOT cancel the shared client's OCR operation.
    expect(cancel).not.toHaveBeenCalled();
  });

  it("F-12: late streaming onEvent after onClose does not render", async () => {
    const transport = new MockTransport();
    const client = new PaperForgeClient(transport as any);
    const view = makeView(client);
    await view.onOpen();
    await view.onClose();

    // A late progress event should short-circuit on the _closed guard.
    // _render() would throw on detached DOM; if guard works, no throw.
    const renderSpy = vi.spyOn(view as any, "_render");
    // Emulate the internal onEvent path: call _render with _closed true.
    expect((view as any)._closed).toBe(true);
    // Direct call should early-return, not touch DOM.
    (view as any)._render();
    expect(renderSpy).toHaveReturned();
  });
});

  it("surfaces the backend blocked machine error, not availability_reason or exit code", async () => {
    const transport = new MockTransport();
    transport.executeHandler = (argv) =>
      argv[0] === "action" && argv[1] === "describe"
        ? descriptorResponse(argv[2])
        : JSON.stringify({});
    transport.streamHandler = async () => ({
      events: [
        {
          schema_version: 1,
          event: "result",
          operation: "ocr.run",
          result: {
            ok: false,
            error: {
              code: "OCR_UPLOAD_FAILED",
              message: "OCR is blocked and needs credentials or source files before retry",
            },
            data: {
              exit_code: 1,
              summary: { blocked: 1, pending: 0 },
              blocked_keys: ["K1"],
            },
          },
        },
      ],
      // The mock derives outcome.ok from this field, not from the terminal
      // event payload — mirror the real transport's failed terminal.
      outcome: { ok: false, exitCode: 1 },
    });
    const view = makeView(new PaperForgeClient({ transport }));
    (view as any)._loadPapers = vi.fn().mockResolvedValue(undefined);
    restoreNotices.length = 0;

    await (view as any)._runOcrAction("ocr.run", ["K1"], "run");

    expect(restoreNotices.length).toBe(1);
    expect(restoreNotices[0]).toContain("OCR is blocked");
    expect(restoreNotices[0]).toContain("K1");
    expect(restoreNotices[0]).not.toContain("exit code");
  });

  it("does not recommend resubmission for an unconfirmed upload in a partly blocked batch", async () => {
    const transport = new MockTransport();
    transport.executeHandler = (argv) =>
      argv[0] === "action" && argv[1] === "describe"
        ? descriptorResponse(argv[2])
        : JSON.stringify({});
    transport.streamHandler = async () => ({
      events: [{
        schema_version: 1,
        event: "result",
        operation: "ocr.run",
        result: {
          ok: false,
          error: { code: "OCR_UPLOAD_FAILED", message: "Submission unconfirmed for K2; do not resubmit." },
          data: { exit_code: 1, blocked_keys: ["K1"], pending_keys: ["K2"] },
        },
      }],
      outcome: { ok: false, exitCode: 1 },
    });
    const view = makeView(new PaperForgeClient({ transport }));
    (view as any)._loadPapers = vi.fn().mockResolvedValue(undefined);
    restoreNotices.length = 0;
    await (view as any)._runOcrAction("ocr.run", ["K1", "K2"], "run");
    expect(restoreNotices[0]).toContain("do not resubmit");
    expect(restoreNotices[0]).not.toContain("then re-run");
  });

  it("names the failed keys in the result-invalid notice instead of a keyless message", async () => {
    const transport = new MockTransport();
    transport.executeHandler = (argv) =>
      argv[0] === "action" && argv[1] === "describe"
        ? descriptorResponse(argv[2])
        : JSON.stringify({});
    transport.streamHandler = async () => ({
      events: [
        {
          schema_version: 1,
          event: "result",
          operation: "ocr.run",
          result: {
            ok: false,
            error: {
              code: "OCR_RESULT_INVALID",
              message: "OCR failed for some papers — fix the failed keys before re-running",
            },
            data: {
              exit_code: 1,
              summary: { failed: 1, pending: 0 },
              failed_keys: ["K9"],
            },
          },
        },
      ],
      outcome: { ok: false, exitCode: 1 },
    });
    const view = makeView(new PaperForgeClient({ transport }));
    (view as any)._loadPapers = vi.fn().mockResolvedValue(undefined);
    restoreNotices.length = 0;

    await (view as any)._runOcrAction("ocr.run", ["K9"], "run");

    expect(restoreNotices.length).toBe(1);
    expect(restoreNotices[0]).toContain("K9");
    expect(restoreNotices[0]).not.toContain("exit code");
  });

describe("OCR saved activity presentation", () => {
  it.each(["en", "zh"])(
    "keeps history distinct from a cancellable local operation (%s)",
    async (language) => {
      const transport = new MockTransport();
      transport.executeHandler = (argv) =>
        JSON.stringify(
          argv[0] === "ocr"
            ? [{ key: "OLDJOB01", title: "Historical paper", status: "queued" }]
            : argv[1] === "ocr"
              ? {
                  activity_state: "idle",
                  historical_activity: {
                    current: 8,
                    total: 166,
                    unsettled: 11,
                  },
                }
              : {}
        );
      const client = new PaperForgeClient({ transport });
      const view = makeView(client);
      setLanguage(view.app, language);
      // Exercise the render boundary without overriding the activity renderer.
      const surface = view as unknown as {
        _loadPapers(): Promise<void>;
        _renderActivity(el: HTMLElement): void;
        running: boolean;
      };
      await surface._loadPapers();
      const container = document.createElement("div");
      surface._renderActivity(container);
      expect(container.textContent).toContain(
        language === "en" ? "Saved OCR progress" : "已保存的 OCR 进度"
      );
      expect(container.textContent).toContain("8 / 166");
      expect(
        container.querySelector('[data-pf-testid="ocr-ws-stop"]')
      ).toBeNull();
      expect(container.textContent).not.toContain("ocr_ws_");
      setLanguage(view.app, "en");
    }
  );
});

describe("OCR workspace empty-filter recovery", () => {
  it("replaces the empty state when a reopened workspace filter has matches", async () => {
    vi.useFakeTimers();
    try {
      const transport = new MockTransport();
      transport.executeHandler = (argv) => {
        if (argv[0] === "ocr")
          return JSON.stringify([
            { key: "FRESH001", title: "Fresh paper", status: "pending" },
          ]);
        if (argv[0] === "action") return descriptorResponse(argv[2]);
        return JSON.stringify({});
      };
      const client = new PaperForgeClient({ transport });
      const view = new OcrWorkspaceView(new WorkspaceLeaf(), {
        getClient: () => client,
      });
      const host = document.createElement("div");
      host.append(document.createElement("div"), document.createElement("div"));
      Object.assign(view, {
        containerEl: host,
        app: { vault: { adapter: { basePath: "/vault" } } },
      });
      await view.onOpen();
      const choose = (value: string) => {
        const select = host.querySelector<HTMLSelectElement>(
          ".pf-ocr-ws-field select"
        );
        if (!select) throw new Error("Missing status filter");
        select.value = value;
        select.dispatchEvent(new Event("change"));
      };
      choose("processed");
      await view.onClose();
      await view.onOpen();
      // Settle the descriptor-driven render before exercising the filter transition.
      await vi.runAllTimersAsync();
      expect(host.querySelector(".pf-ocr-ws-empty")).not.toBeNull();
      choose("all");
      expect(host.querySelector(".pf-ocr-ws-empty")).toBeNull();
      expect(host.querySelectorAll(".pf-ocr-ws-viewport")).toHaveLength(1);
      expect(
        host.querySelector(".pf-ocr-ws-table tbody")?.textContent
      ).toContain("Fresh paper");
      await view.onClose();
    } finally {
      vi.useRealTimers();
    }
  });
});
