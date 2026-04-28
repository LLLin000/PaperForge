const { Plugin, Notice } = require('obsidian');
const { exec } = require('child_process');

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
    {
        id: 'paperforge-status',
        name: 'PaperForge: 查看系统状态',
        cmd: 'status',
        okMsg: null,
    },
];

module.exports = class PaperForgePlugin extends Plugin {
    async onload() {
        for (const c of COMMANDS) {
            this.addCommand({
                id: c.id,
                name: c.name,
                callback: () => this._run(c.cmd, c.okMsg),
            });
        }
    }

    _run(subcommand, okMsg) {
        const vaultPath = this.app.vault.adapter.basePath;
        const cmd = `python -m paperforge ${subcommand}`;

        new Notice(`PaperForge: running ${subcommand}...`);

        exec(cmd, { cwd: vaultPath, timeout: 300000 }, (err, stdout, stderr) => {
            if (err) {
                const msg = stderr
                    ? stderr.split('\n').filter(Boolean).slice(-2).join(' | ')
                    : err.message;
                new Notice(`[!!] PaperForge ${subcommand} failed: ${msg}`, 8000);
                return;
            }
            if (okMsg) {
                new Notice(`[OK] ${okMsg}`);
            } else {
                const firstLine = stdout.trim().split('\n')[0] || '';
                new Notice(`[OK] ${firstLine.slice(0, 80)}`);
            }
        });
    }
};
