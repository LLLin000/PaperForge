---
phase: research-memory-core
reviewed: 2026-05-14T12:00:00Z
depth: deep
files_reviewed: 2
files_reviewed_list:
  - docs/superpowers/plans/2026-05-14-research-memory-core.md
  - docs/superpowers/plans/2026-05-14-research-memory-core-REVIEW.md
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Re-Review: Research Memory Core (post-critical-fix)

**Reviewed:** 2026-05-14 (second pass)
**Depth:** deep (cross-file analysis against paperforge/core/, paperforge/memory/)
**Prior Review:** `2026-05-14-research-memory-core-REVIEW.md` (5 critical, 6 warning, 4 info)
**Status:** issues_found — 3 new warnings, 0 critical; all 11 prior issues verified fixed

---

## Summary

The updated plan has successfully addressed all 5 BLOCKER-level (critical) issues and all 6 WARNING-level issues from the prior review. The fixes are substantive: `ErrorCode.INVALID_INPUT` replaced with `VALIDATION_ERROR`, `--json`/`--payload` argument split corrected, hardcoded paths replaced with `paperforge_paths()`, schema version bumped to 2, stale `reading_log_v2.py` reference removed, and all six warning fixes applied (correction-note write path, input validation, JSON error logging, paper_events clearing, methodology placement documented, secure ID generation).

However, three NEW warnings were discovered — two are consistency gaps where the CR-02 fix was applied incompletely (stale documentation), and one is a data-loss design gap (correction notes lost on rebuild). None are blockers but should be addressed before implementation.

---

## Prior Fix Verification (PASS/FAIL per issue)

| Issue ID | Description | Status | Evidence |
|----------|-------------|--------|----------|
| **CR-01** | `ErrorCode.INVALID_INPUT` → `VALIDATION_ERROR` | **PASS** | Plan uses `ErrorCode.VALIDATION_ERROR` at lines 901, 908, 924, 936, 957; zero `INVALID_INPUT` references |
| **CR-02** | `--json` rename → `--payload`, boolean `--json` flag | **PASS*** | Code blocks fixed (lines 788-795); see NEW-W01 for doc gaps |
| **CR-03** | Hardcoded paths → `paperforge_paths()` | **PASS** | Both `_render_reading_log_md` (lines 533-534) and `_render_project_log_md` (lines 880-881) use config-derived paths |
| **CR-04** | `CURRENT_SCHEMA_VERSION` bump | **PASS** | Line 148: `CURRENT_SCHEMA_VERSION = 2` with comment |
| **CR-05** | Stale `reading_log_v2.py` removed | **PASS** | "New files" section (lines 61-64) lists only 3 files; zero `reading_log_v2` references |
| **WR-01** | No `correction_note` write function | **PASS** | Task 3 Step 6 (lines 550-588) adds `--correct`/`--correction`/`--reason` CLI args + INSERT logic |
| **WR-02** | No data validation in `append_reading_note` | **PASS** | Lines 230-233: `paper_id` and `excerpt` empty checks with error dict return |
| **WR-03** | Silent JSON decode errors | **PASS** | Lines 277-280, 340-343: `logger.warning()` added in catch blocks |
| **WR-04** | `paper_events` not cleared on rebuild | **PASS** | Task 6 Step 2 line 1078: `conn.execute("DELETE FROM paper_events;")` added |
| **WR-05** | `METHODOLOGY_COMPACT.md` not discoverable | **PASS** | Task 7 (line 1099): documents it's intentionally outside `archive/`, with rationale |
| **WR-06** | Weak UUID truncation | **PASS** | Lines 237, 304: `secrets.token_hex(4)` replaces `str(uuid.uuid4())[:6]` |

### CR-02 Detail (* qualified PASS)

The code blocks in Task 5 are correctly fixed — `--payload` accepts the JSON string and `--json` is a proper `store_true` boolean. However, two documentation sections were NOT updated (see NEW-W01 below). The code is correct; the surrounding specification text is stale.

---

## New Issues

### NEW-W01: Interface contract and smoke test retain old `--json '<payload>'` syntax

