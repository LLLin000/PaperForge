"""post-match must not undo an explicit author-bio classification."""

from __future__ import annotations

import paperforge.worker.ocr_post_match_normalize as module


def test_bio_role_survives_reference_zone_fallback(monkeypatch) -> None:
    rows = [
        {
            "page": 1,
            "block_id": "bio",
            "role": "backmatter_body",
            "seed_role": "footnote",
            "text": "Yuxin Bai is now a postdoctoral fellow.",
            "_object_owner_family": "author_bio",
            "render_default": True,
        }
    ]
    shadow_rows = [
        dict(rows[0], role="reference_item", render_default=True, role_source="reference_zone_fallback")
    ]

    class _Doc:
        source_frontmatter_anchors = {"has_anchors": True}

    monkeypatch.setattr(module, "normalize_document_structure", lambda rows, **kwargs: (_Doc(), shadow_rows))
    monkeypatch.setattr(module, "settle_tail_and_backmatter", lambda **kwargs: None)

    result, _ = module.post_match_normalize(
        rows,
        {"matched_figures": []},
        {"tables": []},
        document_structure=_Doc(),
        source_frontmatter_anchors={"has_anchors": True},
    )
    assert result[0]["role"] == "backmatter_body"


def test_non_bio_block_takes_the_shadow_role(monkeypatch) -> None:
    rows = [{"page": 1, "block_id": "ref", "role": "reference_item", "text": "[1] A. Author, Biomaterials 2023."}]
    shadow_rows = [dict(rows[0], role="reference_item")]

    class _Doc:
        source_frontmatter_anchors = {"has_anchors": True}

    monkeypatch.setattr(module, "normalize_document_structure", lambda rows, **kwargs: (_Doc(), shadow_rows))
    monkeypatch.setattr(module, "settle_tail_and_backmatter", lambda **kwargs: None)

    result, _ = module.post_match_normalize(
        rows,
        {"matched_figures": []},
        {"tables": []},
        document_structure=_Doc(),
        source_frontmatter_anchors={"has_anchors": True},
    )
    assert result[0]["role"] == "reference_item"
