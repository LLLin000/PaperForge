# Figure Pipeline VNext Phase 0 + Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a clean legacy/vnext split for the figure pipeline, add the comparison harness and core vnext contracts, and ship a first working vnext slice that handles ownership-safe same-page primary matching without touching sidecar/bundle/locator logic.

**Architecture:** Keep `build_figure_inventory(...)` stable and legacy-backed while introducing `build_figure_inventory_vnext(...)` as a new orchestrator. Build vnext around four internal seams: immutable corpus facts, derived candidate index, ownership ledger, and pass reports/proposals. The first shippable slice ends at same-page primary matching plus diff tooling; all special fallbacks remain legacy-only.

**Tech Stack:** Python 3, pytest, existing OCR figure helpers in `paperforge/worker/ocr_figures.py`, dev scripts under `scripts/dev/`

## Global Constraints

- Legacy implementation is an immutable baseline. Do not retrofit `OwnershipLedger` into the legacy function.
- Phase 0 only performs mechanical extraction: `build_figure_inventory_legacy = old behavior`, `build_figure_inventory_vnext = new orchestrator shell`, `build_figure_inventory` keeps calling legacy until cutover.
- `ResourceRef` is the only valid ownership key; `block_id` alone is forbidden.
- Define `ClaimProposal` and `PassReport` schemas before implementing passes.
- Split facts and hypotheses: `FigureCorpus` stores immutable facts; `FigureCandidateIndex` stores derived candidates and hypotheses.
- Add a legacy-vnext comparison harness before implementing special fallbacks.
- Final arbitration priority is independent of migration order; disabled passes emit no proposals.
- Do not implement sidecar, bundle, locator, group-aware sequential, classic sequential, composite-parent settlement, or final cutover in this plan.
- Preserve the external interface `build_figure_inventory(structured_blocks, page_width=1200) -> FigureInventory`.

---

### Task 1: Mechanical legacy/vnext split and comparison harness

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Create: `scripts/dev/compare_figure_inventory_legacy_vs_vnext.py`
- Test: `tests/test_ocr_figures.py`

**Interfaces:**
- Consumes: existing `build_figure_inventory(structured_blocks: list[dict], page_width: float = 1200) -> dict[str, Any]`
- Produces:
  - `build_figure_inventory_legacy(structured_blocks: list[dict], page_width: float = 1200) -> dict[str, Any]`
  - `build_figure_inventory_vnext(structured_blocks: list[dict], page_width: float = 1200) -> dict[str, Any]`
  - `compare_inventories(legacy: dict[str, Any], vnext: dict[str, Any]) -> dict[str, Any]`

- [ ] **Step 1: Write the failing wrapper contract tests**

```python
# tests/test_ocr_figures.py

def test_build_figure_inventory_wrapper_stays_legacy_path(monkeypatch):
    from paperforge.worker import ocr_figures

    called = {"legacy": 0, "vnext": 0}

    def fake_legacy(blocks, page_width=1200):
        called["legacy"] += 1
        return {"source": "legacy"}

    def fake_vnext(blocks, page_width=1200):
        called["vnext"] += 1
        return {"source": "vnext"}

    monkeypatch.setattr(ocr_figures, "build_figure_inventory_legacy", fake_legacy)
    monkeypatch.setattr(ocr_figures, "build_figure_inventory_vnext", fake_vnext)

    result = ocr_figures.build_figure_inventory([], 1200)

    assert result == {"source": "legacy"}
    assert called == {"legacy": 1, "vnext": 0}


def test_vnext_entrypoint_is_callable_without_cutover():
    from paperforge.worker.ocr_figures import build_figure_inventory_vnext

    result = build_figure_inventory_vnext([], 1200)

    assert isinstance(result, dict)
    assert result.get("pipeline_mode") == "vnext"
    assert result.get("matched_figures") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_figures.py::test_build_figure_inventory_wrapper_stays_legacy_path tests/test_ocr_figures.py::test_vnext_entrypoint_is_callable_without_cutover -v`
Expected: FAIL because `build_figure_inventory_legacy` and `build_figure_inventory_vnext` do not both exist yet.

- [ ] **Step 3: Rename the current function and add the stable wrapper**

