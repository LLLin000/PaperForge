# OCR-v2 Active Queue
> Status: `EXECUTABLE_FROZEN a42f8bb7` / `PROTOCOL_DOCS 781910f3` — S1–S6 lightweight **COMPLETE** on `462398cb` (valid for `a42f8bb7`, `ruff` clean). Hosted CI `32353318123` on docs-only descendant `a2e18fa4` is **green: All Checks Passed, 14/14**, with `3.11` Ubuntu/macOS/Windows, J-Matrix, Ruff, plugin, OCR, E2E; no executable change after `a42f8bb7`. #191 FROZEN / ready-for-agent; #81 OPEN / owner gate. Reconcile recovery/fulltext safety follow-up is closed on disposable fixtures; P authority acceptance is transaction-safe and bound to the exact human-reviewed plan hash; the 969-paper unverified-content census is clean; semantic coverage and all production writes remain owner-gated.
> Last updated: 2026-09-05
> Ticket 05 corrective round 2 is complete: noop settlement truth (`paper_settled`/counters), fail-closed memory dispatch entrypoint, and client-only Stop ownership verified. Next: owner review to formally close 05, then Ticket 06 (Library & Render Quality cutover).


## 2026-09-03: Ticket 04 OCR Workspace & Processing Domain Cutover — corrective closure

- **Initial cutover:** paper rows use `probe("lineage")` plus typed `queryOcrPapers()`; Run OCR, user-facing Redo, and Rebuild Derived use descriptor-gated canonical actions; Stop uses the client-owned cancellation handle.
- **Review corrections:** `ActionExecutionHooks` now pass stop/progress/item-result callbacks into real OCR and rebuild workers; the Workspace consumes wire `event.phase`, fails closed without a shared client, clears dynamic descriptors on read refresh, and sends OCR keys as separate CLI arguments.
- **Verification:** real CLI tests cover rebuild event ordering and worker-safe-point cancellation (`PAPERFORGE_STOP`, `rc=130`); **103 passed, 1 skipped** focused Python tests; **63 plugin tests passed**; `npm run typecheck` clean. No OCR/render materialization ran.
## 2026-09-03: Ticket 05 Knowledge & Retrieval Domain Cutover

- **Vocabulary:** Python and TypeScript agree on the 10 frozen #137 stream events (`start`, `preflight`, `phase`, `progress`, `paper_settled`, `heartbeat`, `item_result`, `result`, `error`, `cancelled`).
- **Worker streaming:** `ActionExecutionHooks` passes `stop_check`, `on_progress`, and `on_item_result` directly into `run_embedding_build`; silent service mode eliminates stdout capture and legacy `EMBED_PROGRESS:` tokens; single token owner.
- **Pre-publish safe point:** `run_embedding_build` checks `_is_stopped()` after verification before irreversible `_shadow.publish()`.
- **Search & Retrieval:** `dashboard.ts` cuts over `executeSearch()` to `client.search(query, options)` and `client.retrieve(query, options)` with unwrap normalization; `--no-expand` added to CLI for wire parity.
- **Smart Retrieval:** `settings.ts` memory/embed build dispatches route through `client.runAction()`, streaming progress, strictly failing closed on cross-domain action IDs, and wiring Stop only when `client.isOperationActive()`.
- **Verification:** **107 passed, 1 skipped** focused Python tests; **448 plugin tests passed**; `npm run typecheck` clean. No production write ran.

### 2026-09-05: Ticket 05 corrective round 2

- **Noop settlement truth:** `paper_settled(key, status)` moved from `_on_progress` to `_on_item_result`; noop/skip branches increment `processed_count`/`papers_skipped`; un-mocked real-service CLI test asserts clean NDJSON with `progress.current==1`, single `paper_settled outcome=noop`, single `item_result status=noop`, `papers_skipped==1`.
- **Fail-closed entrypoint:** `_runAllowedDispatch("memory")` unknown action IDs no longer substitute `memory.build` — Notice + re-probe; typed `satisfies ActionPrimary` regression added.
- **Stop ownership:** `_renderMemoryDetail` Stop renders only when `client.isOperationActive()`; legacy `embedController.busy/stop` fallback and tests pinning execFile memory-build dispatch deleted.
- **Verification:** Python focused **169 passed**; plugin **446/446**; `tsc --noEmit` clean; ruff clean on changed files.

