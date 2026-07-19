# Phase 55: CI Optimization & Consistency Audit - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning
**Mode:** Infrastructure/CI phase — minimal context per ROADMAP

<domain>
## Phase Boundary

Harden CI with plasma matrix strategy, full L0-L4 merge gate, path-filtered triggers, and cross-layer consistency audit that validates L1 mocks against L4 ground truth.

**Requirements:** CI-02, CI-03

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices at the agent's discretion — CI optimization phase with clear ROADMAP success criteria. Existing `ci.yml` from Phases 52-53 provides the base. Optimize, don't rewrite.

</decisions>

<code_context>
## Existing Code Insights

### Existing CI files
- `.github/workflows/ci.yml` — current CI (from Phases 52-53)
- `.github/workflows/ci-chaos.yml` — chaos workflow (Phase 54)

### Test markers
- `unit`, `cli`, `e2e`, `journey`, `chaos`, `slow` — defined in pyproject.toml

### Test directories
- `tests/unit/` — unit tests (Phase 51)
- `tests/cli/` — CLI contract tests (Phase 52)
- `tests/e2e/` — E2E tests (Phase 53)
- `tests/plugin/` (in paperforge/plugin/) — plugin tests (Phase 53)
- `tests/journey/` — journey tests (Phase 54)
- `tests/chaos/` — chaos tests (Phase 54)

</code_context>

<specifics>
## Specific Ideas

- Plasma matrix: L1 on 3 OS x 3 Python; L2-L5 on narrower configs
- Path-filtered triggers: changes to ocr.py trigger L1+L2+L4; changes to main.js trigger L3 only
- Consistency audit: validate L1 mock expectations against L4 real pipeline output
- alls-green check for branch protection
- Exclude chaos from `ci.yml` (already done via separate workflow)

</specifics>

<deferred>
## Deferred Ideas

None
</deferred>
