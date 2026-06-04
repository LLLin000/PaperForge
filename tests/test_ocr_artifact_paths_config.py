from __future__ import annotations

from pathlib import Path


def test_artifact_paths_follow_pipeline_ocr_root(tmp_path: Path) -> None:
    from paperforge.worker.ocr_artifacts import artifact_paths_for_root

    ocr_root = tmp_path / "CustomSystem" / "PaperForge" / "ocr"
    paths = artifact_paths_for_root(ocr_root, "KEY001")

    assert paths.paper_root == ocr_root / "KEY001"
    assert paths.meta_json == ocr_root / "KEY001" / "meta.json"


def test_artifact_paths_for_key_still_works(tmp_path: Path) -> None:
    from paperforge.worker.ocr_artifacts import artifact_paths_for_key

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "paperforge.json").write_text(
        '{"vault_config":{"system_dir":"System","resources_dir":"Resources"}}',
        encoding="utf-8",
    )

    paths = artifact_paths_for_key(vault, "KEY001")
    assert paths.paper_root.as_posix().endswith("/ocr/KEY001")
    assert paths.meta_json.as_posix().endswith("/ocr/KEY001/meta.json")


def test_artifact_paths_for_root_has_all_fields(tmp_path: Path) -> None:
    from paperforge.worker.ocr_artifacts import artifact_paths_for_root

    ocr_root = tmp_path / "ocr"
    paths = artifact_paths_for_root(ocr_root, "KEY001")

    assert paths.paper_root == ocr_root / "KEY001"
    assert paths.meta_json == ocr_root / "KEY001" / "meta.json"
    assert paths.result_json == ocr_root / "KEY001" / "json" / "result.json"
    assert paths.compat_fulltext == ocr_root / "KEY001" / "fulltext.md"
    assert paths.raw_meta == ocr_root / "KEY001" / "raw" / "raw_meta.json"
    assert paths.source_metadata == ocr_root / "KEY001" / "raw" / "source_metadata.json"
    assert paths.blocks_raw == ocr_root / "KEY001" / "canonical" / "blocks.raw.jsonl"
    assert paths.blocks_structured == ocr_root / "KEY001" / "structure" / "blocks.structured.jsonl"