## 2026-09-02: Reconcile Core Frozen & Backend Contract Mapping Established

- **Reconcile Core Frozen:** Core mutation engine (Audit → Staging → R/P/Blocked → CAS/Journal/Rollback → Commit) is frozen under `docs/RECONCILE-EXTENSION-CONTRACT.md`. No new heuristic detectors or mutation logic will be added to Reconcile. Future detectors operate strictly as read-only finding producers conforming to the minimal finding schema.
- **Backend Contract Blueprint:** Established `docs/BACKEND-FRONTEND-CONTRACT-MAPPING.md` defining Python Backend Authority as SSOT across 5 contracts (Observation, Deficit, Policy, Operation, Authority-Write) and 6 product projection domains (Foundation, Library, Processing, Knowledge/Retrieval, Maintenance, Render Quality).
- **Next Lane:** Transition to Backend Surface Rationalization & Frontend Thin-Client Mapping (`PaperForgeClient`).

## 2026-09-02: Stale render-consistency report invalidation

- **Fail-closed boundary:** `write_render_outputs` validates the automatic audit result and, on an exception or non-object result, atomically replaces any prior `render.consistency.json` with a structured `state=FAILED` execution-failure report. If replacement itself fails, it attempts to remove the old report.
- **Projection:** lineage therefore exposes `FAILED` (or `NOT_RUN` after best-effort cleanup) after a new render's automatic audit failure; it never projects the prior `CLEAN`/`DEGRADED` status as current.
- **Verification:** focused reconcile suite **132 passed, 2 skipped, 1 warning**; `render_audit.py` targeted Ruff, both changed Python modules `py_compile`, and `git diff --check` passed. No production mutation.

## 2026-09-02: P authority acceptance hardening

- **Authority action:** `accept-proposal` now shares the paper-scoped writer lock with R, requires the exact SHA-256 of the human-reviewed `final-plan.json`, a nonempty lowercase 16-hex live snapshot, exact staged paths, and the plan's exact `member_refs`; it never selects a same-label plan by mtime.
- **Atomic production boundary:** one schema-v2 journal covers the canonical JPG, Markdown, `figure_inventory.json`, materialization provenance, and proposal report. Each target uses atomic replacement; failed post-audit restores all snapshots before commit; a committed journal keeps production authoritative through cleanup/report-refresh failure and remains recoverable.
- **Verification:** **5 new review-token regression tests passed; focused reconcile suite 126 passed, 2 skipped, 1 warning**. The two symlink tests remain skipped on Windows `WinError 1314` due missing privilege. No production mutation or front OCR/render change.

## 2026-09-02: Exact human-reviewed plan binding

- **Review token:** `render reconcile --json` exposes `p_details[].final_plan_hash`, computed from the exact staged `final-plan.json` bytes. `accept-proposal KEY LABEL --plan-hash HASH` scans all safe matching staging candidates by that hash; no match returns `STALE_REVIEWED_PLAN`.
- **Deterministic duplicates:** identical plan bytes use a stable path tie-break; live snapshot, destination CAS, journal, rollback, and post-audit gates remain unchanged.

## 2026-09-01: Recovery and fulltext safety follow-up

- **R journal recovery:** schema version 2 is required; transaction paths must be exactly `.paperforge-r-promotion/<32-hex-id>`, destinations are limited to `assets/figures/*.jpg`, `render/figures/*.md`, and `render/materialization.provenance.json`, and backups must be integer `.bak` files inside that transaction directory. Symlinked roots/entries are rejected.
- **Fulltext authority:** missing, unreadable, or malformed canonical inventories produce `F0_CANONICAL_AUTHORITY_UNAVAILABLE`, set `mutation_blocked`, and emit no patches, including orphan/reserved embed candidates.
- **Committed reporting:** a post-commit report refresh failure is explicit (`ok=true`, `committed=true`, `report_refresh=failed`) and never triggers rollback of committed artifacts.
- **Verification:** focused reconcile suite **114 passed, 1 warning**; Ruff `E,F,I,UP` and `py_compile` clean. No production mutation or front OCR/render change.

## 2026-09-01: Committed cleanup hardening and R-content census

