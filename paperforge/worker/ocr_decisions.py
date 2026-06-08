from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def record_decision(
    block: dict,
    *,
    stage: str,
    old_role: str | None,
    new_role: str | None,
    reason: str,
    confidence: float | None = None,
    evidence: list[str] | None = None,
) -> None:
    entry: dict[str, Any] = {
        "block_id": block.get("block_id", ""),
        "page": block.get("page", 0),
        "bbox": block.get("bbox") or block.get("block_bbox") or [0, 0, 0, 0],
        "stage": stage,
        "old_role": old_role,
        "new_role": new_role,
        "reason": reason,
        "confidence": confidence,
        "evidence": evidence or [],
    }
    block.setdefault("_decision_log", []).append(entry)


def collect_decisions(blocks: list[dict]) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for block in blocks:
        decisions.extend(block.get("_decision_log", []))
    return decisions


def strip_decision_logs(blocks: list[dict]) -> list[dict]:
    stripped: list[dict] = []
    for block in blocks:
        clone = dict(block)
        clone.pop("_decision_log", None)
        stripped.append(clone)
    return stripped


def summarize_decisions(decisions: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "role_mutation_count": len([d for d in decisions if d.get("old_role") != d.get("new_role")]),
        "role_rescue_count": len([d for d in decisions if "rescue" in str(d.get("stage", ""))]),
        "structured_insert_decision_count": len([d for d in decisions if "structured_insert" in str(d.get("stage", ""))]),
        "tail_promotion_count": len([d for d in decisions if "tail" in str(d.get("stage", ""))]),
        "candidate_resolution_count": len([d for d in decisions if "candidate" in str(d.get("stage", ""))]),
    }


def write_decision_log(path: Path, decisions: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in decisions), encoding="utf-8")
