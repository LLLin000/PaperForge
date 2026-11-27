import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { JSDOM } from "jsdom";

const dom = new JSDOM("<!doctype html><html><body></body></html>");
(globalThis as any).document = dom.window.document;
(globalThis as any).window = dom.window;
(globalThis as any).HTMLElement = dom.window.HTMLElement;
(globalThis as any).navigator = {
  clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
};

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
    if (opts?.type !== undefined) el.type = opts.type;
    if (opts?.placeholder !== undefined) el.placeholder = opts.placeholder;
    if (opts?.value !== undefined) el.value = opts.value;
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
const notices: Array<{ msg: unknown; duration?: number; instance: any }> = [];

vi.mock("obsidian", () => ({
  App: class {},
  Notice: class {
    hidden = false;
    constructor(msg: unknown, duration?: number) {
      notices.push({ msg, duration, instance: this });
    }
    hide() {
      this.hidden = true;
    }
  },
  Menu: class {
    addItem() {
      return this;
    }
    addSeparator() {
      return this;
    }
    showAtMouseEvent() {}
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
    open() {}
    close() {}
  },
  MarkdownRenderer: class {},
  Component: class {},
  loadPdfJs: () => mockLoadPdfJs(),
}));

import { PaperForgePdfView } from "../src/views/pdf-annotator";
import { setLanguage } from "../src/i18n";

function makeBaseContext(annotations: any[] = [], pageCount = 1) {
  return {
    paper_id: "P_UPG",
    title: "PDF Upgrade Test Paper",
    pdf_abs_path: "D:/Z/P_UPG.pdf",
    pdf_vault_rel: "Z/P_UPG.pdf",
    pdf_locator: "Z/P_UPG.pdf",
    is_vault_relative: true,
    pdf_sha256: "sha_upg",
    page_count: pageCount,
    workspace_rel: "Literature/P_UPG",
    note_rel_path: "Literature/P_UPG/P_UPG.md",
    annotations,
  };
}

