# Approach B — Split Read Path Evaluation

**Date:** 2026-07-10  
**Author:** SplitReadArchitecture  
**Scope:** Evaluate Approach B for the PaperForge Retrieval Experience: **Python remains the only writer/schema/build owner; sql.js remains a read-only M-search optimization with an explicit versioned query contract and Python CLI fallback; Python CLI owns `@` and build controls.**  
**Non-goals:** daemon process; native Node SQLite module; preserving Chroma artifacts; preserving current sql.js or deep-search contracts as-is.

---

## Verdict

**Viability:** **Conditionally viable, but only as a constrained optimization layer — not as a peer architecture.**

**Recommendation:** **Recommend for implementation only if PaperForge explicitly treats sql.js as disposable acceleration for M-search, never as a source of truth, and adds four mandatory controls:**

1. **Python-owned versioned M-search contract** with one authoritative field schema and one explicit compatibility version.
2. **Explicit staleness invalidation for sql.js** based on Python-owned DB generation/file freshness, with automatic fallback to Python CLI when freshness cannot be proven.
3. **Python-owned WAL/checkpoint discipline** so the file sql.js reads is intentionally publishable, not an accidental side effect of WAL housekeeping.
4. **Hard deletion of all Chroma/vector-backend ownership leftovers** so Python's SQLite/vec0 path is the only writer/build/control plane.

Without those controls, Approach B repeats the current failure mode: the optimization path drifts away from the canonical path and silently lies to the UI.

**Bottom line:**
- **Yes** to Approach B **as “Python canonical + sql.js cache-like fast path.”**
- **No** to Approach B if sql.js is allowed to invent its own query shape, freshness assumptions, build/status semantics, or result schema.

---

## Exact ownership boundary

### Canonical owner: Python

Python MUST own all of the following:

- **Storage ownership:** `paperforge.db`, vec0 tables, companion meta tables, FTS tables, `build_state`, runtime snapshots.
- **Schema ownership:** `paperforge/memory/schema.py` and every migration/version bump.
- **Build ownership:** `paperforge embed build|status|stop` and all per-paper replacement semantics.
- **Deep query ownership:** `paperforge retrieve`, including `@` routing, query planning, hybrid search, vector retrieval, error taxonomy.
- **Failure taxonomy ownership:** PFResult envelope, error codes, warnings, next actions.
- **Deployment provenance contract:** any change to retrieval schema or CLI envelope must be released as a coordinated Python + plugin contract version.

### Optimization-only reader: sql.js

sql.js MUST own only this:

- **One read-only metadata query path for M-search debounce.**
- **No writes.**
- **No schema authority.**
- **No build state interpretation.**
- **No deep search.**
- **No independent result schema.**
- **No fallback policy beyond “if unsafe/unsupported/stale, route to Python CLI.”**

### Plugin/TypeScript owner

The plugin should own only:

- debounce/UI behavior,
- process spawning for Python CLI,
- displaying the canonical result envelope,
- displaying build state that Python has already normalized.

It MUST NOT own retrieval semantics.

---

## Observed facts

### 1. Python already owns the real database and schema

**Observed:** `paperforge/memory/schema.py` defines schema version 6, creates `papers`, `paper_fts`, vec0 tables, companion meta tables, and `build_state`.

**Observed:** `paperforge/memory/db.py` opens write connections with `PRAGMA journal_mode=WAL;`.

**Observed:** all active retrieval/build/status code paths already go through Python modules against `paperforge.db`.

**Implication:** Approach B aligns with the current real ownership pattern. It does not require a new canonical writer; it requires removing drift around that writer.

---

### 2. sql.js is already only a reader, but it is currently an unsafe one

**Observed:** `paperforge/plugin/src/services/db.ts` loads the full `paperforge.db` file via `fs.readFileSync`, constructs an in-memory sql.js database, and prepares one statement.

**Observed:** the query is currently wrong:

```sql
SELECT zotero_key, title, first_author, year, journal, domain, abstract, rank
FROM paper_fts
WHERE paper_fts MATCH ?
ORDER BY rank
LIMIT ?
```

