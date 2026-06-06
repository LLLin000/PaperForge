# OCR Document Analysis And Span Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the current OCR pipeline so the already-existing span metadata, tail-boundary logic, and second-pass cross-validation become one coherent document-analysis layer instead of scattered local heuristics.

**Architecture:** This plan starts from the code that already exists today. It does not rebuild OCR analysis from zero. The work is to extract document-level logic from `ocr_render.py`, extend current role profiles into section/family profiles, and upgrade the existing second pass in `ocr_blocks.py` from role-local adjustment to section-aware rescue.

**Tech Stack:** Python, existing worker modules (`ocr_blocks.py`, `ocr_roles.py`, `ocr_render.py`, `ocr_profiles.py`, `ocr_pdf_spans.py`, `ocr_rebuild.py`), pytest.

**Spec:** `docs/superpowers/specs/2026-06-06-ocr-unified-span-metadata-design.md`

---

## Current Baseline

The codebase already has substantial span/document-analysis infrastructure:

- `ocr_pdf_spans.py`
  - PDF-derived `span_metadata` extraction already exists
- `ocr_blocks.py`
  - raw/structured rows already carry `span_metadata`
  - a second pass already exists using `second_pass_cross_validate`
- `ocr_profiles.py`
  - role-level span profile and cross-validation helpers already exist
- `ocr_render.py`
  - document/tail logic already exists:
    - `TailBoundary`
    - body/backmatter/reference reconciliation
    - backmatter form classification
    - role normalization after boundary
- `ocr_figures.py`
  - candidate region computation and unresolved cluster groundwork already exist

So the real problem is not lack of machinery. The problem is that it is **fragmented**:

1. document structure logic is embedded in `ocr_render.py`
2. role logic still contains brittle remnants
3. second pass is not yet section-aware
4. span is used mostly as role-local validation, not as document-family reasoning

This plan is therefore a **consolidation plan**, not a greenfield plan.

---

## What Must Not Be Replanned

These are already in place and should be preserved:

- PDF-based span extraction as the source of truth
- carrying `span_metadata` in structured blocks
- current tail boundary reconciliation concepts
- unresolved multi-panel figure degradation instead of fake formal figures
- heuristic-first role assignment

This plan is not permission to throw those away.

---

## Main Gaps To Close

### Gap 1: Document analysis lives in the renderer

Today `ocr_render.py` is doing too much:

- detect body/backmatter/reference boundaries
- classify backmatter form
- normalize roles after the boundary
- order tail pages
- render markdown

This makes it hard for:

- roles
- metadata
- health
- index

to consume the same document structure.

### Gap 2: Second pass is role-local, not section-aware

`ocr_blocks.py` already has:

- first pass role assignment
- profile build
- second pass cross-validation

But it still lacks a real document-level context object.  
That means rescue logic cannot answer:

- “this block sits in references section”
- “this block sits after backmatter boundary”
- “this block is in first-page furniture zone”

### Gap 3: Hardcoded residual heuristics remain

Still risky today:

- backmatter boundary logic using relative page cutoff heuristics that are still too strong
- heading inference that still depends on font-size shortcuts and fallback thresholds
- frontmatter/noise logic still too text-heavy in places

### Gap 4: Profiles are still mostly role profiles, not family profiles

Useful OCR decisions often depend on family comparison:

- heading family vs body family
- frontmatter furniture family vs body family
- reference family vs body family
- caption family vs body family

The current code has pieces of this, but not as an explicit shared layer.

---

## Target End State

The end state should look like this:

1. `ocr_roles.py`
   - produces **high-confidence seed roles**
   - remains heuristic-first
   - no brittle absolute thresholds

2. `ocr_document.py`
   - owns document segmentation:
     - body end
     - backmatter start
     - references start
     - backmatter form
   - owns section/family profile building
   - owns rescue/demotion logic that needs section context

3. `ocr_profiles.py`
   - owns block-level span normalization
   - owns role/family profile aggregation
   - owns low-level cross-validation helpers

4. `ocr_render.py`
   - consumes final roles + document structure
   - renders only
   - does not rediscover structure from scratch

5. `ocr_rebuild.py`
   - emits `role_span_profiles.json`
   - eventually emits document-analysis artifacts if needed

---

## File Structure To Lock In

### `paperforge/worker/ocr_profiles.py`
Own:

- normalized block span profile extraction
- role-level profile aggregation
- family/profile comparison helpers
- profile-quality scoring

### `paperforge/worker/ocr_document.py`
Own:

