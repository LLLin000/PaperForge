# Architecture: 6-Layer Testing Infrastructure

**Project:** PaperForge v2.0
**Researched:** 2026-05-08
**Mode:** Architecture (project research)
**Confidence:** HIGH

---

## 1. Architecture Overview

### 1.1 The 6 Testing Layers

The testing architecture follows a **modified testing diamond** shape: unit tests form the broad base, integration/contract tests form the bulk (where most value is found), and full-system/E2E tests cap the top. An additional "Level 0" version-check layer runs **before** all other layers as a fast health gate.

```
+---------------------------+
| Level 6: Chaos/Destructive|  Rare, manual or scheduled
+---------------------------+
| Level 5: User Journey     |  Contract-driven, run per-release
+---------------------------+
| Level 4: Temp Vault E2E   |  Full pipeline, mock-backed
+---------------------------+
| Level 3: Plugin Runtime   |  Vitest + obsidian-test-mocks
+---------------------------+
| Level 2: CLI Contracts    |  JSON schema stability
+---------------------------+
| Level 1: Python Units     |  Fast, isolated, 1-10ms each
+---------------------------+
| Level 0: Version Sync     |  <100ms pre-flight gate
+---------------------------+
```

**Layer dependency chain (build order):**

```
Level 0 (version check)
    |
    v
Level 1 (unit tests) ----+
    |                     |
    v                     v
Level 2 (CLI contracts)  Level 3 (plugin unit)
    |                     |
    +----------+----------+
               |
               v
         Level 4 (temp vault E2E)
               |
               v
         Level 5 (user journey)
               |
               v
         Level 6 (chaos)
```

### 1.2 Integration Points with Existing Codebase

| Component | Integration | New vs Modified |
|-----------|-------------|-----------------|
| `tests/conftest.py` | Add shared fixtures for mock vault, mock OCR, golden dataset paths. Existing `create_test_vault()` moved to `fixtures/vault_builder.py` | **Modified** — extend, not rewrite |
| `tests/test_*.py` (flat) | Migrated into `tests/unit/` with no behavior change | **Modified** — relocate only |
| `tests/sandbox/` | Retained as-is for backward compat; new golden datasets go to `fixtures/` | **Unchanged** |
| `tests/fixtures/` (existing .json, .pdf) | Expanded into full `fixtures/` hierarchy | **Modified** — add structure |
| `pyproject.toml` `[tool.pytest.ini_options]` | Add markers, ignore patterns for new layers | **Modified** |
| `paperforge/plugin/*` | New `tests/plugin/` tests import via vitest/Jest; no changes to plugin source | **New** |
| `.github/` (new) | New CI workflows for matrix builds | **New** |
| `scripts/` | New `scripts/check_version_sync.py`, `scripts/run_chaos.sh` | **New** |
| `paperforge/cli.py` | CLI contract tests test `main()` return codes and JSON output | **No changes needed** |
| `paperforge/worker/ocr.py` | Mock OCR backend intercepts HTTP calls at `requests` layer | **Test-only, no source changes** |
| `paperforge/commands/` | Unit tests import command modules directly | **No changes needed** |
| `tests/sandbox/00_TestVault/` | Still gitignored; temp vault E2E creates fresh dirs in system temp | **Unchanged** |

---

## 2. Directory Structure

### 2.1 Complete Directory Tree

