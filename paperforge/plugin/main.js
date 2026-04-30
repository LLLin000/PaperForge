const { Plugin, Notice, ItemView, Modal, Setting, PluginSettingTab } = require('obsidian');
const { exec } = require('node:child_process');
const { LANG, detectLang } = require('./i18n.js');

const VIEW_TYPE_PAPERFORGE = 'paperforge-status';

let T = LANG.zh;  // default Chinese, updated in onload()

function t(key) { return T[key] || LANG.en[key] || key; }

const DEFAULT_SETTINGS = {
    vault_path: '',
    system_dir: 'System',
    resources_dir: 'Resources',
    literature_dir: 'Notes',
    control_dir: 'Index_Cards',
    base_dir: 'Base',
    setup_complete: false,
    auto_update: true,
    agent_platform: 'opencode',
    language: '',
};

const ACTIONS = [
    {
        id: 'paperforge-sync',
        title: 'Sync Library',
        desc: 'Pull new references from Zotero and generate literature notes',
        icon: '\u21BB',  // ↻
        cmd: 'sync',
        okMsg: 'Sync complete',
    },
    {
        id: 'paperforge-ocr',
        title: 'Run OCR',
        desc: 'Extract full text and figures from PDFs via PaddleOCR',
        icon: '\u229E',  // ⊞
        cmd: 'ocr',
        okMsg: 'OCR started',
    },
];

class PaperForgeStatusView extends ItemView {
    constructor(leaf) { super(leaf); }

    getViewType() { return VIEW_TYPE_PAPERFORGE; }
    getDisplayText() { return 'PaperForge'; }
    getIcon() { return 'book-open'; }

    async onOpen() {
        this._buildPanel();
        this._fetchStats();
    }

    onClose() { /* no-op */ }

    /* ---------------------------------------------------------------------- */
    /*  Build Panel                                                           */
    /* ---------------------------------------------------------------------- */
    _buildPanel() {
        const root = this.containerEl;
        root.empty();
        root.addClass('paperforge-status-panel');

        /* ── Header ── */
        const header = root.createEl('div', { cls: 'paperforge-header' });

        const headerLeft = header.createEl('div', { cls: 'paperforge-header-left' });
        headerLeft.createEl('div', { cls: 'paperforge-header-logo', text: 'P' });
        headerLeft.createEl('h3', { cls: 'paperforge-header-title', text: 'PaperForge' });
        this._versionBadge = headerLeft.createEl('span', { cls: 'paperforge-header-badge', text: 'v\u2014' });

        const refreshBtn = header.createEl('button', { cls: 'paperforge-header-refresh', attr: { 'aria-label': 'Refresh' } });
        refreshBtn.innerHTML = '\u21BB';
        refreshBtn.addEventListener('click', () => this._fetchStats());

        /* ── Status Message (command output) ── */
        this._messageEl = root.createEl('div', { cls: 'paperforge-message' });

        /* ── Metric Cards (populated by _renderStats) ── */
        this._metricsEl = root.createEl('div', { cls: 'paperforge-metrics' });

        /* ── OCR Pipeline ── */
        this._ocrSection = root.createEl('div', { cls: 'paperforge-ocr-section' });
        this._ocrSection.style.display = 'none';

        const ocrHeader = this._ocrSection.createEl('div', { cls: 'paperforge-ocr-header' });
        ocrHeader.createEl('h4', { cls: 'paperforge-ocr-title', text: 'OCR Pipeline' });
        this._ocrBadge = ocrHeader.createEl('span', { cls: 'paperforge-ocr-badge idle', text: 'Idle' });

        this._ocrTrack = this._ocrSection.createEl('div', { cls: 'paperforge-progress-track' });
        this._ocrCounts = this._ocrSection.createEl('div', { cls: 'paperforge-ocr-counts' });
        this._ocrEmpty = this._ocrSection.createEl('div', { cls: 'paperforge-ocr-empty', text: 'No OCR tasks yet. Mark papers with do_ocr: true to start.' });

        /* ── Quick Actions ── */
        const actions = root.createEl('div', { cls: 'paperforge-actions-section' });
        actions.createEl('h4', { cls: 'paperforge-actions-title', text: 'Quick Actions' });

        const actionsGrid = actions.createEl('div', { cls: 'paperforge-actions-grid' });
        for (const a of ACTIONS) {
            const card = actionsGrid.createEl('div', { cls: 'paperforge-action-card' });
            card.createEl('div', { cls: 'paperforge-action-card-icon', text: a.icon });
            card.createEl('div', { cls: 'paperforge-action-card-title', text: a.title });
            card.createEl('div', { cls: 'paperforge-action-card-desc', text: a.desc });
            card.createEl('div', { cls: 'paperforge-action-card-hint', text: 'Click to run' });
            card.addEventListener('click', () => this._runAction(a, card));
        }
    }

