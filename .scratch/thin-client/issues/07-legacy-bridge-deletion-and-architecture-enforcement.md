# 07 — Legacy Bridge Deletion & Architecture Enforcement

**What to build:** Complete the final contract phase of the Expand–Contract refactor. Physically delete obsolete subprocess spawning helpers, legacy bridge functions, un-typed query methods, and ad-hoc status checks across the plugin codebase. Enforce that business UI code communicates solely through `PaperForgeClient`.

**Blocked by:**
- 06 — Library & Render Quality Domain Cutover

**Status:** in progress — stage 1 corrective complete (authority gate + exact-snapshot ratchet + committed census)

**Round-2 gate corrective (2026-09-05):** Gate B upgraded from name-matching to true **binding provenance** — `spawn as launch`, `cp.spawn`, `const { fork: runFork } = require(...)`, `require(...).spawn(...)` and fallback-chain aliases all resolve to child_process bindings; unrelated objects (`deps.spawn`, `someObject.exec`) and call-result handles (`const child = spawn(...)` then `child.on()`) never count. Synthetic regressions pin every provenance form. The provenance gate immediately caught 4 real spawn sites the regex gate under-counted (ocr-process-controller `spawnFn(...)`, python-bridge `execSync`/`exe`×2/`sp` fallback aliases) — snapshots corrected to 1 and 8 respectively.

## Stage 1 (2026-09-05) — done (superseded wording below replaced by the corrective contract)

- [x] Delete `services/ocr-maintenance-ui.ts` — zero src importers (obsoleted by probe-owned maintenance projections); its dedicated test and stale `vi.mock` blocks removed.
- [x] Add the architecture gate (`tests/client/architecture-boundaries.test.ts`) — final semantics after the corrective: **Gate A** child_process import authority via TS-AST provenance, allowed only in the exact listed files (`client/node-transport.ts` transport root, `services/long-task-client.ts` transport streaming stack pending merge, `services/managed-runtime.ts` listed host seam, plus the legacy ratchet files); **Gate B** exact-snapshot ratchet (`actual === frozen`) resolved by binding provenance (named/aliased imports, namespace members, all require forms, fallback-chain aliases such as `const execSync = _execFileSync || execFileSync`) — never by bare function-name regex, and never counting call-result handles like `const child = spawn(...)`; **Gate C** tombstones for absorbed surfaces.
- [x] Packaging check: `npm run build` clean (no broken import paths); full suite green.

## Remaining surfaces (each needs a client method or a UI decision first)

- `views/dashboard.ts` (3 sites): `_runAction` doctor/repair/needsKey context commands (`spawn` 3012, 3491), `execFileSync` in `_fetchVersion` (248). Needs `client.doctor/repair` typed methods + a client-side stats method before deletion; the Stats view itself still aggregates via `dashboard --json`/`status --json`.
- `views/modals.ts` (3 sites): setup/install flows (295, 953) and one `execFile` (1259). Install journeys need a client `setup`-family reroute or explicit host-seam classification.
- `settings.ts` (7 sites): `_callPython` (477) + runtime-health `_refreshSnapshots` (2510), `_runUpdateAction` (1946), OCR legacy dispatch (2497), auth-secret flows (2616, 3948, 4046). `_callPython` call sites must each map to a typed client method or a documented host seam.
- `main.ts` (2 sites): convergence `_autoSync` (427) and one install/exec path (277). `_autoSync` should route through `client.sync()` + the shared orchestrator.
- `services/config-client.ts` (2 sites): `probeAll`/credential queries still consumed by settings `_refreshAllReadModels` and dashboard global status rows — reroute to `client.probeAll()`/typed queries, then delete.
- `services/ocr-process-controller.ts` (LIVE callers): `main.requestOcrRun()` → `controller.start(...)` drives the `paperforge-ocr` command and Settings reads `plugin.ocrProcessController`; reroute both through `client.runAction("ocr.run")` with production-entry tests BEFORE deleting the controller. `services/embed-build-controller.ts` (2 sites): still imported by main/settings; audit every importer before deletion. Neither is dead wiring.
- `services/action-client.ts` + `next-actions-*`: alive — the follow-up bridge is the sanctioned next_actions consumer; reroute `runActionRequest` through `PaperForgeClient.runAction` (or classify as host seam) before deletion.
- `services/python-bridge.ts`: `paperforgeEnrichedEnv`/runtime resolution used by node-transport (core); only `runSubprocess`/git-detection helpers become dead once the surfaces above are rerouted.

