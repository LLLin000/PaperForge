# Figure Pipeline VNext — Robustness-First Modularization Design

Date: 2026-07-03
Scope: `paperforge/worker/ocr_figures.py` figure pipeline only
Status: Draft for review

## 1. Goal

Extract the legacy figure pipeline into a new, clean, robustness-first pipeline without incrementally mutating the existing 1663-line `build_figure_inventory` implementation.

The new pipeline must:

1. preserve the external interface `build_figure_inventory(structured_blocks, page_width=1200) -> FigureInventory`
2. support isolated development in a dedicated branch/worktree
3. make fallback behavior explicit and auditable
4. prevent state corruption across stages
5. allow clean cutover back into the main OCR pipeline without regressions

## 2. Non-goals

- No attempt to redesign the OCR role system, layout pipeline, or table pipeline in this effort.
- No immediate algorithmic rewrite of every heuristic.
- No mixed incremental edits inside the legacy function as the primary strategy.

## 3. Current state

### 3.1 Repository state observed on 2026-07-03

Current branch: `master`

Dirty tracked files:
- `AGENTS.md`
- `paperforge/worker/ocr_document.py`
- `paperforge/worker/ocr_figures.py`
- `tests/test_ocr_document.py`
- `tests/test_ocr_figures.py`
- `tests/test_ocr_real_paper_regressions.py`

Untracked artifacts:
- `project/archive/2026-07-03-layout-capability-audit.md`
- `project/archive/2026-07-03-layout-risk-scan.md`
- `project/archive/2026-07-03-mcp-risk-scan.md`
- `project/current/2026-07-03-figure-pipeline-analysis.md`
- `tests/fixtures/ocr_real_papers/9TW98JH8/`
- `tests/fixtures/ocr_real_papers/MZC482YI/`

Existing worktrees:
- `.worktrees/feat/pdf-annotation-layer`
- `.worktrees/feat-ocr-structured-pipeline`
- `.worktrees/ocr-v2` (detached HEAD)
- `.worktrees/paperforge-stabilization`
- `.worktrees/plugin-ts-migration`
- `../ocr-reading-order-layers`

Existing local branches tied to worktrees:
- `feat/ocr-structured-pipeline`
- `feat/pdf-annotation-layer`
- `feat/plugin-ts-migration`
- `feature/ocr-reading-order-layers`
- `paperforge-stabilization`
- `hotfix-1.5.5`
- `local-pairing-governance`
- `master`

### 3.2 Architectural state

The current figure pipeline is centered on `paperforge/worker/ocr_figures.py::build_figure_inventory`:

- 1663 lines
- 193 cyclomatic complexity
- 546 cognitive complexity
- 51 loops
- 55 direct callees
- 10 sequential processing stages

The primary structural weakness is not merely function size. The real weakness is the combination of:

- shared mutable state (`matched_figures`, `unmatched_legends`, `unmatched_assets`)
- global ownership mutation (`used_group_ids`, `used_asset_page_ids`, `FigureOwnershipRegistry`)
- sequential fallbacks that encode priority through execution order rather than explicit arbitration

## 4. Why a clean extraction is the right strategy

A cleanliness-first branch is justified because robustness work on this pipeline is unusually sensitive to hidden coupling. Editing the legacy function in place would keep all of the following risks alive during the refactor:

- accidental behavior changes inside a giant function
- interleaving old and new state models
- difficulty proving whether a regression came from the new design or the untouched legacy logic
- inability to compare outputs from old and new implementations on the same inputs

The safer strategy is to create a new pipeline implementation in isolation, keep the legacy path intact, and compare them explicitly before cutover.

## 5. Recommended branch/worktree strategy

### 5.1 Isolation model

Use a **dedicated branch and dedicated worktree** for the new figure pipeline only.

Recommended shape:

- branch: `feat/figure-pipeline-vnext`
- worktree: `.worktrees/feat-figure-pipeline-vnext`

The new pipeline should live alongside the old one, not inside it.

### 5.2 Cleanup before starting

Before creating the new worktree, review all existing worktrees and branches and classify each as:

- active and keep
- stale but inspect first
- removable

Special attention:

- `.worktrees/ocr-v2` is detached HEAD and should not be removed blindly
- any branch with unmerged commits or current relevance must be preserved

Cleanup must be conservative and evidence-led. Removal should happen only after verifying:

- branch merged or intentionally abandoned
- no uncommitted work inside the worktree
- no active role in current OCR work

### 5.3 Coexistence model

Do **not** put `if experimental:` branches throughout the old function.

Instead, make the first extraction step purely mechanical:

- rename the current implementation to `build_figure_inventory_legacy(...)`
- add a new `build_figure_inventory_vnext(...)` orchestrator
- keep `build_figure_inventory(...)` calling legacy until explicit cutover
- add a dev comparison harness that imports both functions directly

The stable wrapper during development is:

```python
def build_figure_inventory(structured_blocks, page_width=1200):
    return build_figure_inventory_legacy(structured_blocks, page_width)
```

