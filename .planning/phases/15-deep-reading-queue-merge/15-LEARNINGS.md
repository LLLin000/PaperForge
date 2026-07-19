---
phase: 15
phase_name: "Deep Reading Queue Merge"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 6
  lessons: 2
  patterns: 3
  surprises: 0
missing_artifacts:
  - "UAT.md"
  - "VERIFICATION.md"
---

## Decisions

### scan_library_records() returns ALL analyze=true records regardless of deep_reading_status

The canonical function does not filter by deep_reading_status — it is the caller's responsibility to apply additional filters. This keeps the function pure (data acquisition only, no business logic).

**Source:** 15-01-PLAN.md (task 1, line 136-147), 15-01-SUMMARY.md (Decisions Made)

---

### scan_library_records() does NOT sort output

Sorting is deferred to callers (deep_reading.py and ld_deep.py each have different sort requirements). The canonical function returns records in filesystem order.

**Source:** 15-01-PLAN.md (task 1, line 167), 15-01-SUMMARY.md (Decisions Made)

---

### ld_deep.py uses module-level direct import from _utils.py

Since _utils.py is a leaf module (no intra-project dependencies), module-level imports from it are safe — no circular dependency risk.

**Source:** 15-01-PLAN.md (task 2, lines 267-272), 15-01-SUMMARY.md (Decisions Made)

---

### deep_reading.py retains status sync + categorization + report generation

The refactored run_deep_reading() still checks has_deep_reading_content() against actual note content and syncs frontmatter before building the queue. Only the inline scanning loop was replaced.

**Source:** 15-01-PLAN.md (task 2, lines 208-212), 15-01-SUMMARY.md (Decisions Made)

---

### OCR status lookup simplified to direct meta.json read via read_json()

Uses the same approach that ld_deep.py previously used with _read_json — direct read of meta.json and extraction of ocr_status field.

**Source:** 15-01-PLAN.md (task 1, line 163), 15-01-SUMMARY.md (Decisions Made)

---

### Regex patterns preserved from ld_deep.py for output consistency

Canonical function uses identical frontmatter extraction regex patterns from ld_deep.py (e.g., `r'^analyze:\s*(true|false)$'`) to guarantee behavioral equivalence.

**Source:** 15-01-PLAN.md (task 1, lines 158-162), 15-01-SUMMARY.md (Decisions Made)

---

## Lessons

### Module-level direct import is safe when target is a leaf module

_utils.py is a leaf module (stdlib + paperforge.config only, no paperforge.worker.* imports). This makes module-level from _utils import ... safe in any consumer without circular import risk.

**Source:** 15-01-PLAN.md (task 2), 15-01-SUMMARY.md (Decisions Made)

---

### Pure data acquisition functions simplify testing and reasoning

scan_library_records() has no side effects and no categorization logic. This separation of concerns makes it testable in isolation and predictable for all callers.

**Source:** 15-01-PLAN.md (task 1), 15-01-SUMMARY.md

---

## Patterns

### Canonical Data Acquisition Function

A single function in _utils.py that acquires data from library records with pure semantics (no side effects, no filtering, no sorting). All consumers delegate to it.

**Source:** 15-01-PLAN.md (lines 57-64), 15-01-SUMMARY.md (patterns-established)

---

### Thin-Wrapper Delegation

Consumer modules wrap the canonical function with their own caller-specific filter and sort logic. The wrapper has minimal code (~14 lines) and delegates real work to the shared function.

**Source:** 15-01-PLAN.md (task 2, lines 276-292), 15-01-SUMMARY.md (patterns-established)

---

### Re-Export with Backward Compatibility Comment

When a function moves from a worker module to _utils.py, the original location gets a short re-export comment (`# Re-exported from _utils.py for backward compatibility`) so existing importers continue working.

**Source:** 15-01-PLAN.md (task 2, lines 199-201), 15-01-SUMMARY.md

---

## Surprises

None documented. Plan executed exactly as written with zero deviations.

**Source:** 15-01-SUMMARY.md (Deviations from Plan)
