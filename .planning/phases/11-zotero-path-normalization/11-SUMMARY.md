# Phase 11 Plan 01: Zotero Path Normalization — Wave 3 Summary

**Phase:** 11
**Plan:** 01
**Wave:** 3 of 4
**Status:** COMPLETE
**Date:** 2026-04-24
**Tasks Completed:** 6 of 8 (Tasks 01-06 done)

---

## One-Liner

Added Path Resolution diagnostics to `paperforge doctor` (junction detection, PDF path validation, wikilink format checking) and integrated `path_error` frontmatter field with `paperforge repair --fix-paths` auto-resolution and `paperforge status` reporting.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 01 | Normalize BBT Path Formats | `2939b86` | `pipeline/worker/scripts/literature_pipeline.py` |
| 02 | Identify Main PDF vs Supplementary | `7e7dbe1` | `pipeline/worker/scripts/literature_pipeline.py` |
| 03 | Generate Obsidian Wikilinks | `adf349e` | `pipeline/worker/scripts/literature_pipeline.py` |
| 04 | Update Library-Record Frontmatter | `adf349e` | `pipeline/worker/scripts/literature_pipeline.py` |
| 05 | Enhance Doctor for Junction Detection | `bdbaca4` | `pipeline/worker/scripts/literature_pipeline.py` |
| 06 | Integrate path_error with Repair/Status | `434660c` | `pipeline/worker/scripts/literature_pipeline.py`, `paperforge/cli.py`, `paperforge/commands/repair.py`, `paperforge/commands/status.py` |

---

## New / Rewritten Functions (Wave 2)

### `obsidian_wikilink_for_pdf(pdf_path, vault_dir, zotero_dir)`
- **Location:** `pipeline/worker/scripts/literature_pipeline.py:680`
- **Signature:** `obsidian_wikilink_for_pdf(pdf_path: str, vault_dir: Path, zotero_dir: Path | None = None) -> str`
- **Purpose:** Convert normalized `storage:KEY/file.pdf` paths to vault-relative Obsidian wikilinks
- **Logic:**
  1. Detects `storage:` prefix -> resolves through `zotero_dir` (`vault/system/Zotero`)
  2. Computes `relative_to(vault_dir)` for clean vault-relative path
  3. Falls back to `absolutize_vault_path()` with `resolve_junction=True` for non-storage paths
  4. Returns `[[relative/path/with/slashes.pdf]]` format
- **Chinese filenames:** Preserved without escaping (wikilink-safe)

### `absolutize_vault_path(vault, path, resolve_junction=False)`
- **Location:** `pipeline/worker/scripts/literature_pipeline.py:700`
- **Purpose:** Resolve paths with optional junction resolution (D-05)
- **When `resolve_junction=True`:** Calls `paperforge.pdf_resolver.resolve_junction()` before returning

---

## New / Rewritten Functions (Wave 3)

### `check_zotero_location(vault, cfg, add_check)`
- **Location:** `pipeline/worker/scripts/literature_pipeline.py:3402`
- **Purpose:** Detect if Zotero data directory is inside vault, junctioned, or missing
- **Logic:**
  1. If `system/Zotero` is a junction/symlink: verify target exists, report pass
  2. If `system/Zotero` is a real directory with `storage/`: report "inside vault"
  3. If missing: auto-detect actual Zotero data dir via `_detect_zotero_data_dir()`, recommend exact `mklink /J` command

### `check_pdf_paths(vault, paths, add_check)`
- **Location:** `pipeline/worker/scripts/literature_pipeline.py:3469`
- **Purpose:** Sample up to 5 random library records and validate their `pdf_path` wikilinks resolve to actual files
- **Output:** Reports `X/Y PDF paths valid` with error type breakdown

### `check_wikilink_format(vault, paths, add_check)`
- **Location:** `pipeline/worker/scripts/literature_pipeline.py:3515`
- **Purpose:** Verify all `pdf_path` values in library-records use `[[...]]` wikilink format
- **Output:** Reports count of non-wikilink paths, suggests re-running `paperforge sync`

### `_detect_path_errors(paths, verbose)`
- **Location:** `pipeline/worker/scripts/literature_pipeline.py:3047`
- **Purpose:** Scan all library-records for `path_error` frontmatter field
- **Returns:** Dict with `total`, `by_type` (error counts), `records` (list of error records)

