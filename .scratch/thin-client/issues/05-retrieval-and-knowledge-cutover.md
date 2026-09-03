# 05 — Knowledge & Retrieval Domain Cutover

**What to build:** Refactor the Smart Retrieval and Knowledge/Memory components to consume `PaperForgeClient`. Index build/rebuild actions route through `client.runAction("memory.rebuild")` or `client.runAction("embed.build")`; semantic search and retrieval queries route through `client.retrieve()` and `client.search()`; vector health indicators read from `client.probe("memory")`.

**Blocked by:**
- 04 — OCR Workspace & Processing Domain Cutover

**Status:** ready-for-agent

- [ ] Connect the Smart Retrieval control panel to `client.probe("memory")` and `client.probe("lineage")`, eliminating client-side vector dimension or build state checks.
- [ ] Bind the localized "构建索引" action to `client.runAction("memory.rebuild")` or `client.runAction("embed.build")` based on probe-suggested primary action, streaming progress through the client.
- [ ] Route user-facing semantic search queries and deep retrieval calls through `client.retrieve(query, options)` and `client.search(query, options)`.
- [ ] Verify that completing an index build invalidates memory and retrieval cache entries across the client generation epoch.
- [ ] Add Vitest tests for retrieval views and search invocation over `MockTransport`.
