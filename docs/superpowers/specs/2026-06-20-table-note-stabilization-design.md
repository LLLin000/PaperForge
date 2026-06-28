# Table Note Stabilization Design

> Date: 2026-06-20
> Status: draft for review
> Scope: stabilize table-note ownership and continue table ambiguity reduction without reopening OCR-v2 role classification

## Goal

Make table notes a stable post-ownership surface.

This design has two linked goals:

1. separate table notes from body prose and page-footnote regions more reliably,
2. improve bare `Table N` matching using stronger layout tie-breaks rather than free-form text rescue.

The intent is to deepen the table-local ownership contract now that rebuild-output pollution, namespace collisions, and basic table-note write-through are already fixed.

## Non-Goals

This design does not:

- redesign OCR role classification,
- add publisher-specific text rules,
- solve figure ownership,
- change the global OCR-v2 readiness conclusion,
- replace the existing table matching scorer wholesale.

## Current Assessment

The first remediation pass already proved three things:

1. table notes can be carried through inventory, object markdown, and fulltext projection,
2. blockquote table-caption pollution is gone,
3. bare `Table N` captions no longer have to be rejected immediately.

The remaining problem is stability.

Current residuals show two failure modes:

- a table note can still be confused with page footnotes or nearby body text,
- a bare `Table N` caption can still remain ambiguous when multiple plausible table assets compete.

Those are not text-understanding failures. They are layout-ownership failures.

## Hard Constraint: No Free-Form Text Rescue

This design keeps the same contract as the previous remediation spec.

Allowed text use:

- controlled marker extraction after structural candidacy already exists,
- note text formatting after note ownership is already decided,
- optional weak note-marker support (`*`, `†`, `a`, `b`, `Abbreviation:`) only as secondary evidence.

Disallowed text use:

- deciding semantic role from prose content,
- using publisher wording to identify notes,
- using table-note wording as the primary ownership signal.

Layout, ownership, and document priors must dominate text.

## Core Design

### 1. Page footnote prior comes before table-local note ownership

When a table sits near the bottom of a page, the main risk is confusing page footnotes with table notes.

The design must therefore build a `page_footnote_prior` from other pages in the same paper before deciding local table-note ownership.

This prior should summarize:

- where page footnotes tend to begin on the page,
- how close they sit to the page bottom,
- whether they span a full column / footer band,
- whether they are repeatedly present across the paper in a similar zone.

If a candidate note block on the current page falls into a strong page-footnote zone, it should default toward page footnote rather than table note unless table-local evidence is substantially stronger.

### 2. Table notes should be recognized as a note band, not isolated blocks

Single-block note decisions are too brittle.

After a table asset is matched, the system should build a `table_below_note_band` by scanning directly below the table and grouping nearby small text blocks that:

- are vertically near the table bottom,
- overlap the table horizontally,
- share smaller typography or tighter line spacing than body prose,
- remain separated from the next body paragraph by a whitespace band.

This band can contain one or more note blocks. Ownership should attach to the band first, then to its member blocks.

### 3. Body exclusion is a first-class signal

The system should not only ask “does this look like a table note?”

It should also ask:

- does this look like continuation of body flow,
- does it align with body spine width,
- is there insufficient whitespace separation from body prose below,
- is it too wide / too long / too regular to plausibly be a note band?

If body evidence is stronger than note-band evidence, the candidate should remain body text.

### 4. Bare `Table N` should use a stronger spatial tie-break, not a broader caption rule

The current improvement allowed bare `Table N` to enter competition. The next step is not more permissive caption detection.

The next step is a stronger tie-break among already-accepted table candidates.

Priority signals:

- stronger x overlap with the candidate asset,
- shorter table-caption-to-asset vertical distance,
- same-column preference when multiple candidates exist,
- stronger advantage over second-best candidate,
- continuation-page handling evaluated separately from same-page matching.

This should improve `matched` / `matched_low_confidence` rates without weakening the role contract.

## Required Contracts

### Table note ownership contract

The table inventory surface should carry, at minimum:

- `note_block_ids`
- `note_texts`
- `note_bboxes`
- `note_band_bbox`
- `note_match_reason`
- `note_confidence`
- `consumed_block_ids`

`note_match_reason` should capture why the band was attached, for example:

- `footnote_role_below_table`
- `vision_footnote_below_table`
- `note_band_geometry_match`
- `page_footnote_prior_rejected`

This is for auditability, not verbosity.

### Page footnote prior contract

The page-footnote prior should be explicit enough to answer:

- why a candidate was rejected as a table note,
- whether the rejection came from page-bottom prior or body-flow prior,
- whether the page had no prior and therefore local geometry dominated.

### Table ambiguity contract

Bare `Table N` should now resolve to one of:

- `matched`
- `matched_low_confidence`
- `ambiguous`
- `unmatched`

but only after candidate competition is run. It must no longer be a purely pre-score rejection path.

## File Responsibilities

### `paperforge/worker/ocr_tables.py`

Owns:

- page-footnote prior derivation for table-note decisions,
- note-band grouping below matched tables,
- note ownership write-through,
- table ambiguity tie-breaks among accepted candidate assets.

### `paperforge/worker/ocr_objects.py`

Owns:

- projection of owned note bands into table object markdown.

### `paperforge/worker/ocr_render.py`

Owns:

- suppression of consumed note blocks from body flow,
- no fresh semantic reclassification.

### `paperforge/worker/ocr_health.py`

Owns:

- additive reporting about note-band ownership and table ambiguity only if useful for auditability.

## Acceptance Criteria

This design is successful when all of the following are true:

1. A table at page bottom no longer greedily captures page footnotes just because text is below the table.
2. Multi-line note bands directly below tables are attached more reliably than single-block note heuristics.
3. Table notes are less likely to be confused with body prose because whitespace and body-width exclusion are explicit.
4. Bare `Table N` captions improve through stronger spatial tie-breaks rather than freer caption admission.
5. No new free-form text rescue path is introduced.

## Validation Strategy

This work should be validated on two sample sets:

1. known residual papers where table ambiguity or note ownership is already visible,
2. a fresh sample of papers that were not manually optimized beforehand.

The point is to verify both local improvement and absence of new failure families.

## References

- `docs/superpowers/specs/2026-06-19-ocr-rebuild-audit-remediation-design.md`
- `project/current/ocr_rebuild_audit.md`
- `paperforge/worker/ocr_tables.py`
- `paperforge/worker/ocr_objects.py`
- `paperforge/worker/ocr_render.py`
