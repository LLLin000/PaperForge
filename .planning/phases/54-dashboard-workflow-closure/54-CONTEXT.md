# Phase 54: User Journey & Chaos Tests - Context

**Gathered:** 2026-05-08
**Status:** Ready for planning
**Mode:** Infrastructure/testing phase — minimal context per ROADMAP

<domain>
## Phase Boundary

Document and implement user journey tests (L5) against verifiable UX contracts, plus destructive/abnormal scenario tests (L6) with safety contracts and CI scheduling.

**Requirements:** JNY-01, JNY-02, JNY-03, CHAOS-01, CHAOS-02, CHAOS-03, CHAOS-04, CI-05

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices at the agent's discretion — testing phase with clear ROADMAP success criteria. UX contracts should be concrete step sequences, not prose. Chaos tests must enforce isolation guards (assert tmp_path).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `fixtures/vault_builder.py` — temp vault creation
- `fixtures/ocr/mock_ocr_backend.py` — deterministic OCR mocking
- `tests/e2e/` — temp vault E2E infrastructure (Phase 53)
- `tests/cli/` — CLI contract infrastructure (Phase 52)

### Established Patterns
- pytest fixtures with tmp_path
- VaultBuilder with completeness levels
- Windows-safe teardown with retry

</code_context>

<specifics>
## Specific Ideas

- Journey tests should reuse e2e_cli_invoker and vault_builder
- Chaos tests must have isolation assertion `assert "tmp" in str(vault)` — never run on real vaults
- UX_CONTRACT.md should be in docs/ for human readers
- CHAOS_MATRIX.md should be in tests/chaos/scenarios/ for CI reference

</specifics>

<deferred>
## Deferred Ideas

- Docker isolation for chaos tests (Phase 55 may need this for CI)
</deferred>
