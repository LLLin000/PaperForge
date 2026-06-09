from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

REAL_VAULT_ENV = "PAPERFORGE_REAL_OCR_VAULT"
REAL_KEYS_ENV = "PAPERFORGE_REAL_OCR_KEYS"

PROBLEM_KEYS = ["TSCKAVIS", "CAQNW9Q2", "A8E7SRVS", "K7R8PEKW", "DWQQK2YB", "M36WA39N"]
CONTROL_KEYS = ["SAN9AYVR", "2GN9LMCW", "7C8829BD"]


def _real_ocr_vault() -> Path | None:
    value = os.environ.get(REAL_VAULT_ENV)
    return Path(value) if value else None


def _real_ocr_keys() -> list[str]:
    value = os.environ.get(REAL_KEYS_ENV, "")
    return [k.strip() for k in value.split(",") if k.strip()]


def _get_vault() -> Path:
    vault = _real_ocr_vault()
    if vault is None:
        pytest.skip(f"Set {REAL_VAULT_ENV} and {REAL_KEYS_ENV} for real OCR integration tests")
    return vault


def _get_ocr_root(vault: Path) -> Path:
    return vault / "System" / "PaperForge" / "ocr"


def _get_keys() -> list[str]:
    keys = _real_ocr_keys()
    if not keys:
        vault = _real_ocr_vault()
        if vault is None:
            pytest.skip(f"Set {REAL_VAULT_ENV} and {REAL_KEYS_ENV} for real OCR integration tests")
        return PROBLEM_KEYS + CONTROL_KEYS
    return keys


def _paper_root(ocr_root: Path, key: str) -> Path:
    return ocr_root / key


def _structured_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "structure" / "blocks.structured.jsonl"


def _fulltext_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "fulltext.md"


def _health_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "health" / "ocr_health.json"


def _metadata_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "metadata" / "resolved_metadata.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _require_artifacts(ocr_root: Path, key: str) -> None:
    missing = [
        str(path)
        for path in [
            _structured_path(ocr_root, key),
            _fulltext_path(ocr_root, key),
            _health_path(ocr_root, key),
            _metadata_path(ocr_root, key),
        ]
        if not path.exists()
    ]
    if missing:
        pytest.skip(f"OCR artifacts not present for {key}: {missing}")


@pytest.fixture(scope="session")
def _vault() -> Path:
    return _get_vault()


@pytest.fixture(scope="session")
def _ocr_root(_vault: Path) -> Path:
    return _get_ocr_root(_vault)


@pytest.fixture(scope="session")
def _all_keys() -> list[str]:
    return _get_keys()


@pytest.fixture(scope="session")
def rebuilt_real_papers(_vault: Path, _all_keys: list[str]) -> dict:
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    result = run_derived_rebuild_for_keys(_vault, _all_keys)
    assert result.get("rebuild_count", 0) >= 1, result
    return result


@pytest.mark.parametrize("key", PROBLEM_KEYS + CONTROL_KEYS)
def test_real_paper_artifacts_exist(_ocr_root: Path, key: str) -> None:
    _require_artifacts(_ocr_root, key)


def test_real_paper_rebuild_runs(rebuilt_real_papers: dict) -> None:
    assert rebuilt_real_papers.get("rebuild_count", 0) >= 1


BODY_RETENTION = {
    "CAQNW9Q2": {"min_body": 28, "max_non_body_insert": 8},
    "A8E7SRVS": {"min_body": 45, "max_non_body_insert": 8},
    # K7R8PEKW remains in the problem cohort as a generic body/reference retention guard.
    # It does not yet have a paper-specific recovery contract in this file.
    "K7R8PEKW": {"min_body": 60, "max_non_body_insert": 8},
    "TSCKAVIS": {"min_body": 50, "max_non_body_insert": 12},
    "DWQQK2YB": {"min_body": 25, "max_non_body_insert": 12},
    "M36WA39N": {"min_body": 45, "max_non_body_insert": 8},
}


def _role_texts(blocks: list[dict], role: str) -> list[str]:
    return [str(block.get("text") or block.get("block_content") or "") for block in blocks if block.get("role") == role]


@pytest.mark.parametrize("key", sorted(BODY_RETENTION))
def test_problem_papers_retain_body_and_avoid_mass_insert_suppression(
    rebuilt_real_papers: dict, _ocr_root: Path, key: str
) -> None:
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))
    roles = [block.get("role") for block in blocks]
    thresholds = BODY_RETENTION[key]

    assert roles.count("body_paragraph") >= thresholds["min_body"], roles.count("body_paragraph")
    assert roles.count("non_body_insert") <= thresholds["max_non_body_insert"], roles.count("non_body_insert")


def test_a8e7srvs_no_frontmatter_body_before_introduction(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    key = "A8E7SRVS"
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))

    intro_idx = len(blocks)
    for idx, b in enumerate(blocks):
        if (
            b.get("role") in ("section_heading", "subsection_heading")
            and "introduction" in str(b.get("text", "")).lower()
        ):
            intro_idx = idx
            break

    assert intro_idx < len(blocks), "No 'Introduction' heading found in A8E7SRVS"

    before_intro = blocks[:intro_idx]
    fm_bodies = [
        b
        for b in before_intro
        if b.get("role") == "body_paragraph"
        and any(
            s in (b.get("text") or "").lower()
            for s in [
                "received:",
                "accepted:",
                "published online",
                "copyright",
                "each author certifies",
                "icmje conflict",
            ]
        )
    ]
    assert len(fm_bodies) == 0, (
        f"Frontmatter-side text leaked into body_paragraph before Introduction "
        f"(block_ids={[b['block_id'] for b in fm_bodies]})"
    )


