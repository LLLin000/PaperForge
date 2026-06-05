# OCR PeerJ-Style Remediation Plan

Date: 2026-06-05  
Scope paper: `2GN9LMCW`  
Reference PDF: `Mobini et al. 2017 - In vitro effect of direct current electrical stimulation on rat mesenchymal stem cells`

## Goal

Stabilize OCR parsing for journal layouts that rely on visual hierarchy rather than numbered headings, and that introduce a backmatter container section such as `ADDITIONAL INFORMATION AND DECLARATIONS`.

This plan is intentionally narrower than the earlier tail-regime work:

- It does **not** redesign the full OCR architecture again.
- It does **not** special-case one paper by string matching bodies.
- It **does** extend the current structured pipeline so that:
  - first-page frontmatter is split into author vs affiliation vs furniture,
  - unnumbered headings are assigned hierarchical levels using PDF span style,
  - backmatter can begin with a container heading,
  - figure inner labels are not promoted into formal legends.

## Current Failures In `2GN9LMCW`

### 1. Author vs affiliation confusion on page 1

Observed:

- `resolved_metadata.authors.value` contains the affiliation line, not the author list.
- `authors_display` also renders the institution instead of the authors.

Root cause:

- Page 1 block role assignment currently labels both the true author line and at least one affiliation line as `authors`.
- Resolver then picks the wrong `authors` block.

This is a **frontmatter zoning failure**, not only a metadata resolver failure.

### 2. Frontmatter furniture leaks into main body

Observed in `fulltext.md`:

- `These authors contributed equally to this work.`
- `Submitted / Accepted / Published`
- `Distributed under Creative Commons`
- `Academic editor`
- `DOI ...`
- `Additional Information and Declarations can be found on page 10`

These are currently rendered as normal body text.

Root cause:

- First-page handling still treats too many furniture blocks as generic `body_paragraph`.
- Suppression is not using the strong layout cues available in this journal.

### 3. Unnumbered headings collapse into a single level

Observed:

- `MATERIALS AND METHODS`
- `Groups`
- `Cell preparation and culture`
- `Electrical stimulation of cells`
- `Cell viability and activity`
- `Osteogenic differentiation`
- `Data analysis`

are mostly rendered at the same heading level.

Root cause:

- Current heading logic can detect "heading-ness", but does not robustly assign heading **level** for unnumbered layouts.
- This journal depends heavily on visual style, not numbering.

### 4. Backmatter boundary is not modeled

Observed:

- `ADDITIONAL INFORMATION AND DECLARATIONS` is rendered as a normal section heading.
- Page 10/11 content under that container is not grouped as one backmatter region.
- `Funding`, `Grant Disclosures`, `Competing Interests`, `Author Contributions`, `Data Availability`, `Supplemental Information` are inconsistently treated as main-section or backmatter headings.

Root cause:

- Current tail logic assumes backmatter starts directly from ordinary backmatter headings or references.
- This paper has a **container heading** that marks the backmatter block before individual sub-sections appear.

### 5. Author-contribution bullets and declarations are not attached cleanly

Observed:

- Some author contribution lines are downgraded incorrectly.
- The page 11 declarations area is only partially grouped.

Root cause:

- Once the backmatter container is missed, section ownership on page 11 becomes unstable.

### 6. Figure 4 legend is wrong

Observed:

- Figure 4 is currently built from `Days post culture in osteogenic differentiation supplemented medium`, which is not a formal caption.

Root cause:

- `raw_label == figure_title` is still trusted too much.
- On multi-panel chart pages, OCR may tag axis labels or internal chart text as `figure_title`.

This is a **formal legend validation** failure.

## Design Decisions

### A. `ADDITIONAL INFORMATION AND DECLARATIONS` becomes a backmatter boundary heading

This is not a new universal requirement for every journal.

It is a bounded rule:

- treat such headings as a `backmatter_boundary_heading` when they appear in the late-paper region,
- and only when followed by a cluster of declaration-like sub-sections and/or references,
- not as a global text special case for all contexts.

This gives us a container for journals like PeerJ without forcing the same pattern onto unrelated papers.

### B. PDF style is a primary signal for unnumbered heading hierarchy

For unnumbered layouts:

- `size`
- `font`
- `flags`
- `color`
- bbox height / width
- spacing before/after

become primary heading-level signals.

For numbered layouts:

- numbering remains the first structural prior,
- style acts as validation / disambiguation,
- not as a replacement.

## Implementation Plan

### Task 1. Strengthen first-page frontmatter zoning

Files:

- `paperforge/worker/ocr_roles.py`
- `paperforge/worker/ocr_metadata.py`

Implementation:

1. Introduce explicit page-1 frontmatter zone analysis:
   - `title_zone`
   - `author_zone`
   - `affiliation_zone`
   - `journal_furniture_zone`
   - `abstract_zone`

2. Use text + geometry + style together:
   - authors:
     - multiple human names,
     - `and`,
     - author markers like `*`, `1`, `2`,
     - near title, above affiliations
   - affiliations:
     - institution keywords,
     - city/country patterns,
     - numbered superscripts,
     - directly below author block
   - furniture:
     - left/side column small-font metadata,
     - editorial / DOI / submission / copyright content

3. Stop allowing affiliation lines to keep the `authors` role.

4. Resolver change:
   - prefer `authors` from the true author zone,
   - treat affiliation blocks as raw frontmatter, not author alternatives.

Acceptance:

