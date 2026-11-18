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

vi.mock("obsidian", () => ({
  App: class {},
  Notice: class {},
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
});
