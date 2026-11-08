# Figure/Table Object Lifecycle Contract

Status: E0 (frozen baseline for E1–E4). Owner: Object Stage. This contract is
normative: later stages may not re-decide what an earlier stage already decided.

## Pipeline

```
Observation → Candidate → Association → Ownership → Identity
            → Reader + Materialization → Delivery → Reconciliation
```

| Stage | Sole owner | Input | Output | Must not do |
|---|---|---|---|---|
| Observation | provider / `ocr_pdf_spans` / page render | PDF page, provider layout, text spans | raw blocks, image/drawing/text evidence | assign figure/table identity |
| Candidate | `ocr_figure_domain` / `ocr_table_domain` | raw blocks, evidence | `FigureCorpus`, `FigureCandidateIndex`, table candidates | claim ownership |
| Association | `ocr_figure_vnext_*` passes, table passes | candidates, layout | proposals (`MATCHED`, `HOLD`, `UNMATCHED`) + provenance | write files, invent ids |
| Ownership | `resolve_media_asset_conflicts`, `OwnershipLedger` | proposals, inventories | one owner per asset; resolutions/withdrawals | re-open decided claims later |
| Identity | figure/table inventory finalization | captions, numbering, group semantics | canonical UID, display label, artifact path | reuse a UID for a different object |
| Reader + Materialization | `ocr_figure_reader`, `ocr_objects` | final inventories | reader payload, crops, object markdown | read pre-arbitration inventory |
| Delivery | `ocr_render`, `write_render_outputs` | final inventories + object files | fulltext embeds | drop or duplicate an object |
| Reconciliation | `fulltext_reconciliation`, audit scripts | artifacts | consistency report | repair silently |

## Status vocabulary

- `MATCHED`: one canonical object owns the asset/caption.
- `HOLD` / `AMBIGUOUS`: evidence insufficient; asset stays unowned and visible.
- `UNMATCHED`: no acceptable association; recorded, never auto-delivered.
- `REASSIGNED`: a later ownership stage moved a claim; the move is atomic and audited.
- `WITHDRAWN`: a claim was removed; the reason and previous state stay in the inventory.

## Identity invariants (E1)

1. Within a paper, every real object has a unique, stable `figure_id` / table id.
2. Display numbering is separate from identity. `Figure 11-1` and `Figure 11-2`
   are distinct objects; `Figure 3 continued` is the same object as `Figure 3`.
3. One artifact path belongs to one object. A collision is a hard failure, never
   a silent overwrite.
4. Identity is assigned from caption syntax + page + group semantics, not by
   appending `_2` to a collision after the fact.
5. `display_label`, `figure_number` (semantic number when known) and
   `figure_namespace` are recorded alongside the UID.
6. Existing artifact links stay valid: changed ids require an explicit migration
   map and a dry-run preview before any batch rewrite.

## Association invariants (E2)

1. All spatial relations are first-class candidates: caption above/below,
   side-by-side (same row, horizontal gap), previous-page figure with top-of-page
   caption, and forward cross-page.
2. A cross-page candidate requires a decisive boundary: top-band caption
   (`<=20%` page height) on the legend page, exactly one unclaimed group on the
   previous page, no caption of its own on that page, and a numbered caption.
3. Duplicate `(page, block_id)` identities are never treated as one object; every
   lookup includes the page.
4. Low confidence yields `HOLD`, not a forced claim. Global score changes are not
   used to hide individual conflicts.
5. Figure/table cross-type competition is resolved before identity and delivery,
   atomically (asset id, bbox, segments, render bbox, match score, consumed and
   bridge sets).

## Delivery invariants (E3)

1. Every `MATCHED` object with assets produces exactly one crop file, one render
   markdown and exactly one fulltext embed.
2. An asset without an accepted owner is classified before any delivery:
   `true_unmatched_figure`, `panel_sub_asset`, `decoration`, `duplicate_asset`,
   `undetermined`. Only `true_unmatched_figure` may be proposed for delivery, and
   only after review.
3. Reader synthesis consumes the inventory **after** conflict arbitration; a
   figure that loses an asset must not keep it in the reader payload.
4. Object UID → asset group → crop → render markdown → fulltext embed is
   traceable; a broken link is a reconciliation failure.
5. No silent overwrite: a duplicate artifact path aborts the write and records
   the conflict.
6. Materialization is transactional: build the complete manifest, validate that
   every target path is unique, render into a staging directory, validate the
   staged files, then swap directories with a journal. Any failure (collision,
   staging error, commit error, interruption) leaves the previous artifacts
   byte-identical; recovery restores the backups before the next run.

## Table invariants (E4)

1. The PDF image crop is the source of truth until structured output is validated.
2. `assistive_text` (HTML) is auxiliary evidence: it may enter Markdown/index only
   after row/column, merged-cell, numeric, unit and footnote fidelity is evaluated.
3. Tables without an asset remain explicit `UNMATCHED`, never fabricated.

## Verification

- `scripts/dev/object_lifecycle_audit.py` reports the frozen metrics.
- Goldens: `tests/fixtures/object_lifecycle_goldens.json` (keys + reviewed facts).
- Known cases: `SRNJDAA2` (composite numbering), `DJLIAZT7` (identity collisions),
  `388XI46Q` p14–15 (previous-page figure), `2AZ2EGQB` p9 (side-by-side),
  `2BYRLKQS` p4 (cross-type conflict), `28ALPCY7` p20 (assetless figure),
  `2HEUD5P9` (ownership/body protection).
- Every PR reports: identity collisions, association accuracy on reviewed cases,
  orphan classes, delivery completeness, ownership conflicts, body-swallow
  regressions and first-parse/rebuild parity versus the current master.

## Change control

- Old 952-paper artifacts are a historical baseline, not a rebuild target.
- Batch vault rewrites require a dry-run migration report, unique target paths,
  valid references and rollback evidence.
- A stage with no ground truth or no demonstrable gain reports No-Go instead of
  adding production rules.
