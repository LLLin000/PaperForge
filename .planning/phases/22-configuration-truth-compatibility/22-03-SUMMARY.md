---
phase: 22-configuration-truth-compatibility
plan: "03"
subsystem: config
tags:
  - config
  - paperforge.json
  - vault_config
  - schema_version
  - migration
  - doctor

requires:
  - phase: 22-configuration-truth-compatibility
    provides: CONFIG_PATH_KEYS constant, migrate_paperforge_json(), get_paperforge_schema_version()
provides:
  - Clean setup wizard output (vault_config-only paperforge.json with schema_version)
  - Doctor migration detection (stale top-level keys, backup path, schema_version)
  - Config source tracing (load_vault_config trace_sources parameter)
affects:
  - 23-canonical-index (needs clean config format)
  - 24-lifecycle-state (needs config source tracing)
  - 25-health-diagnostics (needs doctor migration awareness)

tech-stack:
  added: []
  patterns:
    - "Config source tracing pattern: trace_sources=False returns dict, True returns (config, trace) tuple"
    - "Doctor pattern: add_check(category, status, message, fix) used for new Config Migration section"

key-files:
  created: []
  modified:
    - paperforge/setup_wizard.py - Clean vault_config-only write block with schema_version
    - paperforge/worker/status.py - Doctor Config Migration detection and schema_version display
    - paperforge/config.py - Trace sources parameter and tracing logic

key-decisions:
  - "Clean dict replace replaces existing_config.update() to avoid accumulating stale top-level keys"
  - "trace_sources parameter defaulting to False for full backward compatibility"
  - "Doctor gracefully handles missing paperforge.json with info-level diagnostic"

requirements-completed:
  - CONF-02
  - CONF-03

duration: 8min
completed: 2026-05-03
---

# Phase 22 Plan 03: Setup Doctor Migration & Config Source Tracing Summary

**Setup wizard writes canonical vault_config-only paperforge.json with schema_version, doctor detects stale legacy config with migration guidance, and load_vault_config supports optional config source tracing for CONF-03 runtime inspection.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-03T15:02:24Z
- **Completed:** 2026-05-03T15:11:13Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Setup wizard now writes only `vault_config` block for path keys (no duplicate top-level `system_dir`, `resources_dir`, etc.), includes `schema_version: "2"`, and uses a clean dict instead of `existing_config.update()` to prevent stale key accumulation
- `paperforge doctor` gains a "Config Migration" section that detects stale top-level path keys, reports migration status with backup path hints, and displays current `schema_version`
- `load_vault_config()` supports optional `trace_sources=True` parameter returning a `(config, trace)` tuple showing which source (default/vault_config/top_level/env/override) resolved each config key

## Task Commits

Each task was committed atomically:

1. **Task 1: Setup wizard writes clean vault_config-only paperforge.json** - `d0b050c` (feat)
2. **Task 2: Extend doctor to detect stale top-level config** - `6f91f73` (feat)
3. **Task 3: Add config source tracing to load_vault_config** - `f5db363` (feat)

## Files Created/Modified

- `paperforge/setup_wizard.py` - Replaced `existing_config.update()` with clean dict; removed top-level path keys (system_dir, resources_dir, literature_dir, control_dir, base_dir); added `schema_version: "2"`; preserved non-path top-level keys
- `paperforge/worker/status.py` - Extended imports to include `read_paperforge_json`, `CONFIG_PATH_KEYS`, `get_paperforge_schema_version`; added Config Migration check block detecting stale top-level keys, showing backup paths, and displaying schema_version
- `paperforge/config.py` - Added `trace_sources: bool = False` parameter to `load_vault_config()`; added trace dict tracking source ("vault_config", "top_level", "env", "override") for each key; updated docstring; conditional return: `(config, trace)` when tracing, `config` otherwise

## Decisions Made

- Used explicit dict construction instead of `existing_config.update()` to prevent stale top-level key accumulation across setup runs
- `trace_sources` defaults to `False` for full backward compatibility with all existing callers (CLI, sync, status, doctor)
- Doctor gracefully handles missing `paperforge.json` with info-level diagnostic (not fail) to support fresh installs

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Clean config format (vault_config-only, schema_version: 2) ready for Phase 23 canonical index and Phase 24 lifecycle state
- Doctor migration detection ready for brownfield vault health diagnostics in Phase 25
- Config source tracing ready for debugging and CONF-03 compliance checks

## Self-Check: PASSED

All 3 source files and SUMMARY.md confirmed on disk. All 3 commits verified in git log.

---
*Phase: 22-configuration-truth-compatibility*
*Completed: 2026-05-03*
