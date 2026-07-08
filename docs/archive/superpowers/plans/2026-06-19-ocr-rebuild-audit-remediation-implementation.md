# OCR Rebuild Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the highest-value rebuild-output defects from the 452-paper audit without reopening OCR-v2 role-classification architecture or adding free-form text rescue logic.

**Architecture:** Keep the anchor-first OCR-v2 backbone intact and harden only the post-structure surfaces: ownership write-through, render projection, figure/table inventory contracts, and additive health semantics. The plan starts with visible output pollution, then makes ownership authoritative, then tightens figure/table contracts, and only then adds backward-compatible health/reference semantics.

**Tech Stack:** Python 3.14, `paperforge.worker` OCR pipeline, pytest, repo-local audit docs, existing OCR fixture/unit/regression tests.

**Execution Status:** completed on `ocr-v2` via subagent-driven execution

---

## File Structure

- Modify: `paperforge/worker/ocr_tables.py`
  - Owns table caption matching, table-asset ownership, table-note ownership, and consumed-table-block contract emission.
- Modify: `paperforge/worker/ocr_objects.py`
  - Must consume owned table notes and render them into table object markdown.
- Modify: `paperforge/worker/ocr_render.py`
  - Must skip already-consumed table-note blocks, stop duplicating table captions into fulltext, and tighten reference ordering.
- Modify: `paperforge/worker/ocr_health.py`
  - Must add corrected counts and additive v2 semantics without breaking the current top-level surface.
- Modify: `paperforge/worker/ocr_figures.py`
  - Owns figure namespace split, gated `page_assets`, and clearer ownership outcomes.
- Modify: `tests/test_ocr_tables.py`
  - Table-note ownership and bare `Table N` contract coverage.
- Modify: `tests/test_ocr_objects.py`
  - Table object markdown note rendering coverage.
- Modify: `tests/test_ocr_rendering.py`
  - Fulltext table-caption suppression and consumed-note skipping coverage.
- Modify: `tests/test_ocr_figures.py`
  - Namespace split and `page_assets` strict-gate coverage.
- Modify: `tests/test_ocr_health.py`
  - Heading-count, `references_found`, and additive health-v2 field coverage.
- Modify: `PROJECT-MANAGEMENT.md`
  - Record each landed remediation batch and any deliberately deferred hard cases.

---

### Task 1: Make Table-Note Ownership Reach Object Markdown And Skip Body Flow

**Files:**
- Modify: `paperforge/worker/ocr_tables.py`
- Modify: `paperforge/worker/ocr_objects.py`
- Modify: `paperforge/worker/ocr_render.py`
- Modify: `tests/test_ocr_tables.py`
- Modify: `tests/test_ocr_objects.py`
- Modify: `tests/test_ocr_rendering.py`

- [ ] **Step 1: Add a failing table-inventory contract test for note payload and consumed ids**

Append this test to `tests/test_ocr_tables.py` near the existing note-binding coverage:

```python
def test_table_inventory_emits_note_payload_and_consumed_block_ids() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "page": 5,
            "block_id": "p5_a1",
            "role": "table_asset",
            "text": "table data",
            "bbox": [100, 100, 600, 400],
        },
        {
            "page": 5,
            "block_id": "p5_c1",
            "role": "table_caption",
            "text": "Table 1. Main results",
            "bbox": [100, 420, 600, 460],
        },
        {
            "page": 5,
            "block_id": "p5_n1",
            "role": "footnote",
            "raw_label": "vision_footnote",
            "text": "* p < 0.05",
            "bbox": [100, 405, 600, 425],
        },
    ]

    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]

    assert table["note_block_ids"] == ["p5_n1"]
    assert table["note_texts"] == ["* p < 0.05"]
    assert set(table["consumed_block_ids"]) == {"p5_a1", "p5_c1", "p5_n1"}
```

- [ ] **Step 2: Add a failing table-object markdown test for rendered notes**

Append this test to `tests/test_ocr_objects.py` after the existing table markdown coverage:

```python
def test_table_object_markdown_renders_owned_notes() -> None:
    from paperforge.worker.ocr_objects import render_table_object_markdown

    md = render_table_object_markdown(
        {
            "table_id": "table_001",
            "page": 5,
            "caption": "Table 1. Results.",
            "image_relpath": "assets/tables/table_001.jpg",
            "note_texts": ["* p < 0.05", "Data are mean ± SD."],
        }
    )

    assert "## Notes" in md
    assert "* p < 0.05" in md
    assert "Data are mean ± SD." in md
```

