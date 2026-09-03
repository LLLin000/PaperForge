# 06 — Library & Render Quality Domain Cutover

**What to build:** Refactor the Library view (Zotero sync, orphan detection, document status) and Advanced Render Quality views (audit display, R exact promotion, P proposal acceptance) to route exclusively through `PaperForgeClient` typed methods.

**Blocked by:**
- 05 — Knowledge & Retrieval Domain Cutover

**Status:** ready-for-agent

- [ ] Connect Library overview and sync indicators to `client.probe("library")`, displaying sync state and orphan counts without client-side database scans.
- [ ] Bind manual Library sync triggers to `client.sync()`.
- [ ] Expose the Render Quality diagnostic interface within paper inspection drawers, fetching consistency findings via `client.renderAudit(key)`.
- [ ] Connect R exact repair execution to `client.promoteR(key, objectIds)`, verifying that promotion results refresh view state upon commit.
- [ ] Connect P proposal acceptance to `client.acceptProposal(key, label, planHash)` requiring the exact SHA-256 plan hash, rendering candidate evidence cards before solicitation.
- [ ] Add Vitest tests covering Library sync triggers, Render audit queries, and R/P authority actions over `MockTransport`.
