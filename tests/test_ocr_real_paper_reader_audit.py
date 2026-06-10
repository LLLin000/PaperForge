from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

import pytest


REAL_VAULT_ENV = "PAPERFORGE_REAL_OCR_VAULT"
REAL_KEYS_ENV = "PAPERFORGE_REAL_OCR_KEYS"

PROBLEM_KEYS = ["TSCKAVIS", "CAQNW9Q2", "A8E7SRVS", "K7R8PEKW", "DWQQK2YB", "M36WA39N"]
CONTROL_KEYS = ["SAN9AYVR", "2GN9LMCW", "7C8829BD"]
ALL_KEYS = PROBLEM_KEYS + CONTROL_KEYS

BODY_ROLES = {"body_paragraph", "abstract_body"}
HEADING_ROLES = {"section_heading", "subsection_heading", "sub_subsection_heading", "reference_heading", "backmatter_heading"}
NON_READER_ROLES = {"noise", "frontmatter_noise"}

DEBUG_TOKENS = ["unmatched_legend_", "unresolved_cluster_", "orphan_", "asset_block_id", "legend_block_id"]
HEADING_FORBIDDEN = ["published online", "review article", "steve stegen", "geert carmeliet"]
BODY_FORBIDDEN = [
    "published online",
    "conflict of interest",
    "publisher's note",
    "ethics statement",
]


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


def _get_keys() -> list[str]:
    keys = _real_ocr_keys()
    if keys:
        return keys
    vault = _real_ocr_vault()
    if vault is None:
        pytest.skip(f"Set {REAL_VAULT_ENV} and {REAL_KEYS_ENV} for real OCR integration tests")
    return ALL_KEYS


def _ocr_root(vault: Path) -> Path:
    return vault / "System" / "PaperForge" / "ocr"


def _paper_root(ocr_root: Path, key: str) -> Path:
    return ocr_root / key


def _structured_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "structure" / "blocks.structured.jsonl"


def _fulltext_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "fulltext.md"


def _health_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "health" / "ocr_health.json"


def _reader_figures_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "structure" / "reader_figures.json"


def _figure_inventory_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "structure" / "figure_inventory.json"


def _table_inventory_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "structure" / "table_inventory.json"


