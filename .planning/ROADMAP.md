# Roadmap: v1.3 Path Normalization & Architecture Hardening

**Current:** v1.3 In Progress (2026-04-24)
**Next:** Phase 11 planning

---

## Phases

### Phase 11: Zotero Path Normalization

**Goal:** Implement robust Zotero attachment path parsing and Obsidian wikilink generation.

**Status:** COMPLETE (8/8 tasks)
**Requirements:** ZPATH-01, ZPATH-02, ZPATH-03, SYS-08

Plans:

- [x] 11-PLAN.md: Wave 1 — BBT Path Parsing & Normalization (Tasks 01-02)
  - [x] Task 01: `_normalize_attachment_path()` — absolute Windows, storage:, bare relative
  - [x] Task 02: `_identify_main_pdf()` — hybrid strategy (title -> size -> shortest title)
  
- [x] 11-PLAN.md: Wave 2 — Wikilink Generation & Multi-Attachment (Tasks 03-04)
  - [x] Task 03: `obsidian_wikilink_for_pdf()` rewrite with `zotero_dir` and junction resolution
  - [x] Task 04: Frontmatter updates — `pdf_path`, `supplementary`, `bbt_path_raw`, `path_error`
  
- [x] 11-PLAN.md: Wave 3 — Doctor Integration & Error Handling (Tasks 05-06)
  - [x] Task 05: `paperforge doctor` junction detection and path validation
  - [x] Task 06: `paperforge repair` and `status` path_error integration
  
- [x] 11-PLAN.md: Wave 4 — Tests, Docs & Verification (Tasks 07-08)
  - [x] Task 07: `test_path_normalization.py` with 25 test methods
  - [x] Task 08: Documentation updates and final verification

**Success criteria:**
1. All 4 BBT path input formats correctly parsed
2. Wikilink output matches Obsidian standard
3. Multi-attachment items handled gracefully
4. 100% test coverage for path resolver (25 tests, all passing)

---

### Phase 12: Architecture Cleanup

**Goal:** Fix module boundaries and eliminate test dead zones.

**Status:** Not started
**Requirements:** ARCH-01, ARCH-02, ARCH-03, ARCH-04, TEST-01, TEST-02, TEST-05

Plans:

- [ ] 12-01: Merge pipeline into paperforge package
  - Move `pipeline/worker/scripts/` → `paperforge/worker/`
  - Update all imports
  - Ensure `__init__.py` files present
  
- [ ] 12-02: Integrate skill scripts
  - Move `skills/literature-qa/` → `paperforge/skills/`
  - Update `ld_deep.py` imports
  - Update AGENTS.md references
  
- [ ] 12-03: Fix test dead zones
  - Fix `test_pdf_resolver.py` attachment normalization
  - Fix/remove `test_base_preservation.py` and `test_base_views.py`
  - Verify all tests pass (0 failures)

**Success criteria:**
1. `from paperforge.worker.literature_pipeline import ...` works
2. `from paperforge.skills.literature_qa.ld_deep import ...` works
3. All 178+ tests pass with 0 failures
4. No import collection errors

---

### Phase 13: Quality Assurance Integration

**Goal:** Make consistency audit part of the development workflow.

**Status:** Not started
**Requirements:** QA-01, QA-02, QA-03

Plans:

- [ ] 13-01: Pre-commit hook
  - Create `.pre-commit-config.yaml`
  - Integrate `scripts/consistency_audit.py`
  - Auto-fix mode for violations
  
- [ ] 13-02: CONTRIBUTING.md
  - Document development workflow
  - Explain audit checks
  - Setup instructions for contributors
  
- [ ] 13-03: CI-ready audit
  - GitHub Actions workflow (optional)
  - Ensure audit runs on every PR
  - Block merge on audit failure

**Success criteria:**
1. `git commit` triggers consistency audit
2. Audit failures block commit (or auto-fix)
3. CONTRIBUTING.md explains workflow
4. CI runs audit on pull requests

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|---------------|--------|-----------|
| 1-5 | v1.0 | — | Complete | 2026-04-23 |
| 6-8 | v1.1 | — | Complete | 2026-04-24 |
| 9-10 | v1.2 | — | Complete | 2026-04-24 |
| 11 | v1.3 | 1/1 | Complete | 2026-04-24 |
| 12 | v1.3 | 0/1 | Not started | — |
| 13 | v1.3 | 0/1 | Not started | — |

---

<details>
<summary>✅ v1.0 MVP (Phases 1-5) — SHIPPED 2026-04-23</summary>

- Phase 1: Config And Command Foundation (3/3 plans)
- Phase 2: PaddleOCR And PDF Path Hardening (2/2 plans)
- Phase 3: Config-Aware Obsidian Bases (2/2 plans)
- Phase 4: End-To-End Onboarding And Validation (2/2 plans)
- Phase 5: Release Verification (2/2 plans)

_Archived: `.planning/milestones/v1.0.md`_

</details>

<details>
<summary>✅ v1.1 Sandbox Onboarding (Phases 6-8) — SHIPPED 2026-04-24</summary>

- Phase 6: Setup, CLI, And Diagnostics Consistency (3/3 plans)
- Phase 7: Zotero PDF, Metadata, And State Repair (2/2 plans)
- Phase 8: Deep Helper Deployment And Sandbox Regression Gate (2/2 plans)

_Archived: `.planning/milestones/v1.1.md`_

</details>

<details>
<summary>✅ v1.2 Systematization & Cohesion (Phases 9-10) — SHIPPED 2026-04-24</summary>

- Phase 9: Command Unification & CLI Simplification (2/2 plans)
- Phase 10: Documentation & Cohesion (2/2 plans)

_Archived: `.planning/milestones/v1.2-ROADMAP.md`_

</details>
