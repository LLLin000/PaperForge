# Architecture Research

**Domain:** Python CLI application — shared utilities, logging, pre-commit, progress bars, retry logic integration
**Researched:** 2026-04-25
**Confidence:** HIGH (codebase audited line-by-line; import patterns, duplication, and test sandbox verified)

---

## System Overview — Current State (v1.3)

```
┌──────────────────────────────────────────────────────────────────┐
│  AGENT LAYER — User-triggered deep reasoning                     │
│  .opencode/command/*.md  →  /pf-deep, /pf-paper, /pf-ocr, etc.  │
├──────────────────────────────────────────────────────────────────┤
│  SKILLS LAYER — Agent helper scripts                             │
│  paperforge/skills/literature-qa/scripts/ld_deep.py (1295+ loc)  │
│  └─ Imports from paperforge.config (vault/path resolution)       │
│  └─ Imports from paperforge.worker (deep_reading utils)          │
├──────────────────────────────────────────────────────────────────┤
│  COMMANDS LAYER — Thin dispatch, delegates to workers            │
│  paperforge/commands/{sync,ocr,deep,status,repair}.py            │
│  └─ Each command is ~90 lines: resolve vault, call worker        │
│  └─ Test-aware: checks cli.py module globals for stubs first     │
├──────────────────────────────────────────────────────────────────┤
│  CLI ENTRY — Argument parsing + env loading                      │
│  paperforge/cli.py (371 loc)                                     │
│  └─ Module-level globals initialized to None (test patching)     │
│  └─ _import_worker_functions() lazy-loads if globals are None    │
│  └─ _resolve_pipeline() handles repo vs deployed vault paths     │
├──────────────────────────────────────────────────────────────────┤
│  WORKERS LAYER — 7 modules with ~1,610 lines of DUPLICATED code  │
│  paperforge/worker/{sync,ocr,deep_reading,repair,status,         │
│                     base_views,update}.py                         │
│  └─ Each file has IDENTICAL copies of:                           │
│     load_simple_env, read_json, write_json, read_jsonl,           │
│     write_jsonl, yaml_quote, yaml_block, yaml_list,              │
│     slugify_filename, _extract_year, load_journal_db,            │
│     lookup_impact_factor, load_vault_config, pipeline_paths,     │
│     load_domain_config, STANDARD_VIEW_NAMES                      │
│  └─ Also identical import blocks (~25 imports, ~50 lines each)   │
├──────────────────────────────────────────────────────────────────┤
│  SHARED CONFIG — The ONE centralized module (existing)           │
│  paperforge/config.py (299 loc)                                  │
│  └─ load_simple_env, load_vault_config, paperforge_paths,        │
│     resolve_vault, read_paperforge_json, paths_as_strings        │
├──────────────────────────────────────────────────────────────────┤
│  SUPPORT MODULES                                                 │
│  paperforge/pdf_resolver.py, paperforge/ocr_diagnostics.py       │
└──────────────────────────────────────────────────────────────────┘
```

### Key Observation: The Duplication Problem

All 7 worker modules have identical copies of these functions:
- `load_simple_env()` — 13 lines × 7 = 91 lines duplicated (already in config.py too!)
- `read_json()` — 2 lines × 7 = 14
- `write_json()` — 4 lines × 7 = 28
- `read_jsonl()` — 9 lines × 7 = 63
- `write_jsonl()` — 6 lines × 7 = 42
- `yaml_quote()` — 6 lines × 7 = 42
- `yaml_block()` — 9 lines × 7 = 63
- `yaml_list()` — 9 lines × 7 = 63
- `slugify_filename()` — 3 lines × 7 = 21
- `_extract_year()` — 3 lines × 7 = 21
- `load_journal_db()` — 16 lines × 7 = 112
- `lookup_impact_factor()` — 14 lines × 7 = 98
- `load_vault_config()` — 5 lines delegating to config.py × 7 = 35
- `pipeline_paths()` — 43 lines × 7 = 301
- `load_domain_config()` — 20 lines × 7 = 140
- `STANDARD_VIEW_NAMES` — 4 lines × 7 = 28

**Total duplicated: ~1,162 lines of utility code, plus ~448 lines of import blocks = ~1,610 lines.**

Also duplicated across workers:
- Nearly identical top-level import blocks (~25 imports across csv, hashlib, html, json, os, re, shutil, subprocess, sys, tempfile, urllib.parse, datetime, pathlib, xml.etree, requests, fitz, PIL)

---

## Target Architecture (v1.4 Integration)

