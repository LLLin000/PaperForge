# Phase Annotation 08: PDF Overlay Rendering Spike and Implementation - Research

**Researched:** 2026-06-28
**Domain:** Obsidian plugin PDF overlay rendering, annotation display, fail-closed UI integration
**Confidence:** HIGH for local code/planning constraints; MEDIUM for live Obsidian PDF viewer DOM until the spike is run

## User Constraints (from CONTEXT.md)

### Locked Decisions

- Overlay activation is automatic but fail-closed. If viewer DOM, PDF page layer, annotation position data, or active PDF identity cannot be confirmed, render no overlay. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]
- Failure to render overlay must preserve existing sidebar/list and Phase 7 page-jump behavior. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]
- Default overlay marks are lightweight semi-transparent highlights using annotation color when usable, otherwise a restrained yellow. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]
- Overlay positioning must use preserved `pdfLocation` fields, especially `pageIndex`, `positionJson`, and `selectorJson`; `pageLabel` is display-only. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]
- Render marks only when active PDF identity and page match confidently; never show supplemental-PDF annotations on the main PDF by guesswork. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]
- Overlay interaction is read-only. Popover/detail may show selected text, comment, page, source/read-only provenance, and identity, but no edit/delete/create controls. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]
- Overlay lifecycle must tear down on active file, pane, paper identity, PDF page DOM, or annotation state changes; no continuous polling. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]
- Phase 8 starts with a spike documenting current observable Obsidian PDF viewer DOM/hooks; if no reliable attachment point exists, land a documented disabled/fallback path. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]

### the agent's Discretion

The planner may choose exact helper names, CSS class names, event hooks, and whether the spike and implementation are split into separate plans, as long as the locked decisions are preserved. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]

### Deferred Ideas (OUT OF SCOPE)

- Sidebar/list row auto-expansion or bidirectional synchronization from overlay click is optional and may be deferred. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]
- Local annotation creation/editing/deletion remains future work. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]
- Zotero write-back remains out of scope. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]
- Concept-card evidence integration remains future work after display/navigation/overlay are stable. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]

## Summary

Phase 8 should be planned as a risk-gated implementation, not a direct UI feature drop. The first serial plan should locally spike the current Obsidian PDF viewer in a manual harness and record the attachable DOM/hook contract. Implementation should proceed only through a fail-closed overlay gate that proves active paper, active PDF identity, usable page layer, and usable `positionJson` before creating any marks. [CITED: .planning/ROADMAP.md] [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]

The existing plugin architecture already has the right extension points: pure annotation helpers and PDF target resolution in `paperforge/plugin/src/testable.js`, runtime shell and Obsidian stubs in `paperforge/plugin/main.js`, namespaced annotation CSS in `paperforge/plugin/styles.css`, and Vitest DOM/runtime harnesses covering list, navigation, and bridge contracts. Phase 8 should extend those seams instead of introducing a framework, external package, persistent state, direct DB access, or a new primary workflow. [VERIFIED: codebase grep]

**Primary recommendation:** Use 4 serial plans/waves: viewer probe, pure geometry/view-model helpers, runtime overlay state/render/teardown, then popover plus final automated/manual gate.

## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| OVLY-02 | User can see imported annotations as highlights or marks over native Obsidian PDF viewer when internals are available. | Spike viewer DOM first; render only PaperForge-owned `.paperforge-annotation-overlay-*` marks on confirmed page layers. [CITED: .planning/REQUIREMENTS.md] |
| OVLY-03 | Overlay positioning uses stored annotation position/page data and remains scoped to active PDF/paper. | Use `pdfLocation.pageIndex`, `positionJson`, `selectorJson`, and `resolveAnnotationPdfTarget()` identity guard. [VERIFIED: paperforge/plugin/src/testable.js] |
| OVLY-04 | User can inspect annotation text/comment from overlay through lightweight popover/detail. | Add read-only popover view-model and DOM tests; no edit/delete/write controls. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md] |
| OVLY-05 | Overlay degrades safely when viewer internals change or are unavailable. | Fail closed with empty marks and friendly internal state; preserve sidebar/list and jump behavior. [CITED: .planning/REQUIREMENTS.md] |

