# Phase 11 Plan: Zotero Path Normalization

**Phase:** 11
**Plan:** 01
**Status:** READY
**Milestone:** v1.3 Path Normalization & Architecture Hardening
**Requirements:** ZPATH-01, ZPATH-02, ZPATH-03 (from v1.1 partial → complete), SYS-08 (new)
**Decisions:** D-01 through D-08 (from 11-CONTEXT.md)
**Waves:** 4
**Tasks:** 8

---

## Goal

Implement robust Zotero attachment path parsing from real-world BBT JSON exports and generate correct Obsidian wikilinks for PDF links. Convert all BBT path formats (absolute Windows, storage: prefix, bare relative) into consistent Vault-relative paths with proper wikilink syntax.

## Wave Structure

| Wave | Tasks | Theme | Parallel |
|------|-------|-------|----------|
| 1 | 1-2 | BBT Path Parsing & Normalization | Sequential |
| 2 | 3-4 | Wikilink Generation & Multi-Attachment | Sequential |
| 3 | 5-6 | Doctor Integration & Error Handling | Sequential |
| 4 | 7-8 | Tests, Docs & Verification | Sequential |

---

## Task 01: Normalize BBT Path Formats in load_export_rows()

**Wave:** 1
**Depends on:** None
**Requirement:** ZPATH-01
**Decision:** D-01, D-04

<read_first>
- `pipeline/worker/scripts/literature_pipeline.py` — Current `load_export_rows()` implementation (lines 733-753)
- `paperforge/pdf_resolver.py` — `resolve_pdf_path()`, `resolve_junction()`
- `paperforge/config.py` — `paperforge_paths()` for vault directory resolution
- `.planning/research/v1.3-zotero-paths.md` — Real-world BBT JSON structure analysis
</read_first>

<action>
1. In `load_export_rows()`, add path normalization BEFORE the existing bare path → `storage:` prefix logic.

2. Implement `_normalize_attachment_path(path, zotero_dir)` helper function:
   - **Input:** `attachments[].path` from BBT JSON, Zotero data directory absolute path
   - **Output:** Normalized path string in one of these formats:
     - `storage:KEY/filename.pdf` (for Zotero storage paths)
     - `absolute:/full/path/to/file.pdf` (for non-storage absolute paths)
     - `relative:path/to/file.pdf` (for vault-relative paths already)

3. Handle three BBT export formats:
   - **Absolute Windows paths** (real-world format): `D:\L\Med\Research\99_System\Zotero\storage\8CHARKEY\filename.pdf`
     - Extract 8-character storage key from path segments
     - Convert to `storage:8CHARKEY/filename.pdf`
   - **storage: prefix**: `storage:KEY/filename.pdf` → pass through as-is
   - **Bare relative**: `KEY/filename.pdf` → prepend `storage:` (existing logic)

4. Store the raw BBT path in a new field `bbt_path_raw` for debugging.

5. Add `zotero_storage_key` field extracted from either:
   - The 8-character directory name in absolute paths
   - The KEY in `storage:KEY/...` format
</action>

<acceptance_criteria>
- `grep -n "def _normalize_attachment_path" pipeline/worker/scripts/literature_pipeline.py` returns a match
- `grep -n "bbt_path_raw" pipeline/worker/scripts/literature_pipeline.py` returns at least 2 matches
- `grep -n "zotero_storage_key" pipeline/worker/scripts/literature_pipeline.py` returns at least 2 matches
- Test with real BBT export: absolute Windows paths are converted to `storage:KEY/filename.pdf`
- Test with existing fixtures: `storage:` prefix paths pass through unchanged
- Test with bare relative paths: `KEY/file.pdf` becomes `storage:KEY/file.pdf` (backward compatible)
</acceptance_criteria>

---

## Task 02: Identify Main PDF vs Supplementary Materials

**Wave:** 1
**Depends on:** Task 01
**Requirement:** ZPATH-02
**Decision:** D-02, D-03

<read_first>
- `pipeline/worker/scripts/literature_pipeline.py` — Current attachment iteration logic
- `.planning/research/v1.3-zotero-paths.md` — Attachment structure examples (title, contentType, path)
</read_first>