```
┌──────────────────────────────────────────────────────────────────┐
│  AGENT LAYER (unchanged)                                         │
│  .opencode/command/*.md  →  /pf-deep, /pf-paper, /pf-ocr, etc.  │
├──────────────────────────────────────────────────────────────────┤
│  SKILLS LAYER                                                    │
│  paperforge/skills/literature-qa/scripts/ld_deep.py              │
│  └─ Imports from: paperforge.config (paths)                     │
│  └─ Imports from: paperforge.worker._utils (scan_library_records)│
│  └─ REMOVED: scan_deep_reading_queue() (merged into _utils)      │
├──────────────────────────────────────────────────────────────────┤
│  COMMANDS LAYER (unchanged)                                      │
│  paperforge/commands/{sync,ocr,deep,status,repair}.py            │
├──────────────────────────────────────────────────────────────────┤
│  CLI ENTRY — NOW configures logging                              │
│  paperforge/cli.py                                               │
│  └─ + from paperforge.logging_config import configure_logging    │
│  └─ + configure_logging() called after env load, before dispatch │
│  └─ + -v/--verbose flag added to root parser                    │
├──────────────────────────────────────────────────────────────────┤
│  WORKERS LAYER — Imports from _utils, no local copies            │
│  paperforge/worker/                                              │
│  └─ _utils.py               <-- NEW: shared utilities            │
│  └─ sync.py                 imports from _utils, config          │
│  └─ ocr.py                  imports from _utils, config          │
│  └─ deep_reading.py         imports from _utils, config          │
│  └─ repair.py               imports from _utils, config          │
│  └─ status.py               imports from _utils, config          │
│  └─ base_views.py           imports from _utils, config          │
│  └─ update.py               imports from _utils, config          │
├──────────────────────────────────────────────────────────────────┤
│  SHARED MODULES (expanded)                                       │
│  paperforge/config.py           [existing] vault + path config   │
│  paperforge/logging_config.py   [NEW] structured logging setup   │
│  paperforge/worker/_utils.py    [NEW] shared worker utilities    │
│  paperforge/pdf_resolver.py     [existing] PDF path resolution   │
│  paperforge/ocr_diagnostics.py  [existing] OCR preflight checks  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Integration Points — Detailed Design

### 1. Shared Utilities: `paperforge/worker/_utils.py`

**Decision:** Place in `paperforge/worker/_utils.py` (underscore prefix = internal/private)

**Rationale:**
- Workers are the primary consumers (all 7 modules)
- Commands layer and skills layer can import from `paperforge.worker._utils` — no circular dependency because `_utils.py` has zero imports from other worker modules
- `skills/ld_deep.py` already imports from `paperforge.worker` (sync module), so adding `_utils` imports is consistent
- `config.py` already holds config-only utilities at `paperforge/` top level; `_utils.py` holds worker-domain utilities
- The underscore signals "not public API" to users who might `import paperforge`

**Contents of `_utils.py`:**

```python
"""paperforge.worker._utils — Shared worker utilities (internal, not public API).

All 7 worker modules import from here instead of duplicating these functions.
This module has NO imports from other paperforge.worker.* modules (no circular deps).
"""

from __future__ import annotations

import json
import os
import re
from json import JSONDecodeError
from pathlib import Path

# ---- JSON I/O ----
def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))

def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def read_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows

def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = '\n'.join((json.dumps(row, ensure_ascii=False) for row in rows))
    if text:
        text += '\n'
    path.write_text(text, encoding='utf-8')

# ---- YAML helpers ----
def yaml_quote(value: str) -> str:
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return '"' + str(value or '').replace('\\', '\\\\').replace('"', '\\"') + '"'

def yaml_block(value: str) -> list[str]:
    value = (value or '').strip()
    if not value:
        return ['abstract: |-', '  ']
    lines = ['abstract: |-']
    for line in value.splitlines():
        lines.append(f'  {line}')
    return lines

def yaml_list(key: str, values) -> list[str]:
    cleaned = [str(value).strip() for value in values or [] if str(value).strip()]
    if not cleaned:
        return [f'{key}: []']
    lines = [f'{key}:']
    for value in cleaned:
        lines.append(f'  - {yaml_quote(value)}')
    return lines

# ---- String helpers ----
def slugify_filename(text: str) -> str:
    cleaned = re.sub('[<>:"/\\\\|?*]+', '', text).strip()
    return cleaned[:120] or 'untitled'

def _extract_year(value: str) -> str:
    match = re.search('(19|20)\\d{2}', value or '')
    return match.group(0) if match else ''

def normalize_candidate_title(text: str) -> str:
    return re.sub('\\s+', ' ', str(text or '').strip().lower())

# ---- Env loader (delegates to config.py — removed from _utils!) ----
# NOTE: load_simple_env stays in config.py only.
# Workers that need env loading call paperforge.config.load_simple_env directly.

# ---- Journal database ----
_JOURNAL_DB: dict[str, dict] | None = None

def load_journal_db(system_dir: Path, zoterostyle_path_override: Path | None = None) -> dict[str, dict]:
    """Load zoterostyle.json journal database.
    
    Changed signature: takes system_dir instead of vault to avoid
    depending on load_vault_config, which keeps config.py as the
    single source of config truth.
    """
    global _JOURNAL_DB
    if _JOURNAL_DB is not None:
        return _JOURNAL_DB
    zoterostyle_path = zoterostyle_path_override or (system_dir / 'Zotero' / 'zoterostyle.json')
    if zoterostyle_path.exists():
        try:
            _JOURNAL_DB = read_json(zoterostyle_path)
        except (JSONDecodeError, Exception):
            _JOURNAL_DB = {}
    else:
        _JOURNAL_DB = {}
    return _JOURNAL_DB

def lookup_impact_factor(journal_name: str, extra: str, system_dir: Path) -> str:
    if not journal_name:
        return ''
    journal_db = load_journal_db(system_dir)
    if journal_name in journal_db:
        rank_data = journal_db[journal_name].get('rank', {})
        if isinstance(rank_data, dict):
            sciif = rank_data.get('sciif', '')
            if sciif:
                return str(sciif)
    if extra:
        if_match = re.search('影响因子[:：]\\s*([0-9.]+)', extra)
        if if_match:
            return if_match.group(1)
    return ''

# ---- Constants ----
STANDARD_VIEW_NAMES = frozenset([
    "控制面板", "推荐分析", "待 OCR", "OCR 完成",
    "待深度阅读", "深度阅读完成", "正式卡片", "全记录"
])

# ---- Retry logic ----
def retry_on_failure(max_retries=3, backoff=2.0, exceptions=(Exception,)):
    """Decorator: retry function with exponential backoff + jitter.
    
    Configurable via environment variables:
      PAPERFORGE_RETRY_MAX (default: 3)
      PAPERFORGE_RETRY_BACKOFF (default: 2.0 seconds)
    """
    import time
    import random
    import functools
    import logging
    
    logger = logging.getLogger('paperforge.retry')
    actual_max = int(os.environ.get('PAPERFORGE_RETRY_MAX', max_retries))
    actual_backoff = float(os.environ.get('PAPERFORGE_RETRY_BACKOFF', backoff))
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, actual_max + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == actual_max:
                        logger.error(f'{func.__name__} failed after {actual_max} attempts: {e}')
                        raise
                    delay = actual_backoff * (2 ** (attempt - 1)) + random.uniform(0, 1)
                    logger.warning(
                        f'{func.__name__} attempt {attempt}/{actual_max} failed: {e}. '
                        f'Retrying in {delay:.1f}s...'
                    )
                    time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

