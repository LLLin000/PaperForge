# R1 frozen-algorithm migration plan refresh

Read-only replay of all 952 papers against the frozen Figure/Caption/Ownership algorithm on master `2e0cfffe`. Eight fresh Python processes, 119 papers each; 0 replay errors. No real migration and no vault writes. M1c evidence is unchanged.

## Status and plan metrics

| Metric | M1c | R1 | Delta |
|---|---:|---:|---:|
| READY | 803 | 809 | +6 |
| REQUIRES_APPROVAL | 98 | 89 | -9 |
| M2_REVIEW_REQUIRED | 10 | 7 | -3 |
| HOLD | 41 | 47 | +6 |
| rename ops | 417 | 429 | +12 |
| retarget unique paths | 243 | 256 | +13 |
| retarget occurrences | 244 | 257 | +13 |
| delete candidates (approval-only) | 400 | 391 | -9 |
| collisions | 27 | 26 | -1 |
| dangling | 0 | 0 | +0 |

R1 audit totals: 451 renamed identity mappings; 339 figure asset-claim changes; 387 audit embed occurrences retargeted; 39 missing-new-ID audit embeds.
All 391 delete candidates have `REQUIRES_APPROVAL`; none is auto-approved. Never interpret object-level `delivery_allowed=true` as paper-level READY. R1 READY is 809 papers; 54 papers remain HOLD/M2.

### Every paper status transition

| Paper | M1c → R1 | Reason from plan delta |
|---|---|---|
| 28JLIHLS | M2_REVIEW_REQUIRED → READY | The prior M2/unmatched-caption hold is resolved in the new replay; the caption now has a deterministic figure match. |
| 3QYCST4E | READY → HOLD | New replay splits an old figure identity across multiple candidates; deterministic file/embed mapping is unavailable, so the paper is held. |
| 6QNRHRKX | READY → REQUIRES_APPROVAL | New replay leaves assetless old figure IDs unmapped; delete candidates require approval, changing READY to approval-required. |
| 7IYXQ4WM | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| 7ZZN6PUW | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| 8CCATQE3 | M2_REVIEW_REQUIRED → READY | The prior M2/unmatched-caption hold is resolved in the new replay; the many-to-one figure ownership collision is also gone. |
| 8UC452EE | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| 97M7HFCD | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| A98BQ6YU | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| CKU5UHFW | READY → HOLD | New replay splits an old figure identity across multiple candidates; deterministic file/embed mapping is unavailable, so the paper is held. |
| DR6FGTCA | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| HIU4F3V4 | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| KY76CCC7 | READY → HOLD | New replay splits an old figure identity across multiple candidates; deterministic file/embed mapping is unavailable, so the paper is held. |
| LYEFATEN | REQUIRES_APPROVAL → HOLD | New replay splits an old figure identity across multiple candidates; deterministic file/embed mapping is unavailable, so the paper is held. |
| PZ8B59K4 | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| U96H2WCT | READY → HOLD | New replay splits an old figure identity across multiple candidates; deterministic file/embed mapping is unavailable, so the paper is held. |
| WJNEHSQD | REQUIRES_APPROVAL → READY | Previously approval-gated reserved/assetless or orphan candidates disappear under the new replay; no delete candidate remains. |
| XBSC5X2H | REQUIRES_APPROVAL → HOLD | New replay splits an old figure identity across multiple candidates; deterministic file/embed mapping is unavailable, so the paper is held. |
| XU3QKIPZ | M2_REVIEW_REQUIRED → REQUIRES_APPROVAL | The prior unmatched-caption M2 hold is resolved; remaining orphan cleanup is a delete candidate requiring approval. |

Complete machine-readable transition details (hold codes and delete reasons) are in `transitions.json`; statuses for all papers are in `papers.json`.

## Identity, embeds, deletion, and integrity

