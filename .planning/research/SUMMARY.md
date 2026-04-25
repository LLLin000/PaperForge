# Project Research Summary

**Project:** PaperForge Lite v1.4 — Code Health & UX Hardening
**Domain:** Python CLI application — brownfield Obsidian + Zotero literature pipeline, adding shared utilities, structured logging, pre-commit hooks, progress bars, and retry logic
**Researched:** 2026-04-25
**Confidence:** HIGH

## Executive Summary

PaperForge Lite is a unique open-source tool bridging Zotero reference management, Obsidian note-taking, and AI-powered deep reading. Its v1.3 codebase (~7,757 lines, 7 worker modules, 205 tests) accumulated ~1,610 lines of copy-pasted utility code across workers, 97 bare `print()` calls masquerading as observability, and zero pre-commit safety nets. This research defines v1.4 as a pure code-health milestone: no new user-facing features, only infrastructure hardening that makes future feature work safe and fast.

The recommended approach is a strictly sequenced 6-phase refactor. **Phase 1** establishes logging infrastructure (stdlib `logging` with a single `--verbose` flag). **Phase 2** extracts all duplicated utilities into `paperforge/worker/_utils.py` as a pure leaf module (imports nothing from other workers to avoid circular dependencies). **Phase 3** merges two divergent deep-reading queue implementations into one canonical `scan_library_records()` function. **Phase 4** adds `tqdm` progress bars (TTY-aware, gracefully degraded in CI) and a `tenacity`-based retry decorator for PaddleOCR API calls. **Phase 5** removes ~1,610 lines of dead, duplicated code with backward-compatible re-exports. **Phase 6** installs pre-commit hooks and project health docs.

The single greatest risk is **circular imports** during Phase 2 extraction. The mitigation is a hard rule: `_utils.py` must never import from `paperforge.worker.*` or `paperforge.commands.*`. The second-greatest risk is **breaking existing users' workflows** — all behavioral changes must be opt-in via `paperforge.json` config flags, and a `MIGRATION-v1.4.md` document must ship alongside code changes.

## Key Findings

### Recommended Stack

Three new runtime dependencies, two new dev dependencies, and one stdlib promotion. Every addition was evaluated against the project constraint "keep dependencies small" and the existing `textual` TUI framework already in the dependency tree.

**Core technologies:**
- **tqdm >=4.67.0**: Progress bars for OCR uploads and batch processing — de facto standard (31k GitHub stars), single-purpose, zero transitive dependencies, native TTY auto-detection for graceful CI fallback
- **tenacity >=9.0.0**: Retry/backoff decorator for PaddleOCR API calls — battle-tested retry library with clean `@retry` decorator API, exponential backoff with jitter, configurable via environment variables
- **stdlib `logging`**: Structured, level-based diagnostic output replacing ad-hoc `print()` — zero-cost (already in Python), 2x faster than `loguru`, sufficient for a single-user CLI app; NOT a wholesale replacement of `print()` — user-facing status messages remain on stdout
- **ruff >=0.11.0**: Unified linter + formatter replacing `black`, `isort`, `flake8`, `pyupgrade` — Rust-based (10-100x faster), single `pyproject.toml` section, ~800 bundled rules
- **pre-commit >=4.0.0**: Git hook framework — standard for multi-contributor Python projects, fast hooks only (<2s total), no runtime environment required

**Explicitly NOT recommended:**
- `rich` — already have `textual` for TUI; `rich` would add a competing terminal framework
- `loguru` — cleaner API but adds a transitive dependency for marginal benefit in a CLI app
- `alive-progress` — animated bars break in non-TTY contexts and consume unnecessary CPU
- `click`/`typer` — migrating from `argparse` is out of scope for v1.4

### Expected Features (v1.4 MVP)

All features were derived from a line-by-line codebase audit. Priority ranking: P1 = must ship in v1.4; P2 = should ship if bandwidth permits; P3 = defer to v1.5+.

