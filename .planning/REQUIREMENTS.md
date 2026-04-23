# Requirements: PaperForge Lite Release Hardening

**Defined:** 2026-04-23  
**Core Value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

## v1 Requirements

### Onboarding

- [ ] **ONBD-01**: User can follow one registration-to-first-paper guide that covers Zotero, Better BibTeX, Obsidian, PaddleOCR, and PaperForge.
- [ ] **ONBD-02**: User can run one validation command that reports setup readiness by category.
- [ ] **ONBD-03**: User can see the exact next command after each setup or worker step.

### Configuration

- [ ] **CONF-01**: User can define vault and custom directories through environment variables without editing generated code.
- [x] **CONF-02**: User can inspect resolved PaperForge paths with a command.
- [ ] **CONF-03**: Worker, Agent scripts, command docs, and Base generation all use the same config resolver.
- [ ] **CONF-04**: Existing `paperforge.json` installations remain backward-compatible.

### Commands

- [ ] **CMD-01**: User can run stable commands such as `paperforge status`, `paperforge ocr run`, and `paperforge deep-reading`.
- [ ] **CMD-02**: Legacy direct worker invocation remains supported.
- [ ] **CMD-03**: Command output uses actionable statuses and avoids placeholder paths.

### PaddleOCR

- [ ] **OCR-01**: User can run `ocr doctor` to validate token presence, URL shape, network reachability, and expected API response structure.
- [ ] **OCR-02**: OCR worker validates PDF readability before submitting a job.
- [ ] **OCR-03**: OCR failures identify whether the cause is missing token, bad URL, unauthorized token, unreadable PDF, API schema mismatch, timeout, or provider error.
- [ ] **OCR-04**: User can retry/reset errored or blocked OCR records after fixing configuration.
- [ ] **OCR-05**: OCR polling handles provider schema changes defensively and records raw diagnostic snippets safely.

### Zotero And Paths

- [ ] **ZOT-01**: PDF path resolver supports absolute paths, vault-relative paths, configured Zotero junction paths, and common Zotero storage-relative paths.
- [ ] **ZOT-02**: Selection sync reports records with missing or unreadable PDFs.
- [ ] **ZOT-03**: Better BibTeX export path and expected JSON shape are validated.

### Obsidian Bases

- [ ] **BASE-01**: Generated domain Base files include the operational views from the real vault workflow.
- [ ] **BASE-02**: Base filters are rendered from configured paths instead of hardcoded `03_Resources`.
- [ ] **BASE-03**: Base generation preserves user-edited Base files unless explicitly refreshed.
- [ ] **BASE-04**: Literature Hub Base gives a cross-domain queue overview.

### Deep Reading

- [ ] **DEEP-01**: Deep-reading queue accurately shows ready versus blocked papers.
- [ ] **DEEP-02**: `/LD-deep` prepare uses the same resolved paths as workers.
- [ ] **DEEP-03**: `/LD-deep` failure messages tell the user which worker command fixes the blocker.

### Release Quality

- [ ] **REL-01**: Automated tests cover config resolution, PDF path resolution, OCR state transitions, Base rendering, and command launcher behavior.
- [ ] **REL-02**: A smoke test can run through setup validation, selection sync, index refresh, OCR doctor, OCR queue dry-run, and deep-reading queue.
- [ ] **REL-03**: Documentation and AGENTS guide match implemented commands.

## v2 Requirements

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
| Full provider plugin system in v1 | PaddleOCR must be made reliable first |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ONBD-01 | Phase 4 | Pending |
| ONBD-02 | Phase 4 | Pending |
| ONBD-03 | Phase 4 | Pending |
| CONF-01 | Phase 1 | Pending |
| CONF-02 | Phase 1 | Pending |
| CONF-03 | Phase 1 | Done (01-03) |
| CONF-04 | Phase 1 | Done (01-03) |
| CMD-01 | Phase 1 | Pending |
| CMD-02 | Phase 1 | Done (01-03) |
| CMD-03 | Phase 1 | Pending |
| OCR-01 | Phase 2 | Pending |
| OCR-02 | Phase 2 | Pending |
| OCR-03 | Phase 2 | Pending |
| OCR-04 | Phase 2 | Pending |
| OCR-05 | Phase 2 | Pending |
| ZOT-01 | Phase 2 | Pending |
| ZOT-02 | Phase 2 | Pending |
| ZOT-03 | Phase 4 | Pending |
| BASE-01 | Phase 3 | Pending |
| BASE-02 | Phase 3 | Pending |
| BASE-03 | Phase 3 | Pending |
| BASE-04 | Phase 3 | Pending |
| DEEP-01 | Phase 4 | Pending |
| DEEP-02 | Phase 1 | Done (01-03) |
| DEEP-03 | Phase 4 | Pending |
| REL-01 | Phase 5 | Pending |
| REL-02 | Phase 5 | Pending |
| REL-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 28 total
- Mapped to phases: 28
- Unmapped: 0

---
*Requirements defined: 2026-04-23*  
*Last updated: 2026-04-23 after initialization*
