"""Accept a P proposal and promote it to canonical inventory.

`paperforge render accept-proposal <KEY> <label> [--json]`

Authority action: promotes a verified P proposal (figure_proposal_N) into
canonical figure_inventory as figure_00N with real matched_assets. This is
the ONLY sanctioned path from P_REVIEWABLE to canonical — fulltext/reconcile
never promote on their own.

After promotion:
- figure_inventory.matched_figures gains/updates the canonical entry
- render/reconciliation.proposals.json proposals list drops the accepted label
- downstream: role_index → object_units → retrieval_identity changes →
  lineage vector goes stale → memory.build re-embeds that paper
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def _save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def accept_proposal(
    ocr_root: Path,
    paper_key: str,
    label: str,
) -> dict[str, Any]:
    """Promote one P proposal to canonical inventory.

    Steps:
    1. Read reconciliation.proposals.json, find the proposal with this label
       and a P decision (proposal_only / structurally_unique_proposal /
       unique_without_pdf_confirmation).
    2. Read staging preview artifacts (jpg + md) from the latest
       paperforge-staging run for this paper.
    3. Copy preview jpg → assets/figures/figure_00N.jpg
       Copy preview md  → render/figures/figure_00N.md (rewriting image ref)
    4. Update figure_inventory.matched_figures: upsert canonical entry with
       figure_id=figure_00N, figure_number=N, matched_assets from the
       proposal's surviving candidate(s), settlement_type="accepted_proposal".
    5. Remove the accepted proposal from reconciliation.proposals.json.
    """
    root = ocr_root / paper_key
    recon_path = root / "render" / "reconciliation.proposals.json"
    inv_path = root / "structure" / "figure_inventory.json"
    assets_dir = root / "assets" / "figures"
    render_dir = root / "render" / "figures"

    recon = _load_json(recon_path)
    inv = _load_json(inv_path)

    # 1. find proposal
    prop = None
    for cand in recon.get("proposals", []):
        if str(cand.get("label")) == label and cand.get("decision") in {
            "proposal_only",
            "structurally_unique_proposal",
            "unique_without_pdf_confirmation",
        }:
            prop = cand
            break
    if prop is None:
        return {
            "ok": False,
            "reason": "proposal_not_found",
            "paper_key": paper_key,
            "label": label,
        }

    # 2. find latest staging preview for this label
    staging_base = Path(__import__("tempfile").gettempdir()) / "paperforge-staging"
    candidates = sorted(
        (d for d in staging_base.glob("*_{}/{}/previews/figure_{}".format(paper_key, paper_key, label))),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return {
            "ok": False,
            "reason": "staging_preview_not_found",
            "paper_key": paper_key,
            "label": label,
        }
    preview_dir = candidates[0]
    staged_jpg = preview_dir / "assets" / "figures" / "figure_proposal_{}.jpg".format(label)
    staged_md = preview_dir / "render" / "figures" / "figure_proposal_{}.md".format(label)
    if not staged_jpg.is_file():
        # fallback: flat preview layout
        staged_jpg = preview_dir / "figure_{}.proposed.jpg".format(label)
        staged_md = preview_dir / "figure_{}.proposed.md".format(label)
    if not staged_jpg.is_file():
        return {
            "ok": False,
            "reason": "staged_jpg_missing",
            "paper_key": paper_key,
            "label": label,
            "expected": str(staged_jpg),
        }

    # 3. promote artifacts
    num = int(label)
    canonical_id = "figure_{:03d}".format(num)
    assets_dir.mkdir(parents=True, exist_ok=True)
    render_dir.mkdir(parents=True, exist_ok=True)
    dst_jpg = assets_dir / "{}.jpg".format(canonical_id)
    dst_md = render_dir / "{}.md".format(canonical_id)
    shutil.copy2(staged_jpg, dst_jpg)

    # Build canonical markdown from staged md (rewrite image ref) or from scratch
    caption_text = ""
    for ev in prop.get("evidence_chain", []):
        for item in ev.get("items", []):
            if item.get("text"):
                caption_text = str(item["text"])
                break
        if caption_text:
            break
    page = prop.get("candidate_pages", [{}])[0].get("page") if prop.get("candidate_pages") else None
    if staged_md.is_file():
        md_text = staged_md.read_text(encoding="utf-8")
        md_text = md_text.replace(
            "figure_proposal_{}.jpg".format(label), "{}.jpg".format(canonical_id)
        )
        md_text = md_text.replace("figure_proposal_{}".format(label), canonical_id)
        dst_md.write_text(md_text, encoding="utf-8")
    else:
        md_lines = [
            "# Figure {}".format(label),
            "",
            "![](../../assets/figures/{}.jpg)".format(canonical_id),
            "",
            "## Legend",
            caption_text or "Figure {} (accepted proposal)".format(label),
            "",
        ]
        if page is not None:
            md_lines.append("*Page {}*".format(page))
            md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
        dst_md.write_text("\n".join(md_lines), encoding="utf-8")

    # 4. update figure_inventory
    matched = inv.setdefault("matched_figures", [])
    # collect matched_assets from proposal surviving candidates (if staged run recorded)
    matched_assets: list[dict[str, Any]] = []
    # try dry_bounded surviving candidates recorded in recon? recon doesn't carry them;
    # use the candidate_pages source_images bbox as authoritative asset refs
    for cp in prop.get("candidate_pages", []):
        for si in cp.get("source_images", []):
            m = re.search(r"figure_(\d+)_([\d_]+)\.jpg$", str(si.get("path", "")))
            bbox = None
            if m:
                parts = m.group(2).split("_")
                if len(parts) == 4:
                    try:
                        bbox = [int(x) for x in parts]
                    except ValueError:
                        bbox = None
            matched_assets.append({
                "page": cp.get("page"),
                "block_id": si.get("block_id") or (m.group(1) if m else None),
                "bbox": bbox,
            })

    entry = {
        "figure_id": canonical_id,
        "figure_number": num,
        "figure_namespace": "main",
        "page": page,
        "text": caption_text,
        "matched_assets": matched_assets,
        "asset_block_ids": [str(a.get("block_id")) for a in matched_assets if a.get("block_id")],
        "settlement_type": "accepted_proposal",
        "confidence": 1.0,
    }
    # upsert by figure_id
    replaced = False
    for i, existing in enumerate(matched):
        if str(existing.get("figure_id")) == canonical_id:
            matched[i] = entry
            replaced = True
            break
    if not replaced:
        matched.append(entry)

    # drop reserved entry with same number if present (e.g. figure_reserved_005 → figure_005)
    inv["matched_figures"] = [
        f for f in inv["matched_figures"]
        if not (
            str(f.get("figure_id", "")).startswith("figure_reserved_")
            and str(f.get("figure_id", "")) == "figure_reserved_{:03d}".format(num)
        )
    ]
    _save_json(inv_path, inv)

    # 5. drop the accepted proposal from reconciliation
    recon["proposals"] = [
        p for p in recon.get("proposals", [])
        if not (str(p.get("label")) == label and p is not prop)
    ]
    recon["proposals"] = [
        p for p in recon.get("proposals", []) if str(p.get("label")) != label
    ]
    _save_json(recon_path, recon)

    return {
        "ok": True,
        "paper_key": paper_key,
        "label": label,
        "canonical_id": canonical_id,
        "assets": str(dst_jpg),
        "markdown": str(dst_md),
        "matched_assets_count": len(matched_assets),
        "note": "lineage: role_index/object_units will change → retrieval_identity stale → memory.build re-embeds",
    }
