# OCR-v2 Active Queue

> Status: ACTIVE QUEUE — post-readiness rebuild hardening
> Last updated: 2026-06-19
> Scope: authoritative next-work queue for OCR after readiness-gate completion

## Queue Contract

OCR-v2 architecture readiness is complete.
Post-readiness rebuild hardening is now the active queue.
This file governs next execution when other OCR truth files disagree.

## Current Priorities

1. Rebuild-output pollution fixes
2. Ownership write-through fixes
3. Figure/table inventory contract hardening
4. Additive health-v2 semantics

## Cross-Links

- Evidence source: `project/current/ocr_rebuild_audit.md`
- Architecture boundary note: `project/current/ocr-v2-generalization-boundary.md`
- Historical readiness residuals: `project/current/ocr-v2-remaining-issues-2026-06-18.md`
- Narrative ledger: `PROJECT-MANAGEMENT.md`
