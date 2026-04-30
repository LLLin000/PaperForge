---
phase: 20
name: Plugin Settings Shell & Persistence
milestone: v1.5
requirements: [SETUP-01, SETUP-02, SETUP-03]
status: planning
created: 2026-04-29
---

# Phase 20 Plan — Plugin Settings Shell & Persistence

## Files

| File | Action |
|------|--------|
| `paperforge/plugin/main.js` | MODIFY — add settings tab + persistence |
| `paperforge/plugin/styles.css` | MODIFY — add settings tab styles (minimal) |

## Design Decisions

- **All code in `main.js`:** No build system; CommonJS `require` from obsidian already works. A second file would need careful path handling. Keep it simple.
- **Debounced save at 500ms:** `setTimeout`/`clearTimeout` pattern. In-memory settings update immediately on input change; disk write is debounced.
- **`display()` lifecycle:** `display()` reconstructs DOM from `this.plugin.settings` on each call (tab switch). In-memory settings preserve state — no data loss.
- **String fields only:** No toggles/selects needed for this phase — all 8 settings are text inputs. Password field for API key.

## Tasks

### Task 1: Settings Data Model + Persistence

**File:** `paperforge/plugin/main.js`

Add after `ACTIONS[]` constant:

```js
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
```

In `PaperForgePlugin` class:

```js
async onload() {
    await this.loadSettings();          // NEW — must be first
    this.registerView(VIEW_TYPE_PAPERFORGE, (leaf) => new PaperForgeStatusView(leaf));
    this.addRibbonIcon('book-open', 'PaperForge Dashboard', () => PaperForgeStatusView.open(this));
    this.addSettingTab(new PaperForgeSettingTab(this.app, this));  // NEW
    // ... commands unchanged ...
}

async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
}

async saveSettings() {
    await this.saveData(this.settings);
}
```

**Acceptance:**
- `loadData()` returns null on fresh install → `DEFAULT_SETTINGS` merged without TypeError ✓
- `saveSettings()` writes `data.json` to Obsidian plugin data dir ✓

### Task 2: Settings Tab UI

**File:** `paperforge/plugin/main.js`

Add after `PaperForgeStatusView` class:

```js
const { PluginSettingTab, Setting } = require('obsidian');

class PaperForgeSettingTab extends PluginSettingTab {
    constructor(app, plugin) {
        super(app, plugin);
        this.plugin = plugin;
        this._saveTimeout = null;
    }

    display() {
        const { containerEl } = this;
        containerEl.empty();

        /* ── Section: 基础路径 ── */
        containerEl.createEl('h3', { text: '基础路径' });

        this._addTextSetting('vault_path', 'Vault 路径', '你的 Obsidian Vault 所在目录', '输入 Vault 完整路径...');
        this._addTextSetting('system_dir', '系统目录', '内部系统文件目录（默认 99_System）');
        this._addTextSetting('resources_dir', '资源目录', '管理资源文件目录（默认 20_Resources）');
        this._addTextSetting('literature_dir', '文献目录', '文献笔记存放目录（默认 Literature）');
        this._addTextSetting('control_dir', '控制目录', 'Library-records 控制文件目录（默认 Control）');
        this._addTextSetting('agent_config_dir', 'Agent 配置目录', 'Agent 技能目录（默认 .opencode）');

        /* ── Section: API 密钥 ── */
        containerEl.createEl('h3', { text: 'API 密钥' });

        this._addPasswordSetting('paddleocr_api_key', 'PaddleOCR API 密钥', '用于 OCR 文字识别的 API Key');

        /* ── Section: Zotero ── */
        containerEl.createEl('h3', { text: 'Zotero 链接' });

        this._addTextSetting('zotero_data_dir', 'Zotero 数据目录', 'Zotero 数据目录路径（可选，用于自动检测 PDF）');
    }

    _addTextSetting(key, name, desc, placeholder) {
        const setting = new Setting(this.containerEl)
            .setName(name)
            .setDesc(desc)
            .addText((text) => {
                text.setValue(this.plugin.settings[key] || '')
                    .setPlaceholder(placeholder || '')
                    .onChange((value) => {
                        this.plugin.settings[key] = value;
                        this._debouncedSave();
                    });
            });
        return setting;
    }

    _addPasswordSetting(key, name, desc) {
        const setting = new Setting(this.containerEl)
            .setName(name)
            .setDesc(desc)
            .addText((text) => {
                text.setValue(this.plugin.settings[key] || '')
                    .inputEl.type = 'password';
                text.onChange((value) => {
                    this.plugin.settings[key] = value;
                    this._debouncedSave();
                });
            });
        return setting;
    }

    _debouncedSave() {
        clearTimeout(this._saveTimeout);
        this._saveTimeout = setTimeout(() => this.plugin.saveSettings(), 500);
    }
}
```

**Acceptance:**
- All 8 fields render in correct sections ✓
- Editing a field updates in-memory immediately ✓
- `display()` re-entry (tab switch) preserves typed values ✓

### Task 3: Styles (minimal)

**File:** `paperforge/plugin/styles.css`

Only add if defaults don't look right. Obsidian's built-in `.setting-item` styles work well. Minimal additions:

```css
/* Settings tab sections */
.paperforge-settings-section {
    margin-top: 24px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--background-modifier-border);
}
```

## Success Criteria Verification

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 1 | Settings tab with all 8 fields renders | Open Obsidian → Settings → Community Plugins → PaperForge gear icon |
| 2 | Field edits survive tab switch | Edit a field, click another plugin's settings tab, return — value still there |
| 3 | Settings persist across restart | Fill all fields, restart Obsidian, open settings — values restored |
| 4 | Fresh install has defaults | Remove `data.json`, restart Obsidian — fields show default values |
| 5 | Sidebar and commands work | Click ribbon icon → sidebar panel opens, Sync/OCR buttons functional |

## Verification Commands

```bash
# No automated tests for plugin (UI-only). Manual verification:
# 1. Reload Obsidian (Ctrl+R or Ctrl+Shift+F5)
# 2. Verify settings tab
# 3. Verify sidebar
# 4. Verify commands via Ctrl+P → "PaperForge:"
```
