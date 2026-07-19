---
phase: 11
phase_name: "Zotero Path Normalization"
project: "PaperForge Lite"
generated: "2026-05-02"
counts:
  decisions: 8
  lessons: 5
  patterns: 3
  surprises: 1
missing_artifacts:
  - "11-UAT.md"
---

## Decisions

### Junctions resolved before computing relative paths (D-05)
`absolutize_vault_path()` resolves junctions before computing the vault-relative path, ensuring junction targets are used for wikilink computation rather than the junction point itself.

**Rationale/Context:** Zotero data may live outside the vault. A junction at `vault/system/Zotero` pointing to `D:/Zotero` must be resolved first so the relative path correctly references the junction point, not the target.

**Source:** 11-PLAN.md (Task 3, Decision D-05)

---

### Doctor detects Zotero location and recommends junction (D-07)
`paperforge doctor` checks if Zotero is inside or outside the vault, and if outside, recommends the exact `mklink /J` command to create the required junction.

**Rationale/Context:** Users often don't know where Zotero stores data or whether a junction is needed. Automated detection with copy-paste instructions removes guesswork from setup.

**Source:** 11-PLAN.md (Task 5, Decision D-07)

---

### Obsidian wikilink format with forward slashes (D-08)
All PDF paths are stored as `[[relative/path/to/file.pdf]]` with forward slashes, even on Windows.

**Rationale/Context:** Obsidian wikilinks use forward slashes regardless of platform. Using `pathlib.Path.as_posix()` ensures cross-platform consistency.

**Source:** 11-PLAN.md (Task 3, Decision D-08)

---

### Hybrid main PDF identification strategy
Main PDF identified by: Priority 1 — attachment.title == "PDF" AND contentType == "application/pdf"; Priority 2 — largest PDF file; Priority 3 — first PDF in list. Remaining PDFs become supplementary.

**Rationale/Context:** BBT exports don't always mark the main PDF. Some have title="PDF", some don't. The hybrid strategy maximizes correct identification across real-world export variations.

**Source:** 11-PLAN.md (Task 02)

---

### Three-format BBT path normalization
All 3 BBT export formats (absolute Windows paths, `storage:` prefix, bare relative) are first normalized to `storage:KEY/filename.pdf` intermediate format, then converted to wikilinks.

**Rationale/Context:** Normalizing to an intermediate format decouples BBT parsing from Obsidian path resolution, making each concern independently testable.

**Source:** 11-PLAN.md (Task 01)

---

### path_error integration with repair and status
`paperforge repair --fix-paths` re-resolves path errors using current Zotero location. `paperforge status` reports path error count and suggests repair.

**Rationale/Context:** Path errors can arise from Zotero data relocation or junction changes. Integrating with the repair system allows users to fix paths without manual editing of library-records.

**Source:** 11-PLAN.md (Task 06)

---

### New frontmatter fields for debugging and tracking
Library-records now include `bbt_path_raw`, `zotero_storage_key`, `attachment_count`, `supplementary` (wikilink list), and `path_error`.

**Rationale/Context:** These fields enable debugging of path resolution issues, track attachment metadata, and support the repair workflow with structured error data.

**Source:** 11-PLAN.md (Task 04)

---

### ADR-011 for path normalization
The complete path normalization strategy (D-01 through D-08) was documented as ADR-011 in `docs/ARCHITECTURE.md`.

**Rationale/Context:** Consistent with the architecture documentation pattern established in Phase 10, all major design decisions should be recorded as ADRs.

**Source:** 11-VERIFICATION.md (Acceptance Criteria Verification)

---

## Lessons

### `as_posix()` is idiomatic over `replace("\\", "/")`
`pathlib.Path.as_posix()` converts backslashes to forward slashes and is more robust than string replacement. It was used for wikilink path formatting.

**Rationale/Context:** The plan specified `replace("\\", "/")`, but `as_posix()` is the idiomatic Python approach. Functionally equivalent but cleaner.

