---
phase: 52-runtime-alignment-failure-closure
plan: 001
type: execute
wave: 1
depends_on: [51]
subsystem: plugin
tags:
  - runtime-health
  - version-drift
  - error-classification
  - manifest-alignment
  - pyyaml-dependency
dependency_graph:
  requires: [Phase 51 - Runtime alignment & error classification]
  provides: [Runtime Health settings section, dashboard drift banner, extended error patterns, Copy diagnostic]
  affects: [settings page, dashboard, setup wizard, build system]
tech-stack:
  added: []
  patterns:
    - "execFile for async version comparison"
    - "spawn for pip install --upgrade"
    - "navigator.clipboard for diagnostic copy"
key-files:
  created: []
  modified:
    - manifest.json
    - paperforge/plugin/manifest.json
    - paperforge/plugin/versions.json
    - paperforge/plugin/main.js
    - paperforge/plugin/styles.css
    - pyproject.toml
    - scripts/bump.py
decisions:
  - "Runtime Health section inserted between Python path row and Preparation guide"
  - "Error pattern order: most specific first (pip before generic command not found)"
  - "_syncRuntime reuses _autoUpdate pip install pattern with visible feedback"
metrics:
  duration: "~1 hour"
  completed_date: "2026-05-08"
---

# Phase 52 Plan 001: Runtime Alignment & Failure Closure Summary

**One-liner:** Runtime Health settings section with version match/mismatch badge, dashboard drift warning banner, extended 10-category failure classification with Copy diagnostic button, manifest minAppVersion bump to 1.9.0, and PyYAML dependency.

## Requirements Addressed

| Requirement | Status | Description |
|------------|--------|-------------|
| RUNTIME-04 | Done | Runtime drift detection and sync via settings section + dashboard banner |
| RUNTIME-05 | Done | Install failure classification extended to 10 categories + Copy diagnostic |
| CLEAN-02 | Done | bump.py manifest source chain verified and documented with comment |
| CLEAN-03 | Done | minAppVersion raised to 1.9.0 in root + plugin manifests and versions.json |
| CLEAN-04 | Done | PyYAML>=6.0 added to pyproject.toml dependencies |

## Task Completion

### Task 1: CLEAN fixes (3f98f04)

- Added clarifying comment to bump.py: "Both root_manifest and plugin_manifest are updated from the canonical __init__.py version"
- Updated root `manifest.json` minAppVersion: `1.0.0` → `1.9.0`
- Updated `paperforge/plugin/manifest.json` minAppVersion: `1.0.0` → `1.9.0`
- Updated `versions.json` compatibility: both entries changed to `1.9.0`
- Added `"pyyaml>=6.0"` to pyproject.toml dependencies
- Verified: yaml is already in status.py required_modules list, no bare yaml imports found

### Task 2: Runtime Health UI + Dashboard Drift Banner (2ecbf31)

- **i18n:** Added 14 English and 14 Chinese keys for Runtime Health section and drift warning
- **Settings section:** "Runtime Health" section between Python path row and Preparation guide
  - Shows `Plugin vX → Python vY` with async version fetch via `execFile`
  - Green badge "Match" when versions align
  - Red badge "Mismatch" when versions differ
  - Orange badge "Not installed" when python package missing
  - "Sync Runtime" button runs `pip install --upgrade git+...@${ver}` with visible feedback
- **Dashboard drift banner:** Yellow warning banner at top of dashboard when versions mismatch
  - Created in `_renderGlobalMode()`, populated asynchronously in `_fetchVersion()` callback
  - Non-blocking -- does not interfere with Sync/OCR operations
- **CSS:** `.paperforge-runtime-badge` (match/mismatch/missing states), `.paperforge-drift-banner` (yellow warning)

### Task 3: Extended Failure Classification + Copy Diagnostic (2ecbf31)

- **Error classification:** Extended `_formatSetupError` from 5 to 10 categories:
  1. `pip not found` (new, highest priority)
  2. `Python not found` (existing)
  3. `Network error` (new -- DNS, connection refused, etc.)
  4. `SSL certificate error` (new)
  5. `Disk full` (new)
  6. `PaperForge not installed` (existing)
  7. `Permission denied` (expanded with EPERM)
  8. `Path not found` (existing)
  9. `Timeout` (existing)
  10. Raw fallback / `Unknown error`
- **Copy diagnostic button:** Added to setup wizard catch block after error message
  - Collects: Category + Plugin version + Python path + OS + Raw error (2000 chars)
  - Copies to clipboard via `navigator.clipboard.writeText()`
  - Shows "Copied!" feedback for 3 seconds
- **i18n:** Added `error_copy_diagnostic` and `error_copied` keys in both en/zh
- **CSS:** `.paperforge-copy-diag-btn` with hover states

## Verification Results

All 42 automated checks passed:
- i18n keys: 19/19 present
- _syncRuntime method: found
- _driftBannerEl reference: found
- Error patterns: 9/9 present
- Diagnostic fields: 6/6 present
- CSS classes: 7/7 present
- minAppVersion: 1.9.0 in both manifests
- PyYAML: in pyproject.toml
- bump.py comment: added

## Deviations from Plan

None -- plan executed as written.

## Commits

- `3f98f04`: chore(52-001): align manifest sources, bump minAppVersion to 1.9.0, add PyYAML dep
- `2ecbf31`: feat(52-001): add Runtime Health UI, dashboard drift banner, extended error classification, Copy diagnostic

## Duration

~1 hour

## Success Criteria

- [x] All 5 requirements (RUNTIME-04, RUNTIME-05, CLEAN-02, CLEAN-03, CLEAN-04) addressed
- [x] minAppVersion updated to "1.9.0" in both manifests and versions.json
- [x] PyYAML added to pyproject.toml dependencies
- [x] Runtime Health section displays below Python path in settings
- [x] Version comparison shows match (green) / mismatch (red) badge
- [x] "Sync Runtime" button triggers pip install with feedback
- [x] Dashboard shows yellow drift warning banner when versions mismatch
- [x] _formatSetupError covers 10 categories with correct priority ordering
- [x] "Copy diagnostic" button appears on setup failure with working clipboard copy
- [x] All i18n keys in both English and Chinese
- [x] CSS classes defined for badge states, banner, and diagnostic button
- [x] Automated verification commands pass

## Self-Check: PASSED

All modified files confirmed present on disk.
Both commits confirmed in git history.
No stubs detected -- all UI elements wired to live data sources.

| Check | Result |
|-------|--------|
| File: manifest.json | FOUND |
| File: paperforge/plugin/manifest.json | FOUND |
| File: paperforge/plugin/versions.json | FOUND |
| File: paperforge/plugin/main.js | FOUND |
| File: paperforge/plugin/styles.css | FOUND |
| File: pyproject.toml | FOUND |
| File: scripts/bump.py | FOUND |
| Commit: 3f98f04 | FOUND |
| Commit: 2ecbf31 | FOUND |
