from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path

from paperforge.core.io import read_json, write_json

logger = logging.getLogger(__name__)

CURRENT_SPAN_BACKFILL_VERSION = "2026-07-01.1"
CURRENT_SPAN_VISUAL_CONTAINER_VERSION = "2026-06-26.6"
MIN_SPAN_BACKFILL_COVERAGE = 0.90


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


def _is_text_like_raw_block(block: dict) -> bool:
    raw_label = str(block.get("raw_label") or "")
    text = str(block.get("text") or "").strip()
    bbox = block.get("bbox") or []
    text_like_labels = {"text", "paragraph_title", "abstract", "reference_content", "figure_title"}
    return raw_label in text_like_labels and bool(text) and len(bbox) >= 4


def _compute_span_backfill_coverage(raw_blocks: list[dict]) -> tuple[int, int, float]:
    eligible = [block for block in raw_blocks if _is_text_like_raw_block(block)]
    eligible_count = len(eligible)
    if eligible_count == 0:
        return 0, 0, 1.0
    covered_count = sum(1 for block in eligible if block.get("span_metadata"))
    return covered_count, eligible_count, covered_count / eligible_count


def _span_backfill_is_valid(meta: dict, *, current_pdf_fingerprint: str, coverage: float) -> bool:
    if current_pdf_fingerprint == "unknown":
        return False
    return (
        meta.get("span_backfill_version") == CURRENT_SPAN_BACKFILL_VERSION
        and meta.get("span_visual_container_version") == CURRENT_SPAN_VISUAL_CONTAINER_VERSION
        and meta.get("span_pdf_fingerprint") == current_pdf_fingerprint
        and coverage >= MIN_SPAN_BACKFILL_COVERAGE
    )


def _update_span_status_meta(
    meta: dict, *, covered_count: int, eligible_count: int, coverage: float, status: str,
) -> dict:
    updated = dict(meta)
    updated["span_backfill_covered_count"] = covered_count
    updated["span_backfill_eligible_count"] = eligible_count
    updated["span_backfill_coverage"] = coverage
    updated["span_backfill_status"] = status
    return updated


def _update_span_validity_meta(
    meta: dict, *, fingerprint: str, covered_count: int, eligible_count: int, coverage: float, status: str,
) -> dict:
    updated = _update_span_status_meta(
        meta,
        covered_count=covered_count,
        eligible_count=eligible_count,
        coverage=coverage,
        status=status,
    )
    updated["span_backfill_version"] = CURRENT_SPAN_BACKFILL_VERSION
    updated["span_visual_container_version"] = CURRENT_SPAN_VISUAL_CONTAINER_VERSION
    updated["span_pdf_fingerprint"] = fingerprint
    return updated


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




def _filter_completed_keys(checkpoint_dir: Path | None, keys: list[str]) -> list[str]:
    """Return keys that do not have a .done.<key> marker in checkpoint_dir."""
    if not checkpoint_dir:
        return keys
    cp = Path(checkpoint_dir)
    if not cp.exists():
        return keys
    done = {p.name.removeprefix(".done.") for p in cp.glob(".done.*")}
    return [k for k in keys if k not in done]


def _write_done_marker(checkpoint_dir: Path | None, key: str) -> None:
    """Write a completion marker for a successfully rebuilt paper."""
    if not checkpoint_dir:
        return
    (Path(checkpoint_dir) / f".done.{key}").touch()


