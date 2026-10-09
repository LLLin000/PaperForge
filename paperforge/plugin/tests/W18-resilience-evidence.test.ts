/**
 * W18 resilience evidence — X09 soak (view lifecycle) and J03 stop→restart.
 * Scoped to the P0-A support contract (Windows 11 x64 desktop).
 *
 * Complements the existing F-12 onClose regressions in ocr-workspace-runtime.test.ts.
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

function makeView(
  client: PaperForgeClient | null,
  refreshAll = vi.fn(),
  stubRender = true
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
  if (stubRender) (view as any)._render = vi.fn();
  return view;
}

describe("W18/X09: OcrWorkspaceView lifecycle soak", () => {
  it("survives 10× close cycles without leaving a live search timer", async () => {
    const transport = new MockTransport();
    transport.executeHandler = () => JSON.stringify({});
    const client = new PaperForgeClient({ transport });
    const view = makeView(client);

    for (let i = 0; i < 10; i++) {
      (view as any)._closed = false;
      (view as any)._searchTimer = setTimeout(() => {
        throw new Error("search timer fired after view close");
      }, 50);
      await view.onClose();
      expect((view as any)._searchTimer).toBeUndefined();
      expect((view as any)._closed).toBe(true);
    }
  });

  it("does not cancel the shared client's OCR operation across repeated lifecycles", async () => {
    const client = new PaperForgeClient({ transport: new MockTransport() });
    const cancel = vi.spyOn(client, "cancelActiveOperation");
    const view = makeView(client);
    (view as any)._loadPapers = vi.fn().mockResolvedValue(undefined);

    for (let i = 0; i < 3; i++) {
      await view.onOpen();
      await view.onClose();
    }
    expect(cancel).not.toHaveBeenCalled();
  });

  it("drops late renders after the final close (guard early-returns before touching DOM)", async () => {
    const client = new PaperForgeClient({ transport: new MockTransport() });
    // Real _render (not stubbed): its guard returns before reading
    // containerEl.children[1], so with NO container it must not throw.
    const view = makeView(client, vi.fn(), false);
    await view.onOpen().catch(() => undefined);
    await view.onClose();

    expect((view as any)._closed).toBe(true);
    expect(() => (view as any)._render()).not.toThrow();
  });
});

describe("W18/J03: OCR stop→restart recovery", () => {
  it("after a cancelled build, a restarted build opens a fresh stream with reset state", async () => {
    const transport = new MockTransport();
    transport.executeHandler = (argv) =>
      argv[0] === "action" && argv[1] === "describe"
        ? descriptorResponse(argv[2])
        : JSON.stringify({});
    transport.streamHandler = async () => ({
      delayMs: 100,
      events: [
        {
          schema_version: 1,
          event: "progress",
          operation: "ocr.rebuild_derived",
          current: 1,
          total: 2,
          item_id: "K1",
        },
      ],
    });
    const client = new PaperForgeClient({ transport });
    const view = makeView(client);
    (view as any)._loadPapers = vi.fn().mockResolvedValue(undefined);

    // 1) Start, then stop mid-flight.
    const run1 = (view as any)._runOcrAction(
      "ocr.rebuild_derived",
      ["K1"],
      "rebuild"
    );
    await vi.waitFor(() => {
      if (!transport.calls.some((call) => call.kind === "stream")) {
        throw new Error("first stream has not started");
      }
    });
    (view as any)._stopBuild();
    await run1;

    const firstStream = transport.calls.filter((c) => c.kind === "stream")[0];
    expect(firstStream?.stopped).toBe(true);
    expect((view as any).running).toBe(false);

    // 2) Restart: must open a NEW stream (fresh request), not resume/throw.
    const run2 = (view as any)._runOcrAction(
      "ocr.rebuild_derived",
      ["K1"],
      "rebuild"
    );
    await vi.waitFor(() => {
      if (transport.calls.filter((c) => c.kind === "stream").length < 2) {
        throw new Error("second stream has not started");
      }
    });
    await run2;

    const streams = transport.calls.filter((c) => c.kind === "stream");
    expect(streams.length).toBe(2);
    expect((view as any).running).toBe(false);
  });
});

