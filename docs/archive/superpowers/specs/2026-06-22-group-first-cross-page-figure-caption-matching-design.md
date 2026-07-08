# Group-First Cross-Page Figure-Caption Matching Design

> **Date:** 2026-06-22
> **Status:** Proposed
> **Scope:** Replace caption-first figure matching with group-first, page-ledger-based figure/caption settlement across same-page and cross-page layouts
> **Supersedes:** None directly. Refines the matching stage after `2026-06-21-global-distance-clustering-figure-merge.md`

---

## 1. Problem Statement

The current figure pipeline can already recognize both sides of the problem:

1. **Figure-side objects**: `figure_asset`, `media_asset`, `figure_inner_text`, clustered figure-like regions
2. **Caption-side objects**: formal numbered legends such as `Figure 4. ...`

The recurring failures are no longer primarily about missing detection. They are about **matching order and ownership**.

Current failure mode:

```text
caption -> pick nearby asset(s) -> consume asset(s) -> maybe merge later
```

This creates three structural problems:

| Problem | Why it happens | Consequence |
|---------|----------------|-------------|
| **Caption steals the wrong same-page figure** | Same-page spatial scoring is attempted before cross-page settlement | A caption on page N+1 can consume another figure's panels on page N+1 instead of its own panels on page N |
| **Cross-page figures are treated as fallback exceptions** | Previous-page matching is a narrow heuristic gate, not a first-class layout mode | Full-page figures with captions on the next page become fragile and layout-dependent |
| **Merge happens too late** | Matching is still effectively asset-first, while grouping is only partial pre-processing | Two captions can compete over fragments of what should have been one figure group |

The 2HEUD5P9 Figure 4 / Figure 5 case is a canonical example:

1. Page 12 contains Figure 4 panels as visual assets
2. Page 13 contains Figure 4 caption, Figure 5 assets, and Figure 5 caption
3. Same-page scoring favors page 13 assets for Figure 4 because they are spatially close
4. The real Figure 4 visual group on page 12 loses to the wrong same-page candidate

This is not a one-off bug. It exposes the wrong matching philosophy.

---

## 2. Core Design Principle

The matching unit must be a **stable figure group**, not a raw asset.

The processing order must be:

```text
raw assets
-> figure groups
-> page ledger
-> reserve surplus captions/groups
-> same-page settlement among non-reserved objects
-> cross-page settlement for reserved/residual objects
-> weak tie-breaks
```

Not:

```text
caption -> raw asset match -> consume -> try to merge/fallback later
```

### Hard rule

**Group formation is upstream truth. Matching may consume groups, but matching may not redefine grouping.**

Implications:

1. A caption never matches a bare asset directly if that asset belongs to a figure group
2. A figure group may be matched by at most one caption
3. Two captions may never "share" a figure group unless the system explicitly emits a held/ambiguous state rather than a match

---

## 3. Goals

This design must:

1. Make cross-page figure/caption layouts a normal supported pattern, not a heuristic exception
2. Make grouping happen before caption ownership
3. Prevent a caption from stealing another figure's same-page panels when page-level count balance indicates a cross-page pairing
4. Support both directions:
   - extra caption on current page -> look backward for figure group
   - extra figure group on current page -> look forward for caption
5. Keep the logic independent from body prose analysis as much as possible

---

## 4. Non-Goals

This design does not:

1. Rebuild OCR block detection from scratch
2. Replace the existing asset clustering algorithm in this phase
3. Solve all orphan rendering UX issues
4. Relax legend recognition standards
5. Introduce ML ranking or learned layout classification

---

## 5. New Matching Model

### 5.1 Separate the two streams

The pipeline should explicitly build and carry two independent streams:

1. **Figure groups**
2. **Legends**

These streams are settled against each other later.

#### Figure group

A figure group is the stable visual object created before legend matching.

Minimum fields:

```python
{
    "group_id": str,
    "pages": list[int],
    "asset_block_ids": list[str],
    "panel_label_block_ids": list[str],
    "cluster_bbox_by_page": dict[int, list[int]],
    "union_bbox": list[int],
    "asset_count": int,
    "group_type": str,
}
```

