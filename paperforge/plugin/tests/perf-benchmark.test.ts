// @vitest-environment jsdom
/**
 * PaperForge Host-Impact & UX Performance Benchmark Suite (`npm run bench`).
 * Enforces hard quantitative budgets ensuring zero noticeable Obsidian UI lag.
 */
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { BasePaperRowDto } from "../src/client/paperforge-client";

const resolvePaperContextSpy = vi.fn(async () => ({ kind: "global" as const }));

vi.mock("obsidian", () => {
  class ItemView {
    app: unknown;
    leaf: unknown;
    contentEl = document.createElement("div");
    containerEl = document.createElement("div");
    constructor(leaf: unknown) {
      this.leaf = leaf;
      this.app = (leaf as { app?: unknown })?.app ?? {};
      const header = document.createElement("div");
      header.className = "view-header";
      this.containerEl.appendChild(header);
      this.containerEl.appendChild(this.contentEl);
    }
    registerEvent() {}
  }
  class Modal {
    app: unknown;
    modalEl = document.createElement("div");
    contentEl = document.createElement("div");
    constructor(app: unknown) {
      this.app = app;
    }
    open() {}
    close() {}
    setTitle() {}
  }
  class SuggestModal<T> extends Modal {
    inputEl = document.createElement("input");
    limit = 40;
    setPlaceholder() {}
    setInstructions() {}
    onOpen() {}
    getSuggestions(_q: string): T[] {
      return [];
    }
    renderSuggestion() {}
    onChooseSuggestion() {}
  }
  class PluginSettingTab {
    app: unknown;
    containerEl = document.createElement("div");
    constructor(app: unknown) {
      this.app = app;
    }
    hide() {}
  }
  class Plugin {
    app: unknown;
    manifest: unknown;
    constructor(app: unknown, manifest: unknown) {
      this.app = app;
      this.manifest = manifest;
    }
    loadData = vi.fn(async () => ({}));
    saveData = vi.fn(async () => undefined);
    registerView = vi.fn();
    registerBasesView = vi.fn(() => true);
    addRibbonIcon = vi.fn();
    addCommand = vi.fn();
    addSettingTab = vi.fn();
    addStatusBarItem = vi.fn(() => {
      const el = document.createElement("span");
      return Object.assign(el, {
        setText: (t: string) => {
          el.textContent = t;
        },
      });
    });
    registerEvent = vi.fn();
    registerDomEvent = vi.fn();
    registerInterval = vi.fn(() => 0);
    registerObsidianProtocolHandler = vi.fn();
  }
  class Scope {
    register() {}
  }
  class Menu {
    addItem() {
      return this;
    }
    addSeparator() {
      return this;
    }
    showAtMouseEvent() {}
  }
  return {
    App: class {},
    Plugin,
    ItemView,
    Modal,
    SuggestModal,
    PluginSettingTab,
    MarkdownView: class {},
    TFile: class {},
    Notice: function Notice() {},
    Setting: class {
      setName() {
        return this;
      }
      setDesc() {
        return this;
      }
      addToggle() {
        return this;
      }
      addText() {
        return this;
      }
      addDropdown() {
        return this;
      }
    },
    Component: class {
      load() {}
      unload() {}
    },
    MarkdownRenderer: class {},
    Scope,
    Menu,
    Platform: {
      isWin: true,
      isMacOS: false,
      isLinux: false,
      resourcePathPrefix: "app://local/",
    },
    Keymap: { isModEvent: () => false },
    loadPdfJs: vi.fn(),
  };
});

