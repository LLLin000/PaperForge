"""Build a deterministic, read-only review set for figure/table association errors."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT, _REPO_ROOT / "scripts" / "dev"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

GHOST_KEYS = {"2HEUD5P9", "388XI46Q", "53B47JM8", "55EKJRBC", "5CK2JEIS"}
STRATA = ("2-5%", "5-15%", ">15%", "normal_control", "ghost", "table")


def bucket(distance_ratio: float) -> str:
    if distance_ratio <= 0.05:
        return "2-5%"
    if distance_ratio <= 0.15:
        return "5-15%"
    return ">15%"


def _bbox(block: dict) -> list[float] | None:
    box = block.get("bbox")
    return list(box) if isinstance(box, (list, tuple)) and len(box) >= 4 else None


def _geometry_key(page: int, block_id: str, bbox: list[float] | None) -> tuple:
    return page, str(block_id), tuple(bbox or ())


def _edge_gap_ratio(caption: dict, blocks: list[dict], page: int) -> float | None:
    """Nearest caption/object edge gap, in page heights.

    Centre distance grows with figure height, so it cannot tell "caption under
    a tall figure" from "caption associated with the wrong object". The edge
    gap can.
    """
    cap = _bbox(caption)
    if cap is None:
        return None
    height = float(caption.get("page_height", 0) or 0)
    if height <= 0:
        return None
    best: float | None = None
    for block in blocks:
        if int(block.get("page", 0) or 0) != page or block is caption:
            continue
        role = str(block.get("role", ""))
        if role not in {"media_asset", "figure_asset", "table_asset", "table_html"}:
            continue
        box = _bbox(block)
        if box is None:
            continue
        gap = max(0.0, box[1] - cap[3], cap[1] - box[3])
        if best is None or gap < best:
            best = gap
    return round(best / height, 4) if best is not None else None


def _case(key: str, stratum: str, page: int, caption: dict, blocks: list[dict],
          region_kind: str | None, ratio: float | None, matched_figure_id: str | None,
          inventory_entry: dict | None) -> dict[str, Any]:
    box = _bbox(caption) or []
    candidates = []
    for block in blocks:
        role = str(block.get("role", ""))
        if int(block.get("page", 0) or 0) != page or not (
            role in {"media_asset", "figure_asset", "table_asset", "table_html"}
            or block.get("raw_label") in {"figure", "image", "table", "table_image"}
        ):
            continue
        candidates.append({"id": block.get("block_id"), "bbox": _bbox(block), "role": role or None})
    candidates.sort(key=lambda item: (str(item["id"]), item["bbox"] or [], str(item["role"])))
    provenance = {name: inventory_entry.get(name) if inventory_entry else None
                  for name in ("match_pass", "score", "status", "evidence")}
    return {
        "key": key, "page": page, "stratum": stratum,
        "caption": {"id": caption.get("block_id"), "bbox": box, "text": caption.get("text", "")},
        "candidate_assets": candidates,
        "inventory_state": {"matched_figure_id": matched_figure_id,
                            "state": "matched" if matched_figure_id else "unmatched"},
        "distance_ratio": round(ratio, 4) if ratio is not None else None,
        "edge_gap_ratio": _edge_gap_ratio(caption, blocks, page),
        "layout_region_kind": region_kind,
        **provenance,
    }


def build_cases(key: str, blocks: list[dict], figure_inventory: dict, table_inventory: dict,
                plan: dict, evaluation: dict, per_stratum: int = 10) -> list[dict[str, Any]]:
    """Select bounded strata; repeated (page, block_id) requires exact geometry."""
    buckets: dict[str, list[dict]] = {name: [] for name in STRATA}
    page_region: dict[int, dict[tuple, str]] = {}
    for page_plan in plan.get("pages", []):
        for region in page_plan.get("regions", []):
            for uid in region.get("members", []):
                page_region.setdefault(int(page_plan["page"]), {})[uid] = region.get("kind")
    from paperforge.worker.layout.plan import collect_block_refs

    refs = collect_block_refs(blocks)
    by_uid = {ref.uid: blocks[ref.raw_index] for ref in refs}
    inventory_by_pair = {}
    for entry in figure_inventory.get("matched_figures", []):
        caption_id = str(entry.get("legend_block_id", entry.get("block_id", "")))
        caption_page = int(entry.get("page", 0) or 0)
        captions = [ref for ref in refs if ref.page == caption_page and ref.block_id == caption_id]
        if len(captions) != 1:
            continue
        for asset in entry.get("matched_assets", entry.get("assets", [])):
            asset_page = int(asset.get("page", caption_page) or caption_page)
            assets = [ref for ref in refs if ref.page == asset_page
                      and ref.block_id == str(asset.get("block_id", ""))
                      and (not asset.get("bbox") or list(ref.bbox or ()) == list(asset["bbox"]))]
            if len(assets) == 1:
                inventory_by_pair[(captions[0].uid, assets[0].uid)] = entry

    def add(stratum: str, caption: dict, page: int, ratio: float | None,
            inv: dict | None = None, region: str | None = None) -> None:
        matched_id = (inv or {}).get("figure_id") if inv else None
        buckets[stratum].append(_case(key, stratum, page, caption, blocks, region, ratio, matched_id, inv))

    for pair in evaluation.get("figure_caption", {}).get("suspicious", []):
        caption = by_uid.get(pair.get("caption"))
        if caption is None:
            continue
        ratio = float(pair.get("distance_ratio", 0))
        page = int(pair.get("page", caption.get("page", 0)) or 0)
        uid = pair.get("caption")
        inv = inventory_by_pair.get((uid, pair.get("asset")))
        add(bucket(ratio), caption, page, ratio, inv, page_region.get(page, {}).get(uid))

    for inv in figure_inventory.get("matched_figures", []):
        capid = inv.get("legend_block_id", inv.get("block_id", ""))
        page = int(inv.get("page", 0) or 0)
        captions = [b for b in blocks if int(b.get("page", 0) or 0) == page
                    and str(b.get("block_id", "")) == str(capid)]
        if len(captions) != 1:
            continue
        caption = captions[0]
        for asset in inv.get("matched_assets", inv.get("assets", [])):
            if int(asset.get("page", page) or page) != page:
                continue
            asset_box = asset.get("bbox")
            cap_box = _bbox(caption)
            if cap_box and asset_box and len(asset_box) >= 4:
                height = float(caption.get("page_height", 1) or 1)
                cap_y = (cap_box[1] + cap_box[3]) / 2
                asset_y = (asset_box[1] + asset_box[3]) / 2
                ratio = abs(cap_y - asset_y) / height
                gap = max(0.0, asset_box[1] - cap_box[3], cap_box[1] - asset_box[3]) / height
                if gap <= 0.02:
                    add("normal_control", caption, page, ratio, inv)

    ghost = key in GHOST_KEYS
    if ghost:
        for caption in blocks:
            if "caption" in str(caption.get("role", "")).lower() and _bbox(caption):
                add("ghost", caption, int(caption.get("page", 0) or 0), None)

    for table in table_inventory.get("tables", []):
        capid = table.get("caption_block_id", table.get("block_id", ""))
        page = int(table.get("page", 0) or 0)
        captions = [b for b in blocks if int(b.get("page", 0) or 0) == page
                    and str(b.get("block_id", "")) == str(capid)]
        if len(captions) == 1:
            add("table", captions[0], page, None, table)

    result = []
    for name in STRATA:
        rows = buckets[name]
        rows.sort(key=lambda row: (row["key"], row["page"], row["distance_ratio"] or 0,
                                   str(row["caption"]["id"]), row["caption"]["bbox"]))
        result.extend(rows)
    return result


def _paper_cases(paper_dir: Path, per_stratum: int) -> list[dict[str, Any]]:
    from layout_evidence import build_final_view

    from paperforge.worker.layout.evaluate import evaluate_plan
    from paperforge.worker.layout.plan import build_layout_plan

    view = build_final_view(paper_dir)
    plan = build_layout_plan(view.blocks)
    evaluation = evaluate_plan(plan, view.blocks, view.figure_inventory, view.table_inventory)
    return build_cases(view.key, view.blocks, view.figure_inventory, view.table_inventory,
                       plan.to_dict(), evaluation, per_stratum)


def _markdown(cases: list[dict[str, Any]], ghost_keys: set[str]) -> str:
    counts = {name: sum(case["stratum"] == name for case in cases) for name in STRATA}
    lines = ["| Stratum | Cases |", "|---|---:|"]
    lines.extend(f"| {name} | {counts[name]} |" for name in STRATA)
    lines += ["", f"Ghost keys contributing cases: {len({c['key'] for c in cases if c['key'] in ghost_keys})}",
              "", "| Key | Page | Stratum | Distance ratio | Caption |", "|---|---:|---|---:|---|"]
    top = sorted(cases, key=lambda c: (-(c["distance_ratio"] or 0), c["key"], c["page"]))[:10]
    for case in top:
        lines.append(
            f"| {case['key']} | {case['page']} | {case['stratum']} | "
            f"{case['distance_ratio']} | {case['caption']['id']} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--keys", nargs="*")
    parser.add_argument("--keys-file", type=Path)
    parser.add_argument("--per-stratum", type=int, default=10)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    keys = set(args.keys or [])
    if args.keys_file is not None:
        keys.update(line.strip() for line in args.keys_file.read_text(encoding="utf-8").splitlines() if line.strip())
    if not keys:
        parser.error("provide --keys and/or --keys-file")
    # The known ghost cases are the most valuable negatives; include them even
    # when the sampled corpus does not happen to contain them.
    keys.update(key for key in GHOST_KEYS if (args.vault / key).is_dir())
    keys = sorted(keys)
    cases = []
    for key in keys:
        paper = args.vault / key
        if (paper / "canonical" / "blocks.raw.jsonl").is_file():
            cases.extend(_paper_cases(paper, args.per_stratum))
    cases.sort(key=lambda c: (c["key"], c["page"], c["stratum"], c["distance_ratio"] or 0,
                              str(c["caption"]["id"]), c["caption"]["bbox"]))
    # Quota is global per stratum, not per paper: the review set stays bounded
    # no matter how many papers are scanned.
    kept: list[dict[str, Any]] = []
    used: dict[str, int] = {}
    # Ghost cases are spread one-per-key first, then filled: otherwise the
    # alphabetically first ghost paper consumes the whole stratum.
    ghost_first = [case for case in cases if case["stratum"] == "ghost"]
    seen_ghost_keys: set[str] = set()
    rounded: list[dict[str, Any]] = []
    for case in ghost_first:
        if case["key"] not in seen_ghost_keys:
            seen_ghost_keys.add(case["key"])
            rounded.append(case)
    ordered = rounded + [case for case in cases if case["stratum"] != "ghost"]
    ordered += [case for case in ghost_first if case not in rounded]
    for case in ordered:
        stratum = case["stratum"]
        if used.get(stratum, 0) >= max(0, args.per_stratum):
            continue
        used[stratum] = used.get(stratum, 0) + 1
        kept.append(case)
    cases = kept
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"classification": "UNREVIEWED", "cases": cases},
                                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(_markdown(cases, GHOST_KEYS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
