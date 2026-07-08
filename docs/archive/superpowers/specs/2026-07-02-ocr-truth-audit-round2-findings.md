# OCR Truth Audit — Round 2 Findings

> **Date:** 2026-07-02
> **Method:** 10 new papers batch-audited via `ocr_truth_audit.py` (high-risk mode) + 2 vision agents for RED papers
> **Verdict: 5 GREEN / 4 YELLOW / 1 RED**

## Results

| Paper | Verdict | Figures | Key Issue |
|-------|---------|---------|-----------|
| 53B47JM8 | 🟢 GREEN | 7/7 | Clean — bio artifacts only |
| 72D4YXEB | 🟢 GREEN | 5/5 | Clean |
| 82W2IJIP | 🟢 GREEN | 6/6 | Clean |
| B43QSAJP | 🟢 GREEN | 8/8 | Clean |
| 95FDVE4W | 🟢 GREEN | 10/10 | Reference span FPs — vision confirmed all real ref items |
| 24A2QUAH | 🟡 YELLOW | 1/1 | Frontmatter unknown_structural density |
| 49NUE2G7 | 🟡 YELLOW | 4/? | Fig 2 cross-page gap (caption p3, asset p4) |
| 62LTMCI8 | 🟡 YELLOW | 1/1 | Logo artifact unmatched |
| A35UYJBK | 🟡 YELLOW | 0/0 | Reference span structural issue, no figures |
| **37LK5T97** | **🔴 RED** | **2/3** | **FIG 1 BROKEN** |

## Actionable Bug: 37LK5T97 Figure 1

**Root cause:** Two-column layout on page 2. The FIG. 1 caption (`p2:2`, 246px wide, left column) was classified as `body_paragraph` because the narrow width triggered narrative-prose rejection AND the image (`p2:9`, right column) was in a different column, preventing spatial pairing.

**Vision confirmed:**
- `p2:2` IS the FIG. 1 caption (text: "FIG. 1. Both IM and EC ossification occurs during the bone-healing process...") — seed_role was `figure_caption_candidate`
- `p2:9` IS the FIG. 1 image (693x339px, raw_label='image')
- Blocks `p2:3-p2:8` are FIG. 1 composite diagram interior callouts (Phase I/II/III labels)

**Pipeline defect:** `body_paragraph` role assigned in `normalize_document_structure()` — the narrow-caption + two-column layout caused the caption to be rejected as "figure mention with narrative prose in body spine" rather than kept as a short caption.

**Fix path:** Similar to previous narrow-caption fixes (WV2FF4NV locator bridge pattern). The caption-candidate rejection logic needs a column-aware exception: if a `figure_caption_candidate` is in a different column than the body spine, and the adjacent column has an `media_asset`, the candidate should be preserved.

## Papers That Just Work (no issues found)

5 of 10 papers (53B47JM8, 72D4YXEB, 82W2IJIP, B43QSAJP, 95FDVE4W) had all figures correctly matched with 0 gaps, 0 unmatched assets, 0 unmatched legends. This suggests the pipeline's figure matching is robust for standard single-column papers with clear figure layouts.

## Cross-References

- Audit scripts: `.opencode/skills/paperforge-development/scripts/ocr_truth_audit.py`
- Per-paper audit reports: `audit/<KEY>/audit_report.json`
- Annotated pages: `audit/<KEY>/annotated_pages/`
