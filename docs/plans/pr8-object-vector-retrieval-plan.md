# PR 8: Object Vector Retrieval — Implementation Plan

**Status**: Reviewed (applied 9 review fixes)  
**Depends on**: PR 7 (object unit_id/caption_key/node_id hardening) — confirmed on master @ `e551f79a`  
**Files touched**: 11 files (8 code + 3 docs/tests), ~240 lines net  
**No schema changes, no new FTS table**

---

## Background

Current gap:

```
body_units   → DB → paperforge_body vectors → merge_retrieve ✅
object_units → DB → NO vectors              → merge_retrieve ❌
```

Object units (figure captions, table captions) are persisted in SQLite DB and used by `build_object_units()` / `_upsert_object_units()`, but **never embedded into ChromaDB**.
They are **not** in `body_units_fts` either — so neither FTS search nor vector search can find figure/table content.
`merge_retrieve` only queries `paperforge_fulltext` + `paperforge_body` → figure/table content is invisible to vector search.

## Design: C-lite (new `paperforge_objects` collection)

```
paperforge_fulltext  → legacy chunks   → source="legacy_chunk"
paperforge_body      → body units       → source="body_unit"
paperforge_objects   → object units     → source="object_unit"
```

---

## Changes

### 1. `paperforge/retrieval/manifest.py`

Add `compute_object_units_hash()` for resume detection:

```python
def compute_object_units_hash(units: list[dict]) -> str:
    raw = json.dumps(
        [
            {
                "unit_id": u["unit_id"],
                "paper_id": u["paper_id"],
                "section_path": u.get("section_path", ""),
                "object_kind": u.get("object_kind", ""),
                "object_label": u.get("object_label", ""),
                "caption_text": u.get("caption_text", ""),
                "nearby_body_text": u.get("nearby_body_text", ""),
                "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
            }
            for u in units
        ],
        ensure_ascii=False,
        sort_keys=True,
    )
    return sha256(raw.encode()).hexdigest()
```

**Also update `build_paper_manifest()`** to record `body_units_hash` and `object_units_hash`:

```python
"body_unit_count": len(body_units),
"body_units_hash": compute_body_units_hash(body_units),
"object_unit_count": len(object_units),
"object_units_hash": compute_object_units_hash(object_units),
```

This makes provenance complete: manifest tells you not just how many, but whether content changed.

### 2. `paperforge/embedding/_chroma.py`

Add `"paperforge_objects"` to collection list:

```python
_COLLECTION_NAMES = ["paperforge_fulltext", "paperforge_body", "paperforge_objects"]
```

`delete_paper_vectors()` iterates this list — object vectors will be auto-deleted.

### 3. `paperforge/embedding/builder.py`

Add two functions:

```python
def get_object_units_for_embedding(vault: Path, key: str) -> list[dict]:
    """Fetch object_units from the memory DB for a given paper."""
    ...

def embed_object_units(vault: Path, zotero_key: str, object_units: list[dict]) -> int:
    """Embed object_units into paperforge_objects collection."""
    ...
```

**Embedding text**: `"\n".join([object_label, caption_text, nearby_body_text])`
Useful for queries like "Figure 2" (object_label) or "histological analysis" (caption_text).

**Metadata**: `paper_id`, `section_path`, `unit_id`, `unit_kind="object"`, `object_kind`, `object_label`, `object_units_hash`, `retrieval_policy_version`, `token_estimate`

### 4. `paperforge/embedding/status.py`

In the status dict, add:

```python
"object_chunk_count": col_o.count(),
"total_chunks": ft_count + body_count + object_count,
```

### 5. `paperforge/embedding/search.py`

- Add `"paperforge_objects"` to `RETRIEVAL_COLLECTIONS`
- Source mapping (dict):

```python
source = {
    "paperforge_fulltext": "legacy_chunk",
    "paperforge_body": "body_unit",
    "paperforge_objects": "object_unit",
}[name]
```

- Result fields: add `object_kind` and `object_label` from metadata (empty string when not applicable)

**Note**: `merge_retrieve` queries collections sequentially (not parallel). Accept for now; optimize later if needed.

