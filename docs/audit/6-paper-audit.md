# OCR Truth Audit — 6-Paper Full Audit

**Date:** 2026-07-05
**Auditor:** Automated pipeline analysis + visual verification

---

## Summary

| Paper | Status | Fig Matched | Fig Captions | Unmatched | Issue Category |
|-------|--------|-------------|--------------|-----------|----------------|
| SKXTCE6M | 🟡 Yellow | 14/17 | 17 | 6 | Table→figure routing |
| SRNJDAA2 | 🟡 Yellow | 23/32 | 32 | 9 | Body text → legend false positive |
| 3FDT9652 | 🟡 Yellow | 6/8 | 8 | 1 | Caption→asset matching gap |
| 6QNRHRKX | 🟡 Yellow | 0/7 | 7 | 7 | Figure detection failure |
| SWDN9RHF | 🔴 Red | 1/1 | 1 | 0 | Structural: no abstract |
| SAN9AYVR | 🟢 Green | 31/34 | 34 | 0 | Clean (34 orphans normal) |

---

## 1. SKXTCE6M — Table→Figure Routing ⚠️

**Paper:** Hashemi-Afzal et al., 2025 — *Advancements in hydrogel design for articular cartilage*

**Finding:** 6 table titles classified as `figure_caption_candidate` because `raw_label=figure_title` was assigned by OCR to bold/centered text above HTML `<table>` blocks. The descriptive text ("A summary of hydrogels...") becomes unmatched legend, disappears from rendered fulltext.

**Output impact:** 6 blocks of descriptive table content LOST from markdown. 4 tables rendered as images instead of HTML on pages 11/15/19/23 due to `media_asset` role.

**Root cause:** Raw label `figure_title` doesn't distinguish tables from figures. Adjacency check to `<table>` block missing.

**Fix:** In role classification: if `raw_label=figure_title` and next sibling is `table_html` or `media_asset` → assign `table_caption`.

---

## 2. SRNJDAA2 — Body Text → Legend False Positive ⚠️

**Paper:** (Book chapter on piezoelectric biomaterials, ~1970s)

**Finding:** 9 unmatched legends, all `role=body_paragraph`. They contain "Figure 11-10 shows the x-ray picture..." — inline references to figures in the running text. The pipeline picks up any block starting with "Figure X-Y " as a potential figure legend, even when it's clearly body text.

**Output impact:** MINIMAL. Text is correctly rendered as body paragraphs. The false positives only inflate `unmatched_legends` count, yellowing the health status.

**Root cause:** Legend detection is too aggressive. "Figure N-M shows..." should be distinguished from "Figure N-M. (caption)".

**Fix:** Filter `body_paragraph` blocks from legend candidates. If a block's role (after classification) is `body_paragraph`, it cannot simultaneously be a figure legend.

---

## 3. 6QNRHRKX — Complete Figure Detection Failure 🔴

**Paper:** Weiner & Macnab, 1970 — *Superior Migration of the Humeral Head* (radiology)

**Finding:** 7 figure captions (Fig. 2 through Fig. 7) identified but ZERO figure assets matched. Captions are very short ("Fig. 2" through "Fig. 7") — just labels, no descriptive text. Figures appear to be embedded in two-column text layout. Orphans are sub-panels (~12KB each) that couldn't be matched.

**Output impact:** SEVERE. Figures appear in markdown as bare `> Fig. 2` blockquotes with no image. One descriptive caption text lost entirely.

**Root cause:** Short label-only captions lack the text overlap that the matching algorithm uses to pair captions with figure regions. Possibly combined with figures not detected as image regions by page layout analysis.

**Fix:** Needs investigation of the actual PDF layout — short captions in radiology papers may need a different matching heuristic.

---

## 4. 3FDT9652 — Single Caption Gap ⚠️

**Paper:** (Rotator cuff / shoulder tendon paper)

**Finding:** 6/8 figures matched. One unmatched legend: "A, Full-thickness tear of supraspinatus tendon..." — this is a partial caption starting with a sub-panel label. 2 orphans exist.

**Output impact:** 1 figure caption lost from rendered output.

---

## 5. SWDN9RHF — Structural Red, Figure Quality Good ✅

**Paper:** Roemer et al. — *MRI-based semiquantitative assessment of subchondral bone marrow lesions*

**Finding:** RED status is structural (`abstract_found: False`, `structural_blockers: 2`), not OCR quality. The single figure (Fig. 1) is correctly matched and cropped. The paper has no abstract section in the traditional sense.

**Output impact:** None for figure matching. Red status is a false alarm driven by paper formatting.

---

## 6. SAN9AYVR — Green but High Orphan Count ✅

**Paper:** (Large review, 81 pages, 31 matched figures)

**Finding:** All 31 figures correctly matched. 34 orphans exist but are tiny (2-7KB) — likely small icons, section dividers, plot markers. This is normal behavior for a 81-page paper with dense graphics.

**Output impact:** None.

---

## Categorized Findings

### By Fixability

| Priority | Finding | Effort | Impact |
|----------|---------|--------|--------|
| P0 | Table→figure routing (SKXTCE6M style) | ~5 lines + test | 6 lost content blocks per affected paper |
| P0 | Body text → legend false positive (SRNJDAA2 style) | ~3 lines + test | Noisy health status |
| P1 | Short caption matching (6QNRHRKX style) | Needs layout research | Severe for affected papers |
| P2 | Structural red for no-abstract papers (SWDN9RHF) | ~2 lines | Wrong health signal |

### Cross-cutting Theme

**The health status (yellow/red) is not a reliable indicator of figure matching quality.** Three different mechanisms can trigger yellow:
1. Table→figure routing (real content loss) ← **SKXTCE6M**
2. Body text→legend false positives (noise only) ← **SRNJDAA2**
3. Unmatched legends from detection gaps (real) ← **6QNRHRKX**

Without quality indicators (`build_quality_indicators`) the health report conflates these into one undifferentiated "yellow".
