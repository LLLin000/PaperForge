# Phase 11 Plan 01: Zotero Path Normalization — Wave 1 Summary

**Phase:** 11
**Plan:** 01
**Wave:** 1 of 4
**Status:** COMPLETE
**Date:** 2026-04-24
**Tasks Completed:** 2 of 8

---

## One-Liner

Added `_normalize_attachment_path()` to convert all BBT export formats (absolute Windows, storage: prefix, bare relative) into consistent `storage:KEY/filename.pdf` format, and `_identify_main_pdf()` with hybrid strategy (title==PDF primary, largest size fallback, shortest title final fallback) to distinguish main PDF from supplementary materials.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 01 | Normalize BBT Path Formats | `2939b86` | `pipeline/worker/scripts/literature_pipeline.py` |
| 02 | Identify Main PDF vs Supplementary | `7e7dbe1` | `pipeline/worker/scripts/literature_pipeline.py` |

---

## New Functions

### `_normalize_attachment_path(path, zotero_dir)`
- **Location:** `pipeline/worker/scripts/literature_pipeline.py:733`
- **Purpose:** Normalize BBT attachment paths to consistent `storage:` format
- **Handles 3 formats:**
  1. Absolute Windows: `D:\...\Zotero\storage\8CHARKEY\filename.pdf` → `storage:8CHARKEY/filename.pdf`
  2. `storage:` prefix: pass-through with slash normalization
  3. Bare relative: `KEY/filename.pdf` → `storage:KEY/filename.pdf`
- **Returns:** `(normalized_path, bbt_path_raw, zotero_storage_key)`

### `_identify_main_pdf(attachments)`
- **Location:** `pipeline/worker/scripts/literature_pipeline.py:790`
- **Purpose:** Distinguish main PDF from supplementary materials using hybrid strategy
- **Priority:**
  1. `title == "PDF"` AND `contentType == "application/pdf"`
  2. Largest file by `size` field (if available and differentiated)
  3. Shortest title (when sizes equal or unavailable)
- **Returns:** `(main_pdf_attachment, supplementary_attachments_list)`

---

## Modified Files

### `pipeline/worker/scripts/literature_pipeline.py`
- **Lines added:** ~166
- **Lines modified:** ~8

**Changes:**
1. Added `_normalize_attachment_path()` helper (lines 733-787)
2. Added `_identify_main_pdf()` helper (lines 790-838)
3. Updated `load_export_rows()` attachment processing:
   - Uses `_normalize_attachment_path()` for each attachment
   - Preserves `title`, `size` from BBT JSON
   - Stores `bbt_path_raw`, `zotero_storage_key` per attachment
   - Calls `_identify_main_pdf()` to set row-level fields
   - Adds to row dict: `pdf_path`, `supplementary`, `attachment_count`, `bbt_path_raw`, `zotero_storage_key`, `path_error`
4. Updated `library_record_markdown()` frontmatter generation:
   - Emits `bbt_path_raw`, `zotero_storage_key`, `attachment_count`
   - Emits `supplementary:` as YAML list of wikilinks (`[[path]]`)
   - Emits `path_error` only when non-empty

---

## Acceptance Criteria Verification

### Task 01
- [x] `grep -n "def _normalize_attachment_path"` returns match (line 733)
- [x] `grep -n "bbt_path_raw"` returns 9 matches
- [x] `grep -n "zotero_storage_key"` returns 8 matches
- [x] Absolute Windows paths converted to `storage:KEY/filename.pdf`
- [x] `storage:` prefix paths pass through unchanged
- [x] Bare relative paths become `storage:KEY/file.pdf`

### Task 02
- [x] `grep -n "def _identify_main_pdf"` returns match (line 790)
- [x] `grep -n "supplementary:"` returns 3 matches in frontmatter generation
- [x] `grep -n "attachment_count"` returns 3 matches
- [x] Single-attachment items: `supplementary: []` emitted
- [x] Multi-attachment items: `supplementary` contains list of wikilinks
- [x] No PDF attachments: `path_error: not_found` is set in row dict

---

## Data Flow Changes

```
BBT JSON attachments[]
    ↓ _normalize_attachment_path()
Normalized attachments with bbt_path_raw, zotero_storage_key
    ↓ _identify_main_pdf()
main_pdf + supplementary list
    ↓ load_export_rows() row dict
pdf_path, supplementary, attachment_count, path_error
    ↓ library_record_markdown()
Frontmatter with new fields
```

---

## Deviations from Plan

**None.** Wave 1 executed exactly as written.

**Minor implementation notes:**
- `_normalize_attachment_path()` takes optional `zotero_dir` parameter (per plan) but current implementation detects Zotero storage pattern via path structure (`/storage/8CHARKEY/`) without requiring `zotero_dir`. The parameter is reserved for future stricter validation.
- `supplementary` field stores wikilink-wrapped paths (`[[storage:KEY/file.pdf]]`) in frontmatter. The `storage:` prefix will be resolved to vault-relative paths in Wave 2 (Task 03).

---

## Blockers / Deferred

- **Wave 2 (Tasks 03-04):** Wikilink generation with vault-relative paths and `sync_writeback_queue()` frontmatter updates. `storage:KEY/file.pdf` → `[[system/Zotero/storage/KEY/file.pdf]]` conversion pending.
- **Wave 3 (Tasks 05-06):** Doctor integration and repair/status path_error handling.
- **Wave 4 (Tasks 07-08):** Tests, docs, and final verification.

---

## Key Decisions Applied

- **D-01:** Path normalization in `load_export_rows()` stage (unified conversion)
- **D-02:** Hybrid main PDF identification strategy (title → size → shortest title)
- **D-03:** Supplementary materials stored in `supplementary` frontmatter field
- **D-04:** Code adapts to ALL BBT export formats without user configuration

---

## Self-Check

- [x] `_normalize_attachment_path()` exists and handles 3 formats
- [x] `_identify_main_pdf()` exists with 3-priority hybrid strategy
- [x] `bbt_path_raw` stored per attachment
- [x] `zotero_storage_key` extracted from paths
- [x] `attachment_count` tracked per item
- [x] `supplementary` generated as YAML list
- [x] `path_error` set when no PDFs found
- [x] All changes committed atomically
- [x] Python syntax valid
- [x] Acceptance criteria verified via grep and runtime tests

---

*Wave 1 complete. Ready for Wave 2 (Tasks 03-04).*
