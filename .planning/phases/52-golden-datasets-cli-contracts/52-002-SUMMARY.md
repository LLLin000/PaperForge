---
phase: 52-golden-datasets-cli-contracts
plan: 002
subsystem: tests/cli
tags: [cli, contract-tests, snapshot, mock-ocr, pytest]
dependency-graph:
  requires: [52-001]
  provides: [53, 54]
  affects: [paperforge.cli, pyproject.toml]
tech-stack:
  added: [pytest-snapshot, responses, pytest-timeout, pytest-mock, coverage]
  patterns: [subprocess CLI invoker, snapshot-based output contracts, responses-based HTTP mocking]
key-files:
  created:
    - tests/cli/conftest.py
    - tests/cli/test_contract_helpers.py
    - tests/cli/test_json_contracts.py
    - tests/cli/test_text_contracts.py
    - tests/cli/test_error_codes.py
    - fixtures/ocr/mock_ocr_backend.py
  modified:
    - pyproject.toml
decisions:
  - "Exit code 2 for argparse errors accepted (Python stdlib behavior)"
  - "status --json output has nested 'ocr' object, not flat keys"
  - "Snapshot tests live in tests/cli/snapshots/ (pytest-snapshot default location)"
metrics:
  duration: ~25 min
  completed_date: 2026-05-08
---

# Phase 52 Golden Datasets & CLI Contracts — Plan 002 Summary

**One-liner:** CLI contract test suite — 27 tests across 11 test classes covering all 8 CLI commands (paths, status, sync, ocr, doctor, repair, context, setup) with snapshot-based output validation.

## Tasks Executed

### Task 1: CLI Test Infrastructure — conftest, helpers, mock OCR, pyproject.toml
- `tests/cli/conftest.py` with 3 fixtures: vault_builder, cli_invoker, mock_ocr_backend
- cli_invoker runs CLI commands via `subprocess.run([sys.executable, "-m", "paperforge", ...])` with disposable temp vaults
- `tests/cli/test_contract_helpers.py` with normalize_snapshot (cross-platform path, timestamp, version normalization), assert_valid_json, assert_json_shape
- `fixtures/ocr/mock_ocr_backend.py` with 4 context-managed mock modes: success, pending, error, timeout
- pyproject.toml updated with 5 new test dependencies and 7 pytest markers (unit, cli, e2e, journey, chaos, slow, snapshot)

### Task 2: CLI Contract Tests — all 7 commands + error codes
- `tests/cli/test_json_contracts.py`: TestPathsJson, TestStatusJson, TestContextJson (3 classes, 8 tests)
- `tests/cli/test_text_contracts.py`: TestSyncCli, TestOcrCli, TestDoctorCli, TestRepairCli, TestSetupCli (5 classes, 10 tests)
- `tests/cli/test_error_codes.py`: TestExitCodes, TestErrorOutput, TestCli02ErrorContract (3 classes, 9 tests)
- All 8 CLI commands covered: paths, status, sync, ocr, doctor, repair, context, setup
- Snapshot tests with pytest-snapshot for paths --json and status --json output contracts

## Deviations from Plan

### [Rule 1 - Bug] Fixed subprocess._clean_environ() compatibility
- **Found during:** Task 1 verification
- **Issue:** `subprocess._clean_environ()` doesn't exist in Python 3.14
- **Fix:** Replaced with `os.environ.copy()`
- **Files modified:** tests/cli/conftest.py

### [Rule 1 - Bug] Fixed normalize_snapshot for Windows paths
- **Found during:** Test execution
- **Issue:** regex only matched Unix `/tmp/pf_vault_` paths
- **Fix:** Added Windows path pattern `[A-Za-z]:[\\/][^\s"\']*pf_vault_[a-z0-9]+`
- **Files modified:** tests/cli/test_contract_helpers.py

### [Rule 1 - Bug] Updated status JSON contract to match actual CLI output
- **Found during:** Test execution
- **Issue:** Status --json output has nested `ocr` object and additional keys not in the expected shape
- **Fix:** Updated REQUIRED_KEYS and OPTIONAL_KEYS to match actual output
- **Files modified:** tests/cli/test_json_contracts.py, fixtures/snapshots/status_json/empty_vault.json

## Verification

All 27 tests pass:
```
tests/cli/ -- 27 passed in 32.79s
```

## CLI Requirements Satisfied

- CLI-01: All 7+ CLI commands (paths, status, sync, ocr, doctor, repair, context, setup) have contract tests covering exit codes and output shape
- CLI-02: Error commands produce stable, descriptive output without tracebacks; same error produces deterministic output
- CLI-03: pytest-snapshot tests with normalize_snapshot for dynamic fields (paths, timestamps, versions)

## Success Criteria

- [x] All 7+ CLI commands have contract tests covering exit codes and output shape
- [x] paths --json validated for {vault, worker_script, ld_deep_script} keys
- [x] status --json validated for required shape keys
- [x] context command validated for JSON contract keys
- [x] Text commands (sync, ocr, doctor, repair, setup) validated for stable text output
- [x] Error commands produce stable, descriptive output without tracebacks
- [x] Same error produces deterministic output (CLI-02)
- [x] pytest-snapshot tests with normalize_snapshot for dynamic fields (CLI-03)
- [x] Mock OCR backend in fixtures/ocr/mock_ocr_backend.py with 4 modes (CLI-01 mock integration)
- [x] pyproject.toml updated with new test dependencies and markers
- [x] All Python files syntax-check clean

## Commits

- `3489e5c`: feat(52-golden-datasets-cli-contracts): create golden dataset fixtures