```python
# paperforge/worker/ocr_figures.py

def build_figure_inventory(structured_blocks: list[dict], page_width: float = 1200) -> dict[str, Any]:
    return build_figure_inventory_legacy(structured_blocks, page_width)


def build_figure_inventory_vnext(structured_blocks: list[dict], page_width: float = 1200) -> dict[str, Any]:
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
        "completeness": {
            "total_numbered_legends": 0,
            "accounted_for": 0,
            "details": [],
        },
    }


def build_figure_inventory_legacy(structured_blocks: list[dict], page_width: float = 1200) -> dict[str, Any]:
    # body is the exact former build_figure_inventory implementation, unchanged
    ...
```

- [ ] **Step 4: Add the comparison harness script**

```python
# scripts/dev/compare_figure_inventory_legacy_vs_vnext.py
from __future__ import annotations

import json
from pathlib import Path

from paperforge.worker.ocr_figures import (
    build_figure_inventory_legacy,
    build_figure_inventory_vnext,
)


def _figure_asset_ids(fig: dict[str, object]) -> list[str]:
    ids = {str(x) for x in fig.get("asset_block_ids", [])}
    ids.update(str(asset.get("block_id", "")) for asset in fig.get("matched_assets", []))
    return sorted(x for x in ids if x)


def compare_inventories(legacy: dict[str, object], vnext: dict[str, object]) -> dict[str, object]:
    return {
        "legacy_matched_count": len(legacy.get("matched_figures", [])),
        "vnext_matched_count": len(vnext.get("matched_figures", [])),
        "legacy_unresolved_count": len(legacy.get("unresolved_clusters", [])),
        "vnext_unresolved_count": len(vnext.get("unresolved_clusters", [])),
        "legacy_unmatched_legend_count": len(legacy.get("unmatched_legends", [])),
        "vnext_unmatched_legend_count": len(vnext.get("unmatched_legends", [])),
        "legacy_consumed_block_ids": sorted(
            {bid for fig in legacy.get("matched_figures", []) for bid in _figure_asset_ids(fig)}
        ),
        "vnext_consumed_block_ids": sorted(
            {bid for fig in vnext.get("matched_figures", []) for bid in _figure_asset_ids(fig)}
        ),
    }


def main(blocks_path: str) -> int:
    blocks = [json.loads(line) for line in Path(blocks_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    legacy = build_figure_inventory_legacy(blocks)
    vnext = build_figure_inventory_vnext(blocks)
    print(json.dumps(compare_inventories(legacy, vnext), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1]))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_figures.py::test_build_figure_inventory_wrapper_stays_legacy_path tests/test_ocr_figures.py::test_vnext_entrypoint_is_callable_without_cutover -v`
Expected: PASS

- [ ] **Step 6: Verify the wrapper is the only public call path**

Run: `python -c "import inspect; from paperforge.worker import ocr_figures; print(inspect.signature(ocr_figures.build_figure_inventory)); print(hasattr(ocr_figures, 'build_figure_inventory_legacy')); print(hasattr(ocr_figures, 'build_figure_inventory_vnext'))"`
Expected: the public wrapper still exists and both explicit internal entrypoints exist.

- [ ] **Step 7: Commit**

```bash
git add paperforge/worker/ocr_figures.py scripts/dev/compare_figure_inventory_legacy_vs_vnext.py tests/test_ocr_figures.py
git commit -m "refactor(ocr): split legacy and vnext figure entrypoints"
```

### Task 2: Add vnext core contracts and identity-safe ledger

**Files:**
- Create: `paperforge/worker/ocr_figure_vnext_types.py`
- Create: `paperforge/worker/ocr_figure_vnext_state.py`
- Test: `tests/test_ocr_figure_vnext_types.py`
- Test: `tests/test_ocr_figure_vnext_state.py`

**Interfaces:**
- Consumes: none
- Produces:
  - `ResourceRef`
  - `OwnershipConflict`
  - `ClaimProposal`
  - `PassReport`
  - `OwnershipLedger`
  - `FigurePipelineState.accept_match(...)`

- [ ] **Step 1: Write failing identity tests**

```python
# tests/test_ocr_figure_vnext_types.py
import pytest

from paperforge.worker.ocr_figure_vnext_types import ResourceRef


def test_resource_ref_rejects_page_agnostic_asset():
    with pytest.raises(ValueError):
        ResourceRef(kind="asset", page=None, block_id="42")


def test_resource_ref_normalizes_block_id_type():
    assert ResourceRef(kind="asset", page=1, block_id=42) == ResourceRef(kind="asset", page=1, block_id="42")


def test_resource_ref_rejects_group_without_group_id():
    with pytest.raises(ValueError):
        ResourceRef(kind="group", page=1, block_id=None)
```

