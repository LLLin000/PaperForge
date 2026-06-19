# OCR Truth Audit Report - 7C8829BD

- Mode: `high-risk`
- Status: `READY`
- Reviewed pages: [1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 18, 19, 20, 21, 22]
- Reviewed blocks: 250

## Findings

- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `critical` `reference_span_error`: block appears inside the logical reference reading-order region
- `major` `frontmatter_error`: frontmatter page retains elevated unknown_structural density
- `major` `object_ownership_error`: ambiguous or unresolved object ownership remains in the current artifact set
- `minor` `render_mapping_error`: some render-default blocks are not easily mapped into the current fulltext output

## Disposition Guidance

- Use `repair` when the finding reflects a pipeline defect worth fixing now.
- Use `residual` when the finding is real but intentionally deferred.
- Do not rewrite expected truth to make current output look correct.
