from __future__ import annotations


class FakeNode:
    def __init__(self, node_id, node_type, text="", bbox=(0, 0, 0, 0)):
        self.node_id = node_id
        self.node_type = node_type
        self.text = text
        self.bbox = bbox


def test_two_column_body_zone_orders_left_then_right_when_semantically_continuous() -> None:
    from paperforge.worker.ocr_layout import detect_layout_zones, order_body_spine

    nodes = [
        FakeNode("L1", "paragraph", "Left intro", (80, 100, 500, 160)),
        FakeNode("R1", "paragraph", "Right intro", (700, 110, 1120, 170)),
        FakeNode("L2", "paragraph", "Left methods", (80, 200, 500, 260)),
        FakeNode("R2", "paragraph", "Right methods", (700, 210, 1120, 270)),
    ]

    zones = detect_layout_zones(nodes, page_width=1200, page_height=1600)
    ordered = order_body_spine(nodes, zones, mode="column_major")

    assert [node.node_id for node in ordered] == ["L1", "L2", "R1", "R2"]


def test_zone_detects_two_column_from_body_nodes() -> None:
    from paperforge.worker.ocr_layout import detect_layout_zones

    nodes = [
        FakeNode("L1", "paragraph", "a", (80, 100, 500, 160)),
        FakeNode("R1", "paragraph", "b", (700, 110, 1120, 170)),
    ]

    zones = detect_layout_zones(nodes, page_width=1200, page_height=1600)

    assert len(zones) == 1
    assert zones[0].regime_type == "two_col"


def test_zone_detects_single_column() -> None:
    from paperforge.worker.ocr_layout import detect_layout_zones

    nodes = [
        FakeNode("L1", "paragraph", "a", (100, 80, 1100, 200)),
    ]

    zones = detect_layout_zones(nodes, page_width=1200, page_height=1600)

    assert zones[0].regime_type == "single_col"


def test_default_mode_preserves_original_order() -> None:
    from paperforge.worker.ocr_layout import detect_layout_zones, order_body_spine

    nodes = [
        FakeNode("A", "paragraph", "first", (80, 100, 500, 160)),
        FakeNode("C", "paragraph", "third", (700, 200, 1120, 260)),
        FakeNode("B", "paragraph", "second", (80, 300, 500, 360)),
    ]

    zones = detect_layout_zones(nodes, page_width=1200, page_height=1600)
    ordered = order_body_spine(nodes, zones, mode="prior_preserving")

    assert [node.node_id for node in ordered] == ["A", "C", "B"]
