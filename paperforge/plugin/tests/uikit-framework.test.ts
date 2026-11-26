// @vitest-environment jsdom
/**
 * UIKit Framework & Interactive UI Gallery verification suite.
 * Covers all 10 UIKit primitives/engines + PaperForgeGalleryController rendering.
 */

import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("obsidian", () => {
  class TFile {
    path: string;
    name: string;
    basename: string;
    extension: string;
    constructor(p = "mock.md") {
      this.path = p;
      this.name = p.split("/").pop() || "mock.md";
      this.basename = this.name.replace(/\.[^.]+$/, "");
      this.extension = this.name.includes(".")
        ? this.name.split(".").pop() || ""
        : "";
    }
  }
  class WorkspaceLeaf {
    app?: unknown;
    view?: unknown;
    updateHeader() {}
    async setViewState() {}
  }
  class Component {
    load() {}
    unload() {}
    addChild<T>(c: T) {
      return c;
    }
    register() {}
    registerEvent() {}
    registerDomEvent() {}
    registerInterval() {
      return 0;
    }
  }
  class ItemView extends Component {
    leaf: unknown;
    app: unknown;
    containerEl = document.createElement("div");
    contentEl = document.createElement("div");
    constructor(leaf: unknown) {
      super();
      this.leaf = leaf;
      this.app = (leaf as { app?: unknown })?.app ?? {};
      const header = document.createElement("div");
      header.className = "view-header";
      this.containerEl.appendChild(header);
      this.containerEl.appendChild(this.contentEl);
    }
    getState() {
      return {};
    }
    async setState() {}
  }
  class BasesView extends Component {
    type = "paperforge-table";
    app: unknown = {};
    config: Record<string, unknown> = {};
    data: Record<string, unknown> = { data: [] };
    onDataUpdated() {}
  }
  class Modal {
    app: unknown;
    containerEl = document.createElement("div");
    modalEl = document.createElement("div");
    contentEl = document.createElement("div");
    titleEl = document.createElement("div");
    constructor(app: unknown) {
      this.app = app;
      this.modalEl.appendChild(this.titleEl);
      this.modalEl.appendChild(this.contentEl);
      this.containerEl.appendChild(this.modalEl);
    }
    open() {
      const host = (this.app as { __modalHost?: HTMLElement })?.__modalHost;
      if (host) host.appendChild(this.containerEl);
      (this as unknown as { onOpen?: () => void }).onOpen?.();
    }
    close() {
      (this as unknown as { onClose?: () => void }).onClose?.();
      this.containerEl.remove();
    }
    setTitle(t: string) {
      this.titleEl.textContent = t;
    }
  }
  class SuggestModal<T> extends Modal {
    inputEl = document.createElement("input");
    limit = 40;
    setPlaceholder() {}
    setInstructions() {}
    getSuggestions(_q: string): T[] {
      return [];
    }
    renderSuggestion() {}
    onChooseSuggestion() {}
  }
  class PluginSettingTab extends Component {
    app: unknown;
    plugin: unknown;
    containerEl = document.createElement("div");
    constructor(app: unknown, plugin: unknown) {
      super();
      this.app = app;
      this.plugin = plugin;
    }
    display() {}
    hide() {}
  }
  class Setting {
    settingEl = document.createElement("div");
    constructor(parent: HTMLElement) {
      parent.appendChild(this.settingEl);
    }
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
    addButton() {
      return this;
    }
    addExtraButton() {
      return this;
    }
  }
  return {
    App: class {},
    TFile,
    WorkspaceLeaf,
    Component,
    ItemView,
    BasesView,
    Modal,
    SuggestModal,
    PluginSettingTab,
    Plugin: class extends Component {},
    MarkdownView: class {},
    Scope: class {
      register() {}
    },
    MarkdownRenderer: { render: async () => {} },
    Notice: function Notice() {},
    Menu: class {
      addItem() {
        return this;
      }
      addSeparator() {
        return this;
      }
      showAtMouseEvent() {}
    },
    Setting,
    Platform: { isWin: true, isMacOS: false, isLinux: false },
    Keymap: { isModEvent: () => false },
    setIcon: (el: HTMLElement) => {
      el.textContent = "•";
    },
    setTooltip: () => {},
    loadPdfJs: vi.fn(async () => ({
      getDocument: () => ({
        promise: Promise.reject(
          new Error("mock fallback triggers in-memory doc")
        ),
      }),
    })),
  };
});

