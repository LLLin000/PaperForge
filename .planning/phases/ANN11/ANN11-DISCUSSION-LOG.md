# Phase ANN11: Annotation Card View-Models and Layout - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-07-04
**Phase:** ANN11-Annotation Card View-Models and Layout
**Areas discussed:** Card information density, deterministic side-lane placement, explicit canvas states, long/CJK text behavior, read-only/provenance signaling

---

## Card Information Density

| Option | Description | Selected |
|--------|-------------|----------|
| Compact evidence card | Always show selected text, comment, page, color/type, source/provenance, and read-only status without extra expansion UI. | yes |
| Minimal card | Show only selected text/comment/page and defer provenance to later phases. | |
| Expandable detail card | Add details/drawers/popovers in ANN11. | |

**User's choice:** Approved recommended compact evidence card direction.
**Notes:** The card should move toward the reference UI while staying small enough for side lanes. Expandable details are deferred.

---

## Deterministic Side-Lane Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Reading-order alternation | Sort by stable reading/source order, then alternate left/right lanes. | yes |
| Page clustering | Keep page groups together in one lane or clustered blocks. | |
| Type/color grouping | Group by annotation type or color. | |

**User's choice:** Approved recommended reading-order alternation.
**Notes:** The layout should evoke the reference UI without introducing freeform drag/drop or persistent layout state.

---

## Explicit Canvas States

| Option | Description | Selected |
|--------|-------------|----------|
| Central status plus lane placeholders | Keep central canvas state visible; lanes show cards only when loaded and explicit placeholders/status otherwise. | yes |
| Empty-lane-only states | Represent most states only by empty side lanes. | |
| Reuse v0.2 list states directly | Render list-like state copy inside the canvas. | |

**User's choice:** Approved recommended explicit canvas state model.
**Notes:** Empty, error, missing source, refresh, and stale states must remain distinguishable.

---

## Long Text, CJK, and Layout Resilience

| Option | Description | Selected |
|--------|-------------|----------|
| Bounded previews | Clamp selected text/comment previews with safe wrapping and stable card dimensions. | yes |
| Full text in card | Let card height expand to fit all selected text and comments. | |
| Hide long content | Replace long content with a terse placeholder. | |

**User's choice:** Approved recommended bounded preview behavior.
**Notes:** CJK-heavy content must wrap naturally and must not overlap metadata, badges, or future focus affordances.

---

## Read-Only and Provenance Signaling

| Option | Description | Selected |
|--------|-------------|----------|
| Restrained explicit badge | Show small read-only/provenance signals and preserve source identity for later evidence workflows. | yes |
| Implicit read-only only | Rely on the absence of edit controls. | |
| Action-rich cards | Add editable or write-back-oriented controls. | |

**User's choice:** Approved recommended restrained explicit read-only/provenance signals.
**Notes:** Card selection/focus styling may exist as a future navigation affordance, but ANN11 must not expose create/edit/delete/save/import/apply/write-back.

---

## the agent's Discretion

- Exact function names, CSS class names, DOM structure, placeholder copy, tie-breakers, and test filenames may be chosen during planning/implementation.
- The planner should keep ANN11 scoped to card view-models, lane assignment, DOM rendering, states, CSS resilience, and tests.

## Deferred Ideas

- Source anchors: ANN12.
- Bidirectional navigation: ANN13.
- Connectors and visual polish: ANN14.
- Final verification/live harness: ANN15.
- Expandable details, draggable layout, persistent layout, editing/write-back, AI cards, and multi-paper boards: future scope.
