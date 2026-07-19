# 28ALPCY7 — "Figure N" Lost-in-OCR Investigation

## Paper
- **Title**: 3D-Printed β-Tricalcium Phosphate Scaffold Combined with a Pulse Electromagnetic Field Promotes the Repair of Skull Defects in Rats
- **PDF**: Liang et al., 2019, ACS Biomaterials Science & Engineering
- **Pages**: 37 total

---

## Methodology

For each page containing figures/tables, we compared:
1. **PDF text layer** (PyMuPDF `page.get_text()`) — search for "Figure N"/"Table N" headings
2. **OCR role-index** (block_trace.csv from the PaperForge pipeline) — check for figure_caption/table_caption role

## Pages with Figures/Tables (source: figure_table_ownership_summary.json)

| Page | Content | PDF has heading? | OCR has caption block? | Status |
|------|---------|-----------------|----------------------|--------|
| 9 | Table 1 (primer sequences) | `Table 1.` | b5 table_caption | PRESERVED |
| 12 | Figure 1 (SEM images) | `Figure 1.` | b8 figure_caption | PRESERVED |
| 13 | Figure 2 (LIVE/DEAD staining) | `Figure 2.` | b10 figure_caption | PRESERVED |
| 15 | Figure 3 (CCK-8 analysis) | `Figure 3.` | b4 figure_caption | PRESERVED |
| 16 | Figure 4 (ALP activity) | `Figure 4.` | b4 figure_caption | PRESERVED |
| 17 | Figure 5 (ALP staining) | `Figure 5.` | b11 figure_caption | PRESERVED |
| 19 | Figure 6 charts (ALP/Runx2/OPN) | NO heading (charts only) | b4/b6/b8 fragment captions | Heading on page 20 |
| 20 | Figure 6 caption (qRT-PCR) | `Figure 6.` | b3 figure_caption | PRESERVED |
| 22 | Figure 7 (3D reconstruction) | `Figure 7.` | b4 figure_caption | PRESERVED |
| 23 | Figure 8 (BMD analysis) | `Figure 8.` | b5 figure_caption | PRESERVED |
| 27 | Figure 9 (HE staining) | `Figure 9.` | b5 figure_caption | PRESERVED |
| 36 | TOC graphic | `Table of Contents graphic` | b3 table_caption_candidate | PARTIAL |

---

## Key Finding: No "Figure N" headings are lost from PDF text layer

**All 10 numbered figure/table headings present in the PDF text layer are correctly captured in the OCR role-index.** There is zero cases where a "Figure N"/"Table N" string exists in the PDF text but is absent from OCR blocks.

## Related Issues Found

### 1. Figure 6 heading is on a different page than the figure assets
- The figure caption **"Figure 6. qRT-PCR analysis..."** is on **Page 20**
- But the actual figure chart images (ALP, Runx2, OPN expression) are on **Page 19**
- The figure_table_ownership incorrectly maps Figure 6 to "page": 19 (the legend_block_id=3 on page 19 is actually a body paragraph, not the caption)
- The three chart blocks on page 19 (b5=media_asset/chart, b7=media_asset/chart, b9=figure_asset/chart) have only fragmentary sub-panel labels ("ALP", "Runx2", "OPN") instead of the full Figure 6 heading

### 2. Pages 25-26: Full-page images with no text layer -> media_asset with no caption matching
- Pages 25 and 26 contain **full-page images** with NO text layer (only page numbers and journal header in PDF text)
- The OCR pipeline correctly identified these as `media_asset` blocks (6 total across pages 25, 26, 27, 36):
  - Page 25: b3, b4, b5, b6 = media_asset/image (4 blocks)
  - Page 26: b3, b4 = media_asset/image (2 blocks)
  - Page 27: b3 = media_asset/image (1 block)
- These are **NOT caption-matched** — they remain as unmatched/uncaptioned `media_asset` blocks
- The vision audit confirms these are real figures/charts that "should have caption"
- **Cause**: Captions are embedded within the image pixels, not as separate PDF text — the OCR pipeline cannot extract text from images

### 3. Page 17: Mixed media_asset + figure_asset blocks
- Page 17 has both `media_asset` (b3-b6, 4 image blocks) and `figure_asset` (b9-b10, 2 image blocks)
- The `media_asset` blocks have no figure_number assignment — they are uncaptioned
- The `figure_asset` blocks are matched with `figure_caption` block b11 (Figure 5)
- This suggests sub-panel images within Figure 5 are classified as media_asset, not figure_asset

### 4. Total uncaptioned figure assets
- **4 unmatched figure assets** across the paper
- **8 unmatched table assets** across the paper
- **2 unresolved figure clusters** (pages 17 and 19) where near-neighbor caption matching failed

---

## Summary

| Metric | Count |
|--------|-------|
| Numbered figure/table headings in PDF text | 10 |
| Figure/table headings correctly captured in OCR | 10 |
| **Figure N headings LOST in OCR** | **0** |
| Media_asset blocks (images without caption matching) | 18 |
| Pages with media_asset but NO caption on same page | 25, 26 |
| Unmatched figure assets | 4 |
| Unmatched table assets | 8 |

## Conclusion

**The "Figure N" lost-in-OCR problem does not affect paper 28ALPCY7 in the traditional sense.** All extractable figure/table headings from the PDF text layer are faithfully captured in the OCR role-index blocks. The images on pages 25-26 have their captions embedded within the image pixels (no separate text layer), so there is no "Figure N" text to lose — the OCR pipeline correctly classifies them as media_asset rather than figure_asset, but this means they remain uncaptioned in the structured output.
