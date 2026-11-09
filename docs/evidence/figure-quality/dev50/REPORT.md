# Dev 50 figure-quality diagnosis

## Scope and method

- Read-only `figure_quality_eval.py --set dev` replay over the frozen 50 keys; no vault writes. Replay output: 50 papers, 254 matched figure records; harness reports 50 passed / 0 failed (structural gate only, not a visual-quality pass).
- Retained one `baseline.json` per key plus `result.json`; large replay image sets remain in `.work/dev50` and are not included.
- Layer buckets overlap and are screening signals, not defect adjudications. Caption candidates and multi-page unmatched candidate spread do not establish a defect or a cross-page claim.
- Delivery is split: `current_on_disk_backlog` records missing pre-migration artifacts; `replay_delivery` checks planned replay outputs against the dry-run manifest plus retained files and fulltext embeds. Only replay gaps count as delivery defects.

## Bucket counts

| Bucket | Papers with signal | Definition / caveat |
|---|---:|---|
| caption_recall | 16 | Unmatched legends and/or caption-candidate rows. |
| association | 32 | Unmatched assets, identity claim changes, repeated figure IDs, or same-page multi-owner assets. |
| crop_panel | 21 | Near-edge unmatched assets, panel-text proxy with one asset, or groups of ≥4 assets. |
| page_assembly | 10 | Asset/caption page mismatch, cross-page match, or unmatched candidates/assets spanning multiple pages. |
| delivery | 0 | Replay manifest gap: missing figure asset/render or inconsistent fulltext embed. |
| structural | 1 | Text decrease, pending marker, or table claim change. |
| no_defect | 11 | No screening signal in above layers; not individually adjudicated. |

## Layered totals

| Signal | Items | Papers |
|---|---:|---:|
| Unmatched legends | 17 | 11 |
| Caption-candidate rows | 34 | 16 |
| Figure claims | 254 | 45 |
| Unmatched assets | 54 | 30 |
| Figure-claim changes (dry-run) | 10 | 7 |
| Near-edge assets (≤3% page edge) | 0 | 0 |
| Panel-text proxy + single asset | 6 | 4 |
| Large multi-asset groups (≥4) | 49 | 19 |
| Unmatched candidate pages | 48 | 34 |
| Cross-page matched claims | 0 | 0 |
| Asset/caption page mismatches | 0 | 0 |
| Current on-disk missing asset files (pre-migration backlog) | 174 | 34 |
| Current on-disk missing render markdown | 0 | 0 |
| Current dangling fulltext embeds | 0 | 0 |
| Replay-missing figure assets | 0 | 0 |
| Replay-missing render markdown | 0 | 0 |
| Replay-dangling fulltext embeds | 0 | 0 |
| Replay embeds missing target IDs | 0 | 0 |
| Text-decrease papers | 0 | 0 |
| Pending markers | 0 | 0 |
| Table claim changes | 1 | 1 |

Figure IDs repeat in 6 papers (6 extra entries); same-page asset block is claimed by multiple figures in 1 paper(s). Repeated owner: R8PCX2YL p2/block7×2. The sampled 6A8A9TWD duplicate ID is a separate, visually confirmed wrong association.

**Pre-migration backlog, not replay defects:** 174 non-reserved matched-figure asset files are absent under current `assets/figures/` in 34 papers. The replay manifest supplies every matched figure asset and render; all checked fulltext embeds resolve after replay. Current render markdown and embed targets are present. `figure_reserved_*` entries are excluded from asset file checks.

## Visual sample

Reviewed 30 replay-rendered figure crops/captions across 10 papers (3 per paper), stratified across association/crop/page/caption/structural flags and pre-migration backlog, with a no-signal control. Sheets: [`sheet_1.jpg`](sample_sheets/sheet_1.jpg), [`sheet_2.jpg`](sample_sheets/sheet_2.jpg), [`sheet_3.jpg`](sample_sheets/sheet_3.jpg). The manifest records the exact IDs, asset blocks, root-cause category and notes; 224 other figure records remain unreviewed.

