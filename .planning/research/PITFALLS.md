# Pitfalls Research

**Domain:** Python CLI application — adding shared utilities, logging, pre-commit, and UX improvements to a brownfield Obsidian + Zotero literature pipeline
**Researched:** 2026-04-25
**Confidence:** HIGH

---

## Critical Pitfalls

### Pitfall 1: Shared Utility Extraction Creating Circular Imports

**What goes wrong:**
Extracting `read_json`, `write_json`, `yaml_quote`, `load_vault_config`, `pipeline_paths`, `STANDARD_VIEW_NAMES`, and `_JOURNAL_DB` into `paperforge/worker/_utils.py` creates circular import chains. The 7 worker modules already cross-import: `ocr.py` imports from `sync.py`, `deep_reading.py` imports from both `sync.py` and `ocr.py`, `repair.py` imports from all three. If `_utils.py` re-exports or imports anything from worker modules (even indirectly via shared path construction), circular imports explode at runtime with `ImportError: cannot import name '...' from partially initialized module '...' (most likely due to a circular import)`.

**Why it happens:**
- `_JOURNAL_DB` is a module-level global singleton shared across workers — moving it to `_utils.py` means workers must import from `_utils`, but `sync.py` already exports functions that `ocr.py` and `deep_reading.py` need (e.g., `load_export_rows`, `has_deep_reading_content`).
- `load_vault_config` and `pipeline_paths` are duplicated 7 times with identical logic. Extracting them requires careful dependency ordering to avoid `_utils.py` needing to import `config.py`, which imports... nothing problematic, but the *callers* (workers) already cross-import each other.
- The `pipeline_paths` function in each worker adds worker-specific keys on top of the shared `paperforge_paths()` output. Naively centralizing this function would lose the worker-specific keys.

**How to avoid:**
1. **Make `_utils.py` a pure leaf module** — it imports NOTHING from `paperforge.worker.*` or `paperforge.commands.*`. It can import from `paperforge.config` (already a leaf) and stdlib only. This is the single most important rule.
2. **Do NOT move `pipeline_paths` into `_utils.py`** — each worker's `pipeline_paths` adds unique keys. Instead, provide a `build_pipeline_paths(vault, extra_keys: dict)` factory in `_utils.py` that workers call with their own extras.
3. **Keep `_JOURNAL_DB` in `_utils.py` as a module-level global** — this is safe as long as it only depends on `_utils.py`'s own `read_json` and `load_vault_config`. The singleton pattern (check if not None before loading) works across all importers.
4. **Use lazy imports inside functions** for cross-worker dependencies that already exist. Example: `from paperforge.worker.sync import load_export_rows` inside a function (not at module top) avoids circular import at load time.
5. **Verify with `pytest --collect-only` immediately after extraction** — circular imports manifest as collection failures, not runtime failures. If test collection passes, the import graph is safe.

**Warning signs:**
- `ImportError` mentioning "partially initialized module" during `pytest` collection
- Any `from paperforge.worker import ...` at the top of `_utils.py`
- `_utils.py` importing from `paperforge.commands.*` or `paperforge.skills.*`
- Module count in `sys.modules` growing unexpectedly during import

**Phase to address:**
Phase 1 (shared utility extraction) — this is the first thing to do, and must be done correctly before any other change. All subsequent phases depend on `_utils.py` existing and being safe to import from.

---

### Pitfall 2: Replacing `print()` with `logging` Breaking Piped Output and Test stdio Capture

**What goes wrong:**
The current codebase uses bare `print()` for all output (status messages, OCR progress, deep-reading queue reports). Replacing these with `logging.info()` or `logging.getLogger()` calls without proper configuration breaks:

1. **Piped commands**: `paperforge status | grep ocr` stops working if logs go to stderr by default.
2. **Test stdout capture**: `pytest` tests that assert on `print()` output (e.g., `test_cli_worker_dispatch.py`, `test_path_normalization.py`, `test_legacy_worker_compat.py`) fail because `logging` output goes to stderr or is swallowed.
3. **Duplicate output**: If `logging.basicConfig()` is called in multiple worker modules (which currently happens implicitly via duplicated `load_simple_env` calls), handlers accumulate. The same log line prints twice, then three times, then more as modules are imported.
4. **`logging.basicConfig()` called in library code**: The `cli.py` main() function calls workers, and workers call `load_simple_env`. If any worker module also calls `logging.basicConfig()`, it conflicts with the application-level configuration. This is Python's #1 logging anti-pattern.

