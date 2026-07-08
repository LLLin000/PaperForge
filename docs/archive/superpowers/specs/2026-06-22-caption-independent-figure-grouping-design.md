# Caption-Independent Figure Grouping Design

> **Date:** 2026-06-22
> **Status:** Proposed
> **Scope:** Redefine the upstream figure-group construction layer so figure groups are built from visual assets first, independent of caption-band partitioning. This spec preserves the existing ledger / reservation / same-page / cross-page matching direction discussed in `2026-06-22-group-first-cross-page-figure-caption-matching-design.md` and changes only the grouping truth feeding that matcher.

This spec also supersedes the earlier Stage 1 assumption that existing grouping/clustering could remain untouched while only the matching layer changed. The upstream grouping layer must now be corrected first, or the downstream matcher will continue to consume caption-conditioned pseudo-groups.

---

## 1. Problem Statement

The current OCR figure pipeline mixes two different responsibilities into one step:

1. **Figure grouping**: determine which visual assets belong to the same visual figure unit
2. **Caption settlement**: decide which caption owns which figure unit

Today, `paperforge/worker/ocr_figures.py::_build_candidate_figure_groups_from_assets()` does not build a caption-independent figure stream on multi-caption pages.
When `n_legends >= 2`, it first runs `_partition_assets_by_caption_bands(...)`, then clusters inside each caption band.

Current effective flow:

```text
raw assets
-> caption-band partitioning
-> per-band asset clustering
-> candidate groups
-> ledger / reserve / settlement
```

This violates the design intent already established for cross-page matching:

```text
raw assets
-> figure groups
-> page ledger
-> reserve
-> same-page settlement
-> cross-page settlement
```

The difference matters because the current grouping step is already conditioned on caption location.
Once assets are pre-assigned to captions by band, the downstream ledger sees a page as locally self-consistent even when the true figure ownership is cross-page.

### Canonical failure: 2HEUD5P9 Figure 4 / Figure 5

Observed layout:

1. **Page 12** contains Figure 4 panels as visual assets
2. **Page 13** contains Figure 4 caption, Figure 5 assets, and Figure 5 caption

What the current grouping layer does:

1. Page 13 has 2 legends
2. Assets on page 13 are partitioned into caption bands for Figure 4 and Figure 5
3. Each band produces local candidate groups
4. Figure 4 therefore appears to already have same-page groups on page 13
5. Page 12 groups are orphaned before the cross-page matcher even gets a fair chance

This is not primarily a matching bug anymore.
It is an upstream truth bug: **group formation is already contaminated by caption heuristics**.

---

## 2. Core Principle

Figure grouping must be a standalone visual truth layer.

### Hard rule

**Captions may validate or rank groups, but captions may not define the initial group boundaries.**

Implications:

1. A multi-caption page may still contain multiple figure groups, but those groups must emerge from the visual asset field first
2. Caption-band logic is not allowed to be the first splitter that determines group identity
3. The ledger must operate on caption-independent groups, not caption-conditioned bands

### Separator carve-out

Caption independence does **not** mean caption blindness.

Caption and text blocks may still be used as **neutral visual separators / barriers** when deciding whether two asset regions remain visually continuous.

Allowed:

```text
Use caption/text blocks to answer:
"Are these two asset regions physically interrupted by intervening text?"
```

Forbidden:

```text
Use caption identity to answer:
"Which caption already owns this asset before groups exist?"
```

In short:

```text
caption/text may block continuity,
caption identity may not pre-assign ownership bands
```

---

## 3. Goals

This grouping spec must:

1. Preserve the previously discussed matching direction: ledger -> reserve -> same-page settlement -> cross-page settlement
2. Make figure groups arise from visual adjacency and figure-internal signals first
3. Prevent multi-caption pages from becoming falsely self-balanced purely because assets were pre-divided by caption position
4. Keep band / local caption geometry available as a downstream validation signal for same-page tie-breaking
5. Minimize disruption to the existing matching pipeline in Stage 1

---

## 4. Non-Goals

This spec does not:

1. Rewrite the downstream ledger / reservation / settlement design
2. Introduce ML or learned page classification
3. Solve every orphan rendering issue
4. Replace existing formal caption detection
5. Require a full end-to-end rewrite of `build_figure_inventory()` in one step

---

## 5. Architectural Split

The figure pipeline should explicitly separate two layers.

### 5.1 Semantic grouping layer

Inputs:

1. `figure_asset`
2. `media_asset`
3. optional figure-internal textual markers such as `figure_inner_text`

Behavior:

1. Build visual figure groups independent of caption bands
2. Determine group boundaries from visual adjacency, spacing, and figure-internal continuity
3. Allow neutral layout separators, including caption/text blocks, to block continuity where they physically interrupt the visual field
4. Produce stable page-local figure candidates for ownership

### 5.2 Settlement-assist layer

Inputs:

1. semantic groups from 5.1
2. captions / legends
3. optional caption-band geometry

Behavior:

1. run page ledger / residual ledger
2. reserve surplus legends or groups
3. perform same-page settlement
4. perform cross-page settlement
5. use band / geometry only as supporting evidence, not as upstream truth

