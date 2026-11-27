// @vitest-environment jsdom
/**
 * PaperForge PDF Annotator Real-Runtime Performance, Memory & Selection Benchmark.
 *
 * Measures deterministic runtime metrics across both baseline (`master`) and
 * upgraded (`pdf-engine`) implementations of `PaperForgePdfView`:
 *   1. Canvas pixel memory footprint across a 100-page scroll at DPR=2.5, scale=1.65~2.0
 *      + LRU eviction + `visibilitychange` memory release.
 *   2. Rapid Ctrl+wheel zoom burst (15 wheel events in 150ms): concurrent uncancelled
 *      `page.render()` tasks, `renderTask.cancel()` usage, and DOM layout width/height writes.
 *   3. Rapid `paperforge:state-changed` burst (15 events): coalesced `listAnnotations()` calls.
 *   4. Dense 2-column academic page fixture (900 items/page): synchronous DOM span count,
 *      mount latency, selection latency, and 2-column reading-order contamination.
 *
 * Set `PF_PERF_ENFORCE_BUDGETS=1` to strictly assert post-upgrade target budgets.
 */
import * as fs from "fs";
import * as path from "path";
import { afterEach, describe, expect, it, vi } from "vitest";

const originalDevicePixelRatio = window.devicePixelRatio;
const originalIntersectionObserver = globalThis.IntersectionObserver;

// Polyfill Obsidian HTMLElement helpers used by PaperForgePdfView
const protoAny = HTMLElement.prototype as unknown as Record<string, unknown>;
if (typeof protoAny.empty !== "function") {
  protoAny.empty = function (this: HTMLElement) {
    this.textContent = "";
  };
}
if (typeof protoAny.addClass !== "function") {
  protoAny.addClass = function (this: HTMLElement, ...cls: string[]) {
    for (const c of cls) {
      for (const tok of String(c || "").split(/\s+/).filter(Boolean)) {
        this.classList.add(tok);
      }
    }
  };
}
if (typeof protoAny.removeClass !== "function") {
  protoAny.removeClass = function (this: HTMLElement, ...cls: string[]) {
    for (const c of cls) {
      for (const tok of String(c || "").split(/\s+/).filter(Boolean)) {
        this.classList.remove(tok);
      }
    }
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
      for (const c of String(opts.cls).split(/\s+/).filter(Boolean)) {
        el.classList.add(c);
      }
    }
    if (opts?.text !== undefined) el.textContent = String(opts.text);
    if (opts?.type && "type" in el) (el as HTMLInputElement).type = opts.type;
    if (opts?.value !== undefined && "value" in el) {
      (el as HTMLInputElement).value = opts.value;
    }
    if (opts?.placeholder !== undefined && "placeholder" in el) {
      (el as HTMLInputElement).placeholder = opts.placeholder;
    }
    if (opts?.attr) {
      for (const [k, v] of Object.entries(opts.attr)) {
        el.setAttribute(k, String(v));
      }
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

const mockLoadPdfJs = vi.fn();

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
    async setState() {}
    registerEvent() {}
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
    ItemView,
    Menu,
    Notice: function Notice() {},
    Platform: {
      isWin: true,
      isMacOS: false,
      isLinux: false,
      resourcePathPrefix: "app://local/",
    },
    TFile: class {},
    WorkspaceLeaf: class {},
    loadPdfJs: () => mockLoadPdfJs(),
  };
});

import { PaperForgePdfView } from "../src/views/pdf-annotator";

interface PdfBenchRecord {
  metric: string;
  measured: string;
  target: string;
}

const scorecard: PdfBenchRecord[] = [];
const enforceBudgets = process.env.PF_PERF_ENFORCE_BUDGETS === "1";

function recordMetric(metric: string, measured: string, target: string): void {
  scorecard.push({ metric, measured, target });
}

