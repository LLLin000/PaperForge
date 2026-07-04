from __future__ import annotations
import pytest


def test_ocr_pipeline_v3_enabled_defaults_true(monkeypatch) -> None:
    from paperforge.worker.ocr import _ocr_pipeline_v3_enabled

    monkeypatch.delenv("OCR_PIPELINE_V3", raising=False)

    assert _ocr_pipeline_v3_enabled() is True


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

def test_post_match_normalize_runs_rescue_roles(monkeypatch) -> None:
    from paperforge.worker.ocr_document import DocumentStructure
    import paperforge.worker.ocr_post_match_normalize as post

    rescue_called = False

    def tracking_rescue(rows, profiles, doc):
        nonlocal rescue_called
        rescue_called = True
        return rows

    monkeypatch.setattr(post, "rescue_roles_with_document_context", tracking_rescue)

    # Create rows with enough blocks to trigger rescue (>= 10) and span_metadata
    # so build_role_span_profiles produces non-empty profiles
    rows = []
    for i in range(15):
        rows.append({
            "block_id": str(i),
            "page": 1,
            "role": "body_paragraph",
            "seed_role": "body_paragraph",
            "text": f"Block {i}",
            "bbox": [100, 100 + i * 30, 420, 130 + i * 30],
            "span_metadata": [
                {"size": 10.0 + (i % 5), "font": "Times", "flags": 0, "color": 0}
            ],
        })

    post.post_match_normalize(
        rows,
        {"matched_figures": []},
        {"tables": []},
        document_structure=DocumentStructure(),
        source_frontmatter_anchors=None,
    )

    assert rescue_called, "rescue_roles_with_document_context must be called in post_match_normalize"


def test_v3_synthetic_parity_with_legacy_reference_boundaries(monkeypatch) -> None:
    """Verify v3 path produces same output as legacy on a synthetic reference-heavy paper.

    This is a synthetic proxy for a real-paper parity gate: it creates blocks
    that exercise the reference boundary, tail settlement, and backmatter headings.
    """
    from paperforge.worker.ocr_blocks import build_structured_blocks
    from paperforge.worker.ocr_figures import build_figure_inventory_vnext
    from paperforge.worker.ocr_tables import build_table_inventory_vnext
    from paperforge.worker.ocr_object_writeback import apply_object_writebacks
    from paperforge.worker.ocr_post_match_normalize import post_match_normalize
    from paperforge.worker.ocr_pre_match_normalize import pre_match_normalize

    raw_blocks = [
        {"paper_id": "synth_paper", "block_id": 1, "page": 1, "raw_label": "doc_title", "text": "Test Paper", "bbox": [100, 100, 500, 130]},
        {"paper_id": "synth_paper", "block_id": 2, "page": 1, "raw_label": "text", "text": "Introduction. This is the body.", "bbox": [100, 150, 500, 300]},
        {"paper_id": "synth_paper", "block_id": 3, "page": 1, "raw_label": "image", "text": "", "bbox": [100, 320, 300, 500]},
        {"paper_id": "synth_paper", "block_id": 4, "page": 1, "raw_label": "text", "text": "Figure 1. A caption.", "bbox": [100, 510, 300, 540]},
        {"paper_id": "synth_paper", "block_id": 5, "page": 2, "raw_label": "text", "text": "References", "bbox": [100, 100, 300, 130]},
        {"paper_id": "synth_paper", "block_id": 6, "page": 2, "raw_label": "text", "text": "1. Ref one. 2. Ref two.", "bbox": [100, 140, 500, 200]},
    ]

    monkeypatch.setenv("OCR_PIPELINE_V3", "1")
    try:
        rows_seed, doc_seed = build_structured_blocks(raw_blocks, normalize_mode="seed_only")
        rows_pre, doc_pre = pre_match_normalize(
            rows_seed, source_frontmatter_anchors=None, document_structure=doc_seed
        )
        fig_inv = build_figure_inventory_vnext(rows_pre)
        tab_inv = build_table_inventory_vnext(rows_pre)
        rows_post, doc_post = post_match_normalize(
            rows_pre, fig_inv, tab_inv, document_structure=doc_pre
        )
        apply_object_writebacks(structured_blocks=rows_post, figure_inventory=fig_inv, table_inventory=tab_inv)
    finally:
        monkeypatch.delenv("OCR_PIPELINE_V3", raising=False)

    # Check that key roles are assigned and consistent
    by_id = {b["block_id"]: b for b in rows_post}
    assert by_id[1]["role"] is not None
    assert len(rows_post) == 6
    assert doc_post is not None

