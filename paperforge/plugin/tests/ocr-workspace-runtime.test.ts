/**
 * RC UX Seam Pass P0: OCR Workspace `_resolvePython()` must resolve through
 * the managed-runtime POINTER (readPointer) — the #174 RuntimeBootstrap has
 * no current() — and must return null for installed-but-unpublished runtimes
 * exactly like the Status view. No custom python_path, pointer-only case.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";

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
import { WorkspaceLeaf } from "obsidian";
import { runAction } from "../src/services/python-bridge";

vi.mock("../src/services/python-bridge", () => ({
  runAction: vi.fn(),
  resolvePythonExecutable: () => ({ path: "/usr/bin/python3", extraArgs: [] }),
}));

function readyPointer(pythonPath: string) {
  return {
    pythonPath,
    environmentRoot: "/env",
    paperforgeVersion: "1.3.0",
  };
}

function makeView(plugin: any): OcrWorkspaceView {
  const leaf = new WorkspaceLeaf();
  const view = new (OcrWorkspaceView as any)(leaf, plugin);
  return view as OcrWorkspaceView;
}

describe("OcrWorkspaceView._resolvePython (RC UX Seam P0)", () => {
  let app: any;

  beforeEach(() => {
    app = { plugins: { plugins: {} } };
  });

  it("returns null when no paperforge plugin is registered", () => {
    const view = makeView(null);
    (view as any).app = app;
    expect((view as any)._resolvePython()).toBeNull();
  });

  it("returns null when no pointer is published (installed-but-unpublished NOT usable)", () => {
    app.plugins.plugins["paperforge"] = {
      getManagedRuntime: () => ({ readPointer: () => null }),
    };
    const view = makeView(app.plugins.plugins["paperforge"]);
    (view as any).app = app;
    expect((view as any)._resolvePython()).toBeNull();
  });

  it("pointer-only: resolves the singleton command through readPointer (no custom python_path)", () => {
    app.plugins.plugins["paperforge"] = {
      settings: { python_path: "" },
      getManagedRuntime: () => ({
        readPointer: () => readyPointer("/opt/paperforge/venv/bin/python3"),
      }),
    };
    const view = makeView(app.plugins.plugins["paperforge"]);
    (view as any).app = app;
    expect((view as any)._resolvePython()).toEqual({
      path: "/opt/paperforge/venv/bin/python3",
      args: [],
    });
  });

  it("prefers custom python_path when set (explicit user override wins)", () => {
    const fsMock = vi.spyOn(require("fs"), "existsSync");
    fsMock.mockReturnValue(true);
    try {
      app.plugins.plugins["paperforge"] = {
        settings: { python_path: "C:/custom/python.exe" },
        getManagedRuntime: () => ({
          readPointer: () => readyPointer("/opt/paperforge/venv/bin/python3"),
        }),
      };
      const view = makeView(app.plugins.plugins["paperforge"]);
      (view as any).app = app;
      const result = (view as any)._resolvePython();
      expect(result?.path).toBe("C:/custom/python.exe");
    } finally {
      fsMock.mockRestore();
    }
  });

  it("does NOT fall back to ambient 'python' when runtime is missing", () => {
    app.plugins.plugins["paperforge"] = {};
    const view = makeView(app.plugins.plugins["paperforge"]);
    (view as any).app = app;
    expect((view as any)._resolvePython()).toBeNull();
  });
});

// ═══════════════ RC UX Seam: settled rebuild refreshes the read model ═════
describe("OcrWorkspaceView rebuild settle (RC UX Seam P1)", () => {
  it("invalidates + probes all read models after a settled rebuild", async () => {
    const refreshes: string[] = [];
    const plugin = {
      _settingTab: {
        _refreshAllReadModels: () => {
          refreshes.push("all");
        },
      },
      ocrProcessController: { stop: vi.fn() },
    };
    const view = makeView(plugin);
    (view as any).app = { vault: { adapter: { basePath: "/vault" } } };
    (view as any)._resolvePython = () => ({
      path: "/usr/bin/python3",
      args: [],
    });
    (view as any)._loadPapers = () => Promise.resolve();
    (view as any)._render = () => {};
    (runAction as any).mockResolvedValue({
      ok: true,
      payload: {
        data: { rebuilt: ["K1"], failed: [] },
        next_actions: [],
      },
    });
    (view as any)._runRebuild(["K1"]);
    await Promise.resolve();
    await Promise.resolve();
    expect(refreshes).toContain("all");
    expect((runAction as any).mock.calls[0][3]).toBe("ocr.rebuild_derived");
  });

  it("a rebuild that leaves embed.resume pending still refreshes (durable handoff)", async () => {
    const refreshes: string[] = [];
    const plugin = {
      _settingTab: {
        _refreshAllReadModels: () => {
          refreshes.push("all");
        },
      },
      ocrProcessController: { stop: vi.fn() },
    };
    const view = makeView(plugin);
    (view as any).app = { vault: { adapter: { basePath: "/vault" } } };
    (view as any)._resolvePython = () => ({
      path: "/usr/bin/python3",
      args: [],
    });
    (view as any)._loadPapers = () => Promise.resolve();
    (view as any)._render = () => {};
    (runAction as any).mockResolvedValue({
      ok: true,
      payload: {
        data: { rebuilt: ["K1"], failed: [] },
        next_actions: [{ action_id: "embed.resume", reason: "stale" }],
      },
    });
    (view as any)._runRebuild(["K1"]);
    await Promise.resolve();
    await Promise.resolve();
    // The read model refresh is what makes the Smart Retrieval card show the
    // pending embed CTA durably — the 8s Notice alone is not the handoff.
    expect(refreshes).toContain("all");
  });
});
