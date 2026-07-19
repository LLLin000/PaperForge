---
phase: 16
phase_name: "Retry Progress Bars"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 9
  lessons: 3
  patterns: 4
  surprises: 0
missing_artifacts:
  - "UAT.md"
  - "VERIFICATION.md"
---

## Decisions

### _retry.py and _progress.py follow leaf module pattern (no intra-project imports)

Both modules import only from stdlib and external dependencies (tenacity, tqdm). No imports from paperforge.* modules, ensuring zero circular dependency risk.

**Source:** 16-01-PLAN.md (interfaces), 16-01-SUMMARY.md

---

### configure_retry() reads env vars with sensible defaults

PAPERFORGE_RETRY_MAX defaults to 5; PAPERFORGE_RETRY_BACKOFF defaults to 2.0. Returns a tenacity retry decorator with exponential backoff, jitter, and retryable exception classification (ConnectionError, Timeout, HTTP 429/503).

**Source:** 16-01-PLAN.md (task 2, lines 77-88), 16-01-SUMMARY.md

---

### retry_with_meta writes retry metadata to meta.json on each attempt

On each retry, writes retry_count, last_error, last_attempt_at to meta.json. On exhaustion, re-raises for caller to handle — does not catch internally.

**Source:** 16-01-PLAN.md (task 2, lines 89-94), 16-01-SUMMARY.md

---

### progress_bar wraps tqdm with stderr output per D-10

All tqdm output goes to sys.stderr so stdout remains clean for piped data. Wraps with mininterval=1.0 and compact bar format.

**Source:** 16-01-PLAN.md (task 3, lines 203-213), 16-01-SUMMARY.md

---

### --no-progress is a root-level global flag

Added to the root argument parser (same level as --verbose), not any sub-parser. Accessible across all commands as args.no_progress.

**Source:** 16-02-PLAN.md (task 1, lines 92-103), 16-02-SUMMARY.md

---

### Zombie job detection threshold defaults to 30 minutes

Jobs with ocr_status 'queued' or 'running' older than PAPERFORGE_ZOMBIE_TIMEOUT_MINUTES (default 30) are reset to 'pending' at run_ocr() startup.

**Source:** 16-02-PLAN.md (task 2, lines 144-158), 16-02-SUMMARY.md

---

### Poll failures must not abort batch (batch resilience per D-09)

Previously uncaught poll raise_for_status() would crash the entire batch. Now wrapped in try/except with retry, continuing to next item on exhaustion.

**Source:** 16-02-PLAN.md (task 2, lines 191-211), 16-02-SUMMARY.md

---

### Upload and poll refactored into inner functions for clean retry wrapping

_do_upload() and _do_poll() inner functions capture the actual API call, allowing retry_with_meta() to wrap them without restructuring the large run_ocr() loop.

**Source:** 16-02-PLAN.md (task 2, lines 165-210), 16-02-SUMMARY.md

---

### ensure_ocr_meta() extended with retry metadata defaults

Three new setdefault lines: retry_count=0, last_error=None, last_attempt_at=None. This ensures every meta.json has the retry tracking fields even before any retry occurs.

**Source:** 16-02-PLAN.md (task 2, lines 213-219), 16-02-SUMMARY.md

---

## Lessons

### Refactoring upload/poll into inner functions enables clean retry wrapping

By extracting API call logic into small inner functions, retry_with_meta() can wrap them transparently without restructuring the entire run_ocr() loop or duplicating exception handling.

**Context:** The original upload code was inline inside a large try/except block. Extracting _do_upload() and _do_poll() allowed retry_with_meta() to wrap the API call itself while the existing exception handler continued serving as the catch-all after exhaustion.

**Source:** 16-02-PLAN.md (task 2), 16-02-SUMMARY.md

---

### Zombie reset at startup handles stale processing states gracefully

By scanning meta.json files for stale 'queued'/'running' states at run_ocr() start, zombie jobs from crashes or timeouts are automatically reset without manual intervention.

**Source:** 16-02-PLAN.md (task 2), 16-02-SUMMARY.md

---

### Existing exception handlers naturally serve as batch resilience catch-all

After retry_with_meta() exhausts its attempts and re-raises, the existing except Exception block already handled classification, meta.json update, and continue. No additional structural changes were needed.

**Source:** 16-02-PLAN.md (task 2, lines 248-251), 16-02-SUMMARY.md

---

## Patterns

### Leaf Module for Infrastructure

New infrastructure modules (_retry.py, _progress.py) follow the existing _utils.py leaf module pattern: no intra-project imports, single purpose, stdout/stdlib-only dependencies.

**Source:** 16-01-PLAN.md (tasks 2, 3), 16-01-SUMMARY.md

---

### Env-Var-Based Configuration with Defaults

Retry behavior (max attempts, backoff multiplier) and zombie timeout configured via environment variables with sensible defaults, matching the existing PAPERFORGE_LOG_LEVEL pattern.

**Source:** 16-01-PLAN.md (task 2), 16-02-PLAN.md (task 2)

---

### Inner Function Extraction for Clean Retry Wrapping

When adding retry to existing code, extract the retryable operation into a small inner function, then wrap it with retry_with_meta() — minimal structural change, maximum clarity.

**Source:** 16-02-PLAN.md (task 2), 16-02-SUMMARY.md

---

### tqdm on stderr Preserves Pipe-Compatible Output

progress_bar() writes to sys.stderr by default, ensuring stdout remains clean for piped data. The --no-progress flag provides explicit suppression for CI/non-TTY environments.

**Source:** 16-02-PLAN.md (task 2), 16-02-SUMMARY.md

---

## Surprises

None documented. Both plans executed exactly as written with zero deviations.

**Source:** 16-01-SUMMARY.md, 16-02-SUMMARY.md
