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

### Known limits

- Running heads and folios are placed last; a paper whose body starts in the top 8% keeps those blocks in the body flow (they are not margin unless their role is furniture).
- Column detection needs at least two blocks per side and a 3% gutter; weak splits are assumed column-major at confidence 0.5.
- Staggered columns (one column starts above the other) produce HOLD instead of an order.
- Figure/caption proximity is reported, not used to re-decide ownership. Phase C is where the inventory starts feeding structure decisions.
- The evaluation input is rebuilt from `canonical/blocks.raw.jsonl` (seed roles + pre-match), not the production `structure/blocks.structured.jsonl`; the report says so and must not be read as a render-parity measurement.
