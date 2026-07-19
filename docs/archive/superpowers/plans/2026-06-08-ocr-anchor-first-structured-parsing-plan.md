# OCR Anchor-First Structured Parsing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the OCR worker from eager role assignment into an anchor-first pipeline where signatures, body/reference family anchors, zone inference, family partition, and late role resolution happen in that order while preserving external artifacts.

**Architecture:** Keep current OCR entrypoints and user-facing outputs, but change the semantic decision order. The implementation should first emit observation/signature artifacts, then derive `body_family_anchor` and `reference_family_anchor`, then infer zones, then partition families inside zones, then resolve final roles, and only then run validation-first figure/table matching. Compatibility wiring is split from the final role switch to avoid a one-shot rewrite.

**Tech Stack:** Python 3, PyMuPDF (`fitz`), existing PaperForge worker modules (`ocr_blocks.py`, `ocr_document.py`, `ocr_roles.py`, `ocr_figures.py`, `ocr_tables.py`, `ocr_profiles.py`, `ocr_health.py`), pytest.

---

## File Map

- Create: `paperforge/worker/ocr_signatures.py`
  - Raw observation, marker, span, and layout signature extraction.
- Create: `paperforge/worker/ocr_families.py`
  - Body/reference family anchor discovery and in-zone family partition.
- Modify: `paperforge/worker/ocr_blocks.py`
  - Pipeline orchestration; temporary compatibility glue during migration.
- Modify: `paperforge/worker/ocr_metadata.py`
  - Source-backed frontmatter localization promoted to an early anchor stage.
- Modify: `paperforge/worker/ocr_document.py`
  - Zone inference / region bus / boundary-band logic, with reference-first tail protection.
- Modify: `paperforge/worker/ocr_roles.py`
  - Demote eager `assign_block_role()` usage; add late context-based resolution entrypoint.
- Modify: `paperforge/worker/ocr_figures.py`
  - Validation-first figure matching driven by anchors/zones/families.
- Modify: `paperforge/worker/ocr_tables.py`
  - Validation-first table matching driven by anchors/zones/families.
- Modify: `paperforge/worker/ocr_health.py`
  - Anchor/zone/family/match status reporting.
- Modify: `tests/test_ocr_metadata.py`
- Modify: `tests/test_ocr_document.py`
- Modify: `tests/test_ocr_roles.py`
- Modify: `tests/test_ocr_figures.py`
- Modify: `tests/test_ocr_tables.py`
- Modify: `tests/test_ocr_health.py`
- Create: `tests/test_ocr_signatures.py`
- Create: `tests/test_ocr_families.py`
- Modify: `tests/test_ocr_integration_fixtures.py`
- Modify: `tests/test_ocr_real_paper_regressions.py`

---

### Task 1: Add structural signatures with no semantic role commitment

**Files:**
- Create: `paperforge/worker/ocr_signatures.py`
- Modify: `paperforge/worker/ocr_blocks.py`
- Test: `tests/test_ocr_signatures.py`
- Test: `tests/test_ocr_blocks.py`

- [ ] **Step 1: Write the failing test**

```python
def test_block_signature_extraction_preserves_observation_without_final_role():
    from paperforge.worker.ocr_signatures import build_block_signatures

    block = {
        "block_id": "p2_b14",
        "page": 2,
        "raw_label": "paragraph_title",
        "text": "III. RESULTS AND DISCUSSION",
        "bbox": [207, 141, 504, 162],
        "span_metadata": {"font_size": 9.35, "bold": False},
        "page_width": 1200,
        "page_height": 1600,
    }

    result = build_block_signatures(block)

    assert result["marker_signature"]["type"] == "heading_roman"
    assert result["layout_signature"]["width"] == 297
    assert result["raw_label"] == "paragraph_title"
    assert result["role"] == "unassigned"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ocr_signatures.py::test_block_signature_extraction_preserves_observation_without_final_role -v`
