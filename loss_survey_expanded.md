# OCR Figure N / Table N Loss Survey — Expanded Batch (20 papers)

Survey date: 2026-07-02
Method: Compare PDF text layer (PyMuPDF) vs OCR block text on pages where `role-index.json` has **both `media_asset` AND `figure_caption_candidate`** on the same page.

## Pool Statistics

| Metric | Value |
|--------|-------|
| Total `role-index.json` files scanned | 729 |
| Papers with both roles on same page | 184 |
| Papers in this batch | 20 |
| Papers with detected "loss" | **12 (60%)** |

## Individual Paper Results

### Papers WITH confirmed heading misalignment

| Paper ID | Target Page(s) | Lost Headings | Where They Landed |
|----------|---------------|---------------|-------------------|
| **24YKLTHQ** | 4 | `table 2`, `Figure 3`, `Figure 4A` | OCR p5 (body_paragraph, figure_caption) |
| **2BFG5P6B** | 4 | `Fig. 2`, `Figure 2`, `Figure 3` | OCR p5 (body_paragraph, figure_caption) |
| **2P6JR629** | 1 | `Fig. 1`, `Fig. 2`, `Table 1`, `Fig. 3A/B/C` (6 total) | OCR p2-18 (mostly body_paragraph) |
| **3CIQWBGA** | 4 | `Table S2` | OCR p5 (body_paragraph) |
| **3FDT9652** | 4 | `Table 3`, `TABLE 3`, `Fig. 6` | OCR p5 (figure_caption, table_caption) |
| **3FQYMMXS** | 3 | `Figure S2/S3`, `Figure 1a/b/c`, `Figure 2a/c/2`, `Table S1/S2`, `Table 1` (11 total) | OCR p4 (mostly body_paragraph) |
| **4DU8LEH2** | 7 | `Fig. 4` | OCR p8 (figure_caption_candidate) |
| **4VEGZ7BN** | 2 | `Fig. 6`, `Table 2`, `Fig. 3`, `Fig. 4` (4 total) | OCR p3-5 (figure_caption, table_caption) |
| **59JLHKIN** | 5 | `Figure 6`, `Table 4`, `Figure 6` (3 total) | OCR p6-7 (figure_caption, table_caption) |
| **5CK2JEIS** | 17 | `Figure 8` | OCR p12/13/15/18 (body_paragraph) |
| **5MAW65YD** | 2 | `Fig. 1`, `Fig. 2` | OCR p3 (body_paragraph) |
| **5QLLVFFG** | 10 | `Fig. 7`, `FIG. 6` | OCR p9/11-13 (body_paragraph, figure_caption) |

### Papers WITHOUT misalignment (clean)

29RE4EMX, 2UIPV93M, 3QYCST4E, 4CML4K3Y, 4FY3VQJS, 4M64NZEC, 5PQ7DI4W, 62WG35CZ — all headings present in same-page OCR blocks.

## Aggregate Statistics

| Metric | Count |
|--------|-------|
| Total headings checked (in PDF text layer) | 51 |
| Headings "lost" from same-page OCR | **40 (78.4%)** |
| Truly missing from OCR (nowhere in any page) | **0 (0%)** |
| On same page but wrong role | **1 (2.5%)** — `table 2` in 24YKLTHQ p4 |
| On different page entirely | **39 (97.5%)** |

## Page Offset Distribution

| Offset | Occurrences | % |
|--------|------------|---|
| +1 | 40 | **59.7%** |
| +2 | 7 | 10.4% |
| +0 (same page, wrong role) | 1 | 1.5% |
| -1 | 3 | 4.5% |
| Other | 16 | 23.9% |
| **Total** | **67** | |

The dominant pattern is a **+1 page offset**: headings from PDF page N appear on OCR page N+1.

## Role Distribution at Offset +1

| Role at wrong page | Count | % |
|--------------------|-------|---|
| `body_paragraph` | 33 | **71.7%** |
| `figure_caption` | 10 | 21.7% |
| `table_caption` | 2 | 4.3% |
| `figure_caption_candidate` | 1 | 2.2% |

## Patterns Identified

### 1. Not a text-extraction problem — it's a page-alignment problem

The OCR engine (PaddleOCR-VL-1.5) **does capture figure/table heading text**. In all 40 cases of "loss," the heading text exists in the OCR output — just on the wrong page. The heading-to-`figure_caption_candidate` role mapping on the correct page fails because the heading wasn't placed on its PDF-origin page.

### 2. Systematic +1 forward shift

The overwhelming pattern is +1 page offset (59.7% of all measured offsets). This suggests a systematic boundary misalignment between the PDF text layer page numbering and the OCR page segmentation:
- PDF front matter (cover, TOC, copyright page) may cause a consistent +1 offset
- OCR may be treating a section start page boundary differently

### 3. Newline-split headings

3/12 affected papers had `\n` embedded inside the heading (e.g., `Figure\n3`, `table\n2` in 24YKLTHQ). This suggests that when the heading text crosses a PDF text-layer line boundary, the OCR page-segmentation logic is more likely to misplace it.

### 4. Multi-column layout correlation

**8/12 (67%)** of the affected pages had multi-column layout (by text block x-coordinate analysis), vs. typical single-column academic papers. Multi-column layouts stress test the OCR's page segmentation logic, which may explain the misalignment.

### 5. "Lost" heading tends to degrade to `body_paragraph`

When a heading shifts to the next page, it's most commonly (72%) assigned the `body_paragraph` role instead of `figure_caption_candidate` or `figure_caption`. This means the figure/table loses its caption association entirely, even though the text is preserved.

### 6. Papers with many figures per page are hardest hit

3FQYMMXS (11 lost headings on one page) and 2P6JR629 (6 lost headings on page 1) have dense figure arrays. OCR page segmentation struggles when multiple figure references appear close together, scattering them across subsequent OCR pages.

## Conclusion

**The problem is not OCR text loss — it is OCR page-boundary alignment.** Zero headings are missing from the OCR output; 78.4% of PDF figure/table headings are not found in the same OCR page they originate from. The systematic +1 page offset (60% of cases), multi-column correlation (67%), and the degraded role assignment (`body_paragraph` 72%) all point to the page segmentation step as the root cause.

For the pipeline, this means:
- **`figure_caption_candidate` role assignment misses captions** because the heading text is on page N+1, not page N (where `media_asset` lives)
- The actual number of **true negatives** (headings genuinely lost from OCR) is zero across this sample
- Fixing the page-alignment bug (likely in how the OCR engine maps PDF page numbers to its own page segmentation) would recover essentially all currently "lost" figure/table captions
