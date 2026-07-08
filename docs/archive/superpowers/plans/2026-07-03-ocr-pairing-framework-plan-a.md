# OCR Pairing Framework Plan A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract a generic OCR pairing framework from the current figure vnext implementation and migrate figure pairing onto it with no intended behavior change.

**Architecture:** Keep the external seam unchanged: `build_figure_inventory(...)` continues to return the same inventory contract and `ocr_rebuild.py` / OCR post-processing continue calling it the same way. Extract only the generic pairing mechanics into `ocr_pairing_*` modules, keep figure facts/hypotheses/assembly in figure-domain modules, and do not implement table vnext in this plan.

**Tech Stack:** Python 3.x, pytest, OCR worker modules under `paperforge/worker/`

## Global Constraints

- This plan is **Plan A only**.
- Do **not** implement table vnext in this plan.
- Do **not** change table heuristics in this plan.
- Do **not** redesign OCR roles, layout, zones, or document structure.
- Treat figure migration as a **no-behavior-change refactor**.
- Preserve the external contract of `build_figure_inventory(...)` and `build_figure_inventory_vnext(...)`.
- Preserve current pass order inside figure vnext.
- In Plan A, extract **pass orchestration only** into `ocr_pairing_framework.py`; do **not** claim this plan centralizes proposal arbitration.
- Keep passes using existing `OwnershipLedger` and state accept methods where they already do; do **not** introduce new direct ownership bypasses in Plan A.
- If compatibility shims are needed for old `ocr_figure_vnext_types.py` / `ocr_figure_vnext_state.py`, make them explicit and temporary.

---

## File Map

- `paperforge/worker/ocr_figures.py` — figure entrypoints and vnext orchestration
- `paperforge/worker/ocr_figure_vnext_types.py` — current generic pairing types to extract
- `paperforge/worker/ocr_figure_vnext_state.py` — current ledger/state to extract
- `paperforge/worker/ocr_figure_vnext_corpus.py` — current figure corpus/index, target of domain migration
- `paperforge/worker/ocr_figure_vnext_passes.py` — primary figure passes
- `paperforge/worker/ocr_figure_vnext_sidecar_pass.py` — figure sidecar pass
- `paperforge/worker/ocr_figure_vnext_locator_pass.py` — figure locator pass
- `paperforge/worker/ocr_figure_vnext_group_seq_pass.py` — figure group-sequential pass
- `paperforge/worker/ocr_figure_vnext_composite_pass.py` — figure composite pass
- `paperforge/worker/ocr_figure_vnext_classic_seq_pass.py` — figure classic sequential / unresolved-cluster passes
- `paperforge/worker/ocr_figure_vnext_bundle_pass.py` — figure legend bundle pass
- `paperforge/worker/ocr_figure_vnext_accounting_pass.py` — final figure accounting pass
- `paperforge/worker/ocr_rebuild.py` — rebuild caller that must remain contract-compatible
- `tests/test_ocr_figures.py` — main figure regression and unit coverage
- `tests/test_ocr_rebuild.py` — rebuild smoke coverage if needed for compatibility proof

Target new files:

- `paperforge/worker/ocr_pairing_types.py`
- `paperforge/worker/ocr_pairing_state.py`
- `paperforge/worker/ocr_pairing_framework.py`
- `paperforge/worker/ocr_figure_domain.py`
- `tests/test_ocr_pairing_framework.py`

---

### Task 1: Establish the no-behavior-change baseline

**Files:**
- Modify: `tests/test_ocr_figures.py`
- Create: `tests/test_ocr_pairing_framework.py`
- Optional Create: `scripts/dev/compare_figure_inventory_vnext_baseline.py`

**Interfaces:**
- Consumes: `build_figure_inventory(structured_blocks, page_width=1200, page_pdf_lines_by_page=None) -> dict[str, Any]`
- Produces:
  - `test_build_figure_inventory_delegates_to_vnext()`
  - `test_vnext_types_module_is_currently_generic_surface()`
  - `test_vnext_state_module_is_currently_generic_surface()`
  - optional baseline helper: `compare_vnext_inventory_baseline(...) -> int`

