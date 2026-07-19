# Phase 13: Logging Foundation - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Create `paperforge/logging_config.py` as the single entry point for configuring Python stdlib logging. Add structured, level-based logging for diagnostic/trace/error output (stderr) while preserving `print()` for user-facing formatted output (stdout). Add `--verbose`/`-v` global flag. Zero behavioral change to piped output.

Requirements: OBS-01, OBS-02, OBS-03

Out of scope:
- Progress bars (OBS-04 — Phase 16)
- Actionable OCR error messages (OBS-05 — Phase 17)
- Replacing existing `print()` calls for user-facing output (preserved as-is)
</domain>

<decisions>
## Implementation Decisions

### Logger Hierarchy
- **D-01:** Use `logging.getLogger(__name__)` standard pattern
  - Produces natural hierarchy: `paperforge.worker.sync`, `paperforge.commands.sync`, etc.
  - Enables per-module filtering for debugging
- **D-02:** Entry point: `paperforge/logging_config.py` with a single `configure_logging(verbose: bool)` function
- **D-03:** `configure_logging()` uses `logging.basicConfig()` or `dictConfig()` to set root `paperforge` logger to INFO (default) or DEBUG (when `--verbose`)

### Verbose Flag
- **D-04:** Add `--verbose`/`-v` to the **root parser** (global flag), inherited by all subcommands
  - Replaces current per-command `--verbose` on `deep-reading` and `repair`
  - Maintains backward compat: those commands still accept the flag
- **D-05:** `--verbose` maps to `logging.DEBUG` level on the `paperforge` logger
- **D-06:** `PAPERFORGE_LOG_LEVEL` env var controls default log level (accepts `DEBUG`/`INFO`/`WARNING`/`ERROR`); default is `INFO`

### Dual-Output Boundary
- **D-07:** Classification of existing `print()` calls:
  - **stdout (preserve as `print()`):** `status.py` (system info), `sync.py` (dry-run output), `deep_reading.py` (queue stats), `ocr.py` (command progress)
  - **stderr (migrate to `logging`):** `repair.py` (diagnostic `[repair]` messages), `cli.py` (error messages already on stderr)
- **D-08:** `print()` kept for user-facing stdout output — downstream consumers (Agent scripts, pipes) rely on stdout format stability

### Error and Edge Case Handling
- **D-09:** Invalid `PAPERFORGE_LOG_LEVEL` value → silent fallback to `WARNING`
- **D-10:** Early-boot logging (before `configure_logging()` is called) → use `logging.basicConfig(level=WARNING)` as an initial setup; `configure_logging()` replaces this with full configuration when called

### the agent's Discretion
- Exact formatter style (timestamp format, module name display)
- Whether to use `dictConfig` or programmatic `basicConfig`
- Handler configuration (StreamHandler to stderr, format string details)

</decisions>

<canonical_refs>
## Canonical References

### Requirements (Phase 13 scope)
- `.planning/REQUIREMENTS.md` — OBS-01 (logging_config.py), OBS-02 (dual-output), OBS-03 (--verbose flag)

### Architecture and Prior Decisions
- `.planning/STATE.md` §v1.4 Key Decisions — Dual-output strategy confirmed
- `docs/ARCHITECTURE.md` — Two-layer design, data flow

### Existing Code
- `paperforge/cli.py` — Root parser design, existing --verbose on deep-reading + repair
- `paperforge/config.py` — Config loading pattern (used as reference for logging_config.py single-purpose module)
- `paperforge/worker/repair.py` — `[repair]` diagnostic print() calls to migrate
- `paperforge/commands/deep.py` — Current verbose pass-through pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `paperforge/cli.py` line 171: existing `--verbose` on `deep-reading` subcommand — pattern to generalize to root parser
- `paperforge/cli.py` line 333: already imports `logging.getLogger("paperforge")` in `base-refresh` handler — shows the import pattern works

### Established Patterns
- Worker modules import via `_get_run_*()` lazy loader pattern in `commands/`
- CLI dispatches via `commands/*.run(args)` pattern — args carry all parsed values
- Config module pattern: single-purpose file (`config.py`) with pure functions

### Integration Points
- `paperforge/cli.py` `main()` — Add `configure_logging()` call after arg parsing, before command dispatch
- `paperforge/commands/*.run(args)` — Existing verbose flag on `args` extended via root parser
- Each worker module — Add `logger = logging.getLogger(__name__)` at module level
- `paperforge/worker/__init__.py` — No changes needed (logging config is external to workers)

</code_context>

<specifics>
## Specific Ideas

- "Logging 只接管诊断信息（stderr），不碰用户看到的输出（stdout）。piped commands 必须保持原样。"
- "PAPERFORGE_LOG_LEVEL 是唯一的配置项，不需要配置文件或 YAML 配置"
</specifics>

<deferred>
## Deferred Ideas

- Progress bars (tqdm) — Phase 16 (OBS-04)
- Actionable OCR error message improvement — Phase 17 (OBS-05)
- File-based logging (rotating log files) — not in scope; stderr-only for v1.4
- Structured JSON logging — not in scope; plain text for v1.4

None — discussion stayed within phase scope
</deferred>

---

*Phase: 13-logging-foundation*
*Context gathered: 2026-04-27*
