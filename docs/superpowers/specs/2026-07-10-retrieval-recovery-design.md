# PaperForge Retrieval Recovery — Architecture and UX Design

- **Date:** 2026-07-10
- **Map:** [Wayfinder: Restore PaperForge retrieval end to end](https://github.com/LLLin000/PaperForge/issues/45)
- **Evidence:** Issues #53 (contract drift), #49 (failure matrix), #47 (deployment parity)
- **Status:** Presenting for design approval before implementation

---

## 1. Problem summary

The PaperForge Retrieval Experience has **four P0 contract failures** and **ten lifecycle/integrity drifts** that make M metadata search, @ deep search, and vector build controls silently broken or misleading. The root cause is not one bug — it's four independently drifting subsystems (sql.js, Python CLI, build-state JSON, Chroma-legacy control flow) with no unified contract.

### P0 failures (user-visible breakage)

| # | Failure | Impact |
|---|---------|--------|
| 1 | sql.js queries `paper_fts.year` — column doesn't exist | sql.js never works; every debounce search falls to CLI |
| 2 | Plugin omits `--deep` for `@` queries | hybrid BM25+vector path unreachable |
| 3 | CLI returns `data.chunks`, plugin expects `data.matches`/`data.results` | Every @ query silently shows "No results found" |
| 4 | Build loop writes then immediately deletes vectors | vec0 tables empty despite build_state=completed |

### P1 drift (control/integrity)

5. `--resume` gates on legacy Chroma directory, not vec0 tables
6. `--force` deletes legacy Chroma directory, not vec0 tables
7. Stop writes state after killing PID; dead PID crashes stop
8. Plugin reads stale JSON snapshot, not live SQLite build state
9. embed status counts meta rows, never checks vec0 queryability
10. `text` vs `matched_text`, `first_author` vs `authors` field drift

---

## 2. Design principles

1. **Source Corpus is never at risk.** Papers, OCR, blocks, metadata, annotations are preserved.
2. **Retrieval Artifacts are disposable.** FTS indexes, embeddings, vector tables may be rebuilt.
3. **One owner, one truth, one envelope.** Python owns storage, schema, queries, build lifecycle. Plugin owns UI rendering only.
4. **States are distinguishable.** "No results" and "backend broken" are never the same view.
5. **Recovery over redesign.** Existing Obsidian visual language and DESIGN.md are binding. This is a functional recovery, not a UI overhaul.

---

## 3. Architecture recommendation: Approach A (Python CLI as sole owner)

### Decision

**Implement Approach A as the first recovery phase.** Delete sql.js. Python CLI owns every retrieval and build path. Plugin spawns per-query CLI processes with a unified PFResult envelope.

### Rationale

Approach A is the only option that restores correctness with the smallest diff, no new IPC surface, and no lifecycle complexity. Both Approaches B (sql.js read cache) and C (panel-scoped worker) can be added later as latency optimizations once correctness is proven by contract tests.

### What changes

| Layer | Action |
|-------|--------|
| **Delete** | sql.js service (`db.ts`), `sql-wasm.wasm`, `sql.js` npm dep, sql.js branches in dashboard |
| **Unify Python envelope** | `search` and `retrieve` both return `data.matches` with stable fields (`first_author`, `text`, `heading`) |
| **Fix plugin spawn** | Pass `--deep` for @ queries. Parse only `data.matches`. Kill child on cancel. |
| **Fix build path** | Transactional write-then-delete. Delete Chroma gating. Add vec0 queryability probe. Cooperative stop with state settlement. |
| **Fix plugin state** | Read live `embed status --json` instead of JSON snapshot. Poll during build. |
| **Downgrade JSON snapshot** | Debug-only; never control-plane truth. |

### User-visible latency

| Interaction | Latency | Acceptable? |
|-------------|---------|:---:|
| Debounced M search | ~330ms (200ms debounce + 130ms spawn) | Yes — feels instant |
| Enter M search | ~130ms | Yes |
| @ deep search | ~200-300ms + API | Yes |
| Status check | ~130ms | On settings load — fine |

### Why not sql.js (Approach B) right now?

Approach B requires four mandatory controls before sql.js is safe enough: Python-owned M-search contract, staleness invalidation, WAL publication discipline, and deletion of all Chroma ownership leftovers. Adding these controls alongside the build-path fixes creates unnecessary risk. Approach B becomes a straightforward latency optimization (delete sql.js query, replace with Python-owned contract version) once the unified envelope and Python-as-canonical-owner foundation exist.

### Why not worker (Approach C) right now?

Approach C is architecturally clean but introduces medium-high lifecycle complexity (IPC protocol, worker restart/crash recovery, stale connection handling, concurrency with build, Windows process semantics) before the simplest correctness fixes are proven. It becomes a viable upgrade path once the unified envelope and build-path fixes are stable.

---

## 4. Unified result envelope (PFResult v1)

Every retrieval path returns the same outer shape:

```json
{
  "ok": true,
  "data": {
    "query": "knee",
    "matches": [
      {
        "zotero_key": "...",
        "title": "Title of the paper",
        "first_author": "Author A",
        "year": 2024,
        "journal": "Journal Name",
        "domain": "orthopedics",
        "abstract": "Abstract snippet...",
        "score": 0.95,
        "text": "Matched body text snippet...",
        "heading": "Introduction",
        "source": "fulltext"
      }
    ]
  },
  "count": 5,
  "route_explanation": "FTS match",
  "warnings": []
}
```

Error:

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

### Error codes

| Code | UI state |
|------|----------|
| `VECTOR_NOT_BUILT` | Vectors not built — link to build |
| `VECTOR_CORRUPTED` | Corrupted — force rebuild required |
| `MODEL_CHANGED` | Model changed — rebuild recommended |
| `BACKEND_UNAVAILABLE` | Python/CLI not reachable |
| `TIMEOUT` | Search timed out |
| `INTERNAL_ERROR` | Generic failure with stderr detail |
| `NO_PYTHON` | Python runtime missing or incompatible |

---

## 5. Build lifecycle — correctness guarantees

### Write-then-delete fix

Current (broken):
```python
write_encoded_payload(vault, payload)  # inserts vec0 rows
delete_paper_vectors(vault, paper_id)  # deletes ALL rows for paper, including just-written ones
```
Result: vec0 tables always empty.

Fixed: delete old vectors BEFORE writing new ones (or wrap in a transaction).

### Resume/force — target vec0, not Chroma

- `--resume`: check vec0 meta table row counts, not legacy Chroma directory.
- `--force`: DROP vec0 and companion meta tables, then rebuild. Never touch Chroma paths.
- Delete `get_vector_db_path()` returning legacy `.../indexes/vectors`.

### Health check — prove vec0 queryability

`embed status` must additionally:
- Run a trivial vec0 k-NN query (e.g., `SELECT rowid FROM vec_fulltext WHERE fulltext_embedding MATCH ? LIMIT 1` with a zero vector).
- Report `healthy: false` if it fails, even if meta rows exist.

### Stop — cooperative with state settlement

1. Plugin spawns `paperforge embed stop --json`.
2. Python sends SIGTERM/CTRL_BREAK_EVENT to build PID.
3. Build process catches signal, marks `build_state.status = "stopping"`, finishes current paper, flushes, then exits.
4. Stop command waits for PID to exit or timeout, then writes `status = "idle"` and returns `{state: "stopped"}`.
5. Plugin never directly kill()s the build process — it always goes through `embed stop`.

### JSON snapshot — downgrade to debug-only

`vector-runtime-state.json` is written by `embed status` for human inspection only. Plugin never reads it for control-plane decisions. Plugin reads live `embed status --json` on settings load and polls during build.

---

## 6. UX state model (summary)

Full design: `local://retrieval-ux-state-design.md` (RecoveryUXDesign agent).

### Search domain

| State | Trigger | UI |
|-------|---------|----|
| idle | No query | Input with M/@ mode badge |
| searching | Debounce fired or Enter pressed | Skeleton, input responsive (M) or disabled (@) |
| results | CLI returned matches | Cards with title/author/year/journal/score/snippet |
| empty | 0 matches | "No matching papers found. Try broader terms or @ deep search." |
| vectors not built | Error code `VECTOR_NOT_BUILT` | Warning banner + "Open Vector Settings" |
| backend unavailable | Spawn failed or error code `BACKEND_UNAVAILABLE` | Error card + "Run Doctor" + "Retry" |
| timeout | CLI exceeded 30s | "Search timed out" + Retry |
| model changed | build_state.model ≠ settings model | Warning badge + "Rebuild Vectors" |

### Build domain

| State | Trigger | UI |
|-------|---------|----|
| idle | No vectors built | "Vectors: not built" + Build button |
| ready | build_state=completed, chunks>0, healthy | "Chunks: N | model | mode" + Rebuild option |
| building | Process active | Segmented progress bar, "X/Y papers", paper_id, Stop button |
| stopping | Stop requested | Frozen bar, "Stopping..." spinner, disabled Stop |
| failed | Process exited non-zero | Error banner, stderr detail, Retry/Force Rebuild |
| corrupted | healthy=false | Warning: "Vector index corrupted" + Force Rebuild only |
| stale | build_state=running but PID dead | "Previous build interrupted" + Resume/Discard |
| deps missing | deps_installed=false | "Install Dependencies" button |
| runtime mismatch | Plugin version ≠ CLI version | Drift banner across all states |

### Button hierarchy
1. **Primary CTA:** Build, Rebuild, Retry, Resume
2. **Secondary:** Force Rebuild, Continue anyway
3. **Warning:** Stop, Force Kill
4. **Link-style:** Open Vector Settings, Run Doctor

### Destructive warnings
- Rebuild (existing chunks): "Rebuilding will replace all existing vectors ({N} chunks). This cannot be undone. Continue?"
- Force Rebuild (healthy data): "Force rebuild will delete all existing vectors and rebuild from scratch. Continue?"
- Force Rebuild (corrupted): No warning — data is already useless.

---

## 7. Implementation plan (Approach A)

### Phase 1: Unified contract (P0 fixes)

1. **Unify Python result envelope.** `search.py` and `retrieve.py` return `data.matches` with identical field names. Add `--deep` flag plumbing.
2. **Fix plugin parser.** Delete `matches`/`results`/`chunks` forking. Parse `data.matches`. Use `text` not `matched_text`. Use `first_author` not `authors`.
3. **Fix plugin spawn.** Pass `--deep` for `@`. Delete sql.js service, wasm, npm dep, all sql.js branches.
4. **Contract test.** E2E: spawn CLI → parse JSON → render. Test every error code path.

### Phase 2: Build path correctness

5. **Fix write-then-delete.** Delete old vectors before writing new ones (or transaction wrap).
6. **Fix resume/force.** Target vec0/meta tables, delete Chroma gating from `embed.py` and `_chroma.py`.
7. **Fix health probe.** Add vec0 queryability check to `embed status`.
8. **Fix stop.** Cooperative signal → state settlement → `status=idle`. Plugin goes through CLI, never direct kill.

### Phase 3: Plugin state integrity

9. **Live status via CLI.** `embed status --json` on settings load. Poll during build. Delete JSON snapshot as control-plane truth.
10. **State polling.** Plugin reads `build_state` via `embed status` every 2s during build. Renders progress from live data.

### Phase 4: UX recovery

11. **Implement state matrix.** Every state from Section 6 renders with correct buttons, copy (en/zh), a11y.
12. **Error code routing.** `classifyError(code)` maps `error.code` to UI state components.
13. **i18n.** 33 new keys under `retrieval_*` prefix in both English and Chinese.

### Phase 5: Verification

14. **Contract test suite.** Plugin → CLI → PFResult → render for M search, @ search, all error codes.
15. **Build lifecycle test.** Start → progress → stop → resume → force rebuild in disposable test vault.
16. **Literature-hub acceptance.** Smoke test all paths against the real vault.

---

## 8. Acceptance gates

| Gate | What must pass |
|------|---------------|
| M metadata search | Type "knee" → results with author/year/journal rendered within 400ms |
| @ deep search | Type "@platelet rich plasma" → semantic matches with snippets |
| sql.js deleted | No sql.js import, no wasm asset, no related code paths in bundle |
| Build → vectors exist | `embed build --resume` → vec0 tables have rows → `embed status` reports healthy |
| Stop → idle | Stop build → state settles to idle → Resume works |
| Force rebuild | `embed build --force` → old vectors dropped → new vectors exist |
| Health probe | Corrupted vec0 → status reports `healthy: false` |
| Model change detection | Switch model → warning in UI → rebuild resolves |
| Error distinction | Each error code produces distinct UI, not generic "No results" |
| Live state | Plugin status reflects SQLite truth, not stale JSON snapshot |
| Source Corpus untouched | All 868 papers, OCR, blocks, annotations preserved after rebuild |
