# PRD: Search Redesign + Rebuild UX

## Status

- Author: @LLLin000
- Date: 2026-07-09
- Session: grill-with-docs (conversational sharpening completed)

## Problem

### 1. Search has no UI
`paperforge search` and `paperforge retrieve` are CLI-only. Users navigate the library through Obsidian's Base view (metadata table) or PaperForge's collection panel, but neither provides semantic search or a unified search experience.

### 2. OCR rebuild is unsafe and opaque
- `_needs_derived_rebuild` has a blind branch: old-format OCR (no structured blocks, no `derived_version`) returns `version_mismatch` → misleadingly suggests rebuild
- Rebuild overwrites `fulltext.md` → user annotations/highlights lost
- No backup, no restore, no diff

### 3. sqlite-vec migration leaves ChromaDB orphaned
Users with existing ChromaDB vector data have no migration path. Their vectors are invisible to `merge_retrieve` (which only queries vec0 tables). `prune.py` only deletes from ChromaDB, not from vec0.

## Proposed solution

### Phase 0: Legacy OCR detection fix
Fix `_needs_derived_rebuild` to detect `legacy_ocr` (no structured blocks + no `derived_version`):
- Return `(False, "legacy_ocr")` → do NOT trigger rebuild
- Do NOT suggest rebuild to affected users
- UI shows: "原始 OCR 格式，功能正常。升级搜索需要重建。"

### Phase 1: ChromaDB → vec_fulltext migration
Auto-migration on plugin upgrade:
- Detect ChromaDB `paperforge_fulltext` collection
- Read all vectors + text + metadata
- Write to `vec_fulltext` + `vec_fulltext_meta`
- No API calls (pure local copy, zero cost)
- Old ChromaDB data untouched (safe rollback)
- `prune.py` deletes from both ChromaDB and vec0 tables
- `merge_retrieve` queries vec0 tables (old ChromaDB readable via migration)

### Phase 2: Rebuild UX with version history
**Non-destructive rebuild:**
- Before rebuild: auto-backup `render/fulltext.md` + `render-map.json` to `versions/v1/`
- Rebuild writes new `render/fulltext.md`
- User can restore any version

**UI (File Recovery-style panel):**
- New section in Maintenance tab (or dedicated ItemView)
- Lists papers with available version history
- Per paper: version timeline with dates + sizes
- Actions: [Restore] [Compare]
- Compare: side-by-side diff of old vs new fulltext

**UX:**
- Upgrade: no auto-rebuild. Show non-intrusive banner:
  "优化搜索质量需要重建 OCR 结构数据。已有批注不受影响。"
- User initiates rebuild from Maintenance tab
- Strong confirmation dialog with backup notice
- Progress bar (paper-level granularity)
- Batch rebuild or per-paper

### Phase 3: Search Bar Redesign

**Location: PaperForge ItemView → Collection panel → below actions row**

**Two-mode search bar:**

#### Mode A: Metadata Search (default)
- Query `paper_fts` (FTS5 on papers table: title, author, year, journal, DOI, abstract, domain)
- Multiple terms → AND
- Quoted phrases → exact match (`"rotator cuff"`)
- Field syntax: `author:Smith`, `year:2021`, `doi:10.1234/...`
- No synonym expansion, predictable results
- Backend: `paperforge search <query> --json`
- Rank: FTS5 BM25 score

#### Mode B: @ Deep Search (prefix `@`)
- `@platelet rich plasma` → semantic + keyword search
- Query rewrite (stretch):
  - Entity recognition (medical terms, anatomy, diseases)
  - Synonym expansion
  - Abbreviation expansion
- Hybrid retrieval:
  - BM25 on `body_units_fts` (body unit content)
  - vec0 k-NN on `vec_body` + `vec_objects`
  - Metadata filter support
- Rerank: cross-encoder (stretch, v2)
- Backend: `paperforge retrieve <query> --json`
- Results: paper + section + figure + table

**Results display:**
- Card list in search results area
- Each card: title (clickable → navigate), author, year, journal, score, domain tag, abstract, source snippet
- @ mode: additionally shows matched text snippet + source type (body/section/figure/table)

**Architecture:**
- JS side: search input + mode switching + results rendering
- CLI bridge: `paperforge search` (metadata) / `paperforge retrieve` (deep)
- JSON output parsed, INFO lines stripped
- Debounce: Enter-triggered (not live), or future debounce

## Mental model

```
普通搜索 = 我知道我要找哪篇论文
  @搜索  = 我知道我要找什么知识，但不知道它在哪篇论文里
```

## Non-goals

- sql.js direct DB access (can be v2 when vec0 extension is WASM-compatible)
- Full-text search in Obsidian's Base plugin (PaperForge panel only)
- Real-time search-as-you-type (Enter-triggered)
- Rerank with cross-encoder (v2)