`paper_fts` has **no `year` column**. `year` lives on `papers`. Python's canonical search path correctly does:

```sql
FROM paper_fts f
JOIN papers p ON p.rowid = f.rowid
```

**Observed:** once sql.js initializes, it keeps `_db` and `_queryStmt` for the lifetime of the view. There is **no invalidation when Python changes the database**.

**Observed:** the real database file in the live vault is **88.9 MB**.

**Implication:** sql.js is not a tiny query accelerator over a small index. It is an **88.9 MB in-memory snapshot** of a Python-owned SQLite file. That is acceptable only if the freshness and contract boundaries are explicit and aggressively narrow.

---

### 3. Python CLI already is the canonical fallback and deep path

**Observed:** plugin `dashboard.ts` does:
- sql.js path for debounced non-`@` queries,
- Python CLI path for Enter and for sql.js failure,
- Python CLI path for all `@` queries.

**Observed:** `paperforge/commands/search.py` returns `PFResult(... data.matches ...)`.

**Observed:** `paperforge/commands/retrieve.py` returns `PFResult(... data.chunks ...)` for both standard and deep paths.

**Observed:** plugin currently parses only `data.matches` and `data.results`, never `data.chunks`.

**Observed:** plugin also fails to pass `--deep` for `@` queries.

**Implication:** the split path is already present structurally, but the **typed envelope is not unified**, so the Python-owned canonical path cannot currently be rendered reliably.

---

### 4. Python already owns build state in SQLite, but the plugin reads a stale JSON projection

**Observed:** `paperforge/embedding/build_state.py` persists build state in the `build_state` table in `paperforge.db`.

**Observed:** `paperforge/memory/state_snapshot.py` writes `vector-runtime-state.json`.

**Observed:** plugin `memory-state.ts` reads the JSON snapshot, not SQLite truth.

**Observed:** `settings.ts` treats build as running if either the child process exists **or** the JSON snapshot says `status == "running"`.

**Implication:** Python should remain the owner of build truth; the JSON file must be treated as a disposable projection, not a second state authority.

---

### 5. Legacy Chroma ownership is still contaminating Python's canonical path

**Observed:** `paperforge/embedding/_chroma.py` still defines:
- `get_vector_db_path()` returning legacy `.../indexes/vectors`,
- Chroma deletion,
- migration,
- dual-store delete behavior.

**Observed:** `embed.py --resume` and `--force` still gate on the Chroma directory path.

**Observed:** `embed status` still checks for `chromadb` dependency.

**Implication:** Approach B cannot be safe enough until Python ownership is internally cleaned up. sql.js is not the only split-brain problem; Chroma leftovers also split Python's own control plane.

---

## WAL, checkpoint, and staleness analysis

This is the most important architectural question for Approach B.

### Observed behavior

- Python write connections open SQLite in **WAL** mode.
- sql.js does **not** open SQLite; it reads the current `paperforge.db` file bytes and instantiates an in-memory database.
- sql.js does **not** read the WAL file.
- sql.js does **not** track DB generation, WAL state, file mtime, file size, schema version, or query compatibility version after initial load.
- Live vault evidence showed `paperforge.db-wal` at **0 bytes** during audit, which means sql.js was not stale **at that moment**. That does **not** prove the design is safe.

### Consequence

Approach B creates a **published-file problem**:

- Python writes to the canonical DB.
- sql.js reads a **published snapshot** of that DB.
- WAL means “committed in SQLite” is **not identical** to “visible in the main DB file sql.js reads.”

Therefore, **sql.js freshness cannot be inferred from Python commit success alone.**

### What must be true for sql.js to be safe enough

Python must explicitly publish a sql.js-readable snapshot. The minimum credible mechanism is:

1. **Python remains sole writer.**
2. After a metadata-changing operation that should become visible to M-search, Python must:
   - complete the transaction,
   - run an explicit WAL checkpoint appropriate for publication,
   - update a Python-owned freshness marker/generation,
   - only then treat the metadata state as published.
3. sql.js must validate that the loaded snapshot corresponds to the current published generation before answering.
4. If freshness cannot be proven, the plugin must use Python CLI.

### Recommended minimum control

