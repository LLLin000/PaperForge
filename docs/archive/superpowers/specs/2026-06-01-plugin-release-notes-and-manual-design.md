# Plugin Release Notes & Manual — Design Spec

> **Status:** Approved  
> **Date:** 2026-06-01

## Goal

Add a settings tab and auto-popup for versioned release notes and user manual access, in Chinese first.

## Design

### 1. Release Notes Data

- `paperforge/plugin/src/release-notes.json`
- Array of versioned entries, each with:
  - `version`, `date`, `title`
  - `breaking_or_migration` (string[])
  - `new_features` (string[])
  - `fixes` (string[])
  - `recommended_actions` (string[])

### 2. Settings Tab

- New tab `更新与手册` alongside existing `安装` and `功能`
- Upper section: version log cards, collapsible, newest first
- Lower section: links to external docs (`docs/user-manual.md`)

### 3. Auto-Popup on Version Change

- Trigger: `plugin.manifest.version !== settings.last_seen_version`
- Modal with version title + migration items + recommended actions
- `知道了` button writes `last_seen_version` to persistent settings

### 4. Version Tracking

- `last_seen_version: string` field added to `PaperForgeSettings`
- Compared on plugin `onload()`
- Persisted through `saveSettings()`

### 5. Deployment

- `release-notes.json` copied to plugin output dir alongside `main.js`
- esbuild config updated with a copy step

### 6. Manual

- `docs/user-manual.md` in repo
- Plugin links to it externally; no inline rendering

## Non-Goals

- No English release notes in this phase
- No inline Markdown rendering for manual
- No server-side release notes fetching
