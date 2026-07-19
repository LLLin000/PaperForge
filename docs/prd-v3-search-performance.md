# PRD: Search Performance — sql.js Direct Access + UX Polish

## Status

- Author: @LLLin000
- Date: 2026-07-09
- Session: grill-with-docs (completed)

## Problem

### 1. Metadata search is slow
Each search spawns a Python process (`python -m paperforge search <query> --json`), incurring ~200ms overhead for interpreter + import, while the actual FTS5 query takes <1ms. This prevents real-time search-as-you-type and makes `@ Deep Search` feel sluggish.

### 2. Search result cards have poor click target
Only the title text is clickable. Users expect the entire card to be a click target, and there is no Ctrl+click / Meta+click support to open in a new window.

## Solution

### Phase A: sql.js Database Service

Install the `sql.js` npm package (SQLite compiled to WebAssembly). The plugin already bundles `sql-wasm.wasm` (644KB) but never imports it.

Create `src/services/db.ts`:
- `initDatabase(vaultPath: string): Promise<void>` — load WASM, read `paperforge.db`, prepare FTS5 query statement
- `searchMetadata(query: string, limit?: number): SearchResult[]` — execute FTS5 on `paper_fts`, return typed results
- Lazy initialization: WASM loaded on first search, not on plugin start (avoids impacting Obsidian startup time)
- Handle `paperforge.db` not existing (graceful fallback to CLI)

### Phase B: Real-time Metadata Search

Replace the CLI-based search in `renderSearchSection` / `executeSearch`:

| Before | After |
|--------|-------|
| spawn → python -m paperforge search → parse stdout | sql.js → FTS5 → typed results |
| 200ms per query | 1-5ms per query |
| Enter-triggered only | Debounced 200ms, real-time on input |
| Must parse JSON from log lines | Direct typed access |

Keep `@ Deep Search` on CLI (`paperforge retrieve --json` → `spawn`) since vec0 requires native sqlite-vec extension that sql.js cannot load.

Debounce strategy:
- 200ms debounce on input (metadata)
- Enter-triggered only for @ Deep Search (cannot debounce spawn)

### Phase C: Card Click Target + Ctrl+click

In `renderSearchResults`:
- Move click handler from title element to the entire card element
- Single click → `openLinkText(path, "")` (current window)
- Ctrl/Meta + click → `openLinkText(path, "new-tab")` or similar
- Visual feedback: `cursor: pointer` on card, hover highlight
- Accessibility: `role="button"` on card

## Non-goals

- sqlite-vec WASM (deferred — sql.js cannot load native extensions; @ Deep Search stays on CLI)
- Full daemon architecture (deferred — rejected in grill session)
- Python startup optimization (deferred — @ Deep Search pays ~200ms, acceptable for its frequency)

## Issue breakdown

| # | Title | Depends on |
|---|-------|-----------|
| 41 | Prefactor: sql.js database service | — |
| 42 | Feature: Real-time metadata search via sql.js | #41 |
| 43 | Feature: Card click target + Ctrl+click | — |

## Mental model

User types in search bar → instant results (1ms) before they finish typing.
Only @ prefix triggers a brief loading state while Python starts.
