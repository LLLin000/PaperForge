# R1 frozen-algorithm migration plan refresh

Read-only replay of 952 papers against frozen Figure/Caption/Ownership algorithm on master `2e0cfffe`. Eight fresh Python processes, 119 papers each; 0 replay errors. No real migration and no vault writes. M1c evidence is unchanged.

## Audited status and raw frozen-plan status

| Status | M1c | Frozen R1 plan | Audited R1 |
|---|---:|---:|---:|
| READY | 803 | 809 | 788 |
| REQUIRES_APPROVAL | 98 | 89 | 110 |
| HOLD | 41 | 47 | 47 |
| M2_REVIEW_REQUIRED | 10 | 7 | 7 |

Audited R1 applies a table-claim safety overlay to the frozen plan: 21 papers moved from READY to REQUIRES_APPROVAL because table claims are unresolved or share figure media. `plan.jsonl.gz` remains the raw algorithm output; `papers.json` is the final audited status map and retains `frozen_plan_status` for traceability. All delete candidates remain approval-only.

### Other plan metrics (raw frozen plan vs M1c)

| Metric | M1c | R1 | Delta |
|---|---:|---:|---:|
| rename ops | 417 | 429 | +12 |
| retarget unique paths | 243 | 256 | +13 |
| retarget occurrences | 244 | 257 | +13 |
| delete candidates | 400 | 391 | -9 |
| collisions | 27 | 26 | -1 |
| dangling | 0 | 0 | +0 |

Audit totals: 451 renamed identity mappings; 339 figure asset-claim changes; 387 audit embed occurrences retargeted; 39 missing-new-ID audit embeds.

### Every M1c → audited R1 status transition

