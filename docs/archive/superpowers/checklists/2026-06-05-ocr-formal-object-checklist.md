# OCR Formal Object Checklist

Use this checklist before calling the OCR remediation complete.

## A. Frontmatter

- [ ] `paper_title` is unique and page-1-only
- [ ] authors are either recovered or correctly isolated
- [ ] affiliations are isolated from body
- [ ] DOI is localized correctly
- [ ] abstract is rendered
- [ ] frontmatter noise does not enter body or heading buckets

## B. Headings

- [ ] no long body paragraph is rendered as a heading
- [ ] `Figure N shows ...` body references are not headings
- [ ] heading hierarchy is consistent across the paper
- [ ] references heading is recognized

## C. Figures

- [ ] formal legends are distinct from body mentions
- [ ] candidate legends are not silently promoted without evidence
- [ ] `legend_only` figures remain assetless
- [ ] orphan assets stay orphaned
- [ ] figure object titles use formal figure numbers
- [ ] figure crops match the intended asset bbox

## D. Tables

- [ ] formal table numbers are preserved
- [ ] continuation pages merge into the same formal table
- [ ] table object titles use formal table numbers
- [ ] no raw table HTML remains in `fulltext.md`
- [ ] table crops match the intended asset bbox

## E. Cropping / Assets

- [ ] OCR page-image coordinate cropping is used
- [ ] cached `pages/page_XXX` images are preferred when available
- [ ] `assets/` is structured truth
- [ ] `images/` remains compatibility only
- [ ] path mapping between `assets/` and `images/` is explicit

## F. Index / Health

- [ ] `body` index bucket is free of frontmatter furniture
- [ ] `references` bucket contains actual reference items
- [ ] `abstract_found` is correct
- [ ] `references_found` is correct

## G. Real Paper: `7C8829BD`

- [ ] Figure 3 uses the real chart, not the body mention
- [ ] Figure 4 uses the real page-14 chart
- [ ] no `Check for updates` figure object remains
- [ ] Table 6 and `Table 6 (Continued)` are one formal table
- [ ] Table 7 remains Table 7
- [ ] `fulltext.md` has no inline raw table HTML
