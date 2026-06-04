from __future__ import annotations
from pathlib import Path


def test_phase1_artifact_layout_is_paper_local(tmp_path: Path) -> None:
    from paperforge.worker.ocr_artifacts import artifact_paths_for_key

    vault = tmp_path / "vault"
    vault.mkdir()
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
