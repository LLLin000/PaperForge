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

   The audit is split into **five phases**. Phase 6a-6d use the 4 recipes + 4 templates.
   Phase **6e** is the deep quality pass using the master atom.
   Work through them in this order.
   Each domain has a **data map** (run the recipe) and a **vision template** (read the atom).

   **6a. Figure verification (most error-prone — do this first).**
   ```bash
   python .opencode/skills/paperforge-development/scripts/audit_helpers.py --recipe figure_map --key {KEY}
   ```
   This prints a JSON listing every figure: caption page/text, asset blocks with bboxes,
   match status, candidates, panel labels, cross-page flags.
   Then read `../atoms/ocr-vision-audit-templates.md` → "Template 1: Figure Verification".
   Dispatch a `vision` subagent with the figure_map JSON + that prompt template.
   The vision agent checks: asset coverage, caption correctness, sub-panel merging,
   cross-page pairing, role mislabels. Reports discrepancies between pipeline data and
   visual truth.

   **6b. Frontmatter verification.**
   ```bash
   python .opencode/skills/paperforge-development/scripts/audit_helpers.py --recipe frontmatter_map --key {KEY}
   ```
   Then read `../atoms/ocr-vision-audit-templates.md` → "Template 2: Frontmatter Verification".
   Dispatch `vision` subagent with the frontmatter JSON + template.
   Checks: role correctness on page 1, badge mislabel, missing roles, ordering.

   **6c. Reference verification.**
   ```bash
   python .opencode/skills/paperforge-development/scripts/audit_helpers.py --recipe reference_map --key {KEY}
   ```
   Then read `../atoms/ocr-vision-audit-templates.md` → "Template 3: Reference Verification".
   Dispatch `vision` subagent with the reference JSON + template.
   Checks: reference boundary, real intrusions, zone gaps, transition pages.

   **6d. Body text verification (only flagged pages need vision).**
   ```bash
   python .opencode/skills/paperforge-development/scripts/audit_helpers.py --recipe body_text_map --key {KEY}
   ```
   Then read `../atoms/ocr-vision-audit-templates.md` → "Template 4: Body Text Verification".
   Most pages pass on data alone. Dispatch `vision` only for pages with
   flagged gaps, noise-in-content, or empty body text blocks.

   **6e. Deep quality + typography audit (new — extends all 4 domains).**
   After the 4 recipe-driven vision passes, read `../atoms/ocr-vision-audit-master.md`.
   This atom provides per-role cross-reference pathways, typography checks,
   figure/table quality checks, chart-type routing to the chart-reading atoms,
   and full-page layout audit.
   
   For each block that passed the recipe check, dispatch an additional vision pass
   if the block is Tier A (figure/table/structured) or if the page has typography flags.
   The master atom tells you which data files to cross-reference and what to look for.
   
   **Color reference for annotated pages:** Each role has a distinct color:
   - dark blue: `paper_title` `authors` `affiliation` `frontmatter_*`
   - purple: `abstract_heading` `abstract_body`
   - orange/red: `section_heading` `subsection_heading` `sub_subsection_heading`
   - green: `body_paragraph`
   - red: `reference_heading` `reference_item`
   - purple-brown: `backmatter_*`
   - amber/gold: `figure_asset` `media_asset` `figure_caption*` `table_caption*` `figure_inner_text`
   - teal: `structured_insert*` `non_body_insert`
   - gray: `noise` `footnote` `unknown_structural`

   The annotated pages show what the pipeline decided. Your job is to judge whether
   that matches visual truth. The companion index (`page_*_index.json`) maps label
   numbers to block IDs for cross-reference.

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

   For deep quality checks, see `../atoms/ocr-vision-audit-master.md` section 3 (chart quality),
   section 4 (page typography), and section 2 (per-role analysis with quality dimensions).

8.5. Record quality findings in block_review.jsonl.
   Extend each block_review.jsonl entry with optional fields `quality_checks` and `page_typography`
   as described in `../atoms/ocr-vision-audit-master.md` section 5. Use `null` for unchecked dimensions.

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
