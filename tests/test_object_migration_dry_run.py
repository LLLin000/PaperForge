"""Identity/claims diff used by the migration dry-run."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "object_migration_dry_run",
    Path(__file__).resolve().parents[1] / "scripts/dev/object_migration_dry_run.py",
)
assert _SPEC and _SPEC.loader
module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(module)


def test_identity_diff_maps_by_page_and_legend_anchor() -> None:
    old = {
        "entries": 3,
        "ids": ["figure_002", "figure_002", "figure_003"],
        "duplicate_extra": 1,
        "anchors": {(4, "9"): "figure_002", (4, "10"): "figure_002", (5, "2"): "figure_003"},
        "claims": {"figure_002": ["8"], "figure_003": ["3"]},
    }
    new = [
        {"figure_id": "figure_002", "page": 4, "legend_block_id": "9", "matched_assets": [{"block_id": "8"}]},
        {"figure_id": "figure_002_10", "page": 4, "legend_block_id": "10", "matched_assets": [{"block_id": "4"}]},
        {"figure_id": "figure_003", "page": 5, "legend_block_id": "2", "matched_assets": [{"block_id": "3"}]},
    ]
    diff = module._identity_diff(old, new)
    assert diff["new"]["entries"] == 3
    assert diff["new"]["duplicate_extra"] == 0
    assert ["figure_002", "figure_002_10"] in diff["renamed"]
    assert diff["claims_changed"][0]["new_assets"] == ["4"]
