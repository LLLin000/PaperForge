# Figure Ownership Arbitration Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Converge OCR-v2 figure ownership onto a single arbitration model so dense composite, panel-title, sidecar, and sequence-shell cases stop adding new direct settlement behavior.

**Architecture:** Keep the current OCR-v2 figure pipeline and persisted inventory buckets, but add an internal convergence layer: caption evidence normalization, candidate-source normalization, page-level arbitration metadata, and accounting semantics. This plan does not replace the previously approved visual-grammar roadmap; it constrains how the next `P1B/P2/health`-class work is implemented.

**Tech Stack:** Python, `pytest`, PaperForge OCR pipeline (`paperforge/worker/ocr_figures.py`, `ocr_figure_reader.py`, `ocr_render.py`), existing real-paper audit fixtures and live-paper regression corpus.

---

## 1. Scope And Relationship To Existing Roadmap

This plan implements the architecture constraints defined in:

- `docs/superpowers/specs/2026-06-23-figure-ownership-arbitration-convergence-design.md`

This plan does **not** replace:

- `docs/superpowers/specs/2026-06-23-ocr-visual-grammar-hardening-design.md`
- `docs/superpowers/plans/2026-06-23-ocr-visual-grammar-hardening-implementation.md`

Instead, it adds the missing convergence layer so later `P1B`/`P2`/accounting work cannot keep growing by direct fallback path.

This is a **convergence scaffolding plan first**.

Rule:

```text
It must not implement dense parent ownership arbitration unless P1A/P1B visual grammar foundations are already landed and explicitly verified.
```

Hard rules for this plan:

1. Do not create a new direct `settlement_type` path.
2. Do not remove existing persisted inventory buckets in this pass.
3. Do not widen atomic semantic grouping thresholds in `_cluster_semantic_page_assets()`.
4. Do not hardcode paper ids, page ids, or literal short labels such as `RND` / `COL II`.
5. Do not let `sequence_match` without real asset payload remain in `matched_figures`.
6. Treat dense composite as a subtype of `composite_parent`, not a parallel matcher family.
7. `Task 4`, `Task 5`, and `Task 7` are gated tasks and may not run unless `P1A` diagnostic-only composite-parent candidates already exist on the target branch.

---

## 2. Files Expected To Change

Primary implementation files:

- `paperforge/worker/ocr_figures.py`
- `paperforge/worker/ocr_figure_reader.py`
- `paperforge/worker/ocr_render.py` (only if accounting labels need render-safe treatment)

Primary tests:

- `tests/test_ocr_figures.py`
- `tests/test_ocr_figure_reader.py`
- `tests/test_ocr_render.py`

Reference docs/logging:

- `PROJECT-MANAGEMENT.md`
- `project/current/ocr-v2-generalization-boundary.md` (read for context only unless the implementation changes strategic conclusions)

Real-paper validation targets:

- `VFS8CBW2`
- `6FGDBFQN`
- `2UIPV93M`
- `RKSLQRIM`

---

## 3. Task 0: Baseline Convergence Inventory

