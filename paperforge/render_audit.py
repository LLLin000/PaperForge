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
ALGORITHM_VERSION = 1
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
        rows = list(data.get("matched_figures") or []) + list(data.get("unmatched_captions") or [])
    else:
        rows = (
            list(data.get("tables") or [])
            + list(data.get("held_tables") or [])
            + list(data.get("unmatched_captions") or [])
        )
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        row = dict(row)
        row["canonical_object_id"] = row.get("figure_id") or row.get("table_id")
        row["normalized_label"] = _label(row.get("figure_number") if kind == "figure" else row.get("table_number"))
        if row["normalized_label"] is None:
            row["normalized_label"] = _label(row.get("text") or row.get("caption") or row.get("raw_label"))
        result.append(row)
    return result


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
    }


def _candidates(rows: list[dict[str, Any]], labels: set[str | None], kind: str) -> list[dict[str, Any]]:
    return [_canonical_view(row, kind) for row in rows if row.get("normalized_label") in labels]


def _issue(issue_type: str, severity: str, message: str, **evidence: Any) -> dict[str, Any]:
    return {"type": issue_type, "severity": severity, "message": message, "evidence": evidence}


def _audit_kind(root: Path, kind: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    inventory = root / "structure" / f"{kind}_inventory.json"
    rows = _inventory_rows(inventory, kind)
    artifacts = _render_artifacts(root / "render" / ("figures" if kind == "figure" else "tables"), kind)
    issues: list[dict[str, Any]] = []
    for artifact in artifacts:
        labels = {artifact.get("header_label"), artifact.get("legend_label")} - {None}
        candidates = _candidates(rows, labels, kind)
        artifact_evidence = {
            "file": artifact["file"],
            "page": artifact["page"],
            "header_label": artifact["header_label"],
            "legend_label": artifact["legend_label"],
            "image_ref": artifact["image_ref"],
            "image_exists": artifact["image_exists"],
            "canonical_candidates": candidates,
        }
        if artifact["header_label"] is None:
            issues.append(
                _issue(
                    "render_artifact_integrity",
                    "P1",
                    "render artifact has no canonical header label",
                    **artifact_evidence,
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
                    legend_source=artifact["legend_source"],
                    legend_confidence=artifact["legend_confidence"],
                    diagnosis="render_label_mismatch" if len(candidates) == 1 else "canonical_identity_ambiguous",
                    **artifact_evidence,
                )
            )
        if artifact["image_ref"] and not artifact["image_exists"]:
            issues.append(
                _issue(
                    "render_dangling_asset_reference",
                    "P0",
                    "render artifact references a missing image",
                    **artifact_evidence,
                )
            )
        if not artifact["image_ref"] and kind == "figure":
            issue_type = "caption_without_asset" if artifact["legend_label"] else "render_artifact_integrity"
            message = (
                "caption/legend has no rendered image asset"
                if issue_type == "caption_without_asset"
                else "figure render artifact has no image or legend"
            )
            issues.append(_issue(issue_type, "P1", message, **artifact_evidence))

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
        "render_hash": _sha256_tree(root / "render", exclude_names={"render.consistency.json"}),
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
    try:
        figure_rows, figure_artifacts, figure_issues = _audit_kind(root, "figure")
        table_rows, table_artifacts, table_issues = _audit_kind(root, "table")
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