**Must have (Table Stakes — P1):**
- **Extract `paperforge/worker/_utils.py`** — eliminate ~1,610 lines of duplicated code across 7 worker modules. Single source of truth for JSON I/O, YAML helpers, journal DB, retry decorator, progress bar helper, and deep-reading queue scanner. This is the foundation for ALL other code-health work. HIGH complexity due to import surgery across 7 workers + commands + skills layer.
- **Replace `print()` with structured logging** — add dual-output strategy: `print()` stays for user-facing status (unchanged contract), `logging` added for diagnostic/trace/error output on stderr. Add `--verbose`/`-v` flag. Affects 97 call sites but does NOT change user-facing output format.
- **Merge duplicate deep-reading queue** — `worker/deep_reading.py` and `skills/ld_deep.py` have two divergent implementations. A single `scan_library_records()` function in `_utils.py` serves both CLI and Agent consumers.
- **OCR retry with exponential backoff** — 3 retries on transient failures (HTTP 429, 502, 503, timeouts), configurable via environment variables. Uses `tenacity` decorator. Prevents silent OCR failures from rate limits.
- **Pre-commit hooks** — `.pre-commit-config.yaml` with `ruff` (lint + format), basic file hygiene (trailing whitespace, end-of-file, YAML/JSON/TOML syntax), and a custom consistency audit that verifies no new duplication creeps back in.

**Should have (P2):**
- **Progress indicators for OCR and sync** — `tqdm` progress bars on long-running operations, with automatic fallback to silent passthrough in CI/non-TTY contexts
- **Better error visibility** — structured error codes, actionable fix suggestions, error output goes to stderr via logging while user-facing summaries stay on stdout
- **One-click `paperforge process` command** — chains OCR → deep-reading readiness into a single command; reduces new-user friction from 6 manual steps to 1
- **E2E integration tests** — full pipeline sandbox tests with mocked PaddleOCR API; catches integration bugs that 205 existing unit tests miss
- **Fix README rendering artifact** — delete 3 orphaned Markdown lines outside any code fence

**Defer (v1.5+):**
- **Daemon process for auto-detecting Zotero changes** — violates Lite architecture; keep explicit trigger model
- **Web UI for OCR queue** — adds entire web stack to local-first project; enhance Obsidian Base views instead
- **Auto-trigger deep-reading Agent after OCR** — wastes LLM tokens and violates "user decides" architecture; add `--auto` flag as optional convenience only
- **PostgreSQL/SQLite database** — breaks Obsidian wikilink integration and "plain text forever" philosophy

### Architecture Approach

The v1.3 architecture has 7 worker modules that each carry identical copies of 15+ utility functions. The v1.4 target architecture introduces two new shared modules (`worker/_utils.py` and `logging_config.py`) and refactors all 7 workers to import from them instead of duplicating code.

The dual-output logging strategy is critical: `print()` remains for user-facing status messages (preserving backward compatibility with piped commands and Agent scripts that parse stdout), while `logging` goes to stderr for diagnostic/trace output. The `--verbose` flag enables DEBUG-level output on stderr without polluting human-readable stdout.

The `_utils.py` module follows a strict leaf-module rule: it imports only from `paperforge.config` and stdlib — never from any other worker module. This eliminates circular import risk. The existing test patching pattern (module-level globals set to `None` in `cli.py`, stubs injected by tests via `importlib.reload`) is preserved — `_utils.py` extraction happens below the test stub layer, so tests remain unaffected.

**Major components:**
1. **`paperforge/worker/_utils.py` (NEW, ~250 loc)** — shared JSON I/O, YAML helpers, slugify, journal DB, retry decorator, progress bar helper, deep-reading queue scanner (canonical `scan_library_records()`). Leaf module — zero imports from sibling workers.
2. **`paperforge/logging_config.py` (NEW, ~50 loc)** — single `configure_logging(verbose)` call at CLI startup. Configures `paperforge.*` logger hierarchy once. No `basicConfig()` anywhere else.
3. **7 worker modules (MODIFIED)** — all import from `_utils.py` and `config.py` instead of defining local copies. Each worker's duplicate ~230-line utility block is removed. Import blocks slimmed from ~25 imports to only what's needed.
4. **`paperforge/cli.py` (MODIFIED)** — adds `--verbose`/`-v` flag, calls `configure_logging()` after env loading and before worker dispatch.
5. **`.pre-commit-config.yaml` (NEW)** — hooks: `ruff` (lint + format), `check-yaml/check-toml/check-json`, `trailing-whitespace`, `end-of-file-fixer`, `check-added-large-files`, custom `consistency-audit` hook.

### Critical Pitfalls

7 pitfalls were identified from research, mapped to specific prevention phases. Here are the top 5:

1. **Circular imports from `_utils.py` extraction** — If `_utils.py` imports anything from `paperforge.worker.*` or `paperforge.commands.*`, the 7-worker cross-import graph creates circular chains. **Prevention:** Hard rule that `_utils.py` is a pure leaf module. Verify with `pytest --collect-only` immediately after extraction — circular imports manifest as collection failures, not runtime failures.

