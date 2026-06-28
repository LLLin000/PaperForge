# OCR Truth Audit Report - 28ALPCY7

- Mode: `high-risk`
- Status: `READY`
- Reviewed pages: [1, 2, 9, 12, 13, 15, 16, 17, 19, 22, 23, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36]
- Reviewed blocks: 240

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
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `major` `object_ownership_error`: ambiguous or unresolved object ownership remains in the current artifact set
- `minor` `render_mapping_error`: some render-default blocks are not easily mapped into the current fulltext output

## Disposition Guidance

- Use `repair` when the finding reflects a pipeline defect worth fixing now.
- Use `residual` when the finding is real but intentionally deferred.
- Do not rewrite expected truth to make current output look correct.
