---
phase: annotation-07-pdf-jump-navigation
plan: 03
type: execute
wave: 3
depends_on:
  - annotation-07-02
files_modified:
  - paperforge/plugin/main.js
  - paperforge/plugin/styles.css
  - paperforge/plugin/tests/annotation-section-dom.test.mjs
autonomous: true
requirements:
  - OVLY-01

must_haves:
  truths:
    - "D-01: The existing page badge is a semantic row-level jump button; the rest of the row is not clickable."
    - "D-02: Enabled jump buttons have a concise tooltip and accessible label that identify the source-PDF/page action."
    - "D-03: Page-badge navigation and expand/collapse are independent event paths in both directions."
    - "D-07: A row whose attachment identity cannot be resolved renders an unavailable/disabled jump control and never navigates."
    - "D-11: A row with a confirmed PDF but invalid page data remains enabled for plain-PDF opening."
    - "D-13: Clicking jump preserves search, grouping, filter, expansion, and loaded annotation state."
    - "D-15: The new affordance remains read-only and adds no overlay, edit, delete, save, write-back, or database controls."
  artifacts:
    - path: "paperforge/plugin/main.js"
      provides: "Semantic page-badge jump button wired to the runtime opener"
      contains: "paperforge-annotation-page-badge"
    - path: "paperforge/plugin/styles.css"
      provides: "Compact button reset, hover, focus-visible, and unavailable states"
      contains: ".paperforge-annotation-page-badge"
    - path: "paperforge/plugin/tests/annotation-section-dom.test.mjs"
      provides: "DOM semantics, accessibility, click-isolation, disabled-state, and scope regression coverage"
  key_links:
    - from: "paperforge/plugin/main.js::_renderAnnotationRows"
      to: "PaperForgeStatusView annotation opener"
      via: "page badge click handler only"
      pattern: "paperforge-annotation-page-badge"
    - from: "paperforge/plugin/main.js"
      to: "paperforge/plugin/styles.css"
      via: "existing page-badge class with button state selectors"
      pattern: "paperforge-annotation-page-badge"
---

<objective>
Expose the runtime navigation through an accessible, compact page-badge button while preserving independent expansion behavior and the Phase 8 scope fence.

Purpose: Complete the user-facing OVLY-01 interaction without destabilizing the Phase 6 annotation list.
Output: Row jump affordance, interaction styling, and DOM regression coverage.
</objective>

<execution_context>
@C:/Users/tan/.codex/gsd-core/workflows/execute-plan.md
@C:/Users/tan/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-CONTEXT.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-PATTERNS.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-02-SUMMARY.md
@.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-04-SUMMARY.md
@paperforge/plugin/main.js
@paperforge/plugin/styles.css
@paperforge/plugin/tests/annotation-section-dom.test.mjs

<interfaces>
`_renderAnnotationRows()` currently creates a span page badge and a separate button `.paperforge-annotation-expand-btn`. Plan 02 provides the async annotation opener. The DOM harness supports `title`, arbitrary attributes, recursive `createEl`, and spies for `workspace.openLinkText` and `fileManager.processFrontMatter`.
</interfaces>
</context>

## Artifacts this phase produces

- The visible page badge as the explicit accessible jump action.
- Compact hover/focus/unavailable styles aligned with the existing annotation row.
- DOM regression tests proving navigation/expansion isolation and excluding Phase 8 overlay behavior.

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: Convert the page badge into an accessible isolated jump control</name>
  <files>
    paperforge/plugin/main.js
    paperforge/plugin/tests/annotation-section-dom.test.mjs
  </files>
  <read_first>
    - `paperforge/plugin/main.js` `_renderAnnotationRows()` and the Plan 02 annotation opener.
    - `paperforge/plugin/tests/annotation-section-dom.test.mjs` page badge, expand-button, forbidden-control, and runtime fixture tests.
    - `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-CONTEXT.md` decisions D-01 through D-03, D-07, D-11, D-13, and D-15.
  </read_first>
  <behavior>
    - A resolvable row renders `.paperforge-annotation-page-badge` as `BUTTON` with tooltip and `aria-label` describing the source PDF and display page.
    - An unresolved/ambiguous attachment renders the same control disabled with `aria-disabled="true"` and an unavailable explanation; clicking it opens nothing.
    - A confirmed PDF with invalid page data remains enabled because D-11 allows plain-PDF opening.
    - Clicking the page badge invokes navigation once and leaves `expandedIds`, query, grouping, filter, and loaded rows unchanged.
    - Clicking expand changes only expansion state/rerenders and never calls `workspace.openLinkText`.
    - No click handler is added to `.paperforge-annotation-row`.
  </behavior>
  <action>
    Replace the page badge span in `_renderAnnotationRows()` with a semantic button using the existing class. Resolve availability without side effects, add concise English `title` and `aria-label` text, and disable only when the PDF target itself is unresolved. Bind its click handler only to the Plan 02 opener and stop event propagation; keep the existing expand listener separate and unchanged except for test-required async handling.

    Update the DOM fixtures to include realistic `pdfLocation` and canonical paper PDF metadata. Replace the Phase 6 assertion that forbids PDF jump controls with positive jump-button assertions, while retaining the prohibitions on overlay/popover, edit/delete, save/write-back, database mutation, and concept evidence controls.
  </action>
  <verify>
    <automated>node --check paperforge/plugin/main.js</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-section-dom.test.mjs</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-main-runtime.test.mjs</automated>
  </verify>
  <acceptance_criteria>
    Enabled and unavailable button semantics are automated, jump and expand are isolated in both directions, invalid-page rows still permit plain-PDF navigation, and no row-level click behavior exists.
  </acceptance_criteria>
  <done>D-01 through D-03 are visible in the DOM and D-07/D-11/D-13/D-15 remain enforced.</done>
