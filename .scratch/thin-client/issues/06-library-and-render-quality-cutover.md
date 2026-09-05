# 06 — Library & Render Quality Domain Cutover

**What to build:** Refactor the Library view (Zotero sync, orphan detection, document status) and Advanced Render Quality views (audit display, R exact promotion, P proposal acceptance) to route exclusively through `PaperForgeClient` typed methods.

**Blocked by:**
- 05 — Knowledge & Retrieval Domain Cutover

**Status:** complete (2026-09-05)

- [x] Connect Library overview and sync indicators to `client.probe("library")`, displaying sync state and orphan counts without client-side database scans.
- [x] Bind manual Library sync triggers to `client.sync()`.
- [x] Expose the Render Quality diagnostic interface within paper inspection drawers, fetching consistency findings via `client.renderAudit(key)`.
- [x] Connect R exact repair execution to `client.promoteR(key, objectIds)`, verifying that promotion results refresh view state upon commit.
- [x] Connect P proposal acceptance to `client.acceptProposal(key, label, planHash)` requiring the exact SHA-256 plan hash, rendering candidate evidence cards before solicitation.
- [x] Add Vitest tests covering Library sync triggers, Render audit queries, and R/P authority actions over `MockTransport`.

Implementation notes:
- Python probe library (ready + index_stale paths) now carries structured `details.paper_count`; orphan counts stay on the maintenance envelope the probe already produces — the Library workbench renders both without any client-side database scan.
- `_runManualSync` routes through `client.sync()` (invalidate-on-mutation included); `orchestrateFromSync` consumes the same PFResult document; completion forwards exit code 0/1 into `_refreshAllReadModels` for sync-failure probing (#78).
- Render Quality is a typed-client projection inside the paper technical-details drawer: `client.renderAudit(key)` for findings, `client.renderReconcileStaging(key)` (new) for isolated R/P staging previews, per-object `client.promoteR(key, [objectId])`, per-card `client.acceptProposal(key, label, final_plan_hash)` forwarding the exact reviewed SHA-256. Committed mutations null the staging snapshot so the next render re-stages.
- Reconcile/render core, CAS/journal/plan-hash semantics: untouched (frozen backend contract).

Verification:
- Plugin: **455/455 passed** (28 files, incl. `library-render-quality-cutover.test.ts` 9 cases: sync argv/exit-code, probe-owned facts, renderAudit argv, staging argv, R promote + snapshot invalidation, P accept exact hash, fail-closed); `tsc --noEmit --skipLibCheck` clean.
- Python focused: **193 passed** (`test_probe.py` incl. ready-envelope paper_count, `test_lineage.py`, `test_shadow_rebuild.py`); ruff on changed files adds no new findings.

