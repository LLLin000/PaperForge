# Roadmap: PaperForge

**Current milestone:** v1.11 — Merge Gate (v1.9 Ripple Remediation)
**Phase numbering:** Continuous. v1.10 ended at Phase 45. v1.11 starts at Phase 46.

---

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-04-23)
- ✅ **v1.1 Sandbox Onboarding** — Phases 6-8 (shipped 2026-04-24)
- ✅ **v1.2 Systematization & Cohesion** — Phases 9-10 (shipped 2026-04-24)
- ✅ **v1.3 Path Normalization & Architecture Hardening** — Phases 11-12 (shipped 2026-04-24)
- ✅ **v1.4 Code Health & UX Hardening** — Phases 13-19 (shipped 2026-04-28)
- ✅ **v1.5 Obsidian Plugin Setup Integration** — Phases 20-21 (shipped 2026-04-29)
- ✅ **v1.6 AI-Ready Literature Asset Foundation** — Phases 22-26 (shipped 2026-05-04)
- ✅ **v1.7 Context-Aware Dashboard** — Phases 27-30 (shipped 2026-05-04)
- ✅ **v1.8 AI Discussion & Deep-Reading Dashboard** — Phases 31-36 (shipped 2026-05-07)
- ✅ **v1.9 Frontmatter Rationalization & Library-Record Deprecation** — Phases 37-41 (shipped 2026-05-07)
- ✅ **v1.10 Dependency Cleanup** — Phases 42-45 (shipped 2026-05-07)
- 🚧 **v1.11 Merge Gate — v1.9 Ripple Remediation** — Phases 46-50 (in progress)

*Archive: `.planning/milestones/`*

---

## Phases

<details>
<summary>✅ v1.6 AI-Ready Literature Asset Foundation (Phases 22-26) — SHIPPED 2026-05-04</summary>

- [x] Phase 22: Configuration Truth & Compatibility (3/3)
- [x] Phase 23: Canonical Asset Index & Safe Rebuilds (3/3)
- [x] Phase 24: Derived Lifecycle, Health & Maturity (2/2)
- [x] Phase 25: Surface Convergence, Doctor & Repair (3/3)
- [x] Phase 26: Traceable AI Context Packs (3/3)

</details>

<details>
<summary>✅ v1.7 Context-Aware Dashboard (Phases 27-30) — SHIPPED 2026-05-04</summary>

- [x] Phase 27: Component Library (2/2)
- [x] Phase 28: Dashboard Shell & Context Detection (2/2)
- [x] Phase 29: Per-Paper View (1/1)
- [x] Phase 30: Collection View (1/1)

</details>

<details>
<summary>✅ v1.8 AI Discussion & Deep-Reading Dashboard (Phases 31-36) — SHIPPED 2026-05-07</summary>

- [x] Phase 31: Bug Fixes — Restore version display; remove meaningless "ai" UI row
- [x] Phase 32: Deep-Reading Mode Detection — Plugin routes deep-reading.md to dedicated dashboard mode
- [x] Phase 33: Deep-Reading Dashboard Rendering — Status bar, Pass 1 summary, empty-state AI Q&A card
- [x] Phase 34: Jump to Deep Reading Button — Per-paper dashboard card links to deep-reading.md (completed 2026-05-06)
- [x] Phase 35: AI Discussion Recorder — Python module writes discussion.md + discussion.json into ai/ (completed 2026-05-06)
- [x] Phase 36: Integration Verification — End-to-end pipeline verified with CJK encoding and vault.adapter.read

</details>

<details>
<summary>✅ v1.9 Frontmatter Rationalization & Library-Record Deprecation (Phases 37-41) — SHIPPED 2026-05-07</summary>

- [x] Phase 37: Frontmatter Rationalization (1 plan)
- [x] Phase 38: Workspace Stabilization (1 plan)
- [x] Phase 39: Base View Fix
- [x] Phase 40: Library-Record Deprecation
- [x] Phase 41: Plugin Dashboard Sync

</details>

<details>
<summary>✅ v1.10 Dependency Cleanup (Phases 42-45) — SHIPPED 2026-05-07</summary>

**Milestone Goal:** Fix all code breakage and documentation staleness caused by v1.9's library-records deprecation and directory default changes.

