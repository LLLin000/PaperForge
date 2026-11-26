import { describe, it, expect, vi, beforeEach } from "vitest";
import { JSDOM } from "jsdom";
import * as fs from "node:fs";
import * as path from "node:path";

const dom = new JSDOM("<!doctype html><html><body></body></html>");
(globalThis as any).document = dom.window.document;
(globalThis as any).window = dom.window;
(globalThis as any).HTMLElement = dom.window.HTMLElement;
(globalThis as any).navigator = {
  clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
};

// Polyfill Obsidian-style DOM helpers used in ItemView/Modal builders
function patchElement(proto: any) {
  proto.empty = function () {
    this.innerHTML = "";
  };
  proto.addClass = function (...cls: string[]) {
    this.classList.add(...cls);
  };
  proto.removeClass = function (...cls: string[]) {
    this.classList.remove(...cls);
  };
  proto.toggleClass = function (cls: string, force?: boolean) {
    this.classList.toggle(cls, force);
  };
  proto.setText = function (text: string) {
    this.textContent = text;
  };
  proto.createDiv = function (opts?: any) {
    return this.createEl("div", opts);
  };
  proto.createEl = function (tag: string, opts?: any) {
    const el = this.ownerDocument.createElement(tag);
    if (opts?.cls) {
      for (const c of String(opts.cls).split(/\s+/).filter(Boolean)) {
        el.classList.add(c);
      }
    }
    if (opts?.text !== undefined) el.textContent = String(opts.text);
    if (opts?.attr) {
      for (const [k, v] of Object.entries(opts.attr)) {
        el.setAttribute(k, String(v));
      }
    }
    this.appendChild(el);
    return el;
  };
}
patchElement(dom.window.HTMLElement.prototype);

const mockLoadPdfJs = vi.fn();
const openedModals: Array<{ title: string; text: string }> = [];
const contextMenuItems: string[] = [];
const contextMenuShowSpy = vi.fn();

vi.mock("obsidian", () => ({
  App: class {},
  Notice: class {},
  Menu: class {
    addItem(cb: (item: any) => void) {
      const entry = {
        title: "",
        setTitle(t: string) {
          entry.title = t;
          return entry;
        },
        setIcon() {
          return entry;
        },
        onClick() {
          return entry;
        },
      };
      cb(entry);
      if (entry.title) contextMenuItems.push(entry.title);
      return this;
    }
    addSeparator() {
      return this;
    }
    showAtMouseEvent(ev: MouseEvent) {
      contextMenuShowSpy(ev);
    }
  },
  Platform: { resourcePathPrefix: "app://local/" },
  TFile: class {},
  WorkspaceLeaf: class {},
  ItemView: class {
    leaf: any;
    app: any = {};
    contentEl: HTMLElement;
    constructor(leaf: any) {
      this.leaf = leaf;
      this.contentEl = dom.window.document.createElement("div");
    }
    async setState() {}
  },
  Modal: class {
    app: any;
    contentEl: HTMLElement;
    constructor(app: any) {
      this.app = app;
      this.contentEl = dom.window.document.createElement("div");
    }
    open() {
      (this as any).onOpen?.();
      openedModals.push({
        title: this.contentEl.querySelector("h3")?.textContent ?? "",
        text: this.contentEl.textContent ?? "",
      });
    }
    close() {}
  },
  MarkdownRenderer: class {},
  Component: class {},
  loadPdfJs: () => mockLoadPdfJs(),
}));

import {
  PaperForgePdfView,
  resolvePdfResourceUrl,
  normalizeSelectionRects,
  multiplyPdfTransform,
} from "../src/views/pdf-annotator";
import { OcrWorkspaceView } from "../src/views/ocr-workspace";

