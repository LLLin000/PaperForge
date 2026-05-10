---
phase: pr-3-review
reviewed: 2026-05-08T12:00:00Z
depth: deep
files_reviewed: 21
files_reviewed_list:
  - AGENTS.md
  - README.md
  - docs/INSTALLATION.md
  - docs/setup-guide.md
  - manifest.json
  - paperforge/__init__.py
  - paperforge/ocr_diagnostics.py
  - paperforge/plugin/main.js
  - paperforge/plugin/manifest.json
  - paperforge/plugin/styles.css
  - paperforge/plugin/versions.json
  - paperforge/worker/status.py
  - paperforge/worker/sync.py
  - pyproject.toml
  - scripts/bump.py
  - tests/conftest.py
  - tests/test_asset_index_integration.py
  - tests/test_asset_state.py
  - tests/test_command_docs.py
  - tests/test_migration.py
  - tests/test_plugin_install_bootstrap.py
findings:
  critical: 0
  warning: 6
  info: 3
  total: 9
status: issues_found
---

# PR #3: Code Review Report

**Reviewed:** 2026-05-08T12:00:00Z
**Depth:** deep (cross-file + call-chain + type consistency)
**Files Reviewed:** 21
**Status:** issues_found (6 WARNING, 3 INFO, 0 BLOCKER)

## Summary

Pull Request #3 ("milestone/v1.12-clean") delivers the "plugin runtime closure" feature set: interpreter override, consistent subprocess resolution via `resolvePythonExecutable()`, Dashboard workflow closure (OCR queue add/remove, once-per-session privacy warning, `/pf-deep` command copy with agent platform label), and stronger `doctor` diagnostics. It also consolidates the deep-reading data model to main-note-only and removes stale `docs/` files (INSTALLATION.md, setup-guide.md).

**Overall assessment: NEARLY MERGE READY.** The code is logically sound, the architectural design is clean, and tests pass (501 passed, 2 skipped — both pre-existing platform-specific skips unrelated to this PR). However, 6 WARNING-level issues should be addressed before merging. No BLOCKER-level issues were found.

---

## Checklist Results

| Item | Verdict |
|------|---------|
| **Diff clean?** | YES — No .planning artifacts, no unrelated changes, doc deletions are intentional |
| **Code logically sound for runtime closure?** | YES — Interpreter resolution, runtime health, Dashboard DASH-01/02/03 workflow closure all achieved |
| **Obvious bugs, regressions, missing error handling?** | 6 WARNING issues found (see below) |
| **Test suite sufficient?** | YES — 501 passed, 2 skipped (both pre-existing platform skips in `test_pdf_resolver.py`) |
| **Version alignment clean?** | YES — All three version sources aligned at `1.4.17rc3` |
| **Cross-file consistency?** | 1 issue: `versions.json` retroactively changed minAppVersion for an old release |

---

## Warnings

### WR-01: Hardcoded stale fallback version strings

**File:** `paperforge/plugin/main.js:1482`, `paperforge/plugin/main.js:1728`
**Issue:** Two places hardcode `'1.4.17rc2'` as a fallback when `manifest.version` is falsy:

```javascript
// Line 1482
const ver = this.plugin.manifest.version || '1.4.17rc2';

// Line 1728
const ver = this.manifest.version || '1.4.17rc2';
```

The version has been bumped to `1.4.17rc3` everywhere else, but these fallbacks remain at `rc2`. If `manifest.version` is ever undefined (corrupted settings, race condition during load), the wrong version tag would be passed to `pip install`. While unlikely in practice, this is a maintenance magnet that will inevitably be missed on future bumps.

**Fix:** Replace with a dynamic reference or a generic fallback:

```javascript
const ver = this.plugin.manifest.version;
// If ver is falsy, don't proceed with sync at all
if (!ver) {
    new Notice('[!!] Cannot sync: plugin version unknown', 6000);
    return;
}
```

Or at minimum, align with the current version:

