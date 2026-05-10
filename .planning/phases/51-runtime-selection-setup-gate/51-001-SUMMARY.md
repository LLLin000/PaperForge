---
phase: 51-runtime-selection-setup-gate
plan: 001
subsystem: plugin
tags: [python, runtime, settings-ui, validation, zotero]

requires: []
provides:
  - Python interpreter visibility in plugin settings
  - Manual override with validate button and full check chain
  - Consistent interpreter usage across all subprocess call sites
  - zotero_data_dir required with multi-stage validation
  - Saved override re-validation on plugin load

affects: [Phase 53 Doctor, Phase 52 Setup Polish]

tech-stack:
  added: []
  patterns:
    - resolvePythonExecutable() returns { path, source, extraArgs } object
    - extraArgs pattern for py -3 argument propagation
    - Transient _python_path_stale flag excluded from persistence

key-files:
  modified:
    - paperforge/plugin/main.js

key-decisions:
  - "Manual python_path override is absolute source of truth when set and exists"
  - "Detection order: manual -> .paperforge-test-venv -> .venv -> venv -> py -3 -> python -> python3"
  - "extraArgs pattern for py -3 launcher (separates exe from args for execFile/spawn)"
  - "Stale override shows warning but doesn't clear the saved value"
  - "zotero_data_dir validation blocks install at Step 3 with specific error per failure mode"

requirements-completed:
  - RUNTIME-01
  - RUNTIME-02
  - RUNTIME-03
  - RUNTIME-06

duration: 16min
completed: 2026-05-08
---

# Phase 51: Runtime Selection & Setup Gate - Plan 001 Summary

**Python interpreter path visible in settings with manual override, consistent across all subprocess calls, and required zotero_data_dir with blocking validation**

## Performance

- **Duration:** 16 min
- **Started:** 2026-05-08T~10:00:00Z
- **Completed:** 2026-05-08T~10:16:00Z
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments
- Refactored `resolvePythonExecutable()` to return `{path, source, extraArgs}` with manual override as primary detection source
- Added `python_path` to `DEFAULT_SETTINGS` for storing manual override paths
- Added Python interpreter read-only row (resolved path + source label) to settings page
- Added custom path text input wired to `settings.python_path` with debounced save
- Added Validate button with full check chain: exists -> executable -> version >= 3.10 -> pip warning
- Updated all 8 subprocess call sites to use resolved interpreter with `extraArgs` propagation for `py -3`
- Eliminated all bare `'python'` spawn/exec calls (zero remaining)
- Changed `zotero_data_dir` from optional to required with multi-stage validation in wizard
- Enhanced `_validateStep3()`: non-empty -> exists -> isDirectory -> has `storage/` subdirectory
- Added `_validate()` zotero reject with `validate_zotero` i18n key
- Added reload re-validation with stale override warning via `_python_path_stale` transient flag
- Added 3 new i18n key sets (field_python_interp, field_python_custom, btn_validate) to both en/zh

## Task Commits

Each task was committed atomically:

1. **Task 1: Refactor resolvePythonExecutable + python_path settings + reload re-validation** - `4e16461` (feat)
2. **Task 2: Add Python interpreter row to settings page UI** - `931438d` (feat)
3. **Task 3: Consistent interpreter usage + zotero_data_dir required + validation** - `282035d` (feat)

## Files Modified
- `paperforge/plugin/main.js` — All runtime selection, settings, validation, and interpreter usage logic (2448 lines, ~198 lines added)

## Decisions Made
- **Manual override as primary**: When `settings.python_path` is set and exists, it bypasses all auto-detection. This makes user intent unambiguous.
- **extraArgs for py -3**: The `py -3` Windows launcher requires `-3` as a separate argument. Rather than adding special-case logic at each call site, the resolver returns it in `extraArgs`, and callers spread it into their args array.
- **Stale override is visible, not silent**: When a saved `python_path` no longer exists on disk, the settings UI shows `[!!]` prefix with a warning message. The value is NOT silently cleared — user may fix the path.
- **zotero_data_dir validation specificity**: Each failure mode (empty, not found, not a directory, missing storage/) has its own error message, making it easy for users to diagnose the issue.

## Deviations from Plan

None — plan executed exactly as written. No auto-fixes needed.

## Issues Encountered

None. All syntax checks pass (`node --check` confirms valid JS).

## Next Phase Readiness
- Python interpreter visibility and override complete
- All subprocess calls consistently using resolved interpreter
- zotero_data_dir required with validation ready for install flow
- Ready for Phase 52 (Setup Polish) and Phase 53 (Doctor) which can build on the interpreter resolution infrastructure

---

*Phase: 51-runtime-selection-setup-gate*
*Completed: 2026-05-08*
