# Implementation Handoff — Headless Acceptance, Release Gates, Migration Order

> Date: 2026-08-09
> Status: **ACCEPTED — ARCHITECTURE FROZEN** (decision [#146](https://github.com/LLLin000/PaperForge/issues/146) — the final Wayfinder ticket)
> Research: [#155](https://github.com/LLLin000/PaperForge/issues/155), Read-model cutover: [#148](https://github.com/LLLin000/PaperForge/issues/148), Enforcement: [#149](https://github.com/LLLin000/PaperForge/issues/149), Progress: [#137](https://github.com/LLLin000/PaperForge/issues/137), Trigger: [#158](https://github.com/LLLin000/PaperForge/issues/158)
> Migration map: `docs/implementation-map-python-core-authority.md` (R–T9)

## 0. Completion sequence (the exact condition for implementation to begin)

```text
#146 resolution frozen
  ↓
implementation map updated (R first, T8 redefined)
  ↓
ADR / glossary / ARCHITECTURE updated
  ↓
to-tickets: R + T1–T9 created as ready-for-agent issues
  ↓
verify each issue (scope, acceptance, frozen refs, blocked-by, session size)
  ↓
verify dependency DAG
  ↓
close #146
  ↓
close #135
  ↓
implementation unlocked
```

**ready-for-agent tickets are part of Wayfinder completion evidence** — the handoff is not complete until they exist and their DAG is verified.

## 1. Headless acceptance matrix

### PR-deterministic (CI)

```text
J1  machine contract fixtures          (3-OS)
J2  headless sync + vault preservation (3-OS)
J3  deterministic OCR                 (3-OS)
    architecture audit + gate --allowlist  (every PR)
    slice-specific journeys                (R, T3/T4, T5, T6, T7 — primary L4 host)
```

### Contract fixtures (machine-consumed versioned surfaces only)

```text
CapabilityEnvelope v3 · ProbeAll v1 · ActionDescriptor/ActionRequest · PFResult ·
progress NDJSON (start/phase/progress/item_result/result|error|cancelled) ·
credential/config contracts · existing typed detail contracts
```

Snapshot the **contract shape/semantics** (normalize timestamps/paths), not byte-for-byte dynamic payloads. Human commands (`doctor` text mode, `help`, update text output) are not forced into schema contracts.

### Compatibility vaults

```text
legacy snapshots with intentionally wrong data
legacy library without lineage
partial lineage
current lineage
```

Two key acceptances:

- wrong legacy snapshots → fresh read-model responses fully determine UI (#148);
- unknown lineage → reader fail-closed, reconcile does NOT mass rebuild (#159).

### Deterministic substitutes

- OCR: existing `responses` substitute (#155). No VCR.py, no synthetic OCR images.
- Embedding: **test-only** `RecordingEmbeddingProvider` injected through the existing provider seam (factory monkeypatch / dependency injection). **No production env mode** such as `PAPERFORGE_EMBED_PROVIDER=mock` — a test seam must not become a product seam.
- Live OCR/embed providers: release/manual smoke only.

## 2. Platform gates

```text
3-OS (ubuntu/windows/macos):
  CLI machine contracts
  platform-sensitive bootstrap/runtime smoke
  narrow deterministic integration where OS matters (exit codes, paths, subprocess, os.replace, locking)

Primary L4 host:
  full headless E2E
  audit
  slice journeys

Cancellation (not a 3-OS × journey matrix):
  #137 focused contract tests (stdin stop → cancelled terminal → rc130; cleanup semantics)
  + #150 Windows host evidence
  + targeted platform escalation tests (Windows: grace → taskkill /T /F; POSIX: process-group)
```

Full L4 E2E on 3-OS is not a destination gate; it may grow organically if it stays cheap.

## 3. Final migration order

```text
R   read-model authority + snapshot retirement          (#148 — first slice)
↓
T1  digest lineage publish + probe lineage
↓
T2  action registry + runner + CLI (all-scope only)
↓
T3  memory seam  ∥  T4 embed seam
↓
T5  reconcile (global frontier → minimal frontier → scope merge)
↓
T6  chain runner + dependency-by-emission (sync cutover)
↓
T7  vertical repair journey + reader gate (O1–O3, break recovery, #137 NDJSON emit)
↓
T8  action/sync client cutover + TS policy deletion
↓
T9  legacy producers + enforcement/lifecycle
```

**R = READ client cutover; T8 = ACTION/TRIGGER client cutover.** T8 covers only what R did not: action dispatch → Action Contract, argv/action-policy deletion, `_runIndexRefreshChain` deletion, timer → `paperforge sync` convergence tick, mtime scanner deletion, OCR Workspace action migration, progress-parser replacement. No duplicate "client cutover".

## 4. Gate hierarchy (merge ≠ release)

```text
Slice merge gate:     focused tests + typecheck + Python suite + audit + relevant journey → green → merge
Integration gate:    alls-green + all predecessor contracts still green
Product release:     milestone — all intended slices landed + candidate wheel/bootstrap smoke +
                     live OCR smoke + live embedding smoke + Obsidian/browser manual smoke +
                     Windows manual cancellation/bootstrap checks
```

Each slice is independently mergeable and whole-slice revertible. Each slice shipped ≠ each slice released.

## 5. Agent-ready ticket shape

Each of R, T1–T9 carries exactly:

```text
What to build          (end-to-end behavior, user perspective)
Observable acceptance  (from the frozen docs, not prose)
Frozen design refs     (links; the docs are not copied in)
Explicit deletions     (old authority that must disappear)
Blocked by             (native dependency edges)
Out of scope           (nothing outside the frozen design)
Rollback unit          (whole-slice revert)
```

Guardrail on every ticket:

> **No implementation issue may silently widen its frozen design. New architectural ambiguity → stop and reopen a planning issue.**

DAG: `R → T1 → T2 → (T3 ∥ T4) → T5 → T6 → T7 → T8 → T9`. T3/T4 is the only explicit parallel point.

## 6. Documentation and ledger updates

- ADR: `docs/adr/python-core-authority.md` (consolidated, per #149).
- Glossary: six terms appended to `docs/ARCHITECTURE.md` — Canonical Fact, Semantic Read Model, Action Contract, Bootstrap Adapter, Client Cache, Convergence Tick.
- Ledger (`PROJECT-MANAGEMENT.md`) stays a projection; report/contract stay authoritative (truth hierarchy).
