# OCR Truth Audit Report - K7R8PEKW

- Mode: `high-risk`
- Status: `READY`
- Reviewed pages: [1, 2, 3, 5, 7, 11, 16, 20]
- Reviewed blocks: 189

## Findings

- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `minor` `render_mapping_error`: some render-default blocks are not easily mapped into the current fulltext output

## Disposition Guidance

- Use `repair` when the finding reflects a pipeline defect worth fixing now.
- Use `residual` when the finding is real but intentionally deferred.
- Do not rewrite expected truth to make current output look correct.
