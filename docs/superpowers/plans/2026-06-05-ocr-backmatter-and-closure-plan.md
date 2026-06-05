# OCR Backmatter Tail-Ordering Closure Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the last unresolved OCR issues for `7C8829BD` by fixing tail-page ordering, section-body attachment, and references-zone attachment, without reopening the already-stable figure/table/frontmatter/cropping work.

**Architecture:** This is a narrow closure plan. Backmatter heading detection is already working well enough; the remaining bug is that tail-page blocks are rendered in the wrong structural order. The fix should happen as a dedicated `tail-page ordering` pass after role assignment but before final markdown emission. That pass should attach each `backmatter_body` to the correct `backmatter_heading`, keep `reference_item` blocks under `reference_heading`, and prevent tail sections like `Publisher's note` and `Supplementary material` from being interleaved incorrectly with references.

**Tech Stack:** Python, pytest, structured OCR artifacts, real-paper validation on `D:\L\OB\Literature-hub\System\PaperForge\ocr\7C8829BD`

---

## Already Complete

These are done and should not be reopened in this plan:

- frontmatter title/metadata block render
- abstract render
- figure 3/4 matching and crop recovery
- `assets/` truth + `images/` compatibility mapping
- inline raw `<table>` removal from `fulltext.md`
- formal table count vs segment count in health
- page-marker mismatch in `meta.error`
- backmatter headings are mostly recognized as headings

## Remaining Problems

For `7C8829BD`, the unresolved issues are now:

1. `Generative AI statement`, `References`, `Publisher's note`, and `Supplementary material` are still rendered in the wrong order.
2. Tail section bodies are not reliably attached to the heading that owns them.
3. Reference items start under the wrong heading region because the `References` zone boundary is not enforced strongly enough.

Current bad pattern in `fulltext.md`:

- `## Generative AI statement`
- `## References`
- `## Publisher's note`
- body for Generative AI statement
- body for Publisher's note
- `## Supplementary material`
- then references begin

This shows the problem is no longer role detection; it is tail-page structural ordering.

## Root Cause Summary

### 1. Tail-page reading order is missing

The current pipeline can recognize tail headings, but it still renders page 22 mostly in linear block order.

That is insufficient because the tail page mixes:

- left-column `References`
- right-column `Generative AI statement`
- right-column `Publisher's note`
- lower blocks for `Supplementary material`

These need explicit structural ordering, not naive per-block rendering.

### 2. Section-body attachment is missing

The renderer does not yet explicitly attach:

- `backmatter_body` -> nearest owning `backmatter_heading`
- `reference_item` -> active `reference_heading`

So the right bodies can drift beneath the wrong heading.

### 3. `References` needs a stronger section boundary

Once `reference_heading` appears, the renderer should open a `references zone` and keep subsequent `reference_item` blocks there unless a later tail heading clearly owns intervening non-reference text.

Right now, the boundary is too weak, so other tail headings can be emitted before references are laid down correctly.

## Target Tail Contract

For the tail portion of the paper, the rendered structure should become:

```md
## Author contributions
...

## Funding
...

## Acknowledgments
...

## Conflict of interest
...

## Generative AI statement
...

## Publisher's note
...

## Supplementary material
...

## References
...
```

Or, if the paper’s page-local structure clearly places `References` before certain later sections, the renderer should still maintain **section ownership consistency**:

- each heading immediately followed by its own body
- references grouped under `## References`
- no heading/body cross-wire

The strict requirement is not a fixed global tail order template.  
The strict requirement is **correct heading-body ownership plus a coherent references zone**.

## Task 1: Lock Tail-Ordering Failures In Tests

**Files:**
- Modify: `tests/test_ocr_rendering.py`
- Modify: `tests/test_ocr_render_stabilization.py`

- [ ] **Step 1: Add a failing heading-body attachment test**

Build a fixture with:

