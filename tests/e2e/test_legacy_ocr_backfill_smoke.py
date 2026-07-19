"""E2E smoke tests for legacy OCR backfill against real vault data.

These tests require a real PaperForge vault with legacy OCR directories
(pre-structured-pipeline, no version state in meta.json).

Run:
    pytest tests/e2e/test_legacy_ocr_backfill_smoke.py -v --tb=long

Set PAPERFORGE_VAULT env var to override the default vault path.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

_SMOKE_VAULT = os.environ.get("PAPERFORGE_VAULT", "")
_VAULT_AVAILABLE = bool(_SMOKE_VAULT) and Path(_SMOKE_VAULT).exists()


def _find_legacy_papers(vault: Path) -> list[dict]:
    """Scan vault OCR dir for legacy papers (no version state, ocr_status=done)."""
    from paperforge.worker.ocr_versions import classify_legacy_ocr_state
    from paperforge.core.io import read_json

    cfg_path = vault / "paperforge.json"
    if not cfg_path.exists():
        return []
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    system_dir = cfg.get("vault_config", {}).get("system_dir", "99_System")
    ocr_root = vault / system_dir / "PaperForge" / "ocr"
    if not ocr_root.exists():
        return []

    legacy = []
    for paper_dir in ocr_root.iterdir():
        if not paper_dir.is_dir():
            continue
        meta_path = paper_dir / "meta.json"
        if not meta_path.exists():
            continue
        meta = read_json(meta_path)
        state = classify_legacy_ocr_state(meta, ocr_dir=paper_dir)
        if state["is_legacy"]:
            legacy.append({
                "key": paper_dir.name,
                "can_backfill": state["can_backfill"],
                "has_result_json": state["has_result_json"],
            })
    return legacy


@pytest.mark.skipif(not _VAULT_AVAILABLE, reason="PAPERFORGE_VAULT not set or not found")
def test_smoke_legacy_backfill_identifies_candidates():
    """Verify that the vault has legacy OCR papers and they are correctly classified."""
    vault = Path(_SMOKE_VAULT)
    legacy = _find_legacy_papers(vault)

    assert len(legacy) > 0, (
        f"No legacy OCR papers found in {vault}. "
        "This is expected if all papers have already been backfilled or if "
        "the vault uses the structured pipeline exclusively."
    )

    # At least some should be backfillable (have result.json)
    backfillable = [p for p in legacy if p["can_backfill"]]
    if not backfillable:
        pytest.skip("No backfillable legacy papers found (no result.json available)")


@pytest.mark.skipif(not _VAULT_AVAILABLE, reason="PAPERFORGE_VAULT not set or not found")
def test_smoke_backfill_single_legacy_paper(tmp_path):
    """Backfill a single legacy paper into a temp vault clone and verify artifacts."""
    import shutil

    from paperforge.worker.ocr_rebuild import backfill_from_result, select_legacy_papers_for_backfill

    vault = Path(_SMOKE_VAULT)
    legacy = [p for p in _find_legacy_papers(vault) if p["can_backfill"]]
    if not legacy:
        pytest.skip("No backfillable legacy papers for smoke test")

    target = legacy[0]
    paper_dir = vault / _get_system_dir(vault) / "PaperForge" / "ocr" / target["key"]

    # Copy this paper's OCR dir to temp vault
    temp_vault = tmp_path / "vault"
    shutil.copytree(vault / "paperforge.json", temp_vault / "paperforge.json")
    temp_ocr_dest = temp_vault / _get_system_dir(vault) / "PaperForge" / "ocr" / target["key"]
    shutil.copytree(paper_dir, temp_ocr_dest)

    # Run backfill
    result = backfill_from_result(temp_vault, target["key"])

    assert result["backfill_status"] == "done", (
        f"Backfill failed: {result.get('error', 'unknown error')}"
    )

    # Verify derived artifacts
    assert (temp_ocr_dest / "index" / "role-index.json").exists()
    assert (temp_ocr_dest / "health" / "ocr_health.json").exists()
    assert (temp_ocr_dest / "render" / "fulltext.md").exists()

    # Verify backfill metadata
    meta = json.loads((temp_ocr_dest / "meta.json").read_text(encoding="utf-8"))
    assert meta.get("is_backfilled") is True
    assert "backfilled_at" in meta


def _get_system_dir(vault: Path) -> str:
    cfg = json.loads((vault / "paperforge.json").read_text(encoding="utf-8"))
    return cfg.get("vault_config", {}).get("system_dir", "99_System")
