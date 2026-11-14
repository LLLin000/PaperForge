import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ELIG = _load("build_reattribution_eligibility", "scripts/dev/build_reattribution_eligibility.py")
PACK = _load("figure_review_pack", "scripts/dev/figure_review_pack.py")


def _pack(census_path, papers):
    return {
        "source_census_sha256": "sha256:" + hashlib.sha256(census_path.read_bytes()).hexdigest(),
        "papers": papers,
    }


def _census(papers, targets):
    return {"selection": {"target_keys": targets}, "papers": papers}


def _paper(key, status="REPLAYED", classification="REBUILT_STRUCTURALLY_RESOLVED",
           migration_state="VISUAL_REVIEW_PENDING", snapshot="sha256:s1",
           source="sha256:p1"):
    return {
        "key": key,
        "classification": classification,
        "migration_state": migration_state,
        "rebuilt_state": {
            "status": status,
            "snapshot_fingerprint": snapshot,
            "source_pdf_sha256": source,
        },
    }


def test_unreviewed_replay_is_never_ready(tmp_path):
    census_path = tmp_path / "census.json"
    census_path.write_text(json.dumps(_census([_paper("A")], ["A"])), encoding="utf-8")
    pack_path = tmp_path / "index.json"
    pack_path.write_text(json.dumps(_pack(census_path, [])), encoding="utf-8")

    out = ELIG.derive(census_path, pack_path)

    assert out["status"]["A"] == "VISUAL_REVIEW_PENDING"
    assert out["ready_count"] == 0
    assert out["production_migration_ready_count"] == 0
    assert out["gates"]["historical_596_hold_overlay_applied"] is False


def test_defects_and_identity_drift_are_not_hidden_as_visual_pending(tmp_path):
    papers = [
        _paper("DEFECT", classification="DELIVERY_DEFECT"),
        _paper("DRIFT", classification="UNASSESSED_IDENTITY_DRIFT"),
    ]
    census_path = tmp_path / "census.json"
    census_path.write_text(
        json.dumps(_census(papers, ["DEFECT", "DRIFT"])), encoding="utf-8"
    )
    pack_path = tmp_path / "index.json"
    pack_path.write_text(json.dumps(_pack(census_path, [])), encoding="utf-8")

    out = ELIG.derive(census_path, pack_path)

    assert out["status"]["DEFECT"] == "HOLD"
    assert out["status"]["DRIFT"] == "PENDING_EVIDENCE"


def test_human_review_bound_to_other_snapshot_does_not_count(tmp_path):
    census_path = tmp_path / "census.json"
    census_path.write_text(json.dumps(_census([_paper("A")], ["A"])), encoding="utf-8")
    pack_path = tmp_path / "index.json"
    pack_path.write_text(json.dumps(_pack(census_path, [{
        "key": "A", "review_status": "REVIEWED",
        "snapshot_fingerprint": "sha256:other", "source_pdf_sha256": "sha256:p1",
    }])), encoding="utf-8")

    out = ELIG.derive(census_path, pack_path)

    assert out["status"]["A"] == "VISUAL_REVIEW_PENDING"
    assert out["reasons"]["A"] == ["review_binding_mismatch"]


def test_bound_human_review_on_clean_rebuild_becomes_candidate_not_production(tmp_path):
    census_path = tmp_path / "census.json"
    census_path.write_text(
        json.dumps(_census([_paper("A", migration_state="VISUAL_REVIEW_PENDING")], ["A"])),
        encoding="utf-8",
    )
    pack_path = tmp_path / "index.json"
    pack_path.write_text(json.dumps(_pack(census_path, [{
        "key": "A", "review_status": "REVIEWED",
        "snapshot_fingerprint": "sha256:s1", "source_pdf_sha256": "sha256:p1",
    }])), encoding="utf-8")

    out = ELIG.derive(census_path, pack_path)

    assert out["status"]["A"] == "READY_CANDIDATE"
    assert out["ready_count"] == 1
    assert out["production_migration_ready_count"] == 0
    assert out["gates"]["production_migration_authorized"] is False


def test_source_mismatch_and_unplanned_papers_fail_closed(tmp_path):
    census_path = tmp_path / "census.json"
    census_path.write_text(json.dumps(_census(
        [_paper("A", status="SOURCE_MISMATCH"), _paper("B"), _paper("C")], ["A", "B"]
    )), encoding="utf-8")
    pack_path = tmp_path / "index.json"
    pack_path.write_text(json.dumps(_pack(census_path, [])), encoding="utf-8")

    out = ELIG.derive(census_path, pack_path)

    assert out["status"]["A"] == "HOLD"
    assert out["status"]["B"] == "VISUAL_REVIEW_PENDING"
    assert out["status"]["C"] == "PENDING_REBUILD"
    assert out["reasons"]["C"] == ["not_in_replay_plan"]



