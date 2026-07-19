# Memory Layer Performance Optimization — v1.5.8

> **Branch:** `feature/memory` | **From audit:** Round 3 | **All 10 items**

## P0: Critical Efficiency Bugs

### 1. refresh_paper: O(N) scan per single-paper update

**File:** `paperforge/memory/refresh.py:25`

**Problem:** `refresh_paper()` calls `read_index(vault)` which parses the full 5-10 MB `formal-library.json` every time, then does a linear scan to find one paper.

**Fix:** Add a lightweight `read_index_entry(vault, key) -> dict | None` function that:
- Opens `formal-library.json`
- Uses `ijson` or streaming parse, OR
- Loads only the `items` list and does a dict lookup by `zotero_key`

Alternative (simpler): change `refresh_paper()` signature to accept the entry dict directly from the caller. Caller already has the entry (from sync or OCR completion event). Don't re-read the file.

```python
# New signature
def refresh_paper(vault: Path, entry: dict) -> bool:
    # entry is already resolved by caller, skip read_index
```

Callers updated:
- `sync_service.run()` → after `_build_entry()`, call `refresh_paper(vault, entry)`
- `commands/ocr.py` → after OCR completes, get entry from OCR context, call `refresh_paper(vault, entry)`
- `commands/finalize.py` → after deep-finalize, use the entry dict

### 2. FTS Double-Insert

**File:** `paperforge/memory/builder.py:97,150-158` + `paperforge/memory/schema.py:104`

**Problem:** `papers_ai` trigger fires on `INSERT OR REPLACE INTO papers`, writing a row to `paper_fts`. Then the manual `INSERT INTO paper_fts` (line 150) tries to write AGAIN — IntegrityError caught silently.

**Fix:** In `build_from_index()`:
- Before the paper loop: `conn.execute("DROP TRIGGER IF EXISTS papers_ai")`
- After the paper loop: re-create the trigger from schema
- Remove the manual `INSERT INTO paper_fts` (lines 150-158)

Similarly in `refresh.py`:
- Drop trigger before upsert, re-create after (or just use manual FTS + no trigger)

### 3. _autoRebuild does full build on every change

**File:** `paperforge/plugin/main.js:_autoRebuild()`

**Problem:** Runs `memory build` (full rebuild) on ANY export change. One new paper = 150 papers re-indexed.

**Fix:** Never trigger full `memory build` from auto-poll. Instead:
- On export change: run `paperforge sync --auto` (incremental sync only)
- The sync command already calls `refresh_paper()` internally for new/changed papers
- Only run `memory build` on first install or when user explicitly requests it

Change `_autoRebuild()` to `_autoSync()`:
```javascript
const cmd = `"${pyResult.path}" -m paperforge --vault "${vaultPath}" sync`;
```

## P1: Redundancy Elimination

### 4. Frontmatter read 3 times per paper

**File:** `paperforge/worker/asset_index.py:325-343`

**Problem:** `_build_entry()` calls `read_frontmatter()` 3 separate times for `do_ocr`, `analyze`, `deep_reading_status` from the same file.

**Fix:** Add helper at module level:
```python
def _get_frontmatter_values(note_path: Path) -> dict:
    """Read frontmatter once, return {do_ocr, analyze, deep_reading_status}."""
    fm = read_frontmatter(note_path)
    return {
        "do_ocr": fm.get("do_ocr"),
        "analyze": fm.get("analyze"),
        "deep_reading_status": fm.get("deep_reading_status"),
    }
```

### 5. Duplicate PAPER_COLUMNS logic

**File:** `paperforge/memory/builder.py:109-139` + `paperforge/memory/refresh.py:52-74`

**Problem:** Identical ~30 lines of column-value mapping.

**Fix:** Extract to `paperforge/memory/_columns.py`:
```python
def build_paper_row(entry: dict, generated_at: str) -> dict:
    # single source of truth for papers table columns
    ...
```
Import from both builder.py and refresh.py.

### 6. Dashboard 6 SELECTs → 2

**File:** `paperforge/commands/dashboard.py:65-75`

**Fix:**
```sql
-- Query 1: combined pdf+ocr health
SELECT has_pdf, 
       CASE WHEN ocr_status = 'done' THEN 'done'
            WHEN ocr_status IN ('failed','blocked') THEN 'failed'
            ELSE 'pending' END as ocr_state,
       COUNT(*) as cnt
FROM papers GROUP BY has_pdf, ocr_state;

-- Query 2: domain counts (unchanged)
SELECT domain, COUNT(*) FROM papers GROUP BY domain;
```

## P2: General Optimization

### 7. Per-row INSERT → executemany

**File:** `paperforge/memory/builder.py:143`

**Fix:** Collect paper rows, asset rows, alias rows in lists. Use `executemany()`:
```python
conn.executemany("INSERT OR REPLACE INTO papers (...) VALUES (...)", paper_rows)
conn.executemany("INSERT OR REPLACE INTO paper_assets (...) VALUES (...)", asset_rows)
```

### 8. Poll interval 30s → 120s

**File:** `paperforge/plugin/main.js:3920`

**Fix:** Change `setInterval(..., 30000)` to `setInterval(..., 120000)`.

### 9. _build_entry: 10 file reads per paper

**File:** `paperforge/worker/asset_index.py:_build_entry()`

**Problem:** Multiple `.exists()`, `.read_text()`, frontmatter reads per paper.

**Fix:** Combine the `_legacy_control_flags` + `do_ocr` + `analyze` + `deep_reading_status` into one pass. Don't check `note_path.exists()` when `main_note_path.exists()` — if main exists, use it; only fall back to note_path when main doesn't exist.

### 10. formal-library.json read-once pipeline

**Problem:** `formal-library.json` is parsed by 5+ different modules during a sync→build→dashboard cycle.

**Fix:** Not urgent — each module reads it independently for isolation. This is acceptable for reliability. Could optimize later with in-memory cache, but at risk of staleness.

## Implementation Order

1. P0 #1: refresh_paper accept entry dict (changes refresh.py + callers)
2. P0 #2: FTS trigger removal + manual-only insert
3. P0 #3: _autoRebuild → _autoSync
4. P1 #5: Extract PAPER_COLUMNS helper
5. P1 #4: Single frontmatter parse
6. P1 #6: Dashboard query merge
7. P2 #7: executemany batching
8. P2 #8: Poll interval
9. P2 #9: File read consolidation

Each step: modify → test → commit.
