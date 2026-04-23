# Phase 6, Plan 01 — Summary

**Wave:** 1 (independent doc fixes + HTTP 405 handling)
**Status:** COMPLETED

## Tasks Completed

### Task 1: Fix ld-deep.md field name (SETUP-05)
- **File:** `command/ld-deep.md`
- **Change:** Replaced `literature_script` with `ld_deep_script` in 2 places
  - Line ~170: command example uses `ld_deep_script`
  - Line ~201: field name table uses `ld_deep_script`
- **Verification:** `grep "literature_script" command/ld-deep.md` returns no results
- **Result:** PASS

### Task 2: Add fallback command to AGENTS.md and INSTALLATION.md (SETUP-03)
- **Files:** `AGENTS.md`, `docs/INSTALLATION.md`
- **Change:** Added `python -m paperforge_lite` fallback command documentation
  - AGENTS.md: Added after command list in section 8
  - INSTALLATION.md: Added after worker script fallback
- **Verification:** `grep -c "python -m paperforge_lite" AGENTS.md docs/INSTALLATION.md` finds matches in both
- **Result:** PASS

### Task 3: HTTP 405 detection in ocr_diagnostics.py L2 (DIAG-04)
- **File:** `paperforge_lite/ocr_diagnostics.py`
- **Change:** Added 405-specific handling in L2 check (lines 64-70)
  - When HTTP 405 is detected, returns actionable message explaining method mismatch
- **Verification:** `grep -n "405 Method Not Allowed" paperforge_lite/ocr_diagnostics.py` finds the new code
- **Result:** PASS

## Requirements Covered

| REQ-ID | Description | Status |
|--------|-------------|--------|
| SETUP-03 | Fallback command documented | DONE |
| SETUP-05 | Field name consistency | DONE |
| DIAG-04 | HTTP 405 distinguished | DONE |

---

*Plan 01 complete: 2026-04-23*