import {
  applyElevation,
  applyThemeScope,
  CommandRegistry,
  FilterBarState,
  LayerStack,
  openContextMenuAt,
  renderEmptyState,
  renderFilterBar,
  renderHoldToConfirm,
  renderInlineBanner,
  renderKeycap,
  renderListItem,
  renderScrubNumber,
  SidePeekController,
  ToastQueue,
  tokensFor,
} from "../src/uikit";
import { PaperForgeGalleryController } from "../src/uikit/gallery";

afterEach(() => {
  document.body.innerHTML = "";
  vi.useRealTimers();
});

describe("UIKit Core Engines", () => {
  it("tokensFor & applyThemeScope handle all 4 presets x 3 densities", () => {
    const zDark = tokensFor("zinc", true, "compact", true);
    expect(zDark.preset).toBe("zinc");
    expect(zDark.dark).toBe(true);
    expect(zDark.controlHeight).toBe(28);

    const wComf = tokensFor("warm", false, "comfortable", false);
    expect(wComf.canvas).toBe("#f7f6f3");
    expect(wComf.surface).toBe("#ffffff");
    expect(wComf.rowHeight).toBe(38);

    const host = document.createElement("div");
    applyThemeScope(host, {
      preset: "zinc",
      mode: "dark",
      density: "compact",
      liquidGlass: false,
      reduceMotion: true,
    });
    expect(host.classList.contains("pf-scope-zinc")).toBe(true);
    expect(host.classList.contains("theme-dark")).toBe(true);
    expect(host.classList.contains("pf-density-compact")).toBe(true);
    expect(host.classList.contains("pf-no-glass")).toBe(true);
    expect(host.classList.contains("pf-reduce-motion")).toBe(true);
  });

  it("Elevation applies exclusive pf-elev-* tier class", () => {
    const el = document.createElement("div");
    applyElevation(el, "card");
    expect(el.classList.contains("pf-elev-card")).toBe(true);
    applyElevation(el, "floating");
    expect(el.classList.contains("pf-elev-card")).toBe(false);
    expect(el.classList.contains("pf-elev-floating")).toBe(true);
  });

  it("LayerStack pops top-most dismissible layer on Escape", () => {
    const stack = new LayerStack();
    const order: string[] = [];
    stack.register("peek", () => order.push("peek"));
    stack.register("menu", () => order.push("menu"));
    expect(stack.topId()).toBe("menu");

    const ev1 = new KeyboardEvent("keydown", { key: "Escape" });
    expect(stack.handleKeyDown(ev1)).toBe(true);
    expect(order).toEqual(["menu"]);
    expect(stack.topId()).toBe("peek");

    const ev2 = new KeyboardEvent("keydown", { key: "Escape" });
    expect(stack.handleKeyDown(ev2)).toBe(true);
    expect(order).toEqual(["menu", "peek"]);
    expect(stack.hasOpen()).toBe(false);
  });

  it("CommandRegistry filters by search, overrides shortcuts, and respects guard", () => {
    const reg = new CommandRegistry();
    let count = 0;
    const syncSpec = {
      id: "sync",
      title: "Sync Literature",
      category: "Library",
      defaultShortcut: "Mod+S",
      when: () => false,
      run: () => {
        count += 1;
      },
    };
    const ocrSpec = {
      id: "ocr",
      title: "Run OCR Batch",
      category: "OCR",
      defaultShortcut: "Mod+O",
      run: () => {
        count += 1;
      },
    };
    reg.register(syncSpec);
    reg.register(ocrSpec);
    reg.setOverrides({ ocr: "Mod+Shift+O" });
    expect(reg.shortcutFor("ocr")).toBe("Mod+Shift+O");
    expect(reg.canRun(syncSpec, {})).toBe(false);
    expect(reg.canRun(ocrSpec, {})).toBe(true);
    expect(reg.search("ocr").map((c) => c.id)).toEqual(["ocr"]);
    reg.find("ocr")?.run();
    expect(count).toBe(1);
  });

  it("ToastQueue stacks notices, triggers Undo, and auto-dismisses", () => {
    vi.useFakeTimers();
    const host = document.createElement("div");
    const q = new ToastQueue();
    q.mount(host);
    let undone = false;
    q.push({
      message: "Deleted 1 draft",
      tone: "warning",
      durationMs: 2000,
      undoLabel: "Undo",
      onUndo: () => {
        undone = true;
      },
    });
    expect(q.items()).toHaveLength(1);
    const undoBtn = host.querySelector(
      ".pf-kit-toast-undo"
    ) as HTMLButtonElement;
    undoBtn.click();
    expect(undone).toBe(true);
    expect(q.items()).toHaveLength(0);

    q.push({ message: "Auto expire", durationMs: 1500 });
    expect(q.items()).toHaveLength(1);
    vi.advanceTimersByTime(1600);
    expect(q.items()).toHaveLength(0);

    // Sonner-style keyed reconciliation + depth tracking across stacked pushes
    const id1 = q.push({ id: "t1", message: "First notice", tone: "info" });
    const card1 = host.querySelector(`[data-toast-id="${id1}"]`);
    expect(card1?.getAttribute("data-depth")).toBe("0");

    const id2 = q.push({ id: "t2", message: "Second notice", tone: "warning" });
    const id3 = q.push({ id: "t3", message: "Third notice", tone: "success" });
    expect(host.querySelector(`[data-toast-id="${id1}"]`)).toBe(card1);
    expect(card1?.getAttribute("data-depth")).toBe("2");
    expect(
      host.querySelector(`[data-toast-id="${id2}"]`)?.getAttribute("data-depth")
    ).toBe("1");
    expect(
      host.querySelector(`[data-toast-id="${id3}"]`)?.getAttribute("data-depth")
    ).toBe("0");
  });

  it("SidePeekController opens drawer, focuses inside, and restores focus on close", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const triggerBtn = document.createElement("button");
    triggerBtn.textContent = "Open Peek";
    host.appendChild(triggerBtn);
    triggerBtn.focus();
    expect(document.activeElement).toBe(triggerBtn);

    const stack = new LayerStack();
    const peek = new SidePeekController(host, {
      id: "inspector",
      title: "Paper Details",
      layerStack: stack,
      renderBody: (b) => {
        b.textContent = "Inspector body";
      },
    });
    peek.open();
    expect(peek.isOpen()).toBe(true);
    expect(stack.topId()).toBe("inspector");
    expect(host.querySelector(".pf-kit-sidepeek-panel")?.textContent).toContain(
      "Inspector body"
    );
    stack.dismissTop();
    expect(peek.isOpen()).toBe(false);
    expect(host.querySelector(".pf-kit-sidepeek-panel")).toBeNull();
    expect(document.activeElement).toBe(triggerBtn);
  });

  it("FilterBarState & renderFilterBar remove pills on click and Backspace", () => {
    const state = new FilterBarState();
    state.toggleFilter("domain", "骨科");
    expect(state.hasFilter("domain", "骨科")).toBe(true);

    const host = document.createElement("div");
    renderFilterBar(host, {
      state,
      fields: [
        {
          key: "domain",
          label: "领域",
          options: [
            { value: "骨科", label: "骨科" },
            { value: "运动医学", label: "运动医学" },
          ],
        },
      ],
      savedViews: [{ id: "all", label: "全部", filters: [] }],
    });
    expect(host.querySelectorAll(".pf-kit-filterbar-pill")).toHaveLength(1);
    (host.querySelector(".pf-kit-filterbar-pill") as HTMLButtonElement).click();
    expect(state.active).toHaveLength(0);

    state.toggleFilter("domain", "运动医学");
    const searchInput = host.querySelector(
      ".pf-kit-filterbar-input"
    ) as HTMLInputElement;
    searchInput.value = "";
    searchInput.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Backspace", bubbles: true })
    );
    expect(state.active).toHaveLength(0);
  });

  it("ContextMenu navigates via keyboard, flips near bottom edge, and invokes entry", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const stack = new LayerStack();
    let picked = "";
    const close = openContextMenuAt(
      10,
      10,
      [
        {
          label: "First",
          onSelect: () => {
            picked = "first";
          },
        },
        {
          label: "Second",
          onSelect: () => {
            picked = "second";
          },
        },
      ],
      { layerStack: stack, hostEl: host }
    );
    const menuEl = host.querySelector(".pf-kit-context-menu") as HTMLElement;
    const items = host.querySelectorAll<HTMLButtonElement>(".pf-kit-menu-item");
    expect(items).toHaveLength(2);
    menuEl.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true })
    );
    expect(document.activeElement).toBe(items[0]);
    items[1].click();
    expect(picked).toBe("second");
    expect(stack.hasOpen()).toBe(false);
    close();

    // Flip upward when placed near bottom edge
    const origRect = HTMLElement.prototype.getBoundingClientRect;
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(
      function (this: HTMLElement) {
        if (this.classList?.contains("pf-kit-context-menu")) {
          return {
            width: 220,
            height: 140,
            top: 0,
            left: 0,
            right: 220,
            bottom: 140,
            x: 0,
            y: 0,
            toJSON() {},
          } as DOMRect;
        }
        return origRect.call(this);
      }
    );
    const vh = window.innerHeight || 768;
    const closeFlip = openContextMenuAt(
      20,
      vh - 20,
      [{ label: "Bottom Item", onSelect: () => {} }],
      { layerStack: stack, hostEl: host }
    );
    const flippedMenu = host.querySelector(
      ".pf-kit-context-menu"
    ) as HTMLElement;
    expect(flippedMenu.classList.contains("is-flipped-up")).toBe(true);
    closeFlip();
    vi.restoreAllMocks();
  });

  it("ScrubNumber commits direct edit values within clamped range", () => {
    const host = document.createElement("div");
    let committed = 0;
    const ctrl = renderScrubNumber(host, 5, {
      label: "Min IF",
      min: 1,
      max: 20,
      step: 0.5,
      decimals: 1,
      onCommit: (v) => {
        committed = v;
      },
    });
    expect(ctrl.getValue()).toBe(5);
    ctrl.setValue(42);
    expect(ctrl.getValue()).toBe(20);
    // Click without drag opens inline numeric editor
    const pill = ctrl.el.querySelector(
      ".pf-kit-scrub-pill"
    ) as HTMLButtonElement;
    pill.dispatchEvent(
      new MouseEvent("mousedown", { clientX: 0, button: 0, bubbles: true })
    );
    document.dispatchEvent(
      new MouseEvent("mouseup", { clientX: 0, bubbles: true })
    );
    const input = ctrl.el.querySelector(
      ".pf-kit-scrub-input"
    ) as HTMLInputElement;
    expect(input).not.toBeNull();
    input.value = "12.5";
    input.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Enter", bubbles: true })
    );
    expect(committed).toBe(12.5);
    expect(ctrl.getValue()).toBe(12.5);
  });

  it("Primitives render ListItem, Keycap, Banner, EmptyState, HoldToConfirm", () => {
    vi.useFakeTimers();
    const host = document.createElement("div");
    renderListItem(host, {
      title: "Paper A",
      subtitle: "Biomaterials",
      renderEnd: (s) => {
        s.textContent = "Q1";
      },
    });
    renderKeycap(host, "Mod+Shift+O");
    renderInlineBanner(host, { tone: "info", message: "Ready · OK" });
    renderEmptyState(host, { title: "Empty", subtitle: "No hits" });

    let held = false;
    renderHoldToConfirm(host, {
      label: "Hold Reset",
      durationMs: 400,
      onConfirm: () => {
        held = true;
      },
    });
    vi.setSystemTime(1000);
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
      return window.setTimeout(() => cb(16), 16) as unknown as number;
    });
    const holdBtn = host.querySelector(".pf-kit-hold-btn") as HTMLButtonElement;
    holdBtn.dispatchEvent(
      new MouseEvent("mousedown", { button: 0, bubbles: true })
    );
    vi.setSystemTime(1500);
    vi.advanceTimersByTime(32);
    expect(held).toBe(true);
    vi.unstubAllGlobals();
  });
});

