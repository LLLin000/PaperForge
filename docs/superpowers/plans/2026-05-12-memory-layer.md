# Memory Layer Phase 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a SQLite-backed Memory Layer with `memory build`, `memory status`, and `paper-status` commands.

**Architecture:** New `paperforge/memory/` package with connection, schema, builder, and query modules.
Commands follow the existing CLI pattern (parser registration + `commands/` module dispatch + PFResult envelope).

**Tech Stack:** Python stdlib `sqlite3`, `hashlib`, existing `paperforge.core.result`, `paperforge.worker.asset_index`, `paperforge.worker.asset_state`.

**Spec:** `docs/superpowers/specs/2026-05-12-memory-layer-design.md`

---

## File Structure Map

```
Create:
  paperforge/memory/__init__.py          — package init, re-export key types
  paperforge/memory/db.py                — get_connection(), get_memory_db_path()
  paperforge/memory/schema.py            — CURRENT_SCHEMA_VERSION, CREATE TABLE SQL, drop/create tables
  paperforge/memory/builder.py           — build_from_index() — reads formal-library.json, populates SQLite
  paperforge/memory/query.py             — lookup_paper(), get_paper_status(), get_memory_status()
  paperforge/commands/memory.py          — CLI run() for "memory build" and "memory status"
  paperforge/commands/paper_status.py    — CLI run() for "paper-status"

  tests/unit/memory/__init__.py
  tests/unit/memory/test_schema.py
  tests/unit/memory/test_builder.py
  tests/unit/memory/test_query.py

Modify:
  paperforge/config.py:330-339           — add "memory_db" path key
  paperforge/cli.py:258-259              — register "memory" and "paper-status" subcommands
  paperforge/commands/__init__.py:4-13   — add to _COMMAND_REGISTRY
```

---

### Task 1: Register `memory_db` path in config

**Files:**
- Modify: `paperforge/config.py:330-339`

- [ ] **Step 1: Add `memory_db` key to `paperforge_paths()` return dict**

```python
# At paperforge/config.py, after line 338 ("index": ...):
"memory_db": paperforge / "indexes" / "paperforge.db",
```

- [ ] **Step 2: Verify**

```bash
python -c "from paperforge.config import paperforge_paths; p=paperforge_paths(); print(p.get('memory_db'), p.get('index'))"
```

Expected: both paths point under `.../PaperForge/indexes/`.

- [ ] **Step 3: Commit**

```bash
git add paperforge/config.py
git commit -m "feat(config): add memory_db path key for Memory Layer"
```

---

### Task 2: `paperforge/memory/__init__.py` and `db.py`

**Files:**
- Create: `paperforge/memory/__init__.py`
- Create: `paperforge/memory/db.py`
- Test: `tests/unit/memory/test_schema.py` (write later)

- [ ] **Step 1: Write `__init__.py`**

```python
from __future__ import annotations

from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import ensure_schema, drop_all_tables

__all__ = [
    "get_connection",
    "get_memory_db_path",
    "ensure_schema",
    "drop_all_tables",
]
```

- [ ] **Step 2: Write `db.py`**

```python
from __future__ import annotations

import sqlite3
from pathlib import Path

from paperforge.config import paperforge_paths


def get_memory_db_path(vault: Path) -> Path:
    """Return the absolute path to paperforge.db."""
    paths = paperforge_paths(vault)
    db_path = paths.get("memory_db")
    if not db_path:
        raise FileNotFoundError("memory_db path not configured")
    return db_path


def get_connection(db_path: Path, read_only: bool = False) -> sqlite3.Connection:
    """Open a SQLite connection to paperforge.db with WAL mode.

    Args:
        db_path: Path to paperforge.db.
        read_only: If True, open in read-only mode (for queries).
    """
    if read_only:
        uri = "file:" + db_path.as_posix() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    if not read_only:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
    return conn
```

- [ ] **Step 3: Run a manual import check**

```bash
python -c "from paperforge.memory import get_connection, get_memory_db_path; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add paperforge/memory/__init__.py paperforge/memory/db.py
git commit -m "feat(memory): add db.py with connection and path resolution"
```

---

### Task 3: `paperforge/memory/schema.py`

