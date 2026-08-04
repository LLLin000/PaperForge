# Phase ANN15: Canvas Verification Gate and Live Harness Record - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning

<domain>
## Phase Boundary

ANN15 is the final verification gate for annotation v0.3 Visual Reading Canvas. It does not add new canvas behavior. It proves, records, and separates the confidence levels for the read-only PaperForge-controlled Reading Canvas, existing v0.2 annotation fallback paths, and live Obsidian behavior.

In plain terms: this phase should run a focused automated gate for the v0.3 canvas and v0.2 fallback surface, audit read-only/safety boundaries without mistaking existing legacy fallback code for new canvas risk, and create a live harness record that says exactly what was observed in Obsidian and what remains pending.

This phase must not broaden into new UI features, local annotation editing, Zotero write-back, persistent layout, PDF.js rendering, native PDF DOM anchoring, AI cards, or multi-paper boards.

</domain>

<decisions>
## Implementation Decisions

### Automated Gate Boundary
- **D-01:** ANN15's hard automated gate is a focused slice: v0.3 canvas tests plus v0.2 annotation fallback preservation. Broader plugin or full-repo suites may be run as informational checks, but unrelated baseline failures must not block ANN15.
- **D-02:** Non-ANN15 failures discovered in broader/plugin suites should be recorded in a `Baseline` bucket with command, failure summary, and rationale for why the failure is unrelated to ANN15.
- **D-03:** ANN15-CONTEXT must lock an explicit minimum command list. Planners may add commands, but they must not replace or omit the minimum focused slice commands.
- **D-04:** Focused slice failures are ANN15 blockers and should be fixed before completion unless the failure is proven unrelated baseline behavior and explicitly moved out of the hard gate.

### Minimum Focused Commands
- **D-05:** The minimum syntax gate must include `node --check main.js` from `paperforge/plugin`.
- **D-06:** The minimum canvas module syntax gate must include `node --check` for ANN10-ANN14 canvas modules, including `src/canvas/context.js`, `annotations.js`, `controller.js`, `view-model.js`, `layout.js`, `surface.js`, `anchors.js`, `navigation.js`, `connectors.js`, `render.js`, and `index.js` when those files exist.
- **D-07:** The minimum v0.3 canvas Vitest slice must include `canvas-context.test.mjs`, `canvas-controller.test.mjs`, `canvas-viewmodel.test.mjs`, `canvas-layout.test.mjs`, `canvas-source-anchor.test.mjs`, `canvas-navigation.test.mjs`, `canvas-connectors.test.mjs`, `canvas-render.test.mjs`, `canvas-card-dom.test.mjs`, and `canvas-main-runtime.test.mjs`.
- **D-08:** The minimum v0.2 fallback preservation slice must include `annotation-navigation.test.mjs`, `annotation-main-runtime.test.mjs`, `annotation-section-dom.test.mjs`, and `annotation-overlay.test.mjs`.

### Live Obsidian Harness Record
- **D-09:** ANN15 should create a `LIVE-HARNESS.md` manual checklist and evidence note. Screenshots or video are not required, but the note must be audit-ready.
- **D-10:** `LIVE-HARNESS.md` must record environment, sample paper, operation steps, observations, per-step status, final conclusion, and limitations.
- **D-11:** The live harness should validate the Canvas-first workflow: open active-paper Reading Canvas, central reading surface, side card lanes, card/source focus, connector behavior, fallback button, refresh, and teardown.
- **D-12:** Native PDF overlay confidence must remain separately labeled. Do not merge v0.2 native PDF overlay confidence into v0.3 PaperForge Canvas confidence.
- **D-13:** If the current environment cannot open Obsidian or run the live harness, ANN15 should still create `LIVE-HARNESS.md` and mark live status as `PENDING - not executed in this environment`.
- **D-14:** jsdom or automated tests must not be presented as a substitute for live Obsidian behavior.
- **D-15:** Live harness step statuses should use `PASS`, `FAIL`, `PENDING`, and `NOT APPLICABLE`, with a final overall conclusion.

