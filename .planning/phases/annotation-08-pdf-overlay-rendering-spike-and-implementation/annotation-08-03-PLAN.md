---
phase: annotation-08-pdf-overlay-rendering-spike-and-implementation
plan: "03"
type: execute
wave: 3
depends_on:
  - annotation-08-02
files_modified:
  - paperforge/plugin/main.js
  - paperforge/plugin/styles.css
  - paperforge/plugin/tests/annotation-main-runtime.test.mjs
  - paperforge/plugin/tests/annotation-section-dom.test.mjs
requirements:
  - OVLY-02
  - OVLY-03
  - OVLY-05
requirements_addressed:
  - OVLY-02
  - OVLY-03
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
    - "OVLY-02: Runtime renders PaperForge-owned highlight marks only when the spike attach contract and helper mark model both confirm support."
    - "OVLY-03: Runtime overlay state is scoped to active paper, active PDF path, page layer, and annotation state; wrong PDF/page produces no mark."
    - "OVLY-05: Missing viewer internals, unsupported spike mode, refresh failure, or pane/file changes clear overlay marks and preserve sidebar/list/page badge behavior."
    - "Context decision coverage for this phase set is explicit: D-01 D-02 D-03 D-04 D-05 D-06 D-07 D-08 D-09 D-10 D-11 D-12 D-13 D-14 D-15 D-16 D-17 D-18 D-19 D-20 D-21 D-22 D-23 D-24."
    - "This plan directly implements D-01 D-02 D-03 D-04 D-05 D-06 D-07 D-08 D-09 D-10 D-11 D-12 D-13 D-18 D-19 D-20 D-22 D-24."
  artifacts:
    - path: "paperforge/plugin/main.js"
      provides: "Runtime overlay state, attach, render, refresh, and teardown"
      exports:
        - "__test.PaperForgeStatusView overlay methods as needed"
    - path: "paperforge/plugin/styles.css"
      provides: "SECTION 41 - PDF Annotation Overlay styling"
    - path: "paperforge/plugin/tests/annotation-main-runtime.test.mjs"
      provides: "Runtime attach/fallback/teardown coverage"
    - path: "paperforge/plugin/tests/annotation-section-dom.test.mjs"
      provides: "DOM regression coverage for overlay coexistence with annotation list"
  key_links:
    - from: "paperforge/plugin/main.js"
      to: "paperforge/plugin/src/testable.js"
      via: "inlined or mirrored overlay helper behavior"
      pattern: "buildAnnotationOverlayMarks"
    - from: "paperforge/plugin/main.js"
      to: "paperforge/plugin/styles.css"
      via: "paperforge-annotation-overlay-* class names"
      pattern: "paperforge-annotation-overlay"
---

<objective>
Implement runtime overlay state, safe attach/render, refresh, and teardown in `main.js`, with CSS and runtime/DOM tests.

Purpose: Turn the Plan 01 attach contract and Plan 02 helper view-models into actual PDF overlay behavior while keeping list and page-jump behavior independent and safe.
Output: PaperForge-owned overlay DOM, session-only overlay runtime state, and regression tests.
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
@.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-02-SUMMARY.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-03-SUMMARY.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-04-SUMMARY.md
@paperforge/plugin/main.js
@paperforge/plugin/src/testable.js
@paperforge/plugin/styles.css
@paperforge/plugin/tests/annotation-main-runtime.test.mjs
@paperforge/plugin/tests/annotation-section-dom.test.mjs
@paperforge/plugin/tests/annotation-navigation.test.mjs
@paperforge/plugin/tests/annotation-bridge.test.mjs
</context>

<source_audit>
GOAL: Covered by adding the runtime overlay layer over the native PDF viewer when available.
REQ: OVLY-02 is covered by rendering marks; OVLY-03 by active PDF/page scoping; OVLY-05 by fail-closed attach/teardown and list/jump preservation.
RESEARCH: Implements runtime shell ownership, PaperForge CSS namespace, bounded observer only if required by the spike, and no new dependencies.
CONTEXT: Implements D-01 through D-13, D-18 through D-20, D-22, and D-24 directly. D-14 through D-17 are completed in Plan 04 popover work but mark DOM must already be focusable/clickable for that interaction. Deferred ideas are not included.
</source_audit>

<tasks>

