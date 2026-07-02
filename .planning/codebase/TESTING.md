# Testing Patterns

**Analysis Date:** 2026-07-02

## Test Framework

**Runner:**
- Python: pytest `>=7.4.0` from `pyproject.toml`.
- Plugin: Vitest `^2.1.0` from `paperforge/plugin/package.json`.
- Python pytest config lives in `pyproject.toml`.
- Plugin Vitest config lives in `paperforge/plugin/vitest.config.ts`.

**Assertion Library:**
- Python tests use plain `assert` with pytest fixtures and markers: `tests/unit/core/test_result.py`, `tests/cli/test_json_contracts.py`.
- Plugin tests use Vitest globals configured by `paperforge/plugin/vitest.config.ts`.
- Snapshot assertions use `pytest-snapshot` in CLI contract tests: `tests/cli/test_json_contracts.py`.

**Run Commands:**
```bash
python -m pytest              # Run configured Python testpaths from pyproject.toml
python -m pytest tests/unit   # Run unit tests
python -m pytest tests/cli    # Run CLI contract tests
python -m pytest -m "not slow" # Skip tests marked slow
coverage run -m pytest        # Collect Python coverage when coverage is installed
coverage report               # View Python coverage summary
cd paperforge/plugin && npm test       # Run plugin Vitest suite
cd paperforge/plugin && npm run test:watch # Watch plugin tests
```

## Test File Organization

**Location:**
- Python tests are split by verification layer under `tests/`: `tests/unit/`, `tests/cli/`, `tests/e2e/`, `tests/journey/`, `tests/chaos/`, `tests/audit/`, and `tests/integration/`.
- Legacy/top-level Python tests also exist directly under `tests/`, such as `tests/test_ocr_state_machine.py` and `tests/test_asset_index.py`.
- Plugin tests are isolated under `paperforge/plugin/tests/`.
- Shared fixture builders live in `tests/conftest.py`, `tests/cli/conftest.py`, `tests/e2e/conftest.py`, `tests/chaos/conftest.py`, and `fixtures/vault_builder.py`.

**Naming:**
- Python test files use `test_*.py`: `tests/unit/core/test_result.py`, `tests/cli/test_error_codes.py`, `tests/e2e/test_sync_pipeline.py`.
- Python test classes use `Test*` names grouped by behavior: `TestPFResultRoundTrip` in `tests/unit/core/test_result.py`, `TestStatusJson` in `tests/cli/test_json_contracts.py`.
- Python test functions use `test_*` names that state expected behavior: `test_unknown_error_code_graceful()` in `tests/unit/core/test_result.py`.
- Plugin test files use `*.test.mjs`: `paperforge/plugin/tests/annotation-bridge.test.mjs`, `paperforge/plugin/tests/runtime.test.mjs`.

**Structure:**
```text
tests/
├── conftest.py                    # Global repo path setup and shared vault fixture
├── unit/                          # Fast contract and pure-function tests
│   ├── core/test_result.py
│   ├── annotation/test_service_contracts.py
│   └── memory/test_vector_db.py
├── cli/                           # Subprocess CLI contract tests
│   ├── conftest.py
│   ├── test_json_contracts.py
│   └── test_annotation_json_contracts.py
├── e2e/                           # Temp vault end-to-end workflows
├── journey/                       # User workflow tests
├── chaos/                         # Failure-mode tests
├── audit/                         # Consistency audit tests
└── integration/                   # Multi-component tests

paperforge/plugin/tests/
└── *.test.mjs                     # Vitest coverage for extracted plugin helpers
```

## Test Structure

**Suite Organization:**
```python
from __future__ import annotations

import json

import pytest

from paperforge.core.result import PFResult


class TestPFResultRoundTrip:
    """PFResult serialization round-trip: to_dict -> from_dict."""

    def test_ok_with_data(self) -> None:
        original = PFResult(ok=True, command="sync", version="1.4.17rc3", data={"created": 5})
        reconstructed = PFResult.from_dict(original.to_dict())
        assert reconstructed == original
```

