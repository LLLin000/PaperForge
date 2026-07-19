# OCR-v2 Unified Close-Out Design

> Date: 2026-06-17
> Status: active
> Scope: unify the remaining OCR-v2 close-out work into one bounded execution track instead of splitting it across multiple small plans.

## Goal

Finish the current OCR-v2 close-out pass with one coherent sequence:

1. drop useless preproof cover page 1 at the structured-block layer
2. conservatively tighten tail/post-reference normalization so it stops damaging valid structure
3. run a bounded rebuild and audit pass on the 8 gold papers plus up to 10 additional vault papers selected for layout coverage
4. rewrite the residual error picture from evidence
5. decide whether figure-group work is truly the next dominant blocker

The purpose of this design is not to open another major OCR architecture branch. The purpose is to close the current one cleanly.

## Why This Design Exists

The codebase already passed through the large OCR-v2 redesign: anchor-first parsing, late role resolution, verified-role gate, figure/table inventory, and production-path replay harness.

The remaining work is now smaller in count but easy to scatter:

- one remaining `preproof` page-1 problem
- residual post-reference/tail normalization issues
- some expectations and audits that may now be stale
- unresolved figure ownership work that may or may not actually be the top blocker after another audit pass

Without a unified close-out design, the branch can bounce between small fixes and large architecture ideas without a stable stop condition.

## Non-Goals

This design does not:

- redesign OCR-v2 from scratch
- run full-vault rebuilds indiscriminately
- widen `backmatter_heading` classification through a large phrase list
- add journal-specific figure rescue logic
- force figure-group refactor into the current pass before post-fix audit evidence says it is necessary

## Current Branch Assumptions

The design assumes the following are already true on `ocr-v2`:

- same-page body/reference split has already improved materially
- page-1 correspondence routing now has an explicit `frontmatter_support` path
- tail/post-reference damage is smaller than before but not fully closed
- remaining known issues include:
  - preproof cover page 1 noise still entering the document path
  - post-reference normalization still having edge-case damage or unnecessary taxonomy pressure
  - figure ownership still unresolved on some mixed-layout papers

## Design Overview

The unified close-out pass is intentionally conservative.

It uses the existing pipeline and changes as little surface area as possible:

- preproof cover-page removal happens early so downstream logic never sees useless page-1 cover blocks
- tail/post-reference cleanup prefers "do not damage valid structure" over introducing richer semantic labeling
- audit expansion is bounded to a small, purposeful layout sample instead of the full vault
- figure-group work is demoted from an assumed next step to a decision gate driven by residual evidence

## Section 1: Preproof Page-1 Removal

### Problem

Some preproof papers carry a page-1 cover sheet that is not useful article content. It adds title/author/PII-like clutter that then has to be suppressed, rescued, or routed later.

This is the wrong layer to fight it. If the page is truly useless cover material, the cleanest fix is to remove it before document normalization.

### Decision

When the pipeline can confidently identify a page-1 preproof cover page, it should remove that page from the structured-block stream before `normalize_document_structure()` runs.

### Rationale

- the user explicitly does not want that information preserved
- dropping it early removes downstream contamination in zones, role rescue, and rendering
- this is cleaner than keeping the page and repeatedly teaching later logic to ignore it

### Boundary

This is not a general "drop page 1 if it looks weird" rule.

It applies only when there is strong evidence of a true preproof cover page, using existing preproof signals and page-1 block patterns already available in the pipeline.

### Expected Outcome

- page-1 preproof cover blocks do not appear in `structured_blocks`
- downstream frontmatter suppression logic has less work to do
- the known DW preproof page-1 issue disappears at the source instead of being patched later

## Section 2: Conservative Tail/Post-Reference Cleanup

### Problem

The remaining post-reference issues are mostly not about needing a perfect `backmatter_heading` taxonomy. They are about not harming blocks that should remain stable.

Trying to make `backmatter_heading` more complete without heavy text matching would be brittle. Trying to do it with heavy text matching would create exactly the kind of heuristic bloat the close-out should avoid.

### Decision

Do not expand `backmatter_heading` aggressively.

Instead:

- preserve valid existing `section_heading` / `subsection_heading` / related heading roles when the evidence is already good
- avoid converting valid body or object-adjacent blocks into `backmatter_body`
- keep post-reference normalization focused on preventing structural damage rather than perfecting taxonomy

### Rationale

- fewer text-matching heuristics
- lower regression risk
- aligns with the user's preference not to lean on fragile phrase-based heading detection
- keeps the close-out focused on trust and stability, not label cosmetics

### Expected Outcome

- fewer false `backmatter_body` conversions
- valid headings survive more often as ordinary heading roles
- post-reference structure is cleaner even if the taxonomy remains intentionally boring

## Section 3: Bounded Audit Expansion

### Problem

The next verification pass needs broader evidence than the current 8 gold papers alone, but a full-vault rebuild is unnecessary and expensive.

### Decision

Run the close-out verification pass on:

- the existing 8 gold papers
- up to 10 additional vault papers selected specifically to expand layout coverage

### Selection Method

The extra papers should be selected by layout class, not by randomness or convenience.

Priority layout classes to cover:

1. preproof cover page papers
2. same-page body/reference split papers
3. biography/backmatter-tail papers
4. multi-panel figure papers
5. narrow-caption or side-caption figure papers
6. table-heavy papers
7. publisher margin-noise papers

The chosen set does not need to maximize paper count. It needs to maximize coverage diversity.

### Rationale

- bounded cost
- higher signal than a blind larger run
- gives enough evidence to decide whether figure ownership or some other class is really the next blocker

### Expected Outcome

- the branch gets a broader residual map without opening a full-vault operational loop
- layout coverage becomes more trustworthy for the next prioritization decision

## Section 4: Residual Write-Back

### Problem

The branch has accumulated multiple status documents, plans, and handoff notes. After the bounded rebuild/audit pass, the residual state needs to be rewritten from current evidence so the branch does not drift back into contradictory next steps.

### Decision

After the bounded rebuild/audit pass, update the active project trackers so they reflect the real remaining categories.

At minimum, update:

- `project/current/ocr-error-root-cause-fix-queue.md`
- `PROJECT-MANAGEMENT.md`

### What Must Be Written Back

The write-back should separate:

- issues solved by the current pass
- stale truth / stale expectations revealed by the new audit
- remaining document-structure residuals
- remaining figure-ownership residuals

### Rationale

- keeps the branch's next-step guidance singular
- prevents old June plans from silently retaking control of prioritization

## Section 5: Figure-Group Decision Gate

### Problem

Figure-group work is real, but it is also a larger architectural thread. Reopening it too early would blur whether the current close-out pass actually succeeded.

### Decision

Do not make figure-group refactor an automatic part of this implementation pass.

Instead, turn it into a decision gate after rebuild and audit.

### Gate Condition

Reopen `group-first figure inventory` only if the post-audit residuals show that:

1. figure ownership is now the dominant remaining class
2. it clearly exceeds the remaining document-structure and truth-maintenance residuals
3. the bounded sample confirms it across more than one paper/layout family

### Rationale

- keeps the current pass bounded
- avoids premature architecture expansion
- makes the figure-group decision evidence-led instead of taste-led

## Data Flow Summary

The intended close-out flow becomes:

```text
raw OCR blocks
-> structured block build
-> preproof page-1 drop (when confidently identified)
-> normalize_document_structure()
-> conservative tail/post-reference cleanup
-> render + artifacts
-> rebuild/audit on 8 gold + up to 10 extra vault papers
-> residual rewrite
-> figure-group decision gate
```

## Testing Strategy

The implementation plan derived from this spec should include tests at four levels:

1. **unit tests**
   - preproof page-1 removal fires only on confident preproof cover pages
   - post-reference cleanup preserves valid heading/body/object structure conservatively

2. **document-pipeline tests**
   - `normalize_document_structure()` sees the intended inputs after the preproof drop
   - tail/post-reference behavior does not regress in known mixed-page cases

3. **real-paper regression tests**
   - the current gold-paper production-path checks remain green or improve
   - specific known papers covering preproof and mixed tail behavior are locked

4. **bounded audit verification**
   - 8 gold papers plus up to 10 vault papers are rebuilt and inspected through the repo's audit helpers

## Risks And Mitigations

### Risk 1: dropping page 1 too aggressively

Mitigation:

- require strong preproof-cover evidence
- keep the filter narrow and explicit
- lock non-preproof page-1 behavior with regression tests

### Risk 2: conservative cleanup leaves taxonomy imperfect

Mitigation:

- accept this intentionally
- prioritize stability over label refinement in the current pass
- only reopen taxonomy work if it later becomes a genuine blocker

### Risk 3: 10-paper sample misses an important layout family

Mitigation:

- select papers deliberately by layout class
- document which class each chosen sample covers

### Risk 4: figure-group still turns out to be the main blocker

Mitigation:

- this design already includes a decision gate to reopen that work immediately after audit evidence confirms it

## Acceptance Criteria

This unified close-out pass is successful if all of the following are true:

1. preproof cover page 1 is removed at the structured-block layer for the targeted preproof case(s)
2. post-reference/tail cleanup causes fewer false structure conversions without expanding large phrase-matching taxonomies
3. the branch is verified on 8 gold papers plus up to 10 extra vault papers selected for layout coverage
4. project-tracking docs are rewritten to reflect the post-pass residuals from current evidence
5. the branch ends with a clear evidence-based answer to: "is figure-group the next dominant blocker or not?"

## Implementation Handoff

This spec should produce one implementation plan, not several small competing plans.

That plan should be task-based, but unified, with at least these task groups:

1. preproof page-1 structured-layer removal
2. conservative tail/post-reference cleanup
3. bounded rebuild and audit sample selection/execution
4. residual write-back
5. figure-group decision gate
