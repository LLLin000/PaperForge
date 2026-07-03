"""Identity and normalization tests for vnext figure contracts."""

from __future__ import annotations

import pytest

from paperforge.worker.ocr_figure_vnext_types import ResourceRef


def test_resource_ref_rejects_page_agnostic_asset() -> None:
    with pytest.raises(ValueError):
        ResourceRef(kind="asset", page=None, block_id="42")


def test_resource_ref_normalizes_block_id_type() -> None:
    assert ResourceRef(kind="asset", page=1, block_id=42) == ResourceRef(kind="asset", page=1, block_id="42")


def test_resource_ref_rejects_group_without_group_id() -> None:
    with pytest.raises(ValueError):
        ResourceRef(kind="group", page=1, block_id=None)


@pytest.mark.parametrize(
    "ref_no_meta, ref_with_meta",
    [
        pytest.param(
            ResourceRef(kind="asset", page=1, block_id="42"),
            ResourceRef(kind="asset", page=1, block_id="42", figure_no=5),
            id="asset-figure_no",
        ),
        pytest.param(
            ResourceRef(kind="asset", page=1, block_id="42"),
            ResourceRef(kind="asset", page=1, block_id="42", origin="scan"),
            id="asset-origin",
        ),
        pytest.param(
            ResourceRef(kind="asset", page=1, block_id="42"),
            ResourceRef(kind="asset", page=1, block_id="42", figure_no=5, origin="scan"),
            id="asset-both",
        ),
        pytest.param(
            ResourceRef(kind="legend", page=1, block_id="c1"),
            ResourceRef(kind="legend", page=1, block_id="c1", figure_no=3),
            id="legend-figure_no",
        ),
        pytest.param(
            ResourceRef(kind="legend", page=1, block_id="c1"),
            ResourceRef(kind="legend", page=1, block_id="c1", figure_no=3, origin="pdf"),
            id="legend-both",
        ),
        pytest.param(
            ResourceRef(kind="group", page=2, group_id="g1", block_id=None),
            ResourceRef(kind="group", page=2, group_id="g1", figure_no=1, block_id=None),
            id="group-figure_no",
        ),
        pytest.param(
            ResourceRef(kind="group", page=2, group_id="g1", block_id=None),
            ResourceRef(kind="group", page=2, group_id="g1", origin="aggregation", block_id=None),
            id="group-origin",
        ),
    ],
)
def test_resource_ref_equality_ignores_metadata(
    ref_no_meta: ResourceRef, ref_with_meta: ResourceRef
) -> None:
    assert ref_no_meta == ref_with_meta
    assert hash(ref_no_meta) == hash(ref_with_meta)
    # Dict key lookup — must find same entry despite metadata difference
    d = {ref_no_meta: "found"}
    assert d.get(ref_with_meta) == "found"
    assert d.get(ref_no_meta) == "found"
