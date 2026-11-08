# M1c Post-M2b Migration Preview

Read-only dry run. 952 papers, 0 replay errors, no writes under vault.

## (a) M1 report metrics M1b vs M1c
| metric | M1b | M1c |
|---|---:|---:|
| papers | 952 | 952 |
| errors | 0 | 0 |
| duplicate_extra (old) | 355 | 355 |
| duplicate_extra (new) | 0 | 0 |
| renamed_ids | 433 | 434 |
| claims_changed | 264 | 223 |
| embeds_retargeted | 399 | 381 |
| embeds_missing | 69 | 51 |
| text decrease count | 0 | 0 |

Embed missing reasons M1c: reserved_or_assetless 42, caption_present_unmatched 9.

## (b) Plan metrics M1b vs M1c
| metric | M1b | M1c |
|---|---:|---:|
| READY | 785 | 803 |
| REQUIRES_APPROVAL | 99 | 98 |
| M2_REVIEW_REQUIRED | 28 | 10 |
| HOLD | 40 | 41 |
| rename ops | 416 | 417 |
| retarget unique paths | 243 | 243 |
| retarget occurrences | 244 | 244 |
| embed no-op occurrences | 6249 | 6267 |
| delete_candidate | 401 | 400 |

## M2 review (10 papers, 11 holds)
28JLIHLS, 55EKJRBC, 8CCATQE3, 8PLQZKGN, 9TW98JH8, CAYP5AKS, CYJLYG56, F5CHZH3H, WV2FF4NV, XU3QKIPZ.
Residual M2 cases are HOLD/M2; 16 M2b-fixed cases now have correct owners.

## Migration safety
- Migration-safe (READY): 803 papers.
- Need approval: 98 papers.
- HOLD/M2: 51 papers.
- No production writes. Total text decrease count 0.

See papers.json for per-key status.
