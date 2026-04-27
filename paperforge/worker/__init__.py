"""PaperForge worker modules — migrated from pipeline/worker/scripts."""

from paperforge.worker.base_views import build_base_views, ensure_base_views, merge_base_views
from paperforge.worker.deep_reading import run_deep_reading
from paperforge.worker.ocr import run_ocr
from paperforge.worker.repair import run_repair
from paperforge.worker.status import run_doctor, run_status
from paperforge.worker.sync import (
    _identify_main_pdf,
    _normalize_attachment_path,
    absolutize_vault_path,
    load_export_rows,
    obsidian_wikilink_for_pdf,
    run_index_refresh,
    run_selection_sync,
)

__all__ = [
    "load_export_rows",
    "run_selection_sync",
    "run_index_refresh",
    "run_ocr",
    "run_repair",
    "run_doctor",
    "run_status",
    "run_deep_reading",
    "build_base_views",
    "merge_base_views",
    "ensure_base_views",
    "obsidian_wikilink_for_pdf",
    "absolutize_vault_path",
    "_normalize_attachment_path",
    "_identify_main_pdf",
]
