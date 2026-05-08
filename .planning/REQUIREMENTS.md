# Requirements: PaperForge v2.0

**Defined:** 2026-05-08
**Core Value:** Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.

## v1 Requirements

Requirements for this release. Each maps to roadmap phases.

### Version Consistency (VC)

- [ ] **VC-01**: Version sync checker script validates Python `__version__`, plugin manifest.json, versions.json, CHANGELOG — all 6+ declarations are consistent before any test runs
- [ ] **VC-02**: CI version gate runs version check on every push

### Python Unit Tests (UNIT)

- [ ] **UNIT-01**: Config tests cover reading, env var override, defaults, legacy migration, all path fields
- [ ] **UNIT-02**: BBT parser tests cover all JSON variants — valid, empty, malformed, missing citationKey, missing title, missing DOI, empty attachments, storage: paths, absolute Windows paths, bare relative paths, CJK content, multiple PDFs, zero PDFs
- [ ] **UNIT-03**: PDF resolver tests cover Zotero data dir unset/wrong, storage path missing, CJK filenames, filenames with parentheses, OneDrive paths, moved PDFs, multi-attachment main/supplementary identification
- [ ] **UNIT-04**: OCR state machine tests cover pending → processing → done → failed transitions, retry/backoff, progress, auto_analyze_after_ocr, error recovery
- [ ] **UNIT-05**: Note generation tests cover frontmatter field correctness, template rendering, field migration, CJK-safe output
- [ ] **UNIT-06**: Base generation tests cover .base file structure, workflow-gate filters, config-aware paths, CJK-safe output
- [ ] **UNIT-07**: Index generation tests cover canonical index format, versioned envelope, atomic writes, incremental refresh, rebuild
- [ ] **UNIT-08**: Template checker tests cover asset state derivation (lifecycle/health/maturity/next_step), edge cases, null/incomplete inputs

### CLI Contract Tests (CLI)

- [ ] **CLI-01**: All 7 CLI commands (status, sync, ocr, doctor, repair, context, setup) return stable `--json` schema
- [ ] **CLI-02**: Error responses use standard JSON format with `ok`, `error_code`, `message`, `details`, `suggestions` fields
- [ ] **CLI-03**: pytest-snapshot integration with shape-specific assertions (not whole-file) for CLI output contracts

### Plugin-Backend Integration (PLUG)

- [ ] **PLUG-01**: Plugin runtime helpers testable via Vitest — resolvePythonExecutable, getPluginVersion, checkRuntimeVersion
- [ ] **PLUG-02**: Error classification covers all error patterns (Python missing, import failed, version mismatch, pip install failure, timeout)
- [ ] **PLUG-03**: Command dispatch tests cover buildRuntimeInstallCommand, parseRuntimeStatus, subprocess orchestration

### Temp Vault E2E (E2E)

- [ ] **E2E-01**: Temp vault creation fixture produces disposable Vault with config, directories, mock Zotero data
- [ ] **E2E-02**: Full sync workflow test — BBT JSON → formal notes → canonical index → Base views
- [ ] **E2E-03**: Full OCR workflow with mock PaddleOCR backend via HTTP interception (responses library)
- [ ] **E2E-04**: status/doctor/repair commands run correctly in temp vault with known state
- [ ] **E2E-05**: Multi-domain sync test verifies multiple collections sync correctly and independently

### User Journey Tests (JNY)

- [x] **JNY-01**: UX Contract document (docs/ux-contract.md) with verifiable rules for installation, sync, OCR, and dashboard
- [x] **JNY-02**: New user onboarding journey test — install → sync → OCR → analyze → deep-read
- [x] **JNY-03**: Daily workflow journey test — existing user adds paper, syncs, OCRs, reads

### Chaos / Destructive Tests (CHAOS)

- [x] **CHAOS-01**: Corrupted input tests — malformed JSON, corrupt PDF, broken meta.json, missing frontmatter fields
- [x] **CHAOS-02**: Network failure tests — OCR API timeout, HTTP 401, 500, DNS unreachable
- [x] **CHAOS-03**: Filesystem error tests — permission denied, locked files, missing directories, path too long
- [x] **CHAOS-04**: CHAOS_MATRIX.md documents all destructive scenarios with triggers, expected behavior, and safety contracts