- [ ] **Step 3: Add a failing fulltext test showing consumed note blocks do not render as body text**

Append this test to `tests/test_ocr_rendering.py`:

```python
def test_fulltext_skips_table_note_blocks_consumed_by_inventory() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "page": 5,
            "block_id": "p5_c1",
            "role": "table_caption",
            "text": "Table 1. Main results",
            "bbox": [100, 420, 600, 460],
            "zone": "display_zone",
            "style_family": "table_caption_like",
        },
        {
            "page": 5,
            "block_id": "p5_n1",
            "role": "footnote",
            "text": "* p < 0.05",
            "bbox": [100, 405, 600, 425],
        },
    ]
    table_inventory = {
        "tables": [
            {
                "table_id": "table_001",
                "page": 5,
                "caption_block_id": "p5_c1",
                "caption_text": "Table 1. Main results",
                "asset_block_id": "p5_a1",
                "note_block_ids": ["p5_n1"],
                "note_texts": ["* p < 0.05"],
                "consumed_block_ids": ["p5_a1", "p5_c1", "p5_n1"],
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
```

- [ ] **Step 4: Run the targeted red tests**

Run: `python -m pytest tests/test_ocr_tables.py -k "note_payload_and_consumed_block_ids" -v`

Run: `python -m pytest tests/test_ocr_objects.py -k "renders_owned_notes" -v`

Run: `python -m pytest tests/test_ocr_rendering.py -k "consumed_by_inventory" -v`

Expected: all three FAIL because `note_texts` / `consumed_block_ids` / render skipping do not exist yet.

- [ ] **Step 5: Implement the table-note ownership contract in `ocr_tables.py`**

Update the table append block in `paperforge/worker/ocr_tables.py` so note text and consumed ids are emitted alongside ids:

```python
        note_block_ids: list[str] = []
        note_texts: list[str] = []
        if matched_asset:
            asset_page = matched_asset.get("page", 0)
            asset_bbox = matched_asset.get("bbox", [0, 0, 0, 0])
            asset_bottom = asset_bbox[3] if len(asset_bbox) >= 4 else 0
            for block in structured_blocks:
                bpage = block.get("page", 0)
                if bpage != asset_page:
                    continue
                brole = str(block.get("role", "") or "")
                braw_label = str(block.get("raw_label", "") or "").strip()
                btext = str(block.get("text", "") or "").strip()
                bbbox = block.get("bbox", [0, 0, 0, 0])
                if len(bbbox) < 4:
                    continue
                is_note = brole == "footnote" or braw_label == "vision_footnote"
                if not is_note:
                    continue
                note_top = bbbox[1]
                if asset_bottom <= note_top <= asset_bottom + 80:
                    note_block_ids.append(block.get("block_id", ""))
                    if btext:
                        note_texts.append(btext)

        consumed_block_ids = [caption.get("block_id", "")]
        if matched_asset:
            consumed_block_ids.append(matched_asset.get("block_id", ""))
        consumed_block_ids.extend(note_block_ids)
        consumed_block_ids = [bid for bid in consumed_block_ids if bid]

        tables.append(
            {
                "caption_block_id": caption.get("block_id", ""),
                "page": caption_page,
                "caption_text": caption_text,
                "table_number": table_num,
                "formal_table_number": formal_table_number,
                "asset_block_id": matched_asset.get("block_id", "") if matched_asset else "",
                "asset_bbox": matched_asset.get("bbox", [0, 0, 0, 0]) if matched_asset else [],
                "has_asset": matched_asset is not None,
                "note_block_ids": note_block_ids,
                "note_texts": note_texts,
                "consumed_block_ids": consumed_block_ids,
                "match_status": match_status,
            }
        )
```

- [ ] **Step 6: Implement note rendering in `ocr_objects.py`**

Update `render_table_object_markdown()` in `paperforge/worker/ocr_objects.py`:

```python
def render_table_object_markdown(table: dict[str, Any]) -> str:
    caption = table.get("caption", "")
    image_relpath = table.get("image_relpath", "")
    note_texts = [normalize_ocr_math_text(t) for t in table.get("note_texts", []) if t]
    formal_num = table.get("formal_table_number")
    label = f"Table {formal_num}" if formal_num is not None else f"Table {table.get('table_id', 'unknown')}"
    parts = [f"# {label}", "", f"![](../../{image_relpath})", ""]
    if caption:
        parts.append("## Caption")
        parts.append(normalize_ocr_math_text(caption))
    if note_texts:
        parts.append("")
        parts.append("## Notes")
        parts.extend(note_texts)
    return "\n".join(parts)
```

