> **Branch:** `master` | **Last Updated:** 2026-07-19
> **Active work:** Redesign PRD #83 and agent-ready issues #84–#93 are published; #84 capability presentation contract is the next Ask Matt implementation.
>
> ---
>
> **Current state:** Release N+1 implementation is verified on `master` through `b41b4c88`; #81 remains open only for an explicit release decision, #82 remains blocked on the N+1 support window, and no release was performed.
>
> Live diagnosis confirmed duplicated runtime actions, stale-as-“待接入” presentation, and an asymmetric Module Detail implementation: Installation renders a one-item legacy selector while Library/OCR/Memory use the shared selector. A user grilling session approved a five-module model (Foundation, Library, OCR, Smart Retrieval, Agent Integration), three top-level destinations (Overview, Maintenance, Help), a four-stage dynamic setup journey, user-problem-only Maintenance, and Obsidian-native progressive disclosure.
>
> Next: implement #84 through Ask Matt. Package/tag publication is deferred by owner direction and must not be performed without renewed approval.
## 1. Architecture

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
| Full OCR regression suite | **1278 passed, 8 pre-existing failures, 275 skipped** ✅ |
| Focused merge suite (v3 + tail settlement + writeback + appendix numbering + rendering) | **105 passed, 0 failed** ✅ |
| Layer 2 quality + feedback tests | **22 passed, 0 failed** ✅ (17 quality + 5 feedback) |
| Full vault corpus diff: legacy vs v3 (555 papers) | **547/555 no diff, 5/555 v3 improvement** ✅ |
| 86-paper pre-merge corpus diff | **86/86 no diff** ✅ |
| 6 fixture-backed v3 parity gates | **6/6 pass** ✅ |
| Focused OCR rebuild/redo/maintenance paths | **99 passed, 1 Windows signal test skipped, 1 unrelated empty-result regression deselected** ✅ |
| Plugin tests + TypeScript + production build | **390/390 passed; typecheck/build clean; production bundle 259.3KB** ✅ |
| Live Literature-hub maintenance UI | **734 All / 700 Recommended; no captured errors** ✅ |
| Maintenance regression action model | **19/19 passed** ✅ (per-row canonical action routing, redo confirmation gate, cache manifest preservation) |
| Canonical setup/config migration (#75) | **61 passed, 0 failed** ✅ (fresh/v1/v2 config, CLI routing, path forwarding, failure exit, idempotent rerun) |
| Installation/Help capability tracer (#76) | **21 backend tests + 169 plugin tests passed; typecheck/build clean; independent review PASS** ✅ |
| Managed Runtime lifecycle + navigation (#77) | **192 focused + 289 full passed; typecheck/build clean** ✅ |
| OMP Matt workflow guard | **Fresh OMP auto-discovery confirmed; 7/7 deterministic guard cases passed** ✅ |
| Library/OCR/Memory capability tracers (#78) | **65 backend tests + 178 focused plugin tests, 324 full plugin tests passed across 11 files; typecheck/build clean; backup restore end-to-end** ✅ |
| SecretStorage capability secrets (#79) | **Backend-focused gate, plugin full suite passes; typecheck/build clean** ✅ |
| Maintenance probe — actionable rows, draft, destructive confirmation (#80) | **Backend focused gate 77/77; plugin full suite 381/382** (only pre-existing capability-state test expecting help.stale but receiving help.invalid_response) ✅ **; typecheck/build clean; production bundle 264.4KB; real Obsidian 1.12.7 smoke at 730 and 768 confirmed Maintenance entry focus, actionable-only rows, keyboard Enter, accessible destructive confirmation with exact backend effect, focus trap/restoration, owned inert cleanup, redacted editable issue draft, no token input/auto-open, explicit GitHub open only, URL re-redaction, no horizontal overflow**

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


| 36 | — | Maintenance probe: backend-derived rows, privacy-safe local draft, accessible destructive confirmation (#80) | Feature | Implementation in Issue #80 worktree. Backend-focused gate 77/77; plugin full suite 381/382 (pre-existing capability-state test expecting help.stale but receiving help.invalid_response); typecheck/build clean; production bundle 264.4KB; Obsidian 1.12.7 smoke 730/768 with actionable-only rows, keyboard Enter, accessible destructive confirmation with exact backend effect, focus trap/restoration, owned inert cleanup, redacted editable issue draft, no token input/auto-open, explicit GitHub open only, URL re-redaction, no horizontal overflow. | — |
| 37 | — | Literature-hub loaded duplicate `.obsidian/plugins/paperforge.bak`, while the correct bundle used an unwarmed Managed Runtime and the published 1.5.15 backend lacked `probe` | Deployment/runtime fix | Moved the duplicate outside the plugin scan path, migrated both credentials with readback verification, installed the current backend into the canonical managed venv, restored idempotent migration on startup, shared and warmed the runtime before dispatch, synchronized manifest `minAppVersion` 1.11.4, rebuilt and redeployed. Live cold-start verification: #78 overview/detail, #79 configured secret state, #80 three-row Maintenance inbox; no captured Obsidian errors. | — |
## 3. Remaining Issues — Release-Readiness Layers

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
The OCR maintenance slice has a canonical All/Recommended state model, selected batch actions, streaming progress, cooperative stop, and canonical per-row action routing with confirmation gates for destructive operations. Issues #76–#80 now provide production capability envelopes, the four-destination navigation shell, the machine-local Managed Runtime lifecycle, real Library/OCR/Memory detail probes, and the Maintenance probe with actionable-only backend-derived rows, privacy-safe local issue drafts, and accessible destructive confirmation. All six modules are real probes. Stale or malformed persisted evidence fails closed.

### Layer 4: Downstream Tools
`chunker.py` uses hardcoded section regex + fixed 3-paragraph groups. OCR has rich structured output (sections, headings, figures, tables with captions) — chunker should consume this structure directly. Figures/tables should support separate embedding (text + future vision).

Remaining legacy OCR issues (carried forward):
## 4. Active Queue

1. 🟡 **[Control-center redesign PRD #83](https://github.com/LLLin000/PaperForge/issues/83)** — approved source of truth; ten dependency-ordered agent-ready issues (#84–#93) are published. Start with #84 only.
2. 🟡 **Release cutover #81/#82** — N+1 code is verified on `master`, but #81 stays open for the owner-controlled release gate; N+2 deletion #82 stays open until an N+1 package and support window exist. No release is authorized.
3. ✅ **[Capability-state vocabulary](https://github.com/LLLin000/PaperForge/issues/69)** — resolved at `issuecomment-4971161072`. Orthogonal availability/activity/attention axes, 6-state capability ordinal, 12 canonical verbs, backend-owned severity and primary actions, maintenance projection.
4. ✅ **[Managed runtime](https://github.com/LLLin000/PaperForge/issues/70)** — resolved at `issuecomment-4971239398`. Plugin-managed immutable runtime slots, system-Python bootstrap with validated-triplet fallback, single `active-runtime.json` pointer, `ManagedRuntime` class with `current()`/`status()`/`ensure()`, fail-closed command resolution.
5. ✅ **[Control-center prototype](https://github.com/LLLin000/PaperForge/issues/71)** — resolved with independent Critical/Important PASS review and browser verification at 768px. Six-module control-center HTML prototype covers 5 scenarios with plain-button switcher, primary attention zone, responsive layout, and capability-gated actions. Design decisions recorded in `docs/prototypes/2026-07-14-six-module-control-center.html/.md`. No production implementation before #73.
6. ✅ **[Maintenance prototype](https://github.com/LLLin000/PaperForge/issues/72)** — resolved with independent Critical/Important PASS review and browser verification at 768px. Actionable-only inbox with single-action rows, inline issue-draft review, local redacted export, and confirmation-first report flow. Design decisions recorded in `docs/prototypes/2026-07-14-maintenance-issue-reporting.html/.md`.
7. ✅ **[Migration and acceptance contract #73](https://github.com/LLLin000/PaperForge/issues/73)** — closed after five-domain code audit, user grilling, and independent acceptance reviews. The implementation frontier moved to PRD #74 and child issues #75–#82.
8. 🟡 **Downstream tooling** — section-aware chunking and separate figure/table handling.
9. ⏳ **Compatibility naming cleanup** — deferred post-release.
### 4.1 Immediate Next Steps

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
- [x] Publish redesign PRD [#83](https://github.com/LLLin000/PaperForge/issues/83) and ten dependency-ordered issues [#84–#93](https://github.com/LLLin000/PaperForge/issues/84); begin with #84 through Ask Matt.

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

---

## 6. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-08 | Adopt anchor-first OCR architecture | Early role guessing caused cascading errors; needed structural discovery first |
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
| 2026-06-16 | Gold fixture expansion + 10 pipeline fixes | 98 bug annotations, 8 papers audited, 8 fixes applied (F1-F10) | §9.1 |
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
