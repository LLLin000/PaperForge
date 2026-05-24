# Final Recommendation

> PaperForge PDF Annotation Layer — Architecture & MVP

## Summary

After comprehensive research across ZotFlow, Zotero source code, and Obsidian PDF plugin ecosystem, the recommendation is clear:

**Build a lightweight annotation layer using local Zotero SQLite read-only parsing, cached in a dedicated annotations.db, displayed via monkey-patched PDF viewer overlays in Obsidian, with write-back architecture designed from day one but implemented in Phase 3.**

## Why This Approach

### 1. ZotFlow is too heavy; PaperForge should not replicate it
ZotFlow's bidirectional sync engine (42,918 lines), embedded reader iframe (entire `zotero/reader` submodule), CodeMirror 6 extensions, React UI, Comlink/Penpal communication — 80% of ZotFlow's code is specific to being a full Zotero-in-Obsidian replacement. PaperForge needs only annotation display and lightweight sync.

### 2. Local SQLite reading is sufficient for v1, ideal for v1
All annotation data is available in Zotero's `zotero.sqlite`, fully documented. Read access is explicitly permitted by Zotero's documentation. The read path is:
- Copy DB → temp → parse → annotations.db

### 3. Hybrid read/write architecture is the right long-term design
- **Read**: Local SQLite (fast, offline, zero config)
- **Write**: Zotero Web API (safe, versioned, official)
- **schema includes `sync_state = pending_push` from day one**

### 4. Custom overlay via monkey-patching is the right UX choice
Users chose "direct monkey-patch" over alternatives. PDF++ has proven this is sustainable despite private API dependency.

## Recommended Development Order

```
Phase 1 (1 week):  annotations.db + CLI import/list/patch/delete
Phase 2 (1-2 weeks):  Obsidian PDF overlay (show + create + edit)
Phase 3 (post-MVP):  Zotero Web API write-back
```

## Key Numbers

| Metric | Value |
|--------|-------|
| New Python files | ~6 (annotation/ package) |
| New TS files | ~7 (pdf-overlay/ directory) |
| New CLI commands | 6 (import, list, create, patch, delete, export, status) |
| New DB | 1 (annotations.db, independent schema) |
| DB migrations planned | schema v1 (MVP), v2 (Web API write-back) |
| Estimated development time | 2-3 weeks for MVP |
| Risk level | Medium (Obsidian API stability) |

## What Was NOT Recommended

| Approach | Why Rejected |
|----------|-------------|
| Full ZotFlow bidirectional sync | Over-engineered for PaperForge's needs |
| Custom PDF.js reader iframe | Heavy, UX fragmentation, Obsidian already has PDF.js |
| Annotator-style markdown storage | Fragile, not AI-queryable, hard to maintain |
| Dedicated PDF annotation service | Overkill; local SQLite + CLI is sufficient for v1 |
| Read-only only (no write-back design) | User explicitly requested write-back be designed from start |

## Final Assessment

PaperForge's Annotation Layer is **well-scoped for MVP delivery in 2-3 weeks**. The architecture is clean, the risks are manageable, and the design accounts for future write-back without over-engineering the first version. The key dependency — Obsidian's private PDF viewer API — is a managed risk that PDF++ has successfully navigated for 2+ years.
