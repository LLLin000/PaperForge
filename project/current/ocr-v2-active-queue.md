# OCR-v2 Active Queue
> Status: OCR-v2 is stable; OCR maintenance streaming and the selected-results UI are implemented on `feat/ocr-rebuild-ux`.
> Last updated: 2026-07-14

## Current checkpoint

- Retrieval recovery is merged to `master`; the real Literature-hub vault has a healthy 2560-dimensional vec0 index and working M / @ search paths.
- [OCR rebuild: streaming progress + maintenance UI redesign](https://github.com/LLLin000/PaperForge/issues/64) is implemented and reviewed.
- Multi-key `ocr rebuild` and full `ocr redo` emit separate, flushed progress streams and accept a cross-platform cooperative stop request between papers.
- The maintenance tab now exposes all papers plus the canonical `_needs_derived_rebuild()` recommendation set, selected batch actions, an above-table progress state, and full refresh on completion.
- Source Corpus data remains authoritative and was not modified during verification. Only the deployed plugin bundle and disposable maintenance cache were refreshed.

## Verification status

- Focused Python OCR paths: **97 passed, 1 Windows SIGINT test skipped, 1 unrelated empty-result regression deselected**.
- Plugin: **93 passed**; TypeScript check and production build passed.
- Live Obsidian verification: PaperForge 1.5.15 loaded without captured errors; maintenance rendered **734 All** rows and **700 Recommended** rows from the canonical backend flag.
- Live progress-state harness showed the floating progress bar, current key, Stop control, and disabled row actions.
- The repository-wide Python suite remains blocked during collection by the pre-existing `test_pr9a_resume_rebuild.py` import of removed `_assert_collections_healthy`.

## Frontier

- [ ] Chart a settings-and-recovery UX Wayfinder: define the destination, state model, onboarding boundary, and reference-product research needed for a larger frontend refactor.
- [ ] Decide how permanently non-actionable OCR quality limits leave the rebuild recommendation set and how the UI explains the next user action.
- [ ] Close or follow up [Unified rebuild UX](https://github.com/LLLin000/PaperForge/issues/63) after the OCR slice lands.

## Deferred

- Vector rebuild UX (PRD Slice 1): deferred.
- Memory/global maintenance cleanup (PRD Slice 3): deferred.
- OCR ETA and real-time per-row mutation: out of scope for the completed OCR slice.
