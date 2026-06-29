# OCR-v2 Project Management Log

> **Branch:** `ocr-v2` | **Base:** `master` | **Last Updated:** 2026-06-28
> **Active work:** P0+P1 author bio detection — post-ref text-only bios + figure-residual portrait assets correctly classified as backmatter_body/author_bio_asset. 1018 OCR tests pass, 0 failures.

---

## 0. Executive Summary

**Current state:** P0+P1 bio detection complete. **1018 OCR tests pass, 0 failures.** Pass B (`residual_author_bio_pass`) catches portrait unmatched_assets/unresolved_clusters. Pass C (`post_ref_bio_cleanup`) handles reference_item + figure_caption. Three-pass architecture: P0 (text-only post-ref) ✅, P1 (figure residual) ✅, P2+ (P1 profile card pre-pass) deferred. Next: Run lint and merge ocr-v2 to master.

---

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

### 2.1 Test Suite

| Suite | Result |
|-------|--------|
| Figure stack (figures + reader + containment + backmatter boundary) | **286 passed** ✅ |
| Document + roles + render + gate + rebuild + state machine + trace | **330 passed, 0 failed** ✅ |
| Author bio detection (ocr_bio) | **37 passed** ✅ |
| Spec contracts | All passed ✅ |
| Real-paper regressions | All passed ✅ |
| **Total OCR tests** | **1018 passed, 275 skipped (fixture unavailable), 0 failed** ✅ |
### 2.2 Component Status

| Component | Status |
|-----------|--------|
| Structural gate | Installed |
| Role assignment (seed only) | ✅ |
| Zone inference + fallback | ✅ |
| Figure inventory | Global distance clustering — correct |
| Backmatter boundary | ✅ Ref-anchored partition committed |
| Pre-ref tail zone | ✅ Fixed |
| Abstract detection | ✅ Fixed |
| Frontmatter heading normalization | ✅ Fixed — no text matching |
| non_body_insert clustering | ✅ Fixed — page-1 guard threshold |
| Render (backmatter headings) | ✅ Correct heading rendering |
| State machine | ✅ Accepts done_degraded as terminal |
| Rebuild (span backfill skip) | ✅ Version match check fixed |
| Author bio detection (Passes B+C) | ✅ P0: post-ref text-only bios as backmatter_body. P1: figure-residual portrait assets as author_bio_asset + figure_caption support |

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

### P2 (Deferred)

1. **Figure containment gaps** — `cluster_bbox` containment only runs on matched figures; composite figures with demoted caption upstream never enter containment. Inner-text detection misses `vision_footnote`/`paragraph_title` raw_labels.
2. **Short "Table N" caption matching** — bare `"Table 1."` labels miss table_asset in ownership pipeline. Existing code partially handles it; residual cases remain.
3. **Page-1 body paragraph width check** — right-column body paragraphs on two-column pages naturally narrower; need column-aware spine width check.
4. **Body text backfill overlap** — `backfill_missing_text_from_pdf` uses `get_text("words", clip=expanded)` returning words beyond block's bbox; can cause text duplication at render level.
5. **2HEUD5P9 reference ordering — multi-column page interleave** — References on multi-column pages appear in page-order (top→bottom, left→right), not sorted by number. Need column-aware ref reorder or post-hoc numeric sort within reference_zone.
6. **Mixed-column tail page zone absorption** — 4AG67PBH P21: Acknowledgments (pre-ref body text in left column) absorbed into reference_zone when right column has refs. seed_role=body_paragraph gets accepted as reference_item via reference_zone_fallback. Need column-aware zone inference for mixed tail pages.

### P3 (Boundary / Edge Cases)

1. **DW biography page mismatch** — pages 32-34 vs expectations 33-34.
2. **AJR side-caption recovery** — deliberately deferred; not part of generic inventory refactor.
3. **Chinese Windows encoding** — non-ASCII PDF filenames garbled via GBK codepage. Glob fallback added; residual `meta.json` corruption from earlier runs.
4. **`backfill_missing_text_from_pdf` bbox-exact filtering** — need decision on render-level dedup vs backfill-level bbox clamp.
5. **Multi-caption page column collapse** — `page_assets` group on multi-column pages merges separate figures in different columns.
6. **Figure/table shared-consumption registry** — no shared consumed registry for ambiguous image-like blocks.
7. **Short papers (<3 pages) health falsely red** — no headings/abstract in Letter/Editor formats.

## 4. Active Queue

1. ✅ P1 backmatter boundary (ref-anchored partition)
2. ✅ Pre-ref tail zone fix (4KCHGV2Z)
3. ✅ Gate 5 frontmatter fix series (24YKLTHQ)
4. ✅ Stale trace-vs-expectation fixtures cleared (10 assertion updates)
5. ✅ All stale test expectations reconciled (non_body_insert, caffard, legend_like, structural gate, render, state machine, rebuild, truth docs)
6. ✅ P0 author bio detection (post_ref_bio_cleanup for reference_item)
7. ✅ P1 author bio detection (residual_author_bio_pass + figure_caption support + tag_figure_contained_text protection)
8. **NEXT: Run lint (ruff) then merge ocr-v2 → master**

