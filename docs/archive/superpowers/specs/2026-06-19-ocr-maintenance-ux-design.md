# OCR Maintenance UX Design

> Date: 2026-06-19
> Status: draft written from approved chat direction, pending user review
> Scope: redesign the plugin Settings -> Maintenance tab so ordinary research users can quickly judge whether anything needs action, understand why, and avoid being pushed toward maintenance actions that are unlikely to help.

## Goal

Turn the current OCR maintenance tab from an engineer-facing repair console into a user-facing maintenance decision surface.

The new tab should answer three user questions in order:

1. Do I need to do anything?
2. If yes, which papers are worth acting on?
3. Why is the system recommending action for those papers?

The design priority is:

1. one-glance overall judgment,
2. then explanation,
3. then optional deep technical detail.

## Target User

Primary target user: ordinary research users, not the developer maintaining the OCR pipeline.

This means the default screen should not assume the user understands:

- `green / yellow / red`,
- `done_degraded`,
- `derived_stale`,
- structural gate terminology,
- layout audit terminology,
- rebuild vs redo implementation details.

The interface should translate internal OCR state into user decision language.

## Core Product Principle

The maintenance tab should default to surfacing only problems where user action is likely to help.

In other words:

- actionable problems should be promoted,
- non-actionable quality caveats should be explained but not escalated,
- users should not be pressured to perform maintenance just because a paper fails a strict health heuristic.

Operational shorthand:

> Only interrupt the user for problems that are likely to improve after action.

## Current Problem

The current maintenance tab in `paperforge/plugin/src/settings.ts` is already functionally capable, but its UX is oriented around raw OCR maintenance rows and internal state fields.

Current issues:

1. The tab leads with a full table rather than a conclusion.
2. The user must infer whether a paper needs action from low-level fields.
3. `health`-adjacent badges are visually prominent, but they do not distinguish between:
   - rebuild-fixable issues,
   - true OCR failures,
   - structurally noisy papers where maintenance may not help.
4. The UI encourages users to interpret any warning-like state as a repair task.
5. The existing “recommended action” signal exists in backend data, but it is not the primary organizing principle of the interface.

## Important Domain Truth

`health` is not the same thing as user-facing normality.

Current OCR health logic in `paperforge/worker/ocr_health.py` mixes:

- structural completeness heuristics,
- risk signals for weak layout confidence,
- figure/table confidence issues,
- role gate degradation,
- layout-class sensitivity.

This is useful engineering evidence, but it is not a reliable direct UI verdict for ordinary users.

Some papers will naturally score worse on health-style heuristics because of complex layout or genre, even when maintenance actions are unlikely to improve the result.

Therefore:

- `green` must not be treated as the only “normal” outcome,
- `yellow` must not automatically imply “user should do something”,
- `red` must be interpreted alongside actionability, not in isolation.

## UX Decision Model

The maintenance tab should classify each paper by actionability first, not by raw health color.

### User-Facing Categories

Each paper should land in one of four user-facing categories:

1. `No Action Needed`
2. `Rebuild Recommended`
3. `OCR Failed`
4. `Result Limited`

### Category Definitions

#### 1. No Action Needed

Use when:

- OCR completed,
- there is no clear recommended action,
- and the system does not have strong evidence that user maintenance will help.

This category may include papers that are not perfectly “green” internally, as long as the system does not have a concrete, useful intervention to propose.

#### 2. Rebuild Recommended

Use when:

- backend `recommended_action == "rebuild"`.

This is the highest-priority actionable category for ordinary users because rebuild is lower-cost and more deterministic than rerunning OCR.

The UI should treat rebuild as the main proactive action type.

#### 3. OCR Failed

Use when:

- OCR clearly failed,
- and retrying OCR is the only meaningful next step.

Redo should only be proactively suggested in true failure scenarios.

This reflects the approved UX rule:

> redo is not proactively promoted unless OCR clearly failed.

#### 4. Result Limited

Use when:

- the paper shows warning/degraded signals,
- but the system has no concrete reason to believe rebuild or redo will help.

This category exists to explain limitations without turning them into false maintenance tasks.

Examples:

- complex layout,
- weak confidence signals,
- strict health heuristics failing on papers that are still usable,
- degraded reasons that do not map to a high-confidence maintenance action.

## Mapping from Existing Backend Signals

The existing backend already exposes the most important actionability field via `recommended_action` in `paperforge/worker/ocr_maintenance.py`.

The redesigned UI should map fields as follows:

### Primary decision fields

- `recommended_action`
- `ocr_status`

### Secondary evidence fields

- `health`
- `degraded_reasons`
- `error_summary`
- `error_stage`
- `version`
- `finished_at`
- `model`

### Required mapping behavior

1. `recommended_action == "rebuild"` -> `Rebuild Recommended`
2. explicit OCR failure with redo-worthy state -> `OCR Failed`
3. warning/degraded signals without recommended action -> `Result Limited`
4. completed items without actionable recommendation -> `No Action Needed`

### Explicit non-goal

The UI should not use `green / yellow / red` as the primary category system.

Those may remain visible only inside expanded technical evidence.

## Information Architecture

The tab should be reordered into four vertical sections.

### Section 1: Overall Conclusion Card

This is the first screenful priority.

Contents:

- one sentence overall conclusion,
- three primary counts,
- one short explanation note.

#### Example conclusion copy

- `OCR is mostly in good shape. 2 papers are recommended for rebuild.`
- `OCR has 1 failed paper that needs attention.`
- `OCR looks usable overall. Some papers have limitations, but no maintenance is currently recommended.`

#### Primary counts

- `No Action Needed`
- `Rebuild Recommended`
- `OCR Failed`

