# OCR Rebuild Audit Remediation Design

> Date: 2026-06-19
> Status: executed on `ocr-v2`
> Scope: convert the 2026-06-19 full rebuild audit into a constrained remediation design for OCR rebuild outputs and health semantics

## Goal

Stabilize the rebuild output layer after the 452-paper audit without reopening the OCR-v2 backbone redesign.

This design treats the current rebuild issues as a post-readiness hardening pass over four surfaces:

1. ownership outputs,
2. render projection,
3. health semantics,
4. high-risk figure/table inventory edge cases.

The goal is to remove user-visible output pollution, reduce false red/yellow health noise, and close the most important inventory gaps while preserving the anchor-first OCR-v2 architecture.

## Non-Goals

This design does not:

- redesign the anchor-first OCR-v2 backbone,
- reintroduce early semantic role guessing,
- add text-pattern rescue logic for classification,
- reopen the completed readiness-gate storyline,
- solve every low-severity edge case found in the full corpus audit.

## Hard Constraint: No Free-Form Text Rescue Logic

This is a design invariant.

New fixes in this pass must not use free-form text content as the primary basis for deciding semantic role or ownership.

Allowed controlled text use:

- extracting figure/table namespace and numbers from blocks whose role is already determined,
- extracting continuation markers from blocks whose role is already determined,
- extracting reference-item numbering after reference-role candidacy is already established structurally,
- formatting already-owned captions, legends, or notes for render output.

Disallowed text use:

- introducing new semantic classification rules based on phrases or publisher-specific wording,
- rescuing ownership by matching prose content,
- deciding whether a block is a footnote/table note/figure note/body paragraph from text alone.

The repair surface must stay anchored in existing structure evidence: role, zone, marker signature, style family, page geometry, accepted document structure, and inventory ownership outcomes. Text is permitted only as controlled marker parsing after structural candidacy already exists.

## Current Assessment

The 2026-06-19 rebuild audit does not show that OCR-v2 is architecturally wrong.

It shows that the post-structure output path still has shallow seams:

- ownership evidence is discovered in one module and dropped in another,
- render still contains correctness-affecting policy,
- health still re-infers quality from weak proxies,
- some figure/table inventory cases still use fragile generic heuristics.

The framework backbone remains:

```text
raw observations
-> structural signatures
-> stable anchors / families
-> zone inference
-> late role resolution
-> figure / table validation
-> render + health
```

This remediation pass stays inside the last three stages.

## Problem Breakdown

### 1. Ownership output is incomplete

The audit confirmed that `ocr_tables.py` already detects adjacent note blocks and records `note_block_ids`, but downstream consumers ignore them.

Effects:

- table notes remain outside the table object,
- footnotes leak into body flow,
- fulltext and object render disagree about what belongs to a table.

This is not primarily a detection failure. It is an ownership write-through failure.

### 2. Render projection still carries correctness policy

`ocr_render.py` still decides too much:

- which roles skip body flow,
- how table captions appear in fulltext,
- how reference tail ordering is imposed.

Effects:

- table captions duplicate into fulltext as blockquotes,
- footnotes become body text,
- reference ordering can be wrong even when structure is mostly right.

### 3. Health semantics are too shallow

The health model still uses weak binary gates and weak proxy fields:

- only `section_heading` contributes to heading count,
- a single `raw_label == "reference_content"` can satisfy references,
- `figure_asset_count` is a misleading name for matched-figure count,
- `> 0` issue gates punish tiny and severe failures equally.

Effects:

- false red/yellow inflation,
- poor maintenance prioritization,
- rebuild audit output that overstates some defects and understates others.

### 4. A small set of inventory rules still creates outsized trust risk

The audit isolated four high-leverage inventory issues:

1. bare `Table N` captions are treated as too weak even when geometry is strong,
2. supplementary figure numbering collides with main-figure numbering,
3. `page_assets` grouping is too dangerous without strict gates,
4. figure/table assets can still conceptually compete without one explicit arbitration surface.

These are not invitations to add textual heuristics. They are invitations to tighten ownership contracts.

## Design Principles

### Principle 1: Ownership is the truth surface

If a table note, figure asset, or table asset is discovered during inventory construction, that ownership outcome must survive into:

- structured writeback when needed,
- object markdown generation,
- fulltext rendering,
- health accounting.

No downstream module should have to rediscover ownership from raw blocks.

### Principle 2: Render is a projection module, not a rescue module

Render should consume:

- accepted structured roles,
- accepted document structure,
- accepted figure/table inventory outcomes.

