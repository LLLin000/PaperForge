# OCR Real-Paper Full Closure Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `ocr-v2` from a strong transition build into a true anchor-first OCR v2 by fixing the remaining pipeline-order defects and then closing the real-paper failures on `TSCKAVIS`, `CAQNW9Q2`, `A8E7SRVS`, `DWQQK2YB`, and `M36WA39N`, including figure/legend/object loss.

**Architecture:** This is not another architecture rewrite, but it is broader than the first recovery pass. The branch now has signatures, anchors, zones, family partition, HOLD states, and richer health, but the core authority order is still partially inverted: eager role assignment still happens too early, source-backed frontmatter is not yet a first-class early pipeline stage, and family/zone artifacts do not consistently own final body/render behavior. This closure plan therefore runs in two stages: first correct the pipeline order and semantic authority seams, then close the remaining real-paper render/object failures.

**Tech Stack:** Python 3, existing PaperForge OCR worker modules, PyMuPDF (`fitz`), pytest, real OCR vault at `D:\L\OB\Literature-hub`.

---

## Scope Notes

- **Supersedes for execution purposes:**
  - `docs/superpowers/plans/2026-06-10-ocr-real-paper-recovery-plan.md`
  - the previous version of `2026-06-10-ocr-real-paper-full-closure-plan.md`
- **Evidence source remains:** `docs/superpowers/specs/2026-06-10-ocr-real-paper-regression-ledger.md`
- This plan explicitly incorporates the latest code-review conclusion:

```text
current state:
old eager-role pipeline
+ structural signatures
+ body/reference family anchors
+ region_bus
+ late role repair
+ figure/table HOLD

target state:
raw observations
-> structural signatures
-> source anchors / body family / reference family
-> zones
-> family partition
-> final role
-> figure/table validation
-> render
```

---

## File Map

- Modify: `paperforge/worker/ocr_blocks.py`
  - Split `seed_role` from final `role`, reorder orchestration, stop using eager role as the canonical first semantic truth.
- Modify: `paperforge/worker/ocr_roles.py`
  - Reduce `assign_block_role()` authority; keep only seed behavior. Expand `resolve_final_role()` into the true late authority entrypoint.
- Modify: `paperforge/worker/ocr_signatures.py`
  - Fix reference marker typing for old-style numbered references.
- Modify: `paperforge/worker/ocr_metadata.py`
  - Lift source-backed frontmatter localization into a true early anchor layer consumed by the main OCR pipeline.
- Modify: `paperforge/worker/ocr_document.py`
  - Make zones and boundary logic consume anchors before final roles; support same-page tail/reference split and final body-flow exclusions.
- Modify: `paperforge/worker/ocr_families.py`
  - Tighten family partition so non-body families do not survive as `body_paragraph` by default.
- Modify: `paperforge/worker/ocr_render.py`
  - Final markdown emission must honor frontmatter/display/tail authority instead of legacy role shortcuts.
- Modify: `paperforge/worker/ocr_figures.py`
  - Close legend/object completeness gaps; no silent legend loss, no silent figure disappearance.
- Modify: `paperforge/worker/ocr_objects.py`
  - Ensure rendered figure/table objects are complete, explain missing objects explicitly, and do not silently omit expected objects.
- Modify: `paperforge/worker/ocr_tables.py`
  - Keep table validation aligned with the new authority order as needed.
- Modify: `paperforge/worker/ocr_health.py`
  - Surface pipeline-order closure state and real-paper object completeness in health output.
- Modify: `tests/test_ocr_signatures.py`
- Modify: `tests/test_ocr_metadata.py`
- Modify: `tests/test_ocr_document.py`
- Modify: `tests/test_ocr_families.py`
- Modify: `tests/test_ocr_roles.py`
- Modify: `tests/test_ocr_figures.py`
- Modify: `tests/test_ocr_objects.py`
- Modify: `tests/test_ocr_tables.py`
- Modify: `tests/test_ocr_health.py`
- Modify: `tests/test_ocr_integration_fixtures.py`
- Modify: `tests/test_ocr_real_paper_regressions.py`

---

### Task 1: Expand and correct the real-paper regression matrix

**Files:**
- Modify: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write or tighten the failing tests**

Lock these currently real remaining failures:

```python
def test_tsckavis_key_points_render_as_callout(...):
    ...

def test_tsckavis_table_display_does_not_render_as_body_heading(...):
    ...

def test_caqnw9q2_old_style_references_gain_reference_like_family(...):
    ...

def test_m36wa39n_same_page_tail_nonref_and_references_split_correctly(...):
    ...

def test_real_paper_legends_do_not_silently_disappear_from_object_inventory(...):
    ...
```

Also keep the already-fixed frontmatter/reference-zone regressions green.

- [ ] **Step 2: Run the real-paper suite to confirm the current red set**

Run:
`pytest tests/test_ocr_real_paper_regressions.py -v`

Expected:
- the already fixed frontmatter/reference regressions stay green
- the remaining display/family/object failures stay red

- [ ] **Step 3: Do not commit a red-only change**

Commit this file only after the later code fixes are green.

---

### Task 2: Separate `seed_role` from final `role` in the pipeline

**Files:**
- Modify: `paperforge/worker/ocr_blocks.py`
- Modify: `paperforge/worker/ocr_roles.py`
- Test: `tests/test_ocr_roles.py`
- Test: `tests/test_ocr_integration_fixtures.py`

- [ ] **Step 1: Write failing tests**

```python
def test_build_structured_blocks_preserves_seed_role_and_leaves_final_role_unassigned_initially(...):
    ...

def test_pipeline_does_not_commit_final_semantic_role_before_zone_and_family_partition(...):
    ...
```

- [ ] **Step 2: Run focused tests to verify failure**

Run:
`pytest tests/test_ocr_roles.py tests/test_ocr_integration_fixtures.py -k "seed_role or unassigned" -v`

Expected:
- FAIL because `assign_block_role()` still writes directly into `row["role"]`.

- [ ] **Step 3: Implement minimal fix**

```python
# Keep eager assignment only as seed information:
row["seed_role"] = role.role
row["seed_confidence"] = role.confidence
row["seed_evidence"] = role.evidence

# final semantic role should remain delayed until late resolution
row["role"] = "unassigned"
```

Use a compatibility path only where absolutely necessary, and make the boundary explicit.

- [ ] **Step 4: Re-run focused tests**

Run:
`pytest tests/test_ocr_roles.py tests/test_ocr_integration_fixtures.py -k "seed_role or unassigned" -v`

Expected:
- PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_blocks.py paperforge/worker/ocr_roles.py tests/test_ocr_roles.py tests/test_ocr_integration_fixtures.py
git commit -m "refactor: split OCR seed and final roles"
```

---

### Task 3: Reorder the main OCR pipeline to signatures → anchors → zones → families → final role

**Files:**
- Modify: `paperforge/worker/ocr_blocks.py`
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_metadata.py`
- Test: `tests/test_ocr_integration_fixtures.py`
- Test: `tests/test_ocr_document.py`

- [ ] **Step 1: Write failing tests**

```python
def test_zone_and_family_partition_complete_before_final_role_resolution(...):
    ...

def test_source_backed_frontmatter_anchors_are_available_before_zone_inference(...):
    ...
```

- [ ] **Step 2: Run focused tests to verify failure**

Run:
`pytest tests/test_ocr_integration_fixtures.py tests/test_ocr_document.py -k "before_final_role or frontmatter_anchors" -v`

Expected:
- FAIL because current flow is still `assign_role -> normalize/rescue -> resolve_final_role -> refresh zones/families`.

- [ ] **Step 3: Implement minimal fix**

```python
# Required target order
raw observations
-> build_structural_signatures
-> source-backed frontmatter anchors
-> discover_body_family_anchor
-> discover_reference_family_anchor
-> infer_zones
-> partition_zone_families
-> resolve_final_role
```

Do not reintroduce a second “refresh” pass that makes zones/families post hoc.

- [ ] **Step 4: Re-run focused tests**

Run:
`pytest tests/test_ocr_integration_fixtures.py tests/test_ocr_document.py -k "before_final_role or frontmatter_anchors" -v`

Expected:
- PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_blocks.py paperforge/worker/ocr_document.py paperforge/worker/ocr_metadata.py tests/test_ocr_integration_fixtures.py tests/test_ocr_document.py
git commit -m "refactor: reorder OCR anchor-first pipeline"
```

---

### Task 4: Fix old-style numbered references at the signature layer

**Files:**
- Modify: `paperforge/worker/ocr_signatures.py`
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_families.py`
- Test: `tests/test_ocr_signatures.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write failing tests**

```python
def test_old_style_numbered_reference_is_typed_as_reference_numeric_dot(...):
    ...

