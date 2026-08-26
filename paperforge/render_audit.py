"""Read-only consistency audit for rendered paper artifacts.

V1 audits the render layer only. It never changes OCR blocks, inventories,
asset indexes, metadata, PDFs, or notes. Repair is intentionally out of scope.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
ALGORITHM_VERSION = 3
_LABEL_RE = re.compile(r"\b(?:fig(?:ure)?s?\.?|table|tab\.?|图|scheme)\s*([A-Z]?\d+)", re.IGNORECASE)
_HEADER_RE = re.compile(r"^#\s+(Figure|Table)\s+(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
_PAGE_RE = re.compile(r"\*Page\s+([0-9]+)\*", re.IGNORECASE)
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)|!\[\[([^\]]+)\]\]")


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_tree(root: Path, *, exclude_names: set[str] | None = None) -> str | None:
    if not root.exists():
        return None
    exclude_names = exclude_names or set()
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name not in exclude_names):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        file_hash = _sha256_file(path)
        if file_hash:
            digest.update(file_hash.encode("ascii"))
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _label(value: Any) -> str | None:
    if isinstance(value, int):
        return str(value)
    text = str(value or "").strip()
    if not text:
        return None
    if re.fullmatch(r"[A-Z]?\d+", text, re.IGNORECASE):
        return text.upper()
    match = _LABEL_RE.search(text)
    if match:
        return match.group(1).upper()
    match = re.search(r"(?:figure|table|fig|tab)[_-]([A-Z]?\d+)", text, re.IGNORECASE)
    return match.group(1).upper() if match else None


def _inventory_rows(path: Path, kind: str) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    data = _read_json(path)
    if kind == "figure":
        source_rows = [
            ("matched_figures", row) for row in (data.get("matched_figures") or [])
        ] + [
            ("unmatched_captions", row) for row in (data.get("unmatched_captions") or [])
        ]
    else:
        source_rows = [
            ("tables", row) for row in (data.get("tables") or [])
        ] + [
            ("held_tables", row) for row in (data.get("held_tables") or [])
        ] + [
            ("unmatched_captions", row) for row in (data.get("unmatched_captions") or [])
        ]
    result: list[dict[str, Any]] = []
    for bucket, row in source_rows:
        if not isinstance(row, dict):
            continue
        row = dict(row)
        row["_inventory_bucket"] = bucket
        row["canonical_object_id"] = row.get("figure_id") or row.get("table_id")
        row["normalized_label"] = _label(
            row.get("figure_number") if kind == "figure" else row.get("table_number")
        )
        if row["normalized_label"] is None:
            row["normalized_label"] = _label(row.get("text") or row.get("caption") or row.get("raw_label"))
        result.append(row)
    return result


def _canonical_inventory_bucket(kind: str) -> str:
    return "matched_figures" if kind == "figure" else "tables"


def _inventory_plan_payload(row: dict[str, Any], kind: str) -> dict[str, Any]:
    assets = []
    for asset in row.get("matched_assets") or []:
        if not isinstance(asset, dict):
            continue
        assets.append(
            {
                "page": asset.get("page"),
                "block_id": str(asset.get("block_id") or ""),
                "bbox": asset.get("bbox"),
            }
        )
    caption = row.get("text") or row.get("caption") or row.get("caption_text") or ""
    namespace_key = "figure_namespace" if kind == "figure" else "table_namespace"
    number_key = "figure_number" if kind == "figure" else "table_number"
    return {
        "canonical_object_id": row.get("canonical_object_id"),
        "namespace": str(row.get(namespace_key) or "main").lower(),
        "number": row.get(number_key),
        "page": row.get("page"),
        "legend_page": row.get("legend_page"),
        "rotation": int(row.get("rotation_correction_deg", 0) or 0),
        "cluster_bbox": row.get("cluster_bbox"),
        "matched_assets": assets,
        "caption": re.sub(r"\s+", " ", str(caption)).strip(),
    }


def _inventory_identity_conflicts(
    rows: list[dict[str, Any]], kind: str
) -> list[dict[str, Any]]:
    """Return duplicate canonical rows without selecting a winner.

    This is a reconcile/audit observer. It does not mutate inventory rows and
    deliberately treats both identical and conflicting duplicates as
    cardinality violations.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    bucket = _canonical_inventory_bucket(kind)
    for row in rows:
        if row.get("_inventory_bucket") != bucket:
            continue
        object_id = str(row.get("canonical_object_id") or "")
        if object_id:
            grouped.setdefault(object_id, []).append(row)

    conflicts: list[dict[str, Any]] = []
    for object_id, group in grouped.items():
        if len(group) < 2:
            continue
        payloads = [_inventory_plan_payload(row, kind) for row in group]
        digests = [
            hashlib.sha256(
                json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()[:16]
            for payload in payloads
        ]
        refs = [payload["matched_assets"] for payload in payloads]
        conflicts.append(
            {
                "canonical_object_id": object_id,
                "count": len(group),
                "duplicate_class": (
                    "DUPLICATE_IDENTICAL" if len(set(digests)) == 1 else "DUPLICATE_CONFLICTING"
                ),
                "row_digests": digests,
                "matched_asset_refs": refs,
                "pages": [row.get("page") for row in group],
                "namespaces": [
                    str(row.get("figure_namespace") or row.get("table_namespace") or "main").lower()
                    for row in group
                ],
            }
        )
    return sorted(conflicts, key=lambda item: str(item["canonical_object_id"]))
def _enrich_inventory_positions(root: Path, rows: list[dict[str, Any]], kind: str) -> None:
    if kind != "figure":
        return
    blocks_path = root / "structure" / "blocks.structured.jsonl"
    if not blocks_path.is_file():
        return
    blocks: list[dict[str, Any]] = []
    for line in blocks_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            block = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(block, dict):
            blocks.append(block)
    for row in rows:
        if row.get("legend_page") is not None:
            continue
        label = _label(row.get("figure_number")) or _label(row.get("text"))
        if label is None:
            continue
        candidates = [
            block
            for block in blocks
            if _label(block.get("text")) == label
            and (
                "caption" in str(block.get("role") or "").lower()
                or str(block.get("raw_label") or "").lower() == "figure_title"
            )
        ]
        row_page = _page_number(row.get("page"))
        if row_page is not None:
            page_candidates = [block for block in candidates if _page_number(block.get("page")) == row_page]
            candidates = page_candidates or candidates
        if candidates:
            row["legend_page"] = candidates[0].get("page")
            row["legend_block_id"] = candidates[0].get("block_id")




def _render_artifacts(render_root: Path, kind: str) -> list[dict[str, Any]]:
    if not render_root.is_dir():
        return []
    prefix = "figure_" if kind == "figure" else "table_"
    rows: list[dict[str, Any]] = []
    for path in sorted(render_root.glob(f"{prefix}*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        header = _HEADER_RE.search(text)
        expected_kind = "Figure" if kind == "figure" else "Table"
        header_label = None
        if header and header.group(1).lower() == expected_kind.lower():
            header_label = _label(header.group(2))
        legend_text = text.split("## Legend", 1)[1] if "## Legend" in text else ""
        legend_match = _LABEL_RE.search(legend_text)
        legend_label = legend_match.group(1).upper() if legend_match else None
        image_match = _IMAGE_RE.search(text)
        image_ref = (image_match.group(1) or image_match.group(2)).strip() if image_match else None
        image_path = (path.parent / image_ref).resolve() if image_ref and not image_ref.startswith("http") else None
        page_match = _PAGE_RE.search(text)
        rows.append(
            {
                "file": path.name,
                "path": str(path),
                "header_label": header_label,
                "legend_label": legend_label,
                "legend_source": "render_text" if legend_label else None,
                "legend_confidence": 1.0 if legend_label else 0.0,
                "page": int(page_match.group(1)) if page_match else None,
                "image_ref": image_ref,
                "image_exists": bool(image_path and image_path.is_file()),
                "image_hash": _sha256_file(image_path) if image_path else None,
                "text_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
    return rows


def _page_number(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _position_view(row: dict[str, Any]) -> dict[str, Any]:
    assets = row.get("matched_assets") or []
    asset_pages = sorted(
        {
            page
            for asset in assets
            if isinstance(asset, dict)
            for page in [_page_number(asset.get("page"))]
            if page is not None
        }
    )
    legend_page = _page_number(row.get("legend_page"))
    object_page = _page_number(row.get("page"))
    reference_page = legend_page or object_page
    anchor_pages = [page for page in (legend_page, object_page) if page is not None]
    page_range = sorted(set(anchor_pages + asset_pages)) or None
    same_page = bool(
        reference_page is not None and asset_pages and all(page == reference_page for page in asset_pages)
    )
    cross_page = bool(
        reference_page is not None and asset_pages and any(page != reference_page for page in asset_pages)
    )
    if not asset_pages:
        relation = "no_asset"
        ordering = "no_asset"
    elif same_page:
        relation = "same_page"
        ordering = "same_page"
    elif legend_page is not None and max(asset_pages) < legend_page:
        relation = "asset_before_legend"
        ordering = "asset_before_legend"
    elif legend_page is not None and min(asset_pages) > legend_page:
        relation = "legend_before_asset"
        ordering = "legend_before_asset"
    else:
        relation = "cross_page"
        ordering = "unknown"
    return {
        "legend_page": legend_page,
        "object_page": object_page,
        "asset_pages": asset_pages,
        "page_range": page_range,
        "same_page": same_page,
        "cross_page": cross_page,
        "ordering": ordering,
        "relation": relation,
        "legend_block_id": row.get("legend_block_id"),
        "asset_bboxes": [
            {
                "block_id": asset.get("block_id"),
                "page": asset.get("page"),
                "bbox": asset.get("bbox"),
            }
            for asset in assets
            if isinstance(asset, dict)
        ],
    }

def _render_position_view(artifact: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "render_page": artifact.get("page"),
        "canonical": [
            {
                "canonical_object_id": candidate.get("canonical_object_id"),
                "legend_page": (candidate.get("position") or {}).get("legend_page"),
                "object_page": (candidate.get("position") or {}).get("object_page"),
                "asset_pages": (candidate.get("position") or {}).get("asset_pages", []),
                "page_range": (candidate.get("position") or {}).get("page_range"),
                "same_page": (candidate.get("position") or {}).get("same_page", False),
                "cross_page": (candidate.get("position") or {}).get("cross_page", False),
                "ordering": (candidate.get("position") or {}).get("ordering"),
                "relation": (candidate.get("position") or {}).get("relation"),
            }
            for candidate in candidates
        ],
    }


def _canonical_view(row: dict[str, Any], kind: str) -> dict[str, Any]:
    assets = row.get("matched_assets") or []
    return {
        "canonical_object_id": row.get("canonical_object_id"),
        "namespace": row.get("figure_namespace") or row.get("table_namespace") or "main",
        "normalized_label": row.get("normalized_label"),
        "caption": str(row.get("text") or row.get("caption") or "")[:500],
        "caption_page": row.get("page"),
        "caption_confidence": row.get("confidence") or row.get("role_confidence"),
        "asset_block_ids": row.get("asset_block_ids") or [a.get("block_id") for a in assets if isinstance(a, dict)],
        "asset_pages": [a.get("page") for a in assets if isinstance(a, dict) and a.get("page") is not None],
        "settlement_type": row.get("settlement_type"),
        "kind": kind,
        "position": _position_view(row),
    }



def _candidates(rows: list[dict[str, Any]], labels: set[str | None], kind: str) -> list[dict[str, Any]]:
    return [_canonical_view(row, kind) for row in rows if row.get("normalized_label") in labels]


_DIAGNOSIS_DOMAIN = {
    "render_label_mismatch": "render_layer",
    "render_header_missing": "render_layer",
    "render_image_materialization_missing": "render_layer",
    "render_artifact_empty": "render_layer",
    "dangling_render_asset": "render_layer",
    "render_artifact_missing": "render_layer",
    "canonical_identity_ambiguous": "inventory_layer",
    "inventory_identity_ambiguous": "inventory_layer",
    "upstream_asset_missing_or_reserved": "asset_layer",
}


def _issue(
    issue_type: str,
    severity: str,
    message: str,
    *,
    diagnosis: str | None = None,
    recommended_action: str = "inspect",
    **evidence: Any,
) -> dict[str, Any]:
    issue = {
        "type": issue_type,
        "severity": severity,
        "message": message,
        "domain": _DIAGNOSIS_DOMAIN.get(diagnosis or "", "unknown"),
        "recommended_action": recommended_action,
        "evidence": evidence,
    }
    if diagnosis:
        issue["diagnosis"] = diagnosis
    return issue


def _read_materialization_provenance(root: Path) -> dict[str, Any]:
    relative_path = "render/materialization.provenance.json"
    path = root / relative_path
    if not path.is_file():
        return {
            "path": relative_path,
            "state": "missing",
            "records_by_render_path": {},
        }
    try:
        payload = _read_json(path)
    except (OSError, TypeError, ValueError):
        return {
            "path": relative_path,
            "state": "unreadable",
            "records_by_render_path": {},
        }
    records = payload.get("objects") if isinstance(payload, dict) else None
    records = records if isinstance(records, list) else []
    return {
        "path": relative_path,
        "state": "available",
        "schema_version": payload.get("schema_version") if isinstance(payload, dict) else None,
        "summary": payload.get("summary") if isinstance(payload, dict) else {},
        "records_by_render_path": {
            str(record.get("render_path")): record
            for record in records
            if isinstance(record, dict) and record.get("render_path")
        },
    }


def _materialization_provenance_view(provenance: dict[str, Any]) -> dict[str, Any]:
    return {
        key: provenance[key]
        for key in ("path", "state", "schema_version", "summary")
        if key in provenance
    }


def _audit_kind(
    root: Path,
    kind: str,
    materialization_provenance: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    inventory = root / "structure" / f"{kind}_inventory.json"
    rows = _inventory_rows(inventory, kind)
    _enrich_inventory_positions(root, rows, kind)
    artifacts = _render_artifacts(root / "render" / ("figures" if kind == "figure" else "tables"), kind)

    issues: list[dict[str, Any]] = []
    identity_conflicts = _inventory_identity_conflicts(rows, kind)
    for conflict in identity_conflicts:
        issues.append(
            _issue(
                "inventory_duplicate_entry",
                "P1",
                "canonical inventory object has multiple rows for one object ID",
                diagnosis="inventory_identity_ambiguous",
                recommended_action="inspect_inventory",
                kind=kind,
                **conflict,
            )
        )
    for artifact in artifacts:
        labels = {artifact.get("header_label"), artifact.get("legend_label")} - {None}
        candidates = _candidates(rows, labels, kind)
        asset_candidates = [candidate for candidate in candidates if candidate.get("asset_block_ids")]
        artifact_evidence = {
            "file": artifact["file"],
            "page": artifact["page"],
            "header_label": artifact["header_label"],
            "legend_label": artifact["legend_label"],
            "image_ref": artifact["image_ref"],
            "image_exists": artifact["image_exists"],
            "canonical_candidates": candidates,
        }
        artifact_evidence["position"] = _render_position_view(artifact, candidates)
        if materialization_provenance:
            materialization = materialization_provenance.get("records_by_render_path", {}).get(
                f"render/{'figures' if kind == 'figure' else 'tables'}/{artifact['file']}"
            )
            if materialization:
                artifact_evidence["materialization"] = materialization
        if artifact["header_label"] is None:
            issues.append(
                _issue(
                    "render_artifact_integrity",
                    "P1",
                    "render artifact has no canonical header label",
                    diagnosis="render_header_missing",
                    recommended_action="inspect_render",
                )
            )
        if (
            artifact["legend_label"]
            and artifact["header_label"]
            and artifact["legend_label"] != artifact["header_label"]
        ):
            issues.append(
                _issue(
                    "render_caption_mismatch",
                    "P1",
                    "render header and legend labels disagree",
                    diagnosis="render_label_mismatch" if len(candidates) == 1 else "canonical_identity_ambiguous",
                    recommended_action="rerender" if len(candidates) == 1 else "inspect_inventory",
                    legend_source=artifact["legend_source"],
                    legend_confidence=artifact["legend_confidence"],
                    **artifact_evidence,
                )
            )
        if artifact["image_ref"] and not artifact["image_exists"]:
            issues.append(
                _issue(
                    "render_dangling_asset_reference",
                    "P0",
                    "render artifact references a missing image",
                    diagnosis="dangling_render_asset",
                    recommended_action="rerender",
                    **artifact_evidence,
                )
            )
        if not artifact["image_ref"] and kind == "figure":
            if asset_candidates:
                issue_type = "render_artifact_integrity"
                message = "canonical asset exists but render image materialization is missing"
                diagnosis = "render_image_materialization_missing"
                action = "rerender"
            elif artifact["legend_label"]:
                issue_type = "caption_without_asset"
                message = "caption/legend has no rendered image asset"
                diagnosis = "upstream_asset_missing_or_reserved"
                action = "inspect_asset_matching"
            else:
                issue_type = "render_artifact_integrity"
                message = "figure render artifact has no image or legend"
                diagnosis = "render_artifact_empty"
                action = "inspect_render"
            issues.append(
                _issue(
                    issue_type,
                    "P1",
                    message,
                    diagnosis=diagnosis,
                    recommended_action=action,
                    **artifact_evidence,
                )
            )

    canonical_labels = {row["normalized_label"] for row in rows if row.get("normalized_label")}
    rendered_labels = {a["header_label"] for a in artifacts if a.get("header_label")}
    for label in sorted(canonical_labels - rendered_labels):
        matching = [row for row in rows if row.get("normalized_label") == label]
        has_asset = any(row.get("matched_assets") or row.get("asset_block_ids") for row in matching)
        if has_asset:
            issues.append(
                _issue(
                    "missing_render_materialization",
                    "P1",
                    "canonical object has assets but no matching render header",
                    diagnosis="render_artifact_missing",
                    recommended_action="rerender",
                    kind=kind,
                    label=label,
                    canonical_candidates=[_canonical_view(row, kind) for row in matching],
                )
            )

    return rows, artifacts, issues


def _snapshot(root: Path) -> dict[str, str | None]:
    structure = root / "structure"
    return {
        "blocks_hash": _sha256_file(structure / "blocks.structured.jsonl"),
        "figure_inventory_hash": _sha256_file(structure / "figure_inventory.json"),
        "table_inventory_hash": _sha256_file(structure / "table_inventory.json"),
        "render_hash": _sha256_tree(
            root / "render",
            exclude_names={"render.consistency.json", "reconciliation.proposals.json"},
        ),
        "asset_index_hash": _sha256_tree(root / "assets"),
    }


def audit_paper(ocr_root: Path, paper_key: str, *, write_report: bool = True) -> dict[str, Any]:
    root = ocr_root / paper_key
    if not root.is_dir():
        return {
            "render_consistency_schema_version": SCHEMA_VERSION,
            "audit_algorithm_version": ALGORITHM_VERSION,
            "paper_key": paper_key,
            "state": "FAILED",
            "evidence_mode": "mixed",
            "issues": [_issue("audit_execution_failure", "P0", "OCR paper directory is missing", paper_key=paper_key)],
        }

    issues: list[dict[str, Any]] = []
    materialization_provenance = _read_materialization_provenance(root)
    try:
        figure_rows, figure_artifacts, figure_issues = _audit_kind(
            root,
            "figure",
            materialization_provenance,
        )
        table_rows, table_artifacts, table_issues = _audit_kind(
            root,
            "table",
            materialization_provenance,
        )
        issues.extend(figure_issues)
        issues.extend(table_issues)
        state = "CLEAN" if not issues else "DEGRADED"
        result: dict[str, Any] = {
            "render_consistency_schema_version": SCHEMA_VERSION,
            "audit_algorithm_version": ALGORITHM_VERSION,
            "paper_key": paper_key,
            "state": state,
            "evidence_mode": "exact" if not issues else "mixed",
            "input_snapshot": _snapshot(root),
            "canonical_objects": {
                "figures": [_canonical_view(row, "figure") for row in figure_rows],
                "tables": [_canonical_view(row, "table") for row in table_rows],
            },
            "render_artifacts": {"figures": figure_artifacts, "tables": table_artifacts},
            "materialization_provenance": _materialization_provenance_view(materialization_provenance),
            "summary": {
                "figure_inventory_objects": len(figure_rows),
                "table_inventory_objects": len(table_rows),
                "figure_render_artifacts": len(figure_artifacts),
                "table_render_artifacts": len(table_artifacts),
                "issues_found": len(issues),
                "issues_repaired": 0,
                "issues_remaining": len(issues),
            },
            "issues": issues,
            "audit_0": {"state": state},
            "audit_1": None,
        }
    except Exception as exc:  # noqa: BLE001 — audit must report execution failure
        result = {
            "render_consistency_schema_version": SCHEMA_VERSION,
            "audit_algorithm_version": ALGORITHM_VERSION,
            "paper_key": paper_key,
            "state": "FAILED",
            "evidence_mode": "mixed",
            "input_snapshot": _snapshot(root),
            "materialization_provenance": _materialization_provenance_view(materialization_provenance),
            "issues": [_issue("audit_execution_failure", "P0", str(exc), paper_key=paper_key)],
            "audit_0": {"state": "FAILED"},
            "audit_1": None,
        }

    if write_report:
        report_path = root / "render" / "render.consistency.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["report_path"] = str(report_path)
    return result


def discover_papers(ocr_root: Path) -> list[str]:
    if not ocr_root.is_dir():
        return []
    return sorted(path.name for path in ocr_root.iterdir() if path.is_dir() and not path.name.startswith("."))


def audit_papers(
    ocr_root: Path, paper_keys: Iterable[str] | None = None, *, write_report: bool = True
) -> dict[str, Any]:
    keys = list(paper_keys) if paper_keys else discover_papers(ocr_root)
    reports = [audit_paper(ocr_root, key, write_report=write_report) for key in keys]
    failed = sum(report.get("state") == "FAILED" for report in reports)
    return {
        "render_consistency_schema_version": SCHEMA_VERSION,
        "audit_algorithm_version": ALGORITHM_VERSION,
        "state": "FAILED"
        if failed
        else "CLEAN"
        if all(report.get("state") == "CLEAN" for report in reports)
        else "DEGRADED",
        "papers": reports,
        "summary": {
            "papers": len(reports),
            "clean": sum(report.get("state") == "CLEAN" for report in reports),
            "degraded": sum(report.get("state") == "DEGRADED" for report in reports),
            "failed": failed,
            "issues": sum(len(report.get("issues", [])) for report in reports),
        },
    }
