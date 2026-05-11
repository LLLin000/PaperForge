from __future__ import annotations

import html
import json
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from json import JSONDecodeError
from pathlib import Path

import fitz
import requests
from PIL import Image

from paperforge.config import paperforge_paths
from paperforge.worker import sync as _sync
from paperforge.worker._progress import progress_bar


def _read_dotenv(vault: Path, key: str) -> str:
    """Read *key* from vault/.env or System/PaperForge/.env, return empty if not found."""
    for dotenv_path in (vault / ".env", paperforge_paths(vault).get("pipeline", Path()) / ".env"):
        try:
            for line in dotenv_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() == key:
                    return v.strip().strip('"').strip("'")
        except (OSError, UnicodeDecodeError):
            continue
    return ""


from paperforge.worker.asset_index import refresh_index_entry
from paperforge.worker._retry import retry_with_meta
from paperforge.worker._utils import (
    pipeline_paths,
    read_json,
    write_json,
)
from paperforge.worker.sync import (
    load_control_actions,
    load_export_rows,
)

logger = logging.getLogger(__name__)


def ensure_ocr_meta(vault: Path, row: dict) -> dict:
    paths = pipeline_paths(vault)
    key = row["zotero_key"]
    meta_path = paths["ocr"] / key / "meta.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        meta = read_json(meta_path) if meta_path.exists() else {}
    except Exception:
        meta = {}
    meta.setdefault("zotero_key", key)
    meta.setdefault("source_pdf", row.get("pdf_path", ""))
    meta.setdefault("ocr_provider", "PaddleOCR-VL-1.5")
    meta.setdefault("mode", "async")
    meta.setdefault("ocr_status", "pending")
    meta.setdefault("ocr_job_id", "")
    meta.setdefault("ocr_started_at", "")
    meta.setdefault("ocr_finished_at", "")
    meta.setdefault("page_count", 0)
    meta.setdefault("markdown_path", "")
    meta.setdefault("json_path", "")
    try:
        assets_path = str((paths["ocr"] / key / "images").relative_to(vault)).replace("\\", "/")
    except ValueError:
        assets_path = str(paths["ocr"] / key / "images")
    meta.setdefault("assets_path", assets_path)
    meta.setdefault("fulltext_md_path", "")
    meta.setdefault("error", "")
    meta.setdefault("retry_count", 0)
    meta.setdefault("last_error", None)
    meta.setdefault("last_attempt_at", None)
    return meta


def _read_meta_or_empty(meta_path: Path) -> dict:
    try:
        return read_json(meta_path) if meta_path.exists() else {}
    except Exception:
        return {}


def validate_ocr_meta(paths: dict[str, Path], meta: dict) -> tuple[str, str]:
    status = str(meta.get("ocr_status", "pending") or "pending").strip().lower()
    if status != "done":
        return (status, str(meta.get("error", "") or ""))
    key = str(meta.get("zotero_key", "") or "").strip()
    if not key:
        return ("done_incomplete", "Missing zotero_key in OCR meta")
    ocr_root = paths["ocr"] / key
    fulltext_path = ocr_root / "fulltext.md"
    json_path = ocr_root / "json" / "result.json"
    page_count = int(meta.get("page_count", 0) or 0)
    if not fulltext_path.exists():
        return ("done_incomplete", "OCR fulltext.md missing")
    if not json_path.exists():
        return ("done_incomplete", "OCR result.json missing")
    fulltext_size = fulltext_path.stat().st_size
    json_size = json_path.stat().st_size
    if page_count < 1:
        return ("done_incomplete", "OCR page_count invalid")
    if fulltext_size < 500:
        return ("done_incomplete", "OCR fulltext.md too small")
    if json_size < 1000:
        return ("done_incomplete", "OCR result.json too small")
    try:
        rendered_pages = fulltext_path.read_text(encoding="utf-8").count("<!-- page ")
    except Exception:
        rendered_pages = 0
    if rendered_pages < 1:
        return ("done_incomplete", "OCR fulltext has no rendered pages")
    if rendered_pages != page_count:
        return ("done_incomplete", f"OCR page marker mismatch: meta={page_count}, rendered={rendered_pages}")
    return ("done", "")


def read_ocr_queue(paths: dict[str, Path]) -> list[dict]:
    queue_path = paths["ocr_queue"]
    if not queue_path.exists():
        return []
    try:
        data = read_json(queue_path)
        return data if isinstance(data, list) else []
    except JSONDecodeError:
        text = queue_path.read_text(encoding="utf-8")
        recovered = []
        decoder = json.JSONDecoder()
        index = 0
        while True:
            match = re.search("\\{", text[index:])
            if not match:
                break
            start = index + match.start()
            try:
                obj, end = decoder.raw_decode(text, start)
            except JSONDecodeError:
                index = start + 1
                continue
            if isinstance(obj, dict) and obj.get("zotero_key"):
                recovered.append(obj)
            index = end
        deduped = []
        seen = set()
        for row in recovered:
            key = row.get("zotero_key")
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        write_json(queue_path, deduped)
        return deduped


def write_ocr_queue(paths: dict[str, Path], queue_rows: list[dict]) -> None:
    deduped = []
    seen = set()
    for row in queue_rows:
        key = row.get("zotero_key")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    write_json(paths["ocr_queue"], deduped)


def sync_ocr_queue(paths: dict[str, Path], target_rows: list[dict]) -> list[dict]:
    existing_queue = read_ocr_queue(paths)
    target_map = {row["zotero_key"]: row for row in target_rows}
    synced_queue: list[dict] = []
    queued_keys: set[str] = set()
    for row in existing_queue:
        key = row.get("zotero_key")
        if not key or key not in target_map:
            continue
        target = target_map[key]
        if not target.get("has_pdf"):
            continue
        meta_path = paths["ocr"] / key / "meta.json"
        meta = _read_meta_or_empty(meta_path)
        status = str(meta.get("ocr_status", "pending") or "pending").strip().lower()
        if status in {"done", "blocked"}:
            continue
        synced = dict(row)
        synced["has_pdf"] = bool(target.get("has_pdf"))
        synced["pdf_path"] = target.get("pdf_path", "")
        synced["queue_status"] = status
        if not synced.get("queued_at"):
            synced["queued_at"] = datetime.now(timezone.utc).isoformat()
        synced_queue.append(synced)
        queued_keys.add(key)
    now = datetime.now(timezone.utc).isoformat()
    for row in target_rows:
        key = row["zotero_key"]
        if key in queued_keys:
            continue
        if not row.get("has_pdf"):
            continue
        meta_path = paths["ocr"] / key / "meta.json"
        meta = _read_meta_or_empty(meta_path)
        status = str(meta.get("ocr_status", "pending") or "pending").strip().lower()
        if status in {"done", "blocked"}:
            continue
        synced_queue.append(
            {
                "zotero_key": key,
                "has_pdf": bool(row.get("has_pdf")),
                "pdf_path": row.get("pdf_path", ""),
                "queued_at": now,
                "queue_status": status,
            }
        )
    write_ocr_queue(paths, synced_queue)
    return synced_queue


def cleanup_blocked_ocr_dirs(paths: dict[str, Path]) -> None:
    for meta_path in paths["ocr"].glob("*/meta.json"):
        try:
            meta = read_json(meta_path)
        except Exception:
            continue
        status = str(meta.get("ocr_status", "") or "").strip().lower()
        str(meta.get("zotero_key", "") or "").strip()
        ocr_dir = meta_path.parent
        if status != "blocked":
            continue
        has_payload = any(
            candidate.exists() for candidate in [ocr_dir / "fulltext.md", ocr_dir / "json" / "result.json"]
        )
        if has_payload:
            continue
        shutil.rmtree(ocr_dir, ignore_errors=True)


def normalize_obsidian_markdown(text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    normalized = re.sub("[^\\S\\n]+\\$", "$", normalized)
    normalized = re.sub("\\$[^\\S\\n]+", "$", normalized)
    normalized = re.sub(
        "\\$\\^\\{([^}]+)\\*\\}\\$",
        lambda m: _superscript_to_correspondence_footnote(m.group(1)),
        normalized,
    )
    normalized = re.sub(
        "\\$\\^\\{([^}]*)\\\\dagger\\}\\$", lambda m: _superscript_to_equal_footnote(m.group(1)), normalized
    )
    normalized = re.sub("\\$\\^\\{([^}]*)†\\}\\$", lambda m: _superscript_to_equal_footnote(m.group(1)), normalized)
    normalized = re.sub("\\$\\s+\\^", "$^", normalized)
    normalized = re.sub("\\^\\{\\s+", "^{", normalized)
    normalized = re.sub("\\s+\\}", "}", normalized)
    normalized = normalized.replace("$^{ID}$", "")
    normalized = re.sub("[^\\S\\n]{2,}", " ", normalized)
    normalized = re.sub(
        "(?m)^\\*\\s*Correspondence:\\s*(.+)$", lambda match: f"[^correspondence]: {match.group(1).strip()}", normalized
    )
    normalized = re.sub(
        "(?m)^Correspondence:\\s*(.+)$", lambda match: f"[^correspondence]: {match.group(1).strip()}", normalized
    )
    normalized = re.sub("(?m)^†\\s*(.+)$", lambda match: f"[^equal]: {match.group(1).strip()}", normalized)
    normalized = re.sub(
        r"(?<!\\)(\*{1,3})\s*(?:=\s*)?(p\s*<\s*[\d]+(?:\.[\d]+)?)",
        lambda m: f"${m.group(1)}{m.group(2).strip()}$",
        normalized,
    )
    normalized = re.sub(
        r"\$\^\{\*\}\$\s*=\s*p\s*<\s*([\d]+(?:\.[\d]+)?)",
        lambda m: f"$*p < {m.group(1)}$",
        normalized,
    )
    normalized = re.sub(
        r"\$\^\{\*\}\$\s*(p\s*<\s*[\d]+(?:\.[\d]+)?)",
        lambda m: f"$*{m.group(1).strip()}$",
        normalized,
    )
    normalized = re.sub(
        r"(?<!\$)\bp\s*<\s*[\d]+(?:\.[\d]+)?",
        lambda m: f"${m.group(0).strip()}$" if normalized[: m.start()].count("$") % 2 == 0 else m.group(0),
        normalized,
    )
    normalized = re.sub("([A-Za-z])(\\$[^$\\n]+\\$)", "\\1 \\2", normalized)
    normalized = re.sub("(\\$[^$\\n]+\\$)([A-Za-z])", "\\1 \\2", normalized)
    normalized = re.sub("\\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _image_embed_for_obsidian(vault_rel: Path) -> str:
    return f"![[{str(vault_rel).replace(chr(92), '/')}]]"


def _superscript_to_equal_footnote(content: str) -> str:
    cleaned = re.sub("(,)?\\\\dagger", "", content).replace("†", "").strip(", ")
    if cleaned:
        return f"$^{{{cleaned}}}$[^equal]"
    return "[^equal]"


def _superscript_to_correspondence_footnote(content: str) -> str:
    cleaned = content.replace("*", "").strip(", ")
    if cleaned:
        return f"$^{{{cleaned}}}$[^correspondence]"
    return "[^correspondence]"


def ensure_page_image_cached(url: str, destination: Path) -> Path | None:
    if destination.exists():
        return destination
    if not url:
        return None
    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
    except requests.RequestException:
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    return destination


def render_pdf_page_cached(
    pdf_doc, page_index: int, target_width: int, target_height: int, destination: Path
) -> Path | None:
    if destination.exists():
        return destination
    if not pdf_doc or page_index < 1 or page_index > len(pdf_doc):
        return None
    try:
        page = pdf_doc[page_index - 1]
        rect = page.rect
        zoom_x = target_width / rect.width if target_width and rect.width else 2.0
        zoom_y = target_height / rect.height if target_height and rect.height else 2.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom_x, zoom_y), alpha=False)
        destination.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(destination))
        return destination
    except Exception:
        return None


