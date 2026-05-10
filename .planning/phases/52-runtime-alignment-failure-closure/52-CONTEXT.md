# Phase 52: Golden Datasets & CLI Contracts - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning
**Mode:** Infrastructure/testing phase — minimal context per ROADMAP

<domain>
## Phase Boundary

Build the shared `fixtures/` golden dataset (Zotero JSON, PDF samples, mock OCR responses, expected snapshots) and CLI contract tests (L2) with subprocess invoker and shape-specific snapshot assertions.

**Requirements:** FIX-01, FIX-02, FIX-03, FIX-04, FIX-05, CLI-01, CLI-02, CLI-03

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — infrastructure/testing phase with clear ROADMAP success criteria. Use standard pytest fixture patterns, JSON schema conventions, and the existing test infrastructure.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Existing `tests/conftest.py` patterns for vault fixtures
- `tests/sandbox/test_vault/fixtures/` — existing dummy data
- `paperforge/cli.py` — all 7 CLI commands
- `paperforge/config.py` — path resolution
- Research outputs in `.planning/research/SUMMARY.md`

### Established Patterns
- pytest fixtures in `tests/conftest.py`
- `tmp_path` for temporary directories
- JSON output in CLI commands via `--json` flag

### Integration Points
- `fixtures/` at repo root — new central fixture directory
- `tests/cli/` — new CLI contract test directory
- `pyproject.toml` — add pytest-snapshot, responses, pytest-timeout, pytest-mock dependencies

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond ROADMAP success criteria. Standard golden dataset and CLI contract testing patterns apply.

</specifics>

<deferred>
## Deferred Ideas

- Real PaddleOCR API response capture (deferred to when real API is available for fixture generation)
</deferred>
