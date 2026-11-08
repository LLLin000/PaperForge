"""Create deterministic, read-only human review alternatives for figure/table conflicts."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "scripts" / "dev"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def _box(block: dict) -> list[float] | None:
    value = block.get("bbox")
    if isinstance(value, dict):
        value = [value.get(k) for k in ("x0", "y0", "x1", "y1")]
    try:
        return [float(v) for v in value[:4]] if isinstance(value, (list, tuple)) and len(value) >= 4 else None
    except (TypeError, ValueError):
        return None


def _identity(block: dict) -> tuple[int | None, str]:
    try:
        page = int(block.get("page"))
    except (TypeError, ValueError):
        page = None
    return page, str(block.get("block_id", ""))


def _caption_signal(text: str) -> str | None:
    found = re.search(r"\b(supplementary|supplemental|scheme|figure|fig\.?|table)\b", text, re.I)
    if not found:
        return None
    word = found.group(1).lower()
    return "figure" if word in {"fig", "fig.", "figure"} else word




def _confidence(edge: dict | None) -> tuple[str, str]:
    evidence = (edge or {}).get("evidence", {})
    distance = evidence.get("distance_ratio")
    gap = evidence.get("edge_gap_ratio")
    same = (evidence.get("same_region") or {}).get("value")
    if distance is not None and distance <= 0.08 and gap is not None and gap <= 0.02 and same:
        return "high", "same layout region, centre distance <=0.08, edge gap <=0.02"
    if distance is not None and distance <= 0.16 and same:
        return "medium", "same layout region and centre distance <=0.16"
    return "low", "limited spatial/layout support"


def _alternative(
    decision: str,
    ids: list[str],
    edge: dict | None,
    reason: str,
    *,
    confidence: str | None = None,
    basis: str | None = None,
) -> dict:
    if confidence is None:
        confidence, basis = _confidence(edge)
    else:
        basis = basis or "explicit role/type evidence"
    return {
        "decision": decision,
        "target_asset_ids": sorted(set(ids)),
        "proposed_by": (edge or {}).get("proposed_by", "inventory"),
        "reason": f"{reason}; confidence evidence: {basis}",
        "confidence": confidence,
    }

def build_review_records(
    view: Any, graph: dict | None = None, audit_cases: list[dict] | None = None
) -> list[dict]:
    """Build review records from frozen inventory/graph data and optional audit cases."""
    import figure_evidence_graph

    graph = graph or figure_evidence_graph.build_graph(view, getattr(view, "key", ""))
    blocks = list(view.blocks)
    entries = figure_evidence_graph._inventory_entries(view.figure_inventory, view.table_inventory)
    by_group = {f"group:{entry['kind']}:{entry['group_key'] or i}": entry for i, entry in enumerate(entries)}
    nodes = {node["id"]: node for node in graph["nodes"]}
    block_lookup: dict[tuple, list[dict]] = defaultdict(list)
    for block in blocks:
        block_lookup[_identity(block)].append(block)
    edges_by_source: dict[str, list[dict]] = defaultdict(list)
    for edge in graph["edges"]:
        edges_by_source[edge["source"]].append(edge)
    dupes = {(c.get("page"), str(c.get("block_id"))) for c in graph["conflicts"]
             if c.get("kind") == "duplicate_identity"}

    cases: dict[tuple, dict] = {}
    def add_case(case: dict, kind: str, caption_node_id: str | None = None) -> None:
        caption = case.get("caption") or {}
        page = case.get("page")
        ident = (page, str(caption.get("id", caption.get("block_id", ""))))
        candidates = block_lookup.get(ident, [])
        wanted_box = tuple(caption.get("bbox") or ())
        matching = [b for b in candidates if not wanted_box or tuple(_box(b) or ()) == wanted_box]
        chosen = matching[0] if len(matching) == 1 else (candidates[0] if len(candidates) == 1 else None)
        if caption_node_id is None and chosen is not None:
            cap_node = next((n for n in graph["nodes"] if n.get("type") == "caption" and
                             (n.get("page"), str(n.get("block_id")), tuple(n.get("bbox") or ())) ==
                             (*ident, tuple(_box(chosen) or ()))), None)
            caption_node_id = cap_node["id"] if cap_node else None
        marker = (str(case.get("key", graph.get("key", ""))), page, ident[1], wanted_box, kind)
        cases.setdefault(marker, {"case": case, "kind": kind, "caption_node": caption_node_id, "block": chosen})

    for conflict in graph["conflicts"]:
        if conflict.get("kind") not in {"caption_without_candidate_asset", "asset_multiple_groups"}:
            continue
        nid = conflict.get("caption_id")
        if nid:
            node = nodes.get(nid, {})
            case = {"key": graph.get("key", ""), "page": node.get("page"),
                    "caption": {"id": node.get("block_id"), "bbox": node.get("bbox"), "text": node.get("text", "")}}
            add_case(case, "figure" if "figure" in str(node.get("role", "")).lower() else "table", nid)
        elif conflict.get("kind") == "asset_multiple_groups":
            asset = nodes.get(conflict.get("asset_id"), {})
            for gid in conflict.get("group_ids", []):
                group = by_group.get(gid, {})
                capid = group.get("legend_block_id", group.get("caption_block_id"))
                page = group.get("legend_page", group.get("page", asset.get("page")))
                cap = next((b for b in blocks if _identity(b) == (page, str(capid))), {})
                add_case({"key": graph.get("key", ""), "page": page,
                          "caption": {"id": capid, "bbox": _box(cap), "text": cap.get("text", "")}},
                         group.get("kind", "figure"))
    for node in graph["nodes"]:
        if node.get("type") != "caption":
            continue
        nid = node["id"]
        if any(e["relation"] == "caption_asset" for e in edges_by_source.get(nid, [])):
            add_case({"key": graph.get("key", ""), "page": node.get("page"),
                      "caption": {"id": node.get("block_id"), "bbox": node.get("bbox"),
                                  "text": node.get("text", "")}},
                     "figure" if "figure" in str(node.get("role", "")).lower() else "table", nid)
    for case in audit_cases or []:
        add_case(case, "table" if case.get("stratum") == "table" else "figure")
    role_by_key = {
        (b.get("page"), str(b.get("block_id"))): str(b.get("role") or "").lower() for b in blocks
    }
    for entry in entries:
        if entry.get("kind") != "table":
            continue
        has_asset = entry.get("has_asset", bool(entry.get("asset_block_id") or entry.get("assets")))
        asset_id = entry.get("asset_block_id")
        page = entry.get("page")
        asset_role = role_by_key.get((page, str(asset_id))) if asset_id is not None else None
        # A table holding a figure/media asset is a cross-type mismatch worth
        # reviewing even though the inventory says "has_asset".
        wrong_role = has_asset and asset_role is not None and asset_role not in {"table_html", "table_asset"}
        if not has_asset or wrong_role:
            capid = entry.get("caption_block_id")
            cap = next((b for b in blocks if _identity(b) == (page, str(capid))), {})
            add_case({"key": graph.get("key", ""), "page": page,
                      "caption": {"id": capid, "bbox": _box(cap), "text": cap.get("text", "")}}, "table")

    output = []
    for marker in sorted(cases, key=lambda x: (x[0], x[1] or 0, x[2], x[3], x[4])):
        item = cases[marker]
        case, kind, cnid, cap = item["case"], item["kind"], item["caption_node"], item["block"]
        capinfo = case.get("caption") or {}
        capinfo = {"id": capinfo.get("id", capinfo.get("block_id")),
                   "bbox": capinfo.get("bbox") or (_box(cap) if cap else None),
                   "text": capinfo.get("text", cap.get("text", "") if cap else "")}
        group_edges = [e for e in edges_by_source.get(cnid or "", []) if e["relation"] == "caption_group"]
        groups = [e["target"] for e in group_edges]
        current_entry = by_group.get(groups[0], {}) if len(groups) == 1 else {}
        current_assets = current_entry.get("matched_assets", current_entry.get("assets", [])) or []
        if current_entry.get("asset_block_id"):
            current_assets = [*current_assets, {"block_id": current_entry["asset_block_id"]}]
        current_ids = sorted({
            str(a.get("block_id")) for a in current_assets
            if isinstance(a, dict) and a.get("block_id")
        })
        ambiguous = (marker[1], marker[2]) in dupes or len(block_lookup.get((marker[1], marker[2]), [])) > 1
        match_status = "UNDETERMINED" if ambiguous else current_entry.get(
            "match_status", current_entry.get("_status", "UNRESOLVED")
        )
        current = {
            "group_id": current_entry.get("group_key") if current_entry else None,
            "asset_ids": current_ids,
            "has_asset": current_entry.get("has_asset", bool(current_ids)),
            "match_status": match_status,
        }
        candidate_edges = [
            e for e in edges_by_source.get(cnid or "", [])
            if e["relation"] == "caption_asset"
            and nodes.get(e["target"], {}).get("page") == case.get("page")
        ]
        page_roles = {
            str(b.get("block_id")): str(b.get("role") or "").lower()
            for b in blocks
            if b.get("page") == case.get("page")
        }
        alternatives = []
        if current_ids:
            alternatives.append(_alternative(
                "keep", current_ids, group_edges[0] if group_edges else None,
                "retain current inventory assignment",
            ))
        for edge in candidate_edges:
            asset = nodes.get(edge["target"], {})
            aid = str(asset.get("block_id", ""))
            if aid and aid not in current_ids:
                alternatives.append(_alternative("switch_asset", [aid], edge, "nearby graph candidate"))
        table_assets = [
            b for b in blocks
            if str(b.get("role", "")).lower() in {"table_asset", "table_html"}
            and b.get("page") == case.get("page")
        ]
        current_roles = {page_roles[aid] for aid in current_ids if aid in page_roles}
        if kind == "table" and not current_ids:
            for asset in sorted(table_assets, key=lambda b: (str(b.get("block_id")), _box(b) or [])):
                alternatives.append(_alternative(
                    "attach_table_asset", [str(asset.get("block_id", ""))], None,
                    "table inventory has no asset; existing table-role asset on page",
                ))
        elif kind == "table" and current_roles and not (current_roles & {"table_html", "table_asset"}):
            for asset in sorted(table_assets, key=lambda b: (str(b.get("block_id")), _box(b) or [])):
                aid = str(asset.get("block_id", ""))
                if aid and aid not in current_ids:
                    alternatives.append(_alternative(
                        "switch_asset", [aid], None,
                        "current asset is not a table; same-page table asset exists",
                        confidence="medium",
                        basis="caption type is table and the candidate role is table_html/table_asset",
                    ))
        if not groups:
            alternatives.append(_alternative("new_group", [], None, "caption has no inventory group"))
        alternatives.append(_alternative(
            "no_asset", [], None, "review whether caption intentionally has no associated asset"
        ))
        # One entry per decision/target: the candidate path and the role
        # mismatch path can propose the same asset.
        rank = {"high": 0, "medium": 1, "low": 2}
        unique: dict[tuple, dict] = {}
        for alt in alternatives:
            key = (alt["decision"], tuple(alt["target_asset_ids"]))
            if key not in unique or rank[alt["confidence"]] < rank[unique[key]["confidence"]]:
                unique[key] = alt
        order = {"keep": 0, "switch_asset": 1, "attach_table_asset": 1, "new_group": 2, "no_asset": 3}
        alternatives = sorted(
            unique.values(),
            key=lambda alt: (order[alt["decision"]], rank[alt["confidence"]], alt["target_asset_ids"]),
        )

        for alt in alternatives:
            if alt["decision"] not in {"switch_asset", "attach_table_asset"}:
                continue
            role = page_roles.get(alt["target_asset_ids"][0]) if alt["target_asset_ids"] else None
            if role is None:
                continue
            matches = (kind == "table" and role in {"table_html", "table_asset"}) or (
                kind == "figure" and role in {"figure_asset", "media_asset"}
            )
            if matches:
                if alt["confidence"] == "low":
                    alt["confidence"] = "medium"
                alt["reason"] += "; caption type matches asset role"
            else:
                alt["confidence"] = "low"
                alt["reason"] += "; caption type does not match asset role"
        evidence_edges = candidate_edges + group_edges
        spatial = [e.get("evidence", {}) for e in evidence_edges]
        matched_distances, matched_gaps = [], []
        if cap is not None:
            page = case.get("page")
            dims = (float(cap.get("page_width", 0) or 0), float(cap.get("page_height", 0) or 0))
            for asset_id in current_ids:
                matches = [b for b in blocks if b.get("page") == page and str(b.get("block_id")) == asset_id]
                if len(matches) == 1:
                    distance, gap = figure_evidence_graph._distance(cap, matches[0], dims)
                    if distance is not None:
                        matched_distances.append(distance)
                    if gap is not None:
                        matched_gaps.append(gap)
        assets_evidence = []
        for b in blocks:
            if str(b.get("role", "")).lower() in {"figure_asset", "media_asset", "table_asset", "table_html"}:
                assets_evidence.append({"id": b.get("block_id"), "role": b.get("role"), "page": b.get("page")})
        inventory = current_entry
        evidence = {
            "caption_type_signal": _caption_signal(capinfo["text"]),
            "asset_roles": sorted(
                assets_evidence, key=lambda a: (str(a["page"]), str(a["id"]), str(a["role"]))
            ),
            "layout_region": next(
                ((s.get("same_region") or {}).get("region_id") for s in spatial
                 if (s.get("same_region") or {}).get("region_id")), None
            ),
            "layout_column": any(s.get("same_column") for s in spatial),
            "centre_distance_ratio": matched_distances + [s.get("distance_ratio") for s in spatial],
            "matched_edge_gap_ratio": min(matched_gaps, default=case.get("matched_edge_gap_ratio")),
            "nearest_edge_gap_ratio": min(
                (s.get("edge_gap_ratio") for s in spatial if s.get("edge_gap_ratio") is not None),
                default=case.get("nearest_edge_gap_ratio", case.get("edge_gap_ratio")),
            ),
            "match_score": inventory.get("match_score", inventory.get("score")),
            "candidate_assets": inventory.get("candidate_assets", case.get("candidate_assets", [])),
            "audit": {
                k: case.get(k)
                for k in ("stratum", "distance_ratio", "edge_gap_ratio", "layout_region_kind",
                          "match_pass", "score", "status")
                if k in case
            },
        }
        output.append({"key": case.get("key", graph.get("key", "")), "page": case.get("page"),
                       "caption": capinfo, "kind": kind, "current": current,
                       "alternatives": alternatives, "evidence": evidence, "status": "UNREVIEWED"})
    return output


def _markdown(records: list[dict]) -> str:
    kinds = Counter(r["kind"] for r in records)
    decisions = Counter(a["decision"] for r in records for a in r["alternatives"])
    # Cross-type inventory targets are reported from role evidence.
    cross_type = []
    for r in records:
        roles = {
            str(a["id"]): str(a["role"]).lower()
            for a in r["evidence"]["asset_roles"] if a["page"] == r["page"]
        }
        for alt in r["alternatives"]:
            if alt["decision"] not in {"switch_asset", "attach_table_asset"}:
                continue
            if any(
                (r["kind"] == "figure" and roles.get(a) in {"table_asset", "table_html"}) or
                (r["kind"] == "table" and roles.get(a) in {"figure_asset", "media_asset"})
                for a in alt["target_asset_ids"]
            ):
                cross_type.append((r["key"], r["page"], r["caption"]["id"], alt["target_asset_ids"]))
    best = sorted(((a["confidence"], r, a) for r in records for a in r["alternatives"]
                   if a["decision"] in {"switch_asset", "attach_table_asset"}),
                  key=lambda row: ({"high": 0, "medium": 1, "low": 2}[row[0]], row[1]["key"], row[1]["page"] or 0,
                                   str(row[1]["caption"]["id"]), row[2]["target_asset_ids"]))[:10]
    lines = [
        "## Counts by kind", "",
        *(f"- {k}: {kinds[k]}" for k in ("figure", "table")),
        "", "## Counts by alternative decision", "",
        *(f"- {k}: {decisions[k]}" for k in sorted(decisions)),
        "", "## Cross-type assets", "",
    ]
    lines.extend(
        f"- {key} p.{page} caption `{caption}` → `{','.join(ids)}`"
        for key, page, caption, ids in cross_type
    )
    lines.extend(["", "## Strongest switch/attach alternatives", ""])
    lines.extend(
        f"- {r['key']} p.{r['page']} `{r['caption']['id']}`: {a['decision']} "
        f"`{','.join(a['target_asset_ids'])}` ({confidence})"
        for confidence, r, a in best
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--keys", nargs="*")
    parser.add_argument("--keys-file", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    keys = list(args.keys or [])
    if args.keys_file:
        keys.extend(args.keys_file.read_text(encoding="utf-8").split())
    if not keys:
        keys = sorted(p.name for p in args.vault.iterdir() if p.is_dir())
    keys = list(dict.fromkeys(keys))
    if args.limit is not None:
        keys = keys[:max(0, args.limit)]
    from figure_evidence_graph import build_graph
    from figure_table_error_audit import build_cases
    from layout_evidence import build_final_view

    from paperforge.worker.layout.evaluate import evaluate_plan
    from paperforge.worker.layout.plan import build_layout_plan

    views, audit_rows = [], []
    for key in keys:
        paper = args.vault / key
        if not (paper / "canonical" / "blocks.raw.jsonl").is_file():
            continue
        view = build_final_view(paper)
        plan = build_layout_plan(view.blocks)
        evaluation = evaluate_plan(plan, view.blocks, view.figure_inventory, view.table_inventory)
        audits = build_cases(
            view.key, view.blocks, view.figure_inventory, view.table_inventory,
            plan.to_dict(), evaluation, per_stratum=10,
        )
        views.append((view, build_graph(view, key)))
        audit_rows.extend(audits)
    audit_rows.sort(key=lambda c: (
        c["key"], c["page"], c["stratum"], c["distance_ratio"] or 0,
        str(c["caption"]["id"]), c["caption"]["bbox"],
    ))
    ghost_first, seen_ghost_keys = [], set()
    for case in audit_rows:
        if case["stratum"] == "ghost" and case["key"] not in seen_ghost_keys:
            seen_ghost_keys.add(case["key"])
            ghost_first.append(case)
    ordered = ghost_first + [case for case in audit_rows if case["stratum"] != "ghost"]
    ordered += [case for case in audit_rows if case["stratum"] == "ghost" and case not in ghost_first]
    kept_audits, counts = [], Counter()
    for audit in ordered:
        stratum = audit["stratum"]
        if counts[stratum] < 10:
            kept_audits.append(audit)
            counts[stratum] += 1
    by_key: dict[str, list[dict]] = defaultdict(list)
    for audit in kept_audits:
        by_key[audit["key"]].append(audit)
    records = [
        record for view, graph in views
        for record in build_review_records(view, graph, by_key[view.key])
    ]
    records.sort(key=lambda r: (r["key"], r["page"] or 0, str(r["caption"]["id"]), r["kind"]))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"cases": records}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(_markdown(records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