def test_caqnw9q2_reference_items_gain_reference_like_family(...):
    ...
```

- [ ] **Step 2: Run focused tests to verify failure**

Run:
`pytest tests/test_ocr_signatures.py tests/test_ocr_real_paper_regressions.py -k "old_style or CAQNW9Q2 or reference_like" -v`

Expected:
- FAIL because `1 Author...` is still being typed as `heading_numbered` or left `unknown_like`.

- [ ] **Step 3: Implement minimal fix**

```python
# reference_numeric_dot / reference_numeric_parenthesis must be recognized
# before generic heading_numbered when the trailing text is citation-like.
```

- [ ] **Step 4: Re-run focused tests**

Run:
`pytest tests/test_ocr_signatures.py tests/test_ocr_real_paper_regressions.py -k "CAQNW9Q2 or reference_like or old_style" -v`

Expected:
- PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_signatures.py paperforge/worker/ocr_document.py paperforge/worker/ocr_families.py tests/test_ocr_signatures.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: type OCR old-style references as reference markers"
```

---

### Task 5: Make same-page tail non-reference and reference authority coexist block-locally

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_families.py`
- Test: `tests/test_ocr_document.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write failing tests**

```python
def test_tail_nonref_and_reference_can_coexist_on_same_page(...):
    ...

def test_m36wa39n_author_contributions_is_not_body_on_reference_page(...):
    ...
```

- [ ] **Step 2: Run focused tests to verify failure**

Run:
`pytest tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py -k "same_page or author_contributions or M36WA39N" -v`

Expected:
- FAIL on current mixed tail/reference ownership.

- [ ] **Step 3: Implement minimal fix**

```python
# Same-page top blocks like AUTHOR CONTRIBUTIONS / FUNDING / ACKNOWLEDGMENTS
# must keep non-body authority even when REFERENCES starts lower on the same page.
```

- [ ] **Step 4: Re-run focused tests**

Run:
`pytest tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py -k "same_page or M36WA39N or author_contributions or ethics" -v`

Expected:
- PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_document.py paperforge/worker/ocr_families.py tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: split OCR mixed tail and reference pages"
```

---

### Task 6: Make non-body families authoritative against final body flow

**Files:**
- Modify: `paperforge/worker/ocr_document.py`
- Modify: `paperforge/worker/ocr_blocks.py`
- Modify: `paperforge/worker/ocr_families.py`
- Test: `tests/test_ocr_document.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write failing tests**

```python
def test_body_paragraph_does_not_survive_when_style_family_is_reference_like(...):
    ...

def test_body_paragraph_does_not_survive_when_style_family_is_table_caption_like(...):
    ...

def test_problem_papers_do_not_keep_non_body_family_as_body_paragraph(...):
    ...
```

- [ ] **Step 2: Run focused tests to verify failure**

Run:
`pytest tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py -k "body_paragraph and style_family" -v`

Expected:
- FAIL for the residual `legend_like` / `table_caption_like` / `reference_like` body cases.

- [ ] **Step 3: Implement minimal fix**

```python
# Once a block is in a stable non-body family and not contradicted by stronger evidence,
# it must not remain ordinary body_paragraph in the final flow.
```

- [ ] **Step 4: Re-run focused tests**

Run:
`pytest tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py -k "style_family or body_paragraph" -v`

Expected:
- PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_document.py paperforge/worker/ocr_blocks.py paperforge/worker/ocr_families.py tests/test_ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: harden OCR family authority against body flow"
```

---

### Task 7: Honor frontmatter-side and display/table authority in final rendering

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Modify: `paperforge/worker/ocr_document.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write failing tests**

```python
def test_tsckavis_key_points_render_as_callout(...):
    ...

def test_tsckavis_table_display_does_not_render_as_body_heading(...):
    ...

def test_published_online_does_not_appear_in_heading_stream(...):
    ...
```

- [ ] **Step 2: Run focused tests to verify failure**

Run:
`pytest tests/test_ocr_real_paper_regressions.py -k "TSCKAVIS or key_points or table_display or published_online" -v`

Expected:
- FAIL.

- [ ] **Step 3: Implement minimal fix**

```python
# Render must honor display/frontmatter-side authority and stop routing
# display/table/frontmatter artifacts through body-heading pathways.
```

- [ ] **Step 4: Re-run focused tests**

