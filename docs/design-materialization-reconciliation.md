# Per-Paper Materialization Reconciliation (design)

> Date: 2026-08-09
> Revision 2 (2026-08-09): reader fail-closed gate; `unknown` lineage facet (never stale, never mass-rebuild); single `next_actions` channel (no second intents wire); materialization facets separated from action policy/runtime; three-layer model (global desired → global substrate → per-paper); minimal repair frontier + scope merging; triggers know scope only; not a retry engine; deletion/orphan is library-level; old recommendation producers retired to projections; digest-based lineage identity (counters are diagnostics only).
> Status: **ACCEPTED — ARCHITECTURE FROZEN** (2026-08-09). Later problems are implementation defects or domain-seam issues unless an invariant is proven wrong.
> Parent map: [#135](https://github.com/LLLin000/PaperForge/issues/135)
> Related: [#145](https://github.com/LLLin000/PaperForge/issues/145) (action contract, frozen), [#158](https://github.com/LLLin000/PaperForge/issues/158) (sync trigger ownership), [generation-lineage design](docs/research/2026-08-07-generation-lineage-design.md)
> Ticket: [#159](https://github.com/LLLin000/PaperForge/issues/159) (closed)

## 0. Decision

PaperForge adopts **per-paper desired-state / materialization reconciliation** as its system convergence model. The #145 action chains remain, repositioned:

> **Action chains are the eager fast path. Reconciliation is the eventual-correctness mechanism. The reader freshness gate is the immediate-correctness mechanism.**

```text
Canonical facts
  ├── semantic read models (#140)
  └── lineage / materialization observation
              │
              ▼
           Reconcile
      global frontier -> minimal repair frontier
              │
              ▼
         ActionIntent
              │
              ▼
      Action Registry (#145)
        ├── auto local ──► publish ──► reconcile again
        └── confirmation ──► UI
              │
              ▼
          Reader gate: serves only lineage-compatible materialization
```

System correctness never depends on "the callback after that event finished running". If an eager chain breaks, the next reconciliation re-derives the same intents; until then, the reader gate refuses to serve mismatched materialization.

This decision does not change the frozen #145 contract. It pins how intents are produced and how readers consume materialization.

## 1. Why

The same three artifacts as Revision 1, plus one correction:

1. **Lineage design (2026-08-07, deferred):** desired-vs-published derivation identity; mismatch = stale; **UNRESOLVED when unobserved**; lineage is recorded data, not orchestration. Reconciliation is its consumer.
2. **#145 (frozen):** ActionIntent + registry + scope + dependency-by-emission. Reconciliation is the producer-side counterpart; the registry stays the only policy authority.
3. **#158 (open):** Python owns repair semantics; plugin owns timers; no daemon. Reconciliation is the mechanism.

Correction from the review: without a reader gate, mismatch is observable but still served. Reconcile is eventual repair; the reader gate is the invariant that prevents wrong consumption in the stale window.

## 2. State model — three layers, no new truth source

### 2.1 Global desired state (one authority: Python config + capability registry)

```text
enabled capabilities        (ocr, memory, vector, embed)
ocr pipeline version
retrieval policy version
memory schema version
embedding identity          (provider / model / dimension)
```

### 2.2 Global substrate observed (new layer)

Before any per-paper derivation, observe whether the global substrate satisfies the desired state: memory schema present and compatible, vector backend/dimension compatible, embedding identity available, capabilities enabled.

- If the substrate is incompatible, the **global repair frontier** emits exactly one global intent (`embed.build` for vector substrate, `memory.build` for schema, …) with scope `all`.
- Until it is satisfied, every affected per-paper facet is `blocked_global` — never 800 per-paper repairs for one global change.

### 2.3 Per-paper observed state — digest-based lineage identity

Lineage identity is content-addressed, not counter-driven:

```text
OCR identity        = result_hash
Retrieval identity  = hash(OCR identity + retrieval_policy_version + produced units digests)
Vector identity     = hash(retrieval identity + embedding identity)
```

- **Correctness compares digests.** A rebuild whose output is identical produces an identical digest and leaves downstream layers untouched (change-prune). Generation/run counters exist for diagnostics and audit only and never drive rebuild decisions.
- `source_revision` is the per-layer semantic input digest (e.g., the OCR input hash), never the whole Zotero entry revision — editing a title/author must not re-OCR a PDF.
- **Unknown/unobserved lineage is a first-class state.** Legacy vaults and interrupted publishes carry no identity; the facet is `unknown`, the reader gate fails closed, and reconcile never interprets `unknown` as `stale`. No mass rebuild of old libraries.

### 2.4 Facets — materialization only

```text
ocr:        current | stale | missing | running | unknown
retrieval:  current | stale | missing | unknown
vector:     current | stale | missing | not_required | unknown
```

Materialization facets never carry policy or runtime state:

- `confirmation`, `busy`, `unavailable` come from the #145 ActionDescriptor/Preflight, not from facets. A UI "pending confirmation" badge is a projection of registry policy over a `missing`/`stale` facet.
- `failed` is a last-attempt diagnostic (error, timestamp), not a facet.
- `blocked` is reason-coded: `blocked_global` (upstream substrate) vs `action_unavailable` (preflight). Both are observations feeding the report; neither is a repair intent.
- `running` is an activity observation (publish in progress), orthogonal to the five materialization values.

Derived summaries (read-side only, never stored):

```text
content_ready    = ocr current + retrieval current
semantic_ready   = content_ready + vector current
converged        = every required asset current
needs_action     = at least one repair intent derivable
blocked          = a required asset blocked (reason surfaced; no intent)
```

Deletion/orphan is **not** a per-paper materialization repair. A paper absent from the desired library is library-level prune reconciliation with its own authority; it is never interpreted as `ocr missing`.

## 3. The reconcile seam

```bash
paperforge reconcile [--scope all|papers --key KEY ...] [--json]
```

```text
observe (global desired + substrate + per-paper lineage)
  -> derive facets
  -> derive global repair frontier, then per-paper minimal repair frontier
  -> merge by canonical action (scope merging)
  -> emit ActionIntents
  -> PFResult.next_actions (single channel) + data: facet_summary, per-paper reasons
```

Rules:

- **Pure derivation + intent emission.** No side effects; idempotent (same facts → same result).
- **Global frontier first.** While the substrate is incompatible, only the global intent is emitted; per-paper repairs are `blocked_global`.
- **Minimal repair frontier.** Per paper, all first-layer unsatisfied nodes whose prerequisites are satisfied are independent siblings. Reads existing lineage edges only — no DAG engine, no workflow planner, and independent derivation branches are handled naturally.
- **Scope merging.** Per-paper frontiers merge by canonical action into one intent with a merged papers scope: 100 stale papers → `memory.build([A..Z])`, one invocation.
- **Reconcile decides the operation, never the policy.** Per-paper vector `missing`/`stale` → `embed.resume`; global vector substrate incompatible → `embed.build`. `cost`, `confirmation`, `automatic` come from the #145 registry. No cost policy exists in reconcile.
- **Single channel.** Internal `ActionIntent` objects are projected onto the existing `PFResult.next_actions` wire; Python hands that same result to the #145 follow-up runner. There is no second `intents` wire, and the plugin never loops intents itself.
- **Not a retry engine.** A deficit is not a retry grant. A failed action stops the current invocation; a periodic trigger re-derives an intent only when observed facts changed since the last attempt (`last_attempt` diagnostic), under an explicit retry rule owned by #158. No blind 120-second re-fire of failed work.
- **Remote spend stays gated.** `remote_possible` intents require confirmation (frozen #145). Auto-embedding preauthorization is a future product decision requiring an explicit #145 invariant change.
- **Scope fidelity applies** (subset semantics of the frozen design).

Deficit → operation table (operation decided here; policy from registry):

| Deficit | Repair operation |
|---|---|
| OCR stale/missing | `ocr.run` / `ocr.rebuild_derived` (scoped to keys) |
| Retrieval stale/missing | `memory.build` |
| Vector stale/missing (per-paper) | `embed.resume` |
| Vector substrate incompatible (global) | `embed.build` |
| Blocked (global or preflight) | no intent; reason in per-paper report |

## 4. Triggers — know scope only

```text
OCR publish        -> reconcile(keys)
sync complete      -> reconcile(changed_keys)    # Python already knows changed keys
PaperForge startup -> reconcile(all)
maintenance        -> reconcile(all | changed)
plugin timer       -> reconcile(all)             # client fires; Python derives state
CLI / Agent        -> explicit reconcile
```

A trigger supplies **scope, never semantic state**. "Timer scans files, finds stale papers, reconciles those" is forbidden — that would reintroduce #158's violation. Startup does not know what is stale; it asks reconcile to look at everything.

## 5. Relationship to the frozen #145 contract

Visible behavior is unchanged:

```text
ocr.rebuild_derived
  -> memory.build
  -> embed.resume (confirmation required)
```

Each hop is produced by reconcile after the previous publish:

```text
OCR publishes digest G
  -> reconcile(ABCD)
  -> retrieval identity != hash(G + policy + units)  -> ActionIntent(memory.build, ABCD)
Memory publishes R
  -> reconcile(ABCD)
  -> vector identity != hash(R + embedding)          -> ActionIntent(embed.resume, ABCD)
```

- Dependency-by-emission: preserved and strengthened — the minimal repair frontier emits only prerequisites-satisfied deficits, so sibling intents are independent by construction.
- Confirmation/remote/automatic invariants, scope fidelity, single channel: untouched (this design only changes the producer).
- Chain break: not a correctness event. The next reconcile re-derives `memory.build`; after memory publishes, the next derives `embed.resume`. O2 (memory failure → no `embed.resume` anywhere) holds by construction.
- Eager fast path stays: publish → `reconcile(keys)` inline (`--follow auto` for local automatic repairs).

## 6. Auditability

- **Reader gate** is the immediate correctness check: any reader of derived materialization fails closed on lineage mismatch or `unknown` (`probe lineage --json` keeps its UNRESOLVED semantics); it never serves a mismatched chain.
- `reconcile --json` is the deficit read model; intents travel the existing `next_actions` channel; every intent resolves to a registered handler (parity tests).
- Facet goldens cover `unknown`, `blocked_global`, `not_required`; global-first tests prove one global intent; scope-merge tests prove one intent per canonical action; change-prune tests prove identical digests trigger nothing downstream.
- **Single producer**: after rollout, materialization-repair recommendations exist in exactly one place (reconcile). `asset_state.py` next-step/health logic and OCR maintenance `_recommended_action` become projections of reconcile output or are deleted (single-producer parity tests).

## 7. Implementation mapping (amends the #145 implementation plan, §11)

Prerequisite slice: **digest lineage publish** — persist per-layer derived digests at publish (OCR `result_hash`; retrieval digest; vector digest), `probe lineage --json`, unknown fails closed. Counters are diagnostics only.

- **Phase 1 addition:** `reconcile(keys)` pure module (global frontier → minimal repair frontier → scope merging → single channel); handlers publish-then-reconcile; reconcile decides operation, registry decides policy.
- **Phase 3 addition:** vertical journey asserts eager and break-recovery paths; O2 extended (forced `memory.build` failure → reconcile re-emits `memory.build`, never `embed.resume`); reader fail-closed test.
- **Phase 4 addition:** plugin timer becomes a `reconcile(all)` trigger (scope-only); deletion list for old producers (plan §11).

## 8. Deliberate exclusions

- No FSM / `paper_state` enum; facets derived on read.
- No new truth table or summary persistence.
- No daemon, watcher service, or job registry.
- No workflow engine / DAG engine / Saga (lineage edges are read, not orchestrated).
- No second `intents` wire; no client-side intent loops.
- No retry engine and no blind periodic re-fire of failed actions.
- No per-paper repairs for global-substrate problems.
- No generation-counter-driven rebuilds — digests decide.
- No automatic confirmation of remote spend; no change to frozen #145 invariants.

## 9. Resolved questions

1. `reconcile` is a CLI command, not a registry action: it emits intents and performs no domain side effect.
2. Derived summaries surface through the #140 read models; reconcile defines only the derivation.
3. The eager fast path lands in Phase 1 (publish-then-reconcile), so the vertical journey never builds hardcoded follow-up knowledge.
4. Periodic retry rules are owned by #158, constrained here to: no blind re-fire; re-derive only on changed facts.
