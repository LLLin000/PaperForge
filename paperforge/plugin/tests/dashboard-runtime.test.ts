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

/** Mock health representing a ready runtime. */
function readyHealth(pythonPath: string) {
  return { state: "ready" as const, pythonPath };
}

/** Mock health for any non-ready state. */
const notReadyHealth = { state: "needs_repair" as const, pythonPath: null };

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

  it("returns null when the managed runtime is not ready", () => {
    const mockRuntime = { current: () => notReadyHealth };
    app.plugins.plugins["paperforge"] = {
      getManagedRuntime: () => mockRuntime,
    };
    const view = createView();
    (view as any).app = app;
    expect((view as any)._resolvePython()).toBeNull();
  });

  it("returns the singleton command when the managed runtime is ready", () => {
    const mockRuntime = {
      current: () => readyHealth("/opt/paperforge/venv/bin/python3"),
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
      current: () => readyHealth("/usr/bin/python3.11"),
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
