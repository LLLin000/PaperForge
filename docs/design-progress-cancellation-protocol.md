# Structured Progress, Cancellation, and Terminal Results Protocol

> Date: 2026-08-09
> Status: **ACCEPTED — ARCHITECTURE FROZEN** (decision [#137](https://github.com/LLLin000/PaperForge/issues/137))
> Research: [#139](https://github.com/LLLin000/PaperForge/issues/139) (versioned CLI streaming), Evidence: [#150](https://github.com/LLLin000/PaperForge/issues/150) (real-host cancellation), Action contract: [#145](https://github.com/LLLin000/PaperForge/issues/145), Convergence: [#158](https://github.com/LLLin000/PaperForge/issues/158)

## 0. Two machine modes

- **Single-result mode** (short commands with `--json`): stdout = exactly one `PFResult` JSON document. Unchanged.
- **Structured-stream mode** (long tasks): stdout = NDJSON events, then **exactly one terminal event**, then EOF. stderr = human logs only.

The flag that selects the mode is an implementation detail; the protocol boundary (single-result JSON vs streaming NDJSON) is the contract.

## 1. Stream framing

- stdout carries machine output only: UTF-8, one JSON object per line, `schema_version: 1`, `event` discriminator required on every line.
- stderr carries human logs and diagnostics. Machine-facing warnings enter the terminal `PFResult.warnings`, never stdout prose.
- The old colon-token family (`EMBED_START:…`, `OCR_REBUILD_*`, `OCR_REDO_*`, `DONE`, `NOTICE`) and the tolerant "ignore unknown lines" parser are retired in a clean cutover — no token + NDJSON dual parsing.

## 2. Event vocabulary

### Non-terminal (any number, ordered)

```json
{"schema_version": 1, "event": "start",       "operation": "ocr.rebuild", "total": 12}
{"schema_version": 1, "event": "phase",       "operation": "ocr.rebuild", "phase": "postprocess"}
{"schema_version": 1, "event": "progress",    "operation": "ocr.rebuild", "current": 3, "total": 12, "item_id": "ABC"}
{"schema_version": 1, "event": "item_result", "operation": "ocr.rebuild", "item_id": "ABC", "status": "ok"}
```

- `start`: operation id, optional `total` and `scope`.
- `phase`: for global operations (sync/setup/update) that have no per-item count; per-item operations may also emit phases.
- `progress`: `current`/`total`, optional `item_id`.
- `item_result`: per-item outcome where the domain emits it (the successor of `OCR_REBUILD_RESULT`). Status vocabulary is domain-owned.

### Terminal (exactly one, last, then EOF)

```json
{"schema_version": 1, "event": "result",    "operation": "ocr.rebuild", "result": {"ok": true, ...PFResult...}}
{"schema_version": 1, "event": "error",     "operation": "ocr.rebuild", "result": {"ok": false, ...PFResult...}}
{"schema_version": 1, "event": "cancelled", "operation": "ocr.rebuild", "result": {"ok": false, ...PFResult...}}
```

The terminal payload is the existing `PFResult` (`ok/data/error/warnings/next_actions`); no `cancelled: bool` is added to PFResult. `error` and `cancelled` differ only in the terminal event discriminator and the resulting exit code.

## 3. Cancellation state machine

**One cancellation state machine per process; two ingress paths into the same CancellationToken/flag:**

- Controller-owned process: plugin writes the fixed cooperative stop token `PAPERFORGE_STOP\n` to stdin.
- Terminal user: Ctrl-C / SIGINT / SIGTERM enters the same flag (a normal cooperative cancel, not merely a fallback).

Note on history: #139's research excluded bidirectional stdin commands; #150's real-host evidence (Obsidian 1.13.4 / Electron 37 / Node 22: one `cancelled` event → EOF → rc130; Node/Electron cannot reliably do CTRL_BREAK_EVENT) supersedes that stance for a **single fixed cooperative stop token only** — this is not a general bidirectional command channel.

### Safe points

Checked at: between items; between phases; before an expensive remote call when possible; after child-process completion; before the publication commit. **Never** inside an atomic publish / transaction commit.

### Retired with this decision

- The embed control sidecar, and with it the **cross-process `paperforge embed stop` cooperative-control contract** — stdin cannot reach another process's child. Orphaned processes (controller lost) are hard-terminated only; no persistent control plane is invented (#135: no cross-client job takeover, no daemon).
- Windows hard escalation remains: grace timeout, then `taskkill /T /F` (#150).

## 4. Terminal outcome vs durable state

- `cancelled` is a **terminal operation outcome** (stream + exit code), never a persisted status.
- Durable state after cleanup: `build_state.status = idle`, with `current`/`total` preserved and resume supported (existing `running → stopping → idle → resume` semantics; integration tests already pin `stop → idle → resume`).

### Cleanup guarantees on cancel/failure

- Shadow candidate aborted; live publication stays on the previous version.
- In-place domain operations restore per their existing backup/restore path.
- Publication markers are preserved: OCR `result-hash.pending` is created before derived mutation and removed **only after a verified publish**; on cancel it must remain, keeping the reader fail-closed (never trust the stale hash, never consume half-built artifacts).
- Resume/redo reuse existing semantics (`embed --resume`, OCR redo/rebuild).
- Residual deficits are re-observed by the next sync convergence tick (#158) — the protocol never needs its own recovery machinery.

## 5. Protocol failure — fail closed

| Condition | Handling |
|---|---|
| non-JSON stdout line | protocol failure |
| `schema_version` major != 1 | protocol failure |
| EOF without a terminal event | protocol failure |
| second terminal event | protocol failure |
| events after the terminal event | protocol failure |
| unknown `event` type | protocol failure (the discriminator is semantic; new required event types bump the major version) |
| unknown fields inside a known event | ignored (additive evolution within a major) |

Clients surface a protocol failure and terminate the invocation; they never guess.

## 6. Exit codes

```text
0    completed / result
1    operation-level failure / error
130  cancelled
```

Action commands additionally use `2` (invalid request) and `3` (confirmation required) — **pre-dispatch contract only** (#145). A dispatched long action cancelled mid-run produces a `cancelled` terminal + rc130, never a folded rc1.

## 7. Responsibilities

| Owner | Owns |
|---|---|
| Python commands | event emission; cancellation flag + safe points; child/publication cleanup; exactly-one terminal event; exit code |
| Plugin process controllers | spawn; NDJSON parse → render; Stop button → stdin token; grace timeout; hard escalation (`taskkill /T /F` on Windows); surface the terminal result |
| CLI / Agent | same protocol consumers; no semantic parsing beyond rendering and fail-closed checks |
| #145 action runner | reuses this protocol unchanged for long-task actions; defines no second progress/cancellation protocol |

## 8. Retired vocabulary

`EMBED_START/PROGRESS/DONE`, `OCR_REBUILD_*`, `OCR_REDO_*`, `DONE`, `NOTICE`, and tolerant parsing are retired. Machine warnings → `PFResult.warnings`; human logs → stderr.