**File:** `docs/superpowers/plans/2026-05-14-research-memory-core.md`
**Lines:** 46, 1170
**Severity:** WARNING
**Issue:** The CR-02 fix renamed the payload argument from `--json` to `--payload` in the Task 5 code blocks, but two documentation sections still reference the old syntax:

1. **Line 46** — Interface contract section:
   ```
   paperforge project-log --write --json '<payload>' --vault $VAULT
   ```

2. **Line 1170** — Smoke test command:
   ```bash
   --json '{"date":"2026-05-14","type":"note","title":"test"}' \
   ```

An implementer following the interface contract or smoke test would use `--json '<...>'` which now means "output as JSON" (boolean flag), not "JSON payload". The command would either error (boolean flag receiving a string value) or behave unexpectedly.

**Fix:**
```markdown
# Line 46: Change to:
paperforge project-log --write --payload '<json_payload>' --vault $VAULT

# Line 1170: Change to:
    --payload '{"date":"2026-05-14","type":"note","title":"test"}' \
```

---

### NEW-W02: `correction_note` data has no JSONL backing — permanently lost on DB rebuild

**File:** `docs/superpowers/plans/2026-05-14-research-memory-core.md`
**Lines:** 552-581 (correction write path), 1078 (DELETE FROM paper_events)
**Severity:** WARNING
**Issue:** Task 3 Step 6 writes `correction_note` events directly to `paper_events` (line 573-576). Task 6 clears `paper_events` on rebuild (`DELETE FROM paper_events;`, line 1078). However, unlike reading notes (which are dual-written to JSONL + paper_events), correction notes have **no JSONL equivalent** — they exist only in `paper_events`. On rebuild, all correction history is permanently lost.

Furthermore, the existing `drop_all_tables(conn)` in `builder.py:79` already drops `paper_events` when the schema version changes (since `paper_events` is in `ALL_TABLES`). The plan's added `DELETE FROM paper_events` handles same-version rebuilds, making the data-loss path even broader.

**Fix (Option A — preferred):** Mirror the dual-write pattern used for reading notes. When a correction is written, also append to a `corrections.jsonl` file. Add an `_import_corrections()` function in `builder.py` that restores them on rebuild.

**Fix (Option B — simpler):** Scope the `DELETE FROM paper_events` to exclude `correction_note` rows:
```python
conn.execute("DELETE FROM paper_events WHERE event_type != 'correction_note';")
```

**Fix (Option C):** Document that correction notes are ephemeral and lost on rebuild, and ensure the `paper-context` command's `recheck_targets` warning makes this acceptable.

---

### NEW-W03: `append_reading_note()` failure silently ignored — PFResult always reports success

**File:** `docs/superpowers/plans/2026-05-14-research-memory-core.md`
**Lines:** 432-466 (Task 3 Step 3)
**Severity:** WARNING
**Issue:** In the `reading_log.py` write section, the code calls `append_reading_note()` which returns `{ok, id, path}` or `{ok: False, error: str}`. However, the surrounding logic hardcodes `ok = True` (line 460) without checking the return value:

```python
result = append_reading_note(vault, args.paper_id, ...)
# ... dual-write to paper_events ...

ok = True                              # Always True — ignores result["ok"]
result_obj = PFResult(
    ok=ok,
    command="reading-log",
    version=PF_VERSION,
    data={"written": ok, "id": result.get("id")},  # "id" is None on failure
)
```

If JSONL write fails (disk full, permission error), `result["ok"]` is `False`, `result["id"]` is `None`, but the PFResult contract reports `{ok: true, data: {written: true, id: null}}`. The CLI consumer has no way to detect the failure.

**Fix:**
```python
result = append_reading_note(vault, args.paper_id, ...)
if not result.get("ok"):
    result_obj = PFResult(
        ok=False, command="reading-log", version=PF_VERSION,
        error=PFError(code=ErrorCode.INTERNAL_ERROR,
                       message=result.get("error", "Failed to write reading note")),
    )
    # ... output and return
# Continue with paper_events write only if JSONL succeeded
write_reading_note(...)
```

