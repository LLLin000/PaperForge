# Requirements: v1.3 Path Normalization & Architecture Hardening

> **Defined:** 2026-04-24
> **Core Value:** A new user can install PaperForge, configure their own vault paths and PaddleOCR credentials, then run the full literature pipeline with copy-pasteable commands that diagnose failures clearly.

---

## v1.3 Requirements

### Path Normalization (PATH)

**Goal:** Handle real-world Zotero BBT export paths correctly, supporting absolute paths, multi-attachments, and Obsidian wikilinks.

- [ ] **PATH-01**: Parse BBT JSON `attachments[].path` (absolute Windows paths)
- [ ] **PATH-02**: Extract Zotero 8-bit storage key from `uri`/`select` fields
- [ ] **PATH-03**: Convert absolute path → Vault-relative path (`system/Zotero/storage/KEY/...`)
- [ ] **PATH-04**: Generate Obsidian wikilinks (`[[relative/path]]`) for PDF links
- [ ] **PATH-05**: Handle multi-attachment items (identify main PDF vs supplementary)
- [ ] **PATH-06**: Handle Chinese/special characters in filenames
- [ ] **PATH-07**: Support backward-compatible `storage:` prefix and bare relative paths

### Architecture Cleanup (ARCH)

**Goal:** Fix module boundary leakage discovered during v1.2. Integrate `pipeline/` and `skills/` into `paperforge/` package.

- [ ] **ARCH-01**: Merge `pipeline/worker/scripts/` into `paperforge/worker/`
- [ ] **ARCH-02**: Move `skills/literature-qa/` into `paperforge/skills/`
- [ ] **ARCH-03**: Update all imports to use unified package structure
- [ ] **ARCH-04**: Ensure `pip install -e .` installs all subpackages

### Test Hardening (TEST)

**Goal:** Eliminate test dead zones (broken tests, collection errors) and establish consistent test patterns.

- [ ] **TEST-01**: Fix or remove `test_base_preservation.py` and `test_base_views.py`
- [ ] **TEST-02**: Fix `test_pdf_resolver.py` attachment path normalization
- [ ] **TEST-03**: Add tests for ZoteroPathResolver (all input formats)
- [ ] **TEST-04**: Add tests for wikilink generation
- [ ] **TEST-05**: Ensure all tests pass with 0 failures

### Quality Assurance (QA)

**Goal:** Make consistency audit part of the development workflow, not a manual afterthought.

- [ ] **QA-01**: Create pre-commit hook for consistency audit
- [ ] **QA-02**: Document audit integration in CONTRIBUTING.md
- [ ] **QA-03**: Ensure audit passes on every commit

---

## Deferred to v1.4+

| ID | Requirement | Reason |
|----|-------------|--------|
| PERF-01 | Repair scan O(n*m) → O(n) optimization | Lower priority than path normalization |
| OCR-01 | OCR provider abstraction (beyond PaddleOCR) | Requires API research, not blocking |
| TS-01 | TypeScript Obsidian plugin architecture | Major new stack, needs dedicated milestone |

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Replacing Zotero/Better BibTeX | Core dependency, not changing |
| Auto-triggering deep-reading from workers | Lite architecture keeps them separate |
| Cloud/multi-user service | Local-first scope |
| Mobile app | Not medical researcher workflow |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PATH-01 | Phase 11 | Pending |
| PATH-02 | Phase 11 | Pending |
| PATH-03 | Phase 11 | Pending |
| PATH-04 | Phase 11 | Pending |
| PATH-05 | Phase 11 | Pending |
| PATH-06 | Phase 12 | Pending |
| PATH-07 | Phase 12 | Pending |
| ARCH-01 | Phase 12 | Pending |
| ARCH-02 | Phase 12 | Pending |
| ARCH-03 | Phase 12 | Pending |
| ARCH-04 | Phase 12 | Pending |
| TEST-01 | Phase 12 | Pending |
| TEST-02 | Phase 12 | Pending |
| TEST-03 | Phase 11 | Pending |
| TEST-04 | Phase 11 | Pending |
| TEST-05 | Phase 12 | Pending |
| QA-01 | Phase 13 | Pending |
| QA-02 | Phase 13 | Pending |
| QA-03 | Phase 13 | Pending |

**Coverage:**
- v1.3 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-24*
*Last updated: 2026-04-24 after milestone initiation*
