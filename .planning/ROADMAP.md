# Roadmap: PaperForge Lite

**Project kind:** brownfield-release-hardening
**Current milestone:** v1.5 — Obsidian Plugin Setup Integration
**Phase numbering:** Continuous (never restarts). v1.0 Phases 1-5, v1.1 Phases 6-8, v1.2 Phases 9-10, v1.3 Phases 11-12, v1.4 Phases 13-19, v1.5 Phases 20-21

---

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-04-23)
- ✅ **v1.1 Sandbox Onboarding** — Phases 6-8 (shipped 2026-04-24)
- ✅ **v1.2 Systematization & Cohesion** — Phases 9-10 (shipped 2026-04-24)
- ✅ **v1.3 Path Normalization & Architecture Hardening** — Phases 11-12 (shipped 2026-04-24)
- ✅ **v1.4 Code Health & UX Hardening** — Phases 13-19 (shipped 2026-04-28)
- 🚧 **v1.5 Obsidian Plugin Setup Integration** — Phases 20-21 (in progress)

---

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-5) — SHIPPED 2026-04-23</summary>

### Phase 1: Config And Command Foundation
**Goal**: Stable commands and shared path/env resolution
**Plans**: 3/3 plans complete

### Phase 2: PaddleOCR And PDF Path Hardening
**Goal**: Diagnosable, retryable OCR
**Plans**: 2/2 plans complete

### Phase 3: Config-Aware Obsidian Bases
**Goal**: Real workflow Bases without hardcoded paths
**Plans**: 2/2 plans complete

### Phase 4: End-To-End Onboarding And Validation
**Goal**: User can complete first-paper flow
**Plans**: 2/2 plans complete

### Phase 5: Release Verification
**Goal**: Tests and docs prove ship readiness
**Plans**: 2/2 plans complete

_Archived: `.planning/milestones/v1.0.md`_

</details>

<details>
<summary>✅ v1.1 Sandbox Onboarding (Phases 6-8) — SHIPPED 2026-04-24</summary>

### Phase 6: Setup, CLI, And Diagnostics Consistency
**Goal**: Field names, env vars, export validation, HTTP 405 handling, vault prefill
**Plans**: 3/3 plans complete

### Phase 7: Zotero PDF, Metadata, And State Repair
**Goal**: OCR meta validation, three-way divergence repair, PDF resolver tests
**Plans**: 2/2 plans complete

### Phase 8: Deep Helper Deployment And Sandbox Regression Gate
**Goal**: Importability, fixtures, smoke tests, rollback
**Plans**: 2/2 plans complete

_Archived: `.planning/milestones/v1.1.md`_

</details>

<details>
<summary>✅ v1.2 Systematization & Cohesion (Phases 9-10) — SHIPPED 2026-04-24</summary>

### Phase 9: Command Unification & CLI Simplification
**Goal**: Unified `/pf-*` namespace, `paperforge sync` combined command
**Plans**: 2/2 plans complete

### Phase 10: Documentation & Cohesion
**Goal**: Updated AGENTS.md, migration guide, consistency audit
**Plans**: 2/2 plans complete

_Archived: `.planning/milestones/v1.2-ROADMAP.md`_

</details>

<details>
<summary>✅ v1.3 Path Normalization & Architecture Hardening (Phases 11-12) — SHIPPED 2026-04-24</summary>

### Phase 11: Zotero Path Normalization
**Goal**: Parse 3 BBT formats, generate wikilinks, multi-attachment support
**Plans**: 1/1 plan complete
**Requirements**: ZPATH-01, ZPATH-02, ZPATH-03

### Phase 12: Architecture Cleanup
**Goal**: Eliminate module boundary leaks (pipeline/ → paperforge/worker/), migrate skills
**Plans**: 1/1 plan complete
**Requirements**: ARCH-01, ARCH-02

_Archived: `.planning/milestones/v1.3.md`_

</details>