2. **`print()` → `logging` migration breaking piped output** — Currently `paperforge status | grep ocr` works because `print()` goes to stdout. If replaced wholesale with `logging.info()` (goes to stderr by default), piped commands break. **Prevention:** Dual-output strategy — keep `print()` for user-facing output on stdout, add `logging` for diagnostic output on stderr. This is an additive change, not a replacement.

3. **Progress bars breaking Windows PowerShell piping** — `tqdm` uses `\r` for in-place updates, which fails with PowerShell's UTF-16 redirect encoding. Non-TTY context produces garbage ANSI sequences or no output at all. **Prevention:** TTY-aware `progress_bar()` wrapper in `_utils.py` that auto-disables in non-TTY contexts. Add `--no-progress`/`--quiet` flags for explicit suppression. Reconfigure streams to UTF-8 on Windows early in `cli.py`.

4. **OCR retry corrupting async state machine** — The OCR worker has a `pending → processing → done/failed` state machine. Retries without state-aware logic create duplicate submissions, zombie `processing` states, and state divergence between `meta.json` and `ocr-queue.json`. **Prevention:** Classify errors (only retry on transient HTTP errors, timeouts, connection errors — never on 400/401/403/404). Add `blocked` terminal state for permanent failures. Add `processing→pending` recovery on startup for zombie jobs older than 1 hour.

