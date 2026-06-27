"""Tests for figure containment render hygiene."""
from __future__ import annotations

from paperforge.worker.ocr_figures import (
    _cluster_bboxes_by_proximity,
    _highly_overlaps_any_matched_region,
    _is_contained,
    _matched_asset_keys,
    tag_figure_contained_text,
)


def _bbox(x1, y1, x2, y2):
    return [float(v) for v in (x1, y1, x2, y2)]


class TestIsContained:
    def test_inside_block_gets_tagged(self):
        block = _bbox(100, 100, 300, 300)
        region = _bbox(50, 50, 400, 400)
        assert _is_contained(block, region)

    def test_full_width_block_not_contained(self):
        block = _bbox(50, 100, 400, 300)
        region = _bbox(50, 50, 400, 400)
        assert not _is_contained(block, region)

    def test_centroid_outside_region_not_contained(self):
        block = _bbox(50, 450, 200, 550)
        region = _bbox(50, 50, 400, 400)
        assert not _is_contained(block, region)

    def test_low_overlap_not_contained(self):
        block = _bbox(50, 50, 400, 500)
        region = _bbox(50, 50, 400, 400)
        assert not _is_contained(block, region)


class TestClusterBboxesByProximity:
    def test_merges_overlapping_boxes(self):
        bboxes = [
            _bbox(100, 100, 200, 200),
            _bbox(180, 180, 280, 280),
            _bbox(500, 500, 600, 600),
        ]
        result = _cluster_bboxes_by_proximity(bboxes, margin=40)
        assert len(result) == 2

    def test_empty_input(self):
        assert _cluster_bboxes_by_proximity([]) == []

    def test_single_bbox(self):
        b = [_bbox(10, 10, 100, 100)]
        result = _cluster_bboxes_by_proximity(b)
        assert len(result) == 1
        assert result[0] == _bbox(10, 10, 100, 100)


class TestHighlyOverlapsAnyMatchedRegion:
    def test_drops_when_over_50pct(self):
        fallback = _bbox(100, 100, 300, 300)
        regions = [("matched", _bbox(120, 120, 280, 280))]
        assert _highly_overlaps_any_matched_region(fallback, regions)

    def test_keeps_when_no_overlap(self):
        fallback = _bbox(500, 500, 600, 600)
        regions = [("matched", _bbox(100, 100, 200, 200))]
        assert not _highly_overlaps_any_matched_region(fallback, regions)

    def test_ignores_fallback_tag_regions(self):
        fallback = _bbox(100, 100, 300, 300)
        regions = [("fallback", _bbox(100, 100, 300, 300))]
        assert not _highly_overlaps_any_matched_region(fallback, regions)


class TestMatchedAssetKeys:
    def test_collects_from_matched_assets_and_asset_block_ids(self):
        mf = {
            "page": 3,
            "matched_assets": [{"block_id": "a1"}, {"block_id": "a2"}],
            "asset_block_ids": ["a2", "a3"],
        }
        keys = _matched_asset_keys(mf)
        assert keys == {(3, "a1"), (3, "a2"), (3, "a3")}


