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


def compare_inventories(legacy: dict[str, object], vnext: dict[str, object]) -> dict[str, object]:
    return {
        "legacy_matched_count": len(legacy.get("matched_figures", [])),
        "vnext_matched_count": len(vnext.get("matched_figures", [])),
        "legacy_unresolved_count": len(legacy.get("unresolved_clusters", [])),
        "vnext_unresolved_count": len(vnext.get("unresolved_clusters", [])),
        "legacy_unmatched_legend_count": len(legacy.get("unmatched_legends", [])),
        "vnext_unmatched_legend_count": len(vnext.get("unmatched_legends", [])),
        "legacy_consumed_block_ids": sorted(
            {bid for fig in legacy.get("matched_figures", []) for bid in _figure_asset_ids(fig)}
        ),
        "vnext_consumed_block_ids": sorted(
            {bid for fig in vnext.get("matched_figures", []) for bid in _figure_asset_ids(fig)}
        ),
    }

def compare_blocks_file(blocks_path: Path) -> dict[str, object]:
    blocks = [json.loads(line) for line in blocks_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    legacy = build_figure_inventory_legacy(blocks)
    vnext = build_figure_inventory_vnext(blocks)
    diff = compare_inventories(legacy, vnext)
    diff["paper"] = blocks_path.parent.name
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
