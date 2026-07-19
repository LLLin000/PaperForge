# OCR Truth Audit: SKXTCE6M

**Paper:** Hashemi-Afzal et al., 2025 — *Advancements in hydrogel design for articular cartilage regeneration*
**Status:** Yellow (31p, 723 blocks, 17 figure captions, 14 matched figures, 4 tables)

## Figure Matching Quality: ✅ GOOD

All 14 matched figures verified:
- Crops are clean, no adjacent content bleeding
- Multi-panel figures (Fig 4: 8 sub-panels, Fig 5: 17 sub-panels) correctly stacked
- Caption text matches the visual figure content
- Sub-panel labels (Ⅰ, Ⅱ, Ⅲ) correctly rejected as separate figures (8 rejected legends)

## Primary Finding: Table-Figure Role Misclassification ⚠️

**6 unmatched legends + 4 orphans** all trace to the same root cause.

| Symptom | Count | Root Cause |
|---------|-------|------------|
| Unmatched legends with "Summary of..." text | 6 | `raw_label=figure_title` assigned to table titles |
| Orphan images that are actually tables | 4 | Table content rendered as figure-like, no figure caption match |
| Ambiguous figures (no candidates) | 2 | Same blocks as unmatched legends |

The raw OCR classifier labels any bold/centered title text as `figure_title`, but 6 of these titles sit above HTML `<table>` blocks:

| Page | `raw_label` | Actual Content |
|------|------------|----------------|
| 3 | `figure_title` | "Table 2" + summary above `<table>` |
| 8 | `figure_title` | "Table 3" + summary above `<table>` |
| 11 | `figure_title` | Summary above `<table>` |
| 15 | `figure_title` | Summary above `<table>` |
| 19 | `figure_title` | Summary above `<table>` |
| 23 | `figure_title` | Summary above `<table>` |

## Verdict

- **Figure matching itself works well.** 14/14 matched figures are correct.
- **The "yellow" status is false positive.** Caused by table→figure routing, not real figure quality issues.
- **Fix path:** In role classification: if `raw_label=figure_title` and adjacent to `<table>` block → assign `table_caption` role instead.
