# PaperForge Annotation Schema Integration Design

> Status: DESIGN COMPLETE | Schema Version: v1 (independent)

## Decision: Independent annotations.db

Annotation data will live in a **separate SQLite database** (`annotations.db`) co-located with `paperforge.db`:

```
<vault>/System/PaperForge/indexes/
├── paperforge.db          ← Memory Layer (rebuildable)
├── annotations.db         ← Annotation Layer (never dropped)
├── formal-library.json
└── runtime-state*.json
```

### Rationale

| Concern | Solution |
|---------|----------|
| `drop_all_tables()` would destroy user data | Separate DB is immune to rebuild |
| Schema version coupling | Independent schema version management |
| Rebuild frequency | Memory rebuild is frequent, annotations should persist |
| Backup granularity | Users may want to backup annotations independently |
| Concurrent access | Annotations can be written while memory is being rebuilt |

## Schema: annotations.db

```sql
-- Schema version management
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Main annotation table
CREATE TABLE IF NOT EXISTS annotations (
    id                  TEXT PRIMARY KEY,       -- UUID for local, zotero_key for imported

    -- Paper association (via zotero_key)
    paper_id            TEXT NOT NULL,

    -- Zotero source tracking
    zotero_library_id   INTEGER,
    zotero_item_id      INTEGER,
    zotero_key          TEXT DEFAULT '',
    zotero_attachment_key TEXT DEFAULT '',

    -- PDF tracking
    pdf_path            TEXT DEFAULT '',
    pdf_hash            TEXT DEFAULT '',

    -- Annotation data
    type                TEXT NOT NULL,          -- highlight|underline|note|image|ink|text
    page_index          INTEGER,               -- 0-based
    page_label          TEXT DEFAULT '',

    selected_text       TEXT DEFAULT '',
    comment             TEXT DEFAULT '',
    color               TEXT DEFAULT '',        -- hex: #ffd400
    sort_index          TEXT DEFAULT '',

    -- Position data
    position_json       TEXT DEFAULT '{}',
    selector_json       TEXT DEFAULT '{}',      -- for EPUB/web annotations (future)

    -- Tags
    tags_json           TEXT DEFAULT '[]',

    -- Sync state (from Zotero or local)
    source              TEXT NOT NULL DEFAULT 'paperforge',  -- paperforge|zotero_db|pdf_embedded|imported_json
    source_key          TEXT DEFAULT '',                     -- original key in source system
    source_version      INTEGER,                             -- Zotero version number
    source_modified_at  TEXT DEFAULT '',                     -- ISO 8601 from Zotero

    sync_state          TEXT NOT NULL DEFAULT 'local',       -- local|zotero_synced|zotero_remote_changed|local_modified|conflict|pending_push
    is_readonly         INTEGER NOT NULL DEFAULT 0,          -- 1 = Zotero-sourced, not editable

    -- Metadata
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    deleted_at          TEXT,                                -- soft delete

    FOREIGN KEY (paper_id) REFERENCES papers(zotero_key)  -- conceptual, not enforced cross-DB
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_annotations_paper ON annotations(paper_id);
CREATE INDEX IF NOT EXISTS idx_annotations_type ON annotations(type);
CREATE INDEX IF NOT EXISTS idx_annotations_sync_state ON annotations(sync_state);
CREATE INDEX IF NOT EXISTS idx_annotations_source ON annotations(source);
CREATE INDEX IF NOT EXISTS idx_annotations_page ON annotations(paper_id, page_index);
CREATE INDEX IF NOT EXISTS idx_annotations_zotero_key ON annotations(zotero_key);
CREATE INDEX IF NOT EXISTS idx_annotations_deleted ON annotations(deleted_at) WHERE deleted_at IS NOT NULL;

-- FTS5 full-text search on annotation text and comments
CREATE VIRTUAL TABLE IF NOT EXISTS annotations_fts USING fts5(
    paper_id,
    selected_text,
    comment,
    tags_json,
    content='annotations',
    content_rowid='rowid'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS annotations_ai AFTER INSERT ON annotations BEGIN
    INSERT INTO annotations_fts(rowid, paper_id, selected_text, comment, tags_json)
    VALUES (new.rowid, new.paper_id, new.selected_text, new.comment, new.tags_json);
END;

CREATE TRIGGER IF NOT EXISTS annotations_ad AFTER DELETE ON annotations BEGIN
    INSERT INTO annotations_fts(annotations_fts, rowid, paper_id, selected_text, comment, tags_json)
    VALUES ('delete', old.rowid, old.paper_id, old.selected_text, old.comment, old.tags_json);
END;

CREATE TRIGGER IF NOT EXISTS annotations_au AFTER UPDATE ON annotations BEGIN
    INSERT INTO annotations_fts(annotations_fts, rowid, paper_id, selected_text, comment, tags_json)
    VALUES ('delete', old.rowid, old.paper_id, old.selected_text, old.comment, old.tags_json);
    INSERT INTO annotations_fts(rowid, paper_id, selected_text, comment, tags_json)
    VALUES (new.rowid, new.paper_id, new.selected_text, new.comment, new.tags_json);
END;

-- Sync queue for pending write-back operations
CREATE TABLE IF NOT EXISTS sync_queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    annotation_id   TEXT NOT NULL,
    operation       TEXT NOT NULL,           -- create|update|delete
    payload_json    TEXT NOT NULL,
    retry_count     INTEGER DEFAULT 0,
    last_error      TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (annotation_id) REFERENCES annotations(id)
);

CREATE INDEX IF NOT EXISTS idx_sync_queue_pending ON sync_queue(annotation_id, operation)
    WHERE retry_count < 3;
```

## Sync State Machine

```
                    ┌─────────────┐
                    │   local     │ ← PaperForge-native annotation (no Zotero source)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ pending_push│ ← local edit pending Zotero API push
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │zotero_synced│ ← successfully pushed to Zotero
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
     ┌────────▼───┐ ┌──────▼──────┐ ┌──▼─────────┐
     │local_modif.│ │remote_change│ │  conflict   │
     │  (push)    │ │  (re-pull)  │ │ (manual fix)│
     └────────────┘ └─────────────┘ └─────────────┘
```

## How to Avoid Rebuild Conflict

```python
# In memory/builder.py build_from_index():
# DO NOT drop annotations.db tables
# Only operate on paperforge.db tables

ANNOTATIONS_DB = "annotations.db"  # managed separately

def build_from_index(vault: Path) -> dict:
    # ... existing code touches paperforge.db only ...
    # annotations.db is never dropped
```

## Cross-DB Join Pattern

Since annotations and papers are in separate databases, queries that need both do a two-step lookup:

```python
# Step 1: Get paper
paper = lookup_paper(conn_paperforge, query)

# Step 2: Get annotations for that paper
annotations = conn_annotations.execute(
    "SELECT * FROM annotations WHERE paper_id = ? AND deleted_at IS NULL ORDER BY sort_index",
    (paper["zotero_key"],)
).fetchall()
```
