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
  AnnotationIntent,
  AnnotationKind,
  PaperForgeClient,
  PaperPdfContextDto,
  PdfAnnotationDto,
} from "../client/paperforge-client";

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
  transform: number[];
}

interface PdfPageLike {
  getViewport(params: { scale: number }): PdfViewportLike;
  render(params: {
    canvasContext: CanvasRenderingContext2D;
    viewport: PdfViewportLike;
  }): { promise: Promise<void> };
  getTextContent(): Promise<{ items: PdfTextItem[] }>;
}

interface PdfDocumentLike {
  numPages: number;
  getPage(pageNumber: number): Promise<PdfPageLike>;
  destroy?: () => Promise<void> | void;
}

const COLOR_SWATCHES: Array<{
  id: AnnotationColor;
  hex: string;
  label: string;
}> = [
  { id: "yellow", hex: "#fde047", label: "Yellow" },
  { id: "green", hex: "#86efac", label: "Green" },
  { id: "blue", hex: "#93c5fd", label: "Blue" },
  { id: "red", hex: "#fca5a5", label: "Red" },
  { id: "purple", hex: "#d8b4fe", label: "Purple" },
];

const INTENT_META: Record<
  AnnotationIntent,
  { badge: string; labelKey: string; fallback: string }
> = {
  evidence: {
    badge: "💡",
    labelKey: "pdf_intent_evidence",
    fallback: "核心证据",
  },
  question: {
    badge: "❓",
    labelKey: "pdf_intent_question",
    fallback: "存疑待查",
  },
  method: {
    badge: "🧪",
    labelKey: "pdf_intent_method",
    fallback: "方法细节",
  },
  quote: {
    badge: "✍️",
    labelKey: "pdf_intent_quote",
    fallback: "可引述",
  },
  general: {
    badge: "📌",
    labelKey: "pdf_intent_general",
    fallback: "笔记",
  },
};

