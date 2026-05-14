# Memory Runtime Health Design

> **Date:** 2026-05-15

## Goal

Make the PaperForge memory layer trustworthy for agents while keeping user-facing UX low-noise.
The dashboard should expose only a compact `System Status`, while agents consume a single machine-readable runtime contract that answers:

1. Can I safely read now?
2. Can I safely write now?
3. Can I safely build or repair now?

This design also closes the vector build UX loop: background execution, incremental persistence, resumable progress, and explicit repair actions.

## Problem Statement

Current behavior is spread across multiple partial truth sources:

- `pf_bootstrap.py` reports basic availability and guessed vector state.
- `memory status`, `embed status`, and plugin UI each derive their own status.
- `reading-log`, `paper-context`, SQLite rebuilds, and vector index each have different failure surfaces.
- The plugin UI currently holds transient build state in memory, so re-render/reload can hide or distort the real state.

This creates the exact failure mode the user reported: things feel like they can break anywhere, and agents cannot rely on one authoritative contract.

## Design Principles

1. **One runtime contract**: all agent and plugin health views derive from one CLI command.
2. **Thin UI**: Dashboard `System Status` displays summarized runtime state; it does not invent logic.
3. **Explicit repair**: health checks diagnose and recommend commands, but do not auto-mutate state.
4. **Persistent job state**: vector build status survives plugin re-render, settings close, and Obsidian restart.
5. **Agent-first semantics**: primary consumer is the `paperforge` skill and its workflows, not end-user settings UI.

## New Contract: `paperforge runtime-health --json`

Add a new top-level CLI command:

```bash
paperforge runtime-health --json
```

It returns a PFResult envelope whose `data` field contains:

```json
{
  "summary": {
    "status": "ok|degraded|blocked",
    "reason": "human-readable one-line summary",
    "safe_read": true,
    "safe_write": true,
    "safe_build": true,
    "safe_vector": true
  },
  "layers": {
    "bootstrap": {
      "status": "ok|degraded|blocked",
      "evidence": [],
      "next_action": "...",
      "repair_command": "..."
    },
    "read": {
      "status": "ok|degraded|blocked",
      "evidence": [],
      "next_action": "...",
      "repair_command": "..."
    },
    "write": {
      "status": "ok|degraded|blocked",
      "evidence": [],
      "next_action": "...",
      "repair_command": "..."
    },
    "index": {
      "status": "ok|degraded|blocked",
      "evidence": [],
      "next_action": "...",
      "repair_command": "..."
    },
    "vector": {
      "status": "ok|degraded|blocked",
      "evidence": [],
      "next_action": "...",
      "repair_command": "...",
      "job": {
        "status": "idle|running|stopping|failed|completed",
        "current": 0,
        "total": 0,
        "paper_id": "",
        "last_update": "...",
        "resume_supported": true
      }
    }
  },
  "capabilities": {
    "paper_context": true,
    "reading_log_write": true,
    "project_log_write": true,
    "fts_search": true,
    "vector_retrieve": false
  }
}
```

## Layer Semantics

### 1. `bootstrap`

Checks:

- `paperforge.json` exists and is readable
- path resolution succeeds
- python candidate exists
- `python_verified` semantics remain accurate

Blocked examples:

- no `paperforge.json`
- no usable Python

### 2. `read`

Checks whether agent read workflows can safely run:

- canonical index exists
- memory DB exists or is rebuildable
- `paper-context` can resolve a paper without crashing
- JSONL source files are readable

This layer powers `paper-search`, `paper-qa`, and `deep-reading` preflight.

### 3. `write`

Checks whether agent write workflows can safely persist traces:

- `reading-log.jsonl`, `project-log.jsonl`, `correction-log.jsonl` parent directories writable
- append/read roundtrip contract intact
- no split-truth write path still active

This layer powers `reading-log`, `project-log`, and correction creation.

### 4. `index`

Checks consistency of derived SQLite index:

- schema version current
- tables present
- rebuild path available
- FTS usable
- JSONL -> DB import contract usable

This layer is allowed to be degraded while read/write still remain safe.

### 5. `vector`

Checks semantic retrieval pipeline:

- feature toggle on/off
- deps available
- ChromaDB state readable
- current model known
- active build job status readable
- retrieve safe or blocked

