# Phase Annotation 08: PDF Overlay Rendering Spike and Implementation - Pattern Map

**Mapped:** 2026-06-28
**Files analyzed:** 5 target files plus 4 required test analogs
**Analogs found:** 4 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `paperforge/plugin/src/testable.js` | utility | transform / request-response decision | `resolveAnnotationPdfTarget`, `buildAnnotationListViewModel`, `mergeAnnotationRefreshResult` | exact |
| `paperforge/plugin/main.js` | controller / runtime shell | event-driven / request-response DOM | `_renderAnnotationSection`, `_renderAnnotationRows`, `_openAnnotationPdf` | exact |
| `paperforge/plugin/styles.css` | config / style | DOM presentation | `SECTION 40 - Annotation List` and page badge CSS | role-match |
| `paperforge/plugin/tests/annotation-overlay.test.mjs` or equivalent new pure helper tests | test | transform | `annotation-navigation.test.mjs`, `annotation-bridge.test.mjs` | exact |
| `paperforge/plugin/tests/annotation-overlay-dom.test.mjs` or extensions to existing DOM/runtime tests | test | event-driven DOM | `annotation-main-runtime.test.mjs`, `annotation-section-dom.test.mjs` | exact |
| `docs/planning/manual-obsidian-overlay-check.md` or phase summary note | docs / verification | manual spike | no direct code analog | no analog |

## Pattern Assignments

### `paperforge/plugin/src/testable.js` (utility, transform)

**Analog:** `paperforge/plugin/src/testable.js`

Phase 8 helper logic should live here when it can be tested without Obsidian. Do not put coordinate parsing, fail-closed overlay eligibility, color normalization, row-to-overlay view-model construction, or popover content shaping only in `main.js`.

**State and normalized row contract** (lines 220-296):

```javascript
const ANNOTATION_LOAD_STATES = Object.freeze({
    IDLE: 'idle',
    LOADING: 'loading',
    READY: 'ready',
    EMPTY: 'empty',
    MISSING_PAPER: 'missing-paper',
    MISSING_DB: 'missing-db',
    CLI_ERROR: 'cli-error',
    INVALID_JSON: 'invalid-json',
});

function normalizeAnnotationExportRow(row) {
    const display = {
        page: row.page_index,
        pageLabel: row.page_label,
        type: row.type,
        color: row.color,
        selectedText: row.selected_text,
        comment: row.comment,
    };

    const provenance = {
        source: row.source,
        isReadonly: Boolean(row.is_readonly),
        sourceAttachmentKey: row.source_attachment_key,
        sourceAnnotationKey: row.source_annotation_key,
        syncState: row.sync_state,
    };

    const pdfLocation = {
        pageIndex: row.page_index,
        pageLabel: row.page_label,
        sourceAttachmentKey: row.source_attachment_key,
        positionJson: row.position_json,
        selectorJson: row.selector_json,
        sortIndex: row.sort_index,
        rowId: row.id,
    };

    return { display, provenance, pdfLocation, raw: row };
}
```

**Planner constraint:** overlay helpers must consume `row.display`, `row.provenance`, and `row.pdfLocation`; they must not reparse CLI JSON or read `annotations.db`.

**Session UI identity pattern** (lines 640-668):

```javascript
function createDefaultAnnotationListUiState() {
    return {
        query: '',
        groupMode: 'none',
        typeColorFilter: 'all',
        expandedIds: [],
    };
}

function getAnnotationIdentity(row) {
    if (!row) return '';
    const p = row.provenance || {};
    const loc = row.pdfLocation || {};
    const d = row.display || {};

    if (p.sourceAnnotationKey) return String(p.sourceAnnotationKey);
    if (loc.rowId) return String(loc.rowId);
    if (p.source) return p.source + '|' + (p.sourceAttachmentKey || '') + '|' + (d.page != null ? d.page : '') + '|' + (loc.sortIndex != null ? loc.sortIndex : 0);
    return 'row|' + (d.page != null ? d.page : '') + '|' + (loc.sortIndex != null ? loc.sortIndex : 0);
}
```

