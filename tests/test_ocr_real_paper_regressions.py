from __future__ import annotations

import json
from pathlib import Path

import pytest


VAULT = Path(r"D:\L\OB\Literature-hub")
OCR_ROOT = VAULT / "System" / "PaperForge" / "ocr"

PROBLEM_KEYS = ["TSCKAVIS", "CAQNW9Q2", "A8E7SRVS", "K7R8PEKW"]
CONTROL_KEYS = ["SAN9AYVR", "2GN9LMCW", "7C8829BD"]
ALL_KEYS = PROBLEM_KEYS + CONTROL_KEYS


def _paper_root(key: str) -> Path:
    return OCR_ROOT / key


def _structured_path(key: str) -> Path:
    return _paper_root(key) / "structure" / "blocks.structured.jsonl"


def _fulltext_path(key: str) -> Path:
    return _paper_root(key) / "fulltext.md"


def _health_path(key: str) -> Path:
    return _paper_root(key) / "health" / "ocr_health.json"


def _metadata_path(key: str) -> Path:
    return _paper_root(key) / "metadata" / "resolved_metadata.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _require_artifacts(key: str) -> None:
    if not VAULT.exists():
        pytest.skip(f"Vault path not available: {VAULT}")
    missing = [
        str(path)
        for path in [_structured_path(key), _fulltext_path(key), _health_path(key), _metadata_path(key)]
        if not path.exists()
    ]
    if missing:
        pytest.skip(f"OCR artifacts not present for {key}: {missing}")


@pytest.fixture(scope="session")
def rebuilt_real_papers() -> dict:
    if not VAULT.exists():
        pytest.skip(f"Vault path not available: {VAULT}")
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    result = run_derived_rebuild_for_keys(VAULT, ALL_KEYS)
    assert result.get("rebuild_count", 0) >= 1, result
    return result


@pytest.mark.parametrize("key", ALL_KEYS)
def test_real_paper_artifacts_exist(key: str) -> None:
    _require_artifacts(key)


def test_real_paper_rebuild_runs(rebuilt_real_papers: dict) -> None:
    assert rebuilt_real_papers.get("rebuild_count", 0) >= 1


BODY_RETENTION = {
    "CAQNW9Q2": {"min_body": 35, "max_non_body_insert": 8},
    "A8E7SRVS": {"min_body": 45, "max_non_body_insert": 8},
    "K7R8PEKW": {"min_body": 60, "max_non_body_insert": 8},
    "TSCKAVIS": {"min_body": 55, "max_non_body_insert": 12},
}


def _role_texts(blocks: list[dict], role: str) -> list[str]:
    return [str(block.get("text") or block.get("block_content") or "") for block in blocks if block.get("role") == role]


@pytest.mark.parametrize("key", sorted(BODY_RETENTION))
def test_problem_papers_retain_body_and_avoid_mass_insert_suppression(rebuilt_real_papers: dict, key: str) -> None:
    _require_artifacts(key)
    blocks = _read_jsonl(_structured_path(key))
    roles = [block.get("role") for block in blocks]
    thresholds = BODY_RETENTION[key]

    assert roles.count("body_paragraph") >= thresholds["min_body"], roles.count("body_paragraph")
    assert roles.count("non_body_insert") <= thresholds["max_non_body_insert"], roles.count("non_body_insert")


def test_tsckavis_frontmatter_and_key_points_are_callout(rebuilt_real_papers: dict) -> None:
    key = "TSCKAVIS"
    _require_artifacts(key)
    blocks = _read_jsonl(_structured_path(key))
    fulltext = _fulltext_path(key).read_text(encoding="utf-8", errors="replace")
    heading_text = "\n".join(
        _role_texts(blocks, "section_heading")
        + _role_texts(blocks, "subsection_heading")
        + _role_texts(blocks, "sub_subsection_heading")
    ).lower()

    # Frontmatter must not leak into content headings
    assert "review article" not in heading_text
    assert "steve stegen" not in heading_text
    assert "geert carmeliet" not in heading_text

    # Key points must render as a callout block, not suppressed
    assert "key points" in fulltext.lower()
    assert "[!NOTE]" in fulltext
    assert "skeletal stem and progenitor cells display a high metabolic flexibility" in fulltext.lower()

    # Metadata must capture title and authors from OCR blocks
    meta = _read_json(_metadata_path(key))
    assert len(meta.get("title", {}).get("value", "")) > 10, meta.get("title")
    assert len(meta.get("authors", {}).get("value", [])) > 0, meta.get("authors")
    assert meta.get("authors_display", "") != "", f"authors_display is empty: {meta}"
    assert meta.get("year", {}).get("value", 0), meta.get("year")
    assert meta.get("journal", {}).get("value", ""), meta.get("journal")
    assert meta.get("doi", {}).get("value", ""), meta.get("doi")


CONTROL_MIN_BODY = {
    "SAN9AYVR": 250,
    "2GN9LMCW": 25,
    "7C8829BD": 70,
}


@pytest.mark.parametrize("key", sorted(CONTROL_MIN_BODY))
def test_control_papers_keep_body_and_tail_stability(rebuilt_real_papers: dict, key: str) -> None:
    _require_artifacts(key)
    blocks = _read_jsonl(_structured_path(key))
    roles = [block.get("role") for block in blocks]
    fulltext = _fulltext_path(key).read_text(encoding="utf-8", errors="replace")

    assert roles.count("body_paragraph") >= CONTROL_MIN_BODY[key]
    assert any(w in fulltext for w in ["References", "references", "REFERENCE", "Bibliography"]), "Tail reference marker not found"
