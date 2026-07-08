# Embed Background Progress + Pause

> **For agentic workers:** Use subagent-driven-development.

**Goal:** Embed build runs in background via plugin UI, with progress bar and pause/resume.

**Architecture:** Plugin spawns embed as a persistent child process, parses per-paper progress from stdout, renders progress bar in Features tab, supports kill-and-resume via `--resume` flag.

**Tech Stack:** Python subprocess, Obsidian Plugin API, ChromaDB

---

## Task 1: Add per-paper progress to embed.py

**Files:**
- Modify: `paperforge/commands/embed.py`

**Goal:** Output a progress line for each paper so the plugin can parse it.

- [ ] **Step 1: Add progress print**

In the embed loop, add a print line before embedding each paper:

```python
# After chunk_fulltext, before embed_paper:
print(f"EMBED_PROGRESS:{i+1}:{total}:{key}", flush=True)
```

Where `i` is loop counter, `total` is `len(done_papers)`.

Also add initial line:
```python
total = len(done_papers)
print(f"EMBED_START:{total}", flush=True)
```

And final line:
```python
print("EMBED_DONE", flush=True)
```

All lines are plain text to stdout, format `EMBED_<type>:<arg1>:<arg2>:...`.

- [ ] **Step 2: Commit**

```bash
git add paperforge/commands/embed.py
git commit -m "feat: add structured progress output for embed build"
```

---

## Task 2: Background embed in plugin settings

**Files:**
- Modify: `paperforge/plugin/main.js` (`_renderVectorSection`)

**Goal:** "Build Index" button spawns embed in background, shows progress, supports stop.

- [ ] **Step 1: Add state variables**

In `PaperForgeSettingTab` constructor, add:
```javascript
this._embedProcess = null;        // child process
this._embedProgress = { current: 0, total: 0, key: '' };
this._embedUiInterval = null;     // UI refresh timer
```

- [ ] **Step 2: Replace current install/status buttons with Build/Stop**

In `_renderVectorSection`, when deps are installed and feature is enabled, show:

```
[Build Index]  [Stop]
Progress: ████████░░░░ 342/655 papers  (Current: ABC12345)
```

- [ ] **Step 3: Build button handler**

```javascript
const buildBtn = ...;
buildBtn.addEventListener('click', () => {
    const vp = this.app.vault.adapter.basePath;
    const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(vp, this.plugin.settings);
    const args = [...extraArgs, '-m', 'paperforge', 'embed', 'build', '--resume'];
    
    this._embedProcess = spawn(pythonExe, args, { cwd: vp });
    this._embedProgress = { current: 0, total: 0, key: '' };
    
    // Parse stdout for progress
    this._embedProcess.stdout.on('data', (data) => {
        const lines = data.toString('utf-8').split('\n');
        for (const line of lines) {
            if (line.startsWith('EMBED_START:')) {
                this._embedProgress.total = parseInt(line.split(':')[1]);
            } else if (line.startsWith('EMBED_PROGRESS:')) {
                const parts = line.split(':');
                this._embedProgress.current = parseInt(parts[1]);
                this._embedProgress.key = parts[3];
            } else if (line.startsWith('EMBED_DONE')) {
                this._embedProcess = null;
                this._embedProgress.current = this._embedProgress.total;
            }
        }
        this.display(); // refresh UI
    });
    
    this._embedProcess.on('close', () => {
        this._embedProcess = null;
        this._embedProgress.current = this._embedProgress.total;
        this._embedStatusText = null;
        this.display();
    });
    
    this.display();
});
```

- [ ] **Step 4: Stop button handler**

```javascript
stopBtn.addEventListener('click', () => {
    if (this._embedProcess) {
        this._embedProcess.kill('SIGTERM');
        this._embedProcess = null;
        this.display();
    }
});
```

- [ ] **Step 5: Progress bar rendering**

```javascript
_renderEmbedProgress(containerEl) {
    if (!this._embedProcess && this._embedProgress.total === 0) return;
    
    const { current, total, key } = this._embedProgress;
    const pct = total > 0 ? Math.round(current / total * 100) : 0;
    const bar = containerEl.createEl('div', { cls: 'paperforge-progress-track' });
    bar.createEl('div', {
        cls: 'paperforge-progress-seg active',
        attr: { style: `width:${pct}%` }
    });
    containerEl.createEl('div', {
        cls: 'paperforge-embed-progress-text',
        text: `${current}/${total} papers${key ? ` (${key})` : ''}`
    });
}
```

- [ ] **Step 6: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/styles.css
git commit -m "feat: background embed build with progress bar and stop button"
```

---

## Task 3: CSS for progress bar

**Files:**
- Modify: `paperforge/plugin/styles.css`

**Goal:** Add styles for embed progress bar.

```css
.paperforge-embed-progress-text {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 4px;
    text-align: center;
}
```

---

## Summary

| Task | Files | What |
|------|-------|------|
| 1 | embed.py | Structured progress lines (EMBED_START/PROGRESS/DONE) |
| 2 | main.js | Background spawn + progress bar + stop button |
| 3 | styles.css | Progress text styling |
