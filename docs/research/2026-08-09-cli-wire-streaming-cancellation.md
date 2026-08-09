# Versioned CLI Streaming & Cancellation Protocols — Research Report (PaperForge #139)

- Date: 2026-08-09
- Wayfinder ticket: [Research versioned CLI streaming and cancellation protocols](https://github.com/LLLin000/PaperForge/issues/139)
- Branch: `research/cli-wire-streaming-cancellation`
- Method: primary specifications, first-party documentation, and mature source-level protocol precedents.

Scope: local Python CLI consumed by TypeScript and agents, spawn-per-invocation, same-team (both ends ship together). Every material fact below carries a source tag [S#] resolved in the bibliography. Recommendations are marked as such; facts are sourced.

## 1. Executive recommendation

**Adopt now (smallest robust contract): a one-shot NDJSON event protocol on stdout with a pinned integer wire-contract major, a mandatory terminal result message, per-item partial failures, cooperative cancellation via process-group signals with a TERM→grace→KILL escalation, and strict stdout/stderr separation. No daemon, no version negotiation, no capability negotiation.**

Concretely: `paperforge <cmd> --json-proto --protocol 1` (env `PAPERFORGE_PROTOCOL`); every stdout line is one compact UTF-8 JSON object `{"v":1,"type":"log|progress|result|error|cancelled",...}`; exactly one terminal message (`result`/`error`/`cancelled`) precedes EOF; stderr carries human logs only; exit codes 0 = done (even with per-item failures), 1 = command-level failure, 2 = protocol/transport failure; POSIX spawn with `start_new_session=True` and kill the process group (`SIGTERM` → grace → `SIGKILL`), Windows spawn with `CREATE_NEW_PROCESS_GROUP` and send `CTRL_BREAK_EVENT` (never `CTRL_C`) → grace → `taskkill /T /F`.

**Omit explicitly:** daemon/long-lived server; MCP-style version downgrade negotiation; LSP-style capability negotiation; Content-Length framing; RFC 7464; protobuf/BEP; JSON-RPC ids/batches/notifications; bidirectional stdin commands; multi-major binaries; any transport abstraction layer.

The closest mature precedents are git-lfs custom transfer adapters (first-party subprocess NDJSON with init→transfers→terminate stages and per-item errors) [S2], MCP stdio (subprocess NDJSON + strict stdout/stderr + SIGTERM→SIGKILL shutdown) [S5][S6], and cargo `--message-format=json` (one-shot streaming with a terminal `build-finished` event) [S1].

## 2. Evidence-backed findings by decision area

### 2.1 Independent wire-contract major versions
- The dominant pattern is a **contract version that is independent of tool version, carried explicitly, and pinned/checked by consumers**: Jupyter versions its message spec independently of jupyter_client ("versioned independently of the packages that use it", current 5.5, version string in every message header) [S8]; pip's install report carries `version: "1"` and says "Tools must check this field" [S15]; cargo metadata is "stable and versioned" and callers are told to pass `--format-version` explicitly "to avoid forward incompatibility hazard" [S1]; go-plugin splits core-protocol vs app-protocol version in the handshake line [S14]; Docker versions the API in the URL path with documented min/max per engine [S13].
- **Recommendation:** one integer major (`v`), present in every message, plus a spawn-time pin (`--protocol N`). No in-band negotiation (see 2.9). `v` is the only field whose absence/unknown value is a hard error; everything else is additive-tolerant (2.2).

### 2.2 Additive JSON evolution, unknown fields/enums
- Jupyter: "Both sides should allow unexpected message types, and extra fields in known message types, so that additions to the protocol do not break existing code" [S8]. LSP keeps features compatible "using so called capability flags" and evolves 3.0→3.17 purely additively [S16]. Docker: "A new version of the API is released when new features are added. The Docker API is backward-compatible, so you don't need to update code that uses the API unless you need to take advantage of new features" [S13]. git-lfs added `ref` in v2.4 with "servers should be able to operate with a missing or null ref property" [S3]. ripgrep's JSON envelope explicitly says the type list "may expand over time" [S17]. gh requires the client to opt into fields via `--json a,b,c` — additions are invisible to clients that don't ask [S18].
- **Recommendation:** contract rule: clients MUST ignore unknown fields and unknown `type`/enum values inside the event stream; within a major, only additive changes are allowed (new optional fields, new event types, new error codes). A terminal `result` with an unknown `v` is a hard mismatch, not an ignore.

### 2.3 Partial failures
- git-lfs batch: "If there are problems accessing individual objects, servers should continue to return a 200 status code, and provide per-object errors", each `{"oid":..., "error":{"code":404,"message":...}}` with HTTP-style codes [S3]. git-lfs custom transfers: "Errors for a single transfer request should not terminate the process. The error should be returned in the response structure instead", and — the exit-code rule — "Any unexpected fatal errors in the transfer process (not errors specific to a transfer request) should set the exit code to non-zero and print information to stderr. Otherwise the exit code should be 0 even if some transfers failed" [S2]. Bazel BEP replaces individual events with `Aborted` on early termination rather than failing the whole stream [S19].
- **Recommendation:** batch commands return per-item `{status:"ok"|"error", code?, message?}` inside the terminal `result`; one failing item never aborts the run; exit 0 is allowed when per-item failures are reported (matches PaperForge's own convention that rc 0 = success for machine callers [S20]).

### 2.4 Framing: NDJSON vs RFC 7464 vs others
- NDJSON (jsonlines.org): UTF-8, each line a valid JSON value, `\n` terminator [S10]. MCP stdio: "Messages are delimited by newlines, and MUST NOT contain embedded newlines" [S5]. Cargo: "JSON object per line format" [S1]. git-lfs: "each JSON structure will be sent and received on a single line… with a single line feed at the end (and flush the output)" [S2]. ripgrep: "a sequence of messages, where each message is encoded as a single JSON value on a single line" [S17].
- RFC 7464: RS (0x1E) prefix + LF per text, designed for log files where elements can be truncated; explicitly "not... to be parsed by generic tooling"-friendly; needs a custom scanner and its canary logic exists only because RS allows arbitrary bytes [S11].
- LSP/JSON-RPC over stdio use Content-Length headers + JSON body instead [S16] — robust for arbitrary multi-line JSON but requires a byte-counting state machine on both sides.
- **Recommendation: NDJSON.** Compact single-line JSON (strings with newlines escaped), UTF-8, no BOM, final newline, flush after every message [S2]. It is trivially parsed by Node `readline` [S9] and Python `readline`, is debuggable with `jq`/`head`, and is the framing MCP — the modern local-subprocess standard — chose [S5].

### 2.5 Structured errors and terminal results
- JSON-RPC defines the error object `{code: integer, message, data?}` and reserves code ranges [S4]; LSP mirrors it and adds `ServerCancelled (-32802)` [S16]. MCP's version-mismatch example returns `{code:-32602, message:"Unsupported protocol version", data:{supported:[...], requested:...}}` [S6]. Cargo emits a terminal `build-finished` `{reason, success}` "at the end of the build… helpful for tools to know when to stop reading JSON messages" [S1]. Bazel: "A single BuildFinished event… includes the exit code for the command. This event provides authoritative success/failure information" [S19]. ripgrep's per-file `end` messages carry `stats` summary [S17].
- **Recommendation:** exactly one terminal message (`result` | `error` | `cancelled`) before stdout EOF; the parent treats **EOF without a terminal message as a protocol failure regardless of exit code**; exit code is a coarse backstop, not the primary signal. This aligns with PaperForge's existing `__main__` rule that an unhandled exception must never surface as rc 0 with empty/non-JSON stdout [S20].

### 2.6 stdout/stderr separation
- MCP stdio: "The server MAY write UTF-8 strings to its standard error (stderr) for logging purposes… The server MUST NOT write anything to its stdout that is not a valid MCP message" [S5]. LSP reserves stdout for the protocol and recommends `--clientProcessId` so the server can watch the parent [S16]. Cargo's robustness note — only interpret a stdout line as JSON "if it starts with `{`" [S1] — shows even mature tools tolerate foreign bytes on stdout.
- **Recommendation:** stdout = protocol only (strict); stderr = free-form human diagnostics. The parent MUST treat stderr as unstructured (capture/forward for logs) and MUST fail or skip on non-JSON stdout lines; strict-fail is fine because PaperForge owns the child.

### 2.7 Cancellation signals: Windows / macOS / Linux
- POSIX: spawn with `start_new_session=True` (setsid) or Python 3.11+ `process_group=` (setpgid) so the whole tree is one group [S7]; cancel with `os.killpg(SIGTERM)`, escalate to `SIGKILL`. Node documents the failure mode of not doing this: "On Linux, child processes of child processes will not be terminated when attempting to kill their parent" [S12]. systemd's canonical sequence: SIGTERM → `TimeoutStopSec` → SIGKILL [S21]. MCP stdio shutdown: close stdin → wait → SIGTERM → SIGKILL [S6].
- Windows: no POSIX signals. Python: `SIGTERM` is an alias for `terminate()` (TerminateProcess, abrupt); "CTRL_C_EVENT and CTRL_BREAK_EVENT can be sent to processes started with a creationflags parameter which includes CREATE_NEW_PROCESS_GROUP" [S7]; `signal.SIGBREAK` is the child-side handler [S22]. The deciding fact is in the Win32 API: CTRL_C "cannot be limited to a specific process group… the CTRL+C signal will not be received by processes within the specified process group", while "CTRL+BREAK signals always cause the handler functions to be called" — and delivery is limited to group members sharing the caller's console [S23]. Node on Windows kills abruptly ("signal argument will be ignored except for 'SIGKILL', 'SIGTERM', 'SIGINT' and 'SIGQUIT', and the process will always be killed forcefully and abruptly") [S12] — so a graceful path must come from the child catching CTRL_BREAK/SIGBREAK. Tree-kill escalation: `taskkill /T /F` ("Ends the specified process and any child processes started by it") [S24].
- **Recommendation:** POSIX: `start_new_session=True` + group SIGTERM → grace → group SIGKILL. Windows: `CREATE_NEW_PROCESS_GROUP` + `os.kill(pid, CTRL_BREAK_EVENT)` (never CTRL_C) → grace → `taskkill /pid X /t /f`. Parent always waits after signaling and escalates on timeout (MCP's sequence [S6]); never rely on the child's self-termination.

### 2.8 Cleanup safe points
- Python signal handlers run between bytecodes, never inside the C handler [S22]; the docs warn complex programs to "avoid raising exceptions from signal handlers" and to "install their own SIGINT handler" (set a flag, check it between work units) [S22]. Python's SIGPIPE default is ignore → `BrokenPipeError` on a closed pipe; docs show the catch-and-exit pattern and warn NOT to restore SIG_DFL [S22]. `Popen.communicate(timeout=...)` pattern: on timeout, kill and re-communicate to drain pipes [S7]. Bazel BEP distinguishes premature termination from failure with structured `Aborted.reason` (e.g. `USER_INTERRUPTED`) [S19]; MCP cancellation says receivers should stop processing, free resources, and send no response, and MAY ignore unknown/already-completed requests while senders MUST tolerate late responses [S25]. git-lfs sends `{event:"terminate"}` and the child "should clean up and terminate. No response is expected" [S2]. Jupyter routes shutdown on a dedicated control channel so it is not queued behind long executions [S8].
- **Recommendation:** cooperative cancellation — child installs SIGTERM/SIGBREAK/SIGINT handlers that only set a flag (no exceptions, no locks), checks the flag between atomic units, emits `{"type":"cancelled","reason":...}` when possible, then exits; hard-kill escalation remains the parent's backstop; the parent must also drain pipes after killing (Python communicate pattern [S7]) to avoid deadlocks.

### 2.9 Client/server mismatch handling
- go-plugin: handshake is "a single line of data terminated with a newline" — `CORE-PROTOCOL-VERSION | APP-PROTOCOL-VERSION | NETWORK-TYPE | NETWORK-ADDR | PROTOCOL` — with the client reading it first and failing on mismatch [S14]; README: protocol version "can be incremented to invalidate any previous plugins… a human friendly error message is shown to the end user" [S14]. MCP negotiates in-band (client sends its latest version, server replies with its latest; "If the client does not support the version in the server's response, it SHOULD disconnect") [S6]. Docker pins via path/`DOCKER_API_VERSION` and documents min/max per engine [S13].
- **Recommendation:** since PaperForge ships both ends in lockstep, choose the **cheapest variant: pin + fail fast**. Parent passes `--protocol 1`; child that only supports other majors emits a structured mismatch `error` (`code:"protocol_mismatch", data:{supported:[1], requested:0}`) and exits 2. No downgrade, no discovery, no fallback — same-team local means negotiation is dead machinery. This deliberately rejects MCP's downgrade and go-plugin's multi-version handshake.

### 2.10 Applicability to the same-team local subprocess model
- The git-lfs custom-transfer protocol [S2] is the closest precedent: same-project extension processes, line-delimited JSON over stdin/stdout, `event` discriminator, per-item errors, an explicit `terminate` stage, and exit-code semantics that separate per-item errors from process failures. MCP stdio [S5][S6] is the current canonical local-subprocess protocol (NDJSON, strict stream separation, escalation kill). Cargo [S1] proves the one-shot streaming shape (events + terminal event) for build-style tools. All three are mature, first-party, and require no daemon. [INFERENCE] A spawn-per-invocation model with a terminal-message guarantee gives PaperForge identical robustness to a daemon for CLI-shaped work at a fraction of the lifecycle complexity.

## 3. Minimal PaperForge contract proposal

**Invocation:** `paperforge <command> ... --json-proto --protocol 1` (env `PAPERFORGE_PROTOCOL`; default 1). Child MUST reject other majors with a structured error + exit 2. UTF-8 pinned (`PYTHONUTF8=1` or `sys.stdout.reconfigure`; PaperForge's `__main__` already does the latter on win32 [S20]).

**stdout (protocol only, NDJSON, flush after each message):**
```json
{"v":1,"type":"log",      "ts":"...", "message":"human-readable progress"}
{"v":1,"type":"progress", "ts":"...", "stage":"download", "id":"...", "done":0, "total":100}
{"v":1,"type":"result",  "ts":"...", "ok":true, "data":{...}, "items":[{"status":"ok"},{"status":"error","code":"...","message":"..."}], "summary":{...}}
{"v":1,"type":"error",   "ts":"...", "code":"protocol_mismatch|protocol_error|internal_error", "message":"...", "data":{"supported":[1]}}
{"v":1,"type":"cancelled","ts":"...", "reason":"signal"}
```
Rules: (a) `v` required on every message; unknown `v` on the terminal message = hard mismatch; (b) `type` discriminator; unknown types/fields ignored (additive evolution) [S8][S17]; (c) exactly one terminal message (`result`|`error`|`cancelled`) before EOF — its absence is a protocol failure even if rc 0 [S1][S19]; (d) per-item errors inside `result.items` never abort the run [S2][S3]; (e) all strings newline-escaped, one JSON object per line [S5][S10].

**stderr:** free-form human logs only; never protocol data [S5].

**Exit codes:** 0 = command completed (per-item failures allowed) [S2]; 1 = command-level failure (validation, not-found); 2 = protocol/transport failure (mismatch, framing corruption, internal crash) — consistent with PaperForge's "never rc 0 silently" rule [S20]; document the signal-derived codes (128+n) for hard kills.

**Cancellation (parent side, mirrored in the TS plugin and Python parent):** POSIX: `Popen(..., start_new_session=True)` (or `process_group=0`) → on cancel `os.killpg(pgid, SIGTERM)` → wait ≤ grace (default 5 s) → `os.killpg(pgid, SIGKILL)` [S6][S7][S21]. Windows: `creationflags=CREATE_NEW_PROCESS_GROUP` → `os.kill(pid, CTRL_BREAK_EVENT)` (never CTRL_C [S23]) → grace → `taskkill /pid <pid> /t /f` [S24]. After any kill: drain stdout/stderr and wait (communicate pattern) [S7].

**Child side:** handlers for SIGTERM/SIGBREAK/SIGINT set a flag only (no exceptions from handlers) [S22]; check between atomic units; emit `cancelled` if possible; treat `BrokenPipeError` on stdout as "consumer gone" and exit promptly (code 2 or 141) [S22].

**Parent invariants:** parse stdout with `readline.createInterface`/`for await (line of rl)` (handles partial chunks and a final unterminated line [S9]); EOF without terminal message = failure; stderr forwarded as logs; always wait + escalate on cancel.

## 4. Rejected alternatives and why

1. **RFC 7464 JSON text sequences** — RS+LF framing needs a custom scanner; the RS byte is invisible and breaks `jq`/`head`/line tooling; its truncation-recovery canary exists for log files, not process streams [S11]. NDJSON gives the same incrementality with line tooling [S10].
2. **LSP-style Content-Length framing** — robust for arbitrary multi-line JSON but requires a byte-counting state machine in both Node and Python readers; unnecessary when the protocol mandates compact single-line JSON [S16].
3. **Full JSON-RPC 2.0 with ids/batches/notifications** — correlation machinery exists for long-lived multiplexed servers (LSP/MCP); a one-shot command→stream→terminal-result shape needs none of it [S4][S5].
4. **Protobuf/BEP-style** — schema compilation, no human debugging, no `jq`; BEP's graph and child-announcement semantics solve multi-target builds, not CLI calls [S19].
5. **MCP-style version negotiation/downgrade** — valuable when peers are independently deployed; PaperForge releases both ends together, so downgrade adds failure modes without payoff [S6].
6. **Daemon/long-lived server** — amortizes startup at the cost of lifecycle, crash recovery, orphans, and config drift; the CLI call pattern doesn't need it (git-lfs proves subprocess-per-transfer is fine at scale [S2]).
7. **Bidirectional stdin command channel / duplex requests** — only needed for interactive or streaming-request workloads; PaperForge commands are one-shot. Keep stdin closed after spawn (MCP closes stdin as the first shutdown step [S6]).
8. **ZMQ/Jupyter wire protocol** — multipart frames + HMAC are transport machinery for kernels attached to many frontends [S8]; no such topology here.

## 5. Primary-source bibliography

- [S1] Cargo Book — External Tools / JSON messages: https://doc.rust-lang.org/cargo/reference/external-tools.html
- [S2] Git LFS — Custom Transfer Agents (subprocess protocol): https://github.com/git-lfs/git-lfs/blob/main/docs/custom-transfers.md
- [S3] Git LFS — Batch API: https://github.com/git-lfs/git-lfs/blob/main/docs/api/batch.md
- [S4] JSON-RPC 2.0 Specification: https://www.jsonrpc.org/specification
- [S5] MCP 2025-06-18 — Basic/Transports (stdio): https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
- [S6] MCP 2025-06-18 — Basic/Lifecycle (version negotiation, shutdown, timeouts, error example): https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle
- [S7] Python 3.14 — subprocess module (Popen, start_new_session, process_group, send_signal, Windows): https://docs.python.org/3/library/subprocess.html
- [S8] Jupyter — Messaging in Jupyter (versioning, compatibility, control channel): https://jupyter-client.readthedocs.io/en/stable/messaging.html
- [S9] Node.js — readline module (createInterface, 'line' event): https://nodejs.org/api/readline.html
- [S10] JSON Lines (jsonlines.org): https://jsonlines.org/
- [S11] RFC 7464 — JSON Text Sequences: https://www.rfc-editor.org/rfc/rfc7464
- [S12] Node.js — child_process (kill semantics, Windows, Linux tree caveat): https://nodejs.org/api/child_process.html
- [S13] Docker Engine API — Versioned API and SDK: https://docs.docker.com/reference/api/engine/
- [S14] hashicorp/go-plugin — README + docs/internals.md (handshake, protocol versioning): https://github.com/hashicorp/go-plugin
- [S15] pip — Installation Report: https://pip.pypa.io/en/stable/reference/installation-report/
- [S16] LSP 3.17 Specification (base protocol framing, capability flags, change log): https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
- [S17] ripgrep grep-printer — JSON format: https://docs.rs/grep-printer/latest/grep_printer/struct.JSON.html
- [S18] GitHub CLI — gh formatting (`--json` field opt-in): https://cli.github.com/manual/gh_help_formatting
- [S19] Bazel — Build Event Protocol + Glossary (BuildFinished, Aborted/USER_INTERRUPTED): https://bazel.build/remote/bep and https://bazel.build/remote/bep-glossary
- [S20] PaperForge — paperforge/__main__.py (local, read-only): transport contract comment "never rc 0 silently"
- [S21] systemd.kill(5) (SIGTERM → TimeoutStopSec → SIGKILL): https://manpages.debian.org/testing/systemd/systemd.kill.5.en.html
- [S22] Python 3.14 — signal module (SIGPIPE default, handler execution model, SIGBREAK, CTRL events, SIGPIPE note): https://docs.python.org/3/library/signal.html
- [S23] Microsoft — GenerateConsoleCtrlEvent (CTRL_C cannot target a group; CTRL_BREAK always delivered; console-sharing limit): https://learn.microsoft.com/en-us/windows/console/generateconsolectrlevent
- [S24] Microsoft — taskkill (/t tree kill): https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/taskkill
- [S25] MCP 2025-06-18 — Basic/Utilities/Cancellation: https://modelcontextprotocol.io/specification/2025-06-18/basic/utilities/cancellation

## 6. Open risks / questions

1. **Windows console attachment:** CTRL_BREAK_EVENT reaches only group members sharing the caller's console [S23]. If PaperForge spawns console-less (`CREATE_NO_WINDOW`/`DETACHED_PROCESS`) or the plugin runs from a service context, graceful Windows cancellation may not deliver; the fallback is the abrupt `taskkill /T /F`. Needs a Windows test matrix (console vs detached).
2. **Cooperative-cancellation latency:** Python handlers run between bytecodes; long C-bound units (OCR, PDF text extraction) delay the flag check [S22]. Grace must be a wall-clock budget with hard-kill after it; consider per-command grace knobs.
3. **Encoding drift:** Python's stdout through a pipe uses locale encoding on Windows unless forced [S7]; the contract must mandate UTF-8 (`PYTHONUTF8=1` or reconfigure — PaperForge already reconfigures in `__main__` [S20]).
4. **BrokenPipe/SIGPIPE semantics:** parent crash mid-stream surfaces as `BrokenPipeError` in the child (Python ignores SIGPIPE by default) [S22]; the contract needs an explicit "consumer gone → exit fast, documented code" rule and a parent-side test.
5. **Terminal-message guarantee vs hard kill:** SIGKILL means no terminal message; the parent must enforce its own deadline and treat missing terminal + non-zero exit as a distinct outcome ("killed") rather than command failure.
6. **Buffering:** pipe stdio is block-buffered by default; both sides must flush per message [S2] — easy to miss in the child (Python `print(..., flush=True)` or line-buffering) and in the Node parent (readline handles chunking [S9]).
7. **Migration:** PaperForge already emits single-document `--json` from commands [S20 area: docs/COMMANDS.md]. The proposal adds `--json-proto` as a new mode; decide whether existing `--json` commands keep their shape (recommended: yes — additive rollout, both ends bumped in lockstep).
8. **Version-bump discipline:** define in the ADR what triggers a major bump (rename/removal of a field or event, framing change, exit-code semantic change, terminal-message guarantee change) — additions alone never bump [S13][S15].