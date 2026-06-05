# OCR Tail Regime Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate the remaining OCR tail-page layout corruption by introducing a bidirectional body/backmatter boundary detector, a multi-page tail-spread regroup pass, a first-class references zone, and PDF-style-assisted unnumbered heading discrimination, while cleaning out obsolete text-first noise checks.

**Architecture:** The current failures are no longer in the main OCR pipeline. They are concentrated in the late-body / backmatter transition. The fix should not add paper-specific text rules. Instead, it should change the decision hierarchy:

1. estimate paper-level edge noise bands
2. parse the main body from front to back
3. parse the backmatter from back to front
4. reconcile those into a tail spread
5. carve out a references zone inside that spread
6. attach tail bodies by ownership
7. use PDF style signals only to disambiguate ambiguous unnumbered headings
8. render the resolved tail structure

This keeps the solution structural rather than lexical.

**Tech Stack:** Python, pytest, structured OCR artifacts, PyMuPDF span metadata, real-paper validation on `D:\L\OB\Literature-hub\System\PaperForge\ocr\7C8829BD`

---

## Current Failure

The current output for `7C8829BD` still shows a layout corruption around `Funding`:

- ordinary late-body conclusion text is rendered under `## Funding`
- the real funding continuation from page 22 is separated from `Funding`

This means two things are still wrong:

1. late-body text is being allowed into the tail candidate pool too easily
2. cross-page backmatter continuation is not modeled strongly enough

At the same time, some prior noise suppression has already been reduced enough that `Supplementary material` content can appear again. So the next fix should not be “add more text rules”. It should tighten the regime.

## Root Cause

### 1. Tail ownership is decided too early

In the current flow, late `text` blocks can still become `tail_candidate_body` just because they appear on a page that also contains backmatter headings. That is too broad.

### 2. There is no explicit body-end / backmatter-start reconciliation

The current system still lacks a true shared boundary between:

- forward main-body parsing
- backward backmatter parsing

So the last pages are not being split cleanly into:

- still-body
- tail spread

### 3. Tail handling is still too page-local

This paper needs a spread-level interpretation of pages 21–22:

- `Funding` starts on page 21
- funding continuation is on page 22
- `References` begins on page 22 as an independent region

A page-local grouping pass cannot resolve that reliably.

### 4. Residual text-based noise checks are still too influential

Some old text-based noise checks still exist in `ocr_roles.py`. Even when they no longer dominate every case, they still complicate the regime and should be demoted or removed where they overlap with tail ownership.

### 5. Unnumbered heading hierarchy still needs style support

For papers like:

- `Mobini 2017`
- `Fitzsimmons 2008`

unnumbered headings differ by:

- size
- font family
- bold/italic flags
- color

If the system only uses text and geometry, these headings will collapse too easily into one level.

## Design Changes

## A. Body And Backmatter Must Be Parsed From Opposite Directions

### Forward body spine

Parse from the front:

- stable numbered headings
- stable subsection headings
- body paragraph continuity
- body-local spacing

Output:

- conservative `body_end_candidate`

### Backward backmatter spine

Parse from the end:

- `reference_heading`
- dense `reference_item`
- `backmatter_heading`
- compact tail section bodies

Output:

- conservative `backmatter_start_candidate`

### Boundary reconciliation

If these two boundaries overlap or nearly touch, define a `tail spread` rather than forcing a hard single-page cutoff.

Only blocks inside or after that reconciled spread should enter tail ownership logic.

## B. Tail Candidate Generation Must Be Narrower

`tail_candidate_body` should not mean:

- “any long text on a page that also contains backmatter headings”

It should mean:

- a late-page text block in the reconciled tail spread
- that is not already part of the stable forward body spine
- and is geometrically plausible as a tail-owned body block

This avoids swallowing ordinary late conclusion text.

## C. References Must Be A Region, Not Just A Heading

`reference_heading` must create a `references_zone`:

- anchored at the heading
- extending downward
- containing `reference_item`
- spanning both columns if necessary

Blocks in this zone must be protected from backmatter ownership.

## D. Backmatter Ownership Must Be Spread-Level

Backmatter bodies should be assigned using:

- below-heading geometry
- same-column preference
- horizontal overlap
- cross-page continuation allowance
- exclusion from references zone

This is especially needed for `Funding` continuation from page 21 to page 22.

## E. Noise Must Become Geometry-First

Strong noise should be limited to:

- raw `header`
- raw `footer`
- raw `number`
- edge-band artifacts

Text-triggered noise checks should be:

- removed if redundant
- or demoted to weak fallback only after regime/ownership decisions

This prevents noise heuristics from competing with tail structure.

## F. Style Must Assist Unnumbered Heading Levels

Use PDF span metadata where available:

- `size`
- `font`
- `flags`
- `color`
- line bbox height

Build paper-local style profiles for:

- primary headings
- subsection headings
- backmatter headings
- sidebar/frontmatter furniture

Style is a supporting signal only. Geometry and regime still come first.

