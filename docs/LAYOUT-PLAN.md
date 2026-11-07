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
| Adjacent pairs agreeing with OCR order | 9,261 / 9,843 (94.1%) |
| Plan/OCR inversions | 582 |
| `ambiguous_column` (severity hold) | 201 blocks (keep their OCR position) |
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

### Known limits

- Running heads and folios are placed last; a paper whose body starts in the top 8% keeps those blocks in the body flow (they are not margin unless their role is furniture).
- Column detection needs at least two blocks per side and a 3% gutter; weak splits are assumed column-major at confidence 0.5.
- Staggered columns (one column starts above the other) produce HOLD instead of an order.
- Figure/caption proximity is reported, not used to re-decide ownership. Phase C is where the inventory starts feeding structure decisions.
- The evaluation input is rebuilt from `canonical/blocks.raw.jsonl` (seed roles + pre-match), not the production `structure/blocks.structured.jsonl`; the report says so and must not be read as a render-parity measurement.
