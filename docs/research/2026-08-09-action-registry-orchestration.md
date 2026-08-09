# Action Registry and Follow-up Orchestration Research

- Date: 2026-08-09
- Wayfinder ticket: [#154](https://github.com/LLLin000/PaperForge/issues/154)
- Parent map: [#135](https://github.com/LLLin000/PaperForge/issues/135)
- Scope: Primary-source action-contract research plus current PaperForge migration mapping; no production implementation.

**Final (rev 3)** — Python owns descriptor metadata, handler dispatch, and enforcement; client is modal/transport only.
Tags: [SOURCE] primary spec/doc (links in bibliography), [REPO] PaperForge checkout, [INFERENCE], [RECOMMEND].

## 0. Executive recommendation
Python's `ACTION_REGISTRY` owns descriptor metadata **and** execution: each registered `action_id` maps to an explicit Python handler, invoked through one stable generic action command (`paperforge action run <action_id> --json`). Clients never own argv mapping or policy: they call the generic action, render the confirmation from the existing read model (probe/query envelopes), and transport progress/cancellation. Python enforces confirmation, scope, safety, and per-invocation follow-up-chain invariants (dedupe + loop depth) in one place so CLI, Obsidian, and Agent consumers cannot diverge. The TS `ALLOWED_ACTIONS` allowlist and `next-actions-orchestrator.ts` policy are migration source, not target: argv tables become Python handler bindings; dedupe/depth logic moves into `paperforge/core/action_runner.py`. Client keeps modal, progress, cancel, and duplicate-click suppression (UX only, not authority). Default is **no automatic retry**; retryability is a future Python-exposed property only if an observed need appears.

## 1. Destination architecture
### 1.1 Python — semantics and execution authority
1. **`ACTION_REGISTRY` (existing, extend)**: `action_id -> NextActionSpec{cost, impact, automatic, description}` plus a `handler` reference (callable or explicit module function). Single dispatch table; metadata never carries argv.
2. **Generic dispatch (new, small)**: `paperforge action run <action_id> [--keys K...] [--confirm] --json`. Pipeline: registry lookup (unknown id => protocol error, fail closed; JSON-RPC -32601/-32602 precedent [SOURCE]) → `schema_version` check → scope validation (`all` carries no keys; `papers` requires keys; empty keys never means all [REPO]) → safety/confirmation gate → per-invocation dedupe + depth check → execute handler → structured result via `PFResult`.
3. **Confirmation**: the gate is Python. Actions with `confirmation=required` (or `cost=remote_possible` / `impact=destructive`) execute only when the invocation carries explicit confirmation (`--confirm` from CLI, the confirm flag the plugin passes after its modal, or the agent session's permission-mode authorization). Invariants stay: remote/destructive => never `automatic`, always `confirmation=required` [REPO]. The confirmation *content* (prompt, cost, impact, scope) is read from the existing read model — `ActionPrimary.confirmation_required`/`confirmation_prompt`/`destructive_scope` in probe envelopes and `NextAction.cost/impact/confirmation/reason` in query results [REPO] — so no new `--plan` mode is required. Rationale: MCP requires a human in the loop able to deny [SOURCE]; D-Bus models interactive authorization as a per-call signal the callee honors [SOURCE]; the ask/deny/allow decision is policy, and here policy is enforced at the authority, not the UI [SOURCE].
4. **Dedupe + loop depth = per-invocation follow-up-chain invariants** (corrected): the in-memory `_inFlight`/`_executed` sets (keyed by `dedupe_key`) guard the batch of follow-ups produced by **one** command invocation (e.g. `sync`'s `next_actions`): within that chain, an action runs at most once and cannot re-enqueue itself; `depth>0` => automatic-local only [REPO]. These sets do **not** dedupe independent processes — a one-shot CLI cannot know what another process did — so cross-process dedupe is not claimed. Marker-file/lock dedupe is deferred until a concurrent-execution scenario is observed (Defer, §2).
5. **Retry policy (corrected)**: default is **no automatic retry** anywhere. The client may offer timeout + cancel (transport); retry decisions are not made automatically. If an observed need arises (e.g. an agent loop wants to re-run a failed idempotent action), Python may later expose a retryability property per action (RFC 9110 §9.2.2: only retry when the effect of repeating is known to be same [SOURCE]); that is a deferred, opt-in extension, not part of this contract.
6. **Follow-up chains**: `sync._attach_next_actions` emits descriptors; the terminal runner executes automatic-local inline and surfaces what needs confirmation [REPO]. Extend the same runner behind the generic action command so all consumers call identical logic. Chains remain suggestions expressed as registered IDs; cross-request state is referenced by explicit identifiers (MCP statelessness [SOURCE]).
7. **Results**: keep `PFResult{ok, command, version, data, warnings, next_actions}` [REPO]. Two error classes already exist implicitly: unknown action/schema/version = protocol error; `ok:false` + warnings = execution error (MCP's two-class split [SOURCE]). No envelope expansion (Defer, §2).

### 1.2 Client — modal/transport only (Adopt)
1. **Invoke the stable generic action command**: `execFile(python, ['-m','paperforge','action','run', id, '--json'], argv-array, cwd, timeout)` — no per-action argv tables, no shell strings (GitHub Actions script-injection mitigation: pass values as arguments, never generated script text [SOURCE]).
2. **Render confirmation from the read model**: probe/query envelopes already carry `confirmation_required`, `confirmation_prompt`, `destructive_scope`, `cost`, `impact`, `reason` [REPO]; show the modal; on approval re-invoke with `--confirm`. Deny always possible (MCP SHOULD [SOURCE]).
3. **Progress/cancellation transport**: stream progress fields; cancel via SIGTERM/cancel request; timeout is client-owned (MCP per-request timeouts SHOULD [SOURCE]). Retry: none by default (see 1.5).
4. **Version preflight**: keep `checkRuntimeVersion` (plugin vs `paperforge.__version__` [REPO]); Python refuses `schema_version` mismatch on descriptors (fail closed).
5. **Duplicate-click suppression (UX only)**: a UI-level in-flight set may remain for responsiveness; it is not the dedupe authority — per-invocation chain invariants live in Python.

### 1.3 Migration (existing TS logic = source, not target)
- `ALLOWED_ACTIONS` (action_id → argv) → becomes Python handler bindings in `ACTION_REGISTRY`; delete the TS table after migration.
- `isAutomaticLocal` / `requiresConfirmation` / `_inFlight`+`_executed` / depth guard in `orchestrateNextActions` → move into `paperforge/core/action_runner.py` as per-invocation chain invariants; the TS orchestrator shrinks to modal + `--confirm` re-invoke + progress/cancel.
- Legacy `{"command": str}` follow-ups in `search.py`/`retrieve.py`/`memory.py`/`paper_status.py` → replace with registered `action_id` descriptors or drop (Reject, §2).

## 2. Adopt / Defer / Reject
### Adopt
1. Stable `action_id` dispatch; command strings never on the wire. [SOURCE: MCP/Anthropic/OpenAI/LSP/VS Code name contracts; REPO legacy gap]
2. Python-owned generic action command (`paperforge action run <action_id>`) with registry + handler dispatch; client calls only that. [RECOMMEND per steering]
3. Orthogonal safety facts `cost`/`impact`/`confirmation` + invariants (remote/destructive => never automatic, always confirmation required) enforced in Python. [REPO; SOURCE: MCP ToolAnnotations hints, RFC 9110 safe/unsafe, OWASP LLM01 #5]
4. `scope{kind,keys}` validated in Python (`all` no keys; `papers` keys required). [REPO]
5. Per-invocation follow-up-chain dedupe (`dedupe_key` in-flight/executed within one batch) + loop-depth guard (automatic-local only beyond depth 0) in the Python action runner; client duplicate-click suppression is UX only. [REPO TS logic moves; SOURCE: RFC 9110 9.2.2, Stripe keyed-dedupe precedent]
6. `schema_version` on every descriptor; fail closed on unknown id/schema; client version preflight. [REPO; SOURCE: MCP version negotiation, D-Bus major version]
7. Confirmation content read from the existing read model (probe/query envelopes), gate enforced in Python; no new plan mode. [REPO; SOURCE: Ansible check_mode exists but the read model already covers PaperForge's UX]
8. Default: **no automatic retry**; timeouts and cancel are client transport. [RECOMMEND per steering; SOURCE: RFC 9110 9.2.2]
9. Two error classes: protocol error (unknown action/schema/version) vs execution error (`ok:false` + warnings) — keep existing `PFResult`. [SOURCE: MCP two-class split]
10. Injection hygiene: argv arrays only; reason/prompts rendered as untrusted display text; results sanitized before agent context. [SOURCE: GitHub Actions hardening; MCP untrusted annotations + validate results; OWASP LLM01 indirect injection]

### Defer
1. **`--plan` / dry-run mode** — the descriptor + confirmation are already available from probe/query envelopes (`ActionPrimary.confirmation_required`/`confirmation_prompt`/`destructive_scope`; `NextAction.cost/impact/confirmation/reason`); a plan mode would duplicate the read model. Add only if a consumer is observed that cannot obtain the descriptor without executing. [RECOMMEND per steering]
2. **Per-action `outputSchema`** — only if an observed consumer (e.g. Agent context builder) needs typed outputs; current `data` + `warnings` suffices. [INFERENCE]
3. **MCP server/adapter** — no daemon/HTTP planned; `--json` per-invocation covers current consumers. Revisit if an agent host requires MCP tools; descriptors already map to name/title/inputSchema/annotations. [INFERENCE]
4. **`PFResult` envelope expansion** (e.g. new `error` object) — probe envelopes already carry `error`; expand only on an observed contract gap. [REPO/INFERENCE]
5. **Cross-process dedupe (lock/marker file)** — a one-shot CLI cannot dedupe independent processes; add only when concurrent plugin + CLI execution of the same `dedupe_key` is observed. [RECOMMEND per steering]
6. **Python-exposed retryability property** — expose (e.g. `retryable: true` for read-only/idempotent actions) only if an agent loop is observed re-running failed actions; default stays no-auto-retry. [RECOMMEND per steering]

### Reject
1. **Command strings on the wire** (legacy `{"command": ...}` follow-ups) — injection surface, no metadata, no versioning; migrate to registered IDs. [SOURCE: GitHub Actions script injection; REPO]
2. **Client-owned argv allowlist as execution authority** (current TS `ALLOWED_ACTIONS` + orchestrator policy) — CLI/Obsidian/Agent would each reimplement invariants; corrected destination is Python-owned execution. [RECOMMEND per steering]
3. **Backend-shipped argv + backend-set confirm flags** — policy is enforced by the authority (Python), not declared per-wire-format. [RECOMMEND per steering]
4. **Prompt-only action descriptions** (no registry, no typed structure) — not deterministic for JSON automation/GUI. [INFERENCE]
5. **Server-resolved follow-up chains bypassing the gate** — chains run through Python's runner (registry dispatch, confirmation, per-invocation depth) or not at all. [RECOMMEND]
6. **Automatic retry of any kind in this contract** — default no-retry; revisit only via the deferred retryability property. [RECOMMEND per steering; SOURCE: RFC 9110 9.2.2]
7. **OpenAI strict-mode-everywhere schemas** (`additionalProperties:false`, all required) as the universal descriptor — ergonomics loss for CLI/GUI; adopt only in an agent projection if ever needed. [INFERENCE]

## 3. Findings retained per decision area (condensed, evidence-tagged)
- IDs: MCP name/title; Anthropic `^[a-zA-Z0-9_-]{1,64}$`; LSP opaque command + arguments; VS Code IDs [SOURCE].
- Availability: MCP tools/list per-request + listChanged; LSP dynamic registration; D-Bus Introspectable [SOURCE]; `ActionPrimary.availability` + ttl [REPO].
- Impact/safety: MCP ToolAnnotations are hints, untrusted unless server trusted [SOURCE]; RFC 9110 safe = read-only, SHOULD distinguish in UI [SOURCE]; `impact` + invariants [REPO].
- Confirmation: MCP human-in-the-loop SHOULD, show inputs before call [SOURCE]; D-Bus ALLOW_INTERACTIVE_AUTHORIZATION per-call [SOURCE]; Claude Code modes client-owned [SOURCE]; Python gate per steering; read model exists [REPO].
- Cost: MCP has no cost field (longRunHint only in Inspector UI spec) [SOURCE]; `cost` + never-silently-spend invariant [REPO]; OWASP LLM01 #5/#4, LLM10 [SOURCE].
- Idempotency/dedupe: RFC 9110 9.2.2 declare-or-don't-retry [SOURCE]; Stripe keyed dedupe as authority-side enforcement pattern [SOURCE]; dedupe_key as per-invocation chain invariant [REPO]; no cross-process claim [RECOMMEND].
- Loop/depth: depth guard automatic-local-only beyond depth 0, no self-re-enqueue [REPO]; MCP MRTR forces a fresh JSON-RPC id per round trip [SOURCE].
- Partial success: one action one result; MCP 2025-06-18 removed JSON-RPC batching [SOURCE]; per-item outcomes only across actions [REPO].
- Results: MCP content+structuredContent+isError, two error classes [SOURCE]; PFResult [REPO].
- Chains: statelessness + explicit IDs [SOURCE]; next_actions descriptors [REPO].
- Unknown actions: -32601/-32602 fail closed [SOURCE]; validator refuses [REPO].
- Human vs machine: mode is client property; facts from Python [SOURCE: MCP interface freedom, Claude Code defaultMode].
- Injection: script injection via shell-text interpolation [SOURCE]; prompt injection via results, sanitize before LLM [SOURCE: MCP, OWASP]; reason/prompts = untrusted text [RECOMMEND].
- Version mismatch: per-request protocol version + -32022 supported-list retry [SOURCE]; D-Bus major-version disconnect [SOURCE]; schema_version both sides [REPO].

## 4. Bibliography (direct links)
- MCP tools: https://spec.modelcontextprotocol.io/specification/2025-06-18/tools/ ; /2025-11-25/tools/ ; /2026-07-28/tools/
- MCP lifecycle/versioning/statelessness: /2025-06-18/basic/lifecycle/ ; /2026-07-28/basic/versioning/ ; /2026-07-28/basic/index/ ; /2025-06-18/changelog/
- MCP schema: https://github.com/modelcontextprotocol/specification/blob/main/schema/2026-07-28/schema.ts (ToolAnnotations 1918-1960, CallToolRequest 1869-1891)
- MCP usage: https://github.com/modelcontextprotocol/servers/blob/main/src/git/src/mcp_server_git/server.py ; semantics: https://github.com/modelcontextprotocol/php-sdk/blob/main/src/Schema/ToolAnnotations.php
- JSON-RPC 2.0: https://www.jsonrpc.org/specification
- RFC 9110 9.2.1/9.2.2: https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2 (obsoletes RFC 7231)
- D-Bus spec 0.43: https://dbus.freedesktop.org/doc/dbus-specification.html (Introspectable 2341; ALLOW_INTERACTIVE_AUTHORIZATION 760; version 738)
- LSP 3.17 executeCommand: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#workspace_executeCommand
- VS Code commands: https://code.visualstudio.com/api/references/contribution-points#contributes.commands
- OpenAI function calling: https://developers.openai.com/api/docs/guides/function-calling
- Anthropic tool use: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview ; /define-tools
- Claude Code settings/permission modes: https://code.claude.com/docs/en/settings
- OWASP LLM Top 10 2025: https://genai.owasp.org/llm-top-10/ ; LLM01: https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- GitHub Actions hardening: https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
- Stripe idempotency: https://docs.stripe.com/api/idempotent_requests
- Ansible modules: https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_general.html
- Prior in-repo report: docs/research/2026-07-14-capability-state-action-contract.md

## 5. Open risks and questions
1. Registry-to-handler binding: decide whether handlers live beside `ACTION_REGISTRY` or in per-command modules registered via a decorator — keep one dispatch table.
2. Confirmation token semantics for agents: `--confirm` on CLI is explicit; for agent sessions define what constitutes authorization (permission-mode grant vs per-action confirm) so the Python gate is uniform.
3. Per-invocation chain dedupe covers one command's follow-up batch only; concurrent plugin + CLI execution of the same action is unguarded until the deferred lock/marker mechanism lands — document this explicitly.
4. Migrate the 4 legacy command-string emitters: convert to registered IDs or drop; decide whether read-only commands should emit follow-ups at all.
5. Version skew: currently recoverable (`sync-runtime`); confirm refuse-to-execute on schema mismatch as the default.
6. reason/confirmation_prompt remain display-only; confirm they never reach code paths and are sanitized before agent context (indirect injection via vault content).
7. Depth-guard policy (automatic-local only beyond depth 0) is conservative; confirm whether a legitimate deeper chain (ocr to embed) may run under explicit user approval.