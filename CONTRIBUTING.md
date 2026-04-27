# Contributing to PaperForge Lite

Thank you for your interest in contributing to PaperForge Lite! This document provides setup instructions, workflow guidelines, and code conventions to help you get started.

---

## Development Setup

```bash
# Clone the repository
git clone https://github.com/LLLin000/PaperForge.git
cd PaperForge

# Editable install with test dependencies
pip install -e ".[test]"

# Verify installation
python -m paperforge --version
```

### Requirements

- Python 3.10+
- Zotero + Better BibTeX plugin (for end-to-end testing)
- Obsidian (for Base view generation)
- PaddleOCR API Key (for OCR pipeline — configure in `.env`)

---

## Pre-commit Hooks

Before committing, install the pre-commit hooks to ensure code quality:

```bash
pip install pre-commit
pre-commit install
```

Hooks are configured in `.pre-commit-config.yaml` and include:

- **Ruff lint** (`ruff check --fix`) — catches common errors and style issues
- **Ruff format** (`ruff format`) — enforces consistent code formatting
- **check-yaml** — validates YAML file syntax
- **check-toml** — validates TOML file syntax
- **end-of-file-fixer** — ensures files end with a single newline
- **trailing-whitespace-fixer** — removes trailing whitespace
- **Consistency audit** (`scripts/consistency_audit.py`) — detects duplicate utility functions across modules

> **Note:** Pre-commit hooks run automatically on `git commit`. Do not bypass them. If a hook fails, fix the issue and re-commit. The Ruff configuration in `pyproject.toml` suppresses `E501` (line-too-long) and pre-existing simplifications via `per-file-ignores` — these are not blockers.

---

## Test Workflow

```bash
# Run all tests, stop on first failure
pytest tests/ -x

# Verbose output
pytest tests/ -v

# Filter by keyword (e.g., OCR-related tests)
pytest tests/ -k "ocr"

# Run with coverage report
pytest tests/ --cov

# Collect tests only (no execution) — useful for import validation
pytest tests/ --collect-only
```

### Test Requirements

- **All tests must pass before merging.** The current baseline is 203+ tests, 0 failures, 0 errors (2 pre-existing skips for PDF-dependent tests).
- **Lint must pass:** `ruff check . && ruff format --check .`
- Do not introduce new test failures or lint violations.
- Tests must not make live API calls (PaddleOCR, etc.). Use sandbox fixtures in `tests/sandbox/`.

### Test Structure

Tests are in `tests/` with a shared `conftest.py` providing fixtures. The `tests/sandbox/` directory contains generated deterministic fixtures for OCR, Zotero exports, and vault layouts. Fixture generation scripts are in `tests/sandbox/generate_*.py` — run these only when fixtures need updating.

---

## Architecture Overview

PaperForge Lite uses a **two-layer design**:

```
Worker Layer (automated, deterministic, CLI-triggered)
    paperforge/worker/
    ├── _utils.py        — Leaf module: shared utilities (read_json, write_json, etc.)
    ├── sync.py          — Zotero sync (selection-sync, index-refresh)
    ├── ocr.py           — OCR pipeline (upload, poll, postprocess)
    ├── repair.py        — State and path repair
    ├── status.py        — Doctor and status commands
    ├── deep_reading.py  — Deep-reading queue management
    ├── base_views.py    — Obsidian Base view generation
    ├── update.py        — Auto-update system
    ├── _progress.py     — Progress bar utilities
    └── _retry.py        — Retry with backoff utilities

Agent Layer (interactive, reasoning-driven, user-triggered)
    paperforge/skills/literature-qa/
    ├── scripts/ld_deep.py      — /pf-deep implementation
    ├── prompt_deep_subagent.md  — Agent prompt for deep reading
    └── chart-reading/           — 14 chart-type review guides
```

### Key Architecture Rules

1. **`_utils.py` is a leaf module** — imports only from stdlib and `paperforge/config.py`. Must never import from `paperforge.worker.*` or `paperforge.commands.*`. This prevents circular dependencies.
2. **Worker modules do not import each other directly** — use `_sync.run_selection_sync(vault)` (module-reference pattern) in `ocr.py` to break the sync↔ocr cycle.
3. **Config flows one way:** `paperforge/config.py` → `_utils.py` → worker modules. No reverse imports.
4. **Re-exports preserve backward compatibility:** Moved functions retain `# Re-exported from _utils.py` comments in original modules.

### Key Files

| File | Purpose |
|------|---------|
| `paperforge/config.py` | Path resolution and config loading |
| `paperforge/cli.py` | CLI entry point and command routing |
| `paperforge/__main__.py` | `python -m paperforge` entry point |
| `paperforge.json` | User-facing configuration (paths, update settings, feature flags) |
| `setup_wizard.py` | Interactive first-time setup |
| `scripts/consistency_audit.py` | Duplicate utility function detection |

---

## Code Conventions

1. **No new `print()` calls in worker modules** — use `logger = logging.getLogger(__name__)` with `logger.info()`, `logger.debug()`, etc. `print()` is reserved for user-facing stdout output in CLI commands (`paperforge/commands/`).

2. **Import shared utilities from `_utils.py`** — do not copy-paste `read_json`, `write_json`, `load_journal_db`, etc. into new modules. If you need a utility, add it to `_utils.py` first.

3. **`_utils.py` is a leaf module** — must never import from `paperforge.worker.*` or `paperforge.commands.*`. Violations cause circular import errors.

4. **Requirement IDs in commit messages** — link commits to requirements using the format: `feat(UX-01): add auto_analyze_after_ocr`. Requirement IDs are tracked in `REQUIREMENTS.md` and `.planning/`.

5. **Pre-commit hooks** run on `git commit` — do not bypass them with `--no-verify`. Fix hook failures rather than skipping them.

6. **Forward slashes in paths** — use `Path.as_posix()` for all path-to-string conversions. This ensures consistent wikilinks regardless of OS.

7. **Structured logging** — use `logging.getLogger(__name__)` at module level. Log levels: `DEBUG` for detailed diagnostics, `INFO` for normal operations, `WARNING` for recoverable issues, `ERROR` for failures.

8. **No live API calls in tests** — all tests must use deterministic sandbox fixtures. Mock external services where necessary.

9. **Type hints** — use `from __future__ import annotations` at the top of new modules for PEP 604-style type hints.

10. **Backward compatibility** — API breaks are unacceptable within a major version. Use function-level imports and re-exports when refactoring.

---

## Pull Request Process

1. Ensure all tests pass and lint is clean.
2. Update CHANGELOG.md under `[Unreleased]` with the changes.
3. Update documentation (AGENTS.md, command docs) if user-facing behavior changes.
4. Create a pull request with a clear description of changes and motivation.
5. Reference requirement IDs where applicable.

---

## Getting Help

- Open an issue on GitHub: https://github.com/LLLin000/PaperForge/issues
- Run `paperforge doctor` for system diagnostics
- Review `docs/INSTALLATION.md` and `docs/ARCHITECTURE.md` for detailed setup and design docs

---

*Thank you for contributing to PaperForge Lite — Building a better literature workflow, underground!*