```python
# tests/test_ocr_figure_vnext_state.py
from paperforge.worker.ocr_figure_vnext_types import ClaimProposal, ResourceRef
from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger


def test_ledger_rejects_double_ownership_for_same_asset_and_records_conflict():
    ledger = OwnershipLedger()
    asset = ResourceRef(kind="asset", page=3, block_id="42")
    legend_a = ResourceRef(kind="legend", page=3, block_id="77", figure_no=1)
    legend_b = ResourceRef(kind="legend", page=3, block_id="78", figure_no=2)

    ledger.claim_assets([asset], owner=legend_a, reason="same_page_primary")
    conflict = ledger.try_claim_assets([asset], owner=legend_b, reason="conflicting_match")

    assert conflict is not None
    assert conflict.resource == asset
    assert conflict.current_owner == legend_a
    assert any(entry["action"] == "conflict" for entry in ledger.snapshot())


def test_pipeline_state_accept_match_records_diagnostic():
    state = FigurePipelineState(corpus=None, candidate_index=None, ledger=OwnershipLedger())
    proposal = ClaimProposal(
        pass_name="primary_same_page",
        figure_no=1,
        claim_type="match",
        legends=[ResourceRef(kind="legend", page=1, block_id="c1", figure_no=1)],
        assets=[ResourceRef(kind="asset", page=1, block_id="a1")],
        groups=[],
        confidence=0.9,
        evidence_rank=1,
        reason="same_page_primary",
        diagnostics={"evidence": ["test"]},
    )

    state.accept_match(proposal, {"figure_id": "Figure 1"})

    assert state.matches == [{"figure_id": "Figure 1"}]
    assert state.diagnostics[-1]["event"] == "match_accepted"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_figure_vnext_types.py tests/test_ocr_figure_vnext_state.py -v`
Expected: FAIL because the new types/state modules do not exist.

- [ ] **Step 3: Define the core schemas**

```python
# paperforge/worker/ocr_figure_vnext_types.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ResourceRef:
    kind: Literal["legend", "asset", "group"]
    page: int | None
    block_id: str | None
    group_id: str | None = None
    figure_no: int | None = None
    origin: str | None = None

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

- [ ] **Step 4: Implement the ledger and minimal pipeline state**

```python
# paperforge/worker/ocr_figure_vnext_state.py
from __future__ import annotations

from dataclasses import dataclass, field

from .ocr_figure_vnext_types import ClaimProposal, OwnershipConflict, ResourceRef


class OwnershipLedger:
    def __init__(self) -> None:
        self._owners: dict[ResourceRef, ResourceRef] = {}
        self._journal: list[dict[str, object]] = []

    def claim_assets(self, assets: list[ResourceRef], *, owner: ResourceRef, reason: str) -> None:
        conflict = self.try_claim_assets(assets, owner=owner, reason=reason)
        if conflict is not None:
            raise ValueError(f"asset already owned: {conflict.resource}")

    def try_claim_assets(self, assets: list[ResourceRef], *, owner: ResourceRef, reason: str) -> OwnershipConflict | None:
        for asset in assets:
            current = self._owners.get(asset)
            if current is not None and current != owner:
                conflict = OwnershipConflict(resource=asset, current_owner=current, attempted_owner=owner, reason=reason)
                self._journal.append({
                    "action": "conflict",
                    "resource": asset,
                    "current_owner": current,
                    "attempted_owner": owner,
                    "reason": reason,
                })
                return conflict
        for asset in assets:
            self._owners[asset] = owner
            self._journal.append({"action": "claim", "resource": asset, "owner": owner, "reason": reason})
        return None

    def owner_of(self, resource: ResourceRef) -> ResourceRef | None:
        return self._owners.get(resource)

    def owner_of_asset(self, *, page: int, block_id: int | str) -> ResourceRef | None:
        return self.owner_of(ResourceRef(kind="asset", page=page, block_id=block_id))

    def snapshot(self) -> list[dict[str, object]]:
        return list(self._journal)