</task>

<task type="auto">
  <name>Task 2: Style jump states and run consolidated plugin regressions</name>
  <files>
    paperforge/plugin/styles.css
    paperforge/plugin/tests/annotation-section-dom.test.mjs
  </files>
  <read_first>
    - `paperforge/plugin/styles.css` existing `.paperforge-annotation-page-badge` and `.paperforge-annotation-expand-btn` rules.
    - `paperforge/plugin/tests/annotation-section-dom.test.mjs` Task 1 semantics and scope-regression assertions.
    - `.planning/STATE.md` three known unrelated plugin baseline failures.
  </read_first>
  <action>
    Reset native button chrome while retaining the existing compact badge dimensions, then add clear hover, keyboard `:focus-visible`, and disabled/unavailable styles using existing Obsidian CSS variables. Do not merge jump and expand selectors where their semantics differ, and do not add overlay selectors or viewer-internal hooks.

    Run focused helper, runtime, and DOM suites, then run the full plugin suite. Treat the recorded two `buildRuntimeInstallCommand` failures and one Windows `resolvePythonExecutable` failure as the only known baseline; any additional failure blocks completion and must be fixed in Phase 7 files without weakening tests.
  </action>
  <verify>
    <automated>powershell -NoProfile -Command "$css=Get-Content -Raw 'paperforge/plugin/styles.css'; foreach ($token in @('.paperforge-annotation-page-badge',':focus-visible',':disabled')) { if ($css -notmatch [regex]::Escape($token)) { throw ('Missing jump-control CSS token: ' + $token) } }; Write-Output 'Jump-control CSS tokens present.'"</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-navigation.test.mjs tests/annotation-main-runtime.test.mjs tests/annotation-section-dom.test.mjs tests/annotation-bridge.test.mjs</automated>
    <automated>npm.cmd --prefix paperforge/plugin test</automated>
    Full-suite expectation: no new failures beyond the three unrelated baseline failures recorded in `.planning/STATE.md`.
  </verify>
  <acceptance_criteria>
    The jump button is compact, keyboard-visible, and visibly unavailable when disabled; all focused Phase 7 tests pass; the full suite introduces no failure beyond the documented baseline.
  </acceptance_criteria>
  <done>The user-facing jump affordance is styled, accessible, regression-tested, and contains no Phase 8 overlay behavior.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Annotation row -> interactive DOM | Imported row metadata controls whether a navigation button is enabled. |
| Button click -> runtime opener | Only the page badge may cross into workspace navigation. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-annotation-07-08 | Spoofing | enabled jump affordance | mitigate | Compute availability with the same resolver used at execution and expose disabled semantics for unresolved identity. |
| T-annotation-07-09 | Tampering | row/expand event handling | mitigate | DOM tests prove no row click handler, jump does not expand, and expand does not navigate. |
| T-annotation-07-10 | Elevation of Privilege | annotation controls | mitigate | Regression tests retain absence of edit, delete, save, write-back, DB, and overlay controls. |
| T-annotation-07-11 | Denial of Service | keyboard/mouse activation | accept | One user activation causes one bounded runtime attempt with the Plan 02 single-retry limit. |
| T-annotation-07-SC | Tampering | package supply chain | accept | No package-manager install occurs; styling and tests use existing project dependencies. |
</threat_model>

<verification>
- `node --check paperforge/plugin/main.js`
- `npm.cmd --prefix paperforge/plugin test -- tests/annotation-navigation.test.mjs tests/annotation-main-runtime.test.mjs tests/annotation-section-dom.test.mjs tests/annotation-bridge.test.mjs`
- `npm.cmd --prefix paperforge/plugin test` with only the three documented unrelated baseline failures permitted.
</verification>

<success_criteria>
- [ ] Page badge is the only row-level jump action.
- [ ] Tooltip, aria-label, focus-visible, and disabled semantics are present.
- [ ] Jump and expansion controls are independent.
- [ ] Uncertain attachment identity is unavailable; invalid page data still opens a confirmed PDF.
- [ ] UI state and loaded rows survive navigation.
- [ ] No overlay, mutation, or editing behavior is introduced.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-03-SUMMARY.md`.
</output>
