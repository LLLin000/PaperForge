# OCR High Risk Rule Audit

## Production OCR Chain

`paperforge/worker/ocr.py` is the production orchestrator. The production artifact chain is:

`result.json -> blocks.raw.jsonl -> blocks.structured.jsonl -> document_structure.json -> figure_inventory.json/table_inventory.json -> objects -> render/fulltext.md -> health/ocr_health.json`

Production modules:

- `paperforge/worker/ocr_blocks.py`
- `paperforge/worker/ocr_roles.py`
- `paperforge/worker/ocr_document.py`
- `paperforge/worker/ocr_figures.py`
- `paperforge/worker/ocr_tables.py`
- `paperforge/worker/ocr_objects.py`
- `paperforge/worker/ocr_render.py`
- `paperforge/worker/ocr_health.py`

## Direct Role Mutations

| File | Symbol | Rule | Current Risk | Remediation |
| --- | --- | --- | --- | --- |
| `ocr_document.py` | `_build_region_prepass` | `_in_visual_container` can classify a block as `structured_insert` with confidence `0.85`. | Visual container is treated as a conclusion instead of evidence. | Move to `ocr-insert-score`; visual container becomes one evidence term. |
| `ocr_document.py` | `_build_region_prepass` | `page <= 3` plus key-points/highlights or box anchor can classify `structured_insert`. | Publisher-template sensitive; can swallow body text. | Move to `ocr-insert-score`; keep medium confidence as candidate. |
| `ocr_document.py` | `_build_region_prepass` | `last_insert_on_page` can continue short blocks into `structured_insert`. | Sequential propagation from one early mistake. | Move to `ocr-insert-score`; require cluster coherence and expansion audit. |

## Direct Object Matches

| File | Symbol | Rule | Current Risk | Remediation |
| --- | --- | --- | --- | --- |
| `ocr_figures.py` | `build_figure_inventory` | Same-page nearest asset is assigned to a legend before `caption_score` is computed. | Nearest media can be wrong when multiple figures/assets exist. | Move to `ocr-figure-score-matching`; score all candidates first. |
| `ocr_tables.py` | `_pick_best_asset` | Candidate table asset is selected by vertical distance. | Previous-page, continuation, and rotated tables can misbind. | Move to `ocr-table-score-matching`; select by `score_table_match`. |

## Direct Reorder Decisions

| File | Symbol | Rule | Current Risk | Remediation |
| --- | --- | --- | --- | --- |
| `ocr_render.py` | `_order_tail_blocks` | All tail-page blocks reordered by column+y unconditionally when tail roles outnumber body roles. | Mixed pages (body continuation + backmatter) can break reading order. | Move to `ocr-layout-confidence`; add confidence gate before reorder. |

## Renderer Inference

| File | Symbol | Rule | Current Risk | Remediation |
| --- | --- | --- | --- | --- |
| `ocr_render.py` | `render_fulltext_markdown` heading inference | Heading level (`##`/`###`) determined from font size clusters without confidence scoring. | Ambiguous font sizes produce wrong heading hierarchy. | Move to style-profile confidence; add uncertainty annotations. |
| `ocr_render.py` | `_is_bogus_heading` | Hard-coded rules (text >100 chars, multiple periods, verb words) suppress or demote headings. | False positives suppress genuine section headings. | Move to heading scoring plan; soft-suppress with low confidence. |

## Remediation Map

| Rule Family | Plan | Action |
| --- | --- | --- |
| Figure asset matching | `2026-06-08-ocr-figure-score-matching-plan.md` | Convert nearest-asset choice into scored candidate selection. |
| Table asset matching | `2026-06-08-ocr-table-score-matching-plan.md` | Convert vertical-nearest choice into scored candidate selection. |
| Layout column inference | `2026-06-08-ocr-layout-confidence-plan.md` | Add confidence and low-confidence reorder guard. |
| Structured insert promotion | `2026-06-08-ocr-insert-score-plan.md` | Convert direct promotion into score/candidate behavior. |
| Health aggregation | `2026-06-08-ocr-health-hard-rule-summary-plan.md` | Report remaining hard-rule and uncertainty counts. |

## Baseline Counts

- `direct_role_mutation_count`: 3
- `direct_object_match_count`: 2
- `direct_reorder_decision_count`: 1
- `direct_renderer_inference_count`: 2
