# Roadmap: PaperForge Lite v1.1 Sandbox Onboarding Hardening

**Created:** 2026-04-23  
**Scope:** Fix every issue found by the README-driven sandbox first-time-user simulation.

## Phase 6: Setup, CLI, And Diagnostics Consistency

**Goal:** Make the documented setup path, installed CLI, doctor command, and Agent command docs agree on the same paths, env names, and fallback commands.

**Requirements:** SETUP-01, SETUP-02, SETUP-03, SETUP-04, SETUP-05, DIAG-01, DIAG-02, DIAG-03, DIAG-04

**Success Criteria:**
1. Running `python setup_wizard.py --vault <sandbox-vault>` gives immediate visible progress or a clear TUI message, and the provided vault path is prefilled or otherwise honored.
2. `paperforge paths --json` returns existing deployed paths for worker and `/LD-deep` helper scripts.
3. `paperforge doctor` passes the sandbox's per-domain exports and checks the same PaddleOCR env variable written by setup.
4. README, INSTALLATION.md, AGENTS.md, and `command/LD-deep.md` use field names and fallback commands that exist.

**Implementation Notes:**
- Prefer one resolver contract for both human-readable paths and JSON output.
- Keep `python -m paperforge_lite ...` documented as the fallback when `paperforge` is not registered.
- Doctor should validate all `*.json` exports under the configured exports directory, not only `library.json`.

## Phase 7: Zotero PDF, Metadata, And State Repair

**Goal:** Make sandbox BBT attachment paths resolve correctly and keep OCR/deep-reading state consistent across records, notes, and meta files.

**Requirements:** ZPATH-01, ZPATH-02, ZPATH-03, META-01, META-02, STATE-01, STATE-02, STATE-03, STATE-04

**Success Criteria:**
1. `selection-sync` resolves `KEY/KEY.pdf`, `storage:KEY/file.pdf`, `storage/KEY/file.pdf`, absolute paths, vault-relative paths, and configured Zotero junction paths.
2. Generated library-records for sandbox PDFs contain readable `pdf_path`, non-empty `first_author`, and non-empty `journal`.
3. OCR worker does not leave readable-PDF records in the contradictory `has_pdf: true` plus `ocr_status: nopdf` state.
4. `deep-reading --verbose` surfaces ready/waiting/blocked details directly enough for a first-time user to know the next command.

**Implementation Notes:**
- Fix path resolution before changing OCR state transitions; most downstream contradictions start with unresolved PDFs.
- Use normalized export row fields consistently after `load_export_rows`.
- Add tests around both library-record frontmatter and formal note frontmatter, not only `formal-library.json`.

## Phase 8: Deep Helper Deployment And Sandbox Regression Gate

**Goal:** Turn the manual sandbox audit into an automated release gate that covers deployed Agent helper importability and `/LD-deep prepare`.

**Requirements:** DEEP-04, DEEP-05, DEEP-06, REG-01, REG-02, REG-03

**Success Criteria:**
1. The deployed `ld_deep.py` in the sandbox Vault can run `queue` and `prepare` without manual `PYTHONPATH`.
2. A sandbox OCR-complete fixture produces `figure-map.json`, `chart-type-map.json`, and a `## 🔍 精读` scaffold.
3. One smoke command starts from a clean sandbox and fails if any manual-audit regression reappears.
4. Docs are verified against the same commands used by the smoke test.

**Implementation Notes:**
- The smoke test should be deterministic and should not call the live PaddleOCR API.
- Reuse `tests/sandbox/generate_sandbox.py` or convert it into a pytest fixture factory.
- Keep generated sandbox Vault output ignored by git; only commit fixtures, tests, and docs.

## Phase Summary

| # | Phase | Goal | Requirements | Status |
|---|-------|------|--------------|--------|
| 6 | Setup, CLI, And Diagnostics Consistency | Align setup/docs/doctor/path contracts | 9 | 2 plans |
| 7 | Zotero PDF, Metadata, And State Repair | Resolve PDFs and converge status fields | 9 | Done |
| 8 | Deep Helper Deployment And Sandbox Regression Gate | Automate the manual sandbox audit | 6 | Done |

---
*Roadmap created: 2026-04-23 for milestone v1.1*
