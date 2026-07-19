# OCR Redo Single-Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert OCR redo into an immediate rerun workflow and remove workspace `fulltext.md` as a second truth source.

**Architecture:** Reuse the existing OCR worker as the execution engine, but add a redo preflight that clears stale outputs, targets selected keys only, and writes `ocr_redo` back to `false` only on success. Route all `fulltext_path` consumers to canonical OCR storage.

**Tech Stack:** Python workers/CLI, pytest, Obsidian frontmatter paths.

---

### Task 1: Remove Workspace Fulltext As Truth Source

**Files:**
- Modify: `paperforge/worker/asset_index.py`
- Modify: `paperforge/worker/sync.py`
- Test: `tests/test_sync.py`

- [ ] Delete stale workspace `fulltext.md` during migration/index refresh.
- [ ] Stop bridging OCR fulltext into workspace.
- [ ] Point `entry["fulltext_path"]` at canonical OCR fulltext.
- [ ] Update sync test to expect deletion instead of refresh.

### Task 2: Make OCR Redo Closed-Loop

**Files:**
- Modify: `paperforge/worker/ocr.py`
- Modify: `paperforge/commands/ocr.py`
- Test: `tests/test_ocr.py`

- [ ] Add redo preflight to clear old OCR output and stale workspace fulltext.
- [ ] Force selected notes to `do_ocr: true`, `ocr_status: pending`, `ocr_redo: true` before rerun.
- [ ] Extend `run_ocr()` to accept selected keys.
- [ ] Call OCR directly from `ocr redo`.
- [ ] After rerun, set `ocr_redo: false` only for successful keys.
- [ ] Leave failed/pending keys at `ocr_redo: true`.

### Task 3: Verify End-to-End Behavior

**Files:**
- Test: `tests/test_ocr.py`

- [ ] Cover dry-run no-op behavior.
- [ ] Cover invalid key rejection.
- [ ] Cover success path: delete workspace fulltext, rerun selected key, write back `ocr_redo: false`.
- [ ] Cover incomplete rerun path: preserve `ocr_redo: true`.

### Task 4: Run Regression Suite

**Files:**
- Test: `tests/test_ocr_rendering.py`
- Test: `tests/test_ocr_layout_zones.py`
- Test: `tests/test_ocr_body_spine.py`
- Test: `tests/test_sync.py`
- Test: `tests/test_asset_index.py`

- [ ] Run targeted OCR redo tests first.
- [ ] Run full regression suite for OCR/sync/asset index.
