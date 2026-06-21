# OCR Truth Audit Report - 4AG67PBH

- Mode: `high-risk`
- Status: `READY`
- Reviewed pages: [1, 3, 4, 10, 12, 13, 14, 15, 18, 19, 21, 25]
- Reviewed blocks: 236

## Findings

- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `minor` `render_mapping_error`: some render-default blocks are not easily mapped into the current fulltext output

## Disposition Guidance

- Use `repair` when the finding reflects a pipeline defect worth fixing now.
- Use `residual` when the finding is real but intentionally deferred.
- Do not rewrite expected truth to make current output look correct.
