# ANN15 Research: Canvas Verification Gate and Live Harness Record

## Research Complete

ANN15 is a verification and reporting phase, not a feature phase. The existing canvas and annotation test files already provide the right focused gate surface; the plan should organize them into a repeatable evidence chain, add audit/report artifacts, and avoid broad scans that misclassify legacy v0.2 plugin code.

## Existing Verification Surface

### Plugin command surface

`paperforge/plugin/package.json` defines:

```powershell
npm.cmd test -- <test files>
```

because `npm test` maps to `vitest run`. Syntax checks can run directly with `node --check`.

### Canvas module syntax targets

The current canvas module set is:

- `src/canvas/anchors.js`
- `src/canvas/annotations.js`
- `src/canvas/connectors.js`
- `src/canvas/context.js`
- `src/canvas/controller.js`
- `src/canvas/index.js`
- `src/canvas/layout.js`
- `src/canvas/navigation.js`
- `src/canvas/render.js`
- `src/canvas/surface.js`
- `src/canvas/view-model.js`

These match ANN15-CONTEXT D-06. The plan should avoid PowerShell glob assumptions for `node --check`; list files explicitly or use a PowerShell-native enumeration in execution instructions.

### Focused canvas tests

Existing canvas-focused tests:

- `canvas-context.test.mjs`
- `canvas-controller.test.mjs`
- `canvas-viewmodel.test.mjs`
- `canvas-layout.test.mjs`
- `canvas-source-anchor.test.mjs`
- `canvas-navigation.test.mjs`
- `canvas-connectors.test.mjs`
- `canvas-render.test.mjs`
- `canvas-card-dom.test.mjs`
- `canvas-main-runtime.test.mjs`

`canvas-section-dom.test.mjs` also exists, but it is not part of the locked minimum in CONTEXT.md. The planner may include it as an additional focused check if it remains relevant and stable.

### v0.2 fallback preservation tests

Existing annotation fallback/overlay tests required by the minimum slice:

- `annotation-navigation.test.mjs`
- `annotation-main-runtime.test.mjs`
- `annotation-section-dom.test.mjs`
- `annotation-overlay.test.mjs`

These cover annotation list/page jump/overlay/fallback preservation and prevent ANN15 from treating the canvas as the only usable surface.

## Recommended Verification Artifacts

ANN15 should create or update phase-local artifacts under `.planning/phases/ANN15/`:

- `ANN15-VERIFICATION.md` - final requirement matrix and risk narrative.
- `LIVE-HARNESS.md` - manual Obsidian checklist/evidence note.
- `ANN15-SAFETY-AUDIT.md` - scoped safety scan results, blockers, and allowed legacy occurrences.
- Optional helper script or npm-free command block embedded in a plan if the executor needs a stable way to run the focused command list.

If the slug directory also exists, the executor should keep `.planning/phases/ANN15/` as the canonical execution directory because `gsd-tools` recognizes it as the active phase directory.

## Command Slice Recommendation

From `paperforge/plugin`:

```powershell
node --check main.js
node --check src/canvas/context.js
node --check src/canvas/annotations.js
node --check src/canvas/controller.js
node --check src/canvas/view-model.js
node --check src/canvas/layout.js
node --check src/canvas/surface.js
node --check src/canvas/anchors.js
node --check src/canvas/navigation.js
node --check src/canvas/connectors.js
node --check src/canvas/render.js
node --check src/canvas/index.js
npm.cmd test -- canvas-context.test.mjs canvas-controller.test.mjs canvas-viewmodel.test.mjs canvas-layout.test.mjs canvas-source-anchor.test.mjs canvas-navigation.test.mjs canvas-connectors.test.mjs canvas-render.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs
npm.cmd test -- annotation-navigation.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs annotation-overlay.test.mjs
```

Broader `npm.cmd test` or repo-wide Python tests can be optional informational checks. Failures outside the focused slice should be recorded in a `BASELINE` bucket with command, summary, and why they are outside ANN15.

## Safety Scan Strategy

Use scoped scans and ownership classification:

### Canvas-owned strict targets

- `src/canvas/*.js`
- `tests/canvas-*.test.mjs`
- `styles.css` selectors under `.paperforge-reading-canvas-view`
- ANN15-created verification/liveness artifacts

### Allowlisted legacy areas

- `main.js` plugin settings and `saveData` paths.
- `main.js` existing v0.2 native PDF overlay code using `.pdf-embed`, `.pdf-viewer`, `[data-page-number]`.
- `src/testable.js` and annotation tests that intentionally reference `annotations.db`, `localStorage`, PDF target resolution, or overlay behavior.

These should be documented in an `Allowed legacy occurrences` table rather than treated as blockers.

### Forbidden in canvas-owned code

- create/edit/delete/save/import/apply/write-back controls.
- `annotations.db`, Zotero mutation, vault-note mutation, plugin setting persistence, `localStorage`, persistent layout state.
- native PDF viewer DOM selectors such as `.pdf-viewer`, `.pdf-embed`, `.pdf-container`, `[data-page-number]`.
- evidence/concept-card mutation controls.

## Live Harness Representation

`LIVE-HARNESS.md` should be created even when live Obsidian is unavailable. If not executed, mark:

```text
Overall status: PENDING - not executed in this environment
```

The checklist should be Canvas-first:

1. Open a recognized active paper.
2. Open PaperForge Reading Canvas.
3. Verify central reading surface and side lanes.
4. Select card -> source focus.
5. Select source -> card focus.
6. Verify focused connector behavior.
7. Verify fallback button remains explicit.
8. Refresh and stale handling.
9. Teardown/paper change clears transient state.

Each step should use `PASS`, `FAIL`, `PENDING`, or `NOT APPLICABLE`. Native PDF overlay must be separate and not merged into PaperForge Canvas confidence.

## Recommended Plan Split

1. **ANN15-01: Focused automated gate contract and command runner**
   - locks the focused command slice, optionally introduces a small phase-local verification helper, and records baseline-bucket rules.

2. **ANN15-02: Safety audit and scoped scan evidence**
   - creates `ANN15-SAFETY-AUDIT.md`, runs scoped scans, records blockers and allowed legacy occurrences.

3. **ANN15-03: Live harness record**
   - creates `LIVE-HARNESS.md` with Canvas-first checklist, pending policy, status vocabulary, and native/live split.

4. **ANN15-04: Final verification report and milestone confidence**
   - creates `ANN15-VERIFICATION.md`, maps SAFE/TEST requirements to `PASS/FAIL/PENDING/BASELINE`, explains automated vs live confidence, and records conditional-complete caveat.

## Risks and Planner Notes

- There are two ANN15 directories in the worktree because `gsd-tools` recognizes `.planning/phases/ANN15` but discuss-phase initially created the slug directory. Plans should use `.planning/phases/ANN15` as canonical.
- PowerShell wildcard behavior differs between native command arguments and shell expansion. Plans should list focused test files explicitly.
- Broad token scans across all of `main.js` will produce false positives from existing v0.2 overlay/settings/storage code. Use scoped scans and legacy tables.
- A successful jsdom gate must not be worded as live Obsidian proof.
- `PENDING` live harness status is acceptable when the environment cannot run Obsidian, but it must be visible in final completion wording.

## RESEARCH COMPLETE
