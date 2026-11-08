"""Read-only audit that classifies unmatched OCR assets; never writes to the vault."""
from __future__ import annotations

import argparse
import contextlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

CLASSES = ("panel_sub_asset", "duplicate_asset", "decoration", "true_unmatched_figure", "undetermined")
CAPTION = re.compile(r"\b(?:figure|fig\.?|table|plate)\s*\d+", re.IGNORECASE)


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return {}


def _bbox(item: Any) -> tuple[float, float, float, float] | None:
    raw = item.get("bbox") if isinstance(item, dict) else None
    try:
        if len(raw) != 4:
            return None
        x0, y0, x1, y1 = map(float, raw)
        return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    except (TypeError, ValueError):
        return None


def _page(item: dict[str, Any]) -> int | str | None:
    return item.get("page", item.get("page_number"))


def _same_bbox(a: Any, b: Any) -> bool:
    ba, bb = _bbox(a), _bbox(b)
    return ba is not None and bb is not None and all(
        abs(x - y) <= 1 for x, y in zip(ba, bb, strict=False)
    )


def _contains_or_adjacent(asset: Any, cluster: Any, page_w: float, page_h: float) -> bool:
    a, c = _bbox(asset), _bbox(cluster)
    if a is None or c is None:
        return False
    dx, dy = page_w * .02, page_h * .02
    return a[0] >= c[0] - dx and a[1] >= c[1] - dy and a[2] <= c[2] + dx and a[3] <= c[3] + dy


def _dimensions(
    inventory: dict[str, Any],
    assets: list[dict[str, Any]],
    blocks: list[dict[str, Any]],
) -> dict[Any, tuple[float, float]]:
    dims: dict[Any, tuple[float, float]] = {}
    for source in (inventory.get("page_dimensions_by_page"), inventory.get("page_dimensions")):
        if isinstance(source, dict):
            for page, value in source.items():
                if isinstance(value, dict):
                    w, h = value.get("width"), value.get("height")
                elif isinstance(value, (list, tuple)) and len(value) >= 2:
                    w, h = value[0], value[1]
                else:
                    continue
                with contextlib.suppress(ValueError, TypeError):
                    dims[int(page)] = (float(w), float(h))
    for item in [*assets, *blocks]:
        page = _page(item)
        if page is None or page in dims:
            continue
        w = item.get("page_width", item.get("page_w"))
        h = item.get("page_height", item.get("page_h"))
        try:
            if w and h:
                dims[int(page)] = (float(w), float(h))
        except (ValueError, TypeError):
            pass
    for page in {_page(x) for x in [*assets, *blocks]} - dims.keys():
        coords = [_bbox(x) for x in [*assets, *blocks] if _page(x) == page and _bbox(x)]
        if coords:
            dims[page] = (max(b[2] for b in coords), max(b[3] for b in coords))
    return dims