**Do not make sql.js reason about WAL directly.**

Instead:
- Python publishes a **monotonic metadata generation** in `meta` or a dedicated runtime table/file.
- sql.js stores the loaded generation alongside `_db`.
- Before serving a query, sql.js checks a **cheap freshness signal**:
  - either DB file `mtime/size` plus generation,
  - or a tiny Python-owned sidecar/runtime file containing generation + query contract version + published-at timestamp.
- If mismatch: reload the DB snapshot or immediately fall back to CLI.

### Fatal risk if omitted

If Python does not explicitly publish and sql.js does not explicitly validate freshness, M-search will intermittently return stale results after sync/rebuild/update with **no visible error**. That violates the “preserve user-visible M real-time metadata search” requirement even if average latency looks good.

### [INFERENCE] safest publication rule

A practical safe rule is:
- Python checkpoints/publishes only after metadata rebuild/sync phases, not on every paper write inside a long build.
- M-search can lag during active rebuild, but once Python reports rebuild complete, sql.js must see the same generation.

This keeps checkpointing cost bounded and preserves correctness at stable points.

---

## Database reload and version invalidation

### Current observed state

`db.ts` has only:
- `_db: SqlJsDatabase | null`
- `_queryStmt: SqlJsStatement | null`
- `_sqlJsInitialized` / `_sqlJsFailed` in the dashboard caller

It has **no**:
- loaded DB path metadata,
- loaded generation,
- loaded schema version,
- loaded query-contract version,
- reload-on-change behavior.

### Required invalidation contract

Approach B needs **three distinct invalidation dimensions**:

1. **Schema version** — owned by Python schema.
2. **M-search query-contract version** — owned by Python query contract, not by ad hoc TS code.
3. **Data freshness generation** — owned by Python publication/checkpoint step.

sql.js should only serve M-search if all three match what it loaded.

### Why schema version alone is insufficient

The current failure proves this:
- DB schema version is valid.
- sql.js query is still wrong.

So a schema-compatible DB can still be **query-contract incompatible**.

### Minimum safe version model

Python should publish something equivalent to:

```json
{
  "schema_version": 6,
  "m_search_contract_version": 1,
  "metadata_generation": 42,
  "published_at": "..."
}
```

sql.js should load only if:
- schema version is supported,
- M-search contract version is supported,
- generation matches the published state it has loaded.

Otherwise: fallback to CLI.

### Recommendation

**Do not let TypeScript discover schema by duplicating SQL assumptions.**

Instead, define one explicit Python-owned M-search contract that says:
- exact columns available to M-search,
- exact field names returned to UI,
- ranking semantics,
- nullability/default rules,
- compatibility version.

Then sql.js implements **that contract**, not “whatever looks queryable today.”

---

## Schema discovery vs duplicated SQL

### Observed drift today

Python canonical M-search query in `paperforge/memory/fts.py`:

```sql
SELECT p.zotero_key, p.citation_key, p.title, p.year, p.doi,
       p.first_author, p.journal, p.domain, p.lifecycle,
       p.ocr_status, p.deep_reading_status, p.next_step,
       substr(p.abstract, 1, 300) as abstract,
       rank
FROM paper_fts f
JOIN papers p ON p.rowid = f.rowid
WHERE paper_fts MATCH ?
ORDER BY rank
LIMIT ?
```

sql.js query in `db.ts` duplicates only a subset and duplicates it incorrectly.

### Design choice

Approach B is viable only if the query split is **implementation split, not contract split**.

That means:
- Python defines the contract.
- TypeScript sql.js may have its own SQL text, but it must be treated as an implementation of the same contract.
- Contract tests must compare sql.js M-search output against Python CLI M-search output on the same vault fixture.

### Smallest credible mitigation

Create one explicitly documented shared contract for M-search:
- `zotero_key`
- `citation_key`
- `title`
- `year`
- `first_author`
- `journal`
- `domain`
- `abstract`
- `rank` (or explicitly hidden)
- navigation identity fields if needed

Then make both:
- Python `search.py`
- sql.js `db.ts`

produce exactly those fields.

### Recommendation on field naming

