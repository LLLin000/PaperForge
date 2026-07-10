# PaperForge Retrieval Architecture and Contract Drift

- Evidence date: 2026-07-10
- Wayfinder ticket: [Inventory the live retrieval architecture and contract drift](https://github.com/LLLin000/PaperForge/issues/53)
- Parent map: [Wayfinder: Restore PaperForge retrieval end to end](https://github.com/LLLin000/PaperForge/issues/45)
- Scope: architecture inventory only; no production fix was applied

## Executive finding

PaperForge does not currently have one coherent “vector layer.” It has four partially overlapping systems whose contracts drift independently:

1. Metadata search has a sql.js path and a Python CLI path.
2. The Obsidian `@` path invokes standard vector retrieval, while a separate hybrid deep-search implementation exists but is not selected by the UI.
3. Vector build control has three state representations: Python process state, SQLite `build_state`, and a JSON runtime snapshot consumed by the plugin.
4. ChromaDB migration code and a Chroma/Lance backend abstraction remain beside a direct sqlite-vec production path.

The highest-impact observed failures are contractual, not tuning problems:

- The sql.js metadata query selects a nonexistent `paper_fts.year` column and cannot initialize.
- The `@` UI does not pass the CLI `--deep` flag.
- Every retrieve response is emitted under `data.chunks`, while the plugin only accepts `data.matches` or `data.results`.
- The build loop writes new vec0 rows and then deletes every row for the same paper, including the new rows.
- Resume/force decisions still use the legacy Chroma `indexes/vectors` directory even though active vectors live inside `paperforge.db`.
- The plugin renders nested build state from a JSON snapshot rather than the live SQLite state, so a dead process can remain visually “running.”

These facts explain why isolated fixes have not stabilized the user journey: each fix has targeted one representation while another representation continued to drive the UI or data path.

## Domain boundary

The Wayfinder map already established:

- **Source Corpus**: paper notes, OCR output, structured blocks, metadata, and user annotations. It is authoritative and must be preserved.
- **Retrieval Artifacts**: FTS indexes, embeddings, vec0 tables, and companion metadata. They are disposable and may be rebuilt.
- **Retrieval Experience**: M metadata search, `@` knowledge search, and the build/status/stop/resume controls needed to keep both usable.

This audit does not treat existing ChromaDB, vec0, or FTS contents as preservation targets.

## Current execution map

```mermaid
flowchart TD
    U[Obsidian user]

    U -->|M input, 200 ms| SJ[sql.js search]
    SJ -->|reads a one-time copy| DB[(paperforge.db)]
    SJ -->|prepare fails: paper_fts.year missing| CF[Python CLI fallback]
    U -->|M Enter| CF
    CF --> SC[paperforge search]
    SC --> PF[paper_fts JOIN papers]
    SC --> PM[data.matches]
    PM --> UI[Search card renderer]

    U -->|@ Enter| RC[paperforge retrieve without --deep]
    RC --> MR[merge_retrieve]
    MR --> VEC[vec_fulltext + vec_body + vec_objects]
    RC --> CH[data.chunks]
    CH -->|plugin ignores chunks| EMPTY[No results found]

    HS[hybrid_search]
    HS --> BF[body_units_fts BM25]
    HS --> VB[vec_body + vec_objects]
    HS --> FUSION[0.3 BM25 + 0.7 vector]
    RC -. UI does not select .-> HS

    SET[Plugin settings]
    SET -->|spawn --resume/--force| EB[paperforge embed build]
    EB --> BS[(SQLite build_state)]
    EB --> ENC[API encode thread pool]
    ENC --> W[write new vec0 rows]
    W --> D[delete all rows for paper]
    D --> PROG[stdout progress + build_state progress]

    ES[paperforge embed status] --> SNAP[vector-runtime-state.json]
    BS --> ES
    SNAP --> SET
```

## Path A — M metadata search

### Observed flow

1. `PaperForgeStatusView.renderSearchSection()` creates the input and starts a 200 ms debounce for non-`@` text (`paperforge/plugin/src/views/dashboard.ts:2370-2430`).
2. The debounce calls `executeSearch({source: "sqljs"})`; Enter bypasses sql.js and calls `executeSearch({source: "cli"})`.
3. `initDatabase()` loads `sql-wasm.wasm`, reads the full `paperforge.db` file into a sql.js in-memory database, and prepares a statement (`paperforge/plugin/src/services/db.ts:61-88`).
4. The statement selects `zotero_key, title, first_author, year, journal, domain, abstract, rank` directly from `paper_fts`.
5. `paper_fts` has no `year` column. `year` belongs to `papers` (`paperforge/memory/schema.py:17-53,89-103`).
6. The sql.js initialization throws, `_sqlJsFailed` becomes true, and the request falls through to `python -m paperforge search <query> --json` (`dashboard.ts:2453-2523`).
7. The Python path correctly joins `paper_fts` to `papers`, so it can select `p.year` and structured fields (`paperforge/memory/fts.py:66-81`).
8. `paperforge search` returns a `PFResult` whose list is `data.matches` (`paperforge/commands/search.py:49-66`). The plugin accepts this key.
9. Result navigation resolves `main_note_path`/`note_path`, or looks up `zotero_key` in the cached formal index (`dashboard.ts:2627-2669`).

### Runtime proof

A read-only query against `D:/L/OB/Literature-hub/System/PaperForge/indexes/paperforge.db` reported:

```text
paper_fts columns:
zotero_key, citation_key, title, first_author, authors_json,
abstract, journal, domain, collection_path, collections_json

TypeScript query verdict:
OperationalError: no such column: year
```

The deployed FTS DDL is external-content FTS and matches the source DDL; the failure is the TypeScript query, not a standalone/external-content migration mismatch.

### Additional M-search drift

- `SearchResultItem` and Python return `first_author`, but `renderSearchResults()` only renders `authors`; author text is omitted (`db.ts:12-21`, `dashboard.ts:2677-2687`).
- sql.js returns `rank`, but the renderer displays only `score`; metadata relevance is not shown.
- sql.js reads the database once and keeps `_db` and `_queryStmt` for the view lifetime. It has no invalidation when `paperforge.db` changes.
- Once sql.js fails, every later debounced query falls directly into the Python CLI path. There is no cancellation or request-generation guard, so multiple CLI searches can overlap and older results can overwrite newer input. `[INFERENCE]`
- No plugin test imports or exercises `db.ts`, `executeSearch()`, or `renderSearchResults()`.

## Path B — `@` retrieval

### What the UI actually executes

1. The plugin recognizes `@`, strips the prefix, and selects CLI command name `retrieve` (`dashboard.ts:2432-2442`).
2. It spawns:

   ```text
   python -m paperforge retrieve <query> --json
   ```

   (`dashboard.ts:2519-2523`).
3. It does **not** append `--deep`.
4. `commands.retrieve.run()` therefore sees `deep=False` and executes the standard vector branch, not `hybrid_search()` (`paperforge/commands/retrieve.py:42-51,88-140`).
5. Standard retrieval calls `merge_retrieve()`, which queries `vec_fulltext`, `vec_body`, and `vec_objects` directly (`paperforge/embedding/search.py:66-127`).
6. The CLI returns results under `data.chunks` (`commands/retrieve.py:170-178`).
7. The plugin parser only recognizes `data.matches` and `data.results`; it does not recognize `data.chunks` (`dashboard.ts:2556-2573`).
8. The renderer therefore receives an empty list and displays “No results found.”

### The unused deep implementation

`hybrid_search()` exists and is reachable only when CLI `--deep` is explicitly supplied:

1. `expand_query()` generates abbreviation/synonym variants.
2. `_bm25_search()` queries `body_units_fts`.
3. `_vec_search()` calls the embedding API and queries `vec_body` and `vec_objects`.
4. `_fuse_results()` uses `0.3 * BM25 + 0.7 * vector`.
5. Results are returned under `data.chunks` with `text`, not `matched_text`.

Even if the UI added `--deep`, two more contracts would still fail:

- The plugin would still ignore `data.chunks`.
- The deep card renderer looks for `matched_text`, while Python emits `text` (`dashboard.ts:2727-2737`, `embedding/search.py:210-224,263-268`).

### Hybrid-search behavior drift

- The docstring claims BM25-only fallback when vec0 is unavailable, but `_vec_search()` constructs `OpenAICompatibleProvider` and calls the API before entering its per-table exception handlers. Missing credentials, network failure, or provider failure aborts the whole hybrid request instead of returning BM25-only results (`embedding/search.py:231-258`).
- Vector object results are merged into existing BM25 rows only when `(paper_id, text)` matches. `vec_objects` text generally does not exist in body BM25 results. Vector-only rows are synthesized only when the entire BM25 result set is empty, so object hits are normally discarded (`embedding/search.py:284-352`).
- vec0 tables use the default sqlite-vec distance for `float[N]`, while scores are converted with `1.0 - distance` as if distance were bounded cosine distance (`memory/schema.py:226-236`, `embedding/search.py:99,261`). `[INFERENCE]` The score can be negative or incomparable with the documented cosine semantics unless the metric is made explicit.
- `retrieve_chunks()`, `merge_retrieve()`, `hybrid_search()`, and the Layer 4 gateway duplicate retrieval routing and return different schemas.

## Path C — build, status, stop, resume, and repair

### Observed build flow

1. The Settings panel starts `paperforge embed build --resume` or `--force` as a tracked child process (`paperforge/plugin/src/settings.ts:1230-1304`).
2. The plugin parses `EMBED_START`, `EMBED_PROGRESS`, and `EMBED_DONE` from stdout into in-memory `_embedProgress`.
3. Python preflight reads plugin settings and the canonical asset index, then selects OCR-complete papers (`paperforge/commands/embed.py:203-249`).
4. The build records `status=running`, progress, PID, model, and timestamps in the SQLite `build_state` table (`embed.py:328-340`; `embedding/build_state.py`).
5. A four-worker `ThreadPoolExecutor` encodes paper payloads (`embed.py:342-355,393-541`).
6. Completed payloads are committed to vec0/meta tables via `write_encoded_payload()`.
7. After all payloads for the paper are written, the build calls `delete_paper_vectors(vault, paper_id)` (`embed.py:375-379`).
8. `delete_paper_vectors()` selects every companion-meta row for that `paper_id`, deletes those vec0 rowids, and deletes the companion rows (`embedding/_chroma.py:65-85`).
9. Because the new rows use the same `paper_id`, step 8 deletes the rows written in step 6. The comment “Delete old vectors only after all new payloads are written safely” does not match the storage semantics.
10. Progress and `chunks_embedded` count attempted payloads, not rows remaining after deletion.

### Resume and force target the wrong store

- `get_vector_db_path()` returns `System/PaperForge/indexes/vectors`, the legacy Chroma directory (`embedding/_chroma.py:22-27`).
- Resume uses that directory as the “DB exists” gate (`commands/embed.py:294-304`).
- If the legacy Chroma directory is absent, `resume=False`.
- A user-requested `--resume` with `resume=False` sets `_force_rebuild=True` (`embed.py:314`).
- Force rebuild deletes only the legacy Chroma directory (`embed.py:315-326`). It does not clear vec0 virtual tables or companion metadata in `paperforge.db`.
- The subsequent build appends to vec0 and then deletes per-paper rows as described above.

Thus `--force` does not force-rebuild the active vector store, and `--resume` uses a legacy store to decide whether the active store is resumable.

### State split-brain

Current state is represented three times:

| Representation | Writer | Reader | Freshness |
|---|---|---|---|
| `_embedProcess` + `_embedProgress` | Plugin child-process events | Settings UI | Live only while the plugin owns the child |
| SQLite `build_state` | Python build/status/stop | Python CLI | Live persisted state |
| `vector-runtime-state.json.build_state` | `embed status`, build success, build failure | Plugin `getVectorRuntime()` | Snapshot; not updated on each paper |

The Settings UI defines running as:

```text
plugin owns a child process OR snapshot.build_state.status == "running"
```

(`settings.ts:1171-1182`). It does not query the live SQLite state. A stale JSON snapshot can therefore keep the progress bar and Stop button in a running state after the PID is dead.

`memory-state.ts` also still exposes a deprecated `vector-build-state.json` path, while Python stores build state in SQLite and the plugin never reads that legacy file.

### Stop semantics

- The plugin fires `embed stop --json` and immediately calls `child.kill()` if it owns the build child (`settings.ts:1210-1219`). It does not wait for the CLI stop result.
- `embed stop` reads SQLite state, calls `os.kill(pid, SIGTERM)`, and only afterward writes `status="stopping"` (`commands/embed.py:159-181`).
- The build process installs no SIGTERM handler and has no cooperative cancellation checks.
- If the PID is already dead, `os.kill()` raises and the command leaves the persisted state unchanged.
- If termination succeeds before the stop command writes its state, there is no build-finally path guaranteed to publish `completed`, `failed`, `cancelled`, or `idle`.

### Status/readiness drift

- `embed status` counts companion-meta rows; it does not verify that corresponding vec0 rows exist or execute a vector query (`embedding/status.py:13-60`).
- `embed status` reports `chromadb` as a required dependency even though live retrieval is direct sqlite-vec (`commands/embed.py:119-135`). A valid sqlite-vec runtime can therefore be marked dependency-incomplete.
- `isVectorReady()` and `buildSnapshot()` require `chunk_count > 0`, which means `vec_fulltext_meta`; a body/object-only index with nonzero `total_chunks` is marked not ready (`plugin/src/services/memory-state.ts:184-192,288-294`).
- `getVectorStatusText()` and the Settings count use the sum of fulltext/body/object counts, so different UI helpers disagree about readiness.
- `_assert_collections_healthy()` checks companion-table counts, not vec0 queryability (`commands/embed.py:85-103`).

### Dimension and schema drift

- `detect_embedding_dim()` caches one dimension globally for the Python process, not by vault, model, or provider (`embedding/dim_detect.py:13-30`).
- `ensure_vec_tables()` detects only `vec_body` DDL, drops the three vec0 virtual tables on mismatch, but leaves all companion-meta rows in place (`dim_detect.py:45-70`).
- Recreated vec0 rowids can therefore disagree with stale companion rowids.
- The schema defaults to 1536 dimensions, while runtime probing may recreate tables for another model (`memory/schema.py:226-236`). There is no durable schema contract tying a vec0 generation to provider, model, dimension, or companion metadata generation.

## Active versus legacy architecture

### Active production path

- Metadata source and FTS: `paperforge.db`, `papers`, `paper_fts`, `body_units_fts`.
- Vector storage and query: direct sqlite-vec vec0 tables inside `paperforge.db`.
- Embedding provider: `OpenAICompatibleProvider`, optionally delegating to the requests fallback.
- Build lifecycle: Python CLI plus SQLite `build_state`.
- Plugin presentation: compiled Obsidian bundle plus JSON runtime snapshots.

### Legacy or disconnected path

- `get_vector_backend()` returns `ChromaBackend`, but the refreshed code graph found only its test caller.
- `ChromaBackend` and `VectorBackend` are not used by production retrieval, status, or build paths.
- `LanceBackend` is not wired into the factory and is test/evaluation code only.
- `migrate_chroma_to_vec0()`, dual-backend deletion, Chroma dependency reporting, and the `indexes/vectors` directory keep Chroma in production control flow.
- `get_vector_build_state_path()` and plugin `buildStatePath` describe a JSON state file no longer used as the persisted build-state store.

The migration is therefore neither a clean direct-sqlite cutover nor a completed backend-abstraction migration.

## Source/deployed artifact observation

The repository plugin bundle and the Literature-hub deployed bundle did not match at evidence time:

```text
repository paperforge/plugin/main.js
3b118eb268430c4d50114ab65ac21ba17831e972fff8a35357b70965c50b0d82

Literature-hub .obsidian/plugins/paperforge/main.js
439f94d75c93782a062e8d8402b4f62946c9ce8b8b53be105006ab995fad2b77
```

Both bundles contain the sql.js error marker, progress parsing, `matched_text`, and JSON snapshot path. The exact behavioral delta remains assigned to [Audit source-to-vault deployment parity](https://github.com/LLLin000/PaperForge/issues/47); this ticket only establishes that source and deployed artifacts are not identical.

## Contract-drift ledger

| Severity | Contract | Observed drift | Evidence | Downstream decision |
|---|---|---|---|---|
| P0 | sql.js metadata search is the fast path | Query selects nonexistent `paper_fts.year`; initialization fails | `plugin/src/services/db.ts:81-87`; read-only production DB probe | Query ownership and whether sql.js remains |
| P0 | `@` means deep hybrid search | UI calls `retrieve` without `--deep`, so hybrid search is not selected | `dashboard.ts:2437-2523`; `commands/retrieve.py:46-51` | Unified command/query contract |
| P0 | Retrieve results render in the plugin | CLI returns `data.chunks`; plugin accepts only `matches/results` | `commands/retrieve.py:170-178`; `dashboard.ts:2556-2573` | One result envelope/schema |
| P0 | New vectors replace old vectors safely | Build writes new rows then deletes every row for the paper | `commands/embed.py:375-379`; `_chroma.py:65-85` | Atomic per-paper replacement |
| P1 | `--force` rebuilds the active index | It deletes the legacy Chroma directory, not vec0/meta tables | `commands/embed.py:314-326`; `_chroma.py:22-27` | Repair/rebuild policy |
| P1 | `--resume` detects active-index state | It uses the legacy Chroma directory as the existence gate | `commands/embed.py:294-304` | Resume checkpoint contract |
| P1 | Stop terminates and settles the job | UI double-signals; CLI writes stopping after kill; no cooperative cancellation/final state | `settings.ts:1210-1219`; `commands/embed.py:159-181` | Build lifecycle state machine |
| P1 | Plugin progress reflects persisted truth | UI reads JSON snapshot while SQLite owns live state | `settings.ts:1161-1182`; `build_state.py`; `state_snapshot.py` | Single control-plane truth source |
| P1 | Status establishes vector readiness | Status counts meta rows and readiness checks only fulltext count | `embedding/status.py`; `memory-state.ts:184-192` | Health/readiness invariants |
| P1 | sqlite-vec replaced ChromaDB | Chroma factory, migration, deletion, dependency checks, and path gates remain | `embedding/backends`; `_chroma.py`; `commands/embed.py` | Clean cutover versus real backend adapter |
| P1 | Dimension change safely recreates artifacts | vec tables are dropped while meta rows survive; cache is process-global | `embedding/dim_detect.py` | Generation/model identity policy |
| P2 | Explicit CLI deep search degrades to BM25 | Provider failure occurs before vec-query fallback | `embedding/search.py:231-258` | Provider failure semantics |
| P2 | Explicit CLI deep search includes object vectors | Object rows are normally omitted when BM25 has any rows | `embedding/search.py:284-352` | Fusion/result-source contract |
| P2 | Search card fields are stable | Python/sql.js emit `first_author` and `text`; UI expects `authors` and `matched_text` | `commands/search.py`; `embedding/search.py`; `dashboard.ts` | Shared result type |
| P2 | Tests prove shipped user paths | Tests stop at direct functions or mock write/delete boundaries | test files below | Acceptance topology |
| P2 | Tracker/spec state reflects runtime | Completed migration/search claims coexist with obsolete open Chroma/provider issues | named issues below | Issue reconciliation after architecture choice |

## Test topology and false confidence

### Tests that cover useful internals

- `tests/test_deep_search.py` covers query rewrite, BM25, vec0, and score fusion as direct Python functions.
- `tests/test_e2e_embed_retrieve.py` directly writes deterministic 1536-dimensional payloads and calls `merge_retrieve()`.
- `tests/test_embed_integration.py` covers direct encode/write/retrieve/delete functions.
- `tests/unit/memory/test_vector_db.py` covers SQLite build-state CRUD.
- `tests/test_chroma_migration.py` covers the one-shot Chroma-to-vec0 copy and dual deletion.

### Missing shipped-path coverage

- No test drives `@` from plugin input through CLI arguments, PFResult parsing, and card rendering.
- No test verifies the sql.js query against the actual Python-owned schema.
- No plugin test covers metadata/deep search rendering.
- The embed/retrieve E2E helper calls `write_encoded_payload()` directly; it does not execute `paperforge embed build`.
- `tests/test_pr9c_streaming_embed.py` mocks `write_encoded_payload()` and `delete_paper_vectors()` independently and asserts call counts, not call order or persisted rows. It therefore passes while the production loop deletes newly written rows.
- No test covers stop against a real build process, dead PID settlement, stale JSON snapshot behavior, concurrent starts, or plugin restart during build.
- Backend abstraction tests exercise `ChromaBackend`, which has no production caller.

## Specification and tracker drift

- [PRD: Replace ChromaDB with sqlite-vec for vector storage](https://github.com/LLLin000/PaperForge/issues/25) is closed as completed, but legacy Chroma paths still decide resume, force, dependencies, and deletion.
- [PRD: V2 Search + Rebuild UX](https://github.com/LLLin000/PaperForge/issues/34) is closed as completed, but its `@` path is not selected and its result contract does not render.
- [PRD: E2E tests for OCR → embed → retrieve pipeline](https://github.com/LLLin000/PaperForge/issues/24) is closed, but current E2E coverage bypasses the CLI build and plugin contracts.
- [PRD: Switch embedding provider from requests to openai SDK](https://github.com/LLLin000/PaperForge/issues/23) remains open even though `OpenAICompatibleProvider` currently uses the OpenAI SDK with a configured requests fallback.
- [Health check doesn't validate ChromaDB index](https://github.com/LLLin000/PaperForge/issues/14) remains open even though live retrieval bypasses `ChromaBackend`.
- `docs/prd-v2-search-rebuild-ux.md` describes two user modes and originally excludes sql.js/real-time search; `docs/prd-v3-search-performance.md` later adds sql.js, creating three execution arms without one shared query/result contract.
- The Layer 4 backend protocol was introduced, but direct vec0 access bypasses it in build, status, and retrieval.

## Inputs to the remaining Wayfinder decisions

### [Choose the canonical retrieval architecture and ownership boundary](https://github.com/LLLin000/PaperForge/issues/46)

Must decide between:

- a direct sqlite-vec architecture with dead Chroma/Lance abstraction removed, or
- a real backend boundary with a `Vec0Backend` used by build, query, status, and tests.

It must also decide whether metadata FTS runs only through Python or whether sql.js retains a deliberately versioned read contract.

### [Specify the retrieval build lifecycle and crash recovery semantics](https://github.com/LLLin000/PaperForge/issues/52)

Must define:

- one persisted truth source;
- process ownership and single-writer acquisition;
- cooperative cancellation;
- terminal states;
- per-paper atomic replacement;
- resume checkpoints independent of Chroma paths;
- plugin restart and stale-process behavior.

### [Specify metadata and deep-search contracts](https://github.com/LLLin000/PaperForge/issues/54)

Must define one typed result envelope, one deep-mode selector, stable field names, navigation identity, error/fallback behavior, and score semantics.

### [Define safe repair, rebuild, and model-change policy](https://github.com/LLLin000/PaperForge/issues/51)

Must define complete Retrieval Artifact generations: vec tables, companion rows, FTS indexes, model, dimension, policy version, and checkpoints must be cleared or promoted together.

### [Prototype retrieval panel states and recovery flows](https://github.com/LLLin000/PaperForge/issues/48)

Must not prototype against the current JSON-snapshot-plus-child-process union. It should consume the lifecycle and query contracts decided by the preceding tickets.

### [Define the retrieval acceptance matrix and release gate](https://github.com/LLLin000/PaperForge/issues/50)

Must include the real plugin→CLI→database boundary, not only direct Python functions.

## Map effect

This audit does not add a new ticket. Every confirmed drift belongs to an existing child:

- backend and ownership drift → canonical architecture;
- state/process drift → build lifecycle;
- metadata/deep schema drift → query contracts;
- generation/dimension drift → repair policy;
- user-visible state drift → UI prototype;
- test seams → acceptance matrix.

The map’s existing fog remains fog:

- provider retry/cost budgets still depend on the canonical backend and lifecycle;
- performance budgets need the non-destructive failure matrix baseline;
- ranking work remains conditional on minimum-relevance acceptance results;
- release rollout waits for deployment-parity and recovery decisions.

## Evidence index

### Frontend

- `paperforge/plugin/src/views/dashboard.ts:2370-2749`
- `paperforge/plugin/src/services/db.ts:1-119`
- `paperforge/plugin/src/settings.ts:493-525,1145-1357`
- `paperforge/plugin/src/services/memory-state.ts:117-215,272-317`
- `paperforge/plugin/src/main.ts:86-136`

### Python commands and retrieval

- `paperforge/commands/search.py:14-120`
- `paperforge/commands/retrieve.py:42-178`
- `paperforge/commands/embed.py:70-103,111-200,203-642`
- `paperforge/embedding/search.py:29-356`
- `paperforge/embedding/builder.py:137-224,227-318`
- `paperforge/embedding/build_state.py:12-160`
- `paperforge/embedding/status.py:13-60`
- `paperforge/embedding/dim_detect.py:13-70`
- `paperforge/embedding/_chroma.py:22-183`
- `paperforge/embedding/providers/openai_compatible.py:14-46`
- `paperforge/memory/schema.py:17-123,178-236,238-369`
- `paperforge/memory/state_snapshot.py:37-66`

### Tests

- `tests/test_deep_search.py`
- `tests/test_e2e_embed_retrieve.py`
- `tests/test_embed_integration.py`
- `tests/test_pr9c_streaming_embed.py:149-316`
- `tests/test_chroma_migration.py`
- `tests/unit/memory/test_vector_db.py`
- `paperforge/plugin/tests/`
