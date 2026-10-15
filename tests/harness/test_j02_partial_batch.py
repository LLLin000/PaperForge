"""J02 — a two-paper OCR batch is per-paper: one settles, one fails, none bleeds.

Ported from the H case that drives the workspace table.  The subject is the
per-paper settlement contract (a failed provider job must not mark its sibling,
and must not touch a paper outside the requested scope), which the CLI states
exactly as well as the UI does — without Obsidian, WebDriver or a wheel build.
"""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.harness

CASE_ID = "J02"
TITLE = "Two-paper OCR batch: one settles, one fails, a bystander is untouched"
HOST_SPEC_CASE = "runs a two-paper OCR batch with a rejected confirm, one success and one failure"

HEALTHY = "FIXT0001"
FAILING = "FIXT0002"
BYSTANDER = "FIXT0003"
TERMINALS = ("result", "error", "cancelled")


def test_partial_batch_settles_per_paper(ocr_cli, vault, case, ocr_stub) -> None:
    stub = ocr_stub(mode="success", pages=1, fail_keys=(FAILING,))

    ocr_cli.json("sync")
    wired = ocr_cli.config_set("paddleocr_job_url", stub.url)
    case.check("canonical job url is writable", wired.returncode == 0, wired.tail())
    for key in (HEALTHY, FAILING):
        ocr_cli.set_note_flag(key, "do_ocr", True)

    bystander_dir = vault / "System" / "PaperForge" / "ocr" / BYSTANDER

    run = ocr_cli.action_stream("ocr.run", (HEALTHY, FAILING), confirm="ocr.run", timeout_s=300)
    terminal = run.terminal or {}
    case.check(
        "the batch ends with exactly one terminal event",
        len([event for event in run.events if event.get("event") in TERMINALS]) == 1,
        json.dumps(terminal)[:300],
    )
    case.check(
        "a partially failed batch does not exit 130 (that is a user stop)",
        run.returncode != 130,
        f"rc={run.returncode}",
    )

    healthy_meta = ocr_cli.ocr_meta(HEALTHY)
    failing_meta = ocr_cli.ocr_meta(FAILING)
    case.check(
        "the serviced paper is done",
        str(healthy_meta.get("ocr_status", "")) == "done",
        json.dumps(healthy_meta)[:300],
    )
    case.check(
        "the rejected paper is not done",
        str(failing_meta.get("ocr_status", "")) != "done",
        json.dumps(failing_meta)[:300],
    )
    case.check(
        "the failure carries a diagnosis",
        bool(failing_meta.get("error") or failing_meta.get("error_stage")),
        json.dumps(failing_meta)[:300],
    )
    case.check(
        "the failure did not consume its sibling's result",
        stub.counts.get("result", 0) >= 1,
        json.dumps(stub.counts),
    )
    case.check(
        "the paper outside the requested scope was never touched",
        not bystander_dir.exists(),
        str(bystander_dir),
    )

    listed = ocr_cli.run("ocr", "list", "--json", expect=0)
    if isinstance(listed.payload, list):
        rows = listed.payload
    elif isinstance(listed.data, list):
        rows = listed.data
    elif isinstance(listed.data, dict):
        rows = listed.data.get("rows") or listed.data.get("papers") or []
    else:
        rows = []
    by_key = {
        str(row.get("key") or row.get("zotero_key")): str(row.get("status") or row.get("ocr_status"))
        for row in rows
        if isinstance(row, dict)
    }
    case.check(
        "the maintenance table agrees with the metas",
        by_key.get(HEALTHY) == "done" and by_key.get(FAILING, "") != "done",
        json.dumps(by_key)[:400],
    )
    case.check(
        "the untargeted paper is absent from the scoped table",
        BYSTANDER not in by_key,
        json.dumps(sorted(by_key))[:300],
    )

    case.artifact("ocr-dir-healthy", vault / "System" / "PaperForge" / "ocr" / HEALTHY)
