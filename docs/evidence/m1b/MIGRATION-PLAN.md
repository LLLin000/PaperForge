# M1b Migration Plan Preview

Generated from 952 paper plans.

## Commands
```
python scripts/dev/object_migration_dry_run.py --vault <vault> --keys <keys> --out report.json --plan-out plan.jsonl
python scripts/dev/object_migration_dry_run.py --bundle-plan plan.jsonl --bundle-out docs/evidence/m1b --external-refs
```

## Totals
{
  "papers": 952,
  "status_counts": {
    "READY": 785,
    "REQUIRES_APPROVAL": 99,
    "M2_REVIEW_REQUIRED": 28,
    "HOLD": 40
  },
  "op_counts": {
    "materialize_objects": 952,
    "keep": 27764,
    "retarget": 6484,
    "rewrite": 5466,
    "create": 23848,
    "rename": 416,
    "delete_candidate": 401
  },
  "holds_total": 249,
  "collisions_total": 27,
  "dangling_total": 0,
  "requires_approval_ops": 401,
  "m2_review_ops": 29,
  "hold_papers": 40,
  "backup_files": 6210,
  "safe_rename_ops": 416,
  "retarget_ops": 243,
  "retarget_unique_paths": 243,
  "retarget_occurrences": 244,
  "embed_mapped_noop_occurrences": 6249,
  "ambiguous_embed_holds": 31,
  "assetless_embed_deletes": 73,
  "delete_by_kind": {
    "figure": 214,
    "orphan": 108,
    "embed": 73,
    "table": 6
  },
  "delete_by_reason": {
    "unmapped_assetless": 36,
    "orphan no longer inventoried": 108,
    "reserved_or_assetless": 135,
    "old table has no new counterpart": 6,
    "superseded by several new objects; old file cannot be mapped 1:1": 47,
    "unmapped_table": 2,
    "many_to_one collision": 52,
    "identity_mapping_lost": 15
  },
  "top_hold_reasons": [
    [
      "RESERVED_OR_ASSETLESS",
      77
    ],
    [
      "MANY_TO_ONE",
      52
    ],
    [
      "AMBIGUOUS_OLD_ID",
      31
    ],
    [
      "AMBIGUOUS_EMBED",
      31
    ],
    [
      "UNMAPPED_ASSETLESS",
      29
    ],
    [
      "M2_REVIEW_REQUIRED",
      29
    ]
  ],
  "external_refs_count": 200,
  "external_refs_capped": true
}

## Status counts
{
  "READY": 785,
  "REQUIRES_APPROVAL": 99,
  "M2_REVIEW_REQUIRED": 28,
  "HOLD": 40
}

## Top HOLD reasons
[
  [
    "RESERVED_OR_ASSETLESS",
    77
  ],
  [
    "MANY_TO_ONE",
    52
  ],
  [
    "AMBIGUOUS_OLD_ID",
    31
  ],
  [
    "AMBIGUOUS_EMBED",
    31
  ],
  [
    "UNMAPPED_ASSETLESS",
    29
  ],
  [
    "M2_REVIEW_REQUIRED",
    29
  ]
]

