# Annotation Phase 8: PDF Overlay Rendering Spike and Implementation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-06-28
**Phase:** annotation-08-pdf-overlay-rendering-spike-and-implementation
**Areas discussed:** overlay activation, visual mark style, overlay interaction, positioning and scope, lifecycle/fallback, verification

---

## Gray Areas Selection

| Option | Description | Selected |
|--------|-------------|----------|
| All | Discuss overlay mount, coordinate rendering, click detail, fallback, and verification boundaries. | yes |
| Risk only | Focus mainly on safe degradation when Obsidian PDF viewer internals are unavailable. | |
| Experience only | Focus mainly on highlight appearance and click behavior. | |

**User's choice:** All.
**Notes:** User selected all gray areas.

---

## Overlay Activation

| Option | Description | Selected |
|--------|-------------|----------|
| Auto attempt with safe fallback | Automatically try overlay when PDF viewer can be identified; fall back to list if unavailable. | yes |
| Manual toggle | User explicitly enables overlay before PaperForge tries to attach it. | |
| Spike only | Prove attachment/rendering but do not enable it in ordinary reading flow. | |

**User's choice:** Option 1.
**Notes:** Locked automatic probing with fail-closed fallback to sidebar/list.

---

## Visual Mark Style

| Option | Description | Selected |
|--------|-------------|----------|
| Lightweight translucent highlight | Use a semi-transparent fill like familiar PDF highlights. | yes |
| Thin border | Draw only an outline around the region. | |
| Small pin/marker | Show a compact marker near the annotated region. | |

**User's choice:** Option 1.
**Notes:** Highlight color should use annotation color when available, otherwise a restrained default yellow.

---

## Overlay Interaction

| Option | Description | Selected |
|--------|-------------|----------|
| PDF-local popover | Clicking/focusing a highlight shows selected text, comment, page/source details. | yes |
| Sidebar/list expansion | Clicking a highlight expands or focuses the matching annotation row. | optional |
| Both | Popover plus sidebar/list synchronization. | optional later |

**User's choice:** User delegated remaining decisions to the agent's inclination after earlier choices.
**Notes:** Agent decision: make PDF-local popover the Phase 8 main path; sidebar synchronization is optional/deferred.

---

## Positioning and Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Strict position-data rendering | Render only when page, PDF identity, and position/selector data can be trusted. | yes |
| Approximate page-level markers | If coordinates are missing, show page-level markers anyway. | |
| Guess from selected text | Search PDF text layer and infer positions from text. | |

**User's choice:** Agent discretion.
**Notes:** Agent decision: strict rendering only. Missing coordinates stay in sidebar/list and jump workflow; no guessed overlay.

---

## Lifecycle and Fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Event-driven attach/teardown | Attach on active PDF/paper and annotation state changes; teardown on file/pane/page changes. | yes |
| Continuous polling | Poll the viewer DOM and annotation state frequently. | |
| One-shot render only | Render once after navigation and do not refresh until reopened. | |

**User's choice:** Agent discretion.
**Notes:** Agent decision: event-driven lifecycle with no continuous polling.

---

## Verification Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Spike plus automated fallback tests | Document real viewer hooks, automate helpers/fallback/DOM where possible, manual check for live viewer. | yes |
| Automated only | Avoid manual verification even for viewer internals. | |
| Manual only | Rely on Obsidian manual testing for overlay behavior. | |

**User's choice:** Agent discretion.
**Notes:** Agent decision: start with spike, automate stable helpers and fallback, document manual Obsidian viewer check.

---

## the agent's Discretion

- Exact helper/function names and CSS class names.
- Whether spike and implementation are one plan or separate serial plans.
- Exact Obsidian viewer attachment point after research/spike.
- Exact popover placement and dismissal behavior, provided it remains lightweight and read-only.

## Deferred Ideas

- Bidirectional overlay/list synchronization if it adds risk.
- Local annotation editing/deletion.
- Zotero write-back.
- Concept-card evidence integration.