def test_stale_review_pack_census_does_not_authorize_candidate(tmp_path):
    census_path = tmp_path / "census.json"
    census_path.write_text(json.dumps(_census([_paper("A")], ["A"])), encoding="utf-8")
    pack_path = tmp_path / "index.json"
    pack_path.write_text(json.dumps({
        "source_census_sha256": "sha256:stale",
        "papers": [{
            "key": "A", "review_status": "REVIEWED",
            "snapshot_fingerprint": "sha256:s1", "source_pdf_sha256": "sha256:p1",
        }],
    }), encoding="utf-8")

    out = ELIG.derive(census_path, pack_path)

    assert out["status"]["A"] == "VISUAL_REVIEW_PENDING"
    assert out["reasons"]["A"] == ["review_pack_census_mismatch"]


def test_review_pack_requires_asset_bindings_and_complete_boolean_verdicts(tmp_path):
    papers = []
    selected = []
    labels_by_key = {
        "STALE": {"asset_sha256": "sha256:old", "reviewer": "Reviewer",
                  "caption_ok": True, "panels_ok": True, "crop_ok": True, "delivery_ok": True},
        "INCOMPLETE": {"asset_sha256": "sha256:asset", "reviewer": "Reviewer",
                       "caption_ok": None, "panels_ok": True, "crop_ok": True, "delivery_ok": True},
    }
    for key, answers in labels_by_key.items():
        selected.append(key)
        evidence_dir = tmp_path / key / "evidence"
        evidence_dir.mkdir(parents=True)
        figure_id = f"Figure_{key}"
        fulltext_sha = "sha256:fulltext"
        asset_sha = "sha256:asset"
        render_sha = "sha256:render"
        papers.append({
            "key": key,
            "classification": "REBUILT_STRUCTURALLY_RESOLVED",
            "migration_state": "VISUAL_REVIEW_PENDING",
            "evidence_dir": str(evidence_dir),
            "rebuilt_state": {
                "status": "REPLAYED",
                "snapshot_fingerprint": "sha256:snapshot",
                "source_pdf_sha256": "sha256:source",
                "source_provenance": {
                    "observed": {"path": f"{key}.pdf", "page_count": 4},
                },
                "snapshot_fulltext_sha256": fulltext_sha,
                "snapshot_path": str(tmp_path / key / "snapshot"),
                "delivery": {"figures": {figure_id: {
                    "asset_sha256": asset_sha,
                    "render_sha256": render_sha,
                    "fulltext_sha256": fulltext_sha,
                    "state": "RESOLVED",
                }}},
            },
        })
        label = {
            "key": key,
            "kind": "matched_figure",
            "figure_id": figure_id,
            "page": 1,
            "snapshot_fingerprint": "sha256:snapshot",
            "source_pdf_sha256": "sha256:source",
            "asset_sha256": asset_sha,
            "render_sha256": render_sha,
            "fulltext_sha256": fulltext_sha,
            "caption_ok": True,
            "panels_ok": True,
            "crop_ok": True,
            "delivery_ok": True,
            "reviewer": "Reviewer",
            **answers,
        }
        (evidence_dir / "labels.jsonl").write_text(json.dumps(label) + "\n", encoding="utf-8")

    census_path = tmp_path / "census.json"
    census_path.write_text(json.dumps(_census(papers, selected)), encoding="utf-8")
    sample_path = tmp_path / "sample.json"
    sample_path.write_text(json.dumps({"selected_keys": selected}), encoding="utf-8")
    index = PACK.build_pack(census_path, sample_path, tmp_path / "pack", None)

    statuses = {row["key"]: row for row in index["papers"]}
    assert statuses["STALE"]["review_status"] == "UNKNOWN_STALE_LABELS"
    assert statuses["STALE"]["labels_snapshot_bound"] == 0
    assert statuses["STALE"]["labels_reviewed"] == 0
    assert statuses["INCOMPLETE"]["review_status"] == "UNKNOWN"
    assert statuses["INCOMPLETE"]["labels_snapshot_bound"] == 1
    assert statuses["INCOMPLETE"]["labels_reviewed"] == 0
    assert index["human_review_conducted"] is False

