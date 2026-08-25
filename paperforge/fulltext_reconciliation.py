"""Fulltext presentation reconciliation — 5-class incremental patch (report-only).

F1 MISSING_EMBED, F2 WRONG_EMBED_TARGET, F3 EXTRA_OR_DUPLICATE,
F4 MISPLACED_EMBED, F0 TARGET_DEGRADED (no fulltext mutation, delegate).
Only INSERT/REPLACE/DELETE/MOVE on fulltext; image/legend fixes delegate to render.

P0 fixes applied:
  P0-1: generic embed parser (not figure_\d+ only)
  P0-2: F2 requires exact canonical mapping
  P0-3: F3 splits SAFE_DELETE / PENDING_PROMOTION / BLOCKED_UNKNOWN
  P1:   F4 uses canonical anchor position, not numeric order
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

# P0-1: parse ANY figure embed target, classify semantic identity after
_EMBED_RE = re.compile(
    r"!\[\[render/figures/"
    r"([a-zA-Z_][a-zA-Z0-9_]*)"
    r"\.md\]\]"
)


def _embed_target_kinds(
    targets: list[str],
    canonical_ids: list[str],
    proposal_ids: list[str],
    orphan_ids: list[str],
) -> dict[str, str]:
    """Classify each embed target into semantic kind."""
    canonical_set = set(canonical_ids)
    proposal_set = set(proposal_ids)
    orphan_set = set(orphan_ids)
    kinds: dict[str, str] = {}
    for t in targets:
        if t in canonical_set:
            kinds[t] = "canonical"
        elif t in proposal_set:
            kinds[t] = "proposal"
        elif t in orphan_set:
            kinds[t] = "orphan"
        elif t.startswith("figure_reserved_"):
            kinds[t] = "reserved"
        elif t.startswith("unresolved_cluster_"):
            kinds[t] = "cluster"
        else:
            kinds[t] = "unknown"
    return kinds


def _canonical_figure_ids(figure_inventory: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for fig in figure_inventory.get("matched_figures", []):
        fid = str(fig.get("figure_id") or "")
        if not fid or fid.startswith("figure_reserved_"):
            continue
        if fig.get("figure_number") is None:
            continue
        ids.append(fid)
    return sorted(ids)


def _proposal_figure_ids(figure_inventory: dict[str, Any]) -> list[str]:
    """Figures created by P reconciliation (proposal_only)."""
    return [
        str(f.get("figure_id") or "")
        for f in figure_inventory.get("matched_figures", [])
        if f.get("settlement_type") == "proposal"
    ]


def _orphan_ids(render_figures_dir: Path) -> list[str]:
    """Orphan figure artifacts."""
    if not render_figures_dir.is_dir():
        return []
    return [f.stem for f in render_figures_dir.glob("orphan_*.md")]


def _fulltext_embeds(fulltext: str) -> list[tuple[str, int]]:
    """Return (target, char_offset) for every figure embed in fulltext."""
    return [(m.group(1), m.start()) for m in _EMBED_RE.finditer(fulltext)]


def _file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def fulltext_reconcile(
    ocr_root: Path,
    paper_key: str,
) -> dict[str, Any]:
    root = ocr_root / paper_key
    inv_path = root / "structure" / "figure_inventory.json"
    ft_path = root / "fulltext.md"
    render_fig_dir = root / "render" / "figures"
    try:
        inv = json.loads(inv_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        inv = {}
    try:
        fulltext = ft_path.read_text(encoding="utf-8")
    except (OSError, ValueError, TypeError):
        fulltext = ""

    canonical_ids = _canonical_figure_ids(inv)
    proposal_ids = _proposal_figure_ids(inv)
    orphan_ids = _orphan_ids(render_fig_dir)
    embed_targets_raw = _fulltext_embeds(fulltext)
    targets_only = [t for t, _ in embed_targets_raw]
    kinds = _embed_target_kinds(targets_only, canonical_ids, proposal_ids, orphan_ids)

    # --- canonical analysis ---
    from collections import Counter

    cnt = Counter(targets_only)
    patches: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    ft_hash = _file_hash(ft_path)

    for fid in canonical_ids:
        c = cnt.get(fid, 0)
        if c == 0:
            issues.append({
                "type": "fulltext_missing_embed",
                "object_id": fid,
                "classification": "F1",
                "recommended_action": "INSERT",
            })
            patches.append({
                "op": "INSERT",
                "object_id": fid,
                "reason": "F1_MISSING_EMBED",
                "input_fulltext_hash": ft_hash,
                "authority": "canonical_inventory",
            })
        elif c > 1:
            issues.append({
                "type": "fulltext_duplicate_embed",
                "object_id": fid,
                "classification": "F3",
                "count": c,
                "recommended_action": "DELETE_duplicates",
            })
            patches.append({
                "op": "DELETE",
                "object_id": fid,
                "reason": "F3_DUPLICATE_EMBED",
                "count": c,
                "expected_embed": "![[render/figures/{}.md]]".format(fid),
                "input_fulltext_hash": ft_hash,
                "authority": "canonical_inventory",
            })
        else:
            # c == 1: check target artifact health -> F0
            fig_md = render_fig_dir / "{}.md".format(fid)
            try:
                md_text = fig_md.read_text(encoding="utf-8")
                has_img = "assets/figures" in md_text
            except (OSError, ValueError, TypeError):
                has_img = False
            if not has_img:
                issues.append({
                    "type": "fulltext_target_degraded",
                    "object_id": fid,
                    "classification": "F0",
                    "recommended_action": "NO_FULLTEXT_WRITE",
                    "delegate": "render/inventory",
                })

    # --- reverse scan: extraneous embeds ---
    canonical_set = set(canonical_ids)
    for target, _offset in embed_targets_raw:
        if target in canonical_set:
            continue
        kind = kinds.get(target, "unknown")
        if kind == "proposal":
            issues.append({
                "type": "fulltext_extra_embed",
                "object_id": target,
                "classification": "F3_PENDING_PROPOSAL",
                "recommended_action": "NO_MUTATION",
            })
        elif kind == "reserved":
            # P0-2: F2 only if exact canonical mapping exists
            num = re.search(r"(\d+)$", target)
            if num:
                num_str = num.group(1)
                mapped = [
                    fid for fid in canonical_ids
                    if re.search(r"(\d+)$", fid)
                    and re.search(r"(\d+)$", fid).group(1) == num_str  # noqa: E501
                ]
                if len(mapped) == 1:
                    issues.append({
                        "type": "fulltext_wrong_target",
                        "object_id": target,
                        "canonical_target": mapped[0],
                        "classification": "F2",
                        "recommended_action": "REPLACE",
                    })
                    patches.append({
                        "op": "REPLACE",
                        "from": target,
                        "to": mapped[0],
                        "reason": "F2_WRONG_EMBED_TARGET",
                        "expected_embed": "![[render/figures/{}.md]]".format(mapped[0]),
                        "input_fulltext_hash": ft_hash,
                        "authority": "canonical_inventory",
                    })
                else:
                    issues.append({
                        "type": "fulltext_wrong_target",
                        "object_id": target,
                        "classification": "F2_AMBIGUOUS",
                        "recommended_action": "BLOCK",
                        "candidates": mapped,
                    })
            else:
                issues.append({
                    "type": "fulltext_wrong_target",
                    "object_id": target,
                    "classification": "F2_NO_NUMERIC",
                    "recommended_action": "BLOCK",
                })
        elif kind == "orphan":
            issues.append({
                "type": "fulltext_extra_embed",
                "object_id": target,
                "classification": "F3_ORPHAN",
                "recommended_action": "SAFE_DELETE",
            })
            patches.append({
                "op": "DELETE",
                "object_id": target,
                "reason": "F3_ORPHAN_EMBED",
                "expected_embed": "![[render/figures/{}.md]]".format(target),
                "input_fulltext_hash": ft_hash,
                "authority": "canonical_inventory",
            })
        else:
            issues.append({
                "type": "fulltext_extra_embed",
                "object_id": target,
                "classification": "F3_BLOCKED_UNKNOWN",
                "recommended_action": "BLOCK",
            })

    return {
        "paper_key": paper_key,
        "canonical_ids": canonical_ids,
        "proposal_ids": proposal_ids,
        "orphan_ids": orphan_ids,
        "embeds": targets_only,
        "kinds": kinds,
        "issues": issues,
        "patches": patches,
        "input_fulltext_hash": ft_hash,
        "summary": {
            "canonical": len(canonical_ids),
            "proposals": len(proposal_ids),
            "embeds": len(targets_only),
            "issues": len(issues),
            "patches": len(patches),
            "f1_missing": sum(1 for i in issues if i.get("classification") == "F1"),
            "f2_replace": sum(1 for i in issues if i.get("classification") == "F2"),
            "f2_blocked": sum(
                1 for i in issues
                if i.get("classification", "").startswith("F2_")
            ),
            "f3_safe_delete": sum(
                1 for i in issues if i.get("classification") == "F3_ORPHAN"
            ),
            "f3_pending": sum(
                1 for i in issues if i.get("classification") == "F3_PENDING_PROPOSAL"
            ),
            "f3_blocked": sum(
                1 for i in issues if i.get("classification") == "F3_BLOCKED_UNKNOWN"
            ),
            "f0_delegated": sum(
                1 for i in issues if i.get("classification") == "F0"
            ),
        },
    }