## Project Constraints (from AGENTS.md)

- PaperForge plugin is distributed as Obsidian plugin files `main.js`, `styles.css`, `manifest.json`, and `versions.json`; release packaging should not be changed by Phase 8. [CITED: AGENTS.md]
- Plugin UI text normally uses the project i18n layer when adding broader UI strings; Phase 8 should keep new user-facing strings concise and compatible with existing plugin conventions. [CITED: AGENTS.md]
- Version management is centralized through project scripts; Phase 8 should not manually bump versions unless a later release task requires it. [CITED: AGENTS.md]
- Tests verify contracts and should not be weakened to make broken code pass. [CITED: .planning/STATE.md]
- AGENTS.md rendered with encoding corruption in this terminal; only path/command/English-token directives that were reliably visible are included. [VERIFIED: local file read]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Overlay eligibility and mark view-model | Browser / Client plugin helper layer | Runtime shell | Deterministic parsing, filtering, geometry, and identity decisions should be pure and testable before DOM attachment. [VERIFIED: paperforge/plugin/src/testable.js] |
| Obsidian PDF viewer probing | Browser / Client runtime shell | Obsidian workspace/view APIs | Live viewer DOM/hook inspection belongs in `main.js` because it depends on active panes and Obsidian internals. [VERIFIED: paperforge/plugin/main.js] |
| Overlay DOM rendering/teardown | Browser / Client runtime shell | CSS | Runtime owns attach/remove lifecycle and must remove only PaperForge-owned nodes. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PATTERNS.md] |
| Popover detail | Browser / Client runtime shell | Pure popover view-model helper | The data shape can be tested in helpers; DOM/focus/click behavior belongs in runtime tests. [VERIFIED: codebase grep] |
| Annotation data source | Existing plugin bridge/CLI contract | Python CLI backend | Phase 8 consumes normalized rows only; it must not read or mutate `annotations.db`. [VERIFIED: paperforge/plugin/src/testable.js] |

## Standard Stack

### Core

| Library / File | Version | Purpose | Why Standard |
|---|---:|---|---|
| Obsidian plugin runtime APIs | local plugin dev dependency `obsidian` ^1.12.0 | Workspace, vault, ItemView, Notice, and native PDF viewer context | Existing plugin already uses this runtime shell. [VERIFIED: paperforge/plugin/package.json] |
| `paperforge/plugin/src/testable.js` | local source | Pure annotation normalization, list view-model, refresh merge, PDF target resolution | Established pure helper seam and CommonJS exports for Vitest. [VERIFIED: codebase grep] |
| `paperforge/plugin/main.js` | local source | Obsidian runtime shell, annotation state, DOM rendering, PDF open behavior | Existing place for session state, createEl rendering, and `__test` hooks. [VERIFIED: codebase grep] |
| `paperforge/plugin/styles.css` | local source | Annotation list and future overlay CSS | Existing `.paperforge-annotation-*` namespace and focused style section pattern. [VERIFIED: codebase grep] |
| Vitest + jsdom | Vitest 2.1.9 installed locally; package declares ^2.1.0 | Unit, DOM, runtime stub tests | Current annotation harness uses Vitest and jsdom. [VERIFIED: local node package read] |

### Supporting