This layer is explicitly separate from core read/write health.

## Status Derivation Rules

Top-level `summary.status` is derived conservatively:

- `blocked` if `bootstrap` is blocked, or both `read` and `write` are blocked
- `degraded` if core memory works but any of `index` or `vector` is degraded/blocked
- `ok` only if bootstrap/read/write/index are `ok`, and vector is either `ok` or explicitly disabled

Capability booleans are derived directly from layer outcomes, not inferred from UI state.

## New Vector Build Job Contract

Replace plugin-only transient embed progress with a persistent job state file.

### New file

```text
<system_dir>/PaperForge/indexes/vector-build-state.json
```

### Stored state

```json
{
  "status": "idle|running|stopping|failed|completed",
  "current": 12,
  "total": 340,
  "paper_id": "ABC12345",
  "started_at": "...",
  "last_update": "...",
  "finished_at": "...",
  "resume_supported": true,
  "mode": "local|api",
  "model": "BAAI/bge-small-en-v1.5",
  "message": "...",
  "pid": 12345
}
```

This file is the truth source for plugin progress UI and `runtime-health.layers.vector.job`.

## CLI Changes for Vector Build Lifecycle

### `paperforge embed build --resume --json`

Behavior:

- writes `vector-build-state.json` on start
- updates progress after each paper
- flushes every update to disk
- marks `completed` or `failed` on exit

### `paperforge embed status --json`

Extend to report both collection status and active/persisted job state.

### `paperforge embed stop --json`

New command.

Behavior:

- if active PID exists, request termination
- set state to `stopping`
- on clean exit, preserve resumable progress state

## Plugin UX Contract

### Dashboard

Only `System Status` needs to surface memory runtime state. It should show:

- overall status badge: `OK / Degraded / Blocked`
- one-line reason
- if degraded/blocked: one primary next step
- vector build subline when running: `Embedding 12/340 (ABC12345)`

No need to expose full internals unless user opens advanced settings.

### Features / Vector section

The settings panel becomes a thin job controller:

- Start build -> shell out to CLI
- Stop build -> shell out to CLI stop, not kill arbitrary in-memory child only
- Progress bar -> polls `embed status --json` or `runtime-health --json`
- Re-render safe: if UI remounts, it rehydrates from persisted state file

### Important constraint

UI visibility must never depend on ephemeral `embedStatusText !== null` style gates.
Ready/config sections render from stable capability state; text is allowed to be temporarily unknown.

## Agent Workflow Integration

`paperforge` skill should eventually consume `runtime-health` as the first preflight after bootstrap.

Recommended behavior:

- if `summary.safe_read == false`, block `paper-search`, `paper-qa`, `deep-reading`
- if `summary.safe_write == false`, block `reading-log`, `project-log`
- if `summary.safe_vector == false`, degrade retrieval path but keep FTS path available
- if `layers.vector.job.status == running`, agent may inform user that vector build is in progress and semantic retrieval may be partial

## Repair Model

`runtime-health` is diagnostic-only, but every degraded/blocked layer must return:

- `next_action`: short human message
- `repair_command`: exact CLI command if available

Examples:

- `paperforge memory build --verbose`
- `paperforge embed build --resume`
- `paperforge embed stop`
- `paperforge doctor`

## File Impact

Expected touched areas:

- `paperforge/commands/runtime_health.py` (new)
- `paperforge/cli.py`
- `paperforge/memory/query.py` or a new `paperforge/memory/runtime_health.py`
- `paperforge/memory/vector_db.py`
- `paperforge/commands/embed.py`
- `paperforge/plugin/main.js`
- possibly `paperforge/plugin/src/testable.js`

## Non-Goals

- No daemon/service process in this phase
- No automatic repair during health checks
- No heavy new user-facing dashboard panels
- No attempt to hide all internals from agents; agents still need structured evidence

## Success Criteria

1. There is exactly one authoritative runtime health CLI contract.
2. Dashboard `System Status` can summarize memory state without custom heuristics.
3. Vector build progress survives UI re-render and plugin restart.
4. Start/stop/resume of vector build uses persisted job state.
5. Agents can decide whether read/write/build are safe without guessing from mixed signals.
