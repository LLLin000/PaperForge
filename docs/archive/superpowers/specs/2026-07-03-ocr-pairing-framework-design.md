# OCR Pairing Framework Design

Date: 2026-07-03
Scope: OCR object pairing framework for figure and table pipelines
Status: Draft for review

## 0. Preflight verification gate

Before any framework extraction starts, the implementation plan must prove the current baseline.

Required preflight checks:

1. confirm `build_figure_inventory(...)` currently delegates to `build_figure_inventory_vnext(...)`
2. confirm `ocr_figure_vnext_types.py` and `ocr_figure_vnext_state.py` contain no figure-only logic except naming and any explicitly documented hook behavior
3. run the current figure regression suite and record the passing baseline
4. run the current representative figure comparison command or script and save baseline output artifacts
5. if any preflight check fails, stop framework extraction and fix the baseline first

This gate is mandatory. “No-behavior-change migration” is not meaningful without a recorded figure baseline.

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
- No graph-optimizer or universal inference engine in this iteration.
- No change to downstream public outputs beyond preserving current figure/table inventory contracts.
- No attempt to unify figure and table heuristics into one scoring function.
- No immediate speculative implementation of formula, algorithm, or supplementary pairing domains beyond leaving extension points.

## 3. Current state

## 3.1 Figure pipeline

The current figure pipeline already has a strong internal shape:

```text
FigureCorpus -> FigureCandidateIndex -> FigurePipelineState + OwnershipLedger -> ordered passes -> inventory
```

Observed properties:

- `build_figure_inventory` is intended to be a thin wrapper over `build_figure_inventory_vnext`
- figure vnext already uses:
  - `ResourceRef`
  - `ClaimProposal`
  - `PassReport`
  - `OwnershipLedger`
  - explicit pass orchestration
- recent OCR work has treated figure vnext as the primary pairing path, but the exact default status must be re-proven by the preflight gate above

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
facts -> hypotheses -> claims -> ownership arbitration -> accepted claims -> inventory assembly
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

- extract a generic **OCR pairing framework** for ownership, proposals, reports, arbitration, state transitions, and pass orchestration
- keep **figure domain** and **table domain** separate for fact extraction, hypothesis generation, scoring, and final inventory assembly
- migrate figure first with no intended behavior change
- build table vnext on the framework only after figure migration proves the seam

This gives the repository one deep module for pairing mechanics and two domain modules for figure/table reasoning.

## 7. Implementation split

Implementation must be split into two plans.

### Plan A — Pairing framework extraction + figure migration

Scope:

- preflight baseline verification
- framework extraction
- figure migration onto framework
- import compatibility or shim handling
- no intended figure behavior change
- no table heuristic changes
- no table vnext implementation

This plan ends when figure pairing runs on the new framework with equivalent behavior.

### Plan B — Table vnext on pairing framework

Scope:

- table resource model finalization
- table corpus/index design
- table pass implementation
- legacy-vnext comparison tooling for tables
- behavior-changing validation where improvements are allowed

This plan starts only after Plan A is green.

## 8. Target architecture

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
          - AcceptedClaim
          - run_pipeline()