#### Legend

Legend is any formal numbered figure caption that passes the existing formal-legend gate.

Minimum fields:

```python
{
    "legend_block_id": str,
    "page": int,
    "figure_number": int,
    "figure_namespace": str,
    "bbox": list[int],
    "text": str,
}
```

---

## 6. Page Ledger Model

Instead of classifying pages into many semantic types, use a simple **page ledger** over figure-only signals.

For each page, compute a raw ledger first:

```python
{
    "page": int,
    "legend_count": int,
    "numbered_legend_count": int,
    "group_count": int,
    "top_legend_count": int,
    "bottom_legend_count": int,
    "delta": legend_count - group_count,
}
```

This raw ledger is only a **signal**, not a direct settlement instruction.

### 6.1 Residual ledger

Settlement must operate on a second ledger built from strong, eligible residual objects:

```python
{
    "page": int,
    "unmatched_strong_legend_count": int,
    "unmatched_matchable_group_count": int,
    "residual_delta": unmatched_strong_legend_count - unmatched_matchable_group_count,
}
```

Why two ledgers are required:

1. Raw page counts can include weak/truncated legends
2. Raw page counts can include unresolved or unmatchable groups
3. Settlement decisions must be based on **eligible unowned objects**, not raw detection totals

### 6.2 Surplus helpers

The reservation phase must not leave surplus arithmetic implicit.

Required helper contracts:

```python
def residual_group_surplus(pages: list[int], residual_ledger: dict[int, dict]) -> int:
    return sum(
        max(0, residual_ledger[p]["unmatched_matchable_group_count"] - residual_ledger[p]["unmatched_strong_legend_count"])
        for p in pages if p in residual_ledger
    )


def residual_legend_surplus(pages: list[int], residual_ledger: dict[int, dict]) -> int:
    return sum(
        max(0, residual_ledger[p]["unmatched_strong_legend_count"] - residual_ledger[p]["unmatched_matchable_group_count"])
        for p in pages if p in residual_ledger
    )
```

These helpers define `K` in the reservation rules. The implementation may optimize them, but it may not silently reinterpret surplus arithmetic.

### Interpretation

| Condition | Meaning |
|-----------|---------|
| `delta == 0` | Same-page settlement should usually be sufficient |
| `delta > 0` | More captions than figure groups on this page; at least some captions should look backward |
| `delta < 0` | More figure groups than captions on this page; at least some groups should look forward |

This ledger is intentionally minimal. It only reasons over the figure/caption stream, not over general body-page taxonomy.

---

## 7. Matching Phases

### Phase 1: Group Formation

Existing group formation remains upstream truth.

Requirements:

1. Run visual clustering first
2. Assign every asset to at most one group
3. Do not let later caption matching split or reshape groups
4. Preserve `caption_band_id` as metadata only; it may guide settlement but may not override group identity

### 7.0 Eligibility contracts

Before reservation or settlement, both streams must be filtered to **eligible** objects.

#### Strong numbered legend

`strong numbered legend` means:

1. `figure_number` exists
2. Existing formal legend gate passes
3. Not `_is_insufficient_legend_evidence()`
4. `caption_score >= 0.4`

If the legend entered through validation-first recovery, it must additionally satisfy at least one strong support signal:

1. `anchor_supported`, or
2. `caption_text_supported`

Otherwise it may remain held/ambiguous, but it must not participate in reservation arithmetic.

#### Matchable group

`matchable group` means:

1. `asset_block_ids` is non-empty
2. group is not already owned
3. group is not `_non_body_media`
4. group has a valid `cluster_bbox`
5. group type is not currently suppressed by a higher-priority local mode

For Stage 1, `page_assets` groups on competing-caption pages are not matchable groups for ledger settlement.

### Phase 2: Reserve Before Same-Page Settlement

This is the critical rule missing from caption-first matching.

Same-page settlement may not run naively on every caption/group on a page.

If page `P` has figure/caption imbalance, some objects must be reserved for cross-page settlement first.

#### Rule A: caption-surplus reservation

If `residual_delta(P) > 0`:

1. Compute `K = min(residual_delta(P), residual_group_surplus(P-1, P-2))`
2. Reserve the earliest/topmost `K` strong numbered legends on page `P`
3. Reserved legends may not participate in same-page ownership in this phase

Interpretation:

```text
If the page has more strong captions than matchable groups,
some captions are presumed to belong to earlier pages.
```

#### Rule B: group-surplus reservation

If `residual_delta(P) < 0`:

1. Compute `K = min(-residual_delta(P), residual_legend_surplus(P+1, P+2))`
2. Reserve the latest/bottommost `K` unowned groups on page `P`
3. Reserved groups may not be consumed by same-page legends in this phase

Interpretation:

```text
If the page has more groups than strong captions,
some groups are presumed to belong to later pages.
```

### Phase 3: Same-Page Settlement

Within a page:

1. Match legends to groups in natural reading order
2. Only group-level objects participate
3. Resolve obvious one-to-one same-page cases first
4. Reserved legends/groups are excluded from this phase
5. Do not consume unmatched residual groups or legends yet

Same-page settlement is allowed to use spatial scoring, but only among page-local groups and only after reservation has been applied.

### 7.1 Same-page settlement contract

Same-page settlement must explicitly distinguish the following modes:

1. **Obvious one-to-one page**
   - one strong legend
   - one matchable group
   - no prior/next page residual debt
2. **Balanced multi-pair page**
   - equal strong legends and matchable groups
   - no prior/next page residual debt
3. **Caption-surplus page**
   - reserve surplus legends before same-page matching
4. **Group-surplus page**
   - reserve surplus groups before same-page matching
5. **Sidecar/narrow-caption page**
   - use local caption-band/sidecar partition mode

#### Stage 1 restriction for sidecar pages

To avoid destabilizing already-repaired local sidecar behavior, Stage 1 implementation should exclude sidecar/narrow-caption pages from ledger reservation.

That means:

1. run local sidecar settlement first on those pages
2. only if sidecar mode fails completely may a later phase escalate to cross-page logic

This prevents same-page geometric score from reintroducing the original stealing bug.

### Phase 4: Cross-Page Settlement

After reservation and same-page settlement, use residual ledger state.

#### Rule A: extra caption(s) on page P

If page `P` has residual unmatched legends and `residual_delta(P) > 0`:

1. Search unmatched groups on `P-1`, then `P-2`
2. Prefer nearest prior page with residual unmatched groups
3. Match reserved legends in page order, not by raw same-page score
4. If previous-page matching fails, the legend remains unresolved/ambiguous; it may not re-enter same-page stealing

Interpretation:

```text
caption surplus means the page owes figure groups from earlier pages
```

#### Rule B: extra figure group(s) on page P

If page `P` has residual unmatched groups and `residual_delta(P) < 0`:

1. Search unmatched legends on `P+1`, then `P+2`
2. Prefer nearest later page with residual unmatched legends
3. Match reserved groups in page order, not by raw same-page score

Interpretation:

```text
group surplus means the page owes captions from later pages
```

### 7.2 Lightweight cross-page blockers

The design should avoid full body-page classification, but it still needs light blockers for longer jumps.

Rules:

1. `P-1` / `P+1` cross-page settlement is generally allowed if residual ledger supports it
2. `P-2` / `P+2` settlement requires no strong interruption on the intervening page
3. Strong interruption means section heading / table ownership / reference zone / dense body prose that clearly breaks figure continuation

For Stage 1, `strong interruption` should be implemented conservatively via explicit roles, not a new body classifier.

```python
INTERRUPTION_ROLES = {
    "section_heading",
    "subsection_heading",
    "sub_subsection_heading",
    "table_caption",
    "table_html",
    "reference_heading",
    "reference_item",
    "backmatter_heading",
    "backmatter_body",
}
```

Optional simple prose blocker for Stage 1:

```text
intervening page body_paragraph count >= 3 => treat as strong interruption
```

This is not body-prose ranking. It is only a blocker to prevent long-distance ledger misuse.

### Phase 5: Weak Tie-Breaking

Only after same-page and cross-page settlement have both run:

1. Use geometric score to break ties among still-valid candidates
2. Never use weak score to override already-balanced page-ledger settlement

