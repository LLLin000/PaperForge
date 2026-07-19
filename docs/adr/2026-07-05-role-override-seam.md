# ADR: Block Role Override Seam

**Date:** 2026-07-05
**Status:** Draft (next version)

## Context

OCR figure/table matching is never perfect. Rather than building a GUI for manual adjustment, we can insert a **data seam** between structured block building and render: allow an agent or user to override a block's `role` via a sidecar patch file, then let the existing render pipeline consume the corrected roles.

## Decision

Introduce `override_role_patch.json` (sidecar per paper):

```json
{
  "version": 1,
  "overrides": [
    {"block_id": "p7_b3", "role": "figure_caption"},
    {"block_id": "p9_b1", "role": "section_heading"}
  ]
}
```

Rebuild Phase 3→4 reads this file and applies overrides to structured blocks in memory before render. No changes to matching logic, figure inventory, or render.

### Scope (v1)

**Figure caption matching only.** Not text flow correction (ref zone contamination, heading misplacement). Rationale:
- Agent can 100% confirm a caption mismatch from fulltext + cropped image
- User can describe "page X 'Figure Y.' text should be a figure caption"
- Text flow correction requires position understanding, not just role change

### Block Identification

`block_id` (`p{N}_{label}`) is stable across rebuild. For user→agent handoff, natural language ("page 7, the 'Figure 3.' paragraph") is resolved to `block_id` by matching `page` + block `text` prefix.

### Consumer Tools and Quality Signals

Deferred. Quality indicators (`build_quality_indicators`, `evaluate_readiness`) remain unwired until the override seam is implemented — quality signals without a remediation path cause user frustration.

## Open Questions

- Override + rebuild cycle: does a rebuild re-derive roles and then apply override on top? Yes — override patches after structured block building, not instead of it.
- Backward compat: missing `override_role_patch.json` = no-op.
- Figure inventory consistency: if a block's role changes to `figure_caption`, does the figure inventory need updating? Current render doesn't read figure inventory for captions embedded in structured blocks — it reads block role directly. But this needs verification before v1.


## Related Decisions (Architecture Review 2026-07-05)

### #2 Meta Divergence — FIXED
`_rebuild_one_paper` now writes `meta["ocr_health_overall"]` from the rebuild health report, matching `postprocess_ocr_result`. Commit in feat/rebuild-speed.

### #3 Consumer Tools and Quality Signals
Deferred to role-override v1. Quality signals without a remediation path for the user cause frustration. Once role override gives users a way to fix mismatches, quality signals can gate downstream consumers (context, embed) meaningfully.

### #4 Health Report Richness
Keep all 60+ fields — they feed quality indicators when the module is wired in. No reduction.

### #5 PDF Lines Cache — REJECTED
Rebuild will continue to extract PDF lines from the source PDF each run. The cost is acceptable (~100ms per paper) and caching adds complexity for marginal gain. Role override will work with the current extraction.

### #6 Integration Tests
Deferred to role-override v1. Wire quality module first, then add 3 integration tests for the health → indicators → readiness flow.
