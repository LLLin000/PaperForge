# OCR-v2 Project Management Log

> **Branch:** `ocr-v2` | **Base:** `master` | **Last Updated:** 2026-06-13
> **Rule:** Every step is documented with: What was done, Why it was done, What comes next.

---

## 0. Branch Status Summary

### 0.1 Comparison with master

| Metric | master | ocr-v2 |
|--------|--------|--------|
| Commits ahead of other | 1 (`docs: add OCR real-paper regression design`) | 186 (entire OCR-v2 pipeline) |
| Files changed | -- | 244 files, +44,778 / -896 |
| Merge status | -- | Can be merged (only 1 divergent commit) |

### 0.2 What ocr-v2 is

A structural redesign of PaperForge's OCR pipeline. The original pipeline committed to semantic roles too early (raw OCR labels -> guess -> rescue -> render). **ocr-v2 replaces this with anchor-first parsing:** structural signatures -> stable anchors -> zone inference -> late role resolution -> figure/table validation -> render.

---

## 1. Architecture Overview

### 1.1 The problem (pre-v2)

```
raw_label/text -> final role -> normalize -> rescue -> demote/promote -> attach -> render
```

Early role guesses caused: title/author/footnote misclassification, body paragraphs typed as references, reference continuations leaking into body, left/right column interleave bugs, duplicate figure captions.

### 1.2 The solution (v2 target)

```
raw observations -> structural signatures -> stable anchors/families -> zone inference -> role resolution -> figure/table validation -> render + health
```

Key design documents:
- **Architecture spec:** `docs/superpowers/specs/2026-06-08-ocr-anchor-first-structured-parsing-design.md` (946 lines)
- **Implementation plan:** `docs/superpowers/plans/2026-06-08-ocr-anchor-first-structured-parsing-plan.md`
- **Role gate plan:** `docs/superpowers/plans/2026-06-11-ocr-verified-structural-role-gate.md` (1257 lines)
- **Latest spec realignment plan:** `docs/superpowers/specs/2026-06-13-ocr-real-paper-regression-and-spec-realignment-design.md` (374 lines)

### 1.3 Core principles

1. **seed_role is a proposal, never a final role** -- `assign_block_role()` proposes; `normalize_document_structure()` decides
2. **VERIFY_REQUIRED** roles (paper_title, authors, section_heading, reference_item, figure_caption, etc.) must have `role_verification_status == "ACCEPT"` with non-empty `role_source` and `role_evidence`
3. **Zone != Role** -- being in the body reading environment does not imply `body_paragraph`
4. **Reference tail first** -- reference sections protected from tail contamination
5. **Frontmatter source-backed** -- OCR localizes but must not invent/discard canonical frontmatter

---

## 2. Development Phases (Timeline)

### Phase 1: Artifact Foundation (earliest commits)
- `docs: add OCR structured pipeline design spec` (433e4e5)
- `feat: add OCR artifact path and version helpers`
- `feat: persist OCR raw metadata and version payloads`
- `feat: emit canonical OCR raw blocks`
- `feat: emit OCR structured block artifacts`
- **What:** Established artifact storage, version tracking, raw + structured block output.
- **Why:** Before any redesign, we needed stable on-disk contracts.

### Phase 2: Structured Inventory (figure/table)
- `feat: add OCR figure inventory`
- `feat: add OCR table inventory`
- `feat: emit OCR figure and table objects`
- `feat: add OCR resolved metadata artifact`
- **What:** Figure and table detection, inventory management, metadata resolution.
- **Why:** Figure/table handling is user-facing; must be stable before refactoring roles.

### Phase 3: Health & Rendering
- `feat: render OCR fulltext from structured artifacts`
- `feat: add OCR structured health report`
- `feat: surface OCR structured health in doctor and status`
- **What:** Structured renderer, health reports, status integration.
- **Why:** User-visible outputs must be preserved during refactoring.

