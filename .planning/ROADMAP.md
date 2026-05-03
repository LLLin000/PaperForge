# Roadmap: PaperForge

**Project kind:** brownfield-release-hardening
**Current milestone:** v1.6 — AI-Ready Literature Asset Foundation
**Phase numbering:** Continuous (never restarts). Previous milestone ended at Phase 21, so v1.6 begins at Phase 22.

---

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-04-23)
- ✅ **v1.1 Sandbox Onboarding** — Phases 6-8 (shipped 2026-04-24)
- ✅ **v1.2 Systematization & Cohesion** — Phases 9-10 (shipped 2026-04-24)
- ✅ **v1.3 Path Normalization & Architecture Hardening** — Phases 11-12 (shipped 2026-04-24)
- ✅ **v1.4 Code Health & UX Hardening** — Phases 13-19 (shipped 2026-04-28)
- ✅ **v1.5 Obsidian Plugin Setup Integration** — Phases 20-21 (shipped 2026-04-29)
- 🚧 **v1.6 AI-Ready Literature Asset Foundation** — Phases 22-26 (planned)

---

## Overview

v1.6 turns PaperForge's existing sync, OCR, deep-reading, status, plugin, and `formal-library.json` outputs into one coherent literature asset foundation. The milestone starts by unifying configuration truth, upgrades `formal-library.json` into the canonical derived asset index, derives lifecycle and health from real source artifacts, converges CLI/plugin/Base surfaces on that shared meaning, and then exposes traceable AI context packs on top of trustworthy assets.

## Phases

**Phase Numbering:**
- Integer phases (22, 23, 24...): Planned milestone work
- Decimal phases (22.1, 22.2...): Urgent insertions after roadmap approval

- [x] **Phase 22: Configuration Truth & Compatibility** - Make `paperforge.json` the single runtime truth across CLI, workers, setup, and plugin. (completed 2026-05-03)
- [ ] **Phase 23: Canonical Asset Index & Safe Rebuilds** - Upgrade `formal-library.json` into a rebuildable, atomic, per-paper asset index.
- [ ] **Phase 24: Derived Lifecycle, Health & Maturity** - Compute readiness, health findings, maturity, and next steps from source artifacts.
- [ ] **Phase 25: Surface Convergence, Doctor & Repair** - Make status, plugin dashboard, Base views, doctor, and repair consume the same canonical semantics.
- [ ] **Phase 26: Traceable AI Context Packs** - Generate explainable paper and collection context packs from canonical assets.

## Phase Details

### Phase 22: Configuration Truth & Compatibility
**Goal**: Users can trust one authoritative PaperForge configuration across Python and plugin surfaces, including brownfield vaults with legacy config shapes.
**Depends on**: Phase 21
**Requirements**: CONF-01, CONF-02, CONF-03, CONF-04
**Success Criteria** (what must be TRUE):
  1. User can inspect the effective runtime configuration and clearly see which values come from authoritative `paperforge.json` fields versus plugin UI cache fields.
  2. User can edit settings through the plugin or setup flow, then run `paperforge sync`, `paperforge ocr`, or `paperforge status` and observe the same resolved paths and runtime behavior.
  3. User can open an older vault with legacy top-level config keys and keep using existing commands successfully while PaperForge writes the normalized config shape going forward.
  4. User can change plugin settings without creating a second runtime truth that disagrees with Python-owned config resolution.
**Plans**: 3 plans

Plans:
- [x] 22-01-PLAN.md — Python config layer: schema_version, migration engine, sync hook
- [x] 22-02-PLAN.md — Plugin config truth: read paperforge.json, remove DEFAULT_SETTINGS path fields
- [x] 22-03-PLAN.md — Setup wizard cleanup: vault_config-only output + doctor migration detection + config source tracing

**UI hint**: yes

