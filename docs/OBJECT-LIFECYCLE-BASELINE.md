# Figure/Table Lifecycle Baseline (2026-11-08)

This document freezes the measurement baseline for E0. Two datasets are kept
separate and must not be compared directly:

- **Historical snapshot**: 952 papers as produced before #376–#378 (only for
  regression accounting; the vault has not been rebuilt).
- **Current chain**: read-only replay of the merged code on the 40-paper corpus.

## Historical snapshot (952 papers, pre-#376 artifacts)

| Metric | Value |
|---|---:|
| Papers / figures / tables | 952 / 5,697 / 1,766 |
| Papers with duplicate figure ids | 181 |
| Figure entries sharing an existing id | 355 |
| Papers with fewer figure embeds than entries | 272 |
| Orphan markdown files (892 papers) | 16,953 |
| Orphan markdown embedded in fulltext | 0 |
| Figures without assets (`figure_reserved_*`) | 418 |
| Figures without a parsed number | 447 |
| Tables without an asset | 293 (16.6%) |
| Tables with `assistive_text` HTML | 1,432 (81%) |
| Tables with notes | 121 (6.9%) |
| Continuation tables | 146 |
| Unmatched assets | 1,519 |
| ... of which ≥5% page area | 460 |
| `caption_without_media` (health) | 563 |
| `empty_table` (health) | 293 |
| `ambiguous_table_match` (health) | 215 |

Delivery caveat: "5,697 render md files" is not independent evidence of
completeness — duplicate ids overwrite the same path. Orphans are cropped but
never embedded.

## Current chain (40-paper corpus, merged code)

| Metric | Value |
|---|---:|
| First-parse vs rebuild two-entry parity | 40/40 identical (rows, claims, resolutions, conflicts, markdown, assets) |
| Unmatched assets | 66 |
| ... of which ≥5% page area | 21 |
| Large unmatched: caption only on next page | 9 |
| Large unmatched: caption text on same page | 7 |
| Large unmatched: no caption at all | 5 |
| Side-by-side caption miss (verified) | 1 (`2AZ2EGQB` p9) |
| `figure_inner_text` rows / with owner | 270 / 1 |
| Inventory claims / unsafe (contested) | 978 / 1 |
| Post-match role corrections | 13 in 8 papers |
| Render changes from those corrections | 0 (byte-identical) |

## Visual proxy (20 complex papers, 580 pages, no ML)

PDF graphics (image XObjects + vector clusters) vs current inventory:

| Metric | Value |
|---|---:|
| Visual figure boxes without inventory support | 283 (183 drawing clusters, 100 images) |
| ... of which ≥5% page area | 115 (78 pages) |
| Inventory figure boxes without visual support | 62 (50 unmatched assets) |
| ... of which ≥5% page area | 16 |

The PDF-graphics proxy over-detects decorations, flowcharts and rules; treat 283
as an upper bound until a reference set or a detector separates real figures.
`visual_detection_benchmark.py` (untracked, read-only) produced these numbers.

## Review of the known failures

| Case | Status | Evidence |
|---|---|---|
| `SRNJDAA2` | identity collision (E1) | 25 entries, 1 unique id, 1 render md |
| `DJLIAZT7` | identity collision (E1) | 63 entries across 4 ids |
| `388XI46Q` p14–15 | association miss (E2) | figure image on p14, `Fig. 5` caption at p15 top, no figure match |
| `2AZ2EGQB` p9 | association miss (E2) | caption left of asset, same row, no x-overlap rule |
| `2BYRLKQS` p4 | fixed in #377 | table asset = block 3, figure 1 = block 8, crop verified |
| `28ALPCY7` p20 | genuine assetless figure | `figure_reserved_009`; do not fabricate an asset |
| `2HEUD5P9` | protected | ownership guard; panel crop preserved labels visually |
| `2ZBAK9VY` | fixed in #376 | supplement PDF 8 pages vs 12 OCR pages, cache fallback restores crop |

## Metrics every PR must report

Canonical identity collisions; association accuracy on the reviewed cases; orphan
class counts; crop/render/fulltext delivery completeness; ownership conflicts;
body-swallow and duplicate-output regressions; first-parse/rebuild parity.
