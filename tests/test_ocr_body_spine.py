from __future__ import annotations


def test_body_spine_excludes_figure_captions_and_media() -> None:
    from paperforge.worker.ocr_body_spine import extract_body_spine

    class FakeRole:
        def __init__(self, role, text="", bbox=(0, 0, 0, 0), confidence=0.5, block_id=0):
            self.role = role
            self.text = text
            self.bbox = bbox
            self.confidence = confidence
            self.block_id = block_id

    blocks = [
        FakeRole("section_heading", "5 In vitro PEMF studies", (94, 1328, 387, 1356)),
        FakeRole("body_paragraph", "Over the past few decades...", (92, 1382, 586, 1525)),
        FakeRole("figure_caption", "FIGURE 4", (208, 176, 982, 236)),
        FakeRole("media_asset", "", (208, 176, 982, 714)),
    ]

    spine, non_body = extract_body_spine(blocks)

    assert [node.node_type for node in spine] == ["section_heading", "paragraph"]
    assert len(non_body) == 2


def test_heading_retained_even_when_short() -> None:
    from paperforge.worker.ocr_body_spine import extract_body_spine

    class FakeRole:
        def __init__(self, role, text="", bbox=(0, 0, 0, 0), confidence=0.5, block_id=0):
            self.role = role
            self.text = text
            self.bbox = bbox
            self.confidence = confidence
            self.block_id = block_id

    blocks = [
        FakeRole("subsection_heading", "5.1 Bone", (606, 732, 709, 759)),
        FakeRole("body_paragraph", "For investigating the effects...", (603, 785, 1096, 951)),
    ]

    spine, non_body = extract_body_spine(blocks)

    assert len(spine) == 2
    assert spine[0].node_type == "subsection_heading"


def test_unknown_structural_stays_out_of_spine() -> None:
    from paperforge.worker.ocr_body_spine import extract_body_spine

    class FakeRole:
        def __init__(self, role, text="", bbox=(0, 0, 0, 0), confidence=0.5, block_id=0):
            self.role = role
            self.text = text
            self.bbox = bbox
            self.confidence = confidence
            self.block_id = block_id

    blocks = [
        FakeRole("body_paragraph", "some text"),
        FakeRole("unknown_structural", "ambiguous"),
    ]

    spine, non_body = extract_body_spine(blocks)

    assert len(spine) == 1
    assert len(non_body) == 1
