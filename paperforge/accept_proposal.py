"""Accept a P proposal and promote it to canonical inventory.

`paperforge render accept-proposal <KEY> <label> [--json]`

Authority action: promotes the EXACT staged final plan (what the user
reviewed) into canonical figure_inventory. Invariants:

1. Only FINAL P_REVIEWABLE decisions are accepted (not early proposal_only).
2. The staged final-plan.json is the authority — matched_assets are an
   exact copy of final_plan.member_refs; no re-derivation, no re-matching.
3. Live input snapshot must match the staged plan's snapshot; mismatch →
   STALE_PROPOSAL → refuse.
4. Same-number figure_reserved_00N is NOT auto-deleted; reservation
   correlation must be explicit.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

_FINAL_P_DECISIONS = {
    "structurally_unique_proposal",
    "unique_without_pdf_confirmation",
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def _save_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _snapshot_hash(root: Path) -> str:
    """Cheap live-snapshot fingerprint of the inputs that produced the plan."""
    import hashlib

    parts = []
    for rel in (
        "structure/blocks.structured.jsonl",
        "structure/figure_inventory.json",
        "render/reconciliation.proposals.json",
    ):
        p = root / rel
        if p.is_file():
            parts.append(
                hashlib.sha256(p.read_bytes()).hexdigest()[:16]
            )
        else:
            parts.append("missing")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def accept_proposal(
    ocr_root: Path,
    paper_key: str,
    label: str,
) -> dict[str, Any]:
    root = ocr_root / paper_key
    recon_path = root / "render" / "reconciliation.proposals.json"
    inv_path = root / "structure" / "figure_inventory.json"
    assets_dir = root / "assets" / "figures"
    render_dir = root / "render" / "figures"

    # 1. find latest staging preview with a final-plan.json for this label
    staging_base = Path(__import__("tempfile").gettempdir()) / "paperforge-staging"
    candidates = sorted(
        (
            d
            for d in staging_base.glob(
                "*_{}/{}/previews/figure_{}".format(paper_key, paper_key, label)
            )
            if (d / "final-plan.json").is_file()
        ),
        key=lambda d: (d / "final-plan.json").stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return {
            "ok": False,
            "reason": "staging_final_plan_not_found",
            "paper_key": paper_key,
            "label": label,
        }
    preview_dir = candidates[0]
    plan = _load_json(preview_dir / "final-plan.json")

    # 2. P0-1: only FINAL P_REVIEWABLE decisions
    if plan.get("decision") not in _FINAL_P_DECISIONS:
        return {
            "ok": False,
            "reason": "not_final_p_reviewable",
            "paper_key": paper_key,
            "label": label,
            "decision": plan.get("decision"),
        }

    # 3. P0-2: live snapshot must match staged snapshot (recorded at stage time)
    staged_snapshot = plan.get("input_snapshot_hash")
    live_snapshot = _snapshot_hash(root)
    if staged_snapshot and staged_snapshot != live_snapshot:
        return {
            "ok": False,
            "reason": "STALE_PROPOSAL",
            "paper_key": paper_key,
            "label": label,
            "staged_snapshot": staged_snapshot,
            "live_snapshot": live_snapshot,
        }

    # 4. staged artifacts
    staged_jpg_rel = plan.get("staged_jpg", "")
    staged_md_rel = plan.get("staged_md", "")
    staged_jpg = preview_dir / staged_jpg_rel
    staged_md = preview_dir / staged_md_rel
    if not staged_jpg.is_file():
        return {
            "ok": False,
            "reason": "staged_jpg_missing",
            "paper_key": paper_key,
            "label": label,
            "expected": str(staged_jpg),
        }

    num = int(label)
    canonical_id = "figure_{:03d}".format(num)
    assets_dir.mkdir(parents=True, exist_ok=True)
    render_dir.mkdir(parents=True, exist_ok=True)
    dst_jpg = assets_dir / "{}.jpg".format(canonical_id)
    dst_md = render_dir / "{}.md".format(canonical_id)

    # 5. P0-3: matched_assets = EXACT copy of final_plan.member_refs
    member_refs = plan.get("member_refs") or []
    if not member_refs:
        return {
            "ok": False,
            "reason": "empty_member_refs",
            "paper_key": paper_key,
            "label": label,
        }

    # 6. promote artifacts
    shutil.copy2(staged_jpg, dst_jpg)
    caption_text = str(plan.get("caption_text") or "")
    page = plan.get("page")
    if staged_md.is_file():
        md_text = staged_md.read_text(encoding="utf-8")
        md_text = md_text.replace(
            "figure_proposal_{}.jpg".format(label),
            "{}.jpg".format(canonical_id),
        )
        md_text = md_text.replace(
            "figure_proposal_{}".format(label), canonical_id
        )
        dst_md.write_text(md_text, encoding="utf-8")
    else:
        lines = [
            "# Figure {}".format(label),
            "",
            "![](../../assets/figures/{}.jpg)".format(canonical_id),
            "",
            "## Legend",
            caption_text or "Figure {} (accepted proposal)".format(label),
            "",
        ]
        if page is not None:
            lines.append("*Page {}*".format(page))
            lines.append("")
        lines.append("---")
        lines.append("")
        dst_md.write_text("\n".join(lines), encoding="utf-8")

    # 7. canonical inventory upsert — exact member_refs, no re-derivation
    inv = _load_json(inv_path)
    matched = inv.setdefault("matched_figures", [])
    entry = {
        "figure_id": canonical_id,
        "figure_number": num,
        "figure_namespace": "main",
        "page": page,
        "text": caption_text,
        "matched_assets": member_refs,
        "asset_block_ids": [
            str(a.get("block_id")) for a in member_refs if a.get("block_id")
        ],
        "settlement_type": "accepted_proposal",
        "confidence": 1.0,
        "accepted_from": {
            "staging_dir": str(preview_dir),
            "final_plan_hash": _snapshot_hash(preview_dir),
        },
    }
    replaced = False
    for i, existing in enumerate(matched):
        if str(existing.get("figure_id")) == canonical_id:
            matched[i] = entry
            replaced = True
            break
    if not replaced:
        matched.append(entry)
    _save_json(inv_path, inv)

    # 8. drop the accepted proposal from reconciliation (derived report;
    #    fresh reconcile would regenerate without it anyway)
    recon = _load_json(recon_path)
    recon["proposals"] = [
        p
        for p in recon.get("proposals", [])
        if str(p.get("label")) != label
    ]
    _save_json(recon_path, recon)

    return {
        "ok": True,
        "paper_key": paper_key,
        "label": label,
        "canonical_id": canonical_id,
        "assets": str(dst_jpg),
        "markdown": str(dst_md),
        "member_refs_count": len(member_refs),
        "staging_dir": str(preview_dir),
        "note": "lineage: object_units change → retrieval_identity stale → memory.build re-embeds",
    }
