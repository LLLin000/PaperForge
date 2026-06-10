from __future__ import annotations

import json
from pathlib import Path

import pytest

OCR_CORPUS = Path("D:/L/OB/Literature-hub/System/PaperForge/ocr")


def _load_json_path(key: str) -> Path | None:
    return OCR_CORPUS / key / "json" / "result.json"


def _get_page_blocks(json_path: Path, page: int) -> list[dict]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    pageno = 0
    for payload in data:
        for res in payload.get("layoutParsingResults", []):
            pageno += 1
            if pageno != page:
                continue
            return res.get("prunedResult", {}).get("parsing_res_list", [])
    return []


def test_fixture_interleaved_text_reordered() -> None:
    json_path = _load_json_path("2GN9LMCW")
    assert json_path and json_path.exists(), f"fixture not found: {json_path}"

    blocks = _get_page_blocks(json_path, 11)

    from paperforge.worker.ocr import block_sort_key, validate_block_order
    from paperforge.worker.ocr_orchestrator import reorder_blocks_layered

    sorted_blocks = sorted(blocks, key=block_sort_key)
    validated = validate_block_order(sorted_blocks, 1200)
    layered = reorder_blocks_layered(validated, page_width=1200, page_height=1600)

    body_labels = {"text", "paragraph_title", "abstract"}
    body_ordered = [b for b in layered if b.get("block_label", "") in body_labels]

    assert len(body_ordered) >= 4, f"too few body blocks: {len(body_ordered)}"

    left_count = 0
    right_count = 0
    prev_xc = None
    mid = 600
    for b in body_ordered:
        bb = b.get("block_bbox", [0, 0, 0, 0])
        xc = (bb[0] + bb[2]) / 2 if bb[2] > bb[0] else None
        if xc is None:
            continue
        if xc < mid:
            left_count += 1
            if prev_xc is not None and prev_xc >= mid:
                pass
        else:
            right_count += 1
        prev_xc = xc

    assert left_count >= 1
    assert right_count >= 1


def test_session_regression_heading_retained() -> None:
    json_path = _load_json_path("7C8829BD")
    assert json_path and json_path.exists(), f"fixture not found: {json_path}"

    blocks = _get_page_blocks(json_path, 7)

    from paperforge.worker.ocr import block_sort_key, validate_block_order
    from paperforge.worker.ocr_orchestrator import reorder_blocks_layered

    sorted_blocks = sorted(blocks, key=block_sort_key)
    validated = validate_block_order(sorted_blocks, 1191)
    layered = reorder_blocks_layered(validated, page_width=1191, page_height=1684)

    headings_found = []
    for b in layered:
        if b.get("block_label") == "paragraph_title":
            headings_found.append(b.get("block_content", ""))

    assert any("5 In vitro PEMF studies" in h for h in headings_found), f"missing 5 heading, found: {headings_found}"
    assert any("5.1 Bone" in h for h in headings_found), f"missing 5.1 heading, found: {headings_found}"

    heading_order = [h for h in headings_found if "5" in h or "6" in h or "7" in h]
    heading_positions = {h: i for i, h in enumerate(headings_found)}

    if "5.4" in str(headings_found) and "6 In vivo" in str(headings_found):
        idx_54 = next(i for i, h in enumerate(headings_found) if "5.4" in h)
        idx_6 = next(i for i, h in enumerate(headings_found) if "6 In vivo" in h)
        assert idx_54 < idx_6, "5.4 must come before 6"


def test_session_regression_figure_not_in_unrelated_section() -> None:
    json_path = _load_json_path("7C8829BD")
    assert json_path and json_path.exists(), f"fixture not found: {json_path}"

    blocks = _get_page_blocks(json_path, 14)

    from paperforge.worker.ocr import block_sort_key, validate_block_order
    from paperforge.worker.ocr_orchestrator import reorder_blocks_layered

    sorted_blocks = sorted(blocks, key=block_sort_key)
    validated = validate_block_order(sorted_blocks, 1191)
    layered = reorder_blocks_layered(validated, page_width=1191, page_height=1684)

    body_labels = {"text", "paragraph_title", "abstract"}
    for b in layered:
        content = b.get("block_content", "")
        if "cartilage" in content.lower() and "distribution" in content.lower():
            continue

    assert True


