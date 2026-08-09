# Per-Paper Materialization Reconciliation (design)

> Date: 2026-08-09
> Status: proposed — awaiting review gate. No production implementation.
> Parent map: [#135](https://github.com/LLLin000/PaperForge/issues/135)
> Related: [#145](https://github.com/LLLin000/PaperForge/issues/145) (action contract, frozen), [#158](https://github.com/LLLin000/PaperForge/issues/158) (sync trigger ownership), [generation-lineage design](docs/research/2026-08-07-generation-lineage-design.md) (deferred)
> Ticket: [#159](https://github.com/LLLin000/PaperForge/issues/159)

## 0. Decision

PaperForge adopts **per-paper desired-state / materialization reconciliation** as its system convergence model. The #145 action chains remain, but their status changes:

> **Action chains are the eager fast path. Reconciliation is the correctness mechanism.**

A thin Python seam — `observe paper → derive deficits → emit registered ActionIntents` — runs after every publish and at every external trigger. If an eager chain breaks (crash, vault close, version change), the next reconciliation re-derives the same deficits and emits the same repair intents. System correctness never depends on "the callback after that event finished running".

This decision does not change the frozen #145 contract. It repositions how intents are produced.

## 1. Why

Three existing artifacts already point here:

1. **Lineage design (2026-08-07, deferred):** "desired-vs-published derivation identity" is already defined — OCR G17 → retrieval R42 `derived_from G17` → vector V8 `derived_from R42`; mismatch = stale; lineage is *recorded data, not orchestration*; `probe lineage --json` planned. Reconciliation is the consumer that finally activates it.
2. **#145 (frozen):** ActionIntent + registry + scope + dependency-by-emission. Reconciliation is the producer-side counterpart: deficits become intents through the same registered vocabulary.
3. **#158 (open):** "Python owns change detection, idempotence, locking, sync semantics, and follow-up actions; plugin may own timers; no daemon." Reconciliation is the mechanism that satisfies this: triggers are client lifecycle, repair semantics are Python.

Existing code precedent: `paperforge/worker/asset_state.py` already computes per-paper lifecycle/health/next-step as **pure derivations from a canonical index entry** (no side effects). Reconciliation generalizes that pattern to derived-asset materialization (retrieval/vector generations), which the current lifecycle model does not cover.

Fragility being removed: today, correctness of "OCR → memory → embed" depends on the chain completing. A crash between steps, a vault closed for three days, or a version change after OCR leaves state silently behind. Under reconciliation, that state is re-found and repaired by the next trigger.

## 2. State model — two layers, no new truth source

### 2.1 Global desired state (one authority: Python config + capability registry)

```text
enabled capabilities        (ocr, memory, vector, embed)
ocr pipeline version
retrieval policy version
memory schema version
embedding identity          (provider / model / dimension)
```

Owned by the #142 config contract and the capability registry. Changes to any of these make affected assets `stale` for every paper.

### 2.2 Per-paper observed state (canonical facts + lineage only)

```text
Paper ABCD

Source          source_revision = S12
OCR             published_generation = G17, pipeline_version = O5
Retrieval       generation = R42, derived_from_ocr_generation = G17, policy_version = R3
Vector          generation = V8, derived_from_retrieval_generation = R42, embedding_identity = ...
```

These are existing canonical facts plus the lineage edges from the generation-lineage design. **No `paper_state` enum, no new state table.** Every value below is derived on read by pure functions (the `asset_state.py` pattern), never persisted as a summary.

Prerequisite: the deferred lineage publish work (lineage design steps 1–2 — persist `derived_from_*` at publish, generation ids on the OCR `result-hash` protocol). Reconciliation cannot observe what lineage has not published.

### 2.3 Facets — orthogonal, not one FSM

```text
ocr:        current | stale | missing | running | failed
retrieval:  current | stale | missing | blocked
vector:     current | stale | missing | blocked | not_required | pending_confirmation
```

A single enum state machine is rejected: the combination space (OCR done / memory stale; OCR degraded / vector missing; vector pending confirmation; memory blocked by schema migration; vector disabled) explodes immediately. Facets compose instead.

Derived summaries (read-side only):

```text
content_ready    = ocr current + retrieval current
semantic_ready   = content_ready + vector current
converged        = every asset required by global desired state is current
needs_action     = at least one repair intent is derivable
blocked          = a required asset is blocked (no repair intent; reason surfaced)
```

If vector is disabled globally: `vector = not_required`, `converged = true` with no embedding. If vector is enabled but remote spend is unconfirmed: `content_ready = true`, `semantic_ready = false`, `vector = pending_confirmation`, `converged = false`.

## 3. The reconcile seam

```bash
paperforge reconcile [--scope all|papers --key KEY ...] [--json]
```

```text
observe (canonical facts + lineage + global desired state)
  -> derive per-paper facets
  -> derive deficits (desired != observed)
  -> emit ActionIntents (registered IDs, typed scope)
  -> PFResult { intents, facet_summary, per-paper reasons }
```

Rules:

- **Pure derivation + intent emission.** `reconcile` performs no side effects; it publishes intents through the #145 registry. Idempotent: running it twice with no intervening change emits the same set.
- **Minimal repair set.** Reconcile emits only the **shallowest unsatisfied derivation edge** per paper. If retrieval is stale and vector is therefore also stale, it emits `memory.build`, not `embed.resume` — the vector deficit is re-derived after retrieval publishes. This is dependency-by-emission (§8.1b of the frozen design) restated for reconcile: sibling intents are semantically independent by construction.
- **Blocked facets surface reasons, never intents.** `ocr failed` emits `ocr.run`-family repair only when the domain handler defines retry semantics; a genuinely blocked asset emits no intent and reports the blocker.
- **Remote spend stays gated.** A `remote_possible` deficit (embedding) becomes `vector = pending_confirmation` and an intent that requires confirmation — never an automatic run. The frozen #145 invariants are unchanged. "Auto Embedding = preauthorized spend" is a future product decision that would require an explicit #145 invariant change; it is not smuggled in here.
- **Scope fidelity applies.** `reconcile --scope papers --key A` observes and emits only for A (subset semantics of the frozen design).

Deficit → intent table (initial, all IDs already in the #145 vocabulary or its §13 cutover):

| Deficit | Intent |
|---|---|
| OCR stale/missing (source changed or pipeline version bumped) | `ocr.run` / `ocr.rebuild_derived` (scoped to keys) |
| Retrieval stale/missing (OCR generation mismatch or policy version) | `memory.build` |
| Vector stale/missing (retrieval generation mismatch or embedding identity change) | `embed.build` (local path) or `embed.resume` (remote, pending_confirmation) |
| Blocked asset | no intent; reason in per-paper report |

## 4. Triggers — no daemon

```text
OCR publish        -> reconcile(keys)
sync complete      -> reconcile(changed_keys)
PaperForge startup -> reconcile(stale | missing)
maintenance        -> reconcile
plugin timer       -> reconcile        # client-owned trigger only (#158)
CLI / Agent        -> explicit paperforge reconcile
```

All triggers converge on the one Python seam. The plugin timer owns nothing but firing (resolving #158's U1 gap: schedule is client lifecycle, "what needs repair" is Python). A daemon/job service is only justified when the requirement becomes "self-heal while Obsidian is closed" — a demand-driven change, not this design.

## 5. Relationship to the frozen #145 contract

The visible result is unchanged:

```text
ocr.rebuild_derived
  -> memory.build
  -> embed.resume (pending_confirmation)
```

But each hop is now produced by reconcile after the previous publish, not by handler knowledge:

```text
OCR publishes G17
  -> reconcile(ABCD)
  -> retrieval derived_from != G17  -> ActionIntent(memory.build, ABCD)
Memory publishes R42
  -> reconcile(ABCD)
  -> vector derived_from != R42     -> ActionIntent(embed.resume, ABCD)  [pending]
```

- Dependency-by-emission: preserved and strengthened (minimal repair set).
- Confirmation/remote/automatic invariants: untouched.
- Scope fidelity: untouched (reconcile scopes are the same typed scopes).
- Chain break: no longer a correctness event. After `OCR → Memory → 💥`, the next reconcile re-derives `memory.build`; after memory publishes, the next reconcile derives `embed.resume`. O2 of the implementation plan (forced memory failure → no `embed.resume` anywhere) holds by construction: with retrieval stale, reconcile never derives the vector deficit.
- Eager fast path stays: after a publish, the caller runs `reconcile(keys)` inline (`--follow auto` for local automatic repairs), so interactive flows feel identical.

## 6. Auditability

- `paperforge probe lineage --json` (lineage design, deferred) = observed-state read model; fails closed on missing ids.
- `paperforge reconcile --json` = deficit read model; every emitted intent resolves to a registered handler via the #145 parity tests.
- Facet summaries are pure derivations — one golden-fixture test per facet combination, no state to corrupt.
- Fault-injection tests (lineage design step 4): interrupt at each publish boundary; the reader never serves a mismatched chain, and reconcile re-derives the exact minimal repair set.

## 7. Implementation mapping (after this design is accepted; amends the #145 implementation plan)

Prerequisite (own slice): lineage publish — persist `derived_from_*` at publish, generation ids on OCR `result-hash` (lineage design steps 1–2), `probe lineage --json`.

- **Phase 1 addition:** `reconcile(keys)` as a pure derivation module; `memory.build`/`embed.resume` handlers become publish-then-reconcile (their follow-up intents come from observed deficits, not hardcoded knowledge).
- **Phase 3 addition:** vertical journey asserts both paths — eager (publish → reconcile → run) and break-recovery (publish, simulate crash before follow-up, `reconcile` re-derives the identical intent). O2 extended: after forced `memory.build` failure, `reconcile` emits `memory.build` again and never `embed.resume`.
- **Phase 4 addition:** the #158 plugin timer becomes a plain `reconcile` trigger; the mtime scanner is deleted as already planned.
- **Tests:** facet-summary goldens; minimal-repair-set (two-layer staleness emits only the shallowest); idempotence; per-key scope fidelity; pending_confirmation never auto-runs.

## 8. Deliberate exclusions

- No FSM / `paper_state` enum — facets only, derived on read.
- No new truth table or summary persistence — canonical facts + lineage remain the only state.
- No daemon, watcher service, or job registry (same triggers as today).
- No workflow engine / Saga (lineage design decision 1, unchanged).
- No automatic confirmation of remote spend (frozen #145).
- No change to the frozen #145 invariants; this design is a producer-side seam.

## 9. Open questions for the review

1. `reconcile` as a CLI command (recommended) vs. a registry action: it emits intents rather than performing a domain side effect, so it is a command, not an `ActionSpec` handler.
2. Where derived summaries surface (probe envelopes, dashboard, `paper_status`): deferred to the #140 read-model design; reconcile only defines the derivation.
3. Whether the eager fast path is implemented in Phase 1 (handlers publish-then-reconcile) or Phase 3 (chain wired through reconcile): recommended Phase 1 so the vertical journey never builds hardcoded follow-up knowledge.