### Phase 4: Runtime Integration & Compatibility
- `feat: add OCR runtime preflight warnings for auto-rebuild`
- `feat: classify OCR raw and derived version state`
- `feat: integrate OCR version state into sync runtime`
- `refactor: preserve OCR compatibility through renderer v2`
- **What:** Sync integration, version state, backward compatibility.
- **Why:** Must coexist with existing pipeline during transition.

### Phase 5: Evidence & Search
- `feat: add OCR role-based search index`
- `feat: add OCR evidence objects and paper-context summary`
- `feat: add OCR evidence-aware query routing`
- **What:** Role-indexed search, evidence for query routing.
- **Why:** Downstream agent/AI consumers need structured role access.

### Phase 6: Anchor-First Redesign (the big one)
This is the core transformation. Sub-phases:

#### 6a. Structural Signatures & Span Metadata
- `feat: add OCR structural signatures`
- `feat: carry span_metadata through raw and structured block pipeline`
- `feat: create ocr_profiles.py` (span extraction, profile aggregation, cross-validation)
- `feat: dynamic heading family discovery with profile matching`
- **Why:** OCR needs font/size/layout evidence, not just text heuristics.

#### 6b. Anchor Discovery
- `feat: discover OCR body family anchor`
- `feat: anchor OCR reference families`
- `feat: add OCR region bus inference`
- `feat: partition OCR families inside zones`
- `feat: promote source-backed frontmatter anchors`
- **Why:** Stable anchors must be found before role assignment.

#### 6c. Role Resolution & Validation
- `feat: add late OCR role resolution`
- `feat: validate OCR table matching`
- `feat: tighten OCR figure validation matching`
- `feat: unify OCR decision statuses`
- `feat: wire OCR anchor artifacts`
- `refactor: split OCR seed and final roles`
- **Why:** Roles must be resolved late, after structure exists.

#### 6d. Real-Paper Fixes (iterative)
- Numerous fix commits for: reference zone authority, frontmatter isolation, body retention thresholds, non-body insert detection, math normalization, figure pipeline fixes, etc.
- **Why:** Real papers exposed edge cases not covered by initial design.

### Phase 7: Figure/Table Reader (papers-specific)
- `docs: add OCR figure reader contract design` (2026-06-10)
- `feat: add OCR reader figure schema and stable ids`
- `feat: normalize strict OCR figure inventory for reader synthesis`
- `feat: materialize OCR reader figures and hold semantics`
- `feat: render OCR reader figures without debug leakage`
- `feat: add strict OCR sequence match promotion`
- Multiple fix commits for: figure semantics, render hygiene, reader contract
- **What:** Reader-facing figure output separated from body prose.
- **Why:** Figures must be reader-visible without polluting body flow.

### Phase 8: Verified Structural Role Gate (2026-06-11)
- `docs: document OCR structural role gate` (f281cbe)
- `feat: merge OCR role gate into health` (39a69f9)
- `feat: install OCR verified role gate`
- `feat: add OCR role gate context adapters`
- `feat: verify OCR reference zone from document artifacts`
- **What:** Installed a document-level gate that prevents unverified high-risk roles from rendering. Uses `VERIFY_REQUIRED` set with `role_verification_status`, `role_source`, `role_evidence`.
- **Why:** The original spec was being bypassed -- roles were being assigned and consumed without verification. The gate enforces the anchor-first contract.

### Phase 10: Production-Path Root-Cause Remediation (2026-06-13, LATEST)

**Trigger:** Real-paper regression tests (CAQNW9Q2, DWQQK2YB) surfaced systematic gaps. Instead of patching symptoms, each fix targeted the production path upstream.

#### 10a. Test Infrastructure
- `test: add real-paper trace vs expectations regression harness with fixtures` (e055f6f)
- block_trace.csv copied from vault into test fixtures for self-contained tests
- expectations.json uses only real pipeline roles, updated as fixes land
- **Why:** Needed ground-truth gap measurement before making production changes.