- Replay: 952 papers, 0 errors. Old inventory duplicate extras: 355; new replay duplicate extras: 0.
- Embed rows: 6685; mapped: 6515; unmapped/held or approval-gated: 170. Reasons: `ambiguous_embed` 99, `reserved_or_assetless` 46, `identity_mapping_lost` 15, `caption_present_unmatched` 8, `unmapped_table` 2.
- Rename operations 429 (M1c 417); retarget paths 256 (M1c 243), occurrences 257 (M1c 244). No-op mapped embed occurrences: 6258.
- Delete candidates 391 by kind: {"embed": 63, "figure": 216, "orphan": 106, "table": 6}; reasons: {"identity_mapping_lost": 15, "many_to_one collision": 50, "old table has no new counterpart": 6, "orphan no longer inventoried": 106, "reserved_or_assetless": 115, "superseded by several new objects; old file cannot be mapped 1:1": 60, "unmapped_assetless": 37, "unmapped_table": 2}. All remain approval-only.
- R1 old/new text characters: 60,604,199 / 60,604,839; body characters: 34,011,261 / 33,986,874. Decrease: 0 papers, 0 chars. Historical M1c report also recorded zero text-decrease papers.
- The R1 aggregate body-character total is lower than the old-body total, but there is no paper-level `old_text_chars` → `new_text_chars` decrease; text counters are not interchangeable.

## Q5 / Q9 / Q11 targeted cases

- **Q5, `3QYCST4E` (Figure 1A/1B):** old identity `figure_001` has two caption anchors (1A and 1B); fresh replay emits six unique figures and maps 1A to `figure_001`, 1B to `figure_001B`. Because the old single file/embed cannot map deterministically to both candidates, plan holds with `AMBIGUOUS_OLD_ID` + `AMBIGUOUS_EMBED`; two old figure artifacts are approval-only delete candidates. Paper status READY → HOLD is expected safety behavior, not a failed replay.
- **Q9, `28JLIHLS` (Figure 5/6):** fresh replay restores `figure_005` and delivers a separate `figure_006`; previous unmatched-caption M2 hold clears. No missing asset/render and no collisions/dangling. M2_REVIEW_REQUIRED → READY. Figure 5 asset claim narrows from block IDs [0,2,6] to [0,2]; this is a claim-change audit delta, not a missing delivery.
- **Q11 duplicate/exclusive ownership:** all 355 old duplicate-ID extras are eliminated in fresh replay (0 new duplicate extras). `6A8A9TWD` old inventory has 5 entries/4 unique IDs; new replay has 4/4. The assetless reserved Figure 1 becomes `figure_001`; `figure_s002` retains the Figure 2A/2-B/2-C group and its claimed blocks. Paper remains READY, but that is from its full plan, not an object delivery flag. `8CCATQE3` loses the M1c many-to-one collision (`figure_001` vs `figure_s001`) and unmatched-caption hold; it becomes READY. Remaining unresolved collision clusters: 20 papers / 26 collision records; they are separately listed in `anomalies.json` and do not turn any other paper READY.

## Table-claim audit

- Tables: 1,766 old and 1,766 replayed; 36 claim changes across 33 papers.
 - Named claims: `64AWS4SU` has page 4, caption 4, old claim `8` → new `5`; `G5QGQ9PB` has page 5, caption 2, old claim `9` → new `3`. Both are explicitly retained in `anomalies.json`.
- All 36 table-claim changes with paper/page/caption/old/new value are enumerated in `anomalies.json`.

## Blocking anomalies (separate from delivery)

- 54 papers are HOLD/M2; see `anomalies.json` for every hold code, candidate, and reason. This includes identity ambiguity and unmatched-caption cases.
- 20 papers retain 26 unresolved collision records (M1c: 27); 0 dangling references (M1c: 0). No new dangling cases.
- Text decreases: none. Table-claim changes: 36, all explicitly listed above and in the anomaly artifact.
- Figure asset claims narrow for 137 figure objects; 26 belong to papers still not READY (14 approval-required, 9 HOLD, 3 M2). The 111 READY papers are READY only by their full plan, not because an object-level claim/delivery flag alone establishes paper-level safety.

## Artifacts

- `summary.json`: full current totals and operation/reason counts.
- `plan.jsonl.gz`: full 952-paper migration plan.
- `papers.json`: R1 per-paper status map.
- `transitions.json`: all 19 status transitions with individual reasons and old/new hold/delete evidence.
- `external_refs.json`: external references; 200 matches, capped=True.
- `batches/`: eight fresh-process report JSON and plan JSONL outputs plus merged JSONL; not M1c.