- **Committed journal recovery:** after `state=committed`, production remains authoritative; recovery no longer requires backup files, cleanup is best-effort, and the journal is removed without rollback. A cleanup `OSError` on the original committed call returns `committed=true, cleanup=pending` with `cleanup_error`; the journal remains for the next recovery.
- **Raw path safety:** destination and backup checks inspect raw path components before `.resolve()`; symlinked production, transaction, and backup paths fail closed.
- **Final audit semantics:** report-write success is `report_refresh=written`; a returned audit `state=FAILED` is separately exposed as `report_audit_state=FAILED`; exceptions/non-object results remain `report_refresh=failed`.
- **Read-only census:** `D:\L\OB\Literature-hub\System\PaperForge\ocr` scanned **969** paper directories with `write_report=False`: **0 affected papers, 0 affected objects, 0 audit failures**. No production mutation.
- **Verification:** focused reconcile suite **116 passed, 2 skipped, 1 warning**; symlink tests skipped on Windows `WinError 1314` due missing privilege. Ruff, `py_compile`, and `git diff --check` passed.

## 2026-08-31: D1 status sync

- **R:** duplicate canonical IDs, cross-canonical asset claims, duplicate provenance paths, malformed provenance/journal states, and unsafe object IDs are detected and blocked; selected exact R plans stage in isolation; manifest v2, plan hash, destination CAS, journaled rollback/recovery, post-audit checks, and explicit promotion scope are implemented.
- **Canary:** disposable evidence remains PASS: 12 objects tested, 11 successful promotions, 1 expected page-range/materialization failure, and 11 second-promote no-ops. Fresh isolated `2ZBAK9VY/figure_003` fails only its own staged-source gates. No production write has run.
- **R production blockers:** implementation P0-A/P0-B gates are closed and focused-covered. Production rollout remains owner-blocked; semantic figure-coverage defects are still report-only.
- **R detection boundary:** report and dry-run expose `R_CONTENT_UNVERIFIED` for existing artifacts without authoritative output hashes and block provenance mismatch/ambiguity; they do not prove semantic coverage loss such as a panel absorbed by `table_html`. No automatic merge or overwrite.
- **P/fulltext:** bounded-slot anchors now derive from unique, non-conflicted `main` rows; missing-page candidates block safely. Fulltext duplicate canonical IDs and unavailable fulltext block all patches. No production mutation.


## 2026-08-26: Reconcile-only R promoter

- Reconcile remains independent from the stable OCR/front-render pipeline; no `ocr_figures.py`, `ocr_objects.py`, `ocr.py`, or `ocr_rebuild.py` changes.
- Read-only census: 965 papers scanned; 182 papers contain 250 duplicate canonical figure-ID groups (224 conflicting, 26 identical).
- Audit/reconcile now blocks ambiguous IDs and R staging passes only selected exact plans.
- Added `paperforge render promote-r KEY [OBJECT_ID...] --json`; mutation scope is explicit (`OBJECT_ID` or `--all`). It consumes a verified `r-manifest.json`, checks live snapshot, canonical uniqueness, cross-object `(page, block_id, bbox)` claims, destination CAS, staged image/markdown facts, markdown link, and staging provenance before journaled atomic promotion. Production inventory is not rewritten.
- Verification: focused promoter + reconcile/audit/lineage/CLI/docs suite **114 passed, 1 warning**; targeted Ruff `E,F,I,UP` clean. Post-audit rollback, four hard-kill recovery points, paper writer lock, and cross-object claims passed. A 12-object disposable set produced **11 successful promotions + 1 expected page-range failure**; all 11 second promotes were no-ops.
- Next gate: explicit owner authorization only. No production batch rollout. Evidence: `project/current/render-reconciliation/r-canary-results.json`.

