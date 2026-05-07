# Phase 28: Dashboard Shell & Context Detection - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Detect active file type and switch PaperForge dashboard to the correct mode (global, per-paper, or collection). Auto-refresh on file switch and index change. Phase 29-30 populate the views with data; Phase 28 provides the shell that routes to the right mode.

Depends on: Phase 27 component library (render methods exist)

</domain>

<decisions>
## Implementation Decisions

### Context Detection
- **D-01:** Detect active file via `this.app.workspace.getActiveFile()`.
- **D-02:** `.base` extension → collection mode.
- **D-03:** `.md` with `zotero_key` in frontmatter (via `metadataCache.getFileCache()`) → per-paper mode.
- **D-04:** All other files / no active file → global mode.

### Mode Switching
- **D-05:** `PaperForgeStatusView` adds `_currentMode` property: `'global' | 'paper' | 'collection'`.
- **D-06:** On mode change, clear existing content via `empty()` then call the appropriate render chain.
- **D-07:** Header area shows current mode context (paper title, domain name, or "PaperForge").

### Auto-Refresh
- **D-08:** Subscribe to `this.app.workspace.on('active-leaf-change', ...)` — triggers `_detectAndSwitch()`.
- **D-09:** Subscribe to `this.app.vault.on('modify', ...)` filtered to `formal-library.json` — triggers `_refreshCurrentMode()`.
- **D-10:** Initial data load on `onOpen()` via `_detectAndSwitch()`.

### Data Loading
- **D-11:** `_loadIndex()` reads `formal-library.json` (reusing path resolution from Phase 22-25).
- **D-12:** `_findEntry(key)` — lookup single paper by zotero_key from index items.
- **D-13:** `_filterByDomain(domain)` — filter index items by domain field.
- **D-14:** `_getCachedIndex()` — lazy-load and cache the parsed index in memory; invalidate on mtime change.

### Base Domain Resolution
- **D-15:** `.base` filename (without extension) = domain name. E.g., `骨科.base` → domain `骨科`.
- **D-16:** Domain name used to filter canonical index items.

### Error Handling
- **D-17:** If canonical index is missing or corrupt, show global mode with warning.
- **D-18:** If active paper not found in index, show empty state with "Paper not found" message.

### filewatch
- **D-19:** No fs.watch or Obsidian file watcher dependency. Use `vault.on('modify', ...)` with path filtering.

### the agent's Discretion
- Refresh debounce timing (recommend 500ms after active-leaf-change)
- Header format for each mode (paper title truncated at X chars, domain only, etc.)
- Whether to preserve scroll position on mode switch

</decisions>

<canonical_refs>
## Canonical References

### Phase scope and requirements
- `.planning/ROADMAP.md` §Phase 28 — Dashboard Shell & Context Detection
- `.planning/REQUIREMENTS.md` — DASH-01..04, REFR-01..02

### Source code
- `paperforge/plugin/main.js` — PaperForgeStatusView (lines 177-455), onOpen, _buildPanel, _fetchStats
- `paperforge/plugin/styles.css` — Component CSS from Phase 27
- `.planning/phases/27-component-library/27-CONTEXT.md` — Render methods available

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PaperForgeStatusView.onOpen()` — Currently calls `_buildPanel()` + `_fetchStats()`. Needs mode-aware refactor.
- `PaperForgeStatusView._fetchStats()` — Currently reads formal-library.json via `app.vault.adapter.basePath` + `fs.readFileSync()`.
- `paperforge/plugin/main.js:145` — `DEFAULT_SETTINGS`, `system_dir` for path resolution.
- Phase 27 render methods: `_renderSkeleton`, `_renderEmptyState`, `_renderStats`, `_renderLifecycleStepper`, `_renderHealthMatrix`, `_renderMaturityGauge`, `_renderBarChart`.

### Established Patterns
- Plugin uses `node:fs` for file I/O (readFileSync).
- Obsidian event subscription via `this.app.workspace.on()` and `this.app.vault.on()`.
- Container manipulation via `containerEl.empty()` then `createEl()`.

### Integration Points
- `PaperForgeStatusView.onOpen()` — Entry point for initial load.
- `PaperForgeStatusView.onClose()` — Clean up event listeners.
- Phase 29 will consume `_currentMode === 'paper'` + `_findEntry(key)`.
- Phase 30 will consume `_currentMode === 'collection'` + `_filterByDomain(domain)`.

</code_context>

<specifics>
## Specific Ideas

- When mode switches, the "global" quick actions should remain visible in all modes (Sync, OCR, etc.) — consistent action bar.
- Per-paper mode should add "Copy Context" and "Open Fulltext" as contextual actions.
- Collection mode should add "Sync Domain" and "Open Base" as contextual actions.

</specifics>

<deferred>
None — discussion stayed within phase scope
</deferred>

---

*Phase: 28-dashboard-shell-context-detection*
*Context gathered: 2026-05-04*
