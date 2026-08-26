> **Branch:** `master` | **Last Updated:** 2026-08-26
>
> **Active work:** Reconcile-only R promotion is implemented behind verified staging gates. It remains isolated from the preceding OCR/render pipeline: no `ocr_figures.py`, `ocr_objects.py`, `ocr.py`, or `ocr_rebuild.py` behavior changed. The next gate is crash-injection/recovery plus stratified R canaries; no full-corpus promotion is authorized.
>
> ---
>
> **Current state:** The front OCR/render pipeline remains unchanged. The independent reconcile layer now performs inventory identity diagnostics, excludes ambiguous IDs from R/P planning, and filters R staging to selected repair plans only. No production materialization or canonical inventory mutation was performed.

### 1.1 The problem (pre-v2)


```
raw_label/text → final role → normalize → rescue → demote/promote → attach → render
```

Early role guesses caused: title/author/footnote misclassification, body paragraphs typed as references, reference continuations leaking into body, left/right column interleave bugs, duplicate figure captions.

### 1.2 The solution (v2 target)

```
raw observations → structural signatures → stable anchors/families → zone inference → role resolution → figure/table validation → render + health
```

### 1.3 Core principles

1. **seed_role is a proposal, never a final role** — `assign_block_role()` proposes; `normalize_document_structure()` decides
2. **VERIFY_REQUIRED** roles (paper_title, authors, section_heading, reference_item, figure_caption, etc.) must have `role_verification_status == "ACCEPT"` with non-empty `role_source` and `role_evidence`
3. **Zone != Role** — being in the body reading environment does not imply `body_paragraph`
4. **Reference tail first** — reference sections protected from tail contamination
5. **Frontmatter source-backed** — OCR localizes but must not invent/discard canonical frontmatter

**Key design documents:**

- Architecture spec: `docs/superpowers/specs/2026-06-08-ocr-anchor-first-structured-parsing-design.md`
- Implementation plan: `docs/superpowers/plans/2026-06-08-ocr-anchor-first-structured-parsing-plan.md`
- Role gate plan: `docs/superpowers/plans/2026-06-11-ocr-verified-structural-role-gate.md`
- Latest spec realignment: `docs/superpowers/specs/2026-06-13-ocr-real-paper-regression-and-spec-realignment-design.md`

---

## 2. Current Status

