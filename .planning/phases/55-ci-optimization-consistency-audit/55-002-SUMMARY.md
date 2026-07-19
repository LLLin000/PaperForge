---
phase: 55-ci-optimization-consistency-audit
plan: 002
type: execute
subsystem: ci
tags: [ci, github-actions, plasma-matrix, merge-gate]
dependency-graph:
  requires: [tests/audit/, tests/e2e/, tests/cli/, tests/journey/, paperforge/plugin/]
  provides: [L0-L5 merge gate, single-status branch protection check]
  affects: [.github/workflows/ci.yml, .github/workflows/ci-chaos.yml (unchanged)]
tech-stack:
  added:
    - dorny/paths-filter@v3 (path detection)
    - re-actors/alls-green@v1 (aggregator)
    - Plasma matrix: 3 OS x 3 Python for L1
  patterns:
    - Path-filtered triggers control which layers run per change type
    - L5 journey tests informational-only (not in merge gate)
    - `allowed-skips` in alls-green handles conditionally-skipped jobs
key-files:
  modified:
    - .github/workflows/ci.yml
decisions:
  - alls-green excludes journey-tests (L5 is informational, not a merge blocker)
  - `allowed-skips: version-check, plugin-tests` handles path-filtered skip scenarios
  - Chaos tests NOT in ci.yml (maintained in separate ci-chaos.yml)
  - L1 uses fail-fast: false to avoid one OS failure cancelling others
metrics:
  duration: ~10min
  completed: 2026-05-09
  jobs: 8
  matrix_combinations: 15 (L1:9 + L2:2 + L3:1 + L4:1 + L5:1 + changes:1 + gate:1)
---

# Phase 55 Plan 002: Plasma Matrix CI Pipeline

**One-liner:** Rewrote `.github/workflows/ci.yml` with 8-job plasma matrix pipeline (L0-L5 merge gate), dorny/paths-filter path detection, and re-actors/alls-green aggregator providing single-status check for branch protection.

## Tasks Completed

| Task | Name | Description |
|------|------|-------------|
| 1 | Rewrite ci.yml | Full plasma matrix CI with path-filtered triggers, L0-L5 layer structure, alls-green gate |
| 2 | Validate CI workflow | YAML syntax, structural validation, path filter verification |

## CI Pipeline Structure

| Job | Layer | Strategy | Runs When |
|-----|-------|----------|-----------|
| `changes` | Detection | dorny/paths-filter@v3 | Always |
| `version-check` | L0 | Python 3.11 | version or core changed |
| `unit-tests` | L1 | 3 OS x 3 Python | plugin-only? no → always runs for core |
| `cli-tests` | L2 | 2 Python x 1 OS | plugin-only? no → always runs for core |
| `plugin-tests` | L3 | Node 20 | plugin or core changed |
| `e2e-tests` | L4 | Python 3.11 (E2E + Audit) | plugin-only? no → always runs for core |
| `journey-tests` | L5 | Python 3.11 (informational) | any file changed |
| `alls-green` | Gate | re-actors/alls-green@v1 | always() |

## Path Filters

| Filter | Paths |
|--------|-------|
| version | paperforge/__init__.py, plugin/manifest.json, plugin/versions.json, CHANGELOG.md, pyproject.toml |
| plugin | paperforge/plugin/**, plugin/package.json |
| ocr | paperforge/worker/ocr.py, paperforge/ocr_diagnostics.py |
| core | paperforge/**, tests/**, fixtures/**, pyproject.toml, scripts/** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] YAML indentation for python -c inline script**
- **Found during:** Task 2 validation
- **Issue:** Multiline bash string with embedded Python `-c "..."` had misaligned indentation confusing YAML block scalar parser
- **Fix:** Collapsed to single-line Python command (avoiding YAML literal block scalar indentation issues)

**2. [Rule 3 - Blocking] YAML `on` keyword interpreted as boolean**
- **Found during:** Task 2 validation
- **Issue:** Standard YAML parsers interpret `on:` as a boolean key (true/false), not a string key
- **Fix:** Quoted as `"on"` — GitHub Actions accepts both forms

## Verification

- [x] YAML syntax valid (verified via `yaml.safe_load`)
- [x] All 8 required jobs exist
- [x] L1 matrix: 3 OS (ubuntu, windows, macos) x 3 Python (3.10, 3.11, 3.12)
- [x] L2 matrix: 2 Python (3.10, 3.12) x 1 OS (ubuntu)
- [x] L3: Node 20 (`setup-node@v4`, `node-version: 20`)
- [x] L4: E2E + Audit tests wired correctly
- [x] L5: Journey tests NOT in alls-green gate
- [x] alls-green: re-actors/alls-green@v1 with correct needs and allowed-skips
- [x] Chaos tests NOT included (kept in separate ci-chaos.yml)
- [x] Path filters match project file structure
- [x] Paths-ignore: `**.md` and `docs/**` at trigger level
