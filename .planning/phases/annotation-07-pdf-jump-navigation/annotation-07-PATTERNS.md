# Annotation Phase 7: PDF Jump Navigation - Pattern Map

**Mapped:** 2026-06-21
**Files analyzed:** 7 new/modified files
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `paperforge/plugin/main.js` | component/controller | event-driven, request-response | paper status PDF opener and `_renderAnnotationRows()` in the same file | exact |
| `paperforge/plugin/src/testable.js` | utility | transform | annotation list helpers mirrored into `main.js` | exact |
| `paperforge/plugin/styles.css` | component styling | event-driven UI | existing page-badge and expand-button rules | exact |
| `paperforge/plugin/tests/annotation-section-dom.test.mjs` | test | event-driven DOM | existing page badge and independent expand-control tests | exact |
| `paperforge/plugin/tests/annotation-main-runtime.test.mjs` | test | request-response | existing Obsidian vault/workspace runtime harness | exact |
| `paperforge/plugin/tests/annotation-bridge.test.mjs` | test | transform | `pdfLocation` normalization assertions | role-match |
| `paperforge/plugin/tests/annotation-list-view-model.test.mjs` (or equivalent helper test file selected by planner) | test | transform | pure helper tests exported from `src/testable.js` | role-match |

## Pattern Assignments

### `paperforge/plugin/main.js` (component/controller, event-driven + request-response)

**Primary analogs:** `paperforge/plugin/main.js:2359-2370`, `paperforge/plugin/main.js:2518-2573`

**Imports/runtime pattern** (`main.js:1-5`):

```javascript
const { Plugin, Notice, ItemView, Modal, Setting, PluginSettingTab, addIcon } = require('obsidian');
const { exec, execFile, spawn, execFileSync } = require('node:child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');
```

Use the existing `Notice` import for friendly failures. Do not add filesystem opening or shell execution for navigation.

**Canonical PDF opening pattern** (`main.js:2359-2370`):

```javascript
if (entry.pdf_path) {
    const pathMatch = entry.pdf_path.match(/\[\[([^\]]+)\]\]/);
    const targetPath = pathMatch ? pathMatch[1] : entry.pdf_path;
    const file = this.app.vault.getAbstractFileByPath(targetPath);
    if (file) { this.app.workspace.openLinkText(targetPath, ''); }
}
```

Copy the vault-relative wikilink extraction, `getAbstractFileByPath()` existence check, and `workspace.openLinkText()` behavior. Keep the second argument `''` so navigation follows PaperForge's current Obsidian behavior. Extend the link text with the supported PDF page fragment only after the underlying PDF path has been confidently resolved.

**Page badge and separate expand control** (`main.js:2518-2573`):

```javascript
var isExpanded = this._annotationUiState.expandedIds.indexOf(identity) !== -1;
if (isExpanded) rowEl.addClass('expanded');

var pageBadge = rowEl.createEl('span', {
    cls: 'paperforge-annotation-page-badge',
    text: String(display.pageLabel || display.page || '?')
});

var expandBtn = rowEl.createEl('button', {
    cls: 'paperforge-annotation-expand-btn clickable-icon'
});
expandBtn.addEventListener('click', function () {
    self._annotationUiState = toggleAnnotationExpansion(self._annotationUiState, identity);
    self._renderPaperMode();
});
```

Change the badge itself to a semantic `button`, with `title` and `aria-label`, and bind navigation only to that button. Preserve the existing expand listener as a distinct event path. Do not add a row click handler.

**Normalized navigation inputs** (`main.js:356-390`):

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

Use `pdfLocation.sourceAttachmentKey` for attachment identity and `pdfLocation.pageIndex` for arithmetic. A valid non-negative integer maps to `pageIndex + 1`; never derive the target from `pageLabel`.

**Error/degradation pattern** (`main.js:448-516`):

```javascript
try {
    parsed = JSON.parse(subprocessResult.stdout);
} catch {
    return makeAnnotationState(ANNOTATION_LOAD_STATES.INVALID_JSON, {
        paperKey,
        message: 'Could not read the annotation data for this paper.',
        errorCode: null,
        raw: { stdout: subprocessResult.stdout, stderr: subprocessResult.stderr },
    });
}
```