### 2.1 Test / Verification Status
</br>
| Suite | Result |
|-------|--------|
| 2026-08-15 safety + residual + UI (post-incident) | **130 py (trash layer, prune DB-cleanup, residual detection, registry) + 35 OCR + 4 update + pre-commit destructive-delete check + 408 vitest + tsc clean** ✅ |
| Architecture Audit Slice A (#131) | **183/183 focused passed (153 slice A + 14 collectors + 14 report/gate + 2); Ruff clean; full suite 2883→2899 passed / 292 skipped (0 failures)** ✅ |
| Architecture Review Skill (#132) | **32/32 evals passed** (process invariants + skill document contracts); Ruff clean ✅ |
| Deterministic collectors (#133) | **14/14 passed** (mixed py/ts seam, real TS compiler, exclusions, TS-unavailable coverage, stable IDs, digest movement, signal pairing, publication bypass, wrapper/contract separation); full-repo run: 212 files / 512 facts / honest statuses ✅ |
| Report + CI gate (#134) | **14/14 passed** (projection layers, status rendering, escaping, copy payload, before/after diff, gate semantics); real-browser smoke (10 sections, filters, 10 copy buttons, focus, no overflow); CI e2e job wired ✅ |
| Full OCR regression suite | **1278 passed, 8 pre-existing failures, 275 skipped** ✅ |
| Reconcile-only identity hardening (2026-08-26) | **82 passed, 1 warning** across render audit, figure reconciliation, lineage, and CLI dispatch; Ruff `E,F,I` clean. Read-only corpus census: **965 scanned, 182 papers / 250 duplicate figure-ID groups, 224 conflicting + 26 identical; 500 affected output paths**. ✅ |
| Reconcile-only R promoter (2026-08-26) | **88 passed, 1 warning** across R promoter, audit, reconciliation, lineage, and CLI dispatch; targeted Ruff `E,F,I,UP` clean. Synthetic success, stale-manifest refusal, duplicate-identity refusal, idempotent second run, mid-batch write-failure rollback, real `promote-r` CLI no-manifest fail-closed, and real duplicate-paper staging manifest smoke passed. No production write executed. ✅ |
| Focused merge suite (v3 + tail settlement + writeback + appendix numbering + rendering) | **105 passed, 0 failed** ✅ |
| Layer 2 quality + feedback tests | **22 passed, 0 failed** ✅ (17 quality + 5 feedback) |
| Control Plane Closure (M1–M3, 2026-08-17) | **147 passed, 7 skipped** across embed eligibility/scoped/resume, action registry, T7 journey, architecture boundaries, shadow rebuild, and integration gates; M3-C architecture exemption allowlist is empty; final M3-E/F gate passed after the last mutation ✅ |
| M4 RC lifecycle + static evidence (2026-08-17) | Product source tree `6ef0dfe9`: modular fresh setup/repeat and existing-vault schema-v2 migration passed; disposable OCR → memory → global embed → retrieve → restart passed; legacy rollback failed closed without materialization hash changes; stale-state suite **113 passed/1 warning**, setup/runtime suite **129 passed**, focused RC suite **216 passed/1 warning**, candidate Python CI jobs passed, destructive-delete guard passed, and candidate plugin `npm test` **408/408** + typecheck/build passed after a successful dependency install. Hosted CI run **#32040776725** at `14899168` passed **14/14**, including macOS unit/J-matrix; the deterministic collector is complete-coverage but ineligible on six unresolved active rules and two advisory wrapper findings under #134's skip policy. Real Release-N reinstall/support-window, managed runtime/UI, cancellation, scoped embed, post-RC architecture review, and owner gates remain pending. ✅/PENDING |
| Full vault corpus diff: legacy vs v3 (555 papers) | **547/555 no diff, 5/555 v3 improvement** ✅ |
| 86-paper pre-merge corpus diff | **86/86 no diff** ✅ |
| 6 fixture-backed v3 parity gates | **6/6 pass** ✅ |
| Focused OCR rebuild/redo/maintenance paths | **99 passed, 1 Windows signal test skipped, 1 unrelated empty-result regression deselected** ✅ |
| Plugin tests + TypeScript + production build | **414/414 passed; typecheck/build clean; production bundle 303.7KB** [OK] |
| RC real-Obsidian workflow audit (2026-08-13) | **9/9 original live findings repaired plus paid-action follow-up:** OCR/embed entry points now route through shared dispatch; Python probe/registry owns confirmation policy; consent-required work remains visible instead of launching from a background modal; each click opens one localized confirmation; controller owns progress/cancel/terminal feedback. Focused Python policy tests pass; plugin **391/391**; typecheck and 345.9KB production build clean; live disposable-vault checks observed OCR confirmation and embed confirmation→401 terminal feedback without hidden execution. ✅ |
| RC functional-coverage audit (2026-08-13) | **Full CLI + plugin surface smoke against the disposable vault:** 33 commands exercised (search/paper-*/context/gateway/agent-context/dashboard/deep-reading/prune/reading-log/project-log/base-refresh/ocr list/pipeline-versions/action list+describe/repair --runtime/update preflight + NDJSON). **2 real-path defects found and fixed** — foundation.update remote version check died with `urllib has no attribute request` (update.py imported only urllib.parse; hidden by unit tests mocking `_remote_version`), and doctor's Agent 脚本 importability check always false-WARNed on @dataclass scripts (`module_from_spec` without `sys.modules` registration). Both verified live; regression 3091 parallel + 44 serial py, 391 vitest, tsc/build clean; commits `b3881605` + `a5ce2f16` pushed. ✅ |
| RC UX Seam Pass (2026-08-13) | **P0**: OCR Workspace `_resolvePython()` used the deleted `mr.current()` — pointer-only installs died at Workspace open; now `readPointer()` + managed-pointer-only tests. **P1**: embed terminal + OCR Workspace rebuild settle now invalidate-all/probe-all so Smart Retrieval reflects fresh truth (durable handoff, not the 8s Notice). Setup Stage 1 gained real Cancel (AbortController through installOnce/handshake/setup; no publish, no completion flip) and Later/exit. Rebuild Stop is disabled+explained (was false affordance). Deleted the unreachable legacy Smart Retrieval settings chain that let TS `pip install chromadb openai` directly (+ orphan helpers, 30 dead i18n keys; bundle 345.9→324.7KB). Foundation detail no longer hardcodes `obsidianOk = true` or execs `import openai` — projects pointer + probe. Verification: 403/403 vitest, tsc/build clean, 33 focused py; live Foundation/OCR/embed surfaces re-checked. |
| RC UX Seam corrective FINAL (2026-08-13) | **P0**: Setup Stage 2 `_runSetupPython` no longer falls back to ambient `python` — resolves the managed pointer, fails closed when missing; Stage 2 setup now uses `--json` (machine stream). **P0**: cooperative-cancellation race closed — agent loop checks `_is_stopped()` between sub-steps and a final pre-`publish_pointer()` gate makes cancelled setup never publish (regression: agent-phase cancel → rc 130, `cancelled` terminal, publish never called). **P0**: plugin waits for the cancelled setup child to actually close before settling UI idle (no Retry race). **P1**: "Later" genuinely reaches Overview via a session-only `_setupJourneyDismissedForSession` flag (reset on `hide()` → reopening resumes Stage 1); test drives the real `display()`. Cancellation copy is now "Setup cancelled. The runtime was not activated." Verification: 3092+44 py / 405 vitest / tsc+build clean; live dismiss-gate check. |
| Live Literature-hub maintenance UI | **734 All / 700 Recommended; no captured errors** ✅ |
| Maintenance regression action model | **19/19 passed** ✅ (per-row canonical action routing, redo confirmation gate, cache manifest preservation) |
| Canonical setup/config migration (#75) | **61 passed, 0 failed** ✅ (fresh/v1/v2 config, CLI routing, path forwarding, failure exit, idempotent rerun) |
| Installation/Help capability tracer (#76) | **21 backend tests + 169 plugin tests passed; typecheck/build clean; independent review PASS** ✅ |
| Managed Runtime lifecycle + navigation (#77) | **192 focused + 289 full passed; typecheck/build clean** ✅ |
| OMP Matt workflow guard | **Fresh OMP auto-discovery confirmed; 7/7 deterministic guard cases passed** ✅ |
| Library/OCR/Memory capability tracers (#78) | **65 backend tests + 178 focused plugin tests, 324 full plugin tests passed across 11 files; typecheck/build clean; backup restore end-to-end** ✅ |
| SecretStorage capability secrets (#79) | **Backend-focused gate, plugin full suite passes; typecheck/build clean** ✅ |
| Maintenance probe — actionable rows, draft, destructive confirmation (#80) | **Backend focused gate 77/77; plugin full suite 381/382** (only pre-existing capability-state test expecting help.stale but receiving help.invalid_response) ✅ **; typecheck/build clean; production bundle 264.4KB; real Obsidian 1.12.7 smoke at 730 and 768 confirmed Maintenance entry focus, actionable-only rows, keyboard Enter, accessible destructive confirmation with exact backend effect, focus trap/restoration, owned inert cleanup, redacted editable issue draft, no token input/auto-open, explicit GitHub open only, URL re-redaction, no horizontal overflow**
| Control Center redesign (#83–#93) | **420/420 plugin tests; typecheck/build clean; every Overview, five Module Detail, Maintenance, Help, and four Setup Journey pages exercised in English and Chinese; no untranslated keys or horizontal overflow; deployed to Literature-hub** ✅ |
| Map #94 target-state prototypes | **4 interactive prototypes exercised at 375/768/1280; no script errors or horizontal overflow; screenshot QA found no confirmed visual defects; Standards/Spec re-review findings repaired and browser-confirmed** ✅ |
| Test-vault live UX repair | **407/407 plugin tests; typecheck/build clean; real Obsidian 1.12.7 smoke against `D:\L\Med\test`** — Control Center, Smart Retrieval detail, and OCR Workspace exercised. 593 papers load; idle activity is hidden; workspace opens in a 960px main tab; no raw localization keys; primary CTA computes to accent `rgb(152, 115, 247)` ✅ |

</br>
</br>
| Component | Status |
|-----------|--------|
| Structural gate | Installed |
| Role assignment (seed only) | ✅ |
| Zone inference + fallback | ✅ |
| Figure pipeline vnext | ✅ Shared pairing core + `role_candidate`-aware match-time role resolution |
| Table pipeline vnext | ✅ Shared pairing core + `role_candidate`-aware match-time role resolution |
| Object writeback seam | ✅ `paperforge/worker/ocr_object_writeback.py` active on default path |
| Tail settlement seam | ✅ `paperforge/worker/ocr_tail_settlement.py` active on default path |
| V3 normalize split | ✅ ON by default (`OCR_PIPELINE_V3=0` reverts to legacy) |
| Rebuild/orchestrator seam | ✅ Public wrappers unchanged |
| Cross-domain figure/table conflict resolution | ✅ Still external to pairing core |
| **Quality indicators** (Layer 2) | ✅ `paperforge/worker/ocr_quality.py` — `build_quality_indicators()` with 5 normalizers |
| **Readiness policy** (Layer 2) | ✅ `evaluate_readiness()` + YAML policy evaluator with deep-merge, hard-red, use-case gates |
| **Feedback sidecar** (Layer 2) | ✅ `paperforge/worker/ocr_quality_feedback.py` — per-mark hash, stale detection, no UI |
| **Retrieval architecture** | ✅ Retrieval recovery merged and deployed; vec0 index healthy at 2560 dimensions |
| **M metadata search** | ✅ sql.js and Python CLI paths restored |
| **@ deep search** | ✅ deep CLI invocation and result-envelope consumption restored |
| **Vector build control** | ✅ canonical SQLite lifecycle and health state restored |
| **Control-plane contracts** | ✅ Orthogonal capability/activity/attention model and managed-runtime immutable-slot architecture chosen; documented in `docs/research/2026-07-14-capability-state-action-contract.md` and `docs/research/2026-07-14-managed-runtime-architecture.md` |
| **Setup/config migration** | ✅ Bare, headless, and modular setup share `SetupPlan`; schema-v2 `vault_config` is authoritative with warned v1 read fallback |
| **Capability tracer** | ✅ Installation/Help backend envelopes feed the six-module Overview; malformed/stale persistence fails closed; setup/update actions route to the setup flow |
| **Managed Runtime** | ✅ Immutable machine-local slots, atomic pointer activation, rollback/cancel/retention, exclusive managed dispatch, and startup `status()` warmup before settings/probes |
| **Agent workflow controls** | ✅ `.omp/RULES.md` + `matt-guard.ts` enforce one-writer Matt flow, worktree isolation, and post-mutation verification before release operations |
| **Library/OCR/Memory detail tracers** | ✅ Real capability probes with module-detail-navigation, installation-navigation, and capability-state views; Python owns capability fact definitions; TypeScript render uses exact allowlist, fails closed on unknown keys |
| **Maintenance probe (#80)** | ✅ Backend-derived actionable-only rows, privacy-safe local draft, owned inert cleanup, accessible destructive confirmation with exact backend effect; redacted editable issue draft, no token input/auto-open, explicit GitHub open only, URL re-redaction

### 2.3 Fix Status

| # | Paper | Issue | Type | Fix | Commit |
|---|-------|-------|------|-----|--------|
| 50 | — | **2026-08-14 INCIDENT: prune rmtree deleted production vault root** | **Catastrophic data-loss bug** | `library.prune` handler passed `workspace_dir=Path()` (empty) for residuals; `_prune_orphan_papers_locked` did `if ws.exists(): shutil.rmtree(ws, ignore_errors=True)` — `Path()` resolves to cwd (= vault root), `.exists()` always true, `ignore_errors` swallowed everything → recursively deleted `D:\L\OB\Literature-hub` (Resources/99_System/.venv). **Recovered via DiskGenius + exports copy + intact paperforge.db + Zotero (outside vault)**. Fix: trash architecture — `worker/trash.py` moves deletions to `.paperforge/trash/` + manifest (restorable), `validate_target` fails closed on empty/`.`/root/escape (junctions resolved); prune moves files to trash; vectors/DB rows transactional (rowid-verified); pre-commit + CI (`scripts/check_no_destructive_delete.py`) reject `rmtree+ignore_errors` and empty-path rmtree; legacy ignore_errors sites converted to explicit try/except. | `a0fdfcb6` |
| 51 | — | Residual papers invisible to workspace-only orphan scan | Detection gap | Unified residual detection: Zotero (exports) is authority across ALL carriers (workspace dir / papers FTS rows / vector meta / OCR data), probed independently → OCR-only and FTS-only residuals found (e.g. 9RZU5ZBE empty OCR dir). probe lineage reports paper-level `residuals` with per-carrier flags; reconcile emits ONE `library.prune` clearing every carrier; prune handler/command derive candidates from the residual report. | `0a4a81c4` |
| 52 | — | Smart Retrieval panel showed "811/811 built" + "API Key 未配置" contradiction | UI data-source split | Panel info card read stale plugin cache `_vector_db_configured` while diagnostics read live build state. probe memory now injects structured `details` (api_key_configured / paper counts / build_state) from the same authorities as the state machine; status text / button / info card / impact all derive from the envelope (reason.text + action.primary + details); dead `memory.disabled`/`memory.schema_stale` branches removed. | `e63445ae` |
| 1 | — | P21 zone fix (4AG67PBH "Conflict of Interest" heading) | Pipeline code | `infer_zones()` frontmatter_side_blocks page gate: added `first_reference_page is not None and page >= first_reference_page - 1` | `35aabae` |
| 2 | 4AG67PBH | Author bio text in post-ref reference_item (b8/b10) | New module | `post_ref_bio_cleanup` reclassifies bios as `backmatter_body`; `_bio_text_score` category-weighted 0-5 scoring | `e2f0c8a` |
| 3 | — | author_bio_asset role contract | Pipeline code | `author_bio_asset` added to render_default=False, index_default=False skip sets | `7810eb1` |
| 4 | — | Pass C pipeline wiring | Pipeline code | Insert `post_ref_bio_cleanup` + `prune_figure_inventory_after_bio` after `write_back_figure_roles` | `7810eb1` |
| 5 | — | P1 residual author bio pass (Pass B) | New function | `residual_author_bio_pass` detects portrait unmatched_assets/unresolved_clusters with nearby bio text | `7a1cc5e` |
| 6 | — | P1 figure_caption support in Pass C | Role expansion | `post_ref_bio_cleanup` extended for `figure_caption` role | `7a1cc5e` |
| 7 | — | tag_figure_contained_text author_bio guard | Protection | Skip `author_bio` blocks and `author_bio_asset` role in figure containment | `7a1cc5e` |
| 8 | — | Bio word limit 80→200 | Pipeline code | Real bio text 90-100 words exceeded 80-word limit in `_bio_text_score` | `ae081a4` |
| 9 | 4AG67PBH | Barbara bio as structured_insert_candidate missed by Pass C | Role expansion | Added `structured_insert_candidate` to Pass C role list | `ae081a4` |
| 10 | 4AG67PBH | Page 25 portrait id=5 missing from unmatched_assets | Pipeline bug fix | `ocr_figures.py` 4479/4529 used page-agnostic bare block_id filter, hitting collision when same id exists on different pages. Changed to `(page, block_id)` tuples. | `ae081a4` |
| 11 | 4AG67PBH | Acknowledgment text absorbed as reference_item (p21) | Regex fix | `_is_reference_item_candidate` tightened | `fe9cc70` |
| 13 | WV2FF4NV | Fig 10/6 locator caption bridge | New feature | `_is_previous_page_legend_locator` + bridge in `build_figure_inventory`: connects locator → previous full legend → current visual group. Recovers misclassified legends from rejected_legends. | `3f61f4a` |
| 14 | — | **Issue 3**: Backfill word leakage beyond bbox | Word-level filter | Added `_word_belongs_to_block` + `_word_center_inside_rect` filters after expanded clip | `796e8bb` |
| 15 | — | **Issue 1A**: Validation-first bare table skips same-page asset | Continue guard | Validation-first branch only early-exits when no same-page assets exist | `796e8bb` |
| 16 | — | **Issue 1B**: Split table caption continuation escapes ownership | Continuation materialization | `_find_table_caption_continuation` + `_materialize_table_caption` inside `build_table_inventory` | `796e8bb` |
| 17 | — | **Issue 4**: Short papers (≤2p) incorrectly red + needs_rebuild | Health profile | Added `_health_profile(page_count)` → `short_form` waives abstract/heading gates | `796e8bb` |
| 18 | — | **Issue 2**: Demoted-caption figure inner-text leakage | Container bbox regions | Validated `_container_bbox` regions in `tag_figure_contained_text` via 3 helpers + containment-only integration | `0e4ecbc` |
| 19 | — | **Issue 5**: Cross-column page_assets groups falsely accepted | Column-homogeneity gate | `_column_band_id` + rejection in `_is_safe_page_assets_group` | `4ab227e` |
| 20 | — | **Issue 6**: Same asset consumed by figure AND table | Post-hoc arbitration | `resolve_media_asset_conflicts` resolves asymmetric cases; weak/weak stays in `ownership_conflicts` | `4ab227e` |
| 21 | — | Pairing framework extraction + figure migration | Refactor | Extracted shared `ocr_pairing_*` core from figure vnext; preserved public seams and figure behavior | `6229f6c`, `7cfbb5f`, `32541cf` |
| 22 | — | Table vnext on pairing framework + public cutover | Refactor/feature | Added `ocr_table_domain.py` + `ocr_table_passes.py`, preserved resolver-consumed fields, switched `build_table_inventory(...)` to vnext | `db01518`, `ea6a1f0`, `a9e68ac`, `a2e5788` |
| 23 | 37LK5T97 + cutover corpus | Merge-unblock hardening | Moved figure-only rotation enrichment out of generic state, validated 6 runnable real-paper table fixtures semantically, fixed touched-file lint/format issues | `fa734f6`, `9b285b1` |
| 24 | — | Workstream A — object ownership evidence seam | New module | Added `ocr_object_writeback.py`; unified figure/table asset claims, side-adjacent text claims, consumed-block contract, and renderer consumption skip | `964e05b` |
| 25 | — | Workstream B — tail settlement seam | New module | Added `ocr_tail_settlement.py`, extracted tail/body/backmatter settlement, and attached `TailSettlementReport` to `DocumentStructure` | `7bf652c` |
| 28 | — | Wire apply_object_writebacks into rebuild path | Fix | Rebuild entry point never called apply_object_writebacks; side-adjacent/contained claims missing from rebuild production path | `e8aae2e` |
| 29 | M84CTEM9 | Figure inner_text not merged into figure render | Fix | figure_inner_text blocks were correctly recognized but crop bbox excluded variable labels; render_figure_object_markdown emits only image+legend. Fix: expand crop bbox to include owned figure_inner_text blocks | `c42da20` |
| 30 | — | tag_figure_contained_text binds owner_id on contained blocks | Fix | Contained text path stamped role but not _object_owner_id; needed for crop bbox expansion to find the block-to-figure link | `34827f2` |
| 31 | — | Enable OCR_PIPELINE_V3 by default | Toggle | Full vault corpus diff (555 papers): 547/555 no diff, 5/555 v3 improvements. Set OCR_PIPELINE_V3=0 for legacy | `914acd6` |
| 32 | — | OCR rebuild progress + maintenance selection contract | Feature | Added flushed, prefix-separated rebuild/redo streams; full keyed redo; cooperative stop; canonical `needs_derived_rebuild`; All/Recommended filters; selected batch progress UI | `d7b0a527`, `3a516add`, `e556c8ba` |
| 33 | — | OCR maintenance canonical per-row action model | Fix | Added `maintenanceActionForRow()` for `display_action`→verb routing, `maintenanceActionRequiresConfirmation()` redo confirmation gate, batch-action filtering by canonical verb, and cache-manifest preservation. Batch actions now follow the canonical backend action instead of raw `can_rebuild`/`can_redo` booleans; destructive redo requires user confirmation; cache refresh preserves the backend manifest. | `d7b0a527` |
| 34 | — | Setup/config paths had conflicting precedence, duplicate engines, dropped user paths, and false-success exits | Migration/prefactor | Unified CLI dispatch on `SetupPlan`; v2-only writes with v1 read fallback; complete path forwarding; visible deprecation; non-zero required-step failures | `af849699`, `7b747423`, `906b3caf` |
| 35 | — | Agent sessions could bypass the Matt issue lifecycle, fan out writers, cross worktree boundaries, or release after stale verification | Workflow guard | Added sticky Matt rules plus a project hook that blocks parallel writer batches, cross-worktree mutations, and commit/merge/push/PR/issue-close operations until a recognized verification command succeeds after the latest mutation. | — |
| 49 | — | Architecture Audit Slice A — contract, schemas, canonical evidence, and pure reconciliation (#131) | Architecture contract | Added five immutable layers, validated entity metadata and authority declarations including observer/delegated sets, semantic digests and stable finding IDs, source-complete golden fixtures, report-projection digest integrity, and a pure reconciler with explicit failed/incomplete/findings/clean assessment precedence; repair pass adds strict SHA-256/path validation, auditable consumer identity, entity lifecycle/enforcement inheritance, coverage union, and composable failed audits. | `73a782cf`, `078dd8a7`, `963cc59a` |


| 36 | — | Maintenance probe: backend-derived rows, privacy-safe local draft, accessible destructive confirmation (#80) | Feature | Implementation in Issue #80 worktree. Backend-focused gate 77/77; plugin full suite 381/382 (pre-existing capability-state test expecting help.stale but receiving help.invalid_response); typecheck/build clean; production bundle 264.4KB; Obsidian 1.12.7 smoke 730/768 with actionable-only rows, keyboard Enter, accessible destructive confirmation with exact backend effect, focus trap/restoration, owned inert cleanup, redacted editable issue draft, no token input/auto-open, explicit GitHub open only, URL re-redaction, no horizontal overflow. | — |
| 37 | — | Literature-hub loaded duplicate `.obsidian/plugins/paperforge.bak`, while the correct bundle used an unwarmed Managed Runtime and the published 1.5.15 backend lacked `probe` | Deployment/runtime fix | Moved the duplicate outside the plugin scan path, migrated both credentials with readback verification, installed the current backend into the canonical managed venv, restored idempotent migration on startup, shared and warmed the runtime before dispatch, synchronized manifest `minAppVersion` 1.11.4, rebuilt and redeployed. Live cold-start verification: #78 overview/detail, #79 configured secret state, #80 three-row Maintenance inbox; no captured Obsidian errors. | — |
| 38 | — | Control Center cutover left raw i18n keys, legacy settings surfaces, stale setup state, non-localized actions/notices, Chinese UI falling back to English, and a two-column card grid wider than its host pane | UI/state repair | Completed the five-module / three-destination cutover, removed duplicate surfaces, normalized persisted state, localized backend action IDs and notices, added host document-language fallback, changed card columns to `minmax(0, 1fr)`, and verified every English/Chinese page in real Obsidian without overflow. | — |
| 39 | — | Test-vault live UI: OCR Workspace showed 0/0 papers in a persistent “处理中”, opened in a narrow right sidebar; control center/SR had raw or English strings and white primary actions | Frontend path composition joined `vault`/`PaperForge` twice; sidebar placement was intentional-but-unusable for a table; live renderer used legacy localization keys; Obsidian core selector outranked `.pf-action-btn` | Use `ResolvedPaths.indexesDir`/`ocrDir`, open a main tab, migrate live strings to localized keys, add `sr_config_label`, and make the action selector `button.pf-action-btn` | — |
| 40 | — | Setup Journey exposed stale probe failures and made Library configuration a dead-end status with no editable folder paths | First-run setup depended on manual detection and surfaced a separate library probe action instead of the configuration that determines success | Auto-probe stale Foundation/Library once; consolidate Zotero and all four vault paths in a verified Stage 2 form, with Continue gated on the refreshed result | — |
| 41 | — | Foundation installation nested the legacy setup wizard and ran Library configuration before the user supplied any Library paths | Setup journey conflated Python package installation with `paperforge setup --modular` | Keep the in-flow reinstall action; Foundation accepts a Python executable and installs/verifies only the PaperForge package, while Stage 2 saves and verifies the five Library paths | — |
| 42 | — | Optional capabilities in Stage 3 were checkboxes without their required API/platform configuration, despite the approved prototype defining inline configuration cards | Production Stage 3 only captured transient selections and deferred configuration to module details | Expand each selected optional card in Stage 3: securely store OCR/Retrieval credentials, persist Retrieval model/base URL, and save the Agent platform | — |
| 43 | — | Smart Retrieval kept a global `vector-db-api-key` while Base URL/model were mutable; first profile IDs also exceeded Obsidian’s 64-character limit | Credential identity did not include the retrieval endpoint/model tuple and SecretStorage has a strict identifier contract | Store secrets under a 61-character SHA-256-derived profile ID; only resolve the current tuple; leave unscoped legacy secrets unused because their provenance is unknowable | — |
| 44 | — | Setup Journey Stage 4 treated every cached prerequisite envelope as a current failure, disabling completion even after valid Foundation/Library setup | Stage 3 navigated directly to review without refreshing required probes after a plugin reload | Refresh both prerequisites on Stage 3→4 and offer a localized recheck action only if either remains unavailable | — |
| 45 | — | Foundation reported ready based on config + Python compatibility without asserting the backend package matches the loaded plugin; a prior mismatch could also leave a stale reinstallation CTA after readiness recovered | The installation probe had no expected package-version input, and `_setupReinstallRequested` was treated as a persistent render condition rather than a transient recovery request | Pass the plugin manifest version to the installation probe; a mismatch is actionable and opens forced reinstallation; exact ready clears the request and renders only Continue | — |
| 46 | — | Smart Retrieval replaced its backend-provided `memory.rebuild_vector` action with a generic “检测”; Agent was hard-coded as unimplemented despite its selected-platform skill being deployed; a persisted legacy-key warning remained after the active profile was valid | Fallback action localization discarded the concrete rebuild verb; the Agent card used a placeholder envelope instead of local deployment evidence; profile migration never removed a warning made obsolete by explicit profile configuration | Render the exact localized “构建索引” action and dispatch its allowlisted backend command; derive Agent ready/not-enabled from `<selected platform>/paperforge/SKILL.md`; retain unscoped plaintext but clear only its stale warning once the active profile secret exists | — |
| 47 | — | Smart Retrieval's live “构建索引” first crashed on function-local vector imports, then surfaced only an exit code; after transport recovery it falsely reported failure although indexing completed; a ready page retained a warning impact box | Local imports shadowed module helpers; stderr was discarded; `write_vector_runtime` referenced `object_chunk_count` without accepting it; the impact renderer treated every non-`"ready"` reason string as action-required | Hoist vector helpers, display final stderr diagnostic, declare SOCKS transport for proxy-backed OpenAI SDKs, add `object_chunk_count` to the snapshot contract, and render impact only for `needs_action` | — |
| 48 | — | OCR workspace table width not adapting; action column (预览) invisible; old flex-based `.pf-ocr-ws-table` CSS conflicted with real `<table>` layout; command names had duplicate "PaperForge:" prefix; ribbon icon and ctrl+p command both existed but one command name was malformed | Old section 1 flex CSS (.pf-ocr-ws-table { display: flex }) overrode section 2 table-layout: fixed; `.pf-ocr-ws-col-date` lacked nowrap/muted styling; command names hardcoded "PaperForge:" prefix causing Obsidian double-prefix | Remove conflicting old flex-based table CSS, add `min-width: 0` on title column, add nowrap/muted styling on date column, fix all command name prefixes | — |
| 49 | — | Disposable-vault real UI audit found stale credential truth, 30s probe deadline, missing credential remediation, hidden/incorrect cancellation state, stale embed failure/corruption truth, action-policy drift, dashboard reopen/setup dead ends, raw i18n keys, and OCR NDJSON stdout contamination/scope loss | Multiple projection seams bypassed their owners: dashboard cached flags, probe-owned policy metadata, legacy process fields, and worker human stdout leaked into machine streams | Route dashboard credential status through Python auth; project registered action policy in probe; strict-clean OCR NDJSON and explicit scope; controller-owned Stop/cancel/error truth; pristine vector DB = not-built; 60s probe deadline; awaited dashboard reveal; direct Setup/OCR remediation; complete translations. Evidence: `System/PaperForge/audits/ui-e2e-findings.json` in disposable audit vault. | — |
### 2.4 Recovery Incident (2026-08-14 — **CLOSED** 2026-08-16)

The recovery event is closed. The final mutually exclusive census is frozen in `indexes/recovery-census-final.json`:

| Authority | Final state |
|-----------|-------------|
| Library census | **958 total = 938 OCR/retrieval current + 19 `nopdf` + 1 `pdf_missing` (`4VPYIVAS`)** |
| Integrity | **938 current papers verified** across OCR, retrieval, and materialization integrity |
| Vector substrate | **935 vector-current + 3 `no_content`**; `nopdf`/`pdf_missing` excluded by eligibility |
| Serving | **Smoke verified**: `retrieve "cartilage repair"` returns real hits |

`nopdf` is a valid terminal state for URL-only entries. `4VPYIVAS` is a blocked source state because its index claims a PDF but the file is missing; it is not `nopdf`. This is a user-side recovery item and does not block the RC code freeze.

**Impact:** documentation-only closure record. No re-OCR, rebuild, or embed is required; existing users see no behavior change.

### 2.5 Control Plane Closure (2026-08-17 — **CLOSED**)

| Milestone | Closed contract | Evidence / commits |
|-----------|-----------------|--------------------|
| M1 | OCR execution control: `batch_id`, provider observer, lock recovery, resume, Ctrl+C detach | `cac9b611`, `9178d654`, `bb76e3f0` |
| M1.1 | `no_content` is terminal-satisfied; write-ahead submission marker; bounded provider jobs; submitting state visible | `b6bf4e17`, `9889b973` |
| M2 | Orthogonal availability × applicability preflight, derived settlement, six-event NDJSON contract, architecture boundaries | `1a7430b5`, `744d73cf`, `13f8d544` |
| M3 | EmbeddingService boundary, canonical retrieval-truth eligibility, direct Action→Service handlers, thin CLI adapter, `paper_settled`, build/resume selector parity | `3891da12`, `033a7fee`, `1b43faef`, `f6e5db35`, `30cbfc65`, `cbc66579`, `fd75deaf` |

Known deferred debt: **EmbeddingService stdout relay**. It is a presentation-channel debt, not an ownership, materialization, recovery, or release-contract defect: Actions do not call CLI handlers, Services do not import `paperforge.commands`, structured PFResult remains execution truth, and the relay does not participate in business decisions. Remove it after RC and before Goal/Ensure.

**Impact:** closure record only. M1–M3 changes do not require re-OCR, rebuild, or embed for existing users; M3 adds one standard `paper_settled` NDJSON event for stream consumers.

### 2.6 M4 post-freeze audit and live census closure (2026-08-17–18 — **EVIDENCE OPEN**)

The first shared-state audit against the frozen candidate reproduced two
candidate/code findings:

1. **Retrieval integrity:** mutating a published `body_units.unit_text` without
   changing its manifest left the candidate reporting `retrieval=current` while
   the carrier snapshot was corrupt. Repair commit `46c4ddaf` maps this to
   `retrieval=stale`, `vector=stale`, and `memory.build`.
2. **Frontier parity:** action preflight could classify a per-paper action as
   `needed` when `reconcile()` emitted no intent or a different first frontier.
   Repair commit `46c4ddaf` projects `needed` from reconcile's canonical intent.
3. **Scope leakage:** per-paper preflight, reconcile, and embedding
   eligibility were still calling the full-library lineage probe. On the
   production vault this made an eight-key preflight pay for library residual
   scans and violated the papers-scope contract. Repair `b66fde53` adds the
   canonical-authority-filtered `observe_lineage_papers(keys)` read model;
   scoped consumers now inspect only requested paper carriers and return no
   library residual/orphan facts. Focused scope/parity/action tests pass
   (**87 passed, 1 warning**); the exact eight-key production preflight now
   returns `needed=8` in **3.17 s**. The eight-key execution remains
   owner-confirmed and was not run.

**Impact:** read-only observation and action-projection repair. No production
materialization changed; no re-OCR, rebuild, or embed is required for valid
existing papers. Existing users receive bounded per-paper preflight instead
of a full-library observation.

Focused verification after the repairs: **126 passed, 1 warning** across
lineage, reconcile, embedding eligibility, and action-registry tests. The
repairs remain on `master`, outside frozen candidate `6ef0dfe9`; the normal
candidate/dependent-gate decision remains separate from the census closure.

The **958 → 964 live authority/materialization divergence is explained and
closed** by `project/current/rc-live-census-reconcile.json`:

- frozen recovery scope `R=958`; current formal/live-export scope `F=964`;
  `F-R` contains 7 normal Authority additions and `R-F` contains the one
  confirmed residual `R2PSFXY4`;
- `944` papers are OCR/retrieval current; the remaining 20 are 19 legitimate
  `nopdf` terminals plus blocked `4VPYIVAS` (`pdf_missing`);
- `944 = 933 vector_current + 3 vector_no_content + 8 vector_not_embedded`;
  there are no stale/unknown vector states and no `memory.build` candidate;
- `R2PSFXY4` is outside Authority with all carriers remaining. The canonical
  reader gate excludes it by contract; targeted live serving evidence remains
  open, so no prune was run.

**Impact:** read-only reconciliation only; no production materialization
changed. No re-OCR, rebuild, or memory build is required from the census
divergence. Eight retrieval-current papers remain a known scoped
`embed.resume` evidence action; three `vector_no_content` papers are terminal.

Remaining M4 evidence is release-gate work: true scoped embed with fresh
re-observation, residual serving smoke, exact-candidate frontend/hosted gates,
and rollback/support-window owner acceptance.

### 2.7 Sync latency diagnosis (2026-08-18)

The long `sync --json` path was dominated by the full read-only reconcile
that runs after selection/index phases. Its lineage loop reparsed the
multi-megabyte `formal-library.json` once per paper through
`_resolve_canonical_pdf`, turning canonical-PDF lookup into
O(papers × index-size). On the production vault, full reconcile measured
144.61 s before the optimization and 48.38 s after it; selection sync was
20.90 s and the unchanged-index fast path was 0.53 s. The remaining
non-fatal PDF resolver warning is the known malformed `TPJLQNXR` locator.

The working-tree fix builds one canonical-PDF map per lineage observation;
the existing per-paper resolver remains unchanged for other callers.
Focused disposable-cache, lineage/reconcile, architecture, and sync tests
pass (**167 passed, 1 warning**).

**Impact:** read-only lineage optimization only. No production materialization
changed; no re-OCR, rebuild, or embed is required. A full production `sync`
rerun was not used as verification to avoid concurrent mutation; the
production reconcile measurement and disposable sync suite cover the changed
path.

### 2.8 OCR settlement and scoped-memory regression closure (2026-08-18)

The OCR worker now counts `done_degraded` as a terminal success, emits
per-paper progress only once at settlement, preserves the completed queue
state during upload/poll transitions, and reports terminal-only/no-work runs
as `done` instead of `no items processed`. The status command also exposes the
write-ahead `submitting` window as incomplete execution-unknown state.

The scoped memory build path remains scope-faithful: requested keys are
validated before writable DB access, fresh/destructive DBs fail closed with
`global_rebuild_required`, and existing DB builds do not delete or materialize
non-requested papers. Focused regression coverage is **174 passed, 1 warning**,
including OCR control/state, memory scope, action, lineage, and sync suites;
CLI help, read-only action preflight, and Python syntax checks also passed.

**Impact:** local state/accounting and read-only scope-contract fixes only.
No production vault mutation, re-OCR, rebuild, or embed was performed or is
required for existing valid materializations. Existing users see corrected
terminal counts/progress and bounded scoped-memory behavior; remote provider
jobs and stored OCR artifacts are unchanged.

### 2.9 Lineage probe observation optimization (2026-08-18)

The read-only lineage observation (the dominant `sync --json` / probe /
preflight cost) was tightened without changing any state semantics:

- `meta.json` is read **once per paper per observation** and injected into
  lifecycle / detail / version / execution judging (`materialization/ocr.py`
  functions gained an optional `meta` parameter; old callers unchanged).
- A `current` paper's fine-grained WHY is provably `None` (current requires
  a verified provenance), so probe skips the detail recompute — cutting
  `provenance_state` from 2 to 1 calls per paper (one PDF + raw sha256 per
  paper saved).
- Lineage vector identities are batched into one `IN (layer)` query instead
  of one round-trip per paper.

Focused regression: **189 passed, 1 warning** across lineage, reconcile,
materialization SSOT, embed eligibility, action registry, sync, OCR control,
and scoped-memory suites. Production scoped 8-key `embed.resume` preflight
measured **2.49 s** (previous baseline 3.17 s). A production profiler run
shows the remaining probe time is dominated by the OCR artifact-chain
re-validation (`top_state` must re-parse raw/blocks/tree to prove
`materialized` — 985k line-level JSON parses on the full library); that is
judgment semantics, not waste, and is the target of the deferred observation
cache (post-RC, with the Goal/Ensure kernel).

**Impact:** read-only observation only. No production materialization
changed; no re-OCR, rebuild, or embed is required. Existing users see the
same state outputs at lower cost.

### 2.10 Weak-model Agent protocol closure (#188/#189 — COMPLETE, 2026-08-19)

The PaperForge agent skill was linearized and the last decision class
removed from the model:

- Skill protocol: three linear routes (known paper / known-paper passage /
  cross-library), `query-plan` demoted to optional diagnostic, `retrieve`
  demoted to semantic fallback, agent-constraint rules ("must not render
  CLI args, infer JSON nesting, discover files manually, invent fallback
  tools, repeat fallback branches").
- New canonical local-read primitive `paperforge read <KEY> --find <TERM>`
  (#189): KEY + literal query in, structured `matched / no_match /
  no_readable_source` out; canonical lookup via `memory.query.lookup_paper`
  (no `commands.*` import), fulltext + canonical PDF (wikilink handled by
  pdf_resolver, PyMuPDF), literal case-insensitive substring, read-only.
  Skill no longer carries grep/PyMuPDF/path extraction.
- Qwen3-4B-Instruct fresh-session behavior seam: A/B/C/D all PASS (before
  the primitive, A/B reproducibly bypassed fulltext and called retrieve).
  The retest is the causal control: same prompts, only the protocol
  changed. This seam is now an **Agent compatibility gate** for RC.
- Design principle validated: if an agent needs to extract a locator from
  structured state and synthesize shell/Python to perform a stable product
  action, that action is not yet a PaperForge capability.

**Impact:** additive `read` CLI command; skill protocol only for existing
workflows. No re-OCR, rebuild, or embed required. M4 note: `read` is new
Python code outside frozen candidate `6ef0dfe9`; release head and candidate
rebind remain owner decision.

### 2.11 Agent skill deployment: shared .agents + agent-chosen target (2026-08-19)

Research (2026-08): `.agents/skills` is the widely adopted cross-client
convention for the Agent Skills (SKILL.md) format, natively read by
Claude Code (>= v2.1.121),
Codex, OpenCode, Cursor, Gemini CLI, Kilo, Crush, Kimi-cli, and Oh My Pi/Pi.
GitHub Copilot (`.github/skills`), Cline (`.clinerules`), Windsurf
(`.windsurf/skills`) and augment/trae keep explicit dirs.

Decision: PaperForge no longer routes skill deployment per platform. The
per-platform path table was removed from the code; the agent chooses the
target (it knows its own harness, e.g. `.omp/skills`) and runs the new
read-only-free, deterministic primitive:

```bash
paperforge skill deploy --to <vault-relative-dir> [--overwrite] [--json]
```

Default target is the shared `.agents/skills`. Setup deploys there too;
`agent_platform` remains a canonical identity record (CLI choices + config
enum derive from the single `AGENT_PLATFORM_IDS` registry). Platforms added:
`kilo`, `pi`, `omp`, `crush`, `kimi`. This removes the per-platform path
maintenance burden and keeps the weak-model contract (one command, no path
synthesis).

**Impact:** re-OCR: none; rebuild: none; embed: none; old users: skill
deployment target may change from a per-platform dir to `.agents/skills`
(shared standard; most agents read both).
### 2.12 S1–S6 lightweight disposable certification (2026-08-20 — executable 462398cb → a42f8bb7, docs 781910f3)

S1–S6 executed as current-system certification / #191 gap census, not as #191 product implementation. All gates use disposable minimal fixtures (no full 964-paper migration) and are bound to exact `462398cb` via worktree `D:/L/Med/Research/99_System/LiteraturePipeline/.cert-462398cb` and venv `pf-cert-s1-venv` (Python 3.14.0). Evidence bundle: `project/current/cert-462398cb-S1-S6-matrix.md`. **Hosted `462398cb` `32269242351` failed `L0.5 — Ruff F821 AGENT_SKILL_DIRS`; fix `a42f8bb7` removes dead `headless_setup` block (495-909), `ruff --select F821,F822,F823` now clean, `setup_wizard` 68 passed, no re-OCR/rebuild/embed.**

| Gate | Vault | Result | Note |
|------|-------|--------|------|
| S1 Clean Install | `pf-cert-s1-vault` fresh empty, `setup --modular --skip-checks --json` | **PASS** | `probe installation` = `ready`, `status` = 0 papers, `doctor` FAIL only on optional Zotero/BBT, Foundation independent. #191 gap: `setup` still deploys `.agents/skills` and retains `skill_dir/command_dir/agent_platform` in `paperforge.json`. |
| S2 Existing Vault Without .obsidian | `pf-cert-s2-minimal` — 2-paper `formal-library` + copied fulltext + `System/PaperForge/ocr` fulltext + `memory build` (2 indexed) | **PASS** | `status` 2 papers, `probe` ready, `runtime-health` degraded only before `memory build`, `paper-status`/`search`/`read` succeed after build, `retrieve --paper` scoped and honest, `reconcile`/`sync --dry-run` ok. No command failed due to `.obsidian`/plugin/frontend cache. |
| S4 Maintenance | same | **PASS** | `action list`, `reconcile` (missing→`ocr.run` next_action), `prune` dry-run, `action preflight`, `paper-status UNKNOWNKEY` → `PATH_NOT_FOUND`, `config validate` → `valid` and after inject → `config.corrupt`. No fabricated `healthy`. |
| S5 Destructive Safety | same | **PASS** | `action run ocr.run` without `--confirm` → `confirmation_required` rc3; with `--confirm` → ok; `action run --force` → `unrecognized arguments`; `prune --force` safe (no orphans). Confirmation boundary enforced. |
| S3 Full Library Journey | same disposable 2-paper | **PASS** | Chain `setup → memory build → search → read → retrieve --paper → embed status → action preflight/run` intact without Obsidian; `embed.build --confirm` → explicit `401 invalid_api_key` (fail-closed, not silent) — expected without valid embedding key. Restart simulated via re-`probe`/`read`. |
| S6 Lifecycle / Recovery | same | **PASS (partial)** | `config corrupt` → `config.validate` = `invalid config.corrupt` (fail-closed); restore → `valid` + `setup` repeat idempotent + `probe ready` + `read matched` persist. Offline/stale-pointer/malformed-pointer/Release-N reinstall remain **owner gate / evidence open** (not re-judged lightweight). |

Triage: **No RC blocker** in current-invariant lightweight gates (Ruff blocker now fixed in `a42f8bb7`). **#191 gaps (real, not assumed):** Foundation still deploys skill; `paperforge.json` still has `skill_dir/command_dir/agent_platform`; missing `setup inspect (facts+requirements+questions[]) → plan (observation_fingerprint+plan_hash) → apply (plan_stale guard) → verify` protocol; missing verified-switch `relocate` lifecycle; missing `external_action`/`secure_external` secret contract; S8 multi-client concurrency not live-proven (but `skill status --json` observation exists). Performance (`144s→48s→2.49s`) is post-RC debt. Full RC 5 owner bands remain.

**Impact:** `462398cb` → `a42f8bb7` is dead-code removal only (415 deletions in `setup_wizard.py`); no re-OCR/rebuild/embed for existing users; no production vault mutation. Worktree `.cert-462398cb` and venv `pf-cert-s1-venv` are disposable. New candidate `a42f8bb7` `ruff` clean; hosted `a42f8bb7` pending `3.11+newer`.
### 2.13 Read-only render consistency investigation (2026-08-21 — IN PROGRESS)

The V1 audit ran across **965 papers**: **189 CLEAN, 776 DEGRADED, 0 FAILED**, with **5527 issues**. Domains were `render_layer=5304`, `inventory_layer=164`, and `asset_layer=59`; the dominant diagnoses were `render_image_materialization_missing=3902` and `dangling_render_asset=1254`.

Evidence from `F5CHZH3H`, `UV6IVNUE`, and `8M4QY2CY` shows canonical figure/table objects and legacy `images/blocks` output while `assets/figures`/`assets/tables` and/or render image references are absent. A controlled temporary run through the existing `extract_and_write_objects` path produced no asset/image reference with the raw locator and produced both with the resolved Zotero PDF for one degraded paper (`F5CHZH3H`) and one CLEAN paper (`Z828Y6T9`). This proves the renderer's crop/materialization boundary is sensitive to its existing PDF input; it does not yet prove the historical production failure's exact phase.

The existing object materialization seam now emits additive `render/materialization.provenance.json` records with `status`, `stage`, `reason`, `pdf_input`, paths, and attempts while preserving the legacy crop bool contract. The audit only projects matching records; production corpus currently has `materialization_provenance=missing` because no rerender/rebuild was run.
The temporary 10/10/10 matrix produced: A `render_image_materialization_missing` raw-locator sample = 7 successful direct crops, 3 `pdf_not_found`; the same resolved-PDF sample = 9 successes, 1 `page_out_of_range`; ten CLEAN resolved-PDF samples = 10 successes; ten dangling-reference table samples = 8 successes and 2 `source_asset_unavailable`. These are seam observations, not production rerender results.
The shared `write_render_outputs` boundary now invokes the existing read-only audit after the final render files are written, covering both initial OCR and derived rebuild paths. Audit exceptions are warning-only; rendering behavior remains unchanged.
The fresh disposable 20-paper corpus (10 historical materialization-missing, 5 CLEAN, 5 dangling-reference) ran through the shared output boundary: all 10 materialization-missing figure samples produced `materialize/success`; all 5 CLEAN samples did likewise; dangling samples produced 4 `materialize/success` and 1 `source_asset_unavailable`. This was a disposable render/materializer validation, not a production rebuild.
Across the completed 965-paper report-only pass, the three buckets totalled **3619 exact render repairs, 128 inventory proposals, and 727 blocked cases** across **642, 86, and 354 papers**, respectively. These counts are planning evidence only; no repair action was executed.
The consistency audit now exposes canonical/render position evidence without changing truth: legend page/block, object page, asset pages, page range, relation (`same_page`, `legend_before_asset`, `asset_before_legend`, `cross_page`, `no_asset`), and asset bboxes. In 388XI46Q this makes Figure 3's caption p10 → asset p11 explicit and keeps reservation artifacts visibly asset-less.
The exact-repair planning dry-run checked all **3619 candidates** without writing files: **3619 need fresh provenance, 0 are execution-ready, 0 remain blocked** after correcting ownership keys to `(page, block_id)` for page-local OCR IDs. Five representative live-snapshot checks all matched their audit snapshots but likewise remained `needs_fresh_provenance`. This is a planning result, not an apply authorization.
The full exact materializer dry-run staged all **3619 candidates** in disposable directories: **3618 materialized and verified** (non-empty readable image, correct markdown reference, provenance success) and **1 failed**: `2ZBAK9VY/figure_003`, where the canonical page is 9 but the resolved PDF has only 8 pages (`page_out_of_range`). This confirms a missing PDF-page validity gate; no production file changed.
### 2.14 First and second figure-repair semantics (2026-08-21 — FROZEN)

**First semantic — canonical-to-render gap:** the canonical figure already exists, its ordered asset references and ownership are already known, and only the final render image/markdown link is missing or invalid. The repair writes render-layer outputs only. Full-library staging dry-run covered **3619 candidates across 642 papers**: **3618 materialized and verified**, **1 failed** at `2ZBAK9VY/figure_003` because inventory page 9 exceeds the resolved PDF's 8 pages. No production output was changed.

**Second semantic — canonical-missing figure candidate:** caption/source-image/PDF-media evidence suggests a formal figure, but no canonical inventory object exists. It is proposal-only. In `388XI46Q`, Figure 2 and Figure 5 are high-evidence proposals; neither may create `figure_002`/`figure_005` or write render artifacts.


### 2.15 Bounded-slot proposal dry-run (2026-08-21 — COMPLETE)

All **128 canonical-missing proposals across 86 papers** were tested against existing unresolved clusters/unmatched assets, anchor slots, page ranges, ownership, and optional PDF media. Results: **37 structurally unique proposals with PDF confirmation, 1 unique candidate without PDF confirmation, and 90 blocked**. Blocked causes: 30 multiple candidates, 39 multiple candidates with missing anchors, 20 no candidate, and 1 no candidate with missing anchor. `388XI46Q` produced two structurally unique proposals: Figure 2 from `unresolved_cluster_001` on p8 and Figure 5 from `unmatched_asset_p14_b4` on p14. No canonical object or render file was created.
All **38 structurally unique proposals** were then materialized as temporary proposal previews using existing visual groups: **38/38 preview-verified**, **38/38 staging audits CLEAN**, with 19 unresolved-cluster candidates and 19 caption-role-missed/unmatched-asset candidates. Preview IDs remained provisional; no canonical or production render writes occurred.
Owner review of the first pass found four global gates, all now fixed and rerun: **one-sided anchor direction**, **anchor page-range boundaries** (a cross-page anchor's full range bounds the slot), **paper-level claim exclusivity**, and **visual claim identity** (group IDs plus member block references, so a cluster and its member asset cannot be claimed separately). Corrected rerun over the same 128 proposals: **40 structurally unique with PDF confirmation, 2 unique without PDF confirmation, 86 blocked, 4 `candidate_claim_conflict` blockers; duplicate visual-claim audit is empty.** Transition from the first pass (37): **31 retained, 9 new unique, 6 removed** (`6ZWKUPCU` ×2 and `IGR5PYH2` ×2 via claim conflict, `K6EBNFNK` ×2 via anchor direction).
The corrected **40+2 unique set** was then preview-staged with the authoritative materializer: **42/42 preview-verified, 42/42 staging audits CLEAN** (33 unmatched-asset, 9 unresolved-cluster candidates across 39 papers). This is the current preview-verified set; the earlier 38/38 result applied only to the superseded candidate set.
Human review census rules are frozen in `project/current/human-review-census-rules.md` before any review begins: primary precision = `confirmed / 40` (uncertain stays in the denominator), secondary = the 2 no-PDF-confirmation candidates, and per-row provenance fields are fixed. Machine-side acceptance is complete; semantic acceptance awaits the 42-case full census.

### 2.16 Reconcile-only identity hardening (2026-08-26 — COMPLETE)

The reconcile layer remains independent from the preceding OCR/render pipeline. No front-render source or production artifact was changed. A read-only census over **965 papers** found **250 duplicate canonical figure-ID groups across 182 papers**: **26 identical-plan groups** and **224 conflicting-plan groups**, producing **500 affected output paths**.

`render_audit` now reports `inventory_duplicate_entry` with duplicate class, row digests, pages, namespaces, and ordered asset references. `build_reconciliation_report` removes ambiguous IDs before R/P indexing, emits explicit blocked records, and prevents conflicted labels from becoming replacement proposals. R staging now passes only selected exact-repair rows, never the full inventory or unrelated tables; this prevents reconcile staging from reintroducing an upstream duplicate writer.

The census artifact is `project/current/render-reconciliation/duplicate-id-census.json`. Verification: **82 focused tests passed, 1 warning**; Ruff `E,F,I` clean. D1 promotion and human proposal acceptance remain separate follow-up work.

### 2.17 R promoter (2026-08-26 — IMPLEMENTED, ROLLOUT BLOCKED)

`stage_reconciliation()` now writes an R-only `r-manifest.json` containing the selected object identity, live input snapshot, ordered asset references, plan hash, staged paths, image dimensions/hash, markdown hash, and staging provenance. `paperforge render promote-r KEY [OBJECT_ID...] --json` consumes that manifest without re-materializing.

The promoter validates: manifest freshness, canonical occurrence exactly one, duplicate-identity absence, ordered refs equality, ownership uniqueness, fixed staged/production paths, decodable staged image, staged dimensions/hash, markdown link resolution, staging provenance, and plan hash. It writes production JPG/Markdown via atomic per-file replacement, snapshots targets and rolls back on mid-batch write failure, merges provenance, runs a fresh audit, and is idempotent when artifacts already match.

This is not a rollout approval. Exception-injection rollback is verified; hard-kill/restart recovery and stratified R canaries remain mandatory before any batch promotion. No production write was executed in this session.
### M4 RC Gate Policy

M4 is a validation and release-decision phase, not a feature-development phase. The candidate is frozen after the closure commit; only a verified release blocker may change it.

- **BLOCKER:** data corruption or loss, wrong owner/authority, silent fallback, false state, unrecoverable execution, install/upgrade/rollback failure, or broken CLI/machine contract. Fix it, then rerun the affected gate.
- **NON-BLOCKER:** cosmetic, ergonomic, optimization, or post-RC architecture debt. Record it in the RC matrix and do not change the candidate.
- The unique acceptance source is `project/current/2026-08-17-rc-gate-matrix.md`. Every test and live smoke result must attach evidence to a row.
- RC priority is: CLI behavior in success/failure/cancel/offline/invalid-input cases; complete user-to-screen call chains; one authoritative state machine per domain; and complete preflight/postcondition/re-observation checks.

### Layer 1: OCR Truth Coverage — Layout-Category Audit
**Workstream X complete.** 11 papers audited across 6 layout classes, verified via vision subagents. 6 real bug patterns identified. Full report: `docs/superpowers/analysis/2026-07-05-layout-truth-audit-findings.md`

**Bug patterns found:**
- **A** `_is_obviously_formal_figure_caption` heuristic — "Fig. X shows..." body text classified as figure caption (`ocr_roles.py:193`)
- **B** Cross-column figure asset mis-assignment — nearest-neighbor ignores column boundaries (`ocr_figures.py:704`)
- **C** Render frontmatter skip — authors/affiliations silently dropped from fulltext (`ocr_render.py`)
- **D** Two-column same-page boundary — body pulled to backmatter zone on mixed pages (`ocr_document.py`)
- **E** Frontmatter headings ("ARTICLE INFO") misclassified (`ocr_roles.py`)
- **F** Supplementary-only PDFs — pipeline not designed for non-standard structure

**Non-bugs confirmed:** 170 `reference_span_error` findings = FALSE POSITIVE (high-risk noise). Single-column same-page boundaries = FALSE POSITIVE.

### Layer 2: OCR Quality Report + Readiness Policy
**DONE** at commit `d7b0a527`. Three modules delivered:
- `paperforge/worker/ocr_quality.py` — `build_quality_indicators()` (5 normalsers) + `evaluate_readiness()` (policy evaluator)
- `paperforge/policies/ocr_readiness_v1.yaml` — default policy (weights, hard-red, use-case gates)
- `paperforge/worker/ocr_quality_feedback.py` — human feedback sidecar (per-mark hash, stale detection)
22 new tests. Contract polish: `status/gates/reasons` output shape, hash validation, user override bypass.

### Retrieval Experience Recovery

[Wayfinder: Restore PaperForge retrieval end to end](https://github.com/LLLin000/PaperForge/issues/45) completed and the resulting retrieval fixes are merged to `master`. The live Literature-hub vault has a healthy 2560-dimensional vec0 index; M and @ search paths are operational.

### Layer 3: Plugin UI
The deployed Map #94 control center is under owner acceptance. The current test-vault repair also separates first-run Foundation runtime installation from Stage 2 Library configuration, so an installation action cannot create or overwrite Library configuration before the five editable paths are supplied.
Stage 3 now follows the approved Setup Journey prototype: each selected optional capability expands its configuration in the install flow instead of creating a post-install dead end. Foundation ready now means recognizable vault configuration, Python ≥3.11, and an exact backend/package match to the loaded plugin; it clears any old reinstallation request and renders only an enabled Continue control. Stage 4 rechecks Foundation and Library before deciding whether completion is available, so a fresh plugin session cannot mistake stale cached envelopes for missing configuration.
Smart Retrieval now preserves the backend’s `memory.index_stale → rebuild_index → paperforge embed build --force` contract as the primary localized “构建索引” action, rather than degrading it to “检测”. The active test-vault credential profile is present in Obsidian SecretStorage; its stale migration banner is removed without importing or deleting the unrelated unscoped legacy value. Agent Integration now reports ready when the selected platform contains `paperforge/SKILL.md`; “实时连接尚未验证” remains an explicit separate fact, not a false “未启用” capability state.

### Layer 4: Downstream Tools
`chunker.py` uses hardcoded section regex + fixed 3-paragraph groups. OCR has rich structured output (sections, headings, figures, tables with captions) — chunker should consume this structure directly. Figures/tables should support separate embedding (text + future vision).

### Layer 5: Embed/Vector Pipeline — 2026-08-14 findings (need investigation/optimization)

Verified full library embedded (811 papers, 16000 body + 6725 object chunks, lineage 810, probe ready, deep retrieval returns real matches). Issues found during partial-publish/resume work, all open:

1. **embed build process hangs after publish** — `embed build --resume` completed the shadow publish (DB fully updated, build_state=completed/811/811) but the process never exited (13+ min uptime, ~0 CPU, ~5MB RAM); killed with taskkill. Hang location unidentified; suspect post-publish bookkeeping (`_mark` to live, result emit, or pty/stdin under supervised launch).
2. **Zombie `status=running` downgrades resume to full rebuild** — after a kill, build_state stays `running` with dead pid; next `--resume` with no surviving candidate hits gate-1 (stale running) → `resume=False` → full shadow rebuild re-embeds ALL 811 (correct, wasteful). Writer of the `running` state after manual `interrupted` fix unknown.
3. **Reader `.read.lock` is a mutex, not shared** — plugin polling pile-up (8+ stale processes) queues on it; 10s timeout cascaded into false `memory.db_corrupt`. Fixed at ffb9540a (`_is_lock_failure`, `memory.db_busy`), but mutex-reader contention itself needs optimization (shared read lock or fewer plugin spawns).
4. **Old plugin main.js spawns many short-lived probe/sync processes** that pile up when one hangs; new main.js deployed Aug 14 — pile-up behavior needs observation.
5. **Scoped build false-completed** — fixed c9e4ee69 (`_scoped_global_progress`).



Remaining legacy OCR issues (carried forward):
- **Architecture Audit #131/#132:** **accepted and closed** (commits `73a782cf`, `078dd8a7`, `963cc59a`, `79b96d3d`, `5f03051e`, `d6c9afb0`).
- **#125 canonical abstract island:** **closed** via triage closeout (implemented at `687b3fea`/`1f02281b`, verification recorded, corpus differential 11/398 stable).
- **Triage classification (2026-08-05, per #130):** `active` — #127 (sole `ready-for-agent`), #126, #129 (product lane, chained). `owner decision` — #81 (release gate), #99 (redo-safety path reconfirmation after #129; absorbed #102). `deferred` — #63 (parent; protocol shape absorbed by #126/#127), #82 (N+2 deletion), #94–#98/#100/#103–#105 (Wayfinder, frozen post-release; #101 superseded→#126, #102 superseded→#99). #133/#134 (architecture tooling) — **unblocked by owner directive 2026-08-06; #133 active, #134 blocked by #133**. The 25 full-suite Windows sandbox-lock errors are environmental and unchanged (absent on the 2026-08-06 full run).

## 4. Active Queue

0. 🔒 **M4 Release Candidate validation** — S1–S6 lightweight disposable certification **COMPLETE** on `EXECUTABLE_FROZEN 462398cb` (docs `PROTOCOL_DOCS 781910f3`): `46c4ddaf` and `b66fde53` are already ancestors of `462398cb` (ahead 21/18), so no reconstruction is needed; `781910f3` adds only 2 docs commits. No RC blocker in current lightweight invariants (see §2.12, `project/current/cert-462398cb-S1-S6-matrix.md`). Full RC matrix `2026-08-17` `OWNER GATE` / `EVIDENCE OPEN` rows (plugin managed-runtime browser, Release-N reinstall, full S6) remain open. Local full suite `3312/0` green; hosted exact-SHA CI pending (do not claim `14899168` as `462398cb` evidence). **#81 remains open + `ready-for-human`; #191 remains `ready-for-agent` (FROZEN) without product code change; no release/tag/package publication.**
0.1. ⏳ **Reconcile-only render-result hardening** — identity census and blocking are complete; D1 R promoter is implemented and verified against isolated manifests. No front OCR/render code changed and no production write ran. **Next: crash-injection/recovery checks and stratified R canaries; no batch promotion.**
1. ✅ **[Architecture Audit #131/#132](https://github.com/LLLin000/PaperForge/issues/131)** — **accepted and closed** (Slices A+B; commits `73a782cf`–`d6c9afb0`). Audit report hardened v1→v4 (`e94895a1`→`7567dd2c`), third external review BLOCKER fixed: `repository_state` now semantic Survey content, Audit single gate authority.
1. ✅ **[Product lane #127/#126/#129/#99](https://github.com/LLLin000/PaperForge/issues/127)** — all four **accepted and closed** (next_actions policy, OCR Workspace closure, restore semantics, redo internal-only). Product lane complete.
2. ✅ **[#133 Deterministic collectors](https://github.com/LLLin000/PaperForge/issues/133)** — **ACCEPTED and closed** (owner acceptance 2026-08-07). Python AST + TS compiler collectors + orchestrator → Survey → #131 `reconcile()`; three-tier extraction, fail-closed coverage, unresolved-evidence seam. `collectors.deterministic` Contract lifecycle promoted planned→active at `3eb17ae9`.
3. ✅ **[#134 HTML + CI gate](https://github.com/LLLin000/PaperForge/issues/134)** — **ACCEPTED and closed** (owner acceptance 2026-08-07). Self-contained HTML projection + deterministic gate (Audit-only; allowlist empty until rules reviewed low-FP); independent L4b CI job; Pages fail-safe.
4. 🔒 **[Execution queue](https://github.com/LLLin000/PaperForge/issues/130)** — architecture-tooling lane complete. **Next: RC manual real-vault testing (owner) → #81 release.** Post-acceptance enhancements tracked separately: authority facts (3 role_authority rules), remote-intent literal-argv refinement, generation lineage (design published). Wayfinder #94–#105 frozen (deferred); #82 deferred.
5. ✅ **[Control Center target-state Map #94](https://github.com/LLLin000/PaperForge/issues/94)** — map reconciled and verified; children #95–#105 **frozen** (deferred until post-release).
6. ✅ **[Control-center redesign PRD #83](https://github.com/LLLin000/PaperForge/issues/83)** — #84–#93 implementation is merged to `master`, browser-audited page by page in English and Chinese, and deployed to Literature-hub for owner acceptance.
7. 🟡 **Release cutover #81/#82** — N+1 code is verified on `master`; #81 stays `ready-for-human` for the **owner-controlled release gate** (RC acceptance now owner manual real-vault testing); N+2 deletion #82 stays open until a probe-capable N+1 package and support window exist (**deferred**). No release is authorized.
9. ✅ **[Capability-state vocabulary](https://github.com/LLLin000/PaperForge/issues/69)** — resolved at `issuecomment-4971161072`. Orthogonal availability/activity/attention axes, 6-state capability ordinal, 12 canonical verbs, backend-owned severity and primary actions, maintenance projection.
10. ✅ **[Managed runtime](https://github.com/LLLin000/PaperForge/issues/70)** — resolved at `issuecomment-4971239398`. Plugin-managed immutable runtime slots, system-Python bootstrap with validated-triplet fallback, single `active-runtime.json` pointer, `ManagedRuntime` class with `current()`/`status()`/`ensure()`, fail-closed command resolution.
11. ✅ **[Control-center prototype](https://github.com/LLLin000/PaperForge/issues/71)** — resolved with independent Critical/Important PASS review and browser verification at 768px. Six-module control-center HTML prototype covers 5 scenarios with plain-button switcher, primary attention zone, responsive layout, and capability-gated actions. Design decisions recorded in `docs/prototypes/2026-07-14-six-module-control-center.html/.md`. No production implementation before #73.
12. ✅ **[Maintenance prototype](https://github.com/LLLin000/PaperForge/issues/72)** — resolved with independent Critical/Important PASS review and browser verification at 768px. Actionable-only inbox with single-action rows, inline issue-draft review, local redacted export, and confirmation-first report flow. Design decisions recorded in `docs/prototypes/2026-07-14-maintenance-issue-reporting.html/.md`.
13. ✅ **[Migration and acceptance contract #73](https://github.com/LLLin000/PaperForge/issues/73)** — closed after five-domain code audit, user grilling, and independent acceptance reviews. The implementation frontier moved to PRD #74 and child issues #75–#82.
14. 🟡 **Downstream tooling** — section-aware chunking and separate figure/table handling (**deferred**).
15. ⏳ **Compatibility naming cleanup** — deferred post-release.
### 4.1 Immediate Next Steps

**EXECUTABLE_FROZEN `462398cb` / PROTOCOL_DOCS `781910f3` — frozen, no candidate reconstruction.** `462398cb` after `781910f3 → 7a1e62f9 → 462398cb` has no executable commits beyond the freeze; `46c4ddaf`/`b66fde53` already in `462398cb`. Owner Closure is **evidence-only** — only a violation of the current release invariant may break the `462398cb` freeze. `Source Routing` / `Visual Evidence Serving` / `#191` remain post-RC.

**Final 5 owner bands (RC matrix fixed):**
1. **Plugin / Managed Runtime browser** — verified runtime, stale runtime, non-ready runtime, restart, stale/malformed cache, frontend must fail-closed (no fallback to old owner)
2. **Live process / cancellation** — mixed outcomes, Ctrl+C / SIGTERM, exactly-one terminal, scoped embed/retrieve live smoke, cancel → no continued mutation
3. **Full S6** — stale pointer, malformed pointer, offline, interrupted update, OCR resume, embed resume, restart → authority still consistent
4. **Release-N reinstall** — truly install previous release, verify N+1 → N recovery on existing vault, explicit support window (not just “installs”)
5. **Hosted CI @ exact `462398cb`** — Actions run/job bound to exact SHA; until evidence, record `local 3312/0 green / hosted pending`. Hosted must cover `Python 3.11` (minimum supported) + one mainstream newer (disposable cert used `3.14.0` — proves 3.14 runs but does not replace 3.11 evidence).

**M4 sequence:**
- [x] Close the recovery incident and Control Plane Closure in the ledger.
- [x] Freeze the RC snapshot: candidate SHA, version, Python/plugin bundle, schema/identity versions, and production census.
- [x] Run the local static release gate: Python, candidate plugin vitest/typecheck/build, architecture-boundary unit tests, destructive-delete guard, registry invariants, and version contract.
- [x] Close hosted CI evidence: validation ref `14899168` passed all 14 jobs, including macOS unit/J-matrix and `All Checks Passed` (historical; not exact `462398cb` evidence).
- [x] Repair the retrieval-integrity and frontier-parity blockers in commit `46c4ddaf`; focused lineage/reconcile/embed/action checks **126 passed / 1 warning**; no re-OCR/rebuild/embed for valid materializations.
- [x] **S1–S6 lightweight disposable certification on `462398cb`** (worktree `.cert-462398cb`, `pf-cert-s2-minimal` 2-paper) — S1 Foundation READY independent, S2 no-client Core passes without `.obsidian`, S4 maintenance honest, S5 confirmation boundary, S3 journey without Obsidian, S6 corrupt→valid recovery. **No RC blocker.** Matrix `project/current/cert-462398cb-S1-S6-matrix.md` (*lightweight, not a full RC matrix rerun*).
- [x] Synchronize **#191 PRD** to frozen contract (stale-plan `observation_fingerprint`+`plan_hash`→`setup.plan_stale`, verified-switch `relocate`, single-call `inspect` + `external_action`/`secure_external`) via `gh issue edit`; keep `ready-for-agent` without product code change.
- [ ] **Band 5: Exact-SHA hosted CI @ `462398cb`** — provide Actions run/job for exact SHA (`local 3312/0 green / hosted pending` until then; must include `3.11` + newer).
- [ ] Review the deterministic collector's six unresolved active rules and two advisory wrapper findings as post-RC architecture-tooling debt; do not mutate `462398cb` without an owner-approved blocker.
- [x] Run disposable fresh-install, existing-vault migration, config rollback fail-closed, offline, credential, and schema-v2 gates (M4 original + S1/S2 lightweight).
- [x] Run fresh-vault and existing-vault end-to-end CLI/user-chain smoke; interruption/cancel and true scoped-embed paths remain pending for full S6.
- [ ] **Bands 1–4:** Plugin/Managed Runtime browser, Live process/cancellation, Full S6, Release-N reinstall + support-window (see 5 bands above).
- [ ] Owner decides release version, publication, and support window; keep #81 open until that decision.

- [x] OCR rebuild streaming protocol
- [x] Canonical All/Recommended maintenance filters
- [x] Selected batch rebuild/redo with cooperative stop
- [x] Live Literature-hub plugin verification
- [x] Grill and domain-model the control-center destination
- [x] Create the Wayfinder map, eight child tickets, and native dependency graph
- [x] Audit current setup, readiness, recovery, cache, and migration contracts ([#66](https://github.com/LLLin000/PaperForge/issues/66))
- [x] Study Obsidian-native setup/settings patterns ([#67](https://github.com/LLLin000/PaperForge/issues/67))
- [x] Study desktop installation/health/recovery patterns ([#68](https://github.com/LLLin000/PaperForge/issues/68))
- [x] Define capability-state vocabulary and managed-runtime architecture ([#69](https://github.com/LLLin000/PaperForge/issues/69), [#70](https://github.com/LLLin000/PaperForge/issues/70))
- [x] Add canonical per-row action routing and redo confirmation gates
- [x] Prototype six-module control center ([#71](https://github.com/LLLin000/PaperForge/issues/71))
- [x] Design actionable-only maintenance inbox ([#72](https://github.com/LLLin000/PaperForge/issues/72))
- [x] Publish PRD #74 and eight agent-ready issues (#75–#82) with native dependencies
- [x] Canonicalize setup/config migration ([#75](https://github.com/LLLin000/PaperForge/issues/75)) — 61 focused tests; spec PASS; quality APPROVED
- [x] Implement Installation/Help capability tracer ([#76](https://github.com/LLLin000/PaperForge/issues/76)) — 21 backend tests; 169 plugin tests; typecheck/build clean; independent review PASS
- [x] Implement Managed Runtime lifecycle and the approved Installation-detail navigation shell ([#77](https://github.com/LLLin000/PaperForge/issues/77)) — 192 focused + 289 full tests; typecheck/build clean; merged to `master`
- [x] Expose Library, OCR, and Memory capabilities end to end ([#78](https://github.com/LLLin000/PaperForge/issues/78)) — 65 backend tests + 178 focused plugin tests, 324 full plugin tests across 11 files; typecheck/build clean; fail-closed recognizable config for Library/OCR; red rebuild_result stays non-destructive rebuild; queued OCR progress starts at 0; failed/null Library sync exit outcome is forwarded into fresh Python probe and remains sync actionable
- [x] Implement SecretStorage for capability secrets ([#79](https://github.com/LLLin000/PaperForge/issues/79)) — backend-focused gate passes; plugin full suite passes; typecheck/build clean
- [x] Implement Maintenance probe with backend-derived rows, privacy-safe local draft, and accessible destructive confirmation ([#80](https://github.com/LLLin000/PaperForge/issues/80)) — backend focused gate 77/77; plugin full suite 381/382 (only pre-existing capability-state test expecting help.stale but receiving help.invalid_response); typecheck/build clean; production bundle 264.4KB; real Obsidian 1.12.7 smoke at 730 and 768 confirmed actionable-only rows, keyboard Enter, accessible destructive confirmation with exact backend effect, focus trap/restoration, owned inert cleanup, redacted editable issue draft, no token input/auto-open, explicit GitHub open only, URL re-redaction, no horizontal overflow
- [x] Complete and verify Release N+1 implementation code ([#81](https://github.com/LLLin000/PaperForge/issues/81)) — 390/390 plugin tests, typecheck/build clean, live managed dispatch verified; issue remains open for the release gate.
- [ ] Complete Release N+2 deletion ([#82](https://github.com/LLLin000/PaperForge/issues/82)) only after an N+1 package and support window; publication is currently deferred by owner direction.
- [x] Implement redesign PRD [#83](https://github.com/LLLin000/PaperForge/issues/83) and issues #84–#93; verify every Overview, Module Detail, Maintenance, Help, and Setup Journey page in English and Chinese; deploy the corrected bundle to Literature-hub.
- [x] Reconcile Map #94 prototypes, `DESIGN.md`, responsive behavior, and FE/BE field/action mapping; verify interactions and visuals at 375/768/1280.
- [x] Separate Foundation runtime/package installation from Library configuration; deploy and live-verify that a Foundation run does not change `paperforge.json`.
- [x] Align Setup Journey Stage 3 with the prototype: selected OCR, Smart Retrieval, and Agent cards expand their credential/model/platform configuration in-flow; scope Smart Retrieval credentials to the selected API endpoint/model profile; deploy and live-verify.
- [x] Bind Smart Retrieval SecretStorage credentials to Base URL + model profiles; reject injection for an unsaved profile and leave unscoped legacy keys unavailable rather than guessing their profile.
- [x] Refresh Foundation and Library prerequisites on entering Setup Journey Stage 4; live-verify a configured journey reaches enabled completion after plugin reload.
- [x] Gate Foundation readiness on the loaded plugin version and clear stale reinstallation intent; live-verify exact match has only enabled Continue and mismatch produces a forced reinstall path.
- [x] Preserve Smart Retrieval’s stale-index rebuild action in the UI; derive Agent availability from deployed skills and suppress only migration warnings resolved by an active secure profile.
- [x] Implement R — read-model cutover + snapshot retirement ([#161](https://github.com/LLLin000/PaperForge/issues/161)) — Python 2939 passed, vitest 465/465, tsc/ruff clean; J-matrix wired in CI (#146); contract promoted (read models active, snapshot deprecated, CANONICAL_READ active/advisory); review closure `f14285cd`; CI all green; pending merge.
- [ ] Implement Wave 1 issues #97, #99, and #100; run issue-specific backend/plugin gates and real Obsidian smoke before any deployment.
- [x] Split architecture-audit epic #130 into slices #131–#134 and enforce the execution queue (one `ready-for-agent`).
- [ ] Implement #131 (code complete — final review passed; commit/acceptance pending), then accept it and promote #132 to `ready-for-agent`; after #132, run the mandatory open-issue triage checkpoint recorded in #130.
- [ ] Keep #127/#126/#129/#99 blocked until the triage checkpoint completes; never implement a `blocked` issue.

## 5. Key File Map

### 5.1 Production Code (OCR Pipeline)

| File | Role |
|------|------|
| `paperforge/worker/ocr_blocks.py` | Raw + structured block generation; legacy normalize path plus `normalize_mode=\"seed_only\"` for v3 |
| `paperforge/worker/ocr_roles.py` | `assign_block_role()` — seed/proposal logic only (NOT final) |
| `paperforge/worker/ocr_document.py` | `normalize_document_structure()` — anchor/family/zone + gate + final roles |
| `paperforge/worker/ocr_pre_match_normalize.py` | V3 candidate-only normalize; fills `role_candidate` while preserving public `role = seed_role` |
| `paperforge/worker/ocr_post_match_normalize.py` | V3 post-match role commit; shadow normalize + rescue equivalence + tail settlement |
| `paperforge/worker/ocr_object_writeback.py` | Post-inventory ownership-evidence seam for figure/table assets, contained text, and side-adjacent figure text |
| `paperforge/worker/ocr_tail_settlement.py` | Tail/body/backmatter settlement seam + `TailSettlementReport` |
| `paperforge/worker/ocr_structural_gate.py` | `VERIFY_REQUIRED` role decision + abstract span + reference zone + health |
| `paperforge/worker/ocr_orchestrator.py` | Body reorder, column validation, layered assembly |
| `paperforge/worker/ocr_render.py` | `render_fulltext_markdown()` — skips consumed object-owned blocks and consumes verified artifacts only |
| `paperforge/worker/ocr_health.py` | Health reporting, merged gate summary |
| `paperforge/worker/ocr_profiles.py` | Span extraction, profile aggregation, cross-validation |
| `paperforge/worker/ocr_figures.py` | Figure reader pipeline + `role_candidate`-aware match-time role resolution |
| `paperforge/worker/ocr_tables.py` | Table inventory matching + `role_candidate`-aware match-time role resolution |
| `paperforge/worker/ocr_scores.py` | Score functions (spatial, structured_insert, etc.) |
| `paperforge/worker/ocr_rebuild.py` | Derived rebuild entry point |
| `paperforge/worker/ocr_pdf_spans.py` | PDF span backfill for OCR-missed blocks |
| `paperforge/worker/ocr_bio.py` | Author biography detection utilities and passes |
| `paperforge/worker/ocr_quality.py` | Quality indicators builder (5 normalsers) + readiness policy evaluator |
| `paperforge/worker/ocr_quality_feedback.py` | Human feedback sidecar (per-mark hash, stale detection, append-only) |
| `paperforge/policies/ocr_readiness_v1.yaml` | Default readiness policy (weights, hard-red rules, use-case gates) |

### 5.2 Test Files

| File | Purpose |
|------|---------|
| `tests/test_ocr_figures.py` | Figure inventory, matching, ownership |
| `tests/test_ocr_document.py` | Document structure, normalize, gate |
| `tests/test_ocr_render.py` | Fulltext render contract |
| `tests/test_ocr_figure_reader.py` | Reader contract |
| `tests/test_ocr_trace_vs_expectations.py` | Real-paper trace vs expectations gap report (8 gold papers) |
| `tests/test_ocr_real_paper_regressions.py` | Page-level + document-level regression on real papers |
| `tests/test_ocr_real_paper_audit_contracts.py` | Gold-fixture quality gate |
| `tests/test_ocr_spec_contracts.py` | Architecture contract tests |
| `tests/test_ocr_structural_gate.py` | Gate unit tests |
| `tests/test_ocr_v2_structural_regressions.py` | Structural regression guards |
| `tests/test_ocr_layout_first_regressions.py` | Layout-first behavior guards |
| `tests/test_ocr_object_writeback.py` | Ownership-evidence seam, consumed-block contract, contained/side-adjacent text, cross-page `block_id` guard |
| `tests/test_ocr_tail_settlement.py` | Tail/body/backmatter extraction seam + `TailSettlementReport` |
| `tests/test_ocr_pipeline_v3.py` | `OCR_PIPELINE_V3` toggle, seed-only mode, pre/post normalize split, parity gate |
| `tests/test_ocr_quality.py` | Quality indicators (17 tests: shape, thresholds, health_profile, inventory precedence, run_integrity) + readiness policy (7 tests: default, hard-red, gates, YAML, merge) |
| `tests/test_ocr_quality_feedback.py` | Human feedback sidecar (5 tests: roundtrip, hash validation, append, stale, resolve) |
| `tests/test_appendix_figure_numbering.py` | Appendix figure/table numbering regressions including M84CTEM9 coverage |

### 5.3 Test Fixtures

`tests/fixtures/ocr_real_papers/{CAQNW9Q2,DWQQK2YB,TSCKAVIS,A8E7SRVS,K7R8PEKW,6FGDBFQN,SAN9AYVR,2GN9LMCW}/`

### 5.4 Design Documents

| File | Purpose |
|------|---------|
| `docs/superpowers/specs/2026-06-08-ocr-anchor-first-structured-parsing-design.md` | Architecture spec |
| `docs/superpowers/specs/2026-06-13-ocr-real-paper-regression-and-spec-realignment-design.md` | Current phase spec |
| `docs/superpowers/specs/2026-06-10-ocr-figure-reader-contract-design.md` | Figure reader spec |
| `docs/superpowers/specs/2026-06-23-ocr-visual-grammar-hardening-design.md` | Visual grammar hardening |
| `docs/superpowers/specs/2026-06-27-figure-containment-and-backmatter-boundary-design.md` | Current P0/P1 spec |
| `docs/superpowers/plans/2026-06-18-ocr-v2-readiness-master-plan.md` | Readiness gates master plan |
| `docs/superpowers/specs/2026-07-05-ocr-quality-report-design.md` | Layer 2 design spec — quality indicators, readiness policy, feedback sidecar |
| `docs/superpowers/plans/2026-07-05-ocr-quality-report-plan.md` | Layer 2 implementation plan (3 PRs + contract polish) |
| `docs/superpowers/plans/2026-06-17-ocr-v2-closeout-single-plan.md` | Close-out single plan |
| `docs/superpowers/plans/2026-06-15-group-first-figure-inventory-plan.md` | Group-first figure refactor (deferred) |
| `docs/superpowers/specs/README-ocr.md` | OCR design index |

### 5.5 Active Truth Files

| File | Role |
|------|------|
| `project/current/ocr-v2-active-queue.md` | **Active queue** — next-work authorit |
| `project/current/ocr_rebuild_audit.md` | Evidence source for queue |
| `project/current/ocr-v2-generalization-boundary.md` | Architecture boundary note |
| `project/current/ocr-v2-remaining-issues-2026-06-18.md` | Historical readiness residuals |


## 6. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-17 | Recovery + Control Plane Closure | Recovery CLOSED: frozen 958-paper census, 938 OCR/retrieval current, 935 vector-current + 3 `no_content`, serving smoke verified. M1/M1.1/M2/M3 CLOSED; architecture frozen; M4 RC gate matrix and owner decision are now the only active work. | §2.4–§4 |
| 2026-08-17 | M4 lifecycle evidence and non-blocker classification | Disposable fresh/existing chains, schema migration, fail-closed config rollback, offline failure, stale-state tests, plugin static checks, and safety scan passed. The remaining stdout relay, managed-runtime/UI, cancellation, scoped-embed, CI/checksum, and real Release-N reinstall items remain RC evidence/owner gates; no candidate code or materialization change is justified. | RC matrix |
| 2026-08-18 | Cache canonical PDF lookup per lineage observation | Full sync was reparsing the 4 MB canonical index once per paper inside the lineage loop. Build one observation-scoped PDF map instead; preserve per-paper semantics while reducing the measured full reconcile from 144.61 s to 48.38 s. No materialization rerun is required. |
| 2026-08-20 | S1–S6 lightweight disposable certification on 462398cb | Executed S1→S2→S4→S5→S3→S6 on disposable minimal fixtures (pf-cert-s1-vault + pf-cert-s2-minimal, worktree .cert-462398cb, venv pf-cert-s1-venv, docs 781910f3). No RC blocker in current invariants; Foundation READY independent, no-client Core passes without .obsidian, confirmation boundary enforced, vector 401 is explicit fail-closed. #191 gaps are real (skill deploy in SetupPlan, retired config fields, missing inspect/plan/apply/verify + plan_stale + verified-switch relocate + external_action). Full RC owner gates (plugin browser, Release-N reinstall) remain open. Matrix: project/current/cert-462398cb-S1-S6-matrix.md. |
| 2026-08-20 | Freeze `EXECUTABLE_FROZEN 462398cb` / `PROTOCOL_DOCS 781910f3` and 5 owner bands | Commit graph `781910f3 → 7a1e62f9 → 462398cb` has no executable commits beyond freeze; `46c4ddaf`/`b66fde53` already in `462398cb` (ahead 21/18), `781910f3` is 2 docs commits. Mode switches to **Owner Closure evidence-only** — only a violation of current release invariant may break `462398cb`. Final 5 bands fixed: 1) Plugin/Managed Runtime browser (verified/stale/non-ready/restart/stale+malformed cache, fail-closed), 2) Live process/cancellation (mixed outcomes, Ctrl+C/SIGTERM, exactly-one terminal, scoped live smoke, cancel→no mutation), 3) Full S6 (stale/malformed pointer, offline, interrupted update, OCR/ embed resume, restart authority), 4) Release-N reinstall (true N install + vault recovery + support window), 5) Hosted CI @ exact `462398cb` (`local 3312/0 green / hosted pending`, must cover `3.11` + newer; disposable `3.14.0` does not replace `3.11`). `Source Routing`/`Visual Evidence`/`#191` remain post-RC. |
| 2026-08-20 | Fix `AGENT_SKILL_DIRS` F821 → `a42f8bb7` | Exact `462398cb` hosted `32269242351` failed `L0.5 — Ruff F821` at `setup_wizard.py:520` (dead legacy body after `SetupPlan` delegation still referenced undefined `AGENT_SKILL_DIRS`). Fix: remove dead block 495-909 (415 deletions), `ruff --select F821,F822,F823` clean, `setup_wizard` 68 passed. `Impact: re-OCR none / rebuild none / embed none` — dead code, no behavior change; `462398cb` lightweight S1–S6 evidence remains valid for `a42f8bb7`. New `EXECUTABLE_FROZEN a42f8bb7`, `PROTOCOL_DOCS 781910f3` unchanged. |
| 2026-08-20 | Owner-closure verification refresh | Hosted CI `32353318123` completed **All Checks Passed / 14 of 14** on docs-only descendant `a2e18fa4` (no executable change after `a42f8bb7`); package-install smoke from `pip install .` passed `paperforge --version`, `status`, `action list`, `memory build`, `paper-status`, and `read` on a clean disposable fixture; cancellation/runtime/recovery focused suites passed **75 passed, 1 skipped**. `1.5.14` on a fresh copy of the fixture passed `status` and `paper-status` against `1.5.15`-shaped data. Remaining evidence-only items: real Obsidian Managed Runtime browser, live provider Ctrl+C/recovery, and Release-N support-window owner decision. |
| 2026-08-21 | Render consistency remains report authority; unified probe only projects it | Full read-only audit showed 5304/5527 findings in `render_layer`. The investigation must reuse existing canonical inventory, renderer, PDF resolver, and persisted `render.consistency.json`; `probe lineage` exposes `details.render_consistency` without recomputing or creating a second materialization state. `render reconcile` stays deferred until the historical crop/write gap is explained. |
| 2026-08-21 | Add materialization provenance at the existing object seam | `_crop_asset_from_pdf` retains its default bool contract while `return_result=True` records stage/reason; object tasks write additive `render/materialization.provenance.json`; audit and `probe lineage` only project this result. No renderer behavior, OCR truth, inventory, or production artifact was changed; no reconcile/rerender ran. |
| 2026-08-21 | Fresh provenance corpus before renderer repair | Ran 20 disposable cases through the shared object materializer and render-output audit (10 historical materialization-missing, 5 CLEAN, 5 dangling). The sampled historical missing figures materialized successfully with resolved PDFs; no production rebuild or reconcile is justified yet. |
| 2026-08-21 | Add render position evidence to consistency audit | Reuse existing inventory fields and structured block geometry to expose legend/object/asset pages, page ranges, relations, legend block IDs, and bboxes. Cross-page position is now reported; no matching or canonical truth is changed. |
| 2026-08-21 | Exact repair dry-run is plan-only until fresh provenance | All 3619 exact candidates passed persisted planning gates except that none were execution-ready because production provenance is missing. An initial ownership check exposed page-local block-ID duplication in 9 continuation objects; correcting the key to `(page, block_id)` removed the false blocks. No file was changed. |
| 2026-08-21 | Full exact materializer dry-run found page-validity blocker | Disposable staging verified 3618/3619 exact objects; `2ZBAK9VY/figure_003` correctly failed closed because inventory page 9 exceeds the resolved PDF's 8 pages. Add PDF page-range validation before any bounded repair apply; no production mutation. |
| 2026-08-21 | Freeze three-bucket reconciliation report | Reconciliation emits only `exact_repairs`, `proposals`, and `blocked`; exact repairs reference existing canonical IDs and render-only scope, proposals never create canonical objects, and blocked cases carry review reasons. 388XI46Q validates 8 supported labels / 6 canonical / 2 proposals / 5 reservation blocks. |
| 2026-08-21 | Bounded-slot proposal dry-run | All 128 canonical-missing proposals were tested with existing group outputs, anchor slots, ownership filtering, and optional PDF media. 37 were structurally unique with PDF confirmation, 1 unique without PDF confirmation, and 90 blocked. No canonical or render writes occurred. |
| 2026-08-21 | Proposal preview dry-run | All 38 structurally unique canonical-missing proposals were materialized in temporary staging and passed image/markdown/provenance/PDF-slot checks plus CLEAN staging audit. No proposal was promoted to canonical or production render. |
| 2026-08-21 | Publish audit from shared render-output boundary | `write_render_outputs` now invokes the existing read-only `audit_paper` after `fulltext.md`/`render-map.json`; initial OCR and derived rebuild paths therefore publish the same report. Audit exceptions are warning-only, so this adds observability without changing render behavior or opening reconcile. |
| 2026-08-21 | Add one-sided anchor and claim-exclusivity gates to slot dry-run | Owner review caught same visual group claimed by multiple proposals (e.g. `K6EBNFNK`, `6ZWKUPCU`, `IGR5PYH2`) and candidates outside a lower-only anchor's direction. Corrected rerun: 40 unique with PDF confirmation, 2 without, 86 blocked; duplicate-claim audit empty. |
| 2026-08-21 | Visual claim identity + anchor page-range gates for slot dry-run | Owner review caught cluster/member-asset double-claim risk and single-page anchor bounds. Gates now use member block refs and anchor page ranges. Rerun: 40 unique with PDF confirmation, 2 without, 86 blocked; transition from first pass = 31 retained / 9 new / 6 removed. No writes. |
| 2026-08-21 | Preview-stage the corrected unique set | All 42 current unique candidates (40 with + 2 without PDF confirmation) were materialized in temporary staging: **42/42 preview-verified, 42/42 CLEAN audits**, 33 unmatched-asset and 9 unresolved-cluster candidates across 39 papers. No canonical or production render writes. |
| 2026-08-21 | Freeze human review census rules before review | Primary precision = confirmed/40 (uncertain in denominator), secondary = 2 no-PDF candidates, five decision categories, minimum provenance fields. Rules frozen before any image is viewed to avoid post-hoc criteria. File: project/current/human-review-census-rules.md. |
| 2026-08-21 | Vision-assisted 42-case census completed | minicpm-v4.6 reviewed all 42 candidates against PDF pages: **38 yes, 2 no**. Primary precision (confirmed/40) = **38/40 = 95%**. Both no-PDF-confirmation candidates also confirmed. The 2 failures are both `unmatched_asset` Figure-1 cases where a QR code / chemical schematic was picked instead of the true figure. Artifact: local://reconciliation-census-final.json |
| 2026-08-26 | Keep reconcile independent from front OCR/render | The 965-paper census found 250 duplicate canonical figure-ID groups, but the safe response is not to alter `ocr_figures.py`, `ocr_objects.py`, `ocr.py`, or `ocr_rebuild.py`. Reconcile now observes inventory conflicts, blocks ambiguous R/P plans, and passes only selected R plans into isolated staging; unique front-render behavior remains untouched. |
| 2026-08-26 | D1 R promotion is manifest-gated but rollout-blocked | R promotion consumes only a reconcile-generated `r-manifest.json`; it never re-materializes and never edits canonical inventory. G0–G7 validate snapshot, unique identity, exact ordered refs, ownership, fixed paths, staged image/markdown facts, link, provenance, and plan hash. Atomic per-file replacement and idempotent rerun are verified; multi-file crash recovery and canaries remain mandatory before batch use. |
| 2026-08-16 | Every code change must annotate re-run requirements + old-user impact | During recovery, un-annotated changes forced repeated remote OCR/embed runs ("白费力气" — owner). Commit bodies now carry `Impact: re-OCR / rebuild / embed: none|keys|all` + `old users:` so the operator batches or skips re-runs correctly. Recorded §7.3.1. |
| 2026-08-16 | Two-tier tool surface: stable CLI + deep dev API, never per-task `python -c` | Recovery diagnostics repeatedly re-invoked internal functions via ad-hoc `python -c` (read_index / _resolve_canonical_pdf / compute_ocr_result_hash / provenance_state) — works but is not a stable surface. Product/plugin/agent face the frozen `paperforge <cmd>` CLI (registry actions + probe; fixed args, JSON/NDJSON schemas); developer/advanced-user diagnostics may stay deeper but must be reachable through a FIXED script or dev command, not per-task inline code. Implement post-recovery (owner: "不急"). |
| 2026-08-16 | Goal/ensure orchestrator: agreed direction, deferred post-recovery (attachment review) | External review of the post-incident architecture: actions stay atomic primitives; a thin `ensure <goal>` layer (ocr.current / retrieval.current / vector.current / serving.ready) plans from observation and re-observes after each action (the chain.py pattern generalized); reconcile must stop giving global substrate unconditional priority (embed.build was once the only frontier while 684 OCR were broken); read paths never auto-repair. Direction correct — the 70% substrate already exists (lineage observe + reconcile plan + chain execute). Deferred: recovery batches + RC must finish first; no new orchestration during data repair. |
| 2026-08-15 | Deleting = moving to trash; raw filesystem deletes are forbidden | 2026-08-14 incident: `shutil.rmtree(Path(), ignore_errors=True)` deleted the production vault root (Path() = cwd; ignore_errors swallowed everything). PaperForge now deletes user data ONLY via `worker/trash.py` — a move into `.paperforge/trash/<ts>/<id>/` + manifest, restorable (`paperforge trash restore`); `validate_target` fails closed on empty paths, `.`, the allowed root, and escapes (junctions resolved first); `purge_trash` is the only true delete, restricted to the trash root. "An agent may decide an OBJECT should be deleted, but never which filesystem PATH is recursively deleted — that goes through capability validation + quarantine." |
| 2026-08-15 | Pre-commit + CI reject accident patterns, not all deletes | Guard scope matters: banning every rmtree/unlink would break existing legit cleanup (ocr temp dirs, update tmp, test helpers) and limit development. The pre-commit check (`scripts/check_no_destructive_delete.py`) targets exactly the accident patterns: `rmtree(...ignore_errors=True)` and `rmtree(Path())`/`rmtree("")`/`rmtree(".")`. Ordinary explicit-path deletes stay allowed. Same check runs in pytest (CI) so both gates always agree. |
| 2026-08-15 | Unified residual signal: Zotero is the authority across ALL carriers | A paper removed from Zotero may leave residuals in workspace dir, papers FTS rows, vector meta, or OCR data. Detection is paper-level: key absent from Zotero exports + present in ANY carrier = residual (with per-carrier flags). One `library.prune` clears every carrier; execute per-carrier (files→trash, DB/vectors→transactional rowid-verified deletes) because FTS rebuild is free but vector rebuild is paid. |
| 2026-08-15 | UI renders from backend state machine, single source | The "811/811 built but API Key 未配置" contradiction came from the panel reading a stale plugin cache for one row and live data for another. Smart Retrieval panel now renders status text / button / info card / impact all from the probe envelope (reason.text + action.primary + details). No per-reasonCode frontend branches that can drift from the backend. |
| 2026-08-14 | Library orphans into the state machine — probe reports, reconcile prunes, frontend pops modal | User: "orphans should enter the state machine; popping the modal on the state beats following sync". Orphans (workspace papers absent from the canonical index) are now a first-class library state: `probe lineage` carries `orphan {count, keys, orphans[key,title]}` (reuses the prune scanner, ~0.5s); `probe all`'s maintenance envelope exposes it; reconcile emits `library.prune` (registered, confirmation-required, destructive, never automatic); the frontend consumes maintenance.orphan after every probeAll and pops the existing PaperForgeOrphanModal when orphans go 0→N (once, never every 120s tick; persistent orphans stay on the module card). The modal's hardcoded `python` was replaced with the plugin-resolved runtime (`_resolveRuntimeCommand`). Production: 5 orphans (9NTKAAXV/BKKR4KIV/NSV8KBJY/R2PSFXY4/VCPVA9Q6) now surface in probe + reconcile + will pop the modal on next Obsidian refresh. |
| 2026-08-14 | OCR FINAL corrective (review: 2 P0 + 3 P1 + residue) | P0-1: legacy meta `failed` dropped through to artifact checks (complete old artifacts would look current) — now `failed_legacy` → failed → ocr.run. P0-2: queued/running past zombie timeout (ocr_started_at + PAPERFORGE_ZOMBIE_TIMEOUT_MINUTES) → `queued_interrupted` → failed → ocr.run (was permanent wait since the worker's zombie-reset only fires on the next ocr.run). P1-1: reconcile keeps every detail's reason code (tree_invalid/role_index_*/publish_pending_stale map individually; failed_legacy/retryable/fatal separate) and NO ocr.run for blocked/no_pdf (no executable intent — the state machine says WHY via probe). P1-2: publish marker renamed publish_pending_recent/stale (honest: it's age, not liveness). P1-3: artifact checks now validate SHAPE (blocks first line must be a dict with block identity; tree root dict + nodes list of dicts; role-index dict with collection lists) — `["not a block"]` / `{"nodes":"hello"}` / `123` are invalid. Residue: duplicate `_ocr_detail` deleted, unused import removed, ruff clean (only pre-existing E501 in probe.py left). Tests: 19-case parameterized state-machine matrix (probe state + detail + reconcile action end-to-end) now permanent. |
| 2026-08-14 | probe_ocr driven by lineage state machine, maintenance demoted to quality overlay | probe_ocr reported `ocr.quality_failures` for 2 papers whose OCR merely produced empty blocks — the old maintenance health/display_action flags conflated "OCR not finished" with "OCR quality failed". Now the lineage probe is the authority: failed → ocr.run; incomplete → ocr.rebuild_derived; blocks_* → ocr.run; not_started → ocr.run; no_pdf → user action. Maintenance rows remain only as the independent quality/presentation overlay. Production: probe_ocr now correctly shows ocr.incomplete (9) + Rebuild OCR derived instead of a false quality failure. |
| 2026-08-14 | OCR state machine carries WHY: lifecycle + integrity + version semantics, never conflated | User: "state machine must capture the fine distinctions — failed vs version-old vs incomplete vs pending/queued/finish all have distinct meanings". `_probe_ocr_state` now reads meta.json's ocr_status (lifecycle authority: pending→not_started, processing→queued, failed→failed, nopdf→no_pdf) BEFORE artifact checks (ran_but_empty / tree_missing / tree_empty / version_old). probe lineage per-paper gains `details.{ocr,retrieval,vector}`; reconcile emits distinct reason_codes (lineage.ocr_missing / ocr_ran_but_empty / ocr_no_pdf / ocr_failed / ocr_tree_missing / ocr_tree_empty) and PaperObservation carries details. Production state machine: 802 current, 9 incomplete/tree_empty, 2 ran_but_empty, 1 no_pdf, 145 not_started — every paper's OCR state has a unique, non-confusable meaning. |
| 2026-08-14 | OCR incomplete state: missing/empty structure tree is INCOMPLETE, never current, never quality | 11 papers have a structure-tree.json with `nodes: []` (or missing) — OCR ran but the derived structure was never produced, so body units/structural coordinates cannot exist. Previously the probe reported these `current` (hash compute passed) and reconcile said nothing — the deficit was invisible. Now: `_probe_ocr_state` reports `incomplete` (distinct from `unknown`/`missing` and NEVER conflated with quality); retrieval/vector chain it; reconcile emits `ocr.rebuild_derived` (local derived rebuild, not `ocr.run` — there is no quality defect); the reader gate keeps serving already-materialized vectors of incomplete papers (real data, no regression) while missing-structure papers stay unsearchable. 3 of the 11 (9QKBD38Z/DLVSVU49/ZARNGKY7) have empty source blocks and cannot be rebuilt (unbuildable tree) — rebuild attempted, stays incomplete, reconcile converges via W2. Tests: 4 new (empty tree incomplete, missing tree incomplete, gate allows incomplete vectors). |
| 2026-08-14 | Legacy ChromaDB fulltext vectors get lineage: identity match = searchable | 1.5.x-era products (ChromaDB full-text, no structure tree/manifest) migrate to vec0 but were gated as unknown → upgrade silently lost their vector search (regression). Design: `write_legacy_fulltext_lineage` writes a lineage row with `derived_from=LEGACY_FULLTEXT_RETRIEVAL_ID` and `embedding_identity` = CURRENT endpoint/model + MIGRATED dimension. The probe's existing identity comparison becomes the compatibility oracle: unchanged config ⇒ same dimension/semantic space ⇒ `vector: current` ⇒ reader gate passes (zero gate change); config changed ⇒ `stale` ⇒ dropped + rebuild offered. migrate gains a dimension guard (skips different-model vectors with a warning, never forces into a mismatched table — vec0 rejects the insert anyway). Reconcile stays the single intent producer: legacy papers only get `ocr.run` (upgrade path); no spurious embed.resume/memory.build. 4 new tests (dimension skip, legacy current, legacy stale after config change). |
| 2026-08-14 | Zombie running without candidate keeps resume — no wasteful full rebuild | Zombie `status=running` (dead pid, no candidate) previously forced `resume=False` → full shadow rebuild re-embedding EVERY paper even when vectors exist. Now it marks `interrupted` and KEEPS resume=True; gates 门二 (no rows → fresh) / 门三 (model/identity changed → full) still decide: vectors + matching identity route in-place incremental (only missing papers embedded). Verified: zombie + vectors + matching identity → in-place, no shadow prepare; legacy/no-rows/model-change still shadow (existing tests pass). New test `TestZombieRunningIncremental`. |
| 2026-08-14 | Orphan check O(1) MAX(rowid) boundary, full scan only in doctor | Root cause of the embed "hang"/process pile-up/false-corrupt chain: `inspect_vector_layout` and `verify_candidate` ran a FULL `meta ⋈ vec0` LEFT JOIN for orphan detection — measured 48–117 s at library scale (16k/6.7k rows) because vec0 rowid lookups are slow (sqlite-vec #37/#196). Every status/probe/verify call hit it. Fix: orphan detection = `meta rows WHERE rowid > MAX(vec0 rowid)` (3 ms, O(1)); a vec table dropped/recreated restarts rowids at 1 so every stale meta rowid is provably beyond the new max — catches the only realistic corruption mode. Normal deletes sync meta+vec so no mid-range orphans occur. Full 100% LEFT-JOIN scan moved to `paperforge doctor` (manual, low frequency) with a fail check. Production verified: embed status 116s+ → 1.86s, probe 60s+ → 1.8s. |
| 2026-08-14 | DB busy is transient, never corruption | User saw "检索索引已损坏,请从备份恢复" (memory.db_corrupt) while the DB was healthy. Root cause: `get_memory_status` swallowed ALL exceptions — the reader-barrier mutex (10s timeout) timed out under plugin polling pile-up (8 stale `embed status`/`sync` processes queued on the shared `.read.lock`), returning `schema_ok=False, paper_count_db=0`, which the probe read as `memory.db_corrupt` → restore-from-backup prompt for a perfectly healthy DB. Fix: `_is_lock_failure()` distinguishes timeout/locked/busy; `get_memory_status` marks `locked`; probe returns new `memory.db_busy` ("busy, retry shortly") with a Retry action instead of corrupt. DB integrity verified ok after killing the stale processes. 2 new tests. |
| 2026-08-14 | Distinguish partial-build / identity-changed / failed vector states in UI text | User: "prompt text needs refinement — it should say partial build, not mode-expired; these details were never checked". `memory.vector_build_failed` was shared by both a failed build and an identity-changed substrate, and `memory.vector_build_interrupted` had NO UI status-text mapping (only the button), so a partially built index showed no explanation. Split: new `memory.vector_identity_changed` code ("Embedding configuration changed… rebuild"), interrupted text now says "Vector index is partially built: X/Y papers embedded. Resume to embed the remaining N papers" (no more redundant message repetition), failed text states already-embedded papers stay searchable. UI: settings maps the two new/under-mapped codes to i18n strings (EN+ZH). Rebuilt main.js and deployed to the production vault. 81 py + 408 vitest. |
| 2026-08-14 | Scoped builds must not claim global completed; resume feasible without candidate | User reported "index not complete but UI shows ready, no button". Root cause: the scoped incremental build (embed.resume --scope papers --key X) finished and wrote build_state `completed/1/1` — its own total is just the requested subset, so the probe's Gate 5a returned ready with no action while 728 papers still lacked vectors (false green light). Fix: `_scoped_global_progress()` recomputes GLOBAL progress (distinct papers with vectors vs done papers) for scoped completions and reports `interrupted` while missing → probe surfaces embed.resume again. Also `_resume_feasible()`: a surviving candidate always resumes (shadow-recover); without one, in-place incremental works when the substrate is compatible — only a global substrate defect with no candidate forces embed.build. Live library corrected (completed/1/1 → interrupted/83/811); probe now needs_action + embed.resume. 3 new tests. |
| 2026-08-14 | document_structure.json oversized-write guard + zone cap | 2026-07-06 OCR run produced 39 bloated document_structure.json files (up to 1.6 GB; WML2NNFE had 94.9M block_indices entries) from an abnormal in-memory blocks list. Current code is bounded (recompute: 215 blocks → 28 indices) and the file has no production reader, so the 39 files were deleted (2.97 GB freed) with zero lineage/retrieval impact. Guards: `DOC_STRUCTURE_MAX_BYTES` (5 MB) — oversized serialization skips the write with a warning instead of filling the disk; `_MAX_BLOCKS_FOR_ZONES` (100k) — zone detection degrades to no zones on implausible block counts so downstream never sees giant arrays. 3 new tests. |
| 2026-08-14 | Partial publish: probe offers embed.resume, scoped increments allowed | Side-effect audit of partial publish surfaced two issues, both fixed. ① probe Gate 5b/5c (zombie running / interrupted) hardcoded `embed.build` with a "Resume" label — clicking it force-rebuilt ALL papers instead of resuming; now `embed.resume` when a surviving candidate exists, `embed.build` ("Rebuild") only without one (mirrors Gate 5d). ② `_recover_candidate` made `requires_shadow=True`, so ANY papers-scope request failed fast even though recover never clears the candidate — the "new paper → incremental publish" path was dead while a candidate survived. Fix: fail-fast now exempts `_recover_candidate` (recover only ADDS rows), verifier skips count comparison for scoped builds (`expected_count=None`), recover's `_expected_dim` falls back to vec0 DDL. Verified live: `action run embed.resume --scope papers --key QIZUZJNX` → 1 paper embedded (33 chunks), published, lineage 83/83, retrieval current. |
| 2026-08-14 | Partial publish = checkpoint COPY, not replace | User asked "build a few vectors, don't fully rebuild; partial should be retrievable". Design gap: shadow publish was `os.replace(candidate → live)` which eats the candidate — a stopped build could never make embedded papers retrievable without finishing all 811. Fix: `partial_publish_shadow()` copies (not moves) the candidate onto live under the reader barrier; candidate survives for resume; the copied build_state carries model/endpoint/dimension/identity_version=1, which also unlocks incremental in-place builds (legacy gate clears). Stopped builds now publish whatever has vector rows. Hidden bug fixed in the same pass: resume builds never recreate vec tables so `_expected_dim`/`_stored_dim` stay 0 → `write_vector_lineage` silently wrote nothing (resume-completed publish would have had empty lineage → reader gate dropped everything); `_resolve_lineage_dimension()` falls back to the vec0 DDL self-declaration. Verified live: stop → partial publish → 82 papers current, lineage 82/82, deep retrieval returns real matches, papers-scope embed unlocked. |
| 2026-08-14 | Lineage probe: artifacts are authority, snapshots are cache | `_probe_ocr_state` returned `unknown` when `result-hash.txt` (publish snapshot) was missing even though the OCR artifacts were intact; `_current_embedding_identity` gated on `build_state.vector_dimension`, an external key that was cleared during test cleanup. Both violated DAG content-addressing (Bazel/Airflow): the identity must be recomputed from the artifact, and the embedding dimension must come from the vec0 DDL itself. Fix: snapshot-missing degrades to recompute; dim read from `sqlite_master` DDL with build_state as legacy fallback. Result: 3 test papers unknown→current, library `unknown: 0`, deep retrieval returns real matches. |
| 2026-08-10 | R read-model cutover: snapshot readers/writers deleted in one vertical slice | #148 frozen: fresh read models fully determine UI; zero dual-read; wrong-snapshot authority is the key acceptance |
| 2026-08-13 | RC UI audit authority rule | UI may project Python auth/probe/action state and active controller state, but must not recreate credential, policy, cancellation, or vector-health truth from cached booleans or legacy process fields. |
| 2026-08-13 | Paid remote actions use one policy and execution boundary | Python registry/probe owns cost, impact, and confirmation. TypeScript only localizes the consent copy, then routes OCR and embed through their shared controllers. No entry point may add a second confirmation or launch consent-required work from a background sync callback. |
| 2026-08-13 | RC full-surface functional smoke; two real-path fixes | Every top-level CLI command and plugin surface exercised once against the disposable vault. `foundation.update` always failed its remote version check (missing `import urllib.request`; unit tests mock `_remote_version` so the gap was invisible); doctor's skill importability check always false-WARNed on dataclass-bearing pf_deep.py (module not registered in sys.modules before exec_module). Root-cause fixes plus regression tests; `update --json` and `doctor` re-verified live. |
| 2026-08-13 | RC UX Seam Pass: no false affordances, no stale read models, no trapped setup | Settled mutations (embed terminal, workspace rebuild) always invalidate-all/probe-all; consent-required work lives in the module card durably. Setup Stage 1 is cancellable and exitable. Dead UI that could resurrect TS runtime authority (`pip install chromadb openai`) is deleted, not papered over. Foundation detail projects probe truth instead of hardcoded greens. |
| 2026-08-13 | RC UX Seam FINAL: setup steps ride the managed pointer; cancelled setup never publishes | Stage 2+ setup runs on the published runtime (never ambient python) and speaks NDJSON. Cooperative cancellation is checked between agent sub-steps and gated immediately before pointer publication — the one invariant (cancel ⇒ no publish) now holds even when SIGTERM lands mid-deployment. The plugin holds the setup child until close before allowing Retry. "Later" is a real exit via a session flag, resuming at the same stage on reopen. |
| 2026-08-10 | R review closure (7 findings) | P0: transport argv split (typed client), probeAll = 5 base + derived maintenance (#140), OCR defect-first hermetic order, C0 split PR #176; P1: invalidateAll→probeAll mutation flow, CANONICAL_READ active/advisory, envelope v3 debt pinned T2/T8 |
| 2026-06-10 | Separate figure reader from body prose | Figure info must be reader-visible without body pollution |
| 2026-06-11 | Install verified structural role gate | Spec was being bypassed; gate enforces seed≠final contract |
| 2026-06-13 | Dual-gate regression + spec-contract testing | Tests protected helper behavior, not real-paper outcomes |
| 2026-06-13 | Root-cause approach: no renderer patches | Heading merge goes in raw blocks; boundary detection fixed in infer_zones |
| 2026-06-13 | Figure sequential matching as cross-page tradeoff | Caption-asset pairs on different pages get lower confidence |
| 2026-06-15 | Expand deterministic gold set to 8 papers | Needed broader regression surface before changing figure inventory |
| 2026-06-15 | Do not solve AJR side-caption recovery in group-first refactor | Keep scope generic; AJR-specific rescue is later phase |
| 2026-06-15 | Group-first matching is next architectural target | Existing clusters/visual groups too late in pipeline |
| 2026-06-17 | Single-thread close-out note | authoritative queue moved to `project/current/ocr-v2-closeout-priority.md` |
| 2026-06-21 | Replace greedy region-growth with global distance clustering | Human sees assets as perceptual groups, not competing candidates |
| 2026-06-23 | Pre-ref=body flow, post-ref=backmatter | CRediT/Ethics above References → body_zone |
| 2026-06-23 | Figure containment: render-hygiene pass build_figure_inventory | Containment shouldn't affect matching, only rendering |
| 2026-06-23 | Reference sort: two capture groups | Prevents false matches on plain year numbers |
| 2026-06-26 | P0 before P1 | Fix 2/4/5 are <30 lines fully understood; Fix 1/3 need new specs |
| 2026-06-28 | Pre-ref tail zone: strip from region_bus not re-apply | `_apply_zone_labels` re-applied stale tail zone from `infer_zones()` after ref partition. Fix: strip pre_ref block IDs from region_bus before zone re-apply. |
| 2026-06-28 | Author byline: require lowercase letters | `_looks_like_initial_lastname_byline` matched all-caps journal taglines. Fix: require any lowercase letter in matched text. |
| 2026-06-28 | Page-1 body_start: metadata headings should not trigger | `_is_first_page_body_start` treated ANY section_heading as body start. Fix: only real body section headings (introduction, methods, etc.) trigger body_start on page 1. |
| 2026-06-28 | Frontmatter heading normalization: no text matching | Metadata sidebar labels rejected by structural gate fell to unknown_structural. Fix: normalize held heading blocks in frontmatter_main_zone to frontmatter_noise using only zone + gate decision + seed_role, no text matching. |
| 2026-06-28 | Author bio detection: three-pass cascade, P0 first | Strong structure first, residual explanation second. Real figures must never be preempted. P0: post-ref text-only. P1: figure residual. P2+: P1 profile card pre-pass. |
| 2026-07-04 | Introduce ownership-evidence writeback seam | Figure/table asset claims, contained text, and side-adjacent figure text needed one post-inventory contract so renderer suppression and future late-stage role logic could consume the same evidence. |
| 2026-07-04 | Extract tail settlement out of normalize/build seam | Tail/body/backmatter settlement had grown into a cross-module implicit contract; isolating it lowered blast radius before attempting the v3 normalize split. |
| 2026-07-04 | Keep `OCR_PIPELINE_V3` merged but default-off | The pre/post normalize split is architecturally correct, but synthetic parity is easier to prove than corpus parity. Merging behind a toggle cuts long-lived branch risk without forcing the new path live. |
| 2026-07-04 | Contained figure claims must be page-qualified | Cross-page `block_id` reuse and similar figure geometry can silently hide the wrong text. Ownership claims now require same-page qualification before containment is trusted. |
| 2026-06-28 | Category-weighted bio scoring | career=+3, education=+2, research=+2, institution=+1, publication=+1. Returns (score, categories) tuple. Threshold: score ≥ 4 AND categories ≥ 2. |
| 2026-06-28 | author_bio_asset role: non-rendered, non-indexed | Bio artifacts removed from figure_inventory entirely, never returned to unmatched_assets. Clean prune before reader. |
| 2026-07-01 | Asset-internal figure number recovery: metadata-only pass | Recovery must NOT split OCR blocks or mutate chart text — only patches figure_number, figure_id, recovered_label_text on existing matched figures. Coordinate normalization is caller responsibility. |
| 2026-07-01 | Broaden recovery gate to handle normal prematch unknown figures | Synthetic-figure gate (`bbox_only_asset` flag) excluded `figure_unknown_NNN` from normal rotated prematch path. Gate now allows figure_unknown figures without synthetic flags. |
| 2026-07-03 | Cutover uses evidence gates, not code confidence | VNext matched or improved on the full cutover corpus with identical consumed asset sets; wrapper switch became a release decision only after diff review + gate verification. |
| 2026-07-03 | Legacy schema tests must be upgraded before wrapper switch | Real-paper behavior was cutover-ready earlier, but `test_ocr_figures.py` still asserted legacy-only inventory keys. Updating the test contract was required to make wrapper switch honest. |
| 2026-07-03 | Generic state uses a domain hook for figure rotation enrichment | Figure rotation metadata had to stay behaviorally intact without polluting the shared pairing state used by table passes. A pre-match enricher hook keeps the core generic and the figure path exact. |
| 2026-07-03 | Table parity comparison normalizes benign storage drift only | int/str block IDs, ordering differences, and `None` vs empty unmatched asset IDs are storage-level drift already tolerated downstream. Validation now compares semantic fields rather than raw serialization artifacts. |
| 2026-07-03 | Legacy `block_id=0` drop is treated as a legacy bug, not a parity target | `37LK5T97` showed legacy dropping consumed caption id `0` via falsy filtering. The branch keeps vnext truth and documents the legacy defect instead of reproducing it. |
| 2026-07-05 | Expand crop bbox to include figure_inner_text | figure_inner_text IS the figure content (variables labels, y-axis text); text should be IN the cropped jpg, not listed as a separate note section. Crop bbox now unions all owned figure_inner_text block bboxes. |
| 2026-07-05 | Enable OCR_PIPELINE_V3 by default | Full vault corpus diff (555 papers): 547/555 no diff, 5/555 v3 improvements (3 more figures found, 2 boundary corrections). 98.6% parity is sufficient to flip the default; OCR_PIPELINE_V3=0 restores legacy. |
| 2026-07-05 | figure_inner_text must be in the figure render, not dropped | Side-adjacent and contained text blocks correctly identified as figure_inner_text, but had no display outlet. Crop bbox expansion is the correct fix (text is IN the figure), not a text listing below the image. |
| 2026-07-05 | Health = 3 layers: Quality Signal → Quality Indicator → User Readiness | `build_ocr_health()` preserved raw; `build_quality_indicators()` adds normalized layer; `evaluate_readiness()` applies policy. Never merge health and quality report. |
| 2026-07-05 | Readiness weights in external YAML, never hardcoded in Python | Policy evaluator reads from YAML; thresholds tunable without re-running OCR. Default ships in `paperforge/policies/ocr_readiness_v1.yaml`. |
| 2026-07-05 | Human feedback is a sidecar file, never part of pipeline output | `ocr_quality_feedback.json` is read/written independently; bound to `result_hash` for integrity. |
| 2026-07-05 | Field resolution precedence: direct inventory > health aggregates | `figure_inventory` fields preferred over `health.matched_figure_count_v2` etc. `health.figure_asset_count` is NOT a figure-evidence signal (it's a match count). |
| 2026-07-05 | `user_readiness` must state `"basis": "policy_estimate"` | Pipeline produces signals, not ground truth. Gaps are real, but code doesn't know if a gap is actual missing text or a proper skip. |
| 2026-07-05 | `recommended_use` output shape: `status`/`gates`/`reasons` | Contract fixed at `d7b0a527` from the initial `recommended`/`gate_results` shape. |
| 2026-07-05 | Feedback hashes per-mark, not just root | `append_mark()` injects `result_hash` and `fulltext_hash` into each mark; stale detection compares latest mark's hash with current run. |
| 2026-07-08 | Hash-based OCR staleness detection (two-tier mtime+xxhash) | Version constants require manual bumps; content hash of blocks.structured.jsonl is faster and self-consistent. |
| 2026-07-08 | OpenAI SDK over raw requests for embedding provider | openai SDK has built-in retry, timeout, and error classification; removes hand-rolled HTTP code. Requests fallback available via provider_type config. |
| 2026-07-08 | sqlite-vec replaces ChromaDB for vector storage | ChromaDB HNSW index corruption, heavy deps (~100MB), and separate storage. sqlite-vec is ~1MB, stores vectors in same paperforge.db. Brute force at ~50k vectors <100ms. |
| 2026-07-08 | E2E test fixtures as synthetic PDFs (PyMuPDF) instead of real arXiv PDFs | Avoids license/distribution issues; deterministic and fast to generate. |
| 2026-07-09 | Schema v6: hash/policy columns in vec companion meta tables | Resume hash checks need body_units_hash, object_units_hash, retrieval_policy_version persisted alongside vectors. |
| 2026-07-10 | Retrieval scope is the entire user experience, not only vec0 | M metadata search, `@` retrieval, build lifecycle, status, deployment, and persistence share contracts; auditing only the vector table would miss the observed failures. |
| 2026-07-10 | Source Corpus is preserved; Retrieval Artifacts are disposable | Paper/OCR/structured/user-authored content is authoritative, while FTS indexes, embeddings, vector tables, and companion metadata may be cleared and rebuilt instead of migrated. |
| 2026-07-14 | OCR Recommended is a backend contract, not a plugin heuristic | Rebuild eligibility includes version/hash/artifact drift that the UI cannot reproduce safely; `needs_derived_rebuild` is emitted once by the canonical selector. |
| 2026-07-14 | Cooperative stop is transported over stdin | Windows `SIGINT` can terminate the current paper; a `PAPERFORGE_STOP` control line preserves the finish-current-then-stop contract across platforms. |
| 2026-07-14 | Broader settings work starts with Wayfinding, not another local redesign | Persistent rebuild rows, onboarding, installation, memory configuration, and recovery are one product-state problem; adding controls before defining that model increases ambiguity. |
| 2026-07-14 | Successful updates leave maintenance; quality anomalies are opt-in reports | Routine quality scores create permanent, non-actionable noise. Maintenance shows only stale/failed/corrupt work with a concrete action; unacceptable OCR is reported through a user-reviewed GitHub Issue draft. |
| 2026-07-14 | Control-plane facts come from independent backend capability probes | A global setup boolean and frontend inference cannot represent partial readiness or stale state; every module needs a reason code, one primary action, and revision/freshness evidence. |
| 2026-07-14 | Preserve durable domain truth; migrate JSON runtime snapshots to versioned caches | SQLite build state and per-paper OCR metadata already support recovery, while independently written JSON snapshots have no coherency or staleness protocol. |
| 2026-07-14 | Capability model uses orthogonal availability × activity × attention axes | Session design work produced three independent axes: 6-state availability ordinal (unknown→unavailable→missing_input→needs_action→limited→ready), 2-state activity (idle/running), urgency derived from availability. Backend owns severity and primary actions; plugin renders via color from severity field. One-primary-action invariant with setup > set_config > restore_backup > redo > run > migrate > update > rebuild_* > investigate > probe priority. |
| 2026-07-14 | Managed-runtime: plugin-managed venv with immutable version slots | Adopted Design A after four-design comparison against bundled, resolver-only, and HTTP service alternatives. Single `active-runtime.json` atomic pointer, `ManagedRuntime` class with sync `current()` + async `status()`/`ensure()`, system-Python 3.10+ preferred with release-validated python-build-standalone fallback on supported triplets. Fail-closed: unknown state never renders as ready. |
| 2026-07-14 | OCR maintenance actions route through a canonical verb model | `maintenanceActionForRow()` maps backend `display_action` → `"rebuild"` / `"redo"`. Batch command filtering now uses this verb rather than twin booleans. `maintenanceActionRequiresConfirmation()` gates destructive `redo` behind a browser `confirm()` with localized text. |
| 2026-07-14 | Keep normal readiness in the control center, not permanent status-bar chrome | Obsidian status bars work for active operations and exceptional attention; duplicating six-module health there creates noise and conflicts with the actionable-only maintenance model. |
| 2026-07-14 | Diagnostics stay local until the user reviews an issue draft | Docker-style opaque uploads require a support service and hide bundle contents; PaperForge instead exports redacted data locally and opens a prefilled GitHub draft without token storage or automatic submission. |
| 2026-07-15 | Six-module control center: plain-button scenario switcher, not ARIA tabpanel | Scenario switcher uses `<button>` elements with `aria-current="true"`. No `role="tab"`/`"tablist"`/`"tabpanel"` — clicking a scenario changes the entire page state, inconsistent with tabpanel pattern. |
| 2026-07-15 | Primary attention zone exposes one concrete action, never a generic link | Hero action is the single highest-priority verb (e.g. `rebuild_derived` for OCR), never a "View Details" link. Normal state says "一切正常" with a less prominent refresh action. |
| 2026-07-15 | Maintenance inbox is actionable-only; normal and quality-ok items are absent | Routine quality scores create permanent, non-actionable noise. Maintenance shows only stale/failed/corrupt work with a concrete action; unacceptable OCR is reported through a user-reviewed GitHub Issue draft. |
| 2026-07-15 | Issue-draft flow is confirmation-first, inline redacted, never auto-submitted | User reviews a prefilled GitHub draft panel inline, edits freely, then clicks "Open GitHub" to create. No token storage, no automatic submission. Docker-style opaque upload rejected. |
| 2026-07-15 | Prototype reviews use independent Critical/Important pass/fail gates | Both #71 and #72 prototypes were reviewed by independent reviewer subagents on two dimensions: Critical items (correctness/safety) and Important items (readability/maintainability). All items passed before acceptance. |
| 2026-07-15 | Canonical setup is one `SetupPlan`; configuration writes converge to schema v2 | Duplicate headless/modular/bare engines dropped path inputs and disagreed on success. One engine plus `vault_config`-first reads makes migration observable, idempotent, and reversible through the warned v1 read fallback. |
| 2026-07-15 | Capability integration advances by real tracer, never frontend optimism | #76 exposes only Installation and Help as real probes; Library/OCR/Memory/Maintenance remain explicit placeholders until their backend envelopes ship. Persisted malformed or stale evidence becomes unknown/invalid rather than ready. |
| 2026-07-15 | Module detail navigation extends Wayfinder instead of replacing it | Preserve the primary-attention zone and concrete backend action. Stage `概览 / 模块详情 / 维护 / 帮助` across #77/#78/#80; use explicit module-title navigation, top ordinary buttons, and no dead placeholder details. |
| 2026-07-18 | Enforce Matt with sticky rules plus a minimal deterministic hook | Prose alone cannot prevent orchestration drift. Keep lifecycle guidance in `.omp/RULES.md`; use the hook only for mechanically provable boundaries: one writer, worktree isolation, and verification-after-last-mutation before release operations. |
| 2026-07-18 | Capability facts are Python-owned; TypeScript renders via exact allowlist, fail-closed | Python owns all capability fact definitions and cross-module consistency. TypeScript receives only pre-classified display objects; rendering uses an exact allowlist of known content component keys. Unknown keys render nothing (fail-closed) rather than guessing a classification. TypeScript forwards operation exit outcomes but Python classifies sync failure. This avoids duplicating classification logic across the stack. |
| 2026-07-19 | Maintenance is a backend-derived probe, not a frontend projection | Prior design (2026-07-14) treated maintenance as a frontend-projected view over capability-state data. Real implementation showed that actionable rows (stale, failed, corrupt) and their canonical verbs must come from the backend's `probe maintenance --json` — the frontend cannot reconstruct per-paper rebuild eligibility from capability state alone. Backend owns exact actions; frontend renders via derived model with primary null for quality-ok items. This keeps Maintenance as a true probe while remaining a projection over backend OCR facts rather than a separate pipeline output. Privacy-safe local draft and owned inert modal cleanup are frontend-only concerns. |
| 2026-07-19 | A plugin deployment is valid only when the loaded manifest directory and backend command surface are verified | Copying `main.js` proved nothing while Obsidian loaded a duplicate `paperforge.bak`; the managed venv also contained a published package without `probe`. Release verification must assert `manifest.dir`, cold `ManagedRuntime.status()`, and a real `paperforge probe` command before UI acceptance. |
| 2026-07-19 | Installation is an action; Foundation is the persistent module | Users should not have to understand why an “Installation” module remains after installation. Foundation owns the PaperForge environment; Runtime and Python remain support/recovery details. |
| 2026-07-19 | The control center has five operational modules and three top-level destinations | Foundation, Library, OCR, Smart Retrieval, and Agent Integration have independent lifecycles. Overview, Maintenance, and Help are destinations; Module Detail is contextual drill-down, while Maintenance and Help are not health-reporting modules. |
| 2026-07-19 | Maintenance contains only user-visible, resolvable problems | Internal OCR quality estimates, ordinary OCR imperfections, stale cache, optimization suggestions, and optional capabilities never enabled do not merit user attention. A problem must block use, fail a requested task, make output unusable, or create material data risk and have a concrete action. |
| 2026-07-19 | Backend owns action semantics; plugin owns localized presentation | Stable action IDs, exact commands, scope, and safety facts remain backend-authorized, while the plugin supplies user language and visual priority. This prevents frontend action guessing without leaking English CLI labels. |
| 2026-07-19 | PaperForge UI is Obsidian-native with progressive disclosure | Default surfaces show outcomes, impact, and one next step. Technical detail becomes a one-click privacy-safe Support Diagnostic rather than ordinary UI content. |
| 2026-07-19 | Release remains owner-controlled and deferred | N+1 implementation can be verified without publishing. Do not create a tag, package release, or support-window transition until the owner explicitly reauthorizes release. |
| 2026-07-20 | Resolve host locale from the rendered Obsidian document when vault config is unavailable | Obsidian 1.12.7 exposes Chinese through `document.documentElement.lang` while the previous vault/localStorage-only resolver returned English. Following the host document keeps plugin language aligned without adding a setting or dependency. |
| 2026-07-20 | Use zero-minimum grid tracks for overview cards | CSS Grid `1fr` tracks preserve min-content width and overflow narrow Obsidian settings panes. `minmax(0, 1fr)` plus normal wrapping preserves the two-column layout without clipping or horizontal scroll. |
| 2026-07-23 | Make the repaired prototypes the Map #94 implementation contract | The prototypes incorporate later user testing and therefore supersede earlier map text where they differ. Production must follow the reconciled `DESIGN.md` and FE/BE mapping, not preserve stale sidebar, Maintenance-tab, or two-column Overview decisions. |
| 2026-07-23 | Keep backend gaps explicit instead of simulating authority in frontend copy | OCR safety/activity, Library last-sync, retrieval backup availability, agent deployment, and diagnostics need typed backend fields. `[GAP]` markers prevent prototypes from becoming accidental promises or encouraging frontend inference. |
| 2026-07-26 | Treat real Obsidian test-vault rendering as the UI authority | Prototype pages and stale deployment checks missed path composition, CSS specificity, and layout-host behavior. Future visual acceptance must exercise the built plugin in its target vault, not only mock HTML. |
| 2026-07-26 | Keep first-run Library configuration in the Setup Journey | The user needs one place to configure and verify the paths that determine Library readiness. A status-only stage plus a separate setup modal creates a dead end and duplicates the configuration surface. |
| 2026-07-26 | Separate Foundation runtime setup from Library setup | Python/PaperForge package availability is independent of user-selected Zotero and vault paths. Running modular setup in Foundation made first-run configuration implicit and created a nested legacy-wizard recovery path. |
| 2026-07-26 | Configure selected optional capabilities in Stage 3 | The approved prototype makes choices and required configuration one flow. Checkboxes without credentials/model/platform only postpone the same installation decision to unrelated module pages. |
| 2026-07-26 | Scope Smart Retrieval credentials by endpoint/model profile | A global API key can silently authenticate a changed provider or model configuration. Profile-scoped SecretStorage IDs preserve prior profiles while fail-closing any new, unsaved tuple. |
| 2026-07-26 | Treat unscoped legacy retrieval keys as unavailable | The old global SecretStorage record contains no endpoint/model provenance. Copying it to a changed provider would silently inject the wrong credential, so users must explicitly save the current profile once. |
| 2026-07-26 | Recheck required setup state before Stage 4 | Cached probe envelopes expire across plugin reloads. Completion must be gated by a fresh required-state probe, not by an initial `detection_failed` placeholder that is known stale. |
| 2026-07-26 | Define Foundation ready as exact runtime compatibility | A Python import alone does not prove the executing backend implements the loaded plugin’s contract. Foundation is ready only with valid vault config, supported Python, and exact PaperForge package/plugin version match; otherwise a forced reinstall is the single recovery action. |
| 2026-07-26 | Treat reinstallation as transient recovery state | A prior mismatch must not remain as an action after a fresh probe returns ready. Persistent eligibility comes solely from the current backend envelope; the local request flag is cleared on readiness. |
| 2026-07-26 | Preserve backend actions and local deployment facts | The UI may localize a known action but must not collapse it into an unrelated probe. Agent has no runtime probe, so its capability state must be the conservative filesystem fact—deployed or not deployed—while connection verification remains separately unknown. |
| 2026-07-26 | Clear only migration warnings superseded by a secure profile | Unscoped legacy plaintext cannot be safely assigned to a profile and remains untouched. Once the user supplies a verified profile secret, the warning is no longer actionable and must not obstruct index construction. |
| 2026-07-26 | Treat the live build result as the only retrieval completion gate | The action can route correctly yet fail in the configured Python environment, or complete data writes while failing final bookkeeping. Re-probing to `memory.ready` after the command distinguishes both from a cosmetic success notification. |
| 2026-08-03 | CI-red baseline is release debt, not today's regressions | Every CI run since e0901d55 failed the same way (versions.json rows, vector extras, F821s, 3 plugin faults) — invisible under allowed-skips. #121's real gate surfaced all at once; each fault verified against the pre-#119 baseline before fixing. |
| 2026-08-03 | #119/#120/#121 close with code evidence, not claims | Each acceptance item verified: typecheck clean, vitest 414/414, protocol 65 passed, prod probe memory ready, workflow YAMLs parse, version-sync PASS. Remaining P0-1 stays owner-controlled per risk guidance. |
| 2026-08-04 | F821 gate over F401 backlog | 12 undefined names are real NameError classes (one was #119's own typo, would crash on the deps-missing path); the 50 F401 unused imports are pre-existing style debt — keep them out of the release gate. |
| 2026-08-04 | CI ruff/version gates enforce the whole repo | allowed-skips removed; a broken TS build, missing versions.json row, undefined name, or shadow regression can no longer merge. |
| 2026-08-05 | Architecture audit is five immutable layers with one pure reconciler owned by #131 | Deterministic observation (Survey), deterministic policy results (Audit), and Agent/Human judgment (Review) must never mix; Review binds Contract+Survey+Audit digests and reconciler version; collectors (#133) call #131's reconciler and never reimplement rules. |
| 2026-08-17 | Frozen candidate blocked by shared-state audit | The frozen candidate `6ef0dfe9` reproduced retrieval `current` over a corrupt carrier and a preflight/reconcile first-frontier divergence. Repair commit `46c4ddaf` is on `master` but not in the frozen candidate; build a new candidate and rerun REC-02/M2/M3/dependent RC rows before any owner release decision. No re-OCR/rebuild/embed for valid users; corrupt carriers require `memory.build`. |
| 2026-08-05 | Enforce one `ready-for-agent` issue; downstream issues stay `blocked` until the prerequisite is accepted | Closing a prerequisite does not auto-unblock; the next issue is manually promoted. This prevents a sprawling epic (#130) from becoming a single agent task and keeps the product lane (#127\u2192#126\u2192#129\u2192#99) ahead of architecture tooling (#133/#134). |
| 2026-08-05 | Assessment precedence is failed > incomplete > findings > clean; gate_eligible marks coverage-complete audits only | #134 consumes one authoritative top-level outcome instead of reinterpreting coverage; planned gaps never block, deterministic violations do when blocking + active. |
| 2026-08-05 | Golden evidence is repository-relative and source-complete | Every cited evidence file now carries the `paperforge/` prefix, golden source digests aggregate all cited file/digest pairs, and tests verify file hashes, symbols, and line ranges. |
| 2026-08-05 | Validate authority identity and report projections | Contract-declared publication/role authorities—including observer/delegated sets—must match observed identities; wrapper evidence and report-projection digests are validated at layer boundaries. |
| 2026-08-05 | Multi-valued authorities use exact declared sets | Observer/delegated-executor roles are set-valued; accepting a partial observed set would hide missing lifecycle participants, so reconciliation reports missing and unexpected identities. |
| 2026-08-05 | Harden Slice A contracts and failure semantics | Added deterministic list tie-breakers, ordered wrapper roles, entity lifecycle/enforcement inheritance, unioned required coverage including failed audits, composable failed audits, auditable signal-consumer identity, strict SHA-256/path validators, consistent role selectors, report/view payload-digest consistency, enum validation, and deterministic malformed-input digests. Verification: 117 focused architecture tests passed; Ruff clean; full Python suite 2772 passed / 292 skipped / 25 known Windows sandbox-lock errors. Final read-only review PASS; commits `73a782cf`, `078dd8a7`, and `963cc59a` are on `master`; owner acceptance pending. |
| 2026-08-05 | Slice A acceptance and #132 review-overlay Skill | Owner accepted and closed #131 with verification recorded; #132 manually promoted to `ready-for-agent`. Slice B delivers a model-invoked architecture-review Skill whose process is deterministic and checkable: harness-driven audit/emit steps, `trace` leading word (8-stage completion invariant), adjudication completeness over violated/unresolved findings, digest/reconciler-version binding refusal, and epistemic labeling (inferred/unresolved only). Evals assert process predictability against the fixed Slice A fixtures across full-survey / focused-signal / changed-interface branches. Commit `5f03051e`; re-review PASS. |
| 2026-08-05 | Mandatory triage checkpoint (per #130) | Re-read all open issues against the accepted Contract/Review; classified: active #127/#126/#129 (product lane, #127 sole `ready-for-agent`); owner decision #81 (release gate) and #99 (redo safety, reconfirm after #129); deferred #63/#82/#94–#105/#133/#134; #125 administratively closed after ledger+queue record; Wayfinder #94–#105 frozen, no child agent-ready. Queue file and ledger updated; only #127 unblocked. |
| 2026-08-05 | Product-lane architecture analysis (#127/#126/#129/#99) | Code-verified input/output traces of sync→memory→embed, OCR rebuild/redo→publication, and version restore; published `docs/research/2026-08-05-product-lane-architecture-analysis.md`. 11 findings (G1–G11): P0 dry-run side effects in sync text branch; P0 double-`PaperForge` fulltext path root cause (`systemDir` already contains it); parallel rebuild ignores Stop; `result-hash.txt` reader-only; restore copies fulltext.md only and records no provenance; #99 premise outdated (redo already transactional per #123). Addenda appended to #127/#126/#129/#99/#102 issue bodies. |
| 2026-08-05 | Issue regularization — overlap absorption | #101 (progress bar contract) SUPERSEDED → absorbed into #126 PR B (token format pin, OCR START/DONE emitters, OCR_RUN cleanup, progress states); #102 (embed pre-rebuild backup) SUPERSEDED → absorbed into #99 (backup strategy covers redo + embed in-place path in one policy). #95 stays deferred with an explicit #126-acceptance coverage check; #63 stays open as the parent contract with a protocol note. #94 child list updated; ledger and queue file synced. |
| 2026-08-05 | External review of regularization — adopted | Independent review confirmed queue order and found no missing pre-#127 issue; corrected G1 (dry-run already early-returns at `sync.py:39-52` — regression test, not live P0) and hardened #127 (cost/impact/confirmation split axes, single execution ownership, typed action_id allowlist, safety invariants, PR A–D split). Locked: #126 colon wire format (key-only tokens), #129 fulltext-only restore, #99 split A/B/C, #82 HARD GATE + `blocked`, #94 live table, #63 frozen banner, #95/#97/#103 code-check notes, #105 split-A–D note, #134 CI-allowlist note. Ledger and analysis doc updated. |
| 2026-08-05 | #127 next_actions implementation (PR A–D) | Implemented: `core/next_actions.py` (typed schema, registry, validator with remote/destructive invariants, build-time fail-closed raise); sync producer cutover (Popen removed — no hidden embedding; terminal runner executes automatic-local memory.build only; `--json` single final document with no follow-up; dry-run early-return regression-tested); plugin orchestrator (`next-actions-orchestrator.ts`: fixed action_id→argv allowlist, in-flight+executed dedupe, depth loop guard, confirmation/refusal outcomes; `next-actions-bridge.ts`; `NextActionConfirmModal`; both sync call sites consume `sync --json`). Seam contract tests both sides (26 python + 11 plugin). Review found 2 MAJOR (build validation discarded; executed-marking before actual start) — both fixed with regressions. golden_127 re-pinned to `7372383b`; commits `7372383b`, `417bd3e3`. |
| 2026-08-05 | #126 OCR Workspace closure (PR A–D) | PR A backend: structured rebuild results (success/failed/skipped), exit codes 0/1/130, single-key full token sequence (START/PROGRESS/RESULT/DONE), chunked parallel stop, canonical `ocr_hash` (3-artifact sha256, missing→None), `result-hash.pending` marker protocol in rebuild + postprocess (covers backfill), reader pending-check + incremental skip, Level-2 shared-helper alignment. PR B: plugin-owned `OcrProcessController` singleton (mode-based start, credential fail-closed run/redo, `PAPERFORGE_STOP` stop, settle-once), RESULT/DONE parser events, Settings migration. PR C: fulltext P0 (index path → ocrDir fallback, pure helper), single-paper rebuild, index refresh chain (memory build on successKeys>0 incl. partial/stop; confirmed embed resume; failed memory build blocks prompt), lazy restore (formal → legacy, race protection). PR D: index-first load + background `ocr list --json` enrichment, 100/page pagination, per-page select-all, O(n²) removal, per-filter selection reset. Review: 3 findings → fixed (dropped keys surfaced as skipped + rc 1; real controller stop; version-chip selection reset; reload enrichment preserved) → PASS. Full suite 2867 passed / 292 skipped / 25 sandbox-lock + 2 env vault-search timeouts. Commits `dea041db`, `8426dc84`, `d29cbaa0`, `ac992f9c`, `b8d478f3`, `e47a6539`, `72cf3598`. |
| 2026-08-05 | #129 display restore semantics | Restore relabeled 恢复展示全文文本 with a confirmation dialog stating the display-only boundary (structure/index/memory/vectors untouched). `restoreVersion` persists provenance ({label, restored_at, version_created_at}) into meta.json on success — both formal and legacy backup-* paths; failure writes nothing. Backend `_restore_drift_override` marks `fulltext_drift_state` DRIFTED when the restored version predates the current structured state (hash comparison watches the root compat fulltext, not render/fulltext.md, so the override is required); applied in both `collect_maintenance_rows` and `compute_maintenance_manifest`. Stale notice after restore compares raw `ocr_finished_at` (new `OcrPaper.ocrFinishedAt` field, enrichment never overwrites). Docstring documents display-vs-structural. Review: 3+2 findings → fixed (backup provenance, Date-safe comparison, en translation, raw timestamp) → PASS. 456 plugin tests; commits `2b4dca8d`, `4ab9d6b2`, `5abdc7e1`. |
| 2026-08-06 | #99 redo safety (owner decision) | Owner decision: **redo is internal-only, never user-exposed** — ribbon + command palette registration removed, maintenance action mapping never returns redo, probe never emits ocr.redo action_primary (CLI kept). #99-A convergence documented (redo transactional per #123 + #126 hash protocol). #99-B new `recover_redo_orphans()` — restores papers interrupted mid-redo from `paperforge-redo-<key>-*` snapshots (missing/pending ocr dir restored, completed orphans cleaned), never on dry-run. #99-C embed in-place backup verified as already implemented (test_embed_integration). golden_129 re-pinned to `2b4dca8d`. Review: 4 findings → fixed → PASS. Commits `9a1362e9`, `1a1bb895`, `fd268d05`. Product lane complete; #130 product-lane checklist fully checked. |
| 2026-08-06 | Audit report v1–v4 (external review loop) | Live architecture audit report built at `docs/architecture-audit-2026-08-06/` (`build_audit.py` + `render_html.py` + self-contained index.html). v1 real revision+coverage; v2 honest coverage + Review overlay + OCR_RUN dead protocol removed; v3 enumeration-complete semantics (universal/absence rules unresolved under partial coverage, contract-owned requiredness, step-level traces, digest-bound evidence IDs); v4 (third review BLOCKER): `repository_state` (revision/dirty/dirty_diff_digest) became **semantic Survey content** bound into the survey digest — dirty forces `assessment=failed`, Audit is the single gate authority, View/Summary/HTML only project (previously dirty lived only in Summary/HTML, creating a three-layer truth split). Cross-layer consistency now byte-identical. 153 focused tests; full suite 2883 passed / 292 skipped. Commits `e94895a1`, `b009fe75`, `3fb4a01b`, `7567dd2c`. |
| 2026-08-06 | Owner directive: #133/#134 before RC; RC deferred to owner manual testing | Owner: "可以先做133和134，发布还得等我手动来做真实测试" — the #130 execution gate is overridden for the architecture-tooling lane: #133 promoted to sole `ready-for-agent`; #134 blocked-by-#133; RC acceptance (gate for #81) remains owner-controlled via manual real-vault testing. Deferred-to-#133 items recorded in the review overlay: NextActionFact/RemoteExecutionFact/ConfirmationFact modeling, `operation_write_scope`/`effect_boundary` RuleKind, `test:` extractor evidence schema (name/revision/result). |
| 2026-08-06 | #133 deterministic collectors | `paperforge/architecture_audit/collectors/` — maintainer-only orchestrator + Python AST collector (Tier 1 direct sinks / Tier 2 wrapper callsites via import resolution / Tier 3 dynamic calls with **scoped honest effects**, never fabricated) + Node TS compiler collector (repository-installed typescript 5.9; missing tooling → explicit coverage, never silent all-clear). Versioned wrapper registry encodes #126/#127/#129 legwork. Reconciler gained an unresolved-evidence seam: rules whose effect domain overlaps unresolved dynamic callsites in the matching module stay UNRESOLVED (no false satisfied from partial enumeration). Full-repo run: 212 files / 512 facts / honest statuses. 14 tests; architecture suite 183. Commit `759a44a5`. |
| 2026-08-06 | #134 report projection + CI gate | `paperforge/architecture_audit/report/` — parameterized self-contained HTML projection (10 sections, deterministic/review layers visually separate, safe escaping, copyable evidence, filters, keyboard focus, reduced motion, responsive) + deterministic gate consuming **Audit only** (review/HTML never affect exit; only allowlisted active blocking violations block; ineligible → skipped with reasons, never silent all-clear; allowlist empty until rules reviewed low-FP). docs render_html.py became a thin wrapper; CI e2e job runs orchestrator + gate. 14 tests; real-browser smoke; full suite 2899 passed. Commit `a38c06c7`. |
| 2026-08-07 | Audit review rounds — Pages hardening | Pages workflow rebuilt on every master push (no paths whitelist), fail-fast `evidence_callsite()` (missing/ambiguous → build fails, never silent stale lines), failure landing page when generation fails (stable URL never shows a stale report as current), runtime UTC `generated_at`. Live URL: https://lllin000.github.io/PaperForge/. Commits `7dca7926`, `f841720e`. |
| 2026-08-07 | `status --json` stdout pollution root-caused | PyMuPDF 1.29 prints an import-time deprecation warning to **stdout** for `import fitz`, breaking the machine transport contract (rc 0 + non-JSON stdout). Fixed by migrating all 45+32 `fitz` usages to the official `import pymupdf` (project constraint ≥1.23 already supports it), adding a CLI entry exception guard (traceback + stderr + rc 1 — rc 0 with empty/non-JSON stdout is now impossible), guarding status JSON serialization, and making the e2e test surface stdout/stderr on failure. Commits `eb59aacd` (+ golden_126 re-pin in `79b32b15`). |
| 2026-08-07 | Report is collector-driven; authority roles declared | build_audit.py Survey now comes from the #133 orchestrator (python_ast/typescript complete on the live report); manual evidence demoted to the Review overlay; wrapper registry extended (pending marker, terminal runner, orphan recovery). Contract operations declare execution/lifecycle/stop authorities (plugin controller = stop authority, backend = delegated executor) with 3 new blocking role_authority rules. Lifecycle truth hierarchy documented in `.omp/AGENTS.md` (code existence → collector; architecture acceptance → Contract.lifecycle with tracked promotion; workflow → issue; release → CI/owner; ledger = projection). Node 22 unified (CI + engines + .nvmrc). Generation-lineage design published (deferred). Commit `79b32b15`, `d2dae1b3`. |
| 2026-08-07 | #133/#134 ACCEPTED (acceptance transaction) | External architecture review passed both issues (PASS/ACCEPTED). Closure items: manual_contract_trace removed from required_extractors (manual materials are Review-only — resolves the "manual not Survey input but gate requires it" contradiction); Pages workflow + L4b install Node 22 + npm ci so the TS compiler is real on CI (live report now typescript_compiler=complete, assessment=findings, gate_eligible=true, reasons=[]); acceptance test covers rule_coverage rows (planned rules carry no status). Contract `collectors.deterministic` promoted planned→active at `3eb17ae9`; issues #133/#134 closed with acceptance comments. Post-acceptance follow-ups tracked separately: authority facts, remote-intent literal-argv refinement, generation lineage. |
---

## 7. Agent Instructions

### 7.1 Project Folder Management

The authoritative prompt for project record management lives in `.omp/AGENTS.md`.
It is auto-loaded by omp into every session context and defines when and how to
update `PROJECT-MANAGEMENT.md`, `project/current/*`, and `project/archive/`.

TL;DR: PROJECT-MANAGEMENT.md updated every session end. project/current/ updated
at milestones only. project/archive/ gets moved-to (not deleted) when stale.

### 7.2 How to Update PROJECT-MANAGEMENT.md

1. Update section 2 (Current Status) — test counts, component status, fix status
2. Update section 3 (Remaining Issues) — remove resolved items, add new ones
3. Update section 4 (Active Queue) — check/adjust next steps
4. Add new decisions to section 6 (Decision Log)
5. Add a compressed entry to section 8 (Session Timeline)
6. Update "Last Updated" date at top

### 7.3 Before Starting Any OCR-v2 Work

1. Read section 4 (Active Queue) for current priority
2. Read the relevant design doc from section 5.4
3. Understand what the tests currently expect
4. Work one repair at a time; verify before moving on

### 7.3.1 Mandatory Change-Impact Annotation (owner directive 2026-08-16)

Every code change MUST state, in the commit message (and in the PR/issue
when one exists):

1. **Re-run required?** — whether the change forces `ocr.run` (remote),
   `ocr.rebuild_derived` (local), `memory.build` (local), or `embed.build`
   (remote) on existing papers, and for WHICH papers (all / affected-only /
   none).
2. **Old-user impact** — what existing installations / existing OCR data
   see after the change (e.g. "legacy metas without raw_blocks_hash stay
   unknown until one local rebuild"; "fingerprint now resolves wikilinks,
   no re-OCR needed").

Rationale: silent re-run requirements wasted remote OCR/embed runs during
2026-08-15/16 recovery. A change that needs a re-run MUST say so explicitly
so the operator can batch it; a change that does NOT need one MUST say so,
so nobody re-runs needlessly.

Format (append to commit body):

```
Impact: re-OCR: none | affected keys | all | <condition>
        rebuild: none | affected keys | all | <condition>
        embed:   none | affected keys | all | <condition>
        old users: <what existing data/installs observe>
```

### 7.4 Test Commands
```bash
# Full OCR test suite
python -m pytest tests/test_ocr_*.py -v --tb=short

# Figure stack only
python -m pytest tests/test_ocr_figures.py tests/test_ocr_figure_reader.py tests/test_ocr_render.py -q
# Real-paper regression only
python -m pytest tests/test_ocr_real_paper_regressions.py -v --tb=short

# Spec-contract tests only
python -m pytest tests/test_ocr_spec_contracts.py -v --tb=short

# Structural gate only
python -m pytest tests/test_ocr_structural_gate.py tests/test_ocr_document.py -v --tb=short

# Rebuild a single paper
python scripts/dev/ocr_rebuild_paper.py DWQQK2YB

# Rebuild + regenerate block_trace
python scripts/dev/ocr_rebuild_paper.py --trace DWQQK2YB
# Lint
python -m ruff check paperforge/worker/ocr_*.py
```

### 7.5 Design Doc Reading Order

1. `docs/superpowers/specs/README-ocr.md` — index
2. `docs/superpowers/specs/2026-06-08-ocr-anchor-first-structured-parsing-design.md` — architecture
3. `docs/superpowers/specs/2026-06-13-ocr-real-paper-regression-and-spec-realignment-design.md` — current phase
---

## 8. Session Timeline (Compressed)
| Date | Session | Key Results | Detailed Archive |
|------|---------|-------------|------------------|
| 2026-08-21 | **Read-only render consistency + figure reconciliation reports** | Full audit found 5304 render-layer issues. The shared output boundary emits consistency reports; an on-demand reconciliation pass now separates exact render repairs, inventory proposals, and blocked cases. 388XI46Q produced 8 supported labels, 6 canonical figures, 2 high-evidence proposals, and 5 reservation blocks; 965 report-only files were generated with 3619 exact, 128 proposal, and 727 blocked entries. No action executed. | §2.13, §4 |
| 2026-08-26 | **Reconcile-only identity hardening** | Read-only census scanned 965 papers and found 250 duplicate canonical figure-ID groups across 182 papers (224 conflicting, 26 identical; 500 affected output paths). Audit now emits structured duplicate issues; reconcile excludes ambiguous IDs from R/P indexing and blocks them; R staging filters to selected exact plans instead of passing the full inventory. **82 tests passed, 1 warning; no front OCR/render or production artifact changed.** | §2.16, §4, `project/current/render-reconciliation/duplicate-id-census.json` |
| 2026-08-26 | **D1 R promoter implemented, rollout blocked** | Reconcile writes an R-only manifest; `render promote-r` validates live snapshot, canonical uniqueness, exact refs, ownership, staged image/markdown facts, link, provenance, and plan hash before atomic per-file promotion with rollback on injected mid-batch failure. Synthetic success/stale/duplicate/idempotence/rollback tests and a real no-manifest CLI smoke passed: **88 tests, 1 warning**. No production write ran. | §2.17, §4 |
| 2026-08-17 | **Recovery + Control Plane Closure; M4 RC start** | Closed the stale recovery status in the ledger and recorded the final census: **958 = 938 OCR/retrieval current + 19 `nopdf` + 1 `pdf_missing`**; vectors **935 current + 3 `no_content`**; serving smoke verified. M1/M1.1/M2/M3 are closed. Candidate is frozen; M4 validation is CLI/call-chain/state-authority/pre-post-check focused; #81 remains open `ready-for-human`. | §2.4–§4 |
| 2026-08-17 | **M4 lifecycle and owner-gate evidence** | Product source tree `6ef0dfe9`: fresh modular setup/repeat and existing-vault migration/rollback fail-closed smoke passed; OCR → memory → global embed → retrieve → restart remained current; stale-state **113/1**, setup/runtime **129**, focused RC **216/1**, candidate Python jobs, safety gate, and plugin **408/408 + typecheck/build** passed. Hosted CI **#32040776725** at `14899168` passed **14/14**, including macOS unit/J-matrix and `All Checks Passed`, after checkout and macOS SQLite-runtime CI repairs. Deterministic collector coverage is complete but remains ineligible on six active unresolved rules plus two advisory wrapper findings; #81 stays open `ready-for-human`; managed runtime/UI/cancel/scoped embed/real Release-N rollback, post-RC architecture review, and owner decision remain gated. | `project/current/2026-08-17-rc-gate-matrix.md` |
| 2026-08-17 | **M4 post-freeze blocker audit** | Reproduced retrieval-integrity and frontier-parity defects against candidate `6ef0dfe9`; repair commit `46c4ddaf` landed on `master` and focused regressions passed (**126 passed, 1 warning**). Candidate remains blocked and release stays owner-gated; no release/tag/package publication. | §2.6, §3 |
| 2026-08-17 | **Live formal-library census divergence** | Read-only reconciliation explained the apparent delta: frozen `R=958`, current `F=964`, stable `957`, added `7`, removed `1` (`R2PSFXY4`). Current state is `944 OCR/retrieval current + 19 nopdf + 1 pdf_missing`; vector state is `933 current + 3 no_content + 8 not_embedded`. | **CLOSED as census divergence**; remaining scoped embed and residual-serving evidence are separate M4 gates. | §2.6, RC matrix finding log |
| 2026-08-18 | **M4 census closure projection** | Promoted the read-only reconciliation to the release records. No candidate rebuild, re-OCR, memory build, vector embed, or prune ran. Remaining M4 evidence: 8-paper scoped embed, residual serving smoke, exact-candidate frontend/hosted gates, and rollback/support-window owner acceptance. | `project/current/rc-live-census-reconcile.json`; RC remains owner-gated | §2.6, §3, RC matrix |
| 2026-08-18 | **Sync latency diagnosis and read-only fix** | Full reconcile was the dominant sync cost: repeated canonical-index parsing inside per-paper PDF lookup. One observation-scoped PDF map reduced measured production reconcile from **144.61 s to 48.38 s**; selection was **20.90 s**, unchanged index **0.53 s**. Disposable sync + lineage/reconcile regressions passed **167/167** with one warning. No production sync rerun or materialization mutation was performed. | §2.7, §6 |
| 2026-08-15 | **INCIDENT + safety layer** | **2026-08-14 23:00 production prune run deleted `D:\L\OB\Literature-hub` root** (`rmtree(Path(), ignore_errors=True)` — empty path = cwd = vault root, silent full recursive delete). Survived: paperforge.db (962 FTS + 22.7k vectors + retrieval units), Zotero (1338 PDFs, outside vault), exports copy, Project (partial), Med/Research (137,923 files, separate vault). Recovered via DiskGenius. Root cause fixed with a 3-layer safety net: ① trash architecture (`worker/trash.py` — delete = move + manifest + restore; `validate_target` fails closed on empty/`.`/root/escape; purge restricted to trash root; no ignore_errors anywhere), ② prune moves files to trash + transactional rowid-verified vector/DB deletes, ③ pre-commit + CI (`check_no_destructive_delete.py`) reject `rmtree+ignore_errors` and empty-path rmtree; legacy ignore_errors sites converted to explicit try/except. Commit `a0fdfcb6`. | §2.1, §2.3, §6 |
| 2026-08-15 | Unified residual detection | Zotero-authority residual report across workspace/FTS/vector/OCR carriers; paper-level `residuals` in probe lineage (per-carrier flags); reconcile emits one `library.prune`; prune handler/command + `memory.rebuild` registered; vector delete rowid-verified with rollback on partial rowcount. Found real residual 9RZU5ZBE (empty OCR dir, invisible to old workspace scan). Commit `0a4a81c4`. | §2.3, §6 |
| 2026-08-15 | Smart Retrieval panel single-source render | Panel status/button/info-card/impact all from probe envelope (reason.text + action.primary + details); probe memory injects structured details from same authorities as state machine; dead branches removed. Commit `e63445ae`. | §2.3, §6 |
| 2026-08-14 | Partial publish + resume incrementality | User: "build a few vectors, don't fully rebuild; partial should be retrievable, add = incremental". Audited shadow semantics against Airflow/Bazel DAG principles; implemented `partial_publish_shadow()` (checkpoint COPY candidate → live under reader barrier; candidate survives for resume) + stopped builds publish any vector rows + lineage for ALL vector papers. Fixed hidden bug: resume builds kept `_expected_dim`/`_stored_dim`=0 → `write_vector_lineage` silently wrote nothing → resume-completed publish would have empty lineage → gate dropped all; `_resolve_lineage_dimension()` falls back to vec0 DDL. Live verified: stop → 82 papers current, lineage 82/82, deep retrieval real matches, papers-scope embed unlocked (legacy gate cleared by copied identity). 80 py tests. | §6 |
| 2026-08-14 | sqlite-vec config audit + lineage DAG fix | User challenged "fully rebuilt yet retrieval returns 0" — audited against sqlite-vec official docs (asg017) + Airflow/Bazel DAG principles. **Config is correct**: vec0 DDL `float[2560]`, JSON-array insert with rowid-aligned meta, `MATCH ? AND k = ?` query, KNN live, FTS consistent (16000=16000). **Real defects (2)**: ① `_probe_ocr_state` treated missing `result-hash.txt` snapshot as unknown despite intact artifacts; ② `_current_embedding_identity` gated on `build_state.vector_dimension` (external key, cleared in earlier cleanup). Fixed per DAG content-addressing: recompute from artifacts; dim from vec0 DDL (build_state legacy fallback). Verified: 3 test papers unknown→current, library unknown:0, `retrieve --deep` returns real matches (acromion MRI, score 0.125). 105 py tests incl. 2 new contract tests (snapshot-missing recompute, DDL-dim). | §6 |
| 2026-08-13 | RC full-surface functional coverage + paid-action closure | Disposable vault exercised setup/config, credentials, sync, OCR, embed, cancellation, recovery, navigation, paid-action consent, then every remaining CLI surface (search/paper gateway/context/dashboard/deep-reading/prune/logs/base-refresh/ocr list+versions/action registry/update+repair NDJSON). Fixed 9/9 original findings + paid-action single-policy dispatch + 2 real-path CLI bugs (update urllib import; doctor sys.modules registration). Verification: 3091+44 py / 391 vitest / tsc+build clean; commits `a5ce2f16`+`b3881605` pushed. Release remains deferred to owner-controlled #81. | §2–4 |
| 2026-08-10 | R — read-model cutover + snapshot retirement (#161) | `probe all` aggregate + `ocr pipeline-versions` detail; probe_ocr envelope keeps summary; snapshot writers deleted (state_snapshot.py, embed/memory/runtime-health/status); TS `memory-state.ts` deleted → fail-closed `runtime-paths.ts`; Dashboard/Settings read-model driven; zero readers/writers asserted; wrong-snapshot authority smoke; J-matrix CI (3-OS J1/J2/J3); contract promoted (read-model active, snapshot deprecated, CANONICAL_READ active/advisory); goldens re-pinned (reviewed changes); 2939 py / 465 vitest; commits `696a1712`→`9c22341a`+`f14285cd`; CI all green | §9.N |
| 2026-08-10 | C0 merged to master (#176) + R review closure | slice boundary restored; review P0/P1 fixes landed (`f14285cd`); C0 closed #172 | §9.N |
| 2026-08-10 | T1 — digest lineage publish + probe lineage (#162) | `paperforge/lineage.py`: retrieval identity (manifest) + embedding identity (provider/model/dim/endpoint) + vector identity, lineage rows atomic with shadow publish; `probe lineage --json` per-paper {ocr,retrieval,vector} current/stale/missing/unknown, no DB → unknown envelope, legacy → unknown never stale, no auto-rebuild; golden digest verification normalized (CRLF/LF invariant) + all goldens re-pinned; J1 includes lineage tests | §9.N |
| 2026-08-10 | T1 corrective (#178) — review of #177 found P0-1/P0-2 | probe chain now threads (state, identity): retrieval compares manifest OCR hash vs current published identity + policy constant; vector verifies derived_from vs current retrieval identity; 3 regression tests; P1: collectors canonicalize CRLF→LF (canonical_source_bytes / ts replace); Python 2958/296; CI 14/14; #162 closed | §9.N |
| 2026-08-10 | C1 — Python credential provider + secret migration (#173) | `paperforge/credentials.py` (CredentialKey/CredentialStatus, resolve/store/delete/status, env→keyring→missing, stable codes, lazy keyring); `auth status/set/delete/migrate` CLI (getpass/stdin, never argv, migrate dotenv scrubs after verified store); consumers migrated (worker/ocr, embedding/_config, probe, ocr_diagnostics, preflight, providers, setup_wizard, status, dashboard); TS SecretStorage runtime authority deleted (settings/modals `auth set --stdin`; buildTargetedEnv redacted-only; presence via `auth status`); keyring>=25 dep; hermetic fake-keyring conftest; Python 2982/296, vitest 420/420 | §9.N |
| 2026-08-10 | C1 final corrective (#181) — legacy embedding SecretStorage id | migration bridge recomputes `vector-db-api-key-v2-<sha256(profile)>` (migration knowledge only); preflight drops redundant resolve; _restore_prior wording; Python 2989/296, vitest 426/426; #173 closed | §9.N |
| 2026-08-11 | T6 closure corrective (#167, owner review P0×5/P1×2) | **P0-1** explicit CLI root keeps T2 contract (rc2/3/0/1/130); --follow auto only takes descendants (root_depth=1). **P0-2** W2 production writer: chain settles every dispatched action via `record_last_attempt` + `semantic_attempt_digest` (facet states + identities + library digest + facet summary + substrate); pending/skipped never settle. **P0-3** memory.build handler hardcoded embed.resume deleted — reconcile single producer. **P0-4** pristine vector substrate: legacy requires `has_any_rows`; no-rows gate downgrades only when identity_version>0; pristine scoped resume initializes empty substrate (embeds only requested keys). **P0-5** `PFResult.successful_keys` seam — post-publish reconcile gets ACTUAL successful keys (T7 O1 bridge). **P1** depth 0..4 legal / 5 overflow; strict `scope_from_dict` + normalized-key dedupe. 14 chain + 2 registry + pristine ×2 tests; full suite 3085 py / 426 vitest; commits `fd12f363`+`9db4e2cc`; #167 closed | §9.N |
| 2026-08-11 | T7 closure corrective (#168, owner review P0×5) | **P0-1** `ocr.rebuild_derived` action registered (local derived rebuild, per-key outcomes); reconcile: raw/missing → ocr.run, derived-stale → ocr.rebuild_derived; O1/O3 run the REAL action→runner→reconcile path. **P0-2** memory partial-publish: SAVEPOINT rollback per paper; corrections/units consume ONLY successful_keys; partial failure never advances canonical_index_hash. **P0-3** reader gate fail-closed (probe exception → []); gateway body_units_fts primary arm gated (retrieval-only) + compat vector arm gated. **P0-4** #137 cancellation: `core/cancellation.py` (stdin PAPERFORGE_STOP + SIGINT + SIGTERM); embed sidecar + `embed stop` DELETED; cancelled → rc130 + cancelled terminal. **P0-5** NDJSON terminal ownership: preflight/index/no-candidates/worker-exception all exactly-one terminal; single-key redo streams too. O3 vertical flow test, rc130 test, stop integration rewritten to retirement contract; full suite 3096 py / 426 vitest; commit `ffc4ee05`; #168 closed | §9.N |
| 2026-08-11 | RC CLI 可靠性+唯一真相源审计 | **发现并修复真实契约 bug**:`probe all --json` 输出裸 envelope({schema_version,module:"all",modules}),但 TS `probeAll` 走 invokePaperForge(期望 PFResult {ok,data})→ 每次 `_refreshAllReadModels` 都 reject,UI 状态永不刷新(静默失败,测试 mock 伪造了错误 shape 掩盖)。修:probeAll 直接解析裸 envelope。**唯一真相源全验证**:配置(TS read/save retired)、凭证(keyring,TS 只 strip 旧 env)、action policy(registry,wire 携带)、指针(Python 唯一 writer)、intent(reconcile 唯一 producer)、版本(__version__ canonical + CI 5 处校验)。**CLI 36 命令**可靠执行,机器模式一致(setup/update/repair/ocr=NDJSON;probe=裸 envelope;其余=PFResult;paths=裸 dict 设计)。全量 3134 py / 389 vitest。commit `c1f17907` | §9.N |
| 2026-08-11 | RC 前端按钮闭环审计 | 枚举 probe 全部 23 个 action_id×verb,对照 TS `_runAllowedDispatch` 分支,发现 **4 个按钮闭环断裂**(点击 → "Unknown action" Notice 空转)。修复:① foundation.update(installation.version_mismatch)现标 destructive+confirmation_required(反映 remote/mutating policy),dispatch 走 `action run foundation.update --confirm`;② foundation.update_python → 明确 manual-install Notice(无自动化路径);③ memory.install_vector_deps → setup journey stage 3(重装 paperforge[vector]);④ memory.upgrade_backend 之前错误派发为本地 memory build → 改 `embed migrate --json`(ChromaDB→sqlite-vec)。补 i18n 键 + 4 个 dispatch 回归测试。全量 3134 py / 389 vitest。commit `6daabfc6` | §9.N |
| 2026-08-11 | RC 走查补:OCR/embed 垂直链路 | **发现真实契约断裂并修复**:TS OcrProcessController 用 fail-closed NdjsonStreamParser 解析所有长任务,但 `ocr run`(整队列)零 NDJSON 输出 → 成功运行被 UI 报 "EOF without terminal event" 假失败。修:`ocr run` 非 json 模式发完整 #137 流(start/progress/单 terminal,rc130 取消);`run_ocr` 加 stop_check+progress_callback(paper 边界停止,与 redo 对齐)。**embed 垂直验证通过**:embed build(无 --json)本已发 NDJSON 流;embed.build preflight credential.missing fail-closed。dispatch stub 更新 + 回归测试。全量 3134 py / 385 vitest。commit `43b55c5b` | §9.N |
| 2026-08-11 | RC 走查(前后端匹配+流程) | **契约面验证**:probe envelope(Python build_envelope 全字段 ↔ TS isValidEnvelope 严格校验,6 模块真实输出通过);action argv(TS buildActionArgv ↔ CLI parser 一致);NDJSON(Python emit 事件集 ↔ TS KNOWN_EVENTS 一致,parser 协议 fail-closed);版本三处 1.5.15 一致。**修复 2 项**:① config gate --json 错误从 stderr → stdout(TS 机器调用方此前拿不到结构化错误,透明度缺口);② setup NDJSON vault_initializer 重复 item_id → 独立 zotero_junction id。**备注(发布时)**:PyPI 线上 metadata 仍 Requires-Python >=3.10(本地 wheel 构建正确 >=3.11,随 1.6.0 发布修复)。全量 3133 py / 385 vitest。commit `ee59288f` | §9.N |
| 2026-08-11 | **#174 OWNER ACCEPT + CLOSED** | owner final ACCEPT(0 blocking/P1;Standards PASS;Frozen-spec PASS;Architecture gate PASS)。CI run 31619685405 全绿(L0-L4b 含 J-Matrix + L4b Deterministic Gate)后 close #174。**Wayfinder #135 的 C0/R/C1/T1-T9/F 全部完成**——最后 authority switch 落地。剩余:release verification(wheel smoke、PyPI Requires-Python>=3.11、candidate promotion)→ RC/#81,按 #143 不阻塞实现验收 | §9.N |
| 2026-08-11 | F/#174 pass-2 review(双轴) | **Standards pass-2: 0 findings**(fresh-child verify 在 republish 前、restore 全覆盖、无重复 pointer 解析)。**Spec pass-2: 2 findings 已修**——① probe version_mismatch action 指向未注册 foundation.setup → 改为注册的 foundation.update(verb=update);顺带修 config_missing 误标 foundation.update/"Update PaperForge" → foundation.setup/"Install PaperForge";② foundation.update preflight 缺 pointer gate → 无 pointer 时 unavailable(pointer.missing,与 repair 对称)。测试:probe action_id/verb 断言、update preflight gate regression。全量 3132 py / 385 vitest。commits `260f0f18` + `5746ced4` | §9.N |
| 2026-08-11 | F/#174 owner final corrective(2 P1) | P1-1 `foundation.repair` 政策如实(remote_possible/mutating/confirmation=required/automatic=false——真实 handler 会 pip install + republish pointer,registry 是单一政策真相);preflight 无 pointer → unavailable(pointer.missing);测试:descriptor 真相、无 --confirm → rc3、无 pointer → rc1。P1-2 handshake 第二步 fail-closed:vaultPath 必填;probe exec failure/malformed/unexpected state → fail;显式 pre-setup pass(ready/config_missing/config_corrupt);8 个 handshake 契约测试。全量 3132 py / 385 vitest。commit `109d2d43`。**#174 达到 owner final accept 状态** | §9.N |
| 2026-08-11 | F/#174 reviewer findings(双轴) | 两轴并行 review(Standards + Spec)对 F/#174 全 diff。**Spec 3 findings**:① handshake 补 `probe installation --json`(fresh process,version_mismatch → fail;config-missing 是 setup 前合法状态);② plugin setup journey 走 `--json` #137 NDJSON 真实路径;③ foundation.update/repair 注册(service 已 faithful:#137、零任意 args、scope=all;registry 回 7 actions)。**Standards 2 findings**:① runtime_repair 先 fresh-child 验证 pointer 解释器可导入 + 版本一致才 republish;② `make_cancellation_token().restore` 全部出口调用。commit `d4639de2`。全量 3129 py / 380 vitest。**待 owner 最终验收 #174** | §9.N |
| 2026-08-11 | F/#174 final corrective(owner 5 closure blockers) | **核心两刀**:① ManagedRuntime FSM 杀 → RuntimeBootstrap pre-runtime adapter(删 current/status/ensure/runtimeActionsForHealth/TTL cache/auto-repair;留 discoverInterpreter>=3.11 / platformGate / installOnce(one venv+pinned install+fresh version equality,never --user)/ handshake / readPointer(schema v1 四字段+绝对+fail-closed));全部消费方 pointer-only(installed-but-unpublished NOT usable)。② Setup Journey 第二条 pip 路径删(_installFoundation → installOnce → handshake → setup 发布 pointer);version mismatch → 显式 consent,zero pip before user action。**#137 闭合**:setup NDJSON 流式(逐步 phase/item_result)+ cancellation(rc130);update NDJSON+cancel;`repair --runtime` 独立 runtime lifecycle repair(≠ literature repair)。全量 3129 py / 380 vitest。commit `2ca4f616`。#174 待 owner 验收 | §9.N |
| 2026-08-11 | F/#174 managed-runtime shrink | TS 保留 discovery/platform gates/consent/ONE one-time venv+pinned install/pointer READ/handshake;删 slots/rollback/slot-ensure/runtime-health/TS pointer-write/rollback UI;`ensure()` 单 venv + `paperforge[vector]==<version>` + fresh verify + **不写 pointer**;`status()` 读 pointer.json schema v1(绝对路径),不支持 schema → not_installed;settings 版本 mismatch 自动修复后跑 `paperforge setup --modular`(fresh interpreter)发布 pointer;RuntimeHealth 删 previousVersion/PY;测试 40 managed-runtime + 409 vitest。全量 3125 py / 409 vitest。commit `cef70e4b`。#174 验收项 1-7 全部落地(候选矩阵/audit gate 待 CI) | §9.N |
| 2026-08-11 | F/#174 setup-boundary corrective(owner 3 P0+1 cleanup) | P0-1 setup 不再碰 .env(env_values/merge_env 移出 SetupPlan;C1 boundary,.env 仅 `auth migrate --from dotenv`);P0-2 `ensure_runtime_dependencies()`:openai/chromadb/sqlite_vec 当前解释器已装 → no-op;缺失 → 只装 `paperforge[vector]==<running>` + fresh-child verify(不重装包,保 python-first journey);P0-3 `paperforge setup --json` → #137 NDJSON(start/phase/item_result/exactly-one result|error terminal),插件接 LongTaskClient;P0-4 删 `--paddleocr-key`/`--paddleocr-url`(secret-in-argv+ignored)。全量 3125 py / 420 vitest。commit `4a36cc85`。**Python bootstrap authority 就绪,下一步 managed-runtime shrink** | §9.N |
| 2026-08-11 | F/#174 corrective(owner 5 P0+1 P1) | setup: machine/human 统一 semantics(先算 ok → 成功才 publish → json 失败也 rc1);**RuntimeInstaller 移出 SetupPlan**(setup = post-runtime:config/vault/agent/pointer,plugin 一次性安装后 handshake → setup 发布);update:抽 `perform_update` 纯 lifecycle service(无 prompt/无 print/无 UI confirm,fresh-child 验证安装版本后才 publish observed version,run_update 变薄 CLI wrapper);repair:旧 literature repair 撤 pointer hook(foundation.repair 绑错 domain op);registry:foundation.update+repair 撤注册(回 5 actions);pointer:全 schema v1 校验(四字段+绝对路径)。新测试 7 个。全量 3123 py / 420 vitest。commit `b4e14140`。**managed-runtime shrink 待 Python authority 验收后执行** | §9.N |
| 2026-08-11 | F/#174 cut 1 — Python pointer publication | `paperforge/runtime_pointer.py`:pointer.json schema v1,原子发布(os.replace),fail-soft read;**setup/update/repair 成功才发布**(Python 唯一 writer,interrupted ⇒ 无 pointer ⇒ consent reinstall);foundation.update/foundation.repair 注册(零任意 args,scope=all;setup 需 agent/vault 参数不注册);registry snapshot 5→7。全量 3116 py / 420 vitest。commit `075ee961`。#174 剩余:managed-runtime.ts 收缩(pointer READ 新格式、删 slots/rollback/ensure/runtime-health/pointer-write、plugin-first handshake 触发 setup 发布) | §9.N |
| 2026-08-11 | T9 post-closure audit evidence (2 points) | **exact-unit attribution**:generic read wrapper 按实际 path(字面量/path-var)emit 恰好一条 FilesystemReadFact,绝不每个声明 unit 各发一条;不可解析 path → UnresolvedFact。regression:readCanonicalPath('formal-library.json') → 恰好 1 fact(formal_library, client_cache.read)。**golden_170_canonical_read**:reviewed golden 记录 formal_library wrapped read → active advisory 规则 SATISFIED——补全 #149 promotion evidence ladder(synthetic→golden→real-repo)。全量 3113 py / 420 vitest;commit `444e2fb0`。**T9 全闭合;C0/R/C1/T1–T9 全部完成;唯一实现 frontier = F/#174** | §9.N |
| 2026-08-11 | T9 acceptance 5 — lifecycle promotion (#170) | Owner pin (comment 5267054759):4 条 client_read.*(formal_library/paperforge_config/ocr_state/memory_db)planned→active,advisory 保持;runtime_snapshots 不动(已 active);retrieval.v2 排除;advisory→blocking 留 soak 后独立 commit。tracked contract commit `26f058a6`;真实 repo audit 立即观察规则工作:formal_library/ocr_state bare readFileSync → VIOLATED(advisory)。全量 3111 py / 420 vitest;#170 closed——**T9 完成** | §9.N |
| 2026-08-11 | T9 closure corrective (#170, owner review P0×3+P1) | **P0-1** 默认 orchestrator 给 TS collector 传同一 default wrapper registry(原空——production audit 中 read wrappers 死;orchestrator-level fixture 证明 wrapper_id=client_cache.read)。**P0-2** 语义豁免回到 Contract:4 个 read adapter operations(bootstrap.pointer.read/client_cache.read/navigation.open/workspace.context,role=adapter)声明进 tracked contract operations;evaluator:wrapper_id 必须 ∈ contract-declared adapters,否则 VIOLATED(registry 识别是什么,Contract 决定是否允许)。**P0-3** CANONICAL_READ unresolved 不再做 operation-module scoping(动态 canonical path 影响所有相关 canonical-read 规则——fail incomplete 不猜)。**P1** runtime_state.snapshot 单元 id 统一(TS classifier + ReadSpec 匹配 contract subject,active client_read.runtime_snapshots 规则真正可见 direct read)。另:WrapperSpec._spec_dict 序列化 ReadSpec;相对 TS import 也索引。+6 测试;全量 3107 py / 420 vitest;commit `5bb041f3`。**lifecycle pin 就绪:owner 可 pin formal_library/paperforge_config/ocr_state/memory_db(planned→active,advisory 保持)** | §9.N |
| 2026-08-11 | T9 audit corrective (#170, owner review) | **#149 frozen model**: `FilesystemReadFact(operation_id/unit_id/wrapper_id/path_expression/evidence)` 替换 CanonicalReadFact;`Rule.allowed_read_wrappers` 删除——wrapper MEANING = collector 知识,semantic exemption = 契约 operation/role(rule 永不带 wrapper allowlist)。**TS collector 真实收集**:FS_READ sinks + bare filesystem_read facts + path.join 变量追溯(indexPath → formal_library)+ canonicalUnitForPath 分类;canonical-read wrapper 动态 path → UnresolvedFact。真实 repo:72 filesystem_read(formal_library×4、ocr_state×2)。**wrapper registry**:ReadSpec + registry kind=read;DEFAULT_PYTHON_REGISTRY 带 bootstrap.pointer.read/client_cache.read/navigation.open/workspace.context。**_read_facts scope 修**:规则恒 unit-bound(subject ∪ scope)。**_unresolved/_has_static_violation 扩展 CANONICAL_READ**(动态 path → unresolved;bare read VIOLATED 优先)。**tracked contract**:4 条 client_read.*(planned + advisory + effective_after #170)——owner 待 pin 的实体。全量 3106 py / 420 vitest;commit `7a887dbe`。**验收 5 lifecycle pin:待 owner 按建议 pin formal_library/paperforge_config/ocr_state/memory_db(不 pin runtime_snapshots/retrieval.v2)** | §9.N |
| 2026-08-11 | T9 acceptance 3+4 — CANONICAL_READ + UNRESOLVED semantics (#170) | **UNRESOLVED**: blocking+unresolved → INCOMPLETE + gate not green(原 FINDINGS+gate-eligible 缺陷;golden_126 publication.authority 修正);`_has_static_violation` 静态违规优先于 unresolved(QUERY_SIDE_EFFECT/REMOTE_INTENT/CANONICAL_WRITER/PUBLICATION_MARKER)。**CANONICAL_READ**:`CanonicalReadFact` + reconcile 评估分支(读须经注册 wrapper,否则 VIOLATED/advisory);`Rule.allowed_read_wrappers` wrapper registry 契约 round-trip;advisory 规则 client_read.formal_library/paperforge_config/ocr_state/memory_db/runtime_snapshots 携带 bootstrap.pointer.read/client_cache.read/navigation.open/workspace.context;collector wrapper specs 更新(T6:sync.attach_next_actions/run_terminal_followups → sync.reconcile_and_attach/chain.run_chain);goldens 审查非 blanket。+6 测试;全量 3104 py / 420 vitest;commit `d9216878`。**验收 5 lifecycle promotion:blocked —— #170 无 reviewed issue-comment pin 契约 entities** | §9.N |
| 2026-08-11 | T9 phase 1 — legacy command-string producers + parity (#170, in progress) | Raw command-string recommendation producers deleted from memory.py/paper_status.py/retrieve.py/search.py (wire never carries command text — migrated to diagnostics or registered action ids: next_action_id=embed.build, recommended_command_id, action.*_required codes). Single-producer parity tests: repo-wide grep asserts no action wire carries a command string; every reconcile-emitted action_id hydrates through a registered handler. Full suite 3098 py / 420 vitest; commit `31c5c9d7`. Remaining: CANONICAL_READ advisory rules + wrapper registry + golden re-pin (audit contract extension), UNRESOLVED semantics refinement, lifecycle promotion (blocked — no reviewed issue-comment pin of contract entities yet) | §9.N |
| 2026-08-11 | T8 closure corrective (#169, owner review P0×6 + gaps) | **P0-1** ONE `ActionClient` (action-client.ts): 唯一 argv builder (`--key K` 重复、`--confirm <id>`、`--follow auto`、`--json`);orchestrator/workspace/bridge 消费 ActionRequest 不再拼 argv;confirmed 请求带精确 --confirm。**P0-2** 删全局 `_executed`——TS 只留 in-flight guard;跨调用抑制归 Python W2(input digest);同 scope 后续合法 repair 不被 suppress(已测)。**P0-3/P0-4** ONE `LongTaskClient` + stateful `NdjsonStreamParser`(unknown event/second terminal/event-after-terminal/EOF-without-terminal 全 fail closed);controllers 传播 protocolFailure。**P0-5** embed stop 残留删除:EmbedBuildController.stop() = stdin token + grace + taskkill /T /F / POSIX group;OCR Workspace `_runningMode` 防错 Stop。**P0-6** C1 env 隔离:所有新 spawn/execFile 用 paperforgeEnrichedEnv(),绝不 merge process.env。`autoSyncEnabled` 生效(off → 零 sync)。O4:settings dispatch 按 action_id typed(memory.rebuild_vector → embed);ACTIONS 执行走 typed `toolArgvFor`;TS `ActionPrimary.command` 删。T7 inherited:ocr.rebuild_derived all-scope 解析 rebuildable keys(不再静默 0 篇)。测试:orchestrator 重写、6 个 stateful parser failure cases、typed dispatch;全量 3096 py / 420 vitest;commit `0df2e838`;#169 closed;装 pytest-xdist(全量 ~2.5min 并行) | §9.N |
| 2026-08-11 | T8 — action/sync client cutover + TS policy deletion (#169) | **O4 gate**: ALLOWED_ACTIONS/isAutomaticLocal/requiresConfirmation/(verb,command) dispatch/_runIndexRefreshChain/probe action_primary.command/dashboard cmd strings — all deleted from plugin/src; zero action-policy in TS (registry authority; wire carries policy fields). **Two machine modes** (#137): python-bridge `runAction` (single PFResult JSON) + `runLongTask` (NDJSON + stdin PAPERFORGE_STOP, shell:false); orchestrator derives argv from wire (`action run <id> --scope <kind> [--key ...]`), normalized-scope dedupe. **Timer**: data.json cadence (autoSyncEnabled/autoSyncIntervalSeconds, default 120), vault-open tick + interval → sync only; mtime scanner deleted. **OCR Workspace rebuild** = `action run ocr.rebuild_derived` (Python chain derives follow-ups; embed.resume pending from descriptors). **progress-parser** consumes #137 NDJSON (protocol-fail closed); colon tokens deleted. probe `action_primary.command` deleted. Tests rewritten to NDJSON/argv contract; full suite 3096 py / 414 vitest; commit `3986cd13`; #169 closed | §9.N |
| 2026-08-11 | T7 — OCR vertical journey + reader gate (#168) | **#137 NDJSON**: `core/ndjson.py` (start/phase/progress/item_result + exactly-one result|error|cancelled terminal); embed.build + ocr redo/rebuild stream mode; colon-token family retired; human logs → stderr (stdout machine-only; single PFResult JSON OR one NDJSON stream). **Reader gate** (#159 §6): `reader_gate.py` — retrieval/vector != current → hit dropped; no lineage infra → pass-through; wired at retrieve.py + gateway.py. **O1**: per-paper SAVEPOINT in memory.builder (A fails → B untouched); successful_keys → chain reconcile scope = actual success. **O3**: pending embed.resume encodes nothing until --confirm; confirmed dispatch = exactly requested keys. **Break recovery**: chain crash → reconcile re-derives identical intents. 7 journey + 17 NDJSON contract tests (old token contracts replaced); full suite 3094 py / 426 vitest; commit `bd64de01`; #168 closed | §9.N |
| 2026-08-11 | T6 — follow-up chain runner + sync cutover (#167) | `paperforge/actions/chain.py`: constant depth (root=0, children=1, MAX_FOLLOW_UP_DEPTH=4), per-invocation dedupe by canonical (action_id, normalized scope), auto inlines automatic-local (memory.build), remote/destructive/confirmation stay pending with reason codes; confirmed parent never confirms a child; cancellation halts at next action boundary; pre-dispatch failures record failed step, no children. **Sync cutover**: sync → reconcile(all) (never changed_keys-only) → generic chain runner; `_attach_next_actions`/`_run_terminal_followups`/`_run_memory_build` deleted; reconcile = single producer (post-publish reconcile(successful_keys) per layer). O2 by construction (failed action → no children → no embed.resume anywhere). CLI `action run --follow none|auto`. 10 chain + 10 sync frozen-contract tests; golden_127_sync_embed re-observed (implicit-remote fact deleted, materialization re-pinned to `_reconcile_and_attach`); full suite 3077 py / 426 vitest; commits `7259f966`+`e8cb1407`; #167 closed | §9.N |
| 2026-08-11 | T5 — reconcile module + registry closure (#166) | `paperforge/reconcile.py`: three-layer observation (global desired → global substrate → per-paper lineage), global repair frontier first (exactly one global intent on substrate incompatibility; per-paper facets blocked_global), minimal per-paper frontier (prereqs-satisfied first-layer deficits only), scope merging by canonical action, single PFResult.next_actions channel (no internal intents wire); pure derivation + emission; unknown facets fail closed; registry closed: ocr.run + embed.build registered (credential preflights); CLI `reconcile [--scope --key --json]`; commits `d9408411` + corrective `b87235f5`; #166 closed | §9.N |
| 2026-08-11 | T5 corrective — owner review #166 (P0×3, P1×3) | **P0-1** substrate ≠ availability: new pure observer `paperforge/embedding/substrate.py` (desired identity vs published build_state+vec0 layout) shared by reconcile / run_build / embed.resume preflight; model/endpoint/layout/legacy → global embed.build(all); per-paper missing → embed.resume(keys); credential never flips substrate, never blocks OCR/retrieval repair; vec0-never-built stays per-paper. **P0-2** W2 implemented: overwrite-only last-attempt record (reconcile-last-attempts.json) + input digest over facet states AND lineage identities (probe_lineage carries identities; policy-mismatch stale carries recomputed identity as cause fingerprint); same digest+failed → suppressed, digest changed → re-emitted; record_last_attempt is T6 write side. **P0-3** requested_resume captured BEFORE all effective-resume gates in run_build + isolated tests (no-rows-only downgrade → shadow unscoped / fail-fast scoped). **P1** reconcile→PFResult only; unregistered never emitted (diagnostic); facet_summary pre-global-first. Full suite 3068 passed / 0 failed | §9.N |
| 2026-08-11 | T3 (#164) + T4 (#165) — scoped builds + papers-scope registry | T3: `build_for_keys` (keys=None full-library; unknown key → exit 2; scoped never deletes; correction rewrite limited to requested; deleted=[]) — A/B/C byte-identical on scoped request. T4: embed papers-scope + build-core `--key`; tests: scoped request leaves untouched papers' rowid/updated_at/units/objects/aliases/assets/manifests equal. #164/#165 closed via #184/#185 | §9.N |
| 2026-08-10 | T2 — action registry + runner + CLI (#163) | `paperforge/actions/`: types (ActionSpec/Scope/Request/Context/Preflight/Intent), registry (memory.build/embed.resume all-scope, invariant validation, no command/argv), runner (lookup→scope→preflight→confirmation→handler→PFResult; follow-up chain depth 4 + dedupe + pending/executed/skipped), `action list/describe/run` (exit 2/3/1/0, SIGINT→cancelled rc130); preflight consumes C0 config + C1 credential status; existing next_actions/sync suites pass unmodified; Python 3018/296; J1 gains action contract tests | §9.N |
| 2026-06-17 | OCR-v2 boundary close-out pass | Zone-boundary fixes, tail/backmatter shrink, correspondence routing. 202P/1F/43S | §9.2 |
| 2026-06-18 | Readiness-gates implementation | Gates 1-4 complete + blind audit protocol. 249/249 figure/health/document pass | §9.3 |
| 2026-06-19 | Blind audit (5 unseen papers) | All PASS — no new failure families. OCR-v2 declared "state healthy" | §9.3 |
| 2026-06-21~22 | Figure merge: greedy → global distance clustering | Union-find clustering, 261 tests. Caption-independent semantic grouping, ownership registry, local pairing, conflict detection | §9.5 |
| 2026-06-22 | Cross-page caption consumption fix | Reader/render contract breach fixed — cross-page matches now consume caption on legend page | §9.4 |
| 2026-06-23 | Visual grammar hardening | Composite parent detection, dense page arbitration, figure/table separator veto, dedup refinement | §9.5 |
| 2026-06-26 | Rebuild production run (699 papers) | `--resume` checkpoint, glob fallback, N6XCZD25 body text fix | §9.6 |
| 2026-06-26 | Figure number inference + container admission | Leading `[1]` gap filled, blue sidebar box rendered as `[!NOTE]` | §9.7 |
| 2026-06-26 | UI polish (plugin) | Dashboard CSS, maintenance tab redesign, Vercel-style polish | §9.8 |
| 2026-06-27 | Rebuild audit + index repair | 6 hard-block/high bugs fixed (sync, workspace, field registry) | §9.9 |
| 2026-06-27 | Deep investigation — 5-fix spec | P0 all committed (ref sort, caption insert, figure containment). P1 backmatter in progress | §9.10 |
| 2026-06-28 | P1 backmatter boundary committed | Ref-anchored partition (`3e33e5b`). Pre-ref=body flow confirmed (`9b72783`). 16/16 tests pass. All 5 audit papers verified. | §9.11 |
| 2026-06-28 | Gate 5 blind audit + pre-ref tail zone fix | Gate 5: 24YKLTHQ (13p) + 4KCHGV2Z (9p) rebuilt post-P1. Found pre-ref body pages misclassified as tail_nonref_hold_zone. Root cause: _apply_zone_labels re-applies stale region_bus after ref partition. Fixed by stripping pre_ref block IDs from tail zone. 4KCHGV2Z P7: tail=20 → body=2+disp=5. All 286 figure/backmatter tests green. | §9.12 |
| 2026-06-28 | Gate 5 frontmatter fix series (3 fixes) | 24YKLTHQ: author byline lowercase guard, metadata body_start fix, frontmatter heading normalization (no text matching). All 3 fixes verified on real paper, 461 tests pass, 0 new regressions. | §9.13 |
| 2026-06-28 | Test fix session: 25 tests reconciled | Fixed 10 stale test issues: non_body_insert guard, caffard abstract, legend_like role, structural gate, backmatter heading render, state machine (done_degraded), body_zone anchor, rebuild backfill skip, truth surface docs, trace-vs-expectations (10 assertions). **616 OCR tests, 0 failed.** Expectations updated for post-P1 behavior. | §9.14 |
| 2026-07-04 | A/B/C OCR deepening merge + pre-merge blocker cleanup | Merged Workstream A (`ocr_object_writeback.py`), Workstream B (`ocr_tail_settlement.py`), and Workstream C (`pre_match_normalize` / `post_match_normalize` behind `OCR_PIPELINE_V3`) to `master`. Closed pre-merge blockers: page-qualified writeback lookup, contained-text ownership contract, same-page contained-text guard, and v3 rescue equivalence. Verification: 99 focused tests passed on merged `master`. | §9.24 |
| 2026-06-28 | Data-driven truth audit (2 papers) | 2HEUD5P9 (27p) + 4AG67PBH (25p) — no vision (model limit). Found 3 pipeline defect patterns: zone_leak_frontmatter_to_body (2 papers), reference_boundary_body_mix (2 papers), title_repeat_page2 (1 paper). 12 ghost unknown_structural blocks in 2HEUD5P9. Findings saved to audit/2026-06-28-data-audit-findings.json. | §9.15 |
| 2026-07-05 | Figure inner_text crop merge + V3 default-on | Figure inner_text identified but silently dropped — crop bbox expanded to include owned figure_inner_text blocks (variables in images retained). Rebuild path wired to apply_object_writebacks. Full vault corpus diff: 547/555 no diff, 5/555 v3 improvements. OCR_PIPELINE_V3 enabled by default. 105 tests + 555-paper diff green. | §9.25 |
| 2026-06-28 | P0 author bio detection implementation | Created ocr_bio.py with category-weighted bio scoring, Pass C (post_ref_bio_cleanup), figure match guards. Wired author_bio_asset role contract + pipeline. 30 new tests pass. 1041 total OCR tests, 0 regressions. Commits: `e2f0c8a`, `7810eb1`. | §9.16 |
| 2026-06-28 | P1 author bio detection implementation | Added residual_author_bio_pass (figure-residual portrait assets), extended post_ref_bio_cleanup for figure_caption, tag_figure_contained_text protection. 7 new P1 tests. 1018 total OCR tests, 0 regressions. Commit: `7a1cc5e`. | §9.17 |
| 2026-07-01 | Audit fix commits + orientation-aware rotated figure normalization | Commit 1 (`2d40ad9`) + Commit 2 (`21bdfd0`) + Commit 4 (`7670227`) landed, then refactored rotated-caption handling out of synthetic fallback into normal figure pre-match. Added PyMuPDF `dir/wmode` capture, same-page rotated settlement, rotated crop render. U746UJ7G now matches via `same_page_rotated`; KUR9PBJC unchanged. 422 regression tests pass. | §9.18 |
| 2026-07-01 | Asset-internal figure number recovery implementation | Added `extract_pdf_lines_normalized` helper, `_recover_missing_figure_numbers_from_assets` pass in `build_figure_inventory`, 5 gate functions, 2 pattern constants. U746UJ7G `figure_unknown_000` → `figure_002` with recovered label "Plot of Criteria Time". 6 new tests. 428 regression tests pass. | §9.19 |
| 2026-07-02 | Round 2 truth audit + 3 targeted bug fixes for 37LK5T97 | Batch-audited 10 fresh papers (5 GREEN / 4 YELLOW / 1 RED). 37LK5T97 found with Figure 1 broken (sidecar caption demoted) + 6 unmatched rotated tables. Fixes: (1) `_is_sidecar_candidate` guard in candidate_resolution, (2) `adjacent_x`+`y_overlap` in score_table_match for rotated captions, (3) rotated table render bbox+270° correction. Also: rotated figure crop quality fix (4x zoom + coordinate normalization in `_crop_asset_from_pdf`). Commits: `59cd01a`, `bd3f3b6`, `86e0d14`. 428 regression tests pass. | §9.20 |
| 2026-07-02 | Zone/role robustness completion — Figure caption prefix recovery + inline table fix + table matching audit | Figure caption prefix recovery from PDF text layer (`_recover_figure_heading_prefix`): 5S7UI34M 4→9 matched figures, 33→1 unmatched. Inline `<table>` HTML role fix: 650 blocks now `table_html` after rebuild (priority bug: raw_label=table fired before `<table>` check). Table matching audit: 620 remaining `media_asset` pending full rebuild. 585 figure/table/role tests pass. | §9.21 |
| 2026-07-03 | Figure pipeline vnext cutover completed | Implemented all remaining vnext passes (composite parent, group/classic sequential, unresolved consolidation, accounting), expanded compare harness, curated 5-paper cutover corpus covering all 9 spec categories, generated diff review (improvement=2 / equivalent=2 / parity=1 / regression=0), updated legacy figure tests for vnext contract, and switched `build_figure_inventory(...)` wrapper to vnext on branch `feat/figure-pipeline-vnext`. Verification: 346 tests passed. | §9.22 |
| 2026-07-03 | OCR pairing framework merge-unblock pass | Cleared the remaining merge blockers on `feat/ocr-pairing-framework`: moved figure-only rotation enrichment out of generic state, upgraded table cutover validation to semantic parity across 6 runnable real-paper fixtures including `37LK5T97`, and cleaned touched-file lint/format issues. Verification: 357 targeted tests passed; merge-ready. | §9.23 |
| 2026-07-10 | Retrieval architecture Wayfinder inventory | Charted the end-to-end recovery map and resolved the live-architecture ticket. Confirmed four P0 contract breaks: invalid sql.js metadata SQL, missing `--deep`, ignored `data.chunks`, and build write-then-delete. Published the evidence audit; no production fix applied. | [Architecture audit](https://gist.github.com/LLLin000/aaf5505a991e85ad9bb4cafa922f48bf) |
| 2026-07-14 | OCR rebuild streaming + maintenance UX | Added flushed rebuild/redo progress contracts, full keyed redo, cross-platform cooperative stop, canonical All/Recommended filters, selected batch actions, and cache migration. Verification: 99 focused Python tests, 93 plugin tests, typecheck/build, and live 734/700-row Obsidian state with no captured errors. | §2-4 |
| 2026-07-14 | Control-center Wayfinder charted | Defined the six-module destination (安装 / 文献库 / OCR / 记忆 / 维护 / 帮助), module-independent readiness, actionable-only maintenance, opt-in OCR issue drafts, and a three-ticket research frontier. | [Wayfinder map](https://github.com/LLLin000/PaperForge/issues/65) |
| 2026-07-14 | Capability model, runtime architecture, and maintenance regression fixes | Closed #69 (orthogonal capability/activity/attention model) and #70 (plugin-managed immutable runtime slots). Added canonical per-row maintenance action routing, redo confirmation gate, and cache-manifest preservation across 5 plugin files. Verification: 19/19 maintenance tests pass. | [Capability contract](docs/research/2026-07-14-capability-state-action-contract.md), [Runtime architecture](docs/research/2026-07-14-managed-runtime-architecture.md) |
| 2026-07-14 | Control-center current-contract audit | Inventoried setup, configuration, runtime, readiness, persistence, cache, failure, and recovery contracts across plugin and Python. Closed #66 with a ranked contradiction matrix and preserve/migrate/remove plan; unblocked #69 while #70 remains blocked on desktop/runtime evidence. | [Contract audit](https://github.com/LLLin000/PaperForge/issues/66#issuecomment-4968837257) |
| 2026-07-14 | Obsidian and desktop recovery research | Closed #67 and #68 with primary-source pattern reports. Preserved the six-module IA, independent capability probes, Obsidian-managed plugin updates, module-scoped recovery, local diagnostics, and user-reviewed issue drafts; unblocked #70. | [#67](https://github.com/LLLin000/PaperForge/issues/67#issuecomment-4970653461), [#68](https://github.com/LLLin000/PaperForge/issues/68#issuecomment-4970660288) |
| 2026-07-15 | Six-module control-center + maintenance inbox prototypes completed | Closed #71 (six-module HTML prototype, 5 scenarios, plain-button switcher, responsive 768px) with independent Critical/Important PASS review and browser verification. Closed #72 (actionable-only inbox, inline issue-draft review, confirmation-first report) with same review gate. Both prototype pairs passed all review dimensions. No production code changed. | `docs/prototypes/2026-07-14-six-module-control-center.{html,md}`, `docs/prototypes/2026-07-14-maintenance-issue-reporting.{html,md}` |
| 2026-07-15 | Control-center PRD split + first production slice | Published PRD #74 and eight native dependency-linked issues (#75–#82). Implemented #75: one SetupPlan for all setup entry points, schema-v2 `vault_config`, warned v1 read fallback, complete path forwarding, visible deprecation, and non-zero required-step failures. Verification: 61/61 focused tests; independent Spec PASS / Quality APPROVED. | [PRD #74](https://github.com/LLLin000/PaperForge/issues/74), [Issue #75](https://github.com/LLLin000/PaperForge/issues/75) |
| 2026-07-15 | Installation/Help capability tracer + navigation refinement | Implemented schema-v1 probe envelopes, six-module Overview, setup-complete migration, strict persistence/TTL validation, backend-owned action labels and dispatch, responsive/focus-visible UI, and generated bundle. Verification: 21 backend tests, 169 plugin tests, typecheck/build, live Obsidian stale-cache/action-label smoke test, independent review PASS. Matt flow refined PRD #74 and existing #77/#78/#80 without duplicating issues. | [Issue #76](https://github.com/LLLin000/PaperForge/issues/76), [PRD refinement](https://github.com/LLLin000/PaperForge/issues/74#issuecomment-4980322098) |
| 2026-07-15 | Managed Runtime lifecycle + final navigation shell | Completed #77 with immutable runtime slots, synchronous fail-closed `current`, probed `status`, install/repair/update/rollback/cancel/retention, managed-first dispatch, Release-N fallback, four-destination navigation, Installation detail, Agent integration, and Help focus restoration. Verification: 192 focused + 289 full tests; typecheck/build clean. Merged to `master` in `173a4e8..4ef9e98`. | [Issue #77](https://github.com/LLLin000/PaperForge/issues/77) |
| 2026-07-18 | OMP Matt workflow enforcement | Removed all discoverable Superpowers installations, retained canonical Ask Matt skills, added sticky project rules, and installed an auto-discovered hook for one-writer batches, worktree isolation, and fresh verification gates. Fresh OMP smoke reached the hook; 7/7 deterministic guard cases passed. | `.omp/RULES.md`, `.omp/hooks/pre/matt-guard.ts` |
| 2026-07-18 | Library/OCR/Memory capability tracers (#78) | Implemented real capability probes for Library, OCR, and Memory with module-detail-navigation, installation-navigation, and capability-state views. Python owns capability facts; TypeScript exact allowlist/fail-closed rendering avoids duplicate classification. Verification: 58 backend + 171 plugin tests, typecheck/build clean, Obsidian 730px/768px smoke (no overflow, keyboard focus/restore, heading focus/restore, diagnostic disclosure, OCR rebuild progress 3/10, cooperative stop, idle/re-probe). | §2-4 |
| 2026-07-19 | SecretStorage (#79) + Maintenance probe (#80) | Implemented SecretStorage capability secrets (backend-focused gate, plugin full suite). Implemented Maintenance probe: backend-derived actionable-only rows, privacy-safe local draft, accessible destructive confirmation via derived VerbModel with primary null for quality-ok items. Backend owns exact actions from `probe maintenance --json`; frontend renders downstream. Verification: backend focused gate 77/77; plugin full suite 381/382 (pre-existing capability-state test expecting help.stale but receiving help.invalid_response); typecheck/build clean; production bundle 264.4KB; Obsidian 1.12.7 smoke at 730 and 768 (entry focus, actionable-only, keyboard Enter, destructive confirmation with backend effect, focus trap/restoration, owned inert cleanup, redacted editable draft, no token/auto-open, explicit GitHub open only, URL re-redaction, no overflow). | §2-4 |
| 2026-07-19 | Literature-hub #78–#80 deployment recovery | Found Obsidian loading duplicate `.obsidian/plugins/paperforge.bak`; moved it outside plugin discovery, migrated OCR/Vector secrets with readback verification, synchronized manifest 1.11.4, installed the current backend into the canonical managed venv, restored startup migration, and warmed the shared Managed Runtime before dispatch. Live cold-restart checks showed real Library/OCR/Memory actions, four-button detail selector, three actionable Maintenance rows, configured secrets with no plaintext, and no captured errors. Verification: 384/384 plugin tests, typecheck/build clean, 259.3KB bundle. | §2-6 |
| 2026-07-19 | Control-center UX domain redesign | Live diagnosis proved that the current six-module vocabulary and navigation were not understandable despite passing earlier implementation gates. Completed a user grilling/domain-modeling session; approved five operational modules, three top-level destinations, dynamic setup, six user statuses, navigation-only cards, module-owned configuration, actionable-problem-only Maintenance, separate OCR workspace, and one-click redacted diagnostics. Added plugin domain language, ADR, Obsidian-native `DESIGN.md`, full UX specification, acceptance matrix, and ten dependency-ordered implementation slices. No production code changed. | `paperforge/plugin/CONTEXT.md`, `paperforge/plugin/DESIGN.md`, `project/current/control-center-ux-redesign.md`, `docs/adr/0001-capability-action-semantics.md` |
| 2026-07-19 | N+1 cutover repair + redesign issue map | Completed the final ManagedRuntime/SecretStorage repair (`b41b4c88`), verified 390/390 plugin tests, clean typecheck/build, and live managed dispatch. Kept #81 open for the owner-controlled release gate and #82 open for the future N+2 window. Closed superseded PRD #74; published replacement PRD #83 and dependency-ordered implementation issues #84–#93. No release performed. | §2–4 |
| 2026-07-20 | Control Center implementation, repair, and live page-by-page acceptance | Completed #84–#93, then repaired setup migration, stale state adaptation, duplicated legacy surfaces, action/notice localization, Chinese locale detection, primitive DOM compatibility, card-grid overflow, and transient baseline summary state. Real Obsidian 1.12.7 exercised Overview, all five Module Details, Maintenance, Help, and all four Setup Journey stages in English and Chinese; no untranslated keys or horizontal overflow. Verification: 420/420 plugin tests, clean typecheck/build, 280.1KB production bundle deployed to Literature-hub. | §2–6 |
| 2026-07-23 | Map #94 prototype reconciliation and UX contract audit | Repaired four target-state prototypes and aligned `DESIGN.md` plus FE/BE/CSS mappings: two top-level destinations, single-column Overview, module consequences, OCR cost/safety and next-release gating, three paper states, keyboard tab movement, focus restoration, and responsive controls. Browser checks at 375/768/1280 found no script errors or overflow; screenshot QA found no confirmed visual defects. Production code and deployment were unchanged. | §2–6 |
| 2026-07-26 | Real test-vault UX repair | Drove actual Obsidian 1.12.7 against `D:\L\Med\test`: found and fixed the OCR Workspace doubled-path empty state, right-sidebar placement, live untranslated Control Center/SR text, and core CSS CTA override. Verification: 407/407 plugin tests; built/deployed plugin; Control Center, Smart Retrieval, and OCR Workspace smoke—593 records loaded, idle activity hidden, main-tab width 960px, localized labels, accent CTA. | §2–6 |
| 2026-07-26 | Fresh Setup Journey configuration repair | Reworked live Stage 2 into one editable and verified Zotero/vault-folder form; stale Foundation and Library evidence now refreshes automatically. Verification: 407/407 plugin tests; build/deploy to `D:\L\Med\test`; live Obsidian validation rejected an invalid Zotero path, disabled Continue, then recovered after restoring the configured path; no raw i18n keys. | §2–6 |
| 2026-07-26 | Foundation/Library setup boundary repair | Removed the nested legacy wizard from reinstall. Foundation now takes a Python executable and only validates/installs the PaperForge package; Stage 2 alone saves and verifies Zotero plus four vault paths. Verification: 407/407 plugin tests, 296.4KB build deployed to `D:\L\Med\test`, live Foundation run left `paperforge.json` SHA-256 unchanged, and all five live module details had no raw localization keys. | §2–6 |
| 2026-07-26 | Optional setup configuration repair | Aligned Stage 3 with `setup-journey.html`: selected OCR, Smart Retrieval, and Agent cards now reveal their configuration. OCR/Retrieval keys use Obsidian SecretStorage; Retrieval preserves model/base URL; Agent platform persists in the vault config. Verification: 407/407 plugin tests, 299.9KB build deployed to `D:\L\Med\test`, all three cards rendered with two secret fields, four configuration inputs, one platform selector, vertical scroll, and localized controls. | §2–6 |
| 2026-07-26 | Smart Retrieval credential profile repair | Replaced the global vector-store secret with 61-character SHA-256-derived SecretStorage profile IDs keyed by Base URL and model; this satisfies Obsidian’s identifier limit. All Memory/Embed/search launchers resolve only the current profile; unscoped legacy keys remain unavailable rather than being guessed onto a changed provider. Verification: 409/409 plugin tests including profile-isolation, mismatch fail-closed, identifier-limit, and unscoped-legacy contracts; typecheck/build clean; 301.4KB bundle deployed to `D:\L\Med\test`; live SecretStorage accepted a 61-character diagnostic ID and Stage 3 renders the saved Qwen/SiliconFlow profile as gray hints without the previous error. | §2–6 |
| 2026-07-26 | Setup review stale-state repair | Fixed Stage 3→4 navigation to re-probe Foundation and Library; Stage 4 now reports checking state and exposes a localized recheck only for a genuine unresolved prerequisite. Verification: 409/409 plugin tests; 302.1KB bundle deployed to `D:\L\Med\test`; after reload, live probes returned both prerequisites ready, “完成设置” became enabled, and completion returned to the localized Overview without raw keys. | §2–6 |
| 2026-07-26 | Foundation version-readiness repair | Passed the loaded plugin manifest version into `probe installation`; backend now emits `installation.version_mismatch` rather than ready when its package differs. The setup journey maps that state to forced reinstall; an exact match hides installation actions and enables Continue. Verification: focused probe 74/74 and plugin 409/409 tests; 302.3KB bundle deployed to `D:\L\Med\test`; live Obsidian exercised both mismatch→“重新安装” and restored match→only enabled “继续”, then completed setup to Overview. | §2–6 |
| 2026-07-26 | Ready-state reinstallation latch repair | Cleared the stale `_setupReinstallRequested` flag when Foundation returns ready and made the render/Continue gates depend on the current envelope, not a previous recovery request. Verification: 409/409 plugin tests; bundle deployed to `D:\L\Med\test`; live Obsidian forced the stale latch true, re-probed ready, then rendered only enabled “继续” with no “重新安装”, before returning to the completed Overview. | §2–6 |
| 2026-07-26 | Retrieval action and Agent readiness repair | Restored the localized “构建索引” action for `memory.index_stale`, preserved its exact allowlisted `embed build --force` dispatch, and changed Agent from a permanent placeholder to selected-platform `paperforge/SKILL.md` deployment evidence. Verified profile-aware SecretStorage clears the obsolete migration banner without touching legacy plaintext. Verification: 411/411 plugin tests; 303.3KB bundle deployed to `D:\L\Med\test`; live Obsidian shows no migration banner, secure credential configured, stale-index “构建索引” button, and Agent state ready. | §2–6 |
| 2026-07-26 | Smart Retrieval live rebuild completion repair | Real `D:\L\Med\test` rebuild exposed three runtime defects: Python local-import shadowing, missing SOCKS transport under the configured proxy, and an `object_chunk_count` snapshot signature mismatch. Hoisted the helpers, added `socksio` to vector dependencies, fixed the snapshot contract, and surfaced terminal stderr in the localized notice. The rebuilt 593-paper vec0 index now probes `memory.ready`; the ready page has no stale action-required impact box and its single configuration disclosure contains API key, Base URL, and model. Verification: 414/414 plugin tests, TypeScript/build clean, 6 focused Python tests; full Python collection remains blocked by two pre-existing removed-symbol imports. | §2–6 |
| 2026-07-26 | OCR workspace table layout and command registration repair | Real Obsidian 1.12.7 against `D:\L\Med\test` removed conflicting old flex-based table CSS, restored `table-layout: fixed` semantics for 6-column table, fixed `.pf-ocr-ws-col-date` missing nowrap/muted styling, removed hardcoded "PaperForge:" prefix from all 3 command registrations. Ribbon "PaperForge OCR Workspace" visible in sidebar; command "PaperForge: Open OCR Workspace" registered in ctrl+p; 593-paper table renders with all 6 columns visible, 924×924 scroll/client width (no overflow). Verification: 414/414 plugin tests, 593-row table, no overflow. | §2–6 |
| 2026-07-31 | Retrieval v2 optimization series (issues #113–#117) | 14 commits (`d4cc2fbf`→`a787fc23`): 6 missing paper_id indexes, `get_embed_status(probe=False)` fast path (6.6s→0.46s), fulltext copy size+mtime guard, force rebuild reverted to conservative sqlite3.backup protocol, **#116 per-paper incremental memory build** (materialized `paper_state_hash` diff, `upsert_paper_state` with ON CONFLICT DO UPDATE, in-transaction vector invalidation, orphan-safe log imports, fresh/destructive/additive migration routing). 3 GPT review cycles, 12 P0 fixes. **39 tests pass** incl. 7 new OCR integration tests (fresh build, OCR-only change, artifacts-disappear fast+metadata paths, partial state, tx rollback). #117 opened for atomic shadow vector rebuild. | §2–6 |
| 2026-07-31 | #117 reopen review — 5 P0s + real-vault E2E | Commit `ae3e505d` (5 P0s: force entry UnboundLocalError/NameError, writer lock for all build variants + `build_from_index`, unified `open_live_reader` barrier across 7 reader sites, checkpoint failure aborts publish, failure paths raise through unified handler) + commit `960a60c8` (real-environment E2E on production-data replica: `get_connection` WAL flip-back after publish fixed — WAL only initialized on new DBs; build_state model loss after shadow publish fixed — completed mark carries model/mode/total, resume no longer re-embeds everything). Verified live: force→35 chunks→publish (journal stays DELETE), resume hash-skip, 8 concurrent readers during publish clean, API-failure abort preserves live, all prod read-only commands clean on 868-paper vault. | §2–6 |
| 2026-08-20 | **S1–S6 lightweight certification** | **#191 synchronized** to frozen contract (stale-plan + verified-switch + external_action single-call inspect) via `gh issue edit`; **#191 remains ready-for-agent** without product code change. Executed **S1→S2→S4→S5→S3→S6** on disposable minimal fixtures (worktree `.cert-462398cb` at `462398cb`, venv `pf-cert-s1-venv` 3.14.0, docs `781910f3`): S1 `setup --modular` → `probe ready` (Foundation independent, #191 gap: skill still deployed); S2 2-paper `formal-library` + `memory build` → `status`/`paper-status`/`read`/`search`/`retrieve --paper`/`reconcile`/`sync` all pass without `.obsidian`; S4 maintenance honest (unknown key `PATH_NOT_FOUND`, `config.corrupt` fail-closed, `prune` dry-run); S5 `action run ocr.run` → `confirmation_required` rc3, `--force` → unrecognized, `prune --force` safe; S3 chain `setup→memory→search→read→retrieve→embed` without Obsidian (`embed.build` → explicit `401`); S6 `config corrupt` → `invalid` fail-closed + restore → `setup` repeat idempotent + `probe ready` + `read` persists. **No RC blocker.** #191 real gaps: skill in SetupPlan, retired config fields, missing `inspect/plan/apply/verify` + `plan_stale` + verified-switch `relocate` + `external_action/secure_external`; S8 multi-client concurrency not live-proven. Matrix `project/current/cert-462398cb-S1-S6-matrix.md`. | §2.12, §6 |
| 2026-07-31 | #117 final hardening — commit-point + SEALED + identity routing |
| 2026-07-31 | #117 round-5 hardening — mutator locks + stop control-plane + full-repo gate |
| 2026-07-31 | #117 round-6 — protocol-combination + unified layout contract |
| 2026-07-31 | #117 round-7 — final wiring (effective identity + honest empty + per-collection verify) | Commit `e0901d55`: P0-1 get_effective_api_base_url() unified (provider/dim-cache/identity/persisted state), VECTOR_IDENTITY_VERSION=1 legacy-rebuild; P0-2 vec/meta read separately, unreadable never zeroed, has_any_rows = vec OR meta, routing fail-closed; P1-1 _complete_one accumulates per-collection expected_counts, production verify passes them, candidate records vector_expected_*; P1-2 ensure_vec_tables returns dimension, _expected_dim flows to metadata+verifier, candidate-DDL re-read deleted; stop completed_before_stop race. 4 new tests; shadow 36/36; core 191 pass / 14 baseline; FULL repo 2526 pass / 89 baseline name-for-name; diff self-reviewed. | §2–6 | Commit `cfbfe076`: P0-1 post-publish non-JSON AttributeError fixed (warnings field + plain-text output); P0-2 requires_shadow forces resume=False for EVERY trigger (endpoint/layout change could publish empty candidate via hash-skips); P0-3 WriterLock same-instance re-entry no longer clears ownership (was leaking file lock); P0-4 prune whole destructive pass under WriterLock; P0-5 stop cross-platform _pid_alive + atomic sidecar + honest rc=1 when build survives kill window; P1-1 inspect_vector_layout()/VectorLayout unified contract for routing/ensure/verify; P1-2 empty-library first build initializes in place, VectorRebuildRequired only when existing vectors would be destroyed; P1-3 verifier requires six tables (0 rows legal, absent schema rejected) + per-collection expected + KNN on first non-empty collection. 4 new combination tests; shadow 32/32; FULL repo 2523 pass / 88 fail = baseline; ruff baseline identical. | §2–6 | Commit `15333bec`: P0-1 retrieve_chunks NameError restored (provider/query_embedding/n + sqlite3/Path imports lost in previous barrier migration — F821 caught 8 search.py errors at HEAD); P0-2 final build metadata written INTO candidate pre-seal (live lands self-complete) + outer handler returns rc=0/published=true for post-PUBLISHED failures; P0-3 ensure_vec_tables(allow_recreate=False) raises VectorRebuildRequired on live incremental writes + requires_shadow routes stored-vs-live dimension mismatch (no API probe per build); P0-4 delete_paper_vectors + migrate_chroma_to_vec0 wrapped in WriterLock (prune inherits); P0-5 stop control-plane sidecar (paperforge.embed-control.json), build loop checks _stop_requested(own_pid); P1-2 WriterLock depth keyed per DB path; P1-3 hybrid_search encodes BEFORE reader lock. Self-review before commit caught 2 indentation regressions + _now() scope bug + dimension-probe inefficiency. FULL repo: 2516 pass / 88 fail / 25 err = HEAD baseline name-for-name (stash-verified); shadow 28/28. | §2–6 | Commit `ff1f6d47`: P0-1 cleanup-state init before lock/try (resume errors no longer masked by UnboundLocalError); P0-2 `--force|--resume` mutually exclusive (CLI) + force overrides resume (programmatic); P0-3 os.replace = commit point (state=PUBLISHED set immediately after swap, sidecar cleanup best-effort can't fail publish, abort no-op after); P0-4 events.py import/return restored + write_correction_note under WriterLock; P1-1 SEALED state (NEW→PREPARED→BUILDING→SEALED→VERIFIED→PUBLISHED — verify inspects exactly the file publish swaps); P1-2 `_checkpoint_truncate` verifies busy/log/checkpointed tuple; P1-3 requires_shadow compares (endpoint, model) + endpoint persisted to build_state; fresh-DB WAL init captured pre-connect; reader depth keyed per DB path. 4 new tests; shadow 25/25; regression 180 pass / 14 pre-existing; prod commands clean. | §2–6 |
| 2026-08-03 | #117 close + 89-failure cleanup | GPT 9/10 acceptance; `8cbc4a93` (batches 1–3): 2 real code bugs (ocr max() empty-iterable, status layout check), 47 test-drift fixes, 6 OCR xfails bound to #118. 0 failed / 2596 passed / 7 xfailed; 25 errors = Windows sandbox locks (pass solo, absent on Linux). |
| 2026-08-03 | Release-gate P0-2…P0-7 → #119/#120/#121 | `3e658410` (#119+#120): paperforge[vector] install + sqlite_vec verify in managed runtime, honest deps status (memory.dependencies_missing), requires-python ≥3.11; EmbedBuildController (idle→failed state machine, credentials-before-spawn, duplicate-start guard, 45s cooperative stop, dispose on unload, force-rebuild confirm modal, EMBED_PHASE/NOTICE forward-compat). `8144fed8` (#121): single tag workflow (version/tag gate, wheel vector verify, one Release + checksums), real alls-green (version-check/ruff/protocol/plugin-build/e2e, allowed-skips removed), MIT+3.10 classifiers dropped. |
| 2026-08-04 | CI green for the first time since 1.5.15 | `7b1a93d7`: versions.json 1.5.14/1.5.15 rows, `.[test,vector]` installs, 12 F821 fixes (probe.py constant typo + 11 lazy-annotation imports), ruff gate = F821/F822/F823, 3 plugin test faults (process.platform triplet, .click() vs dispatchEvent, missing display() re-render). 9/9 CI jobs success; plugin vitest 414/414. |
| 2026-08-04 | #118 resolved — 7 OCR decision points closed | `42324657`: 2 REAL production bugs (redo main loop never emitted OCR_REDO_PROGRESS → frontend bar stuck at 0/N; unguarded fitz.open killed whole redo/rebuild batches on corrupt PDFs) + 3 test fixes (cluster-crop pdf_path=None contradiction, slugify 18xx expectation flipped to \d{4} reality, reader_figure_index preferring asset-owning entry). 75 passed/52 skipped touched files; 211 passed broad regression; CI green; zero xfails on master. Ghost matched-entry phenomenon (DWQQK2YB Fig 4: page=40 0-asset entry with legend_id=1 pointing at Fig 3 caption) tracked as #122. |
| 2026-08-04 | GPT release-review P0/P1 batch | `3824fb7b` + `0dd5b506`: 3 BLOCKERS fixed — EmbedBuildController spawn lacked `-m paperforge --vault` (click-to-crash), Setup Journey + bridge installed bare paperforge (Build Index broke for non-managed installs), publish.yml wheel smoke guaranteed-fail on clean runner; P1s — post-publish warning propagation (NOTICE + stderr tail), modal-cancel stuck-running + busy guard, idempotent release rerun; bump.py now writes versions.json; new L2.5 ocr-regression CI job (immediately caught 2 pre-existing prod-vault-dependent tests — skipif-gated; also cleaned 2 dead tests: get_vector_backend, TestAssertCollectionsHealthy). P0-4 no-key redo data safety → #123; #122 emission-defense analysis commented. CI 10/10 green; full suite 2616 passed / 0 failed / 25 Windows sandbox locks (solo pass). |
| 2026-08-04 | #123 + #122 — RC blockers closed | `caa432d8` (#123): single-owner redo executor — discover_redo_keys (read-only) → redo_papers_for_keys → _redo_one_paper_transaction (snapshot/mutate/validate/commit/rollback; exception-safe; restores ocr_dir + workspace fulltexts + note + index; paper-boundary stop; callback post-commit). 7 acceptance tests; old fixture layout was a false positive (PaperForge/ocr vs System/PaperForge/ocr). `91a3cd87`+`c8b2291b` (#122): emission-side ghost suppression — dominated 0-asset entries (explicit or inferred number) + legend identity-mismatch suppressed at inventory; reader skips same-numbered unmatched captions; asset contract bug fixed (matched_assets vs asset_block_ids) after 5 pairing tests caught it; DWQQK2YB = one Fig 4 (p41/7). Full suite 2628 passed / 0 failed / 25 sandbox locks; CI 10/10. |
| 2026-08-04 | OCR credential chain fix (release review) | `5ac491eb`: Run/Redo OCR spawned without PaddleOCR token — paperforgeEnrichedEnv STRIPS PADDLEOCR_* and no SecretStorage resolution was wired; button "did nothing" post-migration. Now resolves buildTargetedEnv(app, "ocr") BEFORE spawn (real child handle, #120 pattern), rebuild stays token-free; stderr tail (500) surfaced in failure Notice; credential failure resets idle + explicit notice. 5 new tests (env injection run/redo, rebuild exclusion, child timing, failure recovery); 419/419 plugin. |
| 2026-08-04 | GPT review round-2 P0 batch |
| 2026-08-05 | #125 canonical abstract island | Enforced one canonical abstract for headingless OCR documents: page-contiguous abstract islands, selection by distance to body transition, rejected-island disposition (following → body flow, preceding → frontmatter/zone evidence, ambiguous → fail closed). No text matching, no page caps, no confidence thresholds; renderer unchanged. Corpus blast radius measured: 11/398 fallback papers. | §2-6 |
| 2026-08-05 | #125 canonical abstract island | Implemented PRD #125: headingless documents with multiple page-disjoint abstract islands now select ONE canonical island nearest the body transition; rejected post-islands demote to body_paragraph (content preserved), pre-islands use frontmatter zone evidence; ambiguous cases fail closed with audit evidence. Z75FY7KR late-body order restored end-to-end. Tests: 247 focused + 2652 full passed / 0 failed (25 sandbox-lock errors baseline); corpus differential 398 fallback papers: exactly 11 multi-island papers changed, 388 single-island unchanged, 24 non-canonical blocks disposed (22 body_paragraph + 2 wrapper frontmatter_noise). | §2-6 | `2401f5c8`: OCR token fail-closed (frontend checks resolved env, backend rc includes blocked/error — no more false "OCR complete"); headless setup + wizard install paperforge[vector]; all 4 git fallbacks → PEP 508 `paperforge[vector] @ git+...`; _ocrStarting dup-start guard; publish.yml uploads all assets --clobber (rerun-safe) + waits for same-SHA All Checks Passed before PyPI. Tests: 421 plugin, 198 python regression, CI 10/10. |
| 2026-08-05 | #130 epic split + queue gates + #131 Slice A implementation | Published architecture-audit epic #130 with slices #131–#134 after external review (epistemic separation, publication authority, digest binding, assessment taxonomy). Enforced hard execution queue: only #131 `ready-for-agent`; #132/#127/#126/#129/#99/#133/#134 `blocked` with unblock criteria in #130; legacy #94–#105 blocked pending triage; #125 flagged needs-triage (implemented, closeout pending). Implemented #131: `paperforge/architecture_audit/` — five immutable layers (Contract/Survey/DeterministicAudit/Review/View), canonical serialization + semantic digests (run metadata excluded), stable deterministic finding IDs, pure reconciliation engine (rule_status + assessment clean|findings|incomplete|failed precedence, offline lifecycle), digest-bound compose, 8 synthetic + 3 golden evidence fixtures (real sha256 digests, repo-relative paths). Two-axis review found and fixed: authority identity check, fixture path prefix, aggregated source digest. Tests: 72/72 focused; full suite 2724 passed / 0 failed / 25 pre-existing sandbox-lock errors; ruff clean. | §2-6 |
| 2026-08-05 | #131 Slice A repair and verification | Repaired authority identity semantics, repository-relative evidence paths, source-complete golden digests, immutable metadata/expanded entity validators, audit/review validation, and standalone layer validation; added exact observer/delegated authority-set reconciliation and report-projection digest validation. Focused architecture tests: 101 passed; Ruff clean. Full Python suite: 2756 passed / 292 skipped / 25 known Windows sandbox-lock errors. Final two-axis re-review PASS; commit and owner acceptance pending. | §2.1–§4 |
| 2026-08-05 | #131 Slice A repair and verification | Repaired authority identity semantics, repository-relative evidence paths, source-complete golden digests, immutable metadata/expanded entity validators, audit/review validation, and standalone layer validation; added exact observer/delegated authority-set reconciliation and report-projection digest validation, failed-audit coverage union, enum validation, and deterministic malformed-input digest fallback. Focused architecture tests: 117 passed; Ruff clean. Full Python suite: 2772 passed / 292 skipped / 25 known Windows sandbox-lock errors. Final read-only review PASS; commits `73a782cf`, `078dd8a7`, and `963cc59a` are on `master`; owner acceptance pending. | §2.1–§4 |
| 2026-08-05 | #131 accepted; #132 review-overlay Skill implemented | Owner accepted #131 (closed, verification recorded); #132 promoted to `ready-for-agent`. Implemented Slice B: `paperforge/skills/architecture-review/` — model-invoked Skill with `trace` leading word and checkable completion checklist, references (adjudication taxonomy, 3 branches, fixture inventory), and `scripts/review_harness.py` (audit/emit CLI + importable API). Evals: 32 passed covering validated-input-first, digest/reconciler-version binding refusal, epistemic labeling, finding-ID integrity, adjudication completeness, mandatory 8-stage trace with enforced evidence pool, three branch shapes, review-record metadata, and skill-document contracts. Two-axis review found and fixed: trace manifest was optional, and saved-audit emits skipped evidence checks — both now fail closed; re-review PASS. Full suite: 2802 passed / 292 skipped / 25 known Windows sandbox-lock errors. Committed `5f03051e`; owner acceptance pending. | §2.1–§4 |
| 2026-08-05 | #132 accepted; mandatory triage checkpoint | Owner accepted and closed #132 (verification recorded; #130 Foundation gate complete). Executed the #130 triage checkpoint: scout-summarized all 21 open issues; classified every one (active: #127/#126/#129; owner decision: #81/#99; deferred: #63/#82/#94–#105/#133/#134; implemented-awaiting-closeout: #125 → closed with closeout comment after ledger+queue record). Wayfinder #94–#105 confirmed frozen with no agent-ready child. Updated `PROJECT-MANAGEMENT.md` and `project/current/ocr-v2-active-queue.md`; marked all six #130 checkpoint checkboxes; unblocked **only #127** (`blocked` → `ready-for-agent`). | §2.1–§4 |
| 2026-08-05 | Product-lane analysis + issue regularization | Pre-implementation architecture analysis of the #127/#126/#129/#99 lane: traced sync→memory→embed, OCR rebuild/redo→publication, version restore in code (file:line evidence). 11 findings (G1–G11) incl. two P0s (dry-run side effects; double-PaperForge fulltext path) and the #99 premise refresh (redo already transactional per #123). Published `docs/research/2026-08-05-product-lane-architecture-analysis.md`; appended addenda to #127/#126/#129/#99/#102 bodies; ledger §3/§6/§8 updated. Committed `160c1c02`. | §2.1–§4 |
| 2026-08-05 | Issue regularization — overlap absorption | #101 closed SUPERSEDED (absorbed into #126 PR B: token format pin, OCR START/DONE emitters, OCR_RUN cleanup, progress states); #102 closed SUPERSEDED (absorbed into #99: backup strategy covers redo + embed in-place path in one policy). #95 deferred with #126-acceptance coverage check; #63 protocol note; #94 child list updated. Queue file and ledger synced. | §2.1–§4 |
| 2026-08-05 | External review adopted; #127 contract hardened | Review confirmed the queue, corrected G1 (dry-run early-return verified at `sync.py:39-52` — regression test, not live P0), and hardened #127 in-body: cost/impact/confirmation split axes with invariants, execution ownership (core produces / CLI runner executes automatic-local / `--json` single final output / plugin sole executor), typed `action_id` allowlist, safety invariants, PR A–D split. Locked #126 colon wire format (key-only tokens), #129 fulltext-only restore, #99 A/B/C units; #82 HARD GATE + `blocked` label; #94 live table; #63 frozen banner; #95/#97/#103 code-check notes; #105 split note; #134 CI-allowlist note. Committed `0e8ae923`. | §2.1–§4 |
| 2026-08-05 | #127 implemented (next_actions policy) | Implemented PR A–D: `core/next_actions.py` typed schema + registry + validator (cost/impact/confirmation axes, remote/destructive invariants, build-time raise); sync cutover (both Popen spawns removed, `--json` single output, terminal runs automatic-local only, dry-run tested); plugin orchestrator + bridge + confirm modal wired into manual and auto sync; seam contract tests (26 python + 11 plugin + 433 plugin full). Two-axis review: 2 MAJOR → fixed (build validation raise; executed-marking only on actual start) + regressions. golden_127 re-observed (Popen facts → `_attach_next_actions`/`_run_terminal_followups`) and re-pinned to `7372383b`; commits `7372383b`, `417bd3e3`. Full python suite: 176 focused green; 2 pre-existing production-vault search timeouts confirmed environmental via stash (stale vector index, unrelated). | §2.1–§4 |
| 2026-08-05 | #126 OCR Workspace closure implemented (4 PRs) | PR A: structured rebuild results + exit codes + single-key tokens + chunked parallel stop + canonical result-hash contract (`result-hash.pending` publication marker in rebuild/postprocess/backfill; reader skips pending papers; Level-2 aligned). PR B: `OcrProcessController` singleton (credential fail-closed, PAPERFORGE_STOP, RESULT/DONE protocol, Settings migration). PR C: fulltext P0 (index→ocrDir fallback, no double-PaperForge), single-paper rebuild, memory-build + confirmed embed chain, lazy restore. PR D: index-first load + background enrichment, 100/page, per-page selection, O(n²) removal. Review: 3 findings (dropped explicit keys, workspace stop not reaching child, version-chip selection reset) → fixed + reload enrichment preserved → PASS. Full suite: 2867 passed / 292 skipped / 25 sandbox locks / 2 env vault-search timeouts. Commits `dea041db`–`72cf3598`. golden_126 re-pinned. | §2.1–§4 |
| 2026-08-06 | #129 + #99 product lane closed | #129 display restore: relabeled 恢复展示全文文本 + confirmation dialog, provenance persisted to meta.json (formal + legacy backup paths), `_restore_drift_override` marks DRIFTED rows when restored version predates structured state, stale notice with raw ocrFinishedAt; review 3+2 → PASS. #99 owner decision: redo internal-only (no user surface), `recover_redo_orphans()` crash recovery, embed backup verified; review 4 → PASS; golden_129 re-pin `553c1375`. Product lane complete; commits `2b4dca8d`–`8f436ecc`. | §2.1–§4 |
| 2026-08-06 | Audit report v1–v3 (external review loop) | Live report `docs/architecture-audit-2026-08-06/` (build_audit + render_html, self-contained HTML). v1 `e94895a1`: real revision/dirty + honest coverage. v2 `b009fe75`: Review overlay with per-rule-family adjudication, evidence extractors, OCR_RUN dead prefix removed from progress parser. v3 `3fb4a01b`: enumeration-complete semantics — universal/absence rules return UNRESOLVED under incomplete required coverage; Contract sole requiredness authority; step-level traces (4×partial); writer-callsite evidence with exact lines; repository_dirty surfaced. 112→153 focused tests incl. coverage-completeness semantics; 456 plugin + TSC + ruff clean; browser DOM verified. | §2.1–§4 |
| 2026-08-06 | Third review BLOCKER fixed (audit v4) | External ChatGPT review: report "基本成立" — 1 must-fix: `repository_dirty` lived only in Summary/HTML, not Audit/View (three-layer truth split risk). Fixed at `7567dd2c`: `RepositoryState` (revision/dirty/dirty_diff_digest) is now **semantic Survey content** (bound into survey digest, excluded from run_metadata); reconciler forces `assessment=failed` + `gate_eligible=false` with ALL reasons (dirty + coverage) merged; View/Summary/HTML project only. Cross-layer byte-identical verified; 3 new tests; full suite **2883 passed / 292 skipped / 0 failures**. Review verdict: report can be called "人工证据驱动、fail-closed、digest-bound". Deferred to #133: NextAction/RemoteExecution/ConfirmationFact modeling, `operation_write_scope` RuleKind, `test:` extractor evidence schema. | §2.1–§4 |
| 2026-08-06 | Owner directive: #133/#134 first; RC manual | Owner: "先做133和134，发布还得等我手动来做真实测试". Compact executed (ledger synced, full suite green); #133 promoted to sole `ready-for-agent`, #134 blocked-by-#133, RC acceptance deferred to owner manual real-vault testing. | §2.1–§4 |
| 2026-08-06 | #133 deterministic collectors implemented | Maintainer-only orchestrator + Python AST collector (Tier 1 sinks: fs writes/os.replace/SQL DML/subprocess; Tier 2 versioned wrapper registry — publish_ocr_result_hash → protocol write, _attach_next_actions → declaration; Tier 3 dynamic calls with scoped honest effects; read-only chains not flagged) + Node TS compiler collector (typescript 5.9 via plugin node_modules; missing → explicit unavailable coverage). Reconciler unresolved-evidence seam: relevant dynamic callsites keep rules UNRESOLVED (no false satisfied). Full-repo run 212 files/512 facts; 14 tests; architecture suite 183; full suite 2899. Commit `759a44a5`; acceptance evidence on #133. | §2.1–§4 |
| 2026-08-06 | #134 report + CI gate implemented | Parameterized self-contained HTML projection (10 sections; deterministic/review separated; escaping; copyable evidence; filters; focus/reduced-motion/responsive) + deterministic gate (Audit-only; allowlisted blocking violations only; skipped-with-reasons when ineligible). docs render_html.py → thin wrapper; CI e2e job runs orchestrator + gate. 14 tests + real-browser smoke (10 copy buttons, filters, no overflow); full suite 2899. Commit `a38c06c7`; acceptance evidence on #134. | §2.1–§4 |

## 9. Historical Detail Archive

> Fixed records and verbose session logs preserved below. The archive is read-only reference — active work is tracked in sections 2-4 above.

---

### 9.1 Gold Fixture Expansion + Bug Fixes (2026-06-16)

Full-day debugging session across 8 gold papers. 98 bug annotations, 8 pipeline fixes (F1-F10).

**Root cause categories identified:**

1. Frontmatter noise unrecognized (ISSN, journal citation) → body pollution
2. Cross-page text fragmentation
3. Tail zone: body prose incorrectly converted to backmatter
4. Backmatter heading gaps
5. Heading merge/split logic
6. Heading rescue from unknown_structural
7. Heading prefix by role (not font size)
8. Permissive figure matching
9. All same-page assets included in group match
10. Composite region text requirement removed

**Fixes applied:** `ocr_roles.py`, `ocr_document.py`, `ocr_blocks.py`, `ocr_render.py`, `ocr_scores.py`, `ocr_figures.py`, `ocr.py`

**Layout-first Phase 1 pass added** — table inventory relaxed for `media_asset` blocks, `_should_keep_formal_caption_seed()` added, `tests/test_ocr_layout_first_regressions.py` created.

---

### 9.2 Boundary Close-Out Pass (2026-06-17)

**Plan:** `docs/superpowers/plans/2026-06-17-ocr-v2-closeout-single-plan.md`

**Tasks 1-5 executed:**

- Same-page reference/body boundary split (block-level vertical split by heading position)
- False tail backmatter conversion reduction
- Page-1 correspondence line → frontmatter_support
- Preproof page-1 frontmatter: first-surviving-page logic, margin-band watermark detection, figure inner label extension
- Active truth-file cleanup: reconciled P0-P2 close-out

**Result:** 202P/1F/43S (sole failure = pre-existing DW figure ownership)

**Key commits:** `6f68bf2`, `b7d369e`, `c7a9c93`, `827a2cc`, `9329843`

---

### 9.3 Readiness-Gates (2026-06-18 ~ 06-19)

**Plan:** `docs/superpowers/plans/2026-06-18-ocr-v2-readiness-master-plan.md`

**Gates implemented:**

- **Gate 1 (Completeness):** `_summarize_page_text_coverage()` + `_classify_region_text_completeness()` + `audit_rendered_text_coverage()`
- **Gate 2 (Figure ownership):** 8 tasks — previous-page sequential fallback, DW Fig 3 xfail→pass, sidecar partition, fallback tightening. Final: 249/249 pass
- **Gate 3 (Ordering):** `_ref_number_sort_key` regex extended, reference boundary normalizers
- **Gate 4 (Layout coverage):** `audit/coverage_ledger.json` with readiness-class taxonomy, contract tests enforce named representatives

**Blind audit (5 unseen papers):** ALL PASS. Papers: 8VB9ZVQG, U746UJ7G, L6ALWJFP, PZ8B59K4, GU9R8EPE. No new failure families discovered.

**Remaining residuals:** ~40 stale audit truth blocks, ~50 edge-case misclassifications (low severity).

---

### 9.4 Cross-Page Caption Consumption Fix (2026-06-22)

**Paper:** SAN9AYVR Figure 24 double-emit. Cross-page figure ownership repair — reader/render chain consumed caption blocks on asset page instead legend page.

**Fixes applied:**

- Reader payload records cross-page caption consumption on legend page
- Render path suppresses original caption block on asset page
- `_recompute_final_unmatched_assets()` added — orphan truth now matches final ownership truth
- Cross-page duplicate `![[render/figures/figure_N.md]]` eliminated

**Test status:** 150 passed (figures + reader + render)

---

### 9.5 Figure Merge Refactor + Visual Grammar Hardening (2026-06-21 ~ 06-23)

**Core change:** Replaced greedy region-growth with **global distance clustering** (union-find):

- `_cluster_page_assets()`: horizontal <12% pw, vertical <8% ph, text-separator-aware
- Caption-as-boundary: each legend claims assets by y-band
- Composite parent detection: `_build_composite_parent_figure_groups_visual_only()`
- Dense page arbitration: `_build_dense_composite_parent_candidates()` when ≥4 visual fragments
- Ownership registry: `FigureOwnershipRegistry` with conflict detection
- Figure/table separation: `asset_family_hint` + table-like veto (confidence ≥0.70)
- Dedup refinement: `_normalized_caption_body` — internal punctuation preserved, terminal punctuation stripped
- `_ref_number_sort_key` with `[N]` bracket support

**Key fix (merge-gate closeout):** Same-number-distinct dedup + grid collapse fix (highest-score selection, not first-match)

**Test status:** 216→225→261 passed (figure stack)

---

### 9.6 Rebuild Production Run (2026-06-26)

**Full `ocr rebuild --all` (699 papers):**

- `--resume` checkpoint support (interrupted rebuilds resume)
- ASCII tqdm progress bar fix (Windows)
- Removed rogue `[DEBUG]` print in `ocr_render.py:1295`

**Fixes found:**

- N6XCZD25: Body paragraphs misclassified `structured_insert` → `body_spine_match` flag in `body_zone`
- Chinese Windows encoding: glob fallback in `resolve_pdf_path`; garbled `meta.json` auto-corrected on rebuild

---

### 9.7 Figure Number Inference + Container Admission (2026-06-26)

**Figure number inference** (leading `[1]` gap): 8-step algorithm in `_infer_missing_main_figure_numbers()`. N6XCZD25 `figure_unknown_005` → `figure_001`.

**Container admission rewrite** (evidence-driven):

- 7-method container extraction: page-sized/crop-like excluded, line-like→grouping only, vertical component merge
- Three-phase per-page loop replaces lazy-cache
- Blue sidebar box score 0.45→0.80 → rendered as `[!NOTE]` callout

**Key commits:** `45cf65e`, `bab0167`, `5ba1a6d`

---

### 9.8 UI Polish (2026-06-26)

**Plugin dashboard cleanup:**

- Vercel-style CSS (cards, collapsible headers, status grid, issue summary funnel)
- Title tooltip with `title_full` field
- Table sorted by time descending
- Click-to-copy on paper paths (pf-copy)
- Global "Start Working" cleanup — Doctor/Repair only in Issues section
- Run OCR button shows pending count
- Redo OCR → Maintenance button (opens settings→maintenance tab)
- DESIGN.md reference file added

---

### 9.9 Rebuild Audit + Index Repair (2026-06-27)

**6 bugs fixed:**

| Issue | Severity | Status |
|-------|----------|--------|
| `sync_service.py`: `_time` UnboundLocalError | HARD BLOCK | FIXED |
| Workspace fulltext never synced from OCR output | HIGH | FIXED |
| `build_index` early-return skips `_build_entry` | HIGH | FIXED |
| Field registry missing 9 common fields → 6000+ WARN | MEDIUM | FIXED |
| "700 papers missing fulltext" — false alarm | MISLEADING | NOTED |
| Base legacy fields — user choice | INFO | DEFERRED |

**Field registry additions:** `aliases`, `tags`, `journal`, `first_author`, `pmid`, `impact_factor`, `abstract`, `keywords`, `ocr_time`.

---

### 9.10 Deep Investigation — 5 Fix Spec (2026-06-27)

**5-paper vision audit:** 25K5KZAQ, NC66N4Q3, 9TW98JH8, YGH7VEX6, XD2BPCMG.

**Fixes identified and resolved:**

| Fix | Issue | Root Cause | Resolution |
|-----|-------|-----------|------------|
| Fix 1 | Figure-internal text containment | No spatial containment in `build_figure_inventory` | Render-hygiene pass: 6 helpers + 19 tests ✅ |
| Fix 2 | Reference sorting `[N]` bracket gap | regex only matches `N.`/`N)`, not `[N]` | Two capture groups `r"^\s*(?:[\d+](\.\))|\[(\d+)\])"` ✅ |
| Fix 3 | Backmatter boundary (CRediT/Ethics) | 7.97pt < 11pt threshold; no container keywords | Ref-anchored partition design 🔄 |
| Fix 4 | Figure caption → `non_body_insert` | `figure_caption` in `_INSERT_CANDIDATE_ROLES` | Removed list ✅ |
| Fix 5 | Demoted body paragraph in figure legends | `body_paragraph` re-enters matching via legend detection | Filter before `_is_validation_first_legend_candidate` ✅ |

**Spec:** `docs/superpowers/specs/2026-06-27-figure-containment-and-backmatter-boundary-design.md`
**Plan:** `docs/superpowers/plans/2026-06-27-figure-containment-implementation-plan.md`

### 9.18 10-Paper Truth Audit + GPT Cross-Validation (2026-07-01)

**Scope:** 10 papers sampled from vault (3 green, 4 yellow, 3 red), batch-audited via `ocr_truth_audit.py` + annotated page vision agents.  
**1 complete vision audit:** U746UJ7G — 0 matched figures, root cause = vector-rendered Figure 1+2 (52 drawing paths, 0 embedded images).  
**Key bugs found:**
- `_TABLE_PREFIX_PATTERN` 3 处只认 `\d+`，不认罗马数字 I/II/III（KUR9PBJC pages 4/5/7）
- `raw_label=figure_title` 的 Table N caption 无 guard → 进 `figure_caption`
- `vision_footnote` 里 "This figure..." 被吞成 footnote（U746UJ7G p8:4）
- `unmatched_assets` 重复计数（matched 后又在 unmatched 列表）
- HTML table block 断连（2YW2MJBL）
- Vector figure pipeline 盲区（U746UJ7G）

**False positives:** `reference_span_error` ~90% noise, `same_page_boundary_error` 100% unreliable.

**GPT 二审修正 8 处:** Roman+S prefix 三处同步、score hard gate、tie-breaking、dedup、`_is_near_figure_media` helper。  
**Outputs:**
- Spec: `docs/superpowers/specs/2026-07-01-ocr-audit-findings-for-gpt.md`
- Plan: `docs/superpowers/plans/2026-07-01-ocr-audit-gpt-fix-plan.md`
- Per-paper vision reports: `local://*-vision-report.md`
**Execution:** 3/4 commits implemented (`2d40ad9`, `21bdfd0`, `7670227`). Commit 3 (unmatched dedup) pre-existing from PR3 (`4ab227e`). Follow-up refactor moved rotated-caption handling earlier: PyMuPDF `dir/wmode` now preserved in `span_metadata`; rotated `vision_footnote` candidates enter normal legend matching; `same_page_rotated` matches carry `rotation_correction_deg` into crop/render. U746UJ7G now produces a normal matched figure (`figure_unknown_000`, `settlement_type=same_page_rotated`) instead of synthetic fallback. 422 regression tests pass.
- Block reviews: `audit/<KEY>/block_review.jsonl`（U746UJ7G, KUR9PBJC, CGGYTEEQ, 7FNV9AW2 etc.）


### 9.19 Asset-Internal Figure Number Recovery (2026-07-01)

**Problem:** U746UJ7G rotated figure — "Figure 2. Plot of Criteria Time..." was absorbed into chart asset bbox during OCR assembly. The rotated prematch refactor (9.18) produced a matched figure (`figure_unknown_000`) but without `figure_number`. No way to assign Figure 2 to the figure.

**Solution:** Metadata-only recovery pass after synthetic vector fallback, before dedup.
- `extract_pdf_lines_normalized` in `ocr_pdf_spans.py` extracts PDF rawdict text lines page-by-page, normalizing coordinates to OCR space
- `_recover_missing_figure_numbers_from_assets` iterates matched_figures without numbers, scans each matched asset's bbox for internal PDF line labels ("Figure N.", "Fig. N:")
- `_needs_asset_internal_figure_number_recovery`: gates by figure_id prefix (`figure_unknown_*` or `synthetic_figure_*`) + text description signal
- `_looks_like_internal_figure_label`: rejects full-sentence patterns ("Figure X shows...") via regex match
- `_asset_edge_band_score`: geometric rejection for lines in asset center (not label position) or covering >15% of asset area
- Coordinate normalization is caller responsibility (done in ocr_rebuild.py)

**Files changed:**
- `paperforge/worker/ocr_figures.py`: 7 new functions + 2 pattern constants + signature change to `build_figure_inventory` + recovery pass call
- `paperforge/worker/ocr_pdf_spans.py`: `extract_pdf_lines_normalized` helper
- `paperforge/worker/ocr_rebuild.py`: call helper, pass `page_pdf_lines_by_page` to inventory builder
- `tests/test_ocr_figures.py`: 6 new tests (basic recovery, duplicate rejection, normal-fig unaffected, multi-label conflict, center rejection, overlap gate)

**Spec:** `docs/superpowers/plans/2026-07-01-ocr-asset-internal-figure-number-recovery-plan.md`
**Execution:**
- U746UJ7G verified: `figure_number == 2`, `figure_id == "figure_002"`, `recovered_label_text` contains "Plot of Criteria Time", flags contain `figure_number_recovered_from_asset_text`
- **428 regression tests pass** (422 existing + 6 new)


### 9.20 Round 2 Truth Audit + 37LK5T97 Bug Fixes (2026-07-02)

**Scope:** 10 new papers batch-audited via `ocr_truth_audit.py` (high-risk mode). 5 GREEN / 4 YELLOW / 1 RED.  
**RED paper:** 37LK5T97 — "Both IM and EC ossification occurs during the bone-healing process"  

**Three bugs found and fixed:**

1. **Figure 1 sidecar demotion:** Caption (left column, 246px) and image (right column, 693px) had zero x_overlap. `_is_near_figure_media()` missed it, `_looks_like_figure_narrative_prose()` caught the long description, and candidate_resolution demoted to `body_paragraph`. **Fix:** Added `_is_sidecar_candidate()` guard — checks vertical overlap with media_asset when horizontal overlap is absent. Caption preserved as `figure_caption_candidate`.
   - File: `paperforge/worker/ocr_document.py`
   - Result: Figure 1 matched as `figure_001` (caption block_id=2, asset block_id=9)

2. **Rotated table caption matching:** Tables 1-3 had rotated captions (span dir=[0,-1], vertical text beside table body). `score_table_match` required x_overlap + asset_below_caption, both failed for rotated sidecar layout. **Fix:** Added `adjacent_x` + `y_overlap_with_asset` scoring branch when caption has rotated text and x_overlap < 0.5.
   - File: `paperforge/worker/ocr_scores.py`
   - Result: All 6 tables matched (has_asset=true, score >= 0.65)

3. **Rotated table render orientation:** Table body also had dir=[0,-1] (rotated 90° content on portrait page). Rendered JPEG showed vertical text. **Fix:** Added `_table_has_rotated_content()` helper; computes union `render_bbox` (caption+asset) and `render_rotation_deg=270` in table entry; render loop passes `rotation_deg` to `_crop_asset_from_pdf`.
   - Files: `paperforge/worker/ocr_tables.py`, `paperforge/worker/ocr_objects.py`
   - Result: Tables 1-5 rendered at correct orientation (1908×2858 → 2858×1908)

**Additional quality fix:** Rotated figure crop quality improved in prior session — `Matrix(2,2)` → `Matrix(4,4)`, PIL rotation from pix.tobytes("png") (single pass, no double JPEG), and OCR→PDF coordinate conversion fix. U746UJ7G figure_002: 2618×1914 px, 5.0M px (4.5x improvement).

**Commits:** `59cd01a` (figure quality+rotation coord fix), `bd3f3b6` (sidecar+table match), `86e0d14` (table render rotation)  
**Tests:** 428 regression tests pass (no new tests added, existing cover the affected paths)  
**Analysis:** `docs/superpowers/analysis/2026-07-02-37lk5t97-figure1-sidecar-bug-analysis.md`  
**Audit findings:** `docs/superpowers/specs/2026-07-02-ocr-truth-audit-round2-findings.md`

### 9.21 Figure Caption Prefix Recovery + Inline Table Fix (2026-07-02)

**Problem 1:** PaddleOCR fails to detect standalone "Figure N" / "FIGURE N" headings in bold/small-caps fonts. Caption body is captured as `figure_caption_candidate` but lacks the figure number prefix → `_is_formal_legend()` fails → caption never enters matching pool.

**Fix:** `_recover_figure_heading_prefix()` in `ocr_figures.py` checks the PDF text layer (via existing `page_pdf_lines_by_page` infrastructure — no extra PDF open) for "Figure N" lines. If the next PDF line (by y-order) shares ≥15 common-prefix chars with the OCR caption text, the heading is prepended. Runs BEFORE the zone/style filter so recovered captions pass through to legend matching.

**Result:** 5S7UI34M (PVA综述): 4→9 matched figures, 33→1 unmatched (p1 logo). HQAQBSBP: Figure 5 recovered. 372 figure tests pass.

**Problem 2:** Inline `<table>` HTML blocks with `raw_label=table` hit the `raw_label="table" → media_asset` fallback (ocr_roles.py:1355) before reaching the `<table>` → `table_html` check (line 1456, gated by `raw_label="text"`). Plus `ocr_document.py:6120-6121` converted `table_html` to `table_html_candidate` — a role with no downstream handler → structural gate downgraded to `unknown_structural`.

**Fix:** (1) Moved inline `<table>` check before `raw_label=table` fallback in `assign_block_role()`. (2) Added `table_html` verifier in structural gate (self-identifying, accepts if text starts with `<table>`). (3) Removed dead `table_html → table_html_candidate` conversion.

**Result:** AH6Q7DLC (worst case, 30 blocks): 29/30 → `table_html` (1 = reference_item). 585 figure/table/role tests pass.

**Files changed:**
- `paperforge/worker/ocr_figures.py` — `_recover_figure_heading_prefix()` + body_zone filter guard
- `paperforge/worker/ocr_roles.py` — inline `<table>` before raw_label=table
- `paperforge/worker/ocr_document.py` — removed `table_html_candidate` dead path
- `paperforge/worker/ocr_structural_gate.py` — `table_html` verifier

### 9.22 Plan A: OCR Pairing Framework Extraction (2026-07-03)

**Goal:** Extract generic OCR pairing mechanics from figure vnext and migrate figure onto the framework with no behavior change. Table vnext deferred to Plan B.

**Architecture (Option B):**
- Generic framework: `ocr_pairing_types.py`, `ocr_pairing_state.py`, `ocr_pairing_framework.py`
- Figure domain: `ocr_figure_domain.py` (FigureCorpus, FigureCandidateIndex), 8 pass files (import paths only)
- Compatibility shims: `ocr_figure_vnext_types.py`, `ocr_figure_vnext_state.py`, `ocr_figure_vnext_corpus.py` each re-export from framework/domain
- `ocr_figures.py`: orchestration loop replaced with `run_pairing_passes(state, pass_classes)` from framework

**Key decisions:**
- Keep `figure_no` and `FigurePipelineState` names in Plan A (rename deferred until migration stable)
- Plan A extracts pass orchestration only, not full framework-owned arbitration
- Table vnext deferred — no table file changes

**Commits (branch `feat/ocr-pairing-framework`, 6 commits over master):**
| # | Commit | Description |
|---|--------|-------------|
| 1 | `0f94123` | docs: add Plan A implementation document |
| 2 | `96a5ddd` | fix(tests): update stale span_backfill_version constants |
| 3 | `1cc44b5` | test(ocr): lock figure vnext extraction baseline |
| 4 | `6229f6c` | refactor(ocr): extract generic pairing types and state |
| 5 | `7cfbb5f` | refactor(ocr): add pairing pass runner and figure domain module |
| 6 | `32541cf` | test(ocr): prove rebuild compatibility with pairing framework |

**Files changed:** 21 files, +1546 -364

**Tests:** 288 pass in figure + rebuild + pairing suites (0 failed). Pre-existing `paperforge.resources` ModuleNotFoundError in test_ocr_document.py unrelated.

**Verification gates:**
- Pre-existing rebuild test fixed (stale version constant)
- `build_figure_inventory` → `build_figure_inventory_vnext` delegation test passes
- Shim identity tests prove re-exports are the same class (not copies)
- Rebuild compatibility test calls `run_derived_rebuild_for_keys()` for real and asserts `build_figure_inventory` is invoked
- No table file changes in diff

**Spec:** `docs/superpowers/specs/2026-07-03-ocr-pairing-framework-design.md`
**Plan:** `docs/superpowers/plans/2026-07-03-ocr-pairing-framework-plan-a.md`
**Branch:** `feat/ocr-pairing-framework` (in worktree `.worktrees/feat-ocr-pairing-framework/`)
