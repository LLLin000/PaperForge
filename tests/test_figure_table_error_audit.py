from __future__ import annotations

from scripts.dev.figure_table_error_audit import bucket, build_cases


def test_bucket_boundaries() -> None:
    assert [bucket(value) for value in (0.03, 0.05, 0.051, 0.15, 0.151)] == [
        "2-5%", "2-5%", "5-15%", "5-15%", ">15%"
    ]


def test_quota_order_and_duplicate_identity_use_geometry() -> None:
    blocks = [
        {"page": 1, "block_id": "same", "bbox": [0, 10, 30, 20], "page_height": 100,
         "role": "figure_caption", "text": "Fig 1"},
        {"page": 1, "block_id": "same", "bbox": [0, 50, 30, 60], "page_height": 100,
         "role": "figure_caption", "text": "Fig 2"},
        {"page": 1, "block_id": "asset", "bbox": [0, 70, 30, 80], "role": "media_asset"},
    ]
    plan = {"pages": [{"page": 1, "regions": [{"kind": "column", "members": ["p1:0000", "p1:0001"]}]}]}
    evaluation = {"figure_caption": {"suspicious": [
        {"page": 1, "caption": "p1:0001", "asset": "p1:0002", "distance_ratio": 0.2,
         "caption_bbox": [0, 50, 30, 60], "asset_bbox": [0, 70, 30, 80]},
        {"page": 1, "caption": "p1:0000", "asset": "p1:0002", "distance_ratio": 0.04,
         "caption_bbox": [0, 10, 30, 20], "asset_bbox": [0, 70, 30, 80]},
    ]}}
    args = ("PAPER", blocks, {"matched_figures": []}, {"tables": []}, plan, evaluation)
    first = build_cases(*args, per_stratum=1)
    second = build_cases(*args, per_stratum=1)
    assert first == second
    assert [(case["stratum"], case["caption"]["text"]) for case in first] == [
        ("2-5%", "Fig 1"), (">15%", "Fig 2")
    ]
    assert first[1]["layout_region_kind"] == "column"
    assert first[0]["candidate_assets"] == [{"id": "asset", "bbox": [0, 70, 30, 80], "role": "media_asset"}]


def test_record_shape_includes_null_provenance_and_unreviewed_case() -> None:
    blocks = [{"page": 2, "block_id": "cap", "bbox": [1, 2, 20, 10],
               "page_height": 100, "role": "table_caption", "text": "Table 1"}]
    cases = build_cases("PAPER", blocks, {}, {"tables": [{"page": 2, "caption_block_id": "cap"}]},
                        {"pages": []}, {"figure_caption": {"suspicious": []}})
    assert len(cases) == 1
    case = cases[0]
    assert case["stratum"] == "table"
    assert case["caption"] == {"id": "cap", "bbox": [1, 2, 20, 10], "text": "Table 1"}
    assert case["inventory_state"] == {"matched_figure_id": None, "state": "unmatched"}
    assert {key: case[key] for key in ("match_pass", "score", "status", "evidence")} == {
        "match_pass": None, "score": None, "status": None, "evidence": None
    }
