---
phase: memory-layer-plan-review
reviewed: 2026-05-12T18:30:00Z
depth: deep
files_reviewed: 9
files_reviewed_list:
  - docs/superpowers/plans/2026-05-12-memory-layer.md
  - docs/superpowers/specs/2026-05-12-memory-layer-design.md
  - paperforge/config.py
  - paperforge/cli.py
  - paperforge/commands/__init__.py
  - paperforge/core/result.py
  - paperforge/core/errors.py
  - paperforge/worker/asset_state.py
  - paperforge/worker/asset_index.py
findings:
  critical: 5
  warning: 5
  info: 4
  total: 14
status: issues_found
---

# Phase: Memory Layer Plan Review

**Reviewed:** 2026-05-12T18:30:00Z
**Depth:** deep (cross-file analysis with import graph tracing)
**Files Reviewed:** 9
**Status:** ISSUES_FOUND

## Verdict: ISSUES_FOUND

5 BLOCKER, 5 WARNING, 4 INFO issues detected. Plan must not be executed until BLOCKER items are resolved.

---

## Summary

The plan maps spec requirements to tasks with reasonable granularity, and the overall architecture (SQLite under `paperforge/memory/`, derived from `formal-library.json`, PFResult-enveloped CLI) is sound. However, the cross-file trace against the actual codebase reveals **five BLOCKER defects** — a non-existent import, a missing spec-critical hash check, two crash-on-legacy-format scenarios, and a Windows-path URI bug. Five WARNING-level issues include an unimplemented `--force` flag, a behavioral divergence from spec for ambiguous queries, a missing `recommended_action` field, near-zero test coverage for business logic, and an inconsistent CLI dispatch pattern.

---

## Critical Issues

### CR-01: Import of non-existent `make_result` in `memory.py`

**File:** Plan Task 6, Step 1 (`paperforge/commands/memory.py` line 4)
**Issue:** The plan code imports `make_result` from `paperforge.core.result`:
```python
from paperforge.core.result import PFError, PFResult, make_result
```
`make_result` is **not defined anywhere** in the codebase. Verified by grep of the entire `paperforge/` tree — zero matches. `core/result.py` (lines 1-79) exports only `PFError` and `PFResult`. This would cause `ImportError` at runtime on every invocation of `paperforge memory`.

**Fix:**
```python
# Remove make_result from the import line — it's never used in the function body either.
from paperforge.core.result import PFError, PFResult
```

---

### CR-02: `get_memory_status` does not check `canonical_index_hash`

**File:** Plan Task 5, Step 1 (`paperforge/memory/query.py`, `get_memory_status()`)
**Issue:** The spec (Design Spec lines 221-226) explicitly requires `memory status` to verify `canonical_index_hash` against the SHA-256 of the current `formal-library.json`:
> - `canonical_index_hash` matches computed hash of current `formal-library.json` → `fresh: bool`

The plan's implementation (lines 678-717) computes `fresh` as only:
```python
result["fresh"] = result["schema_ok"] and result["count_match"]
```
The `canonical_index_hash` stored in `meta` during build is never read back and never compared. The status command will report `fresh: true` even when the canonical index has changed since the last build — giving a falsely green "fresh" signal that causes stale paper-status results.

**Fix:** In `get_memory_status()` after the read-only connection is opened, add:
```python
# Read stored hash from meta
stored_hash_row = conn.execute(
    "SELECT value FROM meta WHERE key = 'canonical_index_hash'"
).fetchone()
stored_hash = stored_hash_row["value"] if stored_hash_row else ""

# Recompute hash from current index
envelope = read_index(vault)
items = envelope.get("items", []) if isinstance(envelope, dict) else []
from paperforge.memory.builder import _compute_hash
current_hash = _compute_hash(items) if items else ""

result["hash_match"] = stored_hash == current_hash
result["fresh"] = result["schema_ok"] and result["count_match"] and result["hash_match"]
```

---

### CR-03: `build_from_index` crashes on legacy-format (bare list) index

