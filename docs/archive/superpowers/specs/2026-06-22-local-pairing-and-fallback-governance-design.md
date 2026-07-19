# Local Pairing And Fallback Governance Design

> **Date:** 2026-06-22
> **Status:** Proposed
> **Scope:** Define a unified model for how semantic figure groups, local caption-group pairing modes, page-level ledger checks, ownership state, and late fallback paths should interact. This spec exists to prevent one-off fixes for sidecar, caption-above, cross-page, preproof, legacy fallback, and table/figure conflicts from drifting into contradictory heuristics.

---

## 1. Why This Spec Exists

The current figure pipeline has already been improved in two important ways:

1. grouping truth is now caption-independent via semantic grouping
2. some late fallback theft has already been reduced via grouped-asset guards

But the pipeline still lacks one unified governance model for how all of these should relate:

1. semantic grouping truth
2. local same-page pairing
3. caption-above vs caption-below vs sidecar interpretation
4. page-level reserve / cross-page settlement
5. late fallback paths (`sidecar`, `legend_bundle`, `group_sequential`, `sequential`, `sequence_match`)
6. figure/table asset ownership boundaries

Without a unifying model, the system will continue to accrete one heuristic per failure mode.
That creates three kinds of risk:

```text
1. contradictory ownership rules
2. fallback paths that steal already-owned assets
3. journal-specific layout fixes that regress other layouts
```

This spec exists to define the full pipeline contract before more localized fixes are added.

---

## 2. Current Pipeline Reality

As of the current code in `paperforge/worker/ocr_figures.py`, the figure pipeline is effectively:

```text
collect legends/assets
-> build semantic candidate groups
-> attach caption-band assist metadata
-> build ledger / residual ledger
-> reserve some legends/groups for cross-page settlement
-> same-page matching using `_score_legend_to_group()`
-> cross-page settlement for reserved objects
-> sidecar fallback
-> preproof legend_bundle fallback
-> group-aware sequential fallback
-> old sequential fallback for ungrouped assets
-> sequence_match promotion
```

This is already a layered system.
The remaining problem is not that stages are missing.
The problem is that the stages still do not share one coherent ownership policy.

### Dependency note

This governance spec assumes or requires two upstream foundations:

1. caption-independent semantic grouping truth
2. group-first ledger / reservation / cross-page matching design

If either foundation is absent in a branch, this spec should be read as the target governance model rather than as a statement that the implementation has already achieved it.

---

## 3. Core Principle

The pipeline must distinguish three different kinds of truth.

### 3.1 Semantic truth

```text
Which visual assets belong to the same figure group?
```

This is defined by visual grouping only.
It must not be pre-assigned by caption ownership.

### 3.2 Local pairing truth

```text
How does a caption relate to a nearby semantic group on this page?
```

This is not group formation.
It is local interpretation of an already-existing caption-group neighborhood.

### 3.3 Page-level / cross-page settlement truth

```text
If some captions or groups remain locally unresolved,
should ownership stay same-page, look backward, or look forward?
```

This is not local geometry alone.
It uses page-level consistency and reserve logic.

---

## 4. The Three Local Pairing Modes

Local caption/group pairing must no longer be treated as one default geometry with one-off exceptions.

The pipeline should recognize three primary local pairing modes.

### 4.1 `caption_below`

The caption sits below its semantic group.

Typical signals:

1. group bbox is above caption bbox
2. strong horizontal overlap
3. vertical distance is small and uninterrupted
4. no strong text barrier between the group and caption

This is the default local mode, but it is not universally correct.

### 4.2 `caption_above`

The caption sits above its semantic group.

Typical signals:

1. caption bbox is above group bbox
2. strong horizontal overlap
3. vertical distance is small and uninterrupted
4. repeated caption-above pattern appears on the page or in the local neighborhood

This must be treated as a valid local mode, not a damaged `caption_below` case.

### 4.3 `caption_sidecar`

The caption sits beside its semantic group, usually in the same row or local horizontal band.

Typical signals:

1. strong y-overlap / row alignment between caption and group
2. horizontal adjacency is stronger than vertical adjacency
3. the caption is narrow relative to the page
4. the caption-group pairing is monotonic with neighboring caption/group pairs

Important:

```text
sidecar is not defined by "two narrow captions on a page"
```

Sidecar may occur with:

