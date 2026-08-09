# Python Action Registry and Follow-up Execution Contract

> Date: 2026-08-09  
> Decision ticket: [#145](https://github.com/LLLin000/PaperForge/issues/145)  
> Parent map: [#135](https://github.com/LLLin000/PaperForge/issues/135)  
> Research: [#154](https://github.com/LLLin000/PaperForge/issues/154)  
> Scope: architecture and migration design only; no production implementation.

## 0. Decision

PaperForge will use one declarative Python action registry and one generic Python runner.

```text
Python capability read model
  -> ActionIntent(action_id, scope, reason, contextual effects)
  -> registry hydration
  -> versioned ActionDescriptor (no command or argv)
  -> CLI / Obsidian / Agent presentation
  -> paperforge action run <action_id>
  -> Python preflight + confirmation gate + handler
  -> PFResult + registered next_actions
  -> Python follow-up runner
```

The registry is a frozen table of data plus plain callables. It is not a plugin system, class hierarchy, daemon, workflow engine, or second control plane.

Python owns:

- stable action identifiers;
- action metadata and handler bindings;
- accepted scope shapes;
- availability and preflight validation;
- impact, cost, reversibility, confirmation, and automatic-execution policy;
- generic dispatch;
- per-invocation follow-up dedupe and depth limits;
- every emitted `next_actions` descriptor.

Clients own only:

- rendering labels, reasons, effects, and progress;
- collecting explicit user confirmation;
- passing the confirmation back to Python;
- invoking the one generic action command without a shell;
- cancellation/progress transport for the running process;
- duplicate-click suppression within the client UI.

Clients never map action IDs to command-specific argv, reclassify safety, decide which follow-ups are automatic, or dispatch domain handlers themselves.

## 1. Why this design

Current code has multiple action vocabularies and policy engines:

1. `paperforge/core/next_actions.py` contains metadata for `memory.build` and `embed.resume`.
2. `paperforge/plugin/src/services/next-actions-orchestrator.ts` repeats the allowlist, argv mapping, automatic/confirmation policy, dedupe, and depth logic.
3. `paperforge/commands/sync.py` contains another hard-coded terminal follow-up dispatcher.
4. `paperforge/commands/probe.py` emits a larger `action_primary` vocabulary with command strings.
5. `paperforge/plugin/src/settings.ts` dispatches probe actions by `(verb, command)` pairs.
6. `memory.py`, `paper_status.py`, `retrieve.py`, `search.py`, and retrieval gateway paths still emit legacy command-string recommendations.

This is the exact policy duplication prohibited by #135 and #154. Stable IDs already exist, but execution still depends on client-owned command knowledge.

The smallest seam that removes the duplication is:

```text
ActionSpec table -> generic runner -> existing domain functions
```

Handlers remain thin adapters over existing command/domain functions. The action layer does not absorb OCR, memory, embedding, configuration, or setup logic.

## 2. Alternatives considered

### A. Functional descriptor table plus handlers

A frozen metadata table and plain handler functions. Smallest surface and easiest migration.

### B. One class per action with `plan()` and `execute()`

This gives a strong preflight/execution split, but adds a class hierarchy for roughly a dozen real operations. The useful gate does not require objects. It also invites speculative `undo`, `retry`, and lifecycle methods.

### C. Declarative `ActionSpec` table plus generic runner

This combines A's small surface with explicit preflight, handler, and chain hooks. Metadata is one authority; handlers are ordinary functions; the runner is the only policy engine.

**Decision: C.**

B is an upgrade path only if action-specific behavior later requires materially different lifecycle methods. Action count alone is not sufficient reason.

## 3. Contract boundaries

### 3.1 Action ID means executable operation

An `action_id` names a stable Python operation, not:

- a display label;
- a CLI spelling;
- an Obsidian destination;
- the reason the operation was suggested;
- a particular warning state.

Different reasons that execute the same operation use the same ID. For example, initial build, stale rebuild, and schema recovery all use `memory.build`; the reason and effect facts differ in the descriptor.

### 3.2 UI navigation is not an action

Retrying a probe, opening settings, opening a note, or opening an issue-draft view is client navigation/read transport, not a backend action unless Python actually performs an operation.

Probe envelopes may therefore contain either:

```json
{"action": {"action_id": "memory.build", "scope": {"kind": "all"}}}
```

or a separate presentation hint:

```json
{"client_hint": {"destination": "settings.memory"}}
```

`client_hint` values never enter the action registry or `next_actions`.

### 3.3 Action intent and descriptor are different types

Domain producers emit only an intent:

```python
@dataclass(frozen=True)
class ActionIntent:
    action_id: str
    scope: ActionScope
    reason_code: str
    reason: str
    preservation_facts: tuple[str, ...] = ()
    replacement_facts: tuple[str, ...] = ()
```

They cannot set cost, impact, confirmation, automatic execution, interruptibility, or handler details.

The registry hydrates the intent into a descriptor for the wire. This prevents a producer from accidentally or deliberately weakening policy.

## 4. Python interface

### 4.1 Core types

```python
ActionHandler = Callable[["ActionContext", "ActionRequest"], PFResult]
ActionPreflight = Callable[["ActionContext", "ActionRequest"], "PreflightResult"]

@dataclass(frozen=True)
class ActionSpec:
    action_id: str
    label_code: str
    description_code: str
    handler: ActionHandler
    preflight: ActionPreflight
    scope_kinds: tuple[str, ...]
    cost: Literal["local", "remote_possible"]
    impact: Literal["read_only", "mutating", "destructive"]
    reversible: bool
    confirmation: Literal["none", "required"]
    automatic: bool
    interruptible: bool

@dataclass(frozen=True)
class AllScope:
    kind: Literal["all"] = "all"

@dataclass(frozen=True)
class PapersScope:
    keys: tuple[str, ...]
    kind: Literal["papers"] = "papers"

ActionScope = AllScope | PapersScope

@dataclass(frozen=True)
class ActionRequest:
    action_id: str
    scope: ActionScope

@dataclass(frozen=True)
class ActionContext:
    vault: Path
    config: ConfigSnapshot
    paths: ResolvedPaths

@dataclass(frozen=True)
class PreflightResult:
    availability: Literal["available", "unavailable", "busy"]
    reason_code: str
    reason: str
    preservation_facts: tuple[str, ...] = ()
    replacement_facts: tuple[str, ...] = ()
```

Action-specific arbitrary `argv` or untyped `args` are deliberately absent. An operation that cannot be identified by `action_id + scope` remains on its typed command contract until it has a real typed request. Generic action dispatch must not become an unvalidated CLI tunnelling layer.

### 4.2 Registry

```python
ACTION_REGISTRY: Mapping[str, ActionSpec] = {
    "library.sync": ActionSpec(...),
    "library.rebuild_index": ActionSpec(...),
    "ocr.run": ActionSpec(...),
    "ocr.rebuild_derived": ActionSpec(...),
    "ocr.diagnose": ActionSpec(...),
    "memory.build": ActionSpec(...),
    "memory.restore_backup": ActionSpec(...),
    "embed.build": ActionSpec(...),
    "embed.resume": ActionSpec(...),
}
```

The initial registry contains only operations with a real Python handler. It must not contain placeholder, client-only, or "not implemented" entries.

The registry is validated at import/test time:

- IDs are unique and match `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$`.
- Every spec has exactly one handler and one preflight callable.
- Every allowed scope kind is known.
- `remote_possible` actions require confirmation and cannot be automatic.
- `destructive` actions require confirmation and cannot be automatic.
- irreversible actions require confirmation and cannot be automatic.
- automatic actions are local, non-destructive, and require no confirmation.
- no descriptor, handler binding, or emitted wire value contains a command string or argv.

The registry may use local imports inside handler functions to avoid command/core import cycles. It must not use dynamic module discovery, decorators with import-order behavior, entry points, or configuration-driven registration.

### 4.3 Preflight

Every invocation performs preflight immediately before dispatch. A cached probe descriptor is advisory and never authorizes execution.

Preflight validates:

- current availability;
- accepted scope kind;
- non-empty paper keys where required;
- current locks/build state;
- required canonical configuration and credentials;
- preservation and replacement facts needed for confirmation.

It consumes existing capability/config/credential read models from #140/#142/#138. It does not create another persistent state source.

There is no separate `plan` object or plan file. `action describe` and confirmation-required responses serialize the current descriptor generated from the same spec and preflight result.

## 5. Wire contract

### 5.1 Action descriptor

```json
{
  "schema_version": 1,
  "action_id": "embed.resume",
  "label_code": "action.embed.resume",
  "description_code": "action.embed.resume.description",
  "scope": {"kind": "papers", "keys": ["ABCD1234"]},
  "availability": "available",
  "reason_code": "vector.pending_after_memory_build",
  "reason": "1 paper is ready for remote embedding",
  "cost": "remote_possible",
  "impact": "mutating",
  "reversible": true,
  "confirmation": "required",
  "automatic": false,
  "interruptible": true,
  "preservation_facts": ["Existing vector rows remain available until replacement commit"],
  "replacement_facts": ["Embedding provider calls may incur remote cost"]
}
```

Forbidden keys include `command`, `cmd`, `argv`, `shell`, `executable`, and command fragments embedded in another field.

The English `reason` and fact strings are safe fallbacks for CLI and Agent consumers. `label_code`, `description_code`, and `reason_code` allow Obsidian to localize presentation without owning policy.

### 5.2 `next_actions`

The existing `next_actions` schema remains version 1 because its registered-ID shape does not need to change. Metadata in the wire is a projection of the registry, not an independent authority.

```json
{
  "schema_version": 1,
  "action_id": "memory.build",
  "scope": {"kind": "papers", "keys": ["ABCD1234"]},
  "automatic": true,
  "cost": "local",
  "impact": "mutating",
  "confirmation": "none",
  "reason": "OCR-derived content changed",
  "dedupe_key": "memory.build:papers:ABCD1234"
}
```

`emit_next_action(intent)` performs registry hydration. Override parameters for policy fields are removed.

Executors re-read the registry before running. If advisory wire metadata conflicts with the current spec, the action is refused as a contract mismatch; the wire never overrides the registry.

### 5.3 Version behavior

- Unknown descriptor schema version: client refuses the descriptor and refreshes the read model.
- Unknown `action_id`: Python returns `action.unknown`; clients do not guess or fall back to legacy commands.
- Missing action after a cached descriptor: Python returns `action.unknown`; no alias or command fallback.
- Additive unknown descriptor fields are ignored by clients.
- Semantic changes to an existing action ID require a schema/versioned contract change or a new ID; IDs are never silently repurposed.

## 6. Generic runner

```python
def run_action(
    request: ActionRequest,
    context: ActionContext,
    *,
    confirmed_action_id: str | None = None,
) -> PFResult:
    spec = require_registered(request.action_id)
    validate_scope(spec, request.scope)
    preflight = spec.preflight(context, request)
    require_available(preflight)
    require_confirmation(spec, request, confirmed_action_id)
    result = spec.handler(context, request)
    return hydrate_next_actions(result)
```

Rules:

1. Registry lookup is exact and fail-closed.
2. Preflight always runs after lookup and immediately before side effects.
3. Confirmation never bypasses availability or validation.
4. Confirmation must name the exact action ID. A generic persisted `yes` flag is not accepted.
5. Handler exceptions become the existing structured `PFResult` error boundary.
6. The runner performs no retries.
7. The runner never invokes a shell.
8. Handlers call existing Python functions directly; they do not spawn `paperforge` recursively.
9. `PFResult` remains the command result envelope. No second action-result envelope is introduced.

## 7. Confirmation contract

Confirmation is an accidental-safety boundary, not an authentication mechanism.

### Interactive CLI

For a confirmation-required root action:

```text
PaperForge will call the configured embedding provider for 1 paper.
Existing vector rows remain available until replacement commit.
Type embed.resume to continue:
```

Only the exact action ID confirms execution.

### JSON/automation

JSON mode never prompts.

Without confirmation:

- result: `ok=false`;
- error code: `action.confirmation_required`;
- exit code: `3`;
- data: current action descriptor.

The caller may render or inspect that descriptor, then re-run:

```bash
paperforge action run embed.resume \
  --scope papers --key ABCD1234 \
  --confirm embed.resume --json
```

A stale confirmation does not pin old facts. Preflight and descriptor generation run again before execution.

No persisted consent token, marker file, confirmation cache, signed plan, or cross-process dedupe record is added.

## 8. Follow-up orchestration

### 8.1 Modes

`paperforge action run` supports an explicit follow-up mode:

- `--follow none` — execute only the requested root action; default.
- `--follow auto` — execute registered automatic local descendants in the same process; return confirmation-required descendants as pending.
- `--follow prompt` — interactive CLI only; execute automatic descendants and prompt separately for each confirmation-required descendant.

`--follow prompt --json` is invalid.

Legacy human-facing commands may select a compatibility mode explicitly while they are being converted to thin adapters. The generic runner itself has no output-mode-dependent default.

### 8.2 Algorithm

```python
def run_follow_up_chain(root_result, context, *, mode, max_depth=4):
    queue = [(0, action) for action in root_result.next_actions]
    seen = set()

    while queue:
        depth, intent = queue.pop(0)
        descriptor = hydrate_from_registry(intent)
        key = canonical_dedupe_key(descriptor.action_id, descriptor.scope)

        if key in seen:
            record_skip(descriptor, "action.duplicate")
            continue
        if depth > max_depth:
            record_skip(descriptor, "action.depth_exceeded")
            continue

        seen.add(key)

        if mode == "none":
            record_pending(descriptor)
            continue
        if not is_automatic_local(descriptor):
            if mode == "prompt" and confirm_interactively(descriptor):
                child = run_action(..., confirmed_action_id=descriptor.action_id)
            else:
                record_pending(descriptor)
                continue
        else:
            child = run_action(...)

        record_execution(child)
        queue.extend((depth + 1, item) for item in child.next_actions)
```

Policy details:

- `is_automatic_local` is implemented once in Python from the current registry spec.
- A confirmed parent does not confirm any child.
- Confirmation-required descendants never auto-run.
- Dedupe is per invocation only.
- The default dedupe key is the canonical JSON representation of `action_id + scope`; producers cannot choose a weaker policy key.
- A spec may define a stricter semantic dedupe function later only for an observed need.
- The maximum depth is four; the current OCR chain needs two descendant levels.
- Duplicate or depth-limited actions are returned as skipped with reason codes, not silently discarded.
- No daemon, queue database, lock marker, or cross-process exactly-once guarantee is implied.

### 8.3 Result shape

The root handler's `PFResult` remains the outer response. When follow-ups are requested, the runner adds one namespaced field under `data`:

```json
{
  "follow_up_execution": {
    "executed": [
      {"action_id": "memory.build", "ok": true}
    ],
    "pending": [
      {"action_id": "embed.resume", "scope": {"kind": "papers", "keys": ["ABCD1234"]}}
    ],
    "skipped": []
  }
}
```

The outer `next_actions` contains only pending actions after the selected follow-up mode. With `--follow none`, it remains unchanged.

## 9. Partial success and failure semantics

`PFResult` remains the authority for command success and error details. The action layer does not invent a generic partial-success taxonomy over domain results.

Batch handlers must expose per-item outcomes in their existing `data` model and follow these rules:

- follow-up scope contains only successfully changed keys;
- failed and skipped keys never enter a downstream mutating action;
- some successes plus some failures may return `ok=true` with warnings and per-item details, consistent with the domain command contract;
- total failure returns `ok=false` and normally no mutating follow-up;
- a failure may emit a registered recovery action only when the domain handler explicitly defines it;
- runner failures stop only that branch of the chain; independent queued actions may continue;
- handler crashes are converted to structured errors and never retried automatically.

## 10. OCR rebuild chain

The first required end-to-end proof is:

```text
ocr.rebuild_derived (explicit root, local mutating)
  -> memory.build (automatic, local mutating, successful keys only)
  -> embed.resume (remote_possible, confirmation required)
```

Example:

```bash
paperforge action run ocr.rebuild_derived \
  --scope papers --key ABCD1234 --key EFGH5678 \
  --follow auto --json
```

If OCR rebuild succeeds only for `ABCD1234`:

1. OCR result retains the failed `EFGH5678` item and warning.
2. Python automatically runs `memory.build` only for `ABCD1234`.
3. If vector work is needed, Python returns `embed.resume` for `ABCD1234` as pending.
4. Obsidian renders the returned confirmation facts.
5. On acceptance, Obsidian invokes the generic runner with `--confirm embed.resume`.

The current `_runIndexRefreshChain` in the OCR workspace and the sync terminal `if action.action_id == "memory.build"` branch are migration sources. They are deleted after parity is proven.

## 11. CLI surface

```bash
paperforge action list --json
paperforge action describe <action_id> [--scope all|papers] [--key KEY] --json
paperforge action run <action_id> [--scope all|papers] [--key KEY] \
  [--confirm <action_id>] [--follow none|auto|prompt] [--json]
```

### `list`

Returns static registered metadata. It is for discovery, documentation, and agent tooling. It does not claim contextual availability.

### `describe`

Runs scope validation and preflight and returns the current descriptor without side effects. It is a read model, not an authorization token.

### `run`

Runs the exact registered operation. JSON output is one `PFResult` document.

Exit codes:

- `0`: action completed according to its domain result;
- `1`: action/domain execution failed;
- `2`: invalid request, unknown action, invalid scope, unavailable action, or schema/contract mismatch;
- `3`: explicit confirmation required.

These codes are stable machine contracts. Clients must not parse human text.

## 12. Client contracts

### 12.1 Obsidian

The plugin uses one generic transport call:

```ts
runAction(request: ActionRequest): Promise<PFResult>
```

Its executable shape is fixed:

```text
python -m paperforge action run <action_id> ... --json
```

The plugin may validate the descriptor schema before display, but it has no action allowlist and no `action_id -> argv` map. It passes `action_id` and scope as data to `execFile`/`spawn` with `shell: false`.

The plugin retains:

- modal and notice rendering;
- localized strings keyed by descriptor codes;
- progress and cancellation UI;
- current active-file/selection scope collection;
- disabling a button while its invocation is running;
- setup or navigation journeys that are explicitly client hints rather than actions.

The plugin deletes:

- `ALLOWED_ACTIONS` command mappings;
- `isAutomaticLocal` and `requiresConfirmation` policy copies;
- follow-up depth/dedupe policy;
- `(verb, command)` dispatch;
- command fields in `ActionPrimary` and dashboard action constants;
- OCR memory-to-embed orchestration.

### 12.2 CLI

The interactive CLI renders Python descriptors, prompts when requested, and delegates execution to the same runner. Legacy command names may remain as user-facing thin adapters during migration, but cannot own follow-up policy.

### 12.3 Agents

Agents use `action list/describe/run --json`. They must:

- treat confirmation-required as a two-step user-consent flow;
- never invent an unknown action ID;
- never convert descriptor text into a shell command;
- pass scope as structured arguments;
- surface pending remote/destructive work instead of auto-confirming it.

No MCP-specific action layer or output-schema framework is added. MCP can wrap the same CLI later if required.

## 13. Action vocabulary cutover

The migration normalizes IDs by executable operation:

| Current/contextual IDs | Canonical target |
|---|---|
| `memory.build`, `memory.rebuild` | `memory.build` |
| `memory.rebuild_vector`, `memory.upgrade_backend` | `embed.build` |
| `library.setup`, `library.configure`, `ocr.setup`, `ocr.enable`, `ocr.configure`, `memory.enable`, `memory.install_vector_deps`, `help.restore` | typed setup/config action from #142/#143; until then retain existing setup journey as `client_hint`, not a fake executable action |
| `library.probe`, `ocr.probe`, `memory.probe` | remove as actions; refresh the corresponding read model |
| `ocr.rebuild_derived` | retain |
| `ocr.run`, `ocr.diagnose`, `ocr.report_issue` | retain only when each maps to a real Python handler |
| raw `paperforge sync --rebuild-index` recommendation | `library.rebuild_index` |
| raw `paperforge paper-lookup` recommendation | `paper.lookup` if it remains a useful executable action; otherwise a read hint |
| raw query/search/retrieve command recommendations | typed registered actions only when their required input has a typed request; otherwise keep them in diagnostic data, not `next_actions` |

`foundation.update_python` is owned by #143. It enters the registry only after #143 provides an executable Python handler.

No deprecated aliases or command-string fallbacks survive the clean cutover.

## 14. Migration slices

### Slice A: registry and runner

- add the frozen `ActionSpec` registry;
- add typed scope/request/preflight types;
- add `action list/describe/run`;
- bind `memory.build` and `embed.resume` to existing functions;
- move registry hydration and invariant validation out of producer-owned fields;
- keep existing `next_actions` v1 wire compatible.

Acceptance: registry invariants, confirmation gate, unknown/version failure, and direct handler dispatch pass without plugin changes.

### Slice B: shared follow-up execution

- add `--follow` modes and per-invocation chain runner;
- replace sync's terminal hard-coded dispatch;
- preserve current sync terminal behavior through explicit adapter mode;
- prove dedupe, depth, and pending confirmation behavior.

Acceptance: sync emits and executes the same successful memory follow-up without a command-specific branch.

### Slice C: OCR vertical chain

- register `ocr.rebuild_derived`;
- emit `memory.build` for successful keys;
- emit `embed.resume` from memory build when needed;
- delete OCR workspace `_runIndexRefreshChain` after parity;
- route Obsidian through `action run ... --follow auto`.

Acceptance: one real/sandboxed OCR rebuild reaches pending embedding confirmation with only Python policy decisions.

### Slice D: probe and client cutover

- remove `command` from probe `action_primary`;
- replace contextual duplicate IDs with canonical IDs or `client_hint`;
- delete plugin argv/verb policy tables;
- consume descriptor metadata and invoke generic runner;
- add architecture-audit rules forbidding command-bearing action descriptors and client action-policy tables.

Acceptance: dashboard/settings actions work with no command string or action-specific argv mapping in TypeScript.

### Slice E: legacy producer cleanup

- migrate or remove every raw command-string `next_actions` producer;
- delete obsolete registry aliases and old orchestration code;
- run the repository-wide no-command-wire audit;
- update the architecture contract lifecycle and project records only after acceptance.

Acceptance: all emitted action IDs resolve to handlers; no action wire contains command text; no client owns action execution policy.

## 15. Verification contract

### Registry and wire

- duplicate or malformed IDs fail registration;
- every registered ID has one handler and preflight callable;
- every handler is reachable from exactly one canonical ID unless deliberate shared execution is documented;
- risky/remote/irreversible policy invariants fail closed;
- `emit_next_action` cannot override policy fields;
- descriptors and `next_actions` contain no command/argv keys or command fragments;
- unknown IDs and metadata mismatches are rejected.

### Dispatch and confirmation

- no handler side effect occurs before successful preflight and confirmation;
- unavailable and invalid-scope actions return exit 2;
- confirmation-required returns exit 3 and the current descriptor;
- exact action-ID confirmation executes once;
- confirming one action never confirms a descendant;
- handler exceptions become one valid PFResult and exit 1.

### Follow-up chain

- automatic local actions execute only in `auto`/`prompt` modes;
- remote/destructive actions remain pending in `auto` mode;
- per-invocation duplicate keys execute once;
- cycles and depth overflow are reported as skipped;
- separate invocations are not globally deduped;
- pending actions are the only actions left in the outer `next_actions`;
- partial batch success scopes descendants to successful keys.

### Cross-client parity

For the same fixture vault and action request:

- direct CLI, Obsidian invocation, and Agent JSON invocation reach the same Python handler;
- action metadata and availability are identical before localization;
- confirmation requirements and exit codes are identical;
- no client can execute an unknown ID by supplying command text;
- Obsidian owns only presentation, transport, cancellation, and duplicate-click suppression.

### OCR acceptance journey

One sandboxed journey proves:

```text
ocr.rebuild_derived
  -> memory.build executed automatically
  -> embed.resume returned pending
  -> explicit confirmation
  -> embed.resume executed
```

Assertions include successful-key scope propagation, one JSON document per invocation, no shell, no TypeScript memory/embed dispatch, and correct cancellation/progress transport.

## 16. Deliberate exclusions

Do not add in this issue:

- daemon or background job service;
- distributed queue;
- cross-process exactly-once markers;
- persisted confirmation tokens;
- automatic retries;
- generic rollback/undo framework;
- class-per-action hierarchy;
- action plugin discovery;
- command strings or argv on the wire;
- arbitrary handler args passthrough;
- MCP-specific server or action schema;
- generic JSON Schema/output-schema framework;
- new progress or cancellation protocol beyond #137/#150;
- credential or config migration owned by #138/#142/#143.

## 17. Final invariants

1. Every executable `action_id` resolves to one explicit Python handler.
2. Every policy field comes from one Python registry.
3. Every invocation rechecks current availability before side effects.
4. Every remote, destructive, or irreversible action requires explicit per-action confirmation.
5. Only local, non-destructive, confirmation-free actions may be automatic.
6. Every follow-up is a registered action ID plus typed scope; never a command string.
7. Every client invokes the same generic runner and owns no backend policy.
8. Every chain is bounded and deduped only within its invocation.
9. Every domain result remains a `PFResult`; the action layer does not create a second result system.
10. No unimplemented, client-only, or navigation-only operation is registered as executable.
