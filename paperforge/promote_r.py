"""Promote verified R repair artifacts from isolated reconcile staging.

This module is reconcile-only. It never re-renders an object and never changes
 the preceding OCR/render pipeline. A promotion consumes the exact R manifest
written by ``stage_reconciliation`` and refuses any stale, ambiguous, or
unverifiable plan before touching production.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from paperforge.render_audit import (
    _inventory_identity_conflicts,
    _inventory_rows,
    audit_paper,
)

_MANIFEST_NAME = "r-manifest.json"
_SUCCESS_MATERIALIZATION_STATUSES = {"materialized", "success"}


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None

_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)|!\[\[([^\]]+)\]\]")


def _sha256_path(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _image_facts(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        from PIL import Image

        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
    except Exception:
        return None
    return {"sha256": _sha256_path(path), "width": width, "height": height}


def _plan_hash(plan: dict[str, Any]) -> str:
    payload = {
        key: plan.get(key)
        for key in (
            "object_id",
            "canonical_identity",
            "input_snapshot_hash",
            "ordered_asset_refs",
            "staged_asset",
            "staged_markdown",
            "production_asset",
            "production_markdown",
        )
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _snapshot_hash(root: Path) -> str:
    parts = []
    for relative in (
        "structure/blocks.structured.jsonl",
        "structure/figure_inventory.json",
        "render/reconciliation.proposals.json",
    ):
        path = root / relative
        parts.append((_sha256_path(path) or "missing")[:16])
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _find_staging_root(
    paper_key: str,
    staging_root: Path | None = None,
) -> Path | None:
    if staging_root is not None:
        candidate = Path(staging_root)
        if candidate.name == paper_key and (candidate / _MANIFEST_NAME).is_file():
            return candidate
        nested = candidate / paper_key
        return nested if (nested / _MANIFEST_NAME).is_file() else None

    base = Path(tempfile.gettempdir()) / "paperforge-staging"
    if not base.is_dir():
        return None
    candidates: list[Path] = []
    for run in base.iterdir():
        if not run.is_dir():
            continue
        candidate = run / paper_key
        if (candidate / _MANIFEST_NAME).is_file():
            candidates.append(candidate)
    return max(candidates, key=lambda path: (path / _MANIFEST_NAME).stat().st_mtime_ns) if candidates else None


def _safe_stage_path(stage_root: Path, relative_path: str) -> Path | None:
    if not relative_path or Path(relative_path).is_absolute():
        return None
    candidate = (stage_root / relative_path).resolve()
    try:
        candidate.relative_to(stage_root.resolve())
    except ValueError:
        return None
    return candidate


def _norm_bbox(value: Any) -> tuple[Any, ...]:
    try:
        return tuple(int(round(float(item))) for item in (value or [])[:4])
    except (TypeError, ValueError):
        return tuple(value or [])


def _ordered_refs(value: Iterable[dict[str, Any]]) -> list[tuple[Any, str, tuple[Any, ...]]]:
    return [
        (
            ref.get("page"),
            str(ref.get("block_id") or ""),
            _norm_bbox(ref.get("bbox")),
        )
        for ref in value
        if isinstance(ref, dict)
    ]


def _markdown_target(markdown_path: Path, image_path: Path) -> tuple[bool, str]:
    try:
        text = markdown_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False, "markdown_unreadable"
    match = _IMAGE_RE.search(text)
    if not match:
        return False, "markdown_image_reference_missing"
    image_ref = (match.group(1) or match.group(2) or "").strip()
    if not image_ref or image_ref.startswith(("http:", "https:", "data:")):
        return False, "markdown_image_reference_external"
    resolved = (markdown_path.parent / image_ref).resolve()
    if resolved != image_path.resolve():
        return False, "markdown_image_reference_mismatch"
    return True, "success"


def _provenance_records(path: Path) -> dict[str, dict[str, Any]] | None:
    if not path.is_file():
        return {}
    payload = _read_json(path)
    if payload is None:
        return None
    records = payload.get("objects")
    if not isinstance(records, list):
        return None
    return {
        str(record.get("render_path")): record
        for record in records
        if isinstance(record, dict) and record.get("render_path")
    }


def _validate_plan(
    root: Path,
    stage_root: Path,
    manifest: dict[str, Any],
    plan: dict[str, Any],
    rows: list[dict[str, Any]],
    conflicts_by_id: dict[str, dict[str, Any]],
    provenance: dict[str, dict[str, Any]] | None,
    live_snapshot: str,
) -> tuple[list[str], dict[str, Any] | None]:
    object_id = str(plan.get("object_id") or "")
    errors: list[str] = []
    identity = plan.get("canonical_identity") or {}
    if not object_id or identity.get("figure_id") != object_id:
        errors.append("canonical_identity_mismatch")
    if plan.get("input_snapshot_hash") != manifest.get("input_snapshot_hash"):
        errors.append("manifest_plan_snapshot_mismatch")
    if plan.get("input_snapshot_hash") != live_snapshot:
        errors.append("STALE_R_PLAN")
    if plan.get("plan_hash") != _plan_hash(plan):
        errors.append("plan_hash_mismatch")

    if object_id in conflicts_by_id:
        errors.append("inventory_duplicate_entry")
    matching_rows = [
        row
        for row in rows
        if row.get("_inventory_bucket") == "matched_figures"
        and str(row.get("figure_id") or "") == object_id
    ]
    if len(matching_rows) != 1:
        errors.append("canonical_occurrence_not_one")
    row = matching_rows[0] if len(matching_rows) == 1 else None

    planned_refs = _ordered_refs(plan.get("ordered_asset_refs") or [])
    current_refs = _ordered_refs((row or {}).get("matched_assets") or [])
    if row is not None and current_refs != planned_refs:
        errors.append("ordered_asset_refs_mismatch")
    ownership_keys = [(page, block_id) for page, block_id, _ in planned_refs]
    if any(not block_id for _, block_id in ownership_keys):
        errors.append("asset_ownership_missing_block_id")
    if len(ownership_keys) != len(set(ownership_keys)):
        errors.append("asset_ownership_not_unique")

    expected_staged_asset = f"assets/figures/{object_id}.jpg"
    expected_staged_markdown = f"render/figures/{object_id}.md"
    expected_production_asset = expected_staged_asset
    expected_production_markdown = expected_staged_markdown
    if plan.get("staged_asset") != expected_staged_asset:
        errors.append("staged_asset_path_mismatch")
    if plan.get("staged_markdown") != expected_staged_markdown:
        errors.append("staged_markdown_path_mismatch")
    if plan.get("production_asset") != expected_production_asset:
        errors.append("production_asset_path_mismatch")
    if plan.get("production_markdown") != expected_production_markdown:
        errors.append("production_markdown_path_mismatch")

    staged_asset = _safe_stage_path(stage_root, expected_staged_asset)
    staged_markdown = _safe_stage_path(stage_root, expected_staged_markdown)
    if staged_asset is None or staged_markdown is None:
        errors.append("staged_path_unsafe")
        return sorted(set(errors)), None
    image_facts = _image_facts(staged_asset)
    markdown_hash = _sha256_path(staged_markdown)
    if image_facts is None:
        errors.append("staged_image_invalid")
    if markdown_hash is None:
        errors.append("staged_markdown_missing")
    link_ok, link_reason = _markdown_target(staged_markdown, staged_asset)
    if not link_ok:
        errors.append(link_reason)

    staged_verification = plan.get("staged_verification") or {}
    stored_image = staged_verification.get("image") or {}
    if not image_facts or stored_image.get("sha256") != image_facts.get("sha256"):
        errors.append("staged_image_hash_mismatch")
    if image_facts and (
        stored_image.get("width") != image_facts.get("width")
        or stored_image.get("height") != image_facts.get("height")
    ):
        errors.append("staged_image_dimensions_mismatch")
    if staged_verification.get("markdown_sha256") != markdown_hash:
        errors.append("staged_markdown_hash_mismatch")
    if staged_verification.get("status") != "passed":
        errors.append("staged_verification_not_passed")

    render_path = expected_staged_markdown.replace("\\", "/")
    record = (provenance or {}).get(render_path)
    if record is None:
        errors.append("staging_provenance_missing")
    else:
        if record.get("status") not in _SUCCESS_MATERIALIZATION_STATUSES:
            errors.append("staging_provenance_not_success")
        if str(record.get("asset_path") or "").replace("\\", "/") != expected_staged_asset:
            errors.append("staging_provenance_asset_mismatch")

    if errors or image_facts is None or markdown_hash is None:
        return sorted(set(errors)), None
    return [], {
        "object_id": object_id,
        "plan": plan,
        "staged_asset": staged_asset,
        "staged_markdown": staged_markdown,
        "image_facts": image_facts,
        "markdown_sha256": markdown_hash,
        "staging_provenance": record or {},
    }


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _cleanup_backup_dir(path: Path) -> None:
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_file():
            child.unlink(missing_ok=True)
    path.rmdir()


def _snapshot_files(paths: list[Path]) -> tuple[Path, list[dict[str, Any]]]:
    backup_dir = Path(tempfile.mkdtemp(prefix="paperforge-r-rollback-"))
    snapshots: list[dict[str, Any]] = []
    try:
        unique_paths = list(dict.fromkeys(paths))
        for index, destination in enumerate(unique_paths):
            existed = destination.is_file()
            backup = backup_dir / f"{index}.bak"
            if existed:
                shutil.copy2(destination, backup)
            snapshots.append(
                {
                    "destination": destination,
                    "existed": existed,
                    "backup": backup if existed else None,
                }
            )
    except Exception:
        _cleanup_backup_dir(backup_dir)
        raise
    return backup_dir, snapshots


def _restore_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.restore")
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _restore_snapshots(snapshots: list[dict[str, Any]]) -> None:
    for snapshot in reversed(snapshots):
        destination = snapshot["destination"]
        if snapshot["existed"]:
            _restore_file(snapshot["backup"], destination)
        else:
            destination.unlink(missing_ok=True)


def _merge_provenance(
    path: Path,
    prepared: list[dict[str, Any]],
) -> dict[str, Any]:
    existing = _read_json(path) if path.is_file() else {}
    if existing is None:
        raise ValueError("production_provenance_unreadable")
    records_value = existing.get("objects")
    records: list[dict[str, Any]] = (
        [record for record in records_value if isinstance(record, dict)]
        if isinstance(records_value, list)
        else []
    )
    by_path = {
        str(record.get("render_path")): dict(record)
        for record in records
        if record.get("render_path")
    }
    for item in prepared:
        plan = item["plan"]
        render_path = str(plan["production_markdown"])
        record = dict(item.get("staging_provenance") or {})
        record.update(
            {
                "object_id": item["object_id"],
                "kind": "figure",
                "status": "materialized",
                "stage": "reconcile_promote_r",
                "reason": "success",
                "asset_path": str(plan["production_asset"]),
                "render_path": render_path,
                "input_snapshot_hash": plan["input_snapshot_hash"],
                "ordered_asset_refs": plan["ordered_asset_refs"],
                "plan_hash": plan["plan_hash"],
                "output": {
                    "image_sha256": item["image_facts"]["sha256"],
                    "width": item["image_facts"]["width"],
                    "height": item["image_facts"]["height"],
                    "markdown_sha256": item["markdown_sha256"],
                },
            }
        )
        by_path[render_path] = record
    output = dict(existing)
    output["schema_version"] = max(int(output.get("schema_version") or 1), 1)
    output["objects"] = sorted(by_path.values(), key=lambda item: (item.get("kind", ""), item.get("object_id", "")))
    summary: dict[str, dict[str, int]] = {"status": {}, "stage": {}, "reason": {}}
    for record in output["objects"]:
        for field in summary:
            value = str(record.get(field) or "unknown")
            summary[field][value] = summary[field].get(value, 0) + 1
    output["summary"] = {"objects": len(output["objects"]), **summary}
    return output


def _issue_mentions_object(issue: dict[str, Any], object_id: str) -> bool:
    evidence = issue.get("evidence") or {}
    if evidence.get("canonical_object_id") == object_id:
        return True
    if evidence.get("file") == f"{object_id}.md":
        return True
    return any(
        candidate.get("canonical_object_id") == object_id
        for candidate in evidence.get("canonical_candidates") or []
        if isinstance(candidate, dict)
    )


def _audit_targets(report: dict[str, Any], object_id: str) -> list[str]:
    return [
        str(issue.get("type"))
        for issue in report.get("issues") or []
        if isinstance(issue, dict) and _issue_mentions_object(issue, object_id)
    ]


def promote_r(
    ocr_root: Path,
    paper_key: str,
    object_ids: Iterable[str] | None = None,
    *,
    staging_root: Path | None = None,
) -> dict[str, Any]:
    """Promote selected verified R plans without re-materializing them."""
    root = Path(ocr_root) / paper_key
    stage_root = _find_staging_root(paper_key, staging_root)
    if stage_root is None:
        return {"ok": False, "reason": "r_manifest_not_found", "paper_key": paper_key}
    manifest_path = stage_root / _MANIFEST_NAME
    manifest = _read_json(manifest_path)
    if manifest is None:
        return {"ok": False, "reason": "r_manifest_unreadable", "paper_key": paper_key}
    if manifest.get("kind") != "R" or manifest.get("paper_key") != paper_key:
        return {"ok": False, "reason": "r_manifest_invalid", "paper_key": paper_key}

    plans = [plan for plan in manifest.get("plans") or [] if isinstance(plan, dict)]
    by_id: dict[str, dict[str, Any]] = {}
    manifest_errors: dict[str, list[str]] = {}
    for plan in plans:
        object_id = str(plan.get("object_id") or "")
        if not object_id or object_id in by_id:
            manifest_errors.setdefault(object_id or "<missing>", []).append("manifest_object_id_not_unique")
        else:
            by_id[object_id] = plan
    requested = {str(value) for value in (object_ids or []) if str(value)}
    unknown = sorted(requested - set(by_id))
    if unknown:
        return {
            "ok": False,
            "reason": "r_object_not_in_manifest",
            "paper_key": paper_key,
            "staging_root": str(stage_root),
            "unknown_object_ids": unknown,
        }
    selected = [by_id[key] for key in sorted(requested)] if requested else [by_id[key] for key in sorted(by_id)]
    if not selected:
        return {
            "ok": False,
            "reason": "r_manifest_has_no_plans",
            "paper_key": paper_key,
            "staging_root": str(stage_root),
        }

    live_snapshot = _snapshot_hash(root)
    if manifest.get("input_snapshot_hash") != live_snapshot:
        return {
            "ok": False,
            "reason": "STALE_R_MANIFEST",
            "paper_key": paper_key,
            "staging_root": str(stage_root),
            "manifest_snapshot": manifest.get("input_snapshot_hash"),
            "live_snapshot": live_snapshot,
        }
    rows = _inventory_rows(root / "structure" / "figure_inventory.json", "figure")
    conflicts = _inventory_identity_conflicts(rows, "figure")
    conflicts_by_id = {str(item["canonical_object_id"]): item for item in conflicts}
    provenance_path = _safe_stage_path(stage_root, str(manifest.get("staging_provenance") or ""))
    provenance = _provenance_records(provenance_path) if provenance_path else None

    validations: list[dict[str, Any]] = []
    prepared: list[dict[str, Any]] = []
    for plan in selected:
        object_id = str(plan.get("object_id") or "")
        errors = manifest_errors.get(object_id, [])
        if provenance is None:
            errors = [*errors, "staging_provenance_unreadable"]
        if not errors:
            errors, item = _validate_plan(
                root,
                stage_root,
                manifest,
                plan,
                rows,
                conflicts_by_id,
                provenance,
                live_snapshot,
            )
            if item is not None:
                prepared.append(item)
        validations.append({"object_id": object_id, "ok": not errors, "gates": errors})
    if any(not item["ok"] for item in validations):
        return {
            "ok": False,
            "reason": "R_GATE_FAILED",
            "paper_key": paper_key,
            "staging_root": str(stage_root),
            "objects": validations,
        }

    before_audit = audit_paper(Path(ocr_root), paper_key, write_report=False)
    destination_root = root
    production_provenance_path = destination_root / "render" / "materialization.provenance.json"
    if production_provenance_path.is_file() and _read_json(production_provenance_path) is None:
        return {
            "ok": False,
            "reason": "R_GATE_FAILED",
            "paper_key": paper_key,
            "staging_root": str(stage_root),
            "objects": validations,
            "global_gates": ["production_provenance_unreadable"],
        }
    promotion_states: dict[str, str] = {}
    promotion_targets = [
        destination_root / plan["production_asset"]
        for plan in (item["plan"] for item in prepared)
    ] + [
        destination_root / plan["production_markdown"]
        for plan in (item["plan"] for item in prepared)
    ] + [production_provenance_path]
    try:
        backup_dir, snapshots = _snapshot_files(promotion_targets)
    except Exception as exc:
        return {
            "ok": False,
            "reason": "R_PROMOTION_PREPARE_FAILED",
            "paper_key": paper_key,
            "staging_root": str(stage_root),
            "objects": validations,
            "error": f"{type(exc).__name__}: {exc}",
        }
    try:
        for item in prepared:
            plan = item["plan"]
            production_asset = destination_root / plan["production_asset"]
            production_markdown = destination_root / plan["production_markdown"]
            image_same = _sha256_path(production_asset) == item["image_facts"]["sha256"]
            markdown_same = _sha256_path(production_markdown) == item["markdown_sha256"]
            if image_same and markdown_same:
                promotion_states[item["object_id"]] = "already_promoted"
                continue
            _atomic_copy(item["staged_asset"], production_asset)
            _atomic_copy(item["staged_markdown"], production_markdown)
            promotion_states[item["object_id"]] = "promoted"
        production_provenance = _merge_provenance(production_provenance_path, prepared)
        if _read_json(production_provenance_path) != production_provenance:
            _write_json_atomic(production_provenance_path, production_provenance)
    except Exception as exc:
        rollback_error: str | None = None
        try:
            _restore_snapshots(snapshots)
        except Exception as rollback_exc:
            rollback_error = f"{type(rollback_exc).__name__}: {rollback_exc}"
        result = {
            "ok": False,
            "reason": "R_PROMOTION_WRITE_FAILED",
            "paper_key": paper_key,
            "staging_root": str(stage_root),
            "objects": validations,
            "rolled_back": rollback_error is None,
            "error": f"{type(exc).__name__}: {exc}",
        }
        if rollback_error:
            result["rollback_error"] = rollback_error
        return result
    finally:
        _cleanup_backup_dir(backup_dir)

    after_audit = audit_paper(Path(ocr_root), paper_key, write_report=True)
    target_delta = {
        item["object_id"]: {
            "before": _audit_targets(before_audit, item["object_id"]),
            "after": _audit_targets(after_audit, item["object_id"]),
        }
        for item in prepared
    }
    return {
        "ok": True,
        "paper_key": paper_key,
        "staging_root": str(stage_root),
        "promoted": [item["object_id"] for item in prepared],
        "promotion_states": promotion_states,
        "objects": validations,
        "audit_1": {
            "before_state": before_audit.get("state"),
            "after_state": after_audit.get("state"),
            "before_issues": len(before_audit.get("issues") or []),
            "after_issues": len(after_audit.get("issues") or []),
            "target_delta": target_delta,
        },
        "production_write": True,
    }
