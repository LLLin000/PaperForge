/**
 * PaperForge Interactive UI Gallery & Design System Storybook.
 *
 * Mirrors the CellPlanner Storybook architecture (`internal/uikit/kit/gallery.go`
 * + `storybook_sections.go`), rendering all 10 live interactive sections:
 * tokens/palettes/elevation/motion/icons, UIKit 6 engines & primitives,
 * Obsidian Bases workbench, Companion sidebar 3 modes & search, Apple Preview
 * PDF reader (+ narrow split), OCR workspace, Settings control center,
 * Setup wizard & domain A/B preview, Quick Switcher & modals, and edge-case
 * CJK/Latin truncation & contrast stress tests.
 */

import { WorkspaceLeaf } from "obsidian";
import { t, setLanguage } from "../i18n";
import type { ProbeEnvelope } from "../client/probe-types";
import type { BaseTableSnapshotDto } from "../client/paperforge-client";
import { PaperForgeBasesView } from "../views/paperforge-base-view";
import { PaperForgeStatusView } from "../views/dashboard";
import { PaperForgePdfView } from "../views/pdf-annotator";
import { OcrWorkspaceView, VersionRestoreModal } from "../views/ocr-workspace";
import { PaperForgeSettingTab } from "../settings";
import { PaperForgeOrphanModal } from "../views/modals";
import { PaperForgeQuickSwitcherModal } from "../views/quick-switcher";
import { renderDomainModePreview } from "../views/domain-preview";
import {
  renderActionButton,
  renderActivityRow,
  renderDisclosure,
  renderErrorAnatomy,
  renderStatusBadge,
} from "../primitives";
import { setPfIcon, type PfIconName } from "../views/icons";
import {
  applyNudge,
  applyThemeScope,
  categoricalPalette,
  MOTION_TOKENS,
  tokensFor,
  type UiColorMode,
  type UiDensity,
  type UiThemePreset,
} from "./theme";
import { applyElevation, type ElevationTier } from "./elevation";
import { LayerStack } from "./layer-stack";
import { CommandRegistry } from "./commands";
import { ToastQueue } from "./toast";
import { SidePeekController } from "./side-peek";
import { FilterBarState, renderFilterBar } from "./filter-bar";
import { attachContextMenu } from "./context-menu";
import { renderScrubNumber } from "./scrub-number";
import {
  renderBadge,
  renderEmptyState,
  renderHoldToConfirm,
  renderInlineBanner,
  renderKeycap,
  renderListItem,
  renderSectionHeader,
} from "./primitives";
import {
  buildGalleryDemoCommands,
  createGalleryMockEnv,
  createMockPdfDocForObsidian,
  ensureObsidianElHelpers,
  GALLERY_FILTER_FIELDS,
  GALLERY_SAVED_VIEWS,
  makeGalleryBaseEntries,
} from "./gallery-fixtures";

export interface GalleryConfigState {
  preset: UiThemePreset;
  mode: "light" | "dark";
  density: UiDensity;
  liquidGlass: boolean;
  reduceMotion: boolean;
  narrowPreview: boolean;
  searchQuery: string;
}

export interface GallerySectionContext {
  controller: PaperForgeGalleryController;
  state: GalleryConfigState;
  layerStack: LayerStack;
  toast: ToastQueue;
  openSidePeek: (opts: {
    id: string;
    title: string;
    subtitle?: string;
    bodyText: string;
  }) => void;
  registerCleanup: (fn: () => void) => void;
}

export interface StorySection {
  id: string;
  group: "基础系统" | "UIKit 原语" | "核心视图" | "设置与边界态";
  title: string;
  subtitle: string;
  keywords: string;
  render: (
    host: HTMLElement,
    ctx: GallerySectionContext
  ) => Promise<void> | void;
}

const ALL_ICON_NAMES: PfIconName[] = [
  "panel-left",
  "panel-right",
  "chevron-left",
  "chevron-right",
  "chevron-down",
  "search",
  "x",
  "more-horizontal",
  "columns-2",
  "refresh-cw",
  "check",
  "alert-triangle",
  "sliders",
  "external-link",
  "folder",
  "book-open",
  "file-text",
  "sparkles",
  "highlighter",
  "pen-tool",
  "text-cursor",
  "box-select",
  "pencil",
  "shapes",
  "square",
  "circle",
  "arrow-up-right",
  "minus",
  "plus",
  "maximize-2",
  "type",
  "sticky-note",
  "trash-2",
  "quote",
  "layers",
  "play",
  "wrench",
  "stethoscope",
  "underline",
  "strikethrough",
  "copy",
  "list",
  "filter",
  "arrow-up-down",
  "settings",
  "layout-grid",
  "palette",
  "info",
  "check-circle",
  "alert-circle",
  "mouse-pointer-click",
  "sun",
  "moon",
  "terminal",
  "database",
  "keyboard",
  "eye",
];

function safeMountPanel(
  container: HTMLElement,
  label: string,
  fn: () => Promise<void> | void
): Promise<void> {
  return Promise.resolve()
    .then(fn)
    .catch((err) => {
      const errMsg = err instanceof Error ? err.message : String(err);
      renderInlineBanner(container, {
        tone: "warning",
        icon: "alert-triangle",
        message: `${label} 预览加载降级：${errMsg}`,
      });
    });
}

async function mountPdfSafely(
  mount: HTMLElement,
  env: ReturnType<typeof createGalleryMockEnv>,
  paperKey: string,
  opts?: {
    scale?: number;
    narrow?: boolean;
    openMarkup?: boolean;
    thumbsTab?: boolean;
  }
): Promise<PaperForgePdfView> {
  const leaf = new WorkspaceLeaf();
  (leaf as unknown as { app: unknown }).app = env.app;
  const view = new PaperForgePdfView(leaf, env.plugin as never);
  (view as unknown as { app: unknown }).app = env.app;
  (view as unknown as { contentEl: HTMLElement }).contentEl = mount;
  (view as unknown as { _scale: number })._scale = opts?.scale ?? 0.86;
  await view.setState({ paperKey, page: 1 }, { history: false });

  // Inside live Obsidian host, loadPdfJs cannot read mock /mock-zotero paths;
  // fall back to our deterministic in-memory PDF document so real toolbar, SVG overlays,
  // highlights, thumbnails, and notes always render cleanly.
  if (
    paperKey &&
    paperKey !== "KEY_NOPDF" &&
    !mount.querySelector(".pf-pdf-toolbar")
  ) {
    const vAny = view as unknown as {
      _doc: unknown;
      _annotations: unknown;
      _ctx: unknown;
      _buildChrome: () => void;
      _mountPages: () => Promise<void>;
    };
    const client = env.plugin.getClient as () => {
      getPdfContext: (k: string) => Promise<unknown>;
    };
    vAny._ctx = await client().getPdfContext(paperKey);
    vAny._annotations = env.annotations;
    vAny._doc = createMockPdfDocForObsidian();
    mount.empty();
    mount.addClass("pf-pdf-view");
    vAny._buildChrome();
    await vAny._mountPages();
  }

  if (opts?.narrow) {
    mount.classList.add("is-narrow");
  }
  if (opts?.openMarkup) {
    (
      mount.querySelector(
        '[data-pf-testid="pdf-markup-toggle"]'
      ) as HTMLButtonElement | null
    )?.click();
  }
  if (opts?.thumbsTab) {
    (
      mount.querySelector(
        '[data-pf-testid="pdf-tab-thumbs"]'
      ) as HTMLButtonElement | null
    )?.click();
  }
  return view;
}

export class PaperForgeGalleryController {
  readonly hostEl: HTMLElement;
  state: GalleryConfigState;
  readonly layerStack = new LayerStack();
  readonly toast = new ToastQueue();

  private rootEl!: HTMLElement;
  private topbarEl!: HTMLElement;
  private navEl!: HTMLElement;
  private canvasEl!: HTMLElement;
  private sectionEls = new Map<string, HTMLElement>();
  private navBtnEls = new Map<string, HTMLButtonElement>();
  private activePeek: SidePeekController | null = null;
  private cleanups: Array<() => void> = [];
  private sections: StorySection[] = [];
  private activeSectionId = "tokens-themes";
  private destroyed = false;

  private readonly onDocKeyDown = (e: KeyboardEvent) => {
    this.layerStack.handleKeyDown(e);
  };

