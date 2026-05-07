# Phase 32: Deep-Reading Mode Detection — Summary

**Status:** Complete ✅

## One-Liner
Plugin routes deep-reading.md to dedicated dashboard mode via `_resolveModeForFile()` pure function, checking deep-reading.md filename BEFORE zotero_key frontmatter.

## Key Deliverables
- `_resolveModeForFile()` at main.js:739 — pure function that returns `{ mode, filePath, key, domain }` based on active file
- Priority: deep-reading.md filename > parent dir pattern (8-char-key - Title) > zotero_key frontmatter > global mode
- `_detectAndSwitch()` uses the resolved mode for all transitions
- Event subscriptions: `active-leaf-change` (debounced 300ms) + `modify` (formal-library.json only)