This means **direction is decided before score**.

---

## 8. Settlement Invariants

These are hard constraints.

### 8.1 One group, one owner

```text
one figure group -> at most one matched legend
one legend -> at most one matched figure group
```

If two captions compete for one group:

1. Do not greedily consume it
2. Emit conflict/ambiguous state
3. Leave ownership unresolved rather than silently stealing it

### 8.2 Merge precedes ownership

No caption is allowed to match a member asset of a multi-asset group while bypassing the group.

### 8.3 Cross-page settlement is symmetric

Backward and forward settlement must both be supported:

1. `legend surplus -> look backward`
2. `group surplus -> look forward`

No special-case asymmetry should remain in the architecture.

---

## 9. Settlement Invariants

These are hard constraints.

### 9.1 One group, one owner

```text
one figure group -> at most one matched legend
one legend -> at most one matched figure group
```

If two captions compete for one group:

1. Do not greedily consume it
2. Emit conflict/ambiguous state
3. Leave ownership unresolved rather than silently stealing it

### 9.2 Merge precedes ownership

No caption is allowed to match a member asset of a multi-asset group while bypassing the group.

### 9.3 Cross-page settlement is symmetric

Backward and forward settlement must both be supported:

1. `legend surplus -> look backward`
2. `group surplus -> look forward`

No special-case asymmetry should remain in the architecture.

### 9.4 Failed reservation settlement must not backslide

If a reserved object fails cross-page settlement:

1. it may enter `ambiguous_figures` / held state
2. it may remain in unmatched output for audit visibility
3. it may **not** re-enter same-page greedy ownership later in the pipeline

Required outputs:

```text
reserved legend failed -> hold_reason="reserved_cross_page_no_valid_group"
reserved group failed  -> hold_reason="reserved_cross_page_no_valid_legend"
```

This rule is what prevents the old fallback chain from silently re-stealing ownership.

---

## 10. Required Changes to Current Pipeline

### 10.1 `caption_group_assignments()`

This function is for same-page rendering support only.

Contract change:

1. It must only compare captions and assets on the same page
2. It must not participate in cross-page semantic ownership

Reason:

Page-local coordinates are not comparable across pages.

### 10.2 `build_figure_inventory()`

This becomes the single semantic truth surface for figure/caption ownership.

Contract changes:

1. Main same-page match consumes only figure groups
2. Reservation happens before same-page match on imbalanced pages
3. Residual unmatched legends and groups enter ledger-based settlement
4. Sequential fallback is renamed conceptually to **cross-page settlement** and becomes a primary stage, not a weak afterthought

Stage 1 implementation constraint:

```text
Do not rewrite build_figure_inventory() end-to-end.
Keep current group formation and current output shape.
Insert reservation + primary cross-page settlement ahead of legacy fallback.
```

### 10.3 Existing previous-page gate

`_allow_previous_page_sequential_match()` is currently too shape-specific.

Current weakness:

1. It relies on caption-at-page-top heuristics
2. It checks the first asset bbox, not the group bbox
3. It behaves like a patch gate rather than a general cross-page policy

Required redesign:

1. Input should be a **group**, not a single first asset
2. Use group bbox / page ledger residuals
3. Remove assumptions that only page-top captions may match backward

### 10.4 Matched figure page semantics

The current output schema overloads `page`.

Cross-page matching requires explicit separation of asset page and legend page.

Required output fields:

```python
{
    "page": int,                 # primary asset/crop/render page
    "asset_pages": list[int],    # pages carrying matched visual group assets
    "legend_page": int,          # page carrying formal caption
    "settlement_type": str,      # same_page | cross_page_backward | cross_page_forward
}
```

Why:

1. crop/render needs the asset page
2. reader placement and audit need the legend page
3. cross-page matches cannot safely overload one field to mean both

Backward-compatible Stage 1 interpretation:

```text
matched_figures.page == primary asset/crop page
```

This must remain true for object extraction.

---

## 11. Proposed Matching Contract

### 11.1 Inputs