@dataclass
class FigurePipelineState:
    corpus: object | None
    candidate_index: object | None
    ledger: OwnershipLedger
    matches: list[dict] = field(default_factory=list)
    unresolved: list[dict] = field(default_factory=list)
    hypotheses: list[dict] = field(default_factory=list)
    diagnostics: list[dict] = field(default_factory=list)

    def accept_match(self, proposal: ClaimProposal, match_record: dict) -> None:
        self.matches.append(match_record)
        self.diagnostics.append({
            "event": "match_accepted",
            "pass_name": proposal.pass_name,
            "figure_no": proposal.figure_no,
            "reason": proposal.reason,
            "resources": {
                "legends": proposal.legends,
                "assets": proposal.assets,
                "groups": proposal.groups,
            },
        })
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_figure_vnext_types.py tests/test_ocr_figure_vnext_state.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_figure_vnext_types.py paperforge/worker/ocr_figure_vnext_state.py tests/test_ocr_figure_vnext_types.py tests/test_ocr_figure_vnext_state.py
git commit -m "feat(ocr): add vnext figure ownership contracts"
```

### Task 3: Build immutable corpus facts and derived candidate index

**Files:**
- Create: `paperforge/worker/ocr_figure_vnext_corpus.py`
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figure_vnext_corpus.py`
- Consumes:
  - `build_figure_inventory_legacy(...)`
  - existing helpers in `ocr_figures.py` such as `_is_formal_legend`, `_build_candidate_figure_groups_from_assets`
  - lazy import from `ocr_document` for `_build_page_layout_profiles`
- Produces:
  - `FigureCorpus.from_blocks(blocks: list[dict], page_width: float = 1200) -> FigureCorpus`
  - `FigureCandidateIndex.from_corpus(corpus: FigureCorpus) -> FigureCandidateIndex`

- [ ] **Step 1: Write failing corpus/index tests**

```python
# tests/test_ocr_figure_vnext_corpus.py
from paperforge.worker.ocr_figure_vnext_corpus import FigureCorpus, FigureCandidateIndex


def test_corpus_keeps_raw_facts_and_no_candidate_groups():
    blocks = [
        {"block_id": "1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption"},
        {"block_id": "2", "page": 1, "role": "figure_asset", "bbox": [0, 0, 10, 10]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    assert [b["block_id"] for b in corpus.raw_legends] == ["1"]
    assert [b["block_id"] for b in corpus.raw_assets] == ["2"]
    assert corpus.page_width == 1200


def test_candidate_index_holds_derived_hypotheses_not_raw_facts():
    blocks = [
        {"block_id": "1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption"},
        {"block_id": "2", "page": 1, "role": "figure_asset", "bbox": [0, 0, 10, 10]},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    assert len(index.formal_legends) == 1
    assert hasattr(index, "candidate_groups")
    assert corpus.raw_legends[0]["block_id"] == "1"
    assert index.bundle_source_legend_ids == set()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_figure_vnext_corpus.py -v`
Expected: FAIL because the corpus/index module does not exist.

- [ ] **Step 3: Implement `FigureCorpus` and `FigureCandidateIndex`**

```python
# paperforge/worker/ocr_figure_vnext_corpus.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FigureCorpus:
    blocks: list[dict]
    page_width: float
    raw_legends: list[dict] = field(default_factory=list)
    raw_assets: list[dict] = field(default_factory=list)
    locator_candidates: list[dict] = field(default_factory=list)
    page_layouts: dict[int, Any] = field(default_factory=dict)
    @classmethod
    def from_blocks(cls, blocks: list[dict], page_width: float = 1200) -> "FigureCorpus":
        from . import ocr_figures
        from .ocr_document import _build_page_layout_profiles

        raw_legends = [b for b in blocks if b.get("role") in {"figure_caption", "figure_caption_candidate"}]
        raw_assets = [b for b in blocks if b.get("role") in {"figure_asset", "media_asset"}]
        locator_candidates = [b for b in raw_legends if ocr_figures._is_previous_page_legend_locator(b)]
        return cls(
            blocks=list(blocks),
            page_width=page_width,
            raw_legends=raw_legends,
            raw_assets=raw_assets,
            locator_candidates=locator_candidates,
            page_layouts=_build_page_layout_profiles(blocks),
        )


@dataclass
class FigureCandidateIndex:
    formal_legends: list[dict]
    held_legends: list[dict]
    rejected_legends: list[dict]
    deduped_legends: list[dict]
    candidate_groups: list[dict]
    competing_caption_pages: set[int]
    sidecar_candidates: dict[int, list[dict]]
    bundle_source_legend_ids: set[str]
    locator_candidates: list[dict]

    @classmethod
    def from_corpus(cls, corpus: FigureCorpus) -> "FigureCandidateIndex":
        from . import ocr_figures

        formal_legends = [b for b in corpus.raw_legends if ocr_figures._is_formal_legend(str(b.get("text", "")), b, corpus.page_width)]
        rejected_legends = [b for b in corpus.raw_legends if b not in formal_legends]
        candidate_groups = ocr_figures._build_candidate_figure_groups_from_assets(
            corpus.raw_assets,
            formal_legends,
            corpus.blocks,
            page_width=corpus.page_width,
        )
        competing_caption_pages = {
            int(leg.get("page"))
            for leg in formal_legends
            if leg.get("page") is not None and ocr_figures._extract_figure_number(str(leg.get("text", ""))) is not None
        }
        return cls(
            formal_legends=formal_legends,
            held_legends=[],
            rejected_legends=rejected_legends,
            deduped_legends=formal_legends,
            candidate_groups=candidate_groups,
            competing_caption_pages=competing_caption_pages,
            sidecar_candidates={},
            bundle_source_legend_ids=set(),
            locator_candidates=corpus.locator_candidates,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_figure_vnext_corpus.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figure_vnext_corpus.py tests/test_ocr_figure_vnext_corpus.py
git commit -m "feat(ocr): add vnext figure corpus and candidate index"
```