The explicit experimental entrypoint is:

```python
def build_figure_inventory_vnext(structured_blocks, page_width=1200):
    ...
```

Comparison must happen through tooling/dev scripts, not production switching.

## 6. VNext architecture

## 6.1 External seam

Keep the existing external interface unchanged:

```python
build_figure_inventory(structured_blocks, page_width=1200) -> FigureInventory
```

This preserves downstream compatibility with renderers, rebuild scripts, and tests.

## 6.2 Internal modules

### A. `FigureCorpus`

Responsibility: immutable interpretation layer over `structured_blocks`.

Provides only stable facts and indexes:
- raw legend-like blocks
- raw asset-like blocks
- figure locator candidates
- page context
- layout hints
- block/page/resource indexes

It may perform:
- prefix recovery
- legend classification
- asset family hinting
- normalized block/resource indexing

It must **not** perform:
- candidate group construction
- fallback-specific hypothesis construction
- matching
- ownership mutation

### B. `FigureCandidateIndex`

Responsibility: derived candidate and hypothesis layer built from `FigureCorpus`.

Provides:
- formal legends
- held legends
- rejected legends
- deduped legends
- candidate groups
- competing caption pages
- sidecar candidates
- bundle-source candidates
- locator candidates

This split prevents `FigureCorpus` from becoming a new god object.

### C. `OwnershipLedger`

Responsibility: single authority over claimable resources.

Resources:
- legends
- groups
- assets

The only valid identity carrier is `ResourceRef`:

```python
@dataclass(frozen=True)
class ResourceRef:
    kind: Literal["legend", "asset", "group"]
    page: int | None
    block_id: int | str | None
    group_id: str | None = None
    figure_no: int | None = None
    origin: str | None = None
```

Identity rules:
- `block_id` alone is never a valid ownership key
- asset identity must include `page + block_id` or a future stable `asset_id`
- group identity must include `page + group_id`
- legend identity must include `page + block_id`, with normalized figure number attached when available

Capabilities:
- reserve
- claim
- block
- release
- conflict reporting
- journal emission
- snapshotting for diagnostics

This is the most important new seam. Without it, modularization would only be cosmetic.

### D. `FigurePipelineState`

Responsibility: store derived decision state, not raw OCR facts.

Contains:
- `corpus`
- `candidate_index`
- `ledger`
- `matches`
- `unresolved`
- `hypotheses`
- `diagnostics`

This state must expose controlled mutations rather than naked list edits.

### E. `Pass` modules

Each stage becomes a module with a small interface:

```python
class FigurePass(Protocol):
    name: str
    def run(self, state: FigurePipelineState) -> PassReport: ...
```

The passes are:
- `PrimarySamePagePass`
- `CrossPageReservationPass`
- `CrossPageSettlementPass`
- `SidecarPass`
- `LegendBundlePass`
- `LocatorBridgePass`
- `GroupSequentialPass`
- `ClassicSequentialPass`
- `CompositeParentPass`
- `FinalAccountingPass`

## 7. Processing model changes for robustness

## 7.1 Proposal-then-commit

Passes must stop mutating global outcome lists directly.

Each pass must first emit an explicit proposal object:

```python
@dataclass
class ClaimProposal:
    pass_name: str
    figure_no: int | None
    claim_type: Literal[
        "match",
        "reserve",
        "block",
        "unresolved_cluster",
        "composite_parent",
    ]
    legends: list[ResourceRef]
    assets: list[ResourceRef]
    groups: list[ResourceRef]
    confidence: float
    evidence_rank: int
    reason: str
    diagnostics: dict
```

And each pass must report its outcome explicitly:

```python
@dataclass
class PassReport:
    pass_name: str
    proposals: list[ClaimProposal]
    accepted: list[ClaimProposal]
    rejected: list[ClaimProposal]
    conflicts: list[OwnershipConflict]
    invariant_errors: list[str]
```

New flow:
1. pass generates `ClaimProposal`
2. proposal is validated
3. ledger arbitrates resource ownership
4. accepted proposals update state
5. rejected proposals remain in diagnostics

This avoids silent corruption from premature list/set mutation.

## 7.2 Explicit resource lifecycle

### Legend lifecycle
- `available`
- `held`
- `matched`
- `rejected`
- `consumed_as_locator`
- `consumed_as_bundle_source`

### Group lifecycle
- `available`
- `reserved`
- `matched`
- `blocked`
- `promoted_to_composite_parent`

### Asset lifecycle
- `available`
- `reserved`
- `owned`
- `blocked`
- `absorbed_into_unresolved_cluster`

## 7.3 Fallbacks become layered arbitration

Replace the current long sequential fallback chain with explicit layers.

### Layer 1 — high certainty
- same-page primary
- sidecar
- locator bridge

### Layer 2 — structural cross-page
- cross-page reservation/settlement
- legend bundle
- group-aware sequential

### Layer 3 — low certainty fallback
- classic sequential
- dense/unresolved consolidation