- document boundary reconciliation
- backmatter form classification
- section-family profile construction
- section-aware rescue / demotion

### `paperforge/worker/ocr_roles.py`
Own only:

- seed-role assignment
- local heuristics
- no deep document-wide reconciliation

### `paperforge/worker/ocr_render.py`
Own only:

- ordering with already-prepared structure
- markdown emission

---

## Implementation Tasks

### Task 1: Extract document-structure logic out of `ocr_render.py`

**Files:**
- Create: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_document.py`
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_render.py`
- Test: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_document.py`
- Test: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_rendering.py`

- [ ] **Step 1: Write failing tests for document boundary object**

Add tests that assert a dedicated document-analysis module can produce:

- `body_end_page`
- `backmatter_start`
- `references_start`
- `spread_start`
- `spread_end`
- `backmatter_form`

Use synthetic examples for:

- flat backmatter
- container backmatter
- mixed tail spread

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
python -m pytest tests/test_ocr_document.py -q
```

Expected:

- FAIL because the document-analysis module does not yet exist.

- [ ] **Step 3: Move these functions into `ocr_document.py`**

Lift the existing logic out of `ocr_render.py`:

- `_detect_forward_body_end`
- `_detect_backward_backmatter_start`
- `_detect_references_start`
- `_reconcile_tail_spread`
- `_classify_backmatter_form`
- `_label_backmatter_regime`
- `_normalize_backmatter_roles_after_boundary`
- `_detect_frontmatter_zone` (zone classification logic)
- `_page_still_frontmatter` (already in `ocr_roles.py`, move here)

Do not change behavior yet beyond moving them and introducing a clearer public API:

```python
def analyze_document_structure(blocks: list[dict]) -> DocumentStructure
```

- [ ] **Step 4: Update `ocr_render.py` to consume the new API**

`ocr_render.py` should call the new document-analysis entry point instead of owning the discovery logic itself.

- [ ] **Step 5: Run tests**

Run:

```bash
python -m pytest tests/test_ocr_document.py tests/test_ocr_rendering.py -k "boundary or backmatter_form" -q
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_document.py paperforge/worker/ocr_render.py tests/test_ocr_document.py tests/test_ocr_rendering.py
git commit -m "refactor: extract OCR document structure analysis"
```

---

### Task 2: Clean `ocr_roles.py` into a true seed-role pass

**✅ ALREADY DONE — skip this task.**

Relevant commits:
- `f6b7f8b` — dynamic heading family discovery, removed `font_size >= 14` hard gate
- `976a073` — consolidated `is_visually_heading` in `_is_backmatter_boundary_heading`
- `c31137f` — added `_page_still_frontmatter()`, restricted text-based frontmatter noise rules
- `b2e1b65` — replaced `page_num == 1` hard gates with `_page_still_frontmatter()` dynamic check

Remaining hardcoded thresholds (if any) are minor and can be cleaned opportunistically during Task 3.

---

### Task 3: Upgrade current second pass into section-aware rescue

**Files:**
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_blocks.py`
- Modify: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\paperforge\worker\ocr_document.py`
- Test: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_document.py`
- Test: `D:\L\Med\Research\99_System\LiteraturePipeline\github-release\.worktrees\feat-ocr-structured-pipeline\tests\test_ocr_roles.py`

- [ ] **Step 1: Write failing tests for section-aware rescue**

Add tests covering:

- `frontmatter_noise` rescued to `body_paragraph` inside body section
- `body_paragraph` promoted to `reference_item` inside references zone
- weak heading demoted to body inside body family
- post-boundary child headings normalized to backmatter family

- [ ] **Step 2: Run tests**

Run:

```bash
python -m pytest tests/test_ocr_document.py tests/test_ocr_roles.py -k "rescue or demote or reference_zone or backmatter_child" -q
```

Expected:

- FAIL

- [ ] **Step 3: Replace `second_pass_cross_validate` as the primary second-pass entry**

Today `ocr_blocks.py` already does:

- first pass
- `build_role_span_profiles`
- `second_pass_cross_validate`

Keep that structure, but change the second pass entry to something like:

```python
rescue_roles_with_document_context(rows, role_profiles, document_structure, section_profiles)
```

This function should live in `ocr_document.py`.

- [ ] **Step 4: Add section-family profiles**

In `ocr_document.py`, add section/family profile building:

- body family
- heading family
- frontmatter furniture family
- backmatter heading family
- reference family
- caption family

These are in addition to role-level profiles, not a replacement.

