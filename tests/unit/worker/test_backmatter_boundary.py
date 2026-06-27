"""Tests for backmatter boundary redesign."""
from __future__ import annotations

from paperforge.worker.ocr_document import (
    TailBoundary,
    _build_tail_boundary_from_ref_partition,
    _classify_same_page_block,
    _clear_partition_zones,
    _has_verified_reference_zone,
    _normalize_pre_ref_disclosure_runs,
    _normalize_reference_roles_from_partition,
    _partition_by_reference_zone,
    _resolve_reference_zone_extent,
)


class TestHasVerifiedReferenceZone:
    def test_has_verified_ref_zone_true(self):
        region_bus = {
            "reference_zone": {"status": "ACCEPT", "block_ids": ["b1"]}
        }
        assert _has_verified_reference_zone(region_bus)

    def test_has_verified_ref_zone_empty_ids(self):
        region_bus = {
            "reference_zone": {"status": "ACCEPT", "block_ids": []}
        }
        assert not _has_verified_reference_zone(region_bus)

    def test_has_verified_ref_zone_reject(self):
        region_bus = {
            "reference_zone": {"status": "REJECT", "block_ids": ["b1"]}
        }
        assert not _has_verified_reference_zone(region_bus)


class TestResolveReferenceZoneExtent:
    def test_resolve_extent_simple(self):
        region_bus = {
            "reference_zone": {
                "boundary_band": {"start_page": 5},
                "effective_end_page": 10,
            }
        }
        start, end = _resolve_reference_zone_extent([], region_bus)
        assert start == 5
        assert end == 10

    def test_resolve_extent_derives_from_block_ids(self):
        blocks = [
            {"block_id": "r1", "page": 1},
            {"block_id": "r2", "page": 2},
            {"block_id": "r3", "page": 3},
        ]
        region_bus = {
            "reference_zone": {
                "boundary_band": {"start_page": 2},
                "block_ids": ["r1", "r2", "r3"],
            }
        }
        start, end = _resolve_reference_zone_extent(blocks, region_bus)
        assert start == 2
        assert end == 3

    def test_resolve_extent_no_block_ids(self):
        region_bus = {
            "reference_zone": {
                "boundary_band": {"start_page": 5},
                "block_ids": [],
            }
        }
        start, end = _resolve_reference_zone_extent([], region_bus)
        assert start == 5
        assert end is None


class TestClassifySamePageBlock:
    def test_classify_same_page_reference_role(self):
        block = {
            "role": "reference_heading",
            "block_id": "b1",
            "page": 1,
            "bbox": [0, 0, 100, 100],
        }
        region_bus = {"reference_zone": {"block_ids": []}}
        result = _classify_same_page_block(block, region_bus, page=1)
        assert result == "reference"

    def test_classify_same_page_block_ids_membership(self):
        block = {
            "role": "body_paragraph",
            "block_id": "ref1",
            "page": 1,
            "bbox": [0, 0, 100, 100],
        }
        region_bus = {"reference_zone": {"block_ids": ["ref1"]}}
        result = _classify_same_page_block(block, region_bus, page=1)
        assert result == "reference"

    def test_classify_same_page_conservative_fallback(self):
        block = {
            "role": "body_paragraph",
            "block_id": "b1",
            "page": 1,
            "bbox": [0, 0, 100, 100],
        }
        region_bus = {"reference_zone": {"block_ids": []}}
        result = _classify_same_page_block(block, region_bus, page=1)
        assert result == "pre_ref"


class TestPartitionByReferenceZone:
    def test_partition_simple_3_way(self):
        blocks = []
        for i in range(1, 6):
            blocks.append({
                "block_id": f"b{i}", "page": i,
                "role": "body_paragraph",
                "bbox": [0, 0, 100, 100],
            })
        blocks.append({
            "block_id": "r1", "page": 6,
            "role": "reference_item",
            "bbox": [0, 0, 100, 100],
        })
        blocks.append({
            "block_id": "r2", "page": 7,
            "role": "reference_item",
            "bbox": [0, 0, 100, 100],
        })
        blocks.append({
            "block_id": "a1", "page": 8,
            "role": "body_paragraph",
            "bbox": [0, 0, 100, 100],
        })
        region_bus = {
            "reference_zone": {
                "status": "ACCEPT",
                "block_ids": ["r1", "r2"],
                "boundary_band": {"start_page": 6},
                "effective_end_page": 7,
            }
        }
        result = _partition_by_reference_zone(blocks, region_bus)
        assert len(result["pre_ref"]) == 5
        assert len(result["reference"]) == 2
        assert len(result["post_ref"]) == 1

    def test_partition_fallback(self):
        region_bus = {
            "reference_zone": {"status": "REJECT", "block_ids": ["b1"]}
        }
        result = _partition_by_reference_zone([], region_bus)
        assert result == {"fallback": True}