| Library / File | Version | Purpose | When to Use |
|---|---:|---|---|
| `annotation-bridge.test.mjs` | local test | Preserves `pdfLocation.positionJson`, `selectorJson`, attachment identity | Extend fixture expectations if overlay helper needs new normalized fields. [VERIFIED: codebase grep] |
| `annotation-navigation.test.mjs` | local test | Fail-closed PDF target resolution | Reuse identity/page mismatch cases for overlay eligibility. [VERIFIED: codebase grep] |
| `annotation-main-runtime.test.mjs` | local test | Obsidian runtime stubs, `openLinkText`, state preservation | Extend for overlay state, fake viewer DOM, teardown, and popover isolation. [VERIFIED: codebase grep] |
| `annotation-section-dom.test.mjs` | local test | DOM regression for annotation rows and forbidden controls | Update old "no overlay/popover" assertion intentionally while preserving no edit/write-back/database/evidence controls. [VERIFIED: codebase grep] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| Existing pure helpers | Ad hoc parsing in `main.js` | Rejected because coordinate parsing and fail-closed eligibility need deterministic unit coverage. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PATTERNS.md] |
| Existing runtime shell | New component framework | Rejected because plugin UI currently uses Obsidian `createEl()` and explicit listeners. [VERIFIED: paperforge/plugin/main.js] |
| Session-only overlay state | Persistent settings/localStorage | Rejected because overlay is runtime availability, not a primary workflow or persisted preference. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md] |

**Installation:** no new packages recommended. Use existing plugin dev dependencies.

## Package Legitimacy Audit

No external packages should be installed for Phase 8. Use the existing Obsidian/Vitest/jsdom test stack already present in `paperforge/plugin/package.json`. [VERIFIED: paperforge/plugin/package.json]

## Recommended Plan Split

| Wave | Plan | Primary Output | Gate |
|---:|---|---|---|
| 1 | Viewer probe and fallback contract | Manual/local spike note identifying current PDF viewer DOM/hooks, active PDF identity signal, page layer target, and fail-closed fallback status | If no reliable attach point exists, stop overlay rendering work and land disabled/fallback state only. |
| 2 | Pure geometry and overlay view-model helpers | `src/testable.js` helpers for position parsing, color normalization, mark building, popover data, and fail-closed result shape | Unit tests for valid rects, invalid JSON, missing rects/page, wrong attachment, supplemental mismatch, non-mutation. |
| 3 | Runtime overlay state/render/teardown | `main.js` session overlay state, safe attach, render marks, refresh/clear lifecycle, bounded observer if needed | Runtime/DOM tests prove attach only on confirmed viewer, teardown removes only PaperForge nodes, list/jump unaffected. |
| 4 | Popover and final gate | Read-only overlay popover, CSS section, final automated gate, manual Obsidian harness note | Focused tests pass; manual harness documents render or safe fallback. |

## Architecture Patterns

### System Architecture Diagram

```text
Annotation CLI JSON
  -> existing bridge normalization
  -> normalized rows {display, provenance, pdfLocation, raw}
  -> Phase 8 pure overlay helpers
      -> resolveAnnotationPdfTarget(row, active paper entry)
      -> parse positionJson / selectorJson
      -> filter by pageIndex + active PDF identity
      -> build marks or fail-closed reason
  -> main.js runtime overlay gate
      -> probe active Obsidian PDF viewer DOM
      -> confirm page layer + active file/PDF identity
      -> render PaperForge-owned overlay marks
      -> click/focus mark opens read-only popover
  -> teardown on file/pane/paper/annotation/viewer change

Failure at any gate
  -> render no overlay
  -> preserve annotation sidebar/list
  -> preserve Phase 7 page-badge jump
  -> show only concise friendly state/notice when needed
```

### Recommended Project Structure

```text
paperforge/plugin/
├── src/testable.js                  # pure overlay helpers and exports
├── main.js                          # runtime probing, state, DOM, teardown, popover
├── styles.css                       # SECTION 41 - PDF Annotation Overlay
└── tests/
    ├── annotation-overlay.test.mjs   # new pure helper tests
    ├── annotation-main-runtime.test.mjs
    └── annotation-section-dom.test.mjs
```

### Pattern 1: Pure Helper Boundary

**What:** Put deterministic overlay logic in `src/testable.js`: `createDefaultAnnotationOverlayState()`, `parseAnnotationPositionJson()`, `normalizeAnnotationColor()`, `buildAnnotationOverlayMarks()`, `buildAnnotationPopoverViewModel()`. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PATTERNS.md]

