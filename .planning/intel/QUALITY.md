# Quality Assessment

**Analysis Date:** 2026-05-16

## Code Organization Strengths

**Well-Defined Module Boundaries:**
- Clear 5-layer architecture (commands/ -> services/ -> adapters/ -> core/ -> worker/) enforced by v2.1 refactor
- Adapter layer (`paperforge/adapters/`) is genuinely independent and testable — BBT parsing, frontmatter, path normalization are isolated from business logic
- Core contract types (`PFResult`, `ErrorCode`) are small, focused, and widely used
- Worker modules (`paperforge/worker/`) separate "mechanical labor" from orchestration

**Version Management:**
- Single source of truth in `paperforge/__init__.py`
- `scripts/bump.py` automates across 4 files + git tag
- Consistent `__version__` import pattern throughout codebase

**PFResult Contract Compliance:**
- All 17 command modules return PFResult
- JSON output flag (`--json`) is consistent across all commands
- Plugin has uniform fallback chain: PFResult JSON -> snapshot files -> CLI fallback
- ErrorCode enum has `.missing_()` handler for forward compatibility

**Test Architecture (Python):**
- 7 test directories with clear levels: unit, cli, integration, e2e, journey, chaos, audit
- ~93 Python test files, ~13,279 total lines
- Snapshot regression tests for JSON contracts
- Audit tests validate mock fidelity against real pipeline output
- Ruff linting enforced via pre-commit (E, F, I, UP, B, SIM)
- Per-file ruff ignore rules are documented with reasons

## Code Organization Risks

### CRITICAL: main.js Monolith (4,914 lines)

**File:** `paperforge/plugin/main.js`

**Issues:**
- Single file contains: IIFE module, 10+ pure functions, ItemView class (~1600 lines), SettingTab class (~1400 lines), Modal classes, and the Plugin class
- No JS build system — raw JS shipped directly
- Inline duplication: `memoryState` IIFE (lines 8-143) duplicates `resolvePythonExecutable()` logic from `src/testable.js` (lines 148-188) — two implementations of the same detection algorithm
- `memoryState.getCachedPython()` (line 85) uses `var` scoping and caches result differently from the pure `resolvePythonExecutable()` function
- Hard to test: most UI logic cannot be unit-tested because it depends on Obsidian `app` object
- No module system: `memoryState`, inline functions, and class definitions all share global scope

**Mitigation:**
- Extraction to `src/testable.js` has started (224 lines, 8 exported functions)
- 4 vitest test files exist for testable.js (310 lines)
- Plan 53-001 documented extraction strategy

### MODERATE: Duplicate Python Detection Logic

**Impact:** Python executable resolution is implemented in at least 4 locations:
1. `memoryState.getCachedPython()` in `main.js` lines 84-115 (vault-scoped caching)
2. `resolvePythonExecutable()` in `main.js` lines 148-188 (testable export, no caching)
3. `getPaperforgePythonCmd()` in `main.js` lines 405-434 (macOS-specific)
4. `_resolve_plugin_interpreter()` in `worker/status.py` lines 235-289 (Python reimplementation)

**Risk:** These diverged implementations may behave differently for edge cases (venv detection, macOS stub python, Windows py launcher).

### MODERATE: Snapshot File Race Conditions

**Files:** `memory-runtime-state.json`, `vector-runtime-state.json`, `runtime-health.json`

**Analysis:**
- Multiple Python commands write to the same snapshot files (status, embed, memory, runtime-health)
- Plugin reads these files synchronously with `readJSONFile()` (uses `fs.existsSync` + `fs.readFileSync`)
- No file locking in Python writers — two concurrent CLI invocations could:
  - Interleave writes to the same file
  - Write partial JSON (plugin reads incomplete file -> parse error -> returns null)
- Worker/vector_db.py has atomic write for build state (write to .tmp then rename) but state_snapshot.py does NOT use this pattern

**Recommendation:** Extend atomic write pattern (write.tmp + replace) to all three snapshot files. Or use a simple file lock (paperforge uses `filelock` in pyproject.toml already for other purposes).

**Evidence:**
- `state_snapshot.py` writes directly: `path.write_text(json.dumps(snap))` — no atomic write
- `vector_db.py` uses atomic write: `tmp = path.with_suffix(".tmp"); tmp.write_text(); tmp.replace(path)` — correct pattern

### LOW: Subprocess Error Handling Gaps

**File:** `paperforge/plugin/main.js` line 2274 `_runAction()`

**Analysis:**
- stdout/stderr parsed line-by-line with rudimentary filtering
- No structured parsing of PFResult output in action runner (contrast with SettingsTab._callPython which parses exit codes)
- `spawn` timeout = 600000ms (10 min) for sync — no user-facing progress for the first 4 seconds (pollTimer)
- `_autoSync` uses `exec()` (shell-unsafe cmd string building) rather than `execFile()` (safer)
  - Line 4720: `` const cmd = `"${pyResult.path}" -m paperforge --vault "${vaultPath}" sync`; ``
  - If vaultPath contains spaces or special characters, this is a shell injection vector (low severity since vault path is user-controlled but not attacker-controlled)

### MODERATE: I18n Coverage Gaps

**File:** `paperforge/plugin/main.js` lines 524-817

