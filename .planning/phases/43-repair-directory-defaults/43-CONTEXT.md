# Phase 43: Repair & Directory Defaults - Context

**Gathered:** 2026-05-07
**Status:** Complete
**Mode:** Infrastructure phase (discuss skipped)

<domain>
## Phase Boundary

Repair worker re-anchored from library-records to formal notes + canonical index for three-way divergence detection. All 14 hardcoded old directory defaults updated to clean names across production code, setup wizard, validation script, .gitignore, and CLI help.

Requirements: REP-01, REP-02, REP-03, DEF-01 through DEF-07

**Completed:**
- `_detect_path_errors()` — reads from Literature/ not library-records
- `run_repair()` — scans Literature/ for formal notes, compares formal_note_ocr_status vs index vs meta
- All fix writes target formal note frontmatter
- 8 `cfg.get("system_dir", "99_System")` → `"System"` across asset_index/sync/repair/setup_wizard
- Setup_wizard function signatures: `"99_System"` → `"System"`, `"03_Resources"` → `"Resources"`, `"05_Bases"` → `"Bases"`
- CLI help text updated
- .gitignore patterns added for new clean names
- repair tests updated (library_record → formal_note assertions)
- 59 tests pass (27 repair + 32 config)
</domain>
