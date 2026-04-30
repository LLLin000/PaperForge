# Architecture Research — v1.5 Obsidian Plugin Settings Tab

**Domain:** Obsidian plugin architecture — settings tab integration with existing sidebar
**Researched:** 2026-04-29
**Confidence:** HIGH

## Current Architecture (v1.4 plugin)

```
paperforge/plugin/main.js (257 lines, CommonJS)
│
├── PaperForgePlugin extends Plugin
│   ├── onload() → registerView, addRibbonIcon, addCommand(sync, ocr)
│   └── onunload() → detachLeavesOfType
│
├── PaperForgeStatusView extends ItemView   ← SIDEBAR (unchanged)
│   ├── _buildPanel() → metrics, OCR progress, quick actions
│   ├── _fetchStats() → exec('python -m paperforge status --json')
│   └── _runAction() → exec('python -m paperforge sync/ocr')
│
└── ACTIONS[] → sync, ocr command definitions
```

Key observations:
- No `loadData`/`saveData` usage — no persistence at all
- No `PluginSettingTab` subclass — no settings tab
- Uses `exec` (not `spawn`) for subprocesses
- Single file, no module splitting

## Target Architecture (v1.5)

```
paperforge/plugin/main.js
│
├── PaperForgePlugin extends Plugin          ← MODIFIED (adds settings tab)
│   ├── DEFAULT_SETTINGS (new)               ← Settings data shape
│   ├── settings (new)                       ← Runtime settings state (loadData/saveData)
│   ├── onload()                             ← MODIFIED: adds addSettingTab()
│   │   ├── registerView (unchanged)
│   │   ├── addRibbonIcon (unchanged)
│   │   ├── addSettingTab(new PaperForgeSettingTab(this.app, this))  ← NEW
│   │   └── addCommand × 2 (unchanged)
│   ├── loadSettings() (new)                 ← Object.assign(DEFAULTS, await loadData())
│   └── saveSettings() (new)                 ← await saveData(this.settings)
│
├── PaperForgeSettingTab extends PluginSettingTab  ← NEW: settings tab
│   ├── display()
│   │   ├── Section: "基础路径" → vault_path, system_dir, resources_dir, etc.
│   │   ├── Section: "API 密钥" → paddleocr_api_key (password field)
│   │   ├── Section: "Zotero 链接" → zotero_data_dir
│   │   └── Section: "安装" → Install button + status area
│   ├── _validate()                          ← Field-level validation
│   ├── _runSetup()                          ← spawn('python -m paperforge setup')
│   └── _formatNotice()                      ← Polished notice from step results
│
├── PaperForgeStatusView extends ItemView    ← SIDEBAR (completely unchanged)
│
└── ACTIONS[] (unchanged)
```

## Integration Points

### 1. Plugin class additions (MODIFIED)

```js
// Settings data model
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

// In PaperForgePlugin:
async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
}

async saveSettings() {
    await this.saveData(this.settings);
}

// In onload(), add after existing registrations:
this.addSettingTab(new PaperForgeSettingTab(this.app, this));
```

### 2. SettingsTab class (NEW)

```js
class PaperForgeSettingTab extends PluginSettingTab {
    constructor(app, plugin) {
        super(app, plugin);
        this.plugin = plugin;
    }

    display() {
        const { containerEl } = this;
        containerEl.empty();
        // ... build form sections ...
    }
}
```

### 3. Subprocess interface (NEW pattern: spawn instead of exec)

Settings tab runs setup via `spawn` for non-blocking progress:

```js
_runSetup() {
    const { spawn } = require('node:child_process');
    const child = spawn('python', ['-m', 'paperforge', 'setup'], {
        cwd: this.plugin.settings.vault_path,
    });
    child.stdout.on('data', (data) => { /* parse step, show notice */ });
    child.stderr.on('data', (data) => { /* parse error, show friendly notice */ });
    child.on('close', (code) => { /* final notice */ });
}
```

### 4. Notice formatting (NEW)

Current code: `new Notice('[!!] sync failed: ' + stderr)` — raw terminal output.

New pattern:
```js
_formatNotice(type, step, detail) {
    const messages = {
        success: { prefix: '[OK]', style: 'notice-success' },
        error: { prefix: '[!!]', style: 'notice-error' },
        progress: { prefix: '[...]', style: '' },
    };
    // Map raw stderr to friendly Chinese messages
    // Log full details to console, show summary in Notice
}
```

## Data Flow

```
1. User opens Obsidian → Plugin Settings → PaperForge
2. display() renders form fields from this.plugin.settings
3. User fills in paths, API key
4. Each text input onChange → debounced saveSettings()
5. User clicks "安装配置" button
6. _runSetup():
   a. _validate() all fields → show specific errors if any
   b. Disable button, show "[...] 正在配置..."
   c. spawn('python -m paperforge setup') with env vars from settings
   d. Parse stdout line-by-line for step progress
   e. Show Notice per step ("创建目录... ✓", "写入配置... ✓")
   f. On completion: Enable button, show "[OK] 配置完成" or "[!!] 配置失败: reason"
7. Sidebar continues working independently (still reads paperforge.json via exec)
```

## Component Responsibilities

| Component | Responsibility | Status |
|-----------|---------------|--------|
| `DEFAULT_SETTINGS` | Data shape, defaults | NEW |
| `PaperForgePlugin.loadSettings()` | Persistence load with defaults merge | NEW |
| `PaperForgePlugin.saveSettings()` | Debounced persistence save | NEW |
| `PaperForgeSettingTab.display()` | UI rendering | NEW |
| `PaperForgeSettingTab._validate()` | Pre-submit field validation | NEW |
| `PaperForgeSettingTab._runSetup()` | Setup subprocess orchestration | NEW |
| `PaperForgeSettingTab._formatNotice()` | Human-readable notice output | NEW |
| `PaperForgeStatusView` | Sidebar (unchanged) | EXISTING |
| `ACTIONS[]` | Quick action definitions (unchanged) | EXISTING |

## Build Order

```
Phase 1: Settings Shell + Persistence
  ├── Add DEFAULT_SETTINGS
  ├── Add loadSettings() / saveSettings() to Plugin
  ├── Create PaperForgeSettingTab with display()
  ├── Register via addSettingTab() in onload()
  └── Verify: settings tab appears, fields persist across restart, sidebar still works

Phase 2: Install Button + Setup Orchestration
  ├── Add _validate() for field-level checks
  ├── Add _runSetup() with spawn integration
  ├── Add _formatNotice() for polished output
  └── Verify: install button works, notices are human-readable, sidebar unaffected
```

---

*Architecture research for: PaperForge v1.5 Obsidian Plugin Setup Integration*
*Researched: 2026-04-29*
