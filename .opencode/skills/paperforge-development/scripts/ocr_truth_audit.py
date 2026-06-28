from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def _find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() or (candidate / ".git").exists():
            return candidate
    raise RuntimeError(f"Could not locate repo root from {start}")


_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _find_repo_root(_THIS_FILE)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from paperforge.worker.ocr_artifacts import artifact_paths_for_root  # noqa: E402
from paperforge.worker.ocr_structural_gate import build_verified_reference_zone_from_artifacts  # noqa: E402
from scripts.dev.ocr_rebuild_paper import rebuild_paper as rebuild_from_raw  # noqa: E402
import fitz  # noqa: E402
from PIL import Image  # noqa: E402


DEFAULT_OUTPUT_ROOT = _REPO_ROOT / "audit"
HOLD_THRESHOLD = 2
UNKNOWN_THRESHOLD = 2
NON_RENDER_ROLES = {
    "figure_caption",
    "figure_inner_text",
    "frontmatter_noise",
    "abstract_heading",
    "abstract_body",
    "table_html",
    "table_caption_candidate",
}
REFERENCE_ALLOWED_ROLES = {"reference_heading", "reference_item"}
_ROLE_COLORS = {
    "paper_title": (0.0, 0.0, 0.6),
    "authors": (0.1, 0.3, 0.75),
    "affiliation": (0.2, 0.5, 0.7),
    "frontmatter_support": (0.4, 0.65, 0.85),
    "frontmatter_noise": (0.55, 0.65, 0.75),
    "abstract_heading": (0.45, 0.0, 0.65),
    "abstract_body": (0.55, 0.3, 0.7),
    "section_heading": (0.85, 0.2, 0.1),
    "subsection_heading": (0.9, 0.4, 0.15),
    "sub_subsection_heading": (0.95, 0.55, 0.25),
    "body_paragraph": (0.0, 0.6, 0.3),
    "reference_heading": (0.75, 0.05, 0.1),
    "reference_item": (0.7, 0.2, 0.2),
    "backmatter_heading": (0.5, 0.15, 0.45),
    "backmatter_boundary_candidate": (0.4, 0.35, 0.45),
    "backmatter_body": (0.55, 0.3, 0.5),
    "media_asset": (0.95, 0.65, 0.05),
    "figure_caption": (0.85, 0.55, 0.0),
    "figure_caption_candidate": (0.9, 0.6, 0.1),
    "figure_inner_text": (0.9, 0.65, 0.3),
    "table_caption": (0.75, 0.55, 0.05),
    "table_caption_candidate": (0.8, 0.6, 0.2),
    "structured_insert": (0.0, 0.55, 0.55),
    "structured_insert_candidate": (0.2, 0.65, 0.65),
    "non_body_insert": (0.1, 0.45, 0.5),
    "noise": (0.35, 0.35, 0.35),
    "footnote": (0.45, 0.45, 0.5),
    "unknown_structural": (0.6, 0.6, 0.6),
}


def _classify_category(block: dict) -> str:
    role = str(block.get("role", ""))
    zone = str(block.get("zone", ""))
    text = _normalize_text(_block_text(block)).lower()
    raw_label = str(block.get("raw_label", ""))
    if role in {"paper_title", "authors", "frontmatter_support", "frontmatter_noise", "affiliation"}:
        return "frontmatter"
    if zone == "frontmatter_main_zone" or zone == "frontmatter_side_zone":
        return "frontmatter"
    if role in {"reference_heading", "reference_item"} or zone == "reference_zone":
        return "reference"
    if zone in {"tail_nonref_hold_zone", "post_reference_backmatter_zone"} or role.startswith("backmatter"):
        return "backmatter"
    if role in {"figure_asset", "media_asset", "figure_caption", "figure_caption_candidate", "figure_inner_text",
                "table_caption", "table_caption_candidate", "table_html"}:
        return "object_caption"
    if raw_label in {"image", "chart", "figure", "table"}:
        return "object_caption"
    if role in {"section_heading", "subsection_heading", "sub_subsection_heading"}:
        return "body"
    if role in {"body_paragraph", "abstract_body", "abstract_heading"}:
        return "body"
    if role == "unknown_structural" or str(block.get("role_verification_status", "")) == "HOLD":
        return "unknown_hold"
    if zone == "body_zone":
        return "body"
    if text in {"references", "bibliography"}:
        return "reference"
    if role in {"noise", "footer", "header"}:
        return "unknown_hold"
    return "unknown_hold"