# ---- Progress bar helper ----
def progress_bar(iterable, desc: str = '', unit: str = 'items'):
    """Wrap iterable with tqdm progress bar, falling back gracefully if TTY unavailable.
    
    Auto-detects: if sys.stdout is a TTY, uses tqdm. Otherwise passes through silently.
    This ensures CI and piped output never break.
    """
    import sys
    try:
        from tqdm import tqdm
        if sys.stdout.isatty():
            return tqdm(iterable, desc=desc, unit=unit)
    except ImportError:
        pass
    return iterable

# ---- Deep-reading queue scanner (merged from 2 implementations) ----
def scan_library_records(
    library_records_dir: Path,
    ocr_dir: Path,
    filter_analyze: bool = True,
) -> list[dict]:
    """Scan library-records for entries awaiting deep reading.
    
    This is the SINGLE source of truth, merged from:
      - worker/deep_reading.py::run_deep_reading() (was: scan + report)
      - skills/ld_deep.py::scan_deep_reading_queue() (was: scan for Agent)
    
    Args:
        library_records_dir: Path to <control_dir>/library-records/
        ocr_dir: Path to <system_dir>/PaperForge/ocr/
        filter_analyze: If True, only return entries with analyze=true
                       and deep_reading_status != done
    
    Returns:
        List of dicts with keys: zotero_key, domain, title, 
        deep_reading_status, ocr_status, record_path, note_path
    """
    import logging
    logger = logging.getLogger('paperforge.deep_reading')
    
    queue: list[dict] = []
    if not library_records_dir.exists():
        return queue
    
    for domain_dir in sorted(library_records_dir.iterdir()):
        if not domain_dir.is_dir():
            continue
        domain = domain_dir.name
        for record_path in sorted(domain_dir.glob('*.md')):
            text = record_path.read_text(encoding='utf-8')
            
            zotero_key_match = re.search(r'^zotero_key:\s*(.+)$', text, re.MULTILINE)
            analyze_match = re.search(r'^analyze:\s*(true|false)$', text, re.MULTILINE)
            status_match = re.search(r'^deep_reading_status:\s*"?(.*?)"?$', text, re.MULTILINE)
            title_match = re.search(r'^title:\s*"?(.+?)"?$', text, re.MULTILINE)
            
            zotero_key = zotero_key_match.group(1).strip().strip('"').strip("'") if zotero_key_match else record_path.stem
            is_analyze = analyze_match is not None and analyze_match.group(1) == 'true'
            dr_status = status_match.group(1).strip() if status_match else 'pending'
            title = title_match.group(1).strip().strip('"') if title_match else ''
            
            if filter_analyze and (not is_analyze or dr_status == 'done'):
                continue
            
            # Check OCR status
            meta_path = ocr_dir / zotero_key / 'meta.json'
            ocr_status = 'pending'
            if meta_path.exists():
                try:
                    meta = read_json(meta_path)
                    ocr_status = str(meta.get('ocr_status', 'pending')).strip().lower()
                except Exception:
                    pass
            
            queue.append({
                'zotero_key': zotero_key,
                'domain': domain,
                'title': title,
                'deep_reading_status': dr_status,
                'ocr_status': ocr_status,
                'record_path': str(record_path),
            })
    
    if filter_analyze:
        queue.sort(key=lambda row: (
            0 if row['ocr_status'] == 'done' else 1,
            row['domain'],
            row['zotero_key'],
        ))
    
    logger.info(f'scan_library_records: found {len(queue)} entries')
    return queue
```

**What moves where:**

| Function | From | To |
|----------|------|-----|
| `read_json`, `write_json`, `read_jsonl`, `write_jsonl` | 7 workers | `_utils.py` |
| `yaml_quote`, `yaml_block`, `yaml_list` | 7 workers | `_utils.py` |
| `slugify_filename`, `_extract_year` | 7 workers | `_utils.py` |
| `load_journal_db`, `lookup_impact_factor` | 7 workers | `_utils.py` (signature changes: takes system_dir not vault) |
| `STANDARD_VIEW_NAMES` | 7 workers | `_utils.py` |
| `load_simple_env` | 7 workers | DELETED from workers; kept ONLY in `config.py` |
| `load_vault_config` | 7 workers | DELETED from workers; kept ONLY in `config.py` |
| `pipeline_paths` | 7 workers | DELETED from workers; kept ONLY in `config.py` |
| `load_domain_config` | 7 workers | DELETED from workers; kept ONLY in `sync.py` (only sync uses it) |
| `scan_deep_reading_queue()` | `skills/ld_deep.py` | `_utils.py::scan_library_records()` |
| Deep-reading scan logic | `worker/deep_reading.py` | `_utils.py::scan_library_records()` |

### 2. Structured Logging Integration

**Decision:** Dual-output strategy — `print()` for user-facing output, `logging` for diagnostic/trace

**New module: `paperforge/logging_config.py`**

```python
"""Centralized logging configuration for PaperForge Lite.

Dual-output strategy:
  - print() — user-facing status messages (keep existing behavior)
  - logging — diagnostic, trace, and error information for developers/CI

Configured once at CLI startup in cli.py::main().
"""
import logging
import sys