```
<repo_root>/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Main CI: all gates except chaos
│       ├── ci-chaos.yml              # Chaos tests (scheduled or manual)
│       └── ci-pr-checks.yml          # Fast pre-flight (L0+L1)
│
├── tests/
│   ├── __init__.py                   # (empty) marks as package
│   ├── conftest.py                   # Root fixtures: mock vault, golden paths, pytest plugins
│   │
│   ├── unit/                         # LEVEL 1: Python unit tests
│   │   ├── __init__.py
│   │   ├── conftest.py               # Overrides/extends root conftest for unit scope
│   │   ├── test_config.py            # Existing, relocated
│   │   ├── test_bbt_parser.py        # New
│   │   ├── test_pdf_resolver.py      # Existing, relocated
│   │   ├── test_ocr_state_machine.py # Existing, relocated
│   │   ├── test_asset_index.py       # Existing, relocated
│   │   ├── test_asset_state.py       # Existing, relocated
│   │   ├── test_discussion.py        # Existing, relocated
│   │   ├── test_repair.py            # Existing, relocated
│   │   ├── test_utils_slugify.py     # Existing, relocated
│   │   ├── test_utils_yaml.py        # Existing, relocated
│   │   ├── test_utils_json.py        # Existing, relocated
│   │   ├── test_utils_journal.py     # Existing, relocated
│   │   ├── test_path_normalization.py# Existing, relocated
│   │   ├── test_setup_wizard.py      # Existing, relocated
│   │   ├── test_doctor.py            # Existing, relocated
│   │   ├── test_ocr_preflight.py     # Existing, relocated
│   │   ├── test_ocr_doctor.py        # Existing, relocated
│   │   ├── test_ocr_classify.py      # Existing, relocated
│   │   ├── test_ocr_rendering.py     # Existing, relocated
│   │   ├── test_ld_deep_config.py    # Existing, relocated
│   │   ├── test_ld_deep_skel.py      # Existing, relocated
│   │   ├── test_ld_deep_postprocess.py # Existing, relocated
│   │   ├── test_prepare_rollback.py  # Existing, relocated
│   │   ├── test_base_views.py        # Existing, relocated
│   │   ├── test_base_preservation.py # Existing, relocated
│   │   ├── test_context.py           # Existing, relocated
│   │   ├── test_legacy_worker_compat.py # Existing, relocated
│   │   └── test_migration.py         # Existing, relocated
│   │
│   ├── cli/                          # LEVEL 2: CLI contract tests
│   │   ├── __init__.py
│   │   ├── conftest.py               # CLI-specific fixtures (subprocess runner)
│   │   ├── test_paths_json.py        # Existing test_cli_paths.py
│   │   ├── test_sync_cli.py          # CLI sync --dry-run contract
│   │   ├── test_status_json.py       # --json output schema
│   │   ├── test_doctor_cli.py        # CLI doctor verdict contract
│   │   ├── test_deep_reading_cli.py  # CLI deep-reading output
│   │   ├── test_ocr_cli.py           # CLI ocr --diagnose contract
│   │   ├── test_repair_cli.py        # CLI repair dry-run contract
│   │   └── test_error_codes.py       # Exit code contract
│   │
│   ├── plugin/                       # LEVEL 3: Plugin runtime tests
│   │   ├── __init__.py
│   │   ├── conftest.py               # Vitest config, obsidian mocks setup
│   │   ├── vitest.config.ts          # Vitest configuration
│   │   ├── test_main.js              # Plugin instantiation
│   │   ├── test_settings.js          # Settings tab rendering
│   │   ├── test_dashboard.js         # Dashboard view logic
│   │   ├── test_subprocess.js        # CLI subprocess dispatch
│   │   ├── test_i18n.js              # i18n key coverage
│   │   ├── test_base_rendering.js    # Base view rendering
│   │   └── fixtures/                 # Plugin test fixtures
│   │       ├── mock_vault_config.json
│   │       └── mock_index.json
│   │
│   ├── e2e/                          # LEVEL 4: Temp vault E2E tests
│   │   ├── __init__.py
│   │   ├── conftest.py               # Temp vault lifecycle
│   │   ├── test_full_sync_ocr_pipeline.py  # sync -> ocr -> status
│   │   ├── test_repair_workflow.py         # Create state divergence, run repair
│   │   ├── test_setup_headless.py          # Headless setup on temp vault
│   │   ├── test_migration_from_v1.py       # Legacy config migration
│   │   ├── test_doctor_e2e.py              # doctor on fully configured vault
│   │   └── test_multi_domain.py            # Multi-domain BBT export sync
│   │
│   ├── journey/                      # LEVEL 5: User journey tests
│   │   ├── __init__.py
│   │   ├── conftest.py               # Journey-level fixtures
│   │   ├── UX_CONTRACT.md            # The UX contract document
│   │   ├── test_new_user_onboarding.py     # First-time user flow
│   │   ├── test_daily_workflow.py          # Regular user sync + OCR + read
│   │   ├── test_upgrade_migration.py       # Existing user upgrading
│   │   └── test_error_recovery.py          # User handles failed OCR, broken paths
│   │
│   ├── chaos/                        # LEVEL 6: Destructive tests
│   │   ├── __init__.py
│   │   ├── conftest.py               # Chaos-specific fixtures
│   │   ├── scenarios/
│   │   │   ├── test_corrupt_json_exports.py      # Malformed BBT JSON
│   │   │   ├── test_missing_pdf_files.py         # PDF referenced but missing
│   │   │   ├── test_ocr_api_timeout.py           # PaddleOCR API hangs
│   │   │   ├── test_zotero_junction_broken.py    # Symlink broken
│   │   │   ├── test_disk_full_simulation.py      # No space for OCR output
│   │   │   ├── test_concurrent_sync_calls.py     # Two syncs at once
│   │   │   ├── test_interrupted_ocr.py           # Kill mid-OCR, resume
│   │   │   └── test_nonexistent_vault_path.py    # Cwd is not a vault
│   │   └── CHAOS_MATRIX.md          # Documentation of chaos scenarios
│   │
│   └── sandbox/                      # Existing — NOT relocated
│       ├── exports/
│       ├── ocr-complete/
│       ├── TestZoteroData/
│       ├── generate_sandbox.py
│       ├── generate_ocr_fixture.py
│       ├── batch_check.py
│       ├── deep_inspect.py
│       └── precise_batch.py
│
├── fixtures/                         # Golden datasets (shared across layers)
│   ├── __init__.py
│   ├── README.md                     # Fixture documentation
│   │
│   ├── zotero/                       # Simulated Better BibTeX JSON exports
│   │   ├── orthopedic.json           # Domain: 骨科
│   │   ├── sports_medicine.json      # Domain: 运动医学
│   │   ├── multi_attachment.json     # Paper with 3 PDF attachments
│   │   ├── no_pdf.json               # Paper without PDF
│   │   ├── absolute_paths.json       # Windows absolute path format
│   │   ├── storage_prefix.json       # storage: prefix format
│   │   ├── bare_relative.json        # Bare KEY/file.pdf format
│   │   └── empty.json                # Empty export (edge case)
│   │
│   ├── pdf/                          # Minimal valid PDFs
│   │   ├── blank.pdf                 # 1-page blank PDF
│   │   ├── two_page.pdf              # 2-page PDF (for multi-page OCR tests)
│   │   ├── with_figures.pdf          # PDF containing embedded images
│   │   └── large.pdf                 # >10MB PDF (for timeout tests)
│   │
│   ├── snapshots/                    # Expected outputs for snapshot testing
│   │   ├── status_json/
│   │   │   └── minimal_vault.json    # Expected status --json output
│   │   ├── paths_json/
│   │   │   └── default_config.json   # Expected paths --json output
│   │   ├── formal_note_frontmatter/
│   │   │   └── orthopedic_article.yaml  # Expected YAML frontmatter
│   │   └── index_json/
│   │       └── after_sync.json       # Expected index structure
│   │
│   └── ocr/                          # Mock OCR response fixtures
│       ├── paddleocr_success.json    # Standard PaddleOCR API success response
│       ├── paddleocr_pending.json    # Async job created, not yet done
│       ├── paddleocr_failed.json     # API returned error
│       ├── paddleocr_timeout.json    # Job never completes
│       ├── extracted_fulltext.md     # Expected OCR output (fulltext.md)
│       └── figure_map.json           # Expected figure-map.json output
│
├── scripts/
│   ├── check_version_sync.py         # LEVEL 0: version consistency checker
│   ├── run_all_tests.sh              # Shell wrapper: L0 -> L1 -> L2 -> L3 -> L4
│   ├── run_chaos_tests.sh            # Shell wrapper for chaos layer
│   └── generate_fixtures.py          # Regenerate golden datasets
│
└── VERSION_SYNC.md                   # Documentation of version sync protocol
```

### 2.2 Migration Path for Existing Tests

Existing flat `tests/test_*.py` files are **relocated** (not rewritten) into `tests/unit/`. This is a pure directory move:

