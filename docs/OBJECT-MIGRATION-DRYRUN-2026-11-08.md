# Figure/Table migration dry-run (M1)

Status: gate evidence before any production rebuild. The OCR vault is read-only;
the trial rebuilds selected papers in a throwaway vault.

## Method

```
python scripts/dev/object_migration_dry_run.py --vault <vault> [--keys ...] --out report.json
python scripts/dev/object_migration_dry_run.py --vault <vault> --keys A B C --trial --workdir <tmp>
```

Each paper is compared as: identity (ids/duplicates/anchors), association
(figure/table claims), delivery (managed crops/markdown/embeds), content
(role counters, body and total text), and unmapped-embed reasons.

## Isolated trial (M0 on real rebuilds)

`2BYRLKQS`, `2AZ2EGQB`, `388XI46Q`: rebuild twice in a temp vault.

| Check | Result |
|---|---|
| First/second status | ok / ok on all 3 |
| Committed artifacts idempotent | 3/3 (structure, inventories, markdown, crops) |
| Staging/journal leftovers | none |
| `.tmp` outliers | none |

## Gold-case diff (7 papers)

| Key | Identity | Delivery |
|---|---|---|
| SRNJDAA2 | 25 entries / 1 unique id → 21 / 21 | 1 old embed retargeted |
| DJLIAZT7 | 63 / 6 → 48 / 48 | 63 embeds retargeted |
| 2AZ2EGQB | 2 → 4 figures (side-by-side) | 2 new figure files |
| 2BYRLKQS | 4 → 4 | unchanged |
| 388XI46Q | 11 → 10 | Figure 5 still unmatched (known) |
| 28ALPCY7 | 10 / 9 → 9 / 9 | assetless Figure 6 stays unmatched |
| 2HEUD5P9 | 7 → 7 | 0 retargets |

## 86 affected papers (after anchor/id/number/caption mapping fallbacks)

| Metric | Result |
|---|---:|
| Papers / errors | 86 / 0 |
| Renamed ids | 74 |
| Claim changes | 68 |
| Embeds retargeted | 121 |
| Unmapped embeds | 69 |
| ... `reserved_or_assetless` (old assetless reserved figures) | 42 |
| ... `caption_present_unmatched` (real association gaps, M2 input) | 27 |

`caption_present_unmatched` examples: `28JLIHLS` figure_005, `3QYCST4E`
figure_003, `55EKJRBC` figure_001, `8PLQZKGN` figure_005/007. These need M2
review before migration; they are not identity-mapping failures.

## Full-corpus run (952 papers, fresh process per 119-paper batch)

| Metric | Result |
|---|---:|
| Papers / errors | 952 / 0 |
| Duplicate figure-id extras | 355 (historical) → **0** |
| Renamed ids | 433 |
| Claim changes | 264 |
| Embeds retargeted | 399 |
| Unmapped embeds | 69 |
| ... `reserved_or_assetless` | 42 |
| ... `caption_present_unmatched` | 27 |
| Papers whose total structured text decreased | **0** |
| Papers whose total structured text increased | 26 |

The 42 `reserved_or_assetless` embeds are old links to assetless reserved
figures; the contract does not deliver those objects, so their removal is
expected. The 27 `caption_present_unmatched` cases are real association gaps
(M2 input), e.g. `28JLIHLS` figure_005, `3QYCST4E` figure_003, `55EKJRBC`
figure_001.

Role deltas (net): `backmatter_body` -1,371, `figure_caption_candidate` -1,287,
`unknown_structural` -882, `structured_insert` -358; body/heading/reference
roles gain correspondingly. Total text is preserved or increased, so these are
classification changes, not content loss.

## Notes / limits

- The historical snapshot was written by older code; role and body deltas partly
  reflect code-version differences (e.g. old `structured_insert` blocks becoming
  body text, old body references becoming `reference_item`), not necessarily
  data loss. Use the total-text delta and the embed classification for triage.
- Replaying all 952 papers in one process can hit MemoryError on very large
  papers (`WML2NNFE`); the final run used fresh processes per 119-paper batch and
  finished with 0 errors. This is a replay-tooling limit, not a pipeline failure.
- No production vault was modified.
