# First parse ↔ derived rebuild equivalence

Scope: the two papers whose role maps differed after the Phase A corpus check
(`2AGGSMVQ`, `23T2B8ZX`, 100-paper sample). Goal: locate the first diverging
stage, then decide whether the difference is a contract defect.

## Method

Per paper, in a throwaway vault containing only `meta.json`,
`canonical/blocks.raw.jsonl` and `raw/source_metadata.json` (`source_pdf`
cleared so the rebuild has no PDF evidence), the rebuild path
`paperforge.worker.ocr_rebuild._rebuild_one_paper` ran serially while
`build_structured_blocks`, `pre_match_normalize`, `post_match_normalize`,
`build_figure_inventory` and `build_table_inventory` were wrapped to snapshot
their inputs and outputs. Each snapshot is keyed by `(page, block_id)` and
compared field by field. The same stages were replayed outside the rebuild with
the rebuild's exact call contract.

## Result

| Stage | `2AGGSMVQ` | `23T2B8ZX` |
|---|---|---|
| raw blocks before / after phase 1 | identical | identical |
| after `build_structured_blocks(seed_only)` | identical | identical |
| after `pre_match_normalize` | identical (full row, incl. `_` fields) | identical |
| figure inventory | identical | identical |
| `post_match_normalize` snapshot | 6 blocks: `media_asset → figure_asset` | 3 blocks: same |
| final `structure/blocks.structured.jsonl` | identical | identical |

The single stage difference is a **call-order difference, not a data
difference**: `_phase3_figure_tables` runs `write_back_figure_roles(...)`
before `post_match_normalize`, so the promotion `media_asset → figure_asset`
is already committed when post-match snapshots are taken. The production
pipeline commits the same promotion during `apply_object_writebacks`, after
post-match. Final roles, `render_default` and `index_default` agree exactly.

Two artefacts of the comparison harness, both fixed while running this, are
worth remembering:

- `post_match_normalize` **must** receive `source_frontmatter_anchors`; omitting
  it flips 1–4 frontmatter blocks per paper (`body_paragraph ↔
  frontmatter_noise`).
- A stage-by-stage comparison must include `write_back_figure_roles` on the
  production side, otherwise the post-match snapshot shows the ordering effect
  and looks like a role regression.

## Decision

No code change. The observed differences are explained by ordering and by the
harness contract above; there is no input evidence change, no role divergence
at the final stage, and nothing to pin with a regression test. First parse and
rebuild converge for these papers once both call contracts are matched.

## Related Phase A fixes in this change

- `paperforge/worker/ocr_document.py`: `_explicit_page_widths` — Box merging
  now requires a page width stated by the OCR layer. `_page_widths_by_page`
  still falls back to the widest bbox for layout banding, where an estimate is
  acceptable.
- `paperforge/worker/ocr_render.py`: in the tail region (`references_start`
  page, falling back to `backmatter_start`), an unnumbered heading whose type
  size equals the body's top-level heading size renders at the top level. The
  role is not rewritten; tail sub-headings with a smaller size, and any
  numbered heading, keep their role depth. `heading_events[].markdown_level`
  follows the emitted prefix.

  Verified against `master` on five papers: `24A2QUAH` (`Conflicts of
  Interest` ###→##, `Acknowledgments` ####→##), `2AGGSMVQ`
  (`ACKNOWLEDGMENTS` ####→##), `5CK2JEIS` (`Acknowledgements` ####→##,
  `Keywords` ####→##, both on pages after `references_start`). Papers without
  span evidence (`2332GHPT` in this vault) keep the role-derived depth —
  there is no typographic evidence to restore from.