    /* ---------------------------------------------------------------------- */
    /*  Fetch & Render Stats                                                  */
    /* ---------------------------------------------------------------------- */
    _fetchStats() {
        this._metricsEl.empty();
        this._metricsEl.createEl('div', { cls: 'paperforge-status-loading', text: 'Loading...' });

        const vp = this.app.vault.adapter.basePath;
        exec('python -m paperforge status --json', { cwd: vp, timeout: 30000 }, (err, stdout) => {
            this._metricsEl.empty();
            if (err) {
                this._metricsEl.createEl('div', { cls: 'paperforge-status-error', text: 'Cannot reach PaperForge CLI.\nMake sure paperforge is installed and in your PATH.' });
                return;
            }
            try {
                const d = JSON.parse(stdout);
                this._renderStats(d);
                this._renderOcr(d);
            } catch {
                this._metricsEl.createEl('div', { cls: 'paperforge-status-error', text: 'Invalid response from paperforge status.' });
            }
        });
    }

    /* ── Metric Cards ── */
    _renderStats(d) {
        this._versionBadge.setText(d.version ? 'v' + d.version : 'v\u2014');

        const metrics = [
            { value: d.total_papers, label: 'Papers', color: 'var(--color-cyan)' },
            { value: d.formal_notes, label: 'Notes', color: 'var(--color-blue)' },
            { value: d.exports, label: 'Exports', color: 'var(--color-purple)' },
        ];
        for (const m of metrics) {
            const card = this._metricsEl.createEl('div', { cls: 'paperforge-metric-card' });
            card.style.setProperty('--metric-color', m.color);
            card.createEl('div', { cls: 'paperforge-metric-value', text: m.value?.toString() || '\u2014' });
            card.createEl('div', { cls: 'paperforge-metric-label', text: m.label });
        }
    }

    /* ── OCR Pipeline ── */
    _renderOcr(d) {
        const ocr = d.ocr || {};
        const total = ocr.total || 0;

        if (total === 0) {
            this._ocrSection.style.display = 'none';
            return;
        }

        this._ocrSection.style.display = 'block';
        this._ocrEmpty.style.display = 'none';

        const done = ocr.done || 0;
        const pending = ocr.pending || 0;
        const processing = ocr.processing || 0;
        const failed = ocr.failed || 0;

        /* Badge */
        this._ocrBadge.removeClass('active', 'idle');
        if (processing > 0 || pending > 0) {
            this._ocrBadge.addClass('active');
            this._ocrBadge.setText('Active');
        } else {
            this._ocrBadge.addClass('idle');
            this._ocrBadge.setText('Idle');
        }

        /* Segmented progress bar */
        this._ocrTrack.empty();
        const segs = [
            { cls: 'pending', count: pending },
            { cls: 'active', count: processing },
            { cls: 'done', count: done },
            { cls: 'failed', count: failed },
        ];
        for (const s of segs) {
            if (s.count > 0) {
                const pct = (s.count / total * 100).toFixed(1);
                this._ocrTrack.createEl('div', {
                    cls: `paperforge-progress-seg ${s.cls}`,
                    attr: { style: `width:${pct}%` },
                });
            }
        }

        /* Counts row */
        this._ocrCounts.empty();
        const labels = [
            { cls: 'pending', value: pending, label: 'Pending' },
            { cls: 'active', value: processing, label: 'Active' },
            { cls: 'done', value: done, label: 'Done' },
            { cls: 'failed', value: failed, label: 'Failed' },
        ];
        for (const l of labels) {
            const cnt = this._ocrCounts.createEl('div', { cls: 'paperforge-ocr-count' });
            cnt.createEl('div', { cls: 'paperforge-ocr-count-value', text: l.value.toString() });
            cnt.createEl('div', { cls: 'paperforge-ocr-count-label', text: l.label });
        }
    }

    /* ── Run Action ── */
    _runAction(a, card) {
        card.addClass('running');
        const vp = this.app.vault.adapter.basePath;
        this._showMessage(`Running ${a.title}...`, 'running');
        exec(`python -m paperforge ${a.cmd}`, { cwd: vp, timeout: 300000 }, (err, stdout, stderr) => {
            card.removeClass('running');
            if (err) {
                const msg = stderr ? stderr.split('\n').filter(Boolean).slice(-2).join(' | ') : err.message;
                this._showMessage(`[!!] ${a.cmd} failed: ${msg}`, 'error');
                new Notice(`[!!] ${a.cmd} failed: ${msg}`, 8000);
                return;
            }
            const output = stdout.trim();
            const summary = output.split('\n').filter(Boolean);
            const first = summary[0]?.slice(0, 80) || a.okMsg || 'Done';
            const detail = summary.length > 1 ? ` (${summary.length} lines)` : '';
            this._showMessage(`[OK] ${a.title}: ${first}${detail}`, 'ok');
            new Notice(`[OK] ${a.okMsg || first}`);
            this._fetchStats();
        });
    }