**When to use:** Any logic that can be tested without live Obsidian: JSON parsing, page/attachment filtering, color fallback, rect shape validation, non-mutating view-model construction.

**Example:**

```javascript
const target = resolveAnnotationPdfTarget(row, entry);
if (!target.ok) {
  return { ok: false, status: 'disabled', marks: [], reason: target.reason };
}
const position = parseAnnotationPositionJson(row.pdfLocation.positionJson);
if (!position.ok) {
  return { ok: false, status: 'disabled', marks: [], reason: 'Annotation has no usable PDF position.' };
}
```

### Pattern 2: Runtime Shell Only Owns Obsidian DOM

**What:** `main.js` should own `_annotationOverlayState`, `_annotationOverlayRootEl`, `_annotationOverlayObserver`, `_tryAttachAnnotationOverlay(reason)`, `_clearAnnotationOverlay()`, `_renderAnnotationOverlayMarks()`, and `_showAnnotationOverlayPopover()`. [VERIFIED: paperforge/plugin/main.js]

**When to use:** Anything that touches `this.app.workspace`, active panes/files, PDF viewer DOM, `MutationObserver`, `Notice`, or Obsidian `createEl()`.

### Pattern 3: CSS Namespace

**What:** Add `SECTION 41 - PDF Annotation Overlay` and style only `.paperforge-annotation-overlay-*` nodes. [VERIFIED: paperforge/plugin/styles.css]

**When to use:** Overlay root, per-page scope, mark, focus state, and popover. Do not style generic PDF viewer selectors.

### Anti-Patterns to Avoid

- **Hard-coded broad PDF selectors:** Live Obsidian PDF DOM can change; broad selectors risk attaching to the wrong pane. Spike first, then gate. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]
- **Guessing PDF identity:** Supplemental annotations on a main PDF are worse than no overlay. Reuse `resolveAnnotationPdfTarget()`. [VERIFIED: paperforge/plugin/src/testable.js]
- **Continuous polling:** Use active file/paper render, annotation refresh, and a bounded observer only after attach. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]
- **Replacing sidebar/list with overlay:** Overlay is an enhancement; list/jump remain the safe workflow. [CITED: .planning/ROADMAP.md]
- **Raw errors in UI:** Preserve friendly error/state patterns and avoid stack traces, raw JSON, Python tracebacks, or shell output. [CITED: .planning/REQUIREMENTS.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Annotation data loading | Direct DB reads or TypeScript SQLite parser | Existing annotation bridge normalized rows | v0.2 source of truth remains CLI/PFResult bridge. [CITED: .planning/REQUIREMENTS.md] |
| PDF identity matching | Path guessing from annotation key | `resolveAnnotationPdfTarget(row, entry)` | Handles attachment identity, single-candidate fallback, and ambiguity fail-closed. [VERIFIED: paperforge/plugin/src/testable.js] |
| UI framework | React/Svelte/custom component layer | Existing Obsidian `createEl()` pattern | Current plugin/test harness is direct DOM with Obsidian stubs. [VERIFIED: paperforge/plugin/main.js] |
| Persistent overlay config | Settings/localStorage flags | Session-only `_annotationOverlayState` | Overlay availability is runtime-dependent and should not become primary workflow state. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md] |
| Error rendering | Raw exception/JSON display | Stable friendly status/reason strings | SAFE-04 forbids raw tracebacks/shell noise in UI. [CITED: .planning/REQUIREMENTS.md] |

**Key insight:** the risky problem is not drawing rectangles; it is proving the rectangle belongs to the active PDF/page in the current pane and tearing it down before it becomes stale.

## Common Pitfalls

