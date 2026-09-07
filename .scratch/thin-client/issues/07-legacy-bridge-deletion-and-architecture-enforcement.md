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

## Stage 2 — step 4 contract corrective (2026-09-06, reviewer-verified findings)

- **P1 mutation invalidation contract completed:** `authSetSecret` and `memoryRestoreBackup` now invalidate the cache in `finally`, same as `configSet`/`configMigrate`/`embedMigrate` — no caller may be relied on to compensate. The real-bug scenario is pinned: `credentialAvailable` cached `unavailable` (60s) → `authSetSecret` → next `credentialAvailable` MUST re-hit the transport (and the same for `memoryStatus` across `memoryRestoreBackup`). A cached `describeAction` unavailability after saving a key can no longer block a subsequent Run.
- **P1 legacy credential migration split by responsibility:** `secret-storage.migrateLegacySecret` no longer holds ANY backend protocol knowledge — `MigrationSpawn` (spawn/pythonPath/pythonArgs/vaultPath/env + the `auth set --stdin --json` argv) is deleted; the module now receives a narrow `writeCredential(kind, value)` capability and owns only the host side (which legacy SecretStorage ids exist, how to clear them). Settings binds the capability to `client.authSetSecret(kind, value, { replace: false })` — honoring the frozen safety semantics: a stale host copy must never overwrite a live keyring value. `authSetSecret` gained `options?: { replace?: boolean }` (default true = user Save; contract test asserts the migration shape emits argv WITHOUT `--replace`). A source-level regression pins the boundary: secret-storage must contain no `child_process`/`"-m"`/`MigrationSpawn` — backend argv knowledge lives only in PaperForgeClient.
- **Gate:** `settings.ts` leaves `HOST_SEAMS` — it now has ZERO child-process sites (the DI spawn passthrough died with the split). Also: settings' `child_process` import removed entirely; `migrateLegacySecret` is a static import now (no runtime-selected module).

## Stage 2 — step 4: Settings semantic commands → typed client, per-site ratchet (2026-09-06, done)

Per the reviewer's principle — classify each site, never target the number:

| Site | Classification | Action |
|---|---|---|
| `_runUpdateAction` execFile (`action run foundation.update --confirm`) | backend semantic | → `client.runAction({action_id:"foundation.update", scope:all, confirm})` |
| `_callPython` spawn+execFile (generic runner; credentialType env-resolution branch) | duplicated semantic authority | **deleted** — only callers were restore-backup + embed migrate; both got typed methods |
| `memory restore-backup` | backend semantic | → `client.memoryRestoreBackup()` (`["memory","restore-backup","--json"]`, 30s) |
| `embed migrate` | backend semantic (mutation) | → `client.embedMigrate()` (`["embed","migrate","--json"]`, 600s, cache-invalidating) |
| `runtime-health` fire-and-forget warm-up | backend semantic read | → `client.runtimeHealth()`; `_refreshSnapshots` keeps envelope-text semantics |
| `_authSetSecret` spawn (`auth set <kind> --stdin --replace --json`) | backend semantic, security-sensitive | → `client.authSetSecret(kind, secret)` — secret travels ONLY via `ExecuteOptions.stdin`; argv never carries it (contract test pins both directions) |
| `_runSetupPython` spawn | **dead code** (zero production callers since the T03 setup cutover) | deleted |
| `deps.spawn` passthrough in `_migrateLegacyCredentials` | **host seam** — DI contract into `secret-storage.migrateLegacySecret`, zero semantic argv assembly | kept; reclassified `LEGACY_RATCHET` → `HOST_SEAMS` |

**Ratchet: `settings.ts` 7 → 1, and the 1 is a host seam (DI passthrough), not legacy debt.** Client gained `_executePfResult(argv, ExecuteOptions)` (stdin/timeout pass-through; PFResult semantics unchanged) and 4 typed methods. `_callPython`'s credentialType env-resolution branch died with it — env assembly is NodeProcessTransport's job.

Test reconciliation: two capability-state `_callPython` plumbing tests deleted (managed-path resolution is transport-owned, covered by node-transport tests); module-detail update/migrate/vector-credential tests re-homed onto the client seam; the sync-failure test drops its dead `_callPython` override (modern equivalent: transport rejection → sentinel 1 forwarded). Client contract tests added for all 4 new typed surfaces (28 total in the contract describe file).

## Stage 2 — step 3 contract corrective (2026-09-06, reviewer-verified findings)