**Why it happens:**
- Python's stdlib `logging` module uses a global root logger. `basicConfig()` is a one-shot configuration — calling it a second time is silently ignored (by default) or raises if `force=True` is passed. This creates confusing behavior where "logs work in this module but not that one."
- `print()` writes to `sys.stdout`; `logging` by default writes to `sys.stderr` (StreamHandler default). Code that captures stdout (pytest, subprocess pipes) misses log output entirely.
- Windows PowerShell encoding (GBK/UTF-8 mismatch on redirected streams) adds another layer — `print()` may work but `logging.StreamHandler` with default encoding may crash.

**How to avoid:**
1. **Configure logging ONCE in `cli.py` `main()`**, before any worker is imported. Use `dictConfig` for explicit, maintainable handler setup.
2. **Use a dedicated `StreamHandler(sys.stdout)` for CLI-facing output** at INFO level and above. Keep `stderr` for WARNING/ERROR only.
3. **Use `sys.stdout.isatty()` check** to emit structured output (JSON) when piped vs. human-readable when interactive. This prevents breaking `paperforge deep-reading | grep ready` workflows.
4. **Add `force=True` to `basicConfig`** in the single configuration call to prevent silent failures if something else already configured logging.
5. **Provide a `get_logger(__name__)` helper** in `_utils.py` that returns a pre-configured logger. All workers use this instead of `logging.getLogger()`.
6. **Preserve `print()` for user-facing interactive output** where formatting matters (OCR queue tables, diagnostic reports). Only replace `print()` for informational/debug messages that don't need rich formatting. Not every `print()` should become a `logger.info()`.
7. **Update test assertions that capture stdout** to either capture logging output (via `caplog` fixture) or verify through the returned exit code + side effects (file contents) rather than stdout.

**Warning signs:**
- `logging.basicConfig()` appearing in any file under `paperforge/worker/`
- Tests that previously passed on stdout assertions suddenly failing
- Log messages appearing twice in CI logs
- `No handlers could be found for logger "paperforge.xxx"` warnings at startup

**Phase to address:**
Phase 2 (logging integration) — must come AFTER shared utility extraction (Phase 1) because the `get_logger` helper lives in `_utils.py`. Must come BEFORE Phase 4 (progress bars) because progress bars interact with logging output formatting.

---

### Pitfall 3: Pre-Commit Hooks That Make Development Painful

**What goes wrong:**
Adding pre-commit hooks without careful tuning causes developers to `--no-verify` commits, skip hooks entirely, or waste hours on false positives. Specific failure modes:

1. **Slow hooks (>5 seconds)**: Running `mypy` or full test suite as a pre-commit hook. Developers commit 50+ times per day in TDD workflows — even 3-second delays compound to minutes of waiting.
2. **False positives on test fixtures**: Dead code detection marks `conftest.py` fixtures, sandbox generators, and `test_*.py` helper functions as "unused" because they're dynamically discovered by pytest.
3. **Formatting hooks that reformat test fixture files**: `ruff format` or `black` applied to sandbox vault files (`tests/sandbox/00_TestVault/`) that have intentional whitespace/formatting.
4. **Windows line ending conflicts**: CRLF vs. LF mismatch between Windows development machines and Linux CI. Hooks pass locally on Windows but fail in CI with "files would be reformatted."
5. **Version skew**: Hooks pinned to specific versions in `.pre-commit-config.yaml` but CI installs different versions, producing different results.

**Why it happens:**
- pre-commit runs hooks in isolated virtualenvs — dependencies may differ from the project's `requirements.txt` or `pyproject.toml`.
- Static analysis tools (dead code detectors, mypy) operate on AST/syntax level and cannot understand pytest fixture discovery, `conftest.py` auto-import, or dynamic dispatch patterns used in `cli.py` stubs.
- `pre-commit run --all-files` in CI catches issues that escaped local hooks (force push, forgotten `pre-commit install`), but if local windows pass and CI Linux fails, developers can't reproduce locally.