**Planner constraint:** add overlay state as a small session-only object, e.g. `createDefaultAnnotationOverlayState()` with fields such as `status`, `paperKey`, `pdfPath`, `viewerAttached`, `activePopoverId`, `lastErrorCode`. It must not persist to plugin settings or localStorage.

**View-model and fail-closed pattern** (lines 946-1035, 1106-1126):

```javascript
function buildAnnotationListViewModel(annotationState, uiState) {
    const aState = annotationState || { state: 'idle', annotations: [] };
    const ui = uiState || createDefaultAnnotationListUiState();
    const rows = Array.isArray(aState.annotations) ? aState.annotations : [];
    const state = aState.state || 'idle';

    if (state === 'loading') {
        return { state: 'loading', rows: [], total: 0, banner: aState.message || 'Loading annotations...', filterOptions: [], groups: undefined, uiState: ui };
    }

    if (state === 'missing-db') {
        return { state: 'missing-db', rows: [], total: 0, errorMessage: aState.message || 'The annotation database is not yet available.', filterOptions: [], groups: undefined, uiState: ui, stale: aState.stale || false };
    }
}

function mergeAnnotationRefreshResult(previousRenderable, nextState) {
    if (nextState.state === 'ready' || nextState.state === 'empty') {
        return nextState;
    }
    if (previousRenderable) {
        const prevState = previousRenderable.state || '';
        if (prevState === 'ready' || prevState === 'empty') {
            const merged = JSON.parse(JSON.stringify(previousRenderable));
            merged.stale = true;
            merged.message = (nextState.message || 'Refresh failed.') + ' - Showing previously loaded (stale) data.';
            return merged;
        }
    }
    return nextState;
}
```

**Planner constraint:** implement overlay eligibility/view-model helpers with the same shape: return explicit `{ ok/status, marks: [], reason }`; on failure return an empty mark set and a stable friendly reason. Failed overlay refresh must not discard usable annotation list state.

**PDF identity guard pattern** (lines 1139-1168, 1274-1346):

```javascript
function extractVaultPdfPath(value) {
    if (value == null || typeof value !== 'string') {
        return { ok: false, path: null, reason: 'PDF path must be a string.' };
    }
    if (/^[A-Za-z]:\\/.test(value)) {
        return { ok: false, path: null, reason: 'Absolute paths are not supported.' };
    }
    const match = value.match(/^\[\[([^\]]+)\]\]$/);
    if (!match) {
        return { ok: false, path: null, reason: 'Malformed wikilink.' };
    }
}

function resolveAnnotationPdfTarget(row, entry) {
    if (!row) return { ok: false, path: null, page: null, linkText: '', reason: 'No annotation row provided.' };
    if (!entry) return { ok: false, path: null, page: null, linkText: '', reason: 'No paper entry provided.' };
    const pdfLoc = row.pdfLocation;
    if (!pdfLoc) return { ok: false, path: null, page: null, linkText: '', reason: 'Annotation row has no PDF location data.' };

    const identity = pdfLoc.sourceAttachmentKey;
    if (identity != null && identity !== '') {
        resolvedCandidate = candidates.find(c => c.attachmentKey === identity) || null;
        if (!resolvedCandidate) {
            return { ok: false, path: null, page: null, linkText: '', reason: 'Could not resolve the annotation to a PDF in the paper entry.' };
        }
    }
}
```

**Planner constraint:** overlay must call or mirror this target resolution before rendering. Supplemental-PDF annotations must fail closed rather than appearing on the main PDF.

**Export pattern** (lines 1354-1390):

```javascript
module.exports = {
    ANNOTATION_LOAD_STATES,
    normalizeAnnotationExportRow,
    makeAnnotationState,
    createDefaultAnnotationListUiState,
    getAnnotationIdentity,
    buildAnnotationListViewModel,
    mergeAnnotationRefreshResult,
    extractVaultPdfPath,
    buildPaperPdfCandidates,
    resolveAnnotationPdfTarget,
};
```

**Planner constraint:** any new pure helper must be exported from `src/testable.js` and mirrored into the inlined helper area in `main.js` if the plugin build still requires inline code.

Recommended new helpers:

| Helper | Location | Purpose |
|---|---|---|
| `createDefaultAnnotationOverlayState()` | `src/testable.js` | session-only overlay status defaults |
| `parseAnnotationPositionJson(positionJson)` | `src/testable.js` | JSON parse with `{ ok:false }` on invalid/missing data |
| `normalizeAnnotationColor(color)` | `src/testable.js` | use valid source color, fallback restrained yellow |
| `buildAnnotationOverlayMarks(annotationState, entry, activePdfPath)` | `src/testable.js` | filter by PDF identity/page/position and return renderable mark view-model |
| `buildAnnotationPopoverViewModel(row)` | `src/testable.js` | selected text/comment/page/source/read-only details, no edit controls |

### `paperforge/plugin/main.js` (runtime shell, event-driven DOM)

**Analog:** `PaperForgeStatusView` annotation list and PDF jump runtime.

**Session state and stale guard pattern** (lines 1603-1683):

```javascript
this._annotationState = makeAnnotationState(ANNOTATION_LOAD_STATES.IDLE);
this._annotationLoadSeq = 0;
this._annotationUiState = createDefaultAnnotationListUiState();
this._lastRenderableAnnotationState = null;

async loadAnnotationsForCurrentPaper(reason) {
    if (!this._currentPaperKey) {
        this._annotationState = makeAnnotationState(ANNOTATION_LOAD_STATES.MISSING_PAPER, {
            paperKey: null,
            message: 'No paper is currently active. Open a paper note or PDF to view its annotations.',
        });
        return null;
    }

    const capturedSeq = ++this._annotationLoadSeq;
    const capturedKey = this._currentPaperKey;
    const result = await annotationLoader({ paperKey: capturedKey, pythonExe, pythonExtraArgs: extraArgs, cwd: vp, timeout: 30000 });

    if (this._currentPaperKey !== capturedKey || this._annotationLoadSeq !== capturedSeq) {
        return this._annotationState;
    }
    result.paperKey = capturedKey;
    this._annotationState = result;
    return result;
}
```

**Planner constraint:** add `_annotationOverlayState`, `_annotationOverlayRootEl`, and possibly `_annotationOverlayObserver` in the same constructor area. Use a monotonic sequence or active identity guard when async viewer probing is involved. Teardown overlay on active paper/file/viewer changes.

**DOM insertion and fallback list pattern** (lines 2595-2675):

```javascript
this._renderAnnotationSection(view, this.getAnnotationState(), entry);

_renderAnnotationSection(container, annotationState, entry) {
    var section = container.createEl('div', { cls: 'paperforge-annotations-section' });
    this._annotationSectionEl = section;

    var vm = buildAnnotationListViewModel(annotationState, this._annotationUiState);

    var header = section.createEl('div', { cls: 'paperforge-annotations-header' });
    header.createEl('span', { cls: 'paperforge-annotations-title', text: 'Annotations' });
    var refreshBtn = header.createEl('button', { cls: 'paperforge-annotations-refresh-btn clickable-icon' });
    refreshBtn.setAttribute('title', 'Refresh annotations');
    refreshBtn.addEventListener('click', this._handleAnnotationRefresh.bind(this));

    var contentArea = section.createEl('div', { cls: 'paperforge-annotations-content' });
    switch (vm.state) {
        case 'ready':
            this._renderAnnotationRows(contentArea, vm);
            break;
        case 'missing-db':
        case 'missing-paper':
        case 'cli-error':
        case 'invalid-json':
            contentArea.createEl('div', { cls: 'paperforge-annotations-error', text: vm.errorMessage || 'Annotation data unavailable.' });
            break;
    }
}
```

**Planner constraint:** overlay must be an enhancement outside the list rendering path. Do not hide, replace, or make `_renderAnnotationSection()` depend on overlay success.

**Row DOM and event isolation pattern** (lines 2731-2828):

