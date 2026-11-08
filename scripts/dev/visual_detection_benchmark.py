"""Read-only visual figure/table detection benchmark.

This tool answers a different question from the OCR figure matcher: *what is
visually on the page*, independent of the OCR block inventory. It renders each
PDF page, collects four box sources and writes per-page overlays plus a JSON
report:

- ``inventory``: the current figure/table boxes from the paper's structure
  artifacts (matched figure crops, table assets, captions, unmatched assets);
- ``pdf_graphics``: image XObjects and vector drawings from PyMuPDF, clustered
  by proximity (no OCR block roles involved);
- ``visual_doclayout``: DocLayout-YOLO detections (optional, lazy import);
- ``visual_docling``: Docling layout detections (optional, lazy import).

Nothing is written to the OCR vault. Outputs go to ``--out`` (overlays, JSON,
summary) only.

Example (no ML dependencies):

    python scripts/dev/visual_detection_benchmark.py \
        --vault /path/to/vault --keys 388XI46Q 2BYRLKQS --limit 10

With DocLayout-YOLO, run inside an environment that has ``doclayout-yolo`` and
``torch`` installed:

    python scripts/dev/visual_detection_benchmark.py --vault ... \
        --keys 388XI46Q --detectors doclayout --out benchmark-out
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BOX_KINDS = ("figure", "table")
SOURCE_COLORS = {
    "inventory": (0, 120, 255),        # blue
    "pdf_graphics": (0, 170, 90),      # green
    "visual_doclayout": (220, 40, 40), # red
    "visual_docling": (150, 60, 200),  # purple
}


@dataclass
class Box:
    source: str
    kind: str
    bbox_pdf: list[float]
    label: str = ""
    confidence: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def as_dict(self, page_w: float, page_h: float) -> dict[str, Any]:
        return {
            "source": self.source,
            "kind": self.kind,
            "label": self.label,
            "confidence": self.confidence,
            "bbox_pdf": [round(value, 2) for value in self.bbox_pdf],
            "bbox_norm": [
                round(self.bbox_pdf[0] / page_w, 4),
                round(self.bbox_pdf[1] / page_h, 4),
                round(self.bbox_pdf[2] / page_w, 4),
                round(self.bbox_pdf[3] / page_h, 4),
            ],
            "meta": self.meta,
        }


def _iou(a: list[float], b: list[float]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0, ix1, iy1 = max(ax0, bx0), max(ay0, by0), min(ax1, bx1), min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _union(boxes: Iterable[list[float]]) -> list[float] | None:
    boxes = [b for b in boxes if len(b) >= 4]
    if not boxes:
        return None
    return [
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    ]


def _area(bbox: list[float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def _cluster_rects(rects: list[list[float]], *, gap: float) -> list[list[float]]:
    """Union rects whose edges are within ``gap`` points (single-linkage)."""
    clusters: list[list[float]] = []
    for rect in rects:
        merged = True
        while merged:
            merged = False
            for index, cluster in enumerate(clusters):
                if (
                    rect[0] <= cluster[2] + gap
                    and rect[2] >= cluster[0] - gap
                    and rect[1] <= cluster[3] + gap
                    and rect[3] >= cluster[1] - gap
                ):
                    clusters[index] = [
                        min(cluster[0], rect[0]),
                        min(cluster[1], rect[1]),
                        max(cluster[2], rect[2]),
                        max(cluster[3], rect[3]),
                    ]
                    rect = clusters.pop(index)
                    merged = True
                    break
        clusters.append(rect)
    return clusters


# --- inventory -------------------------------------------------------------


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _inventory_boxes(paper_dir: Path) -> list[Box]:
    """Figure/table boxes the current pipeline actually materializes."""
    rows = {}
    page_dims: dict[int, tuple[float, float]] = {}
    structured = paper_dir / "structure/blocks.structured.jsonl"
    if structured.is_file():
        for line in structured.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            page = int(row.get("page", 0) or 0)
            rows[(page, str(row.get("block_id", "")))] = row
            width = float(row.get("page_width") or 0)
            height = float(row.get("page_height") or 0)
            if page and width > 0 and height > 0:
                page_dims.setdefault(page, (width, height))

    figures = _load_json(paper_dir / "structure/figure_inventory.json")
    tables = _load_json(paper_dir / "structure/table_inventory.json")
    boxes: list[Box] = []

    for figure in figures.get("matched_figures", []):
        page = int(figure.get("page", 0) or 0)
        crop = figure.get("cluster_bbox") or []
        if not (len(crop) == 4 and crop[2] > crop[0] and crop[3] > crop[1]):
            asset_boxes = [
                a.get("bbox") or []
                for a in figure.get("matched_assets", [])
                if len(a.get("bbox") or []) >= 4
            ]
            crop = _union(asset_boxes) or []
        if len(crop) == 4:
            boxes.append(
                Box(
                    source="inventory",
                    kind="figure",
                    bbox_pdf=[float(v) for v in crop],
                    label=str(figure.get("figure_id", "")),
                    meta={
                        "page": page,
                        "assets": figure.get("asset_block_ids") or [],
                        "page_width": (page_dims.get(page) or (None, None))[0],
                        "page_height": (page_dims.get(page) or (None, None))[1],
                    },
                )
            )
    for asset in figures.get("unmatched_assets", []):
        bbox = asset.get("bbox") or []
        if len(bbox) == 4:
            boxes.append(
                Box(
                    source="inventory",
                    kind="figure",
                    bbox_pdf=[float(v) for v in bbox],
                    label="unmatched_asset",
                    meta={
                        "page": int(asset.get("page", 0) or 0),
                        "block_id": str(asset.get("block_id", "")),
                        "page_width": asset.get("page_width")
                        or (page_dims.get(int(asset.get("page", 0) or 0)) or (None, None))[0],
                        "page_height": asset.get("page_height")
                        or (page_dims.get(int(asset.get("page", 0) or 0)) or (None, None))[1],
                    },
                )
            )
    for table in tables.get("tables", []):
        bbox = table.get("render_bbox") or table.get("asset_bbox") or []
        if len(bbox) == 4 and bbox[2] > bbox[0] and bbox[3] > bbox[1]:
            boxes.append(
                Box(
                    source="inventory",
                    kind="table",
                    bbox_pdf=[float(v) for v in bbox],
                    label=str(table.get("caption_block_id", "")),
                    meta={
                        "page": int(table.get("page", 0) or 0),
                        "asset": table.get("asset_block_id"),
                        "page_width": (page_dims.get(int(table.get("page", 0) or 0)) or (None, None))[0],
                        "page_height": (page_dims.get(int(table.get("page", 0) or 0)) or (None, None))[1],
                    },
                )
            )
    return boxes


# --- PDF visual evidence ---------------------------------------------------


def _pdf_graphics_boxes(page: Any, *, min_area_ratio: float) -> list[Box]:
    page_area = page.rect.width * page.rect.height
    image_rects: list[list[float]] = []
    for info in page.get_image_info():
        bbox = [float(v) for v in info.get("bbox", [])]
        if len(bbox) != 4:
            continue
        if _area(bbox) / page_area < min_area_ratio:
            continue
        image_rects.append(bbox)
    drawing_rects: list[list[float]] = []
    for path in page.get_drawings():
        rect = path.get("rect")
        if rect is None:
            continue
        bbox = [float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)]
        if bbox[2] - bbox[0] < 2 or bbox[3] - bbox[1] < 2:
            continue
        if _area(bbox) / page_area < 0.002:
            continue
        drawing_rects.append(bbox)

    boxes: list[Box] = []
    for bbox in image_rects:
        boxes.append(Box(source="pdf_graphics", kind="figure", bbox_pdf=bbox, label="image_xobject"))
    for bbox in _cluster_rects(drawing_rects, gap=12.0):
        boxes.append(Box(source="pdf_graphics", kind="figure", bbox_pdf=bbox, label="drawing_cluster"))
    return boxes


# --- optional detectors ----------------------------------------------------


def _detect_doclayout(image_path: Path, *, conf: float, device: str, scale: float) -> list[Box]:
    from doclayout_yolo import DocLayoutYOLO  # type: ignore

    model = DocLayoutYOLO.from_pretrained("juliozhao/DocLayout-YOLO-DocStructBench")
    result = model.predict(str(image_path), imgsz=1024, conf=conf, device=device, verbose=False)[0]
    names = result.names
    boxes: list[Box] = []
    for xyxy, cls, score in zip(
        result.boxes.xyxy.tolist(), result.boxes.cls.tolist(), result.boxes.conf.tolist(), strict=False
    ):
        label = str(names.get(int(cls), cls))
        kind = "figure" if label in {"figure", "picture"} else "table" if label == "table" else None
        if kind is None:
            continue
        boxes.append(
            Box(
                source="visual_doclayout",
                kind=kind,
                bbox_pdf=[float(v) / scale for v in xyxy],
                label=label,
                confidence=float(score),
            )
        )
    return boxes


def _detect_docling(image_path: Path, *, scale: float, page_height_pdf: float) -> list[Box]:
    from docling.datamodel.base_models import InputFormat  # type: ignore
    from docling.document_converter import DocumentConverter, ImageFormatOption  # type: ignore

    converter = DocumentConverter(format_options={InputFormat.IMAGE: ImageFormatOption()})
    result = converter.convert(str(image_path))
    boxes: list[Box] = []
    for item, _level in result.document.iterate_items():
        label = str(getattr(item, "label", ""))
        kind = "figure" if label in {"picture", "figure"} else "table" if label == "table" else None
        prov = getattr(item, "prov", None) or []
        if kind is None or not prov:
            continue
        bbox = prov[0].bbox
        left = float(bbox.l) / scale
        right = float(bbox.r) / scale
        top = float(bbox.t) / scale
        bottom = float(bbox.b) / scale
        if str(getattr(bbox, "coord_origin", "")).endswith("BOTTOMLEFT"):
            y0, y1 = page_height_pdf - top, page_height_pdf - bottom
        else:
            y0, y1 = top, bottom
        boxes.append(
            Box(
                source="visual_docling",
                kind=kind,
                bbox_pdf=[left, y0, right, y1],
                label=label,
            )
        )
    return boxes


# --- overlays --------------------------------------------------------------


def _draw_overlay(pdf_page: Any, boxes: list[Box], destination: Path, *, dpi: int) -> None:
    import io

    from PIL import Image, ImageDraw

    pixmap = pdf_page.get_pixmap(dpi=dpi)
    image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
    scale = dpi / 72.0
    draw = ImageDraw.Draw(image)
    for box in boxes:
        color = SOURCE_COLORS.get(box.source, (0, 0, 0))
        x0, y0, x1, y1 = [value * scale for value in box.bbox_pdf]
        draw.rectangle([x0, y0, x1, y1], outline=color, width=3)
        draw.text((x0 + 4, max(0, y0 + 2)), f"{box.source}:{box.label}", fill=color)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)


# --- comparison ------------------------------------------------------------


def _match_sources(primary: list[Box], secondary: list[Box], *, iou_threshold: float) -> dict[str, Any]:
    unmatched_primary = []
    used_secondary: set[int] = set()
    for box in primary:
        best_index = None
        best_iou = 0.0
        for index, other in enumerate(secondary):
            if index in used_secondary:
                continue
            score = _iou(box.bbox_pdf, other.bbox_pdf)
            if score > best_iou:
                best_iou, best_index = score, index
        if best_index is not None and best_iou >= iou_threshold:
            used_secondary.add(best_index)
        else:
            unmatched_primary.append(box.as_dict(1, 1))
    unmatched_secondary = [
        box.as_dict(1, 1) for index, box in enumerate(secondary) if index not in used_secondary
    ]
    return {
        "matched": len(primary) - len(unmatched_primary),
        "unmatched_primary": unmatched_primary,
        "unmatched_secondary": unmatched_secondary,
    }


def _load_reference(path: Path | None) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path and path.is_file() else {}


def _reference_metrics(boxes: list[Box], reference: list[dict]) -> dict[str, Any]:
    if not reference:
        return {}
    ious = []
    used = set()
    for ref in reference:
        best, best_index = 0.0, None
        for index, box in enumerate(boxes):
            if index in used:
                continue
            score = _iou([float(v) for v in ref["bbox"]], box.bbox_pdf)
            if score > best:
                best, best_index = score, index
        if best_index is not None:
            used.add(best_index)
        ious.append(best)
    return {
        "reference_count": len(reference),
        "detected_count": len(boxes),
        "recall_at_0.5": sum(1 for score in ious if score >= 0.5) / len(reference),
        "recall_at_0.75": sum(1 for score in ious if score >= 0.75) / len(reference),
        "mean_best_iou": sum(ious) / len(ious),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, help="Obsidian vault root (source PDFs)")
    parser.add_argument("--ocr-root", default="", help="OCR root; default <vault>/System/PaperForge/ocr")
    parser.add_argument("--keys", nargs="*", default=[])
    parser.add_argument("--limit", type=int, default=0, help="first N papers when --keys is empty")
    parser.add_argument("--pages", default="", help="comma list or ranges, e.g. 4,14-15")
    parser.add_argument("--detectors", default="", help="comma list: doclayout,docling")
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--min-area-ratio", type=float, default=0.01)
    parser.add_argument("--iou-match", type=float, default=0.1)
    parser.add_argument("--reference", default="", help="ground-truth JSON")
    parser.add_argument("--out", required=True)
    parser.add_argument("--overlays", action="store_true", help="write per-page overlay PNGs")
    args = parser.parse_args()

    import pymupdf

    from paperforge.pdf_resolver import resolve_source_pdf

    vault = Path(args.vault)
    ocr_root = Path(args.ocr_root) if args.ocr_root else vault / "System/PaperForge/ocr"
    detectors = [name.strip() for name in args.detectors.split(",") if name.strip()]
    keys = args.keys or sorted(
        directory.name for directory in ocr_root.iterdir() if directory.is_dir() and (directory / "meta.json").is_file()
    )
    if args.limit:
        keys = keys[: args.limit]

    page_filter: set[int] | None = None
    if args.pages:
        page_filter = set()
        for chunk in args.pages.split(","):
            if "-" in chunk:
                start, end = chunk.split("-", 1)
                page_filter.update(range(int(start), int(end) + 1))
            else:
                page_filter.add(int(chunk))

    reference = _load_reference(Path(args.reference) if args.reference else None)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    report: list[dict[str, Any]] = []

    for key in keys:
        paper_dir = ocr_root / key
        meta = _load_json(paper_dir / "meta.json")
        pdf = resolve_source_pdf(vault, meta.get("source_pdf"))
        if pdf is None:
            report.append({"key": key, "error": "source_pdf_unresolved"})
            continue
        inventory = _inventory_boxes(paper_dir)
        document = pymupdf.open(str(pdf))
        try:
            for page_index in range(document.page_count):
                page_number = page_index + 1
                if page_filter and page_number not in page_filter:
                    continue
                page = document[page_index]
                page_w, page_h = page.rect.width, page.rect.height
                boxes = []
                for box in inventory:
                    if int(box.meta.get("page", 0) or 0) != page_number:
                        continue
                    ocr_w = float(box.meta.get("page_width") or 0)
                    ocr_h = float(box.meta.get("page_height") or 0)
                    if ocr_w > 0 and ocr_h > 0:
                        sx, sy = page_w / ocr_w, page_h / ocr_h
                        box.bbox_pdf = [
                            box.bbox_pdf[0] * sx,
                            box.bbox_pdf[1] * sy,
                            box.bbox_pdf[2] * sx,
                            box.bbox_pdf[3] * sy,
                        ]
                    boxes.append(box)
                graphics = _pdf_graphics_boxes(page, min_area_ratio=args.min_area_ratio)
                boxes.extend(graphics)

                page_image_path = out_root / "pages" / f"{key}_p{page_number:03d}.png"
                page_image_path.parent.mkdir(parents=True, exist_ok=True)
                page.get_pixmap(dpi=args.dpi).save(page_image_path)

                for detector in detectors:
                    try:
                        if detector == "doclayout":
                            boxes.extend(
                                _detect_doclayout(
                                    page_image_path, conf=args.conf, device=args.device, scale=args.dpi / 72.0
                                )
                            )
                        elif detector == "docling":
                            boxes.extend(
                                _detect_docling(
                                    page_image_path,
                                    scale=args.dpi / 72.0,
                                    page_height_pdf=page_h,
                                )
                            )
                    except Exception as exc:  # noqa: BLE001 — report detector failure per page
                        report.append(
                            {
                                "key": key,
                                "page": page_number,
                                "detector_error": f"{detector}: {type(exc).__name__}: {exc}",
                            }
                        )

                visual = [box for box in boxes if box.source != "inventory"]
                visual_figures = [box for box in visual if box.kind == "figure"]
                inventory_figures = [box for box in boxes if box.source == "inventory" and box.kind == "figure"]
                figure_match = _match_sources(visual_figures, inventory_figures, iou_threshold=args.iou_match)
                table_match = _match_sources(
                    [box for box in visual if box.kind == "table"],
                    [box for box in boxes if box.source == "inventory" and box.kind == "table"],
                    iou_threshold=args.iou_match,
                )
                page_reference = (reference.get(key) or {}).get("pages", {}).get(str(page_number), [])
                page_record = {
                    "key": key,
                    "page": page_number,
                    "pdf": str(pdf),
                    "page_size_pdf": [round(page_w, 2), round(page_h, 2)],
                    "boxes": [box.as_dict(page_w, page_h) for box in boxes],
                    "visual_missing_from_inventory": figure_match["unmatched_primary"],
                    "inventory_without_visual_support": figure_match["unmatched_secondary"],
                    "table_missing_from_inventory": table_match["unmatched_primary"],
                    "reference_metrics": _reference_metrics(visual, page_reference),
                }
                report.append(page_record)

                if args.overlays:
                    _draw_overlay(
                        page,
                        boxes,
                        out_root / "overlays" / f"{key}_p{page_number:03d}.png",
                        dpi=args.dpi,
                    )
        finally:
            document.close()

    json_path = out_root / "benchmark.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    pages = [entry for entry in report if "boxes" in entry]
    missing = sum(len(entry["visual_missing_from_inventory"]) for entry in pages)
    unsupported = sum(len(entry["inventory_without_visual_support"]) for entry in pages)
    print(f"pages={len(pages)} visual_missing={missing} inventory_unsupported={unsupported} out={json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
