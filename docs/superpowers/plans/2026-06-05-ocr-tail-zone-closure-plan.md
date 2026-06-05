# OCR Tail Zone Closure Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the OCR stabilization work by closing the last tail-page issues: page-level noise band estimation, robust backmatter body attachment, and a true references-zone layout strategy for mixed tail pages such as `7C8829BD`.

**Architecture:** This is a narrow closure plan for the article tail only. Figure/table matching, cropping, frontmatter extraction, and formal object numbering are already stable enough and should not be reopened here. The remaining bug is that the renderer still treats the last pages too much like ordinary linear block streams. The fix is to add a page-regime-aware tail pass that first estimates `header/footer noise bands` from the whole paper, then identifies `usable content area`, then detects `references_zone` anchored by `reference_heading`, and only then attaches `backmatter_body` blocks to the correct `backmatter_heading`. In short: infer page structure first, then order/render the tail.

**Tech Stack:** Python, pytest, structured OCR artifacts, real-paper validation on `D:\L\OB\Literature-hub\System\PaperForge\ocr\7C8829BD`

---

## Scope

This plan only covers the remaining unresolved tail-page issues:

1. page-level noise band estimation
2. tail-page page regime classification
3. references-zone detection
4. backmatter heading/body ownership
5. tail render ordering

This plan must not reopen:

- figure/table matching
- crop coordinate handling
- frontmatter metadata block
- object note numbering
- formal table continuation model

## Current Residual Problems

For `7C8829BD`, the remaining problems are:

1. tail-page section bodies can still attach incorrectly if block order is unusual
2. `Supplementary material` body can disappear if a generic noise rule wins over tail-page ownership
3. mixed tail pages do not always behave like ordinary left-column-then-right-column pages
4. `References` on a mixed tail page should create its own independent zone instead of competing with nearby right-column backmatter sections

The key observation is that page 22 is not a normal two-column body page:

- left column lower half is `References`
- right column upper and middle contain `Generative AI statement`, `Publisher's note`, and `Supplementary material`
- page-local order must be inferred by region, not by one global left-to-right sort

## Desired Tail Strategy

The tail pass should behave like a human reading the page:

1. identify page-edge noise first
2. identify the usable content area
3. detect if this page is a mixed tail page
4. if `References` appears, build a `references_zone` below the `reference_heading`
5. keep reference items inside that zone, even if backmatter headings exist in another column
6. attach each remaining body block to the correct backmatter heading using geometry and ownership, not raw block sequence

## Page Geometry Strategy

### 1. Paper-Level Noise Bands

Use high-confidence raw/header/footer/page-number blocks across the whole paper to estimate:

- `header_band`
- `footer_band`

These are not deletion rules by themselves. They are geometry priors.

Use them to define:

- `usable_y_min`
- `usable_y_max`

Any tail-section body candidate should normally live within the usable content band, not in the header/footer bands.

### 2. Tail Page Regimes

A page near the document tail can be:

- `tail_sections_only`
- `reference_dominant`
- `tail_mixed_sections`

`tail_mixed_sections` applies when:

- there are one or more backmatter headings
- and there is also a `reference_heading` or dense `reference_item` block region

### 3. References Zone

`References zone` should be defined from the `reference_heading`, not from generic page order.

Rules:

- anchor at `reference_heading`
- include only blocks whose `y` is below the heading bottom
- include `reference_item` blocks across both columns
- exclude unrelated right-column tail bodies above or outside the zone

This means `References` becomes a structural region on the page, not just another heading in the generic sort order.

### 4. Backmatter Section Ownership

For backmatter headings such as:

- `Author contributions`
- `Funding`
- `Acknowledgments`
- `Conflict of interest`
- `Generative AI statement`
- `Publisher's note`
- `Supplementary material`

attach body blocks using:

- same-column or strong horizontal overlap
- body `y` below heading `y`
- body within usable content band
- no intervening stronger owning heading
- not inside `references_zone`

This is more robust than “nearest following block”.

## Render Contract

For a mixed tail page, render in section ownership order:

- `## <backmatter heading>`
- its body
- next `## <backmatter heading>`
- its body
- ...
- `## References`
- all reference items in the references zone

The exact global order across columns should follow the page’s actual structural ownership, not a rigid left-column-first template.

## Task 1: Lock The Tail-Zone Failures In Tests

**Files:**
- Modify: `tests/test_ocr_rendering.py`
- Modify: `tests/test_ocr_render_stabilization.py`
- Possibly modify: `tests/test_ocr_roles.py`

- [ ] **Step 1: Add a failing mixed-tail-page fixture**

Create a fixture with:

- one left-column `reference_heading`
- multiple left/right `reference_item` below it
- one right-column `Generative AI statement` heading + body above the reference zone
- one right-column `Publisher's note` heading + body
- one right-column `Supplementary material` heading + body

Assert that references do not steal the right-column section bodies and vice versa.

