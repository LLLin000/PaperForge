# User-Side Skill Stabilization Plan

> **For agentic workers:** Use subagent-driven-development to implement.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make paperforge skill + memory layer reliable for local self-use — no data loss, no split truth sources, no agent misrouting.

**Architecture:** JSONL as single source of truth, SQLite as derived index, CLI as sole write interface, bootstrap as sole path resolver.

**Tech Stack:** Python, JSONL, SQLite, paperforge CLI

---

## Task 1: Unify reading-log data flow (JSONL as single source)

**Files:**
- Modify: `paperforge/commands/reading_log.py` (lookup + export data sources, remove write_reading_note call)
- Modify: `paperforge/memory/events.py` (mark write_reading_note deprecated)

**Goal:** `--lookup` and `export` read from JSONL, not paper_events. `--write` only calls `append_reading_note`.

- [ ] **Step 1: Change lookup_paper_events to read from JSONL**

In `reading_log.py`, replace `lookup_paper_events()` body to use `get_reading_notes_for_paper()` from JSONL instead of querying paper_events. Keep the function return shape the same. Join with papers table for title/year/citation_key.

```python
def lookup_paper_events(vault: Path, key: str) -> dict:
    notes = get_reading_notes_for_paper(vault, key)
    if not notes:
        return {"ok": True, "zotero_key": key, "title": "", "entries": [], "count": 0}
    
    # Try to get paper metadata from DB for richer display
    db_path = get_memory_db_path(vault)
    title = ""
    if db_path.exists():
        conn = get_connection(db_path, read_only=True)
        try:
            row = conn.execute(
                "SELECT title FROM papers WHERE zotero_key = ?", (key,)
            ).fetchone()
            if row:
                title = row["title"] or ""
        finally:
            conn.close()
    
    entries = []
    for n in notes:
        entries.append({
            "created_at": n.get("created_at", ""),
            "section": n.get("section", ""),
            "excerpt": n.get("excerpt", ""),
            "usage": n.get("usage", ""),
            "note": n.get("note", ""),
        })
    return {"ok": True, "zotero_key": key, "title": title, "entries": entries, "count": len(entries)}
```

- [ ] **Step 2: Change export_reading_log to read from JSONL**

In `events.py`, add a new `export_reading_log_from_jsonl()` that reads from `read_all_reading_notes()`, joins with DB for metadata. Or in `reading_log.py`, replace the export path (around line 286) to use JSONL directly with a local join helper.

- [ ] **Step 3: Remove write_reading_note from write path**

In `reading_log.py` `run()`, remove the `write_reading_note()` call (the second write). Only `append_reading_note()` remains.

- [ ] **Step 4: Mark write_reading_note deprecated**

Add deprecation docstring to `write_reading_note` in `events.py`. Do NOT remove the function (backward compat for import_reading_log which may still use it).

- [ ] **Step 5: Commit**

```bash
git add paperforge/commands/reading_log.py paperforge/memory/events.py
git commit -m "refactor: unify reading-log reads to JSONL, deprecate paper_events writes"
```

---

## Task 2: Permanent correction-log.jsonl

**Files:**
- Modify: `paperforge/memory/permanent.py` (add correction append/read functions)
- Modify: `paperforge/commands/paper_context.py` (read corrections from JSONL, fix ref_id → original_id)
- Modify: `paperforge/commands/reading_log.py` (write correction to JSONL, not just paper_events)
- Modify: `paperforge/memory/builder.py` (import corrections on rebuild)

**Goal:** Correction notes live in `correction-log.jsonl`, survive DB rebuilds.

- [ ] **Step 1: Add correction helpers to permanent.py**