| Paper | M1c → R1 | Reason |
|---|---|---|
| 28JLIHLS | M2_REVIEW_REQUIRED → REQUIRES_APPROVAL | Q9 restores figure 5/6, but the page 3 Table 1 replay has no unique asset (ambiguous); approval required rather than READY. Table review requires approval: page 3 caption 7 asset 9 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| 3EFCZ7BB | READY → REQUIRES_APPROVAL | Table review requires approval: page 9 caption 3 asset 4 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY.; page 11 caption 3 asset 4 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| 3FDT9652 | READY → REQUIRES_APPROVAL | Table review requires approval: page 4 caption 2 asset 3 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY.; page 5 caption 8 asset 9 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| 3NRZ95DB | READY → REQUIRES_APPROVAL | Table review requires approval: page 3 caption 6 asset 7 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| 3QYCST4E | READY → HOLD | New replay splits an old figure identity across multiple candidates; deterministic file/embed mapping is unavailable, so the paper is held. |
| 4CBS2KKE | READY → REQUIRES_APPROVAL | Table review requires approval: page 4 caption 6 asset none → 2: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| 4KCHGV2Z | READY → REQUIRES_APPROVAL | Table review requires approval: page 7 caption 16 asset 14 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| 4PFR9M5N | READY → REQUIRES_APPROVAL | Table review requires approval: page 7 caption 4 asset 5 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| 5VMA7WNE | READY → REQUIRES_APPROVAL | Table review requires approval: page 4 caption 3 asset 4 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| 6QNRHRKX | READY → REQUIRES_APPROVAL | New replay leaves assetless old figure IDs unmapped; delete candidates require approval, changing READY to approval-required. |
| 6ZWKUPCU | READY → REQUIRES_APPROVAL | Table review requires approval: page 6 caption 3 asset 4 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| 7IYXQ4WM | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| 7ZZN6PUW | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| 87KJHGP8 | READY → REQUIRES_APPROVAL | Table review requires approval: page 6 caption 4 asset 6 → 5: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| 8CCATQE3 | M2_REVIEW_REQUIRED → READY | The prior M2/unmatched-caption hold is resolved in the new replay; the many-to-one figure ownership collision is also gone. |
| 8UC452EE | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| 97M7HFCD | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| A98BQ6YU | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| AQM3M257 | READY → REQUIRES_APPROVAL | Table review requires approval: page 6 caption 1 asset 11 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| CKU5UHFW | READY → HOLD | New replay splits an old figure identity across multiple candidates; deterministic file/embed mapping is unavailable, so the paper is held. |
| CPQ47TBV | READY → REQUIRES_APPROVAL | Table review requires approval: page 5 caption 2 asset 4 → 3: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| DLVSVU49 | READY → REQUIRES_APPROVAL | Table review requires approval: page 6 caption 7 asset 2 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| DR6FGTCA | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| FRU2XUGJ | READY → REQUIRES_APPROVAL | Table review requires approval: page 4 caption 5 asset 12 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| HIU4F3V4 | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| J2U9DWNW | READY → REQUIRES_APPROVAL | Table review requires approval: page 4 caption 2 asset 5 → 3: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| KG7A5K5V | READY → REQUIRES_APPROVAL | Table review requires approval: page 4 caption 14 asset 3 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| KY76CCC7 | READY → HOLD | New replay splits an old figure identity across multiple candidates; deterministic file/embed mapping is unavailable, so the paper is held. |
| LYEFATEN | REQUIRES_APPROVAL → HOLD | New replay splits an old figure identity across multiple candidates; deterministic file/embed mapping is unavailable, so the paper is held. |
| P9D6GZ9M | READY → REQUIRES_APPROVAL | Table review requires approval: page 3 caption 17 asset 7 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| PZ8B59K4 | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| QUJ3AS6S | READY → REQUIRES_APPROVAL | Table review requires approval: page 5 caption 6 asset 10 → 7: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| S9UMIF83 | READY → REQUIRES_APPROVAL | Table review requires approval: page 3 caption 1 asset 3 → 2: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| TNK4V5PF | READY → REQUIRES_APPROVAL | Table review requires approval: page 4 caption 11 asset 18 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| U96H2WCT | READY → HOLD | New replay splits an old figure identity across multiple candidates; deterministic file/embed mapping is unavailable, so the paper is held. |
| WDRU6TDV | READY → REQUIRES_APPROVAL | Table review requires approval: page 3 caption 9 asset 2 → none: Table claim remains unresolved or shares figure media; verify table asset identity and exclusive ownership before paper-level READY. |
| WJNEHSQD | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| XBSC5X2H | REQUIRES_APPROVAL → HOLD | New replay splits an old figure identity across multiple candidates; deterministic file/embed mapping is unavailable, so the paper is held. |
| XU3QKIPZ | M2_REVIEW_REQUIRED → REQUIRES_APPROVAL | The prior unmatched-caption M2 hold is resolved; remaining orphan cleanup is a delete candidate requiring approval. |

Complete machine-readable transitions, including raw-plan status and table-claim evidence, are in `transitions.json`.

## Figure/object, embed, deletion, and text audit

- Replay: 952 papers, 0 errors. Old inventory duplicate extras: 355; fresh replay duplicate extras: 0.
- Embed rows: 6,685; mapped: 6,515; unmapped/held or approval-gated: 170. Reasons: ambiguous_embed 99, reserved_or_assetless 46, identity_mapping_lost 15, caption_present_unmatched 8, unmapped_table 2.
- Rename operations: 429 (M1c 417); retarget unique paths: 256 (M1c 243), occurrences: 257 (M1c 244). No-op mapped embed occurrences: 6,258.
- Delete candidates: 391 (all REQUIRES_APPROVAL), by kind {"embed": 63, "figure": 216, "orphan": 106, "table": 6}; no deletion auto-approved.
- Text characters old/new: 60,604,199 / 60,604,839; body characters: 34,011,261 / 33,986,874. Per-paper old_text_chars decrease: 0. Historical M1c report also recorded zero text-decrease papers.
- Body-character totals are not interchangeable with old_text_chars; no paper-level text decrease was observed.

