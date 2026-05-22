# Annotation UI Refresh & Tool Suite

> PaperForge PDF annotation overlay — redesigned for Zotero parity + macOS Preview feel

**Date:** 2026-05-20
**Branch:** `feat/pdf-annotation-layer`
**Status:** Draft

---

## 1. UX Design Research Summary

### macOS Preview (reference model)

| Pattern | Detail |
|---------|--------|
| **Persistent Markup Toolbar** | Top-of-viewer bar with tool buttons. Click a tool (Highlight becomes gray = active mode), then select text → auto-annotates. Click tool again to exit mode. |
| **Sticky Note** | Click Note button → cursor becomes crosshair → click anywhere on page → opens inline yellow note. |
| **Undo** | Cmd+Z standard system undo. No toast, no timeout. |
| **Delete** | Control-click annotation → "Remove Highlight" context menu. Or select in sidebar → Delete key. |
| **Highlights & Notes sidebar** | View > Highlights and Notes → sidebar lists every annotation with text, author, date. Click navigates to page. |

### Zotero PDF Reader (feature parity target)

| Pattern | Detail |
|---------|--------|
| **Unlocked mode** | Nothing selected in toolbar. Select text → popup appears near cursor with color swatches → click color → creates highlight/underline. |
| **Locked mode** | Click highlight/underline tool → pick color. Then every text selection auto-creates annotation with that color. |
| **Annotation toolbar** | Highlight | Underline | Sticky Note | Select Area | Color picker. Persistent top bar. |
| **Sticky Note** | Click tool → click page → places note + opens comment. |
| **Annotations sidebar** | Left sidebar showing all annotations sorted by page. Click annotation → "Show on Page" navigates. |
| **Color palette** | 8 colors: yellow, red, green, blue, purple, magenta, orange, gray. |

### PaperForge Design Decision

**Hybrid: Preview-style persistent toolbar + Zotero-style color popup.** The toolbar stays docked at top of PDF viewer (like Preview Markup). Default mode is Zotero's "unlocked" — select text, see color/type popup near cursor. Clicking a tool in toolbar enters "locked" mode — every selection auto-applies.

---

## 2. Persistent Annotation Toolbar

### 2.1 Layout

Docked at the TOP of `.pdf-viewer-container`, above the PDF content. Always visible when a PDF is open with annotations.

```
┌── PDF Viewer ───────────────────────────────────────────────────────┐
│  [◀] [_undoRedo]  [🖍 Highlight] [T̲ Underline] [📝 Note] [✎ Text]  │  [⬤ yellow] [⋮] │
│                                                                      │
│  ── separator ──                                                     │
│                                                                      │
│  PDF content area                                                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Elements (left to right):**
1. **`[◀]`** — Back navigation button. Hidden when no navigation history exists.
2. **`undoRedo`** — Undo (↩) + Redo (↪). Disabled states when stack is empty.
3. **`[Highlight]`** — Tool button. Active state = blue highlight (enters locked mode).
4. **`[Underline]`** — Tool button. Active state = blue highlight.
5. **`[Note]`** — Tool button. Active = cursor becomes crosshair for page-click placement.
6. **`[Text]`** — Tool button. Active = crosshair placement.
7. **`[⬤ yellow]`** — Color indicator. Shows current color. Click opens 8-color palette popup.
8. **`[⋮]`** — More menu: Dashboard toggle, Export annotations, Import from Zotero.

### 2.2 State

```javascript
let _annotationToolMode = null;  // null (unlocked), 'highlight', 'underline', 'note', 'text'
let _currentAnnotationColor = '#ffd400';  // persists across sessions via plugin settings

// Undo system — behaves like standard editor undo
let _undoStack = [];     // [{action:'create'|'delete', ann, pageNum}], max 50
let _redoStack = [];     // [{same}]
// On create: clear redo, push to undo. On delete: push to undo, clear redo.
// On undo: pop undo → push redo → execute reverse action.
// On redo: pop redo → push undo → execute original action.
// Cull limit: if _undoStack.length > 50, shift oldest entries and commit those subprocesses.