def _rebuild_one_paper(vault: Path, key: str) -> dict:
    """Rebuild derived artifacts for a single paper. Module-level for pickle.

    Returns dict with status ('ok', 'skipped') and details.
    """
    from paperforge.worker._utils import pipeline_paths, read_jsonl
    from paperforge.worker.ocr import validate_ocr_meta
    from paperforge.worker.ocr_artifacts import artifact_paths_for_root

    ocr_root = pipeline_paths(vault)["ocr"]
    artifacts = artifact_paths_for_root(ocr_root, key)
    paper_root = artifacts.paper_root

    if not paper_root.exists():
        return {"key": key, "status": "skipped", "reason": "no_paper_dir"}
    if not artifacts.blocks_raw.exists():
        return {"key": key, "status": "skipped", "reason": "no_raw_blocks"}

    all_raw_blocks = list(read_jsonl(artifacts.blocks_raw))
    ocr_meta = read_json(artifacts.meta_json) if artifacts.meta_json.exists() else {}

    # ── Phase 1: clean raw blocks and span backfill ──
    def _phase1_span_backfill() -> dict:
        """Reject overlapping fallback blocks, backfill span_metadata from PDF.
        Returns (span_meta_patch, source_pdf_path). Modifies all_raw_blocks in place."""
        nonlocal all_raw_blocks

        from paperforge.worker.ocr_pdf_spans import (
            _BACKFILL_OVERLAP_REJECT_THRESHOLD,
            _backfill_coverage_in_existing,
        )
        for block in all_raw_blocks:
            if block.get("_text_source") != "pdf_text_layer_fallback":
                continue
            text = str(block.get("text") or block.get("block_content") or "").strip()
            if not text:
                continue
            same_page_body = [
                other for other in all_raw_blocks
                if other is not block
                and other.get("page") == block.get("page")
                and str(other.get("text") or other.get("block_content") or "").strip()
                and other.get("_text_source") != "pdf_text_layer_fallback"
            ]
            if any(
                _backfill_coverage_in_existing(text, str(other.get("text") or other.get("block_content") or ""))
                >= _BACKFILL_OVERLAP_REJECT_THRESHOLD
                for other in same_page_body
            ):
                block["text"] = ""
                block.pop("block_content", None)
                block["_ocr_raw_status"] = "missing_text_rejected"
                block["_ocr_raw_error_type"] = "backfill_overlaps_existing_text_block"
                block["_text_source"] = "pdf_text_layer_fallback_rejected"

        source_pdf_path = _resolve_source_pdf_for_rebuild(vault, key, ocr_meta)
        span_meta_patch: dict[str, object] = {}
        covered_count, eligible_count, coverage = _compute_span_backfill_coverage(all_raw_blocks)

        if not source_pdf_path or not source_pdf_path.exists():
            span_meta_patch = _update_span_status_meta(
                ocr_meta,
                covered_count=covered_count,
                eligible_count=eligible_count,
                coverage=coverage,
                status="unavailable_pdf_missing",
            )
        else:
            from paperforge.worker.ocr_artifacts import compute_pdf_fingerprint

            current_fp = compute_pdf_fingerprint(source_pdf_path)
            if current_fp != "unknown" and _span_backfill_is_valid(
                ocr_meta,
                current_pdf_fingerprint=current_fp,
                coverage=coverage,
            ):
                span_meta_patch = _update_span_validity_meta(
                    ocr_meta,
                    fingerprint=current_fp,
                    covered_count=covered_count,
                    eligible_count=eligible_count,
                    coverage=coverage,
                    status="skipped_valid",
                )
            else:
                from paperforge.worker.ocr_blocks import write_raw_blocks_jsonl
                from paperforge.worker.ocr_pdf_spans import backfill_span_metadata_from_pdf

                backfill_span_metadata_from_pdf(all_raw_blocks, source_pdf_path)
                covered_count, eligible_count, coverage = _compute_span_backfill_coverage(all_raw_blocks)
                write_raw_blocks_jsonl(artifacts.blocks_raw, all_raw_blocks)
                span_meta_patch = _update_span_validity_meta(
                    ocr_meta,
                    fingerprint=current_fp,
                    covered_count=covered_count,
                    eligible_count=eligible_count,
                    coverage=coverage,
                    status="rerun_backfill",
                )

        return {"span_meta_patch": span_meta_patch, "source_pdf_path": source_pdf_path}

    # ── Phase 2: PDF lines, enrich meta, build structured blocks ──
    def _phase2_build_structured(source_pdf_path: Path | None) -> dict:
        """Extract PDF lines, enrich source metadata, build structured blocks.
        Returns {structured, doc_structure, resolved, source_meta, page_pdf_lines_by_page}."""
        from paperforge.worker.ocr_pdf_spans import extract_pdf_lines_normalized

        page_pdf_lines_by_page = extract_pdf_lines_normalized(source_pdf_path)

        _enrich_meta_from_paper_note(vault, key, artifacts.source_metadata)
        source_meta = read_json(artifacts.source_metadata) if artifacts.source_metadata.exists() else {}

        from paperforge.worker.ocr_blocks import build_structured_blocks, write_structured_blocks_jsonl

        structured, doc_structure = build_structured_blocks(
            all_raw_blocks,
            source_metadata=source_meta,
            structure_output_dir=artifacts.blocks_structured.parent,
        )

        from paperforge.worker.ocr_profiles import write_role_span_profiles

        write_role_span_profiles(structured, artifacts.blocks_structured.parent)

        from paperforge.worker.ocr_metadata import (
            extract_frontmatter_candidates_from_blocks,
            resolve_metadata,
            write_resolved_metadata,
        )

        metadata_dir = paper_root / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        frontmatter_candidates = extract_frontmatter_candidates_from_blocks(structured)
        resolved = resolve_metadata(
            source_meta,
            frontmatter_candidates,
            page_blocks=all_raw_blocks,
            structured_blocks=structured,
        )
        write_resolved_metadata(metadata_dir / "resolved_metadata.json", resolved)

        return {
            "structured": structured,
            "doc_structure": doc_structure,
            "resolved": resolved,
            "source_meta": source_meta,
            "page_pdf_lines_by_page": page_pdf_lines_by_page,
        }

    # ── Phase 3: figure/table inventories, bio passes, writebacks ──
    def _phase3_figure_tables(
        structured: list[dict],
        page_pdf_lines_by_page: dict[int, list[dict]],
        source_meta: dict,
    ) -> dict:
        """Build figure and table inventories, run bio passes, resolve conflicts."""
        from paperforge.worker.ocr_figures import (
            build_figure_inventory,
            write_back_figure_roles,
            write_figure_inventory,
        )

        figure_inventory = build_figure_inventory(structured, page_pdf_lines_by_page=page_pdf_lines_by_page)
        write_back_figure_roles(figure_inventory, structured)

        from paperforge.worker.ocr_bio import (
            residual_author_bio_pass,
            post_ref_bio_cleanup,
            prune_figure_inventory_after_bio,
            _resolve_ref_start_page,
        )
        residual_author_bio_pass(
            figure_inventory, structured,
            include_ambiguous=False, include_weak_matched=False,
        )
        ref_start_page = _resolve_ref_start_page(structured)
        if ref_start_page is not None:
            post_ref_bio_cleanup(figure_inventory, structured, ref_start_page=ref_start_page)
            prune_figure_inventory_after_bio(figure_inventory)

        from paperforge.worker.ocr_figure_reader import synthesize_reader_figures

        reader_payload = synthesize_reader_figures(figure_inventory, structured_blocks=structured)
        reader_figures_dir = paper_root / "structure"
        reader_figures_dir.mkdir(parents=True, exist_ok=True)
        write_json(reader_figures_dir / "reader_figures.json", reader_payload)

        from paperforge.worker.ocr_tables import build_table_inventory, write_back_table_roles, write_table_inventory

        table_inventory = build_table_inventory(structured)
        from paperforge.worker.ocr_figures import attach_ownership_conflicts, resolve_media_asset_conflicts

        resolve_media_asset_conflicts(figure_inventory, table_inventory)
        attach_ownership_conflicts(figure_inventory, table_inventory)

        from paperforge.worker.ocr_object_writeback import apply_object_writebacks

        apply_object_writebacks(
            structured_blocks=structured,
            figure_inventory=figure_inventory,
            table_inventory=table_inventory,
        )

        write_figure_inventory(artifacts.blocks_structured.parent / "figure_inventory.json", figure_inventory)
        write_back_table_roles(table_inventory, structured)
        write_table_inventory(artifacts.blocks_structured.parent / "table_inventory.json", table_inventory)

        # ponytail: writes entire list again; if throughput matters, write only changed blocks
        from paperforge.worker.ocr_blocks import write_structured_blocks_jsonl as _write_structured_blocks_jsonl
        _write_structured_blocks_jsonl(artifacts.blocks_structured, structured)

        return {
            "figure_inventory": figure_inventory,
            "table_inventory": table_inventory,
            "reader_payload": reader_payload,
        }

    # ── Phase 4: objects, render, health ──
    def _phase4_render_health(
        structured: list[dict],
        resolved: dict,
        figure_inventory: dict,
        table_inventory: dict,
        reader_payload: dict,
        doc_structure: dict,
        ocr_meta: dict,
        source_pdf_path: Path | None,
    ) -> str:
        """Extract object artifacts, render fulltext markdown, build health report.
        Returns markdown string."""
        from paperforge.worker.ocr_objects import extract_and_write_objects

        _source_pdf_path = Path(ocr_meta.get("source_pdf", "")) if ocr_meta.get("source_pdf") else None
        page_dimensions_by_page: dict[int, tuple[int, int]] = {}
        for block in structured:
            page = int(block.get("page", 0) or 0)
            width = int(block.get("page_width", 0) or 0)
            height = int(block.get("page_height", 0) or 0)
            if page and width and height and page not in page_dimensions_by_page:
                page_dimensions_by_page[page] = (width, height)

        extract_and_write_objects(
            pdf_path=_source_pdf_path,
            figure_inventory=figure_inventory,
            table_inventory=table_inventory,
            asset_root=paper_root / "assets",
            render_root=paper_root / "render",
            page_dimensions_by_page=page_dimensions_by_page,
            structured_blocks=structured,
        )

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

        from paperforge.worker.ocr_health import build_ocr_health, build_ocr_raw_integrity_health, write_ocr_health

        health_report = build_ocr_health(
            page_count=ocr_meta.get("page_count", 0),
            raw_blocks_count=len(all_raw_blocks),
            structured_blocks=structured,
            figure_inventory=figure_inventory,
            table_inventory=table_inventory,
            doc_structure=doc_structure,
            reader_payload=reader_payload,
            rendered_markdown=markdown,
        )
        health_report["ocr_raw_integrity"] = build_ocr_raw_integrity_health(all_raw_blocks)
        write_ocr_health(paper_root / "health", health_report)

        from paperforge.worker.ocr_decisions import collect_decisions, write_decision_log

        write_decision_log(paper_root / "health" / "decision_log.jsonl", collect_decisions(structured))

        return markdown

    # ── Phase 5: indexes, version flags, write meta ──
    def _phase5_finalize(
        resolved: dict,
        structured: list[dict],
        markdown: str,
        span_meta_patch: dict,
    ) -> None:
        """Rebuild indexes, apply version flags, write meta.json."""
        from paperforge.worker.ocr_index import build_role_indexes, write_role_index

        role_indexes = build_role_indexes(
            structured_blocks=structured,
            resolved_metadata=resolved,
        )
        write_role_index(paper_root / "index", role_indexes)

        from paperforge.retrieval.structure_tree import build_structure_tree, write_structure_tree

        structure_tree = build_structure_tree(structured)
        write_structure_tree(paper_root / "index", structure_tree)

        meta = ocr_meta
        meta.update(span_meta_patch)
        meta = _apply_post_rebuild_version_flags(meta)
        meta["ocr_status"] = "done"

        from paperforge.worker.ocr_render import write_render_outputs

        meta = write_render_outputs(
            render_root=paper_root / "render",
            user_fulltext=artifacts.compat_fulltext,
            markdown=markdown,
            meta=meta,
            rebuild_increment=True,
        )
        paths_dict = {"ocr": pipeline_paths(vault)["ocr"]}
        _status, _err = validate_ocr_meta(paths_dict, meta)
        meta["ocr_status"] = _status
        meta["error"] = _err if _err else ""
        write_json(artifacts.meta_json, meta)

    # ── Execute phases ──
    phase1_result = _phase1_span_backfill()
    span_meta_patch = phase1_result["span_meta_patch"]
    source_pdf_path = phase1_result["source_pdf_path"]

    phase2_result = _phase2_build_structured(source_pdf_path)
    structured = phase2_result["structured"]
    doc_structure = phase2_result["doc_structure"]
    resolved = phase2_result["resolved"]
    source_meta = phase2_result["source_meta"]
    page_pdf_lines_by_page = phase2_result["page_pdf_lines_by_page"]

    phase3_result = _phase3_figure_tables(structured, page_pdf_lines_by_page, source_meta)
    figure_inventory = phase3_result["figure_inventory"]
    table_inventory = phase3_result["table_inventory"]
    reader_payload = phase3_result["reader_payload"]

    markdown = _phase4_render_health(
        structured, resolved, figure_inventory, table_inventory,
        reader_payload, doc_structure, ocr_meta, source_pdf_path,
    )

    _phase5_finalize(resolved, structured, markdown, span_meta_patch)

    return {"key": key, "status": "ok"}


