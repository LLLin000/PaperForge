from __future__ import annotations

import json
from pathlib import Path

from tests.conftest import canonical_test_config


def test_phase1_artifact_layout_is_paper_local(tmp_path: Path) -> None:
    from paperforge.worker.ocr_artifacts import artifact_paths_for_key

    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    paths = artifact_paths_for_key(vault, "ABCD1234")
    assert paths.paper_root.as_posix().endswith("/ocr/ABCD1234")
    assert paths.raw_meta.as_posix().endswith("/ocr/ABCD1234/raw/raw_meta.json")
    assert paths.source_metadata.as_posix().endswith("/ocr/ABCD1234/raw/source_metadata.json")
    assert paths.blocks_raw.as_posix().endswith("/ocr/ABCD1234/canonical/blocks.raw.jsonl")
    assert paths.blocks_structured.as_posix().endswith("/ocr/ABCD1234/structure/blocks.structured.jsonl")


def test_raw_and_derived_version_payloads_have_separate_namespaces() -> None:
    from paperforge.worker.ocr_artifacts import build_version_payload

    payload = build_version_payload(
        pdf_fingerprint="sha256:abc",
        result_json_hash="sha256:def",
        ocr_model="PaddleOCR-VL-1.6",
    )
    assert "raw_version" in payload
    assert "derived_version" in payload
    assert payload["raw_version"]["ocr_model"] == "PaddleOCR-VL-1.6"
    assert "renderer_version" in payload["derived_version"]


def test_cleanup_ocr_cache_removes_page_cache_files(tmp_path: Path) -> None:
    from paperforge.worker.ocr_artifacts import cleanup_ocr_artifact_cache

    paper_root = tmp_path / "paper"
    pages_dir = paper_root / "pages"
    pages_dir.mkdir(parents=True)
    (pages_dir / "page_001.jpg").write_text("fake jpg", encoding="utf-8")
    (pages_dir / "page_002.png").write_text("fake png", encoding="utf-8")
    # Canonical data must NOT be touched
    canonical_dir = paper_root / "canonical"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "blocks.raw.jsonl").write_text("{}", encoding="utf-8")

    report = cleanup_ocr_artifact_cache(paper_root)

    assert len(report["pages_removed"]) == 2
    assert "page_001.jpg" in report["pages_removed"]
    assert "page_002.png" in report["pages_removed"]
    assert not pages_dir.exists(), "pages dir should be removed when empty"
    assert canonical_dir.exists(), "canonical data must survive"


def test_cleanup_ocr_cache_dry_run_does_not_delete(tmp_path: Path) -> None:
    from paperforge.worker.ocr_artifacts import cleanup_ocr_artifact_cache

    paper_root = tmp_path / "paper"
    pages_dir = paper_root / "pages"
    pages_dir.mkdir(parents=True)
    (pages_dir / "page_001.jpg").write_text("fake", encoding="utf-8")

    report = cleanup_ocr_artifact_cache(paper_root, dry_run=True)

    assert len(report["pages_removed"]) == 1
    assert pages_dir.exists(), "dry run must not delete files"
    assert (pages_dir / "page_001.jpg").exists(), "dry run must not delete files"


