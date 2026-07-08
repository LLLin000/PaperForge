# OCR Real-Paper Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the current anchor-first OCR v2 pipeline behave correctly on the five real-paper regression cases (`TSCKAVIS`, `CAQNW9Q2`, `A8E7SRVS`, `DWQQK2YB`, `M36WA39N`) by strengthening frontmatter-side authority, reference-zone closure, tail non-reference isolation, and display/table separation.

**Architecture:** This is not another architecture rewrite. It is a real-paper recovery pass on top of the landed anchor-first core. The plan focuses on the specific authority handoff that is still weak in production output: localized frontmatter truth must exclude body flow, reference-family evidence must close into `reference_zone`, and family partition results must become strong enough to keep tail/display/support blocks out of body rendering.

**Tech Stack:** Python 3, existing PaperForge OCR worker modules, PyMuPDF (`fitz`), pytest, real OCR vault at `D:\L\OB\Literature-hub`.

---

## File Map

- Modify: `paperforge/worker/ocr_document.py`
  - Zone inference, tail isolation, reference-zone closure, frontmatter-side exclusion.
- Modify: `paperforge/worker/ocr_families.py`
  - Family authority strengthening for support/display/reference-vs-body separation.
- Modify: `paperforge/worker/ocr_blocks.py`
  - Final orchestration and render/index gating after updated zoning/family authority.
- Modify: `paperforge/worker/ocr_roles.py`
  - Late role authority only if a real failure requires it; do not bloat speculatively.
- Modify: `paperforge/worker/ocr_render.py`
  - Only if body-flow suppression still leaks in render despite corrected roles/zones.
- Modify: `paperforge/worker/ocr_health.py`
  - Real-paper-specific authority signals if health must better expose recovery status.
- Modify: `tests/test_ocr_real_paper_regressions.py`
- Modify: `tests/test_ocr_document.py`
- Modify: `tests/test_ocr_families.py`
- Modify: `tests/test_ocr_integration_fixtures.py`

---

### Task 1: Lock the five real-paper failure classes in tests

**Files:**
- Modify: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write the failing tests**

Add real-paper assertions for these failure classes:

```python
def test_a8e7srvs_frontmatter_side_blocks_do_not_render_as_body(...):
    ...

def test_dwqqk2yb_preproof_followed_frontmatter_does_not_leak_into_body(...):
    ...

def test_m36wa39n_frontiers_editorial_furniture_is_not_body(...):
    ...

def test_tsckavis_table_caption_does_not_render_as_body_heading(...):
    ...

def test_reference_items_do_not_remain_in_body_zone_for_selected_real_papers(...):
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
`pytest tests/test_ocr_real_paper_regressions.py -v`

Expected:
- new real-paper assertions fail on the current branch behavior.

- [ ] **Step 3: Commit the failing test scaffold only after code is fixed**

Do not commit red-only state.

---

### Task 2: Make frontmatter-side zoning authoritative against body flow

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_families.py`
- Test: `tests/test_ocr_document.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Add focused failing tests for frontmatter-side exclusion**

```python
def test_frontmatter_side_candidates_are_not_left_as_body_paragraph_when_source_frontmatter_is_localized():
    ...
```

- [ ] **Step 2: Run focused test to verify failure**

Run:
`pytest tests/test_ocr_document.py -k "frontmatter_side" -v`

Expected:
- FAIL on current leakage.

- [ ] **Step 3: Implement minimal fix**

```python
# In zone inference / post-zone authority handoff:
# localized frontmatter-side blocks must not retain body-flow membership by default
```

- [ ] **Step 4: Run focused tests and real-paper regressions**

Run:
`pytest tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py -k "frontmatter or A8E7SRVS or DWQQK2YB or M36WA39N" -v`

Expected:
- PASS for the targeted frontmatter-side regressions.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_document.py paperforge/worker/ocr_families.py tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: isolate OCR frontmatter side zones"
```

---

### Task 3: Close reference-zone authority where reference items are already stable

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_families.py`
- Test: `tests/test_ocr_document.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write failing tests**

```python
def test_reference_zone_becomes_accept_when_reference_family_and_items_are_stable(...):
    ...

def test_reference_like_blocks_do_not_remain_in_body_zone_on_real_tail_pages(...):
    ...
```

- [ ] **Step 2: Run failing tests**

