---
phase: ANN14
plan: ANN14-04
type: execute
status: planned
wave: 4
depends_on:
  - ANN14-01
  - ANN14-02
  - ANN14-03
files_modified:
  - paperforge/plugin/styles.css
  - paperforge/plugin/tests/canvas-connectors.test.mjs
  - paperforge/plugin/tests/canvas-render.test.mjs
  - paperforge/plugin/tests/canvas-card-dom.test.mjs
  - paperforge/plugin/tests/canvas-main-runtime.test.mjs
  - paperforge/plugin/tests/annotation-main-runtime.test.mjs
  - paperforge/plugin/tests/annotation-section-dom.test.mjs
requirements:
  - CANVAS-05
  - CONN-01
  - CONN-02
  - CONN-03
requirements_addressed:
  - CANVAS-05
  - CONN-01
  - CONN-02
  - CONN-03
user_setup: []
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
must_haves:
  truths:
    - "D-14/D-15/D-16: Connectors hide on narrow/clipped/unreadable presentation states while ANN13 selected/focus/card/source states remain visible."
    - "D-01/D-02/D-03/D-10/D-11/D-12/D-13: Forbidden-scope tests allow only the focused exact connector layer and still forbid always-on webs, page-level/unresolved lines, arrows, dots, animations, and color palettes."
    - "D-18/D-19/D-20: Read-only boundaries, ANN12 anchor precision rules, ANN13 navigation/fallback semantics, and ANN15 native-PDF reliability boundaries remain unchanged."
    - "CANVAS-05: Existing v0.2 annotation list, PDF page jump, overlay, and fallback paths remain available when the canvas cannot provide supported connector geometry."
  artifacts:
    - path: "paperforge/plugin/tests/canvas-main-runtime.test.mjs"
      provides: "Connector lifecycle and fallback-preservation regression coverage"
    - path: "paperforge/plugin/tests/canvas-card-dom.test.mjs"
      provides: "Responsive CSS and forbidden-scope connector scan coverage"
    - path: "paperforge/plugin/tests/annotation-main-runtime.test.mjs"
      provides: "v0.2 annotation runtime fallback preservation coverage"
  key_links:
    - from: "paperforge/plugin/styles.css"
      to: "paperforge/plugin/tests/canvas-card-dom.test.mjs"
      via: "CSS selectors prove connectors hide responsively without hiding selected/focus card states"
      pattern: "paperforge-canvas-connector-layer"
    - from: "paperforge/plugin/main.js"
      to: "paperforge/plugin/tests/annotation-main-runtime.test.mjs"
      via: "Reading Canvas connector work does not change v0.2 annotation list/page jump/overlay fallback paths"
      pattern: "openLinkText|annotation overlay"
---

# ANN14-04 Plan: Responsive and Forbidden-Scope Hardening

## Objective

Close ANN14 with responsive/readability safeguards and validation-focused tests that prove the focused connector layer remains honest, read-only, transient, and non-regressive for v0.2 fallback behavior.

## Scope

- Responsive connector visibility CSS guardrails.
- Connector helper/render/runtime negative-path tests.
- Forbidden-scope scans that distinguish allowed focused connector SVG from forbidden connector leakage.
- CANVAS-05 preservation tests for v0.2 annotation list, page jump, overlay, and fallback behavior.

## Out of Scope

- No new connector features beyond selected/hovered exact pairs.
- No native Obsidian PDF DOM anchoring, always-on webs, page-level or unresolved connector lines, offscreen hints, cropped/faded continuation lines, mutation controls, write-back, persistence, local editing, AI cards, or ANN15 live harness claims.

## Tasks

### Task 1: Harden Responsive Connector Visibility

**Files:** `styles.css`, `tests/canvas-connectors.test.mjs`, `tests/canvas-card-dom.test.mjs`, `tests/canvas-main-runtime.test.mjs`

