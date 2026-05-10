# Phase 51: Runtime Selection & Setup Gate - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can see which Python interpreter PaperForge will use, override it when needed, and complete setup only when the install path is valid. Implementation spans the Obsidian plugin settings tab and the Python-side `resolvePythonExecutable()` function.

**Requirements:** RUNTIME-01, RUNTIME-02, RUNTIME-03, RUNTIME-06

</domain>

<decisions>
## Implementation Decisions

### Auto-Detection Candidates
- Add `py -3` (Windows Python launcher) to the candidate list ahead of bare `python`
- Add `python3` fallback for Linux/macOS after `python`
- Manual override bypasses all auto-detection — it is the absolute source of truth when set

### Override UI Design
- Current interpreter path: shown as a read-only row in plugin settings page with source label ("auto-detected" / "manual")
- Manual override: text input + "Validate" button in plugin settings page (not wizard-only)
- Validation triggered on button click, not on-blur
- Valid: green "✓ Valid: Python 3.11.2 at /path/to/python.exe"
- Invalid: red "✗ Invalid: {specific failure reason}"

### Interpreter Validation Scope
- Minimum: file exists + is executable + runs `--version` returning Python ≥ 3.10
- Check `pip --version` after version passes; warn if pip is missing (but don't block)
- Saved override is re-validated on plugin reload; show stale/warning state but don't block usage

### zotero_data_dir Validation
- Validate: path exists + is a directory + contains a `storage/` subdirectory
- Validation runs at "Install" button click in setup flow, blocking install with specific error messages
- Error messages are specific: "Zotero 数据目录无效：目录不存在" / "Zotero 数据目录中未找到 storage/ 子目录"

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `resolvePythonExecutable()` in `main.js:223-235` — current detection logic (venv candidates + fallback to `python`)
- `main.js:2120-2126` `runPython()` in setup wizard — currently spawns bare `python`, should use resolved interpreter
- `main.js:1550` PaperForgeSettingTab — settings rendering infrastructure
- `main.js:162` `DEFAULT_SETTINGS` — settings schema
- `main.js:337-344` `_fetchVersion()` — fetches paperforge version via resolved interpreter
- `main.js:2370-2397` `_autoUpdate()` — auto-update logic that also needs consistent interpreter

### Established Patterns
- Plugin settings use Obsidian `Setting` class API with `createEl()` DOM manipulation
- Settings persisted via `loadData()`/`saveData()` from Obsidian Plugin API
- Subprocess calls use `spawn()` + `execFile()` from `node:child_process`
- Translation strings in `LANG` object with `t()` helper

### Integration Points
- Setting tab: `PaperForgeSettingTab` class starting at ~line 1550
- Setup wizard: WizardModal class starting at ~line 1855
- Quick Actions: `ACTIONS` array at line 165
- Auto-update: `_autoUpdate()` at line 2370
- Python resolver: `resolvePythonExecutable()` at line 223
- Setup flow: `_stepInstall()` at line 2118 uses `runPython()` with bare `python`

</code_context>

<specifics>
## Specific Ideas

- The user confirmed "manual override as primary" as the Python strategy (option 1 from earlier milestone discussion)
- `py -3` and `python3` should be added as detection candidates
- Detection order: manual override (if set) → `.paperforge-test-venv` → `.venv` → `venv` → `py -3` → `python` → `python3`
- `zotero_data_dir` becomes required in setup flow (RUNTIME-06) — all instances of "optional" language updated to "required"
- All `spawn('python', ...)` direct calls should use the resolved interpreter instead

</specifics>

<deferred>
## Deferred Ideas

- pip availability check is noted but only surfaces as a warning in Phase 51; full pip-environment diagnosis belongs in Phase 53 (Doctor)
- Exports folder validation deferred to v2 (ONBOARD-01/02)
</deferred>
