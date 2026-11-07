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
| Margin blocks | 1,988 (19%) |
| Right-to-left column jumps, OCR order | 287 |
| Right-to-left column jumps, plan order | 0 |
| Adjacent pairs agreeing with OCR order | 9,197 / 9,843 (93.4%) |
| Plan/OCR inversions | 646 |
| `cross_column_jump` conflicts | 181 across 26 pages |
| `ambiguous_column` (hold severity) | 164 |
| `container_leak` | 3 |
| Figure/caption pairs judged by the inventory | 606 matched, 191 with caption and asset more than 2% of the page height apart inside the same region |

Interpretation: the plan removes every order violation that its own regions define, keeps every block, and disagrees with the OCR order on about 6.6% of adjacent pairs. Disagreement is expected where OCR jumps columns (181 cases) and where a table interrupts a column. It is not evidence of correctness by itself — the plan's value is that each disagreement carries a region, a decision and a confidence, so a reviewer can check the claim instead of re-deriving the page.

### Known limits

- Running heads and folios are treated as furniture for the whole page band; a page whose body really starts in the top 8% would lose those blocks from the body path (they stay in coverage).
- Column detection needs at least three blocks per side; sparse bands stay single-column at confidence 0.5.
- Staggered columns (one column starts above the other) produce HOLD instead of an order.
- Figure/caption proximity is reported, not used to re-decide ownership. Phase C is where the inventory starts feeding structure decisions.
