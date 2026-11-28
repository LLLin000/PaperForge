export interface PdfTextContentItem {
  str?: string;
  transform?: number[];
  width?: number;
  height?: number;
  hasEOL?: boolean;
  fontName?: string;
  dir?: string;
}

export interface PdfTextStyleMeta {
  fontFamily?: string;
  ascent?: number;
  descent?: number;
  vertical?: boolean;
}

export interface PdfTextContentLike {
  items?: PdfTextContentItem[];
  styles?: Record<string, PdfTextStyleMeta>;
}

export interface PdfViewportLike {
  width: number;
  height: number;
  transform?: number[];
}

export interface SimpleRectLike {
  left: number;
  top: number;
  right: number;
  bottom: number;
  width: number;
  height: number;
}

export interface TextCharBox {
  char: string;
  /** Normalized [0..1] left, top, right, bottom */
  l: number;
  t: number;
  r: number;
  b: number;
}

export interface TextRun {
  id: number;
  str: string;
  l: number;
  t: number;
  r: number;
  b: number;
  fontH: number;
  hasEOL: boolean;
  /** Cumulative normalized X edges inside this run, length === str.length + 1 */
  charEdges: number[];
  lineIndex: number;
  columnId: number;
  orderIndex: number;
}

export interface TextLine {
  lineIndex: number;
  columnId: number;
  l: number;
  t: number;
  r: number;
  b: number;
  runIndices: number[];
}

export interface PageTextModel {
  pageWidth: number;
  pageHeight: number;
  runs: TextRun[];
  lines: TextLine[];
  plainText: string;
}

export interface TextPosition {
  runIndex: number;
  charOffset: number;
}

export interface GeometricSelectionResult {
  rects: number[][];
  exactText: string;
  start: TextPosition;
  end: TextPosition;
}

/** 6-element 2D affine matrix multiply matching PDF.js `Util.transform(m1, m2)`. */
export function multiplyPdfTransform(m1: number[], m2: number[]): number[] {
  return [
    m1[0] * m2[0] + m1[2] * m2[1],
    m1[1] * m2[0] + m1[3] * m2[1],
    m1[0] * m2[2] + m1[2] * m2[3],
    m1[1] * m2[2] + m1[3] * m2[3],
    m1[0] * m2[4] + m1[2] * m2[5] + m1[4],
    m1[1] * m2[4] + m1[3] * m2[5] + m1[5],
  ];
}

/**
 * Clean raw browser `Range.getClientRects()` against page bounds:
 * - Drops container-level / multi-paragraph jumbo boxes in two-column PDFs
 * - Merges only adjacent same-line fragments (refusing to bridge column gutters)
 * - Trims slight vertical overlap so adjacent highlight lines retain a subtle seam
 */