STRICT_REQUIRED_FIELDS = [
    "block_id",
    "page",
    "review_status",
    "truth_role",
    "truth_zone",
    "truth_reference_membership",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build OCR truth-audit helper outputs for one or more papers.")
    parser.add_argument("paper_keys", nargs="*", help="Explicit paper keys to audit")
    parser.add_argument("--mode", choices=("strict", "high-risk"), default="high-risk")
    parser.add_argument(
        "--current-paper",
        action="store_true",
        help="Use PAPERFORGE_CURRENT_PAPER_KEY/CURRENT_PAPER_KEY from the environment when no explicit key is provided",
    )
    parser.add_argument("--refresh-artifacts", action="store_true", help="Rebuild derived artifacts and refresh annotated pages")
    parser.add_argument("--include-pages", nargs="*", type=int, help="Restrict the audit to specific pages")
    parser.add_argument("--focus", nargs="*", default=[], help="Optional focus labels for downstream review")
    parser.add_argument(
        "--source-root",
        default=None,
        help="OCR root directory outside the repo, e.g. D:/.../System/PaperForge/ocr",
    )
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Audit output root directory")
    return parser


def _load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _write_json(path: Path, payload: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256(path: Path) -> str:
    if not path.exists():
        return "missing"
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _mtime(path: Path) -> float | None:
    return path.stat().st_mtime if path.exists() else None


def _resolve_keys(args: argparse.Namespace) -> list[str]:
    keys = [str(k).strip() for k in args.paper_keys if str(k).strip()]
    if keys:
        return keys
    if args.current_paper:
        env_key = os.environ.get("PAPERFORGE_CURRENT_PAPER_KEY") or os.environ.get("CURRENT_PAPER_KEY")
        if env_key:
            return [env_key.strip()]
    raise SystemExit("No paper key supplied. Pass a key explicitly or use --current-paper with PAPERFORGE_CURRENT_PAPER_KEY.")


def _resolve_ocr_root(raw: str | None) -> Path:
    candidate = raw or os.environ.get("PAPERFORGE_OCR_ROOT") or os.environ.get("PAPERFORGE_REAL_OCR_ROOT")
    if not candidate:
        raise SystemExit(
            "No OCR root supplied. Pass --source-root /path/to/System/PaperForge/ocr or set PAPERFORGE_OCR_ROOT."
        )
    path = Path(candidate)
    if not path.exists():
        raise SystemExit(f"OCR root not found: {path}")
    return path


def _resolve_vault_root(ocr_root: Path) -> Path:
    current = ocr_root.resolve()
    if current.name != "ocr":
        raise RuntimeError(f"Expected OCR root to end with 'ocr', got: {current}")
    paperforge_dir = current.parent
    system_dir = paperforge_dir.parent
    return system_dir.parent if system_dir.name == "System" else system_dir


def _block_text(block: dict) -> str:
    return str(block.get("text") or block.get("block_content") or "")


def _block_bbox(block: dict) -> list[float]:
    bbox = block.get("bbox") or block.get("block_bbox") or [0, 0, 0, 0]
    return [float(v) for v in bbox]


def _block_x0(block: dict) -> float:
    return _block_bbox(block)[0]


def _block_y0(block: dict) -> float:
    return _block_bbox(block)[1]


def _block_page(block: dict) -> int:
    return int(block.get("page", 0) or 0)


def _block_id(block: dict) -> str:
    page = _block_page(block)
    raw = block.get("block_id")
    return f"p{page}:{raw}" if raw is not None else f"p{page}:unknown"


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _safe_rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _artifact_dict(doc_structure: Any) -> dict:
    if doc_structure is None:
        return {}
    if isinstance(doc_structure, dict):
        return doc_structure
    if is_dataclass(doc_structure):
        return asdict(doc_structure)
    if hasattr(doc_structure, "_asdict"):
        return doc_structure._asdict()
    return {}


def _load_block_trace_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _write_block_trace_csv(path: Path, blocks: list[dict]) -> None:
    field_names = [
        "page",
        "block_id",
        "raw_label",
        "content_preview",
        "bbox",
        "role",
        "role_confidence",
        "evidence",
        "seed_role",
        "seed_confidence",
        "zone",
        "style_family",
        "marker_type",
        "render_default",
        "index_default",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=field_names)
        writer.writeheader()
        for block in blocks:
            marker_sig = block.get("marker_signature") or {}
            writer.writerow(
                {
                    "page": block.get("page", ""),
                    "block_id": block.get("block_id", ""),
                    "raw_label": block.get("raw_label", ""),
                    "content_preview": _block_text(block)[:200],
                    "bbox": json.dumps(_block_bbox(block)),
                    "role": block.get("role", ""),
                    "role_confidence": block.get("role_confidence", ""),
                    "evidence": json.dumps(block.get("evidence", [])) if block.get("evidence") else "",
                    "seed_role": block.get("seed_role", ""),
                    "seed_confidence": block.get("seed_confidence", ""),
                    "zone": block.get("zone", ""),
                    "style_family": block.get("style_family", ""),
                    "marker_type": marker_sig.get("type", ""),
                    "render_default": block.get("render_default", True),
                    "index_default": block.get("index_default", True),
                }
            )


def _refresh_artifacts(ocr_root: Path, key: str) -> dict:
    return rebuild_from_raw(ocr_root, key, trace=True, trace_only=False)


def _resolve_audit_source_pdf(ocr_root: Path, key: str) -> Path:
    paper_root = ocr_root / key
    source_pdf = paper_root / "source.pdf"
    if source_pdf.exists():
        return source_pdf
    meta_path = paper_root / "raw" / "source_metadata.json"
    if meta_path.exists():
        meta = _load_json(meta_path, {}) or {}
        src = meta.get("source_pdf")
        if src and Path(src).exists():
            return Path(src)
    raise FileNotFoundError(f"Could not resolve source PDF for {key}")


def _ocr_page_image_path(ocr_root: Path, key: str, page_num: int) -> Path:
    page_dir = ocr_root / key / "pages"
    for suffix in ("png", "jpg", "jpeg"):
        candidate = page_dir / f"page_{page_num:03d}.{suffix}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Missing OCR page image for {key} page {page_num}")


def _render_audit_visuals(key: str, blocks: list[dict], ocr_root: Path, audit_dir: Path) -> list[str]:
    pdf_path = _resolve_audit_source_pdf(ocr_root, key)
    pages_dir = audit_dir / "annotated_pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    by_page: dict[int, list[tuple[int, dict]]] = {}
    for idx, block in enumerate(blocks):
        page = _block_page(block)
        if page <= 0:
            continue
        by_page.setdefault(page, []).append((idx, block))

    doc = fitz.open(str(pdf_path))
    rendered: list[str] = []
    for page_num in sorted(by_page):
        entries = by_page[page_num]
        pdf_page = doc.load_page(page_num - 1)
        pdf_w, pdf_h = pdf_page.rect.width, pdf_page.rect.height
        img_path = _ocr_page_image_path(ocr_root, key, page_num)
        img_w, img_h = Image.open(img_path).size
        x_scale = pdf_w / img_w
        y_scale = pdf_h / img_h

        def _scale_bbox(bbox: list[float]) -> fitz.Rect:
            return fitz.Rect(bbox[0] * x_scale, bbox[1] * y_scale, bbox[2] * x_scale, bbox[3] * y_scale)

        _render_overview_page(pdf_page, page_num, entries, pages_dir, _scale_bbox)
        _write_page_index(page_num, entries, pages_dir)
        rendered.append(f"page_{page_num:03d}.png")
    doc.close()
    return rendered


def _render_overview_page(pdf_page, page_num: int, entries: list[tuple[int, dict]], out_dir: Path, scale_bbox) -> None:
    shape = pdf_page.new_shape()
    for idx, block in entries:
        rect = scale_bbox(_block_bbox(block))
        role = str(block.get("role", ""))
        color = _ROLE_COLORS.get(role, (0.6, 0.6, 0.6))
        shape.draw_rect(rect)
        shape.finish(color=color, width=0.6)
        label = str(block.get("block_id", ""))
        if label:
            pdf_page.insert_text(fitz.Point(rect.x0, max(6, rect.y0 - 1)), label, fontsize=5.5, color=color, overlay=True)
    shape.commit(overlay=True)
    pix = pdf_page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
    pix.save(str(out_dir / f"page_{page_num:03d}.png"))


def _write_page_index(page_num: int, entries: list[tuple[int, dict]], out_dir: Path) -> None:
    rows = []
    for idx, block in entries:
        rows.append({
            "label": str(block.get("block_id", "")),
            "block_id": _block_id(block),
            "page": page_num,
            "role": block.get("role", ""),
            "zone": block.get("zone", ""),
            "category": _classify_category(block),
            "text_preview": _normalize_text(_block_text(block))[:120],
            "bbox": _block_bbox(block),
        })
    _write_json(out_dir / f"page_{page_num:03d}_index.json", rows)


def _artifact_paths(ocr_root: Path, key: str) -> dict[str, Path]:
    artifacts = artifact_paths_for_root(ocr_root, key)
    paper_root = artifacts.paper_root
    structure_dir = paper_root / "structure"
    metadata_dir = paper_root / "metadata"
    render_dir = paper_root / "render"
    return {
        "paper_root": paper_root,
        "result_json": artifacts.result_json,
        "meta_json": artifacts.meta_json,
        "blocks_raw": artifacts.blocks_raw,
        "blocks_structured": artifacts.blocks_structured,
        "source_metadata": artifacts.source_metadata,
        "compat_fulltext": artifacts.compat_fulltext,
        "render_fulltext": render_dir / "fulltext.md",
        "document_structure": structure_dir / "document_structure.json",
        "figure_inventory": structure_dir / "figure_inventory.json",
        "table_inventory": structure_dir / "table_inventory.json",
        "reader_figures": structure_dir / "reader_figures.json",
        "resolved_metadata": metadata_dir / "resolved_metadata.json",
        "decision_log": paper_root / "health" / "decision_log.jsonl",
    }


def _build_fingerprint(paths: dict[str, Path], block_trace: Path, annotated_dir: Path) -> dict:
    annotated_files = sorted(annotated_dir.glob("page_*.png")) if annotated_dir.exists() else []
    return {
        "result_json_hash": _sha256(paths["result_json"]),
        "meta_json_hash": _sha256(paths["meta_json"]),
        "blocks_raw_hash": _sha256(paths["blocks_raw"]),
        "structured_blocks_hash": _sha256(paths["blocks_structured"]),
        "document_structure_hash": _sha256(paths["document_structure"]),
        "figure_inventory_hash": _sha256(paths["figure_inventory"]),
        "table_inventory_hash": _sha256(paths["table_inventory"]),
        "reader_figures_hash": _sha256(paths["reader_figures"]),
        "resolved_metadata_hash": _sha256(paths["resolved_metadata"]),
        "fulltext_hash": _sha256(paths["compat_fulltext"]),
        "block_trace_hash": _sha256(block_trace),
        "annotated_pages": {name.name: _sha256(name) for name in annotated_files},
    }


def _detect_stale(paths: dict[str, Path], block_trace: Path, annotated_dir: Path) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    mismatches: list[str] = []
    required = {
        "result_json": paths["result_json"],
        "meta_json": paths["meta_json"],
        "blocks_raw": paths["blocks_raw"],
        "blocks_structured": paths["blocks_structured"],
        "document_structure": paths["document_structure"],
        "figure_inventory": paths["figure_inventory"],
        "table_inventory": paths["table_inventory"],
        "reader_figures": paths["reader_figures"],
        "resolved_metadata": paths["resolved_metadata"],
        "fulltext": paths["compat_fulltext"],
        "block_trace": block_trace,
    }
    for name, path in required.items():
        if not path.exists():
            missing.append(name)

    if missing:
        return missing, mismatches

    def older(target: str, source: str) -> None:
        if _mtime(required[target]) is not None and _mtime(required[source]) is not None:
            if _mtime(required[target]) < _mtime(required[source]):
                mismatches.append(f"{target} older than {source}")

    older("blocks_structured", "blocks_raw")
    older("document_structure", "blocks_structured")
    older("figure_inventory", "blocks_structured")
    older("table_inventory", "blocks_structured")
    older("reader_figures", "figure_inventory")
    older("resolved_metadata", "blocks_structured")
    older("fulltext", "blocks_structured")
    older("block_trace", "blocks_structured")

    annotated_pages = sorted(annotated_dir.glob("page_*.png")) if annotated_dir.exists() else []
    if not annotated_pages:
        missing.append("annotated_pages")
    elif _mtime(max(annotated_pages, key=lambda p: p.stat().st_mtime)) < _mtime(block_trace):
        mismatches.append("annotated_pages older than block_trace")

    return missing, mismatches


def _page_column(block: dict) -> int:
    bbox = _block_bbox(block)
    width = float(block.get("page_width", 0) or 0)
    if width and bbox[0] >= width * 0.45:
        return 2
    return 1


def _summarize_blocks(blocks: list[dict], mode: str) -> dict:
    pages = sorted({_block_page(b) for b in blocks if _block_page(b) > 0})
    by_page: dict[int, list[dict]] = {}
    for block in blocks:
        by_page.setdefault(_block_page(block), []).append(block)
    return {
        "mode": mode,
        "total_blocks": len(blocks),
        "pages": pages,
        "per_page_counts": {str(page): len(by_page.get(page, [])) for page in pages},
        "blocks": [
            {
                "block_id": _block_id(block),
                "page": _block_page(block),
                "raw_label": block.get("raw_label", ""),
                "role": block.get("role", ""),
                "zone": block.get("zone", ""),
                "bbox": _block_bbox(block),
                "review_status": "pending",
                "truth_role": None,
                "truth_zone": None,
                "truth_order_after": None,
                "truth_order_before": None,
                "truth_object_id": None,
                "truth_reference_membership": None,
            }
            for block in blocks
        ],
    }


def _build_page_risk_summary(
    blocks: list[dict],
    figure_inventory: dict,
    table_inventory: dict,
    reader_figures: dict,
    include_pages: list[int] | None,
) -> dict:
    by_page: dict[int, list[dict]] = {}
    for block in blocks:
        page = _block_page(block)
        if page <= 0:
            continue
        by_page.setdefault(page, []).append(block)

    normalized_reader = reader_figures.get("normalized_inputs", {}) if isinstance(reader_figures, dict) else {}
    matched_figures = normalized_reader.get("matched_figures", []) if isinstance(normalized_reader, dict) else []
    ambiguous_figures = normalized_reader.get("ambiguous_figures", []) if isinstance(normalized_reader, dict) else []
    reader_items = reader_figures.get("reader_figures", []) if isinstance(reader_figures, dict) else []

    summaries: list[dict] = []
    for page, page_blocks in sorted(by_page.items()):
        roles = {str(b.get("role", "")) for b in page_blocks}
        body_count = sum(1 for b in page_blocks if b.get("role") == "body_paragraph")
        ref_count = sum(1 for b in page_blocks if b.get("role") == "reference_item")
        tail_count = sum(1 for b in page_blocks if "tail" in str(b.get("zone", "")) or str(b.get("role", "")).startswith("backmatter"))
        asset_count = sum(1 for b in page_blocks if b.get("role") in {"figure_asset", "media_asset"})
        tableish_count = sum(1 for b in page_blocks if "table" in str(b.get("role", "")) or (b.get("raw_label") == "table"))
        caption_count = sum(1 for b in page_blocks if "caption" in str(b.get("role", "")) or str(b.get("seed_role", "")).endswith("caption"))
        hold_count = sum(1 for b in page_blocks if str(b.get("role_verification_status", "")) == "HOLD")
        unknown_count = sum(1 for b in page_blocks if str(b.get("role", "")) == "unknown_structural")

        page_matched_figures = [item for item in matched_figures if int(item.get("page", 0) or 0) == page]
        page_ambiguous = [item for item in ambiguous_figures if int(item.get("page", 0) or 0) == page]
        page_reader_figures = [item for item in reader_items if int(item.get("page", 0) or 0) == page]

        score = 0
        reasons: list[str] = []
        targets: list[str] = []
        if page == 1:
            score += 5
            reasons.append("frontmatter_page")
            targets.append("frontmatter")
        if "reference_heading" in roles:
            score += 5
            reasons.append("reference_heading_present")
            targets.append("reference_span")
        if body_count and ref_count:
            score += 4
            reasons.append("mixed_body_reference")
            targets.extend(["reference_span", "same_page_boundary"])
        if body_count and (ref_count or tail_count):
            score += 4
            reasons.append("same_page_boundary")
            targets.extend(["same_page_boundary", "reading_order"])
        if asset_count + tableish_count >= 2:
            score += 4
            reasons.append("multi_asset_page")
            targets.append("object_ownership")
        if caption_count and (asset_count + tableish_count) and caption_count != asset_count + tableish_count:
            score += 3
            reasons.append("caption_asset_mismatch")
            targets.append("object_ownership")
        if (asset_count and not page_reader_figures) or page_ambiguous:
            score += 3
            reasons.append("reader_object_gap")
            targets.append("object_ownership")
        if hold_count >= HOLD_THRESHOLD:
            score += 2
            reasons.append("hold_threshold")
            targets.append("reading_order")
        if unknown_count >= UNKNOWN_THRESHOLD:
            score += 2
            reasons.append("unknown_structural_threshold")
            targets.append("body_flow")

        summaries.append(
            {
                "page": page,
                "risk_score": score,
                "risk_reasons": reasons,
                "recommended_audit_targets": sorted(set(targets)),
                "counts": {
                    "body_paragraph": body_count,
                    "reference_item": ref_count,
                    "tail_like": tail_count,
                    "media_assets": asset_count,
                    "table_like": tableish_count,
                    "captions": caption_count,
                    "hold": hold_count,
                    "unknown_structural": unknown_count,
                    "matched_figures": len(page_matched_figures),
                    "ambiguous_figures": len(page_ambiguous),
                },
            }
        )

    selected_pages = include_pages if include_pages else [row["page"] for row in summaries if row["risk_score"] > 0]
    if not selected_pages and summaries:
        selected_pages = [summaries[0]["page"]]
    return {"pages": summaries, "selected_pages": selected_pages}


def _is_high_risk_block(block: dict, selected_pages: set[int]) -> tuple[bool, list[str]]:
    page = _block_page(block)
    if page not in selected_pages:
        return False, []
    role = str(block.get("role", ""))
    zone = str(block.get("zone", ""))
    raw_label = str(block.get("raw_label", ""))
    text = _normalize_text(_block_text(block)).lower()
    reasons: list[str] = []
    if page == 1 or role in {"paper_title", "authors", "frontmatter_support", "frontmatter_noise", "affiliation"}:
        reasons.append("frontmatter")
    if role in {"reference_heading", "reference_item"} or zone == "reference_zone":
        reasons.append("reference_span")
    if zone in {"tail_nonref_hold_zone", "post_reference_backmatter_zone"} or role.startswith("backmatter"):
        reasons.append("backmatter")
    if role in {"figure_asset", "media_asset", "figure_caption_candidate", "table_caption_candidate", "table_html"}:
        reasons.append("object_ownership")
    if raw_label in {"image", "chart", "figure", "table"}:
        reasons.append("object_ownership")
    if str(block.get("role_verification_status", "")) == "HOLD" or role == "unknown_structural":
        reasons.append("needs_resolution")
    if ("reference" in text or text in {"references", "bibliography"}) and zone != "reference_zone":
        reasons.append("same_page_boundary")
    if role == "body_paragraph" and any(tok in text for tok in ("acknowledg", "keywords", "conflict of interest", "funding")):
        reasons.append("same_page_boundary")
    return bool(reasons), sorted(set(reasons))


def _build_audit_scope(mode: str, blocks: list[dict], page_risk_summary: dict, include_pages: list[int] | None) -> dict:
    selected_pages = _selected_pages(mode, page_risk_summary, blocks, include_pages)
    page_set = set(selected_pages)
    required_blocks: list[dict] = []
    if mode == "strict":
        for block in blocks:
            required_blocks.append(
                {
                    "block_id": _block_id(block),
                    "page": _block_page(block),
                    "required_reason": ["strict_all_blocks"],
                    "minimum_fields": STRICT_REQUIRED_FIELDS,
                }
            )
    else:
        for block in blocks:
            is_required, reasons = _is_high_risk_block(block, page_set)
            if is_required:
                required_blocks.append(
                    {
                        "block_id": _block_id(block),
                        "page": _block_page(block),
                        "required_reason": reasons,
                        "minimum_fields": STRICT_REQUIRED_FIELDS,
                    }
                )

    per_page: dict[int, int] = {}
    for item in required_blocks:
        per_page[item["page"]] = per_page.get(item["page"], 0) + 1
    return {
        "mode": mode,
        "selected_pages": selected_pages,
        "required_block_ids": [item["block_id"] for item in required_blocks],
        "required_blocks": required_blocks,
        "selected_page_requirements": [
            {
                "page": page,
                "must_review_page": True,
                "required_block_count": per_page.get(page, 0),
            }
            for page in selected_pages
        ],
    }


def _derive_reference_zone(blocks: list[dict], doc_structure: dict) -> dict:
    direct = doc_structure.get("reference_zone") if isinstance(doc_structure, dict) else None
    if isinstance(direct, dict) and (direct.get("heading_block_id") or direct.get("item_block_ids")):
        return direct

    region_bus = doc_structure.get("region_bus") or {}
    ref_zone = region_bus.get("reference_zone") if isinstance(region_bus, dict) else {}
    zone_ids = set((ref_zone or {}).get("block_ids", [])) if isinstance(ref_zone, dict) else set()
    reference_family_anchor = doc_structure.get("reference_family_anchor") or {}
    tail_spread_dict = {}
    if doc_structure.get("tail_boundary_score"):
        tail_spread_dict = {"reference_end_before_block_id": None}
    return build_verified_reference_zone_from_artifacts(
        blocks,
        {
            "reference_family_anchor": reference_family_anchor,
            "region_bus": {"reference_zone_ids": zone_ids},
            "tail_spread": tail_spread_dict,
        },
    )


def _build_reference_span_audit(blocks: list[dict], verified_zone: dict) -> tuple[dict, list[dict]]:
    heading_id = verified_zone.get("heading_block_id")
    item_ids = list(verified_zone.get("item_block_ids", []))
    allowed_ids = {str(x) for x in item_ids}
    if heading_id is not None:
        allowed_ids.add(str(heading_id))

    indexed = [{"index": idx, "block": block, "artifact_id": _block_id(block), "raw_id": str(block.get("block_id"))} for idx, block in enumerate(blocks)]
    allowed_rows = [row for row in indexed if row["raw_id"] in allowed_ids or row["artifact_id"] in allowed_ids]
    allowed_rows.sort(key=lambda row: row["index"])

    if not allowed_rows:
        return {
            "reference_span": {
                "status": "HOLD",
                "span_id": None,
                "start": None,
                "end": None,
                "ordered_block_ids": [],
                "inside_block_ids": [],
                "explicitly_outside_nearby_block_ids": [],
                "intrusion_candidates": [],
            }
        }, []

    min_idx = allowed_rows[0]["index"]
    max_idx = allowed_rows[-1]["index"]
    intrusion_candidates: list[dict] = []
    for row in indexed[min_idx : max_idx + 1]:
        bid = row["raw_id"] if row["raw_id"] != "None" else row["artifact_id"]
        role = str(row["block"].get("role", ""))
        if bid in allowed_ids:
            continue
        if not _normalize_text(_block_text(row["block"])):
            continue
        intrusion_candidates.append(
            {
                "block_id": row["artifact_id"],
                "page": _block_page(row["block"]),
                "role": role,
                "zone": row["block"].get("zone", ""),
                "reason": "logical_order_between_reference_members",
            }
        )

    first = allowed_rows[0]["block"]
    last = allowed_rows[-1]["block"]
    outside = []
    if min_idx > 0:
        outside.append(_block_id(indexed[min_idx - 1]["block"]))
    if max_idx + 1 < len(indexed):
        outside.append(_block_id(indexed[max_idx + 1]["block"]))

    audit = {
        "reference_span": {
            "status": "ACCEPT" if heading_id and item_ids else "HOLD",
            "span_id": "refspan_001" if item_ids else None,
            "start": {
                "page": _block_page(first),
                "column": _page_column(first),
                "y": _block_y0(first),
                "block_id": _block_id(first),
            },
            "end": {
                "page": _block_page(last),
                "column": _page_column(last),
                "y": _block_y0(last),
                "block_id": _block_id(last),
            },
            "heading_block_id": heading_id,
            "ordered_block_ids": [_block_id(row["block"]) for row in allowed_rows],
            "inside_block_ids": [_block_id(row["block"]) for row in allowed_rows],
            "explicitly_outside_nearby_block_ids": outside,
            "intrusion_candidates": intrusion_candidates,
        }
    }
    return audit, intrusion_candidates


def _build_object_ownership_summary(figure_inventory: dict, table_inventory: dict) -> dict:
    summary = {
        "figures": {
            "matched_count": len(figure_inventory.get("matched_figures", [])),
            "ambiguous_count": len(figure_inventory.get("ambiguous_figures", [])),
            "unresolved_cluster_count": len(figure_inventory.get("unresolved_clusters", [])),
            "unmatched_asset_count": len(figure_inventory.get("unmatched_assets", [])),
            "matched": [],
            "ambiguous": [],
            "unresolved": [],
        },
        "tables": {
            "matched_count": len(table_inventory.get("matched_tables", [])),
            "ambiguous_count": len(table_inventory.get("ambiguous_tables", [])),
            "unmatched_asset_count": len(table_inventory.get("unmatched_assets", [])),
            "matched": [],
            "ambiguous": [],
        },
    }
    for item in figure_inventory.get("matched_figures", []):
        summary["figures"]["matched"].append(
            {
                "figure_number": item.get("figure_number"),
                "legend_block_id": item.get("legend_block_id"),
                "asset_block_ids": [asset.get("block_id") for asset in item.get("matched_assets", [])],
                "page": item.get("page"),
                "match_type": item.get("match_type") or item.get("decision"),
            }
        )
    for item in figure_inventory.get("ambiguous_figures", []):
        summary["figures"]["ambiguous"].append(
            {
                "figure_number": item.get("figure_number"),
                "legend_block_id": item.get("legend_block_id"),
                "asset_block_ids": [asset.get("block_id") for asset in item.get("matched_assets", [])],
                "candidate_asset_ids": item.get("candidate_asset_ids", []),
                "page": item.get("page"),
            }
        )
    for item in figure_inventory.get("unresolved_clusters", []):
        summary["figures"]["unresolved"].append(
            {
                "figure_number": item.get("figure_number"),
                "asset_block_ids": item.get("asset_block_ids", []),
                "page": item.get("page"),
            }
        )
    for item in table_inventory.get("matched_tables", []):
        summary["tables"]["matched"].append(
            {
                "table_number": item.get("table_number"),
                "caption_block_id": item.get("caption_block_id"),
                "asset_block_ids": [asset.get("block_id") for asset in item.get("matched_assets", [])],
                "page": item.get("page"),
            }
        )
    for item in table_inventory.get("ambiguous_tables", []):
        summary["tables"]["ambiguous"].append(
            {
                "table_number": item.get("table_number"),
                "caption_block_id": item.get("caption_block_id"),
                "asset_block_ids": [asset.get("block_id") for asset in item.get("matched_assets", [])],
                "page": item.get("page"),
            }
        )
    return summary


def _build_fulltext_mapping(blocks: list[dict], fulltext: str) -> dict:
    normalized_fulltext = _normalize_text(fulltext)
    rows = []
    found_count = 0
    for block in blocks:
        text = _normalize_text(_block_text(block))
        if not text or block.get("role") in NON_RENDER_ROLES:
            continue
        snippet = text[:80]
        position = normalized_fulltext.find(snippet) if snippet else -1
        found = position >= 0
        found_count += 1 if found else 0
        rows.append(
            {
                "block_id": _block_id(block),
                "page": _block_page(block),
                "role": block.get("role", ""),
                "zone": block.get("zone", ""),
                "render_default": block.get("render_default", True),
                "snippet": snippet,
                "found_in_fulltext": found,
                "fulltext_offset": position,
            }
        )
    return {
        "mappable_block_count": len(rows),
        "found_count": found_count,
        "missing_count": len(rows) - found_count,
        "rows": rows,
    }


def _selected_pages(mode: str, page_risk_summary: dict, blocks: list[dict], include_pages: list[int] | None) -> list[int]:
    if include_pages:
        return include_pages
    if mode == "strict":
        return sorted({_block_page(block) for block in blocks if _block_page(block) > 0})
    return list(page_risk_summary.get("selected_pages", []))


def _build_findings(
    blocks: list[dict],
    page_risk_summary: dict,
    reference_intrusions: list[dict],
    ownership_summary: dict,
    mapping_summary: dict,
) -> list[dict]:
    findings: list[dict] = []
    for intrusion in reference_intrusions[:20]:
        findings.append(
            {
                "category": "reference_span_error",
                "severity": "critical",
                "block_ids": [intrusion["block_id"]],
                "truth": "block should remain outside the accepted reference span",
                "pipeline_behavior": "block appears inside the logical reference reading-order region",
                "root_cause_hypothesis": intrusion["reason"],
                "evidence": {
                    "annotated_page": f"annotated_pages/page_{intrusion['page']:03d}.png",
                    "artifact": "reference_span_audit.json",
                },
            }
        )

    for page in page_risk_summary.get("pages", []):
        if "frontmatter_page" in page.get("risk_reasons", []) and page.get("counts", {}).get("unknown_structural", 0) >= UNKNOWN_THRESHOLD:
            findings.append(
                {
                    "category": "frontmatter_error",
                    "severity": "major",
                    "block_ids": [],
                    "truth": "page 1 should have clearer frontmatter role resolution",
                    "pipeline_behavior": "frontmatter page retains elevated unknown_structural density",
                    "root_cause_hypothesis": "frontmatter anchor or noise routing weakness",
                    "evidence": {
                        "annotated_page": f"annotated_pages/page_{page['page']:03d}.png",
                        "artifact": "page_risk_summary.json",
                    },
                }
            )
        if "same_page_boundary" in page.get("risk_reasons", []) and page.get("counts", {}).get("reference_item", 0) > 0:
            findings.append(
                {
                    "category": "same_page_boundary_error",
                    "severity": "major",
                    "block_ids": [],
                    "truth": "body/reference/backmatter boundaries should be explainable at block level",
                    "pipeline_behavior": "page contains mixed body/reference/tail signals",
                    "root_cause_hypothesis": "same-page boundary ambiguity",
                    "evidence": {
                        "annotated_page": f"annotated_pages/page_{page['page']:03d}.png",
                        "artifact": "page_risk_summary.json",
                    },
                }
            )

    if ownership_summary["figures"]["ambiguous_count"] or ownership_summary["figures"]["unresolved_cluster_count"]:
        findings.append(
            {
                "category": "object_ownership_error",
                "severity": "major",
                "block_ids": [],
                "truth": "figure/table ownership should map captions and assets coherently",
                "pipeline_behavior": "ambiguous or unresolved object ownership remains in the current artifact set",
                "root_cause_hypothesis": "caption-to-asset grouping ambiguity",
                "evidence": {
                    "annotated_page": None,
                    "artifact": "figure_table_ownership_summary.json",
                },
            }
        )

    if mapping_summary.get("missing_count", 0) > 0:
        findings.append(
            {
                "category": "render_mapping_error",
                "severity": "minor",
                "block_ids": [row["block_id"] for row in mapping_summary.get("rows", []) if not row.get("found_in_fulltext")][:20],
                "truth": "rendered fulltext should be traceable back to source blocks",
                "pipeline_behavior": "some render-default blocks are not easily mapped into the current fulltext output",
                "root_cause_hypothesis": "render omission or snippet mismatch",
                "evidence": {
                    "annotated_page": None,
                    "artifact": "fulltext_block_mapping_summary.json",
                },
            }
        )
    return findings


def _write_report_md(path: Path, payload: dict) -> None:
    lines = [
        f"# OCR Truth Audit Report - {payload['paper_key']}",
        "",
        f"- Mode: `{payload['mode']}`",
        f"- Status: `{payload.get('status', 'READY')}`",
        f"- Reviewed pages: {payload.get('reviewed_pages', [])}",
        f"- Reviewed blocks: {len(payload.get('reviewed_blocks', []))}",
        "",
        "## Findings",
        "",
    ]
    findings = payload.get("findings", [])
    if not findings:
        lines.append("- No heuristic findings emitted. Perform manual truth review.")
    else:
        for finding in findings:
            lines.append(
                f"- `{finding['severity']}` `{finding['category']}`: {finding['pipeline_behavior']}"
            )
    lines.extend(
        [
            "",
            "## Disposition Guidance",
            "",
            "- Use `repair` when the finding reflects a pipeline defect worth fixing now.",
            "- Use `residual` when the finding is real but intentionally deferred.",
            "- Do not rewrite expected truth to make current output look correct.",
        ]
    )
    _write_text(path, "\n".join(lines) + "\n")


def _audit_one_paper(
    ocr_root: Path,
    key: str,
    mode: str,
    refresh_artifacts: bool,
    include_pages: list[int] | None,
    focus: list[str],
    output_root: Path,
) -> int:
    if refresh_artifacts:
        _refresh_artifacts(ocr_root, key)

    audit_dir = output_root / key
    audit_dir.mkdir(parents=True, exist_ok=True)

    paths = _artifact_paths(ocr_root, key)
    if not paths["paper_root"].exists():
        raise SystemExit(f"Paper not found under OCR root: {key}")

    blocks = _load_jsonl(paths["blocks_structured"])
    if not blocks:
        raise SystemExit(f"No structured blocks found for {key}: {paths['blocks_structured']}")

    block_trace_path = audit_dir / "block_trace.csv"
    _write_block_trace_csv(block_trace_path, blocks)
    rendered_pages = _render_audit_visuals(key, blocks, ocr_root, audit_dir)

    missing, mismatches = _detect_stale(paths, block_trace_path, audit_dir / "annotated_pages")
    fingerprint = _build_fingerprint(paths, block_trace_path, audit_dir / "annotated_pages")

    block_coverage = _summarize_blocks(blocks, mode)
    figure_inventory = _load_json(paths["figure_inventory"], {}) or {}
    table_inventory = _load_json(paths["table_inventory"], {}) or {}
    reader_figures = _load_json(paths["reader_figures"], {}) or {}
    doc_structure = _load_json(paths["document_structure"], {}) or {}
    fulltext = ""
    for candidate in (paths["compat_fulltext"], paths["render_fulltext"]):
        if candidate.exists():
            fulltext = candidate.read_text(encoding="utf-8", errors="replace")
            break

    page_risk_summary = _build_page_risk_summary(blocks, figure_inventory, table_inventory, reader_figures, include_pages)
    verified_zone = _derive_reference_zone(blocks, doc_structure)
    reference_span_audit, intrusion_candidates = _build_reference_span_audit(blocks, verified_zone)
    ownership_summary = _build_object_ownership_summary(figure_inventory, table_inventory)
    fulltext_mapping = _build_fulltext_mapping(blocks, fulltext)
    audit_scope = _build_audit_scope(mode, blocks, page_risk_summary, include_pages)

    selected_pages = _selected_pages(mode, page_risk_summary, blocks, include_pages)
    reviewed_blocks = [_block_id(block) for block in blocks if _block_page(block) in selected_pages]

    status = "AUDIT_BLOCKED" if missing or (mode == "strict" and mismatches) else "READY"
    findings = [] if status == "AUDIT_BLOCKED" else _build_findings(
        blocks,
        page_risk_summary,
        intrusion_candidates,
        ownership_summary,
        fulltext_mapping,
    )

    report = {
        "paper_key": key,
        "mode": mode,
        "status": status,
        "focus": focus,
        "artifact_fingerprint": fingerprint,
        "artifact_freshness": {
            "missing": missing,
            "mismatches": mismatches,
            "annotated_pages_rendered": rendered_pages,
        },
        "reviewed_pages": selected_pages,
        "reviewed_blocks": reviewed_blocks,
        "findings": findings,
    }

    _write_json(audit_dir / "audit_report.json", report)
    _write_report_md(audit_dir / "audit_report.md", report)
    _write_json(audit_dir / "audit_scope.json", audit_scope)
    _write_json(audit_dir / "block_coverage_summary.json", block_coverage)
    _write_json(audit_dir / "page_risk_summary.json", page_risk_summary)
    _write_json(audit_dir / "reference_intrusion_candidates.json", {"candidates": intrusion_candidates})
    _write_json(audit_dir / "figure_table_ownership_summary.json", ownership_summary)
    _write_json(audit_dir / "fulltext_block_mapping_summary.json", fulltext_mapping)
    _write_json(audit_dir / "reference_span_audit.json", reference_span_audit)
    return 2 if status == "AUDIT_BLOCKED" and mode == "strict" else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    keys = _resolve_keys(args)
    ocr_root = _resolve_ocr_root(args.source_root)
    output_root = Path(args.output_root)

    exit_code = 0
    for key in keys:
        code = _audit_one_paper(
            ocr_root=ocr_root,
            key=key,
            mode=args.mode,
            refresh_artifacts=bool(args.refresh_artifacts),
            include_pages=args.include_pages,
            focus=[str(item) for item in args.focus],
            output_root=output_root,
        )
        exit_code = max(exit_code, code)
        print(f"[OK] {key}: audit outputs written to {output_root / key}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
