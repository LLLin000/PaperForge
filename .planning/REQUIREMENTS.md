# Requirements: PaperForge Lite v1.1 Sandbox Onboarding Hardening

**Defined:** 2026-04-23  
**Core Value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

## Milestone v1.1 Requirements

### Setup And Commands

- [x] **SETUP-01**: User can run `python setup_wizard.py --vault <vault>` and see an immediate, understandable setup UI or message instead of an unexplained terminal stall.
- [x] **SETUP-02**: User can rely on `--vault <vault>` being carried into the wizard flow without retyping the same path.
- [x] **SETUP-03**: User can continue with a documented fallback command when the global `paperforge` executable is not registered.
- [x] **SETUP-04**: User can inspect `paperforge paths --json` and receive installed worker and Agent script paths that actually exist.
- [x] **SETUP-05**: Agent command docs use the same JSON field names emitted by `paperforge paths --json`.

### Diagnostics

- [x] **DIAG-01**: User can run `paperforge doctor` against per-domain Better BibTeX exports without being incorrectly blocked for missing `library.json`.
- [x] **DIAG-02**: User can configure PaddleOCR once with the env variable name that setup writes and workers read.
- [x] **DIAG-03**: Doctor reports the deployed worker script path according to the same resolver contract used by runtime commands.
- [x] **DIAG-04**: OCR doctor distinguishes an expected endpoint-method mismatch from a bad user URL when checking the configured PaddleOCR job endpoint.

### Zotero Paths And Metadata

- [~] **ZPATH-01**: User can sync a BBT attachment path shaped like `KEY/KEY.pdf` when the file exists under the configured Zotero `storage/KEY/` directory.
- [~] **ZPATH-02**: User can sync common `storage:KEY/file.pdf` and `storage/KEY/file.pdf` attachment forms.
- [~] **ZPATH-03**: User sees library-record `pdf_path` populated only with a readable resolved PDF path or an explicit actionable missing-PDF status.
- [x] **META-01**: User sees `first_author` populated in generated library-records from normalized export metadata.
- [x] **META-02**: User sees `journal` populated in generated library-records from normalized export metadata.

### State And Queue Consistency

- [x] **STATE-01**: User can run `selection-sync`, `index-refresh`, and `ocr run` without records simultaneously saying `has_pdf: true` and `ocr_status: nopdf` when the PDF is readable.
- [x] **STATE-02**: User sees formal note OCR status synchronized with validated OCR `meta.json` status after worker refresh.
- [x] **STATE-03**: User sees `paperforge deep-reading --verbose` print the ready/waiting/blocked queue summary directly or print the report path clearly.
- [x] **STATE-04**: User can tell from command output which record needs OCR, which one is blocked, and which one is ready for `/LD-deep`.

### Deep Reading Helpers

- [x] **DEEP-04**: User can run the deployed `ld_deep.py` helper from the Vault installation without manually setting `PYTHONPATH`.
- [x] **DEEP-05**: User can run `/LD-deep queue` documentation examples using paths and field names that exist.
- [x] **DEEP-06**: User can prepare a sandbox OCR-complete paper and get `figure-map.json`, `chart-type-map.json`, and a `## 🔍 精读` scaffold in the formal note.

### Regression Coverage

- [x] **REG-01**: Maintainer can run one sandbox smoke test that starts from a clean `tests/sandbox/00_TestVault` and covers setup-equivalent layout, selection sync, index refresh, OCR preflight/dry-run, deep-reading queue, and `ld_deep.py prepare`.
- [x] **REG-02**: Smoke assertions cover the exact regressions from the manual audit: doctor env names, per-domain JSON, worker path JSON, BBT PDF path resolution, metadata fields, queue output, and deployed Agent importability.
- [x] **REG-03**: README, INSTALLATION.md, AGENTS.md, and command files stay consistent with the smoke-tested commands.

## Future Requirements

### Integrations

- **INT-01**: User can choose OCR providers beyond PaddleOCR.
- **INT-02**: PaperForge can detect Better BibTeX export settings directly where possible.
- **INT-03**: Optional scheduled worker automation can run without opening an agent session.

### UX

- **UX-01**: Setup wizard can repair an existing installation.
- **UX-02**: Setup wizard can import existing production Base files and parameterize them.
- **UX-03**: A dashboard note can summarize current pipeline health.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automatic deep-reading generation from worker | Conflicts with Lite architecture and risks uncontrolled agent work |
| Replacing Zotero collections as the source of domains | Existing workflow depends on Zotero and Better BibTeX exports |
| Multi-user hosted backend | Not needed for local release reliability |
| Full provider plugin system in v1.1 | The current milestone fixes PaddleOCR path/env consistency first |
| Real PaddleOCR network smoke test in default CI | Sandbox regression should be deterministic; live provider checks remain opt-in |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SETUP-01 | Phase 6 | Complete |
| SETUP-02 | Phase 6 | Complete |
| SETUP-03 | Phase 6 | Complete |
| SETUP-04 | Phase 6 | Complete |
| SETUP-05 | Phase 6 | Complete |
| DIAG-01 | Phase 6 | Complete |
| DIAG-02 | Phase 6 | Complete |
| DIAG-03 | Phase 6 | Complete |
| DIAG-04 | Phase 6 | Complete |
| ZPATH-01 | Phase 7 | Partial |
| ZPATH-02 | Phase 7 | Partial |
| ZPATH-03 | Phase 7 | Partial |
| META-01 | Phase 7 | Complete |
| META-02 | Phase 7 | Complete |
| STATE-01 | Phase 7 | Complete |
| STATE-02 | Phase 7 | Complete |
| STATE-03 | Phase 7 | Complete |
| STATE-04 | Phase 7 | Complete |
| DEEP-04 | Phase 8 | Complete |
| DEEP-05 | Phase 8 | Complete |
| DEEP-06 | Phase 8 | Complete |
| REG-01 | Phase 8 | Complete |
| REG-02 | Phase 8 | Complete |
| REG-03 | Phase 8 | Complete |

**Coverage:**
- v1.1 requirements: 24 total
- Complete: 21
- Partial: 3 (ZPATH-01/02/03 — BBT bare path normalization deferred)
- Unmapped: 0

---
*Requirements defined: 2026-04-23 from sandbox first-time-user audit*
