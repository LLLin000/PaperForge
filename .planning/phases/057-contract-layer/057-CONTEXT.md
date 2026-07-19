# Phase 57: Contract Layer - Context

**Gathered:** 2026-05-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Stable JSON contracts (PFResult/PFError dataclasses, ErrorCode enum) that CLI commands produce and the plugin consumes — defining the machine-readable API surface consumed by SYNC, STAT, and SETP phases. Specifically:

1. `paperforge/core/result.py` — PFResult and PFError dataclasses with JSON round-trip serialization
2. `paperforge/core/errors.py` — ErrorCode enum centralizing all error codes
3. CLI commands (`status --json`, `doctor --json`, `sync --json`, `ocr --diagnose --json`) wrapped in PFResult format
4. `dashboard --json` contract with stats and permissions for plugin consumption
5. Plugin reads dashboard via CLI; fallback to index reading during transition
</domain>

<decisions>
## Implementation Decisions

### PFResult Contract Shape
- Top-level fields: `{ok, command, version, data, error}` following Google JSON Style Guide
- Version field: semver string from `__version__` (e.g., `"1.4.17rc3"`)
- Error shape: `{"code":"ERR_CODE","message":"Human text","details":{}}` — machine code + human message + optional payload
- `ok` field: `false` only when `error` is set; `true` when `data` has partial results + `warnings` sub-field

### ErrorCode Enum
- Naming convention: `SCREAMING_SNAKE_CASE` (Python enum standard)
- Initial codes: `PYTHON_NOT_FOUND`, `VERSION_MISMATCH`, `BBT_EXPORT_NOT_FOUND`, `OCR_TOKEN_MISSING`, `SYNC_FAILED`, `VALIDATION_ERROR`, `INTERNAL_ERROR`
- `ErrorCode.UNKNOWN` fallback catch-all required
- Validation errors: single `VALIDATION_ERROR` with `details.field` for field-level granularity

### Dashboard Contract
- Stats: `papers` (total count), `pdf_health` (healthy/broken/missing), `ocr_health` (pending/done/failed), `domain_counts` (dict of domain -> count)
- Permissions: `can_sync` (BBT exports exist), `can_ocr` (PaddleOCR configured), `can_copy_context` (system_dir writable)
- Version: from PFResult envelope (not duplicated in data)
- Transition: Fallback to direct `formal-library.json` reading allowed; removed after 2 release cycles of stable PFResult

### Implementation Structure
- PFResult/PFError in `paperforge/core/result.py`
- ErrorCode in `paperforge/core/errors.py`
- CLI migration: wrap existing JSON output in PFResult envelope first (data field retains old shape), then refactor per-command
- Testing: round-trip unit tests for PFResult serialization + CLI contract tests asserting shape

### the agent's Discretion
- Exact ErrorCode member names and descriptions (beyond the agreed categories)
- ErrorCode string values for serialization
- Dashboard field naming details in data payload
- CLI argument parsing for `--json` flag (follow existing patterns)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `paperforge/worker/status.py:973-998` — existing `--json` output as flat dict (wrapping target)
- `paperforge/commands/status.py` — thin CLI dispatch layer
- `paperforge/commands/ocr.py` — `_diagnose()` and `run()` patterns
- `paperforge/worker/sync.py` — sync worker (JSON output pattern TBD)
- `paperforge/worker/status.py:206` — existing dependency check list with `"import":"yaml"` entries

### Established Patterns
- CLI commands in `paperforge/commands/` with `run(args) -> int` signature
- Workers in `paperforge/worker/` with `run_status(vault, verbose, json_output)` pattern
- `json_output` flag passed to workers for format control
- `import json as _json` in worker code for JSON serialization
- Plugin reads from `formal-library.json` directly (transition away)

### Integration Points
- All `--json` output paths need to be wrapped in PFResult
- Plugin `main.js` reads dashboard data — needs PFResult-aware parsing
- `paperforge/commands/` dispatch layer — where JSON output formatting should be centralized
- `paperforge/core/` — new module location for contract types
- CLI tests at `tests/cli/` — contract verification tests

</code_context>

<specifics>
## Specific Ideas

### Prior Decision from REQUIREMENTS.md
- Dual JSON output during contract transition: old format + new PFResult side-by-side until 2 release cycles of stability
- Plugin keeps fallback to direct index reading during PFResult transition — removed after 2 stable release cycles

### Phase 56 Dependency
- Phase 57 depends on Phase 56 (Stop the Bleeding) — version sync must be stable before contract layer
- Phase 56 created `scripts/check_version_sync.py` — version is now read from `__version__` consistently

</specifics>

<deferred>
## Deferred Ideas

- ErrorCode auto-generation from field_registry.yaml (Phase 57 will) — deferred to Phase 59
- Full JSON schema generation for PFResult (e.g., JSON Schema for external consumers) — out of scope for this phase
- Plugin PFResult parsing utilities (separate phase: plugin contract consumption)

</deferred>
