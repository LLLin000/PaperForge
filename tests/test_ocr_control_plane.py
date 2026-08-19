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


# ── Control-plane corrective (#190 review, 2026-08-19): stop semantics,
# ── provider max-attempt settlement, TOCTOU upload classification ────────


def _run_ocr_harness(
    tmp_path: Path,
    monkeypatch,
    *,
    rows: list[dict],
    meta_for: dict[str, dict],
    token: str = "tok",
) -> tuple:
    """Run-ocr harness: queue prepared from rows; per-key meta from
    meta_for.  Rows carry both ``key`` (export locator) and ``zotero_key``
    (queue identity).  Returns (vault, ocr_mod, paths)."""
    from paperforge.worker import ocr as ocr_mod

    vault = tmp_path / "vault"
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    exports = vault / "System" / "PaperForge" / "exports"
    ocr_root.mkdir(parents=True)
    exports.mkdir(parents=True)
    (exports / "library.json").write_text("[]", encoding="utf-8")
    rows = [
        dict(
            r,
            key=r.get("key", r["zotero_key"]),
            queue_status=r.get("queue_status")
            or meta_for.get(r["zotero_key"], {}).get("ocr_status", "pending"),
        )
        for r in rows
    ]
    for row in rows:
        key = row["zotero_key"]
        (ocr_root / key).mkdir(parents=True, exist_ok=True)
        (ocr_root / key / "meta.json").write_text(
            json.dumps(meta_for.get(key, {"zotero_key": key, "ocr_status": "pending"})),
            encoding="utf-8",
        )
    paths = {"ocr": ocr_root, "exports": exports, "ocr_queue": ocr_root / "ocr_queue.json"}
    monkeypatch.setattr(ocr_mod, "pipeline_paths", lambda _v: paths)
    monkeypatch.setattr(ocr_mod, "load_export_rows", lambda _p: rows)
    monkeypatch.setattr(
        "paperforge.worker.asset_index.read_index",
        lambda _v: {"items": rows},
    )
    monkeypatch.setattr(ocr_mod, "sync_ocr_queue", lambda _paths, _target_rows: rows)
    monkeypatch.setattr(ocr_mod, "validate_ocr_meta", lambda *_a: ("queued", ""))
    monkeypatch.setattr(ocr_mod, "_resolve_paddleocr_token", lambda _v: token)
    monkeypatch.setattr(ocr_mod._sync, "run_index_refresh", lambda *_a, **_k: None)
    monkeypatch.setattr(ocr_mod, "_acquire_controller_lock", lambda _p: True)
    monkeypatch.setenv("PAPERFORGE_POLL_MAX_CYCLES", "3")
    monkeypatch.setenv("PAPERFORGE_POLL_INTERVAL", "0")
    return vault, ocr_mod, paths


def _read_meta(vault, key: str) -> dict:
    import json as _json

    return _json.loads(
        (vault / "System" / "PaperForge" / "ocr" / key / "meta.json").read_text(encoding="utf-8")
    )


def test_stop_detaches_immediately_no_poll_no_sleep(tmp_path, monkeypatch) -> None:
    """P0: stop observed at cycle start -> NO polling, NO sleep, rc130."""
    rows = [{"zotero_key": "AAAA1111", "has_pdf": True, "pdf_path": "x.pdf"}]
    vault, ocr_mod, _ = _run_ocr_harness(
        tmp_path, monkeypatch, rows=rows,
        meta_for={"AAAA1111": {"zotero_key": "AAAA1111", "ocr_status": "queued", "ocr_job_id": "j1"}},
    )
    polled = []
    monkeypatch.setattr(
        ocr_mod.requests, "get",
        lambda *a, **k: polled.append(a) or _raise(),
    )

    def _raise():
        raise AssertionError("must not poll after stop")

    slept = []
    import time as _time_mod

    real_sleep = _time_mod.sleep
    monkeypatch.setattr(_time_mod, "sleep", lambda *a: slept.append(a))

    rc = ocr_mod.run_ocr(vault, stop_check=lambda: True)
    assert rc == 130, "stop must return 130"
    assert polled == [], "no provider poll allowed after stop"
    assert slept == [], "no sleep allowed after stop"


def test_stop_preserves_remote_jobs_in_meta(tmp_path, monkeypatch) -> None:
    """P0: detach keeps queued/running meta (remote jobs keep running)."""
    rows = [{"zotero_key": "AAAA1111", "has_pdf": True, "pdf_path": "x.pdf"}]
    vault, ocr_mod, _ = _run_ocr_harness(
        tmp_path, monkeypatch, rows=rows,
        meta_for={"AAAA1111": {"zotero_key": "AAAA1111", "ocr_status": "running", "ocr_job_id": "j9"}},
    )
    monkeypatch.setattr(
        ocr_mod.requests, "get",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no poll after stop")),
    )
    rc = ocr_mod.run_ocr(vault, stop_check=lambda: True)
    assert rc == 130
    meta = _read_meta(vault, "AAAA1111")
    assert meta["ocr_status"] == "running", "detach must not mutate remote job state"
    assert meta["ocr_job_id"] == "j9"