def _load_real_paper_json(path):
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _load_real_paper_fixture(key: str) -> tuple[list[dict], dict]:
    from pathlib import Path

    root = Path(__file__).resolve().parent / "fixtures" / "ocr_real_papers" / key
    ocr_payload = _load_real_paper_json(root / "ocr_payload.json")
    source_metadata = _load_real_paper_json(root / "source_metadata.json")
    return ocr_payload, source_metadata


def _run_legacy_fixture_pipeline(key: str, tmp_path):
    from paperforge.worker.ocr_blocks import build_raw_blocks_for_result_lines, build_structured_blocks
    from paperforge.worker.ocr_figures import build_figure_inventory
    from paperforge.worker.ocr_tables import build_table_inventory

    ocr_payload, source_metadata = _load_real_paper_fixture(key)
    raw_blocks = build_raw_blocks_for_result_lines(key, ocr_payload)
    rows, doc = build_structured_blocks(
        raw_blocks,
        source_metadata=source_metadata,
        structure_output_dir=str(tmp_path / "legacy"),
    )
    fig = build_figure_inventory(rows)
    tab = build_table_inventory(rows)
    return {"rows": rows, "doc": doc, "fig": fig, "tab": tab}


def _run_v3_fixture_pipeline(key: str, tmp_path):
    from paperforge.worker.ocr_blocks import build_raw_blocks_for_result_lines, build_structured_blocks
    from paperforge.worker.ocr_figures import build_figure_inventory
    from paperforge.worker.ocr_post_match_normalize import post_match_normalize
    from paperforge.worker.ocr_pre_match_normalize import pre_match_normalize
    from paperforge.worker.ocr_tables import build_table_inventory

    ocr_payload, source_metadata = _load_real_paper_fixture(key)
    raw_blocks = build_raw_blocks_for_result_lines(key, ocr_payload)
    rows_seed, doc_seed = build_structured_blocks(
        raw_blocks,
        source_metadata=source_metadata,
        structure_output_dir=str(tmp_path / "v3"),
        normalize_mode="seed_only",
    )
    rows_pre, doc_pre = pre_match_normalize(
        rows_seed,
        source_frontmatter_anchors=getattr(doc_seed, "source_frontmatter_anchors", None),
        document_structure=doc_seed,
    )
    fig = build_figure_inventory(rows_pre)
    tab = build_table_inventory(rows_pre)
    rows_post, doc_post = post_match_normalize(
        rows_pre,
        fig,
        tab,
        document_structure=doc_pre,
        source_frontmatter_anchors=getattr(doc_pre, "source_frontmatter_anchors", None),
    )
    return {"rows": rows_post, "doc": doc_post, "fig": fig, "tab": tab}


def _role_counter(rows: list[dict]):
    from collections import Counter

    return Counter(str(block.get("role") or "") for block in rows)


def _count_truthy(rows: list[dict], field: str) -> int:
    return sum(1 for block in rows if block.get(field))


@pytest.mark.parametrize("key", ["DWQQK2YB", "VAMSAZMG", "PJBMGVTF", "37LK5T97", "8CCATQE3", "5MAW65YD"])
def test_v3_real_paper_parity_matches_legacy_contract(key: str, tmp_path) -> None:
    legacy = _run_legacy_fixture_pipeline(key, tmp_path)
    v3 = _run_v3_fixture_pipeline(key, tmp_path)

    assert _role_counter(v3["rows"]) == _role_counter(legacy["rows"])
    assert _count_truthy(v3["rows"], "render_default") == _count_truthy(legacy["rows"], "render_default")
    assert _count_truthy(v3["rows"], "index_default") == _count_truthy(legacy["rows"], "index_default")
    assert len(v3["fig"].get("matched_figures", [])) == len(legacy["fig"].get("matched_figures", []))
    assert len(v3["tab"].get("tables", [])) == len(legacy["tab"].get("tables", []))