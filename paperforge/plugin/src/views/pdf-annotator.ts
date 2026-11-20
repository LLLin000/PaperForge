import {
  App,
  EventRef,
  ItemView,
  Notice,
  Platform,
  TFile,
  WorkspaceLeaf,
  loadPdfJs,
} from "obsidian";
import { VIEW_TYPE_PAPERFORGE_PDF } from "../constants";
import { t } from "../i18n";
import type {
  AnnotationColor,
  AnnotationKind,
  AnnotationStyleDto,
  PaperForgeClient,
  PaperPdfContextDto,
  PdfAnnotationDto,
} from "../client/paperforge-client";
import { createPfIconBtn, setPfIcon, type PfIconName } from "./icons";

export interface PdfAnnotatorOpenState {
  paperKey: string;
  page?: number;
  annId?: string;
}

interface PdfPluginHost {
  getClient(): PaperForgeClient;
}

interface PdfTextItem {
  str?: string;
  transform?: number[];
  width?: number;
  height?: number;
}

interface PdfViewportLike {
  width: number;
  height: number;
  transform?: number[];
}

interface PdfPageLike {
  getViewport(params: { scale: number }): PdfViewportLike;
  render(params: {
    canvasContext: CanvasRenderingContext2D;
    viewport: PdfViewportLike;
  }): { promise: Promise<void> };
  getTextContent(): Promise<{ items: PdfTextItem[] }>;
}

interface PdfOutlineItem {
  title?: string;
  dest?: unknown;
  items?: PdfOutlineItem[];
}

interface PdfDocumentLike {
  numPages: number;
  getPage(pageNumber: number): Promise<PdfPageLike>;
  getOutline?: () => Promise<PdfOutlineItem[] | null>;
  getDestination?: (dest: string) => Promise<unknown[] | null>;
  getPageIndex?: (ref: unknown) => Promise<number>;
  destroy?: () => Promise<void> | void;
}

type SidebarTab = "thumbs" | "toc" | "annotations";
type HighlightKind = "highlight" | "underline" | "strikethrough";
type MarkupTool = "select" | "area" | "ink" | "shape" | "textbox" | "note";
type ShapeSubtype = "rect" | "ellipse" | "arrow" | "line";
type AuthorFilter = "all" | "user" | "agent";

const PREVIEW_HIGHLIGHT_SWATCHES: Array<{
  id: AnnotationColor;
  hex: string;
  zh: string;
  en: string;
}> = [
  { id: "yellow", hex: "#fde047", zh: "黄色", en: "Yellow" },
  { id: "green", hex: "#86efac", zh: "绿色", en: "Green" },
  { id: "blue", hex: "#93c5fd", zh: "蓝色", en: "Blue" },
  { id: "pink", hex: "#f9a8d4", zh: "粉色", en: "Pink" },
  { id: "purple", hex: "#d8b4fe", zh: "紫色", en: "Purple" },
];

const MARKUP_STROKE_SWATCHES: Array<{
  id: AnnotationColor;
  hex: string;
  zh: string;
  en: string;
}> = [
  { id: "red", hex: "#d64545", zh: "红色", en: "Red" },
  { id: "purple", hex: "#5b45c9", zh: "主色紫", en: "Violet" },
  { id: "blue", hex: "#1d4ed8", zh: "蓝色", en: "Blue" },
  { id: "green", hex: "#1f8a5b", zh: "绿色", en: "Green" },
  { id: "ink", hex: "#1c1b19", zh: "墨黑", en: "Ink" },
];

const STROKE_WIDTHS = [1.5, 2.5, 4];
const TEXTBOX_FONT_SIZES = [12, 14, 16];

function lbl(zh: string, en: string): string {
  return t("pdf_filter_all") === "All" ? en : zh;
}

export function resolvePdfResourceUrl(
  app: App,
  ctx: PaperPdfContextDto
): string {
  if (ctx.is_vault_relative && ctx.pdf_vault_rel) {
    return app.vault.adapter.getResourcePath(ctx.pdf_vault_rel);
  }
  const abs = (ctx.pdf_abs_path || "").replace(/\\/g, "/").replace(/^\/+/, "");
  if (!abs) return "";
  const prefix = Platform.resourcePathPrefix || "app://local/";
  return `${prefix}${encodeURI(abs)}`;
}

export class PaperForgePdfView extends ItemView {
  private plugin: PdfPluginHost;
  private _state: PdfAnnotatorOpenState = { paperKey: "" };
  private _ctx: PaperPdfContextDto | null = null;
  private _doc: PdfDocumentLike | null = null;
  private _annotations: PdfAnnotationDto[] = [];
  private _tocItems: Array<{ title: string; page: number; depth: number }> = [];

  private _scale = 1.25;
  private _fitWidth = false;
  private _currentPage = 1;
  private _sidebarOpen = true;
  private _sidebarTab: SidebarTab = "annotations";
  private _markupOpen = false;
  private _activeTool: MarkupTool = "select";
  private _shapeSubtype: ShapeSubtype = "arrow";
  private _highlightKind: HighlightKind = "highlight";
  private _highlightColor: AnnotationColor = "yellow";
  private _continuousHighlight = false;
  private _markupColor: AnnotationColor = "red";
  private _markupStrokeHex = "#d64545";
  private _markupFillTransparent = true;
  private _markupStrokeWidth = 2.5;
  private _markupFontSize = 14;
  private _popoverColor: AnnotationColor = "yellow";
  private _authorFilter: AuthorFilter = "all";
  private _showAgentLayer = true;
  private _searchQuery = "";
  private _searchMatches: Array<{ page: number; text: string }> = [];
  private _searchIndex = 0;

  private _renderedPages = new Set<number>();
  private _renderingPages = new Set<number>();
  private _pageTexts = new Map<number, string>();
  private _observer: IntersectionObserver | null = null;
  private _pageEls = new Map<number, HTMLElement>();
  private _thumbEls = new Map<number, HTMLElement>();

  private _scrollEl: HTMLElement | null = null;
  private _sidebarEl: HTMLElement | null = null;
  private _sidebarContentEl: HTMLElement | null = null;
  private _markupBarEl: HTMLElement | null = null;
  private _popoverEl: HTMLElement | null = null;
  private _highlightMenuEl: HTMLElement | null = null;
  private _areaFloatEl: HTMLElement | null = null;
  private _pageInputEl: HTMLInputElement | null = null;
  private _zoomLabelEl: HTMLElement | null = null;
  private _searchCountEl: HTMLElement | null = null;

  private _splitMainBtn: HTMLButtonElement | null = null;
  private _markupToggleBtn: HTMLButtonElement | null = null;
  private _aiToggleBtn: HTMLButtonElement | null = null;
  private _sideToggleBtn: HTMLButtonElement | null = null;
  private _clearAiBtn: HTMLButtonElement | null = null;
  private _fitWidthBtn: HTMLButtonElement | null = null;
  private _toolBtns = new Map<string, HTMLButtonElement>();
  private _resizeObserver: ResizeObserver | null = null;
  private _stateRef: EventRef | null = null;
  private _loadVersion = 0;

  constructor(leaf: WorkspaceLeaf, plugin: PdfPluginHost) {
    super(leaf);
    this.plugin = plugin;
  }

  getViewType(): string {
    return VIEW_TYPE_PAPERFORGE_PDF;
  }

  getDisplayText(): string {
    if (this._ctx?.title) {
      return `PDF · ${this._ctx.title.slice(0, 32)}`;
    }
    if (this._state.paperKey) {
      return `PDF · ${this._state.paperKey}`;
    }
    return "PaperForge PDF";
  }

  getIcon(): string {
    return "file-text";
  }

  getState(): Record<string, unknown> {
    return {
      paperKey: this._state.paperKey,
      page: this._currentPage,
      annId: this._state.annId,
    };
  }

  async setState(state: unknown, result: { history: boolean }): Promise<void> {
    const raw = (state ?? {}) as Partial<PdfAnnotatorOpenState>;
    const nextKey = String(raw.paperKey ?? "").trim();
    const samePaper = nextKey && nextKey === this._state.paperKey && this._doc;
    this._state = {
      paperKey: nextKey,
      page: typeof raw.page === "number" ? raw.page : undefined,
      annId: raw.annId ? String(raw.annId) : undefined,
    };
    await super.setState(state, result);
    if (samePaper && this._state.page) {
      this.scrollToPage(this._state.page, this._state.annId);
      return;
    }
    await this._loadAndRender();
  }

  async onOpen(): Promise<void> {
    this._subscribeStateChanges();
    this._bindNarrowObserver();
    await this._loadAndRender();
  }

  private _bindNarrowObserver(): void {
    const updateNarrow = () => {
      const w = this.contentEl?.clientWidth || 0;
      if (w > 0) {
        this.contentEl.classList.toggle("is-narrow", w <= 680);
      }
    };
    updateNarrow();
    if (typeof ResizeObserver === "function" && this.contentEl) {
      this._resizeObserver?.disconnect();
      this._resizeObserver = new ResizeObserver(() => updateNarrow());
      this._resizeObserver.observe(this.contentEl);
    }
  }