- [x] **Phase 42: Core Pipeline Fix** — OCR, status, and sync workers read from formal notes, not library-records
- [x] **Phase 43: Repair & Directory Defaults** — Repair re-anchored; all hardcoded old directory defaults updated
- [x] **Phase 44: Documentation Update** — AGENTS.md, 5 skill files, and 3 docs reflect v1.9 structure
- [x] **Phase 45: Validation & Release Gate** — Tests pass; end-to-end OCR/status verification

</details>

### 🚧 v1.11 Merge Gate — v1.9 Ripple Remediation (Current)

**Milestone Goal:** Resolve all 27 findings from the v1.6-ai-ready-asset-foundation branch review before merging to master. Fix cascading v1.9 structural ripple across four root cause clusters: index path hardcoding, library-records residual traces, setup wizard TUI removal, and new module hardening gaps.

- [x] **Phase 46: Index Path Resolution** — 2 plans: config-resolved paths, env var/placeholder fixes
- [ ] **Phase 47: Library-Records Deprecation Cleanup** — Zero residual traces in production code and documentation
- [x] **Phase 48: Textual TUI Removal** — 2 plans: TUI code removal, documentation updates (completed 2026-05-07)
- [ ] **Phase 49: Module Hardening** — Production-grade safety guards in discussion.py, main.js, asset_state.py
- [x] **Phase 50: Repair Blind Spots** — All 6 divergence types detected and handled by fix mode (completed 2026-05-07)

---

## Phase Details

### Phase 42: Core Pipeline Fix
**Goal**: OCR, status, and sync workers read workflow state (do_ocr, analyze, ocr_status) from formal note frontmatter — same logic as the existing `get_analyze_queue()` pattern. Core workflow unbroken for new papers created post-v1.9.
**Depends on**: Nothing (first v1.10 phase; v1.9 shipped)
**Requirements**: WF-01, WF-02, WF-03, WF-04, SYN-01, SYN-02, SYN-03
**Success Criteria** (what must be TRUE):
  1. Running `paperforge ocr` finds and processes papers whose formal note frontmatter has `do_ocr: true` — no library-records reads
  2. `auto_analyze_after_ocr` writes `analyze: true` into the formal note frontmatter of the processed paper
  3. `paperforge status` reports paper counts and OCR status counts sourced from formal notes + canonical index, not from library-records
  4. `paperforge status` doctor checks (PDF path validation, wikilink format) sample from formal notes, not library-records
  5. `paperforge sync` no longer creates empty library-records domain directories; `load_control_actions()` scans formal note frontmatter instead of library-records directory
  6. Orphaned formal notes (no matching Zotero entry) are cleaned up from the Literature/ directory during sync
**Plans**: TBD

### Phase 43: Repair & Directory Defaults
**Goal**: Repair worker three-way divergence scan and path error detection re-anchored from library-records to formal notes + canonical index. All 14 hardcoded old directory defaults (`99_System`, `03_Resources`, `05_Bases`) updated across production code, setup wizard, validation script, .gitignore, and CLI help text to match `DEFAULT_CONFIG` (`System`, `Resources`, `Bases`).
**Depends on**: Phase 42 (formal note path model confirmed; repair needs the same scan pattern)
**Requirements**: REP-01, REP-02, REP-03, DEF-01, DEF-02, DEF-03, DEF-04, DEF-05, DEF-06, DEF-07
**Success Criteria** (what must be TRUE):
  1. `paperforge repair` three-way divergence scan reads from formal note frontmatter, canonical index, and paper-meta.json — zero library-records reads
  2. `paperforge repair --fix-paths` detects path errors by scanning formal notes and writes fixes into formal note frontmatter
  3. All `cfg.get("system_dir", "99_System")` fallbacks in asset_index, sync, and repair use `"System"` instead
  4. setup_wizard function signature defaults, validate_setup.py legacy fallbacks, and .gitignore patterns use clean directory names (`System`/`Resources`/`Bases`)
  5. CLI `--help` text displays clean default directory names; setup_wizard no longer creates an empty control_dir
**Plans**: TBD

