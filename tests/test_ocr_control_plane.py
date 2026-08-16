"""Control Plane Closure H2: crash/restart invariants for the OCR
execution controller (batch identity + single mutating controller)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    ocr_root.mkdir(parents=True)
    return vault


def _write_meta(vault: Path, key: str, meta: dict) -> None:
    p = vault / "System" / "PaperForge" / "ocr" / key / "meta.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(meta), encoding="utf-8")


def test_controller_lock_stale_recovery(tmp_path: Path) -> None:
    """A crashed controller leaves controller.lock; a fresh run must be
    able to take over after the 30s stale window (H2 crash/restart)."""
    from paperforge.worker import ocr as ocr_mod

    vault = _make_vault(tmp_path)
    lock = vault / "System" / "PaperForge" / "ocr" / "controller.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("stale", encoding="utf-8")
    old = time.time() - 60  # older than the 30s stale window
    import os

    os.utime(lock, (old, old))

    acquired = ocr_mod._acquire_controller_lock(lock)
    assert acquired is True, "stale controller lock must be recoverable"
    assert lock.exists(), "the recovering holder keeps the lock file"


def test_controller_lock_rejects_live_holder(tmp_path: Path) -> None:
    """A LIVE controller lock (fresh) must refuse a second controller."""
    from paperforge.worker import ocr as ocr_mod

    vault = _make_vault(tmp_path)
    lock = vault / "System" / "PaperForge" / "ocr" / "controller.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("live", encoding="utf-8")

    acquired = ocr_mod._acquire_controller_lock(lock)
    assert acquired is False, "a live controller lock must refuse a second controller"


def test_resume_collects_only_unsettled_batch_papers(tmp_path: Path) -> None:
    """resume --batch must collect ONLY unsettled papers of that batch —
    settled papers are never re-OCR'd (the provider-result recovery
    frontier, G1)."""
    from paperforge.commands import ocr as ocr_cmd

    vault = _make_vault(tmp_path)
    batch = "pf-test-123"
    _write_meta(
        vault,
        "AAAA1111",
        {"provider_batch_id": batch, "ocr_status": "running", "ocr_job_id": "j1"},
    )
    _write_meta(
        vault,
        "BBBB2222",
        {"provider_batch_id": batch, "ocr_status": "done"},  # settled — skip
    )
    _write_meta(
        vault,
        "CCCC3333",
        {"provider_batch_id": "pf-other", "ocr_status": "pending"},  # other batch
    )
    keys = ocr_cmd._collect_batch_unsettled(vault, batch)
    assert keys == ["AAAA1111"], f"expected only the unsettled batch paper, got {keys}"