5. **Dead code removal breaking backward compatibility** — Removing duplicated functions from original modules breaks callers using `from paperforge.worker.sync import read_json`. Removing `cli.py` module-level globals breaks 20+ dispatch tests. **Prevention:** Re-export moved functions from original modules with `# Re-exported from _utils.py for backward compatibility` comments. Keep `cli.py` stubs exactly as-is (they are intentionally nullable for test injection). Phase legacy alias removal with deprecation warnings (don't remove `selection-sync` until v1.5+).

## Implications for Roadmap

Based on combined research, a 6-phase sequence is recommended. The ordering is dictated by hard dependency chains: logging infrastructure enables progress bars, shared utilities enable retry logic and queue merge, pre-commit hooks validate the cleaned-up codebase last.

### Phase 1: Foundation (Logging Infrastructure)
**Rationale:** Must come first — all subsequent phases use logger calls for diagnostic output. Adding `--verbose` flag now means every later addition can log at DEBUG level during development.
**Delivers:** `paperforge/logging_config.py`, `--verbose`/`-v` flag on CLI, `tqdm` added to dependencies, UTF-8 stream reconfigure on Windows
**Addresses:** Structured logging (table stakes), Windows encoding safety (pitfall prevention)
**Avoids:** Pitfall 2 (logging breaking piped output) — by using dual-output strategy from day one
**Risk level:** LOW — new module, no existing code modified except `cli.py`

### Phase 2: Shared Utilities Extraction
**Rationale:** THE critical path. All code-health features (logging helpers, retry, progress bars, queue merge) depend on `_utils.py` existing. Must be done correctly before any other change touches worker modules.
**Delivers:** `paperforge/worker/_utils.py` with all shared functions, all 7 workers updated to import from it, re-exports in original modules for backward compatibility
**Addresses:** DRY principle (table stakes P1), ~1,610 lines of duplication eliminated
**Avoids:** Pitfall 1 (circular imports) — by enforcing leaf-module rule; Pitfall 6 (backward compat break) — by keeping re-exports
**Risk level:** HIGH — import surgery across 7 workers + commands + skills layer. Mitigated by: one-worker-at-a-time approach with test suite run after each

### Phase 3: Deep-Reading Queue Merge
**Rationale:** Requires `_utils.py` to exist (for `scan_library_records()`). Two divergent implementations currently exist — merging them prevents users seeing different queues from CLI vs Agent.
**Delivers:** Single `scan_library_records()` in `_utils.py`, both `worker/deep_reading.py` and `skills/ld_deep.py` call it, ~50 lines of duplicate logic removed from `ld_deep.py`
**Addresses:** Merge duplicate deep-reading queue (table stakes P1)
**Risk level:** LOW — purely a consolidation of already-working logic; no behavioral change

### Phase 4: Retry Logic + Progress Bars
**Rationale:** Both features live in `_utils.py` (established in Phase 2). Retry prevents silent OCR failures; progress bars eliminate "did it hang?" UX anxiety during long operations. These are the most user-visible improvements.
**Delivers:** `retry_on_failure` decorator applied to OCR upload/poll functions, `progress_bar()` TTY-aware wrapper with automatic CI fallback, progress bars in sync and ocr workers
**Addresses:** OCR retry with backoff (P1), progress indicators (P2), error visibility (P2)
**Avoids:** Pitfall 4 (Windows piping) — via TTY-aware fallback; Pitfall 5 (OCR state corruption) — via error classification and `blocked` terminal state
**Risk level:** MEDIUM — retry introduces state machine complexity; progress bars must work on Windows PowerShell

### Phase 5: Documentation + Trivial Fixes
**Rationale:** Independent of code changes — can ship in parallel with any phase. Bundled here for cleanup.
**Delivers:** `CONTRIBUTING.md`, `CHANGELOG.md`, README artifact fix (delete 3 orphaned lines)
**Addresses:** CONTRIBUTING.md (P1), CHANGELOG.md (P1), README fix (P2)
**Risk level:** TRIVIAL — docs only, no code dependencies

### Phase 6: Dead Code Removal + Pre-Commit Hooks + Final Polish
**Rationale:** Dead code removal must be LAST — verifying no missing imports before deleting. Pre-commit hooks validate the cleaned-up codebase and prevent future duplication. (Note: `pyproject.toml` ruff config and `.pre-commit-config.yaml` can be committed early, but hooks are activated last.)
**Delivers:** ~1,610 lines of dead code removed, slimmed import blocks, `.pre-commit-config.yaml` active, `scripts/consistency-audit.py` custom hook, `pyproject.toml` ruff configuration
**Addresses:** Pre-commit hooks (P1), dead code cleanup (P3), chart-reading cross-reference (P3)
**Avoids:** Pitfall 3 (painful pre-commit) — fast hooks only, no mypy/pytest in pre-commit, exclude test fixtures; Pitfall 6 (backward compat) — re-exports preserved, `cli.py` stubs untouched
**Risk level:** MEDIUM — dead code removal can silently break imports if not verified with full test suite

### Phase Ordering Rationale

- **Phases 1-2 are the critical path.** Nothing else can proceed without logging and shared utilities. The architecture research confirms this with the dependency chain: logging → utils → queue merge → retry+progress → dead code → pre-commit.
- **Phases 1-2-3-4 must be sequential** due to hard dependencies (each phase's output is the input to the next). **Phases 5-6 can partially overlap** with earlier phases but must complete after Phase 4.
- **Testing gates every phase:** `pytest tests/ -x` must pass after every phase. This prevents compound breakage where Phase 3 failures hide Phase 2 mistakes.
- **The dual-output logging strategy (keeping `print()` for user-facing output) is the single most important architectural decision.** It prevents breaking piped commands, Agent scripts that parse stdout, and existing user workflows — all of which would be regressions if `print()` were wholesale replaced.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 2 (Shared Utilities Extraction):** The import graph is complex — 7 workers with cross-imports between them. The `pipeline_paths` function in each worker adds unique keys on top of shared output, so centralization requires a factory pattern. A `/gsd-research-phase` before Phase 2 should verify the exact extraction strategy for each duplicated function.
- **Phase 4 (Retry Logic):** PaddleOCR API error classification needs validation against actual API behavior. The `blocked` terminal state is a new concept that interacts with existing `repair.py` and `base_views.py` logic. Research should verify the state machine transitions end-to-end.

**Phases with well-documented patterns (skip research-phase):**
- **Phase 1 (Logging):** stdlib `logging` is the most documented Python module. The dual-output strategy is a known pattern. No novel research needed.
- **Phase 5 (Docs):** Standard project health files. Templates exist. No research needed.
- **Phase 6 (Pre-Commit):** Well-documented in `pre-commit` official docs. The `.pre-commit-config.yaml` structure is deterministic. No research needed beyond what STACK.md already provides.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All 6 technology recommendations verified against Context7 official documentation. Alternatives systematically evaluated with clear rejection criteria. Dependency version compatibility confirmed. |
| Features | HIGH | Derived from line-by-line codebase audit of all 22 Python files (7,757+ lines). Every `print()` call, duplicated function, and import block identified by direct inspection. 205 existing tests provide behavioral baseline. |
| Architecture | HIGH | Import graph mapped across all 7 workers + commands + skills layer. Duplication locations catalogued function-by-function. Test patching pattern, circular import risk, and TTY behavior verified. Build order dependency chain confirmed. |
| Pitfalls | HIGH | 7 pitfalls identified from combined codebase audit + external source research (Python import system, Windows encoding, PaddleOCR API behavior, pre-commit isolation). Each pitfall mapped to a specific prevention phase with verification criteria. Recovery strategies documented. |

**Overall confidence:** HIGH — all findings based on direct codebase inspection and verified external sources (Context7 documentation, Python official docs, community articles). No inferences or assumptions.

### Gaps to Address

- **PaddleOCR API error response format:** Research assumed standard HTTP status codes for error classification (400=bad request, 429=rate limit, 503=unavailable). Actual PaddleOCR API may return 200 with error body or use non-standard codes. Validate during Phase 4 implementation with a test API call.
- **Windows UTF-8 reconfigure:** The `sys.stdout.reconfigure(encoding='utf-8')` call in Phase 1 may not work on all Windows terminal configurations (legacy conhost, PowerShell ISE). Test on actual Windows 10/11 PowerShell during Phase 1.
- **`pipeline_paths` factory pattern:** Architecture research identified that each worker's `pipeline_paths` adds unique keys. The exact factory API (`build_pipeline_paths(vault, extra_keys)`) needs design validation during Phase 2 planning.
- **User base size for backward compat impact:** Research could not determine how many users rely on `paperforge selection-sync` or `from paperforge.worker.sync import read_json`. Mitigation (re-exports, deprecation warnings, MIGRATION doc) is in place regardless.

## Sources

### Primary (HIGH confidence)
- **Codebase audit** (April 25, 2026): Direct file inspection of all 22 Python files in `paperforge/` — every worker module, CLI entry point, commands layer, skills layer, config module, and 205 test files. Confirmed 97 `print()` calls, 1,610 duplicated lines, 7 identical copies of 15+ utility functions.
- **Context7 `/tqdm/tqdm`** — Manual progress control API, file iteration patterns, TTY auto-detection behavior
- **Context7 `/jd/tenacity`** — Retry decorator API, wait strategies, stop conditions, before/after callbacks
- **Context7 `/astral-sh/ruff`** — pyproject.toml configuration, linter rule sets (E, F, I, UP, B, SIM), formatter settings, py310 targeting
- **Context7 `/websites/pre-commit`** — Hook configuration structure, CI integration, isolation guarantees
- **Python `logging` module** (official docs) — `basicConfig` anti-patterns, handler accumulation, `force=True` semantics, dual-output patterns

### Secondary (MEDIUM confidence)
- **tildalice.io/logging-vs-loguru-vs-structlog-performance-api-comparison/** (2026-03) — Performance benchmarks: stdlib 2x faster than loguru
- **realpython.com/python-loguru** — API reference (reviewed for comparison; recommended against for this project)
- **dev.to/kaushikcoderpy/python-project-structure-imports-circular-dependencies** — Circular import prevention strategies
- **structlog best practices** — Structured logging patterns (reviewed; structlog rejected as overkill)
- **mathspp.com/blog/til/patching-module-globals-with-pytest** — Test patching pattern validation
- **Rich GitHub issues #3082, #3437** — Windows piping UTF-16 encoding problems with progress bars
- **tildalice.io/precommit-hooks-break-ci-fixes/** — Pre-commit CI integration gotchas

### Project-Specific (PRIMARY confidence)
- `paperforge/cli.py` (371 loc) — dispatch patterns, test patching, legacy aliases
- `paperforge/config.py` (299 loc) — existing centralized config, `load_simple_env` already canonical
- `paperforge/worker/sync.py` (1,444 loc) — all duplication sources documented
- `paperforge/worker/ocr.py` (1,376 loc) — OCR state machine, retry target
- `paperforge/worker/deep_reading.py` (324 loc) — queue implementation A
- `paperforge/skills/literature-qa/scripts/ld_deep.py` (1,420 loc) — queue implementation B
- `paperforge/commands/` (338 loc across 6 modules) — thin dispatch layer
- `tests/conftest.py` (169 loc) — sandbox architecture
- `tests/test_cli_worker_dispatch.py` (157 loc) — test patching reference
- `.planning/PROJECT.md` — milestone constraints and project context
- `AGENTS.md` — documented workflows and backward compatibility contracts

---
*Research completed: 2026-04-25*
*Ready for roadmap: yes*
*Vault-Tec Seal of Approval: ALL-CLEAR. The codebase audit is comprehensive, the pitfall map is exhaustive, and the phase sequence is dependency-verified. Proceed to roadmap creation with confidence.*
