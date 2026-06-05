# OCR Journal Layout Generalization Plan

Date: 2026-06-05  
Primary regression papers:

- `7C8829BD` — Frontiers-style mixed tail spread with backmatter + references
- `2GN9LMCW` — PeerJ-style unnumbered heading hierarchy + declarations container + references

---

## Goal

Generalize the structured OCR pipeline so it handles multiple journal layout families without article-specific text patches.

This plan targets reusable layout behaviors, not one-off paper fixes:

- frontmatter zoning on style-driven first pages,
- heading hierarchy for numbered and unnumbered journals,
- backmatter detection from structure rather than keyword suppression,
- container-style declaration regions before references,
- figure legend validation that distinguishes real captions from inner chart labels.

It explicitly avoids:

- hard-coding one paper's sentences,
- special-casing a single body line,
- direct text patching to "make the markdown look right".

---

## Current State

### Already stabilized

These are no longer the main blockers and should not be re-opened casually:

1. `7C8829BD` tail-spread ordering
   - body paragraphs are no longer broadly absorbed into tail sections
   - funding continuation now reattaches correctly
   - references zone is separated from neighboring backmatter

2. Derived rebuild / backfill runtime
   - legacy OCR papers can be backfilled into structured layers
   - rebuild now clears stale `done_incomplete` state correctly after successful validation

3. Basic page-marker compatibility
   - rebuild path can restore `ocr_status=done` when the rendered marker count is actually correct

4. First-page metadata for `2GN9LMCW`
   - author line is now preferred over affiliation line
   - obvious first-page furniture leakage is reduced

### Still incomplete

1. `2GN9LMCW` backmatter container is only partially modeled
   - `ADDITIONAL INFORMATION AND DECLARATIONS` is recognized as a boundary
   - but child sections inside that container are not all normalized into the same backmatter-child regime

2. `2GN9LMCW` child declarations still have unstable ownership
   - `Grant Disclosures`
   - `Author Contributions`
   - `Data Availability`
   - `Supplemental Information`
   still do not all retain clean heading/body grouping

3. Figure 4 in `2GN9LMCW` is still wrong
   - a chart-internal label is still promoted to a formal legend

4. Generalization is not yet explicit
   - the current code works better on the two audit papers
   - but the rules are not yet expressed as reusable layout-family logic

---

## Root Cause Model

### Root Cause A — boundary detection is necessary but not sufficient

The current bidirectional boundary method answers:

- where the main body ends
- where backmatter begins
- where references begin

But that alone does not solve:

- what internal structure exists inside backmatter
- whether the backmatter is flat or container-based
- which child headings belong to that container
- which bodies belong to which headings

So the missing piece is not a new boundary rule; it is **post-boundary structural modeling**.

### Root Cause B — unnumbered heading hierarchy is still too coarse

The pipeline now detects many unnumbered headings, but it still needs stronger level assignment for journals where hierarchy comes from:

- font size
- font family
- boldness / flags
- color
- spacing
- line height / bbox shape

The issue is not "heading detection only"; it is "heading family classification".

### Root Cause C — `figure_title` is still too trusted

Multi-panel figure pages can contain OCR blocks that are:

- axis titles
- panel labels
- chart legends
- group annotations

and those can still be misread as formal captions when raw label says `figure_title`.

So the missing piece is **formal legend validation**, not better cropping or matching geometry alone.

---

## Design Principles

### 1. Generalize by layout family, not by article

The plan should support classes like:

- numbered two-column body with mixed tail spread
- unnumbered style-driven hierarchy
- backmatter as flat section list
- backmatter as container + child sections
- reference-dominant last pages

This is broad enough to generalize, but still concrete enough to implement.

### 2. Geometry and structure outrank weak text patterns

Priority order should be:

1. raw OCR structural priors
2. page/spread regime
3. geometry / zones
4. style profile
5. heading/body ownership
6. weak text signals

Weak textual phrases may assist, but should never be the first or final authority for backmatter/body decisions.

### 3. Backmatter must be modeled after the boundary, not before it

The system should:

1. detect `body_end`
2. detect `backmatter_start`
3. detect `references_start`
4. classify backmatter form:
   - `flat_backmatter`
   - `container_backmatter`
5. resolve headings and bodies inside that regime

### 4. Figure captions need a formality test

Formal caption != any `figure_title`.

The system must validate that a candidate caption is consistent with:

- caption location
- caption span width
- numbering or caption-like phrasing
- relation to the whole panel group
- not obviously being an internal chart label

---

## Target Architecture Changes

### Task 1. Formalize bidirectional boundary output

Files:

- `paperforge/worker/ocr_render.py`
- possibly shared helpers extracted into a new small module if needed

Implementation:

1. Keep the current forward/backward logic, but make the outputs explicit:
   - `body_end_page`
   - `backmatter_start_page`
   - `references_start_page`
   - `tail_spread_range`

2. Add a reconciliation object, not just a tuple:
   - body range
   - tail range
   - references activation page
   - whether the spread is mixed or cleanly separated

3. Make downstream tail logic consume this structured boundary state instead of recomputing ad hoc.

Acceptance:

- Both `7C8829BD` and `2GN9LMCW` produce stable, explainable boundary outputs.

### Task 2. Add backmatter form classification

Files:

- `paperforge/worker/ocr_roles.py`
- `paperforge/worker/ocr_render.py`

Implementation:

1. Within the detected backmatter range, classify the regime as:
   - `flat_backmatter`
   - `container_backmatter`

