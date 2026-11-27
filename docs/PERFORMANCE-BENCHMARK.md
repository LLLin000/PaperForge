# PaperForge PDF Reader & Host Performance Benchmark

> Reproducible quantitative benchmark specification and **Before vs. After** evidence ledger for the PaperForge Obsidian plugin and PDF reader engine.

---

## 1. Benchmark Environment & Methodology

| Parameter | Value |
| --- | --- |
| **Baseline Commit (`master`)** | `2fcf81fb61330b94512d085819d4a0582d8b2eb2` (`v2.0.11`) |
| **Host OS / Runtime** | Windows (`win32`), Node `v24.11.1`, Vitest `v2.1.9` (`jsdom`) |
| **Real Browser Engine** | Chromium `158.0.8127.38` (`C:\Program Files\Google\Chrome\Application\chrome.exe`) via `playwright-core` + CDP |
| **High-DPI Test Profile** | `devicePixelRatio = 2.5`, `scale = 1.65 ~ 2.0` (`1.8` scroll / `2.0` peak), A4 `595 × 842 pt` |
| **Stress Workloads** | 100-page scroll (Vitest), 80-page / 240-annotation scroll + zoom (Chromium), 15× Ctrl+wheel burst in 150 ms, 15× `paperforge:state-changed` burst, 900-item/page dense 2-column selection fixture |

### Suites

1. **Deterministic Runtime Suite** — [`paperforge/plugin/tests/perf-pdf-runtime.test.ts`](../paperforge/plugin/tests/perf-pdf-runtime.test.ts)
   Measures canvas RGBA pixel footprint, eviction & `visibilitychange` release, Ctrl+wheel zoom `RenderTask` concurrency & `.pf-pdf-page` layout writes, `state-changed` -> `listAnnotations()` coalescing, and dense 2-column DOM span count / reading-order selection contamination.
2. **Real Headless Chromium Stress Suite** — [`scripts/dev/bench_pdf_chromium.mjs`](../scripts/dev/bench_pdf_chromium.mjs)
   Bundles the live `paperforge/plugin/src/views/pdf-annotator.ts` + `styles.css` with `esbuild` and measures real Blink/V8 metrics over CDP (`JSHeapUsedSize`, `Nodes`, `LayoutCount`, `LayoutDuration`), `PerformanceObserver("longtask")`, `requestAnimationFrame` P50/P95/Max frame times, and mounted `<canvas>` pixel bytes.
3. **Host-Impact Scorecard** — [`paperforge/plugin/tests/perf-benchmark.test.ts`](../paperforge/plugin/tests/perf-benchmark.test.ts)
   Measures plugin `onload()`, collapsed sidebar RPC suppression, 2,000-paper Bases & OCR Workspace rendering, Quick Switcher latency, CSS hygiene, and bundle size.

---

## 2. How to Run

### Vitest Deterministic Runtime Benchmark

```bash
cd paperforge/plugin
npx vitest run tests/perf-pdf-runtime.test.ts --reporter=verbose
```

To strictly enforce post-upgrade target budgets (for post-merge CI / verification):

```bash
cd paperforge/plugin
PF_PERF_ENFORCE_BUDGETS=1 npx vitest run tests/perf-pdf-runtime.test.ts --reporter=verbose
```

### Real Chromium Stress Benchmark

Requires `esbuild` (installed in `paperforge/plugin/node_modules`), `playwright-core` (local or global `node_modules`), and a local Chrome, Edge, or Playwright Chromium binary.

```bash
node scripts/dev/bench_pdf_chromium.mjs --pages=80 --dpr=2.5 --scale=1.8
```

Options:

- `--pages=80` — Simulated page count (50–100 recommended; spawns `3 × pages` annotations)
- `--dpr=2.5` — Emulated `deviceScaleFactor`
- `--scale=1.8` — Initial PDF zoom scale
- `--json` — Emit machine-readable JSON metrics
- `--allow-missing` — Exit `0` with a skip notice if `playwright-core` or a browser binary is unavailable
- `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/path/to/chrome` — Override automatic Chrome/Edge detection

---

## 3. Before vs. After Comparison

### 3A. Deterministic Runtime Metrics (`perf-pdf-runtime.test.ts`)

