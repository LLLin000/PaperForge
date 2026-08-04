# ANN15 Safety Audit — Reading Canvas Read-Only Verification

> **Phase:** ANN15 (Canvas Verification Gate and Live Harness Record)
> **Plan:** ANN15-02
> **Audit date:** 2026-07-08
> **Classification vocabulary:** `PASS` | `FAIL` | `BASELINE` | `NOT APPLICABLE`

---

## 1. Strict Canvas-Owned Targets (D-16)

All scans are scoped to the following canvas-owned surfaces only:

| Target | Scope | Pattern |
|--------|-------|---------|
| Canvas source modules | `paperforge/plugin/src/canvas/*.js` | 11 files |
| Canvas-focused tests | `paperforge/plugin/tests/canvas-*.test.mjs` | 10 files (per plan list) + `canvas-section-dom.test.mjs` |
| Reading Canvas CSS/connector surfaces | `paperforge/plugin/styles.css` | Connector selectors, card lane classes |

Canvas-owned test files audited:

- `tests/canvas-context.test.mjs`
- `tests/canvas-controller.test.mjs`
- `tests/canvas-viewmodel.test.mjs`
- `tests/canvas-layout.test.mjs`
- `tests/canvas-source-anchor.test.mjs`
- `tests/canvas-navigation.test.mjs`
- `tests/canvas-connectors.test.mjs`
- `tests/canvas-render.test.mjs`
- `tests/canvas-card-dom.test.mjs`
- `tests/canvas-main-runtime.test.mjs`
- `tests/canvas-section-dom.test.mjs` (cross-check, same scoping)

---

## 2. Evidence-Gathering Scans

### Scan 1 — Read-Only Controls Verification (SAFE-01)

**Command (PowerShell via `Select-String`):**
```powershell
Select-String -Path src/canvas/*.js, styles.css, tests/canvas-*.test.mjs `
  -Pattern "contenteditable|create(ing)?\s+annotation|edit(ing)?\s+annotation|delete\s+annotation|save\s+annotation|import\s+annotation|apply\s+annotation|write.back|remove\s+annotation|evidence\s+mutation|concept.card\s+mutation"
