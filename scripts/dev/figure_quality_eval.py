"""Figure quality evaluation harness (read-only replay, no vault writes)."""

import hashlib

import math

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_DRYRUN_PATH = ROOT / "scripts" / "dev" / "object_migration_dry_run.py"
_SPEC = importlib.util.spec_from_file_location("object_migration_dry_run", _DRYRUN_PATH)
assert _SPEC and _SPEC.loader
DRY = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(DRY)

try:
    import fitz  # type: ignore
except Exception:  # pragma: no cover
    fitz = None
try:
    from PIL import Image, ImageDraw  # type: ignore
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None

VAULT_DEFAULT = Path("D:/Zotero-Vault")
OCR_DEFAULT = None
SET_DIR = ROOT / "docs" / "evidence" / "figure-quality" / "sets"
OUT_ROOT = ROOT / "docs" / "evidence" / "figure-quality"

LABEL_FIELDS = [
    "key", "kind", "figure_id", "page", "block_id", "expected_owner", "current_assets",
    "snapshot_fingerprint", "source_pdf_sha256", "asset_sha256", "render_sha256",
    "fulltext_sha256", "caption_ok", "panels_ok", "crop_ok", "delivery_ok",
    "notes", "reviewer", "reviewed_at",
]


def load_set(name: str) -> list[str]:
    path = SET_DIR / f"{name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("keys", []))


def reviewed(label: dict[str, Any]) -> bool:
    reviewer = str(label.get("reviewer", "") or "").strip().lower()
    return reviewer not in {"", "unreviewed", "todo", "tbd"}