**Action:** Add or verify responsive guardrails so connectors hide on narrow Reading Canvas layouts and remain non-interactive with `pointer-events: none`. Tests must cover the helper-level narrow/clipped geometry hidden states, CSS-level narrow layout hiding for `.paperforge-canvas-connector-layer`, and runtime behavior where hidden connectors do not remove card `aria-selected`, anchor focus styling, or fallback buttons per D-14/D-15/D-16.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-connectors.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs
Pop-Location
```

**Done:** Narrow/clipped/unreadable states hide connectors; selected cards, source anchors, and fallback affordances remain visible and testable.

### Task 2: Strengthen Forbidden-Scope Connector Scans

**Files:** `tests/canvas-render.test.mjs`, `tests/canvas-card-dom.test.mjs`, `tests/canvas-main-runtime.test.mjs`

**Action:** Replace broad pre-ANN14 connector bans with targeted, scoped scans. Allow only `.paperforge-canvas-connector-layer` and `.paperforge-canvas-connector` under `.paperforge-reading-canvas-view` for visible exact connector states, while still forbidding page-level/unresolved connector paths, always-on multi-line webs, native PDF viewer selectors inside ANN14 connector/runtime update code, arrow markers, endpoint dots, animation CSS, annotation-color-following connector styles, draggable/persistent layout controls, and mutation/write-back terms in ANN14-owned connector files/tests per D-01/D-02/D-03/D-10/D-11/D-12/D-13/D-18/D-20. Do not scan all legacy v0.2 plugin files as if every pre-existing `pdf-viewer`, `pdf-embed`, `data-page-number`, `localStorage`, `annotations.db`, or `saveData` occurrence were an ANN14 failure; those are allowed where they belong to existing annotation list, PDF page jump, overlay, persistence, and fallback paths preserved by CANVAS-05.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-render.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs
rg -n "marker-end|arrowhead|endpoint-dot|connector-color|connector-palette|transition:.*connector|animation:.*connector|always-on connector|page-level connector|unresolved connector|offscreen hint|edge badge|contenteditable|write-back|apply annotation|edit annotation|delete annotation" src/canvas/connectors.js src/canvas/render.js tests/canvas-connectors.test.mjs tests/canvas-render.test.mjs tests/canvas-card-dom.test.mjs tests/canvas-main-runtime.test.mjs styles.css
rg -n "pdf-viewer|pdf-embed|data-page-number|localStorage|annotations.db|saveData" src/canvas/connectors.js src/canvas/render.js tests/canvas-connectors.test.mjs tests/canvas-render.test.mjs tests/canvas-card-dom.test.mjs
Pop-Location
```

**Done:** Automated tests and scoped scan output prove ANN14 added only the focused connector layer and no forbidden connector polish, native PDF coupling in connector-owned code, new connector persistence, or mutation/write-back controls. Pre-existing v0.2 fallback/overlay/storage occurrences outside ANN14 connector scope are preserved, not removed.

### Task 3: Preserve CANVAS-05 Fallback Paths

**Files:** `tests/canvas-main-runtime.test.mjs`, `tests/annotation-main-runtime.test.mjs`, `tests/annotation-section-dom.test.mjs`

**Action:** Add focused regressions proving unsupported/unmeasured canvas connector states do not remove or loosen existing v0.2 annotation list, PDF page jump, overlay, and explicit fallback behavior. Keep fallback opening tied to the existing explicit button path and existing `openLinkText` safety checks; connector hidden states must never auto-open PDF and must not change ANN13 fallback eligibility per CANVAS-05/D-16/D-18/D-19.

**Verify:**

```powershell
Push-Location paperforge/plugin
node --check main.js
node --check src/canvas/connectors.js
node --check src/canvas/render.js
npm.cmd test -- canvas-connectors.test.mjs canvas-render.test.mjs canvas-card-dom.test.mjs canvas-main-runtime.test.mjs annotation-navigation.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs
Pop-Location
```

**Done:** Tests prove v0.2 annotation list/page jump/overlay/fallback paths remain available; connector hidden states never trigger PDF opening; read-only and fallback boundaries remain unchanged.

## Acceptance Criteria

- CANVAS-05 is explicitly regression-tested alongside CONN-01, CONN-02, and CONN-03.
- D-01 through D-20 are covered by final hardening tests.
- The focused connector layer is allowed only where ANN14 intends it and forbidden everywhere else.
