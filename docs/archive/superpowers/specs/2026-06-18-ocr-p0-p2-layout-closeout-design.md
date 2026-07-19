# OCR P0-P2 Layout Close-Out Design

> Date: 2026-06-18
> Status: approved design, pending implementation
> Scope: close out the current P0-P2 OCR-v2 issues with layout-first logic, using text only as confirmatory evidence when it is effectively zero-risk.

## Goal

Finish the current OCR-v2 close-out pass without reopening large architecture work.

The target is to complete the active P0-P2 queue by:

1. fixing first-page assumptions after preproof-cover removal,
2. reducing publisher watermark and margin-band false positives,
3. recovering residual figure inner text / panel-like blocks,
4. updating only the expectations that become stale after verified behavior changes.

This work must not introduce new journal-specific rescue branches or a new page-state machine.

## Chosen Approach

Chosen approach: Approach A, "first surviving page anchor plus local expansion".

Why this approach won:

- It directly fixes the current P0 seam in `infer_zones()`.
- It stays inside the existing OCR-v2 architecture instead of starting a new refactor.
- It allows P1 and P2 fixes to share the same zone-authority assumptions.
- It is small enough to verify against existing gold fixtures and audit artifacts before merge.

Rejected alternatives:

- Full page-type state machine: better long-term generalization, too large for close-out.
- Column-lane zone modeling: strongest mixed-layout handling, clearly beyond this pass.

## Design Constraints

1. Layout evidence is primary.
2. Text matching is allowed only as a high-confidence confirmation signal, never as the core classifier skeleton.
3. No new journal-specific hardcoded rescue logic.
4. No reopening figure-group architecture in this pass.
5. Verification must check both the target failure papers and at least one control paper to catch regressions.

## Real Evidence From Audit Artifacts

The design is grounded in the current audit artifacts.

### DWQQK2YB frontmatter failure

In `tests/fixtures/ocr_real_papers/DWQQK2YB/block_trace.csv`, the first surviving page is page 2 after preproof-cover removal.

Observed structure on surviving page 2:

- preproof running header still exists near the top and should not become the article body start,
- title block appears first,
- author and affiliation blocks follow,
- correspondence / equal-contribution lines sit between frontmatter and the later Highlights area,
- body-like structured content only starts after those frontmatter anchors.

This confirms that the current `page == 1` logic is wrong. The correct question is: "what is the first surviving page, and where does its real body start?"

### A8E7SRVS and K7R8PEKW watermark failures

In `audit/A8E7SRVS/block_review.jsonl` and `audit/K7R8PEKW/block_trace.csv`, the noisy publisher strips share the same stable layout profile:

- `raw_label=aside_text`,
- extremely narrow width,
- very tall height,
- pinned to left or right page edge,
- repeated with near-identical geometry across many pages,
- weak coupling to the main body column.

The text often includes "Downloaded from ..." or "For personal use only", but the decisive signal is geometric. Text can be used as a confirming boost only when the edge-band geometry already matches.

### Control risk seen in frontmatter-heavy page-1 papers

Audit frontmatter pages such as `audit/6FGDBFQN/block_review.jsonl` show that page-1 layouts can legitimately contain title, author, metadata, abstract, and side noise together.

This means the fix must not simply broaden frontmatter/noise routing globally. It needs a local first-page anchor decision, followed by narrow expansion rules.

## 1. First Surviving Page Anchor

`infer_zones()` will stop treating literal page 1 as special. Instead it will compute:

- `surviving_pages = sorted(unique positive pages in current block set)`
- `first_surviving_page = surviving_pages[0]` when any page exists

All logic currently tied to `page == 1` for frontmatter/body-start inference will move to `page == first_surviving_page`.

This is not a rename-only change. The first surviving page becomes a local layout inference problem.

## 2. First Surviving Page Body Start

The first surviving page will be split into two local bands:

- pre-body frontmatter band,
- body-start-and-below band.

The split point is the first block on the first surviving page that satisfies a body-start condition.

Body-start condition should be based on layout and structural evidence, not plain text keywords:

- block is not a preproof marker,
- block is not a reference candidate,
- block is not a narrow side-band candidate,
- block is not a frontmatter anchor family block already seen above,
- block has body-like geometry relative to the dominant reading column,
- block appears below the title/author/affiliation/correspondence cluster,
- block is large enough and column-aligned enough to plausibly join body flow or structured insert flow.

Practical rule for this pass:

- keep the existing `_is_page1_body_start()` seam, but generalize it into a first-surviving-page helper fed by page-local geometry and the evolving set of already-seen frontmatter anchors.

## 3. Frontmatter Main Expansion

