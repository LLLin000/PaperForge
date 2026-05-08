# Project Research Summary

**Project:** PaperForge v2.0 — Testing Infrastructure (6-Layer Quality Gates)
**Domain:** Brownfield hybrid Python + Obsidian plugin project — multi-layer quality gate testing
**Researched:** 2026-05-08
**Confidence:** HIGH

## Executive Summary

PaperForge is a **brownfield hybrid Python + Obsidian plugin** project that manages literature assets (Zotero exports, PDFs, OCR fulltext, figures, notes, and AI outputs) as a local-first research library. The current milestone (v2.0) adds a **6-layer quality gate testing infrastructure** — version consistency, Python unit tests, CLI contract tests, plugin-backend integration, temp vault E2E workflows, user journey contracts, and destructive scenarios — with CI matrix, golden datasets, and snapshot testing. The product has 473+ existing tests that need restructuring into a test pyramid, and the testing infrastructure itself is the deliverable.

The recommended approach is a **modified testing diamond** with strict layer dependency ordering (L0 -> L1 -> L2/L3 in parallel -> L4 -> L5), a **plasma CI matrix** (full 3x3 only for unit tests, narrow configs for higher layers), **hierarchical pytest fixtures** (5 levels from empty_vault to full_test_vault), and **shape-specific snapshot assertions** (not whole-file JSON). The build order is: fixtures first, then Python layers (L0-L2), then JS layers (L3), then expensive integration layers (L4-L6).

**Key risks and mitigations:**
1. **Mock drift** — mocks that silently diverge from real APIs. Mitigation: capture real PaddleOCR responses before mocking; use `autospec=True` on all patches; limit patch nesting to 3 levels.
2. **CI combinatorial explosion** — trying to run everything on every platform. Mitigation: plasma CI matrix with path-filtered jobs; L1 on 3x3; L2-L5 on 1-2 configs; slow tests on nightly only.
3. **Snapshot brittleness** — whole-file snapshot assertions that break on every refactor. Mitigation: assert specific shapes with normalized dynamic fields; use `dirty-equals` for timestamps/UUIDs.
4. **Windows path hell** — junctions, symlinks, temp dir differences. Mitigation: at least one Windows CI node; platform-specific tests with `@pytest.mark.skipif`; path normalization utilities.
5. **Fixture bloat** — 100MB+ fixture directories in git. Mitigation: generate fixtures from code; track with manifest; keep large fixtures outside git repo.

## Key Findings

### Recommended Stack

The testing stack splits cleanly into Python test infrastructure and JavaScript plugin test infrastructure, plus CI orchestration.

**Core test framework (Python):**

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| pytest | >=8.0 | Python test framework | Already in use; industry standard |
| pytest-snapshot | >=0.9.0 | Snapshot/approval testing | CLI JSON output stability contracts |
| pytest-timeout | >=2.2.0 | Test timeout guards | Prevent runaway E2E/chaos tests |
| pytest-mock | >=3.12.0 | Enhanced mocking | Better than raw monkeypatch |
| responses | >=0.25.0 | HTTP mock library | Intercept `requests` at HTTP layer for mock OCR |
| coverage | >=7.4.0 | Coverage measurement | Standard Python tool; CI reports |
| ruff | >=0.4.0 | Linting | Already in use via pre-commit hooks |

**Plugin test framework (JavaScript):**

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| Vitest | >=2.0 | JS test runner | Native ESM; 2x faster than Jest; better `obsidian-test-mocks` integration |
| obsidian-test-mocks | >=0.12 | Obsidian API mocks | Community-maintained; 100% code coverage |
| jsdom | >=24.0 | DOM environment | Required by plugin tests (document/window access) |
| Node.js | >=20.0 | JS runtime | Required by Vitest and obsidian-test-mocks |

**CI Infrastructure:**

| Technology | Version | Purpose |
|------------|---------|---------|
| actions/setup-python | v5 | Python version management with cache |
| actions/setup-node | v4 | Node.js version management |
| actions/checkout | v4 | Source checkout |
| re-actors/alls-green | v1 | CI gate aggregation (all-jobs-passed check) |

**Alternatives considered and rejected:**
- **Jest** rejected over Vitest (ESM compatibility, speed)
- **tox** rejected for CI (superfluous complexity; raw pip install is more transparent)
- **syrupy** rejected over pytest-snapshot (extra features not needed for JSON-only snapshots)
- **Real Obsidian E2E** rejected as too expensive (3+ min per test, flaky) — deferred to v2.1