## Table-claim review: all 36 changes

Reviewed all 36 claims across 33 papers, with source old/new inventories, page/caption, bboxes, table match/switch evidence, and figure-media overlap in `table_claim_review.json`.
- **7 benign corrected claims** across 6 papers: Q11 cross-type reassignment or independent table match is evidenced and the resulting table media is not shared with figure media.
- **29 blocking claims** across 27 papers: unmatched/withdrawn/ambiguous/low-confidence table asset or figure/table shared media. This puts 21 previously READY papers into REQUIRES_APPROVAL; 6 were already non-READY.
- Bbox overlap below is geometric intersection of the old and replayed table asset bbox; `n/a` means one side has no matched asset/bbox. Figure-sharing column records exact shared media IDs or bbox intersection with replay figure media. Full bboxes are in the JSON artifact.

| Paper | Page / caption block | Old → new asset | Old/new table bbox overlap? | Figure media relation | Class / causal evidence |
|---|---|---|---|---|---|
| 28JLIHLS | 3 / 7 | 9 → none | n/a (missing bbox) | none observed | BLOCKING; Q9 Figure 5/6 restoration co-occurs, but direct causal link to table-match loss is not established. |
| 3EFCZ7BB | 9 / 3 | 4 → none | n/a (missing bbox) | old shared | BLOCKING; Q11-related figure/table shared-media evidence; no explicit Q5/Q9 attribution. |
| 3EFCZ7BB | 11 / 3 | 4 → none | n/a (missing bbox) | old shared | BLOCKING; Q11-related figure/table shared-media evidence; no explicit Q5/Q9 attribution. |
| 3FDT9652 | 4 / 2 | 3 → none | n/a (missing bbox) | old shared | BLOCKING; Q11-related figure/table shared-media evidence; no explicit Q5/Q9 attribution. |
| 3FDT9652 | 5 / 8 | 9 → none | n/a (missing bbox) | old shared | BLOCKING; Q11-related figure/table shared-media evidence; no explicit Q5/Q9 attribution. |
| 3NRZ95DB | 3 / 6 | 7 → none | n/a (missing bbox) | old shared | BLOCKING; Q11-related figure/table shared-media evidence; no explicit Q5/Q9 attribution. |
| 4CBS2KKE | 4 / 6 | none → 2 | n/a (missing bbox) | new shared/overlap | BLOCKING; Q11-related figure/table shared-media evidence; no explicit Q5/Q9 attribution. |
| 4FL992ND | 3 / 2 | 3 → none | n/a (missing bbox) | old shared | BLOCKING; Q11-related figure/table shared-media evidence; no explicit Q5/Q9 attribution. |
| 4KCHGV2Z | 7 / 16 | 14 → none | n/a (missing bbox) | none observed | BLOCKING; No direct Q5/Q9/Q11 causal evidence found for this claim change. |
| 4PFR9M5N | 7 / 4 | 5 → none | n/a (missing bbox) | none observed | BLOCKING; No direct Q5/Q9/Q11 causal evidence found for this claim change. |
| 5VMA7WNE | 4 / 3 | 4 → none | n/a (missing bbox) | none observed | BLOCKING; No direct Q5/Q9/Q11 causal evidence found for this claim change. |
| 64AWS4SU | 4 / 4 | 8 → 5 | no (IoU 0.000) | old shared | benign; Q11-related ownership conflict; replay records cross_type_conflict_table_asset_reassigned. |
| 6ZWKUPCU | 6 / 3 | 4 → none | n/a (missing bbox) | none observed | BLOCKING; No direct Q5/Q9/Q11 causal evidence found for this claim change. |
| 76YD9KGK | 5 / 2 | none → 2 | n/a (missing bbox) | new shared/overlap | BLOCKING; Q11-related figure/table shared-media evidence; no explicit Q5/Q9 attribution. |
| 87KJHGP8 | 6 / 4 | 6 → 5 | no (IoU 0.000) | old shared + new shared/overlap | BLOCKING; Q11-related ownership conflict; replay records cross_type_conflict_table_asset_reassigned. |
| 9P2W6J8Q | 9 / 2 | none → 3 | n/a (missing bbox) | new shared/overlap | BLOCKING; Q11-related figure/table shared-media evidence; no explicit Q5/Q9 attribution. |
| A4T4TRT2 | 4 / 0 | 3 → 1 | no (IoU 0.000) | old shared | benign; Q11-related ownership conflict; replay records cross_type_conflict_table_asset_reassigned. |
| API5RITV | 50 / 3 | none → 4 | n/a (missing bbox) | new shared/overlap | BLOCKING; Q11-related figure/table shared-media evidence; no explicit Q5/Q9 attribution. |
| AQM3M257 | 6 / 1 | 11 → none | n/a (missing bbox) | old shared | BLOCKING; Q11-related ownership conflict; replay records cross_type_conflict_no_unique_table_asset. |
| CPQ47TBV | 5 / 2 | 4 → 3 | no (IoU 0.000) | old shared + new shared/overlap | BLOCKING; Q11-related ownership conflict; replay records cross_type_conflict_table_asset_reassigned. |
| DLVSVU49 | 6 / 7 | 2 → none | n/a (missing bbox) | old shared | BLOCKING; Q11-related ownership conflict; replay records cross_type_conflict_no_unique_table_asset. |
| FRU2XUGJ | 4 / 5 | 12 → none | n/a (missing bbox) | old shared | BLOCKING; Q11-related ownership conflict; replay records cross_type_conflict_no_unique_table_asset. |
| G5QGQ9PB | 5 / 2 | 9 → 3 | no (IoU 0.000) | old shared | benign; Q11-related ownership conflict; replay records cross_type_conflict_table_asset_reassigned. |
| IVMKWLFV | 3 / 8 | 2 → none | n/a (missing bbox) | old shared | BLOCKING; Q11-related ownership conflict; replay records cross_type_conflict_no_unique_table_asset. |
| J2U9DWNW | 4 / 2 | 5 → 3 | no (IoU 0.000) | old shared + new shared/overlap | BLOCKING; Q11-related ownership conflict; replay records cross_type_conflict_table_asset_reassigned. |
| KG7A5K5V | 4 / 14 | 3 → none | n/a (missing bbox) | old shared | BLOCKING; Q11-related ownership conflict; replay records cross_type_conflict_no_unique_table_asset. |
| M84CTEM9 | 10 / 3 | none → 5 | n/a (missing bbox) | none observed | benign; No direct Q5/Q9/Q11 causal evidence found for this claim change. |
| M84CTEM9 | 10 / 7 | none → 9 | n/a (missing bbox) | none observed | benign; No direct Q5/Q9/Q11 causal evidence found for this claim change. |
| P9D6GZ9M | 3 / 17 | 7 → none | n/a (missing bbox) | old shared | BLOCKING; Q11-related ownership conflict; replay records cross_type_conflict_no_unique_table_asset. |
| QUJ3AS6S | 5 / 6 | 10 → 7 | no (IoU 0.000) | old shared + new shared/overlap | BLOCKING; Q11-related ownership conflict; replay records cross_type_conflict_table_asset_reassigned. |
| S9UMIF83 | 3 / 1 | 3 → 2 | no (IoU 0.000) | old shared + new shared/overlap | BLOCKING; Q11-related ownership conflict; replay records cross_type_conflict_table_asset_reassigned. |
| TNK4V5PF | 4 / 11 | 18 → none | n/a (missing bbox) | old shared | BLOCKING; Q11-related ownership conflict; replay records cross_type_conflict_no_unique_table_asset. |
| VVKIB2EM | 10 / 2 | 14 → 4 | no (IoU 0.000) | old shared + new shared/overlap | BLOCKING; Q11-related ownership conflict; replay records cross_type_conflict_table_asset_reassigned. |
| WDRU6TDV | 3 / 9 | 2 → none | n/a (missing bbox) | old shared | BLOCKING; Q11-related ownership conflict; replay records cross_type_conflict_no_unique_table_asset. |
| Z73N29KR | 4 / 1 | 4 → 2 | no (IoU 0.000) | old shared | benign; Q11-related ownership conflict; replay records cross_type_conflict_table_asset_reassigned. |
| ZFNT2XS7 | 4 / 12 | 16 → 13 | no (IoU 0.000) | old shared | benign; Q11-related ownership conflict; replay records cross_type_conflict_table_asset_reassigned. |