<details>
<summary>✅ v1.4 Code Health & UX Hardening (Phases 13-19) — SHIPPED 2026-04-28</summary>

### Phase 13: Logging Foundation
**Goal**: Structured logging, `--verbose` flag, zero behavioral change to user-facing output
**Requirements**: OBS-01, OBS-02, OBS-03
**Plans**: 3/3 plans complete

### Phase 14: Shared Utilities Extraction
**Goal**: Extract `_utils.py`, eliminate ~1,610 lines of duplication across 7 workers
**Requirements**: CH-01, CH-02, CH-05, TEST-03
**Plans**: 2/2 plans complete

### Phase 15: Deep-Reading Queue Merge
**Goal**: Single canonical `scan_library_records()` for both CLI and Agent consumers
**Requirements**: CH-03, CH-04
**Plans**: 1/1 plan complete

### Phase 16: Retry + Progress Bars
**Goal**: Resilient OCR with exponential backoff and user-visible progress indication
**Requirements**: UX-01, UX-02
**Plans**: 2/2 plans complete

### Phase 17: Dead Code Removal + Pre-Commit
**Goal**: Clean codebase validated by automated git hooks (ruff)
**Requirements**: CH-06, CH-07
**Plans**: 1/1 plan complete

### Phase 18: Documentation + CHANGELOG + UX Polish
**Goal**: Complete user/maintainer docs, auto_analyze_after_ocr, CHANGELOG, CONTRIBUTING
**Requirements**: DOC-01, DOC-02, DOC-03, UX-03
**Plans**: 2/2 plans complete

### Phase 19: Testing
**Goal**: E2E pipeline tests, setup wizard tests, `_utils.py` unit tests (317 passed, 2 skipped)
**Requirements**: TEST-01, TEST-02, TEST-04
**Plans**: 3/3 plans complete

_Note: Phase 20 (v1.4.2 "Headless Setup & Obsidian Plugin") was a placeholder. v1.5 expands this into a full plugin settings tab with setup integration — see Phases 20-21 below._

_Archived: `.planning/milestones/v1.4.md`_

</details>

### 🚧 v1.5 Obsidian Plugin Setup Integration (In Progress)

**Milestone Goal:** Move the entire PaperForge setup/configuration experience from terminal CLI into the Obsidian plugin's settings tab, so a new user downloads one plugin and completes full installation without touching a terminal.

- [x] **Phase 20: Plugin Settings Shell & Persistence** — Obsidian settings tab with all setup fields, persistence across restarts, debounced saves (completed 2026-04-29)
- [ ] **Phase 21: One-Click Install & Polished UX** — Install button with field validation, `spawn`-based subprocess orchestration, human-readable Chinese notices

---

## Phase Details

### Phase 20: Plugin Settings Shell & Persistence
**Goal**: Users can access PaperForge configuration in Obsidian's Settings tab, edit all setup wizard fields, and settings survive restarts and tab switches — all without breaking the existing sidebar.
**Depends on**: Phase 19 (tested deployment pipeline exists)
**Requirements**: SETUP-01, SETUP-02, SETUP-03
**Success Criteria** (what must be TRUE):
  1. User opens Obsidian Settings → Community Plugins → PaperForge (gear icon) and sees a settings tab with all 8 configuration fields grouped in logical sections with Chinese labels and tooltips
  2. User edits any text field, navigates to a different settings tab and returns — all edited values remain intact (in-memory state survives `display()` re-invocation without data loss)
  3. User fills in all fields, closes and re-opens Obsidian, and all values restore correctly from `data.json` — no data loss, corruption, or `TypeError` on null data
  4. First-time install (no prior `data.json`) loads gracefully with `DEFAULT_SETTINGS` values pre-filled — settings tab renders cleanly without JavaScript errors
  5. After registering the settings tab via `addSettingTab()`, the existing `PaperForgeStatusView` sidebar and command palette actions (`Sync Library`, `Run OCR`) continue functioning without regression
**Plans**: TBD
**UI hint**: yes

