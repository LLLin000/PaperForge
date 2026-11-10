# P1 parity evidence

Rebuild-based plan mode; 10 representative papers.

Plan mismatch count (two independent rebuilds): 0

## Per-paper

| key | new figure IDs | plan ops | old/new text chars | table claim changes |
|---|---|---|---|---|
| 3QYCST4E | {'entries': 6, 'unique_ids': 6, 'duplicate_extra': 0} | 38 | 18278 -> 18278 | 0 |
| 28JLIHLS | {'entries': 7, 'unique_ids': 7, 'duplicate_extra': 0} | 50 | 46970 -> 46970 | 1 |
| 6A8A9TWD | {'entries': 4, 'unique_ids': 4, 'duplicate_extra': 0} | 37 | 37085 -> 37085 | 0 |
| 23T2B8ZX | {'entries': 2, 'unique_ids': 2, 'duplicate_extra': 0} | 31 | 32542 -> 32542 | 0 |
| 24YKLTHQ | {'entries': 6, 'unique_ids': 6, 'duplicate_extra': 0} | 68 | 45517 -> 45517 | 0 |
| 4KMPSDBU | {'entries': 8, 'unique_ids': 8, 'duplicate_extra': 0} | 51 | 84158 -> 84158 | 0 |
| 49NUE2G7 | {'entries': 6, 'unique_ids': 6, 'duplicate_extra': 0} | 41 | 57013 -> 57013 | 0 |
| 53B47JM8 | {'entries': 5, 'unique_ids': 5, 'duplicate_extra': 0} | 103 | 68369 -> 68369 | 0 |
| 64AWS4SU | {'entries': 6, 'unique_ids': 6, 'duplicate_extra': 0} | 46 | 33020 -> 33020 | 1 |
| G5QGQ9PB | {'entries': 5, 'unique_ids': 5, 'duplicate_extra': 0} | 58 | 45040 -> 45040 | 1 |

## Exact rebuild command

```bash\python scripts/dev/object_migration_dry_run.py --plan --replay-mode rebuild --keys ...
```

Programmatic: `m.audit_key(vault, ocr_root, key, plan=True, replay_mode='rebuild')` using `paperforge.worker.ocr_rebuild._rebuild_one_paper`.
