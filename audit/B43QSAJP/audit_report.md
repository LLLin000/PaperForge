# OCR Truth Audit Report - B43QSAJP

- Mode: `high-risk`
- Status: `READY`
- Reviewed pages: [1, 4, 5, 6, 9, 10, 13, 14, 15, 17, 19, 21, 22]
- Reviewed blocks: 230

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
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `minor` `render_mapping_error`: some render-default blocks are not easily mapped into the current fulltext output

## Disposition Guidance

- Use `repair` when the finding reflects a pipeline defect worth fixing now.
- Use `residual` when the finding is real but intentionally deferred.
- Do not rewrite expected truth to make current output look correct.
