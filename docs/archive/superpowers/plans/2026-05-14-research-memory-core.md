# Research Memory Core — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the permanent JSONL-based research memory foundation: paper-context (reading-log safety loop), reading-log/project-log JSONL storage + rendering, and methodology compact injection.

**Architecture:** Permanent JSONL files (`logs/reading-log.jsonl`, `logs/project-log.jsonl`) serve as source of truth. `paperforge.db` imports from them on rebuild (reading_log and project_log tables). Markdown rendering is a side effect. A new `paperforge paper-context <key>` command combines paper metadata + prior reading notes + corrections into one call. A new `paperforge project-log` command handles project-level work logging.

**Tech Stack:** Python 3.11+, SQLite (paperforge.db), JSONL files, PFResult contract

---

## Current State (pre-plan)

### What exists
- `paperforge.db` with `papers`, `paper_fts`, `paper_events` tables
- `memory/events.py`: `write_reading_note()` and `export_reading_log()` — both write/read from `paper_events` table in DB (not permanent JSON)
- `commands/reading_log.py`: full CLI for reading-log (write/validate/import/lookup/export), 317 lines
- `commands/agent_context.py`: returns library overview + collections + commands + rules
- `commands/search.py`: FTS5 search with filters
- `skills/paperforge/` (newly restructured): 6 workflow files that reference new CLI commands that don't exist yet
- `memory/schema.py`: `paper_events` table, schema version 1

### What's broken / missing
1. **P0 (resolved)**: pf_search.py deleted, skill_deploy.py fixed, ld_deep renamed to pf_deep
2. **P0 (remaining)**: None — P0 bugs resolved by skill restructure
3. **paper-context CLI**: Does not exist. Is the key safety-loop command.
4. **reading-log stores in DB only**: `write_reading_note()` writes to `paper_events` table. DB rebuild nukes all reading notes. No permanent JSONL storage.
5. **project-log CLI**: Does not exist at all.
6. **METHODOLOGY_COMPACT.md**: Does not exist.
7. **reading-log and project-log rendering**: Does not exist.

### What the workflow files expect (interface contract)
The workflow files in `skills/paperforge/workflows/` reference these CLI atoms that must exist:

```
paperforge paper-context <key> --json --vault $VAULT
  → {ok, data: {paper: {...}, prior_notes: [...], corrections: [...]}}

paperforge reading-log --write <key> --section "..." --excerpt "..." --context "..." --usage "..." --note "..." --project "..." --tags "..." --vault $VAULT
  → {ok, data: {written: true}}

paperforge reading-log --render --project <p> --vault $VAULT
  → renders Project/<p>/reading-log.md

paperforge project-log --write --project <p> --payload '<json_string>' --vault $VAULT
  → {ok, data: {written: true, id: "plog_..."}}

paperforge project-log --render --project <p> --vault $VAULT  
  → renders Project/<p>/project-log.md

paperforge project-log --list <project> --json --vault $VAULT
  → {ok, data: {entries: [...]}}
```

---

## File Structure

### New files
```
paperforge/memory/permanent.py          ← JSONL read/write for reading-log and project-log
paperforge/commands/project_log.py      ← New project-log CLI
paperforge/commands/paper_context.py    ← New paper-context command
```

### Modified files
```
paperforge/cli.py:288-300               ← Update reading-log subparser, add project-log + paper-context
paperforge/commands/reading_log.py      ← Add --context + --tags + --project + --render + JSONL write
paperforge/memory/events.py:9-35        ← Add context/tags/project fields to write_reading_note
paperforge/memory/schema.py             ← Add reading_log + project_log tables + correction_note event_type
paperforge/memory/builder.py            ← Rebuild: import JSONL → DB
paperforge/skills/paperforge/SKILL.md   ← Update CLI references if needed
```

### Deleted files
(none)

---

## Task 1: DB Schema — Add reading_log and project_log tables

**Files:**
- Modify: `paperforge/memory/schema.py`

SQLite tables for import from JSONL. These are derived tables, rebuilt from JSONL on `memory build`.

- [ ] **Step 1: Add CREATE statements**

In `schema.py`, after `EVENT_INDEX_SQL` (line 137), add:

```python
CREATE_READING_LOG = """
CREATE TABLE IF NOT EXISTS reading_log (
    id          TEXT PRIMARY KEY,
    paper_id    TEXT NOT NULL,
    project     TEXT DEFAULT '',
    section     TEXT NOT NULL,
    excerpt     TEXT NOT NULL,
    context     TEXT DEFAULT '',
    usage       TEXT NOT NULL,
    note        TEXT DEFAULT '',
    tags_json   TEXT DEFAULT '[]',
    created_at  TEXT NOT NULL,
    agent       TEXT DEFAULT '',
    verified    INTEGER DEFAULT 0,
    FOREIGN KEY (paper_id) REFERENCES papers(zotero_key)
);
"""

CREATE_PROJECT_LOG = """
CREATE TABLE IF NOT EXISTS project_log (
    id                  TEXT PRIMARY KEY,
    project             TEXT NOT NULL,
    date                TEXT NOT NULL,
    type                TEXT NOT NULL,
    title               TEXT NOT NULL,
    decisions_json      TEXT DEFAULT '[]',
    detours_json        TEXT DEFAULT '[]',
    reusable_json       TEXT DEFAULT '[]',
    todos_json          TEXT DEFAULT '[]',
    related_papers_json TEXT DEFAULT '[]',
    tags_json           TEXT DEFAULT '[]',
    created_at          TEXT NOT NULL,
    agent               TEXT DEFAULT ''
);
"""
```

- [ ] **Step 2: Register in ensure_schema()**

In `ensure_schema()`, add after `conn.execute(CREATE_EVENTS)`:
```python
conn.execute(CREATE_READING_LOG)
conn.execute(CREATE_PROJECT_LOG)
```

- [ ] **Step 3: Add to ALL_TABLES**

```python
ALL_TABLES = ["paper_fts", "papers", "paper_assets", "paper_aliases", "meta", "paper_events", "reading_log", "project_log"]
```

- [ ] **Step 4: Bump CURRENT_SCHEMA_VERSION**

```python
CURRENT_SCHEMA_VERSION = 2  # Bump from 1 for reading_log + project_log tables
```
This ensures existing vaults rebuild to get the new tables.

- [ ] **Step 5: Verify schema compiles**

Run: `python -c "from paperforge.memory.schema import ensure_schema, ALL_TABLES; print(ALL_TABLES)"`
Expected: List includes `reading_log` and `project_log`

- [ ] **Step 6: Commit**

```bash
git add paperforge/memory/schema.py
git commit -m "feat: add reading_log and project_log tables to memory schema"
```

---

## Task 2: JSONL Permanent Storage Layer

**Files:**
- Create: `paperforge/memory/permanent.py`

New module for reading from and appending to JSONL files. No dependencies on DB.

- [ ] **Step 1: Write failing test**

Create file with tests (tests will be added later). For now, just write the module.

- [ ] **Step 2: Write permanent.py**

```python
"""Permanent JSONL storage for reading-log and project-log.

JSONL = one JSON object per line. Append-only. Source of truth.
Never deleted by DB rebuild.
"""

from __future__ import annotations

import json
import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _logs_dir(vault: Path) -> Path:
    from paperforge.config import paperforge_paths
    paths = paperforge_paths(vault)
    return paths["paperforge"] / "logs"


def _ensure_logs_dir(vault: Path) -> Path:
    d = _logs_dir(vault)
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── Reading Log ─────────────────────────────────────────────

def get_reading_log_path(vault: Path) -> Path:
    return _logs_dir(vault) / "reading-log.jsonl"


def append_reading_note(
    vault: Path,
    paper_id: str,
    section: str,
    excerpt: str,
    usage: str,
    context: str = "",
    note: str = "",
    project: str = "",
    tags: list[str] | None = None,
    agent: str = "",
) -> dict:
    """Append a single reading note to reading-log.jsonl.
    
    Returns dict with {id, path, ok} or {ok: false, error: str}.
    """
    if not paper_id or not paper_id.strip():
        return {"ok": False, "error": "paper_id is required"}
    if not excerpt or not excerpt.strip():
        return {"ok": False, "error": "excerpt is required"}
    
    import secrets
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    seq = secrets.token_hex(4)  # 8 hex chars
    entry_id = f"rln_{date_str}_{seq}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    entry = {
        "id": entry_id,
        "paper_id": paper_id,
        "project": project,
        "section": section,
        "excerpt": excerpt,
        "context": context,
        "usage": usage,
        "note": note,
        "tags": tags or [],
        "created_at": now_iso,
        "agent": agent,
        "verified": False,
    }

    filepath = get_reading_log_path(vault)
    _ensure_logs_dir(vault)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {"ok": True, "id": entry_id, "path": str(filepath)}


def read_all_reading_notes(vault: Path) -> list[dict]:
    """Read all reading notes from reading-log.jsonl."""
    filepath = get_reading_log_path(vault)
    if not filepath.exists():
        return []
    entries = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(
                        "Skipping unparseable line in %s: %s", filepath, line[:100]
                    )
                    continue
    return entries


def get_reading_notes_for_paper(vault: Path, paper_id: str) -> list[dict]:
    """Get all reading notes for a specific paper."""
    all_notes = read_all_reading_notes(vault)
    return [n for n in all_notes if n.get("paper_id") == paper_id]


# ── Project Log ──────────────────────────────────────────────

def get_project_log_path(vault: Path) -> Path:
    return _logs_dir(vault) / "project-log.jsonl"


def append_project_entry(vault: Path, entry: dict) -> dict:
    """Append a project log entry to project-log.jsonl.
    
    entry must have: project, date, type, title.
    Auto-generates id and created_at if missing.
    """
    import secrets
    date_str = entry.get("date", datetime.datetime.now().strftime("%Y-%m-%d"))
    seq = secrets.token_hex(4)  # 8 hex chars
    entry_id = f"plog_{date_str}_{seq}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    entry["id"] = entry.get("id", entry_id)
    entry["created_at"] = entry.get("created_at", now_iso)
    # Ensure JSON-serializable fields
    entry.setdefault("decisions", [])
    entry.setdefault("detours", [])
    entry.setdefault("reusable", [])
    entry.setdefault("todos", [])
    entry.setdefault("related_papers", [])
    entry.setdefault("tags", [])
    entry.setdefault("agent", "")

    filepath = get_project_log_path(vault)
    _ensure_logs_dir(vault)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {"ok": True, "id": entry["id"], "path": str(filepath)}


def read_all_project_entries(vault: Path) -> list[dict]:
    """Read all project log entries."""
    filepath = get_project_log_path(vault)
    if not filepath.exists():
        return []
    entries = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(
                        "Skipping unparseable line in %s: %s", filepath, line[:100]
                    )
                    continue
    return entries


def get_project_entries(vault: Path, project: str) -> list[dict]:
    """Get entries for a specific project."""
    all_entries = read_all_project_entries(vault)
    return [e for e in all_entries if e.get("project") == project]
```

