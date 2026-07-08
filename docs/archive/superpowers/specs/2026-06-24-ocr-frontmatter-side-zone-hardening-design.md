# OCR Frontmatter Side Zone Hardening Design

> Date: 2026-06-24
> Status: proposed
> Scope: fix false frontmatter-side capture of real early-body-page headings and body continuations by tightening existing zone inference and early-frontmatter demotion rules. This pass must not add a page-state machine, a new structural gate, or new persistent artifacts.

## Goal

Fix an important OCR-v2 regression class where real body headings on early body pages are misrouted into `frontmatter_side_zone`, then downgraded by the existing structural gate and suppressed from render output.

The target is to restore correct behavior by narrowing unsafe heuristics in the current two-layer design:

1. `zone inference`
2. `structural gate`

This pass changes only the first layer and one adjacent early-demotion helper. It does not introduce a new interpretation layer.

## Why This Spec Exists

The failure seen in paper `49PY5UCJ` looks, at first glance, like heading inference failure. It is not.

Observed pipeline state for page 2:

1. `THE MOLECULAR IDENTITY AND REGULATION OF THE MCU COMPLEX`
   - `seed_role = section_heading`
   - final `role = unknown_structural`
   - `role_verification_status = HOLD`
   - `role_source = structural_gate`
   - `zone = frontmatter_side_zone`

2. `The Pore Forming Subunits`
   - `seed_role = subsection_heading`
   - final `role = subsection_heading`
   - `role_verification_status = ACCEPT`
   - `zone = frontmatter_side_zone`

The important conclusion is:

```text
The main heading is already inferred correctly.
It is later suppressed because zone inference misclassifies it as frontmatter-side,
and the gate only trusts headings that reach body/tail heading evidence.
```

This paper should be easy for the system because:

1. body family is stable
2. heading typography is stable
3. two-column structure is stable
4. raw `paragraph_title` labels are present

The failure is therefore not missing upstream signal. It is over-aggressive zone routing.

## Root Cause

### 1. `_is_frontmatter_side_candidate()` is too aggressive on early pages

The current logic in `paperforge/worker/ocr_document.py` allows page-2 blocks to be treated as frontmatter-side using a coarse proxy like:

```text
early page + top half + narrow or side-column + width/font mismatch
```

This is too broad.

For `49PY5UCJ`, page 2 is already a real body page, but several genuine headings still satisfy those geometry checks:

1. they are above the 55% vertical cutoff
2. they are narrower than body paragraphs
3. they use heading typography different from the body family

Those are normal properties of body headings, not frontmatter evidence.

### 2. `frontmatter_side_zone` is a dangerous sink and should be conservative

Once a real heading enters `frontmatter_side_zone`, later logic becomes defensive rather than generative.

The structural gate is doing what it was designed to do:

1. accept headings backed by heading artifact evidence
2. accept headings in `body_zone` or `tail_body_zone`
3. hold unverified high-risk structural roles

This means the correct fix is not to add another gate or another page-status layer. The correct fix is to stop poisoning the zone assignment.

### 3. `accepted_heading_block_ids` currently amplify inconsistency

The current accepted-heading builder in `paperforge/worker/ocr_document.py` adds bare `block_id` values for body-zone headings.

Because `block_id` is page-local in this OCR data, not globally unique, page-2 headings can be accidentally verified by unrelated later-page headings that reuse the same `block_id`.

This produces the observed unstable pattern:

1. some page-2 headings survive despite wrong zoning
2. some page-2 headings are held and suppressed
3. the behavior looks random even though the underlying logic is deterministic

This pass treats that as part of the same close-out because it directly affects heading verification consistency.

## Chosen Approach

Chosen approach: tighten the existing early-page frontmatter-side heuristic and add strong heading/body vetoes, while leaving the structural gate architecture intact.

Why this approach won:

1. it fixes the actual source of error instead of layering a new interpreter on top
2. it stays close to merge by preserving the current two-layer architecture
3. it makes `frontmatter_side_zone` conservative, which is the correct safety posture
4. it avoids introducing `page_state`, new gate rules, or new document artifacts

Rejected alternatives:

1. page-state machine
   - more expressive, but unnecessary for this bug class
   - increases architecture and review burden

2. new heading acceptance gate based on page-state + typography + body continuity
   - directionally valid, but over-build for the current failure
   - treats the symptom after zone poisoning already happened

## Design Constraints

1. no new `page_state` layer
2. no new persistent artifact fields
3. no new structural gate class or second-stage heading verifier
4. page number may be supporting evidence, but not a standalone classifier for `frontmatter_side_zone`
5. the first surviving page may remain comparatively permissive because it may contain real frontmatter even when original page 1 was dropped
6. pages after the first surviving page must require explicit frontmatter/furniture evidence for `frontmatter_side_zone`
7. real body headings and body continuations must be protected from frontmatter-side capture

## Required Behavior Changes

## 1. Narrow `_is_frontmatter_side_candidate()`

The dangerous rule pattern is:

```python
if page <= 2 and top_half and (narrow or side_column):
    ...
    return True
```

This must be removed or reduced so that early-page narrow/side-column geometry alone is no longer sufficient evidence.

New governing rule:

```text
The first surviving page may remain comparatively permissive because it may
contain real frontmatter even when the original page 1 was dropped.

Pages after the first surviving page must require explicit frontmatter or
publisher-support furniture evidence.
```

For pages after the first surviving page, geometry such as `top_half`, `narrow`, `side_column`, width mismatch, or font-family mismatch may only be supporting evidence. It may not be the trigger by itself.

## 2. Restrict positive evidence for `frontmatter_side_zone`

For pages after the first surviving page, `frontmatter_side_zone` should only be reachable when the block text strongly resembles real frontmatter/support furniture, such as:

1. `correspondence`
2. `corresponding author`
3. `received:`
4. `accepted:`
5. `published online`
6. `equal contribution`
7. `orcid`
8. `highlights`
9. `key points`
10. equivalent publisher/submission support text

Position and shape remain confirmatory evidence, not the primary classifier.

For short furniture headings such as `Highlights` or `Key points`, text alone is not
sufficient after the first surviving page. Require side/support geometry or
structured-support context as additional evidence.

## 3. Add hard vetoes for heading-like blocks

Inside `_is_frontmatter_side_candidate()`, heading-like blocks must veto frontmatter-side classification unless the text itself is explicit frontmatter/support furniture.

Examples of furniture exceptions:

1. `correspondence`
2. `corresponding author`
3. `highlights`
4. `received:` / `accepted:` / `published online`
5. `equal contribution`
6. `orcid`
7. equivalent publisher citation/support metadata

For non-furniture text, the following are veto signals:

1. `seed_role in {section_heading, subsection_heading, sub_subsection_heading}`
2. `marker_signature.type in {canonical_section_name, heading_arabic, heading_decimal}`
3. block text looks like a real section/subsection heading rather than support furniture
4. the block is followed on the same page and same reading column by body continuation

The principle is:

```text
frontmatter_side is a dangerous exclusion zone.
It must be hard to enter and easy to veto.
```

## 4. Protect heading-followed-by-body patterns

If a heading-like block is followed on the same page and same column by `body_paragraph`, the heading must not be treated as frontmatter-side.

This should be decided with existing local page geometry and reading order helpers, not by adding a new document state model.

The check must be bounded more tightly than "some later body exists below it".
It should inspect the nearest meaningful block in the same page and same reading column.
The veto applies only when:

1. that nearest meaningful block is body-like
2. the vertical gap is reasonably small for a heading-to-body transition
3. no display/table/reference/structured-insert boundary lies between the heading and that body block

This protection is needed because this exact pattern appears in `49PY5UCJ`:

1. main heading
2. subsection heading
3. ordinary body paragraph directly below

That sequence is strong body-flow evidence and should override early-page side heuristics.

## 5. Narrow `_demote_early_frontmatter_body_leaks()`

The demotion helper should stop using broad `page <= 2` assumptions.

It should be limited to the first surviving page and only before the first accepted body-start signal on that page.

More concretely:

