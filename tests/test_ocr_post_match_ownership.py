"""Post-match normalization consumes ownership; it never overrides it."""

from __future__ import annotations

from paperforge.worker.ocr_post_match_normalize import (
    _claimed_role_keys,
    _reassert_claimed_roles,
)


def _row(page, block_id, role, owner=None):
    row = {"page": page, "block_id": block_id, "role": role}
    if owner is not None:
        row["_object_owner_id"] = owner
    return row


def test_claimed_role_is_restored_and_the_disagreement_is_recorded():
    rows = [_row(1, "9", "figure_caption", owner="figure_001")]
    claimed = _claimed_role_keys(rows)

    rows[0]["role"] = "body"  # normalize demotes it
    _reassert_claimed_roles(rows, claimed)

    assert rows[0]["role"] == "figure_caption"
    assert rows[0]["_post_match_role_override"] == {
        "role": "body",
        "expected": "figure_caption",
    }


def test_unclaimed_rows_keep_their_normalized_role():
    rows = [_row(1, "2", "body"), _row(1, "9", "figure_caption", owner="figure_001")]
    claimed = _claimed_role_keys(rows)

    rows[0]["role"] = "reference_item"
    rows[1]["role"] = "body"
    _reassert_claimed_roles(rows, claimed)

    assert rows[0]["role"] == "reference_item"
    assert "_post_match_role_override" not in rows[0]
    assert rows[1]["role"] == "figure_caption"


def test_agreement_records_nothing():
    rows = [_row(1, "9", "table_html", owner="table_1")]
    _reassert_claimed_roles(rows, _claimed_role_keys(rows))
    assert rows[0]["role"] == "table_html"
    assert "_post_match_role_override" not in rows[0]
