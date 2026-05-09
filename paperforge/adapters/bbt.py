from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _normalize_attachment_path(path: str, zotero_dir: Path | None = None) -> tuple[str, str, str]:
    """Normalize a BBT attachment path to a consistent storage: format.

    Handles three real-world BBT export formats:
    1. Absolute Windows paths: D:\\...\\Zotero\\storage\\8CHARKEY\\filename.pdf
       -> storage:8CHARKEY/filename.pdf
    2. storage: prefix: storage:KEY/filename.pdf -> pass through
    3. Bare relative: KEY/filename.pdf -> storage:KEY/filename.pdf

    Args:
        path: Raw path from BBT JSON attachment.
        zotero_dir: Optional absolute path to Zotero data directory for
            validating absolute paths.

    Returns:
        Tuple of (normalized_path, bbt_path_raw, zotero_storage_key).
        normalized_path uses forward slashes and storage: prefix for
        Zotero storage paths. bbt_path_raw preserves the original input
        for debugging. zotero_storage_key is the 8-character Zotero key.
    """
    raw = str(path or "").strip()
    if not raw:
        return ("", "", "")

    bbt_path_raw = raw

    # Format 2: Already has storage: prefix — pass through with slash normalization
    if raw.startswith("storage:"):
        storage_rel = raw[len("storage:") :].lstrip("/").lstrip("\\")
        storage_rel = storage_rel.replace("\\", "/")
        parts = storage_rel.split("/")
        zotero_storage_key = parts[0] if parts else ""
        return (f"storage:{storage_rel}", bbt_path_raw, zotero_storage_key)

    # Format 1: Absolute Windows path pointing to Zotero storage
    candidate = Path(raw)
    if candidate.is_absolute():
        norm_path = raw.replace("\\", "/")
        # Detect Zotero storage pattern: .../storage/8CHARKEY/...
        if "/storage/" in norm_path:
            parts_after_storage = norm_path.split("/storage/", 1)[1]
            parts = parts_after_storage.split("/")
            if len(parts) >= 2 and len(parts[0]) == 8 and parts[0].isalnum():
                zotero_storage_key = parts[0]
                filename = "/".join(parts[1:])
                return (f"storage:{zotero_storage_key}/{filename}", bbt_path_raw, zotero_storage_key)
        # Absolute path but not in Zotero storage — mark as absolute
        return (f"absolute:{raw}", bbt_path_raw, "")

    # Format 3: Bare relative path — prepend storage: prefix
    norm = raw.replace("\\", "/")
    parts = norm.split("/")
    zotero_storage_key = parts[0] if parts else ""
    return (f"storage:{norm}", bbt_path_raw, zotero_storage_key)


def _identify_main_pdf(attachments: list[dict]) -> tuple[dict | None, list[dict]]:
    """Identify the main PDF and supplementary materials from attachments.

    Uses a hybrid three-priority strategy (Decision D-02):
    1. Primary: attachment.title == "PDF" AND contentType == "application/pdf"
    2. Fallback heuristic: largest file by size (if available), else shortest title
    3. Final fallback: first PDF attachment in the list

    Args:
        attachments: List of attachment dicts from load_export_rows().

    Returns:
        Tuple of (main_pdf_attachment, supplementary_attachments).
        main_pdf_attachment may be None if no PDFs found.
        supplementary_attachments is a list of all other PDF attachments.
    """
    pdf_attachments = [a for a in attachments if isinstance(a, dict) and a.get("contentType") == "application/pdf"]

    if not pdf_attachments:
        return (None, [])

    # Priority 1: Title exactly equals "PDF"
    for att in pdf_attachments:
        if att.get("title") == "PDF":
            main = att
            supplementary = [a for a in pdf_attachments if a is not main]
            return (main, supplementary)

    # Priority 2: Largest file by size (if size field is available and differentiated)
    sized = [(a, a.get("size", 0) or 0) for a in pdf_attachments]
    sized.sort(key=lambda x: x[1], reverse=True)
    if sized and sized[0][1] > 0 and (len(sized) == 1 or sized[0][1] > sized[1][1]):
        main = sized[0][0]
        supplementary = [a for a in pdf_attachments if a is not main]
        return (main, supplementary)

    # Priority 2b (sizes equal or unavailable): shortest title
    titled = [(a, len(str(a.get("title", "")))) for a in pdf_attachments]
    titled.sort(key=lambda x: x[1])
    main = titled[0][0]
    supplementary = [a for a in pdf_attachments if a is not main]
    return (main, supplementary)