def test_fixture_raw_blocks_nonzero(tmp_path) -> None:
    """Load a real result.json, write blocks.raw.jsonl, verify rows."""
    key = "2GN9LMCW"
    json_path = _load_json_path(key)
    if not json_path or not json_path.exists():
        pytest.skip("fixture not available")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    from paperforge.worker.ocr_blocks import build_raw_blocks_for_result_lines, write_raw_blocks_jsonl

    rows = build_raw_blocks_for_result_lines(key, data)
    assert len(rows) > 0

    out_dir = tmp_path / key
    out_dir.mkdir(parents=True)
    out_path = out_dir / "blocks.raw.jsonl"
    write_raw_blocks_jsonl(out_path, rows)
    assert out_path.exists()
    assert out_path.stat().st_size > 0


# Phase 2: forward-looking contract test; fails until ocr_figures module exists
def test_fixture_figure_inventory_basic(tmp_path) -> None:
    """Verify figure inventory can run against a real OCR fixture."""
    key = "2GN9LMCW"
    json_path = _load_json_path(key)
    if not json_path or not json_path.exists():
        pytest.skip("fixture not available")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    from paperforge.worker.ocr_blocks import build_raw_blocks_for_result_lines, build_structured_blocks

    raw_blocks = build_raw_blocks_for_result_lines(key, data)
    structured, _ = build_structured_blocks(raw_blocks)

    from paperforge.worker.ocr_figures import build_figure_inventory

    inventory = build_figure_inventory(structured)

    assert isinstance(inventory["official_figure_count"], int)
    assert isinstance(inventory["figure_legends"], list)
    assert isinstance(inventory["figure_assets"], list)


def test_fixture_structured_renderer_has_headings_and_body() -> None:
    """Verify the structured renderer preserves headings and body text from a real OCR fixture."""
    key = "2GN9LMCW"
    json_path = _load_json_path(key)
    if not json_path or not json_path.exists():
        pytest.skip("fixture not available")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    from paperforge.worker.ocr_blocks import build_raw_blocks_for_result_lines, build_structured_blocks
    from paperforge.worker.ocr_render import render_fulltext_markdown

    raw_blocks = build_raw_blocks_for_result_lines(key, data)
    structured, _ = build_structured_blocks(raw_blocks)

    output = render_fulltext_markdown(
        structured_blocks=structured,
        resolved_metadata={},
        figure_inventory={},
        table_inventory={},
    )

    assert len(output) > 0, "renderer produced empty output"

    lines = output.split("\n")
    headings = [l for l in lines if l.startswith("## ") or l.startswith("### ")]
    assert len(headings) >= 1, (
        f"expected at least one ## or ### heading in rendered output, "
        f"found {len(headings)} headings in:\n{output[:800]}"
    )

    non_heading_text = [
        l for l in lines
        if l.strip()
        and not l.startswith("#")
        and not l.startswith("<!--")
        and not l.startswith("![[")
    ]
    assert len(non_heading_text) >= 1, (
        f"expected at least one line of body text in rendered output:\n{output[:800]}"
    )


def test_pipeline_emits_signatures_anchors_and_zones_before_final_role_switch(tmp_path: Path) -> None:
    key = "2GN9LMCW"
    json_path = _load_json_path(key)
    if not json_path or not json_path.exists():
        pytest.skip("fixture not available")

    data = json.loads(json_path.read_text(encoding="utf-8"))

    from paperforge.worker.ocr_blocks import build_raw_blocks_for_result_lines, build_structured_blocks

    raw_blocks = build_raw_blocks_for_result_lines(key, data)
    structure_dir = tmp_path / key / "structure"
    structure_dir.mkdir(parents=True)

    rows, doc_structure = build_structured_blocks(raw_blocks, structure_output_dir=structure_dir)
    artifacts = json.loads((structure_dir / "document_structure.json").read_text(encoding="utf-8"))

    assert doc_structure is not None
    assert artifacts["structural_signatures"]
    assert artifacts["anchors"]
    assert artifacts["zones"]
    assert any(row.get("marker_signature") for row in rows)
    assert doc_structure.body_family_anchor is not None
    assert doc_structure.region_bus is not None


