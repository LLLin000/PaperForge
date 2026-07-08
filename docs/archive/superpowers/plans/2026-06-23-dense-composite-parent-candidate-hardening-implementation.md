# Dense Composite Parent Candidate Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `VFS8CBW2` 这类 dense fragmented page 稳定地产生 audit-visible `composite_parent_candidates`，而不改变 ordinary same-page arbitration、sidecar、persisted buckets 或 direct settlement paths。

**Architecture:** 保持现有 atomic grouping 和 live `composite_parent` arbitration path 不动，只增强 Layer 2 candidate construction：把 unresolved visual mass 与 dense-page visual envelope 纳入 parent candidate 构造。这个 ticket 只解决“能不能看见 parent candidate”，不解决“最终谁赢”。

**Tech Stack:** Python, `pytest`, PaperForge OCR pipeline (`paperforge/worker/ocr_figures.py`), live-paper audit corpus (`VFS8CBW2`, `2UIPV93M`, `3FDT9652`, `24YKLTHQ`).

---

## 1. Scope And Hard Boundaries

This plan implements:

- `docs/superpowers/specs/2026-06-23-dense-composite-parent-candidate-hardening-design.md`

It must remain inside these boundaries:

1. Do **not** add or modify any `settlement_type`
2. Do **not** change ordinary same-page arbitration precedence
3. Do **not** modify sidecar behavior
4. Do **not** widen `_cluster_semantic_page_assets()` thresholds
5. Do **not** add literal label blacklists
6. Do **not** rewrite panel-title suppression; you may only read already-existing suppression results
7. Do **not** append dense parent candidates back into ordinary `candidate_groups`
8. Do **not** change persisted bucket semantics (`matched_figures`, `ambiguous_figures`, `unresolved_clusters`, etc.)

Success condition for this ticket:

```text
VFS8CBW2-class dense pages emit usable composite_parent_candidates,
while ordinary pages do not regress into page-wide mega-merge.
```

---

## 2. Files Expected To Change

Primary implementation:

- Modify: `paperforge/worker/ocr_figures.py`

Primary tests:

- Modify: `tests/test_ocr_figures.py`

Optional logging/doc update if findings materially sharpen strategy:

- Modify: `PROJECT-MANAGEMENT.md`

Real-paper verification targets:

- `VFS8CBW2`
- `2UIPV93M`
- `3FDT9652`
- `24YKLTHQ`

---

## 3. Task 0: Baseline Candidate Construction Audit

**Files:**
- Modify: none
- Verify: `paperforge/worker/ocr_figures.py`
- Test: none yet

- [ ] **Step 1: Record current dense-parent construction inputs**

Read and enumerate the current candidate-construction sources around:

```python
_build_candidate_figure_groups_from_assets(...)
_build_composite_parent_figure_groups_visual_only(...)
```

Record explicitly:

1. whether unresolved clusters are currently visible to parent construction
2. whether parent construction depends only on atomic groups
3. whether panel-title suppression output is readable at this stage

- [ ] **Step 2: Capture current VFS8CBW2 failure signature**

Run a lightweight inspection script or test helper showing, for pages `31/32/39/41`:

```text
matched_figures on page
composite_parent_candidates on page
unresolved_clusters on page
```

Expected baseline:

```text
composite_parent_candidates absent or insufficient on the worst dense pages
```

This step is evidence-only. No code changes.

---

## 4. Task 1: Write Failing Synthetic Dense-Candidate Tests

**Files:**
- Modify: `tests/test_ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Add a failing test for dense page parent candidate emission**

Add a synthetic page with:

1. one formal numbered figure caption
2. multiple visual fragments (`>= 4`)
3. one ordinary same-page local group that would only explain part of the page
4. extra unresolved visual mass in the same visual envelope

The test should assert:

```python
def test_dense_fragmented_page_emits_composite_parent_candidate() -> None:
    from paperforge.worker.ocr_figures import build_figure_inventory

    blocks = [
        # one numbered legend
        # several figure-like fragments arranged as one composite page
    ]

    inv = build_figure_inventory(blocks)
    dense_parents = [
        p for p in inv.get("composite_parent_candidates", [])
        if p.get("parent_subtype") == "dense_composite"
    ]

    assert dense_parents, "Dense fragmented page must emit a dense composite parent candidate"
```

- [ ] **Step 2: Add a failing ordinary-page guard test**

Add a second synthetic page with two independent numbered figures and assert no page-wide dense parent is emitted:

```python
def test_ordinary_multi_figure_page_does_not_emit_dense_parent() -> None:
    ...
```

- [ ] **Step 3: Add a failing unresolved-cluster visibility test**

Assert the parent candidate records `unresolved_cluster_ids` when unresolved visual mass participates:

```python
def test_dense_parent_candidate_records_unresolved_cluster_ids() -> None:
    ...
