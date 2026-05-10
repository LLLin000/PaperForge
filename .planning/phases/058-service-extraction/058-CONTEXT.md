# Phase 58: Service Extraction - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — refactoring)

<domain>
## Phase Boundary

Monolithic sync.py (1647 lines) decomposed into focused modules:
- `paperforge/adapters/bbt.py` — BBT JSON parsing (load_export_rows, _normalize_attachment_path, _identify_main_pdf, extract_authors, resolve_item_collection_paths)
- `paperforge/adapters/zotero_paths.py` — path resolution (obsidian_wikilink_for_pdf, absolutize_vault_path, obsidian_wikilink_for_path)
- `paperforge/adapters/obsidian_frontmatter.py` — frontmatter read/write/update using YAML parser replacing regex
- `paperforge/services/sync_service.py` — SyncService class wrapping adapters
- `paperforge/worker/sync.py` — reduced to thin CLI dispatch with no business logic beyond orchestration

Each extracted module independently testable with passing unit tests. All existing sync behavior preserved (zero regressions).
</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure/refactoring phase. Refer to ROADMAP phase goal, success criteria, and existing codebase conventions.

### Prior Decisions
- Incremental extraction from sync.py — adapters first, then SyncService, keeping sync.py as thin shell (from REQUIREMENTS.md)
- No full rewrite of sync.py from scratch
- PFResult/PFError contracts available from Phase 57 (core/result.py, core/errors.py)
</decisions>

<code_context>
## Existing Code Insights

### sync.py Structure (1647 lines)
The file has these logical groups:
- Frontmatter helpers (lines 36-63): `_read_frontmatter_bool_from_text`, `_legacy_control_flags`
- Export parsing (lines 66-382): `load_export_inventory`, `_normalize_attachment_path`, `_identify_main_pdf`, `extract_authors`, `resolve_item_collection_paths`, `load_export_rows`, `collection_fields`
- Path resolution (lines 195-251): `obsidian_wikilink_for_pdf`, `absolutize_vault_path`, `obsidian_wikilink_for_path`
- Candidate/note generation (lines 384-735): `compute_final_collection`, `candidate_markdown`, `generate_review`, `_add_missing_frontmatter_fields`, `update_frontmatter_field`, `load_control_actions`
- Main entry (lines 739+): `run_selection_sync` (primary orchestration entry point)
- Also has `_utils.py` with shared utilities (read_json, write_json, yaml_quote, etc.) — not being extracted

### Imports Needed
- Each adapter module will import from `paperforge.worker._utils` for shared utilities
- SyncService will import from adapters
- sync.py will import SyncService and dispatch to it

### Existing Patterns
- YAML frontmatter helpers in `_utils.py`: `yaml_quote()`, `yaml_block()`, `yaml_list()`
- `pipeline_paths()` provides the paths dict used throughout sync.py
- PFResult wrapping available from Phase 57 for json_output

### Reusable Assets
- `_utils.py` shared utilities (read_json, write_json, yaml operations, slugify) — already extracted in v1.4
- Phase 57 JSON contract types available

</code_context>

<specifics>
## Specific Ideas

### Extraction Order (Recommended)
1. `adapters/zotero_paths.py` — self-contained, no dependencies on other sync.py functions
2. `adapters/bbt.py` — depends on paths but self-contained for BBT parsing
3. `adapters/obsidian_frontmatter.py` — frontmatter operations, replace regex with YAML parser
4. `services/sync_service.py` — wraps adapters
5. Thin sync.py — orchestrates via SyncService

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.
</deferred>
