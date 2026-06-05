# OCR Phase Closure Cleanup Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining OCR stabilization gaps after the major figure/table remediation work, so the pipeline matches the intended contracts for title/frontmatter isolation, metadata cleanliness, formal-table downstream consumption, backmatter heading stability, and page-marker compatibility.

**Architecture:** This is a closure pass, not a redesign. The major object-detection and cropping fixes are already in place and working for `7C8829BD`. The remaining issues are downstream leaks and stale fallback logic: late-paper `paper_title` pollution, frontmatter blocks leaking into body render, physical table segments still being counted and displayed too literally downstream, unclean metadata display values, unstable backmatter heading handling on the tail pages, and page-marker compatibility still reporting a mismatch. This pass should only tighten those seams.

**Tech Stack:** Python, pytest, structured OCR artifacts, real-paper verification against `D:\L\OB\Literature-hub\System\PaperForge\ocr\7C8829BD`

---

## Root Cause Summary

The remaining problems come from six concrete causes:

1. [`ocr_roles.py`](D:/L/Med/Research/99_System/LiteraturePipeline/github-release/.worktrees/feat-ocr-structured-pipeline/paperforge/worker/ocr_roles.py:157)
   still allows page-1 zone heuristics plus generic unnumbered `paragraph_title` fallback to produce `paper_title` outside the real title object lifecycle.

2. [`ocr_render.py`](D:/L/Med/Research/99_System/LiteraturePipeline/github-release/.worktrees/feat-ocr-structured-pipeline/paperforge/worker/ocr_render.py:103)
   still renders blocks whose semantic content has already been consumed into the metadata block, so author/frontmatter material can appear twice.

3. [`ocr_tables.py`](D:/L/Med/Research/99_System/LiteraturePipeline/github-release/.worktrees/feat-ocr-structured-pipeline/paperforge/worker/ocr_tables.py:127)
   now models `formal_table_number` and `segments`, but downstream consumers such as health/render still mostly count or treat physical segment rows literally.

4. [`ocr_metadata.py`](D:/L/Med/Research/99_System/LiteraturePipeline/github-release/.worktrees/feat-ocr-structured-pipeline/paperforge/worker/ocr_metadata.py:80)
   accepts OCR author strings as-is, so metadata display still carries raw math-style affiliation markers and unclean join patterns.

5. [`ocr_render.py`](D:/L/Med/Research/99_System/LiteraturePipeline/github-release/.worktrees/feat-ocr-structured-pipeline/paperforge/worker/ocr_render.py:115)
   emits page markers only for rendered-page transitions, so the compatibility contract still drifts from `meta.page_count`.

6. [`ocr_roles.py`](D:/L/Med/Research/99_System/LiteraturePipeline/github-release/.worktrees/feat-ocr-structured-pipeline/paperforge/worker/ocr_roles.py:130)
   and [`ocr_render.py`](D:/L/Med/Research/99_System/LiteraturePipeline/github-release/.worktrees/feat-ocr-structured-pipeline/paperforge/worker/ocr_render.py:142)
   still lack a distinct backmatter-heading regime. Tail-page small headings are currently split between:
   - `frontmatter_noise` and therefore suppressed
   - generic `section_heading`
   - plain body paragraphs
   This makes the tail structure unstable for:
   - `Author contributions`
   - `Funding`
   - `Acknowledgments`
   - `Conflict of interest`
   - `Generative AI statement`
   - `References`
   - `Publisher's note`
   - `Supplementary material`

## Real-Paper Residual Issues To Eliminate

For `7C8829BD`, the following must be fixed:

1. `Generative AI statement` must not appear as a `paper_title` or title alternative.
2. author line must not reappear in body after already rendering in metadata.
3. `fulltext.md` must not contain raw inline `<table>...</table>` HTML.
4. health and downstream stats should distinguish formal table count from physical segment count.
5. page marker mismatch must disappear from `meta.error`.
6. metadata author display should be cleaner and less OCR-raw.
7. tail-page section structure should be explicit and stable.
8. `References` should render as a true heading, not as plain text or an accidental fallback.

