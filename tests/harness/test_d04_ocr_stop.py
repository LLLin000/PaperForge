"""D04 — a running OCR batch stops cooperatively and says so.

The H version of this case exists because the same contract was once broken in
two places at once (human text on the machine stream, and a poll sleep longer
than the stop grace).  Every assertion here is a process- or file-level fact, so
the case needs no host.
"""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.harness

CASE_ID = "D04"
TITLE = "A running OCR batch stops cooperatively with a cancelled terminal"
HOST_SPEC_CASE = "stops a running OCR batch through the workspace Stop control"

TERMINALS = ("result", "error", "cancelled")
LIVE_STATES = ("pending", "queued", "running")


def test_stop_is_cooperative_and_the_terminal_is_honest(ocr_cli, vault, case, ocr_stub) -> None:
    stub = ocr_stub(mode="slow", pages=1)

    synced = ocr_cli.json("sync")
    case.check("sync exits 0", synced.returncode == 0, synced.tail())

    wired = ocr_cli.config_set("paddleocr_job_url", stub.url)
    case.check("canonical job url is writable", wired.returncode == 0, wired.tail())
    case.check(
        "the run resolves the canonical job url",
        ocr_cli.config_get("paddleocr_job_url") == stub.url,
        ocr_cli.config_get("paddleocr_job_url"),
    )
    ocr_cli.set_note_flag("FIXT0001", "do_ocr", True)

    run = ocr_cli.action_stream(
        "ocr.run",
        ("FIXT0001",),
        confirm="ocr.run",
        # Stop the run *while it is polling a live job*: wait until the provider
        # has swallowed the upload, then cut it.  The deadline covers a stream
        # that goes quiet after the submit.
        stop_on=lambda event: stub.counts.get("submit", 0) >= 1,
        stop_after_s=45,
        timeout_s=180,
    )

    case.check(
        "the provider was actually reached before the stop",
        stub.counts.get("submit", 0) >= 1,
        json.dumps(stub.counts),
    )
    case.check(
        "the stop was delivered inside the deadline",
        not run.expired,
        f"rc={run.returncode} killed={run.expired}",
    )
    case.check(
        "the stop returns the documented exit code",
        run.returncode == 130,
        f"rc={run.returncode} terminal={json.dumps(run.terminal or {})[:200]}",
    )
    terminals = [event for event in run.events if event.get("event") in TERMINALS]
    case.check(
        "exactly one terminal event is emitted",
        len(terminals) == 1,
        f"terminals={[event.get('event') for event in terminals]}",
    )
    case.check(
        "the terminal event is cancelled",
        (run.terminal or {}).get("event") == "cancelled",
        json.dumps(run.terminal or {})[:300],
    )

    meta = ocr_cli.ocr_meta("FIXT0001")
    status = str(meta.get("ocr_status", ""))
    case.check("the stopped paper is not marked done", status != "done", status or "<no meta>")
    case.check("the stopped paper keeps a live state", status in LIVE_STATES, status or "<no meta>")
    case.check(
        "no result was pulled after the stop",
        stub.counts.get("result", 0) == 0,
        json.dumps(stub.counts),
    )

    case.artifact("ocr-dir", vault / "System" / "PaperForge" / "ocr" / "FIXT0001")
