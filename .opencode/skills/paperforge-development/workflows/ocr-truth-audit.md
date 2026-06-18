# OCR Truth Audit

Inputs:

- explicit `paper_key`, or current paper from active context
- `mode: strict | high-risk`

## Pre-flight Checklist

- [ ] Confirm this is developer/internal OCR audit work.
- [ ] Resolve one target paper.
- [ ] Confirm mode: `strict` or `high-risk`.
- [ ] Do not start by writing expectations or fixtures.
- [ ] Use visual and artifact truth first.
- [ ] Know the report contract in `../atoms/ocr-audit-report-schema.md`.
- [ ] Know the page ranking contract in `../atoms/ocr-page-risk-scoring.md`.
- [ ] Know the canonical role list in `../atoms/ocr-canonical-roles.md` — `truth_role` MUST be from that list.

## Workflow

1. Resolve the paper.
   Accept an explicit `paper_key`; otherwise use the current paper in context.

   Also resolve the OCR root explicitly. The literature/OCR vault is outside the repo. Pass it with `--source-root` or set `PAPERFORGE_OCR_ROOT`.

2. Refresh or check required artifacts.
   Run `../scripts/ocr_truth_audit.py` with `--refresh-artifacts` when you need a fresh rebuild. Confirm availability of `block_trace`, `annotated_pages`, structured block artifacts, rendered `fulltext`, document-structure artifacts, and relevant figure/table artifacts.

3. Verify artifact freshness before auditing.
   Check that the paper PDF and derived artifacts belong to the same rebuild generation. At minimum compare fingerprints for `result_json`, raw/structured blocks, document structure, figure/table inventories, reader object outputs, and `fulltext`.

4. Stop on stale artifacts.
   If the required artifacts are out of sync, stop with `AUDIT_BLOCKED: stale artifacts` and record which artifacts mismatch.

5. Generate helper summaries.
   Materialize helper outputs under `audit/<paper_key>/` via `../scripts/ocr_truth_audit.py`, but treat them as accelerators only, not truth.

6. Inspect truth from evidence.
   Start with the overview pages (`annotated_pages/page_*.png`). Each page shows every block as a numbered rectangle, color-coded by the **pipeline's final rendered role** (after gate + normalize, the same role used in `fulltext.md`). Each of the 28 roles has a distinct color, grouped by semantic family:
   - dark blue family: `paper_title` `authors` `affiliation` `frontmatter_support` `frontmatter_noise`
   - purple family: `abstract_heading` `abstract_body`
   - orange/red family: `section_heading` `subsection_heading` `sub_subsection_heading`
   - green: `body_paragraph`
   - red family: `reference_heading` `reference_item`
   - purple-brown family: `backmatter_heading` `backmatter_body` `backmatter_boundary_candidate`
   - amber/gold family: `media_asset` `figure_caption` `figure_caption_candidate` `figure_inner_text` `table_caption` `table_caption_candidate`
   - teal family: `structured_insert` `structured_insert_candidate` `non_body_insert`
   - gray family: `noise` `footnote` `unknown_structural`

   The color tells you what the pipeline decided. Your job is to judge whether that decision matches visual truth.

   The companion index file (`annotated_pages/page_*_index.json`) maps each label number to its full `block_id`, `role`, `zone`, `category`, `text_preview`, and `bbox`. Use the index to look up what any numbered block currently is, then judge its truth visually from the overview page.

   Cross-reference against `block_trace`, document-structure artifacts, and rendered `fulltext` only after forming an initial visual judgment.

7. Write audit outputs.
   Produce the required reports and summaries using `../scripts/ocr_truth_audit.py` plus the schema in `../atoms/ocr-audit-report-schema.md`.

