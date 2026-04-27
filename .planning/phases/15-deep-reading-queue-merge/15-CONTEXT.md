# Phase 15: Deep-Reading Queue Merge - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Merge two divergent queue-scanning implementations (`worker/deep_reading.py` and `skills/ld_deep.py`) into a single canonical `scan_library_records()` in `_utils.py`. Pure refactoring -- zero behavioral change to queue filtering, status output, or sync behavior.

Requirements: CH-03

Out of scope:
- Dead code removal / unused imports (CH-04 -- Phase 17)
- Unnecessary delegation wrappers cleanup (Phase 17)
- Unit tests for `_utils.py` (TEST-04 -- Phase 19)
- Pre-commit hook / consistency audit (DX-01 -- Phase 17)

</domain>

<decisions>
## Implementation Decisions

### Function Placement
- **D-01:** `scan_library_records()` lives in `paperforge/worker/_utils.py`
  - Already the shared utilities hub (Phase 14)
  - Follows `_utils.py`'s leaf module constraint (stdlib + `paperforge.config` only)

### Function Signature & Return Value
- **D-02:** Signature: `scan_library_records(vault: Path) -> list[dict]`
  - Pure data acquisition -- no categorization, no status sync
- **D-03:** Return value structure (`list[dict]`):
  ```python
  [
    {
        "zotero_key": str,
        "domain": str,
        "title": str,
        "analyze": bool,
        "do_ocr": bool,
        "deep_reading_status": str,    # "pending" | "done"
        "ocr_status": str,             # "pending" | "processing" | "done" | "failed"
        "note_path": Path | None,      # resolved formal note path, None if not found
    }
  ]
  ```
  - Returns ALL library records with analyze=true -- not only those with deep_reading_status!=done
  - Caller filters as needed (e.g., `run_deep_reading()` further filters by status)
  - OCR status looked up from `meta.json` if available, defaults to `"pending"`
  - `note_path` resolved via existing `_resolve_formal_note_path()` logic

### Status Sync Separation
- **D-04:** `scan_library_records()` does ONLY scanning -- NO side effects
- **D-05:** `run_deep_reading()` in `deep_reading.py` retains:
  1. Import scanning from `_utils.py`
  2. Status sync (`deep_reading_status` frontmatter update)
  3. Queue categorization (ready/waiting/blocked)
  4. Markdown report generation
  5. `print()` summary to stdout

### Backward Compatibility
- **D-06:** `deep_reading.py:run_deep_reading()` -- internal refactor: uses `scan_library_records()` from `_utils.py` instead of inline scan. Re-export comment at original scan site.
- **D-07:** `ld_deep.py:scan_deep_reading_queue()` -- becomes a thin wrapper that calls `scan_library_records()` and filters/returns. Re-export comment at original definition site.

### ld_deep.py Import Strategy
- **D-08:** Module-level direct import: `from paperforge.worker._utils import scan_library_records`
  - Same pattern as existing `from paperforge.config import ...` (already used via function-level import)
  - Cleaner than function-level lazy import
  - No circular dependency risk (_utils.py is a leaf)

### OCR Status Lookup
- **D-09:** `scan_library_records()` reads `meta.json` at `paths['ocr'] / zotero_key / meta.json` using `read_json()`
  - Same logic as both current implementations
  - Graceful: if `meta.json` doesn't exist or is unreadable, `ocr_status` defaults to `"pending"`

### the agent's Discretion
- Exact error handling for malformed library-record frontmatter (keep current lenient regex approach)
- Sorting of returned list (current `ld_deep.py` sorts by status/domain/key -- caller can sort, not the shared function's concern)
- Whether to include `do_ocr` field in return dict (useful for caller categorization)

</decisions>

<canonical_refs>
## Canonical References

### Requirements (Phase 15 scope)
- `.planning/REQUIREMENTS.md` -- CH-03 (merge queue scanning into _utils.py)
- `.planning/ROADMAP.md` -- Phase 15 success criteria (4 items)

### Source Files (current implementations to merge)
- `paperforge/worker/deep_reading.py:133-232` -- `run_deep_reading()` (combined scan + sync + report)
- `paperforge/skills/literature-qa/scripts/ld_deep.py:1161-1216` -- `scan_deep_reading_queue()` (pure scan)

### Prior Phase Context
- `.planning/phases/14-shared-utilities-extraction/14-CONTEXT.md` -- _utils.py leaf module constraints, conventions
- `.planning/phases/13-logging-foundation/13-CONTEXT.md` -- Logger hierarchy, verbose patterns

### Supporting Functions
- `paperforge/worker/deep_reading.py` -- `_resolve_formal_note_path()` (needed by scan_library_records for note_path resolution; may need extraction to _utils.py or inline in scan)
- `paperforge/worker/sync.py` -- `load_export_rows()`, `has_deep_reading_content()`
- `paperforge/worker/ocr.py` -- `validate_ocr_meta()`
- `paperforge/config.py` -- `paperforge_paths()`, `load_domain_config()`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_utils.py` already has `read_json()` for OCR meta.json reading
- `deep_reading.py` already has `_resolve_formal_note_path()` function -- scan_library_records may need this or a simplified version

### Established Patterns
- Phase 14 `_utils.py` migration pattern: extract to shared module + re-export with comment in original module
- `ld_deep.py` function-level imports for `paperforge.config` -- precedent for cross-package import
- `deep_reading.py` regex-based frontmatter extraction (re.search multiline) -- to be consolidated

### Integration Points
- `paperforge/worker/_utils.py` -- new function `scan_library_records()` added, in a new section `# --- Deep-Reading Queue ---`
- `paperforge/worker/deep_reading.py` -- replace inline scan with call to `scan_library_records()`
- `paperforge/skills/literature-qa/scripts/ld_deep.py` -- replace inline scan with call to `scan_library_records()`, add module-level import

</code_context>

<specifics>
## Specific Ideas

- "scan_library_records() 只返回数据，不做分类。Caller 自己做 ready/waiting/blocked 过滤和状态同步。"
- "ld_deep.py 用模块级直接导入，和已有 paperforge 导入一致"
- "run_deep_reading() 保留状态同步和数据报告的职责"

</specifics>

<deferred>
## Deferred Ideas

- Dead code removal / unused imports -- Phase 17
- Unit tests for `scan_library_records()` -- Phase 19
- Standalone `scan_library_records()` CLI command -- not in scope; functionality accessed through `deep-reading` CLI and Agent

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 15-deep-reading-queue-merge*
*Context gathered: 2026-04-27*