export function normalizeSelectionRects(
  rawRects: SimpleRectLike[],
  pageRect: { left: number; top: number; width: number; height: number }
): number[][] {
  if (pageRect.width <= 0 || pageRect.height <= 0) return [];
  interface PxBox {
    l: number;
    t: number;
    r: number;
    b: number;
    w: number;
    h: number;
  }
  const clipped: PxBox[] = [];
  for (const rc of rawRects) {
    if (rc.width < 2 || rc.height < 2) continue;
    const l = Math.max(0, rc.left - pageRect.left);
    const t = Math.max(0, rc.top - pageRect.top);
    const r = Math.min(pageRect.width, rc.right - pageRect.left);
    const b = Math.min(pageRect.height, rc.bottom - pageRect.top);
    const w = r - l;
    const h = b - t;
    if (w < 2 || h < 2) continue;
    clipped.push({ l, t, r, b, w, h });
  }
  if (clipped.length === 0) return [];

  const sortedHeights = clipped.map((x) => x.h).sort((a, b) => a - b);
  const medH = sortedHeights[Math.floor(sortedHeights.length / 2)] || 12;

  // Reject spurious container wrappers when normal line-height rects are present
  const nonGiant = clipped.filter(
    (x) =>
      x.h <= Math.max(medH * 2.6, 40) &&
      !(x.w > pageRect.width * 0.94 && x.h > pageRect.height * 0.12)
  );
  const pool = nonGiant.length > 0 ? nonGiant : clipped;

  // Drop boxes strictly contained inside another valid box
  const eps = 1.5;
  const deduped = pool.filter(
    (a, idx) =>
      !pool.some(
        (b, j) =>
          j !== idx &&
          b.l <= a.l + eps &&
          b.t <= a.t + eps &&
          b.r >= a.r - eps &&
          b.b >= a.b - eps &&
          b.w * b.h >= a.w * a.h
      )
  );

  // Sort top-to-bottom by line center, then left-to-right
  const band = Math.max(4, medH * 0.48);
  deduped.sort((a, b) => {
    const cyA = (a.t + a.b) / 2;
    const cyB = (b.t + b.b) / 2;
    if (Math.abs(cyA - cyB) > band) return cyA - cyB;
    return a.l - b.l;
  });

  // Merge contiguous glyphs/spans on the same line, never bridging column gutters
  const merged: PxBox[] = [];
  for (const cur of deduped) {
    const prev = merged[merged.length - 1];
    if (prev) {
      const prevCy = (prev.t + prev.b) / 2;
      const curCy = (cur.t + cur.b) / 2;
      const sameLine =
        Math.abs(prevCy - curCy) <= Math.min(prev.h, cur.h) * 0.48;
      const gutterLimit = Math.max(Math.min(prev.h, cur.h) * 1.8, 16);
      const smallGap = cur.l - prev.r <= gutterLimit && cur.l >= prev.l - eps;
      if (sameLine && smallGap) {
        prev.l = Math.min(prev.l, cur.l);
        prev.t = Math.min(prev.t, cur.t);
        prev.r = Math.max(prev.r, cur.r);
        prev.b = Math.max(prev.b, cur.b);
        prev.w = prev.r - prev.l;
        prev.h = prev.b - prev.t;
        continue;
      }
    }
    merged.push({ ...cur });
  }

  // Keep a crisp 1px breathing seam between stacked highlight lines
  for (let i = 1; i < merged.length; i++) {
    const dn = merged[i];
    for (let j = i - 1; j >= 0; j--) {
      const up = merged[j];
      if (dn.t - up.b >= medH) break;
      const horizOverlap = dn.l < up.r && dn.r > up.l;
      if (horizOverlap && up.b > dn.t - 0.5 && up.b - dn.t < medH) {
        const mid = (up.b + dn.t) / 2;
        up.b = Math.min(up.b, mid - 0.6);
        dn.t = Math.max(dn.t, mid + 0.6);
        if (dn.b - dn.t < 2) dn.b = dn.t + 2;
      }
    }
  }

  return merged.map((b) => [
    Math.max(0, Math.min(1, b.l / pageRect.width)),
    Math.max(0, Math.min(1, b.t / pageRect.height)),
    Math.max(0, Math.min(1, b.r / pageRect.width)),
    Math.max(0, Math.min(1, b.b / pageRect.height)),
  ]);
}

function charAdvanceWeight(ch: string): number {
  if (ch === " " || ch === "\t") return 0.28;
  if ("ilIjft.,:;!'|`".includes(ch)) return 0.29;
  if ("mwMW@#%&".includes(ch)) return 0.82;
  if ("ABCDEFGHIJKLMNOPQRSTUVWXYZ".includes(ch)) return 0.66;
  const code = ch.charCodeAt(0);
  // CJK / full-width glyphs
  if (
    (code >= 0x4e00 && code <= 0x9fff) ||
    (code >= 0x3000 && code <= 0x30ff) ||
    (code >= 0xff00 && code <= 0xffef)
  ) {
    return 0.96;
  }
  return 0.52;
}

function buildCharEdges(str: string, leftNorm: number, widthNorm: number): number[] {
  const n = str.length;
  const edges = new Array<number>(n + 1);
  edges[0] = leftNorm;
  if (n === 0 || widthNorm <= 0) {
    for (let i = 1; i <= n; i++) edges[i] = leftNorm;
    return edges;
  }
  let totalWeight = 0;
  const weights = new Array<number>(n);
  for (let i = 0; i < n; i++) {
    const w = charAdvanceWeight(str[i]);
    weights[i] = w;
    totalWeight += w;
  }
  if (totalWeight <= 0) totalWeight = n;
  let acc = 0;
  for (let i = 0; i < n; i++) {
    acc += weights[i];
    edges[i + 1] = leftNorm + (acc / totalWeight) * widthNorm;
  }
  edges[n] = leftNorm + widthNorm;
  return edges;
}