**How to avoid:**
1. **Keep pre-commit hooks FAST (<2 seconds total)**:
   - `ruff` (lint + format) — replaces `black`, `isort`, `flake8`, `pyupgrade` in a single sub-second hook
   - `check-yaml`, `check-json`, `check-toml` — basic syntax checks only
   - `trailing-whitespace`, `end-of-file-fixer`, `mixed-line-ending` — fast text checks
   - NO `mypy`, NO `pytest`, NO dead code detection as pre-commit hooks — these go to CI only
2. **Exclude test fixture directories** from all hooks:
   ```yaml
   exclude: |
     (?x)^(
       tests/sandbox/.*|
       tests/.*/fixtures/.*|
       .*\.base$
     )
   ```
3. **Force LF line endings globally** in `.gitattributes` and `.pre-commit-config.yaml`:
   ```yaml
   - repo: https://github.com/pre-commit/pre-commit-hooks
     hooks:
       - id: mixed-line-ending
         args: ['--fix=lf']
   ```
4. **Run the SAME hooks in CI** via `pre-commit run --all-files` — this eliminates the "works on my machine" problem. If hooks pass locally and CI fails, the hook config is misconfigured, not the code.
5. **Pin ALL hook versions to exact tags** (never `rev: main` or `rev: master`). Run `pre-commit autoupdate` monthly.
6. **Bootstrap with `--min-confidence high`** for any dead code detector, and maintain a `.deadcode.toml` allowlist for intentionally-dynamic symbols (cli.py stubs, pytest fixtures, agent skill entry points).

**Warning signs:**
- Developers using `git commit --no-verify` as a habit
- Pre-commit hook taking >5 seconds to complete
- CI failing on formatting issues that "pass locally"
- Deleted test code being caught by dead-code detection

**Phase to address:**
Phase 3 (pre-commit hooks) — must come AFTER shared utility extraction (Phase 1) because the hooks need to validate the refactored module structure. The `.pre-commit-config.yaml` should be committed early and iterated on.

---

### Pitfall 4: Progress Bars Breaking Windows PowerShell Piping

**What goes wrong:**
Adding `tqdm` or `rich.progress` progress bars to long-running operations (OCR uploads, large PDF processing) breaks two critical workflows:

1. **Non-TTY output**: When `paperforge ocr` is piped to a file or run from a script, progress bars either render as garbage (ANSI escape sequences in text files) or are stripped entirely (rich detects non-TTY and produces no output at all). Users lose visibility into long-running operations.
2. **Windows PowerShell encoding**: PowerShell redirects stdout as UTF-16 by default. `tqdm` uses `\r` (carriage return) for in-place updates, which doesn't work with UTF-16 encoding. Rich's legacy Windows layer uses `mbcs` encoding on redirected streams, causing `UnicodeEncodeError` on Chinese filenames.
3. **Subprocess capture**: When PaperForge is called from another process (AI agent via `paperforge ocr`), the parent captures stdout. Tqdm/rich detect non-TTY and either produce nothing or emit partial output only on completion.

**Why it happens:**
- Both `tqdm` and `rich` check `sys.stderr.isatty()` or `sys.stdout.isatty()` to decide whether to render progress animations. On Windows, this check is unreliable — ConPTY, legacy conhost, and PowerShell ISE all return different results.
- Rich on Windows falls back to "legacy Windows" rendering when stdout is a `FileIO` (pipe redirection), using `mbcs` encoding that cannot handle Unicode characters.
- `tqdm` defaults to `file=sys.stderr` and uses `\r` for updates. On Windows, `sys.stderr.reconfigure(encoding='utf-8')` is needed but not guaranteed.

**How to avoid:**
1. **Use `tqdm` with explicit `disable=None`** (auto-detection) and set `file=sys.stderr` for progress. Emit only final results to `sys.stdout`. This preserves piping of meaningful output.
2. **Detect non-interactive mode explicitly**: Check `sys.stdout.isatty()` and `sys.stderr.isatty()`. If either is False, disable progress bars and use simple line-by-line status messages instead.
3. **Reconfigure stdout/stderr encoding on Windows** early in `cli.py`:
   ```python
   if sys.platform == "win32":
       for stream in (sys.stdout, sys.stderr):
           if hasattr(stream, "reconfigure"):
               stream.reconfigure(encoding="utf-8")
   ```