`Result Limited` should be shown as secondary supporting information, not as a primary alert metric.

#### Required helper note

Add a short note under the summary:

> This page only promotes issues where maintenance is likely to help. Some papers may have limitations that are not meaningfully improved by rerunning maintenance.

### Section 2: Needs Attention

This section shows only actionable papers:

- `Rebuild Recommended`
- `OCR Failed`

This is the main operational list for ordinary users.

Do not show all papers here.

Each row/card should answer:

1. What is the problem?
2. What should I do?
3. Why is that action recommended?

#### Required fields per row/card

- paper title,
- user-facing category,
- one-line explanation,
- primary action button,
- `View why` / `View details` disclosure.

#### Example explanation copy

- `Derived OCR results are stale. Rebuild should regenerate them from existing OCR data.`
- `OCR failed before completion. Rerunning OCR is the only useful next step.`

### Section 3: Result Limitations

This section lists papers in `Result Limited`.

Purpose:

- explain caveats,
- avoid false repair pressure,
- build trust that the system can say “this is imperfect, but maintenance may not help.”

Required section intro:

> These papers show weaker confidence or more complex structure, but PaperForge does not currently have a high-confidence maintenance action to recommend.

Each entry can be lighter-weight than the actionable list, but should still provide:

- paper title,
- concise limitation summary,
- `View why` disclosure.

No primary maintenance button should appear by default in this section.

### Section 4: All Papers

The current table-like detailed view should remain available, but be moved into a collapsed advanced section.

Purpose:

- preserve power-user inspection,
- preserve developer debugging value,
- avoid making the whole tab feel like a backend console.

This section should default to collapsed.

## Row/Card Content Rules

The redesigned default paper item should be card-oriented or at least row-oriented around decision clarity rather than dense columns.

Default visible content should be limited to:

1. title,
2. user-facing verdict,
3. concise reason,
4. action button if actionable,
5. disclosure for supporting evidence.

Do not require the user to interpret a wide table to understand next steps.

## Progressive Disclosure

Technical evidence is still valuable, but should be hidden behind an explicit expand action.

### Expanded details should contain

- internal OCR status,
- internal health summary,
- degraded reasons,
- error summary / stage when present,
- model,
- version,
- recent completion time,
- any backend recommendation rationale already available from current data.

### Expanded details should not be primary UI

These are diagnostic materials, not first-pass decision materials.

## Terminology Rules

The interface should shift from system terminology to user decision terminology.

### Terms to avoid in default view

- `green`
- `yellow`
- `red`
- `done_degraded`
- `derived_stale`
- `role gate degraded`
- `weak body spine`
- `layout audit`
- `reader_figure_coverage_gap`

These may appear only inside expanded details.

### Preferred user-facing terms

- `No Action Needed`
- `Rebuild Recommended`
- `OCR Failed`
- `Result Limited`
- `Recommended action`
- `Why this is recommended`

### Specific action labels

- `Rebuild results`
- `Rerun OCR`

These labels are clearer than generic “fix” phrasing and more honest about what the action actually does.

## Required Explanatory Copy

The redesign must explicitly explain the difference between rebuild and rerun OCR.

### Rebuild explanation

Add nearby helper copy:

> Rebuild regenerates derived OCR results from existing OCR raw data. It does not call the OCR service again.

### Rerun OCR explanation

Add nearby helper copy:

> Rerun OCR is only recommended when OCR clearly failed. It costs more and may not produce a better result unless the previous run failed.

### Result Limited explanation

Add helper copy:

> Some papers have unusual layouts or weaker confidence signals. That does not always mean maintenance can improve them.

## Interaction Behavior

### Filters

Default filter should prioritize the actionability sections rather than raw badge filtering.

If a filter control remains, it should expose user-facing categories first:

- All papers
- Needs attention
- Result limited
- No action needed

Avoid exposing raw internal badge strings as top-level filter choices.

### Bulk actions

Bulk actions should operate only on clearly actionable items.

Rules:

1. bulk rebuild should only target `Rebuild Recommended` items,
2. bulk rerun OCR should only appear for failed papers,
3. “select all” should not silently include non-actionable warning-only papers.

## Data/Logic Constraints

This UX redesign does not require inventing a new backend health system.

The design should reuse existing backend fields wherever possible, especially:

- `recommended_action`,
- `status`,
- `degraded_reasons`,
- `error_summary`,
- `error_stage`,
- `version`.

Minimal additional logic is acceptable if needed to map backend rows into the four user-facing categories, but the design should avoid a deep new maintenance state machine.

## Non-Goals

This design does not:

- redefine OCR health computation,
- promise that all papers can become green,
- hide all technical detail from power users,
- remove the existing detailed table entirely,
- change OCR pipeline backend semantics beyond what is necessary to present them clearly.

## Acceptance Criteria

The redesign is successful when:

1. a first-time ordinary user can tell within a few seconds whether maintenance is needed,
2. actionable items are visually separated from non-actionable quality caveats,
3. rebuild-worthy items are promoted more strongly than redo-worthy items,
4. redo is proactively surfaced only for clear failure cases,
5. warning-like health signals without a useful intervention no longer create false repair pressure,
6. full technical details remain available through disclosure for debugging and trust-building.

## Implementation Notes

The current implementation hotspot is `paperforge/plugin/src/settings.ts`, especially `_renderMaintenanceTab()`.

The likely implementation direction is:

1. keep the existing maintenance row backend model,
2. add a small UI-side category mapper based on actionability,
3. replace the current table-first rendering with summary-first rendering,
4. preserve the existing detailed table inside an advanced collapsed section.

This keeps the diff small while aligning the UX with the approved product logic.