function estimateStringWidthPx(str: string, fontHPx: number): number {
  let sum = 0;
  for (let i = 0; i < str.length; i++) {
    sum += charAdvanceWeight(str[i]);
  }
  return Math.max(fontHPx * 0.3, sum * fontHPx);
}

interface RawRun {
  str: string;
  l: number;
  t: number;
  r: number;
  b: number;
  fontH: number;
  hasEOL: boolean;
}

function clamp01(v: number): number {
  return Math.max(0, Math.min(1, v));
}

function median(vals: number[], fallback: number): number {
  if (vals.length === 0) return fallback;
  const sorted = [...vals].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)] || fallback;
}

/**
 * Find the widest interior vertical gutter `[gx0, gx1]` where the fewest runs cross,
 * requiring meaningful content on both left and right sides so single-column gaps
 * or short tabbed lines never trigger false column splits.
 */
function findColumnGutter(
  runs: RawRun[]
): { gx0: number; gx1: number; crossers: RawRun[] } | null {
  if (runs.length < 3) return null;
  let minX = 1;
  let maxX = 0;
  const heights: number[] = [];
  for (const r of runs) {
    if (r.l < minX) minX = r.l;
    if (r.r > maxX) maxX = r.r;
    heights.push(r.b - r.t);
  }
  const spanX = maxX - minX;
  const medH = median(heights, 0.015);
  const minGutterW = Math.max(0.016, medH * 1.35);
  if (spanX < minGutterW * 4) return null;

  // Exclude wide spanning runs (> 55% of region width) when searching for body gutters
  const narrowRuns = runs.filter((r) => r.r - r.l <= spanX * 0.56);
  if (narrowRuns.length < 3) return null;

  // Sweep candidate X coordinates across narrow runs
  const events: Array<{ x: number; delta: number }> = [];
  for (const r of narrowRuns) {
    events.push({ x: r.l, delta: 1 });
    events.push({ x: r.r, delta: -1 });
  }
  events.sort((a, b) => a.x - b.x || a.delta - b.delta);

  let active = 0;
  let prevX = minX;
  let bestGap: { x0: number; x1: number; score: number } | null = null;
  const marginGuard = spanX * 0.16;

  for (const ev of events) {
    if (active === 0 && ev.x - prevX >= minGutterW) {
      const x0 = prevX;
      const x1 = ev.x;
      const mid = (x0 + x1) / 2;
      if (mid >= minX + marginGuard && mid <= maxX - marginGuard) {
        let leftCount = 0;
        let rightCount = 0;
        for (const r of narrowRuns) {
          if (r.r <= x0 + 1e-4) leftCount++;
          else if (r.l >= x1 - 1e-4) rightCount++;
        }
        const width = x1 - x0;
        const validColPair =
          (leftCount >= 2 && rightCount >= 2) ||
          (Math.max(leftCount, rightCount) >= 2 &&
            Math.min(leftCount, rightCount) >= 1 &&
            width >= 0.035);
        if (validColPair) {
          const balance = Math.min(leftCount, rightCount) / Math.max(leftCount, rightCount);
          const score = width * (0.5 + balance);
          if (!bestGap || score > bestGap.score) {
            bestGap = { x0, x1, score };
          }
        }
      }
    }
    active += ev.delta;
    prevX = ev.x;
  }

  if (!bestGap) return null;
  const mid = (bestGap.x0 + bestGap.x1) / 2;
  const crossers = runs.filter((r) => r.l < mid - 1e-4 && r.r > mid + 1e-4);
  const leftTotal = runs.filter((r) => r.r <= mid + 1e-4).length;
  const rightTotal = runs.filter((r) => r.l >= mid - 1e-4).length;
  // Require majority of lines in this region to actually sit in left/right columns
  const gapW = bestGap.x1 - bestGap.x0;
  const hasTwoSides =
    (leftTotal >= 2 && rightTotal >= 2) ||
    (Math.max(leftTotal, rightTotal) >= 2 &&
      Math.min(leftTotal, rightTotal) >= 1 &&
      gapW >= 0.035);
  if (!hasTwoSides) return null;
  if (crossers.length > Math.max(2, runs.length * 0.45)) return null;

  return { gx0: bestGap.x0, gx1: bestGap.x1, crossers };
}

