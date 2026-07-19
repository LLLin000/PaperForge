---
phase: memory-layer-2-5-spec-review
reviewed: 2026-05-12T00:00:00Z
depth: deep
files_reviewed: 7
files_reviewed_list:
  - docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md
  - paperforge/memory/query.py
  - paperforge/memory/builder.py
  - paperforge/memory/schema.py
  - paperforge/commands/dashboard.py
  - paperforge/memory/fts.py
  - paperforge/cli.py
findings:
  critical: 5
  warning: 8
  info: 7
  total: 20
status: issues_found
---

# Spec Review: Memory Layer Phase 2-5 Design

**Reviewed:** 2026-05-12
**Depth:** deep (cross-file analysis with import graph and call-chain tracing)
**Files Reviewed:** 7 (1 spec + 6 existing source files)
**Status:** issues_found

## Summary

Cross-referenced the Phase 2-5 design spec against the existing Memory Layer codebase (`memory/query.py`, `memory/builder.py`, `memory/schema.py`, `memory/fts.py`), plus the CLI dispatcher (`cli.py`) and dashboard command (`commands/dashboard.py`).

The design correctly reuses existing infrastructure (`compute_hash`, `PAPER_COLUMNS`, `ASSET_FIELDS`, `read_index`) and follows the layered architecture (memory lib → commands module → CLI dispatch). However, five blocker-level issues were found involving **contract violations**, **missing schema migrations**, and **incomplete PFResult compliance** that must be resolved before implementation begins.

---

## Critical Issues

### CR-01: Dashboard return format contract violation

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:188-200`

**Issue:** The spec states "Dashboard output format must NOT change (plugin depends on it)" (line 204), yet `_dashboard_from_db()` adds a new top-level key `_source` to the return dict. The existing `_gather_dashboard_data()` returns `{"stats": {...}, "permissions": {...}}` with exactly two top-level keys. Adding `_source` is a format change that will break any plugin consumer that iterates over top-level keys or destructures the response.

**Fix:** Either:
1. Nest `_source` inside `stats` (e.g., `stats._source`), preserving the two-key top-level structure, OR
2. Explicitly acknowledge the format change and version the dashboard response schema, coordinating with the plugin team.

```python
# Option 1 — nest inside stats:
return {
    "stats": {
        "papers": total,
        "pdf_health": {...},
        "ocr_health": {...},
        "domain_counts": domain_counts,
        "_source": "paperforge.db"   # nested, not top-level
    },
    "permissions": permissions,
}
```

---

### CR-02: Schema version not bumped for new tables

**File:** `paperforge/memory/schema.py:5` (CURRENT_SCHEMA_VERSION = 1)
**Cross-ref:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:282-304`

**Issue:** The spec introduces two new tables (`paper_chunks`, `chunk_fts`) but does not mention incrementing `CURRENT_SCHEMA_VERSION` (currently `1`). The existing `get_memory_status()` in `query.py:38` compares stored schema version against `CURRENT_SCHEMA_VERSION` to detect staleness. If the version stays at 1, existing databases won't be detected as stale, and `ensure_schema()` won't know to create the new tables on upgrade.

Additionally, `build_from_index()` in `builder.py:88-90` drops and recreates all tables when the stored version differs from `CURRENT_SCHEMA_VERSION`:
```python
if stored_version != CURRENT_SCHEMA_VERSION:
    drop_all_tables(conn)
ensure_schema(conn)
```
Without a version bump, upgrading users will never get the new tables.

**Fix:** Bump `CURRENT_SCHEMA_VERSION` to `2` in `schema.py:5`. The spec should explicitly state this.

---