**Files:**
- Modify: none
- Verify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`, `tests/test_ocr_figure_reader.py`, `tests/test_ocr_render.py`

- [ ] **Step 1: Record current settlement producers**

Inspect and list every code site that appends to `matched_figures` or emits match-like states in `paperforge/worker/ocr_figures.py`.

Expected producer list should include current landed producers.

If `composite_parent` is not yet a live producer on the branch, record it as a planned candidate source rather than as a missing baseline seam.

Typical producer list may include:

```python
same_page
composite_parent
sidecar
cross_page_backward
cross_page_forward
legend_bundle
group_sequential
sequential
sequence_match
```

- [ ] **Step 2: Record current bucket semantics**

Write down the active persisted buckets and where they are consumed:

```python
matched_figures
ambiguous_figures
held_figures
unmatched_legends
unmatched_assets
rejected_legends
unresolved_clusters
```

Verify reader/render assumptions before making any internal convergence change.

- [ ] **Step 3: Run baseline tests before changes**

Run:

```bash
python -m pytest tests/test_ocr_figures.py tests/test_ocr_figure_reader.py tests/test_ocr_render.py -q
```

Expected:

```text
current baseline remains green before convergence changes begin
```

---

## 4. Task 1: OwnershipDecision Adapter Layer

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Write failing tests for internal-to-persisted mapping**

Add focused tests asserting that internal ownership-decision metadata can be attached to existing persisted entries without replacing current bucket semantics.

Tests must use public registry APIs rather than direct mutation of `registry.asset_states`.

Use tests shaped like:

```python
def test_ownership_decision_metadata_attaches_without_replacing_buckets() -> None:
    from paperforge.worker.ocr_figures import _ownership_decision_metadata

    meta = _ownership_decision_metadata(
        "provisional",
        "same_page_partial",
        strong=False,
        reason="dense_page_leftovers",
    )

    assert meta["ownership_decision"] == "provisional"
    assert meta["decision_provenance"] == "same_page_partial"
    assert meta["strong_ownership"] is False
    assert meta["decision_reason"] == "dense_page_leftovers"
```

- [ ] **Step 2: Run the new mapping test to confirm failure**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "ownership_decision_metadata" -v --tb=short
```

Expected:

```text
FAIL because the helper does not exist yet
```

- [ ] **Step 3: Add minimal adapter helpers**

In `paperforge/worker/ocr_figures.py`, add a minimal internal metadata helper like:

```python
def _ownership_decision_metadata(decision: str, provenance: str, *, strong: bool, reason: str = "") -> dict:
    return {
        "ownership_decision": decision,
        "decision_provenance": provenance,
        "strong_ownership": strong,
        "decision_reason": reason,
    }
```

Do **not** introduce new persisted buckets in this task.
Do **not** remove current bucket writes in this task.

- [ ] **Step 4: Re-run the focused tests**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "ownership_decision_metadata" -v --tb=short
```

Expected:

```text
PASS
```

---

## 5. Task 2: Provisional Soft Reservation Semantics

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Write failing tests for provisional reservation behavior**

Add tests asserting that provisional ownership blocks legacy fallback consumption during arbitration but may still be superseded by a stronger candidate.

Use tests shaped like:

```python
def test_provisional_reservation_blocks_legacy_fallback() -> None:
    from paperforge.worker.ocr_figures import FigureOwnershipRegistry

    registry = FigureOwnershipRegistry()
    registry.soft_reserve_assets([(1, "a1")], owner_id="legend_1", reason="partial_dense_local")

    assert registry.can_consume_assets([(1, "a1")]) is False


def test_soft_reservation_does_not_update_final_used_sets_until_finalized() -> None:
    from paperforge.worker.ocr_figures import FigureOwnershipRegistry

    registry = FigureOwnershipRegistry()
    registry.soft_reserve_assets([(1, "a1")], owner_id="legend_1", reason="partial_dense_local")

    assert (1, "a1") not in registry.used_asset_page_ids


def test_release_soft_reservation_reopens_assets_for_fallback() -> None:
    from paperforge.worker.ocr_figures import FigureOwnershipRegistry

    registry = FigureOwnershipRegistry()
    registry.soft_reserve_assets([(1, "a1")], owner_id="legend_1", reason="partial_dense_local")
    registry.release_soft_reservation([(1, "a1")], owner_id="legend_1")

    assert registry.can_consume_assets([(1, "a1")]) is True


def test_stronger_candidate_may_supersede_soft_reservation() -> None:
    from paperforge.worker.ocr_figures import FigureOwnershipRegistry

    registry = FigureOwnershipRegistry()
    registry.soft_reserve_assets([(1, "a1")], owner_id="legend_1", reason="partial_dense_local")
    registry.finalize_soft_reservation([(1, "a1")], owner_id="legend_2", owner_family="figure")

    assert registry.asset_states[(1, "a1")]["owner_id"] == "legend_2"
