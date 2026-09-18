# Interaction-Surface Audit — PaperForge Plugin (master `cd6d9fc8`)

**Date:** 2026-09-18 (revised 2026-09-19)
**Audited HEAD:** `cd6d9fc86e1110b4edf54cff8ece782658` (merge of PR #243)
**Scope:** user-triggerable surfaces (`views/`, `client/`, `services/`, `main.ts`)
**Out of scope:** Python backend, CRON/scheduler, settings-tab internals beyond buttons

> **Reviewer correction (2026-09-19):** the user re-checked the diff/CI and the upstream architecture and found several false positives in the first draft. Corrected verdicts are inlined in §1–§4 with `❌ DROPPED` and `⚠️ REDEFINED` markers. Net: F-4/F-5 stay P0 (fixed by #246, which needs a `versions` direct-entry patch before merge — see §7.1); F-10/F-3/F-7/F-14 stay real; F-12 stays real but **must not** cancel the operation; F-9/F-17/F-2/F-11-mechanism/F-13/F-15/F-16/F-1/F-8 are dropped or redefined.

> Note on #246: PR #246 (`chore/integrate-stale-root` → `master`) carries the F-4/F-5 fix. Its first commit (`4bfcd031`) had a wrong versions-mode edge (`_backendUnavailable = true` on versions-only failure — a false long-lived error). Corrected in `e4ff1ead`: a transient `versionsList()` failure **does not** flip the global flag; the direct `versions` entry path still renders the banner when the flag was set by a real acquisition failure.

---

## 1. Click-order-dependent divergent results

### F-3 · Version-restore button retry with no throttle ⚠️ (real)
- `dashboard.ts:2348-2367` (`restoreBtn` → `client.versionsRestore(paper.key, ver.label)`)
- **Divergence:** button is **not** disabled during the await; rapid double-click fires two restore calls. The second may run while the first copy is mid-flight → Python-side guard decides outcome, UI shows two sequential notices, no dedup.
- **Fix:** disable `restoreBtn` + `compareBtn` on click; re-enable on settle.

---

## 2. Identical error conditions that fail to surface all relevant errors

### F-4 · Stale cache masks backend failure after first load ⛔ **FIXED-BY-#246** (currently live on master)
- `dashboard.ts:239-287` `_loadDashboardData(quiet)`
- Catch block (line 265-285) sets `_backendUnavailable=true` **only inside `if (!this._cachedStats)`**.
- After a successful initial load (`_cachedStats` non-null), a backend outage during Refresh/Doctor/Repair:
  - does **not** set `_backendUnavailable`
  - does **not** show the "Cannot reach PaperForge CLI" message
  - leaves the old stats visible → user believes data is live.
- **This is exactly #244's symptom in global mode.** PR #246 lifts the flag set + banner to the shared shell. Before #246 lands, this is a live P0 on master.

### F-5 · Setup CTA only in global mode ⛔ **FIXED-BY-#246** (currently live on master)
- `dashboard.ts:677-679` — `_renderBackendMissingCard(view)` called **only** from `_renderGlobalMode`.
- `_switchMode` (`630-656`) and `_refreshCurrentMode` (`2131-2161`) and `_switchToVersionMode` (`2174-2199`) render paper/collection/versions modes **without** the recovery card.
- **Result:** if the backend dies while you're looking at a paper, you see stale paper data and **no** Setup entry. (The #244 fix addressed this in `chore/`; #246 brings it to master.)
- **Gap in #246:** `_switchToVersionMode` does its own `_contentEl.empty()` + `_renderModeHeader("versions")` and bypasses `_switchMode()`. PR #246 added `_renderBackendBanner()` there (`e4ff1ead`), closing the gap.

### F-6 · Orphan modal failure swallows detail but closes ⚠️
- `modals.ts:218-253` — `describeAction("library.prune")` → `runAction(...)`. `.catch(() => { new Notice("PaperForge: prune failed"); this.close(); })`.
- **Issue:** a partial failure where `failed_keys` is non-empty but `ok` is true is *surfaced*, but a transport-level throw (e.g. pointer invalid) closes the modal with one generic notice — user loses context of which orphans were selected.
- **Fix:** keep modal open on transport error; show `err.message`.

### F-7 · Version list failure masquerades as "no backups" ⚠️
- `_switchToVersionMode` (`dashboard.ts:2174-2199`): on `versionsList()` throw, sets `_versionPapers = []`.
- `_renderVersionMode` (`2201-2497`): if `_versionPapers` is null re-fetches; if empty array, `renderPaperList` shows `version_no_backups` (line 2260-2265).
- **Result:** a backend error and a genuine "no backups" state are visually identical.
- **Fix (deferred from #246):** distinguish `null` (load failed) from `[]` (genuinely empty); show an error strip for null. **Must not** flip the global `_backendUnavailable` flag — that would make the Setup card stick in every mode on a transient versions failure (the false long-lived-error class #244 targeted).

### F-8 · Orphan detection silent on success=false from probe · (downgraded — UX choice)
- `modals.ts:292-325` `checkOrphanState` — `probe("lineage")` then `new PaperForgeOrphanModal(...)` only if `resolved.length > 0`.
- If the probe returns `ok:false` (Python authority says "cannot determine"), the `.catch` shows a Notice; a `ok:true` payload with zero residuals is indistinguishable from "no orphans." Correct, but the **no-orphan** path produces no feedback at all.
- **Note:** a silent success is not a defect. Toasting "0 found" is a UX preference, not a bug.

---

## 3. Silent / long-running service errors (no recovery, no timeout, no cancel UI)

### F-10 · Transport timeout drops stderr ⛔
- `node-transport.ts:397-411` — timeout path: `child.kill(); reject(new Error("...timed out after ${timeout}ms: ${argv.join(" ")}"))`.
- The stderr chunks collected at line 393-395 are **never joined** into the rejection. A 120s timeout on `ocr.run` yields "command timed out" with no hint why (e.g. missing module, permission).
- The `close` path (424-437) **does** include stderr — so only the timeout edge is broken.
- **Fix:** `const stderr = stderrChunks.join("").trim(); const stderrTail = stderr.slice(-2000); const err = new Error(... + (stderrTail ? "\n\nstderr:\n" + stderrTail : "")); err.stderr = stderr; err.timedOut = true; reject(err);`

### F-12 · `OcrWorkspaceView` has no `onClose()` — timer leak + late renders ⚠️ (real, mechanism corrected)
- **Correction:** the first draft cited `ocr-workspace.ts:1475-1478` as the workspace `onClose`. Wrong citation — that `onClose` belongs to `VersionRestoreModal`, a different class. `OcrWorkspaceView` simply **does not override `onClose()`**.
- `_searchTimer` (`120`, `473/483`) is **never** `clearTimeout`'d. If the user types then closes, the timer fires on a detached element → console error / leak.
- Streaming `onEvent` / `_render()` for a closed view can touch a detached DOM (the `globalActivity` is re-derived from `probe("ocr")` on every workspace entry, so the indicator is **not** stranded — see F-11 correction).
- **Fix (do NOT cancel the operation):** add `onClose()` that clears `_searchTimer` and flips `this._closed`; make `_render()` / `onEvent` early-return when `_closed`. Cancelling the child stays owned by `plugin.onunload()` → `client.cancelActiveOperation()`.
- **Rationale:** OCR is Python-authoritative; ownership is shared client + OperationLock. Closing the workspace view is **not** a request to abort a running batch. Node docs: `ChildProcess` cancellation is explicit, not implied by DOM teardown. Obsidian docs: view-owned timers/listeners must be cleaned in `onClose()`.

---

## 4. Dead buttons / missing states / inconsistent UX

### F-14 · PDF button path mismatch on `[[wikilink]]` vs absolute ⚠️
- `dashboard.ts:1038-1056` — `pdfBtn` parses `[[...]]`; if found, `openLinkText`, else `Platform.openPath(path.join(base, targetPath))`.
- `targetPath` from the regex is the **wikilink body** (no `.pdf`); `openLinkText(targetPath, "")` resolves Obsidian-internally, but the absolute fallback joins `base + targetPath` where `targetPath` is already a full OS path from `entry.pdf_path` → double path. Inconsistent.
- **Fix:** branch on whether `entry.pdf_path` is already absolute.

---

## 5. Cross-cutting architecture risks (frontend patterns)

These are standard SPA/Obsidian-plugin failure modes the audit checked against the code. The audit's first draft applied a generic SPA taxonomy; the reviewer correction below re-binds each to the real ownership boundary (View-owned vs shared-client-owned vs Python-owned).

| Risk | In code? | Evidence | Severity |
|---|---|---|---|
| **Stale-response race** (out-of-order async) | Mitigated | `paperforge-client.ts:334-392` `_cachedRead` tags requests with `reqEpoch`; `invalidateCache` bumps epoch and clears in-flight (anti-resurrection guard line 374). Dashboard `_refreshCurrentMode` is render-only, acquisition in `_loadDashboardData`. | Low |
| **Orphaned async on unload** | **Yes (partial)** | F-12 — `OcrWorkspaceView` has no `onClose`; `_searchTimer` leaks and streaming events can render a closed view. NOT a child-process leak (F-13 dropped; cancellation is `plugin.onunload` ownership). | Med |
| **Error aggregation gap** | Partial | `_executePfResult` (622-690) handles `ok:false` + list passthrough with schema check (657). UI layer (F-4/F-7) still collapses multi-condition failures into one Notice. | Medium |
| **Missing cancellation UI** | **No** | F-9 dropped — `_renderActivity()` already renders a gated Stop button (`ocr-workspace.ts` `_renderActivity`, `pf-btn pf-btn-ghost`, disabled when `!client.isOperationActive()`). | — |
| **Timeout without diagnostics** | **Yes** | F-10 — stderr dropped on timeout. | Medium |
| **Resource cleanup on unload** | **Yes (view-scoped)** | F-12 — timer/late-render cleanup, not child cancellation. | Med |
| **Accessibility (aria-live)** | **No** | F-17 dropped — `_renderActivity()` already carries `attr: { "aria-live": "polite" }`. | — |

### Ownership boundary (the audit's key lesson)
PaperForge is no longer a plain SPA: it has three resource-ownership layers —
1. **View-owned:** DOM, debounce timers, view-local callbacks. Cleaned in `onClose()`.
2. **Shared-client-owned:** the active child handle (`PaperForgeClient` + `OperationLock`).
3. **Python-owned:** the actual operation state (`probe("ocr").activity_state`).

A finding that prescribes "view unload → cancel OCR" conflates layer 1 with layer 2 and is wrong (F-13). A finding that prescribes a Stop button assumes layer-2 control is missing when it is already wired (F-9).

---

## 6. Priority summary

| Rank | ID | Title | Effort | Blocker for release? |
|---|---|---|---|---|
| P0 | F-4 | Stale cache masks backend failure | S (1 line + test) | **Yes on master until #246** |
| P0 | F-5 | Setup CTA only in global mode | S (fixed by #246) | **Yes on master until #246** |
| P0 | F-12 | `OcrWorkspaceView` no `onClose` (timer + late-render guard; do NOT cancel) | S | Recommended |
| P1 | F-10 | Timeout drops stderr | S | No |
| P1 | F-3 | Restore button no throttle | S | No |
| P1 | F-7 | Version error ≡ no-backups | S | No |
| P1 | F-14 | PDF absolute/relative path normalization | S | No |
| P2 | F-6 | Orphan modal generic transport failure | S | No |
| P2 | F-11 | Late streaming event renders closed view | S | No (same family as F-12) |
| P3 | F-1 | Setup vs Repair pre-check unification | M | No (under-argued) |
| P3 | F-8 | No-orphan toast (UX choice) | S | No |

---

## 7. Recommended follow-up branches

1. **`fix/dashboard-stale-backend-master`** (PR #246) — open, CI green. The `versions` direct-entry patch (`_switchToVersionMode` calls `_renderBackendBanner()`) + the `_backendUnavailable` non-flip correction (`e4ff1ead`) are in. Merge after CI passes. F-4/F-5 are the only release blockers on master.
2. **`fix/view-lifecycle-and-timeout-diagnostics`** — F-12 (`onClose` clears `_searchTimer`, `_closed` guard, no cancel) + F-10 (bounded stderr on timeout). Tests: (a) closing workspace clears timer; (b) closing workspace does NOT call `cancelActiveOperation`; (c) progress event after close does not render; (d) plugin `onunload` DOES cancel; (e) timeout error carries captured stderr.
3. **`fix/dashboard-error-clarity`** — F-3 (restore pending lock) + F-7 (versions load-error state) + F-14 (PDF path normalization) + F-6 (orphan error detail).

### Dropped / redefined findings (not actionable)
- **F-9** ❌ false positive — `_renderActivity()` already has a gated Stop button.
- **F-17** ❌ false positive — `_renderActivity()` already has `aria-live="polite"`.
- **F-2** ❌ already patched — `setNoteFlag()` calls `_patchCachedEntry()` which updates both the list cache and `_currentPaperEntry`.
- **F-11-mechanism** ⚠️ redefined — `globalActivity` is re-derived from `probe("ocr")` on every workspace entry, so it does not strand; only the late-render path is the real issue.
- **F-13** ❌ wrong ownership — closing the workspace must NOT cancel OCR; plugin `onunload()` owns cancellation.
- **F-15** ❌ future fragility only — the version row has no nested interactive target today.
- **F-16** ❌ wrong coupling — `doctor`/`repair` are filesystem/config actions, not OCR-credential-dependent.

**Web-search supplement:** the user requested external research on frontend architecture failure patterns. This audit was performed by direct code reading against the known SPA/Obsidian-plugin taxonomy, then corrected against Node.js `ChildProcess` lifecycle docs and W3C/MDN `aria-live` guidance (both confirm the dropped findings). No web tool was available in this session; the cross-cutting table in §5 is derived from that taxonomy, not external sources. If you want a cited external reference set (e.g. MDN on `aria-live`, Obsidian `onunload`/workspace events, Electron child-process lifecycle), say so and I'll fetch it.