1. it may only demote blocks on the first surviving page
2. it may only demote blocks before the first accepted body-start signal on that page
3. once a section/subsection heading or long body paragraph is seen on that page, the helper must stop demoting subsequent blocks on that page

Body-start signal may be detected from either `role` or `seed_role`, including
section/subsection headings and long body-like paragraphs.

It must not keep acting as a second coarse early-page suppressor after real body flow has already started.

## 6. Make accepted heading verification use artifact-safe ids

The current accepted-heading builder should not rely on bare page-local `block_id` values when constructing accepted heading membership.

Requirement:

1. accepted heading ids must use the same artifact-safe identity model already used elsewhere for duplicate page-local block ids
2. heading acceptance must not leak across pages because two unrelated blocks share the same local `block_id`
3. this change must only normalize membership identity; it must not change heading acceptance policy

This is not a new artifact. It is a consistency correction inside the existing heading acceptance path.

## Non-Goals

This pass must not:

1. add `page_state`
2. add a new heading gate
3. redesign structural gate policy
4. reopen tail/reference architecture
5. introduce journal-specific rescue branches

## Implementation Outline

The implementation should be limited to the following seams:

1. `paperforge/worker/ocr_document.py`
   - `_is_frontmatter_side_candidate()`
   - early-frontmatter demotion helper(s), especially `_demote_early_frontmatter_body_leaks()`
   - accepted heading id builder

It is acceptable to extend `_is_frontmatter_side_candidate()` with local context
arguments such as `first_surviving_page` and `page_blocks`, as long as no new
persistent artifact or document-level `page_state` is introduced.

2. no intentional changes to the public contract of `paperforge/worker/ocr_structural_gate.py`

If structural gate code changes at all, they should be limited to consuming the corrected accepted-heading ids, not to adding new policy.

## Verification Plan

Verification for this pass must lock four classes.

### A. Target regression

For `49PY5UCJ`:

1. page-2 main section heading does not enter `frontmatter_side_zone`
2. page-2 heading after it does not enter `frontmatter_side_zone` when it is clearly in body flow
3. heading-followed-by-body sequence remains renderable
4. the final fulltext contains the expected heading hierarchy instead of suppressing the major section heading

### B. Body continuation safety

For at least one control paper with legitimate early body flow:

1. page-2 body paragraphs remain in `body_zone`
2. heading/body adjacency is not demoted by early-frontmatter cleanup

### C. Frontmatter-side retention

For at least one paper containing real frontmatter support furniture:

1. correspondence-like support blocks are still excluded from body flow
2. clearly publisher/support side material is still routable to `frontmatter_side_zone`

### D. Preproof-drop first surviving page safety

For at least one control paper where original page 1 was dropped and page 2 becomes the first surviving page:

1. title/authors/frontmatter support on the first surviving page are still preserved correctly
2. the stricter post-frontmatter rule does not misclassify that first surviving page as ordinary body-only layout

### E. Heading-like furniture safety

For at least one paper where `Highlights`, `Key points`, or `Correspondence` is OCR-labeled as `paragraph_title` or another heading-like seed:

1. explicit furniture text can still route to `frontmatter_side_zone`
2. the heading-like veto does not force that block into body flow

### F. Page-1 compatibility

For a control paper with ordinary first-page frontmatter:

1. title/authors/affiliations behavior does not regress
2. page-1 side support remains suppressible

### G. Cross-page block-id collision safety

For a fixture or targeted regression where two different pages reuse the same local `block_id`:

1. accepting `p2:4` must not implicitly accept `p7:4`
2. accepting `p7:4` must not implicitly accept `p2:4`

## Expected Result

After this pass:

1. early body pages are no longer treated as pseudo-frontmatter because they contain narrow headings near the top
2. heading verification becomes stable because accepted heading identity is page-safe
3. the existing structural gate becomes less brittle without being expanded

The intended end state is:

```text
zone inference becomes more conservative about swallowing content,
and the existing gate can keep doing simple verification work.
```

That is the smallest change that makes the system more logically coherent and more mergeable.

## Implementation Guardrail

Implementation must be deletion/narrowing-first.
If the fix appears to require adding a new broad heuristic, stop and report
instead of expanding the rule set.