On the first surviving page, blocks above the body-start anchor enter `frontmatter_main_zone` when they are part of the top article stack:

- title,
- authors,
- affiliations,
- correspondence/support blocks,
- local metadata blocks that share the same main reading band.

Blocks near page edges or in narrow side strips stay eligible for `frontmatter_side_zone` instead.

This preserves the current main/side distinction while making it survive preproof-page removal.

## 4. Body Zone Expansion

`body_zone` should start from the first surviving page once the body-start anchor is found.

Current bug:

- `body_blocks` currently require `page > 1`, which incorrectly excludes page 2 when page 1 has already been removed.

Fix:

- body eligibility should become `page > first_surviving_page` or `page == first_surviving_page and block is at/after body_start_anchor`.
- blocks above that anchor on the first surviving page remain frontmatter-side/frontmatter-main candidates and must not enter body by fallback.

Same-page reference split remains in place:

- above reference heading on the same page stays body,
- below reference heading routes to reference/tail logic.

## 5. Margin-Band Noise Tightening

Publisher watermark cleanup will remain layout-first.

Primary evidence:

- raw label family such as `aside_text` / side-band text,
- edge-pinned x-range,
- very tall aspect ratio,
- very narrow width,
- weak overlap with main body columns,
- repeated strip-like placement across pages.

Allowed confirmatory text evidence, only when the geometry already matches:

- `Downloaded from`
- `For personal use only`

If the text matches but the geometry does not, do not classify as watermark noise from text alone.

Implementation intent for this pass:

- tighten `_looks_like_margin_band_noise()` / `_looks_like_edge_band_noise()` rather than creating a text-only classifier,
- optionally allow a geometry-plus-text confidence boost for borderline edge strips.

## 6. Residual Figure Inner Text Recovery

Residual `figure_inner_text` work should also stay layout-first.

Target blocks are short labels or short figure-internal text that:

- are very small,
- are spatially adjacent to a figure/media asset,
- live within or near the figure asset envelope,
- do not look like true prose lines,
- do not carry formal figure caption prefixes.

This pass should extend the existing `figure inner label` seam rather than adding broad new text rules.

Text can help only when it is near-zero-risk, for example a single panel-style token, but geometry remains the main decision signal.

## 7. P2 Scope Discipline

P2 in this pass means only:

- expectation updates made necessary by verified behavior changes,
- naming/fixture cleanup directly tied to the fixed output.

Explicitly out of scope:

- CLI rebuild wiring,
- figure-group architecture work,
- renderer redesign,
- new artifact families.

## Code Seams

Primary files:

- `paperforge/worker/ocr_document.py`
- `paperforge/worker/ocr_roles.py`

Likely touched seams:

- `infer_zones()`
- `_is_page1_body_start()` or its generalized replacement
- first-page frontmatter-main collection logic
- body-block eligibility logic
- `_looks_like_margin_band_noise()`
- `_looks_like_edge_band_noise()`
- figure-inner-text helper logic in `ocr_roles.py`

Test files:

- `tests/test_ocr_document.py`
- `tests/test_ocr_real_paper_regressions.py`
- fixture expectations only where behavior is visually verified as correct

## Verification Plan

Implementation must be driven by failing tests first.

### Required red tests

1. first surviving page frontmatter/title recovery after preproof removal,
2. first surviving page body-start expansion into body zone,
3. margin-band watermark stays noise on a representative edge-strip case,
4. control regression proving normal true page-1 papers still keep their frontmatter/body split,
5. residual figure-inner-text case if a stable fixture seam exists.

### Required real-paper checks

- `DWQQK2YB` for first surviving page recovery,
- `K7R8PEKW` and/or `A8E7SRVS` for repeated publisher edge-band noise,
- one control paper with legitimate page-1 frontmatter, preferably `6FGDBFQN`, to ensure no regression.

### Success criteria

- DW frontmatter on surviving page 2 is no longer swallowed into generic body fallback,
- body flow can start on the first surviving page,
- publisher strips no longer survive as `unknown_structural` / body-like content when their geometry is the classic margin-band pattern,
- no new regression on ordinary page-1 papers,
- only verified stale expectations are updated.

## Non-Goals

- No full page-state machine.
- No figure-group ownership redesign.
- No publisher-specific profile system.
- No text-first heuristic expansion.

## Decision

Proceed with Approach A as a narrow close-out pass:

- first surviving page replaces literal page 1 for local frontmatter/body inference,
- body start becomes a page-local anchor decision,
- publisher noise remains geometry-first with optional zero-risk text confirmation,
- P2 stays limited to verified expectation cleanup.