### `repair_pdf_paths(vault, paths, error_records, verbose)`
- **Location:** `pipeline/worker/scripts/literature_pipeline.py:3092`
- **Purpose:** Re-resolve PDF paths for items with `path_error`
- **Logic:**
  1. For `not_found`: reload BBT export, re-run `_normalize_attachment_path()` + `_identify_main_pdf()`, regenerate wikilink
  2. For all errors: attempt `resolve_pdf_path()` with current `zotero_dir`
  3. If resolved: update record, clear `path_error`
  4. If still fails: keep `path_error`, log reason

---

## Modified Call Sites

### `run_selection_sync()` — library-record creation
- **Line ~1176:** `pdf_path` now generated via `obsidian_wikilink_for_pdf(resolved_pdf, vault, zotero_dir)`
- **Line ~1177:** Passes `bbt_path_raw`, `zotero_storage_key`, `attachment_count`, `supplementary`, `path_error` to `library_record_markdown()`
- **Line ~1173:** Converts supplementary `storage:` paths to wikilinks before passing

### `run_selection_sync()` — library-record update
- **Line ~1180:** `_add_missing_frontmatter_fields()` now adds `bbt_path_raw`, `zotero_storage_key`, `attachment_count`, `path_error`
- **Line ~1183:** `update_frontmatter_field()` updates `pdf_path` with wikilink format

### `run_index_refresh()` — formal note generation
- **Line ~1705:** `pdf_path` generated via `obsidian_wikilink_for_pdf(pdf_attachments[0]['path'], vault, zotero_dir)`
- Added `zotero_dir` resolution at function entry

### `library_record_markdown()` — frontmatter emission
- **Line ~1029:** `supplementary` now expects pre-formatted wikilink strings from caller
- Emits `bbt_path_raw`, `zotero_storage_key`, `attachment_count`, `path_error` (conditional)

### `run_doctor()` — path resolution checks
- **Line ~3660:** Calls `check_zotero_location()`, `check_pdf_paths()`, `check_wikilink_format()` under "Path Resolution" section

### `run_repair()` — path_error integration
- **Line ~3199:** New `fix_paths` parameter
- **Line ~3353:** Calls `_detect_path_errors()` to scan for path errors
- **Line ~3363:** Calls `repair_pdf_paths()` when `--fix-paths` is passed
- **Line ~3366:** Reports fix count; line ~3368 suggests `--fix-paths` when errors found

### `run_status()` — path_error reporting
- **Line ~3759:** Counts records with `path_error` in frontmatter
- **Line ~3771:** Prints `path_errors: N`; suggests `paperforge repair --fix-paths` if > 0

### `paperforge/commands/repair.py` — result handling
- Captures `run_repair()` result dict
- Prints `path_error` summary with error type breakdown
- Returns non-zero exit code if divergences or path errors remain

---

## Data Flow

```
BBT JSON attachments[]
    ↓ _normalize_attachment_path()
Normalized attachments with bbt_path_raw, zotero_storage_key
    ↓ _identify_main_pdf()
main_pdf (storage:KEY/file.pdf) + supplementary list
    ↓ obsidian_wikilink_for_pdf()
[[system/Zotero/storage/KEY/文件名.pdf]]
    ↓ library_record_markdown()
Frontmatter with pdf_path, supplementary, bbt_path_raw,
  zotero_storage_key, attachment_count, path_error
    ↓ paperforge doctor
Path Resolution section validates junctions, wikilinks, format
    ↓ paperforge repair --fix-paths
Re-resolves failed paths, clears path_error when fixed
```

---

## Deviations from Plan

### Deviation 1: Combined Task 03+04 into single commit
- **Reason:** Both tasks modify the same file (`literature_pipeline.py`) with tightly coupled changes. Task 04 (frontmatter updates) depends on Task 03 (wikilink generation function). Atomic per-file commit was prioritized over per-task commit.
- **Impact:** Single commit `adf349e` covers both tasks.

### Deviation 2: Used `as_posix()` instead of `replace("\\", "/")`
- **Reason:** `pathlib.Path.as_posix()` is the idiomatic Python way to convert backslashes to forward slashes. It is more robust than string replacement.
- **Impact:** Functionally equivalent; acceptance criterion satisfied via `as_posix()` instead of `replace`.