### Phase 44: Documentation Update
**Goal**: All user-facing and agent-facing documentation reflects the v1.9 simplified structure. Zero references to the deprecated library-records workflow remain in AGENTS.md, 5 skill files, or 3 docs files.
**Depends on**: Phase 43 (all code changes finalized; documentation describes the settled behavior)
**Requirements**: DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07, DOC-08, DOC-09
**Success Criteria** (what must be TRUE):
  1. AGENTS.md contains zero references to library-records; frontmatter section shows only formal note fields
  2. All 5 skill files (pf-sync, pf-ocr, pf-status, pf-paper, pf-deep) describe the formal-note-only workflow with no mention of library-records
  3. docs/setup-guide.md directory structure diagram shows Literature/ workspace directories without library-records
  4. docs/ARCHITECTURE.md data flow reflects the v1.9 simplified tracking layer (formal notes + canonical index, no library-record intermediate)
  5. docs/COMMANDS.md sync description shows direct formal note generation without a two-phase library-record step
**Plans**: TBD

### Phase 45: Validation & Release Gate
**Goal**: All existing tests pass with zero regressions. End-to-end verification confirms OCR and status workers operate correctly on the new formal-note-based paths. Release gate met.
**Depends on**: Phase 44 (documentation may need test validation too; all code changes complete)
**Requirements**: VAL-01, VAL-02, VAL-03
**Success Criteria** (what must be TRUE):
  1. Full test suite passes with zero failures (no silent regressions in OCR, repair, sync, or status workflows)
  2. End-to-end: `paperforge ocr` correctly finds and processes a paper whose formal note has `do_ocr: true`
  3. `paperforge status` output contains zero references to library-records (no `library_records: 0` or equivalent)
**Plans**: TBD

### Phase 46: Index Path Resolution
**Goal**: All 5 workspace-path fields in the canonical index (`paper_root`, `main_note_path`, `fulltext_path`, `deep_reading_path`, `ai_path`) use config-resolved `literature_dir` instead of hardcoded `"Literature/"`. All 11 downstream consumers resolve correct paths. Config env var typo and migration gaps fixed.
**Depends on**: Nothing (first v1.11 phase; v1.10 shipped)
**Requirements**: PATH-01, PATH-02, PATH-03, PATH-04, PATH-05, PATH-06
**Success Criteria** (what must be TRUE):
  1. `paperforge sync` generates canonical index entries with `paper_root`, `main_note_path`, `fulltext_path`, `deep_reading_path`, and `ai_path` using the user's configured `literature_dir` — verified via `paperforge context <key> --json` showing correct paths
  2. Plugin dashboard renders per-paper views using config-resolved paths from the index (not hardcoded `"Literature/"`) — verified by opening a paper dashboard after sync with a non-default literature_dir
  3. Environment variable `PAPERFORGE_LITERATURE_DIR` correctly overrides `literature_dir` (no truncation to `PAPERFORGERATURE_DIR`) — verified via `paperforge paths --json`
  4. Legacy `paperforge.json` with top-level `skill_dir` and `command_dir` settings migrates into `vault_config` on first sync — no orphaned top-level keys remain
  5. Shipping `.base` templates contain zero `${LIBRARY_RECORDS}` placeholders — verified by inspecting generated Base files in a fresh vault
**Plans**: TBD
**Plans**: 2 plans

Plans:
- [x] 46-001-PLAN.md — Core path resolution: fix 5 hardcoded "Literature/" in asset_index.py, fix config.py (env var typo, library_records path, CONFIG_PATH_KEYS), fix test_config.py
- [x] 46-002-PLAN.md — Placeholder & Windows path cleanup: remove LIBRARY_RECORDS substitution in base_views.py, remove unnecessary backslash replace in discussion.py
**UI hint**: yes
 
### Phase 47: Library-Records Deprecation Cleanup
**Goal**: Zero library-records references remain in production code (status.py, sync.py, ld_deep.py), documentation (5 command skill files), or user-facing labels. Dead code removed, stale scan paths corrected, post-install instructions updated to single-command workflow.
**Depends on**: Phase 46 (sync.py docstring changes reference same config-resolved paths)
**Requirements**: LEGACY-01, LEGACY-02, LEGACY-03, LEGACY-04, LEGACY-05, LEGACY-06, LEGACY-07
**Success Criteria** (what must be TRUE):
  1. `paperforge status` reports `formal_notes` count (label is `formal_notes`, not `library_records`) — output reflects post-v1.9 reality
  2. Five command skill files (`pf-sync.md`, `pf-ocr.md`, `pf-status.md`, `pf-paper.md`, `pf-deep.md`) contain zero mentions of "library-records" — verified by `grep -r "library.record"` returning no hits in skill files
  3. `paperforge sync` no longer constructs `record_path` or calls `parse_existing_library_record()` — dead code removed, sync completes without errors
  4. Setup wizard post-install instructions describe a single `paperforge sync` workflow (not old `--selection`/`--index` two-phase flow)
  5. `paperforge repair` docstring reads "Scan formal literature notes" (not "library-records") and `ld_deep.py` return dict contains only active path keys
