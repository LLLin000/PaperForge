# Phase 16: Retry + Progress Bars - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the OCR pipeline resilient to transient network failures and provide user-visible progress indication. Add tenacity retry to PaddleOCR API calls, extend meta.json schema, detect and reset zombie jobs, ensure batch resilience, and add tqdm progress bars. Zero behavioral change to OCR output (status print, meta.json format additions only).

Requirements: REL-01, REL-02, REL-03, REL-04, OBS-04

Out of scope:
- OCR error message improvement (OBS-05 — Phase 17)
- Consistency audit / pre-commit (DX-01, DX-02 — Phase 17)
- E2E integration tests (TEST-01 — Phase 19)

</domain>

<decisions>
## Implementation Decisions

### Module Structure
- **D-01:** New `paperforge/worker/_retry.py` — leaf module importing only `tenacity` + stdlib. Houses the `ocr_retry` decorator and any future retry utilities. Keeps `_utils.py` leaf constraint intact.
- **D-02:** New `paperforge/worker/_progress.py` — leaf module importing only `tqdm` + stdlib. Exports a `progress_bar(iterable, desc, total, disable)` function wrapping tqdm. Centralizes tqdm configuration (stderr output, auto-disable, mininterval).

### CLI Flag
- **D-03:** `--no-progress` is a **global root parser flag**, same level as `--verbose` from Phase 13. Syntax: `paperforge --no-progress ocr`. Future commands with progress bars automatically inherit.

### Retry Behavior (REL-01)
- **D-04:** tenacity retry applied to both **upload** (l.1256-1269) and **poll** (l.1175 in ocr.py). Exponential backoff: 1s → 2s → 4s → 8s → max 30s, with jitter.
- **D-05:** Retry on: `requests.ConnectionError`, `requests.Timeout`, `requests.HTTPError` with status 429/503. All other exceptions fail immediately.
- **D-06:** Retry config via env vars: `PAPERFORGE_RETRY_MAX` (max attempts, default 5), `PAPERFORGE_RETRY_BACKOFF` (backoff multiplier, default 2.0). Read from `os.environ` in `configure_retry()` within `_retry.py`.

### meta.json Schema (REL-02)
- **D-07:** Extend meta.json with three new fields:
  - `retry_count` (int, default 0) — incremented each retry attempt
  - `last_error` (str | null, default null) — last exception message
  - `last_attempt_at` (ISO-8601 str | null, default null) — timestamp of last attempt
- Written atomically via existing `write_json()` after each attempt (upload and poll).

### Zombie Reset (REL-03)
- **D-08:** At start of `run_ocr()`, scan all `ocr/<key>/meta.json` files. For entries where `ocr_status == "processing"` and `ocr_started_at` is older than 30 minutes (configurable via env var, default 30min), reset to `pending` and increment `retry_count`. Blocked/error terminal states are never auto-reset.

### Batch Resilience (REL-04)
- **D-09:** Both upload and poll HTTP failures are caught. A single PDF upload or poll failure does NOT abort the batch — failed items are logged, meta.json updated, and processing continues with remaining items. Poll `raise_for_status()` (l.1175) wrapped in try/except.

### Progress Bars (OBS-04)
- **D-10:** tqdm output goes to **stderr** (via `file=sys.stderr`). Auto-detects non-TTY (CI, pipe) — silently falls back to no progress. `--no-progress` flag disables explicitly. Progress shown during: upload iteration (PDF-by-PDF), poll iteration (active jobs).

### the agent's Discretion
- Exact tenacity decorator implementation (`@retry` vs `Retrying` class)
- Whether to wrap individual ocr.py functions or inline the retry logic at call sites
- tqdm `mininterval`, `unit`, formatting details
- Zombie threshold env var name (follow `PAPERFORGE_*` convention)

</decisions>

<canonical_refs>
## Canonical References

### Requirements
- `.planning/REQUIREMENTS.md` §REL-01 — tenacity retry spec (exceptions, backoff config)
- `.planning/REQUIREMENTS.md` §REL-02 — meta.json schema extensions
- `.planning/REQUIREMENTS.md` §REL-03 — zombie detection threshold
- `.planning/REQUIREMENTS.md` §REL-04 — batch resilience requirement
- `.planning/REQUIREMENTS.md` §OBS-04 — tqdm progress bar spec (stderr, auto-disable, --no-progress)

### Prior Decisions
- `.planning/phases/14-shared-utilities-extraction/14-CONTEXT.md` — _utils.py leaf module constraint (D-01, D-04)
- `.planning/phases/13-logging-foundation/13-CONTEXT.md` — global --verbose pattern (D-04), stdout/stderr boundary (D-07)

### Source Code
- `paperforge/worker/ocr.py:1126-1285` — run_ocr() function to be modified (upload l.1256-1269, poll l.1171-1222, meta.json writes l.1188/1221/1246/1253/1267/1275)
- `paperforge/worker/ocr.py:1-60` — Existing imports (requests, json, datetime, etc.)
- `paperforge/worker/_utils.py` — Leaf module pattern to follow for _retry.py and _progress.py

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_utils.py::write_json` — Already used for meta.json writes, no change needed
- `logging_config.py` — Single-purpose module pattern to replicate for _retry.py and _progress.py
- `paperforge/config.py` — Env var reading pattern (os.environ.get)

### Established Patterns
- Phase 13-14: Leaf modules under `paperforge/worker/` import only stdlib + paperforge.config
- Phase 13-14: Single-purpose modules follow logging_config.py precedent (~69 lines)
- Phase 13: `--verbose` global flag — parser pattern in cli.py

### Integration Points
- `paperforge/worker/_retry.py` — New file alongside _utils.py
- `paperforge/worker/_progress.py` — New file alongside _utils.py
- `paperforge/worker/ocr.py` — Import from _retry and _progress, modify run_ocr()
- `paperforge/cli.py` — Add `--no-progress` to root parser
- `pyproject.toml` — Add `tenacity` and `tqdm` to `[project.dependencies]`

</code_context>

<specifics>
## Specific Ideas

- "_retry.py 和 _progress.py 保持 leaf，和 _utils.py 一样只 import 外部库 + stdlib"
- "--no-progress 放在 root parser，和 --verbose 对齐"
- "poll 的 raise_for_status 也要 catch，不能 crash 整个 batch"
- "tqdm 输出到 stderr，不影响 stdout 的 piped 输出"

</specifics>

<deferred>
## Deferred Ideas

- OCR error message improvement (OBS-05) — Phase 17, includes classify_error integration
- E2E tests for retry behavior — Phase 19

</deferred>

---

*Phase: 16-retry-progress-bars*
*Context gathered: 2026-04-27*
