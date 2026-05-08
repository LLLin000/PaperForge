# Technology Stack: v2.0 Testing Infrastructure

**Project:** PaperForge v2.0
**Researched:** 2026-05-08

## Recommended Stack

### Core Test Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | >=8.0 | Python test framework | Already in use; industry standard for Python |
| pytest-snapshot | >=0.9.0 | Snapshot/approval testing | CLI JSON output stability contracts; simpler than full approval-testing libs |
| pytest-timeout | >=2.2.0 | Test timeout guards | Prevent runaway E2E/chaos tests from blocking CI |
| pytest-mock | >=3.12.0 | Enhanced mocking | Built-in monkeypatch replacement; integrates with `unittest.mock` |
| responses | >=0.25.0 | HTTP mock library | Intercept `requests` library calls at HTTP layer for mock OCR backend |
| coverage | >=7.4.0 | Coverage measurement | Standard Python coverage tool; generates CI reports |

### Plugin Test Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Vitest | >=2.0 | JS test runner | Native ESM support (plugin uses `require` but can be wrapped); ~2x faster than Jest |
| obsidian-test-mocks | >=0.12 | Obsidian API mocks | Comprehensive mock implementations of `obsidian.d.ts`; 100% code coverage maintained |
| jsdom | >=24.0 | DOM environment | Required by Obsidian plugin tests (document, window access) |
| Node.js | >=20.0 | JS runtime | Required by Vitest and obsidian-test-mocks |

### CI Infrastructure
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| actions/setup-python | v5 | Python version management | Standard GitHub Action; supports cache, pre-release |
| actions/setup-node | v4 | Node version management | Required for plugin tests |
| actions/checkout | v4 | Source checkout | Latest stable checkout action |
| re-actors/alls-green | v1 | CI gate aggregation | Simplifies "all jobs passed" check with branch protection |

### Supporting Scripts
| Script | Language | Purpose |
|--------|----------|---------|
| `scripts/check_version_sync.py` | Python | Level 0: verify version consistency across 6+ files |
| `scripts/run_all_tests.sh` | Bash | Sequential runner for local testing |
| `scripts/run_chaos_tests.sh` | Bash | Chaos test runner with scenario selection |
| `scripts/generate_fixtures.py` | Python | Regenerate golden datasets from canonical sources |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| HTTP Mock | responses | pytest-httpx | responses is simpler and sufficient for `requests`-based OCR calls; httpx adds unnecessary dependency |
| Plugin Test Mock | obsidian-test-mocks | Manual `__mocks__/obsidian.ts` | Manual obsidian mocking requires constant maintenance as API evolves; obsidian-test-mocks is community-maintained with 100% coverage |
| JS Test Runner | Vitest | Jest | Jest requires transforms for ESM; Vitest is natively ESM-compatible and faster for watch mode |
| Snapshot Testing | pytest-snapshot | syrupy | pytest-snapshot is simpler; syrupy's extra features (serializer plugins) not needed for JSON-only snapshots |
| CI Orchestration | Native GitHub Actions | tox | tox adds complexity for simple package install; actions/setup-python + pip install is more transparent and debuggable |
| Obsidian E2E Testing | Deferred to v2.1 | obsidian-e2e / obsidian-integration-testing | Both require a running Obsidian process, add 3+ min per test, and are flaky in CI. Not worth the cost for current milestone |

## Installation

```toml
# pyproject.toml additions
[project.optional-dependencies]
test = [
    "pytest>=7.4.0",
    "pytest-snapshot>=0.9.0",
    "pytest-timeout>=2.2.0",
    "responses>=0.25.0",
    "pytest-mock>=3.12.0",
    "coverage>=7.4.0",
    "ruff>=0.4.0",
]
```

```bash
# Plugin test dependencies (separate package.json in tests/plugin/)
npm install --save-dev vitest obsidian-test-mocks jsdom
```

## Sources

- pytest documentation: https://pytest.org/ (HIGH confidence — official docs)
- pytest-snapshot: https://pypi.org/project/pytest-snapshot/ (MEDIUM confidence — verified via search)
- obsidian-test-mocks: https://www.npmjs.com/package/obsidian-test-mocks (MEDIUM confidence — verified via Exa search)
- Vitest: https://vitest.dev/ (HIGH confidence — official docs)
- GitHub Actions setup-python: https://github.com/actions/setup-python (HIGH confidence — official docs)
- responses library: https://pypi.org/project/responses/ (HIGH confidence — official docs)
