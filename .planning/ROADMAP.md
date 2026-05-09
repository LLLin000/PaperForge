# Roadmap: PaperForge v2.1 — Contract-Driven Architecture & Engineering Hardening

## Overview

v2.1 transforms PaperForge from feature-stacked monoliths into a contract-driven system. Each phase builds on the last: quick consistency fixes unblock the work (Phase 56), stable JSON contracts define the machine-readable API surface (Phase 57), sync.py decomposes into testable adapters and a service layer (Phase 58), the state machine formalizes with enums and a field registry (Phase 59), and setup_wizard modularizes into focused classes with per-step JSON output (Phase 60). Every requirement maps to exactly one phase.

## Phases

- [ ] **Phase 56: Stop the Bleeding** — Quick consistency fixes: version sync, PyYAML, README/install unification, plugin version pinning
- [ ] **Phase 57: Contract Layer** — PFResult/PFError dataclasses, ErrorCode enum, CLI --json contracts (status/doctor/sync/ocr/dashboard) [Planned, 4 plans]
- [ ] **Phase 58: Service Extraction** — Decompose sync.py into adapters (bbt/zotero_paths/obsidian_frontmatter) and SyncService
- [ ] **Phase 59: State Machine & Field Registry** — PdfStatus/OcrStatus/Lifecycle enums, ALLOWED_TRANSITIONS, field_registry.yaml, doctor field checks
- [ ] **Phase 60: Setup Modularization** — SetupPlan/Checker/RuntimeInstaller/VaultInitializer/AgentInstaller/ConfigWriter classes, setup --headless --json

## Phase Details

### Phase 56: Stop the Bleeding
**Goal**: Quick consistency fixes that unblock all subsequent phases — version declarations synchronized, dependency declarations resolved, install documentation unified, and plugin runtime version pinned.
**Depends on**: Nothing (v2.0 complete)
**Requirements**: BLEED-01, BLEED-02, BLEED-03, BLEED-04
**Success Criteria** (what must be TRUE):
  1. `scripts/check_version_sync.py` passes as a CI gate — all 6+ version declarations (__init__.py, manifest.json, versions.json, pyproject.toml, plugin manifest, docs) return consistent
  2. PyYAML dependency is resolved — either added to pyproject.toml as explicit dependency, or the yaml module existence check is removed from `paperforge doctor` (single source of truth — no "optional dependency" ambiguity)
  3. README, INSTALLATION, and setup-guide present a single unified primary install path — no conflicting recommendations across the three documents
  4. Plugin runtime `pip install paperforge` pins to the plugin manifest version — no version drift possible between the Obsidian plugin and the Python package
**Plans**: 2 plans

Plans:
- [ ] 056-01-PLAN.md — Version sync CI gate script + PyYAML doctor hardening (BLEED-01, BLEED-02)
- [ ] 056-02-PLAN.md — Install doc unification + plugin version pinning (BLEED-03, BLEED-04)

### Phase 57: Contract Layer
**Goal**: Stable JSON contracts (PFResult/PFError dataclasses, ErrorCode enum) that CLI commands produce and the plugin consumes — defining the machine-readable API surface consumed by SYNC, STAT, and SETP phases.
**Depends on**: Phase 56
**Requirements**: CTRT-01, CTRT-02, CTRT-03, CTRT-04, CTRT-05, CTRT-06, CTRT-07, CTRT-08
**Success Criteria** (what must be TRUE):
  1. `PFResult` and `PFError` dataclasses are defined in `paperforge/core/result.py` with `to_json()` serialization that survives round-trip (serialize → deserialize → equal)
  2. All error codes are centralized in `ErrorCode` enum in `paperforge/core/errors.py` — no scattered string-based error codes remain in any production module
  3. `paperforge status --json`, `doctor --json`, `sync --json`, and `ocr --diagnose --json` all return PFResult-format output with consistent `{ok, command, version, data, error}` shape
  4. `paperforge dashboard --json` returns a stable UI contract with stats (papers, pdf_health, ocr_health, domain_counts) and actionable permissions (can_sync, can_ocr, can_copy_context)
  5. Plugin reads dashboard data via `paperforge dashboard --json` CLI contract; fallback to direct `formal-library.json` reading remains available during the transition period (removed after 2 release cycles of stable PFResult)
**Plans**: 4 plans
**UI hint**: yes

Plans:
- [ ] 057-01-PLAN.md — Core contract types: ErrorCode enum + PFResult/PFError dataclasses + round-trip tests (CTRT-01, CTRT-02)
- [ ] 057-02-PLAN.md — Status & doctor --json PFResult wrapping + contract tests (CTRT-03, CTRT-04)
- [ ] 057-03-PLAN.md — Sync & ocr --diagnose --json PFResult wrapping + contract tests (CTRT-05, CTRT-06)
- [ ] 057-04-PLAN.md — Dashboard command + plugin contract integration + contract tests (CTRT-07, CTRT-08)

