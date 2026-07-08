# OCR-v2 Merge-Gate Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clear the two remaining OCR-v2 merge-gate blockers, rerun the bounded regression surface, and leave a crisp closeout record so the branch can be merged with known scope.

**Architecture:** Treat this as a bounded stabilization pass, not a new OCR design phase. Work from the existing red tests in `tests/test_ocr_figures.py`, fix one failure family at a time in `paperforge/worker/ocr_figures.py`, then rerun the targeted and bounded real-paper surfaces before updating the narrative ledger.

**Tech Stack:** Python, pytest, PaperForge OCR strict figure inventory / reader pipeline.

---

## File Map

**Primary implementation files**
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `tests/test_ocr_figures.py`
- Modify: `PROJECT-MANAGEMENT.md`

**Verification surfaces**
- Read/Run: `tests/test_ocr_figure_reader.py`
- Read/Run: `tests/test_ocr_render.py`
- Read/Run: `tests/test_ocr_real_paper_regressions.py`
- Read/Run: `project/current/ocr-v2-active-queue.md`

**Current blocker tests already in repo**
- `tests/test_ocr_figures.py::test_same_number_ocr_minor_caption_variant_still_deduped`
- `tests/test_ocr_figures.py::test_table_labeled_img_figure_grids_still_separate_by_caption_when_caption_is_figure`

## Ground Rules

- Do not add new OCR feature families in this pass.
- Do not widen scope beyond the two known blockers unless the verification commands reveal a directly related regression.
- Do not commit, amend, or push unless the Overseer explicitly asks.
- Preserve the two green guardrails added on 2026-06-24:
  - `test_same_number_distinct_legends_can_both_match_separate_assets`
  - `test_same_number_distinct_legend_is_accounted_not_dropped`

---

### Task 1: Reproduce the Exact Merge-Gate State

**Files:**
- Read: `tests/test_ocr_figures.py`
- Read: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Confirm the worktree state before touching code**

Run:

```bash
git status --short
```

Expected:
- Existing unrelated changes may be present.
- `tests/test_ocr_figures.py` and `PROJECT-MANAGEMENT.md` should already be modified from the latest guardrail pass.

- [ ] **Step 2: Reproduce the current 2 green / 2 red merge-gate slice**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "same_number_distinct_legends_can_both_match_separate_assets or same_number_distinct_legend_is_accounted_not_dropped or same_number_ocr_minor_caption_variant_still_deduped or table_labeled_img_figure_grids_still_separate_by_caption_when_caption_is_figure" -q
```

Expected:
- `2 passed`
- `2 failed`
- Failing tests must be exactly:
  - `test_same_number_ocr_minor_caption_variant_still_deduped`
  - `test_table_labeled_img_figure_grids_still_separate_by_caption_when_caption_is_figure`

- [ ] **Step 3: Capture the failure text before editing**

Record in notes or scratchpad:
- For the dedup failure: current inventory incorrectly emits `same_number_distinct_legends` for punctuation-only drift.
- For the table-like failure: current inventory matches both captions to the top grid instead of splitting top/bottom grids.

Success condition:
- The agent has reproduced the exact known merge-gate state and can prove it with fresh output.

---

### Task 2: Fix Minor OCR Drift Dedup Without Breaking Real Distinct Captions

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Run the dedup blocker test alone**

Run:

```bash
python -m pytest tests/test_ocr_figures.py::test_same_number_ocr_minor_caption_variant_still_deduped -q
```

Expected:
- FAIL
- Failure should show punctuation-only drift being surfaced as `same_number_distinct_legends`.

- [ ] **Step 2: Inspect the dedup normalization path**

Read these functions in `paperforge/worker/ocr_figures.py`:
- `_strip_caption_number_prefix(...)`
- `_normalized_caption_body(...)`
- the `_dedup_map` / `_same_number_distinct_keys` block

Specifically inspect the code around:

```python
existing_body = _normalized_caption_body(str(existing.get("text", "")))
new_body = _normalized_caption_body(text)
```

Goal:
- Keep real body-vs-appendix distinct captions separate.
- Stop punctuation-only or trivial OCR drift from becoming a false distinct caption.

- [ ] **Step 3: Make the smallest safe normalization improvement**

Preferred shape:

```python
def _normalized_caption_body(text: str) -> str:
    body = _strip_caption_number_prefix(text).lower()
    body = re.sub(r"[\s\W_]+", " ", body).strip()
    return body
```

Acceptable alternatives:
- Strip terminal punctuation only, if that is enough to pass the test without collapsing meaning.
- Normalize common OCR punctuation drift with stdlib only.

Do not:
- Add fuzzy matching libraries.
- Add token similarity heuristics unless the smaller normalization fix is demonstrably insufficient.

- [ ] **Step 4: Re-run the single test**

Run:

```bash
python -m pytest tests/test_ocr_figures.py::test_same_number_ocr_minor_caption_variant_still_deduped -q
```

Expected:
- PASS

- [ ] **Step 5: Re-run the distinct-caption green guards**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "same_number_distinct_legends_can_both_match_separate_assets or same_number_distinct_legend_is_accounted_not_dropped or san9ayvr_fig26c_body_narrative or bundle_source_duplicate_loser_is_accounted_not_gap" -q
```

Expected:
- PASS
- No regression where real distinct captions collapse back into duplicate losers.

Success condition:
- Minor OCR drift dedups.
- Real distinct-caption scenarios still survive and stay accounted for.

---

### Task 3: Fix Table-Like Multi-Caption Grid Collapse

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Run the table-like blocker test alone**