- [ ] **Step 7: Implement consumed-note skipping in `ocr_render.py`**

Near the existing consumed-caption handling in `render_fulltext_markdown()`, build consumed table block ids and skip them before body projection:

```python
    consumed_table_block_ids = set()
    for table in table_inventory.get("tables", []):
        for block_id in table.get("consumed_block_ids", []):
            if block_id:
                consumed_table_block_ids.add(block_id)

    block_id = block.get("block_id")
    if block_id is not None and block_id in consumed_table_block_ids:
        continue
```

- [ ] **Step 8: Re-run the targeted tests**

Run: `python -m pytest tests/test_ocr_tables.py -k "note_payload_and_consumed_block_ids" -v`

Run: `python -m pytest tests/test_ocr_objects.py -k "renders_owned_notes" -v`

Run: `python -m pytest tests/test_ocr_rendering.py -k "consumed_by_inventory" -v`

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add paperforge/worker/ocr_tables.py paperforge/worker/ocr_objects.py paperforge/worker/ocr_render.py tests/test_ocr_tables.py tests/test_ocr_objects.py tests/test_ocr_rendering.py
git commit -m "fix: carry owned table notes through rebuild outputs"
```

---

### Task 2: Remove Table-Caption Duplication And Count All Heading Tiers

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Modify: `paperforge/worker/ocr_health.py`
- Modify: `tests/test_ocr_rendering.py`
- Modify: `tests/test_ocr_health.py`

- [ ] **Step 1: Add a failing render test that display-zone table captions do not emit blockquotes**

Append to `tests/test_ocr_rendering.py`:

```python
def test_display_zone_table_caption_only_emits_embed_not_blockquote() -> None:
    from paperforge.worker.ocr_render import render_fulltext_markdown

    structured_blocks = [
        {
            "page": 5,
            "block_id": "p5_c1",
            "role": "table_caption",
            "text": "Table 1. Main results",
            "bbox": [100, 420, 600, 460],
            "zone": "display_zone",
            "style_family": "table_caption_like",
        }
    ]
    table_inventory = {
        "tables": [
            {
                "table_id": "table_001",
                "page": 5,
                "caption_block_id": "p5_c1",
                "caption_text": "Table 1. Main results",
                "asset_block_id": "p5_a1",
                "consumed_block_ids": ["p5_c1", "p5_a1"],
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

    assert "> **Table 1. Main results**" not in md
    assert "![[render/tables/table_001.md]]" in md
```

- [ ] **Step 2: Add a failing health test for multi-tier heading count and stricter references**

Append to `tests/test_ocr_health.py`:

```python
def test_health_counts_all_heading_tiers_and_requires_stronger_reference_evidence() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    structured_blocks = [
        {"role": "section_heading", "text": "Intro"},
        {"role": "subsection_heading", "text": "Methods"},
        {"role": "sub_subsection_heading", "text": "2.1 Setup"},
        {"role": "body_paragraph", "raw_label": "reference_content", "text": "[1] weak raw label"},
    ]

    health = build_ocr_health(
        page_count=1,
        raw_blocks_count=4,
        structured_blocks=structured_blocks,
        figure_inventory={"matched_figures": [], "held_figures": [], "unmatched_legends": [], "unmatched_assets": [], "figure_legend_completeness": {}},
        table_inventory={"tables": [], "held_tables": [], "unmatched_captions": [], "unmatched_assets": []},
        doc_structure={"reference_zone": {"status": "HOLD"}},
        reader_payload=None,
        rendered_markdown=None,
    )

    assert health["section_heading_count"] == 3
    assert health["references_found"] is False
```

- [ ] **Step 3: Run the targeted red tests**

Run: `python -m pytest tests/test_ocr_rendering.py -k "table_caption_only_emits_embed" -v`

Run: `python -m pytest tests/test_ocr_health.py -k "counts_all_heading_tiers" -v`

Expected: FAIL.

- [ ] **Step 4: Implement display-zone table-caption suppression in `ocr_render.py`**

Replace the `table_caption` branch in `paperforge/worker/ocr_render.py` with a pure embed path for display-zone/table-caption-like tables:

```python
        elif role == "table_caption":
            tbl_ids_for_page = tables_by_page.get(block_page, [])
            if tbl_ids_for_page:
                tbl_id = tbl_ids_for_page.pop(0)
                lines.append(f"![[render/tables/{tbl_id}.md]]")
                lines.append("")
            elif text:
                lines.append(f"### {text}")
                lines.append("")
```

- [ ] **Step 5: Implement corrected heading and reference semantics in `ocr_health.py`**

Update the health counters in `paperforge/worker/ocr_health.py`:

```python
    heading_roles = {"section_heading", "subsection_heading", "sub_subsection_heading"}
    section_heading_count = sum(1 for b in structured_blocks if b.get("role") in heading_roles)

    reference_zone = (doc_structure or {}).get("reference_zone", {}) if isinstance(doc_structure, dict) else {}
    reference_zone_status = str(reference_zone.get("status") or "")
    reference_item_count = sum(1 for b in structured_blocks if b.get("role") == "reference_item")
    references_found = reference_zone_status == "ACCEPT" or reference_item_count > 0
```

- [ ] **Step 6: Re-run the targeted tests**

Run: `python -m pytest tests/test_ocr_rendering.py -k "table_caption_only_emits_embed" -v`

Run: `python -m pytest tests/test_ocr_health.py -k "counts_all_heading_tiers" -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add paperforge/worker/ocr_render.py paperforge/worker/ocr_health.py tests/test_ocr_rendering.py tests/test_ocr_health.py
git commit -m "fix: clean table projection and health heading semantics"
```

---

### Task 3: Tighten Bare `Table N` Matching Without Text Rescue

**Files:**
- Modify: `paperforge/worker/ocr_tables.py`
- Modify: `tests/test_ocr_tables.py`

- [ ] **Step 1: Add a failing positive contract test for bare `Table N` under strong geometry**

Append to `tests/test_ocr_tables.py`:

```python
def test_bare_table_number_matches_when_geometry_and_table_evidence_are_strong() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {
            "page": 5,
            "block_id": "p5_a1",
            "role": "table_asset",
            "raw_label": "table",
            "bbox": [100, 100, 600, 400],
            "text": "",
        },
        {
            "page": 5,
            "block_id": "p5_c1",
            "role": "table_caption",
            "text": "Table 1",
            "bbox": [100, 420, 600, 450],
        },
    ]

    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]
    assert table["has_asset"] is True
    assert table["asset_block_id"] == "p5_a1"
```

- [ ] **Step 2: Add a failing negative contract test for nearby competing assets**

Append to `tests/test_ocr_tables.py`:

```python
def test_bare_table_number_stays_ambiguous_when_competing_assets_are_close() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {"page": 5, "block_id": "p5_a1", "role": "table_asset", "raw_label": "table", "bbox": [100, 100, 430, 400], "text": ""},
        {"page": 5, "block_id": "p5_a2", "role": "table_asset", "raw_label": "table", "bbox": [450, 100, 780, 400], "text": ""},
        {"page": 5, "block_id": "p5_c1", "role": "table_caption", "text": "Table 1", "bbox": [100, 420, 780, 450]},
    ]

    inventory = build_table_inventory(structured_blocks)
    table = inventory["tables"][0]
    assert table["has_asset"] is False
    assert table["match_status"] == "ambiguous"
