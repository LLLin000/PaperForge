# OCR Visual Grammar Hardening Design

> **Date:** 2026-06-23
> **Status:** Proposed
> **Scope:** Define the next hardening pass for OCR-v2 figure/table extraction after governance, grouping, reservation, and conflict-surfacing foundations have landed. This spec converts the current residual figure failures from paper-specific debugging into three explicit visual-grammar capability layers, preceded by two small close-out fixes.

---

## 1. Why This Spec Exists

The current OCR-v2 figure pipeline is no longer failing because the broad architecture is directionally wrong.
It already has:

1. caption-independent atomic semantic grouping
2. page ledger / residual ledger / reservation-aware same-page commit
3. explicit local pairing hypotheses
4. late fallback governance and sequence-match contract tightening
5. post-hoc figure/table ownership conflict surfacing

But the audit sweep and visual inspection show that the remaining residuals are still concentrated in a small number of upstream visual-grammar gaps.

The key shift is:

```text
The main risk is no longer ownership order alone.
The main risk is whether the visual object itself is organized correctly before ownership is decided.
```

This spec exists to formalize that next step.

---

## 2. Current State

### 2.1 What is already healthy enough to preserve

The following foundations already exist in `paperforge/worker/ocr_figures.py` and should be treated as stable unless a change is explicitly justified:

1. atomic caption-independent semantic grouping
2. local pairing hypothesis generation (`caption_below`, `caption_above`, `caption_sidecar`)
3. reservation-aware same-page commit gating
4. grouped-asset fallback restrictions
5. `sequence_match` contract tightening
6. post-hoc figure/table ownership conflict surfacing

The active queue also confirms the branch has already moved beyond architecture readiness and into rebuild/output hardening:

- `project/current/ocr-v2-active-queue.md:9`
- `project/current/ocr-v2-active-queue.md:15`

### 2.2 What the audit/vision sweep shows

The `audit/` corpus and the visual inspections do **not** suggest 30 unrelated failures.
They suggest a small set of repeating visual-grammar families.

Representative evidence:

1. `6FGDBFQN`
   - same paper mixes bottom-caption, left-side caption, right-side caption, and above/right caption layouts
   - vision conclusion: not random noise, but internally mixed caption grammar
   - repo evidence: `OCR-V2-READINESS-SUMMARY.md:21`, `audit/6FGDBFQN/audit_report.md:21`

2. `3FDT9652`
   - standard two-column journal pages mixed with full-width composite multi-panel figures
   - one page may contain ordinary caption-below single figures plus a full-width A/B/C composite
   - repo evidence: `audit/3FDT9652/audit_report.md:30`

3. `VFS8CBW2`
   - dense scientific composite figures with mixed chart types and repeated unresolved clusters
   - vision conclusion: one coherent family of high-density multi-panel composite pages, not scattered edge cases
   - repo evidence: `audit/VFS8CBW2/audit_report.md:30`

4. `RKSLQRIM`
   - same paper uses multiple subfigure label conventions and also has figure/table co-page layouts
   - repo evidence: `project/current/phase2-root-cause-analysis.md:97`

5. `2UIPV93M`
   - visually ordinary Chinese medical thesis layout, but current figure ownership is still weak
   - this is the strongest warning that the residual is not limited to exotic layouts
   - repo evidence: `audit/2UIPV93M/audit_report.md:10`

6. `24YKLTHQ`
   - repeated partial ownership of composite figures, suggesting under-grouping of parent figures rather than random per-caption noise
   - repo evidence: `audit/24YKLTHQ/audit_report.md:31`

### 2.3 Core conclusion from the sweep

The residuals are best described as:

```text
1. composite parent grouping is under-modeled
2. page-local mixed caption grammar is under-validated
3. figure/table co-page separation is still too late in the pipeline
```

Those three are the main capability gaps.

---

## 3. Two Close-Out Fixes Before New Capability Work

Before the larger visual-grammar passes, two small close-out fixes must land first.

### P0-A. Persist `ownership_conflicts` before writing figure inventory

Problem:

```text
The pipeline can attach ownership conflicts in memory,
but if `figure_inventory` is written before `table_inventory` exists,
the persisted `figure_inventory.json` may not contain the conflict surface.
```

Requirement:

1. build `table_inventory`
2. call `attach_ownership_conflicts(figure_inventory, table_inventory)`
3. then write `figure_inventory.json`

Why first:

This is a trust fix.
Subsequent figure/table separator work is harder to audit if the persisted artifact is stale.

### P0-B. Bundle-source / caption-list duplicate legend canonicalization

