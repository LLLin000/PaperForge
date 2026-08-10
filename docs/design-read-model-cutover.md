# Product Read-Model Cutover and Snapshot Retirement

> Date: 2026-08-09
> Status: **ACCEPTED — ARCHITECTURE FROZEN** (decision [#148](https://github.com/LLLin000/PaperForge/issues/148))
> Read models: [#140](https://github.com/LLLin000/PaperForge/issues/140), Client boundaries: [#144](https://github.com/LLLin000/PaperForge/issues/144), Enforcement: [#149](https://github.com/LLLin000/PaperForge/issues/149), Cache research: [#157](https://github.com/LLLin000/PaperForge/issues/157), Handoff: [#146](https://github.com/LLLin000/PaperForge/issues/146)

## 0. The cutover line

```text
contract declares planned target
        ↓
Python semantic read models (probe / probeAll / typed details)
        ↓
typed PaperForgeClient
        ↓
Dashboard / Settings cutover
        ↓
memory-state.ts DELETE
        ↓
ZERO READERS
        ↓
snapshot writers DELETE
        ↓
ZERO WRITERS
        ↓
legacy files best-effort cleanup
        ↓
headless + plugin parity smoke
        ↓
read-model authority ACTIVE
        ↓
snapshot contract retired
```

**Key acceptance test (stronger than grep):**

> Given intentionally contradictory legacy snapshot files, fresh Python read-model responses still fully determine Dashboard/Settings output and action availability.

## 1. Lifecycle ordering (Q1)

The new authority is **declared planned first**, proven, then promoted — never announced active before implementation:

```text
0. Contract declaration      read-model authority = planned; snapshot contract = active/deprecating
1. Python read-model surface complete (probe / probeAll / required details)
2. Typed TS client; Dashboard/Settings → probe/query
3. Delete memory-state.ts semantic owner
4. Prove zero client readers
5. Stop snapshot writers (delete state_snapshot implementation and calls)
6. Cleanup legacy snapshot files (best-effort)
7. Focused smoke + parity + regression
8. Tracked promotion            read-model authority → active; snapshot contract → deprecated/removed
```

Promotion is the **last tracked contract change of the slice** (AGENTS.md truth hierarchy: promotion = code change with commit).

## 2. Detail surface: reuse-first + exactly one known gap (Q2)

- Reuse existing module-owned detail surfaces: OCR status/list/maintenance, `embed status --json`, memory status/query, paper/library commands, doctor/runtime-health diagnostics.
- **Exactly one currently-known new detail surface** (per #140): the per-paper OCR pipeline-version list currently embedded in `probe_ocr` — move it to an OCR detail command during this cutover.
- **Dashboard is a consumer, not a source.** No typed method wraps `paperforge dashboard --json` as a read-model authority; Dashboard consumes `probeAll()` + typed detail methods where expanded UI needs rows.

## 3. memory-state.ts (Q3)

Delete the file (snapshot parsing, freshness/needs_rebuild inference, canonical path resolution are all dead responsibilities):

- transport-only types move to `paperforge-client/types`; pure UI formatters move to the UI layer.
- Repository-wide **zero references** required. No same-name empty shell to spare imports.

## 4. Contract retirement vs physical cleanup (Q4)

- **Correctness gate = zero readers + zero writers**, proven in this order: TS reader removed → zero-reader assertion → Python snapshot writes removed → `state_snapshot.py` deleted → zero-writer assertion.
- Legacy files in existing vaults (`memory-runtime-state.json`, `vector-runtime-state.json`, `runtime-health.json`): **Python-owned best-effort cleanup** — hygiene, not correctness. Cleanup failure never fails the cutover; once unread/unwritten they are inert garbage.
- Rollback stays whole-slice revert: old code ignores nothing it doesn't read, and the old writer can recreate disposable snapshots. No TTL, no legacy fallback.

## 5. Diagnostics (Q5)

- Diagnostic commands survive: `paperforge runtime-health --json`, `paperforge doctor`, `ocr doctor` (diagnostics are a separate contract family, not capability summaries — #140).
- The diagnostic **snapshot contract does not**: commands compute on demand → stdout PFResult; nothing writes `indexes/runtime-health.json`.

> **Diagnostic command survives; diagnostic snapshot contract does not.**

## 6. Stale behavior (Q6)

Strictly no dual read during migration. Only: last-known in `data.json` → stale display → actions disabled → fresh probe (per #135/#144). Rollback = `git revert` of the whole vertical slice; never runtime dual-read.

## 7. Slice shape (Q7)

One atomic vertical cutover PR composed of reviewable, dependency-ordered commits:

```text
Commit A   Python probeAll/detail parity
Commit B   typed PaperForgeClient + fixtures
Commit C   Dashboard/Settings cutover
Commit D   memory-state deletion
Commit E   snapshot writer retirement + cleanup
Commit F   zero-reader/zero-writer assertions + smoke
Commit G   contract lifecycle promotion
```

Before merge: target branch keeps the old authority intact. After merge: only the new authority exists. Not a mega-commit.

Smoke (sandbox vault, #155 harness):

- probeAll → Dashboard renders → detail expands → mutation finishes → `invalidateAll()` → no stale action enabled → probeAll → refreshed UI.
- Obsidian absent → the same probeAll succeeds (headless parity).
- **Snapshots pre-exist with deliberately wrong contents → UI output and action availability unaffected** (the key acceptance test).

## 8. Authority vs enforcement promotion (Q8)

Two different facts, promoted separately:

```text
Semantic Read Model authority      → active            (end of this slice)
snapshot contract                  → deprecated/removed (end of this slice)
CANONICAL_READ enforcement (#149)  → active + advisory (this slice)
CANONICAL_READ enforcement         → active + blocking (separate tracked commit after collector soak / FP review)
```

"New authority exists" and "new static rule is mature enough to block CI" are never conflated.
