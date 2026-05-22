# ZotFlow Architecture Analysis

> Status: COMPLETE | Repo: duanxianpi/obsidian-zotflow v1.0.9 | License: AGPL-3.0

## Architecture Overview

ZotFlow 采用 **Main Thread + Web Worker + Reader Iframe** 三层架构：

```
Obsidian Main Thread
├── Plugin (main.ts)
│   ├── WorkerBridge (Comlink)  ←→  Web Worker
│   ├── ZoteroReaderView (Penpal)  ←→  Reader Iframe (zotero/reader)
│   ├── LocalReaderView (vault files)
│   ├── NoteEditorView
│   └── TreeView (React + react-arborist)
│
├── Services (main-thread)
│   ├── ServiceLocator
│   ├── IndexService (zotero_key → file path from frontmatter)
│   ├── ViewStateService
│   ├── CitationService
│   └── EventBus / TaskMonitor / LogService / NotificationService
│
└── Ui Components
    ├── reader/view.ts / bridge.ts / local-view.ts
    ├── tree-view/ (React)
    ├── activity-center/ (React modal)
    ├── editor/ (CodeMirror 6 extensions)
    └── modals/
```

```
Web Worker (worker.ts)
├── ZoteroService (zotero-api-client wrapper)
├── SyncService (42,918 bytes — bidirectional sync engine)
├── AnnotationService (CRUD + diff)
├── LibraryService (per-library permissions)
├── AttachmentService (download + cache from API/WebDAV)
├── TemplateService (LiquidJS rendering)
├── NoteService (source note generation)
├── ConflictService (field-level diff + resolve)
├── IndexedDB (Dexie) — local cache for all Zotero data
└── PDFProcessWorker (nested PDF.js worker for export/import)
```

## Communication Protocols

| Boundary | Protocol | Mechanism |
|----------|----------|-----------|
| Main ↔ Worker | Comlink | Proxy-based RPC, `Comlink.wrap<WorkerAPI>()` |
| Main ↔ Reader Iframe | Penpal | WindowMessenger, structured clone |
| Worker ↔ PDF.js Worker | postMessage | Promise-based request/response |

## Annotation Data Flow

### Read Path (Zotero → Plugin → Iframe)

```
Zotero API → Worker SyncService → IndexedDB (items table)
  → Plugin.annotationService.getAnnotations()
  → getAnnotationJson() (db/annotation.ts)
  → AnnotationJSON[] → ZoteroReaderView
  → IframeBridge.initReader({ annotations })
  → AnnotationManager.setAnnotations() → render overlays
```

### Write Path (Iframe → Plugin → Zotero)

```
User creates annotation in reader iframe
  → annotationsSaved event (Penpal)
  → ZoteroReaderView.handleAnnotationsSaved()
  → WorkerBridge.annotation.saveAnnotations()
  → AnnotationService.saveAnnotations()
    → diff with existing (annotationDataDiff)
    → upsert IndexedDB items (syncStatus = "created"/"updated")
    → trigger source note re-render (debounced)
  → Next push cycle: SyncService.pushDirtyItems()
    → Zotero API (version-based optimistic locking)
```

## Key Technical Decisions

### Why Web API instead of SQLite?
- Full bidirectional sync requires version management
- SQLite write would bypass Zotero's validation + sync state
- Web API supports group libraries, conflict detection

### Local Cache
- Dexie/IndexedDB with schema migration (v1→v2→v3)
- `syncStatus` tracking per item: synced / created / updated / deleted / ignore / conflict
- Raw API response stored in `raw` field for field-level diff

### Reader Embedding
- Git submodule to `zotero/reader`
- Built via webpack, inlined as blob URLs
- Modified Zotero reader engine with Obsidian theme integration
- Iframe sandbox restricted to `allow-scripts allow-same-origin allow-forms`

## What PaperForge Should Borrow

1. **AnnotationJSON schema** — well-designed, Zotero-compatible data model
2. **Conflict resolution model** — field-level diff with keep-local / accept-remote
3. **LiquidJS template pipeline** — if PaperForge wants template-driven notes
4. **SyncStatus pattern** — clean state machine for sync tracking

## What PaperForge Should NOT Borrow

1. **Embedded reader iframe** — too heavy, PaperForge should hook native PDF viewer
2. **CodeMirror 6 extensions** — Obsidian-specific, PaperForge doesn't do real-time editing
3. **React UI components** — PaperForge's plugin is minimal (ribbon icons + status bar)
4. **Full bidirectional sync engine** — PaperForge is read-first, write-limited
