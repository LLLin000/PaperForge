# Phase 18: Documentation + CHANGELOG + UX Polish - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete all user-facing and maintainer-facing documentation for v1.4: CHANGELOG, CONTRIBUTING, migration guide, doc auditing, chart-reading INDEX, command naming alignment. One functional change: `auto_analyze_after_ocr` config option.

Requirements: DX-03, DX-04, UX-01, UX-02, UX-03, UX-04, DOCS-01, DOCS-02, DOCS-03, DOCS-04

Out of scope:
- E2E/integration tests (Phase 19)
- Unit tests for `_utils.py` (Phase 19)

</domain>

<decisions>
## Implementation Decisions

### auto_analyze_after_ocr (UX-01)
- **D-01:** The `auto_analyze_after_ocr` option lives in `paperforge.json` (already at vault root, loaded by update system). Add `"auto_analyze_after_ocr": false` to the top-level schema.
- **D-02:** Hook point: in `run_ocr()`, after the poll loop detects OCR completion (line 1498, `meta["ocr_status"] = "done"`), immediately set `analyze: true` in the library-record frontmatter at `library_records/<domain>/<key>.md`. This happens before the final `_sync.run_selection_sync(vault)` call.
- **D-03:** Config read: load `paperforge.json` at start of `run_ocr()` into a local variable. No new config module needed — use `json.loads()` via `read_json()` from `_utils.py`.

### chart-reading INDEX.md (UX-03)
- **D-04:** Order by approximate biomedical commonness (most common first): bar/column → forest plot → line → scatter → ROC → survival (Kaplan-Meier) → box plot → heatmap → flow diagram → pie → violin → waterfall → volcano → bubble → correlation matrix → dendrogram → nomogram → calibration → QQ plot. ~19 types total.

### Documentation structure
- **D-05:** `CHANGELOG.md` at vault root, Keep a Changelog format. v1.0 through v1.4 sections. Update `paperforge.json` `changelog_url` if needed.
- **D-06:** `CONTRIBUTING.md` at vault root. Sections: dev setup, pre-commit hooks, test workflow, architecture overview, code conventions.
- **D-07:** `docs/MIGRATION-v1.4.md` following v1.2 migration document pattern. Covers: dual-output logging, retry behavior, env vars, pre-commit setup, ruff config, auto_analyze_after_ocr.
- **D-08:** ADR-012 (Shared Utilities Extraction) and ADR-013 (Dual-Output Logging) added as subsections in `docs/ARCHITECTURE.md`.
- **D-09:** AGENTS.md section 1: add "What to type where" table mapping `/pf-*` to `paperforge *`. No structural changes.
- **D-10:** README.md: remove orphaned legacy code lines at ~l.102-104. Review all docs for similar rendering issues.
- **D-11:** ROADMAP.md: update v1.4 plan counts and mark completed phases.

### the agent's Discretion
- Order of files within CHANGELOG.md sections
- Exact phrasing in CONTRIBUTING.md and MIGRATION-v1.4.md
- Specific ARCHITECTURE.md ADR formatting
- Whether to split into 2 plans or 1
- INDEX.md format (table vs list)

</decisions>

<canonical_refs>
## Canonical References

### Requirements (Phase 18 scope)
- `.planning/REQUIREMENTS.md` — DX-03/04, UX-01/02/03/04, DOCS-01/02/03/04 full specs
- `.planning/ROADMAP.md` §Phase 18 — Success criteria, scope boundary

### Existing docs (files to create/modify)
- `paperforge.json` — Add auto_analyze_after_ocr field (vault root)
- `paperforge/worker/ocr.py:1485-1514` — Hook point for auto_analyze_after_ocr (poll completion)
- `paperforge/worker/ocr.py:1586-1590` — Final sync calls (after hook)
- `docs/MIGRATION-v1.2.md` — Template format for MIGRATION-v1.4.md
- `docs/ARCHITECTURE.md` — Target for ADR-012 and ADR-013
- `AGENTS.md` §1 — Target for command mapping table
- `README.md` ~l.102-104 — Orphaned legacy code lines to remove
- `.planning/ROADMAP.md` §18 — Update plan counts

### Reference patterns
- `.planning/phases/14-shared-utilities-extraction/14-CONTEXT.md` — Prior CONTEXT.md for ADR-012 source material
- `.planning/phases/13-logging-foundation/13-CONTEXT.md` — Prior CONTEXT.md for ADR-013 source material
- `paperforge.json` lines 1-28 — Existing schema to extend
- `paperforge/worker/_utils.py:19-21` — `read_json()` for loading paperforge.json

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_utils.py::read_json()` — For loading paperforge.json config
- `yaml_quote()` — For writing analyze=true to frontmatter
- Phase 13/14 CONTEXT.md files — Source material for ADR-012 and ADR-013
- `docs/MIGRATION-v1.2.md` — Template for v1.4 migration doc
- `CHANGELOG.md` — Does not exist yet, will be new file

### Established Patterns
- Keep a Changelog format (per DX-03)
- Phase 13 CONTEXT.md → ADR-013 (dual-output logging)
- Phase 14 CONTEXT.md → ADR-012 (shared utilities extraction)
- `paperforge.json` extends existing config (add top-level key with default false)
- Frontmatter edits via `record_text = record_path.read_text(); new_text = re.sub(...); record_path.write_text(new_text)` — same pattern as deep_reading.py sync

### Integration Points
- `paperforge.json` — Add `auto_analyze_after_ocr: false`
- `paperforge/worker/ocr.py:1498` — After `meta["ocr_status"] = "done"`, check flag and update library-record
- `AGENTS.md` §1 — Add command mapping table after the existing command table
- `docs/ARCHITECTURE.md` — Add ADR sections (alphabetical/numeric order with existing ADRs)

</code_context>

<specifics>
## Specific Ideas

- auto_analyze_after_ocr hook: immediately after poll completion, read library-record, set analyze=true, write back. Simple regex replace on frontmatter line.
- chart-reading INDEX.md: table format (Chart Type | Reading Guide | Commonness), ordered by commonness
- Keep docs files clean — one focused section per requirement
- No new Python dependencies needed

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 18-documentation-ux-polish*
*Context gathered: 2026-04-27*
