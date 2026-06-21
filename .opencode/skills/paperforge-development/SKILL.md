---
name: paperforge-development
description: Use when doing PaperForge engineering or internal OCR truth-audit work. Triggered by: "OCR审计" "审OCR" "审计OCR" "审一下" "审计这篇" "block review" "ocr truth audit" "annotated pages" "看下角色对不对" "块角色" "visual audit" "对照一下图片" "校对block".
---

# PaperForge Development

Developer-only skill family for internal PaperForge OCR audit work.

Use this when the task is to inspect OCR truth, classify failures, and write audit evidence without changing the runtime PaperForge skill graph.

## Route

- OCR truth audit: `workflows/ocr-truth-audit.md`

## Scripts

- `scripts/ocr_truth_audit.py` — artifact generator (annotated pages, summaries, findings)
- `scripts/audit_helpers.py` — structured data maps for vision agents (figure, frontmatter, reference, body)
- `scripts/verify_review_coverage.py` — coverage verification
- `scripts/diff_audit.py` — diff audit between truth and pipeline

## Invariant

- Truth first.
- Do not start by authoring expectations.
- Establish block-level truth from page visuals and artifacts before comparing pipeline behavior.

## Agent Dispatch Rules (CRITICAL — read before any audit task)

The #1 source of audit errors is using the wrong tool for the question.
Follow these rules unconditionally:

### When to dispatch `vision` subagent (MUST):

The workflow in `workflows/ocr-truth-audit.md` Step 6 tells you the exact commands.
Summary:

| Audit domain | Data recipe | Vision template |
|-------------|-------------|----------------|
| Figures | `audit_helpers.py --recipe figure_map` | atoms/ocr-vision-audit-templates.md — Template 1 |
| Frontmatter | `audit_helpers.py --recipe frontmatter_map` | Template 2 |
| References | `audit_helpers.py --recipe reference_map` | Template 3 |
| Body text | `audit_helpers.py --recipe body_text_map` | Template 4 |

**Procedure:** (1) Run the recipe → get JSON. (2) Read the template. (3) Paste JSON into template. (4) Dispatch as `vision` subagent prompt.

### Forbidden agent patterns:

- `general` subagent claiming to "see" an annotated page. **Only `vision` can view images.**
- Concluding figure matching from `figure_table_ownership_summary.json` alone. **Must cross-check with source `figure_inventory.json` AND visual truth.**
- Reporting `reference_intrusion_candidates` as errors without checking block roles.**noise blocks in `reference_zone` are expected.**
- "The block has 0 candidates so figure is on another page" without scanning `page_{N-1}_index.json` and `page_{N+1}_index.json`.

### Finding trust boundaries (CRITICAL):

The auto-generated findings in `audit_report.json` contain substantial noise.
**Only these [CODE] checks are reliable — all others need [VISION]:**

| Finding category | Trust? | Why |
|-----------------|--------|-----|
| `role_mismatch` (from diff_audit.py) | ✅ [CODE] | Direct string comparison, 100% |
| `zone_mismatch` (from block_review.jsonl) | ✅ [CODE] | Direct string comparison, 100% |
| `render_mapping_error` — non-noise blocks | ✅ [CODE] | Substring match, exclude noise |
| `unmatched_asset_count > 0` | ✅ [CODE] | deterministic count from inventory |
| `coverage_check status` | ✅ [CODE] | direct comparison |
| `reference_span_audit status` | ✅ [CODE] | deterministic |
| `same_page_boundary_error` | ❌ NEVER | Page-level heuristic, no actionable info |
| `reference_span_error` (audit_report.json) | ⚠️ Partially | Span may be too wide; need vision to verify boundary |
| `object_ownership_error` (audit_report.json) | ❌ NEVER | Misses unmatched assets entirely |
| `render_mapping_error` — noise blocks | ❌ NEVER | noise should not be in fulltext |
| `image_quality`, `font`, `color`, `typography` | ❌ [VISION] only | No metadata available |

### Per-role audit strategies:

Full methodology for each of the 28 canonical roles is in `atoms/ocr-role-audit-strategies.md`.
Each role is classified into one of 4 tiers:

| Tier | Method | Roles |
|------|--------|-------|
| A | Vision-required | `figure_asset`, `media_asset`, `figure_caption`, `figure_caption_candidate`, `table_caption`, `table_asset`, `table_html`, `structured_insert` |
| B | Data-primary, vision-confirm | `body_paragraph`, `section_heading`, `subsection_heading`, `reference_item`, `reference_heading`, `backmatter_heading`, `backmatter_body` |
| C | Data-sufficient | `paper_title`, `authors`, `affiliation`, `abstract_heading`, `abstract_body`, `keywords`, `frontmatter_support`, `frontmatter_noise`, `footnote` |
| D | Structural-only | `tail_candidate_body`, `backmatter_boundary_*`, `ocr_raw_error`, `unknown_structural`, `page_header`, `page_footer`, `noise` |

### Deep per-role + quality audit:

**`atoms/ocr-vision-audit-master.md`** extends all 4 templates with:
- Per-role analysis covering role/zone/reference AND quality (typography, image, table)
- Cross-reference pathways linking all audit data sources for any block_id
- Chart-type routing to `paperforge/skills/paperforge/atoms/chart-reading/*.md`
- Full-page typography sweep (font consistency, alignment, orphans/widows, heading hierarchy)
- Output format for block_review.jsonl with optional `quality_checks` and `page_typography` fields

After the 4 recipe-driven vision passes in Step 6, run the master atom:
```bash
# Read the master atom before dispatching per-role vision
cat .opencode/skills/paperforge-development/atoms/ocr-vision-audit-master.md
```
It contains the per-role data-cross-ref + quality-check methodology. Paste the relevant section into each vision subagent prompt depending on which role set the agent is reviewing.