### Deviation 3: Functions placed in `literature_pipeline.py` not `ocr_diagnostics.py`
- **Reason:** The plan's acceptance criteria referenced `paperforge/ocr_diagnostics.py`, but `run_doctor()` and all doctor infrastructure live in `pipeline/worker/scripts/literature_pipeline.py`. `ocr_diagnostics.py` is exclusively for OCR (PaddleOCR) tiered checks.
- **Impact:** Path resolution checks are correctly co-located with `run_doctor()`. Grep criteria satisfied in the actual implementation file.

---

## Acceptance Criteria Verification

### Task 03
- [x] `obsidian_wikilink_for_pdf()` signature updated to `(pdf_path, vault_dir, zotero_dir)`
- [x] `absolutize_vault_path()` has `resolve_junction` parameter (lines 700, 709)
- [x] `resolve_junction` imported from `paperforge.pdf_resolver` (line 710)
- [x] Wikilink format `[[...]]` used throughout (lines 697, 698, 722, 723)
- [x] Forward slashes via `as_posix()` (lines 697, 698, 722, 723)
- [x] `run_index_refresh()` updated with new signature (line 1705)

### Task 04
- [x] `bbt_path_raw` passed in writeback (line 1177, 1180)
- [x] `zotero_storage_key` passed in writeback (line 1177, 1180)
- [x] `attachment_count` passed in writeback (line 1177, 1180)
- [x] `path_error` passed in writeback (line 1177, 1180)
- [x] `pdf_path` in wikilink format: `[[...]]`
- [x] `yaml_quote()` correctly handles wikilink strings (no special chars to escape)
- [x] `path_error` only emitted when non-empty (line 1038)
- [x] `supplementary` emits list of wikilinks (line 1032)

### Task 05
- [x] `check_zotero_location` defined (2 grep matches)
- [x] `check_pdf_paths` defined (2 grep matches)
- [x] `check_wikilink_format` defined (2 grep matches)
- [x] `paperforge doctor` output contains "Path Resolution" section (13 matches)
- [x] Junction recommendation includes exact `mklink /J` command string
- [x] Invalid paths reported with specific error counts and types

### Task 06
- [x] `path_error` in `paperforge/commands/repair.py` (7 matches >= 3)
- [x] `path_error` in `paperforge/commands/status.py` (1 match >= 1)
- [x] `repair_pdf_paths` defined (2 matches)
- [x] `--fix-paths` flag in CLI parser (1 match)
- [x] `paperforge repair` shows path error summary when errors exist
- [x] `paperforge status` shows path error count and suggests repair

---

## Blockers / Deferred

- **Wave 4 (Tasks 07-08):** Tests (`test_path_normalization.py`), documentation updates (`AGENTS.md`, `ARCHITECTURE.md`), and final verification.

---

## Key Decisions Applied

- **D-05:** Junctions resolved in `absolutize_vault_path()` before computing relative paths
- **D-07:** `paperforge doctor` detects Zotero location, recommends junction with exact `mklink /J` command
- **D-08:** Obsidian wikilink format `[[relative/path/with/slashes]]` with forward slashes
- **D-01 through D-04:** Carried forward from Wave 1

---

## Self-Check

- [x] `obsidian_wikilink_for_pdf()` returns `[[...]]` format with forward slashes
- [x] `absolutize_vault_path()` has `resolve_junction` parameter
- [x] Library-records contain `pdf_path: "[[...]]"`
- [x] Chinese filenames work in wikilinks (no escaping needed)
- [x] `supplementary` field contains list of wikilinks
- [x] `path_error` only present when there's an error
- [x] `paperforge doctor` contains "Path Resolution" section with 3 checks
- [x] `paperforge repair --fix-paths` flag exists and is wired through CLI
- [x] `paperforge status` shows path_error count and repair suggestion
- [x] All changes committed to git (`bdbaca4`, `434660c`)
- [x] Python syntax valid (verified via `py_compile`)
- [x] Acceptance criteria verified via grep

---

*Wave 3 complete. Ready for Wave 4 (Tasks 07-08).*
