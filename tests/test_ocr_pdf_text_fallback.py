"""Unit tests for backfill_missing_text_from_pdf."""
from pathlib import Path

import fitz

from paperforge.worker.ocr_pdf_spans import (
    _words_to_text,
    backfill_missing_text_from_pdf,
)


def _save_pdf(doc: fitz.Document, path: Path) -> None:
    doc.save(str(path))
    doc.close()


def test_words_to_text_single_line():
    words = [(10, 100, 50, 110, "Hello"), (60, 100, 100, 110, "world")]
    result = _words_to_text(words)
    assert result == "Hello world"


def test_words_to_text_multiple_lines():
    words = [
        (10, 100, 50, 110, "Line1"),
        (10, 120, 50, 130, "Line2"),
    ]
    result = _words_to_text(words)
    assert "Line1" in result
    assert "Line2" in result
    assert result.count("\n") == 1


def test_backfill_recovers_right_column_text(tmp_path: Path):
    """Create a synthetic single-page PDF with right-column text,
    construct a raw block with empty text and matching bbox.
    """
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    page.insert_text((300, 100), "The rotator cable was initially described by Clark and Harryman.", fontname="helv", fontsize=10)
    page.insert_text((300, 115), "continued text on next line", fontname="helv", fontsize=10)

    pdf_path = tmp_path / "test.pdf"
    _save_pdf(doc, pdf_path)

    page_width = 1190
    page_height = 1684

    bbox = [590, 190, 1190, 300]

    blocks = [
        {
            "raw_label": "text",
            "text": "",
            "block_content": "",
            "page": 1,
            "bbox": bbox,
            "page_width": page_width,
            "page_height": page_height,
            "span_metadata": [{"size": 10.0, "font": "Helvetica", "flags": 0, "color": 0}],
        },
        {
            "raw_label": "text",
            "text": "keep me",
            "block_content": "keep me",
            "page": 1,
            "bbox": [100, 100, 500, 200],
            "page_width": page_width,
            "page_height": page_height,
            "span_metadata": [{"size": 10.0, "font": "Helvetica", "flags": 0, "color": 0}],
        },
        {
            "raw_label": "text",
            "text": "",
            "block_content": "",
            "page": 1,
            "bbox": bbox,
            "page_width": page_width,
            "page_height": page_height,
        },
    ]

    backfill_missing_text_from_pdf(blocks, pdf_path)

    assert blocks[0]["_ocr_raw_status"] == "missing_text_recovered"
    assert blocks[0]["_text_source"] == "pdf_text_layer_fallback"
    assert len(blocks[0]["text"].strip()) > 0
    assert len(blocks[0]["block_content"].strip()) > 0
    assert blocks[0]["_original_ocr_text"] == ""
    assert "rotator cable" in blocks[0]["text"].lower()

    assert blocks[1]["text"] == "keep me"
    assert "_text_source" not in blocks[1]

    assert blocks[2]["text"] == ""
    assert "_ocr_raw_status" not in blocks[2]


def test_backfill_requires_page_dimensions(tmp_path: Path):
    """Blocks without page_width/page_height are marked unrecovered, not guessed."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((100, 100), "test text", fontname="helv", fontsize=10)

    pdf_path = tmp_path / "test.pdf"
    _save_pdf(doc, pdf_path)

    blocks = [
        {
            "raw_label": "text",
            "text": "",
            "page": 1,
            "bbox": [100, 80, 400, 130],
            "span_metadata": [{"size": 10.0, "font": "Helvetica", "flags": 0, "color": 0}],
        },
    ]

    backfill_missing_text_from_pdf(blocks, pdf_path)

    assert blocks[0]["_ocr_raw_status"] == "missing_text_unrecovered"
    assert blocks[0]["_ocr_raw_error_type"] == "missing_page_dimensions"


def test_local_reference_pdf_fallback_repairs_only_local_candidate_text() -> None:
    from paperforge.worker.ocr_document import repair_reference_entry_from_pdf_text

    block_run = [
        {"block_id": "r1", "page": 14, "bbox": [620, 900, 1100, 950], "text": "Brown T, Green S."},
        {"block_id": "r2", "page": 14, "bbox": [620, 952, 1100, 1000], "text": "N Engl J M"},
    ]
    page_text = "Body text ... Brown T, Green S. N Engl J Med. 2020;382(4):100-110. More body text"

    repaired = repair_reference_entry_from_pdf_text(block_run, page_text)
    assert "N Engl J Med" in repaired
    assert repaired.startswith("Brown T, Green S.")

def test_backfill_expanded_clip_filters_words_to_original_bbox(monkeypatch, tmp_path):
    from paperforge.worker import ocr_pdf_spans
    import fitz

    class FakePage:
        rect = fitz.Rect(0, 0, 1000, 1000)
        def get_text(self, kind, clip=None):
            if kind == "words":
                return [
                    (100, 100, 120, 110, "inside", 0, 0, 0),
                    (100, 111, 120, 121, "neighbor", 0, 0, 1),
                ]
            if kind == "text":
                return "inside neighbor"
            return []

    class FakeDoc:
        def __len__(self): return 1
        def __getitem__(self, idx): return FakePage()
        def close(self): pass

    monkeypatch.setattr(ocr_pdf_spans, "_fitz_quiet_open", lambda path: FakeDoc())
    monkeypatch.setattr(
        ocr_pdf_spans,
        "_map_ocr_bbox_to_pdf_rect",
        lambda bbox, pw, ph, page: fitz.Rect(100, 100, 120, 110),
    )

    pdf_path = tmp_path / "fake.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n")

    blocks = [{
        "page": 1,
        "bbox": [100, 100, 120, 110],
        "page_width": 1000,
        "page_height": 1000,
        "raw_label": "text",
        "text": "",
        "block_content": "",
        "span_metadata": [{"font": "Body"}],
    }]

    ocr_pdf_spans.backfill_missing_text_from_pdf(blocks, pdf_path)

    assert blocks[0]["text"] == "inside"
    assert blocks[0]["_ocr_raw_status"] == "missing_text_recovered"


def test_backfill_keeps_slightly_misaligned_words_by_center_or_overlap():
    from paperforge.worker.ocr_pdf_spans import _word_belongs_to_block
    import fitz

    block_rect = fitz.Rect(100, 100, 120, 110)

    assert _word_belongs_to_block((99, 100, 109, 110), block_rect) is True
    assert _word_belongs_to_block((121, 111, 131, 121), block_rect) is False