```

- [ ] **Step 3: Run the red table tests**

Run: `python -m pytest tests/test_ocr_tables.py -k "bare_table_number" -v`

Expected: first FAILS because bare captions are currently treated as weak; second may FAIL if the implementation accepts too eagerly.

- [ ] **Step 4: Implement a geometry-only exception for weak explicit table captions**

Refactor the weak-caption path in `paperforge/worker/ocr_tables.py` so bare `Table N` can proceed only under the strict contract:

```python
def _can_match_bare_table_number(caption: dict, top_candidate: dict | None, second_score: float) -> bool:
    if top_candidate is None:
        return False
    if str(caption.get("role") or "") not in {"table_caption", "table_caption_candidate"} and not _is_validation_first_table_candidate(caption):
        return False
    if top_candidate.get("matched_asset_id") == "":
        return False
    if top_candidate.get("score", 0.0) < 0.75:
        return False
    if top_candidate.get("score", 0.0) - second_score < 0.2:
        return False
    evidence = set(top_candidate.get("evidence", []))
    return {"same_page", "x_overlap", "asset_above_caption"}.issubset(evidence) or {"previous_page_continuation", "x_overlap"}.issubset(evidence)
```

Then use that helper instead of unconditional weak-caption rejection.

- [ ] **Step 5: Re-run the bare-caption tests**

Run: `python -m pytest tests/test_ocr_tables.py -k "bare_table_number" -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_tables.py tests/test_ocr_tables.py
git commit -m "fix: gate bare table-number matching on strong geometry"
```

---

### Task 4: Split Figure Namespace And Gate `page_assets`

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `tests/test_ocr_figures.py`
- Modify: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Add a failing unit test for namespace separation**

Append to `tests/test_ocr_figures.py`:

```python
def test_main_and_supplementary_figures_do_not_dedup_into_one_number() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {"page": 3, "block_id": "p3_c1", "role": "figure_caption", "text": "Figure 1. Main figure.", "bbox": [100, 420, 600, 460]},
        {"page": 3, "block_id": "p3_a1", "role": "figure_asset", "bbox": [100, 100, 600, 400], "text": ""},
        {"page": 4, "block_id": "p4_c1", "role": "figure_caption", "text": "Supplementary Figure S1. Supplement.", "bbox": [100, 420, 600, 460]},
        {"page": 4, "block_id": "p4_a1", "role": "figure_asset", "bbox": [100, 100, 600, 400], "text": ""},
    ]

    inventory = build_figure_inventory(structured_blocks)
    figure_ids = {fig["figure_id"] for fig in inventory["matched_figures"]}
    assert "figure_001" in figure_ids
    assert "figure_s001" in figure_ids
