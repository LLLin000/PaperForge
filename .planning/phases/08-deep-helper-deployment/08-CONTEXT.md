# Phase 8: Deep Helper Deployment And Sandbox Regression Gate - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Automate the manual sandbox audit into a deterministic release gate. Fix `ld_deep.py` so it runs from the deployed Vault location without manual `PYTHONPATH`. Create OCR-complete sandbox fixtures that produce `figure-map.json`, `chart-type-map.json`, and a `## 精读` scaffold. Provide one smoke command that starts from a clean sandbox and fails if any manual-audit regression reappears. Verify docs stay consistent with smoke-tested commands.

Out of scope: Real PaddleOCR API network calls in smoke tests, Fig./Tab. deep analysis content, restoring corrupted user data beyond `paperforge repair`.
</domain>

<decisions>
## Implementation Decisions

### ld_deep.py Importability (DEEP-04)
- **D-01:** Fix via `pip install -e .` in setup_wizard — ensure `paperforge_lite` package is always importable from the deployed `ld_deep.py` location. Self-bootstrap or wrapper scripts are not needed.
- **D-02:** The existing `paperforge paths --json` output fields (`ld_deep_script`, `worker_script`, `vault`) are already the canonical field names — docs must reference these.
- **D-03:** Doctor check (existing `run_doctor`) already validates `literature-qa skill directory exists` — extend to check `ld_deep.py` is importable via `python -c "import ld_deep"`.

### OCR-Complete Fixture (DEEP-06)
- **D-04:** Static fixture files committed to `tests/sandbox/ocr-complete/` — pre-generated `fulltext.md`, `meta.json` (with `ocr_status: done`), `figure-map.json`, `chart-type-map.json`. No fixture factory needed.
- **D-05:** The fixture directory structure mirrors a real OCR output: `<zotero_key>/fulltext.md`, `<zotero_key>/meta.json`, `<zotero_key>/figure-map.json`, `<zotero_key>/chart-type-map.json`.
- **D-06:** The `## 精读` scaffold is produced by running `ld_deep.py prepare` against the fixture — not via a separate generator.

### Smoke Test Structure (REG-01, REG-02)
- **D-07:** Extend existing `tests/test_smoke.py` with new tests — NOT a standalone script or separate regression file.
- **D-08:** New smoke test sequence covers: setup-equivalent layout → selection sync → index refresh → OCR preflight/dry-run → deep-reading queue → `ld_deep.py` importability → `ld_deep.py prepare` (against OCR-complete fixture) → doc command extraction + execution validation.
- **D-09:** Smoke assertions must check each REG-02 regression item: doctor env names (`PADDLEOCR_API_TOKEN`), per-domain JSON exports, worker path JSON output, BBT PDF path resolution, metadata fields in library-records, queue output readability, and deployed Agent importability.