**Plans**: 2 plans

Plans:
- [x] 47-001-PLAN.md — Python source cleanup: status.py label/scan path, sync.py dead code + docstrings, ld_deep.py records key, repair.py + discussion.py docstrings (LEGACY-01, 02, 03, 04, 07)
- [ ] 47-002-PLAN.md — Documentation cleanup: setup_wizard.py post-install text, 10 command file copies in command/ + paperforge/command_files/ (LEGACY-05, 06)

### Phase 48: Textual TUI Removal
**Goal**: The broken Textual TUI setup wizard is removed entirely. `paperforge setup` (bare, no `--headless`) prints a help message redirecting users to `--headless` or the plugin settings tab. All TUI classes, import paths, and the `textual` optional dependency are purged. Documentation updated to reflect headless-only setup. `headless_setup()` and all shared utilities preserved intact.
**Depends on**: Nothing (standalone removal; no dependency on PATH or LEGACY phases)
**Requirements**: DEPR-01, DEPR-02, DEPR-03
**Success Criteria** (what must be TRUE):
  1. Running `paperforge setup` (bare, without `--headless`) prints a clean help message redirecting to `paperforge setup --headless` or the Obsidian plugin settings tab — no `NameError` crash, no TUI launch attempt
  2. `setup_wizard.py` contains zero Textual-related imports or classes — `WelcomeStep`, `DirOverviewStep`, `VaultStep`, `PlatformStep`, `DeployStep`, `DoneStep`, `SetupWizardApp`, `ContentSwitcher`, `StepScreen`, and all `from textual` import paths removed; verified by `rg "from textual" setup_wizard.py` returning no hits
  3. All three documentation files (`docs/setup-guide.md`, `docs/INSTALLATION.md`, `README.md`) reference only `paperforge setup --headless` — no bare `paperforge setup` without `--headless` flag
  4. Post-install instruction text and headless completion message describe headless-only workflow; `--non-interactive` CLI option removed; `textual` removed from project optional dependencies
  5. `headless_setup()`, shared utilities (`EnvChecker`, `AGENT_CONFIGS`, `_copy_file_incremental`, `_merge_env_incremental`) preserved and fully functional — zero behavior change for the headless code path
**Plans**: 2 plans
- [ ] `48-001-PLAN.md` — TUI code removal (DEPR-01, DEPR-03): remove textual imports/classes from setup_wizard.py, replace main() with help message, update cli.py help text, remove textual from pyproject.toml
- [ ] `48-002-PLAN.md` — Documentation updates (DEPR-02): update setup-guide.md and INSTALLATION.md for headless-only workflow