### CR-03: FTS virtual table naming violates existing convention

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:295-303`
**Cross-ref:** `paperforge/memory/schema.py:86-101`

**Issue:** The existing FTS virtual table is named `paper_fts` (schema.py line 86). The spec names the new content-sync table `chunk_fts`. The established naming convention is `{entity}_fts` where `{entity}` is the base table name. Since the entity table is `paper_chunks` (not `chunks`), the FTS table should be `paper_chunk_fts` for consistency and to avoid collision with any future `chunks` table from another subsystem.

**Fix:** Rename `chunk_fts` to `paper_chunk_fts` throughout the spec.

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS paper_chunk_fts USING fts5(
    chunk_id UNINDEXED,
    paper_id UNINDEXED,
    source_type,
    section_title,
    chunk_text,
    content='paper_chunks',
    content_rowid='rowid'
);
```

---

### CR-04: `agent-context` output format not wrapped in PFResult

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:26-81`
**Cross-ref:** `paperforge/core/result.py:18-27` (PFResult dataclass)

**Issue:** Every CLI command in the existing codebase returns output via `PFResult.to_json()` (see `paper_status.py:35-40`, `search.py:61`, `dashboard.py:38-40`). The PFResult contract includes fields `ok`, `command`, `version`, `data`, `error`, `warnings`, `next_actions`. The spec's `agent-context` output shows a raw dict structure mimicking PFResult but it is ambiguous whether the implementation will actually use the `PFResult` dataclass.

If this command bypasses PFResult, it breaks the contract that all `--json` outputs conform to the same envelope format, making it impossible for downstream consumers (plugin, agents) to parse responses uniformly.

**Fix:** The spec should state explicitly:
```python
result = PFResult(
    ok=True,
    command="agent-context",
    version=PF_VERSION,
    data={...},  # the full context dict
)
print(result.to_json())
```

---

### CR-05: `get_agent_context()` has no error handling for SQL failures

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:88-107`
**Cross-ref:** `paperforge/memory/schema.py:150-158` (get_schema_version catches OperationalError)

**Issue:** The spec's `get_agent_context()` opens a connection and executes queries but wraps only the connection lifecycle in try/finally (for close). It does not wrap the individual SQL queries in try/except. If the DB exists but has a corrupted schema (wrong column count, missing table), the query will raise `sqlite3.OperationalError` which propagates unhandled up to the CLI command, producing a raw traceback instead of a clean PFResult error.

Compare with `get_memory_status()` in `query.py:46-49` which wraps all DB reads in `try/except Exception` and returns a safe fallback dict.

**Fix:**
```python
def get_agent_context(vault: Path) -> dict:
    conn = get_connection(get_memory_db_path(vault), read_only=True)
    try:
        total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        # ...
    except sqlite3.Error as exc:
        return {"ok": False, "error": f"DB read failed: {exc}"}
    finally:
        conn.close()
```

---

## Warnings

### WR-01: `agent-context` re-derives freshness instead of delegating

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:88-107`
**Cross-ref:** `paperforge/memory/query.py:16-77` (get_memory_status)

**Issue:** The spec's `get_agent_context()` manually queries `SELECT COUNT(*)` and `GROUP BY domain` but does not use the existing `get_memory_status()` function which already computes `fresh`, `needs_rebuild`, `hash_match`, and `count_match`. The `"memory_db": "ready"` field is hardcoded — it doesn't reflect whether the DB is actually fresh. Calling `get_memory_status()` would provide a canonical freshness signal that can gate whether the agent can trust the DB.

**Fix:** Add a call to `get_memory_status(vault)` at the top of `get_agent_context()` and use `result["fresh"]` to set the `memory_db` field to `"ready"` or `"stale"`.

---

### WR-02: `pdf_health` via `lifecycle` is lossy — misses `path_error` states

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:163-167`
**Cross-ref:** `paperforge/commands/dashboard.py:84-107` (path_error regex detection)
**Cross-ref:** `paperforge/memory/builder.py:28-38` (PAPER_COLUMNS — no path_error column)

