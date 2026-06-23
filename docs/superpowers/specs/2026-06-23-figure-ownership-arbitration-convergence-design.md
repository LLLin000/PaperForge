# Figure Ownership Arbitration Convergence Design

> **Date:** 2026-06-23
> **Status:** Proposed
> **Scope:** Define the convergence architecture for OCR-v2 figure ownership so new hard papers are handled by unified caption-evidence, candidate-generation, arbitration, and render/accounting layers rather than by adding new direct settlement paths.

---

## 1. Why This Spec Exists

OCR-v2 has reached the point where adding one more paper-specific fix is more dangerous than helpful.

The system has already accumulated multiple ownership-producing paths:

1. ordinary same-page matching
2. composite parent matching
3. sidecar rescue
4. cross-page backward / forward settlement
5. legend-bundle fallback
6. group-sequential fallback
7. old sequential fallback
8. sequence-match promotion

That accumulation is tolerable only if the system keeps converging toward a single decision model.
Without that convergence, every new hard paper turns into:

```text
new rule
+ new veto
+ new fallback
+ new protection exception
+ new overwrite order question
```

That is how an OCR ownership system becomes impossible to reason about.

This spec exists to stop that growth pattern.

Its purpose is not to solve one paper.
Its purpose is to define how all future figure-ownership fixes must fit into one architecture.

---

## 2. Current Problem Statement

The current hard papers expose different surface failures:

- `2UIPV93M`: same-page over-merge, sidecar overwrite risk, multi-caption scoped arbitration
- `VFS8CBW2`: dense composite under-grouping, panel-title false-caption promotion, weak sequence shells
- `6FGDBFQN`: mixed caption grammar on the same paper
- `RKSLQRIM`: mixed subfigure-label conventions and figure/table co-page interference
- `24YKLTHQ`: partial composite ownership and orphaned visual mass

But these are not independent categories of architecture.
They reduce to four layers of responsibility:

1. **Caption recognition**
2. **Visual ownership candidate generation**
3. **Ownership arbitration / precedence**
4. **Render and accounting semantics**

The key mistake to avoid from now on is solving a layer-3 or layer-4 problem by adding a new direct matching path inside layer 2.

---

## 3. Design Goal

The system must converge toward this mainline:

```text
caption evidence
-> visual candidate generation
-> page-level ownership arbitration
-> accepted / provisional / unresolved / rejected
-> render / accounting
```

Everything new must plug into one of those stages.

### 3.1 Non-goal

This spec does **not** aim to perfectly reconstruct page layout.

The target is:

```text
human-readable academic fulltext
+ traceable figure/table ownership
+ low duplication
+ low body pollution
```

This means the system may leave explainable unresolved visual mass.
It must not hide that mass behind fake strong matches.

---

## 4. Hard Architectural Rules

These rules are mandatory.

### 4.1 No new independent settlement path

From this point forward:

```text
Do not add a new direct settlement path.
```

Allowed additions:

1. new candidate source
2. new evidence feature
3. new arbitration rule
4. new render/accounting rule

Forbidden additions:

1. `VFS8CBW2`-specific fallback
2. page-specific special logic
3. `dense_parent_settlement`
4. sidecar-only dense rescue branch
5. any new path that directly appends to `matched_figures` without going through the shared arbitration contract

### 4.2 Candidate sources may grow; decision states may not

The set of candidate sources may expand.
The set of final ownership states must remain small and stable.

Final figure-ownership decision states are:

```text
accepted
provisional
unresolved
rejected
```

`settlement_type` may continue to exist as provenance.
It must no longer be treated as equivalent to truth strength.

### 4.2.1 OwnershipDecision is internal before bucket migration

In the first convergence pass, `OwnershipDecision` is an internal arbitration result.
It does **not** replace the persisted inventory buckets immediately.

Required mapping:

```text
accepted -> matched_figures
provisional -> ambiguous_figures (or a future provisional audit surface), but not strong solved ownership
unresolved -> unresolved_clusters / unmatched_assets / unmatched_legends depending on object type
rejected -> rejected_legends / rejected_candidates
```

Phase-1 rule:

```text
The system may add `ownership_decision` or equivalent metadata onto existing entries,
but it must not remove the current persisted buckets until reader/render/health/object consumers are migrated.
```