def extract_authors(item: dict) -> list[str]:
    authors = []
    for creator in item.get("creators", []):
        if creator.get("creatorType") != "author":
            continue
        full_name = " ".join(
            part for part in [creator.get("firstName", ""), creator.get("lastName", "")] if part
        ).strip()
        if full_name:
            authors.append(full_name)
        elif creator.get("name"):
            authors.append(creator["name"])
    return authors


def collection_fields(collection_paths: list[str]) -> dict[str, str | list[str]]:
    paths = [path for path in collection_paths if path]
    primary = paths[0] if paths else ""
    if paths:
        primary = sorted(paths, key=lambda value: (value.count("/"), len(value), value), reverse=True)[0]
    tags = []
    seen = set()
    for path in paths:
        for part in [segment.strip() for segment in path.split("/") if segment.strip()]:
            if part not in seen:
                seen.add(part)
                tags.append(part)
    group = primary
    return {"collections": paths, "collection_tags": tags, "collection_group": [group] if group else []}


def resolve_item_collection_paths(item: dict, collection_lookup: dict) -> list[str]:
    paths = []
    collection_keys = item.get("collections") or []
    if collection_keys:
        for key in collection_keys:
            paths.append(collection_lookup.get("path_by_key", {}).get(key, key))
    item_id = item.get("itemID")
    if item_id is not None:
        paths.extend(collection_lookup.get("paths_by_item_id", {}).get(item_id, []))
    return sorted({path for path in paths if path}, key=lambda value: (-value.count("/"), value))


def load_export_rows(path: Path) -> list[dict]:
    from paperforge.worker._domain import build_collection_lookup
    from paperforge.worker._utils import _extract_year, read_json

    data = read_json(path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        collection_lookup = build_collection_lookup(data.get("collections", {}))
        rows = []
        for item in data["items"]:
            if item.get("itemType") in {"attachment", "note", "annotation"}:
                continue
            attachments = []
            for attachment in item.get("attachments", []):
                if not isinstance(attachment, dict):
                    continue
                raw_path = attachment.get("path", "")
                normalized_path, bbt_path_raw, zotero_storage_key = _normalize_attachment_path(raw_path)
                # Preserve contentType from BBT if present; fallback to file extension
                content_type = attachment.get("contentType", "")
                if not content_type and str(normalized_path).lower().endswith(".pdf"):
                    content_type = "application/pdf"
                attachments.append(
                    {
                        "path": normalized_path,
                        "contentType": content_type,
                        "title": attachment.get("title", ""),
                        "bbt_path_raw": bbt_path_raw,
                        "zotero_storage_key": zotero_storage_key,
                        "size": attachment.get("size", 0) or 0,
                    }
                )
            main_pdf, supplementary_pdfs = _identify_main_pdf(attachments)
            pdf_path = main_pdf["path"] if main_pdf else ""
            bbt_path_raw = main_pdf["bbt_path_raw"] if main_pdf else ""
            zotero_storage_key = main_pdf["zotero_storage_key"] if main_pdf else ""
            path_error = "not_found" if not main_pdf else ""
            supplementary = [a["path"] for a in supplementary_pdfs] if supplementary_pdfs else []
            attachment_count = len(attachments)
            rows.append(
                {
                    "key": item.get("key") or item.get("itemKey", ""),
                    "title": item.get("title", ""),
                    "authors": extract_authors(item),
                    "creators": item.get("creators", []),
                    "abstract": item.get("abstractNote", ""),
                    "journal": item.get("publicationTitle", ""),
                    "extra": item.get("extra", ""),
                    "year": _extract_year(item.get("date", "")),
                    "date": item.get("date", ""),
                    "doi": item.get("DOI", ""),
                    "pmid": item.get("PMID", ""),
                    "collections": resolve_item_collection_paths(item, collection_lookup),
                    "attachments": attachments,
                    "pdf_path": pdf_path,
                    "supplementary": supplementary,
                    "attachment_count": attachment_count,
                    "bbt_path_raw": bbt_path_raw,
                    "zotero_storage_key": zotero_storage_key,
                    "path_error": path_error,
                }
            )
        return rows
    raise ValueError(f"Unsupported export format: {path}")