**Issue:** The spec computes `pdf_healthy` as `r["lifecycle"] != "indexed"`. A paper with `lifecycle == "pdf_ready"` has a PDF, but that PDF could be broken (permission denied, file missing). The existing file-scanning code in `dashboard.py:99-107` uses a `path_error` regex to detect these cases and counts them separately as `broken`. The DB schema (`PAPER_COLUMNS`) has no `path_error` column, so the DB-based dashboard cannot distinguish between "healthy PDF" and "broken PDF." The hardcoded `"broken": 0` is misleading.

**Fix:** Either:
1. Add a `path_error` column to the `papers` table and populate it during `build_from_index()`, OR
2. Document this as a known limitation and note that `broken` counts require file-system scanning.

---

### WR-03: `refresh_paper()` linear O(n) scan through formal-library.json

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:228-234`

**Issue:** The spec searches for the target entry by iterating through all items:
```python
for e in items:
    if e.get("zotero_key") == zotero_key:
        entry = e; break
```
For 283 papers this is negligible, but for larger libraries (10K+ entries), this becomes a performance concern. The spec should at minimum acknowledge this limitation and note that an index lookup or dictionary-based approach should be considered for scale.

**Fix:** Build a lookup dict keyed by `zotero_key`:
```python
index_map = {e.get("zotero_key"): e for e in items if e.get("zotero_key")}
entry = index_map.get(zotero_key)
```

---

### WR-04: `refresh_paper()` silent skip on stale index is indistinguishable from success

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:268`

**Issue:** The spec says "If formal-library.json is stale (entry not found), skip silently" and `refresh_paper()` returns `False`. However, the integration points (sync, ocr, deep-finalize, repair) call `refresh_paper()` after modifying state. If the index hasn't been regenerated yet, the refresh silently fails and the DB is now out of sync with the ground truth. The caller has no way to distinguish "refresh succeeded" from "entry not in index yet — DB unchanged."

This is most acute after `paperforge ocr` where OCR status changes but sync hasn't re-run — the DB will show stale OCR status.

**Fix:** Return a richer result:
```python
return {"action": "refreshed", "key": zotero_key}
# vs
return {"action": "skipped", "key": zotero_key, "reason": "not_in_index"}
```
Or raise a distinguishable exception that callers can catch and handle (e.g., trigger a full rebuild).

---

### WR-05: `retrieve` chunk output doesn't specify JOIN to get `title`

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:319-339`
**Cross-ref:** `paperforge/memory/fts.py:41-51` (search_papers JOIN pattern)

**Issue:** The `retrieve` output (lines 327-338) shows `zotero_key` and `title` fields per chunk, but `paper_chunks` stores only `paper_id` (not `zotero_key` or `title`). The existing `search_papers()` in `fts.py:41-51` demonstrates the correct pattern: JOIN `paper_fts f` → `papers p ON p.rowid = f.rowid` to get metadata. The spec's `retrieve` query is unspecified — it must JOIN `chunk_fts` → `paper_chunks` → `papers` to produce the output format shown.

**Fix:** Specify the query:
```sql
SELECT c.chunk_id, c.paper_id, c.source_type, c.section_title,
       c.page_number, c.chunk_text, p.title, p.zotero_key, rank
FROM paper_chunk_fts f
JOIN paper_chunks c ON c.rowid = f.rowid
JOIN papers p ON p.zotero_key = c.paper_id
WHERE paper_chunk_fts MATCH ?
ORDER BY rank LIMIT ?
```

---

### WR-06: `agent-context` advertises `--collection` flag that doesn't exist

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:54`
**Cross-ref:** `paperforge/cli.py:273-283` (search subparser — no --collection flag)

**Issue:** The `agent-context` output lists:
```
"search": {
    "usage": "paperforge search <query> --json [--collection NAME] [--domain NAME] ..."
}
```
But the existing `search` subparser (cli.py lines 273-283) defines `--domain`, `--year-from`, `--year-to`, `--ocr`, `--deep`, `--lifecycle`, `--next-step` — **no `--collection` filter**. If an agent reads the `agent-context` output and tries `--collection`, the command will fail with an unrecognized argument error.