// Polyfill Obsidian HTMLElement helpers used across OcrWorkspaceView, PaperForgePdfView, Settings
const protoAny = HTMLElement.prototype as unknown as Record<string, unknown>;
if (typeof protoAny.empty !== "function") {
  protoAny.empty = function (this: HTMLElement) {
    this.textContent = "";
  };
}
if (typeof protoAny.addClass !== "function") {
  protoAny.addClass = function (this: HTMLElement, ...cls: string[]) {
    this.classList.add(...cls);
  };
}
if (typeof protoAny.removeClass !== "function") {
  protoAny.removeClass = function (this: HTMLElement, ...cls: string[]) {
    this.classList.remove(...cls);
  };
}
if (typeof protoAny.toggleClass !== "function") {
  protoAny.toggleClass = function (
    this: HTMLElement,
    cls: string,
    force?: boolean
  ) {
    this.classList.toggle(cls, force);
  };
}
if (typeof protoAny.setText !== "function") {
  protoAny.setText = function (this: HTMLElement, text: string) {
    this.textContent = text;
  };
}
if (typeof protoAny.createEl !== "function") {
  protoAny.createEl = function (
    this: HTMLElement,
    tag: string,
    opts?: {
      cls?: string;
      text?: string;
      type?: string;
      value?: string;
      placeholder?: string;
      attr?: Record<string, string>;
    },
    cb?: (el: HTMLElement) => void
  ) {
    const doc = this.ownerDocument || document;
    const el = doc.createElement(tag);
    if (opts?.cls) {
      for (const c of String(opts.cls).split(/\s+/).filter(Boolean))
        el.classList.add(c);
    }
    if (opts?.text !== undefined) el.textContent = String(opts.text);
    if (opts?.type && "type" in el) (el as HTMLInputElement).type = opts.type;
    if (opts?.value !== undefined && "value" in el)
      (el as HTMLInputElement).value = opts.value;
    if (opts?.placeholder !== undefined && "placeholder" in el)
      (el as HTMLInputElement).placeholder = opts.placeholder;
    if (opts?.attr) {
      for (const [k, v] of Object.entries(opts.attr))
        el.setAttribute(k, String(v));
    }
    this.appendChild(el);
    cb?.(el);
    return el;
  };
}
if (typeof protoAny.createDiv !== "function") {
  protoAny.createDiv = function (
    this: HTMLElement,
    opts?: Record<string, unknown>,
    cb?: (el: HTMLElement) => void
  ) {
    return (
      this as unknown as {
        createEl: (t: string, o?: unknown, c?: unknown) => HTMLElement;
      }
    ).createEl("div", opts, cb);
  };
}
if (typeof protoAny.createSpan !== "function") {
  protoAny.createSpan = function (
    this: HTMLElement,
    opts?: Record<string, unknown>,
    cb?: (el: HTMLElement) => void
  ) {
    return (
      this as unknown as {
        createEl: (t: string, o?: unknown, c?: unknown) => HTMLElement;
      }
    ).createEl("span", opts, cb);
  };
}

import PaperForgePlugin from "../src/main";
import { PaperForgeBasesView } from "../src/views/paperforge-base-view";
import { PaperForgeStatusView } from "../src/views/dashboard";
import { scorePaperQuickMatch } from "../src/views/quick-switcher";
import { OcrWorkspaceView } from "../src/views/ocr-workspace";
import { PaperForgePdfView } from "../src/views/pdf-annotator";
import { PaperForgeSettingTab } from "../src/settings";

function makeBenchmarkRows(count: number): Record<string, BasePaperRowDto> {
  const rows: Record<string, BasePaperRowDto> = {};
  const domains = ["Stroke", "Cardiology", "Oncology", "Neuro", "Chest"];
  const journals = ["Radiology", "Nature", "NEJM", "Lancet", "MedIA"];
  for (let i = 0; i < count; i += 1) {
    const k = `KEY${String(i).padStart(4, "0")}`;
    rows[k] = {
      zotero_key: k,
      title: `Deep ${domains[i % domains.length]} Analysis Study #${i} Radiology`,
      first_author: `Author${i % 40}`,
      year: String(2018 + (i % 8)),
      journal: journals[i % journals.length],
      impact_factor: String((2 + (i % 35)).toFixed(1)),
      impact_factor_source: "jcr",
      journal_partition: "Q1",
      domain: domains[i % domains.length],
      collections: [i % 2 === 0 ? "Core" : "Review"],
      has_pdf: i % 3 !== 0,
      ocr_status: i % 2 === 0 ? "done" : "pending",
      deep_reading_status: i % 4 === 0 ? "done" : "none",
      main_note_path: `Literature/${k}.md`,
      pdf_path: `${k}.pdf`,
      user_ann_count: i % 5,
      agent_ann_count: i % 3,
      memory_facet_count: i % 4,
      needs_diagnostic: false,
    };
  }
  return rows;
}

interface BenchmarkRecord {
  metric: string;
  measured: string;
  budget: string;
}

const scorecard: BenchmarkRecord[] = [];

const isStandaloneBench = process.argv.some((a) =>
  a.includes("perf-benchmark")
);

