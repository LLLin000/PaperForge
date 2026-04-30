# Pitfalls Research

**Domain:** Obsidian Plugin Settings Tab (Retrofit to Existing CommonJS Plugin)
**Researched:** 2026-04-29
**Confidence:** HIGH

> Source material: Official Obsidian API type definitions (`obsidian.d.ts`, v1.12+), existing PaperForge `main.js` (CommonJS, sidebar + ribbon + commands, zero settings), Obsidian `Setting` / `PluginSettingTab` / `Plugin.loadData/saveData` APIs, `Notice` / `ButtonComponent` / `exec` from `node:child_process`.

---

## Critical Pitfalls

### Pitfall 1: `loadData()` / `saveData()` Data Corruption Due to Timing and Partial Writes

**What goes wrong:**
Calling `this.saveData(this.settings)` inside an `onChange` handler fires on every keystroke. Each keystroke triggers a full `data.json` write (file overwrite). On slow filesystems or with rapid typing, the Obsidian Sync service may pick up intermediate partial writes, or two sequential writes may collide. The result: truncated or corrupted `data.json`, plugin settings reset to defaults on next load.

**Why it happens:**
`Plugin.saveData()` writes to `data.json` in `{vault}/.obsidian/plugins/paperforge/` synchronously from the caller's perspective (it returns a Promise but fires immediately). Obsidian's `Setting.addText(cb => cb.onChange(...))` fires on every `input` event. There is no built-in debounce. Developers naively add `this.saveData()` inside the onChange callback, creating a write-per-keystroke pattern.

**How to avoid:**
- **Debounce saveData**: Wrap `this.saveData()` in a debounce function (250-500ms). Clear it on component unload.
- **Atomic writes**: Obsidian's `saveData` is already atomic (write-to-temp then rename), but debouncing still prevents rapid-fire writes.
- **Schema versioning**: Always include `version: 2` in settings. On `loadData()`, check `settings.version` and run migration if missing or outdated.

```javascript
// Pattern — debounced save with version guard
let _saveTimeout = null;
const debouncedSave = () => {
    clearTimeout(_saveTimeout);
    _saveTimeout = setTimeout(() => this.saveData(this.settings), 300);
};
// In onunload: clearTimeout(_saveTimeout)
```

**Warning signs:**
- `data.json` shows intermediate/incomplete JSON after typing in a text field
- User reports "my settings reset" after Obsidian restart
- Obsidian Sync shows "conflict" on `data.json`

**Phase to address:**
Phase 1 (Settings tab shell + persistence layer). Build debounced save + versioning before ANY settings controls.

---

### Pitfall 2: Settings Tab `display()` Breaking the Existing Sidebar View

**What goes wrong:**
The existing plugin has a `PaperForgeStatusView` (sidebar `ItemView`). Adding a `PluginSettingTab` that mutates global state, overrides `this.app.workspace` internals, or triggers workspace layout changes will break the existing sidebar. Specifically: if the settings tab code uses `this.app.workspace.getLeaf()` or triggers a workspace layout save/restore, it can steal focus from the sidebar, close the sidebar pane, or cause layout jank.

**Why it happens:**
`PluginSettingTab` extends `SettingTab` which has a `display()` method called whenever the user switches to the settings tab. This method is called **fresh each time** — the `containerEl` is reused but emptied each time the tab gains focus. If `display()` opens/closes leaves, registers views, or calls `workspace.revealLeaf()`, it disrupts the workspace layout that the sidebar view depends on.

**How to avoid:**
- **Settings tab is self-contained**: Only mutate `this.containerEl` in `display()`. Never touch `this.app.workspace` from settings.
- **Never register views in `display()`**: View registration (`registerView`) belongs in `onload()`, not in settings display.
- **Do not call `PaperForgeStatusView.open()` from settings**: The settings tab should not trigger sidebar actions.
- **Settings actions that need refresh**: Use `Notice` to tell user "Restart required" or "Click Refresh in sidebar" rather than programmatically opening views.

**Warning signs:**
- Sidebar closes/disappears when switching to Settings tab
- "PaperForge Dashboard" ribbon icon stops working after visiting settings
- Workspace layout resets to default after opening settings