### 6. `paperforge/embedding/__init__.py`

Export `get_object_units_for_embedding` and `embed_object_units`.

### 7. `paperforge/commands/embed.py` — embed build routing

Add `_has_object_units_in_db()` symmetric to `_has_body_units_in_db()`:

```python
def _has_object_units_in_db(vault: Path, key: str) -> bool:
    """Check if paper has object_units in the memory DB."""
    ...
```

Routing logic (structured path handles all three cases):

```python
has_body = _has_body_units_in_db(vault, key)
has_object = _has_object_units_in_db(vault, key)

if has_body or has_object:
    body_units = get_body_units_for_embedding(vault, key) if has_body else []
    object_units = get_object_units_for_embedding(vault, key) if has_object else []

    if resume:
        body_ok = not body_units   # empty = nothing to check = OK
        object_ok = not object_units

        if body_units:
            col = get_collection(vault, name="paperforge_body")
            existing = col.get(where={"paper_id": key}, limit=1)
            body_ok = _hash_matches(existing, body_units, "body_units_hash")

        if object_units:
            col = get_collection(vault, name="paperforge_objects")
            existing = col.get(where={"paper_id": key}, limit=1)
            object_ok = _hash_matches(existing, object_units, "object_units_hash")

        if body_ok and object_ok:
            papers_skipped += 1
            continue

    delete_paper_vectors(vault, key)  # removes all three collections

    chunks_body = 0
    chunks_object = 0
    if body_units:
        chunks_body = embed_body_units(vault, key, body_units)
    if object_units:
        chunks_object = embed_object_units(vault, key, object_units)

    chunks_embedded += chunks_body + chunks_object
    papers_embedded += 1
else:
    # Legacy fulltext path (unchanged)
    ...
```

Key behaviors:
- **body-only paper**: body_ok checked, object_ok = True (empty → OK), embed body only
- **object-only paper**: body_ok = True, object_ok checked, embed object only
- **both**: both checked, both embedded
- **either hash mismatch**: delete all + re-embed both

**Empty list hash note**: When a paper has no object_units (`[]`), resume treats it as OK.
Empty list does not require a vector-side hash record. Only non-empty units trigger a collection check.
This avoids requiring empty vector collections for body-only papers.

### 8. `paperforge/memory/state_snapshot.py` — extend `write_vector_runtime()`

Current signature only accepts `chunk_count`. Extend to accept body/object counts:

```python
def write_vector_runtime(
    vault: Path,
    *,
    enabled: bool,
    mode: str,
    model: str,
    deps_installed: bool,
    deps_missing: list[str] | None,
    py_version: str,
    db_exists: bool,
    chunk_count: int,
    body_chunk_count: int = 0,
    object_chunk_count: int = 0,
    total_chunks: int | None = None,
    build_state: dict | None,
    healthy: bool = True,
    error: str = "",
    corrupted: bool = False,
) -> None:
```

Write the new fields:

```python
"body_chunk_count": body_chunk_count,
"object_chunk_count": object_chunk_count,
"total_chunks": total_chunks if total_chunks is not None else chunk_count + body_chunk_count + object_chunk_count,
```

This keeps CLI `embed status --json` and Obsidian UI runtime snapshot consistent.
Without this change, `commands/embed.py` will get TypeError when passing the new kwargs.

### 9. `paperforge/memory/builder.py`

No changes needed. `_upsert_object_units()` already exists.

---

## Test Plan

### TC-O1: Object DB persistence (Layer A, section 4b)
Already added in PR 7. Verifies unit_id unique, non-empty labels/section_path, DB count == list count.

### TC-O2a: Object vector count (clean full run)
```python
object_db = SELECT COUNT(*) FROM object_units WHERE indexable=1
object_vec = paperforge_objects.count()
assert object_vec == object_db
```

### TC-O2b: Object vector count per-paper (incremental/resume safe)
```python
for key in embedded_keys:
    db_cnt = SELECT COUNT(*) FROM object_units WHERE paper_id=? AND indexable=1
    vec_cnt = len(paperforge_objects.get(where={"paper_id": key}).get("ids", []))
    assert vec_cnt == db_cnt, f"{key}: DB={db_cnt} vec={vec_cnt}"
```
Per-paper assert pinpoints which paper failed and works correctly in resume mode.