```

- [ ] **Step 2: Run the provisional tests to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "provisional_reservation or soft_reservation" -v --tb=short
```

Expected: fail because `soft_reserved` semantics do not exist yet.

- [ ] **Step 3: Implement minimal soft reservation support**

Extend `FigureOwnershipRegistry` in `paperforge/worker/ocr_figures.py` with the smallest safe additions:

```python
def soft_reserve_assets(self, asset_ids: list[tuple[int, str]], *, owner_id: str, reason: str) -> None:
    ...

def finalize_soft_reservation(self, asset_ids: list[tuple[int, str]], *, owner_id: str, owner_family: str) -> None:
    ...

def release_soft_reservation(self, asset_ids: list[tuple[int, str]], *, owner_id: str) -> None:
    ...
```

Constraint:

```text
soft reservations are internal arbitration state only; they must not directly emit matched_figures entries
soft reservations must not update final used sets until finalized
```

- [ ] **Step 4: Re-run the provisional tests**

Run the same command and confirm green.

---

## 6. Task 3: Panel-Title Suppression As Structural Demotion

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Write failing tests for structural panel-title suppression**

Add tests for the exact contract from the spec:

```python
def test_short_unnumbered_in_figure_text_does_not_compete_with_numbered_caption() -> None:
    inventory = build_figure_inventory([...])
    assert all(
        h.get("legend_block_id") != "panel_title_1"
        for h in inventory["local_pairing_hypotheses"]
    )


def test_suppressed_panel_title_remains_embedded_not_body() -> None:
    inventory = build_figure_inventory([...])
    # Assert it is still represented as figure-internal evidence, not lost.
```

Use synthetic text such as `RND` / `COL II` only as test fixtures, not as implementation literals.

- [ ] **Step 2: Run the suppression tests to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "panel_title or embedded_figure_text" -v --tb=short
```

Expected: fail because no formal suppression layer exists yet.

- [ ] **Step 3: Implement structural demotion only**

Add a helper in `paperforge/worker/ocr_figures.py` such as:

```python
def _should_suppress_panel_title_candidate(block: dict, *, page_has_numbered_legend: bool, visual_envelopes: list[dict]) -> bool:
    ...
```

Rules:

1. no numbered marker
2. short text span
3. inside likely figure visual envelope
4. same page already has a strong numbered figure caption
5. no literal string blacklist

Input requirement:

```text
`visual_envelopes` must come from a visual-only prepass.
```

Allowed sources:

1. atomic group envelopes
2. diagnostic composite-parent envelopes if `P1A` already exists

Forbidden source:

```text
caption text identity must not define the visual envelope
```

Output behavior:

```text
demote from formal matching
retain as in-figure / embedded text evidence
never promote into body paragraphs
```

Add an audit-visible surface such as:

```python
inventory["suppressed_caption_candidates"] = [
    {
        "block_id": "...",
        "suppression_reason": "panel_title_inside_visual_envelope",
        "retained_as": "embedded_figure_text",
    }
]
```

- [ ] **Step 4: Re-run the suppression tests**

Run the same test slice and confirm green.

---

## 7. Task 4: Dense Composite Parent Candidate Normalization

**Gate:** This task may only run if `P1A` diagnostic-only composite-parent candidates already exist on the branch.

If they do not exist, stop and execute the `P1A` visual-grammar roadmap task first.

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Write failing tests for dense parent as a composite-parent subtype**

Add tests that enforce the spec’s subtype rule:

```python
def test_dense_parent_candidate_is_composite_parent_subtype() -> None:
    candidate = _build_dense_parent_candidate_fixture(...)
    assert candidate["group_type"] == "composite_parent"
    assert candidate["parent_subtype"] == "dense_composite"


def test_dense_parent_candidate_not_appended_into_ordinary_candidate_groups() -> None:
    inventory = build_figure_inventory([...])
    assert all(g.get("group_type") != "dense_composite_parent" for g in inventory.get("candidate_groups", []))