### Named cases

- **64AWS4SU, page 4/caption 4, block 8 → 5 (8→5 claim): benign corrected.** The old bbox `[168,1042,531,1394]` is exactly the replay Figure 6 media (IoU 1.0); replay explicitly records `cross_type_conflict_table_asset_reassigned`. New block 5 is a separately matched table bbox `[100,635,598,1011]` with extracted HTML table content, no overlap with old bbox or replay figure media. This is a Q11 ownership-conflict correction, not a table losing its content.
- **G5QGQ9PB, page 5/caption 2, block 9 → 3 (9→3 claim): benign corrected.** Old bbox `[255,723,940,1400]` is exactly replay Figure 3 media and overlaps Figure 2 media (IoU 0.596); replay explicitly reassigns after cross-type conflict. New block 3 has extracted HTML table content at `[108,194,1077,313]`, separate from figure media. This is a Q11 ownership-conflict correction.
- **28JLIHLS, page 3/caption 7, block 9 → no asset: BLOCKING.** Old block 9 contains table HTML; fresh table match is `ambiguous`/`unmatched`, no new asset or bbox, so there is no evidence preserving the table claim. Figure 5/6 restoration co-occurs, but no direct causal link to table matching is proven. The paper is REQUIRES_APPROVAL, not READY.
- Shared-media blockers include `4CBS2KKE`, `76YD9KGK`, `87KJHGP8`, `9P2W6J8Q`, `API5RITV`, `CPQ47TBV`, `J2U9DWNW`, `QUJ3AS6S`, `S9UMIF83`, `VVKIB2EM`; their table media shares a block ID or bbox with figure media and is not accepted as paper-level safe.

