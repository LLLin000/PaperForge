import json
from pathlib import Path


def _minimal_results() -> list[dict]:
    return [{
        "layoutParsingResults": [{
            "prunedResult": {
                "width": 600,
                "height": 800,
                "parsing_res_list": [
                    {"block_label": "doc_title", "block_content": "Example", "block_bbox": [0, 0, 100, 20], "block_order": 0},
                    {"block_label": "text", "block_content": "Body", "block_bbox": [0, 40, 100, 80], "block_order": 1},
                ],
            }
        }]
    }]


def test_initial_ocr_persists_machine_hash_without_rebuild_fields(tmp_path: Path, monkeypatch) -> None:
    from paperforge.worker.ocr import postprocess_ocr_result

    vault = tmp_path
    key = "K1"
    paper_root = vault / "System" / "PaperForge" / "ocr" / key
    (paper_root / "meta.json").parent.mkdir(parents=True, exist_ok=True)
    (paper_root / "meta.json").write_text('{"source_pdf": ""}', encoding="utf-8")

    postprocess_ocr_result(vault, key, _minimal_results())

    meta = json.loads((paper_root / "meta.json").read_text(encoding="utf-8"))
    assert meta["machine_fulltext_hash"].startswith("sha256:")
    assert "rebuild_finished_at" not in meta or not meta["rebuild_finished_at"]
    assert int(meta.get("rebuild_count") or 0) == 0