### Pitfall 1: Coordinate System Drift
**What goes wrong:** Marks render offset, inverted, or on the wrong text because PDF coordinates, CSS pixels, scale, rotation, or transformed page layers differ.
**Why it happens:** `positionJson` shape is preserved but not yet interpreted by overlay code. [VERIFIED: paperforge/plugin/src/testable.js]
**How to avoid:** Isolate geometry conversion helpers, validate rect shape, and gate live rendering behind the viewer probe.
**Warning signs:** correct page opens but highlights appear outside text or only after zoom/scroll.

### Pitfall 2: Active PDF Identity Mismatch
**What goes wrong:** A mark from a supplemental PDF appears on the main article PDF.
**Why it happens:** Code falls back to the main PDF when `sourceAttachmentKey` does not match.
**How to avoid:** Reuse exact identity guard; no confident target means no mark. [VERIFIED: paperforge/plugin/src/testable.js]
**Warning signs:** annotations with mismatched or missing attachment keys render despite multiple PDF candidates.

### Pitfall 3: Multi-Pane Leakage
**What goes wrong:** Overlay nodes remain in a previous pane or file after navigation.
**Why it happens:** Runtime state is not tied to active file/paper/viewer identity, or teardown removes too broadly/too late.
**How to avoid:** Store overlay root/observer references, clear on active file/paper/viewer changes, and remove only PaperForge-owned nodes.

### Pitfall 4: Viewer DOM Churn
**What goes wrong:** Obsidian rerenders PDF pages and removes or duplicates marks.
**Why it happens:** PDF viewer internals are not a stable API surface.
**How to avoid:** Run Wave 1 spike, use a bounded `MutationObserver` only after attach, and disconnect during clear.

### Pitfall 5: `positionJson` Shape Instability
**What goes wrong:** JSON parse errors or unexpected rect fields reach UI as raw errors.
**Why it happens:** Imported annotation sources may differ in selector/position shape.
**How to avoid:** `parseAnnotationPositionJson()` returns `{ ok:false, reason }`; skip invalid marks and preserve list rows.

## Code Examples

### Existing Normalized Row Contract

```javascript
const pdfLocation = {
    pageIndex: row.page_index,
    pageLabel: row.page_label,
    sourceAttachmentKey: row.source_attachment_key,
    positionJson: row.position_json,
    selectorJson: row.selector_json,
    sortIndex: row.sort_index,
    rowId: row.id,
};
```

Source: `paperforge/plugin/src/testable.js` lines 261-269. [VERIFIED: paperforge/plugin/src/testable.js]

### Existing Fail-Closed PDF Target Guard

```javascript
if (!row) return { ok: false, path: null, page: null, linkText: '', reason: 'No annotation row provided.' };
if (!entry) return { ok: false, path: null, page: null, linkText: '', reason: 'No paper entry provided.' };
if (!pdfLoc) return { ok: false, path: null, page: null, linkText: '', reason: 'Annotation row has no PDF location data.' };
```

Source: `paperforge/plugin/src/testable.js` lines 1274-1286. [VERIFIED: paperforge/plugin/src/testable.js]

### Existing Runtime State Pattern

```javascript
this._annotationState = makeAnnotationState(ANNOTATION_LOAD_STATES.IDLE);
this._annotationLoadSeq = 0;
this._annotationUiState = createDefaultAnnotationListUiState();
this._lastRenderableAnnotationState = null;
```

Source: `paperforge/plugin/main.js` lines 1614-1617. [VERIFIED: paperforge/plugin/main.js]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| No Obsidian display for imported annotations | Sidebar/list display via normalized plugin bridge | Phase 6 complete | Overlay must not replace list fallback. [CITED: .planning/STATE.md] |
| Static annotation page badge | Semantic jump button opening source PDF/page | Phase 7 Plan 03 complete | Overlay click must not interfere with page-badge navigation. [CITED: .planning/phases/annotation-07-pdf-jump-navigation/annotation-07-03-SUMMARY.md] |
| Overlay prohibited in DOM regression | Phase 8 should introduce overlay intentionally | Phase 8 upcoming | Update only overlay/popover prohibition; keep edit/write-back/database/evidence prohibitions. [VERIFIED: codebase grep] |