```

## 9. Module boundaries

## 9.1 New framework modules

### A. `paperforge/worker/ocr_pairing_types.py`

Responsibility: identity and proposal types used by all pairing domains.

Contents:

- `ResourceRef`
- `OwnershipConflict`
- `ClaimProposal`
- `PassReport`
- `AcceptedClaim` if accepted claims are represented explicitly rather than as raw proposals

These are currently figure-vnext types in all but name.

### B. `paperforge/worker/ocr_pairing_state.py`

Responsibility: generic runtime pairing state and ownership tracking.

Contents:

- `OwnershipLedger`
- `PipelineState`

The key rule is that this module may know about:

- accepted claims
- rejected proposals
- conflicts
- reservations
- diagnostics
- completeness
- claimable resources of kind `anchor`, `asset`, `group`, or `text`

It must not know about:

- figure IDs
- table numbers
- caption continuation semantics
- rotation metadata fields
- markdown rendering
- inventory JSON field names

### C. `paperforge/worker/ocr_pairing_framework.py`

Responsibility: pass protocol and orchestration.

Contents:

- `PairingPass` protocol or abstract base
- `run_pipeline(state, pass_classes)`
- arbitration ordering helpers that are truly domain-neutral

The framework should not become a helper junk drawer. If a helper contains figure- or table-specific geometry assumptions, it stays in the domain module.

## 9.2 Figure domain modules

### `paperforge/worker/ocr_figure_domain.py`

Responsibility:

- `FigureCorpus`
- `FigureCandidateIndex`
- figure-specific indexing helpers
- figure-specific accepted-claim assembly into figure inventory records

Existing figure pass files remain, but their imports move from `ocr_figure_vnext_types/state` to the new framework modules.

Figure-specific enrichments such as rotated-caption output metadata remain in the figure domain, not in the framework.

## 9.3 Table domain modules

### `paperforge/worker/ocr_table_domain.py`

Responsibility:

- `TableCorpus`
- `TableCandidateIndex`
- table-specific hypothesis generation
- table-specific accepted-claim assembly into table inventory records

### `paperforge/worker/ocr_table_passes.py` and optional split pass files

Responsibility:

- all ordered table pairing passes
- use framework proposals/ledger/state
- preserve current table heuristics while making arbitration explicit

## 10. Interface design

## 10.1 Framework resource model

`ResourceRef` should use neutral pairing language.

Preferred shape:

```python
@dataclass(frozen=True)
class ResourceRef:
    kind: Literal["anchor", "asset", "group", "text"]
    page: int | None
    block_id: str | None
    group_id: str | None = None
    entity_no: int | None = None
    role: str | None = None
    origin: str | None = None