The runtime convention separates a concise user message from diagnostic detail. For navigation, catch page-target failures, retry the confirmed plain PDF path, and show a short `Notice`. If attachment resolution is uncertain, show a short notice and do not call `openLinkText()`.

### `paperforge/plugin/src/testable.js` (utility, transform)

**Analog:** mirrored annotation helpers in `src/testable.js:237-271`, `main.js:356-390`, with exports at `src/testable.js:1128-1160`.

**Pure helper pattern** (`src/testable.js:658-705`):

```javascript
function getAnnotationIdentity(row) {
    if (!row) return '';
    const p = row.provenance || {};
    const loc = row.pdfLocation || {};
    if (p.sourceAnnotationKey) return String(p.sourceAnnotationKey);
    if (loc.rowId) return String(loc.rowId);
    return '';
}

function sortAnnotationsForReadingOrder(rows) {
    if (!Array.isArray(rows)) return [];
    const copy = rows.slice();
    copy.sort((a, b) => {
        const pageA = (a && a.pdfLocation || {}).pageIndex;
        const pageB = (b && b.pdfLocation || {}).pageIndex;
        return pageA - pageB;
    });
    return copy;
}
```

Add side-effect-free helpers that accept annotation location plus current paper metadata and return an explicit result such as `{ ok, path, page, reason }`. Avoid passing `app`, `vault`, or `workspace` into pure helpers.

**Mirroring contract:** implement equivalent helper logic in both `src/testable.js` and the inlined helper section of `main.js`. The source version may use modern syntax; the bundled runtime follows the file's existing conservative `var`/function style where applicable. Export every new helper from `src/testable.js` and expose it through `main.js.__test` only if runtime tests need direct access.

**Export pattern** (`src/testable.js:1128-1160`):

```javascript
module.exports = {
    // Annotation bridge
    normalizeAnnotationExportRow,
    // Annotation list view-model helpers
    getAnnotationIdentity,
    toggleAnnotationExpansion,
    buildAnnotationListViewModel,
};
```

### `paperforge/plugin/styles.css` (component styling, event-driven UI)

**Analog:** `styles.css:2608-2620`, `styles.css:2691-2712`.

```css
.paperforge-annotation-page-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 22px;
    padding: 1px 5px;
}

.paperforge-annotation-expand-btn {
    width: 20px;
    height: 20px;
    padding: 0;
    cursor: pointer;
    background: transparent;
}

.paperforge-annotation-expand-btn:hover {
    background: var(--background-modifier-hover);
    color: var(--text-normal);
}
```

Retain the compact badge dimensions. Add button reset, hover, focus-visible, and disabled/unavailable states under the existing badge class. Do not merge badge and expand selectors in a way that obscures their separate semantics.

### `paperforge/plugin/tests/annotation-section-dom.test.mjs` (test, event-driven DOM)

**Analog:** `annotation-section-dom.test.mjs:27-53`, `:65-104`, `:296-361`.

```javascript
const badge = row.querySelector('.paperforge-annotation-page-badge');
expect(badge).toBeTruthy();
expect(badge.textContent).toBeTruthy();

const expandBtn = view._contentEl.querySelector('.paperforge-annotation-expand-btn');
expect(expandBtn).toBeTruthy();
expect(expandBtn.tagName).toBe('BUTTON');
```

Update this contract to require `badge.tagName === 'BUTTON'`, tooltip, accessible label, and disabled semantics where resolution cannot be established. Add click-isolation assertions: badge click leaves `expandedIds` unchanged; expand click leaves `workspace.openLinkText` untouched.

The DOM helper already supports `title` and arbitrary `attr` (`:65-90`), so use the existing `createEl()` harness rather than a new DOM abstraction.

### `paperforge/plugin/tests/annotation-main-runtime.test.mjs` (test, request-response)

**Analog:** `annotation-main-runtime.test.mjs:26-53`, `:172-247`, `:494-505`, `:541-602`.

```javascript
function makeStubApp() {
    return {
        vault: {
            getAbstractFileByPath: vi.fn(() => null),
        },
        workspace: {
            getActiveFile: vi.fn(() => ({ path: 'Paper.md' })),
            openLinkText: vi.fn(),
        },
    };
}
```

