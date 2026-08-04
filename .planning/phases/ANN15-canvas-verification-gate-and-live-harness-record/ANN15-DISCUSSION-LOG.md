# Phase ANN15: Canvas Verification Gate and Live Harness Record - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-07-07
**Phase:** ANN15-Canvas Verification Gate and Live Harness Record
**Areas discussed:** Automated gate boundary, Live Obsidian harness record, Safety audit scan scope, Final confidence report wording

---

## Automated Gate Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Focused slice | v0.3 canvas tests plus v0.2 annotation fallback preservation are the hard gate. | Yes |
| Broader plugin | Larger plugin suite runs as gate with baseline classification. | |
| Full repo | Python plus plugin full suite runs as gate. | |

**User's choice:** Focused slice.
**Notes:** Broader/full suites may be informational only. Unrelated failures must not block ANN15.

| Option | Description | Selected |
|--------|-------------|----------|
| Baseline bucket | Record command, failure summary, and why non-ANN15 failures are unrelated. | Yes |
| Must fix all | Fix every failure encountered. | |
| Skip broader suite | Do not run broader suites. | |

**User's choice:** Baseline bucket.
**Notes:** Baseline records are visible but non-blocking.

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit command list | Lock a minimum focused command list in CONTEXT. | Yes |
| Requirement-derived | Let planner infer commands from requirements. | |
| Current ANN14 list | Use ANN14 validation list directly. | |

**User's choice:** Explicit command list.
**Notes:** Planner may add commands but cannot replace the minimum list.

| Option | Description | Selected |
|--------|-------------|----------|
| Block and fix | Focused slice failures block ANN15 and must be fixed. | Yes |
| Record only | Record failures without fixing. | |
| Case by case | Ask the user for each failure. | |

**User's choice:** Block and fix.
**Notes:** Only proven unrelated baseline failures may be moved out of the hard gate.

---

## Live Obsidian Harness Record

| Option | Description | Selected |
|--------|-------------|----------|
| Manual checklist + evidence note | Write LIVE-HARNESS.md with environment, sample paper, steps, observations, status, and limitations. | Yes |
| Screenshot/video required | Require visual media as evidence. | |
| Automated harness only | Use automation only. | |

**User's choice:** Manual checklist + evidence note.
**Notes:** Screenshots/video are optional, not required.

| Option | Description | Selected |
|--------|-------------|----------|
| Canvas-first workflow | Verify active paper canvas, source surface, lanes, focus, connectors, fallback, refresh, teardown. | Yes |
| Canvas + native overlay split | Also walk native PDF overlay in live harness. | |
| Minimal smoke only | Confirm only that the view opens and content appears. | |

**User's choice:** Canvas-first workflow.
**Notes:** Native PDF overlay confidence remains separately labeled and is not merged into canvas confidence.

| Option | Description | Selected |
|--------|-------------|----------|
| Record pending explicitly | Create LIVE-HARNESS.md and mark live status pending if Obsidian cannot be opened. | Yes |
| Block ANN15 | Require live Obsidian access before completing ANN15. | |
| Replace with jsdom | Treat automation as the live substitute. | |

**User's choice:** Record pending explicitly.
**Notes:** jsdom must not be described as live confidence.

| Option | Description | Selected |
|--------|-------------|----------|
| Per-step status table | Use PASS / FAIL / PENDING / NOT APPLICABLE for each live step. | Yes |
| Single overall status | One status for the entire harness. | |
| Narrative only | Text observations without status table. | |

**User's choice:** Per-step status table.
**Notes:** Include final overall conclusion.

---

## Safety Audit Scan Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Scoped + allowlist | Scan canvas-owned files/tests/CSS and allowlist legacy v0.2 fallback/storage/native overlay code. | Yes |
| Diff-based only | Scan only current changes. | |
| Whole repo strict | Treat all repository hits as potential blockers. | |

**User's choice:** Scoped + allowlist.
**Notes:** Avoid repeating the ANN14 false-positive broad-scan issue.

| Option | Description | Selected |
|--------|-------------|----------|
| Read-only + persistence + native DOM | Prove no edit/write controls, no canvas-owned persistence/write side effects, no native PDF DOM dependency. | Yes |
| Read-only only | Scan only edit/write controls. | |
| Everything forbidden | Scan all deferred features as forbidden. | |

**User's choice:** Read-only + persistence + native DOM.
**Notes:** This matches SAFE-01 through SAFE-04.

| Option | Description | Selected |
|--------|-------------|----------|
| Allowed legacy table | Report allowed legacy hits with file, pattern, and reason. | Yes |
| Ignore silently | Hide allowlisted hits. | |
| Warn everything | Show every allowlisted hit as warning. | |

**User's choice:** Allowed legacy table.
**Notes:** Traceability without false blockers.

| Option | Description | Selected |
|--------|-------------|----------|
| Canvas-owned strict | Canvas-owned violations block; allowlisted legacy hits do not. | Yes |
| Everything strict | Any hit blocks. | |
| Report only | No safety hit blocks. | |

**User's choice:** Canvas-owned strict.
**Notes:** This preserves CANVAS-05 while keeping ANN15 safety meaningful.

---

## Final Confidence Report Wording

| Option | Description | Selected |
|--------|-------------|----------|
| Requirement matrix + risk narrative | Status SAFE/TEST requirements, then explain confidence, pending, baseline, and unproven claims. | Yes |
| User workflow first | Organize by product workflow. | |
| Test log first | Organize by command output. | |

**User's choice:** Requirement matrix + risk narrative.
**Notes:** This preserves traceability while staying readable.

| Option | Description | Selected |
|--------|-------------|----------|
| PASS / FAIL / PENDING / BASELINE | Precise verification vocabulary. | Yes |
| PASS / FAIL only | Binary status. | |
| Green / Yellow / Red | Product-style colors. | |

**User's choice:** PASS / FAIL / PENDING / BASELINE.
**Notes:** Defines scope, blockers, pending live/environment gaps, and non-ANN15 baseline failures.

| Option | Description | Selected |
|--------|-------------|----------|
| Live/native split | Explicitly state automation does not prove live Obsidian and canvas does not prove native PDF overlay. | Yes |
| Only native overlay | Only caveat native PDF overlay. | |
| No special caveats | Just report outcomes. | |

**User's choice:** Live/native split.
**Notes:** Pending items must not be described as done or verified.

| Option | Description | Selected |
|--------|-------------|----------|
| Conditional complete | v0.3 can complete if focused gate passes and LIVE-HARNESS.md exists, with caveat when live is pending. | Yes |
| Only if live PASS | Require live harness pass before milestone completion. | |
| Automated only complete | Complete from automation alone. | |

**User's choice:** Conditional complete.
**Notes:** Completion text must carry a pending caveat if live harness is pending.

## the agent's Discretion

- Choose final report filename and exact table columns.
- Add optional broader plugin/full-repo informational commands.
- Choose helper script names or manual verification templates.
- Expand the focused command list, but do not replace the locked minimum.

## Deferred Ideas

None.
