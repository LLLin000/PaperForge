# Roadmap: PaperForge Lite

**Current:** v1.1 Complete (2026-04-24)  
**Next:** v1.2 candidates under evaluation

---

## Completed: v1.1 Sandbox Onboarding Hardening

**Created:** 2026-04-23  
**Scope:** Fix every issue found by the README-driven sandbox first-time-user simulation.  
**Status:** COMPLETE  

### Phase 6: Setup, CLI, And Diagnostics Consistency

**Goal:** Make the documented setup path, installed CLI, doctor command, and Agent command docs agree on the same paths, env names, and fallback commands.  
**Status:** Done  
**Requirements:** SETUP-01, SETUP-02, SETUP-03, SETUP-04, SETUP-05, DIAG-01, DIAG-02, DIAG-03, DIAG-04 (10/10 Complete)

### Phase 7: Zotero PDF, Metadata, And State Repair

**Goal:** Make sandbox BBT attachment paths resolve correctly and keep OCR/deep-reading state consistent across records, notes, and meta files.  
**Status:** Done (with 3 partial requirements)  
**Requirements:** ZPATH-01~, ZPATH-02~, ZPATH-03~, META-01, META-02, STATE-01, STATE-02, STATE-03, STATE-04 (6/9 Complete, 3 Partial)

### Phase 8: Deep Helper Deployment And Sandbox Regression Gate

**Goal:** Turn the manual sandbox audit into an automated release gate that covers deployed Agent helper importability and `/LD-deep prepare`.  
**Status:** Done (2026-04-24)  
**Requirements:** DEEP-04, DEEP-05, DEEP-06, REG-01, REG-02, REG-03 (6/6 Complete)

---

## Future: v1.2 Candidates

| Priority | Focus | Requirements | Rationale |
|----------|-------|--------------|-----------|
| High | BBT bare path normalization | ZPATH-01, ZPATH-02, ZPATH-03 → Complete | Close the remaining 3 Partial requirements from Phase 7 |
| Medium | Repair scan performance | — | O(n*m) rglob in large vaults; add caching or indexing |
| Medium | OCR provider abstraction | INT-01 | Beyond PaddleOCR (OpenAI, local, etc.) |
| Low | Scheduled worker automation | INT-03 | Run workers without opening an agent session |
| Low | Dashboard health note | UX-03 | Obsidian note summarizing pipeline state |

---

## Phase Summary (All Time)

| # | Phase | Milestone | Goal | Requirements | Status |
|---|-------|-----------|------|--------------|--------|
| 1-5 | Config, PDF, Bases, Onboarding, Workflow | v1.0 | Initial release hardening | 28 | Done |
| 6 | Setup, CLI, And Diagnostics Consistency | v1.1 | Align setup/docs/doctor/path contracts | 10 | Done |
| 7 | Zotero PDF, Metadata, And State Repair | v1.1 | Resolve PDFs and converge status fields | 9 | Done |
| 8 | Deep Helper Deployment And Sandbox Regression Gate | v1.1 | Automate the manual sandbox audit | 6 | Done |

---
*Roadmap created: 2026-04-23 for milestone v1.1*
*Updated: 2026-04-24 — v1.1 complete, v1.2 candidates listed*
