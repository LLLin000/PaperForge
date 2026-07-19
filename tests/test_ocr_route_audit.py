from __future__ import annotations

from pathlib import Path


def test_route_audit_document_exists_and_names_production_chain() -> None:
    doc = Path("docs/ocr/route-audit.md")
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    required = [
        "result.json",
        "blocks.raw",
        "blocks.structured",
        "document_structure",
        "figure_inventory",
        "table_inventory",
        "objects",
        "fulltext",
        "health",
        "index",
    ]
    for token in required:
        assert token in text


def test_route_audit_classifies_legacy_or_experimental_modules() -> None:
    text = Path("docs/ocr/route-audit.md").read_text(encoding="utf-8")
    for module in ["ocr_orchestrator.py", "ocr_layout.py", "ocr_attach.py", "ocr_emit.py"]:
        matching_lines = [line for line in text.splitlines() if module in line]
        assert matching_lines, f"{module} must be listed in route audit"
        assert any(
            label in line
            for line in matching_lines
            for label in ["not used in production path", "experimental", "delete", "production"]
        ), f"{module} must have its own disposition label"


def test_non_production_modules_are_marked_or_absent() -> None:
    modules = [
        Path("paperforge/worker/ocr_orchestrator.py"),
        Path("paperforge/worker/ocr_layout.py"),
        Path("paperforge/worker/ocr_attach.py"),
        Path("paperforge/worker/ocr_emit.py"),
    ]
    for path in modules:
        if path.exists():
            text = path.read_text(encoding="utf-8")
            assert "not used in the OCR production path" in text
