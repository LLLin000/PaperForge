# Phase 8: Deep Helper Deployment And Sandbox Regression Gate - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 08-deep-helper-deployment
**Areas discussed:** ld_deep importability fix, OCR-complete fixture design, Smoke test scope & structure, Doc verification approach, Prepare error handling
**Mode:** discuss

---

## ld_deep.py Importability Fix

| Option | Description | Selected |
|--------|-------------|----------|
| Install-based fix | `pip install -e .` in setup_wizard — paperforge always importable | ✓ |
| Bootstrap self-fix | sys.path insertion in ld_deep.py — self-contained but fragile path guessing | |
| Wrapper script | .bat/.ps1 wrapper sets PYTHONPATH — no ld_deep.py changes, more maintenance burden | |

**User's choice:** Install-based fix (`pip install -e .`)
**Notes:** D-03: extend doctor to check `ld_deep.py` importability via `python -c "import ld_deep"`

---

## OCR-Complete Fixture Design

| Option | Description | Selected |
|--------|-------------|----------|
| Static fixture files | Pre-generated files in tests/sandbox/ocr-complete/ — simple, deterministic | ✓ |
| pytest fixture factory | Generator function mimicking generate_sandbox.py — flexible but complex | |
| Both | Static fixtures for regression + optional generator for coverage | |

**User's choice:** Static fixture files
**Notes:** Must produce figure-map.json, chart-type-map.json from realistic fulltext.md with real figure captions. `ld_deep.py prepare` runs against the fixture to produce the scaffold — not a separate generator.

---

## Smoke Test Scope & Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Extend pytest | Add to tests/test_smoke.py — reuse fixture_vault, existing patterns | ✓ |
| Standalone CLI script | New tests/run_smoke.py — manual orchestration, duplicates pytest | |
| Extended + new regression file | Both: extend test_smoke.py + add test_regression.py for REG-02 specifics | |

**User's choice:** Extend existing `tests/test_smoke.py`
**Notes:** New test sequence: setup → selection-sync → index-refresh → OCR preflight → deep-reading queue → ld_deep import → ld_deep prepare → doc command extraction. Each REG-02 regression item must have a specific assertion.

---

## Doc Verification Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Extract-and-execute from docs | Smoke test extracts commands from README/INSTALLATION/AGENTS/command/*.md and runs them | ✓ |
| Assert commands in docs | Inverse: record canonical commands, check they appear in docs | |
| Manual check | Documented in release checklist — zero automation | |

**User's choice:** Extract-and-execute from docs
**Notes:** Part of smoke test, not separate. Targets paperforge CLI, python -m paperforge, ld_deep.py commands.

---

## Prepare Error Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Roll back on failure | Delete all partial output from current prepare run if any step fails | ✓ |
| Keep partial state | Leave partial output with clear error for debugging | |
| Atomic temp-dir swap | Write to temp dir, atomic rename on full success — robust but complex | |

**User's choice:** Roll back on failure
**Notes:** Steps: figure-map.json → chart-type-map.json → scaffold insertion. Delete steps 1..N-1 outputs if step N fails. Revert formal note scaffold to pre-prepare state.

---

## the agent's Discretion

- Exact fixture content for fulltext.md, figure-map.json, chart-type-map.json
- Doc command extraction regex/markdown parsing approach
- Rollback implementation details (track vs known paths)

## Deferred Ideas

- Standalone regression test file — not needed; extend test_smoke.py
- Real PaddleOCR network smoke test — explicitly out of scope per ROADMAP
- Fig./Tab. deep analysis content quality — Phase 8 only ensures scaffold structure