### Expected Features

**Must have (table stakes):**
- **L0: Version consistency gate** — prevents deployment with mismatched versions across 6+ files. Low complexity. Single Python script.
- **L1: Python unit tests** — existing 470+ tests relocated to `tests/unit/`. Low complexity. Fast isolation.
- **L2: CLI contract tests** — subprocess invoker + snapshot assertions on `--json` output. Medium complexity. Protects plugin<->Python boundary.
- **L3: Plugin unit tests** — Vitest + obsidian-test-mocks. Medium complexity. Catches JS logic errors before manual QA.
- **L4: Temp vault E2E tests** — full pipeline (sync -> OCR -> status -> repair) in disposable vault. High complexity. 3 mock systems.
- **Golden datasets** — centralized `fixtures/` with zotero/, pdf/, ocr/, snapshots/. Medium complexity. Prerequisite for all higher layers.
- **Mock OCR backend** — intercepts PaddleOCR at HTTP layer with `responses`. Medium complexity. Enables deterministic testing.
- **Mock Zotero data source** — static JSON fixtures in 3 BBT path formats. Low complexity.
- **Mock vault filesystem** — `tmp_path` + factory function with configurable completeness. Medium complexity.
- **CI integration** — GitHub Actions with matrix strategies. Medium complexity.

**Should have (differentiators):**
- **Snapshot testing for CLI output** — catches unintended changes immediately. Single assertion per contract test.
- **Plasma CI matrix** — optimizes CI cost while maintaining coverage. Full matrix for fast tests, narrow for slow tests.
- **User journey tests (L5)** — validates complete workflows against documented UX contracts. Catches cross-component gaps.
- **Chaos/destructive tests (L6)** — corrupted inputs, network failures, disk issues. Ensures graceful degradation.
- **Hierarchical conftest fixtures** — root conftest provides shared fixtures; each layer extends/overrides.
- **VaultBuilder factory** — single entry point for 3 completeness levels: "minimal", "standard", "full".
- **CHAOS_MATRIX.md** — documentation of all destructive scenarios, triggers, expected behavior.

**Anti-features (explicitly NOT building):**
- Real Obsidian E2E in CI (3+ min per test, flaky)
- Load/performance testing (local single-user tool)
- Cross-browser testing (plugin runs in Chromium-only Electron)
- Full parallel matrix (54 CI jobs per PR for minimal confidence)
- Automated visual regression (fragile; component-level tests suffice)

### Architecture Approach

The testing architecture follows a **modified testing diamond** (unit tests at base, integration/contract in the middle, E2E at top) with an extra **L0 version-check layer** as the fast pre-flight gate. All layers share a centralized `fixtures/` golden dataset with 4 subdirectories (zotero/, pdf/, snapshots/, ocr/). Mock systems are layered: HTTP-level (`responses` for OCR), static fixtures (for Zotero), and `tmp_path` (for vault filesystem).

**Major components:**
1. **L0: `scripts/check_version_sync.py`** — validates all 6+ version declarations (Python **init**, manifest.json, versions.json, CHANGELOG) before any tests run. Sub-100ms. Single CI job on ubuntu.
2. **L1: `tests/unit/`** — relocated existing 470+ tests. No external dependencies. Mock everything outside module under test. <30s full suite. Coverage >85% for core, >75% for workers.
3. **L2: `tests/cli/`** — subprocess invoker asserts exit codes, stdout JSON schemas, stderr patterns. Uses `pytest-snapshot` with shape-specific assertions (not whole-file).
4. **L3: `tests/plugin/`** — Vitest + obsidian-test-mocks + jsdom. Tests plugin lifecycle, settings, dashboard, i18n. Extracts `paperforge-backend.js` for Node.js-testable backend module.
5. **L4: `tests/e2e/`** — creates full temp vault; calls Python worker functions directly (not subprocess). Session-scoped golden vault + per-test fast clone for performance.
6. **L5: `tests/journey/`** — UX contract-driven complete workflows. Single concrete scenario per test. Step abstraction layer. Nightly-only.
7. **L6: `tests/chaos/scenarios/`** — 8 destructive scenarios documented in CHAOS_MATRIX.md. Docker-only isolation. Safety contracts on every test.
8. **`fixtures/`** (golden dataset) — centralized at repo root. zotero/ (8 JSON fixtures), pdf/ (4 minimal PDFs), snapshots/ (4 subdirectories), ocr/ (5 fixture files). Generated from code where possible.
9. **CI workflows** — 3 workflow files: `ci-pr-checks.yml` (L0+L1 per push, <2min), `ci.yml` (L0-L5 on merge to main), `ci-chaos.yml` (L6 weekly + manual).