**Source:** 11-SUMMARY.md (Deviation 2)

---

### Doctor functions belong in literature_pipeline.py, not ocr_diagnostics.py
The plan's acceptance criteria referenced `paperforge/ocr_diagnostics.py` for path resolution checks, but `run_doctor()` and all doctor infrastructure live in `pipeline/worker/scripts/literature_pipeline.py`.

**Rationale/Context:** `ocr_diagnostics.py` is exclusively for OCR (PaddleOCR) tiered checks. Path resolution checks must be co-located with `run_doctor()` where the dispatch logic resides.

**Source:** 11-SUMMARY.md (Deviation 3)

---

### Test fixtures must match actual implementation behavior
`obsidian_wikilink_for_pdf()` joins `storage:` paths directly under `zotero_dir` (not `zotero_dir/storage/`). Test fixtures had to create PDFs at `zotero_dir/KEY/file.pdf` to match current behavior.

**Rationale/Context:** The underlying path resolution behavior (whether `storage:` should include an implicit `storage/` segment) was deferred to Phase 12. Tests must faithfully reflect current implementation.

**Source:** 11-VERIFICATION.md (Deviation 1)

---

### Consistency audit catches dead links in documentation
Phase 11's consistency audit flagged links to non-existent `.planning/REQUIREMENTS-v1.2.md` and planning file markdown link syntax that resolved to dead links.

**Rationale/Context:** Documentation accumulates stale cross-references over time. Automated dead-link detection is essential for maintaining documentation quality.

**Source:** 11-VERIFICATION.md (Deviation 2)

---

### 25 test methods needed for comprehensive path coverage
The test suite (`test_path_normalization.py`) required 25 test methods across 4 test classes to cover BBT path formats (8), main PDF identification (6), wikilink generation (6), and integration scenarios (5).

**Rationale/Context:** Path normalization involves multiple input formats, edge cases, and output transformations. Adequate coverage required a dedicated test file with systematic test classes.

**Source:** 11-VERIFICATION.md (Test Results)

---

## Patterns

### Combined tightly coupled tasks into single atomic commit
Tasks 03 and 04 both modified the same file (`literature_pipeline.py`) with interdependent changes. They were committed together as `adf349e` to maintain atomicity.

**Rationale/Context:** When multiple tasks modify the same file with tight coupling, splitting into separate commits creates intermediate states that cannot be tested independently.

**Source:** 11-SUMMARY.md (Deviation 1)

---

### `storage:` prefix as intermediate representation
All 3 BBT path formats are normalized to `storage:KEY/file.pdf` as an intermediate step before final wikilink generation.

**Rationale/Context:** This decouples BBT parsing from Obsidian path resolution, allowing each transformation to be tested independently and supporting future path format additions.

**Source:** 11-PLAN.md (Task 01), 11-SUMMARY.md (Data Flow)

---

### Acceptance criteria verified via grep patterns
All acceptance criteria were checked with exact `grep` patterns, ensuring traceable, machine-verifiable criteria.

**Rationale/Context:** grep-verifiable criteria eliminate ambiguity in acceptance testing and enable automated verification during code review.

**Source:** 11-SUMMARY.md (Acceptance Criteria Verification)

---

## Surprises

### Storage path resolution doesn't add implicit storage/ segment
`obsidian_wikilink_for_pdf()` resolves `storage:KEY/file.pdf` directly under `zotero_dir` (`zotero_dir/KEY/file.pdf`) rather than `zotero_dir/storage/KEY/file.pdf`. This differs from real Zotero directory structure.

**Rationale/Context:** This behavior was inherited from the existing `pdf_resolver.py` implementation. Whether it's correct was deferred to Phase 12 architecture cleanup. Tests had to match current behavior despite it potentially being wrong.

**Source:** 11-VERIFICATION.md (Deviation 1)
