---
phase: 22
name: Install Wizard Modal — Settings & Installation Separation
milestone: v1.5
requirements: []
status: planning
created: 2026-04-29
---

# Phase 22 Plan — Install Wizard Modal

## Problem

The settings tab currently mixes two concerns:
1. **Permanent configuration** — directory names, API keys, paths (needs to stay accessible)
2. **One-time installation flow** — checklist, status area, install button (looks "unfinished" after setup)

Users can't put BBT JSON in exports before directories exist. The install flow needs to be a guided wizard, not a single button buried in settings.

## Solution

- **Settings tab stays clean** — only config fields. No install UI.
- **PaperForgeSetupModal** — standalone Obsidian Modal with 5-step wizard
- Modal is triggered from settings tab and optionally from ribbon/command

## File Changes

| File | Action |
|------|--------|
| `paperforge/plugin/main.js` | MODIFY — clean settings tab, add PaperForgeSetupModal class |
| `paperforge/plugin/styles.css` | MODIFY — add modal, wizard step, and summary styles |

## Tasks

### Wave 1 — Settings Tab Cleanup + Modal Trigger

#### Task 1: Remove install UI from settings tab

**File:** `paperforge/plugin/main.js`

Remove from `PaperForgeSettingTab.display()`:
- "安装准备" section with checklist (4 items with `this._checklist`)
- "一键安装" section with status area and install button
- `_statusArea` property

The display method should end after `zotero_data_dir` setting.

**Acceptance:**
- `display()` contains no `安装准备`, `一键安装`, `paperforge-install-status`
- `this._statusArea` no longer exists on the class

#### Task 2: Add wizard trigger button

**File:** `paperforge/plugin/main.js`

Append after the Zotero data dir setting:

```js
/* ── Install Wizard Trigger ── */
new Setting(containerEl)
    .setName('安装向导')
    .setDesc('打开分步安装向导，创建目录结构并完成 PaperForge 环境配置')
    .addButton((btn) => {
        btn.setButtonText('打开安装向导')
            .setCta()
            .onClick(() => {
                new PaperForgeSetupModal(this.app, this.plugin).open();
            });
    });
```

**Acceptance:**
- `grep -n "PaperForgeSetupModal" paperforge/plugin/main.js` returns 2+ matches (import + usage)

#### Task 3: Add setup_complete status indicator

**File:** `paperforge/plugin/main.js`

Add a status hint before the wizard trigger that shows whether setup is complete:

```js
/* ── Setup Status ── */
const setupStatus = containerEl.createEl('div', { cls: 'paperforge-setup-status' });
if (this.plugin.settings.setup_complete) {
    setupStatus.setText('✓ PaperForge 环境已配置完成');
    setupStatus.addClass('paperforge-setup-done');
} else {
    setupStatus.setText('尚未完成安装，请点击下方按钮启动安装向导');
    setupStatus.addClass('paperforge-setup-pending');
}
```

Add `setup_complete: false` to `DEFAULT_SETTINGS`.

### Wave 2 — PaperForgeSetupModal (5-Step Wizard)

#### Task 4: Create PaperForgeSetupModal class with navigation

**File:** `paperforge/plugin/main.js` (append before `module.exports`)

Create a class extending `obsidian.Modal`. The Modal manages its own `_step` state (1-5) and renders content via a `_render()` method. Navigation buttons at the bottom: "上一步" (step > 1), "下一步" (step < 5), "关闭" (step 5 only).

Constructor takes `(app, plugin)`. Import `Modal` from obsidian at the top.

```js
const { Plugin, Notice, ItemView, Modal, Setting, PluginSettingTab } = require('obsidian');
```

```js
class PaperForgeSetupModal extends Modal {
    constructor(app, plugin) {
        super(app);
        this.plugin = plugin;
        this._step = 1;
        this._installError = null;
        this._installComplete = false;
    }

    onOpen() {
        this._render();
    }

    _render() {
        const { contentEl } = this;
        contentEl.empty();
        contentEl.addClass('paperforge-modal');

        this._renderStepIndicator();
        this._renderStepContent();
        this._renderNavigation();
    }
    // ...
}
```

Step indicator shows 5 dots with labels: 概览 → 目录 → 密钥 → 安装 → 完成. Current step is highlighted.

**Acceptance:**
- Modal opens from settings tab trigger
- 5 steps navigable with prev/next buttons
- Step indicator renders correctly
- Modal closes on Escape or "关闭"

#### Task 5: Step 1 — Overview

```js
_stepOverview() {
    const el = this.contentEl.createEl('div', { cls: 'paperforge-modal-step' });
    el.createEl('h2', { text: 'PaperForge 安装向导' });
    el.createEl('p', { text: '本向导将引导您完成 PaperForge 环境的完整配置。' });

    // Directory tree visualization
    const tree = el.createEl('div', { cls: 'paperforge-dir-tree' });
    tree.innerHTML = `
        <div class="paperforge-dir-node root">📁 Vault (${this.app.vault.adapter.basePath})</div>
        <div class="paperforge-dir-children">
            <div class="paperforge-dir-node folder">📁 ${this.plugin.settings.system_dir || '99_System'}/ — 系统文件</div>
            <div class="paperforge-dir-node folder">📁 ${this.plugin.settings.resources_dir || '20_Resources'}/ — 文献资源根目录
                <div class="paperforge-dir-children">
                    <div class="paperforge-dir-node file">📁 ${this.plugin.settings.literature_dir || 'Literature'}/ — 正文笔记</div>
                    <div class="paperforge-dir-node file">📁 ${this.plugin.settings.control_dir || 'Control'}/ — 索引卡片</div>
                </div>
            </div>
            <div class="paperforge-dir-node folder">📁 ${this.plugin.settings.base_dir || '05_Bases'}/ — Base 视图</div>
            <div class="paperforge-dir-node folder">📁 .opencode/ — Agent 配置</div>
        </div>
    `;

    el.createEl('p', { text: '安装过程将自动创建以上目录结构。您可以随时在设置中修改目录名称。', cls: 'paperforge-modal-hint' });
}
```