- [ ] **Step 1: Write the failing baseline tests**

Add to `tests/test_ocr_figures.py`:

```python
def test_build_figure_inventory_delegates_to_vnext(monkeypatch):
    from paperforge.worker import ocr_figures

    called = {}

    def fake_vnext(structured_blocks, page_width=1200, page_pdf_lines_by_page=None):
        called["args"] = (structured_blocks, page_width, page_pdf_lines_by_page)
        return {"pipeline_mode": "vnext", "matched_figures": []}

    monkeypatch.setattr(ocr_figures, "build_figure_inventory_vnext", fake_vnext)

    blocks = [{"block_id": "b1", "page": 1, "role": "body_text", "text": "x"}]
    result = ocr_figures.build_figure_inventory(blocks, page_width=777, page_pdf_lines_by_page={1: []})

    assert result["pipeline_mode"] == "vnext"
    assert called["args"] == (blocks, 777, {1: []})
```

Add to `tests/test_ocr_pairing_framework.py`:

```python
def test_vnext_types_module_is_currently_generic_surface():
    from paperforge.worker.ocr_figure_vnext_types import ClaimProposal, PassReport, ResourceRef

    assert ResourceRef.__name__ == "ResourceRef"
    assert ClaimProposal.__name__ == "ClaimProposal"
    assert PassReport.__name__ == "PassReport"


def test_vnext_state_module_is_currently_generic_surface():
    from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger

    state = FigurePipelineState(corpus=None, candidate_index=None, ledger=OwnershipLedger())

    assert state.matches == []
    assert state.reservations == []
    assert state.unresolved == []
```

- [ ] **Step 2: Run tests to verify the baseline is real**

Run:

```bash
python -m pytest \
  tests/test_ocr_figures.py::test_build_figure_inventory_delegates_to_vnext \
  tests/test_ocr_pairing_framework.py::test_vnext_types_module_is_currently_generic_surface \
  tests/test_ocr_pairing_framework.py::test_vnext_state_module_is_currently_generic_surface -q
```

Expected: PASS. If any test fails, stop and fix the baseline before extraction.

- [ ] **Step 3: Add a representative output-baseline smoke helper**

Create `scripts/dev/compare_figure_inventory_vnext_baseline.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from paperforge.worker.ocr_figures import build_figure_inventory


def compare_vnext_inventory_baseline(fixture_root: Path) -> dict[str, object]:
    structured_path = fixture_root / "structure" / "blocks.structured.jsonl"
    blocks = [json.loads(line) for line in structured_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    inventory = build_figure_inventory(blocks)
    return {
        "pipeline_mode": inventory.get("pipeline_mode"),
        "matched_ids": [m.get("figure_id") for m in inventory.get("matched_figures", [])],
        "match_count": len(inventory.get("matched_figures", [])),
    }
```

Do not overbuild this script. It exists only to capture a pre-extraction baseline on representative fixtures.

- [ ] **Step 4: Run the baseline helper on one representative real-paper fixture**

Run:

```bash
python -c "from pathlib import Path; from scripts.dev.compare_figure_inventory_vnext_baseline import compare_vnext_inventory_baseline; print(compare_vnext_inventory_baseline(Path('tests/fixtures/ocr_real_papers/6QNRHRKX')))"
```

Expected: a small dict showing `pipeline_mode='vnext'` and stable figure IDs / count.

- [ ] **Step 5: Commit**

```bash
git add \
  tests/test_ocr_figures.py \
  tests/test_ocr_pairing_framework.py \
  scripts/dev/compare_figure_inventory_vnext_baseline.py
git commit -m "test(ocr): lock figure vnext extraction baseline"
```

---

### Task 2: Extract generic pairing types into `ocr_pairing_types.py`