/**
 * Recursive XY-cut column & block ordering.
 * Produces leaf groups sorted in natural human reading order.
 */
function xyCutOrder(runs: RawRun[]): RawRun[][] {
  if (runs.length === 0) return [];
  if (runs.length === 1) return [runs];

  const gutter = findColumnGutter(runs);
  if (gutter) {
    const mid = (gutter.gx0 + gutter.gx1) / 2;
    if (gutter.crossers.length === 0) {
      const left = runs.filter((r) => (r.l + r.r) / 2 <= mid);
      const right = runs.filter((r) => (r.l + r.r) / 2 > mid);
      if (left.length > 0 && right.length > 0) {
        return [...xyCutOrder(left), ...xyCutOrder(right)];
      }
    } else {
      // Partition horizontally around spanning header/footer/figure blocks so each
      // non-spanning Y-band can cleanly X-cut into columns without column jumping.
      const sortedCrossers = [...gutter.crossers].sort((a, b) => a.t - b.t);
      const bands: Array<{ y0: number; y1: number }> = [];
      for (const c of sortedCrossers) {
        const last = bands[bands.length - 1];
        if (last && c.t <= last.y1 + 0.004) {
          last.y1 = Math.max(last.y1, c.b);
        } else {
          bands.push({ y0: c.t, y1: c.b });
        }
      }

      // Check if partitioning by crosser Y-bands strictly shrinks the problem
      const groups: RawRun[][] = [];
      let cursorY = -1;
      for (const band of bands) {
        const above = runs.filter(
          (r) => !gutter.crossers.includes(r) && (r.t + r.b) / 2 > cursorY && (r.t + r.b) / 2 < band.y0
        );
        if (above.length > 0) groups.push(above);

        const inBand = runs.filter(
          (r) =>
            gutter.crossers.includes(r)
              ? r.t >= band.y0 - 1e-4 && r.b <= band.y1 + 1e-4
              : (r.t + r.b) / 2 >= band.y0 && (r.t + r.b) / 2 <= band.y1
        );
        if (inBand.length > 0) groups.push(inBand);
        cursorY = band.y1;
      }
      const below = runs.filter(
        (r) => !gutter.crossers.includes(r) && (r.t + r.b) / 2 > cursorY
      );
      if (below.length > 0) groups.push(below);

      if (groups.length > 1) {
        const out: RawRun[][] = [];
        for (const g of groups) {
          if (g.length < runs.length) {
            out.push(...xyCutOrder(g));
          } else {
            out.push(g);
          }
        }
        return out;
      }
    }
  }

  return [runs];
}

function joinRunsText(runs: TextRun[]): string {
  if (runs.length === 0) return "";
  let out = runs[0].str;
  for (let i = 1; i < runs.length; i++) {
    const prev = runs[i - 1];
    const cur = runs[i];
    const sameLine = prev.lineIndex === cur.lineIndex;
    if (!sameLine) {
      if (out.endsWith("-") && !out.endsWith(" -") && /^[a-zA-Z]/.test(cur.str)) {
        out = out.slice(0, -1) + cur.str;
      } else {
        out += "\n" + cur.str;
      }
      continue;
    }
    const avgCharW =
      (prev.r - prev.l) / Math.max(1, prev.str.length) || 0.005;
    const gap = cur.l - prev.r;
    const needsSpace =
      gap > avgCharW * 0.22 &&
      !out.endsWith(" ") &&
      !cur.str.startsWith(" ");
    out += (needsSpace ? " " : "") + cur.str;
  }
  return out;
}

/**
 * Build a scale-invariant normalized `PageTextModel` from PDF.js `getTextContent()`.
 * All coordinates are stored in [0..1] normalized space relative to `viewport`.
 */
