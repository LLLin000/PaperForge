from __future__ import annotations


def test_evidence_object_preserves_role_page_confidence_and_asset() -> None:
    from paperforge.worker.ocr_evidence import build_evidence_hit

    hit = build_evidence_hit(
        paper_id="KEY001",
        role="figure_caption",
        page=7,
        block_id="p7_b18",
        text="Figure 3. Results.",
        asset_path="render/figures/figure_003.md",
        confidence=0.84,
        verification="has_page_crop",
    )

    assert hit["source_type"] == "figure_caption"
    assert hit["page"] == 7
    assert hit["asset"] == "render/figures/figure_003.md"
    assert hit["confidence"] == 0.84