#### 10b. Frontmatter Anchor Bridge (RC1)
- `fix: add ocr_page to source-backed frontmatter anchors` (fe73c3f)
- `fix: bridge frontmatter anchors, add zone fallback...` (5a72315)
- **Root cause:** `_build_source_frontmatter_anchor_ids` read from `source_frontmatter_anchor_ids` but anchors were stored under `source_frontmatter_anchors` (different attribute name). paper_title/authors always HELD.
- **Fix:** Bridge function now reads both attribute shapes. Added `ocr_page` to writer for page-qualified IDs.

#### 10c. Figure Caption Gate (RC2)
- `fix: preserve figure_caption as candidate and extend reference item continuations` (3b130a5)
- `test: add gate handler tests for figure_caption candidate preservation` (417b5b9)
- **Root cause:** `figure_caption` in VERIFY_REQUIRED but no handler in `resolve_verified_role`. Always HELD → unknown_structural.
- **Fix:** Added figure_caption handler: when `accepted_caption_block_ids` empty, returns CANDIDATE with `figure_caption_candidate` (preserved for figure_inventory). Does not fake ACCEPT.

#### 10d. `unassigned` Role Bug (the unifying discovery)
- `fix: use seed_role in zone fallback when role is unassigned` (02cca45)
- `fix: handle unassigned role in zone infer_zones and frontmatter boundary detection` (2ceaa2e)
- **Root cause:** Zone inference and boundary detection run BEFORE structural gate. All blocks have `role="unassigned"` at that point. Code pattern `role = block.get("role") or block.get("seed_role")` failed because `"unassigned"` is truthy.
- **Fix:** Added explicit `if role == "unassigned": role = block.get("seed_role")` in zone fallback, page-1 boundary scan, and post-reference backmatter detection.
- **Impact:** DW empty zones 72→5, CAQ body_zone +5, page 1 frontmatter boundary working.

#### 10e. Figure Pipeline Rescue
- `fix: relax figure caption narrative prose filter and add sequential matching fallback for cross-page captions` (c407ca9)
- `fix: merge adjacent heading blocks at seed level, fix sequential match asset page` (2364fb9)
- **Root cause 1:** `_is_body_mention` rejected figure captions with figure numbers as body prose.
- **Root cause 2:** Spatial matching required same-page legend+asset; sequential fallback added for cross-page captions.
- **Root cause 3:** Sequential match used caption's page for crop, not asset's page.
- **Impact:** DW 0→4 matched figures, CAQ 1→3. All EXACT_MATCH.

#### 10f. Fulltext Rendering Cleanup
- `fix: remove internal status labels from reader figure card output` (3c9d4f3)
- `fix: suppress reader figure cards when embed covers them` (a26de38)
- `fix: remove blockquote prefix from abstract, fix backmatter_start detection` (f522602)
- `fix: exclude bullet-prefixed highlight text from abstract rendering` (06549fd)
- **Impact:** EXACT_MATCH/LEGEND_ONLY status labels removed from figure cards. Figure cards suppressed when embed note covers them. Abstract rendered as plain text. Highlight bullets excluded from abstract.

#### 10g. Backmatter Boundary Detection
- `fix: merge adjacent heading raw blocks before seed role assignment` (8e9ec5a)
- `fix: handle unassigned role in zone infer_zones...` (partial)
- `fix: use max(backward_start, references_start) for spread_end` (f12f20c)
- **Root cause:** `_detect_backward_backmatter_start` scanned backward for role matches but roles were `"unassigned"`. Used dense_refs check that triggered on biography pages (misclassified as reference_items).
- **Fix:** Added seed_role checks. Changed from early-return to min-page tracking. Added `backmatter_heading_candidate` to recognized roles. Requires `reference_heading` on same page for dense_refs. `spread_end` uses max of backward_start and references_start.
- **Impact:** `backmatter_start` 33→25. Conflict of Interest + Acknowledgments promoted to `backmatter_heading`. Reading order fixed.

