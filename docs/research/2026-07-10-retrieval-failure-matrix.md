# PaperForge Retrieval Failure Matrix

- Evidence date: 2026-07-10
- Evidence agent: FailureMatrix
- Wayfinder ticket: [Capture a non-destructive retrieval failure matrix](https://github.com/LLLin000/PaperForge/issues/49)
- Parent map: [Wayfinder: Restore PaperForge retrieval end to end](https://github.com/LLLin000/PaperForge/issues/45)
- Prior evidence: [Retrieval Architecture Contract Drift](https://github.com/LLLin000/PaperForge/issues/53)
- Repository: `D:/L/Med/Research/99_System/LiteraturePipeline/github-release`
- Live vault: `D:/L/OB/Literature-hub` (read-only probes)

---

## Probe design

All probes are non-destructive and reproducible:
1. **Source inspection**: plugin TypeScript + compiled bundle (`main.js`)
2. **Python inspection**: embedded code (`paperforge/commands/`, `paperforge/embedding/`)
3. **Read-only SQL**: direct sqlite3/sqlite-vec queries against `D:/L/OB/Literature-hub/System/PaperForge/indexes/paperforge.db`
4. **CLI execution**: `paperforge search --json`, `paperforge retrieve --json`, `paperforge embed status --json`
5. **File hash**: SHA-256 of deployed vs source `main.js`
6. **Path resolution**: `paperforge_paths()` + `get_vector_db_path()` against live vault

---

## Matrix

### Row 1: sql.js `paper_fts.year` column missing

| Property | Value |
|---|---|
| Severity | **P0** |
| User flow | M metadata search (debounce fast path) |
| Expected | sql.js prepares query, returns results within 200 ms |
| Actual | Query `SELECT zotero_key, …, year FROM paper_fts …` fails — `paper_fts` has no `year` column |
| Downstream | Every debounce search falls to Python CLI path; sql.js never works |

**Reproducible evidence:**

```
# paperforge/plugin/src/services/db.ts:81-87
_queryStmt = _db.prepare(
    `SELECT zotero_key, title, first_author, year, journal, domain, abstract, rank
     FROM paper_fts
     WHERE paper_fts MATCH ?
     ORDER BY rank
     LIMIT ?`
);
```

```
# Live vault probe: PRAGMA table_info(paper_fts)
zotero_key, citation_key, title, first_author, authors_json,
abstract, journal, domain, collection_path, collections_json
# NO year column

# Same probe: SELECT year FROM paper_fts LIMIT 1
→ OperationalError: no such column: year

# papers table HAS year: confirmed via PRAGMA table_info(papers)
```

```
# Correct query (used by Python CLI, confirmed working):
SELECT pf.zotero_key, pf.title, p.year
FROM paper_fts pf JOIN papers p ON pf.zotero_key = p.zotero_key
WHERE paper_fts MATCH ? LIMIT 3
```

---

### Row 2: Plugin does not pass `--deep` for `@` queries

| Property | Value |
|---|---|
| Severity | **P0** |
| User flow | `@` deep hybrid search |
| Expected | CLI receives `--deep` flag, runs `hybrid_search()` |
| Actual | CLI is called as `python -m paperforge retrieve <query> --json` with no `--deep` |
| Downstream | Standard vector retrieve runs (which is also broken — see Row 5); hybrid BM25+vector path never selected |

**Reproducible evidence:**

```
# paperforge/plugin/src/views/dashboard.ts:2437-2442, 2519-2523
const isDeep = raw.startsWith("@");
const query = isDeep ? raw.slice(1).trim() : raw;
const mode = isDeep ? "retrieve" : "search";
…
const child = spawn(
    pythonExe,
    [...pyExtra, "-m", "paperforge", mode, query, "--json"],  // no --deep
    { cwd: vaultPath, timeout: 30000 }
);
```

```
# Compiled bundle confirms:
c = i ? "retrieve" : "search"
# No "--deep" anywhere in the compiled main.js
```

```
# paperforge/commands/retrieve.py:46
deep = getattr(args, "deep", False)  # defaults to False
```

---

### Row 3: CLI returns `data.chunks`, plugin expects `data.matches` / `data.results`

| Property | Value |
|---|---|
| Severity | **P0** |
| User flow | `@` retrieval results display |
| Expected | Plugin parses CLI output, renders result cards |
| Actual | Plugin checks `"matches" in dd` and `"results" in dd` — never matches `"chunks"` → empty results → "No results found" |
| Downstream | Every `@` query silently shows zero results even when vector store has data |

**Reproducible evidence:**

```
# paperforge/commands/retrieve.py:62-64 (deep path)
data = {
    "query": query,
    "chunks": chunks,       # ← key is "chunks"
    "count": len(chunks),
    "deep": True,
    …
}
```

```
# paperforge/commands/retrieve.py:170-178 (standard path)
data = {
    "query": query,
    "chunks": chunks,       # ← same key "chunks"
    "count": len(chunks),
    "route_explanation": …,
}
```

```
# paperforge/plugin/src/views/dashboard.ts:2564-2569 (compiled bundle)
// search output: data.matches
if ("matches" in M && Array.isArray(M.matches)) {
    w = M.matches;
} else if ("results" in M && Array.isArray(M.results)) {
    w = M.results;
}
// NEVER checks "chunks"
```

```
# paperforge/commands/search.py:49-51 (search — correct key)
data = {
    "query": query,
    "matches": results,     # ← key is "matches"
    …
}
```

---

### Row 4: Python emits `text`, deep renderer expects `matched_text`

| Property | Value |
|---|---|
| Severity | **P2** (blocked by Rows 2+3) |
| User flow | `@` result card rendering |
| Expected | Card shows matched text snippet alongside title |
| Actual | Python returns `text` in chunk dict; plugin deep renderer checks `rec["matched_text"]` → never matches → no snippet shown |

**Reproducible evidence:**

```
# paperforge/plugin/src/views/dashboard.ts:2727-2730
if (isDeep && typeof rec["matched_text"] === "string" && rec["matched_text"]) {
    …render matched text…
}
```

```
# paperforge/embedding/search.py — BM25 result fields (confirmed via live probe)
BM25 result fields: unit_id, paper_id, title, first_author, year, journal,
domain, source, text, heading, bm25_score, vec_score
# Has "text": True
# Has "matched_text": False
```

---

### Row 5: vec0 tables are empty (delete-after-write bug)

| Property | Value |
|---|---|
| Severity | **P0** |
| User flow | Any `@` retrieval, any `embed status` health check |
| Expected | vec0 tables contain vectors for 729 processed papers |
| Actual | vec_fulltext, vec_body, vec_objects all have 0 rows. Meta tables also 0 rows. Build_state says "completed" with 729 papers. |

**Reproducible evidence:**

```
# Live vault probe with sqlite-vec extension:
SELECT COUNT(*) FROM vec_fulltext  → 0
SELECT COUNT(*) FROM vec_body     → 0
SELECT COUNT(*) FROM vec_objects  → 0

SELECT COUNT(*) FROM vec_fulltext_meta → 0
SELECT COUNT(*) FROM vec_body_meta    → 0
SELECT COUNT(*) FROM vec_objects_meta → 0
```

```
# paperforge/commands/embed.py:375-379
for payload in bundle.payloads:
    write_encoded_payload(vault, payload)
# Delete old vectors only after all new payloads are written safely
delete_paper_vectors(vault, bundle.paper_id)
```

```
# paperforge/embedding/_chroma.py:65-85
def delete_paper_vectors(vault: Path, zotero_key: str) -> int:
    for vec_table, meta_table in _VEC_TABLE_MAP.values():
        rows = conn.execute(f"SELECT rowid FROM {meta_table} WHERE paper_id = ?", (zotero_key,)).fetchall()
        rowids = [r["rowid"] for r in rows]
        if rowids:
            placeholders = ",".join("?" for _ in rowids)
            conn.execute(f"DELETE FROM {vec_table} WHERE rowid IN ({placeholders})", rowids)  # deletes the rows JUST written
            conn.execute(f"DELETE FROM {meta_table} WHERE paper_id = ?", (zotero_key,))
```

```
# Live vault: paperforge retrieve "shoulder instability" --json 2>&1
→ {"ok": false, "error": {"message": "Vector index is unreadable. Rebuild vectors before retrieving."}}
```

```
# Build_state (live SQLite):
status: completed | current: 729 | total: 729 | model: Qwen/Qwen3-Embedding-4B
→ Contradicts vec0 reality. Build counted payload attempts, not rows surviving deletion.
```

---

### Row 6: `--resume` gates on legacy Chroma path

| Property | Value |
|---|---|
| Severity | **P1** |
| User flow | Resume an interrupted build |
| Expected | Resume checks whether vec0/meta tables have data and resumes from last processed paper |
| Actual | Resume checks `get_vector_db_path(vault)` → resolves to legacy `…/indexes/vectors` (Chroma dir). If absent, resume=False → forces full rebuild |

**Reproducible evidence:**

```
# paperforge/embedding/_chroma.py:22-27
def get_vector_db_path(vault: Path) -> Path:
    paths = paperforge_paths(vault)
    return (paths.get("memory_db", paths.get("index", vault / "System" / "PaperForge"))).parent / "vectors"
```

```
# Live vault probe:
get_vector_db_path(vault) → D:\L\OB\Literature-hub\System\PaperForge\indexes\vectors
Exists: False  ← Chroma directory absent
```

```
# paperforge/commands/embed.py:294-297
if resume:
    …
    db_path = get_vector_db_path(vault)
    if not db_path.exists():
        resume = False  # ← always triggers when Chroma absent
```

---

### Row 7: `--force` deletes legacy Chroma dir, not vec0/meta tables

| Property | Value |
|---|---|
| Severity | **P1** |
| User flow | Force rebuild vectors |
| Expected | Drops all vec0 tables, clears companion meta tables, rebuilds from scratch |
| Actual | Deletes `get_vector_db_path(vault)` → the Chroma `vectors/` directory. vec0 tables and meta rows in paperforge.db are untouched |

**Reproducible evidence:**

```
# paperforge/commands/embed.py:314-326
_force_rebuild = args.force or (resume is False and getattr(args, "resume", False))
if _force_rebuild:
    _gc.collect()
    db_path = get_vector_db_path(vault)
    if db_path.exists():
        import shutil
        shutil.rmtree(str(db_path), ignore_errors=True)
```

```
# Live vault: vectors dir does not exist → --force is a persistent no-op
get_vector_db_path() → D:\L\OB\Literature-hub\System\PaperForge\indexes\vectors → exists=False
```

---

### Row 8: Dead PID / Stop cannot settle

| Property | Value |
|---|---|
| Severity | **P1** |
| User flow | Stop a running build |
| Expected | SIGTERM → cooperative cancellation → state settled to `completed`/`cancelled`/`failed`/`idle` |
| Actual | CLI writes `os.kill(pid, SIGTERM)`, then writes `status="stopping"`. No SIGTERM handler. If PID is already dead, `os.kill()` raises → state stuck in `running`. UI double-signals (child.kill + CLI stop). |

**Reproducible evidence:**

```
# paperforge/commands/embed.py:159-180
if sub == "stop":
    state = read_vector_build_state(vault)
    pid = state.get("pid", 0)
    if pid and state["status"] == "running":
        os.kill(pid, signal.SIGTERM)   # ← no check if pid is alive; raises if dead
        …
    mark_vector_build_state(vault, status="stopping", message="Stop requested")
    # ← no cooperative cancellation checkpoints in build loop
```

```
# paperforge/plugin/src/settings.ts:1210-1219 (compiled bundle)
# Plugin fires "embed stop --json" AND immediately calls child.kill()
# Does not wait for CLI stop result
```

---

### Row 9: JSON snapshot vs SQLite build state split-brain

| Property | Value |
|---|---|
| Severity | **P1** |
| User flow | Settings panel shows build status/progress |
| Expected | UI reads live SQLite `build_state` table |
| Actual | UI reads `vector-runtime-state.json` (written by `embed status --json`). JSON snapshot is only updated on status request, not incrementally during build. Dead process with stale JSON snapshot keeps UI in "running" state. |

**Reproducible evidence:**

```
# paperforge/plugin/src/services/memory-state.ts:167-169
export function getVectorRuntime(vaultPath: string): VectorRuntime | null {
    const paths = resolveVaultPaths(vaultPath);
    return readJSONFile(paths.vectorStatePath) as VectorRuntime | null;
}
```

```
# resolveVaultPaths():131-134
vectorStatePath = path.join(systemDir, "indexes", "vector-runtime-state.json")
```

```
# Live vault: vector-runtime-state.json
build_state.status: "completed" | chunk_count: 0 | total_chunks: 0
```

```
# Plugin compiled bundle (settings display logic):
let h = (Rt(n) || {}).build_state || {};
!this.plugin._embedProcess && h.status === "running" &&
    (this.plugin._embedProgress = { current: h.current || 0, total: h.total || 1, key: h.paper_id || "" });
const isRunning = !!this.plugin._embedProcess || buildState.status === "running";
# → If JSON snapshot says "running" but PID is dead, UI shows "running"
```

---

### Row 10: Status counts meta rows, not vec0 queryability

| Property | Value |
|---|---|
| Severity | **P1** |
| User flow | `paperforge embed status` → readiness assessment |
| Expected | Status confirms vec0 tables are populated and queryable |
| Actual | Status only `SELECT COUNT(*)` from `vec_*_meta` companion tables. Does not verify vec0 row existence or execute a probe vector query. Reports healthy=true even when vec0 has 0 rows. |

**Reproducible evidence:**

```
# paperforge/embedding/status.py:31-36
row_ft = conn.execute("SELECT COUNT(*) AS cnt FROM vec_fulltext_meta").fetchone()
chunk_count = row_ft["cnt"] if row_ft else 0
row_body = conn.execute("SELECT COUNT(*) AS cnt FROM vec_body_meta").fetchone()
body_chunk_count = row_body["cnt"] if row_body else 0
row_obj = conn.execute("SELECT COUNT(*) AS cnt FROM vec_objects_meta").fetchone()
object_chunk_count = row_obj["cnt"] if row_obj else 0
```

```
# Live vault:
embed status reports: healthy=True, total_chunks=0, chunk_count=0
# → "healthy: True" despite zero vectors
```

```
# paperforge/plugin/src/services/memory-state.ts:184-192
export function isVectorReady(vaultPath: string): boolean {
    const s = getVectorRuntime(vaultPath);
    if (!s) return false;
    if (!s.enabled) return false;
    if (!s.deps_installed) return false;
    if (!s.db_exists) return false;
    if (s.healthy === false) return false;
    if (s.chunk_count === 0) return false;  // ← catches 0, but wrong signal source
    return true;
}
```

---

### Row 11: `first_author` vs `authors` field mismatch

| Property | Value |
|---|---|
| Severity | **P2** |
| User flow | M search result card display |
| Expected | Card shows author name |
| Actual | Python returns `first_author` (string). Plugin checks `rec["authors"]` (string or array) → never matches → author text omitted |

**Reproducible evidence:**

```
# paperforge/plugin/src/views/dashboard.ts:2677-2687
if (typeof rec["authors"] === "string") {
    …render authors…
} else if (Array.isArray(rec["authors"])) {
    …render authors…
}
# NEVER checks rec["first_author"]
```

```
# paperforge search "knee" --json (live probe)
match fields: zotero_key, citation_key, title, year, first_author, journal, domain, …
# Has "first_author": true
# Has "authors": false (not present in output)
```

---

### Row 12: Source / deployed main.js hash mismatch

| Property | Value |
|---|---|
| Severity | **P2** |
| User flow | All — plugin execution |
| Expected | Source code matches deployed bundle |
| Actual | SHA-256 differ; deployed (215 KB) is 130 KB smaller than source (345 KB) |

**Reproducible evidence:**

```
Source main.js (paperforge/plugin/main.js):
    SHA-256: 3b118eb268430c4d50114ab65ac21ba17831e972fff8a35357b70965c50b0d82
    Size: 345,270 bytes

Deployed main.js (D:/L/OB/Literature-hub/.obsidian/plugins/paperforge/main.js):
    SHA-256: 439f94d75c93782a062e8d8402b4f62946c9ce8b8b53be105006ab995fad2b77
    Size: 214,690 bytes
```

Note: Both bundles share the same response-parsing logic (`data.matches`/`data.results` only), sql.js init, `matched_text` check, and `vector-runtime-state.json` path. The size difference may be attributable to different minification/transpilation; the exact behavioural delta is out of scope for this ticket.

---

### Row 13: Model/dimension change orphans meta rows

| Property | Value |
|---|---|
| Severity | **P2** |
| User flow | Switch embedding model → rebuild |
| Expected | All vectors and metadata replaced cleanly |
| Actual | `ensure_vec_tables()` detects dimension mismatch, DROP the three vec0 virtual tables, creates new ones — but leaves meta rows intact. Global dimension cache stays for process lifetime. |

**Reproducible evidence:**

```
# paperforge/embedding/dim_detect.py:13-30
_DETECTED_DIM: Optional[int] = None

def detect_embedding_dim(vault: Path) -> int:
    global _DETECTED_DIM
    if _DETECTED_DIM is not None:
        return _DETECTED_DIM  # ← cached globally, not per-vault/model
```

```
# paperforge/embedding/dim_detect.py:61-70
for name in ("vec_fulltext", "vec_body", "vec_objects"):
    conn.execute(f"DROP TABLE IF EXISTS \"{name}\"")
    ddl = f"CREATE VIRTUAL TABLE IF NOT EXISTS \"{name}\" USING vec0(embedding float[{required_dim}]);"
    conn.execute(ddl)
# Note: meta tables (vec_*_meta) are NOT dropped
```

```
# Live vault: vec0 dimension = 2560 (not default 1536)
vec_fulltext DDL: CREATE VIRTUAL TABLE "vec_fulltext" USING vec0(embedding float[2560])
vec_body DDL:     CREATE VIRTUAL TABLE "vec_body" USING vec0(embedding float[2560])
vec_objects DDL:  CREATE VIRTUAL TABLE "vec_objects" USING vec0(embedding float[2560])
```

---

### Row 14: `paperforge embed status` requires `chromadb` dependency

| Property | Value |
|---|---|
| Severity | **P2** |
| User flow | Running `embed status` or `embed build` |
| Expected | Status check only needs sqlite-vec (currently active store) |
| Actual | `embed status` Python code imports and checks for `chromadb`; if absent, reports `deps_missing: ["chromadb"]` |
| Downstream | Valid sqlite-vec-only installation can be reported as dependency-incomplete |

**Reproducible evidence:**

```
# paperforge/commands/embed.py:119-128
if sub == "status":
    …
    try:
        import chromadb  # noqa: F401
    except ImportError:
        _dep_missing.append("chromadb")
    write_vector_runtime(…, deps_installed=len(_dep_missing) == 0, deps_missing=_dep_missing …)
```

---

## Summary of probes executed

| # | Probe type | Target | Command | Output |
|---|---|---|---|---|
| 1 | Read-only SQL | `paper_fts` columns | `PRAGMA table_info(paper_fts)` | Confirmed no `year` column |
| 2 | Read-only SQL | sql.js query | `SELECT year FROM paper_fts` | `OperationalError: no such column: year` |
| 3 | CLI | FTS search | `paperforge search "knee" --json` | 20 results with `data.matches` |
| 4 | CLI | Vector search | `paperforge retrieve "shoulder instability" --json` | Failed: "Vector index is unreadable" |
| 5 | Source inspection | Plugin spawn args | dashboard.ts:2519-2523 | No `--deep` in args |
| 6 | Source inspection | Plugin response parse | dashboard.ts:2564-2569 | Only `matches`/`results`, never `chunks` |
| 7 | Source inspection | Plugin deep render | dashboard.ts:2727-2730 | Expects `matched_text` |
| 8 | Read-only SQL | vec0 row counts | `SELECT COUNT(*) FROM vec_*` | All 0 rows |
| 9 | Source inspection | Delete-after-write | embed.py:375-379, _chroma.py:65-85 | New rows + all-rows-for-paper delete |
| 10 | Python probe | `get_vector_db_path()` | paperforge_paths + _chroma | Returns legacy Chroma path, nonexistent |
| 11 | Source inspection | `--force` implementation | embed.py:314-326 | Deletes legacy Chroma dir |
| 12 | Source inspection | Stop implementation | embed.py:159-180 | os.kill then write "stopping"; no SIGTERM handler |
| 13 | JSON read | `vector-runtime-state.json` | Read file directly | build_state: completed, chunk_count: 0 |
| 14 | Source inspection | Plugin state reading | memory-state.ts:167-169 | Reads JSON snapshot, not SQLite |
| 15 | File hash | Source vs deployed | SHA-256 both files | Mismatch (345KB vs 215KB) |
| 16 | Read-only SQL | vec0 dimension | `sqlite_master` for vec tables | 2560 (not default 1536) |
| 17 | Source inspection | Status meta-only | status.py:31-36 | Only counts meta rows |
| 18 | Source inspection | `chromadb` check | embed.py:119-128 | Requires chromadb for status |
| 19 | CLI | Build state query | SQLite read from paperforge.db | status=completed, 729/729 papers |

---

## Decision gist

```
sql.js year column missing                         → paper_fts is external-content FTS5 that mirrors `papers` columns minus `year`; query must JOIN `papers` or FTS DDL must include `year`
`@` retrieval never gets --deep                     → UI calls `retrieve` without `--deep`; hybrid_search() unreachable from plugin
data.chunks unparseable by plugin                   → CLI returns `data.chunks`, plugin accepts `data.matches`/`data.results`; results silently dropped
text vs matched_text                                → Python emits `text`, plugin deep renderer expects `matched_text`
vec0 tables empty despite build_state=completed     → `delete_paper_vectors()` deletes the rows just written by `write_encoded_payload()`; zero net vectors
--resume gates on legacy Chroma dir path            → `get_vector_db_path()` returns nonexistent `.../indexes/vectors`; resume always false
--force deletes legacy Chroma dir, not vec0/meta    → `force` targets the nonexistent Chroma dir; vec0 tables untouched
Stop writes "stopping" after kill; dead PID raises  → No SIGTERM handler; `os.kill()` on dead PID raises; UI double-signals
Plugin reads JSON snapshot, not live SQLite state   → `vector-runtime-state.json` is the truth source for UI, not SQLite `build_state` table
Status counts meta rows only, not vec0 queryability → `SELECT COUNT(*) FROM vec_*_meta` but no vec0 probe; healthy=true even with 0 vectors
first_author vs authors field mismatch              → Python returns `first_author`, plugin checks `rec["authors"]`
Model/dimension change orphans meta rows            → vec tables dropped on mismatch, meta tables survive; global cache per process
embed status requires chromadb dep                  → Legacy dep check; valid sqlite-vec-only installs marked dep-incomplete
Source/deployed main.js hash mismatch               → Different bundles; exact delta requires separate parity audit
body_units_fts has 14338 rows                       → BM25/FTS text search substrate has data; only vector path is empty
```

---

## Fog / newly specifiable questions

These questions surfaced during evidence collection but cannot be resolved without production changes or non-destructive probing limits:

1. **What is the exact relation between `write_encoded_payload()` commit timing and `delete_paper_vectors()` row selection?** The meta-table rowids written by `write_encoded_payload()` are immediately selected by `delete_paper_vectors()` because both target the same `paper_id`. But does the vec0 virtual table commit its new rows before the DELETE can see them? Currently no rows survive at all — if there were a timing window where at least the final paper's vectors survived, that would change the recovery approach. Answerable via a disposable test vault with instrumented logging.

2. **Does the `--deep` flag fully work end-to-end when called manually?** `hybrid_search()` calls the embedding API, which requires credentials. The BM25 half works (confirmed), but the full hybrid path cannot be tested without a real API call. The `_vec_search()` provider construction happens before the exception handler for missing credentials — a known code-path ordering issue.

3. **What is the exact change delta between source `main.js` and deployed `main.js`?** They have different hashes and sizes. A `diff` of the bundles (after normalizing minification) would reveal whether deployed code contains fixes that source lacks, or vice versa. This is assigned to [Audit source-to-vault deployment parity](https://github.com/LLLin000/PaperForge/issues/47).

4. **How many build iterations have accumulated orphan vec0 vector_chunks / rowids data?** Each `DROP TABLE` + `CREATE VIRTUAL TABLE` for vec tables creates new internal storage tables. If DROP doesn't clean up — or if the companion-meta rows from earlier runs are still in WAL — the DB may have fragmentation. Answerable via WAL inspection or VACUUM simulation in a disposable vault.

5. **Does the `--resume` model-change detection work when the legacy gate is bypassed?** If a build is manually pointed at the correct store, the model-change logic (lines 307-312) compares `stored_model` vs `_current_model`. The `build_state.pid` freshness check (lines 268-292) looks plausible but has never been exercised end-to-end.

6. **Is there a path where a user can distinguish "search found no matching text" from "search is broken"?** Both cases display "No results found." — no error indicator for the contract-drift cases. A future UX improvement.