**Key patterns:**
- **Plasma CI matrix:** L1 on full 3 OS x 3 Python (9 jobs); L2 on 2 Python x 1 OS (2 jobs); L3-L5 on single config (1 job each)
- **Fixture hierarchy (5 levels):** `empty_vault` (config only) -> `config_vault` (+ dirs) -> `vault_with_export` (+ BBT JSON) -> `vault_with_ocr` (+ OCR data) -> `full_test_vault` (+ Zotero storage, formal notes)
- **Mock OCR with `responses`:** intercepts at HTTP layer, not module level. Fixtures from real API captures. Prevents mock drift.
- **Snapshot update protocol:** `pytest --snapshot-update` -> review diff -> commit deliberately. Never "regenerate all snapshots."
- **Truth hierarchy:** L4 is authoritative for "does it work?"; L2 validates CLI translation; L1 validates edge cases. L1 mocks must be validated against L4 output.

### Critical Pitfalls

**Top 7 pitfalls from research (ordered by severity):**

1. **Mocking External Services Too Early and Too Rigidly** — The existing test suite already demonstrates 12+ levels of nested `with patch(...):` blocks. Mocks created from memory (not real API captures) silently drift from real PaddleOCR behavior. Tests pass but production breaks. *Prevention: capture real API responses first; use `autospec=True` on all patches; limit nesting to 3 levels via fixture extraction; add VCR.py layer for OCR polling.*

2. **CI Matrix Combinatorial Explosion Killing Feedback Loops** — A naive full matrix (3 OS x 3 Python x 2 Node = 18 jobs at 15 min each = 4.5 hours wall-clock). Developers wait all day or skip CI. *Prevention: plasma matrix with path-filtered jobs; L1 on 3x3; L2-L5 on narrower configs; `pytest -m "not slow"` for push; hard CI budget of 20 concurrent runners.*

3. **Snapshot Tests Breaking on Every Refactor** — Whole-file JSON snapshots cause 500-line diffs for 5-line code changes. "Regenerated all snapshots" becomes the default review response — regressions slip through. *Prevention: assert specific shapes, not whole files; normalize dynamic fields (timestamps, UUIDs) before snapshotting; use `inline-snapshot` or `dirty-equals` for version-agnostic comparisons.*

4. **Temp Vault Tests Being Slow, Non-Deterministic, or Platform-Specific** — E2E tests with subprocess calls take 30-60 seconds each. Cross-platform path issues (Windows junctions, macOS `/var` -> `/private/var` symlinks). `shutil.rmtree` fails on Windows with `PermissionError`. *Prevention: session-scoped golden vault + per-test fast clone; separate "fast" (Python API) from "full" (subprocess) E2E; safe teardown with retry on Windows; normalize paths in all assertions.*

5. **User Journey Tests Being Too Vague to Automate** — Prose UX contracts like "User opens Obsidian, configures Zotero, runs OCR" are ambiguous and un-automatable. Tests either hardcode assumptions or check nothing meaningful. *Prevention: write journey tests as pseudo-code BEFORE implementation; create a "step" abstraction layer (not raw Playwright); define EXACTLY ONE concrete scenario per test; create journey fixture packs for pre-configured states.*

6. **Destructive Tests That Damage Developer Machines or CI Shared State** — Chaos tests that delete files or modify config can accidentally run on real vaults if `--vault` is omitted or fixture paths resolve incorrectly. *Prevention: ALL destructive tests MUST use `tmp_path` with isolation assertion (`assert "tmp" in str(vault)`); run in Docker only; add safety contract comment to every destructive test function; keep in separate module ignored by default test runner.*

7. **Golden Dataset and Fixture Bloat** — Fixtures grow from 10KB to 100MB+ in git over 6 months. Nobody knows which are still used. Binary fixtures (PDFs, OCR JSON) permanently bloat git history. *Prevention: generate fixtures from code (not hand-written); keep large fixtures outside git via `download_fixtures.py` script; track with MANIFEST.json and validate coverage in CI; version fixture schemas explicitly.*

**See `.planning/research/PITFALLS.md` for all 13 pitfalls, including:** fixture inheritance conflicts (P13), Windows path hell (P12), test layering conflicts (P11), plugin tests testing subprocess mechanics instead of behavior (P10), CLI --json tests checking shape but not semantics (P9), and version sync checking the wrong things (P8).