#### 10h. Heading Merge (Adjacent OCR-Line-Wrap Prevention)
- `fix: merge adjacent heading raw blocks before seed role assignment` (8e9ec5a)
- **Root cause:** OCR splits long headings across lines; second half gets `text` raw_label instead of `paragraph_title`.
- **Fix:** Before seed role assignment, merge adjacent `paragraph_title` blocks on same page + column with ≤30px vertical gap.
- **Constraint:** Only ≤30px gap (same heading, different line). Does NOT merge separate headings at different y-positions. Column-aware to prevent cross-column merge.
- **Impact:** CAQ "Increasing the accuracy and reproducibility in standard radiography" now single heading.

---

## 3. Current State (as of 2026-06-13, end of Phase 10)

### 3.1 What is done

| Component | Status | Key Files |
|-----------|--------|-----------|
| Structural gate | Installed + figure_caption candidate handler | `paperforge/worker/ocr_structural_gate.py` |
| Role assignment (seed only) | Refactored | `paperforge/worker/ocr_roles.py` |
| Zone inference + fallback | Fixed: unassigned role bug | `paperforge/worker/ocr_document.py` |
| Page-1 frontmatter boundary | Working (after unassigned fix) | `paperforge/worker/ocr_document.py` |
| Tail spread body-continuation veto | Installed | `paperforge/worker/ocr_document.py` |
| Post-reference backmatter zone | Installed | `paperforge/worker/ocr_document.py` |
| Reference continuation expansion | Installed | `paperforge/worker/ocr_structural_gate.py` |
| Document normalization with gate | Integrated | `paperforge/worker/ocr_document.py` |
| Figure inventory: sequential matching | Installed for cross-page legends | `paperforge/worker/ocr_figures.py` |
| Renderer consuming verified artifacts | Cleaned: no internal status labels, no redundant cards | `paperforge/worker/ocr_render.py` |
| Heading merge (OCR line-wrap) | Position-based (≤30px vertical gap) | `paperforge/worker/ocr_blocks.py` |
| Backmatter boundary detection | Fixed: seed_role + min-page scan | `paperforge/worker/ocr_document.py` |
| Abstract rendering | Clean: no blockquote, bullet lines excluded | `paperforge/worker/ocr_render.py` |
| Real-paper test fixtures (2 active papers) | In repo, auto-synced from vault | `tests/fixtures/ocr_real_papers/{DWQQK2YB,CAQNW9Q2}/` |
| Trace vs expectations regression harness | Running | `tests/test_ocr_trace_vs_expectations.py` |
| Full test suite | 411 passed, 0 failed | unit + CLI + document + gate |

### 3.2 Real-paper gap report (post Phase 10)

**DWQQK2YB: 39/63 PASS, 24 FAIL**

| Category | Count | Root Cause |
|----------|-------|------------|
| Preproof frontmatter metadata (title/authors/PII) | 9 | Preproof cover suppression overwrites seed roles |
| Abstract/highlights boundary | 2 | Highlight bullet mislabeled as abstract by PaddleOCR |
| Biography role normalization | 9 | Biographies still reference_item; need backmatter_body normalization in post-reference zone |
| Backmatter heading recognition (Biographies, Table Captions) | 2 | sub_subsection_heading/subsection_heading should be backmatter_heading |
| Equal contribution statement | 1 | backmatter_body should be structured_insert |
| "Ami Yoo received" / "Eunpyo Choi received" NOT FOUND | 2 | Page mismatch in expectations (biographies span pages 32-34) |

**CAQNW9Q2: 17/23 PASS, 6 FAIL**
| Category | Count | Root Cause |
|----------|-------|------------|
| Title/author unknown_structural | 3 | Author name format mismatch (J C vs J.C.) |
| REVIEW label unknown_structural | 1 | Article type label not recognized |
| Page 7 Conclusion zone empty | 1 | ref_start=7 blocks Conclusion from body_zone (same-page ref/body conflict) |
| Page 7 gratitude text zone empty | 1 | body_paragraph not classified as backmatter_body |

### 3.3 What is NOT done

