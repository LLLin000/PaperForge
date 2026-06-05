# OCR Formal Object Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the OCR formal-object pipeline so frontmatter, headings, figures, tables, continuation handling, and cropping all obey the new layer contracts, with `7C8829BD` as the real-paper acceptance target.

**Architecture:** Implement this as a layered remediation, not piecemeal patching. First stabilize role and frontmatter detection, then repair figure/table formal object detection, then continuation-aware matching, then keep cropping strictly subordinate to those matching decisions, and finally update object notes/render/health/index to consume the corrected outputs. The key rule is that identity and matching decisions belong upstream, while cropping and rendering are pure consumers.

**Tech Stack:** Python, pytest, Pillow, PyMuPDF/fitz, current OCR artifact pipeline, legacy OCR corpus at `D:\L\OB\Literature-hub`

---

## File Structure

- `paperforge/worker/ocr_roles.py`
  - repair title/frontmatter/reference/body-mention role logic
- `paperforge/worker/ocr_metadata.py`
  - lock metadata recovery to frontmatter analysis
- `paperforge/worker/ocr_figures.py`
  - split formal legends from body mentions and candidate legends
- `paperforge/worker/ocr_tables.py`
  - continuation-aware formal table model
- `paperforge/worker/ocr_objects.py`
  - keep cropping subordinate to matching; fix object note numbering/sections
- `paperforge/worker/ocr_render.py`
  - stop inline table HTML; consume corrected object notes
- `paperforge/worker/ocr_index.py`
  - keep body bucket free of figure/table prose confusion
- `paperforge/worker/ocr_health.py`
  - reflect stabilized references/tables/figures
- `paperforge/worker/ocr.py`
  - pass through required page-dimension/path-map context
- `paperforge/worker/ocr_rebuild.py`
  - make rebuild regenerate corrected inventories/assets/notes
- `tests/test_ocr_roles.py`
- `tests/test_ocr_metadata.py`
- `tests/test_ocr_figures.py`
- `tests/test_ocr_tables.py`
- `tests/test_ocr_objects.py`
- `tests/test_ocr_rendering.py`
- `tests/test_ocr_health.py`
- `tests/test_ocr_index.py`
- `tests/test_ocr_render_stabilization.py`

## Task 1: Lock The Real Failure Modes In Tests

**Files:**
- Modify: `tests/test_ocr_roles.py`
- Modify: `tests/test_ocr_figures.py`
- Modify: `tests/test_ocr_tables.py`
- Modify: `tests/test_ocr_rendering.py`
- Modify: `tests/test_ocr_render_stabilization.py`

- [ ] **Step 1: Add a failing body-mention vs formal-legend test**

Fixture:

- one prose block `Figure 3 shows ...`
- one true figure legend block on next page via `figure_title`
- one matching chart asset

Expected:

- prose block becomes `body_figure_mention` or body paragraph
- true legend becomes the formal legend

- [ ] **Step 2: Add a failing legend-only no-orphan-substitution test**

Expected:

- a `legend_only` figure object keeps no asset
- object-writing layer does not pull in arbitrary `unmatched_assets`

- [ ] **Step 3: Add a failing table-continuation merge test**

Fixture:

- `Table 6`
- `Table 6 (Continued)`
- two page-local assets

Expected:

- one formal table object
- two physical segments

- [ ] **Step 4: Add a failing render test for inline table HTML**

Expected:

- `fulltext.md` does not contain raw `<table>` HTML
- table object references appear instead

- [ ] **Step 5: Run the focused failures**

Run: `python -m pytest tests/test_ocr_roles.py tests/test_ocr_figures.py tests/test_ocr_tables.py tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py -q`

Expected: FAIL

## Task 2: Repair Frontmatter And Heading Semantics

**Files:**
- Modify: `paperforge/worker/ocr_roles.py`
- Modify: `paperforge/worker/ocr_metadata.py`
- Test: `tests/test_ocr_roles.py`
- Test: `tests/test_ocr_metadata.py`

- [ ] **Step 1: Remove unsafe `paragraph_title -> paper_title` fallback**

Replace with page-1/title-zone-only admission.

- [ ] **Step 2: Add explicit `reference_content` handling**

Map OCR `reference_content` to `reference_item`.

- [ ] **Step 3: Split body references to figures from formal legends**

Add explicit exclusion for patterns like:

- `Figure 3 shows`
- `Figure 2 illustrates`
- `Figure 4 depicts`

- [ ] **Step 4: Tighten `text -> heading` promotion**

Only allow under strong geometric/profile conditions.

- [ ] **Step 5: Verify**

Run: `python -m pytest tests/test_ocr_roles.py tests/test_ocr_metadata.py -q`

Expected: PASS

## Task 3: Rebuild Formal Figure Detection And Matching

**Files:**
- Modify: `paperforge/worker/ocr_figures.py`
- Possibly modify: `paperforge/worker/ocr_roles.py`
- Test: `tests/test_ocr_figures.py`

