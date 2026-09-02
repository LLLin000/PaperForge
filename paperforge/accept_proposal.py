"""Accept a reviewed P proposal and promote it to canonical inventory.

The caller-supplied SHA-256 token selects the exact reviewed
``final-plan.json``; that plan is the authority for accepted member refs.
Production writes use the same paper-scoped journal, CAS, audit, and recovery
contract as R promotion; this module never re-matches the proposal.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from paperforge.promote_r import (
    _IMAGE_RE,
    _atomic_copy,
    _audit_failed,
    _cleanup_backup_dir,
    _image_facts,
    _issue_mentions_object,
    _mark_transaction_committed,
    _merge_provenance,
    _promotion_audit,
    _raw_path_has_symlink,
    _recover_pending_transaction,
    _restore_snapshots,
    _sha256_path,
    _snapshot_files,
    _snapshot_hash,
    _write_json_atomic,
)
from paperforge.render_audit import (
    _inventory_asset_claim_conflicts,
    _inventory_identity_conflicts,
    _inventory_rows,
    audit_paper,
)

_FINAL_P_DECISIONS = {
    "structurally_unique_proposal",
    "unique_without_pdf_confirmation",
}


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _finish_transaction(root: Path, transaction_dir: Path) -> None:
    _cleanup_backup_dir(transaction_dir)
    (root / ".paperforge-r-promotion.json").unlink(missing_ok=True)


def _read_json_object(
    path: Path, *, missing_ok: bool
) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return ({}, None) if missing_ok else (None, "missing")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, TypeError, ValueError):
        return None, "unreadable"
    if not isinstance(value, dict):
        return None, "not_object"
    return value, None


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _asset_key(value: dict[str, Any]) -> tuple[Any, str, tuple[int, ...]]:
    page = value.get("page")
    if page is None or isinstance(page, bool):
        raise ValueError("page_missing")
    try:
        page = int(page)
    except (TypeError, ValueError, OverflowError):
        page = str(page)
    block_id = str(value.get("block_id") or "")
    if not block_id:
        raise ValueError("block_id_missing")
    bbox_value = value.get("bbox")
    if not isinstance(bbox_value, (list, tuple)) or len(bbox_value) != 4:
        raise ValueError("bbox_invalid")
    try:
        bbox = tuple(int(round(float(item))) for item in bbox_value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("bbox_invalid") from exc
    return page, block_id, bbox


def _validated_member_refs(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, list) or not value:
        return None
    refs: list[dict[str, Any]] = []
    seen: set[tuple[Any, str, tuple[int, ...]]] = set()
    for raw_ref in value:
        if not isinstance(raw_ref, dict):
            return None
        try:
            key = _asset_key(raw_ref)
        except ValueError:
            return None
        if key in seen:
            return None
        seen.add(key)
        refs.append(dict(raw_ref))
    return refs


def _markdown_targets_image(
    text: str, markdown_parent: Path, image_path: Path
) -> bool:
    match = _IMAGE_RE.search(text)
    if not match:
        return False
    image_ref = (match.group(1) or match.group(2) or "").strip()
    if not image_ref or image_ref.startswith(("http:", "https:", "data:")):
        return False
    try:
        return (markdown_parent / image_ref).resolve() == image_path.resolve()
    except (OSError, RuntimeError):
        return False


def _rollback_transaction(
    root: Path,
    transaction_dir: Path,
    snapshots: list[dict[str, Any]],
) -> tuple[str | None, dict[str, Any] | None]:
    rollback_error: str | None = None
    rollback_audit: dict[str, Any] | None = None
    try:
        _restore_snapshots(snapshots, verify_cas=True)
    except Exception as exc:  # noqa: BLE001 — preserve journal on rollback conflict
        rollback_error = f"{type(exc).__name__}: {exc}"
    if rollback_error is None:
        try:
            rollback_audit = _promotion_audit(
                root.parent, root.name, write_report=False
            )
        except Exception as exc:  # noqa: BLE001 — keep cleanup recoverable
            rollback_error = f"{type(exc).__name__}: {exc}"
        try:
            _finish_transaction(root, transaction_dir)
        except Exception as exc:  # noqa: BLE001 — recovery can finish next call
            if rollback_error is None:
                rollback_error = f"{type(exc).__name__}: {exc}"
    return rollback_error, rollback_audit


def _accept_proposal_unlocked(
    ocr_root: Path,
    paper_key: str,
    label: str,
    plan_hash: str | None,
) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", str(paper_key)):
        return {
            "ok": False,
            "reason": "paper_key_invalid",
            "paper_key": paper_key,
            "label": label,
        }
    root = Path(ocr_root) / paper_key
    if not root.is_dir() or root.is_symlink():
        return {
            "ok": False,
            "reason": "paper_missing",
            "paper_key": paper_key,
            "label": label,
        }
    if plan_hash is None:
        return {
            "ok": False,
            "reason": "review_plan_hash_missing",
            "paper_key": paper_key,
            "label": label,
        }
    if not isinstance(plan_hash, str) or not re.fullmatch(
        r"[0-9a-f]{64}", plan_hash
    ):
        return {
            "ok": False,
            "reason": "review_plan_hash_invalid",
            "paper_key": paper_key,
            "label": label,
        }

    recovery_error = _recover_pending_transaction(root)
    if recovery_error:
        return {
            "ok": False,
            "reason": "ACCEPT_PROPOSAL_RECOVERY_REQUIRED",
            "paper_key": paper_key,
            "label": label,
            "error": recovery_error,
        }

    if not re.fullmatch(r"[1-9]\d*", str(label)):
        return {
            "ok": False,
            "reason": "proposal_label_invalid",
            "paper_key": paper_key,
            "label": label,
        }
    label = str(label)
    try:
        number = int(label)
    except (TypeError, ValueError, OverflowError):
        return {
            "ok": False,
            "reason": "proposal_label_invalid",
            "paper_key": paper_key,
            "label": label,
        }
    canonical_id = f"figure_{number:03d}"

    if _raw_path_has_symlink(root, ".paperforge-r-promotion.lock"):
        return {
            "ok": False,
            "reason": "ACCEPT_PROPOSAL_PATH_UNSAFE",
            "paper_key": paper_key,
            "label": label,
        }
    inventory_path = root / "structure" / "figure_inventory.json"
    asset_path = root / "assets" / "figures" / f"{canonical_id}.jpg"
    markdown_path = root / "render" / "figures" / f"{canonical_id}.md"
    provenance_path = root / "render" / "materialization.provenance.json"
    reconciliation_path = root / "render" / "reconciliation.proposals.json"
    destinations = (
        ("structure/figure_inventory.json", inventory_path),
        (f"assets/figures/{canonical_id}.jpg", asset_path),
        (f"render/figures/{canonical_id}.md", markdown_path),
        ("render/materialization.provenance.json", provenance_path),
        ("render/reconciliation.proposals.json", reconciliation_path),
    )
    if any(_raw_path_has_symlink(root, relative) for relative, _ in destinations):
        return {
            "ok": False,
            "reason": "ACCEPT_PROPOSAL_PATH_UNSAFE",
            "paper_key": paper_key,
            "label": label,
        }
    if asset_path.exists() or markdown_path.exists():
        return {
            "ok": False,
            "reason": "canonical_destination_exists",
            "paper_key": paper_key,
            "label": label,
        }

    staging_base = Path(tempfile.gettempdir()) / "paperforge-staging"
    pattern = f"*_{paper_key}/{paper_key}/previews/figure_{label}"
    candidates: list[tuple[Path, bytes]] = []
    if staging_base.is_dir() and not staging_base.is_symlink():
        for directory in sorted(
            staging_base.glob(pattern), key=lambda path: path.as_posix()
        ):
            plan_candidate = directory / "final-plan.json"
            try:
                relative_directory = directory.relative_to(staging_base).as_posix()
                relative_plan = plan_candidate.relative_to(staging_base).as_posix()
            except (OSError, ValueError):
                continue
            if (
                not directory.is_dir()
                or directory.is_symlink()
                or _raw_path_has_symlink(staging_base, relative_directory)
                or not plan_candidate.is_file()
                or plan_candidate.is_symlink()
                or _raw_path_has_symlink(staging_base, relative_plan)
            ):
                continue
            try:
                candidate_plan_bytes = plan_candidate.read_bytes()
            except (OSError, UnicodeError):
                continue
            if hashlib.sha256(candidate_plan_bytes).hexdigest() == plan_hash:
                candidates.append((directory, candidate_plan_bytes))
    if not candidates:
        return {
            "ok": False,
            "reason": "STALE_REVIEWED_PLAN",
            "paper_key": paper_key,
            "label": label,
            "plan_hash": plan_hash,
        }
    preview_dir, plan_bytes = candidates[0]
    try:
        plan = json.loads(plan_bytes.decode("utf-8"))
    except (OSError, UnicodeError, TypeError, ValueError):
        return {
            "ok": False,
            "reason": "staging_final_plan_unreadable",
            "paper_key": paper_key,
            "label": label,
        }
    if not isinstance(plan, dict) or plan.get("schema_version") != 1:
        return {
            "ok": False,
            "reason": "staging_final_plan_invalid",
            "paper_key": paper_key,
            "label": label,
        }
    if str(plan.get("label") or "") != label:
        return {
            "ok": False,
            "reason": "proposal_label_mismatch",
            "paper_key": paper_key,
            "label": label,
        }
    if not isinstance(plan.get("proposal_id"), str) or not plan["proposal_id"]:
        return {
            "ok": False,
            "reason": "proposal_metadata_missing",
            "paper_key": paper_key,
            "label": label,
        }
    if plan.get("decision") not in _FINAL_P_DECISIONS:
        return {
            "ok": False,
            "reason": "not_final_p_reviewable",
            "paper_key": paper_key,
            "label": label,
            "decision": plan.get("decision"),
        }

    staged_snapshot = plan.get("input_snapshot_hash")
    if not isinstance(staged_snapshot, str) or not re.fullmatch(
        r"[0-9a-f]{16}", staged_snapshot
    ):
        return {
            "ok": False,
            "reason": "proposal_snapshot_missing",
            "paper_key": paper_key,
            "label": label,
        }
    live_snapshot = _snapshot_hash(root)
    if staged_snapshot != live_snapshot:
        return {
            "ok": False,
            "reason": "STALE_PROPOSAL",
            "paper_key": paper_key,
            "label": label,
            "staged_snapshot": staged_snapshot,
            "live_snapshot": live_snapshot,
        }

    expected_staged_jpg = f"assets/figures/figure_proposal_{label}.jpg"
    expected_staged_md = f"render/figures/figure_proposal_{label}.md"
    if (
        plan.get("staged_jpg") != expected_staged_jpg
        or plan.get("staged_md") != expected_staged_md
    ):
        return {
            "ok": False,
            "reason": "staging_path_mismatch",
            "paper_key": paper_key,
            "label": label,
        }
    staged_jpg = preview_dir / expected_staged_jpg
    staged_md = preview_dir / expected_staged_md
    if _raw_path_has_symlink(preview_dir, expected_staged_jpg) or _raw_path_has_symlink(
        preview_dir, expected_staged_md
    ):
        return {
            "ok": False,
            "reason": "staged_path_unsafe",
            "paper_key": paper_key,
            "label": label,
        }
    if not staged_jpg.is_file() or staged_jpg.is_symlink():
        return {
            "ok": False,
            "reason": "staged_jpg_missing",
            "paper_key": paper_key,
            "label": label,
            "expected": str(staged_jpg),
        }
    image_facts = _image_facts(staged_jpg)
    if image_facts is None or not isinstance(image_facts.get("sha256"), str):
        return {
            "ok": False,
            "reason": "staged_jpg_invalid",
            "paper_key": paper_key,
            "label": label,
        }
    if staged_md.is_file():
        if staged_md.is_symlink():
            return {
                "ok": False,
                "reason": "staged_md_unsafe",
                "paper_key": paper_key,
                "label": label,
            }
        try:
            markdown = staged_md.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return {
                "ok": False,
                "reason": "staged_md_unreadable",
                "paper_key": paper_key,
                "label": label,
            }
        markdown = markdown.replace(
            f"figure_proposal_{label}.jpg", f"{canonical_id}.jpg"
        ).replace(f"figure_proposal_{label}", canonical_id)
        header_match = re.search(
            r"^#\s+Figure\b[^\n]*$", markdown, re.IGNORECASE | re.MULTILINE
        )
        if header_match:
            markdown = (
                markdown[: header_match.start()]
                + f"# Figure {label}"
                + markdown[header_match.end() :]
            )
        else:
            markdown = f"# Figure {label}\n\n{markdown.lstrip()}"
    else:
        caption_text = str(plan.get("caption_text") or "")
        lines = [
            f"# Figure {label}",
            "",
            f"![](../../assets/figures/{canonical_id}.jpg)",
            "",
            "## Legend",
            caption_text or f"Figure {label} (accepted proposal)",
            "",
        ]
        if plan.get("page") is not None:
            lines.extend([f"*Page {plan['page']}*", ""])
        lines.extend(["---", ""])
        markdown = "\n".join(lines)
    expected_staged_image = preview_dir / "assets" / "figures" / f"{canonical_id}.jpg"
    if not _markdown_targets_image(
        markdown, staged_md.parent, expected_staged_image
    ):
        return {
            "ok": False,
            "reason": "staged_md_image_reference_invalid",
            "paper_key": paper_key,
            "label": label,
        }
    markdown_bytes = markdown.encode("utf-8")
    markdown_hash = hashlib.sha256(markdown_bytes).hexdigest()

    member_refs = _validated_member_refs(plan.get("member_refs"))
    if member_refs is None:
        return {
            "ok": False,
            "reason": "member_refs_invalid",
            "paper_key": paper_key,
            "label": label,
        }

    inventory, inventory_error = _read_json_object(
        inventory_path, missing_ok=False
    )
    if inventory_error or inventory is None:
        return {
            "ok": False,
            "reason": "canonical_inventory_unavailable",
            "paper_key": paper_key,
            "label": label,
            "error": inventory_error,
        }
    matched = inventory.get("matched_figures")
    if not isinstance(matched, list) or any(
        not isinstance(row, dict) for row in matched
    ):
        return {
            "ok": False,
            "reason": "canonical_inventory_invalid",
            "paper_key": paper_key,
            "label": label,
        }
    reconciliation, reconciliation_error = _read_json_object(
        reconciliation_path, missing_ok=True
    )
    if reconciliation_error or reconciliation is None:
        return {
            "ok": False,
            "reason": "reconciliation_report_unavailable",
            "paper_key": paper_key,
            "label": label,
            "error": reconciliation_error,
        }
    if "proposals" in reconciliation and not isinstance(
        reconciliation["proposals"], list
    ):
        return {
            "ok": False,
            "reason": "reconciliation_report_invalid",
            "paper_key": paper_key,
            "label": label,
        }
    proposal_id = plan["proposal_id"]
    if not any(
        isinstance(proposal, dict)
        and str(proposal.get("label") or "") == label
        and str(proposal.get("proposal_id") or "") == proposal_id
        for proposal in reconciliation["proposals"]
    ):
        return {
            "ok": False,
            "reason": "proposal_not_current",
            "paper_key": paper_key,
            "label": label,
            "proposal_id": proposal_id,
        }

    try:
        existing_rows = _inventory_rows(inventory_path, "figure")
        identity_conflicts = _inventory_identity_conflicts(existing_rows, "figure")
    except Exception as exc:  # noqa: BLE001 — malformed authority fails closed
        return {
            "ok": False,
            "reason": "canonical_inventory_invalid",
            "paper_key": paper_key,
            "label": label,
            "error": f"{type(exc).__name__}: {exc}",
        }
    if identity_conflicts:
        return {
            "ok": False,
            "reason": "canonical_inventory_ambiguous",
            "paper_key": paper_key,
            "label": label,
        }
    if any(str(row.get("figure_id") or "") == canonical_id for row in matched):
        return {
            "ok": False,
            "reason": "canonical_target_exists",
            "paper_key": paper_key,
            "label": label,
        }
    for row in matched:
        row_id = str(row.get("figure_id") or "").lower()
        if row_id.startswith("figure_reserved_") or "reserved" in str(
            row.get("settlement_type") or ""
        ).lower():
            continue
        try:
            row_number = int(row.get("figure_number"))
        except (TypeError, ValueError, OverflowError):
            row_number = None
        if row_number == number:
            return {
                "ok": False,
                "reason": "canonical_label_exists",
                "paper_key": paper_key,
                "label": label,
            }

    prospective_rows = [
        *existing_rows,
        {
            "_inventory_bucket": "matched_figures",
            "canonical_object_id": canonical_id,
            "figure_id": canonical_id,
            "figure_number": number,
            "figure_namespace": "main",
            "matched_assets": member_refs,
        },
    ]
    try:
        claim_conflicts = _inventory_asset_claim_conflicts(
            prospective_rows, "figure"
        )
    except Exception as exc:  # noqa: BLE001 — malformed authority fails closed
        return {
            "ok": False,
            "reason": "canonical_inventory_invalid",
            "paper_key": paper_key,
            "label": label,
            "error": f"{type(exc).__name__}: {exc}",
        }
    if any(canonical_id in conflict["owners"] for conflict in claim_conflicts):
        return {
            "ok": False,
            "reason": "member_refs_claim_conflict",
            "paper_key": paper_key,
            "label": label,
            "conflicts": claim_conflicts,
        }

    plan_hash = hashlib.sha256(plan_bytes).hexdigest()
    updated_inventory = json.loads(json.dumps(inventory, ensure_ascii=False))
    updated_inventory["matched_figures"].append(
        {
            "figure_id": canonical_id,
            "figure_number": number,
            "figure_namespace": "main",
            "page": plan.get("page"),
            "text": str(plan.get("caption_text") or ""),
            "matched_assets": member_refs,
            "asset_block_ids": [
                str(asset["block_id"])
                for asset in member_refs
                if asset.get("block_id")
            ],
            "settlement_type": "accepted_proposal",
            "confidence": 1.0,
            "accepted_from": {
                "staging_dir": str(preview_dir),
                "final_plan_hash": plan_hash,
            },
        }
    )
    updated_reconciliation = json.loads(
        json.dumps(reconciliation, ensure_ascii=False)
    )
    proposals = updated_reconciliation.setdefault("proposals", [])
    updated_reconciliation["proposals"] = [
        proposal
        for proposal in proposals
        if not isinstance(proposal, dict)
        or str(proposal.get("label") or "") != label
        or str(proposal.get("proposal_id") or "") != proposal_id
    ]
    summary = updated_reconciliation.get("summary")
    if isinstance(summary, dict):
        summary["proposals"] = len(updated_reconciliation["proposals"])

    prepared = [
        {
            "object_id": canonical_id,
            "plan": {
                "production_asset": f"assets/figures/{canonical_id}.jpg",
                "production_markdown": f"render/figures/{canonical_id}.md",
                "input_snapshot_hash": staged_snapshot,
                "ordered_asset_refs": member_refs,
                "plan_hash": plan_hash,
            },
            "staging_provenance": {},
            "image_facts": image_facts,
            "markdown_sha256": markdown_hash,
        }
    ]
    try:
        updated_provenance = _merge_provenance(provenance_path, prepared)
    except Exception as exc:  # noqa: BLE001 — malformed provenance fails closed
        return {
            "ok": False,
            "reason": "production_provenance_unavailable",
            "paper_key": paper_key,
            "label": label,
            "error": f"{type(exc).__name__}: {exc}",
        }

    before_audit = _promotion_audit(root.parent, root.name, write_report=False)
    if _audit_failed(before_audit):
        return {
            "ok": False,
            "reason": "ACCEPT_PROPOSAL_PREAUDIT_FAILED",
            "paper_key": paper_key,
            "label": label,
            "audit_0": before_audit,
            "production_write": False,
        }

    inventory_bytes = _json_bytes(updated_inventory)
    provenance_bytes = _json_bytes(updated_provenance)
    reconciliation_bytes = _json_bytes(updated_reconciliation)
    expected_output_hashes = {
        asset_path: image_facts["sha256"],
        markdown_path: markdown_hash,
        inventory_path: hashlib.sha256(inventory_bytes).hexdigest(),
        provenance_path: hashlib.sha256(provenance_bytes).hexdigest(),
        reconciliation_path: hashlib.sha256(reconciliation_bytes).hexdigest(),
    }
    output_preconditions = {
        path: {"exists": True, "sha256": output_hash}
        for path, output_hash in expected_output_hashes.items()
    }
    try:
        transaction_dir, snapshots = _snapshot_files(
            root,
            [
                asset_path,
                markdown_path,
                inventory_path,
                provenance_path,
                reconciliation_path,
            ],
            output_preconditions=output_preconditions,
        )
    except Exception as exc:
        return {
            "ok": False,
            "reason": "ACCEPT_PROPOSAL_PREPARE_FAILED",
            "paper_key": paper_key,
            "label": label,
            "error": f"{type(exc).__name__}: {exc}",
        }

    try:
        _atomic_copy(staged_jpg, asset_path)
        _atomic_write_bytes(markdown_path, markdown_bytes)
        _write_json_atomic(inventory_path, updated_inventory)
        _write_json_atomic(provenance_path, updated_provenance)
        _write_json_atomic(reconciliation_path, updated_reconciliation)

        postcondition_errors: list[str] = []
        for destination, expected_hash in expected_output_hashes.items():
            if _sha256_path(destination) != expected_hash:
                postcondition_errors.append(
                    "output_hash_mismatch:"
                    + destination.relative_to(root).as_posix()
                )
        post_audit = _promotion_audit(root.parent, root.name, write_report=False)
        if not isinstance(post_audit, dict):
            post_audit = {
                "state": "FAILED",
                "issues": [
                    {
                        "type": "audit_execution_failure",
                        "message": "audit returned a non-object result",
                    }
                ],
            }
        if _audit_failed(post_audit):
            postcondition_errors.append("post_audit_failed")
        target_issues = [
            str(issue.get("type"))
            for issue in post_audit.get("issues") or []
            if isinstance(issue, dict)
            and _issue_mentions_object(issue, canonical_id)
            and issue.get("severity") in {"P0", "P1"}
        ]
        postcondition_errors.extend(
            f"target_high_issue:{issue_type}" for issue_type in target_issues
        )
        if postcondition_errors:
            rollback_error, rollback_audit = _rollback_transaction(
                root, transaction_dir, snapshots
            )
            result = {
                "ok": False,
                "reason": "ACCEPT_PROPOSAL_POSTVERIFY_FAILED",
                "paper_key": paper_key,
                "label": label,
                "canonical_id": canonical_id,
                "postcondition_errors": postcondition_errors,
                "post_audit_state": post_audit.get("state"),
                "rolled_back": rollback_error is None,
                "rollback_audit_state": (
                    rollback_audit.get("state") if rollback_audit else None
                ),
            }
            if rollback_error:
                result["rollback_error"] = rollback_error
            return result
        _mark_transaction_committed(root)
    except Exception as exc:
        rollback_error, rollback_audit = _rollback_transaction(
            root, transaction_dir, snapshots
        )
        result = {
            "ok": False,
            "reason": "ACCEPT_PROPOSAL_WRITE_FAILED",
            "paper_key": paper_key,
            "label": label,
            "canonical_id": canonical_id,
            "rolled_back": rollback_error is None,
            "error": f"{type(exc).__name__}: {exc}",
            "rollback_audit_state": (
                rollback_audit.get("state") if rollback_audit else None
            ),
        }
        if rollback_error:
            result["rollback_error"] = rollback_error
        return result

    cleanup_state = "done"
    cleanup_error: str | None = None
    try:
        _finish_transaction(root, transaction_dir)
    except OSError as exc:
        cleanup_state = "pending"
        cleanup_error = f"{type(exc).__name__}: {exc}"

    report_refresh = "written"
    report_refresh_error: str | None = None
    try:
        after_audit = audit_paper(root.parent, root.name, write_report=True)
        if not isinstance(after_audit, dict):
            raise TypeError("audit returned a non-object result")
    except Exception as exc:  # noqa: BLE001 — commit already completed
        after_audit = {
            "state": "FAILED",
            "issues": [
                {
                    "type": "audit_report_refresh_failure",
                    "message": f"{type(exc).__name__}: {exc}",
                }
            ],
        }
        report_refresh = "failed"
        report_refresh_error = f"{type(exc).__name__}: {exc}"

    result = {
        "ok": True,
        "paper_key": paper_key,
        "label": label,
        "canonical_id": canonical_id,
        "assets": str(asset_path),
        "markdown": str(markdown_path),
        "member_refs_count": len(member_refs),
        "staging_dir": str(preview_dir),
        "audit_0": before_audit,
        "audit_1": {
            "before_state": before_audit.get("state"),
            "after_state": after_audit.get("state"),
            "before_issues": len(before_audit.get("issues") or []),
            "after_issues": len(after_audit.get("issues") or []),
            "target_issues": target_issues,
        },
        "committed": True,
        "cleanup": cleanup_state,
        "report_refresh": report_refresh,
        "report_audit_state": after_audit.get("state"),
        "production_write": True,
    }
    if cleanup_error:
        result["cleanup_error"] = cleanup_error
    if report_refresh_error:
        result["report_refresh_error"] = report_refresh_error
    return result


def accept_proposal(
    ocr_root: Path,
    paper_key: str,
    label: str,
    plan_hash: str | None = None,
) -> dict[str, Any]:
    """Accept the exact reviewed P plan named by its SHA-256 token."""
    from filelock import FileLock, Timeout

    root = Path(ocr_root) / paper_key
    if not root.is_dir() or root.is_symlink():
        return {
            "ok": False,
            "reason": "paper_missing",
            "paper_key": paper_key,
            "label": label,
        }
    if _raw_path_has_symlink(root, ".paperforge-r-promotion.lock"):
        return {
            "ok": False,
            "reason": "ACCEPT_PROPOSAL_PATH_UNSAFE",
            "paper_key": paper_key,
            "label": label,
        }
    lock = FileLock(str(root / ".paperforge-r-promotion.lock"), timeout=0)
    try:
        with lock:
            return _accept_proposal_unlocked(
                ocr_root, paper_key, label, plan_hash
            )
    except Timeout:
        return {
            "ok": False,
            "reason": "ACCEPT_PROPOSAL_BUSY",
            "paper_key": paper_key,
            "label": label,
        }