- [ ] **Step 6: Manual review gate**

Reviewer checkpoint before Task 4:
- verify no circular import between `ocr_figures.py` and `ocr_figure_vnext_corpus.py`
- verify `bundle_source_legend_ids` remains empty in this milestone
- verify `FigureCorpus` stores facts only and `FigureCandidateIndex` stores hypotheses only
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_figure_vnext_corpus.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figure_vnext_corpus.py tests/test_ocr_figure_vnext_corpus.py
git commit -m "feat(ocr): add vnext figure corpus and candidate index"
```

### Task 4: Implement `PrimarySamePagePass` and wire vnext milestone

**Files:**
- Create: `paperforge/worker/ocr_figure_vnext_passes.py`
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `scripts/dev/compare_figure_inventory_legacy_vs_vnext.py`
- Test: `tests/test_ocr_figure_vnext_passes.py`
- Test: `tests/test_ocr_figure_vnext_compare.py`

**Interfaces:**
- Consumes:
  - `FigureCorpus`
  - `FigureCandidateIndex`
  - `OwnershipLedger`
  - existing helpers `_score_legend_to_group`, `_project_asset_record`, `_extract_figure_number`, `_extract_figure_namespace`, `_format_figure_id`
- Produces:
  - `PrimarySamePagePass.run(state: FigurePipelineState) -> PassReport`
  - `build_figure_inventory_vnext(...)` returning same-page primary matches only

**Execution guard:** Do not start Task 4 until Task 3 has been reviewed.

- [ ] **Step 1: Write failing same-page primary tests**

```python
# tests/test_ocr_figure_vnext_passes.py
from paperforge.worker.ocr_figure_vnext_corpus import FigureCorpus, FigureCandidateIndex
from paperforge.worker.ocr_figure_vnext_passes import PrimarySamePagePass
from paperforge.worker.ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger


def test_primary_same_page_pass_matches_single_safe_group():
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption", "bbox": [0, 100, 200, 150]},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())

    report = PrimarySamePagePass().run(state)

    assert len(report.accepted) == 1
    assert report.accepted[0].claim_type == "match"
    assert len(state.matches) == 1


