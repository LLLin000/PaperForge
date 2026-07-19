# DWQ Repair And Completeness Phase Design

> Date: 2026-06-18
> Status: approved design, pending user review
> Scope: clean stale OCR tracking files first, then repair the remaining real DWQQK2YB issues, rebuild derived artifacts, and stage the next completeness-check phase without mixing its implementation into the same risky change set.

## Goal

Run one coherent next phase that stops the branch from inheriting stale issue files, repairs the remaining real DWQQK2YB support-routing and figure-ownership problems, refreshes derived artifacts, and leaves the completeness-check layer fully specified and ready for implementation planning.

## Why This Phase Exists

The branch state after `PROJECT-MANAGEMENT.md` section `9.7` is healthier than several current tracking files imply.

Specifically:

- some issue files still report already-fixed P0-P2 items as open,
- DWQQK2YB still has one real support-routing gap,
- DWQQK2YB still has one real figure-ownership gap,
- completeness checking is the next structural safeguard, but it should not be coded in the same pass as the DW repairs.

## Chosen Approach

Chosen approach: fix the repository's truth surfaces first, then repair the remaining DWQQK2YB issues, then rebuild, and only after that plan the completeness-check implementation.

Execution order:

```text
1. Clean stale issue files and align them with 9.7
2. Repair DWQQK2YB frontmatter support routing
3. Repair DWQQK2YB figure ownership
4. Rebuild derived artifacts for affected papers
5. Write / preserve completeness-check spec and implementation plan as the next phase
```

Why this ordering won:

- stale issue files are currently poisoning the next-step narrative,
- support routing and figure ownership are real unresolved defects on DWQQK2YB,
- rebuild should happen after code repair so the derived assets reflect the fixed logic,
- completeness-check implementation should not be entangled with ownership debugging in the same patch set.

## Design Constraints

1. File cleanup happens first.
2. Only real unresolved issues stay in `project/current/` and `PROJECT-MANAGEMENT.md`.
3. DWQQK2YB support routing must become more layout-first and less page-1-text-special-case driven.
4. DWQQK2YB figure ownership must prefer unresolved over over-merged claims.
5. Rebuild is required after the code fix so derived figure assets and structure artifacts reflect the repaired logic.
6. Completeness check remains part of this phase's planning surface, but not part of the same production-code patch.

## Phase Breakdown

## 1. Truth-File Cleanup First

This phase begins by aligning the project trackers with the actual post-`9.7` branch state.

Files to reconcile first:

- `project/current/ocr-v2-remaining-issues-2026-06-18.md`
- `project/current/ocr-v2-closeout-priority.md`
- `PROJECT-MANAGEMENT.md`

The cleanup should remove or rewrite stale entries such as:

- `media_asset -> body_paragraph` when the latest evidence says it was a stale audit-truth bucket,
- outdated DW biography mismatch wording if the fixture/audit state has already moved,
- outdated P0-P2 residuals that were closed in section `9.7`.

The cleanup should preserve genuine unresolved items:

- DWQQK2YB frontmatter support/equal-contribution routing,
- DWQQK2YB figure ownership,
- any still-real backmatter taxonomy ambiguity,
- completeness-check as the next architectural safeguard.

Reason for doing this first:

- every later planning and implementation step otherwise inherits bad state and mis-prioritizes work.

## 2. DWQQK2YB Frontmatter Support Repair

### Problem

Some first-surviving-page support blocks on DWQQK2YB still fall into `frontmatter_noise` or body-like fallback when they should be preserved as `frontmatter_support`.

Examples include:

- corresponding-author support lines,
- equal-contribution support lines,
- support-like blocks adjacent to the title/author/affiliation cluster.

### Root Cause Direction

The current routing still leans too much on:

- page-1-only cases,
- text-start heuristics,
- raw-label-specific routing.

That leaves gaps for first-surviving-page cases where the blocks are:

- `raw_label=text`, not explicit `footnote`,
- visually embedded in the frontmatter cluster,
- support-like by geometry and style rather than by exact prefix.

### Intended Repair Direction

Promote layout evidence to the primary classifier for frontmatter support:

- first surviving page or first-frontmatter page,
- top-of-page placement,
- `frontmatter_main_zone` or `frontmatter_side_zone`,
- `support_like` style family or similar span/layout evidence,
- adjacency to title/authors/affiliations,
- optional marker help such as superscript / affiliation marker,
- text only as confirmatory evidence, not as the main gate.