Problem:

Some papers contain a `Table and Figure Captions` region or caption-list pages, then later repeat the real legend near the true figure page.
If dedup happens too early with coarse `(namespace, figure_number)` preference, the wrong legend instance becomes canonical and contaminates downstream ownership.

Requirement:

1. bundle-source legends must be identified before canonical legend selection
2. real same-page or adjacent-page legends must outrank bundle-source duplicates
3. dedup losers must be explicitly recorded, not silently dropped

Completeness accounting rule:

```text
bundle-source duplicate losers are accounted outcomes, not gaps
```

Required recorded fields:

```text
status = deduped_duplicate
dedup_reason = bundle_source_duplicate_loser
kept_block_id = ...
kept_page = ...
```

Why first:

This is an integrity fix for legend identity.
It reduces noise in later grouping and cross-page interpretation.

---

## 4. Priority Model

This hardening pass is intentionally sequenced as:

```text
P0: close-out fixes
P1A: composite parent detector (diagnostic-only)
P1B: composite parent ownership arbitration
P2: mixed caption grammar validator
P3A: asset family hint
P3B/P3C: co-page figure/table separator veto
```

This priority is deliberate.

### Why P1 comes before P2/P3

The audit suggests the largest broad residual is still:

```text
the system does not always know what the parent figure object is
```

If the object itself is fragmented, later grammar validation or table separation cannot fully repair the result.

### Why P1 must be implemented carefully

P1 has the highest ROI and the highest regression risk.
It must not simply widen the current atomic semantic grouping thresholds.

The existing caption-independent grouping layer is already serving an important invariant:

```text
atomic semantic groups are local visual truth,
independent of caption identity
```

That invariant must be preserved.

---

## 5. P1 - Composite Parent Grouping

P1 must be split into two passes.

### 5.0 P1A vs P1B

```text
P1A:
  build composite parent candidates
  emit diagnostics/tests/audit visibility
  do not change ownership behavior yet

P1B:
  allow strong parent candidates to participate in ownership
  add explicit parent-over-child arbitration
```

This split is required because P1 has the highest expected payoff and the highest regression risk.
The detector and the ownership consequences must not land in one blind step.

### 5.1 Problem

Current semantic grouping is intentionally conservative.
That prevents ordinary same-page neighboring figures from collapsing into one mega-group.
But it also means many true composite figures are fragmented into multiple atomic semantic groups.

This manifests as:

1. unresolved clusters
2. unmatched figure assets
3. partial composite ownership where only 1-2 panels are attached

### 5.2 Hard rule

Do **not** solve this by making atomic semantic grouping looser.

Forbidden approach:

```text
Increase atomic grouping gap thresholds until composite parents merge directly.
```

That would regress ordinary multi-figure pages.

Second hard rule:

```text
initial P1 is same-page only
```

Cross-page parent grouping is explicitly out of scope for this pass.
Existing reservation and cross-page settlement already model caption/group cross-page relations.
P1 should not introduce a second cross-page grouping mechanism.

### 5.3 Required architectural split

P1 must introduce a second visual layer:

```text
atomic semantic groups
-> composite parent candidates
```

The atomic layer remains the current caption-independent local truth.
The new parent layer is a higher-order visual interpretation built on top of atomic groups.

Suggested shape:

```python
atomic_groups = _build_semantic_figure_groups_from_assets(...)
parent_groups = _build_composite_parent_figure_groups(
    atomic_groups,
    assets,
    legends,
    structured_blocks,
    page_width,
)
```

### 5.4 Construction / scoring separation

This separation must remain explicit:

```text
parent candidate construction = visual-only
parent candidate eligibility / scoring = may use caption evidence
```

In particular:

```text
caption alignment may help decide whether a parent candidate can be matched,
but it must not be used to create the parent topology itself
```

### 5.5 Parent-group evidence requirements

A composite parent candidate should require multiple converging signals, not one loose heuristic.

Allowed evidence classes:

1. page-local visual family has `>= 3` atomic groups or `>= 4` panel assets
2. panel bboxes form a stable grid / row / column / regular masonry pattern
3. panel sizes are similar or come from a small number of size classes
4. gaps between child groups are small and not interrupted by strong body/table/reference structure
5. nearby caption alignment suggests one parent object, not several competing captions
6. optional panel-label evidence (`A`, `B`, `C`, `(a)`, `(b)`) may add confidence, but must not be the only reason

Competing-caption veto:

```text
If multiple strong numbered captions geometrically partition the candidate region,
the parent candidate must be rejected or marked weak.
```