## Other blocking anomalies

- Audited paper status is 788 READY, 110 REQUIRES_APPROVAL, 47 HOLD, 7 M2_REVIEW_REQUIRED. Table review added 21 approval requirements; no object-level `delivery_allowed=true` is treated as paper-level READY.
- Unresolved collision clusters: 20 papers / 26 collision records (M1c 27); dangling references: 0 (M1c 0). No new dangling cases.
- Text decreases: none. Table claim changes and figure shared-media conflicts are separately enumerated in `anomalies.json`.
- All 355 old duplicate-ID extras are eliminated in the replay. `3QYCST4E` Q5 1A/1B remains HOLD for ambiguous old-ID/embed mapping; `28JLIHLS` Q9 Figure5/6 is now table-approval-gated despite restored figures; `6A8A9TWD` stays READY under full-plan review, with Figure1 numbered and Figure2A/B/C grouped.

## Artifacts

- `summary.json`: raw frozen-plan metrics plus audited status counts and table-review metrics.
- `plan.jsonl.gz`: raw 952-paper plan from frozen algorithm.
- `papers.json`: audited paper status, frozen-plan status, and table-review overrides.
- `transitions.json`: all M1c-to-audited-R1 transitions with explanations.
- `table_claim_review.json`: all 36 detailed per-claim records, bboxes, overlap, ownership evidence, and classifications.
- `anomalies.json`: blocking table cases, named table claims, figure reductions, hold/collision/dangling cases.
- `external_refs.json`: 200 matches, capped=True.
- `batches/`: eight fresh-process reports/plans plus merged plan JSONL.
