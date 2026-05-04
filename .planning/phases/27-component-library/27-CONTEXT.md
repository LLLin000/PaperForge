# Phase 27: Component Library - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Build pure CSS/DOM visualization components in `paperforge/plugin/styles.css` and `PaperForgeStatusView` render methods. No npm dependencies. All components use Obsidian CSS variables for theming.

Does NOT cover context detection (Phase 28), per-paper view (Phase 29), or collection view (Phase 30).

</domain>

<decisions>
## Implementation Decisions

### Component Architecture
- **D-01:** All components are rendered as `createEl()` calls in `PaperForgeStatusView` methods.
- **D-02:** All styling lives in `paperforge/plugin/styles.css` with `.paperforge-*` class names.
- **D-03:** No npm dependencies, no external CSS frameworks, no canvas/JS chart libraries.

### Metric Card Component
- **D-04:** Rendered as `div.paperforge-metric-card` with child `.metric-value` (large number) and `.metric-label`.
- **D-05:** Optional `.metric-progress-bar` child for maturity gauge context.
- **D-06:** CSS transition on value change (opacity 0.3s).

### Lifecycle Stepper Component
- **D-07:** Vertical step indicator: 6 stages rendered as rows of `div.step`.
- **D-08:** Each `.step` has: `.step-indicator` (circle via border-radius) + `.step-label`.
- **D-09:** CSS `::before` pseudo-element draws connecting line between steps.
- **D-10:** States: `.completed` (green circle + checkmark), `.current` (highlighted, pulsing), `.pending` (gray, dimmed).
- **D-11:** Labels use human-readable names: "Imported", "Indexed", "PDF Ready", "Fulltext Ready", "Deep Read", "AI Ready".

### Health Matrix Component
- **D-12:** 2x2 CSS grid: `div.health-matrix` with `grid-template-columns: 1fr 1fr`.
- **D-13:** 4 cells: PDF Health, OCR Health, Note Health, Asset Health.
- **D-14:** Color coding: `.ok` (green via `var(--color-green)`), `.warn` (yellow/orange), `.fail` (red).
- **D-15:** Each cell shows dimension label + status icon (✓ / ⚠ / ✗).
- **D-16:** Hover tooltip shows specific check results (via CSS `::after` or `title` attribute).

### Maturity Gauge Component
- **D-17:** Segmented horizontal bar: `div.maturity-gauge` with 6 child `.segment` divs.
- **D-18:** Filled segments get color; unfilled segments are gray.
- **D-19:** Current level number displayed prominently below the gauge.
- **D-20:** Blocking checks listed as bullet points under the gauge when level < 6.

### Bar Chart Component
- **D-21:** Horizontal CSS bars: `div.bar-chart` with child `.bar-row` elements.
- **D-22:** Each `.bar-row` has: `.bar-label` (lifecycle name) + `.bar-track` (container) + `.bar-fill` (width as percentage) + `.bar-count` (number).
- **D-23:** Bar transitions smooth via CSS `transition: width 0.3s`.

### Loading & Empty States
- **D-24:** All components show inset loading skeleton shimmer (CSS `@keyframes` animation) when data is null/loading.
- **D-25:** Empty state shows "No data" message with muted styling.

### Theming
- **D-26:** All colors use Obsidian CSS variables: `var(--color-green)`, `var(--color-yellow)`, `var(--color-red)`, `var(--color-cyan)`, `var(--color-blue)`, `var(--color-purple)`, `var(--text-muted)`, `var(--background-modifier-border)`.
- **D-27:** Components respect dark mode automatically through CSS variable binding.

### File Organization
- **D-28:** No new JS files. Components are methods on `PaperForgeStatusView` class.
- **D-29:** `styles.css` gets new sections: each component documented with header comments.

### the agent's Discretion
- Exact CSS variable color choices for each component state.
- Gradient vs flat colors for gauge segments.
- Pulse animation speed for current lifecycle step.
- Tooltip implementation (CSS `::after` vs `title` attribute).
- Loading skeleton animation details.

</decisions>

<canonical_refs>
## Canonical References

### Phase scope and requirements
- `.planning/ROADMAP.md` §Phase 27 — Component Library success criteria
- `.planning/REQUIREMENTS.md` — COMP-01, COMP-02, COMP-03

### Source code
- `paperforge/plugin/main.js` — PaperForgeStatusView ItemView class (lines 177-455), _buildPanel, _renderStats
- `paperforge/plugin/styles.css` — Existing dashboard styling, target for new component styles

### Reference research
- Obsidian CSS variables: `var(--color-green)`, `var(--color-yellow)`, `var(--color-red)`, `var(--color-cyan)`, `var(--color-blue)`, `var(--color-purple)`, `var(--text-muted)`, `var(--background-modifier-border)`
- Dashboard Navigator card layout patterns
- Note Toolbar CSS pattern (pure DOM, no framework)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `paperforge/plugin/main.js:282-295` — Current `_renderStats()` metric card pattern (createEl with value/label, colored by var(--color-*))
- `paperforge/plugin/main.js:299-365` — Current `_renderOcr()` progress bar pattern (segmented divs with percentage widths)
- `paperforge/plugin/styles.css` — Existing `.paperforge-metric-card`, `.paperforge-progress-seg`, `.paperforge-action-card` classes

### Established Patterns
- Plugin renders via `createEl()` DOM API calls — no JSX/react
- Progress bars use nested divs with width percentage
- Color coding via `style.setProperty('--metric-color', ...)` or direct CSS classes
- Quick Actions in 160px min-width grid (`repeat(auto-fit, minmax(160px, 1fr))`)

### Integration Points
- Existing `_renderStats(d)` method reads from canonical index summary and renders metric cards
- Existing `_renderOcr(d)` method reads OCR counts and renders progress bar
- New components will be rendered by Phase 28-30 calling into these components with specific data

</code_context>

<specifics>
## Specific Ideas

- Metrics cards should feel like Dashboard Navigator's file type stats cards — large rounded corners, shadow, clear typography hierarchy.
- Lifecycle stepper should feel like a job pipeline view (imported → processed → ready).
- Health matrix colors should match Obsidian's status colors (green = OK, yellow/yellow = warn, red = fail).
- Don't add JS chart libraries — pure CSS bar charts are sufficient for lifecycle distribution.

</specifics>

<deferred>
None — discussion stayed within phase scope
</deferred>

---

*Phase: 27-component-library*
*Context gathered: 2026-05-04*
