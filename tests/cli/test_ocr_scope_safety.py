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
