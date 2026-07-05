"""paperforge.commands.scoped_fetch — ``paperforge scoped-fetch`` gateway command."""

from __future__ import annotations

import json
from pathlib import Path

from paperforge.core.io import read_json
from paperforge.core.result import PFResult
from paperforge.memory.db import get_connection, get_memory_db_path
from paperforge.retrieval import gateway
from paperforge.retrieval.manifest import build_paper_manifest
from paperforge.retrieval.units import build_body_units, build_object_units


def _find_ocr_dir(vault: Path, paper_id: str) -> Path | None:
    """Look up the OCR output directory for a paper by scanning the ocr root.

    Returns None if no OCR output exists.
    """
    ocr_root = vault / "System" / "PaperForge" / "ocr"
    if not ocr_root.exists():
        return None
    for d in ocr_root.iterdir():
        if d.is_dir() and d.name == paper_id:
            return d
        # also check metadata inside
        index_path = d / "index"
        tree_path = index_path / "structure-tree.json"
        if tree_path.exists():
            try:
                tree = read_json(tree_path)
                if tree.get("paper_id") == paper_id:
                    return d
            except Exception:
                continue
    return None


def _build_units_for_paper(
    vault: Path,
    paper_id: str,
) -> dict:
    """Build retrieval units and manifest for a paper from its OCR output.

    Returns a dict with keys ``body_units``, ``object_units``, ``manifest``
    (or empty lists / None when OCR data is unavailable).
    """
    ocr_dir = _find_ocr_dir(vault, paper_id)
    if ocr_dir is None:
        return {"body_units": [], "object_units": [], "manifest": None}

    index_root = ocr_dir / "index"
    tree_path = index_root / "structure-tree.json"
    structured_path = ocr_dir / "structured-blocks.json"
    if not tree_path.exists() or not structured_path.exists():
        return {"body_units": [], "object_units": [], "manifest": None}

    tree = read_json(tree_path)
    structured_blocks = read_json(structured_path)
    role_index_path = index_root / "role-index.json"
    role_index = read_json(role_index_path) if role_index_path.exists() else {}

    body_units = build_body_units(tree=tree, structured_blocks=structured_blocks)
    object_units = build_object_units(
        tree=tree, structured_blocks=structured_blocks, role_index=role_index
    )

    # Try to read result hash
    result_hash_path = index_root / "result-hash.txt"
    ocr_result_hash = ""
    if result_hash_path.exists():
        ocr_result_hash = result_hash_path.read_text(encoding="utf-8").strip()

    manifest = build_paper_manifest(
        paper_id=paper_id,
        ocr_result_hash=ocr_result_hash,
        structure_tree_bytes=tree_path.read_bytes(),
        retrieval_policy_version="l4.body.v1",
        body_units=body_units,
        object_units=object_units,
        source_paths={
            "structured_blocks": str(structured_path),
            "role_index": str(role_index_path),
            "fulltext": str(ocr_dir / "fulltext.md"),
        },
    )
    return {"body_units": body_units, "object_units": object_units, "manifest": manifest}


def run(args):
    """Execute ``scoped-fetch`` via the Layer 4 gateway."""
    vault = Path(args.vault_path)
    result = gateway.route_gateway(
        vault,
        "scoped-fetch",
        args.query,
        json_mode=args.json,
        limit=getattr(args, "limit", 5),
    )

    # If we have a valid route result, enrich it with retrieval units
    if result.ok and result.data:
        # Extract paper_id from the route plan
        plan = result.data.get("route_plan", {})
        paper_id = (
            plan.get("paper_id")
            or plan.get("primary_paper_id")
            or plan.get("target_id")
            or ""
        )
        if paper_id:
            units = _build_units_for_paper(vault, paper_id)
            result.data["body_units"] = units["body_units"]
            result.data["object_units"] = units["object_units"]
            result.data["manifest"] = units["manifest"]

    print(result.to_json() if args.json else result.data)
    return 0 if result.ok else 1
