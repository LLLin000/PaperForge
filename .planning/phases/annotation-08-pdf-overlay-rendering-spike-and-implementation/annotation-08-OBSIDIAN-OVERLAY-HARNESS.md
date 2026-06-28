# Phase 8 — Obsidian PDF Overlay Harness

> **Status**: Automated gate PASSED (230/230 tests). Manual Obsidian verification pending.

---

## Automated Gate

All automated tests pass on `feat/pdf-annotation-layer`:

| Test File | Tests | Result |
|-----------|-------|--------|
| `annotation-bridge.test.mjs` | 39 | ✅ PASS |
| `annotation-navigation.test.mjs` | 48 | ✅ PASS |
| `annotation-overlay.test.mjs` | 76 | ✅ PASS |
| `annotation-main-runtime.test.mjs` | 47 | ✅ PASS |
| `annotation-section-dom.test.mjs` | 20 | ✅ PASS |
| **Total** | **230** | **✅ ALL PASS** |

### Commands

```powershell
cmd /c "cd /d paperforge/plugin && npx vitest run tests/annotation-bridge.test.mjs tests/annotation-navigation.test.mjs tests/annotation-overlay.test.mjs tests/annotation-main-runtime.test.mjs tests/annotation-section-dom.test.mjs --reporter=verbose"
node --check paperforge/plugin/main.js
```

### Known Baseline Failures (Pre-existing, unrelated)

3 failures in non-annotation test files (pre-date Phase 8):
- `tests/errors.test.mjs` (2 tests): `buildRuntimeInstallCommand` URL/args expectations
- `tests/runtime.test.mjs` (1 test): `resolvePythonExecutable` Windows `py -3` detection

These are unrelated to annotation overlay — they test Python runtime installer paths.

---

## Manual Harness Scope

Manual verification covers only **live Obsidian PDF viewer internals** that cannot be tested in a Node.js DOM environment. All helper, runtime, and DOM behavior is covered by the automated suite above.

---

## Supported Overlay Check

*[Manual — perform in Obsidian]*

1. Open PaperForge Dashboard → navigate to a paper with imported annotations
2. Click a Phase 7 page badge to open the PDF
3. Verify:
   - [ ] Semi-transparent `.paperforge-annotation-overlay-mark` elements appear on the correct page
   - [ ] Marks use annotation color (or default restrained yellow `#ffd400`)
   - [ ] Marks are positioned correctly over the annotated text region
   - [ ] Clicking a mark opens the read-only popover
   - [ ] Popover shows: selected text, comment, page label/number, source/read-only provenance, attachment identity, annotation identity
   - [ ] Popover has NO edit/delete/create/save/write-back/database/import/evidence controls
   - [ ] Focus/keyboard activation also opens the popover
   - [ ] Switching pages tears down stale marks and renders marks for the new page
   - [ ] Closing the popover removes it from DOM

---

## Unsupported Fallback Check

*[Manual — perform in Obsidian if viewer is unavailable]*

If the active pane has no PDF viewer (`findActivePdfViewerRoot` returns null):
- [ ] No overlay marks are rendered (overlay lifecycle stays in `idle` state)
- [ ] Annotation sidebar list, filter, group, and refresh remain fully usable
- [ ] Phase 7 page badge still navigates independently
- [ ] No errors are shown to the user (fail-closed)

---

## Read-Only Safety Check

- [ ] No edit/delete/create/remove/save buttons in overlay or popover
- [ ] No Zotero write-back
- [ ] No `annotations.db` mutation
- [ ] No import/apply controls
- [ ] No concept-card or evidence controls
- [ ] All user text rendered via `textContent`/`setText`, not `innerHTML`
- [ ] No raw errors, raw JSON, tracebacks, or shell output exposed to user
- [ ] No continuous polling — `MutationObserver` attached only during active overlay, disconnected during teardown
- [ ] No PDF identity guessing — identity derived from annotation sourceAttachmentKey, not guessed from viewer state

---

## Final Result

*[Complete after manual Obsidian check]*

| Check | Result |
|-------|--------|
| Automated Gate (230 tests) | **✅ PASS** |
| Overlay marks render on supported PDF viewer | ☐ Yes / ☐ No / ☐ N/A |
| Read-only popover on mark click | ☐ Yes / ☐ No / ☐ N/A |
| No edit/delete/write-back controls | ☐ Yes / ☐ No / ☐ N/A |
| Unsupported fallback preserves list/jump | ☐ Yes / ☐ No / ☐ N/A |
| Teardown on file/pane/paper/annotation change | ☐ Yes / ☐ No / ☐ N/A |
| No Zotero write-back | ✅ Automated (confirm via DOM tests) |
| No `annotations.db` mutation | ✅ Automated (confirm via DOM tests) |
| No continuous polling | ✅ Automated (confirm via lifecycle tests) |
| No raw errors exposed | ✅ Automated (confirm via textContent checks) |

**Manual verification** needs to be done in Obsidian for live PDF viewer internals.

---

*Phase: annotation-08-pdf-overlay-rendering-spike-and-implementation*
*Harness created: 2026-06-28*
