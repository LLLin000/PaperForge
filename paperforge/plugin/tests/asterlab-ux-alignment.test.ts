/**
 * @vitest-environment jsdom
 */
import * as fs from "fs";
import * as path from "path";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("obsidian", () => {
  class ItemView {
    containerEl: HTMLElement;
    app: unknown;
    leaf: unknown;
    constructor(leaf: unknown) {
      this.leaf = leaf;
      this.containerEl = document.createElement("div");
      this.containerEl.createEl("div");
      this.containerEl.createEl("div");
    }
    registerEvent() {}
  }
  class Modal {
    app: unknown;
    contentEl = document.createElement("div");
    constructor(app: unknown) {
      this.app = app;
    }
    open() {}
    close() {}
  }
  class Plugin {}
  class PluginSettingTab {}
  class Scope {
    register() {}
  }
  class WorkspaceLeaf {}
  class TFile {
    path = "";
    basename = "";
    extension = "md";
  }
  const Notice = vi.fn();
  function setIcon() {}
  return {
    ItemView,
    Modal,
    Plugin,
    PluginSettingTab,
    Scope,
    WorkspaceLeaf,
    TFile,
    Notice,
    Platform: {},
    setIcon,
    MarkdownRenderer: { renderMarkdown: vi.fn() },
  };
});

import { PaperForgeStatusView } from "../src/views/dashboard";
import { PaperForgePdfView } from "../src/views/pdf-annotator";
import { setLanguage } from "../src/i18n";

function attachObsidianDomHelpers(el: HTMLElement): void {
  const proto = HTMLElement.prototype as unknown as Record<string, unknown>;
  if (!proto.empty) {
    proto.empty = function (this: HTMLElement) {
      this.innerHTML = "";
    };
  }
  if (!proto.addClass) {
    proto.addClass = function (this: HTMLElement, ...cls: string[]) {
      for (const c of cls) {
        for (const p of String(c).split(/\s+/).filter(Boolean)) {
          this.classList.add(p);
        }
      }
    };
  }
  if (!proto.removeClass) {
    proto.removeClass = function (this: HTMLElement, ...cls: string[]) {
      for (const c of cls) {
        for (const p of String(c).split(/\s+/).filter(Boolean)) {
          this.classList.remove(p);
        }
      }
    };
  }
  if (!proto.setText) {
    proto.setText = function (this: HTMLElement, txt: string) {
      this.textContent = txt;
    };
  }
  if (!proto.setAttr) {
    proto.setAttr = function (
      this: HTMLElement,
      name: string,
      val: string | null
    ) {
      if (val === null) this.removeAttribute(name);
      else this.setAttribute(name, val);
    };
  }
  if (!proto.createDiv) {
    proto.createDiv = function (
      this: HTMLElement,
      opts?:
        | string
        | { cls?: string; text?: string; attr?: Record<string, string> }
    ) {
      return (this as unknown as { createEl: Function }).createEl("div", opts);
    };
  }
  if (!proto.createSpan) {
    proto.createSpan = function (
      this: HTMLElement,
      opts?:
        | string
        | { cls?: string; text?: string; attr?: Record<string, string> }
    ) {
      return (this as unknown as { createEl: Function }).createEl("span", opts);
    };
  }
  if (!proto.createEl) {
    proto.createEl = function (
      this: HTMLElement,
      tag: string,
      opts?:
        | string
        | {
            cls?: string;
            text?: string;
            type?: string;
            title?: string;
            placeholder?: string;
            value?: string;
            attr?: Record<string, string>;
          }
    ) {
      const child = document.createElement(tag);
      if (typeof opts === "string") {
        child.className = opts;
      } else if (opts) {
        if (opts.cls) child.className = opts.cls;
        if (opts.text !== undefined) child.textContent = opts.text;
        if (opts.type && "type" in child)
          (child as HTMLInputElement).type = opts.type;
        if (opts.title) child.title = opts.title;
        if (opts.placeholder && "placeholder" in child)
          (child as HTMLInputElement).placeholder = opts.placeholder;
        if (opts.value !== undefined && "value" in child)
          (child as HTMLInputElement).value = opts.value;
        if (opts.attr) {
          for (const [k, v] of Object.entries(opts.attr)) {
            child.setAttribute(k, v);
          }
        }
      }
      this.appendChild(child);
      return child;
    };
  }
  void el;
}

