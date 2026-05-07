# Phase 25: Surface Convergence, Doctor & Repair - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Surface convergence: make `paperforge status`, plugin dashboard, Base views, doctor, and repair all consume the same lifecycle/health/maturity data from the canonical index. No more independent computation across surfaces.

Does NOT cover AI context packs (Phase 26) or the LLMWiki concept network (v1.7).

</domain>

<decisions>
## Implementation Decisions

### status --json output
- **D-01:** `paperforge status --json` reads from canonical index instead of filesystem scanning.
- **D-02:** Output includes: paper_count, lifecycle_level_counts, health_aggregate (4 dimensions with count per status), maturity_distribution.
- **D-03:** Legacy `run_status()` in `status.py` delegates to `asset_index.py` + `asset_state.py` for derived data.
- **D-04:** Filesystem scan is retained as fallback when canonical index is unavailable.

### Plugin Dashboard
- **D-05:** Plugin reads `formal-library.json` directly via `readFileSync()` instead of spawning `python -m paperforge status --json`.
- **D-06:** Only the envelope metadata and summary fields are read (not full items list) — keeps dashboard fast.
- **D-07:** Existing `_fetchStats()` method refactored to read the JSON file directly, falling back to Python CLI if file is missing.

### Doctor
- **D-08:** New "Index Health" section in `paperforge doctor` output, aggregating from canonical index health fields.
- **D-09:** Shows: PDF Health (OK/warn/fail), OCR Health (OK/warn/fail), Note Health, Asset Health counts.
- **D-10:** Existing checks unchanged — this is additive.

### Repair
- **D-11:** Repair keeps source-first + rebuild pattern: fix source artifacts, then rebuild canonical index. Never edits index directly.
- **D-12:** After repair, `repair.py` calls `rebuild_index()` to regenerate the canonical index.

### Base views
- **D-13:** Base `build_base_views()` adds lifecycle, maturity_level, and next_step columns.
- **D-14:** Old `has_pdf`, `do_ocr`, `analyze`, `ocr_status` columns removed from Base views (superseded by lifecycle).
- **D-15:** Sort order: lifecycle ascending (show auto-computed readiness, not raw fields).
- **D-16:** Base filters updated to use lifecycle instead of raw status combinations.

### the agent's Discretion
- Exact format of plugin dashboard summary (how much of the index to cache in memory)
- Column names in Base views (Chinese labels: 生命周期/就绪状态 等)
- Whether Doctor Index Health is a separate section or merged into existing checks

</decisions>

<canonical_refs>
## Canonical References

### Phase scope and requirements
- `.planning/ROADMAP.md` §Phase 25 — Goal: "make status, dashboard, Bases, doctor, repair consume same canonical semantics"
- `.planning/REQUIREMENTS.md` — SURF-01..04, MIG-01, MIG-03, MIG-04
- `.planning/phases/22-configuration-truth-compatibility/22-CONTEXT.md` — Plugin config truth (reads paperforge.json)
- `.planning/phases/23-canonical-asset-index-safe-rebuilds/23-CONTEXT.md` — Canonical index format
- `.planning/phases/24-derived-lifecycle-health-maturity/24-CONTEXT.md` — lifecycle/health/maturity/next_step fields

### Source code
- `paperforge/worker/status.py` — Current `run_status()` and `run_doctor()` **Primary refactoring target**
- `paperforge/plugin/main.js` — Current dashboard, `_fetchStats()` (line 261), `_renderStats()` (line 282)
- `paperforge/worker/base_views.py` — `build_base_views()` (line 44), `ensure_base_views()` (line 378)
- `paperforge/worker/repair.py` — `run_repair()` (line 173)
- `paperforge/worker/asset_index.py` — `build_index()`, `refresh_index_entry()`
- `paperforge/worker/asset_state.py` — `compute_lifecycle()`, `compute_health()`, `compute_maturity()`, `compute_next_step()`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `paperforge/worker/asset_index.py` `build_index()` — Can be called after repair to regenerate canonical index
- `paperforge/worker/asset_state.py` — All four derivation functions ready to consume
- `paperforge/worker/status.py:404-528` — Current `run_status()` — full rewrite target
- `paperforge/plugin/main.js:261-278` — Current `_fetchStats()` — refactor to direct JSON read

### Established Patterns
- Plugin reads `paperforge.json` directly (Phase 22). Same pattern for `formal-library.json`.
- Base views are Python-generated `.base` files — fully under `build_base_views()` control.
- Doctor checks are additive in `run_doctor()`: "Index Health" as new section.

### Integration Points
- `paperforge/worker/status.py:404` — `run_status()` — change from filesystem to index-based counting
- `paperforge/plugin/main.js:261` — `_fetchStats()` — change from CLI spawn to JSON file read
- `paperforge/worker/base_views.py:44` — `build_base_views()` — replace columns
- `paperforge/worker/repair.py:173` — `run_repair()` — add `build_index()` call after fix

</code_context>

<specifics>
## Specific Ideas

- Plugin should watch `formal-library.json` for changes and auto-refresh dashboard (optional, can defer if too complex).
- Status --json should use the canonical index summary so that `paperforge status` is instant even on large libraries.
- Base views should preserve user customization via the PAPERFORGE_VIEW_PREFIX merge logic already in place.

</specifics>

<deferred>
None — discussion stayed within phase scope
</deferred>

---

*Phase: 25-surface-convergence-doctor-repair*
*Context gathered: 2026-05-04*
