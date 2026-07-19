# Phase 53: Plugin Tests & Temp Vault E2E - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning
**Mode:** Infrastructure/testing phase — minimal context per ROADMAP

<domain>
## Phase Boundary

Build plugin-backend integration tests (L3) with Vitest + obsidian-test-mocks, covering plugin runtime helpers, error classification, and command dispatch. Build full temp vault end-to-end tests (L4) covering sync, OCR, status, doctor, and repair workflows with mock PaddleOCR backend.

**Requirements:** PLUG-01, PLUG-02, PLUG-03, E2E-01, E2E-02, E2E-03, E2E-04, E2E-05, CI-04

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices at the agent's discretion — testing/infrastructure phase. Use standard Vitest patterns, obsidian-test-mocks documentation, and existing temp vault fixture patterns from Phase 52.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `paperforge/plugin/main.js` — Obsidian plugin with runtime helpers
- `paperforge/plugin/src/runtime.js` — Python executable resolution, version checks
- `paperforge/plugin/src/errors.js` — error classification
- `paperforge/plugin/src/commands.js` — command dispatch
- Phase 52 golden datasets in `fixtures/` — shared across E2E tests
- Phase 52 vault builder (`fixtures/vault_builder.py`)
- Phase 52 mock OCR backend (`fixtures/ocr/mock_ocr_backend.py`)

### Established Patterns
- pytest fixtures with `tmp_path` for temp vault creation
- Subprocess isolation via `sys.executable -m paperforge`
- CLI --json contract tests from Phase 52

### Integration Points
- `tests/plugin/` — new directory for Vitest tests
- `tests/e2e/` — new directory for temp vault E2E tests
- `paperforge/plugin/package.json` — add Vitest and obsidian-test-mocks
- `paperforge/plugin/vitest.config.ts` — new Vitest config
- CI: Node 20 runner for plugin tests

</code_context>

<specifics>
## Specific Ideas

- Plugin tests should test extracted modules (runtime.js, errors.js, commands.js) not require full Obsidian app
- E2E tests should use the fixture hierarchy from Phase 52
- Mock OCR must be used for all E2E tests — no real API calls
- E2E tests should clean up temp vaults reliably on Windows (handle file locking)

</specifics>

<deferred>
## Deferred Ideas

None
</deferred>
