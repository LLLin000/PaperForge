# OCR Canonical Roles

`truth_role` in `block_review.jsonl` MUST be one of these canonical pipeline roles.
Do not invent new role names — use only the set below. Non-canonical names
will be normalized by `diff_audit.py` but relying on that is a workflow violation.

## Frontmatter

| Role | When |
|------|------|
| `paper_title` | Document title on page 1 |
| `authors` | Author byline |
| `affiliation` | Author affiliation block |
| `frontmatter_support` | Correspondence, DOI, dates, data availability |
| `frontmatter_noise` | Page-1 non-structural furniture (journal name, article type, publisher strip) |
| `abstract_heading` | "Abstract" label |
| `abstract_body` | Abstract body text |
| `keywords` | Keywords block |

## Body

| Role | When |
|------|------|
| `section_heading` | Top-level section heading |
| `subsection_heading` | Second-level section heading |
| `sub_subsection_heading` | Third-level section heading |
| `body_paragraph` | Narrative body paragraph |
| `tail_candidate_body` | Body paragraph in the tail spread |

## Reference

| Role | When |
|------|------|
| `reference_heading` | "References" heading |
| `reference_item` | Individual reference entry |

## Backmatter

| Role | When |
|------|------|
| `backmatter_heading` | Backmatter section heading (Acknowledgments, Funding, etc.) |
| `backmatter_heading_candidate` | Possible backmatter heading, not yet confirmed |
| `backmatter_body` | Backmatter body paragraph |
| `backmatter_boundary_heading` | Confirmed backmatter boundary heading |
| `backmatter_boundary_candidate` | Possible backmatter boundary |

## Figure / Table

| Role | When |
|------|------|
| `figure_asset` | Figure image/media |
| `figure_caption` | Confirmed figure caption |
| `figure_caption_candidate` | Probable figure caption, not fully confirmed |
| `figure_inner_text` | Text inside a figure (panel labels, axis labels) |
| `table_caption` | Confirmed table caption |
| `table_caption_candidate` | Probable table caption, not fully confirmed |
| `table_asset` | Table image |
| `table_html` | HTML native table |
| `table_html_candidate` | Probable HTML native table |
| `media_asset` | Generic media image (when figure/table type is unclear) |

## Structural Inserts

| Role | When |
|------|------|
| `structured_insert` | Structured block (callout box, highlight, algorithm) |
| `structured_insert_candidate` | Probable structured insert |
| `non_body_insert` | Non-body decorative insert (publisher strip, sidebar filler) |

## Noise & Fallback

| Role | When |
|------|------|
| `noise` | Decorative line, page furniture, garbage OCR |
| `footnote` | Page footnote |
| `unknown_structural` | Block exists but no role fits (structural gate fallback) |
| `ocr_raw_error` | OCR extraction failure (empty text) |
| `page_header` | Running header repeat |
| `page_footer` | Running footer repeat |

## Ground Truth Only (seed roles, never final)

These are assigned as `seed_role` by the early role assignment but never appear
as the final pipeline output role. When auditing, use the final role above
even if the seed role seems more intuitive:

- `figure_title` (raw OCR label, not a final role)