- `backmatter_heading("Generative AI statement")`
- its body block
- `reference_heading("References")`
- several `reference_item`
- `backmatter_heading("Publisher's note")`
- its body block

Expected:

- each heading is followed by its own body
- reference items stay grouped under `References`

- [ ] **Step 2: Add a failing tail mixed-column ordering test**

Model a page with:

- left-column `References`
- right-column `Generative AI statement`
- right-column `Publisher's note`
- lower `Supplementary material`

Expected:

- renderer does not interleave heading/body ownership incorrectly

- [ ] **Step 3: Run tests to confirm failure**

Run: `python -m pytest tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py -q`

Expected: FAIL

## Task 2: Add A Tail-Page Ordering Pass

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Possibly create helper logic inside `paperforge/worker/ocr_render.py`
- Test: `tests/test_ocr_rendering.py`

- [ ] **Step 1: Partition tail blocks before rendering**

For late pages containing any of:

- `backmatter_heading`
- `reference_heading`
- `reference_item`
- `backmatter_body`

collect them into a dedicated tail-page structure instead of rendering them one block at a time.

- [ ] **Step 2: Attach body blocks to the nearest valid owning heading**

Use page-local signals:

- same column or strong horizontal overlap
- closest heading above
- no stronger competing heading between them
- short vertical gap

Result:

- `Generative AI statement` body attaches to `Generative AI statement`
- `Publisher's note` body attaches to `Publisher's note`
- `Supplementary material` body attaches to `Supplementary material`

- [ ] **Step 3: Keep reference items in a dedicated references bucket**

If a block is `reference_item`, it should not be claimed by backmatter headings.

Reference items should be collected under the active `reference_heading`, even if nearby headings exist in another column.

- [ ] **Step 4: Render the ordered tail sections back into markdown**

The renderer should emit:

- heading
- attached body blocks

section by section, instead of by raw block sequence.

- [ ] **Step 5: Verify**

Run: `python -m pytest tests/test_ocr_rendering.py -q`

Expected: PASS

## Task 3: Strengthen The References Zone Boundary

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Possibly modify: `paperforge/worker/ocr_roles.py` only if a role distinction is missing
- Test: `tests/test_ocr_render_stabilization.py`

- [ ] **Step 1: Open a references zone on `reference_heading`**

When `reference_heading` appears:

- start a `references zone`
- collect `reference_item` blocks into it
- do not let generic body/backmatter ordering pull them elsewhere

- [ ] **Step 2: Allow later tail sections without stealing references**

If later headings like `Publisher's note` or `Supplementary material` exist:

- their own body blocks may render after their headings
- but `reference_item` blocks remain under `References`

- [ ] **Step 3: Verify**

Run: `python -m pytest tests/test_ocr_render_stabilization.py -q`

Expected: PASS

## Task 4: Real-Paper Closure Audit On `7C8829BD`

**Files:**
- Verify only

- [ ] **Step 1: Rebuild the real paper**

Run the current derived rebuild/backfill path for `7C8829BD`.

- [ ] **Step 2: Verify tail structure directly in `fulltext.md`**

Check:

- `## Author contributions`
- `## Funding`
- `## Acknowledgments`
- `## Conflict of interest`
- `## Generative AI statement`
- `## References`
- `## Publisher's note`
- `## Supplementary material`

all render as headings, and each body text sits under the correct heading.

- [ ] **Step 3: Verify reference grouping**

Check:

- first reference item appears under `## References`
- `Publisher's note` body is not attached to `Generative AI statement`
- `Supplementary material` body is not mixed into references

## Risks

1. A tail-page ordering pass can accidentally overfit this paper if implemented as a hardcoded heading order template instead of ownership-based grouping.
2. Column-aware attachment rules can misfire on unusual single-column tails unless horizontal/vertical evidence is balanced carefully.
3. References-zone grouping can become too strong if it swallows genuine later tail sections; keep grouping tied to `reference_item` roles only.
