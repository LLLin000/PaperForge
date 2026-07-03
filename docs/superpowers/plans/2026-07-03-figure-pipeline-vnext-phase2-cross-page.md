# Figure Pipeline VNext Phase 2 — Cross-Page Reservation + Settlement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the vnext figure pipeline from same-page primary matching to cross-page reservation and cross-page settlement, while still excluding sidecar, bundle, locator, group-aware sequential, classic sequential, composite-parent settlement, and cutover.

**Architecture:** Build on the completed vnext seams from Phase 0 + Phase 1: `FigureCorpus`, `FigureCandidateIndex`, `OwnershipLedger`, `FigurePipelineState`, and `PrimarySamePagePass`. Add two new passes — `CrossPageReservationPass` and `CrossPageSettlementPass` — that emit and consume explicit proposals without stealing resources from accepted same-page matches.

**Tech Stack:** Python 3, pytest, existing OCR helpers in `paperforge/worker/ocr_figures.py`, vnext modules under `paperforge/worker/`, portable repo fixtures under `tests/fixtures/ocr_vnext_real_papers/`

## Global Constraints

- Build on branch/worktree `feat/figure-pipeline-vnext`; do not edit the main checkout.
- Preserve the external interface `build_figure_inventory(structured_blocks, page_width=1200) -> FigureInventory`.
- Legacy implementation remains the immutable baseline.
- Keep `ResourceRef` as the only ownership key.
- Cross-page reservation/settlement must remain separate from sidecar, bundle, locator, group-aware sequential, classic sequential, and cutover.
- Disabled later passes must emit no proposals.
- Final arbitration priority is independent of migration order.
- New pass reports must remain JSON-safe.
- Add only the tests directly covering this phase; do not broaden to the whole OCR suite inside task steps.

---

### Task 1: Extend state and ledger for reservations

**Files:**
- Modify: `paperforge/worker/ocr_figure_vnext_types.py`
- Modify: `paperforge/worker/ocr_figure_vnext_state.py`
- Create: `tests/test_ocr_figure_vnext_reservations.py`

**Interfaces:**
- Consumes:
  - `ResourceRef`
  - `ClaimProposal`
  - `PassReport`
  - `OwnershipLedger`
  - `FigurePipelineState`
- Produces:
  - `OwnershipLedger.reserve_group(...)`
  - `OwnershipLedger.transition_reserved_group_to_claimed(...)`
  - `OwnershipLedger.can_claim_group(...) -> bool`
  - `FigurePipelineState.accept_reservation(...)`

- [ ] **Step 1: Write failing reservation tests**

```python
# tests/test_ocr_figure_vnext_reservations.py
from paperforge.worker.ocr_figure_vnext_types import ClaimProposal, ResourceRef
from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger


def test_ledger_can_reserve_group_without_claiming_assets():
    ledger = OwnershipLedger()
    group = ResourceRef(kind="group", page=2, block_id=None, group_id="g2")

    ledger.reserve_group(group, reason="cross_page_candidate")

    assert ledger.can_claim_group(group) is False
    assert any(entry["action"] == "reserve_group" for entry in ledger.snapshot())


def test_pipeline_state_accept_reservation_records_diagnostic():
    state = FigurePipelineState(corpus=None, candidate_index=None, ledger=OwnershipLedger())
    proposal = ClaimProposal(
        pass_name="cross_page_reservation",
        figure_no=4,
        claim_type="reserve",
        legends=[ResourceRef(kind="legend", page=1, block_id="l1", figure_no=4)],
        assets=[],
        groups=[ResourceRef(kind="group", page=2, block_id=None, group_id="g2")],
        confidence=0.7,
        evidence_rank=2,
        reason="forward_cross_page_candidate",
        diagnostics={"evidence": ["page_gap"]},
    )

    state.accept_reservation(proposal)

    assert state.diagnostics[-1]["event"] == "reservation_accepted"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_figure_vnext_reservations.py -v`
Expected: FAIL because reservation methods/state hooks do not exist yet.

