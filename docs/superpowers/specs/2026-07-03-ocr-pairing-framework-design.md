# OCR Pairing Framework Design

Date: 2026-07-03
Scope: OCR object pairing framework for figure and table pipelines
Status: Draft for review

## 1. Goal

Create a reusable OCR object-pairing framework that cleanly separates:

1. immutable OCR facts extracted from `structured_blocks`
2. derived matching hypotheses
3. ownership and conflict arbitration
4. ordered pairing passes
5. domain-specific inventory assembly

The first two domains on this framework are:

- figure pairing (`build_figure_inventory` / figure vnext)
- table pairing (`build_table_inventory` / future table vnext)

This work is not a one-off table rescue. It establishes the stable seam for OCR object pairing so figure and table pipelines stop evolving as unrelated systems.

## 2. Non-goals

- No redesign of OCR role assignment, zone inference, signatures, or document layout.
- No graph-optimizer or global inference engine in this iteration.
- No change to downstream public outputs beyond preserving current figure/table inventory contracts.
- No attempt to unify figure and table heuristics into one scoring function.
- No speculative support for formula, algorithm, or supplementary pipelines beyond leaving extension points.

## 3. Current state

## 3.1 Figure pipeline

The current figure pipeline already has a strong internal shape:

```text
FigureCorpus -> FigureCandidateIndex -> FigurePipelineState + OwnershipLedger -> ordered passes -> inventory
```

Observed properties:

- `build_figure_inventory` is now a thin wrapper over `build_figure_inventory_vnext`
- figure vnext already uses:
  - `ResourceRef`
  - `ClaimProposal`
  - `PassReport`
  - `OwnershipLedger`
  - explicit pass orchestration
- figure pipeline behavior has already been validated vault-wide after recent vnext fixes

The main structural problem is placement, not concept. Generic pairing primitives live under `ocr_figure_vnext_*` files even though they are not figure-specific.

## 3.2 Table pipeline

The current table pipeline is still centered on one monolithic `build_table_inventory(structured_blocks)` function in `paperforge/worker/ocr_tables.py`.

Observed properties:

- caption discovery, asset discovery, scoring, ambiguity handling, continuation handling, note attachment, and final assembly all live in one function
- ownership is tracked implicitly via `used_asset_indices: set[int]`
- arbitration priority is encoded by control flow rather than explicit pass boundaries
- the pipeline already contains table-specific heuristics that are worth preserving, including:
  - weak-truncated caption continuation recovery
  - adjacent-page candidate search
  - continuation geometry elevation
  - footnote prior handling
  - `table_html` and rotated table support

The main structural problem is that table pairing has no explicit seam between facts, hypotheses, arbitration, and output assembly.

## 3.3 Shared call-site seam

`run_derived_rebuild_for_keys()` and OCR post-processing already call figure and table pairing side by side:

1. build figure inventory
2. build table inventory
3. resolve cross-domain media ownership conflicts
4. write inventories and object artifacts
5. render markdown

This is the correct external seam to preserve. The new framework is an internal refactor under the existing OCR orchestration.

## 4. Why the framework should be generic

A table-only rewrite would fix the current pain, but it would preserve the wrong module boundary.

The durable pattern in this repository is not “figure pairing” or “table pairing.” It is:

```text
facts -> hypotheses -> claims -> ownership arbitration -> accepted matches -> inventory assembly
```

That pattern is already proven by figure vnext and is broad enough to cover table pairing without forcing figure and table to share heuristics.

The framework should therefore extract the stable pairing mechanics while leaving domain reasoning in figure/table modules.

## 5. Rejected approaches

## 5.1 Option A — shallow reuse only

Extract only `OwnershipLedger` and the pass runner, but leave corpus/index/state structures duplicated in figure and table modules.

Rejected because:

- it shares utilities but not the real seam
- a third pairing domain would duplicate the same state model again
- it reduces code duplication without materially improving locality

## 5.2 Option C — graph engine / universal optimizer

Build a fully generic OCR object graph engine with typed nodes, weighted relations, and global optimization.

Rejected because:

- it overfits future possibilities rather than current repository needs
- it would replace proven heuristics with a more ambitious and less verifiable abstraction
- it would expand verification surface too much for the immediate problem

## 6. Recommended approach

Use a medium-depth design:

- extract a generic **OCR pairing framework** for ownership, proposals, reports, state transitions, and pass orchestration
- keep **figure domain** and **table domain** separate for fact extraction, hypothesis generation, scoring, and final inventory assembly
- migrate figure first with no intended behavior change
- build table vnext on the framework only after figure migration proves the seam

This gives the repository one deep module for pairing mechanics and two domain modules for figure/table reasoning.

## 7. Target architecture

