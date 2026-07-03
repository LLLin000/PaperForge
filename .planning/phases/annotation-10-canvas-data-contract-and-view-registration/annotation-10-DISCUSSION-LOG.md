# Annotation Phase 10: Canvas Data Contract and View Registration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-07-03
**Phase:** annotation-10-canvas-data-contract-and-view-registration
**Areas discussed:** entry points, paper identity, module boundaries, test gates

---

## Gray Areas Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Entry points | Determine whether the Reading Canvas opens from paper panel, command palette, or both. | yes |
| Paper identity | Determine how the canvas binds to the active paper and avoids stale or wrong-paper state. | yes |
| Module boundaries | Determine how to split `src/canvas/*`, keep `main.js` thin, and handle possible runtime import limitations. | yes |
| Test hooks | Determine the minimum Phase 10 verification gate. | yes |

**User's choice:** The user first selected entry points, then continued through the remaining Phase 10 gray areas.
**Notes:** Discussion stayed within Phase 10 foundation scope.

---

## Entry Points

| Option | Description | Selected |
|--------|-------------|----------|
| Paper panel button plus command palette | Use paper panel as the primary explicit-paper entry and command palette as secondary active-paper entry. | yes |
| Paper panel button only | Lowest UI surface, but no command palette access. | |
| Command palette only | Easy to wire, but less discoverable and depends on active-paper resolution. | |
| Global canvas browser | Would require a separate paper-selection workflow. | |

**User's choice:** Approved the recommended paper panel plus command palette approach.
**Notes:** Global browser/sidebar entry is out of scope for Phase 10.

---

## Paper Identity

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed explicit paperKey per canvas | Canvas opened from a paper is bound to that paper and does not auto-switch on active paper changes. | yes |
| Follow active paper automatically | Canvas changes when the active paper changes elsewhere. | |
| Re-resolve identity on every refresh | Refresh guesses paper identity each time from active file or global state. | |

**User's choice:** Approved the fixed explicit paperKey strategy.
**Notes:** From paper panel, use `entry.key`; from command palette, reuse active-paper resolution and fail with a Notice if no paper is available.

---

## Module Boundaries

| Option | Description | Selected |
|--------|-------------|----------|
| New `src/canvas/*` module set | Add `context.js`, `annotations.js`, `controller.js`, `render.js`, and `index.js`; keep `main.js` thin. | yes |
| Minimal two-file split | Only add `context.js` and `render.js`; simpler but risks mixing controller/annotation state into `main.js`. | |
| Inline in `main.js` first | Fastest shipping path, but repeats v0.2 helper-drift risk. | |

**User's choice:** Approved the new `src/canvas/*` module set.
**Notes:** Temporary inline fallback is allowed only if Obsidian runtime cannot require the modules reliably, and must be recorded as debt with parity/runtime tests.

---

## Test Gates

| Option | Description | Selected |
|--------|-------------|----------|
| Helper plus runtime focused gate | Cover context/annotations/controller/render helpers, view/command/button runtime wiring, `node --check main.js`, and v0.2 focused annotation tests. | yes |
| Runtime smoke only | Faster but would under-test stale guards and helper drift. | |
| Full visual canvas tests | Too broad for Phase 10 because cards, anchors, and connectors are later phases. | |

**User's choice:** Approved the helper plus runtime focused gate.
**Notes:** Phase 10 does not require annotation cards, anchors, connector geometry, full visual polish, or successful live native PDF overlay harness.

---

## the agent's Discretion

- The planner may choose exact helper names, CSS class names, command IDs, and test filenames.
- The planner may decide whether Phase 10 uses one implementation plan or multiple small plans.
- The planner must preserve the read-only boundary and v0.2 fallback regression gate.

## Deferred Ideas

- Annotation cards, source anchors, bidirectional navigation, connector lines, full visual polish, persistent layout, global canvas browser, annotation editing, Zotero write-back, AI cards, and multi-paper boards are deferred to later phases.
