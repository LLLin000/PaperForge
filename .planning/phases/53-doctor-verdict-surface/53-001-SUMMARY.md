---
phase: 53
plan: 001
name: Doctor Verdict Surface
subsystem: paperforge.worker.status
type: execute
wave: 1
requirements: [DOCTOR-01, DOCTOR-02, DOCTOR-03, DOCTOR-04]
commit: 6abadd9
duration: ~25 min
completed: 2026-05-08
provides:
  - Interpreter resolution pipeline matching plugin resolvePythonExecutable()
  - Per-module dependency manifest with version extraction
  - Aggregated verdict with color-coded [OK]/[WARN]/[FAIL]
affects:
  - paperforge/worker/status.py (run_doctor output and logic)
tech-stack:
  added:
    - subprocess (interpreter resolution, pip show queries)
    - ANSI color codes (verdict output, disabled for non-TTY)
  patterns:
    - add_check(category, status, message, fix) preserved for all new checks
    - Module-level _MODULE_MANIFEST constant for dependency metadata
    - Subprocess-based interpreter resolution matching Obsidian plugin logic
key-files:
  modified:
    - paperforge/worker/status.py (main implementation)
decisions:
  - Verdict uses ANSI escape codes directly (no external library)
  - _MODULE_MANIFEST is module-level for testability (verification imports it)
  - Return value simplified: 1 if any fail, 0 otherwise (fix_map no longer drives exit code)
  - Existing sys.version_info check kept as "Python 环境" (doctor's own interpreter), new checks as "Python 环境 (插件)" (plugin-resolved interpreter)
---

# Phase 53 Plan 001: Doctor Verdict Surface

**One-liner:** Plugin-matching interpreter resolution pipeline with per-module versioned dependency checks and final color-coded verdict in `paperforge doctor`.

## Objective

`paperforge doctor` previously reported only `sys.executable` Python version and a flat dependency check. After this phase, it replicates the plugin's `resolvePythonExecutable()` interpreter resolution logic, queries that interpreter for Python version and paperforge package status, detects wrong-environment conditions, checks dependency versions individually, and ends with a colored [OK]/[WARN]/[FAIL] verdict with a recommended next CLI action.

## Tasks Executed

### Task 1 — Interpreter resolution + version + package drift (DOCTOR-01, DOCTOR-02)

**Type:** auto

**New helpers added to `paperforge/worker/status.py`:**

| Function | Purpose |
|---|---|
| `_read_plugin_data(vault)` | Reads `.obsidian/plugins/paperforge/data.json` for `python_path` override; returns `{}` on any failure |
| `_resolve_plugin_interpreter(vault, plugin_data)` | Replicates plugin `resolvePythonExecutable()`: manual override -> venv candidates (.paperforge-test-venv, .venv, venv) -> system candidates (py -3, python, python3) -> fallback "python" |
| `_query_resolved_version(interp, extra_args)` | Runs `[interp] + extra_args + ["--version"]` via subprocess; returns (version_str, version_tuple) |
| `_query_resolved_package(interp, extra_args, package_name)` | Runs `pip show <package>` via subprocess on resolved interpreter; returns parsed dict or None |

**Wired into `run_doctor()`:**
- Plugin-resolved interpreter path + source shown under "Python 环境 (插件)"
- Resolved interpreter version validated >= 3.10, with fail otherwise
- PaperForge package version compared against `paperforge.__version__`; drift triggers warning
- Package Location compared against current process's `paperforge.__file__` dir for wrong-environment detection

### Task 2 — Per-module dep checks + verdict (DOCTOR-03, DOCTOR-04)

**Type:** auto

**Dependency check upgrade:**
- Replaced flat `required_modules = ["requests", "pymupdf", "PIL", "yaml"]` with `_MODULE_MANIFEST` (module-level, 4 entries)
- Each module checked individually with version extraction via `getattr(mod, '__version__', None)`
- PyYAML < 6.0 triggers a specific warning instead of pass
- Per-package repair command is specific (e.g., `pip install pyyaml>=6.0` not a generic combined command)

**Verdict aggregation:**
- After all per-category output, checks are scanned for any `fail` or `warn` status
- Verdict displayed as `[OK]` (green), `[WARN]` (yellow), or `[FAIL]` (red)
- Recommended next action selected based on which categories have failures
- ANSI color codes disabled when `sys.stdout.isatty()` is False (piped/file output)
- Return value: `1` if any `fail` status, `0` otherwise

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

Full details in `53-VERIFICATION.md`.

| Requirement | Status |
|---|---|
| DOCTOR-01: Interpreter path + version via plugin resolution | PASS |
| DOCTOR-02: Package version drift + wrong-environment detection | PASS |
| DOCTOR-03: Per-module checks with versions + PyYAML check | PASS |
| DOCTOR-04: Colored verdict + recommended action | PASS |
| Color pipe-safe (no ANSI when not TTY) | PASS |
| No regressions (499/504 existing tests pass) | PASS |

## Commits

| Hash | Description |
|---|---|
| `6abadd9` | feat(53-doctor-verdict-surface): add interpreter resolution, per-module dep checks, and verdict (272 insertions, 18 deletions in status.py) |