**Phase to address:**
Phase 1 (Settings tab shell). Day 1 test: open sidebar, open settings, verify sidebar still visible and functional.

---

### Pitfall 3: `exec` Blocking the Obsidian UI Thread During Long Subprocesses

**What goes wrong:**
The existing plugin uses `exec('python -m paperforge ...', { cwd, timeout }, callback)`. While `exec` itself is async-callback (non-blocking), a settings "Setup Wizard" button that runs `paperforge doctor` or `paperforge sync --setup` can take 10-60 seconds. The user sees a frozen settings tab with no progress indicator. Worse: if the callback throws and isn't caught, the plugin crashes silently. If the timeout fires, the child process may become a zombie (orphaned Python process keeping file handles open).

**Why it happens:**
`exec` buffers all stdout/stderr in memory and delivers them once the process exits. There is no streaming feedback to the settings UI. The `ButtonComponent.onClick(callback)` pattern passes an async callback — but `exec`'s callback-based API doesn't integrate with async/await naturally. The result: the button looks "stuck" with no visual feedback for 10-60 seconds.

**How to avoid:**
- **Use `execFile` or `spawn` for streaming**: `spawn` provides `stdout.on('data')` for live progress. Pipe it to a progress display in the settings tab.
- **Button state management**: Immediately disable the button (`.setDisabled(true)` + `.setButtonText('Running...')`) after click. Re-enable in callback.
- **Wrap exec in Promise with proper cleanup**:
```javascript
const runCommand = (cmd, args, cwd, timeoutMs) => new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { cwd, timeout: timeoutMs, shell: true });
    let stdout = '', stderr = '';
    child.stdout.on('data', d => stdout += d);
    child.stderr.on('data', d => stderr += d);
    child.on('close', code => {
        if (code === 0) resolve(stdout);
        else reject(new Error(stderr || `Exit code ${code}`));
    });
    child.on('error', reject);
});
```
- **Show incremental progress**: For long commands, use `--verbose` or `--progress` flags on the Python side and parse streaming output for progress updates.
- **Timeout + cleanup**: Explicitly `child.kill('SIGTERM')` on timeout. Do not rely solely on the `timeout` option (which can fail on Windows).