// Toolbar DOM
let _annotationToolbarEl = null;
let _annotationToolBtns = [];  // references to each tool button
```

### 2.3 Behavior

**Unlocked mode** (`_annotationToolMode === null`, default):
- User selects text → popup appears near cursor: `<color swatches 1-8>`
- Click color → creates annotation with `type='highlight'` and that color
- Click outside popup → popup closes, selection stays

**Locked mode** (`_annotationToolMode === 'highlight'` or `'underline'`):
- User selects text → annotation auto-created with current mode + color
- No popup appears
- Same behavior as Zotero's locked mode

**Click-to-place mode** (`_annotationToolMode === 'note'` or `'text'`):
- Cursor changes to crosshair over PDF
- Click on page → creates annotation at click point (24pt × 24pt default rect)
- Immediately opens popover with comment textarea
- After creation, mode resets to unlocked (single-shot)

**Color palette popup** (click `[⬤ color]`):
- 8 colored circles in a horizontal or 2×4 grid
- Click a color → update `_currentAnnotationColor`, close palette
- Palette persists across tool modes

---

## 3. Annotation Popover Redesign

### 3.1 Layout

Appears on clicking a rendered annotation rect. Uses fixed positioning anchored near the rect.

```
┌───────────────────────────────┐
│ ⬤ yellow  highlight · page 3 │  ← type + color dot + page
│                               │
│ "The selected text that       │
│  was highlighted appears      │  ← scrollable if > 3 lines
│  here with context..."        │
│                               │
│ ┌─────────────────────────┐   │
│ │ Comment (editable)      │   │  ← textarea, initially collapsed
│ └─────────────────────────┘   │
│                               │
│ tags: #important #result      │  ← click tags to filter
│                               │
│ [↩ Copy] [✕ Delete] [⋮]     │  ← action buttons
└───────────────────────────────┘
```

### 3.2 Actions

| Button | Action |
|--------|--------|
| Copy | Copy selected text to clipboard (no subprocess) |
| Delete | Instant: remove rect DOM + push to undo stack + fire subprocess (no confirm) |
| ⋮ | Menu: Edit comment, Change color, Add tag |

### 3.3 Delete Flow (no confirm)

```
User clicks "✕ Delete" in popover
  → 1. Hide popover immediately
  → 2. Remove rect from DOM (fade-out transition 200ms)
  → 3. Push {action:'delete', ann} to _undoStack (clears _redoStack)
  → 4. _removeAnnotationFromMemory(ann.id)
  → 5. fire deleteLocalAnnotation() subprocess in background
  → 6. On success: _scheduleAnnotationCacheFlush()
  → 7. On failure: re-push ann to memory + re-render (undo handles this case)
```

### 3.4 Undo Flow

```
User clicks ↩ (undo) in toolbar
  → Pop last item from _undoStack
  → If action is 'delete':
      push {action:'undelete', ann} to _redoStack
      _appendAnnotationToMemory(ann)
      _removeAnnotationRectsFromDom(ann.id)  // remove old rects if any
      _renderAnnotationToPage(ann, ...)
      fire createLocalAnnotation() subprocess in background
  → If action is 'create':
      push {action:'uncreate', ann} to _redoStack
      _removeAnnotationRectsFromDom(ann.id)
      _removeAnnotationFromMemory(ann.id)
      fire deleteLocalAnnotation() subprocess
  → After each undo: _scheduleAnnotationCacheFlush()
