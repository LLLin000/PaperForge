# Thin Obsidian and Agent Client Boundaries

> Date: 2026-08-09
> Status: **ACCEPTED — ARCHITECTURE FROZEN** (decision [#144](https://github.com/LLLin000/PaperForge/issues/144))
> Related: [#145](https://github.com/LLLin000/PaperForge/issues/145) action contract, [#137](https://github.com/LLLin000/PaperForge/issues/137) progress protocol, [#140](https://github.com/LLLin000/PaperForge/issues/140) read models, [#143](https://github.com/LLLin000/PaperForge/issues/143) bootstrap, [#157](https://github.com/LLLin000/PaperForge/issues/157) cache research, [#158](https://github.com/LLLin000/PaperForge/issues/158) sync trigger
> Input to: [#149](https://github.com/LLLin000/PaperForge/issues/149) (collector exemptions)

## 0. Core invariant (for the ArchitectureContract)

> **The client may know what the user is looking at and what Python told it; it may not infer what PaperForge means from files, paths, process state, or cached data.**

```text
                  PYTHON
        semantic / read / action authority
              ↑                ↓
         JSON / NDJSON     paths / keys
              ↑                ↓
         PaperForgeClient
        typed transport only
              ↓
   ┌──────────┼──────────┐
   │          │          │
Dashboard  Settings  Workspace
 render     inputs   selection
 only       only      only
```

## 1. PaperForgeClient surface — typed public, generic transport private

No public `query<T>(cmd, args)`: a generic string-command query would grow an implicit TS command map and re-create the exact authority #140 rejected on the Python side.

```ts
interface PaperForgeClient {
  probe(module: ProbeModule): Promise<ProbeEnvelope>;
  probeAll(): Promise<ProbeAllResult>;

  queryOcrPapers(request: OcrPaperQuery): Promise<OcrPaperRows>;   // typed detail methods
  queryMemoryDetail(request: MemoryDetailQuery): Promise<MemoryDetail>;
  paperContext(request: PaperContextQuery): Promise<PaperContext>;

  describeAction(request: ActionRequest): Promise<ActionDescriptor>;
  runAction(request: ActionRequest, options?: RunActionOptions): Promise<PFResult>;

  configGet(...): Promise<...>;
  configSet(...): Promise<...>;
  authStatus(...): Promise<...>;
  authSet(...): Promise<...>;

  // private
  // invokeJson(...) / invokeStream(...) — generic transport, never exposed to business callers
}
```

Business callers cannot pass arbitrary command strings; only typed methods exist. Detail method names map one-to-one to Python's dedicated detail commands; no client-side command table.

## 2. Allowed and prohibited reads

### Allowed

```text
Obsidian active file / selection / workspace leaf        (Obsidian API)
data.json — UI preferences
data.json — last-known display cache (per §3)
~/.paperforge/runtime/pointer.json — READ, bootstrap adapter only (#143)
Python-returned paths — display / open / edit only
```

### Prohibited (semantic reads)

```text
formal-library.json
paperforge.json
OCR meta / result hash / structured blocks / role index
memory database
runtime snapshots / maintenance snapshots
any other canonical PaperForge fact
```

Semantic reads come only from CLI responses (#140, #157). The plugin's UI business code contains no canonical-file `fs.existsSync` / `JSON.parse`.

## 3. Last-known cache — dumb invalidation, no dependency map

Adopts #157, with one simplification: **the client never computes which modules a mutation affects.**

- Per-module persisted last-known: one display-only CLI response per probe module (all six: installation, library, ocr, memory, help, maintenance) in `data.json`, stamped with plugin `received_at`.
- Detail sets (query results): **in-memory only**, never persisted.
- Render last-known immediately; re-probe on demand.
- **On any completed mutation:** clear all six persisted last-known envelopes + all in-memory detail sets, then `probeAll()`. One call: `invalidateAllReadModels()`.
- No TTLs, SWR/SFE windows, revision-token maps, affected-module tables, or dependency reasoning in TS. (If Python later emits a canonical `invalidated_modules` field in PFResult, the client may honor it; until then, full clear is the contract.)

## 4. Stale / error / running UI rules

- `stale` → render last-known + stale marker; actions disabled.
- `probe error` → render last-known + error; actions disabled.
- `running` → render #137 stream events.

Actions stay disabled until a fresh response newer than the last mutation arrives. No additional state machine.

**Running display ≠ process control.** A fresh probe reporting `running` does not mean this plugin owns the process. Only a controller holding the child handle may show a Stop control; otherwise the UI only displays "Running". Views never re-derive `activity_state` / `isRunning`; controllers are the only owners (#157).

## 5. Controller responsibilities — process mechanics only

`OcrProcessController` / `EmbedBuildController` keep their shells:

```text
spawn · stream parse · render callback · stdin stop (PAPERFORGE_STOP) ·
grace timeout · hard escalation (taskkill /T /F) · duplicate-start suppression ·
terminal capture
```

Deleted:

```text
which action should run · argv maps · confirmation policy · remote/local policy ·
follow-up policy · repair sequencing · semantic success classification
```

Controller = process mechanics; Python = job semantics (#137, #145).

## 6. UI context vs canonical identity

**Client owns UI context; Python owns canonical identity resolution.**

- Plugin may directly pass a key as action scope **only when the key came from a Python response** (e.g., an OCR Workspace row's `key`, user-selected → `papers [key]`).
- Active-file scope: Obsidian gives the vault path → `PaperForgeClient.resolveContext(path)` (or the existing `paper-context` typed query) → Python returns `{paper_key: ...}`. The plugin never derives a canonical key from frontmatter, filename, or library lookup.

## 7. Migration mapping (behavior-preserving)

```text
READ      old canonical/snapshot reads          → probe / typed query
ACTION    old CLI argv / TS command maps        → action run
CHAIN     old _runIndexRefreshChain             → action run --follow auto
SETTINGS  paperforge.json parsing/writing       → config get / set
CREDENTIALS                                    → auth set / status / delete
```

Constraint: `--follow auto` is behavior **inside a single Python invocation**. The plugin never loops `result.next_actions`; it consumes only the terminal PFResult and pending confirmation descriptors (#145, #159).

## 8. Agent client

Command set (CLI JSON/NDJSON only):

```text
probe · probe all · dedicated detail commands · action list · action describe ·
action run · config · auth
```

- No MCP server, HTTP API, daemon, or Agent adapter service.
- Confirmation is two-step: `describe` / `confirmation_required` → explicit `run --confirm <exact action>` (#145).
- A future MCP surface is only a transport adapter over this contract; it never re-designs semantics.

## 9. Collector exemptions for #149 — by adapter/helper, not by primitive

Exemptions are scoped to **known wrapper + operation**, never to primitives:

```text
ALLOW  plugin/cache-adapter      → data.json ui_prefs / last_known read+write only
ALLOW  bootstrap-adapter         → ~/.paperforge/runtime/pointer.json READ only
ALLOW  navigation-helper         → openReturnedPath(...) — Python-returned path open/display only
ALLOW  workspace-adapter         → active file / selection / leaf (Obsidian API)
```

Rules:

- Collectors check `source path + sink + known wrapper`, not API names alone (`JSON.parse(formal-library.json)` and `JSON.parse(data.json)` are architecturally different).
- `fs.existsSync` is not blanket-banned: opening a Python-returned external PDF may check existence (navigation failure handling) — but the exists result **must never feed capability/action classification**. It is centralized in one `openReturnedPath(...)` helper, and the collector exempts that helper only.
- Everything outside the four allowlisted wrappers that touches canonical sources is flagged.

## 10. Deletion list (feed into T8)

`ALLOWED_ACTIONS`, `isAutomaticLocal`/`requiresConfirmation`, `(verb,command)` dispatch, `_runIndexRefreshChain`, command fields in `ActionPrimary`/dashboard constants, `memory-state.ts` semantic logic, mtime scanner, canonical-file reads in UI code — deleted, not shadowed (plan §11, #137, #143).