```text
structured_blocks
    |
    +--> FigureDomain
    |      FigureCorpus
    |      FigureCandidateIndex
    |      figure passes
    |      assemble_figure_inventory
    |
    +--> TableDomain
           TableCorpus
           TableCandidateIndex
           table passes
           assemble_table_inventory

                both use
                     |
                     v
          OCR Pairing Framework
          - ResourceRef
          - ClaimProposal
          - PassReport
          - OwnershipConflict
          - OwnershipLedger
          - PipelineState
          - run_pipeline()
```

## 8. Module boundaries

## 8.1 New framework modules

### A. `paperforge/worker/ocr_pairing_types.py`

Responsibility: identity and proposal types used by all pairing domains.

Contents:

- `ResourceRef`
- `OwnershipConflict`
- `ClaimProposal`
- `PassReport`

These are currently figure-vnext types in all but name.

### B. `paperforge/worker/ocr_pairing_state.py`

Responsibility: generic runtime pairing state and ownership tracking.

Contents:

- `OwnershipLedger`
- `PipelineState`
- optional `PipelineResult` helper if result assembly needs a common staging object

The key rule is that this module may know about:

- assets
- groups
- reservations
- conflicts
- diagnostics

It must not know about:

- figure IDs
- table numbers
- caption continuation semantics
- rotation metadata fields
- markdown rendering

### C. `paperforge/worker/ocr_pairing_framework.py`

Responsibility: pass protocol and orchestration.

Contents:

- `PassBase` protocol or abstract base
- `run_pipeline(state, pass_classes)`
- tiny framework helpers only when they are domain-neutral

The framework should not become a helper junk drawer. If a helper contains figure- or table-specific geometry assumptions, it stays in the domain module.

## 8.2 Figure domain modules

### `paperforge/worker/ocr_figure_domain.py`

Responsibility:

- `FigureCorpus`
- `FigureCandidateIndex`
- figure-specific indexing helpers
- figure-specific match record assembly helpers

Existing figure pass files remain, but their imports move from `ocr_figure_vnext_types/state` to the new framework modules.

Figure-specific enrichments such as rotated-caption output metadata remain in the figure domain, not in the framework.

## 8.3 Table domain modules

### `paperforge/worker/ocr_table_domain.py`

Responsibility:

- `TableCorpus`
- `TableCandidateIndex`
- table-specific hypothesis generation
- table-specific inventory assembly helpers

### `paperforge/worker/ocr_table_passes.py` and optional split pass files

Responsibility:

- all ordered table pairing passes
- use framework proposals/ledger/state
- preserve current table heuristics while making arbitration explicit

## 9. Interface design

## 9.1 Framework resource model

`ResourceRef` remains intentionally small:

```python
@dataclass(frozen=True)
class ResourceRef:
    kind: Literal["legend", "asset", "group"]
    page: int | None
    block_id: str | None
    group_id: str | None = None
    entity_no: int | None = None
    origin: str | None = None
```

Design choices:

- `kind` stays generic; no `figure_legend` vs `table_caption`
- `entity_no` is neutral naming for figure number / table number
- `group` stays optional because figures use it heavily and tables may use it for continuation chains or grouped assets later
- the framework does not distinguish “caption” vs “legend”; domain modules decide what semantic role maps onto `kind="legend"`

## 9.2 Pipeline state

`PipelineState` owns the mutable runtime surface:

- `corpus`
- `candidate_index`
- `ledger`
- `matches`
- `unresolved`
- `hypotheses`
- `diagnostics`
- `reservations`
- `completeness`

The state object is generic, but it may accept optional domain hooks:

- `on_accept_match(proposal, match_record)`
- `on_accept_reservation(proposal)`

That keeps framework state transitions generic while allowing figure/table domains to enrich accepted records.

## 9.3 Pass protocol

Every pass must follow the same contract:

1. inspect corpus/index/state
2. produce zero or more `ClaimProposal`s
3. attempt ownership actions through `OwnershipLedger`
4. materialize accepted proposals into domain match records
5. emit a `PassReport`

This is the deep seam. Callers and tests should reason about passes through proposals, accepted matches, conflicts, and diagnostics rather than through incidental list mutation.

## 10. Figure migration plan

Figure migration is a **no-behavior-change refactor**.

Phase goals:

1. move generic types/state/runner out of figure-vnext modules
2. update figure pass imports
3. preserve `build_figure_inventory_vnext()` orchestration order
4. preserve figure output contract and diagnostics
5. re-run existing figure tests and comparison tooling unchanged

Explicit non-goal during migration:

- no new figure heuristic work unless required to keep behavior identical after extraction

This phase proves whether the framework seam is correctly chosen.

## 11. Table vnext design

Table vnext should not copy the figure pass list. It needs a smaller pass set matching table-specific behavior.

Recommended initial passes:

### 11.1 `TableSamePagePass`

Primary caption-to-asset matching on the same page using existing `score_table_match()` evidence.