| Root-cause category | Cases |
|---|---:|
| caption recall | 0 |
| grouping/association | 2 |
| crop boundary | 0 |
| panel split/merge | 0 |
| cross-page assembly | 0 |
| delivery | 0 |
| no-defect | 28 |

The only visually confirmed replay defect is 6A8A9TWD: two `figure_s002` entries under the same legend claim two different page-2 assets; one is the preceding Figure 1 illustration, not Figure 2. Nine sampled figures lacked a current pre-migration asset file, but replay supplies their assets/renders, so they are labeled no-defect rather than delivery failures. No caption-recall, crop-boundary, panel split/merge, cross-page, or replay-delivery defect was visually confirmed.

## Per-paper evidence

Counts below are screening signals. Caption = unmatched legends / candidate rows; crop = near-edge / single-asset panel proxy / ≥4 assets; page = unmatched candidate pages / cross-page claims / caption-page mismatches; current backlog = missing asset files; replay gaps = missing asset / render / embed; structural = text decrease / pending markers / table-claim changes.

| Key | Figs | Caption U/C | Orphans | Claim changes | Duplicate IDs | Crop E/P/L | Page P/X/M | Current backlog A | Replay gaps A/R/E | Structural T/P/Table | Buckets |
|---|---:|---:|---:|---:|---|---|---|---:|---|---|---|
| 3CEUN7T3 | 0 | 0/0 | 1 | 0 | — | 0/0/0 | 1/0/0 | 0 | 0/0/0 | 0/0/0 | association |
| 3FQYMMXS | 10 | 0/0 | 8 | 0 | — | 0/2/3 | 2/0/0 | 0 | 0/0/0 | 0/0/0 | association, crop_panel, page_assembly |
| 47QRWGM4 | 6 | 0/0 | 1 | 0 | — | 0/0/0 | 1/0/0 | 0 | 0/0/0 | 0/0/0 | association |
| 4CML4K3Y | 8 | 1/2 | 2 | 0 | — | 0/0/0 | 3/0/0 | 0 | 0/0/0 | 0/0/0 | caption_recall, association, page_assembly |
| 53B47JM8 | 4 | 5/7 | 6 | 0 | — | 0/0/3 | 3/0/0 | 0 | 0/0/0 | 0/0/0 | caption_recall, association, crop_panel, page_assembly |
| 5MAW65YD | 5 | 0/0 | 0 | 0 | — | 0/0/0 | 0/0/0 | 0 | 0/0/0 | 0/0/0 | no_defect |
| 5SF5MQJN | 1 | 0/0 | 0 | 0 | — | 0/0/0 | 0/0/0 | 0 | 0/0/0 | 0/0/0 | no_defect |
| 64GDU2A7 | 6 | 1/2 | 1 | 0 | — | 0/0/0 | 2/0/0 | 0 | 0/0/0 | 0/0/0 | caption_recall, association, crop_panel, page_assembly |
| 6A8A9TWD | 5 | 0/0 | 1 | 2 | figure_s002×2 | 0/0/0 | 1/0/0 | 0 | 0/0/0 | 0/0/0 | association |
| 6X2YRE3V | 4 | 0/0 | 1 | 0 | — | 0/0/0 | 1/0/0 | 0 | 0/0/0 | 0/0/0 | association |
| 7VPDXE48 | 6 | 0/0 | 1 | 1 | figure_002×2 | 0/0/2 | 1/0/0 | 5 | 0/0/0 | 0/0/0 | association, crop_panel |
| 832486Q6 | 10 | 0/0 | 0 | 0 | — | 0/0/0 | 0/0/0 | 0 | 0/0/0 | 0/0/0 | no_defect |
| 8S9LCPAE | 4 | 2/4 | 1 | 0 | — | 0/0/0 | 2/0/0 | 4 | 0/0/0 | 0/0/0 | caption_recall, association, crop_panel, page_assembly |
| 8V5A2XIY | 6 | 0/1 | 0 | 0 | — | 0/0/0 | 0/0/0 | 4 | 0/0/0 | 0/0/0 | caption_recall |
| 9EQV3ABQ | 6 | 0/0 | 0 | 0 | — | 0/0/1 | 0/0/0 | 5 | 0/0/0 | 0/0/0 | crop_panel |
| ACVQ5LA3 | 6 | 0/1 | 1 | 0 | — | 0/0/1 | 1/0/0 | 5 | 0/0/0 | 0/0/0 | caption_recall, association, crop_panel |
| CQAXQN4D | 4 | 0/0 | 0 | 0 | — | 0/0/0 | 0/0/0 | 4 | 0/0/0 | 0/0/0 | no_defect |
| CUSL5CU2 | 2 | 0/0 | 1 | 0 | — | 0/0/0 | 1/0/0 | 2 | 0/0/0 | 0/0/0 | association |
| DS2FR5FU | 4 | 0/0 | 1 | 0 | — | 0/0/0 | 1/0/0 | 4 | 0/0/0 | 0/0/0 | association |
| ECUA27Y2 | 10 | 0/0 | 1 | 1 | figure_009×2 | 0/1/3 | 1/0/0 | 9 | 0/0/0 | 0/0/0 | association, crop_panel |
| EGY463YC | 2 | 0/0 | 0 | 0 | — | 0/0/0 | 0/0/0 | 2 | 0/0/0 | 0/0/0 | no_defect |
| FCQ7M8U5 | 2 | 0/0 | 0 | 0 | — | 0/0/0 | 0/0/0 | 2 | 0/0/0 | 0/0/0 | no_defect |
| G2IVU22F | 5 | 0/0 | 1 | 0 | — | 0/0/0 | 1/0/0 | 5 | 0/0/0 | 0/0/0 | association |
| G46XM9U7 | 2 | 0/0 | 0 | 0 | — | 0/0/1 | 0/0/0 | 2 | 0/0/0 | 0/0/0 | crop_panel |
| G4C9BVPI | 0 | 1/1 | 0 | 0 | — | 0/0/0 | 1/0/0 | 0 | 0/0/0 | 0/0/0 | caption_recall |
| HL2FUMPM | 1 | 0/0 | 0 | 0 | — | 0/0/0 | 0/0/0 | 1 | 0/0/0 | 0/0/0 | no_defect |
| IN8LEK6F | 14 | 0/0 | 3 | 1 | — | 0/0/1 | 2/0/0 | 14 | 0/0/0 | 0/0/0 | association, crop_panel, page_assembly |
| IVQAQ8IQ | 3 | 0/0 | 0 | 0 | — | 0/0/1 | 0/0/0 | 3 | 0/0/0 | 0/0/0 | crop_panel |
| JC5AM3YP | 7 | 1/2 | 3 | 0 | — | 0/0/3 | 3/0/0 | 6 | 0/0/0 | 0/0/0 | caption_recall, association, crop_panel, page_assembly |
| JCXZNJJC | 1 | 1/1 | 1 | 0 | — | 0/0/0 | 2/0/0 | 1 | 0/0/0 | 0/0/0 | caption_recall, association, page_assembly |
| KG7A5K5V | 5 | 1/1 | 0 | 0 | — | 0/0/0 | 1/0/0 | 4 | 0/0/0 | 0/0/1 | caption_recall, structural |
| M8BNQFIV | 6 | 0/0 | 6 | 3 | — | 0/0/4 | 1/0/0 | 6 | 0/0/0 | 0/0/0 | association, crop_panel |
| M9M2RRDA | 4 | 0/0 | 1 | 0 | — | 0/0/2 | 1/0/0 | 4 | 0/0/0 | 0/0/0 | association, crop_panel |
| MSSWFUKJ | 1 | 0/0 | 0 | 0 | — | 0/0/0 | 0/0/0 | 1 | 0/0/0 | 0/0/0 | no_defect |
| QJAKWMHE | 0 | 0/0 | 0 | 0 | — | 0/0/0 | 0/0/0 | 0 | 0/0/0 | 0/0/0 | no_defect |
| R8PCX2YL | 3 | 1/1 | 0 | 0 | figure_003×2 | 0/0/0 | 1/0/0 | 2 | 0/0/0 | 0/0/0 | caption_recall, association |
| RSGLUYHK | 8 | 0/0 | 1 | 0 | — | 0/0/6 | 1/0/0 | 8 | 0/0/0 | 0/0/0 | association, crop_panel |
| SKXTCE6M | 17 | 0/2 | 1 | 0 | — | 0/0/2 | 1/0/0 | 14 | 0/0/0 | 0/0/0 | caption_recall, association, crop_panel |
| TW2333LF | 6 | 0/0 | 1 | 0 | — | 0/0/2 | 1/0/0 | 6 | 0/0/0 | 0/0/0 | association, crop_panel |
| U746UJ7G | 0 | 0/1 | 2 | 0 | — | 0/0/0 | 2/0/0 | 0 | 0/0/0 | 0/0/0 | caption_recall, association, page_assembly |
| VK2XSGFY | 3 | 2/2 | 1 | 0 | — | 0/0/0 | 3/0/0 | 0 | 0/0/0 | 0/0/0 | caption_recall, association, page_assembly |
| VVIT8SVK | 5 | 0/0 | 1 | 0 | — | 0/0/0 | 1/0/0 | 5 | 0/0/0 | 0/0/0 | association |
| VY8CRKCE | 10 | 0/2 | 1 | 0 | — | 0/0/4 | 1/0/0 | 8 | 0/0/0 | 0/0/0 | caption_recall, association, crop_panel |
| WDV72ZFQ | 6 | 0/0 | 0 | 1 | figure_002×2 | 0/0/1 | 0/0/0 | 5 | 0/0/0 | 0/0/0 | association, crop_panel |
| WDY4IMJB | 2 | 1/4 | 0 | 0 | — | 0/0/0 | 1/0/0 | 2 | 0/0/0 | 0/0/0 | caption_recall |
| WRP8UIHR | 1 | 0/0 | 0 | 0 | — | 0/0/0 | 0/0/0 | 1 | 0/0/0 | 0/0/0 | no_defect |
| WVB9LEFM | 15 | 0/0 | 1 | 1 | figure_005×2 | 0/1/8 | 1/0/0 | 12 | 0/0/0 | 0/0/0 | association, crop_panel |
| XVGX9U4V | 14 | 0/0 | 1 | 0 | — | 0/2/1 | 1/0/0 | 14 | 0/0/0 | 0/0/0 | association, crop_panel |
| YX8VL7DF | 0 | 0/0 | 0 | 0 | — | 0/0/0 | 0/0/0 | 0 | 0/0/0 | 0/0/0 | no_defect |
| ZLSXVG2Y | 4 | 0/0 | 2 | 0 | — | 0/0/0 | 1/0/0 | 4 | 0/0/0 | 0/0/0 | association |

## Q11 recommendation

**Proceed narrowly on duplicate figure-ID / competing-asset claims:** six papers contain repeated figure IDs, and the 6A8A9TWD case is visually proven to assign a Figure 1 asset to Figure 2. Review the remaining duplicate-ID cases before generalizing a fix; R8PCX2YL also has a same-page multi-owner asset signal. **No replay delivery repair is indicated:** the 174 missing pre-migration asset files are supplied by replay, with zero missing replay assets/renders/embed targets.

**HOLD** caption-recall flags, unmatched assets, crop/panel proxies, large asset groups, page-spread candidates, and the lone table claim change: none was visually confirmed as a replay defect in this sample. Text decrease, pending markers, cross-page claims, page mismatches, and replay-delivery gaps were absent.

## Artifacts

- `diagnostics.json`: layered per-paper fields, current backlog separately from replay delivery, figure claims/assets, and review states.
- `result.json` and `<KEY>/baseline.json`: frozen replay and per-paper baseline evidence.
- `sample_sheets/`: three compact sheets and the exact 30-case review manifest.