    _showMessage(msg, cls) {
        if (this._messageEl) {
            this._messageEl.setText(msg);
            this._messageEl.className = `paperforge-message msg-${cls}`;
        }
    }

    /* ── Static: open or reveal view ── */
    static async open(plugin) {
        const leaves = plugin.app.workspace.getLeavesOfType(VIEW_TYPE_PAPERFORGE);
        if (leaves.length > 0) {
            plugin.app.workspace.revealLeaf(leaves[0]);
            return;
        }
        const leaf = plugin.app.workspace.getRightLeaf(false);
        if (leaf) {
            await leaf.setViewState({ type: VIEW_TYPE_PAPERFORGE, active: true });
            plugin.app.workspace.revealLeaf(leaf);
        }
    }
}

class PaperForgeSettingTab extends PluginSettingTab {
    constructor(app, plugin) {
        super(app, plugin);
        this.plugin = plugin;
        this._saveTimeout = null;
    }

    display() {
        const { containerEl } = this;
        containerEl.empty();

        const vaultPath = this.app.vault.adapter.basePath;
        if (!this.plugin.settings.vault_path) {
            this.plugin.settings.vault_path = vaultPath;
            this._debouncedSave();
        }

        /* ── Header ── */
        containerEl.createEl('h2', { text: t('header_title') || 'PaperForge' });
        containerEl.createEl('p', {
            text: t('desc'),
            cls: 'paperforge-settings-desc'
        });

        /* ── Setup Status ── */
        const statusRow = containerEl.createEl('div', { cls: 'paperforge-setup-bar' });
        const statusLabel = statusRow.createEl('span', { cls: 'paperforge-setup-label' });
        if (this.plugin.settings.setup_complete) {
            statusLabel.setText('✓ PaperForge 环境已配置完成');
            statusLabel.addClass('paperforge-setup-done');
        } else {
            statusLabel.setText('尚未安装，完成下方安装准备后点击安装向导');
            statusLabel.addClass('paperforge-setup-pending');
        }

        /* ── Preparation Guide ── */
        containerEl.createEl('h3', { text: '安装准备' });
        containerEl.createEl('p', {
            text: '首次使用前，请依次完成以下准备：',
            cls: 'paperforge-settings-desc'
        });
        const prep = containerEl.createEl('div', { cls: 'paperforge-guide' });
        const prepItems = [
            { title: 'Python 3.9+', desc: '确保 Python 可命令行调用。点击下方按钮会自动检测' },
            { title: 'Zotero 桌面版', desc: '安装 Zotero (https://www.zotero.org)' },
            { title: 'Better BibTeX', desc: 'Zotero → 工具 → 插件 → 安装 Better BibTeX for Zotero' },
            { title: 'BBT 自动导出', desc: 'Zotero 中右键文献子分类 → 导出分类 → BetterBibTeX JSON → 勾选保持更新 → 导出到下方路径（JSON 文件名即为生成的 Base 名）：' },
            { title: '', desc: `${vaultPath}/${this.plugin.settings.system_dir || 'System'}/PaperForge/exports/library.json` },
            { title: 'PaddleOCR Key', desc: '在 https://aistudio.baidu.com/paddleocr 注册获取 API Key' },
        ];
        for (const item of prepItems) {
            const row = prep.createEl('div', { cls: 'paperforge-guide-item' });
            if (item.title) row.createEl('strong', { text: item.title });
            row.createEl('span', { text: item.desc });
        }

        /* ── Pre-check status area ── */
        this._checkEl = containerEl.createEl('div', { cls: 'paperforge-message' });

        /* ── Install / Reconfigure Button ── */
        const needSetup = !this.plugin.settings.setup_complete;
        new Setting(containerEl)
            .setName(needSetup ? '安装向导' : '重新配置')
            .setDesc(needSetup
                ? '自动检测 Python + API Key，通过后打开分步安装向导'
                : '重新运行安装向导，修改目录或密钥配置')
            .addButton((btn) => {
                btn.setButtonText(needSetup ? '打开安装向导' : '重新配置')
                    .setCta()
                    .onClick(() => {
                        if (!needSetup) {
                            new PaperForgeSetupModal(this.app, this.plugin).open();
                        } else {
                            this._preCheck(() => {
                                new PaperForgeSetupModal(this.app, this.plugin).open();
                            });
                        }
                    });
            });

        /* ── Operation Guide ── */
        containerEl.createEl('h3', { text: '操作方式' });
        const guide = containerEl.createEl('div', { cls: 'paperforge-guide' });
        const guideItems = [
            { title: '打开 Dashboard', desc: 'Ctrl+P → 输入 PaperForge: Open Dashboard，或点左侧书本图标' },
            { title: '同步文献', desc: 'Dashboard 中点 Sync Library，从 Zotero 拉取文献生成笔记' },
            { title: '运行 OCR', desc: 'Dashboard 中点 Run OCR，提取 PDF 全文与图表' },
        ];
        for (const item of guideItems) {
            const row = guide.createEl('div', { cls: 'paperforge-guide-item' });
            row.createEl('strong', { text: item.title });
            row.createEl('span', { text: ' — ' + item.desc });
        }

        /* ── Config Summary (only after install) ── */
        if (this.plugin.settings.setup_complete) {
            containerEl.createEl('h3', { text: '当前配置' });
            const summary = containerEl.createEl('div', { cls: 'paperforge-summary' });
            const s = this.plugin.settings;
            const items = [
                { label: 'Vault 路径', val: vaultPath },
                { label: '资源目录', val: `${vaultPath}/${s.resources_dir}` },
                { label: '　正文目录', val: `${vaultPath}/${s.resources_dir}/${s.literature_dir}` },
                { label: '　索引目录', val: `${vaultPath}/${s.resources_dir}/${s.control_dir}` },
                { label: 'Base 目录', val: `${vaultPath}/${s.base_dir}` },
                { label: '系统目录', val: `${vaultPath}/${s.system_dir}` },
                { label: 'API Key', val: s.paddleocr_api_key ? '已配置 ✓' : '未配置 ✗' },
                { label: 'Zotero 数据', val: s.zotero_data_dir || '未设置' },
            ];
            for (const item of items) {
                const row = summary.createEl('div', { cls: 'paperforge-summary-row' });
                row.createEl('span', { cls: 'paperforge-summary-label', text: item.label });
                row.createEl('span', { cls: 'paperforge-summary-value', text: item.val });
            }
        }
    }

