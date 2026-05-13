# Dashboard Copy Interaction + Per-Paper Metadata Enhancement

> **Status:** Spec complete, awaiting implementation
> **Date:** 2026-05-14
> **Scope:** Plugin JS + CSS only (main.js + styles.css)

## Goal

Two UX improvements to the per-paper dashboard view:
1. **Click-to-copy** for discrete metadata fields (single click → clipboard)
2. **Text-selectable** for prose content areas (normal browser selection + copy)
3. **Metadata enhancement** — add Journal / DOI / Zotero Key / Collection Path in a compact inline row below authors/year

---

## Design

### Per-Paper View Layout (after changes)

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  Efficacy of TXA in Reducing Blood Loss...               [📋]  │  ← Title, click-to-copy, copy icon on hover
│  Tianli Xia, Hiroyasu Konno, Jeonghyun Ahn · 2016              │  ← Authors (click-to-copy) · Year
│                                                                │
│  Cancer Research · DOI: 10.1158/... · Zotero: ABCDEFG   🔍    │  ← NEW meta-line (Zotero-style)
│  📂 Orthopedics / Spine                                         │  ← NEW collection path (click-to-copy)
│                                                                │
│  [PDF] [Fulltext]  [OCR done] [Deep-read pending]              │  ← existing status pills + file buttons
│                                                                │
│  ## 🔍 精读  (article overview — text-selectable)               │  ← existing, keep selectable
│  ## 💬 Discussion (Q&A — text-selectable)                      │  ← existing, keep selectable
│  ▶ Technical Details (health, paths — click-to-copy fields)    │  ← existing, add copy-on-click
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Meta-Line CSS (from user-provided reference)

```css
/* Metadata inline row — Zotero style */
.paperforge-meta-line {
    margin-top: 8px;
    font-size: 13px;
    color: var(--text-muted);
    display: flex;
    flex-wrap: wrap;
    gap: 6px 10px;
    align-items: center;
}

.paperforge-meta-item {
    white-space: nowrap;
}

.paperforge-meta-key {
    color: var(--text-faint);
    margin-right: 4px;
}

.paperforge-meta-value {
    color: var(--text-muted);
}

.paperforge-meta-value.mono {
    font-family: var(--font-monospace);
}

/* Clickable fields */
.paperforge-meta-value.clickable,
.paperforge-click-copy {
    cursor: pointer;
    border-bottom: 1px dashed var(--text-faint);
    transition: color 0.15s, border-color 0.15s;
}

.paperforge-meta-value.clickable:hover,
.paperforge-click-copy:hover {
    color: var(--text-accent);
    border-bottom-color: var(--text-accent);
}

.paperforge-copy-icon {
    opacity: 0;
    margin-left: 4px;
    font-size: 11px;
    cursor: pointer;
    transition: opacity 0.15s;
}
.paperforge-click-copy:hover .paperforge-copy-icon {
    opacity: 0.6;
}
```

### Interaction Rules

| Field              | Type     | Click behavior                                     |
| ------------------ | -------- | -------------------------------------------------- |
| Title              | Copy     | Click → copy full title; copy icon appears on hover |
| Authors            | Copy     | Click → copy author string                          |
| Journal            | Display  | Read-only, no copy                                  |
| DOI                | Copy     | Click → copy DOI; also link icon to doi.org         |
| Zotero Key         | Copy     | Click → copy key (monospace)                        |
| Collection Path    | Copy     | Click → copy pipe-joined path                       |
| PMID (if present)  | Copy     | Click → copy PMID                                    |
| Note Path          | Copy     | Inside Technical Details; click → copy path         |
| Fulltext Path      | Copy     | Inside Technical Details; click → copy path         |
| Article Overview   | Select   | Normal text selection, no click-to-copy             |
| Recent Discussion  | Select   | Normal text selection, no click-to-copy             |
| Technical Details  | Mixed    | Paths are click-to-copy; status text is selectable  |

### Copy Feedback

On click → `navigator.clipboard.writeText(value)` then show a brief feedback:
- Change field text to "Copied!" for 1 second, then restore
- OR show a floating tooltip
- Recommended: inline text change (simpler, no new element needed)

---

## Implementation Tasks

### Task 1: Add CSS to styles.css
- Add `.paperforge-meta-line`, `.paperforge-meta-item`, `.paperforge-meta-key`, `.paperforge-meta-value` rules
- Add `.paperforge-click-copy` + `.paperforge-copy-icon` hover rules
- Ensure existing content areas have no `user-select: none`

### Task 2: Render meta-line in _renderPaperMode
- File: `paperforge/plugin/main.js`, in `PaperForgeStatusView._renderPaperMode()`
- After authors/year rendering (~line 1591), insert meta-line div
- Fields: Journal · DOI: xxx · Zotero: xxx · Collection: xxx
- Source data: `entry.journal`, `entry.doi`, `entry.zotero_key`, `entry.collection_path`, `entry.pmid`
- Add `paperforge-meta-value mono clickable` class to DOI, Zotero Key, PMID

### Task 3: Implement click-to-copy helper
- Add `_makeClickCopy(el, value, displayText)` method to `PaperForgeStatusView`
  - Sets cursor:pointer, dashed border, onclick handler
  - On click: copy value, change text to "Copied!", setTimeout restore displayText
- Apply to: title, authors, DOI, zotero_key, collection_path, pmid

### Task 4: Apply click-to-copy to Technical Details
- File: `paperforge/plugin/main.js`, `_renderPaperTechnicalDetails()`
- Make Note Path and Fulltext Path clickable
- Use same `_makeClickCopy` helper

### Task 5: Add copy icon to title
- Append a small 📋 span to the title element
- Show on hover via CSS opacity transition

### Task 6: Verify text selection behavior
- Confirm article overview, recent discussion, and tech details body text are NOT `user-select: none`
- Remove any existing `user-select: none` from content areas (but keep on buttons/toggles)

---

## Files to Modify

| File                      | Changes                                                    |
| ------------------------- | ---------------------------------------------------------- |
| `paperforge/plugin/styles.css` | ~40 lines: meta-line + click-copy + copy-icon CSS          |
| `paperforge/plugin/main.js`    | ~60 lines: meta-line rendering + _makeClickCopy() + wiring |

---

## Acceptance Criteria

- [ ] Meta-line appears below authors/year in per-paper view: Journal · DOI · Zotero · Collection
- [ ] DOI and Zotero Key are monospace, dashed-underline on hover, click to copy
- [ ] Title shows copy icon on hover, click to copy full title
- [ ] Authors click to copy
- [ ] Collection path click to copy
- [ ] Note Path / Fulltext Path in Technical Details click to copy
- [ ] Article overview and Recent Discussion text remains freely selectable
- [ ] "Copied!" feedback displays briefly on click
- [ ] No regressions in global or collection modes
- [ ] Works in both light and dark Obsidian themes
