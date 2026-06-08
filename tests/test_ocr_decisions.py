from __future__ import annotations

import json


def test_record_decision_attaches_normalized_entry() -> None:
    from paperforge.worker.ocr_decisions import record_decision

    block = {"block_id": "p1_b1", "page": 1, "bbox": [1, 2, 3, 4], "role": "body_paragraph"}
    record_decision(
        block,
        stage="candidate_resolution",
        old_role="figure_caption_candidate",
        new_role="body_paragraph",
        reason="body prose likelihood exceeded caption evidence",
        confidence=0.82,
        evidence=["body_prose", "not_near_media"],
    )
    entry = block["_decision_log"][0]
    assert entry["block_id"] == "p1_b1"
    assert entry["page"] == 1
    assert entry["bbox"] == [1, 2, 3, 4]
    assert entry["stage"] == "candidate_resolution"
    assert entry["old_role"] == "figure_caption_candidate"
    assert entry["new_role"] == "body_paragraph"
    assert entry["confidence"] == 0.82
    assert entry["evidence"] == ["body_prose", "not_near_media"]


def test_collect_decisions_flattens_block_logs() -> None:
    from paperforge.worker.ocr_decisions import collect_decisions, record_decision

    blocks = [{"block_id": "a", "page": 1, "bbox": [0, 0, 1, 1], "role": "body_paragraph"}]
    record_decision(blocks[0], stage="rescue", old_role="noise", new_role="body_paragraph", reason="body family match")
    assert len(collect_decisions(blocks)) == 1


def test_strip_decision_logs_removes_internal_logs_without_mutating_source() -> None:
    from paperforge.worker.ocr_decisions import record_decision, strip_decision_logs

    blocks = [{"block_id": "a", "page": 1, "bbox": [0, 0, 1, 1], "role": "body_paragraph"}]
    record_decision(blocks[0], stage="rescue", old_role="noise", new_role="body_paragraph", reason="body family match")
    stripped = strip_decision_logs(blocks)
    assert "_decision_log" in blocks[0]
    assert "_decision_log" not in stripped[0]


def test_build_structured_blocks_records_seed_role_decision() -> None:
    from paperforge.worker.ocr_blocks import build_structured_blocks

    raw = [{"block_id": "p1_b1", "paper_id": "test", "page": 1, "raw_label": "doc_title", "text": "A Study Title Long Enough", "bbox": [100, 50, 700, 90]}]
    structured, _ = build_structured_blocks(raw)
    assert structured[0].get("_decision_log")
    assert structured[0]["_decision_log"][0]["stage"] == "assign_block_role"
    assert structured[0]["_decision_log"][0]["new_role"] == "paper_title"


def test_write_structured_blocks_jsonl_strips_decision_log(tmp_path) -> None:
    from paperforge.worker.ocr_blocks import write_structured_blocks_jsonl
    from paperforge.worker.ocr_decisions import record_decision

    blocks = [{"block_id": "a", "page": 1, "bbox": [0, 0, 1, 1], "role": "body_paragraph"}]
    record_decision(blocks[0], stage="rescue", old_role="noise", new_role="body_paragraph", reason="body family match")
    path = tmp_path / "blocks.structured.jsonl"
    write_structured_blocks_jsonl(path, blocks)
    import json
    with open(path, "r", encoding="utf-8") as f:
        data = json.loads(f.readline())
    assert "_decision_log" not in data