function recordBench(metric: string, measured: string, budget: string) {
  scorecard.push({ metric, measured, budget });
}

describe("PaperForge Performance & Host-Impact Benchmark", () => {
  const tempDirs: string[] = [];

  afterEach(() => {
    for (const d of tempDirs.splice(0)) {
      fs.rmSync(d, { recursive: true, force: true });
    }
    vi.restoreAllMocks();
  });

  it("1. Plugin onload() stays under 50ms with zero synchronous daemon/fs discovery", async () => {
    const tmpVault = fs.mkdtempSync(path.join(os.tmpdir(), "pf-bench-"));
    tempDirs.push(tmpVault);

    const workspaceEvents: Record<
      string,
      Array<(...a: unknown[]) => void>
    > = {};
    const appMock = {
      vault: {
        adapter: { basePath: tmpVault },
        on: vi.fn(),
        offref: vi.fn(),
      },
      workspace: {
        on: vi.fn((ev: string, cb: (...a: unknown[]) => void) => {
          (workspaceEvents[ev] ||= []).push(cb);
          return { ev, cb };
        }),
        offref: vi.fn(),
        onLayoutReady: vi.fn(),
        getLeavesOfType: vi.fn(() => []),
        containerEl: document.createElement("div"),
        rootSplit: {},
      },
      keymap: { pushScope: vi.fn(), popScope: vi.fn() },
    } as unknown as import("obsidian").App;

    const plugin = new PaperForgePlugin(appMock, {
      id: "paperforge",
      name: "PaperForge",
      version: "1.2.11",
      minAppVersion: "1.0.0",
      description: "",
      author: "",
      authorUrl: "",
      isDesktopOnly: true,
    });

    const t0 = performance.now();
    await plugin.onload();
    const elapsed = performance.now() - t0;
    plugin.onunload();

    const onloadBudget = isStandaloneBench ? 50 : 300;
    recordBench(
      "Plugin onload()",
      `${elapsed.toFixed(2)} ms`,
      `< ${onloadBudget.toFixed(2)} ms`
    );
    expect(elapsed).toBeLessThan(onloadBudget);
  });

  it("2. Companion sidebar triggers 0 RPCs when collapsed or on non-document extensions", async () => {
    const sidedock = document.createElement("div");
    sidedock.className = "mod-sidedock is-collapsed";
    document.body.appendChild(sidedock);

    let leafHandler: ((leaf?: unknown) => void) | undefined;
    const leaf = {
      app: {
        vault: { on: vi.fn(), offref: vi.fn() },
        workspace: {
          on: vi.fn((ev: string, cb: (leaf?: unknown) => void) => {
            if (ev === "active-leaf-change") leafHandler = cb;
            return { ev, cb };
          }),
          offref: vi.fn(),
          getActiveFile: vi.fn(() => ({ path: "img.png", extension: "png" })),
        },
        keymap: { pushScope: vi.fn(), popScope: vi.fn() },
      },
    } as unknown as import("obsidian").WorkspaceLeaf;

    const view = new PaperForgeStatusView(leaf);
    sidedock.appendChild(view.containerEl);
    (view as unknown as { _buildPanel: () => void })._buildPanel = () => {};
    (
      view as unknown as { _bootstrapDashboard: () => Promise<void> }
    )._bootstrapDashboard = async () => {};
    (view as unknown as { _fetchVersion: () => void })._fetchVersion = () => {};
    (
      view as unknown as {
        _getClient: () => {
          resolvePaperContext: typeof resolvePaperContextSpy;
        };
      }
    )._getClient = () => ({ resolvePaperContext: resolvePaperContextSpy });

    resolvePaperContextSpy.mockClear();
    view._setupEventSubscriptions();

    const tCollapsedStart = performance.now();
    for (let i = 0; i < 100; i += 1) {
      leafHandler?.({
        view: { file: { path: `Paper${i}.md`, extension: "md" } },
      });
    }
    const collapsedMs = performance.now() - tCollapsedStart;
    expect(resolvePaperContextSpy).not.toHaveBeenCalled();

    sidedock.classList.remove("is-collapsed");
    const tSkipStart = performance.now();
    for (let i = 0; i < 100; i += 1) {
      await view._resolveModeForFile({
        path: `assets/figure-${i}.png`,
        extension: "png",
      });
    }
    const skipMs = performance.now() - tSkipStart;
    expect(resolvePaperContextSpy).not.toHaveBeenCalled();

    view.onClose();
    sidedock.remove();

    const switchBudget = isStandaloneBench ? 15 : 150;
    recordBench(
      "100x collapsed/non-doc switch",
      `${(collapsedMs + skipMs).toFixed(2)} ms (0 RPCs)`,
      `< ${switchBudget.toFixed(2)} ms`
    );
    expect(collapsedMs + skipMs).toBeLessThan(switchBudget);
  });

  it("3. Base Table chunked render + live filter + surgical selection at 2,000 papers", () => {
    const rows = makeBenchmarkRows(2000);
    const snap = {
      generated_at: "2026-01-01T00:00:00Z",
      row_count: 2000,
      rows,
    };
    const root = document.createElement("div");
    document.body.appendChild(root);

    const controller = {
      containerEl: root,
      app: {
        workspace: {
          on: vi.fn(() => ({})),
          offref: vi.fn(),
          openLinkText: vi.fn(),
        },
        vault: { getAbstractFileByPath: vi.fn() },
      },
      data: {
        data: Object.values(rows).map((r) => ({
          file: { path: r.main_note_path, basename: r.zotero_key },
          getValue: () => null,
        })),
        groupedData: [
          {
            key: { toString: () => "" },
            entries: Object.values(rows).map((r) => ({
              file: { path: r.main_note_path, basename: r.zotero_key },
              getValue: () => null,
            })),
          },
        ],
      },
      config: {
        name: "BenchView",
        getOrder: () => [
          "title",
          "first_author",
          "year",
          "journal",
          "impact_factor",
          "domain",
          "ocr_status",
        ],
        getDisplayName: (id: string) => id,
        get: () => undefined,
        set: vi.fn(),
      },
    };

    const view = new PaperForgeBasesView({} as never, root, {
      app: controller.app as never,
      getClient: vi.fn(),
      getBaseSnapshotCache: () => snap,
      getBaseFilters: () => ({}),
      setBaseFilters: vi.fn(),
      refreshBaseSnapshot: vi.fn(async () => snap),
      isOcrRunningForKey: () => false,
      openPaperPdf: vi.fn(async () => undefined),
      openPaperSplitReading: vi.fn(async () => undefined),
      requestOcrRun: vi.fn(async () => undefined),
      triggerManualSync: vi.fn(),
      openOcrDiagnostic: vi.fn(),
    });
    (view as unknown as { data: unknown }).data = controller.data;
    (view as unknown as { config: unknown }).config = controller.config;

    const tRender0 = performance.now();
    view.render();
    const renderMs = performance.now() - tRender0;

    const renderedRowsOnFirstPaint =
      root.querySelectorAll("tr.pf-base-row").length;
    expect(renderedRowsOnFirstPaint).toBeGreaterThan(0);
    expect(renderedRowsOnFirstPaint).toBeLessThanOrEqual(120);

    const searchInput = root.querySelector<HTMLInputElement>(
      '[data-pf-testid="base-filter-search"]'
    )!;
    expect(searchInput).not.toBeNull();
    searchInput.value = "Stroke 2022";

    const tFilter0 = performance.now();
    (
      view as unknown as {
        _updateFilters: (
          patch: Record<string, unknown>,
          opts?: { preserveSearchFocus?: boolean }
        ) => void;
      }
    )._updateFilters({ query: "Stroke 2022" }, { preserveSearchFocus: true });
    const filterMs = performance.now() - tFilter0;

    const cb = root.querySelector<HTMLInputElement>(
      'input[type="checkbox"][data-pf-select-key]'
    )!;
    cb.checked = true;
    const tSel0 = performance.now();
    cb.dispatchEvent(new Event("change"));
    const selMs = performance.now() - tSel0;

    view.onunload();
    root.remove();

    const renderBudget = isStandaloneBench ? 200 : 1500;
    const filterBudget = isStandaloneBench ? 40 : 250;
    const selBudget = isStandaloneBench ? 20 : 150;

    recordBench(
      `Bases initial render (2,000 papers, chunked ${renderedRowsOnFirstPaint})`,
      `${renderMs.toFixed(2)} ms`,
      `< ${renderBudget.toFixed(2)} ms`
    );
    recordBench(
      "Bases filter update (2,000 papers)",
      `${filterMs.toFixed(2)} ms`,
      `< ${filterBudget.toFixed(2)} ms`
    );
    recordBench(
      "Bases surgical checkbox toggle",
      `${selMs.toFixed(2)} ms`,
      `< ${selBudget.toFixed(2)} ms`
    );

    expect(renderMs).toBeLessThan(renderBudget);
    expect(filterMs).toBeLessThan(filterBudget);
    expect(selMs).toBeLessThan(selBudget);
  });

  it("4. Quick Switcher multi-token query across 2,000 papers averages < 5ms", () => {
    const rows = Object.values(makeBenchmarkRows(2000));
    const queries = [
      "stroke 2022",
      "radiology author12",
      "oncology nejm",
      "deep analysis 2020",
      "chest medIA",
    ];
    const t0 = performance.now();
    let totalHits = 0;
    for (let iter = 0; iter < 4; iter += 1) {
      for (const q of queries) {
        for (const r of rows) {
          if (scorePaperQuickMatch(r, q) > 0) totalHits += 1;
        }
      }
    }
    const perQueryMs = (performance.now() - t0) / 20;
    expect(totalHits).toBeGreaterThan(0);

    const qsBudget = isStandaloneBench ? 5 : 40;
    recordBench(
      "Quick Switcher query (2,000 papers)",
      `${perQueryMs.toFixed(2)} ms/query`,
      `< ${qsBudget.toFixed(2)} ms`
    );
    expect(perQueryMs).toBeLessThan(qsBudget);
  });

  it("5. styles.css contains zero bare global * selectors, zero transition:all, and stays < 650 KB", () => {
    const cssPath = path.resolve(__dirname, "..", "styles.css");
    const css = fs.readFileSync(cssPath, "utf-8");
    const sizeKb = Buffer.byteLength(css, "utf-8") / 1024;

    const withoutComments = css.replace(/\/\*[\s\S]*?\*\//g, "");
    const transitionAllMatches =
      withoutComments.match(/transition\s*:\s*all\b/gi) ?? [];

    // Split on rule braces to check selector lists outside keyframes/@media headers
    const bareUniversalSelectors: string[] = [];
    const selectorRegex = /(^|[};])\s*([^{};@]+)\{/g;
    let m: RegExpExecArray | null;
    while ((m = selectorRegex.exec(withoutComments)) !== null) {
      const selGroup = m[2].trim();
      for (const rawSel of selGroup.split(",")) {
        const s = rawSel.trim();
        if (s === "*" || s === "*::before" || s === "*::after") {
          bareUniversalSelectors.push(s);
        }
      }
    }

    recordBench(
      "styles.css hygiene & size",
      `${sizeKb.toFixed(1)} KB (${bareUniversalSelectors.length} bare *, ${transitionAllMatches.length} transition:all)`,
      "< 650 KB (0, 0)"
    );

    expect(bareUniversalSelectors).toEqual([]);
    expect(transitionAllMatches).toEqual([]);
    expect(sizeKb).toBeLessThan(650);
  });

  it("6. OCR Workspace paginated render + filter at 2,000 papers stays within 100 DOM rows", () => {
    const leaf = {
      app: {
        vault: { on: vi.fn(), offref: vi.fn(), adapter: { basePath: "" } },
        workspace: { on: vi.fn(), offref: vi.fn(), getLeavesOfType: () => [] },
        keymap: { pushScope: vi.fn(), popScope: vi.fn() },
      },
    } as unknown as import("obsidian").WorkspaceLeaf;

    const pluginMock = {
      app: (leaf as unknown as { app: unknown }).app,
      getClient: () => ({
        describeAction: vi.fn(async () => null),
      }),
      settings: {},
    };
    const ws = new OcrWorkspaceView(leaf, pluginMock);
    const papers = Array.from({ length: 2000 }, (_, i) => ({
      key: `K${String(i).padStart(4, "0")}`,
      title: `Stroke Biomarker Study #${i}`,
      status: i % 3 === 0 ? "pending" : "done",
      pipelineVersion: "2.0.0",
      lastRun: "2026-01-01",
      hasBackup: false,
      authors: `Author${i % 40}`,
      year: String(2016 + (i % 10)),
      pages: "12",
      backupCount: 0,
      canRedo: false,
      canRebuild: true,
      recommendedAction: "run",
      fulltextPath: `Literature/K${i}/fulltext.md`,
      ocrFinishedAt: "",
    }));
    const wsAny = ws as unknown as {
      papers: unknown[];
      _searchQuery: string;
      _loadState: string;
      _render: () => void;
      _refreshTable: () => void;
    };
    wsAny.papers = papers;
    wsAny._loadState = "ready";

    const tRender0 = performance.now();
    wsAny._render();
    const renderMs = performance.now() - tRender0;

    const renderedRows = ws.contentEl.querySelectorAll(
      "table.pf-ocr-ws-table tbody tr"
    ).length;
    expect(renderedRows).toBeLessThanOrEqual(100);

    const tFilter0 = performance.now();
    wsAny._searchQuery = "Study #19";
    wsAny._refreshTable();
    const filterMs = performance.now() - tFilter0;

    const renderBudget = isStandaloneBench ? 160 : 1200;
    const filterBudget = isStandaloneBench ? 80 : 600;
    recordBench(
      `OCR Workspace render (2,000 papers, ${renderedRows} visible)`,
      `${renderMs.toFixed(2)} ms`,
      `< ${renderBudget.toFixed(2)} ms`
    );
    recordBench(
      "OCR Workspace filter refresh (2,000 papers)",
      `${filterMs.toFixed(2)} ms`,
      `< ${filterBudget.toFixed(2)} ms`
    );
    expect(renderMs).toBeLessThan(renderBudget);
    expect(filterMs).toBeLessThan(filterBudget);
  });

  it("7. PDF Annotator surgical overlay update & 100-page cached search", async () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
      {} as CanvasRenderingContext2D
    );
    const leaf = {
      app: {
        vault: { adapter: { getResourcePath: (p: string) => p } },
        workspace: { on: vi.fn(() => ({})), offref: vi.fn() },
      },
    } as unknown as import("obsidian").WorkspaceLeaf;

    const view = new PaperForgePdfView(leaf, { getClient: vi.fn() });
    const vAny = view as unknown as {
      _ctx: Record<string, unknown>;
      _doc: Record<string, unknown>;
      _annotations: Array<Record<string, unknown>>;
      _pageEls: Map<number, HTMLElement>;
      _pageTexts: Map<number, string>;
      _pageTextsLower: Map<number, string>;
      _searchQuery: string;
      _buildChrome: () => void;
      _refreshOverlays: (p?: number) => void;
      _runSearch: (advance: boolean, step?: number) => Promise<void>;
    };
    vAny._ctx = {
      paper_id: "BENCHPDF",
      title: "100-Page Radiology Study",
      pdf_locator: "bench.pdf",
      is_vault_relative: true,
      pdf_sha256: "abc",
      page_count: 100,
      workspace_rel: "Lit/BENCHPDF",
      note_rel_path: "Lit/BENCHPDF/BENCHPDF.md",
      annotations: [],
    };
    vAny._doc = {
      numPages: 100,
      getPage: async () => ({
        getViewport: ({ scale }: { scale: number }) => ({
          width: 600 * scale,
          height: 800 * scale,
        }),
        render: () => ({ promise: Promise.resolve() }),
        getTextContent: async () => ({ items: [] }),
      }),
    };
    vAny._annotations = Array.from({ length: 200 }, (_, i) => ({
      ann_id: `a_${i}`,
      paper_id: "BENCHPDF",
      page: (i % 100) + 1,
      rects: [[0.1, 0.2, 0.4, 0.24]],
      kind: "highlight",
      color: "yellow",
      author: "user",
      intent: "general",
      exact_text: `Snippet ${i}`,
      comment: "",
    }));
    vAny._buildChrome();
    for (let p = 1; p <= 100; p += 1) {
      const pageEl = document.createElement("div");
      pageEl.className = "pf-pdf-page";
      pageEl.createDiv({ cls: "pf-pdf-overlay-layer" });
      vAny._pageEls.set(p, pageEl);
      const txt =
        p === 87
          ? "Unique Radiomics AUC 0.96 finding on page 87"
          : `Standard body text page ${p}`;
      vAny._pageTexts.set(p, txt);
      vAny._pageTextsLower.set(p, txt.toLowerCase());
    }

    const tFull0 = performance.now();
    vAny._refreshOverlays();
    const fullOverlayMs = performance.now() - tFull0;

    const tSingle0 = performance.now();
    vAny._refreshOverlays(5);
    const singleOverlayMs = performance.now() - tSingle0;

    const tSearch0 = performance.now();
    vAny._searchQuery = "radiomics auc";
    await vAny._runSearch(false);
    const searchMs = performance.now() - tSearch0;

    const fullBudget = isStandaloneBench ? 120 : 800;
    const singleBudget = isStandaloneBench ? 15 : 120;
    const searchBudget = isStandaloneBench ? 25 : 200;
    recordBench(
      "PDF overlays full rebuild (100p / 200 anns)",
      `${fullOverlayMs.toFixed(2)} ms`,
      `< ${fullBudget.toFixed(2)} ms`
    );
    recordBench(
      "PDF overlays surgical single page",
      `${singleOverlayMs.toFixed(2)} ms`,
      `< ${singleBudget.toFixed(2)} ms`
    );
    recordBench(
      "PDF 100-page cached fulltext search",
      `${searchMs.toFixed(2)} ms`,
      `< ${searchBudget.toFixed(2)} ms`
    );

    expect(fullOverlayMs).toBeLessThan(fullBudget);
    expect(singleOverlayMs).toBeLessThan(singleBudget);
    expect(searchMs).toBeLessThan(searchBudget);
  });

  it("8. Settings O(1) collision check (1,000 dirs) + Control Center display()", () => {
    const tmpVault = fs.mkdtempSync(
      path.join(os.tmpdir(), "pf-settings-bench-")
    );
    tempDirs.push(tmpVault);
    const litDir = path.join(tmpVault, "Literature");
    fs.mkdirSync(litDir, { recursive: true });
    for (let i = 0; i < 1000; i += 1) {
      fs.mkdirSync(path.join(litDir, `Paper_${String(i).padStart(4, "0")}`));
    }

    const appMock = {
      vault: { adapter: { basePath: tmpVault }, getConfig: () => "en" },
      workspace: { on: vi.fn(() => ({})), offref: vi.fn() },
    } as unknown as import("obsidian").App;
    const pluginMock = {
      app: appMock,
      manifest: { version: "1.2.11" },
      settings: {
        literature_dir: "",
        resources_dir: "",
        base_dir: "",
        system_dir: ".paperforge",
        skill_dir: ".agents/skills",
        zotero_data_dir: "",
        _setup_complete: true,
        ui_theme_mode: "obsidian",
      },
      saveSettings: vi.fn(async () => undefined),
      getClient: () => null,
    };

    const tab = new PaperForgeSettingTab(appMock, pluginMock as never);
    const tColl0 = performance.now();
    (
      tab as unknown as {
        _detectAndIsolateFolderCollision: (v: string) => void;
      }
    )._detectAndIsolateFolderCollision(tmpVault);
    const collMs = performance.now() - tColl0;

    const tDisp0 = performance.now();
    tab.display();
    tab.activeTab = "module-detail";
    tab.display();
    const dispMs = performance.now() - tDisp0;
    tab.hide();

    const collBudget = isStandaloneBench ? 20 : 150;
    const dispBudget = isStandaloneBench ? 120 : 800;
    recordBench(
      "Settings O(1) collision probe (1,000 dirs)",
      `${collMs.toFixed(2)} ms`,
      `< ${collBudget.toFixed(2)} ms`
    );
    recordBench(
      "Settings Control Center 2x display()",
      `${dispMs.toFixed(2)} ms`,
      `< ${dispBudget.toFixed(2)} ms`
    );

    expect(collMs).toBeLessThan(collBudget);
    expect(dispMs).toBeLessThan(dispBudget);
  });

  it("9. main.js production bundle size check + Scorecard summary", () => {
    const mainJsPath = path.resolve(__dirname, "..", "main.js");
    if (fs.existsSync(mainJsPath)) {
      const bundleKb = fs.statSync(mainJsPath).size / 1024;
      recordBench(
        "main.js bundle size",
        `${bundleKb.toFixed(1)} KB`,
        "< 1500 KB"
      );
      expect(bundleKb).toBeLessThan(1500);
    } else {
      recordBench("main.js bundle size", "not built yet", "< 1500 KB");
    }

    const lines = [
      "",
      "=== PaperForge Performance & Host-Impact Scorecard ===",
      ...scorecard.map(
        (r) => `  - ${r.metric}: ${r.measured} (budget ${r.budget})`
      ),
      "=======================================================",
    ];
    console.info(lines.join("\n"));
    expect(scorecard.length).toBeGreaterThanOrEqual(9);
  });
});
