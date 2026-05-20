# Annotation Interaction Polish — Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 UX gaps: popover no-confirm delete, undo on delete, PDF back-navigation, create/delete cache visibility.

**Architecture:** All changes in `paperforge/plugin/main.js` only. No new files. No CLI changes. Each fix is self-contained.

**Tech Stack:** vanilla JS (Obsidian plugin), existing PDF.js event hooks, existing `_undoStack`/`_renderAnnotationToPage` infrastructure.

---

## Task 1: Popover — Remove Confirm Guard

**Files:**
- Modify: `paperforge/plugin/main.js` around line 1299

- [ ] **Step 1: Remove the confirm() guard**

In `showAnnotationPopover`, find:
```javascript
if (!confirm('Delete this annotation?')) return;
```
Replace with nothing (just let the delete proceed).

- [ ] **Step 2: Verify via plugin tests**

Run: `cd paperforge/plugin && npx vitest run`
Expected: 129 tests pass (no confirm-related tests)

- [ ] **Step 3: Commit**

```bash
git add paperforge/plugin/main.js
git commit -m "feat: remove confirm dialog from annotation delete"
```

---

## Task 2: Create/Delete — Remove Stale `_refreshOverlays()`

**Files:**
- Modify: `paperforge/plugin/main.js` create success callback and delete success callback

- [ ] **Step 1: Find and inspect the two callbacks**

In `main.js`, locate:
1. The `createLocalAnnotation(...).then(...)` success handler (contains `_refreshOverlays()`)
2. The `deleteLocalAnnotation(...).then(...)` success handler (contains `_refreshOverlays()`)

- [ ] **Step 2: Remove `_refreshOverlays()` from create success**

In the create success handler, remove the line `_refreshOverlays();`.
The single annotation is already rendered via `_renderAnnotationToPage(result.data)`.

- [ ] **Step 3: Remove `_refreshOverlays()` from delete success**

In the delete success handler, remove the line `_refreshOverlays();`.
The rects are already removed via `_removeAnnotationRectsFromDom(annotationId)`.

- [ ] **Step 4: Verify via plugin tests**

Run: `cd paperforge/plugin && npx vitest run`
Expected: 129 tests pass

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js
git commit -m "fix: remove stale _refreshOverlays from create/delete success handlers"
```

---

## Task 3: PDF Back-Navigation

**Files:**
- Modify: `paperforge/plugin/main.js` — add nav stack, hook pagechanging, render floating back button

- [ ] **Step 1: Add nav stack module-level variables**

Near other module-level state (after `_currentVaultPath`, `_currentPdfPath`):
```javascript
let _pdfNavStack = [];
let _pdfNavPos = -1;
let _pdfNavBackEl = null;
let _pdfNavForwardEl = null;
```

- [ ] **Step 2: Add `_pushPdfNav` and `_renderPdfNavButtons` helpers**

```javascript
function _pushPdfNav(pageNumber) {
    // Truncate forward history if not at top
    if (_pdfNavPos < _pdfNavStack.length - 1) {
        _pdfNavStack = _pdfNavStack.slice(0, _pdfNavPos + 1);
    }
    _pdfNavStack.push(pageNumber);
    if (_pdfNavStack.length > 100) _pdfNavStack.shift();
    _pdfNavPos = _pdfNavStack.length - 1;
    _renderPdfNavButtons();
}