    _debouncedSave() {
        clearTimeout(this._saveTimeout);
        this._saveTimeout = setTimeout(() => this.plugin.saveSettings(), 500);
    }

    _preCheck(onPass) {
        exec('python --version', { timeout: 8000 }, (pyErr, pyOut) => {
            const results = [];
            const fs = require('fs');
            const path = require('path');

            /* 1 — Python */
            results.push({ label: 'Python', ok: !pyErr, detail: pyErr ? '未安装' : pyOut.trim() });

            /* 2 — Zotero (check install + data dir) */
            let zotOk = false;
            // Try common install locations
            const progFiles = process.env.ProgramFiles || '';
            const localAppData = process.env.LOCALAPPDATA || '';
            const zotInstallDirs = [
                path.join(progFiles, 'Zotero'),
                path.join(progFiles, '(x86)', 'Zotero'),
                path.join(localAppData, 'Programs', 'Zotero'),
                path.join(localAppData, 'Zotero'),
                path.join(home, 'AppData', 'Local', 'Programs', 'Zotero'),
            ].filter(Boolean);
            zotOk = zotInstallDirs.some(d => { try { return fs.existsSync(d); } catch { return false; } });
            // Fallback: check if data dir is configured
            const zotDataDir = this.plugin.settings.zotero_data_dir;
            if (!zotOk && zotDataDir) {
                try { zotOk = fs.existsSync(zotDataDir); } catch {}
            }
            results.push({ label: 'Zotero', ok: zotOk, detail: zotOk ? '已安装' : '未检测到' });

            /* 3 — Better BibTeX (check Zotero extensions dir) */
            let bbtOk = false;
            const appData = process.env.APPDATA || '';
            if (appData) {
                const profilesDir = path.join(appData, 'Zotero', 'Zotero', 'Profiles');
                try {
                    if (fs.existsSync(profilesDir)) {
                        for (const p of fs.readdirSync(profilesDir)) {
                            if (fs.existsSync(path.join(profilesDir, p, 'extensions', 'better-bibtex@retorque.re'))) {
                                bbtOk = true; break;
                            }
                        }
                    }
                } catch {}
            }
            results.push({ label: 'Better BibTeX', ok: bbtOk, detail: bbtOk ? '已安装' : '未检测到' });

            /* Render */
            const marks = { true: '✓', false: '✗' };
            if (this._checkEl) {
                this._checkEl.setText(results.map(r => `${marks[r.ok]} ${r.label}: ${r.detail}`).join('\n'));
                const anyFail = results.some(r => !r.ok);
                this._checkEl.className = `paperforge-message msg-${anyFail ? 'error' : 'ok'}`;
            }
            const bad = results.filter(r => !r.ok);
            if (bad.length > 0) {
                new Notice(`[!!] 未通过: ${bad.map(r => r.label).join(', ')}`, 6000);
            }

            onPass();
        });
    }
}

