# Phase 51: Runtime Selection & Setup Gate - Verification Results

**Date:** 2026-05-08
**Plan:** 51-001
**Branch:** milestone/v1.12-install-runtime-closure

---

## Verification Criteria

### 1. resolvePythonExecutable accepts manual override and includes py -3 / python3

```
[PASS] Function signature: resolvePythonExecutable(vaultPath, settings)
[PASS] Manual override: settings.python_path non-empty + exists returns {path, source:'manual', extraArgs:[]}
[PASS] Detection order: manual -> .paperforge-test-venv -> .venv -> venv -> py -3 -> python -> python3
[PASS] py -3 handled via extraArgs: ['-3'] for proper execFile/spawn argument passing
[PASS] Fallback: returns {path:'python', source:'auto-detected', extraArgs:[]} if nothing works
```

### 2. All spawn/exec call sites use resolved interpreter

```
[PASS] Zero bare 'python' spawn/exec calls remaining (grep confirms 0 results)
[PASS] All 9 usage sites destructure { path, extraArgs } with settings passed:
  - Line 377:  _fetchVersion — plugin?.settings
  - Line 459:  _fetchStats — plugin?.settings
  - Line 1394: _runAction — plugins['paperforge']?.settings
  - Line 1627: Settings UI display — this.plugin.settings
  - Line 1660: Settings UI onChange re-render — this.plugin.settings
  - Line 1855: _preCheck — this.plugin?.settings
  - Line 2323: _runInstall/runPython — this.plugin.settings
  - Line 2464: _stepComplete — this.plugin.settings
  - Line 2521: Command palette — this.settings
  - Line 2575: _autoUpdate — this.settings
[PASS] extraArgs propagated to all execFile/spawn calls for py -3 compat
```

### 3. Settings UI shows path + override + validation

```
[PASS] Read-only Python interpreter row with source label (auto-detected/manual/stale)
[PASS] Custom path text input wired to settings.python_path with onChange auto-save
[PASS] Validate button with full check chain:
  - Empty: "Enter a path first"
  - File exists: "Path does not exist"
  - Executable: "Not executable"
  - Version >= 3.10: "Python version too low, need 3.10+"
  - pip check: warning if pip not found
[PASS] Stale override shows [!!] prefix with warning message
[PASS] Three i18n keys added: field_python_interp, field_python_custom, btn_validate (en/zh)
[PASS] onChange updates read-only row desc via _refreshPythonInterpDesc
```

### 4. zotero_data_dir is required with validation blocking install

```
[PASS] field_zotero_placeholder i18n changed to 'Required'/'必填'
[PASS] Wizard placeholder uses t('field_zotero_placeholder') instead of hardcoded string
[PASS] _validateStep3 checks:
  - Non-empty: "Zotero 数据目录为必填项"
  - Exists: "Zotero 数据目录路径不存在"
  - Is directory: "Zotero 数据目录路径不是一个目录"
  - Has storage/ subdirectory: "Zotero 数据目录中未找到 storage/ 子目录"
[PASS] _validate() rejects missing zotero_data_dir via validate_zotero i18n key
[PASS] zotero_data_dir unconditionally passed to --zotero-data flag
```

### 5. Re-validation on reload works for saved override

```
[PASS] loadSettings() checks settings.python_path for existence
[PASS] Stale path triggers console.warn with descriptive message
[PASS] _python_path_stale transient flag set/cleared without persisting to data.json
[PASS] saveSettings() key filter (Object.keys(DEFAULT_SETTINGS)) excludes _python_path_stale
```

---

## File Stats

| Metric | Value |
|--------|-------|
| Original lines | 2250 |
| Current lines | 2448 |
| Lines added | 198 |
| Commits | 3 |

## Commit Hashes

| Task | Hash | Message |
|------|------|---------|
| 1 | 4e16461 | refactor resolvePythonExecutable with manual override and reload validation |
| 2 | 931438d | add Python interpreter row, custom path input, and validate button to settings UI |
| 3 | 282035d | consistent interpreter usage, zotero_data_dir required with validation |

---

## Requirements Coverage

- **RUNTIME-01**: [PASS] Settings shows resolved Python path + source label
- **RUNTIME-02**: [PASS] Manual override text input + Validate button with full check chain
- **RUNTIME-03**: [PASS] All subprocess calls use resolvePythonExecutable() — zero bare 'python'
- **RUNTIME-06**: [PASS] zotero_data_dir required, validated (exists + dir + storage/ subdir), blocks install on failure

## Deviations

**None** — plan executed exactly as specified.
