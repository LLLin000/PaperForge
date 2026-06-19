---
phase: annotation-06-annotation-sidebar-and-list-view
plan: 04
type: execute
wave: 4
depends_on:
  - annotation-06-03
files_modified:
  - paperforge/plugin/styles.css
  - paperforge/plugin/tests/annotation-section-dom.test.mjs
autonomous: true
requirements:
  - LIST-01
  - LIST-02
  - LIST-05

must_haves:
  truths:
    - "D-04: Long annotation lists are bounded with internal list scrolling and do not consume the whole paper panel."
    - "D-05: Annotation rows use a compact row-list layout, not large cards."
    - "D-06: Default row preview clamps selected text to 2 lines and comment to 1 line."
    - "D-07: Long selected text or comments can expand inline."
    - "D-08: Each row always shows page, color/type, selected text preview, and comment icon or comment summary."
    - "D-09: Provenance details stay in row expansion details, not default rows."
    - "D-10: Color/type is represented as a small color swatch plus type label."
    - "D-24: Styling/regression work does not add PDF jump/open-at-page actions."
    - "D-25: Styling/regression work does not add overlay rendering, PDF popovers, local editing, Zotero write-back, database mutation, or concept evidence wiring."
  artifacts:
    - path: "paperforge/plugin/styles.css"
      provides: "Bounded compact annotation list styling"
      contains: "paperforge-annotations-section"
    - path: "paperforge/plugin/tests/annotation-section-dom.test.mjs"
      provides: "DOM regression coverage for bounded list classes, previews, expansion details, swatch/type, and forbidden controls"
  key_links:
    - from: "paperforge/plugin/main.js"
      to: "paperforge/plugin/styles.css"
      via: "stable annotation section and row class names created in Plan 03"
      pattern: "paperforge-annotation-row|paperforge-annotation-selected-text|paperforge-annotation-comment"
---

<objective>
Finish the annotation list as a bounded, compact, readable UI and run plugin regressions.

Purpose: Ensure the Phase 6 list remains scannable in long papers and does not regress the existing PaperForge panel.
Output: CSS for the annotation section plus DOM/regression tests.
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
@.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-CONTEXT.md
@.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-RESEARCH.md
@.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-02-SUMMARY.md
@.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-03-SUMMARY.md
@paperforge/plugin/styles.css
@paperforge/plugin/main.js
@paperforge/plugin/tests/annotation-main-runtime.test.mjs
@paperforge/plugin/package.json