---

## Info (Non-blocking observations)

### NEW-IN01: Duplicate step numbering in Task 3

**File:** `docs/superpowers/plans/2026-05-14-research-memory-core.md`
**Lines:** 378, 389, 412, 470, 550, 590, 607
**Severity:** INFO
**Issue:** Task 3 step numbering jumps: Step 1 (l.378), Step 2 (l.389), Step 3 (l.412), Step 4 (l.470), Step 6 (l.550), Step 7 (l.590), Step 6 (l.607, again). There is no Step 5, and two different sections are both labeled "Step 6". This could confuse implementers tracking progress.
**Fix:** Renumber sequentially: Step 5 for correction write support (l.550), Step 6 for render dispatch (l.590), Step 7 for commit (l.607).

### NEW-IN02: Misleading error code in `paper_context.py`

**File:** `docs/superpowers/plans/2026-05-14-research-memory-core.md`
**Line:** 736
**Severity:** INFO
**Issue:** The `paper_context.py` `run()` function uses `ErrorCode.PATH_NOT_FOUND` when no paper is found in the database for a given zotero_key. `PATH_NOT_FOUND` (defined in `errors.py:24` under "Config / Vault") is semantically meant for filesystem or vault path lookup failures, not database record lookups. Using the wrong error code category could mislead downstream consumers (plugin UI generating fix-it guidance for a "missing path" when the real issue is a missing paper key).
**Fix:** Use `ErrorCode.VALIDATION_ERROR` or add a purpose-specific code like `PAPER_NOT_FOUND`:
```python
error=PFError(code=ErrorCode.VALIDATION_ERROR,
              message=f"No paper found for key: {key}")
```

---

## Task-by-Task Re-Assessment

| Task | Prior | Current | Notes |
|------|-------|---------|-------|
| 1: DB Schema | PASS* | **PASS** | Schema version bumped, new tables registered |
| 2: JSONL Storage | PASS* | **PASS** | Validation added, JSON errors logged, secure IDs |
| 3: Reading-Log CLI | PASS* | **PASS** | All prior issues fixed; NEW-W03 (unchecked result) to address |
| 4: Paper-Context CLI | PASS* | **PASS** | Correction read path now has matching write path; NEW-IN02 minor |
| 5: Project-Log CLI | **FAIL** → **PASS** | CR-01/CR-02/CR-03 all fixed; NEW-W01 (stale spec docs) to address |
| 6: DB Builder | PASS* | **PASS** | paper_events cleared; NEW-W02 (correction loss on rebuild) to address |
| 7: METHODOLOGY_COMPACT | PASS* | **PASS** | Placement documented as intentional |
| 8: Integration | PASS | **PASS** | Smoke test needs --payload fix (NEW-W01) |

---

## Cross-File Consistency Check

| Check | Result |
|-------|--------|
| `paperforge_paths()` used consistently across render functions | PASS |
| `ErrorCode` values all exist in `errors.py` enum | PASS (verified PATH_NOT_FOUND, VALIDATION_ERROR both exist) |
| `ALL_TABLES` includes `reading_log` and `project_log` | PASS (line 142) |
| `ensure_schema()` creates both new tables | PASS (lines 135-136) |
| `builder.py` delete/add order correct (DELETE before INSERT) | PASS |
| Interface contract matches CLI implementation | FAIL — line 46 uses `--json` not `--payload` |
| Smoke test commands match CLI implementation | FAIL — line 1170 uses `--json` not `--payload` |
| `paper_events` lifecycle documented | PARTIAL — cleared on rebuild but correction notes not restored |

---

## Dependency Graph: Still Verified

```
Task 2 (JSONL) → Tasks 3, 4, 5, 6
Task 7 is independent
Task 8 is integration (depends on all)
```

No circular dependencies introduced.

---

_Reviewed: 2026-05-14_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: deep_
_Prior fixes verified: 11/11 PASS (CR-01 through CR-05, WR-01 through WR-06)_
_New issues found: 3 warnings, 2 info_
