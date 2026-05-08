# Phase 54 Plan 003: CI Chaos Workflow — Summary

**Plan:** 54-003
**Phase:** 54-dashboard-workflow-closure
**Subsystem:** CI/CD — Chaos Test Schedule
**Tags:** github-actions, ci, chaos, workflow
**Date:** 2026-05-09

## Objective

Create the scheduled chaos CI workflow (`ci-chaos.yml`) that runs Level 6 destructive tests weekly and on manual trigger.

## Results

- `.github/workflows/ci-chaos.yml` created with:
  - Weekly schedule: Sunday 06:00 UTC (`cron: "0 6 * * 0"`)
  - Manual trigger via `workflow_dispatch`
  - Runs on `ubuntu-latest` with Python 3.11
  - Runs `pytest tests/chaos/ -m chaos -v --tb=long --timeout=120`
  - Uploads test results as artifact even on failure
- `ci.yml` is NOT modified — chaos tests are explicitly excluded from PR/merge gate.

## Key Decisions

- Single OS (ubuntu-latest) — chaos tests test error handling, not platform compatibility.
- Single Python 3.11 — latest stable.
- `--tb=long` for visible failure details in CI logs.
- `--junit-xml` artifact upload even on failure (`if: always()`).
- 120s timeout per test — subprocess calls can hang on error paths.
- No path filtering — chaos tests are small/fast; always run on schedule/manual.

## Verification

```bash
# YAML content verification
content = open(".github/workflows/ci-chaos.yml").read()
assert "schedule:" in content
assert "workflow_dispatch:" in content
assert "tests/chaos" in content
assert "cron:" in content
```

## Artifacts

| File | Status |
|------|--------|
| `.github/workflows/ci-chaos.yml` | Created (weekly schedule + manual dispatch) |
