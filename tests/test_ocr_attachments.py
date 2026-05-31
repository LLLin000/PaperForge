from __future__ import annotations


class FakeSpineNode:
    def __init__(self, node_id, node_type, text="", bbox=(0, 0, 0, 0)):
        self.node_id = node_id
        self.node_type = node_type
        self.text = text
        self.bbox = bbox


class FakeNonBody:
    def __init__(self, role, text="", bbox=(0, 0, 0, 0), block_id=0):
        self.role = role
        self.text = text
        self.bbox = bbox
        self.block_id = block_id


def test_figure_attaches_to_body_anchor_without_reordering_body() -> None:
    from paperforge.worker.ocr_attach import build_attachment_graph

    spine = [
        FakeSpineNode("sec-6-1", "section_heading", "6.1 Bone", (80, 100, 260, 130)),
        FakeSpineNode("p-1", "paragraph", "As regards the treatment of bone fractures...", (80, 150, 500, 260)),
    ]
    non_body = [
        FakeNonBody("media_asset", "", (208, 176, 982, 714), block_id=100),
        FakeNonBody("figure_caption", "FIGURE 4 Distribution of... cartilage cells/tissues.", (208, 716, 982, 820), block_id=101),
    ]

    attachments = build_attachment_graph(spine, non_body, page_width=1200, page_height=1600)

    assert len(attachments) == 1
    assert attachments[0].kind == "figure"
    assert attachments[0].anchor_node_id == "sec-6-1"


def test_empty_non_body_produces_no_attachments() -> None:
    from paperforge.worker.ocr_attach import build_attachment_graph

    spine = [FakeSpineNode("n1", "paragraph", "text")]
    non_body = []

    attachments = build_attachment_graph(spine, non_body)

    assert len(attachments) == 0
