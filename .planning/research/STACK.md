# Stack Research — v1.5 Obsidian Plugin Settings Tab

**Domain:** Obsidian plugin development (pure JS/CommonJS)
**Researched:** 2026-04-29
**Confidence:** HIGH (verified against existing plugin code and Obsidian API)

## Stack: Zero New Dependencies

This milestone requires NO new npm packages or tooling. Everything is built into Obsidian's plugin API and Node.js stdlib.

### Obsidian Plugin API (already available)

| API Class/Method | Purpose | Notes |
|-----------------|---------|-------|
| `PluginSettingTab` | Settings tab base class | `constructor(app, plugin)`, `display()`, `hide()` |
| `Setting` (from `obsidian`) | Form field builder | `.setName()`, `.setDesc()`, `.addText()`, `.addButton()`, `.addToggle()` |
| `Plugin.loadData()` | Load persisted settings | Returns `Promise<object | null>` |
| `Plugin.saveData(data)` | Persist settings to `data.json` | Returns `Promise<void>` |
| `Notice` (from `obsidian`) | Toast notifications | `new Notice(message, duration)`, supports `DocumentFragment` for rich content |
| `SettingTab.containerEl` | DOM container for settings UI | Use `this.containerEl.empty()` then `.createEl()` |

### Node.js Built-ins (already available in Electron/Obsidian)

| Module | Purpose | Notes |
|--------|---------|-------|
| `node:child_process` (`exec`, `spawn`) | Run Python subprocesses | Already used via `exec` for sidebar actions |
| `node:path` | Cross-platform path handling | `path.sep`, `path.join()`, `path.normalize()` |

### What NOT to Add

| Avoid | Why |
|-------|-----|
| TypeScript | Existing plugin is pure JS CommonJS; converting is out of scope |
| Build system (esbuild, webpack) | Plugin ships as single `main.js`; adding build step breaks current release flow |
| `obsidian-daily-notes-interface` or similar wrappers | Not needed for settings tab |
| React/Vue/Svelte | Obsidian settings use vanilla DOM; framework adds unnecessary complexity |
| `electron` APIs directly | Use Obsidian Plugin API wrappers to stay compatible |

## Settings Persistence Pattern

```js
// DEFAULT settings — merged on every load to prevent crashes on new keys
const DEFAULT_SETTINGS = {
    vault_path: '',
    system_dir: '99_System',
    resources_dir: '20_Resources',
    literature_dir: 'Literature',
    control_dir: 'Control',
    agent_config_dir: '.opencode',
    paddleocr_api_key: '',
    zotero_data_dir: '',
};

// In Plugin class:
async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
}

async saveSettings() {
    await this.saveData(this.settings);
}
```

## Subprocess Pattern for Setup

```js
const { spawn } = require('node:child_process');

// For progress-streaming setup steps (NOT exec — spawn avoids blocking + enables streaming)
function runSetup(settings, onStep, onDone) {
    const child = spawn('python', ['-m', 'paperforge', 'setup', '--json'], {
        cwd: settings.vault_path,
        env: { ...process.env, PADDLEOCR_API_TOKEN: settings.paddleocr_api_key },
    });
    // ... stream parsing ...
}
```

## Debounce Pattern for SaveData

```js
// Prevent data.json corruption from every-keystroke writes
let saveTimeout;
function debouncedSave(plugin) {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => plugin.saveSettings(), 500);
}
```

---

*Stack research for: PaperForge v1.5 Obsidian Plugin Setup Integration*
*Researched: 2026-04-29*