## Task 1: Lock The Remaining Real-Paper Failures In Tests

**Files:**
- Modify: `tests/test_ocr_roles.py`
- Modify: `tests/test_ocr_rendering.py`
- Modify: `tests/test_ocr_metadata.py`
- Modify: `tests/test_ocr_health.py`
- Modify: `tests/test_ocr_render_stabilization.py`

- [ ] **Step 1: Add a failing late-paper-title pollution test**

Assert that:

- `Generative AI statement`
- `Acknowledgments`
- `Funding`
- `Conflict of interest`

cannot become `paper_title`.

- [ ] **Step 2: Add a failing frontmatter-duplication render test**

Assert that when authors are already emitted in the metadata block, the same frontmatter author block is not rendered again in body flow.

- [ ] **Step 3: Add a failing no-inline-table-html render test**

Assert that rendered `fulltext.md` contains object references for tables, not literal `<table>` HTML.

- [ ] **Step 4: Add a failing formal-table-vs-segment health test**

Assert that health can report formal table count distinctly from physical asset segments.

- [ ] **Step 5: Add a failing backmatter-heading render test**

Assert that end-of-article sections such as:

- `Author contributions`
- `Funding`
- `Acknowledgments`
- `Conflict of interest`
- `Generative AI statement`
- `References`

render with explicit section semantics instead of being suppressed or flattened.

- [ ] **Step 6: Add a failing page-marker compatibility test**

Assert that the rendered compatibility markdown has a marker count matching `page_count`.

- [ ] **Step 7: Run tests to confirm failure**

Run: `python -m pytest tests/test_ocr_roles.py tests/test_ocr_rendering.py tests/test_ocr_metadata.py tests/test_ocr_health.py tests/test_ocr_render_stabilization.py -q`

Expected: FAIL

## Task 2: Remove Residual `paper_title` Pollution

**Files:**
- Modify: `paperforge/worker/ocr_roles.py`
- Modify: `paperforge/worker/ocr_metadata.py`
- Test: `tests/test_ocr_roles.py`
- Test: `tests/test_ocr_metadata.py`

- [ ] **Step 1: Narrow `paper_title` admission**

Only allow `paper_title` from:

- trusted frontmatter title zone
- raw `doc_title`
- validated page-1 heading-like candidates that agree with source metadata

Do not allow later `paragraph_title` blocks to become `paper_title`.

- [x] **Step 2: Guard title alternatives against backmatter headings**

`resolve_metadata()` must not preserve OCR title alternatives that originate from late-paper backmatter sections.

- [ ] **Step 3: Verify**

Run: `python -m pytest tests/test_ocr_roles.py tests/test_ocr_metadata.py -q`

Expected: PASS

## Task 3: Fully Isolate Frontmatter From Body Render

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Possibly modify: `paperforge/worker/ocr_blocks.py`
- Test: `tests/test_ocr_rendering.py`
- Test: `tests/test_ocr_render_stabilization.py`

- [x] **Step 1: Identify already-consumed frontmatter blocks**

Once title/authors/doi/affiliations have been emitted into metadata or abstract sections, their corresponding raw blocks should not be rendered again in body flow.

- [x] **Step 2: Keep real body content untouched**

Do not over-suppress neighboring introduction/body blocks while removing duplicated frontmatter material.

- [ ] **Step 3: Verify**

Run: `python -m pytest tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py -q`

Expected: PASS

## Task 4: Add A Distinct Backmatter-Heading Regime

**Files:**
- Modify: `paperforge/worker/ocr_roles.py`
- Modify: `paperforge/worker/ocr_render.py`
- Test: `tests/test_ocr_roles.py`
- Test: `tests/test_ocr_rendering.py`
- Test: `tests/test_ocr_render_stabilization.py`

- [ ] **Step 1: Introduce an explicit `backmatter_heading` role**

This should cover end-of-article structural headings that are not frontmatter noise and not numbered body headings, including:

- `Author contributions`
- `Funding`
- `Acknowledgments`
- `Conflict of interest`
- `Generative AI statement`
- `Publisher's note`
- `Supplementary material`

- [ ] **Step 2: Use page-position and heading-profile evidence**