### Phase 49: Module Hardening
**Goal**: New modules built during v1.6-v1.8 (discussion.py, asset_state.py, main.js) have production-grade safety guards: file locking prevents concurrent write corruption, markdown special characters are escaped, timestamps use UTC, API keys pass via environment not CLI args, DOM rendering avoids XSS vectors, and empty-state outputs are safe JSON.
**Depends on**: Phase 47 (discussion.py docstring fixes share file context with LEGACY-07)
**Requirements**: HARDEN-01, HARDEN-02, HARDEN-03, HARDEN-04, HARDEN-05, HARDEN-06, HARDEN-07
**Success Criteria** (what must be TRUE):
  1. Two concurrent `/pf-paper` calls for the same paper do not corrupt `discussion.json` or `discussion.md` — file locking prevents interleaved write operations
  2. Markdown special characters (`*`, `#`, `[`, `_`, `` ` ``) in QA question/answer fields are escaped before writing to `discussion.md` — no broken formatting when rendered in Obsidian
  3. All timestamps in `discussion.json` use UTC (`datetime.now(timezone.utc)`) — no CST/UTC+8 hardcoded offset; verified by inspecting a newly created discussion session timestamp
  4. Obsidian plugin spawns OCR subprocess with `PADDLEOCR_API_TOKEN` in environment variable (not command-line argument) — API key not visible in process list via Task Manager
  5. Plugin directory tree renders via `createEl()` DOM API (not `innerHTML` assignment) — no XSS vector from user-configured directory names containing HTML/script tags
  6. `paperforge status --json` returns `lifecycle_level_counts`, `health_aggregate`, and `maturity_distribution` as empty dicts `{}` (not `null`) when no canonical index exists — downstream JSON parsers do not crash on field access
**Plans**: 3 plans

Plans:
- [ ] `49-001-PLAN.md` — discussion.py hardening: UTC timestamps (HARDEN-03), markdown escaping (HARDEN-02), file locking (HARDEN-01)
- [ ] `49-002-PLAN.md` — main.js hardening: API key via env var (HARDEN-04), createEl() not innerHTML (HARDEN-05)
- [ ] `49-003-PLAN.md` — asset_state.py + status.py hardening: reorder next_step checks (HARDEN-06), empty dicts not null (HARDEN-07)
**UI hint**: yes

### Phase 50: Repair Blind Spots
**Goal**: Repair worker three-way divergence detection covers all 6 divergence types (was missing the `ocr_status: pending` vs `meta done/failed` case). `--fix` mode handles every detected condition or produces explicit warnings for unhandled types. Silent exception swallowing replaced with logged warnings. Dead code removed.
**Depends on**: Phase 49 (repair.py shares logging patterns with discussion.py hardening)
**Requirements**: REPAIR-01, REPAIR-02, REPAIR-03, REPAIR-04
**Success Criteria** (what must be TRUE):
  1. `paperforge repair` detects condition 4 divergence: `ocr_status: pending` in formal note frontmatter vs `done`/`failed` in `meta.json` — output includes these findings (previously silently skipped)
  2. `paperforge repair --fix` handles all 6 detected divergence types — no silently skipped conditions; any unhandled type produces an explicit `[WARNING]` line in console output
  3. `paperforge repair --fix` logs (rather than silently ignores) index write failures during fix operations — `logger.warning()` calls replace bare `except Exception: pass` blocks
  4. Dead `load_domain_config` call and unused dict comprehension removed from `repair.py:196` — no unreachable code or unused imports
**Plans**: 1 plan

Plans:
- [x] 50-001-PLAN.md — All 4 REPAIR fixes: dead code removal, condition 4 detection, --fix mode coverage, silent exception logging

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 31. Bug Fixes | v1.8 | — | Complete | 2026-05-07 |
| 32. Deep-Reading Mode Detection | v1.8 | — | Complete | 2026-05-07 |
| 33. Deep-Reading Dashboard Rendering | v1.8 | — | Complete | 2026-05-07 |
| 34. Jump to Deep Reading Button | v1.8 | 1/1 | Complete | 2026-05-06 |
| 35. AI Discussion Recorder | v1.8 | 1/1 | Complete | 2026-05-06 |
| 36. Integration Verification | v1.8 | — | Complete | 2026-05-07 |
| 37. Frontmatter Rationalization | v1.9 | 1/1 | Complete | 2026-05-07 |
| 38. Workspace Stabilization | v1.9 | 1/1 | Complete | 2026-05-07 |
| 39. Base View Fix | v1.9 | — | Complete | 2026-05-07 |
| 40. Library-Record Deprecation | v1.9 | — | Complete | 2026-05-07 |
| 41. Plugin Dashboard Sync | v1.9 | — | Complete | 2026-05-07 |
| 42. Core Pipeline Fix | v1.10 | — | Complete | 2026-05-07 |
| 43. Repair & Directory Defaults | v1.10 | — | Complete | 2026-05-07 |
| 44. Documentation Update | v1.10 | — | Complete | 2026-05-07 |
| 45. Validation & Release Gate | v1.10 | — | Complete | 2026-05-07 |
| 46. Index Path Resolution | v1.11 | 2/2 | Complete | 2026-05-07 |
| 47. Library-Records Deprecation Cleanup | v1.11 | 1/2 | In Progress|  |
| 48. Textual TUI Removal | v1.11 | 3/2 | Complete   | 2026-05-07 |
| 49. Module Hardening | v1.11 | 1/3 | In Progress|  |
| 50. Repair Blind Spots | v1.11 | 1/1 | Complete   | 2026-05-07 |

---
*Roadmap updated: 2026-05-07 — v1.11 milestone phases created*
