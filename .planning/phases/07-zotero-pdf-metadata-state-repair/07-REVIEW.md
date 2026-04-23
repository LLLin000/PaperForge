# Phase 7 — Task 3 Code Review: `run_repair()`

**Reviewed:** 2026-04-24
**Depth:** standard
**Files Reviewed:** 2
  - `pipeline/worker/scripts/literature_pipeline.py` (lines 2847-3001)
  - `tests/test_repair.py` (367 lines)

---

## Summary

Task 3 (`run_repair()`) is substantially implemented and tested. The three-way divergence detection logic is correct and the test suite is thorough (20 tests, all passing). Two significant issues were found: a potential NameError from `validated_error` being referenced outside its try block, and dead code (unused `domain_lookup`). The CLI wiring for `repair` is not present — that is Task 4 (not in scope), so the function cannot be invoked via `paperforge repair` yet, but the core function is complete.

---

## Strengths

- **Correct divergence logic:** All four detection cases from the plan are implemented (lines 2905-2916):
  1. `done_incomplete` from `validate_ocr_meta()` — divergence
  2. `library_record=done` but `meta=pending/processing/missing` — divergence
  3. `formal_note=done` but `meta.json` missing/invalid — divergence
  4. `library_record != meta.post_validation` — divergence

- **Comprehensive test suite:** 20 tests covering scan-only mode, fix mode, return structure, and edge cases (nopdf, multiple domains, verbose output). Helper factories `_write_library_record`, `_write_formal_note`, `_write_meta` make test cases readable.

- **Clean function signature:** `(vault, paths, verbose=False, fix=False) -> dict` — idempotent dry-run by default, fix requires explicit flag.

- **Proper use of existing helpers:** `validate_ocr_meta()`, `update_frontmatter_field()`, `_resolve_formal_note_path()`, `load_domain_config()` are all reused correctly.

- **Unicode-safe file I/O:** All `read_text`/`write_text` use `encoding='utf-8'`.

---

## Issues

### Important — Potential NameError: `validated_error` may be unbound

**File:** `pipeline/worker/scripts/literature_pipeline.py:2907`

```python
if meta_validated_status == 'done_incomplete':
    is_divergent = True
    div_reason = f"meta validation: done_incomplete ({validated_error})"
```

`validated_error` is only assigned inside the `try` block at line 2892:

```python
validated_status, validated_error = validate_ocr_meta(paths, meta)
```

If `meta_path.exists()` is True but the `try` block raises an exception before the assignment, `validated_error` is never defined. The outer `except` at line 2900 catches it and appends to `result['errors']`, but `validated_error` could still be unbound when used at line 2907 in the `elif` chain that follows.

**Fix:**
```python
if meta_validated_status == 'done_incomplete':
    is_divergent = True
    div_reason = f"meta validation: done_incomplete ({validated_error})" if 'validated_error' in locals() else "meta validation: done_incomplete"
```

Or initialize `validated_error = ""` before the try block.

---

### Minor — Dead code: unused `domain_lookup`

**File:** `pipeline/worker/scripts/literature_pipeline.py:2860`

```python
domain_lookup = {entry['export_file']: entry['domain'] for entry in config['domains']}
```

`domain_lookup` is computed but never used anywhere in `run_repair()`. It was likely intended for domain-to-export mapping but the function gets domain directly from `record_path.parent.name` (line 2872).

**Fix:** Remove line 2860.

---

### Minor — Code duplication in fix branches

**File:** `pipeline/worker/scripts/literature_pipeline.py:2929-2994`

Two fix branches are nearly identical (lines 2934-2964 and 2965-2994):

```python
# Branch 1: meta_ocr_status is None or meta_validated_status == 'done_incomplete'
new_status = 'pending'
new_record_text = update_frontmatter_field(record_text, 'ocr_status', new_status)
# ... sets do_ocr: true
# [identical logic repeated for branch 2]
```

Both branches: (a) update library_record ocr_status, (b) update formal_note ocr_status, (c) update meta.json ocr_status, (d) set do_ocr: true. Only the condition differs.

**Suggestion:** Extract into a `_repair_set_pending(record_text, record_path, note_path, meta_path)` helper, or at minimum refactor the shared logic to reduce duplication.

---

### Minor — Nested filesystem scan: `_resolve_formal_note_path` does unindexed rglob

**File:** `pipeline/worker/scripts/literature_pipeline.py:2877` (called inside loop at line 2737)

For each library record, `_resolve_formal_note_path` does:

```python
for note_path in domain_dir.rglob('*.md'):   # line 2737
    if frontmatter_pattern.search(text):     # line 2742
```

If a domain has many notes, this is O(n*m) per record. With 100 records and 100 notes each, that's 10,000 file reads.

Not a bug per se (the plan doesn't mention caching), but worth noting as a scaling concern for large vaults.

---

### Minor — Fix logic sets `do_ocr: true` beyond plan specification

**File:** `pipeline/worker/scripts/literature_pipeline.py:2958-2964`

The plan says: *"If meta files missing: set all three to `pending`, set `do_ocr: true`"* (line 136-137).

This is implemented correctly for the first fix branch (lines 2934-2964). However, the second fix branch (lines 2965-2994, triggered when `lib_ocr_status == 'done' and meta_ocr_status in ('pending', 'processing')`) also sets `do_ocr: true` (lines 2988-2994), which is not in the plan's repair actions list.

The plan specifies three repair scenarios (lines 135-138):
1. Missing meta files → set pending + do_ocr
2. Incomplete meta → set pending + do_ocr  
3. library done but meta pending → set library to pending only

The implementation adds `do_ocr: true` to scenario 3 as well. This is likely harmless (setting do_ocr alongside the status reset makes sense to retrigger OCR), but deviates from the plan.

---

## Assessment

| Criterion | Status |
|-----------|--------|
| One clear responsibility per file | Pass |
| Units decomposed for independent testing | Pass |
| Follows plan file structure | Pass |
| New file is not excessively large | Pass (155 lines is reasonable) |
| Function signature clean and documented | Pass |
| Performance concerns (scanning all domains) | Acceptable — rglob is standard, no evidence of excessive I/O |

**Critical issues:** 1 (NameError risk)
**Important issues:** 0
**Minor issues:** 4 (dead code, duplication, nested scan, do_ocr deviation)

---

## Verdict

**Status:** issues_found

The `run_repair()` function is functionally correct and well-tested. The `validated_error` NameError risk should be fixed before this is considered ready. The other issues are minor but should be addressed.

**Recommended fixes (in order of priority):**

1. **Fix potential NameError** at line 2907 — initialize `validated_error` before the try block, or guard the reference.
2. **Remove dead code** — delete `domain_lookup` at line 2860.
3. **Consider refactoring** the duplicated fix branches if the function grows further.

---
_Reviewed: 2026-04-24_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_