**Deprecated/outdated:** The current `annotation-section-dom.test.mjs` assertion that no overlay/popover hooks are present is valid only before Phase 8 and should be replaced with positive overlay/fallback assertions. [VERIFIED: codebase grep]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | A bounded `MutationObserver` may be enough to handle PDF page DOM churn after a reliable attach point is found. [ASSUMED] | Recommended Plan Split, Common Pitfalls | If live Obsidian rerenders differently, Wave 1 must choose disabled/fallback or a different event hook. |
| A2 | Current Obsidian PDF viewer exposes enough DOM identity/page structure for a safe overlay in at least the target environment. [ASSUMED] | Summary, Architecture Patterns | If false, Phase 8 should land fail-closed disabled overlay state and defer rendering. |

## Open Questions (RESOLVED INTO EXECUTION GATES)

1. **RESOLVED: What exact PDF viewer DOM/hook is safe today?**
   - Planning resolution: this is intentionally answered by Plan 01, not by static planning. Plan 01 is the blocking viewer-probe gate that records the supported or unsupported attach contract before runtime overlay rendering work proceeds.
   - Executor rule: Plans 02-04 may implement live overlay rendering only when Plan 01 records a supported attach point with viewer root, page layer, active PDF identity signal, and fallback reason semantics. If Plan 01 records unsupported viewer internals, later work must keep the overlay disabled and preserve the sidebar/list plus Phase 7 jump fallback.
   - Evidence source: Phase 8 context requires a spike, fail-closed attach, and documented disabled/fallback path. [CITED: .planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md]

2. **RESOLVED: What `positionJson` shapes exist in real imported data?**
   - Planning resolution: this is handled through strict parser fixtures and sampling, not by guessing all possible source variants up front.
   - Executor rule: Plan 02 must support known fixture shapes and invalid/missing cases with deterministic `{ ok:false, reason }` results. Plan 01 may sample live examples when available. Unsupported or ambiguous shapes remain list/jump only and must not render overlay marks.
   - Evidence source: existing tests preserve examples with `rects`, and the bridge passes raw `positionJson` through for helper-level interpretation. [VERIFIED: paperforge/plugin/tests/annotation-bridge.test.mjs]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---:|---|---|
| Node.js | Vitest and syntax checks | yes | v24.16.0 | none needed |
| npm.cmd | Package scripts on Windows | yes | 11.13.0 | Use `npm.cmd` because `npm` PowerShell shim is blocked by execution policy |
| Vitest | Plugin unit/DOM/runtime tests | yes | 2.1.9 installed locally | none needed |
| Obsidian live app | Manual viewer spike | not available through automated tests | external manual session | document disabled/fallback path if manual spike cannot confirm hooks |

**Missing dependencies with no fallback:**
- None for automated helper/runtime/DOM testing.

**Missing dependencies with fallback:**
- Live Obsidian viewer internals cannot be proven from static code alone; use manual harness and fail-closed fallback.

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | Vitest 2.1.9 with jsdom |
| Config file | `paperforge/plugin/vitest.config.ts` |
| Quick run command | `cd paperforge/plugin; npm.cmd test -- annotation-overlay.test.mjs annotation-navigation.test.mjs` |
| Full focused suite command | `cd paperforge/plugin; npm.cmd test -- annotation-bridge.test.mjs annotation-navigation.test.mjs annotation-main-runtime.test.mjs annotation-section-dom.test.mjs` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| OVLY-02 | Render marks only when viewer/page layer and identity are confirmed | DOM/runtime | `npm.cmd test -- annotation-main-runtime.test.mjs annotation-section-dom.test.mjs` | Existing files; new cases needed |
| OVLY-03 | Position/page/PDF scoping from `pdfLocation` and `positionJson` | unit | `npm.cmd test -- annotation-overlay.test.mjs annotation-navigation.test.mjs` | New `annotation-overlay.test.mjs` needed |
| OVLY-04 | Read-only popover content from selected text/comment/provenance | unit + DOM | `npm.cmd test -- annotation-overlay.test.mjs annotation-section-dom.test.mjs` | New/extended tests needed |
| OVLY-05 | Fail closed with list/jump preserved | runtime + DOM | `npm.cmd test -- annotation-main-runtime.test.mjs annotation-section-dom.test.mjs` | Existing harness; new cases needed |