- [ ] **Step 3: Verify imports work**

Run: `python -c "from paperforge.memory.permanent import append_reading_note; print('OK')"`

- [ ] **Step 4: Commit**

```bash
git add paperforge/memory/permanent.py
git commit -m "feat: add permanent JSONL storage layer for reading-log and project-log"
```

---

## Task 3: Reading-Log CLI Upgrade — JSONL + context/tags/project + render

**Files:**
- Modify: `paperforge/commands/reading_log.py`
- Modify: `paperforge/cli.py:288-300`
- Modify: `paperforge/memory/events.py` (add context/tags fields to write_reading_note)

Update the existing `reading-log` CLI to:
1. Write to JSONL (permanent) AND paper_events (for FTS search in DB)
2. Support new fields: `--context`, `--tags`, `--project`
3. Add `--render` subcommand to generate markdown per project

- [ ] **Step 1: Add new CLI arguments**

In `cli.py`, find the `reading-log` subparser (line 288) and add:

```python
p_rl.add_argument("--context", help="Full paragraph containing excerpt")
p_rl.add_argument("--tags", help="Comma-separated tags")
p_rl.add_argument("--project", help="Associated project name")
p_rl.add_argument("--render", action="store_true", help="Render reading-log.md for one or all projects")
```

- [ ] **Step 2: Update write_reading_note() in events.py**

Add optional parameters: `context`, `project`, `tags`. Update payload dict to include them.

In `paperforge/memory/events.py`, modify `write_reading_note()`:

```python
def write_reading_note(vault: Path, paper_id: str, section: str,
                       excerpt: str, usage: str = "", note: str = "",
                       context: str = "", project: str = "",
                       tags: list[str] | None = None) -> bool:
    payload = {
        "section": section,
        "excerpt": excerpt,
        "context": context,
        "usage": usage,
        "note": note,
        "project": project,
        "tags": tags or [],
    }
    # ... rest unchanged
```

- [ ] **Step 3: Add JSONL write + render logic to reading_log.py**

In `commands/reading_log.py`, update the `run()` function:

```python
# Add import at top:
from paperforge.memory.permanent import (
    append_reading_note,
    get_reading_notes_for_paper,
    read_all_reading_notes,
)

# In run(), update the write section (around line 268):
if args.paper_id and args.excerpt:
    # 1. Write to permanent JSONL (source of truth)
    import json as _json
    tags = []
    if getattr(args, "tags", ""):
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    
    result = append_reading_note(
        vault,
        args.paper_id,
        getattr(args, "section", "") or "",
        args.excerpt,
        getattr(args, "usage", "") or "",
        getattr(args, "context", "") or "",
        getattr(args, "note", "") or "",
        getattr(args, "project", "") or "",
        tags,
    )
    
# 3. Also write to paper_events for FTS in DB
    db_ok = write_reading_note(
        vault, args.paper_id,
        getattr(args, "section", "") or "",
        args.excerpt,
        getattr(args, "usage", "") or "",
        getattr(args, "note", "") or "",
        getattr(args, "context", "") or "",
        getattr(args, "project", "") or "",
        tags,
    )
    
    # 4. Auto-render if project specified
    if getattr(args, "project", ""):
        _render_reading_log_md(vault, args.project)
    
    ok = result.get("ok", False)
    result_obj = PFResult(
        ok=ok,
        command="reading-log",
        version=PF_VERSION,
        data={"written": ok, "id": result.get("id")},
    )
    # ... output logic
```