**Fix:** Either add `--collection` to the search subparser (requires adding a `collection_path` filter to `search_papers()` in fts.py), or remove it from the agent-context output until it's implemented.

---

### WR-07: FTS triggers for `paper_chunks` / `paper_chunk_fts` not specified

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:295-303`
**Cross-ref:** `paperforge/memory/schema.py:103-118` (FTS_TRIGGERS for papers)

**Issue:** The existing `paper_fts` table uses `content='papers'` (a content-sync external content FTS5 table) and relies on INSERT/UPDATE/DELETE triggers on the `papers` table to keep the FTS index in sync (schema.py lines 103-118). The spec's `chunk_fts` also uses `content='paper_chunks'` with `content_rowid='rowid'` — the same content-sync pattern. But the spec does not mention the required triggers on the `paper_chunks` table. Without them, inserts/deletes into `paper_chunks` won't update the FTS index.

**Fix:** Add trigger definitions to the spec:
```sql
CREATE TRIGGER IF NOT EXISTS paper_chunks_ai AFTER INSERT ON paper_chunks BEGIN
    INSERT INTO paper_chunk_fts(rowid, chunk_id, paper_id, source_type, section_title, chunk_text)
    VALUES (new.rowid, new.chunk_id, new.paper_id, new.source_type, new.section_title, new.chunk_text);
END;
CREATE TRIGGER IF NOT EXISTS paper_chunks_ad AFTER DELETE ON paper_chunks BEGIN
    INSERT INTO paper_chunk_fts(paper_chunk_fts, rowid, chunk_id, paper_id, source_type, section_title, chunk_text)
    VALUES ('delete', old.rowid, old.chunk_id, old.paper_id, old.source_type, old.section_title, old.chunk_text);
END;
CREATE TRIGGER IF NOT EXISTS paper_chunks_au AFTER UPDATE ON paper_chunks BEGIN
    INSERT INTO paper_chunk_fts(paper_chunk_fts, rowid, chunk_id, paper_id, source_type, section_title, chunk_text)
    VALUES ('delete', old.rowid, old.chunk_id, old.paper_id, old.source_type, old.section_title, old.chunk_text);
    INSERT INTO paper_chunk_fts(rowid, chunk_id, paper_id, source_type, section_title, chunk_text)
    VALUES (new.rowid, new.chunk_id, new.paper_id, new.source_type, new.section_title, new.chunk_text);
END;
```

---

### WR-08: DB dashboard hardcodes `broken: 0` — data regression from file scanner

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:191`
**Cross-ref:** `paperforge/commands/dashboard.py:78,98-105` (pdf_broken tracking)
**Cross-ref:** `paperforge/memory/builder.py:28-38` (PAPER_COLUMNS — no path_error)

**Issue:** The existing file-scanning code tracks three PDF states: `healthy`, `broken`, and `missing`. The DB-based approach hardcodes `"broken": 0` because the `papers` table has no column for path_error. This means:
- A PDF file deleted after sync will show as `healthy` (lifecycle unchanged in DB) but is actually broken.
- The user sees 0 broken PDFs in the dashboard when they may have several.

The fallback to file scanning when DB is stale partially mitigates this, but a fresh DB can also have stale path information for any paper whose PDF was moved/deleted after the last `memory build`.

**Fix:** Either add a `broken_pdf_count` computation that cross-checks `pdf_path` existence on disk (lightweight stat call), or document that the DB dashboard shows "index-time PDF health" and the file scanner shows "current PDF health."

---

## Info

### IN-01: Command naming inconsistency — `agent-context` vs existing `paper-status`

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:121`
**Cross-ref:** `paperforge/cli.py:269-271` (paper-status subparser)

**Issue:** Existing commands use descriptive noun phrases: `paper-status`, `deep-reading`, `base-refresh`. The new command `agent-context` follows a different pattern. While the purposes differ (paper-level vs. system-level), the inconsistency is worth noting for CLI discoverability.

**Suggestion:** Consider `context` (shorter) or `memory-context` (follows `memory build`/`memory status` pattern). No change required — just noting.

---

### IN-02: `ALL_TABLES` and `drop_all_tables()` not updated in spec

**File:** `paperforge/memory/schema.py:120,137-141`
**Cross-ref:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:282-303`

