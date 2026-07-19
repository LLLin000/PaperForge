# Phase 33: Deep-Reading Dashboard Rendering — Summary

**Status:** Complete ✅

## One-Liner
Renders deep-reading.md content (status bar, Pass 1 summary) + discussion.json AI Q&A history with session-based collapsible groups and dialog bubbles.

## Key Deliverables
- `_renderDeepReadingMode()` at main.js:1000 — async render that reads deep-reading.md via `app.vault.read()` and discussion.json via `app.vault.read()`
- `_renderDeepStatusCard()` — status overview: figure-map, OCR status, Pass completion, health
- `_renderDeepPass1Card()` — extracts Pass 1 summary from multiple marker patterns (**一句话总览**, ## Pass 1, **文章摘要**)
- `_renderDeepQACard()` — session-based collapsible groups, dialog bubble format (question/answer different colors), default collapsed
- `extractPass1Content()` — marker-priority extraction with section boundary detection
- ModeGuard pattern for async race condition safety
