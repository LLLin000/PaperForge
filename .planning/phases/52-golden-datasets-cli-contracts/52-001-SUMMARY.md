---
phase: 52-golden-datasets-cli-contracts
plan: 001
subsystem: fixtures
tags: [fixtures, golden-dataset, zotero, pdf, ocr, snapshots, vault-builder]
dependency-graph:
  requires: [51]
  provides: [52-002]
  affects: [tests/cli, tests/e2e, tests/journey, tests/chaos]
tech-stack:
  added: [pymupdf (fitz) for PDF generation]
  patterns: [fixture-driven testing, snapshot-based contracts, vault factory pattern]
key-files:
  created:
    - fixtures/MANIFEST.json
    - fixtures/zotero/*.json
    - fixtures/pdf/generate_fixtures.py + 4 PDFs
    - fixtures/ocr/* (6 mock responses + 2 expected outputs)
    - fixtures/snapshots/* (4 snapshot definitions)
    - fixtures/vault_builder.py
decisions: []
metrics:
  duration: ~15 min
  completed_date: 2026-05-08
---

# Phase 52 Golden Datasets & CLI Contracts — Plan 001 Summary

**One-liner:** Golden dataset fixtures — 10 Zotero JSON variants, 4 generated PDFs, 6 mock OCR API responses, 4 snapshot contracts, and a VaultBuilder factory — all tracked in MANIFEST.json.

## Tasks Executed

### Task 1: Zotero JSON Fixture Variants + MANIFEST.json
- 10 Zotero JSON fixture files created in fixtures/zotero/ covering all path format variants, edge cases, CJK content, and multi-attachment scenarios
- malformed.json intentionally breaks JSON parsing
- empty.json is bare `[]` array
- MANIFEST.json tracks all 30+ fixtures with `used_by`, `desc`, `generated` fields
- All CJK content uses non-escaped Unicode

### Task 2: Minimal Valid PDFs + Mock OCR Response Fixtures
- PDF generator script (generate_fixtures.py) using pymupdf creates 4 PDFs from code (blank, two_page, with_figures, CJK_文件名.pdf)
- 6 mock PaddleOCR API response fixtures covering all lifecycle states: submit (202), poll_pending, poll_done, result (2 pages + figure + table), error (401), timeout (queued forever)
- expected_fulltext.md and figure_map.json as expected OCR output artifacts

### Task 3: Expected Output Snapshots + Shared Vault Builder
- 4 snapshot files defining expected CLI output contracts:
  - paths_json/default_config.json (paths --json contract)
  - status_json/empty_vault.json (status --json on empty vault)
  - formal_note_frontmatter/orthopedic_article.yaml (frontmatter YAML contract)
  - index_json/after_sync.json (canonical index entry contract)
- Snapshots use placeholder markers (<VAULT>, <TIMESTAMP>, <VERSION>) for dynamic field normalization
- VaultBuilder class with 3 completeness levels (minimal, standard, full) in fixtures/vault_builder.py

## Verification

All 3 automated verification scripts pass:
- Task 1: 11 JSON files in fixtures/zotero/, all valid (except malformed which correctly fails)
- Task 2: 4 PDFs, 8 OCR fixtures, all JSON valid
- Task 3: VaultBuilder integration PASS (minimal + standard vault builds)

## Deviations from Plan

None — plan executed exactly as written.

## FIX Requirements Satisfied

- FIX-01: 10+ Zotero JSON fixture variants created
- FIX-02: 4 minimal valid PDFs including CJK filename, generated from code
- FIX-03: 6 mock OCR API response fixtures covering all PaddleOCR states
- FIX-04: Expected output snapshots in 4 subdirectories with placeholder markers
- FIX-05: MANIFEST.json tracks all 30+ fixtures with used_by, generated, desc

## Success Criteria

- [x] 10 Zotero JSON fixtures in fixtures/zotero/ covering all FIX-01 variants
- [x] 4 minimal PDFs in fixtures/pdf/ including CJK filename, generated from code
- [x] 6 mock OCR response fixtures in fixtures/ocr/ covering all API states (FIX-03)
- [x] extracted_fulltext.md and figure_map.json as expected OCR outputs
- [x] 4 snapshot files in fixtures/snapshots/ defining expected CLI output contracts (FIX-04)
- [x] MANIFEST.json tracks all 30+ fixtures with used_by, generated, desc (FIX-05)
- [x] VaultBuilder in fixtures/vault_builder.py creates 3-level vaults from golden data
- [x] Automated verification commands all pass
- [x] All 5 FIX requirements satisfied

## Commits

- `3489e5c`: feat(52-golden-datasets-cli-contracts): create golden dataset fixtures