**Patterns:**
- Group related assertions in behavior-focused classes: `TestPathsJson`, `TestStatusJson`, `TestContextJson` in `tests/cli/test_json_contracts.py`.
- Keep contract tests explicit about required and optional keys: `ENVELOPE_KEYS`, `REQUIRED_KEYS`, and `OPTIONAL_KEYS` in `tests/cli/test_json_contracts.py`.
- Use helper functions for repeated seed data and subprocess setup: `_seed()` in `tests/unit/annotation/test_service_contracts.py`, `_run_ocr_with_bad_url()` in `tests/chaos/test_network_failures.py`.
- Assert semantic output, not just successful exit: `tests/cli/test_json_contracts.py` checks JSON shape, types, command names, and non-empty values.
- Failure-mode tests assert graceful behavior and no traceback: `tests/chaos/test_network_failures.py`.

## Mocking

**Framework:** pytest fixtures, pytest-mock, responses, monkeypatch-style patchable seams, and injected JavaScript dependencies.

**Patterns:**
```python
@pytest.fixture
def cli_invoker(vault_builder):
    def _invoke(args: list[str], vault_level: str = "minimal", env: dict | None = None):
        cmd = [sys.executable, "-m", "paperforge", "--vault", str(vault)] + args
        return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=60, env=base_env)
    yield _invoke
```

```python
@pytest.fixture
def mock_ocr_backend():
    import responses as _responses

    def _create_mock():
        rsps = _responses.RequestsMock(assert_all_requests_are_fired=False)
        rsps.add(_responses.POST, "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs", json=submit_data, status=202)
        return rsps

    yield _create_mock
```

```javascript
function resolvePythonExecutable(vaultPath, settings, _fs, _execFileSync) {
    const f = _fs || fs;
    const execSync = _execFileSync || require("node:child_process").execFileSync;
    // tests pass fake fs / exec dependencies
}
```

**What to Mock:**
- Mock external HTTP APIs with `responses` for in-process Python tests: `tests/cli/conftest.py` defines `mock_ocr_backend`.
- Mock subprocess dependencies through explicit injection in plugin helpers: `runSubprocessFn` in `paperforge/plugin/src/testable.js`.
- Patch CLI worker globals when testing dispatch without invoking full workers: `run_status = None` style patch points exist in `paperforge/cli.py`.
- Use temporary vaults and fixture files instead of real user vaults: `tests/conftest.py`, `fixtures/vault_builder.py`.
- Use controlled environment variables for subprocess failure tests: `PADDLEOCR_JOB_URL` in `tests/chaos/test_network_failures.py`.

**What NOT to Mock:**
- Do not mock JSON envelope shape for CLI contract tests; invoke `python -m paperforge` through `cli_invoker` in `tests/cli/conftest.py`.
- Do not use real Zotero or real user vault paths in automated tests; use temp vaults and fixtures.
- Do not mock SQLite when testing annotation query/import behavior; seed an actual SQLite connection as in `tests/unit/annotation/test_service_contracts.py`.
- Do not let network calls cross subprocess boundaries unintentionally; chaos tests control behavior with environment variables because `responses` cannot intercept subprocess HTTP.

## Fixtures and Factories

**Test Data:**
```python
@pytest.fixture
def test_vault() -> Generator[Path, None, None]:
    """Pytest fixture providing a fresh test vault."""
    vault = create_test_vault()
    yield vault
    if FIXTURE_VAULT.exists():
        shutil.rmtree(FIXTURE_VAULT)
```

```python
@pytest.fixture
def ann_with_data(ann_db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(ann_db_path))
    conn.row_factory = sqlite3.Row
    _seed(conn)
    yield conn
    conn.close()
```

**Location:**
- Global vault fixture setup: `tests/conftest.py`.
- CLI subprocess fixture setup: `tests/cli/conftest.py`.
- E2E and chaos fixtures: `tests/e2e/conftest.py`, `tests/chaos/conftest.py`.
- Reusable vault construction: `fixtures/vault_builder.py`.
- OCR JSON fixture data: `fixtures/ocr/`.
- CLI snapshot data: `tests/cli/snapshots/` and `fixtures/snapshots/`.

## Coverage

**Requirements:** No minimum coverage threshold is enforced in `pyproject.toml`.