def test_primary_same_page_pass_prefers_higher_score_when_two_legends_compete_for_one_asset(monkeypatch):
    blocks = [
        {"block_id": "c1", "page": 1, "role": "figure_caption", "text": "Figure 1. Caption", "bbox": [0, 100, 200, 150]},
        {"block_id": "c2", "page": 1, "role": "figure_caption", "text": "Figure 2. Caption", "bbox": [0, 160, 200, 210]},
        {"block_id": "a1", "page": 1, "role": "figure_asset", "bbox": [0, 0, 200, 90], "raw_label": "image"},
    ]
    corpus = FigureCorpus.from_blocks(blocks, page_width=1200)
    index = FigureCandidateIndex.from_corpus(corpus)
    if not index.candidate_groups:
        index.candidate_groups = [{\"group_id\": \"g1\", \"page\": 1, \"asset_block_ids\": [\"a1\"], \"media_blocks\": [{\"block_id\": \"a1\"}], \"group_type\": \"single_asset\", \"cluster_bbox\": [0, 0, 200, 90]}]

    scores = [{\"score\": 0.4, \"decision\": \"matched\", \"evidence\": [\"low\"]}, {\"score\": 0.9, \"decision\": \"matched\", \"evidence\": [\"high\"]}]

    def fake_score(*args, **kwargs):
        return scores.pop(0)

    monkeypatch.setattr(\"paperforge.worker.ocr_figures._score_legend_to_group\", fake_score)
    monkeypatch.setattr(\"paperforge.worker.ocr_figures.score_figure_caption\", lambda *a, **k: {\"score\": 0.9})

    state = FigurePipelineState(corpus=corpus, candidate_index=index, ledger=OwnershipLedger())
    report = PrimarySamePagePass().run(state)

    assert len(report.accepted) == 1
    assert report.accepted[0].figure_no == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ocr_figure_vnext_passes.py -v`
Expected: FAIL because `PrimarySamePagePass` does not exist and arbitration is not implemented.

- [ ] **Step 3: Implement the pass with collect-then-commit arbitration**

```python
# paperforge/worker/ocr_figure_vnext_passes.py
from __future__ import annotations

from .ocr_figure_vnext_types import ClaimProposal, PassReport, ResourceRef


def _resource_page(block: dict) -> int | None:
    page = block.get("page")
    if page is None:
        page = block.get("page_num")
    return int(page) if page is not None else None


class PrimarySamePagePass:
    name = "primary_same_page"

    def _collect_proposals(self, state):
        from . import ocr_figures

        proposals = []
        for legend in state.candidate_index.deduped_legends:
            page = _resource_page(legend)
            if page is None:
                continue
            page_groups = [g for g in state.candidate_index.candidate_groups if _resource_page(g) == page]
            for group in page_groups:
                score = ocr_figures._score_legend_to_group(
                    legend,
                    group,
                    caption_score=ocr_figures.score_figure_caption(legend, nearby_media=True, caption_style_match=False, body_prose_likelihood=False),
                    page_width=state.corpus.page_width,
                )
                if score.get("decision") != "matched":
                    continue
                figure_no = ocr_figures._extract_figure_number(str(legend.get("text", "")))
                proposals.append(ClaimProposal(
                    pass_name=self.name,
                    figure_no=figure_no,
                    claim_type="match",
                    legends=[ResourceRef(kind="legend", page=page, block_id=legend.get("block_id"), figure_no=figure_no)],
                    assets=[ResourceRef(kind="asset", page=page, block_id=bid) for bid in group.get("asset_block_ids", [])],
                    groups=[ResourceRef(kind="group", page=page, block_id=None, group_id=group.get("group_id"))],
                    confidence=float(score.get("score", 0.0)),
                    evidence_rank=1,
                    reason="same_page_primary",
                    diagnostics={"evidence": list(score.get("evidence", [])), "legend_block_id": str(legend.get("block_id", ""))},
                ))
        return proposals

    def _materialize_match(self, state, proposal):
        from . import ocr_figures

        legend = proposal.legends[0]
        page = legend.page
        asset_ids = {str(r.block_id) for r in proposal.assets}
        matched_assets = [ocr_figures._project_asset_record(a) for a in state.corpus.raw_assets if _resource_page(a) == page and str(a.get("block_id", "")) in asset_ids]
        legend_text = next(str(b.get("text", "")) for b in state.candidate_index.deduped_legends if str(b.get("block_id", "")) == legend.block_id)
        namespace = ocr_figures._extract_figure_namespace(legend_text)
        return {\n            \"figure_id\": ocr_figures._format_figure_id(namespace, proposal.figure_no),\n            \"figure_namespace\": namespace,\n            \"figure_number\": proposal.figure_no,\n            \"legend_block_id\": legend.block_id,\n            \"page\": page,\n            \"text\": legend_text,\n            \"matched_assets\": matched_assets,\n            \"asset_block_ids\": sorted(asset_ids),\n            \"settlement_type\": \"same_page\",\n            \"confidence\": proposal.confidence,\n            \"match_score\": {\"score\": proposal.confidence, \"decision\": \"matched\", \"evidence\": proposal.diagnostics[\"evidence\"]},\n            \"flags\": [],\n            \"bridge_block_ids\": [],\n        }

    def run(self, state):
        report = PassReport(pass_name=self.name)
        proposals = self._collect_proposals(state)
        report.proposals.extend(proposals)

        for proposal in sorted(proposals, key=lambda p: (p.evidence_rank, -p.confidence, -(p.figure_no or -1))):
            conflict = state.ledger.try_claim_assets(proposal.assets, owner=proposal.legends[0], reason=proposal.reason)
            if conflict is not None:
                report.conflicts.append(conflict)
                report.rejected.append(proposal)
                continue
            state.accept_match(proposal, self._materialize_match(state, proposal))
            report.accepted.append(proposal)

        return report
```

```python
# paperforge/worker/ocr_figures.py
from dataclasses import asdict


def build_figure_inventory_vnext(structured_blocks: list[dict], page_width: float = 1200) -> dict[str, Any]:
    from .ocr_figure_vnext_corpus import FigureCandidateIndex, FigureCorpus
    from .ocr_figure_vnext_passes import PrimarySamePagePass, _resource_page
    from .ocr_figure_vnext_state import FigurePipelineState, OwnershipLedger

    corpus = FigureCorpus.from_blocks(structured_blocks, page_width=page_width)
    candidate_index = FigureCandidateIndex.from_corpus(corpus)
    state = FigurePipelineState(corpus=corpus, candidate_index=candidate_index, ledger=OwnershipLedger())
    report = PrimarySamePagePass().run(state)
    matched_ids = {str(m.get("legend_block_id", "")) for m in state.matches}

    return {
        \"pipeline_mode\": \"vnext\",
        \"matched_figures\": state.matches,
        \"ambiguous_figures\": [],
        \"unmatched_legends\": [b for b in candidate_index.deduped_legends if str(b.get(\"block_id\", \"\")) not in matched_ids],
        \"unmatched_assets\": [a for a in corpus.raw_assets if (_resource_page(a) is not None and state.ledger.owner_of_asset(page=_resource_page(a), block_id=a.get(\"block_id\")) is None)],
        \"unresolved_clusters\": [],
        \"held_figures\": list(candidate_index.held_legends),
        \"rejected_legends\": list(candidate_index.rejected_legends),
        \"page_ledger\": {},
        \"residual_ledger\": {},
        \"local_pairing_hypotheses\": [],
        \"pass_reports\": [asdict(report)],
        \"completeness\": {\"total_numbered_legends\": len(candidate_index.deduped_legends), \"accounted_for\": len(state.matches), \"details\": []},
    }
```

- [ ] **Step 4: Add comparison smoke test**

```python
# tests/test_ocr_figure_vnext_compare.py
from paperforge.worker.ocr_figures import build_figure_inventory_legacy, build_figure_inventory_vnext
from scripts.dev.compare_figure_inventory_legacy_vs_vnext import compare_inventories


def test_compare_inventories_reports_counts_for_same_page_case():
    blocks = [
        {\"block_id\": \"c1\", \"page\": 1, \"role\": \"figure_caption\", \"text\": \"Figure 1. Caption\", \"bbox\": [0, 100, 200, 150]},
        {\"block_id\": \"a1\", \"page\": 1, \"role\": \"figure_asset\", \"bbox\": [0, 0, 200, 90], \"raw_label\": \"image\"},
    ]
    legacy = build_figure_inventory_legacy(blocks, 1200)
    vnext = build_figure_inventory_vnext(blocks, 1200)
    diff = compare_inventories(legacy, vnext)

    assert diff[\"vnext_matched_count\"] >= 1
    assert \"vnext_consumed_block_ids\" in diff
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_ocr_figure_vnext_passes.py tests/test_ocr_figure_vnext_compare.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_figures.py paperforge/worker/ocr_figure_vnext_passes.py scripts/dev/compare_figure_inventory_legacy_vs_vnext.py tests/test_ocr_figure_vnext_passes.py tests/test_ocr_figure_vnext_compare.py
git commit -m "feat(ocr): add vnext same-page figure pass"
```

### Task 5: Portable real-paper diff harness for milestone corpus

**Files:**
- Create: `tests/fixtures/ocr_vnext_real_papers/2HEUD5P9/blocks.structured.jsonl`
- Modify: `scripts/dev/compare_figure_inventory_legacy_vs_vnext.py`
- Create: `tests/test_ocr_figure_vnext_real_papers.py`
- Read-only source: `D:/L/OB/Literature-hub/System/PaperForge/ocr/2HEUD5P9/structure/blocks.structured.jsonl`

**Interfaces:**
- Consumes:
  - `build_figure_inventory_legacy(...)`
  - `build_figure_inventory_vnext(...)`
  - `compare_inventories(...)`
- Produces:
  - portable repo fixture for one representative real paper
  - `compare_blocks_file(blocks_path: Path) -> dict[str, object]`
  - milestone diff report for one representative real paper

- [ ] **Step 1: Copy the representative real-paper blocks into a repo fixture**

```python
from pathlib import Path
from shutil import copy2

src = Path(r"D:/L/OB/Literature-hub/System/PaperForge/ocr/2HEUD5P9/structure/blocks.structured.jsonl")
dst = Path("tests/fixtures/ocr_vnext_real_papers/2HEUD5P9/blocks.structured.jsonl")
dst.parent.mkdir(parents=True, exist_ok=True)
copy2(src, dst)
```

- [ ] **Step 2: Write the failing fixture-backed test**

```python
# tests/test_ocr_figure_vnext_real_papers.py
from pathlib import Path

from scripts.dev.compare_figure_inventory_legacy_vs_vnext import compare_blocks_file


def test_real_paper_same_page_milestone_reports_diff_shape():
    blocks_path = Path("tests/fixtures/ocr_vnext_real_papers/2HEUD5P9/blocks.structured.jsonl")
    diff = compare_blocks_file(blocks_path)

    assert diff["paper"] == "2HEUD5P9"
    assert "legacy_matched_count" in diff
    assert "vnext_matched_count" in diff
    assert "legacy_consumed_block_ids" in diff
    assert "vnext_consumed_block_ids" in diff

- [ ] **Step 3: Run the test to verify it fails**

Run: `python -m pytest tests/test_ocr_figure_vnext_real_papers.py -v`
Expected: FAIL because `compare_blocks_file(...)` does not exist yet.

- [ ] **Step 4: Add helper for loading one paper and reporting the milestone diff contract**

```python
# scripts/dev/compare_figure_inventory_legacy_vs_vnext.py
from pathlib import Path


def _figure_asset_ids(fig: dict[str, object]) -> list[str]:
    ids = {str(x) for x in fig.get(\"asset_block_ids\", [])}
    ids.update(str(a.get(\"block_id\", \"\")) for a in fig.get(\"matched_assets\", []))
    return sorted(x for x in ids if x)


- [ ] **Step 4: Add helper for loading one paper and reporting the milestone diff contract**

```python
# scripts/dev/compare_figure_inventory_legacy_vs_vnext.py
from pathlib import Path


def _figure_asset_ids(fig: dict[str, object]) -> list[str]:
    ids = {str(x) for x in fig.get("asset_block_ids", [])}
    ids.update(str(a.get("block_id", "")) for a in fig.get("matched_assets", []))
    return sorted(x for x in ids if x)


def compare_blocks_file(blocks_path: Path) -> dict[str, object]:
    blocks = [json.loads(line) for line in blocks_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    legacy = build_figure_inventory_legacy(blocks)
    vnext = build_figure_inventory_vnext(blocks)
    diff = compare_inventories(legacy, vnext)
    diff["paper"] = blocks_path.parent.name
    return diff
```

- [ ] **Step 5: Re-run the real-paper milestone test**

Run: `python -m pytest tests/test_ocr_figure_vnext_real_papers.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/ocr_vnext_real_papers/2HEUD5P9/blocks.structured.jsonl scripts/dev/compare_figure_inventory_legacy_vs_vnext.py tests/test_ocr_figure_vnext_real_papers.py
git commit -m "test(ocr): add portable vnext real-paper comparison harness"
```

## Self-Review

- Spec coverage: This plan deliberately covers only the first safe milestone from the spec: mechanical extraction, comparison harness, core contracts, immutable corpus/candidate split, and same-page primary matching. It intentionally leaves sidecar, bundle, locator, group-aware sequential, classic sequential, composite-parent settlement, and final cutover for later plans.
- Placeholder scan: No `TBD`, `TODO`, temporary fixture placeholders, or deferred implementation markers remain in the task steps. Task 5 uses a repo fixture, not a machine-local pytest path.
- Type consistency: `ResourceRef`, `ClaimProposal`, `PassReport`, `OwnershipLedger`, `FigureCorpus`, `FigureCandidateIndex`, `FigurePipelineState.accept_match(...)`, and `PrimarySamePagePass` are defined before later tasks consume them.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-03-figure-pipeline-vnext-phase0-phase1.md`. Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?