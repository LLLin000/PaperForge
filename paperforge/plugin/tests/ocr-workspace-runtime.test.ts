/**
 * OCR Workspace cutover regressions.
 *
 * These tests exercise the PaperForgeClient seam only. The workspace must not
 * resolve runtimes, spawn subprocesses, or call the legacy OCR controller.
 */
import { describe, expect, it, vi } from "vitest";

vi.mock("obsidian", () => {
  return {
    Notice: class {
      noticeEl: HTMLElement;
      constructor(msg: string) {
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
    WorkspaceLeaf: class {},
    MarkdownRenderer: { render: () => {} },
    Platform: {},
  };
});

import { OcrWorkspaceView } from "../src/views/ocr-workspace";
import { PaperForgeClient } from "../src/client";
import { WorkspaceLeaf } from "obsidian";
import { MockTransport } from "./client/mock-transport";

function makeView(
  client: PaperForgeClient,
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
  it("loads paper rows and global activity from client probes", async () => {
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
      if (argv[0] === "probe" && argv[1] === "ocr") {
        return JSON.stringify({
          activity_state: "running",
          activity_label: "OCR processing",
          activity_progress: { current: 1, total: 2 },
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
    expect((view as any).globalActivity).toMatchObject({
      state: "running",
      current: 1,
      total: 2,
    });
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
          status: "render",
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
});
