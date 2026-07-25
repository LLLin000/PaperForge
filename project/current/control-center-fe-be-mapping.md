# PaperForge Control Center — Frontend/Backend Mapping

> Target contract for the approved prototypes and implementation tickets. `[GAP]` marks a field or command that the current backend does not yet expose.
> Covered surfaces: `control-center-ux.html`, `setup-journey.html`, and `ocr-workspace.html`.

---

## Setup Journey

### Stage 1 — Foundation
| UI | Backend field / command |
|----|------------------------|
| "Runtime Environment" badge (Ready/Checking/Not Installed) | `probe_installation()` → `capability_state`, `reason_code` |
| Python version display | `probe_installation()` → reason_text includes Python version |
| "Continue" button | UI-only: advances to Stage 2 (`_setupStage = 2`) |

### Stage 2 — Connect Library
| UI | Backend field / command |
|----|------------------------|
| Zotero Data Directory input | `settings.zotero_data_dir` → `paperforge.json` `vault_config` |
| "Check" button | `probe_library()` with `zotero_data_dir` as input |
| Check result badge (Ready/Not Found) | `probe_library()` → `capability_state`, `reason_code` |
| **Vault Folders** | |
| System (default: `System`) | `paperforge.json` → `vault_config.system_dir` → `PAPERFORGE_SYSTEM_DIR` env |
| Literature (default: `Literature`) | `paperforge.json` → `vault_config.literature_dir` → `PAPERFORGE_LITERATURE_DIR` env |
| Resources (default: `Resources`) | `paperforge.json` → `vault_config.resources_dir` → `PAPERFORGE_RESOURCES_DIR` env |
| Bases (default: `Bases`) | `paperforge.json` → `vault_config.base_dir` → `PAPERFORGE_BASE_DIR` env |

### Stage 3 — Optional Capabilities
| UI | Backend field / command |
|----|------------------------|
| **OCR Engine** checkbox | `settings.features` — enables/disables OCR module in Control Center |
| OCR API Key input | `PADDLEOCR_API_KEY` → Obsidian SecretStorage (`paddleocr-api-key`) |
| "Test" button | Ping PaddleOCR endpoint with key → success/failure |
| **Smart Retrieval** checkbox | `settings.features` — enables/disables Smart Retrieval module |
| Smart Retrieval API Key | `VECTOR_DB_API_KEY` → Obsidian SecretStorage (`vector-db-api-key`) |
| Smart Retrieval Model | `settings.vector_db_api_model` (default: `text-embedding-3-small`) |
| Smart Retrieval API Base URL | `settings.vector_db_api_base` (default: `https://api.openai.com/v1`) |
| "Test" button | Ping embedding endpoint with key → success/failure |
| **Agent Integration** checkbox | `settings.features` — enables/disables Agent Integration module |
| Agent Platform dropdown | `settings.agent_platform` (values: `opencode`, `claude`, `codex`, `cursor`) |

### Stage 4 — Review & Begin
| UI | Backend field / command |
|----|------------------------|
| Foundation status row | `probe_installation()` → `capability_state` |
| Library status row | `probe_library()` → `capability_state` |
| Optional modules row | Derived from Stage 3 checkbox states |
| "Complete Setup" button | Writes all config to `paperforge.json` + Obsidian `data.json`, sets `_setup_complete = true` |

---

## Control Center

### Overview
| UI | Backend field / command |
|----|------------------------|
| Baseline badge + summary | `probe_installation()` + `probe_library()`; both `capability_state=ready` → baseline Ready |
| 5 module rows (01–05) | Each `probe_<module>()` → `capability_state`, `reason_code`, `updated_at` |
| Plain-language consequence | Localized from stable `reason_code`; must not expose raw backend prose |
| Key metric | Module-specific probe fields (version, paper count, backup timestamp, platform) |
| "Last checked" timestamp | Latest `probe_<module>().updated_at` |
| "Refresh Status" | Re-runs all 5 probes; never starts sync, OCR, restore, or deployment work |

### Foundation Detail
| UI | Backend field / command |
|----|------------------------|
| Badge | `probe_installation()` → six-state `capability_state` |
| PaperForge version | `probe_installation()` → envelope data |
| Runtime info (Python version, path) | `probe_installation()` → structured envelope data; `reason_text` is support-only |
| "Copy Support Diagnostic" | `buildSupportDiagnostic()` → clipboard |

### Library Detail
| UI | Backend field / command |
|----|------------------------|
| Badge | `probe_library()` → six-state `capability_state` |
| Connection summary | Localized from `probe_library().reason_code` |
| Data directory | `paperforge.json` → `zotero_data_dir` |
| Last sync | `[GAP] probe_library()` needs a structured `last_sync` timestamp |
| "Sync library" | `paperforge sync` CLI command, dispatched only from Module Detail |
| "Change" | Opens folder picker → validates → updates `zotero_data_dir` |

