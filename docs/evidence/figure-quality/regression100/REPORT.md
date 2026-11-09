# Regression 100 independent acceptance

## Decision

**NO-GO — do not freeze the algorithm yet.** The replay has three missing figure assets and three corresponding render outputs across two papers, despite zero dangling fulltext targets. This violates the required replay-delivery gate and is absent from Dev 50. No code or rules were changed.

## Scope and method

Ran `figure_quality_eval.py --set regression` read-only against the frozen 100-key set and the current master implementation. The replay covered 100 papers and 552 matched figure records; the harness reported 100/100 cases passed its limited case predicate. Structural gates below were evaluated separately because that predicate does not check all acceptance criteria. Per-paper `baseline.json` and `result.json` are retained. Missing pre-migration files are reported separately from replay output gaps.

## Structural gates

| Gate | Result |
|---|---:|
| Replay errors | 0 — PASS |
| Unique IDs in replay identity output | 100/100 papers — PASS |
| Replay-delivered figure assets | 3 missing across 2 papers — **FAIL** |
| Replay-delivered figure renders | 3 missing across 2 papers — **FAIL** |
| Dangling fulltext targets / embeds missing new IDs | 0 — PASS |
| Text decrease | 0 papers — PASS |
| Pending markers | 0 in pre-migration source; 4 in replay inventories across 3 papers — reported separately |
| Table claim changes vs current master/source baseline | 2 changes in 2 papers: `64AWS4SU`, `G5QGQ9PB` — report only; not fixed |

Delivery gaps: `6QNRHRKX` lacks assets and renders for `figure_unknown_000` and `figure_unknown_001`; `M36WA39N` lacks them for `figure_005_continued_p010_b19`. The source PDF page contexts visibly contain these figures, but the replay manifest does not deliver their figure assets/renders. These are replay gaps, not the separate pre-migration backlog of 364 absent current asset files.

New replay pending markers occur in `6GB9I9KG` (1 unresolved cluster), `8K39NHUQ` (1), and `AT99P8YS` (2); all three had zero pre-migration source pending markers. They are disclosed separately, not attributed to source state.

## Visual review

Manually reviewed 42 figure/caption views from 21 papers. Sampling was stratified across association, caption recall, crop/panel, page assembly, and no-signal controls; an additional delivery-gap follow-up was included. Diagnostic flags selected strata only and were not treated as defect labels. Each sampled record is marked `reviewed` with a manually assigned root-cause category in `sample_sheets/sample.json`.

| Visual root cause | Figures |
|---|---:|
| Delivery | 3 |
| No visible defect | 39 |

The three confirmed delivery findings are the two `6QNRHRKX` figures and the continued `M36WA39N` figure. The other sampled figure/caption pairs visually aligned; no association, caption-recall, crop/panel, or page-assembly defect was confirmed in those views. This is a sample, not a claim that all 552 figures were visually adjudicated. Six compact sheets are in `sample_sheets/`.

## Comparison with Dev 50

| Signal | Dev 50 | Regression 100 |
|---|---:|---:|
| Papers / matched figures | 50 / 254 | 100 / 552 |
| Papers with repeated figure IDs (diagnostic signal) | 6 | 13 |
| Unmatched legend items | 17 | 24 |
| Unmatched assets | 54 | 143 |
| Replay-missing figure assets / renders | 0 / 0 | 3 / 3 |
| Replay dangling fulltext targets | 0 | 0 |
| Visually confirmed sample defects | 2/30 (6.7%) | 3/42 (7.1%) |

Legend/asset and repeated-ID counts are screening signals, not adjudicated defects; inventory sizes differ. The sample defect rate is descriptive, not a performance estimate. The new replay-delivery failures are the decision-driving finding; the earlier Dev 50 sample had none.

## Artifacts

- `diagnostics.json`: per-paper gates, source-vs-replay pending markers, delivery arrays, table-change evidence, Dev 50 comparison, and manually reviewed sample labels.
- `<KEY>/baseline.json` and `<KEY>/result.json`: 100 per-paper evidence pairs.
- `sample_sheets/`: 42 reviewed views, sample manifest, and six compact sheets.
- Total retained artifact size: approximately 1.7 MB (<10 MB).
