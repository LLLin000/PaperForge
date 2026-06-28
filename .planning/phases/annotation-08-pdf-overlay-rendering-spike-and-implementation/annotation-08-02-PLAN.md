---
phase: annotation-08-pdf-overlay-rendering-spike-and-implementation
plan: "02"
type: execute
wave: 2
depends_on:
  - annotation-08-01
files_modified:
  - paperforge/plugin/src/testable.js
  - paperforge/plugin/tests/annotation-overlay.test.mjs
requirements:
  - OVLY-02
  - OVLY-03
  - OVLY-04
  - OVLY-05
requirements_addressed:
  - OVLY-02
  - OVLY-03
  - OVLY-04
  - OVLY-05
autonomous: true
decision_coverage:
  - D-01
  - D-02
  - D-03
  - D-04
  - D-05
  - D-06
  - D-07
  - D-08
  - D-09
  - D-10
  - D-11
  - D-12
  - D-13
  - D-14
  - D-15
  - D-16
  - D-17
  - D-18
  - D-19
  - D-20
  - D-21
  - D-22
  - D-23
  - D-24
must_haves:
  truths:
    - "OVLY-02: Pure helpers produce renderable overlay mark view-models only for confirmed active PDF/page matches."
    - "OVLY-03: Overlay eligibility and geometry use pdfLocation.pageIndex, positionJson, selectorJson, and sourceAttachmentKey; pageLabel remains display-only."
    - "OVLY-04: Popover/detail data is shaped as read-only view-model content without edit/delete/create controls."
    - "OVLY-05: Invalid JSON, missing rects, missing page, wrong attachment, or unsupported spike mode returns empty marks with friendly reasons."
    - "Context decision coverage for this phase set is explicit: D-01 D-02 D-03 D-04 D-05 D-06 D-07 D-08 D-09 D-10 D-11 D-12 D-13 D-14 D-15 D-16 D-17 D-18 D-19 D-20 D-21 D-22 D-23 D-24."
    - "This plan directly implements D-02 D-05 D-06 D-07 D-08 D-09 D-10 D-11 D-12 D-13 D-15 D-17 D-22 D-24."
  artifacts:
    - path: "paperforge/plugin/src/testable.js"
      provides: "Pure overlay state, geometry, color, mark, and popover view-model helpers"
      exports:
        - createDefaultAnnotationOverlayState
        - parseAnnotationPositionJson
        - normalizeAnnotationColor
        - buildAnnotationOverlayMarks
        - buildAnnotationPopoverViewModel
    - path: "paperforge/plugin/tests/annotation-overlay.test.mjs"
      provides: "Vitest coverage for overlay helper contracts"
  key_links:
    - from: "paperforge/plugin/src/testable.js"
      to: "resolveAnnotationPdfTarget"
      via: "identity guard before overlay mark construction"
      pattern: "resolveAnnotationPdfTarget"
    - from: "paperforge/plugin/tests/annotation-overlay.test.mjs"
      to: "paperforge/plugin/src/testable.js"
      via: "imports pure helper exports"
      pattern: "buildAnnotationOverlayMarks"
---

<objective>
Add deterministic overlay eligibility, geometry, color, and popover view-model helpers in `src/testable.js` with focused Vitest coverage.

Purpose: Runtime overlay rendering must be a thin shell over pure fail-closed decisions so PDF identity, page, and position logic is testable without live Obsidian.
Output: Exported helper functions and `annotation-overlay.test.mjs`.
</objective>

<execution_context>
@C:/Users/tan/.codex/gsd-core/workflows/execute-plan.md
@C:/Users/tan/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md
@.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-RESEARCH.md
@.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PATTERNS.md
@.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PDF-VIEWER-SPIKE.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-03-SUMMARY.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-04-SUMMARY.md
@paperforge/plugin/src/testable.js
@paperforge/plugin/tests/annotation-navigation.test.mjs
@paperforge/plugin/tests/annotation-bridge.test.mjs
</context>

<source_audit>
GOAL: Covered by building the pure contract runtime overlay rendering will consume.
REQ: OVLY-02 mark view-models, OVLY-03 scoped position/page/PDF matching, OVLY-04 popover data, and OVLY-05 fail-closed helper results are planned here.
RESEARCH: Implements the recommended pure helper boundary and no-install stack.
CONTEXT: Implements D-02, D-05, D-06, D-07, D-08, D-09, D-10, D-11, D-12, D-13, D-15, D-17, D-22, and D-24 directly. D-01, D-03, D-04, D-14, D-16, D-18, D-19, D-20, D-21, and D-23 are preserved through result shape and later runtime plans. Deferred ideas are not included.
</source_audit>

<tasks>

