"""F03 — P acceptance: fail-closed without evidence, bound to the reviewed plan.

This case exists because probing the lane found it unreachable, in three layers:

1. ``_is_reparse_point`` read every *missing* path as a Windows junction, so
   acceptance refused with ACCEPT_PROPOSAL_PATH_UNSAFE before doing anything.
2. With no canonical reconciliation report it raised ``KeyError: 'proposals'``
   through the CLI (rc=1, empty stdout) instead of refusing with a reason.
3. The staged plan and the canonical report named the same proposal differently
   (``figure_proposal_2`` vs ``inventory_proposal:figure:2``), and no CLI command
   wrote the report at all, so the commit could never happen.

All three are fixed; the flow asserted here is the one a real vault now takes:
audit → stage → promote (which refreshes the report acceptance checks against) →
stage again → accept the reviewed plan by its exact hash.
"""

from __future__ import annotations

import json

import pytest

from .evidence import digest

pytestmark = pytest.mark.harness

CASE_ID = "F03"
TITLE = "P acceptance refuses without evidence and commits the reviewed plan"
HOST_SPEC_CASE = "stages render repairs in isolation and promotes the reviewed candidates"

PAPER = "TSTONE001"
WRONG_HASH = "0" * 64


def _stage(render_cli) -> dict:
    staged = render_cli.json("render", "reconcile", PAPER)
    payload = staged.payload if isinstance(staged.payload, dict) else {}
    papers = payload.get("papers") or []
    details = (papers[0].get("p_details") or []) if papers else []
    if not details:
        return {}
    proposal = details[0]
    plan_path = proposal.get("final_plan")
    if plan_path:
        try:
            from pathlib import Path

            proposal["plan_proposal_id"] = json.loads(
                Path(str(plan_path)).read_text(encoding="utf-8")
            ).get("proposal_id")
        except (OSError, json.JSONDecodeError):
            pass
    return proposal


def test_acceptance_needs_evidence_and_binds_the_reviewed_plan(render_cli, render_vault, case) -> None:
    ocr = render_vault / "System" / "PaperForge" / "ocr" / PAPER
    inventory = ocr / "structure" / "figure_inventory.json"
    report = ocr / "render" / "reconciliation.proposals.json"
    inventory_before = digest(inventory)

    audited = render_cli.json("render", "audit", PAPER)
    case.check("the audit runs", audited.returncode == 0, audited.tail())

    # ── 1. no evidence → structured refusal, nothing written
    proposal = _stage(render_cli)
    case.check("a P proposal is staged", bool(proposal), json.dumps(proposal)[:200])
    if not proposal:
        return
    label = str(proposal.get("label", ""))
    case.check("the fixture ships no canonical report yet", not report.is_file(), str(report))

    no_evidence = render_cli.json(
        "render", "accept-proposal", PAPER, label, "--plan-hash", str(proposal.get("final_plan_hash", "")), expect=None
    )
    refusal = no_evidence.payload if isinstance(no_evidence.payload, dict) else {}
    case.check(
        "acceptance without a reconciliation report refuses with a reason",
        refusal.get("reason") == "reconciliation_report_unavailable",
        f"rc={no_evidence.returncode} stdout={no_evidence.stdout[-160:]!r} stderr={no_evidence.stderr[-160:]!r}",
    )
    case.check(
        "the refusal is a payload, not a traceback",
        "Traceback" not in no_evidence.stderr,
        no_evidence.stderr[-200:],
    )
    case.check(
        "the refused acceptance wrote nothing",
        digest(inventory) == inventory_before,
        "canonical inventory changed",
    )

    # ── 2. the R promotion produces the evidence acceptance checks against
    promoted = render_cli.json("render", "promote-r", PAPER, "figure_a1")
    promotion = promoted.payload if isinstance(promoted.payload, dict) else {}
    case.check("the R promotion commits", promotion.get("committed") is True, json.dumps(promotion)[:300])
    case.check(
        "the promotion refreshed the canonical reconciliation report",
        promotion.get("reconciliation_refresh") == "written" and report.is_file(),
        f"refresh={promotion.get('reconciliation_refresh')} exists={report.is_file()}",
    )

    # ── 3. the reviewed plan is what commits
    proposal = _stage(render_cli)
    label = str(proposal.get("label", ""))
    plan_hash = str(proposal.get("final_plan_hash", ""))
    canonical_id = f"figure_{int(label):03d}" if label.isdigit() else ""
    asset = ocr / "assets" / "figures" / f"{canonical_id}.jpg"
    markdown = ocr / "render" / "figures" / f"{canonical_id}.md"
    case.check(
        "the canonical destination does not exist before acceptance",
        canonical_id != "" and not asset.exists() and not markdown.exists(),
        f"{asset.name}={asset.exists()} {markdown.name}={markdown.exists()}",
    )
    case.check(
        "the staged plan is listed in the canonical report by the same id",
        any(
            str(item.get("proposal_id") or "") == _plan_proposal_id(proposal)
            for item in (json.loads(report.read_text(encoding="utf-8")).get("proposals") or [])
        )
        if report.is_file()
        else False,
        f"plan={_plan_proposal_id(proposal)!r}",
    )

    inventory_before_accept = digest(inventory)
    wrong = render_cli.json(
        "render", "accept-proposal", PAPER, label, "--plan-hash", WRONG_HASH, expect=None
    )
    wrong_payload = wrong.payload if isinstance(wrong.payload, dict) else {}
    case.check(
        "an unreviewed plan hash is refused",
        wrong_payload.get("reason") in ("STALE_REVIEWED_PLAN", "STALE_PROPOSAL"),
        json.dumps(wrong_payload)[:200],
    )
    case.check(
        "a refused acceptance wrote nothing",
        digest(inventory) == inventory_before_accept,
        "canonical inventory changed on a refused acceptance",
    )

    accepted = render_cli.json(
        "render", "accept-proposal", PAPER, label, "--plan-hash", plan_hash, expect=None
    )
    acceptance = accepted.payload if isinstance(accepted.payload, dict) else {}
    case.check(
        "the reviewed plan is accepted",
        acceptance.get("ok") is True,
        f"rc={accepted.returncode} {json.dumps(acceptance)[:300]} {accepted.stderr[-160:]}",
    )
    case.check(
        "acceptance reports the canonical object it created",
        str(acceptance.get("canonical_id") or "") == canonical_id,
        str(acceptance.get("canonical_id")),
    )

    rows = json.loads(inventory.read_text(encoding="utf-8")).get("matched_figures", [])
    row = next((item for item in rows if item.get("figure_id") == canonical_id), None)
    case.check("the proposal became a canonical object", row is not None, f"ids={[item.get('figure_id') for item in rows]}")
    case.check(
        "the canonical row binds the reviewed plan hash",
        (row or {}).get("accepted_from", {}).get("final_plan_hash") == plan_hash,
        json.dumps((row or {}).get("accepted_from"))[:200],
    )
    case.check(
        "the accepted artifacts exist",
        asset.is_file() and markdown.is_file(),
        f"{asset.name}={asset.is_file()} {markdown.name}={markdown.is_file()}",
    )

    after = render_cli.json("render", "audit", PAPER)
    case.check("the audit still runs after acceptance", after.returncode == 0, after.tail())

    case.artifact("inventory", inventory)
    case.artifact("canonical-assets", ocr / "assets")
    case.artifact("reconciliation-report", report)


def _plan_proposal_id(proposal: dict) -> str:
    return str(proposal.get("plan_proposal_id") or "")