Keep Python field names. They already align with the schema.

The plugin should adapt to canonical Python names (`first_author`, `text`, etc.), not force Python to invent UI-only aliases unless the contract intentionally defines them.

---

## Fallback semantics

### Current observed fallback

- Debounced M-search tries sql.js first.
- If sql.js init/query throws, `_sqlJsFailed = true` and future debounce searches fall through to Python CLI.
- Enter always uses Python CLI.

### What works about this

This is the right high-level shape for Approach B:
- fast local optimistic path,
- canonical process fallback,
- explicit Enter path that always gets fresh Python-owned semantics.

### What is missing

Current fallback distinguishes only:
- sql.js succeeded,
- sql.js threw.

Approach B needs richer fallback reasons:

1. **Unsupported contract version** → fallback to CLI.
2. **Stale unpublished snapshot** → fallback to CLI or reload.
3. **sql.js init in progress on first keystroke** → do not mark permanent failure.
4. **sql.js memory/wasm init too slow** → temporary CLI fallback allowed, then retry sql.js after init.
5. **sql.js query execution error** → fallback and surface diagnostics.

### First-keystroke latency reality

Because `paperforge.db` is **88.9 MB**, first sql.js initialization is not trivial:
- full file read,
- wasm module init,
- in-memory DB construction,
- prepared statement creation.

**[INFERENCE] Expected first-use init cost:** roughly **350–500 ms** on the audited machine class.

That means the current 200 ms debounce likely loses the first-query race unless initialization is prewarmed or specially handled.

### Resulting requirement

Approach B needs one of these:

- **prewarm sql.js** when the view opens, or
- **explicit first-init state** where the first debounced query waits/retries instead of permanently declaring sql.js failed, or
- **accept CLI for first query, sql.js for subsequent ones** as a documented performance characteristic.

### Recommendation

The smallest credible version is:
- first query may fall back to CLI while sql.js initializes,
- but initialization failure must be distinguished from initialization pending,
- and once sql.js finishes init, the same query should be re-issued through sql.js if still current.

Otherwise the optimization exists on paper but not in real user typing flow.

---

## Typed result envelope

### Observed state

`PFResult` already provides a canonical outer envelope:

```json
{
  "ok": true|false,
  "command": "...",
  "version": "...",
  "data": ...,
  "error": ...,
  "warnings": [...],
  "next_actions": [...]
}
```

But inside `data` there is drift:
- search → `data.matches`
- retrieve standard → `data.chunks`
- retrieve deep → `data.chunks`
- plugin parser accepts `matches` and `results`, not `chunks`

### Approach B requirement

Because Python owns the canonical read semantics, the inner envelope also needs to be canonical.

### Recommendation

Use one canonical inner envelope shape for all user-facing search/retrieval commands, e.g.:

```json
{
  "query": "...",
  "mode": "metadata" | "deep" | "vector",
  "matches": [...],
  "count": N,
  "route_explanation": {...}
}
```

Then:
- M-search returns `matches`
- deep/vector retrieval also returns `matches`
- each match may have mode-specific fields, but the list key is stable

### Why this matters for Approach B

If Python is canonical, the plugin should not have to know whether a result came from:
- sql.js M-search,
- Python M-search,
- Python vector retrieve,
- Python hybrid deep search.

It should only render the canonical match type for that mode.

### Minimum field unifications needed immediately

- `first_author` vs `authors`
- `text` / `chunk_text` / `matched_text`
- `matches` vs `chunks`
- `score` semantics
- `zotero_key` / `paper_id` navigation identity

### Recommendation

For Approach B, keep `PFResult` outer envelope and standardize **one canonical `data.matches` list** across search and retrieval.

---

## Failure distinction

Approach B needs the UI to distinguish **empty results** from **broken path**.

### Current observed failures collapse together

Today “No results found” can mean:
- sql.js query contract broke,
- Python deep result envelope broke,
- plugin ignored `chunks`,
- vector store is empty,
- vector store is unreadable,
- deep mode was never actually selected,
- true zero-result query.

That is unacceptable for a split architecture.

### Minimum required failure classes

