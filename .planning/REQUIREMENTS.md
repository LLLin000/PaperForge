# Requirements: PaperForge annotation v0.1

**Defined:** 2026-06-17
**Core Value:** Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.

## v0.1 Requirements

Requirements for annotation v0.1. Each maps to roadmap phases.

### Annotation Storage (DATA)

- [ ] **DATA-01**: User has an independent `annotations.db` created under the configured PaperForge index/system location, separate from rebuildable memory databases.
- [ ] **DATA-02**: Annotation schema stores source, library scope, parent paper key, attachment key, selected text, comment, color, page label/index, sort index, tags, position JSON, timestamps, and soft-delete state.
- [ ] **DATA-03**: Annotation schema has explicit schema-version metadata and migration entry points so future annotation versions can evolve without touching `paperforge.db`.
- [ ] **DATA-04**: Memory/index rebuild code does not drop, recreate, or mutate `annotations.db`.

### Zotero Read-Only Import (ZOT)

- [ ] **ZOT-01**: User can import Zotero PDF annotations from a read-only copied `zotero.sqlite` snapshot.
- [ ] **ZOT-02**: User can run a paper-scoped import without deleting or mutating annotations from unrelated papers.
- [ ] **ZOT-03**: Import identity uses source and library scope, not a bare Zotero key alone.
- [ ] **ZOT-04**: Zotero schema probing detects missing/unknown annotation tables or columns and returns an actionable error.
- [ ] **ZOT-05**: Imported Zotero-sourced annotations are marked read-only in v0.1.

### Annotation CLI (CLI)

- [ ] **CLI-01**: User can run `paperforge annotation import --json` and receive stable machine-readable import results.
- [ ] **CLI-02**: User can run `paperforge annotation list --json` for a paper and receive ordered annotations with source provenance.
- [ ] **CLI-03**: User can run `paperforge annotation status --json` and see database health, schema version, total annotations, and source counts.
- [ ] **CLI-04**: User can run `paperforge annotation export --json` for a paper without requiring the Obsidian plugin.
- [ ] **CLI-05**: CLI supports dry-run and paper filtering where relevant, with clear output that distinguishes preview from applied import.

### Safety and Configuration (SAFE)

- [ ] **SAFE-01**: Annotation paths are resolved through PaperForge configuration and do not hardcode vault-specific folders.
- [ ] **SAFE-02**: Zotero DB access defaults to temp-copy mode and cleans up temporary files after import/probe.
- [ ] **SAFE-03**: Error messages cover missing Zotero DB, locked/unreadable DB, missing PaperForge config, unknown Zotero schema, and invalid annotation payloads.
- [ ] **SAFE-04**: v0.1 has no Zotero write-back path and no direct Zotero SQLite mutation.

### Verification (TEST)

- [ ] **TEST-01**: Tests include a fixture Zotero SQLite database with at least one parent paper, one PDF attachment, and multiple annotation types.
- [ ] **TEST-02**: Unit tests cover schema creation, probe normalization, import reconciliation, scoped stale deletion, and service listing/export.
- [ ] **TEST-03**: CLI tests cover `import/list/status/export --json` success and representative failure cases.
- [ ] **TEST-04**: Regression tests prove paper-scoped import does not soft-delete annotations outside the selected paper scope.
- [ ] **TEST-05**: Verification documents any unrelated upstream baseline failures separately from annotation v0.1 failures.

## Future Requirements

### Obsidian PDF Overlay

- **OVLY-01**: User can see imported annotations over the native Obsidian PDF viewer.
- **OVLY-02**: User can open an annotation popover from the PDF overlay.
- **OVLY-03**: Overlay degrades gracefully when Obsidian/PDF.js internals are unavailable.

### Local Annotation Editing

- **EDIT-01**: User can create a local PaperForge annotation from the PDF UI.
- **EDIT-02**: User can edit or delete local PaperForge annotations without modifying Zotero annotations.

### Evidence Integration

- **EVID-01**: User can link an annotation as an evidence anchor from deep-reading output.
- **EVID-02**: Concept-card preview/apply can cite annotation anchors as source evidence.

### Zotero Write-Back

- **PUSH-01**: User can push selected PaperForge local annotations back to Zotero through a safe API-backed path.
- **PUSH-02**: User can review conflicts before write-back.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Obsidian PDF overlay | High-risk plugin/PDF.js work; belongs in annotation v0.2 after backend is stable. |
| Creating/editing/deleting annotations in PDF UI | Requires overlay and interaction model; belongs after read-only import/list works. |
| Writing to Zotero SQLite | Unsafe; Zotero DB is an external source of truth and must not be mutated directly. |
| Zotero Web API write-back | Requires credentials, rate limits, version/conflict handling; future milestone. |
| Concept-card/deep-reading evidence integration | Useful, but annotation storage and CLI must stabilize first. |
| EPUB/web annotations | Different selector model; not needed for PDF annotation MVP. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Annotation Phase 1 | Pending |
| DATA-02 | Annotation Phase 1 | Pending |
| DATA-03 | Annotation Phase 1 | Pending |
| DATA-04 | Annotation Phase 1 | Pending |
| ZOT-01 | Annotation Phase 2 | Pending |
| ZOT-02 | Annotation Phase 2 | Pending |
| ZOT-03 | Annotation Phase 2 | Pending |
| ZOT-04 | Annotation Phase 2 | Pending |
| ZOT-05 | Annotation Phase 2 | Pending |
| CLI-01 | Annotation Phase 3 | Pending |
| CLI-02 | Annotation Phase 3 | Pending |
| CLI-03 | Annotation Phase 3 | Pending |
| CLI-04 | Annotation Phase 3 | Pending |
| CLI-05 | Annotation Phase 3 | Pending |
| SAFE-01 | Annotation Phase 2 | Pending |
| SAFE-02 | Annotation Phase 2 | Pending |
| SAFE-03 | Annotation Phase 3 | Pending |
| SAFE-04 | Annotation Phase 2 | Pending |
| TEST-01 | Annotation Phase 4 | Pending |
| TEST-02 | Annotation Phase 4 | Pending |
| TEST-03 | Annotation Phase 4 | Pending |
| TEST-04 | Annotation Phase 4 | Pending |
| TEST-05 | Annotation Phase 4 | Pending |

**Coverage:**
- annotation v0.1 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0

---
*Requirements defined: 2026-06-17*
*Last updated: 2026-06-17 after annotation v0.1 initiation*
