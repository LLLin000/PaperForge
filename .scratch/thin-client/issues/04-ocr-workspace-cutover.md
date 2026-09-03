# 04 — OCR Workspace & Processing Domain Cutover

**What to build:** Refactor the OCR Workspace and processing interactions to route through `PaperForgeClient`. Table metadata, pipeline versions, and execution states are populated from `client.probe("lineage")` and typed detail queries; rebuild, redo, and batch operations execute via `client.runAction()`; streaming progress and cooperative cancellation route through client operation controllers.

**Blocked by:**
- 03 — Foundation & Maintenance Domain Cutover

**Status:** complete

- [x] Route OCR Workspace paper table rows through `client.probe("lineage")` and `client.queryOcrPapers()`, eliminating direct reads of OCR directories or cache files.
- [x] Connect individual and batch action buttons ("Rebuild Derived", "Run OCR", "Redo") to `client.runAction()`, honoring backend `ActionDescriptor.availability` and `execution_mode`.
- [x] Connect the Workspace progress bar to the streaming output of `client.runAction()`, displaying phase and item results as emitted by the backend.
- [x] Wire the Stop button to `client.cancelActiveOperation()`, ensuring cooperative cancellation reaches the transport.
- [x] Assert that global background OCR activity is observed as "Running" via probe truth, but local "Stop" control is enabled only when this client owns the active operation handle.
- [x] Add Vitest tests for OCR Workspace data loading, action dispatch, availability gating, and cooperative cancellation over `MockTransport`.

Implementation notes: the Workspace no longer resolves Python runtimes, imports `execFile`, or depends on `OcrProcessController`; `ocr.redo` remains an internal legacy command and the user-facing Redo action routes through canonical `ocr.run`.
Verification: focused client/OCR suite **60 passed / 0 failed**; `npm run typecheck` clean.
