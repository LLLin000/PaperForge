"""Stratify the figure/caption pairs the layout plan marks as suspicious.

Read-only. It does not re-match figures or change ownership: it takes the pairs
`evaluate_plan` already flags (same region, caption and asset more than 2% of
the page height apart) and groups them so a human can sample the worst ones.

Usage:
    python scripts/dev/layout_figcaption_audit.py \
        --report layout-plan.json --out figcap.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

BUCKETS = ("2-5%", "5-15%", ">15%")


def bucket(distance_ratio: float) -> str:
    if distance_ratio <= 0.05:
        return "2-5%"
    if distance_ratio <= 0.15:
        return "5-15%"
    return ">15%"


def crop_box(caption_bbox: list[float], asset_bbox: list[float], page_width: float, page_height: float) -> list[float]:
    pad_x, pad_y = page_width * 0.02, page_height * 0.02
    return [
        max(0.0, min(caption_bbox[0], asset_bbox[0]) - pad_x),
        max(0.0, min(caption_bbox[1], asset_bbox[1]) - pad_y),
        min(page_width, max(caption_bbox[2], asset_bbox[2]) + pad_x),
        min(page_height, max(caption_bbox[3], asset_bbox[3]) + pad_y),
    ]


def stratify(report: dict[str, Any]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for paper in report.get("papers", []):
        for page in paper["plan"]["pages"]:
            height = page["height"] or 1.0
            width = page["width"] or 1.0
            caption_region: dict[str, dict] = {}
            bbox_by_uid: dict[str, list[float]] = {}
            for region in page["regions"]:
                for uid in region["members"]:
                    caption_region.setdefault(uid, region)
            metrics = paper["metrics"].get("figure_caption")
            if not metrics:
                continue
            for pair in metrics.get("suspicious", []):
                # `metrics` is per paper; the plan page decides where it belongs.
                if int(pair.get("page", 0) or 0) != int(page["page"]):
                    continue
                caption, asset = pair["caption"], pair["asset"]
                caption_box = pair.get("caption_bbox") or bbox_by_uid.get(caption)
                asset_box = pair.get("asset_bbox") or bbox_by_uid.get(asset)
                if not caption_box or not asset_box:
                    continue
                ratio = pair.get("distance_ratio")
                if ratio is None:
                    cap_y = (caption_box[1] + caption_box[3]) / 2
                    asset_y = (asset_box[1] + asset_box[3]) / 2
                    ratio = abs(cap_y - asset_y) / height
                region = caption_region.get(caption, {})
                entries.append(
                    {
                        "key": paper["key"],
                        "page": page["page"],
                        "caption": caption,
                        "asset": asset,
                        "caption_bbox": caption_box,
                        "asset_bbox": asset_box,
                        "distance_ratio": round(float(ratio), 4),
                        "bucket": bucket(float(ratio)),
                        "region_kind": region.get("kind"),
                        "crop": crop_box(caption_box, asset_box, width, height),
                    }
                )
    counts = {name: sum(1 for entry in entries if entry["bucket"] == name) for name in BUCKETS}
    entries.sort(key=lambda entry: -entry["distance_ratio"])
    return {"total": len(entries), "buckets": counts, "entries": entries}


def _markdown(result: dict[str, Any], top: int = 10) -> str:
    lines = [
        "| bucket | count |",
        "|---|---:|",
        *[f"| {name} | {count} |" for name, count in result["buckets"].items()],
        "",
        "| key | page | distance | bucket | caption → asset |",
        "|---|---:|---:|---|---|",
    ]
    for entry in result["entries"][:top]:
        lines.append(
            f"| {entry['key']} | {entry['page']} | {entry['distance_ratio']:.3f} | "
            f"{entry['bucket']} | {entry['caption']} → {entry['asset']} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path, help="JSON from layout_plan_report.py")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    report = json.loads(args.report.read_text(encoding="utf-8"))
    result = stratify(report)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