**Files:**
- Create: `paperforge/worker/ocr_pairing_types.py`
- Modify: `paperforge/worker/ocr_figure_vnext_types.py`
- Modify: `tests/test_ocr_pairing_framework.py`

**Interfaces:**
- Consumes: current `ResourceRef`, `OwnershipConflict`, `ClaimProposal`, `PassReport`
- Produces:
  - `paperforge.worker.ocr_pairing_types.ResourceRef`
  - `paperforge.worker.ocr_pairing_types.OwnershipConflict`
  - `paperforge.worker.ocr_pairing_types.ClaimProposal`
  - `paperforge.worker.ocr_pairing_types.PassReport`
  - compatibility shim behavior in `ocr_figure_vnext_types.py`

- [ ] **Step 1: Write the failing extraction tests**

Add to `tests/test_ocr_pairing_framework.py`:

```python
def test_pairing_types_module_exports_generic_types():
    from paperforge.worker.ocr_pairing_types import ClaimProposal, PassReport, ResourceRef

    ref = ResourceRef(kind="legend", page=1, block_id="b1")
    proposal = ClaimProposal(
        pass_name="p",
        figure_no=1,
        claim_type="match",
        legends=[ref],
        assets=[],
        groups=[],
        confidence=0.9,
        evidence_rank=1,
        reason="test",
    )
    report = PassReport(pass_name="p")

    assert proposal.pass_name == "p"
    assert report.pass_name == "p"
    assert ref.page == 1


def test_figure_vnext_types_module_reexports_framework_types():
    from paperforge.worker.ocr_pairing_types import ResourceRef as FrameworkResourceRef
    from paperforge.worker.ocr_figure_vnext_types import ResourceRef as FigureModuleResourceRef

    assert FigureModuleResourceRef is FrameworkResourceRef


def test_resource_ref_rejects_page_agnostic_asset():
    import pytest

    from paperforge.worker.ocr_pairing_types import ResourceRef

    with pytest.raises(ValueError):
        ResourceRef(kind="asset", page=None, block_id="a1")


def test_resource_ref_normalizes_block_id_type():
    from paperforge.worker.ocr_pairing_types import ResourceRef

    assert ResourceRef(kind="asset", page=1, block_id=1) == ResourceRef(kind="asset", page=1, block_id="1")


def test_resource_ref_rejects_group_without_group_id():
    import pytest

    from paperforge.worker.ocr_pairing_types import ResourceRef

    with pytest.raises(ValueError):
        ResourceRef(kind="group", page=1, block_id=None)

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest \
  tests/test_ocr_pairing_framework.py::test_pairing_types_module_exports_generic_types \
  tests/test_ocr_pairing_framework.py::test_figure_vnext_types_module_reexports_framework_types \
  tests/test_ocr_pairing_framework.py::test_resource_ref_rejects_page_agnostic_asset \
  tests/test_ocr_pairing_framework.py::test_resource_ref_normalizes_block_id_type \
  tests/test_ocr_pairing_framework.py::test_resource_ref_rejects_group_without_group_id -q
```

Expected: FAIL because `ocr_pairing_types.py` does not exist yet.

- [ ] **Step 3: Write the minimal extraction**

Create `paperforge/worker/ocr_pairing_types.py` with the current dataclasses moved verbatim first:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ResourceRef:
    kind: Literal["legend", "asset", "group"]
    page: int | None
    block_id: str | None
    group_id: str | None = None
    figure_no: int | None = field(default=None, compare=False)
    origin: str | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if self.page is not None:
            object.__setattr__(self, "page", int(self.page))
        if self.block_id is not None:
            object.__setattr__(self, "block_id", str(self.block_id))
        if self.group_id is not None:
            object.__setattr__(self, "group_id", str(self.group_id))

        if self.kind == "asset" and (self.page is None or self.block_id is None):
            raise ValueError("asset ResourceRef requires page + block_id")
        if self.kind == "legend" and (self.page is None or self.block_id is None):
            raise ValueError("legend ResourceRef requires page + block_id")
        if self.kind == "group" and (self.page is None or self.group_id is None):
            raise ValueError("group ResourceRef requires page + group_id")