class TestNormalizeReferenceRoles:
    def test_ref_role_normalization(self):
        block = {"role": "body_paragraph", "block_id": "b1", "page": 6}
        _normalize_reference_roles_from_partition(
            [block], {"reference": [block]}
        )
        assert block["role"] == "reference_item"

    def test_ref_role_normalization_skips_correct_roles(self):
        block = {"role": "reference_heading", "block_id": "b1"}
        _normalize_reference_roles_from_partition(
            [block], {"reference": [block]}
        )
        assert block["role"] == "reference_heading"


class TestNormalizePreRefDisclosureRuns:
    def test_disclosure_exact_match(self):
        block = {
            "role": "body_paragraph", "page": 2, "block_id": "b1",
            "text": "credit authorship contribution statement",
            "bbox": [0, 0, 100, 100],
        }
        partition = {"pre_ref": [block]}
        _normalize_pre_ref_disclosure_runs(
            partition, ref_start_page=5, total_pages=10
        )
        assert block["role"] == "backmatter_heading"

    def test_disclosure_no_substring_match(self):
        block = {
            "role": "body_paragraph", "page": 2, "block_id": "b1",
            "text": "funding mechanism",
            "bbox": [0, 0, 100, 100],
        }
        partition = {"pre_ref": [block]}
        _normalize_pre_ref_disclosure_runs(
            partition, ref_start_page=5, total_pages=10
        )
        assert block["role"] == "body_paragraph"

    def test_disclosure_stops_at_next_heading(self):
        disclosure = {
            "role": "body_paragraph", "page": 2,
            "block_id": "b1",
            "text": "credit authorship contribution statement",
            "bbox": [0, 0, 100, 100],
        }
        heading = {
            "role": "section_heading", "page": 2,
            "block_id": "b2", "text": "something else",
            "bbox": [0, 0, 100, 100],
        }
        body = {
            "role": "body_paragraph", "page": 2,
            "block_id": "b3", "text": "after heading text",
            "bbox": [0, 0, 100, 100],
        }
        partition = {"pre_ref": [disclosure, heading, body]}
        _normalize_pre_ref_disclosure_runs(
            partition, ref_start_page=5, total_pages=10
        )
        assert disclosure["role"] == "backmatter_heading"
        assert body["role"] == "body_paragraph"

    def test_disclosure_no_proximity_gate(self):
        block = {
            "role": "body_paragraph", "page": 2, "block_id": "b1",
            "text": "credit authorship contribution statement",
            "bbox": [0, 0, 100, 100],
        }
        partition = {"pre_ref": [block]}
        _normalize_pre_ref_disclosure_runs(
            partition, ref_start_page=12, total_pages=15
        )
        assert block["role"] == "backmatter_heading"


class TestClearPartitionZones:
    def test_clear_partition_zones(self):
        blocks = [
            {"block_id": "b1", "zone": "reference_zone"},
            {"block_id": "b2", "zone": "body_zone"},
            {"block_id": "b3", "zone": "display_zone"},
            {"block_id": "b4", "zone": "other_zone"},
        ]
        _clear_partition_zones(blocks)
        assert blocks[0]["zone"] == ""
        assert blocks[1]["zone"] == ""
        assert blocks[2]["zone"] == ""
        assert blocks[3]["zone"] == "other_zone"


class TestBuildTailBoundary:
    def test_build_tail_boundary_from_partition(self):
        pre_ref = [
            {"block_id": "b1", "page": 1},
            {"block_id": "b2", "page": 2},
        ]
        reference = [
            {"block_id": "r1", "page": 6},
            {"block_id": "r2", "page": 7},
        ]
        partition = {
            "pre_ref": pre_ref,
            "reference": reference,
            "post_ref": [],
        }
        region_bus = {
            "reference_zone": {"boundary_band": {"start_page": 6}}
        }
        tb = _build_tail_boundary_from_ref_partition(partition, region_bus)
        assert tb.body_end_page == 2
        assert tb.backmatter_start == 2
        assert tb.references_start == 6
        assert tb.spread_start == 6
        assert tb.spread_end == 7
        assert tb.is_clean_separated
        assert tb.reason == "ref_zone_partition"

    def test_tail_spread_start_is_references_start(self):
        pre_ref = [
            {"block_id": "b1", "page": 1},
            {"block_id": "b2", "page": 2},
        ]
        reference = [{"block_id": "r1", "page": 5}]
        partition = {"pre_ref": pre_ref, "reference": reference}
        region_bus = {
            "reference_zone": {"boundary_band": {"start_page": 5}}
        }
        tb = _build_tail_boundary_from_ref_partition(partition, region_bus)
        assert tb.body_end_page == 2
        assert tb.references_start == 5
        assert tb.spread_start == tb.references_start
        assert tb.spread_start != tb.body_end_page
