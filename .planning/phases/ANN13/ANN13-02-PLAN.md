---
phase: ANN13
plan: ANN13-02
type: execute
status: planned
wave: 2
depends_on:
  - ANN13-01
files_modified:
  - paperforge/plugin/src/canvas/navigation.js
  - paperforge/plugin/src/canvas/view-model.js
  - paperforge/plugin/src/canvas/index.js
  - paperforge/plugin/tests/canvas-navigation.test.mjs
  - paperforge/plugin/tests/canvas-viewmodel.test.mjs
  - paperforge/plugin/tests/annotation-navigation.test.mjs
requirements:
  - NAV-03
requirements_addressed:
  - NAV-03
user_setup: []
autonomous: true
decision_coverage:
  - D-15
  - D-16
  - D-18
  - D-19
  - D-25
  - D-26
  - D-27
must_haves:
  truths:
    - "D-15/D-16/D-18/D-19: PDF fallback eligibility is explicit, page-specific, fail-closed, and reuses v0.2 attachment/page safety semantics without creating a new PDF navigation contract."
    - "D-25/D-26/D-27: Fallback metadata remains read-only, introduces no connector layer, and does not depend on native Obsidian PDF viewer DOM internals."
  artifacts:
    - path: "paperforge/plugin/src/canvas/navigation.js"
      provides: "Pure fallback eligibility helper compatible with v0.2 target resolution"
    - path: "paperforge/plugin/src/canvas/view-model.js"
      provides: "Read-only card metadata needed for fallback eligibility"
    - path: "paperforge/plugin/tests/canvas-navigation.test.mjs"
      provides: "Fallback eligibility tests for safe, missing-page, mismatch, and paper mismatch cases"
  key_links:
    - from: "paperforge/plugin/src/testable.js"
      to: "paperforge/plugin/src/canvas/navigation.js"
      via: "v0.2 PDF target semantics inform fallback eligibility"
      pattern: "resolveAnnotationPdfTarget-compatible target shape"
---

# ANN13-02 Plan: Fallback Eligibility and Card Metadata

## Objective

Make safe PDF fallback eligibility available to the canvas without opening PDFs, while preserving enough read-only card metadata for runtime fallback buttons.

## Scope

- Extend `navigation.js` with pure fallback eligibility helpers.
- Extend `view-model.js` only for read-only row/fallback metadata required by ANN13.
- Export helper surface from `index.js`.
- Add/extend focused tests.

## Out of Scope

- No fallback button rendering, no `openLinkText`, no DOM focus/scroll, no source matching changes.
- No mutation controls, connector classes, native PDF viewer DOM dependency, fuzzy fallback, or plain-PDF degraded fallback.

## Tasks

### Task 1: Preserve Read-Only Fallback Metadata

**Files:** `src/canvas/view-model.js`, `tests/canvas-viewmodel.test.mjs`

**Action:** Preserve the minimal row/entry-facing fields needed to evaluate v0.2 PDF fallback: card ID, paper identity, `pdfLocation.pageIndex`, `sourceAttachmentKey`, and source annotation identity.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-viewmodel.test.mjs
Pop-Location
```

**Done:** Card metadata supports fallback eligibility but exposes no edit/import/apply/write-back actions.

### Task 2: Add Pure Fallback Eligibility Helper

**Files:** `src/canvas/navigation.js`, `tests/canvas-navigation.test.mjs`

**Action:** Implement fallback eligibility over card metadata plus v0.2-compatible resolved target input, requiring valid page target and matching identity.

**Verify:**

```powershell
Push-Location paperforge/plugin
npm.cmd test -- canvas-navigation.test.mjs annotation-navigation.test.mjs
Pop-Location
```

**Done:** Safe target is eligible; missing pageIndex, missing PDF path, attachment mismatch, and paper mismatch are ineligible.

### Task 3: Export Fallback Contracts

**Files:** `src/canvas/index.js`, `tests/canvas-navigation.test.mjs`

**Action:** Export only the narrow helper names needed by render/runtime.

**Verify:**

```powershell
Push-Location paperforge/plugin
node --check src/canvas/index.js
npm.cmd test -- canvas-navigation.test.mjs
Pop-Location
```

**Done:** Runtime can import fallback eligibility without importing Obsidian or v0.2 UI code.

## Acceptance Criteria

- NAV-03 has a pure fail-closed eligibility contract.
- Fallback requires an explicit future button click and a valid page target.
- No new PDF resolver or automatic PDF jump is introduced.
