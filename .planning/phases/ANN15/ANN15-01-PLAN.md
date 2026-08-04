---
phase: ANN15
plan: ANN15-01
type: execute
status: planned
wave: 1
depends_on: []
files_modified:
  - .planning/phases/ANN15/ANN15-AUTOMATED-GATE.md
  - .planning/phases/ANN15/ANN15-FOCUSED-FAILURES.md
requirements:
  - TEST-01
  - TEST-02
  - TEST-03
  - TEST-04
requirements_addressed:
  - TEST-01
  - TEST-02
  - TEST-03
  - TEST-04
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
must_haves:
  truths:
    - "D-01/D-03: ANN15 has a hard focused automated gate made from the locked v0.3 canvas and v0.2 fallback preservation command slice."
    - "D-02: Any optional broader-suite failure is recorded in a Baseline bucket with command, summary, and why it is unrelated to ANN15."
    - "D-04: Focused-slice failures remain ANN15 blockers unless proven unrelated baseline behavior and explicitly moved out of the hard gate."
    - "D-05/D-06/D-07/D-08: The minimum syntax, canvas module, v0.3 Vitest, and v0.2 fallback commands are visible and executed from paperforge/plugin."
  artifacts:
    - path: ".planning/phases/ANN15/ANN15-AUTOMATED-GATE.md"
      provides: "Focused command list, run evidence, and baseline bucket policy"
    - path: ".planning/phases/ANN15/ANN15-FOCUSED-FAILURES.md"
      provides: "Blocking focused failure record when the hard gate cannot pass"
  key_links:
    - from: ".planning/phases/ANN15/ANN15-AUTOMATED-GATE.md"
      to: "paperforge/plugin"
      via: "commands executed from plugin working directory"
      pattern: "Push-Location paperforge/plugin"
    - from: ".planning/phases/ANN15/ANN15-AUTOMATED-GATE.md"
      to: ".planning/phases/ANN15/ANN15-VERIFICATION.md"
      via: "automated gate evidence consumed by final report"
      pattern: "Automated gate status"
---

# ANN15-01 Plan: Focused Automated Gate Contract and Evidence

## Objective

Create the canonical ANN15 automated gate evidence file, run only the locked focused command slice as the hard gate, and classify unrelated broader-suite failures as baseline evidence rather than ANN15 blockers.

## Scope

- Create `.planning/phases/ANN15/ANN15-AUTOMATED-GATE.md`.
- Run the explicit minimum focused commands from ANN15-CONTEXT D-05 through D-08.
- Record PASS/FAIL evidence for each focused command.
- Record optional broader checks only in a `Baseline` bucket when their failures are unrelated to ANN15.
- Create `.planning/phases/ANN15/ANN15-FOCUSED-FAILURES.md` only if a focused hard-gate failure remains after analysis.

## Out of Scope

- No new canvas functionality, new UI behavior, new PDF renderer, native PDF DOM anchoring, local annotation editing, Zotero write-back, persistent layout, AI cards, or multi-paper boards.
- Do not claim jsdom or Vitest results prove live Obsidian behavior.
- Do not make broad plugin or full-repo failures part of ANN15's hard gate unless the failure is in the focused ANN15 slice.

## Tasks

### Task 1: Write the Focused Gate Contract

**Files:** `.planning/phases/ANN15/ANN15-AUTOMATED-GATE.md`

**Action:** Create the gate evidence document with sections for `Hard Gate Commands`, `Run Evidence`, `Focused Failures`, and `Baseline Bucket`. The hard gate must cite D-01 through D-08 and must say `.planning/phases/ANN15/` is canonical. Include the exact command list below as the minimum locked slice; additional commands may be appended only after this list and may not replace it.

**Verify:**

```powershell
Select-String -Path .planning/phases/ANN15/ANN15-AUTOMATED-GATE.md -Pattern "node --check main.js","canvas-context.test.mjs","annotation-overlay.test.mjs","Baseline Bucket"
```

**Done:** `ANN15-AUTOMATED-GATE.md` exists, cites D-01 through D-08, and visibly contains this minimum command block:

```powershell
Push-Location paperforge/plugin
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
Pop-Location
```

### Task 2: Run and Record the Hard Gate

**Files:** `.planning/phases/ANN15/ANN15-AUTOMATED-GATE.md`, `.planning/phases/ANN15/ANN15-FOCUSED-FAILURES.md`

**Action:** Execute the minimum focused commands from Task 1 from `paperforge/plugin` and record command, result, summary, and evidence timestamp in `ANN15-AUTOMATED-GATE.md` per D-01/D-03/D-05/D-06/D-07/D-08. If a command fails, classify it before continuing: focused canvas or v0.2 fallback preservation failures are ANN15 blockers per D-04; unrelated environment or non-focused baseline failures must be explicitly justified before being moved out of the hard gate. If a focused blocker remains, create `ANN15-FOCUSED-FAILURES.md` with failing command, relevant file/test, observed output summary, required owner surface, and next remediation step; do not mark ANN15 complete while that file contains unresolved blockers.

**Verify:**

```powershell
Push-Location paperforge/plugin
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
Pop-Location
```

**Done:** Every focused command is recorded as `PASS`, or remaining focused blockers are recorded in `ANN15-FOCUSED-FAILURES.md` and ANN15 is left incomplete.

### Task 3: Record Optional Baseline Evidence Without Expanding the Hard Gate

**Files:** `.planning/phases/ANN15/ANN15-AUTOMATED-GATE.md`

**Action:** If broader plugin or repo checks are run, record them only under `Baseline Bucket` with command, failure summary, and rationale per D-02. Do not convert broad-suite failures into ANN15 blockers unless the failing assertion directly overlaps the locked focused command slice. The baseline vocabulary must distinguish `PASS`, `FAIL`, and `BASELINE`; `BASELINE` means known or discovered non-ANN15 behavior, not a hidden pass.

**Verify:**

```powershell
Select-String -Path .planning/phases/ANN15/ANN15-AUTOMATED-GATE.md -Pattern "Baseline Bucket","BASELINE","Hard Gate Commands"
```

**Done:** `ANN15-AUTOMATED-GATE.md` separates hard-gate focused evidence from optional broader-suite baseline evidence, and no unrelated baseline failure blocks ANN15.

## Acceptance Criteria

- TEST-01 through TEST-04 have focused automated evidence or explicit focused blockers.
- D-01 through D-08 are implemented exactly.
- The final report can consume `ANN15-AUTOMATED-GATE.md` without guessing which commands were hard blockers.