/* ==========================================================================
   Setup Wizard Modal
   ========================================================================== */
class PaperForgeSetupModal extends Modal {
    constructor(app, plugin) {
        super(app);
        this.plugin = plugin;
        this._step = 1;
    }

    onOpen() {
        this._render();
    }

    onClose() {
        this.contentEl.empty();
    }

    _render() {
        const { contentEl } = this;
        contentEl.empty();
        contentEl.addClass('paperforge-modal');

        this._renderStepIndicator();
        this._renderStepContent();
        this._renderNavigation();
    }

    _renderStepIndicator() {
        const steps = ['概览', '目录', 'Agent', '安装', '完成'];
        const bar = this.contentEl.createEl('div', { cls: 'paperforge-step-bar' });
        steps.forEach((label, i) => {
            const n = i + 1;
            const dot = bar.createEl('div', {
                cls: `paperforge-step-dot ${n === this._step ? 'active' : ''} ${n < this._step ? 'done' : ''}`
            });
            dot.createEl('span', { cls: 'paperforge-step-num', text: `${n}` });
            dot.createEl('span', { cls: 'paperforge-step-label', text: label });
        });
    }

    _renderStepContent() {
        const el = this.contentEl.createEl('div', { cls: 'paperforge-step-content' });
        switch (this._step) {
            case 1: this._stepOverview(el); break;
            case 2: this._stepDirectories(el); break;
            case 3: this._stepKeys(el); break;
            case 4: this._stepInstall(el); break;
            case 5: this._stepComplete(el); break;
        }
    }

    _renderNavigation() {
        const nav = this.contentEl.createEl('div', { cls: 'paperforge-step-nav' });
        if (this._step > 1) {
            nav.createEl('button', { cls: 'paperforge-step-btn', text: '← 上一步' })
                .addEventListener('click', () => { this._step--; this._render(); });
        }
        if (this._step < 5) {
            nav.createEl('button', { cls: 'paperforge-step-btn mod-cta', text: '下一步 →' })
                .addEventListener('click', () => { this._step++; this._render(); });
        } else {
            nav.createEl('button', { cls: 'paperforge-step-btn', text: '关闭' })
                .addEventListener('click', () => this.close());
        }
    }

    /* ── Step 1: Overview ── */
    _stepOverview(el) {
        el.createEl('h2', { text: 'PaperForge 安装向导' });
        el.createEl('p', { text: '本向导将引导您完成 PaperForge 环境的完整配置。安装过程会自动创建所有目录结构，无需手动操作。' });

        const s = this.plugin.settings;
        const vault = this.app.vault.adapter.basePath;
        const tree = el.createEl('div', { cls: 'paperforge-dir-tree' });
        tree.innerHTML = `
            <div class="paperforge-dir-node root">📁 Vault (${vault})</div>
            <div class="paperforge-dir-children">
                <div class="paperforge-dir-node folder">📁 ${s.resources_dir || 'Resources'}/ — 文献资源根目录
                    <div class="paperforge-dir-children">
                        <div class="paperforge-dir-node file">📁 ${s.literature_dir || 'Notes'}/ — 正文笔记</div>
                        <div class="paperforge-dir-node file">📁 ${s.control_dir || 'Index_Cards'}/ — 索引卡片</div>
                    </div>
                </div>
                <div class="paperforge-dir-node folder">📁 ${s.base_dir || 'Base'}/ — Base 视图文件</div>
                <div class="paperforge-dir-node folder">📁 ${s.system_dir || 'System'}/ — 系统文件</div>
            </div>`;

        el.createEl('p', {
            text: '系统文件和 Agent 配置位于 Vault 根目录下。文献数据（正文、索引）统一存放在资源目录内。安装后所有字段仍可在设置中修改。',
            cls: 'paperforge-modal-hint'
        });
    }

    /* ── Step 2: Directory Config (editable) ── */
    _stepDirectories(el) {
        el.createEl('h2', { text: '目录配置' });
        el.createEl('p', { text: '配置 PaperForge 的文件组织方式。所有值均可自定义，留空则使用默认值。' });

        const s = this.plugin.settings;
        const vault = this.app.vault.adapter.basePath;

        this._modalField(el, 'Vault 路径', vault, true);

        el.createEl('p', { text: '资源目录是文献数据的统一根目录，以下子目录将创建在其内部：', cls: 'paperforge-modal-hint' });

        this._modalInput(el, '资源目录', 'resources_dir', s.resources_dir, 'Resources');

        el.createEl('p', { text: '资源目录内的两个子目录：', cls: 'paperforge-modal-hint' });

        this._modalInput(el, '正文目录', 'literature_dir', s.literature_dir, 'Notes');
        this._modalInput(el, '索引目录', 'control_dir', s.control_dir, 'Index_Cards');

        el.createEl('p', { text: '独立于资源目录的系统文件：', cls: 'paperforge-modal-hint' });

        this._modalInput(el, '系统目录', 'system_dir', s.system_dir, 'System');
        this._modalInput(el, 'Base 目录', 'base_dir', s.base_dir, 'Base');
    }

