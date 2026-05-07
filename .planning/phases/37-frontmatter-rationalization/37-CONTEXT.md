# Phase 37: Frontmatter Rationalization - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Formal note frontmatter is slimmed to identity fields + workflow flags + pdf_path; all internal/derived data moves to per-workspace paper-meta.json. library_record_markdown() is removed.

Key decisions already made during milestone questioning:
- Formal note frontmatter keeps: title, year, journal, first_author, doi, pmid, zotero_key, domain, abstract, tags (identity) + has_pdf, do_ocr, analyze, ocr_status, deep_reading_status (workflow) + pdf_path
- Removed from frontmatter: paper_root, main_note_path, fulltext_path, deep_reading_path, ai_path (workspace paths — derivable), ocr_job_id, ocr_md_path, ocr_json_path (OCR infrastructure), analysis_note (unused), type (hardcoded "article"), bbt_path_raw, zotero_storage_key, attachment_count (debug fields)
- Per-workspace paper-meta.json stores: ocr_job_id, ocr_md_path, ocr_json_path, health dict, maturity breakdown, paperforge_version, migrated_from (for library-record upgrades)
- _build_entry() continues to produce full entry dicts for canonical index; frontmatter_note() writes only the slim subset
- library_record_markdown() removed from sync.py

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure phase. Key decisions already settled during milestone questioning. Use ROADMAP success criteria as the spec.

### Reference Vault Learnings
See REQUIREMENTS.md §Reference Vault Learnings for working patterns from D:\L\Med\Research_LitControl_Sandbox.

</decisions>

<code_context>
## Existing Code Insights

### Files to Modify
- `paperforge/worker/sync.py` — `frontmatter_note()` (lines ~1598-1670), `library_record_markdown()` (lines ~618-677), `run_index_refresh()` (lines ~1752-1829)
- `paperforge/worker/asset_index.py` — `_build_entry()` (lines ~213-332) — produces the entry dict fed to both frontmatter_note() and the canonical index
- `paperforge/worker/_utils.py` — shared utilities (write_json, read_json, yaml operations)

### Established Patterns
- `write_json()` in _utils.py for atomic JSON writes
- `atomic_write_index()` pattern in asset_index.py for tempfile + os.replace + filelock
- Frontmatter YAML serialization uses `yaml.dump()` with allow_unicode=True, default_flow_style=False

### New Files
- `paperforge/worker/paper_meta.py` — new module for paper-meta.json read/write operations

</code_context>

<specifics>
## Specific Ideas

- paper-meta.json format: flat JSON object, fields: ocr_job_id (str|null), ocr_md_path (str|null), ocr_json_path (str|null), health (dict), maturity (dict with level/level_name/checks/blocking), paperforge_version (str), migrated_from (dict|null with library_record_path and timestamp)
- paper-meta.json written during _build_entry() or immediately after frontmatter_note()
- Existing tests in tests/test_asset_index.py, tests/test_migration.py, tests/test_context.py must be updated for field changes

</specifics>

<deferred>
## Deferred Ideas

- Plugin dashboard verification — Phase 41
- Base view regeneration — Phase 39
- Library-record migration — Phase 40

</deferred>
