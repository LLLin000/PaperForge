from __future__ import annotations

import copy
import json
from pathlib import Path

from paperforge.worker.ocr_tables import build_table_inventory_legacy, build_table_inventory_vnext


def _load_blocks(fixture_root: Path) -> list[dict]:
    # Check both fixture_root/structure/blocks.structured.jsonl and fixture_root/blocks.structured.jsonl
    candidate = fixture_root / "structure" / "blocks.structured.jsonl"
    if not candidate.exists():
        candidate = fixture_root / "blocks.structured.jsonl"
    return [json.loads(line) for line in candidate.read_text(encoding="utf-8").splitlines() if line.strip()]

def _normalize_table(table: dict) -> dict[str, object]:
    return {
        "caption_block_id": table.get("caption_block_id"),
        "page": table.get("page"),
        "formal_table_number": table.get("formal_table_number"),
        "asset_block_id": table.get("asset_block_id"),
        "match_status": table.get("match_status"),
        "note_block_ids": list(table.get("note_block_ids") or []),
        "bridge_block_ids": list(table.get("bridge_block_ids") or []),
        "consumed_block_ids": list(table.get("consumed_block_ids") or []),
        "render_rotation_deg": table.get("render_rotation_deg", 0),
    }


def compare_table_inventory_legacy_vs_vnext(fixture_root: Path) -> dict[str, object]:
    blocks = _load_blocks(fixture_root)
    legacy = build_table_inventory_legacy(copy.deepcopy(blocks))
    vnext = build_table_inventory_vnext(copy.deepcopy(blocks))
    legacy_norm = [_normalize_table(t) for t in legacy.get("tables", [])]
    vnext_norm = [_normalize_table(t) for t in vnext.get("tables", [])]
    return {
        "legacy": legacy_norm,
        "vnext": vnext_norm,
        "diff": {
            "legacy_only": [item for item in legacy_norm if item not in vnext_norm],
            "vnext_only": [item for item in vnext_norm if item not in legacy_norm],
        },
    }
