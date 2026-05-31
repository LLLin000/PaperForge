from __future__ import annotations

import json
from pathlib import Path


def test_fixture_inventory_has_required_failure_classes() -> None:
    inventory_path = Path("tests/fixtures/ocr_reading_order/fixture_inventory.json")
    data = json.loads(inventory_path.read_text(encoding="utf-8"))

    required_classes = {
        "raw_interleave",
        "mixed_body_media",
        "heading_media_mix",
        "cross_column_body",
        "multi_heading_multicol",
        "session_regression_7C8829BD",
    }

    assert required_classes.issubset(set(data["classes"].keys()))