### 4.1 Immediate Next Steps

- [x] 25 fixed tests (10 distinct issues)
- [x] Full OCR regression sweep: 1018 passed, 0 failed
- [x] P0 bio detection: 30 new tests, 0 regressions
- [x] P1 bio detection: 7 new tests, 0 regressions
- [x] tag_figure_contained_text author_bio protection
- [ ] Run lint (ruff)
- [ ] Merge `ocr-v2` into `master`

---

## 5. Key File Map

### 5.1 Production Code (OCR Pipeline)

| File | Role |
|------|------|
| `paperforge/worker/ocr_blocks.py` | Raw + structured block generation; preserves seed_role only |
| `paperforge/worker/ocr_roles.py` | `assign_block_role()` — seed/proposal logic only (NOT final) |
| `paperforge/worker/ocr_document.py` | `normalize_document_structure()` — anchor/family/zone + gate + final roles |
| `paperforge/worker/ocr_structural_gate.py` | `VERIFY_REQUIRED` role decision + abstract span + reference zone + health |
| `paperforge/worker/ocr_orchestrator.py` | Body reorder, column validation, layered assembly |
| `paperforge/worker/ocr_render.py` | `render_fulltext_markdown()` — consumes verified artifacts ONLY |
| `paperforge/worker/ocr_health.py` | Health reporting, merged gate summary |
| `paperforge/worker/ocr_profiles.py` | Span extraction, profile aggregation, cross-validation |
| `paperforge/worker/ocr_figures.py` | Figure reader pipeline |
| `paperforge/worker/ocr_tables.py` | Table inventory matching |
| `paperforge/worker/ocr_scores.py` | Score functions (spatial, structured_insert, etc.) |
| `paperforge/worker/ocr_rebuild.py` | Derived rebuild entry point |
| `paperforge/worker/ocr_pdf_spans.py` | PDF span backfill for OCR-missed blocks |
| `paperforge/worker/ocr_bio.py` | Author biography detection utilities and passes |

### 5.2 Test Files

| File | Purpose |
|------|---------|
| `tests/test_ocr_figures.py` | Figure inventory, matching, ownership | 261 tests |
| `tests/test_ocr_document.py` | Document structure, normalize, gate | 131 tests |
| `tests/test_ocr_render.py` | Fulltext render contract |
| `tests/test_ocr_figure_reader.py` | Reader contract |
| `tests/test_ocr_trace_vs_expectations.py` | Real-paper trace vs expectations gap report (8 gold papers) |
| `tests/test_ocr_real_paper_regressions.py` | Page-level + document-level regression on real papers |
| `tests/test_ocr_real_paper_audit_contracts.py` | Gold-fixture quality gate |
| `tests/test_ocr_spec_contracts.py` | Architecture contract tests |
| `tests/test_ocr_structural_gate.py` | Gate unit tests |
| `tests/test_ocr_v2_structural_regressions.py` | Structural regression guards |
| `tests/test_ocr_layout_first_regressions.py` | Layout-first behavior guards |

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
| 2026-06-28 | Category-weighted bio scoring | career=+3, education=+2, research=+2, institution=+1, publication=+1. Returns (score, categories) tuple. Threshold: score ≥ 4 AND categories ≥ 2. |
| 2026-06-28 | author_bio_asset role: non-rendered, non-indexed | Bio artifacts removed from figure_inventory entirely, never returned to unmatched_assets. Clean prune before reader. |

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
| 2026-06-28 | Data-driven truth audit (2 papers) | 2HEUD5P9 (27p) + 4AG67PBH (25p) — no vision (model limit). Found 3 pipeline defect patterns: zone_leak_frontmatter_to_body (2 papers), reference_boundary_body_mix (2 papers), title_repeat_page2 (1 paper). 12 ghost unknown_structural blocks in 2HEUD5P9. Findings saved to audit/2026-06-28-data-audit-findings.json. | §9.15 |
| 2026-06-28 | P0 author bio detection implementation | Created ocr_bio.py with category-weighted bio scoring, Pass C (post_ref_bio_cleanup), figure match guards. Wired author_bio_asset role contract + pipeline. 30 new tests pass. 1041 total OCR tests, 0 regressions. Commits: `e2f0c8a`, `7810eb1`. | §9.16 |
| 2026-06-28 | P1 author bio detection implementation | Added residual_author_bio_pass (figure-residual portrait assets), extended post_ref_bio_cleanup for figure_caption, tag_figure_contained_text protection. 7 new P1 tests. 1018 total OCR tests, 0 regressions. Commit: `7a1cc5e`. | §9.17 |

---

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

---

*Vault-Tec Research Log — End of Entry — Preparing for the Future!*
