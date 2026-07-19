---
phase: 08-deep-helper-deployment
status: passed
verifier: gsd-executor + orchestrator
date: 2026-04-24
---

# Phase 8 Verification: Deep Helper Deployment And Sandbox Regression Gate

## Phase Goal

Turn the manual sandbox audit into an automated release gate that covers deployed Agent helper importability and `/LD-deep prepare`.

## Requirement IDs Verified

| ID | Description | Status |
|----|-------------|--------|
| DEEP-04 | Deployed ld_deep.py runs without PYTHONPATH | PASS |
| DEEP-05 | Doctor checks importability, not just directory | PASS |
| DEEP-06 | OCR-complete fixture with figure-map + chart-type-map | PASS |
| REG-01 | Smoke test covers setup, doctor, prepare, queue | PASS |
| REG-02 | Regression assertions for prior audit findings | PASS |
| REG-03 | Doc commands are extractable and executable | PASS |
| D-13 | Rollback deletes partial files on failure | PASS |
| D-14 | Rollback restores original note text on failure | PASS |
| D-15 | Rollback tested for both figure-map and scaffold failures | PASS |

## Success Criteria Check

1. **Deployed ld_deep.py runs without PYTHONPATH:**
   - `test_ld_deep_import_from_deployed` passes — uses `importlib.util.spec_from_file_location` successfully
   - `test_regression_agent_importability` passes — script runs without PYTHONPATH
   - Status: PASS

2. **OCR-complete fixture produces scaffold:**
   - `tests/sandbox/ocr-complete/TSTONE001/` contains fulltext.md, figure-map.json, chart-type-map.json, meta.json
   - `test_prepare_produces_scaffold` passes — figure-map + chart-type-map + 精读 section created
   - Status: PASS

3. **One smoke command fails if regression reappears:**
   - `pytest tests/test_smoke.py tests/test_prepare_rollback.py` = 17/17 PASSED
   - Tests cover: setup wizard, doctor importability, env names, per-domain exports, ld_deep import, prepare scaffold, queue output, worker paths, doc commands, metadata fields, PDF paths
   - Status: PASS

4. **Docs verified against smoke test commands:**
   - `test_doc_commands_executable` extracts and runs commands from README.md, INSTALLATION.md, AGENTS.md, command/*.md
   - All extracted commands execute without crash or import error
   - Status: PASS

## Automated Checks

| Check | Result |
|-------|--------|
| pytest tests/test_smoke.py | 14/14 PASSED |
| pytest tests/test_prepare_rollback.py | 3/3 PASSED |
| No live PaddleOCR API calls | VERIFIED |
| Fixtures committed to git | VERIFIED |
| Doctor importability check | VERIFIED |

## Issues Found

- **Pre-existing:** `tests/test_base_preservation.py` and `tests/test_base_views.py` fail with `ModuleNotFoundError: No module named 'pipeline'`. These are Phase 7 tests with import issues unrelated to Phase 8.
- **Auto-fixed during execution:** Python 3.14 dataclass import workaround needed for `importlib.util` imports.

## Human Verification

None required — all criteria are automated.

## Gaps

None.

---
*Verified: 2026-04-24*