  constructor(hostEl: HTMLElement, initial?: Partial<GalleryConfigState>) {
    this.hostEl = hostEl;
    this.state = {
      preset: initial?.preset ?? "obsidian",
      mode: initial?.mode ?? "light",
      density: initial?.density ?? "default",
      liquidGlass: initial?.liquidGlass ?? true,
      reduceMotion: initial?.reduceMotion ?? false,
      narrowPreview: initial?.narrowPreview ?? false,
      searchQuery: initial?.searchQuery ?? "",
    };
    this.sections = this.buildSections();
  }

  async mount(): Promise<void> {
    this.destroyed = false;
    ensureObsidianElHelpers();
    this.hostEl.empty();

    this.rootEl = this.hostEl.createDiv({
      cls: "pf-gallery-root",
      attr: { "data-pf-testid": "ui-gallery-root" },
    });
    this.applyScopeClasses();

    this.topbarEl = this.rootEl.createDiv({ cls: "pf-gallery-topbar" });
    this.renderTopbar();

    const bodyEl = this.rootEl.createDiv({ cls: "pf-gallery-body" });
    this.navEl = bodyEl.createDiv({ cls: "pf-gallery-nav" });
    this.canvasEl = bodyEl.createDiv({ cls: "pf-gallery-canvas" });
    this.canvasEl.classList.toggle("is-narrow", this.state.narrowPreview);

    this.toast.mount(this.rootEl);
    if (typeof document !== "undefined") {
      document.addEventListener("keydown", this.onDocKeyDown);
    }

    this.renderNav();
    await this.renderAllSections();
  }

  destroy(): void {
    this.destroyed = true;
    for (const fn of this.cleanups) {
      try {
        fn();
      } catch {
        // Ignore teardown errors on already detached panels
      }
    }
    this.cleanups = [];
    this.activePeek?.close();
    this.activePeek = null;
    this.toast.destroy();
    this.layerStack.clear();
    if (typeof document !== "undefined") {
      document.removeEventListener("keydown", this.onDocKeyDown);
    }
    this.sectionEls.clear();
    this.navBtnEls.clear();
    this.hostEl.empty();
  }

  setPreset(preset: UiThemePreset): void {
    this.state.preset = preset;
    this.applyScopeClasses();
    this.renderTopbar();
    this.refreshDynamicDisplays();
  }

  setMode(mode: "light" | "dark"): void {
    this.state.mode = mode;
    this.applyScopeClasses();
    this.renderTopbar();
    this.refreshDynamicDisplays();
  }

  setDensity(density: UiDensity): void {
    this.state.density = density;
    this.applyScopeClasses();
    this.renderTopbar();
    this.refreshDynamicDisplays();
  }

  setNarrowPreview(narrow: boolean): void {
    this.state.narrowPreview = narrow;
    this.canvasEl?.classList.toggle("is-narrow", narrow);
    this.renderTopbar();
  }

  setSearchQuery(query: string): void {
    this.state.searchQuery = query;
    this.filterSections();
  }

  private applyScopeClasses(): void {
    const mode: UiColorMode = this.state.mode;
    const isDark = applyThemeScope(this.rootEl, {
      preset: this.state.preset,
      mode,
      density: this.state.density,
      liquidGlass: this.state.liquidGlass,
      reduceMotion: this.state.reduceMotion,
    });
    this.rootEl.classList.add("pf-gallery-root");
    // In standalone HTML mode only, sync host classes on <html> & <body> so Obsidian theme variables switch too.
    if (
      typeof document !== "undefined" &&
      document.body?.dataset?.pfStandalone === "1"
    ) {
      document.documentElement.classList.toggle("theme-dark", isDark);
      document.documentElement.classList.toggle("theme-light", !isDark);
      document.body.classList.toggle("theme-dark", isDark);
      document.body.classList.toggle("theme-light", !isDark);
      document.body.classList.toggle(
        "pf-theme-obsidian",
        this.state.preset === "obsidian"
      );
      document.body.classList.toggle(
        "pf-theme-asterlab",
        this.state.preset === "asterlab"
      );
      document.body.classList.toggle(
        "pf-theme-zinc",
        this.state.preset === "zinc"
      );
      document.body.classList.toggle(
        "pf-theme-warm",
        this.state.preset === "warm"
      );
      document.body.classList.toggle(
        "pf-density-compact",
        this.state.density === "compact"
      );
      document.body.classList.toggle(
        "pf-density-default",
        this.state.density === "default"
      );
      document.body.classList.toggle(
        "pf-density-comfortable",
        this.state.density === "comfortable"
      );
      document.body.classList.toggle("pf-no-glass", !this.state.liquidGlass);
      document.body.classList.toggle(
        "pf-reduce-motion",
        this.state.reduceMotion
      );
    }
  }

  private refreshDynamicDisplays(): void {
    const firstSection = this.sectionEls.get("tokens-themes");
    if (!firstSection) return;
    const body = firstSection.querySelector(
      ".pf-gallery-section-body"
    ) as HTMLElement | null;
    if (body) {
      body.empty();
      const sec = this.sections.find((s) => s.id === "tokens-themes");
      void sec?.render(body, this.createSectionContext());
    }
  }

  private createSectionContext(): GallerySectionContext {
    return {
      controller: this,
      state: this.state,
      layerStack: this.layerStack,
      toast: this.toast,
      registerCleanup: (fn) => {
        this.cleanups.push(fn);
      },
      openSidePeek: (opts) => {
        this.activePeek?.close();
        this.activePeek = new SidePeekController(this.rootEl, {
          id: opts.id,
          title: opts.title,
          subtitle: opts.subtitle,
          icon: "layers",
          layerStack: this.layerStack,
          renderBody: (body) => {
            renderInlineBanner(body, {
              tone: "info",
              icon: "info",
              message:
                "UIKit SidePeek 抽屉引擎 · 已挂载至 LayerStack，按 Esc 或点击遮罩可关闭抽屉，零页面跳转完成上下文核查。",
            });
            const card = body.createDiv({ cls: "pf-gallery-panel" });
            card.createEl("div", {
              cls: "pf-gallery-panel-title",
              text: "实时上下文详情",
            });
            card.createEl("p", {
              text: opts.bodyText,
              cls: "pf-kit-banner-msg",
            });
          },
          renderFooter: (footer) => {
            renderActionButton(footer, {
              label: "推送确认 Toast",
              variant: "primary",
              onClick: () => {
                this.toast.push({
                  message: `已在 SidePeek 内完成：${opts.title}`,
                  tone: "success",
                  undoLabel: "撤销",
                  onUndo: () => {
                    this.toast.push({
                      message: "已执行撤销回调",
                      tone: "info",
                    });
                  },
                });
              },
            });
          },
          onClose: () => {
            this.activePeek = null;
          },
        });
        this.activePeek.open();
      },
    };
  }