@dataclass(frozen=True)
class OwnershipConflict:
    resource: ResourceRef
    current_owner: ResourceRef | None
    attempted_owner: ResourceRef | None
    reason: str


@dataclass
class ClaimProposal:
    pass_name: str
    figure_no: int | None
    claim_type: Literal["match", "reserve", "block", "unresolved_cluster", "composite_parent"]
    legends: list[ResourceRef]
    assets: list[ResourceRef]
    groups: list[ResourceRef]
    confidence: float
    evidence_rank: int
    reason: str
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass
class PassReport:
    pass_name: str
    proposals: list[ClaimProposal] = field(default_factory=list)
    accepted: list[ClaimProposal] = field(default_factory=list)
    rejected: list[ClaimProposal] = field(default_factory=list)
    conflicts: list[OwnershipConflict] = field(default_factory=list)
    invariant_errors: list[str] = field(default_factory=list)
```

Then replace `paperforge/worker/ocr_figure_vnext_types.py` with a compatibility shim:

```python
from .ocr_pairing_types import ClaimProposal, OwnershipConflict, PassReport, ResourceRef

__all__ = ["ResourceRef", "OwnershipConflict", "ClaimProposal", "PassReport"]
```

Do not rename `figure_no` to `entity_no` in Plan A. That belongs to a later compatibility-tightening task only after figure migration is stable.

- [ ] **Step 4: Run tests to verify they pass**

Run the command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add \
  paperforge/worker/ocr_pairing_types.py \
  paperforge/worker/ocr_figure_vnext_types.py \
  tests/test_ocr_pairing_framework.py
git commit -m "refactor(ocr): extract generic pairing types"
```

---

### Task 3: Extract generic state and ledger into `ocr_pairing_state.py`

**Files:**
- Create: `paperforge/worker/ocr_pairing_state.py`
- Modify: `paperforge/worker/ocr_figure_vnext_state.py`
- Modify: `tests/test_ocr_pairing_framework.py`

**Interfaces:**
- Consumes: `ResourceRef`, `ClaimProposal`, `OwnershipConflict`
- Produces:
  - `paperforge.worker.ocr_pairing_state.OwnershipLedger`
  - `paperforge.worker.ocr_pairing_state.FigurePipelineState` (keep existing class name in Plan A for compatibility)
  - compatibility shim behavior in `ocr_figure_vnext_state.py`

- [ ] **Step 1: Write the failing ledger / reexport tests**

Add to `tests/test_ocr_pairing_framework.py`:

```python
def test_pairing_state_module_exports_ownership_ledger():
    from paperforge.worker.ocr_pairing_state import OwnershipLedger
    from paperforge.worker.ocr_pairing_types import ResourceRef

    ledger = OwnershipLedger()
    owner = ResourceRef(kind="legend", page=1, block_id="cap")
    asset = ResourceRef(kind="asset", page=1, block_id="asset")

    assert ledger.try_claim_assets([asset], owner=owner, reason="test") is None
    assert ledger.owner_of_asset(page=1, block_id="asset") == owner


def test_figure_vnext_state_module_reexports_framework_ledger():
    from paperforge.worker.ocr_pairing_state import OwnershipLedger as FrameworkLedger
    from paperforge.worker.ocr_figure_vnext_state import OwnershipLedger as FigureModuleLedger

    assert FigureModuleLedger is FrameworkLedger
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest \
  tests/test_ocr_pairing_framework.py::test_pairing_state_module_exports_ownership_ledger \
  tests/test_ocr_pairing_framework.py::test_figure_vnext_state_module_reexports_framework_ledger -q
```

Expected: FAIL because `ocr_pairing_state.py` does not exist yet.

- [ ] **Step 3: Write the minimal extraction**