1. one caption + one figure
2. multiple captions + multiple figures
3. mixed pages where one caption/group pair is sidecar while others are below/above

Therefore sidecar must be modeled as a **local pairing mode**, not a page type.

---

## 5. Local Pairing Produces Hypotheses, Not Ownership

This is the most important governance rule.

`caption_below`, `caption_above`, and `caption_sidecar` are **local pairing hypotheses**.
They are not accepted ownership yet.

Each hypothesis may carry fields such as:

```python
{
    "legend_block_id": str,
    "group_id": str,
    "mode": "caption_below" | "caption_above" | "caption_sidecar",
    "local_score": float,
    "evidence": list[str],
    "conflicts": list[str],
    "would_consume_asset_ids": list[tuple[int, str]],
}
```

Hard rule:

```text
local hypothesis evaluation must not update used_group_ids or used_asset_page_ids
```

Ownership is committed only after:

1. page ledger / residual ledger has run
2. reservation has excluded cross-page-debt candidates on imbalanced pages
3. local/page consistency validation accepts the hypothesis

This is what prevents a plausible same-page explanation from stealing a group that should remain available for cross-page settlement.

---

## 6. Pairing Mode Is Local, Not Page-Wide

The system must not assume that a whole page, or a whole paper, uses exactly one caption arrangement style.

The following mixtures are valid and must be supported:

1. sidecar + standard caption-below on the same page
2. caption-above + caption-below in the same paper
3. one cross-page figure plus one same-page figure on the same spread

Therefore:

```text
pairing mode is a local caption-group hypothesis,
not a paper-wide or page-wide hard classification
```

This is a critical design constraint.

---

## 7. Two-Level Decision Model

Local pairing must be decided in two layers.

### 7.1 Layer A: Local pairing hypotheses

For each caption and nearby semantic-group neighborhood, the pipeline may form candidate interpretations:

1. `caption_below`
2. `caption_above`
3. `caption_sidecar`

These are hypotheses only.
They are not yet accepted truth.

### 7.2 Layer B: Local/page consistency validation

Those hypotheses must then be validated against neighborhood or page consistency.

Examples of validating signals:

1. monotonic ordering across multiple captions/groups
2. no crossing ownership between adjacent local pairs
3. page-level count alignment after hypothetical local assignments
4. no obvious head/tail shift (first legend unmatched, last group unmatched)
5. repeated local pattern across 2+ figures on the same page

Only after this validation may the system accept `above`, `below`, or `sidecar` for that local region.

---

## 8. Caption Independence Does Not Mean Caption Blindness

The semantic grouping spec already established that caption/text may act as **neutral separators**.
That principle remains in force here.

### Allowed uses of caption/text blocks

Caption/text blocks may be used to answer:

```text
Do these two asset regions remain visually continuous,
or are they physically interrupted by intervening text?
```

### Forbidden uses during semantic grouping

Caption identity may not be used to answer:

```text
Which caption already owns this asset before groups exist?
```

This distinction prevents the old caption-band contamination from reappearing under a different name.

---

## 9. Sidecar Governance

Sidecar is the highest-risk local mode because the wrong trigger will re-partition page assets and can steal ownership.

### 9.1 What sidecar is

Sidecar means:

```text
the local caption-group relationship is primarily horizontal / row-wise,
not vertical
```

### 9.2 What sidecar is not

Sidecar is not:

1. "a page with two narrow captions"
2. "any page where caption width is small"
3. "any multi-column figure page"

### 9.3 Sidecar qualification requirements

A local region may enter sidecar handling only if all are true:

1. the caption is narrow enough to plausibly be sidecar text
2. the caption and candidate group share strong row alignment / y overlap
3. monotonic pairing exists across neighboring local caption/group pairs if more than one is present
4. without local sidecar interpretation, same-page ownership has a high risk of assigning adjacent semantic groups to the wrong captions or forcing an overly coarse page-wide fallback interpretation
5. no stronger ordinary `caption_below` / `caption_above` interpretation explains the local geometry cleanly

### 9.4 Sidecar trigger must be ownership-safe

Even when sidecar mode is accepted, it may only consume:

```text
still-unowned assets or still-unowned semantic group members
```

It may not repartition the entire page asset field after earlier ownership has already been established.

This is a required contract change from the current behavior.

---

## 10. Caption-Above Governance

Caption-above should not be detected by one brittle rule.

The safest mechanism is:

1. allow local `caption_above` hypotheses
2. accept them only after local/page validation confirms that ordinary below-mode interpretation leaves a systematic head/tail mismatch

### Strong signals for caption-above mode

1. caption above group with strong x overlap
2. no local group below the caption in below-mode without contradiction
3. page-level pairing under below-mode produces systematic mismatch, such as:
   - first legend unmatched
   - last figure group unmatched
   - a one-position shift in local assignments
4. repeated caption-above arrangement appears more than once in the page neighborhood

This is a post-pairing validation problem, not merely OCR text classification.

---

## 11. Reservation And Cross-Page Settlement Order

Cross-page settlement remains secondary to semantic grouping and local pairing hypothesis generation.
It is **not** secondary to greedy same-page ownership commit.

Correct order:

```text
semantic grouping
-> local pairing hypotheses
-> page / residual ledger
-> reservation
-> validated same-page commit among non-reserved hypotheses
-> cross-page settlement for reserved / residual objects
-> governed fallback
```

Not:

```text
same-page ownership commit
-> residual
-> cross-page settlement
```

Rules:

1. local pairing modes may be evaluated before cross-page settlement
2. they may not be committed before reservation on imbalanced pages
3. reservation may temporarily withhold otherwise plausible same-page hypotheses from ownership commit
4. cross-page settlement operates only after non-reserved same-page hypotheses have been validated and committed

Authority guardrail:

```text
reservation state has higher authority than same-page commit on imbalanced pages
```

This preserves the earlier Figure 4 / Figure 5 fix direction while fitting it into a broader local-pairing model.

---

## 12. Ownership State Machine

Ownership must be explicit, not inferred ad hoc by each fallback.

### 12.1 Group-level states

```text
unowned
reserved
matched
ambiguous
held
```

### 12.2 Asset-level states

```text
unowned
owned_by_figure
owned_by_table
reserved_by_group
blocked
```

`blocked` must not be a generic catch-all.

It means the asset is intentionally unavailable for figure fallback because it is, for example:

1. non-body media
2. table-owned
3. conflict-held
4. excluded by a stronger structural rule

Every fallback must check both:

1. the candidate group is not already matched or reserved by a stronger layer
2. every `(page, block_id)` it wants to consume is still unowned, or explicitly allowed by the current group owner contract

This is the shared ownership registry model all fallback paths must obey.

Reserved-state failure guardrail:

```text
a reserved object that fails cross-page settlement must transition to ambiguous or held,
or return to unowned only through an explicit audited release step.
it must not silently re-enter greedy same-page or legacy fallback.
```

---

## 13. Fallback Governance Hierarchy

Fallbacks must be treated as a governed family, not as unrelated heuristics.

### 13.1 Order of authority

From strongest to weakest:

1. semantic grouping truth
2. reservation state on imbalanced pages
3. validated same-page local pairing commit among non-reserved objects
4. reserved cross-page settlement
5. governed late fallback
6. audit-only / promotion-only heuristics

### 13.2 Family members

Current late-stage family:

1. sidecar fallback
2. preproof `legend_bundle` fallback
3. group-aware sequential fallback
4. old sequential fallback
5. `sequence_match` promotion

### 13.3 Shared contract

Every late fallback path must obey:

1. consume only still-unowned assets/groups
2. never override already-owned semantic groups
3. emit a full matched-figure contract if it produces a match
4. otherwise remain in ambiguous/held state

Fallback governance should therefore prefer **hard ownership guards** before any new scoring layer is introduced.

### 13.4 Fallback permission table

| Fallback | May consume | Must not do |
|----------|-------------|-------------|
| `sidecar` | local still-unowned semantic groups / group members | repartition the whole page after ownership exists; steal matched groups |
| `legend_bundle` | caption-only page followed by continuous unowned asset/group pages | jump across strong body/table/reference interruptions |
| `group_sequential` | unowned semantic groups, including `single_asset` groups | split multi-asset groups or override stronger local ownership |
| `old sequential` | bare assets not belonging to any semantic group, or an explicitly allowed single-asset compatibility path | consume a multi-asset semantic group member |
| `sequence_match` | only promote an already-formed pairing whose asset/page identity is already known | invent asset ownership from caption order alone; emit half-formed matched figures |

---

## 14. `sequence_match` Must Be A Real Contract Or Not A Match

`sequence_match` is not allowed to produce half-formed matched figures.

