# OCR-v2 Generalization Boundary

> Status: broader architecture note
> Readiness status: complete
> Active execution queue: `project/current/ocr-v2-active-queue.md`

## Cross-Links

- Active queue: `project/current/ocr-v2-active-queue.md`
- Evidence source: `project/current/ocr_rebuild_audit.md`
- Architecture boundary: `project/current/ocr-v2-generalization-boundary.md`

## Problem Statement

The OCR-v2 pipeline is no longer failing because the architecture is directionally wrong. The current problem is that the rule set is already complex, but the generalization boundary is still under-specified. A paper can look healthy after a local fix, then a different paper exposes 3-5 new small failures.

This means the work has moved from single-paper repair into layout-class generalization work.

## Why This Matters

The current system already has the right backbone:

```text
raw observations
-> structural signatures
-> stable anchors / families
-> zone inference
-> late role resolution
-> figure / table validation
-> render + health
```

The instability now comes from interactions between late-stage heuristics, especially when a paper layout does not fit the dominant assumptions.

## Current Assessment

### What is already solid

- Anchor-first parsing replaced early role guessing.
- `seed_role` is treated as proposal, not truth.
- verified-role gate exists for high-risk structural roles.
- 8 gold papers, trace-vs-expectations, and ownership contracts are already in repo.
- deterministic gold verification passes on the expanded fixture set.

### What is still under-formalized

1. Figure ownership and multi-panel interpretation.
2. Zone boundary authority on mixed body/reference/backmatter pages.
3. Reading-order authority vs renderer-side repair.
4. Layout-class coverage in the gold set.

## Main Risks

### 1. Figure ownership remains the primary trust risk

The current figure matcher already has candidate groups, but the generic path still reasons too much from asset order and not enough from an explicit ownership model.

Current observed limits:

- same-row grouping exists, but not full visual-grid reasoning
- grouped scoring still collapses groups to a single cluster bbox
- panel ownership is not explicitly modeled
- side-caption and irregular panel layouts remain fragile

### 2. Zone boundaries are improved but not yet fully authoritative

The codebase already has vertical and column-aware reference-zone artifacts, but `infer_zones()` still derives too much from `first_reference_page` and then expands outward. The remaining risk is same-page mixed layouts where page-level assumptions still overreach.

### 3. Renderer still carries meaningful reorder behavior

The renderer consumes verified artifacts, but it still performs tail ordering and mixed-page reorder logic. When fulltext order is wrong, debugging still spans both structure generation and rendering.

### 4. Layout-class coverage is now a tracked capability surface

The audit corpus is formalized via `audit/coverage_ledger.json` using the approved readiness-class taxonomy (`multi_panel`, `side_caption`, `same_page_ref_body_split`, `post_reference_biography`, `preproof_frontmatter`, `review_callout`, `special_structure`). `tests/test_ocr_real_paper_audit_contracts.py` enforces named representatives per class. Layout coverage is treated as a tracked capability surface rather than just a list of example papers.

## Current Live-Paper Triage

Recent rebuild checks on live vault artifacts sharpen the boundary between papers we should actively optimize for and papers we should only use as guardrail samples.

### RKSLQRIM is a guardrail sample, not a perfection target

`RKSLQRIM` combines several hostile layout traits in one paper:

- text wraparound around figures and tables
- figure/table same-page mixes
- inconsistent subfigure label conventions (`A)`, `(a)`, SI-style overlays)
- backmatter / SI structures that visually resemble object regions

The useful value of this paper is not "make every figure perfect". Its value is to provide negative constraints:

- do not mega-merge across wrapped text
- do not let figure and table ownership steal from each other on co-page layouts
- do not promote panel-local labels into formal caption candidates

Operationally, `RKSLQRIM` should be treated as a **defensive guardrail paper**. Residual ambiguity is acceptable if the pipeline avoids catastrophic ownership corruption.

### VFS8CBW2 remains the highest-value residual vulnerability family

`VFS8CBW2` still looks structurally wrong after rebuild, but not because the base OCR is hopeless. The live artifacts show that the formal long captions survive, while many panel titles / subplot labels also enter the candidate pool as `figure_caption_candidate` blocks.

