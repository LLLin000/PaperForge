"""Read-only figure reconciliation proposals.

This module never creates canonical objects and never mutates OCR truth.  It
classifies existing canonical-to-render gaps, constrained caption/asset
candidates, and blocked reservation/ambiguity cases.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from paperforge.render_audit import _inventory_rows, _render_artifacts

_SCHEMA_VERSION = 1
_ALGORITHM_VERSION = 1
_FORMAL_LABEL_RE = re.compile(
    r"^\s*(?:fig(?:ure)?s?\.?|图)\s*([A-Z]?\d+)\b", re.IGNORECASE
)
_SOURCE_IMAGE_RE = re.compile(r"^page_(\d+)_figure_.*\.(?:jpg|jpeg|png)$", re.IGNORECASE)


def _label_sort(label: str) -> tuple[int, str]:
    try:
        return int(label), label
    except ValueError:
        return 10**9, label


def _read_blocks(root: Path) -> list[dict[str, Any]]:
    path = root / "structure" / "blocks.structured.jsonl"
    if not path.is_file():
        return []
    blocks: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            blocks.append(value)
    return blocks


def _formal_text_census(root: Path) -> dict[str, list[dict[str, Any]]]:
    evidence: dict[str, list[dict[str, Any]]] = {}
    for block in _read_blocks(root):
        text = str(block.get("text") or "").strip()
        match = _FORMAL_LABEL_RE.match(text)
        if match is None:
            continue
        label = match.group(1).upper()
        evidence.setdefault(label, []).append(
            {
                "type": "caption_text",
                "label": label,
                "page": block.get("page"),
                "block_id": block.get("block_id"),
                "role": block.get("role"),
                "raw_label": block.get("raw_label"),
                "text": text[:500],
            }
        )
    return evidence


def _formal_canonical(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    formal: dict[str, dict[str, Any]] = {}
    reservations: list[dict[str, Any]] = []
    for row in rows:
        object_id = str(row.get("figure_id") or "")
        settlement = str(row.get("settlement_type") or "").lower()
        reserved = "reserved" in object_id.lower() or "reservation" in settlement
        if reserved:
            reservations.append(row)
            continue
        number = row.get("figure_number")
        if number is None:
            continue
        label = str(number).upper()
        formal[label] = row
    return formal, reservations


def _formal_render_artifacts(artifacts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    formal: dict[str, dict[str, Any]] = {}
    for artifact in artifacts:
        name = str(artifact.get("file") or "")
        if "reserved" in name.lower():
            continue
        label = artifact.get("header_label")
        if label:
            formal[str(label).upper()] = artifact
    return formal


def _source_images(root: Path) -> list[dict[str, Any]]:
    directory = root / "images" / "blocks"
    if not directory.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.iterdir()):
        match = _SOURCE_IMAGE_RE.match(path.name)
        if match is None or not path.is_file():
            continue
        rows.append(
            {
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "page": int(match.group(1)),
                "bytes": path.stat().st_size,
            }
        )
    return rows


def _pdf_media(
    ocr_root: Path,
    paper_key: str,
    pages: set[int],
    *,
    enabled: bool,
) -> dict[str, Any]:
    if not enabled:
        return {"state": "not_checked", "pages": []}
    if not pages:
        return {"state": "no_candidate_pages", "pages": []}
    try:
        from paperforge.lineage import _canonical_pdf_map

        vault = ocr_root.parents[2]
        pdf_path = _canonical_pdf_map(vault, [paper_key]).get(paper_key)
        if pdf_path is None:
            return {"state": "pdf_unresolved", "pages": []}
        import pymupdf

        doc = pymupdf.open(str(pdf_path))
        records: list[dict[str, Any]] = []
        try:
            for page_number in sorted(pages):
                if page_number < 1 or page_number > len(doc):
                    continue
                page = doc[page_number - 1]
                page_area = float(page.rect.width * page.rect.height)
                for index, info in enumerate(page.get_image_info(xrefs=True)):
                    bbox = info.get("bbox") or (0, 0, 0, 0)
                    area = max(0.0, float(bbox[2] - bbox[0]) * float(bbox[3] - bbox[1]))
                    records.append(
                        {
                            "page": page_number,
                            "index": index,
                            "xref": info.get("xref"),
                            "bbox": list(bbox),
                            "width": info.get("width"),
                            "height": info.get("height"),
                            "area_fraction": round(area / page_area, 5) if page_area else 0.0,
                        }
                    )
        finally:
            doc.close()
        return {"state": "available", "pages": records}
    except Exception as exc:  # noqa: BLE001 — evidence is optional and fail-soft
        return {"state": "unavailable", "reason": type(exc).__name__, "pages": []}


def _candidate_proposal(
    label: str,
    caption_evidence: list[dict[str, Any]],
    source_images: list[dict[str, Any]],
    pdf_media: dict[str, Any],
    occupied_pages: set[int],
) -> dict[str, Any]:
    caption_pages = {
        int(item["page"])
        for item in caption_evidence
        if str(item.get("page", "")).isdigit()
    }
    candidate_pages = set().union(*(range(page - 1, page + 2) for page in caption_pages))
    page_candidates: list[dict[str, Any]] = []
    for page in sorted(page for page in candidate_pages if page > 0):
        if page in occupied_pages:
            continue
        images = [item for item in source_images if item["page"] == page and item["bytes"] > 4096]
        media = [item for item in pdf_media.get("pages", []) if item.get("page") == page]
        if images:
            page_candidates.append(
                {
                    "page": page,
                    "source_images": images,
                    "pdf_media": media,
                    "page_distance": min(abs(page - caption_page) for caption_page in caption_pages)
                    if caption_pages
                    else None,
                }
            )
    decision = "proposal_only"
    confidence = "constrained"
    if len(page_candidates) == 1 and page_candidates[0].get("pdf_media"):
        confidence = "high"
    elif len(page_candidates) != 1:
        decision = "blocked"
    evidence_chain: list[dict[str, Any]] = [
        {"type": "caption", "items": caption_evidence},
        {"type": "source_image_candidates", "items": page_candidates},
    ]
    if pdf_media.get("state") == "available":
        evidence_pages = {candidate.get("page") for candidate in page_candidates}
        evidence_chain.append(
            {
                "type": "pdf_media",
                "items": [
                    item
                    for item in pdf_media.get("pages", [])
                    if item.get("page") in evidence_pages
                ],
            }
        )
    return {
        "proposal_id": f"inventory_proposal:figure:{label}",
        "kind": "figure",
        "label": label,
        "decision": decision,
        "repair_scope": "inventory_proposal" if decision == "proposal_only" else "review_only",
        "evidence_mode": "constrained" if decision == "proposal_only" else "ambiguous",
        "confidence": confidence,
        "candidate_pages": page_candidates,
        "evidence_chain": evidence_chain,
        "action": "inspect_inventory" if decision == "proposal_only" else "review_required",
    }


def build_reconciliation_report(
    ocr_root: Path,
    paper_key: str,
    audit_report: dict[str, Any] | None = None,
    *,
    include_pdf_media: bool = False,
) -> dict[str, Any]:
    root = ocr_root / paper_key
    if audit_report is None:
        audit_path = root / "render" / "render.consistency.json"
        try:
            audit_report = json.loads(audit_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            audit_report = {}
    figure_rows = _inventory_rows(root / "structure" / "figure_inventory.json", "figure")
    artifacts = _render_artifacts(root / "render" / "figures", "figure")
    text_evidence = _formal_text_census(root)
    canonical, reservations = _formal_canonical(figure_rows)
    rendered = _formal_render_artifacts(artifacts)
    source_images = _source_images(root)

    missing_labels = sorted(set(text_evidence) - set(canonical), key=_label_sort)
    candidate_pages = {
        page
        for label in missing_labels
        for item in text_evidence.get(label, [])
        if str(item.get("page", "")).isdigit()
        for page in range(int(item["page"]) - 1, int(item["page"]) + 2)
        if page > 0
    }
    pdf_media = _pdf_media(ocr_root, paper_key, candidate_pages, enabled=include_pdf_media)

    exact_repairs: list[dict[str, Any]] = []
    audit_issues = (audit_report or {}).get("issues", [])
    issue_by_label: dict[str, list[dict[str, Any]]] = {}
    for issue in audit_issues:
        evidence = issue.get("evidence") or {}
        for candidate in evidence.get("canonical_candidates") or []:
            label = candidate.get("normalized_label")
            if label:
                issue_by_label.setdefault(str(label).upper(), []).append(issue)
    for label, row in canonical.items():
        artifact = rendered.get(label)
        image_missing = artifact is None or not artifact.get("image_ref") or not artifact.get("image_exists")
        assets = row.get("matched_assets") or []
        if not image_missing or not assets:
            continue
        object_id = str(row.get("figure_id"))
        exact_repairs.append(
            {
                "repair_id": f"render_repair:{object_id}",
                "kind": "figure",
                "namespace": row.get("figure_namespace") or "main",
                "canonical_object_id": object_id,
                "decision": "exact_repair",
                "repair_scope": "render_only",
                "action": "materialize_render",
                "evidence_mode": "exact",
                "source": {
                    "asset_block_ids": [str(asset.get("block_id")) for asset in assets],
                    "asset_pages": sorted({asset.get("page") for asset in assets if asset.get("page") is not None}),
                    "settlement_type": row.get("settlement_type"),
                    "confidence": row.get("confidence"),
                },
                "render": {
                    "artifact_path": f"render/figures/{object_id}.md",
                    "observed": "artifact_missing" if artifact is None else "image_missing",
                },
                "origin": {
                    "issue_types": sorted(
                        {
                            str(issue.get("type") or "")
                            for issue in issue_by_label.get(label, [])
                            if issue.get("type")
                        }
                    ),
                    "report_path": "render/render.consistency.json",
                },
            }
        )

    proposals: list[dict[str, Any]] = []
    occupied_pages = {
        int(asset.get("page"))
        for row in canonical.values()
        for asset in (row.get("matched_assets") or [])
        if str(asset.get("page", "")).isdigit()
    }
    blocked: list[dict[str, Any]] = []
    for label in missing_labels:
        proposal = _candidate_proposal(
            label,
            text_evidence[label],
            source_images,
            pdf_media,
            occupied_pages,
        )
        if proposal["decision"] == "proposal_only":
            proposals.append(proposal)
        else:
            blocked.append(
                {
                    "block_id": f"blocked:missing_canonical:{label}",
                    "kind": "figure",
                    "decision": "blocked",
                    "repair_scope": "review_only",
                    "reason": "candidate_match_ambiguous",
                    "label": label,
                    "evidence_chain": proposal["evidence_chain"],
                    "action": "review_required",
                }
            )
    for row in reservations:
        object_id = str(row.get("figure_id") or "")
        blocked.append(
            {
                "block_id": f"blocked:reservation:{object_id}",
                "kind": "figure",
                "decision": "blocked",
                "repair_scope": "review_only",
                "reason": "reservation_artifact_conflict",
                "canonical_object_id": object_id,
                "label": row.get("figure_number"),
                "settlement_type": row.get("settlement_type"),
                "confidence": row.get("confidence"),
                "action": "inspect_inventory",
            }
        )

    audit_snapshot = (audit_report or {}).get("input_snapshot")
    if audit_snapshot is None:
        audit_snapshot = {}
    report = {
        "schema_version": _SCHEMA_VERSION,
        "algorithm_version": _ALGORITHM_VERSION,
        "paper_key": paper_key,
        "input_snapshot": audit_snapshot,
        "formal_figure_assessment": {
            "supported_formal_figure_labels": sorted(text_evidence, key=_label_sort),
            "canonical_formal_figure_labels": sorted(canonical, key=_label_sort),
            "rendered_formal_figure_labels": sorted(rendered, key=_label_sort),
            "missing_canonical_labels": missing_labels,
            "missing_render_labels": sorted(set(canonical) - set(rendered), key=_label_sort),
            "caption_evidence": text_evidence,
        },
        "pdf_media_validation": pdf_media,
        "summary": {
            "supported_formal_figures": len(text_evidence),
            "canonical_formal_figures": len(canonical),
            "rendered_formal_figures": len(rendered),
            "exact_repairs": len(exact_repairs),
            "proposals": len(proposals),
            "blocked": len(blocked),
        },
        "exact_repairs": exact_repairs,
        "proposals": proposals,
        "blocked": blocked,
    }
    return report


def write_reconciliation_report(
    ocr_root: Path,
    paper_key: str,
    audit_report: dict[str, Any] | None = None,
    *,
    include_pdf_media: bool = False,
) -> dict[str, Any]:
    report = build_reconciliation_report(
        ocr_root,
        paper_key,
        audit_report,
        include_pdf_media=include_pdf_media,
    )
    path = ocr_root / paper_key / "render" / "reconciliation.proposals.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report["report_path"] = str(path)
    return report
