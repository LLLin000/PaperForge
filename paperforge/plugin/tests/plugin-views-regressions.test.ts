import { describe, expect, it, vi, beforeEach } from "vitest";
import "obsidian-test-mocks/jest-setup";
import * as fs from "node:fs";
import * as path from "node:path";

const { recordedNotices } = vi.hoisted(() => ({
  recordedNotices: [] as string[],
}));

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
    containerEl: HTMLElement;
    constructor(_leaf?: any) {
      super();
      this.contentEl = document.createElement("div");
      this.containerEl = document.createElement("div");
      this.containerEl.append(
        document.createElement("div"),
        document.createElement("div")
      );
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
        recordedNotices.push(msg);
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
    TFile: class {
      path: string;
      constructor(p: string) {
        this.path = p;
      }
    },
    Platform: {},
  };
});

import { PaperForgeStatusView } from "../src/views/dashboard";
import { VIEW_TYPE_PAPERFORGE } from "../src/constants";
import { OcrWorkspaceView } from "../src/views/ocr-workspace";
import { renderDomainModePreview } from "../src/views/domain-preview";
import { PaperForgeClient } from "../src/client";
import { MockTransport } from "./client/mock-transport";
import { setLanguage } from "../src/i18n";

describe("Plugin views qualification regressions", () => {
  beforeEach(() => {
    recordedNotices.length = 0;
    document.body.innerHTML = "";
  });

  it("PF-UI-003: unsubscribes layout-change and all workspace/vault listeners across repeated open/close cycles", async () => {
    const activeWorkspaceRefs = new Map<symbol, string>();
    const activeVaultRefs = new Map<symbol, string>();

    const workspace = {
      on: vi.fn((ev: string, _cb: unknown) => {
        const ref = Symbol(ev);
        activeWorkspaceRefs.set(ref, ev);
        return ref;
      }),
      offref: vi.fn((ref: symbol) => {
        activeWorkspaceRefs.delete(ref);
      }),
      getActiveFile: () => null,
      getActiveViewOfType: () => null,
    };
    const vault = {
      on: vi.fn((ev: string, _cb: unknown) => {
        const ref = Symbol(ev);
        activeVaultRefs.set(ref, ev);
        return ref;
      }),
      offref: vi.fn((ref: symbol) => {
        activeVaultRefs.delete(ref);
      }),
      adapter: { basePath: "" },
    };

    for (let i = 0; i < 10; i += 1) {
      const view = new PaperForgeStatusView({} as any);
      (view as any).app = {
        workspace,
        vault,
        plugins: { plugins: {} },
      };
      (view as any)._fetchVersion = vi.fn();
      (view as any)._bootstrapDashboard = vi.fn().mockResolvedValue(undefined);
      await view.onOpen();
      expect(
        Array.from(activeWorkspaceRefs.values()).includes("layout-change")
      ).toBe(true);
      await view.onClose();
    }

    expect(activeWorkspaceRefs.size).toBe(0);
    expect(activeVaultRefs.size).toBe(0);
  });

  it("PF-UI-010: Companion Version History shows Notice when empty and ready card renders static row without dead button", async () => {
    const transport = new MockTransport();
    transport.executeHandler = (argv) => {
      if (argv[0] === "versions") {
        return JSON.stringify({
          ok: true,
          data: { versions: [], current_label: "", current_path: "" },
        });
      }
      if (argv[0] === "memory") {
        return JSON.stringify({ ok: true, data: { facets: {} } });
      }
      return JSON.stringify({ ok: true, data: {} });
    };
    const client = new PaperForgeClient({ transport });
    const view = new PaperForgeStatusView({} as any);
    (view as any).app = {
      workspace: { openLinkText: vi.fn() },
      vault: {
        getAbstractFileByPath: () => null,
        adapter: { exists: async () => false },
      },
      plugins: {
        plugins: { paperforge: { getClient: () => client, settings: {} } },
      },
    };
    setLanguage((view as any).app, "en");
    view._contentEl = document.createElement("div");
    view._currentPaperKey = "P001";
    view._currentPaperEntry = {
      title: "Ready Paper",
      next_step: "ready",
      deep_reading_status: "pending",
    };

    view._renderPaperMode();

    // Non-interactive ready state must not emit a dead trigger button
    expect(
      view._contentEl.querySelector("button.paperforge-next-step-trigger")
    ).toBeNull();
    expect(
      view._contentEl.querySelector(".paperforge-complete-row")
    ).not.toBeNull();

    // Clicking Version History when versions & backups are both empty emits a Notice
    const verBtn = view._contentEl.querySelector<HTMLButtonElement>(
      '[data-pf-testid="version-history"]'
    )!;
    expect(verBtn).not.toBeNull();
    verBtn.click();

    await vi.waitFor(() => {
      expect(recordedNotices.length).toBeGreaterThan(0);
    });
  });

  it("PF-UI-007: OcrWorkspaceView.open(plugin, paperKey) jumps to the paper's page, selects it, and renders its detail panel", async () => {
    const rows = Array.from({ length: 250 }, (_, i) => ({
      key: `KEY${String(i).padStart(4, "0")}`,
      title: `Paper ${i}`,
      status: i === 150 ? "failed" : "done",
      authors: "Smith",
      year: "2025",
    }));
    const transport = new MockTransport();
    transport.executeHandler = (argv) => {
      if (argv[0] === "ocr") return JSON.stringify(rows);
      if (argv[0] === "action") {
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
      return JSON.stringify({});
    };
    const client = new PaperForgeClient({ transport });
    let createdView: OcrWorkspaceView | null = null;
    const leaf: any = {
      view: null as any,
      setViewState: vi.fn(async () => {
        createdView = new OcrWorkspaceView(leaf, plugin);
        (createdView as any).app = plugin.app;
        leaf.view = createdView;
        await createdView.onOpen();
      }),
    };
    const plugin: any = {
      getClient: () => client,
      app: {
        vault: { adapter: { basePath: "/vault" } },
        workspace: {
          getLeavesOfType: vi.fn(() => (createdView ? [leaf] : [])),
          getLeaf: vi.fn(() => leaf),
          revealLeaf: vi.fn(),
        },
      },
    };
    setLanguage(plugin.app, "en");

    await OcrWorkspaceView.open(plugin, "KEY0150");
    expect(createdView).not.toBeNull();
    const host = (createdView as any).containerEl as HTMLElement;
    expect(host.querySelector(".pf-ocr-ws-pagination")?.textContent).toContain(
      "2 / 3"
    );
    expect(
      host
        .querySelector('tr[data-paper-key="KEY0150"]')
        ?.classList.contains("is-selected")
    ).toBe(true);
    expect(host.querySelector(".pf-ocr-ws-detail")?.textContent).toContain(
      "Paper 150"
    );

    // Apply a filter that hides KEY0210 (done), then deep-link to KEY0210 while view is already open
    (createdView as any).filter = "review";
    await OcrWorkspaceView.open(plugin, "KEY0210");
    expect(host.querySelector(".pf-ocr-ws-pagination")?.textContent).toContain(
      "3 / 3"
    );
    expect(
      host
        .querySelector('tr[data-paper-key="KEY0210"]')
        ?.classList.contains("is-selected")
    ).toBe(true);
    expect(host.querySelector(".pf-ocr-ws-detail")?.textContent).toContain(
      "Paper 210"
    );

    await createdView!.onClose();
  });

  it("PF-UI-011 & PF-SEC-012: domain-preview uses SVG icons with zero raw emojis and styles.css scopes .tag-* selectors", () => {
    const host = document.createElement("div");
    renderDomainModePreview(host, {
      domainMode: "per_collection",
      collections: [
        { key: "C1", name: "Cardiology", path: "Cardiology", item_count: 12 },
      ],
      litDir: "Literature",
      isZh: false,
    });
    expect(
      host.querySelectorAll("svg.pf-svg-icon").length
    ).toBeGreaterThanOrEqual(2);
    expect(host.textContent).not.toMatch(/[📁📂📄]/u);

    renderDomainModePreview(host, {
      domainMode: "unified",
      collections: [
        { key: "C1", name: "Cardiology", path: "Cardiology", item_count: 12 },
      ],
      litDir: "Literature",
      isZh: true,
    });
    expect(
      host.querySelectorAll("svg.pf-svg-icon").length
    ).toBeGreaterThanOrEqual(2);
    expect(host.textContent).not.toMatch(/[📁📂📄]/u);

    const cssPath = path.resolve(__dirname, "../styles.css");
    const css = fs.readFileSync(cssPath, "utf8");
    expect(css).not.toMatch(/^\s*\.tag-(?:pdf|nopdf|collection)\b/m);
    expect(css).toContain(".paperforge-tag.tag-pdf");
    expect(css).toContain(".paperforge-tag.tag-nopdf");
    expect(css).toContain(".paperforge-tag.tag-collection");
  });

  it("PF-UI-012: preserves pending paper leaf and resolves its file when revealing a hidden Companion tab", async () => {
    const workspaceListeners: Record<string, Array<(arg?: any) => void>> = {};
    const workspace = {
      on: vi.fn((ev: string, cb: (arg?: any) => void) => {
        workspaceListeners[ev] = workspaceListeners[ev] ?? [];
        workspaceListeners[ev].push(cb);
        return { ev, cb };
      }),
      offref: vi.fn(),
      getActiveFile: () => null,
      getActiveViewOfType: () => null,
    };
    const leafEl = document.createElement("div");
    leafEl.className = "workspace-leaf";
    document.body.appendChild(leafEl);

    const view = new PaperForgeStatusView({} as any);
    leafEl.appendChild(view.containerEl);
    const contentEl = view.containerEl.children[1] as HTMLElement;
    const resolvePaperContext = vi.fn(async () => ({
      kind: "paper",
      zotero_key: "ZOTKEY01",
    }));

    Object.assign(view as any, {
      app: {
        workspace,
        vault: {
          on: vi.fn(),
          offref: vi.fn(),
          adapter: { basePath: "" },
        },
        plugins: { plugins: {} },
      },
      _contentEl: contentEl,
      _currentMode: "collection",
      _getClient: () => ({ resolvePaperContext }),
      _getCachedIndex: () => [
        { zotero_key: "ZOTKEY01", title: "Cartilage Hydrogel Scaffolds" },
      ],
    });
    (view as any)._renderModeHeader = vi.fn();
    (view as any)._renderBackendBanner = vi.fn();
    (view as any)._renderPaperMode = vi.fn();

    (view as any)._setupEventSubscriptions();

    // 1. Companion tab is hidden behind another tab when the user opens a paper note.
    leafEl.style.display = "none";
    const paperLeaf = {
      view: {
        getViewType: () => "markdown",
        file: {
          path: "Resources/Literature/BoneRegen/ZOTKEY01.md",
          extension: "md",
        },
      },
    };
    for (const cb of workspaceListeners["active-leaf-change"] ?? []) {
      cb(paperLeaf);
    }

    // 2. User switches back to the Companion tab (getActiveFile() is now null).
    leafEl.style.display = "";
    const companionLeaf = {
      view: {
        getViewType: () => VIEW_TYPE_PAPERFORGE,
      },
    };
    for (const cb of workspaceListeners["active-leaf-change"] ?? []) {
      cb(companionLeaf);
    }

    await new Promise((r) => setTimeout(r, 220));
    expect(resolvePaperContext).toHaveBeenCalledWith(
      "Resources/Literature/BoneRegen/ZOTKEY01.md"
    );
    expect((view as any)._currentMode).toBe("paper");
    expect((view as any)._currentPaperKey).toBe("ZOTKEY01");

    await view.onClose();
  });

  it("PF-UI-013: renders immediate loading state during pending startup and shows recovery banner if bootstrap throws", async () => {
    let resolveStats!: (val: any) => void;
    const pendingStats = new Promise((res) => {
      resolveStats = res;
    });
    const view = new PaperForgeStatusView({} as any);
    Object.assign(view as any, {
      app: {
        workspace: {
          on: vi.fn(() => ({})),
          offref: vi.fn(),
          getActiveFile: () => null,
          getActiveViewOfType: () => null,
        },
        vault: {
          on: vi.fn(() => ({})),
          offref: vi.fn(),
          adapter: { basePath: "" },
        },
        plugins: { plugins: {} },
      },
      _getClient: () => ({
        backendVersion: vi.fn(async () => "2.0.8"),
        dashboardStats: vi.fn(() => pendingStats),
        credentialAvailable: vi.fn(async () => false),
        resolvePaperContext: vi.fn(async () => {
          throw new Error("boom during context resolution");
        }),
      }),
      _detectAndSwitch: vi.fn(async () => {
        throw new Error("boom during context resolution");
      }),
    });
    setLanguage((view as any).app, "en");

    await view.onOpen();
    const loadingEl = view.containerEl.querySelector(
      '[data-pf-testid="companion-loading"]'
    );
    expect(loadingEl).not.toBeNull();
    expect(loadingEl?.textContent).toContain("Loading Companion");

    // Settle stats and let _detectAndSwitch throw -> recovery banner & global fallback must appear instead of blank
    resolveStats({
      stats: { papers: 0, ocr_health: {}, pdf_health: {} },
      items: [],
      permissions: {},
    });
    await new Promise((r) => setTimeout(r, 20));
    expect(
      view.containerEl.querySelector('[data-pf-testid="recovery-banner"]')
        ?.textContent
    ).toContain("boom during context resolution");
    expect((view as any)._currentMode).toBe("global");

    await view.onClose();
  });
});