8. Perform visual block review.
   After prep outputs are written, inspect the selected pages and write `audit/<paper_key>/block_review.jsonl`. Every reviewed block must be grounded in page visuals plus bbox/artifact evidence.

   **`truth_role` MUST be one of the canonical roles in `../atoms/ocr-canonical-roles.md`.**
   Do not invent role names. The list includes `paper_title`, `authors`, `abstract_body`, `section_heading`, `body_paragraph`, `reference_item`, `backmatter_body`, `figure_caption`, `table_caption`, `noise`, and all other final pipeline roles.
   Using old names (e.g. `media_asset` for `figure_asset`, `author_list` for `authors`, `structural_noise` for `noise`) is a workflow violation — `diff_audit.py` normalizes them, but the audit should be correct from the start.

   Each line must include `block_id`, `page`, `review_status`, `truth_role`, `truth_zone`, `truth_reference_membership`, and `evidence` with `annotated_page` and `method`. Example:

   ```json
   {"block_id":"p5:9","page":5,"review_status":"reviewed","truth_role":"body_paragraph","truth_zone":"body_zone","truth_reference_membership":"outside","evidence":{"annotated_page":"annotated_pages/page_005.png","method":"visual+bbox"},"short_reason":"Conclusion body before references, not backmatter."}
   ```

   Use the page index to find a block's current role/zone before judging. Color category helps orient: red blocks are reference candidates, purple are backmatter candidates, etc.

9. Verify review coverage.
   Run `../scripts/verify_review_coverage.py` against the paper audit directory. If required blocks are missing for the chosen mode, the audit is incomplete.

## Script Entry Point

Use:

```bash
python .opencode/skills/paperforge-development/scripts/ocr_truth_audit.py CAQNW9Q2 --source-root D:/YOUR/VAULT/System/PaperForge/ocr --mode high-risk --refresh-artifacts
```

For strict mode:

```bash
python .opencode/skills/paperforge-development/scripts/ocr_truth_audit.py DWQQK2YB --source-root D:/YOUR/VAULT/System/PaperForge/ocr --mode strict --refresh-artifacts
```

Coverage verification:

```bash
python .opencode/skills/paperforge-development/scripts/verify_review_coverage.py audit/DWQQK2YB
```

10. Classify findings.
   Classify every real error into the frozen taxonomy. Use `audit_truth_gap` only when the audit layer itself misses or distorts block-level truth.

11. Recommend disposition.
   For each finding, recommend `repair` when it reflects a pipeline defect worth fixing now, or `residual` when it is real but intentionally deferred or outside the current close-out boundary.

## Strict Mode

Strict mode is full-coverage and block-oriented.

- Every block gets a review state.
- Every reviewed block records truth for role, zone, order, object membership, and reference membership.
- Check role correctness against page context.
- Check zone correctness against actual placement.
- Check reading order and fulltext insertion point.
- Check figure/table ownership where applicable.
- Check reference membership and same-page boundary behavior where applicable.
- Do not infer truth from current rendered output as the first step.

Minimum review questions per block:

- What is the true role?
- What is the true zone?
- What blocks should come before and after it?
- Does it belong to a figure or table object?
- Is it inside or outside the accepted reference span?

## High-Risk Mode

High-risk mode is rapid audit for trust-sensitive layout classes.

- Rank pages with the additive score in `../atoms/ocr-page-risk-scoring.md`.
- Prioritize frontmatter pages.
- Prioritize first-reference and mixed reference pages.
- Prioritize same-page body/reference/tail mixes.
- Prioritize post-reference backmatter pages.
- Prioritize figure-dense and table-dense pages.
- Prioritize figure/table ownership and caption-matching failures.

Recommended focus targets:

- `frontmatter`
- `reference_span`
- `same_page_boundary`
- `backmatter`
- `object_ownership`
- `reading_order`

## Truth Rules

Always follow this order:

1. Determine block-level truth from page visuals and artifacts.
2. Record the truth.
3. Compare pipeline behavior against that truth.

Never reverse the order by rewriting expected truth to fit current OCR output.
