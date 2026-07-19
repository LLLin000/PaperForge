from __future__ import annotations

from typing import Any


def build_evidence_hit(
    paper_id: str,
    role: str,
    page: int,
    block_id: str,
    text: str,
    asset_path: str = "",
    confidence: float = 0.0,
    verification: str = "",
) -> dict[str, Any]:
    return {
        "paper_id": paper_id,
        "source_type": role,
        "page": page,
        "block_id": block_id,
        "text": text,
        "asset": asset_path,
        "confidence": confidence,
        "verification": verification,
    }


def build_paper_evidence_summary(
    paper_id: str,
    role_indexes: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    by_role: dict[str, int] = {}
    total = 0

    for category, blocks in role_indexes.items():
        if category == "all_blocks":
            continue
        count = len(blocks)
        by_role[category] = count
        total += count

    return {
        "paper_id": paper_id,
        "total_evidence_blocks": total,
        "by_role": by_role,
        "has_figures": by_role.get("captions", 0) > 0,
        "has_tables": by_role.get("tables", 0) > 0,
        "has_references": by_role.get("references", 0) > 0,
    }