```

---

## 4. Annotation Sidebar (Replaces Dashboard)

### 4.1 Layout

Toggle via `[⋮]` menu → "Toggle Sidebar" or ribbon icon. Opens as a right-side panel within the PDF viewer leaf.

```
┌── Annotation Sidebar ──────────── 280px ──┐
│  Annotations (35)                [✕]      │
│                                             │
│  📊 35 highlights  2 notes                 │
│                                              │
│  ── By Page ──                              │
│  Page 1  ████████████ 12                    │
│  Page 2  ██████ 6                           │
│  Page 3  ████████████████████ 23            │
│  ...                                         │
│                                              │
│  ── Recent ──                                │
│  + "electric field stimulation..."  p.2     │
│  - "biomaterial scaffolds..."  p.5          │
│  + Note "Important finding"  p.3            │
│                                              │
│  ── All Annotations ──                       │
│  ▸ Page 1 (12)                               │
│  ▸ Page 2 (6)                                │
│  ▸ Page 3 (23)  ← expanded                   │
│    ⬤ "Advances in electrical..."  ¶1         │
│    ⬤ "The piezoelectric effect..."  ¶2       │
│    ⬤ "Bone regeneration requires..."  ¶3     │
│    ...                                        │
│                                              │
│  [Export JSON]  [Import Zotero]             │
└──────────────────────────────────────────────┘
```

### 4.2 Features

- **Page bars**: horizontal CSS-bar chart, click a bar → navigate to that page
- **Expandable page sections**: click page header → shows annotation list for that page
- **Click annotation in list** → navigate to page + highlight rect with a brief flash animation
- **Export JSON** → `paperforge annotation export --json` subprocess
- **Import Zotero** → `paperforge annotation import` subprocess
- **Recently created/deleted** list from `_undoStack` entries marked with action type

---

## 5. PDF Back-Navigation

### 5.1 Trigger

PDF.js fires `pagechanging` event when:
- User clicks internal hyperlink / cross-reference
- User clicks outline item
- Programmatic page change

### 5.2 Stack Model

```javascript
let _pdfNavStack = [];  // [{pageNumber, scrollY, scale}]
let _pdfNavPos = -1;    // current position in stack (not always length-1 after back)
```

### 5.3 Behavior

```
On PDF open: push {pageNumber: initial, scrollY: 0, scale: 1}
On pagechanging event (source IS linkService or outline):
  → If current page != event pageNumber:
      push current {pageNumber, scrollY, scale} to stack
      advance _pdfNavPos
      trim any entries after _pdfNavPos (like browser history)
      show [◀] button

Click [◀]:
  → _pdfNavPos--
  → navigate to stack[_pdfNavPos].pageNumber + scrollY
  → enable [▶] forward button
  → if _pdfNavPos === 0: hide [◀]

Click [▶]:
  → _pdfNavPos++
  → navigate
  → if _pdfNavPos === stack.length - 1: hide [▶]

Stack cap: 100 entries. Oldest evicted.
```

---

## 6. Implementation Plan (Phased)

### Phase A: Persistent Toolbar + Locked Mode (core UI)
**Files:** `main.js` (~150 lines new), `styles.css` (~80 lines new)
1. Create toolbar DOM element, inject into `.pdf-viewer-container`
2. Tool buttons: Highlight, Underline, Note, Text with active state toggle
3. `_annotationToolMode` state + locked/unlocked behavior
4. Color palette popup from `[⬤]` button
5. Tests: toolbar DOM structure, mode state transitions

### Phase B: Undo/Redo System
**Files:** `main.js` (~100 lines)
1. `_undoStack` / `_redoStack` with 50-entry cap
2. Undo/Redo buttons in toolbar
3. Undo/Redo action dispatch (create ↔ delete)
4. Stack culling: commit oldest entries every 10 new ops
5. Tests: undo re-renders rect, redo restores, cap enforcement

### Phase C: Popover Redesign (no-confirm delete)
**Files:** `main.js` (~60 lines), `styles.css` (~40 lines)
1. Remove `confirm()` from delete path
2. Add fade-out transition on rect removal
3. Add Copy button to popover
4. Add ⋮ menu with Edit comment / Change color
5. Tests: delete flow, undo after delete

### Phase D: Annotation Sidebar
**Files:** `main.js` (~200 lines), `styles.css` (~150 lines)
1. Sidebar panel DOM template
2. Toggle via ⋮ menu + ribbon icon
3. Page bar chart from `getGroupedAnnotationsForCurrentPaper()`
4. Expandable per-page annotation lists
5. Click-to-navigate on annotation list items
6. Export/Import buttons
7. Tests: sidebar open/close, bar chart rendering, navigation

### Phase E: PDF Back-Navigation
**Files:** `main.js` (~80 lines)
1. `_pdfNavStack` + `_pdfNavPos` state
2. Hook `pagechanging` event for link-driven navigation
3. Back/Forward buttons in toolbar
4. Stock cap + eviction
5. Tests: nav push/pop, button visibility, stack overflow

---

## 7. Rules & Constraints

1. No new Python dependencies. All subprocess calls use existing CLI.
2. No new npm dependencies. Use inline SVG for icons. No icon library.
3. All CSS uses `--background-*` and `--text-*` Obsidian variables. No hardcoded colors for theme.
4. Sidebar must not break Obsidian's native PDF sidebar (thumbnails/outline). Use CSS containment.
5. Toolbar height ≤ 40px to avoid pushing PDF content down significantly.
6. All annotations rendered MUST have `data-annotation-id` attribute for delete targeting.
