# Q7 cross-page evidence: 28JLIHLS

## Scope and method

Read-only review of the source PDF (`Chondrocyte Translocation Response to Direct Current Electric Fields`, DOI 10.1115/1.429661), OCR raw/structured block inventories, and the PDF's full seven pages. The PDF page render overlays show OCR figure assets in red and captions in green; boxes are in source OCR coordinates (page size 1224 × 1584). The page images are rendered at 2×. All supplied PDF pages were searched for figure captions; no pipeline/evaluation code or vault content was changed.

Rendered pages: [p1](28JLIHLS/page_001_annotated.png), [p2](28JLIHLS/page_002_annotated.png), [p3](28JLIHLS/page_003_annotated.png), [p4](28JLIHLS/page_004_annotated.png), [p5](28JLIHLS/page_005_annotated.png), [p6](28JLIHLS/page_006_annotated.png), [p7](28JLIHLS/page_007_annotated.png). Asset crops: [p4/b0](28JLIHLS/page_004_block_00_asset_crop.png), [p4/b2](28JLIHLS/page_004_block_02_asset_crop.png), [p4/b6](28JLIHLS/page_004_block_06_asset_crop.png), [p4/b12](28JLIHLS/page_004_block_12_asset_crop.png).

## Figure 5 — associate left-column pair; block 6 is Figure 6

- Caption: p4/b3, bbox `[115,710,606,933]`.
- Owner set recommended: **p4/b0 + p4/b2** (both `chart` assets in the left column), confidence **high**.
- Bboxes: b0 `[123,70,598,352]`; b2 `[121,390,595,689]`. They are vertically stacked in the same column (center-x difference 2.5; vertical gap 38). Block 2 is immediately above the caption (center-x difference 2.5; gap 21); block 0 is the preceding panel in the same uninterrupted two-chart group. The caption explicitly describes panels (a) and (b), matching the two stacked bar charts. The rendered page shows both left charts immediately above the Fig. 5 caption.
- Block 6 is **assigned to Figure 6**, not Fig. 5, not shared, and not held. Visual proof: the p4/b6 asset `[622,68,1104,331]` is a pair of polar plots labeled `(a)` and `(b)`; Fig. 6 caption p4/b7 `[616,346,1106,479]` explicitly describes the two polar plots and sits directly below it (center-x difference 2; gap 15). It is in the right column, far from the Fig. 5 caption (horizontal center difference 502.5; vertical gap 379). The page render and b6 crop show this correspondence directly.
- Next action: **FIX** the association as Fig. 5 → `{p4/b0,p4/b2}` and Fig. 6 → `{p4/b6}`. Do not include b6 in Fig. 5.

## Figure 6 — one complete p4 asset observed; no p5 continuation

- Caption: p4/b7, bbox `[616,346,1106,479]`.
- Candidate asset: p4/b6, bbox `[622,68,1104,331]`; it contains both labeled polar plots `(a)` and `(b)` described by the caption. Caption/asset are same-column and separated by 15 OCR-coordinate units.
- Page 5 was checked visually and against its complete structured block inventory (p5/b0–b11). It contains no figure asset or figure-caption block; there is no p5 image/panel and therefore no p5 block ID or bbox to record. Pages 6–7 likewise show no figure assets.
- Expected complete asset set supported by the supplied PDF: **`{p4/b6}` only**. The existing manual note claiming a p4→p5 continuation is not supported by the source page render or block inventory; no cross-page merge should be inferred from that note alone. Confidence **high** for the single-page asset set.
- Next action: **FIX** association with p4/b6 only; do not append a p5 asset. If an external version is alleged to contain a continuation, its PDF/source page is missing and must be supplied before revising this result.

## Figure 9 — HOLD: insufficient visual evidence

No Fig. 9 caption was found in either the raw or structured blocks, or in the extracted text of any page in the supplied seven-page PDF. The asset inventory contains figure assets only on PDF pages 2–4; the rendered pages 5–7 contain text/references and no figure image. The supplied PDF presents figure captions numbered 1–7, with no Fig. 9 anchor.

**HOLD: insufficient visual evidence.** Missing: a source/page containing a Fig. 9 caption or image, and its asset/page block IDs and bboxes. The assertion that Figure 9 spans multiple pages cannot be mapped to this source, so no owner set or merge is proposed. Confidence **high** that this supplied PDF has no identifiable Fig. 9; confidence in any alleged external Figure 9 ownership is **none**.

## Structured evidence

Machine-readable page, caption, asset, bbox, adjacency, ownership-candidate, confidence, and next-action records are in [`evidence.json`](evidence.json). No ownership merge was implemented.
