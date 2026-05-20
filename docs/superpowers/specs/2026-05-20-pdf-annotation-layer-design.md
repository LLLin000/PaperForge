# PaperForge PDF Annotation Layer Design

**Date:** 2026-05-20
**Status:** Proposed
**Audience:** Maintainers, contributors, agentic implementers

---

## 1. Summary

PaperForge should add a lightweight PDF annotation layer that treats Zotero as an upstream annotation source instead of trying to become a full Zotero replacement.

The chosen design is:

1. Read Zotero annotations from local `zotero.sqlite` in **read-only** mode.
2. Cache normalized annotations in an independent `annotations.db` under `System/PaperForge/indexes/`.
3. Display those annotations in Obsidian by **monkey-patching the native PDF viewer**, following the proven PDF++ approach.
4. Allow local PaperForge-native annotation creation and editing inside Obsidian.
5. Design write-back from day one, but route future write-back through the **Zotero Web API**, not direct SQLite writes.

This explicitly avoids building a full ZotFlow-style system with its own embedded reader, large sync engine, React-heavy UI surface, or end-to-end Zotero library replacement.

---

## 2. Product Decision

### Chosen Architecture

- **Read path:** local Zotero SQLite, read-only
- **Cache:** independent `annotations.db`
- **Viewer integration:** patch Obsidian's native PDF viewer
- **Write-back design:** future Zotero Web API push
- **Version 1 scope:** import, cache, display, create local annotations, edit local comments/colors

### Why

This design gives PaperForge the strongest trade-off across speed, safety, and user experience:

- Local SQLite gives fast, offline, zero-config reads.
- Independent DB storage prevents memory rebuild from destroying user annotations.
- Native PDF viewer patching preserves Obsidian UX instead of fragmenting it with a second reader.
- Web API write-back avoids the corruption and sync-state hazards of SQLite mutation.

---

## 3. Problem Statement

PaperForge currently has no structured annotation layer. The system can manage papers, OCR, memory state, and plugin runtime state, but it cannot:

1. Read Zotero PDF annotations into a queryable PaperForge data store.
2. Show annotations visually on top of PDFs inside Obsidian.
3. Support local annotation editing in a way that is future-compatible with safe Zotero write-back.

The nearest comparison, ZotFlow, is too large and too opinionated for PaperForge's needs:

- It embeds its own reader iframe.
- It uses a Web API-centric sync model with IndexedDB and a full conflict UI.
- It bundles UI and note-generation concerns that PaperForge does not need for the first version.

At the same time, the simpler alternatives are inadequate:

- Direct SQLite writes are dangerous and explicitly discouraged by Zotero.
- Markdown-as-annotation-storage is fragile and weak for structured query.
- A custom PaperForge-only PDF reader would duplicate functionality the Obsidian native viewer already provides.

---

## 4. Goals

### 4.1 Primary Goals

1. Import Zotero annotations from local SQLite without writing to Zotero.
2. Normalize those annotations into a PaperForge-owned schema.
3. Persist them in a dedicated annotation database that survives memory rebuilds.
4. Render them as overlays in Obsidian's native PDF viewer.
5. Allow PaperForge-local annotation creation and editing in the Obsidian PDF view.
6. Preserve a clean future path for safe Zotero write-back.

### 4.2 Secondary Goals

1. Make annotations searchable by text, comment, and tags.
2. Support export to JSON and Markdown.
3. Support multiple PDF attachments per paper without ambiguity.
4. Keep plugin and CLI contracts machine-readable through `--json` output.

### 4.3 Non-Goals

1. No direct SQLite write-back to Zotero.
2. No full ZotFlow feature parity.
3. No custom embedded PDF.js reader for V1.
4. No EPUB annotation support in V1.
5. No collaborative multi-user annotation sync in V1.
6. No complex ink editing in V1.

---

## 5. Guiding Principles

1. **Zotero SQLite is read-only.** PaperForge may read and cache from it, but must never mutate it.
2. **PaperForge owns its local annotation truth.** Once imported, normalized annotations live under PaperForge's own storage and lifecycle.
3. **Memory rebuild must never destroy user annotations.** Annotation persistence is isolated from `paperforge.db` rebuild semantics.
4. **Use the native viewer unless there is a hard blocker.** The default UX should stay inside Obsidian's existing PDF experience.
5. **Future write-back must use supported contracts.** When write-back arrives, it should go through the Zotero Web API with version-aware conflict handling.
6. **Prefer minimal structure over framework sprawl.** This repo currently uses a single plugin `main.js` plus testable helpers; the design should respect that reality unless a split is clearly necessary.