```

- [ ] **Step 2: Add a failing unit test that `page_assets` does not strict-match when competing captions exist**

Append to `tests/test_ocr_figures.py`:

```python
def test_page_assets_group_does_not_strict_match_when_page_has_competing_captions() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {"page": 5, "block_id": "p5_a1", "role": "figure_asset", "raw_label": "image", "bbox": [100, 100, 300, 260], "text": ""},
        {"page": 5, "block_id": "p5_a2", "role": "figure_asset", "raw_label": "image", "bbox": [320, 100, 520, 260], "text": ""},
        {"page": 5, "block_id": "p5_a3", "role": "figure_asset", "raw_label": "image", "bbox": [540, 100, 740, 260], "text": ""},
        {"page": 5, "block_id": "p5_c1", "role": "figure_caption", "text": "Figure 1. Left.", "bbox": [100, 280, 320, 320], "zone": "display_zone", "style_family": "legend_like"},
        {"page": 5, "block_id": "p5_c2", "role": "figure_caption", "text": "Figure 2. Right.", "bbox": [420, 280, 740, 320], "zone": "display_zone", "style_family": "legend_like"},
    ]

    inventory = build_figure_inventory(structured_blocks)
    assert all("page_assets_group" not in fig.get("confidence_reason", "") for fig in inventory["matched_figures"])
```

- [ ] **Step 3: Run the red figure tests**

Run: `python -m pytest tests/test_ocr_figures.py -k "supplementary_figures_do_not_dedup or page_assets_group_does_not_strict_match" -v`

Expected: FAIL.

- [ ] **Step 4: Implement namespace-aware figure identity in `ocr_figures.py`**

Introduce a namespace extractor and use it in id/dedup logic:

```python
def _extract_figure_namespace(text: str) -> str:
    lower = text.lower()
    if "supplementary" in lower:
        return "supplementary"
    if "extended data" in lower:
        return "extended_data"
    return "main"


def _format_figure_id(namespace: str, number: int) -> str:
    if namespace == "supplementary":
        return f"figure_s{number:03d}"
    if namespace == "extended_data":
        return f"figure_ed{number:03d}"
    return f"figure_{number:03d}"
```

Then replace integer-only dedup keys with `(namespace, number)` tuples.

- [ ] **Step 5: Gate `page_assets` strict matching**

In `paperforge/worker/ocr_figures.py`, only allow `page_assets` to return a strict matched score when one of the explicit gates is true; otherwise return a reader-level/non-strict decision:

```python
    if gt == "page_assets":
        if not group.get("strict_page_assets_ok", False):
            return {
                "score": 0.0,
                "decision": "grouped_evidence_only",
                "evidence": ["same_page", "page_assets_group", "non_strict_only"],
            }
```

Populate `strict_page_assets_ok` when:

- there is exactly one formal figure legend on the page, or
- expected panel count closely matches asset count, or
- no competing figure/table captions exist on the page.

- [ ] **Step 6: Re-run the targeted figure tests**

Run: `python -m pytest tests/test_ocr_figures.py -k "supplementary_figures_do_not_dedup or page_assets_group_does_not_strict_match" -v`

Expected: PASS.

- [ ] **Step 7: Run the existing real-paper regression protecting against page swallowing**

Run: `python -m pytest tests/test_ocr_real_paper_regressions.py -k "mega_merges_same_page_assets" -v`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add paperforge/worker/ocr_figures.py tests/test_ocr_figures.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: split figure namespace and gate page asset grouping"
```

