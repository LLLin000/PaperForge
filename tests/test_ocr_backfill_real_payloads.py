"""Legacy OCR backfill against REAL PaddleOCR payloads.

`tests/sandbox/ocr-real/` holds verbatim `json/result.json` files from a
production vault (see its PROVENANCE.md). The hand-written stub in
`tests/sandbox/ocr-complete/` has a different, invented shape, and building the
regression on it produced a false defect report (#219): a backfilled paper
appeared to lose its page markers and get downgraded. Against all 950 real
papers that never happens.

What the contract actually is:

- a paper is *legacy* when ``ocr_status == "done"`` and meta carries no
  ``raw_version``/``derived_version`` (``worker/ocr_versions.py``);
- ``backfill_from_result`` reads the stored ``result.json``, runs the same
  postprocess pipeline as a fresh OCR, and must leave the paper in a state its
  own validator accepts — not merely "no exception".

The page-marker rule is the sharp edge: ``worker/ocr.py:validate_ocr_meta``
requires the canonical ``fulltext.md`` to carry exactly ``page_count``
``<!-- page N -->`` markers, and the canonical fulltext IS the render output
(``write_render_outputs`` writes both ``render/fulltext.md`` and the root file).
A payload shape the pipeline cannot actually read yields zero markers and the
paper is reported ``done_incomplete`` on the next sync — which is what the
invented stub did.
"""
from __future__ import annotations

import json
from typing import Any, cast
from pathlib import Path

import pytest

from paperforge.config import bootstrap_config, set_config
from paperforge.worker.ocr import validate_ocr_meta
from paperforge.worker.ocr_rebuild import backfill_from_result

FIXTURE_ROOT = Path(__file__).resolve().parent / "sandbox" / "ocr-real"


def _real_fixtures() -> list[str]:
    return sorted(p.name for p in FIXTURE_ROOT.iterdir() if (p / "json" / "result.json").exists())


def _legacy_vault(tmp_path: Path, key: str) -> Path:
    """A vault holding one legacy paper: real payload, no derived artifacts."""
    import shutil

    vault = tmp_path / f"vault-{key}"
    (vault).mkdir(parents=True)
    _ = bootstrap_config(vault)
    for name, value in {
        "system_dir": "System",
        "resources_dir": "Resources",
        "literature_dir": "Literature",
        "control_dir": "LiteratureControl",
        "base_dir": "Bases",
        "skill_dir": ".opencode/skills",
    }.items():
        _ = set_config(vault, name, value)

    paper = vault / "System" / "PaperForge" / "ocr" / key
    (paper / "json").mkdir(parents=True)
    shutil.copy2(FIXTURE_ROOT / key / "json" / "result.json", paper / "json" / "result.json")
    shutil.copy2(FIXTURE_ROOT / key / "meta.json", paper / "meta.json")
    return vault


def test_real_fixtures_are_shaped_like_production() -> None:
    """Guard the fixture itself: the payload must be a per-page response list.

    The stub this replaced was a dict, and that shape mismatch is precisely how
    the suite came to verify something production never emits.
    """
    keys = _real_fixtures()
    assert keys, "no real OCR fixtures found"
    for key in keys:
        payload = cast(
            "list[Any]",
            json.loads((FIXTURE_ROOT / key / "json" / "result.json").read_text(encoding="utf-8")),
        )
        assert isinstance(payload, list), f"{key}: production payloads are a list of pages"
        assert payload, f"{key}: empty payload"
        first = cast("dict[str, Any]", payload[0])
        assert isinstance(first, dict)
        # The fields the postprocess pipeline actually reads.
        assert "layoutParsingResults" in first, f"{key}: not a PaddleOCR page response"


@pytest.mark.parametrize("key", _real_fixtures())
def test_backfill_keeps_a_legacy_paper_valid(tmp_path: Path, key: str) -> None:
    vault = _legacy_vault(tmp_path, key)
    paper = vault / "System" / "PaperForge" / "ocr" / key
    meta_before = cast(
        "dict[str, Any]", json.loads((paper / "meta.json").read_text(encoding="utf-8"))
    )
    page_count = int(meta_before.get("page_count") or 0)
    assert page_count > 0, f"{key}: fixture must declare a page count"

    result = cast("dict[str, Any]", backfill_from_result(vault, key))
    assert result.get("backfill_status") == "done", result

    fulltext = (paper / "fulltext.md").read_text(encoding="utf-8")
    assert fulltext.strip(), f"{key}: backfill produced no fulltext"
    markers = fulltext.count("<!-- page ")
    assert markers == page_count, (
        f"{key}: the canonical fulltext must carry exactly page_count markers "
        f"(markers={markers}, page_count={page_count}); the render output is the "
        "canonical fulltext, and its own validator rejects anything else"
    )

    meta_after = cast(
        "dict[str, Any]", json.loads((paper / "meta.json").read_text(encoding="utf-8"))
    )
    status, reason = validate_ocr_meta({"ocr": vault / "System" / "PaperForge" / "ocr"}, meta_after)
    assert status == "done", f"{key}: backfill left the paper unacceptable: {status} ({reason})"
    assert meta_after.get("ocr_status") == "done", (
        f"{key}: the persisted status must match the validator verdict"
    )


@pytest.mark.parametrize("key", _real_fixtures())
def test_backfill_produces_the_derived_artifacts(tmp_path: Path, key: str) -> None:
    """A backfill that only writes fulltext would leave the rest of the tree stale."""
    vault = _legacy_vault(tmp_path, key)
    paper = vault / "System" / "PaperForge" / "ocr" / key
    _ = backfill_from_result(vault, key)
    for relative in ("raw", "canonical", "structure", "index", "render"):
        assert (paper / relative).is_dir(), f"{key}: backfill did not produce {relative}/"