### Doc Verification (REG-03)
- **D-10:** Smoke test extracts command strings from doc files (README.md, INSTALLATION.md, AGENTS.md, command/*.md) and validates they run successfully against the sandbox vault.
- **D-11:** Extraction targets: `paperforge` CLI commands, `python -m paperforge_lite` fallback commands, and `/LD-deep` / `ld_deep.py` commands.
- **D-12:** Doc command extraction is part of the smoke test — not a separate two-step process.

### Prepare Error Handling
- **D-13:** `prepare_deep_reading` rolls back on failure: if any step fails, all partial output from this prepare run is deleted.
- **D-14:** Steps: (1) figure-map.json, (2) chart-type-map.json, (3) scaffold insertion. If step N fails, delete output of steps 1..N-1.
- **D-15:** Rollback deletes only files written by this prepare run (figure-map.json, chart-type-map.json, scaffold content reverts to pre-prepare state of the formal note).

### the agent's Discretion
- Exact fixture content for `fulltext.md`, `figure-map.json`, `chart-type-map.json` — must be representative but not from real papers.
- How to extract commands from doc files in the smoke test (regex patterns, markdown parsing approach).
- Rollback implementation details (track written files in-memory vs delete by known paths).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — DEEP-04, DEEP-05, DEEP-06, REG-01, REG-02, REG-03 definitions (lines 40-48)

### CLI and Config (Phase 6 decisions)
- `paperforge_lite/cli.py` — lines 309-313: `ld_deep_script` output key
- `paperforge_lite/config.py` — lines 235-275: `paperforge_paths()` returns `ld_deep_script`
- `paperforge_lite/config.py` — lines 260-261: `ld_deep_script = skill_path / "literature-qa" / "scripts" / "ld_deep.py"`

### LD-deep Script
- `skills/literature-qa/scripts/ld_deep.py` — lines 14-35: imports from `paperforge_lite.config` (the importability issue)
- `skills/literature-qa/scripts/ld_deep.py` — lines 958-1140: `prepare_deep_reading()` function (writes figure-map, chart-type-map, scaffold)
- `skills/literature-qa/scripts/ld_deep.py` — lines 1213-1398: CLI dispatch for `queue`, `prepare`, `figure-map`, `chart-type-scan`

### Existing Smoke Tests
- `tests/test_smoke.py` — 389 lines: existing pytest smoke tests with `fixture_vault`
- `tests/test_ld_deep_config.py` — 133 lines: existing ld_deep importability test pattern
- `tests/sandbox/generate_sandbox.py` — 231 lines: sandbox generation script (reuse patterns for fixture layout)

### Sandbox Structure
- `tests/sandbox/00_TestVault/` — existing sandbox vault structure
- `tests/sandbox/exports/` — per-domain BBT export JSON files
- `tests/sandbox/TestZoteroData/storage/` — mock Zotero PDF storage

### Setup Wizard Deployment
- `setup_wizard.py` — lines 968-974: copies `ld_deep.py` to vault skill directory

### Prior Phase Decisions
- `.planning/phases/06-setup-cli-diagnostics-consistency/06-CONTEXT.md` — D-01: field name `ld_deep_script`, D-04: canonical env var `PADDLEOCR_API_TOKEN`, D-16: fallback `python -m paperforge_lite`

### Command Docs (to verify)
- `command/ld-deep.md` — must reference `ld_deep_script` field name
- `command/lp-ocr.md`
- `command/lp-status.md`
- `command/lp-selection-sync.md`
- `command/lp-index-refresh.md`
- `README.md` — quick start commands
- `docs/INSTALLATION.md` — install/configure commands
- `AGENTS.md` — command reference

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/test_smoke.py` `fixture_vault` fixture — creates minimal PaperForge vault in tmp_path, reusable for all Phase 8 tests
- `tests/test_ld_deep_config.py` — import pattern for `ld_deep.py` via `spec_from_file_location`, directly reusable
- `tests/sandbox/generate_sandbox.py` — generates sandbox vault, PDFs, export JSONs; reusable patterns for fixture layout
- `skills/literature-qa/scripts/ld_deep.py` `prepare_deep_reading()` — already implements the full scaffold chain (figure-map → chart-type-scan → scaffold)
- `pipeline/worker/scripts/literature_pipeline.py` `validate_ocr_meta()` — validate OCR completeness; could verify fixture fidelity

### Established Patterns
- Pytest with `fixture_vault(tmp_path)` for isolated test vaults
- Import-based ld_deep testing via `spec_from_file_location` (test_ld_deep_config.py lines 12-19)
- Per-domain exports in `tests/sandbox/exports/` with keys matching Zotero storage
- Doctor tiered diagnostics: L1 token, L2 URL, L3 schema, L4 live (extend importability check)

### Integration Points
- `setup_wizard.py:968-974` — ld_deep.py deployment path: `repo_root/skills/literature-qa/scripts/ld_deep.py` → `vault/.opencode/skills/literature-qa/scripts/ld_deep.py`
- `paperforge_lite/config.py:260-261` — `ld_deep_script` computed from `skill_dir + "literature-qa/scripts/ld_deep.py"`
- `tests/sandbox/00_TestVault/` — has deployed `ld_deep.py` already; the importability test should verify import from this location
- `pipeline/worker/scripts/literature_pipeline.py:3111-3118` — doctor's existing Agent script check (warn-only); should be upgraded to importability check

</code_context>

<specifics>
## Specific Ideas

- "pip install -e ." approach: setup_wizard already writes `.env` — add a step that runs `pip install -e <repo_root>` to make `paperforge_lite` globally importable
- Static fixture `fulltext.md` should contain realistic figure captions (e.g., "Figure 1: Biomechanical comparison...") so `figure-map` and `chart-type-scan` produce non-trivial output
- The smoke test doc extraction: parse markdown code blocks with `paperforge` or `python -m` or `ld_deep.py` prefixes

</specifics>

<deferred>
## Deferred Ideas

- Standalone regression test file (`test_regression.py`) — not needed; extend `test_smoke.py`
- Real PaddleOCR network smoke test — explicitly out of scope per ROADMAP; keep deterministic
- Fig./Tab. deep analysis content quality — Phase 8 only ensures scaffold structure exists, not content quality

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-deep-helper-deployment*
*Context gathered: 2026-04-24*
