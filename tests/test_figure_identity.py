from paperforge.worker.ocr_figures import _extract_figure_marker, _finalize_figure_identities


def _entry(text: str, block: str, asset: str, *, page: int = 1, **extra) -> dict:
    return {
        "text": text,
        "legend_block_id": block,
        "page": page,
        "matched_assets": [{"block_id": asset, "bbox": [1, 1, 10, 10]}],
        "asset_block_ids": [asset],
        **extra,
    }


def test_compound_labels_have_readable_ids_and_keep_legacy_number() -> None:
    first = _extract_figure_marker("Figure 11-1: caption")
    second = _extract_figure_marker("Figure 11-2: caption")
    chinese = _extract_figure_marker("图 5-1 caption")
    assert (first["figure_label"], first["display_label"], first["number"]) == ("11-1", "Figure 11-1", 11)
    assert second["figure_label"] == "11-2"
    assert (chinese["figure_label"], chinese["display_label"]) == ("5-1", "图 5-1")

    inventory = {"matched_figures": [_entry("Figure 11-1: a", "b1", "a1"), _entry("Figure 11-2: b", "b2", "a2")]}
    _finalize_figure_identities(inventory)
    figures = inventory["matched_figures"]
    assert [f["figure_id"] for f in figures] == ["figure_011_1", "figure_011_2"]
    assert [f"assets/figures/{f['figure_id']}.jpg" for f in figures][0] != [f"assets/figures/{f['figure_id']}.jpg" for f in figures][1]
    assert all(f["figure_number"] == 11 and f["figure_namespace"] == "main" for f in figures)


def test_simple_label_keeps_legacy_id_and_caption_edits_do_not_rename() -> None:
    first = {"matched_figures": [_entry("Figure 1: caption", "p1_b1", "asset")]}
    corrected = {"matched_figures": [_entry(" Figure 1.   caption corrected ", "p1_b1", "asset")]}
    _finalize_figure_identities(first)
    _finalize_figure_identities(corrected)
    assert first["matched_figures"][0]["figure_id"] == "figure_001"
    assert corrected["matched_figures"][0]["figure_id"] == "figure_001"


def test_simple_namespace_ids_keep_legacy_names() -> None:
    inventory = {"matched_figures": [
        _entry("Supplementary Figure 4", "s", "sa"),
        _entry("Extended Data Figure 4", "e", "ea"),
        _entry("Fig. A4", "a", "aa"),
    ]}
    _finalize_figure_identities(inventory)
    assert [entry["figure_id"] for entry in inventory["matched_figures"]] == [
        "figure_s004", "figure_ed004", "figure_a004",
    ]

def test_duplicate_label_at_different_anchors_gets_anchor_qualified_id() -> None:
    entries = [
        _entry("Figure 2: first caption", "legend-1", "asset-1", page=1),
        _entry("Figure 2: second caption", "legend-2", "asset-2", page=2),
    ]
    first = {"matched_figures": [dict(entry) for entry in entries]}
    second = {"matched_figures": [dict(entry) for entry in entries]}
    _finalize_figure_identities(first)
    _finalize_figure_identities(second)
    ids = [entry["figure_id"] for entry in first["matched_figures"]]
    assert ids == ["figure_002", "figure_002_p002_blegend-2"]
    assert ids == [entry["figure_id"] for entry in second["matched_figures"]]
    assert first["identity_conflicts"][0]["status"] == "CONFLICT"


def test_repeated_caption_and_group_collapses_to_one_object() -> None:
    entry = _entry("Figure 3: repeated", "caption", "asset")
    duplicate = {**entry, "legend_block_id": "duplicate-caption"}
    inventory = {"matched_figures": [entry, duplicate]}
    _finalize_figure_identities(inventory)
    assert len(inventory["matched_figures"]) == 1
    assert inventory["identity_conflicts"] == []


def test_same_caption_with_multiple_groups_merges_assets() -> None:
    inventory = {"matched_figures": [
        _entry("Figure 4: same caption", "caption", "asset-a", group_id="group-a"),
        _entry("Figure 4: same caption", "caption", "asset-b", group_id="group-b"),
    ]}
    _finalize_figure_identities(inventory)
    assert len(inventory["matched_figures"]) == 1
    result = inventory["matched_figures"][0]
    assert {a["block_id"] for a in result["matched_assets"]} == {"asset-a", "asset-b"}
    assert set(result["merged_group_ids"]) == {"group-a", "group-b"}
    assert inventory["identity_conflicts"] == []


def test_empty_duplicate_claim_does_not_displace_asset_evidence() -> None:
    assetless = _entry("Figure 4: same caption", "caption", "")
    assetless["matched_assets"] = []
    assetless["asset_block_ids"] = []
    with_asset = _entry("Figure 4: same caption", "caption", "asset")
    inventory = {"matched_figures": [assetless, with_asset]}

    _finalize_figure_identities(inventory)

    result = inventory["matched_figures"][0]
    assert [asset["block_id"] for asset in result["matched_assets"]] == ["asset"]
    assert len(result["claims"]) == 2



def test_only_assetless_sequence_matches_are_held() -> None:
    sequence = _entry("Figure 5", "sequence-caption", "")
    sequence["matched_assets"] = []
    sequence["asset_block_ids"] = []
    sequence["settlement_type"] = "sequence_match"
    reservation = _entry("Figure 6", "reservation-caption", "")
    reservation["matched_assets"] = []
    reservation["asset_block_ids"] = []
    reservation["settlement_type"] = "cross_page_reservation"
    inventory = {"matched_figures": [sequence, reservation]}

    _finalize_figure_identities(inventory)

    assert [entry["settlement_type"] for entry in inventory["matched_figures"]] == ["cross_page_reservation"]
    assert inventory["held_figures"][0]["hold_reason"] == "assetless_sequence_match"

