# Stack Research — v1.4 Code Health Additions

**Domain:** Python CLI application (Obsidian + Zotero literature pipeline)
**Researched:** 2026-04-25
**Confidence:** HIGH

## Recommended Stack

### Core Technology Additions (New Dependencies)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| tqdm | >=4.67.0 | Progress bars for OCR uploads and long-running file operations | De facto standard (31k GitHub stars). Single-purpose, zero transitive deps, native file-size iteration support. Perfect for OCR PDF upload progress (`unit='B', unit_scale=True`). Does NOT add a competing terminal framework — `textual` handles TUI, `tqdm` handles progress only. |
| tenacity | >=9.0.0 | Retry/backoff for network operations (PaddleOCR API) | De facto Python retry library (Apache 2.0). Clean decorator API: `@retry(stop=stop_after_attempt(3), wait=wait_exponential(...), retry=retry_if_exception_type(...))`. Supports exponential backoff with jitter, before/after callbacks for reconnection logic. |
| ruff | >=0.11.0 | Linting + formatting (replaces black, isort, flake8, pyupgrade) | Ecosystem standard in 2025-2026. Written in Rust — 10-100x faster than legacy tools. Single `pyproject.toml` section replaces 4 separate tools. First-party `[tool.ruff]` and `[tool.ruff.lint]` config. Built-in isort rules (`I`), pyupgrade rules (`UP`), flake8-bugbear (`B`), flake8-simplify (`SIM`). |

### Supporting Libraries (Zero-Add Dependencies)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| stdlib `logging` | — (Python 3.10+) | Structured, level-based logging replacing all `print()` calls | Primary logging mechanism across all 7 worker modules. Import `logging`, call `logging.getLogger(__name__)`. One-time ~30-line config in `paperforge/logging_config.py`. |
| stdlib `pathlib` | — (Python 3.10+) | Cross-platform path construction | Already heavily used. Reinforce as the sole path primitive — no `os.path` backsliding. |
| `pre-commit` | >=4.0.0 | Git pre-commit hook framework | Installed as dev dependency. `.pre-commit-config.yaml` with ruff + trailing-whitespace + check-yaml hooks. Run via `pre-commit install` once per clone. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `pre-commit` | Git hook automation | `.pre-commit-config.yaml` at repo root. CI-compatible: `pre-commit run --all-files` |
| `ruff` (as formatter) | Code formatting | Configure `[tool.ruff.format]` with `quote-style = "double"`, `line-length = 100` |
| `ruff` (as linter) | Static analysis | Select rules: `E`, `F`, `I`, `UP`, `B`, `SIM`. Ignore `E501` (handled by formatter). Target `py310`. |
| `pytest` (existing) | Test runner | Already in `[project.optional-dependencies] test`. Keep it there. |

## Installation

```bash
# Core runtime dependencies (added to pyproject.toml dependencies)
pip install "tqdm>=4.67.0" "tenacity>=9.0.0"

# Dev dependencies (added to pyproject.toml [project.optional-dependencies] dev)
pip install "ruff>=0.11.0" "pre-commit>=4.0.0"

# After install, initialize pre-commit hooks once
pre-commit install
```

## Updated pyproject.toml Dependencies Section

```toml
[project]
dependencies = [
    "requests>=2.31.0",
    "pymupdf>=1.23.0",
    "pillow>=10.0.0",
    "textual>=0.47.0",
    "tqdm>=4.67.0",
    "tenacity>=9.0.0",
]

[project.optional-dependencies]
test = [
    "pytest>=7.4.0",
]
dev = [
    "ruff>=0.11.0",
    "pre-commit>=4.0.0",
]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "F",      # Pyflakes
    "I",      # isort (import ordering)
    "UP",     # pyupgrade (modern syntax)
    "B",      # flake8-bugbear
    "SIM",    # flake8-simplify
]
ignore = ["E501"]  # line-length handled by formatter

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]  # re-exports are intentional
"tests/*" = ["S101"]      # assert is fine in tests
```

