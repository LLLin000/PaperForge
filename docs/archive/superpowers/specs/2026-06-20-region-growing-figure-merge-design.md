# Region-Growing Figure Merge Design

> Date: 2026-06-20
> Status: draft for review
> Scope: replace fragile row-first multi-panel grouping assumptions with region-growing figure merge plus validation

## Goal

Make figure grouping less dependent on neat layouts.

This design introduces a region-growing merge model that starts from a seed asset and gradually expands to nearby assets, then validates the merged group before it can become strict figure ownership.

The aim is to improve multi-panel and irregular figure grouping without reintroducing page-swallow behavior.

## Non-Goals

This design does not:

- redesign table matching,
- add free-form text-based figure rescue,
- trust whole-page asset grouping as a default,
- replace downstream reader/render contracts unnecessarily.

## Current Assessment

The first grouping hardening pass solved the most dangerous failure: `page_assets` can no longer casually swallow a page.

That made grouping safe enough, but not fully strong enough.

Current limitations remain:

- row-first pair/triple assumptions still dominate,
- irregular 2x2 or stacked layouts are under-modeled,
- a merged group is still often compressed into one coarse `cluster_bbox`,
- grouping confidence and ownership validation are too tightly coupled.

The result is that grouping no longer explodes, but it still leaves ownership recall on the table.

## Hard Constraint: Validation After Growth

The system must not trust a grown group just because its assets are locally adjacent.

Grouping is a candidate-generation phase.
Strict ownership requires a later validation phase.

If validation fails, the system should:

- split back to smaller candidates,
- demote the group to grouped evidence only,
- or leave the legend ambiguous.

It must not force a strict match from a weak merged group.

## Core Design

### 1. Seed from the upper-left asset on each page region

Grouping should begin from the earliest plausible figure asset in page reading order, typically the top-left asset.

This does not mean “the entire page is one figure.”
It means candidate groups start from a concrete seed and grow locally.

### 2. Grow only through local adjacency

From each seed, test adjacent assets one step at a time.

Local adjacency should consider:

- right-neighbor proximity,
- below-neighbor proximity,
- shared boundary bands,
- relative size compatibility,
- gaps that are large in absolute pixels but still small relative to the panels involved.

After absorbing one asset, recompute the active group geometry and continue growing from that updated boundary.

This produces an explicit growth path rather than one-shot row guessing.

### 3. Keep merge evidence per absorbed asset

Each absorbed asset should record why it was merged, for example:

- `adjacent_right`
- `adjacent_below`
- `shared_band`
- `gap_tolerated_by_size_ratio`
- `aligned_stack`

This evidence should survive into debugging surfaces.

The purpose is to make grouping auditable instead of opaque.

### 4. Validate the grown group against control boundaries

Once a group is grown, validate it before strict ownership.

Validation checks should include:

- does the group cross another caption’s likely control zone,
- is the inter-panel gap too large without supporting evidence,
- is the group spanning two visually separate figures,
- is a narrower local group better explained than the larger one,
- does the legend-caption geometry still make sense against the grown group.

If the answer is no, the system should demote or split.

### 5. Keep page-level priors as guardrails, not primary merge logic

Page-level context remains useful as a guardrail:

- where captions cluster,
- where display zones exist,
- where references or backmatter begin.

But page priors should not decide the group directly.
They should only constrain growth and validation.

## Required Contracts

### Candidate group contract

Each figure candidate group should carry:

- `seed_asset_block_id`
- `asset_block_ids`
- `growth_steps`
- `group_bbox`
- `growth_evidence`
- `validation_status`
- `validation_reason`

`growth_steps` should be a compact sequence, not a huge trace dump.

### Validation status contract

At minimum:

- `strict_match_ok`
- `grouped_evidence_only`
- `split_required`
- `ambiguous`

This separates “candidate group exists” from “candidate group is safe to own a legend.”

## File Responsibilities

### `paperforge/worker/ocr_figures.py`

Owns:

- seed selection,
- local adjacency growth,
- candidate-group evidence,
- post-growth validation,
- demotion or split when validation fails.

### `tests/test_ocr_figures.py`

Should grow to cover:

- irregular side-by-side pairs,
- stacked layouts,
- 2x2-like growth,
- large but still acceptable gaps,
- false merges that validation must reject.

### `tests/test_ocr_real_paper_regressions.py`

Should protect:

- no return to page-swallow behavior,
- no regression on already-stable gold papers,
- at least one irregular-layout real-paper case.

## Acceptance Criteria

This design is successful when all of the following are true:

1. Figure grouping no longer depends primarily on row-first neat-layout assumptions.
2. A group can be grown gradually from a seed asset through local adjacency.
3. Large-but-plausible gaps can be tolerated when supported by relative geometry.
4. Suspicious merges are demoted or split rather than forced into strict ownership.
5. No return to unrestricted `page_assets` behavior occurs.

## Validation Strategy

Validate on:

1. known residual figure-ownership papers,
2. fresh unseen papers with mixed multi-panel layouts,
3. the existing no-page-swallow regression set.

Success means not only better match recall, but no new failure family introduced on the unseen sample.

## References

- `docs/superpowers/specs/2026-06-19-ocr-rebuild-audit-remediation-design.md`
- `project/current/ocr-v2-generalization-boundary.md`
- `project/current/ocr_rebuild_audit.md`
- `paperforge/worker/ocr_figures.py`