### OCR Settings
| UI | Backend field / command |
|----|------------------------|
| Module badge | Six-state mapping: Ready / Action Required / Checking |
| User-facing OCR state | `probe_ocr()` → `user_state` (`processed`, `update_available`, `processing`) plus `papers[]` aggregate |
| "X papers processed · current pipeline vY.Z" | `probe_ocr()` → `processed_count`, `current_pipeline_version` |
| Update notice | `probe_ocr()` → `user_state=update_available`; frontend does not infer safety from version strings |
| "Update all papers" | Shared OCR replacement pipeline for all processed papers; current CLI target is `paperforge ocr rebuild --all` |
| Confirmation modal | Backend action contract → `confirmation_required`, `affected_scope`, `preserves_sources`, `backup_supported`, `estimated_cost_available` `[GAP]` |
| Progress bar + paper name | Issue #101 normalized progress token stream |
| "Stop" button | Backend activity contract → `can_stop`; current subprocess path writes `PAPERFORGE_STOP\n` to stdin |
| "Open OCR Workspace" | Activates `paperforge-ocr-workspace` ItemView |

### Smart Retrieval Detail
| UI | Backend field / command |
|----|------------------------|
| Badge | `probe_memory()` → six-state `capability_state` |
| Consequence text | Localized from `reason_code`; explains search impact without implying paper loss |
| "Restore from Backup" | `paperforge memory restore-backup`; enable only when `[GAP] backup_available=true` |
| "Rebuild Index" | `paperforge embed build`; secondary recovery path |

### Agent Detail
| UI | Backend field / command |
|----|------------------------|
| Badge | Six-state value derived from settings plus `[GAP]` agent deployment probe |
| Platform display | `settings.agent_platform` |
| Deployment state | `[GAP]` agent context probe |
| "Configure agent integration" | Inline platform selection → validate → save `settings.agent_platform` → deploy Skills |

### Help
| UI | Backend field / command |
|----|------------------------|
| Getting started links | Navigation to Library/OCR/SmartRetrieval/Agent detail pages |
| Support Diagnostic | `buildSupportDiagnostic()` — all module states + versions |
| Release notes | Opens GitHub release page |

---

## OCR Workspace (Standalone ItemView)

| UI | Backend field / command |
|----|------------------------|
| Paper table rows | `probe_ocr()` → `papers[]` with title, authors, year, `user_state`, version, last run, page count, and health |
| Status filter | Client-side filter on `papers[].user_state` (`processed`, `update_available`, `not_processed`) |
| Version filter chips | Client-side filter on `papers[].last_pipeline_version`; values derive from returned data |
| Update row emphasis | `papers[].user_state=update_available`; frontend does not infer this from raw version comparison |
| "Select all" checkbox | Selects all rows in the current filtered result set |
| "Process Selected" | Enabled only when selected rows include `not_processed`; dispatches `paperforge ocr run --keys ...` |
| Process-selection hint | Derived from selected rows and visible result set; no backend call |
| "Update Selected" | **DISABLED** until redo backup backend ticket #99; user-facing copy says "Available after backup support lands" |
| Per-paper detail panel | |
| Title / Authors / Year | Paper frontmatter fields returned by `probe_ocr().papers[]` |
| State / Version / Last run / Pages / Health | Structured paper fields from `probe_ocr().papers[]` |
| Update explanation | `user_state=update_available`; explains that current text remains usable until updated |
| "Process" | `paperforge ocr run --keys <KEY>` for `not_processed` only |
| "View Fulltext" | Opens `ocr/<KEY>/fulltext.md` |
| "Restore Backup" | Enabled only when paper response reports `backup_available=true` `[GAP]` |
| "Update this paper" | **GATED** until #99; uses the same shared replacement pipeline after backup support lands |
| Progress bar | Issue #101 normalized progress token stream |
| "Stop" | Backend activity `can_stop`; current subprocess path writes `PAPERFORGE_STOP\n` to stdin |

---

## Key Backend Changes Needed

| # | Change | Ticket |
|---|--------|--------|
| 1 | `OCR_PIPELINE_VERSION` aggregate constant | #97 |
| 2 | Per-paper `ocr_pipeline_version` in meta.json | #97 |
| 3 | `probe_ocr()` expose `current_pipeline_version` + `papers[]` | #97 |
| 4 | `redo_papers_for_keys()` add `create_pre_rebuild_backup()` | #99 |
| 5 | Unify redo/rebuild pipeline | #97 |
| 6 | Normalized progress and activity contract | #101 |
| 7 | Structured Library `last_sync` timestamp | Unassigned |
| 8 | Smart Retrieval `backup_available` field | Unassigned |
| 9 | Agent deployment probe | Unassigned |
| 10 | Typed support diagnostic payload | Unassigned |

---

## Key Frontend Changes Needed

| # | Change | Ticket |
|---|--------|--------|
| 1 | Split `styles.css` into `src/styles/*.css` modules | #100 |
| 2 | Kami design tokens → Obsidian CSS variable mapping | #100 |
| 3 | OCR Settings 3-state UX | #96 |
| 4 | Rebuild confirmation modal with safety info | #96 |
| 5 | OCR Workspace `ItemView` registration | #95 |
| 6 | Workspace paper table with virtual scrolling | #95 |
| 7 | Workspace version filter + row highlight | #95 |
| 8 | Progress bar component (4px, kami style) | #101 |
| 9 | Full i18n pass (en + zh) | #98 |
| 10 | Bilingual QA at 768px + 1280px | #98 |
| 11 | Remove Maintenance tab, add Help tab | #100 |
| 12 | Setup Journey 4 stages with inline config | #100 |