### Phase 58: Service Extraction
**Goal**: Monolithic sync.py decomposed into focused adapters and a SyncService class — each module independently testable with its own unit tests, sync.py reduced to a thin CLI dispatch layer.
**Depends on**: Phase 57
**Requirements**: SYNC-01, SYNC-02, SYNC-03, SYNC-04, SYNC-05
**Success Criteria** (what must be TRUE):
  1. `paperforge/adapters/bbt.py` contains all BBT JSON parsing functions (`load_export_rows`, `_normalize_attachment_path`, `_identify_main_pdf`, `extract_authors`, `resolve_item_collection_paths`) — importable and testable in isolation from sync.py
  2. `paperforge/adapters/zotero_paths.py` contains all path resolution functions (`obsidian_wikilink_for_pdf`, `absolutize_vault_path`, `obsidian_wikilink_for_path`) — no path resolution logic remains in sync.py
  3. `paperforge/adapters/obsidian_frontmatter.py` contains frontmatter read/write/update operations using YAML parser (replacing regex-based parsing where possible) — importable and testable in isolation
  4. `paperforge/services/sync_service.py` exists as a `SyncService` class that wraps the decomposed adapter modules; `worker/sync.py` becomes a thin dispatch layer with no business logic beyond orchestration
  5. All extracted modules have passing unit tests covering BBT JSON variants, path formats (storage:/, absolute Windows, CJK filenames, spaces), and frontmatter edge cases — existing sync behavior preserved (no regressions)
**Plans**: TBD

### Phase 59: State Machine & Field Registry
**Goal**: Formalized state machine with explicit enums and allowed transitions, plus a field registry that `paperforge doctor` can validate against — making state changes predictable and field drift detectable.
**Depends on**: Phase 57
**Requirements**: STAT-01, STAT-02, STAT-03, STAT-04, STAT-05
**Success Criteria** (what must be TRUE):
  1. `PdfStatus`, `OcrStatus`, and `Lifecycle` enums are defined in `paperforge/core/state.py` with explicit string values — every existing state string in the codebase maps to an enum member
  2. `ALLOWED_TRANSITIONS` table defines legal state migrations; workers validate transitions before writing state changes — illegal transitions are rejected with clear, actionable error messages
  3. `paperforge/schema/field_registry.yaml` defines every field in the system (formal note frontmatter, index entries, paper-meta.json) with public/required/type/owner/description metadata — complete coverage of all field-carrying structures
  4. `paperforge doctor` checks field completeness against the registry — missing required fields produce actionable warnings with migration suggestions; unknown/invalid fields produce warnings to flag drift
  5. Edge case: fields present in data but absent from registry trigger a "drift detected" diagnostic; fields in registry but absent from data trigger "missing required field" with severity levels
**Plans**: TBD

### Phase 60: Setup Modularization
**Goal**: Monolithic setup_wizard.py decomposed into six focused classes with explicit dependencies — enabling `paperforge setup --headless --json` to return per-step status that the Obsidian plugin can render as progress.
**Depends on**: Phase 57
**Requirements**: SETP-01, SETP-02, SETP-03, SETP-04, SETP-05, SETP-06, SETP-07
**Success Criteria** (what must be TRUE):
  1. `SetupPlan`, `SetupChecker`, `RuntimeInstaller`, `VaultInitializer`, `AgentInstaller`, and `ConfigWriter` classes each exist with a single responsibility and explicit interface — no class exceeds its boundary
  2. `paperforge setup --headless --json` returns per-step status — each step has independent `{ok, error, message}` fields; the plugin UI can render step-by-step progress from the JSON output
  3. `ConfigWriter` writes `paperforge.json` atomically using tempfile + os.replace — no partial or corrupted config files possible on crash or interrupt
  4. `RuntimeInstaller` handles `pip install` with explicit version pinning (from plugin manifest), progress output via callback, and classified errors using the ErrorCode enum from Phase 57
  5. `SetupChecker` validates all preconditions (Python executable, pip availability, dependency health) before any installation step begins — failures produce classified, user-readable diagnostics
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:** 56 → 57 → 58 → 59 → 60

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 56. Stop the Bleeding | 0/2 | Ready to execute | — |
| 57. Contract Layer | 0/TBD | Not started | — |
| 58. Service Extraction | 0/TBD | Not started | — |
| 59. State Machine & Field Registry | 0/TBD | Not started | — |
| 60. Setup Modularization | 0/TBD | Not started | — |
