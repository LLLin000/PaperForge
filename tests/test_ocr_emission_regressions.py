from __future__ import annotations


def test_emission_keeps_headings_in_markdown() -> None:
    from paperforge.worker.ocr_emit import emit_page_markdown

    class Node:
        def __init__(self, node_id, node_type, text=""):
            self.node_id = node_id
            self.node_type = node_type
            self.text = text

    spine = [
        Node("h1", "section_heading", "5 In vitro PEMF studies"),
        Node("p1", "paragraph", "Over the past few decades..."),
    ]

    result = emit_page_markdown(7, spine, [])

    assert "### 5 In vitro PEMF studies" in result
    assert "<!-- page 7 -->" in result
    assert "Over the past few decades..." in result


def test_emission_preserves_page_marker() -> None:
    from paperforge.worker.ocr_emit import emit_page_markdown

    result = emit_page_markdown(14, [], [])

    assert result.startswith("<!-- page 14 -->")


def test_emission_handles_empty_input() -> None:
    from paperforge.worker.ocr_emit import emit_page_markdown

    result = emit_page_markdown(1, [], [])

    assert "<!-- page 1 -->" in result


def test_emission_attachments_referenced_near_anchor() -> None:
    from paperforge.worker.ocr_emit import emit_page_markdown

    class Node:
        def __init__(self, node_id, node_type, text=""):
            self.node_id = node_id
            self.node_type = node_type
            self.text = text

    class Att:
        def __init__(self, attachment_id, kind, anchor_node_id):
            self.attachment_id = attachment_id
            self.kind = kind
            self.anchor_node_id = anchor_node_id

    spine = [
        Node("sec-6-1", "section_heading", "6.1 Bone"),
    ]
    attachments = [
        Att("a1", "figure", "sec-6-1"),
    ]

    result = emit_page_markdown(14, spine, attachments)

    assert "### 6.1 Bone" in result
    assert "[FIGURE attached: a1]" in result