/** Resolve an Obsidian-loadable URL for either a vault PDF or an external Zotero PDF. */
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
  plugin: PdfPluginHost;
  private _state: PdfAnnotatorOpenState = { paperKey: "" };
  private _ctx: PaperPdfContextDto | null = null;
  private _annotations: PdfAnnotationDto[] = [];
  private _doc: PdfDocumentLike | null = null;
  private _scale = 1.25;
  private _currentPage = 1;
  private _areaMode = false;
  private _sidebarOpen = true;
  private _authorFilter: "all" | "user" | "agent" = "all";
  private _showAgentLayer = true;
  private _renderedPages = new Set<number>();
  private _renderingPages = new Set<number>();
  private _observer: IntersectionObserver | null = null;
  private _pageEls = new Map<number, HTMLElement>();
  private _scrollEl: HTMLElement | null = null;
  private _sidebarListEl: HTMLElement | null = null;
  private _popoverEl: HTMLElement | null = null;
  private _aiToggleBtn: HTMLButtonElement | null = null;
  private _clearAiBtn: HTMLButtonElement | null = null;
  private _sideToggleBtn: HTMLButtonElement | null = null;
  private _stateRef: EventRef | null = null;

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
    };
  }

  async setState(state: unknown, result: { history: boolean }): Promise<void> {
    const raw = (state ?? {}) as Partial<PdfAnnotatorOpenState>;
    this._state = {
      paperKey: typeof raw.paperKey === "string" ? raw.paperKey : "",
      page: typeof raw.page === "number" && raw.page >= 1 ? raw.page : 1,
      annId: typeof raw.annId === "string" ? raw.annId : undefined,
    };
    this._currentPage = this._state.page ?? 1;
    await super.setState(state, result);
    await this._loadAndRender();
  }

  async onOpen(): Promise<void> {
    this._subscribeStateChanges();
    if (this._state.paperKey) {
      await this._loadAndRender();
    } else {
      this._renderEmptyState(
        t("pdf_select_paper_hint") ||
          "Select a paper from PaperForge Dashboard to annotate its PDF."
      );
    }
  }

  async onClose(): Promise<void> {
    const ws = (
      this.app as unknown as {
        workspace?: { offref?: (ref: EventRef) => void };
      }
    )?.workspace;
    if (this._stateRef && typeof ws?.offref === "function") {
      ws.offref(this._stateRef);
    }
    this._stateRef = null;
    this._teardownDocument();
  }

  private _subscribeStateChanges(): void {
    if (this._stateRef) return;
    const ws = (
      this.app as unknown as {
        workspace?: {
          on?: (ev: string, cb: (payload?: unknown) => void) => EventRef;
        };
      }
    )?.workspace;
    if (typeof ws?.on === "function") {
      this._stateRef = ws.on(
        "paperforge:state-changed",
        (payload?: unknown) => {
          if (!this._state.paperKey || !this._doc) return;
          const changed = (payload as { changedKeys?: string[] } | undefined)
            ?.changedKeys;
          if (
            Array.isArray(changed) &&
            changed.length > 0 &&
            !changed.includes(this._state.paperKey)
          ) {
            return;
          }
          void this._reloadAnnotationsOnly();
        }
      );
    }
  }

  private async _reloadAnnotationsOnly(): Promise<void> {
    const key = this._state.paperKey;
    if (!key) return;
    const client = this.plugin.getClient() as unknown as {
      listAnnotations?: (paperKey: string) => Promise<PdfAnnotationDto[]>;
    };
    if (typeof client?.listAnnotations !== "function") return;
    try {
      const next = await client.listAnnotations(key);
      if (this._state.paperKey !== key || !Array.isArray(next)) return;
      this._annotations = next;
      this._refreshOverlays();
      this._renderSidebarList();
    } catch {
      // Ignore transient refresh failure while external writer finishes
    }
  }

  private _teardownDocument(): void {
    if (this._observer) {
      this._observer.disconnect();
      this._observer = null;
    }
    this._renderedPages.clear();
    this._renderingPages.clear();
    this._pageEls.clear();
    if (this._doc && typeof this._doc.destroy === "function") {
      try {
        void this._doc.destroy();
      } catch {
        // ignore teardown errors
      }
    }
    this._doc = null;
  }

  private _renderEmptyState(message: string): void {
    const root = this.contentEl;
    root.empty();
    root.addClass("pf-pdf-view");
    root.createDiv({ cls: "pf-pdf-empty", text: message });
  }

  private async _loadAndRender(): Promise<void> {
    const key = this._state.paperKey;
    if (!key) {
      this._renderEmptyState(
        t("pdf_select_paper_hint") || "No paper selected."
      );
      return;
    }
    this._teardownDocument();
    const root = this.contentEl;
    root.empty();
    root.addClass("pf-pdf-view");
    const loading = root.createDiv({
      cls: "pf-pdf-empty",
      text: t("pdf_loading") || "Loading PDF and annotations...",
    });

    const client = this.plugin.getClient();
    let ctx: PaperPdfContextDto;
    try {
      ctx = await client.getPdfContext(key);
    } catch (err) {
      loading.setText(
        `${t("pdf_load_failed") || "Failed to load PDF"}: ${
          err instanceof Error ? err.message : String(err)
        }`
      );
      return;
    }

    this._ctx = ctx;
    this._annotations = Array.isArray(ctx.annotations) ? ctx.annotations : [];
    const resourceUrl = resolvePdfResourceUrl(this.app, ctx);
    if (!resourceUrl) {
      loading.setText(
        t("pdf_not_available") || "No canonical PDF found for this paper."
      );
      return;
    }

    try {
      const pdfjsLib = await loadPdfJs();
      const task = pdfjsLib.getDocument(resourceUrl);
      this._doc = (await task.promise) as PdfDocumentLike;
    } catch (err) {
      loading.setText(
        `${t("pdf_render_failed") || "Unable to open PDF"}: ${
          err instanceof Error ? err.message : String(err)
        }`
      );
      return;
    }

    loading.remove();
    this._buildChrome();
    await this._mountPages();
    this._renderSidebarList();
    if (this._state.page && this._state.page > 1) {
      this.scrollToPage(this._state.page);
    }
  }

  private _buildChrome(): void {
    const root = this.contentEl;
    const ctx = this._ctx!;
    const totalPages = this._doc?.numPages || ctx.page_count || 1;

    const toolbar = root.createDiv({ cls: "pf-pdf-toolbar" });
    const titleGroup = toolbar.createDiv({ cls: "pf-pdf-toolbar-title" });
    titleGroup.createEl("span", {
      cls: "pf-pdf-key-badge",
      text: ctx.paper_id,
    });
    titleGroup.createEl("span", {
      cls: "pf-pdf-doc-title",
      text: ctx.title || ctx.paper_id,
    });
    const hasChanged = this._annotations.some(
      (a) => a.provenance_status === "changed"
    );
    titleGroup.createEl("span", {
      cls: `pf-pdf-prov-badge ${hasChanged ? "is-warn" : "is-ok"}`,
      text: hasChanged
        ? t("pdf_prov_changed") || "⚠ PDF 已变更"
        : t("pdf_prov_verified") || "✓ SHA-256",
    });

    const controls = toolbar.createDiv({ cls: "pf-pdf-toolbar-controls" });
    const prevBtn = controls.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: "‹",
      attr: { "aria-label": "Previous page" },
    });
    const pageInput = controls.createEl("input", {
      cls: "pf-pdf-page-input",
      attr: {
        type: "number",
        min: "1",
        max: String(totalPages),
        value: String(this._currentPage),
        "data-pf-testid": "pdf-page-input",
      },
    }) as HTMLInputElement;
    controls.createEl("span", {
      cls: "pf-pdf-page-total",
      text: `/ ${totalPages}`,
    });
    const nextBtn = controls.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: "›",
      attr: { "aria-label": "Next page" },
    });

    prevBtn.addEventListener("click", () => {
      this.scrollToPage(Math.max(1, this._currentPage - 1));
      pageInput.value = String(this._currentPage);
    });
    nextBtn.addEventListener("click", () => {
      this.scrollToPage(Math.min(totalPages, this._currentPage + 1));
      pageInput.value = String(this._currentPage);
    });
    pageInput.addEventListener("change", () => {
      const target = Math.max(
        1,
        Math.min(totalPages, Number(pageInput.value) || 1)
      );
      this.scrollToPage(target);
    });

    const zoomOut = controls.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: "−",
    });
    const zoomLabel = controls.createEl("span", {
      cls: "pf-pdf-zoom-label",
      text: `${Math.round(this._scale * 100)}%`,
    });
    const zoomIn = controls.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: "+",
    });
    const applyZoom = (nextScale: number) => {
      this._scale = Math.max(0.6, Math.min(2.6, nextScale));
      zoomLabel.setText(`${Math.round(this._scale * 100)}%`);
      void this._mountPages();
    };
    zoomOut.addEventListener("click", () => applyZoom(this._scale - 0.15));
    zoomIn.addEventListener("click", () => applyZoom(this._scale + 0.15));

    const areaBtn = controls.createEl("button", {
      cls: `pf-btn ${this._areaMode ? "mod-cta" : "pf-btn-secondary"}`,
      text: t("pdf_area_mode") || "✂️ 框选图表",
      attr: { "data-pf-testid": "pdf-area-mode-btn" },
    });
    areaBtn.addEventListener("click", () => {
      this._areaMode = !this._areaMode;
      areaBtn.toggleClass("mod-cta", this._areaMode);
      areaBtn.toggleClass("pf-btn-secondary", !this._areaMode);
      this._scrollEl?.toggleClass("is-area-mode", this._areaMode);
    });

    const noteBtn = controls.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: t("pdf_open_note_split") || "📝 并排笔记",
      attr: { "data-pf-testid": "pdf-open-note-btn" },
    });
    noteBtn.addEventListener("click", () => void this._openNoteSideBySide());

    const sideToggle = controls.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: `📋 ${this._annotations.length}`,
      attr: { "data-pf-testid": "pdf-toggle-sidebar" },
    });
    this._sideToggleBtn = sideToggle;

    const agentCount = this._annotations.filter(
      (a) => a.author === "agent"
    ).length;
    const aiToggle = controls.createEl("button", {
      cls: `pf-btn ${this._showAgentLayer ? "mod-cta" : "pf-btn-secondary"}`,
      text: `${t("pdf_ai_layer_toggle") || "🤖 AI 批注层"} (${agentCount})`,
      attr: { "data-pf-testid": "pdf-toggle-ai-layer" },
    });
    this._aiToggleBtn = aiToggle;
    aiToggle.addEventListener("click", () => {
      this._showAgentLayer = !this._showAgentLayer;
      if (!this._showAgentLayer && this._authorFilter === "agent") {
        this._authorFilter = "all";
      }
      aiToggle.toggleClass("mod-cta", this._showAgentLayer);
      aiToggle.toggleClass("pf-btn-secondary", !this._showAgentLayer);
      this._refreshOverlays();
      this._renderSidebarList();
    });

    const body = root.createDiv({ cls: "pf-pdf-body" });
    this._scrollEl = body.createDiv({ cls: "pf-pdf-scroll" });
    const sidebar = body.createDiv({ cls: "pf-pdf-sidebar" });
    if (!this._sidebarOpen) sidebar.style.display = "none";

    sideToggle.addEventListener("click", () => {
      this._sidebarOpen = !this._sidebarOpen;
      sidebar.style.display = this._sidebarOpen ? "" : "none";
    });

    const filterBar = sidebar.createDiv({ cls: "pf-pdf-filter-bar" });
    const filters: Array<["all" | "user" | "agent", string]> = [
      ["all", t("pdf_filter_all") || "全部"],
      ["user", t("pdf_filter_mine") || "🖍️ 我的批注"],
      ["agent", t("pdf_filter_ai") || "🤖 AI 领读"],
    ];
    for (const [id, label] of filters) {
      const chip = filterBar.createEl("button", {
        cls: `pf-pdf-filter-chip ${this._authorFilter === id ? "is-active" : ""}`,
        text: label,
        attr: { "data-author-filter": id },
      });
      chip.addEventListener("click", () => {
        this._authorFilter = id;
        if (id === "agent" && !this._showAgentLayer) {
          this._showAgentLayer = true;
          this._aiToggleBtn?.toggleClass("mod-cta", true);
          this._aiToggleBtn?.toggleClass("pf-btn-secondary", false);
          this._refreshOverlays();
        }
        filterBar
          .querySelectorAll(".pf-pdf-filter-chip")
          .forEach((el) => el.classList.remove("is-active"));
        chip.classList.add("is-active");
        this._renderSidebarList();
      });
    }

    const clearAiBtn = filterBar.createEl("button", {
      cls: "pf-pdf-clear-ai-btn",
      text: t("pdf_clear_ai_btn") || "🧹 清空 AI",
      attr: { "data-pf-testid": "pdf-clear-ai-btn" },
    });
    clearAiBtn.style.display = agentCount > 0 ? "" : "none";
    this._clearAiBtn = clearAiBtn;
    clearAiBtn.addEventListener("click", () => {
      void this.plugin
        .getClient()
        .clearAgentAnnotations(this._state.paperKey)
        .then(() => {
          this._annotations = this._annotations.filter(
            (a) => a.author !== "agent"
          );
          this._refreshOverlays();
          this._renderSidebarList();
          new Notice(t("pdf_cleared_ai_notice") || "已清空 AI 批注层");
        })
        .catch((err) => {
          new Notice(
            `Clear AI failed: ${err instanceof Error ? err.message : String(err)}`
          );
        });
    });

    this._sidebarListEl = sidebar.createDiv({ cls: "pf-pdf-ann-list" });
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
    this._scrollEl.empty();
    this._renderedPages.clear();
    this._renderingPages.clear();
    this._pageEls.clear();
    if (this._observer) {
      this._observer.disconnect();
      this._observer = null;
    }

    const totalPages = this._doc.numPages || 1;
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
      wrap.createDiv({ cls: "pf-pdf-overlay-layer" });
      this._attachPageInteractions(wrap, p);
      this._pageEls.set(p, wrap);
    }

    this._refreshOverlays();

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
              void this._ensurePageRendered(p);
              if (p + 1 <= totalPages) void this._ensurePageRendered(p + 1);
            }
          }
        },
        { root: this._scrollEl, rootMargin: "400px 0px" }
      );
      for (const el of this._pageEls.values()) {
        this._observer.observe(el);
      }
    }

    const initial = Math.min(totalPages, Math.max(1, this._currentPage));
    await this._ensurePageRendered(initial);
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
      const canvas = document.createElement("canvas");
      canvas.className = "pf-pdf-canvas";
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.round(viewport.width * dpr));
      canvas.height = Math.max(1, Math.round(viewport.height * dpr));
      canvas.style.width = `${Math.round(viewport.width)}px`;
      canvas.style.height = `${Math.round(viewport.height)}px`;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        if (dpr !== 1) ctx.scale(dpr, dpr);
        await page.render({ canvasContext: ctx, viewport }).promise;
      }

      const textLayer = document.createElement("div");
      textLayer.className = "pf-pdf-text-layer";
      try {
        const textContent = await page.getTextContent();
        for (const item of textContent.items || []) {
          if (!item.str) continue;
          const span = document.createElement("span");
          span.textContent = item.str;
          const tx = item.transform;
          if (tx && tx.length >= 6 && viewport.transform?.length >= 6) {
            const x = tx[4] * this._scale;
            const y = viewport.height - tx[5] * this._scale;
            const fontH = Math.max(8, Math.abs(tx[3] || 10) * this._scale);
            span.style.left = `${x}px`;
            span.style.top = `${Math.max(0, y - fontH)}px`;
            span.style.fontSize = `${fontH}px`;
          }
          textLayer.appendChild(span);
        }
      } catch {
        // Optional text layer error must not prevent canvas display
      }

      pageEl
        .querySelectorAll(".pf-pdf-canvas, .pf-pdf-text-layer")
        .forEach((n) => n.remove());
      if (overlayLayer) {
        pageEl.insertBefore(canvas, overlayLayer);
        pageEl.insertBefore(textLayer, overlayLayer);
      } else {
        pageEl.appendChild(canvas);
        pageEl.appendChild(textLayer);
      }

      this._renderedPages.add(pageNumber);
      this._renderPageOverlays(pageNumber, pageEl);
    } finally {
      this._renderingPages.delete(pageNumber);
    }
  }

  private _attachPageInteractions(
    pageEl: HTMLElement,
    pageNumber: number
  ): void {
    // Text selection highlight
    pageEl.addEventListener("mouseup", () => {
      if (this._areaMode) return;
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed) return;
      const text = sel.toString().trim();
      if (!text) return;
      const range = sel.getRangeAt(0);
      const pageBox = pageEl.getBoundingClientRect();
      if (pageBox.width <= 0 || pageBox.height <= 0) return;

      const clientRects = Array.from(range.getClientRects()).filter(
        (r) => r.width > 1 && r.height > 1
      );
      const boxes = (
        clientRects.length ? clientRects : [range.getBoundingClientRect()]
      ).map((r) => [
        Math.max(0, Math.min(1, (r.left - pageBox.left) / pageBox.width)),
        Math.max(0, Math.min(1, (r.top - pageBox.top) / pageBox.height)),
        Math.max(0, Math.min(1, (r.right - pageBox.left) / pageBox.width)),
        Math.max(0, Math.min(1, (r.bottom - pageBox.top) / pageBox.height)),
      ]);
      this._openCreatePopover({
        anchorEl: pageEl,
        page: pageNumber,
        rects: boxes,
        kind: "highlight",
        exactText: text,
      });
    });

    // Area marquee crop mode
    let dragStart: { x: number; y: number } | null = null;
    let marqueeEl: HTMLElement | null = null;

    pageEl.addEventListener("pointerdown", (ev: PointerEvent) => {
      if (!this._areaMode) return;
      const box = pageEl.getBoundingClientRect();
      if (box.width <= 0 || box.height <= 0) return;
      dragStart = {
        x: Math.max(0, Math.min(box.width, ev.clientX - box.left)),
        y: Math.max(0, Math.min(box.height, ev.clientY - box.top)),
      };
      marqueeEl = pageEl.createDiv({ cls: "pf-pdf-marquee" });
      marqueeEl.style.left = `${dragStart.x}px`;
      marqueeEl.style.top = `${dragStart.y}px`;
    });

    pageEl.addEventListener("pointermove", (ev: PointerEvent) => {
      if (!dragStart || !marqueeEl) return;
      const box = pageEl.getBoundingClientRect();
      const curX = Math.max(0, Math.min(box.width, ev.clientX - box.left));
      const curY = Math.max(0, Math.min(box.height, ev.clientY - box.top));
      marqueeEl.style.left = `${Math.min(dragStart.x, curX)}px`;
      marqueeEl.style.top = `${Math.min(dragStart.y, curY)}px`;
      marqueeEl.style.width = `${Math.abs(curX - dragStart.x)}px`;
      marqueeEl.style.height = `${Math.abs(curY - dragStart.y)}px`;
    });

    pageEl.addEventListener("pointerup", (ev: PointerEvent) => {
      if (!dragStart) return;
      const box = pageEl.getBoundingClientRect();
      const curX = Math.max(0, Math.min(box.width, ev.clientX - box.left));
      const curY = Math.max(0, Math.min(box.height, ev.clientY - box.top));
      const x0 = Math.min(dragStart.x, curX) / Math.max(1, box.width);
      const y0 = Math.min(dragStart.y, curY) / Math.max(1, box.height);
      const x1 = Math.max(dragStart.x, curX) / Math.max(1, box.width);
      const y1 = Math.max(dragStart.y, curY) / Math.max(1, box.height);
      marqueeEl?.remove();
      marqueeEl = null;
      dragStart = null;
      if (x1 - x0 < 0.01 || y1 - y0 < 0.01) return;
      this._openCreatePopover({
        anchorEl: pageEl,
        page: pageNumber,
        rects: [[x0, y0, x1, y1]],
        kind: "area",
        exactText: "",
      });
    });
  }

  /** Open floating color + note popover and persist via backend authority. */
  public _openCreatePopover(params: {
    anchorEl: HTMLElement;
    page: number;
    rects: number[][];
    kind: AnnotationKind;
    exactText: string;
  }): void {
    this._popoverEl?.remove();
    const pop = this.contentEl.createDiv({
      cls: "pf-pdf-popover",
      attr: { "data-pf-testid": "pdf-create-popover" },
    });
    this._popoverEl = pop;

    let selectedColor: AnnotationColor =
      params.kind === "area" ? "blue" : "yellow";

    const swatchRow = pop.createDiv({ cls: "pf-pdf-swatch-row" });
    for (const sw of COLOR_SWATCHES) {
      const btn = swatchRow.createEl("button", {
        cls: `pf-pdf-swatch ${sw.id === selectedColor ? "is-selected" : ""}`,
        attr: {
          type: "button",
          "aria-label": sw.label,
          style: `background:${sw.hex}`,
        },
      });
      btn.addEventListener("click", () => {
        selectedColor = sw.id;
        swatchRow
          .querySelectorAll(".pf-pdf-swatch")
          .forEach((n) => n.classList.remove("is-selected"));
        btn.classList.add("is-selected");
      });
    }

    const commentInput = pop.createEl("textarea", {
      cls: "pf-pdf-popover-comment",
      attr: {
        placeholder:
          t("pdf_comment_placeholder") || "添加批注想法 / 给 Agent 的问题...",
        rows: "2",
      },
    }) as HTMLTextAreaElement;

    const actions = pop.createDiv({ cls: "pf-pdf-popover-actions" });
    const cancelBtn = actions.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: t("config_cancel") || "取消",
      attr: { type: "button" },
    });
    cancelBtn.addEventListener("click", () => {
      pop.remove();
      this._popoverEl = null;
    });

    const saveBtn = actions.createEl("button", {
      cls: "pf-btn mod-cta",
      text: t("pdf_save_annotation") || "保存批注",
      attr: { type: "button", "data-pf-testid": "pdf-save-ann-btn" },
    });
    saveBtn.addEventListener("click", () => {
      void (async () => {
        try {
          const created = await this.plugin
            .getClient()
            .addAnnotation(this._state.paperKey, {
              page: params.page,
              rects: params.rects,
              kind: params.kind,
              color: selectedColor,
              intent: "general",
              exact_text: params.exactText,
              comment: commentInput.value.trim(),
            });
          this._annotations.push(created);
          this._refreshOverlays();
          this._renderSidebarList();
          if (created.embed_wikilink && navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(created.embed_wikilink);
            new Notice(
              `${t("pdf_crop_copied") || "已保存并复制引用"}: ${created.embed_wikilink}`
            );
          } else {
            new Notice(t("pdf_ann_saved") || "批注已保存");
          }
          window.getSelection()?.removeAllRanges();
          pop.remove();
          this._popoverEl = null;
        } catch (err) {
          new Notice(
            `Save failed: ${err instanceof Error ? err.message : String(err)}`
          );
        }
      })();
    });
  }

  private _refreshOverlays(): void {
    for (const [pageNumber, pageEl] of this._pageEls.entries()) {
      this._renderPageOverlays(pageNumber, pageEl);
    }
  }

  private _renderPageOverlays(pageNumber: number, pageEl: HTMLElement): void {
    const layer = pageEl.querySelector(
      ".pf-pdf-overlay-layer"
    ) as HTMLElement | null;
    if (!layer) return;
    layer.empty();
    for (const ann of this._annotations) {
      if (ann.page !== pageNumber) continue;
      if (ann.author === "agent" && !this._showAgentLayer) continue;
      const boxClasses = [
        "pf-pdf-ann-box",
        `pf-pdf-ann--${ann.color || "yellow"}`,
        `pf-pdf-ann-kind--${ann.kind}`,
      ];
      if (ann.author === "agent") boxClasses.push("pf-pdf-hl-agent");
      if (ann.kind === "margin") boxClasses.push("pf-pdf-margin-bracket");
      for (const rect of ann.rects || []) {
        if (!Array.isArray(rect) || rect.length < 4) continue;
        const box = layer.createDiv({
          cls: boxClasses.join(" "),
          attr: {
            "data-ann-id": ann.ann_id,
            title: ann.comment || ann.exact_text || "",
          },
        });
        box.style.left = `${rect[0] * 100}%`;
        box.style.top = `${rect[1] * 100}%`;
        box.style.width = `${Math.max(0.5, (rect[2] - rect[0]) * 100)}%`;
        box.style.height = `${Math.max(0.5, (rect[3] - rect[1]) * 100)}%`;
      }
    }
  }

  private _renderSidebarList(): void {
    const agentCount = this._annotations.filter(
      (a) => a.author === "agent"
    ).length;
    if (this._sideToggleBtn) {
      this._sideToggleBtn.setText(`📋 ${this._annotations.length}`);
    }
    if (this._aiToggleBtn) {
      this._aiToggleBtn.setText(
        `${t("pdf_ai_layer_toggle") || "🤖 AI 批注层"} (${agentCount})`
      );
    }
    if (this._clearAiBtn) {
      this._clearAiBtn.style.display = agentCount > 0 ? "" : "none";
    }

    const list = this._sidebarListEl;
    if (!list) return;
    list.empty();

    const filtered = this._annotations.filter((a) => {
      const isAgent = a.author === "agent";
      if (isAgent && !this._showAgentLayer) return false;
      if (this._authorFilter === "user") return !isAgent;
      if (this._authorFilter === "agent") return isAgent;
      return true;
    });
    if (!filtered.length) {
      list.createDiv({
        cls: "pf-pdf-sidebar-empty",
        text: t("pdf_no_annotations") || "暂无批注 — 划词或框选图表即可添加。",
      });
      return;
    }

    for (const ann of filtered) {
      const isAgent = ann.author === "agent";
      const card = list.createDiv({
        cls: `pf-pdf-ann-card pf-pdf-ann--${ann.color || "yellow"}${isAgent ? " is-agent" : ""}`,
        attr: { "data-ann-id": ann.ann_id },
      });
      const head = card.createDiv({ cls: "pf-pdf-ann-card-head" });
      if (isAgent) {
        head.createEl("span", {
          cls: "pf-pdf-ann-intent pf-pdf-ann-agent-badge",
          text: ann.lens ? `🤖 AI · ${ann.lens}` : "🤖 AI",
        });
      } else {
        const meta =
          INTENT_META[(ann.intent as AnnotationIntent) || "general"] ??
          INTENT_META.general;
        head.createEl("span", {
          cls: "pf-pdf-ann-intent",
          text: `${meta.badge} ${t(meta.labelKey) || meta.fallback}`,
        });
      }
      head.createEl("span", {
        cls: "pf-pdf-ann-page",
        text: `P.${ann.page}`,
      });
      if (ann.kind === "margin") {
        head.createEl("span", {
          cls: "pf-pdf-ann-fig-badge",
          text: t("pdf_margin_badge") || "页边定位",
        });
      }
      if (ann.figure_id) {
        head.createEl("span", {
          cls: "pf-pdf-ann-fig-badge",
          text: ann.figure_id,
        });
      }
      if (ann.section_path) {
        card.createDiv({
          cls: "pf-pdf-ann-section",
          text: ann.section_path,
        });
      }
      if (ann.crop_asset_rel) {
        const img = card.createEl("img", {
          cls: "pf-pdf-ann-crop-img",
          attr: {
            src: this.app.vault.adapter.getResourcePath(ann.crop_asset_rel),
            alt: ann.embed_wikilink || ann.ann_id,
          },
        });
        img.addEventListener("click", () =>
          this.scrollToPage(ann.page, ann.ann_id)
        );
      }
      if (ann.exact_text) {
        card.createEl("blockquote", {
          cls: "pf-pdf-ann-quote",
          text: ann.exact_text,
        });
      }
      if (ann.comment) {
        card.createEl("p", {
          cls: "pf-pdf-ann-comment",
          text: ann.comment,
        });
      }

      const actions = card.createDiv({ cls: "pf-pdf-ann-card-actions" });
      const jumpBtn = actions.createEl("button", {
        cls: "pf-btn pf-btn-secondary",
        text: t("pdf_jump") || "定位",
      });
      jumpBtn.addEventListener("click", () =>
        this.scrollToPage(ann.page, ann.ann_id)
      );

      if (isAgent) {
        const adoptBtn = actions.createEl("button", {
          cls: "pf-btn pf-btn-secondary",
          text: t("pdf_adopt_btn") || "✓ 采纳",
          attr: { "data-pf-testid": "pdf-adopt-ann-btn" },
        });
        adoptBtn.addEventListener("click", () => {
          void this.plugin
            .getClient()
            .adoptAnnotation(this._state.paperKey, ann.ann_id)
            .then((updated) => {
              this._annotations = this._annotations.map((item) =>
                item.ann_id === ann.ann_id ? updated : item
              );
              this._refreshOverlays();
              this._renderSidebarList();
              new Notice(t("pdf_adopted_notice") || "已采纳为我的批注");
            })
            .catch((err) => {
              new Notice(
                `Adopt failed: ${err instanceof Error ? err.message : String(err)}`
              );
            });
        });
      }

      const promoteBtn = actions.createEl("button", {
        cls: "pf-btn pf-btn-secondary",
        text: t("pdf_promote_log") || "📌 证据卡",
      });
      promoteBtn.addEventListener("click", () => {
        void this.plugin
          .getClient()
          .promoteAnnotation(this._state.paperKey, ann.ann_id, {
            usage: ann.intent || "evidence",
          })
          .then(
            () => new Notice(t("pdf_promoted_notice") || "已存入研究证据日志"),
            (err) =>
              new Notice(
                `Promote failed: ${err instanceof Error ? err.message : String(err)}`
              )
          );
      });

      if (ann.embed_wikilink) {
        const copyBtn = actions.createEl("button", {
          cls: "pf-btn pf-btn-secondary",
          text: t("pdf_copy_embed") || "📋 嵌入图",
        });
        copyBtn.addEventListener("click", () => {
          void navigator.clipboard?.writeText(ann.embed_wikilink);
          new Notice(`Copied ${ann.embed_wikilink}`);
        });
      }

      const delBtn = actions.createEl("button", {
        cls: "pf-btn pf-btn-danger",
        text: t("pdf_delete") || "删除",
      });
      delBtn.addEventListener("click", () => {
        void this.plugin
          .getClient()
          .deleteAnnotation(this._state.paperKey, ann.ann_id)
          .then(() => {
            this._annotations = this._annotations.filter(
              (a) => a.ann_id !== ann.ann_id
            );
            this._refreshOverlays();
            this._renderSidebarList();
          });
      });
    }
  }

  public scrollToPage(page: number, annId?: string): void {
    this._currentPage = page;
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
        box.classList.add("is-flash");
        setTimeout(() => box.classList.remove("is-flash"), 1400);
      }
    }
  }
}