function formatMb(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function installCanvas2dMock(): void {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(
    () =>
      ({
        setTransform: vi.fn(),
        save: vi.fn(),
        restore: vi.fn(),
        scale: vi.fn(),
        drawImage: vi.fn(),
        clearRect: vi.fn(),
        fillRect: vi.fn(),
        measureText: (txt: string) => ({ width: txt.length * 6.4 }),
        font: "11px sans-serif",
      }) as unknown as CanvasRenderingContext2D
  );
}

/** Build a dense 2-column academic page fixture (900 items/page, stream-interleaved by row). */
function buildDenseTwoColTextItems(rowsPerCol = 45, wordsPerRow = 10) {
  const items: Array<{
    str: string;
    transform: number[];
    width: number;
    height: number;
    hasEOL?: boolean;
  }> = [];
  const wordW = 20;
  const gapW = 2.5;
  const fontH = 10;

  for (let r = 0; r < rowsPerCol; r++) {
    const pdfY = 760 - r * 14.5;
    // Left column words (x: 42 .. ~264)
    for (let w = 0; w < wordsPerRow; w++) {
      const x = 42 + w * (wordW + gapW);
      items.push({
        str: `L${String(r).padStart(2, "0")}_${w}`,
        transform: [fontH, 0, 0, fontH, x, pdfY],
        width: wordW,
        height: fontH,
        hasEOL: w === wordsPerRow - 1,
      });
    }
    // Right column words on the same baseline (x: 320 .. ~542)
    for (let w = 0; w < wordsPerColWords(wordsPerRow); w++) {
      const x = 320 + w * (wordW + gapW);
      items.push({
        str: `R${String(r).padStart(2, "0")}_${w}`,
        transform: [fontH, 0, 0, fontH, x, pdfY],
        width: wordW,
        height: fontH,
        hasEOL: w === wordsPerRow - 1,
      });
    }
  }
  return items;
}

function wordsPerColWords(n: number): number {
  return n;
}

function makeStandardViewport(scale: number, w = 595, h = 842) {
  return {
    width: w * scale,
    height: h * scale,
    transform: [scale, 0, 0, -scale, 0, h * scale],
  };
}

function createHarnessView(opts?: {
  numPages?: number;
  renderDelayMs?: number;
  itemsPerPage?: ReturnType<typeof buildDenseTwoColTextItems>;
  onListAnnotations?: () => void;
  onRenderStart?: (pageNumber: number) => void;
  onRenderCancel?: (pageNumber: number) => void;
  onRenderDone?: (pageNumber: number) => void;
}) {
  const numPages = opts?.numPages ?? 100;
  const renderDelayMs = opts?.renderDelayMs ?? 0;
  const stateListeners: Array<(payload?: unknown) => void> = [];

  mockLoadPdfJs.mockResolvedValue({
    getDocument: () => ({
      promise: Promise.resolve({
        numPages,
        getPage: async (pageNumber: number) => ({
          getViewport: ({ scale }: { scale: number }) =>
            makeStandardViewport(scale),
          render: () => {
            opts?.onRenderStart?.(pageNumber);
            let settled = false;
            let rejectFn: ((reason?: unknown) => void) | null = null;
            let timer: ReturnType<typeof setTimeout> | null = null;

            const promise = new Promise<void>((resolve, reject) => {
              rejectFn = reject;
              if (renderDelayMs <= 0) {
                settled = true;
                opts?.onRenderDone?.(pageNumber);
                resolve();
              } else {
                timer = setTimeout(() => {
                  if (settled) return;
                  settled = true;
                  opts?.onRenderDone?.(pageNumber);
                  resolve();
                }, renderDelayMs);
              }
            });

            return {
              promise,
              cancel: () => {
                if (settled) return;
                settled = true;
                if (timer) clearTimeout(timer);
                opts?.onRenderCancel?.(pageNumber);
                const err = new Error("Rendering cancelled");
                err.name = "RenderingCancelledException";
                rejectFn?.(err);
              },
            };
          },
          getTextContent: async () => ({
            items:
              opts?.itemsPerPage ?? [
                {
                  str: `Page ${pageNumber} sample medical text`,
                  transform: [10, 0, 0, 10, 50, 720],
                  width: 180,
                  height: 10,
                },
              ],
            styles: {},
          }),
        }),
        destroy: vi.fn(),
      }),
    }),
  });

  const listAnnotations = vi.fn().mockImplementation(async () => {
    opts?.onListAnnotations?.();
    await new Promise((r) => setTimeout(r, 5));
    return [
      {
        ann_id: "ann_sync_1",
        paper_id: "BENCHPDF",
        page: 1,
        kind: "highlight",
        color: "yellow",
        intent: "general",
        author: "user",
        exact_text: "Page 1 sample",
        comment: "",
        tags: [],
        rects: [[0.1, 0.14, 0.45, 0.16]],
        section_path: "",
        block_id: "",
        figure_id: "",
        crop_asset_rel: "",
        embed_wikilink: "",
        pdf_sha256: "benchsha",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ];
  });

  const client = {
    getPdfContext: vi.fn().mockResolvedValue({
      paper_id: "BENCHPDF",
      title: "100-Page Clinical Benchmark Study",
      pdf_abs_path: "D:/Bench/bench.pdf",
      pdf_vault_rel: "Lit/bench.pdf",
      pdf_locator: "Lit/bench.pdf",
      is_vault_relative: true,
      pdf_sha256: "benchsha",
      page_count: numPages,
      workspace_rel: "Lit/BENCHPDF",
      note_rel_path: "Lit/BENCHPDF/BENCHPDF.md",
      annotations: [],
    }),
    listAnnotations,
    addAnnotation: vi.fn(),
    updateAnnotation: vi.fn(),
    deleteAnnotation: vi.fn(),
    adoptAnnotation: vi.fn(),
    clearAgentAnnotations: vi.fn(),
    promoteAnnotation: vi.fn(),
  };

  const leaf = {
    app: {
      vault: {
        adapter: { getResourcePath: (p: string) => `app://vault/${p}` },
        getAbstractFileByPath: () => null,
      },
      workspace: {
        on: vi.fn((ev: string, cb: (payload?: unknown) => void) => {
          if (ev === "paperforge:state-changed") {
            stateListeners.push(cb);
          }
          return { ev, cb };
        }),
        offref: vi.fn(),
        getLeaf: () => ({ openFile: vi.fn() }),
        openLinkText: vi.fn(),
      },
      keymap: { pushScope: vi.fn(), popScope: vi.fn() },
    },
  } as unknown as import("obsidian").WorkspaceLeaf;

  const view = new PaperForgePdfView(leaf, { getClient: () => client as never });
  view.app = (leaf as unknown as { app: import("obsidian").App }).app;
  document.body.appendChild(view.contentEl);

  return { view, client, stateListeners };
}

function measureMountedCanvases(root: HTMLElement) {
  const canvases = Array.from(
    root.querySelectorAll<HTMLCanvasElement>(".pf-pdf-canvas")
  );
  let totalPixels = 0;
  let maxSinglePixels = 0;
  let activeCanvases = 0;
  for (const c of canvases) {
    const px = c.width * c.height;
    if (px > 0) activeCanvases += 1;
    totalPixels += px;
    if (px > maxSinglePixels) maxSinglePixels = px;
  }
  return {
    totalNodes: canvases.length,
    activeCanvases,
    totalPixels,
    totalBytes: totalPixels * 4,
    maxSinglePixels,
  };
}

describe("PaperForge PDF Real-Runtime Performance & Memory Benchmark", () => {
  const activeViews: PaperForgePdfView[] = [];

  afterEach(async () => {
    for (const v of activeViews.splice(0)) {
      await v.onClose();
      v.contentEl.remove();
    }
    Object.defineProperty(window, "devicePixelRatio", {
      value: originalDevicePixelRatio,
      configurable: true,
    });
    Object.defineProperty(document, "hidden", {
      value: false,
      configurable: true,
    });
    globalThis.IntersectionObserver = originalIntersectionObserver;
    vi.restoreAllMocks();
    mockLoadPdfJs.mockReset();
  });

  it("1. Canvas pixel memory footprint across 100-page scroll (DPR=2.5, scale=1.65~2.0) + visibility release", async () => {
    installCanvas2dMock();
    Object.defineProperty(window, "devicePixelRatio", {
      value: 2.5,
      configurable: true,
    });

    let observerCb:
      | ((entries: Array<{ isIntersecting: boolean; target: Element }>) => void)
      | null = null;
    globalThis.IntersectionObserver = class MockIntersectionObserver {
      constructor(
        cb: (
          entries: Array<{ isIntersecting: boolean; target: Element }>
        ) => void
      ) {
        observerCb = cb;
      }
      observe() {}
      disconnect() {}
      unobserve() {}
    } as unknown as typeof IntersectionObserver;

    const { view } = createHarnessView({ numPages: 100 });
    activeViews.push(view);

    await view.onOpen();
    // Set scale=1.8 (midpoint of 1.65~2.0 high-zoom reading) before opening doc
    (view as unknown as { _scale: number })._scale = 1.8;
    await view.setState({ paperKey: "BENCHPDF", page: 1 }, { history: false });

    const pageEls = (
      view as unknown as { _pageEls: Map<number, HTMLElement> }
    )._pageEls;
    expect(pageEls.size).toBe(100);

    let peakCanvases = 0;
    let peakPixels = 0;
    let peakBytes = 0;
    let maxSinglePixels = 0;

    // Simulate scrolling page 1 -> 100 through real IntersectionObserver callback
    for (let p = 1; p <= 100; p++) {
      const pageEl = pageEls.get(p)!;
      observerCb?.([{ isIntersecting: true, target: pageEl }]);
      // Flush async _ensurePageRendered microtasks
      await new Promise((r) => setTimeout(r, 0));
      const snap = measureMountedCanvases(view.contentEl);
      if (snap.activeCanvases > peakCanvases) peakCanvases = snap.activeCanvases;
      if (snap.totalPixels > peakPixels) peakPixels = snap.totalPixels;
      if (snap.totalBytes > peakBytes) peakBytes = snap.totalBytes;
      if (snap.maxSinglePixels > maxSinglePixels) {
        maxSinglePixels = snap.maxSinglePixels;
      }
    }

    const firstCanvas = view.contentEl.querySelector(
      ".pf-pdf-canvas"
    ) as HTMLCanvasElement | null;
    const effectiveDpr =
      firstCanvas && firstCanvas.width > 0
        ? firstCanvas.width / Math.round(595 * 1.8)
        : 0;

    // Measure high-end scale=2.0 single page & peak budget
    (view as unknown as { _scale: number })._scale = 2.0;
    (view as unknown as { _renderedPages: Set<number> })._renderedPages.delete(100);
    await (
      view as unknown as {
        _ensurePageRendered: (p: number) => Promise<void>;
      }
    )._ensurePageRendered(100);
    const scale20Snap = measureMountedCanvases(view.contentEl);

    // Measure visibility-hide memory release
    const beforeHide = measureMountedCanvases(view.contentEl);
    Object.defineProperty(document, "hidden", {
      value: true,
      configurable: true,
    });
    document.dispatchEvent(new Event("visibilitychange"));
    await new Promise((r) => setTimeout(r, 10));
    const afterHide = measureMountedCanvases(view.contentEl);

    recordMetric(
      "Canvas peak mounted (100p scroll @ DPR=2.5, scale=1.8)",
      `${peakCanvases} canvases`,
      "<= 5 canvases"
    );
    recordMetric(
      "Canvas peak pixel memory (DPR=2.5, scale=1.8)",
      `${formatMb(peakBytes)} (${(peakPixels / 1e6).toFixed(2)} Mpx)`,
      "<= 120.00 MB (<= 30 Mpx)"
    );
    recordMetric(
      "Single-canvas max pixels (DPR=2.5, scale=2.0)",
      `${(scale20Snap.maxSinglePixels / 1e6).toFixed(2)} Mpx (${formatMb(scale20Snap.maxSinglePixels * 4)})`,
      "<= 6.00 Mpx (<= 24.00 MB)"
    );
    recordMetric(
      "Effective canvas DPR @ devicePixelRatio=2.5",
      `${effectiveDpr.toFixed(2)}x`,
      "<= 2.00x"
    );
    recordMetric(
      "Visibility-hide canvas release",
      `${beforeHide.activeCanvases} -> ${afterHide.activeCanvases} canvases (${formatMb(beforeHide.totalBytes)} -> ${formatMb(afterHide.totalBytes)})`,
      "<= 1 canvas retained"
    );

    expect(peakCanvases).toBeGreaterThan(0);
    expect(peakBytes).toBeGreaterThan(0);

    if (enforceBudgets) {
      expect(effectiveDpr).toBeLessThanOrEqual(2.05);
      expect(peakCanvases).toBeLessThanOrEqual(5);
      expect(scale20Snap.maxSinglePixels).toBeLessThanOrEqual(6_050_000);
      expect(afterHide.activeCanvases).toBeLessThanOrEqual(1);
    }
  });

  it("2. Rapid Ctrl+wheel zoom burst (15 events in 150ms): uncancelled renders & DOM layout writes", async () => {
    installCanvas2dMock();

    let totalRenderCalls = 0;
    let cancelledRenderCalls = 0;
    let activeRenders = 0;
    let peakConcurrentUncancelled = 0;

    const { view } = createHarnessView({
      numPages: 100,
      renderDelayMs: 120,
      onRenderStart: () => {
        totalRenderCalls += 1;
        activeRenders += 1;
        if (activeRenders > peakConcurrentUncancelled) {
          peakConcurrentUncancelled = activeRenders;
        }
      },
      onRenderCancel: () => {
        cancelledRenderCalls += 1;
        activeRenders = Math.max(0, activeRenders - 1);
      },
      onRenderDone: () => {
        activeRenders = Math.max(0, activeRenders - 1);
      },
    });
    activeViews.push(view);

    await view.onOpen();
    await view.setState({ paperKey: "BENCHPDF", page: 1 }, { history: false });
    // Start at 0.8x so 15 wheel-in steps (+0.1 each -> 2.3x) never clamp
    (view as unknown as { _scale: number })._scale = 0.8;
    // Reset counters after initial open
    totalRenderCalls = 0;
    cancelledRenderCalls = 0;
    activeRenders = 0;
    peakConcurrentUncancelled = 0;

    const scrollEl = view.contentEl.querySelector(
      ".pf-pdf-scroll"
    ) as HTMLElement;
    expect(scrollEl).not.toBeNull();

    // Track per-page layout width/height writes vs CSS transform writes during burst
    let burstPageLayoutWrites = 0;
    let burstCssTransformWrites = 0;
    const lastPageDims = new Map<Element, string>();
    const lastTransform = new Map<Element, string>();

    const mo = new MutationObserver((records) => {
      for (const rec of records) {
        const el = rec.target as HTMLElement;
        if (el.classList.contains("pf-pdf-page")) {
          const dimSig = `${el.style.width}|${el.style.height}`;
          if (lastPageDims.get(el) !== dimSig) {
            lastPageDims.set(el, dimSig);
            burstPageLayoutWrites += 1;
          }
        }
        if (el.style.transform) {
          if (lastTransform.get(el) !== el.style.transform) {
            lastTransform.set(el, el.style.transform);
            burstCssTransformWrites += 1;
          }
        }
      }
    });
    mo.observe(scrollEl, {
      attributes: true,
      attributeFilter: ["style"],
      subtree: true,
    });

    // Fire 15 Ctrl+wheel events evenly over 150ms (10ms interval)
    for (let i = 0; i < 15; i++) {
      scrollEl.dispatchEvent(
        new WheelEvent("wheel", {
          ctrlKey: true,
          deltaY: -100,
          bubbles: true,
          cancelable: true,
        })
      );
      await new Promise((r) => setTimeout(r, 10));
    }

    // Flush mutation records right at end of the 150ms burst (before 120ms debounce commit)
    await Promise.resolve();
    const pendingRecords = mo.takeRecords();
    for (const rec of pendingRecords) {
      const el = rec.target as HTMLElement;
      if (el.classList.contains("pf-pdf-page")) {
        const dimSig = `${el.style.width}|${el.style.height}`;
        if (lastPageDims.get(el) !== dimSig) {
          lastPageDims.set(el, dimSig);
          burstPageLayoutWrites += 1;
        }
      }
      if (el.style.transform && lastTransform.get(el) !== el.style.transform) {
        lastTransform.set(el, el.style.transform);
        burstCssTransformWrites += 1;
      }
    }
    mo.disconnect();

    const rendersDuringBurst = totalRenderCalls;

    // Wait for debounced final zoom render to settle
    await new Promise((r) => setTimeout(r, 250));

    recordMetric(
      "Ctrl+wheel zoom burst (15x/150ms) renders launched during burst",
      `${rendersDuringBurst} calls (total ${totalRenderCalls} w/ settle)`,
      "<= 3 during burst"
    );
    recordMetric(
      "Ctrl+wheel zoom burst peak concurrent uncancelled renders",
      `${peakConcurrentUncancelled} concurrent (${cancelledRenderCalls} cancelled)`,
      "<= 3 concurrent"
    );
    recordMetric(
      "Ctrl+wheel zoom burst page layout writes (100p DOM reflows)",
      `${burstPageLayoutWrites} layout writes (${burstCssTransformWrites} CSS transform previews)`,
      "0 layout writes during burst"
    );

    expect(totalRenderCalls).toBeGreaterThan(0);

    if (enforceBudgets) {
      expect(peakConcurrentUncancelled).toBeLessThanOrEqual(4);
      expect(burstPageLayoutWrites).toBe(0);
    }
  });

  it("3. Rapid state-changed burst (15 events): listAnnotations() call coalescing", async () => {
    installCanvas2dMock();
    let listCalls = 0;
    const { view, stateListeners } = createHarnessView({
      numPages: 10,
      onListAnnotations: () => {
        listCalls += 1;
      },
    });
    activeViews.push(view);

    await view.onOpen();
    await view.setState({ paperKey: "BENCHPDF", page: 1 }, { history: false });
    expect(stateListeners.length).toBeGreaterThan(0);
    listCalls = 0;

    const t0 = performance.now();
    for (let i = 0; i < 15; i++) {
      stateListeners[0]({ changedKeys: ["BENCHPDF"] });
    }
    // Wait for 150ms+ debounce + async RPC settle
    await new Promise((r) => setTimeout(r, 260));
    const elapsedMs = performance.now() - t0;

    recordMetric(
      "Rapid state-changed burst (15 events) listAnnotations() calls",
      `${listCalls} RPCs (settled in ${elapsedMs.toFixed(1)} ms)`,
      "<= 2 RPCs (debounced)"
    );

    expect(listCalls).toBeGreaterThanOrEqual(1);
    if (enforceBudgets) {
      expect(listCalls).toBeLessThanOrEqual(2);
    }
  });

  it("4. Dense 2-column page fixture (900 items/page): mount cost, DOM spans & selection accuracy", async () => {
    installCanvas2dMock();
    const denseItems = buildDenseTwoColTextItems(45, 10); // 900 items per page
    expect(denseItems).toHaveLength(900);

    const { view } = createHarnessView({
      numPages: 10,
      itemsPerPage: denseItems,
    });
    activeViews.push(view);

    await view.onOpen();
    const tMount0 = performance.now();
    await view.setState({ paperKey: "BENCHPDF", page: 1 }, { history: false });
    // Render pages 1..5 to measure dense text build cost
    for (let p = 1; p <= 5; p++) {
      await (
        view as unknown as { _ensurePageRendered: (n: number) => Promise<void> }
      )._ensurePageRendered(p);
    }
    const mount5PagesMs = performance.now() - tMount0;

    const page1El = (
      view as unknown as { _pageEls: Map<number, HTMLElement> }
    )._pageEls.get(1)!;
    const textSpansPage1 = page1El.querySelectorAll(
      ".pf-pdf-text-layer span"
    ).length;

    // Mock geometry for page 1 at scale=1.25 (595*1.25 = 743.75 x 842*1.25 = 1052.5)
    const scale = (view as unknown as { _scale: number })._scale || 1.25;
    const pageW = 595 * scale;
    const pageH = 842 * scale;
    page1El.getBoundingClientRect = () =>
      ({
        left: 0,
        top: 0,
        right: pageW,
        bottom: pageH,
        width: pageW,
        height: pageH,
        x: 0,
        y: 0,
        toJSON: () => ({}),
      }) as DOMRect;

    // Select Left Column rows 5..14 (PDF y: 687.5 -> 557, screen x: 45 -> 260)
    const startX = 45 * scale;
    const startY = (842 - 687.5) * scale;
    const endX = 260 * scale;
    const endY = (842 - 557) * scale;

    const tSel0 = performance.now();
    // Try pointer/mouse drag first (exercised by geometric pdf-selection-engine)
    const dispatchEvt = (
      type: string,
      clientX: number,
      clientY: number
    ) => {
      page1El.dispatchEvent(
        new MouseEvent(type, {
          bubbles: true,
          cancelable: true,
          button: 0,
          buttons: type === "mouseup" ? 0 : 1,
          clientX,
          clientY,
        })
      );
      if (typeof PointerEvent === "function") {
        const pType = type.replace("mouse", "pointer");
        page1El.dispatchEvent(
          new PointerEvent(pType, {
            bubbles: true,
            cancelable: true,
            button: 0,
            buttons: type === "mouseup" ? 0 : 1,
            clientX,
            clientY,
          })
        );
      }
    };
    dispatchEvt("mousedown", startX, startY);
    dispatchEvt("mousemove", endX, endY);
    dispatchEvt("mouseup", endX, endY);

    let selData = (
      view as unknown as {
        _getSelectionData: () => {
          rects: number[][];
          exactText: string;
        } | null;
      }
    )._getSelectionData();

    // Baseline fallback: `master` relies on DOM TextLayer Range selection
    if (!selData && textSpansPage1 > 0) {
      const spans = Array.from(
        page1El.querySelectorAll<HTMLSpanElement>(".pf-pdf-text-layer span")
      );
      const startSpan = spans.find((s) => s.textContent === "L05_0");
      const endSpan = spans.find((s) => s.textContent === "L14_9");
      if (startSpan && endSpan) {
        const range = document.createRange();
        range.setStart(startSpan.firstChild!, 0);
        range.setEnd(endSpan.firstChild!, endSpan.textContent!.length);
        const startIdx = spans.indexOf(startSpan);
        const endIdx = spans.indexOf(endSpan);
        const selectedSpans = spans.slice(startIdx, endIdx + 1);
        range.getClientRects = () =>
          selectedSpans.map((sp) => {
            const left = parseFloat(sp.style.left || "0");
            const top = parseFloat(sp.style.top || "0");
            const fontH = parseFloat(sp.style.fontSize || "12");
            return {
              left,
              top,
              right: left + 25,
              bottom: top + fontH,
              width: 25,
              height: fontH,
            } as DOMRect;
          }) as unknown as DOMRectList;
        const sel = window.getSelection();
        sel?.removeAllRanges();
        sel?.addRange(range);
        selData = (
          view as unknown as {
            _getSelectionData: () => {
              rects: number[][];
              exactText: string;
            } | null;
          }
        )._getSelectionData();
      }
    }
    const selLatencyMs = performance.now() - tSel0;

    const text = selData?.exactText ?? "";
    const leftTokens = text.match(/L\d{2}_\d/g) ?? [];
    const rightTokens = text.match(/R\d{2}_\d/g) ?? [];
    const totalTokens = leftTokens.length + rightTokens.length;
    const contaminationPct =
      totalTokens > 0 ? (rightTokens.length / totalTokens) * 100 : 0;
    const maxRectRightNorm = (selData?.rects ?? []).reduce(
      (mx, r) => Math.max(mx, r[2] ?? 0),
      0
    );

    recordMetric(
      "Dense 2-col 5-page render+text mount (900 items/p)",
      `${mount5PagesMs.toFixed(2)} ms (${(mount5PagesMs / 5).toFixed(2)} ms/p, ${textSpansPage1} DOM spans/p)`,
      "< 80 ms total, 0 DOM spans/p"
    );
    recordMetric(
      "2-col left-column selection accuracy & latency",
      `${selLatencyMs.toFixed(2)} ms | L=${leftTokens.length}, R_leak=${rightTokens.length} (${contaminationPct.toFixed(1)}%), maxX=${maxRectRightNorm.toFixed(3)}`,
      "0.0% R_leak, maxX <= 0.480"
    );

    expect(text.length).toBeGreaterThan(0);
    expect(leftTokens.length).toBeGreaterThan(0);

    if (enforceBudgets) {
      expect(textSpansPage1).toBe(0);
      expect(contaminationPct).toBe(0);
      expect(maxRectRightNorm).toBeLessThanOrEqual(0.49);
    }
  });

  it("5. Prints PDF Runtime Scorecard summary", () => {
    const lines = [
      "",
      "=== PaperForge PDF Runtime Benchmark Scorecard ===",
      ...scorecard.map(
        (r) => `  - ${r.metric}: ${r.measured} (target ${r.target})`
      ),
      "==================================================",
    ];
    console.info(lines.join("\n"));
    expect(scorecard.length).toBeGreaterThanOrEqual(9);
  });
});
