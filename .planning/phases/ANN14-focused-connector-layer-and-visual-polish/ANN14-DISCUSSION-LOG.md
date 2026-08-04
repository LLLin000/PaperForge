# Phase ANN14: Focused Connector Layer and Visual Polish - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-07-06
**Phase:** ANN14 - Focused Connector Layer and Visual Polish
**Areas discussed:** Connector Eligibility, Geometry Lifecycle, Visual Language, Responsive Readability

---

## Connector Eligibility

| Option | Description | Selected |
|--------|-------------|----------|
| Only exact + selected/hovered | Draw connectors only for exact anchors when card or source anchor is selected/hovered. Most conservative and least misleading. | Yes |
| Exact solid, page-level weak dashed | Allows page-level hints but risks implying stronger evidence than the data supports. | |
| Exact/page-level both draw, unresolved hidden | Most visually complete but too likely to overstate page-level precision. | |

**User's choice:** 1 - only exact + selected/hovered.
**Notes:** Page-level, unresolved, stale, and unmeasured states should keep status/selection styling but receive no connector line.

---

## Geometry Lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| Conservative realtime recompute | Re-measure after selection/hover, scroll, resize, refresh, and lifecycle changes; hide when either endpoint cannot be measured. | Yes |
| Measure once on activation | Simpler but risks drifting lines after scroll/layout changes. | |
| Keep line to viewport edge | Stronger visual continuity but introduces offscreen inference semantics. | |

**User's choice:** 1 - conservative realtime recompute.
**Notes:** If either endpoint is offscreen, zero-size, stale, or missing, hide the connector. Do not guess or draw to the viewport edge.

---

## Visual Language

| Option | Description | Selected |
|--------|-------------|----------|
| Thin solid low-opacity line | Quiet reading aid; selected state can be slightly stronger; no arrows or endpoints. | Yes |
| Dashed/dotted line | Emphasizes non-permanence but can make exact grounding look uncertain. | |
| Annotation color + endpoint dots | More like the reference image but risks visual noise and heavier relationship polish. | |

**User's choice:** 1 - thin solid low-opacity line with selected enhancement.
**Notes:** No arrowheads, endpoint dots, annotation-color-following palette, or animation in ANN14.

---

## Responsive Readability

| Option | Description | Selected |
|--------|-------------|----------|
| Conservative hide | Hide connector when source/card endpoint is invisible, clipped, offscreen, zero-size, or layout is too narrow. | Yes |
| Fade/crop to visible region | More continuous but requires clipping logic and may imply hidden continuation. | |
| Direction indicator | Stronger UX but introduces a new UI semantic for a later phase. | |

**User's choice:** 1 - conservative hide.
**Notes:** Selection/focus state should remain visible when connectors hide.

---

## the agent's Discretion

- Exact helper/module names.
- SVG/path construction details.
- Measurement throttling strategy.
- Namespaced CSS class names.
- Test file split.

## Deferred Ideas

- Page-level weak/dashed connector hints.
- Offscreen edge indicators or direction badges.
- Cropped/faded continuation lines.
- Annotation-color-following connector palette.
- Endpoint dots, arrowheads, animations, and richer relationship polish.
- Full live native-PDF harness validation.

