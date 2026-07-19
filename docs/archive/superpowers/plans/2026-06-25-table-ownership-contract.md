# Table Ownership Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close table note ownership gaps: weak-match caption not lost, ownership skip before role skip, cross-page consumed key resolution.

**Architecture:** Two structural changes in `ocr_tables.py` (caption consumed only when asset exists) and `ocr_render.py` (per-block page for consumed keys, ownership skip check before `_SKIPPED_BODY_ROLES`).

**Tech Stack:** Python 3.14, pytest.

---

### Task 1: A1 — caption consumed only when matched_asset exists

**Files:**
- Modify: `paperforge/worker/ocr_tables.py:430`
- Test: `tests/test_ocr_tables.py` (in Task 4)

- [ ] **Step 1: Change consumed_block_ids to conditional caption**

Current code (line 430):
```python
        consumed_block_ids = [caption.get("block_id", "")]
        if matched_asset:
            consumed_block_ids.append(matched_asset.get("block_id", ""))
        consumed_block_ids.extend(note_block_ids)
```

Change to:
```python
        consumed_block_ids = [caption.get("block_id", "")] if matched_asset else []
        if matched_asset:
            consumed_block_ids.append(matched_asset.get("block_id", ""))
        consumed_block_ids.extend(note_block_ids)
```

Effect: when `matched_asset` is None, `consumed_block_ids` starts empty instead of containing the caption `block_id`. Caption flows through body render to the `table_caption` handler fallback.

- [ ] **Step 2: Run existing table tests**

Run: `python -m pytest tests/test_ocr_tables.py -v --tb=short`
Expected: all existing tests pass.

- [ ] **Step 3: Commit**

```bash
git add paperforge/worker/ocr_tables.py
git commit -m "fix: conditional caption block_id in consumed_block_ids"
```

---

### Task 2: A2 — per-block page for consumed_table_block_keys

**Files:**
- Modify: `paperforge/worker/ocr_render.py:997-1002`

- [ ] **Step 1: Build block→page map and use real page for consumed keys**

Current code (lines 997-1002):
```python
    consumed_table_block_keys: set[tuple[int | None, str | int]] = set()
    for table in table_inventory.get("tables", []):
        table_page = table.get("page")
        for block_id in table.get("consumed_block_ids", []):
            if block_id:
                consumed_table_block_keys.add((table_page, block_id))
```

Change to:
```python
    consumed_table_block_keys: set[tuple[int | None, str | int]] = set()
    # Map both raw id and str(id) because note_block_ids are stringified in
    # build_table_inventory while structured_blocks may carry int block_ids.
    block_page_by_id: dict[str | int, int | None] = {}
    for block in structured_blocks:
        bid = block.get("block_id")
        if bid is None:
            continue
        page = block.get("page")
        block_page_by_id[bid] = page
        block_page_by_id[str(bid)] = page
    for table in table_inventory.get("tables", []):
        for block_id in table.get("consumed_block_ids", []):
            if not block_id:
                continue
            page = block_page_by_id.get(block_id, table.get("page"))
            consumed_table_block_keys.add((page, block_id))
```

This resolves each consumed block's page from structured_blocks instead of assuming all blocks share `table["page"]`. Cross-page notes stay correctly keyed.

- [ ] **Step 2: Run existing render tests**

Run: `python -m pytest tests/test_ocr_render.py -v --tb=short`
Expected: all existing tests pass.

- [ ] **Step 3: Commit**

```bash
git add paperforge/worker/ocr_render.py
git commit -m "fix: resolve consumed table block keys by per-block page"
```

---

### Task 3: A2 — ownership skip before role skip

**Files:**
- Modify: `paperforge/worker/ocr_render.py:1403-1436`

- [ ] **Step 1: Move consumed_table_block_keys check before _SKIPPED_BODY_ROLES**

Current code (lines 1403-1436):
```python
        if role == "structured_insert":
            pass  # render as callout below
        elif not block.get("render_default", True):
            bm_start = getattr(document_structure, "spread_start", None) if document_structure else None
            if role != "frontmatter_noise" or block_page is None or not bm_start or block_page < bm_start:
                continue
        if role in CONSUMED_FRONTMATTER_ROLES and int(block.get("page", 0) or 0) <= 2:
            continue
        _SKIPPED_BODY_ROLES = {
            "abstract_heading",
            "abstract_body",
            "footnote",
            "frontmatter_noise",
            "frontmatter_support",
            "table_html",
            "table_caption_candidate",
            "figure_caption",
            "figure_inner_text",
        }
        if role in _SKIPPED_BODY_ROLES:
            bm_start = getattr(document_structure, "spread_start", None) if document_structure else None
            if role == "frontmatter_noise" and block_page is not None and bm_start and block_page >= bm_start:
                pass
            else:
                continue

        block_id = block.get("block_id")
        block_key = _page_block_key(block_page, block_id)
        if block_id is not None and (block_key in consumed_caption_keys or block_id in consumed_caption_ids_unkeyed):
            continue
        if block_id is not None and (block_page, block_id) in consumed_table_block_keys:
            continue
        if block_key in abstract_member_keys or block_id in abstract_member_ids_unkeyed:
            continue
```

