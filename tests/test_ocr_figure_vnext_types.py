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