- [ ] **Step 4: Add render function + correction write path**

Add to `reading_log.py`:

```python
# Add import at top of file:
from paperforge.memory.permanent import (
    append_reading_note,
    get_reading_notes_for_paper,
    read_all_reading_notes,
)

def _render_reading_log_md(vault: Path, project: str = "") -> None:
    """Render reading-log.md for a specific project from JSONL."""
    all_notes = read_all_reading_notes(vault)
    
    # Filter by project if specified
    if project:
        notes = [n for n in all_notes if n.get("project") == project]
    else:
        notes = all_notes
    
    if not notes:
        return
    
    # Build markdown
    lines = ["# Reading Log", ""]
    if project:
        lines[0] = f"# Reading Log — {project}"
    lines.append("> Auto-generated from reading-log.jsonl. Do not edit manually.")
    lines.append("")
    
    # Group by paper_id
    from collections import defaultdict
    by_paper = defaultdict(list)
    for n in notes:
        by_paper[n["paper_id"]].append(n)
    
    for paper_id, paper_notes in sorted(by_paper.items()):
        first = paper_notes[0]
        lines.append(f"## {paper_id}")
        if first.get("project"):
            lines.append(f"**Project:** {first['project']}")
        lines.append("")
        
        for entry in sorted(paper_notes, key=lambda x: x.get("created_at", "")):
            lines.append(f"### {entry.get('section', '(no section)')}")
            lines.append(f"**Info:** \"{entry['excerpt']}\"")
            if entry.get("context"):
                lines.append("")
                lines.append(f"> {entry['context']}")
            lines.append(f"**Use:** {entry.get('usage', '')}")
            if entry.get("note"):
                lines.append(f"**Note:** {entry['note']}")
            if entry.get("tags"):
                lines.append(f"**Tags:** {', '.join(entry['tags'])}")
            if entry.get("verified"):
                lines.append("**Verified:** yes")
            lines.append("")
        lines.append("---")
        lines.append("")
    
    # Write to project directory or general location
    from paperforge.config import paperforge_paths
    paths = paperforge_paths(vault)
    
    if project:
        resource_dir = paths.get("resources")
        if resource_dir:
            output_dir = resource_dir / "Projects" / project
        else:
            output_dir = vault / "Projects" / project
    else:
        output_dir = paths.get("paperforge", vault / "System" / "PaperForge") / "logs" / "rendered"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "reading-log.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
```

- [ ] **Step 6: Add correction_note write support**

In `reading_log.py`, add a `--correct` path for writing correction notes. These reference a prior reading_note by ID and record the correction in `paper_events`.

```python
# In run(), before the existing export logic, add:
if getattr(args, "correct_id", None):
    correction = getattr(args, "correction", "") or ""
    reason = getattr(args, "reason", "") or ""
    if not correction:
        result = PFResult(ok=False, command="reading-log", version=PF_VERSION,
                        error=PFError(code=ErrorCode.VALIDATION_ERROR, message="--correction is required for --correct"))
        ...
        return 1
    
    # Write correction_note to paper_events
    payload = {
        "ref_id": args.correct_id,
        "correction": correction,
        "reason": reason,
    }
    conn = get_connection(get_memory_db_path(vault), read_only=False)
    try:
        conn.execute(
            "INSERT INTO paper_events (paper_id, event_type, payload_json) VALUES (?, 'correction_note', ?)",
            (args.correct_id.split("_")[0], json.dumps(payload, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()
    ...
```

Also add to CLI subparser:
```python
p_rl.add_argument("--correct", dest="correct_id", help="ID of prior reading note to correct")
p_rl.add_argument("--correction", help="Correction text")
p_rl.add_argument("--reason", help="Reason for correction (e.g. 'Rechecked figure legend')")
```

- [ ] **Step 7: Commit**

```python
if getattr(args, "render", False):
    project = getattr(args, "project", "") or ""
    _render_reading_log_md(vault, project)
    result = PFResult(
        ok=True, command="reading-log", version=PF_VERSION,
        data={"rendered": True, "project": project},
    )
    if args.json:
        print(result.to_json())
    else:
        print(f"Rendered reading-log.md for {'all projects' if not project else project}")
    return 0
```

- [ ] **Step 6: Commit**

```bash
git add paperforge/commands/reading_log.py paperforge/cli.py paperforge/memory/events.py
git commit -m "feat: upgrade reading-log to JSONL with context/tags/project fields and auto-render"
```

---

## Task 4: Paper-Context CLI Command

