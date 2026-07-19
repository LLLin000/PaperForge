# OCR-v2 Active Queue
> Status: OCR-v2 is stable; PRD #74 issues #75–#82 are implemented. Live use exposed a missing-probe release package and a superseded control-center UX contract; publish the backend package first, then route the approved redesign through Ask Matt.
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
- The approved replacement is `control-center-ux-redesign.md`: five operational modules, three top-level destinations, contextual Module Detail, progressive setup, user-problem-only Maintenance, and Obsidian-native presentation.
- The plugin design system is now explicit in `paperforge/plugin/DESIGN.md`; product language is defined in `paperforge/plugin/CONTEXT.md`.
- **[#69](https://github.com/LLLin000/PaperForge/issues/69) resolved** at `issuecomment-4971161072`: orthogonal availability/activity/attention axes, 6-state capability ordinal, 12 canonical verbs, backend-owned severity and primary actions, maintenance projection.
- **[#70](https://github.com/LLLin000/PaperForge/issues/70) resolved** at `issuecomment-4971239398`: plugin-managed immutable runtime slots, system-Python bootstrap with validated-triplet fallback, single `active-runtime.json` pointer, `ManagedRuntime` class with `current()`/`status()`/`ensure()`, fail-closed command resolution.

- **[#71](https://github.com/LLLin000/PaperForge/issues/71) resolved**: six-module control-center HTML prototype with 5 scenarios, plain-button switcher, primary attention zone, responsive layout (768px breakpoint), and capability-gated actions. Independent Critical/Important PASS review. Design decisions recorded in `docs/prototypes/2026-07-14-six-module-control-center.{html,md}`.
- **[#72](https://github.com/LLLin000/PaperForge/issues/72) resolved**: actionable-only maintenance inbox prototype with single-action rows, inline issue-draft review, local redacted export, and confirmation-first report flow. Independent Critical/Important PASS review. Design decisions recorded in `docs/prototypes/2026-07-14-maintenance-issue-reporting.{html,md}`.
- **[#73](https://github.com/LLLin000/PaperForge/issues/73) resolved**: locked migration, security, platform, accessibility, and release-gate acceptance contract after five-domain audit and independent review.
- **[#74](https://github.com/LLLin000/PaperForge/issues/74) published**: split into eight agent-ready issues (#75–#82) with native dependencies.
- **[#75](https://github.com/LLLin000/PaperForge/issues/75) implemented and reviewed**: bare/headless/modular setup share `SetupPlan`; schema-v2 `vault_config` wins; v1 path keys are warned read fallback; all configured directories are forwarded; required failures return non-zero.
- **[#76](https://github.com/LLLin000/PaperForge/issues/76) implemented**: schema-v1 Installation/Help probes flow through the six-module Overview; persisted malformed/stale envelopes fail closed; backend set_config/update actions route to setup.
- **Current navigation is superseded**: the live `概览 / 模块详情 / 维护 / 帮助` shell and Installation-owned Agent/Skills are retained only until the redesign issues land. The approved target removes top-level Module Detail, makes Foundation the persistent environment module, and makes Agent Integration a fifth operational module.
- **[#77](https://github.com/LLLin000/PaperForge/issues/77) implemented**: Managed Runtime lifecycle with immutable slots, synchronous fail-closed `current`, probed `status`, install/repair/update/rollback/cancel/retention, managed-first dispatch, Release-N fallback, four-destination navigation shell. Verification: 192 focused + 289 full tests; typecheck/build clean. Merged to `master`.
- **[#78](https://github.com/LLLin000/PaperForge/issues/78) implemented**: real Library/OCR/Memory capability probes with module-detail-navigation, installation-navigation, and capability-state views. Python owns capability facts; TypeScript exact allowlist/fail-closed rendering. Verification: 58 backend + 171 plugin tests; typecheck/build clean; Obsidian smoke verified.
- **[#79](https://github.com/LLLin000/PaperForge/issues/79) implemented**: SecretStorage for capability secrets. Backend-focused gate passes; plugin full suite passes; typecheck/build clean.
- **[#80](https://github.com/LLLin000/PaperForge/issues/80) implemented**: Maintenance probe with backend-derived actionable-only rows, privacy-safe local issue drafts, and accessible destructive confirmation. Backend owns exact actions from `probe maintenance --json`; frontend renders via derived VerbModel with primary null for quality-ok items. Verification: backend focused gate 77/77; plugin full suite 381/382 (pre-existing capability-state test expecting help.stale but receiving help.invalid_response); typecheck/build clean; production bundle 264.4KB; Obsidian 1.12.7 smoke 730/768: entry focus, actionable-only rows, keyboard Enter, accessible destructive confirmation with exact backend effect, focus trap/restoration, owned inert cleanup, redacted editable issue draft, no token input/auto-open, explicit GitHub open only, URL re-redaction, no horizontal overflow.
- **Literature-hub deployment recovered, then safely rolled back**: duplicate plugin discovery and plaintext credentials remain fixed. The active pointer now targets the probe-capable `v1.5.15` slot because the published `1.5.15` installed into `v1.5.15_build2` lacks `paperforge probe`; do not update/repair until a probe-capable package is published and clean-venv verified.

## Verification status

- Focused Python OCR paths: **99 passed, 1 Windows SIGINT test skipped, 1 unrelated empty-result regression deselected**.
- Plugin: **384/384 passed**; TypeScript check and production build passed (**259.3KB**).
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
- Live rollback verification: active Runtime is `windows-x64\\v1.5.15\\venv\\Scripts\\python.exe`; Installation and Help are ready, Library/OCR/Memory return real probe envelopes, Maintenance returns three backend-derived items, and Obsidian captured no errors.
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
- [x] Implement Release N+1 owner cutover ([#81](https://github.com/LLLin000/PaperForge/issues/81)) and Release N+2 cutover ([#82](https://github.com/LLLin000/PaperForge/issues/82)).
- [x] Grill and domain-model the replacement control-center UX; write `DESIGN.md`, glossary, ADR, full screen specification, acceptance matrix, and dependency-ordered slices.
- [ ] Publish a backend package containing `paperforge probe`; remove the Literature-hub editable runtime only after package-level verification.
- [ ] Route `control-center-ux-redesign.md` through Ask Matt into one parent PRD and agent-ready issues; begin with the capability presentation contract after the package release.

## Deferred

- Vector rebuild UX and Memory/global maintenance naming are superseded by the approved Smart Retrieval and user-problem-only Maintenance design; implementation remains pending in the new slices.
- OCR ETA and real-time per-row mutation: out of scope for the completed OCR slice.
- Compatibility naming cleanup remains deferred post-release.