def _metadata_path(ocr_root: Path, key: str) -> Path:
    return _paper_root(ocr_root, key) / "metadata" / "resolved_metadata.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _require_artifacts(ocr_root: Path, key: str) -> None:
    required = [
        _structured_path(ocr_root, key),
        _fulltext_path(ocr_root, key),
        _health_path(ocr_root, key),
        _metadata_path(ocr_root, key),
        _figure_inventory_path(ocr_root, key),
        _table_inventory_path(ocr_root, key),
        _reader_figures_path(ocr_root, key),
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        pytest.skip(f"OCR artifacts not present for {key}: {missing}")


def _fulltext_lines(ocr_root: Path, key: str) -> list[str]:
    return _fulltext_path(ocr_root, key).read_text(encoding="utf-8", errors="replace").splitlines()


def _block_texts(blocks: list[dict], roles: set[str]) -> list[str]:
    return [str(block.get("text") or block.get("block_content") or "") for block in blocks if block.get("role") in roles]


def _reader_figures(reader_payload: dict) -> list[dict]:
    return list(reader_payload.get("reader_figures", []))


def _formal_legend_blocks(blocks: list[dict]) -> list[dict]:
    legends = []
    for block in blocks:
        role = block.get("role")
        marker_type = str((block.get("marker_signature") or {}).get("type") or "")
        style_family = str(block.get("style_family") or "")
        if role in {"figure_caption", "table_caption", "legend"}:
            legends.append(block)
            continue
        if marker_type == "figure_number" and style_family in {"legend_like", "table_caption_like"}:
            legends.append(block)
    return legends


@pytest.fixture(scope="session")
def real_vault() -> Path:
    return _get_vault()


@pytest.fixture(scope="session")
def real_ocr_root(real_vault: Path) -> Path:
    return _ocr_root(real_vault)


@pytest.fixture(scope="session")
def real_keys() -> list[str]:
    return _get_keys()


@pytest.fixture(scope="session")
def rebuilt_reader_audit_papers(real_vault: Path, real_keys: list[str]) -> dict:
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    result = run_derived_rebuild_for_keys(real_vault, real_keys)
    assert result.get("rebuild_count", 0) >= 1, result
    return result


@pytest.mark.parametrize("key", ALL_KEYS)
def test_reader_audit_artifacts_exist(rebuilt_reader_audit_papers: dict, real_ocr_root: Path, key: str) -> None:
    _require_artifacts(real_ocr_root, key)


@pytest.mark.parametrize("key", ALL_KEYS)
def test_reader_audit_health_has_reader_coverage(rebuilt_reader_audit_papers: dict, real_ocr_root: Path, key: str) -> None:
    health = _read_json(_health_path(real_ocr_root, key))
    for field in (
        "figure_reader_coverage_total",
        "figure_reader_coverage_accounted",
        "figure_reader_coverage_gap_count",
        "figure_reader_coverage_ratio",
    ):
        assert field in health, f"{key}: missing health field {field}"


@pytest.mark.parametrize("key", ALL_KEYS)
def test_reader_audit_no_debug_tokens_in_fulltext(rebuilt_reader_audit_papers: dict, real_ocr_root: Path, key: str) -> None:
    fulltext = _fulltext_path(real_ocr_root, key).read_text(encoding="utf-8", errors="replace")
    for token in DEBUG_TOKENS:
        assert token not in fulltext, f"{key}: debug token leaked into fulltext: {token}"


@pytest.mark.parametrize("key", ALL_KEYS)
def test_reader_audit_consumed_caption_integrity(rebuilt_reader_audit_papers: dict, real_ocr_root: Path, key: str) -> None:
    blocks = _read_jsonl(_structured_path(real_ocr_root, key))
    reader_payload = _read_json(_reader_figures_path(real_ocr_root, key))
    block_ids = {block.get("block_id") for block in blocks}
    owners: dict[int | str, int] = defaultdict(int)
    for figure in _reader_figures(reader_payload):
        for bid in figure.get("consumed_caption_block_ids", []):
            assert bid in block_ids, f"{key}: consumed caption block id missing from structured blocks: {bid}"
            owners[bid] += 1
    assert all(count == 1 for count in owners.values()), f"{key}: consumed caption block owned more than once: {owners}"


@pytest.mark.parametrize("key", ALL_KEYS)
def test_reader_audit_formal_legends_have_reader_outcomes(rebuilt_reader_audit_papers: dict, real_ocr_root: Path, key: str) -> None:
    blocks = _read_jsonl(_structured_path(real_ocr_root, key))
    reader_payload = _read_json(_reader_figures_path(real_ocr_root, key))
    reader_caption_ids = set()
    for figure in _reader_figures(reader_payload):
        caption_id = figure.get("caption_block_id")
        if caption_id is not None:
            reader_caption_ids.add(caption_id)

    legends = _formal_legend_blocks(blocks)
    missing = [block.get("block_id") for block in legends if block.get("block_id") not in reader_caption_ids]
    assert not missing, f"{key}: formal legend blocks missing reader outcomes: {missing[:10]}"


@pytest.mark.parametrize("key", ALL_KEYS)
def test_reader_audit_heading_hygiene(rebuilt_reader_audit_papers: dict, real_ocr_root: Path, key: str) -> None:
    blocks = _read_jsonl(_structured_path(real_ocr_root, key))
    heading_text = "\n".join(_block_texts(blocks, HEADING_ROLES)).lower()
    for token in HEADING_FORBIDDEN:
        assert token not in heading_text, f"{key}: forbidden heading token leaked into heading roles: {token}"


@pytest.mark.parametrize("key", ALL_KEYS)
def test_reader_audit_body_hygiene(rebuilt_reader_audit_papers: dict, real_ocr_root: Path, key: str) -> None:
    blocks = _read_jsonl(_structured_path(real_ocr_root, key))
    body_text = "\n".join(_block_texts(blocks, BODY_ROLES)).lower()
    for token in BODY_FORBIDDEN:
        assert token not in body_text, f"{key}: forbidden body token leaked into body flow: {token}"


@pytest.mark.parametrize("key", ALL_KEYS)
def test_reader_audit_reader_statuses_are_whitelisted(rebuilt_reader_audit_papers: dict, real_ocr_root: Path, key: str) -> None:
    reader_payload = _read_json(_reader_figures_path(real_ocr_root, key))
    allowed = {"EXACT_MATCH", "SEQUENCE_MATCH", "GROUPED_APPROXIMATE", "LEGEND_ONLY", "ASSET_GROUP_ONLY", "HOLD"}
    statuses = {figure.get("reader_status") for figure in _reader_figures(reader_payload)}
    assert statuses <= allowed, f"{key}: unknown reader statuses present: {statuses - allowed}"


@pytest.mark.parametrize("key", ALL_KEYS)
def test_reader_audit_no_duplicate_caption_body_and_card(rebuilt_reader_audit_papers: dict, real_ocr_root: Path, key: str) -> None:
    lines = _fulltext_lines(real_ocr_root, key)
    blocks = _read_jsonl(_structured_path(real_ocr_root, key))
    reader_payload = _read_json(_reader_figures_path(real_ocr_root, key))

    body_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith("> ")]
    body_text = "\n".join(body_lines)

    caption_lookup = {block.get("block_id"): str(block.get("text") or "") for block in blocks}
    duplicated = []
    for figure in _reader_figures(reader_payload):
        caption_id = figure.get("caption_block_id")
        if caption_id is None:
            continue
        caption = caption_lookup.get(caption_id, "").strip()
        if not caption:
            continue
        if caption in body_text and any(caption in line for line in lines if line.strip().startswith("> Caption: ")):
            duplicated.append(caption_id)
    assert not duplicated, f"{key}: caption leaked in both body flow and reader card: {duplicated[:10]}"