Parameterize `makeStubApp()` or override these spies per test. Cover:

- confirmed attachment + valid zero-based page opens the expected vault path/page;
- valid PDF + invalid/missing page opens the plain PDF and notices;
- page-target open rejection retries the plain PDF and notices;
- unmatched specific attachment performs no open and notices;
- badge navigation does not alter `_annotationUiState`, filters, grouping, or expansion;
- expand/refresh controls do not invoke PDF navigation.

Replace the Phase 6 forbidden-navigation assertion at `:590-602` intentionally; keep the edit/delete/write-back prohibitions.

### `paperforge/plugin/tests/annotation-bridge.test.mjs` (test, transform)

**Analog:** `annotation-bridge.test.mjs:184-231`.

```javascript
expect(result.provenance.sourceAttachmentKey).toBe('ATTACH_A');
expect(result.pdfLocation.pageIndex).toBe(2);
expect(result.pdfLocation.pageLabel).toBe('3');
expect(result.pdfLocation.sourceAttachmentKey).toBe('ATTACH_A');
```

Preserve these contracts. Add edge cases only if normalization changes: `pageIndex` zero, null, negative, non-integer, and attachment-key absence. Navigation conversion belongs in the pure helper tests, not normalization tests.

### Pure navigation helper tests (test, transform)

**Analog:** helpers exported from `src/testable.js:1128-1160` and imported with `await import('../src/testable.js')` in existing tests.

Test the result object rather than Obsidian APIs. Include exact attachment match, identity mismatch with no unsafe main-PDF fallback, no-identity/single-candidate fallback, ambiguous candidates, wikilink extraction, and `pageIndex + 1` conversion.

## Shared Patterns

### Vault-relative path contract

**Sources:** `paperforge/adapters/zotero_paths.py:7-38`, `paperforge/pdf_resolver.py:16-68`.

```python
relative = absolute_path.relative_to(vault_dir)
return f"[[{relative.as_posix()}]]"
```

```python
vault_candidate = (vault_root / raw.replace("/", os.sep)).resolve()
if is_valid_pdf(vault_candidate):
    return str(vault_candidate)
```

The plugin should consume canonical vault-relative `pdf_path`/supplementary metadata, not recreate Python's absolute/junction/storage resolution and not open raw external Zotero paths.

### Workspace opening seam

**Source:** `main.js:2364-2367`; **tests:** both runtime harnesses at `annotation-section-dom.test.mjs:156-175` and `annotation-main-runtime.test.mjs:172-191`.

Apply `vault.getAbstractFileByPath(targetPath)` before `workspace.openLinkText(targetPath, '')`. Keep these two methods injectable through the existing app stub.

### Friendly errors and read-only behavior

Use `Notice` for user feedback and keep diagnostics out of notice text. Navigation must not call `fileManager.processFrontMatter`, subprocess helpers, filesystem writers, or annotation mutation paths.

### UI state isolation

Expansion is immutable and session-local (`main.js:762-775`; `src/testable.js:906-918`). Navigation should not rerender the annotation section or modify `_annotationUiState`; only the existing expand listener calls `toggleAnnotationExpansion()`.

## No Analog Found

| Concern | Reason / planner action |
|---|---|
| Attachment-key-to-candidate matching | No existing JavaScript helper maps `sourceAttachmentKey` to canonical `pdf_path`/supplementary candidates. Define a conservative pure resolver from actual entry fields; if metadata cannot prove identity, return unavailable instead of guessing. |
| Exact Obsidian PDF page fragment fallback | Existing code opens plain vault paths only. Confirm the supported page-link form during planning, keep it isolated in a helper, and retain plain-PDF retry behavior. |

## Metadata

**Analog search scope:** `paperforge/plugin`, `paperforge/adapters`, `paperforge/pdf_resolver.py`, Annotation Phase 6 artifacts

**Files scanned:** 9 canonical source/test files plus phase context and repository `AGENTS.md`

**Excluded:** `.planning/phases/07-zotero-pdf-metadata-state-repair` and unrelated files

**Pattern extraction date:** 2026-06-21
