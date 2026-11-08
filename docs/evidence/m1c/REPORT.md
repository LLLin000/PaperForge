# M1c Post-M2b Migration Preview

Read-only dry run. 952 papers, 0 replay errors, no writes under vault.

## M1c vs M1b totals
| metric | M1b | M1c | delta |
|---|---:|---:|---:|
| papers | 952 | 952 | 0 |
| errors | 0 | 0 | 0 |
| status READY | 785 | 803 | 18 |
| status REQUIRES_APPROVAL | 99 | 98 | -1 |
| status M2_REVIEW_REQUIRED | 28 | 10 | -18 |
| status HOLD | 40 | 41 | 1 |
| renamed IDs | 433 | 417 | 1 |
| claims changed | 264 | n/a | - |
| safe retarget unique paths | 243 | 243 | 0 |
| retarget occurrences | 244 | 244 | 0 |
| embed no-op occurrences | 6249 | 6267 | 18 |

## Plan status
- READY: 803
- REQUIRES_APPROVAL: 98
- M2_REVIEW_REQUIRED: 10
- HOLD: 41

## Delete breakdown
{
  "figure": 213,
  "orphan": 108,
  "embed": 73,
  "table": 6
}
{
  "unmapped_assetless": 35,
  "orphan no longer inventoried": 108,
  "reserved_or_assetless": 135,
  "old table has no new counterpart": 6,
  "superseded by several new objects; old file cannot be mapped 1:1": 47,
  "unmapped_table": 2,
  "many_to_one collision": 52,
  "identity_mapping_lost": 15
}

## M2 review
29 holds across 28 papers (includes 8CCATQE3 figure_s001 and CYJLYG56 figure_003_continued_p007_b12; 8PLQZKGN has two cases). Residual M2 cases are HOLD.

## Migration safety
- Migration-safe (READY): 803 papers.
- Need approval: 98 papers.
- Need HOLD/M2 review: 51 papers.
- No production writes performed.
