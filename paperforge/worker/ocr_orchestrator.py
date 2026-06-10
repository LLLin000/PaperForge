from __future__ import annotations

# NOTE: This module is not used in the OCR production path.
# Production OCR structure is owned by ocr_document.py, ocr_figures.py,
# ocr_tables.py, ocr_render.py, and ocr_health.py.
# Keep this module only for compatibility/experimental tests.
from dataclasses import dataclass


@dataclass
class BlockAnnotated:
    block: dict
    role: str = "unknown_structural"
    role_confidence: float = 0.0
    in_body_spine: bool = False


def _bbox_order_key(block: dict) -> tuple:
    bbox = block.get("block_bbox", [0, 0, 0, 0])
    return (int(bbox[1]), int(bbox[0]))


def _bbox_top(block: dict) -> int:
    return int(block.get("block_bbox", [0, 0, 0, 0])[1])


def _bbox_bottom(block: dict) -> int:
    return int(block.get("block_bbox", [0, 0, 0, 0])[3])


def reorder_blocks_layered(
    blocks: list[dict],
    page_width: int = 0,
    page_height: int = 0,
) -> list[dict]:
    """Layout-aware body reordering.

    Note: Full body spine reordering is unavailable (ocr_body_spine
    module was removed). This function is preserved for signature
    compatibility; callers use the column-major fallback in
    _apply_layered_body_reorder instead.
    """
    return blocks
