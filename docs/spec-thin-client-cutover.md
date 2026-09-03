# Specification: Thin Client Cutover & PaperForgeClient Consolidation

## Problem Statement

Currently, the PaperForge Obsidian plugin directly accesses subprocess creation (`child_process.spawn`), manages ad-hoc command strings, duplicates process control state, and attempts to infer business health and action availability within UI views. This creates three critical failures:
1. **State and Policy Drift**: Frontend views independently guess whether a feature is broken or whether a button should be enabled, frequently drifting from Python backend authority.
2. **Process and Invalidation Flaws**: Subprocess management is scattered across multiple controllers (`LongTaskClient`, `ActionClient`, `ConfigClient`), risking stale cache resurrection, inconsistent cancellation, and untracked child processes.
3. **Host Lock-in**: Business views are coupled directly to Node.js APIs and Obsidian desktop internals, making it impossible to adapt PaperForge to a web-based standalone UI (DSH UI), CLI agents, or automated headless harnesses without rewriting presentation logic.

## Solution

Consolidate all process invocation, streaming, caching, and concurrency control into an isomorphic TypeScript client (`PaperForgeClient`) situated on top of an abstract `Transport` seam.

The Python backend remains the sole authority for system state (`probe`), deficit derivation (`reconcile`), action policy (`action registry`), and execution mode (`result` vs `stream`). Business UI views interact only with high-level, typed methods on `PaperForgeClient`. In Node.js (Obsidian), `NodeProcessTransport` manages process lifecycle, environment sanitization, and cooperative cancellation; for testing or alternative environments, `MockTransport` or remote transports are plugged in without modifying UI presentation code.

## User Stories

1. As a researcher, I want the Obsidian dashboard to load instantly from memory cache during routine navigation, so that switching tabs feels native and responsive without latency spikes.
2. As a researcher, I want the dashboard to immediately invalidate cached probe data when a maintenance or rebuild action completes, so that I never see stale status indicators after a repair.
3. As a researcher, I want in-flight status requests for the same module to be merged, so that opening multiple views at once does not spawn redundant Python processes in the background.
4. As a researcher, I want mutations (rebuilds, syncs, setups) to never be deduplicated or skipped, so that every explicit user action executes deterministically.
5. As a researcher, I want stale background reads that complete after a mutation to be safely discarded, so that an outdated read never resurrects an expired status badge.
6. As a researcher, I want the UI to disable all conflicting long-running tasks while an operation is active, so that my local database does not experience lock contention or corruption.
7. As a researcher, I want to see a running indicator when another external process is running OCR, but only see an active "Stop" control when this plugin owns the process handle, so that I cannot trigger unauthorized or broken process signals.
8. As a researcher, I want the Stop button to cooperatively terminate long-running tasks within a grace window before escalating to process-tree termination, so that partial disk writes are safely avoided.
9. As a researcher, I want any long-running operation that fails, cancels, or encounters EOF to release the client operation lock immediately, so that subsequent tasks are not permanently blocked.
10. As a researcher, I want all action buttons to derive their labels, availability, and confirmation prompts directly from backend action descriptors, so that plugin actions always match backend capabilities.
11. As a developer, I want the client core to depend only on an abstract `Transport` interface without Node.js globals, so that PaperForge can run in browser-based standalone UIs and headless test environments.
12. As a developer, I want all backend subprocesses to execute with a sanitized environment that strips ambient API keys, so that credentials remain protected inside the system keyring.
13. As a developer, I want sensitive inputs (such as API keys during initial configuration) to pass strictly via stdin streams, so that credentials never leak into process command arguments or system logs.
14. As a developer, I want every executable surface to explicitly declare whether it emits single JSON results or NDJSON event streams, so that TypeScript client code never relies on hardcoded command dictionaries.
15. As a developer, I want all legacy ad-hoc spawn calls and direct canonical file inspections in UI code to be deleted after cutover, so that the codebase enforces clean architectural boundaries.

## Implementation Decisions

### 1. Transport Seam & Process Consolidation
- The client architecture is split into `PaperForgeClient` (isomorphic business client) and `Transport` (execution adapter).
- The `Transport` interface defines two primitives:
  - `execute(cmd: string, args: string[], options?: ExecuteOptions): Promise<string>`
  - `stream(cmd: string, args: string[], options?: StreamOptions): AsyncIterable<NDJSONEvent>`