**Files:**
- Create: `paperforge/memory/schema.py`
- Create: `tests/unit/memory/__init__.py`
- Create: `tests/unit/memory/test_schema.py`

- [ ] **Step 1: Write `schema.py` with SQL definitions**

```python
from __future__ import annotations

import sqlite3

CURRENT_SCHEMA_VERSION = 1

CREATE_META = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

CREATE_PAPERS = """
CREATE TABLE IF NOT EXISTS papers (
    zotero_key           TEXT PRIMARY KEY,
    citation_key         TEXT NOT NULL DEFAULT '',
    title                TEXT NOT NULL,
    year                 TEXT,
    doi                  TEXT,
    pmid                 TEXT,
    journal              TEXT,
    first_author         TEXT,
    authors_json         TEXT,
    abstract             TEXT,
    domain               TEXT,
    collection_path      TEXT,
    collections_json     TEXT,
    has_pdf              INTEGER NOT NULL DEFAULT 0,
    do_ocr               INTEGER,
    analyze              INTEGER,
    ocr_status           TEXT,
    deep_reading_status  TEXT,
    ocr_job_id           TEXT,
    impact_factor        REAL,
    lifecycle            TEXT,
    maturity_level       INTEGER,
    maturity_name        TEXT,
    next_step            TEXT,
    pdf_path             TEXT,
    note_path            TEXT,
    main_note_path       TEXT,
    paper_root           TEXT,
    fulltext_path        TEXT,
    ocr_md_path          TEXT,
    ocr_json_path        TEXT,
    ai_path              TEXT,
    deep_reading_md_path TEXT,
    updated_at           TEXT
);
"""

CREATE_ASSETS = """
CREATE TABLE IF NOT EXISTS paper_assets (
    paper_id       TEXT NOT NULL,
    asset_type     TEXT NOT NULL,
    path           TEXT NOT NULL,
    exists_on_disk INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (paper_id, asset_type),
    FOREIGN KEY (paper_id) REFERENCES papers(zotero_key)
);
"""

CREATE_ALIASES = """
CREATE TABLE IF NOT EXISTS paper_aliases (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id   TEXT NOT NULL,
    alias      TEXT NOT NULL,
    alias_norm TEXT NOT NULL,
    alias_type TEXT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES papers(zotero_key)
);
"""

INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);",
    "CREATE INDEX IF NOT EXISTS idx_papers_citation_key ON papers(citation_key);",
    "CREATE INDEX IF NOT EXISTS idx_papers_domain ON papers(domain);",
    "CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);",
    "CREATE INDEX IF NOT EXISTS idx_papers_ocr_status ON papers(ocr_status);",
    "CREATE INDEX IF NOT EXISTS idx_papers_deep_status ON papers(deep_reading_status);",
    "CREATE INDEX IF NOT EXISTS idx_papers_lifecycle ON papers(lifecycle);",
    "CREATE INDEX IF NOT EXISTS idx_papers_next_step ON papers(next_step);",
]

ALL_TABLES = ["papers", "paper_assets", "paper_aliases", "meta"]


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables and indexes if they don't exist."""
    conn.execute(CREATE_META)
    conn.execute(CREATE_PAPERS)
    conn.execute(CREATE_ASSETS)
    conn.execute(CREATE_ALIASES)
    for idx_sql in INDEX_SQL:
        conn.execute(idx_sql)
    conn.commit()


def drop_all_tables(conn: sqlite3.Connection) -> None:
    """Drop all Memory Layer tables (for rebuild)."""
    for table in ALL_TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {table};")
    conn.commit()


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Read the stored schema version from meta table, or 0 if not found."""
    try:
        row = conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
        return int(row["value"]) if row else 0
    except sqlite3.OperationalError:
        return 0
```

- [ ] **Step 2: Write the failing test `tests/unit/memory/test_schema.py`**

