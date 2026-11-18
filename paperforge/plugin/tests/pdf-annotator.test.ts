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

  it("renders PDF pages, displays annotations with intent/figure badges, and saves new annotations", async () => {
    const addAnnotation = vi.fn().mockResolvedValue({
      ann_id: "ann_new01",
      paper_id: "P100",
      page: 1,
      kind: "highlight",
      color: "green",
      intent: "question",
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
    const qPill = view.contentEl.querySelector(
      '.pf-pdf-intent-pill[data-intent="question"]'
    ) as HTMLButtonElement;
    qPill.click();
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
        intent: "question",
        exact_text: "Sample ACL text",
        comment: "Why p=0.04?",
      })
    );
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