- `resolved_metadata.authors` for `2GN9LMCW` contains the author names, not the institution line.
- page-1 furniture lines no longer appear in body render.

### Task 2. Build style-aware heading hierarchy for unnumbered papers

Files:

- `paperforge/worker/ocr_render.py`
- `paperforge/worker/ocr_roles.py`

Implementation:

1. Extend style profile extraction to use:
   - font size,
   - font family,
   - flags/boldness,
   - color,
   - bbox height,
   - spacing around the block.

2. Build document-level clusters for heading families:
   - title style,
   - section-heading style,
   - subsection-heading style,
   - backmatter-heading style,
   - body style.

3. For unnumbered heading candidates:
   - classify by nearest style cluster,
   - then validate with layout context.

4. For numbered heading candidates:
   - numbering stays primary,
   - style must still be compatible before final role assignment.

Acceptance:

- `MATERIALS AND METHODS` remains top-level.
- `Groups`, `Cell preparation and culture`, `Electrical stimulation of cells`, `Cell viability and activity`, `Osteogenic differentiation`, `Data analysis` are assigned lower-level headings consistently.
- Similar logic remains valid on numbered-layout papers.

### Task 3. Add backmatter boundary container handling

Files:

- `paperforge/worker/ocr_roles.py`
- `paperforge/worker/ocr_render.py`

Implementation:

1. Add a new role:
   - `backmatter_boundary_heading`

2. Detect it only when all are true:
   - it appears in late pages,
   - visually matches heading style,
   - followed by multiple declaration-like section headings and/or reference heading,
   - not part of the main body section flow.

3. Tail logic changes:
   - once a `backmatter_boundary_heading` is detected,
   - all subsequent eligible blocks until `reference_heading` belong to a backmatter container regime,
   - ordinary body section rules are no longer used there.

4. Render policy:
   - either render the boundary heading explicitly,
   - or treat it as a non-emitted structural container if that reads better,
   - but its ownership effect must still apply.

Acceptance:

- Page 10/11 of `2GN9LMCW` is treated as a backmatter region beginning at `ADDITIONAL INFORMATION AND DECLARATIONS`.

### Task 4. Group declaration sub-sections within the backmatter container

Files:

- `paperforge/worker/ocr_render.py`
- potentially `paperforge/worker/ocr_roles.py`

Implementation:

1. Inside the backmatter container:
   - identify sibling section headings:
     - `Funding`
     - `Grant Disclosures`
     - `Competing Interests`
     - `Author Contributions`
     - `Data Availability`
     - `Supplemental Information`
   - these are not main body headings anymore

2. Attach bodies by:
   - same-page geometry,
   - same column preference,
   - nearest valid heading above,
   - until interrupted by a stronger sibling heading

3. Preserve `references_zone` as a terminal zone:
   - once `reference_heading` starts,
   - later reference items do not re-enter declaration sections.

Acceptance:

- `Funding` contains its declaration body.
- `Grant Disclosures` contains grant list.
- `Competing Interests` contains the competing-interest sentence.
- `Author Contributions` contains all contribution lines.
- `Data Availability` and `Supplemental Information` each retain their own body text.

### Task 5. Tighten figure-title promotion into formal legend

Files:

- `paperforge/worker/ocr_roles.py`
- `paperforge/worker/ocr_figures.py`

Implementation:

1. `figure_title` becomes only a strong prior, not automatic formal legend.

2. Add formal-legend validation:
   - contains `Figure N` / `Fig. N`, or
   - sits in a caption-like region spanning the figure cluster,
   - not obviously panel-internal text,
   - not obviously axis/title-only text,
   - width and placement compatible with a caption line, not just an internal chart label

3. For multi-panel chart pages:
   - prefer captions that describe the whole panel group
   - reject isolated inner labels into `figure_inner_text` / rejected candidate

Acceptance:

- Figure 4 is no longer built from the axis-title text.
- If no formal caption can be validated, it should degrade safely rather than fabricate a bad figure note.

## Risks

### Risk 1. Overfitting PeerJ left-column furniture

Mitigation:

- base rules on zone + style + role interaction,
- not raw text alone,
- and keep the container-heading behavior gated to late-paper declaration clusters.

### Risk 2. Style clustering destabilizes numbered papers

Mitigation:

- numbering remains primary when present,
- style only validates or refines level.

### Risk 3. Backmatter boundary absorbs real discussion text

Mitigation:

- only activate after the main body end,
- require a declaration-cluster pattern,
- and stop at `reference_heading`.

### Risk 4. Figure 4 fix reduces recall on normal legends

Mitigation:

- preserve current high-confidence numbered legend path,
- only tighten the ambiguous `figure_title` fallback path.

## Verification Checklist

- [ ] `2GN9LMCW` authors render as actual authors, not affiliation lines
- [ ] page-1 submission/editor/DOI furniture is suppressed from main body
- [ ] `MATERIALS AND METHODS` and its child headings show a consistent hierarchy
- [ ] `ADDITIONAL INFORMATION AND DECLARATIONS` triggers backmatter container handling
- [ ] `Funding`, `Grant Disclosures`, `Competing Interests`, `Author Contributions`, `Data Availability`, `Supplemental Information` each keep their own body text
- [ ] `REFERENCES` starts a separate references zone
- [ ] Figure 4 no longer uses the axis-title text as its formal legend
- [ ] existing numbered-heading papers still pass regression tests
- [ ] existing tail-spread regression paper `7C8829BD` still renders correctly
