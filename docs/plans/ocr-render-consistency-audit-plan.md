# OCR Render Consistency Audit — V1 Plan

**Status:** V1 read-only audit implementation. Existing render code remains unchanged.

## Boundary

Existing OCR structural parsing, figure/table matching, and render code remain untouched. V1 is an append-only post-render audit. It never synthesizes visual content or edits canonical OCR truth.

```text
existing render → audit_0 → render/render.consistency.json → probe OCR details.render_consistency
```

V1 does not reconcile or modify artifacts. Reconcile is deferred until the corpus audit validates exact repair rules.

## V1 scope

V1 covers only:

- `main.figure`
- `main.table`
- `supplement.figure`
- `supplement.table`

Formula is report-only. Scheme and appendix namespaces are future scope. Unknown namespaces are report-only.

## Canonical object identity

Each V1 visual object receives an internal identity such as `main.figure.002` or `supplement.table.S1`. When an existing `figure_inventory` or `table_inventory` provides the identity, it is the sole identity source. Audit reads that identity; it must not create a competing identity or versioned suffix.

```text
namespace
canonical_object_id
normalized label
caption block id + caption hash
caption source + confidence
caption page + bbox (or page range)
asset block ids
asset page(s) + bbox(es)
document order
```

## Render artifact identity

```text
render header label
legend label
legend source + confidence
render page / page range
image reference
image existence + digest
render file path
render order
```

`legend_source` distinguishes OCR caption text, render markdown text, image OCR, and manual text. `legend_confidence` is preserved for provenance and future repair gating.

Checks compare number, namespace, caption, page/location, asset ownership, file reference, and order. Page ranges are valid evidence; never replace `[2,6]` with an invented page `4`.

## Evidence modes

### Exact

All required facts agree directly. Exact evidence is reported in V1 and is the only evidence mode eligible for future automatic reconcile:

- canonical object is unique;
- namespace and normalized label agree;
- caption source confidence is sufficient;
- caption and asset ownership are unique;
- source page/location agrees;
- image/asset exists;
- target render is missing or has a provable naming/header mismatch;
- no duplicate or competing owner exists.

### Constrained

Some values are ranges or inferred from monotonic document order. Example: Figure 1 is on page 2 and Figure 3 on page 6; Figure 2 may carry `page_range=[2,6]`, not a fabricated exact page.

Constrained evidence creates a proposal/report only. It does not write or materialize. Record `evidence_mode=constrained`, the inference chain, and ranges.

### Ambiguous

Multiple candidates, namespace conflict, missing source asset, contradictory ownership, low/competing caption confidence, or PDF-only visual suspicion. Report only; do not mutate.

```text
exact       → report in V1; future reconcile candidate
constrained → proposal/report only
ambiguous   → report only
```

## Issue classes

Every issue carries `severity: P0|P1|P2` and evidence references.

| Issue | Evidence | V1 action |
|---|---|---|
| `render_id_mismatch` | header/filename differs from unique canonical caption + asset owner | Report exact repair candidate |
| `render_caption_mismatch` | render legend ID differs from unique canonical caption ID | Report; include source/confidence comparison |
| `missing_render_materialization` | caption + figure-map + unique asset exist, canonical render file absent | Report exact repair candidate |
| `render_order_mismatch` | emitted order differs from canonical document order | Report only in V1; presentation order is not assumed equal to document order |
| `render_dangling_asset_reference` | render markdown exists but referenced image is missing/unreadable/hash-mismatched | Report |
| `render_artifact_integrity` | empty/invalid markdown, empty image, invalid encoding, or digest mismatch | Report |
| `duplicate_render_artifact` | two artifacts claim one canonical object | Report and keep both; no deletion |
| `caption_without_asset` | legend/caption exists but no unique source asset | Report |
| `body_reference_without_caption` | body mentions Figure 7 but no caption/object exists | Suspected missing object; report |
| `pdf_visual_candidate_unmapped` | PDF image/drawing candidate has no OCR owner | Report; physical PDF objects are not semantic proof |
| `namespace_conflict` | main/supplement labels collide or namespace is unknown | Report |

`missing_render_materialization` means the render artifact itself is absent. `render_dangling_asset_reference` means the artifact exists but its referenced image is broken.

Concrete production example already observed: `388XI46Q/figure_reserved_005.md` has render header `Figure 5`, legend `Fig. 2`, and no image. This is an evidence example, not a repair rule.

## PDF candidates

PDF image/drawing objects may be recorded as `pdf_visual_candidate_unmapped`. They may participate in a future repair proposal only when all of the following agree:

```text
caption
location
namespace
order
ownership
```

A unique PDF object alone is never enough. No PDF-only automatic repair exists in V1.

## Status and probe semantics

Do not overload OCR lifecycle or capability state. OCR remains its own state (`done`, `done_degraded`, `failed`, etc.). Add an independent fact under the OCR envelope:

```json
"details": {
  "render_consistency": {
    "state": "NOT_RUN|CLEAN|REPAIRED|DEGRADED|FAILED|UNKNOWN",
    "evidence_mode": "exact|constrained|mixed",
    "issues_found": 0,
    "issues_repaired": 0,
    "issues_remaining": 0,
    "report_path": "render/render.consistency.json"
  }
}
```