def test_tsckavis_frontmatter_and_key_points_are_callout(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    key = "TSCKAVIS"
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))
    fulltext = _fulltext_path(_ocr_root, key).read_text(encoding="utf-8", errors="replace")
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
    meta = _read_json(_metadata_path(_ocr_root, key))
    assert len(meta.get("title", {}).get("value", "")) > 10, meta.get("title")
    assert len(meta.get("authors", {}).get("value", [])) > 0, meta.get("authors")
    assert meta.get("authors_display", "") != "", f"authors_display is empty: {meta}"
    assert meta.get("year", {}).get("value", 0), meta.get("year")
    assert meta.get("journal", {}).get("value", ""), meta.get("journal")
    assert meta.get("doi", {}).get("value", ""), meta.get("doi")


def test_tsckavis_no_table_display_as_heading(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    key = "TSCKAVIS"
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))

    heading_text = "\n".join(
        _role_texts(blocks, "section_heading")
        + _role_texts(blocks, "subsection_heading")
        + _role_texts(blocks, "sub_subsection_heading")
    ).lower()

    assert "published online" not in heading_text, "'Published online' leaked into heading roles for TSCKAVIS"

    body_with_fig = [
        b
        for b in blocks
        if b.get("role") == "body_paragraph"
        and b.get("text", "").strip().lower().startswith("fig. ")
        and any(c.isdigit() for c in b.get("text", "")[:10])
    ]
    assert len(body_with_fig) == 0, (
        f"Figure-like text in body_paragraph: block_ids={[b['block_id'] for b in body_with_fig]}"
    )


CONTROL_MIN_BODY = {
    "SAN9AYVR": 235,
    "2GN9LMCW": 25,
    "7C8829BD": 65,
}


@pytest.mark.parametrize("key", sorted(CONTROL_MIN_BODY))
def test_control_papers_keep_body_and_tail_stability(rebuilt_real_papers: dict, _ocr_root: Path, key: str) -> None:
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))
    roles = [block.get("role") for block in blocks]
    fulltext = _fulltext_path(_ocr_root, key).read_text(encoding="utf-8", errors="replace")

    assert roles.count("body_paragraph") >= CONTROL_MIN_BODY[key]
    assert any(w in fulltext for w in ["References", "references", "REFERENCE", "Bibliography"]), (
        "Tail reference marker not found"
    )


@pytest.mark.parametrize("key", PROBLEM_KEYS)
def test_problem_papers_keep_reference_roles_and_exclude_legend_family_from_body(
    rebuilt_real_papers: dict,
    _ocr_root: Path,
    key: str,
) -> None:
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))

    assert any(block.get("role") == "reference_item" for block in blocks)
    assert any(block.get("style_family") for block in blocks), f"No style_family artifacts found for {key}"
    assert not any(
        block.get("role") == "body_paragraph"
        and block.get("style_family") in {"legend_like", "table_caption_like", "reference_like"}
        for block in blocks
    )


def test_dwqqk2yb_post_preproof_not_body(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    key = "DWQQK2YB"
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))

    corr_bodies = [
        b
        for b in blocks
        if b.get("role") == "body_paragraph"
        and any(
            phrase in (b.get("text") or "").lower()
            for phrase in ["corresponding author", "correspondence", "highlights"]
        )
    ]
    assert len(corr_bodies) == 0, (
        f"Post-preproof frontmatter leaked into body_paragraph: block_ids={[b['block_id'] for b in corr_bodies]}"
    )

    total_refs = sum(1 for b in blocks if b.get("role") == "reference_item")
    body_zone_refs = sum(1 for b in blocks if b.get("zone") == "body_zone" and b.get("role") == "reference_item")
    assert body_zone_refs < total_refs, f"All {total_refs} reference items remain in body_zone for {key}"


def test_m36wa39n_editorial_furniture_not_body(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    key = "M36WA39N"
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))
    body_text = "\n".join(str(b.get("text", "")) for b in blocks if b.get("role") == "body_paragraph").lower()

    forbidden = ["edited by:", "reviewed by:", "correspondence:", "specialty section:", "citation:"]
    for phrase in forbidden:
        assert phrase not in body_text, f"'{phrase}' found in body_paragraph for {key}"

    tail_phrases = ["ethics statement", "author contributions"]
    for phrase in tail_phrases:
        assert phrase not in body_text, f"'{phrase}' collapsed into body_paragraph for {key}"


def test_caqnw9q2_heading_preservation_and_ref_classification(rebuilt_real_papers: dict, _ocr_root: Path) -> None:
    key = "CAQNW9Q2"
    _require_artifacts(_ocr_root, key)
    blocks = _read_jsonl(_structured_path(_ocr_root, key))

    headings = [
        b for b in blocks if b.get("role") in ("section_heading", "subsection_heading", "sub_subsection_heading")
    ]
    assert len(headings) >= 5, f"Too few headings ({len(headings)}) for {key}"

    heading_text = "\n".join(_role_texts(blocks, "section_heading")).lower()
    assert "conclusion" in heading_text, f"'Conclusion' heading not found for {key}"

    ref_items = [b for b in blocks if b.get("role") == "reference_item"]
    ref_like = [b for b in ref_items if b.get("style_family") == "reference_like"]
    assert len(ref_like) > 0, (
        f"No reference items have reference_like style_family for {key} "
        f"(style families present: {set(b.get('style_family') for b in ref_items)})"
    )
