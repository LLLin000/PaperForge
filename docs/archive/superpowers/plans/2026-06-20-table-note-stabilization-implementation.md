# Table Note Stabilization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize table-note ownership with page-footnote priors and note-band grouping, while improving bare `Table N` ambiguity resolution through stronger spatial tie-breaks.

**Architecture:** Keep OCR role classification unchanged and harden only the post-ownership table surface. The implementation adds a page-level footnote prior, groups note candidates into a local note band below matched tables, strengthens body exclusion, and upgrades bare `Table N` decisions through layout tie-breaks rather than freer caption admission.

**Tech Stack:** Python 3.14, `paperforge.worker.ocr_tables`, `ocr_objects`, `ocr_render`, `ocr_health`, pytest, rebuild verification on known residual and unseen papers.

---

## File Structure

- Modify: `paperforge/worker/ocr_tables.py`
  - Owns page-footnote prior, note-band grouping, note ownership output, and table ambiguity tie-breaks.
- Modify: `paperforge/worker/ocr_objects.py`
  - Owns projection of note-band metadata into table object markdown.
- Modify: `paperforge/worker/ocr_render.py`
  - Owns body-flow suppression for consumed table-note bands.
- Modify: `paperforge/worker/ocr_health.py`
  - Owns additive reporting only if table-note / ambiguity fields need audit surfacing.
- Modify: `tests/test_ocr_tables.py`
  - Primary unit coverage for page-footnote prior, note-band grouping, and bare `Table N` tie-breaks.
- Modify: `tests/test_ocr_objects.py`
  - Table object markdown note-band rendering coverage.
- Modify: `tests/test_ocr_rendering.py`
  - Consumed note-band suppression coverage.
- Modify: `PROJECT-MANAGEMENT.md`
  - Record the completed table-note stabilization slice and remaining hard cases.

---

### Task 1: Add Page-Footnote Prior And Note-Band Data Model

**Files:**
- Modify: `paperforge/worker/ocr_tables.py`
- Modify: `tests/test_ocr_tables.py`

- [ ] **Step 1: Add a failing test for page-footnote prior outranking table-note attachment at page bottom**

Append this test to `tests/test_ocr_tables.py`:

```python
def test_page_footnote_prior_prevents_table_at_page_bottom_from_absorbing_footer_note() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {"page": 4, "block_id": "p4_a1", "role": "table_asset", "raw_label": "table", "bbox": [80, 980, 760, 1280], "text": ""},
        {"page": 4, "block_id": "p4_c1", "role": "table_caption", "text": "Table 2. Results", "bbox": [80, 1295, 760, 1330]},
        {"page": 4, "block_id": "p4_fn1", "role": "footnote", "raw_label": "vision_footnote", "text": "* Correspondence footnote", "bbox": [80, 1365, 760, 1390]},
        {"page": 2, "block_id": "p2_fn1", "role": "footnote", "raw_label": "vision_footnote", "text": "* prior footer", "bbox": [70, 1360, 750, 1388]},
        {"page": 3, "block_id": "p3_fn1", "role": "footnote", "raw_label": "vision_footnote", "text": "* prior footer", "bbox": [72, 1362, 748, 1389]},
    ]

    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]

    assert table["note_block_ids"] == []
    assert table["note_match_reason"] == "page_footnote_prior_rejected"
```

- [ ] **Step 2: Add a failing test for multi-line note-band grouping below a matched table**

Append this test to `tests/test_ocr_tables.py`:

```python
def test_table_note_blocks_group_into_single_note_band() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {"page": 5, "block_id": "p5_a1", "role": "table_asset", "raw_label": "table", "bbox": [100, 100, 640, 430], "text": ""},
        {"page": 5, "block_id": "p5_c1", "role": "table_caption", "text": "Table 1. Main results", "bbox": [100, 445, 640, 475]},
        {"page": 5, "block_id": "p5_n1", "role": "footnote", "raw_label": "vision_footnote", "text": "* p < 0.05", "bbox": [110, 440, 520, 458]},
        {"page": 5, "block_id": "p5_n2", "role": "footnote", "raw_label": "vision_footnote", "text": "Data are mean ± SD.", "bbox": [110, 460, 560, 480]},
    ]

    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]

    assert table["note_block_ids"] == ["p5_n1", "p5_n2"]
    assert table["note_band_bbox"] == [110, 440, 560, 480]
    assert table["note_match_reason"] == "note_band_geometry_match"
```

- [ ] **Step 3: Run the red tests**

Run: `python -m pytest tests/test_ocr_tables.py -k "page_footnote_prior_prevents or note_band" -v`

Expected: FAIL because the current inventory does not compute a page-footnote prior or note-band bbox/reason.

