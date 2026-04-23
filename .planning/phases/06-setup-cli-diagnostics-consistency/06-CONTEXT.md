# Phase 6: Setup, CLI, And Diagnostics Consistency - Context

**Gathered:** 2026-04-23 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 6 fixes inconsistencies between setup wizard, CLI doctor commands, and Agent command docs. It makes the documented setup path, installed CLI, doctor command, and `/LD-deep` docs agree on the same paths, env names, and fallback commands.

Scope:
- Setup wizard `--vault` prefilled and visible progress (SETUP-01, SETUP-02)
- Fallback command when `paperforge` not registered (SETUP-03)
- `paperforge paths --json` returns accurate deployed paths (SETUP-04)
- Agent command docs use same JSON field names as CLI (SETUP-05)
- Doctor validates per-domain exports, not only library.json (DIAG-01)
- PaddleOCR env var name is consistent across setup/worker/doctor (DIAG-02)
- Doctor reports worker script path via same resolver contract (DIAG-03)
- Doctor distinguishes HTTP 405 endpoint-method mismatch from bad URL (DIAG-04)

Out of scope: Zotero PDF path resolution (Phase 7), deep helper deployment (Phase 8)
</domain>

<decisions>
## Implementation Decisions

### Field Names: JSON Output vs Agent Command Docs

- **D-01:** `paperforge paths --json` outputs field names: `vault`, `worker_script`, `ld_deep_script` (confirmed via `cli.py` line 284)
- **D-02:** `command/ld-deep.md` line 170 and 194 must use `ld_deep_script` instead of the non-existent `literature_script`
- **D-03:** `command/lp-ocr.md` line 17 and `command/lp-status.md` line 17 correctly use `worker_script` field name

### PaddleOCR Env Variable Naming

- **D-04:** Canonical env var name: `PADDLEOCR_API_TOKEN` (setup_wizard.py line 1016 writes this name)
- **D-05:** `ocr_diagnostics.py` and `literature_pipeline.py run_doctor` must both read `PADDLEOCR_API_TOKEN`
- **D-06:** Any discrepancy between what setup writes and what worker/doctor reads must be resolved to use `PADDLEOCR_API_TOKEN` consistently

### Doctor Export Validation (DIAG-01)

- **D-07:** Doctor validates all `*.json` files under exports directory, not only `library.json`
- **D-08:** Per-domain exports (e.g., ` orthopedic.json`, `sports-medicine.json`) must not trigger false "missing library.json" errors
- **D-09:** `run_doctor` in `literature_pipeline.py` line ~2910 must be updated to iterate `exports_dir.glob("*.json")`

### HTTP 405 Handling in Doctor (DIAG-04)

- **D-10:** Doctor L2 check must distinguish HTTP 405 "Method Not Allowed" from other errors
- **D-11:** When 405 is detected, message should explain: "Endpoint supports GET only, but OCR requires POST" (or similar)
- **D-12:** Doctor should still pass if the configured URL has correct shape but wrong method, providing actionable fix suggestion

### Setup Wizard Vault Prefill (SETUP-01, SETUP-02)

- **D-13:** `VaultStep` Input widget must be pre-filled with the `--vault` argument value passed to wizard
- **D-14:** `SetupWizardApp.__init__` must pass `vault` to `VaultStep` so Input `value` attribute can be set
- **D-15:** ProgressBar exists and advances on step transitions — "stall" feeling may be from terminal size/display issues, not missing progress

### Fallback Command Documentation (SETUP-03)

- **D-16:** `python -m paperforge_lite` is the documented fallback when `paperforge` not registered
- **D-17:** AGENTS.md, INSTALLATION.md, and command docs must mention this fallback explicitly

### Doctor Worker Script Path (DIAG-03)

- **D-18:** Doctor reports worker script path via same `paperforge_paths()` resolver contract used by runtime commands
- **D-19:** `paperforge paths --json` `worker_script` key must return a path that actually exists when PaperForge is properly deployed

### the agent's Discretion

- Exact error message wording for 405 distinction (D-11)
- ProgressBar visual rendering approach if stall persists after D-13/D-14
- How to handle case where exports dir has zero JSON files

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CLI and Config
- `paperforge_lite/cli.py` — lines 276-293: `_cmd_paths` output keys, `output_keys = {"vault", "worker_script", "ld_deep_script"}`
- `paperforge_lite/config.py` — lines 208-276: `paperforge_paths()` returns all path inventory keys
- `paperforge_lite/ocr_diagnostics.py` — lines 28: env var name read (`PADDLEOCR_API_TOKEN`), lines 44-77: L2 check

### Setup and Deployment
- `setup_wizard.py` — lines 486-535: `VaultStep` Input widget (needs vault prefilled), lines 1016: env var written as `PADDLEOCR_API_TOKEN`
- `pipeline/worker/scripts/literature_pipeline.py` — line ~2910: `run_doctor` export validation (single file check), line ~2933: env var name used

### Command Docs (must match JSON field names)
- `command/ld-deep.md` — lines 170, 194: uses `literature_script` (WRONG — must change to `ld_deep_script`)
- `command/lp-ocr.md` — line 17: uses `worker_script` (correct)
- `command/lp-status.md` — line 17: uses `worker_script` (correct)

### User-Facing Docs
- `AGENTS.md` — user-facing command reference, must mention fallback
- `docs/INSTALLATION.md` — installation steps, must mention fallback
- `README.md` — quick start guide, consistency with other docs

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `paperforge_lite/config.py` `paperforge_paths()` already returns full path inventory — reuse for doctor reporting
- `ocr_diagnostics.py` L1-L4 tiered structure — extend L2 with 405-specific handling
- ProgressBar widget in setup_wizard.py — already exists, just needs vault prefilled

### Established Patterns
- Config precedence: explicit > env > JSON nested > JSON top-level > defaults
- Doctor tiered diagnostics: L1 token, L2 URL, L3 schema, L4 live
- `paperforge paths --json` output_keys pattern for filtering

### Integration Points
- `run_doctor` in `literature_pipeline.py` must be updated to loop over `*.json` exports
- `VaultStep` needs vault passed from `SetupWizardApp.__init__`
- `command/ld-deep.md` must be updated to use correct field names

</code_context>

<specifics>
## Specific Ideas

- HTTP 405 error message: "URL returned 405 Method Not Allowed — PaddleOCR endpoint may require GET for probing but POST for OCR jobs. Check if your API endpoint supports both methods."
- When no JSON exports exist: doctor should warn but not fail (user may be before first export)
- `--vault` prefilled: `VaultStep` receives vault via app state, Input widget value set from app.vault

</specifics>

<deferred>
## Deferred Ideas

None — Phase 6 scope stayed focused on setup/CLI/docs consistency

</deferred>

---

*Phase: 06-setup-cli-diagnostics-consistency*
*Context gathered: 2026-04-23 (assumptions mode)*
