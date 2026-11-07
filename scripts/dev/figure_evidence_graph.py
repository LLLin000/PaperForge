"""Build a read-only candidate evidence graph for figure and table association."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "scripts" / "dev"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def _bbox(block: dict) -> list[float] | None:
    value = block.get("bbox")
    if isinstance(value, dict):
        value = [value.get(k) for k in ("x0", "y0", "x1", "y1")]
    if not isinstance(value, (list, tuple)) or len(value) < 4:
        return None
    try:
        return [float(v) for v in value[:4]]
    except (TypeError, ValueError):
        return None


def _page(block: dict) -> int | None:
    try:
        return int(block.get("page"))
    except (TypeError, ValueError):
        return None


def _role(block: dict) -> str:
    role = block.get("role", "")
    return str(role.get("name", "") if isinstance(role, dict) else role).lower()


def _identity(block: dict) -> tuple[int | None, str]:
    return _page(block), str(block.get("block_id", ""))


def _distance(a: dict, b: dict, dims: tuple[float, float]) -> tuple[float | None, float | None]:
    aa, bb = _bbox(a), _bbox(b)
    if aa is None or bb is None:
        return None, None
    pw, ph = dims
    scale = math.hypot(pw, ph) if pw > 0 and ph > 0 else math.hypot(
        max(aa[2], bb[2]) - min(aa[0], bb[0]), max(aa[3], bb[3]) - min(aa[1], bb[1])
    )
    if scale <= 0:
        return None, None
    ac = ((aa[0] + aa[2]) / 2, (aa[1] + aa[3]) / 2)
    bc = ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
    dx = max(aa[0] - bb[2], bb[0] - aa[2], 0.0)
    dy = max(aa[1] - bb[3], bb[1] - aa[3], 0.0)
    return math.dist(ac, bc) / scale, math.hypot(dx, dy) / scale


def _inventory_entries(figures: dict, tables: dict) -> list[dict]:
    entries = []
    for name in ("matched_figures", "held_figures", "ambiguous_figures"):
        status = "MATCHED" if name == "matched_figures" else "HOLD"
        for item in figures.get(name, []):
            entries.append({**item, "_status": status, "kind": "figure",
                            "group_key": str(item.get("figure_id", ""))})
    for name in ("tables", "held_tables"):
        status = "MATCHED" if name == "tables" else "HOLD"
        for item in tables.get(name, []):
            group_key = item.get("table_id") or item.get("caption_block_id")
            entries.append({**item, "_status": status, "kind": "table", "group_key": str(group_key or "")})
    return entries


def build_graph(view: Any, key: str = "") -> dict[str, Any]:
    blocks = list(view.blocks)
    figures, tables = view.figure_inventory, view.table_inventory
    entries = _inventory_entries(figures, tables)
    block_by_identity: dict[tuple, list[dict]] = defaultdict(list)
    for block in blocks:
        block_by_identity[_identity(block)].append(block)

    inventory_caption_ids = set()
    inventory_asset_ids = set()
    for entry in entries:
        capid = entry.get("legend_block_id") if entry["kind"] == "figure" else entry.get("caption_block_id")
        if capid:
            inventory_caption_ids.add((entry.get("legend_page", entry.get("page")), str(capid)))
        assets = entry.get("matched_assets", entry.get("assets", [])) or []
        for asset in assets:
            if isinstance(asset, dict) and asset.get("block_id"):
                inventory_asset_ids.add((asset.get("page", entry.get("page")), str(asset["block_id"])))
        if entry.get("asset_block_id"):
            inventory_asset_ids.add((entry.get("asset_page", entry.get("page")), str(entry["asset_block_id"])))

    kinds: dict[int, set[str]] = defaultdict(set)
    for i, block in enumerate(blocks):
        role = _role(block)
        ident = _identity(block)
        if "figure_caption" in role or "table_caption" in role or ident in inventory_caption_ids:
            kinds[i].add("caption")
        if role in {"figure_asset", "media_asset", "table_asset", "table_html"} or ident in inventory_asset_ids:
            kinds[i].add("asset")
    dup_counts = Counter(_identity(b) for b in blocks)
    node_ids: dict[tuple[int, str], list[str]] = defaultdict(list)
    nodes = []
    for i, block in enumerate(blocks):
        for kind in sorted(kinds[i]):
            page, bid = _identity(block)
            box = _bbox(block)
            geom = ",".join(f"{v:g}" for v in box) if box else "null"
            base = f"{kind}:{page}:{bid}:{geom}"
            same = [j for j in range(i) if kinds[j] and _identity(blocks[j]) == (page, bid)]
            nid = base + (f":dup{len(same) + 1}" if dup_counts[(page, bid)] > 1 else "")
            node_ids[(i, kind)] = [nid]
            nodes.append({"id": nid, "type": kind, "page": page, "block_id": bid, "bbox": box,
                          "role": block.get("role"), "text": block.get("text", "")})

    group_nodes, edges, conflicts = [], [], []
    entry_node = {}
    for idx, entry in enumerate(entries):
        gid = f"group:{entry['kind']}:{entry['group_key'] or idx}"
        entry_node[idx] = gid
        group_nodes.append({"id": gid, "type": "group", "kind": entry["kind"], "inventory_id": entry["group_key"],
                            "page": entry.get("page")})
    nodes.extend(group_nodes)

    # Candidate links are evaluated from existing blocks and inventory only; no matching pass is rerun.
    captions = [(i, b) for i, b in enumerate(blocks) if "caption" in kinds[i]]
    assets = [(i, b) for i, b in enumerate(blocks) if "asset" in kinds[i]]
    region_for = {}
    try:
        from paperforge.worker.layout.plan import build_layout_plan, collect_block_refs
        plan = build_layout_plan(blocks)
        refs = {ref.uid: ref for ref in collect_block_refs(blocks)}
        for page in plan.pages:
            for region in page.regions:
                for uid in region.members:
                    ref = refs.get(uid)
                    if ref is not None:
                        region_for[ref.raw_index] = (region.region_id, region.kind)
    except (ImportError, AttributeError, TypeError, ValueError):
        pass
    dims_by_page = {}
    for block in blocks:
        page = _page(block)
        if page is not None:
            dims_by_page[page] = (float(block.get("page_width", 0) or 0), float(block.get("page_height", 0) or 0))

    def edge_evidence(cap: dict, asset: dict, cap_i: int, asset_i: int) -> dict:
        page = _page(cap)
        d, gap = _distance(cap, asset, dims_by_page.get(page, (0, 0))) if page == _page(asset) else (None, None)
        cr, ar = region_for.get(cap_i), region_for.get(asset_i)
        same = bool(cr and ar and cr[0] == ar[0])
        return {"same_region": {"value": same, "region_id": cr[0] if same else None,
                                "region_kind": cr[1] if same else None},
                "same_column": bool(same and cr[1] == ar[1] == "column"),
                "distance_ratio": d, "edge_gap_ratio": gap, "page": page}

    def add_edge(
        src: str,
        dst: str,
        relation: str,
        status: str,
        entry: dict | None = None,
        evidence: dict | None = None,
    ):
        edges.append({"source": src, "target": dst, "relation": relation, "proposed_by":
                      (entry or {}).get("proposed_by", (entry or {}).get("match_pass", "inventory")),
                      "score": (entry or {}).get("score"), "status": status,
                      "evidence": evidence or {"same_region": {"value": None, "region_id": None, "region_kind": None},
                                               "same_column": None, "distance_ratio": None, "edge_gap_ratio": None,
                                               "page": (entry or {}).get("page")}})

    groups_claiming_asset: dict[str, set[str]] = defaultdict(set)
    caption_groups: dict[str, set[str]] = defaultdict(set)
    caption_candidates: dict[str, set[str]] = defaultdict(set)
    for eidx, entry in enumerate(entries):
        gid = entry_node[eidx]
        capid = entry.get("legend_block_id") if entry["kind"] == "figure" else entry.get("caption_block_id")
        cap_page = entry.get("legend_page", entry.get("page"))
        cap_matches = block_by_identity.get((cap_page, str(capid)), []) if capid else []
        cap_i = next((i for i, b in enumerate(blocks) if b in cap_matches), None) if len(cap_matches) == 1 else None
        if cap_i is not None and node_ids.get((cap_i, "caption")):
            cnid = node_ids[(cap_i, "caption")][0]
            caption_groups[cnid].add(gid)
            bb = blocks[cap_i]
            add_edge(cnid, gid, "caption_group", entry["_status"], entry, {"page": _page(bb)})
        matched_assets = entry.get("matched_assets", entry.get("assets", [])) or []
        if entry.get("asset_block_id"):
            matched_assets = [
                *matched_assets,
                {
                    "block_id": entry["asset_block_id"],
                    "page": entry.get("asset_page", entry.get("page")),
                },
            ]
        for item in matched_assets:
            if not isinstance(item, dict):
                continue
            matches = block_by_identity.get((item.get("page", entry.get("page")), str(item.get("block_id", ""))), [])
            if len(matches) != 1:
                continue
            ai = blocks.index(matches[0])
            anid = (node_ids.get((ai, "asset")) or [None])[0]
            if anid:
                add_edge(gid, anid, "group_asset", entry["_status"], entry, {"page": _page(blocks[ai])})
                groups_claiming_asset[anid].add(gid)

    for ci, caption in captions:
        cnid = node_ids[(ci, "caption")][0]
        matched_groups = {e["target"] for e in edges if e["source"] == cnid and e["relation"] == "caption_group"}
        for ai, asset in assets:
            evidence = edge_evidence(caption, asset, ci, ai)
            distance = evidence["distance_ratio"]
            if distance is None or distance > 0.25:
                continue
            anid = node_ids[(ai, "asset")][0]
            if any(e["source"] in matched_groups and e["target"] == anid and e["relation"] == "group_asset"
                   for e in edges):
                continue
            duplicate = dup_counts[_identity(caption)] > 1 or dup_counts[_identity(asset)] > 1
            add_edge(cnid, anid, "caption_asset", "UNDETERMINED" if duplicate else "CANDIDATE", evidence=evidence)
            caption_candidates[cnid].add(anid)
    # Attach direct competition edges from captions to all inventory groups associated via captions/assets.
    for cnid, gids in caption_groups.items():
        for gid in gids:
            for edge in edges:
                if edge["source"] == gid and edge["relation"] == "group_asset":
                    caption_candidates[cnid].add(edge["target"])

    def conflict(kind: str, **fields):
        conflicts.append({"kind": kind, **fields})
    for caption, gids in caption_groups.items():
        if len(gids) >= 2:
            conflict("caption_multiple_groups", caption_id=caption, group_ids=sorted(gids))
    for asset_id, gids in groups_claiming_asset.items():
        if len(gids) >= 2:
            conflict("asset_multiple_groups", asset_id=asset_id, group_ids=sorted(gids))
    captioned = {e["target"] for e in edges if e["relation"] == "caption_group"}
    for group in group_nodes:
        if group["id"] not in captioned:
            conflict("group_without_caption", group_id=group["id"])
    for i, _caption in captions:
        nid = node_ids[(i, "caption")][0]
        if not caption_candidates[nid]:
            conflict("caption_without_candidate_asset", caption_id=nid)
    for ident, matching in block_by_identity.items():
        if len(matching) > 1:
            related = sorted(
                node["id"]
                for node in nodes
                if node.get("page") == ident[0] and node.get("block_id") == ident[1]
            )
            conflict("duplicate_identity", page=ident[0], block_id=ident[1], status="UNDETERMINED",
                     node_ids=related)
    nodes.sort(
        key=lambda node: (
            node["type"],
            str(node.get("page")),
            str(node.get("block_id", node.get("inventory_id", ""))),
            node["id"],
        )
    )
    edges.sort(key=lambda e: (e["relation"], e["source"], e["target"], e["status"]))
    conflicts.sort(key=lambda c: (c["kind"], json.dumps(c, sort_keys=True)))
    return {"key": key or getattr(view, "key", ""), "nodes": nodes, "edges": edges, "conflicts": conflicts}


def _markdown(payload: dict) -> str:
    status = Counter(edge["status"] for paper in payload["papers"] for edge in paper["edges"])
    conflict_counts = Counter(c["kind"] for paper in payload["papers"] for c in paper["conflicts"])
    unresolved = []
    for paper in payload["papers"]:
        byid = {n["id"]: n for n in paper["nodes"]}
        for edge in paper["edges"]:
            if edge["status"] in {"UNRESOLVED", "UNDETERMINED"}:
                unresolved.append((paper["key"], byid.get(edge["source"], {}).get("block_id", edge["source"]),
                                   byid.get(edge["target"], {}).get("block_id", edge["target"])))
    status_lines = [
        f"- {name}: {status[name]}"
        for name in ("MATCHED", "CANDIDATE", "HOLD", "UNRESOLVED", "UNDETERMINED")
    ]
    conflict_lines = [f"- {name}: {conflict_counts[name]}" for name in sorted(conflict_counts)]
    unresolved_lines = [
        f"- {key}: caption `{caption}` / asset `{asset}`"
        for key, caption, asset in unresolved[:10]
    ]
    lines = ["## Status counts", "", *status_lines,
             "", "## Conflicts by kind", "", *conflict_lines,
             "", "## Top unresolved cases", "", *unresolved_lines,
             "", "## Conflict samples"]
    for paper in payload["papers"]:
        for conflict in paper["conflicts"][:3]:
            detail = json.dumps(conflict, sort_keys=True, ensure_ascii=False)
            lines.append(f"- {paper['key']} {conflict['kind']}: {detail}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--keys", nargs="*")
    parser.add_argument("--keys-file", type=Path, help="text file containing paper keys")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--out", required=True, type=Path, help="JSON output path")
    args = parser.parse_args(argv)
    from layout_evidence import build_final_view
    keys = list(args.keys or [])
    if args.keys_file is not None:
        keys.extend(args.keys_file.read_text(encoding="utf-8").split())
    if not keys:
        keys = sorted(p.name for p in args.vault.iterdir() if p.is_dir())
    if args.limit is not None:
        keys = keys[:max(0, args.limit)]
    papers = []
    for key in keys:
        if (args.vault / key / "canonical" / "blocks.raw.jsonl").is_file():
            papers.append(build_graph(build_final_view(args.vault / key), key))
    status_counts = Counter(edge["status"] for paper in papers for edge in paper["edges"])
    conflict_counts = Counter(conflict["kind"] for paper in papers for conflict in paper["conflicts"])
    payload = {
        "papers": papers,
        "totals": {
            "papers": len(papers),
            "nodes": sum(len(paper["nodes"]) for paper in papers),
            "edges": sum(len(paper["edges"]) for paper in papers),
            "status": dict(status_counts),
            "conflicts": dict(conflict_counts),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(_markdown(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