**View Coverage:**
```bash
coverage run -m pytest
coverage report
coverage html
```

Coverage package `coverage>=7.4.0` is listed in `pyproject.toml`, but there is no `[tool.coverage]` section. Add coverage policy in `pyproject.toml` before treating coverage as a gate.

## Test Types

**Unit Tests:**
- Scope pure contracts, serialization, helpers, schema behavior, and focused DB queries.
- Place new pure Python tests under matching subsystem directories such as `tests/unit/core/`, `tests/unit/annotation/`, `tests/unit/memory/`, or `tests/unit/adapters/`.
- Use in-memory or temporary SQLite where persistence behavior matters: `tests/unit/annotation/test_service_contracts.py`.
- Plugin unit tests import `paperforge/plugin/src/testable.js` rather than `paperforge/plugin/main.js`.

**Integration Tests:**
- Use `tests/integration/` for multi-component workflows that are broader than unit tests but not full vault journeys.
- Existing example: `tests/integration/test_memory_workflow.py`.

**CLI Contract Tests:**
- Use `tests/cli/` for subprocess boundary tests of CLI arguments, JSON contracts, text output, and error codes.
- Always invoke CLI through `cli_invoker` from `tests/cli/conftest.py`.
- Assert exit code, stdout/stderr shape, JSON validity, and stable envelope keys.

**E2E Tests:**
- Use `tests/e2e/` for full temp-vault workflows such as sync, status/doctor/repair, OCR, and multi-domain sync.
- Pytest config includes `tests/e2e` in `testpaths` in `pyproject.toml`.

**Journey Tests:**
- Use `tests/journey/` for user-facing workflow coverage: `tests/journey/test_onboarding.py`, `tests/journey/test_daily_workflow.py`.

**Chaos Tests:**
- Use `tests/chaos/` for destructive or abnormal scenarios.
- Mark chaos tests with `pytestmark = pytest.mark.chaos`.
- Include isolation guards before destructive setup: `assert any(x in str(chaos_vault_standard).lower() for x in ("tmp", "temp"))` in `tests/chaos/test_network_failures.py`.

**Audit Tests:**
- Use `tests/audit/` for consistency checks between mock and real pipeline behavior: `tests/audit/test_consistency.py`.

## Common Patterns

**Async Testing:**
```javascript
import { describe, expect, it } from 'vitest';
const helpers = require('../src/testable.js');

it('loads annotations through injected subprocess result', async () => {
  const result = await helpers.loadAnnotationsForPaper({
    paperKey: 'PAPER_A',
    runSubprocessFn: async () => ({ stdout: '{"ok":true,"data":{"db_available":true}}', stderr: '', exitCode: 0 }),
  });
  expect(result.state).toBeDefined();
});
```

Use injected async functions for plugin subprocess workflows instead of spawning real Python from Vitest unless explicitly testing runtime integration.

**Error Testing:**
```python
def test_from_dict_unknown_error_code_graceful() -> None:
    data = {
        "ok": False,
        "command": "sync",
        "version": "2.1.0",
        "error": {"code": "SOME_FUTURE_ERROR_CODE", "message": "Something new happened", "details": {}},
    }
    result = PFResult.from_dict(data)
    assert result.error is not None
    assert result.error.code is ErrorCode.UNKNOWN
```

Use explicit assertions for recoverability and absence of crashes:
```python
combined = (stdout + stderr).lower()
assert "Traceback" not in stderr
assert rc != 0 or "network" in combined or "error" in combined
```

**Snapshot Testing:**
- Use snapshots for regression detection after semantic assertions pass: `test_status_json_snapshot_regression()` in `tests/cli/test_json_contracts.py`.
- Normalize volatile paths or vault-specific values before snapshot comparison with helpers from `tests/cli/test_contract_helpers.py`.

**Database Testing:**
- Use SQLite row factories for named column access: `conn.row_factory = sqlite3.Row` in `tests/unit/annotation/test_service_contracts.py`.
- Keep seed rows local to the test module via `_seed()` and constants such as `_ANNOTATION_COLS`.
- Assert ordering and filter semantics directly in SQL-focused tests.

---

*Testing analysis: 2026-07-02*
