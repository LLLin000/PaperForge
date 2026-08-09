# Thin-Client Cache and Stale-State Research

- Date: 2026-08-09
- Wayfinder ticket: [#157](https://github.com/LLLin000/PaperForge/issues/157)
- Parent map: [#135](https://github.com/LLLin000/PaperForge/issues/135)
- Scope: Client-cache behavior for a CLI-backed Obsidian adapter; no production implementation.

**Scope:** The smallest client cache and auditable client interface for a thin Obsidian adapter whose only semantic source is fresh Python CLI responses. Destination: [Issue #135](https://github.com/LLLin000/PaperForge/issues/135) (supersedes the #69/#73 snapshot model — snapshots deleted, plugin must not parse canonical files, persisted state is display-only last-known, stale state can never enable actions). Every recommendation is tagged **Adopt / Defer / Reject**. **Schema ownership is explicit, not invented here:** wire fields belong to [#139](https://github.com/LLLin000/PaperForge/issues/139) (CLI streaming/NDJSON) and [#140](https://github.com/LLLin000/PaperForge/issues/140) (wire contract versioning); action dispatch/semantics belong to [#154](https://github.com/LLLin000/PaperForge/issues/154); the read-model envelope shape belongs to [#151](https://github.com/LLLin000/PaperForge/issues/151). This report defines only the client cache shape and its rules.

---

## 1. Destination constraints that reshape the cache (from #135)

- **[FACT]** "Runtime snapshots are deleted after consumer cutover." → No snapshot files, no `cache_version`, no per-file TTL gates as transport.
- **[FACT]** "The plugin must not parse PaperForge canonical files for semantic state. It may open Python-returned note/PDF/fulltext paths and own active-file/workspace/navigation/UI preferences." → The plugin's semantic reads are *CLI responses only*.
- **[FACT]** "Client caches are display-only last-known state when stale; actions depending on readiness remain disabled until a fresh envelope arrives." → Staleness is a *display* concern; action-enablement is a *freshness* gate.
- **[FACT]** "`paperforge.json` is Python-owned domain configuration. Obsidian `data.json` contains only UI preferences and stale last-known display data." → The client cache lives in `data.json`, not in vault `System/PaperForge/*`.
- **[FACT]** "Probe is summary; detailed rows use dedicated query commands." "CLI JSON is the current stable transport for CLI, Obsidian, and Agent consumers. No HTTP API or daemon is introduced." "Wire contract major versions are independent from package SemVer; same-major evolution is additive and semantically compatible, unsupported majors fail closed."

**Consequence [INFERENCE]:** with snapshots deleted and canonical files off-limits, there is nothing for the client to key on except the responses it has already received. The cache reduces to **one last-known response per module + one last-requested detail set**, and "staleness" reduces to **"older than the most recent probe result"**. No TTL windows, no revision maps, no token machinery — the display-only rule means staleness has no correctness cliff to guard with window arithmetic.

---

## 2. Executive recommendation

The smallest client cache that preserves responsiveness without a second authority: **persist, per module, the last CLI response the plugin received (display-only) in Obsidian `data.json`, stamped with the plugin's own `received_at` and a `schema_version`; render it immediately on view open; fire an on-demand probe; swap when the fresh response arrives; label the interim copy "as of <time>" and keep all actions disabled until the fresh response arrives; delete the module's cached copy the moment any mutation command completes.** [Adopt]

Staleness needs no timer, no TTL, no window: a response is *fresh* exactly when it is the latest probe result — any other copy is display-only and action-inert by construction. Any additional stamps the backend provides (`computed_at`, revision, contract major) come from the wire contract owned by #139/#140 and are *used if present, never required* — the cache works with only `received_at` + `schema_version`. Auditability = `schema_version` on `data.json`, `received_at` stamps, and the existing plugin diagnostic export gaining a cache-verdict section. **Explicitly rejected as overengineering now:** envelope SWR/SFE window fields, client revision maps, a Python `doctor --cache`, persisted page caches, and per-module TTL tables.

---

## 3. Findings by decision area

### A. In-memory TTL caches / probe throttling
- **[FACT]** RFC 9111 §5.2.2.3 (`must-revalidate`): "once the response has become stale, a cache MUST NOT reuse that response to satisfy another request until it has been successfully validated by the origin." With actions gated on freshness, the client's behavior is must-revalidate by construction [INFERENCE].
- **[FACT]** RFC 5861 §5: SWR validation "suggested [to be] predicated upon an incoming request, to avoid the possibility of an amplification attack" — no timer-driven revalidation. [INFERENCE: on-demand probing only.]
- **[FACT]** Current code: `memory-state.ts` `getVectorRuntime` uses a 2-second module-level TTL before re-probing; `managed-runtime.ts` uses a 5-minute TTL but fails closed (stale → `state:'unknown'`, "Never return 'ready' from stale cache — fail closed").
- **[REC — Adopt]** Replace *freshness TTLs* with a single **probe-dedupe interval** (e.g., 2 s per module): it only prevents re-spawning the CLI in a burst; it never changes what is rendered or which actions are enabled. **[REC — Reject]** Per-module TTL tables and `ttl_seconds` envelope fields as freshness semantics. The ManagedRuntime 5-minute cache is acceptable only as runtime-identity dedupe, not as a display-cache authority [INFERENCE].

### B. Persisted last-known display state
- **[FACT]** #135: `data.json` "contains only UI preferences and stale last-known display data." VS Code docs (Data Storage): persisted state is "restored when the same workspace is opened again" — restore-then-revalidate is the first-party norm.
- **[FACT]** Current code: `getMemoryRuntime` **writes CLI probe output back into the backend-owned snapshot file** (`fs.writeFileSync(paths.memoryStatePath, out)`) — a second-authority leak under the new boundary.
- **[REC — Adopt]** Persist, in `data.json` only, one `last_known[module]` entry = `{ payload (display-only copy of the last CLI response), received_at (plugin-stamped), schema_version }`. **[REC — Reject]** Persisting severity/action derivation, and the client writing any `System/PaperForge/*` file — remove the `getMemoryRuntime` write-back in the cutover. **[REC — Adopt]** On load, render `last_known` immediately (labeled "as of <received_at>"), probe in the background.

### C. Stale-while-revalidate — explicit assessment
- **[FACT]** RFC 5861 §3 / web.dev: SWR = serve stale while revalidating, bounded window, "SHOULD NOT continue to be served stale" beyond it; three windows (fresh → SWR → blocking).
- **[ASSESSMENT]** The *shape* is right and already implicit: show last-known while a fresh probe runs. The *machinery* — window fields, per-module window config, background revalidation scheduling — is **not justified**: (1) stale copies are display-only and cannot enable actions, so no window bounds a correctness cliff; (2) RFC 5861 §5 argues against unattended background revalidation; (3) windows matter only when a consumer must decide *how stale may be served*, which #135 removes by fiat. **[REC — Reject]** SWR window fields and math. Revisit only if a daemon/multi-client consumer (deferred in #135) needs windowed serving.

### D. Disabled action rules
- **[FACT]** #135: "Python owns action metadata and policy; clients own allowlisted transport and UI confirmation... actions depending on readiness remain disabled until a fresh envelope arrives." Corrected [#154](https://github.com/LLLin000/PaperForge/issues/154) moves generic action dispatch/semantics to Python (client-side allowlists like the current TS `ALLOWED_ACTIONS` map are not the target shape). VS Code Contribution Points: "Enablement is expressed with when clauses" (declarative from state). WAI-ARIA `aria-disabled`: "perceivable but disabled, so it is not editable or otherwise operable" — keeps tab-order focusability.
- **[REC — Adopt]** The client's only "disabled rule": **actions are enabled iff the module has a probe result newer than its last mutation**; otherwise the action control renders `aria-disabled="true"` with a reason label ("state as of … — refreshing") and stays focusable. Action descriptors/verbs/dispatch come from Python (#154); the client owns transport + UI confirmation. **[REC — Reject]** Client-side verb/priority tables (`categorizeMaintenanceRow` deleted; TS allowlist superseded by #154's Python dispatch).

### E. Partial-module failure / offline per-capability
- **[FACT]** #135: "Probe all aggregates unchanged module envelopes; partial detection failures remain valid per-module envelopes." Prior #69: per-capability evidence, no global offline flag. Kubernetes nodes doc: heartbeats are per-node; a partition degrades only affected nodes.
- **[REC — Adopt]** Each module's cache/probe stands alone; one module in `limited`/`unavailable` never tints siblings. The probe-failure path below is per-module.

### F. Running state owned by a live controller
- **[FACT]** Docker overview: "The Docker client talks to the Docker daemon, which does the heavy lifting... communicate using a REST API" — the client renders daemon state, holds none. Kubernetes: node controller owns status; missed heartbeat → controller sets `Ready` to `Unknown`. #135: "Long tasks remain plugin-owned subprocesses for now; Python owns job semantics, versioned NDJSON progress, cancellation cleanup, terminal results, and next actions."
- **[FACT]** Current code: `OcrProcessController` — single in-process owner; `isRunning` derives from its own child handle; duplicate starts impossible.
- **[REC — Adopt]** Controllers remain the only owners of `activity_state`/`isRunning`; views render controller state, never re-derive it. Long-task progress comes from the CLI NDJSON contract (#139); terminal results are backend-stamped per that contract. No client-side "is it running?" heuristics.

### G. Offline/error transitions — explicit assessment
- **[FACT]** RFC 9111 §4.2.4: "A cache MUST NOT generate a stale response unless it is disconnected or doing so is explicitly permitted... (e.g. ... extension directives such as those defined in [RFC5861], or configuration in accordance with an out-of-band contract)." RFC 5861 §4: stale-if-error allows serving stale on error; "SHOULD still be visibly stale when sent."
- **[ASSESSMENT]** The error transition needs **no window field**: the display-only rule is itself the bound — labeled last-known on probe failure never enables actions, so there is no staleness limit to enforce. This is stale-if-error *simplified to the display-only rule*.
- **[REC — Adopt]** On probe failure: keep `last_known`, render it labeled "offline/error — data as of <time>", disable actions, retry on next demand. **[REC — Reject]** `stale_if_error_seconds` fields and window arithmetic. Hard `unavailable` (runtime missing, DB corrupt) renders from the probe error itself, never from last-known.

### H. Cache invalidation after mutations
- **[FACT]** RFC 9111 §4.4: "A cache MUST invalidate the target URI... when it receives a non-error status code in response to an unsafe request method"; invalidation = remove or mark "in need of a mandatory validation before they can be sent." Microsoft Cache-Aside: "writes the change to the data store and then invalidates the corresponding item in the cache."
- **[FACT]** Current code already drops caches on mutation: `dashboard.ts` `_invalidateIndex()` (wired to refresh button and a `formal-library.json` modify event); `refreshMaintenanceData` compares manifest hashes. (Legacy file-based shapes are superseded, but the *drop-then-reprobe* pattern is right.)
- **[REC — Adopt]** When any plugin-owned mutation command completes (OCR run/redo/rebuild, memory/embed build, library sync), **delete `last_known[module]` and the last detail set**; the next render shows "refreshing…" and probes. No token comparison or revision propagation: with one copy per module, deletion makes pre-mutation state unservable.

### I. Detail queries / pagination — explicit assessment
- **[FACT]** #135: "Probe is summary; detailed rows use dedicated query commands." #139: pinned-major NDJSON, additive evolution, per-item failures.
- **[ASSESSMENT]** Current detail sets (module rows, maintenance rows) are bounded; **no cursor/pagination machinery is mandated**. Dedicated query commands returning bounded lists in existing shapes suffice, with the same display-only cache rule applied to the last-requested set.
- **[REC — Adopt]** Summary probe (module state) + dedicated query commands returning bounded lists (existing row shapes, per #151/#139). Client holds **only the last-requested detail set in memory** for navigation; re-queries on demand; mutation drops it. **[REC — Defer]** Cursor/keyset pagination (GitHub-style continuation) — only if a measured detail set exceeds comfortable payload sizes. **[REC — Reject]** Persisted page caches, pre-fetching all pages, client-side sort/filter over a fully materialized set.

### J. File opening versus semantic reads
- **[FACT]** #135: plugin "may open Python-returned note/PDF/fulltext paths"; must not parse canonical files for semantic state. Obsidian API (`obsidian.d.ts`): `Vault.cachedRead` — "Use this if you only want to display the content to the user"; `Vault.read` — "directly from disk. Use this if you intend to modify the file content afterwards." `git status --porcelain`: "stable across Git versions and regardless of user configuration" — the stable semantic-interface pattern.
- **[REC — Adopt]** Semantic state arrives only via CLI responses; file *content* is opened only at Python-returned paths and read via Obsidian `cachedRead` (display) or `read` (edit). The plugin never parses `paperforge.json`, SQLite, or state files for semantics. Enforce via the ArchitectureContract/collectors named in #135 (#152 owns enforcement patterns).

### K. Accessibility of checking / stale / error states
- **[FACT]** WCAG 2.2 SC 4.1.3 (Status Messages, Level AA): waiting/progress/results/error messages must be programmatically determinable; sufficient techniques: `role="status"`, `role="alert"`, progressbar/live region. WAI-ARIA: `status` = "advisory information... not important enough to justify an alert", implicit `aria-live="polite"`; `aria-busy` = "element is being modified... assistive technologies may want to wait until the modifications are complete." Current code uses `aria-live="polite"` on messages/activity and `role="listbox"` semantics; no `role="status"`/`role="alert"` typing, no `aria-busy`.
- **[REC — Adopt]** No redesign: (1) "refreshing…" and "data as of <time>" → `role="status"`; probe failures/errors → `role="alert"`; activity → `role="progressbar"`; (2) `aria-busy="true"` on a module card while probing, `false` when the fresh response arrives; (3) severity stays text+color (WCAG 1.4.1); (4) gated actions use `aria-disabled` + reason label, kept focusable.

### L. The auditable client interface (recommended)
```
data.json (plugin-owned) — the ENTIRE client cache:
{
  "schema_version": N,
  "ui_prefs": { … },                        // active-file/workspace/navigation/UI preferences (#135)
  "last_known": {                            // display-only last-known state
    "<module>": {
      "payload": { … },                      // opaque display copy of the last CLI probe/query response
      "received_at": "2026-08-09T10:30:00Z" // plugin-stamped; the ONLY required stamp
    }
  }
}
Rules:
  render   : latest probe result → last_known labeled "as of <received_at>" → "never probed"
  actions  : enabled iff the module has a probe result newer than its last mutation; else aria-disabled + reason
  mutation : any completed mutation command ⇒ delete last_known[module] + last detail set; next render probes
  failure  : probe failure ⇒ keep last_known, label "offline/error — data as of <time>", actions disabled
  throttle : probe-dedupe interval ~2 s/module (no timers, no TTL)
```
**Dependencies, not schemas:** wire-level fields (`computed_at`, revision, contract major, fail-closed on unsupported major) are owned by [#139](https://github.com/LLLin000/PaperForge/issues/139)/[#140](https://github.com/LLLin000/PaperForge/issues/140) and consumed if present — the cache does not require them. Action descriptor/verb/dispatch semantics are owned by [#154](https://github.com/LLLin000/PaperForge/issues/154). Read-model envelope/row shapes are owned by [#151](https://github.com/LLLin000/PaperForge/issues/151).

**Auditability [Adopt]:** (a) `schema_version` on `data.json`; (b) per-module `received_at` stamps; (c) the existing plugin diagnostic export (#68) gains a "cache" section listing each module's verdict (`fresh | last-known(labeled) | never-probed | dropped-after-mutation`) — no new Python command.

---

## 4. Explicit overengineering assessment (as requested)

| Proposal | Verdict | Justification |
|---|---|---|
| Envelope SWR window fields (`stale_while_revalidate_seconds`) | **Reject** | Display-only, action-inert stale copies; no correctness cliff for a window to bound. RFC 5861 §5 argues against background revalidation. Shape (show-last-known-while-fetching) is implicit in the display-only rule. Revisit only with a daemon/multi-client consumer (#135 defers). |
| Envelope SFE window fields (`stale_if_error_seconds`) | **Reject** | Error transition = same display-only rule with an "as of" label; actions never enable from it, so no staleness limit to enforce. |
| Client revision-token maps / cache-versioning | **Reject** | Snapshots deleted, canonical files off-limits: a client revision map is a parallel state machine with no information source. `received_at` + `schema_version` suffice; wire stamps (#139/#140) used if present. |
| Python `doctor --cache` | **Reject** | The client cache is plugin-owned (`data.json`); Python auditing it crosses the boundary. Auditability = envelope stamps (wire, #139/#140) + plugin diagnostic export. |
| Persisted page caches / cursor pagination | **Reject / Defer** | Detail sets are bounded today; dedicated query commands return bounded lists in existing shapes. Cursors only if a measured set outgrows payload comfort. In-memory last set only. |
| Per-module TTL tables (#69) | **Reject/Defer** | Superseded by fresh-vs-last-known. A single probe-dedupe interval covers the only real cost (CLI spawn). Calibrate only if probe cost is measured. |
| Snapshot files / `ocr_maintenance.json` / `cache_version` (#73) | **Reject** | Deleted by the #135 cutover; maintenance rows become a dedicated query command. |
| `getMemoryRuntime` snapshot write-back | **Reject** | Client must not write backend-owned files; remove in cutover. |
| TS `ALLOWED_ACTIONS` allowlist as target | **Reject** | Corrected #154 moves generic action dispatch/semantics to Python; client keeps transport + UI confirmation only. |

**Deferred (not now):** background/periodic revalidation (RFC 5861 §5 request-predicated); cross-client cache sharing (out of scope in #135); cursor pagination (until a measured need).

---

## 5. Minimum cache semantics — the complete contract (Adopt)

1. One `last_known` entry per module, persisted in `data.json` under `schema_version`, display-only, plugin-stamped `received_at`. Wire stamps (#139/#140) consumed if present.
2. Freshness rule: a response enables actions iff it is the latest probe result and newer than the module's last mutation; any other copy is display-only, labeled "as of <time>".
3. Render order: latest probe result → labeled last-known → "never probed".
4. Error rule: probe failure keeps last-known, labeled offline/error, actions disabled, retry on demand.
5. Mutation rule: any completed mutation command deletes `last_known[module]` and the last detail set; next render probes (RFC 9111 §4.4 principle).
6. Probe policy: on-demand + render-triggered, dedupe interval ~2 s/module (throttle only, no timers).
7. Details: summary probe + dedicated query commands returning bounded lists (existing shapes, #151/#139); in-memory last set only.
8. Actions: descriptors/dispatch from Python (#154); client owns transport + UI confirmation; freshness gate + `aria-disabled` + reason label.
9. Semantic-read invariant: plugin consumes CLI responses only; file content via Obsidian `cachedRead`/`read` at Python-returned paths; never parses canonical files.
10. Presentation: WCAG 4.1.3 typing (`role="status"`/`role="alert"`/progressbar), `aria-busy` while probing, text+color severity.

## 6. Evidence retained (primary sources)

- IETF RFC 9111 (HTTP Caching): https://www.rfc-editor.org/rfc/rfc9111 (§4.2.4 Serving Stale Responses; §4.4 Invalidating Stored Responses; §5.2.2.3 must-revalidate)
- IETF RFC 5861 (Cache-Control Extensions for Stale Content): https://www.rfc-editor.org/rfc/rfc5861
- web.dev — stale-while-revalidate (J. Posnick): https://web.dev/articles/stale-while-revalidate
- Microsoft Architecture Center — Cache-Aside pattern: https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside
- Microsoft Architecture Center — Caching guidance (expiration, client-side invalidation): https://learn.microsoft.com/en-us/azure/architecture/best-practices/caching
- Kubernetes — Nodes (heartbeats; node controller sets Ready to Unknown): https://kubernetes.io/docs/concepts/architecture/nodes/
- Docker — Docker overview (client-daemon REST): https://docs.docker.com/get-started/docker-overview/
- Obsidian API type definitions (cachedRead/read/MetadataCache): https://github.com/obsidianmd/obsidian-api/blob/master/obsidian.d.ts
- VS Code — Common Capabilities (Data Storage): https://code.visualstudio.com/api/extension-capabilities/common-capabilities
- VS Code — Contribution Points (command enablement via when clauses): https://code.visualstudio.com/api/references/contribution-points
- W3C — WCAG 2.2 SC 4.1.3 Status Messages: https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html
- W3C — WAI-ARIA 1.2 (status role; aria-busy): https://www.w3.org/TR/wai-aria-1.2/ · MDN mirrors: aria-busy, status role, aria-disabled
- Git — git-status(1) `--porcelain` (stable semantic interface): https://git-scm.com/docs/git-status
- PaperForge: #135 (destination map, supersedes), #157 (this ticket), #69/#73 (predecessor contracts — evidence, not authority), #139/#140 (wire fields — owners), #151 (read-model seams — owner), #154 (action dispatch — owner), #68 desktop-runtime-recovery-patterns, plugin sources (managed-runtime.ts, memory-state.ts, ocr-maintenance-ui.ts, ocr-process-controller.ts, next-actions-orchestrator.ts, dashboard.ts).

## 7. Open risks and questions

1. **Supersession bookkeeping**: #69 §9 "TTL-expired renders as unknown, never as its stored state" is superseded by #135's display-only last-known. The map must record this explicitly so later tickets don't re-lock the old rule. **[flag for map reconciliation]**
2. **Wire-stamp availability**: if #139/#140 do not provide `computed_at`/revision on every response, auditability rests on plugin-stamped `received_at` alone — acceptable, but confirm with ControlPlaneResearch (#151).
3. **Probe cost**: worst case is per view-open + per mutation. Measure CLI spawn cost; if it hurts, raise the dedupe interval (still not a freshness contract).
4. **Multi-window Obsidian**: one `data.json` per vault; multiple plugin instances would each hold last-known copies. Confirm single-instance assumption or scope the dedupe interval per window.
5. **Aria typing reliability on Obsidian 1.11.4**: smoke-test `role="status"` announcements (or `ariaNotify` availability) before claiming WCAG 4.1.3 conformance.
6. **Cutover sequencing**: deleting snapshot files / `ocr_maintenance.json` requires the dedicated query commands to exist first (vertical cutover, #135). Sequence cache deletion with the read-model slice (#151).
7. **Agent consumer**: CLI/Agent consumers have no `data.json`; they re-probe per invocation — confirm the query commands are cheap enough for per-command probes.

*Cross-references: ActionContractResearch (#154-adjacent) owns action-interface details; CliProtocolResearch owns the CLI/wire contract (#139/#140); ControlPlaneResearch owns read-model seams (#151); this report defines only the client cache shape and rules, with dependencies explicit rather than invented.*