---
phase: 54-dashboard-workflow-closure
reviewed: 2026-05-08T00:00:00Z
depth: deep
files_reviewed: 12
files_reviewed_list:
  - paperforge/plugin/main.js
  - paperforge/plugin/styles.css
  - paperforge/worker/status.py
  - pyproject.toml
  - manifest.json
  - paperforge/plugin/manifest.json
  - paperforge/plugin/versions.json
  - scripts/bump.py
  - README.md
  - AGENTS.md
  - docs/INSTALLATION.md
  - docs/setup-guide.md
findings:
  critical: 3
  warning: 2
  info: 0
  total: 5
status: issues_found
---

# Phase 54: Code Review Report

**Reviewed:** 2026-05-08T00:00:00Z
**Depth:** deep
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the plugin/runtime-closure changes across the dashboard, interpreter resolution, doctor output, packaging metadata, and doc cleanup. The branch improves the install surface, but the runtime-closure path still has several correctness gaps: POSIX vault-local environments are not auto-detected by the plugin, the new OCR queue UI does not stay in sync with the data source it renders from, and doctor still mixes interpreter contexts in ways that can produce false diagnoses.

## Critical Issues

### CR-01: Plugin auto-detection still ignores non-Windows virtualenvs

**File:** `paperforge/plugin/main.js:315-319`
**Issue:** `resolvePythonExecutable()` only probes `Scripts/python.exe` paths. On macOS/Linux, a vault-local environment lives under `.venv/bin/python` or `venv/bin/python`, so the plugin silently skips the intended environment and falls back to `py`/`python`. That breaks the milestone's “consistent interpreter usage” goal on non-Windows desktops and can run all plugin subprocesses against the wrong runtime.
**Fix:**
```js
const isWindows = process.platform === 'win32';
const venvCandidates = isWindows
  ? [
      path.join(vaultPath, '.paperforge-test-venv', 'Scripts', 'python.exe'),
      path.join(vaultPath, '.venv', 'Scripts', 'python.exe'),
      path.join(vaultPath, 'venv', 'Scripts', 'python.exe'),
    ]
  : [
      path.join(vaultPath, '.paperforge-test-venv', 'bin', 'python'),
      path.join(vaultPath, '.venv', 'bin', 'python'),
      path.join(vaultPath, 'venv', 'bin', 'python'),
    ];
```

### CR-02: “Add to OCR Queue” updates the note but not the dashboard state it renders from

**File:** `paperforge/plugin/main.js:1083-1098, 1456-1460, 1702-1706`
**Issue:** The new queue button edits `do_ocr` in note frontmatter, but the per-paper view and global stats are still rendered from cached canonical index data. `_refreshCurrentMode()` invalidates and reloads `formal-library.json`, and the file watcher only reacts to `formal-library.json` changes, not formal note edits. Result: after clicking the new queue button, the dashboard can immediately show the old queue state until some later sync/index rebuild happens.
**Fix:**
```js
await this.app.fileManager.processFrontMatter(noteFile, (fm) => {
  fm.do_ocr = newValue;
});

entry.do_ocr = newValue; // optimistic local update
this._currentPaperEntry = { ...entry, do_ocr: newValue };
this._refreshCurrentMode();
```
Also subscribe to formal note modifications or trigger an index refresh path that rebuilds the source the dashboard actually reads.

### CR-03: Doctor still validates dependencies in the current process, not the plugin-resolved interpreter

**File:** `paperforge/worker/status.py:409-434`
**Issue:** The new doctor flow resolves the plugin interpreter first, but per-module dependency checks still call `__import__()` in the current Python process. If the plugin is pinned to a different interpreter or venv, doctor can falsely report dependencies as present/missing and give a clean verdict for a broken plugin runtime.
**Fix:**
```python
def _check_module_in_interpreter(interp: str, extra_args: list[str], module: str) -> tuple[bool, str]:
    cmd = [interp, *extra_args, "-c", f"import {module}; print(getattr({module}, '__version__', ''))"]
    result = subprocess.run(cmd, capture_output=True, timeout=10, text=True)
    return result.returncode == 0, (result.stdout or result.stderr).strip()
```
Run every dependency check through `interp`/`extra_args`, not the doctor process itself.

## Warnings

### WR-01: Doctor's package-path mismatch warning is a false positive for normal installs

**File:** `paperforge/worker/status.py:401-407`
**Issue:** `pip show` returns the site-packages root in `Location`, while `os.path.dirname(__import__("paperforge").__file__)` points at the package directory itself. Those values differ even when they refer to the same environment, so doctor will emit a mismatch warning in healthy installs.
**Fix:**
```python
current_package_root = Path(__import__("paperforge").__file__).resolve().parent
reported_package_root = Path(loc).resolve() / "paperforge"
if reported_package_root != current_package_root:
    add_check(...)
```

### WR-02: Doctor suggests `pip install -e .` from a vault, which is the wrong remediation for plugin-first users

**File:** `paperforge/worker/status.py:396-398`
**Issue:** When the resolved interpreter is missing `paperforge`, doctor tells users to run `pip install -e .`. `paperforge doctor` is run from a vault, not from a repository checkout, so that command is invalid for the primary plugin-first install flow and will usually fail or install the wrong project.
**Fix:**
```python
f"运行: {interp} -m pip install --upgrade git+https://github.com/LLLin000/PaperForge.git"
```
If editable installs are still supported, only suggest `-e .` when the current working directory actually contains the project metadata.

---

_Reviewed: 2026-05-08T00:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: deep_
