# Plan 01 Summary: Pure fail-closed PDF jump-target resolution

**Phase:** annotation-07-pdf-jump-navigation
**Plan:** 01
**Wave:** 1
**Type:** TDD
**Completed:** 2026-06-25

## Tasks

### Task 1 (TDD RED): Failing navigation helper contract tests
- Created `paperforge/plugin/tests/annotation-navigation.test.mjs` with 47 test cases
- Covers: exact attachment identity match, identity mismatch with no unsafe main-PDF fallback, no-identity single-candidate fallback, ambiguous candidates, wikilink extraction, canonical path validation (D-05), pageIndex-to-one-based conversion (D-08), invalid/missing page data (D-11)

### Task 2 (GREEN): Pure fail-closed PDF target resolution
- Added `extractVaultPdfPath(value)` — unwraps wikilinks to vault-relative `.pdf` paths, rejects absolute paths, URIs, traversal, malformed wikilinks, and raw `storage:` values
- Added `buildPaperPdfCandidates(entry)` — extracts canonical PDF candidates from `pdf_path`, `supplementary`, and `zotero_storage_key`, deduplicates by path, retains attachment key from metadata or canonical `/storage/{key}/` path segment
- Added `resolveAnnotationPdfTarget(row, entry)` — resolves `sourceAttachmentKey` to matching candidate; identity-free single-candidate rule (D-06); returns `{ok, path, page, linkText, reason}`; converts pageIndex to one-based page via `pageIndex + 1`; preserves plain-PDF target for invalid page data
- Exported all three helpers from `module.exports` in `testable.js`

## Files Modified
- `paperforge/plugin/src/testable.js` — added 3 new exports
- `paperforge/plugin/tests/annotation-navigation.test.mjs` — new file, 47 tests

## Verification
- `node --check paperforge/plugin/src/testable.js` ✅
- `npm test -- tests/annotation-navigation.test.mjs` — 47/47 passed ✅
- `npm test -- tests/annotation-bridge.test.mjs` — 40/40 passed ✅ (no regressions)

## Decisions Enforced
- D-04: Exact attachment identity matching before candidate fallback
- D-05: Canonical vault-relative path only; non-canonical paths rejected
- D-06: Identity-free single-candidate fallback; ambiguity fails closed
- D-07: Unmatched/ambiguous identity returns unavailable result
- D-08: pageIndex is authoritative; pageLabel is display-only
- D-11: Missing/invalid page data yields plain-PDF target when PDF identity is resolved
