# Research Summary — v1.5 Obsidian Plugin Settings Tab

**Synthesized:** 2026-04-29
**Sources:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md

## Stack Additions

**Zero new dependencies.** All work uses Obsidian Plugin API + Node.js stdlib:
- `PluginSettingTab` — settings tab base class
- `Plugin.loadData()` / `Plugin.saveData()` — persistence to `data.json`
- `Setting` — form field builder (`.addText()`, `.addButton()`, etc.)
- `Notice` — toast notifications (`.setName()`, `.setDesc()`)
- `node:child_process.spawn` — non-blocking subprocess execution (upgrade from `exec`)

No TypeScript, no build system, no new npm packages.

## Feature Table Stakes

1. Settings tab with all setup_wizard.py fields (vault path, 5 dirs, API key, Zotero junction)
2. Settings persist across Obsidian restarts
3. One-click "Install" button runs full setup pipeline
4. Human-readable Chinese notices — never raw terminal output
5. Existing sidebar preserved unchanged

## Architecture

Two-phase build order:
1. **Phase 1 — Settings Shell + Persistence:** Add `DEFAULT_SETTINGS`, `loadSettings()`/`saveSettings()`, `PaperForgeSettingTab` class, register via `addSettingTab()`. Verify sidebar still works.
2. **Phase 2 — Install Button + Setup UX:** Field validation, `spawn`-based subprocess orchestration, polished notice formatting.

Settings tab is purely additive — zero changes to existing `PaperForgeStatusView` or `ACTIONS[]`.

## Watch Out For (Critical Pitfalls)

| # | Pitfall | Prevention |
|---|---------|------------|
| 1 | `saveData` on every keystroke corrupts `data.json` | Debounce saves (500ms timeout) |
| 2 | `display()` destroys form state on tab switch | Immediate in-memory update on change, debounce only disk write |
| 3 | Raw Python tracebacks in Notice | Parse stderr, map to friendly messages, log full details to console |
| 4 | Windows paths with spaces/Unicode break `exec` | Use `spawn` with proper quoting; test on `C:\Users\Test User\Test 测试\` |
| 5 | Button double-click spawns duplicate processes | `setDisabled(true)` + `setButtonText('Running...')` at start |
| 6 | `loadData()` returns `null` → TypeError | Always merge: `Object.assign({}, DEFAULTS, data || {})` |

---

*Research complete: 2026-04-29*
