# Layout plan

The Phase B layout plan is a read-only explanation of page space, built from OCR blocks without changing production OCR output. It describes four concerns:

1. **Region tree** (`regions.py`): vertical bands cut by full-width areas and containers, local columns inside each band, containers with their members, and margin bands for running heads and folios.
2. **Reading graph** (`reading.py`): the proposed order, one decision per adjacent pair (or a HOLD when geometry cannot decide), and the list of held blocks.
3. **Conflict detection** (`conflicts.py`): cross-column jumps in the OCR order, plan/OCR inversions, overlapping membership, container leaks, missing geometry, and blocks sitting on the gutter.
4. **Evaluation** (`evaluate.py`): coverage, inversions, holds, conflict counts, and figure/caption proximity when an inventory is supplied.

Run the read-only vault report from the repository root:

```sh
python scripts/dev/layout_plan_report.py --vault /path/to/PaperForge/ocr --keys PAPER_KEY --out layout-plan.json
```

Omit `--keys` to process vault subdirectories; `--limit N` restricts the number processed. The command reads each paper's `canonical/blocks.raw.jsonl` and optional `raw/source_metadata.json`, then prints a Markdown summary table and writes JSON to `--out` when supplied.

**Phase B is read-only and is not wired into production.** It does not mutate the vault, input blocks, or production OCR output; the report writes only the explicitly requested output file.

## Rules the plan follows

- **Identity is geometric.** `collect_block_refs` sorts each page by bbox and assigns `p{page}:{n}`. `(page, block_id)` repeats in real OCR output, so it cannot be a key. The OCR list order survives only as `raw_index` evidence.
- **Hold instead of guessing.** A pair the geometry cannot order becomes `RELATION_HOLD`; held blocks keep their OCR relative position. Blocks within 2% of the page width from the gutter are reported as `ambiguous_column` (severity `hold`) instead of being assigned a column.
- **Containers own their blocks.** A table or box claims every non-full-width block inside its bbox (2% tolerance); the surrounding column regions drop those members, so ownership is exclusive even when a table spans the gutter.
- **Containers cut bands.** A table between two paragraphs gets its own vertical piece, so the reading path interleaves it instead of emitting it after the whole column.
- **Margins are page furniture.** Blocks whose centre falls outside the middle 8%–92% of the page go to a margin region and are emitted after the body. They are counted in coverage and reported as `coverage.margin`, never as body content or body inversions.
- **No production coupling.** Nothing in `paperforge/worker/layout/` imports the OCR pipeline's writers; the package reads blocks and returns dataclasses.

## Acceptance snapshot (40 complex-layout papers, 587 pages)

Selection used pages with mixed full-width/column content or three or more OCR column jumps, not "any two-column paper".

| Measure | Result |
|---|---|
| Blocks described | 10,430 / 10,430 (0 duplicated, 0 missing) |
| Margin blocks (furniture roles only) | 1,767 (16.9%) |
| Right-to-left column jumps, OCR order | 287 |
| Right-to-left column jumps, plan order | 0 |
| Adjacent pairs agreeing with OCR order | 9,238 / 9,843 (93.9%) |
| Plan/OCR inversions | 605 |
| `ambiguous_column` (severity hold) | 114 blocks (keep their OCR position) |
| `container_leak` | 3 |
| Figure/caption pairs judged by the inventory | 606 matched, 195 flagged (64 at 5–15% of page height, 131 >15%) |

Interpretation: the plan removes every order violation its own regions define, keeps every block, and disagrees with the OCR order on about 5.9% of adjacent pairs. Agreement is not accuracy — the plan can be right where OCR is wrong — so the quality gate audits disagreements on real pages instead of optimising this number.

## Quality gate (2026-11)

| Gate | Result |
|---|---|
| Reading confidence inherits region evidence | yes: every `before` decision is capped by the confidence of the regions it touches (2,267 of 9,843 decisions now sit below 0.70) |
| Margin only holds furniture | margin requires roles `noise` / `footnote` / `frontmatter_noise`; before this gate 2 body paragraphs and 2 section headings ("2. Methods", a 3.2 subsection) were moved to the page end |
| Row-quantised ordering | labels on one visual row are ordered left-to-right (1% of page height tolerance); 621 → 571 inversions, and it fixed a β-TCP / β-TCP+PEMF flip seen on `28ALPCY7` p17 |
| Figure/caption triage | `scripts/dev/layout_figcaption_audit.py` buckets the flagged pairs instead of re-matching them |
| Disagreement triage | `scripts/dev/layout_regression_triage.py` lists every plan/OCR disagreement with regions, confidence and structural tags |

