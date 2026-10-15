"""D05 — a paper flagged for redo is re-extracted through a fresh provider job.

Ported from the H case that clicks the workspace's re-extract control.  Its oracle
is the provider ledger: the redo must submit **one** fresh job, not re-settle the
existing one, and the paper must come out settled.

Two things learned while porting, both worth knowing before writing another OCR
case:

* the redo path resolves a paper's note by scanning for its ``zotero_key`` and
  requires exactly eight alphanumerics (``_find_notes_by_key`` in
  ``worker/ocr.py``).  That is the real Zotero key shape; the *render* fixture's
  ``TSTONE001`` is synthetic and nine characters long, so the redo transaction
  counts it as failed - by design, not by defect.  This case therefore runs on the
  standard vault, whose keys are eight characters.
* the fixture ships no OCR run at all on that vault, and the worker skips an
  up-to-date paper, so the first run is a real one before the redo can differ from
  it.
"""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.harness

CASE_ID = "D05"
TITLE = "A flagged paper is re-extracted through a fresh provider job"
HOST_SPEC_CASE = "re-extracts a flagged paper through the workspace redo control"

PAPER = "FIXT0001"


def test_redo_submits_a_fresh_job(ocr_cli, case, ocr_stub) -> None:
    cli = ocr_cli
    stub = ocr_stub(mode="success", pages=1)
    wired = cli.config_set("paddleocr_job_url", stub.url)
    case.check("the canonical job url is writable", wired.returncode == 0, wired.tail())
    cli.json("sync")
    cli.set_note_flag(PAPER, "do_ocr", True)

    first = cli.action_stream("ocr.run", (PAPER,), confirm="ocr.run", timeout_s=300)
    case.check(
        "the first run settles",
        (first.terminal or {}).get("event") == "result",
        json.dumps(first.terminal or {})[:300],
    )
    case.check("the first run submitted one job", stub.counts.get("submit") == 1, json.dumps(stub.counts))
    settled = json.loads(json.dumps(cli.ocr_meta(PAPER)))
    case.check(
        "the paper is done after the first run",
        str(settled.get("ocr_status")) == "done",
        str(settled.get("ocr_status")),
    )

    # The flag the workspace row shows (the note owns it).
    cli.set_note_flag(PAPER, "ocr_redo", True)

    stub.reset_counts()
    # `--json` belongs to the parent `ocr` parser, not to the redo subparser.
    redone = cli.run("ocr", "--json", "redo", PAPER, expect=0)
    case.check("redo exits 0", redone.returncode == 0, redone.tail())
    case.check(
        "redo submitted exactly one fresh job",
        stub.counts.get("submit") == 1,
        json.dumps(stub.counts),
    )

    after = cli.ocr_meta(PAPER)
    case.check(
        "the paper is settled again",
        str(after.get("ocr_status")) == "done",
        str(after.get("ocr_status")),
    )
    case.check(
        "the redo produced a new provider job, not the old settlement",
        str(after.get("ocr_job_id") or "") != str(settled.get("ocr_job_id") or ""),
        f"before={settled.get('ocr_job_id')} after={after.get('ocr_job_id')}",
    )
    case.check(
        "the redo re-published the paper's artifacts",
        (cli.vault / "System" / "PaperForge" / "ocr" / PAPER / "fulltext.md").is_file(),
        "fulltext.md missing after redo",
    )

    case.artifact("ocr-dir", cli.vault / "System" / "PaperForge" / "ocr" / PAPER)
