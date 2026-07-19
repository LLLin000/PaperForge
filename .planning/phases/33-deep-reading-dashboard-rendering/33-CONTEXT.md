# Phase 33: Deep-Reading Dashboard Rendering - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Render the deep-reading dashboard view when `_currentMode === 'deep-reading'`. Three sections: status card (paper state overview), Pass 1 full-text summary (extracted from deep-reading.md), and AI Q&A history (from discussion.json). All four empty-state conditions render Chinese fallback messages. Phase 32 provides mode routing.

</domain>

<decisions>
## Implementation Decisions

### Status Bar (Information Card)
- **D-01:** Single information card, vertical list style — consistent with health matrix in per-paper view.
- **D-02:** Shows: figure-map status (present/missing), OCR status (done/pending/failed), Pass completion (1/3, 2/3, 3/3), Health status (healthy/warning).
- **D-03:** Reads data from `entry` fields (canonical index) — no additional file reads needed.

### Pass 1 Summary Extraction
- **D-04:** Marker-based parsing from deep-reading.md content. Priority order: `**一句话总览**` → `**Pass 1**` heading → `**文章摘要**`. First match wins.
- **D-05:** Content after the marker is extracted as the summary text.
- **D-06:** Multiple `###` sub-sections under Pass 1 are included in the rendered card.
- **D-07:** RegExp fallback for formatting variations (bold vs markdown, Chinese vs English markers).

### AI Q&A Display
- **D-08:** Sessions-based grouping — each discussion session is a collapsible section.
- **D-09:** Q&A pairs displayed as dialog bubbles — question in one color, answer in another.
- **D-10:** AI Q&A section is DEFAULT COLLAPSED; user clicks to expand.
- **D-11:** Reads from discussion.json via vault.adapter.read() (NOT fs.readFileSync — vault-internal file).

### Empty States
- **D-12:** All four conditions render with Chinese placeholder messages (never JS errors):
  - (a) discussion.json missing → "暂无讨论记录"
  - (b) empty sessions array → "暂无问答内容"
  - (c) missing Pass 1 content → "暂无 Pass 1 总结"
  - (d) deep-reading.md not found → "精读文件未找到"

### Layout
- **D-13:** Three cards stacked vertically: status card, Pass 1 card, AI Q&A card.
- **D-14:** Status card and Pass 1 card expanded by default. AI Q&A card collapsed by default.
- **D-15:** CSS scoped under `.paperforge-mode-deepreading` with `paperforge-deepreading-*` component prefixes.

### the agent's Discretion
- Exact dialog bubble colors (use existing Obsidian CSS variables for consistency)
- Expanding/collapsing animation timing
- Number of `###` sub-sections shown before truncation (if content is very long)
- Deep-reading.md reading mechanism (vault.adapter.read() or Obsidian API)
</decisions>

<canonical_refs>
## Canonical References

### Phase scope and requirements
- `.planning/ROADMAP.md` § Phase 33 — Deep-Reading Dashboard Rendering
- `.planning/REQUIREMENTS.md` § DEEP-02, DEEP-03

### Prior phase context
- `.planning/phases/27-component-library/27-CONTEXT.md` — CSS naming conventions, render methods
- `.planning/phases/29-per-paper-view/29-CONTEXT.md` — Card layout patterns
- `.planning/phases/32-deep-reading-mode-detection/32-CONTEXT.md` — Mode routing, _currentPaperEntry, _renderDeepReadingMode() entry point
- `.planning/phases/31-bug-fixes/31-CONTEXT.md` — Lifecycle stage alignment

### Source code
- `paperforge/plugin/main.js` — _renderDeepReadingMode() placeholder (Phase 32), _renderPaperMode() for layout reference
- `paperforge/plugin/styles.css` — CSS class patterns
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_renderDeepReadingMode()` (main.js:959) — Empty placeholder from Phase 32, ready to be populated
- `_renderPaperMode()` (main.js:817) — Reference pattern for card layout (createEl, div stacking, CSS classes)
- `_renderHealthMatrix()` (main.js:592) — Reference for information-card-with-icons pattern
- `_getCachedIndex()` — For loading paper entry data
- `_findEntry(key)` — Single paper lookup
- `_currentPaperEntry` — Currently loaded paper entry (set by Phase 32)

### Established Patterns
- Card layout: `this._contentEl.createEl('div', { cls: 'paperforge-*-view' })` then nested divs
- CSS naming: `.paperforge-*` for components, `paperforge-*-*` for sub-elements
- Color: Obsidian CSS variables (`var(--color-*)`)
- Quick Actions bar remains visible in all modes (Phase 28 D-07)

### Integration Points
- Called from `_switchMode()` case `'deep-reading'` (Phase 32 D-10)
- `_currentPaperEntry` provides {lifecycle, health, maturity, deep_reading_path, ai_path, ocr_status}
- Phase 34 (Jump to Deep Reading button) depends on Phase 33 rendering being functional
</code_context>

<specifics>
## Specific Ideas

- Pass 1 content structure: `**一句话总览**` paragraph followed by multiple `###` sub-sections (研究问题与核心假设, 作者整体研究路线, etc.)
- Status card should feel like a compact overview — not a full health audit, just at-a-glance state
- AI dialog bubbles: question in one color (e.g., `var(--interactive-accent)` tint), answer in another (e.g., `var(--background-primary-alt)`)
- Session collapsible: header shows session date/model, clicking expands to reveal Q&A pairs

</specifics>

<deferred>
None — discussion stayed within phase scope
</deferred>

---

*Phase: 33-deep-reading-dashboard-rendering*
*Context gathered: 2026-05-06*
