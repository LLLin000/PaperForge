# Media Asset Vision Audit Report

> **Date**: 2026-07-02
> **Method**:  via 
> **Sample**: 14 valid images from 3 papers (24A2QUAH, 28ALPCY7, 5S7UI34M)
> **Extraction**: Cropped from PDF pages via PyMuPDF using media_asset bboxes

## Results

| File | Content Type | Smart Has Caption? | Raw Label |
|------|-------------|-------------------|-----------|
| 24A2QUAH_p3_b3_table.png | data table | YES | table |
| 24A2QUAH_p7_b3_table.png | data table | YES | table |
| 24A2QUAH_p8_b3_table.png | data table | YES | table |
| 28ALPCY7_p25_b3_image.png | figure/chart | YES | image |
| 28ALPCY7_p25_b4_image.png | figure/chart | YES | image |
| 28ALPCY7_p26_b3_image.png | figure/chart | YES | image |
| 5S7UI34M_p1_b2_image.png | journal logo | no | image |
| 5S7UI34M_p4_b2_image.png | figure/chart | YES | image |
| 5S7UI34M_p6_b4_image.png | figure/chart | YES | image |
| 5S7UI34M_p6_b6_image.png | figure/chart | YES | image |
| 5S7UI34M_p8_b3_image.png | figure/chart | YES | image |
| 5S7UI34M_p8_b8_chart.png | figure/chart | YES | chart |
| 5S7UI34M_p8_b9_image.png | figure/chart | YES | image |
| 5S7UI34M_p8_b12_image.png | figure/chart | YES | image |

## Summary

- **Data tables**: 3 (all raw_label=table)
- **Figures/charts**: 10 (raw_label=image or chart)
- **Journal logo**: 1 (page 1, raw_label=image)
- **Should have caption**: 13/14
- **Corrupted crops**: 11 (invalid bbox dimensions during PDF extraction)

## Key Finding

Of 14 successfully extracted media_asset blocks, **13 are real scientific content** that should have been matched with a figure/table caption:
- 3 data tables (raw_label=table) — should be table_html, matched with table captions
- 10 figures/charts (raw_label=image or chart) — should be figure_asset, matched with figure captions
- 1 journal logo on page 1 — correctly excluded from matching

The 650 media_asset with raw_label=table across the corpus are very likely **real data tables misclassified as media_asset** instead of table_html.
The 225 media_asset with raw_label=chart are likely **real figures misclassified as media_asset** instead of figure_asset.
