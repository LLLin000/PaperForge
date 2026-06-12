from __future__ import annotations

import datetime
from pathlib import Path

from paperforge.core.io import read_json, write_json


def _resolve_source_pdf_for_rebuild(vault: Path, key: str, meta: dict) -> Path | None:
    """Resolve a usable source PDF path for span backfill.

    Resolution order:
    1. meta['source_pdf'] if exists and file exists
    2. Zotero storage lookup: {vault}/zotero/storage/{key}/*.pdf
    3. paper dir: {vault}/System/PaperForge/ocr/{key}/source.pdf
    """
    source = meta.get("source_pdf") or ""
    if source and Path(source).exists():
        return Path(source)

    storage_dir = vault / "zotero" / "storage" / key
    if storage_dir.exists():
        pdfs = list(storage_dir.glob("*.pdf"))
        if pdfs:
            return pdfs[0]

    local = vault / "System" / "PaperForge" / "ocr" / key / "source.pdf"
    if local.exists():
        return local

    return None


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
    from paperforge.worker.ocr import validate_ocr_meta
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

        # Backfill span_metadata from source PDF
        ocr_meta = read_json(artifacts.meta_json) if artifacts.meta_json.exists() else {}
        source_pdf_path = _resolve_source_pdf_for_rebuild(vault, key, ocr_meta)
        if source_pdf_path and source_pdf_path.exists():
            from paperforge.worker.ocr_blocks import write_raw_blocks_jsonl
            from paperforge.worker.ocr_pdf_spans import backfill_span_metadata_from_pdf

            backfill_span_metadata_from_pdf(all_raw_blocks, source_pdf_path)
            write_raw_blocks_jsonl(artifacts.blocks_raw, all_raw_blocks)

        # Read source metadata. If legacy/old OCR papers are missing canonical
        # bibliographic metadata, enrich source_metadata.json from the formal
        # Literature-hub note frontmatter before rebuilding OCR-derived layers.
        _enrich_meta_from_paper_note(vault, key, artifacts.source_metadata)
        source_meta = read_json(artifacts.source_metadata) if artifacts.source_metadata.exists() else {}

        # Rebuild structured blocks
        from paperforge.worker.ocr_blocks import build_structured_blocks, write_structured_blocks_jsonl

        structured, doc_structure = build_structured_blocks(
            all_raw_blocks,
            source_metadata=source_meta,
            structure_output_dir=artifacts.blocks_structured.parent,
        )
        write_structured_blocks_jsonl(artifacts.blocks_structured, structured)
        # Write role-level span profiles
        from paperforge.worker.ocr_profiles import write_role_span_profiles

        write_role_span_profiles(structured, artifacts.blocks_structured.parent)

        # Rebuild resolved metadata
        from paperforge.worker.ocr_metadata import (
            extract_frontmatter_candidates,
            resolve_metadata,
            write_resolved_metadata,
        )

        metadata_dir = paper_root / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        frontmatter_candidates = extract_frontmatter_candidates(artifacts.blocks_structured)
        resolved = resolve_metadata(
            source_meta,
            frontmatter_candidates,
            page_blocks=all_raw_blocks,
            structured_blocks=structured,
        )
        write_resolved_metadata(metadata_dir / "resolved_metadata.json", resolved)

        # Rebuild figure inventory
        from paperforge.worker.ocr_figures import build_figure_inventory, write_figure_inventory

        figure_inventory = build_figure_inventory(structured)
        write_figure_inventory(artifacts.blocks_structured.parent / "figure_inventory.json", figure_inventory)

        # Rebuild reader figures
        from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

        reader_payload = synthesize_reader_figures(figure_inventory, structured_blocks=structured)
        reader_figures_dir = paper_root / "structure"
        reader_figures_dir.mkdir(parents=True, exist_ok=True)
        write_json(reader_figures_dir / "reader_figures.json", reader_payload)

        # Rebuild table inventory
        from paperforge.worker.ocr_tables import build_table_inventory, write_table_inventory

        table_inventory = build_table_inventory(structured)
        write_table_inventory(artifacts.blocks_structured.parent / "table_inventory.json", table_inventory)

        # Rebuild object artifacts
        from paperforge.worker.ocr_objects import extract_and_write_objects

        ocr_meta = read_json(artifacts.meta_json) if artifacts.meta_json.exists() else {}
        source_pdf_path = Path(ocr_meta.get("source_pdf", "")) if ocr_meta.get("source_pdf") else None
        page_dimensions_by_page: dict[int, tuple[int, int]] = {}
        for block in structured:
            page = int(block.get("page", 0) or 0)
            width = int(block.get("page_width", 0) or 0)
            height = int(block.get("page_height", 0) or 0)
            if page and width and height and page not in page_dimensions_by_page:
                page_dimensions_by_page[page] = (width, height)

        extract_and_write_objects(
            pdf_path=source_pdf_path,
            figure_inventory=figure_inventory,
            table_inventory=table_inventory,
            asset_root=paper_root / "assets",
            render_root=paper_root / "render",
            page_dimensions_by_page=page_dimensions_by_page,
        )

        # Rebuild render output
        from paperforge.worker.ocr_render import render_fulltext_markdown, write_render_outputs

        rebuild_page_count = ocr_meta.get("page_count", 0) or 0
        if not rebuild_page_count:
            all_rebuild_pages = {int(b["page"]) for b in structured if b.get("page")}
            rebuild_page_count = max(all_rebuild_pages) if all_rebuild_pages else 0
        markdown = render_fulltext_markdown(
            structured_blocks=structured,
            resolved_metadata=resolved,
            figure_inventory=figure_inventory,
            table_inventory=table_inventory,
            page_count=rebuild_page_count,
            document_structure=doc_structure,
            reader_payload=reader_payload,
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
            doc_structure=doc_structure,
            reader_payload=reader_payload,
        )
        write_ocr_health(paper_root / "health", health_report)

        # Persist decision log
        from paperforge.worker.ocr_decisions import collect_decisions, write_decision_log

        write_decision_log(paper_root / "health" / "decision_log.jsonl", collect_decisions(structured))

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
        # Rebuild regenerated the derived outputs; validate from a clean
        # optimistic status instead of short-circuiting on a stale
        # done_incomplete value from a previous render.
        meta["ocr_status"] = "done"
        # Re-validate and clear stale errors (e.g. page marker mismatch from pre-fix render)
        paths_dict = {"ocr": pipeline_paths(vault)["ocr"]}
        _status, _err = validate_ocr_meta(paths_dict, meta)
        meta["ocr_status"] = _status
        meta["error"] = _err if _err else ""
        write_json(artifacts.meta_json, meta)

        rebuilt_count += 1

    return {"rebuild_count": rebuilt_count}