```javascript
var rowEl = listContainer.createEl('div', { cls: 'paperforge-annotation-row' });

var badgeResult = resolveAnnotationPdfTarget(row, this._currentPaperEntry);
var pageBadge = rowEl.createEl('button', {
    cls: 'paperforge-annotation-page-badge',
    text: String(display.pageLabel || display.page || '?'),
    title: badgeTitle,
    attr: { 'aria-label': badgeAriaLabel },
});
if (!badgeEnabled) {
    pageBadge.disabled = true;
    pageBadge.setAttribute('aria-disabled', 'true');
}
pageBadge.addEventListener('click', function (r) {
    return function (ev) {
        ev.stopPropagation();
        this._openAnnotationPdf(r);
    };
}(row).bind(this));

var selEl = rowEl.createEl('span', { cls: 'paperforge-annotation-selected-text' });
selEl.setText(selPreview.text);
```

**Planner constraint:** overlay DOM must use `createEl()` / `document.createElement()` and `textContent` or `setText` for user text. Overlay click handlers must `stopPropagation()` where needed and must not trigger row expansion or page-jump side effects.

**Navigation read-only pattern** (lines 2938-2954):

```javascript
_openAnnotationPdf(row) {
    var result = resolveAnnotationPdfTarget(row, this._currentPaperEntry);
    if (!result.ok) {
        new Notice(result.reason || 'Could not open PDF for this annotation.', 5000);
        return;
    }

    var abstractFile = this.app.vault.getAbstractFileByPath(result.path);
    if (!abstractFile) {
        new Notice('PDF file not found in vault: ' + result.path, 5000);
        return;
    }

    this.app.workspace.openLinkText(result.linkText, '');
}
```

**Planner constraint:** overlay attach/render must be read-only. It may inspect active file/viewer DOM, but must not write Zotero, mutate `annotations.db`, save plugin settings, or call filesystem writers.

**Runtime test hook pattern** (lines 6050-6058):

```javascript
if (typeof module !== 'undefined' && module.exports) {
    module.exports.__test = {
        PaperForgeStatusView,
        extractVaultPdfPath,
        buildPaperPdfCandidates,
        resolveAnnotationPdfTarget,
    };
}
```

**Planner constraint:** expose any runtime-only overlay methods needed by tests through this existing `__test` seam. Keep exported hooks side-effect free.

Recommended runtime methods:

| Function / field | Location | Responsibility |
|---|---|---|
| `_annotationOverlayState` | `PaperForgeStatusView` constructor | session-only overlay status |
| `_clearAnnotationOverlay()` | `main.js` | remove PaperForge-owned overlay root/popover/observer |
| `_tryAttachAnnotationOverlay(reason)` | `main.js` | event-driven safe probe, fail closed |
| `_renderAnnotationOverlayMarks(viewerContext, marks)` | `main.js` | DOM creation over confirmed page layer |
| `_showAnnotationOverlayPopover(mark, anchorEl)` | `main.js` | read-only PDF-local details |
| `_refreshAnnotationOverlay(reason)` | `main.js` | rebuild from confirmed annotation state and active PDF identity |

### `paperforge/plugin/styles.css` (style config, DOM presentation)

**Analog:** `SECTION 40 - Annotation List`.

**Annotation style namespace pattern** (lines 2434-2586):

```css
/* SECTION 40 - Annotation List */
.paperforge-annotations-section {
    margin: 8px 0 4px;
}

.paperforge-annotations-error {
    padding: 10px 10px;
    margin: 4px 0;
    font-size: 12px;
    color: var(--text-error);
    background: color-mix(in srgb, var(--text-error) 6%, transparent);
    border: 1px solid color-mix(in srgb, var(--text-error) 16%, transparent);
    border-radius: var(--radius-s, 4px);
    line-height: 1.4;
}
```

**Planner constraint:** add a separate section, e.g. `SECTION 41 - PDF Annotation Overlay`, using only `paperforge-annotation-overlay-*` class names. Do not style generic `.pdf-viewer`, `.page`, `.textLayer`, or global `[data-*]` selectors.

**Interactive highlight/button pattern** (lines 2609-2642):

```css
.paperforge-annotation-page-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 22px;
    padding: 1px 5px;
    font-size: 10px;
    font-weight: 600;
    color: var(--text-faint);
    background: var(--pf-surface-alt);
    border: none;
    border-radius: 3px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s, opacity 0.15s;
}

.paperforge-annotation-page-badge:focus-visible {
    outline: 2px solid var(--interactive-accent);
    outline-offset: 1px;
}
```