**File:** Plan Task 4, Step 1 (`paperforge/memory/builder.py`, line 467-471)
**Issue:** `read_index(vault)` in `asset_index.py` (line 160-176) can return a **bare list** (legacy pre-v1.6 format). The `build_from_index` function only checks for `None`:
```python
envelope = read_index(vault)
if envelope is None:
    raise FileNotFoundError(...)
items = envelope.get("items", [])      # <-- CRASH: list has no .get()
```
If the vault has a legacy-format `formal-library.json` (not yet migrated by a sync run), `envelope` is a `list`, and `envelope.get(...)` raises `AttributeError`. The existing codebase has `is_legacy_format()` and `migrate_legacy_index()` in `asset_index.py` (lines 178-212) specifically for this case.

**Fix:** Add legacy format detection after the `None` check:
```python
envelope = read_index(vault)
if envelope is None:
    raise FileNotFoundError(
        "Canonical index not found. Run paperforge sync --rebuild-index."
    )
from paperforge.worker.asset_index import is_legacy_format
if is_legacy_format(envelope):
    raise FileNotFoundError(
        "Canonical index is in legacy (bare-list) format. "
        "Run paperforge sync --rebuild-index to migrate."
    )
items = envelope.get("items", [])
generated_at = envelope.get("generated_at", "")
```

---

### CR-04: `get_memory_status` crashes on legacy-format index

**File:** Plan Task 5, Step 1 (`paperforge/memory/query.py`, line 708-713)
**Issue:** Same legacy-format crash as CR-03, but in the read path:
```python
envelope = read_index(vault)
if envelope:
    result["paper_count_index"] = envelope.get("paper_count", 0)  # CRASH on list
```
A bare-list envelope causes `AttributeError`.

**Fix:** Add the same `is_legacy_format` guard:
```python
envelope = read_index(vault)
if envelope and isinstance(envelope, dict):
    result["paper_count_index"] = envelope.get("paper_count", 0)
    ...
```

---

### CR-05: Windows-path URI incompatibility in `get_connection` read-only mode