  async onClose(): Promise<void> {
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
      this._resizeObserver = null;
    }
    if (this._stateRef) {
      const ws = this.app?.workspace as unknown as {
        offref?: (ref: EventRef) => void;
      };
      ws?.offref?.(this._stateRef);
      this._stateRef = null;
    }
    this._teardownDocument();
    this.contentEl.empty();
  }

  private _subscribeStateChanges(): void {
    if (this._stateRef) return;
    const ws = this.app?.workspace as unknown as {
      on?: (ev: string, cb: (payload?: unknown) => void) => EventRef;
    };
    if (typeof ws?.on === "function") {
      this._stateRef = ws.on(
        "paperforge:state-changed",
        (payload?: unknown) => {
          const key = this._state.paperKey;
          if (!key || !this._doc) return;
          const changedKeys = (
            payload as { changedKeys?: string[] } | undefined
          )?.changedKeys;
          if (
            !Array.isArray(changedKeys) ||
            changedKeys.length === 0 ||
            changedKeys.includes(key)
          ) {
            void this._reloadAnnotationsOnly();
          }
        }
      );
    }
  }

  private async _reloadAnnotationsOnly(): Promise<void> {
    const key = this._state.paperKey;
    if (!key) return;
    try {
      const list = await this.plugin.getClient().listAnnotations(key);
      this._annotations = list;
      if (this._ctx) {
        this._ctx.annotations = list;
      }
      this._refreshOverlays();
      this._renderSidebarBody();
    } catch {
      // Transient reload errors stay silent so the reading flow continues
    }
  }

  private _teardownDocument(): void {
    this._closeTransientPopups();
    if (this._observer) {
      this._observer.disconnect();
      this._observer = null;
    }
    this._renderedPages.clear();
    this._renderingPages.clear();
    this._pageTexts.clear();
    this._pageEls.clear();
    this._thumbEls.clear();
    this._toolBtns.clear();
    if (this._doc && typeof this._doc.destroy === "function") {
      try {
        void this._doc.destroy();
      } catch {
        // Ignore pdf.js teardown noise
      }
    }
    this._doc = null;
  }

  private _closeTransientPopups(): void {
    this._popoverEl?.remove();
    this._popoverEl = null;
    this._highlightMenuEl?.remove();
    this._highlightMenuEl = null;
    this._areaFloatEl?.remove();
    this._areaFloatEl = null;
  }

  private _renderEmptyState(message: string): void {
    this.contentEl.empty();
    const wrap = this.contentEl.createDiv({ cls: "pf-pdf-empty" });
    wrap.createEl("p", { text: message });
  }

  private async _loadAndRender(): Promise<void> {
    const version = ++this._loadVersion;
    const root = this.contentEl;
    this._teardownDocument();
    root.empty();
    root.addClass("pf-pdf-view");

    if (!this._state.paperKey) {
      this._renderEmptyState(
        t("pdf_select_paper_hint") ||
          "Open a paper from PaperForge Library or Companion to view its PDF."
      );
      return;
    }

    const loading = root.createDiv({ cls: "pf-pdf-empty" });
    loading.setText(t("pdf_loading") || "Loading PDF...");

    let ctx: PaperPdfContextDto;
    try {
      ctx = await this.plugin.getClient().getPdfContext(this._state.paperKey);
    } catch (err) {
      if (version !== this._loadVersion) return;
      loading.setText(
        `${t("pdf_load_failed") || "Failed to load PDF"}: ${
          err instanceof Error ? err.message : String(err)
        }`
      );
      return;
    }

    if (version !== this._loadVersion) return;
    this._ctx = ctx;
    this._annotations = Array.isArray(ctx.annotations) ? ctx.annotations : [];
    const headerTitle = (this.leaf as unknown as { updateHeader?: () => void })
      .updateHeader;
    if (typeof headerTitle === "function") {
      headerTitle.call(this.leaf);
    }

    const resourceUrl = resolvePdfResourceUrl(this.app, ctx);
    if (!resourceUrl) {
      loading.setText(
        t("pdf_not_available") || "Canonical PDF not available for this paper."
      );
      return;
    }

    try {
      const pdfjsLib = await loadPdfJs();
      const task = pdfjsLib.getDocument(resourceUrl);
      this._doc = (await task.promise) as PdfDocumentLike;
    } catch (err) {
      if (version !== this._loadVersion) return;
      loading.setText(
        `${t("pdf_render_failed") || "Unable to open PDF"}: ${
          err instanceof Error ? err.message : String(err)
        }`
      );
      return;
    }

    if (version !== this._loadVersion) return;
    loading.remove();
    this._buildChrome();
    await this._mountPages();
    void this._loadTocOutline();
    if (this._state.page) {
      this.scrollToPage(this._state.page, this._state.annId);
    } else if (this._state.annId) {
      const target = this._annotations.find(
        (a) => a.ann_id === this._state.annId
      );
      if (target) this.scrollToPage(target.page, target.ann_id);
    }
  }

  private _buildChrome(): void {
    const root = this.contentEl;
    const ctx = this._ctx!;
    const totalPages = this._doc?.numPages || ctx.page_count || 1;

    // Tier 1: Calm 40px Preview Toolbar
    const toolbar = root.createDiv({ cls: "pf-pdf-toolbar" });

    // Left: Sidebar toggle + Title + Conditional Provenance Warning
    const leftGroup = toolbar.createDiv({ cls: "pf-pdf-toolbar-left" });
    this._sideToggleBtn = createPfIconBtn(leftGroup, {
      icon: "panel-left",
      label: lbl("显示/隐藏侧栏", "Toggle Sidebar"),
      cls: "pf-pdf-icon-btn",
      testid: "pdf-toggle-sidebar",
      active: this._sidebarOpen,
    });
    this._sideToggleBtn.addEventListener("click", () => {
      this._sidebarOpen = !this._sidebarOpen;
      this._syncChromeState();
    });

    const docTitle = leftGroup.createEl("span", {
      cls: "pf-pdf-doc-title",
      text: ctx.title || ctx.paper_id,
    });
    docTitle.title = ctx.title || ctx.paper_id;

    const hasChanged = this._annotations.some(
      (a) => a.provenance_status === "changed"
    );
    if (hasChanged) {
      const warn = leftGroup.createEl("span", {
        cls: "pf-pdf-prov-badge is-warn",
        attr: { "data-pf-testid": "pdf-prov-changed" },
      });
      const warnIcon = warn.createEl("span", { cls: "pf-pdf-inline-icon" });
      setPfIcon(warnIcon, "alert-triangle", 13);
      warn.createEl("span", {
        text: t("pdf_prov_changed") || "Source PDF modified",
      });
    }

    // Center: Page Navigation & Zoom (Apple Preview subtle clusters)
    const centerGroup = toolbar.createDiv({ cls: "pf-pdf-toolbar-center" });
    const navCluster = centerGroup.createDiv({ cls: "pf-pdf-nav-cluster" });
    const prevBtn = createPfIconBtn(navCluster, {
      icon: "chevron-left",
      label: lbl("上一页", "Previous page"),
      cls: "pf-pdf-icon-btn",
    });
    const pageInput = navCluster.createEl("input", {
      cls: "pf-pdf-page-input pf-tnum",
      type: "number",
      value: String(this._currentPage),
    });
    pageInput.min = "1";
    pageInput.max = String(totalPages);
    this._pageInputEl = pageInput;
    navCluster.createEl("span", {
      cls: "pf-pdf-page-total pf-tnum",
      text: `/ ${totalPages}`,
    });
    const nextBtn = createPfIconBtn(navCluster, {
      icon: "chevron-right",
      label: lbl("下一页", "Next page"),
      cls: "pf-pdf-icon-btn",
    });

    prevBtn.addEventListener("click", () => {
      this.scrollToPage(Math.max(1, this._currentPage - 1));
    });
    nextBtn.addEventListener("click", () => {
      this.scrollToPage(Math.min(totalPages, this._currentPage + 1));
    });
    pageInput.addEventListener("change", () => {
      const target = Math.max(
        1,
        Math.min(totalPages, Number(pageInput.value) || 1)
      );
      this.scrollToPage(target);
    });

    const zoomCluster = centerGroup.createDiv({ cls: "pf-pdf-zoom-cluster" });
    const zoomOut = createPfIconBtn(zoomCluster, {
      icon: "minus",
      label: lbl("缩小", "Zoom out"),
      cls: "pf-pdf-icon-btn",
    });
    this._zoomLabelEl = zoomCluster.createEl("span", {
      cls: "pf-pdf-zoom-label pf-tnum",
      text: `${Math.round(this._scale * 100)}%`,
    });
    const zoomIn = createPfIconBtn(zoomCluster, {
      icon: "plus",
      label: lbl("放大", "Zoom in"),
      cls: "pf-pdf-icon-btn",
    });
    this._fitWidthBtn = createPfIconBtn(zoomCluster, {
      icon: "maximize-2",
      label: t("pdf_fit_width") || "Zoom to Fit",
      cls: "pf-pdf-icon-btn",
      testid: "pdf-fit-width-btn",
      active: this._fitWidth,
    });

    zoomOut.addEventListener("click", () => {
      this._fitWidth = false;
      this._scale = Math.max(0.6, Math.round((this._scale - 0.15) * 100) / 100);
      this._syncZoomAndRerender();
    });
    zoomIn.addEventListener("click", () => {
      this._fitWidth = false;
      this._scale = Math.min(2.6, Math.round((this._scale + 0.15) * 100) / 100);
      this._syncZoomAndRerender();
    });
    this._fitWidthBtn.addEventListener("click", () => {
      this._fitWidth = !this._fitWidth;
      if (this._fitWidth && this._scrollEl) {
        const w = Math.max(420, (this._scrollEl.clientWidth || 720) - 48);
        this._scale = Math.max(
          0.75,
          Math.min(2.2, Math.round((w / 595) * 100) / 100)
        );
      }
      this._syncZoomAndRerender();
    });

    // Right: Apple Preview Split Highlight + Markup + AI Layer + Note Split + Search
    const rightGroup = toolbar.createDiv({ cls: "pf-pdf-toolbar-right" });

    // Split Highlight Button
    const splitWrap = rightGroup.createDiv({ cls: "pf-pdf-split-highlight" });
    this._splitMainBtn = splitWrap.createEl("button", {
      cls: "pf-pdf-split-main",
      type: "button",
      attr: {
        "data-pf-testid": "pdf-highlight-tool",
        "aria-label": t("pdf_highlight_tool") || "Highlight",
        title: t("pdf_highlight_tool") || "Highlight",
      },
    });
    this._splitMainBtn.addEventListener("click", () => {
      void this._handleSplitHighlightClick();
    });

    const splitCaret = splitWrap.createEl("button", {
      cls: "pf-pdf-split-caret",
      type: "button",
      attr: {
        "data-pf-testid": "pdf-highlight-menu-btn",
        "aria-label": lbl("高亮颜色与样式", "Highlight style menu"),
        title: lbl("高亮颜色与样式", "Highlight style menu"),
      },
    });
    setPfIcon(splitCaret, "chevron-down", 12);
    splitCaret.addEventListener("click", (ev) => {
      ev.stopPropagation();
      this._toggleHighlightDropdown(splitWrap);
    });

    this._markupToggleBtn = createPfIconBtn(rightGroup, {
      icon: "pen-tool",
      label: t("pdf_markup_toggle") || "Show Markup Toolbar",
      cls: "pf-pdf-icon-btn",
      testid: "pdf-markup-toggle",
      active: this._markupOpen,
    });
    this._markupToggleBtn.addEventListener("click", () => {
      this._markupOpen = !this._markupOpen;
      if (!this._markupOpen) {
        this._activeTool = "select";
      }
      this._syncChromeState();
    });

    this._aiToggleBtn = createPfIconBtn(rightGroup, {
      icon: "sparkles",
      label: t("pdf_ai_layer_toggle") || "AI Guide",
      cls: "pf-pdf-icon-btn",
      testid: "pdf-toggle-ai-layer",
      active: this._showAgentLayer,
    });
    this._aiToggleBtn.addEventListener("click", () => {
      this._showAgentLayer = !this._showAgentLayer;
      this._syncChromeState();
      this._refreshOverlays();
      this._renderSidebarBody();
    });

    const splitNoteBtn = createPfIconBtn(rightGroup, {
      icon: "columns-2",
      label: t("pdf_open_note_split") || "Open Note Beside PDF",
      cls: "pf-pdf-icon-btn",
      testid: "pdf-open-note-btn",
    });
    splitNoteBtn.addEventListener("click", () => {
      void this._openNoteSideBySide();
    });

    // Search input
    const searchWrap = rightGroup.createDiv({ cls: "pf-pdf-search-wrap" });
    const searchIcon = searchWrap.createEl("span", {
      cls: "pf-pdf-search-icon",
    });
    setPfIcon(searchIcon, "search", 13);
    const searchInput = searchWrap.createEl("input", {
      cls: "pf-pdf-search-input",
      type: "text",
      placeholder: t("pdf_search_placeholder") || "Search",
    });
    this._searchCountEl = searchWrap.createEl("span", {
      cls: "pf-pdf-search-count pf-tnum",
    });
    searchInput.addEventListener("input", () => {
      this._searchQuery = searchInput.value.trim().toLowerCase();
      void this._runSearch(false);
    });
    searchInput.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") {
        ev.preventDefault();
        void this._runSearch(true, ev.shiftKey ? -1 : 1);
      }
    });

    // Tier 2: Collapsible 36px Apple Preview Markup Bar
    this._markupBarEl = root.createDiv({ cls: "pf-pdf-markup-bar" });
    this._buildMarkupBar(this._markupBarEl);

    // Body: Left Collapsible Sidebar + Central Page Viewport
    const body = root.createDiv({ cls: "pf-pdf-body" });

    this._sidebarEl = body.createDiv({ cls: "pf-pdf-sidebar" });
    const tabHeader = this._sidebarEl.createDiv({ cls: "pf-pdf-sidebar-tabs" });
    const seg = tabHeader.createDiv({ cls: "pf-segmented" });
    const tabs: Array<{ id: SidebarTab; icon: PfIconName; label: string }> = [
      {
        id: "thumbs",
        icon: "layers",
        label: t("pdf_sidebar_thumbs") || "Thumbnails",
      },
      {
        id: "toc",
        icon: "list",
        label: t("pdf_sidebar_toc") || "TOC",
      },
      {
        id: "annotations",
        icon: "highlighter",
        label: t("pdf_sidebar_annotations") || "Annotations",
      },
    ];
    for (const tab of tabs) {
      const btn = seg.createEl("button", {
        cls: `pf-segmented-btn${this._sidebarTab === tab.id ? " is-active" : ""}`,
        type: "button",
        attr: { "data-pf-testid": `pdf-tab-${tab.id}` },
      });
      const ic = btn.createEl("span", { cls: "pf-pdf-tab-icon" });
      setPfIcon(ic, tab.icon, 13);
      btn.createEl("span", { text: tab.label });
      btn.addEventListener("click", () => {
        this._sidebarTab = tab.id;
        seg.querySelectorAll(".pf-segmented-btn").forEach((el) => {
          el.classList.remove("is-active");
        });
        btn.addClass("is-active");
        this._renderSidebarBody();
      });
    }

    this._sidebarContentEl = this._sidebarEl.createDiv({
      cls: "pf-pdf-sidebar-content",
    });

    this._scrollEl = body.createDiv({ cls: "pf-pdf-scroll" });
    this._syncChromeState();
    this._renderSidebarBody();
  }

  private _buildMarkupBar(bar: HTMLElement): void {
    bar.empty();
    const toolsGroup = bar.createDiv({ cls: "pf-pdf-markup-tools" });

    const registerToolBtn = (
      id: string,
      icon: PfIconName,
      label: string,
      testid: string,
      onClick: () => void,
      parent: HTMLElement = toolsGroup
    ) => {
      const btn = createPfIconBtn(parent, {
        icon,
        label,
        cls: "pf-pdf-icon-btn",
        testid,
      });
      this._toolBtns.set(id, btn);
      btn.addEventListener("click", onClick);
      return btn;
    };

    registerToolBtn(
      "select",
      "text-cursor",
      lbl("文本选择", "Text Selection"),
      "pdf-tool-select",
      () => this._setTool("select")
    );
    registerToolBtn(
      "area",
      "box-select",
      t("pdf_area_mode") || "Rectangular Selection",
      "pdf-area-mode-btn",
      () => this._setTool(this._activeTool === "area" ? "select" : "area")
    );
    registerToolBtn(
      "ink",
      "pencil",
      lbl("自由画笔", "Sketch / Ink"),
      "pdf-tool-ink",
      () => this._setTool(this._activeTool === "ink" ? "select" : "ink")
    );

    const shapeCluster = toolsGroup.createDiv({ cls: "pf-pdf-shape-cluster" });

    const shapes: Array<{
      subtype: ShapeSubtype;
      icon: PfIconName;
      zh: string;
      en: string;
    }> = [
      { subtype: "rect", icon: "square", zh: "矩形", en: "Rectangle" },
      { subtype: "ellipse", icon: "circle", zh: "椭圆", en: "Ellipse" },
      { subtype: "arrow", icon: "arrow-up-right", zh: "箭头", en: "Arrow" },
      { subtype: "line", icon: "minus", zh: "直线", en: "Line" },
    ];
    for (const sh of shapes) {
      registerToolBtn(
        `shape:${sh.subtype}`,
        sh.icon,
        lbl(sh.zh, sh.en),
        `pdf-tool-shape-${sh.subtype}`,
        () => {
          if (
            this._activeTool === "shape" &&
            this._shapeSubtype === sh.subtype
          ) {
            this._setTool("select");
          } else {
            this._shapeSubtype = sh.subtype;
            this._setTool("shape");
          }
        },
        shapeCluster
      );
    }

    toolsGroup.createDiv({ cls: "pf-pdf-bar-sep" });

    registerToolBtn(
      "textbox",
      "type",
      lbl("文本框", "Text Box"),
      "pdf-tool-textbox",
      () => this._setTool(this._activeTool === "textbox" ? "select" : "textbox")
    );
    registerToolBtn(
      "note",
      "sticky-note",
      lbl("便签", "Sticky Note"),
      "pdf-tool-note",
      () => this._setTool(this._activeTool === "note" ? "select" : "note")
    );

    const styleGroup = bar.createDiv({ cls: "pf-pdf-markup-styles" });
    for (const sw of MARKUP_STROKE_SWATCHES) {
      const btn = styleGroup.createEl("button", {
        cls: `pf-pdf-mini-swatch${
          this._markupColor === sw.id ? " is-selected" : ""
        }`,
        type: "button",
        attr: {
          "aria-label": lbl(sw.zh, sw.en),
          title: lbl(sw.zh, sw.en),
        },
      });
      btn.style.background = sw.hex;
      btn.addEventListener("click", () => {
        this._markupColor = sw.id;
        this._markupStrokeHex = sw.hex;
        styleGroup
          .querySelectorAll(".pf-pdf-mini-swatch")
          .forEach((el) => el.classList.remove("is-selected"));
        btn.addClass("is-selected");
      });
    }

    styleGroup.createDiv({ cls: "pf-pdf-bar-sep" });

    const fillBtn = styleGroup.createEl("button", {
      cls: `pf-btn pf-btn-ghost pf-pdf-pill-ctrl${
        !this._markupFillTransparent ? " is-active" : ""
      }`,
      type: "button",
      text: lbl("填充", "Fill"),
    });
    fillBtn.addEventListener("click", () => {
      this._markupFillTransparent = !this._markupFillTransparent;
      fillBtn.toggleClass("is-active", !this._markupFillTransparent);
    });

    const widthWrap = styleGroup.createDiv({
      cls: "pf-pdf-width-group pf-pdf-stroke-group",
    });
    for (const w of STROKE_WIDTHS) {
      const wb = widthWrap.createEl("button", {
        cls: `pf-pdf-pill-ctrl pf-pdf-stroke-btn${
          this._markupStrokeWidth === w ? " is-active" : ""
        }`,
        type: "button",
        attr: {
          "aria-label": `${w}pt`,
          title: `${w}pt`,
        },
      });
      const bar = wb.createEl("span", { cls: "pf-stroke-bar" });
      bar.style.height = `${w === 1.5 ? 1.5 : w === 2.5 ? 2.5 : 4}px`;
      wb.addEventListener("click", () => {
        this._markupStrokeWidth = w;
        widthWrap
          .querySelectorAll(".pf-pdf-pill-ctrl")
          .forEach((el) => el.classList.remove("is-active"));
        wb.addClass("is-active");
      });
    }

    const fontWrap = styleGroup.createDiv({
      cls: "pf-pdf-width-group pf-pdf-font-group",
    });
    fontWrap.createEl("span", { cls: "pf-pdf-font-prefix", text: "Aa" });
    for (const fs of TEXTBOX_FONT_SIZES) {
      const fb = fontWrap.createEl("button", {
        cls: `pf-pdf-pill-ctrl pf-tnum${
          this._markupFontSize === fs ? " is-active" : ""
        }`,
        type: "button",
        text: String(fs),
        attr: {
          "aria-label": `${fs}px`,
          title: `${fs}px`,
        },
      });
      fb.addEventListener("click", () => {
        this._markupFontSize = fs;
        fontWrap
          .querySelectorAll(".pf-pdf-pill-ctrl")
          .forEach((el) => el.classList.remove("is-active"));
        fb.addClass("is-active");
      });
    }
  }

  private _setTool(next: MarkupTool): void {
    this._activeTool = next;
    if (next !== "select") {
      this._continuousHighlight = false;
    }
    this._syncChromeState();
  }

  private _syncChromeState(): void {
    if (this._markupBarEl) {
      this._markupBarEl.style.display = this._markupOpen ? "flex" : "none";
    }
    if (this._sidebarEl) {
      this._sidebarEl.style.display = this._sidebarOpen ? "flex" : "none";
    }
    if (this._scrollEl) {
      this._scrollEl.toggleClass("is-area-mode", this._activeTool === "area");
      this._scrollEl.toggleClass("is-ink-mode", this._activeTool === "ink");
      this._scrollEl.toggleClass("is-shape-mode", this._activeTool === "shape");
      this._scrollEl.toggleClass(
        "is-textbox-mode",
        this._activeTool === "textbox"
      );
      this._scrollEl.toggleClass("is-note-mode", this._activeTool === "note");
      this._scrollEl.toggleClass(
        "is-continuous-hl",
        this._continuousHighlight && this._activeTool === "select"
      );
    }

    this._sideToggleBtn?.toggleClass("is-active", this._sidebarOpen);
    this._markupToggleBtn?.toggleClass("is-active", this._markupOpen);
    this._aiToggleBtn?.toggleClass("is-active", this._showAgentLayer);
    this._fitWidthBtn?.toggleClass("is-active", this._fitWidth);

    if (this._splitMainBtn) {
      this._splitMainBtn.empty();
      const iconName: PfIconName =
        this._highlightKind === "underline"
          ? "underline"
          : this._highlightKind === "strikethrough"
            ? "strikethrough"
            : "highlighter";
      const ic = this._splitMainBtn.createEl("span", {
        cls: "pf-pdf-split-ic",
      });
      setPfIcon(ic, iconName, 14);
      const swatchHex =
        PREVIEW_HIGHLIGHT_SWATCHES.find((s) => s.id === this._highlightColor)
          ?.hex ?? "#fde047";
      const dot = this._splitMainBtn.createEl("span", {
        cls: "pf-pdf-split-dot",
      });
      dot.style.background = swatchHex;
      this._splitMainBtn.toggleClass(
        "is-active",
        this._continuousHighlight && this._activeTool === "select"
      );
    }

    this._toolBtns.forEach((btn, key) => {
      if (key.startsWith("shape:")) {
        const sub = key.slice("shape:".length);
        btn.toggleClass(
          "is-active",
          this._activeTool === "shape" && this._shapeSubtype === sub
        );
      } else {
        btn.toggleClass("is-active", this._activeTool === key);
      }
    });
  }

  private _syncZoomAndRerender(): void {
    if (this._zoomLabelEl) {
      this._zoomLabelEl.setText(`${Math.round(this._scale * 100)}%`);
    }
    this._syncChromeState();
    void this._mountPages();
  }

  private _getSelectionData(): {
    pageEl: HTMLElement;
    pageNumber: number;
    rects: number[][];
    exactText: string;
  } | null {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) return null;
    const exactText = sel.toString().trim();
    if (!exactText) return null;
    const range = sel.getRangeAt(0);
    const anchor = range.commonAncestorContainer;
    const anchorEl =
      anchor.nodeType === 1 ? (anchor as HTMLElement) : anchor.parentElement;
    const pageEl = anchorEl?.closest?.(".pf-pdf-page") as HTMLElement | null;
    if (!pageEl) return null;
    const pageNumber = Number(pageEl.getAttribute("data-page-number") || 1);
    const pr = pageEl.getBoundingClientRect();
    const boxes: number[][] = [];
    if (
      pr.width > 0 &&
      pr.height > 0 &&
      typeof range.getClientRects === "function"
    ) {
      const clientRects = Array.from(range.getClientRects());
      for (const r of clientRects) {
        if (r.width < 2 || r.height < 2) continue;
        boxes.push([
          Math.max(0, (r.left - pr.left) / pr.width),
          Math.max(0, (r.top - pr.top) / pr.height),
          Math.min(1, (r.right - pr.left) / pr.width),
          Math.min(1, (r.bottom - pr.top) / pr.height),
        ]);
      }
    }
    if (boxes.length === 0) {
      boxes.push([0.1, 0.15, 0.85, 0.2]);
    }
    return { pageEl, pageNumber, rects: boxes, exactText };
  }

  private async _handleSplitHighlightClick(): Promise<void> {
    const selData = this._getSelectionData();
    if (selData) {
      await this._commitQuickTextMarkup(selData);
      try {
        window.getSelection()?.removeAllRanges();
      } catch {
        // JSDOM selection clearing fallback
      }
      return;
    }
    this._activeTool = "select";
    this._continuousHighlight = !this._continuousHighlight;
    this._syncChromeState();
  }

  private async _commitQuickTextMarkup(selData: {
    pageNumber: number;
    rects: number[][];
    exactText: string;
  }): Promise<void> {
    const key = this._state.paperKey;
    if (!key) return;
    try {
      const saved = await this.plugin.getClient().addAnnotation(key, {
        page: selData.pageNumber,
        rects: selData.rects,
        kind: this._highlightKind,
        color: this._highlightColor,
        intent: "general",
        exact_text: selData.exactText,
        comment: "",
      });
      this._annotations.push(saved);
      this._refreshOverlays();
      this._renderSidebarBody();
    } catch (err) {
      new Notice(err instanceof Error ? err.message : String(err));
    }
  }

  private _toggleHighlightDropdown(anchorEl: HTMLElement): void {
    if (this._highlightMenuEl) {
      this._highlightMenuEl.remove();
      this._highlightMenuEl = null;
      return;
    }
    const menu = this.contentEl.createDiv({
      cls: "pf-pdf-highlight-dropdown",
      attr: { "data-pf-testid": "pdf-highlight-dropdown" },
    });
    this._highlightMenuEl = menu;

    const swatchRow = menu.createDiv({ cls: "pf-pdf-dropdown-swatches" });
    for (const sw of PREVIEW_HIGHLIGHT_SWATCHES) {
      const btn = swatchRow.createEl("button", {
        cls: `pf-pdf-swatch${
          this._highlightKind === "highlight" && this._highlightColor === sw.id
            ? " is-selected"
            : ""
        }`,
        type: "button",
        attr: {
          "data-color": sw.id,
          "aria-label": lbl(sw.zh, sw.en),
          title: lbl(sw.zh, sw.en),
        },
      });
      btn.style.background = sw.hex;
      btn.addEventListener("click", () => {
        this._highlightKind = "highlight";
        this._highlightColor = sw.id;
        menu.remove();
        this._highlightMenuEl = null;
        this._syncChromeState();
        const sel = this._getSelectionData();
        if (sel) {
          void this._commitQuickTextMarkup(sel);
        }
      });
    }

    menu.createDiv({ cls: "pf-pdf-menu-divider" });

    const addStyleRow = (
      kind: HighlightKind,
      icon: PfIconName,
      text: string,
      testid: string
    ) => {
      const row = menu.createEl("button", {
        cls: `pf-pdf-menu-item${this._highlightKind === kind ? " is-selected" : ""}`,
        type: "button",
        attr: { "data-pf-testid": testid },
      });
      const ic = row.createEl("span", { cls: "pf-pdf-menu-ic" });
      setPfIcon(ic, icon, 14);
      row.createEl("span", { text });
      row.addEventListener("click", () => {
        this._highlightKind = kind;
        menu.remove();
        this._highlightMenuEl = null;
        this._syncChromeState();
        const sel = this._getSelectionData();
        if (sel) {
          void this._commitQuickTextMarkup(sel);
        }
      });
    };

    addStyleRow(
      "underline",
      "underline",
      t("pdf_style_underline") || "Underline",
      "pdf-menu-underline"
    );
    addStyleRow(
      "strikethrough",
      "strikethrough",
      t("pdf_style_strikethrough") || "Strikethrough",
      "pdf-menu-strikethrough"
    );

    menu.createDiv({ cls: "pf-pdf-menu-divider" });

    const noteItem = menu.createEl("button", {
      cls: "pf-pdf-menu-item",
      type: "button",
    });
    setPfIcon(
      noteItem.createEl("span", { cls: "pf-pdf-menu-ic" }),
      "sticky-note",
      14
    );
    noteItem.createEl("span", { text: t("pdf_add_note") || "Add Note" });
    noteItem.addEventListener("click", () => {
      menu.remove();
      this._highlightMenuEl = null;
      const sel = this._getSelectionData();
      const targetPageEl = sel?.pageEl ?? this._pageEls.get(this._currentPage);
      if (targetPageEl) {
        this._openCreatePopover({
          anchorEl: targetPageEl,
          page: sel?.pageNumber ?? this._currentPage,
          rects: sel?.rects ?? [[0.12, 0.16, 0.52, 0.2]],
          kind: sel ? this._highlightKind : "note",
          exactText: sel?.exactText ?? "",
        });
      }
    });

    const rect = anchorEl.getBoundingClientRect();
    if (rect.width > 0) {
      menu.style.top = `${Math.round(rect.bottom + 6)}px`;
      menu.style.right = `${Math.max(12, Math.round(window.innerWidth - rect.right))}px`;
    }
  }

  private async _openNoteSideBySide(): Promise<void> {
    const noteRel = this._ctx?.note_rel_path;
    if (!noteRel) {
      new Notice(t("paper_note_missing") || "Reading note path unavailable.");
      return;
    }
    const af = this.app.vault.getAbstractFileByPath(noteRel);
    if (af instanceof TFile) {
      const leaf = this.app.workspace.getLeaf("split");
      await leaf.openFile(af);
      return;
    }
    await this.app.workspace.openLinkText(noteRel, "", "split");
  }

  private async _mountPages(): Promise<void> {
    if (!this._doc || !this._scrollEl) return;
    if (this._observer) {
      this._observer.disconnect();
      this._observer = null;
    }
    this._renderedPages.clear();
    this._renderingPages.clear();
    this._pageEls.clear();
    this._scrollEl.empty();

    const totalPages = this._doc.numPages;
    const firstPage = await this._doc.getPage(1);
    const defaultVp = firstPage.getViewport({ scale: this._scale });
    const estW = Math.max(300, Math.round(defaultVp.width));
    const estH = Math.max(400, Math.round(defaultVp.height));

    for (let p = 1; p <= totalPages; p++) {
      const wrap = this._scrollEl.createDiv({
        cls: "pf-pdf-page",
        attr: { "data-page-number": String(p) },
      });
      wrap.style.width = `${estW}px`;
      wrap.style.height = `${estH}px`;
      wrap.createDiv({ cls: "pf-pdf-text-layer" });
      wrap.createDiv({ cls: "pf-pdf-overlay-layer" });
      this._pageEls.set(p, wrap);
      this._attachPageInteractions(wrap, p);
    }

    if (typeof IntersectionObserver !== "undefined") {
      this._observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (!entry.isIntersecting) continue;
            const p = Number(
              (entry.target as HTMLElement).getAttribute("data-page-number")
            );
            if (p >= 1) {
              this._currentPage = p;
              if (this._pageInputEl) {
                this._pageInputEl.value = String(p);
              }
              this._highlightActiveThumb();
              void this._ensurePageRendered(p);
              if (p + 1 <= totalPages) void this._ensurePageRendered(p + 1);
            }
          }
        },
        { root: this._scrollEl, threshold: 0.15 }
      );
      this._pageEls.forEach((el) => this._observer?.observe(el));
    }

    const startPage = this._currentPage || 1;
    await this._ensurePageRendered(startPage);
    if (startPage + 1 <= totalPages) {
      await this._ensurePageRendered(startPage + 1);
    }
    this._refreshOverlays();
    if (this._sidebarTab === "thumbs") {
      this._renderSidebarBody();
    }
  }

  private async _ensurePageRendered(pageNumber: number): Promise<void> {
    if (
      !this._doc ||
      this._renderedPages.has(pageNumber) ||
      this._renderingPages.has(pageNumber)
    ) {
      return;
    }
    const pageEl = this._pageEls.get(pageNumber);
    if (!pageEl) return;
    this._renderingPages.add(pageNumber);
    try {
      const page = await this._doc.getPage(pageNumber);
      const viewport = page.getViewport({ scale: this._scale });
      pageEl.style.width = `${Math.round(viewport.width)}px`;
      pageEl.style.height = `${Math.round(viewport.height)}px`;

      const overlayLayer = pageEl.querySelector(".pf-pdf-overlay-layer");
      pageEl.querySelector(".pf-pdf-canvas")?.remove();
      const canvas = document.createElement("canvas");
      canvas.className = "pf-pdf-canvas";
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.round(viewport.width * dpr));
      canvas.height = Math.max(1, Math.round(viewport.height * dpr));
      canvas.style.width = `${Math.round(viewport.width)}px`;
      canvas.style.height = `${Math.round(viewport.height)}px`;
      if (overlayLayer) {
        pageEl.insertBefore(canvas, overlayLayer);
      } else {
        pageEl.appendChild(canvas);
      }

      const ctx2d = canvas.getContext("2d");
      if (ctx2d) {
        if (typeof ctx2d.setTransform === "function") {
          ctx2d.setTransform(dpr, 0, 0, dpr, 0, 0);
        }
        await page.render({ canvasContext: ctx2d, viewport }).promise;
      }

      const textLayer = pageEl.querySelector(
        ".pf-pdf-text-layer"
      ) as HTMLElement | null;
      if (textLayer) {
        textLayer.empty();
        const textContent = await page.getTextContent();
        const plainChunks: string[] = [];
        for (const item of textContent.items || []) {
          if (!item.str) continue;
          plainChunks.push(item.str);
          const span = document.createElement("span");
          span.textContent = item.str;
          const tx = item.transform;
          if (tx && tx.length >= 6 && (viewport.transform?.length ?? 0) >= 6) {
            const x = tx[4] * this._scale;
            const y = viewport.height - tx[5] * this._scale;
            const fontH = Math.max(8, Math.abs(tx[3] || 10) * this._scale);
            span.style.left = `${x}px`;
            span.style.top = `${Math.max(0, y - fontH)}px`;
            span.style.fontSize = `${fontH}px`;
          }
          textLayer.appendChild(span);
        }
        this._pageTexts.set(pageNumber, plainChunks.join(" "));
      }

      this._renderedPages.add(pageNumber);
      this._renderPageOverlays(pageNumber, pageEl);
      if (this._sidebarTab === "thumbs") {
        this._updateThumbPreview(pageNumber, canvas);
      }
    } finally {
      this._renderingPages.delete(pageNumber);
    }
  }

  private _attachPageInteractions(
    pageEl: HTMLElement,
    pageNumber: number
  ): void {
    // Selection-first continuous highlight ONLY when pen mode active; plain reading shows zero popup
    pageEl.addEventListener("mouseup", () => {
      if (this._activeTool !== "select" || !this._continuousHighlight) return;
      const selData = this._getSelectionData();
      if (!selData || selData.pageNumber !== pageNumber) return;
      void this._commitQuickTextMarkup(selData);
      try {
        window.getSelection()?.removeAllRanges();
      } catch {
        // Ignore JSDOM selection reset differences
      }
    });

    let dragStart: { x: number; y: number } | null = null;
    let marqueeEl: HTMLElement | null = null;
    let inkPoints: number[][] = [];
    let draftSvg: SVGSVGElement | null = null;

    const toNorm = (ev: MouseEvent): [number, number] | null => {
      const pr = pageEl.getBoundingClientRect();
      if (pr.width <= 0 || pr.height <= 0) return null;
      return [
        Math.max(0, Math.min(1, (ev.clientX - pr.left) / pr.width)),
        Math.max(0, Math.min(1, (ev.clientY - pr.top) / pr.height)),
      ];
    };

    pageEl.addEventListener("mousedown", (ev) => {
      const targetEl = ev.target as HTMLElement | null;
      if (targetEl?.closest?.(".pf-pdf-inline-textbox")) return;
      if (this._activeTool === "select") return;
      const pt = toNorm(ev);
      if (!pt) return;

      if (this._activeTool === "note") {
        ev.preventDefault();
        this._openCreatePopover({
          anchorEl: pageEl,
          page: pageNumber,
          rects: [
            [
              pt[0],
              pt[1],
              Math.min(0.98, pt[0] + 0.03),
              Math.min(0.98, pt[1] + 0.03),
            ],
          ],
          kind: "note",
          exactText: "",
        });
        return;
      }

      if (this._activeTool === "textbox") {
        ev.preventDefault();
        this._spawnInlineTextbox(pageEl, pageNumber, pt[0], pt[1]);
        return;
      }

      if (this._activeTool === "area") {
        ev.preventDefault();
        this._areaFloatEl?.remove();
        this._areaFloatEl = null;
        dragStart = { x: pt[0], y: pt[1] };
        marqueeEl = pageEl.createDiv({ cls: "pf-pdf-marquee" });
        return;
      }

      if (this._activeTool === "ink" || this._activeTool === "shape") {
        ev.preventDefault();
        dragStart = { x: pt[0], y: pt[1] };
        inkPoints = [pt];
        draftSvg = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "svg"
        );
        draftSvg.setAttribute("class", "pf-pdf-svg-draft");
        draftSvg.setAttribute("viewBox", "0 0 1000 1000");
        draftSvg.setAttribute("preserveAspectRatio", "none");
        pageEl.appendChild(draftSvg);
      }
    });

    pageEl.addEventListener("mousemove", (ev) => {
      if (!dragStart) return;
      const pt = toNorm(ev);
      if (!pt) return;

      if (marqueeEl && this._activeTool === "area") {
        const x0 = Math.min(dragStart.x, pt[0]);
        const y0 = Math.min(dragStart.y, pt[1]);
        const x1 = Math.max(dragStart.x, pt[0]);
        const y1 = Math.max(dragStart.y, pt[1]);
        marqueeEl.style.left = `${x0 * 100}%`;
        marqueeEl.style.top = `${y0 * 100}%`;
        marqueeEl.style.width = `${(x1 - x0) * 100}%`;
        marqueeEl.style.height = `${(y1 - y0) * 100}%`;
        return;
      }

      if (draftSvg && this._activeTool === "ink") {
        inkPoints.push(pt);
        draftSvg.innerHTML = "";
        const pl = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "polyline"
        );
        pl.setAttribute(
          "points",
          inkPoints.map((p) => `${p[0] * 1000},${p[1] * 1000}`).join(" ")
        );
        pl.setAttribute("fill", "none");
        pl.setAttribute("stroke", this._markupStrokeHex);
        pl.setAttribute("stroke-width", String(this._markupStrokeWidth * 2));
        pl.setAttribute("stroke-linecap", "round");
        pl.setAttribute("stroke-linejoin", "round");
        draftSvg.appendChild(pl);
        return;
      }

      if (draftSvg && this._activeTool === "shape") {
        draftSvg.innerHTML = "";
        this._renderSvgShape(draftSvg, this._shapeSubtype, {
          rect: [
            Math.min(dragStart.x, pt[0]),
            Math.min(dragStart.y, pt[1]),
            Math.max(dragStart.x, pt[0]),
            Math.max(dragStart.y, pt[1]),
          ],
          points: [
            [dragStart.x, dragStart.y],
            [pt[0], pt[1]],
          ],
          stroke: this._markupStrokeHex,
          fill: this._markupFillTransparent
            ? "none"
            : `${this._markupStrokeHex}26`,
          strokeWidth: this._markupStrokeWidth,
          idSeed: "draft",
        });
      }
    });

    pageEl.addEventListener("mouseup", (ev) => {
      if (!dragStart) return;
      const start = dragStart;
      dragStart = null;
      const mEl = marqueeEl;
      marqueeEl = null;
      const dSvg = draftSvg;
      draftSvg = null;
      const pt = toNorm(ev);
      if (!pt) {
        mEl?.remove();
        dSvg?.remove();
        return;
      }

      const x0 = Math.min(start.x, pt[0]);
      const y0 = Math.min(start.y, pt[1]);
      const x1 = Math.max(start.x, pt[0]);
      const y1 = Math.max(start.y, pt[1]);

      if (this._activeTool === "area") {
        mEl?.remove();
        if (x1 - x0 < 0.015 || y1 - y0 < 0.015) return;
        this._showAreaFloatActions(pageEl, pageNumber, [x0, y0, x1, y1]);
        return;
      }

      if (this._activeTool === "ink") {
        dSvg?.remove();
        if (inkPoints.length < 2) return;
        const xs = inkPoints.map((p) => p[0]);
        const ys = inkPoints.map((p) => p[1]);
        const bbox: [number, number, number, number] = [
          Math.min(...xs),
          Math.min(...ys),
          Math.max(...xs),
          Math.max(...ys),
        ];
        void this._saveMarkupAnnotation(pageNumber, [bbox], "ink", {
          points: inkPoints,
          stroke_color: this._markupStrokeHex,
          stroke_width: this._markupStrokeWidth,
        });
        return;
      }

      if (this._activeTool === "shape") {
        dSvg?.remove();
        if (
          Math.abs(pt[0] - start.x) < 0.01 &&
          Math.abs(pt[1] - start.y) < 0.01
        ) {
          return;
        }
        const style: AnnotationStyleDto = {
          shape_type: this._shapeSubtype,
          stroke_color: this._markupStrokeHex,
          fill_color: this._markupFillTransparent
            ? "transparent"
            : `${this._markupStrokeHex}26`,
          stroke_width: this._markupStrokeWidth,
          points: [
            [start.x, start.y],
            [pt[0], pt[1]],
          ],
        };
        void this._saveMarkupAnnotation(
          pageNumber,
          [[x0, y0, Math.max(x1, x0 + 0.005), Math.max(y1, y0 + 0.005)]],
          "shape",
          style
        );
      }
    });
  }

  private async _saveMarkupAnnotation(
    page: number,
    rects: number[][],
    kind: AnnotationKind,
    style: AnnotationStyleDto,
    comment = ""
  ): Promise<void> {
    const key = this._state.paperKey;
    if (!key) return;
    try {
      const saved = await this.plugin.getClient().addAnnotation(key, {
        page,
        rects,
        kind,
        color: kind === "textbox" ? "transparent" : this._markupColor,
        intent: "general",
        exact_text: "",
        comment,
        style,
      });
      this._annotations.push(saved);
      this._refreshOverlays();
      this._renderSidebarBody();
    } catch (err) {
      new Notice(err instanceof Error ? err.message : String(err));
    }
  }

  private _spawnInlineTextbox(
    pageEl: HTMLElement,
    pageNumber: number,
    nx: number,
    ny: number
  ): void {
    pageEl.querySelector(".pf-pdf-inline-textbox")?.remove();
    const ta = pageEl.createEl("textarea", {
      cls: "pf-pdf-inline-textbox",
      placeholder: lbl(
        "输入批注文字 (Enter 保存)…",
        "Type text (Enter to save)…"
      ),
      attr: { "data-pf-testid": "pdf-inline-textbox" },
    });
    ta.style.left = `${Math.min(75, Math.round(nx * 100))}%`;
    ta.style.top = `${Math.min(90, Math.round(ny * 100))}%`;
    ta.style.fontSize = `${this._markupFontSize}px`;
    ta.style.color = this._markupStrokeHex;
    ta.focus();

    let committed = false;
    const commit = async () => {
      if (committed) return;
      committed = true;
      const val = ta.value.trim();
      ta.remove();
      if (!val) return;
      await this._saveMarkupAnnotation(
        pageNumber,
        [[nx, ny, Math.min(0.96, nx + 0.25), Math.min(0.96, ny + 0.07)]],
        "textbox",
        {
          font_size: this._markupFontSize,
          stroke_color: this._markupStrokeHex,
        },
        val
      );
    };

    ta.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && !ev.shiftKey) {
        ev.preventDefault();
        void commit();
      } else if (ev.key === "Escape") {
        committed = true;
        ta.remove();
      }
    });
    ta.addEventListener("blur", () => {
      void commit();
    });
  }

  private _showAreaFloatActions(
    pageEl: HTMLElement,
    pageNumber: number,
    rect: [number, number, number, number]
  ): void {
    this._areaFloatEl?.remove();
    const floatEl = pageEl.createDiv({
      cls: "pf-pdf-area-float",
      attr: { "data-pf-testid": "pdf-area-float" },
    });
    this._areaFloatEl = floatEl;
    floatEl.style.left = `${Math.min(72, Math.round(rect[0] * 100))}%`;
    floatEl.style.top = `${Math.min(92, Math.round(rect[3] * 100 + 1))}%`;

    const saveCrop = async (copyToClip: boolean) => {
      floatEl.remove();
      this._areaFloatEl = null;
      const key = this._state.paperKey;
      if (!key) return;
      try {
        const saved = await this.plugin.getClient().addAnnotation(key, {
          page: pageNumber,
          rects: [rect],
          kind: "area",
          color: this._highlightColor,
          intent: "general",
        });
        this._annotations.push(saved);
        this._refreshOverlays();
        this._renderSidebarBody();
        if (copyToClip) {
          const payload =
            saved.embed_wikilink || this._buildCitationText(saved);
          if (payload && navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(payload);
            new Notice(t("pdf_crop_copied") || "Selection copied");
          }
        } else {
          new Notice(t("pdf_ann_saved") || "Area saved");
        }
      } catch (err) {
        new Notice(err instanceof Error ? err.message : String(err));
      }
    };

    const copyImgBtn = floatEl.createEl("button", {
      cls: "pf-btn pf-btn-primary",
      type: "button",
      text: lbl("插入笔记引用", "Copy Image Link"),
    });
    copyImgBtn.addEventListener("click", () => {
      void saveCrop(true);
    });

    const saveBtn = floatEl.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      type: "button",
      text: lbl("存为框选", "Save Area"),
    });
    saveBtn.addEventListener("click", () => {
      void saveCrop(false);
    });

    const noteBtn = floatEl.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      type: "button",
      text: t("pdf_add_note") || "Add Note",
    });
    noteBtn.addEventListener("click", () => {
      floatEl.remove();
      this._areaFloatEl = null;
      this._openCreatePopover({
        anchorEl: pageEl,
        page: pageNumber,
        rects: [rect],
        kind: "area",
        exactText: "",
      });
    });

    const cancelBtn = createPfIconBtn(floatEl, {
      icon: "x",
      label: lbl("取消", "Cancel"),
      cls: "pf-pdf-icon-btn",
    });
    cancelBtn.addEventListener("click", () => {
      floatEl.remove();
      this._areaFloatEl = null;
    });
  }

  /** Open floating color + note popover and persist via backend authority. */
  public _openCreatePopover(params: {
    anchorEl: HTMLElement;
    page: number;
    rects: number[][];
    kind: AnnotationKind;
    exactText: string;
    existingAnn?: PdfAnnotationDto;
  }): void {
    this._popoverEl?.remove();
    const pop = this.contentEl.createDiv({
      cls: "pf-pdf-popover",
      attr: { "data-pf-testid": "pdf-create-popover" },
    });
    this._popoverEl = pop;
    this._popoverColor =
      (params.existingAnn?.color as AnnotationColor) || this._highlightColor;

    const header = pop.createDiv({ cls: "pf-pdf-popover-header" });
    header.createEl("span", {
      cls: "pf-pdf-popover-title",
      text: params.existingAnn
        ? lbl(`编辑第 ${params.page} 页批注`, `Edit Note (p.${params.page})`)
        : params.kind === "area"
          ? lbl(
              `第 ${params.page} 页框选批注`,
              `Area Selection (p.${params.page})`
            )
          : lbl(
              `第 ${params.page} 页高亮与笔记`,
              `Highlight & Note (p.${params.page})`
            ),
    });
    const closeIcon = createPfIconBtn(header, {
      icon: "x",
      label: lbl("关闭", "Close"),
      cls: "pf-pdf-icon-btn",
    });

    const swatchRow = pop.createDiv({ cls: "pf-pdf-swatch-row" });
    for (const sw of PREVIEW_HIGHLIGHT_SWATCHES) {
      const btn = swatchRow.createEl("button", {
        cls: `pf-pdf-swatch${this._popoverColor === sw.id ? " is-selected" : ""}`,
        type: "button",
        attr: {
          "data-color": sw.id,
          "aria-label": lbl(sw.zh, sw.en),
          title: lbl(sw.zh, sw.en),
        },
      });
      btn.style.background = sw.hex;
      btn.addEventListener("click", () => {
        this._popoverColor = sw.id;
        swatchRow
          .querySelectorAll(".pf-pdf-swatch")
          .forEach((b) => b.classList.remove("is-selected"));
        btn.addClass("is-selected");
      });
    }

    if (params.exactText) {
      pop.createEl("div", {
        cls: "pf-pdf-popover-quote",
        text:
          params.exactText.length > 140
            ? `${params.exactText.slice(0, 140)}…`
            : params.exactText,
      });
    }

    const commentBox = pop.createEl("textarea", {
      cls: "pf-pdf-popover-comment",
      placeholder: t("pdf_comment_placeholder") || "Write a note...",
    });
    commentBox.value = params.existingAnn?.comment ?? "";
    commentBox.rows = 3;

    const actions = pop.createDiv({ cls: "pf-pdf-popover-actions" });
    const cancelBtn = actions.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      type: "button",
      text: t("wizard_cancel") || "Cancel",
    });
    const saveBtn = actions.createEl("button", {
      cls: "pf-btn pf-btn-primary",
      type: "button",
      text: t("pdf_save_annotation") || "Save",
      attr: { "data-pf-testid": "pdf-save-ann-btn" },
    });

    const closePop = () => {
      pop.remove();
      this._popoverEl = null;
    };
    closeIcon.addEventListener("click", closePop);
    cancelBtn.addEventListener("click", closePop);

    saveBtn.addEventListener("click", () => {
      void (async () => {
        saveBtn.disabled = true;
        try {
          const client = this.plugin.getClient();
          const key = this._state.paperKey;
          if (params.existingAnn) {
            const upd = await client.updateAnnotation(
              key,
              params.existingAnn.ann_id,
              {
                color: this._popoverColor,
                comment: commentBox.value.trim(),
              }
            );
            const idx = this._annotations.findIndex(
              (a) => a.ann_id === upd.ann_id
            );
            if (idx >= 0) this._annotations[idx] = upd;
          } else {
            const saved = await client.addAnnotation(key, {
              page: params.page,
              rects: params.rects,
              kind: params.kind,
              color: this._popoverColor,
              intent: "general",
              exact_text: params.exactText,
              comment: commentBox.value.trim(),
            });
            this._annotations.push(saved);
            if (saved.embed_wikilink && navigator.clipboard?.writeText) {
              try {
                await navigator.clipboard.writeText(saved.embed_wikilink);
                new Notice(t("pdf_crop_copied") || "Copied embed link");
              } catch {
                // Clipboard non-critical
              }
            }
          }
          closePop();
          this._refreshOverlays();
          this._renderSidebarBody();
        } catch (err) {
          saveBtn.disabled = false;
          new Notice(err instanceof Error ? err.message : String(err));
        }
      })();
    });
  }

  private _refreshOverlays(): void {
    this._pageEls.forEach((pageEl, pageNumber) => {
      this._renderPageOverlays(pageNumber, pageEl);
    });
  }

  private _renderPageOverlays(pageNumber: number, pageEl: HTMLElement): void {
    const layer = pageEl.querySelector(
      ".pf-pdf-overlay-layer"
    ) as HTMLElement | null;
    if (!layer) return;
    layer.empty();

    const pageAnns = this._annotations.filter((ann) => {
      if (ann.page !== pageNumber) return false;
      if (ann.author === "agent" && !this._showAgentLayer) return false;
      return true;
    });

    const needsSvg = pageAnns.some(
      (a) => a.kind === "shape" || a.kind === "ink"
    );
    let svgEl: SVGSVGElement | null = null;
    if (needsSvg) {
      svgEl = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svgEl.setAttribute("class", "pf-pdf-svg-layer");
      svgEl.setAttribute("viewBox", "0 0 1000 1000");
      svgEl.setAttribute("preserveAspectRatio", "none");
      layer.appendChild(svgEl);
    }

    for (const ann of pageAnns) {
      if (ann.kind === "ink" && svgEl) {
        const pts = ann.style?.points || [];
        if (pts.length >= 2) {
          const pl = document.createElementNS(
            "http://www.w3.org/2000/svg",
            "polyline"
          );
          pl.setAttribute(
            "points",
            pts.map((p) => `${p[0] * 1000},${p[1] * 1000}`).join(" ")
          );
          pl.setAttribute("fill", "none");
          pl.setAttribute("stroke", ann.style?.stroke_color || "#d64545");
          pl.setAttribute(
            "stroke-width",
            String((ann.style?.stroke_width || 2) * 2)
          );
          pl.setAttribute("stroke-linecap", "round");
          pl.setAttribute("stroke-linejoin", "round");
          svgEl.appendChild(pl);
        }
        continue;
      }

      if (ann.kind === "shape" && svgEl) {
        const r = ann.rects?.[0] ?? [0.1, 0.1, 0.3, 0.3];
        this._renderSvgShape(svgEl, ann.style?.shape_type || "rect", {
          rect: [r[0], r[1], r[2], r[3]],
          points: ann.style?.points,
          stroke: ann.style?.stroke_color || "#d64545",
          fill:
            !ann.style?.fill_color || ann.style.fill_color === "transparent"
              ? "none"
              : ann.style.fill_color,
          strokeWidth: ann.style?.stroke_width || 2,
          idSeed: ann.ann_id,
        });
        continue;
      }

      const boxClasses = [
        "pf-pdf-ann-box",
        `pf-pdf-ann--${ann.color || "yellow"}`,
        `pf-pdf-ann-kind--${ann.kind}`,
      ];
      if (ann.author === "agent") boxClasses.push("pf-pdf-hl-agent");
      if (ann.kind === "margin") boxClasses.push("pf-pdf-margin-bracket");

      for (const rect of ann.rects || []) {
        const box = layer.createDiv({
          cls: boxClasses.join(" "),
          attr: { "data-ann-id": ann.ann_id },
        });
        box.style.left = `${rect[0] * 100}%`;
        box.style.top = `${rect[1] * 100}%`;
        box.style.width = `${Math.max(0.5, (rect[2] - rect[0]) * 100)}%`;
        box.style.height = `${Math.max(0.5, (rect[3] - rect[1]) * 100)}%`;

        if (ann.kind === "textbox") {
          box.setText(ann.comment || ann.exact_text || "");
          box.style.fontSize = `${ann.style?.font_size || 14}px`;
          box.style.color = ann.style?.stroke_color || "#1c1b19";
        } else if (ann.kind === "note") {
          setPfIcon(box, "sticky-note", 14);
          box.title = ann.comment || lbl("便签批注", "Sticky Note");
        }

        box.addEventListener("click", (ev) => {
          ev.stopPropagation();
          this._openCreatePopover({
            anchorEl: pageEl,
            page: ann.page,
            rects: ann.rects,
            kind: ann.kind,
            exactText: ann.exact_text,
            existingAnn: ann,
          });
        });
      }
    }
  }

  private _renderSvgShape(
    svg: SVGSVGElement,
    shapeType: ShapeSubtype,
    opts: {
      rect: [number, number, number, number];
      points?: number[][];
      stroke: string;
      fill: string;
      strokeWidth: number;
      idSeed: string;
    }
  ): void {
    const [x0, y0, x1, y1] = opts.rect;
    const sw = String(opts.strokeWidth * 2);
    if (shapeType === "rect") {
      const el = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      el.setAttribute("x", String(x0 * 1000));
      el.setAttribute("y", String(y0 * 1000));
      el.setAttribute("width", String(Math.max(4, (x1 - x0) * 1000)));
      el.setAttribute("height", String(Math.max(4, (y1 - y0) * 1000)));
      el.setAttribute("rx", "4");
      el.setAttribute("stroke", opts.stroke);
      el.setAttribute("fill", opts.fill);
      el.setAttribute("stroke-width", sw);
      svg.appendChild(el);
      return;
    }
    if (shapeType === "ellipse") {
      const el = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "ellipse"
      );
      el.setAttribute("cx", String(((x0 + x1) / 2) * 1000));
      el.setAttribute("cy", String(((y0 + y1) / 2) * 1000));
      el.setAttribute("rx", String(Math.max(4, ((x1 - x0) / 2) * 1000)));
      el.setAttribute("ry", String(Math.max(4, ((y1 - y0) / 2) * 1000)));
      el.setAttribute("stroke", opts.stroke);
      el.setAttribute("fill", opts.fill);
      el.setAttribute("stroke-width", sw);
      svg.appendChild(el);
      return;
    }

    const p0 = opts.points?.[0] ?? [x0, y0];
    const p1 = opts.points?.[1] ?? [x1, y1];
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", String(p0[0] * 1000));
    line.setAttribute("y1", String(p0[1] * 1000));
    line.setAttribute("x2", String(p1[0] * 1000));
    line.setAttribute("y2", String(p1[1] * 1000));
    line.setAttribute("stroke", opts.stroke);
    line.setAttribute("stroke-width", sw);
    line.setAttribute("stroke-linecap", "round");
    if (shapeType === "arrow") {
      const markerId = `pf-arr-${opts.idSeed}`;
      const defs = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "defs"
      );
      const marker = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "marker"
      );
      marker.setAttribute("id", markerId);
      marker.setAttribute("markerWidth", "10");
      marker.setAttribute("markerHeight", "10");
      marker.setAttribute("refX", "7");
      marker.setAttribute("refY", "3");
      marker.setAttribute("orient", "auto");
      const arrowPath = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "path"
      );
      arrowPath.setAttribute("d", "M0,0 L8,3 L0,6 Z");
      arrowPath.setAttribute("fill", opts.stroke);
      marker.appendChild(arrowPath);
      defs.appendChild(marker);
      svg.appendChild(defs);
      line.setAttribute("marker-end", `url(#${markerId})`);
    }
    svg.appendChild(line);
  }

  private _renderSidebarBody(): void {
    const container = this._sidebarContentEl;
    if (!container) return;
    container.empty();
    if (this._sidebarTab === "thumbs") {
      this._renderThumbsTab(container);
    } else if (this._sidebarTab === "toc") {
      this._renderTocTab(container);
    } else {
      this._renderAnnotationsTab(container);
    }
  }

  private _renderThumbsTab(container: HTMLElement): void {
    this._thumbEls.clear();
    const total = this._doc?.numPages || this._ctx?.page_count || 1;
    const grid = container.createDiv({ cls: "pf-pdf-thumb-grid" });
    for (let p = 1; p <= total; p++) {
      const card = grid.createDiv({
        cls: `pf-pdf-thumb-item${p === this._currentPage ? " is-active" : ""}`,
        attr: { "data-page": String(p) },
      });
      const preview = card.createDiv({ cls: "pf-pdf-thumb-preview" });
      const pageEl = this._pageEls.get(p);
      const canvas = pageEl?.querySelector(
        ".pf-pdf-canvas"
      ) as HTMLCanvasElement | null;
      if (canvas) {
        this._paintThumbInto(preview, canvas);
      } else {
        preview.createEl("span", {
          cls: "pf-tnum pf-pdf-thumb-ph",
          text: `P${p}`,
        });
      }
      card.createEl("span", { cls: "pf-pdf-thumb-num pf-tnum", text: `${p}` });
      card.addEventListener("click", () => {
        this.scrollToPage(p);
      });
      this._thumbEls.set(p, card);
    }
  }

  private _paintThumbInto(
    previewEl: HTMLElement,
    srcCanvas: HTMLCanvasElement
  ): void {
    if (typeof srcCanvas.toDataURL !== "function") return;
    try {
      const dataUrl = srcCanvas.toDataURL();
      if (!dataUrl || dataUrl === "data:,") return;
      previewEl.empty();
      const img = previewEl.createEl("img", { cls: "pf-pdf-thumb-img" });
      img.src = dataUrl;
    } catch {
      // Ignore tainted or mock canvases
    }
  }

  private _updateThumbPreview(
    pageNumber: number,
    srcCanvas: HTMLCanvasElement
  ): void {
    const card = this._thumbEls.get(pageNumber);
    const preview = card?.querySelector(
      ".pf-pdf-thumb-preview"
    ) as HTMLElement | null;
    if (preview) {
      this._paintThumbInto(preview, srcCanvas);
    }
  }

  private _highlightActiveThumb(): void {
    this._thumbEls.forEach((el, page) => {
      el.toggleClass("is-active", page === this._currentPage);
    });
  }

  private async _loadTocOutline(): Promise<void> {
    const items: Array<{ title: string; page: number; depth: number }> = [];
    const doc = this._doc;
    if (doc && typeof doc.getOutline === "function") {
      try {
        const outline = await doc.getOutline();
        const walk = async (
          nodes: PdfOutlineItem[] | null | undefined,
          depth: number
        ) => {
          if (!nodes) return;
          for (const node of nodes) {
            let pageNum = 1;
            try {
              if (
                Array.isArray(node.dest) &&
                node.dest[0] &&
                doc.getPageIndex
              ) {
                pageNum = (await doc.getPageIndex(node.dest[0])) + 1;
              } else if (
                typeof node.dest === "string" &&
                doc.getDestination &&
                doc.getPageIndex
              ) {
                const resolved = await doc.getDestination(node.dest);
                if (resolved?.[0]) {
                  pageNum = (await doc.getPageIndex(resolved[0])) + 1;
                }
              }
            } catch {
              pageNum = 1;
            }
            if (node.title) {
              items.push({ title: node.title, page: pageNum, depth });
            }
            await walk(node.items, depth + 1);
          }
        };
        await walk(outline, 0);
      } catch {
        // Fallback below
      }
    }
    if (items.length === 0 && this._annotations.length > 0) {
      const seen = new Set<string>();
      for (const ann of this._annotations) {
        if (ann.section_path && !seen.has(ann.section_path)) {
          seen.add(ann.section_path);
          items.push({ title: ann.section_path, page: ann.page, depth: 0 });
        }
      }
    }
    this._tocItems = items;
    if (this._sidebarTab === "toc") {
      this._renderSidebarBody();
    }
  }

  private _renderTocTab(container: HTMLElement): void {
    if (this._tocItems.length === 0) {
      container.createDiv({
        cls: "pf-pdf-sidebar-empty",
        text: lbl(
          "该 PDF 暂无嵌入大纲目录",
          "No outline sections found in this PDF."
        ),
      });
      return;
    }
    const list = container.createDiv({ cls: "pf-pdf-toc-list" });
    for (const item of this._tocItems) {
      const row = list.createEl("button", {
        cls: "pf-pdf-toc-row",
        type: "button",
      });
      row.style.paddingLeft = `${10 + item.depth * 14}px`;
      row.createEl("span", { cls: "pf-pdf-toc-title", text: item.title });
      row.createEl("span", {
        cls: "pf-pdf-toc-page pf-tnum",
        text: `P${item.page}`,
      });
      row.addEventListener("click", () => {
        this.scrollToPage(item.page);
      });
    }
  }

  private _renderAnnotationsTab(container: HTMLElement): void {
    const filterBar = container.createDiv({ cls: "pf-pdf-filter-bar" });
    const authorSeg = filterBar.createDiv({ cls: "pf-segmented" });
    const agentCount = this._annotations.filter(
      (a) => a.author === "agent"
    ).length;
    const authorChips: Array<{ id: AuthorFilter; label: string }> = [
      { id: "all", label: t("pdf_filter_all") || "All" },
      { id: "user", label: t("pdf_filter_mine") || "Mine" },
      {
        id: "agent",
        label: `${t("pdf_filter_ai") || "AI Guide"} (${agentCount})`,
      },
    ];
    for (const ch of authorChips) {
      const btn = authorSeg.createEl("button", {
        cls: `pf-segmented-btn${this._authorFilter === ch.id ? " is-active" : ""}`,
        type: "button",
        text: ch.label,
        attr: { "data-pf-testid": `pdf-author-filter-${ch.id}` },
      });
      btn.addEventListener("click", () => {
        this._authorFilter = ch.id;
        this._renderSidebarBody();
      });
    }

    if (agentCount > 0) {
      this._clearAiBtn = filterBar.createEl("button", {
        cls: "pf-btn pf-btn-ghost pf-pdf-clear-ai-btn",
        type: "button",
        text: t("pdf_clear_ai_btn") || "Clear AI",
        attr: { "data-pf-testid": "pdf-clear-ai-btn" },
      });
      this._clearAiBtn.addEventListener("click", () => {
        void (async () => {
          const res = await this.plugin
            .getClient()
            .clearAgentAnnotations(this._state.paperKey);
          this._annotations = this._annotations.filter(
            (a) => a.author !== "agent"
          );
          this._refreshOverlays();
          this._renderSidebarBody();
          new Notice(
            `${t("pdf_cleared_ai_notice") || "Cleared AI annotations"} (${
              res.deleted_count ?? 0
            })`
          );
        })();
      });
    }

    const listEl = container.createDiv({ cls: "pf-pdf-ann-list" });
    const filtered = this._annotations.filter((ann) => {
      if (this._authorFilter === "agent") return ann.author === "agent";
      if (this._authorFilter === "user") return ann.author !== "agent";
      if (ann.author === "agent" && !this._showAgentLayer) return false;
      return true;
    });

    if (filtered.length === 0) {
      listEl.createDiv({
        cls: "pf-pdf-sidebar-empty",
        text:
          t("pdf_no_annotations") ||
          "No highlights or notes yet. Select text and click Highlight.",
      });
      return;
    }

    for (const ann of filtered) {
      const isAgent = ann.author === "agent";
      const card = listEl.createDiv({
        cls: `pf-pdf-ann-card${isAgent ? " is-agent" : ""}`,
        attr: { "data-ann-id": ann.ann_id },
      });

      const head = card.createDiv({ cls: "pf-pdf-ann-card-head" });
      const dot = head.createEl("span", { cls: "pf-pdf-ann-dot" });
      const swHex =
        [...PREVIEW_HIGHLIGHT_SWATCHES, ...MARKUP_STROKE_SWATCHES].find(
          (s) => s.id === ann.color
        )?.hex ??
        ann.style?.stroke_color ??
        "#5b45c9";
      dot.style.background = swHex;

      const kindLabels: Record<string, string> = {
        highlight: lbl("高亮", "highlight"),
        underline: lbl("下划线", "underline"),
        strikethrough: lbl("删除线", "strikethrough"),
        margin: lbl("页边定位", "margin"),
        area: lbl("图表框选", "area"),
        ink: lbl("画笔", "ink"),
        shape: lbl("图形", "shape"),
        textbox: lbl("文本框", "textbox"),
        note: lbl("便签", "note"),
      };
      head.createEl("span", {
        cls: "pf-pdf-ann-kind",
        text: kindLabels[ann.kind] || ann.kind,
      });
      if (isAgent) {
        const lensZh: Record<string, string> = {
          skeleton: "逻辑骨架",
          critique: "审稿存疑",
          method: "关键方法",
        };
        const lensText = ann.lens
          ? ` · ${lbl(lensZh[ann.lens] || ann.lens, ann.lens)}`
          : "";
        head.createEl("span", {
          cls: "pf-pdf-ann-agent-badge",
          text: `AI${lensText}`,
        });
      }
      if (ann.figure_id) {
        head.createEl("span", {
          cls: "pf-pdf-ann-fig-badge pf-tnum",
          text: ann.figure_id,
        });
      }
      head.createEl("span", {
        cls: "pf-pdf-ann-page pf-tnum",
        text: `p.${ann.page}`,
      });

      if (ann.section_path) {
        const sec = card.createEl("div", {
          cls: "pf-pdf-ann-section",
          text: ann.section_path,
        });
        sec.addEventListener("click", () =>
          this.scrollToPage(ann.page, ann.ann_id)
        );
      }

      if (ann.exact_text) {
        const quoteEl = card.createEl("blockquote", {
          cls: "pf-pdf-ann-quote",
          text: ann.exact_text,
        });
        quoteEl.style.borderLeftColor = swHex;
      }
      if (ann.comment) {
        card.createEl("p", {
          cls: "pf-pdf-ann-comment",
          text: ann.comment,
        });
      }

      if (ann.crop_asset_rel) {
        const img = card.createEl("img", { cls: "pf-pdf-ann-crop-img" });
        img.src = this.app.vault.adapter.getResourcePath(ann.crop_asset_rel);
        img.addEventListener("click", () =>
          this.scrollToPage(ann.page, ann.ann_id)
        );
      }

      const actions = card.createDiv({ cls: "pf-pdf-ann-card-actions" });

      const jumpBtn = actions.createEl("button", {
        cls: "pf-btn pf-btn-ghost",
        type: "button",
        text: t("pdf_jump") || "Locate",
      });
      jumpBtn.addEventListener("click", () =>
        this.scrollToPage(ann.page, ann.ann_id)
      );

      if (isAgent) {
        const adoptBtn = actions.createEl("button", {
          cls: "pf-btn pf-btn-secondary",
          type: "button",
          text: t("pdf_adopt_btn") || "Adopt",
          attr: { "data-pf-testid": "pdf-adopt-ann-btn" },
        });
        adoptBtn.addEventListener("click", () => {
          void (async () => {
            const updated = await this.plugin
              .getClient()
              .adoptAnnotation(this._state.paperKey, ann.ann_id);
            const idx = this._annotations.findIndex(
              (a) => a.ann_id === ann.ann_id
            );
            if (idx >= 0) this._annotations[idx] = updated;
            this._refreshOverlays();
            this._renderSidebarBody();
            new Notice(
              t("pdf_adopted_notice") || "Adopted into your annotations"
            );
          })();
        });
      }

      const citeBtn = actions.createEl("button", {
        cls: "pf-btn pf-btn-ghost",
        type: "button",
        text: t("pdf_copy_citation") || "Copy Note Citation",
        attr: { "data-pf-testid": "pdf-copy-citation-btn" },
      });
      citeBtn.addEventListener("click", () => {
        void (async () => {
          const citation = this._buildCitationText(ann);
          if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(citation);
          }
          new Notice(t("pdf_citation_copied") || "Citation copied");
        })();
      });

      if (ann.embed_wikilink) {
        const copyImgBtn = actions.createEl("button", {
          cls: "pf-btn pf-btn-ghost",
          type: "button",
          text: t("pdf_copy_embed") || "Copy Image Link",
        });
        copyImgBtn.addEventListener("click", () => {
          void (async () => {
            if (navigator.clipboard?.writeText) {
              await navigator.clipboard.writeText(ann.embed_wikilink);
            }
            new Notice(t("pdf_crop_copied") || "Embed copied");
          })();
        });
      } else if (!isAgent) {
        const promoteBtn = actions.createEl("button", {
          cls: "pf-btn pf-btn-ghost",
          type: "button",
          text: t("pdf_promote_log") || "Add to Log",
        });
        promoteBtn.addEventListener("click", () => {
          void (async () => {
            await this.plugin
              .getClient()
              .promoteAnnotation(this._state.paperKey, ann.ann_id, {
                usage: "evidence",
              });
            new Notice(t("pdf_promoted_notice") || "Added to Reading Log");
          })();
        });
      }

      const delBtn = createPfIconBtn(actions, {
        icon: "trash-2",
        label: t("pdf_delete") || "Delete",
        cls: "pf-pdf-icon-btn pf-pdf-ann-del-btn",
      });
      delBtn.addEventListener("click", () => {
        void (async () => {
          await this.plugin
            .getClient()
            .deleteAnnotation(this._state.paperKey, ann.ann_id);
          this._annotations = this._annotations.filter(
            (x) => x.ann_id !== ann.ann_id
          );
          this._refreshOverlays();
          this._renderSidebarBody();
        })();
      });
    }
  }

  private _buildCitationText(ann: PdfAnnotationDto): string {
    const key = ann.paper_id || this._state.paperKey;
    const noteRel = this._ctx?.note_rel_path || "";
    const noteLink = noteRel
      ? `[[${noteRel}|${key} p.${ann.page}]]`
      : `[[${key} p.${ann.page}]]`;
    const quoteText =
      ann.exact_text || ann.comment || ann.section_path || `Page ${ann.page}`;
    if (ann.embed_wikilink) {
      return `${ann.embed_wikilink}\n> ${noteLink}`;
    }
    return `> "${quoteText}" — ${noteLink}`;
  }

  private async _runSearch(advance: boolean, step = 1): Promise<void> {
    if (!this._searchQuery) {
      this._searchMatches = [];
      this._searchCountEl?.setText("");
      return;
    }
    if (!advance || this._searchMatches.length === 0) {
      const total = this._doc?.numPages || 0;
      const matches: Array<{ page: number; text: string }> = [];
      for (let p = 1; p <= total; p++) {
        let txt = this._pageTexts.get(p);
        if (txt === undefined && this._doc) {
          try {
            const page = await this._doc.getPage(p);
            const tc = await page.getTextContent();
            txt = (tc.items || []).map((i) => i.str || "").join(" ");
            this._pageTexts.set(p, txt);
          } catch {
            txt = "";
          }
        }
        if (txt && txt.toLowerCase().includes(this._searchQuery)) {
          matches.push({ page: p, text: txt });
        }
      }
      this._searchMatches = matches;
      this._searchIndex = 0;
    } else {
      this._searchIndex =
        (this._searchIndex + step + this._searchMatches.length) %
        this._searchMatches.length;
    }

    if (this._searchMatches.length === 0) {
      this._searchCountEl?.setText("0/0");
      return;
    }
    const active = this._searchMatches[this._searchIndex];
    this._searchCountEl?.setText(
      `${this._searchIndex + 1}/${this._searchMatches.length}`
    );
    this.scrollToPage(active.page);
  }

  public scrollToPage(page: number, annId?: string): void {
    this._currentPage = page;
    if (this._pageInputEl) {
      this._pageInputEl.value = String(page);
    }
    this._highlightActiveThumb();
    const el = this._pageEls.get(page);
    if (el) {
      el.scrollIntoView?.({ behavior: "smooth", block: "start" });
      void this._ensurePageRendered(page);
    }
    if (annId) {
      const box = this.contentEl.querySelector(
        `.pf-pdf-ann-box[data-ann-id="${annId}"]`
      );
      if (box) {
        box.addClass("is-flash");
        window.setTimeout(() => box.removeClass("is-flash"), 1600);
      }
    }
  }
}