---

## 6. Current Conflict To Remove

Current `_build_candidate_figure_groups_from_assets()` behavior on `n_legends >= 2`:

```python
if n_legends >= 2:
    band_map = _partition_assets_by_caption_bands(page_legends, page_media, page_height)
    partitions = ...
else:
    partitions = [(None, list(page_media))]

for band_id, partition in partitions:
    clusters = _cluster_page_assets(partition, ...)
```

This means a multi-caption page is grouped differently solely because captions are present.

That behavior is the conflict.

The grouping layer should not ask:

```text
Which caption band does this asset sit near?
```

It should ask first:

```text
Which neighboring assets does this asset visually belong with?
```

Only after those groups exist may caption-band evidence be used to check whether a local caption/group association is plausible.

### Hidden second conflict: caption-count-aware clustering

The contamination is not limited to `_partition_assets_by_caption_bands(...)`.

Current `_cluster_page_assets(...)` also takes `n_legends` and changes merge behavior based on caption count.
That means even if band partitioning were removed, semantic grouping could still remain caption-conditioned if it reuses the same caption-count-sensitive topology rules.

Required rule:

```text
Semantic grouping must not use `n_legends` or caption count to decide whether visual assets belong together.
```

Implementation implication:

1. semantic grouping must bypass current caption-count-dependent clustering behavior, or
2. current clustering must be wrapped/refactored with an explicit semantic mode that does not consult caption count

---

## 7. Proposed Grouping Model

### 7.1 Build semantic groups per page from the full page asset set

For each page:

1. collect all figure-like assets on the page
2. cluster them visually using the existing asset clustering logic as the primary base
3. allow figure-internal continuity signals to keep assets together when they belong to one composite figure
4. allow caption/text blocks as neutral separators only
5. do not split by caption bands during this phase
6. do not let caption count alter semantic topology during this phase

The result is a caption-independent group stream:

```python
semantic_groups = build_semantic_figure_groups(page_assets, page_blocks)
```

### 7.2 Optional same-page assist groups

Band partitioning may still exist, but only as a secondary assist stream:

```python
band_local_groups = build_caption_band_local_groups(page_legends, page_assets, page_blocks)
```

Rules:

1. `band_local_groups` may help same-page validation or tie-breaking
2. `band_local_groups` may not be the group stream used by ledger or reservation
3. `band_local_groups` may not redefine semantic group identity
4. `band_local_groups` must be attachable back to semantic groups as assist metadata, not as replacement groups

### 7.3 Required relation between semantic groups and band assist

If band-local evidence is used downstream, it must be attachable back to semantic groups explicitly.

Accepted shapes include embedded assist metadata:

```python
{
    "group_id": str,
    "page": int,
    "asset_block_ids": list[str],
    "cluster_bbox": list[int],
    "group_type": str,
    "assist": {
        "caption_band_ids": list[str],
        "band_overlap": {str: float},
    },
}
```

or a separate side map:

```python
band_assist_by_group_id = {
    "group_0001": {
        "best_caption_band_id": str | None,
        "overlap_ratio": float,
        "evidence": list[str],
    }
}
```

Hard rule:

```text
band assist must be keyed by semantic group identity;
it may not create an alternative group universe that ledger consumes
```

---

## 8. Grouping Invariants

### 8.1 Semantic groups are caption-independent

Changing caption positions or caption count may not change semantic grouping of the same asset field, except where captions are only used as weak validation metadata after groups already exist.

### 8.2 Same page, same visual field, same semantic groups

If a page's visual assets are unchanged, adding or removing a second caption may not cause the page to be repartitioned into a different semantic group topology.

Equivalent acceptance phrasing:

```text
same visual assets + different caption count
=> same semantic group topology
```

Semantic topology comparison must use sorted sets of `asset_block_ids` per group, not generated `group_id` values.

Suggested comparison form:

```python
{frozenset(g["asset_block_ids"]) for g in semantic_groups}
```

### 8.3 Settlement consumes groups, not bands

Ledger and reservation must only count semantic groups.

### 8.4 Band logic is evidence, not truth

Caption-band assignment may:

1. down-rank a same-page candidate
2. prefer one already-valid same-page candidate over another
3. support sidecar handling

Caption-band assignment may not:

1. create a semantic group boundary
2. suppress a semantic group from ledger accounting
3. make a page look self-balanced before reserve logic runs

Caption/text movement may affect grouping only when it physically changes neutral separator/barrier geometry; caption identity, caption count, or ownership-band assignment alone may not change semantic topology.

### 8.5 No aggregate page group as semantic truth on competing-caption pages

An aggregate "all assets on the page" helper may still exist for debugging or weak fallback, but on competing-caption pages it may not be treated as semantic ledger truth.

Reason:

```text
semantic grouping on multi-caption pages must prefer visually separated clusters
over collapsing the whole page into one ownership truth object
```

---

## 9. Required Contract Changes

### 9.1 `build_figure_inventory()`

