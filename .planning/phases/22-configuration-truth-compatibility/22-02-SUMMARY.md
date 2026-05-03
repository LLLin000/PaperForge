---
phase: 22-configuration-truth-compatibility
plan: "02"
subsystem: plugin, config
tags:
  - main.js
  - paperforge.json
  - Obsidian
  - plugin
  - DEFAULT_SETTINGS
  - vault_config

# Dependency graph
requires:
  - phase: 22-01
    provides: Python config migration (auto-migrates top-level keys to vault_config block)
provides:
  - Plugin reads path configuration from canonical paperforge.json (not from DEFAULT_SETTINGS or data.json)
  - Plugin Settings tab displays path values from paperforge.json
  - Plugin data.json no longer stores path directory fields
  - savePaperforgeJson() writes config changes to paperforge.json vault_config block
  - Fresh vaults without paperforge.json do not crash plugin (graceful fallback to Python defaults)
affects:
  - 22-03 (settings write-back)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Single source of truth: plugin path config sourced exclusively from paperforge.json
    - Thin plugin shell: plugin reads/writes Python-owned config file, no independent path defaults
    - Defensive key filtering: saveSettings() only persists keys that exist in DEFAULT_SETTINGS

key-files:
  created: []
  modified:
    - paperforge/plugin/main.js - Refactored DEFAULT_SETTINGS, added readPaperforgeJson()/savePaperforgeJson(), updated loadSettings/saveSettings, refactored PaperForgeSettingTab

key-decisions:
  - "Added paddleocr_api_key and zotero_data_dir to DEFAULT_SETTINGS (plan had a bug: the proposed DEFAULT_SETTINGS omitted them, which would cause data loss when saveSettings() filters to only DEFAULT_SETTINGS keys)"
  - "Plugin data.json cleaned on first load by calling saveSettings() which now filters to non-path DEFAULT_SETTINGS keys only"

patterns-established:
  - "path-config-from-paperforge: all path directory values (system_dir, resources_dir, literature_dir, control_dir, base_dir) read from paperforge.json at load time, not from plugin data.json"
  - "non-path-persistence: saveSettings() filters to DEFAULT_SETTINGS keys only, automatically excluding path fields"
  - "paperforge-json-write: savePaperforgeJson() writes to vault_config block, removes stale top-level keys, and preserves all non-path config"

requirements-completed:
  - CONF-01
  - CONF-04

# Metrics
duration: 6 min
completed: 2026-05-03
---

# Phase 22 Plan 02: Plugin Reads paperforge.json as Path Config Source of Truth — Summary

**Refactored Obsidian plugin to read path configuration from `paperforge.json` (vault_config block), eliminating the second runtime truth problem where plugin DEFAULT_SETTINGS had wrong defaults (System/Resources/Notes/Index_Cards/Base instead of Python's 99_System/03_Resources/Literature/LiteratureControl/05_Bases).**

## Performance

- **Duration:** 6 min
- **Started:** 2026-05-03T14:51:57Z
- **Completed:** 2026-05-03T14:57:52Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

- Removed all 5 path directory keys from DEFAULT_SETTINGS (system_dir, resources_dir, literature_dir, control_dir, base_dir), keeping only non-path settings
- Added `readPaperforgeJson()` method reading from paperforge.json vault_config block with Python DEFAULT_CONFIG fallback for fresh vaults
- Refactored `loadSettings()` to overwrite path fields from paperforge.json after merging data.json
- Refactored `saveSettings()` to filter persisted keys to DEFAULT_SETTINGS only (path fields automatically excluded)
- Added `savePaperforgeJson()` method writing path config back to paperforge.json vault_config block, removing stale top-level keys
- Refactored `PaperForgeSettingTab` to display path values from `_pfConfig` (paperforge.json source) instead of plugin.settings
- Added `saveSettings()` cleanup call in `onload()` to purge stale path fields from existing plugin data.json

## Task Commits

Each task was committed atomically:

1. **Task 1: Add readPaperforgeJson() and clean DEFAULT_SETTINGS** - `00ae8e8` (feat)
2. **Task 2: Refactor SettingsTab to read from paperforge.json** - `cda3cff` (feat)
3. **Task 3: Add savePaperforgeJson() and data.json cleanup** - `36de493` (feat)

## Files Created/Modified

- `paperforge/plugin/main.js` - Complete refactor of config truth architecture:
  - `DEFAULT_SETTINGS` (line 145): Removed 5 path keys, kept 7 non-path keys
  - `readPaperforgeJson()` (line 1043): Reads paperforge.json vault_config block with Python default fallback
  - `savePaperforgeJson()` (line 1083): Writes path config to paperforge.json vault_config block
  - `loadSettings()` (line 1144): Overwrites path fields from readPaperforgeJson()
  - `saveSettings()` (line 1155): Filters to DEFAULT_SETTINGS keys only
  - `onload()` (line 988): Calls saveSettings() to clean stale data.json path keys
  - `PaperForgeSettingTab` (line 443): Added _pfConfig cache, _refreshPfConfig(), Config Summary reads from _pfConfig

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added paddleocr_api_key and zotero_data_dir to DEFAULT_SETTINGS**
- **Found during:** Task 1 (DEFAULT_SETTINGS replacement)
- **Issue:** The plan's proposed DEFAULT_SETTINGS omitted `paddleocr_api_key` and `zotero_data_dir`. The refactored `saveSettings()` filters persisted keys to only those in `DEFAULT_SETTINGS`, so any key missing from DEFAULT_SETTINGS would be silently dropped on save — causing permanent data loss of user API keys and Zotero data paths.
- **Fix:** Added `paddleocr_api_key: ''` and `zotero_data_dir: ''` to DEFAULT_SETTINGS. These are non-path user settings that must survive the saveSettings() filter.
- **Files modified:** paperforge/plugin/main.js (DEFAULT_SETTINGS block)
- **Verification:** Verification script confirms both keys are present in DEFAULT_SETTINGS and excluded from path-key removal checks
- **Committed in:** `00ae8e8` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Critical data-loss bug prevented — without this fix, existing user paddleocr_api_key and zotero_data_dir values would be permanently deleted from plugin data.json on first saveSettings() call after the refactor.

## Issues Encountered

None — plan executed cleanly with the one deviation documented above.

## Next Phase Readiness

Ready for 22-03 (settings write-back). The plugin now:
- Reads path config exclusively from paperforge.json
- Displays paperforge.json values in Settings tab
- Writes path changes to paperforge.json via savePaperforgeJson()
- Gracefully falls back to Python defaults when file doesn't exist
- Cleans stale path fields from plugin data.json on first load

---

*Phase: 22-configuration-truth-compatibility*
*Completed: 2026-05-03*