Run:
`pytest tests/test_ocr_real_paper_regressions.py -k "TSCKAVIS or key_points or table_display or published_online" -v`

Expected:
- PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_render.py paperforge/worker/ocr_document.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: honor OCR display and frontmatter authority in render"
```

---

### Task 8: Close figure/legend/object completeness so figures are never silently dropped

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Modify: `paperforge/worker/ocr_objects.py`
- Modify: `paperforge/worker/ocr_health.py`
- Test: `tests/test_ocr_figures.py`
- Test: `tests/test_ocr_objects.py`
- Test: `tests/test_ocr_real_paper_regressions.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_real_paper_legends_do_not_disappear_without_object_accounting(...):
    ...

def test_figure_inventory_counts_matched_held_ambiguous_unresolved_consistently(...):
    ...

def test_figure_objects_exist_or_are_explicitly_unresolved_for_real_papers(...):
    ...
```

Specific failures this task must lock:
- a paper has multiple formal legends in `fulltext.md` but too few figure object notes in `render/figures/`
- one figure can disappear entirely, leaving only legends/orphans/unresolved with no explicit accounting
- `unresolved_cluster_count` may exist without enough object-level explanation for the missing figures

- [ ] **Step 2: Run focused tests to verify failure**

Run:
`pytest tests/test_ocr_figures.py tests/test_ocr_objects.py tests/test_ocr_real_paper_regressions.py -k "real_paper_legends or figure_inventory_counts or unresolved_cluster or render_figures" -v`

Expected:
- FAIL on current missing-figure/object-completeness cases.

- [ ] **Step 3: Implement minimal fix**

```python
# Every formal legend family outcome must become one explicit state:
# matched figure object / held figure / ambiguous figure / unresolved cluster / unmatched legend.
# No legend may disappear without inventory explanation.
```

- [ ] **Step 4: Re-run focused tests**

Run:
`pytest tests/test_ocr_figures.py tests/test_ocr_objects.py tests/test_ocr_real_paper_regressions.py -k "figure_inventory or unresolved or render_figures" -v`

Expected:
- PASS.

- [ ] **Step 5: Commit**

```bash
git add paperforge/worker/ocr_figures.py paperforge/worker/ocr_objects.py paperforge/worker/ocr_health.py tests/test_ocr_figures.py tests/test_ocr_objects.py tests/test_ocr_real_paper_regressions.py
git commit -m "fix: close OCR figure and legend object gaps"
```

---

### Task 9: Run the exact five-paper rebuild verification and lock the closure result

**Files:**
- Modify: `tests/test_ocr_real_paper_regressions.py`
- Optional note update: `docs/superpowers/specs/2026-06-10-ocr-real-paper-regression-ledger.md`

- [ ] **Step 1: Run the exact rebuild command on the five target papers**

Run:
```bash
python -X utf8 -c "from pathlib import Path; from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys; vault=Path(r'D:\L\OB\Literature-hub'); keys=['TSCKAVIS','CAQNW9Q2','A8E7SRVS','DWQQK2YB','M36WA39N']; print(run_derived_rebuild_for_keys(vault, keys))"
```

- [ ] **Step 2: Run the targeted real-paper regression suite**

Run:
`pytest tests/test_ocr_real_paper_regressions.py -v`

Expected:
- the five target paper regressions pass, or the output leaves only clearly documented residual failures outside this closure scope.

- [ ] **Step 3: Update ledger summary only if the failure picture materially changed**

```markdown
## Closure status
- fixed:
- remaining:
```

- [ ] **Step 4: Commit final recovery verification**

```bash
git add tests/test_ocr_real_paper_regressions.py docs/superpowers/specs/2026-06-10-ocr-real-paper-regression-ledger.md
git commit -m "test: verify OCR real-paper closure set"
```

---

## Self-review checklist

Before execution starts, verify:

1. The plan now fixes the pipeline-order defects called out in the review, not just the downstream symptoms.
2. `assign_block_role()` is no longer treated as the early semantic truth source in the target execution path.
3. Old-style numbered references, same-page tail/reference mixing, and figure/legend/object disappearance are all explicitly covered.
4. Figure/legend completeness is written as an explicit accounting contract, not just "improve matching".
5. The plan still stays on closure work and does not reopen a brand-new architecture redesign.

---

**Plan complete and saved to `docs/superpowers/plans/2026-06-10-ocr-real-paper-full-closure-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