export function buildPageTextModel(
  textContent: PdfTextContentLike,
  viewport: PdfViewportLike
): PageTextModel {
  const pageWidth = Math.max(1, viewport.width);
  const pageHeight = Math.max(1, viewport.height);
  const vt = viewport.transform;
  const styles = textContent.styles ?? {};
  const rawRuns: RawRun[] = [];

  for (const item of textContent.items ?? []) {
    const str = item.str ?? "";
    if (!str || !str.trim()) continue;
    const tx = item.transform;
    let xPx = 0;
    let baselineYPx = pageHeight * 0.5;
    let fontHPx = Math.max(6, (item.height || 10) * (vt ? Math.hypot(vt[0], vt[1]) || 1 : 1));
    let vpScale = 1;

    if (tx && tx.length >= 6 && vt && vt.length >= 6) {
      vpScale = Math.hypot(vt[0], vt[1]) || 1;
      if (vt[3] < 0) {
        const m = multiplyPdfTransform(vt, tx);
        xPx = m[4];
        baselineYPx = m[5];
        fontHPx = Math.max(
          4,
          Math.hypot(m[2], m[3]) || Math.hypot(m[0], m[1]) || (item.height || 10) * vpScale
        );
      } else {
        const scaleY = Math.hypot(vt[2], vt[3]) || vpScale;
        xPx = vt[0] * tx[4] + vt[2] * tx[5] + vt[4];
        baselineYPx =
          pageHeight - (vt[1] * tx[4] + vt[3] * tx[5] + vt[5]);
        fontHPx = Math.max(
          4,
          Math.abs(tx[3] || item.height || 10) * scaleY
        );
      }
    } else if (tx && tx.length >= 6) {
      xPx = tx[4];
      baselineYPx = pageHeight - tx[5];
      fontHPx = Math.max(4, Math.abs(tx[3] || item.height || 10));
    }

    const styleMeta = item.fontName ? styles[item.fontName] : undefined;
    const ascent =
      typeof styleMeta?.ascent === "number" && styleMeta.ascent > 0.3 && styleMeta.ascent <= 1.2
        ? styleMeta.ascent
        : 0.84;
    const descentRaw =
      typeof styleMeta?.descent === "number" ? Math.abs(styleMeta.descent) : 0.18;
    const descent = descentRaw > 0.05 && descentRaw <= 0.45 ? descentRaw : 0.18;

    const itemWidthPx =
      typeof item.width === "number" && item.width > 0
        ? item.width * vpScale
        : estimateStringWidthPx(str, fontHPx);

    const topPx = Math.max(0, baselineYPx - fontHPx * ascent);
    const botPx = Math.min(pageHeight, baselineYPx + fontHPx * descent);
    const leftPx = Math.max(0, xPx);
    const rightPx = Math.min(pageWidth, xPx + Math.max(1, itemWidthPx));

    if (rightPx <= leftPx || botPx <= topPx) continue;

    rawRuns.push({
      str,
      l: clamp01(leftPx / pageWidth),
      t: clamp01(topPx / pageHeight),
      r: clamp01(rightPx / pageWidth),
      b: clamp01(botPx / pageHeight),
      fontH: fontHPx / pageHeight,
      hasEOL: Boolean(item.hasEOL),
    });
  }

  if (rawRuns.length === 0) {
    return { pageWidth, pageHeight, runs: [], lines: [], plainText: "" };
  }

  // Partition into reading-order columns/blocks via recursive XY-cut
  const columnGroups = xyCutOrder(rawRuns);

  const runs: TextRun[] = [];
  const lines: TextLine[] = [];

  columnGroups.forEach((group, colIdx) => {
    const heights = group.map((g) => g.b - g.t);
    const medH = median(heights, 0.015);
    const lineTol = Math.max(0.004, medH * 0.48);

    const sorted = [...group].sort((a, b) => {
      const cyA = (a.t + a.b) / 2;
      const cyB = (b.t + b.b) / 2;
      if (Math.abs(cyA - cyB) > lineTol) return cyA - cyB;
      return a.l - b.l;
    });

    // Cluster runs into visual lines within this column/block
    const colLines: RawRun[][] = [];
    for (const r of sorted) {
      const cy = (r.t + r.b) / 2;
      const prevLine = colLines[colLines.length - 1];
      if (prevLine) {
        const ref = prevLine[0];
        const refCy = (ref.t + ref.b) / 2;
        const tol = Math.max(0.003, Math.min(ref.b - ref.t, r.b - r.t) * 0.52);
        if (Math.abs(cy - refCy) <= tol) {
          prevLine.push(r);
          continue;
        }
      }
      colLines.push([r]);
    }

    for (const rawLine of colLines) {
      rawLine.sort((a, b) => a.l - b.l);
      const lineIdx = lines.length;
      const runIndices: number[] = [];
      let lineL = 1;
      let lineT = 1;
      let lineR = 0;
      let lineB = 0;

      for (const r of rawLine) {
        const runIdx = runs.length;
        runIndices.push(runIdx);
        runs.push({
          id: runIdx,
          str: r.str,
          l: r.l,
          t: r.t,
          r: r.r,
          b: r.b,
          fontH: r.fontH,
          hasEOL: r.hasEOL,
          charEdges: buildCharEdges(r.str, r.l, r.r - r.l),
          lineIndex: lineIdx,
          columnId: colIdx,
          orderIndex: runIdx,
        });
        lineL = Math.min(lineL, r.l);
        lineT = Math.min(lineT, r.t);
        lineR = Math.max(lineR, r.r);
        lineB = Math.max(lineB, r.b);
      }

      lines.push({
        lineIndex: lineIdx,
        columnId: colIdx,
        l: lineL,
        t: lineT,
        r: lineR,
        b: lineB,
        runIndices,
      });
    }
  });

  const plainText = joinRunsText(runs);
  return { pageWidth, pageHeight, runs, lines, plainText };
}