This paper is best understood as:

```text
OCR noise is somewhat elevated
+
dense multi-panel composite pages
+
panel text falsely competing with formal captions
```

The important consequence is that `VFS8CBW2` exposes **generalizable vulnerabilities**, not just one ugly paper:

1. panel text / subplot labels can be mis-promoted into caption candidates
2. dense composite pages can still explode into many `unresolved_clusters`
3. one real caption plus many local titles can fragment ownership instead of producing a parent figure

This makes `VFS8CBW2` a better positive target for continued figure-ownership hardening than `RKSLQRIM`.

### Current pragmatic priority order

For closeout work, the live-paper priority is now:

1. `VFS8CBW2` — highest-value residual vulnerability family
2. `6FGDBFQN` — mixed caption-grammar / side-caption residuals
3. `3FDT9652` / `24YKLTHQ` — smaller residual ownership tails
4. `RKSLQRIM` — regression guardrail, not a perfection target
5. `DWQQK2YB` / `2UIPV93M` — now healthy enough to leave the high-priority queue

## Agreed Direction

Execution priority is currently governed by `project/current/ocr-v2-active-queue.md`.
This file remains the broader architectural boundary note, not the day-to-day execution queue.

### Priority 1: Figure ownership generalization

The near-term architectural target remains the existing group-first figure inventory plan, but it is now sequenced behind Gate 1 completeness work in the readiness model:

- candidate groups become the strict matching unit
- `single_asset` stays as a valid candidate path
- fallback paths must not steal grouped assets
- downstream reader/render payload shape stays stable

### Priority 2: Reading-order authority cleanup

Move toward a clearer single source of truth for ordering so renderer-side repair becomes smaller and easier to audit.

### Priority 3: Stronger boundary artifacts

Continue shifting mixed-page boundary authority toward explicit page + column + y-position artifacts rather than page-only inference.

### Priority 4: Layout-class test expansion

Expand fixture classification deliberately, not randomly:

- multi-panel
- side-caption
- same-page ref/body split
- post-reference biography/backmatter
- preproof frontmatter
- special review/callout layouts

## What We Should Not Do Yet

- Do not jump straight to full visual-grid modeling.
- Do not mix AJR-specific rescue logic into the generic group-first refactor.
- Do not add a large new artifact surface before existing structure artifacts are tightened.
- Do not treat every new paper failure as a one-off rule patch without classifying the failure type first.
- Do not optimize for perfect parsing of `RKSLQRIM`-style wraparound pages before the system is robust on higher-value composite vulnerability families such as `VFS8CBW2`.

## Relevant Files

- `PROJECT-MANAGEMENT.md`
- `paperforge/worker/ocr_figures.py`
- `paperforge/worker/ocr_document.py`
- `paperforge/worker/ocr_render.py`
- `tests/test_ocr_figures.py`
- `tests/test_ocr_real_paper_regressions.py`
- `audit/`
- `docs/superpowers/plans/2026-06-15-group-first-figure-inventory-plan.md`

## Next Actions

1. Keep `PROJECT-MANAGEMENT.md` and `project/current/ocr-v2-active-queue.md` aligned.
2. Use `docs/superpowers/specs/2026-06-18-ocr-v2-readiness-gates-design.md` as the definition of "state healthy."
3. Execute `docs/superpowers/plans/2026-06-18-ocr-v2-readiness-master-plan.md` as the active queue.
4. Implement Gate 1 completeness before reopening Gate 2 figure-group work.
5. Replace the stale fixture-ledger assumption with an audit-based coverage ledger before claiming Gate 4 coverage is formalized.
6. Reduce renderer-side reorder responsibilities once ordering authority is clearer.

## Archive Trigger

Move this file to `project/archive/` when all of the following are true:

1. Group-first figure inventory is implemented and verified.
2. The active OCR-v2 priority is no longer “generalization boundary formalization”.
3. `PROJECT-MANAGEMENT.md` has been updated to point at the next active topic.