  private renderTopbar(): void {
    this.topbarEl.empty();

    const brand = this.topbarEl.createDiv({ cls: "pf-gallery-brand" });
    const iconSpan = brand.createSpan({ cls: "pf-kit-list-item-icon" });
    setPfIcon(iconSpan, "palette");
    brand.createSpan({
      cls: "pf-gallery-title",
      text: "PaperForge UIKit 设计画廊",
    });
    renderBadge(brand, `${this.sections.length} 模块`, "accent");

    const controls = this.topbarEl.createDiv({ cls: "pf-gallery-controls" });

    // Light / Dark segmented switcher
    const modeSeg = controls.createDiv({ cls: "pf-gallery-seg" });
    for (const [val, label] of [
      ["light", "浅色 Light"],
      ["dark", "深色 Dark"],
    ] as const) {
      const btn = modeSeg.createEl("button", {
        cls: `pf-gallery-seg-btn${this.state.mode === val ? " is-active" : ""}`,
        text: label,
        attr: { type: "button", "data-pf-testid": `gallery-mode-${val}` },
      });
      btn.addEventListener("click", () => this.setMode(val));
    }

    // 4 Theme presets
    const presetSeg = controls.createDiv({ cls: "pf-gallery-seg" });
    for (const [val, label] of [
      ["obsidian", "Obsidian"],
      ["asterlab", "纯净极简"],
      ["zinc", "中性灰阶"],
      ["warm", "暖纸阅读"],
    ] as const) {
      const btn = presetSeg.createEl("button", {
        cls: `pf-gallery-seg-btn${this.state.preset === val ? " is-active" : ""}`,
        text: label,
        attr: { type: "button", "data-pf-testid": `gallery-preset-${val}` },
      });
      btn.addEventListener("click", () => this.setPreset(val));
    }

    // 3 Density tiers
    const densitySeg = controls.createDiv({ cls: "pf-gallery-seg" });
    for (const [val, label] of [
      ["compact", "紧凑"],
      ["default", "标准"],
      ["comfortable", "舒适"],
    ] as const) {
      const btn = densitySeg.createEl("button", {
        cls: `pf-gallery-seg-btn${this.state.density === val ? " is-active" : ""}`,
        text: label,
        attr: { type: "button", "data-pf-testid": `gallery-density-${val}` },
      });
      btn.addEventListener("click", () => this.setDensity(val));
    }

    // Quick behavioral toggles
    const toggleSeg = controls.createDiv({ cls: "pf-gallery-seg" });
    const glassBtn = toggleSeg.createEl("button", {
      cls: `pf-gallery-seg-btn${this.state.liquidGlass ? " is-active" : ""}`,
      text: "毛玻璃",
      attr: { type: "button", "data-pf-testid": "gallery-toggle-glass" },
    });
    glassBtn.addEventListener("click", () => {
      this.state.liquidGlass = !this.state.liquidGlass;
      this.applyScopeClasses();
      this.renderTopbar();
    });

    const motionBtn = toggleSeg.createEl("button", {
      cls: `pf-gallery-seg-btn${this.state.reduceMotion ? " is-active" : ""}`,
      text: "减弱动效",
      attr: { type: "button", "data-pf-testid": "gallery-toggle-motion" },
    });
    motionBtn.addEventListener("click", () => {
      this.state.reduceMotion = !this.state.reduceMotion;
      this.applyScopeClasses();
      this.renderTopbar();
    });

    const narrowBtn = toggleSeg.createEl("button", {
      cls: `pf-gallery-seg-btn${this.state.narrowPreview ? " is-active" : ""}`,
      text: "520px 窄屏",
      attr: { type: "button", "data-pf-testid": "gallery-toggle-narrow" },
    });
    narrowBtn.addEventListener("click", () => {
      this.setNarrowPreview(!this.state.narrowPreview);
    });

    const search = controls.createEl("input", {
      cls: "pf-gallery-search",
      type: "search",
      placeholder: "筛选组件 / 面板...",
      value: this.state.searchQuery,
      attr: { "data-pf-testid": "gallery-search-input" },
    }) as HTMLInputElement;
    search.addEventListener("input", () => {
      this.setSearchQuery(search.value);
    });
  }

