"""F03 — P acceptance: fail-closed without evidence, and currently unreachable.

Probing this lane found three layered defects in the only path that may add a
reviewed canonical object:

1. ``_is_reparse_point`` read every *missing* path as a Windows junction, so
   acceptance refused with ACCEPT_PROPOSAL_PATH_UNSAFE before doing anything.
   Fixed in promote_r.py.
2. With no canonical reconciliation report, acceptance raised ``KeyError:
   'proposals'`` straight through the CLI (rc=1, empty stdout).  Fixed in
   accept_proposal.py - it now answers ``reconciliation_report_unavailable``.
3. The proposal-identity mismatch that keeps the commit unreachable:

       staged final-plan.json : proposal_id = "figure_proposal_2"
       canonical report       : proposal_id = "inventory_proposal:figure:2"

   and nothing in the CLI writes the canonical report at all: ``render
   reconcile`` stages into tmp, R promotion copies the report only if staging has
   one (it does not), and ``write_reconciliation_report`` has no callers.

So this case asserts what is real (the refusal contract) and records the lane as
BLOCKED rather than VERIFIED - an unreachable capability is not evidence, and the
index has to say so.  The acceptance-commit half belongs here once an owner
decides which producer owns the proposal identity and who writes the report.
"""

from __future__ import annotations

import json

import pytest

from .evidence import digest

pytestmark = pytest.mark.harness

CASE_ID = "F03"
TITLE = "P acceptance refuses without evidence (commit unreachable)"
HOST_SPEC_CASE = "stages render repairs in isolation and promotes the reviewed candidates"

PAPER = "TSTONE001"
BLOCKER = (
    "P acceptance cannot commit: the staged final-plan proposal_id "
    "('figure_proposal_2') never matches the canonical report's "
    "('inventory_proposal:figure:2'), and no CLI command writes "
    "render/reconciliation.proposals.json."
)


def test_acceptance_without_evidence_refuses_structured(render_cli, render_vault, case) -> None:
    ocr = render_vault / "System" / "PaperForge" / "ocr" / PAPER
    inventory = ocr / "structure" / "figure_inventory.json"
    report = ocr / "render" / "reconciliation.proposals.json"
    inventory_before = digest(inventory)

    case.check("the fixture ships no reconciliation report", not report.is_file(), str(report))

    staged = render_cli.json("render", "reconcile", PAPER)
    payload = staged.payload if isinstance(staged.payload, dict) else {}
    papers = payload.get("papers") or []
    details = (papers[0].get("p_details") or []) if papers else []
    case.check("a P proposal is staged", bool(details), json.dumps(payload)[:300])
    if not details:
        return
    proposal = details[0]
    label = str(proposal.get("label", ""))
    plan_hash = str(proposal.get("final_plan_hash", ""))
    case.check(
        "the proposal has a label and a reviewed plan hash",
        bool(label) and len(plan_hash) == 64,
        json.dumps(proposal)[:200],
    )

    refused = render_cli.json(
        "render",
        "accept-proposal",
        PAPER,
        label,
        "--plan-hash",
        plan_hash,
        expect=None,
    )
    refusal = refused.payload if isinstance(refused.payload, dict) else {}
    case.check(
        "acceptance without a reconciliation report refuses with a reason",
        refusal.get("reason") == "reconciliation_report_unavailable",
        f"rc={refused.returncode} stdout={refused.stdout[-160:]!r} stderr={refused.stderr[-160:]!r}",
    )
    case.check(
        "the refusal is a payload, not a traceback",
        "Traceback" not in refused.stderr,
        refused.stderr[-200:],
    )
    case.check(
        "the refused acceptance wrote nothing",
        digest(inventory) == inventory_before,
        "canonical inventory changed",
    )

    # The commit half needs the two producers to agree on a proposal identity and
    # on who writes the canonical report; until then this case is not verified.
    case.blocked(BLOCKER)
    case.artifact("inventory", inventory)