```python
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from paperforge.memory.schema import (
    ALL_TABLES,
    ensure_schema,
    drop_all_tables,
    get_schema_version,
    CURRENT_SCHEMA_VERSION,
)
from paperforge.memory.db import get_connection


def test_ensure_schema_creates_all_tables():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        conn = get_connection(db_path)
        ensure_schema(conn)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row["name"] for row in cursor.fetchall()}
        for table in ALL_TABLES:
            assert table in tables, f"Missing table: {table}"
        conn.close()
    finally:
        db_path.unlink(missing_ok=True)


def test_drop_all_tables_clears_all():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        conn = get_connection(db_path)
        ensure_schema(conn)
        drop_all_tables(conn)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row["name"] for row in cursor.fetchall()}
        assert tables == set()
        conn.close()
    finally:
        db_path.unlink(missing_ok=True)


def test_get_schema_version_returns_zero_when_no_meta():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        conn = get_connection(db_path)
        ensure_schema(conn)
        assert get_schema_version(conn) == 0
        conn.close()
    finally:
        db_path.unlink(missing_ok=True)


def test_get_schema_version_returns_stored_value():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        conn = get_connection(db_path)
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('schema_version', '1')"
        )
        conn.commit()
        assert get_schema_version(conn) == 1
        conn.close()
    finally:
        db_path.unlink(missing_ok=True)


def test_schema_version_mismatch_triggers_rebuild_semantics():
    """When stored version != CURRENT, get_schema_version returns a different int."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    try:
        conn = get_connection(db_path)
        ensure_schema(conn)
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('schema_version', '99')"
        )
        conn.commit()
        stored = get_schema_version(conn)
        assert stored != CURRENT_SCHEMA_VERSION
        conn.close()
    finally:
        db_path.unlink(missing_ok=True)
```

- [ ] **Step 3: Run tests and verify they pass**

```bash
python -m pytest tests/unit/memory/test_schema.py -v
```

- [ ] **Step 4: Commit**

```bash
git add paperforge/memory/schema.py tests/unit/memory/
git commit -m "feat(memory): add schema module with table definitions and tests"
```

---

### Task 4: `paperforge/memory/builder.py`

**Files:**
- Create: `paperforge/memory/builder.py`
- Create: `tests/unit/memory/test_builder.py`
- Modify: (none)

- [ ] **Step 1: Write `builder.py`**