def filter_reviewed(labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [lb for lb in labels if reviewed(lb)]


def score_association(labels: list[dict[str, Any]], replay_figures: list[dict[str, Any]]) -> dict[str, Any]:
    """Precision/recall of figure->asset association against reviewed labels."""
    by_id = {str(f.get("figure_id")): f for f in replay_figures}
    tp = fp = fn = unknown = 0
    for lb in filter_reviewed(labels):
        fid = str(lb.get("figure_id"))
        rf = by_id.get(fid, {})
        replay_assets = {
            str(a.get("block_id")) for a in (rf.get("matched_assets") or [])
            if a.get("block_id") is not None
        }
        expected_raw = lb.get("expected_owner")
        if expected_raw is None:
            unknown += 1
            continue
        if isinstance(expected_raw, (list, tuple)):
            expected = {str(x) for x in expected_raw}
        else:
            expected = {x for x in str(expected_raw).replace(",", " ").split() if x}
        tp += len(replay_assets & expected)
        fp += len(replay_assets - expected)
        fn += len(expected - replay_assets)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    return {"tp": tp, "fp": fp, "fn": fn, "unknown_expected": unknown,
            "precision": precision, "recall": recall,
            "f1": (2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) else 1.0}




def score_labels(
    labels: list[dict[str, Any]], replay: dict[str, Any] | None = None,
    manual_findings: list[dict[str, Any]] | None = None, key: str = "",
    snapshot_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Score agent labels and confirmed findings only for the current snapshot."""
    rev = filter_reviewed(labels)
    def failures(rows, field):
        return sum(1 for lb in rows if lb.get(field) is False)
    def known(rows, field):
        return sum(1 for lb in rows if lb.get(field) is not None)
    out = {
        "total_labels": len(labels),
        "reviewed": len(rev),
        "unreviewed": len(labels) - len(rev),
        "crop_failures": failures(rev, "crop_ok"),
        "delivery_failures": failures(rev, "delivery_ok"),
        "caption_failures": failures(rev, "caption_ok"),
        "panel_failures": failures(rev, "panels_ok"),
        "known": {field: known(rev, field) for field in ("crop_ok", "delivery_ok", "caption_ok", "panels_ok")},
        "association": score_association(rev, replay.get("figures", [])) if replay is not None else None,
    }
    if manual_findings is not None:
        scoped = [
            f for f in manual_findings
            if f.get("key") == key
            and (
                snapshot_fingerprint is None
                or f.get("snapshot_fingerprint") == snapshot_fingerprint
            )
        ]
        confirmed = [f for f in scoped if f.get("status") == "confirmed"]
        human_rows = []
        for finding in confirmed:
            human_rows.append({
                "key": key, "figure_id": finding.get("figure"), "reviewer": "user-manual",
                "expected_owner": finding.get("expected_asset_blocks"),
                "crop_ok": finding.get("crop_ok"), "delivery_ok": finding.get("delivery_ok"),
                "caption_ok": finding.get("caption_ok"), "panels_ok": finding.get("panel_ok"),
            })
        human = score_labels(human_rows, replay)
        out["agent_scored"] = out.copy()
        out["human_verified"] = human
        unresolved = [f for f in scoped if f.get("status") != "superseded"]
        out["unknown"] = {
            field: sum(1 for f in unresolved if f.get(field) is None)
            for field in ("expected_asset_blocks", "crop_ok", "delivery_ok", "panel_ok")
        }
        out["unknown"]["findings"] = sum(
            any(f.get(field) is None for field in ("expected_asset_blocks", "crop_ok", "delivery_ok", "panel_ok"))
            for f in unresolved
        )
        out["superseded"] = sum(f.get("status") == "superseded" for f in scoped)
        out["disputed"] = sum(f.get("status") == "disputed" for f in scoped)
        out["lifecycle_counts"] = {
            "confirmed": len(confirmed), "superseded": out["superseded"],
            "disputed": out["disputed"],
        }
        out["figure_count_delta"] = -sum(bool(f.get("missing_figure")) for f in confirmed)
        for field in ("crop_failures", "delivery_failures", "caption_failures", "panel_failures"):
            out[field] = human[field]
        out["known"] = human["known"]
        out["association"] = human["association"]
    return out


def diff_results(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Per-case fixed/regressed diff between two result JSONs."""
    prev_cases = {c.get("key"): c for c in previous.get("cases", []) if "key" in c}
    curr_cases = {c.get("key"): c for c in current.get("cases", []) if "key" in c}
    fixed = []
    regressed = []
    for key in sorted(set(prev_cases) | set(curr_cases)):
        p = prev_cases.get(key, {})
        c = curr_cases.get(key, {})
        p_ok = p.get("passed", p.get("ok"))
        c_ok = c.get("passed", c.get("ok"))
        if p_ok is False and c_ok is True:
            fixed.append(key)
        elif p_ok is True and c_ok is False:
            regressed.append(key)
    return {"fixed": fixed, "regressed": regressed,
            "fixed_count": len(fixed), "regressed_count": len(regressed)}


def structural_baseline(key: str, dry_entry: dict[str, Any], ocr_root: Path) -> dict[str, Any]:
    ident = dry_entry.get("identity", {})
    new = ident.get("new", {})
    old = ident.get("old", {})
    delivery = dry_entry.get("delivery", {})
    content = dry_entry.get("content", {})
    paper_dir = ocr_root / key
    # count missing manifest files
    # dangling embeds
    dangling = len(delivery.get("embeds_missing_new_id", []) or [])
    unique_ok = (new.get("unique_ids", 0) == new.get("entries", 0)) if new else False
    text_decrease = content.get("new_text_chars", 0) < content.get("old_text_chars", 0) if content else False
    pending = 0
    inv = paper_dir / "structure" / "figure_inventory.json"
    if inv.is_file():
        try:
            d = json.loads(inv.read_text(encoding="utf-8"))
            pending = len(d.get("held_figures", []) or []) + len(d.get("unresolved_clusters", []) or [])
        except Exception:
            pending = 0
    manifest_delivery = delivery.get("manifest_delivery", {})
    return {
        "key": key,
        "unique_ids_ok": bool(unique_ok),
        "dangling_fulltext_targets": dangling,
        "missing_manifest_assets": list(manifest_delivery.get("missing_assets", [])),
        "missing_manifest_renders": list(manifest_delivery.get("missing_renders", [])),
        "pending_markers": pending,
        "text_decrease": bool(text_decrease),
        "old_text_chars": content.get("old_text_chars"),
        "new_text_chars": content.get("new_text_chars"),
        "old_entries": old.get("entries"),
        "new_entries": new.get("entries"),
    }


def _render_page_with_overlays(
    pdf_path: Path, page_num: int, overlays: list, out_path: Path, scale: float = 1.0
) -> None:
    if fitz is None or Image is None:
        return
    import contextlib
    with contextlib.suppress(Exception):
        doc = fitz.open(str(pdf_path))
        if page_num - 1 >= len(doc):
            doc.close()
            return
        page = doc[page_num - 1]
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        draw = ImageDraw.Draw(img) if ImageDraw is not None else None
        if draw is not None:
            for bbox, color, label in overlays:
                if not bbox or len(bbox) != 4:
                    continue
                x0, y0, x1, y1 = [int(v) for v in bbox]
                x0 = max(0, min(img.width, x0))
                y0 = max(0, min(img.height, y0))
                x1 = max(0, min(img.width, x1))
                y1 = max(0, min(img.height, y1))
                draw.rectangle((x0, y0, x1, y1), outline=color, width=3)
                draw.text((x0, max(0, y0 - 12)), str(label), fill=color)
        if img.width > 700:
            ratio = 700 / img.width
            img = img.resize((700, int(img.height * ratio)))
        img.save(out_path, "JPEG", quality=35, optimize=True)
        doc.close()


def ocr_to_pdf_bbox(bbox, ocr_width, ocr_height, pdf_width, pdf_height):
    sx = pdf_width / ocr_width if ocr_width else 1.0
    sy = pdf_height / ocr_height if ocr_height else 1.0
    return [bbox[0] * sx, bbox[1] * sy, bbox[2] * sx, bbox[3] * sy]


def render_scale_for_page(ocr_width, ocr_height, pdf_width, pdf_height):
    if not pdf_width:
        return 1.0
    return (ocr_width or pdf_width) / pdf_width


def _vault_ocr_root(vault: Path, ocr_root: Path | None) -> Path:
    return ocr_root if ocr_root else vault / "System" / "PaperForge" / "ocr"


def _review_inventory(replay_inventory: dict | None, paper_dir: Path) -> dict:
    if replay_inventory is not None:
        return replay_inventory
    return DRY._read_json(paper_dir / "structure" / "figure_inventory.json")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _pdf_page_count(path: Path | None) -> int | None:
    if path is None or not path.exists():
        return None
    try:
        import fitz as _fitz
        doc = _fitz.open(str(path))
        n = doc.page_count
        doc.close()
        return n
    except Exception:  # noqa: BLE001
        return None


def _expected_source_provenance(paper_dir: Path, vault: Path) -> dict[str, Any]:
    meta = DRY._read_json(paper_dir / "meta.json") or {}
    raw_meta = DRY._read_json(paper_dir / "raw" / "raw_meta.json") or {}
    source_meta = DRY._read_json(paper_dir / "raw" / "source_metadata.json") or {}
    locator = source_meta.get("source_pdf") or meta.get("source_pdf")
    try:
        from paperforge.pdf_resolver import resolve_source_pdf
        expected_path = resolve_source_pdf(vault, locator) if locator else None
    except Exception:  # noqa: BLE001
        expected_path = None
    expected_page_count = (
        meta.get("source_page_count")
        or meta.get("page_count")
        or raw_meta.get("page_count")
    )
    raw_version = meta.get("raw_version") or {}
    expected_fp = raw_version.get("pdf_fingerprint") or raw_meta.get("pdf_fingerprint")
    return {
        "source_pdf": locator,
        "path": str(expected_path) if expected_path else None,
        "page_count": expected_page_count,
        "fingerprint": expected_fp,
    }


def _source_identity_mismatch(expected: dict[str, Any], observed: dict[str, Any]) -> bool:
    expected_path = expected.get("path")
    observed_path = observed.get("path")
    if not expected_path or not observed_path or str(expected_path) != str(observed_path):
        return True

    expected_pages = expected.get("page_count")
    observed_pages = observed.get("page_count")
    if expected_pages is None or observed_pages is None:
        return True
    try:
        if int(expected_pages) < 1 or int(expected_pages) != int(observed_pages):
            return True
    except (TypeError, ValueError):
        return True

    expected_fingerprint = str(expected.get("fingerprint") or "").strip()
    observed_fingerprint = str(observed.get("fingerprint") or "").strip()
    return not expected_fingerprint or not observed_fingerprint or expected_fingerprint != observed_fingerprint


def _image_evidence_fingerprints(
    review_dir: Path, snapshot: dict,
) -> dict[str, dict[str, str]]:
    files = snapshot.get("files", {}) or {}
    return {
        "page_images": {
            path.name: _sha256_file(path)
            for path in sorted(review_dir.glob("page_*.jpg"))
        },
        "crop_images": {
            Path(rel).name: row["sha256"]
            for rel, row in files.items()
            if rel.startswith("assets/figures/") and rel.lower().endswith((".jpg", ".jpeg", ".png"))
        },
        "render_files": {
            Path(rel).name: row["sha256"]
            for rel, row in files.items()
            if rel.startswith("render/figures/") and rel.endswith(".md")
        },
    }


def _snapshot_delivery_audit(replay: dict, snapshot: dict, page_count: int | None) -> dict:
    snapshot_dir = Path(snapshot["directory"])
    files = snapshot.get("files", {}) or {}
    manifest = snapshot.get("manifest", {}) or {}
    expected_assets = manifest.get("assets", []) or []
    expected_renders = manifest.get("render", []) or []
    rows = replay.get("rows", []) or []
    blocks = {
        (int(row.get("page", 0) or 0), str(row.get("block_id"))): row
        for row in rows
        if row.get("page") and row.get("block_id") is not None
    }
    embeds = replay.get("embeds", []) or []
    associations = replay.get("figure_inventory", {}).get("association_reservations", []) or []
    results = {}

    for figure in replay.get("figures", []) or []:
        fid = str(figure.get("figure_id") or "")
        claims = figure.get("matched_assets") or []
        reserved = (
            fid.startswith("figure_reserved_")
            or figure.get("settlement_type") == "cross_page_reservation"
            or any(
                str(item.get("figure_id") or item.get("reserved_figure_id") or "") == fid
                and item.get("status") in {"RESERVED", "HOLD"}
                for item in associations
            )
        )
        valid_claim = bool(claims)
        for claim in claims:
            page = int(claim.get("page", 0) or 0)
            block_id = str(claim.get("block_id") or "")
            row = blocks.get((page, block_id))
            bbox = claim.get("bbox") or (row or {}).get("bbox")
            if not row or (page_count and not 1 <= page <= page_count) or not bbox or len(bbox) != 4:
                valid_claim = False
                break
            try:
                x0, y0, x1, y1 = [float(value) for value in bbox]
                width = float(row.get("page_width") or 0)
                height = float(row.get("page_height") or 0)
                valid_claim = (
                    all(math.isfinite(value) for value in (x0, y0, x1, y1))
                    and x0 >= 0 and y0 >= 0 and x1 > x0 and y1 > y0
                    and (not width or x1 <= width)
                    and (not height or y1 <= height)
                )
            except (TypeError, ValueError):
                valid_claim = False
            if not valid_claim:
                break

        asset_candidates = [
            rel for rel in expected_assets
            if Path(rel).stem == fid and "figures" in Path(rel).parts
        ]
        asset_rel = asset_candidates[0] if asset_candidates else None
        asset_record = files.get(asset_rel, {}) if asset_rel else {}
        asset_path = snapshot_dir / asset_rel if asset_rel and asset_record else None
        image_valid = False
        if asset_path is not None and Image is not None:
            try:
                with Image.open(asset_path) as image:
                    image.verify()
                image_valid = True
            except Exception:  # noqa: BLE001 — corrupt or non-image crop is not delivery
                pass

        render_candidates = [
            rel for rel in expected_renders
            if Path(rel).stem == fid and "figures" in Path(rel).parts
        ]
        render_rel = render_candidates[0] if render_candidates else None
        render_record = files.get(render_rel, {}) if render_rel else {}
        render_path = snapshot_dir / render_rel if render_rel and render_record else None
        render_text = render_path.read_text(encoding="utf-8") if render_path else ""
        render_references_crop = bool(asset_rel and Path(asset_rel).name in render_text)
        embed_exists = bool(
            render_rel
            and any(
                item.get("kind") == "figures"
                and item.get("object_id") == fid
                and item.get("target") == render_rel
                for item in embeds
            )
            and "fulltext.md" in files
        )
        reasons = []
        if not claims:
            reasons.append("no_asset_claim")
        elif not valid_claim:
            reasons.append("invalid_asset_claim")
        if not asset_record:
            reasons.append("missing_crop_file")
        elif not image_valid:
            reasons.append("invalid_crop_image")
        if not render_record:
            reasons.append("missing_render")
        elif not render_references_crop:
            reasons.append("render_missing_crop_reference")
        if not embed_exists:
            reasons.append("missing_fulltext_embed")

        state = (
            "UNRESOLVED_RESERVATION" if reserved and not claims
            else "RESOLVED" if valid_claim and image_valid and render_references_crop and embed_exists
            else "DELIVERY_DEFECT"
        )
        results[fid] = {
            "state": state,
            "claim_count": len(claims),
            "valid_asset_claim": valid_claim,
            "asset_path": asset_rel,
            "asset_sha256": asset_record.get("sha256"),
            "crop_image_valid": image_valid,
            "render_path": render_rel,
            "render_sha256": render_record.get("sha256"),
            "render_references_crop": render_references_crop,
            "embed_exists": embed_exists,
            "fulltext_sha256": (files.get("fulltext.md") or {}).get("sha256"),
            "reasons": reasons,
        }

    states = {fid: row["state"] for fid, row in results.items()}
    return {
        "status": "NO_MATCHED_FIGURES" if not states else (
            "RESOLVED" if all(state == "RESOLVED" for state in states.values()) else "HOLD"
        ),
        "figure_states": states,
        "figures": results,
        "summary": {
            "resolved": sum(state == "RESOLVED" for state in states.values()),
            "unresolved_reservations": sum(state == "UNRESOLVED_RESERVATION" for state in states.values()),
            "delivery_defects": sum(state == "DELIVERY_DEFECT" for state in states.values()),
        },
        "expected_assets_missing": [rel for rel in expected_assets if rel not in files],
        "expected_renders_missing": [rel for rel in expected_renders if rel not in files],
    }






def _label_matches_snapshot(
    label: dict, snapshot: dict, source_pdf_sha256: str | None,
    delivery: dict, replay: dict,
) -> bool:
    if (
        label.get("snapshot_fingerprint") != snapshot.get("fingerprint")
        or label.get("source_pdf_sha256") != source_pdf_sha256
    ):
        return False
    if label.get("kind") == "matched_figure":
        evidence = (delivery.get("figures") or {}).get(str(label.get("figure_id") or ""))
        return bool(evidence) and all(
            label.get(field) == evidence.get(field)
            for field in ("asset_sha256", "render_sha256", "fulltext_sha256")
        )
    if label.get("kind") == "unmatched_legend":
        page = int(label.get("page", 0) or 0)
        block_id = str(label.get("block_id") or "")
        return (
            label.get("fulltext_sha256") == (snapshot.get("files", {}).get("fulltext.md") or {}).get("sha256")
            and any(
                int(row.get("page", 0) or 0) == page
                and str(row.get("block_id") or "") == block_id
                for row in replay.get("rows", []) or []
            )
        )
    return False


def _finding_matches_snapshot(
    finding: dict, snapshot: dict, source_pdf_sha256: str | None, delivery: dict,
) -> bool:
    if (
        finding.get("snapshot_fingerprint") != snapshot.get("fingerprint")
        or finding.get("source_pdf_sha256") != source_pdf_sha256
    ):
        return False
    fid = str(finding.get("figure_id") or finding.get("figure") or "")
    evidence = (delivery.get("figures") or {}).get(fid)
    return bool(evidence) and all(
        finding.get(field) == evidence.get(field)
        for field in ("asset_sha256", "render_sha256", "fulltext_sha256")
    )
def load_source_overrides(path: str | Path | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if manifest.get("schema") != "paperforge.figure_quality_source_manifest.v1":
        raise ValueError("unsupported source manifest schema")
    overrides = manifest.get("source_overrides", {})
    if not isinstance(overrides, dict) or any(not isinstance(row, dict) for row in overrides.values()):
        raise ValueError("source_overrides must map paper keys to objects")
    return overrides


def run_key(
    vault: Path, ocr_root: Path, key: str, out_dir: Path,
    source_override: dict[str, Any] | None = None,
    work_root: Path | None = None,
) -> dict[str, Any]:
    """Rebuild one paper in isolation and derive its review evidence.

    ``work_root`` holds the heavy rebuild snapshot payload; ``out_dir`` receives only
    the derived evidence. Without it, both live under ``out_dir``.
    """
    paper_dir = ocr_root / key
    meta = DRY._read_json(paper_dir / "meta.json") or {}
    recorded_prov = _expected_source_provenance(paper_dir, vault)
    source_meta = DRY._read_json(paper_dir / "raw" / "source_metadata.json") or {}
    recorded_locator = source_meta.get("source_pdf") or meta.get("source_pdf")
    locator = (source_override or {}).get("source_pdf") or recorded_locator
    try:
        from paperforge.pdf_resolver import resolve_source_pdf

        pdf = resolve_source_pdf(vault, locator) if locator else None
    except Exception:  # noqa: BLE001 — unresolved provenance is a source mismatch
        pdf = None
    meta["source_pdf"] = locator
    if source_override:
        expected_prov = {
            "source_pdf": locator,
            "path": str(pdf) if pdf else None,
            "page_count": source_override.get("page_count"),
            "fingerprint": source_override.get("fingerprint"),
        }
        source_selection = {
            "kind": "manifest_override",
            "recorded_source_pdf": recorded_locator,
            "basis": source_override.get("basis", ""),
        }
    else:
        expected_prov = recorded_prov
        source_selection = None
    observed_prov = {
        "source_pdf": locator,
        "path": str(pdf) if pdf else None,
        "page_count": _pdf_page_count(pdf),
        "fingerprint": _sha256_file(pdf) if pdf else None,
    }
    recorded_mismatch = _source_identity_mismatch(recorded_prov, observed_prov)
    expected_mismatch = _source_identity_mismatch(expected_prov, observed_prov)
    source_provenance = {
        "recorded": recorded_prov,
        "expected": expected_prov,
        "observed": observed_prov,
        "checks": {
            "recorded_identity_match": not recorded_mismatch,
            "selected_identity_match": not expected_mismatch,
        },
    }
    if source_selection:
        source_provenance["selection"] = source_selection
    if recorded_mismatch or expected_mismatch:
        case_result = {
            "key": key,
            "status": "SOURCE_MISMATCH",
            "result": "SOURCE_MISMATCH",
            "classification": "SOURCE_MISMATCH",
            "source_mismatch": True,
            "source_provenance": source_provenance,
            "source_pdf_sha256": observed_prov.get("fingerprint"),
            "snapshot_fingerprint": None,
            "rebuilt_state": {"status": "NOT_REBUILT"},
            "visual_review_status": "UNKNOWN_SOURCE_MISMATCH",
            "visual_label_counts": {"total": 0, "snapshot_bound": 0, "reviewed": 0, "unreviewed": 0, "stale": 0},
            "evidence_fingerprints": {"page_images": {}, "crop_images": {}, "render_files": {}},
            "structural_pass": False,
            "visual_pass": False,
            "accepted": False,
            "acceptance_blocked_by": ["source_identity_mismatch"],
            "figures": 0,
            "structural": {},
            "expected": expected_prov,
            "observed": observed_prov,
        }
        return {
            "key": key, "entry": {}, "baseline": {}, "case": case_result,
            "out_dir": str(out_dir / key), "snapshot_dir": None, "snapshot": None,
            "replay_figures": [], "bound_labels": [],
        }
    # Rebuild once in isolation; its persisted snapshot feeds audit and review evidence.
    kdir = out_dir / key
    kdir.mkdir(parents=True, exist_ok=True)
    snapshot_root = (work_root or kdir) / key / "rebuild_snapshots"
    try:
        replay_kwargs = {"snapshot_root": snapshot_root}
        if source_override:
            replay_kwargs["source_pdf_override"] = pdf
        new = DRY._rebuild_replay(vault, ocr_root, key, **replay_kwargs)
        snapshot = new.get("snapshot")
        if not snapshot:
            raise RuntimeError("isolated rebuild did not persist a review snapshot")
        replay_figures = new["figures"]
        replay_rows = new.get("rows", [])
        replay_inventory = new.get("figure_inventory") or {}
        entry = DRY.audit_key(vault, ocr_root, key, plan=False, replay=new)
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
        case_result = {
            "key": key, "status": "REBUILD_ERROR", "result": "REBUILD_ERROR",
            "classification": "REBUILD_ERROR", "structural_pass": False,
            "visual_pass": False, "accepted": False,
            "acceptance_blocked_by": ["rebuild_error"],
            "source_provenance": source_provenance, "error": error,
            "visual_review_status": "UNKNOWN",
        }
        return {
            "key": key, "entry": {"key": key, "error": error}, "baseline": {},
            "case": case_result, "out_dir": str(kdir), "snapshot_dir": None,
        }

    snapshot_dir = Path(snapshot["directory"])
    # Derived evidence is small and belongs with out_dir; the rebuild payload is large and
    # lives in the snapshot directory. Human labels must survive a rerun, so they are keyed
    # by paper rather than by fingerprint.
    evidence_dir = kdir
    evidence_dir.mkdir(parents=True, exist_ok=True)
    # Page previews are large and fully reproducible from the source PDF + snapshot, so they
    # live in the work root. Evidence keeps the small artifacts and their hashes.
    review_dir = (work_root or kdir) / key / "review_context"
    review_dir.mkdir(parents=True, exist_ok=True)
    inv = replay_inventory
    rebuilt_delivery = _snapshot_delivery_audit(new, snapshot, observed_prov.get("page_count"))
    labels_path = evidence_dir / "labels.jsonl"
    if not labels_path.is_file():
        lines = []
        for f in replay_figures:
            fid = str(f.get("figure_id"))
            asset_ids = [
                str(a.get("block_id")) for a in (f.get("matched_assets") or [])
                if a.get("block_id") is not None
            ]
            evidence = rebuilt_delivery["figures"].get(fid, {})
            row = {
                "key": key,
                "kind": "matched_figure",
                "figure_id": fid,
                "page": int(f.get("page", 0) or 0),
                "expected_owner": "",
                "current_assets": " ".join(asset_ids),
                "snapshot_fingerprint": snapshot["fingerprint"],
                "source_pdf_sha256": observed_prov.get("fingerprint"),
                "asset_sha256": evidence.get("asset_sha256"),
                "render_sha256": evidence.get("render_sha256"),
                "fulltext_sha256": evidence.get("fulltext_sha256"),
                "caption_ok": None,
                "panels_ok": None,
                "crop_ok": None,
                "delivery_ok": None,
                "notes": "",
                "reviewer": "",
                "reviewed_at": "",
            }
            lines.append(json.dumps(row, ensure_ascii=False))
        unmatched_label_rows = list(inv.get("unmatched_legends", []) or [])
        seen_legend_blocks = {
            str(row.get("block_id"))
            for row in unmatched_label_rows
            if row.get("block_id") is not None
        }
        for row in replay_rows:
            if (
                str(row.get("role")) == "figure_caption_candidate"
                and str(row.get("block_id")) not in seen_legend_blocks
            ):
                unmatched_label_rows.append(row)
                seen_legend_blocks.add(str(row.get("block_id")))
        fulltext_sha = (snapshot.get("files", {}).get("fulltext.md") or {}).get("sha256")
        for unmatched in unmatched_label_rows:
            lines.append(json.dumps({
                "key": key,
                "kind": "unmatched_legend",
                "figure_id": "",
                "page": int(unmatched.get("page", 0) or 0),
                "block_id": unmatched.get("block_id"),
                "expected_owner": "",
                "current_assets": "",
                "snapshot_fingerprint": snapshot["fingerprint"],
                "source_pdf_sha256": observed_prov.get("fingerprint"),
                "asset_sha256": None,
                "render_sha256": None,
                "fulltext_sha256": fulltext_sha,
                "caption_ok": None,
                "panels_ok": None,
                "crop_ok": None,
                "delivery_ok": None,
                "notes": "",
                "reviewer": "",
                "reviewed_at": "",
            }, ensure_ascii=False))
        labels_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    inv = replay_inventory
    unmatched_legends = inv.get("unmatched_legends", []) or []
    unmatched_assets = inv.get("unmatched_assets", []) or []
    caption_rows = [r for r in replay_rows if str(r.get("role")) in {"figure_caption", "figure_caption_candidate"}]

    page_ocr_size = {}
    for source in (replay_rows, unmatched_legends, unmatched_assets, caption_rows):
        for item in source:
            pg = item.get("page")
            if pg and item.get("page_width") and item.get("page_height") and pg not in page_ocr_size:
                page_ocr_size[pg] = (item.get("page_width"), item.get("page_height"))

    pages = set()
    for figure in replay_figures:
        if figure.get("page"):
            pages.add(int(figure.get("page")))
        for asset in figure.get("matched_assets") or []:
            if asset.get("page"):
                pages.add(int(asset.get("page")))
    # pages to render
    for u in unmatched_legends:
        if u.get("page"):
            pages.add(int(u.get("page")))
    for a in unmatched_assets:
        if a.get("page"):
            pages.add(int(a.get("page")))
    for r in caption_rows:
        if r.get("page"):
            pages.add(int(r.get("page")))

    if pdf is not None and fitz is not None:
        for pg in sorted(pages):
            out_path = review_dir / f"page_{pg:03d}.jpg"
            overlays = []
            for f in replay_figures:
                for a in (f.get("matched_assets") or []):
                    if int(a.get("page", 0) or 0) == pg and a.get("bbox"):
                        overlays.append((a.get("bbox"), (0, 0, 255), str(f.get("figure_id"))))
            for asset in unmatched_assets:
                if int(asset.get("page", 0) or 0) == pg and asset.get("bbox"):
                    overlays.append((asset.get("bbox"), (255, 140, 0), "unmatched_asset"))
            for legend in unmatched_legends:
                if int(legend.get("page", 0) or 0) == pg and legend.get("bbox"):
                    overlays.append((legend.get("bbox"), (255, 0, 0), "unmatched_legend"))
            for row in caption_rows:
                if int(row.get("page", 0) or 0) == pg and row.get("bbox"):
                    overlays.append((row.get("bbox"), (0, 180, 0), "caption_candidate"))
            ocr_w, ocr_h = page_ocr_size.get(pg, (None, None))
            doc = fitz.open(str(pdf))
            if pg < 1 or pg > len(doc):
                doc.close()
                continue
            page = doc[pg - 1]
            if not ocr_w:
                ocr_w, ocr_h = page.rect.width, page.rect.height
            scale = render_scale_for_page(ocr_w, ocr_h, page.rect.width, page.rect.height)
            doc.close()
            _render_page_with_overlays(pdf, pg, overlays, out_path, scale)
    baseline = structural_baseline(key, entry, ocr_root)
    baseline["unmatched"] = {
        "legends": [
            {"page": u.get("page"), "block_id": u.get("block_id"), "text": str(u.get("text", ""))[:300]}
            for u in unmatched_legends
        ],
        "assets": [
            {"page": a.get("page"), "bbox": a.get("bbox")} for a in unmatched_assets
        ],
        "caption_candidates": [
            {"page": r.get("page"), "block_id": r.get("block_id"), "text": str(r.get("text", ""))[:300]}
            for r in caption_rows
        ],
    }
    evidence_fingerprints = _image_evidence_fingerprints(review_dir, snapshot)
    baseline["source_provenance"] = source_provenance
    baseline["snapshot_fingerprint"] = snapshot["fingerprint"]
    baseline["evidence_fingerprints"] = evidence_fingerprints
    baseline["rebuilt_state"] = {
        "snapshot_fingerprint": snapshot["fingerprint"],
        "delivery": rebuilt_delivery,
    }
    historical_inventory_path = paper_dir / "structure" / "figure_inventory.json"
    baseline["historical_state"] = {
        "figure_inventory_sha256": (
            _sha256_file(historical_inventory_path) if historical_inventory_path.is_file() else None
        ),
        "pending_markers": baseline.get("pending_markers", 0),
    }
    held_records = inv.get("held_figures", []) or []
    holds = [
        {
            "page": hold.get("legend_page", hold.get("page")),
            "legend_block_id": hold.get("legend_block_id"),
            "text": hold.get("text"),
            "hold_reason": hold.get("hold_reason"),
            "candidate_groups": hold.get("candidate_groups", []),
        }
        for hold in held_records
    ]
    reservation_records = inv.get("association_reservations", []) or []
    reservation_status_counts = {
        status: sum(1 for item in reservation_records if item.get("status") == status)
        for status in ("RESERVED", "RESOLVED", "HOLD")
    }
    baseline["figure_holds"] = holds
    baseline["reservation_status_counts"] = reservation_status_counts
    (evidence_dir / "audit.json").write_text(
        json.dumps(
            {"dry_run": entry, "structural": baseline, "unmatched": baseline["unmatched"]},
            ensure_ascii=False, indent=1,
        ),
        encoding="utf-8",
    )
    label_rows = [
        json.loads(line) for line in labels_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    bound_label_rows = [
        row for row in label_rows
        if _label_matches_snapshot(
            row, snapshot, observed_prov.get("fingerprint"), rebuilt_delivery, new,
        )
    ]
    stale_label_count = len(label_rows) - len(bound_label_rows)
    complete_labels = [
        row for row in bound_label_rows
        if reviewed(row) and all(isinstance(row.get(field), bool) for field in (
            "caption_ok", "panels_ok", "crop_ok", "delivery_ok",
        ))
    ]
    visually_complete = bool(label_rows) and len(bound_label_rows) == len(label_rows) and len(complete_labels) == len(label_rows)
    visual_status = "REVIEWED" if visually_complete else (
        "UNKNOWN_NO_LABELS" if not label_rows
        else "UNKNOWN_STALE_LABELS" if stale_label_count
        else "UNKNOWN"
    )
    delivery_summary = rebuilt_delivery["summary"]
    structural_pass = not (
        entry.get("error")
        or baseline.get("text_decrease")
        or baseline.get("dangling_fulltext_targets")
        or baseline.get("missing_manifest_assets")
        or baseline.get("missing_manifest_renders")
        or delivery_summary["delivery_defects"]
        or delivery_summary["unresolved_reservations"]
    )
    visual_pass = visual_status == "REVIEWED"
    acceptance_blocked_by = [
        reason for reason, blocker in (
            ("structural_delivery_failure", not structural_pass),
            ("human_visual_review_incomplete", not visual_pass),
        ) if blocker
    ]
    case_result = {
        "key": key,
        "source_provenance": source_provenance,
        "source_pdf_sha256": observed_prov.get("fingerprint"),
        "snapshot_fingerprint": snapshot["fingerprint"],
        "evidence_fingerprints": evidence_fingerprints,
        "rebuilt_delivery": rebuilt_delivery,
        "visual_review_status": visual_status,
        "visual_label_counts": {
            "total": len(label_rows),
            "snapshot_bound": len(bound_label_rows),
            "reviewed": len(complete_labels),
            "unreviewed": len(label_rows) - len(complete_labels),
            "stale": stale_label_count,
        },
        # Structural delivery and human visual acceptance are separate verdicts: a clean
        # rebuild nobody has looked at is not acceptance.
        "structural_pass": structural_pass,
        "visual_pass": visual_pass,
        "accepted": False,
        "acceptance_blocked_by": acceptance_blocked_by,
        "figures": len(replay_figures),
        "hold_figures": len(holds),
        "holds": holds,
        "reservation_status_counts": reservation_status_counts,
        "structural": baseline,
    }
    return {
        "key": key, "entry": entry, "baseline": baseline, "case": case_result,
        "out_dir": str(kdir), "snapshot_dir": str(snapshot_dir), "snapshot": snapshot,
        "replay_figures": replay_figures,
        "bound_labels": bound_label_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", default=str(VAULT_DEFAULT))
    parser.add_argument("--ocr-root", default="")
    parser.add_argument("--keys", nargs="*", default=[])
    parser.add_argument("--set", dest="set_name", default="")
    parser.add_argument("--out", default="", help="output root (default docs/evidence/figure-quality/<set>)")
    parser.add_argument("--score", action="store_true", help="scoring mode: read labels and previous result")
    parser.add_argument("--previous", default="", help="previous result JSON for diff")
    parser.add_argument("--result-out", default="", help="write result JSON")
    parser.add_argument("--source-manifest", default="", help="per-key OCR source PDF overrides")
    args = parser.parse_args()
    source_overrides = load_source_overrides(args.source_manifest)

    vault = Path(args.vault)
    ocr_root = Path(args.ocr_root) if args.ocr_root else vault / "System" / "PaperForge" / "ocr"

    keys = list(args.keys)
    if args.set_name:
        keys = keys + load_set(args.set_name)
    keys = sorted(set(keys))

    set_name = args.set_name or "adhoc"
    out_root = Path(args.out) if args.out else (OUT_ROOT / set_name)
    out_root.mkdir(parents=True, exist_ok=True)

    cases = []
    runs = {}
    for key in keys:
        r = run_key(vault, ocr_root, key, out_root, source_override=source_overrides.get(key))
        runs[key] = r
        cases.append(r["case"])

    result = {
        "set": set_name,
        "keys": keys,
        "cases": cases,
        "totals": {
            "papers": len(keys),
            "structural_pass": sum(
                1 for c in cases if c.get("structural_pass") and c.get("status") != "SOURCE_MISMATCH"
            ),
            "structural_fail": sum(
                1 for c in cases if not c.get("structural_pass") and c.get("status") != "SOURCE_MISMATCH"
            ),
            "visual_pass": sum(1 for c in cases if c.get("visual_pass")),
            "accepted": sum(1 for c in cases if c.get("accepted")),
            "source_mismatches": sum(
                1 for c in cases if c.get("status") == "SOURCE_MISMATCH"
            ),
        },
    }

    # Score untouched agent labels and manual findings as separate metric sets.
    findings_path = out_root / "manual_findings.jsonl"
    manual_findings = (
        [json.loads(line) for line in findings_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if findings_path.is_file() else []
    )
    score_summary = {}
    for key in keys:
        run = runs[key]
        snapshot = run.get("snapshot") or {}
        case = run.get("case", {})
        delivery = case.get("rebuilt_delivery", {})
        source_sha = case.get("source_pdf_sha256")
        labels = run.get("bound_labels", [])
        replay = {"figures": run.get("replay_figures", [])}
        key_findings = [finding for finding in manual_findings if finding.get("key") == key]
        bound_findings = [
            finding for finding in key_findings
            if snapshot and _finding_matches_snapshot(finding, snapshot, source_sha, delivery)
        ]
        score_summary[key] = score_labels(
            labels, replay, bound_findings, key,
            snapshot_fingerprint=snapshot.get("fingerprint"),
        )
        score_summary[key]["stale_labels"] = case.get("visual_label_counts", {}).get("stale", 0)
        score_summary[key]["stale_manual_findings"] = len(key_findings) - len(bound_findings)

    result["scores"] = score_summary

    result["visual_review"] = {
        "papers_reviewed": sum(case.get("visual_review_status") == "REVIEWED" for case in cases),
        "papers_unknown": sum(case.get("visual_review_status") != "REVIEWED" for case in cases),
        "labels_total": sum((case.get("visual_label_counts") or {}).get("total", 0) for case in cases),
        "labels_snapshot_bound": sum(
            (case.get("visual_label_counts") or {}).get("snapshot_bound", 0) for case in cases
        ),
        "labels_reviewed": sum(
            (case.get("visual_label_counts") or {}).get("reviewed", 0) for case in cases
        ),
        "stale_labels": sum(
            (case.get("visual_label_counts") or {}).get("stale", 0) for case in cases
        ),
    }

    if args.previous:
        try:
            prev = json.loads(Path(args.previous).read_text(encoding="utf-8"))
            result["diff"] = diff_results(prev, result)
        except Exception as exc:  # noqa: BLE001
            result["diff_error"] = f"{type(exc).__name__}: {exc}"

    out_path = Path(args.result_out) if args.result_out else (out_root / "result.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result["totals"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