For M-search:
- `M_SEARCH_UNSUPPORTED_CONTRACT`
- `M_SEARCH_STALE_SNAPSHOT`
- `M_SEARCH_SQLJS_INIT_FAILED`
- `M_SEARCH_SQLJS_QUERY_FAILED`
- `M_SEARCH_CLI_FAILED`
- `M_SEARCH_NO_MATCHES`

For deep search:
- `DEEP_SEARCH_NOT_INDEXED`
- `DEEP_SEARCH_INDEX_UNREADABLE`
- `DEEP_SEARCH_PROVIDER_FAILED`
- `DEEP_SEARCH_NO_MATCHES`

For build lifecycle:
- `BUILD_RUNNING`
- `BUILD_STOPPING`
- `BUILD_CANCELLED`
- `BUILD_FAILED`
- `BUILD_STALE_PID_RECOVERED`
- `BUILD_READY`
- `BUILD_NOT_BUILT`

### Recommendation

Python should own these distinctions and emit them through PFResult. The plugin should not guess from stderr, missing keys, or implicit empty arrays.

---

## Comparison against every P0 / P1 failure-matrix row

## P0 rows

### Row 1: sql.js `paper_fts.year` column missing

**Approach B status:** **Fixable and compatible.**

- Cause is duplicated TypeScript SQL drifting from Python schema.
- Approach B resolves this only if Python owns the contract and sql.js becomes a strict implementation of that contract.
- Required control: shared M-search contract + sql.js compatibility version + contract parity tests.

**Verdict:** not a reason to reject Approach B; it is exactly the failure Approach B must prevent.

---

### Row 2: Plugin does not pass `--deep` for `@` queries

**Approach B status:** **Directly compatible and required to fix.**

- Under Approach B, Python CLI owns `@` semantics.
- Therefore the plugin must pass `--deep` or invoke the exact canonical deep-search command/flag shape Python defines.

**Verdict:** fully resolvable inside Approach B.

---

### Row 3: CLI returns `data.chunks`, plugin expects `data.matches` / `data.results`

**Approach B status:** **Must be fixed or Approach B fails.**

- This is the canonical result-envelope problem.
- If Python owns canonical retrieval, plugin and Python cannot disagree on inner list key.

**Verdict:** mandatory fix; otherwise Approach B is non-viable.

---

### Row 5: vec0 tables are empty (delete-after-write bug)

**Approach B status:** **Independent of sql.js, but fatal unless fixed.**

- This is a Python ownership bug.
- It proves why Python must be the only writer and why its canonical path must be internally coherent before sql.js can be trusted as an optimization.

**Verdict:** Approach B remains viable only if this is fixed in Python first.

---

## P1 rows

### Row 6: `--resume` gates on legacy Chroma path

**Approach B status:** **Must be deleted/fixed in Python.**

- Not a split-read problem directly.
- But it violates “Python owns build controls” because Python still consults a non-canonical store.

**Verdict:** mandatory cleanup for Approach B.

---

### Row 7: `--force` deletes legacy Chroma dir, not vec0/meta tables

**Approach B status:** **Must be fixed in Python.**

- Same reasoning as Row 6.
- Approach B does not tolerate build controls targeting anything except active SQLite/vec0 artifacts.

**Verdict:** mandatory cleanup.

---

### Row 8: Dead PID / Stop cannot settle

**Approach B status:** **Fixable and required.**

- Python CLI owns build control in Approach B, so stop semantics must be robust.
- Plugin should not be a second kill authority beyond requesting canonical stop.

**Verdict:** mandatory fix; otherwise “Python owns build controls” is false in practice.

---

### Row 9: JSON snapshot vs SQLite build-state split-brain

**Approach B status:** **Must be narrowed, not necessarily deleted.**

- SQLite must be truth.
- JSON snapshot may remain as a UI cache/projection only.
- Plugin must treat JSON as advisory and Python CLI/SQLite-derived state as canonical.

**Verdict:** mandatory truth-boundary fix.

---

### Row 10: Status counts meta rows, not vec0 queryability

**Approach B status:** **Must be fixed in Python.**