def crop_block_asset(page_image_path: Path, bbox: list[int], destination: Path) -> bool:
    if destination.exists():
        return True
    try:
        with Image.open(page_image_path) as img:
            x1, y1, x2, y2 = (max(0, int(v)) for v in bbox)
            if x2 <= x1 or y2 <= y1:
                return False
            crop = img.crop((x1, y1, x2, y2))
            destination.parent.mkdir(parents=True, exist_ok=True)
            crop.save(destination)
            return True
    except Exception:
        return False


def block_sort_key(block: dict) -> tuple[int, int, int, int]:
    bbox = block.get("block_bbox", [0, 0, 0, 0])
    return (int(bbox[1]), int(bbox[0]), int(bbox[3]), int(bbox[2]))


def clean_block_text(text: str) -> str:
    text = html.unescape(normalize_obsidian_markdown(text)).strip()
    return text


def is_subfigure_label(text: str) -> bool:
    compact = re.sub("\\s+", " ", text.strip().lower())
    return bool(
        re.fullmatch("(?:\\([a-z]\\)\\s*)+", compact)
        or re.fullmatch("[a-z]", compact)
        or re.fullmatch("[a-z]\\)", compact)
    )


def is_affiliation_line(text: str) -> bool:
    compact = " ".join(text.split())
    if re.match("^(?:\\$\\^\\{)?\\d+(?:[,\\d-]*)?(?:\\})?", compact):
        return True
    keywords = (
        "university",
        "department",
        "college",
        "school",
        "institute",
        "hospital",
        "center",
        "centre",
        "laboratory",
        "lab",
        "program",
        "research",
    )
    lower = compact.lower()
    return any(word in lower for word in keywords) and len(compact) > 30


def is_frontmatter_noise_line(text: str) -> bool:
    compact = " ".join(text.split())
    lower = compact.lower()
    if compact in {"Article", "Review"}:
        return True
    prefixes = (
        "academic editor:",
        "copyright:",
        "licensee",
        "this article is an open access article",
        "publisher's note:",
        "check for updates",
    )
    if lower.startswith(prefixes):
        return True
    if re.fullmatch("\\d+\\s+\\w{1,6}", compact):
        return True
    return bool(len(compact) < 18 and re.search("\\d", compact))


def is_reference_tail_noise_line(text: str) -> bool:
    compact = clean_block_text(text)
    lower = compact.lower()
    if "submit your next manuscript" in lower:
        return True
    patterns = (
        "^doi:\\s*10\\.",
        "^Cite this article as:",
        "^Submit your next manuscript",
        "^BioMed Central\\b",
        "^Convenient online submission$",
        "^Thorough peer review$",
        "^No space constraints",
        "^Immediate publication on acceptance$",
        "^Inclusion in PubMed, CAS, Scopus and Google Scholar$",
        "^Research which is freely available for redistribution$",
        "^[•\\-]\\s*(Convenient online submission|Thorough peer review|No space constraints|Immediate publication on acceptance|Inclusion in PubMed|Research which is freely available)",
    )
    return any(re.match(pattern, compact, flags=re.IGNORECASE) for pattern in patterns)


def parse_reference_number(text: str) -> int | None:
    text = clean_block_text(text)
    m = re.match("^\\s*(\\d+)[\\.\\)]\\s*", text)
    if m:
        return int(m.group(1))
    m = re.match("^\\s*\\[(\\d+)\\][\\]\\.\\)\\s]*", text)
    if m:
        return int(m.group(1))
    return None


def sort_reference_blocks(blocks: list[dict]) -> list[dict]:
    numbered_count = sum(parse_reference_number(block.get("block_content", "")) is not None for block in blocks)
    if numbered_count >= max(3, len(blocks) // 2):
        return sorted(
            blocks,
            key=lambda block: (
                parse_reference_number(block.get("block_content", "")) is None,
                parse_reference_number(block.get("block_content", "")) or 10**9,
                block_sort_key(block),
            ),
        )
    return sorted(
        blocks, key=lambda block: (block.get("block_bbox", [0, 0, 0, 0])[0], block.get("block_bbox", [0, 0, 0, 0])[1])
    )


def assign_reference_continuation(continuation_block: dict, reference_blocks: list[dict]) -> int | None:
    bbox = continuation_block.get("block_bbox", [0, 0, 0, 0])
    x1, y1, x2, _ = bbox
    candidates = []
    for index, ref_block in enumerate(reference_blocks):
        rb = ref_block.get("block_bbox", [0, 0, 0, 0])
        rx1, ry1, rx2, ry2 = rb
        horizontal_overlap = min(x2, rx2) - max(x1, rx1)
        same_column = horizontal_overlap > 0 or abs((x1 + x2) / 2 - (rx1 + rx2) / 2) < 180
        if not same_column or ry1 > y1:
            continue
        candidates.append((index, ry2, abs((x1 + x2) / 2 - (rx1 + rx2) / 2)))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[1], item[2]))
    return candidates[0][0]


def clean_author_line(text: str) -> str:
    text = clean_block_text(text)
    text = text.replace("$^{ID}$", "")
    text = re.sub("\\s*,\\s*", ", ", text)
    text = re.sub("\\s+and\\s+", " and ", text)
    text = re.sub("([a-z])and ([A-Z])", "\\1 and \\2", text)
    return text


def handle_first_page_metadata_lines(
    text: str, rendered: list[str], affiliation_buffer: list[str], deferred_meta: list[str], footnotes: list[str]
) -> bool:
    handled = False
    lines = [part.strip() for part in text.splitlines() if part.strip()]
    if not lines:
        return True
    for line in lines:
        if is_frontmatter_noise_line(line):
            handled = True
            continue
        if line.startswith("Citation:"):
            deferred_meta.append(line)
            handled = True
            continue
        if (
            line.startswith("Received:")
            or line.startswith("Revised:")
            or line.startswith("Accepted:")
            or line.startswith("Published:")
        ):
            deferred_meta.append(line)
            handled = True
            continue
        if line.startswith("Correspondence:") or line.startswith("* Correspondence:"):
            footnotes[:] = [fn for fn in footnotes if not fn.startswith("[^correspondence]:")]
            footnotes.append(f"[^correspondence]: {line.split(':', 1)[1].strip()}")
            handled = True
            continue
        if line.startswith("† "):
            footnotes[:] = [fn for fn in footnotes if not fn.startswith("[^equal]:")]
            footnotes.append(f"[^equal]: {line[2:].strip()}")
            handled = True
            continue
        if is_affiliation_line(line):
            affiliation_buffer.append(line)
            handled = True
            continue
        if "$^{" in line and "," in line and (" and " in line):
            rendered.append(clean_author_line(line))
            handled = True
            continue
        if len(line) < 22 or re.fullmatch("\\d+\\s+\\w+", line):
            handled = True
            continue
    return handled


def footnote_marker_and_body(content: str) -> tuple[str, str]:
    cleaned = clean_block_text(content)
    match = re.match("^\\$?\\^?\\{?([^\\}\\s]+)\\}?\\$?\\s*(.+)$", cleaned)
    if match:
        return (match.group(1).strip(), match.group(2).strip())
    return ("", cleaned)


def attach_footnote_reference(text: str, marker: str, footnote_id: str) -> str:
    if not marker:
        return text
    candidates = [f"$^{{{marker}}}$", f"$^{{{marker},*}}$", f"$^{{*,{marker}}}$"]
    for token in candidates:
        if token in text and f"{token}[^{footnote_id}]" not in text:
            return text.replace(token, f"{token}[^{footnote_id}]", 1)
    return text


def parse_vision_footnote_entries(content: str) -> list[tuple[str, str]]:
    cleaned = clean_block_text(content)
    if not cleaned:
        return []
    matches = re.findall("\\$?\\^\\{?([A-Za-z*]+)\\}?\\$?\\s*([^;]+)", cleaned)
    if matches:
        return [(marker.strip(), body.strip()) for marker, body in matches if body.strip()]
    marker, body = footnote_marker_and_body(content)
    return [(marker, body)] if body else []


