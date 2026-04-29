const { Plugin, Notice, ItemView } = require('obsidian');
const { exec } = require('node:child_process');

const VIEW_TYPE_PAPERFORGE = 'paperforge-status';

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
        new Notice(`PaperForge: running ${a.cmd}...`);
        exec(`python -m paperforge ${a.cmd}`, { cwd: vp, timeout: 300000 }, (err, stdout, stderr) => {
            card.removeClass('running');
            if (err) {
                const msg = stderr ? stderr.split('\n').filter(Boolean).slice(-2).join(' | ') : err.message;
                new Notice(`[!!] ${a.cmd} failed: ${msg}`, 8000);
                return;
            }
            new Notice(`[OK] ${a.okMsg || stdout.trim().split('\n')[0].slice(0, 80)}`);
            this._fetchStats();
        });
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

        containerEl.createEl('h3', { text: '基础路径' });

        this._addTextSetting('vault_path', 'Vault 路径', '你的 Obsidian Vault 所在目录', '输入 Vault 完整路径...');
        this._addTextSetting('system_dir', '系统目录', '内部系统文件目录（默认 99_System）');
        this._addTextSetting('resources_dir', '资源目录', '管理资源文件目录（默认 20_Resources）');
        this._addTextSetting('literature_dir', '文献目录', '文献笔记存放目录（默认 Literature）');
        this._addTextSetting('control_dir', '控制目录', 'Library-records 控制文件目录（默认 Control）');
        this._addTextSetting('agent_config_dir', 'Agent 配置目录', 'Agent 技能目录（默认 .opencode）');

        containerEl.createEl('h3', { text: 'API 密钥' });

        this._addPasswordSetting('paddleocr_api_key', 'PaddleOCR API 密钥', '用于 OCR 文字识别的 API Key');

        containerEl.createEl('h3', { text: 'Zotero 链接' });

        this._addTextSetting('zotero_data_dir', 'Zotero 数据目录', 'Zotero 数据目录路径（可选，用于自动检测 PDF）');

        containerEl.createEl('h3', { text: '安装配置' });

        this._statusArea = containerEl.createEl('div', { cls: 'paperforge-install-status' });
        this._statusArea.setText('填写上方配置后，点击下方按钮一键安装');

        new Setting(containerEl)
            .setName('一键安装')
            .setDesc('根据上方配置写入 PaperForge 配置文件，创建目录结构，检查环境依赖')
            .addButton((button) => {
                button.setButtonText('安装配置')
                    .setCta()
                    .onClick(() => this._runSetup(button));
            });
    }

    _addTextSetting(key, name, desc, placeholder) {
        new Setting(this.containerEl)
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
    }

    _addPasswordSetting(key, name, desc) {
        new Setting(this.containerEl)
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
    }

    _debouncedSave() {
        clearTimeout(this._saveTimeout);
        this._saveTimeout = setTimeout(() => this.plugin.saveSettings(), 500);
    }

    _validate() {
        const errors = [];
        const s = this.plugin.settings;

        if (!s.vault_path || !s.vault_path.trim()) {
            errors.push('Vault 路径未填写，请输入 Obsidian Vault 的完整路径');
        }
        if (!s.system_dir || !s.system_dir.trim()) {
            errors.push('系统目录未填写');
        }
        if (!s.resources_dir || !s.resources_dir.trim()) {
            errors.push('资源目录未填写');
        }
        if (!s.literature_dir || !s.literature_dir.trim()) {
            errors.push('文献目录未填写');
        }
        if (!s.control_dir || !s.control_dir.trim()) {
            errors.push('控制目录未填写');
        }
        if (!s.agent_config_dir || !s.agent_config_dir.trim()) {
            errors.push('Agent 配置目录未填写');
        }
        if (!s.paddleocr_api_key || !s.paddleocr_api_key.trim()) {
            errors.push('PaddleOCR API 密钥未填写，请先获取 API Key');
        }

        return errors;
    }

    async _runSetup(button) {
        const errors = this._validate();
        if (errors.length > 0) {
            this._showNotice('error', '配置验证失败', errors.join('；'));
            return;
        }

        button.setDisabled(true);
        button.setButtonText('正在安装...');
        this._setStatus('正在配置 PaperForge 环境...', 'progress');

        const { spawn } = require('node:child_process');
        const s = this.plugin.settings;

        const args = [
            '-m', 'paperforge', 'setup', '--headless',
            '--vault', s.vault_path.trim(),
            '--paddleocr-key', s.paddleocr_api_key.trim(),
            '--system-dir', s.system_dir.trim(),
            '--resources-dir', s.resources_dir.trim(),
            '--literature-dir', s.literature_dir.trim(),
            '--control-dir', s.control_dir.trim(),
            '--agent', 'opencode',
        ];

        if (s.zotero_data_dir && s.zotero_data_dir.trim()) {
            args.push('--zotero-data', s.zotero_data_dir.trim());
        }

        try {
            const result = await new Promise((resolve, reject) => {
                const child = spawn('python', args, {
                    cwd: s.vault_path.trim(),
                    env: process.env,
                    timeout: 120000,
                });

                let stdout = '';
                let stderr = '';

                child.stdout.on('data', (data) => {
                    const text = data.toString('utf-8');
                    stdout += text;
                    this._processSetupOutput(text);
                });

                child.stderr.on('data', (data) => {
                    stderr += data.toString('utf-8');
                });

                child.on('close', (code) => {
                    if (code === 0) {
                        resolve({ stdout, stderr });
                    } else {
                        reject(new Error(stderr || `exit code ${code}`));
                    }
                });

                child.on('error', (err) => {
                    reject(err);
                });
            });

            this._showNotice('success', '配置完成', 'PaperForge 安装配置已完成！现可运行同步和 OCR 命令。');
            this._setStatus('配置完成！', 'success');
        } catch (err) {
            console.error('PaperForge setup failed:', err.message);
            this._showNotice('error', '配置失败', this._formatSetupError(err.message));
            this._setStatus('配置失败，请检查设置后重试', 'error');
        } finally {
            button.setDisabled(false);
            button.setButtonText('安装配置');
        }
    }

    _showNotice(type, title, detail) {
        const prefix = { success: '[OK]', error: '[!!]', progress: '[...]' };
        const duration = type === 'error' ? 8000 : 4000;
        new Notice(`${prefix[type] || ''} ${title}\n${detail}`, duration);
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

    _processSetupOutput(text) {
        const lines = text.split('\n').filter(Boolean);
        for (const line of lines) {
            if (line.includes('[*]') || line.includes('[OK]') || line.includes('[FAIL]')) {
                const clean = line.replace(/^\[\*\].*\d+:?\s*/, '').replace(/^\[OK\]\s*/, '').replace(/^\[FAIL\]\s*/, '');
                this._setStatus(clean, 'progress');
            }
        }
    }

    _setStatus(message, type) {
        if (this._statusArea) {
            this._statusArea.setText(message);
            this._statusArea.className = 'paperforge-install-status';
            if (type) {
                this._statusArea.addClass(`paperforge-install-${type}`);
            }
        }
    }
}

module.exports = class PaperForgePlugin extends Plugin {
    async onload() {
        await this.loadSettings();
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