Run:

```bash
python -m pytest tests/test_ocr_figures.py::test_table_labeled_img_figure_grids_still_separate_by_caption_when_caption_is_figure -q
```

Expected:
- FAIL
- Failure should show Figure 5 incorrectly owning `grid_top_left` / `grid_top_right` instead of the bottom grid.

- [ ] **Step 2: Inspect the figure matcher decision path**

Read these regions in `paperforge/worker/ocr_figures.py`:
- the strong `table_like` veto block in the same-page matcher
- the group scoring / candidate selection path
- any sequential or distance-cluster fallback that still admits table-labeled groups later

Focus question:
- Why does same-page matching skip or mis-score the bottom caption’s correct grid, then let later fallback reuse the top grid for both captions?

- [ ] **Step 3: Apply the smallest ownership-safe fix**

Target behavior:
- OCR `table_like` hints must not cause two numbered figure captions on the same page to collapse onto one shared image grid.
- The fix should preserve conservative figure/table separation.

Preferred directions, in order:
1. Respect caption-band / vertical ordering boundaries before sequential fallback can reuse an already more plausible grid.
2. Prevent group-sequential fallback from reusing the same asset group for a later caption when another nearer lower grid exists.
3. Narrow the table-like veto so it does not erase legitimate figure ordering evidence on multi-caption figure pages.

Do not:
- Remove the `table_like` guard wholesale.
- Add a new global matching mode.

- [ ] **Step 4: Re-run the single test**

Run:

```bash
python -m pytest tests/test_ocr_figures.py::test_table_labeled_img_figure_grids_still_separate_by_caption_when_caption_is_figure -q
```

Expected:
- PASS

- [ ] **Step 5: Re-run the existing table-like guardrails**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "figure_matcher_skips_strong_table_like_region or ambiguous_region_is_not_hard_forced or sidecar or ownership_conflicts" -q
```

Expected:
- PASS
- The fix must not regress conservative figure/table separation or sidecar behavior.

Success condition:
- Multi-caption table-labeled figure grids separate correctly by caption.
- The old strong table-like protection still works where intended.

---

### Task 4: Run the Bounded Merge-Gate Verification Surface

**Files:**
- Run: `tests/test_ocr_figures.py`
- Run: `tests/test_ocr_figure_reader.py`
- Run: `tests/test_ocr_render.py`
- Run: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Re-run the four-test merge-gate slice**

Run:

```bash
python -m pytest tests/test_ocr_figures.py -k "same_number_distinct_legends_can_both_match_separate_assets or same_number_distinct_legend_is_accounted_not_dropped or same_number_ocr_minor_caption_variant_still_deduped or table_labeled_img_figure_grids_still_separate_by_caption_when_caption_is_figure" -q
```

Expected:
- `4 passed`

- [ ] **Step 2: Re-run the bounded figure stack**

Run:

```bash
python -m pytest tests/test_ocr_figures.py tests/test_ocr_figure_reader.py tests/test_ocr_render.py -q
```

Expected:
- PASS, or only pre-existing known failures already documented in the repo.
- If there is a failure, stop and classify whether it is a direct consequence of the two fixes.

- [ ] **Step 3: Re-run the bounded real-paper regression surface**

Run:

```bash
python -m pytest tests/test_ocr_real_paper_regressions.py -k "6FGDBFQN or 2UIPV93M or VFS8CBW2 or RKSLQRIM or DWQQK2YB" -v --tb=short
```

Expected:
- PASS where fixtures are present.
- If some tests skip because fixtures are absent in the current worktree, record that explicitly instead of pretending they passed.

Success condition:
- The blockers are fixed.
- The bounded suite is green or any skips are honestly explained.

---

### Task 5: Close Out the Branch Handoff Cleanly

**Files:**
- Modify: `PROJECT-MANAGEMENT.md`

- [ ] **Step 1: Update the narrative ledger immediately after verification**

Add a new dated section to `PROJECT-MANAGEMENT.md` with:
- Problem
- Root cause
- Fix
- Result
- Exact test commands run and their status

The entry must say whether the real-paper regression command passed fully or was partially skipped due to fixture availability.

- [ ] **Step 2: Record remaining known issues precisely**

If everything is green:
- State that the branch is at merge-ready bounded scope.

If anything still fails:
- State the remaining blocker by test name and failure family.
- Do not use vague wording like “needs more work.”

- [ ] **Step 3: Produce the final handoff summary for the Overseer**

Use this structure in the response:

```markdown
Checked:
- <command>
- <command>

Fixed:
- <failure family>

Still blocked:
- <if none, say none>

Files changed:
- `paperforge/worker/ocr_figures.py`
- `tests/test_ocr_figures.py`
- `PROJECT-MANAGEMENT.md`

Merge recommendation:
- <merge now / hold for X>
```

Success condition:
- Another engineer can read the ledger and the final reply and know exactly whether the branch is merge-ready.

---

## Definition Of Done

This closeout is done only if all of the following are true:

1. `test_same_number_ocr_minor_caption_variant_still_deduped` passes.
2. `test_table_labeled_img_figure_grids_still_separate_by_caption_when_caption_is_figure` passes.
3. The two green distinct-caption guardrails still pass.
4. The bounded figure stack command has no new unexplained failures.
5. The bounded real-paper regression command is either green or honestly reported with explicit skips.
6. `PROJECT-MANAGEMENT.md` contains a fresh dated closeout entry.
7. No commit/push was performed unless explicitly requested by the Overseer.