- Python owns build state and readiness.
- Counting meta rows is insufficient.
- Status must probe actual vec0 queryability and row consistency.

**Verdict:** mandatory fix.

---

## Additional P1/P2 relevance to Approach B

### P1: legacy Chroma still in production control flow

**Approach B impact:** fatal to the ownership boundary if retained.

### P1: dimension/model change orphans metadata

**Approach B impact:** Python schema/build owner must fix generation replacement semantics.

### P2: provider failure aborts deep BM25 fallback

**Approach B impact:** Python deep path should degrade correctly because Python owns `@` semantics.

### P2: source/deployed bundle mismatch

**Approach B impact:** not unique to Approach B, but split-read increases sensitivity to provenance drift. Contract versioning becomes more important, not less.

---

## Build-state truth and process lifecycle under Approach B

### Desired truth model

- **Truth source:** SQLite `build_state` in `paperforge.db`
- **Writer:** Python only
- **Projection/cache:** `vector-runtime-state.json` may exist, but only as a read-only summary generated from Python truth
- **Plugin child-process state:** ephemeral local UI state only

### Required lifecycle rules

1. Plugin requests build/start/stop through Python CLI.
2. Python acquires and updates canonical build state.
3. Python writes terminal states (`completed`, `failed`, `cancelled`, `idle`) in finally/handler paths.
4. Plugin may display streamed progress, but must reconcile against Python canonical state.
5. Stale PID detection and crash recovery belong to Python, not to sql.js or dashboard heuristics.

### Why this matters to Approach B

Approach B is only about split **read** on M-search. If build truth is also split, the architecture stops being constrained and starts becoming another incoherent multi-owner system.

---

## Deployment provenance

### Observed state

- Python is an **editable install** from the repo.
- Plugin bundle is manually copied and may differ by build mode from repo artifact.
- There is no auditable single joint runtime revision.

### Impact on Approach B

Approach B is more sensitive to provenance than CLI-only architecture because:
- Python contract changes can silently break sql.js compatibility.
- Plugin bundle can be stale while Python is current.

### Minimum acceptable provenance rule

Any release that changes:
- M-search contract,
- deep-search result envelope,
- build-state semantics,
- schema version,
- publication/freshness generation rules,

must be treated as a **joint contract release** for Python + plugin.

### Recommendation

Add an explicit query-contract version surfaced to both Python CLI and plugin, and fail/fallback fast when mismatched.

---

## Deletion list

Approach B should delete anything that implies a second canonical writer or storage owner.

### Delete / stop using

1. **Chroma production control-path ownership**
   - `paperforge/embedding/_chroma.py:get_vector_db_path()` as build gate
   - Chroma delete path in `delete_paper_vectors()`
   - `migrate_chroma_to_vec0()` from production path
   - `chromadb` dependency requirement in `embed status`

2. **Backend abstraction that is not actually canonical**
   - any production-facing `ChromaBackend` / `LanceBackend` ownership expectations
   - backend-factory paths that imply multiple live stores if only vec0/SQLite is canonical

3. **Plugin-side retrieval semantics**
   - deep-mode semantics inferred without `--deep`
   - plugin-side result-key guessing (`matches` vs `results` vs missing `chunks`)
   - plugin-side field assumptions that diverge from Python canonical names

4. **Second build-state truth**
   - `vector-build-state.json` legacy path semantics
   - any UI logic that treats JSON snapshot as canonical over Python-owned state

### Keep, but narrow

- `vector-runtime-state.json` only as disposable UI projection.
- sql.js only as M-search accelerator with strict invalidation/fallback.

---

## Smallest credible mitigation set

This is the minimum set that makes sql.js **safe enough** rather than canonical.

### 1. Versioned Python-owned M-search contract

Define one contract with:
- field names,
- query semantics,
- compatibility version,
- ranking expectations,
- freshness requirements.

### 2. Explicit publication/freshness generation

Python must publish when M-search-visible metadata is safe for sql.js to read.

### 3. sql.js compatibility gate

sql.js serves only when:
- supported schema version,
- supported M-search contract version,
- loaded generation matches current published generation.

Else: reload or fallback.

### 4. First-init handling for 88.9 MB DB

