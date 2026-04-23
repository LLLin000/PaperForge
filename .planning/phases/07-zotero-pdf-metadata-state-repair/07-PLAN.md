# Phase 7 Implementation Plan — Zotero PDF, Metadata, And State Repair

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Fix PDF path resolution for BBT bare paths, validate OCR meta before reading, add `paperforge repair` command detecting three-way state divergence.

**Architecture:** Three independent fixes: (1) normalize BBT attachment paths in `load_export_rows()`, (2) call `validate_ocr_meta()` before using `ocr_status` in `run_deep_reading()`, (3) add `run_repair()` function + CLI subcommand.

**Tech Stack:** Python 3.11+, `literature_pipeline.py` (3285 lines), `pdf_resolver.py` (116 lines), `ocr_diagnostics.py` (256 lines)

---

## File Map

| File | Role |
|------|------|
| `pipeline/worker/scripts/literature_pipeline.py` | Core worker logic — all three fixes live here |
| `paperforge_lite/cli.py` | CLI dispatch — add `repair` subcommand |
| `paperforge_lite/pdf_resolver.py` | PDF resolution utilities — no changes needed |
| `tests/test_pdf_resolver.py` | PDF resolver unit tests |

---

## Tasks

### Task 1: Fix BBT PDF path normalization in `load_export_rows()`

**Files:**
- Modify: `pipeline/worker/scripts/literature_pipeline.py:744-750`

**Current code (line 747-749):**
```python
attachment_path = attachment.get('path', '')
content_type = 'application/pdf' if str(attachment_path).lower().endswith('.pdf') else ''
attachments.append({'path': attachment_path, 'contentType': content_type})
```

**Problem:** BBT exports `KEY/KEY.pdf` (bare format). `resolve_pdf_path()` expects either `storage:KEY/KEY.pdf` (for storage-relative branch at line 60) or an absolute path. Bare `KEY/KEY.pdf` fails both branches.

**Fix — normalize bare `KEY/KEY.pdf` to `storage:KEY/KEY.pdf`:**
```python
attachment_path = attachment.get('path', '')
if attachment_path and not attachment_path.startswith("storage:") and not Path(attachment_path).is_absolute():
    attachment_path = "storage:" + attachment_path
content_type = 'application/pdf' if str(attachment_path).lower().endswith('.pdf') else ''
attachments.append({'path': attachment_path, 'contentType': content_type})
```

- [ ] **Step 1: Write failing test**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Apply fix to line 747-749**
- [ ] **Step 4: Run tests to verify they pass**
- [ ] **Step 5: Commit**

---

### Task 2: Call `validate_ocr_meta()` in `run_deep_reading()` before using `ocr_status`

**Files:**
- Modify: `pipeline/worker/scripts/literature_pipeline.py:2788-2795`

**Current code (lines 2788-2795):**
```python
if meta_path.exists():
    try:
        meta = read_json(meta_path)
        ocr_status = str(meta.get('ocr_status', 'pending')).strip().lower()
    except Exception:
        pass
```

**Problem:** `validate_ocr_meta()` checks 7 conditions (file existence, size, page markers) before confirming `done`, but `run_deep_reading()` bypasses it. Result: `meta.json` with `ocr_status: done` but missing files → paper appears ready but isn't.

Also: `validate_ocr_meta()` returns `done_incomplete` as a status, but `run_deep_reading()` line 2805 only checks `ocr_status == 'done'` for ready queue. `done_incomplete` would be treated as blocked.

**Fix:**
```python
if meta_path.exists():
    try:
        meta = read_json(meta_path)
        validated_status, error_msg = validate_ocr_meta(paths, meta)
        ocr_status = validated_status
    except Exception:
        pass
```

**Also fix ready queue check (line 2805):**
`done_incomplete` should be treated as blocked (needs re-OCR), not ready and not purely waiting. Change line 2805 from:
```python
ready = [q for q in pending_queue if q['ocr_status'] == 'done']
```
to:
```python
ready = [q for q in pending_queue if q['ocr_status'] == 'done' and not q.get('_ocr_error')]
```

- [ ] **Step 1: Write failing test for `done_incomplete` misclassification**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Apply fix — replace lines 2792-2793 with `validate_ocr_meta()` call**
- [ ] **Step 4: Run tests to verify they pass**
- [ ] **Step 5: Commit**

---

### Task 3: Add `run_repair()` function

**Files:**
- Modify: `pipeline/worker/scripts/literature_pipeline.py` — add new `run_repair()` function
- Test: `tests/test_repair.py` — new test file

**New function `run_repair(vault: Path, paths: dict, verbose: bool = False) -> dict`:**

Scans all domains for three-way state divergence:
1. Read `library_record.md` frontmatter `ocr_status`
2. Read `formal_note.md` frontmatter `ocr_status`
3. Read `meta.json` `ocr_status` after `validate_ocr_meta()`
4. Report contradictions

Returns dict:
```python
{
    "scanned": int,
    "divergent": list[dict],  # items with contradictions
    "fixed": int,
    "errors": list[dict],
}
```

Detection rules:
- `done_incomplete` from `validate_ocr_meta()` → treat as blocked (needs re-OCR)
- If `library_record.ocr_status` = `done` but `meta.ocr_status` = `pending/processing` → divergence
- If `formal_note.ocr_status` = `done` but `meta.json` missing or invalid → divergence
- If `library_record.ocr_status` != `meta.ocr_status` (post-validation) → divergence

Repair actions (controlled by `fix: bool` parameter):
- If meta files missing: set all three to `pending`, set `do_ocr: true`
- If meta incomplete: set all three to `pending`, set `do_ocr: true`
- If library_record says done but meta says pending: set library_record to `pending`

- [ ] **Step 1: Write failing test for `run_repair()`**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `run_repair()` function**
- [ ] **Step 4: Run tests to verify they pass**
- [ ] **Step 5: Commit**

---

### Task 4: Add `repair` subcommand to CLI

**Files:**
- Modify: `paperforge_lite/cli.py` — add `repair` to dispatch

**New command:**
```
paperforge repair [--verbose] [--fix]
```

- `--verbose`: Show detailed divergence report
- `--fix`: Actually apply repairs (default is dry-run)

- [ ] **Step 1: Add `repair` to CLI dispatch**
- [ ] **Step 2: Test CLI dispatch**
- [ ] **Step 3: Commit**

---

### Task 5: Update AGENTS.md

**Files:**
- Modify: `AGENTS.md` — document `paperforge repair` command

- [ ] **Step 1: Add `paperforge repair` to command reference**
- [ ] **Step 2: Commit**

---

## Test Plan

| Test | File | What it covers |
|------|------|---------------|
| `test_bbt_path_normalization` | new in `tests/test_pdf_resolver.py` | BBT bare `KEY/KEY.pdf` → `storage:KEY/KEY.pdf` |
| `test_deep_reading_done_incomplete_blocked` | new in `tests/test_smoke.py` | `done_incomplete` misclassified as ready |
| `test_repair_detects_divergence` | new `tests/test_repair.py` | three-way divergence detection |
| `test_repair_dry_run_vs_fix` | new `tests/test_repair.py` | dry-run vs actual fix |
| `test_repair_no_divergence` | new `tests/test_repair.py` | clean state → no divergence reported |

---

## Verification

After all tasks:
1. Run `pytest tests/test_pdf_resolver.py tests/test_smoke.py -v` — all PASS
2. Run `python -m paperforge_lite repair --verbose` — confirm no crashes
3. Confirm `paperforge repair` appears in `paperforge --help`
