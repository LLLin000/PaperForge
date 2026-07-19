# OCR Truth Surface Realignment Design

> Date: 2026-06-19
> Status: executed on `ocr-v2`
> Scope: realign the OCR-v2 project truth files so rebuild-audit work and readiness-gate completion can coexist without narrative conflict

## Goal

Create one coherent project truth surface for OCR-v2.

The repo must stop forcing readers to choose between two half-compatible stories:

1. OCR-v2 completed all readiness gates and passed blind audit.
2. The 452-paper rebuild audit opened a new queue of post-readiness remediation work.

Both can be true, but only if the files explicitly distinguish framework readiness from rebuild-output hardening.

This realignment is intentionally narrow. It is not a broad documentation rewrite project.

## Non-Goals

This design does not:

- change OCR algorithm behavior,
- decide exact code patches for the rebuild findings,
- reopen the readiness model itself,
- turn every historical doc into a fresh spec,
- rewrite the technical analysis bodies of historical files.

## Execution-Range Constraint

This design must stay small.

Allowed edits:

- headers,
- status lines,
- “Next Work” / active queue sections,
- cross-links,
- contradictory wording that misstates the active truth.

Disallowed edits:

- rewriting historical technical analysis bodies for style,
- re-explaining already completed readiness-gate technical details,
- turning truth-surface cleanup into a repo-wide prose modernization pass.

## Problem Statement

The current repo truth surface is split across:

- `PROJECT-MANAGEMENT.md`
- `project/current/ocr-v2-closeout-priority.md`
- `project/current/ocr-v2-generalization-boundary.md`
- `project/current/ocr-v2-remaining-issues-2026-06-18.md`
- `project/current/ocr_rebuild_audit.md`

These files no longer operate at the same level.

Some files speak about:

- branch-level architecture readiness,
- known-layout confidence,
- blind audit completion,

while the new rebuild audit speaks about:

- full-corpus output quality,
- health false positives,
- ownership write-through defects,
- post-gate hardening priorities.

The missing piece is not more analysis. It is a clean separation of evaluation surfaces.

## Core Distinction To Preserve

The repo must distinguish these two claims explicitly.

### Claim A: OCR-v2 framework readiness

Meaning:

- the anchor-first architecture is the right backbone,
- the known readiness gates are complete,
- unseen-paper blind audit did not reveal new failure families,
- the branch is no longer blocked on pre-readiness architectural uncertainty.

### Claim B: rebuild-output hardening remains

Meaning:

- the broader rebuild corpus still reveals output-layer defects,
- these defects are mostly post-structure and post-ownership contract problems,
- they justify more work before a “production-polished rebuild surface” claim,
- they do not invalidate the readiness-gate conclusion.

The repo should never again imply that Claim B automatically negates Claim A.

## Design Principle: One Question Per Truth File

Each active truth file should answer one primary question.

If a file tries to answer two questions at once, it becomes narrative sludge.

## Target Truth Surface

### Final hierarchy

The truth surface should converge on the following hierarchy:

- **Authoritative active queue:** one file only
- **Evidence source:** detailed rebuild audit evidence
- **Architecture boundary note:** broader conceptual risk and boundary note
- **Historical readiness residuals:** frozen residual files from the completed readiness cycle
- **Narrative ledger:** chronological record of what happened and why

The active queue and the evidence source must never again be the same conceptual file.

### 1. `project/current/ocr-v2-closeout-priority.md`

Primary question:

> What is the single active OCR queue right now?

Required role after realignment:

- become the short authoritative queue for current OCR work,
- explicitly state whether the active queue is branch-merge work, rebuild hardening, or another phase,
- link outward to broader notes and detailed audits.

Recommended outcome:

- either rename this role into a clearer active queue file such as `project/current/ocr-v2-active-queue.md`,
- or keep the filename temporarily but mark it explicitly as `ACTIVE QUEUE — post-readiness rebuild hardening` and treat the old closeout role as historical.

Required change:

- stop implying that “all gates done” means “nothing important remains,”
- replace merge-readiness-only framing with explicit branch state plus active post-gate queue.

### 2. `project/current/ocr-v2-generalization-boundary.md`

Primary question:

> What architectural risks still matter conceptually, independent of today’s queue?

Required role after realignment:

- remain the broader architecture note,
- describe what the backbone solved and what classes remain sensitive,
- stop acting like the day-to-day execution queue.

Required change:

- add explicit language that the readiness-gate story is complete,
- frame rebuild hardening as a new surface layered on top of that completed story.

### 3. `project/current/ocr-v2-remaining-issues-2026-06-18.md`

Primary question:

> What residuals remained at the end of the readiness-gate cycle?

Required role after realignment:

- freeze it as a readiness-cycle residual file,
- stop letting it pretend to be the active queue after the full rebuild audit.

Required change:

- clearly label it as readiness-cycle residuals,
- add a pointer to the new rebuild-audit remediation queue.

### 4. `project/current/ocr_rebuild_audit.md`

Primary question:

> What did the full rebuild corpus audit find, and what remediation order does it imply?

Required role after realignment:

- become the detailed post-readiness rebuild hardening evidence source,
- own the problem inventory and fix priority for the rebuild surface,
- not pretend to redefine OCR-v2 architecture from scratch.

Required change:

- state explicitly that it is a post-readiness audit surface,
- avoid language that sounds like the readiness gates were fake or invalid.

### 5. `PROJECT-MANAGEMENT.md`

Primary question:

> What happened, why, and what comes next?

Required role after realignment:

- record the narrative handoff clearly,
- make the transition from readiness completion to rebuild hardening explicit,
- identify which file now governs next execution.

`PROJECT-MANAGEMENT.md` must not become the source of next execution tasks. When it conflicts with the active queue, the active queue wins.

Required change:

- add a dedicated transition section naming the new active queue,
- remove or overwrite wording that leaves “merge now” and “new major queue” standing side by side without explanation.

## Required Narrative Contract

After realignment, every active file should preserve the following contract:

```text
OCR-v2 architecture readiness is complete.
Post-readiness rebuild hardening is now the active queue.
These are different evaluation surfaces, not contradictory truths.
```

If one active file violates this contract, the truth surface is not aligned.

## Naming And Status Rules

### Rule 1: Active queue files must say they are active

If a file governs current work, its header must explicitly say so.

### Rule 2: Historical residual files must say what cycle they belong to

If a file describes residuals from a completed cycle, that status must be visible in the header.

### Rule 3: Broader architecture notes must not double as execution queues

Architecture notes may explain risk direction, but must not silently override the active queue.

### Rule 4: Detailed audits must declare their evaluation surface

`ocr_rebuild_audit.md` should explicitly say it is evaluating rebuild outputs across the corpus, not rejudging readiness-gate completion.

## Required Realignment Actions

### Action A: declare the active queue explicitly

One current file must win as the active queue for OCR work after this design lands.

Recommended winner:

- `project/current/ocr-v2-closeout-priority.md`

but with renamed framing if necessary so “closeout” does not mislead readers.

Preferred end state:

- `project/current/ocr-v2-active-queue.md` as the clean long-term queue name,
- or a clearly relabeled transitional queue if file churn must be minimized.

### Action B: install explicit cross-links

Each active truth file should link to:

- the active queue,
- the broader architecture note,
- the rebuild audit if it is relevant,
- the historical residual file if it still matters for interpretation.

The point is not more prose. The point is zero ambiguity about which layer a reader is on.

### Action C: rewrite, do not merely append

Where a prior statement is no longer the active truth, it should be rewritten, not just followed by a newer contradictory paragraph.

This is especially important for:

- merge-readiness language,
- “all gates done” language,
- “next work” sections.

The editing rule is narrow: rewrite only the contradictory control-plane surfaces, not the underlying historical analysis bodies.

### Action D: standardize OCR state vocabulary

The truth surface should use a stable vocabulary set:

- `readiness-gate complete`
- `post-readiness rebuild hardening`
- `active queue`
- `broader architecture note`
- `historical readiness residuals`

Do not alternate casually between “close-out,” “done,” “remaining issues,” and “next work” without naming which surface is being discussed.

## Contradiction Pass Checklist

The implementation plan must include a contradiction pass over active truth files for phrases such as:

- `merge now`
- `nothing remains`
- `all done`
- `final remaining`
- `active remaining issues`
- `readiness incomplete`
- `reopen architecture`

For each hit, the reviewer must classify whether it is talking about:

1. readiness-cycle status,
2. active rebuild-hardening queue,
3. historical analysis that should be preserved but clearly relabeled.

No contradiction pass is complete if it only appends a new sentence without resolving the old conflicting one.

## Acceptance Criteria

This design is successful when all of the following are true:

1. A new reader can understand in under five minutes that readiness completion and rebuild hardening are different truths.
2. Only one active file governs “what to do next.”
3. `PROJECT-MANAGEMENT.md` explains the handoff from readiness gates to rebuild hardening.
4. `ocr_rebuild_audit.md` is clearly framed as post-readiness evidence, not a repudiation of the OCR-v2 backbone.
5. The broader architecture note remains useful without pretending to be the active queue.
6. Historical residual files are clearly labeled as historical-cycle residuals.

## Risks

### Risk 1: leaving stale language in place

If old “merge now” or “all done” wording stays beside new rebuild-hardening language, the design fails even if a new file exists.

Mitigation:

- rewrite active headers and “Next Work” sections directly.

### Risk 2: inventing a third narrative layer

Adding too many meta-files could make the truth surface worse.

Mitigation:

- prefer reassigning current files over creating new ones unless a new file is truly necessary.

### Risk 3: treating documentation repair as cosmetic

This is not cosmetic. It directly affects planning quality, agent handoff quality, and whether future work attacks the right surface.

Mitigation:

- define explicit acceptance criteria and one authoritative queue.

## Execution Order

The implementation plan for this design should proceed in this order:

1. declare the vocabulary and active queue,
2. rewrite active-file headers and status sections,
3. relabel historical residual files,
4. align `PROJECT-MANAGEMENT.md` handoff language,
5. run a final contradiction pass across all active OCR truth files.

## References

- `PROJECT-MANAGEMENT.md`
- `project/current/ocr-v2-closeout-priority.md`
- `project/current/ocr-v2-generalization-boundary.md`
- `project/current/ocr-v2-remaining-issues-2026-06-18.md`
- `project/current/ocr_rebuild_audit.md`
- `docs/superpowers/specs/2026-06-18-ocr-v2-readiness-gates-design.md`
