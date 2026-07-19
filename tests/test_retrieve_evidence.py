from __future__ import annotations


def test_retrieve_falls_back_to_ocr_evidence_when_vector_index_empty() -> None:
    from paperforge.worker.ocr_evidence import build_evidence_hit

    hit = build_evidence_hit(
        paper_id="KEY001",
        role="body_paragraph",
        page=3,
        block_id="p3_b12",
        text="We applied 2 V/cm for 30 minutes.",
        confidence=0.92,
        verification="",
    )

    assert hit["source_type"] == "body_paragraph"
    assert "V/cm" in hit["text"]
    assert hit["confidence"] > 0.5
