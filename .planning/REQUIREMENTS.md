# Requirements: PaperForge

**Defined:** 2026-05-06
**Core Value:** Researchers always know what papers they have, what state those papers are in, and whether each paper is reliably usable by AI with traceable fulltext, figures, notes, and source links.

## v1.8 Requirements

### AI Discussion Recording

- [ ] **AI-01**: `paperforge/worker/discussion.py` writes discussion.md (human-readable Q&A, `问题:` / `解答:` format, chronological sections) into paper workspace `ai/` directory.
- [ ] **AI-02**: `paperforge/worker/discussion.py` writes discussion.json (structured, sessions[] array with `schema_version`, `timestamp`, `qa_pairs[]` per session) into paper workspace `ai/` directory.
- [ ] **AI-03**: `/pf-paper` and `/pf-deep` agent sessions trigger discussion recorder at session completion, producing both files.

### Deep-Reading Dashboard

- [ ] **DEEP-01**: `_detectAndSwitch()` recognizes `deep-reading.md` as the `deep-reading` mode, checked BEFORE the `zotero_key` branch to prevent routing to per-paper mode.
- [ ] **DEEP-02**: `_renderDeepReadingMode()` renders: status bar (figure-map, OCR state, Pass 1/2/3 completion), Pass 1 full-text summary card (extracted from deep-reading.md), and AI Q&A history card (from `discussion.json`).
- [ ] **DEEP-03**: All four empty-state conditions render user-facing messages ("暂无" or equivalent) rather than errors: (a) missing discussion.json, (b) empty sessions, (c) missing Pass 1 content, (d) deep-reading.md not found.

### Navigation & Polish

- [ ] **NAV-01**: Per-paper dashboard card has a "Jump to Deep Reading" button that opens `deep-reading.md` via `openLinkText()`, verifying file existence with `getAbstractFileByPath()` before navigating.
- [ ] **NAV-02**: Plugin version number is read and displayed (from `paperforge/__init__.py` or `manifest.json` build-time embedding).
- [ ] **NAV-03**: Meaningless "ai" row is removed from plugin rendering.

### Integration Verification

- [ ] **INTEG-01**: End-to-end test: `/pf-paper` → discussion files created → dashboard shows AI Q&A history on deep-reading.md open. Windows CJK encoding verified; no `btoa()` on Chinese paths.

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### AI Discussion Recording

- **AI-04**: Threaded discussion format (nested Q&A threads within sessions, instead of flat qa_pairs[]).
- **AI-05**: Discussion search/retrieval across all papers by keyword or date range.

### Deep-Reading Dashboard

- **DEEP-04**: Inline editing of Pass 1 summary from dashboard (two-way sync with deep-reading.md).
- **DEEP-05**: Figure thumbnail previews in dashboard status bar (embeds from figure-map.json images).

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-recording every agent interaction | Recording is voluntary/session-end only — agents must explicitly trigger. Auto-capture would produce noise and violate user privacy expectations. |
| Dashboard replacing deep-reading.md | Dashboard is an index INTO the deep-reading note, not a replacement. Full content lives in .md file. |
| Real-time dashboard syncing during agent sessions | Dashboard refreshes on active-leaf-change only. Polling or websocket sync would violate thin-shell constraint. |
| Discussion analytics/categorization | V1.8 records raw Q&A. Tagging, categorization, and cross-paper analysis deferred to v2. |
| Figure preview carousel in dashboard | Deferred to v2. Status bar shows figure count and map existence only. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AI-01 | Phase 35 | Pending |
| AI-02 | Phase 35 | Pending |
| AI-03 | Phase 35 | Pending |
| DEEP-01 | Phase 32 | Pending |
| DEEP-02 | Phase 33 | Pending |
| DEEP-03 | Phase 33 | Pending |
| NAV-01 | Phase 34 | Pending |
| NAV-02 | Phase 31 | Pending |
| NAV-03 | Phase 31 | Pending |
| INTEG-01 | Phase 36 | Pending |

**Coverage:**
- v1.8 requirements: 10 total
- Mapped to phases: 10 ✓
- Unmapped: 0

---
*Requirements defined: 2026-05-06*
*Last updated: 2026-05-06 — traceability updated during roadmap creation*
