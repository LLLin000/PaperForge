# Requirements: PaperForge annotation v0.2

**Defined:** 2026-06-18
**Core Value:** Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.

## v0.2 Requirements

annotation v0.2 turns the verified annotation backend/CLI from v0.1 into an Obsidian-facing reading surface. The milestone continues after Annotation Phase 4, so the roadmap starts at Annotation Phase 5.

### Plugin Data Bridge (BRDG)

- [ ] **BRDG-01**: User can load annotation data for the active paper in Obsidian through the existing PaperForge plugin without manually running shell commands.
- [ ] **BRDG-02**: Plugin calls the v0.1 annotation CLI/contracts as the source of truth rather than reimplementing annotation database queries in TypeScript.
- [ ] **BRDG-03**: Plugin handles missing `annotations.db`, missing paper identity, empty annotations, and CLI failure states with clear user-facing messages.
- [ ] **BRDG-04**: Annotation rows preserve provenance fields needed for display: page, selected text, comment, color, type, read-only state, source, and source attachment identity.

### Annotation Sidebar/List (LIST)

- [x] **LIST-01**: User can view a paper-scoped annotation list in the PaperForge Obsidian UI.
- [x] **LIST-02**: User can scan annotations by page, color, type, selected text, and comment without opening raw JSON.
- [x] **LIST-03**: User can filter or group annotations by at least page and type/color.
- [x] **LIST-04**: User can refresh the annotation list after importing annotations without restarting Obsidian.
- [x] **LIST-05**: List UI degrades gracefully for empty papers, missing PDFs, and unsupported annotation fields.

### PDF Navigation and Overlay (OVLY)

- [ ] **OVLY-01**: User can jump from an annotation list item to the corresponding PDF and page when the source PDF is available.
- [x] **OVLY-02**: User can see imported annotations as highlights or marks over the native Obsidian PDF viewer when viewer internals are available.
- [x] **OVLY-03**: Overlay positioning uses stored annotation position/page data and remains scoped to the active PDF/paper.
- [ ] **OVLY-04**: User can inspect annotation text/comment from the overlay through a lightweight popover or selection detail.
- [x] **OVLY-05**: Overlay degrades safely when Obsidian PDF.js internals change or are unavailable, falling back to the sidebar/list without breaking the plugin.

### Safety and Scope (SAFE)

- [ ] **SAFE-01**: v0.2 remains read-only for Zotero-sourced annotations; it does not add Zotero write-back.
- [ ] **SAFE-02**: v0.2 does not make local annotation creation/editing/deletion a primary workflow.
- [ ] **SAFE-03**: Plugin display code does not mutate `annotations.db` except through existing explicit import/apply commands if surfaced later.
- [ ] **SAFE-04**: Errors never expose raw Python tracebacks or shell noise in the Obsidian UI.

### Verification (TEST)

- [ ] **TEST-01**: Tests cover plugin-side parsing of annotation CLI JSON success and failure payloads.
- [ ] **TEST-02**: Tests cover annotation list rendering states: loaded rows, empty rows, missing DB, missing paper, and command failure.
- [ ] **TEST-03**: Tests or a documented manual harness cover jump-to-PDF/page behavior.
- [ ] **TEST-04**: Overlay work includes a risk-gated verification path that proves either the overlay renders correctly or the fallback list remains usable.
- [ ] **TEST-05**: Final verification distinguishes v0.2 failures from known unrelated baseline failures inherited from v0.1.

## Future Requirements

### Local Annotation Editing

- **EDIT-01**: User can create a local PaperForge annotation from the PDF UI.
- **EDIT-02**: User can edit or delete local PaperForge annotations without modifying Zotero annotations.
- **EDIT-03**: User can review conflicts between local annotations and imported Zotero annotations.

### Evidence Integration

- **EVID-01**: User can link an annotation as an evidence anchor from deep-reading output.
- **EVID-02**: Concept-card preview/apply can cite annotation anchors as source evidence.
- **EVID-03**: Annotation anchors can be used as evidence candidates during merge/review flows.

### Zotero Write-Back

- **PUSH-01**: User can push selected PaperForge local annotations back to Zotero through a safe API-backed path.
- **PUSH-02**: User can review conflicts before write-back.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Direct Zotero SQLite mutation | Unsafe; Zotero remains an external source of truth. |
| Zotero Web API write-back | Requires credentials, versioning, conflict handling, and a separate safety design. |
| Full local annotation editor | v0.2 focuses on display/navigation/overlay; editing belongs after display is stable. |
| Concept-card evidence integration | Valuable, but v0.2 first proves annotation visibility and PDF grounding inside Obsidian. |
| EPUB/web annotations | Different selector model; PDF annotations remain the target. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BRDG-01 | Annotation Phase 5 | Pending |
| BRDG-02 | Annotation Phase 5 | Pending |
| BRDG-03 | Annotation Phase 5 | Pending |
| BRDG-04 | Annotation Phase 5 | Pending |
| LIST-01 | Annotation Phase 6 | Complete |
| LIST-02 | Annotation Phase 6 | Complete |
| LIST-03 | Annotation Phase 6 | Complete |
| LIST-04 | Annotation Phase 6 | Complete |
| LIST-05 | Annotation Phase 6 | Complete |
| OVLY-01 | Annotation Phase 7 | Complete |
| OVLY-02 | Annotation Phase 8 | Complete |
| OVLY-03 | Annotation Phase 8 | Complete |
| OVLY-04 | Annotation Phase 8 | Pending |
| OVLY-05 | Annotation Phase 8 | Complete |
| SAFE-01 | Annotation Phase 9 | Pending |
| SAFE-02 | Annotation Phase 9 | Pending |
| SAFE-03 | Annotation Phase 9 | Pending |
| SAFE-04 | Annotation Phase 9 | Pending |
| TEST-01 | Annotation Phase 9 | Pending |
| TEST-02 | Annotation Phase 9 | Pending |
| TEST-03 | Annotation Phase 9 | Pending |
| TEST-04 | Annotation Phase 9 | Pending |
| TEST-05 | Annotation Phase 9 | Pending |

**Coverage:**

- annotation v0.2 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0

---
*Requirements defined: 2026-06-18*
*Last updated: 2026-06-18 after annotation v0.2 initiation*
