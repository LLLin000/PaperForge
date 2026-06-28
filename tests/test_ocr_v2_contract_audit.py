from __future__ import annotations

import inspect


def test_render_fulltext_does_not_globally_scan_abstract_roles() -> None:
    from paperforge.worker import ocr_render

    source = inspect.getsource(ocr_render.render_fulltext_markdown)

    assert 'role") in ("abstract_heading", "abstract_body")' not in source
    assert "role') in ('abstract_heading', 'abstract_body')" not in source
    assert "abstract_span" in source


def test_render_fulltext_uses_verified_role_gate_reference_zone_when_available() -> None:
    from paperforge.worker import ocr_render

    source = inspect.getsource(ocr_render.render_fulltext_markdown)

    assert "has_verified_reference_zone" in source or "reference_zone" in source
    assert "return non_ref + refs" not in source


def test_emit_page_objects_uses_reader_as_primary_gate() -> None:
    from paperforge.worker import ocr_render

    source = inspect.getsource(ocr_render._emit_page_objects)

    assert "has_reader" in source
    assert "if not has_reader" in source or "if has_reader" in source


def test_required_roles_cannot_finish_without_accept_verification() -> None:
    from paperforge.worker.ocr_document import normalize_document_structure
    from paperforge.worker.ocr_structural_gate import VERIFY_REQUIRED

    blocks = [
        {
            "block_id": "h",
            "role": "unassigned",
            "seed_role": "abstract_heading",
            "text": "Abstract",
            "render_default": True,
        },
        {
            "block_id": "a",
            "role": "unassigned",
            "seed_role": "abstract_body",
            "text": "Real abstract.",
            "render_default": True,
        },
        {
            "block_id": "intro",
            "role": "unassigned",
            "seed_role": "section_heading",
            "text": "Introduction",
            "render_default": True,
        },
        {
            "block_id": "bad_ref",
            "role": "unassigned",
            "seed_role": "reference_item",
            "text": "[1] body-zone parameter",
            "render_default": True,
        },
    ]

    _doc, normalized = normalize_document_structure(blocks)

    offenders = [
        block
        for block in normalized
        if block.get("role") in VERIFY_REQUIRED and block.get("role_verification_status") != "ACCEPT"
    ]
    passthrough = [
        block
        for block in normalized
        if block.get("role") in VERIFY_REQUIRED and block.get("role_source") == "non_structural_seed"
    ]
    assert offenders == []
    assert passthrough == []