def classify_assets(inventory: dict[str, Any], blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assets = [a for a in inventory.get("unmatched_assets", []) if isinstance(a, dict)]
    dims = _dimensions(inventory, assets, blocks)
    clusters: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    for fig in inventory.get("matched_figures", []) or []:
        if not isinstance(fig, dict):
            continue
        figure_box = _bbox(fig)
        matched = [a for a in fig.get("matched_assets", []) or [] if isinstance(a, dict) and _bbox(a)]
        if figure_box:
            clusters.append({**fig, "bbox": figure_box})
        elif matched:
            boxes = [_bbox(a) for a in matched]
            clusters.append({
                "page": fig.get("page", matched[0].get("page")),
                "bbox": [min(b[0] for b in boxes), min(b[1] for b in boxes),
                         max(b[2] for b in boxes), max(b[3] for b in boxes)],
            })
        for a in fig.get("matched_assets", []) or []:
            if isinstance(a, dict):
                claims.append({**a, "page": a.get("page", fig.get("page"))})
        for box in fig.get("asset_bboxes", []) or []:
            if isinstance(box, (list, tuple)):
                claims.append({"page": fig.get("page"), "bbox": box})
    repeat_pages: dict[tuple[Any, ...], set[Any]] = defaultdict(set)
    for a in assets:
        box = _bbox(a)
        if box:
            repeat_pages[(round(box[2]-box[0]), round(box[3]-box[1]), *(round(x) for x in box))].add(_page(a))
    repeated = {key for key, pages in repeat_pages.items() if len(pages) >= 3}
    results = []
    for asset in assets:
        page = _page(asset)
        w, h = dims.get(page, (0.0, 0.0))
        box = _bbox(asset)
        label = "undetermined"
        if any(_page(c) == page and _contains_or_adjacent(asset, c, w, h) for c in clusters):
            label = "panel_sub_asset"
        elif any(_page(c) == page and _same_bbox(asset, c) for c in claims):
            label = "duplicate_asset"
        elif box and w > 0 and h > 0:
            area = max(0.0, box[2]-box[0]) * max(0.0, box[3]-box[1])
            centre_y = (box[1]+box[3])/2
            repeat_key = (round(box[2]-box[0]), round(box[3]-box[1]), *(round(x) for x in box))
            if area < .01*w*h or centre_y <= .05*h or centre_y >= .95*h or repeat_key in repeated:
                label = "decoration"
            elif area >= .02*w*h:
                overlaps = any(_page(c) == page and _overlap(box, _bbox(c)) for c in clusters)
                has_caption = any(_page(b) == page and _caption_near(box, b, h) for b in blocks)
                if not overlaps and not has_caption:
                    label = "true_unmatched_figure"
        results.append(
            {
                "block_id": asset.get("block_id"),
                "page": page,
                "bbox": asset.get("bbox"),
                "classification": label,
            }
        )
    return results


def _overlap(a: tuple[float, ...], b: tuple[float, ...] | None) -> bool:
    return bool(b and a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1])


def _caption_near(asset: tuple[float, ...], block: dict[str, Any], page_h: float) -> bool:
    box = _bbox(block)
    if box is None or not CAPTION.search(str(block.get("text", ""))):
        return False
    return abs((box[1]+box[3])/2 - (asset[1]+asset[3])/2) <= .15*page_h


def _blocks(path: Path) -> list[dict[str, Any]]:
    try:
        return [obj for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and isinstance((obj := json.loads(line)), dict)]
    except (OSError, UnicodeError, ValueError):
        return []


FIGURE_EMBED = re.compile(r"!\[\[render/figures/([^]\|]+)\.md(?:\|[^\]]*)?\]\]")


