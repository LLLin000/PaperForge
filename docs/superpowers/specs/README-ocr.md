# OCR Design Index

Use this file as the quick index for the **current** OCR design and execution stack.

## Current OCR architecture source of truth

- `2026-07-04-ocr-pipeline-deepening-design.md`
  - Current top-level architecture for the A/B/C deepening pass.
  - Defines:
    - **Workstream A** — `ocr_object_writeback.py` ownership-evidence seam
    - **Workstream B** — `ocr_tail_settlement.py` tail/body/backmatter settlement seam
    - **Workstream C** — `pre_match_normalize(...)` / `post_match_normalize(...)` split behind `OCR_PIPELINE_V3`

- `2026-06-08-ocr-anchor-first-structured-parsing-design.md`
  - Base OCR v2 architecture.
  - Still the foundational reference for anchors, zones, family partition, structural gating, and render contracts.

## Current OCR implementation plans

- `../plans/2026-07-04-ocr-object-writeback-implementation-plan.md`
  - Workstream A implementation plan.

- `../plans/2026-07-04-ocr-tail-settlement-implementation-plan.md`
  - Workstream B implementation plan.

- `../plans/2026-07-04-ocr-pipeline-v3-implementation-plan.md`
  - Workstream C implementation plan.

- `../plans/2026-07-04-pre-merge-verification-plan.md`
  - Merge-gate checklist used to close the remaining blockers before merging A/B/C to `master`.

## Current merged status on `master`

- `ocr_object_writeback.py` is active on the default path.
- `ocr_tail_settlement.py` is active on the default path.
- `OCR_PIPELINE_V3` exists, but remains **OFF by default**.
- Current focused merge suite on merged `master`: **99 passed**.

## Still-relevant related OCR workflow design

- `2026-06-01-ocr-redo-single-source-design.md`
  - Approved design for OCR redo and canonical single-source fulltext behavior.

- `../plans/2026-06-01-ocr-redo-single-source.md`
  - Implementation plan for the single-source redo workflow.

## Notes

- The 2026-07-04 A/B/C stack is now the active OCR design thread.
- Workstream C is merged, but its new path is intentionally gated behind `OCR_PIPELINE_V3`; legacy behavior remains the default production path.
- Older OCR reading-order, convergence-only, and intermediate phase plans remain historical references, not current execution targets.