## .pre-commit-config.yaml Structure

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=500']

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.11.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Progress bar | tqdm | rich.progress | Already have `textual` for TUI wizard. Adding `rich` (~2MB) duplicates terminal-UI capability. tqdm is single-purpose, 30x smaller, zero transitive deps. |
| Progress bar | tqdm | alive-progress | Animated progress bars look flashy but consume CPU and break in non-TTY contexts (CI, redirected output). tqdm auto-detects TTY and degrades gracefully. |
| Logging | stdlib `logging` | loguru | loguru (21k stars) has a cleaner API but adds a transitive dependency. Project constraint: "Keep dependencies small." For a CLI app doing file I/O (not a web service), zero-cost stdlib logging is sufficient. ~30 lines of config replaces `print()` with `logging.info()/warning()/error()`. The 2x performance advantage of stdlib matters when logging during file-heavy operations. |
| Logging | stdlib `logging` | structlog | Processor pipelines and PII masking are overkill for a single-user CLI app. |
| Retry | tenacity | stamina | Less mature, smaller community. Tenacity is battle-tested. |
| Retry | tenacity | backoff | API is less ergonomic (function-based, harder to configure). Tenacity decorator pattern is cleaner. |
| Retry | tenacity | Retry (requests.packages) | Deprecated. Part of urllib3 internals, not a public API. |
| Linting | ruff | flake8 + plugins | Flake8 requires managing a plugin ecosystem. Ruff bundles ~800 rules in one binary. 10-100x faster. |
| Formatting | ruff format | black | Black requires separate install and config. Ruff format is drop-in compatible with Black's style, same config file. |
| Import sorting | ruff (I rules) | isort | isort requires separate install. Ruff's `I` rules match isort behavior exactly. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `rich` (progress or logging) | Already have `textual` for TUI. Adding `rich` would add a second terminal framework with overlapping capability. Dependency bloat violates "keep deps small" constraint. | `tqdm` for progress; `stdlib logging` for output |
| `loguru` | Adds dependency for marginal benefit. Exception locals capture (`diagnose=True`) is the main advantage — useful in web services, unnecessary in CLI. stdlib `logging.exception()` already captures tracebacks. | stdlib `logging` module |
| `click` / `typer` | Project architecture uses `argparse` (documented in ADRs). Migrating CLI framework is out of scope for v1.4 code health milestone. | Keep `argparse` |
| `black` (separate install) | ruff format is drop-in compatible. Two formatters in the pipeline increases maintenance burden. | ruff format |
| `isort` (separate install) | ruff's `I` rules (isort) handle import sorting. Separate tool means separate config and CI step. | ruff's `I` lint rules |
| `flake8` (separate install) | ruff bundles all common flake8 rules. Managing flake8 plugin versions is a separate maintenance burden. | ruff |
| Custom retry loop (manual `while` + `time.sleep`) | Error-prone, hard to test, inconsistent across modules. Tenacity is 0-config for basic cases and fully customizable for edge cases. | tenacity |
| `print()` for status output | No level filtering, no timestamp, no module identification. Untestable — can't assert on log output. | stdlib `logging` |

## Stack Patterns by Variant

**If OCR operation (file upload to PaddleOCR API):**
- Use `tqdm` with `unit='B', unit_scale=True` for upload progress
- Use `tenacity` with `retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError))` and `wait=wait_exponential(multiplier=1, min=4, max=30)`
- Log via `logging.getLogger(__name__).info("Uploading %s...", filename)`

**If worker module needs shared state/config:**
- Import from `paperforge.config`: `load_vault_config`, `paperforge_paths`, `load_simple_env`
- Import from `paperforge.worker._utils`: `read_json`, `write_json`, `read_jsonl`, `write_jsonl`, `load_journal_db`, `lookup_impact_factor`, `STANDARD_VIEW_NAMES`, `get_logger`

**If CI/CD pipeline:**
- `pre-commit run --all-files` as a GitHub Actions step
- `ruff check` and `ruff format --check` for linting verification
- `pytest` for test suite (existing)

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| tqdm >=4.67.0 | Python 3.8+ | Well within project's `>=3.10` requirement |
| tenacity >=9.0.0 | Python 3.8+ | Async support (Tornado, asyncio, Trio) included but unused |
| ruff >=0.11.0 | Python 3.10+ (for `py310` target) | Rust binary, no Python version coupling at runtime |
| pre-commit >=4.0.0 | Python 3.9+ | Framework only — hooks run in their own isolated environments |
| stdlib logging | Python 3.2+ | Core library, present in all Python 3.10+ installations |

## Integration Points with Existing Architecture

### 1. Shared Utilities: `paperforge/worker/_utils.py`

**Functions to extract from 7 duplicated locations into single source:**