```

- [ ] **Step 2: Run the dense parent tests to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "dense_parent_candidate or composite_parent_subtype" -v --tb=short
```

Expected: fail because subtype normalization is not explicit yet.

Rule:

```text
This task may normalize existing parent candidate schema, but must not secretly implement parent generation if none exists.
```

- [ ] **Step 3: Normalize dense parent candidate schema**

Adjust parent candidate generation in `paperforge/worker/ocr_figures.py` so dense composite candidates are represented as:

```python
{
    "group_type": "composite_parent",
    "parent_subtype": "dense_composite",
    ...
}
```

Do not add a new settlement path.
Do not append them into the ordinary atomic `candidate_groups` stream.

- [ ] **Step 4: Re-run dense parent tests**

Run the same test slice and confirm green.

---

## 8. Task 5: Trigger/Scoring Separation For Dense Pages

**Gate:** This task may only run after `P1A` diagnostic-only composite-parent candidates already exist and Task 4 schema normalization is complete.

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Write failing tests for construction-time vs arbitration-time signals**

Add tests that enforce:

```text
construction-time candidate generation may not require already-built unresolved buckets
arbitration-time scoring may use coverage gain / leftover mass
```

Example test shape:

```python
def test_dense_parent_candidate_can_be_constructed_from_visual_fragment_count_only() -> None:
    ...


def test_dense_parent_arbitration_uses_leftover_mass_to_outrank_partial_same_page() -> None:
    ...
```

- [ ] **Step 2: Run the trigger/scoring tests to confirm failure**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "dense_parent_arbitration or leftover_mass" -v --tb=short
```

- [ ] **Step 3: Separate the two phases in code**

Refactor the parent logic into two helpers in `paperforge/worker/ocr_figures.py`:

```python
def _build_dense_composite_parent_candidates(...):
    ...  # visual-only, construction-time


def _score_dense_parent_candidate_against_local_ownership(...):
    ...  # arbitration-time, may consider coverage gain and unresolved reduction
```

Do not allow the build helper to depend on already-finalized unresolved buckets.

- [ ] **Step 4: Re-run the trigger/scoring tests**

Run the same slice and confirm green.

---

## 9. Task 6: Unified Sequence-Shell Accounting

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`, `paperforge/worker/ocr_figure_reader.py`
- Test: `tests/test_ocr_figures.py`, `tests/test_ocr_figure_reader.py`, maybe `tests/test_ocr_render.py`

- [ ] **Step 1: Write failing tests for assetless shell demotion**

Add tests shaped like:

```python
def test_assetless_sequence_shell_not_emitted_to_matched_figures() -> None:
    inventory = _promote_sequence_matches({...}, blocks=[])
    assert all(m.get("settlement_type") != "sequence_match" for m in inventory["matched_figures"])


def test_assetless_sequence_shell_emits_ambiguous_hold_reason() -> None:
    inventory = _promote_sequence_matches({...}, blocks=[])
    assert any(a.get("hold_reason") == "assetless_sequence_shell" for a in inventory["ambiguous_figures"])
```

If the current branch already keeps assetless sequence shells out of `matched_figures`, do not force a behavior rewrite.
Use this task to add explicit shell labeling and accounting only.

- [ ] **Step 2: Run the sequence-shell tests to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_figures.py tests/test_ocr_figure_reader.py -k "assetless_sequence_shell or sequence_match" -v --tb=short
```

- [ ] **Step 3: Demote shell outcomes without payload**

In `_promote_sequence_matches(...)`, enforce:

```text
no asset payload -> stay out of matched_figures
emit shell status into ambiguous/diagnostic surface instead
do not increment official_figure_count
```

Update reader handling only as needed so this new shell state remains render-safe and audit-visible.

- [ ] **Step 4: Re-run the sequence-shell tests**

Run the same slice and confirm green.

---

## 10. Task 7: VFS8CBW2-Class Dense Page Arbitration Regression

**Gate:** This is behavior-changing dense arbitration work and must be executed as a separate follow-up ticket.

Preconditions:

1. `P1A` diagnostic-only parent candidates are already stable
2. Task 1 metadata exists
3. Task 2 soft reservations exist
4. Task 4 and Task 5 have landed

If those conditions are not met, stop here.

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py` and real-paper validations

