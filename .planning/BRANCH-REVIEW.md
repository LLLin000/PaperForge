---
phase: branch-review-v1.6-ai-ready-asset-foundation
reviewed: 2026-05-07T00:00:00Z
depth: deep
files_reviewed: 11
files_reviewed_list:
  - paperforge/worker/sync.py
  - paperforge/worker/asset_index.py
  - paperforge/worker/asset_state.py
  - paperforge/worker/ocr.py
  - paperforge/commands/context.py
  - paperforge/worker/discussion.py
  - paperforge/worker/repair.py
  - paperforge/worker/status.py
  - paperforge/setup_wizard.py
  - paperforge/plugin/main.js
  - pyproject.toml
findings:
  critical: 3
  warning: 4
  info: 0
  total: 7
status: issues_found
---

# Branch Review Report

## Critical Issues

### CR-01: First upgrade sync can delete legacy flat notes before preserving deep-reading content

**File:** `paperforge/worker/sync.py:1547-1549,1649-1652,1719-1729`  
**Issue:** `migrate_to_workspace()` refuses to migrate when no canonical index exists, but `run_index_refresh()` still proceeds to `build_index()` and later deletes matching flat notes once workspace folders exist. For a user upgrading from `master` with only legacy flat notes, the workspace note is rebuilt from scratch and the original flat note can then be deleted, dropping any existing `## 🔍 精读` content and other legacy note body content.

**Fix:** Make migration scan legacy flat notes directly instead of depending on an existing index, and do not delete flat notes until deep-reading/body preservation has been verified in the workspace files.

### CR-02: Legacy library-record workflow flags are dropped on upgrade

**File:** `paperforge/worker/sync.py:652-677,735-737`; `paperforge/worker/asset_index.py:307-308`  
**Issue:** The branch stops reading `do_ocr` / `analyze` from legacy `library-records` and `run_selection_sync()` explicitly skips any migration of those controls. `_build_entry()` now derives both flags only from formal notes or OCR meta. On upgrade from `master`, queued OCR/deep-reading selections stored only in library records are silently reset, breaking pending user workflows.

**Fix:** Add an explicit one-time migration that imports `do_ocr`, `analyze`, and related state from legacy library-record files into formal-note frontmatter before the first rebuild, then keep the old files until migration succeeds.

### CR-03: Canonical index can declare papers AI-ready even when required workspace assets do not exist

**File:** `paperforge/worker/asset_index.py:334-338,357-364`; `paperforge/worker/asset_state.py:39-48,100-114`  
**Issue:** `_build_entry()` always fills `paper_root`, `main_note_path`, `fulltext_path`, `deep_reading_path`, and `ai_path` as strings whether or not those files exist. `compute_lifecycle()` and `compute_health()` treat non-empty strings as sufficient, so entries can be marked `ai_context_ready` / `healthy` while `deep-reading.md` or `fulltext.md` is missing. That breaks the contract of the new canonical asset index and can feed dead paths to `paperforge context`, the dashboard, and downstream agents.

**Fix:** Derive readiness from filesystem existence, not path-string presence. For example, require `Path(vault, fulltext_path).exists()` / `Path(vault, deep_reading_path).exists()` before returning `ai_context_ready` or `asset_health=healthy`.

## Warnings

### WR-01: Setup wizard accepts unsupported Python versions

**File:** `paperforge/setup_wizard.py:137-146`; `pyproject.toml:10`; `paperforge/plugin/main.js:17-20`  
**Issue:** The setup wizard passes Python `>=3.8` and the plugin UI advertises `3.9+`, but the package metadata requires `>=3.10`. Fresh installs can therefore be reported as valid by setup while later install/runtime steps fail on unsupported interpreters.

**Fix:** Align every setup check and UI string to `>=3.10`.

### WR-02: Discussion recorder can commit partial state on malformed Q&A payloads

**File:** `paperforge/worker/discussion.py:185-189,314-333`  
**Issue:** `record_session()` appends to `discussion.json` before rendering `discussion.md`, and `_build_md_session()` blindly indexes `qa['question']` / `qa['answer']`. A malformed QA item can therefore persist JSON, fail Markdown generation, and return an error after only half of the append completed.

**Fix:** Validate each QA pair before any write, or build both JSON and Markdown payloads completely in memory before replacing either file.

### WR-03: “Copy Collection Context” exports the whole vault, not the visible collection

**File:** `paperforge/plugin/main.js:209-216,1319-1322`  
**Issue:** The UI promises “all visible papers,” but `_runAction()` hardcodes `--all` for `needsFilter`. In collection mode this copies every indexed paper to the clipboard, which is both incorrect behavior and an avoidable prompt-scope leak.

**Fix:** Pass the active collection/domain filter to `paperforge context` instead of defaulting to `--all`.

### WR-04: Repair writes the canonical index through the non-atomic helper

**File:** `paperforge/worker/repair.py:290-305,331-346`; `paperforge/worker/_utils.py:69-71`  
**Issue:** `repair --fix` mutates `formal-library.json` using `write_json()` instead of the lock-protected atomic writer introduced in `asset_index.py`. Concurrent `sync`/`ocr`/dashboard reads can observe torn or stale index state.

**Fix:** Route every canonical-index write through `asset_index.atomic_write_index()` (or rebuild via `refresh_index_entry()` / `build_index()` only).

---

_Reviewer: gsd-code-reviewer_  
_Depth: deep_
