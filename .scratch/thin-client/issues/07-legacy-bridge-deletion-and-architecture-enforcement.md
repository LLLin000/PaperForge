# 07 — Legacy Bridge Deletion & Architecture Enforcement

**What to build:** Complete the final contract phase of the Expand–Contract refactor. Physically delete obsolete subprocess spawning helpers, legacy bridge functions, un-typed query methods, and ad-hoc status checks across the plugin codebase. Enforce that business UI code communicates solely through `PaperForgeClient`.

**Blocked by:**
- 06 — Library & Render Quality Domain Cutover

**Status:** ready-for-agent

- [ ] Delete all remaining direct `child_process.spawn("paperforge", ...)` and `child_process.execFile` calls inside view and component files.
- [ ] Remove deprecated client helpers in `services/python-bridge.ts`, `services/action-client.ts`, and `services/long-task-client.ts` that have been absorbed by `PaperForgeClient` and `NodeProcessTransport`.
- [ ] Audit the entire TypeScript codebase to confirm that no business presentation component directly reads canonical filesystem paths or infers capability states.
- [ ] Verify that allowed host-layer seams are strictly restricted to:
  1. Bootstrap/runtime adapter (`ManagedRuntime.status()`)
  2. Obsidian workspace leaf/context
  3. Opening Python-returned file paths
  4. Local UI preference persistence in `data.json`
- [ ] Run the complete plugin test suite (`npm test`), verify clean typechecking (`npm run build`), and execute a headless packaging check to confirm no broken import paths remain.