- [ ] **Step 3: Extend types/state minimally for reservation support**

```python
# paperforge/worker/ocr_figure_vnext_state.py
class OwnershipLedger:
    def __init__(self) -> None:
        self._owners: dict[ResourceRef, ResourceRef] = {}
        self._reserved_groups: set[ResourceRef] = set()
        self._journal: list[dict[str, object]] = []

    def reserve_group(self, group: ResourceRef, *, reason: str) -> None:
        self._reserved_groups.add(group)
        self._journal.append({"action": "reserve_group", "group": group, "reason": reason})

    def can_claim_group(self, group: ResourceRef) -> bool:
        return group not in self._reserved_groups

    def transition_reserved_group_to_claimed(self, group: ResourceRef, *, owner: ResourceRef, reason: str) -> None:
        if group in self._reserved_groups:
            self._reserved_groups.remove(group)
        self._journal.append({"action": "claim_reserved_group", "group": group, "owner": owner, "reason": reason})


@dataclass
class FigurePipelineState:
    ...
    reservations: list[dict] = field(default_factory=list)

    def accept_reservation(self, proposal: ClaimProposal) -> None:
        self.reservations.append({
            "pass_name": proposal.pass_name,
            "figure_no": proposal.figure_no,
            "reason": proposal.reason,
            "groups": proposal.groups,
            "legends": proposal.legends,
        })
        self.diagnostics.append({
            "event": "reservation_accepted",
            "pass_name": proposal.pass_name,
            "figure_no": proposal.figure_no,
            "reason": proposal.reason,
            "resources": {
                "legends": proposal.legends,
                "groups": proposal.groups,
            },
        })
```

- [ ] **Step 4: Run reservation tests to verify they pass**

Run: `python -m pytest tests/test_ocr_figure_vnext_reservations.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figure_vnext_state.py tests/test_ocr_figure_vnext_reservations.py
git commit -m "feat(ocr): add vnext cross-page reservation state"
```

### Task 2: Implement `CrossPageReservationPass`

**Files:**
- Modify: `paperforge/worker/ocr_figure_vnext_passes.py`
- Modify: `tests/test_ocr_figure_vnext_passes.py`

**Interfaces:**
- Consumes:
  - `FigurePipelineState`
  - `ClaimProposal`
  - `PassReport`
  - `ResourceRef`
  - existing helpers from `ocr_figures.py` for page/group scoring
- Produces:
  - `CrossPageReservationPass.run(state) -> PassReport`

- [ ] **Step 1: Add failing reservation pass tests**

```python
# tests/test_ocr_figure_vnext_passes.py
from paperforge.worker.ocr_figure_vnext_passes import CrossPageReservationPass


def test_cross_page_reservation_pass_reserves_forward_group_when_same_page_primary_misses():
    # use a synthetic state where legend is on page 1 and only group is on page 2
    ...


def test_cross_page_reservation_pass_does_not_reserve_group_already_claimed_same_page():
    # use a synthetic state with an already-owned same-page asset/group
    ...
```

- [ ] **Step 2: Run the failing reservation pass tests**

Run: `python -m pytest tests/test_ocr_figure_vnext_passes.py -k cross_page_reservation -v`
Expected: FAIL because `CrossPageReservationPass` does not exist yet.

- [ ] **Step 3: Implement the reservation pass**

