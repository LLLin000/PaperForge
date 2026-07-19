# OCR Vision Audit Templates

> **Purpose:** Structured prompts for vision agents. Each template pairs with a `--recipe` from `audit_helpers.py`.
> The agent workflow: (1) run `audit_helpers.py --recipe figure_map` to get JSON → (2) read this template → (3) dispatch vision with data + template → (4) vision reports findings.
>
> **After running these 4 templates**, read `ocr-vision-audit-master.md` for the deep quality pass:
> per-role cross-reference pathways, typography checks, chart-type routing to `paperforge/skills/paperforge/atoms/chart-reading/*.md`, figure/table quality checks.

---

## Template 1: Figure Verification

**Data source:** `audit_helpers.py --recipe figure_map --key {KEY}`

**Vision agent prompt (replace {KEY}, {DATA_JSON}, {PAGE_LIST}):**

```
You are auditing figure matching for paper {KEY}. Below is a structured summary
of every figure the pipeline detected — matched, ambiguous, and unresolved.

FIGURE DATA:
{DATA_JSON}

Annotated pages are at:
  audit/{KEY}/annotated_pages/page_NNN.png  (color-coded block rectangles)
  audit/{KEY}/annotated_pages/page_NNN_index.json  (maps label numbers to block IDs)

For EACH figure in the data, look at the corresponding annotated page(s) and answer:

### For every figure:

1. VISUAL CONFIRMATION: Find the colored rectangle(s) for this figure on the annotated page.
   - The label numbers on the PNG correspond to `block_id` in the data.
   - The index JSON maps label_number → block_id, role, bbox.
   - TRACE: Find the caption block first (its label number), then find each asset block.

2. ASSET COVERAGE: Does the set of colored boxes cover ALL visible sub-panels of this figure?
   - Count how many sub-panels the figure has (from the colored boxes on the page).
   - Compare with `assets` list in the data. Are any sub-panels MISSING? Are any EXTRA?
   - If data says N assets but visually you see M sub-panels: report the discrepancy.

3. CAPTION CORRECTNESS: Is the caption text (shown in the data) visually the correct caption for this figure?
   - Is the caption block positioned correctly relative to the figure (below, above, or side-by-side)?
   - Does the caption text match what you see on the page?
   - Is it a REAL caption (description of the figure), not a section heading or body text?

4. SUB-PANEL MERGING: Are sub-panels of the SAME figure correctly grouped?
   - If the page has a 2x2 grid of images with ONE shared caption, they should be ONE figure.
   - If the data shows them as separate figures: that's a merge failure.
   - If the data shows them as one figure with N assets: check that N matches visual sub-panels.

5. CROSS-PAGE CHECK: If a figure's caption is on a different page than its assets:
   - Is this correct (caption on page N+1, image on page N)? Or is it a mismatch?
   - Look at both pages to confirm.

6. ROLE MISLABELS:
   - Is any `figure_caption` block actually a section heading? (e.g., "Figure 3. In vitro evaluation..." at the top of a new section)
   - Is any `figure_asset` / `media_asset` block actually a table?
   - Is any `figure_caption` actually just a sub-panel label ("Fig. 6" only, no description)?

### For each figure, report:

```
Fig {N} — page {P} — status: {OK / PROBLEM}
  Issue: {specific problem description}
  Evidence: {what you see on the annotated page that supports this}
```

### After checking all figures, provide a summary:

```
Total figures: {N}
OK: {M}
Problems found: {K}

Problem details:
  Fig X: [one-line issue]
  ...
```

### Common patterns to watch for:

- **Truncated label as standalone figure:** "Fig. 6" with no description text, next to a long caption block below → these should be ONE figure with the long text as caption.
- **Multi-panel grid as separate figures:** 4 images in a 2x2 grid, each with "Fig. N" label, one shared caption below → should be ONE composite figure.
- **Caption between two figures:** "Fig. 2" caption sandwiched between Fig 2 image above and Fig 3 image below → caption belongs to the image ABOVE.
- **Empty/phantom blocks in figure area:** A colored box with no visible content inside → the block detection created a ghost.
    - **Cross-page orphan:** Caption on page N, image on page N-1 → normal for preproofs.
```

---

## Template 2: Frontmatter Verification

**Data source:** `audit_helpers.py --recipe frontmatter_map --key {KEY}`

**Vision agent prompt:**