Because initial sql.js load is expensive:
- initialization pending must not be treated as permanent failure,
- first-query behavior must be explicitly defined,
- prewarm or post-init retry is strongly recommended.

### 5. Canonical PFResult inner envelope alignment

At minimum:
- all user-facing retrieval/search return `data.matches`,
- stable navigation identity,
- stable author/snippet field names.

### 6. Python-only build-control cleanup

Fix/delete:
- delete-after-write,
- Chroma path gates,
- dead PID stop failure,
- meta-only health checks,
- split build-state truth.

### 7. Contract parity tests

A test vault must prove:
- sql.js M-search output equals Python CLI M-search output for representative queries,
- sql.js stale generation falls back correctly,
- `@` path renders canonical Python results,
- build/status/stop operate entirely through Python truth.

---

## Fatal risks

### Fatal risk 1: stale sql.js snapshot served as if current

If Python publication and sql.js freshness validation are not explicit, users get stale M-search with no error.

**Severity:** fatal to Approach B's credibility.

**Smallest mitigation:** Python-owned published generation + sql.js invalidation/fallback.

---

### Fatal risk 2: contract drift between Python search and sql.js query

The current `year` bug is direct proof this happens.

**Severity:** fatal unless contract versioning + parity tests exist.

**Smallest mitigation:** one documented M-search contract and fixture parity tests.

---

### Fatal risk 3: first-query sql.js init loses to debounce and permanently degrades to CLI

With an 88.9 MB DB, first initialization is expensive enough to miss the first 200 ms debounce window.

**Severity:** not correctness-fatal, but can nullify the optimization in real UX.

**Smallest mitigation:** pending-vs-failed distinction, init retry/replay, optional prewarm.

---

### Fatal risk 4: Python canonical path remains internally split by Chroma leftovers

If build/resume/force still target legacy Chroma paths, sql.js safety is irrelevant because the canonical path itself is not coherent.

**Severity:** fatal to the “Python sole owner” claim.

**Smallest mitigation:** delete Chroma production gates and target only SQLite/vec0 artifacts.

---

### Fatal risk 5: build/status truth remains split between SQLite and JSON snapshot

If plugin keeps trusting stale JSON as truth, recovery and status UX remain misleading.

**Severity:** fatal to lifecycle reliability.

**Smallest mitigation:** SQLite truth; JSON projection only.

---

## Approximate files affected

### TypeScript / plugin

1. `paperforge/plugin/src/services/db.ts`
   - fix query
   - add compatibility/freshness gating
   - add reload/invalidation logic
   - distinguish init-pending vs init-failed

2. `paperforge/plugin/src/views/dashboard.ts`
   - pass canonical deep flag / command shape
   - parse canonical PFResult inner envelope
   - render canonical fields (`first_author`, snippet field)
   - handle sql.js pending/retry/fallback states

3. `paperforge/plugin/src/services/memory-state.ts`
   - narrow JSON snapshot interpretation to projection/cache

4. `paperforge/plugin/src/settings.ts`
   - stop treating JSON snapshot as equal to canonical state
   - rely on Python-owned lifecycle semantics

5. `paperforge/plugin/tests/...`
   - add end-to-end contract tests for M-search fallback and `@` rendering

### Python / canonical retrieval

6. `paperforge/memory/fts.py`
   - define/anchor canonical M-search contract fields

7. `paperforge/commands/search.py`
   - emit canonical `data.matches`
   - optionally expose contract version/freshness metadata

8. `paperforge/commands/retrieve.py`
   - unify to canonical `data.matches`
   - deep path selection and field naming

9. `paperforge/commands/embed.py`
   - fix delete-after-write ordering/atomic replacement
   - remove Chroma-gated resume/force logic
   - settle stop lifecycle robustly
   - publish freshness/generation at appropriate points

10. `paperforge/embedding/_chroma.py`
   - remove production ownership behavior or collapse to vec0-only helpers

11. `paperforge/embedding/status.py`
   - validate actual vec0 queryability, not meta rows only

12. `paperforge/embedding/build_state.py`
   - canonical lifecycle semantics if needed

