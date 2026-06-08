from __future__ import annotations

# NOTE: This module is not used in the OCR production path.
# Production OCR structure is owned by ocr_document.py, ocr_figures.py,
# ocr_tables.py, ocr_render.py, and ocr_health.py.
# Keep this module only for compatibility/experimental tests.

from dataclasses import dataclass, field


@dataclass
class Attachment:
    attachment_id: str
    kind: str
    source_block_ids: list[int | str] = field(default_factory=list)
    caption_block_ids: list[int | str] = field(default_factory=list)
    anchor_node_id: str | None = None
    anchor_section_path: list[str] = field(default_factory=list)
    attachment_confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)


def _attr(obj, name, default=None):
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


def _bbox_y_center(bbox):
    return (bbox[1] + bbox[3]) / 2


def _bbox_distance(a, b):
    return abs(_bbox_y_center(a) - _bbox_y_center(b))


def build_attachment_graph(
    spine: list,
    non_body: list,
    page_width: int = 0,
    page_height: int = 0,
) -> list[Attachment]:
    attachments: list[Attachment] = []
    media_blocks = []
    caption_blocks = []

    for item in non_body:
        role = _attr(item, "role", "unknown")
        if role == "media_asset":
            media_blocks.append(item)
        elif role in ("figure_caption", "table_caption"):
            caption_blocks.append(item)

    paired_media_ids: set[int | str] = set()

    for caption in caption_blocks:
        cap_bbox = tuple(_attr(caption, "bbox", (0, 0, 0, 0)))
        best_media = None
        best_distance = float("inf")

        for media in media_blocks:
            mid = _attr(media, "block_id", id(media))
            if mid in paired_media_ids:
                continue
            med_bbox = tuple(_attr(media, "bbox", (0, 0, 0, 0)))
            distance = _bbox_distance(cap_bbox, med_bbox)
            if distance < best_distance:
                best_distance = distance
                best_media = media

        if best_media is not None:
            mid = _attr(best_media, "block_id", id(best_media))
            paired_media_ids.add(mid)

            anchor = None
            if spine:
                anchor = _attr(spine[0], "node_id", "")
            anchor_section = []
            for node in spine:
                if _attr(node, "node_type", "") in ("section_heading", "subsection_heading"):
                    anchor_section.append(_attr(node, "text", ""))

            attachments.append(
                Attachment(
                    attachment_id=f"attach-{len(attachments)}",
                    kind="figure",
                    source_block_ids=[_attr(best_media, "block_id", 0)],
                    caption_block_ids=[_attr(caption, "block_id", 0)],
                    anchor_node_id=anchor,
                    anchor_section_path=anchor_section,
                    attachment_confidence=0.5,
                    evidence=[f"caption-media pair at distance {best_distance:.0f}"],
                )
            )

    return attachments