    /* ── Step 3: Keys, Zotero & Agent ── */
    _stepKeys(el) {
        el.createEl('h2', { text: 'API 密钥与 Agent 平台' });
        const s = this.plugin.settings;

        el.createEl('p', { text: '选择你使用的 AI Agent 平台，安装时将按对应格式部署技能文件：', cls: 'paperforge-modal-hint' });

        const AGENTS = [
            { key: 'opencode', name: 'OpenCode' },
            { key: 'claude', name: 'Claude Code' },
            { key: 'cursor', name: 'Cursor' },
            { key: 'github_copilot', name: 'GitHub Copilot' },
            { key: 'windsurf', name: 'Windsurf' },
            { key: 'codex', name: 'Codex' },
            { key: 'cline', name: 'Cline' },
        ];
        const agentRow = el.createEl('div', { cls: 'paperforge-modal-field' });
        agentRow.createEl('label', { cls: 'paperforge-modal-label', text: 'Agent 平台' });
        const select = agentRow.createEl('select', { cls: 'paperforge-modal-select' });
        for (const a of AGENTS) {
            const opt = select.createEl('option', { text: a.name, attr: { value: a.key } });
            if (a.key === (s.agent_platform || 'opencode')) opt.selected = true;
        }
        select.addEventListener('change', () => {
            s.agent_platform = select.value;
            if (this._pendingSave) clearTimeout(this._pendingSave);
            this._pendingSave = setTimeout(() => { this.plugin.saveSettings(); this._pendingSave = null; }, 500);
        });

        el.createEl('p', { text: '以下为 API 密钥与 Zotero 配置：', cls: 'paperforge-modal-hint' });

        this._modalSecret(el, 'PaddleOCR API 密钥', 'paddleocr_api_key', s.paddleocr_api_key, '用于 OCR 文字识别的 API Key');
        this._modalInput(el, 'Zotero 数据目录', 'zotero_data_dir', s.zotero_data_dir || '', '可选，用于自动检测 PDF');
    }

    /* ── Modal form helpers ── */
    _modalField(el, label, value, disabled) {
        const row = el.createEl('div', { cls: 'paperforge-modal-field' });
        row.createEl('label', { cls: 'paperforge-modal-label', text: label });
        const input = row.createEl('input', { cls: 'paperforge-modal-input', attr: { type: 'text' } });
        input.value = value;
        input.disabled = !!disabled;
    }

    _modalInput(el, label, key, value, placeholder) {
        const row = el.createEl('div', { cls: 'paperforge-modal-field' });
        row.createEl('label', { cls: 'paperforge-modal-label', text: label });
        const input = row.createEl('input', {
            cls: 'paperforge-modal-input',
            attr: { type: 'text', placeholder: placeholder || '' }
        });
        input.value = value;
        const settings = this.plugin.settings;
        input.addEventListener('input', () => {
            settings[key] = input.value;
            if (this._pendingSave) clearTimeout(this._pendingSave);
            this._pendingSave = setTimeout(() => {
                this.plugin.saveSettings();
                this._pendingSave = null;
            }, 500);
        });
    }

    _modalSecret(el, label, key, value, placeholder) {
        const row = el.createEl('div', { cls: 'paperforge-modal-field' });
        row.createEl('label', { cls: 'paperforge-modal-label', text: label });
        const input = row.createEl('input', {
            cls: 'paperforge-modal-input',
            attr: { type: 'password', placeholder: placeholder || '' }
        });
        input.value = value;
        const settings = this.plugin.settings;
        input.addEventListener('input', () => {
            settings[key] = input.value;
            if (this._pendingSave) clearTimeout(this._pendingSave);
            this._pendingSave = setTimeout(() => {
                this.plugin.saveSettings();
                this._pendingSave = null;
            }, 500);
        });
    }

    /* ── Step 4: Install ── */
    _stepInstall(el) {
        el.createEl('h2', { text: '开始安装' });
        this._installLog = el.createEl('div', { cls: 'paperforge-install-log' });

        const startBtn = el.createEl('button', {
            cls: 'paperforge-step-btn mod-cta',
            text: '开始安装'
        });
        startBtn.addEventListener('click', () => this._runInstall(startBtn));
    }