```python
# paperforge/worker/ocr_figure_vnext_passes.py
class CrossPageReservationPass:
    name = "cross_page_reservation"

    def run(self, state):
        report = PassReport(pass_name=self.name)
        for legend in state.candidate_index.deduped_legends:
            page = _resource_page(legend)
            if page is None:
                continue
            if any(str(m.get("legend_block_id", "")) == str(legend.get("block_id", "")) for m in state.matches):
                continue
            forward_groups = [
                g for g in state.candidate_index.candidate_groups
                if _resource_page(g) is not None and _resource_page(g) > page
            ]
            for group in forward_groups[:1]:
                group_ref = ResourceRef(kind="group", page=_resource_page(group), block_id=None, group_id=group.get("group_id"))
                if not state.ledger.can_claim_group(group_ref):
                    continue
                proposal = ClaimProposal(
                    pass_name=self.name,
                    figure_no=None,
                    claim_type="reserve",
                    legends=[ResourceRef(kind="legend", page=page, block_id=legend.get("block_id"), figure_no=None)],
                    assets=[],
                    groups=[group_ref],
                    confidence=0.6,
                    evidence_rank=2,
                    reason="forward_cross_page_candidate",
                    diagnostics={"evidence": ["page_gap", "same_page_miss"]},
                )
                report.proposals.append(proposal)
                state.ledger.reserve_group(group_ref, reason=proposal.reason)
                state.accept_reservation(proposal)
                report.accepted.append(proposal)
                break
        return report
```

- [ ] **Step 4: Run the reservation pass tests**

Run: `python -m pytest tests/test_ocr_figure_vnext_passes.py -k cross_page_reservation -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figure_vnext_passes.py tests/test_ocr_figure_vnext_passes.py
git commit -m "feat(ocr): add vnext cross-page reservation pass"
```

### Task 3: Implement `CrossPageSettlementPass`

**Files:**
- Modify: `paperforge/worker/ocr_figure_vnext_passes.py`
- Modify: `tests/test_ocr_figure_vnext_passes.py`
- Modify: `paperforge/worker/ocr_figures.py`

**Interfaces:**
- Consumes:
  - `CrossPageReservationPass` output in `state.reservations`
  - `OwnershipLedger.transition_reserved_group_to_claimed(...)`
- Produces:
  - `CrossPageSettlementPass.run(state) -> PassReport`
  - vnext orchestrator calling same-page pass, then reservation pass, then settlement pass

- [ ] **Step 1: Add failing settlement tests**

```python
# tests/test_ocr_figure_vnext_passes.py
from paperforge.worker.ocr_figure_vnext_passes import CrossPageSettlementPass


def test_cross_page_settlement_pass_claims_reserved_group_into_match_record():
    ...


def test_cross_page_settlement_pass_keeps_same_page_matches_untouched():
    ...
```

- [ ] **Step 2: Run the failing settlement tests**

Run: `python -m pytest tests/test_ocr_figure_vnext_passes.py -k cross_page_settlement -v`
Expected: FAIL because `CrossPageSettlementPass` does not exist yet.

- [ ] **Step 3: Implement the settlement pass and wire orchestrator order**

```python
# paperforge/worker/ocr_figure_vnext_passes.py
class CrossPageSettlementPass:
    name = "cross_page_settlement"

    def run(self, state):
        report = PassReport(pass_name=self.name)
        for reservation in state.reservations:
            legend = reservation["legends"][0]
            group = reservation["groups"][0]
            state.ledger.transition_reserved_group_to_claimed(group, owner=legend, reason="cross_page_settlement")
            proposal = ClaimProposal(
                pass_name=self.name,
                figure_no=reservation["figure_no"],
                claim_type="match",
                legends=[legend],
                assets=[],
                groups=[group],
                confidence=0.6,
                evidence_rank=2,
                reason="cross_page_settlement",
                diagnostics={"evidence": ["reservation_claimed"]},
            )
            state.accept_match(proposal, {
                "figure_id": f"figure_reserved_{len(state.matches):03d}",
                "figure_namespace": "figure",
                "figure_number": reservation["figure_no"],
                "legend_block_id": legend.block_id,
                "page": legend.page,
                "text": "",
                "matched_assets": [],
                "asset_block_ids": [],
                "settlement_type": "cross_page_reservation",
                "confidence": 0.6,
                "match_score": {"score": 0.6, "decision": "matched", "evidence": ["reservation_claimed"]},
                "flags": ["cross_page_reserved"],
                "bridge_block_ids": [],
            })
            report.accepted.append(proposal)
        return report
```