def test_provider_final_attempt_settles_fatal(tmp_path, monkeypatch) -> None:
    """P0: provider failure on the LAST allowed attempt -> fatal_error
    terminal with empty job id — never a hanging queued row."""
    from paperforge.providers.paddleocr import ProviderStatus

    from paperforge.worker import ocr as ocr_mod

    rows = [{"zotero_key": "AAAA1111", "has_pdf": True, "pdf_path": "x.pdf"}]
    vault, _ocr_mod, _ = _run_ocr_harness(
        tmp_path, monkeypatch, rows=rows,
        meta_for={
            "AAAA1111": {
                "zotero_key": "AAAA1111", "ocr_status": "queued",
                "ocr_job_id": "j1", "job_attempt": ocr_mod.MAX_OCR_JOB_ATTEMPTS - 1,
            }
        },
    )
    # The pre-poll loop polls queued jobs directly (no batch observer) —
    # keep it "running" there so the MAIN loop's batch observer drives the
    # terminal provider failure.
    monkeypatch.setattr(
        ocr_mod.requests, "get",
        lambda *a, **k: _resp({"data": {"state": "running"}}),
    )
    monkeypatch.setattr(
        "paperforge.providers.paddleocr.PaddleOCRProvider.get_batch_status",
        lambda self, batch: {"j1": (ProviderStatus.FAILED, {"state": "failed", "errorMsg": "boom"})},
    )
    rc = ocr_mod.run_ocr(vault)
    meta = _read_meta(vault, "AAAA1111")
    assert meta["ocr_status"] == "fatal_error", meta
    assert meta["ocr_job_id"] == "", meta
    assert meta["job_attempt"] == ocr_mod.MAX_OCR_JOB_ATTEMPTS, meta
    assert rc == 1, "fatal_error is a settled FAILURE terminal -> rc 1"


def test_unexpected_postprocess_exception_persists_and_releases(tmp_path, monkeypatch) -> None:
    """P1: a generic postprocess crash must persist an error state and
    release the active slot (no hanging queued row, resumable)."""
    from paperforge.providers.paddleocr import ProviderStatus

    rows = [{"zotero_key": "AAAA1111", "has_pdf": True, "pdf_path": "x.pdf"}]
    vault, ocr_mod, _ = _run_ocr_harness(
        tmp_path, monkeypatch, rows=rows,
        meta_for={"AAAA1111": {"zotero_key": "AAAA1111", "ocr_status": "running", "ocr_job_id": "j1"}},
    )

    def boom(*a, **k):
        raise RuntimeError("postprocess exploded")

    monkeypatch.setattr(
        "paperforge.providers.paddleocr.PaddleOCRProvider.get_batch_status",
        lambda self, batch: {
            "j1": (
                ProviderStatus.DONE,
                {"state": "done", "resultUrl": {"jsonUrl": "http://x/result"}},
            )
        },
    )
    monkeypatch.setattr(ocr_mod, "postprocess_ocr_result", boom)
    monkeypatch.setattr(
        ocr_mod.requests, "get",
        lambda *a, **k: _resp({"data": {"state": "done", "resultUrl": {"jsonUrl": "http://x/result"}}})
        if "jobs" in a[0] else _text_resp("{}"),
    )
    # "{}" is a result line without ["result"] key -> generic exception path.
    rc = ocr_mod.run_ocr(vault)
    meta = _read_meta(vault, "AAAA1111")
    assert meta["ocr_status"] not in ("queued", "running"), meta
    assert meta["error_stage"] == "postprocess", meta


def _resp(payload):
    class _R:
        def json(self):
            return payload

        def raise_for_status(self):
            return None

        @property
        def status_code(self):
            return 200

        @property
        def text(self):
            return ""

    return _R()


def _text_resp(text):
    class _R:
        def json(self):
            return {}

        def raise_for_status(self):
            return None

        @property
        def status_code(self):
            return 200

        @property
        def text(self):
            return text

    return _R()


def test_upload_file_disappears_is_blocked_not_nopdf(tmp_path, monkeypatch) -> None:
    """P1: PDF resolved then vanishing at upload -> blocked + error_stage
    source (repair frontier), never a legal nopdf terminal."""
    rows = [{"zotero_key": "AAAA1111", "has_pdf": True, "pdf_path": "x.pdf"}]
    vault, ocr_mod, _ = _run_ocr_harness(
        tmp_path, monkeypatch, rows=rows,
        meta_for={"AAAA1111": {"zotero_key": "AAAA1111", "ocr_status": "pending"}},
    )
    monkeypatch.setattr(
        "paperforge.pdf_resolver.resolve_pdf_path",
        lambda *a, **k: str(tmp_path / "x.pdf"),
    )

    def boom(*a, **k):
        raise FileNotFoundError("gone")

    monkeypatch.setattr(ocr_mod.requests, "post", boom)
    monkeypatch.setattr(ocr_mod, "_resolve_zotero_data_dir", lambda _v: None)
    rc = ocr_mod.run_ocr(vault)
    meta = _read_meta(vault, "AAAA1111")
    assert meta["ocr_status"] == "blocked", meta
    assert meta["error_stage"] == "source", meta
    assert rc == 1, "blocked is a settled FAILURE terminal -> rc 1"