## Implications for Roadmap

Based on combined research, the testing infrastructure should be built in **5 phases** with strict dependency ordering. Each phase delivers value independently and is testable before the next begins.

### Phase 1: Foundation — Fixture Hierarchy + L0 + L1 Relocation

**Rationale:** All higher layers depend on healthy fixtures and a working test runner. The existing 473+ tests must be relocated into the new hierarchy before any new tests are written. L0 (version check) and L1 (unit tests) can be extracted early because they require minimal new infrastructure.

**Delivers:**
- Refactored `tests/conftest.py` with 5-level fixture hierarchy (`empty_vault` -> `config_vault` -> `vault_with_export` -> `vault_with_ocr` -> `full_test_vault`)
- All existing tests relocated from flat `tests/` to `tests/unit/` (pure directory moves, no behavior changes)
- `scripts/check_version_sync.py` (L0: validates 6+ version declarations, semver structure, installed `--version` against source)
- `ci-pr-checks.yml` (L0 on ubuntu + L1 on full 3x3 matrix, <2 min)
- `pyproject.toml` updated with markers, testpaths, new dependencies
- `tests/sandbox/` retained in place for backward compat

**Addresses:** FEATURES.md table stakes (L0, L1)
**Avoids:** PITFALLS.md P13 (fixture inheritance) — implement hierarchy before any new tests; P8 (version sync wrong checks) — validate installed version not file strings
**Stack:** pytest >=8.0, pytest-timeout >=2.2.0, pytest-mock >=3.12.0, coverage >=7.4.0, ruff >=0.4.0
**Research flag:** Well-documented patterns — pytest fixtures and test organization are standard. No deep research needed.

### Phase 2: Golden Datasets + CLI Contract Tests (L2)

**Rationale:** The `fixtures/` golden dataset is the shared foundation for L2-L6. L2 (CLI contracts) is the most valuable integration layer — it protects the Python<->plugin boundary with minimal setup (subprocess invoker + snapshot assertions). Building fixtures and L2 together ensures fixture design matches real usage.

**Delivers:**
- `fixtures/` directory structure: zotero/ (8 fixtures), pdf/ (4 minimal PDFs), snapshots/ (4 subdirectories), ocr/ (5 files)
- `fixtures/MANIFEST.json` — tracks `used_by`, `generated`, `desc` for each fixture
- `tests/cli/` with subprocess invoker fixture and contract tests for all 7 CLI commands
- `pytest-snapshot` integrated with shape-specific assertions (not whole-file)
- Mock OCR backend with `responses` library, using fixture responses captured from real API
- `ci.yml` extended with L2 on 2 Python versions x 1 OS
- All L2 tests excluded from `ci-pr-checks.yml` (they depend on L1 being green)

**Addresses:** FEATURES.md table stakes (golden datasets, mock OCR, L2), differentiators (snapshot testing)
**Avoids:** PITFALLS.md P1 (mock drift) — capture real API first; P3 (snapshot brittleness) — shape assertions; P7 (fixture bloat) — MANIFEST + CI validation; P9 (CLI shallow tests) — schema validation + cross-command consistency
**Research flag:** **Needs research** — Snapshot testing strategy decisions: inline vs external snapshots, normalization helpers for dynamic fields. Low risk, but needs concrete examples before implementation.

### Phase 3: Plugin Tests + Temp Vault E2E (L3 + L4)

**Rationale:** L3 and L4 can be built in parallel (they target different runtimes: JS vs Python). L3 (plugin) is independent of Python layers; L4 (E2E) depends on L2 being stable (contracts define what E2E tests should verify). Building them together optimizes the critical path.

**Delivers:**
- `tests/plugin/` with Vitest + obsidian-test-mocks + jsdom
- Extracted `paperforge-backend.js` module for Node.js-testable backend interface
- Plugin lifecycle, settings, dashboard, i18n, subprocess dispatch tests
- `tests/e2e/conftest.py` with session-scoped golden vault + per-test fast clone
- Temp vault E2E tests: full sync-OCR-status pipeline, repair workflow, headless setup, migration, doctor, multi-domain
- Safe teardown with Windows file-lock retry
- Mock OCR used in L2/L3/L4 with layer-specific fixture configurations
- CI extended with L3 (1 Node) + L4 (1 Python, 1 OS)