- **P1 fake canonical `ocr.redo` removed:** `settings._runAllowedDispatch` no longer routes `verb==="redo" || actionId==="ocr.redo"` — the Python registry has no `ocr.redo` primary (#99: internal-only), so encoding it in the thin client was re-introducing legacy semantic knowledge. `_dispatchOcrAction` mode narrowed to `"run" | "rebuild"`; the redo label/notice/confirm-token branches are gone. A stale `ocr.redo` envelope now falls through to the frozen unknown-pair invariant: **Notice → re-probe, NEVER substitute** (regression pins it: confirm modal still presents per envelope policy, then zero dispatches + unknown-action notice). The user-facing Redo affordance in the OCR Workspace keeps using the canonical `ocr.run` descriptor (unchanged, T04).
- **P1 `main.requestOcrRun` production-entry regression added** (`tests/client/main-ocr-run-cutover.test.ts`, 4 cases, shared client mocked directly — no child_process): ① exact wiring `{action_id:"ocr.run", scope:{kind:"all"}, confirm:"ocr.run"}` + item_result failed-key "B" surfaces in the notice + `_autoSync` settle; ② active-operation guard → zero dispatches, no settle; ③ cancelled event → stopped notice + settle; ④ registry unavailability → notice carries `availability_reason`, not a generic failure.
- **P2 availability reason surfaced:** failure detail order in BOTH `main.requestOcrRun` and `settings._dispatchOcrAction` is `failedKeys → payload.availability_reason → payload.error.message → exit code` — command-palette users with a missing token see `ocr.credential_missing`, not bare "OCR failed" (legacy controller parity).
- Found and fixed during the corrective: the then-branch settle (`_refreshAllReadModels` + `display`) had been dropped from `settings._dispatchOcrAction` by the first corrective pass — the settle regression ("clears activity and re-probes all after settle") now guards it.

## Stage 2 — step 3: OCR live callers → shared client, `OcrProcessController` deleted (2026-09-06, done)

Leaf→root order per reviewer: migrate the live callers FIRST, keep Stop/operation ownership, then physically delete the controller.

- **`main.requestOcrRun()`** (command palette + Settings run dispatch + Dashboard) → `client.runAction({action_id:"ocr.run", scope:{kind:"all"}, confirm:"ocr.run"})` with #137 event mapping (`start/phase/progress/item_result` → `_ocrProgress`; failed keys aggregated from non-succeeded item_results; `cancelled` event → stopped notice). Client-side confirm modal kept; already-running guard → `client.isOperationActive()`; settle → `_autoSync` (unchanged cadence).
- **`settings._dispatchOcrAction(mode)`** — run still delegates to `plugin.requestOcrRun(true)`; rebuild → `ocr.rebuild_derived` (scope all); redo → `ocr.redo` + confirm token (the module-level confirm modal already ran). Envelope activity overlay + `_ocrProgress` mapping preserved; settle → `_refreshAllReadModels()`.
- **Stop ownership** — Settings OCR Stop button → `client.isOperationActive() ? client.cancelActiveOperation()` (single OperationLock owner, T05 semantics). Cooperative-stop protocol itself stays Python-side (`#137` `stop_check`, covered by Python tests); the TS side never wrote stdin tokens.
- **Credential fail-closed** — moved from the controller's `needsCredential` callback to where it always belonged: the Python action registry (`describeAction.availability`), consumed by `client.runAction`'s gate. Tests assert the unavailable descriptor produces a structured rejection, no transport call, and an activity reset.
- **Deleted:** `services/ocr-process-controller.ts` (second spawn owner: its own argv assembly, `PAPERFORGE_STOP` stdin writes, credential resolution, NDJSON parsing) + `tests/ocr-process-controller.test.ts` (14 tests of the dead seam — the surviving behaviors are covered client-side: exact-argv, gating, Stop ownership, item_result aggregation) + main's `ocrProcessController` field/construction + settings' `OcrProcessOutcome` import + controller-era `_ocrBuffer/_ocrStderr/_ocrWasStopped` state writes.
- **Gate:** `services/ocr-process-controller.ts` leaves `LEGACY_RATCHET` (1 test-seam spawn site) and enters `TOMBSTONES`.
- Also carried: reviewer's P2 from step 2 — `configMigrate` regression now asserts the runtime-returned DTO equals the real Python wire (not just fixture shape + argv).

## Stage 2 — step 2 contract corrective (2026-09-06, reviewer-verified findings)

- **P1 configMigrate DTO vs Python wire:** the carried-over type lie from legacy config-client was not allowed to survive the typed cutover. `ConfigMutationData` split into `ConfigSetData` (per-field: `changed` + `field`) and `ConfigMigrateData` (snapshot meta + `changed` + `dry_run` + `warnings`, never `field`) — matching the real `config migrate` machine output. The regression now asserts the full real wire DTO, not a fixture-shaped subset.
- **P1 `_executePfResult` never saw real rejections:** the first fail-closed hardening only handled a transport that RESOLVES an ok:false JSON — but `NodeProcessTransport.execute` rejects non-zero exits, and the Python config contract emits a structured ok:false PFResult on stdout WITH rc=1/2, so the authority reason was being lost to a generic "exit code 1" error (a real regression vs legacy config-client, which JSON-parsed err stdout). Fixed at the layer split the reviewer prescribed: **Transport owns process/exit semantics; PaperForgeClient._executePfResult owns PFResult machine-protocol semantics.** On a transport rejection the client inspects `err.stdout`: parseable PFResult ok:false → throw the authority message; parseable PFResult ok:true despite rc≠0 → protocol contradiction, transport error wins; no/parsing-failed stdout → transport error wins. `Transport.execute()`'s global nonzero-reject contract untouched; no Python change; no public generic API added.
- Regression set on the real rejection path: rc=1 + structured stdout → `config.migration_required` survives; rc=1 + ok:true stdout → contradiction, transport error; rc=1 + no stdout → transport error; resolved ok:false → fail closed (MockTransport still exercises this branch).

## Stage 2 — step 2: `config-client` dissolved (2026-09-06, done)

Per the reviewer's decomposition brief, `config-client.ts` (428 lines) was split by **actual responsibility**, then deleted — the goal was eliminating duplicate semantic authority, not shrinking a file count:

- **probeAll semantic read** → `PaperForgeClient.probeAll()` (existing); return type corrected to the true bare envelope `ProbeAllEnvelope {schema_version, module:"all", modules}` (the old cast `Record<string, ProbeEnvelope>` was a type lie). Settings' `_refreshAllReadModels` invalidates the shared cache first (`client.invalidateCache()`) so a refresh can never serve a 60s-stale probe.
- **credential/config typed queries** → Python authority surface already existed (`auth status <svc> --json`, `config <verb> --json`), so per the brief these became **client typed methods, no Python contract change needed**: `credentialAvailable("embedding"|"ocr")`, `configList`, `configValidate`, `configMigrate(dryRun)`, `configSet(key, value)` (mutations invalidate the cache), `embedStatus()`, `memoryStatus()`. Vault path, python resolution, env sanitization, and PFResult unwrapping now happen exactly once, in `NodeProcessTransport`/`PaperForgeClient`.
- **runtime/bootstrap-only helper** — `config-client`'s own `invokePaperForge` was a second generic argv wrapper with a second `resolvePythonExecutable` call and its own `execFile`/`windowsHide` options; that is precisely the duplicated semantic authority, deleted, not re-homed.
- **Shared-root hardening:** `_executePfResult` is now fail-closed — a structured `ok:false` PFResult throws with the authority's message; previously every PFResult-based read silently received `null` data on authority rejection.
- **Dead weight removed with the file:** unused `configGet/configUnset/configPaths/paperContext/queryOcrPapers` standalone, the module-scope `_detailCaches`/`refreshAll`/`getDetailCache`/`invalidateAll` cache nobody read, `ConfigClientError`, and the `--json` double-append in `auth status` argv.
- **Gate evidence:** `services/config-client.ts` leaves `LEGACY_RATCHET` (2 execFile sites) and enters `TOMBSTONES`; the argv-contract regression from `read-model-client.test.ts` was re-homed onto the unified seam in `tests/client/paperforge-client.test.ts` (6 cases: exact argv for list/set/migrate dry+real/validate/auth-status, mutation invalidation, TTL caching, ok:false fail-closed).
- Consumers cut over: `main.ts` (configValidate/embedStatus/configMigrate×2/configList×2), `settings.ts` (configSet×5, memoryStatus, embedStatus, credentialAvailable("embedding"), invalidateCache+probeAll), `views/dashboard.ts` (credentialAvailable("ocr") via `_getClient()`).
- Ticket 06 note: `expectOnlyClientSync` now admits `auth` on the unified transport — the OCR-token render read previously never reached any transport because config-client resolved python (and failed) outside the seam; now it is an honest transport call.

## Stage 2 — step 1: `main._autoSync` (2026-09-05, done)

- `main._autoSync` routes through the shared `PaperForgeClient.sync()` and hands the SAME PFResult document to the SAME `orchestrateFromSync` bridge as Settings/Dashboard (`resolveCommand: () => this._getPythonCommand()`). main never assembles sync argv, never spawns for sync, never duplicates next_actions policy, never creates a second client; `NodeProcessTransport` owns the redacted env.
- Semantics preserved: `_autoSyncRunning` dedup (concurrent ticks collapse to one sync), timer cadence untouched, failure cleanup resets running-state/`_memoryStatusText`, and `ok:false`/throw paths skip refresh + follow-ups.
- **First architecture-ratchet evidence:** `main.ts` provenance snapshot lowered **2 → 1** (only the dashboard-tool dispatcher `execFile` remains); the gate enforces it and the regression covers the semantics (4 cases: exact sync argv + bridge handoff, concurrent-tick dedup, transport failure, structured `ok:false`).
- Evidence corrective (reviewer-verified): the bridge MODULE is mocked, not child_process — the success case asserts `orchestrateFromSync` receives `JSON.stringify(SYNC_RESULT)` (the same parsed PFResult document's semantic content; `client.sync()` JSON.parses the backend stdout, so raw bytes are not preserved by design) together with `{ vaultPath: "/vault", resolveCommand: expect.any(Function) }`, and both the transport-failure and structured `ok:false` cases assert zero refresh and zero follow-up calls. Direct child-process usage of main.ts stays enforced by the provenance gate (snapshot = 1).

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