| Existing Path | New Path |
|---------------|----------|
| `tests/test_config.py` | `tests/unit/test_config.py` |
| `tests/test_ocr_state_machine.py` | `tests/unit/test_ocr_state_machine.py` |
| `tests/test_asset_index.py` | `tests/unit/test_asset_index.py` |
| `tests/test_e2e_pipeline.py` | `tests/e2e/test_full_sync_ocr_pipeline.py` (renamed) |
| `tests/test_e2e_cli.py` | `tests/cli/test_sync_cli.py` (split across cli/) |
| `tests/test_smoke.py` | `tests/unit/test_smoke.py` (retained as-is) |
| `tests/test_plugin_install_bootstrap.py` | `tests/plugin/test_main.js` (rewritten as JS) |
| `tests/conftest.py` | Keep in root, add imports from `fixtures/` |

**Existing `tests/sandbox/` directory is RETAINED in place** — it is used for manual debugging and backward compat but is NOT part of the automated pipeline. New golden datasets go to `fixtures/`.

---

## 3. Mock System Architecture

### 3.1 Mock Systems Overview

```
                    +--------------+
                    |  Test Runner |
                    +------+-------+
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
+---------+---+  +--------+-------+  +------+-------+
| Mock OCR    |  | Mock Zotero   |  | Mock Vault   |
| Backend     |  | Data Source   |  | Filesystem   |
+-------------+  +---------------+  +--------------+
| Intercepts   |  | Static JSON   |  | tmp_path     |
| requests to  |  | fixtures from |  | + created    |
| PaddleOCR    |  | fixtures/     |  | dirs & files |
| API at HTTP  |  | zotero/       |  | + paperforge.|
| layer        |  |               |  |   json       |
+--------------+  +---------------+  +--------------+
```

### 3.2 Mock OCR Backend

**Purpose:** Intercept HTTP calls to the PaddleOCR API so tests never touch the real network.

**Approach:** `responses` library (or `pytest-httpx`) for Python-level HTTP interception + fixture JSON responses.

```
tests/
├── conftest.py  (root)         -- registers mock_ocr_backend fixture
├── unit/
│   └── conftest.py             -- imports mock_ocr_backend, applies auto-use
└── fixtures/
    └── ocr/                    -- PaddleOCR API response fixtures
        ├── paddleocr_success.json
        ├── paddleocr_pending.json
        └── paddleocr_failed.json
```

**Architecture:**

```python
# tests/conftest.py (conceptual)

@pytest.fixture
def mock_ocr_backend():
    """Intercept HTTP calls to PaddleOCR API and return fixture responses."""
    import responses
    with responses.RequestsMock() as rsps:
        # Job submission endpoint
        rsps.post(
            "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
            json={"job_id": "mock-job-001", "status": "queued"},
            status=202,
        )
        # Job status polling endpoint
        rsps.get(
            re.compile(r"https://paddleocr\.aistudio-app\.com/api/v2/ocr/jobs/mock-job-\d+"),
            json={"status": "completed", "result_url": "https://mock/results"},
            status=200,
        )
        # Result download
        rsps.get(
            "https://mock/results",
            json=MOCK_OCR_RESULT,  # Loaded from fixtures/ocr/paddleocr_success.json
            status=200,
        )
        yield rsps


@pytest.fixture
def mock_ocr_backend_timeout():
    """OCR API that always returns 'pending' (simulates timeout)."""
    # ... similar pattern returning 202 forever
```

**Fixture data flow:**

```
fixtures/ocr/paddleocr_success.json
    --> mock_ocr_backend fixture
        --> ocr.py's requests.post() / requests.get()
            --> run_ocr() processes result
                --> test asserts OCR output files exist
```

**Layer applicability:**

| Layer | Uses Mock OCR? | How |
|-------|----------------|-----|
| L1 Unit | YES | Via `mock_ocr_backend` fixture auto-use in `tests/unit/conftest.py` |
| L2 CLI | YES | Via `mock_ocr_backend` in CLI conftest |
| L3 Plugin | N/A | Plugin doesn't call OCR directly |
| L4 E2E | **NO** | Uses real file-based OCR fixture (`tests/sandbox/ocr-complete/`) |
| L5 Journey | **NO** | Full-system test with real (or realistically simulated) OCR |
| L6 Chaos | YES | `mock_ocr_backend_timeout` + corrupt responses |

### 3.3 Mock Zotero Data Source

**Purpose:** Provide deterministic BBT JSON exports without requiring a real Zotero installation.

**Approach:** Static JSON files in `fixtures/zotero/` that mirror the three supported BBT path formats.

```
fixtures/zotero/
├── orthopedic.json           # Single-domain, single paper
├── sports_medicine.json      # Second domain
├── multi_attachment.json     # 1 main PDF + 2 supplementary
├── no_pdf.json               # Entry without attachments
├── absolute_paths.json       # Windows D:\Zotero\storage\KEY\file.pdf
├── storage_prefix.json       # storage:KEY/file.pdf
├── bare_relative.json        # KEY/file.pdf
└── empty.json                # [] — edge case
```

**Fixture reader:**

```python
# tests/conftest.py (conceptual)

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

@pytest.fixture
def zotero_export(request: pytest.FixtureRequest) -> list[dict]:
    """Load a named BBT JSON fixture."""
    fixture_name = getattr(request, "param", "orthopedic.json")
    path = FIXTURES_DIR / "zotero" / fixture_name
    return json.loads(path.read_text(encoding="utf-8"))
```

### 3.4 Mock Vault Filesystem

**Purpose:** Create a deterministic, isolated vault filesystem for each test layer.

**Three implementations, one interface:**

| Layer | Implementation | Speed | Realism |
|-------|---------------|-------|---------|
| L1 Unit | `tmp_path` + minimal dirs | Fastest | Low |
| L2 CLI | `tmp_path` + full vault with `paperforge.json` | Fast | Medium |
| L4 E2E | `tmp_path` + full vault + mock Zotero storage + OCR fixtures | Medium | High |
| L6 Chaos | `tmp_path` + deliberately broken vault | Fast | Low (by design) |

**Unified interface via `conftest.py`:**

```python
# tests/conftest.py (conceptual)

@pytest.fixture
def vault_builder():
    """Factory fixture: returns a function that builds vaults at different completeness levels."""
    from fixtures.vault_builder import VaultBuilder
    return VaultBuilder(fixtures_root=FIXTURES_DIR)

# Usage in tests:
# vault_builder("minimal")    -> tmp_path + paperforge.json only
# vault_builder("standard")   -> tmp_path + full dirs + blank.pdf
# vault_builder("full")       -> tmp_path + full dirs + exports + OCR fixtures + mock PDFs
```

