"""Reattribute historical Figure delivery findings against isolated rebuild snapshots."""

from __future__ import annotations

import argparse
import importlib.util
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_FQE_PATH = ROOT / "scripts" / "dev" / "figure_quality_eval.py"
_SPEC = importlib.util.spec_from_file_location("figure_quality_eval_for_census", _FQE_PATH)
assert _SPEC and _SPEC.loader
FQE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(FQE)

DEFAULT_ELIGIBILITY = ROOT / "docs/evidence/r2-audit/migration-eligibility.json"
DEFAULT_HISTORICAL = ROOT / "docs/evidence/r3-follow-up/reservation-census.json"
DEFAULT_SAMPLE = ROOT / "docs/evidence/r3/sample-manifest.json"
DEFAULT_PDF_REVIEW = ROOT / "docs/evidence/r3a/pdf-review.json"
DEFAULT_ADJUDICATIONS = ROOT / "docs/evidence/r3-reattribution/user-adjudications.json"
DEFAULT_OUT = ROOT / "docs/evidence/r3-reattribution"
OTHER_CROP_SEED = "r3-reattribution-other-crop-v1"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()




def plan_replays(census: dict[str, Any], frozen_keys: list[str], other_crop_count: int = 24) -> dict[str, Any]:
    papers = {row["key"]: row for row in census["papers"]}
    reservation_keys = sorted(
        key for key, row in papers.items() if row.get("cross_page_reservations_in_matched")
    )
    missing_crop_keys = sorted(
        key for key, row in papers.items()
        if (row.get("render_asset_checks") or {}).get("missing_asset_file_records", 0) > 0
    )
    frozen = sorted(set(frozen_keys))
    other_candidates = [
        key for key in missing_crop_keys
        if key not in set(reservation_keys) and key not in set(frozen)
    ]
    other_candidates.sort(
        key=lambda key: hashlib.sha256(f"{OTHER_CROP_SEED}:{key}".encode("utf-8")).hexdigest()
    )
    other_sample = other_candidates[:other_crop_count]
    target = sorted(set(reservation_keys) | set(frozen) | set(other_sample))

    reservation_objects = [
        (row["key"], item)
        for row in census["papers"]
        for item in (row.get("cross_page_reservations_in_matched") or [])
    ]
    exact_object_overlap = []
    ordinal_candidate_overlap = []
    for key, reservation in reservation_objects:
        missing_ids = set(
            (papers[key].get("render_asset_checks") or {}).get("missing_asset_figure_ids", [])
        )
        figure_id = str(reservation.get("figure_id") or "")
        if figure_id in missing_ids:
            exact_object_overlap.append({"key": key, "reservation_figure_id": figure_id})
        if figure_id.startswith("figure_reserved_"):
            normalized = figure_id.replace("figure_reserved_", "figure_", 1)
            if normalized in missing_ids:
                ordinal_candidate_overlap.append({
                    "key": key,
                    "reservation_figure_id": figure_id,
                    "missing_crop_figure_id": normalized,
                })

    return {
        "frozen_sample_keys": frozen,
        "reservation_papers": reservation_keys,
        "missing_crop_papers": missing_crop_keys,
        "other_missing_crop_candidates": len(other_candidates),
        "other_missing_crop_sample_seed": OTHER_CROP_SEED,
        "other_missing_crop_sample": other_sample,
        "target_keys": target,
        "overlap": {
            "reservation_paper_count": len(reservation_keys),
            "missing_crop_paper_count": len(missing_crop_keys),
            "paper_intersection_count": len(set(reservation_keys) & set(missing_crop_keys)),
            "reservation_object_count": len(reservation_objects),
            "exact_figure_id_intersection_count": len(exact_object_overlap),
            "exact_figure_id_intersections": exact_object_overlap,
            "same_ordinal_candidate_count": len(ordinal_candidate_overlap),
            "same_ordinal_candidates": ordinal_candidate_overlap,
            "same_ordinal_identity_is_proven": False,
            "exact_raw_id_matches_are_namespace_sanity_check": True,
            "interpretation": (
                f"{len(set(reservation_keys) & set(missing_crop_keys))} papers overlap at paper level; "
                f"{len(exact_object_overlap)} exact raw Figure IDs overlap (expected zero across reserved "
                "versus materialized namespaces); "
                f"{len(ordinal_candidate_overlap)} IDs become same-ordinal candidates only after stripping "
                "figure_reserved_. These are not proven mappings; rebuilt ownership evidence is required "
                "before deduplication."
            ),
        },
        "denominators": {
            "paper": "One OCR key. A paper can appear in reservation and missing-crop groups.",
            "object": "One reservation record inside matched_figures; a paper may hold several.",
            "unique_claim_pair": "One (paper, figure_id) crop claim; repeats are counted once.",
            "note": (
                "Historical record counts in reservation-census.json count records; the 3,127 vs "
                "2,972 gap is duplicate claim records, not missing files. Never treat record, "
                "unique-pair, and paper counts as interchangeable."
            ),
        },
    }