### 4.3 Partial local ownership is not automatically protected

Any same-page result that only explains a small subset of the local visual mass on a dense page is not automatically strong ownership.

It must remain at most:

```text
provisional
```

until arbitration confirms it is the best ownership explanation.

### 4.3.1 Provisional ownership uses soft reservation semantics

`provisional` must have explicit reservation behavior.
Otherwise it either blocks stronger repair paths too early or remains too weak to prevent duplicate fallback consumption.

Required semantics:

```text
provisional candidates may place soft reservations during arbitration
soft reservations block legacy fallback from consuming the same assets during the arbitration window
soft reservations may be superseded by a stronger candidate before finalization
only accepted decisions finalize ownership into matched_figures truth
rejected or unresolved outcomes must release or downgrade the reservation according to the audit policy
```

### 4.4 Assetless sequence shells are not solved matches

If a `sequence_match` has no real asset payload, it is not a real ownership win.

It may be visible as a shell outcome for traceability.
It must not count as a strong solved match in audit or health reporting.

Required output rule:

```text
assetless sequence shells must not be emitted into matched_figures
```

They may instead appear as:

1. `ambiguous_figures` with `hold_reason = "assetless_sequence_shell"`
2. a separate `sequence_shells` audit bucket

They must not increment:

1. `official_figure_count`
2. solved ownership metrics in health / audit summaries

---

## 5. Unified Object Model

The ownership system should be understood through five conceptual objects.

### 5.1 `Block`

Raw or normalized OCR block.

### 5.2 `CaptionEvidence`

Represents the status of a text block with respect to figure/table ownership.

Examples:

- formal numbered figure caption
- formal numbered table caption
- panel title candidate
- embedded figure text
- weak caption candidate

### 5.3 `VisualGroup`

An atomic or higher-order visual grouping candidate.

Examples:

- atomic single asset
- same-row pair
- distance cluster
- composite parent candidate
- dense composite parent candidate

### 5.4 `FigureCandidate`

A proposed explanation that a given legend owns a specific visual grouping.

This is where same-page, composite-parent, sidecar-rescue, and sequence-shell provenance belong.

Minimum contract shape in the convergence direction:

```python
{
    "candidate_id": str,
    "candidate_source": str,
    "legend_block_id": str | None,
    "visual_group_id": str | None,
    "asset_block_ids": list[str],
    "embedded_text_block_ids": list[str],
    "page": int,
    "legend_page": int | None,
    "asset_pages": list[int],
    "bbox": list[float],
    "evidence": list[str],
    "conflicts": list[str],
    "coverage_score": float,
    "caption_score": float,
    "visual_score": float,
    "arbitration_score": float | None,
}
```

The exact field names may vary.
The shape must remain unified across candidate sources.

### 5.5 `OwnershipDecision`

The final arbitrated state:

- `accepted`
- `provisional`
- `unresolved`
- `rejected`

---

## 6. Layer 1 - Caption Evidence

This layer answers:

```text
Is this block a real formal caption,
or only a panel title / embedded figure text / weak candidate?
```

### 6.1 Required outcome classes

At minimum, figure-side evidence must distinguish:

1. `formal_numbered_figure_caption`
2. `weak_figure_caption_candidate`
3. `panel_title_candidate`
4. `embedded_figure_text`

### 6.2 Dense-page panel-title suppression rule

This spec introduces a formal suppression rule for pages like `VFS8CBW2`.

When the same page already contains a valid numbered figure caption, a short unnumbered figure-caption-like block must not be allowed to compete as a formal caption if it is visually inside a figure envelope and behaves more like a local panel title or assay label.

The rule must be structural, not lexical.

Allowed signals include:

1. no figure number
2. short text span
3. inside a likely visual parent envelope
4. page already has a strong numbered figure caption
5. title-like geometry rather than legend-like geometry

Forbidden implementation:

```text
literal blacklist of strings such as RND / COL II / Basal respiration rate
```

### 6.3 Required handling of suppressed panel titles

Suppressed panel-title candidates are **not** deleted.

They must:

1. stop participating in formal figure matching
2. remain available as in-figure text for downstream figure artifact rendering
3. not be promoted into body paragraphs

---

## 7. Layer 2 - Visual Candidate Generation

This layer answers:

```text
What visual ownership candidates exist for a caption?
```