def _parse_asset_bbox_from_line(line: str) -> tuple[int, int, int, int] | None:
    match = re.search("page_(\\d+)_(?:figure|table)_(\\d+)_(\\d+)_(\\d+)_(\\d+)\\.jpg", line)
    if not match:
        return None
    return tuple(int(match.group(i)) for i in range(2, 6))


def _bbox_area(bbox: tuple[int, int, int, int]) -> int:
    x1, y1, x2, y2 = bbox
    return max(0, x2 - x1) * max(0, y2 - y1)


def _bbox_contains(outer: tuple[int, int, int, int], inner: tuple[int, int, int, int], margin: int = 12) -> bool:
    ox1, oy1, ox2, oy2 = outer
    ix1, iy1, ix2, iy2 = inner
    return ox1 - margin <= ix1 and oy1 - margin <= iy1 and (ox2 + margin >= ix2) and (oy2 + margin >= iy2)


def dedupe_page_media_lines(lines: list[str]) -> list[str]:
    media_indexes: list[tuple[int, tuple[int, int, int, int]]] = []
    for idx, line in enumerate(lines):
        if not line.startswith("![["):
            continue
        bbox = _parse_asset_bbox_from_line(line)
        if bbox:
            media_indexes.append((idx, bbox))
    drop_indexes: set[int] = set()
    for idx, bbox in media_indexes:
        for other_idx, other_bbox in media_indexes:
            if idx == other_idx:
                continue
            if _bbox_contains(other_bbox, bbox) and _bbox_area(other_bbox) > _bbox_area(bbox) * 1.15:
                drop_indexes.add(idx)
                break
    return [line for i, line in enumerate(lines) if i not in drop_indexes]


def attach_table_footnotes(table_html: str, marker_to_id: dict[str, str]) -> str:
    def replacer(match):
        markers = [part.strip() for part in match.group(1).split(",")]
        refs = []
        for marker in markers:
            ref_id = marker_to_id.get(marker)
            refs.append(f"{marker}[^{ref_id}]" if ref_id else marker)
        return ", ".join(refs) + "</td>"

    return re.sub("([a-z](?:\\s*,\\s*[a-z])*)</td>", replacer, table_html)


def media_clusters(blocks: list[dict]) -> tuple[dict[int, int], list[list[dict]]]:
    media = [b for b in blocks if b.get("block_label") in {"image", "chart"}]
    clusters: list[list[dict]] = []
    block_to_cluster: dict[int, int] = {}
    for block in media:
        x1, y1, x2, y2 = block.get("block_bbox", [0, 0, 0, 0])
        assigned = None
        for idx, cluster in enumerate(clusters):
            cx1 = min(item["block_bbox"][0] for item in cluster) - 40
            cy1 = min(item["block_bbox"][1] for item in cluster) - 40
            cx2 = max(item["block_bbox"][2] for item in cluster) + 40
            cy2 = max(item["block_bbox"][3] for item in cluster) + 40
            if not (x2 < cx1 or x1 > cx2 or y2 < cy1 or (y1 > cy2)):
                assigned = idx
                break
        if assigned is None:
            assigned = len(clusters)
            clusters.append([])
        clusters[assigned].append(block)
        block_to_cluster[block.get("block_id", -1)] = assigned
    return (block_to_cluster, clusters)


def _bbox_width(bbox: list[int]) -> int:
    return max(0, int(bbox[2]) - int(bbox[0]))


def _bbox_height(bbox: list[int]) -> int:
    return max(0, int(bbox[3]) - int(bbox[1]))


def _bbox_horizontal_overlap(a: list[int], b: list[int]) -> int:
    return max(0, min(int(a[2]), int(b[2])) - max(int(a[0]), int(b[0])))


def _bbox_vertical_overlap(a: list[int], b: list[int]) -> int:
    return max(0, min(int(a[3]), int(b[3])) - max(int(a[1]), int(b[1])))


def _bbox_horizontal_overlap_ratio(a: list[int], b: list[int]) -> float:
    width = min(_bbox_width(a), _bbox_width(b))
    if width <= 0:
        return 0.0
    return _bbox_horizontal_overlap(a, b) / width


def _bbox_center_x(bbox: list[int]) -> float:
    return (int(bbox[0]) + int(bbox[2])) / 2


def _bbox_center_y(bbox: list[int]) -> float:
    return (int(bbox[1]) + int(bbox[3])) / 2


def _cluster_bbox(cluster: list[dict]) -> list[int]:
    return [
        min(int(item["block_bbox"][0]) for item in cluster),
        min(int(item["block_bbox"][1]) for item in cluster),
        max(int(item["block_bbox"][2]) for item in cluster),
        max(int(item["block_bbox"][3]) for item in cluster),
    ]


def _union_bboxes(bbox_list: list[list[int]]) -> list[int]:
    return [
        min(int(bbox[0]) for bbox in bbox_list),
        min(int(bbox[1]) for bbox in bbox_list),
        max(int(bbox[2]) for bbox in bbox_list),
        max(int(bbox[3]) for bbox in bbox_list),
    ]


def is_formal_figure_legend(text: str) -> bool:
    cleaned = clean_block_text(text)
    if not cleaned:
        return False
    return bool(
        re.match(
            "^(?:Extended\\s+Data\\s+Fig\\.?\\s+\\w+|Extended\\s+Data\\s+Figure\\s+\\w+|Extended\\s+Data\\s+Table\\s+\\w+|Supplementary\\s+Fig\\.?\\s+\\w+|Supplementary\\s+Figure\\s+\\w+|Supplementary\\s+Table\\s+\\w+|Supplementary\\s+Video\\s+\\w+|Figure\\s+\\d+|Fig\\.?\\s+\\d+|Table\\s+\\d+|Scheme\\s+\\w+|Graphical\\s+Abstract(?:\\s*[:|.\\-].*)?)",
            cleaned,
            flags=re.IGNORECASE,
        )
    )


def is_numbered_figure_caption(text: str) -> bool:
    cleaned = clean_block_text(text)
    if not re.match(r"^(?:Figure|Fig\.?)\s+\d+\b", cleaned, flags=re.IGNORECASE):
        return False
    return not re.match(
        r"^(?:Figure|Fig\.?)\s+\d+\s+(?:shows?|illustrates?|depicts?|describes?|summarizes?)\b",
        cleaned,
        flags=re.IGNORECASE,
    )


def _figure_caption_blocks(blocks: list[dict]) -> list[dict]:
    captions = []
    for block in blocks:
        if block.get("block_label") not in {"figure_title", "paragraph_title", "text"}:
            continue
        text = clean_block_text(block.get("block_content", ""))
        if is_formal_figure_legend(text):
            captions.append(block)
    return captions


