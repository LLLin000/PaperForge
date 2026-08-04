# Phase ANN12: Controlled Reading Surface and Source Anchors - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-07-06
**Phase:** ANN12-Controlled Reading Surface and Source Anchors
**Areas discussed:** Central reading source priority, anchor precision levels, exact text matching, missing source behavior, anchor visual form, safe deferred interaction boundary

---

## Central Reading Source Priority

| Option | Description | Selected |
|--------|-------------|----------|
| Fulltext-first fallback chain | Prefer `entry.fulltext_path`, fall back to formal note body/summary, then explicit source-unavailable placeholder. | yes |
| Formal note first | Use paper note content before OCR fulltext. | |
| Placeholder only | Do not render source text until PDF-aware rendering exists. | |

**User's choice:** Approved the recommended fulltext-first fallback chain.
**Notes:** The central surface should not be blank when source is missing, and it should remain PaperForge-owned DOM.

---

## Anchor Precision Levels

| Option | Description | Selected |
|--------|-------------|----------|
| Three explicit statuses | Use `exact`, `page-level`, and `unresolved`, with visibly different semantics. | yes |
| Binary anchored/unanchored | Treat all supported anchors as one class. | |
| Visual-first anchors | Render anchors optimistically and explain uncertainty later. | |

**User's choice:** Approved the recommended three-status model.
**Notes:** Exact means unique source-text grounding; page-level and unresolved must not look like exact evidence.

---

## Exact Text Matching

| Option | Description | Selected |
|--------|-------------|----------|
| Conservative unique match | Generate exact anchors only when selected text uniquely matches owned source text. | yes |
| Fuzzy or ranked match | Pick the best candidate when text approximately matches. | |
| Multi-match exact | Treat multiple matching spans as exact candidates. | |

**User's choice:** Approved conservative unique matching.
**Notes:** Ambiguity downgrades to page-level or unresolved. ANN12 must not guess.

---

## Missing Source Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve cards and show source-unavailable | Keep annotation cards visible and mark anchors unresolved with reasons. | yes |
| Hide annotations without source | Do not show cards when no source can be rendered. | |
| Treat as empty canvas | Collapse source-missing state into empty. | |

**User's choice:** Approved preserving cards with explicit source-unavailable state.
**Notes:** Missing source is not the same as no annotations.

---

## Anchor Visual Form

| Option | Description | Selected |
|--------|-------------|----------|
| Exact inline highlight plus page/block marker | Exact gets restrained inline highlight; page-level gets page/block marker; unresolved gets status only. | yes |
| All anchors inline | Render all anchors as inline highlights. | |
| Marker strip only | Avoid inline highlighting entirely in ANN12. | |

**User's choice:** Approved exact inline highlights plus page/block markers.
**Notes:** Page-level markers must not imply text-level precision.

---

## Safe Deferred Interaction Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Anchor model/render only | Expose anchor identity/status/source span/page block, but defer navigation and connectors. | yes |
| Include navigation | Let cards and anchors focus/scroll each other in ANN12. | |
| Include connector geometry | Draw relationship lines as part of anchor work. | |

**User's choice:** Approved anchor model/render only.
**Notes:** Navigation belongs to ANN13. Connectors belong to ANN14. ANN12 must avoid native PDF DOM dependency and write-back controls.

---

## the agent's Discretion

- The planner may choose exact helper names, source model shapes, normalization thresholds, CSS class names, placeholder copy, and focused test filenames.
- The planner should preserve the conservative grounding strategy and clearly separate exact/page-level/unresolved anchor semantics.

## Deferred Ideas

- Card/source navigation and selection synchronization: ANN13.
- Connector lines and geometry: ANN14.
- Final live harness and full canvas verification: ANN15.
- Native PDF DOM anchoring, PDF.js, fuzzy/ranked matching, local editing/write-back, draggable layout, AI cards, and multi-paper boards: future scope.
