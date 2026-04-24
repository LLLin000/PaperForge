# Phase 7 Summary — Zotero PDF, Metadata, And State Repair

**Status:** Complete (with one task deferred)  
**Date:** 2026-04-24  
**Plan:** [07-PLAN.md](07-PLAN.md)  
**Review:** [07-REVIEW.md](07-REVIEW.md)  

---

## What Was Accomplished

### 1. OCR Meta Validation in Deep Reading (Task 2)

`run_deep_reading()` now calls `validate_ocr_meta()` before trusting `meta.json` `ocr_status`. This prevents papers with corrupted/missing OCR files from being incorrectly reported as ready for deep reading.

- **Commit:** `981f5fa`
- **Tests:** `test_smoke.py` — `test_smoke_deep_reading_done_incomplete_is_blocked`
- **Impact:** Closes gap where `ocr_status: done` with missing files → false-ready state

### 2. Three-Way State Divergence Repair (Task 3)

New `run_repair(vault, paths, verbose, fix)` function scans all domains and detects contradictions between:
1. `library_record.md` frontmatter `ocr_status`
2. `formal_note.md` frontmatter `ocr_status`
3. `meta.json` `ocr_status` (post-`validate_ocr_meta()`)

Supports dry-run (default) and `--fix` mode. Repair actions set divergent records to `pending` and retrigger OCR where needed.

- **Commits:** `6052c82`, `d0ba1da`, `ff12515`
- **Tests:** `tests/test_repair.py` — 20 tests covering scan, fix, edge cases, verbose output
- **Issues found and fixed in review:**
  - Potential NameError on `validated_error` (fixed by initialization before try block)
  - Dead code `domain_lookup` removed
  - Case 3 (None meta_ocr_status) handling added
  - Case 4 repair logic added

### 3. Repair CLI Subcommand (Task 4)

Added `paperforge repair [--verbose] [--fix]` to CLI dispatch.

- **Commit:** `1f817a5`
- **File:** `paperforge_lite/cli.py`

### 4. Documentation Update (Task 5)

Added `paperforge repair` command reference to `AGENTS.md`.

- **Commit:** `bef53fc`

### 5. PDF Resolver Tests (Bonus)

Added `tests/test_pdf_resolver.py` with 8+ tests covering absolute, vault-relative, junction, storage-relative, and missing file scenarios for `resolve_pdf_path()`.

- **Commit:** `6052c82` (bundled with run_repair)
- **Note:** Tests validate `pdf_resolver.py` in isolation; BBT → resolver integration remains untested for bare paths.

---

## What Was Not Accomplished

### BBT PDF Path Normalization (Task 1 — Deferred)

The plan called for normalizing bare `KEY/KEY.pdf` BBT attachment paths to `storage:KEY/KEY.pdf` in `load_export_rows()` (line 747-749). **This code change was not implemented.**

**Current state:**
```python
attachment_path = attachment.get('path', '')
content_type = 'application/pdf' if str(attachment_path).lower().endswith('.pdf') else ''
attachments.append({'path': attachment_path, 'contentType': content_type})
```

**Why deferred:** The `run_repair()` function and OCR meta validation were prioritized as they address active state corruption issues. BBT bare path handling can be addressed when a concrete reproduction case is available.

**Workaround:** BBT can be configured to export with `storage:` prefix, or users can ensure PDFs are in paths that `resolve_pdf_path()` handles via other branches (absolute, vault-relative).

---

## Test Coverage Added

| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_repair.py` | 20 | Three-way divergence detection, dry-run vs fix, edge cases |
| `tests/test_pdf_resolver.py` | 8+ | PDF path resolution (unit tests) |
| `tests/test_smoke.py` | 1+ | `done_incomplete` blocked in deep-reading queue |

---

## Requirements Mapping

| Requirement | Status | Evidence |
|-------------|--------|----------|
| ZPATH-01 | **Partial** | `resolve_pdf_path()` handles paths; BBT bare → storage: normalization deferred |
| ZPATH-02 | **Partial** | `storage:` prefix paths resolve correctly; bare paths not auto-normalized |
| ZPATH-03 | **Partial** | `pdf_path` populated when resolution succeeds; bare paths may fail |
| META-01 | **Complete** | `first_author` extracted from BBT `creators` and written to library-records |
| META-02 | **Complete** | `journal` extracted from `publicationTitle` and written to library-records |
| STATE-01 | **Complete** | `validate_ocr_meta()` ensures state consistency; `repair` command fixes divergences |
| STATE-02 | **Complete** | `run_deep_reading()` calls `validate_ocr_meta()` before using `ocr_status` |
| STATE-03 | **Complete** | `paperforge deep-reading --verbose` prints ready/waiting/blocked queues |
| STATE-04 | **Complete** | `paperforge repair` identifies which records need OCR, are blocked, or ready |

---

## Known Issues (Non-Blocking)

1. **BBT bare path normalization:** Not implemented. Tracked for future phase if user reports PDF resolution failures.
2. **O(n*m) scan in `_resolve_formal_note_path`:** Per-record rglob scales poorly with large vaults. Acceptable for current vault sizes.
3. **Duplicated fix branches in `run_repair()`:** Two nearly identical repair branches could be refactored into a helper. Minor code quality issue.

---

## Commits

| Commit | Message |
|--------|---------|
| `981f5fa` | fix(run_deep_reading): call validate_ocr_meta() before using ocr_status |
| `6052c82` | Add run_repair() function for three-way OCR state divergence repair |
| `d0ba1da` | fix(run_repair): case 2 repair updates all three + case 3 handles None; add test_fix_case4 |
| `ff12515` | fix: initialize validated_status and validated_error before try block |
| `1f817a5` | Add repair subcommand to CLI |
| `bef53fc` | docs(agents): add paperforge repair command reference |

---
*Phase 7 completed: 2026-04-24*
