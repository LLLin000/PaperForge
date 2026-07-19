# Phase 17: Dead Code Removal + Pre-Commit - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove dead code (unused imports, UPDATE_* constants, delegation wrappers), install automated pre-commit hooks (ruff + consistency audit), add ruff config to pyproject.toml, and improve OCR error messages with actionable context (library-record name). Last code phase before documentation/testing.

Requirements: CH-04, DX-01, DX-02, OBS-05

Out of scope:
- pre-commit hook installation instructions (DX-04 — Phase 18)
- pre-commit hook test coverage (TEST-01/TEST-02 — Phase 19)

</domain>

<decisions>
## Implementation Decisions

### Plan Structure
- **D-01:** Single plan covering all 4 requirements (CH-04, DX-01, DX-02, OBS-05). Dead code removal is mechanical with exact line numbers from REQUIREMENTS.md; pre-commit config is a single file; ruff config is a pyproject.toml section; OBS-05 is a targeted change to 2 error paths in ocr.py.

### consistency-audit Extension
- **D-02:** Add a new Check 5 (duplicate utility function detection) to existing `scripts/consistency_audit.py`. Scans all 7 worker modules for functions that are re-exported from `_utils.py` but still have local copies. If any local copy exists outside the re-export comment, the audit fails.
- **D-03:** The `.pre-commit-config.yaml` calls `scripts/consistency_audit.py` as a custom hook. No separate script.

### OBS-05 Scope
- **D-04:** Minimal change: add `zotero_key` (library-record name) to the error context passed to existing error handling paths in ocr.py's upload and poll loops. Reuse existing `classify_error()` function. No restructuring of the error message format.
- **D-05:** Error messages in meta.json get an additional `library_record` field containing the zotero_key for context. Existing `error` and `suggestion` fields remain unchanged.

### ruff Configuration
- **D-06:** DX-02 rules E, F, I, UP, B, SIM are standard and clear-cut. Add `[tool.ruff]` section to pyproject.toml targeting Python 3.10+. No additional rules beyond the spec.

### Dead Code Removal Scope
- **D-07:** Remove unused imports from all 7 worker modules and command modules (`csv`, `hashlib`, `shutil`, `subprocess`, `zipfile`, `ElementTree`, `fitz`, `PIL` where not used). Determine unused by running `ruff check` and removing flagged imports.
- **D-08:** Remove UPDATE_* constants from `status.py` lines 620-625 (duplicated in `update.py`).
- **D-09:** Replace delegation wrappers (`load_vault_config`, `pipeline_paths`) in worker modules with direct `from paperforge.config import ...`. The wrappers are thin delegation functions that add an unnecessary hop. Backward compatibility: public names are preserved in `paperforge.config` directly.

### the agent's Discretion
- Exact order of tasks within the single plan
- Whether to run `ruff check --fix` as part of the dead code task or as a separate pre-commit validation step
- Exact regex for duplicate-utility detection in Check 5
- Number of pre-commit hook files (one `.pre-commit-config.yaml` at root)

</decisions>

<canonical_refs>
## Canonical References

### Requirements (Phase 17 scope)
- `.planning/REQUIREMENTS.md` — CH-04 (dead code items with exact line numbers), DX-01 (pre-commit hooks list), DX-02 (ruff rules), OBS-05 (actionable error messages)

### Existing Code
- `scripts/consistency_audit.py` — Existing audit script, add Check 5 here (D-02)
- `pyproject.toml` — Add `[tool.ruff]` section, no `[tool.ruff.lint]` yet
- `paperforge/worker/*.py` — All 7 workers for dead import removal
- `paperforge/worker/ocr.py:1256-1269` — Upload error handling (add zotero_key context per D-05)
- `paperforge/worker/ocr.py:1171-1222` — Poll error handling (add zotero_key context per D-05)

### Patterns
- `.planning/phases/16-retry-progress-bars/16-CONTEXT.md` — Phase 16 context for module creation pattern
- `paperforge/worker/_retry.py` — Leaf module pattern (imports only from stdlib + paperforge.config)
- `paperforge/worker/_progress.py` — Leaf module pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/consistency_audit.py` already exists with 4 checks (old commands, paperforge_lite, dead links, command docs) and a clear pattern: `check_*()` function returning `(exit_code, violations)` tuple. Add Check 5 following same pattern.
- `pyproject.toml` has no `[tool.ruff]` section — fresh add.

### Established Patterns
- Pre-commit hooks follow `.pre-commit-config.yaml` at repo root (standard Python convention).
- Ruff rules are configured in `pyproject.toml` `[tool.ruff]` sections, not a separate `.ruff.toml`.
- Workers import from `paperforge.worker._utils` for shared utilities. Direct `paperforge.config` imports are already used by `_utils.py` and `logging_config.py`.

### Integration Points
- `.pre-commit-config.yaml` — new file at repo root (must NOT interfere with non-v1.4 users until explicit install)
- `pyproject.toml` — append `[tool.ruff]` section at end
- Each worker module — removed imports are scattered across the top import block of each file

</code_context>

<specifics>
## Specific Ideas

- "直接plan" — user wants efficiency, standard approaches for Phase 17
- "Less is more" for OBS-05 — minimal change, just add context key

</specifics>

<deferred>
## Deferred Ideas

- README.md legacy code snippet cleanup — Phase 18 (UX-02)
- pre-commit hook install instructions in CONTRIBUTING.md — Phase 18 (DX-04)

None — discussion stayed within phase scope

</deferred>

---

*Phase: 17-dead-code-precommit*
*Context gathered: 2026-04-27*
