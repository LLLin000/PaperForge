# Phase 47: Library-Records Deprecation Cleanup — Verification Report

**Date:** 2026-05-07
**Plan 47-001 executed:** Yes
**Plan 47-002 executed:** Yes

---

## Verification Status: PASSED (with notes)

---

## Plan 47-001: Python Source Cleanup

### LEGACY-01 — status.py stale-record detection + output label

| Check | Status |
|-------|--------|
| `status.py` compiles without error | PASS |
| Stale-record detection uses `paths.get("control")` (not `library_records`) | PASS |
| Stale-record message: "stale record(s) found in control directory" | PASS |
| Fix instruction: "Review and remove stale files from the control directory" | PASS |
| Comment updated to "Stale record detection in control directory" | PASS |
| Output label: `- formal_notes:` (not `- library_records:`) | PASS |
| Zero `library_records` hits in file | PASS |

### LEGACY-02 — sync.py dead code removal

| Check | Status |
|-------|--------|
| `sync.py` compiles without error | PASS |
| `parse_existing_library_record()` function removed | PASS |
| `record_path` construction (`paths["library_records"]`) removed | PASS |
| `parse_existing_library_record()` call removed | PASS |
| Zero `parse_existing_library_record` references remain | PASS |

### LEGACY-03 — ld_deep.py records key removal

| Check | Status |
|-------|--------|
| `ld_deep.py` compiles without error | PASS |
| Docstring updated to "Returns ocr, literature keys" (no "records") | PASS |
| `"records": shared["library_records"]` line removed from return dict | PASS |
| Zero `"records"` key in return dict | PASS |
| Tests updated to not expect `records` key | PASS |

### LEGACY-04 — repair.py docstring

| Check | Status |
|-------|--------|
| `repair.py` compiles without error | PASS |
| Docstring reads "Scan formal literature notes" | PASS |

### LEGACY-07 — hardcoded Literature/ references

| Check | Status |
|-------|--------|
| `discussion.py` docstring uses `{literature_dir}/` | PASS |
| `sync.py` `migrate_to_workspace()` docstring uses `<literature_dir>/` (4 references) | PASS |
| `sync.py` print label uses "in literature" (not "in Literature/") | PASS |

### Comprehensive `grep -n "library_records"` across all 5 production files

```
paperforge/worker/status.py: (no hits)
paperforge/worker/sync.py: (no hits)
paperforge/worker/repair.py: (no hits)
paperforge/skills/literature-qa/scripts/ld_deep.py: (no hits)
paperforge/worker/discussion.py: (no hits)
```

**Result: PASS — zero hits**

---

## Plan 47-002: Documentation Cleanup

### LEGACY-05 — setup_wizard.py post-install

| Check | Status |
|-------|--------|
| Step 3 heading: "同步 Zotero 并生成正式笔记" (no "文献") | PASS |
| Single `paperforge sync` command shown | PASS |
| No two-phase `--selection`/`--index` code block | PASS |
| Auto-completion description included | PASS |
| Deprecation notice for `--selection`/`--index` included (as footnote) | PASS |
| Zero `library-records` references in file | PASS |

### LEGACY-06 — Command file library-records purge

| Check | Status |
|-------|--------|
| `grep -r "library.record" command/` — zero hits | PASS |
| `grep -r "library.record" paperforge/command_files/` — zero hits | PASS |
| All 10 files valid UTF-8 Markdown | PASS |
| All files describe formal-note-only workflows | PASS |

---

## Test Suite: `pytest tests/ -q --tb=short`

| Metric | Count |
|--------|-------|
| **Total tests** | 482 |
| **Passed** | 478 |
| **Skipped** | 2 |
| **Failed (pre-existing, unrelated)** | 2 |

### Pre-existing Failures (not caused by this phase)

1. **`test_retry_exhaustion_becomes_error`** — expects `"error"` but gets `"blocked"` (OCR state machine)
2. **`test_full_cycle_from_pending_to_done`** — expects `"done"` but gets `"queued"` (OCR state machine)

Both are in `tests/test_ocr_state_machine.py` and relate to OCR state transitions. They were present before this phase's changes and are unrelated to library-records deprecation.

---

## Summary

**Verdict: PASSED** — All LEGACY-01 through LEGACY-07 requirements verified. Zero library-records references remain in production code, documentation, or user-facing labels. All Python files compile. 478/482 tests pass (2 pre-existing OCR test failures unrelated to this phase).