<action>
1. Implement `_identify_main_pdf(attachments)` helper function with hybrid strategy:

   **Priority 1 (Primary):**
   - `attachment.title == "PDF"` AND `attachment.contentType == "application/pdf"`

   **Priority 2 (Fallback heuristic):**
   - Filter to `contentType == "application/pdf"` items only
   - Select the LARGEST file by size (if size field available)
   - If sizes are equal or unavailable, select the one with shortest title (main PDFs often have simple titles)

   **Priority 3 (Final fallback):**
   - First PDF attachment in the list

   **Returns:** `(main_pdf_attachment, supplementary_attachments)` where supplementary is a list of all other PDF attachments

2. In `load_export_rows()`, when processing each item:
   - Call `_identify_main_pdf()` on the item's attachments
   - Store main PDF path in `pdf_path` (existing field, now wikilink format)
   - Store supplementary materials in new `supplementary` field as list of wikilinks: `["[[path1]]", "[[path2]]"]`
   - If no PDF attachments found, set `pdf_path: null` and `path_error: not_found`

3. Handle single-attachment items gracefully (no supplementary field if empty).

4. Add `attachment_count` field to track total attachments per item.
</action>

<acceptance_criteria>
- `grep -n "def _identify_main_pdf" pipeline/worker/scripts/literature_pipeline.py` returns a match
- `grep -n "supplementary:" pipeline/worker/scripts/literature_pipeline.py` returns at least 1 match (frontmatter generation)
- `grep -n "attachment_count" pipeline/worker/scripts/literature_pipeline.py` returns at least 2 matches
- Test with single-attachment item: `supplementary` field is absent or empty
- Test with multi-attachment item: `supplementary` contains list of wikilinks
- Test with no PDF attachments: `path_error: not_found` is set
</acceptance_criteria>

---

## Task 03: Generate Obsidian Wikilinks

**Wave:** 2
**Depends on:** Task 01, Task 02
**Requirement:** ZPATH-03
**Decision:** D-05, D-08

<read_first>
- `pipeline/worker/scripts/literature_pipeline.py` — `obsidian_wikilink_for_pdf()`, `absolutize_vault_path()`, `obsidian_wikilink_for_path()` (lines 680-704)
- `paperforge/pdf_resolver.py` — `resolve_junction()` for junction resolution
- `paperforge/config.py` — Vault path configuration
</read_first>

<action>
1. Rewrite `obsidian_wikilink_for_pdf(pdf_path, vault_dir, zotero_dir)` to:
   - Accept normalized `pdf_path` (in `storage:KEY/file.pdf` format)
   - Convert to absolute path using `zotero_dir`:
     - `storage:KEY/file.pdf` → `{zotero_dir}/storage/KEY/file.pdf`
   - Call `absolutize_vault_path()` with junction resolution (D-05)
   - Compute vault-relative path: `os.path.relpath(absolute_pdf_path, vault_dir)`
   - Convert backslashes to forward slashes: `path.replace("\\", "/")`
   - Return wikilink: `[[relative/path/to/file.pdf]]`

2. Update `absolutize_vault_path()` to:
   - Accept `resolve_junction=True` parameter
   - If True and path contains a junction, resolve it to the target path BEFORE computing relative path
   - Use existing `pdf_resolver.resolve_junction()` logic

3. In `sync_writeback_queue()`, update frontmatter generation:
   - `pdf_path: "[[system/Zotero/storage/KEY/文件名.pdf]]"` (wikilink format)
   - Handle Chinese/special characters in filenames (no escaping needed for wikilinks)

4. Add `zotero_dir` to the vault config resolution so `load_export_rows()` has access to it.

5. Ensure all wikilink paths use forward slashes `/` even on Windows (D-08).
</action>

