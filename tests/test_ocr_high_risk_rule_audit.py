from __future__ import annotations

from pathlib import Path


def test_high_risk_rule_audit_has_required_sections() -> None:
    report = Path("docs/ocr/high-risk-rule-audit.md")
    assert report.exists()
    text = report.read_text(encoding="utf-8")

    required = [
        "## Production OCR Chain",
        "## Direct Role Mutations",
        "## Direct Object Matches",
        "## Direct Reorder Decisions",
        "## Renderer Inference",
        "## Remediation Map",
        "## Baseline Counts",
    ]
    for heading in required:
        assert heading in text

    for metric in [
        "direct_role_mutation_count",
        "direct_object_match_count",
        "direct_reorder_decision_count",
        "direct_renderer_inference_count",
    ]:
        assert metric in text
