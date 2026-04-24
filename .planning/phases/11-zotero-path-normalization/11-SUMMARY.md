# Phase 11 Plan 01: Zotero Path Normalization — Wave 2 Summary

**Phase:** 11
**Plan:** 01
**Wave:** 2 of 4
**Status:** COMPLETE
**Date:** 2026-04-24
**Tasks Completed:** 4 of 8 (Tasks 01-04 done)

---

## One-Liner

Rewrote `obsidian_wikilink_for_pdf()` to generate `[[system/Zotero/storage/KEY/文件名.pdf]]` wikilinks from normalized `storage:KEY/file.pdf` paths using `zotero_dir` resolution, and updated `run_selection_sync()` to emit `pdf_path`, `supplementary`, `bbt_path_raw`, `zotero_storage_key`, `attachment_count`, and `path_error` in library-record frontmatter.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 01 | Normalize BBT Path Formats | `2939b86` | `pipeline/worker/scripts/literature_pipeline.py` |
| 02 | Identify Main PDF vs Supplementary | `7e7dbe1` | `pipeline/worker/scripts/literature_pipeline.py` |
| 03 | Generate Obsidian Wikilinks | `adf349e` | `pipeline/worker/scripts/literature_pipeline.py` |
| 04 | Update Library-Record Frontmatter | `adf349e` | `pipeline/worker/scripts/literature_pipeline.py` |

---

## New / Rewritten Functions

### `obsidian_wikilink_for_pdf(pdf_path, vault_dir, zotero_dir)`
- **Location:** `pipeline/worker/scripts/literature_pipeline.py:680`
- **Signature:** `obsidian_wikilink_for_pdf(pdf_path: str, vault_dir: Path, zotero_dir: Path | None = None) -> str`
- **Purpose:** Convert normalized `storage:KEY/file.pdf` paths to vault-relative Obsidian wikilinks
- **Logic:**
  1. Detects `storage:` prefix → resolves through `zotero_dir` (`vault/system/Zotero`)
  2. Computes `relative_to(vault_dir)` for clean vault-relative path
  3. Falls back to `absolutize_vault_path()` with `resolve_junction=True` for non-storage paths
  4. Returns `[[relative/path/with/slashes.pdf]]` format
- **Chinese filenames:** Preserved without escaping (wikilink-safe)

### `absolutize_vault_path(vault, path, resolve_junction=False)`
- **Location:** `pipeline/worker/scripts/literature_pipeline.py:700`
- **Purpose:** Resolve paths with optional junction resolution (D-05)
- **When `resolve_junction=True`:** Calls `paperforge.pdf_resolver.resolve_junction()` before returning

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
```

---

## Deviations from Plan

### Deviation 1: Combined Task 03+04 into single commit
- **Reason:** Both tasks modify the same file (`literature_pipeline.py`) with tightly coupled changes. Task 04 (frontmatter updates) depends on Task 03 (wikilink generation function). Atomic per-file commit was prioritized over per-task commit.
- **Impact:** Single commit `adf349e` covers both tasks.

### Deviation 2: Used `as_posix()` instead of `replace("\\", "/")`
- **Reason:** `pathlib.Path.as_posix()` is the idiomatic Python way to convert backslashes to forward slashes. It is more robust than string replacement.
- **Impact:** Functionally equivalent; acceptance criterion satisfied via `as_posix()` instead of `replace`.

---

## Blockers / Deferred

- **Wave 3 (Tasks 05-06):** Doctor integration (`check_zotero_location`, `check_pdf_paths`, `check_wikilink_format`) and repair/status `path_error` handling.
- **Wave 4 (Tasks 07-08):** Tests (`test_path_normalization.py`), documentation updates (`AGENTS.md`, `ARCHITECTURE.md`), and final verification.

---

## Key Decisions Applied

- **D-05:** Junctions resolved in `absolutize_vault_path()` before computing relative paths
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
- [x] All changes committed to git (`adf349e`)
- [x] Python syntax valid (verified via import)
- [x] Acceptance criteria verified via grep

---

*Wave 2 complete. Ready for Wave 3 (Tasks 05-06).*