### TC-O3: Object vector metadata
```python
meta = sample from paperforge_objects
assert meta["unit_kind"] == "object"
assert meta["object_kind"] in {"figure", "table"}
assert meta["object_label"]
assert meta["object_units_hash"]
```

### TC-O4: Object caption query
```python
caption_phrase = pick from object_units.caption_text
results = merge_retrieve(vault, query=caption_phrase, limit=10)
assert any(r["source"] == "object_unit" for r in results)
```

### TC-O5: Object resume hash
```python
# First embed → count = N
# Re-run --resume → count = N (skip)
# Modify caption_text in DB → re-run --resume → count = N (hash mismatch → re-embed)
# Verify metadata.object_units_hash changed
```

### TC-O6: Source merge cap
```python
results = merge_retrieve(vault, caption_query, limit=10)
object_count = sum(1 for r in results if r["source"] == "object_unit")
assert object_count >= 1       # objects not drowned by legacy
assert per_paper_count <= 2    # cap works
```

### TC-O7: delete_paper_vectors removes all three collections
```python
# Add vectors to fulltext/body/objects for same paper_id
delete_paper_vectors(vault, key)
assert all three collections have 0 vectors for key
```

### TC-O8: Object-only route
```python
# Paper has object_units but no body_units
# embed build
assert object vectors created in paperforge_objects
assert legacy path not used (no new legacy chunks for this paper)
```

### TC-O9: Status total consistency
```python
status = get_embed_status(vault)
assert status["total_chunks"] == (
    status["chunk_count"]
    + status["body_chunk_count"]
    + status["object_chunk_count"]
)
# Check embed status --json output includes object_chunk_count
```

### TC-O10: Resume does not duplicate
```python
first_count = paperforge_objects.count()
# re-run --resume
second_count = paperforge_objects.count()
assert second_count == first_count
# modify caption → re-run → verify hash changed, count unchanged
```

### TC-O11: Object result fields in merge_retrieve
```python
results = merge_retrieve(vault, query=caption_phrase, limit=10)
obj = first r where source == "object_unit"
assert obj["object_kind"] in {"figure", "table"}
assert obj["object_label"]
assert obj["section_path"]
```

---

## Implementation Order

| Step | File | What | Complexity |
|------|------|------|------------|
| 1 | `manifest.py` | `compute_object_units_hash()` + manifest records both hashes | +20 lines |
| 2 | `_chroma.py` | `_COLLECTION_NAMES` + `paperforge_objects` | +1 line |
| 3 | `builder.py` | `get_object_units_for_embedding()` + `embed_object_units()` | +60 lines |
| 4 | `status.py` | `object_chunk_count`, `total_chunks` | +5 lines |
| 5 | `state_snapshot.py` | Extend `write_vector_runtime()` signature, write new fields | +15 lines |
| 6 | `search.py` | 3rd collection, source mapping, object_kind/object_label fields | +15 lines |
| 7 | `__init__.py` | Export new functions | +2 lines |
| 8 | `commands/embed.py` | `_has_object_units_in_db`, structured path routing, dual resume, counters | +35 lines |
| 9 | Tests | TC-O1 through TC-O11 | +80 lines |

**Total**: ~240 lines, 11 files (8 code + 3 docs/tests), no schema changes, no new FTS table.

---

## Risks

| Risk | Mitigation |
|------|------------|
| 3-collection ChromaDB query is sequential, ~50% slower | Accept for now; source-aware early stopping or parallel queries if latency issue |
| Object chunks with empty caption_text waste vectors | Already filtered: `indexable=0` / `veto_reason="empty_caption"` |
| Object_units hash vs body_units hash diverge | Resume checks both; if either changed, delete all + re-embed both |
| 709 papers without object_units yet | Same gap as body_units; fixed by full pipeline rebuild |
| vector-runtime-state and status JSON drift | Fixed: both updated from same `get_embed_status()` call |