```javascript
const ver = this.plugin.manifest.version || '1.4.17rc3';
```

---

### WR-02: versions.json retroactively changed minAppVersion for old release 1.4.3

**File:** `paperforge/plugin/versions.json:2`
**Issue:** The entry `"1.4.3": "1.0.0"` was changed to `"1.4.3": "1.9.0"`.

In Obsidian's plugin update mechanism, `versions.json` maps each plugin version to the minimum Obsidian version required **for that specific release**. Old entries must remain unchanged — they represent the requirements that were valid at the time of that release. Version `1.4.3` did NOT require Obsidian `1.9.0`.

Only the **new** version entry (`1.4.17rc3`) should map to `"1.9.0"`. The old `1.4.3` entry should stay at `"1.0.0"`.

```diff
 {
-  "1.4.3": "1.9.0",
+  "1.4.3": "1.0.0",
   "1.4.17rc3": "1.9.0"
 }
```

---

### WR-03: JS `resolvePythonExecutable` only has Windows-style venv paths

**File:** `paperforge/plugin/main.js:884-887`
**Issue:** The JavaScript `resolvePythonExecutable()` function hardcodes Windows-only venv paths:

```javascript
const venvCandidates = [
    path.join(vaultPath, '.paperforge-test-venv', 'Scripts', 'python.exe'),
    path.join(vaultPath, '.venv', 'Scripts', 'python.exe'),
    path.join(vaultPath, 'venv', 'Scripts', 'python.exe'),
];
```

On macOS/Linux (where Obsidian/Electron also runs), virtualenv Python binaries live in `bin/python`, not `Scripts/python.exe`. The Python counterpart in `status.py` (`_resolve_plugin_interpreter`) correctly handles this with an `os.name == "nt"` check. The JavaScript version does not, meaning venv detection silently falls through on POSIX systems.

**Fix:** Add platform-aware venv paths:

```javascript
const isWin = process.platform === 'win32';
const venvCandidates = isWin ? [
    path.join(vaultPath, '.paperforge-test-venv', 'Scripts', 'python.exe'),
    path.join(vaultPath, '.venv', 'Scripts', 'python.exe'),
    path.join(vaultPath, 'venv', 'Scripts', 'python.exe'),
] : [
    path.join(vaultPath, '.paperforge-test-venv', 'bin', 'python'),
    path.join(vaultPath, '.venv', 'bin', 'python'),
    path.join(vaultPath, 'venv', 'bin', 'python'),
];
```

---

### WR-04: `execFileSync` in synchronous code path can block UI thread

**File:** `paperforge/plugin/main.js:897-914`
**Issue:** `resolvePythonExecutable()` uses `execFileSync` (synchronous) to test system candidates, with a 5-second timeout per candidate, up to 3 candidates. This function is called during **synchronous rendering** of both the Settings tab (`display()`) and the Dashboard (`_renderGlobalMode()`).

If Python is not properly installed and `py -3`, `python`, or `python3` each time out, the Obsidian render thread blocks for up to 15 seconds. This causes a visible UI freeze.

**Fix:** Two options:

1. **Async-first design**: Make `resolvePythonExecutable` async, cache the resolved interpreter, and use the cached value during rendering. The system candidate probe runs once asynchronously.

2. **Use `execFile` instead of `execFileSync`**: Replace the system candidate loop with an async approach:

```javascript
// Return cached result if already probed
if (resolvePythonExecutable._cache) return resolvePythonExecutable._cache;

// During synchronous rendering, skip the execFileSync probe entirely
// and let the async probe update the cache later.
```

---

### WR-05: Bare `Exception` catch in `_read_plugin_data`

**File:** `paperforge/worker/status.py:1963`
**Issue:** The `_read_plugin_data` function catches bare `Exception`, which can suppress `KeyboardInterrupt`, `MemoryError`, and other system-level exceptions:

```python
except (json.JSONDecodeError, OSError, Exception):
    return {}
```

