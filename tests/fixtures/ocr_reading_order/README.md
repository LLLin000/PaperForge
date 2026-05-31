# OCR Reading Order - Test Fixtures

Fixture pages sourced from 696 real OCR-ed academic papers (10,430 pages) in the
PaperForge corpus. Each fixture key identifies a page within a paper that
exhibits a specific layout failure mode for the reading-order engine.

## Fixture Classes

| Class | Failure Mode | Description |
|---|---|---|
| `raw_interleave` | Two-column pages where left/right paragraphs alternate | Page content is physically laid out across two columns, but raw OCR extraction interleaves the columns paragraph-by-paragraph instead of reading left column then right column. |
| `mixed_body_media` | Body text, figures, and captions coexist on the same page | Pages containing a mix of running body text alongside embedded figures, tables, and their captions. The reading-order engine must separate media blocks from body flow. |
| `heading_media_mix` | Headings adjacent to or embedded in media blocks | Pages where section headings appear near figures or tables, making it ambiguous whether the heading belongs to the preceding body, the following body, or the media block. |
| `cross_column_body` | Center-spanning body content | Content (often an abstract, a wide equation, or a centered block) that spans the full page width in a multi-column layout, breaking the column-flow assumption. |
| `multi_heading_multicol` | Multiple headings in multi-column layouts | Pages with several section and subsection headings distributed across multiple columns. The encoder must maintain correct heading hierarchy through column transitions. |
| `session_regression_7C8829BD` | Regression suite for paper `7C8829BD` | Specific pages from the paper debugged during this development session. These pages produced ordering errors in the pre-refactor pipeline and serve as a canary for regressions. |

## Source

All fixture pages are drawn from real academic papers (PDFs) in the PaperForge
corpus. Each entry's `key` is the paper hash and `page` is the 1-indexed page
number within that paper.

## Expansion Policy

When adding new fixtures:
1. Classify the page into an existing class if one matches; create a new class
   only if no existing class captures the failure mode.
2. Prefer pages that are known to have caused ordering bugs in production.
3. Update this README with the new class description whenever a new class is
   added.
4. Run `test_fixture_inventory_has_required_failure_classes` after any
   structural changes to `fixture_inventory.json`.