**File:** Plan Task 2, Step 2 (`paperforge/memory/db.py`, line 122-123)
**Issue:**
```python
uri = f"file:{db_path}?mode=ro" if read_only else str(db_path)
conn = sqlite3.connect(uri, uri=read_only)
```
On Windows, `db_path` contains backslashes (e.g., `D:\Vault\System\PaperForge\indexes\paperforge.db`). The constructed URI `file:D:\Vault\...?mode=ro` is NOT a valid [RFC 8089 file URI](https://datatracker.ietf.org/doc/html/rfc8089). SQLite's URI parser requires either `file:///D:/...` (authority path) or `file:D:/...` (local path with forward slashes). With backslashes, `sqlite3.connect(..., uri=True)` may fail with `sqlite3.OperationalError: unable to open database file` or silently misinterpret the path.

**Fix:** Normalize the path to use forward slashes before constructing the URI:
```python
def get_connection(db_path: Path, read_only: bool = False) -> sqlite3.Connection:
    if read_only:
        # Windows-safe: convert to forward slashes for SQLite URI parser
        posix_path = str(db_path.resolve()).replace("\\", "/")
        uri = f"file:{posix_path}?mode=ro"
    else:
        uri = str(db_path)
    conn = sqlite3.connect(uri, uri=read_only)
    conn.row_factory = sqlite3.Row
    if not read_only:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
    return conn
```

---

## Warnings

### WR-01: `--force` flag on `memory build` defined but never implemented

**File:** Plan Task 6, Step 3 (cli.py parser) + Task 4 builder
**Issue:** The CLI parser adds `--force` to `memory build`:
```python
p_memory_build.add_argument("--force", action="store_true", help="Force rebuild")
```
Neither `memory.run()` nor `build_from_index()` checks `args.force`. The builder always deletes all paper data and rebuilds (lines 486-488), making `--force` redundant for the current logic. However, a future optimization that caches unchanged entries would make `--force` meaningful. Either implement the flag or remove it — dead CLI interfaces degrade user experience and create maintenance debt.

**Fix:** Either (a) remove the `--force` argument entirely from the parser, or (b) wire it through:
```python
# In builder.py: add force parameter
def build_from_index(vault: Path, force: bool = False) -> dict:
    ...
    if force:
        drop_all_tables(conn)
    ...
# In memory.py:
counts = build_from_index(vault, force=getattr(args, "force", False))
```

---

### WR-02: Ambiguous query (>1 results) returns full status instead of candidate list only

**File:** Plan Task 5 (`paperforge/memory/query.py`, `get_paper_status()`, lines 775-793)
**Issue:** The spec (Design Spec line 243) states:
> **>1 results:** Candidate list only (no full status details)

The plan returns full status for the first match PLUS the candidate list:
```python
entry = entries[0]
assets = get_paper_assets(conn, entry["zotero_key"])
entry["health"] = compute_health(entry)       # Full status details computed
entry["candidates"] = entries if len(entries) > 1 else None
entry["assets"] = assets
return entry
```
And the CLI output (paper_status.py lines 986-991) always prints title/year/lifecycle/next_step — even when multiple candidates exist. This violates the spec's "candidate list only" requirement for ambiguous queries.

**Fix:** When `len(entries) > 1`, return candidate summary only:
```python
if len(entries) > 1:
    return {
        "candidates": [
            {
                "zotero_key": e.get("zotero_key", ""),
                "title": e.get("title", ""),
                "year": e.get("year", ""),
                "doi": e.get("doi", ""),
                "domain": e.get("domain", ""),
            }
            for e in entries
        ],
        "candidate_count": len(entries),
    }
```

---

### WR-03: `recommended_action` field missing from paper-status output

**File:** Plan Task 5 (`paperforge/memory/query.py`, `get_paper_status()`) + Task 6 (`paper_status.py`)
**Issue:** The spec (Design Spec lines 252-253) requires:
> `recommended_action`: e.g., `"/pf-deep ABCDEFG"` or `"paperforge sync"` or `"paperforge ocr"`

The plan only returns `entry["next_step"]` (e.g., `"/pf-deep"`) in the output but never computes a concrete `recommended_action` like `"/pf-deep ABCDEFG"`. The spec implies this should be a ready-to-use command string with the paper key substituted in.

**Fix:** In `get_paper_status()`, after computing health, add:
```python
step = entry.get("next_step", "")
zkey = entry.get("zotero_key", "")
action_map = {
    "/pf-deep": f"/pf-deep {zkey}",
    "ocr": f"paperforge ocr --key {zkey}",
    "sync": "paperforge sync",
    "repair": "paperforge repair",
    "ready": "Ready — no action needed",
}
entry["recommended_action"] = action_map.get(step, step)
```

---

### WR-04: Core business logic functions have zero test coverage

**File:** Plan Tasks 4-5 (test files)
**Issue:** The plan specifies 8 tests total:
- 4 schema tests (table creation/deletion/schema version) — good
- 3 builder tests — but ALL three test only `_compute_hash`, a 10-line helper. `build_from_index()` (~150 lines) has **zero tests**.
- 1 query test — only tests `get_memory_status()` with a nonexistent vault path. `lookup_paper()`, `get_paper_assets()`, `get_paper_status()`, and `_entry_from_row()` have **zero tests**.

Untested edge cases include: empty items list, schema version mismatch trigger, corrupt JSON in authors/collections, exact zotero_key lookup, DOI lookup, title substring search, no-results path, asset reconstruction with None values.

**Fix:** Add at minimum:
- `test_build_from_index_empty_items()` — ensure handles empty index gracefully
- `test_build_from_index_schema_mismatch()` — verify drop+rebuild on version change
- `test_build_from_index_populates_correctly()` — build from a mock envelope, verify paper count/asset count
- `test_lookup_paper_by_key()` — exact zotero_key match
- `test_lookup_paper_by_doi()` — DOI lookup
- `test_lookup_paper_by_title_substring()` — LIKE match
- `test_lookup_paper_no_results()` — returns empty list
- `test_get_paper_status_returns_none_for_missing()` — paper not found
- `test_entry_from_row_handles_null_fields()` — None values don't crash

---

### WR-05: CLI dispatch pattern inconsistent with existing codebase

**File:** Plan Task 6, Step 3 (cli.py dispatch blocks)
**Issue:** The plan adds verbose-index carving logic in the dispatch blocks:
```python
if args.command == "memory":
    argv = sys.argv.copy()
    try:
        idx = argv.index("memory")
        args.verbose = "--verbose" in argv[idx:] or "-v" in argv[idx:]
    except ValueError:
        pass
    from paperforge.commands import memory
    return memory.run(args)
```
No other command dispatch in `cli.py` (lines 407-533) uses this pattern. All 15 existing command dispatches simply import and call `run(args)`. The `--verbose` flag is already a top-level argument parsed by argparse (cli.py lines 132-136), and `configure_logging(verbose=...)` is called at line 402 BEFORE any dispatch. This carving code is redundant and adds 14 lines of unnecessary complexity per command.

**Fix:** Follow the existing pattern — just import and dispatch:
```python
if args.command == "memory":
    from paperforge.commands import memory
    return memory.run(args)

if args.command == "paper-status":
    from paperforge.commands import paper_status
    return paper_status.run(args)
```

---

## Info

### IN-01: Unused `compute_health` import in `builder.py`

**File:** Plan Task 4, Step 1 (`paperforge/memory/builder.py`, line 414)
**Issue:** `compute_health` is imported but never called in `build_from_index()`. Per the spec (line 141), health dimensions are computed at query time only, so this import is conceptually correct to exclude. The dead import is harmless but clutters the import block.

**Fix:** Remove `compute_health` from the builder import:
```python
from paperforge.worker.asset_state import (
    compute_lifecycle,
    compute_maturity,
    compute_next_step,
)
```

---

### IN-02: `_COMMAND_REGISTRY` entries not consumed by `cli.py` dispatch

**File:** Plan Task 6, Step 4 (`paperforge/commands/__init__.py`)
**Issue:** The plan adds `"memory"` and `"paper-status"` to `_COMMAND_REGISTRY`, which powers `get_command_module()` for dynamic dispatch. However, `cli.py` uses hard-coded `if/elif` chains (not `get_command_module()`), so these registry entries are unused by the primary dispatch path. The entries are only consumed if some other code path calls `get_command_module("memory")`.

**Fix:** Not critical for Phase 1, but either (a) use `get_command_module()` in cli.py dispatch to reduce duplication, or (b) document that the registry exists for future dynamic-dispatch migration.

---

### IN-03: `_compute_hash` uses `.get()` instead of direct key access per spec

**File:** Plan Task 4, Step 1 (`paperforge/memory/builder.py`, line 448-449)
**Issue:** The spec (line 202) explicitly says:
> `sorted(items, key=lambda e: e["zotero_key"])`

The plan uses `e.get("zotero_key", "")` — a safe-access variant. This is arguably more robust (it won't crash on malformed entries), but the spec's direct-access was an intentional design choice to fail-loud on corrupt data rather than silently producing a different hash. Decide which contract you want.

**Fix:** Either align with spec (remove `.get()` for loud failure) or update the spec to accept safe access.

---

### IN-04: `_entry_from_row` uses fragile `.rstrip("_json")`

**File:** Plan Task 5, Step 1 (`paperforge/memory/query.py`, line 729)
**Issue:**
```python
entry[key.rstrip("_json")] = json.loads(entry.pop(key))
```
`rstrip("_json")` removes any trailing characters in the set `{'_', 'j', 's', 'o', 'n'}`, not the literal substring `"_json"`. For `"authors_json"` this produces `"authors"` (correct), and for `"collections_json"` it produces `"collections"` (correct). But if future columns with names like `"version_json"` or `"annotation_json"` were added, this would produce `"versi"` or `"annotati"` — silently wrong. The fix is trivial and prevents future bugs.

**Fix:**
```python
for key in ("authors_json", "collections_json"):
    if key in entry and entry[key]:
        try:
            clean_key = key[:-5]  # strip "_json" suffix (exactly 5 chars)
            entry[clean_key] = json.loads(entry.pop(key))
        except json.JSONDecodeError:
            pass
```

---

_Reviewed: 2026-05-12T18:30:00Z_
_Reviewer: VT-OS/OPENCODE (gsd-code-reviewer)_
_Depth: deep_
