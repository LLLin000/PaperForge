---
phase: agent-context-plan-review
reviewed: 2026-05-12T00:00:00Z
depth: deep
files_reviewed: 6
files_reviewed_list:
  - docs/superpowers/plans/2026-05-12-agent-context.md
  - docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md
  - paperforge/cli.py
  - paperforge/commands/__init__.py
  - paperforge/core/result.py
  - paperforge/memory/schema.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase: agent-context Plan Review

**Reviewed:** 2026-05-12
**Depth:** deep (cross-file analysis — spec vs plan vs existing CLI conventions vs schema)
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the `agent-context` implementation plan against the Phase 2-5 design spec (Feature 1), existing `cli.py` conventions, the `PFResult` contract, and the `papers` table schema. The plan follows established CLI dispatch patterns and all SQL column names correctly match the schema. However, one **BLOCKER** output-structure violation was found (collections at wrong JSON path), along with several warnings about error handling and spec fidelity.

---

## Critical Issues

### CR-01: `collections` output at wrong JSON path — spec/plan contract violation

**File:** `docs/superpowers/plans/2026-05-12-agent-context.md:121-128` and `docs/superpowers/plans/2026-05-12-agent-context.md:239-248`

**Issue:** The spec defines `collections` as a top-level key under `data`, sibling to `library`:

```json
// Spec (lines 44-47 of design spec):
"data": {
    "library": { ... },
    "collections": [ ... ],   // ← top-level under data
    "commands": { ... },
    "rules": [ ... ]
}
```

But the plan nests `collections` *inside* `library`:

```python
# Plan: get_agent_context() returns (line 121-128):
return {
    "paper_count": total,
    "domain_counts": domains,
    "lifecycle_counts": lifecycle_counts,
    "ocr_counts": ocr_counts,
    "deep_reading_counts": deep_counts,
    "collections": collections,          # ← inside library dict
}

# Plan: CLI wrapper constructs (line 239-248):
data = {
    "library": library,                  # ← library includes collections
    ...
}
# No separate "collections" key at data level!
```

Result: `data.library.collections` instead of spec's `data.collections`. Any downstream agent or plugin that follows the spec contract and accesses `data.collections` will get nothing / `undefined`.

**Fix:** Either:

**Option A (move to spec location):** Remove `collections` from `get_agent_context()` return value, and set it at the `data` level in the CLI wrapper:

```python
# In get_agent_context(), remove "collections":
return {
    "paper_count": total,
    "domain_counts": domains,
    "lifecycle_counts": lifecycle_counts,
    "ocr_counts": ocr_counts,
    "deep_reading_counts": deep_counts,
}
# In CLI run(), add collections at data level:
data = {
    "paperforge": {...},
    "library": library,
    "collections": _build_collection_tree_from_conn(vault),  # separate call
    "commands": COMMANDS,
    "rules": RULES,
}
```

**Option B (update spec):** If nesting is intentional, update the spec JSON example to show `library.collections` instead of `data.collections`. The non-json output code in the plan (line 264) already reads `lib.get("collections", [])` which matches the nested location.

---

## Warnings

### WR-01: Blanket `except Exception` silently swallows all query errors

**File:** `docs/superpowers/plans/2026-05-12-agent-context.md:129-130`

**Issue:** The `get_agent_context()` function has:

```python
try:
    ...
    return {...}
except Exception:
    return None
```

This catches *everything* — corrupt DB, permission errors, schema mismatch, disk I/O errors — and returns `None`. The caller then reports:

> "Memory database not found. Run paperforge memory build."

This message is **wrong** for non-missing-DB failures. A corrupt database or a permission error is not fixed by rebuilding the database. The real exception is lost entirely, making debugging impossible.

**Fix:** At minimum, log the exception before returning `None`. Better: distinguish between "DB missing" and "DB query failed":