4. **Provide `--no-progress` / `--quiet` flags** so scripts and agents can suppress progress bars explicitly.
5. **For OCR uploads**: emit progress as log-level messages (`logger.info("Uploading page 3/12...")`) rather than a progress bar. The OCR worker already writes `meta.json` with status — use that as the canonical progress tracking, not terminal output.

**Warning signs:**
- ANSI escape codes appearing in piped output files
- `UnicodeEncodeError` when running `paperforge ocr 2>&1 | tee log.txt` on Windows
- Progress bars appearing as a single static line instead of animating
- "No output" when calling `paperforge ocr` from subprocess

**Phase to address:**
Phase 4 (progress indicators / UX improvements) — depends on Phase 2 (logging) because progress indicators must coexist with the logging infrastructure. Should be tested on both Windows PowerShell and Git Bash.

---

### Pitfall 5: OCR Retry Logic Corrupting the Async State Machine

**What goes wrong:**
The OCR worker (`ocr.py`) manages an async state machine: `pending → processing → done/failed`. Adding retry/backoff without careful state management causes:

1. **Duplicate submissions**: Retrying a job that already submitted successfully creates a second OCR task. PaddleOCR processes both, producing two result sets. The second one overwrites the first or leaves orphaned files.
2. **Zombie `processing` state**: If the process crashes during a retry (Ctrl+C, OOM, power loss), `meta.json` stays at `ocr_status: processing`. No code recovers from this state — the job is permanently stuck.
3. **Infinite retry loops on permanent failures**: PaddleOCR 400 errors (bad PDF, authentication failure, quota exceeded) are NOT transient. Retrying them with exponential backoff wastes API quota and blocks the queue.
4. **State divergence between `meta.json` and `ocr-queue.json`**: The OCR worker writes both files. If retry logic updates one but not the other, the `deep-reading` worker reports incorrect status, and `paperforge repair` cannot automatically fix it.

**Why it happens:**
- The current code has no retry mechanism at all. Adding one needs to distinguish transient failures (network timeout, 503 Service Unavailable, connection reset) from permanent failures (400 Bad Request, 401 Unauthorized, 404 Not Found, file corruption).
- `meta.json` and `ocr-queue.json` are written independently — there's no atomic multi-file transaction. If the process dies between writes, they diverge.
- The `meta.json` schema has no `retry_count`, `last_error`, or `last_attempt_at` fields. Retry logic operates blind — it cannot distinguish "never attempted" from "failed 3 times."