```python
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from paperforge import __version__ as PF_VERSION
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import (
    CURRENT_SCHEMA_VERSION,
    ensure_schema,
    drop_all_tables,
    get_schema_version,
)
from paperforge.worker.asset_index import read_index
from paperforge.worker.asset_state import (
    compute_lifecycle,
    compute_maturity,
    compute_next_step,
)

logger = logging.getLogger(__name__)

PAPER_COLUMNS = [
    "zotero_key", "citation_key", "title", "year", "doi", "pmid",
    "journal", "first_author", "authors_json", "abstract", "domain",
    "collection_path", "collections_json",
    "has_pdf", "do_ocr", "analyze", "ocr_status", "deep_reading_status",
    "ocr_job_id", "impact_factor",
    "lifecycle", "maturity_level", "maturity_name", "next_step",
    "pdf_path", "note_path", "main_note_path", "paper_root",
    "fulltext_path", "ocr_md_path", "ocr_json_path", "ai_path",
    "deep_reading_md_path", "updated_at",
]

ASSET_FIELDS = [
    ("pdf", "pdf_path"),
    ("formal_note", "note_path"),
    ("main_note", "main_note_path"),
    ("ocr_fulltext", "fulltext_path"),
    ("ocr_meta", "ocr_json_path"),
    ("deep_reading", "main_note_path"),
    ("ai_dir", "ai_path"),
]

ALIAS_TYPES = ["zotero_key", "citation_key", "title", "doi"]


def compute_hash(items: list[dict]) -> str:
    sorted_items = sorted(items, key=lambda e: e["zotero_key"])
    raw = json.dumps(sorted_items, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _resolve_vault_path(vault: Path, rel_path: str) -> Path:
    if not rel_path:
        return Path()
    p = vault / rel_path
    return p.resolve() if p.exists() else p


def build_from_index(vault: Path) -> dict:
    """Read formal-library.json and build/rebuild paperforge.db.
    
    Returns a dict with counts for reporting.
    """
    envelope = read_index(vault)
    if envelope is None:
        raise FileNotFoundError(
            "Canonical index not found. Run paperforge sync --rebuild-index."
        )
    # Legacy format: bare list of entries (pre-envelope)
    if isinstance(envelope, list):
        items = envelope
        generated_at = ""
    else:
        items = envelope.get("items", [])
        generated_at = envelope.get("generated_at", "")
    if isinstance(items, list) and items and isinstance(items[0], dict):
        canonical_hash = compute_hash(items)
    else:
        canonical_hash = ""

    db_path = get_memory_db_path(vault)
    conn = get_connection(db_path, read_only=False)
    try:
        stored_version = get_schema_version(conn)
        if stored_version != CURRENT_SCHEMA_VERSION:
            drop_all_tables(conn)
        ensure_schema(conn)

        conn.execute("DELETE FROM paper_aliases;")
        conn.execute("DELETE FROM paper_assets;")
        conn.execute("DELETE FROM papers;")

        now_utc = datetime.now(timezone.utc).isoformat()
        papers_count = 0
        assets_count = 0
        aliases_count = 0

        for entry in items:
            zotero_key = entry.get("zotero_key", "")
            if not zotero_key:
                continue

            lifecycle = str(compute_lifecycle(entry))
            maturity = compute_maturity(entry)
            next_step = str(compute_next_step(entry))

            paper_values = {}
            for col in PAPER_COLUMNS:
                if col == "authors_json":
                    paper_values[col] = json.dumps(
                        entry.get("authors", []), ensure_ascii=False
                    )
                elif col == "collections_json":
                    paper_values[col] = json.dumps(
                        entry.get("collections", []), ensure_ascii=False
                    )
                elif col == "lifecycle":
                    paper_values[col] = lifecycle
                elif col == "maturity_level":
                    paper_values[col] = maturity.get("level", 1)
                elif col == "maturity_name":
                    paper_values[col] = maturity.get("level_name", "")
                elif col == "next_step":
                    paper_values[col] = next_step
                elif col == "updated_at":
                    paper_values[col] = generated_at
                elif col in ("do_ocr", "analyze"):
                    val = entry.get(col)
                    paper_values[col] = 1 if val else 0
                elif col == "has_pdf":
                    paper_values[col] = 1 if entry.get("has_pdf") else 0
                else:
                    paper_values[col] = entry.get(col, "")

            placeholders = ", ".join([f":{c}" for c in PAPER_COLUMNS])
            cols = ", ".join(PAPER_COLUMNS)
            conn.execute(
                f"INSERT OR REPLACE INTO papers ({cols}) VALUES ({placeholders})",
                paper_values,
            )
            papers_count += 1

            for asset_type, entry_field in ASSET_FIELDS:
                path_val = entry.get(entry_field, "")
                if not path_val:
                    continue
                rel_path = str(path_val).replace("\\", "/")
                abs_path = _resolve_vault_path(vault, rel_path)
                exists = 1 if abs_path.exists() else 0

                if asset_type == "deep_reading":
                    if abs_path.exists():
                        try:
                            content = abs_path.read_text(encoding="utf-8")
                            exists = 1 if "## 🔍 精读" in content else 0
                        except Exception:
                            exists = 0

                conn.execute(
                    """INSERT OR REPLACE INTO paper_assets
                       (paper_id, asset_type, path, exists_on_disk)
                       VALUES (?, ?, ?, ?)""",
                    (zotero_key, asset_type, rel_path, exists),
                )
                assets_count += 1

            for alias_type in ALIAS_TYPES:
                raw_val = entry.get(alias_type, "")
                if not raw_val:
                    continue
                raw_str = str(raw_val)
                conn.execute(
                    """INSERT OR REPLACE INTO paper_aliases
                       (paper_id, alias, alias_norm, alias_type)
                       VALUES (?, ?, ?, ?)""",
                    (
                        zotero_key,
                        raw_str,
                        raw_str.lower().strip(),
                        alias_type,
                    ),
                )
                aliases_count += 1

        meta_upserts = [
            ("schema_version", str(CURRENT_SCHEMA_VERSION)),
            ("paperforge_version", PF_VERSION),
            ("created_at", now_utc),
            ("last_full_build_at", now_utc),
            ("canonical_index_hash", canonical_hash),
            ("canonical_index_generated_at", generated_at),
        ]
        for key, value in meta_upserts:
            conn.execute(
                """INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)""",
                (key, value),
            )

        conn.commit()

        return {
            "db_path": str(db_path),
            "papers_indexed": papers_count,
            "assets_indexed": assets_count,
            "aliases_indexed": aliases_count,
            "schema_version": str(CURRENT_SCHEMA_VERSION),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

- [ ] **Step 2: Write the test `tests/unit/memory/test_builder.py`**

Note: This test needs an actual `formal-library.json` fixture. Use the existing test vault.

```python
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from paperforge.memory.builder import build_from_index, compute_hash


