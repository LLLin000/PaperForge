# Human Review Census — Canonical-Missing Proposal Previews

> **Date frozen:** 2026-08-21
> **Status:** Rules frozen BEFORE review begins (no post-hoc criteria)
> **Scope:** All 42 preview-verified candidates from `bounded-slot-preview-v3-set.json` — full census, not a sample.

## Decision categories (frozen)

| Category | Definition |
|----------|-----------|
| `confirmed` | The candidate visual object fully corresponds to the target Figure; caption/legend correspondence is correct. |
| `wrong_visual` | The visual object belongs to a different Figure or is clearly not the target Figure. |
| `partial_visual` | The correct target Figure was identified, but only some panels/visual content were recovered. |
| `wrong_grouping` | The base visual content is related, but the grouping/crop combination is wrong (e.g. extra panels merged in, panels missing from the merge). |
| `uncertain` | Even manual PDF inspection cannot reliably adjudicate. |

## Primary metric (frozen)

```text
human-confirmed precision = confirmed / 40
```

Denominator: the 40 PDF-confirmed structurally unique proposals.
`uncertain` stays in the denominator — "human cannot confirm" is not success.

## Secondary metrics (reported separately)

```text
secondary review outcome  = human decisions on the 2 unique_without_pdf_confirmation candidates
overall confirmation rate = confirmed / 42 (optional context only)
```

## Review table schema (minimum provenance per row)

| Field | Required |
|-------|----------|
| paper_key | always |
| figure_label | always |
| proposal_subtype | always |
| candidate_kind | always |
| pdf_confirmation | always |
| human_decision | always |
| review_note | required when human_decision ≠ confirmed |

## Interpretation boundary

`42/42 CLEAN` means materialization and internal render consistency succeeded for every preview.
It does NOT mean any of them are semantically correct. That is what this census answers.

## Acceptance criterion

If primary precision is high, the canonical-missing reconciliation path is accepted as:

```text
canonical missing
→ bounded evidence reconciliation
→ high-quality proposal preview
→ human confirmation
```

No further machine-rule expansion before this census completes.
