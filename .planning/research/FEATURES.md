# Feature Research

**Domain:** Python CLI application — code health, observability, and UX polish
**Researched:** 2026-04-25
**Confidence:** HIGH

## Feature Landscape

All features below were identified by a comprehensive codebase audit of the PaperForge Lite v1.3 codebase (~7,757 lines, 7 worker modules, 205 pytest tests, 97 `print()` calls, ~1,610 lines of duplicated utility code). Research conducted by direct file inspection of every module.

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Structured logging (levels, file output) | Every CLI app in 2026 uses `logging` — print()-only feels amateurish. Users can't redirect output, can't filter by severity, can't persist logs for debugging. | MEDIUM | 97 print() calls across 11 files. Replace with `logging.getLogger(__name__)`. Preserve CLI simplicity — add `--verbose/-v` and `--log-file` flags. |
| Progress indicators for long operations | OCR uploads take minutes. Users stare at a blank terminal wondering if it hung. Every modern CLI app shows spinners or progress bars. | LOW | Affects only the OCR worker's upload/status-poll loops. Use `rich.progress` (already in transient deps via Textual's `rich` dependency) for spinners + progress bars. |
| Clear error visibility on failure | When OCR fails, users currently get a raw print() and must grep meta.json to understand why. They expect structured, actionable error output. | MEDIUM | Tied to logging migration. Add error codes (PF-OCR-001 etc.), always print the fix action with the error. |
| Zero orphaned legacy artifacts | README line 102-104 has a `python <resolved_worker_script>` code block dangling outside any fence — renders as broken Markdown. Embarrassing for a release-quality project. | TRIVIAL | Delete the 3 orphan lines. One-line fix. |
| DRY principle (no copy-paste utilities) | ~1,610 lines of identical utility code across ocr.py, sync.py, deep_reading.py — any bug fix must be replicated 3x. Developer expectations violated. | HIGH | Extract to `paperforge/worker/_utils.py`. Requires careful import surgery across 7 workers + commands + cli.py. Highest-risk table stakes item. |
| Single source of truth for deep-reading queue | `worker/deep_reading.py` and `ld_deep.py` both scan library-records for deep-reading queue status. Having two implementations means bugs can diverge — users see different queues from CLI vs Agent. | MEDIUM | Merge into `paperforge/worker/_utils.py` or `paperforge/commands/deep.py`. The worker version is the canonical one; ld_deep.py should call it. |
| Pre-commit hooks | Standard for any Python project with >1 contributor. Catches formatting, imports, and lint issues before they hit CI. Zero hooks currently. | LOW | Add `.pre-commit-config.yaml` with `ruff`, `isort`, trailing-whitespace, end-of-file-fixer. |
| CONTRIBUTING.md | GitHub-standard file. Without it, potential contributors don't know how to set up dev env, run tests, or follow code style. | TRIVIAL | Standard template — dev setup, test commands, code style, PR process. |
| CHANGELOG.md | Keeps users and contributors informed about what changed. Critical for a self-updating CLI app where users run `paperforge update`. | TRIVIAL | Populate from git history + milestone notes; maintain going forward. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| One-click OCR→deep-reading flow | Currently users must: (1) open library-record in Obsidian, (2) edit `do_ocr: true`, (3) run `paperforge ocr`, (4) wait, (5) edit `analyze: true`, (6) run `/pf-deep`. A `paperforge process` command that chains all steps automates the mechanical parts. Drastically reduces friction for new users. | MEDIUM | Requires smart defaults: auto-set `do_ocr=true` when `has_pdf=true`, auto-set `analyze=true` after OCR completes. Must respect user opt-out. Depends on logging migration for clear progress output. |
| OCR retry with exponential backoff | PaddleOCR API is rate-limited and occasionally returns transient errors. Currently: single attempt, manual retry. With backoff: 3 retries with 1s/2s/4s delay, only on 429/503 statuses. Shows sophistication. | LOW | Configurable via `paperforge.json`: `ocr.retry_max` and `ocr.retry_backoff_base`. Wrap in `_utils.py` shared retry decorator. |
| Chart-reading guide cross-reference index | 19 chart-reading guides exist but the agent prompt only lists a few inline examples. A generated `CHART_GUIDES_INDEX.md` with a table-of-contents mapping chart types to guide files reduces agent hallucination and ensures all 19 guides get used. | LOW | Generate from file listing during `paperforge update` or setup. Embed a mapping dict in `ld_deep.py` that the agent prompt references. |
| Unified agent/CLI brand | Currently `/pf-*` and `paperforge *` are documented as "same thing, two ways to call" — but users see `/pf-sync` and `paperforge sync` as potentially different commands. A consistent mental model (documented in AGENTS.md + README) where `/pf-*` is explicitly "Agent wrapper of CLI command" clears confusion. | TRIVIAL | Add a table to AGENTS.md mapping every `/pf-*` to its `paperforge` equivalent. Add "(same as `paperforge sync`)" to command help text. |
| E2E integration tests | 205 unit tests exist but no end-to-end test that runs the full pipeline: setup wizard → sync → ocr (mocked PaddleOCR) → deep-reading queue → repair. Catches integration bugs that unit tests miss. | MEDIUM | Build on existing sandbox test infrastructure (`tests/sandbox/`). Mock PaddleOCR API with `responses` or `httpx`. |
| Dead code cleanup | ~1,610 lines of duplicated code, plus unused imports (html, csv, hashlib, subprocess, sys, tempfile, urllib.parse, zipfile, ET, requests, fitz, PIL in modules that don't use them). A clean codebase is a competitive signal of project quality. | LOW (effort) / MEDIUM (risk) | Systematic: use `vulture` or `ruff check --select F401` to find dead code. Each import removal must be verified against runtime usage. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Daemon process for auto-detecting Zotero changes | "I want OCR to happen automatically when I add a paper." | Violates Lite architecture (no daemon, no cloud service). Adds process management complexity (start/stop/restart), conflicts with Obsidian's single-user model, and introduces file-watching race conditions. | Keep the "explicit trigger" model. Improve it with `paperforge process` one-click flow. Document the 1-command workflow prominently. |
| Web UI for OCR queue management | "Obsidian Base views are clunky." | Adds an entire web stack (Flask/FastAPI + frontend) to a local-first project. Requires port management, authentication concerns, and browser dependency. Massive scope creep. | Enhance Obsidian Base views with better filters, or add a `paperforge queue --interactive` TUI using Textual (already a dependency). |
| Auto-trigger deep-reading Agent after OCR completes | "I want it fully automatic." | Agent deep-reading requires LLM reasoning, costs tokens, and needs user judgment (which papers deserve deep reading?). Automatic triggering wastes resources and violates the intentional "user decides" architecture. | Keep the explicit `/pf-deep` trigger. Add `--auto` flag to `paperforge process` that skips to the "ready for /pf-deep" stage with a clear prompt. |
| PostgreSQL or SQLite database instead of Markdown files | "JSON/Markdown is slow for large libraries." | This is an Obsidian-native project. Markdown files ARE the database. Replacing them breaks Obsidian integration (wikilinks, Base views, search). Adds dependency, breaks the "plain text, forever" philosophy. | Optimize file I/O: add caching for repeated reads, batch writes for bulk operations. |
| Real-time progress over WebSocket for OCR status | "I want a live dashboard." | Requires a server, WebSocket protocol, and browser. Violates local-first constraint. Massive complexity for a feature of marginal value (OCR is async, minutes-long — polling is fine). | Use `rich.live` for auto-refreshing terminal status display. Add `paperforge ocr --watch` that polls meta.json every 5s. |

## Feature Dependencies

```
paperforge/worker/_utils.py (shared utilities extraction)
    └──requires──> Full codebase audit (identify duplication)

Structured logging (print() → logging)
    └──enhances──> Progress indicators (log levels control verbosity)
    └──enhances──> Error visibility (structured log output with codes)
    └──depends_on──> _utils.py extraction (shared logger config)

OCR→deep-reading one-click flow
    └──depends_on──> Logging migration (for progress output)
    └──depends_on──> OCR retry/backoff (for reliability)
    └──enhances──> Unified agent/CLI brand (single `paperforge process` command)

Merge duplicate deep-reading queue
    └──depends_on──> _utils.py extraction (shared scanning function)
    └──blocked_by──> ld_deep.py still has independent queue logic

Pre-commit hooks
    └──enables──> Dead code cleanup (ruff catches unused imports)
    └──enables──> Consistency audit (automated on commit)

E2E integration tests
    └──depends_on──> Logging migration (testable structured output)
    └──depends_on──> _utils.py extraction (mockable shared modules)

README artifact fix ──independent──> (trivial, no dependencies)

CONTRIBUTING.md + CHANGELOG.md ──independent──> (docs only, no code deps)

Chart-reading cross-reference ──enhances──> Agent prompt quality
    └──depends_on──> chart-type-map.json generation (already exists)
```

### Dependency Notes

- **_utils.py extraction is the critical path**: All code-health features (logging, dedup, retry) depend on having a single shared utilities module. Must be Phase 1 of v1.4.
- **Logging migration is the second critical path**: Progress indicators, error visibility, and testability of CLI output all depend on structured logging.
- **OCR workflow simplification can ship independently** if logging is done first, since it needs progress output.
- **README artifact, CONTRIBUTING.md, CHANGELOG.md are fully independent** — can ship in any order, any phase.
- **E2E tests can be built incrementally** — start with setup_wizard tests (no logging dependency), add pipeline tests after logging.

## MVP Definition

### Launch With (v1.4 — code health & UX hardening)

Minimum viable product — what's needed to call this milestone done.

- [ ] **Extract `paperforge/worker/_utils.py`** — Eliminate ~1,610 lines of duplicate code across ocr.py, sync.py, deep_reading.py. Single source of truth for: env loading, JSON I/O, YAML helpers, slugify, journal DB, vault config delegation, pipeline paths, domain config. This is the foundation for all other code-health work.
- [ ] **Replace print() with logging** — Add `logging` module with INFO/WARNING/ERROR levels, `--verbose` flag, `--log-file` option. Preserve CLI simplicity by default. Affects 97 print() calls across all workers + CLI.
- [ ] **Merge duplicate deep-reading queue** — `ld_deep.py::scan_deep_reading_queue()` calls the shared implementation in `_utils.py` (which wraps `worker/deep_reading.py` logic). Single canonical queue scanner.
- [ ] **OCR retry with exponential backoff** — 3 retries on transient failures (HTTP 429/503), configurable in `paperforge.json`. Prevents OCR jobs from silently failing on rate limits.
- [ ] **Fix README rendering artifact** — Remove orphaned lines 102-104 that render as broken Markdown.
- [ ] **Add pre-commit hooks** — `.pre-commit-config.yaml` with ruff, isort, trailing-whitespace, end-of-file-fixer.
- [ ] **Add CONTRIBUTING.md + CHANGELOG.md** — Standard project health files.

### Add After Validation (v1.4.x or v1.5)

Features to add once core code health is established.

- [ ] **One-click `paperforge process` command** — Chains OCR→deep-reading readiness into a single command. Trigger: after users report friction with the multi-step workflow.
- [ ] **Progress indicators for OCR** — `rich.progress` spinners during upload/poll cycles. Trigger: after logging migration stabilizes and user feedback on long waits.
- [ ] **Chart-reading cross-reference index** — Generated guide index for agent prompt. Trigger: after agent usage patterns show underutilization of chart guides.
- [ ] **E2E integration tests** — Full pipeline sandbox tests with mocked PaddleOCR. Trigger: after `_utils.py` extraction stabilizes module boundaries.
- [ ] **Setup wizard tests** — Textual TUI tests. Trigger: after Textual test harness is set up (requires `textual` testing utilities).
- [ ] **Dead code cleanup** — Remove unused imports and dead functions. Trigger: after pre-commit hooks enforce import hygiene.

### Future Consideration (v2+)

Features to defer until code health is fully established.

- [ ] **Unified agent/CLI help text** — Cross-reference table in AGENTS.md. Defer: the current documentation is adequate; this is polish.
- [ ] **OCR auto-trigger on sync** — `paperforge sync --with-ocr`. Defer: needs careful UX design to avoid surprising users with API calls.
- [ ] **`paperforge queue --interactive` TUI** — Textual-based queue manager. Defer: Obsidian Base views are the intended interface; TUI is a nice-to-have.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Extract shared `_utils.py` | MEDIUM (invisible but reduces bugs) | HIGH (1,610 lines to refactor) | P1 |
| Replace print() with logging | HIGH (debuggability, observability) | MEDIUM (97 call sites, config wiring) | P1 |
| Merge duplicate deep-reading queue | MEDIUM (consistency) | LOW (~50 lines of reconciliation) | P1 |
| OCR retry with backoff | HIGH (prevents silent failures) | LOW (wrap in retry decorator) | P1 |
| Fix README artifact | LOW (cosmetic but embarrassing) | TRIVIAL (delete 3 lines) | P2 |
| Pre-commit hooks | MEDIUM (prevents future debt) | LOW (1 config file) | P1 |
| CONTRIBUTING.md + CHANGELOG.md | LOW (docs) | TRIVIAL (templates) | P2 |
| One-click OCR→deep-reading flow | HIGH (UX friction reduction) | MEDIUM (new command module) | P2 |
| Progress indicators for OCR | HIGH (UX, eliminates "did it hang?") | LOW (rich library, ~30 lines) | P2 |
| Better error visibility | HIGH (actionable error messages) | MEDIUM (error code system + log formatting) | P2 |
| Chart-reading cross-reference | MEDIUM (Agent quality) | LOW (generate from file listing) | P3 |
| E2E integration tests | MEDIUM (prevent regressions) | MEDIUM (new test fixtures) | P2 |
| Setup wizard tests | LOW (Textual testing is niche) | MEDIUM (Textual test harness) | P3 |
| Dead code cleanup | LOW (existing code works) | LOW (automated with ruff) | P3 |

**Priority key:**
- P1: Must have for v1.4
- P2: Should have for v1.4 if bandwidth permits
- P3: Nice to have, future consideration

## Competitor Feature Analysis

PaperForge Lite has no direct open-source competitors (Obsidian + Zotero literature pipeline with OCR + Agent deep reading is a unique combination). Closest analogues:

| Feature | Zotero (native) | Obsidian Zotero Integration plugin | PaperForge Lite v1.3 | PaperForge Lite v1.4 target |
|---------|-----------------|-----------------------------------|----------------------|---------------------------|
| PDF OCR | Via Zotero PDF reader | None | PaddleOCR async, state machine | + retry/backoff, structured errors, progress indicators |
| Progress feedback | Built-in progress bar | N/A | print() only | Rich spinners + progress bars |
| Error visibility | Modal dialogs | Console (dev tools) | print() to stdout, grep meta.json | Structured log output with error codes + fix suggestions |
| CLI workflow | None | None | 5 CLI commands | + `paperforge process` one-click flow |
| Logging | Internal Zotero logs | Plugin console | print() only | Python logging with levels + file output |
| Deep reading | None | None | `/pf-deep` with 19 chart guides | + cross-reference index for chart guides |
| Code health | Closed source | TypeScript, unknown | ~1,610 dup lines, 97 print() | DRY, structured, testable |
| Project docs | N/A | README only | README + AGENTS.md + 10 ADRs | + CONTRIBUTING.md + CHANGELOG.md |

## Sources

- Direct codebase inspection: `paperforge/worker/ocr.py` (1376 lines), `paperforge/worker/sync.py` (1444 lines), `paperforge/worker/deep_reading.py` (324 lines), `paperforge/worker/repair.py` (548 lines), `paperforge/worker/status.py` (625 lines), `paperforge/worker/update.py` (462 lines), `paperforge/worker/base_views.py` (516 lines)
- `paperforge/skills/literature-qa/scripts/ld_deep.py` (1420 lines) — agent-side deep reading helpers
- `paperforge/cli.py` (371 lines) — CLI entry point
- `paperforge/commands/` (338 lines across 6 modules) — command dispatch layer
- `paperforge/config.py` (299 lines) — shared config resolver
- `README.md` — artifact on lines 102-104
- `paperforge/skills/literature-qa/prompt_deep_subagent.md` (298 lines) — agent prompt with chart-reading references
- `paperforge/skills/literature-qa/chart-reading/` — 19 chart-reading guides
- 205 pytest tests in `tests/`
- `.planning/PROJECT.md` — project context and milestone constraints
- No existing `.pre-commit-config.yaml`, `CONTRIBUTING.md`, or `CHANGELOG.md`

---
*Feature research for: PaperForge Lite v1.4 Code Health & UX Hardening*
*Researched: 2026-04-25*
