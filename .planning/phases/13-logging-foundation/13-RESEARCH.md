# Research: Phase 13 — Logging Foundation

**Research Date:** 2026-04-27
**Audit Type:** Codebase `print()` landscape, CLI parser structure, logging integration points
**Phase Requirements:** OBS-01, OBS-02, OBS-03

---

## 1. Current `print()` Landscape

### 1.1 Stdout — User-Facing Output (PRESERVE as `print()`)

These are the summary/status lines that users and downstream consumers (Agent scripts, pipes) rely on. They MUST remain on stdout unchanged.

| File | Line | Statement | Classification |
|------|------|-----------|----------------|
| `worker/sync.py` | 881 | `print(f'selection-sync: wrote {written} records, updated {updated} records')` | User-facing summary |
| `worker/sync.py` | 1255 | `print(f'search: task written -> {task_path}')` | User-facing summary |
| `worker/sync.py` | 1402 | `print(f'index-refresh: wrote {len(index_rows)} index rows')` | User-facing summary |
| `worker/sync.py` | 1442 | `print(f'index-refresh: cleaned {deleted_count} orphaned records...')` | User-facing summary |
| `worker/deep_reading.py` | 322 | `print(f'deep-reading: synced {synced} records, {len(pending_queue)} pending')` | User-facing summary |
| `worker/ocr.py` | 71 | `print(f"[INFO] Processing specific key: {key}")` | User-facing status |
| `worker/ocr.py` | 1374 | `print(f'ocr: updated {changed} records')` | User-facing summary |
| `worker/status.py` | 598-613 | `print('PaperForge Lite status')` + system info | User-facing status |
| `worker/status.py` | 518-540 | `print("PaperForge Lite Doctor")` + check results | User-facing status |
| `commands/sync.py` | 65-75 | `print("[DRY-RUN]")`, `print("  - selection-sync")` etc. | User-facing dry-run preview |
| `commands/ocr.py` | 15-24 | `print(f"OCR Doctor...")` etc. | User-facing diagnostic report |
| `commands/repair.py` | 53-54 | `print(repair summary)` | User-facing repair summary |

**Total stdout-only print() calls to preserve: ~12 locations**, mostly single-line status summaries at function exit points. These are the contract with downstream consumers.

### 1.2 Stderr — Diagnostic Output (MIGRATE to `logging`)

These are `[repair]`-tagged diagnostic messages in `worker/repair.py` and similar diagnostic print() calls. They belong on stderr via `logging`.

| File | Lines | Pattern | Migration Target |
|------|-------|---------|------------------|
| `worker/repair.py` | 236 | `print(f"[repair] error reading {record_path}: {e}")` | `logger.error()` |
| `worker/repair.py` | 303-304 | `print(f"[repair] error loading export for {domain}: {e}")` | `logger.error()` |
| `worker/repair.py` | 339-340 | `print(f"[repair] fixed path for {zotero_key}: ...")` | `logger.info()` |
| `worker/repair.py` | 357 | `print(f"[repair] cleared path_error for {zotero_key}")` | `logger.info()` |
| `worker/repair.py` | 360 | `print(f"[repair] {zotero_key} path still unresolved")` | `logger.warning()` |
| `worker/repair.py` | 363 | `print(f"[repair] {zotero_key} has empty pdf_path...")` | `logger.warning()` |
| `worker/repair.py` | 368 | `print(f"[repair] {zotero_key} has no pdf_path field")` | `logger.warning()` |
| `worker/repair.py` | 423 | `print(f"[repair] {zotero_key} meta validation error: ...")` | `logger.warning()` |
| `worker/repair.py` | 456 | `print(f"[repair] divergent: {zotero_key} | {div_reason}")` | `logger.info()` |
| `worker/repair.py` | 526 | `print(f"[repair] fixed {fixed_count} files for {zotero_key}")` | `logger.info()` |
| `worker/repair.py` | 533 | `print(f"[repair] Found {total} items with path errors: ...")` | `logger.info()` |
| `worker/repair.py` | 540 | `print(f"[repair] Fixed {fixed_count} PDF paths")` | `logger.info()` |
| `worker/repair.py` | 542 | `print("[repair] Tip: run with --fix-paths...")` | `logger.info()` |
| `worker/repair.py` | 544 | `print("[repair] No path errors found")` | `logger.info()` |
| `commands/ocr.py` | 78-87 | `print("\n[Auto-diagnose]...")`, `print("[WARN] ...")` | `logger.info()` / `logger.warning()` |
| `update.py` | 227 | `print(_color(msg, c))` via `_log()` | `logger.info()` |

**Total diagnostic print() calls to migrate: ~20 locations across 3 files** (repair.py, commands/ocr.py, update.py).

### 1.3 Already on Stderr

- `cli.py:269` — `print(f"Error: {exc}", file=sys.stderr)` — already goes to stderr, keep as-is or optionally migrate to `logger.error()`

---

## 2. Existing Logging Usage

Only **one module** currently uses Python logging:

- **`paperforge/pdf_resolver.py`**: `import logging` (line 8), `logger = logging.getLogger(__name__)` (line 12), `logger.error(...)` (line 66)

Additionally, `cli.py` line 333 uses a direct one-shot logging call:
```python
logger = __import__("logging").getLogger("paperforge")
logger.info(f"Refreshing Base views in {paths['bases']}")
```

