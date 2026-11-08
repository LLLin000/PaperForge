"""One figure/table association sequence for every producer.

First parse, derived rebuild and the read-only evidence builder used to run
slightly different sequences: first parse skipped `write_back_figure_roles`,
`resolve_media_asset_conflicts`, `attach_ownership_conflicts` and the explicit
table role writeback, while rebuild ran all of them. That is how the same page
could end up with different ownership depending on which path wrote it last
(`2BYRLKQS` p4: the table kept a figure asset in first parse).

This module owns the order. Callers keep their own persistence (files, reader
payload, hashes); they must not re-order these calls.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ObjectStageResult:
    figures: dict
    tables: dict
    reader_payload: dict


def run_association_stage(
    structured: list[dict],
    *,
    page_pdf_lines_by_page: dict[int, list[dict]] | None = None,
) -> ObjectStageResult:
    """Match figures/tables and resolve their conflicts. Mutates roles, not files."""
    from paperforge.worker.ocr_bio import (
        _resolve_ref_start_page,
        post_ref_bio_cleanup,
        prune_figure_inventory_after_bio,
        residual_author_bio_pass,
    )
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures
    from paperforge.worker.ocr_figures import (
        attach_ownership_conflicts,
        build_figure_inventory,
        resolve_media_asset_conflicts,
        write_back_figure_roles,
    )
    from paperforge.worker.ocr_tables import build_table_inventory

    figures = build_figure_inventory(structured, page_pdf_lines_by_page=page_pdf_lines_by_page)
    # Early role promotion: the post-match stage must see figure_asset roles, and
    # the bio passes must see the promoted captions.
    write_back_figure_roles(figures, structured)

    residual_author_bio_pass(figures, structured, include_ambiguous=False, include_weak_matched=False)
    ref_start_page = _resolve_ref_start_page(structured)
    if ref_start_page is not None:
        post_ref_bio_cleanup(figures, structured, ref_start_page=ref_start_page)
        prune_figure_inventory_after_bio(figures)

    tables = build_table_inventory(structured)
    # Reader synthesis consumes the inventory after conflict arbitration.
    resolve_media_asset_conflicts(figures, tables, structured=structured)
    attach_ownership_conflicts(figures, tables)
    reader_payload = synthesize_reader_figures(figures, structured_blocks=structured)
    return ObjectStageResult(figures=figures, tables=tables, reader_payload=reader_payload)


def commit_object_roles(structured: list[dict], figures: dict, tables: dict) -> None:
    """Apply the resolved ownership to block roles. `apply_object_writebacks` is
    the single consumer of object claims; the table role writeback is the table
    counterpart and must run after it."""
    from paperforge.worker.ocr_object_writeback import apply_object_writebacks
    from paperforge.worker.ocr_tables import write_back_table_roles

    apply_object_writebacks(structured_blocks=structured, figure_inventory=figures, table_inventory=tables)
    write_back_table_roles(tables, structured)
