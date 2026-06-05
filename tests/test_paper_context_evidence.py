from __future__ import annotations


def test_paper_context_includes_evidence_summary() -> None:
    from paperforge.worker.ocr_evidence import build_paper_evidence_summary

    summary = build_paper_evidence_summary(
        paper_id="KEY001",
        role_indexes={
            "body": [{"role": "body_paragraph", "text": "Text..."}],
            "captions": [{"role": "figure_caption", "text": "Figure 1."}],
            "references": [{"role": "reference_item", "text": "Smith 2024."}],
            "metadata": [{"role": "metadata_title", "text": "Paper Title"}],
            "tables": [],
        },
    )

    assert "total_evidence_blocks" in summary
    assert summary["total_evidence_blocks"] == 4
    assert "by_role" in summary
    assert summary["by_role"]["body"] == 1
    assert summary["by_role"]["captions"] == 1
    assert "has_figures" in summary or "has_tables" in summary
