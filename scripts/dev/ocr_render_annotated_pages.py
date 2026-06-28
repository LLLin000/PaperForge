"""Render fitz-based annotated PDF pages for OCR gold audits.

Reads `block_trace.csv` from the test fixtures, resolves the source PDF from the
Literature-hub vault, and writes one annotated PNG per PDF page.

Usage:
    python scripts/dev/ocr_render_annotated_pages.py CAQNW9Q2 DWQQK2YB
    python scripts/dev/ocr_render_annotated_pages.py --all-gold
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import fitz
from PIL import Image


_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[2]
_FIXTURE_ROOT = _REPO_ROOT / "tests" / "fixtures" / "ocr_real_papers"
_LEDGER_PATH = _REPO_ROOT / "audit" / "coverage_ledger.json"
_VAULT = Path(r"D:\L\OB\Literature-hub")
_OCR_ROOT = _VAULT / "System" / "PaperForge" / "ocr"

ROLE_COLORS = {
    "paper_title": (0.0, 0.4, 1.0),
    "authors": (0.0, 0.7, 0.8),
    "abstract_heading": (0.4, 0.0, 0.9),
    "abstract_body": (0.6, 0.0, 0.9),
    "section_heading": (1.0, 0.2, 0.2),
    "subsection_heading": (1.0, 0.5, 0.0),
    "body_paragraph": (0.0, 0.7, 0.2),
    "reference_heading": (0.7, 0.1, 0.1),
    "reference_item": (0.7, 0.2, 0.2),
    "backmatter_heading": (0.5, 0.2, 0.7),
    "backmatter_body": (0.5, 0.3, 0.7),
    "structured_insert": (0.9, 0.0, 0.7),
    "frontmatter_support": (0.2, 0.7, 0.9),
    "frontmatter_noise": (0.4, 0.4, 0.4),
    "noise": (0.5, 0.5, 0.5),
    "unknown_structural": (0.2, 0.2, 0.2),
}


def _load_ledger() -> dict:
    return json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))


def _gold_keys() -> list[str]:
    return [paper["paper_key"] for paper in _load_ledger().get("papers", [])]


def _read_trace(key: str) -> list[dict[str, str]]:
    path = _FIXTURE_ROOT / key / "block_trace.csv"
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _resolve_source_pdf(key: str) -> Path:
    note_candidates = list(_VAULT.glob(f"Resources/Literature/**/{key}.md"))
    for note_path in note_candidates:
        text = note_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if not line.startswith("pdf_path:"):
                continue
            start = line.find("[[")
            end = line.find("]]", start + 2)
            if start >= 0 and end > start:
                rel = line[start + 2:end]
                pdf_path = _VAULT / rel.replace("/", "\\")
                if pdf_path.exists():
                    return pdf_path

    meta_path = _OCR_ROOT / key / "raw" / "source_metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        source = meta.get("source_pdf")
        if source and Path(source).exists():
            return Path(source)

    local = _OCR_ROOT / key / "source.pdf"
    if local.exists():
        return local

    raise FileNotFoundError(f"Could not resolve source PDF for {key}")


def _parse_bbox(raw: str) -> fitz.Rect:
    bbox = json.loads(raw)
    return fitz.Rect(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))


def _ocr_page_image_path(key: str, page_number: int) -> Path:
    page_dir = _OCR_ROOT / key / "pages"
    for suffix in ("png", "jpg", "jpeg"):
        candidate = page_dir / f"page_{page_number:03d}.{suffix}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Missing OCR page image for {key} page {page_number}")


def _scale_rect_to_pdf(key: str, page_number: int, rect: fitz.Rect, pdf_rect: fitz.Rect) -> fitz.Rect:
    image_path = _ocr_page_image_path(key, page_number)
    image_width, image_height = Image.open(image_path).size
    x_scale = pdf_rect.width / image_width
    y_scale = pdf_rect.height / image_height
    return fitz.Rect(
        rect.x0 * x_scale,
        rect.y0 * y_scale,
        rect.x1 * x_scale,
        rect.y1 * y_scale,
    )


def _role_color(role: str) -> tuple[float, float, float]:
    return ROLE_COLORS.get(role, (0.1, 0.1, 0.1))


def render_annotated_pages(key: str, *, zoom: float = 2.0) -> Path:
    pdf_path = _resolve_source_pdf(key)
    trace_rows = _read_trace(key)
    out_dir = _FIXTURE_ROOT / key / "annotated_pages"
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    rows_by_page: dict[int, list[dict[str, str]]] = {}
    for row in trace_rows:
        rows_by_page.setdefault(int(row["page"]), []).append(row)

    for page_number in range(1, doc.page_count + 1):
        page = doc.load_page(page_number - 1)
        boxes = rows_by_page.get(page_number, [])
        shape = page.new_shape()
        for row in boxes:
            rect = _scale_rect_to_pdf(key, page_number, _parse_bbox(row["bbox"]), page.rect)
            role = row.get("role", "")
            color = _role_color(role)
            shape.draw_rect(rect)
            shape.finish(color=color, width=0.8)
            label = f"{row.get('block_id', '')}:{role}"
            page.insert_text(
                fitz.Point(rect.x0, max(8, rect.y0 - 2)),
                label,
                fontsize=5,
                color=color,
                overlay=True,
            )
        shape.commit(overlay=True)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        pix.save(str(out_dir / f"page_{page_number:03d}.png"))

    doc.close()
    return out_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("keys", nargs="*")
    parser.add_argument("--all-gold", action="store_true")
    parser.add_argument("--zoom", type=float, default=2.0)
    args = parser.parse_args(argv)

    keys = args.keys
    if args.all_gold:
        keys = _gold_keys()
    if not keys:
        parser.error("provide paper keys or use --all-gold")

    for key in keys:
        out_dir = render_annotated_pages(key, zoom=args.zoom)
        print(f"[OK] {key}: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
