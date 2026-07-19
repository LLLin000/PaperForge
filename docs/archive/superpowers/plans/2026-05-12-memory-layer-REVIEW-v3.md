---
phase: memory-layer-plan-v3-quick-check
reviewed: 2026-05-12T09:25:08Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - docs/superpowers/plans/2026-05-12-memory-layer.md
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: issues_found
---

# Phase: Memory Layer Plan v3 Quick Check

**Reviewed:** 2026-05-12T09:25:08Z
**Depth:** standard (plan-only, cross-referenced against codebase for `--key` validation)
**Files Reviewed:** 1
**Status:** ISSUES_FOUND (1 WARNING remaining)

---

## Summary

Quick final check of the implementation plan after v3 review fixes. All 5 named issues from the prior review are **confirmed fixed**. The plan incorporates all 14 fixes from the original v1 deep review (5 CR + 5 WR + 4 IN). One new WARNING-level issue identified in the `_entry_from_row` function.

---

## Named Issue Verification

| Issue | Status | Evidence |
|-------|--------|----------|
| **N-BLKR-01**: hash query inside try block | **FIXED** | Lines 713-716 — `stored_hash_row = conn.execute(...)` is inside the `try:` block at line 708 |
| **N-BLKR-02**: NameError on `status` in memory.py | **FIXED** | Line 985 — `if result.ok:` guards access to `status` on line 986. `result` is always assigned in both try/except branches |
| **N-WRN-01**: paper_status empty fields for unresolved | **FIXED** | Line 1055 — `if data.get("resolved"):` guards detailed field printing |
| **N-INFO-01**: private `_compute_hash` renamed to `compute_hash` | **FIXED** | Line 451 — `def compute_hash(...)` (public). Line 683 — `from paperforge.memory.builder import compute_hash` |
| **N-INFO-02**: JSON decode logged with `logging.warning` | **FIXED** | Lines 762-764 — `logging.warning("Corrupted JSON in column %s for paper %s", key, ...)` |

All 5 named issues from the prior review are resolved in the plan.

---

## Original v1 Review Issue Verification (bonus)

Cross-checked all 14 issues from `2026-05-12-memory-layer-REVIEW.md`:

| Issue | Status |
|-------|--------|
| CR-01: `make_result` import | **FIXED** — line 910 imports only `PFError, PFResult` |
| CR-02: hash not checked | **FIXED** — lines 713-746 compare stored hash vs computed |
| CR-03: legacy format crash in builder | **FIXED** — lines 475-480 handle `isinstance(envelope, list)` |
| CR-04: legacy format crash in query | **FIXED** — lines 725-733 handle bare list |
| CR-05: Windows-path URI bug | **FIXED** — line 122 uses `db_path.as_posix()` |
| WR-01: `--force` flag | **FIXED** — removed from CLI parser (lines 1080-1082) |
| WR-02: ambiguous query returns full status | **FIXED** — lines 823-838 return candidates only when >1 |
| WR-03: recommended_action missing | **FIXED** — lines 846-855 compute concrete action strings |
| WR-04: zero test coverage | **REMAINS** — plan still has only 4 schema + 3 hash tests |
| WR-05: CLI dispatch pattern | **FIXED** — lines 1089-1099 use simple dispatch |
| IN-01: unused compute_health import | **FIXED** — removed from builder imports (lines 417-422) |
| IN-02: _COMMAND_REGISTRY not consumed | **REMAINS** — still present but rate-limited to INFO |
| IN-03: compute_hash .get vs direct | **FIXED** — line 452 uses `e["zotero_key"]` (direct access) |
| IN-04: fragile rstrip("_json") | **FIXED** — line 760 uses `key[:-5]` instead of `rstrip` |

---

## Warnings

### WR-V3-01: Data silently lost when JSON decode fails in `_entry_from_row`

**File:** `docs/superpowers/plans/2026-05-12-memory-layer.md:759-760`
**Issue:** When `json.loads()` raises `JSONDecodeError`, `entry.pop(key)` has already executed — the original `_json` column value is removed from the result dict and never restored. The field disappears silently from query output.

```python
# Current (plan line 759-760)
try:
    entry[key[:-5]] = json.loads(entry.pop(key))  # pop() happens BEFORE json.loads()
except json.JSONDecodeError:
    logging.warning(...)                            # original value already lost
```

**Fix:**
```python
# Pop first, then try to decode, restore on failure
raw = entry.pop(key)
try:
    entry[key[:-5]] = json.loads(raw)
except json.JSONDecodeError:
    entry[key] = raw  # keep original JSON string visible
    logging.warning(
        "Corrupted JSON in column %s for paper %s",
        key, entry.get("zotero_key", "?"),
    )
```

---

_Reviewed: 2026-05-12T09:25:08Z_
_Reviewer: VT-OS/OPENCODE (gsd-code-reviewer)_
_Depth: standard_