```

Interpretation:

- `anchor` = numbered textual anchor, e.g. figure legend, table caption, locator caption
- `asset` = media block, table block, html table asset
- `group` = figure group, continuation group, or other grouped claim target
- `text` = note block, bridge block, caption tail, continuation text

Design choices:

- `anchor` replaces figure-biased `legend` naming
- `entity_no` remains neutral naming for figure number / table number
- `role` may distinguish attach-only text resources such as `note`, `bridge`, or `caption_tail`
- `origin` remains free for provenance when a domain needs additional audit context

If implementation keeps `kind="legend"` for compatibility, the spec requires an explicit definition that it means a generic numbered textual anchor, not specifically a figure legend.

## 10.2 Ownership semantics for text-like resources

Table notes, bridge blocks, and caption tails must not fall back to ad hoc side sets.

Framework rule:

- text-like resources may be journaled and attached even when they are not exclusive-owned in the same way as assets
- the ledger must support either exclusive claim or explicit attach-only journaling for these resources
- if table note tracking still needs manual mutation outside `OwnershipLedger`, the seam is wrong

## 10.3 Pipeline state

`PipelineState` should stay narrow and generic.

Preferred runtime surface:

- `domain`
- `corpus`
- `candidate_index`
- `ledger`
- `accepted`
- `rejected`
- `conflicts`
- `diagnostics`
- `completeness`

Optional:

- `reservations` if reservation is a framework-level concept rather than just a ledger journal event

The state should store accepted claims or accepted-claim records, not final figure/table inventory records. Domain assemblers convert accepted claims into domain inventory outputs later.

This prevents the framework state from turning into a new god object that indirectly carries figure/table JSON semantics.

## 10.4 Pass protocol and arbitration

Ownership arbitration must happen in the framework runner or through a framework-controlled ledger contract, not inside each pass’s local mutation loop.

Preferred pass contract:

1. inspect corpus/index/state
2. propose zero or more `ClaimProposal`s
3. framework runner sorts/arbitrates proposals
4. runner/ledger performs claim/reserve/block transitions
5. accepted claims are recorded generically
6. domain assembler converts accepted claims into inventory records after arbitration
7. pass emits `PassReport`

A pass may supply domain evidence payload in `ClaimProposal.diagnostics`, but it should not bypass framework arbitration by appending final inventory rows directly during proposal iteration.

This preserves the main vnext design goal: arbitration priority must be explicit, not an accident of loop order.

## 11. Figure migration plan contract

Figure migration is a **no-behavior-change refactor** and belongs entirely to Plan A.

Phase goals:

1. move generic types/state/runner out of figure-vnext modules
2. update figure pass imports
3. preserve `build_figure_inventory_vnext()` orchestration order
4. preserve figure output contract and diagnostics
5. re-run existing figure tests and comparison tooling unchanged

Explicit non-goals during figure migration:

- no new figure heuristic work unless required to keep behavior identical after extraction
- no table vnext implementation
- no table heuristic changes

This phase proves whether the framework seam is correctly chosen.

## 12. Table legacy behavior map

Before Plan B starts, the table rewrite must map every current behavior to a new home.

Required legacy parity map:

- caption discovery -> `TableCorpus` / `TableCandidateIndex`
- table asset discovery -> `TableCorpus`
- `score_table_match()` -> `TableSamePagePass` / `TableAdjacentPagePass`
- weak-truncated caption recovery -> `TableWeakCaptionRecoveryPass`
- adjacent-page candidate search -> `TableAdjacentPagePass`
- continuation geometry elevation -> `TableAdjacentPagePass`
- footnote prior handling -> scoring input or `TableNotesAttachmentPass`
- note / bridge attachment -> `TableNotesAttachmentPass`
- `table_html` / rotated table support -> `TableCorpus` asset projection + table assembler
- ambiguity handling -> framework rejected proposals / unresolved records
- `used_asset_indices` -> `OwnershipLedger`
- final inventory shape -> `assemble_table_inventory`

This map is mandatory input to Plan B.

## 13. Table vnext design

Table vnext should not copy the figure pass list. It needs a smaller pass set matching table-specific behavior.

Recommended initial passes:

### 13.1 `TableSamePagePass`

Primary caption-to-asset matching on the same page using existing `score_table_match()` evidence.

### 13.2 `TableWeakCaptionRecoveryPass`

Handles weak or truncated captions, including continuation text materialization and weak explicit caption gating.

### 13.3 `TableAdjacentPagePass`

Handles candidate pages `page-1`, `page`, `page+1` with continuation geometry elevation and explicit arbitration.

### 13.4 `TableNotesAttachmentPass`

Attaches bridge blocks, note blocks, footnote-like table notes, and caption-tail text after the main match decision.

### 13.5 `TableFinalAccountingPass`

Produces completeness/accounting, unmatched captions, unmatched assets, and diagnostics.

A later sixth pass may be added if bare-asset or continuation-chain handling proves cleaner as a separate pass, but this is not assumed up front.

## 14. Ownership model

The current table pipeline’s `used_asset_indices` is replaced by `OwnershipLedger`.

Rules:

- an asset may have only one owner inside a domain pairing run
- reservations must be explicit and logged
- ambiguity is represented as rejected or unresolved proposals, not by silently skipping assets
- attach-only text resources must still be journaled through framework-visible structures
- cross-domain figure-vs-table media conflict resolution remains outside the framework at the current rebuild seam

This last rule matters. The pairing framework is **intra-domain** arbitration. Figure-vs-table conflict resolution remains a separate OCR orchestration concern.

## 15. Result assembly

The framework must not output final `figure_inventory` or `table_inventory` JSON directly.

Reason:

- figure and table output shapes are materially different
- output fields such as `rotation_correction_deg`, `continuation_of`, `note_block_ids`, `matched_assets`, and `table_number` are domain semantics

Therefore:

- framework output = accepted claims, rejected proposals, conflicts, diagnostics, completeness, and any required reservation journal
- domain output = assembled inventory JSON preserving today’s external contracts

This avoids forcing a shallow “universal inventory” abstraction that would only mirror implementation details.

## 16. Cross-domain resolver compatibility contract

Cross-domain figure-vs-table conflict resolution stays outside the framework, but the framework migration must preserve the data it consumes.

Figure and table inventories must continue exposing enough stable consumed-media information for the resolver.

Required compatibility fields or equivalents:

- consumed block IDs or block/page-scoped IDs
- `matched_assets`-style records or an equivalent structured asset list
- stable `asset_block_ids` or equivalent normalized identifiers
- consistently normalized page numbers for all consumed resources

If Plan B changes the table inventory shape, it must preserve these resolver inputs or update the external resolver in the same plan with explicit regression coverage.

## 17. File layout after Plan A / Plan B

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

If tests or scripts still import them, temporary compatibility shims are acceptable during Plan A, but the final target is framework-owned types/state.

`ocr_tables.py` and `ocr_figures.py` remain the external entrypoint files.

## 18. Branch strategy

Use a dedicated branch for isolation:

- branch: `feat/ocr-pairing-framework`

Recommended sequence:

### Plan A commit range

1. preflight baseline evidence
2. framework extraction commit(s)
3. figure migration commit(s)
4. shim removal or import-compat cleanup commit(s)

### Plan B commit range

1. table parity-map preparation and legacy-vnext diff tooling
2. table domain and pass introduction commit(s)
3. table vnext verification and cutover commit(s)

Do not mix framework extraction with table heuristic changes in one commit range.

## 19. Verification strategy

## 19.1 Plan A — figure migration gate

Required evidence:

- all existing figure unit/regression tests pass
- import path compatibility tests pass if compatibility shims are used
- representative figure fixtures show no public output diff except diagnostics-only or formatting-neutral differences explicitly approved in review
- current comparison tooling remains runnable after migration
- if old `ocr_figure_vnext_types/state` modules remain temporarily, they are either compatibility shims or tested as deprecated import bridges

## 19.2 Plan B — table vnext gate

Required evidence:

- `build_table_inventory` remains legacy-backed until vnext passes regression review
- `build_table_inventory_vnext` exists separately during validation
- a legacy-vnext diff script or equivalent verification path exists for tables
- explicit regression coverage for:
  - `table_html` assets
  - rotated tables
  - weak-truncated captions
  - continuation captions
  - adjacent-page matching
  - notes / footnotes / bridge attachments
- real-paper verification on at least one known table-heavy fixture and on `37LK5T97`

## 19.3 Integration gate

Required evidence:

- rebuild path still produces figure inventory, table inventory, object artifacts, and markdown end-to-end
- renderer consumes both inventories without contract breakage
- cross-domain media conflict resolver still sees stable consumed IDs / asset records

## 20. Risks and controls

### Risk 1 — framework learns domain semantics

Control: keep all inventory-field semantics and output enrichments out of framework types/state.

### Risk 2 — table vnext becomes a copy of figure vnext

Control: design passes around table behavior and the legacy parity map, not around symmetry with figure pass names.

### Risk 3 — migration changes figure behavior accidentally

Control: make Plan A a dedicated no-behavior-change plan with explicit baseline diffing.

### Risk 4 — framework too shallow to matter

Control: framework must own ownership, proposals, reports, arbitration, and runtime state. If table still needs ad hoc ownership mutation outside `OwnershipLedger`, the seam is wrong.

## 21. Decision

Proceed with **Option B**:

- generic OCR pairing framework
- Plan A = framework extraction + figure no-behavior migration
- Plan B = table vnext on the framework
- future extension allowed, but not designed around speculative universal object graph ambitions

This is the smallest deep module that solves the real architectural duplication without turning the OCR pairing problem into a research platform.