<acceptance_criteria>
- `grep -n "\\[\\[" pipeline/worker/scripts/literature_pipeline.py` returns matches in wikilink generation
- `grep -n "replace.*\\\\\\\\.*" pipeline/worker/scripts/literature_pipeline.py` returns backslash-to-slash conversion
- `grep -n "resolve_junction" pipeline/worker/scripts/literature_pipeline.py` returns at least 2 matches
- Test: Absolute Windows path `D:\Zotero\storage\ABC12345\paper.pdf` → wikilink `[[system/Zotero/storage/ABC12345/paper.pdf]]`
- Test: Path with Chinese characters generates valid wikilink: `[[system/Zotero/storage/KEY/中文.pdf]]`
- Test: Junction-resolved path produces correct relative wikilink
</acceptance_criteria>

---

## Task 04: Update Library-Record Frontmatter with New Fields

**Wave:** 2
**Depends on:** Task 02, Task 03
**Requirement:** SYS-08

<read_first>
- `pipeline/worker/scripts/literature_pipeline.py` — `sync_writeback_queue()` frontmatter generation
- `tests/sandbox/` — Existing library-record fixtures for format reference
</read_first>

<action>
1. Update `sync_writeback_queue()` to include new fields in library-record frontmatter:
   ```yaml
   ---
   zotero_key: "ITEMKEY"
   domain: "骨科"
   title: "论文标题"
   year: 2024
   doi: "10.xxxx/xxxxx"
   collection_path: "子分类"
   has_pdf: true
   pdf_path: "[[system/Zotero/storage/8CHARKEY/文件名.pdf]]"
   bbt_path_raw: "D:\\L\\Med\\...\\storage\\8CHARKEY\\文件名.pdf"
   zotero_storage_key: "8CHARKEY"
   attachment_count: 3
   supplementary:
     - "[[system/Zotero/storage/8CHARKEY/supp1.pdf]]"
     - "[[system/Zotero/storage/8CHARKEY/supp2.pdf]]"
   fulltext_md_path: "..."
   recommend_analyze: true
   analyze: false
   do_ocr: true
   ocr_status: "done"
   deep_reading_status: "pending"
   path_error: ""  # or "not_found", "invalid", "permission_denied"
   analysis_note: ""
   ---
   ```

2. Ensure `path_error` is only present when there's an actual error (empty string or omitted when OK).

3. Update the `yaml_quote()` helper if needed to handle wikilink strings (which contain `[[` and `]]`).

4. Maintain backward compatibility: existing fields (zotero_key, domain, etc.) remain unchanged.
</action>

<acceptance_criteria>
- `grep -n "bbt_path_raw" pipeline/worker/scripts/literature_pipeline.py` returns at least 1 match (in writeback)
- `grep -n "zotero_storage_key" pipeline/worker/scripts/literature_pipeline.py` returns at least 1 match (in writeback)
- `grep -n "attachment_count" pipeline/worker/scripts/literature_pipeline.py` returns at least 1 match (in writeback)
- `grep -n "path_error" pipeline/worker/scripts/literature_pipeline.py` returns at least 1 match (in writeback)
- Generated library-record contains `pdf_path` in wikilink format: `[[...]]`
- `yaml_quote()` correctly handles wikilink strings without breaking YAML parsing
</acceptance_criteria>

---

## Task 05: Enhance paperforge doctor for Junction Detection

**Wave:** 3
**Depends on:** Task 03
**Requirement:** SYS-08
**Decision:** D-07

<read_first>
- `paperforge/ocr_diagnostics.py` — Current doctor command implementation
- `paperforge/config.py` — `paperforge_paths()` and vault configuration
- `paperforge/pdf_resolver.py` — `resolve_junction()`
</read_first>

<action>
1. Add `check_zotero_location()` diagnostic to `paperforge doctor`:
   - Detect if Zotero data directory is inside the Vault or outside
   - If INSIDE: report "Zotero inside vault — direct paths available" (green)
   - If OUTSIDE: report "Zotero outside vault — junction recommended" (yellow) with instructions:
     ```
     Run as Administrator:
     mklink /J "<vault>\system\Zotero" "<zotero_data_dir>"
     ```
   - If junction already exists: verify it points to the correct location

2. Add `check_pdf_paths()` diagnostic:
   - Sample 5 random items from BBT export
   - Verify their `pdf_path` wikilinks resolve to actual files
   - Report: "5/5 PDF paths valid" or "3/5 valid, 2 path errors found"
   - Show specific error types (not_found, invalid, permission_denied)

