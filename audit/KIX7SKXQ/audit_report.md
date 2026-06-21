# OCR Truth Audit Report - KIX7SKXQ

- Mode: `high-risk`
- Status: `READY`
- Reviewed pages: [1, 2, 5, 9, 10, 12, 15, 16, 17, 18, 20, 21, 23, 25]
- Reviewed blocks: 256

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
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `minor` `render_mapping_error`: some render-default blocks are not easily mapped into the current fulltext output

## Disposition Guidance

- Use `repair` when the finding reflects a pipeline defect worth fixing now.
- Use `residual` when the finding is real but intentionally deferred.
- Do not rewrite expected truth to make current output look correct.
