"""D06 — derived OCR artifacts rebuild locally, with zero provider traffic.

The oracle is the stub's own request ledger: a rebuild that talks to the
provider (or re-uploads the PDF) fails the case, which is exactly what the H
case asserts from the UI.  Host-agnostic: nothing here involves a view.
"""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.harness

CASE_ID = "D06"
TITLE = "Derived OCR artifacts rebuild locally without provider traffic"
HOST_SPEC_CASE = "rebuilds derived OCR artifacts locally without provider traffic"

TERMINALS = ("result", "error", "cancelled")


def test_rebuild_derived_is_local(ocr_cli, vault, case, ocr_stub) -> None:
    stub = ocr_stub(mode="success", pages=1)

    ocr_cli.json("sync")
    wired = ocr_cli.config_set("paddleocr_job_url", stub.url)
    case.check("canonical job url is writable", wired.returncode == 0, wired.tail())
    ocr_cli.set_note_flag("FIXT0001", "do_ocr", True)

    first = ocr_cli.action_stream("ocr.run", ("FIXT0001",), confirm="ocr.run", timeout_s=300)
    terminal = first.terminal or {}
    case.check(
        "the first OCR run settles with a result terminal",
        terminal.get("event") == "result",
        json.dumps(terminal)[:300],
    )
    case.check(
        "the provider served a result",
        stub.counts.get("result", 0) >= 1,
        json.dumps(stub.counts),
    )

    meta = ocr_cli.ocr_meta("FIXT0001")
    case.check(
        "a settled paper is done",
        str(meta.get("ocr_status", "")) == "done",
        str(meta.get("ocr_status", "<no meta>")),
    )

    ocr_dir = vault / "System" / "PaperForge" / "ocr" / "FIXT0001"
    case.artifact("ocr-artifacts", ocr_dir)

    stub.reset_counts()
    rebuilt = ocr_cli.action_stream("ocr.rebuild_derived", ("FIXT0001",), timeout_s=180)
    case.check(
        "rebuild settles with a result terminal",
        (rebuilt.terminal or {}).get("event") == "result",
        json.dumps(rebuilt.terminal or {})[:300],
    )
    case.check("rebuild exits 0", rebuilt.returncode == 0, f"rc={rebuilt.returncode}")
    case.check(
        "rebuild made no provider request of any kind",
        not stub.counts,
        json.dumps(stub.counts),
    )
    case.check(
        "rebuild kept the paper done",
        str(ocr_cli.ocr_meta("FIXT0001").get("ocr_status", "")) == "done",
        str(ocr_cli.ocr_meta("FIXT0001").get("ocr_status", "")),
    )
    case.artifact("ocr-artifacts-after-rebuild", ocr_dir)