    async _runInstall(btn) {
        btn.disabled = true;
        btn.textContent = '正在安装...';
        this._installLog.setText('正在配置 PaperForge 环境...\n');
        this._log('正在验证配置...');

        const s = this.plugin.settings;
        const errors = this._validate();
        if (errors.length > 0) {
            this._log('验证失败：');
            errors.forEach(e => this._log('  ✗ ' + e));
            btn.disabled = false;
            btn.textContent = '重试';
            return;
        }

        const { spawn } = require('node:child_process');
        const args = [
            '-m', 'paperforge',
            '--vault', s.vault_path.trim(),
            'setup', '--headless',
            '--paddleocr-key', s.paddleocr_api_key.trim(),
            '--system-dir', s.system_dir.trim(),
            '--resources-dir', s.resources_dir.trim(),
            '--literature-dir', s.literature_dir.trim(),
            '--control-dir', s.control_dir.trim(),
            '--base-dir', s.base_dir.trim(),
            '--agent', s.agent_platform || 'opencode',
        ];
        if (s.zotero_data_dir && s.zotero_data_dir.trim()) {
            args.push('--zotero-data', s.zotero_data_dir.trim());
        }

        try {
            await new Promise((resolve, reject) => {
                const child = spawn('python', args, {
                    cwd: s.vault_path.trim(),
                    env: process.env,
                    timeout: 120000,
                });
                child.stdout.on('data', (data) => {
                    const text = data.toString('utf-8');
                    this._processSetupOutput(text);
                });
                child.stderr.on('data', (data) => {
                    const text = data.toString('utf-8');
                    this._log('[stderr] ' + text.trim());
                });
                child.on('close', (code) => {
                    code === 0 ? resolve() : reject(new Error(`exit code ${code}`));
                });
                child.on('error', (err) => reject(err));
            });
            this._log('\n✓ 安装完成！');
            s.setup_complete = true;
            await this.plugin.saveSettings();
            setTimeout(() => { this._step = 5; this._render(); }, 800);
        } catch (err) {
            console.error('PaperForge setup failed:', err.message);
            this._log('\n✗ 安装失败：' + this._formatSetupError(err.message));
            btn.disabled = false;
            btn.textContent = '重试';
        }
    }

    _log(msg) {
        if (this._installLog) {
            this._installLog.setText(this._installLog.textContent + msg + '\n');
        }
    }

    _validate() {
        const errors = [];
        const s = this.plugin.settings;
        if (!s.vault_path || !s.vault_path.trim()) errors.push('Vault 路径未填写');
        if (!s.resources_dir || !s.resources_dir.trim()) errors.push('资源目录未填写');
        if (!s.literature_dir || !s.literature_dir.trim()) errors.push('正文目录未填写');
        if (!s.control_dir || !s.control_dir.trim()) errors.push('索引目录未填写');
        if (!s.base_dir || !s.base_dir.trim()) errors.push('Base 目录未填写');
        if (!s.paddleocr_api_key || !s.paddleocr_api_key.trim()) errors.push('PaddleOCR API 密钥未填写');
        return errors;
    }

    _processSetupOutput(text) {
        const lines = text.split('\n').filter(Boolean);
        for (const line of lines) {
            if (line.includes('[*]') || line.includes('[OK]') || line.includes('[FAIL]')) {
                const clean = line.replace(/^\[\*\].*\d+:?\s*/, '').replace(/^\[OK\]\s*/, '').replace(/^\[FAIL\]\s*/, '');
                this._log('  ' + clean);
            }
        }
    }

    _formatSetupError(raw) {
        const patterns = [
            { match: /command not found|No such file|not recognized/i, msg: '未找到 Python 环境，请确保已安装 Python 并加入 PATH' },
            { match: /paperforge.*not found|cannot import|ModuleNotFoundError|No module named/i, msg: '未安装 PaperForge 包，请先运行 pip install paperforge' },
            { match: /permission denied|EACCES/i, msg: '权限不足，无法创建目录或写入文件' },
            { match: /ENOENT/i, msg: '路径不存在，请检查 Vault 路径是否正确' },
            { match: /timeout|timed out/i, msg: '操作超时，请检查网络连接后重试' },
        ];
        for (const p of patterns) {
            if (p.match.test(raw)) return p.msg;
        }
        const fallback = raw.split('\n').filter(Boolean).slice(0, 3).join('；');
        return fallback.slice(0, 200) || '未知错误，请查看控制台日志';
    }