### Visual audit (by the main agent, on rendered PDF pages)

| Page | Verdict |
|---|---|
| `27MFWJWJ` p9 | plan worse: panel labels read (b, c, a) instead of (a, b, c), and DOI lines move after later body text |
| `28ALPCY7` p17 | plan better after the row fix: `β-TCP` before `β-TCP+PEMF`, running head deferred |
| `2E4EPHN2` p8 | tie: both orders match the visible figure/legend flow |
| `2JG7RKFN` p1 | tie for body text; sidebar boxes (citation, dates, check-for-updates) differ, all furniture |
| `38W7XV4F` p7 | tie: identical order |
| `2H8MZ27H` p6 | tie at page level: 12-panel figure and both columns match; differences are panel-label placement |

The audited sample is small (6 pages, chosen where the plan disagrees most). It is enough to reject "the plan is simply better" and to name the failure class that remains: multi-panel figures whose labels are separate blocks, and DOI/URL lines inside figure bands.

## Production acceptance (C0)

`layout/acceptance.py` is the only door between the plan and production. It
does not compute layout; it decides whether a page's plan order may replace the
current order, and says no by default.

```python
from paperforge.worker.layout import build_layout_plan, assess_plan

plan = build_layout_plan(blocks)          # final structured blocks
for result in assess_plan(plan, blocks):  # ACCEPT / HOLD / REJECT
    ...
```

| Field | Meaning |
|---|---|
| `status` | `ACCEPT` / `HOLD` / `REJECT` |
| `accepted_order` | uid sequence, only when `ACCEPT` |
| `fallback_reason` | `identity_mismatch`, `uid_set_mismatch`, `duplicate_membership`, `hold_conflict`, `hold_decision`, `low_confidence`, `undecided_blocks` |
| `source_mapping` | uid → index in the blocks list, verified against the plan fingerprint |
| `held_blocks` | blocks whose position must not be taken from the plan |
| `evidence` | counts and the threshold the decision used |

### Rules

- **REJECT** when the plan cannot describe the input at all: unknown plan
  version, uid-set mismatch, a uid claimed by two regions, a missing
  fingerprint, or a block whose fingerprint changed after planning. The
  fingerprint (`page | block_id | bbox | role | text`) is what makes positional
  uids safe to bridge back to blocks.
- **HOLD** when the page is described but not confidently: any hold-severity or
  order-blocking conflict (`ambiguous_column`, `missing_geometry`,
  `overlapping_membership`, `container_leak`), any `hold` decision, any body
  decision below `min_confidence`, or a body block no decision touches.
- **ACCEPT** otherwise. Margins are furniture: they are excluded from the
  threshold and kept at the end of `accepted_order`, so applying the order
  loses nothing.

`min_confidence` defaults to 0.80: same-region (0.85) and band-boundary (0.80)
evidence pass, a 0.70 column hand-off does not. That is deliberate — the
hand-off is exactly the part Phase B cannot prove yet.

### Measured on the 40-paper corpus (587 pages)

| Threshold | ACCEPT | HOLD | accepted blocks | dominant hold reasons |
|---|---:|---:|---:|---|
| 0.80 (default) | 56 pages (9.5%) | 531 | 914 / 10,430 (8.8%) | `low_confidence` 369, `hold_conflict` 114, `hold_decision` 48 |
| 0.85 | 17 pages | 570 | 149 / 10,430 | `low_confidence` 408 |

No page was REJECTed on real data: the plan and the blocks it is asked about
always came from the same run.

This is the C0 answer to "how much could take over today": about 9% of pages,
and only where every ordering claim on the page is geometry-confident. C1 must
shadow-render those pages on final structured blocks and diff them; C2 gates
the switch behind `OCR_LAYOUT_ORDER_MODE`.

### Figure/caption identity

`evaluate.py` no longer keys figure/caption lookups by `(page, block_id)` alone:
duplicate ids make `(page, block_id) → uid` ambiguous, so those keys are
dropped and counted as `figure_caption.undetermined` instead of being
attributed to the wrong block. The 195 suspicious pairs remain distance
observations, not ownership decisions.

## Shadow render (C1)