- [ ] **Step 2: Add a failing supplementary-material body ownership test**

Assert that a `Supplementary material` body block in the usable middle content band is rendered beneath that heading and is not suppressed as noise.

- [ ] **Step 3: Add a failing noise-band guard test**

Assert that blocks in the inferred footer/header band are treated as non-body candidates, but a middle-page section body is not suppressed just because it contains a weak noise phrase.

- [ ] **Step 4: Run tests to confirm failure**

Run: `python -m pytest tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py tests/test_ocr_roles.py -q`

Expected: FAIL

## Task 2: Add Paper-Level Noise Band Estimation

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Possibly add helper logic inside `paperforge/worker/ocr_render.py`
- Test: `tests/test_ocr_render_stabilization.py`

- [ ] **Step 1: Infer header/footer bands from the whole paper**

Use high-confidence blocks with roles such as:

- `noise`
- raw `header`
- raw `footer`
- raw `number`

Estimate a conservative:

- `header_band_max_y`
- `footer_band_min_y`

- [ ] **Step 2: Expose usable content band helpers**

Define helpers for:

- `is_in_header_band(block)`
- `is_in_footer_band(block)`
- `is_in_usable_content_band(block)`

- [ ] **Step 3: Use these only as geometric priors**

Do not delete blocks just because they are near a band. Use the bands to guide tail ownership and zone detection.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_ocr_render_stabilization.py -q`

Expected: PASS

## Task 3: Add `references_zone` Detection

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Test: `tests/test_ocr_rendering.py`

- [ ] **Step 1: Detect mixed tail pages**

A page is `tail_mixed_sections` if it contains:

- one or more `backmatter_heading`
- and a `reference_heading` or a dense reference area

- [ ] **Step 2: Build a references zone anchored at `reference_heading`**

Zone rules:

- `block.y1 >= reference_heading.y2`
- block role is `reference_item`
- allow both columns
- stop using these blocks for ordinary backmatter attachment

- [ ] **Step 3: Keep `reference_heading` structurally distinct**

`reference_heading` should start the references section but should not absorb unrelated right-column backmatter text above or outside the zone.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_ocr_rendering.py -q`

Expected: PASS

## Task 4: Add Robust Backmatter Body Ownership

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Possibly modify: `paperforge/worker/ocr_roles.py`
- Test: `tests/test_ocr_rendering.py`
- Test: `tests/test_ocr_roles.py`

- [ ] **Step 1: Attach tail bodies by geometry, not sequence**

For each `backmatter_heading`, candidate body blocks must satisfy:

- below the heading
- same column or strong horizontal overlap
- inside usable content band
- not inside references zone
- not intercepted by another nearer owning heading

- [ ] **Step 2: Demote generic noise phrase overrides inside tail ownership**

If a block clearly belongs to a backmatter section by geometry, do not let a weak noise phrase rule suppress it.

- [ ] **Step 3: Keep heading-body ownership local to the page**

Do not let one section steal bodies from a different column or from the references zone.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_ocr_rendering.py tests/test_ocr_roles.py -q`

Expected: PASS

## Task 5: Tail Render Reassembly

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Test: `tests/test_ocr_render_stabilization.py`

- [ ] **Step 1: Emit backmatter sections by ownership groups**

Each heading should be followed by its attached bodies.

- [ ] **Step 2: Emit references section by zone**

After section grouping, emit:

- `## References`
- then all `reference_item` in zone order

- [ ] **Step 3: Preserve earlier stable behavior**

Do not disturb:

- frontmatter
- main body pages
- figure/table placement
- page-marker compatibility

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_ocr_render_stabilization.py -q`

Expected: PASS

## Task 6: Real-Paper Closure Audit On `7C8829BD`

**Files:**
- Verify only

- [ ] **Step 1: Rebuild `7C8829BD`**

Run the current derived rebuild/backfill path again.

- [ ] **Step 2: Check page 22 specifically**

Expected:

- `## Acknowledgments` -> acknowledgment paragraph
- `## Conflict of interest` -> conflict paragraph
- `## Generative AI statement` -> AI statement paragraph
- `## Publisher's note` -> publisher note paragraph
- `## Supplementary material` -> supplementary material paragraph/link
- `## References` -> reference list

- [ ] **Step 3: Confirm no heading/body cross-wire**

Specifically:

- `This manuscript reflects only the authors' views...` must stay under `Funding`
- `The author(s) declare that no Generative AI...` must stay under `Generative AI statement`
- `All claims expressed...` must stay under `Publisher's note`
- supplementary material line must not disappear
- references must not start under `Supplementary material`

## Risks

1. A references zone that is too broad may swallow nearby right-column tail content.
2. A backmatter ownership rule that is too local may fail when the body text is offset but still clearly owned by a heading.
3. Noise-band estimation can become too aggressive if based on too few pages; keep it conservative and use it only as a prior.