### 7.1 Candidate source inventory

Current and future candidate sources may include:

1. atomic single asset
2. same-row pair
3. ordinary local same-page group
4. composite parent candidate
5. dense composite parent candidate
6. sidecar rescue candidate
7. sequence shell candidate

### 7.2 Dense composite parent candidates are a candidate source, not a matcher

This is the most important rule in the spec.

For `VFS8CBW2`-class pages, the next system capability is:

```text
dense_composite_parent_candidate
```

This must be generated as part of candidate generation.
It must **not** be implemented as a new direct settlement path.

### 7.2.1 Dense parent is a composite-parent subtype

`dense_composite_parent_candidate` is not a new ownership family parallel to `composite_parent`.

It is a subtype or evidence profile of composite parent candidacy.

Required interpretation:

```text
dense_composite_parent_candidate is a subtype of composite_parent_candidate,
not a separate ownership path and not a new settlement mechanism
```

One acceptable representation is:

```python
{
    "group_type": "composite_parent",
    "parent_subtype": "dense_composite",
    ...
}
```

### 7.3 Dense parent construction constraints

Dense parent candidates must be:

1. **visual-only** at construction time
2. built after atomic groups already exist
3. separate from ordinary `candidate_groups`
4. same-page only in the first iteration

Construction must not rely on caption text identity.
Caption alignment is allowed later in arbitration.

### 7.4 Dense parent trigger envelope

The system should only build dense parent candidates in pages that look like real dense-composite pages.

Construction-time trigger signals:

1. page contains a formal numbered figure caption
2. same local visual zone contains many fragments
3. visual fragment count is high, e.g. `>= 4`
4. the candidate does not cross another numbered caption interval boundary
5. local fragments show compact visual structure rather than page-wide scatter

This is not page-wide mega-merge.
This is scoped visual-parent candidacy.

Arbitration-time scoring signals may additionally use:

1. coverage gain over ordinary local ownership
2. unresolved visual mass reduction
3. penalty for partial local ownership that explains only a small subset of the zone
4. sibling-caption conflict penalties

Rule:

```text
Layer 2 construction may not depend on values that only exist after Layer 3/4 finalization.
```

### 7.5 Dense parent candidate contract

Minimum suggested fields:

```python
{
    "parent_id": str,
    "page": int,
    "child_group_ids": list[str],
    "asset_block_ids": list[str],
    "embedded_text_block_ids": list[str],
    "bbox": list[float],
    "fragment_count": int,
    "visual_mass": float,
    "coverage_gain": float,
    "compactness": float,
    "grid_score": float,
    "crosses_caption_boundary": bool,
    "conflicts_with_sibling_legend": bool,
    "confidence": float,
}
```

The exact field names may vary.
The semantics may not.

---

## 8. Layer 3 - Ownership Arbitration

This layer answers:

```text
Among the available candidates, which ownership explanation wins?
```

### 8.1 Arbitration replaces path-order truth

The system must stop relying on path order as the ultimate source of truth.

Today too much meaning still comes from:

```text
which matcher ran first
which fallback ran later
which path protected or reclaimed ownership
```

That is what must converge.

### 8.2 Ordinary same-page ownership may be provisional on dense pages

If an ordinary same-page candidate matches only a local subset of a dense visual page, and substantial unresolved visual mass remains in the same visual zone, that result cannot automatically become protected accepted ownership.

Instead:

```text
ordinary same-page result -> provisional
```

until dense-parent arbitration has had a chance to compete.

### 8.3 Dense parent outranks partial local ownership when safe

A dense parent candidate should outrank a partial same-page local claim only if:

1. coverage gain is significant
2. compactness / grid structure is strong enough
3. it does not cross another numbered caption boundary
4. it does not conflict with a sibling numbered legend
5. it remains within the current legend’s legal visual zone

### 8.4 Sidecar is rescue-only

Sidecar must remain a rescue interpretation, not a global page rewrite mechanism.

It may only operate on legend-local unresolved / ambiguous / no-asset situations.

It must not:

1. silently overwrite already accepted strong ownership
2. rewrite a whole page because two narrow captions exist
3. become the recovery path for dense composite fragmentation

### 8.5 Required precedence direction

This spec does not hardcode a final numeric score ladder.
But it does require this qualitative precedence:

```text
strong scoped parent
> strong ordinary local ownership
> sidecar rescue
> sequence shell
```

And also:

```text
partial ordinary local ownership on dense page
< strong dense parent candidate
```

### 8.6 Relationship to existing roadmap

This convergence spec does **not** replace the already-approved visual-grammar hardening roadmap.

It acts as an architecture constraint layer for that roadmap.

Required relationship:

```text
P0 close-out fixes still land first
P1A diagnostic-only parent detection still lands before ownership-bearing parent arbitration
P1B / P2 / P3 and later dense-page work must follow the convergence rules in this spec
```

---

## 9. Layer 4 - Render and Accounting

This layer answers:

```text
How should the final artifact treat the chosen ownership result?
```

### 9.1 Sequence shell accounting rule

Assetless or weak sequence recovery must no longer appear equivalent to a solved figure.

Required distinction:

1. `sequence_match` with real asset payload -> weak but real ownership result
2. `sequence_match` without real asset payload -> shell outcome only

Shell outcomes must not be counted as strong matched ownership in health and audit summaries.

Suggested shell label:

```text
assetless_sequence_shell
```

### 9.2 Unresolved clusters must remain explainable

The system is allowed to preserve unresolved visual mass.
It is not allowed to hide that mass by overstating solved ownership.

This is a hard honesty requirement for the audit layer.

---

## 10. Anti-Goals

The following are explicitly out of scope or forbidden:

1. hardcoding `VFS8CBW2` page numbers
2. hardcoding specific short labels like `RND` or `COL II`
3. page-wide mega-merge when many visual blocks exist
4. suppressing all `figure_caption_candidate` blocks on dense pages
5. solving dense composite pages by pushing more logic into sidecar
6. treating all `sequence_match` outcomes as strong matches
7. widening atomic semantic grouping thresholds just to make dense pages pass

---

## 11. Required Diagnostics Before Major Logic Changes

Before the next implementation pass, the system should emit a diagnostic view for the representative dense pages.

The diagnostic surface should show, side-by-side:

1. formal numbered captions
2. all figure-caption candidates
3. suppressed panel-title candidates
4. atomic visual groups
5. composite / dense parent candidates
6. accepted ownership
7. provisional ownership
8. unresolved clusters
9. sequence-shell outcomes

This diagnostic is intended to prevent threshold tuning in the dark.

---

## 12. Validation Papers

Validation should use papers as capability-family representatives, not as excuses to create one-paper mechanisms.

Recommended mapping:

1. `2UIPV93M`
   - scoped multi-caption arbitration
   - false protected same-page prevention

2. `VFS8CBW2`
   - dense composite consolidation
   - panel-title suppression
   - sequence-shell accounting honesty

3. `6FGDBFQN`
   - mixed caption grammar

4. `RKSLQRIM`
   - guardrail-only paper
   - used to ensure no mega-merge / no figure-table theft / no body pollution

5. `24YKLTHQ`
   - partial composite ownership / orphan reduction

Each paper should map to a capability family.
If a new paper falls into an existing family, the system must adjust that family’s mechanism rather than inventing a new isolated path.

---

## 13. Stop Criteria

The stopping goal is not perfect PDF reconstruction.

The stopping goal is:

```text
human-readable academic fulltext with traceable figure/table ownership
```

The system is good enough when all of the following are true:

1. major section order is correct
2. formal figure/table captions are not silently lost
3. figures/tables do not massively pollute body text
4. the same asset is not silently owned by multiple figures/tables
5. strong matched figures carry real asset payload
6. dense composite figures can be attached as one coherent ownership result
7. unresolved clusters may remain, but they are explainable and not hidden behind fake matches
8. the final markdown is usable for human reading and downstream agent retrieval

This means the project can stop before it perfectly names every panel A/B/C/D.

The threshold is:

```text
the figure is correctly attached as a figure
```

not:

```text
every subpanel is perfectly reconstructed as a first-class structured object
```

---

## 14. Immediate Next Spec/Plan Implication

The next implementation plan should not be “fix `VFS8CBW2`.”

It should be:

```text
freeze the ownership decision model,
add dense composite candidate generation,
add panel-title suppression,
and demote weak sequence shells in accounting.
```

That is the convergent path.

That is how complexity stops growing.
