/**
 * Vitest tests for PaperForgeStatusView._resolvePython() — Issue #81.
 *
 * Verifies the method uses the plugin singleton's ManagedRuntime and never
 * constructs its own or falls back to ambient `python`.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import "obsidian-test-mocks/jest-setup";
const runtimePointer = vi.hoisted(() => ({
  value: null as Record<string, string> | null,
}));
vi.mock("../src/services/managed-runtime", () => ({
  readRuntimePointer: () => runtimePointer.value,
  resolveRuntimeCommand: (pointer: { pythonPath?: string } | null) =>
    pointer?.pythonPath ? { command: pointer.pythonPath, args: [] } : null,
}));

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
      open() {
        document.body.append(this.contentEl);
        if ("onOpen" in this && typeof this.onOpen === "function")
          this.onOpen();
      }
      close() {
        this.contentEl.remove();
      }
    },
    MarkdownRenderer: { render: () => {} },
    App: class {},
    TFile: class {},
  };
});

import { PaperForgeStatusView } from "../src/views/dashboard";
import { ResearchRecordCaptureModal } from "../src/views/research-record";
import {
  VIEW_TYPE_PAPERFORGE,
  VIEW_TYPE_PAPERFORGE_PDF,
} from "../src/constants";
import { TFile } from "obsidian";
import { PaperForgeClient } from "../src/client/paperforge-client";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { resolve, join } from "node:path";

describe("PaperForgeStatusView runtime pointer resolution", () => {
  let leaf: any;
  let app: any;

  function createView(): PaperForgeStatusView {
    return new (PaperForgeStatusView as any)(leaf);
  }

  beforeEach(() => {
    leaf = {};
    app = { plugins: { plugins: {} } };
    runtimePointer.value = null;
  });

  it("returns null when Python has not published a runtime pointer", () => {
    const view = createView();
    (view as any).app = app;
    expect((view as any)._resolvePython()).toBeNull();
  });

  it("uses the Python-published pointer without consulting the plugin registry", () => {
    runtimePointer.value = {
      pythonPath: "/opt/paperforge/venv/bin/python3",
      environmentRoot: "/opt/paperforge/venv",
      paperforgeVersion: "1.3.0",
    };
    const view = createView();
    (view as any).app = app;

    expect((view as any)._resolvePython()).toEqual({
      path: "/opt/paperforge/venv/bin/python3",
      args: [],
    });
  });

  it("never falls back to ambient Python", () => {
    const view = createView();
    (view as any).app = app;
    const result = (view as any)._resolvePython();

    expect(result).toBeNull();
    expect(result).not.toEqual(expect.objectContaining({ path: "python" }));
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
  it.each(["paper", "collection"])(
    "preserves the visible %s scope",
    async (mode) => {
      const requestOcrRun = vi.fn();
      const view = new PaperForgeStatusView(
        {} as ConstructorParameters<typeof PaperForgeStatusView>[0]
      );
      Object.assign(view, {
        app: { plugins: { plugins: { paperforge: { requestOcrRun } } } },
      });
      view._currentMode = mode === "paper" ? "paper" : "collection";
      view._currentPaperKey = "SCOPE001";
      view._currentDomain = "Selected collection";
      view._cachedItems = [
        { zotero_key: "SCOPE001", domain: "Selected collection" },
        { zotero_key: "SCOPE002", domain: "Other collection" },
      ];
      await view._runAction(
        { id: "paperforge-ocr" },
        document.createElement("button")
      );
      expect(requestOcrRun).toHaveBeenCalledWith({
        kind: "papers",
        keys: ["SCOPE001"],
      });
    }
  );
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
      "PaperForge Core did not answer"
    );
    expect(view.containerEl.textContent).toContain("Open Setup");
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
      "PaperForge Core did not answer"
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
      "PaperForge Core did not answer"
    );
    await view.onClose();
  });

  it("shows Setup guidance when a refresh fails after a successful load", async () => {
    let fail = false;
    const dashboardStats = vi.fn(async () => {
      if (fail) throw new Error("backend down");
      return {
        stats: { papers: 1 },
        permissions: { can_sync: true },
        items: [{ zotero_key: "K1", title: "Paper One", domain: "cardio" }],
      };
    });
    const view = makeLifecycleView(
      {
        dashboardStats,
        backendVersion: vi.fn(async () => "1.5.15"),
        credentialAvailable: vi.fn(async () => false),
        resolvePaperContext: vi.fn(),
      },
      null
    );

    await view.onOpen();
    await vi.waitFor(() => expect(dashboardStats).toHaveBeenCalledOnce());
    fail = true;
    await view._invalidateIndex();
    await view._detectAndSwitch();

    expect(view._getCachedIndex()).toHaveLength(1);
    expect(view.containerEl.textContent).toContain("Open Setup");
    await view.onClose();
  });

  it("shows Setup guidance when a refresh fails in paper mode", async () => {
    let fail = false;
    const dashboardStats = vi.fn(async () => {
      if (fail) throw new Error("backend down");
      return {
        stats: { papers: 1 },
        permissions: { can_sync: true },
        items: [{ zotero_key: "K1", title: "Paper One", domain: "cardio" }],
      };
    });
    const view = makeLifecycleView(
      {
        dashboardStats,
        backendVersion: vi.fn(async () => "1.5.15"),
        credentialAvailable: vi.fn(async () => false),
        resolvePaperContext: vi.fn(async () => ({
          kind: "paper",
          zotero_key: "K1",
        })),
      },
      {
        path: "03_Resources/Literature/Cardio/K1/K1.md",
        extension: "md",
        basename: "K1",
      }
    );

    await view.onOpen();
    await vi.waitFor(() => {
      expect(dashboardStats).toHaveBeenCalledOnce();
      expect(view._currentMode).toBe("paper");
    });

    fail = true;
    await view._invalidateIndex();
    await view._detectAndSwitch();

    expect(view._currentMode).toBe("paper");
    expect(view.containerEl.textContent).toContain("Open Setup");
    await view.onClose();
  });
  it("versions-mode direct entry preserves Setup banner after backend acquisition fail", async () => {
    let fail = false;
    const dashboardStats = vi.fn(async () => {
      if (fail) throw new Error("backend down");
      return {
        stats: { papers: 0 },
        permissions: { can_sync: false },
        items: [],
      };
    });
    const versionsList = vi.fn(async () => [
      { key: "K1", title: "Paper One", versions: [], current_label: "" },
    ]);
    const view = makeLifecycleView(
      {
        dashboardStats,
        backendVersion: vi.fn(async () => "1.5.15"),
        credentialAvailable: vi.fn(async () => false),
        resolvePaperContext: vi.fn(),
        versionsList,
      },
      null
    );

    await view.onOpen();
    await vi.waitFor(() => expect(dashboardStats).toHaveBeenCalledOnce());
    // Flip backend unavailability via refresh path (same as #244).
    fail = true;
    await view._invalidateIndex();
    await view._detectAndSwitch();
    // Now in global mode with the Setup banner showing from the failed stats.
    // Direct versions entry must not clear it — the entry path bypasses
    // _switchMode(). The banner must persist because _backendUnavailable
    // was set by dashboardStats failure, not by versionsList failure.
    await view._switchToVersionMode("K1");

    expect(view._currentMode).toBe("versions");
    expect(view.containerEl.textContent).toContain("Open Setup");
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

  it("reports a completed failing Doctor diagnosis as issues, not success", async () => {
    const dashboardStats = vi.fn(async () => ({
      stats: { papers: 1 },
      permissions: { can_sync: true },
      items: [{ zotero_key: "K1", title: "Paper One", domain: "cardio" }],
    }));
    const doctor = vi.fn(async () => ({ ok: false }));
    const view = makeLifecycleView(
      {
        dashboardStats,
        backendVersion: vi.fn(async () => "1.5.15"),
        credentialAvailable: vi.fn(async () => false),
        doctor,
        resolvePaperContext: vi.fn(),
      },
      null
    );

    await view.onOpen();
    await vi.waitFor(() => expect(dashboardStats).toHaveBeenCalledOnce());
    await view._runAction(
      { id: "paperforge-doctor", okMsg: "Doctor complete" },
      document.createElement("div")
    );

    expect(doctor).toHaveBeenCalledOnce();
    const message = view.containerEl.querySelector(".paperforge-message");
    expect(message?.textContent).toContain("Doctor reported issues");
    expect(message?.classList.contains("msg-error")).toBe(true);
    const recovery = view.containerEl.querySelector(
      '[data-pf-testid="recovery-banner"]'
    );
    expect(recovery?.textContent).toContain("Doctor reported issues");
    await view.onClose();
  });

  it("keeps an active search across a same-mode leaf rerender", async () => {
    const query = "suture";
    const search = vi.fn(async (value: string) =>
      value === query
        ? [
            {
              title: "Suture Anchor",
              zotero_key: "K1",
              main_note_path: "Resources/K1.md",
            },
          ]
        : []
    );
    const readingRecords = vi.fn(async () => ({ matches: [] }));
    const dashboardStats = vi.fn(async () => ({
      stats: { papers: 1 },
      permissions: { can_sync: true },
      items: [{ zotero_key: "K1", title: "Suture Anchor", domain: "cardio" }],
    }));
    let activeFile: any = null;
    let activeLeafChanged: (() => void) | undefined;
    const view = makeLifecycleView(
      {
        dashboardStats,
        backendVersion: vi.fn(async () => "1.5.15"),
        credentialAvailable: vi.fn(async () => false),
        resolvePaperContext: vi.fn(async () => ({
          kind: "domain",
          domain: "cardio",
        })),
        search,
        readingRecords,
      },
      null
    );
    view.app.workspace.getActiveFile = () => activeFile;
    view.app.workspace.on = (event: string, handler: () => void) => {
      if (event === "active-leaf-change") activeLeafChanged = handler;
      return {};
    };
    view.app.workspace.off = vi.fn();
    view._bindCtrlEnterInput = vi.fn();

    await view.onOpen();
    await vi.waitFor(() => {
      expect(dashboardStats).toHaveBeenCalledOnce();
      expect(view._currentMode).toBe("global");
    });
    activeFile = { path: "Bases/Old.base", extension: "base" };
    if (!activeLeafChanged)
      throw new Error("active-leaf listener was not registered");
    activeLeafChanged();
    await vi.waitFor(() => {
      expect(
        view.containerEl.querySelector(".paperforge-search-input")
      ).not.toBeNull();
    });
    const input = view.containerEl.querySelector<HTMLInputElement>(
      ".paperforge-search-input"
    );
    if (!input) throw new Error("collection search input was not rendered");
    input.value = query;
    input.dispatchEvent(new Event("input", { bubbles: true }));

    activeFile = { path: "Bases/New.base", extension: "base" };
    activeLeafChanged();

    await vi.waitFor(() => {
      expect(
        view.containerEl.querySelector(".paperforge-search-results")
          ?.textContent
      ).toContain("Suture Anchor");
    });
    expect(
      view.containerEl.querySelector<HTMLInputElement>(
        ".paperforge-search-input"
      )?.value
    ).toBe(query);
    expect(search).toHaveBeenCalledWith(query);
    await view.onClose();
  });

  it("never steals '/' keystrokes from CodeMirror contenteditable editors outside Companion", async () => {
    const view = makeLifecycleView(
      {
        dashboardStats: vi.fn(async () => ({
          stats: { papers: 1 },
          permissions: { can_sync: true },
          items: [{ zotero_key: "K1", title: "Paper One", domain: "cardio" }],
        })),
        backendVersion: vi.fn(async () => "2.0.0rc6"),
        credentialAvailable: vi.fn(async () => false),
        resolvePaperContext: vi.fn(async () => ({
          kind: "paper",
          zotero_key: "K1",
          entry: null,
        })),
      },
      { path: "Resources/K1/K1.md", extension: "md" }
    );
    await view.onOpen();
    await vi.waitFor(() => {
      expect(
        view.containerEl.querySelector(".paperforge-search-input")
      ).not.toBeNull();
    });
    const focusSpy = vi.spyOn(view._searchInput!, "focus");

    const cmEditor = document.createElement("div");
    cmEditor.className = "cm-editor";
    const cmContent = document.createElement("div");
    cmContent.className = "cm-content";
    cmContent.setAttribute("contenteditable", "true");
    cmEditor.appendChild(cmContent);
    document.body.appendChild(cmEditor);

    const extEvent = new KeyboardEvent("keydown", {
      key: "/",
      bubbles: true,
      cancelable: true,
    });
    cmContent.dispatchEvent(extEvent);
    expect(extEvent.defaultPrevented).toBe(false);
    expect(focusSpy).not.toHaveBeenCalled();

    const innerEvent = new KeyboardEvent("keydown", {
      key: "/",
      bubbles: true,
      cancelable: true,
    });
    view.containerEl.dispatchEvent(innerEvent);
    expect(innerEvent.defaultPrevented).toBe(true);
    expect(focusSpy).toHaveBeenCalledOnce();

    cmEditor.remove();
    await view.onClose();
  });

  it("keeps Companion locked on PDF reader paperKey across PDF <-> Companion focus and reuses file resolution LRU cache", async () => {
    const dashboardStats = vi.fn(async () => ({
      stats: { papers: 1 },
      permissions: { can_sync: true },
      items: [{ zotero_key: "K1", title: "Paper One", domain: "cardio" }],
    }));
    const resolvePaperContext = vi.fn(async (p: string) =>
      p.includes("K1")
        ? { kind: "paper", zotero_key: "K1", entry: null }
        : { kind: "none" }
    );
    let activeFile: any = { path: "Resources/K1/K1.md", extension: "md" };
    let activeLeafChanged: ((leaf?: any) => void) | undefined;
    const view = makeLifecycleView(
      {
        dashboardStats,
        backendVersion: vi.fn(async () => "2.0.0rc6"),
        credentialAvailable: vi.fn(async () => false),
        resolvePaperContext,
      },
      activeFile
    );
    view.app.workspace.getActiveFile = () => activeFile;
    view.app.workspace.on = (event: string, handler: (leaf?: any) => void) => {
      if (event === "active-leaf-change") activeLeafChanged = handler;
      return {};
    };
    view.app.workspace.off = vi.fn();

    await view.onOpen();
    await vi.waitFor(() => {
      expect(view._currentMode).toBe("paper");
      expect(view._currentPaperKey).toBe("K1");
    });
    expect(resolvePaperContext).toHaveBeenCalledTimes(1);

    // Focusing built-in PaperForge PDF reader (even when getActiveFile() is null) keeps Paper Mode
    activeFile = null;
    const pdfLeaf = {
      view: {
        getViewType: () => VIEW_TYPE_PAPERFORGE_PDF,
        getState: () => ({ paperKey: "K1", page: 2 }),
      },
    };
    activeLeafChanged?.(pdfLeaf);
    await vi.waitFor(() => {
      expect(view._currentFilePath).toBe("pdf:K1");
    });
    expect(view._currentMode).toBe("paper");
    expect(view._currentPaperKey).toBe("K1");

    // Clicking inside Companion itself preserves current paper context
    const selfLeaf = {
      view: { getViewType: () => VIEW_TYPE_PAPERFORGE },
    };
    activeLeafChanged?.(selfLeaf);
    await new Promise((r) => setTimeout(r, 90));
    expect(view._currentMode).toBe("paper");
    expect(view._currentPaperKey).toBe("K1");

    // Switching back to the previously resolved file uses LRU cache (no extra resolvePaperContext call)
    activeFile = { path: "Resources/K1/K1.md", extension: "md" };
    activeLeafChanged?.({ view: { getViewType: () => "markdown" } });
    await vi.waitFor(() => {
      expect(view._currentFilePath).toBe("Resources/K1/K1.md");
    });
    expect(resolvePaperContext).toHaveBeenCalledTimes(1);

    await view.onClose();
  });
});

describe("PaperForgeStatusView note opening", () => {
  it("opens an externally created note without deleting or rewriting it", async () => {
    // The constructor only stores this leaf; host behavior is supplied below.
    const hostLeaf = {} as ConstructorParameters<
      typeof PaperForgeStatusView
    >[0];
    const view = new PaperForgeStatusView(hostLeaf);
    const notePath = "Resources/Literature/J01/J01.md";
    const file = Object.assign(Object.create(TFile.prototype), {
      path: notePath,
      extension: "md",
    });
    let indexed: TFile | null = null;
    const remove = vi.fn();
    const write = vi.fn();
    const leaf = { openFile: vi.fn(async () => undefined) };
    const host = {
      vault: {
        getAbstractFileByPath: () => indexed,
        adapter: {
          exists: async () => true,
          reconcileInternalFile: vi.fn(async () => {
            indexed = file;
          }),
          remove,
          write,
        },
      },
      workspace: {
        getMostRecentLeaf: () => leaf,
        getLeaf: () => leaf,
        revealLeaf: async () => undefined,
        setActiveLeaf: vi.fn(),
        openLinkText: vi.fn(),
      },
    };
    Object.assign(view, { app: host });
    await view._openSearchResult(notePath, false);
    expect(leaf.openFile).toHaveBeenCalledWith(file);
    expect(remove).not.toHaveBeenCalled();
    expect(write).not.toHaveBeenCalled();
  });

  it.each([false, true])(
    "reads the authoritative note on a cold cache miss (workspace=%s) without rewriting bytes",
    async (workspace) => {
      // The constructor only stores this leaf; the host behavior is supplied below.
      const leaf = {} as ConstructorParameters<typeof PaperForgeStatusView>[0];
      const view = new PaperForgeStatusView(leaf);
      const notePath = "Resources/Literature/J01/J01.md";
      const read = vi.fn(
        async () => "## 🔍 精读\n**一句话总览:** Existing note overview\n"
      );
      const remove = vi.fn();
      const write = vi.fn();
      Object.assign(view, {
        app: {
          vault: {
            getAbstractFileByPath: () => null,
            adapter: {
              exists: async (p: string) => p === notePath,
              read,
              remove,
              write,
            },
          },
        },
      });
      const container = document.createElement("div");
      view._renderPaperOverviewCard(
        container,
        workspace
          ? {
              note_path: "Resources/Literature/J01.md",
              main_note_path: notePath,
            }
          : { note_path: notePath }
      );
      await vi.waitFor(() =>
        expect(container.textContent).toContain("Existing note overview")
      );
      expect(container.textContent).not.toContain("笔记文件不存在");
      expect(read).toHaveBeenCalledWith(notePath);
      expect(remove).not.toHaveBeenCalled();
      expect(write).not.toHaveBeenCalled();
      const missing = document.createElement("div");
      view._renderPaperOverviewCard(missing, {
        note_path: "Resources/Literature/MISSING.md",
      });
      await vi.waitFor(() =>
        expect(missing.textContent).toContain("Note file does not exist")
      );
    }
  );

  it("does not create a truly missing note while opening a result", async () => {
    // The constructor only stores this leaf; host behavior is supplied below.
    const leaf = {} as ConstructorParameters<typeof PaperForgeStatusView>[0];
    const view = new PaperForgeStatusView(leaf);
    const openLinkText = vi.fn();
    Object.assign(view, {
      app: {
        vault: {
          getAbstractFileByPath: () => null,
          adapter: { exists: async () => false },
        },
        workspace: { openLinkText },
      },
    });
    vi.useFakeTimers();
    try {
      const opening = view._openSearchResult(
        "Resources/Literature/MISSING.md",
        false
      );
      await vi.advanceTimersByTimeAsync(5100);
      await opening;
      expect(openLinkText).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("living paper memory card & research record search", () => {
  it("hides manual capture form clutter in paper mode, renders Living Paper Memory facets, and supports record search/correction", async () => {
    const vault = mkdtempSync(join(tmpdir(), "pf-record-ui-"));
    const run = promisify(execFile);
    const python = process.env.PF_PYTHON || "python";
    const cwd = resolve("../..");
    const env = {
      ...process.env,
      PYTHON_KEYRING_BACKEND: "keyring.backends.fail.Keyring",
      PAPERFORGE_KEYRING_BACKEND: "keyring.backends.fail.Keyring",
    };
    try {
      await run(
        python,
        [
          "-c",
          [
            "from pathlib import Path",
            "import json, sys",
            "from paperforge.config import bootstrap_config",
            "from paperforge.services.memory_card_service import refine_memory_facet",
            "vault = Path(sys.argv[1])",
            "bootstrap_config(vault)",
            "(vault / 'Resources/Literature/Ortho/PAPER001 - Test').mkdir(parents=True, exist_ok=True)",
            "(vault / '.paperforge/indexes').mkdir(parents=True, exist_ok=True)",
            "(vault / '.paperforge/indexes/formal-library.json').write_text(json.dumps({'version': 1, 'items': [{'zotero_key': 'PAPER001', 'title': 'Unrelated title', 'paper_root': 'Resources/Literature/Ortho/PAPER001 - Test/'}]}), encoding='utf-8')",
            "refine_memory_facet(vault, 'PAPER001', facet='idea_logic', content='Uses 75 Hz PEMF to rescue chondrocyte osteogenesis via Ca2+ influx.')",
          ].join("; "),
          vault,
        ],
        { cwd, env }
      );
      const client = new PaperForgeClient({
        transport: {
          execute: async (argv) =>
            (
              await run(
                python,
                ["-m", "paperforge", "--vault", vault, ...argv],
                { cwd, env }
              )
            ).stdout,
          stream: () => {
            throw new Error("No remote/stream operations in record capture");
          },
        },
      });
      const view = new PaperForgeStatusView(
        {} as ConstructorParameters<typeof PaperForgeStatusView>[0]
      );
      Object.assign(view, {
        app: {
          plugins: { plugins: { paperforge: { getClient: () => client } } },
        },
      });
      view._contentEl = document.createElement("div");
      document.body.append(view._contentEl);
      view._currentPaperKey = "PAPER001";
      view._currentPaperEntry = { title: "Unrelated title" };
      view._renderPaperMode();

      // Phase 3: redundant manual record-entry form button is removed from Paper Mode UI
      expect(
        view._contentEl.querySelector('[data-pf-testid="save-research-record"]')
      ).toBeNull();

      // Phase 3: Living Paper Memory Card renders facets dynamically
      const memCard = view._contentEl.querySelector(
        '[data-pf-testid="living-memory-card"]'
      );
      expect(memCard).not.toBeNull();
      await vi.waitFor(
        () =>
          expect(memCard!.textContent).toContain(
            "Uses 75 Hz PEMF to rescue chondrocyte osteogenesis via Ca2+ influx."
          ),
        { timeout: 10000 }
      );

      // Preserve underlying capture modal + search correction history contract
      new ResearchRecordCaptureModal(
        (view as any).app,
        client,
        "PAPER001",
        "",
        () => {
          if (view._searchInput?.value.trim()) void view.executeSearch();
        }
      ).open();
      view._currentPaperKey = "OTHER001";
      const modal = document.querySelector<HTMLElement>(
        ".paperforge-record-modal"
      )!;
      const quote =
        modal.querySelector<HTMLTextAreaElement>('[name="excerpt"]')!;
      const usage = modal.querySelector<HTMLTextAreaElement>('[name="usage"]')!;
      quote.value = "An exact saved observation";
      usage.value = "non-title-bridge-marker";
      const sourcePath = modal.querySelector<HTMLInputElement>('[name="pdf"]')!;
      sourcePath.value = "https://example.invalid/private.pdf";
      modal.querySelector<HTMLInputElement>('[name="page"]')!.value = "2";
      modal.querySelector<HTMLButtonElement>('button[type="submit"]')!.click();
      await vi.waitFor(
        () => expect(modal.textContent).toContain("Operation failed"),
        { timeout: 10000 }
      );
      expect(quote.value).toBe("An exact saved observation");
      expect(quote.disabled).toBe(false);
      expect(modal.textContent).not.toMatch(/rln_\d{8}_/);
      sourcePath.value = "";
      modal.querySelector<HTMLButtonElement>('button[type="submit"]')!.click();
      await vi.waitFor(() => expect(modal.textContent).toMatch(/rln_\d{8}_/), {
        timeout: 10000,
      });
      expect(modal.textContent).toContain("unknown");
      expect(
        view._contentEl.querySelector(".paperforge-search-input")
      ).not.toBeNull();
      view._searchInput!.value = "non-title-bridge-marker";
      await view.executeSearch();
      const group = view._contentEl.querySelector(".paperforge-record-results");
      expect(group?.textContent).toContain("An exact saved observation");
      expect(group?.textContent).toContain("non-title-bridge-marker");
      expect(group?.textContent).toContain("PAPER001");
      expect(group?.textContent).not.toContain("OTHER001");
      modal.remove();
      group!.querySelector<HTMLButtonElement>("button")!.click();
      const detail = document.querySelector<HTMLElement>(
        ".paperforge-record-modal"
      )!;
      detail.querySelector<HTMLTextAreaElement>('[name="correction"]')!.value =
        "Rechecked: do not use the earlier interpretation";
      detail.querySelector<HTMLInputElement>('[name="reason"]')!.value =
        "Source review";
      detail.querySelector<HTMLButtonElement>('button[type="submit"]')!.click();
      await vi.waitFor(
        () => expect(group!.textContent).toContain("No matching records"),
        { timeout: 10000 }
      );
      const history = view._contentEl.querySelector<HTMLInputElement>(
        '.paperforge-record-search input[type="checkbox"]'
      )!;
      history.checked = true;
      history.dispatchEvent(new Event("change"));
      await vi.waitFor(
        () =>
          expect(group!.textContent).toContain(
            "historical, not active evidence"
          ),
        { timeout: 10000 }
      );
      expect(detail.textContent).toContain("Source review");
      expect(detail.textContent).toContain("Rechecked: do not use");
    } finally {
      document.body.innerHTML = "";
      rmSync(vault, { recursive: true, force: true });
    }
  }, 30000);
});