| Metric | Before (`master` `2fcf81fb`) | After (Post-Merge) | Target Budget |
| --- | --- | --- | --- |
| **Canvas peak mounted (100p scroll @ DPR=2.5, scale=1.8)** | `9 canvases` | _TBD (post-merge)_ | `<= 5 canvases` |
| **Canvas peak pixel memory (100p scroll @ DPR=2.5, scale=1.8)** | `348.37 MB (91.32 Mpx)` | _TBD (post-merge)_ | `<= 120.00 MB (<= 30 Mpx)` |
| **Single-canvas max pixels (DPR=2.5, scale=2.0)** | `12.52 Mpx (47.78 MB)` | _TBD (post-merge)_ | `<= 6.00 Mpx (<= 24.00 MB)` |
| **Effective canvas DPR @ `devicePixelRatio=2.5`** | `2.50x` | _TBD (post-merge)_ | `<= 2.00x` |
| **Visibility-hide (`document.hidden=true`) canvas release** | `8 -> 8 canvases (318.73 MB -> 318.73 MB)` | _TBD (post-merge)_ | `<= 1 canvas retained` |
| **Ctrl+wheel burst (15×/150ms): `page.render()` calls during burst** | `15 calls (16 total w/ settle)` | _TBD (post-merge)_ | `<= 3 during burst` |
| **Ctrl+wheel burst: peak concurrent uncancelled renders** | `9 concurrent (0 cancelled)` | _TBD (post-merge)_ | `<= 3 concurrent` |
| **Ctrl+wheel burst: `.pf-pdf-page` layout writes (reflows)** | `1500 layout writes (0 CSS transform previews)` | _TBD (post-merge)_ | `0 layout writes during burst` |
| **Rapid `state-changed` burst (15×): `listAnnotations()` RPCs** | `15 RPCs` | _TBD (post-merge)_ | `<= 2 RPCs (debounced)` |
| **Dense 2-col 5-page render+text mount (900 items/p)** | `146.39 ms (29.28 ms/p, 900 DOM spans/p)` | _TBD (post-merge)_ | `< 80 ms total, 0 DOM spans/p` |
| **2-col left-column selection latency & column leak** | `181.48 ms \| L=100, R_leak=90 (47.4%), maxX=0.912` | _TBD (post-merge)_ | `0.0% R_leak, maxX <= 0.480` |

### 3B. Real Headless Chromium Metrics (`bench_pdf_chromium.mjs --pages=80 --dpr=2.5 --scale=1.8`)

| Metric | Before (`master` `2fcf81fb`) | After (Post-Merge) | Target Goal |
| --- | --- | --- | --- |
| **Open + Mount (80p, 240 annotations)** | `143 ms` | _TBD (post-merge)_ | `< 120 ms` |
| **DOM Nodes (Open → Scroll → End)** | `8,375 -> 65,164 -> 196,470` | _TBD (post-merge)_ | `< 5,000` steady state |
| **rAF Frame Time P50 / P95 / Max** | `7.00 ms / 48.60 ms / 104.10 ms` | _TBD (post-merge)_ | `P95 <= 16.7 ms` |
| **rAF Frames > 16.7 ms** | `25 / 151 frames (16.6%)` | _TBD (post-merge)_ | `< 5%` |
| **Long Tasks (`> 50 ms`)** | `1 task (max 70.00 ms, TBT 20.00 ms)` | _TBD (post-merge)_ | `0 tasks` |
| **JS Heap (Peak / End / Total)** | `5.11 MB / 4.74 MB / 11 MB` | _TBD (post-merge)_ | `<= 10 MB` |
| **Canvas Pixel Memory (Scroll Peak)** | `348.37 MB (9 canvases)` | _TBD (post-merge)_ | `<= 120 MB (<= 5 canvases)` |
| **Canvas Pixel Memory (Zoom Overall Peak)** | `812.82 MB (24 canvases)` | _TBD (post-merge)_ | `<= 150 MB` |
| **Canvas Pixel Memory (After `visibilitychange` hidden)** | `812.82 MB (24 canvases, 0% released)` | _TBD (post-merge)_ | `<= 25 MB (<= 1 canvas)` |
| **Zoom Burst (15×/150ms) Renders & Cancel** | `27 started, 0 cancelled` | _TBD (post-merge)_ | `<= 3 started, stale cancelled` |
| **Zoom Burst CDP `LayoutCount` / `LayoutDuration`** | `46 layouts / 219.83 ms` | _TBD (post-merge)_ | `<= 4 layouts / < 25 ms` |
| **State-Changed Burst (15×) `listAnnotations()`** | `15 calls` | _TBD (post-merge)_ | `<= 2 calls` |

