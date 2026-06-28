# Annotation Phase 8 Validation Plan

**Phase:** annotation-08-pdf-overlay-rendering-spike-and-implementation  
**Created:** 2026-06-28  
**Status:** Ready for plan gate review  
**Scope:** OVLY-02, OVLY-03, OVLY-04, OVLY-05

## Validation Strategy

Phase 8 uses risk-gated validation. The live Obsidian PDF viewer is the uncertain part, so Wave 1 must first record whether PaperForge can safely attach an overlay. Later waves must either implement against that recorded attach contract or keep the overlay disabled while preserving sidebar/list and PDF jump behavior.

Automated tests cover deterministic helpers, runtime state, DOM rendering, teardown, and read-only popover behavior. Manual Obsidian verification is allowed only for live viewer internals that cannot be fully represented in Vitest.

## Requirement Coverage Matrix

| Requirement | Validation Evidence | Plans | Gate |
|---|---|---|---|
| OVLY-02 | Viewer probe document, overlay helper tests, runtime DOM tests, visual CSS check | 01, 02, 03, 04 | Supported viewer renders translucent read-only marks; unsupported viewer renders none |
| OVLY-03 | Page/PDF identity tests using `pageIndex`, `positionJson`, `selectorJson`, and `sourceAttachmentKey` | 02, 03, 04 | No mark appears unless active PDF identity and page match confidently |
| OVLY-04 | Popover view-model and DOM tests | 02, 04 | Click/focus shows selected text, comment, page, and read-only provenance with no edit/delete/create controls |
| OVLY-05 | Fail-closed helper/runtime tests plus manual unsupported-viewer note | 01, 02, 03, 04 | Sidebar/list and Phase 7 jump stay usable when overlay cannot attach |

## Wave Validation

### Wave 1: Viewer Probe And Attach Contract

- Write `annotation-08-PDF-VIEWER-SPIKE.md`.
- Record `viewerRoot`, `pageLayer`, active PDF identity signal, scale/rotation/page observations, `supportDecision`, and `fallbackReason`.
- Gate: later overlay rendering work may proceed only if the spike records a supported attach contract. If unsupported, later plans must implement disabled/fallback behavior only.
- Manual Obsidian check is acceptable here because the live viewer DOM is outside the Vitest harness.

### Wave 2: Pure Overlay Helpers

- Add or extend helper tests, likely in `paperforge/plugin/tests/annotation-overlay.test.mjs`.
- Validate parser behavior for known `positionJson` fixtures, invalid JSON, missing rects, unknown shapes, page mismatch, PDF identity mismatch, color fallback, and popover view-model construction.
- Gate: helpers must return structured disabled reasons instead of raw errors.

### Wave 3: Runtime Overlay Rendering And Teardown

- Extend runtime/DOM tests for attach state, mark rendering, teardown, viewer changes, annotation state changes, and fallback.
- Verify overlay DOM is namespaced and PaperForge-owned.
- Verify sidebar/list/filter/group and Phase 7 jump behavior still work when overlay is disabled.
- Gate: no continuous polling and no stale marks after active file, pane, paper, PDF DOM, or annotation state changes.

### Wave 4: Read-Only Popover And Final Phase Gate

- Test click/focus popover behavior from overlay marks.
- Verify selected text/comment/page/source identity display uses safe text APIs, not raw HTML.
- Verify no edit, delete, create, local edit, database write, Zotero write-back, or evidence write-back controls are introduced.
- Run focused annotation suite and record manual Obsidian harness result in the final summary.

## Automated Commands

Run syntax checks after touching plugin JavaScript:

```powershell
node --check paperforge/plugin/main.js
node --check paperforge/plugin/src/testable.js
```

Run focused annotation tests as they become available:

```powershell
Set-Location paperforge/plugin
npm.cmd test -- annotation-bridge.test.mjs annotation-navigation.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs annotation-overlay.test.mjs
```

If `annotation-overlay.test.mjs` does not exist at the start of execution, Wave 2 must create it before claiming helper coverage.

## Nyquist Sampling

- Per task: run the smallest focused test command that covers the touched helper, runtime, DOM, or CSS behavior.
- Per wave: run the full focused annotation suite available at that point.
- Phase gate: run syntax checks, the full focused annotation suite, and record the manual Obsidian overlay harness result.

## Manual Harness Boundary

Live Obsidian PDF viewer internals cannot be fully trusted from local static code alone. The manual harness must record enough evidence to justify one of two outcomes:

- `supported`: viewer root, page layer, active PDF identity, and page geometry are observable enough for read-only marks.
- `unsupported`: overlay remains disabled and the user keeps sidebar/list plus Phase 7 jump behavior.

Unsupported is an acceptable Phase 8 result only when the disabled/fallback path is tested and documented.

## Blocking Criteria

- Do not render overlay marks without confirmed active PDF identity and matching `pageIndex`.
- Do not render overlay marks for missing, invalid, ambiguous, or unsupported `positionJson`.
- Do not expose raw DOM, JSON, stack, shell, or parser errors to the user.
- Do not add edit/delete/create/write-back controls.
- Do not use continuous polling as the primary refresh mechanism.