### Fixtures / Golden Datasets (FIX)

- [ ] **FIX-01**: Zotero JSON fixtures — 8+ variants covering valid, empty, malformed, missing keys, CJK content, multi-attachment, absolute/storage/bare paths
- [ ] **FIX-02**: PDF fixture samples — minimal valid PDFs including CJK filenames and special characters
- [ ] **FIX-03**: Mock OCR response fixtures — realistic PaddleOCR API responses for submit, poll, result, error, timeout
- [ ] **FIX-04**: Expected output snapshots — formal note, Base file, canonical index expected outputs for golden dataset inputs
- [ ] **FIX-05**: MANIFEST.json tracks all fixtures with `used_by`, `generated`, `desc` metadata

### CI Infrastructure (CI)

- [ ] **CI-01**: PR check workflow (ci-pr-checks.yml) — L0 + L1 on push, <2 minute target
- [ ] **CI-02**: Full CI gate (ci.yml) — L0 through L4 on merge to main
- [ ] **CI-03**: Plasma matrix — 3 OS (win/mac/linux) × 3 Python (3.10/3.11/3.12) for L1; narrower for higher layers
- [ ] **CI-04**: Node 20 CI runner for plugin Vitest tests
- [x] **CI-05**: Scheduled chaos workflow (ci-chaos.yml) — L6 weekly + manual trigger

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real Obsidian E2E in CI | Requires running Obsidian process; 3+ min per test, flaky. Use obsidian-test-mocks for unit tests |
| Load/performance testing | PaperForge is a local single-user tool; no performance requirements |
| Cross-browser testing | Plugin runs inside Obsidian's Electron (Chromium only) — not applicable |
| Full parallel 3×3×6 matrix | 54 CI jobs per PR for minimal added confidence. Plasma matrix is sufficient |
| Automated visual regression | Screenshot-based plugin UI tests are fragile and high-maintenance |
| Coverage percentage gates | Would incentivize superficial testing. Use targeted coverage instead |
| Property-based testing (Hypothesis) | High complexity, low value for this project's domain |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| VC-01 | Phase 51 | Pending |
| VC-02 | Phase 51 | Pending |
| UNIT-01 | Phase 51 | Pending |
| UNIT-02 | Phase 51 | Pending |
| UNIT-03 | Phase 51 | Pending |
| UNIT-04 | Phase 51 | Pending |
| UNIT-05 | Phase 51 | Pending |
| UNIT-06 | Phase 51 | Pending |
| UNIT-07 | Phase 51 | Pending |
| UNIT-08 | Phase 51 | Pending |
| CLI-01 | Phase 52 | Pending |
| CLI-02 | Phase 52 | Pending |
| CLI-03 | Phase 52 | Pending |
| PLUG-01 | Phase 53 | Pending |
| PLUG-02 | Phase 53 | Pending |
| PLUG-03 | Phase 53 | Pending |
| E2E-01 | Phase 53 | Pending |
| E2E-02 | Phase 53 | Pending |
| E2E-03 | Phase 53 | Pending |
| E2E-04 | Phase 53 | Pending |
| E2E-05 | Phase 53 | Pending |
| JNY-01 | Phase 54 | Complete |
| JNY-02 | Phase 54 | Complete |
| JNY-03 | Phase 54 | Complete |
| CHAOS-01 | Phase 54 | Complete |
| CHAOS-02 | Phase 54 | Complete |
| CHAOS-03 | Phase 54 | Complete |
| CHAOS-04 | Phase 54 | Complete |
| FIX-01 | Phase 52 | Pending |
| FIX-02 | Phase 52 | Pending |
| FIX-03 | Phase 52 | Pending |
| FIX-04 | Phase 52 | Pending |
| FIX-05 | Phase 52 | Pending |
| CI-01 | Phase 51 | Pending |
| CI-02 | Phase 55 | Pending |
| CI-03 | Phase 55 | Pending |
| CI-04 | Phase 53 | Pending |
| CI-05 | Phase 54 | Complete |

**Coverage:**
- v2.0 requirements: 38 total
- Mapped to phases: 38
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-08*
*Last updated: 2026-05-08 after initial definition*