  private renderNav(): void {
    this.navEl.empty();
    this.navBtnEls.clear();

    const groups: StorySection["group"][] = [
      "基础系统",
      "UIKit 原语",
      "核心视图",
      "设置与边界态",
    ];

    for (const grp of groups) {
      const items = this.sections.filter((s) => s.group === grp);
      if (items.length === 0) continue;
      const box = this.navEl.createDiv();
      box.createDiv({ cls: "pf-gallery-nav-group-title", text: grp });
      for (const sec of items) {
        const btn = box.createEl("button", {
          cls: `pf-gallery-nav-item${this.activeSectionId === sec.id ? " is-active" : ""}`,
          text: sec.title,
          attr: { type: "button", "data-pf-section": sec.id },
        }) as HTMLButtonElement;
        btn.addEventListener("click", () => {
          this.activeSectionId = sec.id;
          this.updateActiveNav();
          this.sectionEls
            .get(sec.id)
            ?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
        this.navBtnEls.set(sec.id, btn);
      }
    }
  }

  private updateActiveNav(): void {
    for (const [id, btn] of this.navBtnEls.entries()) {
      btn.classList.toggle("is-active", id === this.activeSectionId);
    }
  }

  private filterSections(): void {
    const q = this.state.searchQuery.trim().toLowerCase();
    for (const sec of this.sections) {
      const hay = `${sec.title} ${sec.subtitle} ${sec.keywords}`.toLowerCase();
      const visible = !q || hay.includes(q);
      const secEl = this.sectionEls.get(sec.id);
      const navEl = this.navBtnEls.get(sec.id);
      if (secEl) secEl.style.display = visible ? "" : "none";
      if (navEl) navEl.style.display = visible ? "" : "none";
    }
  }

  private async renderAllSections(): Promise<void> {
    this.canvasEl.empty();
    this.sectionEls.clear();
    const ctx = this.createSectionContext();

    for (const sec of this.sections) {
      if (this.destroyed) return;
      const card = this.canvasEl.createDiv({
        cls: "pf-gallery-section",
        attr: { "data-pf-section-id": sec.id },
      });
      applyElevation(card, "surface");
      this.sectionEls.set(sec.id, card);

      const head = card.createDiv({ cls: "pf-gallery-section-head" });
      const titleBox = head.createDiv();
      titleBox.createEl("h2", {
        cls: "pf-gallery-section-title",
        text: sec.title,
      });
      titleBox.createEl("p", {
        cls: "pf-gallery-section-desc",
        text: sec.subtitle,
      });
      renderBadge(head, sec.group, "neutral");

      const body = card.createDiv({ cls: "pf-gallery-section-body" });
      await safeMountPanel(body, sec.title, () => sec.render(body, ctx));
    }

    this.filterSections();
  }

  private buildSections(): StorySection[] {
    return [
      {
        id: "tokens-themes",
        group: "基础系统",
        title: "01 · 设计令牌、4 套配色与动效",
        subtitle:
          "Obsidian · 纯净极简 · 中性灰阶 · 暖纸阅读 四主题 × Light/Dark × 5 级阴影层级 × 图标矩阵",
        keywords:
          "theme tokens palette obsidian minimal slate zinc warm elevation motion icons",
        render: (host, ctx) => {
          const isDark = ctx.state.mode === "dark";
          const activeTokens = tokensFor(
            ctx.state.preset,
            isDark,
            ctx.state.density,
            ctx.state.liquidGlass
          );

          renderInlineBanner(host, {
            tone: "info",
            icon: "palette",
            message: `当前作用域：${ctx.state.preset.toUpperCase()} · ${isDark ? "Dark" : "Light"} · 密度 ${ctx.state.density} · Surface ${activeTokens.surface} · Accent ${activeTokens.accent} · Control ${activeTokens.controlHeight}px · Row ${activeTokens.rowHeight}px`,
          });

          // 4 Theme presets swatch matrix
          const presetGrid = host.createDiv({ cls: "pf-gallery-grid-4" });
          for (const preset of [
            "obsidian",
            "asterlab",
            "zinc",
            "warm",
          ] as const) {
            const tk = tokensFor(
              preset,
              isDark,
              ctx.state.density,
              ctx.state.liquidGlass
            );
            const tile = presetGrid.createDiv({
              cls: "pf-gallery-swatch-card",
            });
            tile.style.background = tk.surface;
            tile.style.color = tk.text;
            tile.style.borderColor = tk.borderStrong;

            const top = tile.createDiv({ cls: "pf-kit-section-header" });
            top.createSpan({
              text: preset.toUpperCase(),
              cls: "pf-gallery-panel-title",
            }).style.color = tk.text;
            if (preset === ctx.state.preset) {
              renderBadge(top, "当前", "accent");
            }

            const bar = tile.createDiv({ cls: "pf-gallery-swatch-bar" });
            for (const c of [
              tk.canvas,
              tk.surface,
              tk.accent,
              tk.textMuted,
              tk.text,
            ]) {
              const seg = bar.createDiv();
              seg.style.flex = "1";
              seg.style.background = c;
            }
            tile.createDiv({
              text: `${tk.surface} · ${tk.accent}`,
              cls: "pf-kit-list-item-sub pf-tnum",
            }).style.color = tk.textMuted;

            const pickBtn = tile.createEl("button", {
              text: "应用预设",
              cls: "pf-btn pf-btn-quiet pf-btn-sm",
              attr: { type: "button" },
            });
            pickBtn.addEventListener("click", () =>
              ctx.controller.setPreset(preset)
            );
          }

          // Elevation 5-tier + Motion 4-tier
          const midGrid = host.createDiv({ cls: "pf-gallery-grid-2" });
          const elevPanel = midGrid.createDiv({ cls: "pf-gallery-panel" });
          renderSectionHeader(elevPanel, {
            title: "五级表面海拔（Elevation Stack）",
            meta: "5 层",
          });
          const elevRow = elevPanel.createDiv({ cls: "pf-gallery-grid-3" });
          for (const tier of [
            "canvas",
            "surface",
            "card",
            "floating",
            "modal",
          ] as ElevationTier[]) {
            const box = elevRow.createDiv({ cls: "pf-gallery-panel" });
            applyElevation(box, tier);
            box.createSpan({ text: tier, cls: "pf-kit-list-item-title" });
            box.createSpan({
              text: `pf-elev-${tier}`,
              cls: "pf-kit-list-item-sub",
            });
          }

          const motionPanel = midGrid.createDiv({ cls: "pf-gallery-panel" });
          renderSectionHeader(motionPanel, {
            title: "四级物理动效与校验轻晃（Motion + Nudge）",
            meta: `${MOTION_TOKENS.micro.durationMs}ms–${MOTION_TOKENS.fluid.durationMs}ms`,
          });
          const motionMeta = motionPanel.createDiv({
            cls: "pf-kit-banner-msg pf-tnum",
            text: `Micro ${MOTION_TOKENS.micro.durationMs}ms · Snappy ${MOTION_TOKENS.snappy.durationMs}ms · Fluid ${MOTION_TOKENS.fluid.durationMs}ms · Hero ${MOTION_TOKENS.hero.durationMs}ms`,
          });
          void motionMeta;
          const motionBtns = motionPanel.createDiv({
            cls: "pf-gallery-controls",
          });
          const nudgeTarget = motionPanel.createDiv({
            cls: "pf-gallery-panel",
            text: "点击右侧按钮触发 260ms ±5px 验证抖动（pf-nudge）或 Toast / SidePeek 滑入",
          });
          renderActionButton(motionBtns, {
            label: "触发 pf-nudge 抖动",
            variant: "secondary",
            onClick: () => applyNudge(nudgeTarget),
          });
          renderActionButton(motionBtns, {
            label: "弹出 Toast",
            variant: "secondary",
            onClick: () =>
              ctx.toast.push({
                message: "ToastQueue 测试消息 · 支持撤销",
                tone: "success",
                undoLabel: "撤销",
                onUndo: () =>
                  ctx.toast.push({ message: "已撤销刚才的操作", tone: "info" }),
              }),
          });
          const stackBtn = motionBtns.createEl("button", {
            cls: "pf-btn pf-btn-secondary",
            text: "演示 3 层堆叠 Toast",
            attr: {
              type: "button",
              "data-pf-testid": "gallery-toast-stack-demo",
            },
          });
          stackBtn.addEventListener("click", () => {
            ctx.toast.push({
              message: "1. 已完成 Zotero 元数据差异校验",
              tone: "info",
            });
            ctx.toast.push({
              message: "2. 后台队列正在重排 KEY_INCOMPLETE",
              tone: "warning",
            });
            ctx.toast.push({
              message: "3. 已写入 KEY_DONE 认知记忆 · 悬停可展开",
              tone: "success",
              undoLabel: "撤销",
              onUndo: () =>
                ctx.toast.push({ message: "已撤销最新更新", tone: "info" }),
            });
          });
          renderActionButton(motionBtns, {
            label: "打开 SidePeek 抽屉",
            variant: "primary",
            onClick: () =>
              ctx.openSidePeek({
                id: "gallery-demo-peek",
                title: "UIKit SidePeek 实例",
                subtitle: "ESC / 遮罩可关闭 · LayerStack 托管",
                bodyText:
                  "在 CellPlanner UIKit 中，复杂详情优先滑出右侧 SidePeek，而非切走当前表格上下文。",
              }),
          });

          // Categorical palette + Icon grid
          const palPanel = host.createDiv({ cls: "pf-gallery-panel" });
          renderSectionHeader(palPanel, {
            title: "科学分类 8 色板（Categorical Scientific Palette）",
            meta: "8 色",
          });
          const palStrip = palPanel.createDiv({ cls: "pf-gallery-swatch-bar" });
          for (const hex of categoricalPalette(isDark)) {
            const cell = palStrip.createDiv();
            cell.style.flex = "1";
            cell.style.background = hex;
            cell.title = hex;
          }

          const iconPanel = host.createDiv({ cls: "pf-gallery-panel" });
          renderSectionHeader(iconPanel, {
            title: "矢量图标体系（Lucide 1.65px 线性 SVG）",
            meta: `${ALL_ICON_NAMES.length} 个`,
          });
          const iconGrid = iconPanel.createDiv({ cls: "pf-gallery-icon-grid" });
          for (const iconName of ALL_ICON_NAMES) {
            const tile = iconGrid.createDiv({ cls: "pf-gallery-icon-tile" });
            const holder = tile.createSpan({ cls: "pf-kit-list-item-icon" });
            setPfIcon(holder, iconName);
            tile.createSpan({ text: iconName });
          }
        },
      },
      {
        id: "uikit-engines",
        group: "UIKit 原语",
        title: "02 · UIKit 六大交互引擎与原语",
        subtitle:
          "FilterBar 条件构建 · ScrubNumber 拖曳微调 · CommandRegistry + Keycap · ContextMenu · SidePeek · Six-State 徽章",
        keywords:
          "filter bar scrub number commands keycap context menu toast side peek badges list item",
        render: (host, ctx) => {
          const env = createGalleryMockEnv();
          const allRows = Object.values(env.snapshot.rows);

          // 1. Live FilterBar Engine
          const filterPanel = host.createDiv({ cls: "pf-gallery-panel" });
          const filterState = new FilterBarState();
          const countSlot = filterPanel.createDiv();
          const barSlot = filterPanel.createDiv();
          const matchesFilter = (r: (typeof allRows)[number]): boolean => {
            const q = filterState.query.trim().toLowerCase();
            if (q) {
              const hay =
                `${r.title} ${r.first_author} ${r.journal}`.toLowerCase();
              if (!hay.includes(q)) return false;
            }
            for (const f of filterState.active) {
              const val = String(
                (r as unknown as Record<string, unknown>)[f.fieldKey] ?? ""
              );
              if (val !== f.value) return false;
            }
            return true;
          };
          const renderFilterArea = () => {
            const matched = allRows.filter(matchesFilter);
            countSlot.empty();
            renderSectionHeader(countSlot, {
              title: "FilterBar 多条件筛选与保存视图",
              meta: `命中 ${matched.length} / ${allRows.length} 篇`,
            });
            barSlot.empty();
            renderFilterBar(barSlot, {
              state: filterState,
              fields: GALLERY_FILTER_FIELDS,
              savedViews: GALLERY_SAVED_VIEWS,
              searchPlaceholder: "搜索标题 / 作者 / 期刊...",
              layerStack: ctx.layerStack,
              onChange: renderFilterArea,
            });
          };
          renderFilterArea();

          const grid2 = host.createDiv({ cls: "pf-gallery-grid-2" });

          // 2. ScrubNumber + HoldToConfirm + ContextMenu
          const leftBox = grid2.createDiv({ cls: "pf-gallery-panel" });
          renderSectionHeader(leftBox, {
            title: "ScrubNumber 数值拖曳 & HoldToConfirm 安全确认",
          });
          const scrubRow = leftBox.createDiv({ cls: "pf-gallery-controls" });
          renderScrubNumber(scrubRow, 5.0, {
            label: "最低 IF",
            unit: "分",
            min: 0,
            max: 50,
            step: 0.5,
            decimals: 1,
            onCommit: (v) =>
              ctx.toast.push({
                message: `更新 IF 阈值：${v.toFixed(1)}`,
                tone: "info",
              }),
          });
          renderScrubNumber(scrubRow, 12, {
            label: "Top-K 片段",
            min: 4,
            max: 40,
            step: 1,
            decimals: 0,
          });
          renderScrubNumber(scrubRow, 4, {
            label: "OCR 并发数",
            min: 1,
            max: 12,
            step: 1,
            decimals: 0,
          });

          const ctxTarget = leftBox.createDiv({
            cls: "pf-kit-banner pf-kit-banner--info",
            text: "在此卡片点击鼠标右键（或触发上下文菜单），测试视口防溢出 ContextMenu 引擎",
          });
          ctxTarget.style.cursor = "context-menu";
          attachContextMenu(
            ctxTarget,
            () => [
              {
                label: "在侧车阅读器打开 PDF",
                icon: "book-open",
                shortcut: "Mod+Enter",
                onSelect: () =>
                  ctx.toast.push({
                    message: "菜单执行：打开侧车 PDF",
                    tone: "success",
                  }),
              },
              {
                label: "队列重跑全文解析",
                icon: "refresh-cw",
                checked: true,
                onSelect: () =>
                  ctx.toast.push({
                    message: "菜单执行：队列 OCR",
                    tone: "info",
                  }),
              },
              { kind: "separator" },
              {
                label: "移除测试记录",
                icon: "trash-2",
                danger: true,
                onSelect: () =>
                  ctx.toast.push({
                    message: "菜单执行：危险项点击",
                    tone: "warning",
                  }),
              },
            ],
            { layerStack: ctx.layerStack, hostEl: host }
          );

          const holdWrap = leftBox.createDiv({ cls: "pf-gallery-controls" });
          renderHoldToConfirm(holdWrap, {
            label: "按住 0.8s 确认批量重置",
            confirmedLabel: "已重置队列",
            durationMs: 800,
            onConfirm: () =>
              ctx.toast.push({
                message: "HoldToConfirm 长按确认完成",
                tone: "danger",
              }),
          });

          // 3. CommandRegistry + ListItem + Keycap + Badges
          const rightBox = grid2.createDiv({ cls: "pf-gallery-panel" });
          renderSectionHeader(rightBox, {
            title: "CommandRegistry 命令注册表 & ListItem / Keycap",
          });
          const cmdReg = new CommandRegistry();
          for (const spec of buildGalleryDemoCommands((msg) =>
            ctx.toast.push({ message: msg, tone: "success" })
          )) {
            cmdReg.register(spec);
          }
          for (const cmd of cmdReg.all()) {
            const chord = cmdReg.shortcutFor(cmd.id);
            renderListItem(rightBox, {
              title: cmd.title,
              subtitle: cmd.category,
              renderStart: (slot) => setPfIcon(slot, "terminal", 14),
              renderEnd: chord
                ? (slot) => renderKeycap(slot, chord)
                : undefined,
              onClick: () => cmd.run(),
            });
          }

          // 4. Existing PaperForge primitives showcase
          const primBox = host.createDiv({ cls: "pf-gallery-panel" });
          renderSectionHeader(primBox, {
            title:
              "PaperForge 业务原语：六态徽章 · 按钮层级 · 活动进度行 · 可折叠披露 · 空态",
          });
          const badgeRow = primBox.createDiv({ cls: "pf-gallery-controls" });
          for (const st of [
            "ready",
            "checking",
            "not_enabled",
            "setup_required",
            "action_required",
            "detection_failed",
          ] as const) {
            renderStatusBadge(badgeRow, st);
          }
          const btnRow = primBox.createDiv({ cls: "pf-gallery-controls" });
          renderActionButton(btnRow, {
            label: "主要操作 CTA",
            variant: "primary",
            onClick: () => {},
          });
          renderActionButton(btnRow, {
            label: "次要按钮",
            variant: "secondary",
            onClick: () => {},
          });
          renderActionButton(btnRow, {
            label: "静默幽灵按钮",
            variant: "ghost",
            onClick: () => {},
          });
          renderKeycap(btnRow, "Mod+Shift+O");

          renderActivityRow(primBox, {
            label: "后台队列解析全文 (KEY_PROC)",
            progress: { current: 2, total: 5 },
            scope: "骨科集合",
            stopLabel: "停止",
            onStop: () =>
              ctx.toast.push({ message: "模拟中断后台队列", tone: "warning" }),
          });
          renderDisclosure(primBox, {
            title: "高级选项与技术标识（默认折叠披露）",
            renderBody: (b) => {
              b.createEl("div", {
                text: "zotero_key=KEY_DONE · sha256=e3b0c442 · seq=42",
                cls: "pf-kit-banner-msg pf-tnum",
              });
            },
          });
          renderEmptyState(primBox, {
            icon: "database",
            title: "零命中空状态范式",
            subtitle:
              "当前筛选条件未匹配到文献记录，可点击右侧按钮一键清空筛选。",
            actionLabel: "清空筛选",
            onAction: () =>
              ctx.toast.push({ message: "已触发空状态恢复动作", tone: "info" }),
          });
        },
      },
      {
        id: "base-workbench",
        group: "核心视图",
        title: "03 · Obsidian Bases 文献库工作台 (`PaperForgeBasesView`)",
        subtitle:
          "原生分组小圆点 + 自定义「课题优先级」列 + 多选表头上下文栏 + 零命中空态",
        keywords:
          "bases table view paperforge-table literature hub group multi-select",
        render: (host, ctx) => {
          const env = createGalleryMockEnv({
            populatedMemory: true,
            ocrRunning: true,
          });
          const panelA = host.createDiv({ cls: "pf-gallery-panel" });
          panelA.createDiv({
            cls: "pf-gallery-panel-title",
            text: "A. 分组表格视图（骨科 / 运动医学 + 状态胶囊）",
          });
          const mountA = panelA.createDiv({ cls: "pf-ob-bases-view-mount" });
          const bvA = new PaperForgeBasesView(
            {} as never,
            mountA,
            env.plugin as never
          );
          (bvA as unknown as { app: unknown }).app = env.app;
          bvA.config = {
            getOrder: () => [
              "file.name",
              "note.first_author",
              "note.year",
              "note.journal",
              "note.impact_factor",
              "note.priority",
              "note.ocr_status",
              "note.annotations",
            ],
            getDisplayName: (id: string) =>
              id === "note.priority" ? "课题优先级" : "",
          } as never;
          const grpOrtho = makeGalleryBaseEntries(env.snapshot, [
            "KEY_DONE",
            "KEY_PROC",
            "KEY_PENDING",
            "KEY_INCOMPLETE",
          ]);
          const grpSports = makeGalleryBaseEntries(env.snapshot, [
            "KEY_FAILED",
            "KEY_NOPDF",
          ]);
          bvA.data = {
            groupedData: [
              {
                key: { data: "骨科", toString: () => "骨科" },
                hasKey: () => true,
                entries: grpOrtho,
              },
              {
                key: { data: "运动医学", toString: () => "运动医学" },
                hasKey: () => true,
                entries: grpSports,
              },
            ],
            data: [...grpOrtho, ...grpSports],
          } as never;
          bvA.onload();
          bvA.onDataUpdated();
          ctx.registerCleanup(() => bvA.unload());

          const grid = host.createDiv({ cls: "pf-gallery-grid-2" });
          const panelB = grid.createDiv({ cls: "pf-gallery-panel" });
          panelB.createDiv({
            cls: "pf-gallery-panel-title",
            text: "B. 多选表头上下文操作栏（已选 3 篇 → 批量操作）",
          });
          const mountB = panelB.createDiv({ cls: "pf-ob-bases-view-mount" });
          const bvB = new PaperForgeBasesView(
            {} as never,
            mountB,
            env.plugin as never
          );
          (bvB as unknown as { app: unknown }).app = env.app;
          bvB.config = {
            getOrder: () => [
              "file.name",
              "note.year",
              "note.impact_factor",
              "note.ocr_status",
            ],
            getDisplayName: () => "",
          } as never;
          bvB.data = {
            data: makeGalleryBaseEntries(env.snapshot, [
              "KEY_DONE",
              "KEY_PENDING",
              "KEY_FAILED",
            ]),
          } as never;
          bvB.onload();
          (bvB as unknown as { _selectedKeys: Set<string> })._selectedKeys =
            new Set(["KEY_DONE", "KEY_PENDING", "KEY_FAILED"]);
          bvB.render();
          ctx.registerCleanup(() => bvB.unload());

          const panelC = grid.createDiv({ cls: "pf-gallery-panel" });
          panelC.createDiv({
            cls: "pf-gallery-panel-title",
            text: "C. 零命中筛选空状态",
          });
          const mountC = panelC.createDiv({ cls: "pf-ob-bases-view-mount" });
          const bvC = new PaperForgeBasesView(
            {} as never,
            mountC,
            env.plugin as never
          );
          (bvC as unknown as { app: unknown }).app = env.app;
          bvC.data = {
            data: makeGalleryBaseEntries(env.snapshot, [
              "KEY_DONE",
              "KEY_PROC",
            ]),
          } as never;
          (
            bvC as unknown as { _localFilters: Record<string, unknown> }
          )._localFilters = {
            query: "nonexistent-biomaterial-xyz",
            status: "all",
          };
          bvC.onload();
          bvC.onDataUpdated();
          ctx.registerCleanup(() => bvC.unload());
        },
      },
      {
        id: "companion-sidebar",
        group: "核心视图",
        title: "04 · Companion 伴读侧栏三态 (`PaperForgeStatusView`)",
        subtitle:
          "全局工作区 · 单学科集合漏斗 · 单篇 5 维度持续演进研究认知记忆",
        keywords:
          "dashboard companion status view global collection paper living memory",
        render: (host, ctx) => {
          const grid = host.createDiv({ cls: "pf-gallery-grid-3" });

          const makeDash = (
            parent: HTMLElement,
            title: string,
            configure: (
              v: PaperForgeStatusView,
              snap: BaseTableSnapshotDto
            ) => void
          ) => {
            const box = parent.createDiv({ cls: "pf-gallery-panel" });
            box.createDiv({ cls: "pf-gallery-panel-title", text: title });
            const mount = box.createDiv();
            const env = createGalleryMockEnv({
              populatedMemory: true,
              ocrRunning: true,
            });
            const leaf = new WorkspaceLeaf();
            (leaf as unknown as { app: unknown }).app = env.app;
            const v = new PaperForgeStatusView(leaf);
            (v as unknown as { app: unknown }).app = env.app;
            (v as unknown as { containerEl: HTMLElement }).containerEl = mount;
            (v as unknown as Record<string, unknown>)._cachedStats = {
              paper_count: Object.keys(env.snapshot.rows).length,
            };
            (v as unknown as Record<string, unknown>)._cachedItems =
              Object.values(env.snapshot.rows).map((r) => ({
                ...r,
                authors: [r.first_author],
                pdf_path: r.has_pdf ? `storage:${r.zotero_key}/paper.pdf` : "",
              }));
            (v as unknown as Record<string, unknown>)._dashboardPermissions = {
              can_sync: true,
              can_ocr: true,
            };
            (v as unknown as Record<string, unknown>)._paperforgeVersion =
              "v2.2.0";
            v._buildPanel();
            configure(v, env.snapshot);
            ctx.registerCleanup(() => v.unload());
          };

          makeDash(grid, "A. Global 全局概览模式", (v) => {
            v._currentMode = "global";
            v._renderModeHeader("global");
            v._renderGlobalMode();
          });

          makeDash(grid, "B. Collection 学科集合模式", (v) => {
            v._currentMode = "collection";
            v._currentDomain = "骨科";
            v._renderModeHeader("collection");
            v._renderCollectionMode();
          });

          makeDash(grid, "C. Paper 单篇伴读 + 5维认知记忆", (v, snap) => {
            v._currentMode = "paper";
            v._currentPaperKey = "KEY_DONE";
            v._currentPaperEntry = {
              ...snap.rows.KEY_DONE,
              authors: ["Zhang W.", "Li M."],
              pdf_path: "storage:KEY_DONE/paper.pdf",
              next_step: "ready",
            };
            v._renderModeHeader("paper");
            v._renderPaperMode();
          });
        },
      },
      {
        id: "companion-search",
        group: "核心视图",
        title: "05 · 伴读检索引擎矩阵（M 元数据 / @ 混合深检 / 索引异常引导）",
        subtitle:
          "验证关键词元数据匹配、全文+图表双路混合深检与索引缺失时的可恢复引导卡",
        keywords: "search retrieve metadata hybrid deep vector index recovery",
        render: (host, ctx) => {
          const grid = host.createDiv({ cls: "pf-gallery-grid-3" });
          const mountSearchCard = (
            title: string,
            configure: (v: PaperForgeStatusView) => void
          ) => {
            const box = grid.createDiv({ cls: "pf-gallery-panel" });
            box.createDiv({ cls: "pf-gallery-panel-title", text: title });
            const mount = box.createDiv();
            const env = createGalleryMockEnv();
            const leaf = new WorkspaceLeaf();
            (leaf as unknown as { app: unknown }).app = env.app;
            const v = new PaperForgeStatusView(leaf);
            (v as unknown as { app: unknown }).app = env.app;
            (v as unknown as { containerEl: HTMLElement }).containerEl = mount;
            (v as unknown as Record<string, unknown>)._cachedStats = {
              paper_count: 6,
            };
            (v as unknown as Record<string, unknown>)._cachedItems =
              Object.values(env.snapshot.rows);
            (v as unknown as Record<string, unknown>)._dashboardPermissions = {
              can_sync: true,
              can_ocr: true,
            };
            v._buildPanel();
            v._currentMode = "global";
            v._renderModeHeader("global");
            v.renderSearchSection(v._contentEl);
            configure(v);
            ctx.registerCleanup(() => v.unload());
          };

          mountSearchCard("A. M 元数据即时筛选", (v) => {
            if (v._searchInput) v._searchInput.value = "PEMF 75 Hz";
            v._searchState = "results";
            v._searchDeep = false;
            v._searchResults = [
              {
                zotero_key: "KEY_DONE",
                title: "75 Hz PEMF Enhances Osteogenic Differentiation",
                first_author: "Zhang W.",
                journal: "Biomaterials",
                year: "2025",
                score: 0.94,
                snippet:
                  "PEMF stimulation at 75 Hz markedly enhanced osteogenic markers...",
              },
            ];
            v._renderSearchState();
          });

          mountSearchCard("B. @ 混合深检（正文 + Fig. 对象）", (v) => {
            if (v._searchInput)
              v._searchInput.value = "@nifedipine Ca2+ 22 min";
            v._searchState = "results";
            v._searchDeep = true;
            v._searchResults = [
              {
                zotero_key: "KEY_DONE",
                title: "Fig 1. Osteogenic ALP Peak",
                object_label: "figure_001",
                score: 0.97,
                snippet:
                  "Intracellular Ca2+ peaked at 22 min and was abolished by Nifedipine.",
              },
            ];
            v._renderSearchState();
          });

          mountSearchCard("C. 向量索引未建 / 重建引导", (v) => {
            v._searchState = "vectors-not-built";
            v._renderSearchState();
          });
        },
      },
      {
        id: "pdf-reader",
        group: "核心视图",
        title: "06 · 内置侧车 PDF 阅读器 (`PaperForgePdfView`)",
        subtitle:
          "macOS 预览双层工具栏（高亮 ▾ + 标记展开）+ 矢量批注层 + 520px 窄分栏自适应 + 源文件变更告警",
        keywords:
          "pdf annotator reader apple preview highlight markup shape vector narrow sha256",
        render: async (host, ctx) => {
          const panelFull = host.createDiv({ cls: "pf-gallery-panel" });
          panelFull.createDiv({
            cls: "pf-gallery-panel-title",
            text: "A. 完整桌面阅读态（渐进式工具栏 + AI/用户双向批注 + SVG 箭头与方框）",
          });
          const mountFull = panelFull.createDiv({
            cls: "pf-gallery-pdf-frame",
          });
          const envFull = createGalleryMockEnv({ pdfChanged: false });
          const vFull = await mountPdfSafely(mountFull, envFull, "KEY_DONE", {
            scale: 0.85,
            openMarkup: true,
          });
          ctx.registerCleanup(() => vFull.unload());

          const grid2 = host.createDiv({ cls: "pf-gallery-grid-2" });
          const panelNarrow = grid2.createDiv({ cls: "pf-gallery-panel" });
          panelNarrow.createDiv({
            cls: "pf-gallery-panel-title",
            text: "B. 520px 窄分栏 + PDF 变更警告 + 缩略图栏",
          });
          const narrowWrap = panelNarrow.createDiv({
            cls: "pf-gallery-narrow-box",
          });
          const mountNarrow = narrowWrap.createDiv({
            cls: "pf-gallery-pdf-frame is-narrow-frame",
          });
          const envChanged = createGalleryMockEnv({ pdfChanged: true });
          const vNarrow = await mountPdfSafely(
            mountNarrow,
            envChanged,
            "KEY_DONE",
            {
              scale: 0.65,
              narrow: true,
              thumbsTab: true,
            }
          );
          ctx.registerCleanup(() => vNarrow.unload());

          const panelEmpty = grid2.createDiv({ cls: "pf-gallery-panel" });
          panelEmpty.createDiv({
            cls: "pf-gallery-panel-title",
            text: "C. 无可用规范 PDF 空状态",
          });
          const mountEmpty = panelEmpty.createDiv();
          const envEmpty = createGalleryMockEnv();
          const vEmpty = await mountPdfSafely(
            mountEmpty,
            envEmpty,
            "KEY_NOPDF"
          );
          ctx.registerCleanup(() => vEmpty.unload());
        },
      },
      {
        id: "ocr-workspace",
        group: "核心视图",
        title: "07 · 高级 OCR 批量维护工作台 (`OcrWorkspaceView`)",
        subtitle:
          "多状态混合队列并发视图（已完成 · 解析中 · 部分缺失 · 异常失败 · 待处理）+ 右侧单篇诊断抽屉",
        keywords:
          "ocr workspace batch queue failed incomplete diagnostic fulltext",
        render: async (host, ctx) => {
          const env = createGalleryMockEnv({ ocrRunning: true });
          const panel = host.createDiv({ cls: "pf-gallery-panel" });
          const wsMount = panel.createDiv();
          const leaf = new WorkspaceLeaf();
          (leaf as unknown as { app: unknown }).app = env.app;
          const ws = new OcrWorkspaceView(leaf, env.plugin as never);
          (ws as unknown as { app: unknown }).app = env.app;
          wsMount.appendChild(ws.containerEl);
          await ws.onOpen();
          (ws as unknown as { selectedKey: string | null }).selectedKey =
            "KEY_FAILED";
          (ws as unknown as { _render: () => void })._render();
          ctx.registerCleanup(() => ws.unload());
        },
      },
      {
        id: "settings-center",
        group: "设置与边界态",
        title: "08 · 设置控制中心与模块详情 (`PaperForgeSettingTab`)",
        subtitle:
          "五大核心能力六态总览（含新增 Zinc 主题 & 3 档间距密度控制条）+ OCR / 智能检索详情面",
        keywords:
          "settings control center userstate ready checking setup_required action_required memory ocr",
        render: (host, ctx) => {
          const grid = host.createDiv({ cls: "pf-gallery-grid-2" });

          const left = grid.createDiv({
            cls: "pf-gallery-panel pf-ob-settings-pane",
          });
          left.createDiv({
            cls: "pf-gallery-panel-title",
            text: "A. Control Center 五模块总览 + 外观配置",
          });
          const envLeft = createGalleryMockEnv({
            allReady: false,
            ocrRunning: true,
            memoryStale: true,
          });
          envLeft.envelopes.ocr.activity_progress = { current: 2, total: 5 };
          const tabLeft = new PaperForgeSettingTab(
            envLeft.app,
            envLeft.plugin as never
          );
          (
            tabLeft as unknown as {
              _capabilityState: Record<string, ProbeEnvelope>;
            }
          )._capabilityState = envLeft.envelopes;
          (
            tabLeft as unknown as {
              _renderControlCenter: (c: HTMLElement) => void;
            }
          )._renderControlCenter(left.createDiv());
          ctx.registerCleanup(() => tabLeft.hide());

          const right = grid.createDiv({
            cls: "pf-gallery-panel pf-ob-settings-pane",
          });
          right.createDiv({
            cls: "pf-gallery-panel-title",
            text: "B. 外观主题 / 密度配置 & 智能检索（就绪态）",
          });
          const envRight = createGalleryMockEnv({ allReady: true });
          const tabRight = new PaperForgeSettingTab(
            envRight.app,
            envRight.plugin as never
          );
          (
            tabRight as unknown as {
              _capabilityState: Record<string, ProbeEnvelope>;
            }
          )._capabilityState = envRight.envelopes;
          (
            tabRight as unknown as {
              _renderAppearanceTab: (c: HTMLElement) => void;
            }
          )._renderAppearanceTab(right.createDiv());
          (
            tabRight as unknown as {
              _renderMemoryDetail: (c: HTMLElement) => void;
            }
          )._renderMemoryDetail(right.createDiv());
          ctx.registerCleanup(() => tabRight.hide());
        },
      },
      {
        id: "onboarding-domain",
        group: "设置与边界态",
        title: "09 · 新手心智引导（能力地图 · 1 步导入 · 按需解锁 AI）",
        subtitle:
          "10 秒看懂免费开箱 vs 按需解锁 · 引擎自动合入导入流 · Zotero 目录折叠自定义 · 分步详情兼容视图",
        keywords:
          "setup wizard onboarding express domain mode preview capability map",
        render: (host, ctx) => {
          const grid = host.createDiv({ cls: "pf-gallery-grid-2" });

          // Left: interactive stage switcher + Setup Wizard
          const left = grid.createDiv({
            cls: "pf-gallery-panel pf-ob-settings-pane",
          });
          const head = left.createDiv({ cls: "pf-kit-section-head" });
          head.createDiv({
            cls: "pf-gallery-panel-title",
            text: "A. 安装向导阶段演示（点击切换阶段）",
          });
          const switcher = left.createDiv({ cls: "pf-gallery-seg" });
          const stageMount = left.createDiv();

          let curStage: 1 | 2 | 3 | 4 | "express" = "express";
          const renderStage = () => {
            switcher.empty();
            stageMount.empty();
            for (const [id, label] of [
              ["express", "极速一屏"],
              [1, "Stage 1"],
              [2, "Stage 2"],
              [3, "Stage 3"],
              [4, "Stage 4"],
            ] as const) {
              const b = switcher.createEl("button", {
                cls: `pf-gallery-seg-btn${curStage === id ? " is-active" : ""}`,
                text: label,
                attr: { type: "button" },
              });
              b.addEventListener("click", () => {
                curStage = id;
                renderStage();
              });
            }
            const env = createGalleryMockEnv();
            (env.plugin.settings as Record<string, unknown>)._setup_complete =
              false;
            const tab = new PaperForgeSettingTab(env.app, env.plugin as never);
            (tab as unknown as Record<string, unknown>)._capabilityState =
              makeAllReadyEnvs(curStage === "express" || curStage >= 2);
            (tab as unknown as Record<string, unknown>)._attemptedProbes =
              new Set(["installation", "library", "ocr", "memory", "agent"]);
            (tab as unknown as Record<string, unknown>)._runtimeStatus = {
              runtime_ready: curStage !== 1,
              version_matches_expected: true,
              runtime_version: "2.2.0",
              expected_version: "2.2.0",
            };
            (tab as unknown as Record<string, unknown>)._runtimeStatusVersion =
              "2.2.0";
            (
              tab as unknown as { _setupExpressMode: boolean }
            )._setupExpressMode = curStage === "express";
            (
              tab as unknown as { _setupExpressAiOpen: boolean }
            )._setupExpressAiOpen = false;
            (
              tab as unknown as { _setupExpressAiTab: string }
            )._setupExpressAiTab = "embed";
            if (curStage === "express") {
              (env.plugin.settings as Record<string, unknown>).literature_dir =
                "PaperForge/Literature";
              (
                tab as unknown as { _zoteroDetectRan: boolean }
              )._zoteroDetectRan = true;
              (
                tab as unknown as { _detectedFolderCollisionMsg: string }
              )._detectedFolderCollisionMsg =
                "检测到库内已存在原有 Literature 文件夹：已自动隔离为 PaperForge/Literature。";
              (
                tab as unknown as { _zoteroDetectData: unknown }
              )._zoteroDetectData = {
                found: true,
                zotero_dir: "/mock-zotero",
                total_papers: 142,
                collections: env.collections,
              };
            } else {
              (tab as unknown as { _setupStage: number })._setupStage =
                curStage;
              (
                tab as unknown as { _setupOptionals: Record<string, boolean> }
              )._setupOptionals = {
                ocr: true,
                memory: true,
                agent: true,
              };
            }
            const tAny = tab as unknown as {
              containerEl: HTMLElement;
              display: () => void;
              _renderSetupJourney: (c: HTMLElement) => void;
            };
            tAny.containerEl = stageMount;
            tAny.display = () => {
              stageMount.empty();
              tAny._renderSetupJourney(stageMount);
            };
            tAny._renderSetupJourney(stageMount);
          };
          renderStage();
          void ctx;

          // Right: Live Domain Mode A/B Preview
          const right = grid.createDiv({
            cls: "pf-gallery-panel pf-ob-settings-pane",
          });
          right.createDiv({
            cls: "pf-gallery-panel-title",
            text: "B. Zotero 分类归档方式 A/B 实时预览",
          });
          const envPrev = createGalleryMockEnv();
          const boxA = right.createDiv({ cls: "pf-gallery-panel" });
          boxA.createDiv({
            cls: "pf-preview-pane-title",
            text: "选项 A（推荐）：按顶层分类建子目录",
          });
          renderDomainModePreview(boxA.createDiv(), {
            domainMode: "per_collection",
            collections: envPrev.collections,
            litDir: "PaperForge/Literature",
            isZh: true,
          });
          const boxB = right.createDiv({ cls: "pf-gallery-panel" });
          boxB.createDiv({
            cls: "pf-preview-pane-title",
            text: "选项 B：全部汇入统一目录",
          });
          renderDomainModePreview(boxB.createDiv(), {
            domainMode: "unified",
            collections: envPrev.collections,
            litDir: "PaperForge/Literature",
            isZh: true,
          });
        },
      },
      {
        id: "modals-edge",
        group: "设置与边界态",
        title: "10 · 弹窗家族、快速检索与极端文本压测",
        subtitle:
          "QuickSwitcher 建议行 · VersionRestoreModal · PaperForgeOrphanModal · ErrorAnatomy · CJK/Latin 超长混排防溢出",
        keywords:
          "quick switcher modal version restore orphan error anatomy overflow truncation contrast",
        render: (host, ctx) => {
          const env = createGalleryMockEnv();
          setLanguage(env.app, "zh");

          const topGrid = host.createDiv({ cls: "pf-gallery-grid-2" });

          // A. QuickSwitcher Suggestion Card Preview (Papers + > Command Mode)
          const qsPanel = topGrid.createDiv({ cls: "pf-gallery-panel" });
          qsPanel.createDiv({
            cls: "pf-gallery-panel-title",
            text: "A. PaperForgeQuickSwitcherModal 实时检索与 > 命令双栖预览",
          });
          const demoReg = new CommandRegistry();
          for (const spec of buildGalleryDemoCommands((msg) =>
            ctx.toast.push({ message: msg, tone: "success" })
          )) {
            demoReg.register(spec);
          }
          const qsMock = new PaperForgeQuickSwitcherModal(
            env.app,
            {
              ...(env.plugin as Record<string, unknown>),
              getCommandRegistry: () => demoReg,
            } as never,
            "open"
          );
          const qsShell = qsPanel.createDiv({ cls: "pf-qs-gallery-shell" });
          const qsPrompt = qsShell.createDiv({ cls: "pf-qs-gallery-prompt" });
          qsPrompt.createSpan({
            cls: "pf-qs-gallery-query",
            text: "PEMF  /  > ocr",
          });
          qsPrompt.createSpan({ cls: "pf-qs-kbd", text: "Cmd+K" });
          const qsList = qsShell.createDiv({ cls: "pf-qs-modal" });
          qsList.createDiv({ cls: "pf-qs-gallery-group", text: "匹配文献" });
          const rows = qsMock.getSuggestions("PEMF").slice(0, 2);
          rows.forEach((item, idx) => {
            const rowWrap = qsList.createDiv({
              cls: `suggestion-item${idx === 0 ? " is-selected" : ""}`,
            });
            qsMock.renderSuggestion(item, rowWrap);
          });
          qsList.createDiv({
            cls: "pf-qs-gallery-group",
            text: "命令模式 (> ocr)",
          });
          const cmdHits = qsMock.getSuggestions("> ocr").slice(0, 2);
          cmdHits.forEach((cmdItem) => {
            const rowWrap = qsList.createDiv({ cls: "suggestion-item" });
            qsMock.renderSuggestion(cmdItem, rowWrap);
          });

          // B. ErrorAnatomy + Long CJK/Latin Overflow Stress
          const stressPanel = topGrid.createDiv({ cls: "pf-gallery-panel" });
          stressPanel.createDiv({
            cls: "pf-gallery-panel-title",
            text: "B. ErrorAnatomy 故障解剖 & 超长中英混排防溢出边界测试",
          });
          renderErrorAnatomy(stressPanel, {
            whatHappened:
              "历史扫描 PDF（KEY_FAILED）在 PaddleOCR 远端超时后未能生成结构化块。",
            impact:
              "该文献暂不参与全文混合检索；已处理好的其他 247 篇不受影响。",
            nextStep:
              "在高级 OCR 批量维护工作台检查原 PDF 或点击「重新 OCR」重试。",
            onCopyDiagnostic: () =>
              ctx.toast.push({
                message: "已复制脱敏诊断上下文",
                tone: "success",
              }),
            copyLabel: t("problem_copy") || "复制诊断信息",
            impactLabel: t("problem_impact") || "影响：",
            nextLabel: t("problem_next") || "建议：",
          });
          renderListItem(stressPanel, {
            title:
              "Supercalifragilisticexpialidocious 2026 α-TCP/β-Ca₃(PO₄)₂ & Ca²⁺ 多中心研究 ($E = \\frac{1}{2}mv^2$) · https://doi.org/10.1016/j.biomaterials.2025.1234567890",
            subtitle:
              "Zhang W., Chen R., Liu K. · D:\\科研文献\\骨科生物材料\\2025 PEMF 综述\\paper.pdf · Nature Biomedical Engineering (IF 27.7)",
            selected: true,
            renderStart: (slot) => setPfIcon(slot, "file-text", 14),
            renderEnd: (slot) => renderBadge(slot, "2026 · 防溢出", "accent"),
          });

          // C. Modals rendered inline via __modalHost
          const modalsGrid = host.createDiv({ cls: "pf-gallery-grid-2" });

          const vrCard = modalsGrid.createDiv({ cls: "pf-gallery-panel" });
          vrCard.createDiv({
            cls: "pf-gallery-panel-title",
            text: "C. 版本恢复对比弹窗（VersionRestoreModal）",
          });
          const vrHost = vrCard.createDiv({ cls: "pf-gallery-modal-frame" });
          const envVr = createGalleryMockEnv();
          (envVr.app as unknown as { __modalHost: HTMLElement }).__modalHost =
            vrHost;
          const vrModal = new VersionRestoreModal(
            envVr.app,
            "KEY_DONE",
            [
              {
                label: "v3.2",
                created_at: "2026-11-18T10:00:00Z",
                source: "rebuild-v3",
                renderer_version: "v3.2",
                fulltext_size: 48200,
                source_path: ".paperforge/ocr/KEY_DONE/versions/v2/fulltext.md",
              },
              {
                label: "v3.1",
                created_at: "2026-10-02T08:15:00Z",
                source: "ocr-initial",
                renderer_version: "v3.1",
                fulltext_size: 47910,
                source_path: ".paperforge/ocr/KEY_DONE/versions/v1/fulltext.md",
              },
            ],
            "v3.2",
            ".paperforge/ocr/KEY_DONE/render/fulltext.md",
            async () => ({
              intent: "restore",
              key: "KEY_DONE",
              source_path: "",
              target_path: "",
              label: "v3.1",
              current_path: "",
              provenance_persisted: true,
            }),
            undefined,
            undefined,
            {
              "v3.2": [
                "# 3.1 Pulsed Electromagnetic Field Parameters",
                "",
                "75 Hz PEMF (1.2 mT, 2 h/day) significantly increased osteogenic ALP activity at day 7 (p < 0.01) and Ca2+ influx peaking at 22 min.",
                "",
                "> Fig 1 (Matched · caption bbox): Intracellular Ca2+ transient abolished by 10 µM nifedipine.",
              ].join("\n"),
              "v3.1": [
                "# 3.1 Pulsed Electromagnetic Field Parameters",
                "",
                "75 Hz PEMF (1.2 mT, 2 h/day) increased ALP activity at day 7 (p < 0.01) and Ca2+ influx.",
                "",
                "[Legacy block] Intracellular Ca2+ transient abolished by 10 uM nifedipine.",
              ].join("\n"),
            }
          );
          vrModal.open();
          ctx.registerCleanup(() => vrModal.close());

          const orpCard = modalsGrid.createDiv({ cls: "pf-gallery-panel" });
          orpCard.createDiv({
            cls: "pf-gallery-panel-title",
            text: "D. 孤儿工作区清理弹窗（PaperForgeOrphanModal）",
          });
          const orpHost = orpCard.createDiv({ cls: "pf-gallery-modal-frame" });
          const envOrp = createGalleryMockEnv();
          (envOrp.app as unknown as { __modalHost: HTMLElement }).__modalHost =
            orpHost;
          const orpModal = new PaperForgeOrphanModal(
            envOrp.app,
            [
              {
                key: "OLD_DEL01",
                title: "Removed Zotero Entry (Duplicate Preprint)",
                collection_path: "骨科",
              },
              {
                key: "OLD_DEL02",
                title: "Outdated Pilot Study Withdrawn from Collection",
                collection_path: "运动医学",
              },
            ],
            "/mock-vault",
            null
          );
          orpModal.open();
          ctx.registerCleanup(() => orpModal.close());
        },
      },
    ];
  }
}

function makeAllReadyEnvs(allReady: boolean): Record<string, ProbeEnvelope> {
  return createGalleryMockEnv({ allReady }).envelopes;
}
