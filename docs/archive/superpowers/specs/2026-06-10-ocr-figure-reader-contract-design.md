# OCR Figure Reader Contract Design

Date: 2026-06-10
Status: Proposed
Scope: OCR figure output contract only

## 1. Purpose

This design defines a human-first figure output contract for OCR v2.

The goal is not to increase strict figure match counts by relaxing standards. The goal is to guarantee that formal figure information becomes reader-visible, deduplicated, and traceable even when strict asset-level matching is incomplete.

This design separates three concerns that are currently mixed together:

1. Strict object matching
2. Reader-visible figure presentation
3. Audit and debug diagnostics

Core principle:

```text
Strict object matching is not required for reader-visible figure output.
When a formal legend or salient visual group is human-discernible,
the system must emit a reader-level figure object while preserving
strict audit status separately.
```

## 2. Problem Statement

The current figure pipeline binds reader-visible output too tightly to strict match success.

Current implicit contract:

```text
matched_figures == official figures == readable figures
```

This causes three recurring failure modes:

1. Formal legends are recognized, but if strict matching fails, reader-visible output disappears or collapses into orphan-only debug artifacts.
2. Long formal legends can leak into body flow and pollute fulltext readability.
3. Debug object names such as `unmatched_legend_003`, `unresolved_cluster_002`, and `orphan_017` can leak into user-facing markdown.

These are implementation philosophy problems, not just classifier problems.

## 3. Non-Goals

This design does not:

1. Lower strict object matching standards
2. Pretend ambiguous matches are exact
3. Force inline-perfect placement of figure cards in fulltext
4. Solve all figure/table matching quality issues in one step
5. Replace the strict audit inventory with a reader-only inventory

## 4. Layered Architecture

### 4.1 Strict Object Layer

The strict layer remains conservative and audit-first.

Responsibilities:

1. Detect formal figure legends
2. Detect visual assets and clusters
3. Perform strict matching
4. Produce strict outcomes:
   - `matched_figures`
   - `held_figures`
   - `ambiguous_figures`
   - `unmatched_legends`
   - `unresolved_clusters`
   - `orphan_assets`
5. Produce strict completeness:
   - `figure_legend_completeness`

Strict layer standards are not relaxed by this design.

### 4.2 Reader Layer

The reader layer creates stable, human-readable figure objects.

Responsibilities:

1. Convert human-discernible figure information into reader-visible objects
2. Preserve strict status separately from reader status
3. Deduplicate caption/body/render paths using consumed block ids
4. Prevent formal figure information from silently disappearing from reading output

The reader layer is not a garbage bucket. It only accepts:

1. Formal numbered legends
2. Salient visual groups

### 4.3 Audit Layer

The audit layer preserves strict diagnostics and also measures reader coverage.

Responsibilities:

1. Report strict completeness
2. Report reader coverage
3. Detect user-facing hygiene failures such as debug leakage and duplicate captions

## 5. New Module Boundary

Add a dedicated reader synthesis module:

```text
paperforge/worker/ocr_figure_reader.py
```

Primary function:

```python
def synthesize_reader_figures(
    figure_inventory: dict,
    structured_blocks: list[dict],
    document_structure: DocumentStructure | None = None,
) -> dict:
    ...
```

Why a new module:

1. `ocr_figures.py` should remain the strict inventory builder
2. Reader presentation logic is a separate contract
3. This keeps strict, reader, and render responsibilities separable

Implementation constraint:

```text
Reader layer should reuse strict-layer formal legend detection helpers where possible.
It may add exclusions, but it must not maintain an independent conflicting
formal-legend classifier.
```

## 6. Reader Inputs and Synthesis Priority

Reader figure synthesis must follow a fixed priority order to avoid duplicate consumption.

Priority order:

1. `matched_figures` -> `EXACT_MATCH` or `SEQUENCE_MATCH`
2. `held_figures` / `ambiguous_figures` with formal legend + visual candidates -> `GROUPED_APPROXIMATE` or `HOLD`
3. unmatched formal numbered legends -> `LEGEND_ONLY`
4. unresolved salient visual groups -> `ASSET_GROUP_ONLY`
5. remaining debug buckets stay in audit only

Hard dedupe rules:

1. One `legend_block_id` may produce at most one `reader_figure`
2. One `asset_block_id` may be consumed by at most one `reader_figure`
3. Exception: a shared visual group may be referenced by more than one reader object only when explicitly marked shared or held

Reader object invariants:

1. One formal legend can produce at most one reader figure
2. One reader figure can be rendered at most once
3. A consumed caption block must belong to exactly one reader figure
4. Candidate visual assets in `GROUPED_APPROXIMATE` are not consumed unless they are rendered as the representative visual group
5. Reader ids must be stable across rebuilds when figure number and source block ids are unchanged

## 7. Reader Admission Gates

### 7.1 Formal Legend Gate

Not all unmatched legend-like text may enter the reader layer.

Only legends satisfying all of the following are eligible:

1. `marker_signature.type == figure_number`
2. The block is a formal numbered legend candidate
3. The block is not an inline prose mention such as `Figure 2 shows...`
4. The block is not just a panel label
5. The block does not score as high body prose likelihood
6. Caption evidence is not already rejected by strict logic

Implication:

```text
formal numbered legend unmatched -> LEGEND_ONLY candidate
inline mention unmatched -> reject from reader layer
```

### 7.2 Salient Visual Group Gate

Not all unresolved clusters or orphan assets may enter the reader layer.

Eligible salient visual groups must satisfy at least one strong salience condition and no strong exclusion condition.

Strong salience conditions:

1. Large area relative to page
2. Stable cluster of multiple media blocks
3. Location in body or display zone
4. Strong proximity to a formal legend or figure-like reference

Default initial thresholds:

1. Large area: visual bbox area >= 3% of page area
2. Wide-and-tall fallback: width >= 30% of page width and height >= 8% of page height
3. Stable cluster: >= 2 media blocks and cluster bbox area >= 2% of page area

Strong exclusion conditions:

1. Frontmatter sidebar furniture
2. Footer/header publisher furniture
3. Watermark-like decoration
4. Small isolated fragments without figure-like grouping evidence
5. `preproof_cover_zone`
6. Page-1 frontmatter-side furniture band

Implication:

```text
salient unresolved visual group -> ASSET_GROUP_ONLY or HOLD
small noisy fragment -> audit only
```

## 8. Reader Figure Schema

Each reader figure must preserve both reader and strict statuses.

Recommended schema:

```json
{
  "reader_figure_id": "reader_figure_003",
  "figure_number": 3,
  "reader_status": "GROUPED_APPROXIMATE",
  "strict_status": "ambiguous",
  "strict_source": "ambiguous_figures",
  "caption_block_id": "p7_b9",
  "caption_text": "FIGURE 3 | ...",
  "visual_groups": [
    {
      "page": 7,
      "asset_block_ids": ["p7_b10", "p7_b11"],
      "group_status": "candidate_group"
    }
  ],
  "consumed_caption_block_ids": ["p7_b9"],
  "consumed_asset_block_ids": ["p7_b10", "p7_b11"],
  "debug_refs": {
    "matched_figure_id": null,
    "candidate_asset_ids": ["p7_b10", "p7_b11"]
  }
}
```

Hard schema rule:

```text
reader_status and strict_status must be separate fields.
```

Stable id rule:

1. If `figure_number` exists, `reader_figure_id = figure_{number:03d}_reader`
2. If no `figure_number` exists but there is a salient visual group, `reader_figure_id = visual_group_{page}_{ordinal}_reader`
3. If an id collision remains after those rules, append a stable suffix such as `_b`, `_c`, derived from source block ordering

## 9. Reader Status Definitions

### 9.1 `EXACT_MATCH`

Reader-visible figure derived from a strict exact match.

### 9.2 `SEQUENCE_MATCH`

Reader-visible figure derived from a strict match promoted by sequence consistency.

Important:

```text
SEQUENCE_MATCH is a strict/object-layer match status,
not a reader-only approximation label.
```

### 9.3 `GROUPED_APPROXIMATE`

Requirements:

1. Formal legend exists
2. At least one visual group candidate exists
3. Strict layer cannot justify exact or sequence match
4. A human reader could still reasonably understand the approximate correspondence

Hard rule:

```text
No visual candidate => cannot use GROUPED_APPROXIMATE.
```

### 9.4 `LEGEND_ONLY`

Requirements:

1. Formal numbered legend exists
2. No suitable visual group candidate exists

### 9.5 `ASSET_GROUP_ONLY`

Requirements:

1. Salient visual group exists
2. No reliable formal legend is linked

### 9.6 `HOLD`

Represents a reader-relevant but weakly supported figure-like object.

This status must not become a noisy default output path.

Two practical sub-classes exist even if stored as one top-level status:

1. `reader_hold`: enough evidence to render a compact user-visible outcome
2. `audit_hold`: useful for audit only, not rendered in main fulltext

### 9.7 `REJECT`

Excluded from reader output.

## 10. Mapping Rules from Strict to Reader

The synthesis rules are:

1. formal legend + exact strict match -> `EXACT_MATCH`
2. formal legend + sequence strict match -> `SEQUENCE_MATCH`
3. formal legend + candidate visual group(s) but no strict exact/sequence match -> `GROUPED_APPROXIMATE`
4. formal legend + no visual group -> `LEGEND_ONLY`
5. salient visual group + no formal legend -> `ASSET_GROUP_ONLY`
6. weak but still reader-relevant evidence -> `HOLD`
7. everything else -> audit only or reject

## 11. Consumed Block Contract

Reader synthesis must output stable consumed block ids.

Required outputs:

```json
{
  "consumed_caption_block_ids": [],
  "consumed_asset_block_ids": []
}
```

Rules:

1. A caption block may be consumed only if it is represented in a `reader_figure`
2. `LEGEND_ONLY` counts as a valid reader outcome and must consume its caption block if the caption is shown in the figure card
3. `EXACT_MATCH`, `SEQUENCE_MATCH`, `GROUPED_APPROXIMATE`, `LEGEND_ONLY`, and reader-visible `HOLD` consume caption blocks when their caption text is rendered in the figure card
4. `ASSET_GROUP_ONLY` consumes assets but not captions
5. A caption block that does not produce any reader outcome must not be consumed

Asset-consumption refinement:

1. `EXACT_MATCH` and `SEQUENCE_MATCH` consume matched assets
2. `GROUPED_APPROXIMATE` always consumes the caption if rendered, but consumes assets only when a representative visual group is actually rendered
3. Candidate-only assets for `GROUPED_APPROXIMATE` remain in `candidate_asset_ids`, not `consumed_asset_block_ids`
4. `LEGEND_ONLY` consumes caption only
5. Reader-visible `HOLD` consumes only the blocks actually rendered in the hold card
6. Audit-only hold consumes nothing

This contract is required to prevent:

1. Duplicate caption output in body and card form
2. Accidental deletion of useful body content

## 12. Render Contract

### 12.1 Render Source

Fulltext rendering must consume `reader_figures`, not only `matched_figures`.

### 12.2 Body Flow Deduplication

During body rendering:

```python
if block_id in consumed_caption_block_ids:
    skip
```

This must be id-based, not pattern-based. Pattern-only suppression is too risky and may delete real body content.

Figure-card render dedupe:

1. The renderer must maintain `rendered_reader_figure_ids`
2. A `reader_figure_id` may be rendered at most once in fulltext

### 12.3 Debug Artifact Hygiene

The following strings must never appear in user-facing `fulltext.md`:

1. `unmatched_legend_`
2. `unresolved_cluster_`
3. `orphan_`
4. `asset_block_id`
5. `legend_block_id`

These may remain in JSON artifacts and debug refs.

### 12.4 Long Legend Rule

Formal long figure legends must not remain in normal body flow.

They must be moved into figure cards when consumed.

### 12.5 HOLD Rendering Rule

`HOLD` is not a default large figure-card status.

Rules:

1. Only `reader_hold` outcomes may render in user-facing fulltext
2. `reader_hold` should render compactly, not as a large verbose card by default
3. `audit_hold` remains in JSON/audit only

### 12.6 Placement Fallback Order

Full inline-perfect placement is not required initially. Render placement must follow a deterministic fallback order:

1. If a caption block has reliable page and order information, place the figure card near that block or at the end of that page segment
2. If there is no reliable caption placement but a visual group exists, place at the end of the asset page segment
3. If the item looks appendix-like or figure-plate-like, place in a figures appendix section
4. If placement cannot be resolved, place in a document-end figure reader appendix

This avoids both placement chaos and premature investment in high-risk inline insertion logic.

## 13. Strict Layer Enhancement: Sequence Match

Sequence consistency is intentionally deferred.

It should be introduced only after the reader contract is stable.

`SEQUENCE_MATCH` must belong to the strict/object layer and must require evidence such as:

1. Figure numbers are continuous
2. Candidate cluster count is compatible with legend count
3. Document order is consistent
4. Local relations are not contradictory

This is a strict promotion path, not a reader-only approximation.

## 14. New Audit Metrics

Add reader coverage metrics:

```json
{
  "figure_reader_coverage_total": 0,
  "figure_reader_coverage_accounted": 0,
  "figure_reader_coverage_gap_count": 0,
  "figure_reader_coverage_ratio": 1.0
}
```

Definitions:

1. `total`: formal numbered legends that pass the Formal Legend Gate plus salient visual groups that pass the Salient Visual Group Gate and are not already linked to a formal legend
2. `accounted`: number that produced valid reader outcomes
3. `gap_count`: reader-visible missing outcomes
4. `ratio`: accounted / total

Priority rule:

```text
Strict completeness gaps matter.
Reader coverage gaps matter more.
```

## 15. Testing Strategy

### 15.1 Unit Tests

Add tests for:

1. strict-to-reader priority ordering
2. legend deduplication by `legend_block_id`
3. asset deduplication by `asset_block_id`
4. formal unmatched legend -> `LEGEND_ONLY`
5. inline figure mention -> rejected from reader layer
6. unresolved salient visual group -> `ASSET_GROUP_ONLY` or `HOLD`
7. non-salient fragment -> audit only
8. `GROUPED_APPROXIMATE` requires at least one visual candidate
9. `LEGEND_ONLY` consumes caption block when rendered
10. `ASSET_GROUP_ONLY` does not consume caption blocks
11. stable `reader_figure_id` generation from figure number and source blocks

### 15.2 Render Tests

Add tests for:

1. consumed caption blocks do not reappear in body flow
2. debug artifact names do not appear in fulltext
3. long formal legends do not remain in body flow when consumed
4. caption is not duplicated between body flow and figure card
5. reader-visible `HOLD` renders compactly
6. audit-only hold does not render in fulltext
7. a `reader_figure_id` is not rendered more than once

### 15.3 Real-Paper Audit Tests

For the 9-paper cohort, enforce:

1. Every formal numbered legend has a strict outcome
2. Every formal numbered legend has a reader outcome
3. If a legend is consumed, it appears through a reader figure
4. Fulltext contains no debug ids listed above
5. Formal legend text is not simultaneously emitted in body flow and figure card
6. `reader_figures` are not unreasonably sparse relative to formal legend count
7. Every `consumed_caption_block_id` exists in structured blocks
8. Every `consumed_asset_block_id` exists in figure assets or visual media clusters
9. Every `consumed_caption_block_id` belongs to exactly one `reader_figure`
10. Every rendered `reader_figure_id` exists in `reader_figures`

## 16. Acceptance Criteria

### Global

1. Strict matching standards remain unchanged or stricter
2. Reader output no longer depends solely on `matched_figures`
3. Formal figure information no longer disappears silently from user-facing output
4. Debug artifact names do not leak into user-facing markdown
5. Consumed block ids enforce caption deduplication

### Reader-Layer Quality Gates

1. `GROUPED_APPROXIMATE` must have at least one visual candidate
2. `LEGEND_ONLY` must be formal-numbered only
3. `ASSET_GROUP_ONLY` must pass the salient visual group gate
4. Pure debug noise must not become reader output

### Real-Paper Gates

For target real papers:

1. `A8E7SRVS`: Fig. 1-5 must be represented in `reader_figures`, even if strict exact matching remains incomplete
2. `M36WA39N`: long legends must not pollute body flow and duplicate heavily
3. `SAN9AYVR`: duplicated figure-caption body output must be reduced sharply
4. `7C8829BD` and `K7R8PEKW`: unresolved debug artifacts must no longer appear directly as reader-facing fulltext objects

## 17. Phased Execution

### Phase 1: Schema + Reader Synthesis

Implement:

1. `ocr_figure_reader.py`
2. `reader_figures`
3. `reader_coverage`
4. `consumed_caption_block_ids`
5. `consumed_asset_block_ids`

Do not yet modify sequence matching.

### Phase 2: Render Contract Migration

Implement:

1. render from `reader_figures`
2. body-flow skip using consumed ids
3. debug artifact hygiene
4. long-legend removal from body flow
5. deterministic fallback placement

### Phase 3: Strict Layer Enhancement

Add minimal sequence-consistency promotion for `SEQUENCE_MATCH`.

### Phase 4: Real-Paper Audit Lock

Lock behavior with real-paper audit tests over the 9-paper cohort.

## 18. Final Decision

This design should proceed.

The key architectural decision is:

```text
Reader-visible success is a first-class contract.
It is separate from strict object success,
but it must remain traceable back to strict audit status.
```

This preserves strictness without allowing strict mismatch to erase human-usable figure information.
