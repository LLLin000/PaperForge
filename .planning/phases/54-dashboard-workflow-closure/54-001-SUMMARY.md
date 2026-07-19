# Phase 54 Plan 001: UX Contract + Journey Tests — Summary

**Plan:** 54-001
**Phase:** 54-dashboard-workflow-closure
**Subsystem:** Testing — L5 User Journey Tests
**Tags:** ux-contract, journey-tests, conftest, onboarding, daily-workflow
**Date:** 2026-05-09

## Objective

Define the UX contract document (`docs/ux-contract.md`) and implement Level 5 user journey tests for the two critical user workflows — new user onboarding and daily paper workflow.

## Results

- **docs/ux-contract.md**: 6862 chars, 4 complete workflows (install, sync, OCR, dashboard) with verifiable step sequences.
- **tests/journey/**: conftest, test_onboarding.py, test_daily_workflow.py — all passing.
- Both tests marked `@pytest.mark.journey`, excluded from default CI gate.

## Key Decisions

- Isolation guard uses `any(x in str(vault).lower() for x in ("tmp", "temp"))` to support both POSIX (`/tmp/`) and Windows (`Temp\`) temp directories.
- Journey tests run `paperforge` via subprocess in disposable tmp_path vaults.
- Established vault fixture creates a second domain (sports_medicine) for multi-domain workflow testing.
- Onboarding test uses `mock_ocr_success` context manager for OCR step (requires in-process mock when testing via subprocess).

## Deviations from Plan

### Rule 2 — Missing Critical Functionality

1. **Cross-platform isolation guard**: Original `assert "tmp" in str(vault)` fails on Windows where `tempfile.mkdtemp()` writes to `Temp\`. Fixed to case-insensitive check for both `tmp` and `temp`.

## Verification

```
python -m pytest tests/journey/ -m journey -v --tb=short --timeout=120
> 2 passed
python -m pytest tests/chaos/ -m chaos -v --tb=short --timeout=120
> 13 passed, 1 skipped
```

## Artifacts

| File | Status |
|------|--------|
| `docs/ux-contract.md` | Created (6862 chars, 4 workflows) |
| `tests/journey/__init__.py` | Created |
| `tests/journey/conftest.py` | Created (3 fixtures: fresh/established vault + CLI invoker) |
| `tests/journey/test_onboarding.py` | Created (6-step new user journey) |
| `tests/journey/test_daily_workflow.py` | Created (5-step existing user adds paper) |
