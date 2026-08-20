# OCR-v2 Active Queue
> Status: `EXECUTABLE_FROZEN a42f8bb7` (fix `AGENT_SKILL_DIRS` F821, `462398cb` → `a42f8bb7`) / `PROTOCOL_DOCS 781910f3` — S1–S6 lightweight **COMPLETE** on `462398cb` (now valid for `a42f8bb7`, `ruff` clean). #191 FROZEN / ready-for-agent; #81 OPEN / owner gate. Local `a42f8bb7` `68` setup tests passed, `ruff` clean; hosted `a42f8bb7` pending `3.11+newer`.
> Last updated: 2026-08-20

## 2026-08-20: S1–S6 lightweight certification (EXECUTABLE_FROZEN 462398cb → a42f8bb7)

- S1–S6 executed S1→S2→S4→S5→S3→S6 on disposable minimal fixtures: `pf-cert-s1-vault` + `pf-cert-s2-minimal` (2-paper). Worktree `.cert-462398cb` (462398cb) now fixed in `a42f8bb7` (415 deletions, no re-OCR). `462398cb` hosted `32269242351` failed `L0.5 — Ruff F821 AGENT_SKILL_DIRS`; `a42f8bb7` is `ruff --select F821,F822,F823` clean.
- **S1 PASS:** `setup --modular` → `probe installation ready`, `status` 0 papers, `doctor` only Zotero/BBT optional fails. #191 gap: still deploys `.agents/skills` and retains `skill_dir/command_dir/agent_platform`.
- **S2 PASS:** `status` 2 papers, `probe` ready, `runtime-health`, `paper-status`/`read`/`search` succeed after `memory build`, `retrieve --paper` scoped, `reconcile`/`sync --dry-run` honest. No failure due to `.obsidian`/plugin cache.
- **S4 PASS:** `action list`, `reconcile`, `prune` dry-run, `action preflight`, `UNKNOWNKEY` → `PATH_NOT_FOUND`, `config validate` valid→corrupt→valid. No fabricated `healthy`.
- **S5 PASS:** `action run ocr.run` without `--confirm` → `confirmation_required` rc3; with `--confirm` → ok; `action run --force` → `unrecognized arguments`; `prune --force` safe. Boundary enforced.
- **S3 PASS:** `setup → memory build → search → read → retrieve --paper → embed status/preflight` chain without Obsidian; `embed.build --confirm` → explicit `401 invalid_api_key` (fail-closed, expected without valid key). Restart re-`read` persists.
- **S6 PASS (partial):** `config corrupt` → `config.corrupt` fail-closed; restore → `valid` + `setup` repeat idempotent + `probe ready` + `read` persists. Remaining S6 sub-paths (stale/malformed pointer, offline, OCR resume, Release-N reinstall) remain owner gate.
- Triage: **No RC blocker** in lightweight gates. #191 real gaps: skill deploy in SetupPlan, retired config fields, missing `setup inspect/plan/apply/verify` + `plan_stale` + verified-switch `relocate` + `external_action/secure_external`. Performance remains debt. Matrix: `project/current/cert-462398cb-S1-S6-matrix.md`. Correct language: **S1–S6 lightweight certification complete; S6 partial / owner gates remain** (not `S1–S6 PASS`).
- Next: **Do not build `462398cb+46c4ddaf+b66fde53` candidate.** `EXECUTABLE_FROZEN 462398cb` is already the candidate (`3312/0` local green). Remaining **RC Owner Closure** on exact `462398cb`: 1) Managed Runtime / Plugin browser (stale/non-ready/restart/fail-closed/cache), 2) M2/M3 live process (mixed outcomes/cancellation/Ctrl+C/scoped embed), 3) S6 full recovery (malformed/stale pointer/offline/interrupted update/OCR resume/embed resume), 4) Release-N reinstall + support-window owner decision, 5) exact-SHA hosted CI (provide Actions run / job evidence; `local green / hosted pending`). Keep `#191` FROZEN. Research `Source Routing` / `Visual Evidence` deferred post-RC.

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