# 01 — Client Core Engine & Transport Consolidation

**What to build:** An isomorphic TypeScript client core (`PaperForgeClient`) situated above an abstract `Transport` seam. It consolidates existing process-spawning and streaming mechanics (`LongTaskClient`, `ActionClient`, `ManagedRuntime`) into a unified adapter, enforces generation-aware memory caching with in-flight read deduplication, and provides a client-level operation lock for mutual-exclusion long tasks.

**Blocked by:** None — can start immediately.

**Status:** closed

- [x] Define the `Transport` interface supporting both single-execution (`execute`) and NDJSON streaming (`stream`).
- [x] Implement `MockTransport` in tests to simulate high-concurrency calls, stream event sequences, cancellation signals, and unexpected EOF/error states.
- [x] Implement `PaperForgeClient` core with generation/epoch tagging on all cache entries and in-flight reads, ensuring stale reads across a mutation boundary are discarded and never resurrect cached data.
- [x] Enforce read deduplication for `probe`, `search`, and detail queries, while guaranteeing that mutations (`runAction`, `setup`, `sync`, `promoteR`, `acceptProposal`) are never deduplicated.
- [x] Implement `OperationLock` within `PaperForgeClient` that records the active operation, gates concurrent long tasks, and releases deterministically across all terminal states (result, error, cancelled, spawn failure, decode error, EOF).
- [x] Implement `NodeProcessTransport` reusing `ManagedRuntime` for active Python interpreter resolution, `paperforgeEnrichedEnv()` for credential environment sanitization, and proven stdin `PAPERFORGE_STOP` escalation for cancellation.
- [x] Provide full Vitest unit test coverage for `PaperForgeClient` with `MockTransport` proving cache invalidation, anti-resurrection guards, lock semantics, and cancellation behavior.
