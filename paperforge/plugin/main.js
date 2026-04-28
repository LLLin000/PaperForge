const { Plugin, Notice, ItemView } = require('obsidian');
const { exec } = require('node:child_process');

const VIEW_TYPE_PAPERFORGE = 'paperforge-status';

const COMMANDS = [
    {
        id: 'paperforge-sync',
        name: 'PaperForge: 同步文献并生成笔记',
        cmd: 'sync',
        okMsg: 'Sync complete',
    },
    {
        id: 'paperforge-ocr',
        name: 'PaperForge: 运行 OCR',
        cmd: 'ocr',
        okMsg: 'OCR started — check status for completion',
    },
];

class PaperForgeStatusView extends ItemView {
    constructor(leaf) {
        super(leaf);
    }

    getViewType() { return VIEW_TYPE_PAPERFORGE; }
    getDisplayText() { return 'PaperForge'; }
    getIcon() { return 'book-open'; }

    async onOpen() {
        this._buildPanel();
        this._fetchStats();
    }

    onClose() {}

    _buildPanel() {
        const root = this.containerEl;
        root.empty();
        root.addClass('paperforge-status-panel');

        root.createEl('div', { cls: 'paperforge-status-header' }, (el) => {
            el.createEl('h3', { text: 'PaperForge' });
            const refreshBtn = el.createEl('button', {
                cls: 'paperforge-status-refresh',
                text: 'Refresh',
            });
            refreshBtn.addEventListener('click', () => this._fetchStats());
        });

        this._metricsEl = root.createEl('div', { cls: 'paperforge-metrics' });
        this._actionsEl = root.createEl('div', { cls: 'paperforge-actions' }, (el) => {
            el.createEl('h4', { text: 'Quick Actions' });
            const btnGrp = el.createEl('div', { cls: 'paperforge-actions-buttons' });
            for (const c of COMMANDS) {
                const btn = btnGrp.createEl('button', {
                    cls: 'paperforge-action-btn',
                    text: c.name,
                });
                btn.addEventListener('click', () => this._runCommand(c));
            }
        });
    }

    _fetchStats() {
        this._metricsEl.empty();
        this._metricsEl.createEl('div', {
            text: 'Loading...',
            cls: 'paperforge-status-loading',
        });

        const vaultPath = this.app.vault.adapter.basePath;
        exec('python -m paperforge status', { cwd: vaultPath, timeout: 30000 }, (err, stdout) => {
            this._metricsEl.empty();
            if (err) {
                this._metricsEl.createEl('div', {
                    text: 'Error connecting to PaperForge. Is it installed?',
                    cls: 'paperforge-status-error',
                });
                return;
            }
            this._renderMetrics(stdout);
        });
    }

    _renderMetrics(statusText) {
        const lines = statusText.split('\n').filter(Boolean);
        const stats = {};

        for (const line of lines) {
            const m = line.match(/^\S+/);
            if (!m) continue;
            const key = m[0].toLowerCase();
            stats.total = stats.total || 0;
            if (key === 'found') {
                const n = parseInt(line.match(/\d+/)?.[0] || '0');
                stats.total += n;
            }
        }

        const metrics = [
            { label: 'Papers', value: stats.total || '—', color: 'var(--color-cyan)' },
        ];

        for (const metric of metrics) {
            const card = this._metricsEl.createEl('div', { cls: 'paperforge-metric-card' });
            card.createEl('div', { text: metric.value.toString(), cls: 'paperforge-metric-value' });
            card.createEl('div', { text: metric.label, cls: 'paperforge-metric-label' });
            if (metric.color) {
                card.style.setProperty('--metric-color', metric.color);
            }
        }
    }

    _runCommand(c) {
        const vaultPath = this.app.vault.adapter.basePath;
        new Notice(`PaperForge: running ${c.cmd}...`);
        exec(`python -m paperforge ${c.cmd}`, { cwd: vaultPath, timeout: 300000 }, (err, stdout, stderr) => {
            if (err) {
                const msg = stderr
                    ? stderr.split('\n').filter(Boolean).slice(-2).join(' | ')
                    : err.message;
                new Notice(`[!!] ${c.cmd} failed: ${msg}`, 8000);
                return;
            }
            new Notice(`[OK] ${c.okMsg || stdout.trim().split('\n')[0].slice(0, 80)}`);
            this._fetchStats();
        });
    }

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

module.exports = class PaperForgePlugin extends Plugin {
    async onload() {
        this.registerView(VIEW_TYPE_PAPERFORGE, (leaf) => new PaperForgeStatusView(leaf));

        this.addRibbonIcon('book-open', 'PaperForge Status', () => {
            PaperForgeStatusView.open(this);
        });

        this.addCommand({
            id: 'paperforge-status-panel',
            name: 'PaperForge: 打开状态面板',
            callback: () => PaperForgeStatusView.open(this),
        });

        for (const c of COMMANDS) {
            this.addCommand({
                id: c.id,
                name: c.name,
                callback: () => {
                    const vaultPath = this.app.vault.adapter.basePath;
                    new Notice(`PaperForge: running ${c.cmd}...`);
                    exec(`python -m paperforge ${c.cmd}`, { cwd: vaultPath, timeout: 300000 }, (err, stdout, stderr) => {
                        if (err) {
                            const msg = stderr ? stderr.split('\n').filter(Boolean).slice(-2).join(' | ') : err.message;
                            new Notice(`[!!] ${c.cmd} failed: ${msg}`, 8000);
                            return;
                        }
                        new Notice(`[OK] ${c.okMsg || stdout.trim().split('\n')[0].slice(0, 80)}`);
                    });
                },
            });
        }
    }

    onunload() {
        this.app.workspace.detachLeavesOfType(VIEW_TYPE_PAPERFORGE);
    }
};