# OCR-v2 Project Management History Snapshot

> Archived: 2026-06-17
> Source: root `PROJECT-MANAGEMENT.md` before index split
> Purpose: preserve the detailed OCR-v2 history that previously lived in the root file

## Snapshot Scope

This archive preserves the pre-split management detail for OCR-v2:

- branch status and architectural direction
- development phases and remediation rounds
- current-state snapshot as of 2026-06-15
- gold-paper coverage status and gap reports
- planned next steps at the time of the snapshot
- key file map and decision log
- 2026-06-16 / 2026-06-17 session handoff notes

## 1. Branch And Architecture Summary

- Branch: `ocr-v2`
- Base: `master`
- Summary at snapshot time: structural redesign of the OCR pipeline from early semantic role guessing to anchor-first structured parsing.

The architectural direction recorded in the original file was:

```text
raw observations
-> structural signatures
-> stable anchors / families
-> zone inference
-> late role resolution
-> figure / table validation
-> render + health
```

Core principles preserved from the original log:

1. `seed_role` is a proposal, never the final role.
2. verify-required roles must be accepted with evidence.
3. zone and role are separate concepts.
4. reference-tail protection comes before loose body reconstruction.
5. frontmatter is source-backed, not OCR-invented.

## 2. Development Phases Captured In The Old Root File

The pre-split root file tracked the OCR-v2 work in broad phases:

- artifact foundation
- structured inventory for figures/tables
- health and rendering
- runtime integration and compatibility
- evidence and search
- anchor-first redesign
- figure/table reader separation
- verified structural role gate
- production-path root-cause remediation
- structural gate anchor and author matching fixes
- final gap-closure rounds

The original file also preserved the rationale for each phase, especially the move away from early role guessing and the requirement that downstream render output consume verified structure rather than speculative roles.

## 3. Historical Fix Rounds Preserved

The old root file contained multiple detailed fix batches with commit-by-commit notes, including:

- figure caption gate rescue
- `unassigned` role handling in zone inference and boundary detection
- cross-page sequential figure matching fallback
- heading merge before seed-role assignment
- backmatter boundary fixes
- source-frontmatter anchor bridge into normalization
- author matching overhaul
- frontmatter-noise override for verify-required roles
- formal-library author enrichment
- same-page body/reference vertical split
- box/content merge behavior
- same-page table/figure pre-emission before references
- tail rendering fixes for pages without a reference heading

These details were previously tracked directly in `PROJECT-MANAGEMENT.md` and are intentionally preserved here as the historical narrative of how OCR-v2 reached its current shape.

## 4. Current-State Snapshot Preserved From 2026-06-15

The pre-split root file recorded the following high-level state:

- structural gate installed and integrated
- role assignment reduced to seed/proposal behavior
- zone inference fixed for the `unassigned` truthiness bug
- page-1 frontmatter boundary working after upstream fixes
- tail spread body-continuation veto installed
- post-reference backmatter zone installed
- document normalization and gate integrated
- cross-page sequential figure matching installed
- render cleanup completed for reader figure output
- heading line-wrap merge installed
- gold fixtures expanded to 8 papers
- trace-vs-expectations and ownership contracts running

The deterministic gold command recorded in the old file was:

```bash
python -m pytest tests/test_ocr_real_paper_audit_contracts.py tests/test_ocr_trace_vs_expectations.py tests/test_ocr_real_paper_regressions.py -q
```

Result at that snapshot: `22 passed, 42 skipped`.

## 5. Historical Gap Snapshot

The old root file preserved these live concerns:

- DW preproof frontmatter suppression
- DW biography-page expectation mismatch
- CAQ same-page reference/body conflict
- CAQ correspondence footnote routing
- figure inventory still asset-first
- AJR side-caption recovery explicitly deferred

It also preserved the larger interpretation that reader coverage was no longer the urgent issue; grouped or multi-panel figure interpretation was the deeper remaining weakness.

## 6. Historical Next-Step Direction

At snapshot time the immediate handoff target was:

- execute the group-first figure inventory plan

Acceptance boundaries recorded in the old file:

1. candidate groups become the strict matching unit
2. `single_asset` remains valid
3. fallback and sequence promotion must not split claimed groups
4. reader/render payload shape must stay compatible
5. AJR improvements remain observational in that phase

The old root file also preserved rebuild commands, test commands, file maps, design-doc links, and decision-log entries for new contributors.

## 7. Gold Fixture Expansion Session Notes Preserved

The original file ended with a 2026-06-16 / 2026-06-17 session section covering:

- expanded `expected_bugs` coverage across all 8 gold papers
- root-cause categories across frontmatter, figures, tail zones, headings, formulas, and whitespace
- the figure-processing handoff, including multi-panel risk notes
- K7R8PEKW before/after notes
- a parked hard case for adjacent formal figure captions with risky auto-separation
- a later tail-rendering fix for K7R8PEKW page 16

Those notes remain historically relevant, but they are no longer appropriate to keep inline in the root management index.

## 8. Why This Snapshot Exists

The root `PROJECT-MANAGEMENT.md` had become both:

- the navigation entry point for current work
- the full historical ledger for OCR-v2

That made active work harder to see and harder to maintain. This snapshot preserves the detailed history while allowing the root file to shrink into an index.