## 2026-08-20: S1–S6 lightweight certification (EXECUTABLE_FROZEN 462398cb → a42f8bb7)
- **S1 PASS:** `setup --modular` → `probe installation ready`, `status` 0 papers, `doctor` only Zotero/BBT optional fails. #191 gap: still deploys `.agents/skills` and retains `skill_dir/command_dir/agent_platform`.
- **S2 PASS:** `status` 2 papers, `probe` ready, `runtime-health`, `paper-status`/`read`/`search` succeed after `memory build`, `retrieve --paper` scoped, `reconcile`/`sync --dry-run` honest. No failure due to `.obsidian`/plugin cache.
- **S4 PASS:** `action list`, `reconcile`, `prune` dry-run, `action preflight`, `UNKNOWNKEY` → `PATH_NOT_FOUND`, `config validate` valid→corrupt→valid. No fabricated `healthy`.
- **S5 PASS:** `action run ocr.run` without `--confirm` → `confirmation_required` rc3; with `--confirm` → ok; `action run --force` → `unrecognized arguments`; `prune --force` safe. Boundary enforced.
- **S3 PASS:** `setup → memory build → search → read → retrieve --paper → embed status/preflight` chain without Obsidian; `embed.build --confirm` → explicit `401 invalid_api_key` (fail-closed, expected without valid key). Restart re-`read` persists.
- **S6 PASS (partial):** `config corrupt` → `config.corrupt` fail-closed; restore → `valid` + `setup` repeat idempotent + `probe ready` + `read` persists. Remaining S6 sub-paths (stale/malformed pointer, offline, OCR resume, Release-N reinstall) remain owner gate.
- Triage: **No RC blocker** in lightweight gates. #191 real gaps: skill deploy in SetupPlan, retired config fields, missing `setup inspect/plan/apply/verify` + `plan_stale` + verified-switch `relocate` + `external_action/secure_external`. Performance remains debt. Matrix: `project/current/cert-462398cb-S1-S6-matrix.md`. Correct language: **S1–S6 lightweight certification complete; S6 partial / owner gates remain** (not `S1–S6 PASS`).
- Next: **Do not build `462398cb+46c4ddaf+b66fde53` candidate.** `EXECUTABLE_FROZEN a42f8bb7` is the dead-code release-hygiene fix on top of `462398cb` (`3312/0` local + hosted tree green). Remaining **RC Owner Closure**: 1) Managed Runtime / Plugin browser (stale/non-ready/restart/fail-closed/cache), 2) M2/M3 live process (mixed outcomes/cancellation/Ctrl+C/scoped embed), 3) S6 full recovery (malformed/stale pointer/offline/interrupted update/OCR resume/embed resume), 4) Release-N reinstall + support-window owner decision. Hosted CI run `32353318123` is green on docs-only descendant `a2e18fa4` (no executable change after `a42f8bb7`); no new code candidate needed. Keep `#191` FROZEN. Research `Source Routing` / `Visual Evidence` deferred post-RC.

## 2026-08-18: Census closure and remaining RC gates

- Frozen recovery scope `R=958`; current formal/live-export scope `F=964`:
  seven normal Authority additions and one confirmed residual removal.
- Current production state is frozen as **964 Authority = 944
  OCR/retrieval current + 19 `nopdf` terminal + 1 `pdf_missing`**.
- Vector state is **933 current + 3 `no_content` terminal + 8
  `not_embedded` actionable**. No retrieval-current paper is stale/unknown and
  no `memory.build` candidate exists.
- The eight vector deficits are the exact scoped `embed.resume` evidence set:
  owner-approved preflight → explicit confirmation → settlement → fresh probe.
  No production mutation was run.
- `R2PSFXY4` is a sync-confirmed residual outside Authority. Reader-gate
  exclusion is contract-proven; targeted live serving evidence remains open.
  Do not prune solely for census presentation.
- Next: complete the scoped embed gate, residual serving smoke, exact-candidate
  frontend/hosted evidence, and rollback/support-window owner decision. No
  release/tag/package publication.

## 2026-08-18: Sync latency diagnosis

- Full `sync --json` latency was dominated by full reconcile, not the
  unchanged-index path: per-paper lineage lookup reparsed the canonical
  `formal-library.json`.
- Working-tree fix builds one canonical-PDF map per lineage observation.
  Production read-only reconcile measured **144.61 s → 48.38 s**; no
  re-OCR, rebuild, embed, prune, or production sync rerun was performed.
- Disposable sync plus lineage/reconcile regressions: **167 passed, 1
  warning**.

## 2026-08-17: M4 blocker checkpoint

- Frozen candidate `6ef0dfe9` reported retrieval `current` over a corrupt
  published carrier after a body-unit mutation; repair commit `46c4ddaf` maps
  this to retrieval/vector `stale` and `memory.build`.
- Preflight and reconcile disagreed on the canonical per-paper first frontier;
  repair commit `46c4ddaf` makes preflight project reconcile's intent.
- Focused regression gate: **126 passed, 1 warning** across lineage, reconcile,
  embedding eligibility, and action registry.
- No re-OCR/rebuild/embed is required for valid existing materializations.
  Corrupt retrieval carriers require `memory.build`; embed follows only after
  retrieval becomes eligible.