## Task 1: Lock The Mechanism Failure In Tests

**Files:**
- Modify: `tests/test_ocr_roles.py`
- Modify: `tests/test_ocr_rendering.py`
- Modify: `tests/test_ocr_render_stabilization.py`

- [ ] **Step 1: Add a failing tail-candidate-overreach test**

Fixture:

- late body paragraphs on a page that also contains backmatter headings
- true backmatter heading/body on the same page

Expected:

- ordinary late body paragraphs do not become tail-owned blocks

- [ ] **Step 2: Add a failing cross-page funding continuation test**

Fixture:

- `Funding` heading on page N
- funding body continues on page N+1
- references also begin on page N+1

Expected:

- continuation remains under `Funding`
- references stay in `References`

- [ ] **Step 3: Add a failing style-aware unnumbered heading test**

Fixture:

- two unnumbered headings with distinct visual style
- one body block with ordinary body style

Expected:

- headings do not flatten into one generic level by text alone
- body block is not promoted to heading

- [ ] **Step 4: Run tests to confirm failure**

Run: `python -m pytest tests/test_ocr_roles.py tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py -q`

Expected: FAIL

## Task 2: Add Bidirectional Body/Backmatter Boundary Detection

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Possibly add helper functions there
- Test: `tests/test_ocr_render_stabilization.py`

- [ ] **Step 1: Implement forward body spine detection**

Detect a conservative `body_end_candidate` using:

- stable body headings
- subsection continuity
- paragraph flow

- [ ] **Step 2: Implement backward backmatter spine detection**

Detect a conservative `backmatter_start_candidate` using:

- `reference_heading`
- dense references
- backmatter headings
- short tail bodies

- [ ] **Step 3: Reconcile into a tail spread**

Only blocks inside or after the reconciled spread should enter tail regroup logic.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_ocr_render_stabilization.py -q`

Expected: PASS

## Task 3: Move Tail Ownership Out Of The Base Role Layer

**Files:**
- Modify: `paperforge/worker/ocr_roles.py`
- Test: `tests/test_ocr_roles.py`

- [ ] **Step 1: Narrow `tail_candidate_body` generation**

Require:

- tail-spread context
- not already stable forward-body content
- plausible geometry for owned tail text

- [ ] **Step 2: Remove or demote obsolete text-first noise checks**

Keep strong noise only for:

- header/footer/page number
- obvious edge-band artifacts

Demote tail-overlapping text phrases to weak fallbacks.

- [ ] **Step 3: Preserve first-page frontmatter behavior**

Do not regress existing frontmatter filtering.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_ocr_roles.py -q`

Expected: PASS

## Task 4: Add Spread-Level Tail Ownership And References Zone

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Test: `tests/test_ocr_rendering.py`
- Test: `tests/test_ocr_render_stabilization.py`

- [ ] **Step 1: Build a first-class `references_zone`**

Rules:

- anchor at `reference_heading`
- include `reference_item`
- may span both columns
- protect from backmatter ownership

- [ ] **Step 2: Attach backmatter bodies by spread-level ownership**

Use:

- nearest valid heading above
- same-column preference
- cross-page continuation allowance
- references-zone exclusion

- [ ] **Step 3: Emit groups instead of raw block order**

Render:

- heading
- owned bodies
- references zone

not raw block sequence.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_ocr_rendering.py tests/test_ocr_render_stabilization.py -q`

Expected: PASS

## Task 5: Add Style-Aware Heading Profiles

**Files:**
- Modify: `paperforge/worker/ocr_render.py`
- Possibly add helper extraction logic
- Test: `tests/test_ocr_roles.py`
- Test: `tests/test_ocr_rendering.py`

- [ ] **Step 1: Extract PDF style metadata where available**

Support:

- size
- font family/name
- bold/italic flags
- color

- [ ] **Step 2: Build local heading style profiles**

For:

- body headings
- subsection headings
- backmatter headings

- [ ] **Step 3: Use style only for disambiguation**

Style should help separate ambiguous unnumbered headings, not replace geometry/regime.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_ocr_roles.py tests/test_ocr_rendering.py -q`

Expected: PASS

## Task 6: Real-Paper Verification

**Files:**
- Verify only

- [ ] **Step 1: Rebuild `7C8829BD`**

Run the derived rebuild/backfill path again.

- [ ] **Step 2: Verify the page 21–22 spread**

Expected:

- ordinary late body text stays in the conclusion
- `Author contributions` only owns contribution text
- `Funding` owns its own body and continuation
- `References` owns the reference list

- [ ] **Step 3: Sanity-check a style-heavy PDF**

Use `Mobini 2017` to verify that visually distinct unnumbered headings remain separable.

## Risks

1. A body/backmatter boundary that is too eager can still eat conclusion text.
2. A spread that is too wide can overfit later pages.
3. Style metadata quality varies; style must remain secondary.
4. Removing too many text-noise checks globally can regress first-page suppression if not limited to tail logic.