---

## 6. Core Research Findings

### 6.1 Zotero Schema Facts

Zotero stores annotation data in `itemAnnotations`, keyed to `items(itemID)` and attached to `itemAttachments(itemID)` through `parentItemID`.

The relevant columns are:

- `type`
- `text`
- `comment`
- `color`
- `pageLabel`
- `sortIndex`
- `position`
- `isExternal`

Type mapping is:

- `1` → `highlight`
- `2` → `note`
- `3` → `image`
- `4` → `ink`
- `5` → `underline`
- `6` → `text`

The `position` JSON is already rich enough for rendering:

- `rects` for highlight-like annotations
- `paths` for ink
- `pageIndex` for page scoping
- optional `width`/`height` for image/ink data

### 6.2 ZotFlow Architecture Lessons

Useful parts:

- normalized annotation schema
- conflict-state thinking
- clear read/write separation in the sync engine

Parts to avoid:

- reader iframe architecture
- large worker bridge and IndexedDB runtime
- full Zotero library replacement UI

### 6.3 Obsidian PDF Feasibility Facts

Overlay display is feasible by patching private PDF viewer classes and listening to PDF.js event bus events such as:

- `textlayerrendered`
- `annotationlayerrendered`
- `pagerendered`
- `scalechanged`

There is no stable public PDF view API, so this is an accepted managed risk.

---

## 7. Proposed Architecture

## 7.1 System Overview

```text
Zotero SQLite (read-only)
        ↓
Probe / Import pipeline
        ↓
annotations.db
        ↓
CLI JSON contracts
        ↓
Obsidian plugin bridge
        ↓
Native PDF viewer overlay
```

## 7.2 Storage Boundary

PaperForge will add:

```text
System/PaperForge/indexes/annotations.db
```

This DB is separate from:

- `paperforge.db`
- vector DB state
- canonical index JSON snapshots

That separation is intentional. `paperforge.db` is a rebuildable memory-layer artifact. `annotations.db` is a persistent user-data store.

## 7.3 Runtime Layers

### Python Layer

Responsibilities:

- locate Zotero data directory
- copy `zotero.sqlite` to temp when needed
- run read-only SQL queries
- normalize annotation rows
- store/update/search/export annotations in `annotations.db`
- provide CLI entrypoints with JSON output

### Plugin Layer

Responsibilities:

- detect active PDF files
- map PDF file to PaperForge paper key
- fetch annotations through CLI subprocess calls
- patch native PDF viewer load/render lifecycle
- render and update overlay DOM
- collect selection data for local annotation creation
- show popovers/edit affordances

### Future Sync Layer

Responsibilities:

- inspect `sync_state`
- enqueue pending push operations
- push through Zotero Web API
- detect remote version drift and conflicts

---

## 8. Data Model

## 8.1 Database Choice

Use an independent SQLite database with its own schema version and migration path.

## 8.2 Main Table

The normalized table should contain:

- identity (`id`, `paper_id`)
- Zotero source tracking (`zotero_key`, `zotero_item_id`, `zotero_attachment_key`, `source_version`)
- PDF association (`pdf_path`, `pdf_hash`)
- annotation payload (`type`, `page_index`, `page_label`, `selected_text`, `comment`, `color`, `sort_index`, `position_json`, `selector_json`, `tags_json`)
- sync lifecycle (`source`, `sync_state`, `is_readonly`, `source_modified_at`)
- timestamps (`created_at`, `updated_at`, `deleted_at`)

## 8.3 Search

Use FTS5 on:

- `selected_text`
- `comment`
- `tags_json`

## 8.4 Write-Back Readiness

Even before implementation, the schema must reserve:

- `sync_state = pending_push`
- a `sync_queue` table
- a place to track source version and future push errors

This avoids a destructive redesign when write-back is implemented later.

---

## 9. Read Path Design

## 9.1 Import Mechanics

The importer will:

1. detect the Zotero DB path from CLI option or configured/default data dir
2. **by default** copy `zotero.sqlite` to a temp directory, with an explicit opt-out only for controlled environments
3. open the copy in SQLite `mode=ro`
4. query annotations plus parent attachment and top-level paper context
5. query tags through `itemTags` and `tags`
6. normalize to PaperForge schema
7. upsert into `annotations.db`

## 9.2 Identity Rules

For imported Zotero annotations:

- local row `id` should be stable and PaperForge-owned
- Zotero's annotation key should live in `zotero_key`
- `(source='zotero_db', zotero_key)` should be treated as the external identity

This avoids overloading local primary keys with source keys and leaves room for future locally-created annotations that do not yet exist in Zotero.

