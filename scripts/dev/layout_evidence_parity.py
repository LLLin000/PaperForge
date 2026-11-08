"""R0: parity between the read-only evidence builder and the disk artifacts.

It answers one question: do the blocks the audits consume match what production
wrote to `structure/`? Read-only; the vault is opened but never written.

Usage:
    python scripts/dev/layout_evidence_parity.py \
        --vault D:/L/OB/Literature-hub/System/PaperForge/ocr \
        --keys 2332GHPT 2AGGSMVQ --out parity.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT, _REPO_ROOT / "scripts" / "dev"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

FIELDS = ("role", "role_candidate", "render_default", "index_default", "_object_owner_id", "zone")


def _key(block: dict) -> tuple:
    bbox = block.get("bbox") or []
    geometry = tuple(round(float(value), 1) for value in bbox[:4]) if len(bbox) >= 4 else None
    return (int(block.get("page", 0) or 0), str(block.get("block_id") or ""), geometry)


def _rows_by_key(rows: list[dict]) -> dict[tuple, list[dict]]:
    grouped: dict[tuple, list[dict]] = {}
    for row in rows:
        grouped.setdefault(_key(row), []).append(row)
    return grouped


def _figure_claims(inventory: dict) -> Counter:
    claims = Counter()
    for figure in inventory.get("matched_figures", []):
        assets = figure.get("matched_assets") or figure.get("assets") or []
        for asset in assets:
            claims[(str(figure.get("figure_id")), int(figure.get("page", 0) or 0), str(asset.get("block_id")))] += 1
    return claims


def _table_claims(inventory: dict) -> Counter:
    """Table claims the way the inventory actually stores them.

    Tables do not expose a `members` list; ownership is `asset_block_id` plus
    the per-page `segments`. Claiming from `members` reported zero differences
    for every paper, which is a coverage bug, not parity.
    """
    claims = Counter()
    for table in inventory.get("tables", []):
        key = str(table.get("table_id") or table.get("caption_block_id") or "")
        page = int(table.get("page", 0) or 0)
        asset_id = table.get("asset_block_id")
        if asset_id is not None:
            claims[(key, page, str(asset_id))] += 1
        for segment in table.get("segments", []) or []:
            segment_asset = segment.get("asset_block_id")
            if segment_asset is None:
                continue
            claims[(key, int(segment.get("page", page) or page), str(segment_asset))] += 1
    return claims


def parity_for(paper_dir: Path) -> dict[str, Any] | None:
    from layout_evidence import build_final_view

    raw_path = paper_dir / "canonical" / "blocks.raw.jsonl"
    disk_path = paper_dir / "structure" / "blocks.structured.jsonl"
    if not raw_path.is_file() or not disk_path.is_file():
        return None

    view = build_final_view(paper_dir)
    disk_rows = [json.loads(line) for line in disk_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    memory = _rows_by_key(view.blocks)
    disk = _rows_by_key(disk_rows)
    field_diffs: Counter = Counter()
    samples: list[dict] = []
    unmatched_memory = 0
    unmatched_disk = 0

    for key in set(memory) | set(disk):
        left = memory.get(key, [])
        right = disk.get(key, [])
        if len(left) != len(right):
            unmatched_memory += max(0, len(left) - len(right))
            unmatched_disk += max(0, len(right) - len(left))
        for a, b in zip(left, right, strict=False):
            for name in FIELDS:
                if a.get(name) != b.get(name):
                    field_diffs[name] += 1
                    if len(samples) < 8:
                        samples.append(
                            {
                                "page": key[0],
                                "block_id": key[1],
                                "field": name,
                                "memory": a.get(name),
                                "disk": b.get(name),
                            }
                        )

    memory_figures = _figure_claims(view.figure_inventory)
    disk_figures = _figure_claims(_load(paper_dir / "structure" / "figure_inventory.json"))
    memory_tables = _table_claims(view.table_inventory)
    disk_tables = _table_claims(_load(paper_dir / "structure" / "table_inventory.json"))

    return {
        "key": paper_dir.name,
        "rows": {"memory": len(view.blocks), "disk": len(disk_rows)},
        "identity": {"unmatched_memory": unmatched_memory, "unmatched_disk": unmatched_disk},
        "field_diffs": dict(sorted(field_diffs.items())),
        "samples": samples,
        "figure_claims": {"memory": sum(memory_figures.values()), "disk": sum(disk_figures.values()),
                          "only_memory": sum((memory_figures - disk_figures).values()),
                          "only_disk": sum((disk_figures - memory_figures).values())},
        "table_claims": {"memory": sum(memory_tables.values()), "disk": sum(disk_tables.values()),
                         "only_memory": sum((memory_tables - disk_tables).values()),
                         "only_disk": sum((disk_tables - memory_tables).values())},
        "trace": view.trace,
    }


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _markdown(reports: list[dict]) -> str:
    lines = [
        "| key | rows mem/disk | unmatched | role | render | index | owner | fig claims Δ | table claims Δ |",
        "|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    for report in reports:
        diffs = report["field_diffs"]
        figures = report["figure_claims"]
        tables = report["table_claims"]
        lines.append(
            f"| {report['key']} | {report['rows']['memory']}/{report['rows']['disk']} | "
            f"{report['identity']['unmatched_memory']}/{report['identity']['unmatched_disk']} | "
            f"{diffs.get('role', 0)} | {diffs.get('render_default', 0)} | {diffs.get('index_default', 0)} | "
            f"{diffs.get('_object_owner_id', 0)} | "
            f"{figures['only_memory']}/{figures['only_disk']} | {tables['only_memory']}/{tables['only_disk']} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--keys", nargs="*")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    keys = args.keys or sorted(path.name for path in args.vault.iterdir() if path.is_dir())
    if args.limit is not None:
        keys = keys[: max(0, args.limit)]
    reports = [report for key in keys if (report := parity_for(args.vault / key)) is not None]
    totals = {
        "papers": len(reports),
        "exact_match": sum(
            1
            for report in reports
            if not report["field_diffs"]
            and not report["identity"]["unmatched_memory"]
            and not report["identity"]["unmatched_disk"]
            and report["figure_claims"]["only_memory"] == 0
            and report["figure_claims"]["only_disk"] == 0
        ),
    }
    payload = {"papers": reports, "totals": totals}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(_markdown(reports))
    print(f"\n{totals}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