### Safety Audit Scope
- **D-16:** Safety scans should be scoped plus allowlisted. Scan ANN10-ANN15 canvas-owned files, relevant tests, and CSS/connector surfaces; explicitly allow existing v0.2 fallback, storage, settings, and native PDF overlay occurrences.
- **D-17:** Safety checks must prove three boundaries: no read-only-breaking controls, no canvas-owned persistence/write side effects, and no canvas-owned native PDF viewer DOM dependency.
- **D-18:** Allowed legacy hits such as existing `main.js` storage/settings/PDF overlay paths should be listed in an `Allowed legacy occurrences` table with file, pattern, and reason.
- **D-19:** Canvas-owned files and ANN15 changes are strict: read/write/native-DOM violations are blockers. Allowlisted legacy occurrences are recorded but do not block.
- **D-20:** The ANN14 lesson is locked in: do not use a broad forbidden scan that treats every pre-existing `pdf-viewer`, `pdf-embed`, `data-page-number`, `localStorage`, `annotations.db`, or `saveData` occurrence as an ANN15 failure.

### Final Confidence Report
- **D-21:** ANN15's final verification report should use a requirement matrix plus risk narrative. The matrix should status `SAFE-01` through `SAFE-04` and `TEST-01` through `TEST-05`.
- **D-22:** Report statuses should be `PASS`, `FAIL`, `PENDING`, and `BASELINE`. `PASS` means proven in ANN15 scope; `FAIL` is an ANN15 blocker; `PENDING` means live/environment/unproven; `BASELINE` means known non-ANN15 failure.
- **D-23:** The risk narrative must explain automated confidence, live harness state, baseline bucket, safety scan results, and unproven claims.
- **D-24:** The report must explicitly state the live/native split: automated/jsdom passing does not prove live Obsidian behavior, and v0.3 PaperForge Canvas passing does not prove v0.2 native PDF overlay behavior.
- **D-25:** Pending items must not be described as done, verified, or passed.
- **D-26:** v0.3 may be marked conditionally complete if the focused automated gate passes and `LIVE-HARNESS.md` exists. If the live harness is `PENDING`, completion text must carry that caveat.

### the agent's Discretion
The planner may choose exact filenames for the final verification report, exact table columns, helper scripts, and whether to include optional broader plugin/full-repo informational commands, as long as the explicit focused gate, live-harness honesty, scoped safety audit, and status vocabulary above are preserved.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Scope
- `.planning/PROJECT.md` - annotation v0.3 goal, read-only scope, v0.2 live harness caveat, and milestone completion context.
- `.planning/REQUIREMENTS.md` - SAFE-01 through SAFE-04 and TEST-01 through TEST-05 define ANN15's required verification scope.
- `.planning/ROADMAP.md` - ANN15 goal, dependency on ANN14, success criteria, and "do not skip live Obsidian harness recording" research flag.
- `.planning/STATE.md` - Current milestone state and known caveats; treat ROADMAP/REQUIREMENTS as authoritative if STATE lags.

### Prior Verification and Canvas Phases
- `.planning/phases/ANN14/ANN14-CONTEXT.md` - Connector eligibility, geometry, visual restraint, responsive, and safety boundaries that ANN15 must verify.
- `.planning/phases/ANN14/ANN14-VALIDATION.md` - Focused connector validation matrix and the scoped forbidden-scan correction that ANN15 should carry forward.
- `.planning/phases/ANN13/ANN13-CONTEXT.md` - Navigation, fallback, accessibility, lifecycle, and v0.2 PDF page fallback decisions to verify.
- `.planning/phases/ANN12/ANN12-CONTEXT.md` - PaperForge-owned source surface, exact/page-level/unresolved anchor decisions, native PDF DOM prohibition, and read-only boundary.
- `.planning/phases/annotation-09-display-layer-verification-gate/annotation-09-VERIFICATION.md` - v0.2 automated display-layer gate and pending live native PDF overlay harness record.

### Codebase Maps
- `.planning/codebase/TESTING.md` - Vitest, focused plugin test conventions, command shapes, and baseline-failure handling context.
- `.planning/codebase/CONVENTIONS.md` - CommonJS plugin style, safe DOM/text insertion, narrow helper exports, and test naming conventions.
- `.planning/codebase/STRUCTURE.md` - Plugin source/test file locations and where verification code belongs.

