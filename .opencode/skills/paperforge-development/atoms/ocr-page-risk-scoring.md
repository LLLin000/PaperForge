# OCR Page Risk Scoring

Use this only for `high-risk` mode page selection.

Truth-first note:

- The score prioritizes likely inspection value.
- It does not author expected truth.
- Final judgment still comes from visual review plus artifact grounding.

## Fixed Additive Formula

```text
page_risk_score =
  +5 if page == 1
  +5 if contains reference_heading
  +4 if contains both body_paragraph and reference_item
  +4 if contains tail/body/ref mixed evidence
  +4 if figure/table asset count >= 2
  +3 if caption count != asset count
  +3 if reader/object coverage gap exists
  +2 if verify-required HOLD count >= threshold
  +2 if unknown_structural count >= threshold
```

## Risk Reason Hints

Suggested reason labels:

- `frontmatter_page`
- `reference_heading_present`
- `mixed_body_reference`
- `same_page_boundary`
- `multi_asset_page`
- `caption_asset_mismatch`
- `reader_object_gap`
- `hold_threshold`
- `unknown_structural_threshold`

## Example Output Shape

```json
{
  "page": 7,
  "risk_score": 14,
  "risk_reasons": [
    "mixed_body_reference",
    "reference_heading_present",
    "same_page_boundary"
  ],
  "recommended_audit_targets": [
    "reference_span",
    "reading_order"
  ]
}
```