### 11.2 `TableWeakCaptionRecoveryPass`

Handles weak or truncated captions, including continuation text materialization and weak explicit caption gating.

### 11.3 `TableAdjacentPagePass`

Handles candidate pages `page-1`, `page`, `page+1` with continuation geometry elevation and explicit arbitration.

### 11.4 `TableNotesAttachmentPass`

Attaches bridge blocks, note blocks, and footnote-like table notes after the main match decision.

### 11.5 `TableFinalAccountingPass`

Produces completeness/accounting, unmatched captions, unmatched assets, and diagnostics.

A later sixth pass may be added if bare-asset or continuation-chain handling proves cleaner as a separate pass, but this is not assumed up front.

## 12. Ownership model

The current table pipeline’s `used_asset_indices` is replaced by `OwnershipLedger`.

Rules:

- an asset may have only one owner inside a domain pairing run
- reservations must be explicit and logged
- ambiguity is represented as rejected or unresolved proposals, not by silently skipping assets
- cross-domain figure-vs-table media conflict resolution remains outside the framework at the current rebuild seam

This last rule matters. The pairing framework is **intra-domain** arbitration. Figure-vs-table conflict resolution remains a separate OCR orchestration concern.

## 13. Result assembly

The framework must not output final `figure_inventory` or `table_inventory` JSON directly.

Reason:

- figure and table output shapes are materially different
- output fields such as `rotation_correction_deg`, `continuation_of`, `note_block_ids`, `matched_assets`, and `table_number` are domain semantics

Therefore:

- framework output = accepted matches, reservations, conflicts, diagnostics, completeness
- domain output = assembled inventory JSON preserving today’s external contracts

This avoids forcing a shallow “universal inventory” abstraction that would only mirror implementation details.

## 14. File layout after migration

Target layout:

```text
paperforge/worker/
  ocr_pairing_types.py
  ocr_pairing_state.py
  ocr_pairing_framework.py

  ocr_figure_domain.py
  ocr_figure_vnext_accounting_pass.py
  ocr_figure_vnext_bundle_pass.py
  ocr_figure_vnext_classic_seq_pass.py
  ocr_figure_vnext_composite_pass.py
  ocr_figure_vnext_group_seq_pass.py
  ocr_figure_vnext_locator_pass.py
  ocr_figure_vnext_passes.py
  ocr_figure_vnext_sidecar_pass.py

  ocr_table_domain.py
  ocr_table_passes.py
```

Current `ocr_figure_vnext_types.py` and `ocr_figure_vnext_state.py` should disappear after migration if no figure-only logic remains there.

`ocr_tables.py` and `ocr_figures.py` remain the external entrypoint files.

## 15. Branch strategy

Use a dedicated branch for isolation:

- branch: `feat/ocr-pairing-framework`

Recommended branch sequence:

1. framework extraction commit
2. figure migration commit(s)
3. table vnext introduction commit(s)
4. cleanup/cutover commit

Do not mix framework extraction with table heuristic changes in one commit. We want one commit range that proves figure behavior is preserved before table work starts.

## 16. Verification strategy

## 16.1 Figure migration verification

Required evidence:

- targeted figure unit/regression tests
- vnext comparison tooling still green on representative fixtures
- no intended change in figure inventory outputs except formatting-neutral diagnostics if needed

## 16.2 Table vnext verification

Required evidence:

- existing table tests updated or preserved
- explicit regression coverage for:
  - `table_html` assets
  - rotated tables
  - weak-truncated captions
  - continuation captions
  - adjacent-page matching
  - footnote/note attachment
- real-paper verification on at least one known table-heavy fixture and on `37LK5T97`

## 16.3 Integration verification

Required evidence:

- rebuild path still produces figure inventory, table inventory, objects, and markdown end-to-end
- figure/table cross-domain conflict resolution still runs at the rebuild seam
- no renderer contract breakage

## 17. Risks and controls

### Risk 1 — framework learns domain semantics

Control: keep all domain fields and enrichment hooks out of core framework types.

### Risk 2 — table vnext becomes a copy of figure vnext

Control: design passes around table behavior, not around symmetry with figure pass names.

### Risk 3 — migration changes figure behavior accidentally

Control: figure migration is its own commit range and verification gate before table work starts.

### Risk 4 — framework too shallow to matter

Control: framework must own ownership, proposals, reports, pass orchestration, and runtime state. If table still needs ad hoc ownership mutation outside `OwnershipLedger`, the seam is wrong.

## 18. Decision

Proceed with **Option B**:

- generic OCR pairing framework
- figure migrated first with no intended behavior change
- table vnext built on the framework second
- future extension allowed, but not designed around speculative universal object graph ambitions

This is the smallest deep module that solves the real architectural duplication without turning the OCR pairing problem into a research platform.
