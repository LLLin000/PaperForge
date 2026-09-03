# ADR 0003: PaperForgeClient Architecture and Transport Seam

- **Status:** ACCEPTED
- **Deciders:** User, Assistant
- **Date:** 2026-09-02
- **Supersedes:**
  - `docs/design-thin-client-boundaries.md` §3 (cache policy: replaces no-TTL full wipe with generation-aware TTL + in-flight read deduplication + mutation invalidation)
  - `docs/design-thin-client-boundaries.md` §5 (process-controller ownership: consolidates separate process shells behind `Transport` and `OperationLock`)
- **Preserves Invariants:**
  - `docs/design-thin-client-boundaries.md` §0 (Core invariant: Python owns all semantics, read models, and action authority; client never infers meaning from files or raw process state)
  - `docs/design-thin-client-boundaries.md` §1 (Typed public client: no public `query<T>(cmd, args)` string commands; business callers only consume typed domain methods)
  - `docs/design-thin-client-boundaries.md` §2 (Allowed vs prohibited reads: UI never directly reads canonical files)
  - `docs/design-thin-client-boundaries.md` §4 (Running display ≠ process control: backend running truth is probe-owned; local Stop ownership requires child process handle)

## Context

The Obsidian frontend previously mixed direct `child_process.spawn` calls, command string construction, raw stdout parsing, and ad-hoc status inference throughout multiple view classes (`settings.ts`, `modals.ts`, `ocr-workspace.ts`). Existing process-handling code was split between `LongTaskClient`, `ActionClient`, `ConfigClient`, and `ManagedRuntime`. To enable clean portability to external frontends (such as a standalone web-based DSH UI or CLI agents), the presentation layer must be decoupled from process execution transport, and existing process plumbing must be consolidated into a unified client.

## Decisions

### 1. Transport Adapter Seam (Consolidated Subprocess Stack)
Rather than building a second subprocess stack, `PaperForgeClient` consolidates existing process utilities (`LongTaskClient`, `ActionClient`, `ManagedRuntime`) behind a unified `Transport` seam:
- It communicates through a minimal `Transport` interface:
  ```typescript
  export interface Transport {
    execute(cmd: string, args: string[], options?: ExecuteOptions): Promise<string>;
    stream(cmd: string, args: string[], options?: StreamOptions): AsyncIterable<NDJSONEvent>;
  }
  ```
- Obsidian provides `NodeProcessTransport`:
  - Resolves the active Python interpreter via `ManagedRuntime` (`~/.paperforge/runtime/active-runtime.json`), never ambient `python`.
  - Runs with a **sanitized subprocess environment** (`paperforgeEnrichedEnv()`): never inherits ambient secret environment variables; credentials stay inside the Python keyring authority.
  - Submits sensitive inputs (like API keys during setup) via **stdin-only submission** (`auth set <kind> --stdin`), never CLI arguments or environment variables.
  - Handles process lifecycle using existing proven patterns: `PAPERFORGE_STOP` over stdin, grace period, Windows `taskkill /T /F`, and POSIX process-group kill.
- Future standalone UIs (DSH) or test suites provide alternative transports (WebSocket, local HTTP daemon, or in-memory `MockTransport`) without modifying domain methods.

### 2. Generation-Aware In-Memory Cache with In-Flight Deduplication
To eliminate UI stutter and avoid repeatedly launching Python processes while ensuring "stale is never ready":
- **TTL Gating**: `PaperForgeClient` caches probe responses in memory according to each module's backend-specified TTL (`ttl_seconds`).
- **In-Flight Deduplication Policy**:
  - `probe`, `query`, `search`, and `detail` requests: **YES** — concurrent calls for the same resource share a single in-flight promise.
  - `runAction`, `setup`, `sync`, `promoteR`, `acceptProposal`: **NEVER** — mutations are never deduplicated.
- **Generation / Epoch Invalidation (Anti-Resurrection Guard)**:
  To prevent stale reads from resurrecting outdated cache entries across a mutation boundary:
  ```text
  read A starts at generation = 5
          ↓
  mutation B commits
          ↓
  generation → 6 (cache invalidated)
          ↓
  old read A returns
          ↓
  MUST NOT repopulate generation-6 cache
  ```
  Every cache entry and in-flight read is tagged with a client-level `epoch: number`. A read result is committed to the cache if and only if `currentEpoch === readEpoch`. Any completed mutation increments `epoch` and purges the memory cache.

### 3. Operation Lock as Execution Ownership (Not State Authority)
- **Scope of Lock**: Answers *"Does this PaperForgeClient instance own an active mutual-exclusion long task?"* It does **NOT** answer *"Is PaperForge running in the background?"*
  ```text
  Backend running truth → probe / Python authority
  Local Stop button ownership → Operation Lock holding active child handle
  ```
  If an external terminal runs OCR, `probe` returns `activity_state = "running"`, but `client.isOperationActive()` is `false`. The UI renders "Running" but disables the "Stop" button.
- **Release Conditions**: The lock must release deterministically on **all** terminal outcomes:
  `result` terminal, `error` terminal, `cancelled` terminal, spawn failure, protocol decode error, or unexpected EOF.

### 4. Machine Contract Binding (Python-Owned Mode)
- Every executable action descriptor emitted by the backend explicitly declares:
  `execution_mode = "result" | "stream"`
- `PaperForgeClient` routes to `execute` or `stream` based on the backend descriptor's `execution_mode`, never by hardcoding action ID tables in TypeScript.
- Action IDs strictly follow the Python registry (`memory.build`, `memory.rebuild`, `embed.build`, `embed.resume`, etc.); client code never invents synthetic action names.

### 5. Progressive Domain Cutover (Expand–Contract)
Migration follows a strict 7-ticket sequence:
1. T1: Client Core + Transport Consolidation + MockTransport tests
2. T2: Python Surface Audit + Machine Mode DTO Normalization
3. T3: Domain A (Foundation) & Domain E (Maintenance) cutover
4. T4: Domain C (OCR Workspace) cutover
5. T5: Domain D (Retrieval & Knowledge) cutover
6. T6: Domain B (Library) & Domain F (Render Quality) cutover
7. T7: Legacy bridge/spawn deletion + architecture enforcement (pure contract ticket)
