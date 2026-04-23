# Phase 5: Release Verification - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 5 proves the release is robust enough to ship and maintain. It delivers:
1. Unit tests covering config resolver, path resolver, OCR state machine, Base rendering, and launcher commands
2. A smoke test running on a fixture vault without touching the real vault
3. Documentation consistency validation across docs, setup wizard, command files, and AGENTS guide
4. Formal defect audit from DEFECTS.md with each item marked fixed/deferred/superseded

v2 requirements (INT-01, INT-02, INT-03, UX-01, UX-02, UX-03) are explicitly deferred to a future backlog — not in scope for Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Test Coverage Scope (REL-01)

- **Coverage standard:** Key modules have tests covering critical paths; no mandatory line/branch coverage percentage
- **Must-cover modules:**
  - `paperforge_lite/config.py` — resolve_vault(), load_vault_config(), paperforge_paths(), load_simple_env()
  - `paperforge_lite/ocr_diagnostics.py` — L1-L4 diagnostic levels
  - `paperforge_lite/pdf_resolver.py` — absolute, vault-relative, junction, storage-relative paths
  - `literature_pipeline.py` Base generation — build_base_views(), substitute_config_placeholders(), 8-view structure
  - `paperforge_lite/cli.py` — all command dispatches (status, selection-sync, index-refresh, ocr, ocr doctor, deep-reading)
- **Coverage gaps to report:** resolve_vault() fallback on missing paperforge.json, load_simple_env() exception handling, Chinese path handling in placeholder substitution

### Smoke Test Design (REL-02)

- **形式:** `tests/smoke_test.py` — standalone Python script, runnable outside pytest
- **Command:** `python tests/smoke_test.py --vault /path/to/fixture`
- **流程步骤 (按顺序):**
  1. `paperforge doctor` — validate_setup category check (no live OCR)
  2. `paperforge selection-sync` — generates library-records from fixture BBT JSON
  3. `paperforge index-refresh` — generates formal notes from fixture library-records
  4. `paperforge ocr doctor --dry-run` — L1-L3 diagnostics, no L4 (avoids live OCR)
  5. `paperforge ocr run --dry-run` — preflight check only, no job submission
  6. `paperforge deep-reading` — displays queue state (ready/blocked/waiting)
- **Fixture vault contents:**
  - Better BibTeX JSON fixture (3 papers: 2 with PDFs, 1 without)
  - Dummy PDF files (2 readable, 1 unreadable)
  - `paperforge.json` with default paths
  - `.env` with dummy token (passes L1-L2, fails L3-L4)
- **OCR job submission guard:** `paperforge ocr run` refuses to submit jobs in fixture vault unless `--force` flag is passed

### Documentation Consistency (REL-03)

- **AGENTS.md consistency check:**
  - All `<system_dir>` placeholders replaced with paperforge CLI commands
  - Legacy Python path form preserved as backup option
  - `/LD-deep` command format matches literature-qa skill