**Analysis:**
- Dashboard UI (PaperForgeStatusView) uses many hardcoded English strings:
  - Line 1559: `"System Status"`, line 1572: `"Library Snapshot"`, lines 1575-1578: `"papers"`, `"PDFs ready"`, `"OCR done"`, `"deep-read done"`
  - Lines 2163-2182: `"Workflow Overview"`, `"Total"`, `"PDF Ready"`, `"OCR Done"`, `"Deep Read"`, `"Sync Library"`, `"Run OCR"`
  - Line 2219: `"Attention"`, line 3577: `" chunks embedded"`
- Settings tab uses `t()` function but StatusView UI is mostly untranslated
- Translation structure is flat (all keys in one object) — hard to maintain
- ~400 keys total but StatusView covers <50 via `t()`

### LOW: Settings Tab Complexity

**File:** `paperforge/plugin/main.js` lines 2517-3903 (PaperForgeSettingTab)

**Analysis:**
- 1,386 lines for a single settings tab class
- Mixes: state management, UI rendering, Python subprocess calls, file I/O, skill management, vector DB config, model cache management
- Inline CSS strings throughout (`element.style.cssText = ...`) — hard to maintain
- State tracking intertwined with rendering (`_vectorDepsOk`, `_embedStatusText`, `_memoryStatusText` are both state flags and cache markers)

### MODERATE: JS Test Coverage

- 4 test files for JS, 310 lines total
- Only test `src/testable.js` exported functions
- Zero tests for: PaperForgeStatusView, PaperForgeSettingTab, Plugin class, memoryState IIFE, i18n system
- No E2E tests for plugin behavior
- Test setup uses vitest but no Obsidian API mocking utilities

### HIGH: Python Test Coverage Distribution

**Total:** ~13,279 lines of tests across 93 files

**Distribution concerns:**
- Tests live in 7 levels (unit, cli, integration, e2e, journey, chaos, audit) but no test count per level collected here
- Largest worker modules (ocr.py: 1835 lines, sync.py: 1126 lines, status.py: 1072 lines) are the hardest to unit test
- OCR testing requires PaddleOCR API mock (responses library used, but OCR module is 1835 lines — likely under-tested)
- No test coverage target documented (not enforced in CI)

## Technical Debt Inventory

### Debt 1: Legacy Worker Patterns
**Files:** `paperforge/worker/sync.py` (1126 lines), `paperforge/worker/ocr.py` (1835 lines)

**Issues:**
- v2.1 architecture introduced SyncService but worker/sync.py still contains 1126 lines of legacy logic
- SyncService at `services/sync_service.py` line 37: "Full migration of note-writing logic is planned for v2.2"
- `_retry.py` module exists but not consistently used

### Debt 2: setup_wizard.py Monolith
**File:** `paperforge/setup_wizard.py` (794 lines)

**Issues:**
- Setup wizard split into `paperforge/setup/` (6 modules, ~500 lines total) but the legacy `setup_wizard.py` still exists at 794 lines
- Likely duplicated logic between setup/ modules and monolithic setup_wizard.py

### Debt 3: Ruff Per-File Ignores
**File:** `pyproject.toml` lines 99-113

**Issues:**
- 7 files have per-file ruff rule ignores
- `F821` (undefined names) ignored in update.py and sync.py — actual bugs or intentional?
- 8 test-level rules ignored across all test files (E501, E402, etc.)

### Debt 4: No CI/CD Integration
- No GitHub Actions workflow detected
- Tests run locally only
- Release process is manual (`gh release create`)
- No automated test run on PR

### Debt 5: Obsidian API Version Constraint
**File:** `paperforge/plugin/manifest.json`

- `minAppVersion: "1.9.0"` — relatively recent, may not be compatible with older Obsidian installs
- Desktop-only (`"isDesktopOnly": true`) — Electron APIs assumed

## Dependency Risks

### Risk 1: PaddleOCR API Dependency
- OCR pipeline requires external PaddleOCR API (Baidu)
- API key required (`PADDLEOCR_API_TOKEN` in .env)
- No offline OCR fallback
- Chinese service may have latency/availability issues outside China

### Risk 2: ChromaDB + sentence-transformers Optional Dependencies
- Vector DB feature requires 3 optional packages (~500MB)
- sentence-transformers downloads models on first use (80-440MB each)
- HF mirror dependency for users behind firewalls
- No fallback to pure-JS embedding

### Risk 3: Electron require() Limitations
- Obsidian plugins run in Electron renderer process
- `require('node:child_process')`, `require('fs')` work but are Electron-specific
- No `require()` for local project files — forces all code into main.js or inline IIFE
- This is the root cause of the main.js monolith

## Recommendations

1. **Split main.js:** Extract SettingTab, StatusView, and Plugin class into separate files, use a manual concatenation build step
2. **Atomic snapshot writes:** Extend .tmp + rename pattern to all 3 snapshot files
3. **Deduplicate Python detection:** Single shared algorithm with documented fallback order
4. **Translate StatusView:** Wrap all user-facing strings in plugin StatusView with `t()` calls
5. **Add JS UI tests:** Mock Obsidian API for StatusView rendering tests
6. **Remove legacy setup_wizard.py:** After confirming setup/6-module split is complete
7. **Add CI pipeline:** GitHub Actions for ruff + pytest + vitest

---

*Quality assessment: 2026-05-16*
