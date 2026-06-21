# OCR Per-Role Audit Strategies

> **Use this as a quick reference** for deciding how to inspect any role.
> For actual audit work, use `scripts/audit_helpers.py` recipes + `ocr-vision-audit-templates.md`.
> Do NOT write custom Python for per-role checks — it's already built.

## Tier Classification

| Tier | Method | When |
|------|--------|------|
| A | **Vision-required** | Must dispatch `vision` subagent. Data alone insufficient. |
| B | **Data-primary, vision-confirm** | Read data first. Dispatch vision only when data flags an issue. |
| C | **Data-sufficient** | JSON analysis is enough. Vision only for ordering/layout ambiguity. |
| D | **Structural-only** | Read from block trace / document structure. No vision needed. |

## Role → Tier Mapping

### Tier A — Vision-Required

| Role | Why vision is needed |
|------|---------------------|
| `figure_asset` | Is the box covering an actual image? Are sub-panels merged? |
| `media_asset` | Is this a figure, a table, or a phantom block? |
| `figure_caption` | Is it a real caption, sub-panel label, or body mention? Where is its image? |
| `figure_caption_candidate` | Should it be confirmed or demoted? |
| `figure_inner_text` | Is it inside a figure (panel label) or separate text? |
| `table_caption` | Same as figure_caption. Cross-page? |
| `table_caption_candidate` | Should it be confirmed? |
| `table_asset` | Is this actually a table image? |
| `table_html` | Is the HTML table rendering correctly? |
| `structured_insert` | Is this a callout box or mislabeled body text? |
| `structured_insert_candidate` | Should it be confirmed? |
| `non_body_insert` | What is this element visually? |

### Tier B — Data-Primary, Vision-Confirm

| Role | Data check | When to add vision |
|------|-----------|-------------------|
| `body_paragraph` | zone=body_zone? text non-empty? | zone wrong, text empty, or two-column ambiguity |
| `section_heading` | numbering depth, heading absorption (two levels in one block) | verify visually if absorption detected |
| `subsection_heading` | same as section_heading | same |
| `sub_subsection_heading` | same | same |
| `reference_heading` | in reference_zone? before first reference_item? | transition page boundary |
| `reference_item` | in reference_zone? correct numbering pattern? | real intrusions or numbering gaps |
| `backmatter_heading` | after last reference? in backmatter_zone? | if inside reference_zone |
| `backmatter_body` | same | same |

### Tier C — Data-Sufficient

`paper_title`, `authors`, `affiliation`, `frontmatter_support`, `frontmatter_noise`,
`abstract_heading`, `abstract_body`, `keywords`, `footnote`

These are on page 1 (or page N for footnotes) at known positions with known patterns.
Read `page_001_index.json`. Vision only for ordering ambiguity or badge mislabel suspicion.

### Tier D — Structural-Only

`tail_candidate_body`, `backmatter_boundary_candidate`, `backmatter_boundary_heading`,
`ocr_raw_error`, `unknown_structural`, `page_header`, `page_footer`, `noise`

Read from `blocks.structured.jsonl` (text, span_metadata, _ocr_raw_status) or
`document_structure.json` (tail order, boundaries). No vision needed.

## Common Failure Patterns (quick reference)

| Pattern | Signal in data | Confirmation |
|---------|---------------|-------------|
| Sub-panels not merged | N asset blocks, 1 fig with < N assets | Vision: are they panels of same figure? |
| Caption sandwiched between figs | close_asset_tie with above+below | Vision: which figure owns the caption? |
| Cross-page caption | no_asset_match, prev/next page has orphan assets | Vision: is image on adjacent page? |
| Sub-panel heading as caption | figure_caption with text like "Musculoskeletal conditions..." | Vision: is this a panel heading? |
| Truncated legend as standalone | "Fig. 6" only, long caption below | Vision: composite figure with shared caption? |
| Table mislabeled as figure | media_asset with raw_label=table | Vision: is this a table or figure? |
| Body text as noise | noise with text_preview > 30 chars, not at page edge | Vision: is this body text? |
| Heading absorption | section_heading text has "2. ... 2.1. ..." | Vision: two heading levels merged? |
| Badge as authors | authors text = "HIGHLIGHTED PAPER" | Vision: is it a badge or authors? |
| Reference zone intrusion | body_paragraph in reference_zone | Vision: verify boundary |