<task type="auto">
  <name>Task 1: Add overlay state, position parsing, and color helpers</name>
  <files>paperforge/plugin/src/testable.js, paperforge/plugin/tests/annotation-overlay.test.mjs</files>
  <action>Add and export `createDefaultAnnotationOverlayState()`, `parseAnnotationPositionJson(positionJson)`, and `normalizeAnnotationColor(color)`. `createDefaultAnnotationOverlayState()` returns a session-only object with stable fields such as `status`, `reason`, `paperKey`, `pdfPath`, `viewerAttached`, and `activePopoverId`; it must not persist settings or touch storage. `parseAnnotationPositionJson()` accepts the preserved `pdfLocation.positionJson`, validates a JSON object with same-page rect data, and returns `{ ok:false, rects:[], reason }` for missing, invalid, empty, non-numeric, negative, or unsupported shapes without throwing. `normalizeAnnotationColor()` accepts usable hex/rgb-like annotation colors and otherwise returns the restrained default yellow required by D-06. Tests must cover valid rects, invalid JSON, empty rects, missing page, non-mutating inputs, restrained default yellow, and friendly reasons with no raw stack traces.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check src/testable.js; npm.cmd test -- annotation-overlay.test.mjs annotation-bridge.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>The helper exports exist, invalid position/color data fails closed without throwing, and bridge preservation tests still pass.</acceptance_criteria>
  <done>State, position parsing, and color helpers are exported and covered by focused tests.</done>
</task>

<task type="auto">
  <name>Task 2: Build overlay mark and read-only popover view-model helpers</name>
  <files>paperforge/plugin/src/testable.js, paperforge/plugin/tests/annotation-overlay.test.mjs</files>
  <action>Add and export `buildAnnotationOverlayMarks(annotationState, entry, activePdfPath, options)` and `buildAnnotationPopoverViewModel(row)`. `buildAnnotationOverlayMarks()` must consume normalized rows only, call or reuse `resolveAnnotationPdfTarget()` before any mark is created, compare the resolved PDF path to `activePdfPath`, use `pdfLocation.pageIndex` for machine page matching, ignore `pageLabel` for arithmetic, skip rows without usable position/selector data, and return a stable `{ ok, status, marks, skipped, reason }` shape. Each mark must include a stable annotation identity, pageIndex, rect geometry, normalized color, selected text/comment snippets, source/read-only provenance, and target PDF path. `buildAnnotationPopoverViewModel()` must expose selected text, comment, page label/page number, source, read-only state, attachment/annotation identity, and no edit/delete/create/write-back/database/evidence actions per D-14 through D-17. Tests must include wrong attachment, supplemental mismatch, active PDF mismatch, invalid position JSON, missing rects, missing page, and unsupported spike mode if the spike document recorded unsupported.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check src/testable.js; npm.cmd test -- annotation-overlay.test.mjs annotation-navigation.test.mjs annotation-bridge.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>Overlay mark construction is purely derived from normalized annotation state and confirmed PDF identity; popover data is read-only and safe for DOM text rendering.</acceptance_criteria>
  <done>Overlay mark and popover view-model helpers pass helper, navigation, and bridge tests.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI-normalized annotation rows -> overlay helpers | Annotation position/color/text/provenance values are untrusted display inputs. |
| Paper entry metadata -> PDF identity matching | PDF paths and attachment keys must be resolved through existing helper contracts. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-annotation-08-02-S | Spoofing | `buildAnnotationOverlayMarks` | mitigate | Require `resolveAnnotationPdfTarget()` and active PDF path equality before creating a mark. |
| T-annotation-08-02-T | Tampering | Helper inputs | mitigate | Do not mutate annotation rows, paper entries, or helper options; tests assert immutable input behavior. |
| T-annotation-08-02-I | Information Disclosure | Helper reason strings | mitigate | Return stable friendly reasons only; tests reject stack traces, raw JSON dumps, shell output, and local absolute paths. |
| T-annotation-08-02-D | Denial of Service | Position parsing | mitigate | Bound parsing to JSON object/array validation and skip bad rows instead of throwing or looping. |
| T-annotation-08-02-E | Elevation of Privilege | Popover view model | mitigate | Expose read-only display fields only; no edit/delete/create/write-back/database/evidence actions. |
| T-annotation-08-02-SC | Tampering | npm/pip/cargo installs | accept | No package installs are planned; use existing Vitest/jsdom stack. |
</threat_model>

<verification>
Run focused helper tests plus existing navigation and bridge tests. No Obsidian live viewer is required for this plan.
</verification>

<success_criteria>
- `annotation-overlay.test.mjs` exists and passes.
- `src/testable.js` exports overlay helpers without breaking existing annotation helper exports.
- Helper behavior is read-only, fail-closed, and scoped to active PDF identity and page data.
</success_criteria>

<output>
Create `.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-02-SUMMARY.md` when done.
</output>