Do not classify these only by keyword membership.
Use:

- late-page position
- small-heading geometry
- spacing above/below
- consistency with nearby backmatter layout

- [ ] **Step 3: Render `backmatter_heading` explicitly**

Render as a stable heading level, not as body paragraph and not as suppressed noise.

- [ ] **Step 4: Render `reference_heading` as a true heading**

`References` should be emitted as a heading section, not plain text.

- [ ] **Step 5: Verify**

Run: `python -m pytest tests/test_ocr_roles.py tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py -q`

Expected: PASS

## Task 5: Finish Formal-Table Downstream Consumption

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Modify: `paperforge/worker/ocr_health.py`
- Possibly modify: `paperforge/worker/ocr_objects.py`
- Test: `tests/test_ocr_rendering.py`
- Test: `tests/test_ocr_health.py`

- [x] **Step 1: Make render consume formal table objects, not raw table HTML**

If a table has a formal object with image truth, `fulltext.md` should link/embed the table object instead of rendering assistive HTML.

- [x] **Step 2: Distinguish formal table count from segment count**

Health should be able to report:

- formal table count
- physical table segment count

without pretending they are the same thing.

- [x] **Step 3: Keep continuation display coherent**

Continuation segments should still map to the same formal table number downstream.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_ocr_rendering.py tests/test_ocr_health.py -q`

Expected: PASS

## Task 6: Clean Metadata Display Values

**Files:**
- Modify: `paperforge/worker/ocr_metadata.py`
- Possibly modify: `paperforge/worker/ocr_render.py`
- Test: `tests/test_ocr_metadata.py`

- [x] **Step 1: Add display-safe author normalization**

Normalize obvious OCR spacing artifacts in metadata-only contexts, especially:

- `$ ^{...} $ -> $^{...}$`
- missing spaces around `and`
- repeated raw OCR separator artifacts

This should improve metadata display without rewriting original body text.

- [x] **Step 2: Preserve raw author block separately**

Keep raw OCR frontmatter preserved for auditability even if display values are cleaned.

- [ ] **Step 3: Verify**

Run: `python -m pytest tests/test_ocr_metadata.py -q`

Expected: PASS

## Task 7: Restore Page-Marker Compatibility

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Possibly modify: `paperforge/worker/ocr.py`
- Test: `tests/test_ocr_render_stabilization.py`

- [ ] **Step 1: Emit one compatibility marker per page**

Even if a page only contributes figure/table objects or suppressed frontmatter, the compatibility output should still preserve marker coverage.

- [ ] **Step 2: Clear stale mismatch error when contract is satisfied**

Once the compatibility output is correct, `meta.error` should not keep reporting `page marker mismatch`.

- [ ] **Step 3: Verify**

Run: `python -m pytest tests/test_ocr_render_stabilization.py -q`

Expected: PASS

## Task 8: Real-Paper Closure Audit

**Files:**
- Verify only

- [ ] **Step 1: Rebuild `7C8829BD`**

Run the current derived rebuild/backfill path again.

- [x] **Step 2: Confirm metadata cleanup**

Check:

- no `Generative AI statement` title alternative
- authors present and display-clean enough

- [ ] **Step 3: Confirm render cleanup**

Check:

- no duplicated frontmatter author block in body
- no inline `<table>` HTML
- explicit tail-page headings render correctly
- `References` renders as a heading
- page markers cover all pages

- [ ] **Step 4: Confirm health/state cleanup**

Check:

- `references_found = true`
- `abstract_found = true`
- formal table handling reflected downstream
- `meta.error` no longer reports page marker mismatch

## Risks

1. Over-tightening title logic may accidentally drop valid page-1 titles in edge PDFs.
2. Frontmatter de-duplication may remove content that should remain visible if block provenance is not tracked carefully.
3. Removing inline table HTML may reduce text-only usefulness if object-note assistive content is not adequate.
4. Page-marker restoration may reintroduce noisy empty pages if done mechanically instead of compatibility-aware.
5. A new `backmatter_heading` regime may overfit this paper unless it is tied to geometry and position, not just keyword lists.
