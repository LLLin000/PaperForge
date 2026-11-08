# Table structure decision (E4)

Status: evaluation only. No change to the user-facing fulltext this round; the
PDF crop remains the source of truth.

## What exists

| Source | Corpus value |
|---|---:|
| Tables with inventory rows | 1,768 |
| Tables without an asset | 295 |
| Tables with `assistive_text` HTML | 1,432 (81%) |
| Tables with notes | 121 (6.9%) |
| Continuation tables | 146 |
| Table markdown files | 1,765 |
| Markdown with image / caption | 1,765 / 1,765 |
| Markdown/fulltext with structured content | 0 / 0 |

40-paper sample (80 tables): 70 HTML, 0 parse errors, 693 rows, max 9 columns,
29 heuristic header rows, 62 rowspan cells, 40 colspan cells, numeric ratio
0.109, 7 P-value cells, 209 unit cells, 7 notes, 0 structured emissions.

## Why the HTML is not emitted yet

1. PaddleOCR output uses `<td>` without `<th>`, so header semantics need a
   geometric/structural heuristic, not tags.
2. Row/column order and merged cells are not validated against the image; a
   plausible-looking HTML table can silently misplace values.
3. Numeric fidelity is unmeasured. Clinical tables depend on exact numbers,
   P values, confidence intervals and units; a generative fill-in would be a
   correctness hazard.
4. Footnotes and abbreviations are separate blocks; linking them to cells has
   no validated contract.

## Decision

- Keep the image crop as the truth for tables.
- Treat `assistive_text` as auxiliary evidence for a future structured table
  object, never as a replacement without validation.
- Do not inject HTML into fulltext or the index this round.

## Acceptance criteria for a future structured-table PR

- Cell precision/recall against a reviewed sample (>= 0.98 for numeric cells).
- Exact match for numbers, P values, confidence intervals and units.
- Header levels and merged cells reproduced from the image, not guessed.
- Footnote/abbreviation attachment with source provenance.
- Cross-page continuation represented as one table with page segments.
- If the PDF text layer is available, digits come from it before OCR.
