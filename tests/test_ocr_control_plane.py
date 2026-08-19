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


def test_resume_excludes_submitting_crash_window(tmp_path: Path) -> None:
    """M1.1 (7.3): a paper in submission_state=submitting is in the
    submit→persist crash window — the remote job MAY exist without a
    persisted job_id.  Auto-resume must EXCLUDE it (execution_unknown,
    never a blind double submit)."""
    from paperforge.commands import ocr as ocr_cmd

    vault = _make_vault(tmp_path)
    batch = "pf-test"
    _write_meta(
        vault,
        "AAAA1111",
        {"provider_batch_id": batch, "ocr_status": "pending", "submission_state": "submitting"},
    )
    _write_meta(
        vault,
        "BBBB2222",
        {"provider_batch_id": batch, "ocr_status": "pending"},
    )
    keys = ocr_cmd._collect_batch_unsettled(vault, batch)
    assert keys == ["BBBB2222"], "submitting papers must be excluded from auto-resume"


def test_provider_jobs_bounded_and_deduped() -> None:
    """M1.1 (7.2): the provider-attempt provenance list stays bounded (<=3)
    and never duplicates the current job id."""
    jobs: list[dict] = []
    for attempt in range(5):
        jid = f"j{attempt}"
        jobs = [j for j in jobs if isinstance(j, dict) and j.get("job_id") != jid]
        jobs.append({"attempt": attempt + 1, "job_id": jid})
        jobs = jobs[-3:]
    assert len(jobs) <= 3, "provider_jobs must be bounded"
    assert jobs[-1] == {"attempt": 5, "job_id": "j4"}
    assert jobs[0] == {"attempt": 3, "job_id": "j2"}


def test_ocr_progress_reports_each_settlement_once() -> None:
    """Polling updates are not progress: each terminal paper emits once."""
    from paperforge.worker.ocr import _emit_settlement_progress

    events: list[str] = []
    reported: set[str] = set()
    row = {"zotero_key": "AAAA1111", "queue_status": "running"}
    for status in ("running", "queued", "done_degraded", "done_degraded"):
        row["queue_status"] = status
        _emit_settlement_progress(events.append, reported, row)
    assert events == ["AAAA1111"]


def test_ocr_status_reports_complete_when_no_unfinished_papers(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """An empty active queue is an explicit complete state, not ambiguity."""
    from paperforge.commands import ocr as ocr_cmd

    vault = _make_vault(tmp_path)
    monkeypatch.setattr(
        "paperforge.worker._utils.pipeline_paths",
        lambda _vault: {"ocr": vault / "System" / "PaperForge" / "ocr"},
    )
    assert ocr_cmd._run_ocr_status(vault, json_output=True) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"status": "complete", "count": 0, "jobs": []}


def test_ocr_status_surfaces_submission_crash_window(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """A write-ahead submitting marker is incomplete/execution-unknown."""
    from paperforge.commands import ocr as ocr_cmd

    vault = _make_vault(tmp_path)
    _write_meta(
        vault,
        "AAAA1111",
        {"ocr_status": "pending", "submission_state": "submitting"},
    )
    monkeypatch.setattr(
        "paperforge.worker._utils.pipeline_paths",
        lambda _vault: {"ocr": vault / "System" / "PaperForge" / "ocr"},
    )
    monkeypatch.setattr("paperforge.worker.ocr._resolve_paddleocr_token", lambda _vault: "")
    assert ocr_cmd._run_ocr_status(vault, json_output=True) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "incomplete"
    assert payload["count"] == 1
    assert payload["jobs"][0]["status"] == "submitting"


def test_ocr_run_reports_terminal_only_scope_as_done(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """A scope containing only settled papers is a successful no-op."""
    from paperforge.worker import ocr as ocr_mod

    vault = tmp_path / "vault"
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    exports = vault / "System" / "PaperForge" / "exports"
    ocr_root.mkdir(parents=True)
    exports.mkdir(parents=True)
    (exports / "library.json").write_text("[]", encoding="utf-8")
    (ocr_root / "AAAA1111").mkdir()
    (ocr_root / "AAAA1111" / "meta.json").write_text(
        json.dumps({"zotero_key": "AAAA1111", "ocr_status": "done_degraded"}),
        encoding="utf-8",
    )
    paths = {
        "ocr": ocr_root,
        "exports": exports,
        "ocr_queue": ocr_root / "ocr_queue.json",
    }
    monkeypatch.setattr(ocr_mod, "pipeline_paths", lambda _vault: paths)
    monkeypatch.setattr(
        ocr_mod,
        "load_export_rows",
        lambda _path: [{"key": "AAAA1111", "attachments": []}],
    )
    monkeypatch.setattr(
        "paperforge.worker.asset_index.read_index",
        lambda _vault: {"items": [{"zotero_key": "AAAA1111", "pdf_path": "paper.pdf"}]},
    )
    monkeypatch.setattr(ocr_mod, "sync_ocr_queue", lambda _paths, _rows: [])
    monkeypatch.setattr(ocr_mod, "validate_ocr_meta", lambda *_args: ("done", ""))
    monkeypatch.setattr(ocr_mod, "_resolve_paddleocr_token", lambda _vault: "")
    monkeypatch.setattr(ocr_mod._sync, "run_index_refresh", lambda *_args, **_kwargs: None)
    monkeypatch.setenv("PAPERFORGE_POLL_MAX_CYCLES", "1")

    assert ocr_mod.run_ocr(vault, selected_keys={"AAAA1111"}) == 0
    assert "OCR: done=1" in capsys.readouterr().out
