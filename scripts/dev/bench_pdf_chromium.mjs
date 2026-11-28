#!/usr/bin/env node
/**
 * Real-Chromium PDF Reader Stress Benchmark (`scripts/dev/bench_pdf_chromium.mjs`).
 *
 * Bundles the live `paperforge/plugin/src/views/pdf-annotator.ts` + `styles.css`
 * with an Obsidian browser shim and drives a 50-100 page simulated PDF stress test
 * inside real headless Chromium / Chrome / Edge via `playwright-core`:
 *   - Real JS Heap (`performance.memory` + CDP `JSHeapUsedSize`)
 *   - Real DOM Node count, `LayoutCount`, `LayoutDuration`, `RecalcStyleCount`
 *   - Real `requestAnimationFrame` frame times (P50 / P95 / P99 / max, >16.7ms, >50ms)
 *   - Real Long Tasks (`PerformanceObserver` entryTypes: ["longtask"])
 *   - Mounted canvas RGBA pixel footprint + `visibilitychange` memory release
 *
 * Requirements:
 *   - `esbuild` (installed in `paperforge/plugin/node_modules`)
 *   - `playwright-core` (local or global `node_modules`)
 *   - Chrome / Edge / Playwright Chromium (`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` optional)
 *
 * Usage:
 *   node scripts/dev/bench_pdf_chromium.mjs [--pages=80] [--dpr=2.5] [--scale=1.8] [--json] [--allow-missing]
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..");
const PLUGIN_DIR = path.join(REPO_ROOT, "paperforge", "plugin");
const PDF_VIEW_TS = path.join(PLUGIN_DIR, "src", "views", "pdf-annotator.ts");
const STYLES_CSS = path.join(PLUGIN_DIR, "styles.css");

function parseArgs(argv) {
  const opts = {
    pages: 80,
    dpr: 2.5,
    scale: 1.8,
    json: false,
    allowMissing: false,
  };
  for (const a of argv) {
    if (a.startsWith("--pages=")) opts.pages = Math.max(10, Math.min(200, Number(a.slice(8)) || 80));
    else if (a.startsWith("--dpr=")) opts.dpr = Math.max(1, Math.min(4, Number(a.slice(6)) || 2.5));
    else if (a.startsWith("--scale=")) opts.scale = Math.max(0.6, Math.min(3, Number(a.slice(8)) || 1.8));
    else if (a === "--json") opts.json = true;
    else if (a === "--allow-missing") opts.allowMissing = true;
  }
  return opts;
}

function tryResolveModule(name) {
  const require = createRequire(import.meta.url);
  const candidateRoots = [
    PLUGIN_DIR,
    REPO_ROOT,
    path.join(os.homedir(), "node_modules"),
    path.join(os.homedir(), "AppData", "Roaming", "npm", "node_modules"),
    process.env.NODE_PATH || "",
  ].filter(Boolean);
  for (const root of candidateRoots) {
    try {
      return require(require.resolve(name, { paths: [root] }));
    } catch {
      // try next search root
    }
  }
  try {
    return require(name);
  } catch {
    return null;
  }
}

function findBrowserExecutable() {
  const envPath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;
  if (envPath && fs.existsSync(envPath)) return envPath;

  const candidates =
    process.platform === "win32"
      ? [
          path.join(process.env.PROGRAMFILES || "C:\\Program Files", "Google", "Chrome", "Application", "chrome.exe"),
          path.join(process.env["PROGRAMFILES(X86)"] || "C:\\Program Files (x86)", "Google", "Chrome", "Application", "chrome.exe"),
          path.join(process.env["PROGRAMFILES(X86)"] || "C:\\Program Files (x86)", "Microsoft", "Edge", "Application", "msedge.exe"),
          path.join(process.env.PROGRAMFILES || "C:\\Program Files", "Microsoft", "Edge", "Application", "msedge.exe"),
        ]
      : process.platform === "darwin"
        ? [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
          ]
        : [
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/usr/bin/microsoft-edge",
          ];

  for (const p of candidates) {
    if (p && fs.existsSync(p)) return p;
  }
  return null;
}

async function bundlePdfHarness(buildDir, opts) {
  const esbuild = tryResolveModule("esbuild");
  if (!esbuild) {
    throw new Error(
      "Missing `esbuild`. Run `npm ci` inside `paperforge/plugin` before running this benchmark."
    );
  }

  const shimPath = path.join(buildDir, "obsidian_shim.ts");
  fs.writeFileSync(
    shimPath,
    `
const proto = HTMLElement.prototype as unknown as Record<string, unknown>;
if (typeof proto.empty !== "function") {
  proto.empty = function (this: HTMLElement) { this.textContent = ""; };
}
if (typeof proto.addClass !== "function") {
  proto.addClass = function (this: HTMLElement, ...cls: string[]) {
    for (const c of cls) for (const t of String(c || "").split(/\\s+/).filter(Boolean)) this.classList.add(t);
  };
}
if (typeof proto.removeClass !== "function") {
  proto.removeClass = function (this: HTMLElement, ...cls: string[]) {
    for (const c of cls) for (const t of String(c || "").split(/\\s+/).filter(Boolean)) this.classList.remove(t);
  };
}
if (typeof proto.toggleClass !== "function") {
  proto.toggleClass = function (this: HTMLElement, cls: string, force?: boolean) { this.classList.toggle(cls, force); };
}
if (typeof proto.setText !== "function") {
  proto.setText = function (this: HTMLElement, text: string) { this.textContent = text; };
}
if (typeof proto.createEl !== "function") {
  proto.createEl = function (this: HTMLElement, tag: string, opts?: any, cb?: (el: HTMLElement) => void) {
    const el = this.ownerDocument.createElement(tag);
    if (opts?.cls) for (const c of String(opts.cls).split(/\\s+/).filter(Boolean)) el.classList.add(c);
    if (opts?.text !== undefined) el.textContent = String(opts.text);
    if (opts?.type && "type" in el) (el as HTMLInputElement).type = opts.type;
    if (opts?.value !== undefined && "value" in el) (el as HTMLInputElement).value = opts.value;
    if (opts?.placeholder !== undefined && "placeholder" in el) (el as HTMLInputElement).placeholder = opts.placeholder;
    if (opts?.attr) for (const [k, v] of Object.entries(opts.attr)) if (v != null) el.setAttribute(k, String(v));
    this.appendChild(el);
    cb?.(el);
    return el;
  };
}
if (typeof proto.createDiv !== "function") {
  proto.createDiv = function (this: HTMLElement, opts?: any, cb?: any) { return (this as any).createEl("div", opts, cb); };
}
if (typeof proto.createSpan !== "function") {
  proto.createSpan = function (this: HTMLElement, opts?: any, cb?: any) { return (this as any).createEl("span", opts, cb); };
}

export class App {}
export class TFile {}
export class WorkspaceLeaf {}
export class Notice { constructor(_msg?: string) {} }
export class Menu {
  addItem() { return this; }
  addSeparator() { return this; }
  showAtMouseEvent() {}
}
export class ItemView {
  app: any;
  leaf: any;
  contentEl = document.createElement("div");
  containerEl = document.createElement("div");
  constructor(leaf: any) {
    this.leaf = leaf;
    this.app = leaf?.app ?? {};
    this.containerEl.appendChild(this.contentEl);
  }
  async setState() {}
  registerEvent() {}
}
export const Platform = { isWin: true, isMacOS: false, isLinux: false, resourcePathPrefix: "app://local/" };

function buildTwoColItems() {
  const items: any[] = [];
  for (let r = 0; r < 30; r++) {
    const y = 760 - r * 20;
    for (let w = 0; w < 10; w++) {
      items.push({ str: \`L\${r}_\${w}\`, transform: [10, 0, 0, 10, 42 + w * 22, y], width: 19, height: 10, hasEOL: w === 9 });
    }
    for (let w = 0; w < 10; w++) {
      items.push({ str: \`R\${r}_\${w}\`, transform: [10, 0, 0, 10, 320 + w * 22, y], width: 19, height: 10, hasEOL: w === 9 });
    }
  }
  return items;
}

const SHARED_ITEMS = buildTwoColItems();

export async function loadPdfJs() {
  const cfg = (window as any).__PF_BENCH_CFG__;
  const totalPages = cfg.pages;
  return {
    getDocument: () => ({
      promise: Promise.resolve({
        numPages: totalPages,
        getPage: async (pageNumber: number) => ({
          getViewport: ({ scale }: { scale: number }) => ({
            width: 595 * scale,
            height: 842 * scale,
            transform: [scale, 0, 0, -scale, 0, 842 * scale],
          }),
          render: ({ canvasContext, viewport }: { canvasContext: CanvasRenderingContext2D; viewport: { width: number; height: number } }) => {
            cfg.renderStats.started += 1;
            let done = false;
            let timer: any = null;
            let rej: any = null;
            const promise = new Promise<void>((resolve, reject) => {
              rej = reject;
              timer = setTimeout(() => {
                if (done) return;
                done = true;
                const s = viewport.width / 595;
                canvasContext.save();
                canvasContext.scale(s, s);
                canvasContext.fillStyle = "#ffffff";
                canvasContext.fillRect(0, 0, 595, 842);
                canvasContext.fillStyle = "#0f172a";
                canvasContext.font = "11px sans-serif";
                canvasContext.fillText(\`Benchmark Page \${pageNumber}\`, 42, 48);
                canvasContext.fillStyle = "#e2e8f0";
                canvasContext.fillRect(320, 120, 230, 140);
                canvasContext.restore();
                cfg.renderStats.completed += 1;
                resolve();
              }, 12);
            });
            return {
              promise,
              cancel: () => {
                if (done) return;
                done = true;
                clearTimeout(timer);
                cfg.renderStats.cancelled += 1;
                const err = new Error("Rendering cancelled");
                err.name = "RenderingCancelledException";
                rej?.(err);
              },
            };
          },
          getTextContent: async () => ({ items: SHARED_ITEMS, styles: {} }),
        }),
        destroy: async () => {},
      }),
    }),
  };
}
`,
    "utf-8"
  );

  const entryPath = path.join(buildDir, "bench_entry.ts");
  fs.writeFileSync(
    entryPath,
    `
import { PaperForgePdfView } from ${JSON.stringify(PDF_VIEW_TS)};

function buildAnnotations(totalPages: number) {
  const out: any[] = [];
  for (let p = 1; p <= totalPages; p++) {
    out.push({
      ann_id: \`hl_\${p}\`,
      paper_id: "BENCH",
      page: p,
      kind: "highlight",
      color: "yellow",
      intent: "general",
      author: "user",
      exact_text: \`Key finding on page \${p}\`,
      comment: "",
      tags: [],
      rects: [[0.08, 0.22, 0.45, 0.25]],
      section_path: "Results",
      block_id: "",
      figure_id: "",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "sha",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    out.push({
      ann_id: \`ai_\${p}\`,
      paper_id: "BENCH",
      page: p,
      kind: "margin",
      color: "purple",
      intent: "general",
      author: "agent",
      lens: "methods",
      grounding_tier: "exact_span",
      exact_text: \`Method sample on page \${p}\`,
      comment: "Check cohort power",
      tags: [],
      rects: [[0.54, 0.40, 0.91, 0.44]],
      section_path: "Methods",
      block_id: "",
      figure_id: "",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "sha",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    out.push({
      ann_id: \`sh_\${p}\`,
      paper_id: "BENCH",
      page: p,
      kind: "shape",
      color: "red",
      intent: "general",
      author: "user",
      exact_text: "",
      comment: "",
      tags: [],
      rects: [[0.55, 0.16, 0.85, 0.30]],
      style: { shape_type: "arrow", stroke_color: "#d64545", stroke_width: 2, points: [[0.55, 0.16], [0.85, 0.30]] },
      section_path: "",
      block_id: "",
      figure_id: "",
      crop_asset_rel: "",
      embed_wikilink: "",
      pdf_sha256: "sha",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
  }
  return out;
}

(window as any).__mountPdfBench = async function (pages: number, scale: number) {
  const stateListeners: Array<(payload?: unknown) => void> = [];
  const anns = buildAnnotations(pages);
  const stats = (window as any).__PF_BENCH_CFG__.renderStats;
  const client = {
    getPdfContext: async () => ({
      paper_id: "BENCH",
      title: \`\${pages}-Page Chromium Stress PDF\`,
      pdf_abs_path: "D:/Bench/stress.pdf",
      pdf_vault_rel: "Lit/stress.pdf",
      pdf_locator: "Lit/stress.pdf",
      is_vault_relative: true,
      pdf_sha256: "sha",
      page_count: pages,
      workspace_rel: "Lit/BENCH",
      note_rel_path: "Lit/BENCH/BENCH.md",
      annotations: anns,
    }),
    listAnnotations: async () => {
      stats.listAnnotationsCalls += 1;
      return anns;
    },
    addAnnotation: async () => anns[0],
    updateAnnotation: async () => anns[0],
    deleteAnnotation: async () => ({ deleted: true }),
    adoptAnnotation: async () => anns[0],
    clearAgentAnnotations: async () => ({ deleted_count: 0 }),
    promoteAnnotation: async () => ({ promoted: true }),
  };

  const leaf: any = {
    app: {
      vault: {
        adapter: { getResourcePath: (p: string) => p },
        getAbstractFileByPath: () => null,
      },
      workspace: {
        on: (ev: string, cb: (payload?: unknown) => void) => {
          if (ev === "paperforge:state-changed") stateListeners.push(cb);
          return { ev, cb };
        },
        offref: () => {},
        getLeaf: () => ({ openFile: async () => {} }),
        openLinkText: async () => {},
      },
      keymap: { pushScope: () => {}, popScope: () => {} },
    },
  };

  const view = new PaperForgePdfView(leaf, { getClient: () => client as any }) as any;
  view.app = leaf.app;
  view._scale = scale;
  const root = document.getElementById("bench-root")!;
  root.appendChild(view.contentEl);
  await view.onOpen();
  await view.setState({ paperKey: "BENCH", page: 1 }, { history: false });
  (window as any).__PF_VIEW__ = view;
  (window as any).__PF_STATE_LISTENERS__ = stateListeners;
  return { mountedPages: view.contentEl.querySelectorAll(".pf-pdf-page").length };
};
`,
    "utf-8"
  );

  const bundleJs = path.join(buildDir, "bench_bundle.js");
  await esbuild.build({
    entryPoints: [entryPath],
    bundle: true,
    platform: "browser",
    target: ["chrome120"],
    outfile: bundleJs,
    plugins: [
      {
        name: "pf-obsidian-shim",
        setup(build) {
          build.onResolve({ filter: /^obsidian$/ }, () => ({ path: shimPath }));
        },
      },
    ],
    define: {
      "process.env.NODE_ENV": '"production"',
    },
  });

  const htmlPath = path.join(buildDir, "index.html");
  fs.writeFileSync(
    htmlPath,
    `<!doctype html>
<html class="theme-light">
<head>
  <meta charset="utf-8" />
  <title>PaperForge Chromium PDF Benchmark</title>
  <link rel="stylesheet" href="${pathToFileURL(STYLES_CSS).href}" />
  <style>
    html, body, #bench-root { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; background: #fff; font-family: Inter, system-ui, sans-serif; }
    .pf-pdf-view { width: 100%; height: 100%; display: flex; flex-direction: column; }
  </style>
</head>
<body>
  <div id="bench-root"></div>
  <script>
    window.__PF_BENCH_CFG__ = {
      pages: ${opts.pages},
      renderStats: { started: 0, completed: 0, cancelled: 0, listAnnotationsCalls: 0 },
    };
  </script>
  <script src="${pathToFileURL(bundleJs).href}"></script>
</body>
</html>`,
    "utf-8"
  );
  return htmlPath;
}

function percentile(sorted, p) {
  if (!sorted.length) return 0;
  const idx = Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * p));
  return sorted[idx];
}

function cdpMetricMap(metrics) {
  const out = {};
  for (const m of metrics) out[m.name] = m.value;
  return out;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const playwrightCore = tryResolveModule("playwright-core");
  if (!playwrightCore) {
    const msg =
      "playwright-core not found. Install playwright-core or set NODE_PATH to run Chromium benchmark.";
    if (opts.allowMissing) {
      console.warn("[bench_pdf_chromium] SKIPPED:", msg);
      process.exit(0);
    }
    console.error("[bench_pdf_chromium] BLOCKED:", msg);
    process.exit(2);
  }

  const exe = findBrowserExecutable();
  const buildDir = fs.mkdtempSync(path.join(os.tmpdir(), "pf-pdf-chrome-"));
  let browser;
  try {
    const htmlPath = await bundlePdfHarness(buildDir, opts);
    const launchOpts = {
      headless: true,
      args: ["--enable-precise-memory-info", "--disable-dev-shm-usage"],
      ...(exe ? { executablePath: exe } : {}),
    };
    browser = await playwrightCore.chromium.launch(launchOpts);
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      deviceScaleFactor: opts.dpr,
    });
    const page = await context.newPage();
    const cdp = await context.newCDPSession(page);
    await cdp.send("Performance.enable");

    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => {
      (window).__longTasks = [];
      try {
        const obs = new PerformanceObserver((list) => {
          for (const e of list.getEntries()) {
            (window).__longTasks.push(e.duration);
          }
        });
        obs.observe({ entryTypes: ["longtask"] });
      } catch {
        // LongTask observer unavailable
      }
    });

    const tOpen0 = Date.now();
    await page.evaluate(
      ({ pages, scale }) => (window).__mountPdfBench(pages, scale),
      { pages: opts.pages, scale: opts.scale }
    );
    const openMs = Date.now() - tOpen0;

    const cdpAfterMount = cdpMetricMap((await cdp.send("Performance.getMetrics")).metrics);

    // Phase 2: Real scroll across all pages while measuring rAF frame times & peak canvas bytes
    const scrollResult = await page.evaluate(async () => {
      const scrollEl = document.querySelector(".pf-pdf-scroll");
      const frameTimes = [];
      let peakCanvasBytes = 0;
      let peakCanvasCount = 0;
      let peakHeapBytes = 0;
      const totalScroll = Math.max(1000, scrollEl.scrollHeight - scrollEl.clientHeight);
      const steps = 90;
      let lastTs = performance.now();

      for (let i = 1; i <= steps; i++) {
        await new Promise((resolve) =>
          requestAnimationFrame((ts) => {
            frameTimes.push(ts - lastTs);
            lastTs = ts;
            resolve();
          })
        );
        scrollEl.scrollTop = Math.round((totalScroll * i) / steps);
        const canvases = document.querySelectorAll(".pf-pdf-canvas");
        let bytes = 0;
        let active = 0;
        canvases.forEach((c) => {
          const px = c.width * c.height;
          if (px > 0) active += 1;
          bytes += px * 4;
        });
        if (bytes > peakCanvasBytes) peakCanvasBytes = bytes;
        if (active > peakCanvasCount) peakCanvasCount = active;
        if (performance.memory?.usedJSHeapSize > peakHeapBytes) {
          peakHeapBytes = performance.memory.usedJSHeapSize;
        }
      }
      await new Promise((r) => setTimeout(r, 150));
      return { frameTimes, peakCanvasBytes, peakCanvasCount, peakHeapBytes };
    });

    const cdpAfterScroll = cdpMetricMap((await cdp.send("Performance.getMetrics")).metrics);

    // Phase 3: Rapid Ctrl+wheel zoom burst (15 events in 150ms)
    const cdpBeforeZoom = cdpAfterScroll;
    const zoomResult = await page.evaluate(async () => {
      const scrollEl = document.querySelector(".pf-pdf-scroll");
      const view = (window).__PF_VIEW__;
      view._scale = 0.8;
      const statsBefore = { ...(window).__PF_BENCH_CFG__.renderStats };
      const frames = [];
      let peakCanvasBytes = 0;
      let peakCanvasCount = 0;
      let peakHeapBytes = 0;
      let rafRunning = true;
      let last = performance.now();
      const pump = (ts) => {
        frames.push(ts - last);
        last = ts;
        const canvases = document.querySelectorAll(".pf-pdf-canvas");
        let bytes = 0;
        let active = 0;
        canvases.forEach((c) => {
          const px = c.width * c.height;
          if (px > 0) active += 1;
          bytes += px * 4;
        });
        if (bytes > peakCanvasBytes) peakCanvasBytes = bytes;
        if (active > peakCanvasCount) peakCanvasCount = active;
        if (performance.memory?.usedJSHeapSize > peakHeapBytes) {
          peakHeapBytes = performance.memory.usedJSHeapSize;
        }
        if (rafRunning) requestAnimationFrame(pump);
      };
      requestAnimationFrame(pump);

      for (let i = 0; i < 15; i++) {
        scrollEl.dispatchEvent(
          new WheelEvent("wheel", { ctrlKey: true, deltaY: -100, bubbles: true, cancelable: true })
        );
        await new Promise((r) => setTimeout(r, 10));
      }
      await new Promise((r) => setTimeout(r, 320));
      rafRunning = false;
      const statsAfter = { ...(window).__PF_BENCH_CFG__.renderStats };
      return {
        frames,
        peakCanvasBytes,
        peakCanvasCount,
        peakHeapBytes,
        rendersStarted: statsAfter.started - statsBefore.started,
        rendersCompleted: statsAfter.completed - statsBefore.completed,
        rendersCancelled: statsAfter.cancelled - statsBefore.cancelled,
      };
    });
    const cdpAfterZoom = cdpMetricMap((await cdp.send("Performance.getMetrics")).metrics);

    // Phase 4: Rapid state-changed burst (15 events) + visibilitychange hide
    const stateAndHideResult = await page.evaluate(async () => {
      const listeners = (window).__PF_STATE_LISTENERS__ || [];
      const stats = (window).__PF_BENCH_CFG__.renderStats;
      const listBefore = stats.listAnnotationsCalls;
      for (let i = 0; i < 15; i++) {
        listeners[0]?.({ changedKeys: ["BENCH"] });
      }
      await new Promise((r) => setTimeout(r, 260));
      const listDelta = stats.listAnnotationsCalls - listBefore;

      const countCanvases = () => {
        let active = 0;
        let bytes = 0;
        document.querySelectorAll(".pf-pdf-canvas").forEach((c) => {
          const px = c.width * c.height;
          if (px > 0) active += 1;
          bytes += px * 4;
        });
        return { active, bytes };
      };
      const beforeHide = countCanvases();
      Object.defineProperty(document, "hidden", { value: true, configurable: true });
      document.dispatchEvent(new Event("visibilitychange"));
      await new Promise((r) => setTimeout(r, 40));
      const afterHide = countCanvases();

      const mem = performance.memory
        ? {
            usedJSHeapSize: performance.memory.usedJSHeapSize,
            totalJSHeapSize: performance.memory.totalJSHeapSize,
          }
        : null;
      const longTasks = (window).__longTasks || [];
      return { listDelta, beforeHide, afterHide, mem, longTasks };
    });

    const cdpEnd = cdpMetricMap((await cdp.send("Performance.getMetrics")).metrics);

    const allFrames = [...scrollResult.frameTimes, ...zoomResult.frames].sort((a, b) => a - b);
    const longTasks = stateAndHideResult.longTasks.filter((d) => d > 50);
    const peakCanvasBytes = Math.max(scrollResult.peakCanvasBytes, zoomResult.peakCanvasBytes);
    const peakCanvasCount = Math.max(scrollResult.peakCanvasCount, zoomResult.peakCanvasCount);
    const peakHeapBytes = Math.max(
      scrollResult.peakHeapBytes || 0,
      zoomResult.peakHeapBytes || 0,
      cdpAfterScroll.JSHeapUsedSize || 0,
      cdpAfterZoom.JSHeapUsedSize || 0,
      cdpEnd.JSHeapUsedSize || 0,
      stateAndHideResult.mem?.usedJSHeapSize || 0
    );
    const report = {
      browser: browser.version(),
      executable: exe || "playwright-bundled",
      config: { pages: opts.pages, dpr: opts.dpr, scale: opts.scale, annotations: opts.pages * 3 },
      openMs,
      scrollAndZoomRaf: {
        sampleCount: allFrames.length,
        p50Ms: Number(percentile(allFrames, 0.5).toFixed(2)),
        p95Ms: Number(percentile(allFrames, 0.95).toFixed(2)),
        maxMs: Number((allFrames[allFrames.length - 1] || 0).toFixed(2)),
        framesOver16_7ms: allFrames.filter((x) => x > 16.7).length,
        framesOver50ms: allFrames.filter((x) => x > 50).length,
      },
      longTasksOver50ms: {
        count: longTasks.length,
        maxMs: Number((Math.max(0, ...longTasks)).toFixed(2)),
        totalBlockingMs: Number(longTasks.reduce((s, d) => s + Math.max(0, d - 50), 0).toFixed(2)),
      },
      memory: {
        jsHeapPeakMb: Number((peakHeapBytes / 1048576).toFixed(2)),
        jsHeapEndMb: Number(((cdpEnd.JSHeapUsedSize || stateAndHideResult.mem?.usedJSHeapSize || 0) / 1048576).toFixed(2)),
        jsHeapTotalMb: Number(((cdpEnd.JSHeapTotalSize || stateAndHideResult.mem?.totalJSHeapSize || 0) / 1048576).toFixed(2)),
        scrollPeakCanvasCount: scrollResult.peakCanvasCount,
        scrollPeakCanvasMb: Number((scrollResult.peakCanvasBytes / 1048576).toFixed(2)),
        peakCanvasCount,
        peakCanvasMb: Number((peakCanvasBytes / 1048576).toFixed(2)),
        afterHideCanvasCount: stateAndHideResult.afterHide.active,
        afterHideCanvasMb: Number((stateAndHideResult.afterHide.bytes / 1048576).toFixed(2)),
      },
      zoomBurst: {
        rendersStarted: zoomResult.rendersStarted,
        rendersCompleted: zoomResult.rendersCompleted,
        rendersCancelled: zoomResult.rendersCancelled,
        cdpLayoutCountDelta: Math.round((cdpAfterZoom.LayoutCount || 0) - (cdpBeforeZoom.LayoutCount || 0)),
        cdpLayoutDurationMs: Number((((cdpAfterZoom.LayoutDuration || 0) - (cdpBeforeZoom.LayoutDuration || 0)) * 1000).toFixed(2)),
      },
      stateChangedBurst15x: {
        listAnnotationsCalls: stateAndHideResult.listDelta,
      },
      domNodesAfterMount: Math.round(cdpAfterMount.Nodes || 0),
      domNodesAfterScroll: Math.round(cdpAfterScroll.Nodes || 0),
      domNodesEnd: Math.round(cdpEnd.Nodes || 0),
    };

    if (opts.json) {
      console.log(JSON.stringify(report, null, 2));
    } else {
      console.log("\n=== PaperForge Real-Chromium PDF Runtime Benchmark ===");
      console.log(`Browser: Chromium ${report.browser} (${report.executable})`);
      console.log(`Config:  ${opts.pages} pages, ${opts.pages * 3} annotations, DPR=${opts.dpr}, scale=${opts.scale}`);
      console.log(`Open+Mount (${opts.pages}p): ${report.openMs} ms | DOM Nodes: ${report.domNodesAfterMount} -> ${report.domNodesAfterScroll} (scroll) -> ${report.domNodesEnd} (end)`);
      console.log(
        `rAF Frame Times: P50=${report.scrollAndZoomRaf.p50Ms} ms, P95=${report.scrollAndZoomRaf.p95Ms} ms, Max=${report.scrollAndZoomRaf.maxMs} ms (>16.7ms: ${report.scrollAndZoomRaf.framesOver16_7ms}/${report.scrollAndZoomRaf.sampleCount})`
      );
      console.log(
        `Long Tasks (>50ms): ${report.longTasksOver50ms.count} tasks (max ${report.longTasksOver50ms.maxMs} ms, TBT ${report.longTasksOver50ms.totalBlockingMs} ms)`
      );
      console.log(
        `JS Heap: Peak=${report.memory.jsHeapPeakMb} MB, End=${report.memory.jsHeapEndMb} MB / ${report.memory.jsHeapTotalMb} MB total`
      );
      console.log(
        `Canvas Pixel Memory: ScrollPeak=${report.memory.scrollPeakCanvasMb} MB (${report.memory.scrollPeakCanvasCount}), OverallPeak=${report.memory.peakCanvasMb} MB (${report.memory.peakCanvasCount}) -> After hide=${report.memory.afterHideCanvasMb} MB (${report.memory.afterHideCanvasCount})`
      );
      console.log(
        `Zoom Burst (15x/150ms): started=${report.zoomBurst.rendersStarted}, cancelled=${report.zoomBurst.rendersCancelled}, CDP LayoutCount delta=${report.zoomBurst.cdpLayoutCountDelta}, LayoutDuration=${report.zoomBurst.cdpLayoutDurationMs} ms`
      );
      console.log(
        `State-Changed Burst (15x): listAnnotations() calls = ${report.stateChangedBurst15x.listAnnotationsCalls}`
      );
      console.log("======================================================\n");
    }
  } finally {
    await browser?.close().catch(() => {});
    fs.rmSync(buildDir, { recursive: true, force: true });
  }
}

main().catch((err) => {
  console.error("[bench_pdf_chromium] FAILED:", err);
  process.exit(1);
});
