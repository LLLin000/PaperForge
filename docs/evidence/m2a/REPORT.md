# Object Migration Review (M2a)

Cases: 31 (27 caption_present_unmatched + 2 controls).

## Counts

- CAPTION_MISCLASSIFIED: 1
- IDENTITY_MAPPING: 1
- OLD_MISMATCH: 3
- REAL_ASSOCIATION_FAILURE: 26

## Case table

| Key | Old id | Page | Old asset | New candidates | Classification | Confidence | Proposed action |
|---|---|---:|---|---|---|---|---|
| 28JLIHLS | figure_005 | 4 | yes | figure_006, figure_007 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| 3QYCST4E | figure_003 | 3 | yes | figure_002 | REAL_ASSOCIATION_FAILURE | high | remove Figure 2 claim, attach to Figure 3 |
| 55EKJRBC | figure_001 | 3 | yes | - | REAL_ASSOCIATION_FAILURE | high | fix new association |
| 66HTYNWM | figure_003 | 3 | yes | figure_002 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| 6GB9I9KG | figure_002 | 5 | yes | figure_004, figure_003 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| 8PLQZKGN | figure_005 | 9 | yes | - | REAL_ASSOCIATION_FAILURE | medium | fix new association |
| 8PLQZKGN | figure_007 | 12 | yes | - | REAL_ASSOCIATION_FAILURE | medium | fix new association |
| 9TW98JH8 | figure_001 | 2 | no | figure_003, figure_002 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| BAUEIRRM | figure_001 | 2 | no | figure_002 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| CAYP5AKS | figure_003 | 9 | no | - | REAL_ASSOCIATION_FAILURE | high | fix new association |
| EXNS5AG2 | figure_003 | 5 | yes | figure_004 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| F5CHZH3H | figure_044 | 37 | no | figure_038 | OLD_MISMATCH | medium | no action (old wrong) |
| FB48C9EL | figure_009 | 9 | no | figure_008 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| FC72S4K9 | figure_005 | 5 | no | figure_006, figure_004 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| FU5SNSPA | figure_006 | 6 | yes | figure_005 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| FX7PTWSK | figure_004 | 5 | no | figure_003 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| IKYZIAFS | figure_002 | 2 | yes | figure_003 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| J97KY85B | figure_001 | 2 | yes | figure_003 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| M8CNKCIZ | figure_006 | 4 | no | figure_005, figure_004 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| MZC482YI | figure_003 | 3 | no | figure_004 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| PJR7X5ZJ | figure_001 | 2 | yes | figure_002 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| S9UMIF83 | figure_003 | 2 | no | figure_001, figure_004, figure_002 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| TJHT3UBI | figure_010 | 12 | no | figure_009 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| VDQCYYIA | figure_001 | 4 | no | figure_003 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| WV2FF4NV | figure_010 | 15 | no | figure_009 | OLD_MISMATCH | medium | no action (old wrong) |
| XU3QKIPZ | figure_004 | 4 | no | figure_003 | OLD_MISMATCH | medium | no action (old wrong) |
| Y9NEE9D2 | figure_007 | 5 | no | figure_009, figure_008 | REAL_ASSOCIATION_FAILURE | high | fix new association |
| 388XI46Q | figure_005 | 15 | no | - | REAL_ASSOCIATION_FAILURE | medium | fix new association |
| 28ALPCY7 | figure_reserved_009 | 20 | no | figure_006 | IDENTITY_MAPPING | high | no action (control/identity) |
| 8CCATQE3 | figure_s001 | 3 | no | figure_main_p003_b7 | CAPTION_MISCLASSIFIED | high | fix caption classification |
| CYJLYG56 | figure_003_continued_p007_b12 | 7 | no | - | REAL_ASSOCIATION_FAILURE | high | fix new association |

## Evidence-backed vs hypothesis

- Evidence-backed: bbox overlaps, asset file existence, caption row role, and unmatched-asset entries come from the replay/vault artifacts.
- Hypothesis: final root-cause labels are review hypotheses until M2b matching changes are validated.

## Controls

- 388XI46Q: known Figure 5 remains unmatched (control).
- 28ALPCY7: assetless Figure 6 must remain unmatched (control).