def test_compute_hash_deterministic():
    items1 = [{"zotero_key": "A"}, {"zotero_key": "B"}]
    items2 = [{"zotero_key": "B"}, {"zotero_key": "A"}]
    assert compute_hash(items1) == compute_hash(items2)


def test_compute_hash_different_for_different_data():
    items1 = [{"zotero_key": "A", "title": "X"}]
    items2 = [{"zotero_key": "A", "title": "Y"}]
    assert compute_hash(items1) != compute_hash(items2)


def test_compute_hash_handles_empty():
    assert compute_hash([]) == compute_hash([])
    assert len(compute_hash([])) == 64  # SHA-256 hex
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/unit/memory/test_builder.py -v
```

- [ ] **Step 4: Commit**

```bash
git add paperforge/memory/builder.py tests/unit/memory/test_builder.py
git commit -m "feat(memory): add builder module that populates SQLite from formal-library.json"
```

---

### Task 5: `paperforge/memory/query.py`

**Files:**
- Create: `paperforge/memory/query.py`
- Create: `tests/unit/memory/test_query.py`

- [ ] **Step 1: Write `query.py`**

```python
from __future__ import annotations

import json
import logging
from pathlib import Path

from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.memory.schema import get_schema_version, CURRENT_SCHEMA_VERSION
from paperforge.memory.builder import compute_hash
from paperforge.worker.asset_state import compute_health
from paperforge.worker.asset_index import read_index


def get_memory_status(vault: Path) -> dict:
    """Check paperforge.db health and staleness.
    
    Returns a dict with: db_exists, schema_ok, fresh, count_match,
    paper_count_db, paper_count_index, needs_rebuild.
    """
    db_path = get_memory_db_path(vault)
    result = {
        "db_exists": db_path.exists(),
        "schema_ok": False,
        "fresh": False,
        "count_match": False,
        "paper_count_db": 0,
        "paper_count_index": 0,
        "needs_rebuild": True,
    }
    if not db_path.exists():
        return result

    conn = get_connection(db_path, read_only=True)
    try:
        stored_version = get_schema_version(conn)
        result["schema_ok"] = stored_version == CURRENT_SCHEMA_VERSION
        row = conn.execute("SELECT COUNT(*) as cnt FROM papers").fetchone()
        result["paper_count_db"] = row["cnt"] if row else 0
        stored_hash_row = conn.execute(
            "SELECT value FROM meta WHERE key = 'canonical_index_hash'"
        ).fetchone()
        stored_hash = stored_hash_row["value"] if stored_hash_row else ""
    except Exception:
        return result
    finally:
        conn.close()

    envelope = read_index(vault)
    if envelope is not None:
        # Handle legacy format (bare list)
        if isinstance(envelope, list):
            items = envelope
            paper_count = len(items)
            index_hash = compute_hash(items)
        else:
            items = envelope.get("items", [])
            paper_count = envelope.get("paper_count", 0)
            index_hash = compute_hash(items)
        result["paper_count_index"] = paper_count

        # Compare stored hash with computed hash
        result["hash_match"] = stored_hash == index_hash

        result["count_match"] = (
            result["paper_count_db"] == result["paper_count_index"]
        )

    result["fresh"] = (
        result["schema_ok"]
        and result["count_match"]
        and result.get("hash_match", False)
    )
    result["needs_rebuild"] = not result["fresh"]
    return result


def _entry_from_row(row) -> dict:
    """Reconstruct an entry dict from a papers row (sqlite3.Row)."""
    entry = {k: row[k] for k in row.keys()}
    for key in ("has_pdf", "do_ocr", "analyze"):
        if key in entry and entry[key] is not None:
            entry[key] = bool(entry[key])
    for key in ("authors_json", "collections_json"):
        if key in entry and entry[key]:
            try:
                entry[key[:-5]] = json.loads(entry[key])
                del entry[key]
            except json.JSONDecodeError:
                logging.warning(
                    "Corrupted JSON in column %s for paper %s",
                    key, entry.get("zotero_key", "?"),
                )
    return entry


