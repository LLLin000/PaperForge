# Windows Structured Cancellation Research

- Date: 2026-08-09
- Wayfinder task: [#150](https://github.com/LLLin000/PaperForge/issues/150)
- Parent map: [#135](https://github.com/LLLin000/PaperForge/issues/135)
- Scope: Throwaway workstation and isolated real-Obsidian experiments; no production implementation.

- **Date:** 2026-08-09 · **Method:** throwaway probes in OS temp and a disposable Obsidian profile/vault (removed after use) · **Repository:** read-only (`paperforge/plugin`) · **GitHub issue:** https://github.com/LLLin000/PaperForge/issues/150 (resolution of #139: https://github.com/LLLin000/PaperForge/issues/139)

## 1. Exact environment (all observed)

| Component | Version / value |
|---|---|
| OS | Windows 11 Home China, build 10.0.26200 (kernel 26200.8875), x64 |
| Node (harness) | v24.11.1 (`C:\Program Files\nodejs\node.exe`) |
| Python | 3.14.0 (CPython, MSC v.1944, AMD64) at `D:\programs\Python\python.exe` |
| **Obsidian (actual host, isolated disposable profile)** | **1.13.4** (`D:\programs\Obsidian\Obsidian.exe`) |
| **Electron (embedded in Obsidian 1.13.4)** | **37.6.0**, win32 x64 |
| **Node inside the Obsidian host** | **v22.19.0** (`process.versions` of the host renderer) |
| Host probe vault | `C:\Users\Lin\AppData\Local\Temp\pf-obsidian-cancel-audit` (disposable, isolated profile) |
| Shell | bash (MSYS/xterm-256color); Node matrix runs executed under `cmd.exe` for canonical console semantics |

## 2. Plugin spawn-mode inventory (read from `paperforge/plugin/src`)

| Site | Call shape | Stop mechanism today |
|---|---|---|
| `services/python-bridge.ts` `runSubprocess` | `spawn(py, args, { cwd, timeout, windowsHide: true })` — no `shell`, no `detached`, no process-group flags; resolves on `close`; `error` → exitCode −1 | none (timeout only) |
| `services/python-bridge.ts` `runQueryPlan` / `checkRuntimeVersion` | `execFile`/`execFileSync` with `windowsHide: true`, `timeout` | none |
| `services/ocr-process-controller.ts` `_spawn` | `spawn(path, [...args, "-m", "paperforge", ...], { cwd, shell: false, windowsHide: true, env, stdio: ["pipe","pipe","pipe"] })` | cooperative stdin token `PAPERFORGE_STOP\n`; `close` code 130 also treated as stopped |
| `services/embed-build-controller.ts` `start` | `spawn(py, [...args, "embed", "build", flag], { cwd, env, windowsHide: true })` | control sidecar `embed stop --json` (45 s) + poll; `dispose()` calls `child.kill()` (abrupt) |
| package scripts | plain esbuild/tsc dev scripts; no spawn wrappers | — |

**No production code path uses `detached`, `shell: true`, or `CREATE_NEW_PROCESS_GROUP`; nothing on Windows ever delivers a console event.** These facts were the hypotheses the probe tested.

## 3. Throwaway prototype (removed after use)

Files (all in `%TEMP%\wf-probe\` and the disposable host vault, deleted): `wf_child.py` (NDJSON v1 emitter + descendant spawner + flag-only SIGBREAK/SIGTERM/SIGINT handlers + `--no-terminal` / `--grace` / `--buffered` knobs + console probe via `GetConsoleWindow`/`GetConsoleProcessList`), `wf_child_stdin.py` (stdin-token cooperative stop: background reader thread, token `PAPERFORGE_STOP\n` sets flag, safe-point check emits `cancelled`), `wf_grandchild.py` (heartbeat descendant), `wf_send.py <pid> ctrl_break|ctrl_c|terminate|taskkill|probe_group`, `wf_parent.py` (Python leader: `creationflags=CREATE_NEW_PROCESS_GROUP` ± `CREATE_NO_WINDOW`/`DETACHED_PROCESS`, then CTRL_BREAK → grace → taskkill), `wf_drive.mjs` (20-scenario Node matrix), `wf_consoleless_launch.mjs` (drives the matrix inside a `CREATE_NO_WINDOW` Node process — console-less host mimic), host probe plugin (`manifest.json` + plain-CJS `main.js`) loaded in the isolated Obsidian profile/vault.

Child wire format (per #139 contract): one JSON object per stdout line, `{"v":1,"type":"start|progress|cancelled|result",...}`, flush per line; stderr = human logs; terminal = exactly one of `cancelled`/`result` before EOF; exit 130 after cooperative cancel.

Key probe snippets:

```python
# wf_child.py — flag-only cooperative handlers (SIGBREAK = Windows CTRL_BREAK_EVENT)
for s in (signal.SIGBREAK, signal.SIGTERM, signal.SIGINT):
    signal.signal(s, _handler)          # _handler sets CTX["flag"] only
...
if CTX["flag"]:
    time.sleep(args.grace)              # grace window
    out({"v": 1, "type": "cancelled", "reason": "signal", "signum": CTX["sig"]})
    sys.exit(130)
```

```python
# wf_child_stdin.py — cooperative stop that works from the plugin (console-independent)
for line in sys.stdin:                    # reader thread
    if line == "PAPERFORGE_STOP\n": flag["stop"] = True
...
if flag["stop"]:                          # checked at safe points
    out({"v": 1, "type": "cancelled", "reason": "stdin"})
    sys.exit(130)
```

```python
# wf_send.py core — the only way to send CTRL_BREAK_EVENT
os.kill(group, signal.CTRL_BREAK_EVENT)   # group = target pid; needs CREATE_NEW_PROCESS_GROUP
```

```python
# wf_parent.py — the #139-recommended Windows spawn shape (Python-parent only)
child = subprocess.Popen(cargv, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, ...)
os.kill(child.pid, signal.CTRL_BREAK_EVENT)   # -> grace -> taskkill /pid X /T /F
```

```js
// wf_drive.mjs — Node shapes mirroring the plugin API/options
spawn(PY, args, { windowsHide: true })
spawn(PY, args, { shell: false, windowsHide: true, stdio: ["ignore","pipe","pipe"] })
spawn(PY, args, { windowsHide: true, detached: true })
spawn(PY, args, { windowsHide: true, shell: true })      // cmd.exe /c
spawn(PY, args, { windowsHide: true, timeout: 1500, killSignal: "SIGTERM" })
```

## 4. Observed compatibility matrix (all rows executed on this machine)

Legend: ✅ cooperative `cancelled` event received · ❌ abrupt/no event · n/a not applicable. Every row was run at least once; terminal-event rows show exactly what arrived on stdout.

### 4.1 Node harness (console-attached terminal) using the plugin's API/options — NOT the plugin context

> This section is a **Node harness running under a terminal console** using the same `child_process` API/options as the plugin (`windowsHide`, `shell`, `detached`, `timeout`). It isolates the OS-level behavior of each option combination; the **real plugin context is the Obsidian/Electron host**, whose row is §4.4.

| # | Spawn opts (Node) | Cancel tactic | Child exit (close event) | Terminal event on stdout | Descendant after cancel | Notes |
|---|---|---|---|---|---|---|
| 1 | `windowsHide:true` | `child.kill("SIGTERM")` | `code=null, signal="SIGTERM"` | ❌ none | — | abrupt TerminateProcess; stream stops mid-progress (item 4/12); no drain |
| 2 | `windowsHide:true` | `child.kill()` (default) | `code=null, signal="SIGTERM"` | ❌ none | — | same as #1 |
| 3 | `windowsHide:true` | `child.kill("SIGKILL")` | `code=null, signal="SIGKILL"` | ❌ none | — | same as #1 |
| 4 | `windowsHide:false` | `child.kill("SIGTERM")` | `code=null, signal="SIGTERM"` | ❌ none | — | same; child shared parent console (peers incl. node+cmd) |
| 5 | `windowsHide:false` | CTRL_BREAK via helper | send **failed WinError 87** | child ran to completion (`result`) | — | **Node never sets CREATE_NEW_PROCESS_GROUP → the process group does not exist → GenerateConsoleCtrlEvent cannot target it** |
| 6 | `windowsHide:false` | CTRL_C (group 0 broadcast) | send rc=0, nothing delivered | child ran to completion (`result`) | — | sender was console-less (see §4.3); broadcast also cannot be targeted |
| 7 | `windowsHide:true` | CTRL_BREAK via helper | send **failed WinError 87** | child ran to completion | — | same root cause as #5 |
| 8 | `windowsHide:true` | `taskkill /pid X /T /F` | `code=1, signal=null` | ❌ none | killed | whole tree dies; child killed mid-progress |
| 9 | `detached:true` | `child.kill("SIGTERM")` | `code=null, signal="SIGTERM"` | ❌ none | — | abrupt; child had **no console at all** (`console_peers: []`) |
| 10 | `detached:true` | CTRL_BREAK via helper | send **failed WinError 87** | ran to completion | — | group absent + no console |
| 11 | `shell:true` | `child.kill("SIGTERM")` | `code=null, signal="SIGTERM"` | ✅ child completed | — | **only cmd.exe died; the python child was orphaned and ran to completion** — the Node-documented tree-kill failure, observed |
| 12 | `shell:true` | `taskkill /pid X /T /F` on cmd pid | `code=1` | ❌ none | — | tree kill from cmd pid reaches python |
| 13 | `windowsHide:true, timeout:1500, killSignal:"SIGTERM"` | Node timeout | `code=null, signal="SIGTERM"` | ❌ none | — | timeout option = same abrupt TerminateProcess |
| 14 | `windowsHide:true` | none (completes) | `code=0` | ✅ `result` | — | baseline |
| 15 | `windowsHide:true` + `--no-terminal` | none (completes) | `code=0` | ❌ **EOF with no terminal event, rc=0** | — | exactly the #139 §2.5 hazard, observed: rc 0 is not proof of a terminal message |
| 16 | `windowsHide:true` + `--no-terminal --buffered` | none | `code=0` | ❌ no terminal (all progress lines still arrived) | — | block-buffered pipe still delivered every line before EOF on this workload |
| 17 | `windowsHide:true` + descendant | `child.kill("SIGTERM")` | `code=null, signal="SIGTERM"` | ❌ none | **SURVIVED (heartbeat continued)** | orphan risk confirmed: `child.kill()` alone leaves the worker tree alive |
| 18 | `windowsHide:true` + descendant | `taskkill /T /F` | `code=1` | ❌ none | killed | tree kill is the only Node-reachable way to reap descendants |
| 19 | `windowsHide:false` + descendant | CTRL_BREAK | send failed 87 | ran to completion | survived (completion) | — |
| 20 | `windowsHide:true` + descendant + grace 0.5 | CTRL_BREAK then taskkill after 3 s | ran to completion | ✅ `result` | — | break undelivered (87) so escalation was correctly skipped; child never entered stopping |
| **21** | `windowsHide:true, shell:false, stdio:["pipe","pipe","pipe"]` (plugin `OcrProcessController` shape) + descendant | **stdin token `PAPERFORGE_STOP\n` written at 1.2 s** | `code=130` | ✅ **`{"type":"cancelled","reason":"stdin_token"}` after 0.5 s grace, then EOF** | **survived** (heartbeat continued; child exited without reaping) | cooperative stop works through the plugin's exact spawn shape; **descendant reaping is the child's job** — the token reaches only the child |

### 4.2 Python parent with `CREATE_NEW_PROCESS_GROUP` (the #139-recommended shape) — cmd console attached

| # | creationflags | Cancel | Result | Terminal event | Descendant |
|---|---|---|---|---|---|
| B1 | `CREATE_NEW_PROCESS_GROUP` (512) | CTRL_BREAK → grace 0.5 s | exit **130** after ~0.86 s | ✅ `{"type":"cancelled","signum":21}` (SIGBREAK) | n/a |
| B2 | 512 \| `CREATE_NO_WINDOW` | CTRL_BREAK (rc=0) | **not delivered** — child ran to completion, rc=0 | ✅ `result` | n/a |
| B3 | 512, + descendant | CTRL_BREAK → grace 0.5 s | exit 130 | ✅ `cancelled` | **killed by the group break** (default SIGBREAK handler) — heartbeat stopped, tasklist confirmed dead |
| B4 | 512 \| `DETACHED_PROCESS` | CTRL_BREAK (rc=0) | **not delivered** — completed rc=0 | ✅ `result` | n/a |
| B5 | 512 | CTRL_BREAK → child grace 3 s | exit 130 after ~3.34 s | ✅ `cancelled` | n/a |

### 4.3 Console-less host mimic (Node spawned with `windowsHide:true` → `CREATE_NO_WINDOW`, no console)

| Spawn | Cancel | Result |
|---|---|---|
| `windowsHide:false` child | CTRL_BREAK via console-less helper | **`OSError: [WinError 87] 参数错误。`** (ERROR_INVALID_PARAMETER) — the sender is not attached to a console; delivery impossible |
| `windowsHide:false` child | `child.kill("SIGTERM")` | abrupt TerminateProcess (`code=null, signal="SIGTERM"`) — no cancelled event |

### 4.4 Actual Obsidian/Electron host — **ACHIEVED** (isolated disposable profile + vault, driven via CDP)

| Fact | Observed value |
|---|---|
| Host | Obsidian **1.13.4**, Electron **37.6.0**, host Node **v22.19.0**, win32 x64 |
| Plugin spawn | `spawn(py, args, { windowsHide: true, shell: false, stdio: ["pipe","pipe","pipe"] })` — the real plugin shape, executed inside the host renderer |
| Cancel | `PAPERFORGE_STOP\n` written to child stdin **at 400 ms** (mid-work) |
| Child stdout | exactly one NDJSON terminal event: `cancelled {reason: "stdin", current: 2}` — no other trailing events |
| Child exit | **code 130, signal null**, reached **473 ms** after spawn (≈73 ms after the token) |
| Escalation | host hard timer did **not** fire (cooperative path completed first) |
| Vault | `C:\Users\Lin\AppData\Local\Temp\pf-obsidian-cancel-audit` (disposable, removed) |

**What the host row settles:** the stdin-token cooperative stop — already shipped for OCR (`OcrProcessController.stop()`) and replicated in probe row #21 under identical Node options — **works end-to-end inside the real Obsidian/Electron host**: token → child safe point → exactly one structured `cancelled` → EOF → rc=130, all within the grace budget, no console events involved. The `CTRL_BREAK_EVENT` route remains impossible from this host (console-less sender, §4.3; no `CREATE_NEW_PROCESS_GROUP` from Node, §4.1 #5/#7/#10) — observed at OS level and consistent with the host row.

## 5. Terminal-event / stdout-stderr behavior (observed)

- **Normal completion:** `start` → 12× `progress` → exactly one `result` → EOF; rc=0; stderr carried only the pid banner. `processProgressChunk`-style parsing is compatible with these lines (verified against `paperforge/plugin/src/services/progress-parser.ts` formats).
- **Cooperative cancel — stdin token, Node harness (#21):** token written mid-stream (item 4) → `cancelled` after 0.5 s grace → EOF → rc=130.
- **Cooperative cancel — stdin token, actual Obsidian host (§4.4):** token at 400 ms → exactly one `cancelled {reason:"stdin", current:2}` → EOF → **rc=130, signal null, 473 ms total**, no escalation.
- **Cooperative cancel — group CTRL_BREAK (B1/B3/B5):** `cancelled` arrives **after** the grace sleep (0.5 s / 3 s), then EOF, then rc=130 — the event precedes EOF and is the sole terminal line; stderr ends with `cancelled emitted, exiting`.
- **Abrupt kill (all `child.kill` variants, timeout option):** stdout simply stops mid-line-stream (no partial-line corruption was observed — the pipe closes cleanly); **no** `cancelled`, **no** `result`; close event `code=null, signal="SIGTERM"`; `child.killed===true`. The adapter cannot distinguish "killed by host" from "crashed" — both are EOF-without-terminal.
- **EOF without terminal event:** rc=0 + 13 non-terminal lines (observed #15/#16). Confirms the contract rule must be *parent-side*: EOF without terminal = protocol failure regardless of rc.
- **Drain:** Node captured all events up to the kill; no deadlock occurred. For taskkill rows, stderr/stdout pipes closed on process death with no hang (bounded 20 s race in driver never triggered).
- **Encoding:** `taskkill` emits localized (GBK) output; the probe's first helper crashed decoding it as UTF-8 — a real foot-gun for any TS adapter parsing `taskkill` output (use byte capture + `errors:"replace"`, or ignore output and use rc + `tasklist` verification).

## 6. Grace / escalation (observed)

- Grace is honored **only** when a cooperative signal actually reaches the child: stdin token (#21, §4.4: token→cancelled within ~73 ms host-side, well inside a 3–5 s budget) or same-console group CTRL_BREAK (B1/B3/B5: 0.5 s → ~0.86 s total incl. loop remainder; 3 s → ~3.34 s).
- From Node/Electron, no signal ever reaches the child's handlers (WinError 87 or silent no-op), so "grace" there means: **grace timer measured host-side between the stop request and the `taskkill /T /F` escalation** — the child gets that wall-clock budget to emit `cancelled` on its own (via the stdin token), and the host hard-kills the tree when the budget expires.
- `taskkill /T /F` exit path observed: child close `code=1`, tree reaped (#8/#12/#18). **Order matters:** if `child.kill()` runs *before* `taskkill /T`, the parent is already dead and the descendants are no longer in its process tree for `/T` to traverse (inferred from #17's surviving descendant + taskkill tree semantics `[INFERENCE]`). The escalation must therefore invoke `taskkill /PID X /T /F` **directly**, never `child.kill` first.

## 7. Actual Obsidian host execution: **ACHIEVED** (statement)

Host execution was achieved in a **fully isolated disposable Obsidian profile/vault** (`C:\Users\Lin\AppData\Local\Temp\pf-obsidian-cancel-audit`), driven via CDP, with the probe plugin using the production spawn shape (`windowsHide:true, shell:false, stdio:['pipe','pipe','pipe']`). Observed: Obsidian 1.13.4 / Electron 37.6.0 / Node v22.19.0; token at 400 ms → exactly one NDJSON `cancelled {reason:'stdin', current:2}` → exit **130, signal null, 473 ms**, no escalation (§4.4).

Earliest attempts in this agent's own window (single-instance handoff to a live user Obsidian 1.9.14; then vault-registered relaunch where the vault opened but the probe plugin did not load within the bounded window) are superseded by the isolated-profile/CDP run above; all temp profiles, vaults, and registry entries were removed, and no production Obsidian data was touched. **Electron-host facts are now observed, not inferred**, and they confirm the console-less-host conclusions of §4.3: the only cooperative channel that works from the host is stdin; console events are unreachable.

## 8. Smallest safe Windows spawn/cancellation contract for #139/#150 (recommendation)

**Spawn (plugin → python):** keep the current shape — `spawn(py, args, { cwd, windowsHide: true, shell: false, stdio: ["pipe","pipe","pipe"], env })`, **no `detached`, no `shell:true`** (observed: shell orphaning, §4.1 #11; detached console loss, #9/#10). Do not attempt process groups from TS — Node has no `creationFlags` knob, so `CREATE_NEW_PROCESS_GROUP` is unreachable from the Obsidian host (observed: WinError 87, §4.1 #5/#7/#10, §4.3; consistent with the achieved host row §4.4).

**Windows cooperative stop = the stdin-token channel that already exists** (`PAPERFORGE_STOP\n` in `OcrProcessController.stop()`; observed end-to-end in #21 **and in the actual Obsidian host**, §4.4) — extend it to embed/query-plan paths. It is console-independent and works in every observed spawn mode. The `CTRL_BREAK_EVENT` ladder of #139 applies **only** when the parent is Python and the child was spawned with `CREATE_NEW_PROCESS_GROUP` in the same console (B1/B3/B5) — adopt it for Python-side orchestration (tests, scripts, future sidecar), not for the plugin.

**Cancel sequence from the plugin (minimal, every step observed to work):**
1. write the stdin stop token; start a host-side wall-clock grace timer (3–5 s) — the child uses that budget to reach a safe point and emit `cancelled` (§4.4: ~73 ms in practice);
2. at grace expiry, **escalate directly with `taskkill /pid <pid> /T /F`** — no intermediate `child.kill()` (killing the parent first orphans the descendants before `/T` can traverse them — #17 vs #18);
3. drain stdout/stderr to EOF with a bounded wait after the kill (observed: closes cleanly, no deadlock), then classify.

**Terminal-event contract (adapter side, when no terminal event arrives):** the TS adapter MUST treat **EOF without a terminal `result`/`error`/`cancelled` line as a protocol failure** (or "killed") **regardless of exit code** — observed rc=0 with no terminal event (#15/#16) and rc=null+killed without one (#1–#4). Map: terminal line present → use it; EOF + rc=0 → `protocol_error`; EOF + rc≠0 → command failure; EOF after a stop request → `killed` (distinct from `cancelled`). Never wait for a terminal event after a hard kill — the process cannot emit one.

**Python side (child):** keep flag-only SIGBREAK/SIGTERM/SIGINT handlers (never raise from handlers), check at safe points, emit `cancelled` then exit 130; **on cooperative stop, the child MUST terminate its own descendants** — observed: the stdin token stops only the child and leaves the grandchild heartbeating (#21); the group CTRL_BREAK does kill descendants (B3) but that path is unavailable from the plugin; **stderr**: unstructured only; **stdout**: NDJSON v1, flush per line; emit exactly one terminal line before EOF on every non-killed path.

## 9. Adopt / Defer / Reject

| Decision | Item | Evidence |
|---|---|---|
| **Adopt** | stdin-token cooperative stop as the universal Windows cancel (OCR has it; extend to embed/query-plan paths) | #21 and **§4.4 host row**: `cancelled` + rc=130 under the plugin's exact spawn shape, inside the real Obsidian/Electron host |
| **Adopt** | parent-side "EOF without terminal = protocol failure" rule + distinct `killed` outcome | #15/#16 observed rc=0-no-terminal; #1–#4 abrupt-kill EOF |
| **Adopt** | `taskkill /pid X /T /F` invoked **directly** as the grace-escalation backstop (never after `child.kill`), with bounded drain after kill | #8/#12/#18: tree reaped, no deadlock; #17 vs #18: `child.kill` orphans descendants that `/T` can no longer reach |
| **Adopt** | keep `windowsHide:true`, `shell:false` | #4/#11: shell orphaning observed; `windowsHide` gives the child its own hidden console, avoiding visible windows; identical shape proven in host row |
| **Reject** | `child.kill()` as the escalation step (keep it only as a last-resort single-process abort where tree reaping is proven unnecessary) | #17: descendants survive it; it defeats the subsequent `/T` traversal |
| **Adopt (Python-side only)** | `CREATE_NEW_PROCESS_GROUP` + CTRL_BREAK → grace → taskkill, when the parent is Python | B1/B3/B5: full cooperative cancel with `cancelled` event, grace honored, descendants included |
| **Defer** | Node-side process-group creation (e.g. via a native helper or PowerShell P/Invoke `CreateProcess`) | not needed for the contract above; adds a native dependency |
| **Defer** | `CTRL_C_EVENT` anywhere | cannot be targeted; broadcast would hit the user's own console processes (MSDN; broadcast test delivered nothing from console-less sender — partial) |
| **Reject** | `detached:true` for worker processes | #9/#10: no console, no CTRL delivery, orphan risk |
| **Reject** | `shell:true` for worker processes | #11: killing the shell orphans python |
| **Reject** | relying on Node `timeout`/`killSignal` for structured cancellation | #13: same abrupt TerminateProcess, no terminal event |
| **Reject** | parsing `taskkill` output as UTF-8 | observed GBK crash in probe helper; use rc + `tasklist` verification |

## 10. Limitations / untested claims

- **Provenance of the host row:** §4.4 facts (Obsidian 1.13.4 / Electron 37.6.0 / host Node v22.19.0, token at 400 ms, `cancelled {reason:"stdin", current:2}`, rc=130/signal null/473 ms, no escalation) were observed in the isolated CDP-driven host run coordinated by the main agent; harness rows §4.1–§4.3 were observed in this agent's own runs. Both sets were produced on the same workstation.
- `GetConsoleWindow()` returned 0 for *all* children (ConPTY/terminal artifact); the `GetConsoleProcessList` peer sets are the reliable console-attachment evidence used in the matrix.
- CTRL_C broadcast behavior from a **console-attached** sender was not exercised (would have sent Ctrl+C to the user's own console processes — intentionally skipped); the "new-process-group children ignore CTRL_C" rule is doc-sourced only.
- B2/B4's "rc=0 but undelivered" vs §4.3's WinError 87 distinction is observed, but the exact Win32 call-site condition (attached sender + valid group + different console → silent no-op) is inferred from MSDN `GenerateConsoleCtrlEvent` semantics `[INFERENCE]`.
- The "`child.kill` before `taskkill /T` orphans descendants" ordering hazard is inferred from #17 (survivor after kill) + taskkill tree semantics; the exact kill-then-taskkill interleaving was not separately run `[INFERENCE]`.
- Grace timing includes loop-remainder effects; exact "grace budget from signal receipt" was not measured to sub-100 ms in the harness (host row: 473 ms total incl. ~73 ms token→cancelled).
- One matrix row (console-less `wh_false_sigterm`) did not write a record file (driver process exited before flush); its result (abrupt kill, no event) was confirmed by an identical manual run.
- All runs: single machine, Windows 11 26200; no Win10/WinServer/ARM coverage; host row used Obsidian 1.13.4 (Electron 37.6.0) — the machine's other Obsidian install (1.9.14) was not used for host execution.

## 11. Primary links

- Issue #150 (this task): https://github.com/LLLin000/PaperForge/issues/150
- Issue #139 (protocol/cancellation research, source-grounded report `docs/research/2026-08-09-cli-wire-streaming-cancellation.md`, branch `research/cli-wire-streaming-cancellation`): https://github.com/LLLin000/PaperForge/issues/139
- Plugin spawn sites: `paperforge/plugin/src/services/python-bridge.ts` (`runSubprocess`, `runQueryPlan`), `ocr-process-controller.ts` (`_spawn`, `stop`), `embed-build-controller.ts` (`start`, `stop`, `dispose`), `progress-parser.ts` (token formats)
- Node child_process kill semantics: https://nodejs.org/api/child_process.html (Windows kill, Linux tree caveat)
- MSDN GenerateConsoleCtrlEvent (group targeting, console-sharing limit): https://learn.microsoft.com/en-us/windows/console/generateconsolectrlevent
- MSDN taskkill /T /F: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/taskkill
- Python subprocess/signal (CREATE_NEW_PROCESS_GROUP, CTRL_BREAK_EVENT, SIGBREAK): https://docs.python.org/3/library/subprocess.html · https://docs.python.org/3/library/signal.html