- [ ] **Step 4: Implement page-footnote prior helpers in `ocr_tables.py`**

Add helpers near the top of `paperforge/worker/ocr_tables.py`:

```python
def _collect_page_footnote_prior(structured_blocks: list[dict]) -> dict[int, float]:
    prior_by_page: dict[int, float] = {}
    footer_tops: list[float] = []
    for block in structured_blocks:
        if str(block.get("role", "") or "") != "footnote" and str(block.get("raw_label", "") or "") != "vision_footnote":
            continue
        bbox = block.get("bbox") or [0, 0, 0, 0]
        if len(bbox) < 4:
            continue
        footer_tops.append(float(bbox[1]))
    if not footer_tops:
        return prior_by_page
    typical_top = min(footer_tops)
    for block in structured_blocks:
        page = int(block.get("page", 0) or 0)
        if page:
            prior_by_page[page] = typical_top
    return prior_by_page


def _table_note_falls_into_page_footnote_prior(note_bbox: list[float], page: int, prior_by_page: dict[int, float]) -> bool:
    if page not in prior_by_page or len(note_bbox) < 4:
        return False
    return float(note_bbox[1]) >= float(prior_by_page[page])
```

- [ ] **Step 5: Implement note-band grouping and new note contract fields**

Replace the single-block note collection path in `build_table_inventory()` with grouped note-band logic:

```python
        note_block_ids: list[str] = []
        note_texts: list[str] = []
        note_bboxes: list[list[float]] = []
        note_band_bbox: list[float] = []
        note_match_reason = ""
        note_confidence = 0.0

        page_footnote_prior = _collect_page_footnote_prior(structured_blocks)

        if matched_asset:
            asset_page = matched_asset.get("page", 0)
            asset_bbox = matched_asset.get("bbox", [0, 0, 0, 0])
            asset_bottom = asset_bbox[3] if len(asset_bbox) >= 4 else 0
            candidates: list[dict] = []
            for block in structured_blocks:
                if int(block.get("page", 0) or 0) != int(asset_page or 0):
                    continue
                bbbox = block.get("bbox") or [0, 0, 0, 0]
                if len(bbbox) < 4:
                    continue
                if bbbox[1] < asset_bottom or bbbox[1] > asset_bottom + 100:
                    continue
                if _table_note_falls_into_page_footnote_prior(bbbox, int(asset_page or 0), page_footnote_prior):
                    note_match_reason = "page_footnote_prior_rejected"
                    continue
                candidates.append(block)

            if candidates:
                candidates.sort(key=lambda b: (b.get("bbox") or [0, 0, 0, 0])[1])
                note_block_ids = [str(b.get("block_id", "")) for b in candidates if b.get("block_id")]
                note_texts = [str(b.get("text", "") or "").strip() for b in candidates if str(b.get("text", "") or "").strip()]
                note_bboxes = [b.get("bbox", [0, 0, 0, 0]) for b in candidates]
                note_band_bbox = [
                    min(bb[0] for bb in note_bboxes),
                    min(bb[1] for bb in note_bboxes),
                    max(bb[2] for bb in note_bboxes),
                    max(bb[3] for bb in note_bboxes),
                ]
                note_match_reason = "note_band_geometry_match"
                note_confidence = 0.85
```

Then emit:

```python
                "note_bboxes": note_bboxes,
                "note_band_bbox": note_band_bbox,
                "note_match_reason": note_match_reason,
                "note_confidence": note_confidence,
```

- [ ] **Step 6: Re-run the targeted tests**

Run: `python -m pytest tests/test_ocr_tables.py -k "page_footnote_prior_prevents or note_band" -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add paperforge/worker/ocr_tables.py tests/test_ocr_tables.py
git commit -m "feat: add page footnote prior for table note bands"
```

---

### Task 2: Add Body Exclusion And Object/Render Projection For Note Bands

**Files:**
- Modify: `paperforge/worker/ocr_tables.py`
- Modify: `paperforge/worker/ocr_objects.py`
- Modify: `paperforge/worker/ocr_render.py`
- Modify: `tests/test_ocr_objects.py`
- Modify: `tests/test_ocr_rendering.py`

- [ ] **Step 1: Add a failing object markdown test for note-band metadata**

Append to `tests/test_ocr_objects.py`:

```python
def test_table_object_markdown_renders_note_band_texts_in_notes_section() -> None:
    from paperforge.worker.ocr_objects import render_table_object_markdown

    md = render_table_object_markdown(
        {
            "table_id": "table_001",
            "page": 5,
            "caption": "Table 1. Results.",
            "image_relpath": "assets/tables/table_001.jpg",
            "note_texts": ["* p < 0.05", "Data are mean ± SD."],
            "note_match_reason": "note_band_geometry_match",
        }
    )

    assert "## Notes" in md
    assert "* p < 0.05" in md
    assert "Data are mean ± SD." in md
```