1. **RC1 completion:** CAQ title/authors still HELD — `_match_author_block_to_source_authors` needs period/space normalization. DW preproof page 1 title/authors need seed rescue.
2. **Biography role normalization:** reference_item → backmatter_body conversion in post_reference_backmatter_zone.
3. **Backmatter heading recognition:** `sub_subsection_heading` before `backmatter_start` should be promoted.
4. **Same-page ref/body conflict:** Reference zone start on same page blocks body headings.

---

## 4. Next Steps (Ordered by Priority, post Phase 10)

### 4.1 Second repair cycle (remaining root causes)

- [ ] **RC1 completion:** Fix author name matching (period/space normalization) in `_match_author_block_to_source_authors`. Fix DW preproof page 1 title/authors seed rescue.
- [ ] **Biography role normalization:** Convert `reference_item` → `backmatter_body` in `post_reference_backmatter_zone` during `normalize_document_structure`.
- [ ] **Backmatter heading promotion:** Promote `sub_subsection_heading` / `subsection_heading` before `backmatter_start` to `backmatter_heading`.
- [ ] **Same-page ref/body zone:** Reference zone start on same page should not block body-zone assignment for pre-reference blocks.
- [ ] **Update DW expectations for biography page mapping** (pages 32-34 instead of 33-34).

### 4.2 Merge back to master

- [ ] Verify all tests pass (unit, CLI, document, gate) — 411/411 currently green
- [ ] Verify real-paper regression on audited samples
- [ ] Run lint (ruff)
- [ ] Merge `ocr-v2` into `master`

---

## 5. Key File Map

### 5.1 Production code (OCR pipeline)

| File | Role |
|------|------|
| `paperforge/worker/ocr_blocks.py` | Raw + structured block generation; preserves seed_role only |
| `paperforge/worker/ocr_roles.py` | `assign_block_role()` -- seed/proposal logic only (NOT final) |
| `paperforge/worker/ocr_document.py` | `normalize_document_structure()` -- anchor/family/zone + gate + final roles |
| `paperforge/worker/ocr_structural_gate.py` | `VERIFY_REQUIRED` + role decision + abstract span + reference zone + health counters |
| `paperforge/worker/ocr_orchestrator.py` | Body reorder, column validation, layered assembly |
| `paperforge/worker/ocr_render.py` | `render_fulltext_markdown()` -- consumes verified artifacts ONLY |
| `paperforge/worker/ocr.py` | CLI entry, page rendering, figure/table embed |
| `paperforge/worker/ocr_health.py` | Health reporting, merged with gate summary |
| `paperforge/worker/ocr_profiles.py` | Span extraction, profile aggregation, cross-validation |
| `paperforge/worker/ocr_figures.py` | Figure reader pipeline |
| `paperforge/worker/ocr_tables.py` | Table inventory and matching |

### 5.2 Test files

| File | Tests |
|------|-------|
| `tests/test_ocr_trace_vs_expectations.py` | **NEW**: Real-paper trace vs expectations gap report (DWQQK2YB, CAQNW9Q2) |
| `tests/test_ocr_real_paper_regressions.py` | Page-level + document-level regression on real papers |
| `tests/test_ocr_spec_contracts.py` | Architecture contract tests |
| `tests/test_ocr_structural_gate.py` | Gate unit tests (incl. figure_caption candidate) |
| `tests/test_ocr_entrypoints.py` | Hard guard: OCR-v2 must use document pipeline |
| `tests/test_ocr_v2_structural_regressions.py` | Synthetic tests through document pipeline |
| `tests/test_ocr_document.py` | `normalize_document_structure()` with verification fields |
| `tests/test_ocr_render.py` | Renderer consuming accepted spans/objects |
| `tests/test_ocr_health.py` | Health with gate degradation |
| `tests/test_ocr_roles.py` | Legacy role tests |
| `tests/test_ocr_rendering.py` | Legacy render tests |

### 5.3 Test fixtures

| Path | Paper | Purpose |
|------|-------|---------|
| `tests/fixtures/ocr_real_papers/CAQNW9Q2/` | CAQNW9Q2 | Comprehensive structure sample |
| `tests/fixtures/ocr_real_papers/DWQQK2YB/` | DWQQK2YB | Figure/legend sample |
| `tests/fixtures/ocr_real_papers/A8E7SRVS/` | A8E7SRVS | Additional audited paper |