```python
groups = build_figure_groups(assets, panel_labels)
legends = collect_formal_legends(blocks)
raw_ledger = build_page_ledger(groups, legends)
residual_ledger = build_residual_ledger(groups, legends)
```

### 11.2 Settlement

```python
reserved_legends, reserved_groups = reserve_cross_page_objects(groups, legends, residual_ledger)
same_page_matches, residual_legends, residual_groups = settle_same_page(
    groups, legends, residual_ledger,
    reserved_legends=reserved_legends,
    reserved_groups=reserved_groups,
)
cross_page_matches = settle_cross_page(
    residual_groups,
    residual_legends,
    residual_ledger,
    reserved_legends=reserved_legends,
    reserved_groups=reserved_groups,
)
final_matches = same_page_matches + cross_page_matches
```

### 11.2a Stage 1 implementation mapping

Stage 1 should map this contract onto the current pipeline with minimal disruption:

1. keep current `_build_candidate_figure_groups_from_assets()`
2. build raw/residual ledger from current legends + candidate groups
3. compute `reserved_legend_ids` / `reserved_group_ids` before the current caption loop
4. current same-page caption loop skips reserved objects
5. run primary cross-page settlement before current legacy fallback chain
6. legacy single-asset fallback may only consume assets that do not belong to any group

### 11.3 Priority

```text
1. group formation
2. raw page ledger
3. residual ledger
4. reserve surplus captions/groups
5. same-page settlement among non-reserved objects
6. cross-page settlement for reserved/residual objects
7. weak geometric tie-breaks
8. unresolved -> ambiguous/held, never silent theft
```

---

## 12. 2HEUD5P9 Expected Behavior Under This Design

### Observed counts

```text
page 12: groups > legends
page 13: legends > groups
```

### Natural settlement

1. Raw ledger identifies page 13 caption surplus
2. Reservation reserves the earliest/topmost surplus legend on page 13: Figure 4
3. Same-page settlement excludes reserved Figure 4 and consumes Figure 5 against page 13 visual groups
4. Cross-page settlement matches reserved Figure 4 backward to page 12 figure group(s)

Expected outcome:

1. Figure 4 does **not** consume page 13 Figure 5 panels
2. Figure 4 no longer leaves page 12 panels as orphan media
3. Figure 5 keeps ownership of its page 13 assets

---

## 13. Migration Strategy

### Stage 1

Keep existing clustering. Add raw ledger + residual ledger + reservation before same-page settlement.

Do not replace the entire caption loop in this stage. The goal is to insert ledger-aware reservation and primary cross-page settlement while preserving current clustering and current render payloads.

### Stage 2

Extract settlement helpers:

```python
collect_figure_legends()
build_figure_groups()
build_page_ledger()
build_residual_ledger()
reserve_cross_page_objects()
settle_same_page()
settle_cross_page()
```

### Stage 3

Limit old single-asset sequential fallback to bare assets that do not belong to any group.

---

## 14. Acceptance Criteria

The implementation is accepted only if all are true:

1. No caption may consume bare assets that belong to a merged figure group
2. No two captions may consume the same figure group
3. A page with caption surplus may match backward without requiring caption-at-page-top heuristics
4. A page with group surplus may match forward without requiring ad hoc bundle exceptions
5. 2HEUD5P9 Figure 4 matches page 12 visual groups; Figure 5 keeps page 13 visual groups
6. Orphan count must not increase because a same-page wrong match blocked a valid cross-page match
7. A conflicting two-caption / one-group case resolves to ambiguous/held, not silent duplicate ownership
8. Legacy bare-asset fallback may not consume any asset already owned by a group
9. Stage 1 implementation preserves existing same-page one-to-one figure behavior outside reserved pages

---

## 15. Implementation Notes

This design intentionally avoids a heavy page classifier.

The page ledger is the minimum viable abstraction because it answers the actual question the matcher needs:

```text
Does this page have too many captions or too many figures?
```

That signal is enough to drive natural cross-page settlement without baking more same-page geometric patches into the pipeline.

This design is intentionally **not yet implementation-ready** until the reservation and residual-ledger rules above are respected. A naive "same-page first, cross-page later" implementation will recreate the existing 2HEUD5P9 ownership bug.
