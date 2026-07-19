# Phase 40: Library-Record Deprecation — Summary

**Status:** Complete ✅
**Requirements:** LRD-01 through LRD-05

## One-Liner
Library-records fully deprecated: sync stops creation (LRD-01/03 handled by Phase 37), doctor detects stale directory (LRD-05), orphaned-record cleanup path updated (LRD-04), migration handled by _build_entry defaults (LRD-02).

## Key Deliverables
- LRD-01 (new users never see library-records): ✓ Phase 37 removed library_record_markdown()
- LRD-02 (upgrading user migration): ✓ _build_entry() defaults do_ocr/analyze to has_pdf; load_control_actions() still available for future migration enhancement
- LRD-03 (sync stops): ✓ run_selection_sync() no longer writes library-records
- LRD-04 (orphaned cleanup): ✓ points to control_records_dir; no-op if directory empty (normal for new users)
- LRD-05 (doctor stale detection): ✓ added check to run_doctor(): warns if library-records/ directory still has .md files

## Verification
- 188+ tests pass
- grep confirms zero library_record_markdown references
- Doctor reports stale library-records if detected