The grouping/matching boundary becomes:

```text
collect legends/assets
-> build semantic_groups (caption-independent)
-> build raw/residual ledger from semantic_groups
-> compute reservations
-> same-page settlement (may consult band_local_groups)
-> cross-page settlement
-> legacy fallback with ownership guards
```

### 9.2 `_build_candidate_figure_groups_from_assets()`

This function currently mixes grouping truth with caption-band partitioning.

Required Stage 1 refactor direction:

1. either split it into two helpers:
   - `build_semantic_figure_groups(...)`
   - `build_caption_band_local_groups(...)`
2. or change its contract so its primary return is semantic groups and any band-local derivation is explicit side metadata

Additional requirement:

```text
semantic grouping path may not call caption-band partitioning,
and may not pass caption count into topology-changing clustering logic
```

### 9.3 Ledger inputs

`_build_page_ledger()` and `_build_residual_ledger()` must consume semantic groups only.

They may not consume caption-band-local groups.

### 9.4 Matching plan update requirement

Any implementation plan that assumes "keep current clustering unchanged" must be updated.

New Stage 1 baseline:

```text
1. build semantic_groups first
2. ledger / reservation consume semantic_groups only
3. same-page settlement may consult band assist
4. legacy fallback still obeys ownership guards
```

---

## 10. Interaction With Existing Matching Spec

This spec does **not** replace the matching spec.
It corrects the upstream assumption needed to make that spec valid.

### Matching logic that remains valid

The following ideas still stand:

1. reserve before same-page matching
2. skip reserved objects during same-page settlement
3. reserved legends look backward
4. reserved groups look forward
5. band / geometry can help local same-page validation

### What changes

Only this:

```text
the objects being counted and reserved must come from semantic grouping,
not from band-conditioned grouping
```

And therefore the earlier Stage 1 matching plan must be interpreted as depending on this grouping correction first, or be amended to include it directly.

---

## 11. 2HEUD5P9 Expected Behavior Under This Grouping Design

Desired upstream truth:

1. Page 12 semantic assets form a Figure 4 visual group
2. Page 13 semantic assets form the local figure group(s) actually visible on page 13
3. Page 13 should not appear self-balanced merely because Figure 4 caption was used to create a Figure 4 band on page 13

Desired downstream effect:

1. Ledger sees a real mismatch between page 12 groups and page 13 captions/groups
2. Figure 4 can be reserved and matched backward
3. Figure 5 keeps local page 13 ownership
4. Page 12 Figure 4 panels no longer remain orphaned because of a false same-page local match on page 13

---

## 12. Migration Strategy

### Stage 1: separate truth from evidence

1. keep the downstream matching logic already discussed
2. introduce caption-independent semantic grouping
3. keep caption-band grouping only as same-page assist metadata
4. switch ledger / residual ledger inputs to semantic groups
5. ensure semantic grouping still respects neutral separator barriers and does not regress ordinary same-page multi-figure pages

### Stage 2: tighten same-page assist usage

1. explicitly document where band-local evidence may influence scoring
2. remove any remaining places where band-local groups silently behave like semantic groups

### Stage 3: remove dead assumptions

1. clean up any dead `page_assets`-style code paths that are no longer produced by the actual group builder
2. make group-type contracts explicit and test-backed

---

## 13. Required Tests

### 13.1 Caption count does not change semantic topology

Given the same visual asset set:

1. case A: one caption
2. case B: two captions

Expectation:

```text
semantic group asset topology is unchanged
```

### 13.2 Caption-band assist does not enter ledger

Expectation:

```text
band_local_groups may exist,
but _build_page_ledger() and _build_residual_ledger() count semantic_groups only
```

### 13.3 Ordinary same-page two-figure page does not collapse

Expectation:

```text
removing band partition from semantic truth must not collapse
two visually separated same-page figures into one semantic group
```

### 13.4 Caption as separator remains allowed

Expectation:

```text
two asset clusters physically separated by intervening caption/text
may remain separate because the text acts as a neutral barrier,
not because the caption pre-owns either side
```

### 13.5 2HEUD5P9 upstream truth check

Expectation:

```text
page 13 Figure 4 caption must not create a fake page-13 Figure-4 semantic group
before reserve logic runs
```

---

## 14. Acceptance Criteria

This grouping redesign is accepted only if all are true:

1. multi-caption pages are not semantically pre-split by caption bands before ledger construction
2. changing caption geometry alone does not redefine semantic group identity
3. ledger / residual ledger operate on caption-independent groups
4. same-page band logic remains available as a downstream validation aid only
5. 2HEUD5P9 no longer fails because Figure 4 already appears locally satisfied on page 13 before reserve logic runs
6. existing ordinary same-page multi-figure layouts do not regress in local ownership quality
7. semantic grouping still permits text/caption blocks to behave as neutral visual separators
8. caption count alone does not change semantic group topology

---

## 15. Implementation Notes

The key discipline is simple:

```text
group first from vision,
caption second for ownership
```

If captions help define groups, the matcher is already biased before it starts.
That is exactly the conflict this spec removes.
