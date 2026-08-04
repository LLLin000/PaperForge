---
phase: ANN15
plan: ANN15-03
type: execute
status: planned
wave: 1
depends_on: []
files_modified:
  - .planning/phases/ANN15/LIVE-HARNESS.md
requirements:
  - SAFE-04
  - TEST-05
requirements_addressed:
  - SAFE-04
  - TEST-05
user_setup: []
autonomous: true
decision_coverage:
  - D-09
  - D-10
  - D-11
  - D-12
  - D-13
  - D-14
  - D-15
must_haves:
  truths:
    - "D-09/D-10: LIVE-HARNESS.md exists with environment, sample paper, operation steps, observations, per-step status, conclusion, and limitations."
    - "D-11: The checklist follows the Canvas-first workflow: open active-paper canvas, central surface, side lanes, focus, connectors, fallback, refresh, and teardown."
    - "D-12/D-14: Native PDF overlay confidence and automated/jsdom confidence remain separately labeled."
    - "D-13/D-15: If live Obsidian cannot be executed, the file records PENDING - not executed in this environment using PASS/FAIL/PENDING/NOT APPLICABLE step statuses."
  artifacts:
    - path: ".planning/phases/ANN15/LIVE-HARNESS.md"
      provides: "Manual Obsidian checklist and evidence note for live canvas confidence"
  key_links:
    - from: ".planning/phases/ANN15/LIVE-HARNESS.md"
      to: ".planning/phases/ANN15/ANN15-VERIFICATION.md"
      via: "TEST-05 and SAFE-04 live confidence evidence"
      pattern: "Overall status"
---

# ANN15-03 Plan: Live Obsidian Harness Record

## Objective

Create the canonical ANN15 live harness record for the PaperForge Reading Canvas, using honest status labels that separate live Obsidian behavior from automated jsdom/Vitest confidence and from the older v0.2 native PDF overlay harness.

## Scope

- Create `.planning/phases/ANN15/LIVE-HARNESS.md`.
- Record environment, sample paper, steps, observations, per-step status, final conclusion, and limitations.
- Use `PASS`, `FAIL`, `PENDING`, and `NOT APPLICABLE` statuses.
- Mark the live run `PENDING - not executed in this environment` if the current executor cannot open Obsidian.

## Out of Scope

- Screenshots and video are optional, not required.
- Do not describe automated jsdom/Vitest passing as live Obsidian proof.
- Do not merge v0.3 PaperForge Canvas confidence with v0.2 native PDF overlay confidence.
- Do not add or change canvas functionality while creating the harness record.

## Tasks

### Task 1: Create the Live Harness Template and Pending Policy

**Files:** `.planning/phases/ANN15/LIVE-HARNESS.md`

**Action:** Create `LIVE-HARNESS.md` with sections for `Environment`, `Sample paper`, `Execution status`, `Canvas-first checklist`, `Observations`, `Native/live split`, `Limitations`, and `Final conclusion` per D-09/D-10/D-13/D-15. Include the status vocabulary `PASS`, `FAIL`, `PENDING`, and `NOT APPLICABLE`. If Obsidian is unavailable, set `Overall status: PENDING - not executed in this environment` and explain that this is honest pending evidence, not a failure and not a pass.

**Verify:**

```powershell
Select-String -Path .planning/phases/ANN15/LIVE-HARNESS.md -Pattern "Overall status","PENDING - not executed in this environment","PASS","FAIL","NOT APPLICABLE"
```

**Done:** The file exists and is audit-ready even before a live Obsidian run is possible.

### Task 2: Add the Canvas-First Manual Checklist

**Files:** `.planning/phases/ANN15/LIVE-HARNESS.md`

**Action:** Add the required Canvas-first checklist per D-11. Steps must cover: open a recognized active paper, open PaperForge Reading Canvas, verify central reading surface, verify left/right card lanes, select card to focus source, select source to focus card, verify focused connector behavior, verify explicit fallback button/path, refresh/stale handling, and teardown or paper-change cleanup. Each row must include step, expected observation, actual observation, status, and evidence note. Leave actual observation as `PENDING - not executed in this environment` when no live run occurred.

**Verify:**

```powershell
Select-String -Path .planning/phases/ANN15/LIVE-HARNESS.md -Pattern "Open PaperForge Reading Canvas","central reading surface","side card lanes","focused connector","fallback","teardown"
```

**Done:** A future human or agent with GUI access can execute the checklist without reconstructing ANN15 context.

### Task 3: Record Live/Native Split and Limitations

**Files:** `.planning/phases/ANN15/LIVE-HARNESS.md`

**Action:** Add a `Native/live split` section per D-12/D-14. It must state that automated tests and jsdom results do not prove live Obsidian behavior, and that v0.3 PaperForge Reading Canvas confidence does not prove the v0.2 native PDF overlay harness. If native overlay is untested, mark it `PENDING` rather than `PASS`. The final conclusion must avoid words like done, verified, or passed for pending live items.

**Verify:**

```powershell
Select-String -Path .planning/phases/ANN15/LIVE-HARNESS.md -Pattern "jsdom","does not prove live Obsidian","native PDF overlay","PENDING"
```

**Done:** SAFE-04 and TEST-05 can be evaluated without overstating live or native PDF confidence.

## Acceptance Criteria

- `LIVE-HARNESS.md` exists under `.planning/phases/ANN15/`.
- D-09 through D-15 are implemented exactly.
- Pending live behavior is recorded honestly and remains separate from automated confidence.