Expected: FAIL because `build_block_signatures` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def build_block_signatures(block: dict) -> dict:
    # Emit raw observation + span/layout/marker signatures.
    # Do not assign semantic roles here.
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ocr_signatures.py tests/test_ocr_blocks.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_signatures.py paperforge/worker/ocr_blocks.py tests/test_ocr_signatures.py tests/test_ocr_blocks.py
git commit -m "feat: add OCR structural signatures"
```

### Task 2: Promote source-backed frontmatter anchors

**Files:**
- Modify: `paperforge/worker/ocr_metadata.py`
- Modify: `paperforge/worker/ocr_blocks.py`
- Test: `tests/test_ocr_metadata.py`

- [ ] **Step 1: Write the failing test**

```python
def test_preproof_page_one_does_not_block_page_two_title_localization():
    from paperforge.worker.ocr_metadata import _align_frontmatter_to_source_metadata

    source_meta = {"title": "Canonical Title", "authors": ["A. Yoo"]}
    page_blocks = [
        {"block_id": "p1_b1", "block_label": "text", "block_content": "Journal Pre-proof", "page": 1},
        {"block_id": "p2_b1", "block_label": "doc_title", "block_content": "Canonical Title", "page": 2},
    ]

    aligned = _align_frontmatter_to_source_metadata(source_meta, page_blocks)

    assert aligned["title"]["source"] == "zotero"
    assert aligned["title"]["value"] == "Canonical Title"
    assert aligned["title"].get("ocr_aligned") is True
    assert aligned["title"].get("ocr_block_id") == "p2_b1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ocr_metadata.py::test_preproof_page_one_does_not_block_page_two_title_localization -v`
Expected: FAIL until source alignment can localize beyond page 1.

- [ ] **Step 3: Write minimal implementation**

```python
def _align_frontmatter_to_source_metadata(source_meta: dict, page_blocks: list[dict]) -> dict:
    # Keep source metadata canonical while searching OCR blocks across the frontmatter window.
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ocr_metadata.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_metadata.py paperforge/worker/ocr_blocks.py tests/test_ocr_metadata.py
git commit -m "feat: promote source-backed frontmatter anchors"
```

### Task 3: Discover middle-page body family anchor

**Files:**
- Create: `paperforge/worker/ocr_families.py`
- Modify: `paperforge/worker/ocr_blocks.py`
- Test: `tests/test_ocr_families.py`

- [ ] **Step 1: Write the failing test**

```python
def test_middle_page_body_family_anchor_uses_dominant_repeated_family():
    from paperforge.worker.ocr_families import discover_body_family_anchor

    blocks = [
        {"page": 3, "text": "Long body text A " * 8, "marker_signature": {"type": "none"}, "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"}, "layout_signature": {"width": 260, "x_center": 240}},
        {"page": 4, "text": "Long body text B " * 8, "marker_signature": {"type": "none"}, "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"}, "layout_signature": {"width": 262, "x_center": 242}},
        {"page": 4, "text": "Figure 1.", "marker_signature": {"type": "figure_number"}, "span_signature": {"font_size_median": 8.0, "font_family_norm": "Times"}, "layout_signature": {"width": 210, "x_center": 260}},
    ]

    anchor = discover_body_family_anchor(blocks, page_count=8)
    assert anchor["status"] == "ACCEPT"
    assert anchor["family_name"] == "body_family"
    assert anchor["sample_pages"] == [3, 4]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ocr_families.py::test_middle_page_body_family_anchor_uses_dominant_repeated_family -v`
