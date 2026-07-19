# OCR-v2 Active Queue
> Status: OCR-v2 is stable; all eight PRD #74 child issues (#75–#80) are implemented and verified; #81 Release N+1 owner cutover is next.
> Last updated: 2026-07-19

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

- **[#71](https://github.com/LLLin000/PaperForge/issues/71) resolved**: six-module control-center HTML prototype with 5 scenarios, plain-button switcher, primary attention zone, responsive layout (768px breakpoint), and capability-gated actions. Independent Critical/Important PASS review. Design decisions recorded in `docs/prototypes/2026-07-14-six-module-control-center.{html,md}`.
- **[#72](https://github.com/LLLin000/PaperForge/issues/72) resolved**: actionable-only maintenance inbox prototype with single-action rows, inline issue-draft review, local redacted export, and confirmation-first report flow. Independent Critical/Important PASS review. Design decisions recorded in `docs/prototypes/2026-07-14-maintenance-issue-reporting.{html,md}`.
- **[#73](https://github.com/LLLin000/PaperForge/issues/73) resolved**: locked migration, security, platform, accessibility, and release-gate acceptance contract after five-domain audit and independent review.
- **[#74](https://github.com/LLLin000/PaperForge/issues/74) published**: split into eight agent-ready issues (#75–#82) with native dependencies.
- **[#75](https://github.com/LLLin000/PaperForge/issues/75) implemented and reviewed**: bare/headless/modular setup share `SetupPlan`; schema-v2 `vault_config` wins; v1 path keys are warned read fallback; all configured directories are forwarded; required failures return non-zero.
- **[#76](https://github.com/LLLin000/PaperForge/issues/76) implemented**: schema-v1 Installation/Help probes flow through the six-module Overview; persisted malformed/stale envelopes fail closed; backend set_config/update actions route to setup.
- **Wayfinder navigation refinement approved and implemented**: `概览 / 模块详情 / 维护 / 帮助` shell live across #77/#78/#80. Installation owns Agent platform/Skills under Agent 集成; no empty placeholder detail pages. All six modules (Installation, Library, OCR, Memory, Maintenance, Help) are real probes.
- **[#77](https://github.com/LLLin000/PaperForge/issues/77) implemented**: Managed Runtime lifecycle with immutable slots, synchronous fail-closed `current`, probed `status`, install/repair/update/rollback/cancel/retention, managed-first dispatch, Release-N fallback, four-destination navigation shell. Verification: 192 focused + 289 full tests; typecheck/build clean. Merged to `master`.
- **[#78](https://github.com/LLLin000/PaperForge/issues/78) implemented**: real Library/OCR/Memory capability probes with module-detail-navigation, installation-navigation, and capability-state views. Python owns capability facts; TypeScript exact allowlist/fail-closed rendering. Verification: 58 backend + 171 plugin tests; typecheck/build clean; Obsidian smoke verified.
- **[#79](https://github.com/LLLin000/PaperForge/issues/79) implemented**: SecretStorage for capability secrets. Backend-focused gate passes; plugin full suite passes; typecheck/build clean.
- **[#80](https://github.com/LLLin000/PaperForge/issues/80) implemented**: Maintenance probe with backend-derived actionable-only rows, privacy-safe local issue drafts, and accessible destructive confirmation. Backend owns exact actions from `probe maintenance --json`; frontend renders via derived VerbModel with primary null for quality-ok items. Verification: backend focused gate 77/77; plugin full suite 381/382 (pre-existing capability-state test expecting help.stale but receiving help.invalid_response); typecheck/build clean; production bundle 264.4KB; Obsidian 1.12.7 smoke 730/768: entry focus, actionable-only rows, keyboard Enter, accessible destructive confirmation with exact backend effect, focus trap/restoration, owned inert cleanup, redacted editable issue draft, no token input/auto-open, explicit GitHub open only, URL re-redaction, no horizontal overflow.

## Verification status

- Focused Python OCR paths: **99 passed, 1 Windows SIGINT test skipped, 1 unrelated empty-result regression deselected**.
- Plugin: **93 passed**; TypeScript check and production build passed.
- Maintenance regression tests: **19/19 passed** (canonical action routing, confirmation gate, cache manifest preservation).
- Live Obsidian verification: PaperForge 1.5.15 loaded without captured errors; maintenance rendered **734 All** rows and **700 Recommended** rows from the canonical backend flag.
- Live progress-state harness showed the floating progress bar, current key, Stop control, and disabled row actions.
- Prototype #71 (control center): **Critical PASS (5/5), Important PASS (11/11)** — independent reviewer dimensions confirmed.
- Prototype #72 (maintenance inbox): **Critical PASS (4/4), Important PASS (6/6)** — independent reviewer dimensions confirmed.
- Both prototypes browser-verified at 768px viewport with scenario-switching, action-button interactions, expand/collapse diagnostics, and issue-draft flow.
- Issue #77 verification: **192 focused + 289 full tests passed**; typecheck/build clean.
- Issue #78 verification: **58 backend + 171 plugin tests passed**; typecheck/build clean; Obsidian 730px/768px smoke.
- Issue #79 verification: **backend-focused gate, plugin full suite pass**; typecheck/build clean.
- Issue #80 verification: **backend focused gate 77/77; plugin full suite 381/382** (only pre-existing capability-state test expecting help.stale but receiving help.invalid_response); typecheck/build clean; production bundle 264.4KB; real Obsidian 1.12.7 smoke at 730 and 768 confirmed all acceptance criteria.
- Issue #75 verification: **61/61 focused tests passed**; independent review returned **Spec PASS / Quality APPROVED**.
- Issue #76 verification: **21/21 backend probe tests and 169/169 plugin tests passed**; TypeScript check and production build passed; live Obsidian stale-cache/action-label smoke test and independent review passed.
- No production plugin code was modified during prototype work.
- The repository-wide Python suite remains blocked during collection by the pre-existing `test_pr9a_resume_rebuild.py` import of removed `_assert_collections_healthy`.
## Frontier

- [x] Prototype the six-module control center ([#71](https://github.com/LLLin000/PaperForge/issues/71)).
- [x] Design the actionable-only maintenance inbox ([#72](https://github.com/LLLin000/PaperForge/issues/72)).
- [x] Lock migration/acceptance contract (#73), publish PRD #74, and create dependency-linked issues #75–#82.
- [x] Canonicalize setup and configuration migration ([#75](https://github.com/LLLin000/PaperForge/issues/75)).
- [x] Implement Installation/Help capability tracer ([#76](https://github.com/LLLin000/PaperForge/issues/76)).
- [x] Implement Managed Runtime lifecycle + navigation shell ([#77](https://github.com/LLLin000/PaperForge/issues/77)).
- [x] Expose Library, OCR, Memory capability tracers ([#78](https://github.com/LLLin000/PaperForge/issues/78)).
- [x] Implement SecretStorage for capability secrets ([#79](https://github.com/LLLin000/PaperForge/issues/79)).
- [x] Implement Maintenance probe with backend-derived rows, privacy-safe draft, destructive confirmation ([#80](https://github.com/LLLin000/PaperForge/issues/80)).
- [ ] Implement Release N+1 owner cutover ([#81](https://github.com/LLLin000/PaperForge/issues/81)).

## Deferred

- Vector rebuild UX (PRD Slice 1): deferred.
- Memory/global maintenance cleanup (PRD Slice 3): deferred.
- OCR ETA and real-time per-row mutation: out of scope for the completed OCR slice.
- Release N+2 cutover shim deletion remains blocked by its native issue dependency (#82).
