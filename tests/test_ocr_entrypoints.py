from __future__ import annotations

import inspect


def test_ocr_v2_entrypoints_and_signatures_are_document_pipeline() -> None:
    from paperforge.worker import ocr_blocks, ocr_document, ocr_health, ocr_render

    assert hasattr(ocr_blocks, "build_structured_blocks")
    assert hasattr(ocr_document, "normalize_document_structure")
    assert hasattr(ocr_render, "render_fulltext_markdown")
    assert hasattr(ocr_health, "build_ocr_health")

    blocks_sig = inspect.signature(ocr_blocks.build_structured_blocks)
    render_sig = inspect.signature(ocr_render.render_fulltext_markdown)

    assert "raw_blocks" in blocks_sig.parameters
    assert render_sig.parameters["structured_blocks"].kind is inspect.Parameter.KEYWORD_ONLY
    assert render_sig.parameters["document_structure"].kind is inspect.Parameter.KEYWORD_ONLY
    assert render_sig.parameters["reader_payload"].kind is inspect.Parameter.KEYWORD_ONLY