    /* ── Step 5: Complete ── */
    _stepComplete(el) {
        el.createEl('h2', { text: '✓ PaperForge 安装完成' });

        const summary = el.createEl('div', { cls: 'paperforge-summary' });
        summary.createEl('div', { cls: 'paperforge-summary-title', text: '当前完整配置' });

        const s = this.plugin.settings;
        const vault = this.app.vault.adapter.basePath;
        const items = [
            { label: 'Vault 路径', val: vault, icon: '📁' },
            { label: '资源目录', val: `${vault}/${s.resources_dir}`, icon: '📂' },
            { label: '正文目录', val: `${vault}/${s.resources_dir}/${s.literature_dir}`, icon: '📄' },
            { label: '索引目录', val: `${vault}/${s.resources_dir}/${s.control_dir}`, icon: '📄' },
            { label: 'Base 目录', val: `${vault}/${s.base_dir}`, icon: '📂' },
            { label: '系统目录', val: `${vault}/${s.system_dir}`, icon: '⚙' },
            { label: 'API Key', val: s.paddleocr_api_key ? '已配置 ✓' : '未配置 ✗', icon: '🔑' },
            { label: 'Zotero 数据', val: s.zotero_data_dir || '未设置', icon: '🔗' },
        ];
        for (const item of items) {
            const row = summary.createEl('div', { cls: 'paperforge-summary-row' });
            row.createEl('span', { cls: 'paperforge-summary-icon', text: item.icon });
            row.createEl('span', { cls: 'paperforge-summary-label', text: item.label });
            row.createEl('span', { cls: 'paperforge-summary-value', text: item.val });
        }

        /* Next steps */
        el.createEl('h3', { text: '下一步操作' });
        const nextList = el.createEl('div', { cls: 'paperforge-nextsteps' });
        const steps = [
            ['打开 PaperForge Dashboard', '按 Ctrl+P 打开命令面板，输入 "PaperForge: Open Dashboard" 并回车；或点击左侧边栏的书本图标 (📖) 直接打开'],
            ['同步文献', '在 Dashboard 面板中点击 "Sync Library" 按钮，即可从 Zotero 拉取文献并生成笔记'],
            ['运行 OCR', '在 Dashboard 中点击 "Run OCR" 按钮，提取 PDF 全文和图表'],
            ['配置 Better BibTeX 自动导出', 'Zotero → 编辑 → 首选项 → Better BibTeX → 勾选 "Keep updated"，导出路径设置为：'],
            ['', `${vault}/${s.system_dir}/PaperForge/exports/library.json`],
        ];
        for (const [title, desc] of steps) {
            const item = nextList.createEl('div', { cls: 'paperforge-nextstep-item' });
            if (title) item.createEl('strong', { text: title });
            item.createEl('span', { text: desc });
        }
    }
}

module.exports = class PaperForgePlugin extends Plugin {
    async onload() {
        await this.loadSettings();
        T = (detectLang() === 'zh') ? LANG.zh : LANG.en;
        this.registerView(VIEW_TYPE_PAPERFORGE, (leaf) => new PaperForgeStatusView(leaf));

        this.addRibbonIcon('book-open', 'PaperForge Dashboard', () => PaperForgeStatusView.open(this));

        this.addSettingTab(new PaperForgeSettingTab(this.app, this));

        this.addCommand({
            id: 'paperforge-status-panel',
            name: 'PaperForge: Open Dashboard',
            callback: () => PaperForgeStatusView.open(this),
        });

        for (const a of ACTIONS) {
            this.addCommand({
                id: a.id,
                name: `PaperForge: ${a.title}`,
                callback: () => {
                    const vp = this.app.vault.adapter.basePath;
                    new Notice(`PaperForge: running ${a.cmd}...`);
                    exec(`python -m paperforge ${a.cmd}`, { cwd: vp, timeout: 300000 }, (err, stdout, stderr) => {
                        if (err) {
                            new Notice(`[!!] ${a.cmd} failed: ${(stderr || err.message).slice(0, 120)}`, 8000);
                            return;
                        }
                        new Notice(`[OK] ${a.okMsg || stdout.trim().split('\n')[0].slice(0, 80)}`);
                    });
                },
            });
        }

        /* ── Auto-update PaperForge (non-blocking) ── */
        if (this.settings.auto_update !== false) {
            this._autoUpdate();
        }
    }

    _autoUpdate() {
        const vp = this.app.vault.adapter.basePath;
        exec('python -m paperforge update', { cwd: vp, timeout: 60000 }, (err, stdout) => {
            if (err) return;
            const result = stdout.trim();
            if (result.includes('already up to date') || result.includes('already up-to-date')) return;
            const firstLine = result.split('\n')[0].slice(0, 80);
            new Notice(`[OK] PaperForge 已更新: ${firstLine}`, 6000);
        });
    }

    onunload() {
        this.app.workspace.detachLeavesOfType(VIEW_TYPE_PAPERFORGE);
    }

    async loadSettings() {
        this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
    }

    async saveSettings() {
        await this.saveData(this.settings);
    }
};