```
You are auditing page 1 (frontmatter) for paper {KEY}.

FRONTMATTER DATA:
{DATA_JSON}

Annotated page: audit/{KEY}/annotated_pages/page_001.png

The data lists every block on page 1, top-to-bottom, with its pipeline-assigned role.
Your job: verify each block's role against what you VISUALLY see on the page.

### For each block, answer:

1. ROLE CHECK: Is the assigned role correct?
   - paper_title: should be the LARGEST text near the top, centered or left-aligned.
   - authors: multiple names, usually below the title, smaller font.
   - affiliation: institutional addresses, below authors.
   - abstract_heading / abstract_body: "Abstract" label + paragraph text.
   - frontmatter_noise: journal name, article type badge, publisher strip — small text at page edges.
   - frontmatter_support: correspondence, DOI, dates.

2. BADGE CHECK: Is there a "HIGHLIGHTED PAPER" or "RESEARCH ARTICLE" badge?
   - If the data labels it as authors → WRONG.
   - If the data labels it as noise → correct.

3. MISSING ROLES: Are any expected roles missing?
   - If data says `missing_expected: ["paper_title"]` → check if the title is absorbed into another block.
   - If data says `missing_expected: ["abstract_heading"]` → check if the abstract exists but is labeled as body_paragraph.

4. ORDERING: The blocks in the data are sorted top-to-bottom. Is this order visually correct?
   - Expected: title → authors → affiliation → (badges/noise mixed in) → abstract → keywords → body text.
   - If the order looks wrong visually, report the correct order.

### Report format:

```
Page 1 — {paper_title}
  Roles OK: {list of correct roles}
  Roles WRONG:
    p1:{block_id}: labeled as {role}, should be {correct_role}
  Missing: {list}
  Badge issue: {yes/no + detail}
```
```

---

## Template 3: Reference Verification

**Data source:** `audit_helpers.py --recipe reference_map --key {KEY}`

**Vision agent prompt:**

```
You are auditing reference completeness for paper {KEY}.

REFERENCE DATA:
{DATA_JSON}

Annotated pages are at audit/{KEY}/annotated_pages/. Focus on:
  - The first reference page (where references begin)
  - The last reference page (where references end)
  - Any "transition_pages" listed in the data

### Check these specific things:

1. REFERENCE BOUNDARY: On the first reference page, is there a clean boundary between body text and references?
   - Look for the "References" heading (colored as reference_heading).
   - Body text (green) should STOP before this heading.
   - If body paragraphs appear AFTER the "References" heading → intrusion.

2. INTRUSIONS: The data lists "real_intrusions" — body_paragraph or backmatter blocks inside the reference zone.
   - If empty: no intrusions detected.
   - If not empty: look at the specific pages listed. Are these REALLY inside the reference zone?
   - Note: noise blocks (gray) between reference items are NORMAL (page numbers, headers).

3. ZONE GAPS: The data lists references not in `reference_zone`.
   - Look at the listed pages. Are these reference items that should be in reference_zone?
   - If ALL refs on a page are in the wrong zone: the zone assignment failed for that page.

4. TRANSITION PAGES: Pages where body and references co-exist.
   - Look at the page: is the visual boundary clean?
   - Is there body text that should have ended before the references?

5. REFERENCE NUMBERING: The data lists missing or duplicate reference numbers.
   - This is a data-derived check. No visual verification needed.
   - Missing numbers may indicate references absorbed into body text → check visually if the missing references appear as body paragraphs.

### Report format:

```
References — {total_references} total
  Span: {start} → {end}
  Boundary clean: {yes/no}
  Real intrusions: {count or "none"}
  Zone issues: {count or "none"}
  Numbering gaps: {list or "none"}

  Visual findings:
    [page-specific observations]
```
```

---

## Template 4: Body Text Verification

**Data source:** `audit_helpers.py --recipe body_text_map --key {KEY}`

**Vision agent prompt:**

```
You are auditing body text cleanliness for paper {KEY}.

BODY TEXT DATA:
{DATA_JSON}

The data lists, per page, every body_paragraph, noise, unknown_structural, and
other content block with their bboxes, zones, and text previews.

Annotated pages at audit/{KEY}/annotated_pages/page_NNN.png

### For pages flagged in the data:

1. NOISE IN CONTENT AREA: Blocks with `flag: text_in_content_area` or `flag: empty_in_content_area`.
   - Look at the specific page. Is the noise block actually sitting in body text?
   - Is it page furniture (page number, header) that happens to have non-edge coordinates?
   - Is it a phantom (empty box with no visible content)?

2. BODY TEXT WITH EMPTY TEXT: Body_paragraph blocks with `flag: empty_text_*`.
   - Look at the bbox on the annotated page. Is there visible text at this position?
   - If yes: OCR missed the text → PDF backfill needed.
   - If no: the block is a phantom that should be removed.

3. LARGE GAPS between body paragraphs (gap_px > 100).
   - Look at what's in the gap (listed in `blocks_in_gap`).
   - Is there supposed to be a figure, heading, or table here?
   - Is it a two-column layout where the gap is the right-column text?

4. TWO-COLUMN SUSPICION: If a page has body paragraphs with widely different x-centers.
   - Look at the page layout. Is it genuinely two-column?
   - Do the left and right columns each have coherent reading order?

### Report format:

```
Body text — {page_count} pages checked
  Pages with noise in content: {list}
  Pages with empty body text: {list}
  Pages with large gaps: {list}

  Per-page findings:
    Page {N}: [specific observations]
```
