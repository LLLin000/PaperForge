# VNext Cutover Corpus Map

**Date:** 2026-07-03
**Purpose:** Map the comparison corpus for OCR vnext cutover evaluation (spec §8.3).
**Total papers:** 5 (3 existing fixtures + 2 new)

## Coverage Summary

| Category | Paper(s) | Coverage |
|----------|----------|----------|
| same-page normal figure | 2HEUD5P9 | Strong |
| multi-panel same-row group | 2HEUD5P9 | Strong |
| sidecar legend page | 28JLIHLS | Strong |
| bundle-source page | DWQQK2YB | Moderate |
| locator-bridge page | DWQQK2YB | Moderate |
| dense composite parent page | 24YKLTHQ | Strong |
| classic sequential-only rescue page | YGH7VEX6 | Strong |
| unmatched asset / unresolved cluster page | 2HEUD5P9 | Strong |
| duplicated / continued legend page | DWQQK2YB | Moderate |

**Missing categories:** None — all 9 spec §8.3 categories are covered.

---

## Existing Fixtures (3 papers)

### 2HEUD5P9 — Same-page, multi-panel, unmatched assets

**Blocks:** 670 | **Pages:** 27 | **Source:** Vault (existing fixture)

**Categories covered:**
- **same-page normal figure** — Pages 3, 4, 9, 13, 15, 19, 21 all have `figure_caption` blocks with `figure_asset` blocks on the same page. PrimarySamePagePass is exercised on each.
- **multi-panel same-row group** — Page 4: 1 caption ("Figure 2") with 14 figure assets. Page 9: 1 caption ("Figure 3") with 15 figure assets. These are multi-panel figures where multiple asset blocks share one caption. The pipeline's distance clustering forms candidate groups that the same-page pass matches.
- **unmatched asset / unresolved cluster page** — 74 figure assets total vs 8 figure captions. Pages 21, 15, 13, and others have assets that greatly outnumber captions. After all matching passes, the residual assets remain as unresolved clusters for FinalAccountingPass and UnresolvedClusterConsolidation.

**Why chosen:** Largest existing fixture with richest figure layout — covers 3 spec categories.

---

### DWQQK2YB — Cross-page, locator bridge, bundle source, duplicated legend

**Blocks:** 273 | **Pages:** 41 | **Source:** Vault (existing fixture)

**Categories covered:**
- **cross-page layout** — Captions on pages 35-36 point to assets on pages 37-41. CrossPageReservationPass and CrossPageSettlementPass must bridge the gap.
- **locator-bridge page** — Caption text spans across the page boundary; the locator bridge pass connects figure captions on early pages to their visual groups on later pages. Pages 35-36 have caption candidates while corresponding assets appear on pages 37-41.
- **bundle-source page** — Page 35: 3 `figure_caption_candidate` blocks (Fig. 1-3) with 0 `figure_asset` blocks. This triggers the LegendBundlePass, which must match these 3 bundled captions to assets on subsequent pages.
- **duplicated / continued legend page** — Fig. 3 appears on both page 35 (as candidate) and page 40 (as candidate text). Fig. 4 appears on page 36 and page 41. This exercises the deduplication logic and tests that duplicated captions don't create spurious matches.

**Why chosen:** Only fixture exercising locator bridge, bundle source, and duplicated legend — coverage breadth.

---

### YGH7VEX6 — Classic sequential rescue

**Blocks:** 189 | **Pages:** 8 | **Source:** Vault (existing fixture)

**Categories covered:**
- **classic sequential-only rescue page** — 14 figure captions, but only 12 expected to match via same-page passes (per brief). The residual 2 unmatched captions fall through to ClassicSequentialPass, which matches them to forward-page assets in reading order. This exercises the fallback matching path.

**Why chosen:** Small (189 blocks, 8 pages) with dense caption-asset arrangement. The 2-gap pattern is the most compact regression test for classic sequential matching.

---

## New Fixtures (2 papers)

### 28JLIHLS — Sidecar legend page

**Blocks:** 161 | **Pages:** 7 | **Source:** Vault (new fixture)

**Categories covered:**
- **sidecar legend page** — Pages 3-4 each have 3 `figure_caption` blocks with widths ~488-491px (narrow on a 1200px page width) and 2-3 matching `figure_asset` blocks. The narrow caption width (< 600px) causes low same-page matching scores, making these captions candidates for the SidecarPass. The pass must match each narrow caption to its nearest asset band by y-alignment.

**Paper details:**
- Full title: "Galvanotaxis of chondrocytes"
- 7 figure captions total (Fig. 1-7), 6 figure assets
- Fig. 1 on page 2 (full width) — standard same-page match
- Fig. 2-4 on page 3 (narrow) — sidecar candidates
- Fig. 5-7 on page 4 (narrow) — sidecar candidates
- Remaining pages (5-7): references, footnotes, noise

**Why chosen:** Very small (161 blocks) with the cleanest sidecar pattern in the vault — multiple adjacent pages each with 3 narrow captions and matching assets.

---

### 24YKLTHQ — Dense composite parent page

**Blocks:** 182 | **Pages:** 13 | **Source:** Vault (new fixture)

**Categories covered:**
- **dense composite parent page** — Page 7: 1 `figure_caption` block ("Figure 5: Distribution of EFs in cartilage explant cultured in vitro") with 8 `figure_asset` blocks, 0 `body_paragraph` blocks. This dense arrangement of assets with a single caption exercises CompositeParentPass, which must detect the composite parent cluster and match it to the single caption.

**Paper details:**
- Full title: "Computational modelling of electric field distribution in cartilage"
- 9 figure captions, 16 figure assets
- Pages 3, 5, 6, 7, 8: caption+asset pages
- Page 7 is the primary dense composite target (8 assets clustered, 1 caption)
- Additional pages (4): 2 narrow "Source: own" caption candidates (sidecar-adjacent pattern, secondary)
- Remaining pages: references, noise, metadata

**Why chosen:** Small (182 blocks) with the clearest dense composite page in the vault — high asset density and zero body interference on page 7.

---

## Source Paths

All fixtures are copies of `blocks.structured.jsonl` from the OCR vault:

| Key | Vault Path |
|-----|-----------|
| 2HEUD5P9 | `D:/L/OB/Literature-hub/System/PaperForge/ocr/2HEUD5P9/structure/blocks.structured.jsonl` |
| DWQQK2YB | `D:/L/OB/Literature-hub/System/PaperForge/ocr/DWQQK2YB/structure/blocks.structured.jsonl` |
| YGH7VEX6 | `D:/L/OB/Literature-hub/System/PaperForge/ocr/YGH7VEX6/structure/blocks.structured.jsonl` |
| 28JLIHLS | `D:/L/OB/Literature-hub/System/PaperForge/ocr/28JLIHLS/structure/blocks.structured.jsonl` |
| 24YKLTHQ | `D:/L/OB/Literature-hub/System/PaperForge/ocr/24YKLTHQ/structure/blocks.structured.jsonl` |

## Notes

- One paper covers multiple categories where the layout naturally demonstrates more than one pattern (e.g., DWQQK2YB covers 4 categories).
- All 9 required categories from spec §8.3 are covered by at least one paper.
- Each category has at least "Moderate" coverage (verifiable from block role/page analysis).
- New fixtures were selected for small size (<200 blocks) and clear category signal.
- No text-matching was used in fixture selection — only structural signals (bbox width, role distribution, asset-to-caption ratio, page composition).