<task type="auto">
  <name>Task 1: Add session overlay state, safe attach, refresh, and teardown</name>
  <files>paperforge/plugin/main.js, paperforge/plugin/tests/annotation-main-runtime.test.mjs</files>
  <action>In `PaperForgeStatusView`, add session-only overlay fields such as `_annotationOverlayState`, `_annotationOverlayRootEl`, `_annotationOverlayObserver`, and `_annotationOverlayActiveKey`. Mirror the new pure helper behavior into `main.js` if the current Obsidian bundle still inlines `src/testable.js`. Add runtime methods `_clearAnnotationOverlay()`, `_tryAttachAnnotationOverlay(reason)`, and `_refreshAnnotationOverlay(reason)` or equivalent names. The attach path must read the Plan 01 spike contract behaviorally: no confirmed active paper, active PDF path, viewer root, page layer, or usable helper marks means no overlay render. Refresh must run after annotation load/refresh and paper-mode render, and teardown must run on active file/pane/paper identity or annotation-state changes per D-18 and D-19. Do not add continuous polling per D-20; a bounded `MutationObserver` is allowed only when attached and must be disconnected in `_clearAnnotationOverlay()`. Tests must use fake viewer DOM fixtures and prove unsupported viewer internals leave sidebar/list and Phase 7 page-badge behavior intact.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check main.js; npm.cmd test -- annotation-main-runtime.test.mjs annotation-overlay.test.mjs annotation-navigation.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>Runtime state is session-only, attach fails closed, teardown is deterministic, and existing list/jump runtime tests remain passing.</acceptance_criteria>
  <done>Overlay state/attach/refresh/teardown methods exist and are covered by runtime tests.</done>
</task>

<task type="auto">
  <name>Task 2: Render PaperForge-owned overlay marks and CSS without disrupting list DOM</name>
  <files>paperforge/plugin/main.js, paperforge/plugin/styles.css, paperforge/plugin/tests/annotation-section-dom.test.mjs</files>
  <action>Add `_renderAnnotationOverlayMarks(viewerContext, marks)` or equivalent to create only `.paperforge-annotation-overlay-*` nodes inside the confirmed viewer/page layer. Marks must be lightweight semi-transparent highlights per D-05 through D-07, use annotation color when normalized and restrained yellow otherwise, preserve PDF text readability, expose keyboard focus hooks for Plan 04, and remove only PaperForge-owned nodes during teardown. Add `SECTION 41 - PDF Annotation Overlay` in `styles.css`; style only `.paperforge-annotation-overlay-*` classes and avoid global PDF viewer selectors. Update the existing DOM test that forbids overlay/popover hooks so Phase 8 now positively verifies overlay coexistence while retaining stronger prohibitions against edit/delete/remove/write-back/database/evidence controls. Tests must verify page badge click still navigates independently, expand state is unchanged by overlay rendering, and failed attach does not hide or replace `.paperforge-annotations-section`.</action>
  <verify>
    <automated>powershell -NoProfile -Command "Push-Location paperforge/plugin; node --check main.js; npm.cmd test -- annotation-main-runtime.test.mjs annotation-section-dom.test.mjs annotation-overlay.test.mjs annotation-navigation.test.mjs annotation-bridge.test.mjs; Pop-Location"</automated>
  </verify>
  <acceptance_criteria>Overlay marks render only under confirmed viewer/page conditions, styling is namespaced, teardown removes marks, and sidebar/list/page-badge behavior remains unchanged.</acceptance_criteria>
  <done>Runtime mark rendering, CSS, and DOM regressions pass the focused annotation suite.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Obsidian PDF viewer DOM -> runtime attach | Viewer internals are unstable and untrusted until the spike contract and runtime checks confirm them. |
| Overlay helper marks -> DOM | Mark view-models become interactive DOM and must not inject user text as HTML. |
| Workspace events -> overlay lifecycle | File, pane, paper, and annotation changes can make existing marks stale. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-annotation-08-03-S | Spoofing | Active PDF/viewer match | mitigate | Confirm active PDF path and page layer before rendering; fail closed on mismatch or ambiguity. |
| T-annotation-08-03-T | Tampering | PDF viewer DOM | mitigate | Create and remove only `.paperforge-annotation-overlay-*` nodes; never delete broad viewer DOM. |
| T-annotation-08-03-R | Repudiation | Overlay state transitions | accept | No audit trail required for read-only display; tests document state transitions and fallback behavior. |
| T-annotation-08-03-I | Information Disclosure | Runtime errors and annotation text | mitigate | Use friendly notices/state, `textContent`/`setText`, and no raw errors, raw JSON, tracebacks, or shell output. |
| T-annotation-08-03-D | Denial of Service | Viewer DOM churn | mitigate | No continuous polling; bounded observer only while attached and disconnected during clear. |
| T-annotation-08-03-E | Elevation of Privilege | Annotation stores | mitigate | Runtime overlay is display-only and must not write Zotero, mutate `annotations.db`, save settings, or call import/apply. |
| T-annotation-08-03-SC | Tampering | npm/pip/cargo installs | accept | No package installs are planned; use existing test stack. |
</threat_model>

<verification>
Run `node --check main.js` and the focused annotation Vitest suites covering bridge, navigation, overlay helpers, runtime, and DOM.
</verification>

<success_criteria>
- Runtime overlay state exists and is session-only.
- Overlay attach/render occurs only when viewer internals and active PDF identity are confirmed.
- Teardown removes stale marks on file/pane/paper/annotation/viewer changes.
- Existing sidebar/list/filter/group/page-jump behavior is not broken.
</success_criteria>

<output>
Create `.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-03-SUMMARY.md` when done.
</output>
