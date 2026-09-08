/**
 * Vitest tests for PaperForgeStatusView._resolvePython() — Issue #81.
 *
 * Verifies the method uses the plugin singleton's ManagedRuntime and never
 * constructs its own or falls back to ambient `python`.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import "obsidian-test-mocks/jest-setup";

// Mock obsidian — minimal stubs needed to construct PaperForgeStatusView
vi.mock("obsidian", () => {
  class MockComponent {
    register() {}
    registerEvent() {}
    registerDomEvent() {}
    registerInterval() {
      return 0;
    }
    load() {}
    unload() {}
  }
  class MockView extends MockComponent {
    app: any;
    contentEl: HTMLElement;
    constructor(leaf: any) {
      super();
      this.contentEl = document.createElement("div");
    }
  }
  return {
    ItemView: MockView,
    WorkspaceLeaf: class {},
    View: MockView,
    Component: MockComponent,
    Notice: class {
      noticeEl: HTMLElement;
      constructor(msg: string) {
        this.noticeEl = document.createElement("div");
        this.noticeEl.textContent = msg;
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
    MarkdownRenderer: { render: () => {} },
    App: class {},
    TFile: class {},
  };
});

import { PaperForgeStatusView } from "../src/views/dashboard";

/** Mock pointer representing a published runtime (schema v1). */
function readyPointer(pythonPath: string) {
  return {
    pythonPath,
    environmentRoot: "/env",
    paperforgeVersion: "1.3.0",
  };
}

describe("PaperForgeStatusView._resolvePython", () => {
  let leaf: any;
  let app: any;

  function createView(): PaperForgeStatusView {
    return new (PaperForgeStatusView as any)(leaf);
  }

  beforeEach(() => {
    leaf = {};
    app = { plugins: { plugins: {} } };
  });

  it("returns null when no paperforge plugin is registered", () => {
    const view = createView();
    (view as any).app = app;
    expect((view as any)._resolvePython()).toBeNull();
  });

  it("returns null when the registered plugin has no getManagedRuntime", () => {
    app.plugins.plugins["paperforge"] = {};
    const view = createView();
    (view as any).app = app;
    expect((view as any)._resolvePython()).toBeNull();
  });

  it("returns null when no pointer is published (installed-but-unpublished is NOT usable)", () => {
    const mockRuntime = { readPointer: () => null };
    app.plugins.plugins["paperforge"] = {
      getManagedRuntime: () => mockRuntime,
    };
    const view = createView();
    (view as any).app = app;
    expect((view as any)._resolvePython()).toBeNull();
  });

  it("returns the singleton command when a pointer is published", () => {
    const mockRuntime = {
      readPointer: () => readyPointer("/opt/paperforge/venv/bin/python3"),
    };
    app.plugins.plugins["paperforge"] = {
      getManagedRuntime: () => mockRuntime,
    };
    const view = createView();
    (view as any).app = app;
    const result = (view as any)._resolvePython();
    expect(result).toEqual({
      path: "/opt/paperforge/venv/bin/python3",
      args: [],
    });
  });

  it("does NOT fall back to ambient 'python' when runtime is missing", () => {
    // If there is no plugin with getManagedRuntime, result must be null
    // rather than { path: "python", args: [] }
    app.plugins.plugins["paperforge"] = {};
    const view = createView();
    (view as any).app = app;
    const result = (view as any)._resolvePython();
    expect(result).toBeNull();
    // Specifically assert NOT { path: "python" }
    expect(result).not.toEqual(expect.objectContaining({ path: "python" }));
  });

  it("passes args from the runtime command when present", () => {
    // resolveRuntimeCommand always returns args: [] currently,
    // but test the contract so it survives future changes
    const mockRuntime = {
      readPointer: () => readyPointer("/usr/bin/python3.11"),
    };
    app.plugins.plugins["paperforge"] = {
      getManagedRuntime: () => mockRuntime,
    };
    const view = createView();
    (view as any).app = app;
    const result = (view as any)._resolvePython();
    expect(result).toHaveProperty("path", "/usr/bin/python3.11");
    expect(result).toHaveProperty("args");
    expect(Array.isArray(result!.args)).toBe(true);
  });
});

describe("PaperForgeStatusView OCR dispatch", () => {
  it("routes dashboard OCR through the plugin's shared dispatcher", async () => {
    const requestOcrRun = vi.fn();
    const view = new (PaperForgeStatusView as any)({});
    (view as any).app = {
      plugins: { plugins: { paperforge: { requestOcrRun } } },
    };

    await (view as any)._runAction(
      { id: "paperforge-ocr", commandId: "ocr" },
      document.createElement("button")
    );

    expect(requestOcrRun).toHaveBeenCalledOnce();
  });
});