Narrow-read `paperforge/plugin/styles.css` around existing PaperForge paper-mode patterns:
- `.paperforge-paper-view`
- `.paperforge-paper-overview`
- `.paperforge-next-step-card`
- `.paperforge-contextual-btn`
- `.paperforge-empty-state`
- `.paperforge-section-label`
- `.paperforge-status-strip`
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add bounded compact annotation list styles</name>
  <files>
    paperforge/plugin/styles.css
  </files>
  <action>
    Add CSS for the class hooks created by Plan 03. Use existing PaperForge panel visual language and restrained spacing. The annotation section should look like an integrated paper-mode section, not a separate floating card.

    Style the list as compact rows with stable dimensions: section header, controls row, bounded internal scroll area, row meta line, page badge, color swatch plus type label, selected-text preview, comment preview/icon, and inline expansion details. Clamp selected text to 2 lines and comment to 1 line by default. Keep provenance/read-only/source/attachment/timestamp details hidden until the row is expanded. Ensure long lists use `max-height` or equivalent internal scrolling so they do not dominate the paper panel.

    Do not add behavior in this plan. If Plan 03 did not create the needed class hooks in `main.js`, stop and report Plan 03 incomplete rather than adding runtime behavior here.
  </action>
  <verify>
    <automated>powershell -NoProfile -Command "$css=Get-Content -Raw 'paperforge/plugin/styles.css'; foreach ($token in @('paperforge-annotations-section','paperforge-annotations-list','paperforge-annotation-row','paperforge-annotation-swatch','paperforge-annotation-selected-text','paperforge-annotation-comment')) { if ($css -notmatch $token) { throw ('Missing CSS token: ' + $token) } }; Write-Output 'Annotation CSS tokens present.'"</automated>
  </verify>
  <done>The annotation list has bounded scroll behavior, compact rows, 2-line selected-text preview, 1-line comment preview, swatch/type label styling, and expansion-detail styling.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2: Add DOM regression checks and run plugin tests</name>
  <files>
    paperforge/plugin/tests/annotation-section-dom.test.mjs
  </files>
  <behavior>
    - Test 1: A long ready-state annotation list renders a bounded list container and compact row elements with stable class hooks per D-04 and D-05.
    - Test 2: Row DOM contains page, color swatch, type label, selected-text preview, and comment preview/icon per D-08 and D-10.
    - Test 3: Provenance/read-only/source/attachment/timestamps are absent from default row text and appear only in expansion details per D-09.
    - Test 4: Preview elements expose CSS classes used for 2-line selected text and 1-line comment clamping per D-06.
    - Test 5: The DOM contains no jump/open-at-page, overlay, edit/delete, write-back, DB mutation, or concept evidence controls per D-24 and D-25.
  </behavior>
  <action>
    Create `paperforge/plugin/tests/annotation-section-dom.test.mjs` or, if the runtime test structure makes a separate file redundant, keep the new assertions in this file and import the same runtime test hook from `main.js`. Use jsdom and the real annotation section renderer from `PaperForgeStatusView`.

    The test should focus on DOM contract and regression safety rather than duplicating Plan 02 helper tests. It should verify class hooks, row content placement, expansion detail boundaries, and the absence of later-phase affordances. Do not modify `package.json`, do not add npm packages, and do not loosen existing tests.
  </action>
  <verify>
    <automated>node --check paperforge/plugin/main.js</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-list-viewmodel.test.mjs</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-main-runtime.test.mjs</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-section-dom.test.mjs</automated>
    <automated>npm.cmd --prefix paperforge/plugin test</automated>
  </verify>
  <done>DOM regression tests pass, the full plugin Vitest suite passes, and any failure is fixed rather than papered over. If a dependency is missing, stop and report the exact missing dependency prerequisite instead of adding packages.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Runtime DOM -> CSS layout | Class hooks from `main.js` are styled into a bounded list. |
| Imported text -> visible row layout | Potentially long annotation content is constrained to readable previews. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-annotation-06-10 | Denial of Service | long annotation list layout | mitigate | CSS bounds list height with internal scrolling and regression tests check the bounded container. |
| T-annotation-06-11 | Information Disclosure | provenance fields | mitigate | Default row hides provenance/debug details; expansion-only DOM regression checks enforce this. |
| T-annotation-06-12 | Tampering | later-phase controls | mitigate | DOM tests assert absence of jump, overlay, edit/delete, write-back, DB mutation, and evidence affordances. |
| T-annotation-06-SC | Tampering | npm installs | accept | This plan uses existing `vitest` and `jsdom` dependencies already declared in `package.json`. |
</threat_model>

<verification>
- `node --check paperforge/plugin/main.js`
- `npm.cmd --prefix paperforge/plugin test -- tests/annotation-list-viewmodel.test.mjs`
- `npm.cmd --prefix paperforge/plugin test -- tests/annotation-main-runtime.test.mjs`
- `npm.cmd --prefix paperforge/plugin test -- tests/annotation-section-dom.test.mjs`
- `npm.cmd --prefix paperforge/plugin test`
</verification>

<success_criteria>
- [ ] Long annotation lists are bounded and internally scrollable.
- [ ] Rows use compact row-list styling, not large cards.
- [ ] Selected-text preview is visually clamped to 2 lines and comment preview to 1 line.
- [ ] Inline expansion reveals provenance details without cluttering default rows.
- [ ] Color/type is visible as a swatch plus type label.
- [ ] DOM regression tests prove no Phase 7/8/future controls were added.
- [ ] Full plugin Vitest regression runs through `npm.cmd` using existing dependencies.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-04-SUMMARY.md`.
</output>
