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

## Lifecycle-aware scoring

Agent-only values are scored from `labels.jsonl`; human-verified values use only `status=confirmed` user findings. The cohorts are never mixed. `null` stays unknown (not a pass), and only confirmed findings contribute human failures or association false negatives. Superseded and disputed records remain auditable but are excluded from confirmed-failure metrics.

| Key | Metric set | Association P/R | FN | Crop failures | Delivery failures | Unknown |
|---|---|---:|---:|---:|---:|---:|
| 3QYCST4E | Agent-scored | 0.86 / 0.67 | 3 | 2 | 0 | 0 |
| 3QYCST4E | Human-verified | n/a (0 findings) | 0 | 0 | 0 | 0 |
| 28JLIHLS | Agent-scored | 1.00 / 0.70 | 3 | 0 | 0 | 0 |
| 28JLIHLS | Human-verified | 1.00 / 0.33 | 2 | 0 | 1 | 4 |

For 28JLIHLS, four records have at least one unknown measurement: one unknown expected asset identity, three unknown crop values, one unknown delivery value, and four unknown panel values (field counts overlap). Unknown is not a pass; only the two confirmed records contribute to human-verified failure metrics. The Q5-era manual-adjusted 3QYCST4E score was P/R 0.88/0.70, crop failures 2, delivery failures 1; after Q5, Figure 1B is delivered (asset 8), so that stale failure is superseded and excluded. The old 28JLIHLS manual-adjusted score was P/R 1.00/0.78, crop failures 1, delivery failures 3; lifecycle scoring now excludes the disputed Figure 2 crop and stale cross-page/Figure 9 delivery claims. Figure 5 remains confirmed (expected p4/b0+b2); Figure 6 is confirmed as p4/b6 only.

| Finding | Lifecycle | Reason / evidence |
|---|---|---|
| 3QYCST4E figure_001B | Superseded | Q5 / PR #401 delivered figure_001B, asset 8. |
| 28JLIHLS figure_002 crop | Disputed | Q6 / PR #402 evidence reports no 24h/72h text; caption says t=0, 30, 60. The finding does not count as a crop failure. |
| 28JLIHLS figure_005 | Confirmed | Q7 supports p4/b0+b2; block 6 belongs to Figure 6. |
| 28JLIHLS figure_006 cross-page merge | Superseded | Q7 supports p4/b6 only; no p5 continuation. |
| 28JLIHLS figure_006 asset | Confirmed | Q7 supports expected asset {6}. |
| 28JLIHLS figure_009 multi-page merge | Disputed | Q7 found no Fig. 9 caption/image in the supplied PDF; external ownership remains unknown. |

Detailed counts and the three cohort objects (`agent_scored`, `human_verified`, `unknown`) are stored in `result.json`. The original agent-only smoke-set totals above are unchanged; this lifecycle overlay does not rewrite agent labels or infer a pass from missing evidence.

## Manual review provenance

Original notes are preserved in `MANUAL-REVIEW.md`; lifecycle status and evidence references are recorded in `manual_findings.jsonl`. Q7 source review is documented in `../q7/REPORT.md` and `../q7/evidence.json`.