This confirms that:
- `logging.getLogger("paperforge")` works and resolves correctly
- The pattern is compatible with the existing codebase
- No `basicConfig()` or handler setup exists yet anywhere in the codebase

---

## 3. CLI Parser Structure

### 3.1 Current `--verbose` Locations

| Subcommand | Line in cli.py | Current Behavior |
|------------|----------------|------------------|
| `deep-reading` | 171 | `--verbose, -v` — passes to `run_deep_reading(vault, verbose=True)` via `commands/deep.py` |
| `repair` | 178 | `--verbose, -v` — passes to `run_repair(vault, paths, verbose=True, ...)` via `commands/repair.py` |

### 3.2 Global Flag Opportunity

Currently, `--verbose` is per-subcommand. The plan is to promote it to a **root parser flag** (global), inherited by all subcommands. The `argparse` root parser supports `parser.add_argument("--verbose", "-v", ...)` before `add_subparsers()`, and subcommands automatically inherit parent parser arguments when using `parents=[]` — but only if explicitly wired.

**Alternative approach (simpler):** Add `--verbose` to the root parser, then access it via `args.verbose` in every command dispatch. argparse propagates root-level args to all subcommands by default when using `add_subparsers()` without `parents=[]` override.

**Current pass-through chain (deep-reading example):**
```
cli.py: build_parser() → adds --verbose to deep-reading subparser
cli.py: main() → args.verbose available on Namespace
cli.py: deep.run(args) → commands/deep.py: run(args) → run_deep_reading(vault, verbose=args.verbose)
worker/deep_reading.py: run_deep_reading(vault, verbose) → uses verbose for [repair] print branching
```

**For sync and ocr:** Neither `run_selection_sync(vault)` nor `run_ocr(vault)` accept `verbose` yet — these signatures need updating.

---

## 4. Integration Points

### 4.1 CLI Entry Point

The `configure_logging()` call MUST be inserted in `cli.py:main()` after arg parsing and before command dispatch. The current flow:

```
cli.py:main()
  1. _resolve_pipeline()
  2. _import_worker_functions()
  3. parser = build_parser()
  4. args = parser.parse_args(argv)
  5. vault = resolve_vault(...)
  6. load_simple_env(...)
  7. cfg = load_vault_config(...)
  8. args.vault_path, args.cfg, args.paths set
  9. Command dispatch: sync.run(args), ocr.run(args), etc.
```

**Insertion point:** After step 8, before step 9:
```python
from paperforge.logging_config import configure_logging
configure_logging(verbose=getattr(args, "verbose", False))
```

### 4.2 Each Worker Module

Add at module level:
```python
import logging
logger = logging.getLogger(__name__)
```

Then replace `print(...)` with:
| Old | New |
|-----|-----|
| `print(f"[repair] ...")` | `logger.info(...)`, `logger.warning(...)`, or `logger.error(...)` |
| (keep stdout print()) | (no change) |

### 4.3 Command Module Updates

| Module | Change |
|--------|--------|
| `commands/deep.py` | Already passes `verbose` — no change needed |
| `commands/repair.py` | Already passes `verbose` — no change needed |
| `commands/sync.py` | Add `verbose` passthrough: `run_selection_sync(vault, verbose=args.verbose)` |
| `commands/ocr.py` | Add `verbose` passthrough: `run_ocr(vault, verbose=args.verbose)` |
| `commands/status.py` | Add `verbose` passthrough if status needs debug output |

---

## 5. Key Findings Summary

| Finding | Detail |
|---------|--------|
| **12 stdout `print()` locations** | Must stay as `print()` — user-facing summaries |
| **~20 diagnostic `print()` locations** | In `repair.py` (mostly `[repair]` tagged), `commands/ocr.py`, `update.py` — migrate to `logging` |
| **1 existing logging user** | `pdf_resolver.py` — confirms pattern works |
| **1 existing one-shot logging call** | `cli.py:333` — confirms `logging.getLogger("paperforge")` resolves |
| **2 subcommands with `--verbose`** | `deep-reading`, `repair` — already wired through to worker |
| **3 subcommands without `--verbose`** | `sync`, `ocr`, `status` — need new verbose passthrough |
| **No `basicConfig()` anywhere** | First-time setup needed in `logging_config.py` |
| **diagnostic print() guard pattern** | All `[repair]` diagnostic calls are gated by `if verbose:` blocks |

---

## 6. Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Accidentally converting stdout print() to logging | Low | Clear classification in task actions (use the table above) |
| `logging.basicConfig()` called multiple times | Low | `configure_logging()` checks `logging.getLogger().hasHandlers()` |
| Verbose flag wiring missed for sync/ocr | Low | Explicit tasks for each command module |
| Early-boot logging before configure_logging() | Low | D-10: initial `basicConfig(level=WARNING)` as safety net |
| Import cycle from `logging_config.py` to worker modules | None | `logging_config.py` imports only stdlib `logging` — pure leaf module |
| Test patching of `cli.run_*` stubs | Low | Worker modules import logging at module level; tests can set log level independently |

---

*Research completed: 2026-04-27*
*Phase: 13-logging-foundation*
*Next: Spawn gsd-planner to create PLAN.md files*