def test_strict_superset_asset_claim_keeps_specific_claim_and_records_overclaim() -> None:
    broad = _entry("Figure 4: same caption", "caption", "asset-a")
    broad["matched_assets"] = [{"block_id": f"asset-{i}", "bbox": [i, 1, i + 1, 10]} for i in range(4)]
    broad["asset_block_ids"] = [f"asset-{i}" for i in range(4)]
    specific = _entry("Figure 4: same caption", "caption", "asset-2")
    specific["matched_assets"] = [{"block_id": f"asset-{i}", "bbox": [i, 1, i + 1, 10]} for i in (2, 3)]
    specific["asset_block_ids"] = ["asset-2", "asset-3"]
    inventory = {"matched_figures": [broad, specific]}

    _finalize_figure_identities(inventory)

    result = inventory["matched_figures"][0]
    assert {asset["block_id"] for asset in result["matched_assets"]} == {"asset-2", "asset-3"}
    assert result["overclaims"][0]["reason"] == "strict_superset_asset_claim"
    assert len(result["claims"]) == 2
    assert inventory["identity_conflicts"] == []


def test_partial_asset_overlap_keeps_smaller_claim_and_records_hold() -> None:
    first = _entry("Figure 4: same caption", "caption", "asset-1")
    first["matched_assets"] = [{"block_id": f"asset-{i}", "bbox": [i, 1, i + 1, 10]} for i in (1, 2, 3)]
    first["asset_block_ids"] = ["asset-1", "asset-2", "asset-3"]
    second = _entry("Figure 4: same caption", "caption", "asset-3")
    second["matched_assets"] = [{"block_id": f"asset-{i}", "bbox": [i, 1, i + 1, 10]} for i in (3, 4)]
    second["asset_block_ids"] = ["asset-3", "asset-4"]
    inventory = {"matched_figures": [first, second]}

    _finalize_figure_identities(inventory)

    assert {asset["block_id"] for asset in inventory["matched_figures"][0]["matched_assets"]} == {
        "asset-3", "asset-4",
    }
    assert inventory["identity_conflicts"][0]["status"] == "HOLD"
    assert inventory["identity_conflicts"][0]["reason"] == "partially_overlapping_asset_claims"


def test_same_label_with_different_caption_on_page_is_held() -> None:
    inventory = {"matched_figures": [
        _entry("Figure 4: first caption", "caption-a", "asset-a"),
        _entry("Figure 4: conflicting caption", "caption-b", "asset-b"),
    ]}
    _finalize_figure_identities(inventory)
    assert len(inventory["matched_figures"]) == 1
    assert inventory["identity_conflicts"][0]["status"] == "HOLD"


def test_continuation_merges_assets_into_base_identity() -> None:
    base = _entry("Figure 3: base", "base-caption", "asset-a")
    continuation = _entry("Figure 3 continued", "continued-caption", "asset-b", page=2, is_continuation=True)
    inventory = {"matched_figures": [continuation, base]}
    _finalize_figure_identities(inventory)
    assert len(inventory["matched_figures"]) == 1
    result = inventory["matched_figures"][0]
    assert result["figure_label"] == "3"
    assert {a["block_id"] for a in result["matched_assets"]} == {"asset-a", "asset-b"}
    assert result["continued_from"] == ["continued-caption"]


def test_unnumbered_captions_have_deterministic_unique_ids() -> None:
    entries = [_entry("Unnumbered caption A", "caption-a", "asset-a"), _entry("Unnumbered caption B", "caption-b", "asset-b")]
    first = {"matched_figures": [dict(e) for e in entries]}
    second = {"matched_figures": [dict(e) for e in entries]}
    _finalize_figure_identities(first)
    _finalize_figure_identities(second)
    ids = [f["figure_id"] for f in first["matched_figures"]]
    assert ids == [f["figure_id"] for f in second["matched_figures"]]
    assert len(ids) == len(set(ids))
    assert len({f"render/figures/{i}.md" for i in ids}) == len(ids)


def test_markdown_heading_uses_display_label() -> None:
    from paperforge.worker.ocr_objects import render_figure_object_markdown

    markdown = render_figure_object_markdown({
        "figure_id": "figure_main_11-1_deadbeef",
        "display_label": "Figure 11-1",
        "caption": "caption",
        "was_cropped": False,
    })
    assert markdown.startswith("# Figure 11-1\n")


def test_duplicate_artifact_id_aborts_before_dispatch(tmp_path, monkeypatch) -> None:
    import pytest

    import paperforge.worker.ocr_objects as objects

    dispatched = []
    monkeypatch.setattr(objects, "_write_figure_object_task", lambda data, **kwargs: dispatched.append(data["fig_id"]) or {})
    figures = {"matched_figures": [
        {"figure_id": "same", "page": 1, "text": "Figure 1", "matched_assets": []},
        {"figure_id": "same", "page": 2, "text": "Figure 2", "matched_assets": []},
    ]}
    with pytest.raises(objects.MaterializationCollisionError):
        objects.extract_and_write_objects(
            None, figures, {"tables": [], "unmatched_assets": []}, tmp_path / "assets", tmp_path / "render",
        )
    assert dispatched == []
    assert figures["identity_collisions"][0]["type"] == "identity_collision"
    assert figures["identity_collisions"][0]["status"] == "HARD_FAILURE"