function charOffsetInRun(run: TextRun, nx: number): number {
  const edges = run.charEdges;
  const n = run.str.length;
  if (nx <= edges[0]) return 0;
  if (nx >= edges[n]) return n;
  for (let i = 0; i < n; i++) {
    const mid = (edges[i] + edges[i + 1]) / 2;
    if (nx < mid) return i;
  }
  return n;
}

/**
 * Hit-test normalized coordinates `(nx, ny)` against `PageTextModel`.
 * Prioritizes lines in the same column bounds to prevent column-jumping when dragging near gutters.
 */
export function hitTestPoint(
  model: PageTextModel,
  nx: number,
  ny: number,
  preferredColumnId?: number
): TextPosition | null {
  if (model.runs.length === 0 || model.lines.length === 0) return null;

  // 1. Direct run hit (with slight vertical tolerance)
  for (const run of model.runs) {
    const padY = (run.b - run.t) * 0.15;
    if (
      nx >= run.l &&
      nx <= run.r &&
      ny >= run.t - padY &&
      ny <= run.b + padY
    ) {
      return {
        runIndex: run.orderIndex,
        charOffset: charOffsetInRun(run, nx),
      };
    }
  }

  // 2. Nearest line, preferring matching column if active drag started in one
  let bestLine: TextLine | null = null;
  let bestScore = Infinity;

  for (const line of model.lines) {
    const dx = nx < line.l ? line.l - nx : nx > line.r ? nx - line.r : 0;
    const dy = ny < line.t ? line.t - ny : ny > line.b ? ny - line.b : 0;
    const colPenalty =
      preferredColumnId !== undefined && line.columnId !== preferredColumnId
        ? 0.25
        : 0;
    // Weight vertical distance inside same horizontal band gently, penalize cross-column distance strongly
    const score = dy * 2.5 + dx * 4.0 + colPenalty;
    if (score < bestScore) {
      bestScore = score;
      bestLine = line;
    }
  }

  if (!bestLine || bestLine.runIndices.length === 0) return null;

  // Find closest run on bestLine
  let bestRun = model.runs[bestLine.runIndices[0]];
  let bestDx = Infinity;
  for (const rIdx of bestLine.runIndices) {
    const run = model.runs[rIdx];
    const dx = nx < run.l ? run.l - nx : nx > run.r ? nx - run.r : 0;
    if (dx < bestDx) {
      bestDx = dx;
      bestRun = run;
    }
  }

  return {
    runIndex: bestRun.orderIndex,
    charOffset: charOffsetInRun(bestRun, nx),
  };
}

function compareTextPos(a: TextPosition, b: TextPosition): number {
  if (a.runIndex !== b.runIndex) return a.runIndex - b.runIndex;
  return a.charOffset - b.charOffset;
}

/**
 * Compute crisp per-line normalized highlight rects and reading-order text between `anchor` and `focus`.
 */