**Issue:** The `ALL_TABLES` list in `schema.py:120` controls which tables `drop_all_tables()` removes on rebuild. The spec introduces `paper_chunks` and `chunk_fts` but doesn't mention updating this list. If `drop_all_tables()` is called during a full rebuild (e.g., schema version mismatch), the old tables won't be dropped, potentially leaving orphaned data.

**Suggestion:** The spec should note that `ALL_TABLES` must be updated to include the new tables.

---

### IN-03: `ensure_schema()` not mentioned in spec

**File:** `paperforge/memory/schema.py:123-134`
**Cross-ref:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:282-303`

**Issue:** The spec defines `CREATE TABLE` statements for `paper_chunks` and `chunk_fts` but doesn't mention that `ensure_schema()` must be updated to execute these statements. Both `build_from_index()` and `refresh_paper()` rely on `ensure_schema()` to guarantee tables exist.

**Suggestion:** Add a note: "Update `ensure_schema()` in `schema.py` to execute `CREATE TABLE IF NOT EXISTS paper_chunks` and `CREATE VIRTUAL TABLE IF NOT EXISTS paper_chunk_fts`."

---

### IN-04: `retrieve` command name vs `search` — discoverability concern

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:57-60,315-317`
**Cross-ref:** `paperforge/cli.py:273` (search subparser)

**Issue:** The spec introduces `paperforge retrieve` for OCR fulltext searching alongside existing `paperforge search` for metadata searching. The names don't make the distinction self-evident. New users won't know whether to `search` or `retrieve`. 

**Suggestion:** Consider `paperforge fulltext` or `paperforge search-content` to make the purpose clearer. Alternatively, add a `--fulltext` flag to the existing `search` command that switches to `chunk_fts` when specified. No blocker — naming preference.

---

### IN-05: `agent-context` requires `--json` flag but always outputs JSON

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:121,127`
**Cross-ref:** `paperforge/cli.py` (all commands gate JSON output on --json flag)

**Issue:** The spec says "Always outputs `--json` format; no human-readable mode needed" (line 127), yet the CLI spec shows `paperforge agent-context --json` (line 121). If the command always outputs JSON, the `--json` flag is either redundant (confusing) or incorrectly documented (the command should work without `--json` for human-readable output, like `paper-status` does in `paper_status.py:52-68`).

**Suggestion:** Either:
1. Make `--json` required/default and remove it from the usage (always JSON), or
2. Add a human-readable mode like `paper-status` and keep `--json` as optional.

---

### IN-06: Field name `paper_status` (underscore) vs `paper-status` (hyphen) in `agent-context` output

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:49`
**Cross-ref:** `paperforge/cli.py:269` (paper-status subparser name)

**Issue:** The `agent-context` output uses `"paper-status"` as the command key (correct, matches CLI name). However, the next_actions pattern in existing code uses the command name as-is. Minor — no bug, just noting for consistency review.

---

### IN-07: Chunking strategy — `max 500 tokens` underspecified

**File:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md:306-311`

**Issue:** The spec says "Max 500 tokens per chunk" and "max 3 paragraphs per chunk" but doesn't specify:
- What constitutes a "token" (word-based? `tiktoken`? character count / 4?)
- Whether the token limit or paragraph limit takes precedence
- What happens when a single paragraph exceeds 500 tokens (split mid-paragraph? truncate? keep as oversized chunk?)

**Suggestion:** Clarify tokenization method and tie-breaking rules. For example: "Use `len(text.split())` as a word-count proxy for tokens. If a single paragraph exceeds 500 words, split at sentence boundaries."

---

_Reviewed: 2026-05-12_
_Reviewer: VT-OS/OPENCODE Terminal (gsd-code-reviewer)_
_Depth: deep_