## 9.3 Deletion Semantics

If a previously imported Zotero annotation disappears from the source, PaperForge should:

- mark it as remotely deleted if it was never locally modified, or
- mark it as conflict if local edits exist and future write-back semantics would be ambiguous

For V1, soft delete is sufficient.

---

## 10. Overlay Design

## 10.1 Chosen Strategy

Patch the native PDF viewer instead of creating a custom reader.

The plugin should:

1. patch viewer load lifecycle
2. create per-page overlay layers
3. render rect-based annotation DOM on page render events
4. show popovers on click/hover
5. collect selections for local annotation creation

## 10.2 Rendering Model

For each rendered page:

- create `div.pf-annotation-overlay`
- call `window.pdfjsLib.setLayerDimensions()` to align it with the page viewport
- place child rects using percentage-based CSS positioning

This mirrors PDF++ and avoids re-computing absolute pixel positions on every zoom.

## 10.3 Editing Model

Imported Zotero annotations:

- display as read-only in V1
- show lock state visually

PaperForge-local annotations:

- can be created from PDF text selection
- can be edited for comment and color
- can be deleted locally

## 10.4 Failure Behavior

If patching fails due to Obsidian version drift:

- the plugin must not crash
- the annotation feature should disable itself cleanly
- the user should still retain CLI annotation access

---

## 11. Write-Back Design

## 11.1 Architectural Decision

When write-back is implemented, it should use the **Zotero Web API**, not direct SQLite writes.

## 11.2 Why Web API for Writes

Advantages over SQLite mutation:

1. respects Zotero's sync and validation rules
2. supports version-aware optimistic locking
3. avoids corruption risk when the Zotero client is open
4. works with supported group library semantics
5. aligns with Zotero's official extension and automation model

## 11.3 Hybrid Read/Write Model

Chosen long-term model:

- **Read:** local SQLite
- **Write:** Zotero Web API

This keeps reads fast and offline while reserving writes for supported contracts.

## 11.4 Conflict States

The design should support at least:

- `zotero_synced`
- `local_modified`
- `pending_push`
- `zotero_remote_changed`
- `conflict`

That state model is enough to stage future sync behavior without overbuilding V1.

---

## 12. CLI Surface

The feature should introduce a new top-level command family:

```text
paperforge annotation import
paperforge annotation list
paperforge annotation create
paperforge annotation patch
paperforge annotation delete
paperforge annotation export
paperforge annotation status
```

Every command should support `--json` for plugin consumption.

---

## 13. Testing Strategy

## 13.1 Python

Need tests for:

- schema initialization and migration
- probe behavior and read-only DB open
- annotation import/upsert/delete behavior
- CLI JSON contracts
- search/export behavior

## 13.2 Plugin

Need tests for:

- path/runtime helper additions in `src/testable.js`
- subprocess argument construction
- annotation JSON parsing and state classification
- overlay coordinate conversion helpers extracted into testable functions where practical

## 13.3 Integration

Need fixture-driven tests proving:

- import from representative Zotero rows
- imported annotations survive memory rebuild
- plugin-visible JSON output stays stable

The fixture coverage should include at least:

- highlight with multi-rect `position.rects`
- note with comment payload
- underline with selected text
- tags attached through `itemTags`
- non-ASCII/CJK selected text
- imported readonly rows and PaperForge-local rows

---

## 14. Risks

1. **Obsidian private PDF viewer API drift**
   - mitigation: narrow patch surface, fail soft, add plugin tests around extracted helpers
2. **Zotero schema drift**
   - mitigation: schema checks and clear importer errors
3. **plugin conflicts with PDF++**
   - mitigation: detect overlap and document incompatibility or fallback mode
4. **large annotation counts**
   - mitigation: render only visible pages and cache per-page annotation grouping

---

## 15. Rollout Strategy

### Phase 1

- `annotations.db`
- probe/import pipeline
- CLI commands
- no viewer integration yet

### Phase 2

- PDF overlay rendering
- local annotation create/edit/delete
- read-only display of imported Zotero annotations

### Phase 3

- Web API write-back
- push queue
- remote version reconciliation and conflict handling

---

## 16. Final Recommendation

PaperForge should proceed with a lightweight, layered annotation system centered on:

- **read-only local Zotero SQLite ingestion**
- **independent local annotation persistence**
- **native Obsidian PDF overlay rendering**
- **future Web API write-back**

This design keeps the V1 implementation small enough to ship, avoids the major risk of SQLite writes, preserves the strongest UX available in Obsidian, and leaves a clean upgrade path to safe synchronization later.