Change to:
```python
        if role == "structured_insert":
            pass  # render as callout below
        elif not block.get("render_default", True):
            bm_start = getattr(document_structure, "spread_start", None) if document_structure else None
            if role != "frontmatter_noise" or block_page is None or not bm_start or block_page < bm_start:
                continue
        if role in CONSUMED_FRONTMATTER_ROLES and int(block.get("page", 0) or 0) <= 2:
            continue

        # Ownership skip first — table note removal by contract, not by role
        block_id = block.get("block_id")
        if block_id is not None and (block_page, block_id) in consumed_table_block_keys:
            continue

        _SKIPPED_BODY_ROLES = {
            "abstract_heading",
            "abstract_body",
            "footnote",
            "frontmatter_noise",
            "frontmatter_support",
            "table_html",
            "table_caption_candidate",
            "figure_caption",
            "figure_inner_text",
        }
        if role in _SKIPPED_BODY_ROLES:
            bm_start = getattr(document_structure, "spread_start", None) if document_structure else None
            if role == "frontmatter_noise" and block_page is not None and bm_start and block_page >= bm_start:
                pass
            else:
                continue

        block_key = _page_block_key(block_page, block_id)
        if block_id is not None and (block_key in consumed_caption_keys or block_id in consumed_caption_ids_unkeyed):
            continue
        if block_key in abstract_member_keys or block_id in abstract_member_ids_unkeyed:
            continue
```

Changes:
- `consumed_table_block_keys` check extracted (with `block_id = block.get("block_id")`) and placed before `_SKIPPED_BODY_ROLES`
- Old `consumed_table_block_keys` check at line 1433 removed
- Redundant `block_id = block.get("block_id")` removed from original location (already fetched above)

- [ ] **Step 2: Run render tests**

Run: `python -m pytest tests/test_ocr_render.py -v --tb=short`
Expected: all existing tests pass.

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/unit/ tests/test_ocr_render.py tests/test_ocr_tables.py -v --tb=short`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add paperforge/worker/ocr_render.py
git commit -m "fix: ownership skip before role skip in render loop"
```

---

### Task 4: Inventory regression tests

**Files:**
- Add to: `tests/test_ocr_tables.py`

Add three tests at end of file.

- [ ] **Step 1: Add `test_strong_table_match_collects_note_block_ids_and_texts`**

```python
def test_strong_table_match_collects_note_block_ids_and_texts() -> None:
    """Strong match collects note_block_ids, note_texts, and consumed_block_ids."""
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "page": 5, "block_id": "p5_asset",
            "role": "table_asset", "raw_label": "table",
            "bbox": [100, 540, 600, 900], "text": "",
        },
        {
            "page": 5, "block_id": "p5_caption",
            "role": "table_caption",
            "text": "Table 1. Results.", "bbox": [100, 500, 600, 540],
        },
        {
            "page": 5, "block_id": "p5_note",
            "role": "footnote",
            "text": "* p < 0.05.", "bbox": [100, 905, 600, 930],
        },
    ]

    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]
    assert table["has_asset"] is True
    assert "p5_note" in table.get("note_block_ids", [])
    assert table.get("note_texts") == ["* p < 0.05."]
    consumed = table.get("consumed_block_ids", [])
    assert "p5_caption" in consumed
    assert "p5_asset" in consumed
    assert "p5_note" in consumed
```

- [ ] **Step 2: Add `test_weak_match_caption_has_empty_consumed_block_ids`**