Rules:
- lower layers cannot steal already-claimed resources from higher layers
- same-layer conflicts are resolved by confidence, evidence rank, and pass-specific precedence
- classic sequential consumes only untouched or explicitly eligible resources

## 7.4 Invariants become first-class

Each pass should be followed by invariant checks.

Examples:
- one asset cannot be owned by two figures
- matched legends cannot remain in unmatched pools
- unresolved clusters cannot contain owned assets
- completeness totals must equal the numbered legends admitted to the pipeline
- every consumed resource must be explainable through journal entries

## 7.5 Preserve information; do not eagerly delete it

When a pass fails, downgrade state rather than deleting objects from the system.

Examples:
- failed match -> unmatched, not removed
- unsafe group -> blocked with reason
- locator-consumed legend -> marked consumed, not erased
- low-certainty match -> preserved as such in diagnostics

This improves auditability and debugging.

## 8. Migration strategy

## 8.1 First cut

Do **not** start with sidecar or bundle logic.

Phase 0 must be purely mechanical extraction:

- rename current behavior to `build_figure_inventory_legacy(...)`
- add a new `build_figure_inventory_vnext(...)` orchestrator shell
- keep `build_figure_inventory(...)` calling legacy only
- add a `compare_figure_inventory_legacy_vs_vnext` harness

The legacy implementation is an immutable behavioral baseline.

Do **not** retrofit `OwnershipLedger` into the legacy function.
The ledger is introduced only inside `build_figure_inventory_vnext(...)`.

## 8.2 Recommended rollout order

### Step 1
Mechanical extraction + comparison harness

### Step 2
`OwnershipLedger` + `FigurePipelineState` + same-page primary matching inside vnext

### Step 3
Cross-page reservation + settlement

### Step 4
Special fallbacks
- sidecar
- bundle
- locator

### Step 5
Low-certainty and accounting tail
- group-aware sequential
- classic sequential
- completeness/accounting

Rationale: the weakest, broadest fallback logic should be migrated last.

Migration order does **not** define final arbitration priority.
During partial rollout, disabled passes must emit no proposals.
Final arbitration priority is defined only by the layer table in §7.3.

## 8.3 Comparison strategy

During development, run the new path and legacy path on the same papers and diff:

- matched figure count
- unmatched legends
- unresolved clusters
- ownership conflicts
- completeness totals
- downstream rendering effects

Required comparison corpus must include:
- same-page normal figure
- multi-panel same-row group
- sidecar legend page
- bundle-source page
- locator-bridge page
- dense composite parent page
- classic sequential-only rescue page
- unmatched asset / unresolved cluster page
- duplicated / continued legend page

Each corpus entry should emit a diff report containing at least:
- legacy matched count
- vnext matched count
- legacy unresolved count
- vnext unresolved count
- resource conflict count
- rendered figure cards diff
- consumed block ids diff

## 9. Cutover gates

The new pipeline becomes default only if all of the following hold.

### Gate 1 — contract
`FigureInventory` schema remains compatible.

### Gate 2 — regression suite
All relevant figure/render/rebuild tests pass.

### Gate 3 — real-paper diff review
Differences on representative real papers are explained and judged strictly better or equivalent.

VNext may differ from legacy only if:
- the difference is explicitly recorded in the diff report
- no previously rendered confident figure disappears without explanation
- no owned asset appears in unresolved clusters
- no figure card consumes the same asset twice

### Gate 4 — diagnostics superiority
The new pipeline must provide stronger traceability than the old one:
- claim journal
- ownership conflict explanation
- pass-level invariants
- completeness accounting trace

## 10. Risk assessment

### Main benefits
- far better locality
- auditable ownership and fallback behavior
- safer future debugging
- ability to add new figure rules without touching a giant mutable function

### Main risks
- migration period may temporarily create dual complexity
- if `FigurePipelineState` is too broad, it becomes a new god object
- if pass interfaces leak too much detail, the modules stay shallow

## 11. Decision

Proceed with a clean extraction into a dedicated branch/worktree, anchored on a new ownership/state seam rather than incremental edits inside the existing giant function.

This is the best balance of robustness, cleanliness, and regression control.

## 12. Required clarifications before implementation

1. Legacy implementation is an immutable baseline.
   Do not retrofit `OwnershipLedger` into the legacy function.

2. Phase 0 only performs mechanical extraction:
   - `build_figure_inventory_legacy = old behavior`
   - `build_figure_inventory_vnext = new orchestrator shell`
   - `build_figure_inventory` keeps calling legacy until cutover

3. Add `ResourceRef` as the only valid ownership key.
   `block_id` alone is forbidden.

4. Define `ClaimProposal` and `PassReport` schemas before implementing passes.

5. Split `FigureCorpus` and `FigureCandidateIndex`:
   - `FigureCorpus` stores immutable facts
   - `FigureCandidateIndex` stores derived candidates and hypotheses

6. Add a legacy-vnext comparison harness before implementing special fallbacks.

7. Final arbitration priority is independent of migration order.
