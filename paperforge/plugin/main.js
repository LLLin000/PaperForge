const { Plugin, Notice, ItemView } = require('obsidian');
const { exec } = require('node:child_process');

const VIEW_TYPE_PAPERFORGE = 'paperforge-status';

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

module.exports = class PaperForgePlugin extends Plugin {
    async onload() {
        this.registerView(VIEW_TYPE_PAPERFORGE, (leaf) => new PaperForgeStatusView(leaf));

        this.addRibbonIcon('book-open', 'PaperForge Dashboard', () => PaperForgeStatusView.open(this));

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
};
