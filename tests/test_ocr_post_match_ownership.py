"""Post-match normalization consumes inventory ownership; it never overrides it."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import paperforge.worker.ocr_post_match_normalize as module
from paperforge.worker.ocr_post_match_normalize import (
    _inventory_claimed_roles,
    _reassert_claimed_roles,
    post_match_normalize,
)


def _row(page, block_id, role, owner=None):
    row = {"page": page, "block_id": block_id, "role": role, "text": "text"}
    if owner is not None:
        row["_object_owner_id"] = owner
    return row


def _figures(caption="9", assets=("8",)):
    return {
        "matched_figures": [
            {
                "figure_id": "figure_001",
                "page": 1,
                "legend_block_id": caption,
                "asset_block_ids": list(assets),
            }
        ]
    }


def _tables(caption="2", asset="3"):
    return {
        "tables": [
            {
                "caption_block_id": caption,
                "page": 1,
                "asset_block_id": asset,
                "has_asset": True,
            }
        ]
    }


def _run(rows, shadow_roles, figures=None, tables=None):
    shadow = [{**row, "role": shadow_roles.get(str(row["block_id"]), row["role"])} for row in rows]
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        module,
        "normalize_document_structure",
        lambda rows, **kwargs: (SimpleNamespace(source_frontmatter_anchors={}), shadow),
    )
    monkeypatch.setattr(module, "settle_tail_and_backmatter", lambda **kwargs: None)
    try:
        return post_match_normalize(
            rows,
            figures if figures is not None else _figures(),
            tables if tables is not None else _tables(),
            document_structure=SimpleNamespace(),
        )[0]
    finally:
        monkeypatch.undo()


def test_inventory_claims_cover_captions_and_assets():
    claims, ambiguous = _inventory_claimed_roles(
        [_row(1, "2", "table_caption"), _row(1, "3", "table_html"), _row(1, "8", "figure_asset"), _row(1, "9", "figure_caption")],
        _figures(),
        _tables(),
    )
    assert claims == {
        (1, "9"): "figure_caption",
        (1, "8"): "figure_asset",
        (1, "2"): "table_caption",
        (1, "3"): "table_html",
    }
    assert ambiguous == {}


def test_duplicate_identity_is_not_protected():
    claims, ambiguous = _inventory_claimed_roles(
        [_row(1, "9", "figure_caption"), _row(1, "9", "body_paragraph")],
        _figures(),
        _tables(),
    )
    assert (1, "9") not in claims
    assert ambiguous == {(1, "9"): "duplicate_identity"}


def test_block_claimed_by_figure_and_table_is_not_protected():
    figures = _figures()
    tables = _tables(asset="8")
    claims, unsafe = _inventory_claimed_roles(
        [_row(1, "8", "figure_asset")], figures, tables
    )
    assert (1, "8") not in claims
    assert unsafe == {(1, "8"): "contested_ownership"}


def test_shadow_demotion_of_a_committed_caption_is_rejected():
    rows = [
        _row(1, "9", "figure_caption"),
        _row(1, "8", "figure_asset"),
        _row(1, "5", "body_paragraph"),
    ]
    result = _run(rows, {"9": "body_paragraph", "5": "body_paragraph"})

    protected = next(row for row in result if row["block_id"] == "9")
    assert protected["role"] == "figure_caption"
    assert protected["_post_match_role_override"] == {
        "role": "body_paragraph",
        "expected": "figure_caption",
        "source": "figure_table_inventory",
    }
    assert next(row for row in result if row["block_id"] == "5")["role"] == "body_paragraph"


def test_table_asset_claim_is_protected():
    rows = [_row(1, "3", "table_html")]
    result = _run(rows, {"3": "body_paragraph"})
    assert result[0]["role"] == "table_html"
    assert result[0]["_post_match_role_override"]["expected"] == "table_html"


def test_ambiguous_identity_keeps_the_shadow_role():
    rows = [_row(1, "9", "figure_caption"), _row(1, "9", "body_paragraph")]
    result = _run(rows, {"9": "reference_item"})
    assert [row["role"] for row in result] == ["reference_item", "reference_item"]
    assert all(row.get("_post_match_role_ambiguous") for row in result)
    assert all("_post_match_role_override" not in row for row in result)


def test_agreement_records_nothing():
    rows = [_row(1, "9", "figure_caption")]
    result = _run(rows, {})
    assert result[0]["role"] == "figure_caption"
    assert "_post_match_role_override" not in result[0]


def test_reassert_records_disagreement():
    rows = [_row(1, "9", "body")]
    _reassert_claimed_roles(rows, {(1, "9"): "figure_caption"})
    assert rows[0]["role"] == "figure_caption"
    assert rows[0]["_post_match_role_override"]["role"] == "body"
