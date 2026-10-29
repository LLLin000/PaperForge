"""#349: synthetic PDFs through the real CLI/worker to the final HTTP seam."""

from __future__ import annotations

import json
import socket

import pymupdf
import pytest
import responses

from paperforge.cli import main
from paperforge.worker._utils import pipeline_paths
from tests.conftest import canonical_test_config


@pytest.fixture
def scope_vault(tmp_path, monkeypatch):
    # Never consult a real credential, export, PDF, or outbound socket.
    monkeypatch.setattr(socket.socket, "connect", lambda *_: pytest.fail("outbound socket forbidden"))
    monkeypatch.setenv("PAPERFORGE_CREDENTIAL_OCR__DEFAULT", "synthetic-scope-token")
    monkeypatch.setenv("PAPERFORGE_POLL_INTERVAL", "0")
    monkeypatch.setenv("PAPERFORGE_POLL_MAX_CYCLES", "1")
    vault = tmp_path / "vault"
    vault.mkdir()
    canonical_test_config(vault)
    paths = pipeline_paths(vault)
    paths["exports"].mkdir(parents=True, exist_ok=True)
    paths["ocr"].mkdir(parents=True, exist_ok=True)
    rows = []
    pdfs = {}
    for key in ("SCOPE001", "SCOPE002"):
        pdf = vault / f"{key}.pdf"
        with pymupdf.open() as doc:
            doc.new_page().insert_text((72, 72), f"Synthetic scope fixture {key}")
            doc.save(pdf)
        pdfs[key] = pdf.read_bytes()
        rows.append(
            {
                "key": key,
                "title": f"Synthetic {key}",
                "attachments": [{"contentType": "application/pdf", "path": str(pdf)}],
            }
        )
    (paths["exports"] / "synthetic.json").write_text(json.dumps(rows), encoding="utf-8")
    from paperforge.worker.asset_index import get_index_path

    index_path = get_index_path(vault)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {"items": [{"zotero_key": key, "pdf_path": str(vault / f"{key}.pdf"), "has_pdf": True} for key in pdfs]}
        ),
        encoding="utf-8",
    )
    paths["ocr_queue"].write_text(
        json.dumps(
            [
                {"zotero_key": key, "has_pdf": True, "pdf_path": str(vault / f"{key}.pdf"), "queue_status": "pending"}
                for key in pdfs
            ]
        ),
        encoding="utf-8",
    )
    return vault, pdfs


@pytest.mark.parametrize(
    "argv",
    [
        ["ocr", "--key", "SCOPE001"],
        ["ocr", "run", "SCOPE001"],
        ["action", "run", "ocr.run", "--scope", "papers", "--key", "SCOPE001", "--confirm", "ocr.run", "--json"],
    ],
)
def test_cli_key_uploads_only_requested_pdf(scope_vault, argv):
    vault, pdfs = scope_vault
    uploaded = []

    def submit(request):
        body = request.body
        matches = [key for key, pdf in pdfs.items() if pdf in body]
        assert len(matches) == 1, "multipart upload must contain exactly one identifiable PDF"
        uploaded.extend(matches)
        return 202, {"Content-Type": "application/json"}, json.dumps({"data": {"jobId": f"job-{matches[0]}"}})

    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        http.add_callback(responses.POST, "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs", callback=submit)
        for key in pdfs:
            http.get(
                f"https://paddleocr.aistudio-app.com/api/v2/ocr/jobs/job-{key}", json={"data": {"state": "running"}}
            )
        main(["--vault", str(vault), *argv])
    assert uploaded == ["SCOPE001"]