Expected result:

- support-like blocks stay in frontmatter flow,
- they no longer leak into body or generic noise,
- they remain isolated from later tail/reference logic.

## 3. DWQQK2YB Figure Ownership Repair

### Problem

DWQQK2YB still fails figure ownership expectations on the mixed post-reference figure pages.

Observed current behavior:

- Figure 2 claims far too many assets,
- Figure 3 has a caption but no owned asset,
- Figure 4 also over-claims assets.

This is not a fulltext problem. It is an ownership/materialization problem in the figure-inventory path.

### Root Cause Direction

The likely failure seam is the candidate-group and asset-claim boundary logic, not caption text detection itself.

The current matching path appears too willing to treat a broad same-page media cluster as one ownership pool.

That creates two failure modes:

1. **over-merge**: one caption claims multiple visual bands or adjacent figure groups,
2. **empty local match**: a caption gets no local candidate group and becomes ambiguous.

### Intended Repair Direction

Ownership should be constrained by local visual partitioning before caption claim:

- partition same-page pre-caption media into smaller vertical/column-aware groups,
- keep caption ownership local to its most plausible band/group,
- do not let a narrow or local caption swallow the whole page's media cluster,
- if no local candidate exists, keep the figure unresolved rather than attaching the wrong assets.

Policy for this phase:

- prefer unresolved over wrong merge,
- fix DWQQK2YB specifically by improving the generic partition/claim logic, not by adding a one-paper rescue rule.

## 4. Rebuild After Repair

Once the code fixes land, rebuild is mandatory for the affected papers.

Why:

- figure JPGs and other derived artifacts are persisted outputs,
- earlier composite/crop/ownership logic changes do not retroactively rewrite already-emitted derived assets,
- rebuild is needed even when the underlying OCR result JSON is unchanged.

Canonical rebuild path for this phase:

- `scripts/dev/ocr_rebuild_paper.py`

This should be used to regenerate:

- structured blocks,
- reader figures,
- inventories,
- render outputs,
- derived asset files.

## 5. Completeness Check Stays In This Phase As Planned Next Work

The completeness-check layer remains part of the phase design, but as the next implementation slice after the DW repairs.

It keeps the already-approved structure:

- page text coverage,
- region coverage,
- fulltext coverage.

It remains:

- fuzzy, not exact-match,
- signal-first,
- inserted after raw-role assignment and before normalization for the early checks,
- render-audit-based for the downstream fulltext check.

This phase should preserve the spec and include it in the next implementation plan, but should not bundle its production-code changes with the DW ownership repair patch unless the user explicitly re-scopes again.

## Verification Plan

This phase must verify four things separately.

### 1. Truth files are no longer stale

- `project/current/*` and `PROJECT-MANAGEMENT.md` agree on what is really fixed vs really open.

### 2. DWQQK2YB support routing is correct

- corresponding-author / equal-contribution blocks on the first surviving page remain in frontmatter support flow,
- they do not leak into body output.

### 3. DWQQK2YB figure ownership is correct

- Figure 2 no longer over-claims,
- Figure 3 either resolves correctly or remains intentionally unresolved with no false claim,
- Figure 4 no longer over-claims,
- ownership regression test reflects the repaired generic logic.

### 4. Rebuilt artifacts reflect the fixed logic

- derived figure assets and reader-figure artifacts are regenerated after the fix,
- rebuild output no longer lags behind the repaired code path.

## Non-Goals

- Do not reopen all figure-group architecture work unless the DW fix proves insufficient.
- Do not mix completeness-check production implementation into the same risky code patch.
- Do not keep stale issues around “for history” in the active current-priority files.

## Deliverables

This combined phase should produce:

1. cleaned current-truth documentation,
2. a DWQQK2YB support-routing repair,
3. a DWQQK2YB figure-ownership repair,
4. a rebuild pass over affected derived artifacts,
5. a concrete next-step implementation plan that includes the already-approved completeness-check work.

## Decision

Proceed in this order:

1. clean stale files first,
2. repair DWQQK2YB frontmatter support,
3. repair DWQQK2YB figure ownership,
4. rebuild derived artifacts,
5. carry completeness-check forward as the explicitly planned next slice.
