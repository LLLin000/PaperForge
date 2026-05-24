# Annotation Service API Design

> Python service layer for annotation operations.

## Module: `paperforge/annotation/__init__.py`

```python
"""
PaperForge Annotation Layer.

Read-only Zotero SQLite parsing → annotations.db cache → CLI commands → Obsidian overlay.
"""
```

## Module: `paperforge/annotation/probe.py`

```python
class ZoteroAnnotationProbe:
    """Read-only probe into Zotero SQLite for annotations."""

    def __init__(self, zotero_db_path: Path):
        self.zotero_db_path = zotero_db_path

    def copy_to_temp(self) -> Path:
        """Copy zotero.sqlite to temp file. Returns temp path."""

    def open_readonly(self, db_path: Path) -> sqlite3.Connection:
        """Open SQLite in read-only mode (URI mode=ro)."""

    def fetch_annotations(self, conn, paper_key: str = "", limit: int = 100) -> list[dict]:
        """Fetch annotations with parent attachment info."""

    def fetch_tags_for_annotations(self, conn, item_ids: list[int]) -> dict[int, list[str]]:
        """Fetch tags for annotation items."""

    def probe(self, limit: int = 20) -> dict:
        """Full probe: schema check → fetch → return unified JSON."""
```

## Module: `paperforge/annotation/db.py`

```python
class AnnotationDB:
    """Management of annotations.db."""

    def __init__(self, vault: Path):
        self.vault = vault
        self.db_path = vault / "System" / "PaperForge" / "indexes" / "annotations.db"

    def get_connection(self, read_only: bool = False) -> sqlite3.Connection:
        """Open connection with WAL mode."""

    def ensure_schema(self):
        """Create tables if not exist, migrate if needed."""

    def integrity_check(self) -> bool:
        """PRAGMA integrity_check."""

    def get_stats(self) -> dict:
        """Return count by type, source, sync_state."""
```

## Module: `paperforge/annotation/import_annotations.py`

```python
def import_from_zotero(
    vault: Path,
    zotero_db_path: Path | None = None,
    paper_key: str = "",
    dry_run: bool = False,
) -> dict:
    """Import annotations from Zotero SQLite into annotations.db.

    Steps:
    1. Detect/copy Zotero SQLite
    2. Open read-only connection
    3. Fetch annotations (optionally filtered by paper_key)
    4. For each annotation:
       a. Check if already imported (by zotero_key + source_version)
       b. If new: INSERT with sync_state='zotero_synced', is_readonly=1
       c. If updated: UPDATE with new position/comment/text, bump version
       d. If deleted: soft delete (set deleted_at)
    5. Commit
    6. Return import stats
    """
```

## Module: `paperforge/annotation/export.py`

```python
def export_json(ann_conn, paper_key: str) -> str:
    """Export annotations for a paper as pretty JSON."""

def export_markdown(ann_conn, paper_key: str, paper_title: str) -> str:
    """Export annotations as formatted Markdown."""
```

## CLI: `paperforge/commands/annotation.py`

```python
def run(args) -> int:
    """Dispatch annotation subcommands."""
    if args.annotation_action == "import":
        return _cmd_import(args)
    elif args.annotation_action == "list":
        return _cmd_list(args)
    elif args.annotation_action == "create":
        return _cmd_create(args)
    elif args.annotation_action == "patch":
        return _cmd_patch(args)
    elif args.annotation_action == "delete":
        return _cmd_delete(args)
    elif args.annotation_action == "export":
        return _cmd_export(args)
    elif args.annotation_action == "status":
        return _cmd_status(args)
```

## JSON Output Contract

All commands support `--json` flag. Output envelope:

```json
{
    "ok": true,
    "command": "annotation <subcommand>",
    "data": {
        "paper_id": "ABCD1234",
        "annotations": [...],
        "count": 15
    },
    "meta": {
        "db_path": "/path/to/annotations.db",
        "elapsed_ms": 123
    }
}
```

Error envelope:

```json
{
    "ok": false,
    "command": "annotation <subcommand>",
    "error": {
        "code": "ZOTERO_DB_NOT_FOUND",
        "message": "Zotero SQLite not found at /path/to/zotero.sqlite"
    }
}
```