3. Add `check_wikilink_format()` diagnostic:
   - Verify all `pdf_path` values in library-records use `[[...]]` format
   - Report any legacy bare paths or Markdown links

4. Update doctor output to group path-related diagnostics under a "Path Resolution" section.
</action>

<acceptance_criteria>
- `grep -n "check_zotero_location" paperforge/ocr_diagnostics.py` returns a match
- `grep -n "check_pdf_paths" paperforge/ocr_diagnostics.py` returns a match
- `grep -n "check_wikilink_format" paperforge/ocr_diagnostics.py` returns a match
- `paperforge doctor` output contains "Path Resolution" section header
- Test with Zotero outside vault: doctor shows junction recommendation with exact mklink command
- Test with invalid paths: doctor reports specific error counts and types
</acceptance_criteria>

---

## Task 06: Integrate path_error with Repair and Status

**Wave:** 3
**Depends on:** Task 04, Task 05
**Requirement:** SYS-08
**Decision:** D-06

<read_first>
- `paperforge/commands/repair.py` — Current repair implementation
- `paperforge/commands/status.py` — Current status implementation
- `pipeline/worker/scripts/literature_pipeline.py` — `load_export_rows()` where errors originate
</read_first>

<action>
1. Update `paperforge repair` to:
   - Detect `path_error` fields in library-records
   - Report summary: "Found 12 items with path errors: 8 not_found, 3 invalid, 1 permission_denied"
   - For `not_found` errors: attempt to re-resolve using updated path logic (in case Zotero location changed)
   - For `invalid` errors: flag for manual review with the raw BBT path
   - Add `--fix-paths` flag to auto-attempt path re-resolution

2. Update `paperforge status` to:
   - Show path error count in the status summary
   - If path errors exist, suggest running `paperforge repair --fix-paths`

3. Add `repair_pdf_paths()` function to repair module:
   - Re-run path normalization on items with `path_error`
   - If path now resolves, update `pdf_path` and clear `path_error`
   - If still fails, update `path_error` with the specific reason

4. Ensure repair operations are logged with before/after state.
</action>

<acceptance_criteria>
- `grep -n "path_error" paperforge/commands/repair.py` returns at least 3 matches
- `grep -n "path_error" paperforge/commands/status.py` returns at least 1 match
- `grep -n "repair_pdf_paths" paperforge/commands/repair.py` returns a match
- `grep -n "--fix-paths" paperforge/commands/repair.py` returns a match
- `paperforge repair` shows path error summary when errors exist
- `paperforge status` shows path error count and suggests repair
</acceptance_criteria>

---

## Task 07: Write Tests for Path Normalization

**Wave:** 4
**Depends on:** Task 01, Task 02, Task 03
**Requirement:** ZPATH-01, ZPATH-02, ZPATH-03

<read_first>
- `tests/test_pdf_resolver.py` — Existing PDF resolver tests
- `tests/test_smoke.py` — Smoke test patterns
- `tests/sandbox/ocr-complete/TSTONE001/` — Existing fixture structure
</read_first>