**Files:**
- Create: `paperforge/commands/paper_context.py`
- Modify: `paperforge/cli.py` (add subparser + dispatch)

Build the `paperforge paper-context <key> --json` command.

- [ ] **Step 1: Add CLI subparser**

In `cli.py`, after the `paper-status` subparser (line 286):

```python
p_pc = sub.add_parser("paper-context", help="Get full context for a paper (metadata + reading notes + corrections)")
p_pc.add_argument("key", help="Zotero key")
p_pc.add_argument("--json", action="store_true", help="Output as JSON")
```

- [ ] **Step 2: Add dispatch in main()**

In `cli.py` main(), add after paper-status dispatch:

```python
if args.command == "paper-context":
    from paperforge.commands import paper_context
    return paper_context.run(args)
```

- [ ] **Step 3: Write paper_context.py**

```python
from __future__ import annotations

import argparse
import sys

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.permanent import get_reading_notes_for_paper


def _build_paper_context(vault, key: str) -> dict | None:
    """Build full context for a paper: metadata + reading notes + corrections."""
    
    # Get paper from DB
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return None
    
    conn = get_connection(db_path, read_only=True)
    try:
        row = conn.execute(
            """SELECT zotero_key, citation_key, title, year, doi, journal,
                      first_author, domain, collection_path, has_pdf,
                      ocr_status, analyze, deep_reading_status, lifecycle,
                      next_step, pdf_path, note_path, fulltext_path, paper_root
               FROM papers WHERE zotero_key = ?""",
            (key,),
        ).fetchone()
        
        if not row:
            return None
        
        paper = dict(row)
        
        # Get reading notes from permanent JSONL
        prior_notes = get_reading_notes_for_paper(vault, key)
        
        # Get corrections from paper_events
        corrections = []
        corr_rows = conn.execute(
            """SELECT created_at, payload_json
               FROM paper_events
               WHERE paper_id = ? AND event_type = 'correction_note'
               ORDER BY created_at DESC""",
            (key,),
        ).fetchall()
        for cr in corr_rows:
            import json
            payload = json.loads(cr["payload_json"])
            corrections.append({
                "created_at": cr["created_at"],
                "previous_note_id": payload.get("ref_id", ""),
                "correction": payload.get("correction", ""),
                "reason": payload.get("reason", ""),
            })
        
        # Build recheck targets (unverified notes)
        recheck_targets = []
        for n in prior_notes:
            if not n.get("verified", False):
                recheck_targets.append(
                    f"{n.get('section', 'unknown')}: {n.get('excerpt', '')[:80]}..."
                )
        
        return {
            "warning": "Prior reading notes are not verified facts. Re-check source before reuse.",
            "paper": paper,
            "prior_notes": prior_notes,
            "corrections": corrections,
            "recheck_targets": recheck_targets,
        }
    finally:
        conn.close()


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    key = args.key
    
    context = _build_paper_context(vault, key)
    
    if context is None:
        result = PFResult(
            ok=False,
            command="paper-context",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.PATH_NOT_FOUND,
                message=f"No paper found for key: {key}",
            ),
        )
    else:
        result = PFResult(
            ok=True,
            command="paper-context",
            version=PF_VERSION,
            data=context,
        )
    
    if args.json:
        print(result.to_json())
    else:
        if result.ok:
            p = result.data["paper"]
            print(f"Paper: {p.get('title', key)}")
            print(f"  Key: {p.get('zotero_key', '')}")
            print(f"  OCR: {p.get('ocr_status', 'unknown')}")
            print(f"  Lifecycle: {p.get('lifecycle', '')}")
            notes = result.data.get("prior_notes", [])
            print(f"  Reading notes: {len(notes)}")
            print(f"  Corrections: {len(result.data.get('corrections', []))}")
            if result.data.get("recheck_targets"):
                print(f"  Recheck targets: {len(result.data['recheck_targets'])}")
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
    
    return 0 if result.ok else 1
```

- [ ] **Step 4: Commit**

```bash
git add paperforge/commands/paper_context.py paperforge/cli.py
git commit -m "feat: add paper-context CLI command for reading-log safety loop"
```

---

## Task 5: Project-Log CLI Command

**Files:**
- Create: `paperforge/commands/project_log.py`
- Modify: `paperforge/cli.py` (add subparser + dispatch)

- [ ] **Step 1: Add CLI subparser**

In `cli.py`, after the reading-log subparser block:

```python
p_pl = sub.add_parser("project-log", help="Record or render project work logs")
p_pl.add_argument("--write", action="store_true", help="Write a new project log entry")
p_pl.add_argument("--payload", help="JSON payload for the entry")
p_pl.add_argument("--project", help="Project name (required for write/list/render)")
p_pl.add_argument("--list", action="store_true", help="List all entries for a project")
p_pl.add_argument("--render", action="store_true", help="Render project-log.md")
p_pl.add_argument("--limit", type=int, default=50, help="Max entries to list")
p_pl.add_argument("--json", action="store_true", help="Output as PFResult JSON")
```