**How to avoid:**
1. **Add retry metadata to `meta.json`**: `retry_count` (int), `last_error` (str), `last_attempt_at` (ISO timestamp). Update these atomically before each retry.
2. **Classify errors explicitly**: Only retry on `requests.Timeout`, `requests.ConnectionError`, HTTP 429, HTTP 503, HTTP 502. Never retry on HTTP 400, 401, 403, 404, or JSON parse errors.
3. **Add a `blocked` terminal state**: If `retry_count >= max_retries` OR the error is non-retryable, set `ocr_status: blocked`. The deep-reading worker already handles `blocked` (cleanup_blocked_ocr_dirs), and `paperforge repair` can detect it.
4. **Recover `processing` state on startup**: During `load_simple_env` / init, scan `meta.json` files with `ocr_status: processing`. If `last_attempt_at` is older than 1 hour (or missing), transition to `pending` for retry. This prevents zombie jobs.
5. **Use `tenacity` library** (lightweight, well-maintained, supports both sync and async) with:
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=2, min=4, max=60),
       retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
       before_sleep=lambda retry_state: update_meta_retry_count(retry_state),
   )
   ```
6. **Write `meta.json` using atomic write-then-rename** pattern to prevent corrupt files from mid-crash writes.

**Warning signs:**
- `ocr_status: processing` records that are hours/days old
- Duplicate OCR results for the same `zotero_key`
- PaddleOCR API returning 429 Too Many Requests (rate limiting)
- `ocr-queue.json` and `meta.json` disagreeing on job status

**Phase to address:**
Phase 5 (retry/backoff for OCR worker) — depends on Phase 2 (logging, to emit structured retry logs) and Phase 1 (shared utilities for write_json atomic). Must be tested with simulated network failures.

---

### Pitfall 6: Dead Code Removal Breaking Backward Compatibility

**What goes wrong:**
Removing "dead code" — legacy command aliases, unused imports, deprecated function stubs — breaks users still relying on those interfaces:

1. **Legacy CLI aliases removed**: `paperforge selection-sync`, `paperforge index-refresh`, `paperforge ocr run`, and `paperforge ocr doctor` are mapped in `cli.py` to new unified commands but callers (scripts, cron jobs, agent skills) may still use them.
2. **`cli.py` module-level globals (`run_status = None`, `run_selection_sync = None`, ...) removed**: Tests patch these via `importlib.reload(cli)` + `patch.object(cli, "run_status", stub)`. Removing them breaks all dispatch tests.
3. **`STRAIGHT_VIEW_NAMES`, `_JOURNAL_DB`, `STANDARD_VIEW_NAMES` removed from original modules**: Callers may `from paperforge.worker.sync import STANDARD_VIEW_NAMES` — if only `_utils.py` defines it, those imports break.
4. **Duplicate utility functions removed without re-export**: If `read_json` is moved to `_utils.py` and removed from `sync.py`, any code that does `from paperforge.worker.sync import read_json` breaks, even if the same function exists in `_utils.py`.
5. **`paperforge_lite` package name aliases removed**: The v1.2 rename from `paperforge_lite` to `paperforge` may have residual imports in user scripts or agent configurations.

**Why it happens:**
- Python's import system caches modules in `sys.modules`. `from paperforge.worker.sync import read_json` creates a binding to the `sync` module's namespace. Even if `read_json` is an identical function in `_utils.py`, the import path is different and the test/script fails.
- Dead code detectors flag `cli.py` stubs as "unused" because they're set to `None` and then conditionally assigned by `_import_worker_functions()`. This is intentional, not dead code.
- Legacy command aliases (`selection-sync`, `index-refresh`) were kept for backward compatibility. The v1.2 migration guide says they're deprecated but still functional. Removing them changes the documented CLI surface.

**How to avoid:**
1. **Re-export moved functions from original modules**: After moving `read_json` to `_utils.py`, add `from paperforge.worker._utils import read_json` to `sync.py`. This preserves the existing import path. Mark as `# Re-exported from _utils.py for backward compatibility`.
2. **Keep `cli.py` stubs exactly as-is**: The `globals set to None` pattern is intentionally designed for test patching. Do not "simplify" it.
3. **Phase legacy alias removal**: Add a deprecation warning (`warnings.warn("'selection-sync' is deprecated, use 'paperforge sync --selection'", DeprecationWarning)`) in v1.4. Actually remove in v1.5 or later. Give users at least one release cycle.
4. **Use a dead-code tool with an allowlist**: Create `deadcode.toml` with explicit exclusions for:
   - `cli.py` module-level globals
   - `conftest.py` fixtures and helpers
   - `test_*.py` files entirely
   - `__init__.py` re-exports
   - Functions called via `getattr`, decorators, or string-based dispatch
   - Agent skill entry points (`ld_deep.py`)
5. **Check backward imports with grep before removal**: `rg "from paperforge.worker.sync import (read_json|write_json|yaml_quote|load_vault_config)"` across the entire repo to find all importers.

**Warning signs:**
- `ModuleNotFoundError` or `ImportError` on user machines after update
- Dead code tool marking `cli.py` stubs as unused
- "Removed unused import" commits that delete imports used by string-based dispatch
- CI passing but users reporting "command not found" for `selection-sync`

**Phase to address:**
Phase 6 (dead code cleanup) — must be the LAST code change phase, after all other phases are stable. Run dead code detection as a CI check, not a pre-commit hook. Review findings manually, never auto-fix.

---

### Pitfall 7: Workflow Changes That Confuse Existing Users

**What goes wrong:**
The v1.4 milestone introduces significant workflow changes — OCR queue auto-processing, simplified manual steps, progress indicators. Users who have established workflows get confused or lose data:

1. **Changed frontmatter field behavior**: If `do_ocr: true` now triggers OCR automatically (previously required manual `paperforge ocr`), users with existing `do_ocr: true` set on hundreds of records get unexpected OCR processing.
2. **Removed manual steps**: If the workflow goes from "edit frontmatter → run ocr → run deep-reading → run /pf-deep" to "edit frontmatter → done (everything auto)", users lose the explicit control they rely on.
3. **Output format changes**: If `paperforge deep-reading` output format changes (from Markdown table to something else), scripts and agent prompts that parse this output break.
4. **Chinese-language UI consistency**: The project has Chinese frontmatter fields (`analyze`, `do_ocr`) and Chinese Base view names (`控制面板`, `推荐分析`, `待OCR`). Adding English-only error messages or log output breaks the mixed-language UX.

**Why it happens:**
- The project has an existing user base using v1.2/v1.3 workflows. Changes to the workflow must be opt-in or backward-compatible, not forced.
- User-edited frontmatter (in Obsidian) is the primary control mechanism. Any automation that modifies frontmatter without user consent violates the Lite architecture's principle of "worker does mechanical work, user controls decisions."
- Documentation (AGENTS.md, README.md, INSTALLATION.md) must be updated simultaneously with code changes. Out-of-sync docs are worse than no docs.

**How to avoid:**
1. **Workflow changes must be opt-in**: Add a `paperforge.json` config key (e.g., `"auto_ocr": false` default) that gates new automation. Existing users get zero behavior change until they explicitly enable it.
2. **Preserve all existing CLI command output formats**: If `deep-reading` output changes, add a `--format json` flag for scripts, keep Markdown as default for humans.
3. **Never auto-modify user-set frontmatter fields**: The `analyze`, `do_ocr` fields are user-controlled. Workers may read them but must not write them (except `ocr_status` and `deep_reading_status` which are system-managed).
4. **Maintain Chinese-language consistency**: Error messages, log output, and CLI help text should continue to use Chinese where the existing codebase does. New English-only messages should be bilingual or use Chinese.
5. **Update AGENTS.md and README.md in the SAME commit as code changes**: This prevents the documentation lag that users hit when they `paperforge update` and commands change without explanation.
6. **Write a MIGRATION-v1.4.md document**: Following the pattern established in v1.2's MIGRATION-v1.2.md, document every behavioral change, every removed/deprecated feature, and every workflow change with before/after examples.

**Warning signs:**
- Users reporting "paperforge stopped working" after update
- Frontmatter values changed unexpectedly after running sync
- Agent commands (`/pf-deep`, `/pf-paper`) behaving differently
- English error messages appearing in a Chinese-language vault