### Phase 23: Canonical Asset Index & Safe Rebuilds
**Goal**: Users can rebuild and safely refresh a canonical literature asset index from existing library-records, OCR outputs, formal notes, and repair results.
**Depends on**: Phase 22
**Requirements**: ASSET-01, ASSET-02, ASSET-03, ASSET-04, MIG-02
**Success Criteria** (what must be TRUE):
  1. User can rebuild `formal-library.json` from existing library-records, OCR outputs, and formal notes without manually repairing the index file itself.
  2. User can inspect the canonical index and see each paper represented once with stable identifiers, schema version, normalized paths, and provenance.
  3. After `sync`, `ocr`, `deep-reading`, or `repair`, user can refresh the index incrementally and see affected papers update without unrelated asset records being corrupted.
  4. If an index write is interrupted, the previous readable index remains intact and user can rerun the rebuild safely on Windows.
  5. During migration or rebuild, generated artifacts can be regenerated without losing hand-authored notes or user intent fields.
**Plans**: TBD

### Phase 24: Derived Lifecycle, Health & Maturity
**Goal**: Users can understand each paper's lifecycle state, health findings, maturity level, and next best action from source-derived evidence instead of hand-edited status flags.
**Depends on**: Phase 23
**Requirements**: STATE-01, STATE-02, STATE-03, STATE-04, AIC-01
**Success Criteria** (what must be TRUE):
  1. User can see each paper's lifecycle state such as imported, indexed, PDF-ready, fulltext-ready, deep-read, and AI-context-ready, derived from actual source artifacts.
  2. User can see concrete health findings explaining why a paper is blocked, including PDF, path, OCR, note-link, and generated-asset evidence.
  3. User can see a recommended next step for a paper or collection, such as `sync`, `ocr`, `repair`, `/pf-deep`, or rebuild index.
  4. User can trust that readiness states are computed from source artifacts rather than hand-edited status fields.
  5. User can see a transparent maturity/workflow level with explainable criteria instead of a black-box score.
**Plans**: TBD

### Phase 25: Surface Convergence, Doctor & Repair
**Goal**: Users see one consistent library-state model across `paperforge status`, doctor/repair flows, plugin dashboard, and generated Base views, with migration-safe repair paths.
**Depends on**: Phase 24
**Requirements**: SURF-01, SURF-02, SURF-03, SURF-04, MIG-01, MIG-03, MIG-04
**Success Criteria** (what must be TRUE):
  1. User sees the same lifecycle, health, maturity, and next-step meaning in `paperforge status`, plugin dashboard, and generated Base views because they all read the canonical index.
  2. User can use plugin dashboard actions as thin shells over CLI commands and get the same outcomes without JavaScript re-implementing lifecycle or health rules.
  3. User can run `paperforge doctor` or `paperforge repair` on an older vault and get explicit findings for stale configs, old index formats, old Base/templates, or partial OCR assets before those issues silently break workflows.
  4. User can repair source artifacts first and then rebuild derived state, and the repaired result is reflected across CLI, plugin, and Base surfaces without hand-editing the canonical index.
  5. If migration or rebuild fails, user has a documented and reversible rebuild path that restores working generated surfaces without losing notes or intent fields.
**Plans**: TBD
**UI hint**: yes

### Phase 26: Traceable AI Context Packs
**Goal**: Users can generate explainable, reusable AI context packs for one paper or a collection using only canonical, traceable PaperForge assets.
**Depends on**: Phase 25
**Requirements**: AIC-02, AIC-03, AIC-04
**Success Criteria** (what must be TRUE):
  1. User can generate an ask-this-paper or copy-context-pack bundle for a single paper that clearly lists included metadata, fulltext, note links, and provenance.
  2. User can generate a collection-level context pack from canonical assets without requiring hardcoded discipline-specific extraction schemas.
  3. User can only invoke AI context entry points when PaperForge can explain what source assets were included or why pack generation is blocked.
  4. User can trace every item in a context pack back to the originating PDF, OCR output, and formal note.
**Plans**: TBD

## Progress

**Execution Order:** Phases execute sequentially: 22 → 23 → 24 → 25 → 26.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 22. Configuration Truth & Compatibility | 3/3 | Complete   | 2026-05-03 |
| 23. Canonical Asset Index & Safe Rebuilds | 0/TBD | Not started | - |
| 24. Derived Lifecycle, Health & Maturity | 0/TBD | Not started | - |
| 25. Surface Convergence, Doctor & Repair | 0/TBD | Not started | - |
| 26. Traceable AI Context Packs | 0/TBD | Not started | - |

---

*Roadmap updated: 2026-05-03 for milestone v1.6 planning*