- [ ] **Step 1: Write failing synthetic dense-page arbitration tests**

Add the minimum family regressions:

```python
def test_dense_composite_parent_collects_large_fragment_set() -> None:
    ...


def test_dense_parent_does_not_swallow_neighboring_ordinary_figure() -> None:
    ...


def test_partial_same_page_claim_becomes_provisional_when_large_same_zone_leftovers_remain() -> None:
    ...
```

- [ ] **Step 2: Run the synthetic dense-page tests to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "dense_composite or provisional_when_large_leftovers" -v --tb=short
```

- [ ] **Step 3: Implement the arbitration rule, not a new settlement path**

Update same-page + parent arbitration flow so:

```text
partial local same-page ownership on dense pages is provisional
strong dense composite parent may outrank it if safe
the final accepted output still lands in existing matched_figures bucket
```

- [ ] **Step 4: Re-run synthetic dense-page tests**

Run the same slice and confirm green.

---

## 11. Task 8: Real-Paper Validation

**Files:**
- Modify: none unless a narrowly justified follow-up is required
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Run focused real-paper validation for capability families**

Run:

```bash
python -m pytest tests/test_ocr_real_paper_regressions.py -k "VFS8CBW2 or 6FGDBFQN or 2UIPV93M" -v --tb=short
```

Expected:

```text
no regression on 2UIPV93M scoped arbitration
no regression on 6FGDBFQN mixed grammar
VFS8CBW2 improves or at minimum stops overstating ownership via shell matches
```

- [ ] **Step 2: Run core figure stack verification**

Run:

```bash
python -m pytest tests/test_ocr_figures.py tests/test_ocr_figure_reader.py tests/test_ocr_render.py -q
```

Expected: green.

- [ ] **Step 3: Rebuild one live paper only after tests are green**

Run:

```bash
python -m paperforge --vault "D:/L/OB/Literature-hub" ocr rebuild VFS8CBW2
```

Expected manual checks afterward:

```text
fewer unresolved clusters on representative dense pages
panel-title blocks no longer compete as formal captions
no assetless sequence shell counted as strong match
```

---

## 12. Task 9: Documentation And Logging

**Files:**
- Modify: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Add a convergence entry after the code is verified**

Document:

```text
problem
root cause
fix
result
tests
```

Mention explicitly that this plan added convergence constraints rather than a new one-paper path.

---

## 13. Self-Review Against Spec

Coverage check:

1. OwnershipDecision adapter/mapping -> Task 1
2. provisional soft reservation semantics -> Task 2
3. panel-title suppression -> Task 3
4. dense parent as composite-parent subtype -> Task 4
5. trigger/scoring separation -> Task 5
6. assetless sequence-shell demotion -> Task 6
7. unified dense-page arbitration -> Task 7
8. relationship to existing roadmap -> enforced in Scope and Task constraints

Placeholder scan:

1. No `TBD` / `TODO`
2. Every task has exact file targets and commands
3. No step says “similar to previous task”

Type consistency check:

1. `ownership_decision` is internal metadata, not a replacement bucket
2. `composite_parent` remains the parent family; `dense_composite` is subtype only
3. `assetless_sequence_shell` is not allowed into `matched_figures`

---

## 14. Execution Recommendation

This plan should be executed in **small tickets**, not as one uninterrupted rewrite.

Suggested ticket order:

1. `Ticket A: Task 0 + Task 1 + Task 2 + Task 6`
2. `Ticket B: Task 3`
3. `Ticket C: Task 4 + Task 5` (only if `P1A` already exists)
4. `Ticket D: Task 7` (separate behavior-changing follow-up)
5. `Ticket E: Task 8 + Task 9`

This keeps the convergence work measurable and reversible.
