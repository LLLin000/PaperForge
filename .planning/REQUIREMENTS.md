# Requirements: PaperForge v1.12 Install & Runtime Closure

**Defined:** 2026-05-08
**Core Value:** Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.

## v1 Requirements

### Runtime & Install

- [ ] **RUNTIME-01**: Plugin shows the exact Python interpreter path it will use, and whether that path came from manual override or auto-detection
- [ ] **RUNTIME-02**: User can manually set the Python interpreter in plugin settings, and the plugin validates that interpreter before using it
- [ ] **RUNTIME-03**: When no manual override is set, plugin selects a Python interpreter through a defined detection order and uses that same interpreter consistently for install, update, version checks, and commands
- [ ] **RUNTIME-04**: Plugin can detect whether the selected interpreter's installed `paperforge` package matches the plugin version, and can surface or trigger a safe runtime sync path when it does not
- [ ] **RUNTIME-05**: Install and runtime sync failures are classified into actionable categories such as missing Python, invalid interpreter, missing pip, package install failure, dependency failure, or network/source failure
- [ ] **RUNTIME-06**: `zotero_data_dir` is required in setup flow and validated before install completes

### Doctor

- [x] **DOCTOR-01**: `paperforge doctor` reports the actual Python interpreter path and Python version being checked
- [x] **DOCTOR-02**: `paperforge doctor` reports whether `paperforge` is installed in that interpreter, what version/path it resolves to, and whether runtime/package drift or wrong-environment conditions exist
- [x] **DOCTOR-03**: `paperforge doctor` checks critical dependencies including YAML support and gives direct repair guidance for missing packages
- [x] **DOCTOR-04**: `paperforge doctor` ends with a clear top-level verdict and next action, rather than only listing low-level checks

### Dashboard

- [ ] **DASH-01**: User can add or remove a paper from the OCR queue from the Dashboard without manually editing `do_ocr`
- [ ] **DASH-02**: Dashboard provides a complete `/pf-deep` handoff by surfacing `zotero_key`, copying the full command, and telling the user which Agent context to run it in
- [ ] **DASH-03**: OCR actions surface a clear privacy warning before uploading PDFs to PaddleOCR API

### Cleanup & Packaging

- [ ] **CLEAN-01**: Obsolete `docs/` guidance and competing old user-entry paths are removed or demoted so plugin-first onboarding is the primary documented path
- [ ] **CLEAN-02**: Root `manifest.json` is generated from a single canonical manifest source so plugin version metadata cannot drift
- [ ] **CLEAN-03**: `minAppVersion` is raised to a tested Obsidian baseline that supports Bases for the intended workflow
- [ ] **CLEAN-04**: Packaging and runtime metadata are aligned with actual runtime expectations, including fixing `PyYAML` dependency drift

## v2 Requirements

### Onboarding Follow-Ups

- **ONBOARD-01**: Plugin verifies Better BibTeX export JSON presence and validity directly from the UI
- **ONBOARD-02**: Plugin offers one-click copy or validation flow for the exports directory path

## Out of Scope

| Feature | Reason |
|---------|--------|
| Obsidian Community Plugin publishing | Release/distribution work is out of scope for this milestone; focus stays on install/runtime closure inside the existing repo |
| Release automation beyond manifest source alignment | This milestone fixes version-source drift, not the full release pipeline |
| New OCR capabilities | Scope is closure and usability of the existing OCR flow, not new OCR product features |
| New deep-reading capabilities | Scope is handoff and workflow closure for `/pf-deep`, not expanding analysis behavior |
| New research or knowledge-extraction features | This milestone hardens product entry points and runtime behavior rather than adding new end-user capabilities |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| RUNTIME-01 | Phase 51 | Pending |
| RUNTIME-02 | Phase 51 | Pending |
| RUNTIME-03 | Phase 51 | Pending |
| RUNTIME-04 | Phase 52 | Pending |
| RUNTIME-05 | Phase 52 | Pending |
| RUNTIME-06 | Phase 51 | Pending |
| DOCTOR-01 | Phase 53 | Complete |
| DOCTOR-02 | Phase 53 | Complete |
| DOCTOR-03 | Phase 53 | Complete |
| DOCTOR-04 | Phase 53 | Complete |
| DASH-01 | Phase 54 | Pending |
| DASH-02 | Phase 54 | Pending |
| DASH-03 | Phase 54 | Pending |
| CLEAN-01 | Phase 54 | Pending |
| CLEAN-02 | Phase 52 | Pending |
| CLEAN-03 | Phase 52 | Pending |
| CLEAN-04 | Phase 52 | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-08*
*Last updated: 2026-05-08 after roadmap traceability mapping*
