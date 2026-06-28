# OCR-v2 Readiness Gates Design

> Date: 2026-06-18
> Status: draft design approved in chat, pending user review
> Scope: define the formal readiness gates that OCR-v2 must pass before it can be called layout-robust for broad academic-paper parsing.

## Goal

Replace the current informal "looks healthy" judgment with a single readiness model.

The model should answer three operational questions:

1. What work is still required before OCR-v2 can be called structurally healthy?
2. In what order should that work happen?
3. What evidence is strong enough to say the branch is ready for broader-layout confidence, even before unseen-paper blind audit begins?

This design covers the first four readiness gates and treats unseen-paper blind audit as the next gate after those four are complete.

## Non-Goals

This design does not:

- redesign the OCR-v2 architecture,
- replace the existing completeness-check design,
- replace the existing group-first figure inventory plan,
- execute the blind audit itself,
- declare OCR-v2 universally robust across all journals after local fixes alone.

## Current Problem

The repo has already moved beyond "the architecture is wrong."

The remaining risk is that OCR-v2 can look healthy on known fixtures while still failing to generalize across layout classes. The current truth is spread across several files:

- `project/current/ocr-v2-closeout-priority.md`
- `project/current/ocr-v2-generalization-boundary.md`
- `project/current/ocr-v2-remaining-issues-2026-06-18.md`
- `PROJECT-MANAGEMENT.md`
- the existing completeness and figure-inventory plans/specs

Those files are individually useful, but they do not yet form one clean readiness story. Some judgments are stale because they still speak in the language of "close-out" or "zone-boundary pass" rather than explicit readiness gates.

## Readiness Model

OCR-v2 should be considered "state healthy" only after the first four gates below are complete and verified.

Gate 5 is the next-stage validation step, not part of this implementation cycle.

### Gate 1: Completeness Detection Exists And Works

Purpose:

- catch likely OCR text loss early,
- stop later structure logic from reasoning over silently incomplete text,
- separate extraction loss from later render/path loss.

Required outcome:

- page-level coverage signals exist,
- region-level completeness signals exist for high-value text blocks,
- rendered fulltext gap signals exist downstream,
- the signals are conservative and evidence-bearing rather than aggressive auto-repair.

Primary reference:

- `docs/superpowers/specs/2026-06-18-ocr-completeness-check-design.md`

Exit criteria:

1. `build_structured_blocks()` emits completeness evidence at the block/page level.
2. Tests prove page-level low-coverage detection on synthetic and normal cases.
3. Tests prove region-level gap classification on empty/short/truncated cases.
4. A downstream rendered-text coverage audit exists and emits structured gaps.
5. Existing PDF backfill is explicitly treated as complementary, not replaced.

### Gate 2: Figure Ownership Generalization Is No Longer The Primary Trust Risk

Purpose:

- stop same-page and multi-panel figure ownership from remaining ambiguous on structurally common layouts,
- move the inventory path from asset-order reasoning toward explicit candidate-group ownership.

Required outcome:

- grouped candidates become the primary matching unit,
- fallback paths cannot steal valid grouped assets,
- known DW-style ownership failures are resolved by model logic rather than tolerated as "captured but ambiguous."

Primary reference:

- `docs/superpowers/plans/2026-06-15-group-first-figure-inventory-plan.md`

Exit criteria:

1. Group-first inventory is implemented and verified.
2. Same-page pair/triple panel layouts pass deterministic unit coverage.
3. `DWQQK2YB`-class mixed post-reference figure pages no longer rely on ambiguity-acceptable assertions.
4. Reader/render payload shape remains stable unless a proven incompatibility forces a small contract update.
5. Health/audit artifacts expose grouped-vs-single behavior clearly enough for debugging.

### Gate 3: Ordering And Boundary Authority Are Centered In Structure, Not Renderer Repair

Purpose:

- reduce hidden reorder behavior in render stages,
- make mixed body/reference/backmatter pages auditable from structure artifacts,
- give the pipeline a clearer single source of truth for reading order and boundary decisions.

Required outcome:

- same-page mixed layouts depend on explicit page/column/y-position evidence,
- renderer-side reorder responsibilities shrink,
- debugging wrong order no longer requires chasing both structure and renderer heuristics equally.

Primary references:

- `paperforge/worker/ocr_document.py`
- `paperforge/worker/ocr_orchestrator.py`
- `paperforge/worker/ocr_render.py`
- `project/current/ocr-v2-generalization-boundary.md`

Exit criteria:

1. Structure-layer artifacts are the primary authority for mixed-page ordering.
2. Renderer keeps only minimal presentational ordering behavior.
3. Same-page ref/body/backmatter boundary regressions have explicit coverage and no active P0 residuals.
4. Project docs no longer describe renderer-side repair as a meaningful remaining dependency for correctness.

### Gate 4: Layout-Class Coverage Is Deliberate Enough To Support Generalization Claims

Purpose:

- stop treating each newly found paper as an isolated surprise,
- formalize which layout/risk classes OCR-v2 is expected to handle,
- make the gold set representative rather than merely useful.

Required outcome:

- the audit-paper ledger and taxonomy become more precise,
- the audited real-paper set deliberately covers high-risk layout classes,
- each class has concrete verification expectations.

Primary references:

- `audit/`
- `tests/test_ocr_real_paper_audit_contracts.py`
- `project/current/ocr-v2-generalization-boundary.md`

Target layout/risk classes for this pass:

- multi-panel
- side-caption
- same-page ref/body split
- post-reference biography/backmatter
- preproof frontmatter
- review/callout/special-structure pages

Exit criteria:

1. Taxonomy is tightened beyond broad single/multi-column labels.
2. The audited real-paper set contract explicitly covers the target classes above.
3. Fixture expectations include enough page/object assertions for those classes.
4. Project docs describe layout-class coverage as a tracked capability surface, not just a list of example papers.

### Gate 5: Unseen-Paper Blind Audit

This is intentionally outside the current implementation cycle.

Purpose:

- validate that the first four gates produce real generalization rather than overfitting to known fixtures.

Entry condition:

- Gates 1-4 are complete and verified,
- project truth files say OCR-v2 is ready for blind audit,
- no active P0 trust risk remains in the known set.

Expected outcome:

- a bounded sample of unseen papers is run without code changes during the audit window,
- failures are classified by layout class rather than patched immediately,
- OCR-v2 is judged by how often it reveals new failure families, not by whether every paper is perfect.

## Execution Order

The readiness work should proceed in this order:

1. Gate 1: completeness-check layer
2. Gate 2: figure ownership generalization
3. Gate 3: ordering/boundary authority cleanup
4. Gate 4: layout-class coverage expansion
5. Gate 5: unseen-paper blind audit

Why this order:

- Gate 1 protects the rest of the pipeline from silent text-loss reasoning.
- Gate 2 removes the largest remaining trust-risk class.
- Gate 3 makes structural truth easier to audit and reduces renderer coupling.
- Gate 4 should be tightened after the core structural rules stop shifting heavily.
- Gate 5 is only meaningful after the system has passed the known-layout gates.

## Project Truth-File Realignment

As part of the readiness planning work, the project docs should be updated so they tell one consistent story.

### Files That Must Be Updated

- `project/current/ocr-v2-closeout-priority.md`
- `project/current/ocr-v2-generalization-boundary.md`
- `project/current/ocr-v2-remaining-issues-2026-06-18.md`
- `PROJECT-MANAGEMENT.md`

### Required Realignment Rules

1. `ocr-v2-closeout-priority.md` should stop framing the branch mainly as a close-out topic and instead become the short authoritative readiness queue.
2. `ocr-v2-generalization-boundary.md` should remain the broader architecture/risk note, but its "Next Actions" must reflect the readiness-gate order rather than the older zone-boundary-close-out storyline.
3. `ocr-v2-remaining-issues-2026-06-18.md` should reflect active readiness blockers, deferred low-priority conservatism, and the fact that blind audit is next-stage rather than current-slice work.
4. `PROJECT-MANAGEMENT.md` should add a new section recording the readiness-gates transition, what became outdated, and which document now governs next execution.
5. When a prior judgment is no longer the active truth, it should be rewritten rather than left standing beside the new thread.

## Plan Structure

The follow-up implementation plan should be a single master readiness plan.

That plan should:

- define one active execution thread,
- split work into four implementation phases matching Gates 1-4,
- treat Gate 5 as a post-readiness gate with entry criteria only,
- reuse existing detailed artifacts where they are already strong,
- add only the missing plan sections for Gate 3 and Gate 4,
- explicitly include the project-truth-file cleanup as part of the work rather than as optional documentation debt.

### Reuse Strategy

Reuse, do not rewrite, the following where possible:

- Gate 1 detail: `2026-06-18-ocr-completeness-check-design.md`
- Gate 2 detail: `2026-06-15-group-first-figure-inventory-plan.md`

Add new master-plan sections for:

- Gate 3 ordering/boundary authority cleanup,
- Gate 4 layout taxonomy + fixture coverage expansion,
- project truth-file realignment,
- Gate 5 blind-audit trigger and success rubric.

## Acceptance Standard For "State Healthy"

The branch may be called "state healthy" only when all of the following are true:

1. Gates 1-4 are complete and verified.
2. No active P0 trust-risk item remains in known fixtures.
3. Figure ownership no longer passes by ambiguity tolerance on known hard cases.
4. Structural ordering truth primarily lives upstream of render.
5. Layout capability is expressed as an explicit tested taxonomy, not just anecdotal paper coverage.
6. Project truth files agree on the active thread and next gate.

This phrase does not yet mean "universal robustness across all journals."

It means OCR-v2 is strong enough on known layout classes to justify the next-stage unseen-paper blind audit.

## Risks To Avoid

1. Turning the readiness plan into a large rewrite of already-good plans.
2. Reopening completed close-out work without evidence of current regressions.
3. Claiming generalization from known fixtures alone.
4. Expanding taxonomy randomly instead of by failure/risk class.
5. Leaving old project judgments in place after the active execution thread changes.

## Deliverables From This Planning Pass

1. A written readiness-gates design doc.
2. A master implementation plan for Gates 1-4 plus Gate 5 entry criteria.
3. Updated project truth files that point at the readiness-gate thread.

## Success Condition For This Design

This design is successful if the next implementation plan can be written without ambiguity about:

- what "state healthy" means,
- which four gates belong to the current cycle,
- which gate is intentionally deferred,
- which docs are authoritative,
- and what evidence is required before broader confidence claims are allowed.