Create `paperforge/worker/ocr_pairing_state.py` by moving the current `OwnershipLedger` and `FigurePipelineState` verbatim first, only changing imports:

```python
from __future__ import annotations

from dataclasses import dataclass, field

from .ocr_pairing_types import ClaimProposal, OwnershipConflict, ResourceRef


class OwnershipLedger:
    ...


@dataclass
class FigurePipelineState:
    corpus: object | None
    candidate_index: object | None
    ledger: OwnershipLedger
    matches: list[dict] = field(default_factory=list)
    unresolved: list[dict] = field(default_factory=list)
    hypotheses: list[dict] = field(default_factory=list)
    diagnostics: list[dict] = field(default_factory=list)
    reservations: list[dict] = field(default_factory=list)
    completeness: dict = field(default_factory=dict)

    def accept_match(self, proposal: ClaimProposal, match_record: dict) -> None:
        ...

    def accept_reservation(self, proposal: ClaimProposal) -> None:
        ...
```

Then replace `paperforge/worker/ocr_figure_vnext_state.py` with a compatibility shim:

```python
from .ocr_pairing_state import FigurePipelineState, OwnershipLedger

__all__ = ["OwnershipLedger", "FigurePipelineState"]
```

Do not rename `FigurePipelineState` yet. That compatibility cleanup belongs after the framework extraction is proven stable.

- [ ] **Step 4: Run tests to verify they pass**

Run the command from Step 2.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add \
  paperforge/worker/ocr_pairing_state.py \
  paperforge/worker/ocr_figure_vnext_state.py \
  tests/test_ocr_pairing_framework.py
