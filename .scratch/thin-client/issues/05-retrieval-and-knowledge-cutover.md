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

Corrective round 2 (noop settlement + fail-closed entrypoint + Stop ownership):
- `registry._on_progress()` no longer settles papers as `succeeded`; `paper_settled(key, status, None)` moved into `_on_item_result()` so noop/skip papers settle with their real status.
- `run_embedding_build` restores `processed_count` / `papers_skipped` increments on all noop branches, so `progress.current` and `papers_skipped` are truthful.
- New un-mocked CLI test: real `embed.resume` against a fully seeded vault (matched body/object units hashes + aligned vec0 rows) executes the hash-skip branch without network and asserts `progress.current==1`, single `paper_settled outcome=noop`, single `item_result status=noop`, `papers_skipped==1`, every stdout line clean NDJSON.
- `_runAllowedDispatch("memory", …)` else-branch no longer substitutes an unknown `action_id` with `memory.build` — Notice + re-probe, fail-closed; regression test added (`ActionPrimary satisfies` typed).
- `_renderMemoryDetail` removed the last `embedController.busy/stop` fallback; Stop renders only when `client.isOperationActive()`; legacy module-detail-navigation tests pinning execFile memory-build dispatch and the embed-controller Stop deleted.
Verification:
- Python focused: **169 passed** (`test_action_registry.py` + `test_shadow_rebuild.py` + `test_lineage.py`); ruff clean on changed files (embedding.py pre-existing findings unchanged vs HEAD).
- Plugin: **446/446 passed** (27 files); `tsc --noEmit --skipLibCheck` clean.
