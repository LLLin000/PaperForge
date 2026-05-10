# Phase 46: Index Path Resolution - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

All 5 workspace-path fields in the canonical index (`paper_root`, `main_note_path`, `fulltext_path`, `deep_reading_path`, `ai_path`) use config-resolved `literature_dir` instead of hardcoded `"Literature/"`. All 11 downstream consumers resolve correct paths. Config env var typo and migration gaps fixed.

Requirements: PATH-01 through PATH-06.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Known code context:
- `asset_index.py:334-338` — 5 hardcoded `"Literature/"` strings in workspace-path dict
- `config.py:65` — env var key typo `PAPERFORGERATURE_DIR` (missing `LI`)
- `config.py:358-364` — `CONFIG_PATH_KEYS` migration tuple missing `skill_dir` and `command_dir`
- `base_views.py:154` — `${LIBRARY_RECORDS}` placeholder
- `discussion.py:266` — unnecessary Windows path `replace("/","\\")`

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `paperforge/config.py` — `DEFAULT_CONFIG` with `literature_dir: "Literature"` and `load_vault_config()` that resolves config values
- `paperforge/worker/asset_index.py` — `_build_entry()` function (line 290+) that constructs the index entry dict
- `paperforge/worker/_utils.py` — shared `pipeline_paths()` utility for path resolution

### Established Patterns
- Config keys resolved via `load_vault_config()` with env var override support
- Path construction uses `Path` objects with forward-slash normalization

### Integration Points
- 5 index fields referenced by 11 consumers: plugin dashboard, context command, discussion.py, ld_deep.py, status.py, repair.py, sync.py

</code_context>

<specifics>
No specific requirements — infrastructure phase.

</specifics>

<deferred>
None

</deferred>
