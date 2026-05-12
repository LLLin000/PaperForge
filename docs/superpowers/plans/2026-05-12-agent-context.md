# agent-context — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add `paperforge agent-context --json` command that gives agents a library overview, command catalog, collection map, and behavior rules in one call.

**Architecture:** New `paperforge/memory/context.py` queries paperforge.db for aggregated stats. CLI wrapper in `paperforge/commands/agent_context.py`. Pure read-only, no file scanning.

**Tech Stack:** Python stdlib `sqlite3`, existing `paperforge.memory.db`, `paperforge.core.result.PFResult`.

**Spec:** `docs/superpowers/specs/2026-05-12-memory-layer-phase2-5-design.md`

**Prerequisites:** Memory Layer Phase 1 + FTS5 already implemented on `feature/memory` branch.

---

## File Structure

```
Create:
  paperforge/memory/context.py          — get_agent_context(vault) -> dict
  paperforge/commands/agent_context.py  — CLI run(args) -> int
  tests/unit/memory/test_context.py     — unit tests

Modify:
  paperforge/cli.py                     — add "agent-context" subparser + dispatch
  paperforge/commands/__init__.py       — add to _COMMAND_REGISTRY
```

---

### Task 1: `paperforge/memory/context.py`

**Files:**
- Create: `paperforge/memory/context.py`
- Create: `tests/unit/memory/test_context.py`

- [ ] **Step 1: Write `paperforge/memory/context.py`**

```python
from __future__ import annotations

from pathlib import Path

from paperforge.memory.db import get_connection, get_memory_db_path


def _build_collection_tree(conn) -> list[dict]:
    """Build collection hierarchy from papers.collection_path.
    
    Each collection_path is pipe-separated, e.g. "骨科 | 骨折".
    Returns flat list of top-level collections with sub-collections.
    """
    rows = conn.execute(
        "SELECT collection_path, COUNT(*) as cnt FROM papers "
        "WHERE collection_path != '' "
        "GROUP BY collection_path ORDER BY cnt DESC"
    ).fetchall()
    top: dict[str, dict] = {}
    for row in rows:
        parts = [p.strip() for p in row["collection_path"].split("|") if p.strip()]
        if not parts:
            continue
        root = parts[0]
        if root not in top:
            top[root] = {"name": root, "count": 0, "sub": []}
        top[root]["count"] += row["cnt"]
        if len(parts) > 1:
            sub_name = parts[-1]
            if sub_name not in top[root]["sub"]:
                top[root]["sub"].append(sub_name)
    for c in top.values():
        c["sub"] = sorted(c["sub"])
    return sorted(top.values(), key=lambda x: -x["count"])


def get_agent_context(vault: Path) -> dict | None:
    """Build agent context from paperforge.db — library stats + collection tree.
    
    Returns None if DB is missing or query fails.
    """
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return None

    conn = get_connection(db_path, read_only=True)
    try:
        total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]

        domains = {
            r["domain"]: r["cnt"]
            for r in conn.execute(
                "SELECT domain, COUNT(*) as cnt FROM papers GROUP BY domain ORDER BY cnt DESC"
            ).fetchall()
        }

        lifecycle_counts = {
            r["lifecycle"]: r["cnt"]
            for r in conn.execute(
                "SELECT lifecycle, COUNT(*) as cnt FROM papers GROUP BY lifecycle"
            ).fetchall()
        }

        ocr_counts = {
            r["ocr_status"]: r["cnt"]
            for r in conn.execute(
                "SELECT ocr_status, COUNT(*) as cnt FROM papers GROUP BY ocr_status"
            ).fetchall()
        }

        deep_counts = {
            r["deep_reading_status"]: r["cnt"]
            for r in conn.execute(
                "SELECT deep_reading_status, COUNT(*) as cnt FROM papers GROUP BY deep_reading_status"
            ).fetchall()
        }

        collections = _build_collection_tree(conn)

        return {
            "library": {
                "paper_count": total,
                "domain_counts": domains,
                "lifecycle_counts": lifecycle_counts,
                "ocr_counts": ocr_counts,
                "deep_reading_counts": deep_counts,
            },
            "collections": collections,
        }
    except Exception:
        return None
    finally:
        conn.close()
```

- [ ] **Step 2: Write `tests/unit/memory/test_context.py`**

```python
from __future__ import annotations

from pathlib import Path

from paperforge.memory.context import get_agent_context


def test_get_agent_context_returns_none_when_no_db():
    assert get_agent_context(Path("/nonexistent/vault")) is None
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/unit/memory/test_context.py -v
```

