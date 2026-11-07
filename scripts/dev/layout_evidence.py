"""Shared read-only evidence builder: the blocks the production renderer sees.

This mirrors the *derived rebuild* phase chain
(`paperforge/worker/ocr_rebuild.py::_rebuild_one_paper`, phases 2–3) in memory,
without writing anything. All read-only audits in this round consume it, so
they compare the same input the renderer actually gets.

Known divergence, deliberate: `_enrich_meta_from_paper_note` writes
`raw/source_metadata.json`; this builder never writes, so metadata enrichment
is skipped. `scripts/dev/layout_evidence_parity.py` reports whether that
changes the final rows.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FinalView:
    key: str
    blocks: list[dict]
    document_structure: Any
    figure_inventory: dict[str, Any]
    table_inventory: dict[str, Any]
    reader_payload: dict[str, Any]
    metadata: dict[str, Any]
    trace: list[str] = field(default_factory=list)


def _load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_final_view(paper_dir: Path) -> FinalView:
    """Final structured blocks, inventories and document structure, in memory."""
    from paperforge.worker.ocr_blocks import build_structured_blocks
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures
    from paperforge.worker.ocr_figures import (
        attach_ownership_conflicts,
        build_figure_inventory,
        resolve_media_asset_conflicts,
        write_back_figure_roles,
    )
    from paperforge.worker.ocr_object_writeback import apply_object_writebacks
    from paperforge.worker.ocr_post_match_normalize import post_match_normalize
    from paperforge.worker.ocr_pre_match_normalize import pre_match_normalize
    from paperforge.worker.ocr_tables import build_table_inventory, write_back_table_roles

    trace: list[str] = []
    raw_blocks = _load_jsonl(paper_dir / "canonical" / "blocks.raw.jsonl")
    metadata = _load_json(paper_dir / "raw" / "source_metadata.json", {})
    trace.append("raw")

    blocks, document = build_structured_blocks(
        raw_blocks, source_metadata=metadata, normalize_mode="seed_only"
    )
    trace.append("structured:seed_only")

    anchors = getattr(document, "source_frontmatter_anchors", None)
    blocks, document = pre_match_normalize(
        blocks, source_frontmatter_anchors=anchors, document_structure=document
    )
    trace.append("pre_match")

    figures = build_figure_inventory(blocks)
    write_back_figure_roles(figures, blocks)
    trace.append("figures:matching+roles")

    from paperforge.worker.ocr_bio import (
        _resolve_ref_start_page,
        post_ref_bio_cleanup,
        prune_figure_inventory_after_bio,
        residual_author_bio_pass,
    )

    residual_author_bio_pass(figures, blocks, include_ambiguous=False, include_weak_matched=False)
    ref_start_page = _resolve_ref_start_page(blocks)
    if ref_start_page is not None:
        post_ref_bio_cleanup(figures, blocks, ref_start_page=ref_start_page)
        prune_figure_inventory_after_bio(figures)
    trace.append("figures:bio_cleanup")

    reader_payload = synthesize_reader_figures(figures, structured_blocks=blocks)
    trace.append("figures:reader_payload")

    tables = build_table_inventory(blocks)
    resolve_media_asset_conflicts(figures, tables)
    attach_ownership_conflicts(figures, tables)
    trace.append("tables+conflicts")

    blocks, document = post_match_normalize(
        blocks,
        figures,
        tables,
        document_structure=document,
        source_frontmatter_anchors=anchors,
    )
    trace.append("post_match")

    apply_object_writebacks(structured_blocks=blocks, figure_inventory=figures, table_inventory=tables)
    write_back_table_roles(tables, blocks)
    trace.append("writeback")

    return FinalView(
        key=paper_dir.name,
        blocks=blocks,
        document_structure=document,
        figure_inventory=figures,
        table_inventory=tables,
        reader_payload=reader_payload,
        metadata=metadata,
        trace=trace,
    )