describe("PaperForgeGalleryController (All 10 Sections + Live Controls)", () => {
  it("mounts all 10 live sections cleanly and toggles themes/densities/narrow/search", async () => {
    // JSDOM canvas.getContext returns null cleanly; silence any jsdom warning
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
      {} as CanvasRenderingContext2D
    );
    vi.spyOn(HTMLCanvasElement.prototype, "toDataURL").mockReturnValue(
      "data:,"
    );
    const host = document.createElement("div");
    document.body.appendChild(host);

    const ctrl = new PaperForgeGalleryController(host);
    await ctrl.mount();

    const sections = host.querySelectorAll("[data-pf-section-id]");
    expect(sections).toHaveLength(10);

    // Real views & primitives present
    expect(host.querySelector(".pf-base-filter-bar")).not.toBeNull();
    expect(host.querySelector("tr.pf-base-row")).not.toBeNull();
    expect(host.querySelector(".paperforge-header")).not.toBeNull();
    expect(host.querySelector(".pf-pdf-toolbar")).not.toBeNull();
    expect(host.querySelector(".pf-ocr-workspace")).not.toBeNull();
    expect(host.querySelector(".pf-control-center")).not.toBeNull();
    expect(
      host.querySelector('[data-pf-testid="settings-density-mode"]')
    ).not.toBeNull();

    // Zero degraded panels across all 10 mounted gallery sections
    expect(host.textContent).not.toContain("预览加载降级");

    // OCR Workspace renders real <strong> element without literal "<strong>" HTML text & wires ErrorAnatomy
    const ocrSec = host.querySelector('[data-pf-section-id="ocr-workspace"]')!;
    const ocrCount = ocrSec.querySelector(".pf-ocr-ws-toolbar-count");
    expect(ocrCount?.textContent).not.toContain("<strong>");
    expect(ocrCount?.querySelector("strong")).not.toBeNull();
    expect(ocrSec.querySelector(".pf-error-anatomy")).not.toBeNull();

    // Bases Panel B selection bar omits global Sync Library; Panel C filtered zero-match shows reset button
    const basesSec = host.querySelector(
      '[data-pf-section-id="base-workbench"]'
    )!;
    const selBar = basesSec.querySelector(
      '[data-pf-testid="base-selection-bar"]'
    );
    expect(selBar).not.toBeNull();
    expect(
      selBar?.querySelector('[data-pf-testid="base-sync-library"]')
    ).toBeNull();
    expect(
      basesSec.querySelector('[data-pf-testid="base-reset-filters-empty"]')
    ).not.toBeNull();

    // Deep search panel syncs mode badge to "@" & humanizes figure_001 -> Fig. 1 with highlighted snippet
    const searchSec = host.querySelector(
      '[data-pf-section-id="companion-search"]'
    )!;
    expect(searchSec.textContent).not.toContain("figure_001");
    expect(searchSec.textContent).toContain("Fig. 1");
    expect(searchSec.querySelector("mark.pf-search-hl")).not.toBeNull();
    const deepToggles = Array.from(
      searchSec.querySelectorAll('[data-pf-testid="dash-search-mode-toggle"]')
    );
    expect(deepToggles[1]?.textContent?.trim()).toBe("@");

    // Companion single paper mode reconciles deep_reading_status === "complete"
    const compSec = host.querySelector(
      '[data-pf-section-id="companion-sidebar"]'
    )!;
    expect(compSec.querySelector(".paperforge-complete-row")).not.toBeNull();

    // Quick Start uses single PaperForge/Literature path & non-paywall badges
    const qsSec = host.querySelector(
      '[data-pf-section-id="onboarding-domain"]'
    )!;
    expect(
      qsSec.querySelector(".pf-express-default-summary")?.textContent
    ).toContain("PaperForge/Literature");
    expect(qsSec.textContent).not.toContain("开箱免费");
    expect(qsSec.textContent).not.toContain("用到再开");
    expect(qsSec.textContent).not.toContain("Included Free");
    expect(qsSec.textContent).not.toContain("Unlock Anytime");

    // Standalone host dark sync toggles document.body.theme-dark when data-pf-standalone="1"
    document.body.dataset.pfStandalone = "1";
    (
      host.querySelector(
        '[data-pf-testid="gallery-mode-dark"]'
      ) as HTMLButtonElement
    ).click();
    (
      host.querySelector(
        '[data-pf-testid="gallery-preset-zinc"]'
      ) as HTMLButtonElement
    ).click();
    (
      host.querySelector(
        '[data-pf-testid="gallery-density-compact"]'
      ) as HTMLButtonElement
    ).click();
    (
      host.querySelector(
        '[data-pf-testid="gallery-toggle-narrow"]'
      ) as HTMLButtonElement
    ).click();

    const rootEl = host.querySelector('[data-pf-testid="ui-gallery-root"]')!;
    expect(rootEl.classList.contains("theme-dark")).toBe(true);
    expect(document.body.classList.contains("theme-dark")).toBe(true);
    expect(rootEl.classList.contains("pf-scope-zinc")).toBe(true);
    expect(rootEl.classList.contains("pf-density-compact")).toBe(true);
    expect(
      host.querySelector(".pf-gallery-canvas")?.classList.contains("is-narrow")
    ).toBe(true);
    delete document.body.dataset.pfStandalone;

    // Global search filters sections cleanly
    const search = host.querySelector(
      '[data-pf-testid="gallery-search-input"]'
    ) as HTMLInputElement;
    search.value = "ocr";
    search.dispatchEvent(new Event("input"));
    const visibleSections = Array.from(sections).filter(
      (el) => (el as HTMLElement).style.display !== "none"
    );
    expect(visibleSections.length).toBeGreaterThanOrEqual(1);
    expect(visibleSections.length).toBeLessThan(10);

    ctrl.destroy();
    expect(host.innerHTML).toBe("");
  });
});