- [ ] **Step 4: Commit**

```bash
git add paperforge/memory/context.py tests/unit/memory/test_context.py
git commit -m "feat(memory): add agent context query module"
```

---

### Task 2: `paperforge/commands/agent_context.py`

**Files:**
- Create: `paperforge/commands/agent_context.py`
- Modify: `paperforge/cli.py` (add parser + dispatch)
- Modify: `paperforge/commands/__init__.py` (register)

- [ ] **Step 1: Write `paperforge/commands/agent_context.py`**

```python
from __future__ import annotations

import argparse
import sys

from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.context import get_agent_context
from paperforge import __version__ as PF_VERSION

COMMANDS = {
    "paper-status": {
        "usage": "paperforge paper-status <zotero_key|citation_key|doi|title> --json",
        "purpose": "Look up one paper's full status and recommended next action",
    },
    "search": {
        "usage": "paperforge search <query> --json [--collection NAME] [--domain NAME] [--ocr done|pending] [--year-from N] [--limit N]",
        "purpose": "Full-text search with optional collection/domain/lifecycle filters",
    },
    "retrieve": {
        "usage": "paperforge retrieve <query> --json [--limit N]",
        "purpose": "Search OCR fulltext chunks for evidence paragraphs (coming soon)",
    },
    "deep": {
        "usage": "/pf-deep <zotero_key>",
        "purpose": "Full three-pass deep reading with chart analysis",
    },
    "ocr": {
        "usage": "/pf-ocr",
        "purpose": "Run OCR on papers marked do_ocr:true",
    },
    "sync": {
        "usage": "/pf-sync",
        "purpose": "Sync Zotero and regenerate formal notes + index",
    },
}

RULES = [
    "Use paperforge.db via CLI commands before reading individual files.",
    "Do not infer paper state from stale frontmatter when memory status is fresh.",
    "Read source files only after resolving candidates via paper-status or search.",
    "To locate a paper: start with collection scope if known, then expand to full library search.",
]


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path

    library = get_agent_context(vault)
    if library is None:
        result = PFResult(
            ok=False,
            command="agent-context",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.PATH_NOT_FOUND,
                message="Memory database not found or query failed. Run paperforge memory build.",
            ),
        )
        if args.json:
            print(result.to_json())
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
        return 1

    data = {
        "paperforge": {
            "version": PF_VERSION,
            "vault": str(vault),
            "memory_db": "ready",
        },
        "library": library["library"],
        "collections": library["collections"],
        "commands": COMMANDS,
        "rules": RULES,
    }

    result = PFResult(
        ok=True,
        command="agent-context",
        version=PF_VERSION,
        data=data,
    )

    if args.json:
        print(result.to_json())
    else:
        lib = data["library"]
        print(f"Papers: {lib['paper_count']} total")
        print(f"Domains: {lib['domain_counts']}")
        print(f"Lifecycle: {lib['lifecycle_counts']}")
        for c in data.get("collections", []):
            subs = f" ({len(c['sub'])} sub)" if c["sub"] else ""
            print(f"  [{c['count']:3}] {c['name']}{subs}")

    return 0 if result.ok else 1
```

- [ ] **Step 2: Register CLI parser in `paperforge/cli.py`**

In `build_parser()`, after the search parser, add:

```python
    p_ac = sub.add_parser("agent-context", help="Generate agent bootstrap context")
    p_ac.add_argument("--json", action="store_true", help="Output as JSON")
```

In `main()` dispatch, after the search dispatch, add:

```python
        if args.command == "agent-context":
            from paperforge.commands.agent_context import run
            return run(args)
```

- [ ] **Step 3: Update `paperforge/commands/__init__.py`**

Add to `_COMMAND_REGISTRY`:
```python
    "agent-context": "paperforge.commands.agent_context",
```

- [ ] **Step 4: Verify**

```bash
python -m paperforge agent-context --help
python -m pytest tests/unit/ -q --no-header
```

- [ ] **Step 5: Commit**

```bash
git add paperforge/commands/agent_context.py paperforge/cli.py paperforge/commands/__init__.py
git commit -m "feat(cli): add agent-context command for agent bootstrap"
```

---

### Task 3: Integration test + install

- [ ] **Step 1: Reinstall + test on test vault**

```bash
pip install --force-reinstall --no-deps .  # from feature/memory
python -m paperforge --vault "D:\L\Med\test1" agent-context --json
```

Expected: full PFResult with library overview and collection tree.

- [ ] **Step 2: Verify all existing tests still pass**

```bash
python -m pytest tests/unit/ -q --no-header
```