@pytest.mark.parametrize(
    "argv",
    [
        ["ocr", "run", "UNKNOWN1"],
        ["ocr", "run", "SCOPE001", "UNKNOWN1"],
        ["ocr", "--key", " "],
        ["ocr", "run", " "],
        ["ocr", "run", "SCOPE001", " "],
        [
            "action",
            "run",
            "ocr.run",
            "--scope",
            "papers",
            "--key",
            "SCOPE001",
            "--key",
            " ",
            "--confirm",
            "ocr.run",
            "--json",
        ],
        ["ocr", "run", "--keys-file", "missing-keys.txt"],
        ["action", "run", "ocr.run", "--scope", "papers", "--key", "UNKNOWN1", "--confirm", "ocr.run", "--json"],
        [
            "action",
            "run",
            "ocr.run",
            "--scope",
            "papers",
            "--key",
            "SCOPE001",
            "--key",
            "UNKNOWN1",
            "--confirm",
            "ocr.run",
            "--json",
        ],
        ["action", "run", "ocr.run", "--scope", "papers", "--key", " ", "--confirm", "ocr.run", "--json"],
    ],
)
def test_invalid_scope_refuses_before_any_write_or_http(scope_vault, capsys, argv):
    vault, _ = scope_vault
    before = {p.relative_to(vault): p.read_bytes() for p in vault.rglob("*") if p.is_file()}
    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        rc = main(["--vault", str(vault), *argv])
        assert not http.calls
    assert rc != 0
    output = capsys.readouterr()
    assert any(word in output.out + output.err for word in ("unknown paper keys", "scope", "keys file"))
    assert {p.relative_to(vault): p.read_bytes() for p in vault.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("entry", ["cli", "action"])
@pytest.mark.parametrize("extra_keys", [[], ["SCOPE001"]])
def test_explicit_empty_file_never_means_all(scope_vault, capsys, extra_keys, entry):
    vault, _ = scope_vault
    empty = vault / "empty-keys.txt"
    empty.write_text("\ufeff \r\n", encoding="utf-8")
    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        argv = (
            ["ocr", "run", *extra_keys]
            if entry == "cli"
            else [
                "action",
                "run",
                "ocr.run",
                "--scope",
                "papers",
                "--confirm",
                "ocr.run",
                "--json",
                *[arg for key in extra_keys for arg in ("--key", key)],
            ]
        )
        rc = main(["--vault", str(vault), *argv, "--keys-file", str(empty)])
        assert not http.calls
    assert rc != 0
    captured = capsys.readouterr()
    assert "scope" in captured.out + captured.err


@pytest.mark.parametrize("entry", ["worker", "action"])
def test_stop_after_first_upload_never_submits_next_paper(scope_vault, capsys, monkeypatch, entry):
    from paperforge.worker.ocr import run_ocr

    vault, pdfs = scope_vault
    uploaded = []

    def submit(request):
        uploaded.extend(key for key, pdf in pdfs.items() if pdf in request.body)
        return 202, {}, json.dumps({"data": {"jobId": "synthetic-job"}})

    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        http.add_callback(responses.POST, "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs", callback=submit)
        http.get(
            "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs/synthetic-job", json={"data": {"state": "running"}}
        )
        if entry == "action":
            monkeypatch.setattr(
                "paperforge.core.cancellation.make_cancellation_token", lambda: (lambda: bool(uploaded), lambda: None)
            )
            rc = main(
                [
                    "--vault",
                    str(vault),
                    "action",
                    "run",
                    "ocr.run",
                    "--scope",
                    "papers",
                    "--key",
                    "SCOPE001",
                    "--key",
                    "SCOPE002",
                    "--confirm",
                    "ocr.run",
                    "--json",
                ]
            )
        else:
            rc = run_ocr(vault, selected_keys=set(pdfs), stop_check=lambda: bool(uploaded))
    assert uploaded == ["SCOPE001"]
    assert rc == 130
    assert "Remote OCR jobs continue" in capsys.readouterr().err
    meta = json.loads((pipeline_paths(vault)["ocr"] / "SCOPE001" / "meta.json").read_text())
    assert meta["ocr_job_id"] == "synthetic-job"
    assert meta["ocr_status"] in ("queued", "running")


def test_scoped_run_preserves_unselected_blocked_and_zombie_state(scope_vault):
    from paperforge.worker.ocr import run_ocr

    vault, _ = scope_vault
    ocr = pipeline_paths(vault)["ocr"]
    for key, status in (("BLOCK001", "blocked"), ("SCOPE002", "running")):
        folder = ocr / key
        folder.mkdir()
        (folder / "meta.json").write_text(
            json.dumps({"zotero_key": key, "ocr_status": status, "ocr_started_at": "2020-01-01T00:00:00+00:00"}),
            encoding="utf-8",
        )
    before = {p: p.read_bytes() for key in ("BLOCK001", "SCOPE002") for p in (ocr / key).rglob("*") if p.is_file()}
    with responses.RequestsMock(assert_all_requests_are_fired=False):
        run_ocr(vault, selected_keys={"SCOPE001"}, stop_check=lambda: True)
    assert {p: p.read_bytes() for p in before if p.exists()} == before


def test_stop_during_transport_retry_prevents_another_post(scope_vault, monkeypatch):
    from paperforge.worker.ocr import run_ocr

    vault, _ = scope_vault
    monkeypatch.setenv("PAPERFORGE_RETRY_MAX", "2")
    monkeypatch.setenv("PAPERFORGE_RETRY_BACKOFF", "0")
    attempts = []

    def rejected(request):
        attempts.append(request.url)
        return 503, {}, "synthetic temporary failure"

    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        http.add_callback(responses.POST, "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs", callback=rejected)
        rc = run_ocr(vault, selected_keys={"SCOPE001"}, stop_check=lambda: bool(attempts))
    assert len(attempts) == 1
    assert rc == 130


def test_whole_library_action_requires_explicit_confirmation(scope_vault, capsys):
    vault, _ = scope_vault
    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        rc = main(["--vault", str(vault), "action", "run", "ocr.run", "--scope", "all", "--json"])
        assert not http.calls
    assert rc == 3
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert events[-1]["result"]["error"]["code"] == "action.confirmation_required"


def test_fresh_list_selection_reaches_only_selected_pdf(scope_vault, capsys):
    """#351: discovery without seeded OCR artifacts feeds the final HTTP scope."""
    vault, pdfs = scope_vault
    paths = pipeline_paths(vault)
    paths["ocr_queue"].unlink()
    paths["ocr"].rmdir()
    before = {p: p.read_bytes() for p in vault.rglob("*") if p.is_file()}
    main(["--vault", str(vault), "ocr", "list", "--json"])
    rows = json.loads(capsys.readouterr().out)
    assert {r["key"]: r["status"] for r in rows} == {"SCOPE001": "pending", "SCOPE002": "pending"}
    assert not paths["ocr"].exists()
    assert {p: p.read_bytes() for p in before} == before
    selected = next(r["key"] for r in rows if r["key"] == "SCOPE001")
    uploads = []

    def submit(request):
        matches = [key for key, pdf in pdfs.items() if pdf in request.body]
        assert matches == ["SCOPE001"]
        uploads.extend(matches)
        return 202, {}, json.dumps({"data": {"jobId": "fresh-list-job"}})

    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        http.add_callback(responses.POST, "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs", callback=submit)
        http.get("https://paddleocr.aistudio-app.com/api/v2/ocr/jobs/fresh-list-job", json={"data": {"state": "running"}})
        rc = main(["--vault", str(vault), "action", "run", "ocr.run", "--scope", "papers",
                   "--key", selected, "--confirm", "ocr.run", "--json"])
    assert rc == 1  # Scripted provider stays pending, never successful OCR.
    assert uploads == ["SCOPE001"]
    assert not (paths["ocr"] / "SCOPE002").exists()


def test_controlled_401_returns_blocked_not_poll_timeout(scope_vault, capsys) -> None:
    """HTTP 401 is a credential rejection, not a poll window: the action
    terminal must be blocked/actionable, never OCR_POLL_TIMEOUT with a
    re-run-polling instruction.  Pending work is absent, so nothing may
    claim a resumable poll; partial successes (none here) would survive."""
    import requests

    vault, _ = scope_vault

    def rejected(request):
        raise requests.exceptions.HTTPError(
            "401 Client Error: Unauthorized",
            response=type("R", (), {"status_code": 401, "text": "invalid token"})(),
        )

    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        http.add_callback(
            responses.POST,
            "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
            callback=rejected,
        )
        rc = main([
            "--vault", str(vault), "action", "run", "ocr.run",
            "--scope", "papers", "--key", "SCOPE001",
            "--confirm", "ocr.run", "--json",
        ])
    assert rc == 1
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    terminal = next(e for e in events if e.get("event") in ("result", "error", "cancelled"))
    result = terminal.get("result", {})
    assert result.get("ok") is False
    error = result.get("error", {}) or {}
    assert error.get("code") != "OCR_POLL_TIMEOUT"
    assert error.get("code") == "OCR_UPLOAD_FAILED"
    assert "poll" not in str(error.get("message", "")).lower() or "before retry" in str(error.get("message", "")).lower()
    data = result.get("data", {}) or {}
    assert (data.get("summary", {}) or {}).get("blocked", 0) >= 1
    assert (data.get("summary", {}) or {}).get("pending", 0) == 0
    assert "SCOPE001" in (data.get("blocked_keys", []) or [])

def test_unconfirmed_upload_never_resubmits(scope_vault, monkeypatch, capsys) -> None:
    """A lost upload response may hide an accepted remote job."""
    import requests

    vault, _ = scope_vault
    monkeypatch.setenv("PAPERFORGE_RETRY_MAX", "2")
    monkeypatch.setenv("PAPERFORGE_RETRY_BACKOFF", "0")
    calls = []

    def dropped(request):
        calls.append(1)
        raise requests.ConnectionError("synthetic response disconnect")

    argv = [
        "--vault", str(vault), "action", "run", "ocr.run",
        "--scope", "papers", "--key", "SCOPE001", "--confirm", "ocr.run", "--json",
    ]
    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        http.add_callback(responses.POST, "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs", callback=dropped)
        assert main(argv) == 1
        events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
        terminal = next(e for e in events if e.get("event") in ("result", "error", "cancelled"))
        message = terminal["result"]["error"]["message"].lower()
        assert "unconfirmed" in message
        assert "do not" in message
        assert main(argv) == 1
    assert len(calls) == 1
    meta = json.loads((pipeline_paths(vault)["ocr"] / "SCOPE001" / "meta.json").read_text(encoding="utf8"))
    assert meta["submission_state"] == "submitting"
    assert not meta.get("ocr_job_id")


def test_rate_limit_is_a_confirmed_rejection_not_poll_timeout(scope_vault, capsys) -> None:
    vault, _ = scope_vault
    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        http.post("https://paddleocr.aistudio-app.com/api/v2/ocr/jobs", status=429, json={"error": "quota"})
        rc = main([
            "--vault", str(vault), "action", "run", "ocr.run",
            "--scope", "papers", "--key", "SCOPE001", "--confirm", "ocr.run", "--json",
        ])
        posts = [call for call in http.calls if call.request.method == "POST"]
        assert len(posts) == 1
    assert rc == 1
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    result = next(e for e in events if e.get("event") in ("result", "error"))["result"]
    assert result["error"]["code"] == "OCR_RESULT_INVALID"
    assert "quota" in result["error"]["message"].lower()
    assert "SCOPE001" in result["data"]["failed_keys"]
    meta = json.loads((pipeline_paths(vault)["ocr"] / "SCOPE001" / "meta.json").read_text(encoding="utf8"))
    assert meta["provider_error_status"] == 429
    assert meta.get("submission_state") != "submitting"


def test_rate_limit_with_pending_job_does_not_promise_safe_whole_batch_retry(scope_vault, capsys) -> None:
    vault, _ = scope_vault
    def submit(request):
        if b"SCOPE001" in request.body:
            return 429, {}, json.dumps({"error": "quota"})
        return 202, {}, json.dumps({"data": {"jobId": "job-two"}})

    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        http.add_callback(responses.POST, "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs", callback=submit)
        http.get("https://paddleocr.aistudio-app.com/api/v2/ocr/jobs/job-two", json={"data": {"state": "running"}})
        rc = main([
            "--vault", str(vault), "action", "run", "ocr.run", "--scope", "papers",
            "--key", "SCOPE001", "--key", "SCOPE002", "--confirm", "ocr.run", "--json",
        ])
    assert rc == 1
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    result = next(e for e in events if e.get("event") in ("result", "error"))["result"]
    assert "quota" in result["error"]["message"].lower()
    assert "without new uploads" not in result["error"]["message"].lower()
    assert "SCOPE001" in result["data"]["failed_keys"]
    assert "SCOPE002" in result["data"]["pending_keys"]


def test_timed_out_remote_job_keeps_identity_without_new_upload(scope_vault, monkeypatch) -> None:
    vault, _ = scope_vault
    monkeypatch.setenv("PAPERFORGE_ZOMBIE_TIMEOUT_MINUTES", "0")
    monkeypatch.setattr("paperforge.worker.ocr._paper_timed_out", lambda _meta: True)
    meta = pipeline_paths(vault)["ocr"] / "SCOPE001" / "meta.json"
    meta.parent.mkdir(parents=True)
    meta.write_text(json.dumps({
        "zotero_key": "SCOPE001", "ocr_status": "queued", "ocr_job_id": "old-job",
        "ocr_started_at": "2020-01-01T00:00:00+00:00", "submission_state": "submitted",
    }), encoding="utf8")
    argv = [
        "--vault", str(vault), "action", "run", "ocr.run",
        "--scope", "papers", "--key", "SCOPE001", "--confirm", "ocr.run", "--json",
    ]
    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        http.get("https://paddleocr.aistudio-app.com/api/v2/ocr/jobs/old-job", json={"data": {"state": "running"}})
        assert main(argv) == 1
        assert main(argv) == 1
        assert not [call for call in http.calls if call.request.method == "POST"]
    state = json.loads(meta.read_text(encoding="utf8"))
    assert state["ocr_job_id"] == "old-job"
    assert state["ocr_status"] in ("queued", "running")


def test_missing_remote_result_never_resubmits_completed_job(scope_vault, capsys) -> None:
    vault, _ = scope_vault
    meta = pipeline_paths(vault)["ocr"] / "SCOPE001" / "meta.json"
    meta.parent.mkdir(parents=True)
    meta.write_text(json.dumps({
        "zotero_key": "SCOPE001", "ocr_status": "queued", "ocr_job_id": "old-job",
        "submission_state": "submitted",
    }), encoding="utf8")
    argv = [
        "--vault", str(vault), "action", "run", "ocr.run",
        "--scope", "papers", "--key", "SCOPE001", "--confirm", "ocr.run", "--json",
    ]
    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        http.get("https://paddleocr.aistudio-app.com/api/v2/ocr/jobs/old-job",
                 json={"data": {"state": "done", "resultUrl": {"jsonUrl": "https://result.test/missing"}}})
        http.get("https://result.test/missing", status=404)
        assert main(argv) == 1
        assert main(argv) == 1
        assert not [call for call in http.calls if call.request.method == "POST"]
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    terminals = [event["result"] for event in events if event.get("event") in ("result", "error")]
    assert len(terminals) == 2
    assert all(result["error"]["code"] == "OCR_RESULT_INVALID" for result in terminals)
    assert all("result could not be retrieved" in result["error"]["message"] for result in terminals)
    state = json.loads(meta.read_text(encoding="utf8"))
    assert state["ocr_job_id"] == "old-job"
    assert state["ocr_status"] == "queued"
    assert state["error_stage"] == "result"


def test_partial_success_survives_blocked_batch(scope_vault, capsys) -> None:
    """SCOPE001 genuinely completes through provider done + fetch, then
    SCOPE002 hits a 401 rejection in the same run: the terminal stays
    blocked (never poll-timeout) and keeps the successful key."""
    import requests

    vault, pdfs = scope_vault
    submitted: list[str] = []

    def submit_or_done(request):
        if b"SCOPE001" in request.body:
            submitted.append("SCOPE001")
            return 202, {"Content-Type": "application/json"}, json.dumps({"data": {"jobId": "job-SCOPE001"}})
        raise requests.exceptions.HTTPError(
            "401 Client Error: Unauthorized",
            response=type("R", (), {"status_code": 401, "text": "invalid token"})(),
        )

    page = {
        "layoutParsingResults": [{
            "prunedResult": {
                "width": 600, "height": 800,
                "parsing_res_list": [
                    {"block_label": "doc_title", "block_content": "Scope one", "block_bbox": [0, 0, 100, 20], "block_order": 0},
                    {"block_label": "text", "block_content": "Body", "block_bbox": [0, 40, 100, 80], "block_order": 1},
                ],
            }
        }]
    }
    result_text = json.dumps({"result": page})

    with responses.RequestsMock(assert_all_requests_are_fired=False) as http:
        http.add_callback(
            responses.POST,
            "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
            callback=submit_or_done,
        )
        http.get(
            "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs/job-SCOPE001",
            json={"data": {"state": "done", "resultUrl": {"jsonUrl": "https://x/result-S1"}}},
        )
        http.get("https://x/result-S1", body=result_text)
        rc = main([
            "--vault", str(vault), "action", "run", "ocr.run",
            "--scope", "papers", "--key", "SCOPE001", "--key", "SCOPE002",
            "--confirm", "ocr.run", "--json",
        ])
    assert rc == 1
    assert submitted == ["SCOPE001"]
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    terminal = next(e for e in events if e.get("event") in ("result", "error", "cancelled"))
    result = terminal.get("result", {}) or {}
    assert (result.get("error", {}) or {}).get("code") == "OCR_UPLOAD_FAILED"
    data = result.get("data", {}) or {}
    assert "SCOPE002" in (data.get("blocked_keys", []) or [])
    # PFResult.successful_keys is chain-internal and never serialized
    # (core/result.py); the public settlement carries it as
    # data.successful_keys via settlement_payload.
    assert "SCOPE001" in (data.get("successful_keys", []) or [])
    assert (data.get("summary", {}) or {}).get("pending", 0) == 0