---

## 4. Layer-by-Layer Architecture

### 4.1 Level 0: Version Build Consistency

**Purpose:** Ensure all version declarations agree before any tests run.

**Location:** `scripts/check_version_sync.py`

**What it checks:**

| File | Field | Check |
|------|-------|-------|
| `paperforge/__init__.py` | `__version__` | Authoritative source |
| `paperforge/plugin/manifest.json` | `version` | Must match `__version__` |
| `paperforge/plugin/versions.json` | All versions | Each must match `__version__` |
| `pyproject.toml` (dynamic) | `version` attr | Must point to `paperforge.__version__` |
| `paperforge.json` (DEFAULT_CONFIG) | `version` | Must match (if present) |
| `VERSION_SYNC.md` | Documented version | Must match (consistency audit) |
| `CHANGELOG.md` | Latest release | Must correspond to current version |

**Exit codes:** 0 = all sync, 1 = mismatch found.

**Execution:** Called first in CI `ci-pr-checks.yml` before any other test job.

```
ci-pr-checks.yml:
  check-version-sync:
    runs-on: ubuntu-latest
    steps:
      - python scripts/check_version_sync.py
```

**Integration:** This is the ONLY layer that can fail independently without running others. If it fails, all subsequent test jobs are skipped.

### 4.2 Level 1: Python Unit Tests

**Purpose:** Fast, isolated tests for individual functions/modules.

**Location:** `tests/unit/`

**Characteristics:**
- No external dependencies (network, filesystem beyond `tmp_path`)
- No subprocess calls
- Mock everything outside the module under test
- Target: 1-10ms per test, <30s for the full suite
- Coverage target: >85% for `paperforge/*.py`, >75% for `paperforge/worker/*.py`

**Fixture layering:**

```
tests/conftest.py (root)
  |-- vault_builder factory fixture
  |-- zotero_export fixture
  |-- mock_ocr_backend fixture
  |
  tests/unit/conftest.py
    |-- auto-use: mock_ocr_backend (for OCR unit tests)
    |-- auto-use: set PAPERFORGE_POLL_INTERVAL=0
```

**Test patterns per module:**

| Module | Test File | Pattern |
|--------|-----------|---------|
| `paperforge/config.py` | `test_config.py` | Pure function inputs/outputs, env var overrides |
| `paperforge/pdf_resolver.py` | `test_pdf_resolver.py` | Path resolution with fixture paths |
| `paperforge/worker/ocr.py` | `test_ocr_state_machine.py` | Mock HTTP, assert state transitions |
| `paperforge/worker/_utils.py` | `test_utils_*.py` | Pure function tests |
| `paperforge/worker/sync.py` | Migrated from `test_e2e_pipeline.py` | Mock file I/O |
| `paperforge/worker/repair.py` | `test_repair.py` | Create divergence scenarios, test detection |
| `paperforge/worker/asset_index.py` | `test_asset_index.py` | Build index from known data, assert structure |
| `paperforge/setup_wizard.py` | `test_setup_wizard.py` | Test headless flow with tmp_path vault |

### 4.3 Level 2: CLI Contract Tests

**Purpose:** Validate CLI command output schemas, exit codes, and JSON output stability.

**Location:** `tests/cli/`

**Characteristics:**
- Run `paperforge <command>` via subprocess (`sys.executable -m paperforge`)
- Assert exit codes, stdout JSON schemas, stderr patterns
- No external network (CLI commands that hit network are mocked at Python level)
- Not a full E2E test — tests the **CLI boundary only**

**Pattern:**

```python
# tests/cli/conftest.py (conceptual)

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def cli_invoker(vault_builder):
    """Returns a function that runs paperforge CLI in a temp vault."""
    vault = vault_builder("minimal")

    def _invoke(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "paperforge", "--vault", str(vault)] + args,
            capture_output=True,
            text=True,
            timeout=30,
        )

    return _invoke
```

**Contract tests for each command:**

| Command | Contract Check |
|---------|---------------|
| `paths --json` | Output is valid JSON with exactly `{vault, worker_script, ld_deep_script}` keys |
| `status --json` | Output is valid JSON with `{total_papers, version, ...}` |
| `sync --dry-run` | Exit 0, prints summary without modifying filesystem |
| `doctor` | Output contains `[OK]`, `[WARN]`, or `[FAIL]` verdict prefix |
| `deep-reading` | Tabular output or valid JSON |
| `ocr --diagnose` | Diagnoses without crashing, exit 0 or 1 |
| `repair` (no args) | Dry-run output, exit 0 |
| `repair --fix` | Actual repair on mock divergence |
| Unrecognized command | Exit 1, prints error to stderr |
| Missing vault | Exit 1, does not crash with traceback |

**Snapshot testing with `pytest-snapshot`:**

```python
# Conceptual snapshot usage
def test_paths_json_matches_snapshot(cli_invoker, snapshot):
    result = cli_invoker(["paths", "--json"])
    assert result.returncode == 0
    snapshot.assert_match(result.stdout, "paths_default_config.json")
```

Snapshots stored at `fixtures/snapshots/paths_json/default_config.json`.

### 4.4 Level 3: Plugin Runtime Tests

**Purpose:** Test the Obsidian plugin JS code (`paperforge/plugin/main.js`) without a running Obsidian instance.

**Location:** `tests/plugin/`

**Technology stack:**
- **Vitest** (preferred over Jest for ESM compatibility and speed)
- **`obsidian-test-mocks`** package for Obsidian API mocks
- **`jsdom`** environment for DOM APIs

**Directory layout:**

```
tests/plugin/
├── vitest.config.ts              # Vitest configuration
├── conftest.py                   # (unused — Vitest loads TS/JS config)
├── __mocks__/
│   └── obsidian.ts               # Manual mock if needed (obsidian-test-mocks preferred)
├── test_main.js                  # Plugin lifecycle, onload(), onunload()
├── test_settings.js              # Settings tab rendering and persistence
├── test_dashboard.js             # Dashboard view component tests
├── test_subprocess.js            # CLI subprocess dispatch from plugin
├── test_i18n.js                  # i18n key coverage (all keys in zh and en)
├── test_base_rendering.js        # Base view rendering
└── fixtures/
    ├── mock_vault_config.json    # Simulated paperforge.json
    └── mock_index.json           # Simulated canonical index
```

