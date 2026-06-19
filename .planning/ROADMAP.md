# Roadmap: PaperForge annotation v0.2 - Obsidian PDF Annotation Display Layer

## Overview

annotation v0.2 builds on the completed annotation v0.1 backend and CLI foundation. v0.1 proved PaperForge can safely import Zotero PDF annotations into `annotations.db` and expose them through stable `paperforge annotation import/list/status/export --json` commands.

v0.2 makes those annotations visible and useful inside Obsidian. The milestone starts with a plugin data bridge and sidebar/list view, then adds PDF navigation and overlay support. The overlay is intentionally risk-gated because Obsidian PDF viewer internals can change.

## Phases

- [x] **Annotation Phase 5: Plugin Annotation Data Bridge** - Connect the Obsidian plugin to v0.1 annotation CLI JSON and normalize UI-ready state.
- [ ] **Annotation Phase 6: Annotation Sidebar and List View** - Display paper-scoped annotations in Obsidian with scanning, filtering, refresh, and empty/error states.
- [ ] **Annotation Phase 7: PDF Jump Navigation** - Jump from an annotation row to the source PDF/page using existing paper/PDF path resolution.
- [ ] **Annotation Phase 8: PDF Overlay Rendering Spike and Implementation** - Render imported annotations over the native PDF viewer when available, with graceful fallback.
- [ ] **Annotation Phase 9: Display Layer Verification Gate** - Verify plugin parsing/rendering/navigation/overlay fallback and document known baseline failures separately.

## Phase Details

### Annotation Phase 5: Plugin Annotation Data Bridge

**Goal:** Let the Obsidian plugin load annotation data through the v0.1 CLI contracts without reimplementing annotation storage in TypeScript.

**Depends on:** Annotation Phase 4

**Requirements:** BRDG-01, BRDG-02, BRDG-03, BRDG-04

**Success Criteria:**

1. Plugin has a single annotation data-loading path that calls or reuses `paperforge annotation list/export --json`.
2. CLI JSON parsing preserves page, selected text, comment, color, type, source, read-only state, and attachment identity.
3. Missing DB, missing paper identity, empty annotation list, and command failures produce structured UI states.
4. The bridge is covered by tests using representative PFResult success/error fixtures.

**Plans:**

- `annotation-05-01-PLAN.md` - Testable annotation bridge helpers and state normalization (Wave 1).
- `annotation-05-02-PLAN.md` - Obsidian runtime integration with active-paper annotation state (Wave 2, depends on Wave 1).

### Annotation Phase 6: Annotation Sidebar and List View

**Goal:** Show paper-scoped annotations in an Obsidian UI surface that is useful even before overlay rendering is stable.

**Depends on:** Annotation Phase 5

**Requirements:** LIST-01, LIST-02, LIST-03, LIST-04, LIST-05

**Success Criteria:**

1. User can open a paper annotation list from the PaperForge plugin UI.
2. Rows show page, type/color, selected text, comment, source, and read-only status in a compact readable layout.
3. User can filter or group by page and type/color.
4. User can refresh annotation data after import without restarting Obsidian.
5. Empty, missing PDF, missing DB, and unsupported field states are visible and non-crashing.

**Plans:**

- `annotation-06-01-PLAN.md` - Phase 5 bridge hard preflight and dependency gate (Wave 1).
- `annotation-06-02-PLAN.md` - Pure annotation list view-model helpers and tests (Wave 2, depends on Wave 1).
- `annotation-06-03-PLAN.md` - Paper-mode annotation section runtime integration (Wave 3, depends on Wave 2).
- `annotation-06-04-PLAN.md` - Bounded compact styling and DOM/regression coverage (Wave 4, depends on Wave 3).

### Annotation Phase 7: PDF Jump Navigation

**Goal:** Let the user jump from a list item to the corresponding PDF and page.

**Depends on:** Annotation Phase 6

**Requirements:** OVLY-01

**Success Criteria:**

1. Annotation list rows expose a jump/open action.
2. Jump action resolves the correct paper/PDF path using existing PaperForge metadata/path conventions.
3. Jump action opens the PDF and lands on or near the annotation page where Obsidian supports page fragments or viewer commands.
4. Unsupported jump cases show a clear fallback message and keep the annotation list usable.

**Plans:** TBD

### Annotation Phase 8: PDF Overlay Rendering Spike and Implementation

**Goal:** Render imported annotations over the native Obsidian PDF viewer when viewer internals are available, while falling back safely to the sidebar/list when they are not.

**Depends on:** Annotation Phase 7

**Requirements:** OVLY-02, OVLY-03, OVLY-04, OVLY-05

**Success Criteria:**

1. A spike identifies the current Obsidian PDF viewer hooks/DOM structure used for overlay attachment.
2. Overlay marks are scoped to the active PDF/paper and use stored page/position data.
3. User can inspect selected text/comment from an overlay mark through a lightweight popover or detail surface.
4. Overlay teardown and refresh do not leave stale marks when switching files or panes.
5. If PDF viewer internals are unavailable, the plugin disables overlay and preserves the annotation list workflow.

**Plans:** TBD

### Annotation Phase 9: Display Layer Verification Gate

**Goal:** Prove annotation v0.2 works as an Obsidian-facing display layer and distinguish display-layer regressions from unrelated baseline failures.

**Depends on:** Annotation Phase 8

**Requirements:** SAFE-01, SAFE-02, SAFE-03, SAFE-04, TEST-01, TEST-02, TEST-03, TEST-04, TEST-05

**Success Criteria:**

1. Tests cover plugin parsing of annotation PFResult success/error payloads.
2. Tests cover list rendering states: loaded, empty, missing DB, missing paper, and command failure.
3. Jump-to-PDF/page behavior is verified through tests or a documented manual harness.
4. Overlay verification proves either correct rendering or safe fallback.
5. Final notes confirm v0.2 does not add Zotero write-back or local editing as a primary workflow.

**Plans:** TBD

## Progress

**Execution Order:** Annotation Phase 5 -> Annotation Phase 6 -> Annotation Phase 7 -> Annotation Phase 8 -> Annotation Phase 9

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| Annotation Phase 5. Plugin Annotation Data Bridge | 2/2 | Executed | 2026-06-19 |
| Annotation Phase 6. Annotation Sidebar and List View | 0/4 | Planned | - |
| Annotation Phase 7. PDF Jump Navigation | 0/TBD | Not started | - |
| Annotation Phase 8. PDF Overlay Rendering Spike and Implementation | 0/TBD | Not started | - |
| Annotation Phase 9. Display Layer Verification Gate | 0/TBD | Not started | - |

---
*Roadmap created: 2026-06-18*
