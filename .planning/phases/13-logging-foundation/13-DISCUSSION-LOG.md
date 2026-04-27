# Phase 13: Logging Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 13-logging-foundation
**Areas discussed:** Logger hierarchy design, Verbose flag design, Dual-output boundary rules, Error and edge case handling

---

## Logger Hierarchy Design

| Option | Description | Selected |
|--------|-------------|----------|
| `__name__` standard pattern | Each module uses `logging.getLogger(__name__)`, natural hierarchy | ✓ |
| Flat naming | Short names like 'sync', 'ocr' — no hierarchy | |
| Mixed mode | Workers use hierarchy, CLI commands use flat | |

**User's choice:** `__name__` standard pattern (recommended)
**Notes:** N/A

---

## Verbose Flag Design

| Option | Description | Selected |
|--------|-------------|----------|
| Global --verbose | Add to root parser, inherited by all subcommands | ✓ |
| Per-command wiring | Each command adds its own --verbose | |

**User's choice:** Global --verbose (recommended)
**Notes:** Maintain backward compat for existing per-command `--verbose` on deep-reading and repair

---

## Dual-Output Boundary Rules

| Option | Description | Selected |
|--------|-------------|----------|
| Agree with classification | status/sync/deep-reading/ocr → stdout (print); repair → stderr (logging) | ✓ |
| repair also stdout | Repair reports are user-triggered, should go to stdout | |
| Agent discretion | Decide case by case at implementation time | |

**User's choice:** Agree with classification
**Notes:** N/A

---

## Error and Edge Case Handling

### Invalid PAPERFORGE_LOG_LEVEL

| Option | Description | Selected |
|--------|-------------|----------|
| Silent fallback to WARNING | Simplest, no error interruption | ✓ |
| Print warning then fallback | Informs user about invalid config | |
| Error exit | Strict mode, interrupts workflow | |

**User's choice:** Silent fallback to WARNING (recommended)
**Notes:** N/A

### Early-boot logging

| Option | Description | Selected |
|--------|-------------|----------|
| basicConfig then replace | Initial WARNING setup, replaced by configure_logging() later | ✓ |
| Delay all logs | NullHandler only, no logs before config | |

**User's choice:** basicConfig then replace (recommended)
**Notes:** N/A

---

## The agent's Discretion

- Exact formatter style (timestamp format, module name display)
- Whether to use dictConfig or programmatic basicConfig
- Handler configuration (StreamHandler to stderr, format string details)

## Deferred Ideas

- Progress bars (tqdm) — Phase 16
- Actionable OCR error message improvement — Phase 17
- File-based logging — not in scope for v1.4
- Structured JSON logging — not in scope for v1.4
