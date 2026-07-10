# Approach A — Python CLI as Sole Retrieval Owner

**Date:** 2026-07-10
**Author:** Main (synthesized from latency probes in failure matrix + architecture drift audit)
**Scope:** Evaluate Approach A for the PaperForge Retrieval Experience: **Python CLI is the only query/build execution owner. Plugin invokes a fresh CLI process for M, @, status, build, and control; sql.js is deleted; SQLite/FTS/sqlite-vec and build_state stay Python-owned.**
**Non-goals:** daemon process; sql.js; native Node SQLite module; Chroma migration.

---

## Verdict

**Viability: Strongly viable — the simplest correct path.**

**Recommendation: Implement as the first recovery phase regardless of which long-term architecture is chosen.** Approach A is the only option that can restore retrieval correctness within a single session without introducing new IPC surface or lifecycle complexity. It can later be upgraded to Approach B (add sql.js as read-only cache) or Approach C (add worker) once correctness is proven.

**Fatal risk:** The only fatal risk is the same as today — contract drift between Python payloads and TypeScript parsers. This is mitigated by a unified PFResult envelope enforced by contract tests.

---

## Exact ownership boundary

### Python owns everything retrieval (canonical)

- **Storage:** `paperforge.db` (FTS, vec0, meta, build_state)
- **Schema:** `paperforge/memory/schema.py`
- **M query execution:** `paperforge search --json`
- **@ query execution:** `paperforge retrieve --deep --json`
- **Build execution:** `paperforge embed build|status|stop`
- **Status/health:** `paperforge embed status --json`
- **Result envelope:** one unified `PFResult` across all search/retrieve paths
- **Error taxonomy:** `ok: false` with `error.code` and `error.message`

### Plugin owns UI only

- spawn Python CLI per query
- parse one result envelope (`PFResult`)
- render cards, progress, errors
- manage debounce and abortion (kill child process)

### Explicitly deleted

- `paperforge/plugin/src/services/db.ts` (sql.js service)
- `paperforge/plugin/sql-wasm.wasm`
- `sql.js` from `package.json`
- All sql.js initialization/fallback branches in dashboard
- `vector-runtime-state.json` as authoritative UI truth (may remain as debug snapshot)
- Legacy Chroma production gates in resume/force/delete/status

---

## Observed latency

All measurements from the live Literature-hub vault (D:/L/OB/Literature-hub, 868 papers, 88.9 MB paperforge.db):

| Operation | Time | Notes |
|-----------|------|-------|
| Bare Python child spawn (`python -c pass`) | 73 ms | Floor cost per CLI call |
| `paperforge.cli` import from fresh process | 116 ms | Import chain: config 18ms, db 28ms, search 6ms |
| Full M metadata search spawn (`search knee --json`) | **131 ms** | Cold end-to-end |
| Direct SQLite FTS5 JOIN query (5 results) | 16.4 ms | Query-only, no spawn |
| sqlite-vec extension load | 102.1 ms | One-time per process |

### User-visible latency under Approach A

| Interaction | Expected latency | Perceived |
|-------------|-----------------|-----------|
| Debounced M search (200ms timer) | ~130 ms from spawn | **~330 ms total** (200ms debounce + 130ms spawn) |
| Enter-triggered M search | ~130 ms | Acceptable for explicit action |
| @ deep search (cold) | ~200-300 ms (spawn + vec load + API) | Acceptable |
| @ deep search (warm, sequential) | ~130 ms + API | Acceptable |
| Status/health check | ~130 ms | On settings load — fine |
| Build start | ~130 ms | One-time cost |

### Is ~330ms debounce acceptable?

Yes. The current debounce is 200ms. Adding 130ms spawn gives ~330ms from last keystroke to results. This is within the 200-500ms range where users perceive "instant." The sql.js path was intended to skip the 130ms spawn, but it never worked (Row 1 — `paper_fts.year` missing), so the real user experience has always been CLI fallback anyway.

---

## P0/P1 matrix resolution

| Row | How Approach A fixes it |
|-----|------------------------|
| P0 R1: sql.js `paper_fts.year` | **Resolved by deletion.** No JS-owned SQL. Python owns the query next to the schema. |
| P0 R2: missing `--deep` flag | **Resolved.** Plugin passes `--deep` for `@` queries. One flag, one path. |
| P0 R3: `data.chunks` vs `matches` | **Resolved by unification.** Both search and retrieve return `data.matches` with stable field names. |
| P0 R5: delete-after-write bug | **Must fix independently.** Same Python build loop. Requires transaction-level fix. |
| P0 R4: `text` vs `matched_text` | **Resolved by unification.** One field name in the envelope. |
| P1 R6: resume gates on Chroma | **Must fix in build path.** Delete Chroma gating, check vec0 tables. |
| P1 R7: force deletes Chroma dir | **Must fix in build path.** Drop vec0 tables, not legacy dir. |
| P1 R8: dead PID stop unsettled | **Must fix in build path.** Cooperative cancellation + state settlement. |
| P1 R9: JSON vs SQLite split-brain | **Resolved.** Plugin reads `embed status --json` which queries live SQLite. JSON snapshot becomes debug-only. |
| P1 R10: meta-only health | **Must fix in status path.** Add vec0 queryability probe. |

