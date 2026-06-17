# Roadmap: PaperForge annotation v0.1 - PDF Annotation Backend & CLI Foundation

## Overview

annotation v0.1 creates the backend foundation for PaperForge PDF annotations on top of the current upstream/master base. The milestone intentionally absorbs only the stable backend/CLI ideas from the old `feat/pdf-annotation-layer` branch. It does not merge the high-risk Obsidian PDF overlay work.

The order is storage first, then Zotero import, then CLI contracts, then verification.

## Phases

- [x] **Annotation Phase 1: Annotation Storage Foundation** - Independent `annotations.db`, schema metadata, source/provenance fields, and rebuild isolation.
- [ ] **Annotation Phase 2: Zotero Probe and Safe Import** - Read-only Zotero SQLite probing, temp-copy access, scoped import reconciliation, and no write-back.
- [ ] **Annotation Phase 3: Annotation CLI JSON Contracts** - `paperforge annotation import/list/status/export --json` with stable success/error output.
- [ ] **Annotation Phase 4: Annotation Verification Gate** - Fixture SQLite, unit/integration/CLI regression tests, and baseline-failure documentation.

## Phase Details

### Annotation Phase 1: Annotation Storage Foundation

**Goal:** Create the PaperForge-owned annotation database layer without coupling it to rebuildable memory/index databases.

**Depends on:** None

**Requirements:** DATA-01, DATA-02, DATA-03, DATA-04

**Success Criteria:**

1. `paperforge/annotation/` exists with database and schema modules.
2. `annotations.db` initializes in the configured PaperForge index/system location.
3. Schema includes source/provenance, paper association, annotation content, position JSON, sync/read-only state, timestamps, and soft-delete fields.
4. A regression test proves memory/index rebuild paths do not drop or mutate `annotations.db`.

**Plans:** 3 plans

Plans:
- [x] annotation-01-01-PLAN.md - Annotation package and DB path/connection helpers [Wave 1]
- [x] annotation-01-02-PLAN.md - Annotation schema lifecycle and schema tests [Wave 2]
- [x] annotation-01-03-PLAN.md - Memory rebuild isolation regression and targeted verification [Wave 3]

### Annotation Phase 2: Zotero Probe and Safe Import

**Goal:** Import Zotero PDF annotations safely from a read-only copied SQLite snapshot.

**Depends on:** Annotation Phase 1

**Requirements:** ZOT-01, ZOT-02, ZOT-03, ZOT-04, ZOT-05, SAFE-01, SAFE-02, SAFE-04

**Success Criteria:**

1. Probe code reads Zotero annotation tables from a copied `zotero.sqlite` snapshot by default.
2. Normalized annotations preserve selected text, comment, color, page, sort index, tags, position JSON, and source modified time.
3. Imported identity includes source and library scope rather than a bare Zotero key alone.
4. Paper-scoped import only reconciles stale rows inside that paper scope.
5. Zotero-sourced rows are marked read-only and no code path writes to Zotero SQLite.

**Plans:** 4 plans

Plans:
- [ ] annotation-02-01-PLAN.md - Zotero snapshot/probe/errors and valid fixture helpers [Wave 1]
- [ ] annotation-02-02-PLAN.md - Zotero annotation normalization [Wave 2, blocked on Wave 1]
- [ ] annotation-02-03-PLAN.md - Scoped import reconciliation into `annotations.db` [Wave 3, blocked on Wave 2]
- [ ] annotation-02-04-PLAN.md - End-to-end import flow verification [Wave 4, blocked on Wave 3]

### Annotation Phase 3: Annotation CLI JSON Contracts

**Goal:** Expose annotation storage and import behavior through stable user-facing CLI commands.

**Depends on:** Annotation Phase 2

**Requirements:** CLI-01, CLI-02, CLI-03, CLI-04, CLI-05, SAFE-03

**Success Criteria:**

1. `paperforge annotation import --json` reports imported/updated/deleted/skipped counts and whether the run was a dry-run.
2. `paperforge annotation list --json` returns ordered annotations for a paper with source provenance and read-only state.
3. `paperforge annotation status --json` returns schema version, DB path, total counts, source counts, and health checks.
4. `paperforge annotation export --json` exports paper-scoped annotations without requiring Obsidian.
5. CLI failure output is stable and actionable for missing Zotero DB, missing config, unknown schema, invalid filters, and unreadable DB.

### Annotation Phase 4: Annotation Verification Gate

**Goal:** Prove annotation v0.1 works and distinguish annotation regressions from unrelated upstream baseline failures.

**Depends on:** Annotation Phase 3

**Requirements:** TEST-01, TEST-02, TEST-03, TEST-04, TEST-05

**Success Criteria:**

1. Test fixtures include a minimal Zotero SQLite database with parent paper, PDF attachment, and multiple annotation rows.
2. Unit tests cover schema creation, probe normalization, importer reconciliation, and service list/export behavior.
3. CLI tests cover success and failure JSON for import/list/status/export.
4. A regression test proves importing one paper does not soft-delete annotations for another paper.
5. Verification notes call out unrelated upstream baseline failures separately from annotation v0.1 status.

## Progress

**Execution Order:** Annotation Phase 1 -> Annotation Phase 2 -> Annotation Phase 3 -> Annotation Phase 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| Annotation Phase 1. Annotation Storage Foundation | 3/3 | ✓ Complete | 2026-06-17 |
| Annotation Phase 2. Zotero Probe and Safe Import | 0/4 | Planned | - |
| Annotation Phase 3. Annotation CLI JSON Contracts | 0/TBD | Not started | - |
| Annotation Phase 4. Annotation Verification Gate | 0/TBD | Not started | - |

---
*Roadmap created: 2026-06-17*