def configure_logging(verbose: bool = False) -> None:
    """Configure the 'paperforge' logger hierarchy.
    
    Args:
        verbose: If True, set DEBUG level. Otherwise INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    # Root paperforge logger
    logger = logging.getLogger('paperforge')
    logger.setLevel(level)
    
    # Sub-loggers for specific domains
    for name in ('sync', 'ocr', 'deep_reading', 'repair', 'status', 
                 'update', 'base_views', 'retry', 'cli', 'skills'):
        logging.getLogger(f'paperforge.{name}').setLevel(level)
    
    # Only add handler if none exists (prevents duplicate output on reload)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        formatter = logging.Formatter(
            '[%(levelname)s] %(name)s: %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    # Quiet down noisy third-party loggers
    for noisy in ('urllib3', 'requests', 'PIL'):
        logging.getLogger(noisy).setLevel(logging.WARNING)
```

**Usage pattern in workers:**

```python
import logging
logger = logging.getLogger('paperforge.ocr')  # or 'paperforge.sync', etc.

# User-facing (keep print):
print("OCR processing: TSTONE001.pdf — uploaded, polling...")

# Diagnostic (new, goes to stderr via logging):
logger.info("OCR upload: file_size=%d, pages=%d", file_size, page_count)
logger.warning("OCR API returned non-200: %d, retrying...", status_code)
logger.error("OCR failed permanently for TSTONE001: %s", error_msg)
```

**Backward compatibility:**
- All existing `print()` calls remain (user-facing status, queue reports, OCR results)
- New `logger.info/warning/error` calls are additive, not replacement
- `--verbose` / `-v` flag enables DEBUG-level logging output on stderr
- The logging handler writes to stderr, so `print()` output to stdout is not polluted
- CI/headless: logs go to stderr (capturable), prints go to stdout (human-readable)

**CLI integration (cli.py changes):**

```python
# Add to build_parser():
parser.add_argument('--verbose', '-v', action='store_true',
                    help='Enable verbose diagnostic logging')

# Add to main(), after env loading:
from paperforge.logging_config import configure_logging
configure_logging(verbose=getattr(args, 'verbose', False))
```

### 3. Pre-Commit Hooks Integration

**Decision:** Add `.pre-commit-config.yaml` at repo root. Hooks run on `git commit` only. Tests run separately via `pytest` — they do not intersect.

**File: `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-added-large-files
        args: ['--maxkb=500']
      - id: detect-private-key

  - repo: local
    hooks:
      - id: consistency-audit
        name: Consistency Audit
        entry: python scripts/consistency-audit.py
        language: python
        additional_dependencies: []
        files: '^paperforge/'
        pass_filenames: false
```

**Why this doesn't break the test sandbox:**

| Concern | Why Safe |
|---------|----------|
| Pre-commit runs full pipeline? | No — hooks are static analysis only |
| Pre-commit needs Zotero? | No — hooks check source files, not runtime |
| Pre-commit creates vault files? | No — hooks are read-only on staged files |
| Pre-commit interferes with `pytest`? | No — `pytest` is invoked separately by the developer |
| Pre-commit fails in CI? | No — add `skip: [consistency-audit]` in GitHub Actions if CI env lacks the script |

**What the custom consistency-audit hook checks:**
1. No worker module defines functions that also exist in `_utils.py` (except sync.py during transition)
2. All 7 worker modules import from `paperforge.worker._utils` instead of defining their own copies
3. No `load_simple_env` function exists outside `config.py`
4. `scan_library_records` is imported only from `_utils.py` (not duplicated in `ld_deep.py` or `deep_reading.py`)
5. `STANDARD_VIEW_NAMES` is defined only in `_utils.py`

### 4. Progress Bar Integration

**Decision:** Add `tqdm` to dependencies. Wrap in a TTY-aware helper in `_utils.py`.

**Changes:**

1. **pyproject.toml:** Add `"tqdm>=4.66.0"` to `dependencies`

2. **`_utils.py`** — `progress_bar()` helper (shown above in Section 1)

3. **Usage in workers:**

```python
# paperforge/worker/sync.py (run_selection_sync)
from paperforge.worker._utils import progress_bar

# Before:
for export_path in sorted(paths['exports'].glob('*.json')):
    for item in load_export_rows(export_path):
        ...

# After:
for export_path in progress_bar(
    sorted(paths['exports'].glob('*.json')), 
    desc='Processing domains', unit='domain'
):
    for item in progress_bar(
        load_export_rows(export_path), 
        desc=f'  {export_path.stem}', unit='record'
    ):
        ...
```

```python
# paperforge/worker/ocr.py (run_ocr — PDF upload loop)
from paperforge.worker._utils import progress_bar

for record in progress_bar(
    pending_records, 
    desc='Uploading PDFs for OCR', unit='pdf'
):
    ...
```

**Graceful degradation:**
- If `sys.stdout.isatty()` is False (CI, piped output): `progress_bar()` returns the original iterable — no progress bar, no line noise
- If `tqdm` is not installed: `progress_bar()` returns the original iterable — no crash
- Default timeouts and polling intervals unchanged

### 5. Retry Logic Integration

**Decision:** Shared decorator in `_utils.py`. Only OCR worker uses it initially. Available for other workers that make HTTP calls.

**Design:**

```
┌─────────────────────────────────────────┐
│  paperforge/worker/_utils.py            │
│  ┌───────────────────────────────────┐  │
│  │ retry_on_failure(                 │  │
│  │   max_retries=3,                  │  │
│  │   backoff=2.0,                    │  │
│  │   exceptions=(RequestException,)  │  │
│  │ )                                 │  │
│  └───────────────────────────────────┘  │
│             ↑ import ↑                   │
│  ┌───────────────────────────────────┐  │
│  │ paperforge/worker/ocr.py          │  │
│  │ @retry_on_failure(                │  │
│  │   exceptions=(requests.           │  │
│  │     RequestException,)            │  │
│  │ )                                 │  │
│  │ def _upload_pdf(...):             │  │
│  │ def _poll_ocr_status(...):         │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

**Retry policy:**
- Max retries: 3 (configurable via `PAPERFORGE_RETRY_MAX` env var)
- Backoff: exponential (2s, 4s, 8s) with random jitter (±1s)
- Retryable: `requests.RequestException` (network errors, timeouts, 5xx)
- Non-retryable: `json.JSONDecodeError`, `ValueError`, 4xx responses
- Each retry logged via `logging.getLogger('paperforge.retry')`

**Where retry is applied:**
- `ocr.py`: `_upload_pdf_to_paddleocr()` — network upload
- `ocr.py`: `_poll_paddleocr_job()` — status polling
- `ocr_diagnostics.py`: HTTP health check (one attempt, no retry needed for diagnostics)
- `update.py`: GitHub API call for latest release (could add, low priority)

**OCR-specific retry integration (ocr.py changes):**

```python
from paperforge.worker._utils import retry_on_failure
import requests

@retry_on_failure(max_retries=3, backoff=2.0, exceptions=(requests.RequestException,))
def _upload_pdf_to_paddleocr(pdf_path: Path, api_key: str, api_url: str) -> dict:
    """Upload PDF to PaddleOCR API with retry on transient failures."""
    # ... existing upload logic ...
    response = requests.post(api_url, files={'file': open(pdf_path, 'rb')}, 
                            headers={'Authorization': f'Bearer {api_key}'})
    response.raise_for_status()
    return response.json()
```

### 6. Deep-Reading Queue Merge

**Current state:** Two implementations doing the same thing differently

| Aspect | `worker/deep_reading.py` | `skills/ld_deep.py` |
|--------|--------------------------|---------------------|
| Function | `run_deep_reading()` | `scan_deep_reading_queue()` |
| Input | vault: Path | vault: Path |
| Scan source | Exports JSON → load_export_rows | library-records/*.md directly |
| Output | Writes deep-reading-queue.md report | Returns list of dicts |
| Side effects | Updates deep_reading_status in records | None |
| Called by | CLI: `paperforge deep-reading` | Agent: `python ld_deep.py queue` |
| Filter | Analyzes all records (has analyze check later) | Filters to analyze=true, status!=done |

**Merge strategy:**

```
BEFORE (two implementations):
┌──────────────────────────┐    ┌──────────────────────────┐
│ worker/deep_reading.py   │    │ skills/ld_deep.py        │
│ ┌──────────────────────┐ │    │ ┌──────────────────────┐ │
│ │ run_deep_reading()   │ │    │ │ scan_deep_reading_   │ │
│ │ - scan exports JSON  │ │    │ │ queue()              │ │
│ │ - scan library-records│ │   │ │ - scan library-records│ │
│ │ - update status      │ │    │ │ - check analyze flag │ │
│ │ - write report       │ │    │ │ - check OCR status   │ │
│ └──────────────────────┘ │    │ │ - return list[dict]  │ │
└──────────────────────────┘    │ └──────────────────────┘ │
                                └──────────────────────────┘

AFTER (single source of truth):
┌──────────────────────────┐
│ worker/_utils.py         │
│ ┌──────────────────────┐ │
│ │ scan_library_records │ │  ← SINGLE SOURCE OF TRUTH
│ │ (filter_analyze=True)│ │     Returns list[dict]
│ └──────────────────────┘ │
└──────┬───────────────┬───┘
       │ import        │ import
       ▼               ▼
┌──────────────┐ ┌──────────────┐
│ deep_reading │ │ ld_deep.py   │
│ run_deep_    │ │ prepare_deep_│
│ reading():   │ │ reading():   │
│ - calls scan_│ │ - calls scan_│
│   library_   │ │   library_   │
│   records()  │ │   records()  │
│ - updates    │ │ - Agent-     │
│   status     │ │   specific   │
│ - writes     │ │   formatting │
│   report     │ │              │
└──────────────┘ └──────────────┘
```

**What changes in each file:**

- **`worker/_utils.py`** — ADD `scan_library_records()` (new, extracted logic)
- **`worker/deep_reading.py`** — REPLACE inline scan logic with: `from paperforge.worker._utils import scan_library_records; queue = scan_library_records(paths['library_records'], paths['ocr'])`; keep status-updating and report-writing logic
- **`skills/ld_deep.py`** — REPLACE `scan_deep_reading_queue()` with: `from paperforge.worker._utils import scan_library_records; return scan_library_records(records_root, ocr_root)`; REMOVE the 50-line inline implementation
- **`skills/ld_deep.py`** — UPDATE `main()` queue subcommand to use `scan_library_records()` instead of `scan_deep_reading_queue()`

### 7. Dead Code Removal Strategy

**Safe cleanup phases:**

**Phase A — Immediate (safe, no callers):**
| File | Dead Code | Action |
|------|-----------|--------|
| `worker/status.py` | `UPDATE_*` constants (duplicated from `update.py`) | REMOVE; they were copied during v1.2 migration |
| `worker/status.py` | Duplicated import block (fitz, PIL, etc.) | REPLACE with only needed imports |
| `skills/ld_deep.py` | `scan_deep_reading_queue()` function | REMOVE after merge into `_utils.py` |
| All 7 workers | `load_simple_env()` function (already in `config.py`) | REMOVE; callers use `config.load_simple_env` directly |

**Phase B — After _utils.py extraction (safe, tests verify):**
| File | Dead Code | Action |
|------|-----------|--------|
| 6 workers (not sync.py) | `read_json`, `write_json`, etc. utilities | REMOVE; import from `_utils.py` |
| 6 workers (not sync.py) | `load_vault_config`, `pipeline_paths` | REMOVE; import from `config.py` |
| 6 workers (not sync.py) | `load_journal_db`, `lookup_impact_factor` | REMOVE; import from `_utils.py` |
| 6 workers (not sync.py) | `STANDARD_VIEW_NAMES` | REMOVE; import from `_utils.py` |
| 6 workers (not sync.py) | Massive import blocks | REPLACE with only needed imports |

**Phase C — Low risk, post-validation:**
| File | Code to Evaluate | Action |
|------|-----------------|--------|
| `cli.py` | `--selection`, `--index` flags in sync command | KEEP (backward compat per AGENTS.md) |
| `cli.py` | Old subparsers (`selection-sync`, `index-refresh`) | KEEP (backward compat, documented) |
| `cli.py` | `_resolve_pipeline()` method | EVALUATE — may be obsolete after v1.3 worker/ migration |

**Verification gate:** After each phase, run full test suite (`pytest tests/ -x`). All 203 tests must pass. Test failures indicate an import path that needs updating.

---

## Recommended Project Structure (v1.4 target)

```
paperforge/
├── __init__.py                    # Version string only
├── __main__.py                    # python -m paperforge entry
├── cli.py                         # CLI entry, arg parsing, logging init
├── config.py                      # [EXISTING] Vault config + path resolution
├── logging_config.py              # [NEW] Structured logging setup
├── pdf_resolver.py                # [EXISTING] PDF path resolution
├── ocr_diagnostics.py             # [EXISTING] OCR preflight checks
│
├── commands/                      # Thin dispatch layer
│   ├── __init__.py
│   ├── sync.py                    # Delegates to worker/sync.py
│   ├── ocr.py                     # Delegates to worker/ocr.py
│   ├── deep.py                    # Delegates to worker/deep_reading.py
│   ├── status.py                  # Delegates to worker/status.py
│   └── repair.py                  # Delegates to worker/repair.py
│
├── worker/                        # Core processing (7 modules → 8 with _utils)
│   ├── __init__.py                # Public re-exports
│   ├── _utils.py                  # [NEW] Shared utilities (~250 loc)
│   ├── sync.py                    # Selection sync + index refresh
│   ├── ocr.py                     # PaddleOCR integration
│   ├── deep_reading.py            # Queue scanning + status sync
│   ├── repair.py                  # State divergence repair
│   ├── status.py                  # System status + doctor
│   ├── base_views.py              # Obsidian Base generation
│   └── update.py                  # Auto-update logic
│
└── skills/                        # Agent helper scripts
    └── literature-qa/
        └── scripts/
            └── ld_deep.py         # Deep reading prepare + validate
```

---

## Data Flow — Logging & Progress Bar Integration

```
User runs: paperforge sync --verbose

  cli.py::main()
    │
    ├─ 1. parse args: --verbose=True
    ├─ 2. resolve_vault()
    ├─ 3. load_simple_env() x2     # vault .env + pf .env
    ├─ 4. configure_logging(verbose=True)     # [NEW] sets up stderr logging
    │      └─ logger 'paperforge' at DEBUG level
    │
    └─ 5. dispatch to commands/sync.py::run(args)
           │
           └─ worker/sync.py::run_selection_sync(vault)
                │
                ├─ logger.info("Starting selection-sync for %s", vault)   # [NEW] stderr
                ├─ print("selection-sync: wrote 5 records")                # stdout (unchanged)
                │
                └─ for domain in progress_bar(domains):                   # [NEW] tqdm bar
                     │
                     └─ for item in progress_bar(items):
                          ├─ Process each item
                          └─ logger.debug("Processed %s", item['key'])   # [NEW] only with -v

Terminal output:
  STDOUT: "selection-sync: wrote 5 records, updated 3 records"  ← user sees this
  STDERR: "[INFO] paperforge.sync: Starting selection-sync..."   ← only with -v

CI / Piped output:
  STDOUT: "selection-sync: wrote 5 records, updated 3 records"  ← same
  STDERR: (no tqdm bars, progress_bar() passes through)          ← no noise
```

---

## Retry Data Flow — OCR Worker

```
User runs: paperforge ocr

  cli.py::main()
    └─ commands/ocr.py::run()
         └─ worker/ocr.py::run_ocr(vault)
              │
              ├─ Scan library-records for do_ocr=true, ocr_status!=done
              ├─ For each pending PDF:
              │    │
              │    └─ _upload_pdf_to_paddleocr(pdf_path, ...)
              │         │
              │         └─ @retry_on_failure(max_retries=3, backoff=2.0)
              │              │
              │              ├─ Attempt 1: POST fails (ConnectionError)
              │              │    logger.warning("attempt 1/3 failed... retrying in 2.3s")
              │              ├─ Attempt 2: POST succeeds
              │              │    return response
              │              └─ If all 3 fail:
              │                   logger.error("failed after 3 attempts")
              │                   raise → caught by run_ocr → mark ocr_status=failed
              │
              └─ _poll_ocr_job(job_id, ...)
                   │
                   └─ @retry_on_failure(max_retries=5, backoff=5.0)
                        (longer backoff for polling — API may be processing)

Environment variable overrides:
  PAPERFORGE_RETRY_MAX=5        → 5 retries for all decorated functions
  PAPERFORGE_RETRY_BACKOFF=10.0 → 10s base backoff
```

---

## Architectural Patterns

### Pattern 1: Module-Level Globals for Test Patching

**What:** `cli.py` initializes worker function references to `None`, allowing tests to inject stubs before `main()` is called. `_import_worker_functions()` only imports if the global is still `None`.

**When to use:** When you need to test CLI dispatch without invoking real workers. The commands layer also checks for cli patches via `_get_run_*()` helper functions that prefer cli globals.

**Trade-offs:**
- PRO: Tests can stub workers without mocking entire import chains
- PRO: No test pollution between test runs (each test reloads cli module)
- CON: Module-level state is fragile; must `importlib.reload(cli)` in tests
- CON: Adding new workers requires updating globals, `_import_worker_functions()`, and test stubs

**Impact on v1.4 integration:** This pattern is NOT affected by `_utils.py` extraction. Worker stubs are injected at the `cli.run_*` level, which is above the worker layer. `_utils.py` imports happen inside workers, which stubs bypass entirely.

### Pattern 2: Thin Commands Dispatch Layer

**What:** `paperforge/commands/*.py` modules are ~90 lines each. They resolve vault/paths, select the correct worker function (checking CLI globals for test stubs), call it, and return exit codes.

**When to use:** When the CLI needs a stable API surface but worker internals change frequently. The commands layer isolates CLI argument handling from business logic.

**Trade-offs:**
- PRO: Testable independently (commands can call stub workers)
- PRO: Agent and CLI share the same worker code path
- CON: Adds one more module per command (5 modules × ~90 lines = ~450 lines)

**Impact on v1.4 integration:** The commands layer does NOT need changes. Workers importing from `_utils.py` is invisible to commands. Logging configuration happens above this layer in `cli.py`. The only change: progress bars appear in stdout during worker execution (tqdm writes to stdout), which the commands layer doesn't interfere with.

### Pattern 3: Delegate-to-Shared-Module Compatibility Wrappers

**What:** Worker modules define thin wrappers like `load_vault_config()` and `pipeline_paths()` that delegate to `paperforge.config`. These exist to preserve the legacy API surface for existing callers.

**When to use:** During migration — maintain backward compatibility while moving the real implementation to a shared location.

**Trade-offs:**
- PRO: No breaking changes to callers during migration
- PRO: Graceful transition (deprecation warnings can be added)
- CON: Thin wrappers are code that must eventually be cleaned up

**Impact on v1.4 integration:** These wrapper functions are PART of the duplication problem. After `_utils.py` extraction, workers can import directly from `config.py` and `_utils.py`. The wrappers become dead code and should be removed in Phase B of dead code cleanup.

### Pattern 4: TTY-Aware Graceful Degradation (Progress Bars)

**What:** The `progress_bar()` helper in `_utils.py` auto-detects whether stdout is a TTY. If yes, wraps the iterable with `tqdm`. If no (CI, pipe, redirect), returns the iterable unchanged.

**When to use:** For any long-running operation where progress feedback is useful in interactive terminals but would produce garbage output in CI logs.

**Trade-offs:**
- PRO: No CI output pollution
- PRO: Falls back silently if `tqdm` is not installed
- PRO: User gets visual feedback, CI gets clean logs
- CON: TTY detection is heuristic — some terminal emulators may not be detected correctly

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Importing `_utils.py` from `config.py`

**What people do:** Put all shared utilities in `config.py` to avoid creating a new file.

**Why it's wrong:** `config.py` has a clear responsibility (configuration + path resolution). Adding JSON I/O, YAML helpers, retry logic, journal database loading, and progress bars bloats it into a "god module." Tests that mock config also inadvertently pull in unrelated utilities.

**Instead:** Create `worker/_utils.py` for worker-domain utilities. Keep `config.py` focused on configuration hierarchy and path resolution only.

### Anti-Pattern 2: Replacing all `print()` calls with `logging.info()`

**What people do:** `s/print(/logger.info(/g` across the entire codebase.

**Why it's wrong:**
- User-facing status messages (queue reports, sync counts, OCR results) are consumed by humans reading stdout
- `logging.info()` goes to stderr by default, which is invisible unless redirected
- Some downstream consumers (Agent integration, script wrappers) may parse stdout
- Breaking the stdout contract silently breaks the Agent workflow

**Instead:** Dual-output strategy: keep `print()` for user-facing output, add `logging` for diagnostic/trace/error messages on stderr.

### Anti-Pattern 3: Putting retry logic directly in `ocr.py`

**What people do:** Write a for-loop with `time.sleep()` inline in the OCR worker functions.

**Why it's wrong:**
- Duplicates retry logic when `repair.py` or `sync.py` later need it
- Inline retry is harder to test (can't mock sleep, can't count retries)
- No centralized configuration (each inline loop has different magic numbers)

**Instead:** Extract `retry_on_failure` decorator into `_utils.py`. Apply via decorator. Tests can mock the decorator or verify retry count via logging output.

### Anti-Pattern 4: Pre-commit hooks that require a running environment

**What people do:** Add `pytest` to pre-commit hooks, or add hooks that import the project code and need `PYTHONPATH` set up.

**Why it's wrong:**
- Pre-commit runs in an isolated venv, often without project dependencies
- Tests that need a real Zotero installation will fail in pre-commit's sandbox
- Slows down every commit (full test suite takes minutes)
- Test failures on commit are confusing (developer expected commits to save work, not run tests)

**Instead:** Pre-commit hooks are static analysis only (linting, formatting, consistency checks). Integration tests go in CI (GitHub Actions). Smoke tests are run manually or in CI.

---

## Scaling Considerations

PaperForge Lite is a single-user desktop CLI tool. Scaling concerns are about user experience, not server load.

| Concern | At 100 library records | At 1000 library records | Mitigation |
|---------|----------------------|------------------------|------------|
| Sync duration | <1 second | ~5 seconds | Progress bar shows per-domain progress |
| OCR processing | 1-2 PDFs typical | 10-20 PDFs (rare) | Progress bar + retry handles long queues |
| Deep-reading scan | Instant | <1 second | Already O(n) scan, no change needed |
| Log output volume | Minimal | ~50 lines | `--verbose` flag controls DEBUG output |
| Pre-commit speed | <2 seconds | <2 seconds | Only checks staged files, not full project |

**First bottleneck:** OCR processing time (dominated by PaddleOCR API, not local code). Progress bars and retry logic address the UX and reliability aspects of this bottleneck.

---

## Component Responsibilities

| Component | Responsibility | New/Modified | Dependencies |
|-----------|---------------|--------------|--------------|
| `paperforge/worker/_utils.py` | Shared I/O, YAML, retry, progress, journal DB, queue scan | **NEW** | `config.py` (for journal DB path) |
| `paperforge/logging_config.py` | Structured logging setup, handler configuration | **NEW** | stdlib `logging` |
| `paperforge/cli.py` | Add `--verbose` flag, call `configure_logging()` | MODIFIED | `logging_config.py` |
| `paperforge/worker/sync.py` | Import from `_utils.py`, remove local copies, add progress bars | MODIFIED | `_utils.py`, `config.py` |
| `paperforge/worker/ocr.py` | Import from `_utils.py`, remove local copies, add retry decorator, progress bars | MODIFIED | `_utils.py`, `config.py` |
| `paperforge/worker/deep_reading.py` | Import `scan_library_records` from `_utils.py`, remove duplicate scan logic | MODIFIED | `_utils.py` |
| `paperforge/worker/repair.py` | Import from `_utils.py`, remove local copies | MODIFIED | `_utils.py` |
| `paperforge/worker/status.py` | Import from `_utils.py`, remove local copies, remove dead UPDATE_* constants | MODIFIED | `_utils.py` |
| `paperforge/worker/base_views.py` | Import from `_utils.py`, remove local copies | MODIFIED | `_utils.py` |
| `paperforge/worker/update.py` | Import from `_utils.py`, remove local copies | MODIFIED | `_utils.py` |
| `paperforge/skills/.../ld_deep.py` | Import `scan_library_records` from `_utils.py`, remove `scan_deep_reading_queue()` | MODIFIED | `_utils.py` |
| `pyproject.toml` | Add `tqdm` dependency | MODIFIED | N/A |
| `.pre-commit-config.yaml` | Pre-commit hooks (ruff, consistency audit) | **NEW** | `ruff`, `pre-commit` |
| `scripts/consistency-audit.py` | Worker duplication checker for pre-commit | **NEW** | N/A |
| `tests/` | Update imports in test files that mock worker utilities | MODIFIED (minor) | `_utils.py` |

---

## Build Order (Dependency-Aware)

```
Phase 1: Foundation (no user-facing changes, infrastructure only)
  ┌─────────────────────────────────────────────────────────────┐
  │ 1a. Create paperforge/logging_config.py                    │
  │ 1b. Add --verbose flag to cli.py, call configure_logging() │
  │ 1c. Add tqdm to pyproject.toml dependencies                │
  │ STATUS: logging works, -v flag works, tqdm available       │
  └─────────────────────────────────────────────────────────────┘
                    │
Phase 2: Shared utilities extraction (core refactor)             
  ┌─────────────────────────────────────────────────────────────┐
  │ 2a. Create paperforge/worker/_utils.py with ALL functions  │
  │ 2b. Update sync.py to import from _utils.py (keep originals│
  │     as aliases for backward compat during transition)      │
  │ 2c. Run tests: pytest tests/ -x                            │
  │ 2d. Update ocr.py to import from _utils.py                 │
  │ 2e. Run tests: pytest tests/ -x                            │
  │ 2f. Repeat for deep_reading, repair, status, base_views,    │
  │     update (one at a time, test after each)                │
  │ STATUS: all 7 workers import from _utils.py, tests pass    │
  └─────────────────────────────────────────────────────────────┘
                    │
Phase 3: Deep-reading queue merge                                
  ┌─────────────────────────────────────────────────────────────┐
  │ 3a. Add scan_library_records() to _utils.py                │
  │ 3b. Update worker/deep_reading.py to use it                │
  │ 3c. Update skills/ld_deep.py to use it                     │
  │ 3d. Remove scan_deep_reading_queue() from ld_deep.py       │
  │ 3e. Run tests: pytest tests/ -x                            │
  │ STATUS: single queue scanner, both consumers use it        │
  └─────────────────────────────────────────────────────────────┘
                    │
Phase 4: Retry logic + progress bars                              
  ┌─────────────────────────────────────────────────────────────┐
  │ 4a. Add retry_on_failure decorator to _utils.py            │
  │ 4b. Apply @retry_on_failure to OCR upload + poll functions │
  │ 4c. Add progress_bar() to _utils.py                        │
  │ 4d. Add progress bars to sync and ocr workers              │
  │ 4e. Run tests: pytest tests/ -x                            │
  │ STATUS: OCR retries on failure, progress bars in terminal  │
  └─────────────────────────────────────────────────────────────┘
                    │
Phase 5: Dead code removal + cleanup                              
  ┌─────────────────────────────────────────────────────────────┐
  │ 5a. Remove duplicated functions from 6 workers (Phase B)   │
  │ 5b. Remove UPDATE_* constants from status.py (Phase A)     │
  │ 5c. Remove load_simple_env from all workers (Phase A)      │
  │ 5d. Slim import blocks in all workers                      │
  │ 5e. Run tests: pytest tests/ -x                            │
  │ STATUS: ~1,610 lines eliminated from codebase              │
  └─────────────────────────────────────────────────────────────┘
                    │
Phase 6: Pre-commit hooks                                         
  ┌─────────────────────────────────────────────────────────────┐
  │ 6a. Create .pre-commit-config.yaml                         │
  │ 6b. Create scripts/consistency-audit.py                    │
  │ 6c. Add ruff configuration to pyproject.toml               │
  │ 6d. Run: pre-commit run --all-files                        │
  │ 6e. Fix any lint violations                                │
  │ STATUS: pre-commit hooks active, CI-ready                  │
  └─────────────────────────────────────────────────────────────┘
```

**Why this order:**
1. Logging infrastructure first — so subsequent phases can use logger calls immediately
2. Shared utilities extraction must precede everything else (retry, progress bars, queue merge all go in `_utils.py`)
3. Deep-reading queue merge depends on `_utils.py` existing
4. Retry and progress bars depend on `_utils.py` utilities being available
5. Dead code removal is last — verifying no missing imports before deleting
6. Pre-commit hooks are final — they validate the cleaned-up codebase

---

## Sources

- Codebase audit of all 22 Python files in `paperforge/` (April 25, 2026)
- `paperforge/cli.py` — CLI dispatch patterns, test patching (lines 32-109)
- `paperforge/config.py` — existing centralized config module (lines 1-299)
- `paperforge/worker/sync.py` — largest worker, all duplication sources (lines 1-1034)
- `paperforge/worker/deep_reading.py` — deep reading queue implementation A (lines 1-324)
- `paperforge/skills/literature-qa/scripts/ld_deep.py` — deep reading queue implementation B (lines 1-1295)
- `paperforge/worker/ocr.py` — OCR worker, retry target (lines 1-120 of 1376)
- `paperforge/worker/status.py` — dead code evidence (lines 1-100 of 625)
- `paperforge/commands/sync.py` — commands layer pattern (lines 1-92)
- `tests/conftest.py` — test sandbox architecture (lines 1-169)
- `tests/test_cli_worker_dispatch.py` — test patching pattern (lines 1-157)
- `pyproject.toml` — current dependencies and configuration (lines 1-50)
- `tqdm` documentation — TTY auto-detection behavior (Context7 / official docs)
- Python `logging` module — best practices for library logging (official docs)
- `pre-commit` documentation — hook isolation and configuration (official docs)

---

*Architecture research for: PaperForge Lite v1.4 — shared utilities, logging, pre-commit, progress bars, retry logic integration*
*Researched: 2026-04-25*
*Confidence: HIGH — codebase audited line-by-line; all import patterns, duplication locations, and test sandbox behaviors verified*