Since `OSError` already covers the `PermissionError`/`FileNotFoundError` cases, the bare `Exception` is redundant and dangerous.

**Fix:**

```python
except (json.JSONDecodeError, OSError):
    return {}
```

---

### WR-06: Zotero data directory changed from optional to required without migration path

**Files:** `paperforge/plugin/main.js` (setup wizard validation, step 4 logic, summary page)
**Issue:** The Zotero data directory was previously optional (with placeholder text "可选，用于自动检测 PDF"). It is now required, with strict validation: not empty, exists, is a directory, and contains `storage/` subdirectory.

Existing users who completed setup with `zotero_data_dir` left empty will encounter setup wizard validation failures on their next reconfiguration visit. There is no migration logic to detect this state and prompt the user, nor an auto-discovery mechanism to fill in a likely path.

**Fix:** Add a one-time migration notice or auto-discovery:

```javascript
// On settings load, if zotero_data_dir is empty, attempt auto-discovery:
if (!s.zotero_data_dir) {
    const candidates = [
        path.join(os.homedir(), 'Zotero'),
        path.join(os.homedir(), 'Zotero', 'storage'),
    ];
    for (const c of candidates) {
        if (fs.existsSync(path.join(c, 'storage'))) {
            s.zotero_data_dir = c;
            break;
        }
    }
}
```

---

## Info

### IN-01: Repetitive `require('fs')` calls in method bodies

**File:** `paperforge/plugin/main.js` — methods `_validatePythonOverride`, `_syncRuntime`, `_preCheck`, `_validateSetup`, etc.
**Issue:** `require('fs')`, `require('path')`, and `require('node:child_process')` are called at the top of individual methods instead of once at module scope. This is wasteful (Node caches `require` calls, so there's no runtime penalty) but is a readability/maintainability concern.

**Suggestion:** Move all `require()` calls to module scope at the top of the file.

---

### IN-02: `run_doctor()` return value semantics changed

**File:** `paperforge/worker/status.py` (near line 2290)
**Issue:** The return value of `run_doctor()` changed semantics:

- **Before:** returned `1` if `fix_map` had entries (any issue with a suggested fix, including warnings)
- **After:** returns `1 if has_fail else 0` (only hard failures)

Callers (CI scripts, `paperforge doctor` CLI handler) may rely on exit code `1` for any actionable issue. Verify that the CLI handler for `doctor` checks for warnings separately. If not, a warnings-only state would now produce exit code 0 when it previously produced 1.

---

### IN-03: `versions.json` missing trailing newline

**File:** `paperforge/plugin/versions.json`
**Issue:** The file ends without a trailing newline (`\n` at EOF). Minor POSIX compatibility concern — some tools (e.g., `diff`, `cat`) warn about missing trailing newlines.

---

## Conclusion

**Verdict: CONDITIONAL MERGE** — fix the 6 WARNING issues first.

The three most important fixes are:
1. **WR-01** — Fix hardcoded `'1.4.17rc2'` fallbacks (quick fix, prevents latent version drift)
2. **WR-02** — Restore `"1.4.3": "1.0.0"` in versions.json (data integrity for Obsidian update mechanism)
3. **WR-05** — Remove bare `Exception` catch in `_read_plugin_data` (defensive coding)

WR-03 and WR-04 are cross-platform correctness issues; WR-06 is a UX gap for existing users. None block the merge but should be documented as known limitations.

The structural design of the PR is sound. The interpreter resolution refactoring (returning `{path, source, extraArgs}` instead of a bare string) is cleanly applied across all call sites. The Dashboard workflow closure (DASH-01/02/03) is well-implemented with proper state management. The deep-reading model consolidation to main-note-only is consistent across JS plugin, Python backend, and tests.

---

_Reviewed: 2026-05-08T12:00:00Z_
_Reviewer: VT-OS/OPENCODE (gsd-code-reviewer)_
_Depth: deep_