```python
def test_weak_match_caption_has_empty_consumed_block_ids() -> None:
    """Weak-matched caption should not be consumed — falls through to blockquote."""
    from paperforge.worker.ocr_tables import build_table_inventory

    # Asset on page 8, caption on page 5 — outside candidate_pages range
    # (caption_page - 1, caption_page, caption_page + 1), so never matched.
    structured_blocks = [
        {
            "page": 8, "block_id": "p8_asset",
            "role": "table_asset", "raw_label": "table",
            "bbox": [100, 540, 600, 900], "text": "",
        },
        {
            "page": 5, "block_id": "p5_caption",
            "role": "table_caption",
            "text": "Table 1.", "bbox": [100, 50, 600, 90],
        },
    ]

    inventory = build_table_inventory(structured_blocks)
    assert inventory["tables"]
    table = inventory["tables"][0]
    assert table["has_asset"] is False
    assert table["match_status"] in {"unmatched_caption", "ambiguous"}
    assert "p5_caption" not in table.get("consumed_block_ids", [])
```

- [ ] **Step 3: Run both inventory tests**

Run: `python -m pytest tests/test_ocr_tables.py::test_strong_table_match_collects_note_block_ids_and_texts tests/test_ocr_tables.py::test_weak_match_caption_has_empty_consumed_block_ids -v --tb=short`
Expected: all PASS.

Note: cross-page consumed key test lives in Task 5 (render layer) because `build_table_inventory` only collects notes on the matched asset's page — cross-page resolution is a renderer concern.

- [ ] **Step 4: Commit**

```bash
git add tests/test_ocr_tables.py
git commit -m "test: inventory contract for table note ownership"
```

---

### Task 5: Render regression tests

**Files:**
- Add to: `tests/test_ocr_render.py`

Add three tests at end of file.

- [ ] **Step 1: Add `test_weak_match_caption_fallback_not_lost`**

```python
def test_weak_match_caption_fallback_not_lost() -> None:
    """Weak-matched table caption uses blockquote fallback, not heading, not silent loss."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured = [
        {
            "page": 5,
            "role": "table_caption",
            "text": "Table 1. Results summary.",
            "block_id": "p5_b1",
        },
    ]

    # Weak-match table: inventory has has_asset=False, consumed_block_ids=[]
    # Caption must NOT be lost — falls through to blockquote fallback.
    table_inventory = {
        "tables": [
            {
                "page": 5,
                "caption_block_id": "p5_b1",
                "caption_text": "Table 1. Results summary.",
                "has_asset": False,
                "consumed_block_ids": [],
                "match_status": "unmatched_caption",
            }
        ],
        "unmatched_assets": [],
    }

    md = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory=table_inventory,
        page_count=5,
        document_structure=None,
        reader_payload={},
    )

    assert "### Table 1. Results summary." not in md
    assert "> **Table Caption:** Table 1. Results summary." in md
```

- [ ] **Step 2: Add `test_consumed_table_note_skipped_before_role_skip`**

This tests that a body_paragraph-role note (not footnote) is removed from body by ownership skip:

```python
def test_consumed_table_note_skipped_before_role_skip() -> None:
    """Non-footnote-role table note removed by ownership skip, not role skip."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured = [
        {
            "page": 5,
            "role": "body_paragraph",
            "text": "Main body text.",
            "block_id": "p5_body",
            "bbox": [100, 100, 500, 130],
        },
        {
            "page": 5,
            "role": "table_asset",
            "raw_label": "table",
            "text": "",
            "block_id": "p5_asset",
            "bbox": [100, 200, 600, 500],
        },
        {
            "page": 5,
            "role": "table_caption",
            "text": "Table 1. Results.",
            "block_id": "p5_caption",
            "bbox": [100, 510, 600, 550],
        },
        {
            "page": 5,
            "role": "body_paragraph",
            "text": "Note: all values are mean +/- SD.",
            "block_id": "p5_note",
            "bbox": [100, 555, 600, 580],
        },
    ]

    table_inventory = {
        "tables": [
            {
                "caption_block_id": "p5_caption",
                "page": 5,
                "caption_text": "Table 1. Results.",
                "asset_block_id": "p5_asset",
                "has_asset": True,
                "consumed_block_ids": ["p5_caption", "p5_asset", "p5_note"],
                "segments": [{"page": 5, "asset_block_id": "p5_asset", "asset_bbox": [100, 200, 600, 500]}],
                "note_block_ids": ["p5_note"],
                "note_texts": ["Note: all values are mean +/- SD."],
                "match_status": "matched",
            }
        ],
        "unmatched_assets": [],
    }

    md = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory=table_inventory,
        page_count=5,
        document_structure=None,
        reader_payload={},
    )

    # Note: ownership skip removes both caption text and note from body
    assert "Note: all values are mean +/- SD." not in md
    assert "Table 1. Results." not in md
    # Table embed emitted via _emit_page_objects
    assert "![[render/tables/table_001.md]]" in md
    # Fallback NOT triggered for matched table
    assert "> **Table Caption:**" not in md
```

