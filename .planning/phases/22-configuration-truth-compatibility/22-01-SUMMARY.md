---
phase: 22-configuration-truth-compatibility
plan: 01
subsystem: config
tags: [python, config, migration, schema-version, paperforge-json]
requires:
  - phase: 21-one-click-install-and-polished-ux
    provides: Plugin setup flow that writes vault_config block
provides:
  - schema_version field in DEFAULT_CONFIG and paperforge.json
  - get_paperforge_schema_version() public API
  - migrate_paperforge_json() migration engine
  - Legacy top-level keys migrated to vault_config with .bak backup
  - sync command auto-triggers migration at startup
affects:
  - Phase 22-02 (Plugin config truth: read paperforge.json, remove DEFAULT_SETTINGS)
  - Phase 22-03 (Setup wizard vault_config-only output + doctor migration detection)
tech-stack:
  added: shutil (stdlib, for backup copy)
  patterns: Gap-fill migration (top-level fills keys missing from vault_config, never overrides existing vault_config values)
key-files:
  created: []
  modified:
    - paperforge/config.py
    - paperforge/commands/sync.py
    - tests/test_config.py
key-decisions:
  - "schema_version is metadata, excluded from load_vault_config() path config output; use get_paperforge_schema_version() instead"
  - "Migration uses gap-fill logic: top-level keys only fill gaps where vault_config misses a key, never override existing vault_config values"
  - "Backup file extension: .bak, created only on first migration (subsequent runs are no-op)"
  - "schema_version '2' marks vault_config-canonical format; absence/1 means legacy top-level format"
patterns-established:
  - "Config migration: detect top-level path keys -> merge gaps into vault_config -> backup original -> set schema_version -> write normalized output"
  - "Verify by Python -c one-liners for fast CI feedback (pytest for deeper contract tests)"
requirements-completed:
  - CONF-01
  - CONF-02
duration: 4 min
completed: 2026-05-03
---

# Phase 22 Plan 01: Python Config Migration Summary

**schema_version marker, top-level-to-vault_config migration engine, and auto-trigger in sync command**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-03T14:38:00Z
- **Completed:** 2026-05-03T14:42:18Z
- **Tasks:** 3 (2 TDD with RED/GREEN, 1 auto)
- **Files modified:** 3

## Accomplishments

- Added `schema_version: "2"` to `DEFAULT_CONFIG` as the canonical schema marker
- Added `get_paperforge_schema_version(vault)` public function returning int, defaulting to 1 for legacy files
- Excluded `schema_version` from `load_vault_config()` output (it is metadata, not a path config key)
- Built `migrate_paperforge_json(vault)` with gap-fill logic: legacy top-level path keys are merged into `vault_config` (only where vault_config misses a key), backup created as `paperforge.json.bak`, non-path keys preserved, `schema_version` set to `"2"`
- Wired migration into `paperforge sync` -- called automatically after vault resolution, before any sync operations, with info logging and verbose console output
- 10 new pytest tests covering schema_version resolution, migration behavior, idempotency, non-path key survival, and vault_config creation

## Task Commits

Each task was committed atomically:

1. **Task 1 (TDD RED): schema_version tests** - `4c76fb1` (test)
2. **Task 1 (TDD GREEN): schema_version implementation** - `e085070` (feat)
3. **Task 2 (TDD RED): migration tests** - `8067baf` (test)
4. **Task 2 (TDD GREEN): migration engine** - `e2d3f5a` (feat)
5. **Task 3 (auto): sync wiring** - `37ce6ec` (feat)

**Plan metadata:** pending metadata commit

## Files Created/Modified

- `paperforge/config.py` - Added `get_paperforge_schema_version()`, `migrate_paperforge_json()`, `CONFIG_PATH_KEYS`, `schema_version` in `DEFAULT_CONFIG`, `import shutil`, `config.pop("schema_version", None)` in `load_vault_config()`
- `paperforge/commands/sync.py` - Added import and call for `migrate_paperforge_json()` in `run()` after vault resolution
- `tests/test_config.py` - 10 new tests for schema_version resolution and migration engine

## Decisions Made

- `schema_version` is metadata excluded from `load_vault_config()` path config output
- Migration uses gap-fill: top-level values only populate keys missing from `vault_config`, never override existing values
- Backup file uses `.bak` suffix, created only on first migration
- `schema_version: "2"` = canonical (`vault_config`-only) format; absence or `"1"` = legacy top-level format

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan's Task 2 verify command has assertion inconsistent with behavior spec**
- **Found during:** Task 2 verification
- **Issue:** The plan's automated verify command (`python -c "..."` in Task 2 `<verify>` section) expects top-level `system_dir: "OldSystem"` to override existing `vault_config.system_dir: "99_System"`. This contradicts the behavior spec which states "top-level fills gaps where vault_config misses a key" — there is no gap since vault_config already has the key.
- **Fix:** No code change needed. My implementation correctly follows the behavior spec (gap-fill only). The plan's verify command has a wrong expectation for the case where both top-level and vault_config have the same key.
- **Files modified:** None (plan documentation inconsistency, not a code issue)
- **Verification:** pytest tests pass with correct gap-fill behavior; `load_vault_config()` top-level override logic (step 3 in merge chain) is a separate concern that applies at runtime, not during migration
- **Committed in:** N/A (not a code fix)

---

**Total deviations:** 1 auto-fixed (1 plan inconsistency, no code changes needed)
**Impact on plan:** None. All code implements the spec correctly. All 42 tests pass.

## Issues Encountered

None.

## Next Phase Readiness

- Python config layer is ready: `schema_version` marker + migration engine + sync hook
- Ready for Phase 22-02 (Plugin config truth: read paperforge.json, remove DEFAULT_SETTINGS path fields)
- Ready for Phase 22-03 (Setup wizard vault_config-only output + doctor migration detection + config source tracing)

---
*Phase: 22-configuration-truth-compatibility*
*Completed: 2026-05-03*

## Self-Check: PASSED

- All 3 source files exist: `paperforge/config.py`, `paperforge/commands/sync.py`, `tests/test_config.py`
- All 5 task commits verified in git log: `4c76fb1`, `e085070`, `8067baf`, `e2d3f5a`, `37ce6ec`
- SUMMARY.md created at expected path
- 42 tests pass (32 config + 10 CLI/worker dispatch)