**Warning signs:**
- Clicking "Run Setup" freezes Obsidian for 20+ seconds
- Multiple "Run" clicks spawn multiple subprocesses (because button wasn't disabled)
- Zombie Python processes after Obsidian close (check Task Manager)
- Settings tab becomes unresponsive with no loading indicator

**Phase to address:**
Phase 2 (Setup wizard controls). This is where subprocess UX matters most.

---

### Pitfall 4: Windows Path Encoding — `basePath` with Spaces and Unicode in `exec` cwd

**What goes wrong:**
The existing code uses `this.app.vault.adapter.basePath` as `cwd` for `exec`. On Windows, `basePath` returns a native path like `C:\Users\Lin\My Vault` (with spaces) or `D:\L\Med\Research\99_System\LiteraturePipeline` (with non-ASCII-like directory names). When passed to `exec('python -m paperforge ...', { cwd: basePath })`, the Windows command interpreter may fail to parse the path due to spaces, or the Python process may mishandle Unicode in working directory paths.

Additionally, `basePath` may have different case than the actual filesystem path (Windows is case-insensitive but Node's `path` comparisons are case-sensitive). If any code does `pathA === pathB` comparisons, it will fail.

**Why it happens:**
- `exec` uses `cmd.exe` on Windows for `shell: true` (default). Spaces in paths require quoting.
- `basePath` is a native OS path. Inside Obsidian's Electron runtime, this is fine for Vault API calls. But passing it directly to a Python subprocess as `cwd` may expose encoding mismatches (Electron's `basePath` may be UTF-16 on Windows while Python expects UTF-8 or system locale encoding).
- `path.sep` on Windows is `\`, but the vault adapter uses `/` internally. Mixed separators in path construction can cause "file not found" errors.

**How to avoid:**
- **Quote the cwd**: `{ cwd: basePath }` is fine — Node's `child_process` handles quoting internally. But verify by testing with a path like `C:\Users\Test User\My Vault`.
- **Normalize paths before using in Python commands**: Use `path.normalize()` for any path argument passed as a CLI argument, and wrap in double quotes.
- **Test with a vault path containing**: spaces, Chinese characters, em-dashes, and trailing spaces.
- **`spawn` over `exec`**: `spawn` accepts an explicit `cwd` option with proper quoting. It's safer for Windows subprocess handling because it doesn't go through `cmd.exe` by default (though `shell: true` restores cmd.exe behavior).
- **Path arguments passed to Python**: Always wrap in double quotes: `python -m paperforge status --vault "C:\My Vault\"`

**Warning signs:**
- `exec` returns "The system cannot find the path specified" despite path existing
- Works on one Windows machine but fails on another (encoding/locale difference)
- Python process starts but can't find vault files (wrong working directory)
- Error: `'C:\Users\Lin' is not recognized as an internal or external command` (space in path not quoted)

**Phase to address:**
Phase 2 (Setup wizard / path configuration). Must test on a vault with spaces and Unicode in path.

---

### Pitfall 5: Raw stderr Dumped Into `Notice` — User-Unfriendly Output

**What goes wrong:**
The existing plugin code does:
```javascript
new Notice(`[!!] ${a.cmd} failed: ${(stderr || err.message).slice(0, 120)}`, 8000);
```
This shows raw Python tracebacks, CLI errors, or JSON blobs in the Obsidian notification. The user sees technical gobbledygook like `[!!] sync failed: Traceback (most recent call last):\n  File "paperforge", line 12, in <module>\nModuleNotFoundError: No module named 'paperforge'`.

**Why it happens:**
`exec` delivers unfiltered stderr. The naive approach is to show it directly. Python's tracebacks are multi-line, include absolute paths, and are not user-actionable for non-technical users.

**How to avoid:**
- **Parse stderr for known error patterns, return user-friendly messages**:
```javascript
const parseError = (stderr) => {
    if (stderr.includes('ModuleNotFoundError')) 
        return 'PaperForge is not installed. Open Settings and run the Setup Wizard.';
    if (stderr.includes('FileNotFoundError') && stderr.includes('library.json'))
        return 'No Zotero export found. Check that Better BibTeX is configured.';
    if (stderr.includes('ConnectionError') || stderr.includes('timeout'))
        return 'Cannot reach PaddleOCR API. Check your internet connection and API key.';
    // Fallback: show first line only, stripped of path info
    const firstLine = stderr.split('\n').find(l => l.trim() && !l.includes('File "'));
    return `Error: ${firstLine || 'Unknown error'}. See console for details.`;
};
```
- **Log full stderr to console**: `console.error('[PaperForge]', stderr)` so developers can still access the raw error.
- **Use `Notice` duration**: Short messages 4000ms, errors 8000ms, success 3000ms.
- **Never show `[!!]` or `[OK]` in user-facing notices**: These are terminal artifacts.
- **Use Obsidian's `createFragment` for rich notices**: `new Notice(createFragment(frag => frag.createEl('b', { text: 'Setup Complete' })))`.

**Warning signs:**
- Notices show full Python tracebacks
- Error messages contain absolute file paths from the developer's machine
- User reports "I got an error but I don't understand what to do"

**Phase to address:**
Phase 2 (Setup wizard error handling). All subprocess calls from settings must produce polished notices.

---

### Pitfall 6: Form State Loss on Tab Switch — `display()` is Called Fresh, Rebuilding Destroys Unsaved Changes

**What goes wrong:**
`SettingTab.display()` is called **every time the user switches to the settings tab**. If `display()` rebuilds the entire form from `this.settings`, any unsaved changes in text fields are lost when the user switches to another tab and comes back. Worse: if the user typed something invalid, the validation state is lost and the field resets to the last saved value.

**Why it happens:**
`SettingTab.hide()` is called when user switches away. `display()` is called when they return. The `containerEl` is managed by Obsidian's settings system — it gets emptied or hidden. The standard pattern is `display()` reads from `plugin.settings` and rebuilds the UI. But if the user typed a new value and hasn't triggered `saveData()` yet (debounce hasn't fired), the in-memory `this.settings` may or may not be up to date depending on whether `onChange` updated it synchronously.

**How to avoid:**
- **Update `this.settings` immediately on change, debounce only the `saveData()` call**:
```javascript
new Setting(containerEl)
    .addText(cb => cb
        .setValue(this.plugin.settings.someKey)
        .onChange(value => {
            this.plugin.settings.someKey = value;  // immediate in-memory update
            this.debouncedSave();                    // debounced disk write
        }));
```
- **Do NOT read from DOM on save**: Always read from `this.plugin.settings` when saving, not from `component.getValue()`.
- **Clean up in `hide()`**: If you have validation state, persist it before hiding. Obsidian calls `hide()` before removing the tab content.
- **Never reset the form from `display()` without checking if unsaved changes exist**.

**Warning signs:**
- User types a value, switches to "Appearance" tab, comes back — field is empty again
- Validation errors disappear when switching tabs (they shouldn't)
- Settings file shows old value despite user seeing new value in the field

**Phase to address:**
Phase 1 (Settings persistence). This is fundamental to the `PluginSettingTab` lifecycle.

---

### Pitfall 7: `data.json` Missing Keys Crash on First Load (No Migration Path)

**What goes wrong:**
On first load (or after adding a new setting field), `loadData()` returns `null` or `{}`. If the code does `this.settings = await this.loadData()` and then accesses `this.settings.someNewKey` without checking existence, it gets `undefined`. If the code later does `this.settings.someNewKey.toLowerCase()` or similar, it throws a TypeError that crashes the plugin silently (no `Notice`, only console error).

**Why it happens:**
`loadData()` returns `null` when `data.json` doesn't exist (first run). Returns `{}` when file exists but is empty. Returns parsed JSON otherwise. Developers forget to handle the `null` and `undefined` cases for newly added settings keys.

**How to avoid:**
- **Always merge with defaults after load**:
```javascript
const DEFAULT_SETTINGS = {
    version: 2,
    resourcesDir: '20_Resources',
    controlDir: '21_Library',
    autoAnalyzeAfterOcr: false,
    pythonPath: 'python',
};
async onload() {
    const data = await this.loadData();
    this.settings = Object.assign({}, DEFAULT_SETTINGS, data || {});
    // Migrate from older versions:
    if (this.settings.version < 2) {
        this.settings.autoAnalyzeAfterOcr = false; // new field
        this.settings.version = 2;
        await this.saveData(this.settings);
    }
}
```
- **Never access `this.settings.X` without default fallback**: Use `this.settings.someKey ?? defaultValue`.
- **Test first-launch scenario**: Delete `data.json`, reload Obsidian, verify settings tab works without crash.

**Warning signs:**
- Plugin silently fails after update (new setting field added without migration)
- `Cannot read property 'toLowerCase' of undefined` in console
- Settings tab blank after first install (data.json missing)

**Phase to address:**
Phase 1 (Settings persistence layer). Write DEFAULT_SETTINGS + merge + migration before any settings controls.

---

### Pitfall 8: Button Double-Click Spawning Multiple Subprocesses

**What goes wrong:**
A "Run Setup" button in settings that uses `onClick` without disabling itself will allow the user to click repeatedly. Each click spawns a new `exec`/`spawn`. Two Python processes now compete for resources, write to the same files, and the second invocation may fail with "file locked" errors.

**Why it happens:**
`ButtonComponent.onClick()` does not auto-disable the button. The developer forgets to add `setDisabled(true)` at the start of the handler and `setDisabled(false)` in the callback. Network latency or slow Python startup means the user sees no immediate feedback and clicks again.

**How to avoid:**
```javascript
new Setting(containerEl)
    .setName('Setup')
    .addButton(btn => btn
        .setButtonText('Run Setup')
        .setCta()
        .onClick(async (evt) => {
            btn.setDisabled(true);
            btn.setButtonText('Running...');
            try {
                const result = await runSetupCommand();
                new Notice('Setup complete. Restart Obsidian to apply.', 5000);
            } catch (e) {
                new Notice(`Setup failed: ${parseError(e.stderr)}`, 8000);
            } finally {
                btn.setDisabled(false);
                btn.setButtonText('Run Setup');
            }
        }));
```
- **Use a guard flag**: `if (this._setupRunning) return; this._setupRunning = true;` for additional safety.
- **Never keep button enabled during async operations**.

**Warning signs:**
- Two "Python" processes in Task Manager
- "File is locked by another process" errors
- User reports "I clicked it twice and it broke"

**Phase to address:**
Phase 2 (Setup wizard). Every action button must disable itself on click.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip `DEFAULT_SETTINGS` merge — assume `loadData()` always returns full object | Saves 3 lines of code | Plugin crashes on first install; every new setting requires migration logic later | Never |
| Hardcode `exec('python ...')` without configurable Python path | Simple, works for most users | Breaks for users with `python3`, conda envs, or pyenv; requires code change + release to fix | Never — make it a setting from day 1 |
| Use `Notice` for all output, including long success messages | Quick to implement | Long messages clip; no way to show structured output (lists, links); no scroll | MVP only if all messages < 80 chars |
| Skip debounce — save on every `onChange` | Works for low setting count | `data.json` write per keystroke; sync conflicts; disk wear on SSDs over years | Never for text inputs (toggle is ok) |
| Use `setTimeout` for debounce without cleanup | Simple | Memory leak; saveData fires after plugin unload; "Cannot read property of undefined" on closed plugin | Never — always store timer handle and clear |
| Store paths as Windows backslash format in settings | "It works on my machine" | Breaks on macOS/Linux; broken wikilinks; path comparisons fail across OS | Never — always store forward-slash paths |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `exec` / `spawn` (Python CLI) | Not quoting `cwd` with spaces on Windows | `spawn` with explicit `{ cwd, shell: true }` — Node handles quoting; test on path with spaces |
| `exec` / `spawn` (Python CLI) | Assuming `python` is the correct binary name | Make Python path a setting (`pythonPath`); default to `python` on Windows, `python3` on macOS/Linux per `process.platform` |
| `exec` / `spawn` (Python CLI) | Using `child_process.exec` which buffers all output (max 1MB) | Use `spawn` for long-running commands (`sync`, `ocr`); use `exec` only for quick commands (`status`, `doctor`) |
| `exec` / `spawn` (Python CLI) | Not handling process.umask or env inheritance | Pass `env: { ...process.env, PYTHONIOENCODING: 'utf-8' }` to force UTF-8 output from Python |
| `Plugin.saveData()` | Calling it outside onload/display contexts where `this.app` may be unavailable | Only call `saveData` in methods with access to `this.app` (settings tab has `this.app` injected); never from standalone functions |
| `Plugin.loadData()` | Not awaiting it | `loadData()` returns `Promise<any>`; must be awaited or `.then()`'d. Synchronous access returns a Promise, not data. |
| Vault adapter `basePath` | Passing it directly to shell commands without sanitization | `basePath` is native OS path; use `path.resolve(basePath)` to normalize, then pass as `cwd` to `spawn` |
| `Notice` message formatting | Using `\n` for multi-line (strips whitespace in Obsidian's notice CSS) | Use `createFragment` for rich text; or keep messages single-line, ~60-80 chars max |
| `Button.onClick` async | Not handling promise rejection | Wrap in try/catch; show Notice on error; always re-enable button in finally block |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Rebuilding entire settings form on every `display()` call | Slow tab switching (500ms+ perceptible lag) when settings tab has 20+ fields | Cache DOM structure; only update values in `display()`, don't recreate; use `Setting.clear()` strategically | 15+ settings fields |
| `saveData()` on every keystroke | Disk I/O spikes; Obsidian Sync uploads; SSDs degrade over years with 100k+ writes/day | Debounce 250-500ms; use `saveLocalStorage` for transient UI state instead of `saveData` | Any text input setting |
| Loading entire `library.json` in settings display | Settings tab freezes for 5+ seconds when Zotero export is large | Never load external data files in settings `display()`; show counts only; use a "View Details" button that opens a separate view | Zotero library > 1000 entries |
| `exec` with 300s timeout for OCR jobs | Settings tab appears frozen; no cancel button; user force-quits Obsidian | Never run long subprocesses from settings UI; dispatch a command that opens the sidebar view with progress tracking instead | Any subprocess > 10 seconds |
| Re-registering event handlers every `display()` call | Memory leak: each tab switch adds new listeners without removing old ones | Use `SettingTab.hide()` to clean up; register events through `this.plugin.registerEvent()` for auto-cleanup on unload | After 10+ tab switches |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing API keys (PaddleOCR) in `data.json` unencrypted | API key readable by any plugin; leaked via Obsidian Sync; exposed in git if vault is versioned | Use `SecretStorage` API (Obsidian v1.11.4+) for API keys: `await this.app.secretStorage.set('paddleocr_key', key)` |
| Passing user-provided paths to `exec` without validation | Command injection if user types `; rm -rf /` or `&& evil_command` in a path setting | Validate paths: `path.resolve(userPath); if (!resolved.startsWith(basePath)) reject;` — use `spawn` with args array, never string interpolation |
| Exposing `data.json` to git via vault versioning | API keys, internal paths, and settings leaked to public repo | Add `.obsidian/plugins/paperforge/data.json` to `.gitignore` (or use SecretStorage for secrets) |
| Running Python subprocess with inherited `PATH` | Malicious `python` binary in PATH earlier than expected; `paperforge` could be a different package | Use absolute path to Python if configured; verify `python -c "import paperforge"` before running commands |
| Settings import/export without validation | Malformed JSON import can crash plugin or execute arbitrary code if eval'd | Validate imported JSON against schema; never `eval()`; use `JSON.parse()` with try/catch; verify all keys match expected schema |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing raw Python errors in Notice | User sees cryptic traceback, doesn't know what action to take | Parse error; map to human-readable message with action hint ("Check your Python installation in Settings > PaperForge") |
| No feedback during long setup operations | User clicks "Run Setup", nothing happens for 30s, assumes plugin is broken | Show "Running..." on button; add a progress bar or spinner; show incremental status messages |
| `Notice` text too long (clips at ~80 chars) | Critical information hidden | Split into multiple short notices or use a modal for detailed output |
| Toggle/checkbox with no immediate save indication | User changes toggle, doesn't know if it's saved | Show brief "Saved" notice after debounce fires; or show a green checkmark icon next to saved settings |
| Settings tab with no "Reset to Defaults" | User makes a mess, can't undo | Add "Reset to Defaults" button per section; confirm with Notice; merge defaults without overwriting API keys |
| Path inputs requiring exact format without browse button | User guesses wrong path format (backslash vs forward slash, trailing slash) | Provide a "Browse" button using Obsidian's file/folder suggest API; auto-normalize path on blur |
| Setup wizard that doesn't check prerequisites | User goes through setup, fails at the end because Python is missing | Check prerequisites FIRST (Python exists, paperforge importable, Zotero configured) before showing the main settings form |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Persistence:** Settings survive Obsidian restart — verify by changing a toggle, restarting, checking it persisted
- [ ] **Persistence:** New setting defaults populate on first load — delete `data.json`, reload, verify all fields show defaults
- [ ] **Validation:** Empty required fields show red error text — test empty Python path, empty resources directory
- [ ] **Validation:** Invalid paths are caught before subprocess runs — test with non-existent path, UNC path, path with `..`
- [ ] **Subprocess:** Button disables during execution — rapid double-click test
- [ ] **Subprocess:** Timeout doesn't orphan the Python process — run a command that hangs, check Task Manager after timeout
- [ ] **Sidebar:** Existing sidebar (PaperForgeStatusView) still works after settings tab added — open sidebar, open settings, switch tabs, verify sidebar still renders
- [ ] **Ribbon:** Ribbon icon still opens sidebar after settings tab added — click ribbon, verify sidebar opens
- [ ] **Commands:** All existing commands (`PaperForge: Sync Library`, `PaperForge: Run OCR`) still work — invoke from command palette
- [ ] **Windows path:** Works with vault path containing spaces and Unicode — test with `C:\Users\Test User\My 测试 Vault\`
- [ ] **Notice quality:** Error messages are user-readable, not raw Python tracebacks — trigger each error case, check Notice text
- [ ] **Unload:** Settings tab closes cleanly when plugin is disabled — disable plugin, verify no errors in console, no orphaned processes
- [ ] **Migration:** Upgrading from v1.4.9 (no settings) to v1.5.0 (with settings) doesn't lose data — install old plugin, add data, upgrade, verify

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Corrupted `data.json` | LOW | Delete `data.json`, reload Obsidian — plugin creates fresh defaults. User reconfigures settings (5 fields max). |
| Orphaned Python subprocess | LOW | Kill via Task Manager (Windows) or `pkill -f paperforge` (macOS/Linux). No data loss — just process leak. |
| Settings tab crashes sidebar | MEDIUM | Disable plugin, restart Obsidian, delete `data.json`, re-enable. Sidebar view is re-registered in `onload()`. |
| `loadData()` returns `null` with no merge | LOW | Add `DEFAULT_SETTINGS` merge in `onload()` — no data lost, just settings reset to defaults on next load. |
| Double-click spawning duplicate subprocess | LOW | Kill extra processes. Add button disable pattern — fix is code-only, no data migration needed. |
| Broken path config (spaces, encoding) | MEDIUM | User edits `data.json` manually to fix path. Or reset settings and reconfigure. Provide a "Repair" button in settings that validates all paths. |
| `saveData` without debounce causing sync conflicts | MEDIUM | Delete `data.json` on all synced devices, reconfigure on one device. Add debounce in next release. |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| #1: loadData/saveData corruption | Phase 1 (Settings shell) | Delete data.json, restart, verify defaults; toggle setting, restart, verify persistence |
| #2: Settings tab breaks sidebar | Phase 1 (Settings shell) | Open sidebar + settings simultaneously, switch tabs, verify sidebar stays open and renders correctly |
| #3: exec blocks UI | Phase 2 (Setup wizard) | Run setup with slow network; verify button shows "Running..." and doesn't freeze Obsidian |
| #4: Windows path encoding | Phase 1 (Settings shell) | Test with vault path: `C:\Users\Test User\My Vault 测试\` |
| #5: Raw stderr in Notice | Phase 2 (Setup wizard) | Trigger Python not found error; verify Notice shows "PaperForge not installed. Open Settings to configure." |
| #6: Form state loss on tab switch | Phase 1 (Settings shell) | Type in text field, switch to Appearance tab, switch back, verify text preserved |
| #7: Missing keys crash on first load | Phase 1 (Settings shell) | Delete data.json (or fresh install), open settings, verify all controls render without console errors |
| #8: Button double-click spawns duplicates | Phase 2 (Setup wizard) | Rapid click "Run Setup" 5 times; verify only 1 Python process in Task Manager |

---

## Sources

- **Official Obsidian API types** (`obsidian.d.ts`, retrieved from `https://raw.githubusercontent.com/obsidianmd/obsidian-api/master/obsidian.d.ts`): Plugin, PluginSettingTab, Setting, SettingTab, Notice, ButtonComponent, TextComponent, DropdownComponent, ToggleComponent, DataAdapter, Vault, Workspace, loadData, saveData, addSettingTab. HIGH confidence.
- **Official Obsidian API docs** (`https://docs.obsidian.md/Reference/TypeScript+API/Plugin/loadData`): Confirms `loadData()` returns `Promise<any>`, data stored in `data.json`. HIGH confidence.
- **Existing PaperForge plugin code** (`paperforge/plugin/main.js`): Confirms CommonJS pattern, `exec` usage, `Notice` patterns, `basePath` usage, sidebar `ItemView`, ribbon icon, commands. HIGH confidence.
- **Node.js `child_process` documentation** (`https://nodejs.org/api/child_process.html`): `exec` vs `spawn` behavior, `shell` option on Windows, timeout behavior, quoting requirements. HIGH confidence.
- **Training data knowledge**: Common Obsidian plugin development patterns, `SettingTab.display()` lifecycle, `hide()` behavior, debounce patterns in Electron apps, Windows path handling in Electron. MEDIUM confidence.

---

*Pitfalls research for: Obsidian Plugin Settings Tab (Retrofit to PaperForge CommonJS Plugin)*
*Researched: 2026-04-29*
