# Feature Landscape: 6-Layer Testing Infrastructure

**Domain:** Multi-layer quality gate testing
**Researched:** 2026-05-08

## Table Stakes

Features the testing infrastructure must provide. Missing any = incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Version consistency gate (L0) | Preventing deployment with mismatched versions across Python package, Obsidian plugin, and config is critical for Ops | Low | Single Python script; checks `__init__.py`, `manifest.json`, `versions.json` |
| Unit tests (L1) | Without isolated unit tests, regressions are caught too late (E2E only) | Low | Existing 470+ tests move into `tests/unit/` |
| CLI output contract tests (L2) | Plugin and agents parse CLI JSON output; schema changes break downstream | Medium | Subprocess invoker + snapshot assertions |
| Plugin unit tests (L3) | Plugin JS runs inside Obsidian; mock-based tests catch logic errors before manual QA | Medium | Vitest + obsidian-test-mocks |
| E2E pipeline tests (L4) | Integration points between sync/OCR/status must be tested together | High | Temp vault lifecycle; 3 mock systems |
| Golden datasets | Deterministic test data shared across all layers | Medium | Centralized `fixtures/` with zotero/, pdf/, ocr/, snapshots/ |
| CI integration | Tests must run automatically on PR and merge | Medium | GitHub Actions workflows with matrix |
| Mock system for OCR | Tests must not hit real PaddleOCR API | Medium | `responses` HTTP mock + fixture JSON responses |
| Mock system for Zotero | Tests must not require real Zotero installation | Low | Static JSON fixtures in `fixtures/zotero/` |
| Mock vault filesystem | Each test needs an isolated, disposable vault | Medium | `tmp_path` + factory function for configurable completeness |

## Differentiators

Features that add significant value beyond basic testing.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Snapshot testing for CLI output | Catches unintended output changes immediately; makes output format changes deliberate commits | Low | Single assertion per contract test |
| Plasma CI matrix | Optimizes CI cost while maintaining coverage confidence | Medium | Full matrix for fast tests, narrow matrix for slow tests |
| User journey tests (L5) | Validates complete workflows against documented UX contracts; catches cross-component gaps that E2E misses | High | Most expensive tests; run only on merge to main |
| Chaos/destructive tests (L6) | Ensures system handles corrupted inputs, network failures, disk issues gracefully | High | Scheduled weekly; parallelized by scenario |
| Hierarchical conftest fixtures | Root conftest provides shared fixtures; each layer's conftest extends/overrides | Medium | Reduces duplication while keeping layer-specific behavior |
| Unified vault_builder factory | Single entry point for creating vaults at 3 completeness levels | Medium | `VaultBuilder(fixtures_root)` with `"minimal"`, `"standard"`, `"full"` modes |
| Chaos scenario matrix documentation | `CHaOS_MATRIX.md` documents all destructive scenarios, triggers, expected behavior | Low | Living document; updated as new edge cases discovered |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Real Obsidian E2E in CI | Requires running Obsidian process; adds 3+ min per test; flaky results | Use `obsidian-test-mocks` for unit tests; manual QA for real Obsidian |
| Load/performance testing | PaperForge is local single-user tool; no performance requirements | Not needed; defer unless user reports slow performance |
| Cross-browser testing | Plugin runs inside Obsidian's Electron instance (Chromium) | Not applicable; plugin does not need cross-browser compat |
| Full parallel test matrix (3×3×6) | Would cost 54 CI jobs per PR for minimal added confidence | Plasma matrix: L1 on 3×3, L2-L5 on 1-2 configs |
| Test database / snapshots on every test | Snapshot tests add maintenance burden; use only for CLI contract output | Limit snapshot tests to JSON output format stability |
| Automated visual regression | Screenshot-based plugin UI tests are fragile and high-maintenance | Defer; component-level tests catch logic errors at lower cost |

## Feature Dependencies

```
fixtures/ (golden datasets)
    |
    +--> L0 (version check) -- independent, needs only scripts/
    |
    +--> L1 (unit tests) -- needs fixtures/ + mock systems
    |       |
    |       +--> L2 (CLI contracts) -- needs L1 + fixtures/snapshots/
    |
    +--> L3 (plugin tests) -- independent of Python layers; needs fixtures/ for mock vault config
    |
    L2 + L3
    |
    +--> L4 (E2E) -- needs golden datasets + mock systems + vault_builder
    |       |
    |       +--> L5 (journey) -- needs E2E working + UX_CONTRACT.md
    |
    L6 (chaos) -- independent but shares mock systems
```

## MVP Recommendation

**Must have for v2.0 launch:**

1. **L0 + L1** (version sync + unit tests) — highest value per effort; existing tests just need relocation
2. **`fixtures/` directory** (golden datasets) — prerequisite for all higher layers
3. **Mock OCR backend** — enables deterministic testing without real API calls
4. **L2 CLI contract tests** — protects the plugin<->Python boundary
5. **`ci-pr-checks.yml`** — fast pre-flight gate (L0 + L1) on every PR

**Must have for v2.0 completion:**

6. **L3 plugin tests** — Vitest + obsidian-test-mocks
7. **L4 temp vault E2E** — full pipeline confidence
8. **`ci.yml` full gate** — complete CI with all layers

**Defer to v2.1 if needed:**

9. **L5 journey tests** — high effort; most value after core pipeline is proven
10. **L6 chaos tests** — valuable but can be added incrementally post-launch

## Sources

- Existing codebase analysis: all 30 existing test files audited for behavioral correctness
- pytest best practices (verified via Exa search): pytest-with-eric.com, orchestrator.dev
- GitHub Actions matrix patterns (verified via official docs): docs.github.com/en/actions/guides/building-and-testing-python
