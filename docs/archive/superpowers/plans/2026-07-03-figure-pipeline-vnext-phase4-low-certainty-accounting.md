# Figure Pipeline VNext Phase 4 — Low-Certainty Fallbacks + Composite Parent + Accounting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the remaining passes from spec §7.3: `CompositeParentPass` (Layer 1, but runs during same-page scan), `GroupSequentialPass` (Layer 2), `ClassicSequentialPass` (Layer 3), unresolved cluster consolidation, and `FinalAccountingPass`. This completes all spec-defined passes and prepares the pipeline for cutover evaluation.

**Architecture:** Build on the completed Phase 0–3 vnext seams. Each pass follows the established proposal-then-commit pattern. Composite parent candidates are pre-built in the corpus/candidate index (they're structural, not matching decisions). The sequential passes consume only untouched or explicitly eligible resources per spec §7.3 Rule. The accounting pass verifies completeness and emits invariant violations.

**Tech Stack:** Python 3, pytest, existing OCR helpers in `paperforge/worker/ocr_figures.py`, vnext modules under `paperforge/worker/`

## Global Constraints

- Build on branch/worktree `feat/figure-pipeline-vnext`; do not edit the main checkout.
- Preserve the external interface `build_figure_inventory(structured_blocks, page_width=1200) -> FigureInventory`.
- Legacy implementation remains the immutable baseline.
- Keep `ResourceRef` as the only ownership key.
- Lower layers cannot steal already-claimed resources from higher layers (spec §7.3 Rule 1).
- Classic sequential consumes only untouched or explicitly eligible resources (spec §7.3 Rule 3).
- Disabled passes must emit no proposals.
- Final arbitration priority is independent of migration order.
- New pass reports must remain JSON-safe.
- Reuse existing legacy helper functions via lazy import — do not duplicate them.
- Add only the tests directly covering this phase.
- Do not implement final cutover in this plan.

---

### Task 1: Add composite_parent_candidates to FigureCandidateIndex

**Rationale:** The legacy pipeline builds composite parent candidates (`_build_composite_parent_figure_groups_visual_only` + `_build_dense_composite_parent_candidates`) as structural pre-computation before matching. The vnext `FigureCandidateIndex` needs these candidates available so `CompositeParentPass` (Task 2) can consume them. This is a structural computation, not a matching decision — it belongs in the candidate index.

**Files:**
- Modify: `paperforge/worker/ocr_figure_vnext_corpus.py`
- Modify: `tests/test_ocr_figure_vnext_corpus.py`

**Interfaces:**
- Consumes:
  - `ocr_figures._build_composite_parent_figure_groups_visual_only(atomic_groups, assets, structured_blocks, page_width) -> list[dict]`
- Produces:
  - `FigureCandidateIndex.composite_parent_candidates: list[dict]` (new field)

- [ ] **Step 1: Write failing test**

Add to `tests/test_ocr_figure_vnext_corpus.py`:

```python
def test_candidate_index_populates_composite_parent_candidates():
    # 4 assets on page 1 arranged in a 2x2 grid (two rows, two columns)
    # Each pair shares horizontal alignment and vertical adjacency
    # Assert: index.composite_parent_candidates is non-empty
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ocr_figure_vnext_corpus.py -k composite_parent -v`
Expected: FAIL (field doesn't exist)

- [ ] **Step 3: Add composite_parent_candidates to FigureCandidateIndex**

Add `composite_parent_candidates: list[dict]` field to the dataclass. In `from_corpus`, call:
```python
composite_parent_candidates = ocr_figures._build_composite_parent_figure_groups_visual_only(
    candidate_groups,
    corpus.raw_assets,
    corpus.blocks,
    corpus.page_width,
)
```
Pass it in the `cls(...)` return.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ocr_figure_vnext_corpus.py -v`
Expected: All pass

- [ ] **Step 5: Run full vnext suite**

Run: `python -m pytest tests/test_ocr_figure_vnext_*.py -q`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_figure_vnext_corpus.py tests/test_ocr_figure_vnext_corpus.py
git commit -m "feat(ocr): add composite_parent_candidates to vnext candidate index"
```

### Task 2: Implement CompositeParentPass

**Rationale:** The legacy composite parent arbitration (ocr_figures.py:3480-3598) runs as part of the same-page legend scan: for each numbered legend, if a composite parent candidate exists on the same page with sufficient confidence and ≥2 child groups, the legend claims all child group assets as a single multi-panel figure. This pass ports that into the proposal model.

**Files:**
- Create: `paperforge/worker/ocr_figure_vnext_composite_pass.py`
- Create: `tests/test_ocr_figure_vnext_composite_pass.py`

**Key logic (port from legacy ocr_figures.py:3480-3598):**
1. For each unmatched numbered legend:
   - Find composite_parent_candidates on the same page, not yet consumed
   - Sort by parent_confidence (highest first)
   - Check: confidence ≥ 0.60, no competing numbered legends on same page (or band-scoped), ≥2 effective child groups
   - Claim all child group assets via `try_claim_assets`
   - Create match with `settlement_type="composite_parent"`, `flags=["composite_parent_match"]`
2. `confidence` = parent_confidence, `evidence_rank=1` (high certainty, same-page)

- [ ] **Step 1: Write failing tests** (3 tests: happy path multi-panel match, competing caption blocks it, insufficient child groups skip)

- [ ] **Step 2: Run failing tests**

- [ ] **Step 3: Implement CompositeParentPass** (standalone file, local `_resource_page`, lazy import `ocr_figures`)

- [ ] **Step 4: Run tests**

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figure_vnext_composite_pass.py tests/test_ocr_figure_vnext_composite_pass.py
git commit -m "feat(ocr): add vnext CompositeParentPass"
```

### Task 3: Implement GroupSequentialPass

**Rationale:** The legacy group-aware sequential fallback (ocr_figures.py:4589-4716) consumes unmatched `distance_cluster` and `single_asset` groups that no same-page legend claimed. It matches unmatched numbered legends to these groups preferring same-page → next-page → previous-page order. This is spec §7.3 Layer 2.

**Files:**
- Create: `paperforge/worker/ocr_figure_vnext_group_seq_pass.py`
- Create: `tests/test_ocr_figure_vnext_group_seq_pass.py`

**Key logic (port from legacy ocr_figures.py:4589-4716):**
1. Collect unmatched groups: `candidate_groups` not yet claimed, type in `{distance_cluster, single_asset}`, no assets owned
2. Sort by page, then y-position
3. For each unmatched numbered legend:
   - Find same-page groups, score with `_score_legend_to_group`, take best if score ≥ 0.5
   - If no same-page match, take first next-page group
   - If no next-page, check previous-page with `_allow_previous_page_sequential_match`
   - Claim group assets via `try_claim_assets`
   - `confidence=0.45`, `evidence_rank=5`, `settlement_type="group_sequential"`, `flags=["group_sequential_match"]`

- [ ] **Step 1: Write failing tests** (3 tests: same-page group match, next-page fallback, previous-page with `_allow_previous_page_sequential_match` guard)

- [ ] **Step 2: Run failing tests**

- [ ] **Step 3: Implement GroupSequentialPass**

- [ ] **Step 4: Run tests**

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figure_vnext_group_seq_pass.py tests/test_ocr_figure_vnext_group_seq_pass.py
git commit -m "feat(ocr): add vnext GroupSequentialPass"
```

### Task 4: Implement ClassicSequentialPass + UnresolvedClusterConsolidation

**Rationale:** The legacy classic sequential fallback (ocr_figures.py:4720-4862) is the last-resort matcher: it matches unmatched numbered captions to remaining ungrouped assets in reading order. After sequential matching, remaining unmatched assets on pages with rejected legends form unresolved clusters. This is spec §7.3 Layer 3.

**Files:**
- Create: `paperforge/worker/ocr_figure_vnext_classic_seq_pass.py`
- Create: `tests/test_ocr_figure_vnext_classic_seq_pass.py`

**Key logic:**

**ClassicSequentialPass** (port from ocr_figures.py:4720-4830):
1. Compute ungrouped unmatched assets (not in any candidate_group, not owned)
2. Sort captions and assets by (page, y-position)
3. For each unmatched numbered caption:
   - Scan for previous-page asset (with `_allow_previous_page_sequential_match` guard) or future-page asset
   - Claim via `try_claim_assets`
   - `confidence=0.35`, `evidence_rank=6`, `settlement_type="sequential"`, `flags=["sequential_match"]`

**UnresolvedClusterConsolidation** (port from ocr_figures.py:4831-4862):
After classic sequential, build unresolved clusters from remaining unmatched assets on pages with rejected legends using `_media_clusters`. Store in `state.unresolved` (new field on `FigurePipelineState`).

- [ ] **Step 1: Write failing tests** (3 tests: classic sequential match in reading order, previous-page guard, unresolved cluster formation from rejected-legend page assets)

- [ ] **Step 2: Run failing tests**

- [ ] **Step 3: Implement ClassicSequentialPass + unresolved cluster logic**

Add `unresolved: list[dict]` field to `FigurePipelineState` if not already present (check first — it exists in the dataclass but is currently empty). The pass appends to `state.unresolved`.

- [ ] **Step 4: Run tests**

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figure_vnext_classic_seq_pass.py tests/test_ocr_figure_vnext_classic_seq_pass.py paperforge/worker/ocr_figure_vnext_state.py
git commit -m "feat(ocr): add vnext ClassicSequentialPass with unresolved cluster consolidation"
```

### Task 5: Implement FinalAccountingPass

**Rationale:** The legacy pipeline computes `figure_legend_completeness` (ocr_figures.py:4994-5126) which verifies every numbered formal legend lands in an explicit outcome bucket (matched, held, unmatched, gap). Spec §7.4 requires invariant checks after each pass. This pass runs last, computes completeness, and emits invariant violations.

**Files:**
- Create: `paperforge/worker/ocr_figure_vnext_accounting_pass.py`
- Create: `tests/test_ocr_figure_vnext_accounting_pass.py`

**Key logic:**
1. Collect all numbered legend block_ids that entered the pipeline (from `candidate_index.deduped_legends` with figure numbers)
2. Classify each into: matched (in `state.matches`), unmatched (in unmatched pool), held, or gap (silently dropped)
3. Check invariants (spec §7.4):
   - Every matched figure's assets are owned in the ledger
   - No unmatched legend appears in `state.matches`
   - `accounted_for == total - gap_count`
4. Populate `state.completeness` dict with total, accounted_for, gap_count, details
5. Emit invariant violations to `report.invariant_errors`

- [ ] **Step 1: Write failing tests** (3 tests: all legends matched → gap_count=0, one legend dropped → gap_count=1, invariant violation when asset ownership mismatch)

- [ ] **Step 2: Run failing tests**

- [ ] **Step 3: Implement FinalAccountingPass**

- [ ] **Step 4: Run tests**

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figure_vnext_accounting_pass.py tests/test_ocr_figure_vnext_accounting_pass.py
git commit -m "feat(ocr): add vnext FinalAccountingPass with invariant checks"
```

### Task 6: Wire all passes into orchestrator + populate output fields

**Rationale:** Wire the 4 new passes into the orchestrator in spec §7.3 layer order, and populate the output dict fields that were previously stubs (`unresolved_clusters`, `completeness` with real data).

**Pass ordering (spec §7.3, final):**
1. `PrimarySamePagePass` (Layer 1)
2. `CompositeParentPass` (Layer 1 — runs after same-page, before sidecar, because it's same-page structural)
3. `SidecarPass` (Layer 1)
4. `LocatorBridgePass` (Layer 1)
5. `CrossPageReservationPass` (Layer 2)
6. `CrossPageSettlementPass` (Layer 2)
7. `LegendBundlePass` (Layer 2)
8. `GroupSequentialPass` (Layer 2)
9. `ClassicSequentialPass` (Layer 3)
10. `FinalAccountingPass` (post-processing)

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`

**Changes to orchestrator:**
- Import all 4 new pass classes
- Add to pass ordering tuple
- Update output dict:
  - `"unresolved_clusters": state.unresolved` (instead of `[]`)
  - `"completeness"`: use `state.completeness` if populated by FinalAccountingPass

- [ ] **Step 1: Update orchestrator**

- [ ] **Step 2: Run all vnext tests**

Run: `python -m pytest tests/test_ocr_figure_vnext_*.py -q`
Expected: All pass

- [ ] **Step 3: Run full figure test suite**

Run: `python -m pytest tests/test_ocr_figures.py tests/test_ocr_render.py -q`
Expected: No regressions (legacy path unchanged, wrapper still calls legacy)

- [ ] **Step 4: Commit**

```bash
git add paperforge/worker/ocr_figures.py
git commit -m "feat(ocr): wire vnext Phase 4 passes into orchestrator with accounting"
```

## Self-Review

- Spec coverage: This phase completes all 10 spec-defined passes (§6.2 E). It implements spec §7.3 Layer 2 (group sequential), Layer 3 (classic sequential, unresolved consolidation), composite parent (structural same-page), and §7.4 invariants/accounting. Only final cutover (§8.3, §9) remains.
- Helper reuse: All passes reuse legacy helpers via lazy import (`_build_composite_parent_figure_groups_visual_only`, `_score_legend_to_group`, `_allow_previous_page_sequential_match`, `_media_clusters`, `_filter_figure_assets`, `_grouped_asset_page_ids`).
- Layer ordering: CompositeParentPass runs at Layer 1 (same-page structural) before sidecar. GroupSequential at Layer 2 after legend bundle. ClassicSequential at Layer 3 (lowest certainty, only untouched resources).
- Invariant checks: FinalAccountingPass implements spec §7.4 invariant examples.
- Placeholder scan: No `TBD` or `TODO` in task steps.

## Execution Handoff

Plan complete. Recommended: Subagent-Driven execution with Tasks 2-5 parallelizable (isolated files), Task 1 as prerequisite, Task 6 as final wiring.