13. `paperforge/embedding/dim_detect.py`
   - generation/model/dimension replacement cleanup

14. `paperforge/memory/state_snapshot.py`
   - keep only as Python-owned projection
   - possibly expose published generation / contract version summary

15. `paperforge/memory/schema.py`
   - if adding explicit generation/contract metadata storage

16. docs / contract research artifact(s)
   - retrieval contract documentation and acceptance matrix

**Expected touched footprint:** roughly **12–16 files**, depending on whether generation metadata lives in SQLite meta, runtime snapshot, or both.

---

## Minimal implementation sequence

1. **Fix Python canonical path first**
   - delete-after-write
   - resume/force Chroma gates
   - build/status truth issues
   - canonical deep-search command routing

2. **Define canonical result envelope and M-search contract**
   - one inner `data.matches`
   - one field vocabulary
   - one contract version

3. **Make plugin consume only canonical Python contract**
   - `@` deep flag
   - result rendering fields
   - failure distinction

4. **Constrain sql.js to that contract**
   - correct JOIN query
   - compatibility version check
   - freshness generation/invalidation
   - pending-vs-failed init handling

5. **Add parity and fallback acceptance tests**
   - sql.js vs Python M-search equivalence
   - stale snapshot fallback
   - `@` end-to-end rendering
   - build-state truth/recovery flows

This ordering matters: **do not harden sql.js before the Python canonical path is coherent.**

---

## Expected / measured latency

### Measured / observed facts

- Live `paperforge.db` size: **88.9 MB**.
- `sql-wasm.wasm` size: **659,730 bytes**.
- sql.js current design loads the **entire DB file** into memory on initialization.
- Once loaded, sql.js prepared-statement queries are expected to be very fast because they are in-memory and single-statement.

### [INFERENCE] expected latency envelope

**sql.js steady-state query:** ~**5–20 ms** for typical M-search after initialization.  
**Python CLI M-search:** ~**200–500 ms** wall time including process spawn/import/SQLite open/query/JSON parse.  
**sql.js first initialization:** ~**350–500 ms** on the audited machine due to 88.9 MB file read + wasm init + DB construction.

### Interpretation

- sql.js is plausibly worth keeping for steady-state M-search responsiveness.
- sql.js is **not** a free optimization on first use.
- At current DB size, the first debounce will likely miss unless initialization is prewarmed or retried intelligently.

---

## Acceptance seams

The implementation should be approved only if these seams are demonstrably covered:

1. **Contract seam:** Python CLI and sql.js return identical M-search records for the same test vault/query set.
2. **Freshness seam:** after Python publishes metadata changes, sql.js either reloads to the same generation or falls back to CLI.
3. **Deep seam:** `@` from plugin input reaches Python canonical deep path and renders returned matches.
4. **Failure seam:** empty results and broken-path results are visibly distinct.
5. **Lifecycle seam:** build/status/stop/restart recover from dead PID and do not rely on Chroma artifacts.
6. **Deployment seam:** contract mismatch between plugin bundle and Python runtime fails safe to CLI rather than silently misrendering.

---

## Recommendation for implementation

**Recommended, with constraints.**

I recommend implementing Approach B **only** as the following disciplined architecture:

> **Python is the sole owner of retrieval storage, schema, build lifecycle, deep search, and contract semantics. sql.js is a strictly read-only, version-gated, freshness-gated optimization for debounced M-search and must always be safe to bypass.**

### Why recommend it

- It preserves the current user-visible M real-time search affordance.
- It avoids introducing a daemon or native Node SQLite module.
- It matches the repo's real canonical center of gravity: Python + SQLite/vec0.
- It allows the plugin to stay thin and UX-focused.

### Why not make it canonical

Because the current evidence shows that whenever TypeScript owns query semantics independently, it drifts. sql.js should survive only as a **cache-like read path with a contract leash**.

### Final yes/no

- **Yes, implement Approach B** if the team wants to preserve fast debounced M-search without adding a daemon/native Node module.
- **No, do not implement a loose version of Approach B** where sql.js gets independent schema/query assumptions or where Python publication/freshness is left implicit.

That looser version is exactly what failed already.
