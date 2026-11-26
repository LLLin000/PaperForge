"""Heavy mixed-state stress tests for the OCR batch state machine (run_ocr & ocr.run)."""

from __future__ import annotations

import json
import os
import sys
import threading
import types
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

from tests.conftest import canonical_test_config


def _write_valid_pdf(path: Path) -> None:
    import pymupdf

    path.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), f"Synthetic medical paper PDF for {path.stem}.")
        doc.save(path)


def _valid_jsonl_result(key: str) -> str:
    body = " ".join(
        f"Clinical cohort evaluation for {key} paragraph segment {i}." for i in range(18)
    )
    payload = {
        "result": {
            "layoutParsingResults": [
                {
                    "prunedResult": {
                        "page_count": 1,
                        "width": 1000,
                        "height": 1400,
                        "parsing_res_list": [
                            {
                                "block_label": "doc_title",
                                "block_content": f"Title for {key}",
                                "block_bbox": [80, 60, 900, 120],
                                "block_id": 0,
                            },
                            {
                                "block_label": "text",
                                "block_content": body,
                                "block_bbox": [80, 150, 920, 800],
                                "block_id": 1,
                            },
                        ],
                    }
                }
            ]
        }
    }
    return json.dumps(payload, ensure_ascii=False)


class _Resp:
    def __init__(
        self,
        *,
        status_code: int = 200,
        json_data: dict | None = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self) -> dict:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            err = requests.exceptions.HTTPError(f"HTTP {self.status_code}", response=self)
            raise err


@pytest.fixture(autouse=True)
def _isolate_ocr_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPERFORGE_CREDENTIAL_OCR__DEFAULT", "stress-test-token")
    monkeypatch.setenv("PAPERFORGE_POLL_INTERVAL", "0")
    monkeypatch.setenv("PAPERFORGE_POLL_MAX_CYCLES", "30")
    monkeypatch.setenv("PADDLEOCR_MAX_ITEMS", "3")
    monkeypatch.setitem(
        sys.modules,
        "winreg",
        types.SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            HKEY_LOCAL_MACHINE=object(),
            OpenKey=lambda *a, **kw: (_ for _ in ()).throw(OSError("no registry")),
            OpenKeyEx=lambda *a, **kw: (_ for _ in ()).throw(OSError("no registry")),
            QueryValueEx=lambda *a, **kw: (_ for _ in ()).throw(OSError("no registry")),
        ),
    )