#### Task 6: Step 2 — Directory Review

Show all directory configs in a clean summary table:
- Vault path (read-only, auto-detected)
- 资源目录
- 正文目录 (under resources)
- 索引目录 (under resources)
- Base 目录
- 系统目录
- Agent 配置目录

Each row shows the key and the actual resolved path. All sourced from `this.plugin.settings`.

```js
_stepDirectories() {
    // For each setting, show name + description + current value + resolved path preview
    const s = this.plugin.settings;
    const vault = this.app.vault.adapter.basePath;
    const rows = [
        { name: 'Vault 路径', value: vault, resolved: vault },
        { name: '资源目录', key: 'resources_dir', resolved: `${vault}/${s.resources_dir}` },
        { name: '正文目录', key: 'literature_dir', resolved: `${vault}/${s.resources_dir}/${s.literature_dir}` },
        { name: '索引目录', key: 'control_dir', resolved: `${vault}/${s.resources_dir}/${s.control_dir}` },
        { name: 'Base 目录', key: 'base_dir', resolved: `${vault}/${s.base_dir}` },
        { name: '系统目录', key: 'system_dir', resolved: `${vault}/${s.system_dir}` },
        { name: 'Agent 配置', key: 'agent_config_dir', resolved: `${vault}/${s.agent_config_dir}` },
    ];
    // Render as a styled list/table
}
```

#### Task 7: Step 3 — Keys & Zotero

Show current values for:
- PaddleOCR API Key (masked, show last 4 chars if set)
- Zotero 数据目录

Allow inline editing or at least display the current values.

```js
_stepKeys() {
    const s = this.plugin.settings;
    // Show paddleocr_api_key with masked display
    // Show zotero_data_dir if set
    // Allow editing via Setting components
}
```

#### Task 8: Step 4 — Install

**This is the core step.** Shows:
1. Pre-install checklist (Zotero + BBT installed? API key ready?)
2. "开始安装" button → runs `python -m paperforge setup --headless` with current settings
3. Real-time progress display (stdout streaming)
4. Success/failure handling

```js
async _stepInstall() {
    const s = this.plugin.settings;

    // Checklist items
    const checks = [
        { id: 'zotero', text: '已安装 Zotero 桌面版 + Better BibTeX 插件' },
        { id: 'apikey', text: '已获取 PaddleOCR API Key', ok: !!s.paddleocr_api_key },
        { id: 'vault', text: 'Vault 路径正确', ok: true },
    ];

    // Render checklist with checkboxes

    // Install button — disabled until all checks pass
    // On click: spawn python -m paperforge setup --headless
    // Stream stdout to progress area
    // On success: mark setup_complete = true, move to step 5
    // On failure: show error, allow retry
}
```

Use same `spawn` pattern as current `_runSetup()` but render status in the modal content instead of Obsidian notices. Add a progress log area that accumulates lines.

#### Task 9: Step 5 — Completion Summary

After successful install:

```js
_stepComplete() {
    const s = this.plugin.settings;
    const vault = this.app.vault.adapter.basePath;
    
    el.createEl('h2', { text: '✅ 安装完成' });
    el.createEl('p', { text: 'PaperForge 环境已成功配置。以下为当前完整配置：' });

    // Full config summary table:
    // - All 8 directories with resolved full paths
    // - API Key status (已配置/未配置)
    // - Zotero data dir status

    // Next Steps section:
    el.createEl('h3', { text: '📋 下一步操作' });
    const steps = [
        '配置 Better BibTeX 自动导出：Zotero → 编辑 → 首选项 → Better BibTeX → 勾选 "Keep updated"，导出路径设置为：',
        `${vault}/${s.system_dir}/PaperForge/exports/library.json`,
        '将 Zotero 数据目录链接到 Vault：打开终端运行 paperforge doctor 查看推荐命令',
        '在 Obsidian 中运行 /pf-sync 同步文献',
        '或点击侧边栏 PaperForge 图标，在 Dashboard 中运行 Sync Library',
    ];
    // Render each step

    // Button: "关闭向导" → close modal
}
```

### Success Criteria

- [ ] Settings tab contains NO install UI (no checklist, no status area, no install button)
- [ ] Settings tab has "打开安装向导" CTA button that opens the modal
- [ ] Modal shows 5-step wizard with step indicator
- [ ] Step 2 shows resolved paths correctly (资源/正文/索引 relationships clearly displayed)
- [ ] Step 4 runs headless_setup with progress display
- [ ] Step 5 shows full config summary and next steps
- [ ] Modal handles errors gracefully (network failure, missing Python, etc.)