Semantics:

- `NOT_RUN`: audit has not executed.
- `CLEAN`: audit ran and found no issue.
- `REPAIRED`: reserved for a future post-reconcile audit that passes; it does not mean every source field is exact.
- `DEGRADED`: unresolved or proposal-only issues remain, but render is usable.
- `FAILED`: audit execution failed because inputs were corrupt, required metadata was missing, or the audit crashed.
- `UNKNOWN`: state cannot be observed.

`render.consistency.json` is the provenance authority for this audit, not `meta.json`.
The unified `probe lineage --json` surface projects this existing report under `details.render_consistency`; it does not recompute render findings or create a second state authority.

```json
{
  "render_consistency_schema_version": 1,
  "audit_algorithm_version": 2,
  "input_snapshot": {
    "blocks_hash": "...",
    "figure_inventory_hash": "...",
    "table_inventory_hash": "...",
    "render_hash": "...",
    "asset_index_hash": "..."
  },
  "issues": [],
  "audit_0": {},
  "audit_1": null
}
```

Each issue also reports:

```json
{
  "domain": "render_layer|inventory_layer|asset_layer|ocr_layer|unknown",
  "diagnosis": "render_image_materialization_missing",
  "recommended_action": "rerender|inspect_inventory|inspect_asset_matching|inspect_render"
}
```

`type` describes what was observed; `domain` describes the likely failure layer; `diagnosis` describes the likely cause; `recommended_action` is guidance only and never executes repair. Initial corpus evidence is diagnostic, not a repair authorization.

`audit_algorithm_version` and `render_consistency_schema_version` are separate. The input snapshot records source and render changes, not only renderer version.
The existing object materializer may write `render/materialization.provenance.json` as an additive result sidecar. It records object status, stage, reason, PDF-input availability, asset/render paths, and crop attempts. The audit reads this sidecar when present and attaches the matching record to issue evidence; it never recomputes or replaces the materializer's result.
The shared `write_render_outputs` boundary invokes the existing audit after `fulltext.md` and `render-map.json` are written, so initial OCR and derived rebuild paths publish the same report. Audit failure is diagnostic-only and does not fail rendering.
## Reconciliation proposal report

`render/reconciliation.proposals.json` is an on-demand, read-only projection of existing inventory, render consistency, materialization provenance, structured caption text, and optional PDF media evidence. It has exactly three result buckets:

```json
{
  "summary": {
    "exact_repairs": 0,
    "proposals": 0,
    "blocked": 0
  },
  "exact_repairs": [],
  "proposals": [],
  "blocked": []
}
```

Rules:

- `exact_repairs` may reference only an existing `canonical_object_id` and have `repair_scope=render_only`.
- `proposals` may describe a missing canonical candidate but never create one or request `materialize_render`.
- `blocked` records reservations, ambiguity, ownership conflicts, missing source, and other review targets.
- Scores rank evidence only; hard constraints and canonical identity decide the bucket.
- The report reuses the audit input snapshot and is projected by `probe lineage` under `details.render_reconciliation`.
The consistency report also exposes position evidence from existing truth: legend page/block, object page, asset pages, page range, relation, and asset bboxes. PDF media remains optional evidence for on-demand reconciliation, not a second canonical source.
Position relations expose both booleans and ordering: `same_page`, `cross_page`, and `ordering=legend_before_asset|asset_before_legend|same_page|unknown|no_asset`. The legacy `relation` value remains as a compact compatibility label.

## Authority boundary

Future `paperforge render reconcile` may update only:

- render-layer markdown artifacts;
- render-layer image materialization through the existing renderer;
- `render/render.consistency.json`;
- `render/materialization.provenance.json`.

It must not mutate:

- OCR blocks;
- `figure_inventory` or `table_inventory`;
- asset indexes;
- canonical metadata;
- `meta.json`;
- source PDF or user-authored notes.

## Execution surface

V1 implements only:

```text
paperforge render audit
```

It is read-only for one paper or a batch. `paperforge render reconcile` is a later phase after the corpus audit.

## Implementation phases

1. Build read-only consistency audit against existing `render/figures`, `figure_inventory`, `render/fulltext.md`, and source block/asset metadata.
2. Run it over the real OCR corpus; review false positives and issue distribution.
3. Freeze exact repair rules from observed evidence; only then design explicit reconcile.
4. Integrate the audit as a post-pass after render without changing the existing render algorithm.
5. Keep V1 to main/supplement figure/table namespaces; formula remains report-only and scheme/appendix remain future scope.

## Unresolved case queue

These remain report-only until separately specified:

- caption continuation across pages;
- `Figs. 2A–2D` and mixed ranges where subfigure ownership is unclear;
- main/supplement/scheme/appendix namespace ambiguity;
- one asset claimed by multiple captions;
- one caption with multiple plausible assets;
- image-only PDF objects with no caption;
- tables or formulas that visually resemble figures;
- renderer output whose file order is correct but page/location evidence is incomplete.

The audit must emit these cases with evidence and leave existing render artifacts unchanged.