def _setup_vault_papers(tmp_path: Path, specs: list[dict]) -> tuple[Path, dict[str, Path]]:
    from paperforge.worker._utils import pipeline_paths

    vault = tmp_path / "vault"
    vault.mkdir(parents=True, exist_ok=True)
    canonical_test_config(vault)
    paths = pipeline_paths(vault)
    paths["ocr"].mkdir(parents=True, exist_ok=True)
    paths["exports"].mkdir(parents=True, exist_ok=True)
    paths["literature"].mkdir(parents=True, exist_ok=True)
    lr_dir = paths["library_records"] / "Orthopedics"
    lr_dir.mkdir(parents=True, exist_ok=True)

    export_rows: list[dict] = []
    for spec in specs:
        key = spec["key"]
        pdf_rel = spec.get("pdf_rel", f"pdfs/{key}.pdf")
        has_pdf = spec.get("has_pdf", True)
        create_pdf = spec.get("create_pdf", has_pdf)
        if has_pdf and create_pdf:
            _write_valid_pdf(vault / pdf_rel)
        attachments = (
            [{"contentType": "application/pdf", "path": pdf_rel}] if has_pdf else []
        )
        export_rows.append(
            {"key": key, "title": f"Paper {key}", "attachments": attachments}
        )
        (lr_dir / f"{key}.md").write_text(
            f"---\nzotero_key: {key}\nanalyze: false\ndo_ocr: true\n---\n# {key}\n",
            encoding="utf-8",
        )
        paper_dir = paths["ocr"] / key
        paper_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "zotero_key": key,
            "ocr_status": spec.get("initial_status", "pending"),
            "ocr_job_id": spec.get("initial_job_id", ""),
            "retry_count": spec.get("retry_count", 0),
            "job_attempt": spec.get("job_attempt", 0),
        }
        if spec.get("create_valid_done"):
            (paper_dir / "json").mkdir(parents=True, exist_ok=True)
            (paper_dir / "json" / "result.json").write_text("x" * 2048, encoding="utf-8")
            (paper_dir / "fulltext.md").write_text(
                "<!-- page 1 -->\n"
                + ("Valid clinical fulltext content. " * 20)
                + "\n<!-- page 2 -->\n"
                + ("More clinical evidence. " * 15),
                encoding="utf-8",
            )
            meta["page_count"] = 2
        elif spec.get("create_tiny_done"):
            (paper_dir / "json").mkdir(parents=True, exist_ok=True)
            (paper_dir / "json" / "result.json").write_text("x" * 2048, encoding="utf-8")
            (paper_dir / "fulltext.md").write_text("tiny", encoding="utf-8")
            meta["page_count"] = 2
        (paper_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    (paths["exports"] / "Orthopedics.json").write_text(
        json.dumps(export_rows), encoding="utf-8"
    )
    return vault, paths


class _MockBatchProvider:
    """Disable batch endpoint so all tests exercise per-job poll deterministically."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def get_batch_status(self, batch_id: str) -> dict:
        raise RuntimeError("batch endpoint offline in unit stress test")

    def extract_result_url(self, payload: dict) -> str:
        return ""


class TestOcrBatchStress:
    def test_16_paper_mixed_state_ocr_storm_no_slot_leak_or_deadlock(
        self, tmp_path: Path
    ) -> None:
        """16 mixed-state papers with max_items=3: errors, blocked, nopdf,
        poll exceptions, result-unavailable slot-leak traps, provider retries,
        and postprocess crashes must NOT deadlock remaining pending papers."""
        from paperforge.worker.ocr import run_ocr

        specs = [
            {"key": "P01_ALREADY_DONE", "initial_status": "done", "create_valid_done": True},
            {"key": "P02_DONE_DEGRADED", "initial_status": "done_degraded", "create_valid_done": True},
            {"key": "P03_DONE_INCOMPLETE", "initial_status": "done", "create_tiny_done": True},
            {"key": "P04_NOPDF", "has_pdf": False},
            {"key": "P05_MISSING_PDF", "has_pdf": True, "create_pdf": False},
            {"key": "P06_PREQUEUED_POLL_EXC", "initial_status": "queued", "initial_job_id": "job-pre-exc"},
            {"key": "P07_PREQUEUED_OK", "initial_status": "queued", "initial_job_id": "job-pre-ok"},
            {"key": "P08_RESULT_EMPTY_URL"},
            {"key": "P09_RESULT_DL_FAIL"},
            {"key": "P10_RESULT_DL_FAIL_2"},
            {"key": "P11_HTTP_403_BLOCKED"},
            {"key": "P12_HTTP_429_QUOTA"},
            {"key": "P13_PROVIDER_RETRY_OK"},
            {"key": "P14_PROVIDER_FATAL_3X"},
            {"key": "P15_POSTPROCESS_CRASH"},
            {"key": "P16_TAIL_PENDING_OK"},
        ]
        vault, paths = _setup_vault_papers(tmp_path, specs)

        upload_counts: dict[str, int] = {}
        poll_counts: dict[str, int] = {
            "job-pre-exc": 0,
            "job-pre-ok": 0,
        }
        job_to_key: dict[str, str] = {
            "job-pre-exc": "P06_PREQUEUED_POLL_EXC",
            "job-pre-ok": "P07_PREQUEUED_OK",
        }
        lock = threading.Lock()

        def _fake_post(url: str, *, data=None, files=None, **kwargs):
            file_obj = files["file"]
            key = Path(file_obj.name).stem
            with lock:
                n = upload_counts.get(key, 0) + 1
                upload_counts[key] = n
            if key == "P11_HTTP_403_BLOCKED":
                return _Resp(status_code=403, text="Forbidden")
            if key == "P12_HTTP_429_QUOTA":
                return _Resp(status_code=429, text="Quota exhausted")
            job_id = f"job-{key}-{n}"
            with lock:
                job_to_key[job_id] = key
                poll_counts[job_id] = 0
            return _Resp(status_code=200, json_data={"data": {"jobId": job_id}})

        def _fake_get(url: str, **kwargs):
            if url.startswith("http://result.local/"):
                key = url.rsplit("/", 1)[-1]
                if key in {"P09_RESULT_DL_FAIL", "P10_RESULT_DL_FAIL_2"}:
                    raise requests.exceptions.ConnectionError(f"download failed for {key}")
                if key == "P15_POSTPROCESS_CRASH":
                    return _Resp(
                        status_code=200,
                        text=json.dumps(
                            {"result": {"layoutParsingResults": [{"prunedResult": "CORRUPT_POSTPROCESS"}]}}
                        ),
                    )
                return _Resp(status_code=200, text=_valid_jsonl_result(key))

            job_id = url.rsplit("/", 1)[-1]
            with lock:
                poll_counts[job_id] = poll_counts.get(job_id, 0) + 1
                pcount = poll_counts[job_id]
                key = job_to_key[job_id]

            if key == "P06_PREQUEUED_POLL_EXC":
                raise requests.exceptions.Timeout("initial poll timeout")
            if key == "P07_PREQUEUED_OK":
                if pcount == 1:
                    return _Resp(status_code=200, json_data={"data": {"state": "running"}})
                return _Resp(
                    status_code=200,
                    json_data={
                        "data": {
                            "state": "done",
                            "resultUrl": {"jsonUrl": f"http://result.local/{key}"},
                        }
                    },
                )
            if key == "P08_RESULT_EMPTY_URL":
                return _Resp(
                    status_code=200,
                    json_data={"data": {"state": "done", "resultUrl": {"jsonUrl": ""}}},
                )
            if key == "P13_PROVIDER_RETRY_OK":
                attempt = upload_counts.get(key, 1)
                if attempt == 1:
                    return _Resp(
                        status_code=200,
                        json_data={"data": {"state": "failed", "errorMsg": "transient gpu oom"}},
                    )
                return _Resp(
                    status_code=200,
                    json_data={
                        "data": {
                            "state": "done",
                            "resultUrl": {"jsonUrl": f"http://result.local/{key}"},
                        }
                    },
                )
            if key == "P14_PROVIDER_FATAL_3X":
                return _Resp(
                    status_code=200,
                    json_data={"data": {"state": "failed", "errorMsg": "corrupt pdf stream"}},
                )
            return _Resp(
                status_code=200,
                json_data={
                    "data": {
                        "state": "done",
                        "resultUrl": {"jsonUrl": f"http://result.local/{key}"},
                    }
                },
            )

        progressed: list[str] = []
        sink: dict = {}

        with (
            patch("paperforge.worker.ocr.requests.post", side_effect=_fake_post),
            patch("paperforge.worker.ocr.requests.get", side_effect=_fake_get),
            patch("paperforge.providers.paddleocr.PaddleOCRProvider", _MockBatchProvider),
            patch("paperforge.worker.sync.run_selection_sync"),
            patch("paperforge.worker.sync.run_index_refresh"),
            patch("paperforge.worker.ocr.retry_with_meta", side_effect=lambda fn, _m, *a, **kw: fn(*a, **kw)),
        ):
            rc = run_ocr(
                vault,
                no_progress=True,
                progress_callback=progressed.append,
                result_sink=sink,
            )

        assert rc == 1  # expected because batch contains blocked/failed/queued papers
        per_key = sink["per_key"]

        # Papers that MUST complete despite P06/P08/P09/P10/P15 slot-leak hazards:
        for ok_key in (
            "P01_ALREADY_DONE",
            "P02_DONE_DEGRADED",
            "P03_DONE_INCOMPLETE",
            "P07_PREQUEUED_OK",
            "P13_PROVIDER_RETRY_OK",
            "P16_TAIL_PENDING_OK",
        ):
            assert per_key[ok_key] in ("done", "done_degraded"), f"{ok_key} landed in {per_key[ok_key]}"

        # Already done papers were NOT re-uploaded:
        assert "P01_ALREADY_DONE" not in upload_counts
        assert "P02_DONE_DEGRADED" not in upload_counts
        assert upload_counts["P03_DONE_INCOMPLETE"] == 1
        assert upload_counts["P13_PROVIDER_RETRY_OK"] == 2
        assert upload_counts["P14_PROVIDER_FATAL_3X"] == 3
        assert upload_counts["P16_TAIL_PENDING_OK"] == 1

        # Exact failure & classification settlements:
        assert per_key["P04_NOPDF"] == "nopdf"
        assert per_key["P05_MISSING_PDF"] == "blocked"
        assert per_key["P11_HTTP_403_BLOCKED"] == "blocked"
        assert per_key["P12_HTTP_429_QUOTA"] == "error"
        assert per_key["P14_PROVIDER_FATAL_3X"] == "fatal_error"
        assert per_key["P15_POSTPROCESS_CRASH"] == "fatal_error"

        assert "P12_HTTP_429_QUOTA" in sink["rate_limited_keys"]
        assert {"P08_RESULT_EMPTY_URL", "P09_RESULT_DL_FAIL", "P10_RESULT_DL_FAIL_2"} <= set(
            sink["result_unavailable_keys"]
        )
        # All terminal settlement failures also emit progress notifications:
        for terminal_key in (
            "P03_DONE_INCOMPLETE",
            "P04_NOPDF",
            "P05_MISSING_PDF",
            "P07_PREQUEUED_OK",
            "P11_HTTP_403_BLOCKED",
            "P12_HTTP_429_QUOTA",
            "P13_PROVIDER_RETRY_OK",
            "P14_PROVIDER_FATAL_3X",
            "P15_POSTPROCESS_CRASH",
            "P16_TAIL_PENDING_OK",
        ):
            assert terminal_key in progressed, f"{terminal_key} never reported progress"

        assert not (paths["ocr"] / "controller.lock").exists()

    def test_12_paper_ocr_cooperative_stop_mid_batch_and_resume(
        self, tmp_path: Path
    ) -> None:
        """Stop after 3 settled papers out of 12, confirm rc == 130 and lock
        release, then resume to complete remaining papers with zero duplicate uploads."""
        from paperforge.worker.ocr import run_ocr

        specs = [{"key": f"K{i:02d}"} for i in range(1, 13)]
        vault, paths = _setup_vault_papers(tmp_path, specs)

        upload_counts: dict[str, int] = {}
        settled: list[str] = []
        stop_flag = False

        def _fake_post(url: str, *, files=None, **kwargs):
            key = Path(files["file"].name).stem
            upload_counts[key] = upload_counts.get(key, 0) + 1
            return _Resp(status_code=200, json_data={"data": {"jobId": f"j-{key}"}})

        def _fake_get(url: str, **kwargs):
            if url.startswith("http://result.local/"):
                key = url.rsplit("/", 1)[-1]
                return _Resp(status_code=200, text=_valid_jsonl_result(key))
            key = url.rsplit("/", 1)[-1].removeprefix("j-")
            return _Resp(
                status_code=200,
                json_data={
                    "data": {
                        "state": "done",
                        "resultUrl": {"jsonUrl": f"http://result.local/{key}"},
                    }
                },
            )

        def _on_progress(k: str) -> None:
            nonlocal stop_flag
            settled.append(k)
            if len(settled) >= 3:
                stop_flag = True

        sink1: dict = {}
        with (
            patch("paperforge.worker.ocr.requests.post", side_effect=_fake_post),
            patch("paperforge.worker.ocr.requests.get", side_effect=_fake_get),
            patch("paperforge.providers.paddleocr.PaddleOCRProvider", _MockBatchProvider),
            patch("paperforge.worker.sync.run_selection_sync"),
            patch("paperforge.worker.sync.run_index_refresh"),
        ):
            rc1 = run_ocr(
                vault,
                no_progress=True,
                stop_check=lambda: stop_flag,
                progress_callback=_on_progress,
                result_sink=sink1,
            )

        assert rc1 == 130
        assert not (paths["ocr"] / "controller.lock").exists()
        assert len(settled) == 3

        # Pass 2: resume without stop — all 12 settle with zero duplicate uploads.
        sink2: dict = {}
        with (
            patch("paperforge.worker.ocr.requests.post", side_effect=_fake_post),
            patch("paperforge.worker.ocr.requests.get", side_effect=_fake_get),
            patch("paperforge.providers.paddleocr.PaddleOCRProvider", _MockBatchProvider),
            patch("paperforge.worker.sync.run_selection_sync"),
            patch("paperforge.worker.sync.run_index_refresh"),
        ):
            rc2 = run_ocr(vault, no_progress=True, result_sink=sink2)

        assert rc2 == 0
        assert all(sink2["per_key"][f"K{i:02d}"] in ("done", "done_degraded") for i in range(1, 13))
        assert all(upload_counts[f"K{i:02d}"] == 1 for i in range(1, 13))

    def test_ocr_controller_lock_released_on_unexpected_exception(
        self, tmp_path: Path
    ) -> None:
        from paperforge.worker.ocr import run_ocr

        vault, paths = _setup_vault_papers(tmp_path, [{"key": "KERR01"}])

        with (
            patch("paperforge.worker.ocr.requests.post", side_effect=RuntimeError("boom-unexpected")),
            patch("paperforge.worker.sync.run_selection_sync"),
            patch("paperforge.worker.sync.run_index_refresh"),
            patch("paperforge.worker.ocr.write_ocr_queue", side_effect=RuntimeError("disk exploded")),
        ):
            with pytest.raises(RuntimeError, match="disk exploded"):
                run_ocr(vault, no_progress=True)

        assert not (paths["ocr"] / "controller.lock").exists()

    def test_ocr_action_handler_emits_item_result_for_all_mixed_outcomes(
        self, tmp_path: Path, capsys
    ) -> None:
        """_ocr_run_handler must emit item_result for upload-stage blocked/nopdf/error
        papers as well as succeeded papers, keeping stdout strictly machine-only."""
        from paperforge.actions.registry import ACTION_REGISTRY
        from paperforge.actions.types import (
            ActionContext,
            ActionExecutionHooks,
            ActionRequest,
            AllScope,
        )

        specs = [
            {"key": "ACT_OK"},
            {"key": "ACT_NOPDF", "has_pdf": False},
            {"key": "ACT_MISSING", "has_pdf": True, "create_pdf": False},
            {"key": "ACT_403"},
        ]
        vault, _ = _setup_vault_papers(tmp_path, specs)

        def _fake_post(url: str, *, files=None, **kwargs):
            key = Path(files["file"].name).stem
            if key == "ACT_403":
                return _Resp(status_code=403, text="Denied")
            return _Resp(status_code=200, json_data={"data": {"jobId": f"j-{key}"}})

        def _fake_get(url: str, **kwargs):
            if url.startswith("http://result.local/"):
                key = url.rsplit("/", 1)[-1]
                return _Resp(status_code=200, text=_valid_jsonl_result(key))
            key = url.rsplit("/", 1)[-1].removeprefix("j-")
            return _Resp(
                status_code=200,
                json_data={
                    "data": {
                        "state": "done",
                        "resultUrl": {"jsonUrl": f"http://result.local/{key}"},
                    }
                },
            )

        events: list[tuple[str, str]] = []
        progress_calls: list[str] = []
        hooks = ActionExecutionHooks(
            progress=lambda cur, tot, item_id: progress_calls.append(item_id),
            item_result=lambda item_id, status: events.append((item_id, status)),
        )
        ctx = ActionContext(vault=vault, config={}, paths={}, execution_hooks=hooks)
        req = ActionRequest(action_id="ocr.run", scope=AllScope())

        with (
            patch("paperforge.worker.ocr.requests.post", side_effect=_fake_post),
            patch("paperforge.worker.ocr.requests.get", side_effect=_fake_get),
            patch("paperforge.providers.paddleocr.PaddleOCRProvider", _MockBatchProvider),
            patch("paperforge.worker.sync.run_selection_sync"),
            patch("paperforge.worker.sync.run_index_refresh"),
        ):
            res = ACTION_REGISTRY["ocr.run"].handler(ctx, req)

        captured = capsys.readouterr()
        assert captured.out.strip() == ""
        assert not res.ok
        assert res.successful_keys == ["ACT_OK"]
        by_key = dict(events)
        assert by_key["ACT_OK"] in ("done", "done_degraded")
        assert by_key["ACT_NOPDF"] == "nopdf"
        assert by_key["ACT_MISSING"] == "blocked"
        assert by_key["ACT_403"] == "blocked"
        assert set(progress_calls) == {"ACT_OK", "ACT_NOPDF", "ACT_MISSING", "ACT_403"}
