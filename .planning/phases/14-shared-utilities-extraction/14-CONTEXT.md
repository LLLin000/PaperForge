# Phase 14: Shared Utilities Extraction - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Create `paperforge/worker/_utils.py` as a pure leaf module containing all duplicated utility functions (~1,610 lines removed from 7 workers). All 7 worker modules import from `_utils.py` instead of defining local copies. Backward compatibility preserved via re-exports. Zero behavioral change.

Requirements: CH-01, CH-02, CH-05, TEST-03

Out of scope:
- Deep-reading queue merge (CH-03 — Phase 15)
- Dead code removal / unused imports (CH-04 — Phase 17)
- Consistency audit hook (DX-01 — Phase 17)
- Unit tests for `_utils.py` (TEST-04 — Phase 19)

</domain>

<decisions>
## Implementation Decisions

### File Structure
- **D-01:** `_utils.py` organized by category with section headers:
  - `# --- JSON I/O ---` : `read_json`, `write_json`, `read_jsonl`, `write_jsonl`
  - `# --- YAML Helpers ---` : `yaml_quote`, `yaml_block`, `yaml_list`
  - `# --- String / Path Utils ---` : `slugify_filename`, `_extract_year`
  - `# --- Journal Database ---` : `_JOURNAL_DB`, `load_journal_db`, `lookup_impact_factor`
  - `# --- Constants ---` : `STANDARD_VIEW_NAMES`
  - ~150 lines total
- `load_simple_env` stays in `base_views.py` (defined once, not duplicated across workers)

### Module-Level State
- **D-02:** `_JOURNAL_DB` remains a module-level global cache in `_utils.py`. No `lru_cache` or class wrapping — simplest approach, zero behavioral change, read-only after first load so shared state is safe.

### Naming
- **D-03:** `STANDARD_VIEW_NAMES` (no underscore prefix) — matches existing `base_views.py` export, consistent with current behavior.

### Leaf Module Constraint
- **D-04:** `_utils.py` imports ONLY from stdlib and `paperforge.config`. Zero imports from `paperforge.worker.*` or `paperforge.commands.*`. Circular import firebreak.

### Backward Compatibility
- **D-05:** Each original worker module retains re-exports with `# Re-exported from _utils.py` comments at the site of the original function definition.
- **D-06:** All 7 workers (`sync.py`, `ocr.py`, `deep_reading.py`, `repair.py`, `status.py`, `update.py`, `base_views.py`): replace local function definitions with `from paperforge.worker._utils import read_json, write_json, ...`.

### Module-Level Logger
- **D-07:** `_utils.py` gets `logger = logging.getLogger(__name__)` following Phase 13 pattern. Each worker retains its own `logger = logging.getLogger(__name__)` unchanged.

### the agent's Discretion
- Exact order of functions within each category section
- Whether to use `"""docstrings"""` on re-export imports
- Split strategy: all 7 workers in one commit vs sequential
- Error handling in `read_json(write_json` etc. (keep existing bare `json.loads`/`json.dumps`)
- Whether to inline `_extract_year` as a module-private function (keep underscore prefix)

</decisions>

<canonical_refs>
## Canonical References

### Requirements (Phase 14 scope)
- `.planning/REQUIREMENTS.md` — CH-01 (function list for _utils.py), CH-02 (worker migration), CH-05 (test pass), TEST-03 (regression bar)
- `.planning/ROADMAP.md` §Phase 14 — Success criteria, scope boundary, leaf module constraint
- `.planning/PROJECT.md` — Leaf module constraint rationale, v1.4 architecture decisions

### Existing Code (source of truth)
- `paperforge/worker/base_views.py:47-134` — Canonical source of all utility function implementations (most authoritative copy)
- `paperforge/worker/base_views.py:26-29` — `STANDARD_VIEW_NAMES` definition
- `paperforge/worker/deep_reading.py:51-140` — Second copy of same utilities (confirms identical behavior)
- `paperforge/worker/sync.py:47-135` — Third copy
- `paperforge/worker/ocr.py:53-142` — Fourth copy
- `paperforge/worker/repair.py:55-145` — Fifth copy
- `paperforge/worker/status.py:49-140` — Sixth copy
- `paperforge/worker/update.py:47-135` — Seventh copy

### Patterns (reference for module structure)
- `paperforge/logging_config.py` — Single-purpose module pattern (Phase 13 precedent)
- `paperforge/config.py` — Config module pattern (single-purpose, pure functions)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- All 7 workers: identical utility function blocks ~15 lines each, only difference is module-level `_JOURNAL_DB` position
- `base_views.py:47-134` is the cleanest copy — use as the migration source of truth
- `_utils.py` will be ~150 lines; compare to `logging_config.py` (69 lines) for module-size precedent

### Established Patterns
- Phase 13 `logging_config.py`: single-purpose module with no imports from workers — exact pattern `_utils.py` should follow
- Phase 12 architecture: workers live under `paperforge/worker/`, import from each other via lazy imports to break cycles
- `_utils.py` must NOT use lazy imports — it's a leaf module, no cycles allowed

### Integration Points
- `paperforge/worker/__init__.py` — No changes needed (exports are function-level, not utility-level)
- Each worker module — Replace top-level function definitions with `from paperforge.worker._utils import ...`
- Tests — `pytest tests/ -x` after migration verifies no regression
- `paperforge/worker/_utils.py` — New file, lives alongside the 7 workers

</code_context>

<specifics>
## Specific Ideas

- "分组，按 JSON I/O / YAML / 字符串 / 期刊数据库 分组，每组大约 3-4 个函数"
- "_JOURNAL_DB 保持 module global，简单，零行为变更"
- "STANDARD_VIEW_NAMES 保持现状，不带下划线"
- "提取过程不应该改变任何行为 — 纯重构"

</specifics>

<deferred>
## Deferred Ideas

- Deep-reading queue merge into `_utils.py` — Phase 15 (CH-03)
- Unit tests for `_utils.py` functions — Phase 19 (TEST-04)
- Consistency audit for duplicate function detection — Phase 17 (DX-01)
- Dead code / unused import removal — Phase 17 (CH-04)

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-shared-utilities-extraction*
*Context gathered: 2026-04-27*