class TestTagFigureContainedText:
    def _block(self, bid, page, x1, y1, x2, y2, role="body_paragraph",
               raw_label="", asset_family_hint=""):
        b = {
            "block_id": bid,
            "page": page,
            "bbox": _bbox(x1, y1, x2, y2),
            "role": role,
        }
        if raw_label:
            b["raw_label"] = raw_label
        if asset_family_hint:
            b["asset_family_hint"] = asset_family_hint
        return b

    def _matched_fig(self, page, cluster_bbox, matched_assets=None):
        return {
            "page": page,
            "cluster_bbox": cluster_bbox,
            "matched_assets": matched_assets or [],
            "asset_block_ids": [a["block_id"] for a in (matched_assets or [])],
        }

    def test_body_paragraph_inside_matched_region_becomes_figure_inner_text(self):
        region = _bbox(50, 50, 400, 400)
        block = self._block("b1", 1, 100, 100, 300, 300, role="body_paragraph")
        mf = self._matched_fig(1, region, matched_assets=[{"block_id": "a1", "bbox": _bbox(50, 50, 400, 400)}])
        blocks = [block, self._block("a1", 1, 50, 50, 400, 400, role="figure_asset")]
        tag_figure_contained_text(blocks, [mf])
        assert block.get("_figure_contained") is True
        assert block["role"] == "figure_inner_text"

    def test_body_paragraph_inside_fallback_region_becomes_figure_inner_text(self):
        block = self._block("b1", 1, 100, 100, 300, 300, role="body_paragraph")
        fallback_asset = self._block("a1", 1, 50, 50, 400, 400, role="media_asset",
                                     raw_label="image", asset_family_hint="figure_like")
        blocks = [block, fallback_asset]
        tag_figure_contained_text(blocks, [])
        assert block.get("_figure_contained") is True
        assert block["role"] == "figure_inner_text"

    def test_block_outside_region_unchanged(self):
        region = _bbox(50, 50, 200, 200)
        block = self._block("b1", 1, 300, 300, 400, 400, role="body_paragraph")
        mf = self._matched_fig(1, region, matched_assets=[{"block_id": "a1", "bbox": _bbox(50, 50, 200, 200)}])
        blocks = [block, self._block("a1", 1, 50, 50, 200, 200, role="figure_asset")]
        tag_figure_contained_text(blocks, [mf])
        assert not block.get("_figure_contained")
        assert block["role"] == "body_paragraph"

    def test_figure_asset_never_tagged(self):
        region = _bbox(50, 50, 400, 400)
        asset = self._block("a1", 1, 100, 100, 200, 200, role="figure_asset")
        mf = self._matched_fig(1, region, matched_assets=[{"block_id": "a1", "bbox": _bbox(50, 50, 400, 400)}])
        blocks = [asset]
        tag_figure_contained_text(blocks, [mf])
        assert not asset.get("_figure_contained")
        assert asset["role"] == "figure_asset"

    def test_asset_in_matched_excluded_from_fallback(self):
        block = self._block("b1", 1, 100, 100, 300, 300, role="body_paragraph")
        matched_asset = self._block("a1", 1, 50, 50, 400, 400, role="media_asset",
                                    raw_label="image", asset_family_hint="figure_like")
        mf = self._matched_fig(1, _bbox(50, 50, 400, 400),
                               matched_assets=[{"block_id": "a1", "bbox": _bbox(50, 50, 400, 400)}])
        blocks = [block, matched_asset]
        tag_figure_contained_text(blocks, [mf])
        assert block.get("_figure_contained") is True

    def test_table_html_not_in_fallback(self):
        block = self._block("b1", 1, 100, 100, 300, 300, role="body_paragraph")
        table = self._block("t1", 1, 50, 50, 400, 400, role="table_html")
        blocks = [block, table]
        tag_figure_contained_text(blocks, [])
        assert not block.get("_figure_contained")

    def test_render_default_index_default_unchanged(self):
        region = _bbox(50, 50, 400, 400)
        for role in ("figure_caption", "noise", "figure_inner_text", "table_html", "table_asset"):
            block = self._block("b1", 1, 100, 100, 300, 300, role=role)
            mf = self._matched_fig(1, region, matched_assets=[{"block_id": "a1", "bbox": _bbox(50, 50, 400, 400)}])
            blocks = [block, self._block("a1", 1, 50, 50, 400, 400, role="figure_asset")]
            tag_figure_contained_text(blocks, [mf])
            assert not block.get("_figure_contained"), f"role={role} should not be tagged"

    def test_structured_insert_inside_figure_becomes_figure_inner_text(self):
        region = _bbox(50, 50, 400, 400)
        block = self._block("b1", 1, 100, 100, 300, 300, role="structured_insert")
        mf = self._matched_fig(1, region, matched_assets=[{"block_id": "a1", "bbox": _bbox(50, 50, 400, 400)}])
        blocks = [block, self._block("a1", 1, 50, 50, 400, 400, role="figure_asset")]
        tag_figure_contained_text(blocks, [mf])
        assert block["role"] == "figure_inner_text"
