# Phase 24: Derived Lifecycle, Health & Maturity - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Compute lifecycle state, health findings, maturity level, and next-step recommendations from source artifacts (canonical index, OCR meta, formal notes). Introduce `paperforge/worker/asset_state.py` as the derivation engine. No new files by users, no hand-edited state fields.

Does NOT cover surface convergence, plugin dashboard updates, or AI context packs -- those are Phases 25-26.

</domain>

<decisions>
## Implementation Decisions

### Lifecycle states
- **D-01:** Six derived lifecycle states: `imported` → `indexed` → `pdf_ready` → `fulltext_ready` → `deep_read_done` → `ai_context_ready`.
- **D-02:** Derivation rules from canonical index fields:
  - `pdf_ready`: `has_pdf == true`
  - `fulltext_ready`: `ocr_status == "done"`
  - `deep_read_done`: `deep_reading_status == "done"`
  - `ai_context_ready`: `fulltext_ready AND deep_read_done AND all workspace paths present`

### Health dimensions
- **D-03:** Four health dimensions plus aggregated Library Health:
  - **PDF Health**: `path_error` non-empty, `pdf_path` validity
  - **OCR Health**: `ocr_status` in {failed, blocked, nopdf}, results integrity
  - **Note Health**: formal note exists, frontmatter not stale
  - **Asset Health**: `fulltext_path`, workspace paths present
- **D-04:** Health derivation is a pure function over canonical index entry: `compute_health(entry) -> dict[str, str]`
- **D-05:** Health findings include concrete fix paths (e.g., "Run `paperforge ocr`" for OCR pending)

### Maturity scoring
- **D-06:** Library Maturity / Workflow Level scored 1-6: Metadata → PDF → Fulltext → Figure → AI → Review Ready.
- **D-07:** Each level displays which checks passed and which are still blocking.
- **D-08:** Maturity is computed per paper. Library-level maturity is the aggregate (count per level).

### Next-step recommendations
- **D-09:** Each paper gets one recommended next step: `sync` | `ocr` | `repair` | `/pf-deep` | `rebuild index` | `ready`

### Module
- **D-10:** New module `paperforge/worker/asset_state.py` exports `compute_lifecycle(entry)`, `compute_health(entry)`, `compute_maturity(entry)`, `compute_next_step(entry)`.
- **D-11:** Lifecycle/health/maturity/next-step are embedded in canonical index entries during `build_index`/`refresh_index_entry`.

### the agent's Discretion
- Exact `ai_context_ready` definition (whether it requires additional conditions beyond fulltext + deep_read)
- Figure-level maturity dependency (whether `figure_count > 0` is required for "Figure Ready" level)
- Health dimension display names (Chinese labels: PDF健康, OCR健康, etc.)

### Folded Todos
None.

</decisions>

<canonical_refs>
## Canonical References

### Phase scope and requirements
- `.planning/ROADMAP.md` §Phase 24 — Goal: "source-derived readiness, health findings, maturity, next steps"
- `.planning/REQUIREMENTS.md` — STATE-01..04, AIC-01
- `.planning/research/SUMMARY.md` §Phase 3 — Health/lifecycle architecture
- `.planning/phases/23-canonical-asset-index-safe-rebuilds/23-CONTEXT.md` — D-12 workspace paths in canonical index

### Source code
- `paperforge/worker/asset_index.py` — Canonical index generation, entry structure, `_build_entry()`. **Primary integration point.**
- `paperforge/worker/asset_index.py` §`CURRENT_SCHEMA_VERSION` — Index schema version
- `paperforge/worker/status.py` — Existing status/doctor checks (some health logic already exists here)
- `paperforge/worker/deep_reading.py` — Deep reading status derivation
- `paperforge/worker/ocr.py` — OCR status tracking

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `paperforge/worker/asset_index.py` `_build_entry()` — Where lifecycle/health fields should be added to index entries
- `paperforge/worker/status.py` `run_status()` — Existing counting logic that could be replaced by index-derived data
- `paperforge/worker/status.py` `check_pdf_paths()` — Existing PDF health check pattern

### Established Patterns
- Pure function pattern: `asset_index.py` uses standalone functions with explicit vault/path params
- Status derivation from source artifacts (no hand-edited fields) already done for `deep_reading_status` in `deep_reading.py`

### Integration Points
- `asset_index.py:build_index()` — Add lifecycle/health/maturity/next-step computation to index entries
- `asset_index.py:refresh_index_entry()` — Same computation during incremental refresh
- `status.py:run_status()` — Can read lifecycle/health from index instead of recomputing

</code_context>

<specifics>
## Specific Ideas

- Lifecycle/health/maturity should be machine-only fields in the canonical index JSON (not mirrored to frontmatter).
- Health findings should be precise enough to power `paperforge doctor` output without re-scanning filesystem.

</specifics>

<deferred>
None -- discussion stayed within phase scope
</deferred>

---

*Phase: 24-derived-lifecycle-health-maturity*
*Context gathered: 2026-05-04*