- [ ] **Step 2: Add dispatch**

In `cli.py` main():

```python
if args.command == "project-log":
    from paperforge.commands import project_log
    return project_log.run(args)
```

- [ ] **Step 3: Write project_log.py**

```python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.config import paperforge_paths
from paperforge.memory.permanent import (
    append_project_entry,
    get_project_entries,
    read_all_project_entries,
)


def _render_project_log_md(vault: Path, project: str) -> None:
    """Render project-log.md from JSONL."""
    entries = get_project_entries(vault, project)
    if not entries:
        return
    
    lines = [f"# Project Log — {project}", ""]
    lines.append("> Auto-generated from project-log.jsonl. Do not edit manually.")
    lines.append("")
    
    for entry in sorted(entries, key=lambda x: x.get("created_at", ""), reverse=True):
        lines.append(f"## {entry.get('date', '')} — {entry.get('title', '(untitled)')}")
        lines.append(f"**Type:** {entry.get('type', '')}")
        lines.append("")
        
        if entry.get("decisions"):
            lines.append("### 核心决策")
            for d in entry["decisions"]:
                lines.append(f"- {d}")
            lines.append("")
        
        if entry.get("detours"):
            lines.append("### 弯路与修正")
            for dt in entry["detours"]:
                if isinstance(dt, dict):
                    lines.append(f"- **错误:** {dt.get('wrong', '')}")
                    lines.append(f"  **纠正:** {dt.get('correction', '')}")
                    lines.append(f"  **解决:** {dt.get('resolution', '')}")
                else:
                    lines.append(f"- {dt}")
            lines.append("")
        
        if entry.get("reusable"):
            lines.append("### 可复用方法论")
            for r in entry["reusable"]:
                lines.append(f"- {r}")
            lines.append("")
        
        if entry.get("todos"):
            lines.append("### 待办")
            for t in entry["todos"]:
                done = "x" if t.get("done", False) else " "
                lines.append(f"- [{done}] {t.get('content', '')}")
            lines.append("")
        
        if entry.get("tags"):
            lines.append(f"**Tags:** {', '.join(entry['tags'])}")
        
        lines.append("---")
        lines.append("")
    
    from paperforge.config import paperforge_paths
    paths = paperforge_paths(vault)
    resource_dir = paths.get("resources")
    if resource_dir:
        output_dir = resource_dir / "Projects" / project
    else:
        output_dir = vault / "Projects" / project
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "project-log.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    
    if getattr(args, "write", False):
        project = getattr(args, "project", "")
        payload_str = getattr(args, "payload", "")
        
        if not project:
            result = PFResult(ok=False, command="project-log", version=PF_VERSION,
                            error=PFError(code=ErrorCode.VALIDATION_ERROR, message="--project is required for --write"))
            print(result.to_json() if getattr(args, "json", False) else result.error.message, 
                  file=sys.stderr if not getattr(args, "json", False) else sys.stdout)
            return 1
        
        if not payload_str:
            result = PFResult(ok=False, command="project-log", version=PF_VERSION,
                            error=PFError(code=ErrorCode.VALIDATION_ERROR, message="--payload is required for --write"))
            print(result.to_json() if getattr(args, "json", False) else result.error.message,
                  file=sys.stderr if not getattr(args, "json", False) else sys.stdout)
            return 1
        
        try:
            entry = json.loads(payload_str)
            entry["project"] = project
            result_data = append_project_entry(vault, entry)
            
            # Auto-render
            _render_project_log_md(vault, project)
            
            result = PFResult(ok=True, command="project-log", version=PF_VERSION, data=result_data)
        except json.JSONDecodeError as e:
            result = PFResult(ok=False, command="project-log", version=PF_VERSION,
                            error=PFError(code=ErrorCode.VALIDATION_ERROR, message=f"Invalid JSON: {e}"))
        
        if getattr(args, "json", False):
            print(result.to_json())
        else:
            print("Written." if result.ok else f"Error: {result.error.message}")
        return 0 if result.ok else 1
    
    if getattr(args, "list", False):
        project = getattr(args, "project", "")
        if not project:
            result = PFResult(ok=False, command="project-log", version=PF_VERSION,
                            error=PFError(code=ErrorCode.VALIDATION_ERROR, message="--project is required for --list"))
            print(result.to_json() if getattr(args, "json", False) else result.error.message,
                  file=sys.stderr if not getattr(args, "json", False) else sys.stdout)
            return 1
        
        entries = get_project_entries(vault, project)
        data = {"project": project, "entries": entries[:getattr(args, "limit", 50)], "count": len(entries)}
        result = PFResult(ok=True, command="project-log", version=PF_VERSION, data=data)
        
        if getattr(args, "json", False):
            print(result.to_json())
        else:
            print(f"{len(entries)} entries for project '{project}'")
            for e in entries[:5]:
                print(f"  [{e['date']}] {e['type']}: {e['title']}")
        return 0
    
    if getattr(args, "render", False):
        project = getattr(args, "project", "")
        if not project:
            result = PFResult(ok=False, command="project-log", version=PF_VERSION,
                            error=PFError(code=ErrorCode.VALIDATION_ERROR, message="--project is required for --render"))
            print(result.to_json() if getattr(args, "json", False) else result.error.message,
                  file=sys.stderr if not getattr(args, "json", False) else sys.stdout)
            return 1
        
        _render_project_log_md(vault, project)
        result = PFResult(ok=True, command="project-log", version=PF_VERSION,
                         data={"rendered": True, "project": project})
        if getattr(args, "json", False):
            print(result.to_json())
        else:
            print(f"Rendered project-log.md for '{project}'")
        return 0
    
    # Default: show all projects with entry counts
    all_entries = read_all_project_entries(vault)
    from collections import Counter
    project_counts = Counter(e["project"] for e in all_entries if e.get("project"))
    
    result = PFResult(ok=True, command="project-log", version=PF_VERSION,
                     data={"projects": dict(project_counts)})
    if getattr(args, "json", False):
        print(result.to_json())
    else:
        if project_counts:
            print("Projects with log entries:")
            for proj, cnt in project_counts.most_common():
                print(f"  {proj}: {cnt} entries")
        else:
            print("No project log entries found.")
    return 0
```