- [ ] **Step 1: Introduce explicit figure categories**

Represent:

- formal legend
- candidate legend
- body mention
- matched figure
- legend-only figure
- orphan asset

- [ ] **Step 2: Restore the old prose exclusion guard**

The new pipeline should incorporate `master`’s anti-body-reference logic into the formal legend path.

- [ ] **Step 3: Remove orphan substitution for legend-only figures**

If no asset is matched, keep the figure assetless.

- [ ] **Step 4: Keep unmatched legends/assets honest**

Populate `unmatched_legends` and `unmatched_assets` truthfully.

- [ ] **Step 5: Verify**

Run: `python -m pytest tests/test_ocr_figures.py -q`

Expected: PASS

## Task 4: Rebuild Formal Table Detection With Continuation

**Files:**
- Modify: `paperforge/worker/ocr_tables.py`
- Modify: `paperforge/worker/ocr_objects.py`
- Test: `tests/test_ocr_tables.py`
- Test: `tests/test_ocr_objects.py`

- [ ] **Step 1: Add formal number + continuation model**

Each table object should carry:

- `formal_table_number`
- `segments`
- `is_continuation`
- `continuation_of`

- [ ] **Step 2: Merge `Table N (Continued)` into the prior formal table**

Do not create a new displayed formal number.

- [ ] **Step 3: Make object note title use formal table number**

Avoid `table_007 -> # Table 7` if the formal caption is `Table 6`.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_ocr_tables.py tests/test_ocr_objects.py -q`

Expected: PASS

## Task 5: Keep Cropping Strictly Subordinate To Matching

**Files:**
- Modify: `paperforge/worker/ocr_objects.py`
- Modify: `paperforge/worker/ocr_blocks.py`
- Modify: `paperforge/worker/ocr.py`
- Modify: `paperforge/worker/ocr_rebuild.py`
- Test: `tests/test_ocr_objects.py`

- [ ] **Step 1: Preserve OCR page dimensions into structured blocks**

Do not drop `page_width` / `page_height`.

- [ ] **Step 2: Prefer cached OCR page images for crop**

Use `pages/page_XXX.(jpg|png)` first, then render-to-OCR-size fallback.

- [ ] **Step 3: Ensure cropping does not modify matching outcome**

No reassignment of bbox ownership inside cropping/object-writing.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_ocr_objects.py -q`

Expected: PASS

## Task 6: Render And Index Consumption Cleanup

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Modify: `paperforge/worker/ocr_index.py`
- Modify: `paperforge/worker/ocr_health.py`
- Test: `tests/test_ocr_rendering.py`
- Test: `tests/test_ocr_index.py`
- Test: `tests/test_ocr_health.py`

- [ ] **Step 1: Remove inline table HTML from `fulltext.md`**

Use table object references instead.

- [ ] **Step 2: Make body bucket ignore formal figure/table prose confusion**

Do not let formal captions or body mentions pollute the wrong index buckets.

- [ ] **Step 3: Make health reflect reference/content correctness**

Verify `references_found` once `reference_content` is mapped.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_ocr_rendering.py tests/test_ocr_index.py tests/test_ocr_health.py -q`

Expected: PASS

## Task 7: Real-Paper Verification On `7C8829BD`

**Files:**
- Verify only

- [ ] **Step 1: Rebuild the real paper**

Run the corrected backfill / derived rebuild path on `7C8829BD`.

- [ ] **Step 2: Verify figure behavior**

Expected:

- Figure 3 asset is the page-11 chart, not page-10 prose
- Figure 4 asset is the page-14 chart
- no `Check for updates` figure fallback

- [ ] **Step 3: Verify table continuation behavior**

Expected:

- page 15 and 16 remain formal Table 6
- page 19 remains formal Table 7
- object-note display numbering follows formal table number

- [ ] **Step 4: Verify render behavior**

Expected:

- no inline table HTML in `fulltext.md`
- table object links instead

## Task 8: Final Verification

**Files:**
- Verify only

- [ ] **Step 1: Run focused suite**

Run: `python -m pytest tests/test_ocr_roles.py tests/test_ocr_metadata.py tests/test_ocr_figures.py tests/test_ocr_tables.py tests/test_ocr_objects.py tests/test_ocr_rendering.py tests/test_ocr_health.py tests/test_ocr_index.py tests/test_ocr_render_stabilization.py -q`

Expected: PASS

- [ ] **Step 2: Run real-paper smoke checks**

Expected:

- assets are correct
- numbering is correct
- no orphan substitution regression

## Risks

1. Removing body-mention legends may reduce figure recall if candidate-legend logic is too weak.
2. Table continuation merging may accidentally over-merge distinct same-number supplements if numbering context is weak.
3. Render cleanup may break existing downstream consumers expecting inline table HTML.
4. Real-paper validation must confirm that formal-number display stays correct after continuation merging.
