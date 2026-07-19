# Phase 43: Repair & Directory Defaults - Summary

**Status:** Complete ✅
**Tests:** 59 passed (27 repair + 32 config)
**Date:** 2026-05-07

## Changes

### `repair.py`
- `_detect_path_errors()` scans Literature/ for path_error in formal notes
- `run_repair()` three-way comparison: formal_note_ocr_status vs index vs meta
- Fix writes target formal note frontmatter

### Directory Defaults
- 8 `cfg.get("system_dir", "99_System")` → `"System"` across asset_index/sync/repair/setup_wizard
- setup_wizard function sigs: `"99_System"` → `"System"`, `"03_Resources"` → `"Resources"`, `"05_Bases"` → `"Bases"`
- `scripts/validate_setup.py` defaults updated
- `.gitignore` patterns added for `System/`, `Resources/`, `Bases/`
- CLI help text updated

### Tests
- `test_repair.py`: `library_record` → `formal_note` assertions; tests now create formal notes not library-records