**Planner constraint:** overlay marks should be lightweight: `position:absolute`, transparent fill, small border radius, `mix-blend-mode` only if verified safe, and focus-visible styling. Preserve PDF text readability.

Recommended CSS classes:

| Class | Purpose |
|---|---|
| `.paperforge-annotation-overlay-root` | PaperForge-owned absolute overlay container attached inside confirmed page/container |
| `.paperforge-annotation-overlay-page` | Per-page overlay scope, if needed |
| `.paperforge-annotation-overlay-mark` | Highlight rectangle |
| `.paperforge-annotation-overlay-mark:focus-visible` | Keyboard focus ring |
| `.paperforge-annotation-overlay-popover` | Read-only details surface |
| `.paperforge-annotation-overlay-popover-title` | compact source/page line |
| `.paperforge-annotation-overlay-popover-text` | selected text |
| `.paperforge-annotation-overlay-popover-comment` | comment |

### Pure helper tests (test, transform)

**Analogs:** `paperforge/plugin/tests/annotation-navigation.test.mjs`, `paperforge/plugin/tests/annotation-bridge.test.mjs`.

**Bridge fixture with position/selector preservation** (`annotation-bridge.test.mjs` lines 47-48, 218-219):

```javascript
position_json: '{"pageIndex":0,"rects":[{"x":0,"y":0,"w":100,"h":20}]}',
selector_json: '{}',

position_json: '{"pageIndex":2,"rects":[]}',
selector_json: '{"type":"text","value":"test"}',
```

**Planner constraint:** add tests proving helper behavior for valid rects, invalid JSON, missing rects, missing `pageIndex`, wrong attachment identity, supplemental mismatch, color fallback, and non-mutating input.

**Navigation helper test style** (`annotation-navigation.test.mjs` lines 239-320, 326-425):

```javascript
const result = resolveAnnotationPdfTarget(row, entryMainOnly);
expect(result.ok).toBe(true);
expect(result.page).toBe(1);

const result = resolveAnnotationPdfTarget(rowWithMismatch, entryMainOnly);
expect(result.ok).toBe(false);
expect(result.path).toBeNull();
expect(result.reason).toBeTruthy();
```

**Planner constraint:** overlay helper tests should assert stable result shape, fail-closed reasons, no raw internal exception strings in user-facing messages, and no mutation.

### Runtime / DOM overlay tests (test, event-driven DOM)

**Analogs:** `paperforge/plugin/tests/annotation-main-runtime.test.mjs`, `paperforge/plugin/tests/annotation-section-dom.test.mjs`.

**Obsidian stub and createEl harness** (`annotation-main-runtime.test.mjs` lines 34-115):

```javascript
function installObsidianStub() {
    originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (request === 'obsidian') {
            return {
                Plugin: class Plugin {},
                Notice: class Notice {
                    constructor(msg, duration) {
                        this.msg = msg;
                        this.duration = duration;
                        noticeCalls.push(this);
                    }
                },
                ItemView: class ItemView {
                    constructor(leaf) {
                        this.leaf = leaf;
                        this.app = leaf && leaf.app;
                        this.containerEl = leaf && leaf.containerEl;
                    }
                },
                addIcon: vi.fn(),
            };
        }
        return originalLoad.call(this, request, parent, isMain);
    };
}
```

**Runtime view fixture** (`annotation-main-runtime.test.mjs` lines 209-258):

```javascript
function makeRuntimeView(opts = {}) {
    const containerEl = createObsidianEl('div');
    const contentEl = createObsidianEl('div', { cls: 'paperforge-content-area' });
    containerEl.appendChild(contentEl);
    addCreateEl(contentEl);

    const view = Object.create(PaperForgeStatusView.prototype);
    view.app = opts.app || makeStubApp();
    view._currentPaperKey = Object.prototype.hasOwnProperty.call(opts, 'paperKey') ? opts.paperKey : 'PAPER_A';
    view._currentPaperEntry = opts.paperEntry || { title: 'Test Paper', pdf_path: '[[test.pdf]]' };
    view._annotationState = opts.annotationState || readyState(view._currentPaperKey, 3);
    view._annotationUiState = opts.uiState || { query: '', groupMode: 'none', typeColorFilter: 'all', expandedIds: [] };
    view._annotationLoader = opts.loader || vi.fn(async ({ paperKey }) => readyState(paperKey, 3));
    return view;
}
```

