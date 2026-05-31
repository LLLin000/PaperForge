from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BodySpineNode:
    node_id: str
    node_type: str
    text: str = ""
    bbox: tuple[int, int, int, int] = (0, 0, 0, 0)
    role_confidence: float = 0.5
    block_ids: list = field(default_factory=list)


def _attr(obj, name, default=None):
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


def extract_body_spine(role_assignments: list) -> tuple[list[BodySpineNode], list]:
    spine: list[BodySpineNode] = []
    non_body: list = []

    for i, item in enumerate(role_assignments):
        role = _attr(item, "role", "unknown_structural")

        if role in {"section_heading", "subsection_heading"}:
            spine.append(
                BodySpineNode(
                    node_id=f"spine-{i}",
                    node_type=role,
                    text=_attr(item, "text", ""),
                    bbox=tuple(_attr(item, "bbox", (0, 0, 0, 0))),
                    role_confidence=_attr(item, "confidence", 0.5),
                    block_ids=[_attr(item, "block_id", i)],
                )
            )
        elif role == "body_paragraph":
            spine.append(
                BodySpineNode(
                    node_id=f"spine-{i}",
                    node_type="paragraph",
                    text=_attr(item, "text", ""),
                    bbox=tuple(_attr(item, "bbox", (0, 0, 0, 0))),
                    role_confidence=_attr(item, "confidence", 0.5),
                    block_ids=[_attr(item, "block_id", i)],
                )
            )
        else:
            non_body.append(item)

    return spine, non_body
