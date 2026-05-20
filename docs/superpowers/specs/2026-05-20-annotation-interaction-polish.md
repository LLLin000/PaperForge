# Annotation Interaction Polish: Popover, Undo, Back-Nav, Cache

> **Scope**: fix the 4 known UX gaps in the PDF annotation overlay (popover, undo, back-nav, cache visibility). No new architecture. No toolbar redesign. All within existing `main.js` paths.

---

## 1. Popover — Remove Confirm, Instant Delete

**Current**: `confirm('Delete this annotation?')` blocks the delete. Ugly.

**Target**: click trash → annotation disappears immediately from DOM + memory → subprocess fires in background → cache flush debounced. No dialog.

**Change**: in `showAnnotationPopover`, line 1299 — remove the `if (!confirm(...)) return;` guard. Delete is always instant.

---

## 2. Undo After Delete

**Current**: undo stack infrastructure exists (`_undoStack`, `_undoPos`) but is not wired into delete.

**Target**: delete pushes an undo entry. Floating "Undo" button appears at bottom of viewport. Click restores the annotation. Same underlying subprocess (delete → insert). Undo entries expire on next PDF close or after 50 stack entries.

**Storage**: undo stack object `{ action: 'delete', annotation: <snapshot>, pageIndex: N }`.

**Rendering**: undo button is a floating pill: `[ ↩ Undo ]` at bottom-center, auto-hides after 8 seconds of inactivity.

---

## 3. Back Button for PDF Link Navigation

**Current**: clicking internal PDF links (TOC, citations, cross-references) navigates to another page with no way back.

**Target**: floating `[ ◀ ]` button at top-left when navigation history exists. Click → return to previous page.

**Implementation**:
- `_pdfNavStack = []`, `_pdfNavPos = -1`
- Hook `pagechanging` event: if navigating to a non-adjacent page (|Δ| > 1), push current page to stack
- Back button pops stack, calls `handle.scrollPageIntoView({ pageNumber: N })`
- Forward button appears when not at top of stack (`_pdfNavPos < _pdfNavStack.length - 1`)
- Stack cap: 100

---

## 4. Create/Delete Cache Visibility

**Root cause**: after create/delete subprocess succeeds, `_refreshOverlays()` re-reads the JSON cache file. But the cache hasn't been flushed yet (`--defer-cache-refresh` delays the `annotation cache-refresh` subprocess by 700ms). So `_refreshOverlays()` reads the OLD cache and the new annotation disappears.

**Fix**: remove `_refreshOverlays()` from create and delete success callbacks. The single annotation is already rendered/removed via `_renderAnnotationToPage()` / `_removeAnnotationRectsFromDom()`. The cache flush (700ms debounce) handles persistence. On next PDF open, the full cache is read correctly.

---

## Implementation Order

1. **Popover no-confirm** — 1 line change, test immediately
2. **Create/delete cache** — remove `_refreshOverlays()` from 2 callbacks, test create + delete
3. **Back nav** — add `_pdfNavStack`, hook pagechanging, render floating button
4. **Undo on delete** — push snapshot to undo stack, show undo pill, restore flow