2. `container_backmatter` is triggered only when:
   - a strong boundary/container heading exists,
   - it is followed by multiple declaration-style child headings,
   - and references begin later in the same region

3. Add / retain roles:
   - `backmatter_boundary_heading`
   - `backmatter_heading`
   - `backmatter_body`
   - `reference_heading`
   - `reference_item`

4. Do not make container detection depend on one journal phrase alone.
   - The heading text may seed the candidate,
   - but boundary confirmation must depend on late-page position + style + child-heading cluster + references follow-through.

Acceptance:

- `2GN9LMCW` page 10/11 is treated as `container_backmatter`
- `7C8829BD` remains in the simpler mixed-tail / flat-backmatter path

### Task 3. Normalize backmatter child section ownership

Files:

- `paperforge/worker/ocr_render.py`
- potentially `paperforge/worker/ocr_roles.py`

Implementation:

1. Inside `flat_backmatter`:
   - keep current heading/body ownership, but ensure references remain terminal

2. Inside `container_backmatter`:
   - child headings are grouped under the container
   - their bodies are assigned by:
     - same-page geometry
     - same-column preference
     - nearest valid heading above
     - interruption by a stronger sibling heading

3. Remove any residual path where container children fall back to generic body flow or noise suppression.

4. Normalize child heading levels:
   - container heading at one level
   - child declarations at one consistent lower level
   - references handled separately

Acceptance:

- For `2GN9LMCW`, the following each keep their own body:
  - `Funding`
  - `Grant Disclosures`
  - `Competing Interests`
  - `Author Contributions`
  - `Data Availability`
  - `Supplemental Information`

### Task 4. Finish style-aware heading family classification

Files:

- `paperforge/worker/ocr_render.py`
- `paperforge/worker/ocr_roles.py`

Implementation:

1. Build reusable style-family clustering using:
   - span size
   - font family
   - flags
   - color
   - bbox height
   - local spacing

2. Distinguish:
   - main section headings
   - subsection headings
   - backmatter child headings
   - body-like emphasized text that should not become headings

3. Preserve numbering as primary when present.
   - style serves as validation and level refinement, not replacement

Acceptance:

- `2GN9LMCW`
  - `MATERIALS AND METHODS`, `RESULTS`, `DISCUSSION`, `CONCLUSIONS` remain top-level
  - `Groups`, `Cell preparation and culture`, `Electrical stimulation of cells`, `Cell viability and activity`, `Osteogenic differentiation`, `Data analysis` are consistently lower-level
- numbered papers do not regress

### Task 5. Tighten first-page frontmatter zoning generally

Files:

- `paperforge/worker/ocr_roles.py`
- `paperforge/worker/ocr_metadata.py`

Implementation:

1. Keep the zone-based first-page logic, but generalize it beyond `2GN9LMCW`:
   - title zone
   - author zone
   - affiliation zone
   - furniture zone
   - abstract zone

2. Use geometry + style + text morphology together rather than phrase suppression.

3. Ensure affiliation blocks cannot retain `authors`.

4. Preserve raw frontmatter for audit, but keep furniture out of the main body by default.

Acceptance:

- `2GN9LMCW` remains correct for author extraction
- earlier papers with good frontmatter do not regress

### Task 6. Add formal legend validation for ambiguous figure-title blocks

Files:

- `paperforge/worker/ocr_roles.py`
- `paperforge/worker/ocr_figures.py`

Implementation:

1. Treat `figure_title` as a strong prior only.

2. Add a formality filter:
   - caption-like width and placement
   - relation to whole figure cluster
   - numbering or caption-style wording when available
   - reject obvious axis / inner-chart labels

3. Add safe degradation:
   - if the system cannot validate a formal legend, keep the asset and lower confidence,
   - do not invent a bad figure note.

Acceptance:

- `2GN9LMCW` Figure 4 no longer uses the axis-title line as the formal legend
- already-correct figures in `7C8829BD` remain stable

---

## Remaining Risks

### Risk 1. Overfitting container backmatter to PeerJ

Mitigation:

- require structural confirmation:
  - late-page location
  - heading style
  - multiple child sections
  - references follow-through

### Risk 2. Style-family clustering destabilizes numbered journals

Mitigation:

- numbering stays primary,
- style only validates and refines.

### Risk 3. Reference start swallows later declaration children

Mitigation:

- references remain terminal only after `references_start` and validated reference density,
- not merely after any reference-like text.

### Risk 4. Figure legend tightening reduces recall

Mitigation:

- preserve high-confidence numbered caption path,
- tighten only the ambiguous `figure_title` fallback path.

---

## Verification Checklist

General:

- [ ] no direct single-line paper-specific body-text patches are introduced
- [ ] geometry/style/ownership remain primary over text suppression

`7C8829BD`:

- [ ] funding continuation still attaches correctly
- [ ] late body text is not absorbed into backmatter
- [ ] references zone remains stable

`2GN9LMCW`:

- [ ] authors display is the true author line
- [ ] page-1 furniture does not leak into main body
- [ ] heading hierarchy is consistent for unnumbered sections
- [ ] `ADDITIONAL INFORMATION AND DECLARATIONS` acts as a container boundary
- [ ] declarations child sections each retain their own body
- [ ] references remain separate from declaration sections
- [ ] Figure 4 no longer uses an inner chart label as formal legend

Regression:

- [ ] numbered-heading papers still pass
- [ ] older legacy-backfilled papers still rebuild successfully
