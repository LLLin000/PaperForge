"""Production-path contract audit for real OCR papers.

Classification: secondary audit coverage.
Primary regression gate is tests/test_ocr_real_paper_regressions.py
(spec-contract + fixture-backed production-path replay).

These tests validate broader real-paper drift but require
PAPERFORGE_REAL_OCR_VAULT env; they are not the deterministic
first-line gate.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

REAL_VAULT_ENV = "PAPERFORGE_REAL_OCR_VAULT"
REAL_KEYS_ENV = "PAPERFORGE_REAL_OCR_KEYS"

ALL_KEYS = ["TSCKAVIS", "CAQNW9Q2", "A8E7SRVS", "K7R8PEKW", "DWQQK2YB", "M36WA39N", "SAN9AYVR", "2GN9LMCW", "7C8829BD"]

LEGEND_PREFIX = re.compile(r"^(FIGURE\s+\d+\s*[|\u2502]|Fig\.\s*\d+)", re.IGNORECASE)


def _vault() -> Path:
    v = os.environ.get(REAL_VAULT_ENV)
    if not v:
        pytest.skip(f"Set {REAL_VAULT_ENV}")
    return Path(v)


def _ocr_root() -> Path:
    return _vault() / "System" / "PaperForge" / "ocr"


def _keys() -> list[str]:
    raw = os.environ.get(REAL_KEYS_ENV, "")
    if raw:
        return [k.strip() for k in raw.split(",") if k.strip()]
    return ALL_KEYS


def _structured_path(key: str) -> Path:
    return _ocr_root() / key / "structure" / "blocks.structured.jsonl"


def _fulltext_path(key: str) -> Path:
    return _ocr_root() / key / "fulltext.md"


def _reader_figures_path(key: str) -> Path:
    return _ocr_root() / key / "structure" / "reader_figures.json"


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


_BODY_ROLES = {"body_paragraph", "abstract_body"}
_HEADING_ROLES = {
    "section_heading",
    "subsection_heading",
    "sub_subsection_heading",
    "reference_heading",
    "backmatter_heading",
}
_FORBIDDEN_BODY_PHRASES = [
    "published online",
    "conflict of interest",
    "publisher's note",
    "ethics statement",
    "reviewed by:",
    "edited by:",
    "specialty section:",
    "citation:",
]
_FORBIDDEN_HEADING_PHRASES = [
    "published online",
    "review article",
    "steve stegen",
    "geert carmeliet",
]


def _block_text(block: dict) -> str:
    return str(block.get("text") or block.get("block_content") or "")


def _is_figure_caption_in_body(block: dict) -> bool:
    if block.get("role") != "body_paragraph":
        return False
    text = _block_text(block).strip()
    if not text:
        return False
    if LEGEND_PREFIX.match(text) or text.startswith("> **"):
        return True
    return False


@pytest.fixture(scope="module")
def rebuilt() -> dict:
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    result = run_derived_rebuild_for_keys(_vault(), _keys())
    assert result.get("rebuild_count", 0) >= 1
    return result


def test_rebuild_succeeds(rebuilt: dict) -> None:
    assert rebuilt["rebuild_count"] >= 1


# ---- Per-paper contract tests ----

_PAPER_CONTRACTS = {
    "TSCKAVIS": {
        "min_body": 48,
        "min_headings": 4,
        "expected_figures": 5,
        "body_no_figure_captions": True,
        "no_frontmatter_before_intro": True,
        "reader_figures_min": 2,
    },
    "CAQNW9Q2": {
        "min_body": 27,
        "min_headings": 5,
        "expected_figures": 3,
        "body_no_figure_captions": True,
        "no_frontmatter_before_intro": True,
        "reader_figures_min": 2,
    },
    "A8E7SRVS": {
        "min_body": 42,
        "min_headings": 4,
        "expected_figures": 6,
        "body_no_figure_captions": True,
        "no_frontmatter_before_intro": True,
        "reader_figures_min": 4,
    },
    "K7R8PEKW": {
        "min_body": 60,
        "min_headings": 4,
        "expected_figures": 4,
        "body_no_figure_captions": True,
        "no_frontmatter_before_intro": True,
        "reader_figures_min": 3,
    },
    "DWQQK2YB": {
        "min_body": 25,
        "min_headings": 4,
        "expected_figures": 4,
        "body_no_figure_captions": True,
        "no_frontmatter_before_intro": True,
        "reader_figures_min": 3,
    },
    "M36WA39N": {
        "min_body": 45,
        "min_headings": 4,
        "expected_figures": 7,
        "body_no_figure_captions": True,
        "no_frontmatter_before_intro": True,
        "reader_figures_min": 5,
    },
    "SAN9AYVR": {
        "min_body": 200,
        "min_headings": 10,
        "expected_figures": 31,
        "body_no_figure_captions": True,
        "no_frontmatter_before_intro": True,
        "reader_figures_min": 10,
    },
    "2GN9LMCW": {
        "min_body": 25,
        "min_headings": 3,
        "expected_figures": 4,
        "body_no_figure_captions": True,
        "no_frontmatter_before_intro": True,
        "reader_figures_min": 2,
    },
    "7C8829BD": {
        "min_body": 65,
        "min_headings": 4,
        "expected_figures": 7,
        "body_no_figure_captions": True,
        "no_frontmatter_before_intro": True,
        "reader_figures_min": 1,
    },
}


@pytest.mark.parametrize("key", sorted(_PAPER_CONTRACTS))
def test_body_paragraph_count(rebuilt: dict, key: str) -> None:
    blocks = _read_jsonl(_structured_path(key))
    body_count = sum(1 for b in blocks if b.get("role") in _BODY_ROLES)
    assert body_count >= _PAPER_CONTRACTS[key]["min_body"], (
        f"{key}: only {body_count} body paragraphs, expected >= {_PAPER_CONTRACTS[key]['min_body']}"
    )


@pytest.mark.parametrize("key", sorted(_PAPER_CONTRACTS))
def test_figure_captions_not_in_body(rebuilt: dict, key: str) -> None:
    blocks = _read_jsonl(_structured_path(key))
    body_fig_captions = [b for b in blocks if _is_figure_caption_in_body(b)]
    max_allowed = 1  # minor strict-layer misclassifications are acceptable
    assert len(body_fig_captions) <= max_allowed, (
        f"{key}: {len(body_fig_captions)} figure captions leaked into body_paragraph "
        f"(max allowed {max_allowed}): "
        f"block_ids={[b['block_id'] for b in body_fig_captions[:5]]}"
    )


@pytest.mark.parametrize("key", sorted(_PAPER_CONTRACTS))
def test_fulltext_no_figure_caption_pollution(rebuilt: dict, key: str) -> None:
    fulltext = _fulltext_path(key).read_text(encoding="utf-8", errors="replace")
    lines = fulltext.split("\n")
    body_lines = []
    for line in lines:
        stripped = line.strip()
        if (
            stripped.startswith("![[")
            or stripped.startswith(">")
            or stripped.startswith("#")
            or stripped.startswith("<!--")
        ):
            continue
        body_lines.append(stripped)
    polluted = [line for line in body_lines if LEGEND_PREFIX.match(line)]
    max_allowed = 1  # minor inline figure mentions are acceptable
    assert len(polluted) <= max_allowed, (
        f"{key}: {len(polluted)} figure captions appear as body text in fulltext "
        f"(max allowed {max_allowed}): "
        f"{polluted[:3]}"
    )


@pytest.mark.parametrize("key", sorted(_PAPER_CONTRACTS))
def test_reader_figures_present(rebuilt: dict, key: str) -> None:
    rf_path = _reader_figures_path(key)
    if not rf_path.exists():
        pytest.skip(f"reader_figures.json not found for {key}")
    payload = _read_json(rf_path)
    count = len(payload.get("reader_figures", []))
    expected_min = _PAPER_CONTRACTS[key]["reader_figures_min"]
    assert count >= expected_min, f"{key}: only {count} reader figures, expected >= {expected_min}"


@pytest.mark.parametrize("key", sorted(_PAPER_CONTRACTS))
def test_heading_hygiene(rebuilt: dict, key: str) -> None:
    blocks = _read_jsonl(_structured_path(key))
    heading_text = "\n".join(_block_text(b) for b in blocks if b.get("role") in _HEADING_ROLES).lower()
    for phrase in _FORBIDDEN_HEADING_PHRASES:
        assert phrase not in heading_text, f"{key}: forbidden phrase '{phrase}' in heading roles"


@pytest.mark.parametrize("key", sorted(_PAPER_CONTRACTS))
def test_no_debug_tokens(rebuilt: dict, key: str) -> None:
    fulltext = _fulltext_path(key).read_text(encoding="utf-8", errors="replace")
    for token in ("unmatched_legend_", "unresolved_cluster_", "orphan_", "asset_block_id", "legend_block_id"):
        assert token not in fulltext, f"{key}: debug token '{token}' in fulltext"


@pytest.mark.parametrize("key", sorted(_PAPER_CONTRACTS))
def test_body_no_frontmatter_furniture(rebuilt: dict, key: str) -> None:
    blocks = _read_jsonl(_structured_path(key))
    body_text = "\n".join(_block_text(b) for b in blocks if b.get("role") in _BODY_ROLES).lower()
    for phrase in _FORBIDDEN_BODY_PHRASES:
        assert phrase not in body_text, f"{key}: frontmatter phrase '{phrase}' leaked into body"


@pytest.mark.parametrize("key", sorted(_PAPER_CONTRACTS))
def test_reader_figure_cards_in_fulltext(rebuilt: dict, key: str) -> None:
    fulltext = _fulltext_path(key).read_text(encoding="utf-8", errors="replace")
    rf_path = _reader_figures_path(key)
    if not rf_path.exists():
        pytest.skip(f"reader_figures.json not found for {key}")
    payload = _read_json(rf_path)
    figure_count = len(payload.get("reader_figures", []))
    if figure_count == 0:
        return
    card_count = fulltext.count("> **Figure")
    embed_count = fulltext.count("![[render/figures/figure_")
    assert card_count >= figure_count * 0.5, (
        f"{key}: only {card_count} reader figure cards for {figure_count} reader figures. "
        f"Expected at least {figure_count * 0.5:.0f} cards in fulltext."
    )
    assert embed_count > 0, f"{key}: no figure embeds in fulltext despite {figure_count} reader figures"
