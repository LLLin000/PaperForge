import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "figure_delivery_census", ROOT / "scripts/dev/figure_delivery_census.py"
)
assert SPEC and SPEC.loader
FDC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FDC)

REBUILT_STATE_KEYS = {
    "status", "snapshot_fingerprint", "snapshot_path", "source_pdf_sha256",
    "snapshot_fulltext_sha256", "source_provenance", "delivery", "error",
    "acceptance_blocked_by", "matched_figure_count", "identity_count_comparison",
    "inventory_evidence_missing", "held_figures", "association_reservations",
    "unresolved_reservations", "unresolved_holds", "visual_review_status",
    "visual_label_counts",
}
PAPER_KEYS = {
    "key", "evidence_dir", "base_status", "historical_state", "prior_r2_state_context",
    "prior_r2_state_context_note", "prior_r3a_pdf_review_context",
    "prior_r3a_pdf_review_binding", "source_adjudications", "source_adjudications_unbound",
    "rebuilt_state", "classification", "migration_state",
}


def _record(tmp_path):
    paper = tmp_path / "ocr" / "K"
    paper.mkdir(parents=True)
    inventory = {
        "matched_figures": [], "held_figures": [], "association_reservations": [],
    }
    (paper / "figure_inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
    snapshot_root = tmp_path / "snapshots" / "s1"
    (snapshot_root / "structure").mkdir(parents=True)
    (snapshot_root / "structure" / "figure_inventory.json").write_text(
        json.dumps(inventory), encoding="utf-8"
    )
    run = {
        "out_dir": str(tmp_path / "out" / "K"),
        "snapshot": {"fingerprint": "sha256:s1", "directory": str(snapshot_root)},
        "case": {
            "status": "ok", "structural_pass": True, "figures": 0,
            "rebuilt_delivery": {"figure_states": {}, "summary": {
                "resolved": 0, "unresolved_reservations": 0, "delivery_defects": 0,
            }},
            "acceptance_blocked_by": ["human_visual_review_incomplete"],
            "visual_review_status": "UNKNOWN",
            "visual_label_counts": {"total": 0},
        },
    }
    return FDC._paper_record(
        "K",
        {"status": "RESOLVED", "matched_figures": 0},
        "READY",
        run,
        None,
        [],
    )


def test_paper_record_keeps_full_rebuilt_state_shape(tmp_path):
    record = _record(tmp_path)

    assert set(record) == PAPER_KEYS
    assert set(record["rebuilt_state"]) == REBUILT_STATE_KEYS
    assert record["rebuilt_state"]["matched_figure_count"] == 0


def test_record_is_json_serializable_and_classified(tmp_path):
    record = _record(tmp_path)

    json.dumps(record)
    assert record["classification"] == "REBUILT_STRUCTURALLY_RESOLVED"
    assert record["migration_state"] == "VISUAL_REVIEW_PENDING"
