# OCR-v2 Close-Out Priority

> Status: active authoritative readiness queue
> Last updated: 2026-06-18
> Owner file for next work: `docs/superpowers/plans/2026-06-18-ocr-v2-readiness-master-plan.md`

## Why This File Exists

The repo had multiple valid but competing June 15-17 narratives:

- `PROJECT-MANAGEMENT.md` still pointed at the group-first figure refactor as the next task.
- `project/current/phase2-root-cause-analysis.md` and `project/current/ocr-error-root-cause-fix-queue.md` showed that the largest remaining production risk had shifted to zone-boundary authority.
- `project/current/ocr-v2-generalization-boundary.md` correctly described the broader architectural boundary, but it was too high-level to serve as the next execution thread.

This file is the tie-breaker. If another document disagrees about what to do next, this file wins until it is archived.

## Current Baseline

- Branch: `ocr-v2`
- Audit baseline date: `2026-06-17`
- Verified audited blocks: `945 / 1097` (`86.1%`)
- Remaining mismatches after Phase 2: `152`

## Close-Out Pass Completed After 9.7 (2026-06-18)

The unified close-out plan has been executed, and P0-P2 layout close-out is recorded in `PROJECT-MANAGEMENT.md` section 9.7:
- Preproof cover page 1 dropped at structured-block layer
- Tail/post-reference cleanup tightened conservatively
- 8 gold + 10 vault papers rebuilt and audited
- Regression suite: 202P / 1F / 43S
- DW diff audit: 57% verified; CAQ diff audit: 88% verified

That pass is no longer the active execution thread. The branch has now moved into readiness-gate work: finish the first four gates required for "state healthy," then run unseen-paper blind audit as the next-stage gate.

## Remaining readiness blockers before "state healthy"
- Gate 1: completeness-check layer implementation
- Gate 2: figure ownership generalization on mixed post-reference and multi-panel pages
- Gate 3: ordering/boundary authority still partly depends on renderer-side repair
- Gate 4: audit-paper taxonomy and coverage ledger are not yet formal enough for generalization claims

## Next Work
1. Execute `docs/superpowers/plans/2026-06-18-ocr-v2-readiness-master-plan.md`
2. Implement Gate 1 first: fuzzy OCR completeness-check layer (`docs/superpowers/specs/2026-06-18-ocr-completeness-check-design.md`)
3. Keep Gate 5 (unseen-paper blind audit) out of the current cycle; use it only after Gates 1-4 are complete

## Authoritative Reference
This file is the tie-breaker for the active readiness queue. `project/current/ocr-v2-generalization-boundary.md` remains the broader architecture note, and `docs/superpowers/specs/2026-06-18-ocr-v2-readiness-gates-design.md` defines the readiness model the queue is following.