- The census divergence is now closed separately; repaired code remains outside
  the frozen candidate and follows the normal candidate/dependent-gate path.

## 2026-08-13: RC audit checkpoint

- Wayfinder #135 and final authority cutover #174 are complete, owner-accepted, and closed.
- Real Obsidian exercised setup/config, Python-owned credentials, sync/reconcile, OCR run/rebuild/redo/cancel, embed confirmation/build/cancel/retry, memory automatic actions, runtime recovery, navigation, and restart persistence.
- All 9 observed defects are repaired: stale credential truth, 30s probe timeout, missing credential remediation, hidden/incorrect cancellation state, stale embed failure/corruption projection, registry-policy drift, dashboard reopen/setup dead ends, raw i18n keys, and OCR NDJSON stdout/scope faults.
- Audit evidence is in the disposable vault at `System/PaperForge/audits/ui-e2e-findings.json` and `operation-timing.json`; source vault data was not mutated.
- Only #81 remains on the release path, but the frozen candidate is currently
  blocked by the M4 findings above. Owner-controlled version sync, candidate
  promotion, PyPI/GitHub release, and plugin manifest publication resume only
  after the repaired candidate passes the dependent gates.

## Current checkpoint

- Retrieval recovery is merged to `master`; the real Literature-hub vault has a healthy 2560-dimensional vec0 index and working M / @ search paths.
- [OCR rebuild: streaming progress + maintenance UI redesign](https://github.com/LLLin000/PaperForge/issues/64) is implemented, reviewed, verified, and closed.
- Multi-key `ocr rebuild` and full `ocr redo` emit separate, flushed progress streams and accept a cross-platform cooperative stop request between papers.
- The maintenance tab now exposes all papers plus the canonical `_needs_derived_rebuild()` recommendation set, selected batch actions, an above-table progress state, and full refresh on completion.
- Per-row maintenance actions now route through `maintenanceActionForRow()` — rebuild/redo follow the canonical backend `display_action` rather than raw booleans.
- Destructive `redo` requires user confirmation via `maintenanceActionRequiresConfirmation()`.
- Cache refresh preserves the backend manifest (was overwriting it with empty on each refresh).
- Source Corpus data remains authoritative and was not modified during verification. Only the deployed plugin bundle and disposable maintenance cache were refreshed.
- [Current-contract audit](https://github.com/LLLin000/PaperForge/issues/66#issuecomment-4968837257) identified the migration boundary: preserve durable OCR/SQLite truth and recovery actions; replace global setup state, duplicate runtime/config resolution, and freshness-free snapshots.
- The approved `control-center-ux-redesign.md` is implemented: five operational modules, three top-level destinations, contextual Module Detail, progressive setup, user-problem-only Maintenance, and Obsidian-native presentation.
- `paperforge/plugin/DESIGN.md` and `paperforge/plugin/CONTEXT.md` now govern the production surface.
- Ticket 04 OCR Workspace & Processing Domain Cutover is complete after corrective closure: its read/action/progress/cancellation paths use `PaperForgeClient`, real worker events are streamed, missing-client fallback is removed, and dynamic descriptors refresh with the read model.
- **[#83–#93](https://github.com/LLLin000/PaperForge/issues/83) implemented**: schema-v2 presentation, shared primitives, five-card Overview, four-stage Setup Journey, Library/OCR/Smart Retrieval/Agent details, Maintenance/Help, and cutover cleanup are merged to `master`.
- **[#69](https://github.com/LLLin000/PaperForge/issues/69) resolved** at `issuecomment-4971161072`: orthogonal availability/activity/attention axes, 6-state capability ordinal, 12 canonical verbs, backend-owned severity and primary actions, maintenance projection.
- **[#70](https://github.com/LLLin000/PaperForge/issues/70) resolved** at `issuecomment-4971239398`: plugin-managed immutable runtime slots, system-Python bootstrap with validated-triplet fallback, single `active-runtime.json` pointer, `ManagedRuntime` class with `current()`/`status()`/`ensure()`, fail-closed command resolution.

- **[#71](https://github.com/LLLin000/PaperForge/issues/71) resolved**: six-module control-center HTML prototype with 5 scenarios, plain-button switcher, primary attention zone, responsive layout (768px breakpoint), and capability-gated actions. Independent Critical/Important PASS review. Design decisions recorded in `docs/prototypes/2026-07-14-six-module-control-center.{html,md}`.
- **[#72](https://github.com/LLLin000/PaperForge/issues/72) resolved**: actionable-only maintenance inbox prototype with single-action rows, inline issue-draft review, local redacted export, and confirmation-first report flow. Independent Critical/Important PASS review. Design decisions recorded in `docs/prototypes/2026-07-14-maintenance-issue-reporting.{html,md}`.
- **[#73](https://github.com/LLLin000/PaperForge/issues/73) resolved**: locked migration, security, platform, accessibility, and release-gate acceptance contract after five-domain audit and independent review.
- **[#74](https://github.com/LLLin000/PaperForge/issues/74) closed as superseded**: completed #75–#80 remain the control-plane baseline; the product model and remaining work moved to #83.
- **[#75](https://github.com/LLLin000/PaperForge/issues/75) implemented and reviewed**: bare/headless/modular setup share `SetupPlan`; schema-v2 `vault_config` wins; v1 path keys are warned read fallback; all configured directories are forwarded; required failures return non-zero.
- **[#76](https://github.com/LLLin000/PaperForge/issues/76) implemented**: schema-v1 Installation/Help probes flow through the six-module Overview; persisted malformed/stale envelopes fail closed; backend set_config/update actions route to setup.
- **Current navigation is cut over**: Overview / Maintenance / Help are the only top-level destinations; Foundation, Library, OCR, Smart Retrieval, and Agent Integration open as contextual Module Details.
- **[#77](https://github.com/LLLin000/PaperForge/issues/77) implemented**: Managed Runtime lifecycle with immutable slots, synchronous fail-closed `current`, probed `status`, install/repair/update/rollback/cancel/retention, managed-first dispatch, Release-N fallback, four-destination navigation shell. Verification: 192 focused + 289 full tests; typecheck/build clean. Merged to `master`.
- **[#78](https://github.com/LLLin000/PaperForge/issues/78) implemented**: real Library/OCR/Memory capability probes with module-detail-navigation, installation-navigation, and capability-state views. Python owns capability facts; TypeScript exact allowlist/fail-closed rendering. Verification: 58 backend + 171 plugin tests; typecheck/build clean; Obsidian smoke verified.
- **[#79](https://github.com/LLLin000/PaperForge/issues/79) implemented**: SecretStorage for capability secrets. Backend-focused gate passes; plugin full suite passes; typecheck/build clean.
- **[#80](https://github.com/LLLin000/PaperForge/issues/80) implemented**: Maintenance probe with backend-derived actionable-only rows, privacy-safe local issue drafts, and accessible destructive confirmation. Backend owns exact actions from `probe maintenance --json`; frontend renders via derived VerbModel with primary null for quality-ok items. Verification: backend focused gate 77/77; plugin full suite 381/382 (pre-existing capability-state test expecting help.stale but receiving help.invalid_response); typecheck/build clean; production bundle 264.4KB; Obsidian 1.12.7 smoke 730/768: entry focus, actionable-only rows, keyboard Enter, accessible destructive confirmation with exact backend effect, focus trap/restoration, owned inert cleanup, redacted editable issue draft, no token input/auto-open, explicit GitHub open only, URL re-redaction, no horizontal overflow.
- **Literature-hub deployment recovered, then safely rolled back**: duplicate plugin discovery and plaintext credentials remain fixed. The active pointer now targets the probe-capable `v1.5.15` slot because the published `1.5.15` installed into `v1.5.15_build2` lacks `paperforge probe`; do not update/repair until a probe-capable package is published and clean-venv verified.

- **Test-vault UI repair deployed:** OCR Workspace now loads the 593-paper formal index through `ResolvedPaths`, opens as a main tab rather than a right sidebar, hides idle activity, localizes the live Chinese Control Center/Smart Retrieval labels, and uses an accent primary action despite Obsidian core button styling.
- **Setup Journey boundary repair deployed:** Foundation exposes the Python executable and installs/verifies only the PaperForge package; Stage 2 alone presents the editable Zotero plus four vault paths and runs modular setup to save and verify them. Reinstall remains in-flow and no longer opens the legacy wizard.
- **Optional setup configuration deployed:** selected Stage 3 OCR, Smart Retrieval, and Agent cards expand their credential/model/base-URL/platform fields. Credentials are saved through Obsidian SecretStorage, not plugin settings.
- **Smart Retrieval live rebuild repaired:** test-vault `构建索引` now rebuilds the 593-paper vec0 index to `memory.ready`. The unified detail has one configuration disclosure for API key, Base URL, and model; terminal failures display their final stderr diagnostic; a ready index has no stale warning panel.
## Verification status

- Focused Python OCR paths: **99 passed, 1 Windows SIGINT test skipped, 1 unrelated empty-result regression deselected**.
- Plugin: **414/414 passed**; TypeScript check and production build passed (**303.7KB**).
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
- Control Center live acceptance: Obsidian 1.12.7 exercised Overview, all five Module Details, Maintenance, Help, and all four Setup Journey stages in English and Chinese; no untranslated keys or horizontal overflow. Corrected bundle deployed to Literature-hub.
- Live Setup Journey verification: Foundation auto-refreshed to ready; Library Stage 2 rendered five editable fields with no raw i18n keys. An invalid Zotero path failed validation and disabled Continue; restoring the path re-enabled it.
- Live Foundation-run verification: completed with no legacy modal and no Library stage transition; `D:\L\Med\test\paperforge.json` retained SHA-256 `856d89520a766e927dbae7e00880b912cfbf89a3747fa0f109329dc864f5a36c`.
- Live optional-stage verification: all three selected cards rendered in the in-flow setup with two SecretStorage password fields, four total configuration inputs, one Agent platform selector, enabled Continue, vertical page scroll, and no raw i18n keys.
- Production plugin code was modified only for the deployed test-vault UX repairs; prototype-only records above remain historical.
- The repository-wide Python suite remains blocked during collection by two pre-existing removed-symbol imports: `test_pr9a_resume_rebuild.py` imports `_assert_collections_healthy`, and `test_layer4_vector_backend.py` imports `get_vector_backend`.
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
- [x] Complete and verify Release N+1 implementation code ([#81](https://github.com/LLLin000/PaperForge/issues/81)); keep the issue open for the owner-controlled release gate.
- [ ] Complete Release N+2 deletion ([#82](https://github.com/LLLin000/PaperForge/issues/82)) only after an N+1 package and support window.
- [x] Implement replacement PRD [#83](https://github.com/LLLin000/PaperForge/issues/83) and dependency-ordered issues #84–#93.
- [x] Browser-audit every English and Chinese Control Center page and deploy the corrected bundle to Literature-hub.
- [x] Cut OCR Workspace and processing interactions over to `PaperForgeClient` (Ticket 04), including real worker-backed progress/item-result events, cooperative cancellation, phase-field consumption, fail-closed client ownership, multi-key argv, and descriptor refresh.
- [x] Cut Knowledge & Retrieval interactions over to `PaperForgeClient` (Ticket 05), including frozen #137 vocabulary, worker-backed embed progress streaming, single cancellation token, dashboard search/retrieve normalization, and Smart Retrieval action dispatch.

## Deferred

- Vector rebuild UX and Memory/global maintenance naming are superseded by the approved Smart Retrieval and user-problem-only Maintenance design; implementation remains pending in the new slices.
- OCR ETA and real-time per-row mutation: out of scope for the completed OCR slice.
- Compatibility naming cleanup remains deferred post-release.


## 2026-07-27: #112 — Agent Skill retrieval contract sync

- [x] Rewrite `atoms/retrieval-routing.md` as 5-part canonical protocol (intent determination, planner protocol, safe executor, one-fallback rule, evidence interpretation + session state)
- [x] Update `SKILL.md`: version bump `2026-07-27.1`, remove `rg`/`semantic` from pre-flight, replace `known-paper` intent with `locate`, remove "vector status gates retrieval routing" from runtime-health
- [x] Rewrite `molecules/discover-papers.md`: delete multi-arm search, use plan→primary→fallback, delete top-10 paper-context enrichment
- [x] Rewrite `molecules/find-supporting-evidence.md`: delete `rg`/`grep` ladder, use structure coordinates for evidence, scope-paper safety rules
- [x] Rewrite `molecules/read-known-paper.md`: two-phase (locate → Q&A), session cache, question-type routing, no default fulltext load
- [x] Rewrite `molecules/deep-analyze-paper.md`: Step 0 uses `--structure`, StructureTree as navigation map, no hardcoded section titles
- [x] Sync `docs/ARCHITECTURE.md`, `docs/COMMANDS.md`, `docs/help/en/guide.md`, `docs/help/zh/guide.md`
- [x] Mark issues #106–#110 closed