**Phase to address:**
All phases — workflow impact assessment should be part of every code change. The MIGRATION document should be maintained continuously, not written at the end.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Re-exporting all utils via `__init__.py` wildcard | One import for callers | Circular dependency risk, breaks explicit imports, makes static analysis impossible | Never — use explicit `from _utils import X` in each worker |
| `logging.basicConfig()` in each worker module | Logs work immediately | Duplicate handlers, silent failures, "where is my log going?" confusion | Never — configure once in cli.py main() |
| `try: import tqdm; USE_PROGRESS=True except: pass` | No new dependency | Inconsistent UX, some users get bars and some don't, impossible to debug | Only if tqdm is optional and `--no-progress` is the default |
| `time.sleep(retry_count * 2)` for backoff | No library needed | Blocks event loop, no jitter (thundering herd), can't configure max retries | Only for scripts with <3 calls, never for OCR worker |
| `git add -A && pre-commit run --all-files` in CI | Simple CI pipeline | Reformats entire codebase on every PR, loses git blame history, causes merge conflicts | Never — run only on changed files |
| Removing "unused" `cli.py` stubs | Cleaner code | Breaks 20+ dispatch tests, breaks backward compat | Never — these are intentionally nullable for test injection |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| PaddleOCR API | Retrying on 400/401 errors | Only retry on timeout, 429, 502, 503. Write `blocked` state for permanent failures. |
| obsidian:// wikilinks | Assuming forward slashes always work | Always use relative paths with `/`. Never store Windows backslash paths in wikilinks. |
| Better BibTeX JSON | Assuming `attachments[].path` is always storage:-prefixed | Handle 3 BBT formats: absolute Windows paths, `storage:` prefix, bare relative. Use `_normalize_attachment_path`. |
| `.env` files | Overwriting user-set env vars (no-overwrite is correct) | `load_simple_env` in config.py correctly checks `if not key or key in os.environ: continue`. Preserve this. |
| Windows junctions | Assuming `Path.resolve()` follows junctions | On Windows, `Path.resolve()` follows junctions. Use `paperforge.pdf_resolver.resolve_junction` for explicit control. |
| Frontmatter parsing | Regex-based parsing instead of YAML library | Use regex for surgical field access (preserves comments and formatting). NEVER rewrite entire frontmatter — use `update_frontmatter_field` and `_add_missing_frontmatter_fields` patterns. |
| Base view files | Hardcoding vault paths in `.base` JSON | Always use relative paths from vault root. Generated Bases use config-aware templates. |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `rglob('*.md')` on entire literature directory | Slow deep-reading scans | Cache formal note paths by zotero_key in a JSON index. Rebuild index on sync only. | ~500 literature notes |
| `read_json` + `write_json` for every OCR queue mutation | I/O thrashing, corrupt files on crash | Batch queue writes. Use atomic write-then-rename. | 20+ queued items |
| Loading all export JSONs on every sync | 10-30s sync time with large Zotero libraries | Load incrementally. Cache export inventory in memory during sync session. | 5,000+ Zotero items |
| Progress bar refresh on every OCR page | 100% CPU on progress rendering, no actual speed gain | Update progress on time intervals (every 500ms), not on every page completion. | 50+ page PDFs |
| Pre-commit running on all files in monorepo | 30s+ per commit, developers use --no-verify | `exclude` slow directories. Run slow checks in CI only. Use `stages: [push]` for expensive hooks. | Any repo with 50+ Python files |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Removing `--verbose` from deep-reading | Users can't see why a paper is blocked for deep reading | Keep `--verbose` and expand it to show per-paper status details |
| Changing `paperforge deep-reading` output format | Scripts that parse the queue report break | Add `--format json` for scripts, keep Markdown table as default for humans |
| Adding progress bars without quiet mode | AI agents calling `paperforge ocr` get garbage output | Add `--no-progress`/`--quiet` flags. Detect non-TTY and disable progress bars. |
| English-only log messages in Chinese UI | Chinese-speaking users (the target audience) lose context | Keep log messages bilingual where practical; use Chinese for user-facing messages |
| "Auto-fix" pre-commit hooks that reformat Obsidian Base files | Base view JSON gets reformatted, Obsidian can't parse it | Exclude `.base` files from all formatting hooks |
| Silent OCR failure with only meta.json updated | Users think OCR succeeded but fulltext.md is empty | Surface OCR errors prominently in `deep-reading` output. Highlight `ocr_status: failed` entries. |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Shared `_utils.py`:** Often missing re-exports in original modules — verify `from paperforge.worker.sync import read_json` still works after extraction.
- [ ] **Logging configuration:** Often missing `force=True` on `basicConfig` — verify second import doesn't swallow logs.
- [ ] **Pre-commit hooks:** Often running slow checks locally — verify total hook time <2 seconds on a fresh clone.
- [ ] **Progress bars:** Often untested on Windows PowerShell — verify output is clean when piped to `tee` or `> file.txt`.
- [ ] **OCR retry:** Often missing `processing→pending` recovery — verify zombie jobs older than 1 hour are automatically recovered.
- [ ] **Dead code removal:** Often removing "unused" test fixtures — verify all tests pass after cleanup (run full suite, not just changed files).
- [ ] **Workflow backward compat:** Often missing migration doc — verify AGENTS.md and README.md reflect all behavioral changes.
- [ ] **Atomic file writes:** Often using direct `write_text()` for state files — verify write-then-rename for `meta.json`, `ocr-queue.json`, `frontmatter` updates.
- [ ] **Windows encoding:** Often untested on Chinese Windows locale — verify `UnicodeEncodeError` doesn't occur on Chinese filenames/paths with `print()` or logging.
- [ ] **Test still capturing stdout:** Often silently passing because `pytest` captures output — verify with `pytest -s` (no capture) that output doesn't duplicate or miss.

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Circular import from `_utils.py` | LOW | Revert `_utils.py` to leaf-only imports. Use lazy function-level imports for cross-worker deps. Run `pytest --collect-only` to verify. |
| Logging duplicate handlers | LOW | Remove `basicConfig` from all workers. Add `force=True` to central config call. Verify with `logger.info("test")` appearing exactly once. |
| Pre-commit too slow | LOW | Move slow hooks to CI stage in `.pre-commit-config.yaml`. Developers run `pre-commit install` again. |
| Progress bar garbage in pipes | MEDIUM | Add `--no-progress` flag. Detect `not sys.stderr.isatty()`. Users add `--no-progress` to scripts. |
| Corrupt OCR state from failed retry | MEDIUM | Run `paperforge repair --fix` which detects `processing` state divergence. Add `blocked` state for permanent failures. Users re-set `do_ocr: true` for affected papers. |
| ImportError after dead code removal | MEDIUM | Add re-exports to original modules. Write allowlist for dead code tool. Users may need to update their scripts/aliases. |
| Workflow surprise for existing users | HIGH | Write MIGRATION-v1.4.md BEFORE release. Add opt-in config flag. Support `--legacy-mode` if needed. Communicate changes in release notes. |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Circular imports in shared utils | Phase 1: Shared Utility Extraction | `pytest --collect-only` passes. No `from paperforge.worker` in `_utils.py`. |
| Logging breaks piped output | Phase 2: Logging Integration | `paperforge status | grep ocr` works. Tests pass with and without `-s`. Single handler per logger. |
| Pre-commit too slow/aggressive | Phase 3: Pre-Commit Hooks | `time pre-commit run --all-files` <5s total. No false positives on test fixtures. |
| Progress bars break piping | Phase 4: Progress Indicators | `paperforge ocr --no-progress` works. Non-TTY output is clean text. Windows PowerShell tested. |
| OCR retry corrupts state | Phase 5: Retry/Backoff | Simulated network failure test. `meta.json` integrity after crash. No zombie `processing` records. |
| Dead code removal breaks compatibility | Phase 6: Dead Code Cleanup | All 203 existing tests pass. `paperforge selection-sync` still works (with deprecation warning). |
| Workflow changes confuse users | All phases (continuous) | MIGRATION-v1.4.md complete. AGENTS.md updated. Opt-in config gates new behavior. |