`scripts/dev/layout_shadow_render.py` builds the **final** structured blocks
(post-match + object writebacks), asks the acceptance gate, and renders the
same document twice with the existing renderer:

- baseline: `layout_order=None`, the renderer's own order;
- shadow: accepted, in-scope pages follow the plan's order;
- the same run also renders with `layout_order={}` and asserts it is a no-op.

Nothing is written to the OCR vault; the report is the only output.

### Renderer seam

`render_fulltext_markdown(..., layout_order=...)` is the only production
change. It is off by default. Blocks are stamped with `_layout_source_index`
*before* `_convert_footnotes_to_callouts`, because that function replaces block
dicts and `id(block)` cannot be used for mapping. The override is applied
after the renderer's own tail ordering and before the body traversal, and only
for pages listed in the map.

Scope for now: pages with a container region, a reference/backmatter role, or
an object-owning block stay on the baseline path.

### Measured (40 papers, 587 pages, final blocks)

| Threshold | ACCEPT | in scope | changed pages | markdown | block multiset | headings | empty override |
|---|---:|---:|---:|---|---|---|---|
| 0.80 (default) | 48 | 9 | **0** | equal | equal | equal | no-op |
| 0.70 (diagnostic, not adopted) | 224 | 76 | **0** | equal | equal | equal | n/a |

C1 result: with the gate as designed, no accepted page changes what the
renderer emits — the plan order coincides with the renderer's own order on
those pages. Complex two-column pages are HOLD, so the reading-order benefit is
not yet observable.

### What C1 found in the region builder

The first shadow run at 0.70 showed 16 changed pages and one heading-order
regression (`38W7XV4F` p15: a level-4 heading before its level-3 parent). The
cause was a single-column page split into two "columns" — headings in one,
paragraphs in the other — because column detection compared **centres** and a
wide heading's centre differs from a narrow paragraph's. Splitting now also
requires the two clusters' horizontal ranges to be (almost) disjoint; the
single-column pages stay one region, and the regression disappears.

Cost: adjacent-pair agreement moved 94.1% → 93.9% (582 → 605 inversions across
the corpus) because a few pages that were split before are now correctly
merged. C1 also confirmed `accepted_order` is a strict permutation (rejected
otherwise) and that the fingerprint covers `render_default`, `index_default`
and `_object_owner_id`.

## Evidence baseline (R0)

`scripts/dev/layout_evidence.py::build_final_view` is the single read-only
replay of the derived rebuild's phases 2–3: structured(seed) → pre-match →
figure matching + role writeback → residual author-bio cleanup → post-reference
cleanup/prune → reader synthesis → table inventory → media/ownership conflict
resolution → post-match → object writebacks → table role writeback. Every audit
in this round consumes it.

`scripts/dev/layout_evidence_parity.py` compares it against the disk artifacts
(`structure/blocks.structured.jsonl`, both inventories).

### What the comparison shows (5 papers)

| Key | rows mem/disk | role | owner | fig/table claims |
|---|---|---|---|---|
| `2332GHPT` | 193/193 | 0 | 0 | 0/0 |
| `2AGGSMVQ` | 122/122 | 4 | 4 | 0/0 |
| `24A2QUAH` | 222/222 | 0 | 0 | 0/0 |
| `2HEUD5P9` | 670/670 | 4 | 0 | 0/0 |
| `27MFWJWJ` | 255/255 | 0 | 0 | 0/0 |

Row identity is exact everywhere. Field-level drift has two causes, and they
must not be conflated:

1. **Version drift.** `role_candidate` and `zone` are absent from artifacts
   written by older code (papers OCR'd in June/July). This is not a stage gap:
   production writes `blocks.structured.jsonl` twice — once after pre-match and
   again after object writebacks — so the final rows are on disk whenever the
   same code wrote them.
2. **Value gaps that need review.** `2AGGSMVQ` p3/p4: the disk run classified
   four body paragraphs as `figure_inner_text` owned by `figure_003`/`figure_006`
   (the Phase A swallowing defect); the current chain leaves them as body text.
   `2HEUD5P9` p26–27: current chain says `reference_item` where the disk run
   says `backmatter_body` for author-bio paragraphs.

The builder was validated against a real serial `_rebuild_one_paper` run on
`2HEUD5P9` in a throwaway vault: 670/670 rows and 0 role differences. It is
what audits consume; disk artifacts are a versioned snapshot and are only used
for this parity check.

Across the 40-paper corpus: row identity matches on every paper, figure claims
match on every paper, and only 19 rows differ in value (8 role, 11 owner).
Three patterns:

| pattern | rows | reading |
|---|---:|---|
| `body_paragraph → figure_inner_text` (owned by a figure) | 4 | older disk output swallowed body text into figures; current chain does not |
| `reference_item → backmatter_body` on author-bio paragraphs | 4 | current chain labels bios as references; the older output's `backmatter_body` looks more correct — flagged as a possible current-code regression |
| `None → ""` / `None → figure_00X` on object owners | 11 | same swallowing pattern plus an empty-string owner normalisation |

## Figure/table error audit (F0)

`scripts/dev/figure_table_error_audit.py` builds a bounded, deterministic
review set. It never decides that a pair is wrong: every case is
`UNREVIEWED`, with the caption, candidate assets, current inventory state,
distance and edge-gap evidence, layout region kind, and any pass provenance the
inventory carries.

Strata: suspicious pairs by centre-distance bucket, matched-pair negative
controls, the five known ghost cases, and table caption/asset cases. The quota
is global per stratum, so the review set stays bounded regardless of corpus
size; ghost cases are spread one per paper.

### Result (40-paper corpus + all five ghost keys)

| Stratum | Cases |
|---|---:|
| 2–5% | 0 |
| 5–15% | 10 |
| >15% | 10 |
| normal control | 10 |
| ghost | 10 |
| table | 10 |

Two observations from building it:

1. **The 2–5% band is empty.** `evaluate_plan` flags pairs beyond 2% of page
   height; matched captions under a figure routinely exceed that because the
   metric measures centre-to-centre distance, which grows with figure height.
   The audit therefore records an `edge_gap_ratio` (nearest caption/object edges)
   next to the centre distance; adjacency, not centre distance, is what tells
   "caption under a tall figure" from "caption associated with the wrong
   object".
2. **Ghost coverage needs the ghost papers explicitly.** Three of the five ghost
   keys are outside the 40-paper sample, so the audit always unions them in.

The 195 suspicious pairs were never treated as 195 errors; this script exists to
turn them into a 50-case set a human can review.
## Reading-order diagnosis (R1)

`scripts/dev/layout_reading_diagnosis.py` compares three sequences per page —
the renderer's input order, the plan's proposed order, and the order the
renderer actually emits — and attributes every page to one of five categories.

| Category | Meaning |
|---|---|
| `already_correct` | plan order equals the renderer's input order (nothing to change) |
| `gate_blocked` | plan order differs, page not accepted (reason recorded) |
| `scope_blocked` | plan order differs, accepted, page excluded by the shadow scope |
| `non_emitting_only` | differences exist only among blocks the renderer suppresses |
| `real_change_candidate` | the emitted event order differs |

### Result (40 papers, 587 pages, final blocks)

| Gate | already_correct | gate_blocked | scope_blocked | non_emitting_only | real_change |
|---|---:|---:|---:|---:|---:|
| 0.80 (production candidate) | 5 | 535 | 38 | 9 | **0** |
| 0.70 (diagnostic) | 5 | 363 | 144 | 75 | **0** |

**Zero pages change the emitted reading order at either threshold.** Lowering
the gate moves pages from `gate_blocked` into `scope_blocked` /
`non_emitting_only`; it does not create a single visible change. The plan's
column-major order already coincides with what the renderer produces, so the
plan's 605 disagreements with the raw OCR order are gains the renderer had
already made independently.

The only untested pockets are the 144 scope-blocked pages at 0.70 — figure/
table/backmatter-heavy pages the shadow deliberately leaves on the baseline
path — and the 75 pages whose differences are only in suppressed blocks.

### Decision

C2 (production reading-order takeover) is **NO-GO on this corpus**: there is no
page where the plan would change what a reader sees, so a switch would add risk
without benefit. The evidence does not support lowering the gate; it supports
stopping at C1. Re-opening C2 requires either (a) a page class where the plan
proposes an order the renderer does not already produce, or (b) accepting the
scope-blocked pages, which is a different, higher-risk change.

## Figure/table candidate evidence graph (F1)

`scripts/dev/figure_evidence_graph.py` builds a read-only graph that explains
association decisions without changing inventory:

- nodes: `caption`, `asset`, `group` (one per inventory figure/table);
- edges: `caption_group` (MATCHED/HOLD from inventory state), `group_asset`
  (MATCHED), `caption_asset` candidates (CANDIDATE within an 18%-of-page
  diagonal window, UNRESOLVED when block identity is duplicated);
- evidence per edge: `same_region` (region id/kind), `same_column`, centre
  distance, edge gap, page;
- conflicts: `caption_multiple_groups`, `asset_multiple_groups`,
  `group_without_caption`, `caption_without_candidate_asset`,
  `duplicate_identity` (UNDETERMINED).

Pass provenance is copied only when the inventory carries it (`proposed_by`,
`score`); nothing is invented and no pass is re-run. Scores from different
passes are kept side by side, never summed.

### Result (40 papers)

| Status | Edges | Origin |
|---|---:|---|
| MATCHED | 967 | inventory |
| HOLD | 30 | inventory (`no_asset`) |
| CANDIDATE | 331 | `spatial_proximity` |
| UNRESOLVED / UNDETERMINED | 0 | — |

| Conflict | Count |
|---|---:|
| `caption_without_candidate_asset` | 14 |
| `asset_multiple_groups` | 1 |

The single cross-group claim is a figure group and a table group both claiming
`asset:4:8` on `2BYRLKQS` — exactly the kind of cross-type competition F2 would
need to arbitrate. The 14 captions without a candidate asset are the first
concrete candidates for a missing-figure review, not proof of a miss.

The graph is a review surface: it can say the current match is questionable, it
cannot change it.

### Visual review of the conflicts (main agent)

Fifteen conflict cases were rendered from the PDFs and judged:

| Case | Verdict |
|---|---|
| 11 of the original 14 `caption_without_candidate_asset` | **not missing figures**: the asset exists and is adjacent, but centre distance exceeded the window. Fixed by the edge-gap criterion; those cases no longer conflict. |
| `28ALPCY7` p20 (Figure 6) | genuine missing asset: the caption block spans the figure area and no asset role exists on the page (`figure_reserved_009`). |
| `388XI46Q` p9 (Fig. 2) | genuine missing asset: caption present, matched figure has no asset (`figure_reserved_005`). |
| `2P6JR629` p1 | caption-role misclassification: the block is an author biography (`figure_caption_candidate`), not a caption. |
| `2BYRLKQS` p4 | **real cross-type error**: table 1 (caption y176) claims the figure image (y1007) whose true caption is Figure 1 at y1377 (edge gap ≈ 0.004 vs ≈ 0.50 for the table). The table should lose the asset. |

### Evidence-contract corrections (before F2)

Three measurement defects were fixed so F2 does not inherit them:

1. **Table claim parity** counted `table.members`, a field the inventory does
   not use; it reported zero differences for every paper. Claims now come from
   `asset_block_id` plus per-page `segments`. With that, 5 of 40 papers show
   real claim drift (e.g. `3EFCZ7BB` 2 vs 6), which is version drift between the
   in-memory replay and the disk snapshot, now visible instead of masked.
2. **Figure/caption edge gap** measured the nearest asset on the page, not the
   matched one. Cases now record `matched_edge_gap_ratio` (target asset) and
   `nearest_edge_gap_ratio` separately; 30 of the 50 audit cases have a matched
   target to measure.
3. **Graph status** marked every inventory table `MATCHED`, including tables
   with no asset. `MATCHED` now requires a resolved asset; assetless entries are
   `HOLD` with `status_reason: no_asset` (30 edges). Spatial candidates carry
   `origin: spatial` and `proposed_by: spatial_proximity`, so they are never
   mistaken for proposals from a pairing pass.
4. **Candidate window** used centre distance only, so a large figure directly
   above its caption never qualified. Adjacency now also qualifies
   (`edge_gap_ratio <= 0.05`), and each edge records `candidate_basis`
   (`centre` / `edge_gap`). Candidates 331 → 359; `caption_without_candidate_asset`
   14 → 3.

## Author-bio role divergence (review)

The R0 parity run flagged four rows in `2HEUD5P9` where the replay said
`reference_item` and the (older) disk output said `backmatter_body`. The
investigation found a real classification defect, not version drift:

- The five tail blocks are author biographies ("… is now a postdoctoral fellow
  in Professor …", "… is a professor at …").
- `post_ref_bio_cleanup` only inspected `reference_item` / `reference_heading` /
  `figure_caption` / `structured_insert_candidate` and required text score ≥ 4
  with ≥ 2 categories. At that stage the bios were `footnote` / `body_paragraph`,
  so they were never candidates.
- `post_match_normalize` then rewrote them through the reference-zone fallback
  to `reference_item`, which is a zone default, not a semantic decision. The
  same paper's first bio (outside the zone) stayed `body_paragraph` — the same
  content type received two different roles.

Fix (production, narrow):

1. `post_ref_bio_cleanup` now also inspects tail prose (`footnote`,
   `body_paragraph`) and reference items whose `seed_role` was prose, with a
   relaxed threshold (score ≥ 3, ≥ 1 category). Real references are still
   excluded by `_looks_like_reference`, and correspondence/address blocks are
   excluded explicitly (the first attempt misclassified "Address correspondence
   to: … University of Kansas" as a bio).
2. `post_match_normalize` keeps `backmatter_body` for a block already tagged
   `author_bio`; the specific bio decision outranks the zone default.

Measured on the 40-paper corpus: 4 blocks change role (all in `2HEUD5P9`), the
rebuilt render has the same character multiset and same length as the old
output, and the shadow render still reports zero changed pages and no markdown,
multiset or heading regressions. Parity for `2HEUD5P9` now matches the disk
output; the remaining role gaps (`27MSS3VH` 2, `28JLIHLS` 1, `3FQYMMXS` 1) are
the older disk's figure-swallowing rows, already known.

The C2 freeze is unchanged: this is a classification fix, not a reading-order
takeover.

## F2A: conflict review (before any joint matching)

`scripts/dev/figure_conflict_review.py` turns conflicts and the audit sample
into review records: the current inventory decision, the concrete alternatives
(`keep`, `switch_asset`, `attach_table_asset`, `new_group`, `no_asset`) with an
ordinal confidence, and the evidence behind them (caption type signal, asset
roles, layout region/column, centre distance, matched and nearest edge gaps,
inventory `match_score` / `candidate_assets`). Every record is `UNREVIEWED`;
the tool never decides that a pairing is wrong.

Rules that keep the list reviewable:

- switch candidates must be on the caption's page;
- caption type and asset role are cross-checked: a table offering a
  `figure_asset` is a cross-type proposal, while a table offering `table_html`
  is role-consistent and rated higher;
- a table that holds a figure/media asset is included even though the inventory
  says `has_asset` (that is exactly the cross-type case);
- one alternative per (decision, target).

### Result (40 papers, 186 cases)

| Decision | Alternatives |
|---|---:|
| `switch_asset` | 359 (21 high, 339 medium, 39 low) |
| `attach_table_asset` | 40 |
| `new_group` | 80 |
| `keep` | 71 |
| `no_asset` | 186 (one per case, as the fallback) |

Visual review of the conflict set (the PDFs, not the scores):

| Finding | Count |
|---|---|
| Caption-without-candidate that were adjacency artefacts (asset present) | 11 / 14 |
| Genuine missing assets (`28ALPCY7` p20 Figure 6, `388XI46Q` p9 Fig. 2) | 2 |
| Caption-role misclassification (biography as `figure_caption_candidate`) | 1 |
| Real cross-type mismatch (`2BYRLKQS` p4 table 1 → figure image; gap 0.50 vs 0.004 for Figure 1) | 1 |

### F2B decision

A general joint-matching optimizer is **not justified** by this evidence: one
reproducible cross-type mismatch and two missing assets in 40 papers is not a
regression class, and the two missing assets cannot be fixed by re-matching —
the objects are absent from the inventory. The only defensible narrow change is
a guarded cross-type correction (a table whose asset role is a figure asset,
with a same-page table asset adjacent); corpus impact is one paper. It is
recorded here as a candidate for a separate PR, not implemented.

## One object-association sequence (P0-A)

First parse and derived rebuild ran different figure/table sequences. The
missing first-parse calls were not cosmetic: without
`resolve_media_asset_conflicts` the same page could keep a cross-type claim
depending on which path wrote it last.

`paperforge/worker/ocr_object_stage.py` now owns the order:

```
build_figure_inventory → write_back_figure_roles → residual bio cleanup
→ post-reference bio cleanup/prune → reader synthesis → build_table_inventory
→ resolve_media_asset_conflicts → attach_ownership_conflicts
```

| Call | first parse (before) | rebuild (before) | both (now) |
|---|---|---|---|
| `write_back_figure_roles` | no | yes | yes |
| bio cleanup | yes | yes | yes |
| reader synthesis | yes | yes | yes |
| `resolve_media_asset_conflicts` | **no** | yes | yes |
| `attach_ownership_conflicts` | no | yes | yes |
| table role writeback | via writeback only | explicit | `commit_object_roles` |

`commit_object_roles` applies `apply_object_writebacks` then
`write_back_table_roles`, so writeback stays the single consumer of object
claims. First parse also passes `page_pdf_lines_by_page` to figure matching,
which it used to skip.

Validation: the shared replay matches a real serial `_rebuild_one_paper` on all
40 corpus papers — 0 row differences and 0 claim differences between figure and
table inventories (PDF absent, same evidence).

### Two-entry equality with PDF evidence

The shared stage fixed the call order, but the two entries still resolved the
PDF differently, which changed *evidence*: first parse resolved the stored
`source_pdf` locator and then re-read `meta["source_pdf"]` before span backfill,
so `[[vault]]` wikilinks and `storage:` locators skipped PDF text evidence
(`span_metadata`, missing-text recovery, PDF lines). Rebuild never resolved
those locators at all. That is why 821 of 952 corpus papers report weak span
coverage (0%) while their PDFs are present.

`pdf_resolver.resolve_source_pdf()` is now the one resolution both entries use.
First parse resolves once and reuses the path for page rendering, the
fingerprint, span backfill, missing-text recovery and figure matching; rebuild
uses the same helper before its legacy fallbacks. Rebuild also falls back to the
cached page image when an OCR page exceeds the configured PDF (a supplement can
replace the main file), instead of silently emitting no asset.

`scripts/dev/ocr_two_entry_parity.py` verifies the contract end to end: it
replays `postprocess_ocr_result` from `json/result.json` and then runs
`_rebuild_one_paper` on the same input, PDF and metadata in a throwaway vault,
comparing roles, render flags, ownership, figure/table asset claims, ownership
resolutions/conflicts, rendered markdown and asset files.

Measured on the 40-paper corpus (all PDFs resolvable):

| Comparison | Result |
|---|---|
| Final rows (role, render/index flags, owner) | 40/40 identical |
| Figure/table asset claims | 40/40 identical |
| Ownership resolutions and conflicts | 40/40 identical |
| Rendered markdown | 40/40 identical |
| Asset files (names + bytes) | 40/40 identical |

The run found one real divergence (`2ZBAK9VY`: a supplement PDF with 8 pages
against 12 OCR pages) which is what the cache fallback above fixes.

## Cross-type asset claims (P0-B)

`resolve_media_asset_conflicts` used to leave every figure/table tie unresolved
unless one side was explicit and strong. `2BYRLKQS` p4: figure 1 (legend block 9)
and table 2 (caption block 2) both claimed block 8, strengths tied at (1,1), so
block 8 was reported as `asset_multiple_groups` while the table's own
`table_html` block 3 sat unclaimed.

The resolver now breaks a weak/weak tie with caption adjacency when blocks are
supplied:

- edge gap figure caption → asset `0.0025` vs table caption → asset `0.4956`;
- winner must be ≤ `0.05` (5% page height) and the loser ≥ `0.12`;
- the losing table moves only to a **unique** same-page table-kind block
  (`role`/`raw_label` table evidence, not the post-match role) within `0.05` of
  its caption and unclaimed by any figure or table; otherwise it loses the asset
  (`has_asset = False`) and the conflict remains visible;
- figure claims are never re-attached this way — a dropped figure is riskier
  than a dropped table claim.

Result on `2BYRLKQS` p4: figure 1 keeps block 8, table 2 moves to block 3,
`ownership_conflicts` empty. Corpus impact over the 40-paper set: exactly this
one resolution.

### Known limits

- Running heads and folios are placed last; a paper whose body starts in the top 8% keeps those blocks in the body flow (they are not margin unless their role is furniture).
- Column detection needs at least two blocks per side and a 3% gutter; weak splits are assumed column-major at confidence 0.5.
- Staggered columns (one column starts above the other) produce HOLD instead of an order.
- Figure/caption proximity is reported, not used to re-decide ownership. Phase C is where the inventory starts feeding structure decisions.
- The evaluation input is rebuilt from `canonical/blocks.raw.jsonl` (seed roles + pre-match), not the production `structure/blocks.structured.jsonl`; the report says so and must not be read as a render-parity measurement.
