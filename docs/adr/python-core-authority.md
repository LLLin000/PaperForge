# ADR: Python Core Authority

- Date: 2026-08-09
- Status: ACCEPTED (consolidated from Wayfinder decisions #145, #159, #137, #143, #144, #158, #148, #149; map #135)
- Related: docs/design-python-action-contract.md, docs/design-materialization-reconciliation.md, docs/design-progress-cancellation-protocol.md, docs/design-bootstrap-adapter-lifecycle.md, docs/design-thin-client-boundaries.md, docs/design-read-model-cutover.md, docs/design-architecture-contract-enforcement.md, docs/design-implementation-handoff.md

## Context

PaperForge grew with the Obsidian plugin owning runtime discovery, canonical-file parsing, state interpretation, and action policy. Product authority was split across Python and TypeScript, producing duplicate vocabularies, fragile `(verb, command)` dispatch, and no single truth for readiness or repair semantics. The destination: PaperForge as a standalone Python application with the plugin reduced to a GUI/bootstrap adapter with no product-semantic authority.

## Decision

Python owns all product semantics; clients own presentation, transport, and lifecycle triggers only. The boundary is enforced by a deterministic architecture audit, not by convention.

## Consequences

- One authority per fact: canonical storage stays distributed; interpretation lives in Python read models; action metadata and policy live in one Python registry; reconciliation derives repair intents from lineage observation; the reader gate fails closed.
- Clients (Obsidian GUI adapter, Agent, CLI) consume typed JSON/NDJSON surfaces and open only Python-returned paths. They never infer meaning from files, paths, process state, or cached data.
- Long tasks speak one NDJSON protocol with one cancellation state machine; the timer is a dumb client fire into a Python convergence entrypoint.
- Vertical clean cutovers with whole-slice rollback; old authority is deleted, never coexisting.
- Enforcement is a deterministic structural audit (CANONICAL_READ + existing rule kinds), not a static semantic analyzer.

## § Read Model

`probe(module)` / `probe_all()` are the capability read-model surface; dedicated typed detail commands carry rows. Snapshots are retired as contracts (display-only last-known cache in `data.json`); memory-state.ts is deleted. First implementation slice: read-model cutover.

## § Action

One declarative Python ActionSpec registry + generic runner (`action list/describe/run`); action_id names an executable operation; producers emit intent only; confirmation is exact per-action; follow-up execution is explicit (`--follow none|auto`) with per-invocation dedupe/depth; no command strings or argv on any wire; scope fidelity is subset semantics.

## § Reconciliation

Per-paper desired-state/materialization reconciliation: digest lineage (OCR=result_hash, retrieval=hash(ocr+policy+units), vector=hash(retrieval+embedding)); unknown lineage fails closed (never stale, never mass rebuild); global frontier before per-paper minimal repair frontier; scope merging by canonical action; single `next_actions` channel; not a retry engine (re-derive only on changed facts); remote embedding stays confirmation-required.

## § Progress

Two machine modes: single-result PFResult JSON and structured-stream NDJSON (start/phase/progress/item_result + exactly-one result|error|cancelled terminal). One cancellation state machine, two ingress (stdin `PAPERFORGE_STOP` per #150 evidence; terminal signals). Exit codes 0/1/130; action 2/3 pre-dispatch only. Sidecar and cross-process `embed stop` retired.

## § Bootstrap

Plugin may create the first runnable Python environment; once PaperForge can execute, it never owns runtime lifecycle semantics or canonical runtime publication. `~/.paperforge/runtime/` with Python as sole pointer writer; verbs setup/update/repair; matrix is candidate until wheel+smoke gates; bootstrap is the last recovery boundary for an unrunnable runtime.

## § Thin Client

Client may know what the user is looking at and what Python told it; never infer meaning from files, paths, process state, or cache. Typed PaperForgeClient (no generic query); allow/prohibit read lists; invalidateAll → probeAll on mutation; client owns UI context, Python owns canonical identity resolution; controllers are process mechanics only.

## § Trigger

Sync convergence tick: dumb client timer (data.json cadence, vault-open + interval) fires `paperforge sync`; Python detects external changes, syncs, then runs `reconcile(all)`. Headless = same entrypoint via cron/systemd/Task Scheduler/CLI.

## § Enforcement

Complete the existing ArchitectureContract + deterministic collectors; delta = RuleKind.CANONICAL_READ + FilesystemReadFact + TS filesystem-read extraction + wrapper registry (bootstrap.pointer.read / client_cache.read / navigation.open / workspace.context). Lifecycle and enforcement promote separately; UNRESOLVED never passes (fail-incomplete); collector → survey → contract → audit → report → ledger; promotion = tracked commit.