**Planner constraint:** extend this harness for fake PDF viewer DOM. Tests should create a minimal viewer/page layer fixture and prove overlay attaches only when required selectors/identity/page data are present.

**Navigation and state preservation tests** (`annotation-main-runtime.test.mjs` lines 697-770, 773-812):

```javascript
view._openAnnotationPdf(row);
expect(app.workspace.openLinkText).toHaveBeenCalledWith('99_System/Zotero/storage/ABCDEFGH/test.pdf#page=3', '');

badge.click();
expect(view._annotationUiState.query).toBe('');
expect(view._annotationUiState.groupMode).toBe('page');
expect(view._annotationUiState.typeColorFilter).toBe('all');
```

**Planner constraint:** overlay click/popover tests must prove no call to `openLinkText` unless explicitly invoking the page badge, no change to `_annotationUiState.expandedIds`, and no list rerender side effect.

**Forbidden controls regression surface** (`annotation-section-dom.test.mjs` lines 617-704):

```javascript
const jumpButtons = section.querySelectorAll('.paperforge-annotation-page-badge');
expect(jumpButtons.length).toBe(1);
expect(jumpButtons[0].tagName).toBe('BUTTON');

const html = section.innerHTML.toLowerCase();
expect(html).not.toContain('save');
expect(html).not.toContain('write back');
expect(html).not.toContain('sync to zotero');
expect(html).not.toContain('database');
expect(html).not.toContain('evidence');
```

**Planner constraint:** update the old "no overlay/popover hooks present" assertion intentionally once overlay exists, but keep stronger prohibitions: no edit/delete/remove, no write-back, no database mutation, no concept-card evidence controls.

## Shared Patterns

### Annotation State/List/Navigation Architecture

Source:
- `paperforge/plugin/src/testable.js` lines 220-296, 640-668, 946-1126, 1274-1346
- `paperforge/plugin/main.js` lines 1603-1683, 2619-2675, 2731-2828, 2938-2954

Current architecture:

1. CLI bridge returns normalized rows.
2. `normalizeAnnotationExportRow()` creates `{ display, provenance, pdfLocation, raw }`.
3. `PaperForgeStatusView` owns session-only `_annotationState`, `_annotationUiState`, load sequence, and stale-renderable fallback.
4. `buildAnnotationListViewModel()` turns state into renderable rows, messages, filters, groups.
5. `main.js` renders DOM through Obsidian-style `createEl()` with stable `paperforge-annotation-*` classes.
6. Phase 7 navigation is row-local: page badge computes availability via `resolveAnnotationPdfTarget()` and `_openAnnotationPdf()` uses `workspace.openLinkText()` read-only.

Phase 8 overlay must extend this architecture, not bypass it.

### Fail-Closed Overlay Gate

Apply to all overlay attach/render paths:

```javascript
// Existing analog: resolveAnnotationPdfTarget()
if (!row) return { ok: false, path: null, reason: 'No annotation row provided.' };
if (!entry) return { ok: false, path: null, reason: 'No paper entry provided.' };
if (!pdfLoc) return { ok: false, path: null, reason: 'Annotation row has no PDF location data.' };
```

Required Phase 8 equivalents:

- no active paper key -> no overlay
- no confirmed PDF target -> no overlay
- no confirmed active PDF/viewer identity -> no overlay
- no usable page layer -> no overlay
- no usable `positionJson` / rects -> keep list row, no overlay mark
- invalid coordinate conversion -> skip that mark, not the whole list

### Event-Driven Refresh / Teardown

Use existing lifecycle points rather than continuous polling:

- active paper render calls annotation section near `main.js` line 2595
- annotation refresh uses `_handleAnnotationRefresh()` around `main.js` lines 2916-2930
- active paper state uses `_currentPaperKey`, `_currentPaperEntry`, `_currentFilePath`