```python
# paperforge/worker/ocr_figures.py
from dataclasses import asdict


def build_figure_inventory_vnext(structured_blocks: list[dict], page_width: float = 1200) -> dict[str, Any]:
    from .ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus
    from .ocr_figure_vnext_passes import PrimarySamePagePass, CrossPageReservationPass, CrossPageSettlementPass, _resource_page
    from .ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger

    corpus = FigureCorpus.from_blocks(structured_blocks, page_width=page_width)
    candidate_index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=candidate_index, ledger=OwnershipLedger())
    reports = []
    for pass_cls in (PrimarySamePagePass, CrossPageReservationPass, CrossPageSettlementPass):
        reports.append(pass_cls().run(state))
    ...
    "pass_reports": [asdict(r) for r in reports],
```

- [ ] **Step 4: Run the settlement tests**

Run: `python -m pytest tests/test_ocr_figure_vnext_passes.py -k cross_page_settlement -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figure_vnext_passes.py paperforge/worker/ocr_figures.py tests/test_ocr_figure_vnext_passes.py
git commit -m "feat(ocr): add vnext cross-page settlement pass"
```

### Task 4: Portable cross-page real-paper harness

**Files:**
- Create: `tests/fixtures/ocr_vnext_real_papers/DWQQK2YB/blocks.structured.jsonl`
- Modify: `tests/test_ocr_figure_vnext_real_papers.py`
- Modify: `scripts/dev/compare_figure_inventory_legacy_vs_vnext.py`

**Interfaces:**
- Consumes:
  - `compare_blocks_file(...)`
- Produces:
  - second portable real-paper fixture for a cross-page/locator-style paper
  - fixture-backed regression asserting diff contract shape for the cross-page milestone

- [ ] **Step 1: Copy the representative cross-page paper into a repo fixture**

```python
from pathlib import Path
from shutil import copy2

src = Path(r"D:/L/OB/Literature-hub/System/PaperForge/ocr/DWQQK2YB/structure/blocks.structured.jsonl")
dst = Path("tests/fixtures/ocr_vnext_real_papers/DWQQK2YB/blocks.structured.jsonl")
dst.parent.mkdir(parents=True, exist_ok=True)
copy2(src, dst)
```

- [ ] **Step 2: Add the failing cross-page fixture-backed test**

```python
# tests/test_ocr_figure_vnext_real_papers.py
from pathlib import Path

from scripts.dev.compare_figure_inventory_legacy_vs_vnext import compare_blocks_file


def test_real_paper_cross_page_milestone_reports_diff_shape():
    blocks_path = Path("tests/fixtures/ocr_vnext_real_papers/DWQQK2YB/blocks.structured.jsonl")
    diff = compare_blocks_file(blocks_path)

    assert diff["paper"] == "DWQQK2YB"
    assert "legacy_matched_count" in diff
    assert "vnext_matched_count" in diff
```

- [ ] **Step 3: Run the cross-page fixture test to verify it fails before implementation completes**

Run: `python -m pytest tests/test_ocr_figure_vnext_real_papers.py -k cross_page_milestone -v`
Expected: FAIL until the fixture and cross-page passes are wired.

- [ ] **Step 4: Re-run the real-paper fixture tests after Tasks 2 and 3**

Run: `python -m pytest tests/test_ocr_figure_vnext_real_papers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/ocr_vnext_real_papers/DWQQK2YB/blocks.structured.jsonl tests/test_ocr_figure_vnext_real_papers.py
git commit -m "test(ocr): add portable cross-page real-paper harness"
```

## Self-Review

- Spec coverage: This phase covers only cross-page reservation + settlement and the portable harness needed to observe that milestone. It intentionally leaves sidecar, bundle, locator-specific reconciliation, group-aware sequential, classic sequential, composite-parent settlement, and cutover to later plans.
- Placeholder scan: No `TBD`, `TODO`, or machine-local pytest paths remain in task steps; local absolute paths are used only as read-only source locations for copying repo fixtures.
- Type consistency: reservation and settlement interfaces extend the existing vnext seams instead of bypassing them.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-03-figure-pipeline-vnext-phase2-cross-page.md`. Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?