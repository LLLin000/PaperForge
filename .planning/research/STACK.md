# Research: annotation v0.1 Stack

**Date:** 2026-06-17
**Milestone:** annotation v0.1 - PDF Annotation Backend & CLI Foundation

## Recommendation

Use the existing PaperForge Python stack only:

- Python standard library `sqlite3` for `annotations.db`
- Existing config/path resolver for vault and system/index paths
- Existing CLI dispatch in `paperforge/cli.py`
- Existing pytest test stack

Do not add a new database dependency, PDF.js dependency, or Obsidian plugin overlay dependency in v0.1.

## Source Inputs

- Remote branch `feat/pdf-annotation-layer`
- Remote reports:
  - `reports/00-executive-summary.md`
  - `reports/03-paperforge-schema-design.md`
  - `reports/05-mvp-implementation-plan.md`
  - `reports/06-risk-and-license-review.md`
- Current clean `upstream/master` worktree:
  - `C:\Users\tan\Desktop\GaoLab-SYSUCC\9.code\PaperForge-feat-pdf-annotation-layer`

## Stack Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Local storage | Independent `annotations.db` | Annotation data is user data and must not be dropped during memory/index rebuilds. |
| Zotero source | Read-only SQLite probe | Offline, no API keys, enough for Zotero PDF annotations. |
| SQLite access | Copy `zotero.sqlite` to temp by default | Avoid locks and inconsistent reads while Zotero is open. |
| CLI output | Stable JSON contract | Plugin and future automation can consume it without parsing text. |
| Plugin overlay | Deferred | The old branch's PDF overlay depends on Obsidian/PDF.js internals and should be isolated in v0.2. |

## Dependencies Not Added

- No `sql.js`/WASM in v0.1
- No Obsidian PDF monkey-patching in v0.1
- No Zotero Web API client in v0.1
- No write-back credentials or token storage in v0.1

## Integration Notes

The old annotation branch has useful backend modules, but the implementation should be ported selectively because the branch is behind current master and contains high-risk plugin changes. v0.1 should use current PaperForge path/config conventions and current CLI patterns rather than copying old branch assumptions.