```python
# ── Correction Log ─────────────────────────────────────────────────────────

def get_correction_log_path(vault: Path) -> Path:
    return _logs_dir(vault) / "correction-log.jsonl"


def append_correction(
    vault: Path,
    paper_id: str,
    original_id: str,
    correction: str,
    reason: str = "",
    agent: str = "",
) -> dict:
    if not paper_id:
        return {"ok": False, "error": "paper_id is required"}
    if not original_id:
        return {"ok": False, "error": "original_id is required"}
    if not correction:
        return {"ok": False, "error": "correction is required"}

    date_str = datetime.date.today().strftime("%Y%m%d")
    entry_id = f"corr_{date_str}_{secrets.token_hex(4)}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    entry: dict[str, object] = {
        "id": entry_id,
        "event_type": "correction",
        "created_at": now,
        "paper_id": paper_id,
        "original_id": original_id,
        "correction": correction,
        "reason": reason,
        "agent": agent,
    }

    log_dir = _ensure_logs_dir(vault)
    filepath = log_dir / "correction-log.jsonl"

    try:
        with filepath.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        return {"ok": False, "error": str(e)}

    return {"ok": True, "id": entry_id, "path": str(filepath)}


def read_all_corrections(vault: Path) -> list[dict]:
    filepath = get_correction_log_path(vault)
    return _read_jsonl(filepath)


def get_corrections_for_paper(vault: Path, paper_id: str) -> list[dict]:
    all_corrections = read_all_corrections(vault)
    return [c for c in all_corrections if c.get("paper_id") == paper_id]
```

- [ ] **Step 2: Fix paper_context.py to read from JSONL**

Replace the `paper_events` query for corrections with `get_corrections_for_paper()`. Fix `ref_id` → `original_id`.

- [ ] **Step 3: Dual-write correction in reading_log.py**

In `reading_log.py` `run()`, when writing a correction, write to BOTH:
1. `append_correction()` → `correction-log.jsonl` (permanent)
2. `write_correction_note()` → `paper_events` (FTS search, optional — keep for now)

- [ ] **Step 4: Add correction import to builder.py**

Add `_import_correction_log()` that reads `correction-log.jsonl` and inserts into paper_events (so corrections are searchable after rebuild).

- [ ] **Step 5: Commit**

```bash
git add paperforge/memory/permanent.py paperforge/commands/paper_context.py \
        paperforge/commands/reading_log.py paperforge/memory/builder.py
git commit -m "feat: permanent correction-log.jsonl, fix original_id field alignment"
```

---

## Task 3: Fix pf_bootstrap.py path resolution + Python fallback

**Files:**
- Modify: `paperforge/skills/paperforge/scripts/pf_bootstrap.py`

**Goal:** Support `vault_config` nested config, fallback Python to `python`/`python3`/`sys.executable`.

- [ ] **Step 1: Add resolve_cfg()**

```python
DEFAULTS = {
    "system_dir": "System",
    "resources_dir": "Resources",
    "literature_dir": "Literature",
    "control_dir": "LiteratureControl",
    "base_dir": "Bases",
}

def resolve_cfg(raw: dict) -> dict:
    cfg = DEFAULTS.copy()
    nested = raw.get("vault_config", {})
    if isinstance(nested, dict):
        cfg.update({k: v for k, v in nested.items() if v})
    cfg.update({k: raw[k] for k in DEFAULTS if raw.get(k)})
    return cfg
```

Replace direct `cfg.get(...)` calls with `cfg = resolve_cfg(...)`.

- [ ] **Step 2: Fix Python fallback**

In `_find_python_with_paperforge()`, if no paperforge-capable Python is found:
- Try `python`, `python3`
- Fall back to `sys.executable`
- Return `"python"` (not None) with `python_verified: false`

In `main()`, after python_candidate:
```python
if result.get("python_candidate"):
    result["python_verified"] = True
else:
    result["python_candidate"] = "python"
    result["python_verified"] = False
```

- [ ] **Step 3: Commit**

```bash
git add paperforge/skills/paperforge/scripts/pf_bootstrap.py
git commit -m "fix: bootstrap vault_config nest, python fallback with verified flag"
```

---

## Task 4: FTS safe query with fallback

**Files:**
- Modify: `paperforge/memory/fts.py`

**Goal:** Three-level fallback for FTS queries.

- [ ] **Step 1: Add tokenizer and fallback logic**