**Addresses:** FEATURES.md must-haves (L3, L4), differentiators (VaultBuilder factory)
**Avoids:** PITFALLS.md P4 (temp vault slow) — session-scoped + per-test clone; P10 (plugin subprocess mechanics) — extract backend module; P12 (Windows path hell) — platform-specific marks + normalization
**Research flag:** **Needs research** — `obsidian-test-mocks` API surface: does it support the specific `App`, `Workspace`, `Plugin` APIs used by PaperForge? Verify by loading the npm package and comparing against actual usage in `paperforge/plugin/main.js`.

### Phase 4: User Journey + Chaos Tests (L5 + L6)

**Rationale:** These are the most expensive and least stable tests. They should be built LAST, after the foundation (L0-L4) is solid. L5 depends on L4 for vault infrastructure; L6 is independent but shares mock systems with L2.

**Delivers:**
- `tests/journey/UX_CONTRACT.md` — concrete step sequences for each user journey
- 4 journey tests: new user onboarding, daily workflow, upgrade migration, error recovery
- Journey fixture packs: "half-setup", "ready-for-deep-reading" pre-configured environments
- `tests/chaos/scenarios/CHAOS_MATRIX.md` — 8 destructive scenarios documented
- 8 chaos test files with Docker-only isolation and safety contracts
- `ci-chaos.yml` — weekly schedule + manual trigger, scenarios parallelized by matrix
- Journey tests NOT in PR gate (nightly only); chaos tests NOT in regular CI

**Addresses:** FEATURES.md differentiators (L5, L6, chaos matrix doc)
**Avoids:** PITFALLS.md P5 (vague journeys) — concrete scenarios + step abstraction; P6 (destructive safety) — isolation assertions + Docker
**Research flag:** **Needs research** — Chaos scenario design: what are the real-world failure modes for PaddleOCR API, Zotero junctions, concurrent sync calls? Needs domain knowledge from the existing codebase's error-handling paths.

### Phase 5: CI Matrix Optimization + Consistency Audit

**Rationale:** The final phase optimizes and hardens the CI pipeline based on real data from earlier phases. Path filters, performance baselines, and cross-layer consistency audits should be informed by actual CI run times and failure patterns.

**Delivers:**
- Path-filtered CI triggers (e.g., changes to `ocr.py` trigger L1+L2+L4; changes to `main.js` trigger L3)
- `pytest -m "slow"` markers for tests >30s (moved to nightly or merge-only)
- Consistency audit test: validates L1 mock expectations against L4 real output
- `re-actors/alls-green` gate aggregation for branch protection
- `scripts/validate_fixtures.py` — CI check that every fixture is referenced by at least one test
- CI budget enforcement: max 20 concurrent runners; single-config L2-L5

**Addresses:** FEATURES.md differentiators (plasma CI matrix), anti-features avoidance (full matrix)
**Avoids:** PITFALLS.md P2 (CI too slow) — plasma matrix; P11 (test layering conflicts) — truth hierarchy + mock validation
**Research flag:** **Standard patterns** — GitHub Actions path filters and matrix strategies are well-documented. No deep research needed.

### Phase Ordering Rationale

1. **Fixtures before tests** (Phase 1 before Phase 2): Golden datasets and fixture hierarchy are prerequisites for ALL test layers. Building them first prevents the "kitchen sink" fixture anti-pattern and fixture bloat.
2. **Python before JS** (Phase 2 before Phase 3): L2 CLI contracts define the interface between Python and plugin JS. Building L2 first means L3 can validate against known contracts. However, L3 and L4 can be parallelized since they target different runtimes.
3. **Cheap before expensive** (L0-L2 before L4-L6): The most valuable-per-effort tests (version sync, unit, CLI contracts) cost <2 min CI time. They catch 80% of regressions. E2E, journey, and chaos tests add 10-30 min each and should be built only when the fast layers are solid.
4. **Optimize last** (Phase 5 after all others): CI matrix optimization metrics (path filter accuracy, test durations, flake rates) can only be measured once all phases are running in CI. Optimizing earlier would be premature.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Golden datasets + L2):** Snapshot testing strategy — inline vs external, normalization helpers. Low risk, but need concrete decisions before implementation.
- **Phase 3 (L3 plugin tests):** `obsidian-test-mocks` API surface coverage — does it fully support PaperForge's Obsidian API usage patterns? Verify by loading the npm package.
- **Phase 4 (L5 + L6):** Chaos scenario design — what are the real-world failure modes for PaddleOCR, Zotero junctions, concurrent sync? Needs codebase analysis of error-handling paths.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** pytest fixture hierarchy, test relocation, version checking — well-documented established patterns
- **Phase 5 (CI optimization):** GitHub Actions path filters, matrix strategies — official docs are comprehensive

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | pytest, Vitest, obsidian-test-mocks, responses are well-documented and verified against official sources. Alternatives analysis is thorough. |
| Features | HIGH | Feature landscape derived from existing codebase analysis (473+ tests) + official docs. Table stakes, differentiators, and anti-features are clearly scoped. |
| Architecture | HIGH | Detailed directory structure, mock system architecture, CI matrix design, fixture hierarchy, and 6 ADRs. All decisions have clear rationale and alternatives considered. |
| Pitfalls | HIGH | 13 pitfalls identified with prevention strategies, recovery plans, and phase mapping. Based on existing codebase analysis (12-level mock nesting, single fixture patterns) + external sources (pytest best practices, snapshot testing analysis). |

