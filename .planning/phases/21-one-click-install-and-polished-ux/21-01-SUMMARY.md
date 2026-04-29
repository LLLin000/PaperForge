---
phase: 21-one-click-install-and-polished-ux
plan: 01
subsystem: plugin
tags: [obsidian, plugin, settings-tab, css, validation, chinese-ui]
requires:
  - phase: 20-plugin-settings-shell-persistence
    provides: PaperForgeSettingTab with DEFAULT_SETTINGS, display(), helpers
provides:
  - Install button section with status area in settings tab
  - Client-side field validation for 7 required fields
  - Status area CSS styles with success/error/progress color variants
affects: [21-one-click-install-and-polished-ux]
tech-stack:
  added: []
  patterns:
    - Obsidian CSS variables for theme-consistent styling
    - color-mix() for subtle tinted backgrounds
key-files:
  created: []
  modified:
    - paperforge/plugin/main.js
    - paperforge/plugin/styles.css
key-decisions:
  - "D-01: Settings tab is purely additive — zero changes to PaperForgeStatusView sidebar or ACTIONS[] definitions"
  - "D-02: Client-side only validation using string trim checks, no filesystem calls"
  - "D-03: zotero_data_dir is NOT validated (optional field — auto-detected by headless_setup)"
  - "D-04: All error messages in Chinese per INST-03 requirement"
requirements-completed: [INST-01, INST-03]
duration: 5 min
completed: 2026-04-29
---

# Phase 21 Plan 01: Install Button UI & Field Validation

**Install button section with status area, client-side validation of 7 required fields, and CSS status styles with success/error/progress color variants**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-29T14:38:41Z
- **Completed:** 2026-04-29T14:43:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- "安装配置" section appended to `PaperForgeSettingTab.display()` with status div + CTA button
- `_validate()` method checks 7 required settings fields for non-empty values with Chinese error messages
- `paperforge/plugin/styles.css` gains SECTION 5 with 4 CSS classes for install status display
- Button onClick wired to `_runSetup(button)` — forward declaration for Plan 02 subprocess wiring
- No existing code modified (sidebar, actions, other settings sections preserved)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add install button section and status area to display()** - `2f1feec` (feat)
2. **Task 2: Add _validate() field validation method** - `0d60dd6` (feat)
3. **Task 3: Add install status CSS styles** - `dc6be1c` (feat)

**Plan metadata:** (final commit after summary)

## Files Created/Modified

- `paperforge/plugin/main.js` - Added "安装配置" section (14 lines), `_validate()` method (29 lines)
- `paperforge/plugin/styles.css` - Added SECTION 5 with `.paperforge-install-status`, `.paperforge-install-success`, `.paperforge-install-error`, `.paperforge-install-progress` (31 lines)

## Decisions Made

- **Additive-only approach**: Settings tab is purely additive to existing `PaperForgeSettingTab.display()` — no modifications to `PaperForgeStatusView` sidebar or `ACTIONS[]` definitions
- **Client-side validation**: Uses simple string checks (`!s.key || !s.key.trim()`), no filesystem calls. Path existence validation deferred to subprocess (fails gracefully with friendly error message)
- **Optional field exclusion**: `zotero_data_dir` is NOT validated — it's optional and auto-detected by the headless setup

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Plan 21-02: wire `_runSetup()` subprocess orchestration and notice formatting helpers into the install button.

## Self-Check: PASSED

- [x] All 3 tasks committed atomically (2f1feec, 0d60dd6, dc6be1c)
- [x] main.js: install section, _validate(), _runSetup reference present
- [x] styles.css: SECTION 5 with all 3 status variants present
- [x] No existing code modified (sidebar, actions preserved)
- [x] SUMMARY.md created in plan directory

---

*Phase: 21-one-click-install-and-polished-ux*
*Completed: 2026-04-29*