**Key test patterns:**

```javascript
// test_main.js (conceptual)
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { App } from 'obsidian-test-mocks/obsidian';
import { MyPlugin } from '../../paperforge/plugin/main.js';

describe('Plugin lifecycle', () => {
  let app;
  let plugin;

  beforeEach(() => {
    app = new App();
    plugin = new MyPlugin(app, { id: 'paperforge' });
  });

  it('should load without error', async () => {
    await expect(plugin.onload()).resolves.not.toThrow();
  });

  it('should register views', async () => {
    await plugin.onload();
    expect(app.views.get('paperforge-status')).toBeDefined();
  });
});
```

**What is NOT tested at this layer:**
- Actual subprocess execution of the Python CLI (that's L2)
- Actual Obsidian rendering (that's L4/L5)
- File watchers and real-time updates

**Why Vitest over Jest:**

| Factor | Vitest | Jest |
|--------|--------|------|
| ESM support | Native | Requires transforms |
| Speed | ~2x faster on watch mode | Slower |
| `obsidian-test-mocks` support | First-class | Compatible via config |
| TypeScript | Native | Via ts-jest |
| File parallelism control | Simple config | More complex |

### 4.5 Level 4: Temp Vault E2E Tests

**Purpose:** Test the full Python pipeline (sync -> OCR -> status -> repair) in a freshly created temporary vault.

**Location:** `tests/e2e/`

**Characteristics:**
- Creates a complete vault in OS temp directory (via `tmp_path`)
- Copies golden datasets into the vault
- Calls Python worker functions directly (not via subprocess)
- Workflow: sync -> verify index -> verify formal notes -> (mock) OCR -> verify OCR results -> verify status
- No network access (mock OCR intercept, static Zotero exports from fixtures)

**Fixture architecture:**

```python
# tests/e2e/conftest.py (conceptual)

import shutil
from pathlib import Path

import pytest

from paperforge.config import paperforge_paths

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


@pytest.fixture
def e2e_vault(tmp_path: Path) -> Path:
    """Create a fully-populated temp vault for E2E tests."""
    vault = tmp_path / "test_vault"
    vault.mkdir()

    # 1. Create paperforge.json
    # 2. Create directory structure (System, PaperForge, Resources, Literature, etc.)
    # 3. Copy Zotero export fixtures into PaperForge/exports/
    # 4. Copy mock PDFs into Zotero/storage/
    # 5. Copy OCR fixture into PaperForge/ocr/
    # 6. Create .env with mock PADDLEOCR_API_TOKEN
    # 7. Return vault path
    ...

    return vault


@pytest.fixture
def run_sync(e2e_vault: Path):
    """Run full sync pipeline and return paths dict."""
    from paperforge.worker.sync import run_selection_sync, run_index_refresh
    run_selection_sync(e2e_vault)
    run_index_refresh(e2e_vault)
    return paperforge_paths(e2e_vault)
```

**Workflow test example:**

```python
# tests/e2e/test_full_sync_ocr_pipeline.py (conceptual)

class TestFullPipeline:
    """sync -> index -> formal notes -> OCR -> status."""

    def test_sync_creates_workspace_notes(self, run_sync, e2e_vault):
        """After sync, workspace notes exist in Literature/<domain>/."""
        paths = run_sync
        lit_dir = paths["literature"]
        ws_notes = list(lit_dir.rglob("*.md"))
        assert len(ws_notes) > 0
        assert all("zotero_key:" in n.read_text() for n in ws_notes)

    def test_ocr_completes_on_do_ocr_true(self, e2e_vault, mock_ocr_backend):
        """Papers with do_ocr: true get OCR results."""
        # 1. Run sync
        # 2. Set do_ocr=true in formal note frontmatter
        # 3. Run OCR
        # 4. Assert meta.json exists with ocr_status: done

    def test_status_reports_correct_counts(self, e2e_vault, run_sync):
        """status output matches actual vault contents."""
        from paperforge.worker.status import run_status
        result = run_status(e2e_vault)
        assert result["total_papers"] >= 1
```

### 4.6 Level 5: User Journey Tests

**Purpose:** Validate complete user-facing workflows against a documented UX contract.

**Location:** `tests/journey/`

**UX Contract:** `tests/journey/UX_CONTRACT.md` documents the complete set of user journeys the product supports. Each journey maps to one test file.

**Journeys covered:**

| Journey | Test File | Description |
|---------|-----------|-------------|
| New user onboard | `test_new_user_onboarding.py` | Install -> setup wizard -> sync -> OCR -> deep read |
| Daily workflow | `test_daily_workflow.py` | Open Obsidian -> open dashboard -> sync -> check status -> close |
| Upgrade migration | `test_upgrade_migration.py` | User upgrades from v1.x -> migration runs -> everything works |
| Error recovery | `test_error_recovery.py` | User sees error -> runs doctor -> runs repair -> back to normal |

**Architecture:**

```python
# tests/journey/conftest.py (conceptual)

@pytest.fixture
def full_vault(tmp_path_factory) -> Path:
    """Session-scoped vault used for ALL journey tests (expensive setup, share it)."""
    vault = tmp_path_factory.mktemp("journey_vault")
    # Full setup: create vault, install paperforge.json, copy golden datasets,
    # run headless setup, run sync, run OCR, create deep-reading artifacts
    ...
    return vault
```

Note: Journey tests use `tmp_path_factory` (session scope) rather than `tmp_path` (function scope) because the setup is expensive. Tests within a journey file must NOT mutate shared state; each test creates its own paper copy within the vault.

### 4.7 Level 6: Chaos / Destructive Tests

**Purpose:** Ensure the system handles abnormal, malicious, or catastrophic inputs gracefully.

**Location:** `tests/chaos/scenarios/`

**CHAOS_MATRIX.md:** Documents all chaos scenarios, their trigger conditions, expected behavior, and recovery paths.

**Scenario categories:**

| Category | Scenario | Trigger | Expected Behavior |
|----------|----------|---------|-------------------|
| Corrupt input | `test_corrupt_json_exports.py` | Malformed JSON in exports/ | Graceful error, no crash, actionable error message |
| Missing resources | `test_missing_pdf_files.py` | PDF path in formal note but file missing | pdf_path wikilink is broken, status reports error, repair detects it |
| API failures | `test_ocr_api_timeout.py` | PaddleOCR never returns completion | OCR worker retries, eventually fails with clear message |
| Filesystem errors | `test_zotero_junction_broken.py` | Zotero junction/symlink broken | doctor detects, repair offers fix |
| Resource exhaustion | `test_disk_full_simulation.py` | No space for OCR output | OCR worker fails gracefully, existing data intact |
| Concurrency | `test_concurrent_sync_calls.py` | Two sync processes at same time | FileLock prevents corruption, second process waits or errors |
| Interruption | `test_interrupted_ocr.py` | Kill OCR mid-job, restart | OCR resumes from last known state, no duplicate work |
| Invalid config | `test_nonexistent_vault_path.py` | --vault points to nothing | Exit 1, clear "path not found" message |

**Chaos fixtures pattern:**

```python
# tests/chaos/conftest.py (conceptual)

@pytest.fixture
def corrupted_export(tmp_path) -> Path:
    """A directory with a corrupted BBT export."""
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir(parents=True)
    (exports_dir / "orthopedic.json").write_text(
        "this is not valid json {{{", encoding="utf-8"
    )
    return exports_dir


@pytest.fixture
def vault_with_broken_junction(tmp_path) -> Path:
    """A vault where the Zotero junction target doesn't exist."""
    vault = _create_base_vault(tmp_path)
    # Create the junction path but point it to nowhere
    zotero_link = vault / "99_System" / "Zotero"
    zotero_link.mkdir(parents=True, exist_ok=True)
    # Simulate broken junction by having an empty dir instead of link
    return vault
```

---

## 5. CI Matrix Architecture

### 5.1 Workflow File Structure

```
.github/workflows/
├── ci-pr-checks.yml       # Fast pre-flight: L0 + L1 (every push)
├── ci.yml                 # Full gate: L0-L5 (PR merge & main push)
└── ci-chaos.yml           # Chaos: L6 (weekly schedule & manual)
```

### 5.2 ci-pr-checks.yml — Fast Pre-Flight

**Purpose:** Run in <2 minutes. Blocks PR if version sync or unit tests fail.

```yaml
name: PR Pre-flight

on:
  pull_request:
    paths-ignore:
      - 'docs/**'
      - '**.md'
      - '.planning/**'

jobs:
  check-version-sync:
    name: Check version sync (L0)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python scripts/check_version_sync.py

  unit-tests:
    name: Unit tests (L1) - py${{ matrix.python }} on ${{ matrix.os }}
    needs: [check-version-sync]
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python: ["3.10", "3.11", "3.12"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - name: Install deps
        run: |
          pip install -e ".[test]"
      - name: Run unit tests
        run: |
          pytest tests/unit/ -q --tb=short -x
```

**Matrix: 3 OS × 3 Python = 9 jobs (each <2 min)**

### 5.3 ci.yml — Full Gate

**Purpose:** Run all gates (L0-L5) on merge to main. Plasma matrix where L1 runs everywhere, L2-L5 run on selective configurations.

```yaml
name: CI Full Gate

on:
  push:
    branches: [master, main]
  pull_request:
    # Also on PR, but with matrix

jobs:
  # ── L0 ──
  check-version-sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python scripts/check_version_sync.py

  # ── L1: Full matrix ──
  unit-tests:
    needs: [check-version-sync]
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python: ["3.10", "3.11", "3.12"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - run: pip install -e ".[test]"
      - run: pytest tests/unit/ -q --tb=short --timeout=60
      - run: ruff check paperforge/ tests/

  # ── L2: Singular config ──
  cli-contract-tests:
    needs: [unit-tests]
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python: ["3.10", "3.12"]     # Cover oldest + newest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - run: pip install -e ".[test]"
      - run: pytest tests/cli/ -q --tb=short

  # ── L3: Plugin tests (Node) ──
  plugin-tests:
    needs: [check-version-sync]
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node: ["20"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}
      - run: npm ci                  # Installs vitest, obsidian-test-mocks, etc.
        working-directory: tests/plugin/
      - run: npx vitest run
        working-directory: tests/plugin/

  # ── L4: Temp vault E2E ──
  e2e-tests:
    needs: [cli-contract-tests]
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python: ["3.11"]            # Single Python for E2E (cost optimization)
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - run: pip install -e ".[test]"
      - run: pytest tests/e2e/ -q --tb=short --timeout=120

  # ── L5: User journey ──
  journey-tests:
    needs: [e2e-tests]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[test]"
      - run: pytest tests/journey/ -q --tb=short --timeout=300

  # ── Result ──
  all-gates-passed:
    if: always()
    needs: [check-version-sync, unit-tests, cli-contract-tests, plugin-tests, e2e-tests, journey-tests]
    runs-on: ubuntu-latest
    steps:
      - uses: re-actors/alls-green@release/v1
        with:
          jobs: ${{ toJSON(needs) }}
```

### 5.4 ci-chaos.yml — Destructive Tests

```yaml
name: Chaos Tests

on:
  schedule:
    - cron: "0 6 * * 0"      # Every Sunday 06:00 UTC
  workflow_dispatch:           # Manual trigger

jobs:
  chaos-tests:
    strategy:
      fail-fast: false
      matrix:
        python: ["3.12"]
        scenario:
          - corrupt_json_exports
          - missing_pdf_files
          - ocr_api_timeout
          - zotero_junction_broken
          - concurrent_sync_calls
          - interrupted_ocr
          - nonexistent_vault_path
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - run: pip install -e ".[test]"
      - name: Run chaos scenario ${{ matrix.scenario }}
        run: |
          pytest tests/chaos/scenarios/test_${{ matrix.scenario }}.py -q --tb=short --timeout=120
```

### 5.5 Cost Optimization Rationale

| Layer | Full Matrix Rationale |
|-------|----------------------|
| L0 Version check | Single OS (ubuntu). Version checks are OS-independent. |
| L1 Unit tests | **Full 3×3 matrix.** Unit tests catch Python version and OS-specific path/symlink issues. Cheap per-job (~2 min). |
| L2 CLI contracts | **2 Python versions × 1 OS** (Linux). CLI subprocess behavior is largely OS-independent; Python version differences in argparse matter. |
| L3 Plugin tests | **1 Node version × 1 OS.** Obsidian plugin testing with mocks does not vary significantly across Node versions. |
| L4 E2E | **1 Python × 1 OS** (Linux). E2E tests are expensive (~10 min). Run on reference config only. |
| L5 Journey | **1 Python × 1 OS** (Linux). Most expensive (~15 min). Single config validates contract. |
| L6 Chaos | **1 Python × 1 OS** (Linux). Run scenarios in parallel via matrix on scenario, not OS. |

---

## 6. Build Order & Dependencies

### 6.1 Strict Dependency Chain

```
L0 (version sync)
  |
  +-----> L1 (unit tests) ──────────────> L3 (plugin tests)
  |         |                                     |
  |         +-----> L2 (CLI contracts)            |
  |                   |                           |
  |                   +-----> L4 (E2E) ───────────+
  |                             |
  |                             +-----> L5 (journey)
  |
  +-----> L6 (chaos) - INDEPENDENT, scheduled
```

### 6.2 Justification

| Edge | Why |
|------|-----|
| L0 -> L1 | No point running tests if versions are inconsistent (false positives from wrong version comparisons) |
| L1 -> L2 | CLI contracts depend on worker functions being correct; broken units would produce misleading CLI failures |
| L1 -> L3 | Plugin tests and unit tests are independent (Python vs JS). Can run in parallel after L0 passes |
| L2 -> L4 | E2E tests build on contracts — if CLI outputs malformed JSON, E2E will also fail. Run contracts first for faster feedback |
| L4 -> L5 | Journey tests are supersets of E2E; if E2E fails, journeys will too. Run cheaper E2E first |
| L6 standalone | Chaos tests are slow and destructive; run on schedule, not on every PR |

### 6.3 Incremental Adoption

The layers can be rolled out in this order:

```
Phase 1 (v2.0a): L0 + L1 + restructured tests/unit/
  - Move existing tests into tests/unit/
  - Create scripts/check_version_sync.py
  - Create tests/unit/conftest.py
  - Create ci-pr-checks.yml

Phase 2 (v2.0b): L2 + fixtures/
  - Create tests/cli/ with subprocess invoker
  - Create fixtures/ directory with golden datasets
  - Add snapshot testing (pytest-snapshot)
  - Extend CI for L2

Phase 3 (v2.0c): L3 + L4
  - Create tests/plugin/ with Vitest + obsidian-test-mocks
  - Create tests/e2e/ with temp vault lifecycle
  - Create robust mock systems (mock OCR, mock vault builder)
  - Add L3/L4 to CI

Phase 4 (v2.0d): L5 + L6
  - Create UX_CONTRACT.md
  - Create tests/journey/
  - Create tests/chaos/scenarios/
  - Add scheduled chaos workflow
```

---

## 7. pyproject.toml Configuration Updates

```toml
# Additions to existing [tool.pytest.ini_options]
[tool.pytest.ini_options]
addopts = """
    --ignore=tests/sandbox/00_TestVault/
    --ignore=tests/sandbox/
    --strict-markers
"""
markers = [
    "unit: Unit tests (Level 1) — fast, isolated",
    "cli: CLI contract tests (Level 2) — subprocess boundary",
    "plugin: Plugin tests (Level 3) — vitest, not pytest",
    "e2e: End-to-end tests (Level 4) — temp vault",
    "journey: User journey tests (Level 5) — full workflows",
    "chaos: Destructive tests (Level 6) — abnormal scenarios",
    "slow: Tests that take >30s (skip during development)",
    "network: Tests that require network access",
    "snapshot: Tests that use snapshot comparison",
]

[tool.pytest.ini_options]
# Existing addopts remains
addopts = "--ignore=tests/sandbox/00_TestVault/ --strict-markers"
testpaths = ["tests/unit", "tests/cli", "tests/e2e", "tests/journey", "tests/chaos"]
```

**New test dependency additions to `pyproject.toml`:**

```toml
[project.optional-dependencies]
test = [
    "pytest>=7.4.0",
    "pytest-snapshot>=0.9.0",     # Snapshot testing for CLI contracts
    "pytest-timeout>=2.2.0",      # Timeout guards for E2E/chaos tests
    "responses>=0.25.0",          # HTTP mock for OCR backend
    "pytest-mock>=3.12.0",        # Built-in monkeypatch on steroids
    "ruff>=0.4.0",
    "coverage>=7.4.0",            # Coverage measurement
]
```

**Vitest config for plugin tests:**

The plugin tests use a separate JavaScript toolchain. Configuration at `tests/plugin/vitest.config.ts`:

```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./setup.ts'],  // Configures obsidian-test-mocks
    fileParallelism: false,       // Plugin tests are stateful
    include: ['test_*.js'],
  },
  resolve: {
    alias: {
      'obsidian': 'obsidian-test-mocks/obsidian',
    },
  },
});
```

---

## 8. Data Flow Between Layers

### 8.1 Golden Dataset Flow

```
fixtures/
├── zotero/orthopedic.json ───────────> tests/unit/ (via zotero_export fixture)
│                                       tests/cli/ (via vault_builder copy)
│                                       tests/e2e/ (via vault_builder copy)
│
├── pdf/blank.pdf ─────────────────────> tests/unit/ (pdf_resolver tests)
│                                       tests/e2e/ (via Zotero storage copy)
│
├── ocr/paddleocr_success.json ────────> tests/unit/ (via mock_ocr_backend fixture)
│                                       tests/cli/ (via mock_ocr_backend fixture)
│
├── snapshots/paths_json/*.json ───────> tests/cli/ (via snapshot comparison)
│   snapshots/formal_note_frontmatter/   tests/e2e/ (via snapshot comparison)
│
└── ocr/extracted_fulltext.md ─────────> tests/e2e/ (expected output fixture)
```

### 8.2 Mock System Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                   pytest session start                      │
└─────────────────────────────────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
        ┌───────────────────┐   ┌───────────────────┐
        │ tests/conftest.py │   │  conftest per      │
        │ (root)            │   │  layer dir         │
        │                   │   │                    │
        │ vault_builder     │   │ cli: cli_invoker   │
        │ zotero_export     │   │ unit: auto-mocks   │
        │ mock_ocr_backend  │   │ e2e: e2e_vault     │
        └───────────────────┘   └────────────────────┘
                    │                     │
                    ▼                     ▼
        ┌───────────────────────────────────────┐
        │         Each test function            │
        │         - requests fixtures           │
        │         - asserts behavior            │
        │         - cleanup via tmp_path        │
        └───────────────────────────────────────┘
```

---

## 9. Snapshot Testing Architecture

### 9.1 When to Use Snapshots

| Area | Snapshot Type | Tool |
|------|--------------|------|
| CLI `--json` output | Full JSON string | `pytest-snapshot` |
| Formal note frontmatter | YAML/string | `pytest-snapshot` |
| Canonical index JSON | Full JSON | `pytest-snapshot` |
| OCR meta.json | Full JSON | `pytest-snapshot` |
| Figure map JSON | Full JSON | `pytest-snapshot` |

### 9.2 Snapshot Storage Layout

```
fixtures/snapshots/
├── paths_json/
│   └── default_config.json        # Expected output of `paths --json`
├── status_json/
│   └── minimal_vault.json         # Expected output of `status --json`
├── formal_note_frontmatter/
│   └── orthopedic_article.yaml    # Expected frontmatter after sync
└── index_json/
    └── after_sync.json            # Expected index after full sync
```

### 9.3 Snapshot Update Protocol

When a deliberate change modifies output format (e.g., adding a new field to `status --json`):

```bash
# 1. Run tests to see which snapshots fail
pytest tests/cli/ --snapshot-update
# 2. Review the diff
git diff fixtures/snapshots/
# 3. Commit updated snapshots with the feature change
```

---

## 10. Exclusions & Boundaries

### What This Architecture Does NOT Cover

| Area | Reason | Handled By |
|------|--------|------------|
| Real Obsidian plugin E2E | Requires a running Obsidian process; `obsidian-e2e` is experimental and would add 3+ min per test | Manual QA, deferred to v2.1 |
| Real PaddleOCR API integration | Requires API key + network; tested manually via `ocr doctor --live` | Manual test |
| Performance / load testing | PaperForge is a local single-user tool; no load requirement | Not planned |
| Cross-version plugin compat | Plugin runs inside Obsidian which handles its own compatibility | Obsidian manifest `minAppVersion` |
| Installation packaging tests | `pip install` validation is handled by CI matrix's `pip install -e .` step | CI matrix |

### Boundaries Between Layers (What NOT to test in each layer)

| Layer | Don't Test Here | Because |
|-------|-----------------|---------|
| L1 Unit | Subprocess execution, filesystem side effects | Those are L2/L4 concerns |
| L2 CLI | Python API correctness, OCR state transitions | L1 covers those faster |
| L3 Plugin | Python worker logic, CLI output parsing | L1/L2 cover those |
| L4 E2E | Edge cases in individual functions, pure logic | L1 covers those |
| L5 Journey | Exceptions and error states that users never see | L6 covers those |
| L6 Chaos | Happy-path workflows | L4/L5 cover those |

---

## 11. Architecture Decision Records

### ADR-001: Flat tests/ → Subdirectory Migration

- **Status:** Accepted
- **Context:** Existing tests are flat in `tests/`. With 6 layers, flat becomes unmanageable.
- **Decision:** Relocate existing tests to `tests/unit/`. Keep `tests/sandbox/` in place.
- **Consequence:** All existing test imports continue to work (they import from `paperforge.*` which is unchanged). CI must update `testpaths`.

### ADR-002: pytest-snapshot for CLI Contracts

- **Status:** Accepted
- **Context:** CLI JSON output must remain stable across releases. Manual assertions are brittle.
- **Decision:** Use `pytest-snapshot` for CLI contract tests, store snapshots in `fixtures/snapshots/`.
- **Consequence:** Snapshot updates become deliberate commits, forcing review before merging output changes.

### ADR-003: Vitest over Jest for Plugin Tests

- **Status:** Accepted
- **Context:** The plugin uses modern JS (ESM, async/await). Testing options: Vitest vs Jest.
- **Decision:** Use Vitest — native ESM support, faster watch mode, better `obsidian-test-mocks` integration.
- **Consequence:** Plugin devs need Node 20+. CI runs a separate `npm ci && npx vitest run` step.

### ADR-004: Plasma CI Matrix (not Full Cartesian)

- **Status:** Accepted
- **Context:** A full 3×3×1 matrix (OS × Python × Node) for all layers would cost 27+ CI jobs per PR.
- **Decision:** Use a plasma matrix — L1 runs on full 3×3, L2-L5 run on progressively narrower configs.
- **Consequence:** Some OS × Python combinations are untested for L2-L5. Acceptable because L1 covers OS-specific code paths.

### ADR-005: Mock OCR at HTTP Layer, Not Module Layer

- **Status:** Accepted
- **Context:** OCR tests need to intercept network calls. Options: mock `requests` at module level vs mock HTTP entirely.
- **Decision:** Use `responses` library to intercept at the HTTP layer. Fixtures are real PaddleOCR response examples.
- **Consequence:** Tests capture the full request/response flow. Adding new API endpoints automatically exercises mock coverage.

### ADR-006: Golden Datasets in fixtures/, Not in tests/

- **Status:** Accepted
- **Context:** Fixture JSON files and PDFs were previously scattered across `tests/fixtures/`, `tests/sandbox/`, and `tests/`.
- **Decision:** Centralize all golden datasets in `<repo_root>/fixtures/` with subdirectories by type.
- **Consequence:** All layers reference the same canonical fixtures. Clear boundary between test code and test data.

---

## Sources

- pytest documentation on good integration practices: https://pytest.org/latest/goodpractices.html (MEDIUM confidence — verified via Exa search)
- obsidian-test-mocks: https://registry.npmjs.org/obsidian-test-mocks (MEDIUM confidence — verified via Exa search)
- obsidian-e2e: https://registry.npmjs.org/obsidian-e2e (MEDIUM confidence — verified via Exa search)
- GitHub Actions matrix testing patterns: https://docs.github.com/en/actions/guides/building-and-testing-python (HIGH confidence — official GitHub docs)
- Python test pyramid best practices: https://pytest-with-eric.com/pytest-best-practices/pytest-organize-tests/ (MEDIUM confidence — community expert)