Run:
`pytest tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py -k "reference_zone or reference_like" -v`

Expected:
- FAIL on current weak closure behavior.

- [ ] **Step 3: Implement minimal fix**

```python
# Strengthen reference-zone closure from existing reference-family evidence
# without overfitting generic backmatter
```

- [ ] **Step 4: Re-run targeted tests**

Run:
`pytest tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py -k "reference_zone or TSCKAVIS or CAQNW9Q2 or DWQQK2YB or M36WA39N" -v`

Expected:
- PASS for reference-zone closure checks.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_document.py paperforge/worker/ocr_families.py tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: close OCR reference zones on real papers"
```

---

### Task 4: Keep tail non-reference headings and support blocks out of body

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_families.py`
- Test: `tests/test_ocr_document.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write failing tests**

```python
def test_tail_nonref_heading_does_not_collapse_to_body_paragraph(...):
    ...

def test_author_contributions_and_ethics_blocks_are_not_body_on_frontiers_real_paper(...):
    ...
```

- [ ] **Step 2: Run failing tests**

Run:
`pytest tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py -k "tail_nonref or author_contributions or ethics" -v`

Expected:
- FAIL on current tail leakage.

- [ ] **Step 3: Implement minimal fix**

```python
# Tail non-reference headings/support blocks should survive as non-body authority
# even when generic backmatter remains weakly typed.
```

- [ ] **Step 4: Re-run targeted tests**

Run:
`pytest tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py -k "tail_nonref or M36WA39N or DWQQK2YB" -v`

Expected:
- PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_document.py paperforge/worker/ocr_families.py tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: keep OCR tail support out of body flow"
```

---

### Task 5: Stop display/table insertions from acting like body headings

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_render.py`
- Test: `tests/test_ocr_document.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write failing tests**

```python
def test_tsckavis_table_caption_like_blocks_do_not_render_as_body_headings(...):
    ...
```

- [ ] **Step 2: Run failing tests**

Run:
`pytest tests/test_ocr_real_paper_regressions.py -k "TSCKAVIS or table_caption" -v`

Expected:
- FAIL on current display/body leakage.

- [ ] **Step 3: Implement minimal fix**

```python
# Ensure table/display family blocks are not emitted through body heading pathways.
```

- [ ] **Step 4: Re-run tests**

Run:
`pytest tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py -k "TSCKAVIS or table_caption or display" -v`

Expected:
- PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_document.py paperforge/worker/ocr_render.py tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: separate OCR display captions from body headings"
```

---

### Task 6: Run the exact five-paper rebuild verification and lock the recovery target

**Files:**
- Modify: `tests/test_ocr_real_paper_regressions.py`
- Optional docs note if needed: `docs/superpowers/specs/2026-06-10-ocr-real-paper-regression-ledger.md`

- [ ] **Step 1: Run the exact real-paper rebuild and regression set**

Run:
```bash
python -X utf8 -c "from pathlib import Path; from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys; vault=Path(r'D:\\L\\OB\\Literature-hub'); keys=['TSCKAVIS','CAQNW9Q2','A8E7SRVS','DWQQK2YB','M36WA39N']; print(run_derived_rebuild_for_keys(vault, keys))"
```

- [ ] **Step 2: Verify the repaired papers against targeted checks**

Run:
`pytest tests/test_ocr_real_paper_regressions.py -v`

Expected:
- targeted five-paper regressions pass or clearly identify any remaining residual blockers.

- [ ] **Step 3: Commit final recovery-test updates**

```bash
git add tests/test_ocr_real_paper_regressions.py docs/superpowers/specs/2026-06-10-ocr-real-paper-regression-ledger.md
git commit -m "test: lock OCR real-paper recovery cases"
```

---

## Self-review checklist

Before execution starts, verify:

1. This plan is driven by the five observed real-paper failures, not by generic OCR cleanup.
2. Each task maps to a real failure class from the regression ledger.
3. Frontmatter-side authority, reference-zone closure, tail non-reference isolation, and display/table separation are all explicitly covered.
4. No task quietly broadens into another architecture rewrite.
5. The exact five-paper rebuild command is included and preserved as final verification evidence.

---

**Plan complete and saved to `docs/superpowers/plans/2026-06-10-ocr-real-paper-recovery-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