describe("PaperForgeStatusView.onOpen production lifecycle (Step 5 wiring corrective)", () => {
  function polyfillDom() {
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
      function (
        this: HTMLElement,
        tag: string,
        opts?: Record<string, unknown>
      ) {
        const el = document.createElement(tag);
        if (opts?.cls) el.className = String(opts.cls);
        if (opts?.text) el.textContent = String(opts.text);
        if (opts?.attr) {
          for (const [k, v] of Object.entries(
            opts.attr as Record<string, string>
          ))
            el.setAttribute(k, String(v));
        }
        this.appendChild(el);
        return el;
      }
    );
    polyfill(
      "createSpan",
      function (this: HTMLElement, opts?: Record<string, unknown>) {
        const el = document.createElement("span");
        if (opts?.cls) el.className = String(opts.cls);
        if (opts?.text) el.textContent = String(opts.text);
        this.appendChild(el);
        return el;
      }
    );
  }

  function makeLifecycleView(client: Record<string, unknown>, activeFile: any) {
    polyfillDom();
    const view = new (PaperForgeStatusView as any)({});
    (view as any).containerEl = document.createElement("div");
    (view as any).app = {
      workspace: {
        on: () => ({}),
        off: () => undefined,
        getActiveFile: () => activeFile,
      },
      vault: { adapter: { basePath: "C:/vault" } },
      plugins: {
        plugins: { paperforge: { getClient: () => client, settings: {} } },
      },
    };
    (view as any)._getClient = () => client;
    return view;
  }

  it("cold open with an active paper: loads the read model FIRST, then resolves and renders the entry", async () => {
    const dashboardStats = vi.fn(async () => ({
      stats: { papers: 1 },
      permissions: { can_sync: true },
      items: [{ zotero_key: "K1", title: "Paper One", domain: "cardio" }],
    }));
    const resolvePaperContext = vi.fn(async () => ({
      kind: "paper",
      zotero_key: "K1",
      entry: null,
    }));
    const backendVersion = vi.fn(async () => "1.5.15");
    const view = makeLifecycleView(
      { dashboardStats, resolvePaperContext, backendVersion },
      {
        path: "03_Resources/Literature/Cardio/ABCD1234/ABCD1234.md",
        extension: "md",
        basename: "ABCD1234",
      }
    );

    await view.onOpen();
    // onOpen fires bootstrap without awaiting it — drain the chain
    await vi.waitFor(() => {
      expect(dashboardStats).toHaveBeenCalledOnce();
      expect(view._currentPaperEntry && view._currentPaperEntry.title).toBe(
        "Paper One"
      );
    });

    // read model actually loaded into the cache
    expect(view._getCachedIndex()).toEqual([
      { zotero_key: "K1", title: "Paper One", domain: "cardio" },
    ]);
    expect(view._dashboardPermissions).toEqual({ can_sync: true });
    // mode header shows the entry title, never "Not found in index"
    expect(view.containerEl.textContent).not.toContain("Not found in index");
    expect(view.containerEl.textContent).toContain("Paper One");
    await view.onClose();
  });

  it("cold open with no active file: global mode renders from the loaded read model (no empty-index, export health from can_sync)", async () => {
    const dashboardStats = vi.fn(async () => ({
      stats: { papers: 3 },
      permissions: { can_sync: true },
      items: [
        { zotero_key: "K1", title: "Paper One", domain: "cardio" },
        { zotero_key: "K2", title: "Paper Two", domain: "derm" },
      ],
    }));
    const resolvePaperContext = vi.fn();
    const credentialAvailable = vi.fn(async () => false);
    const backendVersion = vi.fn(async () => "1.5.15");
    const view = makeLifecycleView(
      {
        dashboardStats,
        resolvePaperContext,
        backendVersion,
        credentialAvailable,
      },
      null
    );

    await view.onOpen();
    await vi.waitFor(() => {
      expect(dashboardStats).toHaveBeenCalledOnce();
      expect(view._currentMode).toBe("global");
    });
    expect(resolvePaperContext).not.toHaveBeenCalled();
    expect(view._getCachedIndex()).toHaveLength(2);
    expect(view._dashboardPermissions).toEqual({ can_sync: true });
    // can_sync=true must never render as export missing
    expect(view.containerEl.textContent).not.toContain("No exports found");
    expect(view.containerEl.textContent).toContain("Exports detected");
    await view.onClose();
  });

  it("backend failure on cold open: fail-closed message, no invented items", async () => {
    const dashboardStats = vi.fn(async () => {
      throw new Error("backend down");
    });
    const backendVersion = vi.fn(async () => "1.5.15");
    const view = makeLifecycleView(
      {
        dashboardStats,
        backendVersion,
        resolvePaperContext: vi.fn(),
        credentialAvailable: vi.fn(async () => false),
      },
      null
    );

    await view.onOpen();
    await vi.waitFor(() => {
      expect(dashboardStats).toHaveBeenCalledOnce();
    });
    expect(view._getCachedIndex()).toEqual([]);
    expect(view._cachedStats).toBeNull();
    expect(view.containerEl.textContent).toContain(
      "Cannot reach PaperForge CLI"
    );
    await view.onClose();
  });

  it("RECOVERY: a failed initial load is not sticky — quiet Refresh re-acquires and clears the stale failure message", async () => {
    let fail = true;
    const dashboardStats = vi.fn(async () => {
      if (fail) throw new Error("backend down");
      return {
        stats: { papers: 1 },
        permissions: { can_sync: true },
        items: [{ zotero_key: "K1", title: "Paper One", domain: "cardio" }],
      };
    });
    const credentialAvailable = vi.fn(async () => false);
    const backendVersion = vi.fn(async () => "1.5.15");
    const view = makeLifecycleView(
      {
        dashboardStats,
        backendVersion,
        credentialAvailable,
        resolvePaperContext: vi.fn(),
      },
      null
    );

    await view.onOpen();
    await vi.waitFor(() => {
      expect(dashboardStats).toHaveBeenCalledOnce();
    });
    expect(view._cachedStats).toBeNull();
    expect(view.containerEl.textContent).toContain(
      "Cannot reach PaperForge CLI"
    );

    // backend recovers; the top Refresh button is the natural recovery action
    fail = false;
    await view._invalidateIndex();
    await view._detectAndSwitch();

    // the quiet path RE-ACQUIRED instead of no-op'ing on the null cache
    expect(dashboardStats).toHaveBeenCalledTimes(2);
    expect(view._cachedStats).not.toBeNull();
    expect(view._getCachedIndex()).toHaveLength(1);
    expect(view._dashboardPermissions).toEqual({ can_sync: true });
    // the stale failure message no longer hangs in the message bar
    expect(view.containerEl.textContent).not.toContain(
      "Cannot reach PaperForge CLI"
    );
    await view.onClose();
  });

  it("RECOVERY: Doctor success re-acquires the read model and re-renders the current mode from the fresh payload", async () => {
    let loaded = false;
    const dashboardStats = vi.fn(async () => {
      if (!loaded) throw new Error("backend down");
      return {
        stats: { papers: 1 },
        permissions: { can_sync: true },
        items: [{ zotero_key: "K1", title: "Paper One", domain: "cardio" }],
      };
    });
    const credentialAvailable = vi.fn(async () => false);
    const backendVersion = vi.fn(async () => "1.5.15");
    const doctor = vi.fn(async () => undefined);
    const view = makeLifecycleView(
      {
        dashboardStats,
        backendVersion,
        credentialAvailable,
        doctor,
        resolvePaperContext: vi.fn(),
      },
      null
    );

    await view.onOpen();
    await vi.waitFor(() => {
      expect(dashboardStats).toHaveBeenCalledOnce();
    });
    expect(view._getCachedIndex()).toEqual([]);

    // user fixes the runtime, then runs Doctor
    loaded = true;
    const card = document.createElement("div");
    await view._runAction(
      { id: "paperforge-doctor", okMsg: "Doctor complete" },
      card
    );

    expect(doctor).toHaveBeenCalledOnce();
    // fresh acquisition AFTER the initial failure (the old quiet guard
    // would have skipped it) and the mode re-rendered from the payload
    expect(dashboardStats).toHaveBeenCalledTimes(2);
    expect(view._getCachedIndex()).toHaveLength(1);
    // the current (global) mode re-rendered from the FRESH payload:
    // counts and permissions come from the recovered acquisition
    expect(view.containerEl.textContent).toContain("1 papers");
    expect(view.containerEl.textContent).toContain("Exports detected");
    await view.onClose();
  });
});