- [ ] **Step 3: Add `test_table_object_renderer_includes_footnote_note`**

```python
def test_table_object_renderer_includes_footnote_note() -> None:
    """Table object renderer (render_table_object_markdown) includes ## Notes section.
    Fulltext body skips the footnote-role note via ownership skip (not role skip)."""
    from paperforge.worker.ocr_render import render_fulltext_markdown
    from paperforge.worker.ocr_objects import render_table_object_markdown

    note_text = "* p < 0.05 vs baseline."

    obj_md = render_table_object_markdown({
        "table_id": "table_001",
        "page": 5,
        "caption": "Table 1. Results.",
        "image_relpath": "assets/tables/table_001.jpg",
        "confidence": 0.85,
        "formal_table_number": 1,
        "note_texts": [note_text],
        "note_match_reason": "note_band_geometry_match",
    })

    assert "## Notes" in obj_md
    assert note_text in obj_md

    structured = [
        {
            "page": 5,
            "role": "body_paragraph",
            "text": "Main body text.",
            "block_id": "p5_body",
            "bbox": [100, 100, 500, 130],
        },
        {
            "page": 5,
            "role": "footnote",
            "text": note_text,
            "block_id": "p5_note",
            "bbox": [100, 905, 600, 930],
        },
        {
            "page": 5,
            "role": "table_asset",
            "raw_label": "table", "text": "",
            "block_id": "p5_asset",
            "bbox": [100, 200, 600, 500],
        },
        {
            "page": 5,
            "role": "table_caption",
            "text": "Table 1. Results.",
            "block_id": "p5_caption",
            "bbox": [100, 510, 600, 550],
        },
    ]

    table_inventory = {
        "tables": [
            {
                "caption_block_id": "p5_caption",
                "page": 5,
                "caption_text": "Table 1. Results.",
                "asset_block_id": "p5_asset",
                "has_asset": True,
                "consumed_block_ids": ["p5_caption", "p5_asset", "p5_note"],
                "segments": [{"page": 5, "asset_block_id": "p5_asset", "asset_bbox": [100, 200, 600, 500]}],
                "note_block_ids": ["p5_note"],
                "note_texts": [note_text],
                "match_status": "matched",
            }
        ],
        "unmatched_assets": [],
    }

    md = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory=table_inventory,
        page_count=5,
        document_structure=None,
        reader_payload={},
    )

    assert note_text not in md
    assert "![[render/tables/table_001.md]]" in md
    assert "> **Table Caption:**" not in md
```

- [ ] **Step 4: Add cross-page consumed note test**

```python
def test_consumed_table_note_uses_actual_block_page_not_table_page() -> None:
    """Consumed key uses each block's real page, not table['page']."""
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured = [
        {
            "page": 6,
            "role": "table_caption",
            "text": "Table 1. Results.",
            "block_id": "p6_caption",
        },
        {
            "page": 7,
            "role": "body_paragraph",
            "text": "Note: cross-page table note.",
            "block_id": "p7_note",
        },
    ]

    table_inventory = {
        "tables": [
            {
                "page": 6,
                "caption_text": "Table 1. Results.",
                "has_asset": True,
                "consumed_block_ids": ["p6_caption", "p7_note"],
                "note_block_ids": ["p7_note"],
                "note_texts": ["Note: cross-page table note."],
                "match_status": "matched",
            }
        ],
        "unmatched_assets": [],
    }

    md = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={"matched_figures": [], "unmatched_assets": [], "unresolved_clusters": []},
        table_inventory=table_inventory,
        page_count=7,
        document_structure=None,
        reader_payload={},
    )

    # p7_note is consumed via key (7, "p7_note"), not (6, "p7_note")
    assert "Note: cross-page table note." not in md
```

- [ ] **Step 5: Run all 4 render tests**

Run: `python -m pytest tests/test_ocr_render.py::test_weak_match_caption_fallback_not_lost tests/test_ocr_render.py::test_consumed_table_note_skipped_before_role_skip tests/test_ocr_render.py::test_table_object_renderer_includes_footnote_note tests/test_ocr_render.py::test_consumed_table_note_uses_actual_block_page_not_table_page -v --tb=short`
Expected: all PASS.

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/unit/ tests/test_ocr_render.py tests/test_ocr_tables.py -v --tb=short`
Expected: 300+ passed.

- [ ] **Step 7: Commit**

```bash
git add tests/test_ocr_render.py
git commit -m "test: render contract for table ownership and note skip"
```