### Phase 21: One-Click Install & Polished UX
**Goal**: Users trigger full PaperForge setup with one click and receive step-by-step Chinese feedback via Obsidian notices — no terminal interaction required, no raw traceback exposure.
**Depends on**: Phase 20 (settings tab shell and persistence must exist before adding install behavior)
**Requirements**: INST-01, INST-02, INST-03, INST-04
**Success Criteria** (what must be TRUE):
  1. User fills in all required configuration fields and clicks "安装配置" — the full setup pipeline executes: `paperforge.json` is written, directories are created, environment checks pass, and agent configs are generated
  2. During setup execution, the Install button is visually disabled and displays "正在安装..." — clicking it again produces no duplicate subprocess (double-click prevention with `setDisabled(true)`)
  3. User sees step-by-step Chinese notice toasts throughout setup progress ("正在创建目录... ✓", "正在写入配置文件... ✓", "正在检查环境... ✓") — raw Python tracebacks or terminal stderr content is never displayed directly in the Notice
  4. User leaves a required field empty (e.g., Vault path) and clicks Install — receives a specific, friendly Chinese error notice (e.g., "未找到 Vault 路径，请检查设置") before any subprocess is spawned, preventing cryptic mid-install failures
  5. After setup completes (success or failure), the sidebar `PaperForgeStatusView` panel and command palette actions (`Sync Library`, `Run OCR`) continue working normally — settings tab code is strictly additive with zero coupling to sidebar internals
**Plans**: 2 plans (21-01, 21-02)
**UI hint**: yes

---

## Progress

**Execution Order:** Phases 20 → 21 are strictly sequential. Phase 20 provides the settings shell; Phase 21 adds install behavior on top.

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Config & Command Foundation | v1.0 | 3/3 | Complete | 2026-04-23 |
| 2. PaddleOCR & PDF Path Hardening | v1.0 | 2/2 | Complete | 2026-04-23 |
| 3. Config-Aware Obsidian Bases | v1.0 | 2/2 | Complete | 2026-04-23 |
| 4. End-To-End Onboarding | v1.0 | 2/2 | Complete | 2026-04-23 |
| 5. Release Verification | v1.0 | 2/2 | Complete | 2026-04-23 |
| 6. Setup & CLI Diagnostics | v1.1 | 3/3 | Complete | 2026-04-24 |
| 7. Zotero PDF & Metadata Repair | v1.1 | 2/2 | Complete | 2026-04-24 |
| 8. Deep Helper & Sandbox Gate | v1.1 | 2/2 | Complete | 2026-04-24 |
| 9. Command Unification & CLI | v1.2 | 2/2 | Complete | 2026-04-24 |
| 10. Documentation & Cohesion | v1.2 | 2/2 | Complete | 2026-04-24 |
| 11. Zotero Path Normalization | v1.3 | 1/1 | Complete | 2026-04-24 |
| 12. Architecture Cleanup | v1.3 | 1/1 | Complete | 2026-04-24 |
| 13. Logging Foundation | v1.4 | 3/3 | Complete | 2026-04-27 |
| 14. Shared Utils Extraction | v1.4 | 2/2 | Complete | 2026-04-27 |
| 15. Queue Merge | v1.4 | 1/1 | Complete | 2026-04-27 |
| 16. Retry + Progress | v1.4 | 2/2 | Complete | 2026-04-27 |
| 17. Dead Code + Pre-Commit | v1.4 | 1/1 | Complete | 2026-04-27 |
| 18. Docs + CHANGELOG + UX | v1.4 | 2/2 | Complete | 2026-04-27 |
| 19. Testing | v1.4 | 3/3 | Complete | 2026-04-28 |
| 20. Plugin Settings Shell & Persistence | v1.5 | 1/1 | Complete    | 2026-04-29 |
| 21. One-Click Install & Polished UX | v1.5 | 0/2 | Planned     | — |

---

*Roadmap updated: 2026-04-29 — Phase 21 plans created (One-Click Install & Polished UX)*
