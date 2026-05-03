# Requirements: PaperForge

**Defined:** 2026-05-03
**Core Value:** Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.

## v1 Requirements

Requirements for milestone v1.6: AI-Ready Literature Asset Foundation.

### Configuration Truth

- [x] **CONF-01**: User can configure PaperForge from a single canonical config source (`paperforge.json`) that is interpreted consistently by CLI, workers, setup flow, and plugin.
- [x] **CONF-02**: User can upgrade an existing vault and keep working even if legacy top-level config keys are still present; the system reads them compatibly and writes the normalized shape going forward.
- [x] **CONF-03**: User can inspect the effective runtime configuration and see which values are authoritative versus UI cache values.
- [x] **CONF-04**: User can safely edit plugin settings without creating a second runtime truth that disagrees with Python commands.

### Canonical Asset Index

- [x] **ASSET-01**: User can rebuild a canonical literature asset index from existing library-records, OCR outputs, and formal notes without manual repair of the index file itself.
- [x] **ASSET-02**: User can rely on the canonical index to represent one paper as one unified asset record with stable identifiers, paths, provenance, and schema version.
- [ ] **ASSET-03**: User can refresh the canonical index incrementally after sync, OCR, deep-reading, or repair operations without corrupting existing data.
- [x] **ASSET-04**: User can recover safely from interrupted writes because canonical index updates are atomic and Windows-safe.

### Lifecycle And Health

- [ ] **STATE-01**: User can see each paper's derived lifecycle state such as imported, indexed, PDF-ready, fulltext-ready, deep-read, and AI-context-ready.
- [ ] **STATE-02**: User can see why a paper is not ready, with concrete health findings covering PDF, path resolution, OCR, note linkage, and generated assets.
- [ ] **STATE-03**: User can see the recommended next step for each paper or collection, such as sync, OCR, repair, deep-read, or rebuild index.
- [ ] **STATE-04**: User can trust that readiness states are derived from source artifacts rather than hand-edited status fields.

### Surface Convergence

- [ ] **SURF-01**: User sees the same lifecycle and health meaning in `paperforge status`, plugin dashboard, and generated Base views.
- [ ] **SURF-02**: User can run repair and doctor flows that fix source artifacts first and then rebuild derived state, instead of patching the canonical index directly.
- [ ] **SURF-03**: User can use plugin dashboard actions as a thin shell over CLI commands, without JS re-implementing lifecycle or health rules.
- [ ] **SURF-04**: User can open library queues and health views that are derived from the canonical index rather than duplicated filtering logic spread across the system.

### Maturity And AI Context

- [ ] **AIC-01**: User can see a transparent Library Maturity or Workflow Level for a paper or library, with explainable criteria rather than a black-box score.
- [ ] **AIC-02**: User can generate a traceable context pack for a single paper that includes the relevant metadata, fulltext, note links, and provenance.
- [ ] **AIC-03**: User can generate a collection-level context pack from canonical assets without hardcoding discipline-specific extraction schemas.
- [ ] **AIC-04**: User can use AI context entry points such as ask-this-paper or ask-this-collection only when the system can explain what source assets were included.

### Brownfield Rollout

- [ ] **MIG-01**: User can upgrade an existing PaperForge vault to v1.6 and detect stale or incompatible assets before they silently break dashboard or workflow behavior.
- [x] **MIG-02**: User can rebuild generated artifacts safely during migration without losing hand-authored notes or user intent fields.
- [ ] **MIG-03**: User can run doctor and repair commands that explicitly identify migration issues in old configs, old index formats, old Base templates, or partial OCR assets.
- [ ] **MIG-04**: User can recover from a failed migration with a documented, reversible rebuild path.

## v2 Requirements

Deferred to future release. Tracked but not in the current roadmap.

### Specialized Extraction

- **EXTR-01**: User can define and save domain-specific extraction schemas such as PICO, mechanism tables, or parameter tables.
- **EXTR-02**: User can run schema-driven batch extraction jobs over context packs and persist structured outputs.
- **EXTR-03**: User can manage prompt templates and extraction profiles independently from core asset state.

### Extended AI Workflows

- **AIX-01**: User can compose multi-step review workspaces over multiple collections with reusable saved workflows.
- **AIX-02**: User can audit and compare context-pack outputs across repeated AI runs.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Hardcoded PICO, mechanism, parameter, or other discipline-specific extraction products as core built-ins | This milestone focuses on reusable asset infrastructure, not field-specific output schemas |
| Replacing Zotero, Better BibTeX, or Obsidian Bases | PaperForge is built on top of those systems rather than competing with them |
| Automatically triggering deep-reading agents from workers | The worker/agent split remains intentional and should stay explicit |
| Per-prompt button sprawl in the plugin | Prompt-specific workflows stay templates or optional frameworks, not core product logic |
| Cloud multi-user sync or hosted service features | v1.6 remains local-first and single-user |
| Litmaps or ResearchRabbit-style discovery graph productization | Discovery tooling is outside this milestone's asset-foundation scope |
| Moving business logic from Python into the plugin | The plugin must remain a thin shell over CLI and canonical index outputs |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONF-01 | Phase 22 | Complete |
| CONF-02 | Phase 22 | Complete |
| CONF-03 | Phase 22 | Complete |
| CONF-04 | Phase 22 | Complete |
| ASSET-01 | Phase 23 | Complete |
| ASSET-02 | Phase 23 | Complete |
| ASSET-03 | Phase 23 | Pending |
| ASSET-04 | Phase 23 | Complete |
| STATE-01 | Phase 24 | Pending |
| STATE-02 | Phase 24 | Pending |
| STATE-03 | Phase 24 | Pending |
| STATE-04 | Phase 24 | Pending |
| SURF-01 | Phase 25 | Pending |
| SURF-02 | Phase 25 | Pending |
| SURF-03 | Phase 25 | Pending |
| SURF-04 | Phase 25 | Pending |
| AIC-01 | Phase 24 | Pending |
| AIC-02 | Phase 26 | Pending |
| AIC-03 | Phase 26 | Pending |
| AIC-04 | Phase 26 | Pending |
| MIG-01 | Phase 25 | Pending |
| MIG-02 | Phase 23 | Complete |
| MIG-03 | Phase 25 | Pending |
| MIG-04 | Phase 25 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-03*
*Last updated: 2026-05-03 after v1.6 roadmap creation*
