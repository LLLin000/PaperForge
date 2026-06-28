# OCR Design Index

Use this file as the quick index for current OCR design docs.

## Current OCR architecture source of truth

- `2026-06-08-ocr-anchor-first-structured-parsing-design.md`
  - Current clean target architecture for OCR parsing.
  - Covers anchors, zones, reference-first tail parsing, family partition, and figure/table validation.

## Current OCR implementation plan

- `../plans/2026-06-08-ocr-anchor-first-structured-parsing-plan.md`
  - Task-by-task implementation sequence for the anchor-first redesign.

## Still-active related OCR workflow design

- `2026-06-01-ocr-redo-single-source-design.md`
  - Separate approved design for OCR redo and canonical single-source fulltext behavior.

- `../plans/2026-06-01-ocr-redo-single-source.md`
  - Implementation plan for the single-source redo workflow.

## Notes

- This worktree keeps only the current OCR v2 architecture/design baseline plus the still-relevant single-source redo docs.
- Older OCR reading-order, structured-pipeline phase plans, score-tuning plans, and convergence-only intermediate OCR drafts were removed after they were superseded by the anchor-first design.
- `2026-05-31-ocr-skip-and-tags-preserve-design.md` and its paired plan remain because they are mixed OCR/plugin frontmatter behavior work, not replaced by the anchor-first parsing redesign.
