# 7FNV9AW2 Vision Audit Report

## Summary

**Score: 10p (YELLOW)** — Two real issues found: (1) reference reading-order span overrun
(p8:33–34 leakage); (2) frontmatter OCR gap (p1:8 empty in affiliation zone).
All 18 core reference items (p8:16–32) are correctly classified. Block-level role
assignments are sound; the errors are in span/reading-order boundaries and OCR
completeness.

---

## 1. Frontmatter — Page 1

### Finding: Frontmatter OCR gap (ocr_text_missing)

| Block | Role | Conf | Vision Assessment |
|-------|------|------|-------------------|
| p1:0 | noise | 0.9 | "nature communications" header ✅ |
| p1:1 | unknown_structural | 0.2 | Empty header_image logo — should be noise ⚠️ |
| p1:2 | non_body_insert | 0.3 | "Article" badge — plausible ✅ |
| p1:4 | paper_title | 0.8 | Title text, dark blue overlay ✅ |
| p1:7 | authors | 0.8 | Contains "Published online: 17 March 2023" + author names. Published date is frontmatter_noise merged into authors block ⚠️ |
| **p1:8** | **ocr_text_missing** | **0.8** | **Empty bbox [429,454,1005,507]. Affiliation text visible on page but OCR failed to extract it. This is the primary frontmatter error.** ❌ |
| p1:9 | non_body_insert | 0.3 | "Check for updates" — journal UI element ✅ |
| p1:14 | footnote | 0.7 | Affiliation/email footnote in left column ✅ |
| p1:15–16 | noise | 0.9 | Footer + page number ✅ |

**Root cause:** p1:8 is a region where the source OCR detected text presence (raw_label=text) but extracted zero characters. This zone contains the author affiliation block ("1State Laboratory of Surface & Interface, Zhengzhou University of Light Industry...") which is present in the PDF but was lost during OCR extraction. The position aligns with the right-column affiliation area between the author names and "Check for updates."

**Impact:** The abstract (p1:10) and body (p1:11) are unaffected. The missing affiliation text means the metadata extraction (author affiliations) will be incomplete.

---

## 2. Reference Boundary — Page 8

### Finding: Reference reading-order span overrun

Page 8 is a two-column layout: Methods on the left, Data availability + References on the right.

| Block | Content | Pipeline Role | Vision Role | Verdict |
|-------|---------|---------------|-------------|---------|
| p8:13 | "Data availability" | subsection_heading | heading | ✅ |
| p8:14 | Data availability text | body_paragraph | body | ✅ |
| p8:15 | "References" | **reference_heading** | heading | ✅ |
| p8:16 | "1. Li, G. R. et al." | **reference_item** | red/reference | ✅ |
| p8:17 | "2. Rothemund, P. et al." | **reference_item** | red/reference | ✅ |
| p8:18 | "3. Acome, E. et al." | **reference_item** | red/reference | ✅ |
| p8:19 | "4. You, I. et al." | **reference_item** | red/reference | ✅ |
| p8:20 | "5. Ruth, S. R. A. et al." | **reference_item** | red/reference | ✅ |
| p8:21 | "6. Rosset, S. & Shea, H. R." | **reference_item** | red/reference | ✅ |
| p8:22 | "7. Chen, Y. F. et al." | **reference_item** | red/reference | ✅ |
| p8:23 | "8. Feng, Q. K. et al." | **reference_item** | red/reference | ✅ |
| p8:24 | "9. Cao, C. J. et al." | **reference_item** | red/reference | ✅ |
| p8:25 | "10. Kou, H. R. et al." | **reference_item** | red/reference | ✅ |
| p8:26 | "11. Liu, X. Y. et al." | **reference_item** | red/reference | ✅ |
| p8:27 | "12. Yin, L. J. et al." | **reference_item** | red/reference | ✅ |
| p8:28 | "13. Liu, L. et al." | **reference_item** | red/reference | ✅ |
| p8:29 | "14. Uddin, S. et al." | **reference_item** | red/reference | ✅ |
| p8:30 | "15. Topper, T. et al." | **reference_item** | red/reference | ✅ |
| p8:31 | "16. Huang, J. J. et al." | **reference_item** | red/reference | ✅ |
| p8:32 | "17. Chen, Z. Q. et al." | **reference_item** | red/reference | ✅ |
| **p8:33** | "Nature Communications \| (2023)14:1483" | **noise (0.9)** | gray/footer | **✅ role / ❌ span** |
| **p8:34** | "8" (page number) | **noise (0.9)** | gray/page# | **✅ role / ❌ span** |

### The Span Error

All 20 reference_span_error findings trace to a single root cause: the
reference reading-order span spans **p8:15 through p8:34**, but the actual
reference content is only **p8:16 through p8:32**.

**What leaked in:**
- **p8:33** — journal footer ("Nature Communications | (2023)14:1483")
- **p8:34** — page number ("8")

Both are individually correctly classified as `noise` (conf 0.9) in the
structured blocks. The error is at the **span assignment level**: the
reading-order algorithm does not stop the reference span after the last
reference item.

**What about p8:15 (heading)?** The "References" heading block is the natural
start of the reference section. Whether it belongs in the reference span or
in a preceding "backmatter start" span is a design choice. The span currently
includes it, which is reasonable.

### Vision Confirmation

The annotated page confirms all reference items (1-17) are overlaid in **red**
(the reference content color). The footer and page number are in **gray** (the
noise color). There is no green (body) overlay among any of the reference zone
blocks — the pipeline correctly separated body from reference at the
individual block role level.

---

## 3. Per-Finding Verdict

| Finding Category | Count | Vision Verdict |
|---|---|---|
| reference_span_error (p8:15-34) | 20 | **18 FALSE POSITIVES** (p8:16-32 are correctly reference blocks) + **2 TRUE POSITIVES** (p8:33-34 should be excluded from reference span) |
| same_page_boundary_error (p8, p9) | 2 | Confirmed — page 8 is a clear body-to-reference transition; the two-column layout creates ambiguity |
| render_mapping_error (various) | 1 | Not visually auditable; affects many block-to-text mapping |

**Adjusted finding count:** 2 real issues (span leakage of footer+page number)
+ frontmatter OCR gap (p1:8).
