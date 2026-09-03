# 05 — Knowledge & Retrieval Domain Cutover

**What to build:** Refactor the Smart Retrieval and Knowledge/Memory components to consume `PaperForgeClient`. Index build/rebuild actions route through `client.runAction("memory.rebuild")` or `client.runAction("embed.build")`; semantic search and retrieval queries route through `client.retrieve()` and `client.search()`; vector health indicators read from `client.probe("memory")`.

**Blocked by:**
- 04 — OCR Workspace & Processing Domain Cutover

**Status:** complete

- [x] Harmonize TS `NdjsonStreamParser` vocabulary with Python #137 spec (`preflight`, `paper_settled`, `heartbeat`), eliminating contract divergence.
- [x] Wire `ActionExecutionHooks` and single cancellation token owner into `run_embedding_build`, ensuring `action run embed.build` and `action run embed.resume` stream worker-backed progress without stdout buffering or token collision.
- [x] Connect the Smart Retrieval control panel to `client.probe("memory")` and `client.probe("lineage")`, eliminating client-side vector dimension or build state checks.
- [x] Bind the localized "构建索引" / resume actions to `client.runAction()`, streaming progress through the client and wiring Stop to `client.cancelActiveOperation()`.
- [x] Route user-facing semantic search queries and deep retrieval calls through `client.retrieve(query, options)` and `client.search(query, options)`.
- [x] Verify that completing an index build invalidates memory and retrieval cache entries across the client generation epoch.
- [x] Add real CLI and Vitest tests for embed streaming, cooperative cancellation, search, and retrieval views over `MockTransport`.

Implementation notes:
- Python and TS event vocabulary frozen to the 10 standard #137 events (`start`, `preflight`, `phase`, `progress`, `paper_settled`, `heartbeat`, `item_result`, `result`, `error`, `cancelled`).
- `ActionExecutionHooks` feeds `stop_check`, `on_progress`, and `on_item_result` directly into `run_embedding_build`, eliminating stdout redirection, legacy `EMBED_PROGRESS:` tokens, and duplicate cancellation tokens.
- Added pre-publish cancellation safe point between `verify_candidate()` and `_shadow.publish()`.
- Added `--no-expand` CLI wire parity for `RetrieveOptions.expand`.
- Dashboard search and deep retrieval (@ query) cut over to `client.search(query, options)` and `client.retrieve(query, options)`, unwrapping `SearchResult[]` inside the client.
- Smart Retrieval build/resume dispatches route through `client.runAction()`, streaming progress, strictly failing closed on cross-domain action IDs, and wiring Stop only when `client.isOperationActive()`.
Verification:
- Python: **107 passed / 1 skipped** focused tests (`TestEmbedActionStreamWire` covers real CLI progress, paper settlement, `PAPERFORGE_STOP` cancellation with `rc=130`, and un-mocked real service clean NDJSON stream).
- Plugin: **448/448 passed**; `npm run typecheck` clean.
