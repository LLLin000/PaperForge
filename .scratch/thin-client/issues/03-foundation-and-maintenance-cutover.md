# 03 — Foundation & Maintenance Domain Cutover

**What to build:** Refactor the Foundation (Setup Journey, Runtime status) and Maintenance views to communicate exclusively through `PaperForgeClient`. Setup Journey becomes a pure consumer of `client.setup()` and `client.probe("installation")`; Maintenance becomes a pure consumer of the Deficit contract (`client.reconcile()`) and Action registry (`client.describeAction()`), removing frontend status calculation and hardcoded action buttons.

**Blocked by:**
- 01 — Client Core Engine & Transport Consolidation
- 02 — Python Surface Audit & Machine-Mode Normalization

**Status:** ready-for-agent

- [ ] Refactor Setup Journey to invoke `client.setup()` with user-collected configuration arguments, streaming the #137 NDJSON progress bar directly from the client stream.
- [ ] Connect Foundation module status and reload checks strictly to `client.probe("installation")`, eliminating ad-hoc python detection or direct settings inspection.
- [ ] Refactor the Maintenance view to populate items directly from `client.reconcile()` deficit outputs instead of deriving issues in TypeScript.
- [ ] Drive Maintenance action buttons and confirmation dialogs dynamically from `ActionDescriptor` properties returned by `client.describeAction()`, removing hardcoded action names and strings.
- [ ] Verify that completing any maintenance action triggers client-level cache invalidation and refreshes the view with updated probe truth.
- [ ] Add plugin Vitest tests demonstrating Setup Journey streaming and Maintenance deficit rendering over `MockTransport`.
