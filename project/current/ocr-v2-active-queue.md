# OCR-v2 Active Queue
> Status: OCR-v2 is stable; OCR maintenance streaming with canonical per-row actions is implemented; the capability vocabulary and managed-runtime architecture are chosen.
> Last updated: 2026-07-14

## Current checkpoint

- Retrieval recovery is merged to `master`; the real Literature-hub vault has a healthy 2560-dimensional vec0 index and working M / @ search paths.
- [OCR rebuild: streaming progress + maintenance UI redesign](https://github.com/LLLin000/PaperForge/issues/64) is implemented and reviewed.
- Multi-key `ocr rebuild` and full `ocr redo` emit separate, flushed progress streams and accept a cross-platform cooperative stop request between papers.
- The maintenance tab now exposes all papers plus the canonical `_needs_derived_rebuild()` recommendation set, selected batch actions, an above-table progress state, and full refresh on completion.
- Per-row maintenance actions now route through `maintenanceActionForRow()` — rebuild/redo follow the canonical backend `display_action` rather than raw booleans.
- Destructive `redo` requires user confirmation via `maintenanceActionRequiresConfirmation()`.
- Cache refresh preserves the backend manifest (was overwriting it with empty on each refresh).
- Source Corpus data remains authoritative and was not modified during verification. Only the deployed plugin bundle and disposable maintenance cache were refreshed.
- [Current-contract audit](https://github.com/LLLin000/PaperForge/issues/66#issuecomment-4968837257) identified the migration boundary: preserve durable OCR/SQLite truth and recovery actions; replace global setup state, duplicate runtime/config resolution, and freshness-free snapshots.
- [Obsidian-native research](https://github.com/LLLin000/PaperForge/issues/67#issuecomment-4970653461) preserves the six-module IA, progressive setup, capability-gated commands, and minimal transient status chrome.
- [Desktop runtime/recovery research](https://github.com/LLLin000/PaperForge/issues/68#issuecomment-4970660288) establishes module-scoped repair, compatibility-gated updates, local redacted diagnostics, and user-reviewed issue drafts.
- **[#69](https://github.com/LLLin000/PaperForge/issues/69) resolved** at `issuecomment-4971161072`: orthogonal availability/activity/attention axes, 6-state capability ordinal, 12 canonical verbs, backend-owned severity and primary actions, maintenance projection.
- **[#70](https://github.com/LLLin000/PaperForge/issues/70) resolved** at `issuecomment-4971239398`: plugin-managed immutable runtime slots, system-Python bootstrap with validated-triplet fallback, single `active-runtime.json` pointer, `ManagedRuntime` class with `current()`/`status()`/`ensure()`, fail-closed command resolution.

## Verification status

- Focused Python OCR paths: **99 passed, 1 Windows SIGINT test skipped, 1 unrelated empty-result regression deselected**.
- Plugin: **93 passed**; TypeScript check and production build passed.
- Maintenance regression tests: **19/19 passed** (canonical action routing, confirmation gate, cache manifest preservation).
- Live Obsidian verification: PaperForge 1.5.15 loaded without captured errors; maintenance rendered **734 All** rows and **700 Recommended** rows from the canonical backend flag.
- Live progress-state harness showed the floating progress bar, current key, Stop control, and disabled row actions.
- The repository-wide Python suite remains blocked during collection by the pre-existing `test_pr9a_resume_rebuild.py` import of removed `_assert_collections_healthy`.

## Frontier

- [ ] Prototype the six-module control center ([#71](https://github.com/LLLin000/PaperForge/issues/71)) — design information hierarchy and interaction model for 安装 / 文献库 / OCR / 记忆 / 维护 / 帮助.
- [ ] Design actionable-only maintenance inbox with user-reviewed GitHub Issue draft reporting ([#72](https://github.com/LLLin000/PaperForge/issues/72)).
- [ ] Integrate the accepted model ([#73](https://github.com/LLLin000/PaperForge/issues/73)).
- [ ] Keep routine OCR quality outside maintenance; successful updates leave the queue, while unacceptable results use a user-reviewed GitHub Issue draft.

## Deferred

- Vector rebuild UX (PRD Slice 1): deferred.
- Memory/global maintenance cleanup (PRD Slice 3): deferred.
- OCR ETA and real-time per-row mutation: out of scope for the completed OCR slice.
