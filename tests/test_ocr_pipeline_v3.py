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