def test_document_structure_json_includes_compatibility_anchor_artifacts(tmp_path: Path) -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw_blocks = [
        {
            "paper_id": "KEY001",
            "page": 1,
            "block_id": "p1_b1",
            "raw_label": "doc_title",
            "raw_order": 0,
            "bbox": [100, 60, 700, 120],
            "text": "Canonical Title",
            "page_width": 1200,
            "page_height": 1600,
            "span_metadata": [{"font": "Times-Bold", "size": 18.0, "flags": 16, "color": 0}],
        },
        {
            "paper_id": "KEY001",
            "page": 3,
            "block_id": "p3_b1",
            "raw_label": "text",
            "raw_order": 1,
            "bbox": [110, 120, 370, 280],
            "text": "Long body text A " * 8,
            "page_width": 1200,
            "page_height": 1600,
            "span_metadata": [{"font": "Times-Roman", "size": 9.0, "flags": 0, "color": 0}] * 8,
        },
        {
            "paper_id": "KEY001",
            "page": 4,
            "block_id": "p4_b1",
            "raw_label": "text",
            "raw_order": 2,
            "bbox": [112, 120, 374, 280],
            "text": "Long body text B " * 8,
            "page_width": 1200,
            "page_height": 1600,
            "span_metadata": [{"font": "Times-Roman", "size": 9.0, "flags": 0, "color": 0}] * 8,
        },
        {
            "paper_id": "KEY001",
            "page": 8,
            "block_id": "p8_b1",
            "raw_label": "paragraph_title",
            "raw_order": 3,
            "bbox": [110, 120, 320, 160],
            "text": "References",
            "page_width": 1200,
            "page_height": 1600,
            "span_metadata": [{"font": "Times-Bold", "size": 10.0, "flags": 16, "color": 0}],
        },
        {
            "paper_id": "KEY001",
            "page": 8,
            "block_id": "p8_b2",
            "raw_label": "text",
            "raw_order": 4,
            "bbox": [110, 180, 400, 260],
            "text": "[1] Example reference entry with enough tokens to be reference-like.",
            "page_width": 1200,
            "page_height": 1600,
            "span_metadata": [{"font": "Times-Roman", "size": 8.5, "flags": 0, "color": 0}] * 6,
        },
        {
            "paper_id": "KEY001",
            "page": 8,
            "block_id": "p8_b3",
            "raw_label": "text",
            "raw_order": 5,
            "bbox": [112, 270, 404, 350],
            "text": "[2] Another reference entry with enough tokens to be reference-like.",
            "page_width": 1200,
            "page_height": 1600,
            "span_metadata": [{"font": "Times-Roman", "size": 8.5, "flags": 0, "color": 0}] * 6,
        },
    ]

    structure_dir = tmp_path / "structure"
    structure_dir.mkdir()

    build_structured_blocks(raw_blocks, structure_output_dir=structure_dir)

    payload = json.loads((structure_dir / "document_structure.json").read_text(encoding="utf-8"))

    assert payload["structural_signatures"]
    assert payload["anchors"]["body_family_anchor"]["status"] == "ACCEPT"
    assert payload["anchors"]["reference_family_anchor"]["status"] == "ACCEPT"
    assert payload["zones"]["body_zone"]["status"] == "ACCEPT"
    assert payload["zones"]["reference_zone"]["status"] == "ACCEPT"


def test_document_structure_write_skipped_when_oversized(tmp_path: Path, monkeypatch) -> None:
    """2026-07-06 incident guard: an abnormally large document_structure
    payload (up to 1.6 GB from bloated block_indices) must NOT be written —
    the dump has no production reader, so skip it and log instead of filling
    the disk."""
    import dataclasses

    from paperforge.worker import ocr_blocks

    @dataclasses.dataclass
    class _Dummy:
        body_end_page: int = 10
        zones: list = dataclasses.field(default_factory=list)

    monkeypatch.setattr(ocr_blocks, "DOC_STRUCTURE_MAX_BYTES", 64)
    out = tmp_path / "structure"
    ocr_blocks._write_document_structure_json(_Dummy(), out)
    assert not (out / "document_structure.json").exists()


def test_document_structure_write_happens_when_normal(tmp_path: Path) -> None:
    """Normal payloads still write (the guard must not break healthy runs)."""
    import dataclasses

    from paperforge.worker import ocr_blocks

    @dataclasses.dataclass
    class _Dummy:
        body_end_page: int = 10
        zones: list = dataclasses.field(default_factory=list)

    out = tmp_path / "structure"
    ocr_blocks._write_document_structure_json(_Dummy(), out)
    payload = json.loads((out / "document_structure.json").read_text(encoding="utf-8"))
    assert payload["body_end_page"] == 10


def test_reference_zones_degrades_on_abnormal_block_count(tmp_path: Path, monkeypatch) -> None:
    """Zone indices are bounded by the blocks list; an abnormally huge list
    (corrupted input) must yield NO zones rather than ballooned arrays."""
    from paperforge.worker import ocr_document

    monkeypatch.setattr(ocr_document, "_MAX_BLOCKS_FOR_ZONES", 10)
    blocks = [{"role": "reference_heading", "page": 1, "bbox": [0, 0, 100, 100]}] + [
        {"role": "reference_item", "page": 1, "bbox": [0, 110, 100, 200]}
    ] * 20
    zones = ocr_document._detect_reference_zones(blocks, {})
    assert zones == []
