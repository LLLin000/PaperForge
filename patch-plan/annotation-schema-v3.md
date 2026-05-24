# Annotation Schema v1 (Independent, not v3)

> Note: While PaperForge's memory layer is at schema v2, annotation schema starts at v1 independently.

## DB Location

```
<vault>/System/PaperForge/indexes/annotations.db
```

## Schema Version Management

```python
ANNOTATIONS_SCHEMA_VERSION = 1

def get_annotations_schema_version(conn):
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        return int(row["value"]) if row else 0
    except sqlite3.OperationalError:
        return 0

def ensure_annotations_schema(conn):
    stored = get_annotations_schema_version(conn)
    if stored == 0:
        _create_annotations_schema(conn)
        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', '1')")
        conn.commit()
    elif stored < ANNOTATIONS_SCHEMA_VERSION:
        _migrate_annotations_schema(conn, stored)
```

## Full DDL

See `reports/03-paperforge-schema-design.md` for complete DDL.

### Tables

| Table | Purpose |
|-------|---------|
| `meta` | Schema version, last import timestamp, stats |
| `annotations` | Main annotation data |
| `annotations_fts` | FTS5 virtual table for full-text search |
| `sync_queue` | Pending write-back operations (future) |

### Indexes

```sql
idx_annotations_paper         — paper_id
idx_annotations_type          — type
idx_annotations_sync_state    — sync_state
idx_annotations_source        — source
idx_annotations_page          — (paper_id, page_index)
idx_annotations_zotero_key    — zotero_key
idx_annotations_deleted       — partial index on deleted_at IS NOT NULL
```

## Migration Strategy (Future)

| Version | Changes |
|---------|---------|
| 1 (MVP) | Initial schema as designed |
| 2 | Web API write-back support: add `api_response_json`, `last_push_attempt` columns |
| 3 | Group library support: add `zotero_group_id` column |

## Cross-DB Note

Annotations DB is independent from paperforge.db. To correlate:

```python
# Get all annotations for a paper
def get_paper_annotations(ann_conn, paper_zotero_key):
    return ann_conn.execute(
        "SELECT * FROM annotations WHERE paper_id = ? AND deleted_at IS NULL ORDER BY sort_index",
        (paper_zotero_key,)
    ).fetchall()
```
