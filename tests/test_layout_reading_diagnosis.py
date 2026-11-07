from __future__ import annotations

from types import SimpleNamespace

from scripts.dev.layout_reading_diagnosis import classify_pages


def _case(order, *, accepted=True, role=None, events=("a", "b"), container=False):
    blocks = [
        {"page": 1, "block_id": "a", "bbox": [0, 0, 10, 10], "text": "alpha", "role": role},
        {"page": 1, "block_id": "b", "bbox": [0, 20, 10, 30], "text": "beta"},
    ]
    region = SimpleNamespace(kind="container") if container else SimpleNamespace(kind="column")
    plan_order = ["uid-a", "uid-b"] if order == [0, 1] else ["uid-b", "uid-a"]
    page = SimpleNamespace(page=1, regions=[region], order=plan_order)
    plan = SimpleNamespace(pages=[page])
    gate = SimpleNamespace(
        page=1,
        accepted=accepted,
        accepted_order=["uid-a", "uid-b"] if order == [0, 1] else ["uid-b", "uid-a"],
        source_mapping={"uid-a": 0, "uid-b": 1},
        fallback_reason=None if accepted else "low_confidence",
        held_blocks=["uid-a"] if not accepted else [],
        evidence={"confidence": 0.75},
    )
    emitted = [{"page": 1, "block_id": item} for item in events]
    return blocks, plan, [gate], emitted


def test_already_correct():
    assert classify_pages(*_case([0, 1]))[0]["category"] == "already_correct"


def test_gate_blocked():
    page = classify_pages(*_case([1, 0], accepted=False))[0]
    assert page["category"] == "gate_blocked"
    assert page["fallback_reason"] == "low_confidence"


def test_scope_blocked():
    assert classify_pages(*_case([1, 0], role="reference_item"))[0]["category"] == "scope_blocked"


def test_non_emitting_only():
    # Layout swap changes suppressed b/a input positions, but only a is emitted.
    assert classify_pages(*_case([1, 0], events=("a",)))[0]["category"] == "non_emitting_only"


def test_real_change_candidate():
    page = classify_pages(*_case([1, 0]))[0]
    assert page["category"] == "real_change_candidate"
    assert [block["block_id"] for block in page["blocks"]] == ["a", "b"]
