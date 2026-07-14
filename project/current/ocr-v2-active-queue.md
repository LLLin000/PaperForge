# OCR-v2 Active Queue
> Status: OCR-v2 is stable; OCR maintenance streaming is implemented, the control-center UX is charted, and the current setup/readiness/recovery contract audit is resolved.
> Last updated: 2026-07-14

## Current checkpoint

- Retrieval recovery is merged to `master`; the real Literature-hub vault has a healthy 2560-dimensional vec0 index and working M / @ search paths.
- [OCR rebuild: streaming progress + maintenance UI redesign](https://github.com/LLLin000/PaperForge/issues/64) is implemented and reviewed.
- Multi-key `ocr rebuild` and full `ocr redo` emit separate, flushed progress streams and accept a cross-platform cooperative stop request between papers.
- The maintenance tab now exposes all papers plus the canonical `_needs_derived_rebuild()` recommendation set, selected batch actions, an above-table progress state, and full refresh on completion.
- Source Corpus data remains authoritative and was not modified during verification. Only the deployed plugin bundle and disposable maintenance cache were refreshed.
- [Current-contract audit](https://github.com/LLLin000/PaperForge/issues/66#issuecomment-4968837257) identified the migration boundary: preserve durable OCR/SQLite truth and recovery actions; replace global setup state, duplicate runtime/config resolution, and freshness-free snapshots.

## Verification status

- Focused Python OCR paths: **99 passed, 1 Windows SIGINT test skipped, 1 unrelated empty-result regression deselected**.
- Plugin: **93 passed**; TypeScript check and production build passed.
- Live Obsidian verification: PaperForge 1.5.15 loaded without captured errors; maintenance rendered **734 All** rows and **700 Recommended** rows from the canonical backend flag.
- Live progress-state harness showed the floating progress bar, current key, Stop control, and disabled row actions.
- The repository-wide Python suite remains blocked during collection by the pre-existing `test_pr9a_resume_rebuild.py` import of removed `_assert_collections_healthy`.

## Frontier

- [ ] Define the shared module capability-state and action vocabulary in [#69](https://github.com/LLLin000/PaperForge/issues/69), now unblocked by the audit.
- [ ] Complete [Obsidian-native patterns](https://github.com/LLLin000/PaperForge/issues/67) and [desktop installation/health/recovery patterns](https://github.com/LLLin000/PaperForge/issues/68); keep the managed-runtime decision blocked until #68 closes.
- [ ] Keep routine OCR quality outside maintenance; successful updates leave the queue, while unacceptable results use a user-reviewed GitHub Issue draft.
- [ ] Close or follow up [Unified rebuild UX](https://github.com/LLLin000/PaperForge/issues/63) after the OCR slice lands.

## Deferred

- Vector rebuild UX (PRD Slice 1): deferred.
- Memory/global maintenance cleanup (PRD Slice 3): deferred.
- OCR ETA and real-time per-row mutation: out of scope for the completed OCR slice.