function _renderPdfNavButtons() {
    // Remove existing buttons
    if (_pdfNavBackEl) { _pdfNavBackEl.remove(); _pdfNavBackEl = null; }
    if (_pdfNavForwardEl) { _pdfNavForwardEl.remove(); _pdfNavForwardEl = null; }
    if (_pdfNavPos < 0) return;
    var container = document.querySelector('.pdf-viewer-container');
    if (!container) return;
    // Back button (show if pos > 0)
    if (_pdfNavPos > 0) {
        _pdfNavBackEl = document.createElement('button');
        _pdfNavBackEl.className = 'pf-nav-btn pf-nav-back';
        _pdfNavBackEl.textContent = '\u25C0';
        _pdfNavBackEl.title = 'Back to page ' + _pdfNavStack[_pdfNavPos - 1];
        _pdfNavBackEl.addEventListener('click', function () {
            if (_pdfNavPos <= 0 || !_pdfInternalHandle) return;
            _pdfNavPos--;
            _pdfInternalHandle.scrollPageIntoView({ pageNumber: _pdfNavStack[_pdfNavPos] });
            _renderPdfNavButtons();
        });
        container.appendChild(_pdfNavBackEl);
    }
    // Forward button (show if pos < stack.length - 1)
    if (_pdfNavPos < _pdfNavStack.length - 1) {
        _pdfNavForwardEl = document.createElement('button');
        _pdfNavForwardEl.className = 'pf-nav-btn pf-nav-forward';
        _pdfNavForwardEl.textContent = '\u25B6';
        _pdfNavForwardEl.title = 'Forward to page ' + _pdfNavStack[_pdfNavPos + 1];
        _pdfNavForwardEl.addEventListener('click', function () {
            if (_pdfNavPos >= _pdfNavStack.length - 1 || !_pdfInternalHandle) return;
            _pdfNavPos++;
            _pdfInternalHandle.scrollPageIntoView({ pageNumber: _pdfNavStack[_pdfNavPos] });
            _renderPdfNavButtons();
        });
        container.appendChild(_pdfNavForwardEl);
    }
}
```

- [ ] **Step 3: Hook pagechanging in injectPdfEventHooks**

In the `pagerendered` event handler (within `injectPdfEventHooks`), add a `pagechanging` subscription. But we need to only push when the page JUMP is significant (not scrolling):

Actually, the `pagechanging` event fires on any page change. We only want to push when it's a LINK-driven jump. Simplest approach: push on EVERY page change (including scrolling one page at a time). The user just cares about being able to go back.

Better approach: track `_lastNavPage` and only push when the jump is > 1 page:
```javascript
// Inside injectPdfEventHooks, before the pagerendered handler:
var _lastNavPage = null;
handle.eventBus.on('pagechanging', function (evt) {
    if (_lastNavPage !== null && Math.abs(evt.pageNumber - _lastNavPage) > 1) {
        _pushPdfNav(_lastNavPage);
    }
    _lastNavPage = evt.pageNumber;
});
```

- [ ] **Step 4: Reset nav stack on new PDF**

In `injectPdfEventHooks`, before setting up event hooks:
```javascript
_pdfNavStack = [];
_pdfNavPos = -1;
if (_pdfNavBackEl) { _pdfNavBackEl.remove(); _pdfNavBackEl = null; }
if (_pdfNavForwardEl) { _pdfNavForwardEl.remove(); _pdfNavForwardEl = null; }
```

- [ ] **Step 5: Add CSS for nav buttons**

In `styles.css`:
```css
.pf-nav-btn {
    position: absolute;
    top: 8px; z-index: 100;
    background: var(--background-primary);
    border: 1px solid var(--background-modifier-border);
    border-radius: 4px; color: var(--text-muted);
    cursor: pointer; padding: 4px 8px; font-size: 14px;
    opacity: 0.6; transition: opacity 0.15s;
}
.pf-nav-btn:hover { opacity: 1; }
.pf-nav-back { left: 8px; }
.pf-nav-forward { left: 40px; }
```

- [ ] **Step 6: Verify manually**

Open a PDF with internal TOC links. Click a TOC entry that jumps to page 10. Verify back button appears. Click it — returns to page 1.

- [ ] **Step 7: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/styles.css
git commit -m "feat: add PDF back/forward navigation buttons"
```

---

## Task 4: Undo on Delete

