# OCR Truth Audit Report - 4M64NZEC

- Mode: `high-risk`
- Status: `READY`
- Reviewed pages: [1, 2, 3, 4, 5]
- Reviewed blocks: 118

## Findings

- `major` `frontmatter_error`: frontmatter page retains elevated unknown_structural density
- `major` `same_page_boundary_error`: page contains mixed body/reference/tail signals
- `major` `object_ownership_error`: ambiguous or unresolved object ownership remains in the current artifact set
- `minor` `render_mapping_error`: some render-default blocks are not easily mapped into the current fulltext output

## Disposition Guidance

- Use `repair` when the finding reflects a pipeline defect worth fixing now.
- Use `residual` when the finding is real but intentionally deferred.
- Do not rewrite expected truth to make current output look correct.