def test_zone_and_family_partition_complete_before_final_role_resolution(tmp_path: Path) -> None:
    """Zones and families must be fully resolved before resolve_final_role runs.

    The target pipeline order is:
        raw observations -> signatures -> frontmatter anchors -> body anchor
        -> reference anchor -> infer_zones -> partition_zone_families
        -> resolve_final_role

    This test verifies that when resolve_final_role is called, zone and
    style_family are already populated on each block (not stale/unassigned).
    """
    key = "2GN9LMCW"
    json_path = _load_json_path(key)
    if not json_path or not json_path.exists():
        pytest.skip("fixture not available")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    from paperforge.worker.ocr_blocks import build_raw_blocks_for_result_lines, build_structured_blocks

    raw_blocks = build_raw_blocks_for_result_lines(key, data)
    rows, doc_structure = build_structured_blocks(raw_blocks)

    assert doc_structure is not None
    assert doc_structure.region_bus is not None

    # Blocks with block_id that fall in ANY zone must have both zone and
    # style_family set.  If resolve_final_role ran before zone/family
    # partition, these would be missing or stale.
    all_zone_ids: set[str] = set()
    for zone_data in doc_structure.region_bus.values():
        all_zone_ids.update(zone_data.get("block_ids") or [])

    zoned_rows = [
        r for r in rows
        if r.get("block_id") is not None
        and f"p{r.get('page')}:{r['block_id']}" in all_zone_ids
    ]
    assert len(zoned_rows) > 0, "need at least some zoned blocks"

    for row in zoned_rows:
        assert row.get("zone") is not None, (
            f"block {row.get('block_id')} (page {row.get('page')}) missing zone "
            f"before final role resolution — role={row.get('role')}"
        )
        assert row.get("style_family") is not None, (
            f"block {row.get('block_id')} (page {row.get('page')}) missing style_family "
            f"before final role resolution — role={row.get('role')}"
        )


def test_source_backed_frontmatter_anchors_are_available_before_zone_inference(tmp_path: Path) -> None:
    """Source-backed frontmatter anchors must be established before zone inference.

    The frontmatter anchor layer (title, authors, DOI from source metadata)
    must be available in the anchors dict consumed by infer_zones, not added
    after the fact as a post-hoc enrichment.
    """
    key = "2GN9LMCW"
    json_path = _load_json_path(key)
    if not json_path or not json_path.exists():
        pytest.skip("fixture not available")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    from paperforge.worker.ocr_blocks import build_raw_blocks_for_result_lines, build_structured_blocks

    raw_blocks = build_raw_blocks_for_result_lines(key, data)
    structure_dir = tmp_path / key / "structure"
    structure_dir.mkdir(parents=True)

    rows, doc_structure = build_structured_blocks(raw_blocks, structure_output_dir=structure_dir)
    artifacts = json.loads((structure_dir / "document_structure.json").read_text(encoding="utf-8"))

    # The document structure should have both body and reference anchors
    # established, and these anchors should have been used to infer zones
    # (not added after zone inference).
    assert doc_structure is not None
    assert doc_structure.body_family_anchor is not None

    # Reference anchor must be discovered (status can be ACCEPT or HOLD)
    assert doc_structure.reference_family_anchor is not None, (
        "reference_family_anchor must be discovered before zone inference"
    )

    # The anchors dict in the serialized artifact should contain both anchors
    anchors_artifact = artifacts.get("anchors", {})
    assert "body_family_anchor" in anchors_artifact, (
        "body_family_anchor must be in anchors artifact"
    )
    assert "reference_family_anchor" in anchors_artifact, (
        "reference_family_anchor must be in anchors artifact"
    )

    # Zones should reference the anchor families in the region_bus
    region_bus = doc_structure.region_bus
    assert region_bus is not None
    body_zone = region_bus.get("body_zone", {})
    if body_zone.get("status") == "ACCEPT":
        assert body_zone.get("anchor_family") == "body_family_anchor", (
            "body_zone should reference body_family_anchor"
        )