- [ ] **Step 4: Commit**

```bash
git add paperforge/commands/project_log.py paperforge/cli.py
git commit -m "feat: add project-log CLI command with JSONL write + auto-render"
```

---

## Task 6: DB Builder — Import JSONL on rebuild

**Files:**
- Modify: `paperforge/memory/builder.py`

When `paperforge memory build` runs, it should import reading-log.jsonl → reading_log table and project-log.jsonl → project_log table.

- [ ] **Step 1: Add import functions**

In `builder.py`, add:

```python
import json as _json
from paperforge.memory.permanent import read_all_reading_notes, read_all_project_entries


def _import_reading_log(conn, vault: Path) -> int:
    """Import reading-log.jsonl into reading_log table. Returns count."""
    notes = read_all_reading_notes(vault)
    conn.execute("DELETE FROM reading_log")
    count = 0
    for note in notes:
        conn.execute(
            """INSERT INTO reading_log (id, paper_id, project, section, excerpt, context, usage, note, tags_json, created_at, agent, verified)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                note["id"], note["paper_id"],
                note.get("project", ""),
                note["section"], note["excerpt"],
                note.get("context", ""), note["usage"],
                note.get("note", ""),
                _json.dumps(note.get("tags", []), ensure_ascii=False),
                note["created_at"],
                note.get("agent", ""),
                1 if note.get("verified") else 0,
            ),
        )
        count += 1
    return count


def _import_project_log(conn, vault: Path) -> int:
    """Import project-log.jsonl into project_log table. Returns count."""
    entries = read_all_project_entries(vault)
    conn.execute("DELETE FROM project_log")
    count = 0
    for entry in entries:
        conn.execute(
            """INSERT INTO project_log (id, project, date, type, title, decisions_json, detours_json, reusable_json, todos_json, related_papers_json, tags_json, created_at, agent)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry["id"], entry["project"],
                entry.get("date", ""), entry["type"], entry["title"],
                _json.dumps(entry.get("decisions", []), ensure_ascii=False),
                _json.dumps(entry.get("detours", []), ensure_ascii=False),
                _json.dumps(entry.get("reusable", []), ensure_ascii=False),
                _json.dumps(entry.get("todos", []), ensure_ascii=False),
                _json.dumps(entry.get("related_papers", []), ensure_ascii=False),
                _json.dumps(entry.get("tags", []), ensure_ascii=False),
                entry.get("created_at", ""),
                entry.get("agent", ""),
            ),
        )
        count += 1
    return count
```

- [ ] **Step 2: Call import functions in build flow**

Find the build function in `builder.py` and add after papers import:

```python
reading_count = _import_reading_log(conn, vault)
logger.info(f"Imported {reading_count} reading notes from JSONL")

project_count = _import_project_log(conn, vault)
logger.info(f"Imported {project_count} project log entries from JSONL")

# Clear paper_events to prevent duplicate accumulation from previous rebuilds
# Note: correction_note events also live here; consider dual-writing corrections to
# reading-log.jsonl in future to preserve them across rebuilds.
conn.execute("DELETE FROM paper_events WHERE event_type != 'correction_note';")
```