Representative veto situation:

```text
>= 2 strong figure legends on the same page
each has plausible local pairing to different child groups
caption order and child-group order are monotonic
=> do not promote one composite parent across them
```

### 5.6 Output contract

Parent groups should carry explicit parent metadata, not masquerade as ordinary atomic groups.

Suggested fields:

```python
{
    "group_id": str,
    "group_type": "composite_parent",
    "child_group_ids": list[str],
    "asset_block_ids": list[str],
    "cluster_bbox": list[float],
    "parent_evidence": list[str],
    "parent_confidence": float,
}
```

### 5.6 Invariants

1. if a parent group is accepted and matched, its child groups may not be consumed later by fallback paths
2. if parent evidence is weak, child groups must remain available and behavior should fall back to the existing atomic path
3. parent grouping must remain caption-independent at construction time

Parent-over-child arbitration rule:

```text
parent and child groups must not be treated as ordinary peer candidates that can both commit ownership
```

Required behavior:

```text
if a parent candidate is accepted:
  all child_group_ids and child asset ids become consumed/reserved by the parent

if a parent candidate is weak or rejected:
  it is ignored for ownership purposes
  child groups remain available to the existing atomic path
```

P1A confidence bands:

```text
parent_confidence >= 0.75:
    matchable parent candidate in P1B

0.50 <= parent_confidence < 0.75:
    diagnostic-only / audit-visible
    must not enter ownership matching yet

< 0.50:
    ignore
```

Weak parent candidates must never consume child groups.

### 5.7 Expected beneficiaries

Highest direct benefit:

1. `VFS8CBW2`
2. `24YKLTHQ`
3. `2UIPV93M`
4. `RKSLQRIM`

Expected broader effect:

```text
lower unmatched_fig_assets
lower unresolved_clusters
better composite-figure panel coverage on ordinary papers, not just exotic ones
```

---

## 6. P2 - Mixed Caption Grammar Validator

### 6.1 Problem

The pipeline already knows about local pairing modes.
But it still lacks one explicit validator that checks whether a page-local set of hypotheses is internally coherent.

The residual issue is not just “sidecar exists”.
It is:

```text
one page or one paper may contain multiple local caption grammars,
and the system still lacks one consistent validator for those mixtures
```

### 6.2 Hard rule

P2 must be a **validator layer**, not a replacement matcher.

Forbidden approach:

```text
Create a parallel second matcher for sidecar/above/below ownership.
```

Required approach:

```text
take existing local_pairing_hypotheses
-> validate page-local consistency
-> accept / defer / reject / conflict-tag
```

### 6.3 Output contract

The validator must annotate hypotheses with explicit grammar status fields.

Suggested shape:

```python
{
    "hypothesis_id": str,
    "legend_block_id": str,
    "group_id": str,
    "mode": "caption_below" | "caption_above" | "caption_sidecar",
    "grammar_status": "accepted" | "deferred" | "rejected" | "conflict",
    "grammar_reason": str,
    "grammar_evidence": list[str],
}
```

### 6.4 Suggested interface

```python
_validate_page_local_caption_grammar(
    local_pairing_hypotheses,
    candidate_groups,
    legends,
    ownership,
    page_width,
)
```

### 6.5 First-pass execution boundary

P2 initial pass must be annotation-first and gate-light.

```text
P2 Stage 1 annotates hypotheses and protects obvious stronger ordinary pairs.
It must not globally replace same-page matching order.
```

This keeps P2 as a validator layer rather than a second matcher.

### 6.6 Required checks

The validator should be able to check at least:

1. monotonic ordering within a local caption column
2. whether a sidecar hypothesis truly has row-coupled evidence
3. whether an ordinary `caption_below` or `caption_above` pair has a stronger local score and should be protected
4. whether local hypotheses on the same page imply incompatible grammar without enough separation
5. whether a page-local region is mixed but still self-consistent, versus mixed and contradictory

### 6.7 Expected beneficiaries

Highest direct benefit:

1. `6FGDBFQN`
2. `3FDT9652`
3. `RKSLQRIM`

Expected broader effect:

```text
fewer visually absurd caption/asset bindings
less sidecar overreach
more stable behavior on pages with mixed local grammar
```

---

## 7. P3 - Co-Page Figure/Table Early Separator

### 7.1 Problem

The system can now surface figure/table ownership conflicts after matching.
But post-hoc surfacing is not enough for pages where a strong table-like region and a strong figure-like region share the same page.

The remaining gap is early separation.

### 7.2 Hard rule