- [ ] **Step 5: Run tests**

Run:

```bash
python -m pytest tests/test_ocr_document.py tests/test_ocr_roles.py -k "rescue or demote or reference_zone or backmatter_child" -q
```

Expected:

- PASS

- [ ] **Step 6: Commit**

```bash
git add paperforge/worker/ocr_blocks.py paperforge/worker/ocr_document.py tests/test_ocr_document.py tests/test_ocr_roles.py
git commit -m "feat: add section-aware OCR rescue pass"
```

---

### Task 4: Extend `ocr_profiles.py` from role profiles to family profiles

**✅ ALREADY DONE — skip this task.**

Relevant commits:
- `24f3e31` — `ocr_profiles.py` with `build_role_span_profiles`, `compare_against_role_family`, `cross_validate_with_span`
- `fc600fa` — cleanup and test tightening

`compare_against_role_family` already performs block-to-family comparison. `build_role_span_profiles` already aggregates by semantic role family. No additional family-profile abstraction is needed — the current API supports it directly.

The spec's section-family concepts (heading family vs body family) will be realized by passing the right block subsets into `build_role_span_profiles` during the section-aware rescue pass (Task 3).

---

### Task 5: Wire document-analysis artifacts into rebuild outputs

**✅ ALREADY DONE — skip this task.**

Relevant commits:
- `0ab9f7d` — `write_role_span_profiles` implemented, wired into both `ocr.py` and `ocr_rebuild.py`

`role_span_profiles.json` is already emitted during rebuild. Structured blocks already carry `span_metadata`. No additional artifact wiring is needed here.

---

### Task 6: Real-paper regression validation from current state

**Files:**
- Verify runtime artifacts only:
  - `D:\L\OB\Literature-hub\System\PaperForge\ocr\7C8829BD\`
  - `D:\L\OB\Literature-hub\System\PaperForge\ocr\2GN9LMCW\`

- [ ] **Step 1: Rebuild audit papers**

Run:

```bash
@'
from pathlib import Path
from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys, backfill_from_result
vault = Path(r'D:\L\OB\Literature-hub')
print(run_derived_rebuild_for_keys(vault, ['7C8829BD']))
print(backfill_from_result(vault, '2GN9LMCW'))
'@ | python -
```

- [ ] **Step 2: Run focused OCR suite**

Run:

```bash
python -m pytest tests/test_ocr_profiles.py tests/test_ocr_document.py tests/test_ocr_roles.py tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py tests/test_ocr_rebuild.py -q
```

Expected:

- PASS

- [ ] **Step 3: Manual audit**

Verify:

- `7C8829BD`
  - tail spread still correct
  - funding continuation still correct
  - references zone still stable
- `2GN9LMCW`
  - first-page authors/furniture still correct
  - unnumbered hierarchy still correct
  - declarations container still stable
  - no fake Figure 4 returns

- [ ] **Step 4: Commit**

```bash
git add paperforge/worker/ocr_blocks.py paperforge/worker/ocr_document.py paperforge/worker/ocr_profiles.py paperforge/worker/ocr_roles.py paperforge/worker/ocr_render.py paperforge/worker/ocr_rebuild.py tests/test_ocr_profiles.py tests/test_ocr_document.py tests/test_ocr_roles.py tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py tests/test_ocr_rebuild.py
git commit -m "feat: unify OCR document analysis with span validation"
```

---

## Coverage Checklist

- [X] the plan starts from current code, not from a greenfield architecture
- [X] PDF-based span extraction as source of truth
- [X] carrying `span_metadata` in structured blocks
- [X] current tail boundary reconciliation concepts
- [X] unresolved multi-panel figure degradation
- [X] heuristic-first role assignment
- [ ] document boundary logic is moved out of `ocr_render.py`
- [X] no absolute backmatter page gate remains — done in `f6b7f8b`, `c31137f`
- [X] no fixed font-size thresholds as primary heading rules — done in `f6b7f8b`
- [X] `span_metadata` stays a validator, not a standalone classifier
- [X] `role_span_profiles.json` emitted during rebuild — done in `0ab9f7d`
- [X] `compare_against_role_family` exists — done in `24f3e31`
- [ ] `ocr_roles.py` becomes a cleaner seed-role stage (partially done)
- [ ] current second-pass cross-validation becomes section-aware rescue
- [ ] `_page_still_frontmatter` moved to `ocr_document.py`
- [ ] current good behavior on `7C8829BD` and `2GN9LMCW` is preserved