If promoted entries enter `matched_figures`, they must carry the same core contract as other matches:

```python
{
    "page": int,
    "legend_page": int,
    "asset_pages": list[int],
    "matched_assets": list[dict],
    "asset_block_ids": list[str],
    "settlement_type": str,
}
```

If that cannot be supplied, the figure must remain `ambiguous` or `held` instead of being promoted to a fake match.

Additional prohibition:

```text
sequence_match may not invent asset ownership from caption order alone.
It may only promote an already-formed legend-group pairing whose assets and pages are already known.
```

---

## 15. Table / Figure Ownership Boundary

The whole-pipeline model must also account for image-like tables and table-like figures.

Hard rule:

```text
one asset block -> at most one semantic owner family
```

Meaning:

1. a block cannot simultaneously become a matched figure asset and a matched table asset
2. dedup / ownership guards at `(page, block_id)` level are required across figure and table paths

Recommended shared surfaces:

```text
global_owned_asset_ids
figure_owned_asset_ids
table_owned_asset_ids
```

Conflict rule:

```text
if asset claimed by both figure and table,
do not silently duplicate;
emit ownership_conflict with candidate identifiers
```

This is especially important on multi-column mixed-layout pages.

---

## 16. Canonical Layout Families And Their Meaning

The following papers define the stress cases the unified model must explain.

### 16.1 `3FDT9652`

Meaning:

1. three-column or quasi-three-column pages
2. multiple neighboring figures that must remain separate
3. table/figure mixed pages

Risk if model is wrong:

```text
semantic grouping over-merges adjacent figures,
or table/figure ownership collides
```

Test target:

```text
synthetic minimal fixture first,
real-paper observational regression second
```

### 16.2 `6FGDBFQN`

Meaning:

1. true sidecar-heavy local pairing
2. caption beside figure, not below
3. dense page with multiple local figure/caption regions

Risk if model is wrong:

```text
sidecar fallback steals entire page assets,
or sidecar trigger is too weak and misfires on non-sidecar pages
```

Test target:

```text
synthetic local row-pairing fixture first,
real-paper observational regression second
```

### 16.3 `8VB9ZVQG`

Meaning:

1. large composite figure with loose panel spacing
2. cross-page caption on next page

Risk if model is wrong:

```text
semantic grouping over-splits one real figure,
or next-page caption pairing becomes fragile
```

Test target:

```text
synthetic large-composite + next-page-caption fixture first,
real-paper observational regression second
```

### 16.4 `24YKLTHQ`

Meaning:

1. caption-above convention
2. noisy `Source: own` attribution lines
3. figure/table role instability

Risk if model is wrong:

```text
caption-below bias breaks ownership,
or attribution/source lines pollute legend truth
```

Test target:

```text
synthetic caption-above + attribution fixture first,
real-paper observational regression second
```

---

## 17. Acceptance Criteria

This holistic model is acceptable only if all are true:

1. semantic groups remain caption-independent
2. sidecar, above, and below are treated as local pairing modes, not as page-wide hard classes
3. a page may contain mixed local pairing modes without forcing one global interpretation
4. local pairing may be evaluated early, but same-page ownership is not committed before reservation on imbalanced pages
5. late fallbacks consume only still-unowned objects
6. `sequence_match` either emits a full matched-figure contract or does not promote
7. figure/table ownership is one-owner-only at `(page, block_id)` level
8. `3FDT9652` does not over-merge adjacent figures
9. `6FGDBFQN` true sidecar layouts can be locally interpreted without page-wide theft
10. `8VB9ZVQG` loose composite figures are not over-split
11. `24YKLTHQ` caption-above layouts can be recovered through local/page validation rather than below-only bias

---

## 18. Implementation Consequence

No more single-issue fixes should be introduced without first locating them in this model:

1. Is it a semantic grouping issue?
2. Is it a local pairing hypothesis issue?
3. Is it a reservation / cross-page settlement issue?
4. Is it a late fallback governance issue?
5. Is it an output contract issue?

If a change cannot be placed into one of those layers, it is probably another isolated patch and should be reconsidered.

---

## 19. Summary

The system should be thought of as:

```text
group first from vision,
generate local pairing hypotheses,
reserve before greedy same-page ownership on imbalanced pages,
commit validated same-page ownership,
then fallback only under ownership-safe governance
```

That is the whole-pipeline discipline this spec establishes.