def estimate_body_column_width(blocks: list[dict], page_width: int = 0) -> int:
    widths: list[int] = []
    for block in blocks:
        if block.get("block_label") not in {"text", "paragraph_title", "abstract"}:
            continue
        text = clean_block_text(block.get("block_content", ""))
        if (
            not text
            or is_subfigure_label(text)
            or re.match("^(?:Figure|Fig\\.?|Table)\\s+\\w+", text, flags=re.IGNORECASE)
        ):
            continue
        bbox = [int(value) for value in block.get("block_bbox", [0, 0, 0, 0])]
        width = _bbox_width(bbox)
        height = _bbox_height(bbox)
        if width <= 0 or height <= 0:
            continue
        if page_width and width >= int(page_width * 0.82):
            widths.append(width)
            continue
        if width >= 430:
            widths.append(width)
    if not widths:
        return int(page_width * 0.45) if page_width else 520
    widths.sort()
    return widths[len(widths) // 2]


def is_body_paragraph_like_text_block(
    block: dict,
    body_column_width: int = 0,
    cluster_bboxes: list[list[int]] | None = None,
    caption_bbox: list[int] | None = None,
) -> bool:
    if block.get("block_label") not in {"text", "paragraph_title", "abstract"}:
        return False
    text = clean_block_text(block.get("block_content", ""))
    if not text or is_formal_figure_legend(text) or is_subfigure_label(text):
        return False
    bbox = [int(value) for value in block.get("block_bbox", [0, 0, 0, 0])]
    width = _bbox_width(bbox)
    height = _bbox_height(bbox)
    if width <= 0 or height <= 0:
        return False
    if body_column_width and width < int(body_column_width * 0.72):
        return False
    if (not body_column_width) and width < 360:
        return False
    if height < 110:
        return False
    sentence_breaks = len(re.findall(r"[.!?](?:\s|$)", text))
    if len(text) < 180 and sentence_breaks < 2:
        return False
    if caption_bbox is not None:
        caption_gap = int(caption_bbox[1]) - int(bbox[3])
        if not (24 <= caption_gap <= 720):
            return False
    if cluster_bboxes:
        nearest_vertical_gap = None
        for cluster_bbox in cluster_bboxes:
            if _bbox_vertical_overlap(bbox, cluster_bbox) > 0:
                return False
            gap = None
            if int(bbox[3]) <= int(cluster_bbox[1]):
                gap = int(cluster_bbox[1]) - int(bbox[3])
            elif int(cluster_bbox[3]) <= int(bbox[1]):
                gap = int(bbox[1]) - int(cluster_bbox[3])
            if gap is None:
                continue
            if nearest_vertical_gap is None or gap < nearest_vertical_gap:
                nearest_vertical_gap = gap
        if nearest_vertical_gap is not None and nearest_vertical_gap > 140:
            return False
    return True


def _precaption_media_region(
    caption_bbox: list[int],
    cluster_bboxes: list[list[int]],
    blocks: list[dict] | None = None,
    body_column_width: int = 0,
) -> list[int] | None:
    relevant = [bbox for bbox in cluster_bboxes if int(bbox[3]) <= int(caption_bbox[1]) + 24]
    if len(relevant) < 1:
        return None
    if not blocks:
        return _union_bboxes(relevant)
    caption_y1 = int(caption_bbox[1])
    barrier_y = 0
    for block in blocks:
        label = block.get("block_label", "")
        if label not in {"text", "paragraph_title", "abstract"}:
            continue
        bbox = block.get("block_bbox", [0, 0, 0, 0])
        if int(bbox[3]) > caption_y1 + 24 or int(bbox[3]) <= barrier_y:
            continue
        text = clean_block_text(block.get("block_content", ""))
        if not text:
            continue
        if is_subfigure_label(text):
            continue
        if is_formal_figure_legend(text):
            barrier_y = max(barrier_y, int(bbox[3]))
            continue
        width = _bbox_width(bbox)
        height = _bbox_height(bbox)
        if width <= 0 or height <= 0:
            continue
        if body_column_width and width < int(body_column_width * 0.45):
            continue
        if not body_column_width and width < 320:
            continue
        if len(text) < 30:
            continue
        barrier_y = max(barrier_y, int(bbox[3]))
    for block in blocks:
        label = block.get("block_label", "")
        if label not in {"figure_title", "paragraph_title", "text"}:
            continue
        text = clean_block_text(block.get("block_content", ""))
        if not is_formal_figure_legend(text):
            continue
        bbox = block.get("block_bbox", [0, 0, 0, 0])
        if int(bbox[3]) <= caption_y1 and int(bbox[3]) > barrier_y:
            barrier_y = max(barrier_y, int(bbox[3]))
    filtered = [bbox for bbox in relevant if int(bbox[1]) >= barrier_y - 24]
    if len(filtered) < 1:
        return None
    return _union_bboxes(filtered)


def compute_precaption_composite_regions(blocks: list[dict], page_width: int = 0, page_height: int = 0) -> list[dict]:
    caption_blocks = _figure_caption_blocks(blocks)
    _, clusters = media_clusters(blocks)
    cluster_bboxes = [_cluster_bbox(cluster) for cluster in clusters]
    body_column_width = estimate_body_column_width(blocks, page_width=page_width)
    regions: list[dict] = []
    for caption in caption_blocks:
        caption_bbox = [int(value) for value in caption.get("block_bbox", [0, 0, 0, 0])]
        precaption_region = _precaption_media_region(
            caption_bbox, cluster_bboxes, blocks=blocks, body_column_width=body_column_width
        )
        if not precaption_region:
            continue
        region_blocks = []
        for block in blocks:
            label = block.get("block_label", "")
            bbox = [int(value) for value in block.get("block_bbox", [0, 0, 0, 0])]
            if bbox[3] > caption_bbox[1] + 24:
                continue
            if bbox[3] < precaption_region[1] - 240:
                continue
            vertical_overlap_with_region = _bbox_vertical_overlap(bbox, precaption_region)
            near_region_side = vertical_overlap_with_region > 0 and (
                0 <= precaption_region[0] - bbox[2] <= 80 or 0 <= bbox[0] - precaption_region[2] <= 80
            )
            intersects_region = (
                _bbox_horizontal_overlap(bbox, precaption_region) > 0
                or precaption_region[0] - 24 <= _bbox_center_x(bbox) <= precaption_region[2] + 24
                or near_region_side
            )
            if not intersects_region:
                continue
            if label in {"image", "chart"}:
                if _bbox_vertical_overlap(bbox, precaption_region) <= 0 and bbox[3] < precaption_region[1] - 80:
                    continue
                region_blocks.append(block)
                continue
            if label in {"text", "paragraph_title"}:
                if bbox[3] < precaption_region[1] - 80:
                    continue
                width = _bbox_width(bbox)
                text = clean_block_text(block.get("block_content", ""))
                if is_body_paragraph_like_text_block(
                    block,
                    body_column_width=body_column_width,
                    cluster_bboxes=cluster_bboxes,
                    caption_bbox=caption_bbox,
                ):
                    continue
                if (
                    text
                    and (
                        not re.match(
                            "^(?:Extended\\s+Data\\s+Fig\\.?|Extended\\s+Data\\s+Figure|Figure|Fig\\.?|Table)\\s+\\w+",
                            text,
                            flags=re.IGNORECASE,
                        )
                    )
                    and (
                        width <= int(max(body_column_width, 1) * 0.78)
                        or is_embedded_figure_text_block(block, blocks, page_width=page_width, page_height=page_height)
                    )
                ):
                    region_blocks.append(block)
        media_ids = {block.get("block_id") for block in region_blocks if block.get("block_label") in {"image", "chart"}}
        text_ids = {
            block.get("block_id") for block in region_blocks if block.get("block_label") in {"text", "paragraph_title"}
        }
        if len(media_ids) < 1 or not text_ids or len(region_blocks) < 3:
            continue
        region_bbox = [
            min(int(block["block_bbox"][0]) for block in region_blocks),
            min(int(block["block_bbox"][1]) for block in region_blocks),
            max(int(block["block_bbox"][2]) for block in region_blocks),
            max(int(block["block_bbox"][3]) for block in region_blocks),
        ]
        regions.append(
            {
                "bbox": region_bbox,
                "block_ids": {block.get("block_id") for block in region_blocks},
                "caption_block_id": caption.get("block_id"),
            }
        )
    return regions


def is_embedded_figure_text_block(block: dict, blocks: list[dict], page_width: int = 0, page_height: int = 0) -> bool:
    label = block.get("block_label", "")
    if label not in {"text", "paragraph_title"}:
        return False
    text = clean_block_text(block.get("block_content", ""))
    if not text:
        return False
    if is_formal_figure_legend(text):
        return False
    bbox = [int(value) for value in block.get("block_bbox", [0, 0, 0, 0])]
    width = _bbox_width(bbox)
    height = _bbox_height(bbox)
    if width <= 0 or height <= 0:
        return False
    if label == "paragraph_title" and is_subfigure_label(text):
        return True
    caption_blocks = _figure_caption_blocks(blocks)
    cluster_index, clusters = media_clusters(blocks)
    cluster_bboxes = [_cluster_bbox(cluster) for cluster in clusters]
    body_column_width = estimate_body_column_width(blocks, page_width=page_width)
    del cluster_index
    nearest_media = None
    nearest_media_distance = None
    close_media_count = 0
    stacked_media_above = False
    stacked_media_below = False
    side_media = False
    for cluster_bbox in cluster_bboxes:
        horizontal_ratio = _bbox_horizontal_overlap_ratio(bbox, cluster_bbox)
        vertical_overlap = _bbox_vertical_overlap(bbox, cluster_bbox)
        top_gap = int(bbox[1]) - int(cluster_bbox[3])
        bottom_gap = int(cluster_bbox[1]) - int(bbox[3])
        center_inside_x = int(cluster_bbox[0]) <= _bbox_center_x(bbox) <= int(cluster_bbox[2])
        center_inside_y = int(cluster_bbox[1]) <= _bbox_center_y(bbox) <= int(cluster_bbox[3])
        if (
            horizontal_ratio >= 0.45
            and (0 <= top_gap <= 48 or 0 <= bottom_gap <= 48 or vertical_overlap > 0)
            or (center_inside_x and abs(_bbox_center_y(bbox) - _bbox_center_y(cluster_bbox)) <= max(80, height * 4))
        ):
            close_media_count += 1
        if horizontal_ratio >= 0.5 and 0 <= top_gap <= 90:
            stacked_media_above = True
        if horizontal_ratio >= 0.5 and 0 <= bottom_gap <= 90:
            stacked_media_below = True
        if vertical_overlap > 0 and (
            0 <= int(bbox[0]) - int(cluster_bbox[2]) <= 60 or 0 <= int(cluster_bbox[0]) - int(bbox[2]) <= 60
        ):
            side_media = True
        dx = 0
        if int(bbox[2]) < int(cluster_bbox[0]):
            dx = int(cluster_bbox[0]) - int(bbox[2])
        elif int(cluster_bbox[2]) < int(bbox[0]):
            dx = int(bbox[0]) - int(cluster_bbox[2])
        dy = 0
        if int(bbox[3]) < int(cluster_bbox[1]):
            dy = int(cluster_bbox[1]) - int(bbox[3])
        elif int(cluster_bbox[3]) < int(bbox[1]):
            dy = int(bbox[1]) - int(cluster_bbox[3])
        distance = dx + dy
        if nearest_media_distance is None or distance < nearest_media_distance:
            nearest_media_distance = distance
            nearest_media = cluster_bbox
            del center_inside_y
    nearest_caption_above = None
    nearest_caption_below = None
    for caption in caption_blocks:
        cb = [int(value) for value in caption.get("block_bbox", [0, 0, 0, 0])]
        if cb[3] <= bbox[1] and (nearest_caption_above is None or cb[3] > nearest_caption_above[3]):
            nearest_caption_above = cb
        if cb[1] >= bbox[3] and (nearest_caption_below is None or cb[1] < nearest_caption_below[1]):
            nearest_caption_below = cb
    media_between_block_and_caption = 0
    media_x_covering_block = 0
    precaption_region = None
    if nearest_caption_below:
        precaption_region = _precaption_media_region(nearest_caption_below, cluster_bboxes)
        for cluster_bbox in cluster_bboxes:
            if cluster_bbox[1] >= nearest_caption_below[1] + 24:
                continue
            if cluster_bbox[3] <= bbox[1] - 24:
                continue
            media_between_block_and_caption += 1
            if (
                cluster_bbox[0] - 24 <= _bbox_center_x(bbox) <= cluster_bbox[2] + 24
                or _bbox_horizontal_overlap_ratio(bbox, cluster_bbox) >= 0.35
            ):
                media_x_covering_block += 1
    if nearest_caption_above:
        caption_gap = bbox[1] - nearest_caption_above[3]
        left_align_gap = abs(bbox[0] - nearest_caption_above[0])
        effective_page_width = max(page_width, width)
        if (
            0 <= caption_gap <= 72
            and left_align_gap <= 80
            and (width >= int(effective_page_width * 0.45))
            and (not stacked_media_above)
        ):
            return False
    if is_body_paragraph_like_text_block(
        block,
        body_column_width=body_column_width,
        cluster_bboxes=cluster_bboxes,
        caption_bbox=nearest_caption_below,
    ):
        return False
    score = 0.0
    if is_subfigure_label(text):
        score += 4.0
    if width <= int(max(body_column_width, 1) * 0.78):
        score += 1.4
    elif width <= int(max(body_column_width, 1) * 0.9):
        score += 0.5
    if label == "paragraph_title" and len(text) <= 24:
        score += 0.8
    if height <= 26:
        score += 0.8
    elif height <= 34:
        score += 0.4
    if page_width and width <= int(page_width * 0.22):
        score += 0.5
    if close_media_count >= 2:
        score += 2.0
    elif close_media_count == 1:
        score += 1.1
    if stacked_media_above and stacked_media_below:
        score += 2.2
    elif stacked_media_above or stacked_media_below:
        score += 0.9
    if side_media:
        score += 1.0
    if nearest_caption_below and nearest_media:
        caption_gap = nearest_caption_below[1] - bbox[3]
        media_gap = min(
            abs(bbox[1] - nearest_media[3]),
            abs(nearest_media[1] - bbox[3]),
            abs(_bbox_center_y(bbox) - _bbox_center_y(nearest_media)),
        )
        if 0 <= caption_gap <= 120 and media_gap <= 80:
            score += 0.8
    if nearest_caption_below:
        caption_gap = nearest_caption_below[1] - bbox[3]
        if 0 <= caption_gap <= 520 and media_between_block_and_caption >= 3:
            score += 0.9
        if 0 <= caption_gap <= 520 and media_x_covering_block >= 2:
            score += 1.3
        if (
            0 <= caption_gap <= 520
            and media_x_covering_block >= 1
            and (width <= int(max(page_width, width) * 0.82))
            and (height <= 96)
        ):
            score += 0.8
        if precaption_region:
            region_overlap = _bbox_horizontal_overlap_ratio(bbox, precaption_region)
            within_region_y = (
                int(precaption_region[1]) - 24 <= int(bbox[1]) <= int(precaption_region[3]) + 24
                and int(bbox[3]) <= int(nearest_caption_below[1]) + 24
            )
            if region_overlap >= 0.55 and within_region_y:
                score += 1.5
            if (
                int(precaption_region[0]) - 24 <= _bbox_center_x(bbox) <= int(precaption_region[2]) + 24
                and within_region_y
                and (media_between_block_and_caption >= 2)
            ):
                score += 1.1
    if len(text) <= 22:
        score += 0.15
    return score >= 2.6


def is_embedded_vision_footnote_block(
    block: dict, blocks: list[dict], page_width: int = 0, page_height: int = 0
) -> bool:
    if block.get("block_label") != "vision_footnote":
        return False
    if is_formal_figure_legend(block.get("block_content", "")):
        return False
    bbox = [int(value) for value in block.get("block_bbox", [0, 0, 0, 0])]
    if _bbox_width(bbox) <= 0 or _bbox_height(bbox) <= 0:
        return False
    composite_regions = compute_precaption_composite_regions(blocks, page_width=page_width, page_height=page_height)
    for region in composite_regions:
        region_bbox = region.get("bbox", [0, 0, 0, 0])
        if _bbox_contains(tuple(region_bbox), tuple(bbox), margin=36):
            return True
    _, clusters = media_clusters(blocks)
    for cluster in clusters:
        cluster_bbox = _cluster_bbox(cluster)
        if _bbox_contains(tuple(cluster_bbox), tuple(bbox), margin=24):
            return True
        if _bbox_horizontal_overlap(bbox, cluster_bbox) > 0 and _bbox_vertical_overlap(bbox, cluster_bbox) > 0:
            return True
        vertical_overlap = _bbox_vertical_overlap(bbox, cluster_bbox)
        near_side = (
            vertical_overlap > 0
            and _bbox_width(bbox) <= 180
            and (0 <= int(cluster_bbox[0]) - int(bbox[2]) <= 60 or 0 <= int(bbox[0]) - int(cluster_bbox[2]) <= 60)
        )
        if near_side:
            return True
    return False


def caption_group_assignments(blocks: list[dict]) -> tuple[dict[int, list[dict]], dict[int, list[dict]]]:
    figure_captions = []
    table_captions = []
    for block in blocks:
        if block.get("block_label") not in {"figure_title", "paragraph_title", "text"}:
            continue
        text = clean_block_text(block.get("block_content", ""))
        if is_numbered_figure_caption(text):
            figure_captions.append(block)
        elif re.match("^(?:Table|Extended\\s+Data\\s+Table|Supplementary\\s+Table)\\s+\\d+", text, flags=re.IGNORECASE):
            table_captions.append(block)
    figure_map: dict[int, list[dict]] = {}
    table_map: dict[int, list[dict]] = {}
    for block in blocks:
        label = block.get("block_label")
        bbox = block.get("block_bbox", [0, 0, 0, 0])
        if label in {"image", "chart"}:
            best_caption = None
            best_distance = None
            for caption in figure_captions:
                cb = caption.get("block_bbox", [0, 0, 0, 0])
                if bbox[1] < cb[1]:
                    horizontal_overlap = _bbox_horizontal_overlap(bbox, cb)
                    center_delta = abs(_bbox_center_x(bbox) - _bbox_center_x(cb))
                    width_gate = max(140, min(_bbox_width(bbox), _bbox_width(cb)) * 0.6)
                    if horizontal_overlap <= 0 and center_delta > width_gate:
                        continue
                    distance = cb[1] - bbox[1]
                    if best_distance is None or distance < best_distance:
                        best_caption = caption
                        best_distance = distance
            if best_caption:
                figure_map.setdefault(best_caption["block_id"], []).append(block)
        elif label == "table":
            best_caption = None
            best_distance = None
            for caption in table_captions:
                cb = caption.get("block_bbox", [0, 0, 0, 0])
                distance = min(abs(bbox[1] - cb[3]), abs(cb[1] - bbox[3]))
                if distance < 260 and (best_distance is None or distance < best_distance):
                    best_caption = caption
                    best_distance = distance
            if best_caption:
                table_map.setdefault(best_caption["block_id"], []).append(block)
    return (figure_map, table_map)


def render_page_blocks(
    vault: Path, page_index: int, result: dict, images_dir: Path, page_cache_dir: Path, pdf_doc=None
) -> list[str]:
    pruned = result.get("prunedResult", {})
    blocks = sorted(pruned.get("parsing_res_list", []), key=block_sort_key)
    raw_reference_blocks = [block for block in blocks if block.get("block_label") == "reference_content"]
    first_reference_y = min(
        (block.get("block_bbox", [0, 10**9, 0, 0])[1] for block in raw_reference_blocks), default=10**9
    )
    ocr_width = int(pruned.get("width", 0) or 0)
    ocr_height = int(pruned.get("height", 0) or 0)
    page_image = render_pdf_page_cached(
        pdf_doc, page_index, ocr_width, ocr_height, page_cache_dir / f"page_{page_index:03d}.png"
    )
    if not page_image:
        page_image = ensure_page_image_cached(
            result.get("inputImage", ""), page_cache_dir / f"page_{page_index:03d}.jpg"
        )
    cluster_index, clusters = media_clusters(blocks)
    figure_caption_map, table_caption_map = caption_group_assignments(blocks)
    composite_regions = compute_precaption_composite_regions(blocks, page_width=ocr_width, page_height=ocr_height)
    composite_by_block_id: dict[int, dict] = {}
    for region in composite_regions:
        region["rendered"] = False
        for block_id in region.get("block_ids", set()):
            composite_by_block_id[block_id] = region
    caption_linked_media_ids = {
        item.get("block_id")
        for media_list in list(figure_caption_map.values()) + list(table_caption_map.values())
        for item in media_list
    }
    rendered: list[str] = [f"<!-- page {page_index} -->"]
    reference_blocks: list[dict] = []
    reference_continuations: list[dict] = []
    footnotes: list[str] = []
    footnote_counter = 0
    rendered_cluster_ids: set[int] = set()
    rendered_caption_media_ids: set[int] = set()
    first_page_meta_done = page_index != 1
    affiliation_buffer: list[str] = []
    deferred_meta: list[str] = []
    for block in blocks:
        label = block.get("block_label", "")
        content = block.get("block_content", "")
        bbox = block.get("block_bbox", [0, 0, 0, 0])
        composite_region = composite_by_block_id.get(block.get("block_id"))
        if composite_region:
            if not composite_region.get("rendered"):
                composite_region["rendered"] = True
                region_bbox = composite_region["bbox"]
                asset_path = (
                    images_dir
                    / "blocks"
                    / f"page_{page_index:03d}_figure_{region_bbox[0]}_{region_bbox[1]}_{region_bbox[2]}_{region_bbox[3]}.jpg"
                )
                if page_image and crop_block_asset(page_image, region_bbox, asset_path):
                    rendered.append(_image_embed_for_obsidian(asset_path.relative_to(vault)))
            continue
        if label in {"header", "header_image", "footer", "footer_image", "number"}:
            continue
        if label == "doc_title":
            rendered.append(f"# {clean_block_text(content)}")
            continue
        if label == "paragraph_title":
            title = clean_block_text(content)
            if (
                title.lower() == "check for updates"
                or is_subfigure_label(title)
                or is_reference_tail_noise_line(title)
                or is_embedded_figure_text_block(block, blocks, page_width=ocr_width, page_height=ocr_height)
            ):
                continue
            if page_index == 1 and affiliation_buffer:
                rendered.extend(affiliation_buffer)
                affiliation_buffer.clear()
            if page_index == 1 and deferred_meta:
                rendered.extend(deferred_meta)
                deferred_meta.clear()
                first_page_meta_done = True
            rendered.append(f"### {title}")
            continue
        if label == "abstract":
            if page_index == 1 and affiliation_buffer:
                rendered.extend(affiliation_buffer)
                affiliation_buffer.clear()
            rendered.append(clean_block_text(content))
            if page_index == 1 and deferred_meta:
                rendered.extend(deferred_meta)
                deferred_meta.clear()
                first_page_meta_done = True
            continue
        if label == "reference_content":
            text = clean_block_text(content)
            if text and (not is_reference_tail_noise_line(text)):
                if parse_reference_number(text) is None:
                    reference_continuations.append(block)
                else:
                    reference_blocks.append(block)
            continue
        if label == "text":
            text = clean_block_text(content)
            if (
                not text
                or is_subfigure_label(text)
                or is_frontmatter_noise_line(text)
                or is_reference_tail_noise_line(text)
                or is_embedded_figure_text_block(block, blocks, page_width=ocr_width, page_height=ocr_height)
            ):
                continue
            if raw_reference_blocks and bbox[1] >= first_reference_y - 10:
                reference_continuations.append(block)
                continue
            if is_numbered_figure_caption(text):
                linked_media = figure_caption_map.get(block.get("block_id"), []) or table_caption_map.get(
                    block.get("block_id"), []
                )
                if linked_media and page_image:
                    rendered_caption_media_ids.update(item.get("block_id") for item in linked_media)
                    union_bbox = [
                        min(item["block_bbox"][0] for item in linked_media),
                        min(item["block_bbox"][1] for item in linked_media),
                        max(item["block_bbox"][2] for item in linked_media),
                        max(item["block_bbox"][3] for item in linked_media),
                    ]
                    asset_kind = "figure" if block.get("block_id") in figure_caption_map else "table"
                    asset_path = (
                        images_dir
                        / "blocks"
                        / f"page_{page_index:03d}_{asset_kind}_{union_bbox[0]}_{union_bbox[1]}_{union_bbox[2]}_{union_bbox[3]}.jpg"
                    )
                    if crop_block_asset(page_image, union_bbox, asset_path):
                        rendered.append(_image_embed_for_obsidian(asset_path.relative_to(vault)))
                    if asset_kind == "table":
                        for item in linked_media:
                            if item.get("block_label") == "table" and item.get("block_content"):
                                rendered.append(clean_block_text(item.get("block_content", "")))
                                break
                rendered.append(text)
                continue
            if page_index == 1 and (not first_page_meta_done):
                if handle_first_page_metadata_lines(text, rendered, affiliation_buffer, deferred_meta, footnotes):
                    continue
            rendered.append(text)
            continue
        if label == "display_formula":
            formula = clean_block_text(content)
            formula = formula.strip()
            if formula.startswith("$$") and formula.endswith("$$") and (len(formula) >= 4):
                formula = formula[2:-2].strip()
            rendered.append(f"$$\n{formula}\n$$")
            continue
        if label == "formula_number":
            rendered.append(clean_block_text(content))
            continue
        if label in {"table", "image", "chart"}:
            if block.get("block_id") in caption_linked_media_ids:
                continue
            if block.get("block_id") in rendered_caption_media_ids:
                continue
            if label in {"image", "chart"}:
                cluster_id = cluster_index.get(block.get("block_id", -1))
                if cluster_id is None or cluster_id in rendered_cluster_ids:
                    continue
                rendered_cluster_ids.add(cluster_id)
                cluster_blocks = clusters[cluster_id]
                bbox = [
                    min(item["block_bbox"][0] for item in cluster_blocks),
                    min(item["block_bbox"][1] for item in cluster_blocks),
                    max(item["block_bbox"][2] for item in cluster_blocks),
                    max(item["block_bbox"][3] for item in cluster_blocks),
                ]
                asset_name = f"page_{page_index:03d}_figure_{bbox[0]}_{bbox[1]}_{bbox[2]}_{bbox[3]}.jpg"
            else:
                asset_name = f"page_{page_index:03d}_{label}_{bbox[0]}_{bbox[1]}_{bbox[2]}_{bbox[3]}.jpg"
            asset_path = images_dir / "blocks" / asset_name
            if page_image and crop_block_asset(page_image, bbox, asset_path):
                rendered.append(_image_embed_for_obsidian(asset_path.relative_to(vault)))
            if label == "table" and content:
                rendered.append(clean_block_text(content))
            continue
        if label == "figure_title":
            caption_text = clean_block_text(content)
            if is_subfigure_label(caption_text):
                continue
            if not is_formal_figure_legend(caption_text):
                continue
            linked_media = figure_caption_map.get(block.get("block_id"), []) or table_caption_map.get(
                block.get("block_id"), []
            )
            if linked_media and page_image:
                rendered_caption_media_ids.update(item.get("block_id") for item in linked_media)
                union_bbox = [
                    min(item["block_bbox"][0] for item in linked_media),
                    min(item["block_bbox"][1] for item in linked_media),
                    max(item["block_bbox"][2] for item in linked_media),
                    max(item["block_bbox"][3] for item in linked_media),
                ]
                asset_kind = "figure" if block.get("block_id") in figure_caption_map else "table"
                asset_path = (
                    images_dir
                    / "blocks"
                    / f"page_{page_index:03d}_{asset_kind}_{union_bbox[0]}_{union_bbox[1]}_{union_bbox[2]}_{union_bbox[3]}.jpg"
                )
                if crop_block_asset(page_image, union_bbox, asset_path):
                    rendered.append(_image_embed_for_obsidian(asset_path.relative_to(vault)))
                if asset_kind == "table":
                    for item in linked_media:
                        if item.get("block_label") == "table" and item.get("block_content"):
                            rendered.append(clean_block_text(item.get("block_content", "")))
                            break
            rendered.append(caption_text)
            continue
        if label == "vision_footnote":
            if is_formal_figure_legend(content):
                rendered.append(clean_block_text(content))
                continue
            if is_embedded_vision_footnote_block(block, blocks, page_width=ocr_width, page_height=ocr_height):
                continue
            entries = parse_vision_footnote_entries(content)
            marker_to_id = {}
            for marker, body in entries:
                footnote_counter += 1
                footnote_id = f"p{page_index}-fn{footnote_counter}"
                marker_to_id[marker] = footnote_id
                footnotes.append(f"[^{footnote_id}]: {body or clean_block_text(content)}")
            if rendered and marker_to_id:
                last = rendered[-1]
                if last.startswith("<table>"):
                    rendered[-1] = attach_table_footnotes(last, marker_to_id)
                else:
                    for marker, footnote_id in marker_to_id.items():
                        rendered[-1] = attach_footnote_reference(rendered[-1], marker, footnote_id)
            continue
    if footnotes:
        rendered.append("")
        rendered.extend(footnotes)
    rendered = dedupe_page_media_lines(rendered)
    if reference_blocks:
        rendered.append("")
        ordered_reference_blocks = sort_reference_blocks(reference_blocks)
        continuation_map: dict[int, list[str]] = {}
        sorted_continuations = sorted(reference_continuations, key=block_sort_key)
        assigned_continuation_indexes: set[int] = set()
        incomplete_reference_indexes = [
            index
            for index, block in enumerate(ordered_reference_blocks)
            if clean_block_text(block.get("block_content", "")).rstrip().endswith(":")
        ]
        for index, continuation in zip(incomplete_reference_indexes, sorted_continuations, strict=False):
            continuation_text = clean_block_text(continuation.get("block_content", ""))
            if continuation_text:
                continuation_map.setdefault(index, []).append(continuation_text)
                assigned_continuation_indexes.add(id(continuation))
        for continuation in sorted_continuations:
            if id(continuation) in assigned_continuation_indexes:
                continue
            target_index = assign_reference_continuation(continuation, ordered_reference_blocks)
            if target_index is None:
                continue
            continuation_map.setdefault(target_index, []).append(
                clean_block_text(continuation.get("block_content", ""))
            )
            assigned_continuation_indexes.add(id(continuation))
        unassigned_continuations = [
            clean_block_text(continuation.get("block_content", ""))
            for continuation in sorted_continuations
            if id(continuation) not in assigned_continuation_indexes
        ]
        for index, block in enumerate(ordered_reference_blocks):
            text = clean_block_text(block.get("block_content", ""))
            if text:
                rendered.append(text)
            for continuation_text in continuation_map.get(index, []):
                if continuation_text:
                    rendered.append(continuation_text)
            if text.rstrip().endswith(":") and unassigned_continuations:
                rendered.append(unassigned_continuations.pop(0))
    return [part for part in rendered if part]


def postprocess_ocr_result(vault: Path, key: str, all_results: list[dict]) -> tuple[int, str, str, str]:
    paths = pipeline_paths(vault)
    ocr_root = paths["ocr"] / key
    json_dir = ocr_root / "json"
    images_dir = ocr_root / "images"
    page_cache_dir = ocr_root / "pages"
    meta_path = ocr_root / "meta.json"
    json_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    page_cache_dir.mkdir(parents=True, exist_ok=True)
    page_num = 0
    merged_parts = []
    meta = read_json(meta_path) if meta_path.exists() else {}
    source_pdf = Path(meta.get("source_pdf", "")) if meta.get("source_pdf") else None
    pdf_doc = None
    try:
        if source_pdf and source_pdf.exists():
            pdf_doc = fitz.open(str(source_pdf))
        for page_payload in all_results:
            for res in page_payload.get("layoutParsingResults", []):
                page_num += 1
                merged_parts.append(
                    "\n\n".join(render_page_blocks(vault, page_num, res, images_dir, page_cache_dir, pdf_doc=pdf_doc))
                )
    finally:
        if pdf_doc is not None:
            pdf_doc.close()
    write_json(json_dir / "result.json", all_results)
    fulltext_path = ocr_root / "fulltext.md"
    fulltext_path.write_text("\n\n".join(merged_parts).strip() + "\n", encoding="utf-8")
    markdown_dir = ocr_root / "markdown"
    if markdown_dir.exists():
        shutil.rmtree(markdown_dir)
    markdown_path = str(fulltext_path.relative_to(vault)).replace("\\", "/") if page_num else ""
    json_path = str((json_dir / "result.json").relative_to(vault)).replace("\\", "/")
    fulltext_md_path = str(fulltext_path.resolve())
    return (page_num, markdown_path, json_path, fulltext_md_path)


def run_ocr(vault: Path, verbose: bool = False, no_progress: bool = False) -> int:
    from paperforge.pdf_resolver import resolve_pdf_path

    paths = pipeline_paths(vault)
    cleanup_blocked_ocr_dirs(paths)

    # Zombie reset: reset stale processing jobs to pending
    zombie_timeout = int(os.environ.get("PAPERFORGE_ZOMBIE_TIMEOUT_MINUTES", "30"))
    ocr_root = paths.get("ocr")
    if ocr_root and ocr_root.exists():
        for meta_dir in ocr_root.iterdir():
            meta_path = meta_dir / "meta.json"
            if not meta_path.exists():
                continue
            try:
                meta = read_json(meta_path)
            except Exception:
                continue
            zkey = meta.get("zotero_key", meta_dir.name)
            zstatus = str(meta.get("ocr_status", "") or "").strip().lower()
            if zstatus in {"queued", "running"}:
                zstarted = meta.get("ocr_started_at", "")
                if zstarted:
                    try:
                        started_dt = datetime.fromisoformat(zstarted)
                        if (datetime.now(timezone.utc) - started_dt).total_seconds() > zombie_timeout * 60:
                            meta["ocr_status"] = "pending"
                            meta["retry_count"] = int(meta.get("retry_count", 0)) + 1
                            write_json(meta_path, meta)
                            logger.warning(
                                "Zombie reset %s: was %s, started at %s, reset to pending", zkey, zstatus, zstarted
                            )
                    except Exception:
                        pass

    control_actions = load_control_actions(paths)
    target_keys = {key for key, action in control_actions.items() if action.get("do_ocr", False)}
    target_rows = []
    for export_path in sorted(paths["exports"].glob("*.json")):
        for item in load_export_rows(export_path):
            if item["key"] not in target_keys:
                continue
            pdf_attachments = [a for a in item.get("attachments", []) if a.get("contentType") == "application/pdf"]
            target_rows.append(
                {
                    "zotero_key": item["key"],
                    "has_pdf": bool(pdf_attachments),
                    "pdf_path": pdf_attachments[0]["path"] if pdf_attachments else "",
                }
            )
    for row in target_rows:
        key = row["zotero_key"]
        meta = ensure_ocr_meta(vault, row)
        if str(meta.get("ocr_status", "") or "").strip().lower() == "error":
            meta["ocr_status"] = "pending"
            meta["ocr_job_id"] = ""
            meta["ocr_started_at"] = ""
            meta["ocr_finished_at"] = ""
            meta["retry_count"] = 0
            write_json(paths["ocr"] / key / "meta.json", meta)
        status, _error = validate_ocr_meta(paths, meta)
        if status == "done_incomplete":
            meta["ocr_status"] = "pending"
            meta["ocr_job_id"] = ""
            meta["ocr_started_at"] = ""
            meta["ocr_finished_at"] = ""
            meta["error"] = _error
            meta["retry_count"] = 0
            write_json(paths["ocr"] / key / "meta.json", meta)
    ocr_queue = sync_ocr_queue(paths, target_rows)
    max_items_raw = os.environ.get("PADDLEOCR_MAX_ITEMS", "").strip()
    max_items = 3
    if max_items_raw:
        try:
            max_items = max(1, int(max_items_raw))
        except ValueError:
            max_items = 3
    token = os.environ.get("PADDLEOCR_API_TOKEN", "").strip()
    if not token:
        token = os.environ.get("PADDLEOCR_API_TOKEN_USER", "").strip()
    if not token:
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as env_key:
                token = str(winreg.QueryValueEx(env_key, "PADDLEOCR_API_TOKEN")[0]).strip()
        except Exception:
            token = ""
    if not token:
        # Fallback: parse vault-root .env
        token = _read_dotenv(vault, "PADDLEOCR_API_TOKEN")
    job_url = os.environ.get("PADDLEOCR_JOB_URL", "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs").strip()
    model = os.environ.get("PADDLEOCR_MODEL", "PaddleOCR-VL-1.5").strip()
    optional_payload = {"useDocOrientationClassify": False, "useDocUnwarping": False, "useChartRecognition": False}
    changed = 0
    active_submitted = 0
    queue_changed = False
    _submitted: set[str] = set()  # keys newly uploaded in this run

    def _do_poll(job_id: str, token_val: str) -> requests.Response:
        resp = requests.get(f"{job_url}/{job_id}", headers={"Authorization": f"bearer {token_val}"}, timeout=60)
        resp.raise_for_status()
        return resp

    for queue_row in progress_bar(ocr_queue, desc="Processing OCR", disable=no_progress):
        key = queue_row["zotero_key"]
        meta = ensure_ocr_meta(vault, queue_row)
        status = str(meta.get("ocr_status", "pending") or "pending").strip().lower()
        queue_row["queue_status"] = status
        if status == "done":
            queue_changed = True
            continue
        if status in {"queued", "running"} and meta.get("ocr_job_id"):
            active_submitted += 1
            if not token:
                continue
            meta_path_poll = paths["ocr"] / key / "meta.json"
            try:
                response = retry_with_meta(_do_poll, meta_path_poll, meta["ocr_job_id"], token)
            except Exception as e:
                meta["ocr_status"] = "pending"
                meta["error"] = str(e)
                meta["last_error"] = str(e)
                meta["retry_count"] = int(meta.get("retry_count", 0)) + 1
                queue_row["queue_status"] = "pending"
                write_json(paths["ocr"] / key / "meta.json", meta)
                changed += 1
                active_submitted = max(0, active_submitted - 1)
                continue
            try:
                payload = response.json()["data"]
                state = payload["state"]
            except (json.JSONDecodeError, KeyError) as e:
                meta["ocr_status"] = "pending"
                meta["error"] = f"API schema mismatch during polling: {e}"
                meta["last_error"] = meta["error"]
                meta["raw_response"] = response.text[:1000]
                meta["retry_count"] = int(meta.get("retry_count", 0)) + 1
                queue_row["queue_status"] = "pending"
                write_json(paths["ocr"] / key / "meta.json", meta)
                changed += 1
                active_submitted = max(0, active_submitted - 1)
                continue
            if state in {"pending", "running"}:
                meta["ocr_status"] = state
                queue_row["queue_status"] = state
                meta["error"] = ""
            elif state == "done":
                try:
                    result_url = payload["resultUrl"]["jsonUrl"]
                    result_response = requests.get(result_url, timeout=120)
                    result_response.raise_for_status()
                    lines = [line.strip() for line in result_response.text.splitlines() if line.strip()]
                    all_results = []
                    for line in lines:
                        page_payload = json.loads(line)["result"]
                        all_results.append(page_payload)
                    page_num, markdown_path, json_path, fulltext_md_path = postprocess_ocr_result(
                        vault, key, all_results
                    )
                except Exception as e:
                    meta["ocr_status"] = "pending"
                    meta["error"] = str(e)
                    meta["retry_count"] = int(meta.get("retry_count", 0)) + 1
                    queue_row["queue_status"] = "pending"
                    write_json(paths["ocr"] / key / "meta.json", meta)
                    changed += 1
                    active_submitted = max(0, active_submitted - 1)
                    continue
                meta["ocr_status"] = "done"
                # Per D-01: auto_analyze_after_ocr opt-in workflow streamlining
                cfg_path = vault / "paperforge.json"
                if cfg_path.exists():
                    try:
                        pf_cfg = read_json(cfg_path)
                        if pf_cfg.get("auto_analyze_after_ocr", False):
                            note_glob = list(paths["literature"].rglob(f"{key}.md"))
                            if not note_glob:
                                note_glob = list(paths["literature"].rglob(f"{key} - *.md"))
                            if note_glob:
                                note_path = max(note_glob, key=lambda p: len(p.parents))
                                text = note_path.read_text(encoding="utf-8")
                                text = re.sub(
                                    r"^analyze:.*$",
                                    "analyze: true",
                                    text,
                                    count=1,
                                    flags=re.MULTILINE,
                                )
                                note_path.write_text(text, encoding="utf-8")
                    except Exception:
                        logger.warning("auto_analyze_after_ocr: failed for %s", key, exc_info=True)
                meta["ocr_finished_at"] = datetime.now(timezone.utc).isoformat()
                meta["page_count"] = page_num
                meta["markdown_path"] = markdown_path
                meta["json_path"] = json_path
                meta["fulltext_md_path"] = fulltext_md_path
                meta["error"] = ""
                queue_row["queue_status"] = "done"
                queue_changed = True
                active_submitted = max(0, active_submitted - 1)
            else:
                meta["ocr_status"] = "error"
                meta["error"] = payload.get("errorMsg", "Unknown OCR failure")
                meta["library_record"] = key
                queue_row["queue_status"] = "error"
                active_submitted = max(0, active_submitted - 1)
            write_json(paths["ocr"] / key / "meta.json", meta)
            changed += 1

    # Upload pending items in batches until none remain (processes all do_ocr items, not just max_items)
    def _do_upload(token_val: str, pdf_path: Path) -> requests.Response:
        with open(pdf_path, "rb") as file_handle:
            resp = requests.post(
                job_url,
                headers={"Authorization": f"bearer {token_val}"},
                data={"model": model, "optionalPayload": json.dumps(optional_payload)},
                files={"file": file_handle},
                timeout=120,
            )
        resp.raise_for_status()
        return resp

    # Combined upload + poll loop: process all items in batches up to max_items concurrency
    import time as _time

    poll_interval = int(os.environ.get("PAPERFORGE_POLL_INTERVAL", "15"))
    max_poll_cycles = int(os.environ.get("PAPERFORGE_POLL_MAX_CYCLES", "60"))
    _completed_count = 0
    _failed_count = 0
    _token_warned = False
    for _cycle in range(max_poll_cycles):
        remaining = [r for r in ocr_queue if r.get("queue_status", "") not in ("done", "nopdf", "blocked")]
        if not remaining:
            break
        available_slots = max(0, max_items - active_submitted)
        if available_slots > 0:
            upload_items = [r for r in remaining if r.get("queue_status", "") not in ("queued", "running")][
                :available_slots
            ]
            for queue_row in upload_items:
                key = queue_row["zotero_key"]
                meta = ensure_ocr_meta(vault, queue_row)
                _sanitized_temp = None
                status = str(meta.get("ocr_status", "pending") or "pending").strip().lower()
                if status in {"done", "queued", "running"}:
                    continue
                resolved_pdf = resolve_pdf_path(
                    queue_row.get("pdf_path", ""),
                    queue_row.get("has_pdf", False),
                    vault,
                    paths.get("zotero_dir") if "zotero_dir" in paths else None,
                )
                if not resolved_pdf:
                    meta["ocr_status"] = "nopdf"
                    queue_row["queue_status"] = "nopdf"
                    write_json(paths["ocr"] / key / "meta.json", meta)
                    changed += 1
                    print(f"OCR: {key} skipped (PDF not found)", flush=True)
                    continue
                if not token:
                    meta["ocr_status"] = "blocked"
                    queue_row["queue_status"] = "blocked"
                    write_json(paths["ocr"] / key / "meta.json", meta)
                    changed += 1
                    if not _token_warned:
                        print("OCR: no API token configured — set PADDLEOCR_API_TOKEN in .env", flush=True)
                        _token_warned = True
                    continue
                upload_pdf = resolved_pdf
                if meta.get("needs_sanitize"):
                    try:
                        import tempfile

                        doc = fitz.open(str(resolved_pdf))
                        _sanitized_temp = Path(tempfile.mktemp(suffix=".pdf"))
                        doc.save(str(_sanitized_temp), garbage=4, deflate=True, clean=True)
                        doc.close()
                        upload_pdf = _sanitized_temp
                        meta["needs_sanitize"] = False
                    except Exception:
                        pass
                if int(meta.get("retry_count", 0)) >= 3:
                    meta["ocr_status"] = "error"
                    meta["error"] = meta.get("error", "") or "Upload failed after 3 retries"
                    queue_row["queue_status"] = "error"
                    write_json(paths["ocr"] / key / "meta.json", meta)
                    changed += 1
                    continue
                print(f"OCR: {key} uploading to PaddleOCR...", flush=True)
                try:
                    response = retry_with_meta(_do_upload, paths["ocr"] / key / "meta.json", token, upload_pdf)
                    meta["ocr_job_id"] = response.json()["data"]["jobId"]
                except Exception as e:
                    if _sanitized_temp is not None and _sanitized_temp.exists():
                        _sanitized_temp.unlink(missing_ok=True)
                    import requests as _requests

                    if isinstance(e, _requests.exceptions.HTTPError):
                        _status = getattr(getattr(e, "response", None), "status_code", 0)
                        if _status == 401:
                            meta["ocr_status"] = "blocked"
                            meta["error"] = "PaddleOCR token invalid"
                            meta["retry_count"] = 3
                            queue_row["queue_status"] = "blocked"
                            write_json(paths["ocr"] / key / "meta.json", meta)
                            changed += 1
                            print(f"OCR: {key} blocked (invalid API token)", flush=True)
                            continue
                    if isinstance(e, FileNotFoundError):
                        meta["ocr_status"] = "nopdf"
                        meta["error"] = "PDF not found"
                        queue_row["queue_status"] = "nopdf"
                        write_json(paths["ocr"] / key / "meta.json", meta)
                        changed += 1
                        continue
                    retry_count = int(meta.get("retry_count", 0)) + 1
                    meta["retry_count"] = retry_count
                    meta["error"] = str(e)
                    meta["last_error"] = str(e)
                    meta["ocr_status"] = "pending"
                    queue_row["queue_status"] = "pending"
                    write_json(paths["ocr"] / key / "meta.json", meta)
                    changed += 1
                    print(f"OCR: {key} upload failed (retry {retry_count}/3): {e}", flush=True)
                    continue
                meta["ocr_status"] = "queued"
                meta["ocr_started_at"] = datetime.now(timezone.utc).isoformat()
                meta["error"] = ""
                queue_row["queue_status"] = "queued"
                write_json(paths["ocr"] / key / "meta.json", meta)
                changed += 1
                active_submitted += 1
                print(f"OCR: {key} queued (job {meta['ocr_job_id']})", flush=True)
            if _sanitized_temp is not None and _sanitized_temp.exists():
                _sanitized_temp.unlink(missing_ok=True)
        poll_items = [r for r in remaining if r.get("queue_status") in ("queued", "running")]
        for queue_row in poll_items:
            key = queue_row["zotero_key"]
            meta = ensure_ocr_meta(vault, queue_row)
            job_id = meta.get("ocr_job_id", "")
            if not job_id:
                continue
            try:
                response = retry_with_meta(_do_poll, paths["ocr"] / key / "meta.json", job_id, token)
                payload = response.json()["data"]
                state = payload["state"]
            except Exception:
                continue
            if state == "done":
                try:
                    result_url = payload["resultUrl"]["jsonUrl"]
                    result_response = requests.get(result_url, timeout=120)
                    if result_response.status_code == 404:
                        meta["ocr_status"] = "pending"
                        meta["ocr_job_id"] = ""
                        meta["needs_sanitize"] = True
                        meta["error"] = "Result object not found on provider (404)"
                        meta["retry_count"] = 0
                        queue_row["queue_status"] = "pending"
                        write_json(paths["ocr"] / key / "meta.json", meta)
                        changed += 1
                        active_submitted = max(0, active_submitted - 1)
                        print(f"OCR: {key} result expired, will retry", flush=True)
                        continue
                    result_response.raise_for_status()
                    lines = [l.strip() for l in result_response.text.splitlines() if l.strip()]
                    results = [json.loads(l)["result"] for l in lines]
                    page_num, md_path, json_path, fulltext_md_path = postprocess_ocr_result(vault, key, results)
                except Exception:
                    continue
                meta["ocr_status"] = "done"
                meta["ocr_finished_at"] = datetime.now(timezone.utc).isoformat()
                meta["page_count"] = page_num
                meta["markdown_path"] = md_path
                meta["json_path"] = json_path
                meta["fulltext_md_path"] = fulltext_md_path
                meta["error"] = ""
                queue_row["queue_status"] = "done"
                queue_changed = True
                active_submitted = max(0, active_submitted - 1)
                _completed_count += 1
                print(f"OCR: {key} completed ({page_num} pages)", flush=True)
            elif state in ("error", "failed"):
                meta["error"] = payload.get("errorMsg", "Unknown OCR failure")
                meta["ocr_status"] = "queued"
                queue_row["queue_status"] = "queued"
                _failed_count += 1
                print(f"OCR: {key} failed: {meta['error']}", flush=True)
            else:
                meta["ocr_status"] = state
                queue_row["queue_status"] = state
            write_json(paths["ocr"] / key / "meta.json", meta)
            changed += 1
        if any(r.get("queue_status") in ("queued", "running") for r in ocr_queue):
            _time.sleep(poll_interval)
    # Collect completed OCR keys for incremental index refresh (before filtering)
    _done_ocr_keys = (
        [r.get("zotero_key", "") for r in ocr_queue if r.get("queue_status") == "done"] if queue_changed else []
    )
    if queue_changed:
        ocr_queue = [row for row in ocr_queue if str(row.get("queue_status", "")).lower() != "done"]
    write_ocr_queue(paths, ocr_queue)
    # Determine exit code: 0 = all settled, 1 = some items still pending
    final_remaining = [r for r in ocr_queue if r.get("queue_status", "") not in ("done", "nopdf", "blocked", "error")]
    pending_keys = [r["zotero_key"] for r in final_remaining]
    final_statuses = {r["zotero_key"]: r.get("queue_status", "?") for r in ocr_queue}
    done_count = sum(1 for s in final_statuses.values() if s == "done")
    failed_count = sum(1 for s in final_statuses.values() if s in ("error", "blocked"))
    pending_count = len(final_remaining)

    summary_parts = []
    if done_count:
        summary_parts.append(f"done={done_count}")
    if failed_count:
        summary_parts.append(f"failed={failed_count}")
    if pending_count:
        summary_parts.append(f"pending={pending_count} ({', '.join(pending_keys)})")
    print(f"OCR: {' '.join(summary_parts) if summary_parts else 'no items processed'}", flush=True)
    if pending_keys:
        print("OCR: re-run to continue polling incomplete items", flush=True)

    try:
        _sync.run_selection_sync(vault)
        if _done_ocr_keys:
            done_keys = [k for k in _done_ocr_keys if k]
            for ocr_key in done_keys:
                refresh_index_entry(vault, ocr_key)
            if verbose:
                print(f"ocr: refreshed {len(done_keys)} index entries incrementally")
        else:
            _sync.run_index_refresh(vault)
    except ImportError:
        _sync.run_index_refresh(vault)
    except Exception as e:
        logger.error("Post-OCR index refresh failed: %s", e)
    print(f"ocr: updated {changed} records")
    return 1 if pending_keys else 0