---

## Result envelope — unified PFResult

All retrieval paths (M search, @ deep) return the same outer shape:

```json
{
  "ok": true,
  "data": {
    "query": "knee",
    "matches": [
      {
        "zotero_key": "...",
        "title": "...",
        "first_author": "...",
        "year": 2024,
        "journal": "...",
        "domain": "...",
        "abstract": "...",
        "score": 0.95,
        "text": "...",
        "heading": "...",
        "source": "fulltext"
      }
    ]
  },
  "count": 5,
  "warnings": []
}
```

Error envelope:

```json
{
  "ok": false,
  "error": {
    "code": "VECTOR_CORRUPTED",
    "message": "Vector index is unreadable. Rebuild vectors before retrieving.",
    "details": {}
  }
}
```

Error codes: `VECTOR_NOT_BUILT`, `VECTOR_CORRUPTED`, `MODEL_CHANGED`, `BACKEND_UNAVAILABLE`, `TIMEOUT`, `INTERNAL_ERROR`, `NO_PYTHON`.

---

## Build state flow

1. Plugin spawns `paperforge embed build --resume` (or `--force`).
2. Python writes `build_state` to SQLite as the only truth.
3. Plugin polls `paperforge embed status --json` periodically during build.
4. `embed status` reads live SQLite `build_state` and vec0 queryability, returns fresh PFResult.
5. Plugin renders progress bar and state from the status response.
6. On stop: plugin spawns `paperforge embed stop --json`. Python kills PID, writes `status=idle` to SQLite, returns settlement confirmation.
7. `vector-runtime-state.json` becomes a debug-only snapshot written by `embed status` for human inspection. Plugin never reads it as control-plane truth.

---

## Minimal implementation sequence

1. **Unify result envelope.** Make `paperforge search` and `paperforge retrieve` return the same `data.matches` key with the same field names (`first_author`, `text`). Add `--deep` flag plumbing to retrieve.
2. **Fix plugin parser.** Remove `matches`/`results`/`chunks` forking. Parse only `data.matches`. Remove `matched_text` check — use `text`.
3. **Fix plugin spawn.** Pass `--deep` for `@` queries. Delete sql.js service.
4. **Fix build path.** Transactional write-then-delete. Delete Chroma gating from resume/force. Add vec0 queryability check to status. Cooperative stop with state settlement.
5. **Fix plugin state.** Read live `embed status --json` instead of JSON snapshot. Poll during build.
6. **Add contract tests.** E2E: plugin spawn → CLI output → parse → render. Test every error code.

---

## Approximate files affected

- **Delete:** `paperforge/plugin/src/services/db.ts`, `paperforge/plugin/sql-wasm.wasm`
- **Modify plugin:** `dashboard.ts` (search spawn + parsing + state), `settings.ts` (build state), `memory-state.ts` (delete snapshot-as-truth), `python-bridge.ts` (unified spawn helper)
- **Modify Python:** `search.py` (unified envelope), `retrieve.py` (unified envelope + `--deep`), `embed.py` (fix build loop, Chroma cleanup, cooperative stop, status probe), `build_state.py` (canonical truth), `status.py` (vec0 queryability), `_chroma.py` (delete legacy production gates), `state_snapshot.py` (downgrade to debug-only)
- **New:** contract test file for envelope schema

---

## Comparison to Approaches B and C

| Dimension | A (CLI only) | B (sql.js cache) | C (worker) |
|-----------|-------------|-------------------|------------|
| Correctness risk | Lowest — one code path | Medium — staleness risk | Medium — IPC/lifecycle risk |
| Implementation complexity | Lowest | Medium | High |
| M search latency | ~330ms (debounce+spawn) | ~200ms (sql.js hit) | ~10-25ms (worker hit) |
| @ search latency | ~200-300ms | ~200-300ms | ~130ms + API |
| New IPC surface | None | None | JSON-lines protocol |
| Ownership clarity | Best — one owner | Good — two readers | Good — two workers |
| Upgrade path | Baseline | From A → B | From A → C |
| Files changed | ~12 | ~16 | ~22 + 4 new |

---

## Final verdict

**Approach A is the correct first recovery phase.** It restores retrieval correctness with the smallest diff and no new lifecycle complexity. It establishes the unified PFResult envelope and Python-as-canonical-owner contracts that both B and C also require. Once correctness is proven in the live vault with contract tests, the team can decide whether to add Approach B (sql.js read cache) or Approach C (panel-scoped worker) as a latency optimization.

**Bottom line: Implement Approach A now. Defer B and C until after correctness is restored and contract tests gate the live pipeline.**
