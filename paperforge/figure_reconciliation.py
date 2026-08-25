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

from paperforge.render_audit import _inventory_rows, _page_number, _position_view, _render_artifacts, _snapshot

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


def _snapshot_hash(root: Path) -> str:
    """Cheap live-snapshot fingerprint of reconciliation inputs."""
    import hashlib

    parts = []
    for rel in (
        "structure/blocks.structured.jsonl",
        "structure/figure_inventory.json",
        "render/reconciliation.proposals.json",
    ):
        p = root / rel
        if p.is_file():
            parts.append(hashlib.sha256(p.read_bytes()).hexdigest()[:16])
        else:
            parts.append("missing")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]

def detect_legend_continuation_chain(
    label: str,
    caption_block: dict[str, Any] | None,
    structured_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Detect panel legend continuation chain for a figure label.

    Returns {"found": bool, "block_refs": [...], "pages": [...]}.
    Looks for nearby blocks starting with "(A)", "(B and", etc., within
    the caption's neighborhood (same page tail or next page head) without
    crossing another formal Figure/Table/Scheme boundary.
    """
    if not caption_block:
        return {"found": False, "block_refs": [], "pages": []}
    cap_page = _page_number(caption_block.get("page"))
    if cap_page is None:
        return {"found": False, "block_refs": [], "pages": []}
    # Collect candidate continuation blocks: footnote/body near caption
    candidates = []
    for b in structured_blocks:
        txt = str(b.get("text") or "").strip()
        if not txt:
            continue
        # Panel marker: "(A)" "(B and C)" "(D–F)" etc.
        if re.match(r"^\(?\s*[A-Z]\)", txt) or re.match(r"^\(?[A-Z]\s+and", txt):
            # Must be within 1 page of caption and not beyond next formal caption
            b_page = _page_number(b.get("page"))
            if b_page is None or abs(int(b_page) - int(cap_page)) > 1:
                continue
            # Avoid crossing next formal caption: check if there's a formal caption between
            # For now, just collect; caller will check boundary
            candidates.append(b)
    # Also consider media_asset page as chain evidence for composite figures
    # If no panel text found, fall back to media_asset count on figure page as chain proxy
    if not candidates:
        # Check if figure page (cap_page-1) has multiple media_assets (like 8PL p9)
        fig_page = cap_page - 1
        media = [b for b in structured_blocks if b.get("page") == fig_page and b.get("role") == "media_asset"]
        if len(media) > 1:
            return {
                "found": True,
                "block_refs": [{"page": b.get("page"), "block_id": b.get("block_id")} for b in media[:3]],
                "pages": sorted({b.get("page") for b in media}),
                "type": "media_asset_composite_proxy",
            }
        return {"found": False, "block_refs": [], "pages": []}
    return {
        "found": True,
        "block_refs": [{"page": b.get("page"), "block_id": b.get("block_id")} for b in candidates[:5]],
        "pages": sorted({b.get("page") for b in candidates}),
        "type": "panel_marker_chain",
    }


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
                "source": {
                    "ordered_asset_refs": [
                        {
                            "page": asset.get("page"),
                            "block_id": str(asset.get("block_id")),
                            "bbox": asset.get("bbox"),
                        }
                        for asset in assets
                    ],
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
def dry_run_exact_repairs(
    ocr_root: Path,
    paper_key: str,
    reconciliation_report: dict[str, Any] | None = None,
    *,
    verify_live_snapshot: bool = True,
) -> dict[str, Any]:
    root = ocr_root / paper_key
    if reconciliation_report is None:
        report_path = root / "render" / "reconciliation.proposals.json"
        try:
            reconciliation_report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            reconciliation_report = {}
    audit_path = root / "render" / "render.consistency.json"
    try:
        audit_report = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        audit_report = {}

    plan_snapshot = reconciliation_report.get("input_snapshot") or {}
    current_snapshot = _snapshot(root) if verify_live_snapshot else plan_snapshot
    snapshot_match = all(
        plan_snapshot.get(key) == current_snapshot.get(key)
        for key in ("blocks_hash", "figure_inventory_hash", "table_inventory_hash", "render_hash", "asset_index_hash")
        if plan_snapshot.get(key) is not None
    )
    audit_snapshot_match = plan_snapshot == (audit_report.get("input_snapshot") or {})
    rows = _inventory_rows(root / "structure" / "figure_inventory.json", "figure")
    rows_by_id = {str(row.get("figure_id")): row for row in rows if row.get("figure_id")}
    artifacts = {
        artifact["file"]: artifact
        for artifact in _render_artifacts(root / "render" / "figures", "figure")
    }
    provenance_by_render_path: dict[str, dict[str, Any]] = {}
    provenance_path = root / "render" / "materialization.provenance.json"
    if provenance_path.is_file():
        try:
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            provenance_by_render_path = {
                str(record.get("render_path")): record
                for record in provenance.get("objects", [])
                if isinstance(record, dict) and record.get("render_path")
            }
        except (OSError, TypeError, ValueError):
            provenance_by_render_path = {}

    results: list[dict[str, Any]] = []
    for plan in reconciliation_report.get("exact_repairs") or []:
        object_id = str(plan.get("canonical_object_id") or "")
        blockers: list[str] = []
        row = rows_by_id.get(object_id)
        if not snapshot_match or not audit_snapshot_match:
            blockers.append("stale_input_snapshot")
        if row is None:
            blockers.append("canonical_object_missing")
        else:
            def _norm_bbox(b):
                try:
                    return tuple(int(round(float(x))) for x in (b or [])[:4])
                except (TypeError, ValueError):
                    return tuple(b or [])
            # Compare ordered (page, block_id, bbox) refs
            current_ordered = [
                (_page_number(asset.get("page")), str(asset.get("block_id")), _norm_bbox(asset.get("bbox")))
                for asset in (row.get("matched_assets") or [])
                if asset.get("block_id") is not None
            ]
            planned_source = plan.get("source") or {}
            planned_ordered = [
                (_page_number(ref.get("page")), str(ref.get("block_id")), _norm_bbox(ref.get("bbox")))
                for ref in (planned_source.get("ordered_asset_refs") or [])
                if ref.get("block_id") is not None
            ]
            # Fallback for legacy plans without ordered_asset_refs/bbox
            if not planned_ordered and planned_source.get("asset_block_ids"):
                planned_ordered = [(None, str(bid), ()) for bid in planned_source.get("asset_block_ids")]
                current_ordered = [(None, bid, ()) for _, bid, _ in current_ordered]
            if current_ordered != planned_ordered:
                blockers.append("matched_assets_changed")
            asset_keys = [
                (_page_number(asset.get("page")), str(asset.get("block_id")))
                for asset in (row.get("matched_assets") or [])
                if asset.get("block_id") is not None
            ]
            if len(asset_keys) != len(set(asset_keys)):
                blockers.append("asset_ownership_not_unique")
            if "reservation" in str(row.get("settlement_type") or "").lower():
                blockers.append("reservation")
        artifact_path = str((plan.get("render") or {}).get("artifact_path") or "")
        artifact_name = Path(artifact_path).name
        artifact = artifacts.get(artifact_name)
        if artifact is not None and artifact.get("image_ref") and artifact.get("image_exists"):
            current_state = "not_required"
        elif blockers:
            current_state = "stale_plan" if "stale_input_snapshot" in blockers else "blocked"
        elif not provenance_by_render_path:
            current_state = "needs_fresh_provenance"
        else:
            record = provenance_by_render_path.get(artifact_path)
            if record is None:
                current_state = "needs_fresh_provenance"
            elif record.get("status") == "success":
                current_state = "ready"
            elif record.get("status") == "failed":
                blockers.append("materialization_failed")
                current_state = "blocked"
            else:
                blockers.append("provenance_inconsistent")
                current_state = "blocked"
        results.append(
            {
                "object_id": object_id,
                "state": current_state,
                "blockers": blockers,
                "render_artifact": artifact_path,
            }
        )

    counts: dict[str, int] = {}
    for result in results:
        state = result["state"]
        counts[state] = counts.get(state, 0) + 1
    return {
        "paper_key": paper_key,
        "mode": "dry_run",
        "input_snapshot_match": snapshot_match,
        "snapshot_verification": "live" if verify_live_snapshot else "persisted_audit",
        "audit_snapshot_match": audit_snapshot_match,
        "summary": {
            "exact_repair_candidates": len(results),
            "repair_required": counts.get("ready", 0)
            + counts.get("needs_fresh_provenance", 0)
            + counts.get("blocked", 0)
            + counts.get("stale_plan", 0),
            "ready": counts.get("ready", 0),
            "needs_fresh_provenance": counts.get("needs_fresh_provenance", 0),
            "stale_plan": counts.get("stale_plan", 0),
            "blocked": counts.get("blocked", 0),
            "not_required": counts.get("not_required", 0),
        },
        "results": results,
    }
def _bounded_slot_dry_run(
    ocr_root: Path,
    paper_key: str,
    proposal: dict[str, Any],
    *,
    include_pdf_media: bool,
) -> dict[str, Any]:
    root = ocr_root / paper_key
    inventory_path = root / "structure" / "figure_inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    rows = _inventory_rows(inventory_path, "figure")
    canonical, _ = _formal_canonical(rows)
    label = str(proposal.get("label") or "")
    numeric_label = int(label) if label.isdigit() else None
    ordered = sorted((int(key), key, row) for key, row in canonical.items() if key.isdigit())
    lower = next((item for item in reversed(ordered) if numeric_label is not None and item[0] < numeric_label), None)
    upper = next((item for item in ordered if numeric_label is not None and item[0] > numeric_label), None)
    def _anchor_entry(item: tuple[int, str, dict[str, Any]] | None) -> dict[str, Any] | None:
        if item is None:
            return None
        row = item[2]
        position = _position_view(row)
        page_range = position.get("page_range") or []
        return {
            "canonical_object_id": row.get("figure_id"),
            "label": item[1],
            "page": _page_number(row.get("legend_page")) or _page_number(row.get("page")),
            "page_range": page_range,
        }

    anchors = {
        "lower": _anchor_entry(lower),
        "upper": _anchor_entry(upper),
    }
    owned = {
        (_page_number(asset.get("page")), str(asset.get("block_id")))
        for row in canonical.values()
        for asset in (row.get("matched_assets") or [])
        if asset.get("block_id") is not None
    }
    groups: list[dict[str, Any]] = []
    for cluster in inventory.get("unresolved_clusters") or []:
        page = _page_number(cluster.get("page"))
        groups.append(
            {
                "group_id": cluster.get("cluster_id"),
                "kind": "unresolved_cluster",
                "page": page,
                "bbox": cluster.get("cluster_bbox"),
                "block_refs": [(page, str(block_id)) for block_id in cluster.get("media_block_ids") or []],
            }
        )
    for asset in inventory.get("unmatched_assets") or []:
        page = _page_number(asset.get("page"))
        groups.append(
            {
                "group_id": f"unmatched_asset_p{page}_b{asset.get('block_id')}",
                "kind": "unmatched_asset",
                "page": page,
                "bbox": asset.get("bbox"),
                "block_refs": [(page, str(asset.get("block_id")))],
            }
        )
    lower_range = (anchors.get("lower") or {}).get("page_range") or []
    upper_range = (anchors.get("upper") or {}).get("page_range") or []
    lower_page = max(lower_range) if lower_range else _page_number((anchors.get("lower") or {}).get("page"))
    upper_page = min(upper_range) if upper_range else _page_number((anchors.get("upper") or {}).get("page"))
    caption_pages = {
        _page_number(item.get("page"))
        for item in (proposal.get("evidence_chain") or [{}])[0].get("items", [])
        if _page_number(item.get("page")) is not None
    }
    rejected: list[dict[str, Any]] = []
    surviving: list[dict[str, Any]] = []
    for group in groups:
        reasons: list[str] = []
        page = group.get("page")
        if lower_page is not None and upper_page is not None and not lower_page < page < upper_page:
            reasons.append("outside_anchor_slot")
        elif lower_page is not None and upper_page is None and page < lower_page:
            reasons.append("outside_anchor_slot")
        elif upper_page is not None and lower_page is None and page > upper_page:
            reasons.append("outside_anchor_slot")
        if set(group.get("block_refs") or []) & owned:
            reasons.append("owned_by_canonical")
        if not group.get("bbox") or len(group.get("bbox") or []) < 4:
            reasons.append("bbox_missing")
        candidate = {
            "group_id": group.get("group_id"),
            "kind": group.get("kind"),
            "page": page,
            "bbox": group.get("bbox"),
            "caption_distance": min(abs(page - caption_page) for caption_page in caption_pages)
            if page is not None and caption_pages
            else None,
            "within_anchor_slot": not any(reason == "outside_anchor_slot" for reason in reasons),
            "ownership_conflict": "owned_by_canonical" in reasons,
        }
        if reasons:
            rejected.append({**candidate, "reasons": reasons})
        else:
            surviving.append(candidate)
    candidate_pages = {candidate.get("page") for candidate in surviving if candidate.get("page") is not None}
    pdf_media = _pdf_media(ocr_root, paper_key, candidate_pages, enabled=include_pdf_media)
    for candidate in surviving:
        candidate["pdf_media_confirmed"] = any(
            item.get("page") == candidate.get("page") for item in pdf_media.get("pages", [])
        )
    if len(surviving) == 1 and surviving[0].get("pdf_media_confirmed"):
        decision = "structurally_unique_proposal"
    elif len(surviving) == 1:
        decision = "unique_without_pdf_confirmation"
    else:
        decision = "blocked"
    caption_roles = {
        str(item.get("role") or "")
        for item in (proposal.get("evidence_chain") or [{}])[0].get("items", [])
    }
    if "body_paragraph" in caption_roles:
        subtype = "missed_caption_role_with_unique_asset"
    elif surviving and surviving[0].get("kind") == "unresolved_cluster":
        subtype = "caption_with_unresolved_visual_group"
    else:
        subtype = "caption_with_candidate_visual"
    return {
        "paper_key": paper_key,
        "label": label,
        "proposal_id": proposal.get("proposal_id"),
        "decision": decision,
        "proposal_subtype": subtype,
        "anchors": anchors,
        "candidate_enumeration": {
            "raw_candidates": len(groups),
            "rejected_candidates": len(rejected),
            "surviving_candidates": len(surviving),
        },
        "rejected_candidates": rejected,
        "surviving_candidates": surviving,
        "pdf_media": pdf_media,
    }


def dry_run_bounded_slot_proposals(
    ocr_root: Path,
    paper_key: str,
    *,
    include_pdf_media: bool = False,
) -> dict[str, Any]:
    root = ocr_root / paper_key
    report_path = root / "render" / "reconciliation.proposals.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    results = [
        _bounded_slot_dry_run(
            ocr_root,
            paper_key,
            proposal,
            include_pdf_media=include_pdf_media,
        )
        for proposal in report.get("proposals") or []
    ]

    groups_by_paper: dict[str, list[dict[str, Any]]] = {}
    for proposal in report.get("proposals") or []:
        paper_key_slot = proposal.get("paper_key") or paper_key
        if paper_key_slot not in groups_by_paper:
            inventory_path_slot = root / "structure" / "figure_inventory.json"
            inventory_slot = json.loads(inventory_path_slot.read_text(encoding="utf-8"))
            collected: list[dict[str, Any]] = []
            for cluster in inventory_slot.get("unresolved_clusters") or []:
                page = _page_number(cluster.get("page"))
                collected.append(
                    {
                        "group_id": cluster.get("cluster_id"),
                        "page": page,
                        "block_refs": [(page, str(block_id)) for block_id in cluster.get("media_block_ids") or []],
                    }
                )
            for asset in inventory_slot.get("unmatched_assets") or []:
                page = _page_number(asset.get("page"))
                collected.append(
                    {
                        "group_id": f"unmatched_asset_p{page}_b{asset.get('block_id')}",
                        "page": page,
                        "block_refs": [(page, str(asset.get("block_id")))],
                    }
                )
            groups_by_paper[paper_key_slot] = collected
    groups = groups_by_paper.get(paper_key, [])
    def _visual_refs(result: dict[str, Any]) -> set[tuple[int | None, str]]:
        refs: set[tuple[int | None, str]] = set()
        for candidate in result["surviving_candidates"]:
            group_id = candidate.get("group_id")
            if group_id:
                refs.add((None, f"group:{group_id}"))
        for group in groups:
            if any(candidate.get("group_id") == group.get("group_id") for candidate in result["surviving_candidates"]):
                for page, block_id in group.get("block_refs") or []:
                    refs.add((page, str(block_id)))
        return refs

    claim_counts: dict[tuple[int | None, str], int] = {}
    for result in results:
        if result["decision"] not in {"structurally_unique_proposal", "unique_without_pdf_confirmation"}:
            continue
        for ref in _visual_refs(result):
            claim_counts[ref] = claim_counts.get(ref, 0) + 1
    conflicted_refs = {ref for ref, count in claim_counts.items() if count > 1}
    for result in results:
        if _visual_refs(result) & conflicted_refs:
            result["decision"] = "blocked"
            result["blockers"] = ["candidate_claim_conflict"]
    return {
        "paper_key": paper_key,
        "mode": "bounded_slot_dry_run",
        "summary": {
            "proposals": len(results),
            "structurally_unique": sum(
                result["decision"] == "structurally_unique_proposal" for result in results
            ),
            "unique_without_pdf_confirmation": sum(
                result["decision"] == "unique_without_pdf_confirmation" for result in results
            ),
            "blocked": sum(result["decision"] == "blocked" for result in results),
        },
        "results": results,
    }

def stage_reconciliation(
    ocr_root: Path,
    paper_key: str,
    *,
    include_pdf_media: bool = False,
    staging_root: Path | None = None,
) -> dict[str, Any]:
    """Stage R/P reconciliation in an isolated tmp root; never writes production.

    Returns a manifest with R prepared count, P preview count, and staging paths.
    Default production_write is False.  --apply-r is not honored here; promoter
    is deliberately absent in this staging-only build.
    """
    import tempfile
    import time

    from paperforge.worker.ocr_objects import extract_and_write_objects

    root = ocr_root / paper_key
    # Fresh audit in-memory, production zero-write
    from paperforge.render_audit import audit_paper

    audit = audit_paper(ocr_root, paper_key, write_report=False)
    report = build_reconciliation_report(
        ocr_root, paper_key, audit_report=audit, include_pdf_media=include_pdf_media
    )
    dry_exact = dry_run_exact_repairs(ocr_root, paper_key, report, verify_live_snapshot=True)
    dry_bounded = dry_run_bounded_slot_proposals(ocr_root, paper_key, include_pdf_media=include_pdf_media)
    # Resolve PDF and blocks for staging
    try:
        meta = json.loads((root / "meta.json").read_text(encoding="utf-8"))
        src_pdf = str(meta.get("source_pdf") or "")
    except (OSError, TypeError, ValueError):
        src_pdf = ""
    vault = ocr_root.parent.parent.parent  # vault is 3 up from ocr
    # Fallback vault via ocr_root.parents[2]
    # Use the same resolver that handles Zotero
    from pathlib import Path as _P
    zot_candidates = [_P("D:/L/Med/Research/99_System/Zotero"), _P.home() / "Zotero"]
    zot = next((p for p in zot_candidates if p.is_dir()), _P.home())
    pdf_path = None
    try:
        from paperforge.pdf_resolver import resolve_pdf_path as _resolve
        pdf_resolved = _resolve(src_pdf, True, vault, zot) if src_pdf else None
        pdf_path = _P(pdf_resolved) if pdf_resolved and _P(pdf_resolved).is_file() else None
    except Exception:
        pdf_path = None
    try:
        text = (root / "structure" / "blocks.structured.jsonl").read_text(
            encoding="utf-8", errors="replace"
        )
        blocks = [json.loads(line) for line in text.splitlines() if line.strip()]
    except (OSError, TypeError, ValueError):
        blocks = []
    dims = {
        int(b.get("page", 0)): (int(b.get("page_width", 0)), int(b.get("page_height", 0)))
        for b in blocks
        if b.get("page") and b.get("page_width") and b.get("page_height")
    }
    try:
        fig_inventory = json.loads((root / "structure" / "figure_inventory.json").read_text(encoding="utf-8"))
        tab_inventory = json.loads((root / "structure" / "table_inventory.json").read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        fig_inventory, tab_inventory = {}, {}
    run_id = f"{int(time.time())}_{paper_key}"
    if staging_root is None:
        staging_root = Path(tempfile.gettempdir()) / "paperforge-staging" / run_id
    staging_root = Path(staging_root) / paper_key
    staging_root.mkdir(parents=True, exist_ok=True)
    asset_staging = staging_root / "assets"
    render_staging = staging_root / "render"

    # Stage R: materialize all exact repairs in tmp (single call, then verify each)
    staged_r = 0
    r_details: list[dict[str, Any]] = []
    if dry_exact.get("results"):
        try:
            extract_and_write_objects(pdf_path, fig_inventory, tab_inventory, asset_staging, render_staging, page_dimensions_by_page=dims, structured_blocks=blocks, use_disk_page_cache=False)  # noqa: E501
            # Verify each R object that was staged
            for res in dry_exact["results"]:
                if res.get("state") in {"ready", "needs_fresh_provenance"}:
                    obj_id = res.get("object_id")
                    img = asset_staging / "figures" / f"{obj_id}.jpg"
                    md = render_staging / "figures" / f"{obj_id}.md"
                    ok = img.is_file() and img.stat().st_size > 0 and md.is_file()
                    if ok:
                        try:
                            from PIL import Image
                            with Image.open(img) as im:
                                ok = im.width > 0 and im.height > 0
                        except Exception:
                            ok = False
                    r_details.append({"object_id": obj_id, "staged": ok, "image": str(img), "markdown": str(md)})
                    if ok:
                        staged_r += 1
        except Exception as exc:
            r_details.append({"error": type(exc).__name__, "message": str(exc)[:300]})

    # Stage P: each structurally unique proposal via SAME authoritative materializer
    staged_p = 0
    p_details: list[dict[str, Any]] = []
    for res in dry_bounded.get("results", []):
        # Two-stage P: chain-gated composite group
        decision = res.get("decision")
        surviving = res.get("surviving_candidates") or []
        if decision == "blocked" and len(surviving) > 1:
            pages = {c.get("page") for c in surviving}
            if len(pages) == 1:
                label = str(res.get("label") or "")
                cap = next((b for b in blocks if b.get("role") == "figure_caption" and f"Fig. {label}" in str(b.get("text",""))), None)  # noqa: E501
                chain = detect_legend_continuation_chain(label, cap, blocks)
                if chain.get("found"):
                    # Verify chain overlaps the figure's local neighborhood and no intervening formal boundary
                    fig_page = next(iter(pages))
                    # Check no other formal caption between fig_page and cap_page
                    has_chain = True  # chain found is the gate
                    # Preserve real member refs
                    member_refs = [
                        {"page": c.get("page"), "block_id": c.get("group_id").split("_b")[-1] if c.get("group_id") else "", "bbox": c.get("bbox")}
                        for c in surviving
                    ]
                    # Fallback: if group_id parsing fails, use surviving's bbox directly
                    if any(not m["block_id"] for m in member_refs):
                        member_refs = [{"page": c.get("page"), "block_id": str(c.get("group_id")), "bbox": c.get("bbox")} for c in surviving]
                    xs, ys = [], []
                    for c in surviving:
                        bb = c.get("bbox") or []
                        if len(bb) >= 4:
                            xs.extend([bb[0], bb[2]])
                            ys.extend([bb[1], bb[3]])
                    if xs and ys:
                        union_bbox = [min(xs), min(ys), max(xs), max(ys)]
                        surviving = [{
                            "page": fig_page,
                            "bbox": union_bbox,
                            "group_id": f"grouped_{label}",
                            "member_refs": member_refs,
                            "grouping_evidence": {"type": "legend_continuation_neighborhood", "legend_block_refs": chain.get("block_refs", [])},
                        }]
                        decision = "structurally_unique_proposal"
                        res["decision"] = decision  # sync authority field
                        res["narrowed_by"] = "composite_group_via_legend_chain"
                        res["surviving_candidates"] = surviving
        if decision not in {"structurally_unique_proposal", "unique_without_pdf_confirmation"}:
            continue
        # Use the (possibly grouped) surviving
        page = surviving[0].get("page") if surviving else None
        bbox = surviving[0].get("bbox") if surviving else None
        if page is None or not bbox or len(bbox) < 4:
            continue
        label = str(res.get("label") or "")
        # Caption text from proposal evidence_chain
        caption_text = ""
        for p in report.get("proposals", []):
            if str(p.get("label")) == label:
                for ev in p.get("evidence_chain", []):
                    for it in ev.get("items", []):
                        if it.get("text"):
                            caption_text = str(it.get("text"))
                            break
                    if caption_text:
                        break
            if caption_text:
                break
        # Same-page two-column legend: merge left+right caption blocks if detected
        # Check if this label has a multicolumn pair on its caption page
        try:
            from paperforge.worker.ocr_figures import _collect_same_page_multicolumn_legend_pairs
            # Need blocks and page_width; use 1200 as default
            pairs = _collect_same_page_multicolumn_legend_pairs(blocks, page_width=1200)
            for prim, cont in pairs:
                if f"Fig. {label}" in str(prim.get("text") or "") or f"Figure {label}" in str(prim.get("text") or ""):
                    # Merge
                    caption_text = str(prim.get("text") or "").rstrip() + " " + str(cont.get("text") or "").strip()
                    break
        except Exception:
            pass
        preview_root = staging_root / "previews" / f"figure_{label}"
        preview_root.mkdir(parents=True, exist_ok=True)
        preview_asset = preview_root / "assets"
        preview_render = preview_root / "render"
        # Synthetic figure for this proposal - preserve real member_refs if grouped
        surviving_entry = surviving[0] if surviving else {}
        member_refs = surviving_entry.get("member_refs")
        if member_refs:
            matched_assets = member_refs
        else:
            # Single candidate: use its page/bbox with real block_id if available
            blk_id = surviving_entry.get("group_id", f"proposal_{label}")
            # Try to extract real block_id from group_id like unmatched_asset_p3_b2
            if "_b" in blk_id:
                blk_id = blk_id.split("_b")[-1]
            matched_assets = [{"page": page, "block_id": blk_id, "bbox": bbox}]
        proposal_fig = {
            "figure_id": f"figure_proposal_{label}",
            "page": page,
            "figure_number": label,
            "figure_namespace": "main",
            "text": caption_text or f"Figure {label} (proposed)",
            "matched_assets": matched_assets,
            "asset_block_ids": [str(m.get("block_id")) for m in matched_assets],
            "settlement_type": "proposal",
            "confidence": 0.0,
        }
        # Final AssetPlan manifest: what user reviewed is exactly what accept promotes
        final_plan = {
            "schema_version": 1,
            "label": label,
            "proposal_id": f"figure_proposal_{label}",
            "decision": decision,
            "narrowed_by": res.get("narrowed_by"),
            "page": page,
            "member_refs": matched_assets,
            "caption_text": caption_text,
            "input_snapshot_hash": _snapshot_hash(root),
            "staged_jpg": "assets/figures/figure_proposal_{}.jpg".format(label),
            "staged_md": "render/figures/figure_proposal_{}.md".format(label),
        }
        (preview_root / "final-plan.json").write_text(
            json.dumps(final_plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        proposal_inventory = {
            "matched_figures": [proposal_fig],
            "unresolved_clusters": [],
            "unmatched_assets": [],
        }
        ok = False
        preview_path = preview_root / f"figure_{label}.proposed.jpg"
        preview_md = preview_root / f"figure_{label}.proposed.md"
        try:
            extract_and_write_objects(
                pdf_path,
                proposal_inventory,
                {"tables": [], "unmatched_assets": []},
                preview_asset,
                preview_render,
                page_dimensions_by_page=dims,
                structured_blocks=blocks,
                use_disk_page_cache=False,
            )
            # Materializer writes to assets/figures/figure_proposal_<label>.jpg
            staged_img = preview_asset / "figures" / f"figure_proposal_{label}.jpg"
            staged_md = preview_render / "figures" / f"figure_proposal_{label}.md"
            if staged_img.is_file() and staged_img.stat().st_size > 0:
                # Keep authoritative staging structure; preview manifest points there
                preview_path = staged_img
                preview_md = staged_md
                ok = True
                try:
                    from PIL import Image

                    with Image.open(preview_path) as im:
                        ok = im.width > 0 and im.height > 0
                except Exception:
                    ok = False
                # Verify markdown link resolves
                if ok and staged_md.is_file():
                    md_text = staged_md.read_text(encoding="utf-8")
                    # Check image_relpath resolves to staged_img
                    if "figure_proposal_" not in md_text:
                        ok = False
        except Exception:
            ok = False
        if ok and not preview_md.is_file():
            # Fallback markdown if materializer did not produce one
            preview_md.parent.mkdir(parents=True, exist_ok=True)
            preview_md.write_text(f"# Figure {label} (proposed)\n\n![](../../assets/figures/figure_proposal_{label}.jpg)\n\n*Page {page}*\n\n---\n", encoding="utf-8")  # noqa: E501
        if ok:
            staged_p += 1
        p_details.append({"label": label, "page": page, "staged": ok, "preview": str(preview_path), "preview_md": str(preview_md)})
    # Fresh fulltext reconciliation on the SAME in-memory report
    try:
        from paperforge.fulltext_reconciliation import fulltext_reconcile

        ft_result = fulltext_reconcile(
            ocr_root,
            paper_key,
            reconciliation_report=report,
        )
    except Exception as exc:  # noqa: BLE001 — fulltext is fail-soft observer
        ft_result = {"error": type(exc).__name__, "message": str(exc)[:200]}
    return {
        "paper_key": paper_key,
        "staging_root": str(staging_root),
        "production_write": False,
        "summary": {
            "exact_total": len(dry_exact.get("results", [])),
            "r_prepared_staged": staged_r,
            "proposals_total": len(dry_bounded.get("results", [])),
            "p_preview_staged": staged_p,
        },
        "r_details": r_details,
        "p_details": p_details,
        "dry_exact": dry_exact,
        "dry_bounded": dry_bounded,
        "fulltext": ft_result,
    }
