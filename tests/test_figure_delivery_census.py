import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "dev" / "figure_delivery_census.py"
SPEC = importlib.util.spec_from_file_location("figure_delivery_census", PATH)
assert SPEC and SPEC.loader
FDC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FDC)


def test_replay_plan_keeps_paper_and_object_overlap_distinct():
    census = {
        "papers": [
            {
                "key": "A",
                "cross_page_reservations_in_matched": [{"figure_id": "figure_reserved_003"}],
                "render_asset_checks": {
                    "missing_asset_file_records": 2,
                    "missing_asset_figure_ids": ["figure_003"],
                },
            },
            {
                "key": "B",
                "cross_page_reservations_in_matched": [],
                "render_asset_checks": {
                    "missing_asset_file_records": 1,
                    "missing_asset_figure_ids": ["figure_001"],
                },
            },
            {
                "key": "C",
                "cross_page_reservations_in_matched": [{"figure_id": "figure_reserved_004"}],
                "render_asset_checks": {"missing_asset_file_records": 0, "missing_asset_figure_ids": []},
            },
            {
                "key": "D",
                "cross_page_reservations_in_matched": [],
                "render_asset_checks": {
                    "missing_asset_file_records": 1,
                    "missing_asset_figure_ids": ["figure_002"],
                },
            },
        ]
    }

    plan = FDC.plan_replays(census, ["D"], other_crop_count=1)

    assert plan["reservation_papers"] == ["A", "C"]
    assert plan["missing_crop_papers"] == ["A", "B", "D"]
    assert plan["overlap"]["paper_intersection_count"] == 1
    assert plan["overlap"]["exact_figure_id_intersection_count"] == 0
    assert plan["overlap"]["same_ordinal_candidate_count"] == 1
    assert plan["overlap"]["same_ordinal_identity_is_proven"] is False
    assert plan["other_missing_crop_sample"] == ["B"]
    assert plan["target_keys"] == ["A", "B", "C", "D"]
    assert "1 papers overlap" in plan["overlap"]["interpretation"]
    assert "1 IDs become same-ordinal candidates" in plan["overlap"]["interpretation"]


def test_migration_gate_does_not_turn_unknown_into_ready_or_blanket_hold():
    assert FDC._migration_state("LEGACY_BACKLOG_RESOLVED", "UNKNOWN") == "VISUAL_REVIEW_PENDING"
    assert FDC._migration_state("SOURCE_MISMATCH", "UNKNOWN") == "HOLD"
    assert FDC._migration_state("REBUILD_ERROR_UNASSESSED", "UNKNOWN") == "PENDING_EVIDENCE"
    assert FDC._migration_state("REBUILD_EVIDENCE_INCOMPLETE", "UNKNOWN") == "PENDING_EVIDENCE"
    assert FDC._migration_state("UNASSESSED", "UNKNOWN") == "PENDING_REBUILD"


def test_false_candidate_requires_source_bound_adjudication_and_explains_omission():
    historical = {"census_status": "UNEXPECTED", "matched_figures": 1}
    case = {
        "structural_pass": True,
        "figures": 0,
        "rebuilt_delivery": {"figure_states": {}},
    }
    inventory = {
        "held_figures": [{
            "legend_page": 4,
            "legend_block_id": "2",
        }],
        "association_reservations": [],
    }
    adjudications = [{
        "figure_id": "figure_reserved_003",
        "legend_page": 4,
        "legend_block_id": "2",
    }]

    classification, unresolved_reservations, unresolved_holds = FDC._classify(
        historical, case, inventory, adjudications,
    )

    assert classification == "FALSE_FIGURE_CANDIDATE"
    assert unresolved_reservations == []
    assert unresolved_holds == []


def test_matching_id_is_required_to_apply_id_bound_adjudication():
    reservation = {
        "figure_id": "figure_reserved_004",
        "legend_page": 4,
        "legend_block_id": "2",
    }
    adjudication = {
        "figure_id": "figure_reserved_003",
        "legend_page": 4,
        "legend_block_id": "2",
    }

    assert not FDC._adjudication_matches(reservation, adjudication)


def test_missing_rebuilt_inventory_is_pending_evidence():
    classification, _, _ = FDC._classify(
        {"matched_figures": 1},
        {"structural_pass": True, "figures": 1, "rebuilt_delivery": {"figure_states": {}}},
        {},
        [],
        inventory_missing=True,
    )

    assert classification == "REBUILD_EVIDENCE_INCOMPLETE"


def test_unexplained_positive_count_drift_is_not_marked_resolved():
    classification, _, _ = FDC._classify(
        {"matched_figures": 1},
        {"structural_pass": True, "figures": 2, "rebuilt_delivery": {"figure_states": {}}},
        {},
        [],
    )

    assert classification == "UNASSESSED_IDENTITY_DRIFT"


def test_partial_replay_reuses_prior_records_only_when_inputs_match(tmp_path):
    record = {"key": "K", "classification": "LEGACY_BACKLOG_RESOLVED"}
    census_path = tmp_path / "reattribution-census.json"
    census_path.write_text(json.dumps({
        "scope": {"inputs": {"source": "sha256:current"}},
        "papers": [record],
    }), encoding="utf-8")

    assert FDC._reusable_prior_records(
        tmp_path, {"source": "sha256:current"}
    ) == {"K": record}
    assert FDC._reusable_prior_records(
        tmp_path, {"source": "sha256:changed"}
    ) == {}


def test_reused_record_backfills_fulltext_hash_from_verified_snapshot(tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    fulltext = snapshot / "fulltext.md"
    fulltext.write_text("current text", encoding="utf-8")
    fulltext_sha = FDC._sha256_file(fulltext)
    fingerprint = "sha256:snapshot"
    (snapshot / "snapshot.json").write_text(json.dumps({
        "fingerprint": fingerprint,
        "files": {"fulltext.md": {"sha256": fulltext_sha}},
    }), encoding="utf-8")
    record = {
        "key": "K",
        "rebuilt_state": {
            "snapshot_path": str(snapshot),
            "snapshot_fingerprint": fingerprint,
        },
    }
    (tmp_path / "reattribution-census.json").write_text(json.dumps({
        "scope": {"inputs": {"source": "sha256:current"}},
        "papers": [record],
    }), encoding="utf-8")

    reused = FDC._reusable_prior_records(tmp_path, {"source": "sha256:current"})

    assert reused["K"]["rebuilt_state"]["snapshot_fulltext_sha256"] == fulltext_sha
    saved = json.loads((tmp_path / "papers" / "K.json").read_text(encoding="utf-8"))
    assert saved["rebuilt_state"]["snapshot_fulltext_sha256"] == fulltext_sha
