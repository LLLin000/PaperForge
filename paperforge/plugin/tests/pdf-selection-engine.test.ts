import { describe, it, expect } from "vitest";
import {
  buildPageTextModel,
  hitTestPoint,
  selectRange,
  selectWordAt,
  selectLineOrParagraphAt,
  type PdfTextContentLike,
  type PdfViewportLike,
} from "../src/views/pdf-selection-engine";

const BASE_VP: PdfViewportLike = {
  width: 600,
  height: 800,
  transform: [1, 0, 0, -1, 0, 800],
};

function makeItem(
  str: string,
  x: number,
  yTopDown: number,
  width: number,
  fontH = 12
) {
  // Convert top-down Y (0..800) to PDF bottom-up baseline Y for transform [1,0,0,-1,0,800]
  const baselinePdfY = 800 - yTopDown;
  return {
    str,
    transform: [1, 0, 0, fontH, x, baselinePdfY],
    width,
    height: fontH,
  };
}

describe("pdf-selection-engine (Option B geometric engine)", () => {
  it("detects two-column XY-cut layout with full-width title and sorts reading order without column jumping", () => {
    const tc: PdfTextContentLike = {
      items: [
        // Full-width title spanning across center gutter (x=60..540)
        makeItem("Deep Learning for Knee MRI Segmentation", 60, 60, 480, 18),
        // Interleaved PDF stream order: Left Col Line 1, Right Col Line 1, Left Col Line 2, Right Col Line 2
        makeItem("Left column first line", 50, 140, 200, 12),
        makeItem("Right column first line", 340, 140, 200, 12),
        makeItem("Left column second line", 50, 162, 200, 12),
        makeItem("Right column second line", 340, 162, 200, 12),
        makeItem("Left column third line", 50, 184, 200, 12),
        makeItem("Right column third line", 340, 184, 200, 12),
      ],
    };

    const model = buildPageTextModel(tc, BASE_VP);
    expect(model.lines).toHaveLength(7);

    // Title first, then all Left column lines, then all Right column lines
    const orderedText = model.runs.map((r) => r.str);
    expect(orderedText).toEqual([
      "Deep Learning for Knee MRI Segmentation",
      "Left column first line",
      "Left column second line",
      "Left column third line",
      "Right column first line",
      "Right column second line",
      "Right column third line",
    ]);

    // Dragging inside Left column even when cursor drifts into center gutter (nx=0.49) stays in Left column!
    const anchor = hitTestPoint(model, 55 / 600, 138 / 800)!;
    expect(anchor).not.toBeNull();
    const anchorCol = model.runs[anchor.runIndex].columnId;
    const focus = hitTestPoint(model, 295 / 600, 182 / 800, anchorCol)!;
    const sel = selectRange(model, anchor, focus);
    expect(sel.exactText).toContain("Left column first line");
    expect(sel.exactText).toContain("Left column third line");
    expect(sel.exactText).not.toContain("Right column");
    expect(sel.rects).toHaveLength(3);
  });

  it("handles full-width spanning figure caption between two-column sections via recursive XY-cut", () => {
    const tc: PdfTextContentLike = {
      items: [
        makeItem("Col1 top A", 50, 100, 180, 12),
        makeItem("Col2 top B", 350, 100, 180, 12),
        makeItem("Col1 top C", 50, 120, 180, 12),
        makeItem("Col2 top D", 350, 120, 180, 12),
        makeItem(
          "Figure 1. Full width spanning caption across both columns.",
          60,
          200,
          480,
          11
        ),
        makeItem("Col1 bot E", 50, 260, 180, 12),
        makeItem("Col2 bot F", 350, 260, 180, 12),
        makeItem("Col1 bot G", 50, 280, 180, 12),
        makeItem("Col2 bot H", 350, 280, 180, 12),
      ],
    };

    const model = buildPageTextModel(tc, BASE_VP);
    expect(model.runs.map((r) => r.str)).toEqual([
      "Col1 top A",
      "Col1 top C",
      "Col2 top B",
      "Col2 top D",
      "Figure 1. Full width spanning caption across both columns.",
      "Col1 bot E",
      "Col1 bot G",
      "Col2 bot F",
      "Col2 bot H",
    ]);
  });

  it("computes tight horizontal glyph bounds from item.width without overhang", () => {
    const tc: PdfTextContentLike = {
      items: [
        {
          str: "Precision",
          transform: [1, 0, 0, 12, 100, 700],
          width: 60, // exact 60px advance width at scale 1
          height: 12,
        },
      ],
    };
    const model = buildPageTextModel(tc, BASE_VP);
    expect(model.runs).toHaveLength(1);
    const run = model.runs[0];
    expect(run.l).toBeCloseTo(100 / 600, 5);
    expect(run.r).toBeCloseTo(160 / 600, 5);

    // Selecting full item yields exact normalized box matching item.width
    const sel = selectRange(
      model,
      { runIndex: 0, charOffset: 0 },
      { runIndex: 0, charOffset: "Precision".length }
    );
    expect(sel.exactText).toBe("Precision");
    expect(sel.rects[0][0]).toBeCloseTo(100 / 600, 5);
    expect(sel.rects[0][2]).toBeCloseTo(160 / 600, 5);

    // Sub-range selection inside item stays strictly inside [l, r]
    const sub = selectRange(
      model,
      { runIndex: 0, charOffset: 0 },
      { runIndex: 0, charOffset: 4 }
    );
    expect(sub.exactText).toBe("Prec");
    expect(sub.rects[0][2]).toBeLessThan(run.r);
    expect(sub.rects[0][2]).toBeGreaterThan(run.l);
  });

  it("supports double-click word selection and triple-click paragraph selection", () => {
    const tc: PdfTextContentLike = {
      items: [
        // Paragraph 1 (lines at y=100, 118)
        makeItem("Hello", 60, 100, 40, 12),
        makeItem("radiomics", 108, 100, 72, 12),
        makeItem("world.", 186, 100, 45, 12),
        makeItem("Second line of para one.", 60, 118, 180, 12),
        // Paragraph 2 after gap (y=170)
        makeItem("Separate second paragraph.", 60, 170, 190, 12),
      ],
    };

    const model = buildPageTextModel(tc, BASE_VP);

    // Double-click inside "radiomics"
    const wordSel = selectWordAt(model, 130 / 600, 96 / 800);
    expect(wordSel).not.toBeNull();
    expect(wordSel!.exactText).toBe("radiomics");
    expect(wordSel!.rects).toHaveLength(1);
    expect(wordSel!.rects[0][0]).toBeCloseTo(108 / 600, 4);
    expect(wordSel!.rects[0][2]).toBeCloseTo(180 / 600, 4);

    // Triple-click on line 1 selects Paragraph 1 (both lines), stopping before Paragraph 2
    const paraSel = selectLineOrParagraphAt(model, 130 / 600, 96 / 800);
    expect(paraSel).not.toBeNull();
    expect(paraSel!.exactText).toBe(
      "Hello radiomics world.\nSecond line of para one."
    );
    expect(paraSel!.rects).toHaveLength(2);
  });

  it("joins hyphenated line-wraps cleanly on selection copy and keeps single-column layouts intact", () => {
    const tc: PdfTextContentLike = {
      items: [
        makeItem("This   method uses a", 60, 100, 400, 12),
        makeItem("hyper-", 60, 120, 40, 12),
        makeItem("parameterized model.", 60, 140, 150, 12),
      ],
    };
    const model = buildPageTextModel(tc, BASE_VP);
    const sel = selectRange(
      model,
      { runIndex: 1, charOffset: 0 },
      { runIndex: 2, charOffset: "parameterized model.".length }
    );
    expect(sel.exactText).toBe("hyperparameterized model.");
    expect(model.runs.every((r) => r.columnId === 0)).toBe(true);
  });
});