### 5.4 Design documents

| File | Purpose |
|------|---------|
| `docs/superpowers/specs/2026-06-08-ocr-anchor-first-structured-parsing-design.md` | Architecture spec (946 lines) |
| `docs/superpowers/specs/2026-06-13-ocr-real-paper-regression-and-spec-realignment-design.md` | Current phase spec (374 lines) |
| `docs/superpowers/specs/2026-06-10-ocr-figure-reader-contract-design.md` | Figure reader spec |
| `docs/superpowers/specs/2026-06-01-ocr-redo-single-source-design.md` | OCR redo spec |
| `docs/superpowers/specs/README-ocr.md` | OCR design index |
| `docs/superpowers/plans/2026-06-11-ocr-verified-structural-role-gate.md` | Role gate plan (1257 lines) |
| `docs/superpowers/plans/2026-06-08-ocr-anchor-first-structured-parsing-plan.md` | Main implementation plan |
| `docs/superpowers/plans/2026-06-10-ocr-figure-reader-contract-implementation.md` | Figure reader plan |

---

## 6. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-08 | Adopt anchor-first OCR architecture | Early role guessing caused cascading errors; needed structural discovery first |
| 2026-06-10 | Separate figure reader from body prose | Figure info must be reader-visible without body pollution |
| 2026-06-11 | Install verified structural role gate | Spec was being bypassed; gate enforces seed!=final contract |
| 2026-06-13 | Dual-gate regression + spec-contract testing | Tests protected helper behavior, not real-paper outcomes; needed trustworthy gate before repairs |
| 2026-06-13 | Limit first repair to 3 files (roles, orchestrator, render) | Prevents scope creep into full rewrite; fixes highest-impact failures first |
| 2026-06-13 | Root-cause approach: no renderer patches | Heading merge goes in raw blocks (before seed), boundary detection fixed in infer_zones (not renderer), figure cards clean at renderer but card logic stays upstream |
| 2026-06-13 | Figure sequential matching as cross-page tradeoff | `build_figure_inventory` requires same-page spatial match; sequential fallback added for caption-asset pairs on different pages (lower confidence, acceptable for user-facing output) |
| 2026-06-13 | `backmatter_heading_candidate` seed_role detection in backward scan | `_detect_backward_backmatter_start` must check seed_role (not just role) because roles are `"unassigned"` at scan time |

---

## 7. Agent Instructions

### 7.1 How to update this file

When completing a step:
1. Add a new row to the timeline in section 2 under the current phase
2. Mark the corresponding checkbox in section 4
3. Update section 3 (Current State) if applicable
4. Add any new decisions to section 6
5. Update the "Last Updated" date at top

### 7.2 Before starting any OCR-v2 work

1. Read section 4 (Next Steps) for current priority
2. Read the relevant design doc from section 5.4
3. Understand what the tests currently expect
4. Work one repair at a time; verify before moving on

### 7.3 Test commands

```bash
# Full OCR test suite
python -m pytest tests/test_ocr_*.py -v --tb=short

# Real-paper regression only
python -m pytest tests/test_ocr_real_paper_regressions.py -v --tb=short

# Spec-contract tests only
python -m pytest tests/test_ocr_spec_contracts.py -v --tb=short

# Structural gate only
python -m pytest tests/test_ocr_structural_gate.py tests/test_ocr_document.py -v --tb=short

# Lint
python -m ruff check paperforge/worker/ocr_*.py
```

### 7.4 Design doc reading order (for new contributors)

1. `docs/superpowers/specs/README-ocr.md` -- index
2. `docs/superpowers/specs/2026-06-08-ocr-anchor-first-structured-parsing-design.md` -- architecture
3. `docs/superpowers/specs/2026-06-13-ocr-real-paper-regression-and-spec-realignment-design.md` -- current phase

---

*Vault-Tec Research Log -- End of Entry -- Preparing for the Future!*