export function selectRange(
  model: PageTextModel,
  anchor: TextPosition,
  focus: TextPosition
): GeometricSelectionResult {
  if (model.runs.length === 0) {
    return { rects: [], exactText: "", start: anchor, end: focus };
  }
  const forward = compareTextPos(anchor, focus) <= 0;
  const start = forward ? anchor : focus;
  const end = forward ? focus : anchor;

  if (
    start.runIndex === end.runIndex &&
    start.charOffset === end.charOffset
  ) {
    return { rects: [], exactText: "", start, end };
  }

  interface LineSeg {
    l: number;
    t: number;
    r: number;
    b: number;
    lineIndex: number;
    runs: Array<{ run: TextRun; slice: string; l: number; r: number }>;
  }

  const lineMap = new Map<number, LineSeg>();

  for (let i = start.runIndex; i <= end.runIndex; i++) {
    const run = model.runs[i];
    if (!run) continue;
    const c0 = i === start.runIndex ? Math.max(0, start.charOffset) : 0;
    const c1 =
      i === end.runIndex
        ? Math.min(run.str.length, end.charOffset)
        : run.str.length;
    if (c1 <= c0) continue;

    const slice = run.str.slice(c0, c1);
    const l = run.charEdges[c0] ?? run.l;
    const r = run.charEdges[c1] ?? run.r;
    if (r <= l) continue;

    let seg = lineMap.get(run.lineIndex);
    if (!seg) {
      seg = {
        l,
        t: run.t,
        r,
        b: run.b,
        lineIndex: run.lineIndex,
        runs: [],
      };
      lineMap.set(run.lineIndex, seg);
    } else {
      seg.l = Math.min(seg.l, l);
      seg.t = Math.min(seg.t, run.t);
      seg.r = Math.max(seg.r, r);
      seg.b = Math.max(seg.b, run.b);
    }
    seg.runs.push({ run, slice, l, r });
  }

  const segs = Array.from(lineMap.values()).sort(
    (a, b) => a.lineIndex - b.lineIndex
  );
  if (segs.length === 0) {
    return { rects: [], exactText: "", start, end };
  }

  // Trim slight vertical overlap between adjacent lines for clean visual seam
  for (let i = 1; i < segs.length; i++) {
    const dn = segs[i];
    const up = segs[i - 1];
    const horizOverlap = dn.l < up.r && dn.r > up.l;
    const h = Math.min(up.b - up.t, dn.b - dn.t);
    if (horizOverlap && up.b > dn.t - 0.001 && up.b - dn.t < h) {
      const mid = (up.b + dn.t) / 2;
      up.b = Math.min(up.b, mid - 0.0008);
      dn.t = Math.max(dn.t, mid + 0.0008);
    }
  }

  const rects = segs.map((s) => [
    clamp01(s.l),
    clamp01(s.t),
    clamp01(s.r),
    clamp01(s.b),
  ]);

  // Build clean reading-order text
  const textLines: string[] = [];
  for (const seg of segs) {
    let lineTxt = "";
    for (let j = 0; j < seg.runs.length; j++) {
      const part = seg.runs[j];
      if (j > 0) {
        const prev = seg.runs[j - 1];
        const avgCharW =
          (prev.r - prev.l) / Math.max(1, prev.slice.length) || 0.005;
        const gap = part.l - prev.r;
        if (
          gap > avgCharW * 0.22 &&
          !lineTxt.endsWith(" ") &&
          !part.slice.startsWith(" ")
        ) {
          lineTxt += " ";
        }
      }
      lineTxt += part.slice;
    }
    if (lineTxt) textLines.push(lineTxt);
  }

  let exactText = "";
  for (let i = 0; i < textLines.length; i++) {
    const cur = textLines[i];
    if (i === 0) {
      exactText = cur;
    } else if (
      exactText.endsWith("-") &&
      !exactText.endsWith(" -") &&
      /^[a-zA-Z]/.test(cur)
    ) {
      exactText = exactText.slice(0, -1) + cur;
    } else {
      exactText += "\n" + cur;
    }
  }

  return { rects, exactText: exactText.trim(), start, end };
}

