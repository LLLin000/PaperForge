# Generation Lineage for Derived Publication Units (design)

**Date:** 2026-08-07
**Status:** Design only — implementation deferred past #133/#134 acceptance
**Trigger:** Architecture audit review (2026-08-07): OCR → Memory → Vector is
"locally transaction-correct" but not yet "system generation-consistent".

## Problem

Each derived layer is individually healthy, but nothing proves the layer the
user queries is derived from the generation they believe:

```
OCR generation        G17
Memory units          R16     (derived from G16)
FTS                   16      (derived from G16)
Vector live           15      (derived from R15)
```

Every layer passes its own freshness checks (`result-hash`, manifest
freshness, `build_state`, `live_generation`), yet the system can serve a stale
lineage. Current defenses are per-module code rules, not one observable
invariant.

## Goal

Make "the user's query sees one compatible committed generation" a
**machine-checkable invariant**, so invalidation decisions ("参数变了要不要重建",
"版本升级要不要重 embed") follow from a desired-vs-published derivation
identity instead of code rules.

## Model

Each derived publication unit records **source generation identity**:

```
retrieval.units:   derived_from_ocr_generation = G17
retrieval.fts:     derived_from_ocr_generation = G17
vectors.live:      derived_from_retrieval_generation = R42
```

Reader-side invariant:

```
current OCR G17
   → retrieval derived from G17
   → vector derived from the retrieval generation derived from G17
mismatch → stale (never silently serve)
```

## Design decisions

1. **No workflow engine / Saga / Temporal.** The lineage is *recorded data*,
   not orchestration. Adding a workflow engine to a local-first vault tool is
   the wrong weight class (audit review agrees).
2. **Generation identity is a monotonic counter + source digests** per layer
   (OCR generation id derived from the already-canonical `result-hash`;
   retrieval/vector generations from their build_state transaction ids).
3. **Written at publish time** (same commit point as the current
   `os.replace` publish for vectors and `result-hash` publish for OCR), so a
   generation id can never dangle.
4. **Stale = derivation chain mismatch**, reported through the existing
   `probe memory` / `maintenance` surface with one canonical verb
   (`rebuild_derived`), never guessed by the UI.

## Contract additions (future)

- Publication units gain `derived_from` edge metadata (OCR → retrieval →
  vectors) in the ArchitectureContract asset graph.
- New rule kind sketch: `derivation_consistent` — a reader operation's
  observed lineage must equal the desired derivation chain; UNRESOLVED when
  any layer's generation identity is unobserved (same fail-closed semantics
  as the existing enumeration rules).

## Implementation path

1. Extend the vector `build_state` + `memory` meta to persist
   `derived_from_*` ids at publish (the publish commit point already exists
   from #117).
2. Extend OCR `result-hash` protocol to carry a generation id (the
   `result-hash.pending` marker already exists from #126).
3. Add a `paperforge probe lineage --json` capability envelope; fail closed
   on missing ids.
4. Fault-injection tests (not plain unit tests): interrupt at each publish
   boundary, assert the reader never serves a mismatched chain.
5. Promote `derivation_consistent` rules in the audit Contract once the
   collectors can observe the ids.

## Non-goals

- Cross-generation backfill/migration of old vaults (legacy rows stay
  `generation unknown` → rule UNRESOLVED, never guessed).
- Distributed consensus or cross-machine lineage.
