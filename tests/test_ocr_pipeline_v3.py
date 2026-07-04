from __future__ import annotations


def test_ocr_pipeline_v3_enabled_defaults_false(monkeypatch) -> None:
    from paperforge.worker.ocr import _ocr_pipeline_v3_enabled

    monkeypatch.delenv("OCR_PIPELINE_V3", raising=False)

    assert _ocr_pipeline_v3_enabled() is False


def test_ocr_pipeline_v3_enabled_truthy(monkeypatch) -> None:
    from paperforge.worker.ocr import _ocr_pipeline_v3_enabled

    monkeypatch.setenv("OCR_PIPELINE_V3", "1")

    assert _ocr_pipeline_v3_enabled() is True


def test_build_structured_blocks_seed_only_skips_legacy_normalize(monkeypatch) -> None:
    import paperforge.worker.ocr_document as ocr_document
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "test_paper",
            "block_id": "r1",
            "page": 1,
            "raw_label": "text",
            "raw_order": 0,
            "text": "Minimal body text.",
            "bbox": [100, 100, 420, 140],
            "page_width": 612,
            "page_height": 792,
        }
    ]

    rows, doc = build_structured_blocks(raw_blocks, normalize_mode="seed_only")

    assert len(rows) == 1
    assert rows[0]["role"] == rows[0]["seed_role"]
    assert doc is not None


def test_pre_match_normalize_preserves_public_role_and_sets_role_candidate(monkeypatch) -> None:
    from paperforge.worker.ocr_document import DocumentStructure
    import paperforge.worker.ocr_pre_match_normalize as pre

    def fake_normalize(rows, source_frontmatter_anchors=None, pdf_path=None):
        shadow_rows = [dict(r) for r in rows]
        shadow_rows[0]["role"] = "figure_caption_candidate"
        return DocumentStructure(), shadow_rows

    monkeypatch.setattr(pre, "normalize_document_structure", fake_normalize)

    rows = [
        {
            "block_id": "c1",
            "page": 1,
            "role": "body_paragraph",
            "seed_role": "body_paragraph",
            "text": "Figure 1. Example caption text.",
            "bbox": [100, 100, 520, 160],
        }
    ]

    out_rows, doc = pre.pre_match_normalize(
        rows, source_frontmatter_anchors=None, document_structure=DocumentStructure()
    )

    assert out_rows[0]["role"] == "body_paragraph"
    assert out_rows[0]["role_candidate"] == "figure_caption_candidate"
    assert doc is not None


def test_figure_inventory_accepts_role_candidate_caption_blocks() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory_vnext

    blocks = [
        {
            "block_id": "cap1",
            "page": 2,
            "role": "body_paragraph",
            "role_candidate": "figure_caption_candidate",
            "seed_role": "figure_caption",
            "raw_label": "figure_title",
            "zone": "display_zone",
            "style_family": "legend_like",
            "marker_signature": {"type": "figure_number"},
            "text": "Figure 1. Example caption",
            "bbox": [100, 100, 420, 140],
        },
        {
            "block_id": "asset1",
            "page": 2,
            "role": "media_asset",
            "role_candidate": "media_asset",
            "seed_role": "media_asset",
            "raw_label": "image",
            "zone": "display_zone",
            "text": "",
            "bbox": [100, 160, 420, 380],
        },
    ]

    inv = build_figure_inventory_vnext(blocks)

    assert inv.get("matched_figures") or inv.get("figure_legends")


def test_table_inventory_accepts_role_candidate_caption_blocks() -> None:
    from paperforge.worker.ocr_tables import build_table_inventory_vnext

    blocks = [
        {
            "block_id": "cap1",
            "page": 3,
            "role": "body_paragraph",
            "role_candidate": "table_caption_candidate",
            "seed_role": "table_caption",
            "raw_label": "figure_title",
            "zone": "display_zone",
            "style_family": "table_caption_like",
            "marker_signature": {"type": "table_number"},
            "text": "Table 1. Outcomes",
            "bbox": [100, 100, 420, 140],
        },
        {
            "block_id": "asset1",
            "page": 3,
            "role": "media_asset",
            "role_candidate": "media_asset",
            "seed_role": "media_asset",
            "raw_label": "table",
            "zone": "display_zone",
            "text": "",
            "bbox": [100, 160, 420, 380],
        },
    ]

    inv = build_table_inventory_vnext(blocks)

    assert inv.get("tables")


def test_post_match_normalize_commits_shadow_role_back_to_public_role(monkeypatch) -> None:
    from paperforge.worker.ocr_document import DocumentStructure
    import paperforge.worker.ocr_post_match_normalize as post

    def fake_normalize(rows, source_frontmatter_anchors=None, pdf_path=None):
        shadow_rows = [dict(r) for r in rows]
        shadow_rows[0]["role"] = "figure_caption"
        shadow_rows[0]["role_source"] = "shadow_post_match"
        return DocumentStructure(), shadow_rows

    monkeypatch.setattr(post, "normalize_document_structure", fake_normalize)

    rows = [
        {
            "block_id": "c1",
            "page": 1,
            "role": "body_paragraph",
            "seed_role": "body_paragraph",
            "role_candidate": "figure_caption_candidate",
            "text": "Figure 1. Example caption text.",
            "bbox": [100, 100, 520, 160],
        }
    ]

    out_rows, doc = post.post_match_normalize(
        rows,
        {"matched_figures": []},
        {"tables": []},
        document_structure=DocumentStructure(),
        source_frontmatter_anchors=None,
    )

    assert out_rows[0]["role"] == "figure_caption"
    assert out_rows[0]["role_candidate"] == "figure_caption_candidate"
    assert out_rows[0]["role_source"] == "shadow_post_match"
    assert doc is not None



def test_build_structured_blocks_legacy_default_still_matches_seed_contract() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "test_paper",
            "block_id": "r1",
            "page": 1,
            "raw_label": "text",
            "text": "Minimal body text.",
            "bbox": [100, 100, 420, 140],
        }
    ]

    rows, _ = build_structured_blocks(raw_blocks)

    assert rows[0]["role"]
    assert rows[0]["seed_role"]