## Sample plan snippet
```json
{
 "schema": "paperforge.migration_plan.v1",
 "key": "2332GHPT",
 "execution_model": "rebuild+verify: operations are expected artifact effects, not shell mv",
 "status": "READY",
 "objects": [
  {
   "kind": "figure",
   "old_id": "figure_001",
   "new_id": "figure_001",
   "candidates": [
    "figure_001"
   ],
   "entries": 1,
   "anchors": [
    {
     "page": 2,
     "legend_block_id": "3",
     "text": "Figure 1 Classification of Hamada Grade. (A) Grade 1, the acromiohumeral interval is 6 mm or more. (B) Grade 2, the acromiohumeral interval is less than 6 mm (C) Grade 3, the acromiohumeral interval is less than 6 mm with acetabulization of the acromion. (D) Grade 4A, narrowing of the glenohumeral joint without acetabulization of the acromion. (E) Grade 4B, narrowing of the glenohumeral joint with acetabulization of the acromion. (F) Grade 5, an instance of humeral head collapse.",
     "asset_blocks": [
      {
       "block_id": 2,
       "page": 2,
       "bbox": [
        210,
        133,
        979,
        643
       ]
      }
     ]
    }
   ],
   "old_files": [
    "assets/figures/figure_001.jpg",
    "render/figures/figure_001.md"
   ],
   "status": "planned"
  },
  {
   "kind": "figure",
   "old_id": "figure_002",
   "new_id": "figure_002",
   "candidates": [
    "figure_002"
   ],
   "entries": 1,
   "anchors": [
    {
     "page": 3,
     "legend_block_id": "3",
     "text": "Figure 2 Flowchart of patient inclusion. RCTs, rotator cuff tears.",
     "asset_blocks": [
      {
       "block_id": 2,
       "page": 3,
       "bbox": [
        209,
        131,
        980,
        574
       ]
      }
     ]
    }
   ],
   "old_files": [
    "assets/figures/figure_002.jpg",
    "render/figures/figure_002.md"
   ],
   "status": "planned"
  }
 ],
 "operations": [
  {
   "op": "materialize_objects",
   "kind": "paper",
   "object_uid": "",
   "old_path": "",
   "new_path": "",
   "old_sha256": "",
   "status": "planned",
   "reason": "rebuild writes objects before inventory/fulltext",
   "depends_on": [],
   "op_id": "materialize-objects"
  },
  {
   "op": "keep",
   "kind": "figure",
   "object_uid": "figure_001",
   "old_id": "figure_001",
   "old_path": "assets/figures/figure_001.jpg",
   "new_path": "assets/figures/figure_001.jpg",
   "old_sha256": "bcbce1ad60d76fafb4933edf795088df6c1b55c0cd309c61339180a9767bc2e3",
   "status": "planned",
   "reason": "identity mapping"
  },
  {
   "op": "keep",
   "kind": "figure",
   "object_uid": "figure_001",
   "old_id": "figure_001",
   "old_path": "render/figures/figure_001.md",
   "new_path": "render/figures/figure_001.md",
   "old_sha256": "f0586a93470e9c6ff549d4db05b90cea693b1449b497be00d23a4617a55530c9",
   "status": "planned",
   "reason": "identity mapping"
  },
  {
   "op": "keep",
   "kind": "figure",
   "object_uid": "figure_002",
   "old_id": "figure_002",
   "old_path": "assets/figures/figure_002.jpg",
   "new_path": "assets/figures/figure_002.jpg",
   "old_sha256": "d089e66da000eaa963bd40d75b947e370f516e976ea1677e2830f9913cdfda45",
   "status": "planned",
   "reason": "identity mapping"
  },
  {
   "op": "keep",
   "kind": "figure",
   "object_uid": "figure_002",
   "old_id": "figure_002",
   "old_path": "render/figures/figure_002.md",
   "new_path": "render/figures/figure_002.md",
   "old_sha256": "3d35f57b4c2bc25993a4ac85938330dbf16776c6694c550e5e8bcaba96b211ed",
   "status": "planned",
   "reason": "identity mapping"
  },
  {
   "op": "keep",
   "kind": "table",
   "object_uid": "table_001",
   "old_id": "table_001",
   "old_path": "assets/tables/table_001.jpg",
   "new_path": "assets/tables/table_001.jpg",
   "old_sha256": "28f2ba8b8603c9bff9dbd688753c76c0a4de28b306f9cbbcbfe6f5a0d8f0d5b5",
   "status": "planned",
   "reason": "table identity mapping"
  },
  {
   "op": "keep",
   "kind": "table",
   "object_uid": "table_001",
   "old_id": "table_001",
   "old_path": "render/tables/table_001.md",
   "new_path": "render/tables/table_001.md",
   "old_sha256": "
```

## Limits
- Table id pairing is by order when anchors do not match.
- 42 assetless/legacy removals are REQUIRES_APPROVAL, not confirmed misses.
- 27 caption_present_unmatched cases are M2_REVIEW_REQUIRED, not confirmed misses.
- Filesystem and SQLite effects are not atomic; restore+verify rollback.