describe("PaperForgePdfView & hidden fulltext safety (Commit 2C)", () => {
  beforeEach(() => {
    openedModals.length = 0;
    mockLoadPdfJs.mockReset();
    mockLoadPdfJs.mockResolvedValue({
      getDocument: () => ({
        promise: Promise.resolve({
          numPages: 2,
          getPage: async () => ({
            getViewport: ({ scale }: { scale: number }) => ({
              width: 600 * scale,
              height: 800 * scale,
              transform: [scale, 0, 0, scale, 0, 0],
            }),
            render: () => ({ promise: Promise.resolve() }),
            getTextContent: async () => ({
              items: [
                { str: "Sample ACL text", transform: [1, 0, 0, 12, 72, 700] },
              ],
            }),
          }),
        }),
      }),
    });
  });

  it("keeps views/pdf-annotator.ts free of Node fs and child_process imports", () => {
    const src = fs.readFileSync(
      path.resolve(__dirname, "../src/views/pdf-annotator.ts"),
      "utf-8"
    );
    expect(src).not.toMatch(/from\s+["'](?:node:)?(?:fs|child_process)/);
    expect(src).not.toMatch(/new\s+PaperForgeClient\(/);
  });

  it("resolves vault-relative and external Zotero PDFs via Obsidian adapter / resourcePathPrefix", () => {
    const app = {
      vault: {
        adapter: {
          getResourcePath: (rel: string) => `app://vault/${rel}`,
        },
      },
    } as any;

    const vaultUrl = resolvePdfResourceUrl(app, {
      paper_id: "K1",
      title: "Vault Paper",
      pdf_abs_path: "D:/Vault/paper.pdf",
      pdf_vault_rel: "Zotero/paper.pdf",
      pdf_locator: "Zotero/paper.pdf",
      is_vault_relative: true,
      pdf_sha256: "abc",
      page_count: 1,
      workspace_rel: "Resources/Literature/Ortho/K1",
      note_rel_path: "Resources/Literature/Ortho/K1/K1.md",
      annotations: [],
    });
    expect(vaultUrl).toBe("app://vault/Zotero/paper.pdf");

    const extUrl = resolvePdfResourceUrl(app, {
      paper_id: "K2",
      title: "Ext Paper",
      pdf_abs_path: "D:\\Zotero Library\\storage\\AT01\\ACL Paper.pdf",
      pdf_vault_rel: "",
      pdf_locator: "storage:AT01/ACL Paper.pdf",
      is_vault_relative: false,
      pdf_sha256: "def",
      page_count: 1,
      workspace_rel: "Resources/Literature/Ortho/K2",
      note_rel_path: "Resources/Literature/Ortho/K2/K2.md",
      annotations: [],
    });
    expect(extUrl).toBe(
      "app://local/D:/Zotero%20Library/storage/AT01/ACL%20Paper.pdf"
    );

    const posixHashUrl = resolvePdfResourceUrl(app, {
      paper_id: "K3",
      title: "macOS/Linux Paper",
      pdf_abs_path: "/Users/alice/Zotero/storage/MX09/Paper #1 - Next?.pdf",
      pdf_vault_rel: "",
      pdf_locator: "storage:MX09/Paper #1 - Next?.pdf",
      is_vault_relative: false,
      pdf_sha256: "ghi",
      page_count: 1,
      workspace_rel: "Resources/Literature/Ortho/K3",
      note_rel_path: "Resources/Literature/Ortho/K3/K3.md",
      annotations: [],
    });
    expect(posixHashUrl).toBe(
      "app://local/Users/alice/Zotero/storage/MX09/Paper%20%231%20-%20Next%3F.pdf"
    );
  });

  it("renders PDF pages, omits 5-pill intent clutter, and saves new annotations", async () => {
    const addAnnotation = vi.fn().mockResolvedValue({
      ann_id: "ann_new01",
      paper_id: "P100",
      page: 1,
      kind: "highlight",
      color: "green",
      intent: "general",
      author: "user",
      exact_text: "Sample ACL text",
      comment: "Why p=0.04?",
      tags: [],
      rects: [[0.1, 0.2, 0.5, 0.24]],
      section_path: "Results",
      block_id: "b1",
      figure_id: "figure_001",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "sha1",
      created_at: "2026-11-18T00:00:00Z",
      updated_at: "2026-11-18T00:00:00Z",
      provenance_status: "verified",
    });

    const client = {
      getPdfContext: vi.fn().mockResolvedValue({
        paper_id: "P100",
        title: "ACL Reconstruction Trial",
        pdf_abs_path: "C:/Zotero/storage/X/acl.pdf",
        pdf_vault_rel: "",
        pdf_locator: "storage:X/acl.pdf",
        is_vault_relative: false,
        pdf_sha256: "sha1",
        page_count: 2,
        workspace_rel: "Resources/Literature/Ortho/P100",
        note_rel_path: "Resources/Literature/Ortho/P100/P100.md",
        annotations: [
          {
            ann_id: "ann_existing",
            paper_id: "P100",
            page: 1,
            kind: "area",
            color: "blue",
            intent: "evidence",
            author: "user",
            exact_text: "",
            comment: "KM survival curve",
            tags: [],
            rects: [[0.1, 0.3, 0.8, 0.7]],
            section_path: "Results > Survival",
            block_id: "b2",
            figure_id: "figure_001",
            crop_asset_rel:
              "Resources/Literature/Ortho/P100/assets/P100_ann_existing.jpg",
            embed_wikilink: "![[P100_ann_existing.jpg]]",
            pdf_sha256: "sha1",
            created_at: "2026-11-18T00:00:00Z",
            updated_at: "2026-11-18T00:00:00Z",
            provenance_status: "verified",
          },
        ],
      }),
      addAnnotation,
      listAnnotations: vi.fn().mockResolvedValue([]),
      adoptAnnotation: vi.fn(),
      clearAgentAnnotations: vi.fn(),
      deleteAnnotation: vi.fn().mockResolvedValue({ deleted: true }),
      promoteAnnotation: vi.fn().mockResolvedValue({ promoted: true }),
    } as any;

    const view = new PaperForgePdfView({} as any, { getClient: () => client });
    view.app = {
      vault: {
        adapter: { getResourcePath: (p: string) => `app://vault/${p}` },
        getAbstractFileByPath: () => null,
      },
      workspace: {
        getLeaf: () => ({ openFile: vi.fn() }),
        openLinkText: vi.fn(),
      },
    } as any;

    await view.setState({ paperKey: "P100", page: 1 }, { history: false });

    expect(mockLoadPdfJs).toHaveBeenCalledOnce();
    expect(view.contentEl.querySelectorAll(".pf-pdf-page")).toHaveLength(2);
    expect(view.contentEl.textContent).toContain("figure_001");
    expect(view.contentEl.textContent).toContain("KM survival curve");

    const pageEl = view.contentEl.querySelector(".pf-pdf-page") as HTMLElement;
    view._openCreatePopover({
      anchorEl: pageEl,
      page: 1,
      rects: [[0.1, 0.2, 0.5, 0.24]],
      kind: "highlight",
      exactText: "Sample ACL text",
    });
    expect(view.contentEl.querySelectorAll(".pf-pdf-intent-pill")).toHaveLength(
      0
    );
    const commentBox = view.contentEl.querySelector(
      ".pf-pdf-popover-comment"
    ) as HTMLTextAreaElement;
    commentBox.value = "Why p=0.04?";
    const saveBtn = view.contentEl.querySelector(
      '[data-pf-testid="pdf-save-ann-btn"]'
    ) as HTMLButtonElement;
    saveBtn.click();

    await vi.waitFor(() => {
      expect(addAnnotation).toHaveBeenCalledOnce();
    });
    expect(addAnnotation).toHaveBeenCalledWith(
      "P100",
      expect.objectContaining({
        page: 1,
        intent: "general",
        exact_text: "Sample ACL text",
        comment: "Why p=0.04?",
      })
    );
  });

  it("supports AI PDF annotation layer toggle, margin bracket, adopt, and live state-changed reload", async () => {
    const stateListeners: Array<(payload?: unknown) => void> = [];
    const agentAnn = {
      ann_id: "ann_ai_01",
      paper_id: "P200",
      page: 1,
      kind: "margin",
      color: "purple",
      intent: "general",
      author: "agent",
      lens: "skeleton",
      grounding_tier: "margin_fallback",
      exact_text: "Scanned theorem statement.",
      comment: "Key mechanistic claim needing sample size check.",
      tags: [],
      rects: [[0.012, 0.25, 0.022, 0.38]],
      section_path: "Results",
      block_id: "blk_1",
      figure_id: "",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "sha1",
      created_at: "2026-11-18T00:00:00Z",
      updated_at: "2026-11-18T00:00:00Z",
      provenance_status: "verified",
    };
    const adoptedAnn = {
      ...agentAnn,
      author: "user",
      lens: "",
    };

    const adoptAnnotation = vi.fn().mockResolvedValue(adoptedAnn);
    const listAnnotations = vi.fn().mockResolvedValue([
      agentAnn,
      {
        ...agentAnn,
        ann_id: "ann_ai_02",
        kind: "highlight",
        comment: "Live pushed from CLI agent",
      },
    ]);

    const client = {
      getPdfContext: vi.fn().mockResolvedValue({
        paper_id: "P200",
        title: "Agent Review Paper",
        pdf_abs_path: "C:/Zotero/storage/Y/paper.pdf",
        pdf_vault_rel: "",
        pdf_locator: "storage:Y/paper.pdf",
        is_vault_relative: false,
        pdf_sha256: "sha1",
        page_count: 1,
        workspace_rel: "Resources/Literature/Ortho/P200",
        note_rel_path: "Resources/Literature/Ortho/P200/P200.md",
        annotations: [agentAnn],
      }),
      listAnnotations,
      adoptAnnotation,
      clearAgentAnnotations: vi.fn().mockResolvedValue({
        paper_id: "P200",
        deleted_count: 1,
        deleted_ids: [],
      }),
      deleteAnnotation: vi.fn(),
      promoteAnnotation: vi.fn(),
    } as any;

    const view = new PaperForgePdfView({} as any, { getClient: () => client });
    view.app = {
      vault: {
        adapter: { getResourcePath: (p: string) => `app://vault/${p}` },
        getAbstractFileByPath: () => null,
      },
      workspace: {
        on: (_ev: string, cb: (payload?: unknown) => void) => {
          stateListeners.push(cb);
          return cb;
        },
        offref: vi.fn(),
        getLeaf: () => ({ openFile: vi.fn() }),
        openLinkText: vi.fn(),
      },
    } as any;

    await view.onOpen();
    await view.setState({ paperKey: "P200", page: 1 }, { history: false });

    expect(
      view.contentEl.querySelectorAll(
        ".pf-pdf-ann-box.pf-pdf-hl-agent.pf-pdf-margin-bracket"
      )
    ).toHaveLength(1);
    expect(view.contentEl.textContent).toContain("AI · skeleton");

    // Toggle AI layer off -> hides AI overlays & cards
    const aiToggle = view.contentEl.querySelector(
      '[data-pf-testid="pdf-toggle-ai-layer"]'
    ) as HTMLButtonElement;
    aiToggle.click();
    expect(view.contentEl.querySelectorAll(".pf-pdf-hl-agent")).toHaveLength(0);
    aiToggle.click();
    expect(view.contentEl.querySelectorAll(".pf-pdf-hl-agent")).toHaveLength(1);

    // Live workspace state-changed notification reloads external CLI agent marks
    expect(stateListeners.length).toBeGreaterThan(0);
    stateListeners[0]({ changedKeys: ["P200"] });
    await vi.waitFor(() => {
      expect(listAnnotations).toHaveBeenCalledWith("P200");
      expect(view.contentEl.textContent).toContain(
        "Live pushed from CLI agent"
      );
    });

    // Adopt button converts AI annotation into user annotation
    const adoptBtn = view.contentEl.querySelector(
      '[data-pf-testid="pdf-adopt-ann-btn"]'
    ) as HTMLButtonElement;
    adoptBtn.click();
    await vi.waitFor(() => {
      expect(adoptAnnotation).toHaveBeenCalledWith("P200", "ann_ai_01");
    });
  });

  it("supports Preview split highlight (no popup), collapsible Markup bar SVG/textbox, and note citation copy", async () => {
    const addAnnotation = vi.fn().mockImplementation(async (_k, input) => ({
      ann_id: `ann_mk_${Math.random().toString(16).slice(2, 6)}`,
      paper_id: "P300",
      page: input.page,
      kind: input.kind,
      color: input.color,
      intent: input.intent ?? "general",
      exact_text: input.exact_text ?? "",
      comment: input.comment ?? "",
      tags: [],
      rects: input.rects,
      style: input.style ?? {},
      section_path: "",
      block_id: "",
      figure_id: "",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "sha3",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      provenance_status: "verified",
    }));

    const client: any = {
      getPdfContext: vi.fn().mockResolvedValue({
        paper_id: "P300",
        title: "Preview UX Paper",
        pdf_abs_path: "D:/Z/P300.pdf",
        pdf_vault_rel: "Z/P300.pdf",
        pdf_locator: "Z/P300.pdf",
        is_vault_relative: true,
        pdf_sha256: "sha3",
        page_count: 1,
        workspace_rel: "Literature/P300",
        note_rel_path: "Literature/P300/P300.md",
        annotations: [
          {
            ann_id: "ann_prev_1",
            paper_id: "P300",
            page: 1,
            kind: "shape",
            color: "red",
            intent: "general",
            exact_text: "",
            comment: "",
            tags: [],
            rects: [[0.2, 0.2, 0.5, 0.4]],
            style: {
              shape_type: "arrow",
              stroke_color: "#d64545",
              stroke_width: 2,
            },
            section_path: "Methods",
            block_id: "",
            figure_id: "",
            crop_asset_rel: "",
            embed_wikilink: "",
            pdf_sha256: "sha3",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
            provenance_status: "verified",
          },
          {
            ann_id: "ann_prev_2",
            paper_id: "P300",
            page: 1,
            kind: "highlight",
            color: "yellow",
            intent: "general",
            exact_text: "Anterior tunnel angle was 24 deg.",
            comment: "",
            tags: [],
            rects: [[0.1, 0.5, 0.6, 0.54]],
            section_path: "Results",
            block_id: "",
            figure_id: "",
            crop_asset_rel: "",
            embed_wikilink: "",
            pdf_sha256: "sha3",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
            provenance_status: "verified",
          },
        ],
      }),
      listAnnotations: vi.fn().mockResolvedValue([]),
      addAnnotation,
    };

    const view = new PaperForgePdfView({} as any, {
      getClient: () => client,
    }) as any;
    view.app = {
      vault: { adapter: { getResourcePath: (p: string) => p } },
      workspace: { on: vi.fn().mockReturnValue({}), offref: vi.fn() },
    };
    await view.onOpen();
    await view.setState({ paperKey: "P300", page: 1 }, { history: false });

    // Initial state renders arrow SVG shape & zero unsolicited create popovers
    expect(
      view.contentEl.querySelectorAll(".pf-pdf-svg-layer line")
    ).toHaveLength(1);
    expect(
      view.contentEl.querySelector('[data-pf-testid="pdf-create-popover"]')
    ).toBeNull();

    // Plain mouseup in select mode creates ZERO popup and does NOT call addAnnotation
    const pageEl = view.contentEl.querySelector(".pf-pdf-page") as HTMLElement;
    pageEl.dispatchEvent(
      new dom.window.MouseEvent("mouseup", { bubbles: true })
    );
    expect(addAnnotation).not.toHaveBeenCalled();
    expect(
      view.contentEl.querySelector('[data-pf-testid="pdf-create-popover"]')
    ).toBeNull();

    // Toggling highlight split button activates continuous mode; dropdown selects underline + green
    const hlBtn = view.contentEl.querySelector(
      '[data-pf-testid="pdf-highlight-tool"]'
    ) as HTMLButtonElement;
    hlBtn.click();
    expect(hlBtn.classList.contains("is-active")).toBe(true);

    const menuBtn = view.contentEl.querySelector(
      '[data-pf-testid="pdf-highlight-menu-btn"]'
    ) as HTMLButtonElement;
    menuBtn.click();
    const underlineOpt = view.contentEl.querySelector(
      '[data-pf-testid="pdf-menu-underline"]'
    ) as HTMLButtonElement;
    underlineOpt.click();
    expect(view._highlightKind).toBe("underline");

    // Markup toggle expands secondary bar & activates textbox tool
    const markupBtn = view.contentEl.querySelector(
      '[data-pf-testid="pdf-markup-toggle"]'
    ) as HTMLButtonElement;
    markupBtn.click();
    const tbBtn = view.contentEl.querySelector(
      '[data-pf-testid="pdf-tool-textbox"]'
    ) as HTMLButtonElement;
    tbBtn.click();
    expect(tbBtn.classList.contains("is-active")).toBe(true);

    // Zotero-style Copy Note Citation writes markdown link to clipboard
    const writeClip = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(globalThis.navigator, "clipboard", {
      value: { writeText: writeClip },
      configurable: true,
    });
    const citeBtn = view.contentEl.querySelector(
      '[data-pf-testid="pdf-copy-citation-btn"]'
    ) as HTMLButtonElement;
    citeBtn.click();
    await vi.waitFor(() => {
      expect(writeClip).toHaveBeenCalledTimes(1);
      expect(writeClip.mock.calls[0][0]).toContain("P300.md|P300 p.1");
    });
  });

  it("OcrWorkspaceView opens read-only DiagnosticFulltextPreviewModal for .paperforge/ paths", async () => {
    const readDiagnosticFulltext = vi.fn().mockResolvedValue({
      paper_id: "P1",
      content: "# OCR Diagnostic Line 1",
      truncated: false,
      total_lines: 1,
      total_chars: 23,
    });
    const view = new OcrWorkspaceView(
      {} as any,
      {
        getClient: () => ({ readDiagnosticFulltext }),
        settings: {},
      } as any
    );
    (view as any).app = {
      vault: {
        adapter: { basePath: "/vault" },
        getAbstractFileByPath: () => null,
      },
      workspace: {},
    };
    (view as any).papers = [
      { key: "P1", fulltextPath: ".paperforge/ocr/P1/fulltext.md" },
    ];

    await (view as any)._openFulltext("P1");
    expect(readDiagnosticFulltext).toHaveBeenCalledWith("P1");
    expect(openedModals).toHaveLength(1);
    expect(openedModals[0].text).toContain("# OCR Diagnostic Line 1");
  });

  it("uses actual first-page width for Fit-to-Width, supports Escape/Ctrl+F shortcuts, ephemeral state, and canvas LRU eviction", async () => {
    mockLoadPdfJs.mockResolvedValueOnce({
      getDocument: () => ({
        promise: Promise.resolve({
          numPages: 12,
          getPage: async () => ({
            getViewport: ({ scale }: { scale: number }) => ({
              width: 842 * scale,
              height: 595 * scale,
              transform: [scale, 0, 0, scale, 0, 0],
            }),
            render: () => ({ promise: Promise.resolve() }),
            getTextContent: async () => ({
              items: [
                { str: "Landscape page", transform: [1, 0, 0, 12, 10, 500] },
              ],
            }),
          }),
        }),
      }),
    });

    const client: any = {
      getPdfContext: vi.fn().mockResolvedValue({
        paper_id: "P_WIDE",
        title: "Landscape Supplement",
        pdf_abs_path: "D:/Z/P_WIDE.pdf",
        pdf_vault_rel: "Z/P_WIDE.pdf",
        pdf_locator: "Z/P_WIDE.pdf",
        is_vault_relative: true,
        pdf_sha256: "shawide",
        page_count: 12,
        workspace_rel: "Literature/P_WIDE",
        note_rel_path: "Literature/P_WIDE/P_WIDE.md",
        annotations: [],
      }),
      listAnnotations: vi.fn().mockResolvedValue([]),
    };

    const view = new PaperForgePdfView({} as any, {
      getClient: () => client,
    }) as any;
    view.app = {
      vault: { adapter: { getResourcePath: (p: string) => p } },
      workspace: { on: vi.fn().mockReturnValue({}), offref: vi.fn() },
    };

    await view.onOpen();
    await view.setState({ paperKey: "P_WIDE", page: 1 }, { history: false });

    // Dynamic page base width (842pt instead of hardcoded 595pt)
    expect(view._firstPageBaseWidth).toBe(842);
    Object.defineProperty(view._scrollEl, "clientWidth", {
      value: 890,
      configurable: true,
    });
    const fitBtn = view.contentEl.querySelector(
      '[data-pf-testid="pdf-fit-width-btn"]'
    ) as HTMLButtonElement;
    fitBtn.click();
    expect(view._scale).toBe(1);

    // Ephemeral state round-trip
    view._scrollEl.scrollTop = 320;
    const eph = view.getEphemeralState();
    expect(eph.scroll).toBe(320);
    expect(eph.fitWidth).toBe(true);
    view.setEphemeralState({ scroll: 150, scale: 1.5, fitWidth: false });
    expect(view._scale).toBe(1.5);

    // Escape resets continuous highlight / tool state
    view._continuousHighlight = true;
    view._activeTool = "area";
    view.contentEl.dispatchEvent(
      new dom.window.KeyboardEvent("keydown", { key: "Escape", bubbles: true })
    );
    expect(view._continuousHighlight).toBe(false);
    expect(view._activeTool).toBe("select");

    // Canvas LRU eviction drops far-away rendered canvases while preserving text cache
    for (let p = 1; p <= 12; p += 1) {
      await view._ensurePageRendered(p);
    }
    expect(view._renderedPages.size).toBeLessThanOrEqual(9);
    expect(view._pageTexts.size).toBe(12);

    // 2px reading progress hairline updates with scrollToPage
    const progressFill = view.contentEl.querySelector(
      '[data-pf-testid="pdf-progress-fill"]'
    ) as HTMLElement;
    expect(progressFill).not.toBeNull();
    view.scrollToPage(6);
    expect(progressFill.style.width).toBe("50%");
    expect(progressFill.getAttribute("aria-valuenow")).toBe("50");

    // Highlight dropdown closes on outside pointerdown
    const caret = view.contentEl.querySelector(
      '[data-pf-testid="pdf-highlight-menu-btn"]'
    ) as HTMLButtonElement;
    caret.click();
    expect(
      view.contentEl.querySelector('[data-pf-testid="pdf-highlight-dropdown"]')
    ).not.toBeNull();
    dom.window.document.body.dispatchEvent(
      new dom.window.Event("pointerdown", { bubbles: true })
    );
    expect(
      view.contentEl.querySelector('[data-pf-testid="pdf-highlight-dropdown"]')
    ).toBeNull();

    // PDF++ native contextmenu fires when text selection exists on page
    contextMenuItems.length = 0;
    contextMenuShowSpy.mockClear();
    const firstPageEl = view._pageEls.get(1) as HTMLElement;
    view._getSelectionData = () => ({
      pageEl: firstPageEl,
      pageNumber: 1,
      rects: [[0.1, 0.2, 0.4, 0.24]],
      exactText: "Key radiological finding",
    });
    firstPageEl.dispatchEvent(
      new dom.window.MouseEvent("contextmenu", {
        bubbles: true,
        cancelable: true,
      })
    );
    expect(contextMenuShowSpy).toHaveBeenCalledTimes(1);
    expect(contextMenuItems.length).toBe(4);

    // Non-empty text selection in normal "select" mode shows floating mini-bar and saves highlight in 1 click
    const addAnnotationSpy = vi.fn().mockResolvedValue({
      ann_id: "ann_hl_float",
      paper_id: "P_WIDE",
      page: 1,
      kind: "highlight",
      color: "green",
      intent: "general",
      exact_text: "Key radiological finding",
      comment: "",
      tags: [],
      rects: [[0.1, 0.2, 0.4, 0.24]],
      section_path: "",
      block_id: "",
      figure_id: "",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "shawide",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    client.addAnnotation = addAnnotationSpy;
    firstPageEl.dispatchEvent(
      new dom.window.MouseEvent("mouseup", { bubbles: true })
    );
    const floatBar = view.contentEl.querySelector(
      '[data-pf-testid="pdf-selection-float-bar"]'
    );
    expect(floatBar).not.toBeNull();
    expect(
      view.contentEl.querySelector('[data-pf-testid="pdf-create-popover"]')
    ).toBeNull();
    (
      view.contentEl.querySelector(
        '[data-pf-testid="pdf-sel-hl-green"]'
      ) as HTMLButtonElement
    ).click();
    await vi.waitFor(() => expect(addAnnotationSpy).toHaveBeenCalledOnce());
    expect(addAnnotationSpy.mock.calls[0][1].color).toBe("green");

    // Double-buffered zoom keeps existing canvas until replacement finishes painting
    view._renderedPages.delete(1);
    const oldCanvas = firstPageEl.querySelector(
      ".pf-pdf-canvas"
    ) as HTMLCanvasElement;
    expect(oldCanvas).not.toBeNull();
    await view._ensurePageRendered(1);
    expect(firstPageEl.querySelectorAll(".pf-pdf-canvas")).toHaveLength(1);

    await view.onClose();
  });

  it("normalizeSelectionRects merges same-line spans, refuses dual-column gutters, drops giant container rects, and trims line seams", () => {
    const pageRect = { left: 100, top: 200, width: 600, height: 800 };
    const cleaned = normalizeSelectionRects(
      [
        // Giant wrapper box spanning almost entire page should be dropped
        {
          left: 110,
          top: 210,
          right: 690,
          bottom: 500,
          width: 580,
          height: 290,
        },
        // Contiguous same-line words on left column
        { left: 130, top: 300, right: 200, bottom: 314, width: 70, height: 14 },
        {
          left: 204,
          top: 300,
          right: 310,
          bottom: 314,
          width: 106,
          height: 14,
        },
        // Right column word on same Y separated by a wide central gutter (90px) must NOT merge!
        {
          left: 400,
          top: 300,
          right: 540,
          bottom: 314,
          width: 140,
          height: 14,
        },
        // Second stacked line slightly overlapping line 1 vertically
        {
          left: 130,
          top: 313,
          right: 290,
          bottom: 327,
          width: 160,
          height: 14,
        },
      ],
      pageRect
    );

    expect(cleaned).toHaveLength(3);
    // Line 1 left column merged cleanly (x0=30/600=0.05, x1=210/600=0.35)
    expect(cleaned[0][0]).toBeCloseTo(0.05, 3);
    expect(cleaned[0][2]).toBeCloseTo(0.35, 3);
    // Line 1 right column kept separate (x0=300/600=0.50, x1=440/600=0.733)
    expect(cleaned[1][0]).toBeCloseTo(0.5, 3);
    expect(cleaned[1][2]).toBeCloseTo(440 / 600, 3);
    // Line 2 seam trimmed cleanly so line 1 bottom <= line 2 top
    expect(cleaned[0][3]).toBeLessThanOrEqual(cleaned[2][1]);

    // Standard PDF.js viewport transform * text transform maps CropBox & Y-flip
    const vp = [2, 0, 0, -2, -20, 1600];
    const tx = [1, 0, 0, 10, 50, 700];
    const m = multiplyPdfTransform(vp, tx);
    expect(m[4]).toBe(80);
    expect(m[5]).toBe(200);
  });
});
