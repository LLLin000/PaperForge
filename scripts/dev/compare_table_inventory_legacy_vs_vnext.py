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


def _str_id(val: object) -> str | None:
    """Normalize a block ID to str, or None if empty/missing."""
    if val is None or val == "":
        return None
    return str(val)


def _str_ids_sorted(vals: list) -> list[str]:
    """Normalize block ID list to sorted strings, dropping None/empty entries."""
    return sorted(str(v) for v in (vals or []) if v is not None and v != "")


def _normalize_table(table: dict) -> dict[str, object]:
    """Normalize a table inventory entry so legacy and vnext results are comparable.

    Benign drift handled:
    - block IDs stored as int vs str -> normalized to str
    - ``asset_block_id`` stored as ``""`` (legacy) vs ``None`` (vnext) -> both become None
    - ordering of list fields -> sorted
    """
    asset_id = _str_id(table.get("asset_block_id"))
    return {
        "caption_block_id": _str_id(table.get("caption_block_id")),
        "page": table.get("page"),
        "formal_table_number": table.get("formal_table_number"),
        "asset_block_id": asset_id,  # None if empty in either pipeline
        "match_status": table.get("match_status"),
        "note_block_ids": _str_ids_sorted(table.get("note_block_ids", [])),
        "bridge_block_ids": _str_ids_sorted(table.get("bridge_block_ids", [])),
        "consumed_block_ids": _str_ids_sorted(table.get("consumed_block_ids", [])),
        "render_rotation_deg": table.get("render_rotation_deg", 0),
    }


def _table_sort_key(t: dict) -> tuple:
    return (t.get("page") or 0, t.get("formal_table_number") or 0)


def compare_table_inventory_legacy_vs_vnext(fixture_root: Path) -> dict[str, object]:
    blocks = _load_blocks(fixture_root)
    legacy = build_table_inventory_legacy(copy.deepcopy(blocks))
    vnext = build_table_inventory_vnext(copy.deepcopy(blocks))
    legacy_norm = [_normalize_table(t) for t in legacy.get("tables", [])]
    vnext_norm = [_normalize_table(t) for t in vnext.get("tables", [])]
    # Sort deterministically so ordering drift does not cause false diffs.
    legacy_norm.sort(key=_table_sort_key)
    vnext_norm.sort(key=_table_sort_key)
    return {
        "legacy_raw": legacy,
        "vnext_raw": vnext,
        "legacy": legacy_norm,
        "vnext": vnext_norm,
        "diff": {
            "legacy_only": [item for item in legacy_norm if item not in vnext_norm],
            "vnext_only": [item for item in vnext_norm if item not in legacy_norm],
        },
    }
