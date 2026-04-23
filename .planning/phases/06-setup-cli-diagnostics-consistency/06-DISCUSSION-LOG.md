# Phase 6: Setup, CLI, And Diagnostics Consistency - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-04-23
**Phase:** 06-setup-cli-diagnostics-consistency
**Mode:** assumptions
**Areas analyzed:** Field name mismatch, PaddleOCR env var, Doctor per-domain exports, HTTP 405 handling, Vault prefill, ProgressBar, Fallback command

---

## Assumptions Presented

| Assumption | Confidence | Evidence |
|-----------|-----------|----------|
| `literature_script` vs `ld_deep_script` mismatch in ld-deep.md | Confident | cli.py line 284, command/ld-deep.md lines 170, 194 |
| PaddleOCR env var name inconsistency (TOKEN vs KEY) | Confident | setup_wizard.py line 1016, literature_pipeline.py line ~2933, ocr_diagnostics.py line 28 |
| Doctor validates only library.json, not all *.json | Confident | literature_pipeline.py line ~2910 |
| L2 check has no explicit HTTP 405 handling | Confident | ocr_diagnostics.py lines 64-69 |
| VaultStep Input has no value prefilled from --vault arg | Confident | setup_wizard.py line 498, VaultStep compose |
| ProgressBar provides visible progress | Likely | setup_wizard.py lines 1322-1324, 1360-1364 |
| python -m paperforge_lite is the fallback command | Likely | cli.py has __main__.py entry point |

## Corrections Made

No corrections — all assumptions confirmed by user.

## Auto-Resolved

None — user confirmed all assumptions directly.

## External Research

None — all findings from codebase analysis.

---

*Discussion log created: 2026-04-23*
