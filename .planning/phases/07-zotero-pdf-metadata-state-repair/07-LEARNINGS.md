---
phase: 07
phase_name: "Zotero PDF Metadata State Repair"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 5
  lessons: 5
  patterns: 3
  surprises: 3
missing_artifacts:
  - "VERIFICATION.md"
  - "UAT.md"
---

## Decisions

### D-01: `validate_ocr_meta()` must be called before using `ocr_status` in deep reading
`run_deep_reading()` was reading `ocr_status` directly from `meta.json` without validation. Changed to call `validate_ocr_meta()` which checks 7 conditions (file existence, size, page markers) before confirming status.

**Rationale/Context:** `meta.json` with `ocr_status: done` but missing/corrupt files would falsely report papers as ready for deep reading.  
**Source:** 07-PLAN.md (Task 2)

### D-02: `done_incomplete` treated as blocked (not ready)
`validate_ocr_meta()` can return `done_incomplete`, which should be treated as blocked (needs re-OCR) rather than ready or waiting.

**Rationale/Context:** Deep reading queue had a binary filter (`ocr_status == 'done'`) that didn't account for the `done_incomplete` state.  
**Source:** 07-PLAN.md (Task 2)

### D-03: Repair command defaults to dry-run with `--fix` flag
`paperforge repair` scans for state divergence by default and does nothing. `--fix` flag applies actual changes to divergent records.

**Rationale/Context:** Destructive state changes should be opt-in. Users scan, review, then apply.  
**Source:** 07-PLAN.md (Task 3, 4)

### D-04: Three-way state comparison for detecting configuration drift
Repair compares three sources: library_record frontmatter, formal_note frontmatter, and meta.json (post-validation).

**Rationale/Context:** State can diverge because different processes write to different files independently. Three-way comparison catches all inconsistency modes.  
**Source:** 07-PLAN.md (Task 3)

### D-05: BBT bare path normalization deferred
Normalizing bare `KEY/KEY.pdf` to `storage:KEY/KEY.pdf` in `load_export_rows()` was not implemented. The code change was deferred in favor of state repair work.

**Rationale/Context:** `run_repair()` and OCR meta validation address active state corruption. BBT bare path handling has no concrete reproduction case.  
**Source:** 07-SUMMARY.md (Task 1 — Deferred)

---

## Lessons

### L-01: Deep-reading bypassed OCR validation entirely
`run_deep_reading()` read `ocr_status` directly from `meta.json` without calling `validate_ocr_meta()`, even though that function existed and checked 7 conditions.

**Rationale/Context:** The validation function was written but not wired into the queue logic. Two independently developed features weren't connected.  
**Source:** 07-PLAN.md (Task 2)

### L-02: Uninitialized variables in try/except blocks cause NameError
The `validated_error` variable was referenced outside a try block where it was assigned, causing a potential `NameError` if the assignment didn't execute.

**Rationale/Context:** Fix by initializing `validated_status` and `validated_error` before the try block.  
**Source:** 07-SUMMARY.md (Known Issues)

### L-03: Dead code accumulates without detection
`domain_lookup` was discovered and removed during review — dead code that was previously unreachable.

**Rationale/Context:** No automated dead code detection was in place. Discovered during manual review.  
**Source:** 07-SUMMARY.md (Known Issues)

### L-04: Edge cases in state comparison (None meta_ocr_status)
Case 3 (where `meta_ocr_status` is `None`) needed special handling added during implementation. The initial implementation assumed meta always had a valid status.

**Rationale/Context:** Missing/incomplete meta.json leads to `None` status, which wasn't accounted for in comparison logic.  
**Source:** 07-SUMMARY.md (Known Issues)

### L-05: `O(n*m)` scan scales poorly with vault size
The `_resolve_formal_note_path()` function uses per-record `rglob`, which scales poorly with large vaults.

**Rationale/Context:** Acceptable for current vault sizes but would become a bottleneck with hundreds of records.  
**Source:** 07-SUMMARY.md (Known Issues)

---

## Patterns

### P-01: Three-way state comparison for configuration drift
Compare three data sources (library_record, formal_note, meta.json) to detect inconsistent states.

**When to use:** When multiple independent processes write to different files and state must remain synchronized.  
**Source:** 07-PLAN.md (Task 3)

### P-02: Dry-run default with explicit fix flag
Commands that modify state do nothing by default (scan/display). Users must opt in with `--fix` to apply changes.

**When to use:** Any command that could modify user data. Provides safety while allowing repair.  
**Source:** 07-PLAN.md (Task 3, 4)

### P-03: Test-first for defect fixes
Write a failing test that reproduces the bug, then implement the fix, then verify the test passes.

**When to use:** For any bug fix where the expected behavior is clearly defined. Prevents regression and proves the fix works.  
**Source:** 07-PLAN.md (all tasks)

---

## Surprises

### S-01: Deep-reading was reporting papers as ready when OCR files were missing/corrupt
`run_deep_reading()` trusted `meta.json` `ocr_status: done` without validating that the actual OCR files existed and were complete. This created a false-ready state.

**Impact:** High — users would attempt deep reading on papers without valid OCR data.  
**Source:** 07-PLAN.md (Task 2) / 07-SUMMARY.md

### S-02: `done_incomplete` status existed but was unhandled in queue logic
`validate_ocr_meta()` could return `done_incomplete`, but `run_deep_reading()` only checked `ocr_status == 'done'`, causing `done_incomplete` papers to silently fall through.

**Impact:** Medium — papers with incomplete OCR were neither ready nor visibly blocked, causing confusion.  
**Source:** 07-PLAN.md (Task 2)

### S-03: BBT bare path handling was lower priority than expected
The BBT bare `KEY/KEY.pdf` path normalization was deferred because no concrete reproduction case existed, despite being identified in the plan.

**Impact:** Low — workaround exists (configure BBT with `storage:` prefix). Tracked for future phase.  
**Source:** 07-SUMMARY.md (Task 1 — Deferred)