Do not add continuous polling. A bounded `MutationObserver` for the PDF viewer is acceptable only if it is created during overlay attach and disconnected during `_clearAnnotationOverlay()`.

### DOM Safety

Copy these constraints:

- Use `createEl()` where available.
- Use `setText()` / `textContent` for selected text, comments, provenance.
- Use PaperForge-owned class names.
- Remove only PaperForge-owned overlay nodes.
- Never query-and-delete broad Obsidian/PDF viewer DOM.

### CSS Namespace

Existing namespace: `.paperforge-annotation-*`.

Phase 8 namespace: `.paperforge-annotation-overlay-*`.

Do not create selectors that target global PDF internals directly in CSS. Runtime may probe viewer DOM, but CSS should style only PaperForge-owned overlay elements.

## Anti-Patterns To Avoid

| Anti-pattern | Why it is prohibited | Safe alternative |
|---|---|---|
| Guessing Obsidian PDF internals by hard-coded broad selectors | Viewer DOM can change; false positives can corrupt unrelated panes | Spike first, attach only when identity/page layer can be confirmed |
| Global DOM pollution | Overlay nodes may leak across panes/files | Store overlay root/observer references and remove only `.paperforge-annotation-overlay-*` nodes |
| Continuous polling | Wasteful and brittle | Use active-file/paper render, annotation refresh, and bounded observer hooks |
| Breaking list/jump behavior | Phase 8 is enhancement only | Keep `_renderAnnotationSection()` and `_openAnnotationPdf()` independent |
| Writing Zotero/DB/plugin settings | Phase is read-only display | Consume normalized rows and session state only |
| Using `pageLabel` for coordinates | Labels are display text | Use `pdfLocation.pageIndex` and parsed position/selector data |
| Rendering supplemental annotations on main PDF by guesswork | Wrong source PDF is worse than no overlay | Reuse `resolveAnnotationPdfTarget()` identity guard |
| Showing raw DOM errors/JSON/stack traces in UI | Bad UX and leaks internals | Stable friendly status/reason strings |

## Planner Constraints

### Put These In `src/testable.js`

- overlay state default helper
- position/selector JSON parsing
- color normalization
- annotation row to overlay mark view-model
- PDF identity/page filtering
- coordinate conversion math that can be tested without live Obsidian
- popover data view-model
- stable fail-closed result shapes

### Keep These In `main.js`

- probing active Obsidian PDF viewer DOM
- attaching/removing overlay roots
- wiring `MutationObserver` or workspace events
- rendering mark elements and popovers
- lifecycle teardown on paper/file/viewer changes
- concise `Notice` or internal status updates

### Keep These In `styles.css`

- independent `SECTION 41 - PDF Annotation Overlay`
- `.paperforge-annotation-overlay-*` classes only
- semi-transparent highlight style
- focus-visible style
- read-only popover style
- no broad PDF viewer selectors

### Test Harness Requirements

- Pure helper tests should import from `../src/testable.js`.
- Runtime tests should reuse `Module._load` Obsidian stub and `PaperForgeStatusView` from `main.js.__test`.
- DOM tests should create fake viewer/page layers and verify attach/teardown.
- Regression tests must preserve page-badge jump, expand isolation, list rendering, and forbidden write/edit controls.

## No Analog Found

| File / Work Item | Role | Data Flow | Reason |
|---|---|---|---|
| Real Obsidian PDF viewer spike notes | docs / verification | manual runtime observation | Current code has no existing PDF overlay attachment point or live viewer DOM contract |

Planner should include a spike plan that documents the current observable PDF viewer DOM/hooks and records the chosen attachment point. If no reliable point exists, implement a disabled/fallback overlay state and tests for fail-closed behavior.

## Metadata

**Analog search scope:** `paperforge/plugin/main.js`, `paperforge/plugin/src/testable.js`, `paperforge/plugin/styles.css`, `paperforge/plugin/tests/*annotation*.mjs`, Phase 7 summaries, Phase 8 context.
**Files scanned:** 10 required files plus `AGENTS.md`.
**Pattern extraction date:** 2026-06-28.