git commit -m "refactor(ocr): extract generic pairing state and ledger"
```

---

### Task 4: Add `ocr_pairing_framework.py` and migrate figure orchestration imports

**Files:**
- Create: `paperforge/worker/ocr_pairing_framework.py`
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: all figure pass files under `paperforge/worker/ocr_figure_vnext_*.py`
- Modify: `tests/test_ocr_figures.py`
- Modify: `tests/test_ocr_pairing_framework.py`

**Interfaces:**
- Consumes: `FigurePipelineState`, `PassReport`, existing figure pass classes
- Produces:
  - `run_pairing_passes(state, pass_classes) -> list[PassReport]`
  - figure pass imports now sourced from `ocr_pairing_types` / `ocr_pairing_state`
  - no change to per-pass arbitration behavior in Plan A
- [ ] **Step 1: Write the failing runner test**

Add to `tests/test_ocr_pairing_framework.py`:

```python
def test_run_pairing_passes_executes_in_declared_order():
    from paperforge.worker.ocr_pairing_framework import run_pairing_passes
    from paperforge.worker.ocr_pairing_state import FigurePipelineState, OwnershipLedger
    from paperforge.worker.ocr_pairing_types import PassReport

    seen = []

    class FirstPass:
        name = "first"
        def run(self, state):
            seen.append(self.name)
            return PassReport(pass_name=self.name)

    class SecondPass:
        name = "second"
        def run(self, state):
            seen.append(self.name)
            return PassReport(pass_name=self.name)

    state = FigurePipelineState(corpus=None, candidate_index=None, ledger=OwnershipLedger())
    reports = run_pairing_passes(state, [FirstPass, SecondPass])

    assert seen == ["first", "second"]
    assert [r.pass_name for r in reports] == ["first", "second"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_ocr_pairing_framework.py::test_run_pairing_passes_executes_in_declared_order -q
```

Expected: FAIL because `ocr_pairing_framework.py` does not exist yet.

- [ ] **Step 3: Write the minimal framework runner and migrate imports**

Create `paperforge/worker/ocr_pairing_framework.py`:

```python
from __future__ import annotations

from collections.abc import Sequence


def run_pairing_passes(state, pass_classes: Sequence[type]) -> list:
    reports = []
    for pass_cls in pass_classes:
        reports.append(pass_cls().run(state))
    return reports
```

In `paperforge/worker/ocr_figures.py`, replace the local orchestration loop inside `build_figure_inventory_vnext(...)`:

```python
reports = []
for pass_cls in (
    PrimarySamePagePass,
    CompositeParentPass,
    SidecarPass,
    LocatorBridgePass,
    CrossPageReservationPass,
    CrossPageSettlementPass,
    LegendBundlePass,
    GroupSequentialPass,
    ClassicSequentialPass,
    UnresolvedClusterConsolidation,
    FinalAccountingPass,
):
    reports.append(pass_cls().run(state))
```

with:

```python
from .ocr_pairing_framework import run_pairing_passes

reports = run_pairing_passes(
    state,
    [
        PrimarySamePagePass,
        CompositeParentPass,
        SidecarPass,
        LocatorBridgePass,
        CrossPageReservationPass,
        CrossPageSettlementPass,
        LegendBundlePass,
        GroupSequentialPass,
        ClassicSequentialPass,
        UnresolvedClusterConsolidation,
        FinalAccountingPass,
    ],
)
```

Then update all figure pass files to import from the extracted modules, for example:

```python
from .ocr_pairing_types import ClaimProposal, PassReport, ResourceRef
from .ocr_pairing_state import FigurePipelineState
```

Keep pass logic unchanged in Plan A. This task only extracts **orchestration**, not framework-owned arbitration. Do not refactor passes to centralize proposal commit logic in this plan.

- [ ] **Step 4: Run focused tests to verify the runner is wired correctly**

Run:

```bash
python -m pytest \
  tests/test_ocr_pairing_framework.py::test_run_pairing_passes_executes_in_declared_order \
  tests/test_ocr_figures.py::test_build_figure_inventory_delegates_to_vnext -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add \
  paperforge/worker/ocr_pairing_framework.py \
  paperforge/worker/ocr_figures.py \
  paperforge/worker/ocr_figure_vnext_*.py \
  tests/test_ocr_pairing_framework.py \
  tests/test_ocr_figures.py
git commit -m "refactor(ocr): add pairing pass runner for figure vnext"
```

---

### Task 5: Move figure facts and hypotheses into `ocr_figure_domain.py`

**Files:**
- Create: `paperforge/worker/ocr_figure_domain.py`
- Modify: `paperforge/worker/ocr_figure_vnext_corpus.py`
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `tests/test_ocr_pairing_framework.py`
- Modify: `tests/test_ocr_figures.py`

**Interfaces:**
- Consumes: current `FigureCorpus`, `FigureCandidateIndex`
- Produces:
  - `paperforge.worker.ocr_figure_domain.FigureCorpus`
  - `paperforge.worker.ocr_figure_domain.FigureCandidateIndex`
  - compatibility shim behavior in `ocr_figure_vnext_corpus.py`

- [ ] **Step 1: Write the failing domain-module reexport tests**

Add to `tests/test_ocr_pairing_framework.py`:

```python
def test_figure_domain_module_exports_corpus_and_candidate_index():
    from paperforge.worker.ocr_figure_domain import FigureCandidateIndex, FigureCorpus

    assert FigureCorpus.__name__ == "FigureCorpus"
    assert FigureCandidateIndex.__name__ == "FigureCandidateIndex"


def test_legacy_vnext_corpus_module_reexports_figure_domain_types():
    from paperforge.worker.ocr_figure_domain import FigureCorpus as DomainFigureCorpus
    from paperforge.worker.ocr_figure_vnext_corpus import FigureCorpus as LegacyModuleFigureCorpus

    assert LegacyModuleFigureCorpus is DomainFigureCorpus
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest \
  tests/test_ocr_pairing_framework.py::test_figure_domain_module_exports_corpus_and_candidate_index \
  tests/test_ocr_pairing_framework.py::test_legacy_vnext_corpus_module_reexports_figure_domain_types -q
```

Expected: FAIL because `ocr_figure_domain.py` does not exist yet.

- [ ] **Step 3: Write the minimal domain extraction**

Create `paperforge/worker/ocr_figure_domain.py` by moving `FigureCorpus` and `FigureCandidateIndex` from `ocr_figure_vnext_corpus.py` first.

If the moved code needs helpers from `ocr_figures.py`, keep those imports lazy inside methods or classmethods. Preferred pattern:

```python
class FigureCandidateIndex:
    @classmethod
    def from_corpus(cls, corpus):
        from . import ocr_figures
        ...
```

Do **not** add a new top-level import cycle between `ocr_figures.py` and `ocr_figure_domain.py`.

Then replace `paperforge/worker/ocr_figure_vnext_corpus.py` with:

```python
from .ocr_figure_domain import FigureCandidateIndex, FigureCorpus

__all__ = ["FigureCorpus", "FigureCandidateIndex"]
```

In `paperforge/worker/ocr_figures.py`, change:

```python
from .ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus
```

to:

```python
from .ocr_figure_domain import FigureCandidateIndex, FigureCorpus
```

Do not edit corpus/index behavior in this task beyond lazy-import adjustments needed to avoid circular imports.

- [ ] **Step 4: Run focused tests and one representative figure regression**

Run:

```bash
python -m pytest \
  tests/test_ocr_pairing_framework.py::test_figure_domain_module_exports_corpus_and_candidate_index \
  tests/test_ocr_pairing_framework.py::test_legacy_vnext_corpus_module_reexports_figure_domain_types \
  tests/test_ocr_figures.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add \
  paperforge/worker/ocr_figure_domain.py \
  paperforge/worker/ocr_figure_vnext_corpus.py \
  paperforge/worker/ocr_figures.py \
  tests/test_ocr_pairing_framework.py \
  tests/test_ocr_figures.py
git commit -m "refactor(ocr): move figure corpus and candidate index into domain module"
```

---

### Task 6: Prove rebuild compatibility and close Plan A

**Files:**
- Modify: `tests/test_ocr_rebuild.py`
- Modify: `tests/test_ocr_pairing_framework.py`
- Optional Modify: `paperforge/worker/ocr_rebuild.py` only if imports need compatibility cleanup

**Interfaces:**
- Consumes: extracted framework modules, unchanged `build_figure_inventory(...)`
- Produces:
  - rebuild-level compatibility test
  - final baseline comparison results proving no intended figure behavior change

- [ ] **Step 1: Write the rebuild compatibility test against the real rebuild path**

Add to `tests/test_ocr_rebuild.py`:

```python
def test_run_derived_rebuild_for_keys_still_uses_public_build_figure_inventory(tmp_path: Path, monkeypatch) -> None:
    import json

    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    key = "TESTKEY1"
    paper_root = tmp_path / "System" / "PaperForge" / "ocr" / key
    (paper_root / "canonical").mkdir(parents=True)
    (paper_root / "raw").mkdir(parents=True)
    (paper_root / "structure").mkdir(parents=True)

    (paper_root / "canonical" / "blocks.raw.jsonl").write_text(
        json.dumps(
            {
                "paper_id": key,
                "page": 1,
                "block_id": "p1_b1",
                "raw_label": "text",
                "raw_order": 0,
                "text": "Example text",
                "bbox": [10, 10, 100, 40],
                "page_width": 600,
                "page_height": 800,
            }
        )
        + "\\n",
        encoding="utf-8",
    )
    (paper_root / "raw" / "source_metadata.json").write_text(
        json.dumps({"title": "Example Title"}),
        encoding="utf-8",
    )
    (paper_root / "meta.json").write_text(json.dumps({"source_pdf": ""}), encoding="utf-8")

    called = {"count": 0}

    def fake_build_figure_inventory(structured_blocks, page_width=1200, page_pdf_lines_by_page=None):
        called["count"] += 1
        return {
            "pipeline_mode": "vnext",
            "matched_figures": [],
            "ambiguous_figures": [],
            "unmatched_legends": [],
            "unmatched_assets": [],
            "unresolved_clusters": [],
            "held_figures": [],
            "rejected_legends": [],
            "page_ledger": {},
            "residual_ledger": {},
            "local_pairing_hypotheses": [],
            "pass_reports": [],
            "completeness": {"total_numbered_legends": 0, "accounted_for": 0, "details": []},
        }

    monkeypatch.setattr("paperforge.worker.ocr_figures.build_figure_inventory", fake_build_figure_inventory)
    monkeypatch.setattr("paperforge.worker.ocr_blocks.write_structured_blocks_jsonl", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "paperforge.worker.ocr_metadata.extract_frontmatter_candidates_from_blocks",
        lambda structured: {"title": "Example Title", "authors_text": None, "doi_candidates": []},
    )

    result = run_derived_rebuild_for_keys(tmp_path, [key])

    assert result["rebuild_count"] == 1
    assert called["count"] > 0
```

This test must call `run_derived_rebuild_for_keys(...)` for real. Do not replace it with a hand-call to the fake function.

- [ ] **Step 2: Run the focused rebuild and framework tests**

Run:

```bash
python -m pytest \
  tests/test_ocr_pairing_framework.py \
  tests/test_ocr_rebuild.py::test_run_derived_rebuild_for_keys_still_uses_public_build_figure_inventory -q
```

Expected: PASS.

- [ ] **Step 3: Run representative figure regression proof**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -q
python -c "from pathlib import Path; from scripts.dev.compare_figure_inventory_vnext_baseline import compare_vnext_inventory_baseline; print(compare_vnext_inventory_baseline(Path('tests/fixtures/ocr_real_papers/6QNRHRKX')))"
```

Expected:

- all figure tests PASS
- baseline helper output remains unchanged from Task 1

- [ ] **Step 4: Remove any accidental table changes from the diff**

Run:

```bash
git diff --name-only -- paperforge/worker/ocr_tables.py tests/test_ocr_tables.py
```

Expected: no output. If there is output, revert it before committing.

- [ ] **Step 5: Commit**

```bash
git add \
  tests/test_ocr_rebuild.py \
  tests/test_ocr_pairing_framework.py \
  scripts/dev/compare_figure_inventory_vnext_baseline.py \
  paperforge/worker/ocr_pairing_types.py \
  paperforge/worker/ocr_pairing_state.py \
  paperforge/worker/ocr_pairing_framework.py \
  paperforge/worker/ocr_figure_domain.py \
  paperforge/worker/ocr_figure_vnext_types.py \
  paperforge/worker/ocr_figure_vnext_state.py \
  paperforge/worker/ocr_figure_vnext_corpus.py \
  paperforge/worker/ocr_figure_vnext_*.py \
  paperforge/worker/ocr_figures.py
git commit -m "refactor(ocr): migrate figure vnext onto pairing framework"
```

---

## Self-Review Checklist

- Spec coverage:
  - Preflight baseline gate -> Task 1
  - Framework type extraction -> Task 2
  - Framework state/ledger extraction -> Task 3
  - Framework runner / arbitration seam -> Task 4
  - Figure-domain migration -> Task 5
  - Rebuild compatibility and no-behavior proof -> Task 6
  - Table vnext intentionally excluded -> enforced in Global Constraints and Task 6 Step 4
- Placeholder scan:
  - No `TODO` / `TBD` / “similar to Task N” placeholders remain.
  - One note in Task 6 explicitly tells the implementer to reuse existing rebuild fixture helpers in-file instead of inventing new infrastructure; this is intentional scoping guidance, not a missing design detail.
- Type consistency:
  - Plan A keeps `figure_no` and `FigurePipelineState` names for compatibility.
  - Framework extraction is import-path-first; neutral renames like `entity_no` and `anchor` are deferred until after migration stability is proven.

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-03-ocr-pairing-framework-plan-a.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