def test_pack_marks_zero_label_papers_unknown(tmp_path):
    census_path = tmp_path / "census.json"
    census_path.write_text(json.dumps(_census([_paper("A")], ["A"])), encoding="utf-8")
    evidence = tmp_path / "A"
    evidence.mkdir()
    sample_path = tmp_path / "sample.json"
    sample_path.write_text(json.dumps({"selected_keys": ["A"]}), encoding="utf-8")

    index = PACK.build_pack(census_path, sample_path, tmp_path / "pack", None)

    row = index["papers"][0]
    assert row["labels_total"] == 0
    assert row["review_status"] == "UNKNOWN_NO_LABELS"
    assert index["human_review_conducted"] is False
    assert index["totals"]["zero_label"] == 1


def test_pack_refreshes_only_unreviewed_legends_bound_to_current_source_location(tmp_path):
    snapshot = tmp_path / "snapshot"
    structure = snapshot / "structure"
    structure.mkdir(parents=True)
    (structure / "blocks.structured.jsonl").write_text(
        '{"page": 2, "block_id": "B"}\n{"page": 3, "block_id": "C"}\n{"page": 1, "block_id": 0}\n',
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    labels = [
        {
            "key": "A", "kind": "unmatched_legend", "figure_id": "",
            "page": 2, "block_id": "B", "snapshot_fingerprint": "sha256:old",
            "source_pdf_sha256": "sha256:source", "fulltext_sha256": "sha256:old-text",
            "caption_ok": None, "panels_ok": None, "crop_ok": None, "delivery_ok": None,
            "reviewer": "", "reviewed_at": "", "notes": "",
        },
        {
            "key": "A", "kind": "unmatched_legend", "figure_id": "",
            "page": 3, "block_id": "C", "snapshot_fingerprint": "sha256:old",
            "source_pdf_sha256": "sha256:source", "fulltext_sha256": "sha256:old-text",
            "caption_ok": True, "panels_ok": False, "crop_ok": True, "delivery_ok": True,
            "reviewer": "Reviewer", "reviewed_at": "2026-11-14", "notes": "checked",
        },
        {
            "key": "A", "kind": "unmatched_legend", "figure_id": "",
            "page": 4, "block_id": "D", "snapshot_fingerprint": "sha256:current",
            "source_pdf_sha256": "sha256:source", "fulltext_sha256": "sha256:current-text",
            "caption_ok": None, "panels_ok": None, "crop_ok": None, "delivery_ok": None,
            "reviewer": "", "reviewed_at": "", "notes": "",
        },
        {
            "key": "A", "kind": "unmatched_legend", "figure_id": "",
            "page": 1, "block_id": 0, "snapshot_fingerprint": "sha256:current",
            "source_pdf_sha256": "sha256:source", "fulltext_sha256": "sha256:current-text",
            "caption_ok": None, "panels_ok": None, "crop_ok": None, "delivery_ok": None,
            "reviewer": "", "reviewed_at": "", "notes": "",
        },
    ]
    (evidence / "labels.jsonl").write_text(
        "\n".join(json.dumps(row) for row in labels) + "\n", encoding="utf-8"
    )
    census = {
        "selection": {"target_keys": ["A"]},
        "papers": [{
            "key": "A",
            "classification": "REBUILT_STRUCTURALLY_RESOLVED",
            "migration_state": "VISUAL_REVIEW_PENDING",
            "evidence_dir": str(evidence),
            "rebuilt_state": {
                "status": "REPLAYED",
                "snapshot_path": str(snapshot),
                "snapshot_fingerprint": "sha256:current",
                "snapshot_fulltext_sha256": "sha256:current-text",
                "source_pdf_sha256": "sha256:source",
                "source_provenance": {"observed": {"path": "A.pdf", "page_count": 3}},
                "delivery": {"figures": {}},
            },
        }],
    }
    census_path = tmp_path / "census.json"
    census_path.write_text(json.dumps(census), encoding="utf-8")
    sample_path = tmp_path / "sample.json"
    sample_path.write_text(json.dumps({"selected_keys": ["A"]}), encoding="utf-8")

    index = PACK.build_pack(census_path, sample_path, tmp_path / "pack", None)

    rows = [json.loads(line) for line in (evidence / "labels.jsonl").read_text().splitlines()]
    assert index["papers"][0]["labels_refreshed"] == 1
    assert index["papers"][0]["labels_snapshot_bound"] == 2
    assert index["papers"][0]["labels_stale"] == 2
    assert index["papers"][0]["review_status"] == "UNKNOWN_STALE_LABELS"
    assert rows[0]["snapshot_fingerprint"] == "sha256:current"
    assert rows[0]["fulltext_sha256"] == "sha256:current-text"
    assert rows[1]["reviewer"] == "Reviewer"
    assert rows[1]["notes"] == "checked"
    assert rows[1]["snapshot_fingerprint"] == "sha256:old"
