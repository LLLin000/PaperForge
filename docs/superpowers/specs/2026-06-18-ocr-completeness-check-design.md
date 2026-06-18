# OCR Completeness Check Design

> Date: 2026-06-18
> Status: approved design, pending user review
> Scope: add a fuzzy completeness-check layer to detect early OCR text loss without relying on exact full-text matching.

## Goal

Add an OCR completeness-check layer so the pipeline can detect likely missing content immediately after raw-role assignment, before document normalization and zone inference depend on incomplete text.

The goal is not exact text reconstruction. The goal is to catch likely dropped content early enough that later structure logic does not reason over a mutilated block set.

## Current Baseline

The immediate P0-P2 layout close-out is already complete and recorded in `PROJECT-MANAGEMENT.md` as `9.7`.

That work fixed:

- first-surviving-page frontmatter recovery,
- margin-band watermark detection,
- compact mixed-alnum figure inner labels,
- structural-gate fallback for `paper_title` and `authors` in `frontmatter_main_zone`.

The next addition should build on that stable baseline rather than reopen the just-finished layout close-out.

## Chosen Approach

Chosen approach: Approach A, a three-layer fuzzy coverage audit.

Execution shape:

```text
raw blocks
-> raw role assignment
-> completeness check (page coverage + region coverage)
-> normalize_document_structure
-> zone inference / structural gate / render
-> fulltext coverage check
```

Why this approach won:

- It catches missing text before anchor and zone logic consume the blocks.
- It does not require brittle exact matching against the PDF native text layer.
- It separates early extraction loss from late rendering loss.
- It is safe to land as a signal-first layer before any aggressive auto-recovery.

Rejected alternatives:

- Raw-block-only correction before role assignment: too little structure, too easy to over-merge text.
- Render-only audit: too late to protect normalization and zone inference.

## Design Constraints

1. No exact full-document text matching.
2. Use fuzzy coverage and local region evidence, not whole-page string equality.
3. The first version is signal-first: detect and label likely gaps before trying to auto-patch many of them.
4. The check should focus on high-retention blocks and may expand a bit beyond them, but it must not try to repair obvious noise, watermark strips, or generic reference pages.
5. The feature must preserve the existing OCR-v2 architecture and stay local to the build path.

## Target Coverage Layers

## 1. Page Text Coverage

Purpose:

- detect pages where OCR text volume is materially lower than the PDF native text volume,
- provide a page-level risk signal rather than a repair decision.

Proposed signal:

- `ocr_token_count / pdf_token_count`
- `ocr_char_count / pdf_char_count`

Output example:

- `page_text_coverage_status = ok | low | missing_pdf_text`
- `page_text_coverage_ratio_tokens`
- `page_text_coverage_ratio_chars`

This layer must not directly rewrite block text. It is a page-level alert channel only.

## 2. Region Coverage

Purpose:

- detect block-local extraction loss at the point where raw roles are already known,
- give the strongest early signal for whether a high-value block is truncated, empty, or split.

Proposed workflow:

1. For each eligible OCR text block, clip the PDF native text layer to the same page and approximately the same bbox.
2. Compare OCR block text and PDF-region text with fuzzy rather than exact checks.
3. Label likely gaps conservatively.

Eligible block families for the first pass:

- `paper_title`
- `authors`
- `affiliation`
- `frontmatter_support`
- `abstract*`
- `section_heading`
- `subsection_heading`
- `body_paragraph`
- `structured_insert`
- optionally `figure_caption_candidate`, `table_caption_candidate`, `backmatter_body`

Explicit non-targets for the first pass:

- obvious noise and watermark strips,
- generic reference-item repair,
- page headers/footers,
- non-text visual assets.

Output labels:

- `complete`
- `likely_truncated`
- `likely_missing_tail`
- `likely_split_across_neighbor`
- `empty_vs_pdf`
- `short_vs_pdf`
- `pdf_unavailable`

This is the primary completeness layer.

## 3. Fulltext Coverage

Purpose:

- detect loss introduced after structured blocks already exist,
- distinguish raw extraction loss from rendering/path loss.

Proposed workflow:

1. After `render_fulltext_markdown`, sample major PDF native text segments from body-like pages.
2. Check whether those segments are fuzzily represented in rendered fulltext.
3. Emit a `rendered_text_gap` signal when long native-text spans are absent.

This layer is a downstream audit, not an early repair step.

## Fuzzy Completeness Logic

The system should not attempt exact matching. It should instead look for strong local signs of incompleteness.

## Region Gap Indicators

High-confidence suspicious cases include:

- PDF region has substantial text but OCR block text is empty,
- OCR block text is much shorter than PDF region text,
- OCR block text is a prefix-like fragment of the PDF region text,
- OCR text and neighboring OCR block geometry suggest that one logical sentence/title/byline was split incorrectly,
- high-value blocks such as title, byline, heading, abstract lead, or early body paragraph are abnormally short compared with the PDF region.

## Matching Rules

The fuzzy comparison should prefer:

- token overlap,
- normalized prefix containment,
- character-length ratio,
- local punctuation loss patterns,
- same-page and same-column consistency.

The check should avoid:

- cross-page reconstruction,
- broad cross-column harvesting,
- whole-page concatenation,
- exact paragraph reconstruction from the entire PDF text layer.

## Safety Boundaries

1. Never cross pages.
2. Do not cross the dominant column boundary unless the PDF-region overlap is overwhelmingly local and the block is already wide enough to span the column.
3. Prefer tagging over rewriting when confidence is not very high.
4. Do not treat reference pages as the main target in the first version.
5. Do not auto-recover watermark or publisher-strip text.

## Output Contract

The first version should attach evidence to blocks and pages even if it does not patch many texts.

Suggested block-level fields:

- `text_completeness_status`
- `text_completeness_confidence`
- `text_completeness_evidence`
- `pdf_region_text_len`
- `ocr_text_len`

Suggested page-level fields:

- `page_text_coverage_status`
- `page_text_coverage_ratio_tokens`
- `page_text_coverage_ratio_chars`

Suggested document/render-level fields:

- `rendered_text_gap_count`
- `rendered_text_gap_examples`

If a future high-confidence recovery path is added, it should also mark:

- `_text_source = "ocr+pdf_completeness_recovery"`
- `text_recovery_confidence`
- `text_recovery_evidence`

## Placement In Existing Code

Best insertion point for early completeness checks:

- `paperforge/worker/ocr_blocks.py`, inside `build_structured_blocks()`
- after the initial `seed_role` rows are created,
- before `_has_preproof_cover_page_one()` and before `normalize_document_structure()`.

Reason:

- the blocks already have `seed_role`, signatures, bbox, and page context,
- the normalization and zone logic have not yet consumed the text,
- this is the narrowest place to insert the feature without redesigning the whole runtime.

Best insertion point for downstream rendered coverage:

- after `render_fulltext_markdown` in the replay/runtime path,
- likely as a health/audit artifact rather than inline mutation.

## Relationship To Existing PDF Backfill

The repository already has `backfill_missing_text_from_pdf()` in `paperforge/worker/ocr_pdf_spans.py`.

That existing step solves one narrow case:

- OCR block text is empty and the same bbox can recover text from the PDF text layer.

The new completeness layer is broader and fuzzier:

- detect likely truncation, short extraction, split-neighbor loss, and downstream render gaps,
- without requiring the block to be empty,
- without exact full-text alignment.

This means the new layer should complement, not replace, the existing PDF text fallback.

## Verification Plan

The implementation must verify three questions separately.

### 1. Page-level coverage signal works

- a synthetic page with large PDF-native text but intentionally reduced OCR text should be flagged low-coverage,
- a normal matched page should not be flagged.

### 2. Region-level gap signal works

- a block with empty or obviously short OCR text against a richer PDF region should produce `raw_text_gap`,
- a block with normal OCR text should remain `complete`.

### 3. Fulltext-level coverage signal works

- a rendered output missing a known long PDF-native segment should produce `rendered_text_gap`,
- a normal render should not.

## Non-Goals

- Exact page-text equality.
- Aggressive auto-repair of all mismatches.
- Reference-section reconstruction.
- New journal-specific rules.
- Reopening the completed P0-P2 layout close-out work.

## Expected Effect On Current Residual Problems

This feature is expected to help most with:

- frontmatter/body blocks whose text is partially lost before zone inference,
- accepted-but-unfixed body fragmentation,
- lingering frontmatter footnote/body leakage caused by incomplete local text evidence,
- future audits that currently cannot easily distinguish extraction gaps from later structural mistakes.

It is not expected to directly solve:

- figure ownership architecture,
- backmatter heading taxonomy,
- CLI rebuild wiring,
- cosmetic `media_asset` vs `figure_asset` naming differences.

## Decision

Proceed with a three-layer fuzzy completeness check:

- page coverage for coarse page-level signal,
- region coverage for early block-level gap detection,
- fulltext coverage for downstream render-gap detection,
- with signal-first behavior and conservative metadata before broad auto-recovery.
