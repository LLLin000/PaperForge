# Phase 50: Repair Blind Spots - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Repair worker three-way divergence detection covers all 6 divergence types (was missing the `ocr_status: pending` vs `meta done/failed` case). `--fix` mode handles every detected condition or produces explicit warnings for unhandled types. Silent exception swallowing replaced with logged warnings. Dead code removed.

Requirements: REPAIR-01 through REPAIR-04.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — infrastructure/hardening phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Known code context:
- `repair.py:252,258` — condition 4: `note_ocr_status == "pending"` vs `meta done/failed` divergence detection
- `repair.py:278-363` — `--fix` mode: currently handles 2/6 types
- `repair.py:226,306-307,347-348,355-356` — bare `except Exception: pass` blocks
- `repair.py:196` — dead `load_domain_config` call and unused dict comprehension

</decisions>

<code_context>
## Existing Code Insights

### Key File
- `paperforge/worker/repair.py` — all changes in one file

### Established Patterns
- `logger.warning()` for error logging (established in Phase 49)
- Three-way divergence: formal note frontmatter, canonical index, and paper-meta.json

</code_context>

<specifics>
No specific requirements — infrastructure phase.

</specifics>

<deferred>
None

</deferred>