def _enrich_meta_from_paper_note(vault: Path, key: str, meta_path: Path) -> None:
    """Read the paper note's Zotero frontmatter and inject into meta.json.

    This ensures legacy backfill captures the real title/authors/DOI from
    Zotero rather than relying on OCR frontmatter guessing.
    """
    try:
        from paperforge.worker._utils import pipeline_paths

        paths = pipeline_paths(vault)
        lit_dir = paths.get("literature")
        if lit_dir and lit_dir.exists():
            pattern = f"**/{key}*.md"
            matches = list(lit_dir.rglob(pattern))
            # Filter to exact key match: the note file is named <key>.md
            note = next((m for m in matches if m.stem == key), None)
            if note and note.exists():
                from paperforge.adapters.obsidian_frontmatter import read_frontmatter_dict

                content = note.read_text(encoding="utf-8", errors="replace")
                fm = read_frontmatter_dict(content)
                if not fm:
                    return
                meta = read_json(meta_path) if meta_path.exists() else {}
                changed = False
                # Always re-extract authors on rebuild — source_metadata may carry stale
                # first-author-only entries from previous runs with no way to detect them
                if meta.get("authors_source") != "zotero":
                    meta.pop("authors", None)
                    meta.pop("authors_incomplete", None)
                    meta.pop("authors_source", None)
                    meta.pop("first_author", None)
                    changed = True
                for field in ("title", "authors", "year", "journal", "doi"):
                    if field not in meta or not meta.get(field):
                        val = fm.get(field)
                        if val:
                            meta[field] = val
                            changed = True
                if (not meta.get("authors")) and fm.get("first_author"):
                    meta["authors"] = [str(fm["first_author"])]
                    meta["first_author"] = str(fm["first_author"])
                    meta["authors_incomplete"] = True
                    meta["authors_source"] = "paper_note.first_author_fallback"
                    changed = True
                if changed:
                    write_json(meta_path, meta)
    except Exception:
        pass


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
        # Inject Zotero metadata from paper note frontmatter before postprocess
        _enrich_meta_from_paper_note(vault, key, paper_dir / "meta.json")

        # Resolve source_pdf so extract_and_write_objects can crop figures/tables
        try:
            meta_before = read_json(paper_dir / "meta.json") if (paper_dir / "meta.json").exists() else {}
            src = str(meta_before.get("source_pdf", ""))
            if src and "storage:" in src:
                from paperforge.pdf_resolver import resolve_junction, resolve_pdf_path

                pf_cfg = read_json(vault / "paperforge.json") if (vault / "paperforge.json").exists() else {}
                zotero_path = None
                zotero_dir = pf_cfg.get("zotero_data_dir", "") or pf_cfg.get("zotero_link", "")
                if zotero_dir:
                    zotero_path = Path(zotero_dir)
                    if not zotero_path.is_absolute():
                        zotero_path = resolve_junction((vault / zotero_dir).resolve())
                resolved = resolve_pdf_path(src, True, vault, zotero_path)
                if not resolved and zotero_path and src.startswith("storage:"):
                    storage_key = src[len("storage:") :].split("/")[0].strip()
                    storage_dir = (zotero_path / "storage" / storage_key).resolve()
                    if storage_dir.exists():
                        pdfs = [f for f in storage_dir.iterdir() if f.suffix.lower() == ".pdf"]
                        if pdfs:
                            resolved = str(pdfs[0])
                if resolved:
                    meta_before["source_pdf"] = resolved
                    write_json(paper_dir / "meta.json", meta_before)
        except Exception:
            pass

        _, _, _, _ = postprocess_ocr_result(vault, key, all_results)

        # Add backfill metadata
        meta_path = paper_dir / "meta.json"
        meta = read_json(meta_path) if meta_path.exists() else {}
        meta["is_backfilled"] = True
        meta["backfilled_at"] = __import__("datetime").datetime.now().isoformat()
        meta["ocr_status"] = "done"
        # Fix assets_path from legacy images/ to structured assets/
        if meta.get("assets_path", "").endswith("/images"):
            meta["assets_path"] = meta["assets_path"].replace("/images", "/assets")
        elif meta.get("assets_path", "").endswith("\\images"):
            meta["assets_path"] = meta["assets_path"].replace("\\images", "\\assets")
        write_json(meta_path, meta)

        return {"backfill_status": "done", "paper_key": key}
    except Exception as e:
        return {"backfill_status": "failed", "paper_key": key, "error": str(e)}


def select_legacy_papers_for_backfill(papers: list[dict]) -> list[str]:
    """Filter papers that need legacy backfill.

    Args:
        papers: List of paper dicts with is_legacy and can_backfill flags.

    Returns:
        List of zotero_keys needing backfill.
    """
    return [p["zotero_key"] for p in papers if p.get("is_legacy") and p.get("can_backfill")]