describe("PaperForgePdfView upgrade: Option B selection, CRUD closed-loop, and perf invariants", () => {
  beforeEach(() => {
    notices.length = 0;
    mockLoadPdfJs.mockReset();
    Object.defineProperty(dom.window.document, "hidden", {
      value: false,
      configurable: true,
    });
    Object.defineProperty(dom.window, "devicePixelRatio", {
      value: 1,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("renders zero DOM text spans, supports geometric drag/dblclick/triple-click selection, and copies sorted reading-order text on Ctrl+C", async () => {
    mockLoadPdfJs.mockResolvedValue({
      getDocument: () => ({
        promise: Promise.resolve({
          numPages: 1,
          getPage: async () => ({
            getViewport: ({ scale }: { scale: number }) => ({
              width: 600 * scale,
              height: 800 * scale,
              transform: [scale, 0, 0, -scale, 0, 800 * scale],
            }),
            render: () => ({ promise: Promise.resolve() }),
            getTextContent: async () => ({
              items: [
                {
                  str: "Left first line",
                  transform: [1, 0, 0, 12, 50, 700],
                  width: 180,
                  height: 12,
                },
                {
                  str: "Right first line",
                  transform: [1, 0, 0, 12, 340, 700],
                  width: 180,
                  height: 12,
                },
                {
                  str: "Left second line",
                  transform: [1, 0, 0, 12, 50, 680],
                  width: 180,
                  height: 12,
                },
              ],
            }),
          }),
        }),
      }),
    });

    const client: any = {
      getPdfContext: vi.fn().mockResolvedValue(makeBaseContext([], 1)),
      listAnnotations: vi.fn().mockResolvedValue([]),
    };
    const view = new PaperForgePdfView({} as any, { getClient: () => client });
    view.app = {
      vault: { adapter: { getResourcePath: (p: string) => p } },
      workspace: { on: vi.fn().mockReturnValue({}), offref: vi.fn() },
    } as any;
    setLanguage(view.app, "zh");

    try {
      await view.onOpen();
      await view.setState({ paperKey: "P_UPG", page: 1 }, { history: false });

    const pageEl = view.contentEl.querySelector(".pf-pdf-page") as HTMLElement;
    // Zero 1000-span DOM text layer bottleneck
    expect(pageEl.querySelectorAll(".pf-pdf-text-layer span")).toHaveLength(0);

    // Mock bounding rect for geometric hit-testing
    pageEl.getBoundingClientRect = () =>
      ({
        left: 0,
        top: 0,
        right: 600,
        bottom: 800,
        width: 600,
        height: 800,
      }) as DOMRect;

    // 1. Mouse drag in left column (y=96..118, x=55..235)
    pageEl.dispatchEvent(
      new dom.window.MouseEvent("mousedown", {
        button: 0,
        clientX: 55,
        clientY: 96,
        detail: 1,
        bubbles: true,
      })
    );
    pageEl.dispatchEvent(
      new dom.window.MouseEvent("mousemove", {
        clientX: 235,
        clientY: 118,
        bubbles: true,
      })
    );
    pageEl.dispatchEvent(
      new dom.window.MouseEvent("mouseup", {
        clientX: 235,
        clientY: 118,
        detail: 1,
        bubbles: true,
      })
    );

    expect(
      pageEl.querySelectorAll(".pf-pdf-sel-rect").length
    ).toBeGreaterThanOrEqual(2);
    expect(
      view.contentEl.querySelector('[data-pf-testid="pdf-selection-float-bar"]')
    ).not.toBeNull();

    // Ctrl+C copies sorted geometric selection text
    const writeClip = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(globalThis.navigator, "clipboard", {
      value: { writeText: writeClip },
      configurable: true,
    });
    view.contentEl.dispatchEvent(
      new dom.window.KeyboardEvent("keydown", {
        key: "c",
        ctrlKey: true,
        bubbles: true,
      })
    );
    expect(writeClip).toHaveBeenCalledWith(
      "Left first line\nLeft second line"
    );

    // 2. Double-click selects a single word ("first")
    pageEl.dispatchEvent(
      new dom.window.MouseEvent("dblclick", {
        clientX: 112,
        clientY: 96,
        bubbles: true,
      })
    );
    const wordData = (view as any)._getSelectionData();
    expect(wordData?.exactText).toBe("first");

    // 3. Triple-click selects paragraph in left column without jumping into right column
    pageEl.dispatchEvent(
      new dom.window.MouseEvent("mousedown", {
        button: 0,
        clientX: 60,
        clientY: 96,
        detail: 3,
        bubbles: true,
      })
    );
    pageEl.dispatchEvent(
      new dom.window.MouseEvent("mouseup", {
        clientX: 60,
        clientY: 96,
        detail: 3,
        bubbles: true,
      })
    );
    const paraData = (view as any)._getSelectionData();
    expect(paraData?.exactText).toBe("Left first line\nLeft second line");

      await view.onClose();
    } finally {
      setLanguage(view.app, "en");
    }
  });

  it("enforces CRUD closed-loop: click-outside/Escape dismissal, on-page delete/adopt, SVG clickability, Undo stack, Clear AI confirmation, and lensZh labels", async () => {
    mockLoadPdfJs.mockResolvedValue({
      getDocument: () => ({
        promise: Promise.resolve({
          numPages: 1,
          getPage: async () => ({
            getViewport: ({ scale }: { scale: number }) => ({
              width: 600 * scale,
              height: 800 * scale,
              transform: [scale, 0, 0, -scale, 0, 800 * scale],
            }),
            render: () => ({ promise: Promise.resolve() }),
            getTextContent: async () => ({ items: [] }),
          }),
        }),
      }),
    });

    const agentMethodAnn = {
      ann_id: "ann_agent_m",
      paper_id: "P_UPG",
      page: 1,
      kind: "highlight",
      color: "purple",
      intent: "general",
      author: "agent",
      lens: "methods",
      grounding_tier: "exact",
      exact_text: "Randomization used 1:1 block.",
      comment: "Check allocation concealment.",
      tags: [],
      rects: [[0.1, 0.2, 0.6, 0.24]],
      section_path: "Methods",
      block_id: "b1",
      figure_id: "",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "sha_upg",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };

    const agentCustomAnn = {
      ...agentMethodAnn,
      ann_id: "ann_agent_c",
      lens: "custom",
      grounding_tier: "fuzzy",
      rects: [[0.1, 0.3, 0.6, 0.34]],
      comment: "Custom follow-up",
    };

    const inkAnn = {
      ann_id: "ann_ink_1",
      paper_id: "P_UPG",
      page: 1,
      kind: "ink",
      color: "red",
      intent: "general",
      author: "user",
      exact_text: "",
      comment: "Freehand arrow",
      tags: [],
      rects: [[0.2, 0.4, 0.5, 0.6]],
      style: {
        points: [
          [0.2, 0.4],
          [0.5, 0.6],
        ],
        stroke_color: "#d64545",
        stroke_width: 2.5,
      },
      section_path: "",
      block_id: "",
      figure_id: "",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "sha_upg",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };

    const shapeAnn = {
      ...inkAnn,
      ann_id: "ann_shape_1",
      kind: "shape",
      comment: "Box around Fig 1",
      style: {
        shape_type: "rect",
        stroke_color: "#1d4ed8",
        fill_color: "transparent",
        stroke_width: 2,
      },
    };

    const addAnnotation = vi.fn().mockImplementation(async (_k, input) => ({
      ...inkAnn,
      ann_id: "ann_restored_1",
      page: input.page,
      kind: input.kind,
      rects: input.rects,
      comment: input.comment ?? "",
      style: input.style,
    }));
    const deleteAnnotation = vi.fn().mockResolvedValue({ deleted: true });
    const adoptAnnotation = vi.fn().mockResolvedValue({
      ...agentMethodAnn,
      author: "user",
      lens: "",
    });
    const clearAgentAnnotations = vi
      .fn()
      .mockResolvedValue({ paper_id: "P_UPG", deleted_count: 1 });

    const client: any = {
      getPdfContext: vi
        .fn()
        .mockResolvedValue(
          makeBaseContext([agentMethodAnn, agentCustomAnn, inkAnn, shapeAnn], 1)
        ),
      listAnnotations: vi.fn().mockResolvedValue([]),
      addAnnotation,
      deleteAnnotation,
      adoptAnnotation,
      clearAgentAnnotations,
    };

    const view = new PaperForgePdfView({} as any, { getClient: () => client });
    view.app = {
      vault: { adapter: { getResourcePath: (p: string) => p } },
      workspace: { on: vi.fn().mockReturnValue({}), offref: vi.fn() },
    } as any;
    setLanguage(view.app, "zh");

    try {
      await view.onOpen();
      await view.setState({ paperKey: "P_UPG", page: 1 }, { history: false });

    // lensZh mapping renders Chinese labels for "methods" and "custom"
    expect(view.contentEl.textContent).toContain("关键方法");
    expect(view.contentEl.textContent).toContain("专题追问");

    const pageEl = view.contentEl.querySelector(".pf-pdf-page") as HTMLElement;

    // 1. _showSelectionMiniBar closes on Escape and click-outside
    (view as any)._showSelectionMiniBar(pageEl, {
      pageNumber: 1,
      rects: [[0.1, 0.2, 0.4, 0.24]],
      exactText: "Sample",
    });
    expect(
      view.contentEl.querySelector('[data-pf-testid="pdf-selection-float-bar"]')
    ).not.toBeNull();
    dom.window.document.dispatchEvent(
      new dom.window.KeyboardEvent("keydown", { key: "Escape", bubbles: true })
    );
    expect(
      view.contentEl.querySelector('[data-pf-testid="pdf-selection-float-bar"]')
    ).toBeNull();

    (view as any)._showSelectionMiniBar(pageEl, {
      pageNumber: 1,
      rects: [[0.1, 0.2, 0.4, 0.24]],
      exactText: "Sample 2",
    });
    dom.window.document.body.dispatchEvent(
      new dom.window.Event("pointerdown", { bubbles: true })
    );
    expect(
      view.contentEl.querySelector('[data-pf-testid="pdf-selection-float-bar"]')
    ).toBeNull();

    // 2. _openCreatePopover closes on outside pointerdown & Escape
    view._openCreatePopover({
      anchorEl: pageEl,
      page: 1,
      rects: [[0.1, 0.2, 0.4, 0.24]],
      kind: "highlight",
      exactText: "Test quote",
    });
    expect(
      view.contentEl.querySelector('[data-pf-testid="pdf-create-popover"]')
    ).not.toBeNull();
    dom.window.document.body.dispatchEvent(
      new dom.window.Event("pointerdown", { bubbles: true })
    );
    expect(
      view.contentEl.querySelector('[data-pf-testid="pdf-create-popover"]')
    ).toBeNull();

    // 3. Clicking an AI overlay opens on-page popover with lens + grounding badge + direct Adopt button
    const aiBox = pageEl.querySelector(
      `[data-ann-id="${agentMethodAnn.ann_id}"]`
    ) as HTMLElement;
    aiBox.click();
    expect(
      view.contentEl.querySelector('[data-pf-testid="pdf-popover-agent-meta"]')
        ?.textContent
    ).toContain("关键方法");
    expect(
      view.contentEl.querySelector(
        '[data-pf-testid="pdf-popover-grounding-badge"]'
      )?.textContent
    ).toBe("exact");
    const directAdoptBtn = view.contentEl.querySelector(
      '[data-pf-testid="pdf-popover-adopt-btn"]'
    ) as HTMLButtonElement;
    expect(directAdoptBtn).not.toBeNull();
    directAdoptBtn.click();
    await vi.waitFor(() => {
      expect(adoptAnnotation).toHaveBeenCalledWith("P_UPG", "ann_agent_m");
    });

    // 4. SVG shapes & ink strokes have pointer-events: stroke while <svg> stays none, and clicking opens edit popover with Delete
    const svgLayer = pageEl.querySelector(".pf-pdf-svg-layer") as SVGElement;
    expect(svgLayer).not.toBeNull();
    const inkPolyline = svgLayer.querySelector(
      'polyline[data-ann-id="ann_ink_1"]'
    ) as SVGPolylineElement;
    const shapeRect = svgLayer.querySelector(
      'rect[data-ann-id="ann_shape_1"]'
    ) as SVGRectElement;
    expect(inkPolyline.style.pointerEvents).toBe("stroke");
    expect(shapeRect.style.pointerEvents).toBe("stroke");

    inkPolyline.dispatchEvent(
      new dom.window.MouseEvent("click", { bubbles: true })
    );
    const popDelBtn = view.contentEl.querySelector(
      '[data-pf-testid="pdf-popover-delete-btn"]'
    ) as HTMLButtonElement;
    expect(popDelBtn).not.toBeNull();
    popDelBtn.click();
    await vi.waitFor(() => {
      expect(deleteAnnotation).toHaveBeenCalledWith("P_UPG", "ann_ink_1");
    });
    expect(
      pageEl.querySelector('polyline[data-ann-id="ann_ink_1"]')
    ).toBeNull();

    // 5. Undo toast button or Ctrl+Z restores deleted ink annotation
    expect(notices.length).toBeGreaterThan(0);
    const lastNotice = notices[notices.length - 1];
    expect(lastNotice.msg).toBeInstanceOf(dom.window.DocumentFragment);
    view.contentEl.dispatchEvent(
      new dom.window.KeyboardEvent("keydown", {
        key: "z",
        ctrlKey: true,
        bubbles: true,
      })
    );
    await vi.waitFor(() => {
      expect(addAnnotation).toHaveBeenCalledWith(
        "P_UPG",
        expect.objectContaining({ page: 1, kind: "ink" })
      );
    });

    // 6. Clear AI requires 2-click confirmation
    const clearBtn = view.contentEl.querySelector(
      '[data-pf-testid="pdf-clear-ai-btn"]'
    ) as HTMLButtonElement;
    expect(clearBtn).not.toBeNull();
    clearBtn.click();
    expect(clearAgentAnnotations).not.toHaveBeenCalled();
    expect(clearBtn.getAttribute("data-confirming")).toBe("true");
    clearBtn.click();
    await vi.waitFor(() => {
      expect(clearAgentAnnotations).toHaveBeenCalledWith("P_UPG");
    });

      await view.onClose();
    } finally {
      setLanguage(view.app, "en");
    }
  });

  it("enforces performance invariants: DPR/pixel cap, renderTask.cancel(), canvas cap=5, visibilitychange release, debounced wheel zoom & state-changed reload, and blob thumbnails", async () => {
    vi.useFakeTimers();
    const cancelSpy = vi.fn();
    let rejectPendingRender: ((err: unknown) => void) | null = null;
    let renderCount = 0;

    mockLoadPdfJs.mockResolvedValue({
      getDocument: () => ({
        promise: Promise.resolve({
          numPages: 8,
          getPage: async () => ({
            getViewport: ({ scale }: { scale: number }) => ({
              width: 2200 * scale,
              height: 3000 * scale,
              transform: [scale, 0, 0, -scale, 0, 3000 * scale],
            }),
            render: () => {
              renderCount += 1;
              if (renderCount === 3) {
                return {
                  promise: new Promise<void>((_res, rej) => {
                    rejectPendingRender = rej;
                  }),
                  cancel: () => {
                    cancelSpy();
                    const err = new Error("Cancelled");
                    err.name = "RenderingCancelledException";
                    rejectPendingRender?.(err);
                  },
                };
              }
              return { promise: Promise.resolve(), cancel: cancelSpy };
            },
            getTextContent: async () => ({ items: [] }),
          }),
        }),
      }),
    });

    // Patch canvas getContext + toBlob + URL.createObjectURL/revokeObjectURL for deterministic test
    const origGetContext = dom.window.HTMLCanvasElement.prototype.getContext;
    const origToBlob = dom.window.HTMLCanvasElement.prototype.toBlob;
    (dom.window.HTMLCanvasElement.prototype as any).getContext = function () {
      return { setTransform: vi.fn(), drawImage: vi.fn() };
    };
    const toBlobSpy = vi.fn((cb: (b: Blob | null) => void) => {
      cb(new dom.window.Blob(["thumb"], { type: "image/jpeg" }));
    });
    (dom.window.HTMLCanvasElement.prototype as any).toBlob = toBlobSpy;

    const origCreateObjectURL = (URL as any).createObjectURL;
    const origRevokeObjectURL = (URL as any).revokeObjectURL;
    const createObjUrlSpy = vi.fn().mockReturnValue("blob:mock-thumb-1");
    const revokeObjUrlSpy = vi.fn();
    Object.defineProperty(URL, "createObjectURL", {
      value: createObjUrlSpy,
      configurable: true,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      value: revokeObjUrlSpy,
      configurable: true,
    });

    try {
      // Simulate 4x HiDPI screen -> must be capped <= 2 and total pixels <= 6_000_000
      Object.defineProperty(dom.window, "devicePixelRatio", {
        value: 4,
        configurable: true,
      });

      const stateListeners: Array<(payload?: unknown) => void> = [];
      const listAnnotations = vi.fn().mockResolvedValue([]);
      const client: any = {
        getPdfContext: vi.fn().mockResolvedValue(makeBaseContext([], 8)),
        listAnnotations,
      };
      const view = new PaperForgePdfView({} as any, {
        getClient: () => client,
      }) as any;
      view.app = {
        vault: { adapter: { getResourcePath: (p: string) => p } },
        workspace: {
          on: (_ev: string, cb: (p?: unknown) => void) => {
            stateListeners.push(cb);
            return cb;
          },
          offref: vi.fn(),
        },
      };

      await view.onOpen();
      await view.setState({ paperKey: "P_UPG", page: 1 }, { history: false });

      // 1. Pixel-budget cap: 2200*1.25 x 3000*1.25 = 2750 x 3750 = 10.3M > 6M -> scaled down <= 6_000_000
      const firstCanvas = view.contentEl.querySelector(
        ".pf-pdf-canvas"
      ) as HTMLCanvasElement;
      expect(firstCanvas.width * firstCanvas.height).toBeLessThanOrEqual(
        6_000_000
      );

      // 2. Thumbnails NOT generated when annotations tab is active
      expect(toBlobSpy).not.toHaveBeenCalled();

      // 3. Start render #3 (pending), then Ctrl+wheel zoom cancels stale task & previews CSS transform
      const pendingP3 = view._ensurePageRendered(3);
      const scrollEl = view._scrollEl as HTMLElement;
      scrollEl.dispatchEvent(
        new dom.window.WheelEvent("wheel", {
          deltaY: -100,
          ctrlKey: true,
          cancelable: true,
          bubbles: true,
        })
      );
      expect(view._pagesStageEl.style.transform).toContain("scale(");
      expect(cancelSpy).not.toHaveBeenCalled();

      // After 120ms debounce, zoom commits, clears transform, and cancels stale render task
      await vi.advanceTimersByTimeAsync(125);
      await pendingP3;
      expect(cancelSpy).toHaveBeenCalled();
      expect(view._pagesStageEl.style.transform).toBe("");

      // 4. Canvas LRU eviction caps rendered canvases at <= 5
      for (let p = 1; p <= 8; p++) {
        view._currentPage = p;
        await view._ensurePageRendered(p);
      }
      expect(view._renderedPages.size).toBeLessThanOrEqual(5);

      // 5. visibilitychange hidden releases all non-current canvases (even stale canvases cleared from _renderedPages)
      view._currentPage = 8;
      await view._ensurePageRendered(7);
      expect(view._renderedPages.size).toBeGreaterThan(1);
      // Simulate _syncZoomAndRerender clearing _renderedPages while leaving a stale canvas on page 7
      view._renderedPages.delete(7);
      expect(view.contentEl.querySelectorAll(".pf-pdf-canvas").length).toBeGreaterThan(1);
      Object.defineProperty(dom.window.document, "hidden", {
        value: true,
        configurable: true,
      });
      dom.window.document.dispatchEvent(
        new dom.window.Event("visibilitychange")
      );
      expect(Array.from(view._renderedPages)).toEqual([8]);
      expect(view.contentEl.querySelectorAll(".pf-pdf-canvas")).toHaveLength(1);

      // 6. Switching to Thumbs tab triggers async toBlob + createObjectURL, revoked on teardown
      const thumbsBtn = view.contentEl.querySelector(
        '[data-pf-testid="pdf-tab-thumbs"]'
      ) as HTMLButtonElement;
      thumbsBtn.click();
      expect(toBlobSpy).toHaveBeenCalled();
      expect(createObjUrlSpy).toHaveBeenCalled();

      // 7. Debounced state-changed coalesces burst of 4 events into 1 reload after 150ms
      stateListeners[0]({ changedKeys: ["P_UPG"] });
      stateListeners[0]({ changedKeys: ["P_UPG"] });
      stateListeners[0]({ changedKeys: ["P_UPG"] });
      stateListeners[0]({ changedKeys: ["P_UPG"] });
      expect(listAnnotations).not.toHaveBeenCalled();
      await vi.advanceTimersByTimeAsync(160);
      expect(listAnnotations).toHaveBeenCalledTimes(1);

      await view.onClose();
      expect(revokeObjUrlSpy).toHaveBeenCalledWith("blob:mock-thumb-1");
    } finally {
      (dom.window.HTMLCanvasElement.prototype as any).getContext =
        origGetContext;
      (dom.window.HTMLCanvasElement.prototype as any).toBlob = origToBlob;
      Object.defineProperty(URL, "createObjectURL", {
        value: origCreateObjectURL,
        configurable: true,
      });
      Object.defineProperty(URL, "revokeObjectURL", {
        value: origRevokeObjectURL,
        configurable: true,
      });
    }
  });
});