| Function | Currently In (# copies) | New Location | Notes |
|----------|------------------------|--------------|-------|
| `read_json(path)` | 7 workers | `_utils.py` | Simple wrapper, but 7 copies |
| `write_json(path, data)` | 7 workers | `_utils.py` | 7 copies |
| `read_jsonl(path)` | 7 workers | `_utils.py` | 7 copies |
| `write_jsonl(path, rows)` | 7 workers | `_utils.py` | 7 copies |
| `_JOURNAL_DB` (module-level cache) | 7 workers | `_utils.py` | Single module-level cache |
| `load_journal_db(vault)` | 7 workers | `_utils.py` | 7 copies |
| `lookup_impact_factor(...)` | 7 workers | `_utils.py` | 7 copies |
| `STANDARD_VIEW_NAMES` (constant) | 7 workers | `_utils.py` | 7 copies (identical frozenset) |
| `load_simple_env(env_path)` | **Already in `paperforge/config.py`** | Workers import from `paperforge.config` | Already canonical — workers just need to stop having their own copies |

**Imports after refactor (each worker module):**
```python
from paperforge.config import load_vault_config, paperforge_paths, load_simple_env
from paperforge.worker._utils import (
    read_json, write_json, read_jsonl, write_jsonl,
    load_journal_db, lookup_impact_factor,
    STANDARD_VIEW_NAMES, get_logger,
)
```

### 2. Structured Logging: `paperforge/logging_config.py`

**New module providing `configure_paperforge_logging(level, log_file)` invoked once at CLI entrypoint:**

```python
# paperforge/logging_config.py (new)
import logging
import sys

FORMAT = "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
DATE_FORMAT = "%H:%M:%S"

def configure_paperforge_logging(
    level: int = logging.INFO,
    log_file: str | None = None,
) -> None:
    root = logging.getLogger("paperforge")
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(FORMAT, DATE_FORMAT))
    root.addHandler(handler)
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(logging.Formatter(FORMAT, DATE_FORMAT))
        root.addHandler(fh)
```

**Worker usage pattern:**
```python
import logging
logger = logging.getLogger(__name__)  # e.g. "paperforge.worker.ocr"

# Replace: print("[INFO] Starting OCR...")
# With:
logger.info("Starting OCR on %d papers...", len(queue))

# Replace: print(f"[ERROR] Failed: {e}")
# With:
logger.error("PaddleOCR upload failed: %s", e)
# Or with traceback:
logger.exception("PaddleOCR upload crashed")
```

### 3. Progress Bars: OCR Worker Integration

```python
from tqdm import tqdm

# PDF upload progress (in ocr.py)
file_size = Path(pdf_path).stat().st_size
with tqdm(total=file_size, unit='B', unit_scale=True,
          unit_divisor=1024, desc=f"Uploading {filename}") as pbar:
    with open(pdf_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            response = session.post(url, data=chunk, ...)
            pbar.update(len(chunk))

# Batch processing progress (in sync.py, ocr.py, deep_reading.py)
for record in tqdm(records, desc="Processing library records",
                   unit="record"):
    process_one(record)
```

### 4. Retry Logic: OCR API Calls

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((
        requests.Timeout, requests.ConnectionError, requests.HTTPError
    )),
    before_sleep=lambda retry_state: logger.warning(
        "Retrying %s (attempt %d/%d) after %.1fs...",
        retry_state.fn.__name__,
        retry_state.attempt_number,
        3,
        retry_state.next_action.sleep,
    ),
)
def upload_to_paddleocr(pdf_path: Path, api_key: str) -> dict:
    ...
```

### 5. Pre-commit: No Code Changes Required

Pre-commit is purely a developer workflow tool. Install once per clone:
```bash
pip install pre-commit  # or pip install -e ".[dev]"
pre-commit install
```
CI integration: add `pre-commit run --all-files` to CI workflow.

## Sources

- `/tqdm/tqdm` (Context7) — Manual progress control, file iteration API, CallbackIOWrapper
- `/jd/tenacity` (Context7) — Retry decorator, wait strategies, stop conditions, before/after callbacks
- `/astral-sh/ruff` (Context7) — pyproject.toml configuration, linter rules, formatter settings, py310 targeting
- `/websites/pre-commit` (Context7) — .pre-commit-config.yaml structure, hook installation
- `/delgan/loguru` (Context7) — API reference (reviewed for comparison; recommended AGAINST for this project)
- `tildalice.io/logging-vs-loguru-vs-structlog-performance-api-comparison/` (2026-03) — Performance benchmarks confirming stdlib 2x faster, loguru better API but adds deps
- `realpython.com/python-loguru` (2025-05) — Loguru tutorial (reviewed for comparison)
- `python.libhunt.com/compare-tqdm-vs-rich` — Community popularity: tqdm 31k stars, rich 55k stars (rich's extra stars mostly from formatting features, not progress bars)
- `paperforge/config.py` (project source) — `load_simple_env` already centralized here; workers still have their own stale copies
- Project grep of 7 worker modules — Confirmed 7x duplication of `read_json`, `write_json`, `read_jsonl`, `write_jsonl`, `load_journal_db`, `lookup_impact_factor`, `STANDARD_VIEW_NAMES`

---

*Stack research for: PaperForge Lite v1.4 Code Health & UX Hardening*
*Researched: 2026-04-25 — all recommendations verified against Context7 official documentation*