Render should not compensate for weak ownership or weak structure by adding fresh correctness logic.

### Principle 3: Health should consume explicit outcomes, not weak side effects

Health fields should derive from:

- accepted reference/body/tail structure,
- explicit inventory outcome buckets,
- explicit heading-role counts,
- explicit matched/held/unmatched counts.

The health surface should become more interpretable, not more magical.

### Principle 4: Geometry and structure beat prose

When deciding ownership or match confidence in this pass, prefer:

- page,
- column,
- bbox relation,
- zone,
- style family,
- marker signature,
- already-accepted role.

Do not compensate with phrase-based rescue logic.

## Remediation Scope

### Phase A: Output pollution fixes

This is the first execution batch because it removes visible corruption with low architectural risk.

Included:

1. footnote blocks that belong to table notes must stop rendering as body text,
2. fulltext table-caption blockquote duplication must be removed,
3. table object markdown must render owned notes,
4. heading count must include `section_heading`, `subsection_heading`, and `sub_subsection_heading`.

Expected result:

- cleaner fulltext,
- lower visible noise,
- immediate reduction in misleading health failures.

### Phase B: Inventory contract hardening

This batch fixes small contract defects with high leverage.

Included:

1. `Table N` captions may match only under strong geometry and ownership evidence,
2. supplementary and extended-data figures must split from the main-figure namespace,
3. `page_assets` grouping must be gated tightly or demoted out of strict ownership,
4. inventory outcomes must be made explicit enough for completeness accounting.

Expected result:

- fewer false unmatched tables,
- no main/supplementary collisions,
- less risk of one legend swallowing a whole page.

### Phase C: Semantics cleanup for health and ordering

This is important but belongs after Phases A-B because it depends on better ownership truth.

Included:

1. reference ordering should prefer explicit numbering when present,
2. fallback reference ordering should use layout authority appropriate to single-column vs two-column reference zones,
3. `references_found` should depend on accepted structure rather than one raw label,
4. health issue scoring should move toward ratio/weighted semantics.

Expected result:

- health reports become maintenance-meaningful,
- reference-tail errors become easier to debug,
- green/yellow/red becomes less arbitrary.

## Required Figure Namespace And Outcome Contracts

To support render and health correctly, the inventory surfaces should separate namespace from outcome.

### Figure namespace / kind

At minimum, numbered figure candidates in this pass must be representable as:

- `main`
- `supplementary`
- `extended_data`
- `unknown`

`supplementary` is not an ownership outcome. It is a namespace/kind that can independently be matched, held, ambiguous, or unmatched.

### Ownership outcome

At minimum, numbered ownership candidates in this pass must be representable as:

- `matched`
- `matched_low_confidence`
- `held`
- `ambiguous`
- `unmatched`
- `rejected`
- `deduped_duplicate`

Not every file must use identical field names internally, but the emitted semantics must be complete enough that:

- completeness does not guess why something disappeared,
- render does not need to infer missing ownership states,
- audits can distinguish “missing” from “intentionally excluded”.

## Required Table Note Ownership Contract

The table-note path must stop at a complete ownership contract rather than a dead identifier list.

`ocr_tables.py` should emit, at minimum:

- `note_block_ids`
- either `note_blocks` or `note_texts` for downstream render consumption
- a consumed-block surface that includes `caption_block_id`, `asset_block_id`, and `note_block_ids`

The downstream contract is:

- `ocr_objects.py` consumes owned table notes and renders them under a dedicated notes section in the table object markdown
- `ocr_render.py` skips any block already consumed by table ownership when projecting body flow
- `ocr_health.py` counts owned notes as consumed ownership, not as free-floating body pollution

Keeping only `note_block_ids` is insufficient because the current failure mode is precisely that discovery exists but no projection consumer uses it.

## Required Bare `Table N` Matching Contract

Bare `Table N` captions may match only when all of the following are satisfied:

1. the caption block is already a `table_caption`, `table_caption_candidate`, or validation-first table candidate,
2. the candidate asset is already a `table_asset` or has accepted table-like raw-label evidence such as `table` or `table_image`,
3. the caption/asset relation is same-page or an accepted continuation-page relation,
4. the caption and asset have strong horizontal overlap,
5. the asset is below the caption unless an accepted previous-page continuation geometry is in effect,
6. there is no close competing asset within the ambiguity threshold.

This rule exists to prevent a weak bare caption from swallowing nearby figure assets.

## Required `page_assets` Gate

`page_assets` must not produce strict matched ownership unless at least one of the following is true:

1. exactly one formal figure legend exists on that page,
2. expected panel count closely matches page asset count,
3. no competing figure/table caption candidates exist on the page.

If those gates are not satisfied, `page_assets` may only emit reader-level grouped evidence, not strict ownership.

This keeps page-level grouping from becoming a page-swallow path.

## File Responsibilities

### `paperforge/worker/ocr_tables.py`

Owns:

- table caption matching,
- table asset ownership,
- adjacent table-note ownership,
- table inventory outcome emission,
- consumed-table-block contract emission.

Must not:

- rely on prose pattern rescue,
- emit downstream-only dead fields.

### `paperforge/worker/ocr_figures.py`

Owns:

- figure numbering namespace,
- figure group candidate generation,
- legend-to-asset ownership outcomes,
- completeness accounting inputs.

Must not:

- introduce text-pattern role rescue,
- leave grouped-vs-single outcomes too implicit for health.

### `paperforge/worker/ocr_objects.py`

Owns:

- object markdown projection for figures and tables.

Must consume:

- table note ownership already decided upstream,
- namespace-aware figure/table identity already decided upstream.

### `paperforge/worker/ocr_render.py`

Owns:

- projection of accepted ownership and structure into fulltext.

Must stop owning:

- duplicated table-caption policy,
- body leakage for owned note blocks.

### `paperforge/worker/ocr_health.py`

Owns:

- maintenance-facing summary semantics.

Must become:

- explicit about what it is counting,
- less dependent on weak proxy checks.

## Health V2 Compatibility Rule

The first health pass in this remediation cycle should be backward-compatible.

Required approach:

- add corrected counters such as total heading count across all heading tiers,
- rename or parallelize misleading fields such as matched-figure count,
- add ratio/weighted or issue-breakdown-v2 style fields,
- tighten `references_found` to accepted reference evidence,
- keep the current top-level `overall` surface compatible until the richer fields are proven.

This is a semantics-deepening step, not a permission slip for a large breaking health rewrite.

## Acceptance Criteria

This design is successful when all of the following are true:

1. Table notes owned by table inventory appear in table object markdown and no longer leak into body flow.
2. Fulltext no longer emits blockquote table captions before table embeds on normal display-zone tables.
3. Heading health counts all three heading tiers.
4. Bare `Table N` captions can match only under the explicit strong-geometry contract and without introducing free-form text rescue.
5. Supplementary figure numbering no longer collides with main figures because namespace/kind is separated from outcome.
6. `page_assets` no longer acts as an unrestricted page swallow path.
7. `references_found` no longer passes from one weak raw label alone.
8. Health output becomes more interpretable for the rebuild audit surface through additive or compatibility-preserving v2 fields before any top-level scoring replacement.

## Execution Order

The implementation plan should sequence the work in this order:

1. output pollution fixes,
2. ownership write-through fixes,
3. inventory contract hardening,
4. health and reference semantics cleanup,
5. audit-facing doc updates for the rebuild queue.

This order is deliberate:

- first remove visible corruption,
- then make ownership authoritative,
- then tighten health semantics once ownership truth is stable.

## Risks

### Risk 1: Hidden dependency on dead fields

If any downstream consumer implicitly expects the current weak output shapes, making ownership explicit may expose previously hidden assumptions.

Mitigation:

- keep changes localized to existing ownership consumers,
- add focused tests for render/object/health projections.

### Risk 2: Over-correcting with page-level figure grouping

The current `page_assets` patch is high risk precisely because it improves recall by weakening ownership boundaries.

Mitigation:

- gate it strictly,
- or reduce it to a non-strict candidate/reference path rather than a direct ownership path.

### Risk 3: Reintroducing text heuristics through “small convenience” fixes

This would violate the core architectural direction and quickly rot.

Mitigation:

- treat the no-text-matching rule as hard review criteria for every remediation step.

## Out of Scope Residuals

The following may remain after this pass and should not block the design unless they rise to trust-risk level:

- low-severity audit-truth drift blocks,
- conservative backmatter-heading taxonomy,
- isolated corpus-specific edge cases that do not create new failure families.

## References

- `project/current/ocr_rebuild_audit.md`
- `project/current/ocr-v2-closeout-priority.md`
- `project/current/ocr-v2-generalization-boundary.md`
- `paperforge/worker/ocr_tables.py`
- `paperforge/worker/ocr_figures.py`
- `paperforge/worker/ocr_render.py`
- `paperforge/worker/ocr_objects.py`
- `paperforge/worker/ocr_health.py`