const WORD_CHAR_RE = /[\p{L}\p{N}_'-]/u;

/** Double-click word selection in normalized coordinates. */
export function selectWordAt(
  model: PageTextModel,
  nx: number,
  ny: number
): GeometricSelectionResult | null {
  const pos = hitTestPoint(model, nx, ny);
  if (!pos) return null;
  const run = model.runs[pos.runIndex];
  if (!run || !run.str) return null;

  const idx = Math.min(run.str.length - 1, Math.max(0, pos.charOffset));
  const line = model.lines[run.lineIndex];
  if (!line) return null;

  // Flatten line runs into character tokens to allow words spanning run boundaries
  const flatChars: Array<{ runIndex: number; charOffset: number; ch: string }> = [];
  let targetFlatIdx = 0;
  for (const rIdx of line.runIndices) {
    const r = model.runs[rIdx];
    const prevRun =
      flatChars.length > 0 ? model.runs[flatChars[flatChars.length - 1].runIndex] : null;
    if (prevRun) {
      const avgW = (prevRun.r - prevRun.l) / Math.max(1, prevRun.str.length) || 0.005;
      if (r.l - prevRun.r > avgW * 0.22) {
        flatChars.push({ runIndex: prevRun.orderIndex, charOffset: prevRun.str.length, ch: " " });
      }
    }
    for (let c = 0; c < r.str.length; c++) {
      if (r.orderIndex === run.orderIndex && c === idx) {
        targetFlatIdx = flatChars.length;
      }
      flatChars.push({ runIndex: r.orderIndex, charOffset: c, ch: r.str[c] });
    }
  }
  if (flatChars.length === 0) return null;

  const targetCh = flatChars[targetFlatIdx]?.ch ?? " ";
  const isWord = WORD_CHAR_RE.test(targetCh);
  let left = targetFlatIdx;
  let right = targetFlatIdx;
  if (isWord) {
    while (left > 0 && WORD_CHAR_RE.test(flatChars[left - 1].ch)) left--;
    while (right + 1 < flatChars.length && WORD_CHAR_RE.test(flatChars[right + 1].ch)) right++;
  }

  const startToken = flatChars[left];
  const endToken = flatChars[right];
  return selectRange(
    model,
    { runIndex: startToken.runIndex, charOffset: startToken.charOffset },
    { runIndex: endToken.runIndex, charOffset: endToken.charOffset + 1 }
  );
}

/** Triple-click line / paragraph selection in normalized coordinates. */
export function selectLineOrParagraphAt(
  model: PageTextModel,
  nx: number,
  ny: number
): GeometricSelectionResult | null {
  const pos = hitTestPoint(model, nx, ny);
  if (!pos) return null;
  const anchorRun = model.runs[pos.runIndex];
  if (!anchorRun) return null;
  const colId = anchorRun.columnId;
  const colLines = model.lines.filter((l) => l.columnId === colId);
  const localIdx = colLines.findIndex((l) => l.lineIndex === anchorRun.lineIndex);
  if (localIdx < 0) return null;

  const lineHeights = colLines.map((l) => l.b - l.t);
  const medH = median(lineHeights, 0.015);
  const maxParaGap = medH * 0.9;

  let startLocal = localIdx;
  while (startLocal > 0) {
    const cur = colLines[startLocal];
    const prev = colLines[startLocal - 1];
    const gap = cur.t - prev.b;
    const hRatio = Math.max(cur.b - cur.t, prev.b - prev.t) / Math.max(1e-4, Math.min(cur.b - cur.t, prev.b - prev.t));
    if (gap > maxParaGap || hRatio > 1.35) break;
    startLocal--;
  }

  let endLocal = localIdx;
  while (endLocal + 1 < colLines.length) {
    const cur = colLines[endLocal];
    const next = colLines[endLocal + 1];
    const gap = next.t - cur.b;
    const hRatio = Math.max(cur.b - cur.t, next.b - next.t) / Math.max(1e-4, Math.min(cur.b - cur.t, next.b - next.t));
    if (gap > maxParaGap || hRatio > 1.35) break;
    endLocal++;
  }

  const firstLine = colLines[startLocal];
  const lastLine = colLines[endLocal];
  const firstRunIdx = firstLine.runIndices[0];
  const lastRunIdx = lastLine.runIndices[lastLine.runIndices.length - 1];
  const lastRun = model.runs[lastRunIdx];
  if (firstRunIdx === undefined || !lastRun) return null;

  return selectRange(
    model,
    { runIndex: firstRunIdx, charOffset: 0 },
    { runIndex: lastRunIdx, charOffset: lastRun.str.length }
  );
}