def _run_parallel_rebuild(vault: Path, keys: list[str], workers: int, checkpoint_dir: Path | None) -> list[dict]:
    """Run rebuild in parallel using a process pool."""
    from concurrent.futures import ProcessPoolExecutor, as_completed

    results: list[dict] = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_rebuild_one_paper, vault, k): k for k in keys}
        for future in as_completed(futures):
            key = futures[future]
            try:
                result = future.result()
                if result.get("status") == "ok":
                    _write_done_marker(checkpoint_dir, key)
                results.append(result)
            except Exception as e:
                results.append({"key": key, "status": "failed", "error": str(e)})
    return results


def run_derived_rebuild_for_keys(
    vault: Path,
    keys: list[str],
    progress_bar=None,
    checkpoint_dir: Path | None = None,
    parallel: int = 4,
) -> dict:
    """Run derived-layer rebuild for the given paper keys without raw OCR rerun.

    Rebuilds: structured blocks, metadata, figure/table inventories, objects,
    render outputs, and health — from stored raw blocks only.

    If checkpoint_dir is provided, .done.<key> marker files track progress so
    interrupted runs can skip completed work via --resume.

    Args:
        vault: Vault root path.
        keys: Paper keys to rebuild.
        progress_bar: Optional progress bar wrapper (tqdm-style).
        checkpoint_dir: Directory for .done.<key> completion markers.
        parallel: Number of parallel workers (0 = serial). Default 4.
    """
    keys = _filter_completed_keys(checkpoint_dir, keys)
    if not keys:
        return {"rebuild_count": 0}

    workers = int(parallel) if parallel else 0

    if workers > 0 and len(keys) > 1:
        results = _run_parallel_rebuild(vault, keys, workers, checkpoint_dir)
        return {"rebuild_count": sum(1 for r in results if r.get("status") == "ok")}

    rebuilt_count = 0
    keys_iter = progress_bar(keys, desc="OCR rebuild") if progress_bar else keys
    for key in keys_iter:
        result = _rebuild_one_paper(vault, key)
        if result.get("status") == "ok":
            rebuilt_count += 1
            _write_done_marker(checkpoint_dir, key)
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
                # Fallback: if authors still incomplete, read from formal-library.json
                if meta.get("authors_incomplete") or not meta.get("authors"):
                    index_path = paths.get("index")
                    if index_path and index_path.exists():
                        try:
                            idx_data = read_json(index_path)
                            idx_entry = next(
                                (e for e in (idx_data.get("items") or []) if e.get("zotero_key") == key),
                                None,
                            )
                            if idx_entry and idx_entry.get("authors"):
                                meta["authors"] = list(idx_entry["authors"])
                                meta.pop("authors_incomplete", None)
                                meta["authors_source"] = "formal_library"
                                changed = True
                        except Exception:
                            pass
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
