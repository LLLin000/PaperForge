# OCR Truth Audit Report - 2UIPV93M

- Mode: `high-risk`
- Status: `READY`
- Reviewed pages: [1, 2, 5, 6, 10, 13, 14, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 36, 49, 58]
- Reviewed blocks: 264

## Findings

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