- [ ] **Step 3: Commit**

```bash
git add paperforge/memory/builder.py
git commit -m "feat: import JSONL into DB on memory build"
```

---

## Task 7: METHODOLOGY_COMPACT.md Creation

**Files:**
- Create: `fixtures/methodology/METHODOLOGY_COMPACT.md`
- Modify: `paperforge/setup_wizard.py` (optional, deploy template)

Create the default methodology compact file. This goes in:

- **Vault location**: `<system_dir>/PaperForge/methodology/METHODOLOGY_COMPACT.md` (NOT in `archive/`)
- **Package fixture**: `fixtures/methodology/METHODOLOGY_COMPACT.md` (copied during setup)
- **Note**: `pf_bootstrap.py` scans `archive/` for method cards; `METHODOLOGY_COMPACT.md` is deliberately outside `archive/` since it's a system file, not a searchable card.

- [ ] **Step 1: Create the file**

```markdown
# PaperForge Methodology Compact

## General
- Separate source fact, interpretation, and intended use.
- Prior reading-log is not verified fact; re-check source before reuse.
- When user corrects a judgment, record the correction if relevant.

## Literature work
- Do not collapse heterogeneous studies without comparing model, parameter, endpoint, and measurement layer.
- Distinguish device-level settings from local biological exposure.
- Confirm within-study internal chain (material→output→effect) before making cross-study claims.

## Clinical research
- Separate candidate variables, selected variables, final model variables, and sensitivity variables.
- Do not infer causality from predictive variables.

## Writing
- Do not write unsupported claims. Every factual claim must have a source reference.
- Prefer bounded conclusions over broad overclaims.
- Distinguish "the paper says X" from "I infer Y from X".
```

- [ ] **Step 2: Ensure setup wizard creates methodology directory**

In `setup_wizard.py` or `setup/` modules, ensure `System/PaperForge/methodology/archive/` is created and METHODOLOGY_COMPACT.md is copied.

- [ ] **Step 3: Verify methodology index scanning in pf_bootstrap.py**

The `_scan_methodology_archive()` function already reads from `System/PaperForge/methodology/archive/`. Verify it works with the actual file structure.

- [ ] **Step 4: Commit**

```bash
git add fixtures/methodology/METHODOLOGY_COMPACT.md
git commit -m "feat: add METHODOLOGY_COMPACT.md for agent guidance"
```

---

## Task 8: Integration — Wire Everything Together

**Files:**
- Modify: `paperforge/skills/paperforge/SKILL.md` (verify CLI references are correct)

- [ ] **Step 1: Verify skill SKILL.md references correct commands**

Check that SKILL.md and all workflow files reference the correct CLI commands (`paper-context`, `reading-log --write`, etc.) with correct parameter names.

- [ ] **Step 2: Smoke test the full flow**

```bash
# Test paper-context
$PYTHON -m paperforge paper-context ABC12345 --json --vault <test_vault>

# Test reading-log write
$PYTHON -m paperforge reading-log --write ABC12345 \
    --section "Results Fig.3" --excerpt "test" --usage "test" \
    --context "test context" --project "test-project" \
    --vault <test_vault>

# Test reading-log render
$PYTHON -m paperforge reading-log --render --project "test-project" --vault <test_vault>

# Test project-log write
$PYTHON -m paperforge project-log --write --project "test-project" \
    --payload '{"date":"2026-05-14","type":"note","title":"test"}' \
    --vault <test_vault>

# Test project-log render
$PYTHON -m paperforge project-log --render --project "test-project" --vault <test_vault>
```

- [ ] **Step 3: Commit**

```bash
git add paperforge/skills/paperforge/SKILL.md
git commit -m "chore: verify skill CLI references match new commands"
```

---

## Summary

| Task | Files | Description |
|------|-------|-------------|
| 1 | `memory/schema.py` | Add reading_log + project_log DB tables |
| 2 | `memory/permanent.py` (new) | JSONL append/read for both log types |
| 3 | `commands/reading_log.py`, `cli.py`, `memory/events.py` | Upgrade reading-log CLI with JSONL + new fields + render |
| 4 | `commands/paper_context.py` (new), `cli.py` | New paper-context command |
| 5 | `commands/project_log.py` (new), `cli.py` | New project-log CLI |
| 6 | `memory/builder.py` | Import JSONL → DB on rebuild |
| 7 | `fixtures/methodology/METHODOLOGY_COMPACT.md` (new) | Default methodology compact |
| 8 | Skill files | Verify references, smoke test |

### Build order dependencies
Task 2 → Task 3 (JSONL storage needed for CLI)
Task 2 → Task 4 (paper-context reads reading notes from JSONL)
Task 2 → Task 5 (project-log writes to JSONL)
Task 2 → Task 6 (DB import reads from JSONL)
Task 7 is independent