<action>
1. Create `tests/test_path_normalization.py` with test cases:

   **Test class: TestBBTPathNormalization**
   - `test_absolute_windows_path` — Input `D:\Zotero\storage\ABC12345\paper.pdf` → Output `storage:ABC12345/paper.pdf`
   - `test_storage_prefix_path` — Input `storage:ABC12345/paper.pdf` → Output `storage:ABC12345/paper.pdf` (pass-through)
   - `test_bare_relative_path` — Input `ABC12345/paper.pdf` → Output `storage:ABC12345/paper.pdf`
   - `test_path_with_chinese_characters` — Chinese filename handled correctly
   - `test_path_with_spaces` — Filename with spaces handled correctly

   **Test class: TestMainPdfIdentification**
   - `test_title_pdf_primary` — Attachment with title="PDF" selected as main
   - `test_fallback_largest_file` — Largest PDF selected when no title="PDF"
   - `test_fallback_first_pdf` — First PDF selected when sizes equal
   - `test_no_pdf_attachments` — Returns None, sets path_error

   **Test class: TestWikilinkGeneration**
   - `test_basic_wikilink` — `storage:KEY/file.pdf` → `[[system/Zotero/storage/KEY/file.pdf]]`
   - `test_junction_resolution` — Junction resolved before relative path computed
   - `test_forward_slashes` — Output uses `/` not `\`
   - `test_chinese_filename_wikilink` — Chinese characters preserved in wikilink

2. Create test fixtures in `tests/fixtures/`:
   - `bbt_export_absolute.json` — Sample BBT export with absolute Windows paths
   - `bbt_export_storage.json` — Sample with storage: prefix
   - `bbt_export_mixed.json` — Sample with mixed formats

3. Mock `zotero_dir` and `vault_dir` in tests to avoid filesystem dependencies.

4. Ensure all tests run without requiring actual Zotero installation.
</action>

<acceptance_criteria>
- `tests/test_path_normalization.py` exists and contains at least 12 test methods
- `pytest tests/test_path_normalization.py -v` passes (all tests green)
- Test fixtures exist in `tests/fixtures/` directory
- No test requires actual Zotero installation or real PDF files
- Tests cover all three BBT path formats (absolute, storage:, bare)
- Tests cover main PDF identification (all 3 priority levels)
- Tests cover wikilink generation (basic, junction, slashes, Chinese)
</acceptance_criteria>

---

## Task 08: Update Documentation and Final Verification

**Wave:** 4
**Depends on:** Task 05, Task 06, Task 07
**Requirement:** SYS-08

<read_first>
- `AGENTS.md` — Current documentation
- `docs/ARCHITECTURE.md` — Data flow documentation
- `docs/MIGRATION-v1.2.md` — Migration guide format reference
- `command/pf-sync.md` — Command doc format
</read_first>

<action>
1. Update `AGENTS.md`:
   - Add "Path Resolution" section explaining how BBT paths are normalized
   - Document the three supported BBT export formats
   - Explain wikilink format and junction setup
   - Add example library-record showing new fields (`pdf_path`, `supplementary`, `path_error`)

2. Update `docs/ARCHITECTURE.md`:
   - Update data flow diagram to show path normalization stage
   - Add ADR-011: "Zotero Path Normalization Strategy" documenting decisions D-01 through D-08

3. Run full test suite:
   - `pytest tests/` — All tests pass
   - `python -m paperforge doctor` — Operational
   - `python -m paperforge sync --dry-run` — Shows correct wikilink paths
   - `python -m paperforge repair --verbose` — Shows path error summary

4. Run consistency audit:
   - `python scripts/consistency_audit.py` — 4/4 passing

5. Create `11-VERIFICATION.md` documenting:
   - Test results (count and status)
   - Doctor output sample
   - Sample library-record with new fields
   - Any deviations or issues found
</action>

<acceptance_criteria>
- `AGENTS.md` contains "Path Resolution" section header
- `AGENTS.md` shows example wikilink: `[[system/Zotero/storage/KEY/文件名.pdf]]`
- `docs/ARCHITECTURE.md` contains "ADR-011" or path normalization reference
- `pytest tests/` passes with 0 failures (or only pre-existing failures)
- `python scripts/consistency_audit.py` shows 4/4 passing
- `11-VERIFICATION.md` exists in phase directory
- `11-VERIFICATION.md` contains test count and sample library-record
</acceptance_criteria>

---

## Summary

| Requirement | Tasks | Coverage |
|------------|-------|----------|
| ZPATH-01: Parse all BBT path formats | 01, 07 | Complete |
| ZPATH-02: Main PDF identification | 02, 07 | Complete |
| ZPATH-03: Obsidian wikilink generation | 03, 04, 07 | Complete |
| SYS-08: Path error handling & doctor integration | 05, 06, 08 | Complete |

**Risk:** Low — builds on existing path resolution infrastructure
**Complexity:** Medium — mainly string manipulation and path arithmetic
**Estimated Duration:** 2-3 hours