@pytest.mark.parametrize("key", ALL_KEYS)
def test_reader_audit_reader_coverage_is_not_trivially_zero(rebuilt_reader_audit_papers: dict, real_ocr_root: Path, key: str) -> None:
    health = _read_json(_health_path(real_ocr_root, key))
    blocks = _read_jsonl(_structured_path(real_ocr_root, key))
    legends = _formal_legend_blocks(blocks)
    if legends:
        assert health.get("figure_reader_coverage_total", 0) > 0, f"{key}: reader coverage total is zero despite formal legends"


def test_reader_audit_normalized_matched_figures_keep_figure_semantics(
    rebuilt_reader_audit_papers: dict,
    real_ocr_root: Path,
) -> None:
    key = "TSCKAVIS"
    payload = _read_json(_reader_figures_path(real_ocr_root, key))
    matched = payload["normalized_inputs"]["matched_figures"]
    assert matched, "Expected matched figures in TSCKAVIS"
    bad = [
        item for item in matched
        if item.get("marker_type") not in {"figure_number", None}
        or item.get("style_family") not in {"legend_like", None}
    ]
    assert not bad, [{k: b[k] for k in list(b)[:5]} for b in bad[:3]]


@pytest.mark.parametrize("key", ["K7R8PEKW", "DWQQK2YB", "M36WA39N", "SAN9AYVR", "2GN9LMCW", "7C8829BD"])
def test_reader_audit_known_debug_leak_cases(
    rebuilt_reader_audit_papers: dict,
    real_ocr_root: Path,
    key: str,
) -> None:
    fulltext = _fulltext_path(real_ocr_root, key).read_text(encoding="utf-8", errors="replace")
    assert "unresolved_cluster_" not in fulltext
    assert "unmatched_legend_" not in fulltext