```

- [ ] **Step 4: Run the focused tests and confirm they fail for the right reason**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "dense_parent_candidate" -v --tb=short
```

Expected:

```text
FAIL because current candidate construction does not emit or annotate dense composite parent candidates strongly enough
```

---

## 5. Task 2: Strengthen Dense Candidate Construction Only

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Extend parent construction inputs without touching arbitration**

Enhance `_build_composite_parent_figure_groups_visual_only(...)` so it can incorporate:

1. atomic group envelopes
2. unresolved-cluster envelopes
3. dense-page fragment counts / compactness / grid-like structure

Implementation rule:

```text
The function may return richer composite_parent candidates,
but must not append to matched_figures, must not consume ownership,
and must keep ownership_enabled = False.
```

- [ ] **Step 2: Add dense-page trigger gating**

Only construct dense parent candidates when the page looks like a true dense composite page, using structural signals only.

Minimum signals to encode:

1. same-page numbered legend exists
2. fragment count high enough
3. unresolved / atomic fragments form compact local envelope
4. candidate does not look like page-wide scatter

- [ ] **Step 3: Add required candidate fields**

Ensure emitted parent candidates carry at least:

```python
parent_subtype = "dense_composite"
unresolved_cluster_ids = [...]
fragment_count = ...
atomic_child_count = ...
unresolved_child_count = ...
compactness = ...
grid_score = ...
construction_reason = [...]
ownership_enabled = False
```

- [ ] **Step 4: Re-run the focused synthetic tests**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "dense_parent_candidate" -v --tb=short
```

Expected:

```text
PASS
```

---

## 6. Task 3: Real-Paper Verification

**Files:**
- Modify: none unless test scaffolding is needed
- Verify: live artifacts and/or real-paper regression tests

- [ ] **Step 1: Verify VFS8CBW2 emits dense parent candidates on hot pages**

Use either fixture-backed replay or live artifact inspection to confirm pages `31/32/39/41` now contain non-empty `composite_parent_candidates`.

- [ ] **Step 2: Verify 2UIPV93M does not regress**

Confirm page 18 still keeps:

```text
图3 = same_page
图4 = composite_parent
```

- [ ] **Step 3: Verify ordinary papers do not page-merge**

Check at least:

1. `3FDT9652`
2. `24YKLTHQ`

Expected:

```text
No new page-wide mega-merge behavior
```

- [ ] **Step 4: Run the focused verification commands**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "dense_parent_candidate or composite_parent" -v --tb=short
python -m paperforge --vault "D:/L/OB/Literature-hub" ocr rebuild VFS8CBW2
python -m paperforge --vault "D:/L/OB/Literature-hub" ocr rebuild 2UIPV93M
```

Expected:

```text
VFS8CBW2 gains visible composite_parent_candidates on dense pages
2UIPV93M remains stable
```

---

## 7. Task 4: Logging And Stop Check

**Files:**
- Modify: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Record what changed and what did not**

Add one entry documenting:

1. the dense candidate-construction gap
2. the visual-only parent candidate hardening
3. that this ticket did **not** change arbitration precedence or sidecar
4. which real papers were used as success / guardrail checks

- [ ] **Step 2: Explicitly record stop-condition outcome**

Log whether any of these happened:

1. atomic grouping thresholds widened
2. new settlement path introduced
3. sidecar changed
4. bucket semantics changed

Expected:

```text
all remain unchanged
```

---

## 8. Self-Review Of Plan Against Spec

Coverage check:

1. Candidate construction only, not arbitration: covered by Tasks 0/2
2. Keep separate from ordinary `candidate_groups`: covered by Task 2 constraints
3. Use unresolved visual mass as input: covered by Task 1/2/3
4. Ordinary pages must stay stable: covered by Task 1 guard + Task 3 real-paper checks
5. No sidecar / bucket / settlement path rewrite: enforced in Scope And Hard Boundaries and Task 4 stop check

Placeholder scan:

1. No `TODO` / `TBD`
2. All test additions name concrete assertions
3. All verification steps include explicit commands

Type consistency:

1. Candidate subtype name fixed as `parent_subtype = "dense_composite"`
2. Candidate remains `group_type = "composite_parent"`
3. `ownership_enabled = False` preserved throughout the plan

No spec gap remains for this narrow ticket.

---

## 9. Execution Recommendation

This is already a small, executable ticket.

Recommended execution mode:

**1. Subagent-Driven (recommended)**
- one implementer
- one spec-boundary reviewer
- one code-quality reviewer

Do **not** combine this ticket with panel-title suppression changes, sidecar changes, or dense arbitration rollout.
