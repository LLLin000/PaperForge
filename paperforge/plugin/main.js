const { Plugin, Notice, ItemView } = require('obsidian');
const { exec } = require('node:child_process');

const VIEW_TYPE_PAPERFORGE = 'paperforge-status';

const COMMANDS = [
    { id: 'paperforge-sync', name: 'PaperForge: 同步文献并生成笔记', cmd: 'sync', okMsg: 'Sync complete' },
    { id: 'paperforge-ocr', name: 'PaperForge: 运行 OCR', cmd: 'ocr', okMsg: 'OCR started' },
];

class PaperForgeStatusView extends ItemView {
    constructor(leaf) { super(leaf); }

    getViewType() { return VIEW_TYPE_PAPERFORGE; }
    getDisplayText() { return 'PaperForge'; }
    getIcon() { return 'book-open'; }

    async onOpen() { this._buildPanel(); this._fetchStats(); }
    onClose() {}

    _buildPanel() {
        const root = this.containerEl;
        root.empty();
        root.addClass('paperforge-status-panel');

        root.createEl('div', { cls: 'paperforge-status-header' }, (el) => {
            el.createEl('h3', { text: 'PaperForge' });
            const btn = el.createEl('button', { cls: 'paperforge-status-refresh', text: 'Refresh' });
            btn.addEventListener('click', () => this._fetchStats());
        });

        this._statsEl = root.createEl('div', { cls: 'paperforge-stats' });
        this._ocrEl = root.createEl('div', { cls: 'paperforge-ocr-section' });
        this._actionsEl = root.createEl('div', { cls: 'paperforge-actions' }, (el) => {
            el.createEl('h4', { text: 'Actions' });
            const bg = el.createEl('div', { cls: 'paperforge-actions-buttons' });
            for (const c of COMMANDS) {
                const b = bg.createEl('button', { cls: 'paperforge-action-btn', text: c.name });
                b.addEventListener('click', () => this._runCmd(c));
            }
        });
    }

    _fetchStats() {
        this._statsEl.empty();
        this._ocrEl.empty();
        this._statsEl.setText('Loading...');

        const vp = this.app.vault.adapter.basePath;
        exec('python -m paperforge status --json', { cwd: vp, timeout: 30000 }, (err, stdout) => {
            this._statsEl.empty();
            if (err) {
                this._statsEl.createEl('div', { text: 'Error connecting to PaperForge', cls: 'paperforge-status-error' });
                return;
            }
            try {
                const d = JSON.parse(stdout);
                this._renderStats(d);
                this._renderOcr(d);
            } catch {
                this._statsEl.createEl('div', { text: 'Invalid response from paperforge', cls: 'paperforge-status-error' });
            }
        });
    }

    _renderStats(d) {
        const metrics = [
            { label: 'Papers', value: d.total_papers, color: 'var(--color-cyan)' },
            { label: 'Notes', value: d.formal_notes, color: 'var(--color-blue)' },
            { label: 'Exports', value: d.exports, color: 'var(--color-purple)' },
        ];
        const grid = this._statsEl.createEl('div', { cls: 'paperforge-metrics' });
        for (const m of metrics) {
            const card = grid.createEl('div', { cls: 'paperforge-metric-card' });
            card.style.setProperty('--metric-color', m.color);
            card.createEl('div', { cls: 'paperforge-metric-value', text: m.value?.toString() || '—' });
            card.createEl('div', { cls: 'paperforge-metric-label', text: m.label });
        }
    }

    _renderOcr(d) {
        const ocr = d.ocr || {};
        const total = ocr.total || 0;
        const done = ocr.done || 0;
        const pending = ocr.pending || 0;
        const failed = ocr.failed || 0;
        const pct = total > 0 ? Math.round(done / total * 100) : 0;

        const section = this._ocrEl;
        section.createEl('h4', { text: 'OCR Progress' });

        const bar = section.createEl('div', { cls: 'paperforge-progress-bar' });
        bar.createEl('div', { cls: 'paperforge-progress-fill', attr: { style: `width:${pct}%` } });
        bar.createEl('span', { cls: 'paperforge-progress-label', text: `${done}/${total} (${pct}%)` });

        const detail = section.createEl('div', { cls: 'paperforge-progress-detail' });
        if (pending > 0) {
            detail.createEl('div', { cls: 'paperforge-progress-row' }, (el) => {
                el.createEl('span', { text: 'Processing', cls: 'paperforge-progress-row-label' });
                el.createEl('span', { text: pending.toString(), cls: 'paperforge-progress-row-value' });
            });
        }
        if (failed > 0) {
            detail.createEl('div', { cls: 'paperforge-progress-row' }, (el) => {
                el.createEl('span', { text: 'Failed', cls: 'paperforge-progress-row-label' });
                el.createEl('span', { text: failed.toString(), cls: 'paperforge-progress-row-value paperforge-progress-row-failed' });
            });
        }
    }

    _runCmd(c) {
        const vp = this.app.vault.adapter.basePath;
        new Notice(`PaperForge: running ${c.cmd}...`);
        exec(`python -m paperforge ${c.cmd}`, { cwd: vp, timeout: 300000 }, (err, stdout, stderr) => {
            if (err) {
                const msg = stderr ? stderr.split('\n').filter(Boolean).slice(-2).join(' | ') : err.message;
                new Notice(`[!!] ${c.cmd} failed: ${msg}`, 8000);
                return;
            }
            new Notice(`[OK] ${c.okMsg || stdout.trim().split('\n')[0].slice(0, 80)}`);
            this._fetchStats();
        });
    }

    static async open(plugin) {
        const leaves = plugin.app.workspace.getLeavesOfType(VIEW_TYPE_PAPERFORGE);
        if (leaves.length > 0) { plugin.app.workspace.revealLeaf(leaves[0]); return; }
        const leaf = plugin.app.workspace.getRightLeaf(false);
        if (leaf) { await leaf.setViewState({ type: VIEW_TYPE_PAPERFORGE, active: true }); plugin.app.workspace.revealLeaf(leaf); }
    }
}

module.exports = class PaperForgePlugin extends Plugin {
    async onload() {
        this.registerView(VIEW_TYPE_PAPERFORGE, (leaf) => new PaperForgeStatusView(leaf));
        this.addRibbonIcon('book-open', 'PaperForge Status', () => PaperForgeStatusView.open(this));
        this.addCommand({ id: 'paperforge-status-panel', name: 'PaperForge: 打开状态面板', callback: () => PaperForgeStatusView.open(this) });
        for (const c of COMMANDS) {
            this.addCommand({
                id: c.id, name: c.name,
                callback: () => {
                    const vp = this.app.vault.adapter.basePath;
                    new Notice(`PaperForge: running ${c.cmd}...`);
                    exec(`python -m paperforge ${c.cmd}`, { cwd: vp, timeout: 300000 }, (err, stdout, stderr) => {
                        if (err) { new Notice(`[!!] ${c.cmd} failed: ${(stderr || err.message).slice(0, 120)}`, 8000); return; }
                        new Notice(`[OK] ${c.okMsg || stdout.trim().split('\n')[0].slice(0, 80)}`);
                    });
                },
            });
        }
    }

    onunload() { this.app.workspace.detachLeavesOfType(VIEW_TYPE_PAPERFORGE); }
};