- [ ] **Step 2: Add a failing render test that consumed note-band blocks do not fall back into body flow**

Append to `tests/test_ocr_rendering.py`:

```python
def test_fulltext_skips_consumed_table_note_band_blocks() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {"page": 5, "block_id": "p5_c1", "role": "table_caption", "text": "Table 1. Main results", "bbox": [100, 430, 600, 460], "zone": "display_zone", "style_family": "table_caption_like"},
        {"page": 5, "block_id": "p5_n1", "role": "footnote", "text": "* p < 0.05", "bbox": [100, 470, 600, 490]},
        {"page": 5, "block_id": "p5_n2", "role": "footnote", "text": "Data are mean ± SD.", "bbox": [100, 492, 600, 512]},
    ]
    table_inventory = {
        "tables": [
            {
                "table_id": "table_001",
                "page": 5,
                "caption_block_id": "p5_c1",
                "asset_block_id": "p5_a1",
                "note_block_ids": ["p5_n1", "p5_n2"],
                "consumed_block_ids": ["p5_c1", "p5_a1", "p5_n1", "p5_n2"],
            }
        ]
    }

    md = render_fulltext_markdown(
        structured_blocks=structured_blocks,
        resolved_metadata={},
        figure_inventory={"matched_figures": []},
        table_inventory=table_inventory,
        page_count=5,
        document_structure=None,
        reader_payload={"figures": []},
    )

    assert "* p < 0.05" not in md
    assert "Data are mean ± SD." not in md
```

- [ ] **Step 3: Run the red tests**

Run: `python -m pytest tests/test_ocr_objects.py -k "note_band" tests/test_ocr_rendering.py -k "note_band_blocks" -v`

Expected: FAIL if note-band projection is incomplete.

- [ ] **Step 4: Strengthen body exclusion in `ocr_tables.py`**

Before finalizing a note band, reject candidates that look too much like body flow:

```python
def _looks_like_body_text_below_table(block: dict, table_bbox: list[float]) -> bool:
    bbox = block.get("bbox") or [0, 0, 0, 0]
    if len(bbox) < 4 or len(table_bbox) < 4:
        return False
    block_width = bbox[2] - bbox[0]
    table_width = table_bbox[2] - table_bbox[0]
    text = str(block.get("text", "") or "").strip()
    return block_width >= table_width * 0.9 and len(text.split()) >= 12
```

Use it to exclude likely body blocks from the note band.

- [ ] **Step 5: Keep object/render projection aligned with the note-band contract**

Ensure:

```python
# ocr_objects.py
note_texts = [normalize_ocr_math_text(t) for t in table.get("note_texts", []) if t]

# ocr_render.py
consumed_table_block_ids.update(table.get("consumed_block_ids", []))
```

No new semantic classification should be added in render.

- [ ] **Step 6: Re-run the targeted tests**

Run: `python -m pytest tests/test_ocr_objects.py -k "note_band" tests/test_ocr_rendering.py -k "note_band_blocks" -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add paperforge/worker/ocr_tables.py paperforge/worker/ocr_objects.py paperforge/worker/ocr_render.py tests/test_ocr_objects.py tests/test_ocr_rendering.py
git commit -m "fix: project table note bands through object and render"
```

---

### Task 3: Continue Bare `Table N` Stabilization With Stronger Tie-Breaks

**Files:**
- Modify: `paperforge/worker/ocr_tables.py`
- Modify: `tests/test_ocr_tables.py`

- [ ] **Step 1: Add a failing same-page tie-break test**

Append to `tests/test_ocr_tables.py`:

```python
def test_bare_table_number_prefers_candidate_with_better_x_overlap_and_shorter_vertical_gap() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {"page": 6, "block_id": "p6_a1", "role": "table_asset", "raw_label": "table", "bbox": [100, 200, 600, 500], "text": ""},
        {"page": 6, "block_id": "p6_a2", "role": "table_asset", "raw_label": "table", "bbox": [620, 120, 980, 520], "text": ""},
        {"page": 6, "block_id": "p6_c1", "role": "table_caption", "text": "Table 3", "bbox": [100, 520, 600, 545]},
    ]

    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]

    assert table["asset_block_id"] == "p6_a1"
    assert table["match_status"] in {"matched", "matched_low_confidence"}
```

- [ ] **Step 2: Add a failing continuation-page test**

Append to `tests/test_ocr_tables.py`:

```python
def test_bare_table_number_can_match_previous_page_continuation_under_strong_geometry() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {"page": 7, "block_id": "p7_a1", "role": "table_asset", "raw_label": "table", "bbox": [100, 120, 640, 1000], "text": ""},
        {"page": 8, "block_id": "p8_c1", "role": "table_caption", "text": "Table 4", "bbox": [100, 90, 640, 120]},
    ]

    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]

    assert table["match_status"] in {"matched_low_confidence", "matched"}
    assert table["asset_block_id"] == "p7_a1"
```

- [ ] **Step 3: Run the red tests**

Run: `python -m pytest tests/test_ocr_tables.py -k "prefers_candidate_with_better_x_overlap or continuation_under_strong_geometry" -v`

Expected: FAIL because the current same-page tie-break is not strong enough and continuation handling is too conservative.

- [ ] **Step 4: Improve tie-break scoring in `ocr_tables.py`**

Add a helper to rank bare-table candidates after the base scorer runs:

```python
def _bare_table_tie_break(score: dict, caption: dict, asset: dict) -> tuple[float, float, float]:
    cb = caption.get("bbox") or [0, 0, 0, 0]
    ab = asset.get("bbox") or [0, 0, 0, 0]
    x_overlap = min(cb[2], ab[2]) - max(cb[0], ab[0]) if len(cb) >= 4 and len(ab) >= 4 else 0.0
    vertical_gap = max(0.0, cb[1] - ab[3]) if len(cb) >= 4 and len(ab) >= 4 else 9999.0
    return (float(score.get("score", 0.0)), float(x_overlap), -float(vertical_gap))
```

Use this tuple as a secondary sort key for weak explicit captions after `score_table_match` runs.

- [ ] **Step 5: Allow a continuation-specific geometry path for bare `Table N`**

If a candidate asset is on the previous page and:

- x overlap is high,
- the asset extends near the previous page bottom,
- the caption sits at the next page top,

allow `matched_low_confidence` rather than forcing `ambiguous`.

Keep this path narrower than same-page matching.

- [ ] **Step 6: Re-run the targeted tests**

Run: `python -m pytest tests/test_ocr_tables.py -k "prefers_candidate_with_better_x_overlap or continuation_under_strong_geometry" -v`

Expected: PASS.

- [ ] **Step 7: Run the full table suite**

Run: `python -m pytest tests/test_ocr_tables.py -v --tb=short`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add paperforge/worker/ocr_tables.py tests/test_ocr_tables.py
git commit -m "fix: improve bare table ambiguity tie-breaks"
```

---

### Task 4: Validate On Residual And Unseen Papers, Then Record The Slice

**Files:**
- Modify: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Rebuild a residual sample set after the table-note changes**

Run:

```bash
python -m paperforge --vault "D:\L\OB\Literature-hub" ocr rebuild --clear-checkpoint
python -m paperforge --vault "D:\L\OB\Literature-hub" ocr rebuild 69TA9S8W 4PFR9M5N 7I4YGKFG A8E7SRVS X5FJTVGP VZMMSJBS X3NTXX4M
```

Expected: rebuild completes without introducing a new failure family.

- [ ] **Step 2: Verify table-note and ambiguity metrics from generated artifacts**

Check these artifact expectations manually or with a small script:

- no blockquote table captions in fulltext,
- note-band fields present where note ownership exists,
- some previously ambiguous bare `Table N` cases now become `matched_low_confidence` or `matched`,
- page-bottom footer notes are not greedily absorbed.

- [ ] **Step 3: Update `PROJECT-MANAGEMENT.md` with the completed slice**

Append a new section:

```md
### 11.4 Table Note Stabilization + Table Ambiguity Slice (2026-06-20)

**Problem:** Table notes still risked confusion with page footnotes and body text, while bare `Table N` captions still stayed overly ambiguous after the first rebuild-hardening pass.

**Root cause:** The table surface lacked a page-footnote prior, grouped note-band ownership, and stronger layout tie-breaks among already-accepted table candidates.

**Fix:** Added page-footnote priors, table-below note-band grouping, body exclusion, explicit note-band contract fields, and stronger same-page / continuation tie-breaks for bare `Table N`.

**Result:** Table-note ownership is more stable, page-bottom footer notes are less likely to be absorbed, and table ambiguity is reduced through geometry rather than freer caption admission.

**Validation:** Rebuilt residual and unseen papers after the change; no new failure family introduced.
```

- [ ] **Step 4: Commit**

```bash
git add PROJECT-MANAGEMENT.md
git commit -m "docs: record table note stabilization slice"
```

---

## Self-Review Notes

- Spec coverage: this plan covers page-footnote priors, note-band grouping, body exclusion, stronger bare `Table N` tie-breaks, and residual/unseen-paper validation.
- Scope discipline: figure ownership and merge growth are explicitly deferred to the second design thread.
