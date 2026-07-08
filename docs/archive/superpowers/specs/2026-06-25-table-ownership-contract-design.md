# Table Note Ownership Contract — Design Spec

## Problem

OCR-v2 table pipeline has three unclosed gaps in the note ownership contract:

1. **Weak-matched table captions are silently lost** — `consumed_block_ids` unconditionally includes caption `block_id` even when `has_asset=False`. The body renderer skips the caption but no embed is emitted (because `tables_by_page` filters `has_asset=True` only). Caption text vanishes from fulltext.
2. **`_SKIPPED_BODY_ROLES` runs before `consumed_table_block_keys`** — footnote-role table notes are skipped by role rather than by ownership. Works but inverts the control relationship: table ownership should be the first-class skip mechanism.
3. **Weak-matched table notes are neither consumed nor rendered** — note collection only runs when `matched_asset` exists. The notes stay in body (existing behavior, acceptable for now).

## Scope

- `paperforge/worker/ocr_tables.py` — `build_table_inventory` only.
- `paperforge/worker/ocr_render.py` — `render_fulltext_markdown` skip ordering only.
- No changes to `ocr.py`, `ocr_document.py`, `ocr_objects.py`.
- No new figure heuristics.

## Approach (chosen: A — minimal)

Two structural changes:

### A1. `ocr_tables.py:430` — caption consumed only when asset exists

```python
# before:
consumed_block_ids = [caption.get("block_id", "")]
# after:
consumed_block_ids = [caption.get("block_id", "")] if matched_asset else []
```

- Strong match (`has_asset=True`): caption consumed as before → embed replaces it in fulltext.
- Weak match (`has_asset=False`): caption NOT consumed → flows through body render to `table_caption` handler → `tables_by_page` empty → blockquote fallback (`> **Table Caption:** {text}`).
- Note blocks unaffected: `note_block_ids` only populated when `matched_asset` exists (line 358 guard). Weak matches have no collected notes; existing behavior unchanged.

### A2. `ocr_render.py` — ownership skip before role skip, with per-block page

**Reorder.** Extract the `consumed_table_block_keys` check and insert it before the `_SKIPPED_BODY_ROLES` block. The old position's instance is removed (only `consumed_caption_keys` and `abstract_member_keys` remain there).

**Per-block page.** The consumed key currently uses `table["page"]` for all blocks, but notes/assets may live on different pages (cross-page continuation). Build `consumed_table_block_keys` using each block's real page:

```python
block_page_by_id = {
    block.get("block_id"): block.get("page")
    for block in structured_blocks
    if block.get("block_id") is not None
}

for table in table_inventory.get("tables", []):
    for block_id in table.get("consumed_block_ids", []):
        if not block_id:
            continue
        page = block_page_by_id.get(block_id, table.get("page"))
        consumed_table_block_keys.add((page, block_id))
```

Effect:
- Footnote-role table notes: consumed by ownership first, removed from body.
- Non-table footnotes: not consumed → still hit `_SKIPPED_BODY_ROLES` → skipped.
- Cross-page note: resolved to its actual page → ownership skip works.
- All other consumed blocks unchanged.

## Testing

Split by layer — inventory tests in `test_ocr_tables.py`, render/integration tests in `test_ocr_render.py`:

### `tests/test_ocr_tables.py` — inventory contract

| Test | Fixture | Assertions |
|------|---------|------------|
| `test_strong_table_match_collects_note_block_ids_and_texts` | same-page caption + asset, x_overlap >= 0.5, asset below caption, footnote-role note below asset | `note_block_ids` non-empty; `note_texts` non-empty; `consumed_block_ids` includes caption, asset, note |
| `test_weak_match_caption_has_empty_consumed_block_ids` | table_caption + far-away asset (score < 0.4) | `consumed_block_ids` empty (no caption, no asset, no notes); caption still in `tables` |
| `test_cross_page_note_consumed_by_actual_page` | caption page=6, asset page=7, note on page=7 | note_block_id mapped to page=7 in consumed block tracking |

### `tests/test_ocr_render.py` — render contract

| Test | Fixture | Assertions |
|------|---------|------------|
| `test_weak_match_caption_fallback_not_lost` | table_caption + weak table inventory (no has_asset) | `> **Table Caption:**` present; `### Table` absent |
| `test_consumed_table_note_skipped_before_role_skip` | strong match + **body_paragraph-role** note below asset (non-footnote) | note text NOT in fulltext body — proves ownership skip, not role-skip |
| `test_footnote_role_table_note_renders_in_object` | strong match + footnote-role note below asset | note text in table_xxx.md `## Notes`; note text NOT in fulltext |

The `body_paragraph`-role note test is critical: it proves ownership skip actually fires, not that `footnote` was caught by `_SKIPPED_BODY_ROLES`.

## Acceptance

- Existing 300+ tests stay green.
- For matched tables, every note block in `note_block_ids` must:
  - be included in `consumed_block_ids`;
  - be rendered in `render/tables/table_xxx.md` under `## Notes`;
  - not render as main fulltext body prose.
- Weak-matched table captions must fall back to `> **Table Caption:** {text}` blockquote, not vanish.
- Non-footnote-role table notes are removed from body by ownership skip, not by `_SKIPPED_BODY_ROLES`.
- Non-table footnotes still globally skipped by `_SKIPPED_BODY_ROLES`.
- Table-like notes not admitted by note geometry remain governed by existing body rendering behavior.
