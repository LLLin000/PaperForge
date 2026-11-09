from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VAULT = Path("D:/L/OB/Literature-hub/System/PaperForge/ocr")
BUCKETS = ("caption_recall", "association", "crop_panel", "page_assembly", "delivery", "structural", "no_defect")


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def make_diagnostics(out: Path, vault: Path) -> dict:
    result = load(out / "result.json", {})
    papers = []
    figures = []
    for case in result.get("cases", []):
        key = case["key"]
        paper_dir = vault / key
        baseline = load(out / key / "baseline.json", {})
        dry = baseline.get("dry_run", {})
        structural = baseline.get("structural", {})
        inv = load(paper_dir / "structure" / "figure_inventory.json", {})
        rows = [json.loads(line) for line in (out / key / "labels.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        matches = inv.get("matched_figures", [])
        claims = dry.get("identity", {}).get("claims_changed", [])
        delivery = dry.get("delivery", {})
        tables = dry.get("tables", {})
        content = dry.get("content", {})
        dims = {}
        for item in [*inv.get("matched_figures", []), *inv.get("unmatched_assets", []), *inv.get("unmatched_legends", [])]:
            if item.get("page") and item.get("page_width") and item.get("page_height"):
                dims[int(item["page"])] = (float(item["page_width"]), float(item["page_height"]))
        unmatched_assets = inv.get("unmatched_assets", []) or []
        unmatched_legends = inv.get("unmatched_legends", []) or []
        candidates = [r for r in rows if r.get("kind") == "unmatched_legend"]
        cand_counts = Counter(x["figure_id"] for x in matches)
        asset_owners = Counter(f"p{int(a.get('page', f.get('page', 0)) or 0)}:b{a.get('block_id')}" for f in matches for a in f.get("matched_assets", []))
        near_edge = []
        for asset in unmatched_assets:
            page = int(asset.get("page", 0) or 0)
            box = asset.get("bbox") or []
            size = dims.get(page)
            if len(box) >= 4 and size:
                w, h = size
                gap = min(box[0], box[1], w - box[2], h - box[3])
                if gap <= min(w, h) * .03:
                    near_edge.append({"page": page, "block_id": asset.get("block_id"), "edge_gap_px": round(gap, 1)})
        multipanel = [f for f in matches if re.search(r"\b(?:[a-z](?:\s*[,–-]\s*[a-z]){1,}|\b\d+\s+panels?)\b", str(f.get("text", "")), re.I)]
        multiasset = [f for f in matches if len(f.get("matched_assets", [])) >= 4]
        cross_page = [f for f in matches if any(int(a.get("page", f.get("page", 0)) or 0) != int(f.get("page", 0) or 0) for a in f.get("matched_assets", []))]
        caption_pages = {int(f.get("page", 0) or 0) for f in matches}
        asset_pages = {int(a.get("page", 0) or 0) for f in matches for a in f.get("matched_assets", [])}
        page_asset_mismatches = [{"figure_id": str(f.get("figure_id", "")), "caption_page": int(f.get("page", 0) or 0), "asset_pages": sorted({int(a.get("page", f.get("page", 0)) or 0) for a in f.get("matched_assets", []) if int(a.get("page", f.get("page", 0)) or 0) != int(f.get("page", 0) or 0)})} for f in matches if any(int(a.get("page", f.get("page", 0)) or 0) != int(f.get("page", 0) or 0) for a in f.get("matched_assets", []))]
        page_mismatch = [x["figure_id"] for x in page_asset_mismatches]
        flags = {
            "caption_recall": {"unmatched_legends": len(unmatched_legends), "caption_candidate_rows": len(candidates), "items": candidates},
            "association": {"figure_claims": len(matches), "unmatched_assets": len(unmatched_assets), "duplicate_asset_owners": {k: v for k, v in asset_owners.items() if v > 1}, "duplicate_figure_ids": {k: v for k, v in cand_counts.items() if v > 1}, "claims_changed": len(claims)},
            "crop_panel": {"near_edge_assets": near_edge, "multi_panel_single_asset": [f.get("figure_id") for f in multipanel if len(f.get("matched_assets", [])) == 1], "large_multi_asset_groups": [{"figure_id": f.get("figure_id"), "assets": len(f.get("matched_assets", []))} for f in multiasset]},
            "page_assembly": {"asset_pages_without_caption_page": page_mismatch, "cross_page_claims": [f.get("figure_id") for f in cross_page], "multi_page_candidates": sorted({int(x.get("page", 0) or 0) for x in unmatched_legends} | {int(x.get("page", 0) or 0) for x in unmatched_assets})},
            "delivery": {"render_added": len(delivery.get("render_added", [])), "render_removed": len(delivery.get("render_removed", [])), "missing_embeds": len(delivery.get("embeds_missing_new_id", [])), "dangling_targets": structural.get("dangling_fulltext_targets", 0), "new_orphans": dry.get("new_orphans", 0), "manifest_figures": dry.get("new_manifest", {}).get("figures", 0), "render_missing": not bool(dry.get("new_manifest", {}).get("figures", 0)) and bool(matches)},
            "structural": {"text_decrease": structural.get("text_decrease", False), "pending_markers": structural.get("pending_markers", 0), "table_claim_changes": len(tables.get("claim_changes", [])), "changed_figure_claims": len(claims), "old_text_chars": structural.get("old_text_chars"), "new_text_chars": structural.get("new_text_chars"), "role_changes": {"removed": content.get("role_removed", {}), "added": content.get("role_added", {})}},
        }
        concrete = {str(f.get("figure_id", "")) for f in matches if not str(f.get("figure_id", "")).startswith("figure_reserved")}
        missing_assets = sorted(fid for fid in concrete if not (paper_dir / "assets" / "figures" / f"{fid}.jpg").is_file())
        missing_renders = sorted(fid for fid in concrete if not (paper_dir / "render" / "figures" / f"{fid}.md").is_file())
        fulltext = paper_dir / "fulltext.md"
        embeds = re.findall(r"!\[\[render/(figures|tables)/([^\]]+)\]\]", fulltext.read_text(encoding="utf-8")) if fulltext.is_file() else []
        dangling_embeds = sorted(f"{kind}/{target}" for kind, target in embeds if not (paper_dir / "render" / kind / target).is_file())
        flags["page_assembly"]["asset_caption_page_mismatches"] = page_asset_mismatches
        flags["delivery"].update({"missing_assets": missing_assets, "missing_renders": missing_renders, "dangling_fulltext_embeds": dangling_embeds, "reserved_assetless": sum(1 for f in matches if str(f.get("figure_id", "")).startswith("figure_reserved"))})
        bucket_flags = [name for name in BUCKETS[:-1] if (
            (name == "caption_recall" and (unmatched_legends or candidates)) or
            (name == "association" and (unmatched_assets or claims or any(v > 1 for v in asset_owners.values()))) or
            (name == "crop_panel" and (near_edge or multipanel or multiasset)) or
            (name == "page_assembly" and (page_mismatch or cross_page or len(flags["page_assembly"]["multi_page_candidates"]) > 1)) or
            (name == "delivery" and (flags["delivery"]["missing_assets"] or flags["delivery"]["missing_renders"] or flags["delivery"]["dangling_fulltext_embeds"] or flags["delivery"]["missing_embeds"] or flags["delivery"]["dangling_targets"] or flags["delivery"]["render_missing"])) or
            (name == "structural" and (flags["structural"]["text_decrease"] or flags["structural"]["pending_markers"] or flags["structural"]["table_claim_changes"]))
        )]
        duplicate_ids = {fid: count for fid, count in cand_counts.items() if count > 1}
        papers.append({"key": key, "figures": len(matches), "unmatched_legends": len(unmatched_legends), "caption_candidates": len(candidates), "unmatched_assets": len(unmatched_assets), "near_edge_assets": len(near_edge), "multi_panel_single_asset": len(flags["crop_panel"]["multi_panel_single_asset"]), "large_multi_asset_groups": len(multiasset), "cross_page_claims": len(cross_page), "asset_caption_page_mismatches": len(page_asset_mismatches), "multi_page_candidate_pages": len(flags["page_assembly"]["multi_page_candidates"]), "claim_changes": len(claims), "duplicate_figure_ids": duplicate_ids, "duplicate_asset_owners": flags["association"]["duplicate_asset_owners"], "missing_assets": len(missing_assets), "missing_renders": len(missing_renders), "dangling_fulltext_embeds": len(dangling_embeds), "reserved_assetless": flags["delivery"]["reserved_assetless"], "missing_embeds": flags["delivery"]["missing_embeds"], "dangling_targets": flags["delivery"]["dangling_targets"], "text_decrease": bool(flags["structural"]["text_decrease"]), "pending_markers": flags["structural"]["pending_markers"], "table_claim_changes": flags["structural"]["table_claim_changes"], "buckets": bucket_flags or ["no_defect"], "diagnostics": flags})
        for f in matches:
            assets = f.get("matched_assets", [])
            figures.append({"key": key, "figure_id": str(f.get("figure_id", "")), "legend_block_id": str(f.get("legend_block_id", "")), "page": int(f.get("page", 0) or 0), "caption": str(f.get("text", "")), "asset_count": len(assets), "asset_blocks": [str(a.get("block_id", "")) for a in assets], "asset_pages": [int(a.get("page", f.get("page", 0)) or 0) for a in assets], "case_flags": bucket_flags or ["no_defect"], "review_status": "unreviewed", "root_cause": "unreviewed", "image": f"{key}/{f.get('figure_id')}_asset0.jpg" if assets else f"{key}/page_{int(f.get('page',0) or 0):03d}.jpg"})
    return {"set": "dev", "source": "read-only Dev 50 replay; inventory heuristics are screening signals, not defect labels", "papers": papers, "figures": figures}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    args = parser.parse_args()
    data = make_diagnostics(args.out, args.vault)
    (args.out / "diagnostics.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"papers": len(data["papers"]), "figures": len(data["figures"]), "buckets": dict(Counter(b for p in data["papers"] for b in p["buckets"]))}))


if __name__ == "__main__":
    main()
