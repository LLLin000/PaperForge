from __future__ import annotations

import json
from pathlib import Path

from paperforge.worker.ocr_figures import (
    build_figure_inventory_legacy,
    build_figure_inventory_vnext,
)


def _figure_asset_ids(fig: dict[str, object]) -> list[str]:
    ids = {str(x) for x in fig.get("asset_block_ids", [])}
    ids.update(str(asset.get("block_id", "")) for asset in fig.get("matched_assets", []))
    return sorted(x for x in ids if x)


def _settlement_type_counts(figures: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for fig in figures:
        st = str(fig.get("settlement_type", ""))
        if st:
            counts[st] = counts.get(st, 0) + 1
    return counts


def compare_inventories(legacy: dict[str, object], vnext: dict[str, object]) -> dict[str, object]:
    _legacy_figure_ids = sorted(
        str(f.get("figure_id", "")) for f in legacy.get("matched_figures", []) if f.get("figure_id")
    )
    _vnext_figure_ids = sorted(
        str(f.get("figure_id", "")) for f in vnext.get("matched_figures", []) if f.get("figure_id")
    )
    _legacy_consumed = sorted(
        {bid for fig in legacy.get("matched_figures", []) for bid in _figure_asset_ids(fig)}
    )
    _vnext_consumed = sorted(
        {bid for fig in vnext.get("matched_figures", []) for bid in _figure_asset_ids(fig)}
    )
    return {
        "legacy_matched_count": len(legacy.get("matched_figures", [])),
        "vnext_matched_count": len(vnext.get("matched_figures", [])),
        "legacy_unresolved_count": len(legacy.get("unresolved_clusters", [])),
        "vnext_unresolved_count": len(vnext.get("unresolved_clusters", [])),
        "legacy_unmatched_legend_count": len(legacy.get("unmatched_legends", [])),
        "vnext_unmatched_legend_count": len(vnext.get("unmatched_legends", [])),
        "legacy_consumed_block_ids": sorted(_legacy_consumed),
        "vnext_consumed_block_ids": sorted(_vnext_consumed),
        # New gate fields
        "legacy_completeness": legacy.get("figure_legend_completeness", {}),
        "vnext_completeness": vnext.get("completeness", {}),
        "legacy_figure_ids": _legacy_figure_ids,
        "vnext_figure_ids": _vnext_figure_ids,
        "vnext_pass_names": [str(r.get("pass_name", "")) for r in vnext.get("pass_reports", [])],
        "legacy_settlement_types": _settlement_type_counts(legacy.get("matched_figures", [])),
        "vnext_settlement_types": _settlement_type_counts(vnext.get("matched_figures", [])),
        "consumed_ids_only_in_legacy": sorted(set(_legacy_consumed) - set(_vnext_consumed)),
        "consumed_ids_only_in_vnext": sorted(set(_vnext_consumed) - set(_legacy_consumed)),
    }

def _roles_for_ids(ids: list[str], blocks: list[dict]) -> dict[str, int]:
    """Count roles for a set of block IDs."""
    lookup = {str(b.get("block_id")): b.get("role", "?") for b in blocks}
    counts: dict[str, int] = {}
    for bid in ids:
        role = lookup.get(bid, "NOT_FOUND")
        counts[role] = counts.get(role, 0) + 1
    return counts



def compare_blocks_file(blocks_path: Path) -> dict[str, object]:
    blocks = [json.loads(line) for line in blocks_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    legacy = build_figure_inventory_legacy(blocks)
    vnext = build_figure_inventory_vnext(blocks)
    diff = compare_inventories(legacy, vnext)
    diff["paper"] = blocks_path.parent.name
    diff["lost_block_roles"] = _roles_for_ids(diff.get("consumed_ids_only_in_legacy", []), blocks)
    diff["gained_block_roles"] = _roles_for_ids(diff.get("consumed_ids_only_in_vnext", []), blocks)
    return diff


def main(blocks_path: str) -> int:
    blocks = [json.loads(line) for line in Path(blocks_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    legacy = build_figure_inventory_legacy(blocks)
    vnext = build_figure_inventory_vnext(blocks)
    print(json.dumps(compare_inventories(legacy, vnext), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1]))