```python
import logging
logger = logging.getLogger(__name__)

def get_agent_context(vault: Path) -> dict:
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return None

    conn = get_connection(db_path, read_only=True)
    try:
        ...
        return {...}
    except Exception as exc:
        logger.exception("Failed to query agent context from %s", db_path)
        return None
    finally:
        conn.close()
```

Or propagate the exception upward and let the CLI layer construct a more accurate `PFError` with `ErrorCode.INTERNAL_ERROR` and the actual error message (matching how `search.py` handles exceptions at line 62-66).

### WR-02: Docstring is misleading about return conditions

**File:** `docs/superpowers/plans/2026-05-12-agent-context.md:78-81`

**Issue:**

```python
def get_agent_context(vault: Path) -> dict:
    """Build agent bootstrap context from paperforge.db.
    
    Returns None if DB is missing.
    """
```

The docstring says "Returns None if DB is missing" but the function returns `None` on *any* exception (DB missing, corrupt, permission denied, etc.). Inaccurate docstrings mislead future maintainers.

**Fix:** Update to:

```python
"""Build agent bootstrap context from paperforge.db.

Returns None if the DB file does not exist or a query fails.
"""
```

### WR-03: Search command usage string missing `--year-to` flag

**File:** `docs/superpowers/plans/2026-05-12-agent-context.md:189-192`

**Issue:** The plan's `COMMANDS` dict lists:

```python
"search": {
    "usage": "paperforge search <query> --json [--collection NAME] [--domain NAME] [--ocr done|pending] [--year-from N] [--limit N]",
    ...
}
```

But the spec (line 54) and the actual CLI parser (`cli.py:279`) both include `[--year-to N]`. The plan omits it. The spec usage string is:

```
paperforge search <query> --json [--collection NAME] [--domain NAME] [--ocr done|pending] [--year-from N] [--year-to N] [--limit N]
```

An agent that reads the plan's command catalog may not know `--year-to` is available.

**Fix:** Add `[--year-to N]` to the search usage string in `COMMANDS`:

```python
"search": {
    "usage": "paperforge search <query> --json [--collection NAME] [--domain NAME] [--ocr done|pending] [--year-from N] [--year-to N] [--limit N]",
    "purpose": "Full-text search with optional collection/domain/lifecycle filters",
},
```

---

## Info

### IN-01: Minimal test coverage — no integration-level test

**File:** `docs/superpowers/plans/2026-05-12-agent-context.md:137-147`

**Issue:** The single test only covers the `None` return when DB is absent:

```python
def test_get_agent_context_returns_none_when_no_db():
    assert get_agent_context(Path("/nonexistent/vault")) is None
```

There are no tests for:
- Successful query of a populated DB
- Empty DB (0 papers)
- Collection tree with multi-level pipe-separated paths
- Collection tree with empty/whitespace-only paths
- Domain/lifecycle/OCR/deep-reading counts

**Fix:** Consider adding a fixture-based test using an in-memory SQLite DB with sample data.

### IN-02: Redundant `_COMMAND_REGISTRY` entry

**File:** `docs/superpowers/plans/2026-05-12-agent-context.md:290-293` and `paperforge/cli.py:431-571`

**Issue:** The plan adds `agent-context` to `_COMMAND_REGISTRY` *and* adds direct `if args.command == "agent-context"` dispatch in `cli.py`. The existing `cli.py` main() function already uses direct dispatch for most commands (`paper-status`, `search`, `context`, `dashboard`, etc.) and only uses `_COMMAND_REGISTRY` for `memory` subcommand dispatch. Adding to both is harmless but inconsistent — either use the registry or use direct dispatch, not both.

Since the plan already adds to `_COMMAND_REGISTRY`, you could use it for dispatch instead:

```python
if args.command == "agent-context":
    mod = get_command_module("agent-context")
    return mod.run(args)
```

Or keep the direct dispatch and skip `_COMMAND_REGISTRY` (matching `search`, `paper-status`, `context` patterns). Either is fine — just pick one.

---

_Reviewed: 2026-05-12_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: deep_