def _historical_state(row: dict[str, Any]) -> dict[str, Any]:
    checks = row.get("render_asset_checks") or {}
    return {
        "census_status": row.get("status"),
        "visual_review": row.get("visual_review", "UNKNOWN"),
        "matched_figures": row.get("matched_figures", 0),
        "held_figures": row.get("held_figures", 0),
        "cross_page_reservations": row.get("cross_page_reservations_in_matched", []),
        "matched_without_assets": row.get("matched_without_assets", []),
        "missing_crop_claim_records": checks.get("missing_asset_file_records", 0),
        "missing_crop_figure_ids": checks.get("missing_asset_figure_ids", []),
        "missing_render_reference_figure_ids": checks.get("render_without_image_reference_figure_ids", []),
        "missing_embeds": row.get("missing_embed", []),
        "ownership_conflicts": row.get("ownership_conflicts", []),
        "audit_violations": row.get("audit_violations", {}),
        "flags": row.get("flags", []),
        "input_fingerprints": row.get("input_fingerprints", {}),
    }


def _same_path(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    return os.path.normcase(os.path.realpath(left)) == os.path.normcase(os.path.realpath(right))


def _adjudication_matches(record: dict[str, Any], adjudication: dict[str, Any]) -> bool:
    record_id = str(record.get("figure_id") or record.get("reserved_figure_id") or "")
    wanted_id = str(adjudication.get("figure_id") or "")
    if record_id and wanted_id:
        return record_id == wanted_id
    page = record.get("legend_page", record.get("page"))
    wanted_page = adjudication.get("legend_page")
    block_id = record.get("legend_block_id")
    wanted_block_id = adjudication.get("legend_block_id")
    return (
        page is not None
        and wanted_page is not None
        and block_id is not None
        and wanted_block_id is not None
        and str(page) == str(wanted_page)
        and str(block_id) == str(wanted_block_id)
    )


def _rebuilt_inventory(snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    if not snapshot:
        return {}
    path = Path(snapshot["directory"]) / "structure" / "figure_inventory.json"
    return _read_json(path) if path.is_file() else None


def _adjudication_binding_reasons(
    key: str, case: dict[str, Any], item: dict[str, Any],
) -> list[str]:
    observed = case.get("source_provenance", {}).get("observed", {})
    reasons = []
    if item.get("key") != key:
        reasons.append("paper_key_mismatch")
    if item.get("status") != "FALSE_FIGURE_CANDIDATE":
        reasons.append("unsupported_status")
    if item.get("source_pdf_sha256") != case.get("source_pdf_sha256"):
        reasons.append("source_sha256_mismatch")
    if item.get("source_page_count") != observed.get("page_count"):
        reasons.append("source_page_count_mismatch")
    if not _same_path(item.get("source_pdf"), observed.get("path")):
        reasons.append("source_path_mismatch")
    return reasons


def _bound_adjudications(
    key: str, case: dict[str, Any], adjudications: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        item for item in adjudications
        if not _adjudication_binding_reasons(key, case, item)
    ]


def _record_is_adjudicated(record: dict[str, Any], adjudications: list[dict[str, Any]]) -> bool:
    return any(_adjudication_matches(record, item) for item in adjudications)


def _classify(
    historical: dict[str, Any], case: dict[str, Any], inventory: dict[str, Any],
    adjudications: list[dict[str, Any]], inventory_missing: bool = False,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    status = case.get("status")
    if status == "SOURCE_MISMATCH":
        return "SOURCE_MISMATCH", [], []
    if status == "REBUILD_ERROR":
        return "REBUILD_ERROR_UNASSESSED", [], []
    if inventory_missing:
        return "REBUILD_EVIDENCE_INCOMPLETE", [], []

    delivery = case.get("rebuilt_delivery") or {}
    states = list((delivery.get("figure_states") or {}).values())
    if "UNRESOLVED_RESERVATION" in states:
        return "UNRESOLVED_RESERVATION", [], []
    if "DELIVERY_DEFECT" in states:
        return "DELIVERY_DEFECT", [], []

    reservations = inventory.get("association_reservations", []) or []
    unresolved_reservations = [
        row for row in reservations
        if row.get("status") in {"RESERVED", "HOLD"}
        and not _record_is_adjudicated(row, adjudications)
    ]
    held = inventory.get("held_figures", []) or []
    unresolved_holds = [
        row for row in held if not _record_is_adjudicated(row, adjudications)
    ]
    if unresolved_reservations:
        return "UNRESOLVED_RESERVATION", unresolved_reservations, unresolved_holds
    if unresolved_holds:
        return "HOLD", [], unresolved_holds
    if not case.get("structural_pass", False):
        return "STRUCTURAL_FAILURE", [], []

    current_count = case.get("figures", 0)
    expected_count = max(0, historical.get("matched_figures", 0) - len(adjudications))
    if current_count != expected_count:
        return "UNASSESSED_IDENTITY_DRIFT", [], []
    if adjudications:
        return "FALSE_FIGURE_CANDIDATE", [], []
    if historical.get("census_status") == "UNEXPECTED":
        return "LEGACY_BACKLOG_RESOLVED", [], []
    return "REBUILT_STRUCTURALLY_RESOLVED", [], []


def _migration_state(classification: str, visual_status: str) -> str:
    if classification in {
        "SOURCE_MISMATCH", "UNRESOLVED_RESERVATION", "HOLD", "DELIVERY_DEFECT", "STRUCTURAL_FAILURE",
    }:
        return "HOLD"
    if classification == "UNASSESSED":
        return "PENDING_REBUILD"
    if classification in {
        "REBUILD_ERROR_UNASSESSED", "REBUILD_EVIDENCE_INCOMPLETE", "UNASSESSED_IDENTITY_DRIFT",
    }:
        return "PENDING_EVIDENCE"
    if visual_status != "REVIEWED":
        return "VISUAL_REVIEW_PENDING"
    return "READY_CANDIDATE"




def _paper_record(
    key: str,
    old: dict[str, Any],
    base_status: str,
    run: dict[str, Any] | None,
    pdf_review: dict[str, Any] | None,
    adjudication_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    case = (run or {}).get("case", {})
    snapshot = (run or {}).get("snapshot")
    loaded_inventory = _rebuilt_inventory(snapshot)
    inventory_missing = snapshot is not None and loaded_inventory is None
    inventory = loaded_inventory or {}
    historical = _historical_state(old)
    source_bound_adjudications = _bound_adjudications(key, case, adjudication_rows)
    key_adjudications = [item for item in adjudication_rows if item.get("key") == key]
    unbound_adjudications = [
        {
            "entry": item,
            "binding_failure_reasons": _adjudication_binding_reasons(key, case, item),
        }
        for item in key_adjudications
        if _adjudication_binding_reasons(key, case, item)
    ]
    classification, unresolved_reservations, unresolved_holds = _classify(
        historical, case, inventory, source_bound_adjudications, inventory_missing,
    ) if run else ("UNASSESSED", [], [])
    visual_status = case.get("visual_review_status", "UNKNOWN")
    current_count = case.get("figures")
    expected_count = max(0, historical["matched_figures"] - len(source_bound_adjudications))
    count_status = (
        "NOT_REBUILT" if current_count is None
        else "COUNT_MATCH_ONLY" if current_count == expected_count
        else "COUNT_MISMATCH_UNASSESSED"
    )
    rebuilt_state = {
        "status": "REPLAYED" if snapshot else case.get("status", "NOT_REBUILT"),
        "snapshot_fingerprint": (snapshot or {}).get("fingerprint"),
        "snapshot_path": (snapshot or {}).get("directory"),
        "source_pdf_sha256": case.get("source_pdf_sha256"),
        "snapshot_fulltext_sha256": (
            (((snapshot or {}).get("files") or {}).get("fulltext.md") or {}).get("sha256")
        ),
        "source_provenance": case.get("source_provenance"),
        "delivery": case.get("rebuilt_delivery"),
        "error": case.get("error"),
        "acceptance_blocked_by": case.get("acceptance_blocked_by"),
        "matched_figure_count": current_count,
        "identity_count_comparison": {
            "historical_matched_count": historical["matched_figures"],
            "explained_false_candidate_count": len(source_bound_adjudications),
            "expected_count_for_count_check_only": expected_count,
            "rebuilt_count": current_count,
            "status": count_status,
            "identity_proven": False,
        },
        "inventory_evidence_missing": inventory_missing,
        "held_figures": inventory.get("held_figures", []) or [],
        "association_reservations": inventory.get("association_reservations", []) or [],
        "unresolved_reservations": unresolved_reservations,
        "unresolved_holds": unresolved_holds,
        "visual_review_status": visual_status,
        "visual_label_counts": case.get("visual_label_counts", {}),
    }
    return {
        "key": key,
        "evidence_dir": (run or {}).get("out_dir"),
        "base_status": base_status,
        "historical_state": historical,
        "prior_r2_state_context": old.get("r2_isolation", {}),
        "prior_r2_state_context_note": (
            "Historical per-paper R2 record; may include tables and other non-Figure artifacts. "
            "Not used for the rebuilt Figure classification."
        ),
        "prior_r3a_pdf_review_context": pdf_review,
        "prior_r3a_pdf_review_binding": "CONTEXT_ONLY_NO_RECORDED_SOURCE_SHA256",
        "source_adjudications": source_bound_adjudications,
        "source_adjudications_unbound": unbound_adjudications,
        "rebuilt_state": rebuilt_state,
        "classification": classification,
        "migration_state": _migration_state(classification, visual_status),
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _reusable_prior_records(
    out_root: Path, inputs: dict[str, str | None],
) -> dict[str, dict[str, Any]]:
    path = out_root / "reattribution-census.json"
    if not path.is_file():
        return {}
    prior = _read_json(path)
    if (prior.get("scope") or {}).get("inputs") != inputs:
        return {}
    records = {row["key"]: row for row in prior.get("papers", [])}
    for key, record in records.items():
        rebuilt = record.get("rebuilt_state") or {}
        if rebuilt.get("snapshot_fulltext_sha256") or not rebuilt.get("snapshot_path"):
            continue
        snapshot_dir = Path(rebuilt["snapshot_path"])
        manifest_path = snapshot_dir / "snapshot.json"
        fulltext_path = snapshot_dir / "fulltext.md"
        if not manifest_path.is_file() or not fulltext_path.is_file():
            continue
        try:
            manifest = _read_json(manifest_path)
            actual_sha = _sha256_file(fulltext_path)
        except (OSError, json.JSONDecodeError):
            continue
        expected_sha = (manifest.get("files") or {}).get("fulltext.md", {}).get("sha256")
        if (
            manifest.get("fingerprint") != rebuilt.get("snapshot_fingerprint")
            or not expected_sha
            or actual_sha != expected_sha
        ):
            continue
        rebuilt["snapshot_fulltext_sha256"] = actual_sha
        _write_json(out_root / "papers" / f"{key}.json", record)
    return records


def build_census(
    vault: Path,
    ocr_root: Path,
    eligibility_path: Path,
    historical_path: Path,
    sample_path: Path,
    pdf_review_path: Path,
    adjudications_path: Path,
    out_root: Path,
    other_crop_count: int = 24,
    work_root: Path | None = None,
    only_keys: list[str] | None = None,
) -> dict[str, Any]:
    """Reattribute historical findings through isolated rebuilds.

    ``work_root`` holds rebuild snapshot payloads so the committed evidence tree keeps
    only derived hashes. ``only_keys`` replays a subset for diagnosis; it never shrinks
    the READY frame used for history-versus-rebuilt accounting.
    """
    eligibility = _read_json(eligibility_path)
    historical = _read_json(historical_path)
    sample = _read_json(sample_path)
    pdf_review_data = _read_json(pdf_review_path) if pdf_review_path.is_file() else {"entries": []}
    adjudication_data = _read_json(adjudications_path) if adjudications_path.is_file() else {"entries": []}
    if eligibility.get("schema") != "paperforge.migration_eligibility.v1":
        raise ValueError("unsupported migration eligibility schema")
    if historical.get("schema") != "paperforge.reservation_census.v1":
        raise ValueError("unsupported historical Census schema")

    ready_status = eligibility.get("status", {})
    ready_keys = sorted(key for key, status in ready_status.items() if status == "READY")
    historical_rows = {row["key"]: row for row in historical.get("papers", [])}
    if set(ready_keys) != set(historical_rows):
        raise ValueError("historical Census keys do not equal the frozen READY frame")

    plan = plan_replays(historical, sample.get("selected_keys", []), other_crop_count)
    plan["frozen_sample_candidate_count"] = sample.get("candidate_count")
    plan["frozen_sample_excluded_keys"] = sample.get("excluded", [])
    plan["sample_frame_note"] = (
        f"The frozen R3 sample used {sample.get('candidate_count')} candidates; the READY replay frame has "
        f"{len(ready_keys)} papers. Excluded frozen-sample keys are not implicitly dropped from READY; "
        "they are re-evaluated only if selected by the supplementary replay sample."
    )
    if not set(plan["target_keys"]) <= set(ready_keys):
        raise ValueError("replay target lies outside the READY frame")
    pdf_reviews = {row.get("key"): row for row in pdf_review_data.get("entries", [])}
    adjudications = adjudication_data.get("entries", [])
    input_paths = {
        "eligibility": eligibility_path,
        "historical_census": historical_path,
        "frozen_sample_manifest": sample_path,
        "prior_r3a_pdf_review": pdf_review_path,
        "source_adjudications": adjudications_path,
        "figure_quality_evaluator": ROOT / "scripts/dev/figure_quality_eval.py",
        "rebuild_runner": ROOT / "scripts/dev/object_migration_dry_run.py",
    }
    inputs = {
        name: _sha256_file(path) if path.is_file() else None
        for name, path in input_paths.items()
    }

    out_root.mkdir(parents=True, exist_ok=True)
    if work_root is not None:
        work_root.mkdir(parents=True, exist_ok=True)
    target_keys = set(plan["target_keys"])
    if only_keys:
        unknown = set(only_keys) - target_keys
        if unknown:
            raise ValueError(f"diagnostic keys lie outside the replay plan: {sorted(unknown)}")
        target_keys &= set(only_keys)
    previous_records = _reusable_prior_records(out_root, inputs) if only_keys else {}
    for key in plan["target_keys"]:
        if key not in target_keys:
            continue
        # run_key validates the recorded source identity, performs exactly one real isolated
        # derived rebuild, persists its content-addressed snapshot, and derives review labels.
        run = FQE.run_key(vault, ocr_root, key, out_root, work_root=work_root)
        record = _paper_record(
            key, historical_rows[key], ready_status[key], run,
            pdf_reviews.get(key), adjudications,
        )
        _write_json(out_root / "papers" / f"{key}.json", record)
        print(json.dumps({
            "key": key,
            "rebuilt_state": record["rebuilt_state"]["status"],
            "classification": record["classification"],
            "migration_state": record["migration_state"],
        }, ensure_ascii=False), flush=True)

    records = []
    for key in ready_keys:
        if key in target_keys:
            records.append(_read_json(out_root / "papers" / f"{key}.json"))
        elif key in previous_records:
            records.append(previous_records[key])
        else:
            records.append(_paper_record(
                key, historical_rows[key], ready_status[key], None,
                pdf_reviews.get(key), adjudications,
            ))

    classification_counts = {}
    migration_counts = {}
    rebuilt_counts = {}
    historical_counts = {}
    for row in records:
        classification_counts[row["classification"]] = classification_counts.get(row["classification"], 0) + 1
        migration_counts[row["migration_state"]] = migration_counts.get(row["migration_state"], 0) + 1
        state = row["rebuilt_state"]["status"]
        rebuilt_counts[state] = rebuilt_counts.get(state, 0) + 1
        historical_status = row["historical_state"]["census_status"]
        historical_counts[historical_status] = historical_counts.get(historical_status, 0) + 1

    return {
        "schema": "paperforge.figure_delivery_reattribution.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "ready_frame_count": len(ready_keys),
            "replay_plan_size": len(plan["target_keys"]),
            "replayed_subset_size": len(target_keys),
            "partial_replay": bool(only_keys),
            "historical_state_and_rebuilt_state_are_separate": True,
            "rebuild_mode": "isolated derived rebuild from retained raw blocks; no OCR Provider call",
            "rebuild_is_unaided": True,
            "prior_pdf_review_instructions_applied": False,
            "prior_pdf_review_source_hashes_available": False,
            "prior_pdf_review_context_only": True,
            "prior_r2_records_may_include_nonfigure_artifacts": True,
            "historical_census_summary": historical.get("summary", {}),
            "live_vault_writes": False,
            "production_migration": False,
            "prior_596_hold_overlay_applied": False,
            "inputs": inputs,
        },
        "selection": plan,
        "summary": {
            "historical_status_counts": historical_counts,
            "rebuilt_state_counts": rebuilt_counts,
            "classification_counts": classification_counts,
            "migration_state_counts": migration_counts,
            "replay_plan_size": len(plan["target_keys"]),
            "replayed_subset_size": len(target_keys),
            "replayed_papers": rebuilt_counts.get("REPLAYED", 0),
            "source_mismatch_papers": rebuilt_counts.get("SOURCE_MISMATCH", 0),
            "unbound_source_adjudications": sum(
                len(row["source_adjudications_unbound"]) for row in records
                if row["rebuilt_state"]["status"] == "REPLAYED"
            ),
            "unreplayed_source_adjudications": sum(
                len(row["source_adjudications"]) for row in records
                if row["rebuilt_state"]["status"] != "REPLAYED"
            ),
            "count_identity_mismatches_unassessed": sum(
                row["rebuilt_state"]["status"] == "REPLAYED"
                and row["rebuilt_state"]["identity_count_comparison"]["status"]
                == "COUNT_MISMATCH_UNASSESSED" for row in records
            ),
            "provider_ocr_runs": 0,
            "live_vault_writes": 0,
            "production_migration_ready": sum(
                row["migration_state"] == "READY_CANDIDATE" for row in records
            ),
        },
        "papers": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", default="D:/Zotero-Vault")
    parser.add_argument("--ocr-root", default="")
    parser.add_argument("--eligibility", default=str(DEFAULT_ELIGIBILITY))
    parser.add_argument("--historical-census", default=str(DEFAULT_HISTORICAL))
    parser.add_argument("--sample-manifest", default=str(DEFAULT_SAMPLE))
    parser.add_argument("--pdf-review", default=str(DEFAULT_PDF_REVIEW))
    parser.add_argument("--adjudications", default=str(DEFAULT_ADJUDICATIONS))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--other-crop-sample", type=int, default=24)
    parser.add_argument(
        "--work-root", default=str(ROOT / ".work" / "r3-reattribution"),
        help="scratch root for rebuild snapshot payloads (never the evidence tree)",
    )
    parser.add_argument(
        "--only-keys", nargs="*", default=[],
        help="diagnostic subset of already-planned replay keys",
    )
    args = parser.parse_args()

    vault = Path(args.vault)
    ocr_root = Path(args.ocr_root) if args.ocr_root else vault / "System" / "PaperForge" / "ocr"
    census = build_census(
        vault, ocr_root,
        Path(args.eligibility), Path(args.historical_census), Path(args.sample_manifest),
        Path(args.pdf_review), Path(args.adjudications), Path(args.out), args.other_crop_sample,
        Path(args.work_root) if args.work_root else None,
        args.only_keys,
    )
    out_path = Path(args.out) / "reattribution-census.json"
    _write_json(out_path, census)
    print(json.dumps(census["summary"], ensure_ascii=False))
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
