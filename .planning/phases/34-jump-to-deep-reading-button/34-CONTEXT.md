# Phase 34: Jump to Deep Reading Button - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Per-paper dashboard card provides a one-click contextual button to open the associated deep-reading.md file, with file-existence verification before navigation. Button is hidden when the paper has no deep_reading_path or deep_reading_status is not 'done'. Phase 33 provides the deep-reading dashboard rendering that the button navigates to. Phase 32 provides the mode detection that triggers when deep-reading.md opens.

</domain>

<decisions>
## Implementation Decisions

### Button Placement & Relationship to Existing Button
- **D-01:** The jump button lives in the **next-step recommendation card**, replacing the "Copy Context" button when the card shows "All Set" (`ready`) state AND `deep_reading_status === 'done'`.
- **D-02:** The existing "Copy Key for /pf-deep" (clipboard copy) in the `/pf-deep` next-step state remains unchanged — it serves a different lifecycle stage (pre-deep-reading).
- **D-03:** Button is **hidden** (not just disabled) when conditions are not met.
- **D-04:** On click: call `getAbstractFileByPath(deep_reading_path)` to verify file existence, then `openLinkText()` to open deep-reading.md in the active leaf.
- **D-05:** If `deep_reading_path` exists in the index but the file is missing from disk, show an Obsidian Notice ("精读文件未找到") instead of crashing.

### Label & i18n Strategy
- **D-06:** Button label added to the existing `t()` i18n language pack (main.js LANG.zh / LANG.en).
- **D-07:** Chinese label: `"跳转到精读"`, English label: `"Open Deep Reading"`.
- **D-08:** Icon: magnifying glass — reuses the same icon the existing `/pf-deep` next-step card uses.

### the agent's Discretion
- Exact positioning of the button text within the next-step card element structure
- CSS class name for the button
- Whether to add a subtle tooltip on hover

</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` § Phase 34
- `.planning/REQUIREMENTS.md` § NAV-01
- `.planning/phases/29-per-paper-view/29-CONTEXT.md` — Next-step card layout
- `.planning/phases/32-deep-reading-mode-detection/32-CONTEXT.md` — Mode routing
- `.planning/phases/33-deep-reading-dashboard-rendering/33-CONTEXT.md` — Dashboard rendering
- `paperforge/plugin/main.js` — _renderPaperMode, _renderNextStepCard, _openFulltext
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_renderNextStepCard()` (main.js:890) — The next-step card where the jump button lives
- `_openFulltext()` (main.js:944) — Reference pattern: getAbstractFileByPath → openLinkText → Notice
- `LANG` object and `t()` function — i18n system for button label

### Integration Points
- `entry.deep_reading_path` and `entry.deep_reading_status` from canonical index
- Click opens deep-reading.md → active-leaf-change → mode detection → Phase 33 rendering
</code_context>

<specifies>
No specific requirements beyond decisions above
</specifies>

<deferred>
None
</deferred>

---

*Phase: 34-jump-to-deep-reading-button*
*Context gathered: 2026-05-06*
