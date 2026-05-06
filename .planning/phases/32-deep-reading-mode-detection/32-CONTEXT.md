# Phase 32: Deep-Reading Mode Detection - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Plugin detects `deep-reading.md` files (by filename + parent directory pattern) and routes them to a dedicated `deep-reading` dashboard mode, checked BEFORE the existing `zotero_key` frontmatter check. Prevents deep-reading.md from routing to per-paper mode. Phase 33 populates the deep-reading view with content.

</domain>

<decisions>
## Implementation Decisions

### Detection Strategy
- **D-01:** Check filename (`activeFile.basename === 'deep-reading'`) AND parent directory matches `{8-char-key} - {Title}` pattern.
- **D-02:** Insert this check as the FIRST branch inside the `.md` extension handler — BEFORE the `zotero_key` frontmatter check.
- **D-03:** If deep-reading.md is found outside a valid workspace parent pattern, fall back to normal `.md` handling (if has zotero_key → per-paper mode, else → global mode).

### Key Resolution
- **D-04:** In deep-reading mode, resolve zotero_key from frontmatter (`metadataCache.getFileCache().frontmatter.zotero_key`), same mechanism as per-paper mode.
- **D-05:** Use resolved key to call `_findEntry(key)` to load the paper's canonical index entry.

### Mode Identity Guard
- **D-06:** Track `_currentFilePath` alongside `_currentMode`. `_switchMode` checks BOTH mode string AND file path before treating as no-op.
- **D-07:** Extract `_resolveModeForFile()` as a pure function that returns `{mode, filePath, key}` given an activeFile. Decouples detection logic from side effects.

### State Management
- **D-08:** Add `'deep-reading'` to `_currentMode` type: `'global' | 'paper' | 'collection' | 'deep-reading'`.
- **D-09:** Deep-reading mode does NOT modify `_currentDomain` (stays null). Key and entry stored in `_currentPaperKey` / `_currentPaperEntry`.

### Auto-Refresh
- **D-10:** `_switchMode('deep-reading')` triggers `_renderDeepReadingMode()` similar to how paper mode triggers `_renderPaperMode()`. Content lives in `this._contentEl`.
- **D-11:** Refresh on active-leaf-change (300ms debounce carries from Phase 28), same as other modes.

### Quick Actions
- **D-12:** Deep-reading mode keeps the same Quick Actions bar as other modes (Sync, OCR, etc.) — consistent with Phase 28 D-07 principle.

### the agent's Discretion
- Exact regex for parent directory pattern validation
- CSS transition/animation class name for mode switch
- Error handling if `_findEntry()` returns null in deep-reading mode (show placeholder or empty state)

</decisions>

<canonical_refs>
## Canonical References

### Phase scope and requirements
- `.planning/ROADMAP.md` § Phase 32 — Deep-Reading Mode Detection
- `.planning/REQUIREMENTS.md` § DEEP-01 — Mode detection for deep-reading.md (checked BEFORE zotero_key)

### Prior phase context
- `.planning/phases/28-dashboard-shell-context-detection/28-CONTEXT.md` — Existing `_detectAndSwitch()`, `_switchMode()`, mode identity guard patterns
- `.planning/phases/29-per-paper-view/29-CONTEXT.md` — Per-paper key resolution via frontmatter
- `.planning/phases/31-bug-fixes/31-CONTEXT.md` — Lifecycle stage key alignment (affects deep-reading stage display)

### Source code
- `paperforge/plugin/main.js` — PaperForgeStatusView class, specifically `_detectAndSwitch()` (lines 714-760), `_switchMode()` (lines 763-780), `_refreshCurrentMode()` (lines 1046+)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_detectAndSwitch()` (main.js:714) — Current routing logic, will be extended with deep-reading branch
- `_switchMode()` (main.js:763) — Mode switching with identity check, content clear, render dispatch
- `_findEntry(key)` (main.js:446) — Single paper lookup by zotero_key from canonical index
- `_getCachedIndex()` (main.js:439) — Lazy-loaded, cached canonical index
- `this.app.metadataCache.getFileCache()` — Frontmatter reading (already used for zotero_key)

### Established Patterns
- `.md + zotero_key in frontmatter` → paper mode (Phase 28 D-03)
- `.base` → collection mode (Phase 28 D-02)
- No active file → global mode (Phase 28 D-04)
- Quick Actions bar visible in all modes (Phase 28 D-07)
- `active-leaf-change` triggers `_detectAndSwitch()` with 300ms debounce (Phase 28 D-08/D-19)

### Integration Points
- Phase 32 extends `_detectAndSwitch()` — INSERT deep-reading check INSIDE the `if (ext === 'md')` block, BEFORE the zotero_key check
- Phase 33 will consume `_currentMode === 'deep-reading'` in `_switchMode()` dispatch to call `_renderDeepReadingMode()`
- `_currentPaperKey` and `_currentPaperEntry` will be set for Phase 33 consumption
</code_context>

<specifics>
## Specific Ideas

- The detection order matters: deep-reading.md must be caught before its zotero_key frontmatter routes to per-paper mode
- Parent directory pattern: `{8-char-alphanumeric} - {anything}` — match `^[A-Z0-9]{8} - .+$` against parent dir name
- Identity guard should prevent mode re-render when same file is re-detected (double-fire from Obsidian)

</specifics>

<deferred>
None — discussion stayed within phase scope
</deferred>

---

*Phase: 32-deep-reading-mode-detection*
*Context gathered: 2026-05-06*