### 3C. Existing Host-Impact Scorecard (`perf-benchmark.test.ts` Baseline on `master`)

- **Plugin `onload()`**: `8.96 ms` (budget `< 300.00 ms`)
- **100× collapsed/non-doc switch**: `7.92 ms (0 RPCs)` (budget `< 150.00 ms`)
- **Bases initial render (2,000 papers, chunked 80)**: `261.99 ms` (budget `< 1500.00 ms`)
- **Bases filter update (2,000 papers)**: `4.13 ms` (budget `< 250.00 ms`)
- **Bases surgical checkbox toggle**: `22.57 ms` (budget `< 150.00 ms`)
- **Quick Switcher query (2,000 papers)**: `1.95 ms/query` (budget `< 40.00 ms`)
- **`styles.css` hygiene & size**: `412.6 KB (0 bare *, 0 transition:all)` (budget `< 650 KB`)
- **OCR Workspace render (2,000 papers, 100 visible)**: `79.47 ms` (budget `< 1200.00 ms`)
- **OCR Workspace filter refresh (2,000 papers)**: `133.90 ms` (budget `< 600.00 ms`)
- **PDF overlays full rebuild (100p / 200 anns)**: `49.93 ms` (budget `< 800.00 ms`)
- **PDF overlays surgical single page**: `0.23 ms` (budget `< 120.00 ms`)
- **PDF 100-page cached fulltext search**: `1.52 ms` (budget `< 200.00 ms`)
- **Settings O(1) collision probe (1,000 dirs)**: `0.95 ms` (budget `< 150.00 ms`)
- **Settings Control Center 2× `display()`**: `51.84 ms` (budget `< 800.00 ms`)
- **`main.js` bundle size**: `935.3 KB` (budget `< 1500 KB`)

---

## 4. Baseline Bottleneck Diagnosis (`master`)

1. **Unbounded High-DPI Canvas Allocation (`812.82 MB` peak in Chromium, `348.37 MB` scroll peak)**:
   - `pdf-annotator.ts` reads raw `devicePixelRatio` (`2.5x`) with no DPR ceiling or per-canvas pixel cap, allocating `12.52 Mpx` (`47.78 MB`) for a single A4 page at `2.0x` zoom.
   - `MAX_RENDERED_CANVASES = 9` retains up to 9 canvases during scroll, and during rapid zoom double-buffering + uncancelled renders accumulate up to **24 active canvases (`812.82 MB`)** simultaneously.
   - No `visibilitychange` listener exists, so hiding/backgrounding the Obsidian tab releases `0 MB`.
2. **Zoom Reflow Storm & Uncancelled `RenderTask`s (`1,500` layout writes / `46` Chromium layouts / `219.83 ms`)**:
   - Every Ctrl+wheel event invokes `_syncZoomAndRerender()`, rewriting `style.width` and `style.height` on all 100 `.pf-pdf-page` containers (`15 × 100 = 1,500` writes) and launching overlapping `page.render()` tasks without storing or calling `renderTask.cancel()`.
3. **Un-debounced `paperforge:state-changed` Reloads (`15 -> 15` RPCs)**:
   - Batch agent annotations or rapid sync updates trigger 1:1 `listAnnotations()` RPCs + full overlay/sidebar rebuilds instead of coalescing bursts.
4. **Synchronous 900-Span DOM TextLayer & 2-Column Range Contamination (`196,470` DOM nodes, `47.4%` column leak)**:
   - Creating 900 `<span>` nodes per page synchronously with `measureCtx.measureText` bloats DOM node count to `65k–196k` nodes across an 80-page session.
   - Stream-interleaved 2-column items cause browser DOM `Range` selection on the left column to pull in `47.4%` of right-column tokens (`maxX = 0.912`).