**Files:**
- Modify: `paperforge/plugin/main.js` — push undo entry on delete, render undo pill, restore on click

- [ ] **Step 1: Add undo pill rendering helper**

```javascript
let _undoPillEl = null;
let _undoTimer = null;

function _showUndoPill(undoEntry) {
    if (_undoPillEl) _undoPillEl.remove();
    if (_undoTimer) clearTimeout(_undoTimer);
    _undoPillEl = document.createElement('div');
    _undoPillEl.className = 'pf-undo-pill';
    _undoPillEl.innerHTML = '<span>Annotation deleted</span> <button>Undo</button>';
    _undoPillEl.querySelector('button').addEventListener('click', function () {
        // Restore: re-append to memory, render to page, schedule cache flush
        _appendAnnotationToMemory(undoEntry.annotation);
        _renderAnnotationToPage(undoEntry.annotation);
        // Re-create via subprocess
        createLocalAnnotation(undoEntry.vaultPath, undoEntry.pdfPath, {
            type: undoEntry.annotation.type,
            page_index: undoEntry.annotation.page_index,
            page_label: undoEntry.annotation.page_label || '',
            selected_text: undoEntry.annotation.selected_text || '',
            comment: undoEntry.annotation.comment || '',
            color: undoEntry.annotation.color || '#ffd400',
            position_json: JSON.stringify(undoEntry.annotation.position),
        }).then(function () {
            _scheduleAnnotationCacheFlush(undoEntry.vaultPath);
        });
        _undoPillEl.remove();
        _undoPillEl = null;
    });
    // Find PDF viewer container
    var container = document.querySelector('.pdf-viewer-container');
    if (container) container.appendChild(_undoPillEl);
    // Auto-hide after 8s
    _undoTimer = setTimeout(function () {
        if (_undoPillEl) { _undoPillEl.remove(); _undoPillEl = null; }
    }, 8000);
}
```

- [ ] **Step 2: Push undo entry on delete**

In the delete button handler (inside `showAnnotationPopover`), before calling `deleteLocalAnnotation`:
```javascript
// Snapshot annotation for undo
_showUndoPill({
    annotation: JSON.parse(JSON.stringify(ann)),  // deep copy
    vaultPath: vaultPath,
    pdfPath: pdfPath,
});
```

- [ ] **Step 3: Add CSS for undo pill**

In `styles.css`:
```css
.pf-undo-pill {
    position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%);
    z-index: 100; background: var(--background-primary);
    border: 1px solid var(--background-modifier-border);
    border-radius: 6px; padding: 6px 14px; font-size: 13px;
    display: flex; gap: 12px; align-items: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.pf-undo-pill button {
    background: none; border: none; color: var(--text-accent);
    cursor: pointer; font-weight: 600; padding: 0;
}
```

- [ ] **Step 4: Verify manually**

Open a PDF. Delete an annotation. Verify undo pill appears at bottom-center. Click Undo — annotation reappears.

- [ ] **Step 5: Commit**

```bash
git add paperforge/plugin/main.js paperforge/plugin/styles.css
git commit -m "feat: add undo on annotation delete"
```

---

## Task 5: Full Verification

- [ ] **Step 1: Run plugin tests**

```bash
cd paperforge/plugin && npx vitest run
```
Expected: 129 tests pass

- [ ] **Step 2: Run Python tests**

```bash
python -m pytest tests/unit/annotation/ tests/cli/ -v --tb=short
```
Expected: all pass

- [ ] **Step 3: Sync to vault and manually test**

Copy `main.js` + `styles.css` to `D:\L\OB\Literature-hub\.obsidian\plugins\paperforge\`.
Reload Obsidian. Open a PDF. Test: delete annotation (no confirm), undo pill appears and works, back button on link jump works, create new annotation persists.

- [ ] **Step 4: Commit any remaining fixes**

```bash
git add -A && git commit -m "chore: final verification adjustments"
```
