---
name: paperforge-development
description: Use when doing PaperForge engineering or internal OCR truth-audit work. Triggered by: "OCR审计" "审OCR" "审计OCR" "审一下" "审计这篇" "block review" "ocr truth audit" "annotated pages" "看下角色对不对" "块角色" "visual audit" "对照一下图片" "校对block".
---

# PaperForge Development

Developer-only skill family for internal PaperForge OCR audit work.

Use this when the task is to inspect OCR truth, classify failures, and write audit evidence without changing the runtime PaperForge skill graph.

## Route

- OCR truth audit: `workflows/ocr-truth-audit.md`

## Scripts

- Audit helper: `scripts/ocr_truth_audit.py`

## Invariant

- Truth first.
- Do not start by authoring expectations.
- Establish block-level truth from page visuals and artifacts before comparing pipeline behavior.
