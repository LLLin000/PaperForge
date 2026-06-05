from __future__ import annotations

import datetime
from pathlib import Path

from paperforge.core.io import read_json, write_json


def _apply_post_rebuild_version_flags(meta: dict) -> dict:
    """Update version state flags after a derived-layer rebuild.

    - derived_stale becomes False (derived artifacts are now current)
    - raw_upgradable is preserved (only raw OCR can clear this)
    - version_state_updated_at is refreshed
    """
    updated = dict(meta)
    updated["derived_stale"] = False
    updated["version_state_updated_at"] = datetime.datetime.now().isoformat()
    return updated


def select_papers_for_derived_rebuild(papers: list[dict]) -> list[str]:
    """Filter papers requiring derived-only rebuild (not raw upgrade).

    Args:
        papers: List of paper dicts with at least zotero_key and derived_stale.

    Returns:
        List of zotero_keys needing derived rebuild.
    """
    return [p["zotero_key"] for p in papers if p.get("derived_stale") and not p.get("raw_upgradable")]


def run_derived_rebuild_for_keys(vault: Path, keys: list[str]) -> dict:
    """Run derived-layer rebuild for the given paper keys without raw OCR rerun.

    Rebuilds: structured blocks, metadata, figure/table inventories, objects,
    render outputs, and health — from stored raw blocks only.
    """
    from paperforge.worker._utils import pipeline_paths, read_jsonl
    from paperforge.worker.ocr_artifacts import artifact_paths_for_root

    ocr_root = pipeline_paths(vault)["ocr"]
    rebuilt_count = 0

    for key in keys:
        artifacts = artifact_paths_for_root(ocr_root, key)
        paper_root = artifacts.paper_root
        if not paper_root.exists():
            continue

        # Read stored raw blocks
        if not artifacts.blocks_raw.exists():
            continue
        all_raw_blocks = list(read_jsonl(artifacts.blocks_raw))

        # Rebuild structured blocks
        from paperforge.worker.ocr_blocks import build_structured_blocks, write_structured_blocks_jsonl

        structured = build_structured_blocks(all_raw_blocks)
        write_structured_blocks_jsonl(artifacts.blocks_structured, structured)

        # Read source metadata
        source_meta = read_json(artifacts.source_metadata) if artifacts.source_metadata.exists() else {}

        # Rebuild resolved metadata
        from paperforge.worker.ocr_metadata import (
            extract_frontmatter_candidates,
            resolve_metadata,
            write_resolved_metadata,
        )

        metadata_dir = paper_root / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        frontmatter_candidates = extract_frontmatter_candidates(artifacts.blocks_structured)
        resolved = resolve_metadata(source_meta, frontmatter_candidates)
        write_resolved_metadata(metadata_dir / "resolved_metadata.json", resolved)

        # Rebuild figure inventory
        from paperforge.worker.ocr_figures import build_figure_inventory, write_figure_inventory

        figure_inventory = build_figure_inventory(structured)
        write_figure_inventory(artifacts.blocks_structured.parent / "figure_inventory.json", figure_inventory)

        # Rebuild table inventory
        from paperforge.worker.ocr_tables import build_table_inventory, write_table_inventory

        table_inventory = build_table_inventory(structured)
        write_table_inventory(artifacts.blocks_structured.parent / "table_inventory.json", table_inventory)

        # Rebuild object artifacts
        from paperforge.worker.ocr_objects import extract_and_write_objects

        ocr_meta = read_json(artifacts.meta_json) if artifacts.meta_json.exists() else {}
        source_pdf_path = Path(ocr_meta.get("source_pdf", "")) if ocr_meta.get("source_pdf") else None
        extract_and_write_objects(
            pdf_path=source_pdf_path,
            figure_inventory=figure_inventory,
            table_inventory=table_inventory,
            asset_root=paper_root / "assets",
            render_root=paper_root / "render",
        )

        # Rebuild render output
        from paperforge.worker.ocr_render import render_fulltext_markdown, write_render_outputs

        markdown = render_fulltext_markdown(
            structured_blocks=structured,
            resolved_metadata=resolved,
            figure_inventory=figure_inventory,
            table_inventory=table_inventory,
        )
        write_render_outputs(
            render_root=paper_root / "render",
            compat_fulltext=artifacts.compat_fulltext,
            markdown=markdown,
        )

        # Rebuild health
        from paperforge.worker.ocr_health import build_ocr_health, write_ocr_health

        health_report = build_ocr_health(
            page_count=ocr_meta.get("page_count", 0),
            raw_blocks_count=len(all_raw_blocks),
            structured_blocks=structured,
            figure_inventory=figure_inventory,
            table_inventory=table_inventory,
        )
        write_ocr_health(paper_root / "health", health_report)

        # Rebuild role index
        from paperforge.worker.ocr_index import build_role_indexes, write_role_index

        role_indexes = build_role_indexes(
            structured_blocks=structured,
            resolved_metadata=resolved,
        )
        write_role_index(paper_root / "index", role_indexes)

        # Update version state in meta.json
        meta = read_json(artifacts.meta_json) if artifacts.meta_json.exists() else {}
        meta = _apply_post_rebuild_version_flags(meta)
        write_json(artifacts.meta_json, meta)

        rebuilt_count += 1

    return {"rebuild_count": rebuilt_count}


def backfill_from_result(vault: Path, key: str) -> dict:
    """Backfill all derived OCR artifacts from an existing result.json.

    For papers that were OCR'd before the structured pipeline existed,
    this reads the stored result.json, normalizes it, and runs the
    full postprocess pipeline to produce all Phase 1-5 artifacts.

    Args:
        vault: Vault root path.
        key: Zotero key of the paper to backfill.

    Returns:
        Dict with backfill_status and paper_key.
    """
    from paperforge.worker._utils import pipeline_paths
    from paperforge.worker.ocr import postprocess_ocr_result

    ocr_root = pipeline_paths(vault)["ocr"]
    paper_dir = ocr_root / key
    result_path = paper_dir / "json" / "result.json"

    if not result_path.exists():
        return {"backfill_status": "skipped_no_result", "paper_key": key}

    try:
        raw = read_json(result_path)
    except Exception:
        return {"backfill_status": "failed_read", "paper_key": key}

    # Normalize: legacy result.json may be {"pages": [...]} dict or a list directly
    if isinstance(raw, dict):
        all_results = raw.get("pages", [])
        if not isinstance(all_results, list):
            all_results = [raw]
    elif isinstance(raw, list):
        all_results = raw
    else:
        return {"backfill_status": "failed_format", "paper_key": key}

    if not all_results:
        return {"backfill_status": "skipped_empty", "paper_key": key}

    try:
        _, _, _, _ = postprocess_ocr_result(vault, key, all_results)

        # Add backfill metadata
        meta_path = paper_dir / "meta.json"
        meta = read_json(meta_path) if meta_path.exists() else {}
        meta["is_backfilled"] = True
        meta["backfilled_at"] = __import__("datetime").datetime.now().isoformat()
        write_json(meta_path, meta)

        return {"backfill_status": "done", "paper_key": key}
    except Exception as e:
        return {"backfill_status": "failed", "paper_key": key, "error": str(e)}