```

**Results:**

| File | Line | Match | Classification |
|------|------|-------|---------------|
| `src/canvas/render.js` | 10 | Comment: "No edit, delete, create, save, import, apply, write-back, database, evidence, or concept-card controls" | **PASS** — JSDoc comment asserting absence, not a control |
| `tests/canvas-controller.test.mjs` | 37 | Comment: "Shorthand: create annotation loader wrapping a v0.2 mock" | **PASS** — Test helper comment; negative test exists elsewhere |
| `tests/canvas-viewmodel.test.mjs` | 398 | `const FORBIDDEN = ['edit', 'delete', 'create', 'save', 'import', 'apply', 'writeBack', ...]` | **PASS** — Negative assertion testing absence |
| `tests/canvas-viewmodel.test.mjs` | 442 | `FORBIDDEN_VERBS` array | **PASS** — Negative assertion testing absence |
| `tests/canvas-source-anchor.test.mjs` | 566 | Comment: "D-24/D-25: no navigation, connector, SVG, mutation, write-back" | **PASS** — Assertion comment |
| `tests/canvas-source-anchor.test.mjs` | 579 | `it('D-25: anchor model has no mutation, import, apply, or write-back fields', ...)` | **PASS** — Negative test |
| `tests/canvas-source-anchor.test.mjs` | 590 | `expect(anchor).not.toHaveProperty('write_back')` | **PASS** — Negative assertion |
| `tests/canvas-render.test.mjs` | 44 | FORBIDDEN array = `'write back', 'write-back', 'evidence', 'concept card'` | **PASS** — Negative assertion |
| `tests/canvas-card-dom.test.mjs` | 39 | FORBIDDEN array | **PASS** — Negative assertion |
| `tests/canvas-card-dom.test.mjs` | 668, 676 | `const forbidden = [...]`, `expect(html).not.toContain('contenteditable')` | **PASS** — Negative assertions |
| `tests/canvas-main-runtime.test.mjs` | 400, 732, 740 | `const forbidden = [...]`, `expect(html).not.toContain('contenteditable')` | **PASS** — Negative assertions |
| `tests/canvas-section-dom.test.mjs` | 211, 263 | `it('canvas button text does not contain edit/delete/save/create/import/write-back terms', ...)` | **PASS** — Negative assertion |
| `styles.css` | — | No hits | **PASS** |

**Verdict: PASS** — Zero read-only-breaking controls found in canvas-owned production code. All hits are negative test assertions (`.not.toContain()`, `.not.toHaveProperty()`) or JSDoc comments stating absence. No `contenteditable`, no create/edit/delete/save/import/apply/write-back controls exist in canvas-owned code.

---

### Scan 2 — Persistence / Write Side Effects (SAFE-02)

**Command:**
```powershell
Select-String -Path src/canvas/*.js, styles.css, tests/canvas-*.test.mjs `
  -Pattern "annotations\.db|localStorage|saveData|writeFile|writeText|vault\.modify|modify\(|setItem|persistent\s+layout|layout\s+state"
```

**Results:**

| File | Line | Match | Classification |
|------|------|-------|---------------|
| `src/canvas/layout.js` | 13 | Comment: "No random, draggable, persisted, localStorage, settings, or Obsidian `.canvas` layout data" | **PASS** — JSDoc comment asserting absence |
| `tests/canvas-context.test.mjs` | 43 | `db_path: '/vault/System/PaperForge/indexes/annotations.db'` | **PASS** — Test fixture (mock data), not a write side effect |
| `tests/canvas-layout.test.mjs` | 363, 376 | `it('does not contain localStorage/plugin settings/session fields', ...)` | **PASS** — Negative assertion |
| `tests/canvas-render.test.mjs` | 378 | `it('no card, anchor, connector, or persistent layout classes present', ...)` | **PASS** — Negative assertion |
| `styles.css` | — | No hits | **PASS** |

**Verdict: PASS** — Zero canvas-owned persistence/write side effects. All hits are JSDoc comments asserting absence, test fixture data (read-only mock), or negative test assertions. No `saveData`, `writeFile`, `writeText`, `vault.modify()`, `setItem`, or `localStorage` calls exist in canvas-owned code.

---

### Scan 3 — Native PDF Viewer DOM Dependency (SAFE-03)

**Command:**
```powershell
Select-String -Path src/canvas/*.js, styles.css, tests/canvas-*.test.mjs `
  -Pattern "pdf-viewer|pdf-embed|pdf-container|data-page-number|PDFViewer|viewerContainer"
```

**Results:**

| File | Line | Match | Classification |
|------|------|-------|---------------|
| `tests/canvas-navigation.test.mjs` | 238 | `expect(json).not.toContain('pdf-viewer')` | **PASS** — Negative assertion |
| `tests/canvas-navigation.test.mjs` | 240 | `expect(json).not.toContain('data-page-number')` | **PASS** — Negative assertion |
| `tests/canvas-card-dom.test.mjs` | 550 | `it('has no native PDF selectors (.pdf-viewer, .pdf-embed) [D-04/D-26]', ...)` | **PASS** — Negative test (D-04/D-26) |
| `tests/canvas-card-dom.test.mjs` | 553 | CSS selector check guard | **PASS** — Negative assertion |
| `tests/canvas-card-dom.test.mjs` | 709 | `expect(html).not.toContain('.pdf-viewer')` | **PASS** — Negative assertion |
| `tests/canvas-card-dom.test.mjs` | 710 | `expect(html).not.toContain('.pdf-embed')` | **PASS** — Negative assertion |
| `tests/canvas-card-dom.test.mjs` | 711 | `expect(html).not.toContain('data-page-number="')` | **PASS** — Negative assertion |
| `tests/canvas-card-dom.test.mjs` | 780–782 | Connector block negative assertions | **PASS** — Negative assertions |
| `tests/canvas-main-runtime.test.mjs` | 717–719 | `expect(html).not.toContain('pdf-viewer')`, etc. | **PASS** — Negative assertions |
| `styles.css` | — | No hits | **PASS** |

**Verdict: PASS** — Zero native PDF viewer DOM dependencies in canvas-owned code. All hits are negative test assertions proving the Reading Canvas does NOT use `.pdf-viewer`, `.pdf-embed`, `.pdf-container`, `[data-page-number]`, `PDFViewer`, or `viewerContainer`. The canvas owns its own DOM structure.

---

## 3. Blockers

**None.** All three scans (SAFE-01, SAFE-02, SAFE-03) pass for canvas-owned code. Zero `FAIL` classifications.

---

## 4. Allowed Legacy Occurrences Table (D-18 / D-20)

The following legacy v0.2 occurrences exist outside canvas-owned code. They are **not ANN15 blockers** because:
- They reside in `main.js` (Obsidian plugin host), `src/testable.js` (shared helpers), or non-canvas annotation tests
- They are protected by existing v0.2 fallback tests
- They represent the native PDF overlay architecture (`_findPdfViewerRoot`, `_attachAnnotationOverlay`) which is NOT ported to the Reading Canvas
- `saveData` / `localStorage` maintain plugin settings state orthogonal to canvas rendering

| File | Pattern | Reason | Disposition |
|------|---------|--------|-------------|
| `main.js:523` | `annotations.db` | Settings/storage code: status check for annotations DB availability | **BASELINE** — Plugin host, not canvas-owned |
| `main.js:1559–1560` | `localStorage` | Language detection fallback in plugin init | **BASELINE** — Plugin host, not canvas-owned |
| `main.js:3278` | `_findPdfViewerRoot()` | v0.2 native PDF overlay attachment (`PdfAnnotationOverlay`) | **BASELINE** — v0.2 overlay not ported to canvas |
| `main.js:3284` | `[data-page-number]` | v0.2 native PDF page layer discovery | **BASELINE** — v0.2 overlay not ported to canvas |
| `main.js:3289` | `.pdf-embed` (comment) | v0.2 overlay root creation on PDF page | **BASELINE** — v0.2 overlay, outside canvas scope |
| `main.js:3311, 3322` | `.pdf-embed, .pdf-viewer, .pdf-container` | v0.2 native PDF viewer root selectors | **BASELINE** — v0.2 overlay, outside canvas scope |
| `main.js:3432` | `[data-page-number]` | v0.2 page element query for overlay positioning | **BASELINE** — v0.2 overlay, outside canvas scope |
| `main.js:7514` | `saveData(dataToSave)` | Plugin settings persistence (`saveSettings()`) | **BASELINE** — Plugin host settings, orthogonal to canvas |
| `src/testable.js:331, 457` | `annotations.db` | Legacy test helper comments referencing annotations DB | **BASELINE** — Shared helpers, not canvas-owned |
| `src/testable.js:1368` | `localStorage` (comment) | Test helper comment referencing localStorage | **BASELINE** — Shared helpers, not canvas-owned |
| `tests/annotation-bridge.test.mjs:64` | `annotations.db` | Test fixture mock data for annotation bridge | **BASELINE** — v0.2 annotation test, not canvas-owned |
| `tests/annotation-main-runtime.test.mjs:452` | `localStorage / saveData` | Negative test: "control changes do not persist to plugin settings or localStorage" | **BASELINE** — v0.2 annotation test, not canvas-owned |
| `tests/annotation-main-runtime.test.mjs:881` | `.pdf-embed` | Negative assertion: "Should remain idle — no .pdf-embed in DOM" | **BASELINE** — v0.2 annotation test, not canvas-owned |
| `tests/annotation-overlay.test.mjs:691` | `write-back` / `database` | Negative assertion overlay | **BASELINE** — v0.2 overlay test, not canvas-owned |
| `tests/annotation-section-dom.test.mjs:703, 715` | `write back` | Negative assertion section test | **BASELINE** — v0.2 section test, not canvas-owned |

---

## 5. Summary

| Scan | Requirement | Canvas-Owned Verdict | Notes |
|------|-------------|---------------------|-------|
| Read-only controls | SAFE-01 | **PASS** | Zero production code violations; all hits are negative test assertions or JSDoc comments |
| Persistence/write side effects | SAFE-02 | **PASS** | Zero canvas-owned persistence; `annotations.db`/`localStorage` appear only in test fixtures and JSDoc comments |
| Native PDF DOM dependency | SAFE-03 | **PASS** | Zero canvas-owned native PDF selectors; all hits are negative tests proving canvas-own-DOM |
| Legacy occurrences | D-18 / D-20 | **BASELINE** (n/a) | 15 legacy occurrences allowlisted with rationale; none are ANN15 blockers |

**Final classification:** All three safety requirements pass. No blockers found in canvas-owned code. All legacy occurrences are recorded with clear ownership attribution and protected by existing v0.2 fallback tests.