def lookup_paper(conn, query: str) -> list[dict]:
    """Multi-strategy lookup. Returns list of matching paper dicts."""
    q = query.strip()
    results = []

    for lookup_col in ("zotero_key", "citation_key", "doi"):
        row = conn.execute(
            f"SELECT * FROM papers WHERE LOWER({lookup_col}) = LOWER(?)",
            (q,),
        ).fetchone()
        if row:
            return [_entry_from_row(row)]

    rows = conn.execute(
        """SELECT * FROM papers
           WHERE LOWER(title) LIKE '%' || LOWER(?) || '%'
           LIMIT 20""",
        (q,),
    ).fetchall()
    if rows:
        return [_entry_from_row(r) for r in rows]

    rows = conn.execute(
        """SELECT p.* FROM papers p
           JOIN paper_aliases a ON a.paper_id = p.zotero_key
           WHERE a.alias_norm LIKE '%' || LOWER(?) || '%'
           LIMIT 20""",
        (q,),
    ).fetchall()
    return [_entry_from_row(r) for r in rows]


def get_paper_assets(conn, zotero_key: str) -> list[dict]:
    rows = conn.execute(
        "SELECT asset_type, path, exists_on_disk FROM paper_assets WHERE paper_id = ?",
        (zotero_key,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_paper_status(vault: Path, query: str) -> dict | None:
    """Full paper status lookup. Returns dict or None if not found.

    If multiple candidates found, returns a candidate list without full status.
    """
    db_path = get_memory_db_path(vault)
    if not db_path.exists():
        return None

    conn = get_connection(db_path, read_only=True)
    try:
        entries = lookup_paper(conn, query)
        if not entries:
            return None

        # Multiple candidates → return candidate list only (no full status)
        if len(entries) > 1:
            return {
                "resolved": False,
                "candidates": [
                    {
                        "zotero_key": e.get("zotero_key"),
                        "title": e.get("title"),
                        "year": e.get("year"),
                        "citation_key": e.get("citation_key"),
                        "lifecycle": e.get("lifecycle"),
                    }
                    for e in entries
                ],
            }

        entry = entries[0]
        assets = get_paper_assets(conn, entry["zotero_key"])
        entry["health"] = compute_health(entry)
        entry["assets"] = assets
        entry["resolved"] = True

        next_step = entry.get("next_step", "")
        zk = entry.get("zotero_key", "")
        if next_step == "/pf-deep":
            entry["recommended_action"] = f"/pf-deep {zk}"
        elif next_step == "ocr":
            entry["recommended_action"] = f"paperforge ocr --key {zk}"
        elif next_step == "sync":
            entry["recommended_action"] = "paperforge sync"
        else:
            entry["recommended_action"] = None

        return entry
    finally:
        conn.close()
```

- [ ] **Step 2: Write `tests/unit/memory/test_query.py`**

```python
from __future__ import annotations

from paperforge.memory.query import get_memory_status


def test_get_memory_status_returns_needs_rebuild_when_no_db():
    from pathlib import Path
    result = get_memory_status(Path("/nonexistent/vault"))
    assert result["db_exists"] is False
    assert result["needs_rebuild"] is True
```

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/unit/memory/test_query.py -v
```

- [ ] **Step 4: Commit**

```bash
git add paperforge/memory/query.py tests/unit/memory/test_query.py
git commit -m "feat(memory): add query module for paper lookup and status check"
```

---

### Task 6: CLI commands — `memory.py` and `paper_status.py`

**Files:**
- Create: `paperforge/commands/memory.py`
- Create: `paperforge/commands/paper_status.py`
- Modify: `paperforge/cli.py:258-259` (register parsers)
- Modify: `paperforge/commands/__init__.py:4-13` (register in command dispatch)

- [ ] **Step 1: Write `paperforge/commands/memory.py`**

```python
from __future__ import annotations

import argparse
import sys

from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.builder import build_from_index
from paperforge.memory.query import get_memory_status
from paperforge import __version__ as PF_VERSION


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    sub_cmd = args.memory_subcommand

    if sub_cmd == "build":
        try:
            counts = build_from_index(vault)
            result = PFResult(
                ok=True,
                command="memory build",
                version=PF_VERSION,
                data=counts,
            )
        except FileNotFoundError:
            result = PFResult(
                ok=False,
                command="memory build",
                version=PF_VERSION,
                error=PFError(
                    code=ErrorCode.PATH_NOT_FOUND,
                    message="Canonical index not found. Run paperforge sync --rebuild-index.",
                ),
                next_actions=[
                    {
                        "command": "paperforge sync --rebuild-index",
                        "reason": "Generate formal-library.json first",
                    }
                ],
            )
        except Exception as exc:
            result = PFResult(
                ok=False,
                command="memory build",
                version=PF_VERSION,
                error=PFError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=str(exc),
                ),
            )
        if args.json:
            print(result.to_json())
        else:
            if result.ok:
                print(f"Memory built: {result.data}")
            else:
                print(f"Error: {result.error.message}", file=sys.stderr)
        return 0 if result.ok else 1

    if sub_cmd == "status":
        try:
            status = get_memory_status(vault)
            result = PFResult(
                ok=True,
                command="memory status",
                version=PF_VERSION,
                data=status,
            )
        except Exception as exc:
            result = PFResult(
                ok=False,
                command="memory status",
                version=PF_VERSION,
                error=PFError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=str(exc),
                ),
            )
        if args.json:
            print(result.to_json())
        else:
            if result.ok:
                for k, v in status.items():
                    print(f"  {k}: {v}")
            else:
                print(f"Error: {result.error.message}", file=sys.stderr)
        return 0 if result.ok else 1

    print(f"Unknown memory subcommand: {sub_cmd}", file=sys.stderr)
    return 1
```

- [ ] **Step 2: Write `paperforge/commands/paper_status.py`**

```python
from __future__ import annotations

import argparse
import sys

from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult
from paperforge.memory.query import get_paper_status
from paperforge import __version__ as PF_VERSION


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    query = args.query

    try:
        status = get_paper_status(vault, query)
        if status is None:
            result = PFResult(
                ok=False,
                command="paper-status",
                version=PF_VERSION,
                error=PFError(
                    code=ErrorCode.PATH_NOT_FOUND,
                    message=f"No paper found for: {query}",
                ),
                next_actions=[
                    {
                        "command": "paperforge search",
                        "reason": "Search for papers by keyword",
                    }
                ],
            )
        else:
            result = PFResult(
                ok=True,
                command="paper-status",
                version=PF_VERSION,
                data=status,
            )
    except Exception as exc:
        result = PFResult(
            ok=False,
            command="paper-status",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.INTERNAL_ERROR,
                message=str(exc),
            ),
        )

    if args.json:
        print(result.to_json())
    else:
        if result.ok:
            data = result.data
            if data.get("resolved"):
                print(f"Zotero Key:   {data.get('zotero_key', '')}")
                print(f"Title:        {data.get('title', '')}")
                print(f"Year:         {data.get('year', '')}")
                print(f"Lifecycle:    {data.get('lifecycle', '')}")
                print(f"Next Step:    {data.get('next_step', '')}")
            if data.get("candidates"):
                print(f"\nMultiple candidates: {len(data['candidates'])}")
                for c in data["candidates"]:
                    print(f"  - {c['zotero_key']}: {c['title']} ({c['year']})")
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)

    return 0 if result.ok else 1
```

- [ ] **Step 3: Register in `cli.py`**

In `paperforge/cli.py`, at `build_parser()` after line 259 (`p_dash`), add:

```python
    # Memory Layer commands
    p_memory = sub.add_parser("memory", help="Manage the Memory Layer")
    p_memory_sp = p_memory.add_subparsers(dest="memory_subcommand", required=True)
    p_memory_build = p_memory_sp.add_parser("build", help="Build the memory database from canonical index")
    p_memory_build.add_argument("--json", action="store_true", help="Output as JSON")
    p_memory_status = p_memory_sp.add_parser("status", help="Check memory database status")
    p_memory_status.add_argument("--json", action="store_true", help="Output as JSON")

    p_paper_status = sub.add_parser("paper-status", help="Look up a paper's status")
    p_paper_status.add_argument("query", help="Paper identifier (zotero_key, DOI, title, alias)")
    p_paper_status.add_argument("--json", action="store_true", help="Output as JSON")
```

In `main()`, after `if args.command == "dashboard": ...` (around line 468, find the command dispatch section), add:

```python
        if args.command == "memory":
            from paperforge.commands.memory import run
            return run(args)

        if args.command == "paper-status":
            from paperforge.commands.paper_status import run
            return run(args)
```

(Follow existing dispatch pattern — see how "dashboard" dispatches.)

- [ ] **Step 4: Register in `commands/__init__.py`**

In `paperforge/commands/__init__.py`, add to `_COMMAND_REGISTRY`:

```python
    "memory": "paperforge.commands.memory",
    "paper-status": "paperforge.commands.paper_status",
```

- [ ] **Step 5: Verify CLI registration**

```bash
paperforge --help
```
Expected: `memory` and `paper-status` appear in subcommand list.

```bash
paperforge memory --help
```
Expected: shows `build` and `status` subcommands.

```bash
paperforge memory status --help
```

- [ ] **Step 6: Commit**

```bash
git add paperforge/commands/memory.py paperforge/commands/paper_status.py paperforge/cli.py paperforge/commands/__init__.py
git commit -m "feat(cli): add memory build/status and paper-status commands"
```

---

### Task 7: Integration test

**Files:**
- Create: `tests/integration/test_memory_workflow.py`

- [ ] **Step 1: Write integration test**

```python
from __future__ import annotations

import pytest
from pathlib import Path


@pytest.mark.integration
def test_memory_build_and_status_with_test_vault(test_vault: Path):
    """End-to-end: sync → memory build → memory status → paper-status."""
    import subprocess
    import json

    pf = ["python", "-m", "paperforge", "--vault", str(test_vault)]

    # 1. Sync to ensure formal-library.json exists
    result = subprocess.run(pf + ["sync", "--json"], capture_output=True, text=True)
    # If sync fails, skip (test vault may not have exports)
    if result.returncode != 0:
        pytest.skip("Sync failed — test vault may lack export files")

    # 2. Memory build
    result = subprocess.run(pf + ["memory", "build", "--json"], capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["data"]["papers_indexed"] > 0

    # 3. Memory status
    result = subprocess.run(pf + ["memory", "status", "--json"], capture_output=True, text=True)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["data"]["fresh"] is True
    assert data["data"]["needs_rebuild"] is False
```

- [ ] **Step 2: Run integration test** (requires test vault)

```bash
python -m pytest tests/integration/test_memory_workflow.py -v -m integration
```

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_memory_workflow.py
git commit -m "test(memory): add integration test for memory build/status workflow"
```

---

### Task 8: Final verification — run full test suite

- [ ] **Step 1: Run all tests**

```bash
python -m pytest tests/unit/ tests/integration/ -q --tb=short
```

Expected: All tests pass, no regressions.

- [ ] **Step 2: Run ruff lint**

```bash
ruff check paperforge/memory/ paperforge/commands/memory.py paperforge/commands/paper_status.py --fix && ruff format paperforge/memory/ paperforge/commands/memory.py paperforge/commands/paper_status.py
```

- [ ] **Step 3: Manual smoke test with real vault**

```bash
paperforge memory build --json
paperforge memory status --json
paperforge paper-status "aaronStimulationGrowthFactor2004" --json
```

Expected: Real data flows through, paper status shows lifecycle, next_step, assets.

---

## Summary

| Task | Files Created | Files Modified | Tests |
|------|--------------|----------------|-------|
| 1. Config path | — | `config.py` | manual |
| 2. db.py | `memory/__init__.py`, `memory/db.py` | — | manual |
| 3. schema.py | `memory/schema.py` | — | `test_schema.py` (4 tests) |
| 4. builder.py | `memory/builder.py` | — | `test_builder.py` (3 tests) |
| 5. query.py | `memory/query.py` | — | `test_query.py` (1 test) |
| 6. CLI | `commands/memory.py`, `commands/paper_status.py` | `cli.py`, `commands/__init__.py` | — |
| 7. Integration | `tests/integration/test_memory_workflow.py` | — | 1 test |
| 8. Verification | — | — | full suite + lint |