- `NodeProcessTransport` consolidates the existing logic from `LongTaskClient`, `ActionClient`, and `ManagedRuntime`:
  - Locates the canonical interpreter via `~/.paperforge/runtime/active-runtime.json`.
  - Uses `paperforgeEnrichedEnv()` to sanitize the process environment, preventing ambient secret leaks.
  - Submits credentials via stdin exclusively (`auth set <kind> --stdin`).
  - Implements the proven cancellation protocol: stdin `PAPERFORGE_STOP\n` $\rightarrow$ grace timeout $\rightarrow$ Windows `taskkill /T /F` or POSIX `SIGKILL` on the process group.

### 2. Generation-Aware Cache & Request Deduplication
- Probe requests (`probe *`, detail queries, search) are cached in-memory with TTLs derived from backend `ttl_seconds`.
- Concurrent in-flight reads for identical keys share a single promise.
- Every read request captures the client's current `epoch: number`.
- When any mutation (`runAction`, `setup`, `sync`, `promoteR`, `acceptProposal`) completes, the client increments `epoch` and purges cached responses.
- When an in-flight read finishes, it commits its result to cache only if `readEpoch === currentEpoch`, completely eliminating stale cache resurrection.
- Mutation calls bypass deduplication and always execute directly.

### 3. Operation Lock Semantics
- `OperationLock` manages client execution ownership, not global backend state.
- When a long-running streaming operation starts, `OperationLock` records the active child handle and locks the client.
- The lock releases deterministically on any terminal event: `result`, `error`, `cancelled`, spawn error, stream parse failure, or stream EOF.
- The UI checks `client.isOperationActive()` to govern local cancellation controls. Global activity ("running") is derived strictly from `probe.activity_state`.

### 4. Machine Contract & DTO Normalization
- The Python backend explicitly declares execution mode on all actions:
  `execution_mode: "result" | "stream"`
- `PaperForgeClient` routes dispatch based on this descriptor field, eliminating TypeScript-side command name heuristics.
- Action IDs strictly adhere to canonical registry identifiers (`memory.build`, `memory.rebuild`, `embed.build`, `embed.resume`, etc.).

### 5. Expand–Contract Migration Sequence
- Phase 1 (Expand): Introduce `PaperForgeClient` alongside existing clients.
- Phase 2 (Cutover): Migrate product domains one by one (Foundation $\rightarrow$ Maintenance $\rightarrow$ OCR Workspace $\rightarrow$ Retrieval $\rightarrow$ Library/Render Quality).
- Phase 3 (Contract): In a dedicated final ticket, physically delete legacy bridges, ad-hoc spawn calls, and obsolete controllers.

## Testing Decisions

- **Testing Principles**: Tests must verify observable behavior across client seams, not internal variable states.
- **Primary Seam**: `PaperForgeClient` tested against `MockTransport`.
  - Tests simulate high-concurrency probe reads, verifying single execution via dedup.
  - Tests simulate mutation-during-read races, asserting that late-arriving reads from prior generations never populate the cache.
  - Tests verify that `runAction`, `setup`, and `sync` never deduplicate calls.
  - Tests verify that `OperationLock` acquires during active streams and reliably releases on all failure/terminal states.
- **Transport Seam**: `NodeProcessTransport` tested against mock processes and cancellation signals.
  - Verifies stdin `PAPERFORGE_STOP` injection, grace period escalation, and sanitized environment creation.
- **Prior Art**: Existing unit test suites in `tests/` (Python) and `paperforge/plugin/tests/` (Vitest) provide fixtures for probe envelopes and #137 NDJSON streams.

## Out of Scope

- Implementing standalone web or DSH UI components (this spec provides the client boundary, not the alternate host implementations).
- Adding new OCR layout heuristics or expanding the Reconcile detector set (governed by `docs/RECONCILE-EXTENSION-CONTRACT.md`).
- Altering the backend SQLite database schema or changing the canonical filesystem hierarchy inside the vault.

## Further Notes

- All changes maintain compatibility with Obsidian desktop 1.11.4+.
- This cutover resolves technical debt identified in architectural audits while laying the groundwork for multi-frontend extensibility.