Expected: FAIL because body-family anchor discovery does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def discover_body_family_anchor(blocks: list[dict], page_count: int) -> dict:
    # Sample middle pages, cluster repeated body-like styles, and return the dominant family anchor.
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ocr_families.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_families.py paperforge/worker/ocr_blocks.py tests/test_ocr_families.py
git commit -m "feat: discover OCR body family anchor"
```

### Task 4: Build reference family anchor before final reference roles

**Files:**
- Modify: `paperforge/worker/ocr_families.py`
- Modify: `paperforge/worker/ocr_document.py`
- Test: `tests/test_ocr_families.py`
- Test: `tests/test_ocr_document.py`

- [ ] **Step 1: Write the failing test**

```python
def test_reference_family_anchor_comes_from_marker_and_family_evidence_not_final_role():
    from paperforge.worker.ocr_families import discover_reference_family_anchor

    blocks = [
        {"page": 8, "text": "References", "marker_signature": {"type": "canonical_section_name"}, "span_signature": {"font_size_median": 10.0}, "layout_signature": {"width": 120}, "role": "unassigned"},
        {"page": 8, "text": "[1] Example reference", "marker_signature": {"type": "reference_numeric_bracket", "number": 1}, "span_signature": {"font_size_median": 8.5}, "layout_signature": {"width": 250}, "role": "unassigned"},
        {"page": 8, "text": "[2] Another reference", "marker_signature": {"type": "reference_numeric_bracket", "number": 2}, "span_signature": {"font_size_median": 8.5}, "layout_signature": {"width": 252}, "role": "unassigned"},
    ]

    anchor = discover_reference_family_anchor(blocks)
    assert anchor["status"] == "ACCEPT"
    assert anchor["family_name"] == "reference_family"
    assert anchor["item_count"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ocr_families.py::test_reference_family_anchor_comes_from_marker_and_family_evidence_not_final_role -v`
Expected: FAIL until reference-family anchor discovery exists.

- [ ] **Step 3: Write minimal implementation**

```python
def discover_reference_family_anchor(blocks: list[dict]) -> dict:
    # Build reference-family anchor from markers, style consistency, and tail continuity.
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ocr_families.py tests/test_ocr_document.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_families.py paperforge/worker/ocr_document.py tests/test_ocr_families.py tests/test_ocr_document.py
git commit -m "feat: anchor OCR reference families"
```

### Task 5: Infer zones / region bus from anchors and boundary bands

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_blocks.py`
- Test: `tests/test_ocr_document.py`
- Test: `tests/test_ocr_layout_zones.py`

- [ ] **Step 1: Write the failing test**

```python
def test_reference_zone_is_inferred_from_reference_family_anchor_not_preexisting_roles():
    from paperforge.worker.ocr_document import infer_zones

    blocks = [
        {"block_id": "p1_b1", "page": 1, "text": "Abstract", "marker_signature": {"type": "canonical_section_name"}, "span_signature": {"font_size_median": 10.0}, "layout_signature": {"width": 120}},
        {"block_id": "p4_b1", "page": 4, "text": "Body text", "marker_signature": {"type": "none"}, "span_signature": {"font_size_median": 9.0}, "layout_signature": {"width": 260}},
        {"block_id": "p8_b1", "page": 8, "text": "References", "marker_signature": {"type": "canonical_section_name"}, "span_signature": {"font_size_median": 10.0}, "layout_signature": {"width": 120}},
        {"block_id": "p8_b2", "page": 8, "text": "[1] Example reference", "marker_signature": {"type": "reference_numeric_bracket", "number": 1}, "span_signature": {"font_size_median": 8.5}, "layout_signature": {"width": 250}},
    ]
    anchors = {
        "body_family_anchor": {"status": "ACCEPT", "family_name": "body_family", "sample_pages": [4]},
        "reference_family_anchor": {"status": "ACCEPT", "family_name": "reference_family", "item_count": 1},
    }

    zones = infer_zones(blocks, anchors)
    assert zones["reference_zone"]["status"] == "ACCEPT"
    assert "p8_b2" in zones["reference_zone"]["block_ids"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ocr_document.py::test_reference_zone_is_inferred_from_reference_family_anchor_not_preexisting_roles -v`
Expected: FAIL until zone inference consumes anchors instead of final roles.

- [ ] **Step 3: Write minimal implementation**

```python
def infer_zones(blocks: list[dict], anchors: dict[str, dict]) -> dict[str, dict]:
    # Build frontmatter/body/reference/display/tail-hold zones from accepted anchors and boundary bands.
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ocr_document.py tests/test_ocr_layout_zones.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_document.py paperforge/worker/ocr_blocks.py tests/test_ocr_document.py tests/test_ocr_layout_zones.py
git commit -m "feat: infer OCR zones from anchors"
```

### Task 6: Partition style/layout families inside zones

**Files:**
- Modify: `paperforge/worker/ocr_families.py`
- Modify: `paperforge/worker/ocr_profiles.py`
- Test: `tests/test_ocr_families.py`
- Test: `tests/test_ocr_profiles.py`

- [ ] **Step 1: Write the failing test**

```python
def test_partition_zone_families_separates_legend_like_from_body_like():
    from paperforge.worker.ocr_families import partition_zone_families

    blocks = [
        {"block_id": "p4_b1", "zone": "body_zone", "text": "Long narrative paragraph " * 6, "marker_signature": {"type": "none"}, "span_signature": {"font_size_median": 9.0, "font_family_norm": "Times"}, "layout_signature": {"width": 260}},
        {"block_id": "p4_b2", "zone": "body_zone", "text": "Figure 2. Long legend text", "marker_signature": {"type": "figure_number", "number": 2}, "span_signature": {"font_size_median": 8.0, "font_family_norm": "Times"}, "layout_signature": {"width": 220}},
    ]
    anchors = {"body_family_anchor": {"status": "ACCEPT", "family_name": "body_family"}}

    partitioned = partition_zone_families(blocks, anchors)
    assert partitioned["p4_b1"]["style_family"] == "body_like"
    assert partitioned["p4_b2"]["style_family"] == "legend_like"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ocr_families.py::test_partition_zone_families_separates_legend_like_from_body_like -v`
Expected: FAIL until family partition is explicit.

- [ ] **Step 3: Write minimal implementation**

```python
def partition_zone_families(blocks: list[dict], anchors: dict[str, dict]) -> dict[str, dict]:
    # Partition blocks into body_like / heading_like / legend_like / table_caption_like / reference_like / support_like / unknown_like.
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ocr_families.py tests/test_ocr_profiles.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_families.py paperforge/worker/ocr_profiles.py tests/test_ocr_families.py tests/test_ocr_profiles.py
git commit -m "feat: partition OCR families inside zones"
```

### Task 7: Add late role resolution entrypoint and demote eager role assignment

**Files:**
- Modify: `paperforge/worker/ocr_roles.py`
- Modify: `paperforge/worker/ocr_blocks.py`
- Test: `tests/test_ocr_roles.py`

- [ ] **Step 1: Write the failing test**

```python
def test_resolve_final_role_uses_zone_and_family_context_instead_of_default_body():
    from paperforge.worker.ocr_roles import resolve_final_role

    block = {
        "block_id": "p4_b2",
        "text": "Figure 2. A long legend that sits inside the body page.",
        "zone": "body_zone",
        "style_family": "legend_like",
        "marker_signature": {"type": "figure_number", "number": 2},
    }

    resolved = resolve_final_role(block, anchors={}, families={})
    assert resolved.role != "body_paragraph"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ocr_roles.py::test_resolve_final_role_uses_zone_and_family_context_instead_of_default_body -v`
Expected: FAIL because `resolve_final_role` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def resolve_final_role(block: dict, anchors: dict, families: dict) -> RoleAssignment:
    # Resolve final role only after zone and family context are known.
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ocr_roles.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_roles.py paperforge/worker/ocr_blocks.py tests/test_ocr_roles.py
git commit -m "feat: add late OCR role resolution"
```

### Task 8A: Upgrade figure matching to validation-first behavior

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `paperforge/worker/ocr_objects.py`
- Test: `tests/test_ocr_figures.py`
- Test: `tests/test_ocr_objects.py`

- [ ] **Step 1: Write the failing test**

```python
def test_figure_matching_can_hold_when_legend_is_ambiguous():
    from paperforge.worker.ocr_figures import build_figure_inventory

    structured_blocks = [
        {"paper_id": "K001", "page": 10, "block_id": "p10_b1", "zone": "body_zone", "style_family": "legend_like", "text": "Figure 1", "marker_signature": {"type": "figure_number", "number": 1}, "bbox": [50, 50, 300, 90], "page_width": 1200, "page_height": 1600},
        {"paper_id": "K001", "page": 10, "block_id": "p10_b2", "zone": "body_zone", "style_family": "body_like", "text": "Narrative prose", "marker_signature": {"type": "none"}, "bbox": [50, 100, 900, 140], "page_width": 1200, "page_height": 1600},
    ]

    inv = build_figure_inventory(structured_blocks)
    assert "held_figures" in inv or "ambiguous_figures" in inv
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ocr_figures.py::test_figure_matching_can_hold_when_legend_is_ambiguous -v`
Expected: FAIL until HOLD behavior is explicit.

- [ ] **Step 3: Write minimal implementation**

```python
def build_figure_inventory(structured_blocks: list[dict], page_width: float = 1200) -> dict[str, Any]:
    # Use anchors/zones/families and emit HOLD when figure evidence is insufficient.
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ocr_figures.py tests/test_ocr_objects.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figures.py paperforge/worker/ocr_objects.py tests/test_ocr_figures.py tests/test_ocr_objects.py
git commit -m "feat: validate OCR figure matching"
```

### Task 8B: Upgrade table matching to validation-first behavior

**Files:**
- Modify: `paperforge/worker/ocr_tables.py`
- Modify: `paperforge/worker/ocr_objects.py`
- Test: `tests/test_ocr_tables.py`
- Test: `tests/test_ocr_objects.py`

- [ ] **Step 1: Write the failing test**

```python
def test_table_matching_can_hold_when_caption_and_asset_conflict():
    from paperforge.worker.ocr_tables import build_table_inventory

    structured_blocks = [
        {"paper_id": "K001", "page": 12, "block_id": "p12_b1", "zone": "display_zone", "style_family": "table_caption_like", "text": "Table 2. Caption", "marker_signature": {"type": "table_number", "number": 2}, "bbox": [50, 50, 300, 90], "page_width": 1200, "page_height": 1600},
        {"paper_id": "K001", "page": 12, "block_id": "p12_b2", "zone": "display_zone", "style_family": "unknown_like", "text": "", "marker_signature": {"type": "none"}, "raw_label": "table", "bbox": [50, 120, 900, 500], "page_width": 1200, "page_height": 1600},
    ]

    inv = build_table_inventory(structured_blocks)
    assert any(t.get("match_status") in {"ambiguous", "held"} for t in inv.get("tables", [])) or inv.get("held_tables")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ocr_tables.py::test_table_matching_can_hold_when_caption_and_asset_conflict -v`
Expected: FAIL until HOLD/ambiguous table behavior is explicit.

- [ ] **Step 3: Write minimal implementation**

```python
def build_table_inventory(structured_blocks: list[dict]) -> dict[str, Any]:
    # Validate table caption/asset compatibility and keep a HOLD path.
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ocr_tables.py tests/test_ocr_objects.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_tables.py paperforge/worker/ocr_objects.py tests/test_ocr_tables.py tests/test_ocr_objects.py
git commit -m "feat: validate OCR table matching"
```

### Task 9: Unify decision statuses and expand OCR health diagnostics

**Files:**
- Modify: `paperforge/worker/ocr_health.py`
- Modify: `paperforge/worker/ocr_decisions.py`
- Test: `tests/test_ocr_health.py`
- Test: `tests/test_ocr_decisions.py`

- [ ] **Step 1: Write the failing test**

```python
def test_health_reports_anchor_zone_and_hold_statuses():
    from paperforge.worker.ocr_health import build_ocr_health

    report = build_ocr_health(
        page_count=2,
        raw_blocks_count=3,
        structured_blocks=[],
        figure_inventory={"matched_figures": [], "held_figures": [], "unmatched_legends": [], "unmatched_assets": []},
        table_inventory={"tables": [], "held_tables": [], "unmatched_assets": [], "unmatched_captions": []},
        doc_structure={
            "anchor_summary": {"reference_family_anchor": "ACCEPT", "body_family_anchor": "ACCEPT"},
            "zone_summary": {"reference_zone": "ACCEPT", "body_zone": "ACCEPT"},
            "held_counts": {"families": 1, "matches": 0},
        },
    )

    assert "reference_zone_confidence" in report or "anchor_summary" in report
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ocr_health.py::test_health_reports_anchor_zone_and_hold_statuses -v`
Expected: FAIL until health includes unified decision states.

- [ ] **Step 3: Write minimal implementation**

```python
DECISION_STATUSES = {"ACCEPT", "HOLD", "REJECT", "SOURCE_ONLY", "OBSERVATION_ONLY"}

def build_ocr_health(...):
    # Report anchor/zone/family/match statuses using the shared decision vocabulary.
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ocr_health.py tests/test_ocr_decisions.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_health.py paperforge/worker/ocr_decisions.py tests/test_ocr_health.py tests/test_ocr_decisions.py
git commit -m "feat: unify OCR decision statuses"
```

### Task 10A: Compatibility wiring without switching final semantic authority

**Files:**
- Modify: `paperforge/worker/ocr_blocks.py`
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_rebuild.py`
- Test: `tests/test_ocr_artifacts.py`
- Test: `tests/test_ocr_integration_fixtures.py`

- [ ] **Step 1: Write the failing integration test**

```python
def test_pipeline_emits_signatures_anchors_and_zones_before_final_role_switch():
    # Use an existing fixture helper and assert diagnostic artifacts exist.
    ...
    assert artifacts["structural_signatures"]
    assert artifacts["anchors"]
    assert artifacts["zones"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ocr_artifacts.py tests/test_ocr_integration_fixtures.py -v`
Expected: FAIL until compatibility wiring emits the new artifacts.

- [ ] **Step 3: Write minimal implementation**

```python
def build_structured_blocks(raw_blocks: list[dict], structure_output_dir: str | Path | None = None) -> tuple[list[dict], Any]:
    # Emit signatures/anchors/zones artifacts while keeping legacy outputs compatible.
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ocr_artifacts.py tests/test_ocr_integration_fixtures.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_blocks.py paperforge/worker/ocr_document.py paperforge/worker/ocr_rebuild.py tests/test_ocr_artifacts.py tests/test_ocr_integration_fixtures.py
git commit -m "feat: wire OCR anchor artifacts"
```

### Task 10B: Switch final role authority to anchors/zones/families and close regressions

**Files:**
- Modify: `paperforge/worker/ocr_blocks.py`
- Modify: `paperforge/worker/ocr_roles.py`
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `paperforge/worker/ocr_tables.py`
- Modify: `paperforge/worker/ocr_health.py`
- Test: `tests/test_ocr_real_paper_regressions.py`
- Test: `tests/test_ocr_integration_fixtures.py`

- [ ] **Step 1: Write the failing regression test**

```python
def test_pipeline_keeps_reference_zone_and_legend_family_out_of_default_body():
    # Use an existing regression fixture with frontmatter/body/references/legend mix.
    ...
    assert any(row["role"] == "reference_item" for row in rows)
    assert not any(row["role"] == "body_paragraph" and row.get("style_family") == "legend_like" for row in rows)
```

- [ ] **Step 2: Run the regression tests to verify they fail**

Run: `pytest tests/test_ocr_real_paper_regressions.py tests/test_ocr_integration_fixtures.py -v`
Expected: FAIL until final role authority switches from eager role assignment to anchor-first resolution.

- [ ] **Step 3: Write minimal implementation**

```python
def build_structured_blocks(raw_blocks: list[dict], structure_output_dir: str | Path | None = None) -> tuple[list[dict], Any]:
    # Final authority flow: signatures -> anchors -> zones -> families -> late roles -> figure/table validation -> health.
    ...
```

- [ ] **Step 4: Run the targeted OCR test set**

Run: `pytest tests/test_ocr_signatures.py tests/test_ocr_families.py tests/test_ocr_metadata.py tests/test_ocr_document.py tests/test_ocr_roles.py tests/test_ocr_figures.py tests/test_ocr_tables.py tests/test_ocr_health.py tests/test_ocr_integration_fixtures.py tests/test_ocr_real_paper_regressions.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_blocks.py paperforge/worker/ocr_roles.py paperforge/worker/ocr_document.py paperforge/worker/ocr_figures.py paperforge/worker/ocr_tables.py paperforge/worker/ocr_health.py tests/test_ocr_signatures.py tests/test_ocr_families.py tests/test_ocr_metadata.py tests/test_ocr_document.py tests/test_ocr_roles.py tests/test_ocr_figures.py tests/test_ocr_tables.py tests/test_ocr_health.py tests/test_ocr_integration_fixtures.py tests/test_ocr_real_paper_regressions.py
git commit -m "feat: switch OCR to anchor-first role authority"
```

---

## Self-review checklist

Before implementation starts, verify:

1. No early test depends on final role labels before anchors/zones/families exist.
2. Body-family anchor discovery is a separate step from zone inference.
3. Reference-family anchor discovery happens before final `reference_item` roles.
4. Family partition inside zones has its own explicit task and file boundary.
5. `assign_block_role()` is no longer the conceptual entrypoint for semantic truth.
6. Figure and table validation are implemented in separate tasks.
7. Compatibility wiring is split from the final semantic authority switch.
8. Shared decision statuses are visible across anchors, zones, families, and object matches.

---

**Plan complete and saved to `docs/superpowers/plans/2026-06-08-ocr-anchor-first-structured-parsing-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
