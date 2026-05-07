# Phase 29: Per-Paper View - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Render the per-paper dashboard view using Phase 27 components, triggered by Phase 28 context detection when user opens a paper card (`.md` with `zotero_key`). No new component development.

Depends on: Phase 27 (components), Phase 28 (shell + `_findEntry`)

</domain>

<decisions>
## Implementation Decisions

### Render Entry Point
- **D-01:** `_renderPaperMode(entry)` — called by Phase 28 `_switchMode('paper')`.
- **D-02:** Entry comes from `this._findEntry(key)` using the frontmatter `zotero_key`.
- **D-03:** Shows loading skeleton while index loads, empty state if key not found.

### Component Layout (top to bottom)
- **D-04:** Paper metadata header: title, authors, year (from entry fields).
- **D-05:** Lifecycle stepper: `_renderLifecycleStepper(container, entry.lifecycle)`.
- **D-06:** Health matrix: `_renderHealthMatrix(container, entry.health)`.
- **D-07:** Maturity gauge: `_renderMaturityGauge(container, entry.maturity.level, entry.maturity.blocking)`.
- **D-08:** Next-step recommendation: shows `entry.next_step` as a human-readable action card.
- **D-09:** Next-step card includes an action button that triggers the relevant CLI command (sync/ocr/repair) or copies the key for `/pf-deep`.

### Contextual Actions
- **D-10:** Above the components, row of contextual action buttons.
- **D-11:** "Copy Context" — executes `paperforge context <key>`, copies to clipboard.
- **D-12:** "Open Fulltext" — opens the fulltext.md file from `entry.fulltext_path`.
- **D-13:** Use existing `ACTIONS` pattern from plugin for CLI commands.

### the agent's Discretion
- Button order (Copy Context vs Open Fulltext)
- Action button styling (icon vs text vs both)
- Whether to show abstract in the metadata header

</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` §Phase 29 — Per-Paper View success criteria
- `.planning/REQUIREMENTS.md` — PAPER-01..04
- `.planning/phases/27-component-library/27-CONTEXT.md` — Component render methods
- `.planning/phases/28-dashboard-shell-context-detection/28-CONTEXT.md` — Context detection + _findEntry
- `paperforge/plugin/main.js` — PaperForgeStatusView class

</canonical_refs>

<code_context>
## Reusable Assets
- `_renderLifecycleStepper(container, lifecycle)` — from Phase 27
- `_renderHealthMatrix(container, health)` — from Phase 27
- `_renderMaturityGauge(container, level, blockers)` — from Phase 27
- `_findEntry(key)` — from Phase 28
- `_loadIndex()` — from Phase 28
- Existing `ACTIONS` array and `_runAction()` for CLI commands

## Integration Points
- Called from Phase 28 `_switchMode()` when `_currentMode === 'paper'`
- Entry data comes from canonical index (formal-library.json)

</code_context>

<deferred>
None
</deferred>

---

*Phase: 29-per-paper-view*
*Context gathered: 2026-05-04*
