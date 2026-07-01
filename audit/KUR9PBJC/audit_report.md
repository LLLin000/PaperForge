# OCR Truth Audit Report - KUR9PBJC

- Mode: `high-risk`
- Status: `READY`
- Reviewed pages: [1, 4, 5, 6, 7, 9, 10, 12, 13, 14, 15, 16, 19]
- Reviewed blocks: 199

## Findings

- `major` `frontmatter_error`: frontmatter page retains elevated unknown_structural density
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `minor` `render_mapping_error`: some render-default blocks are not easily mapped into the current fulltext output

## Disposition Guidance

- Use `repair` when the finding reflects a pipeline defect worth fixing now.
- Use `residual` when the finding is real but intentionally deferred.
- Do not rewrite expected truth to make current output look correct.
