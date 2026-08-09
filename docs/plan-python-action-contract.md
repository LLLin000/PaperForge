# Python Action Contract — Implementation Plan

> Date: 2026-08-09
> Design: [Python Action Registry and Follow-up Execution Contract](https://github.com/LLLin000/PaperForge/blob/design/python-action-contract/docs/design-python-action-contract.md) (ACCEPTED / ARCHITECTURE FROZEN, `596b4dd8`)
> Parent map: [#135](https://github.com/LLLin000/PaperForge/issues/135)
> Design ticket: [#145](https://github.com/LLLin000/PaperForge/issues/145) (closed, frozen)
> Status: awaiting review gate. No production implementation yet.

## 0. Goal and success criterion

Implement the frozen design as one vertical cutover. The success criterion is not "the new runner works":

> **The new Python authority lands AND the old TypeScript authority is deleted.**

Functional tests going green while the old orchestrator coexists does not complete Python Core Authority. The deletion gate (Phase 4) is part of acceptance, not an afterthought.

The four implementation observations from the design review are first-class acceptance tests, not nice-to-haves:

| # | Observation | Proves |
|---|---|---|
| O1 | Scope actual side effects | A/B/C fixture, request `[A,B]`, only A succeeds → B and C Memory and Vector state untouched |
| O2 | Dependency actual causality | `memory.build` deliberately fails → no `embed.resume` appears anywhere in the result |
| O3 | Remote confirmation boundary | pending `embed.resume[A]`: 0 embedding provider calls before confirmation; exactly `{A}` after |
| O4 | Old authority disappears | after the journey is green, TS `_runIndexRefreshChain`, `ALLOWED_ACTIONS`, automatic/confirmation policy, `(verb,command)` dispatch are deleted — not shadowed |

## 1. Grounded starting state (verified 2026-08-09)

| Surface | Location | Scope-faithful today? |
|---|---|---|
| OCR derived rebuild | `paperforge/worker/ocr_rebuild.py:663` `run_derived_rebuild_for_keys(vault, keys, ...)` | Yes — already keys-scoped |
| OCR run | `paperforge/worker/ocr.py:2519` `run_ocr(vault, ..., selected_keys=None)` | Yes — keys-scoped when selected |
| Memory build | `paperforge/memory/builder.py:263` `build_from_index(vault)` → `_build_from_index_locked` | No — whole library; per-paper seam exists (`_incremental_units_only`, `_rebuild_paper_units(conn, key, ...)` at :755) |
| Embed build | `paperforge/commands/embed.py:334` `done_papers = [e for e in items if ocr_status == "done"]` | No — all OCR-done papers, no keys filter |
| Sync terminal follow-ups | `paperforge/commands/sync.py:128` `_run_terminal_followups`, `:148` `_run_memory_build` | Policy re-implemented in Python CLI (third executor) |
| Probe action vocabulary | `paperforge/commands/probe.py` `build_action_primary` (~24 call sites with `command=` strings) | No — second vocabulary with command strings |
| TS orchestrator | `paperforge/plugin/src/services/next-actions-orchestrator.ts:42` `ALLOWED_ACTIONS` (action_id→argv), `:77` `isAutomaticLocal`, `:85` `requiresConfirmation` | No — full policy re-implementation |
| TS settings dispatch | `paperforge/plugin/src/settings.ts:1642` `_runAllowedDispatch` (verb, command) matching | No — fragile string matching |
| OCR workspace chain | `paperforge/plugin/src/views/ocr-workspace.ts:884` `_runIndexRefreshChain` (called :865 with `successKeys.length`) | No — client-owned memory→embed orchestration |
| Audit goldens | `paperforge/architecture_audit/collectors/common.py:308` wrapper `sync.run_terminal_followups`; fixtures `golden_127_sync_embed.json`, `golden_126_ocr_rebuild.json` | Must be re-pinned when the wrapped symbols change |

Existing wire contract tests to keep green through Slice A/B: `tests/test_next_actions.py`, `tests/test_sync_next_actions.py`.

## 2. Phase order (seams and vertical acceptance first)

The design's §14 slices are re-sequenced: scope-faithful seams and the OCR vertical journey come before any client work. Nothing client-side is touched until O1–O3 pass on the Python side.

```text
Phase 0  Harness + fixtures                 (no production change)
Phase 1  Registry + runner + scope-faithful Memory/Embed seams   [design Slice A]
Phase 2  Chain runner + dependency-by-emission                   [design Slice B]
Phase 3  OCR vertical journey (O1, O2, O3)                       [design Slice C]
Phase 4  Client cutover + deletion gate (O4)                     [design Slice D]
Phase 5  Legacy producer cleanup + audit rules + lifecycle       [design Slice E]
```

Each phase has an exit criterion the reviewer can check independently; phases 1–3 must not be merged into one large PR.

## 3. Phase 0 — harness and fixtures

New test infrastructure, zero production code.

- Sandbox vault generator: papers A, B, C with PDFs, one deterministic OCR outcome per paper (A succeeds, B fails, C untouched — configurable).
- Mock embedding provider: env-gated (e.g. `PAPERFORGE_EMBED_PROVIDER=mock`), records every called key into a JSON log; fails loudly if any call happens without the mock.
- Assertion utilities: read `paperforge.db` rows and the vector DB per key; `assert_only_keys_touched(requested, affected)` implementing `affected_keys ⊆ requested_keys`.
- Fixture for forced `memory.build` failure (O2): one paper whose unit rebuild raises (corrupt artifact), asserting sync-style isolation.

Exit: fixture suite runs standalone; a deliberately broken scope assertion fails.

## 4. Phase 1 — registry, runner, scope-faithful seams (Slice A)

### 4.1 `paperforge/actions/` package

- `core` additions per design §4: `ActionSpec`, `AllScope`/`PapersScope`, `ActionRequest`, `ActionContext`, `PreflightResult` (availability + `availability_reason_*` + facts), `ACTION_REGISTRY` with import/test-time invariants (unique IDs, scope-kind known and faithfully enforced, remote/destructive ⇒ confirmation-required and never automatic, no command/argv anywhere).
- `ActionIntent` (trigger reason only) + `emit_next_action` hydration; wire stays `next_actions` schema v1.
- CLI `paperforge action list|describe|run` with exit codes 0/1/2/3; `--confirm <action_id>` exact-match; `--follow none|auto`; `--json`.
- Initial registry: only actions with real handlers — `library.sync`, `library.rebuild_index`, `ocr.run`, `ocr.rebuild_derived`, `ocr.diagnose`, `memory.build`, `memory.restore_backup`, `embed.build`, `embed.resume`. No placeholder entries.

### 4.2 Memory seam (must be scope-faithful before `memory.build` registers `papers`)

- Add `build_for_keys(vault, keys: list[str] | None)` in `paperforge/memory/builder.py`:
  - `keys=None` → current `build_from_index` behavior unchanged.
  - `keys` given → validate against canonical `formal-library.json` keys (unknown key → invalid scope, exit 2), filter items to those keys, and schedule through the existing per-paper `_incremental_units_only` / `_rebuild_paper_units` path so hashing, writer lock, and publication order (canonical hash advanced last) are preserved.
- `memory.build` handler calls `build_for_keys`; preflight rejects `papers` scope with zero keys.

### 4.3 Embed seam (must be scope-faithful before `embed.resume` registers `papers`)

- Extract the build core of `paperforge/commands/embed.py` (the `done_papers` loop, currently the largest function in the file) into `run_build(items, keys: list[str] | None, ...)`:
  - `keys=None` → current behavior (`done_papers` = all OCR-done).
  - `keys` given → `candidates = [e for e in done_papers if e["zotero_key"] in keys]`; every candidate's key must be in the requested set; per-key results recorded.
  - Keep the existing thread-pool/progress/resume machinery unchanged; the extraction is a pure filter + parameterization, no behavior change for the un-scoped path.
- `embed.resume`/`embed.build` handlers route through `run_build` with the request scope.

### 4.4 Scope-fidelity parity tests (per handler, design §15)

For `memory.build` and `embed.resume` with fixture A/B/C, request `[A, B]`, only A changed:

- memory: `paperforge.db` rows for B and C are byte-identical before/after (units, hashes, timestamps);
- embed: mock provider log shows calls only for keys in the requested set; `affected_keys ⊆ requested_keys` holds even when B fails mid-batch;
- `action describe memory.build --scope papers --key A --json` returns the descriptor; `--scope papers` with zero keys exits 2.

Exit: all parity tests green; full-library behavior of both commands unchanged (existing command tests pass untouched).

## 5. Phase 2 — chain runner and dependency-by-emission (Slice B)

- `run_follow_up_chain(root_result, context, *, mode)` per design §8.2: root = depth 0, children = depth 1, `depth > MAX_FOLLOW_UP_DEPTH (= 4)` rejected; per-invocation dedupe by `canonical_dedupe_key(action_id, scope)` with normalized (deduped, stable-sorted) keys; automatic-local-only execution; pending/skipped reported with reason codes; cancellation halts at the next action boundary.
- `sync.py`:
  - `_attach_next_actions` emits `memory.build` only (drop the sibling `embed.resume`; dependency-by-emission §8.1b).
  - `_run_terminal_followups` and `_run_memory_build` are replaced by the shared chain runner (sync becomes a client of the runner, keeping its try/except isolation so a follow-up crash cannot fail sync).
  - Parity: with the sandbox vault, `paperforge sync` produces the same successful memory follow-up as today.
- O2 test: force `memory.build` failure in the harness; assert the sync result and any chain output contain no `embed.resume` (the prerequisite failed, so no dependent action is emitted or pending).

Exit: `tests/test_next_actions.py` and `tests/test_sync_next_actions.py` pass unmodified; O2 green.

## 6. Phase 3 — OCR vertical journey (Slice C + O1–O3)

- Register `ocr.rebuild_derived` → `run_derived_rebuild_for_keys` (already keys-scoped), then emit `memory.build` for **successful** keys only (design §9: failed/skipped keys never enter a downstream mutating action).
- `memory.build` handler emits `embed.resume` for keys whose vector rows are now stale/missing — only on success, per dependency-by-emission.
- Full journey: `paperforge action run ocr.rebuild_derived --scope papers --key A --key B --follow auto --json`

Acceptance (each is a standalone test, not a screenshot):

- **O1**: request `[A, B]`, A OCR-rebuilds successfully, B fails → B and C Memory and Vector state untouched; result `data` carries per-key outcomes; `embed.resume` (if pending) scoped to `{A}`.
- **O2**: with `memory.build` failing, the final result contains no `embed.resume` — neither emitted, pending, nor in `next_actions`.
- **O3**: pending `embed.resume[A]` — mock provider log empty (0 calls) until `--confirm embed.resume`; after confirmation exactly `{A}` appears in the log; a second run with `--confirm` naming a different action exits 2 and calls nothing.

Exit: O1–O3 green against the sandbox vault.

## 7. Phase 4 — client cutover and deletion gate (Slice D + O4)

Only after Phase 3 is green:

1. Plugin `next-actions-orchestrator.ts`: delete `ALLOWED_ACTIONS`, `isAutomaticLocal`, `requiresConfirmation`, dedupe/depth logic. Replace with a thin loop: automatic → spawn `paperforge action run <id> --json`; confirmation-required → modal from descriptor (label/availability_reason/facts from `action describe`), then spawn with `--confirm <id>`. Duplicate-click suppression stays.
2. `ocr-workspace.ts`: delete `_runIndexRefreshChain`; the rebuild path becomes `action run ocr.rebuild_derived ... --follow auto`.
3. `settings.ts`: delete `_runAllowedDispatch` (verb, command) matching; dispatch by `action_id` for generic actions, keep client UX journeys keyed by id (setup steps, issue-draft modal, OCR controller).
4. `constants.ts` + `probe.py`: remove `command` fields from action surfaces (probe `action_primary`, dashboard action constants); descriptor comes from `action describe`.
5. **O4 gate**: repo-wide grep asserts — no `_runIndexRefreshChain`, no `ALLOWED_ACTIONS`, no `isAutomaticLocal`/`requiresConfirmation`, no `(verb, command)` dispatch table, no `command:` string in action wire — survive in `paperforge/plugin/src`. The plugin may only own presentation, transport, cancellation, and duplicate-click suppression.

Exit: plugin behavior parity on the sandbox vault (dashboard actions, OCR workspace, sync follow-ups) with zero action-policy code in TS; O4 greps green.

## 8. Phase 5 — legacy producers, audit rules, lifecycle (Slice E)

- Migrate or remove raw command-string `next_actions` producers: `commands/memory.py` (`"paperforge sync --rebuild-index"`), `paper_status.py`, `retrieve.py`, `search.py`, `retrieval/gateway.py` — to registered IDs or diagnostic data only.
- Architecture audit: update `collectors/common.py` wrapper specs (`sync.run_terminal_followups` is replaced by the chain runner wrapper; add action-dispatch wrappers and rules forbidding command-bearing action descriptors and client action-policy tables); re-pin goldens `golden_126_ocr_rebuild.json`, `golden_127_sync_embed.json` (their pinned symbols change in Phases 2–4).
- Lifecycle: promote the action contract capability in `ArchitectureContract.lifecycle` only after the full acceptance journey passes; update `PROJECT-MANAGEMENT.md` and the active queue per repo rules.

Exit: no action wire contains command text; all emitted IDs resolve to handlers; audit suite green with re-pinned goldens; contract promoted.

## 9. Risks

- **Embed extraction** (`embed.py` build core) is the largest single change; the un-scoped path must stay behavior-identical (existing embed tests are the guard). If extraction proves risky, land it as its own PR before Phase 1 acceptance.
- **Handler crash isolation**: in-process handlers must keep sync's existing try/except pattern so a follow-up crash cannot fail the parent command (design §6).
- **Mock provider realism**: O3 must not accidentally exercise the real provider; the mock is fail-closed (any call without the env gate aborts).
- **Audit goldens drift**: any phase touching `_run_terminal_followups`/`run_derived_rebuild_for_keys` must re-pin goldens in the same commit (Phase 5 lists it; Phases 2–4 must not silently break the audit suite).
- **Windows**: all spawns use `execFile`/`spawn` with `shell: false` and `python -m paperforge action run ...`; no argv concatenation (design §12.1).
- **Wire compat**: `next_actions` v1 stays byte-compatible until Phase 4; the plugin consumes descriptors via `action describe`, not by re-deriving policy.

## 10. Review gate

The reviewer checks, in order:

1. Phase 0 fixtures exist and a broken scope assertion fails (harness honesty);
2. Phase 1: `memory.build`/`embed.resume` scoped invocations touch only requested keys (subset semantics) — before any plugin change;
3. Phase 2: O2 green — forced memory failure leaves no `embed.resume`;
4. Phase 3: O1–O3 green on the sandbox vault;
5. Phase 4: O4 greps green — old TS authority deleted, not coexisting;
6. Phase 5: audit goldens re-pinned, contract lifecycle promoted, project records updated.

Only after gate 6 is the implementation considered complete under the §15 design acceptance.

## 11. Amendment — reconciliation integration (#159, accepted)

The reconciliation design (`docs/design-materialization-reconciliation.md`, frozen) amends the phases above:

**New prerequisite slice (before Phase 1): digest lineage publish.**
Persist per-layer derived digests at the existing publish commit points: OCR identity = `result_hash`; retrieval identity = `hash(OCR identity + retrieval_policy_version + produced units digests)`; vector identity = `hash(retrieval identity + embedding identity)`. Add `paperforge probe lineage --json`; missing identity fails closed (`unknown`, never `stale`). Generation/run counters are diagnostics only.

**Phase 1 additions:**
- `reconcile(keys)` pure module: observe → global repair frontier → per-paper minimal repair frontier → scope merging by canonical action → emit ActionIntents.
- Single channel: intents project onto the existing `PFResult.next_actions` wire; no second `intents` wire; the plugin never loops intents.
- Handlers publish-then-reconcile; reconcile decides the operation only (`embed.resume` per-paper vs `embed.build` global substrate); cost/confirmation come from the registry.
- Global-first: one global intent while the substrate is incompatible; per-paper facets `blocked_global`.

**Phase 3 additions:**
- Break-recovery journey: crash between chain steps → `reconcile` re-derives the identical intent.
- O2 extended: forced `memory.build` failure → `reconcile` re-emits `memory.build`, never `embed.resume`.
- Reader fail-closed test: mismatched or `unknown` lineage is never served.

**Phase 4 additions:**
- Plugin timer becomes `reconcile(all)` — scope-only trigger, no state scanning, per #158.
- **Deletion list (old recommendation producers become projections or are deleted):**
  - `paperforge/worker/asset_state.py` — `compute_next_step` and the fix-path logic of `compute_health` retire to projections of reconcile output, or are deleted (lifecycle computation stays);
  - OCR maintenance `_recommended_action` / `compute_display_fields` — consume reconcile output instead of deciding redo/rebuild/configure;
  - any remaining recommended-action computation in probe/maintenance surfaces;
  - single-producer grep-assert: no materialization-repair recommendation outside reconcile.

**New tests:** unknown-lineage fail-closed (legacy vaults get no mass rebuild); global-first (one `embed.build`, per-paper `blocked_global`); scope merge (100 keys → one `memory.build` intent); not-a-retry (failed action not re-fired on identical facts); change-prune (identical digest → no downstream rebuild).
