# Smoke-set visual annotation (round 1)

Reviewer: `agent-visual-v1`. Basis: page overlays, per-figure crops, current replay labels; not source-vault file presence (new objects do not exist pre-migration). This is an agent visual pass, not an independent human adjudication; human spot-check is still required.

## Coverage and score

| Key | Reviewed / rows | Association P | R | Caption fail | Panel fail | Crop fail | Delivery fail |
|---|---:|---:|---:|---:|---:|---:|---:|
| 28ALPCY7 | 9/9 | 1.00 | 0.96 | 0 | 0 | 0 | 0 |
| 28JLIHLS | 7/7 | 1.00 | 0.70 | 0 | 0 | 0 | 0 |
| 2AZ2EGQB | 4/4 | 1.00 | 1.00 | 0 | 1 | 1 | 0 |
| 2BYRLKQS | 4/4 | 1.00 | 1.00 | 0 | 0 | 0 | 0 |
| 2HEUD5P9 | 7/7 | 1.00 | 1.00 | 0 | 0 | 0 | 0 |
| 388XI46Q | 12/12 | 1.00 | 0.84 | 0 | 0 | 0 | 0 |
| 3QYCST4E | 8/8 | 0.86 | 0.67 | 2 | 0 | 2 | 0 |
| 55EKJRBC | 5/5 | 1.00 | 0.80 | 0 | 0 | 0 | 0 |
| DJLIAZT7 | 19/66 | 0.70 | 1.00 | 0 | 0 | 7 | 0 |
| SRNJDAA2 | 26/26 | 0.80 | 0.77 | 1 | 2 | 0 | 5 |
| **Total** | **101/148** | **0.93** | **0.91** | **3** | **3** | **10** | **5** |

DJLIAZT7 was time-boxed at 19 reviewed rows (66 total); the rest are `reviewer=""`, `time-boxed; not visually reviewed`.

## Findings

- **28JLIHLS**: Figure 5 caption exists but its three page-4 asset blocks are unclaimed (recall 0.70). This is the known lost-figure case.
- **3QYCST4E**: two table captions are present as `unmatched_legend` and counted as caption failures (they are not figure captions); Figure 2/3 crops cut the lower edge (2 crop failures). Precision loss is one extra claim.
- **2AZ2EGQB**: Figure 2 crop contains only panels A/C; panels B/D are missing (1 panel + 1 crop failure).
- **388XI46Q**: Figure 5 now exists (caption p15, asset p14) and scores as a true positive. Recall 0.84; the missing rows are reserved/assetless figures and the Fig.8 continuation, not the new cross-page case.
- **DJLIAZT7**: 7 crop failures in the 19 reviewed rows (mostly old duplicate-id figures); the rest of the paper is unannotated.
- **SRNJDAA2**: the weakest paper: precision 0.80 / recall 0.77, 5 delivery failures, 2 panel failures, 1 caption failure.
- **2HEUD5P9 / 2BYRLKQS**: no failures in this sample.
- **28ALPCY7**: Figure 6 remains assetless; its crop/delivery are `null` (not applicable), so the control is clean.

## Reproduce

```
python scripts/dev/figure_quality_eval.py --set smoke --score \
  --out docs/evidence/figure-quality/smoke \
  --result-out docs/evidence/figure-quality/smoke/result.json
```

`labels.jsonl` rows are the source of truth; `result.json` contains the per-case scores. Unreviewed rows are ignored by scoring. No pipeline or vault changes were made.

## Manual review addendum (user, 2026-11-09)

The user visually reviewed the smoke set; see `MANUAL-REVIEW.md` and `manual_findings.jsonl`. Overrides:

- **3QYCST4E**: Figure 1B (caption block 9, asset block 8, p2) is missing; 1A/1B need a composite split.
- **28JLIHLS**: Figure 2 crop drops the `24h`/`72h` annotations (crop_ok overridden to false); Figure 5 caption remains unassociated; Figure 6 needs a p4→p5 cross-page merge; Figure 9 spans pages and is not merged.
- **SRNJDAA2**: deferred as a difficult item.
