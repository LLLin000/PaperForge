---
phase: 54-dashboard-workflow-closure
plan: 001
subsystem: plugin/dashboard
tags:
  - dashboard
  - ocr-queue
  - pf-deep-handoff
  - i18n
dependency-graph:
  requires: []
  provides: [ocr-queue-buttons, pf-deep-command-copy, pending-ocr-action]
  affects: [dashboard-ui, per-paper-view]
tech-stack:
  added: []
  patterns:
    - "processFrontMatter for note frontmatter editing"
    - "conditional action card rendering via _renderPendingOcrAction"
key-files:
  modified:
    - paperforge/plugin/main.js
    - paperforge/plugin/styles.css
metrics:
  duration: ~5min
  completed: 2026-05-08
---

# Phase 54 Plan 001: OCR Queue Buttons, /pf-deep Handoff & Pending OCR Action

**One-liner:** Add OCR queue toggle buttons, improved `/pf-deep <key>` command copy with agent platform label, and dynamic "Run All Pending OCR" action to the dashboard.

## Summary

Plan 54-001 implemented three DASH requirements:

### DASH-01: OCR Queue Control
- Users can add/remove papers from the OCR queue directly from the per-paper dashboard card, without manual frontmatter editing
- Clicking the toggle button calls `app.fileManager.processFrontMatter()` to set `do_ocr: true/false`
- Brief Notice confirms the action; view refreshes to reflect new state
- Shows status hint ("OCR pending" / "OCR already done") when paper is in queue

### DASH-02: /pf-deep Handoff
- Copy button now copies the full command `/pf-deep <key>` instead of just the key
- Agent platform label ("Run in opencode") shown below the copy button, reading from saved `agent_platform` setting
- Step info text updated to reflect the new workflow

### Dynamic Action: "Run All Pending OCR"
- When OCR stats show pending items > 0, a styled action card appears in the Quick Actions grid
- Card uses orange accent styling; click dispatches the `paperforge-ocr` action
- Stale cards are removed on re-render

### i18n
- 13 new keys added to both LANG.en and LANG.zh (OCR queue, /pf-deep handoff, privacy warning)

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add i18n keys | 14f965d | main.js |
| 2 | Add OCR queue buttons | 14f965d | main.js |
| 3 | Improve /pf-deep handoff + pending OCR action + CSS | 14f965d | main.js, styles.css |

## Decisions Made

- OCR queue uses in-memory processFrontMatter for immediate frontmatter writes
- Agent platform read from `settings.agent_platform`, defaulting to `'opencode'`
- Pending OCR action card uses orange border/background for visual distinction
- CSS classes follow existing `paperforge-*` naming convention

## Deviations from Plan

None — plan executed exactly as written.
