# Phase 14: Shared Utilities Extraction - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 14-shared-utilities-extraction
**Areas discussed:** File structure, _JOURNAL_DB cache pattern, STANDARD_VIEW_NAMES naming

---

## File structure in _utils.py

| Option | Description | Selected |
|--------|-------------|----------|
| Grouped (Recommended) | Functions organized by category with section headers (JSON I/O, YAML, String, Journal DB) | ✓ |
| Flat | All functions alphabetically ordered, no grouping | |

**User's choice:** Grouped (Recommended)
**Notes:** 4 groups, each 3-4 functions, ~150 lines total. `load_simple_env` excluded (only in base_views.py, not duplicated).

---

## _JOURNAL_DB cache pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Keep module global (Recommended) | Same as current pattern, just moved to _utils.py. Zero behavioral change. | ✓ |
| functools.lru_cache | Replace global with `@lru_cache(maxsize=1)`. More testable. | |
| Class encapsulation | `JournalDB(vault)` class. Cleaner but overengineered for Phase 14. | |

**User's choice:** Keep module global (Recommended)
**Notes:** Cache is read-only after first load; shared state across workers is safe. No mutation concern.

---

## STANDARD_VIEW_NAMES naming

| Option | Description | Selected |
|--------|-------------|----------|
| STANDARD_VIEW_NAMES (Recommended) | Keep current name, matches existing base_views.py export | ✓ |
| _STANDARD_VIEW_NAMES | Add underscore to indicate internal module constant | |

**User's choice:** STANDARD_VIEW_NAMES (Recommended)
**Notes:** No underscore prefix.

---

## the agent's Discretion

- Exact order of functions within each category section
- Whether to use docstrings on re-export imports
- Split strategy: all 7 workers in one commit vs sequential
- Error handling in read_json/write_json (keep existing bare json.loads/json.dumps)
- Whether to inline _extract_year as module-private (keep underscore prefix)

## Deferred Ideas

- Deep-reading queue merge into _utils.py — Phase 15
- Unit tests for _utils.py functions — Phase 19
- Consistency audit for duplicate function detection — Phase 17
