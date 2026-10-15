"""F02 — render staging is isolated, and the reviewed R plan is what promotes.

Host-agnostic: the subject is the reconcile/promote contract (staging writes
nothing canonical, the promoted object is the reviewed one, a second promote is
a no-op), which the H case can only reach through the dashboard's quality
drawer.  Its archived evidence once read status=FAILED while the case passed;
here the oracle is the canonical inventory and the artifacts themselves.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .evidence import digest, tree_digest

pytestmark = pytest.mark.harness

CASE_ID = "F02"
TITLE = "Render repair staging is isolated and the reviewed R plan promotes"
HOST_SPEC_CASE = "stages render repairs in isolation and promotes the reviewed candidates"

PAPER = "TSTONE001"


def test_staging_writes_nothing_and_promotion_commits(render_cli, render_vault, case) -> None:
    ocr = render_vault / "System" / "PaperForge" / "ocr" / PAPER
    inventory = ocr / "structure" / "figure_inventory.json"
    report = ocr / "render" / "render.consistency.json"

    audit = render_cli.json("render", "audit", PAPER)
    case.check("audit exits 0", audit.returncode == 0, audit.tail())
    case.check("the audit report is written", report.is_file(), str(report))
    case.artifact("report-before", report)

    inventory_before = digest(inventory)
    assets_before = tree_digest(ocr / "assets")
    figures_before = tree_digest(ocr / "render" / "figures")

    staged = render_cli.json("render", "reconcile", PAPER)
    case.check("reconcile exits 0", staged.returncode == 0, staged.tail())
    payload = staged.payload if isinstance(staged.payload, dict) else {}
    summary = payload.get("summary") or {}
    case.check(
        "staging declares no production write",
        summary.get("production_write") is False,
        json.dumps(summary)[:300],
    )

    papers = payload.get("papers") or []
    case.check("the fixture paper staged", len(papers) == 1, json.dumps(payload)[:200])
    paper_row = papers[0] if papers else {}
    details = paper_row.get("r_details") or []
    case.check(
        "an R candidate is staged and marked staged",
        bool(details) and details[0].get("staged") is True,
        json.dumps(details)[:300],
    )
    object_id = str(details[0].get("object_id", "")) if details else ""
    staging_root = Path(str(paper_row.get("staging_root", "")))
    case.check(
        "staging lives outside the vault",
        bool(str(staging_root)) and str(render_vault) not in str(staging_root),
        str(staging_root),
    )
    case.check(
        "staging wrote nothing canonical",
        digest(inventory) == inventory_before
        and tree_digest(ocr / "assets") == assets_before
        and tree_digest(ocr / "render" / "figures") == figures_before,
        "canonical bytes changed during a staging-only run",
    )

    promoted = render_cli.json("render", "promote-r", PAPER, object_id)
    case.check("promote-r exits 0", promoted.returncode == 0, promoted.tail())
    promotion = promoted.payload if isinstance(promoted.payload, dict) else {}
    case.check(
        "the promotion committed",
        promotion.get("committed") is True,
        json.dumps(promotion)[:400],
    )
    case.check(
        "the promoted object's issue cleared",
        ((promotion.get("audit_1") or {}).get("target_delta") or {})
        .get(object_id, {})
        .get("after")
        == [],
        json.dumps(promotion.get("audit_1"))[:300],
    )
    asset = ocr / "assets" / "figures" / f"{object_id}.jpg"
    markdown = ocr / "render" / "figures" / f"{object_id}.md"
    case.check(
        "the canonical artifacts exist after promotion",
        asset.is_file() and markdown.is_file(),
        f"{asset.name}={asset.is_file()} {markdown.name}={markdown.is_file()}",
    )
    case.check(
        "the audit report was refreshed by the promotion",
        promotion.get("report_refresh") == "written",
        str(promotion.get("report_refresh")),
    )

    assets_after = tree_digest(ocr / "assets")
    figures_after = tree_digest(ocr / "render" / "figures")
    inventory_after = digest(inventory)

    again = render_cli.json("render", "promote-r", PAPER, object_id)
    repeat = again.payload if isinstance(again.payload, dict) else {}
    case.check(
        "a second promote of the same object changes nothing",
        tree_digest(ocr / "assets") == assets_after
        and tree_digest(ocr / "render" / "figures") == figures_after
        and digest(inventory) == inventory_after,
        json.dumps(repeat.get("target_delta"))[:300],
    )

    case.artifact("canonical-assets", ocr / "assets")
    case.artifact("inventory", inventory)