describe("ADR-016: AsterLab UX Contract Alignment", () => {
  beforeEach(() => {
    attachObsidianDomHelpers(document.body);
    setLanguage({} as never, "zh");
  });

  it("CSS styles enforce three-tier radii (zero 5/7/8/9px literals)", () => {
    const cssPath = path.resolve(__dirname, "../styles.css");
    const css = fs.readFileSync(cssPath, "utf-8");
    const offTier = css.match(/border-radius:\s*(?:5|7|8|9)px/g) ?? [];
    expect(offTier).toEqual([]);
  });

  it("UI view sources contain zero [!!] or [OK] log-prefix strings", () => {
    const srcRoot = path.resolve(__dirname, "../src");
    const uiFiles = [
      "main.ts",
      "views/dashboard.ts",
      "views/ocr-workspace.ts",
      "views/paperforge-base-view.ts",
      "views/pdf-annotator.ts",
    ];
    for (const rel of uiFiles) {
      const content = fs.readFileSync(path.join(srcRoot, rel), "utf-8");
      expect(content).not.toMatch(/\["?\[!!\]|"\[OK\]/);
    }
  });

  it("renders zero-idle Global Activity Strip and jumps via DeepLink when active", async () => {
    const openPaperPdf = vi.fn().mockResolvedValue(undefined);
    const openOcrDiagnostic = vi.fn();
    let tasks: Array<{
      kind: "sync" | "ocr" | "embed";
      label: string;
      current?: number;
      total?: number;
      key?: string;
    }> = [];

    const view = new PaperForgeStatusView({} as never);
    (view as unknown as { app: unknown }).app = {
      plugins: {
        plugins: {
          paperforge: {
            settings: { base_dir: "Bases" },
            getActiveBackgroundTasks: () => tasks,
            openPaperPdf,
            openOcrDiagnostic,
          },
        },
      },
      vault: {
        adapter: { getBasePath: () => "/vault", exists: async () => false },
        getAbstractFileByPath: () => null,
      },
      workspace: {
        on: () => ({}),
        getActiveFile: () => null,
        getActiveViewOfType: () => null,
      },
    };
    view._buildPanel();

    const strip = view.containerEl.querySelector(
      '[data-pf-testid="global-activity-strip"]'
    ) as HTMLElement;
    expect(strip).not.toBeNull();
    expect(strip.children.length).toBe(0);

    tasks = [
      {
        kind: "ocr",
        label: "正在解析全文",
        current: 2,
        total: 5,
        key: "KEY_PROC",
      },
    ];
    (
      view as unknown as { _renderGlobalActivityStrip: () => void }
    )._renderGlobalActivityStrip();

    expect(strip.children.length).toBe(1);
    expect(strip.textContent).toContain("正在解析全文");
    expect(strip.textContent).toContain("2/5");

    const jumpBtn = strip.querySelector(
      '[data-pf-testid="activity-jump-ocr"]'
    ) as HTMLButtonElement;
    jumpBtn.click();
    expect(openOcrDiagnostic).toHaveBeenCalledWith("KEY_PROC");
  });

  it("shows recoverable inline banner with cause + action instead of silent toast on failure", async () => {
    const sync = vi.fn().mockResolvedValue({ ok: true });
    const view = new PaperForgeStatusView({} as never);
    (view as unknown as { app: unknown }).app = {
      plugins: {
        plugins: {
          paperforge: {
            settings: { base_dir: "MissingBases" },
            getClient: () => ({
              sync,
              credentialAvailable: async () => false,
            }),
            openSetupJourney: () => true,
          },
        },
      },
      vault: {
        adapter: { getBasePath: () => "/vault", exists: async () => false },
        getAbstractFileByPath: () => null,
      },
      workspace: {
        on: () => ({}),
        getActiveFile: () => null,
        getActiveViewOfType: () => null,
      },
    };
    view._buildPanel();
    view._backendUnavailable = true;
    view._renderBackendBanner();
    view._renderGlobalMode();

    // Single Primary CTA discipline: recovery card owns .primary, so hubBtn downgrades
    const primaryBtns = view.containerEl.querySelectorAll(
      ".paperforge-contextual-btn.primary"
    );
    expect(primaryBtns.length).toBe(1);

    // Click hubBtn when .base dir is missing -> inline recovery banner appears
    const hubBtn = Array.from(view.containerEl.querySelectorAll("button")).find(
      (b) => b.textContent?.includes("打开文献中心")
    ) as HTMLButtonElement;
    hubBtn.click();

    const banner = view.containerEl.querySelector(
      '[data-pf-testid="recovery-banner"]'
    );
    expect(banner).not.toBeNull();
    expect(banner?.textContent).toContain("MissingBases");
    const dismiss = banner?.querySelector(
      ".pf-recovery-banner-dismiss"
    ) as HTMLButtonElement;
    dismiss.click();
    expect(
      view.containerEl.querySelector('[data-pf-testid="recovery-banner"]')
    ).toBeNull();
  });

  it("turns Living Paper Memory page references into PDF DeepLink buttons", async () => {
    const openPaperPdf = vi.fn().mockResolvedValue(undefined);
    const getMemoryCard = vi.fn().mockResolvedValue({
      paper_id: "KEY_DONE",
      facets: [
        {
          facet: "idea_logic",
          label: "研究思路与逻辑链",
          content:
            "在 [p.3, Sec. 3.1] 证实 L-type Ca2+ 通道峰值，详见第 5 页。",
          updated_at: "2026-11-20T00:00:00Z",
          revision: 1,
        },
      ],
    });
    const view = new PaperForgeStatusView({} as never);
    (view as unknown as { app: unknown }).app = {
      plugins: {
        plugins: {
          paperforge: {
            settings: {},
            getClient: () => ({ getMemoryCard }),
            openPaperPdf,
          },
        },
      },
      vault: {
        adapter: { getBasePath: () => "/vault", exists: async () => false },
        getAbstractFileByPath: () => null,
      },
      workspace: {
        on: () => ({}),
        getActiveFile: () => null,
        getActiveViewOfType: () => null,
      },
    };
    view._buildPanel();
    view._currentPaperKey = "KEY_DONE";

    const host = document.createElement("div");
    await (
      view as unknown as {
        _loadLivingMemoryInto: (el: HTMLElement, key: string) => Promise<void>;
      }
    )._loadLivingMemoryInto(host, "KEY_DONE");

    const p3Btn = host.querySelector(
      '[data-pf-testid="memory-deeplink-p3"]'
    ) as HTMLButtonElement | null;
    const p5Btn = host.querySelector(
      '[data-pf-testid="memory-deeplink-p5"]'
    ) as HTMLButtonElement | null;
    expect(p3Btn?.textContent).toBe("[p.3, Sec. 3.1]");
    expect(p5Btn?.textContent).toBe("第 5 页");
    p3Btn?.click();
    expect(openPaperPdf).toHaveBeenCalledWith("KEY_DONE", { page: 3 });
  });

  it("toggles .is-narrow on PaperForgePdfView when split-pane width <= 680px", async () => {
    const pdfView = new PaperForgePdfView({} as never, {
      app: {} as never,
      getClient: () => ({}) as never,
    });
    const el = document.createElement("div");
    Object.defineProperty(el, "clientWidth", {
      value: 620,
      configurable: true,
    });
    (pdfView as unknown as { contentEl: HTMLElement }).contentEl = el;
    (
      pdfView as unknown as { _bindNarrowObserver: () => void }
    )._bindNarrowObserver();
    expect(el.classList.contains("is-narrow")).toBe(true);
  });

  it("synchronizes corner radii with Obsidian host CSS variables, Liquid Glass, and 4-tier motion", () => {
    const cssPath = path.resolve(__dirname, "../styles.css");
    const css = fs.readFileSync(cssPath, "utf-8");
    expect(css).toContain(
      "--pf-radius-control: var(--input-radius, var(--radius-s, 6px))"
    );
    expect(css).toContain(
      "--pf-radius-btn: var(--button-radius, var(--radius-s, 6px))"
    );
    expect(css).toContain("--pf-radius-panel: var(--radius-m, 10px)");
    expect(css).toContain(
      "--pf-radius-dialog: var(--modal-radius, var(--radius-l, 12px))"
    );
    expect(css).toContain("rgba(20, 22, 28, 0.86)");
    expect(css).toContain("@keyframes pf-float-up");
    expect(css).toContain("@keyframes pf-pop-in");
    expect(css).toContain("@keyframes pf-nudge");
    expect(css).toContain("body.pf-reduce-motion");
    expect(css).toContain("body.pf-no-glass");
    expect(css).toContain("body.pf-theme-warm");
  });

  it("applies .pf-nudge when saving an empty Living Paper Memory facet", async () => {
    const refineMemoryCard = vi.fn();
    const getMemoryCard = vi.fn().mockResolvedValue({
      paper_id: "KEY_DONE",
      facets: [],
    });
    const view = new PaperForgeStatusView({} as never);
    (view as unknown as { app: unknown }).app = {
      plugins: {
        plugins: {
          paperforge: {
            settings: {},
            getClient: () => ({ getMemoryCard, refineMemoryCard }),
          },
        },
      },
      vault: {
        adapter: { getBasePath: () => "/vault", exists: async () => false },
        getAbstractFileByPath: () => null,
      },
      workspace: {
        on: () => ({}),
        getActiveFile: () => null,
        getActiveViewOfType: () => null,
      },
    };
    view._buildPanel();
    view._currentPaperKey = "KEY_DONE";

    const host = document.createElement("div");
    await (
      view as unknown as {
        _loadLivingMemoryInto: (el: HTMLElement, key: string) => Promise<void>;
      }
    )._loadLivingMemoryInto(host, "KEY_DONE");

    const addBtn = host.querySelector(
      '[data-pf-testid="memory-facet-add-idea_logic"]'
    ) as HTMLButtonElement;
    addBtn.click();

    const editor = host.querySelector(
      '[data-pf-testid="memory-facet-editor-idea_logic"]'
    ) as HTMLTextAreaElement;
    const saveBtn = host.querySelector(
      '[data-pf-testid="memory-facet-save"]'
    ) as HTMLButtonElement;
    editor.value = "   ";
    saveBtn.click();

    expect(refineMemoryCard).not.toHaveBeenCalled();
    expect(editor.classList.contains("pf-nudge")).toBe(true);
  });
});
