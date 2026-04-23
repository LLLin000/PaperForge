# Milestones: PaperForge Lite Release Hardening

**Project:** PaperForge Lite — Local Obsidian + Zotero literature workflow for medical researchers

---

## Milestone v1.0: Initial Release (2026-04-23)

**Goal:** Prove the release is robust enough to ship and maintain.

**Completed:** 2026-04-23

### What Shipped

| Phase | Name | Goal |
|-------|------|------|
| 1 | Config And Command Foundation | Stable commands and shared path/env resolution |
| 2 | PaddleOCR And PDF Path Hardening | Diagnosable, retryable OCR |
| 3 | Config-Aware Obsidian Bases | Real workflow Bases without hardcoded paths |
| 4 | End-To-End Onboarding And Validation | User can complete first-paper flow |
| 5 | Release Verification | Tests and docs prove ship readiness |

### Requirements Validated

| ID | Requirement | Phase |
|----|-------------|-------|
| CONF-01 | Env vars override JSON values | Phase 1 |
| CONF-02 | paperforge_paths returns 13-key inventory | Phase 1 |
| CONF-03 | All consumers use same resolver | Phase 1 |
| CONF-04 | Legacy paperforge.json backward compat | Phase 1 |
| CMD-01 | Stable paperforge CLI commands | Phase 1 |
| CMD-02 | Legacy direct worker invocation supported | Phase 1 |
| CMD-03 | Actionable statuses, no placeholders | Phase 1 |
| DEEP-02 | /LD-deep uses same resolver as workers | Phase 1 |
| OCR-01 | ocr doctor L1-L4 diagnostics | Phase 2 |
| OCR-02 | PDF preflight before OCR | Phase 2 |
| OCR-03 | Failure classification (blocked/error/nopdf) | Phase 2 |
| OCR-04 | Retry by re-running ocr | Phase 2 |
| OCR-05 | Defensive API schema handling | Phase 2 |
| ZOT-01 | PDF path resolver (absolute/relative/junction/storage) | Phase 2 |
| ZOT-02 | Selection sync reports missing PDFs | Phase 2 |
| ZOT-03 | BBT export validation | Phase 4 |
| BASE-01 | 8-view domain Bases matching real workflow | Phase 3 |
| BASE-02 | Config-aware path placeholders | Phase 3 |
| BASE-03 | User-edited Bases preserved on refresh | Phase 3 |
| BASE-04 | Literature Hub Base cross-domain overview | Phase 3 |
| ONBD-01 | Registration-to-first-paper guide | Phase 4 |
| ONBD-02 | paperforge doctor validation command | Phase 4 |
| ONBD-03 | Next-step guidance after each command | Phase 4 |
| DEEP-01 | Deep-reading queue shows ready vs blocked | Phase 4 |
| DEEP-03 | /LD-deep failure messages point to fix command | Phase 4 |
| REL-01 | Unit tests for config, OCR, Base, CLI | Phase 5 |
| REL-02 | Fixture smoke test on dummy vault | Phase 5 |
| REL-03 | Docs/AGENTS match commands | Phase 5 |

### Test Coverage

- 145 tests passing, 2 skipped
- Coverage: config resolver, path resolver, OCR state machine, Base rendering, CLI dispatch, command docs

### Key Files Modified

- `paperforge_lite/config.py` — shared resolver
- `paperforge_lite/cli.py` — CLI launcher
- `paperforge_lite/pdf_resolver.py` — PDF path resolution
- `paperforge_lite/ocr_diagnostics.py` — OCR diagnostics
- `pipeline/worker/scripts/literature_pipeline.py` — worker + Base generation
- `tests/` — 15 test files (145 tests)
- `AGENTS.md` — updated to paperforge CLI format
- `docs/` — installation and setup guides

### Deferred to v1.1

| ID | Requirement | Reason |
|----|-------------|--------|
| INT-01 | OCR provider plugin system | PaddleOCR must stabilize first |
| INT-02 | BBT settings auto-detection | Requires BBT plugin API research |
| INT-03 | Scheduled worker automation | Conflicts with Lite two-layer design |
| UX-01 | Setup wizard repair mode | Current install flow sufficient |
| UX-02 | Base file import parameterization | base-refresh covers this |
| UX-03 | Pipeline health dashboard | Not core to v1 value |

---
*Milestone v1.0 completed: 2026-04-23*
*Total phases: 5 | Total requirements: 28 validated*