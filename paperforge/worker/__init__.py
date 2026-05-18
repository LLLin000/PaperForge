"""PaperForge worker modules — migrated from pipeline/worker/scripts."""

from __future__ import annotations

import importlib
from typing import Any

_MODULE_MAP: dict[str, str] = {
    "load_export_rows": "paperforge.worker.sync",
    "run_selection_sync": "paperforge.worker.sync",
    "run_index_refresh": "paperforge.worker.sync",
    "run_ocr": "paperforge.worker.ocr",
    "run_repair": "paperforge.worker.repair",
    "run_doctor": "paperforge.worker.status",
    "run_status": "paperforge.worker.status",
    "run_deep_reading": "paperforge.worker.deep_reading",
    "build_base_views": "paperforge.worker.base_views",
    "merge_base_views": "paperforge.worker.base_views",
    "ensure_base_views": "paperforge.worker.base_views",
    "obsidian_wikilink_for_pdf": "paperforge.worker.sync",
    "absolutize_vault_path": "paperforge.worker.sync",
    "_normalize_attachment_path": "paperforge.worker.sync",
    "_identify_main_pdf": "paperforge.worker.sync",
}

__all__ = list(_MODULE_MAP.keys())


def __getattr__(name: str) -> Any:
    """Lazy-import worker functions to avoid circular / broken import chains."""
    if name in _MODULE_MAP:
        mod = importlib.import_module(_MODULE_MAP[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