### Plugin Code and Tests
- `paperforge/plugin/main.js` - Obsidian plugin runtime, Reading Canvas view, v0.2 fallback/overlay code, storage/settings legacy occurrences, and syntax gate target.
- `paperforge/plugin/src/canvas/context.js` - Canvas paper context and explicit identity contract.
- `paperforge/plugin/src/canvas/annotations.js` - v0.2-compatible annotation loader wrapper.
- `paperforge/plugin/src/canvas/controller.js` - Canvas session controller, refresh, stale, and teardown lifecycle.
- `paperforge/plugin/src/canvas/view-model.js` - Card view-model and read-only card data contract.
- `paperforge/plugin/src/canvas/layout.js` - Deterministic side-lane placement.
- `paperforge/plugin/src/canvas/surface.js` - PaperForge-owned source surface and source block contract.
- `paperforge/plugin/src/canvas/anchors.js` - Exact/page-level/unresolved anchor contracts.
- `paperforge/plugin/src/canvas/navigation.js` - ANN13 selection, fallback, lifecycle, and accessibility state.
- `paperforge/plugin/src/canvas/connectors.js` - ANN14 connector eligibility and geometry helpers.
- `paperforge/plugin/src/canvas/render.js` - Canvas DOM rendering, source/card/fallback/connector surfaces, and safe text insertion.
- `paperforge/plugin/src/canvas/index.js` - Canvas CommonJS export surface.
- `paperforge/plugin/styles.css` - Reading Canvas namespace, connector classes, responsive hiding, and selected/focus/fallback styling.
- `paperforge/plugin/tests/canvas-context.test.mjs`, `canvas-controller.test.mjs`, `canvas-viewmodel.test.mjs`, `canvas-layout.test.mjs`, `canvas-source-anchor.test.mjs`, `canvas-navigation.test.mjs`, `canvas-connectors.test.mjs`, `canvas-render.test.mjs`, `canvas-card-dom.test.mjs`, `canvas-main-runtime.test.mjs` - Minimum v0.3 canvas focused gate.
- `paperforge/plugin/tests/annotation-navigation.test.mjs`, `annotation-main-runtime.test.mjs`, `annotation-section-dom.test.mjs`, `annotation-overlay.test.mjs` - Minimum v0.2 fallback/overlay preservation gate.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Existing focused Vitest files already cover most ANN10-ANN14 behavior and should become the hard ANN15 gate rather than inventing a separate test harness.
- ANN14's `ANN14-VALIDATION.md` already defines scoped connector/safety scan examples and explicitly avoids broad false-positive scans against legacy v0.2 paths.
- v0.2 `annotation-*` plugin tests preserve the existing annotation list, page jump, overlay, and fallback behavior required by CANVAS-05 and TEST-04/TEST-05.
- `paperforge/plugin/main.js` contains both new Reading Canvas runtime and legacy plugin settings/storage/native overlay paths, so ANN15 scans must classify occurrences by ownership rather than by raw token presence.

### Established Patterns
- Plugin tests run with Vitest from `paperforge/plugin`.
- Plugin JavaScript uses CommonJS modules under `paperforge/plugin/src/canvas/` and `require('./src/canvas')` from `main.js`.
- User-facing canvas DOM should use safe DOM/text APIs and namespaced CSS.
- Known baseline failures should be separated from focused phase blockers rather than driving unrelated refactors.
- Live Obsidian behavior and jsdom behavior are different confidence layers and should be reported separately.

### Integration Points
- The final automated gate should run from `paperforge/plugin`.
- The final verification report should consume test results, safety scan results, baseline-bucket notes, and `LIVE-HARNESS.md`.
- `LIVE-HARNESS.md` should live under `.planning/phases/ANN15-canvas-verification-gate-and-live-harness-record/` unless the planner chooses a more specific phase-local path.
- State/milestone completion updates should cite focused gate status and live harness status separately.

</code_context>

<specifics>
## Specific Ideas

- Treat ANN15 as an honesty gate rather than a feature phase.
- A conditional complete is acceptable only when the focused automated gate passes and a live harness record exists.
- `PENDING` is an honest state, not a failure, when the environment cannot run live Obsidian; it must not be renamed to `PASS`.
- The final report should be useful to a future maintainer who needs to know exactly which behaviors are proven, which are live-pending, and which failures are unrelated baseline issues.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within ANN15 scope.

</deferred>

---

*Phase: ANN15-canvas-verification-gate-and-live-harness-record*
*Context gathered: 2026-07-07*