P3 should begin as a **strong separator / veto layer**, not as a full figure/table pipeline rewrite.

Required posture:

```text
strong figure-like evidence -> table matcher should back off or down-rank
strong table-like evidence -> figure matcher should back off or down-rank
ambiguous region -> do not hard-assign too early
```

### 7.3 Staged rollout

P3 should be delivered in three small passes:

```text
P3A:
  compute and expose asset_family_hint only

P3B:
  figure matcher applies strong table_like veto / down-rank

P3C:
  table matcher applies strong figure_like veto / down-rank
```

Do not land all three as one opaque change.

### 7.4 Suggested artifact

```python
asset["asset_family_hint"] = "figure_like" | "table_like" | "ambiguous"
asset["asset_family_confidence"] = float
asset["asset_family_evidence"] = list[str]
```

### 7.5 Strong `table_like` evidence

Examples:

1. `raw_label == "table"`
2. HTML table source
3. dense aligned text-cell grid
4. nearby table caption
5. row/column numeric cell structure

### 7.6 Strong `figure_like` evidence

Examples:

1. panel grid
2. image/chart raw labels
3. subfigure labels
4. nearby figure caption
5. mixed scientific visual panel composition

### 7.7 Expected beneficiaries

Highest direct benefit:

1. `RKSLQRIM`
2. `24YKLTHQ`
3. `2UIPV93M`

Expected broader effect:

```text
fewer user-visible figure/table swap mistakes
cleaner ownership separation on mixed pages
lower need for post-hoc conflict-only reporting
```

---

## 8. What This Spec Explicitly Does Not Do

1. It does not widen the atomic semantic grouping thresholds globally.
2. It does not re-open the already-landed reservation / cross-page governance model.
3. It does not treat every residual as a paper-specific one-off patch.
4. It does not turn sidecar into a page-wide mode classifier.
5. It does not immediately rewrite the whole figure/table pipeline into one unified matcher.

---

## 9. Validation Strategy

### 9.1 P0 validation papers

1. `DWQQK2YB`
2. `2HEUD5P9`
3. `SAN9AYVR`

### 9.2 P1 validation papers

1. `2UIPV93M`
2. `VFS8CBW2`
3. `24YKLTHQ`
4. `RKSLQRIM`

P1A should first prove:

```text
parent candidates are diagnosable and stable without changing ownership
```

P1B should only begin after P1A diagnostics show the candidate set is not manufacturing mega-groups.

### 9.3 P2 validation papers

1. `6FGDBFQN`
2. `3FDT9652`
3. `RKSLQRIM`

### 9.4 P3 validation papers

1. `RKSLQRIM`
2. `24YKLTHQ`
3. `2UIPV93M`

### 9.5 Metrics to watch

Do not evaluate only by `matched_count`.

Track at least:

1. `unmatched_fig_assets`
2. `unresolved_clusters`
3. panel coverage quality for matched composite figures
4. duplicate-legend gap accounting
5. `ownership_conflicts`
6. figure cards / rendered object loss or duplication

For P1 specifically, the key question is:

```text
Does a matched figure cover the full visual parent family,
not merely whether some matched_figure entry exists?
```

---

## 10. Recommended Execution Shape

This work should not be implemented as one giant pass.

Recommended cadence:

```text
P0 -> verify
P1A -> verify
P1B -> verify
P2 -> verify
P3A -> verify
P3B/P3C -> verify
```

Each stage should be PR-sized and include:

1. 2-4 synthetic tests
2. 2-3 real-paper validations
3. one broader regression sweep after the stage is green locally

---

## 11. Expected Outcome

If this spec is followed correctly:

1. ordinary papers should improve, not just exotic layout samples
2. composite-figure panel coverage should improve materially
3. mixed caption grammar pages should produce fewer absurd local bindings
4. figure/table co-page mistakes should become rarer and more explicit
5. residual OCR-v2 figure failures should be explainable by a much smaller set of visual-grammar limitations

That is the intended endpoint:

```text
not more heuristics,
but fewer, higher-level visual grammar capabilities
```

---

## 12. Relevant Files

- `paperforge/worker/ocr_figures.py`
- `paperforge/worker/ocr.py`
- `paperforge/worker/ocr_rebuild.py`
- `paperforge/worker/ocr_tables.py`
- `tests/test_ocr_figures.py`
- `tests/test_ocr_real_paper_regressions.py`
- `audit/`
- `project/current/ocr-v2-active-queue.md`
- `project/current/ocr-v2-generalization-boundary.md`
- `.opencode/skills/paperforge-development/workflows/ocr-truth-audit.md`