---

## Sources

- Python's import system and circular dependencies: https://dev.to/kaushikcoderpy/python-project-structure-imports-circular-dependencies-syspath-2026-4904 (HIGH confidence)
- structlog structured logging best practices: https://structlog.readthedocs.io/en/stable/logging-best-practices.html (HIGH confidence)
- Python logging migration patterns: https://medium.com/@dhruvshirar/structured-logging-in-python (MEDIUM confidence)
- Pytest monkeypatching module globals: https://mathspp.com/blog/til/patching-module-globals-with-pytest (HIGH confidence)
- Pytest fixtures and monkeypatch docs: https://docs.pytest.org/en/stable/how-to/monkeypatch.html (HIGH confidence)
- Rich on Windows piping issues: https://github.com/Textualize/rich/issues/3082 (MEDIUM confidence), https://github.com/Textualize/rich/issues/3437 (MEDIUM confidence)
- Tenacity retry library: https://tenacity.readthedocs.io/en/stable (HIGH confidence)
- Pre-commit hooks breaking CI: https://tildalice.io/precommit-hooks-break-ci-fixes/ (MEDIUM confidence)
- Pre-commit hooks vs CI: https://tildalice.io/pre-commit-hooks-vs-ci-when-to-skip-local-checks/ (MEDIUM confidence)
- Dead code detection in Python: https://github.com/sen-ltd/deadcode-py (MEDIUM confidence)
- Atomic file writes in Python: Standard POSIX pattern (write to tempfile, rename) — multiple official Python docs references (HIGH confidence)
- PaperForge codebase audit (2026-04-25): Direct analysis of all 7 worker modules, cli.py, config.py, test files, and inter-module import graph (HIGH confidence, first-hand observation)

---

*Pitfalls research for: PaperForge Lite v1.4 — adding shared utilities, logging, pre-commit, and UX improvements*
*Researched: 2026-04-25*
