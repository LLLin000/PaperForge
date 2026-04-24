# Phase 11: Zotero Path Normalization - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement robust Zotero attachment path parsing from real-world BBT JSON exports and generate correct Obsidian wikilinks for PDF links.

Scope:
- Parse BBT JSON `attachments[].path` (absolute Windows paths, storage: prefix, bare relative)
- Extract Zotero 8-bit storage key from `uri`/`select` fields
- Convert absolute path → Vault-relative path
- Generate Obsidian wikilinks (`[[relative/path]]`)
- Handle multi-attachment items (identify main PDF vs supplementary)
- Handle Chinese/special characters in filenames
- Support backward-compatible `storage:` prefix and bare relative paths

Out of scope:
- Repair scan performance optimization (Phase 12)
- Pipeline module cleanup (Phase 12)
- Skill scripts integration (Phase 12)
- Consistency audit CI (Phase 13)
</domain>

<decisions>
## Implementation Decisions

### Path Normalization Timing
- **D-01:** Convert paths in `load_export_rows()` stage (unified conversion)
- All BBT input formats normalized to Vault-relative path at ingestion time
- Downstream code (wikilink generation, PDF resolver) works with consistent relative paths
- Rationale: Avoids repeated conversion logic, matches existing `storage:` prefix normalization pattern

### Multi-Attachment Handling
- **D-02:** Main PDF identification uses hybrid strategy:
  1. Primary: `title == "PDF"` AND `contentType == "application/pdf"`
  2. Fallback: Analyze file size + title structure heuristics
  3. Final fallback: First PDF attachment
- **D-03:** Supplementary materials stored in `supplementary` frontmatter field
  - Format: `supplementary: ["[[path1]]", "[[path2]]"]`
  - Title determination for supplementary materials deferred to future phase

### BBT Export Format Support
- **D-04:** Code adapts to ALL BBT export formats without requiring user configuration
  - Absolute Windows paths (`D:\...\storage\KEY\file.pdf`) — **real-world format**
  - `storage:` prefixed paths (`storage:KEY/file.pdf`)
  - Bare relative paths (`KEY/file.pdf`)
- No dependency on BBT configuration changes
- Rationale: PaperForge Lite philosophy — minimal user configuration

### Junction Handling
- **D-05:** Resolve junctions in `absolutize_vault_path()` before computing relative paths
- Reuse existing `pdf_resolver.resolve_junction()` logic
- Ensures wikilink paths are correct even when Vault contains junctioned directories

### Error Handling
- **D-06:** Granular `path_error` frontmatter field for failed path resolution
  - `path_error: not_found` — File does not exist
  - `path_error: invalid` — Path format unrecognizable
  - `path_error: permission_denied` — Cannot read file
  - Empty/omitted when no error
- `paperforge repair` can detect and surface path errors

### Zotero Directory Link Strategy
- **D-07:** Smart detection of Zotero data directory location
  - If Zotero is INSIDE Vault → use direct relative paths, no junction needed
  - If Zotero is OUTSIDE Vault → `paperforge doctor` detects and recommends creating junction
  - Junction target: `<vault>/system/Zotero/` → `<zotero_data_dir>`
- Rationale: Supports both setups transparently

### Wikilink Standard
- **D-08:** Obsidian wikilink format: `[[relative/path/with/slashes]]`
  - No Markdown standard links `[text](path)`
  - Forward slashes `/` even on Windows
  - Path relative to Vault root
- Rationale: Enables Obsidian graph view and backlink functionality

### the agent's Discretion
- Exact file size thresholds for main PDF fallback heuristics
- Error message wording for path_error states
- Whether to include supplementary materials in OCR queue (default: no)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Path Resolution
- `paperforge/pdf_resolver.py` — Existing path resolution logic (absolute, relative, junction, storage)
- `paperforge/config.py` — Vault path configuration and `paperforge_paths()`

### BBT Export Format
- `.planning/research/v1.3-zotero-paths.md` — Real-world BBT JSON structure analysis
- `pipeline/worker/scripts/literature_pipeline.py` §733-753 — `load_export_rows()` attachment handling

### Wikilink Generation
- `pipeline/worker/scripts/literature_pipeline.py` §680-704 — `obsidian_wikilink_for_pdf()`, `absolutize_vault_path()`, `obsidian_wikilink_for_path()`

### Architecture
- `docs/ARCHITECTURE.md` — Two-layer design, data flow, directory structure rationale
- `paperforge/commands/__init__.py` — Command registry pattern for new commands

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `paperforge/pdf_resolver.py` — `resolve_pdf_path()`, `resolve_junction()`, `is_valid_pdf()`
- `pipeline/worker/scripts/literature_pipeline.py` — `load_export_rows()`, `obsidian_wikilink_for_pdf()`
- `paperforge/config.py` — `paperforge_paths()` for vault directory resolution

### Established Patterns
- Path normalization in `load_export_rows()` (bare path → `storage:` prefix)
- Frontmatter YAML generation with `yaml_quote()` helper
- `paperforge/commands/` package for CLI command modules

### Integration Points
- `load_export_rows()` — Where BBT JSON is parsed; add absolute path normalization here
- `sync_writeback_queue()` — Where library-records are written; ensure `pdf_path` uses wikilink
- `paperforge doctor` — Add junction detection and path validation

</code_context>

<specifics>
## Specific Ideas

- "如果 Zotero 库在 Vault 外，必须建立 junction；如果在 Vault 内，直接用相对路径"
- "系统应该允许用户后期修改路径，比如转移 zotero 库的位置，更改 base、literature 这些文件夹的名称"
- Obsidian wikilink syntax: `[[system/Zotero/storage/KEY/文件名.pdf]]`
- Windows paths use `\` in filesystem but `/` in wikilinks

</specifics>

<deferred>
## Deferred Ideas

- Supplementary material title determination strategy (multi-attachment metadata)
- User-configurable path overrides for base/literature directories after initial setup
- Repair scan performance optimization (O(n*m) → O(n)) — Phase 12
- Pipeline module boundary cleanup (`pipeline/` → `paperforge/`) — Phase 12
- Skill scripts integration (`skills/` → `paperforge/skills/`) — Phase 12

</deferred>

---

*Phase: 11-zotero-path-normalization*
*Context gathered: 2026-04-24*