### Sampling Rate

- **Per task commit:** focused test matching touched layer.
- **Per wave merge:** full focused annotation suite.
- **Phase gate:** `node --check main.js` plus full focused annotation suite, then manual Obsidian overlay harness note.

### Wave 0 Gaps

- [ ] `paperforge/plugin/tests/annotation-overlay.test.mjs` - pure helper coverage for OVLY-02/03/04/05.
- [ ] Fake PDF viewer DOM fixture in runtime/DOM tests.
- [ ] Manual Obsidian harness note for current PDF viewer probe and final gate.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no | No authentication surface in this phase. |
| V3 Session Management | no | Session-only plugin state, no user session handling. |
| V4 Access Control | yes | Read-only display boundary; no Zotero write-back, no DB mutation, no edit/delete controls. [CITED: .planning/REQUIREMENTS.md] |
| V5 Input Validation | yes | Parse and validate `positionJson`, `selectorJson`, color, pageIndex, PDF identity before rendering. |
| V6 Cryptography | no | No cryptographic operations. |

### Known Threat Patterns for Plugin Overlay

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| DOM injection through selected text/comment | Tampering / XSS-like UI injection | Use `setText()` / `textContent`, never `innerHTML` for annotation text. [VERIFIED: paperforge/plugin/main.js] |
| Wrong-PDF overlay | Spoofing / Integrity | Match active PDF via `resolveAnnotationPdfTarget()` and viewer identity; fail closed on ambiguity. [VERIFIED: paperforge/plugin/src/testable.js] |
| Raw error leakage | Information disclosure | Stable friendly reasons/notices only; no raw tracebacks, shell noise, or JSON dumps. [CITED: .planning/REQUIREMENTS.md] |
| Stale overlay after pane/file change | Integrity | Store root/observer refs, clear on active identity changes, remove only PaperForge-owned nodes. |

## Sources

### Primary (HIGH confidence)

- `.planning/ROADMAP.md` - Phase 8 goal, dependency, success criteria. [CITED]
- `.planning/REQUIREMENTS.md` - OVLY, SAFE, TEST requirements. [CITED]
- `.planning/STATE.md` - Phase 7 completion, current test baseline, known failures. [CITED]
- `.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-CONTEXT.md` - locked decisions and boundaries. [CITED]
- `.planning/phases/annotation-08-pdf-overlay-rendering-spike-and-implementation/annotation-08-PATTERNS.md` - local pattern map. [CITED]
- `paperforge/plugin/src/testable.js` - normalized row, view-model, PDF target helper, exports. [VERIFIED]
- `paperforge/plugin/main.js` - runtime state, DOM rendering, page-badge jump, test seam. [VERIFIED]
- `paperforge/plugin/styles.css` - annotation namespace and page badge style. [VERIFIED]
- `paperforge/plugin/tests/*.mjs` annotation suites - bridge/navigation/runtime/DOM harness. [VERIFIED]

### Secondary (MEDIUM confidence)

- None. User explicitly requested no external research.

### Tertiary (LOW confidence)

- A1/A2 assumptions about live Obsidian viewer attach feasibility and bounded observer usefulness.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified from local package and code files.
- Architecture: HIGH - local planning and code agree on pure helper/runtime/CSS/test seams.
- Pitfalls: HIGH for identity/list/fail-closed risks from local context; MEDIUM for live viewer DOM details pending spike.

**Research date:** 2026-06-28
**Valid until:** First Obsidian PDF viewer spike result or any Obsidian/plugin viewer DOM change, whichever comes first.