def _delivery(paper_dir: Path) -> dict[str, Any]:
    inv = _json(paper_dir / "structure/figure_inventory.json")
    rows = inv.get("matched_figures", []) if isinstance(inv, dict) else []
    rows = [row for row in rows if isinstance(row, dict) and row.get("figure_id")]
    try:
        fulltext = (paper_dir / "fulltext.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        fulltext = ""
    embedded = {match.group(1) for match in FIGURE_EMBED.finditer(fulltext)}
    unique_rows: dict[str, dict[str, Any]] = {}
    for row in rows:
        unique_rows.setdefault(str(row["figure_id"]), row)
    without_embed = [key for key in unique_rows if key not in embedded]
    table_claims: set[tuple[Any, str]] = set()
    table_inventory = _json(paper_dir / "structure/table_inventory.json")
    for table in table_inventory.get("tables", []) if isinstance(table_inventory, dict) else []:
        if not isinstance(table, dict):
            continue
        for field in ("asset_block_id", "caption_block_id"):
            if table.get(field) is not None:
                table_claims.add((table.get("page"), str(table[field])))
        for field in ("asset_block_ids", "consumed_block_ids", "note_block_ids"):
            table_claims.update((table.get("page"), str(block_id))
                                for block_id in table.get(field, []) or [] if block_id is not None)
        for segment in table.get("segments", []) or []:
            if isinstance(segment, dict) and segment.get("asset_block_id") is not None:
                table_claims.add((segment.get("page", table.get("page")), str(segment["asset_block_id"])))
    undelivered = []
    for figure_id in without_embed:
        row = unique_rows[figure_id]
        assets = row.get("matched_assets") or []
        claims = [
            {"page": asset.get("page", row.get("page")), "block_id": str(asset["block_id"])}
            for asset in assets if isinstance(asset, dict) and asset.get("block_id") is not None
        ]
        if not claims:
            claims = [{"page": row.get("page"), "block_id": str(block_id)}
                      for block_id in row.get("asset_block_ids") or []]
        overlap = [claim for claim in claims if (claim["page"], claim["block_id"]) in table_claims]
        intentional = bool(claims) and len(overlap) == len(claims)
        if row.get("matched_assets") or row.get("asset_block_ids"):
            undelivered.append({
                "figure_id": figure_id, "page": row.get("page"),
                "asset_count": len(assets) if assets else len(row.get("asset_block_ids") or []),
                "reconciliation_type": "missing_embed_for_asset_object",
                "intentional_non_delivery": intentional,
                "table_claim_overlap": overlap,
            })
    render_dir = paper_dir / "render" / "figures"
    markdown = [path.stem for path in render_dir.glob("*.md")] if render_dir.is_dir() else []
    canonical_md = [stem for stem in markdown if not stem.startswith("orphan_")]
    stale = [stem for stem in canonical_md
             if stem not in unique_rows and not stem.startswith("unresolved_cluster_")]
    never_embedded = [stem for stem in canonical_md if stem not in embedded]
    return {
        "inventory_ids_without_embed": len(without_embed),
        "asset_bearing_without_embed": len(undelivered),
        "intentional_non_delivery": sum(item["intentional_non_delivery"] for item in undelivered),
        "canonical_md_never_embedded": len(never_embedded),
        "stale_canonical_md": len(stale),
        "asset_bearing_undelivered": undelivered,
    }


def audit_paper(paper_dir: Path) -> dict[str, Any]:
    inv = _json(paper_dir / "structure/figure_inventory.json")
    classes = classify_assets(
        inv if isinstance(inv, dict) else {},
        _blocks(paper_dir / "structure/blocks.structured.jsonl"),
    )
    counts = Counter(item["classification"] for item in classes)
    return {"paper": paper_dir.name, "assets": classes, "delivery": _delivery(paper_dir),
            "totals": {name: counts.get(name, 0) for name in CLASSES}}


def audit_corpus(ocr_root: Path, keys: list[str] | None = None, limit: int | None = None) -> dict[str, Any]:
    root = Path(ocr_root)
    if keys:
        selected = [root / key for key in keys]
    elif root.is_dir():
        selected = sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name)
    else:
        selected = []
    if limit is not None:
        selected = selected[:max(0, limit)]
    papers = [audit_paper(path) for path in selected]
    totals = {name: sum(p["totals"][name] for p in papers) for name in CLASSES}
    delivery_keys = ("inventory_ids_without_embed", "asset_bearing_without_embed",
                     "intentional_non_delivery", "canonical_md_never_embedded", "stale_canonical_md")
    delivery_totals = {key: sum(p["delivery"][key] for p in papers) for key in delivery_keys}
    undelivered = [{"paper": p["paper"], **item}
                   for p in papers for item in p["delivery"]["asset_bearing_undelivered"]]
    delivery_totals["asset_bearing_delivery_violations"] = sum(
        not item["intentional_non_delivery"] for item in undelivered
    )
    return {
        "papers": papers,
        "totals": {**totals, "assets": sum(totals.values()), "papers_scanned": len(papers),
                   **delivery_totals},
        "samples": {name: [{"paper": p["paper"], **a} for p in papers for a in p["assets"]
                           if a["classification"] == name][:10] for name in CLASSES},
        "asset_bearing_undelivered": undelivered,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ocr-root", required=True, type=Path)
    parser.add_argument("--keys", nargs="+")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--summary", action="store_true", help="omit per-paper asset detail")
    args = parser.parse_args(argv)
    report = audit_corpus(args.ocr_root, args.keys, args.limit)
    if args.summary:
        report["papers"] = [
            {"paper": p["paper"], "totals": p["totals"], "delivery": p["delivery"]}
            for p in report["papers"]
        ]
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