**Overall confidence:** HIGH

### Gaps to Address

1. **`obsidian-test-mocks` API coverage validation** — The npm package claims 100% code coverage of `obsidian.d.ts`, but PaperForge uses specific APIs (settings tab, dashboard views, subprocess dispatch). Need to verify the mock covers all usage in `paperforge/plugin/main.js` before Phase 3 implementation.

2. **Real PaddleOCR response format** — Mock OCR fixture design depends on capturing at least one real API response. If the API has changed or is inaccessible, fixture generation will need a different approach (e.g., API documentation or developer-provided example).

3. **CI budget constraints** — The plasma matrix assumes GitHub-hosted runners are available. If this is a self-hosted runner or has credit limits, the matrix may need further reduction. Phase 5 should calibrate based on actual limits.

4. **Windows junction behavior in CI** — Windows GitHub Actions runners may have different junction/symlink behavior than local Windows machines. The Windows E2E test may need adjustment after initial CI runs on Windows.

## Sources

### Primary (HIGH confidence)
- **pytest documentation:** https://pytest.org/ — fixture scopes, tmp_path, markers, import modes
- **GitHub Actions setup-python:** https://github.com/actions/setup-python — matrix patterns, version management
- **GitHub Actions docs:** https://docs.github.com/en/actions/guides/building-and-testing-python — CI matrix optimization
- **responses library docs:** https://pypi.org/project/responses/ — HTTP mock library
- **Project codebase:** `tests/conftest.py`, `tests/test_ocr_state_machine.py`, `tests/test_e2e_cli.py`, `tests/test_e2e_pipeline.py`, `tests/test_plugin_install_bootstrap.py` — existing 473+ test behavioral analysis
- **Project version schema:** `paperforge/__init__.py`, `manifest.json`, `pyproject.toml` — multiple version sources

### Secondary (MEDIUM confidence)
- **pytest-snapshot:** https://pypi.org/project/pytest-snapshot/ — verified via PyPI search; community-maintained
- **obsidian-test-mocks:** https://www.npmjs.com/package/obsidian-test-mocks — verified via Exa search; community-maintained
- **Vitest:** https://vitest.dev/ — official docs
- **pytest-with-eric.com** (2024-2026): Fixture management, temp directory strategies, flaky test stabilization — community expert patterns
- **CircleCI documentation:** Test splitting, parallelism strategies — adapted for GitHub Actions
- **snapshot testing analysis (2025-01):** "Why Snapshot Testing Sucks" — targeted behavior-driven assertions

### Tertiary (LOW confidence)
- **obsidian-e2e:** https://www.npmjs.com/package/obsidian-e2e — evaluated and rejected; experimental, needs real Obsidian process

### Research Files (full details)
- **STACK.md:** Complete technology stack with versions, rationale, alternatives, and installation config (.planning/research/STACK.md)
- **FEATURES.md:** Full feature landscape with table stakes, differentiators, anti-features, dependencies, and MVP recommendation (.planning/research/FEATURES.md)
- **ARCHITECTURE.md:** Complete architecture with directory structure, mock systems, CI matrix, snapshot strategy, 6 ADRs, and build order (.planning/research/ARCHITECTURE.md)
- **PITFALLS.md:** 13 pitfalls with prevention strategies, recovery costs, "looks done but isn't" checklist, performance traps, and integration gotchas (.planning/research/PITFALLS.md)

---
*Research completed: 2026-05-08*
*Ready for roadmap: yes*