---

### Task 5: Add Health V2 Fields And Land The Batch Documentation Update

**Files:**
- Modify: `paperforge/worker/ocr_health.py`
- Modify: `tests/test_ocr_health.py`
- Modify: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Add a failing health-v2 test for additive fields**

Append to `tests/test_ocr_health.py`:

```python
def test_health_emits_additive_v2_fields_without_replacing_overall() -> None:
    from paperforge.worker.ocr_health import build_ocr_health

    health = build_ocr_health(
        page_count=1,
        raw_blocks_count=0,
        structured_blocks=[{"role": "section_heading", "text": "Intro"}],
        figure_inventory={"matched_figures": [], "held_figures": [], "unmatched_legends": [], "unmatched_assets": [], "figure_legend_completeness": {}},
        table_inventory={"tables": [], "held_tables": [], "unmatched_captions": [], "unmatched_assets": []},
        doc_structure={"reference_zone": {"status": "ACCEPT"}},
        reader_payload=None,
        rendered_markdown=None,
    )

    assert "overall" in health
    assert "heading_total_v2" in health
    assert "matched_figure_count_v2" in health
    assert "issue_breakdown_v2" in health
```

- [ ] **Step 2: Run the red test**

Run: `python -m pytest tests/test_ocr_health.py -k "emits_additive_v2_fields" -v`

Expected: FAIL.

- [ ] **Step 3: Implement additive v2 fields in `ocr_health.py`**

Add the corrected fields near the existing return payload in `paperforge/worker/ocr_health.py`:

```python
    issue_breakdown_v2 = {
        "caption_without_media": caption_without_media,
        "media_without_caption": media_without_caption,
        "empty_tables": empty_tables,
        "abstract_found": abstract_found,
        "references_found": references_found,
        "heading_total": section_heading_count,
        "formal_legend_gaps": formal_legend_gaps,
    }

    return {
        "overall": overall,
        "section_heading_count": section_heading_count,
        "references_found": references_found,
        "heading_total_v2": section_heading_count,
        "matched_figure_count_v2": len(figure_inventory.get("matched_figures", [])),
        "issue_breakdown_v2": issue_breakdown_v2,
        "figure_asset_count": figure_asset_count,
    }
```

- [ ] **Step 4: Re-run the targeted v2 health test**

Run: `python -m pytest tests/test_ocr_health.py -k "emits_additive_v2_fields" -v`

Expected: PASS.

- [ ] **Step 5: Record the completed remediation batches in `PROJECT-MANAGEMENT.md`**

Append a new section using the repo’s established format:

```md
### 11.2 OCR Rebuild Audit Remediation Batch 1 (2026-06-19)

**Problem:** Full rebuild outputs still leaked owned table notes into body flow, duplicated table captions in fulltext, and overstated health defects through weak heading/reference semantics.

**Root cause:** Ownership evidence stopped at inventory fields; render and health still relied on shallow projection/proxy logic.

**Fix:** Carried table-note ownership through inventory/object/render surfaces, removed display-zone table-caption duplication, counted all heading tiers, and added additive health-v2 counters.

**Result:** Fulltext is cleaner, table objects retain owned notes, and health artifacts are more interpretable without replacing the top-level compatibility surface.

**Test status:** `python -m pytest tests/test_ocr_tables.py tests/test_ocr_objects.py tests/test_ocr_rendering.py tests/test_ocr_figures.py tests/test_ocr_health.py -v --tb=short`
```

- [ ] **Step 6: Run the focused regression suite for this plan slice**

Run: `python -m pytest tests/test_ocr_tables.py tests/test_ocr_objects.py tests/test_ocr_rendering.py tests/test_ocr_figures.py tests/test_ocr_health.py -v --tb=short`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add paperforge/worker/ocr_health.py tests/test_ocr_health.py PROJECT-MANAGEMENT.md
git commit -m "feat: add additive rebuild health semantics"
```

---

## Self-Review Notes

- Spec coverage: this plan covers Phase A pollution fixes, ownership write-through, bare `Table N` hardening, namespace split, `page_assets` gates, and additive health-v2 semantics.
- Intentional deferral: full figure/table cross-arbitration beyond current inventory seams and major overall-score replacement are not included here.
- No placeholders rule: all code steps, tests, commands, doc edits, and project-management text are specified directly.