```python
import re

def tokenize_for_fts(q: str) -> str:
    """Extract alphanumeric + CJK tokens and quote them for safe FTS."""
    tokens = re.findall(r"[\w\u4e00-\u9fff]+", q)
    if not tokens:
        return q
    return " OR ".join(f'"{t}"' for t in tokens)


def _fts_search(conn, query, params, limit):
    """Try raw FTS, fall back to quoted tokens, then LIKE."""
    from contextlib import closing
    
    conditions = ["paper_fts MATCH ?"]
    all_params = [query] + params
    
    try:
        where = " AND ".join(conditions)
        sql = f"""
            SELECT ... FROM paper_fts f JOIN papers p ON p.rowid = f.rowid
            WHERE {where} ORDER BY rank LIMIT ?
        """
        all_params.append(limit)
        conn.row_factory = sqlite3.Row
        return conn.execute(sql, all_params).fetchall()
    except sqlite3.OperationalError:
        pass
    
    # Level 2: quoted tokens
    try:
        token_query = tokenize_for_fts(query)
        all_params = [token_query] + params + [limit]
        sql = f"""
            SELECT ... FROM paper_fts f JOIN papers p ON p.rowid = f.rowid
            WHERE paper_fts MATCH ? {'AND ...' * len(params)} ORDER BY rank LIMIT ?
        """
        return conn.execute(sql, all_params).fetchall()
    except sqlite3.OperationalError:
        pass
    
    # Level 3: LIKE fallback
    like_param = f"%{query}%"
    conditions = [
        "(p.title LIKE ? OR p.abstract LIKE ? OR p.doi LIKE ? OR p.citation_key LIKE ?)"
    ]
    all_params = [like_param, like_param, like_param, like_param] + params + [limit]
    # ... construct and execute LIKE query
    return rows
```

- [ ] **Step 2: Update search_papers() to use _fts_search**

Replace the direct FTS query with the safe fallback.

- [ ] **Step 3: Commit**

```bash
git add paperforge/memory/fts.py
git commit -m "feat: safe FTS search with token-quote and LIKE fallback"
```

---

## Task 5: SKILL.md — router + PYTHON fallback + workflow rules

**Files:**
- Create: `paperforge/skills/paperforge/workflows/project-engineering.md`
- Modify: `paperforge/skills/paperforge/SKILL.md`
- Modify: `paperforge/skills/paperforge/workflows/deep-reading.md`
- Modify: `paperforge/skills/paperforge/workflows/paper-qa.md`
- Modify: `paperforge/skills/paperforge/workflows/project-log.md`
- Modify: `paperforge/skills/paperforge/workflows/methodology.md`

**Goal:** Engineering router, PYTHON fallback, workflow safety reinforcement.

- [ ] **Step 1: Add PYTHON fallback to SKILL.md**

After bootstrap section, add:
```markdown
If `python_verified` is `false` or `python_candidate` is `null`:
Try `python` → `python3` → `sys.executable` in order.
If all fail, stop and tell user to set `python_path` in `paperforge.json`.
```

- [ ] **Step 2: Add project-engineering to router table**

Add to routing table:
```markdown
| "branch" "代码审查" "feature" "dashboard" "memory layer" "用户反馈" "报错" "安装失败" "Git" "Zotero" "BetterBibTeX" "OCR" "插件" | `workflows/project-engineering.md` |
```

- [ ] **Step 3: Create project-engineering workflow stub**

Minimal workflow for engineering tasks — routes to appropriate context retrieval.

- [ ] **Step 4: Reinforce safety rule in deep-reading.md and paper-qa.md**

Add at top of each:
```markdown
> Prior reading-log entries are **recheck targets only**, never factual answers.
> Always verify against original source before using any reading-log content.
```

- [ ] **Step 5: Clarify project-log vs methodology boundary**

In project-log.md: "Record what happened this session."
In methodology.md: "Only archive methods reusable across multiple projects/tasks."

- [ ] **Step 6: Commit**

```bash
git add paperforge/skills/paperforge/
git commit -m "chore: add PYTHON fallback, engineering router, workflow safety rules"
```

---

## Summary

| Task | Priority | Files | Risk |
|------|----------|-------|------|
| 1 — reading-log unify | P0 | reading_log.py, events.py | Low — just changes data source |
| 2 — correction permanent | P0 | permanent.py, paper_context.py, reading_log.py, builder.py | Low — new file, additive |
| 3 — bootstrap fix | P0 | pf_bootstrap.py | Low — no changes to CLI |
| 4 — FTS safe query | P0 | fts.py | Low — additive fallback |
| 5 — SKILL/router/rules | P1 | 6 files under skills/ | Trivial — docs only |