## Stage 1 corrective (2026-09-05) — gate hardened to authority + exact snapshot

Reviewer findings, all closed (no business code touched):

- **Exact-snapshot ratchet (was max-baseline):** every gate entry now asserts `actual === frozen` (Gate B). Deleting a call forces the snapshot down in the same commit; debt can never silently regrow.
- **Import authority gate (Gate A, TS AST via the `typescript` compiler API):** importing/requiring `child_process` is legal only in the exact listed files — any new importer fails the suite. The over-broad `client/**` directory exemption is gone: authority owners are exactly `client/node-transport.ts` (transport root) and `services/long-task-client.ts` (transport streaming stack, snapshot-frozen, must merge into node-transport before 07 closes). Regex call-name matching is replaced by AST call-expression counting over `{spawn, exec, execFile, execFileSync, spawnSync, execSync, fork}` (identifier + property access), so `spawn as launch` / `exec` / `fork` styles are covered.
- **No blanket file exemptions:** `secret-storage.ts` needs none — its `deps.spawn` is an injected DI seam with no child_process import, so the authority gate alone proves it clean; `managed-runtime.ts` is now a listed HOST_SEAM (bootstrap/runtime adapter: imports `cpExecFile`/`cpExecFileSync` and injects them as DI defaults, zero direct call sites) instead of an undocumented exemption.
- **Census correction (OCR controller is LIVE, not dead wiring):** `main.requestOcrRun()` → `ocrProcessController.start(...)` is still driven by the `paperforge-ocr` command and Settings reads `plugin.ocrProcessController` for its stop button. Stage 2 must first route `main.requestOcrRun` and the Settings OCR CTA through `client.runAction("ocr.run")` with production-entry tests, THEN delete `OcrProcessController`. `EmbedBuildController` likewise requires a full main/settings importer audit before deletion — neither may be direct-deleted.
- **Census is committed** (this file): the surface→prerequisite table below is the authoritative handoff for the next session.

Stage 2 execution order (leaf callers → transport root; each step lowers the snapshot): 1) `main._autoSync` → `client.sync()` + shared orchestration; 2) config-client read surfaces → `client.probeAll()`/typed queries, delete duplication; 3) OCR main/settings live callers → `client.runAction`, then delete `OcrProcessController`; 4) Embed controller residual callers → shared client, delete; 5) Dashboard `_runAction`/stats/version → typed methods/probe DTO; 6) Settings `_callPython` callers, one typed migration each; 7) modals setup/bootstrap seams → classify true host seam vs backend command; 8) collapse `action-client`/`next-actions-bridge`/`long-task-client`/`python-bridge` remnants into the transport root.

- [ ] Delete all remaining direct `child_process.spawn("paperforge", ...)` and `child_process.execFile` calls inside view and component files.
- [ ] Remove deprecated client helpers in `services/python-bridge.ts`, `services/action-client.ts`, and `services/long-task-client.ts` that have been absorbed by `PaperForgeClient` and `NodeProcessTransport`.
- [ ] Audit the entire TypeScript codebase to confirm that no business presentation component directly reads canonical filesystem paths or infers capability states.
- [ ] Verify that allowed host-layer seams are strictly restricted to:
  1. Bootstrap/runtime adapter (`ManagedRuntime.status()`)
  2. Obsidian workspace leaf/context
  3. Opening Python-returned file paths
  4. Local UI preference persistence in `data.json`
- [ ] Run the complete plugin test suite (`npm test`), verify clean typechecking (`npm run build`), and execute a headless packaging check to confirm no broken import paths remain.