- **Doc cross-check scope:**
  - AGENTS.md ↔ cli.py (command existence and format match)
  - README.md ↔ INSTALLATION.md (installation steps match)
  - command/*.md ↔ cli.py (each command doc has a corresponding subparser)
  - docs/README.md ↔ setup_wizard.py (setup steps match)
- **Existing tests to extend:**
  - `test_command_docs.py` already checks command doc ↔ CLI consistency — extend to cover AGENTS.md
  - Add `test_doc_installation_consistency.py` to check README vs INSTALLATION.md

### Defect Audit

- **Audit scope:** All 16 defects listed in DEFECTS.md
- **Resolution categories:**
  - `FIXED (Phase N)` — Phase 1-4 implementation resolves this defect
  - `DEFERRED → v2` — Belongs to v2 requirements (INT-01, INT-02, INT-03, UX-01, UX-02, UX-03)
  - `SUPERSEDED` — Problem resolved by other means (not by explicit Phase fix)
- **Output:** Update DEFECTS.md with status annotations inline
- **v2 requirements handling:**
  - Create `.planning/backlog.md` listing all v2 requirements with defer rationale
  - ROADMAP.md Phase 5 Implementation Notes adds: "v2 requirements moved to backlog"
- **Audit by:** Phase 5 researcher comparing DEFECTS.md against Phase 1-4 plan files and implementation code

### v2 Requirements Backlog

| ID     | Requirement               | Defer Rationale |
|--------|---------------------------|-----------------|
| INT-01 | OCR provider plugin system | PaddleOCR must be stable first (v1 goal) |
| INT-02 | BBT settings auto-detection | Requires BBT plugin API research |
| INT-03 | Scheduled worker automation | Conflicts with Lite two-layer design |
| UX-01  | Setup wizard repair mode   | Current install flow sufficient |
| UX-02  | Base file import parameterization | base-refresh covers this |
| UX-03  | Pipeline health dashboard  | Not core to v1 value proposition |

### the agent's Discretion

- Exact smoke test exit code schema (0 = all pass, non-zero = first failure step)
- smoke_test.py verbose output format (plain text vs structured)
- Coverage gap acceptance threshold (how many gaps block plan vs how many are noted)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Planning
- `.planning/PROJECT.md` — project purpose, constraints, and known issues
- `.planning/REQUIREMENTS.md` — REL-01, REL-02, REL-03 requirements and traceability
- `.planning/ROADMAP.md` — Phase 5 goal and success criteria
- `.planning/research/DEFECTS.md` — 16 high-risk defects to audit

### Prior Phase Contexts
- `.planning/phases/01-config-and-command-foundation/01-CONTEXT.md` — Phase 1 decisions (config hierarchy, CLI surface)
- `.planning/phases/02-paddleocr-and-pdf-path-hardening/CONTEXT.md` — Phase 2 decisions (OCR state machine, doctor L1-L4)
- `.planning/phases/03-obsidian-bases-config-aware/03-CONTEXT.md` — Phase 3 decisions (8-view Base, placeholders)
- `.planning/phases/04-onboarding-validation/04-CONTEXT.md` — Phase 4 decisions (doctor subcommands, AGENTS update)

### Implementation Files
- `paperforge_lite/config.py` — shared resolver (Phase 1)
- `paperforge_lite/ocr_diagnostics.py` — L1-L4 doctor (Phase 2)
- `paperforge_lite/pdf_resolver.py` — PDF path resolution (Phase 2)
- `pipeline/worker/scripts/literature_pipeline.py` — Base generation, workers (Phase 3)
- `paperforge_lite/cli.py` — command dispatch (Phase 1)
- `tests/` — 126 existing tests across 15 test files

</canonical_refs>

<codebase_context>
## Existing Code Insights

### Reusable Assets
- `tests/fixtures/blank.pdf` — existing dummy PDF for OCR tests
- `test_ocr_doctor.py` — existing L1-L4 doctor tests (can inform smoke test fixture approach)
- `test_base_preservation.py` — existing Base file handling tests

### Established Patterns
- Config resolution uses `**shared` dict merge in `pipeline_paths()`
- CLI dispatch uses ArgumentParser with subparsers
- OCR state machine uses 6 states: pending/processing/done/blocked/error/nopdf
- Base generation uses 8-view structure with `${SCREAMING_SNAKE_CASE}` placeholders

### Integration Points
- `paperforge` CLI entrypoint: `paperforge_lite/__main__.py` → `cli.py`
- Worker dispatch: `literature_pipeline.py` imported and called by `cli.py`
- Smoke test will call `paperforge` CLI commands as subprocess or via `main()` directly

</codebase_context>

<specifics>
## Specific Ideas

- Smoke test fixture vault should be under `tests/fixtures/vault/` with its own paperforge.json
- smoke_test.py should print step-by-step progress with clear pass/fail markers
- DEFECTS.md update should include phase reference for each FIXED item (e.g., "PaddleOCR auth preflight → FIXED (Phase 2)")
- v2 requirements deferral rationale should be one line each, consistent with ROADMAP.md style

</specifics>

<deferred>
## Deferred Ideas

### v2 Requirements (moved to backlog)
- INT-01: OCR provider plugin system → PaddleOCR must stabilize first
- INT-02: BBT settings auto-detection → requires BBT plugin API research
- INT-03: Scheduled worker automation → conflicts with Lite two-layer design
- UX-01: Setup wizard repair mode → current install flow sufficient
- UX-02: Base file import parameterization → base-refresh covers this
- UX-03: Pipeline health dashboard → not core to v1 value

### Reviewed Todos (not applicable for Phase 5)
- None — Phase 5 is release verification with no new capability scope

</deferred>

---

*Phase: 05-release-verification*
*Context gathered: 2026-04-23*