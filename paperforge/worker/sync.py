from __future__ import annotations

import html
import logging
import os
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import requests

from paperforge.config import load_vault_config, paperforge_paths
from paperforge.worker._domain import build_collection_lookup, load_domain_config, load_domain_collections
from paperforge.worker._utils import (
    _extract_year,
    lookup_impact_factor,
    pipeline_paths,
    read_json,
    read_jsonl,
    slugify_filename,
    write_json,
    write_jsonl,
    yaml_block,
    yaml_list,
    yaml_quote,
)

import paperforge.worker.asset_index as asset_index

logger = logging.getLogger(__name__)


def _read_frontmatter_bool_from_text(text: str, key: str, default: bool = False) -> bool:
    match = re.search(rf"^{re.escape(key)}:\s*(?:[\"'])?(true|false)(?:[\"'])?\s*$", text, re.MULTILINE | re.IGNORECASE)
    if not match:
        return default
    return match.group(1).lower() == "true"


def _read_frontmatter_optional_bool_from_text(text: str, key: str) -> Optional[bool]:
    match = re.search(rf"^{re.escape(key)}:\s*(?:[\"'])?(true|false)(?:[\"'])?\s*$", text, re.MULTILINE | re.IGNORECASE)
    if not match:
        return None
    return match.group(1).lower() == "true"


def _legacy_control_flags(paths: dict[str, Path], zotero_key: str) -> dict[str, Optional[bool]]:
    records_root = paths.get("library_records")
    if not records_root or not records_root.exists():
        return {"do_ocr": None, "analyze": None}
    for record_path in records_root.rglob(f"{zotero_key}.md"):
        try:
            text = record_path.read_text(encoding="utf-8")
        except Exception:
            continue
        return {
            "do_ocr": _read_frontmatter_optional_bool_from_text(text, "do_ocr"),
            "analyze": _read_frontmatter_optional_bool_from_text(text, "analyze"),
        }
    return {"do_ocr": None, "analyze": None}


def load_export_inventory(paths: dict[str, Path]) -> dict[str, dict]:
    inventory = {"doi": {}, "pmid": {}, "title": {}}
    for export_path in sorted(paths["exports"].glob("*.json")):
        domain = export_path.stem
        for item in load_export_rows(export_path):
            record = {
                "zotero_key": item.get("key", ""),
                "domain": domain,
                "title": item.get("title", ""),
                "doi": item.get("doi", ""),
                "pmid": item.get("pmid", ""),
                "collections": item.get("collections", []),
            }
            doi = str(record.get("doi", "") or "").strip().lower()
            pmid = str(record.get("pmid", "") or "").strip()
            title = normalize_candidate_title(record.get("title", ""))
            if doi and doi not in inventory["doi"]:
                inventory["doi"][doi] = record
            if pmid and pmid not in inventory["pmid"]:
                inventory["pmid"][pmid] = record
            if title and title not in inventory["title"]:
                inventory["title"][title] = record
    return inventory


def find_existing_library_match(row: dict, inventory: dict[str, dict]) -> dict | None:
    doi = str(row.get("doi", "") or "").strip().lower()
    if doi and doi in inventory["doi"]:
        return inventory["doi"][doi]
    pmid = str(row.get("pmid", "") or "").strip()
    if pmid and pmid in inventory["pmid"]:
        return inventory["pmid"][pmid]
    title = normalize_candidate_title(row.get("title", ""))
    if title and title in inventory["title"]:
        return inventory["title"][title]
    return None


def resolve_collection_choice(domain: str, raw_value: str, catalog: dict[str, list[str]]) -> dict[str, str]:
    text = str(raw_value or "").strip()
    if not text:
        return {"resolved": "", "match": "", "input": ""}
    allowed = [path for path in catalog.get(domain, []) if path]
    if not allowed:
        return {"resolved": "", "match": "no_catalog", "input": text}
    lower_text = text.lower()
    if "/" not in text:
        leaf_matches = [path for path in allowed if path.split("/")[-1].strip().lower() == lower_text]
        leaf_matches = sorted(set(leaf_matches))
        if len(leaf_matches) > 1:
            return {"resolved": "", "match": "ambiguous_leaf", "input": text}
    exact_map = {path: path for path in allowed}
    if text in exact_map:
        return {"resolved": text, "match": "exact", "input": text}
    lower_exact = {path.lower(): path for path in allowed}
    if lower_text in lower_exact:
        return {"resolved": lower_exact[lower_text], "match": "exact_ci", "input": text}
    leaf_matches = [path for path in allowed if path.split("/")[-1].strip().lower() == lower_text]
    if len(leaf_matches) == 1:
        return {"resolved": leaf_matches[0], "match": "leaf", "input": text}
    suffix_matches = [path for path in allowed if path.lower().endswith("/" + lower_text) or path.lower() == lower_text]
    suffix_matches = sorted(set(suffix_matches))
    if len(suffix_matches) == 1:
        return {"resolved": suffix_matches[0], "match": "suffix", "input": text}
    compact = re.sub("\\s+", "", lower_text)
    compact_matches = []
    for path in allowed:
        path_compact = re.sub("\\s+", "", path.lower())
        if path_compact.endswith("/" + compact) or path_compact == compact:
            compact_matches.append(path)
    compact_matches = sorted(set(compact_matches))
    if len(compact_matches) == 1:
        return {"resolved": compact_matches[0], "match": "compact_suffix", "input": text}
    match = "ambiguous" if leaf_matches or suffix_matches or compact_matches else "unresolved"
    return {"resolved": "", "match": match, "input": text}


def apply_candidate_collection_resolution(row: dict, catalog: dict[str, list[str]]) -> dict:
    resolved = dict(row)
    domain = str(resolved.get("domain", "") or "").strip()
    recommended = resolve_collection_choice(domain, resolved.get("recommended_collection", ""), catalog)
    user = resolve_collection_choice(domain, resolved.get("user_collection", ""), catalog)
    resolved["recommended_collection"] = recommended.get("resolved", "")
    resolved["user_collection_resolved"] = user.get("resolved", "")
    if str(resolved.get("user_collection", "") or "").strip():
        resolved["final_collection"] = user.get("resolved", "")
        resolved["collection_resolution"] = (
            f"user_{user.get('match', 'unresolved')}" if user.get("match") else "user_unresolved"
        )
    else:
        resolved["final_collection"] = recommended.get("resolved", "")
        resolved["collection_resolution"] = (
            f"recommended_{recommended.get('match', 'unresolved')}"
            if recommended.get("match")
            else "recommended_unresolved"
        )
    return resolved


def apply_existing_library_match(row: dict, inventory: dict[str, dict]) -> dict:
    resolved = dict(row)
    match = find_existing_library_match(resolved, inventory)
    if not match:
        resolved["existing_zotero_key"] = ""
        resolved["existing_collections"] = []
        resolved["duplicate_hint"] = ""
        return resolved
    resolved["existing_zotero_key"] = str(match.get("zotero_key", "") or "").strip()
    resolved["existing_collections"] = list(match.get("collections", []) or [])
    collections_text = " | ".join(resolved["existing_collections"])
    if collections_text:
        resolved["duplicate_hint"] = f"已存在于 Zotero: {resolved['existing_zotero_key']} ({collections_text})"
    else:
        resolved["duplicate_hint"] = f"已存在于 Zotero: {resolved['existing_zotero_key']}"
    return resolved


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


def obsidian_wikilink_for_pdf(pdf_path: str, vault_dir: Path, zotero_dir: Path | None = None) -> str:
    text = str(pdf_path or "").strip()
    if not text:
        return ""
    # Handle storage: prefix paths by resolving through zotero_dir
    if text.startswith("storage:") and zotero_dir is not None:
        storage_rel = text[len("storage:") :].lstrip("/").lstrip("\\")
        absolute_pdf_path = zotero_dir / "storage" / storage_rel.replace("/", os.sep)
        absolute_str = str(absolute_pdf_path)
    else:
        absolute_str = absolutize_vault_path(vault_dir, text, resolve_junction=True)
    if not absolute_str:
        return ""
    absolute_path = Path(absolute_str)
    try:
        relative = absolute_path.relative_to(vault_dir)
    except ValueError:
        # Path outside vault — try to route through Zotero junction inside vault
        if zotero_dir is not None and zotero_dir.exists():
            try:
                from paperforge.pdf_resolver import resolve_junction
                real_zotero = resolve_junction(zotero_dir)
                if real_zotero != zotero_dir:
                    rel_to_zotero = absolute_path.relative_to(real_zotero)
                    via_junction = zotero_dir / rel_to_zotero
                    relative = via_junction.relative_to(vault_dir)
                    return f"[[{relative.as_posix()}]]"
            except (ValueError, OSError):
                pass
        return f"[[{absolute_path.as_posix()}]]"
    return f"[[{relative.as_posix()}]]"


def absolutize_vault_path(vault: Path, path: str, resolve_junction: bool = False) -> str:
    text = str(path or "").strip()
    if not text:
        return ""
    candidate = Path(text)
    result = str(candidate) if candidate.is_absolute() else str((vault / text.replace("/", os.sep)).resolve())
    if resolve_junction:
        from paperforge.pdf_resolver import resolve_junction

        result = str(resolve_junction(Path(result)))
    return result


def obsidian_wikilink_for_path(vault: Path, path: str) -> str:
    absolute = absolutize_vault_path(vault, path, resolve_junction=True)
    if not absolute:
        return ""
    absolute_path = Path(absolute)
    try:
        relative = absolute_path.relative_to(vault)
    except ValueError:
        return f"[[{absolute_path.as_posix()}]]"
    return f"[[{relative.as_posix()}]]"


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


def load_export_rows(path: Path) -> list[dict]:
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


def compute_final_collection(row: dict) -> str:
    user_raw = str(row.get("user_collection", "") or "").strip()
    user_resolved = str(row.get("user_collection_resolved", "") or "").strip()
    recommended = str(row.get("recommended_collection", "") or "").strip()
    if user_raw:
        return user_resolved
    return recommended


def canonicalize_decision(value: str) -> str:
    text = str(value or "").strip()
    if text in {"", "待查"}:
        return "待定"
    if text in {"排除", "不纳入"}:
        return "不纳入"
    if text == "纳入":
        return "纳入"
    return "待定"


def candidate_markdown(row: dict) -> str:
    row = dict(row)
    row["final_collection"] = compute_final_collection(row)
    row["decision"] = canonicalize_decision(row.get("decision", ""))
    lines = ["---"]
    ordered_keys = [
        "candidate_id",
        "domain",
        "title",
        "authors",
        "year",
        "journal",
        "doi",
        "pmid",
        "source",
        "requester_skill",
        "request_context",
        "abstract_short",
        "decision",
        "recommended_collection",
        "recommend_confidence",
        "recommend_reason",
        "user_collection",
        "user_collection_resolved",
        "final_collection",
        "collection_resolution",
        "duplicate_hint",
        "existing_zotero_key",
        "existing_collections",
        "import_status",
        "note",
        "candidate_source_type",
        "source_zotero_key",
        "cited_ref_number",
        "trigger_sentence",
        "source_context",
        "task_relevance_reason",
        "harvest_priority",
        "raw_reference",
        "status",
    ]
    row.setdefault("status", "candidate")
    for key in ordered_keys:
        value = row.get(key, "")
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {yaml_quote(item)}")
        elif value == "":
            lines.append(f"{key}:")
        elif "\n" in str(value):
            lines.extend(
                yaml_block(str(value)).copy()
                if key == "abstract"
                else [f"{key}: |-"] + [f"  {line}" for line in str(value).splitlines()]
            )
        else:
            lines.append(f"{key}: {yaml_quote(value)}")
    lines.extend(
        [
            "---",
            "",
            f"# {row['candidate_id']}",
            "",
            "候选文献轻量记录，仅用于 Base 决策和 write-back 触发，不是正式文献卡片。",
            "",
        ]
    )
    return "\n".join(lines)


def generate_review(candidates: list[dict]) -> str:
    normalized = []
    for row in candidates:
        copy = dict(row)
        copy["decision"] = canonicalize_decision(copy.get("decision", ""))
        normalized.append(copy)
    include = [c for c in normalized if c.get("decision") == "纳入"]
    exclude = [c for c in normalized if c.get("decision") == "不纳入"]
    lines = [
        "# 本轮候选总览",
        "",
        "## 检索背景",
        "",
        f"- 候选数量：{len(normalized)}",
        f"- 建议纳入：{len(include)}",
        f"- 不纳入：{len(exclude)}",
        "",
        "## 总体判断",
        "",
        "- 当前候选池已经按决策状态分层，可直接进入 Base 处理。",
        "",
        "## 推荐优先纳入",
        "",
    ]
    if include:
        for row in include:
            lines.extend(
                [
                    f"### {row['candidate_id']}",
                    "",
                    f"- 标题：{row['title']}",
                    f"- 推荐分类：`{compute_final_collection(row)}`",
                    f"- 理由：{row.get('recommend_reason', '')}",
                    "",
                ]
            )
    else:
        lines.extend(["- 暂无", ""])
    lines.extend(["## 不纳入", ""])
    if exclude:
        for row in exclude:
            lines.extend(
                [
                    f"### {row['candidate_id']}",
                    "",
                    f"- 标题：{row['title']}",
                    f"- 理由：{row.get('recommend_reason', '')}",
                    "",
                ]
            )
    else:
        lines.extend(["- 暂无", ""])
    lines.extend(["## 下一步", "", "1. 在 Base 中确认决策。", "2. 对纳入项执行 write-back。", "3. 刷新正式索引。", ""])
    return "\n".join(lines)


DEEP_READING_HEADER = "## 🔍 精读"


def extract_preserved_deep_reading(text: str) -> str:
    """Extract the `## 🔍 精读` section by matching it as a real markdown header.

    Uses regex to ensure we match `## 🔍 精读` at the start of a line,
    avoiding false positives from prose text that merely mentions the string.
    """
    if not text:
        return ""
    match = re.search("^## 🔍 精读\\s*$", text, re.MULTILINE)
    if not match:
        return ""
    start = match.start()
    preserved = text[start:].strip()
    return preserved


def has_deep_reading_content(text: str) -> bool:
    """Return True only if the deep-reading section contains *substantive* content.

    A scaffold alone (filled with placeholders like '（待补充）') does NOT count.
    We strip out structural lines (section headers, callout headers, empty lists)
    and placeholder text, then require at least one prose sentence or 20 chars
    of actual content.
    """
    preserved = extract_preserved_deep_reading(text)
    if not preserved:
        return False
    body = preserved.replace(DEEP_READING_HEADER, "").strip()
    if not body:
        return False
    lines = body.splitlines()
    non_placeholder_chars = 0
    has_prose_sentence = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("### "):
            continue
        if re.match("^>\\s*\\[!", stripped):
            continue
        if "（待补充）" in stripped:
            continue
        if re.match("^[-*]\\s*$", stripped):
            continue
        non_placeholder_chars += len(stripped)
        if re.search("[\\u4e00-\\u9fff]", stripped) and re.search("[。！？\\.\\!\\?]$", stripped):
            has_prose_sentence = True
    return has_prose_sentence or non_placeholder_chars >= 20




def _add_missing_frontmatter_fields(existing_content: str, new_fields: dict[str, str]) -> str:
    """Surgically append missing fields to existing frontmatter without overwriting anything."""
    if not existing_content.startswith("---"):
        return existing_content
    parts = existing_content.split("---", 2)
    if len(parts) < 3:
        return existing_content
    frontmatter = parts[1]
    body = parts[2]
    lines_to_add = []
    for key, value in new_fields.items():
        pattern = "^" + re.escape(key) + "\\s*:"
        if not re.search(pattern, frontmatter, re.MULTILINE):
            lines_to_add.append(f"{key}: {yaml_quote(value)}")
    if not lines_to_add:
        return existing_content
    new_frontmatter = frontmatter.rstrip("\n") + "\n" + "\n".join(lines_to_add) + "\n"
    return f"---{new_frontmatter}---{body}"


def update_frontmatter_field(content: str, key: str, value: str) -> str:
    """Update an existing frontmatter field value, or add if missing."""
    if not content.startswith("---"):
        return content
    pattern = "^" + re.escape(key) + "\\s*:.*$"
    replacement = f"{key}: {yaml_quote(value)}"
    new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE, count=1)
    if count == 0:
        new_content = _add_missing_frontmatter_fields(content, {key: value})
    return new_content


def load_control_actions(paths: dict[str, Path]) -> dict[str, dict]:
    actions = {}
    lit_root = paths.get("literature")
    if not lit_root or not lit_root.exists():
        return actions
    for note_file in lit_root.rglob("*.md"):
        if note_file.name in ("fulltext.md", "deep-reading.md", "discussion.md"):
            continue
        try:
            text = note_file.read_text(encoding="utf-8")
        except Exception:
            continue
        key_match = re.search(r"^zotero_key:\s*(.+)$", text, re.MULTILINE)
        if not key_match:
            continue
        zotero_key = key_match.group(1).strip()
        do_ocr = False
        do_ocr_match = re.search(r"^do_ocr:\s*(?:[\"'])?(true|false)(?:[\"'])?\s*$", text, re.MULTILINE | re.IGNORECASE)
        if do_ocr_match:
            do_ocr = do_ocr_match.group(1).lower() == "true"
        analyze = False
        analyze_match = re.search(r"^analyze:\s*(?:[\"'])?(true|false)(?:[\"'])?\s*$", text, re.MULTILINE | re.IGNORECASE)
        if analyze_match:
            analyze = analyze_match.group(1).lower() == "true"
        actions[zotero_key] = {"analyze": analyze, "do_ocr": do_ocr}
    return actions


def run_selection_sync(vault: Path, verbose: bool = False) -> int:
    from paperforge.worker.base_views import ensure_base_views
    from paperforge.worker.ocr import validate_ocr_meta

    paths = pipeline_paths(vault)
    config = load_domain_config(paths)
    ensure_base_views(vault, paths, config)
    domain_lookup = {entry["export_file"]: entry["domain"] for entry in config["domains"]}
    written = 0
    updated = 0
    for export_path in sorted(paths["exports"].glob("*.json")):
        domain = domain_lookup.get(export_path.name, export_path.stem)
        for item in load_export_rows(export_path):
            pdf_attachments = [a for a in item.get("attachments", []) if a.get("contentType") == "application/pdf"]
            has_pdf = bool(pdf_attachments)
            raw_pdf_path = pdf_attachments[0].get("path", "") if pdf_attachments else ""
            from paperforge.pdf_resolver import resolve_pdf_path

            cfg = load_vault_config(vault)
            zotero_dir = vault / cfg.get("system_dir", "System") / "Zotero"
            resolved_pdf = resolve_pdf_path(raw_pdf_path, has_pdf, vault, zotero_dir)
            collection_meta = collection_fields(item.get("collections", []))
            meta_path = paths["ocr"] / item["key"] / "meta.json"
            meta = read_json(meta_path) if meta_path.exists() else {}
            validated_ocr_status, validated_error = validate_ocr_meta(paths, meta) if meta else ("pending", "")
            if meta:
                meta["ocr_status"] = validated_ocr_status
                if validated_error:
                    meta["error"] = validated_error
                    write_json(meta_path, meta)
            note_path = paths["literature"] / domain / f"{item['key']} - {slugify_filename(item['title'])}.md"
            note_text = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
            fulltext_md_path = obsidian_wikilink_for_path(
                vault, meta.get("fulltext_md_path", "") or meta.get("markdown_path", "")
            )
            ocr_status = meta.get("ocr_status", "pending")
            record_ocr_status = "nopdf" if not has_pdf or not resolved_pdf else ocr_status
            creators = item.get("creators", [])
            first_author = ""
            for c in creators:
                if c.get("creatorType") == "author":
                    first_author = f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
                    break
            journal = item.get("journal", "")
            extra = item.get("extra", "")
            impact_factor = lookup_impact_factor(journal, extra, vault)
            # Convert supplementary storage: paths to wikilinks
            supplementary_wikilinks = []
            for supp_path in item.get("supplementary", []):
                if supp_path:
                    wikilink = obsidian_wikilink_for_pdf(supp_path, vault, zotero_dir)
                    if wikilink:
                        supplementary_wikilinks.append(wikilink)
            pdf_wikilink = obsidian_wikilink_for_pdf(resolved_pdf, vault, zotero_dir) if resolved_pdf else ""

            # Phase 37: library-records deprecated — skip creation.
            # Formal notes now carry workflow flags (do_ocr, analyze) directly.
            # Existing library-records are migrated via Phase 40 logic.
            updated += 1
    print(f"selection-sync: wrote {written} records, updated {updated} records")
    return 0


def load_candidates_by_id(paths: dict[str, Path]) -> dict[str, dict]:
    candidates = read_json(paths["candidates"])
    return {row["candidate_id"]: row for row in candidates}


def save_candidates(paths: dict[str, Path], candidate_map: dict[str, dict]) -> None:
    collection_catalog = load_domain_collections(paths)
    export_inventory = load_export_inventory(paths)
    rows = []
    for row in candidate_map.values():
        copy = dict(row)
        copy["decision"] = canonicalize_decision(copy.get("decision", ""))
        copy = apply_candidate_collection_resolution(copy, collection_catalog)
        copy = apply_existing_library_match(copy, export_inventory)
        copy["final_collection"] = compute_final_collection(copy)
        rows.append(copy)
    write_json(paths["candidates"], rows)


def writeback_command_for_candidate(row: dict) -> dict | None:
    final_collection = str(row.get("final_collection", "") or "").strip()
    if not final_collection:
        return None
    candidate_id = str(row.get("candidate_id", "") or "").strip()
    if not candidate_id:
        return None
    command = {
        "command_id": f"wb-native-{candidate_id}",
        "status": "queued",
        "source_candidate_id": candidate_id,
        "target_domain": str(row.get("domain", "") or "").strip(),
        "target_collection": final_collection,
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
    existing_zotero_key = str(row.get("existing_zotero_key", "") or "").strip()
    if existing_zotero_key:
        command.update({"action": "attach_existing_item_to_collection", "existing_zotero_key": existing_zotero_key})
        return command
    doi = str(row.get("doi", "") or "").strip()
    pmid = str(row.get("pmid", "") or "").strip()
    if doi:
        command.update(
            {
                "action": "create_item_from_identifier",
                "identifier_type": "doi",
                "identifier": doi,
                "metadata_fallback": {
                    "title": row.get("title", ""),
                    "authors": row.get("authors", []),
                    "year": str(row.get("year", "") or ""),
                    "journal": row.get("journal", ""),
                    "doi": doi,
                    "pmid": pmid,
                    "abstractNote": row.get("abstract_short", ""),
                },
            }
        )
        return command
    if pmid:
        command.update(
            {
                "action": "create_item_from_identifier",
                "identifier_type": "pmid",
                "identifier": pmid,
                "metadata_fallback": {
                    "title": row.get("title", ""),
                    "authors": row.get("authors", []),
                    "year": str(row.get("year", "") or ""),
                    "journal": row.get("journal", ""),
                    "doi": doi,
                    "pmid": pmid,
                    "abstractNote": row.get("abstract_short", ""),
                },
            }
        )
        return command
    command.update(
        {
            "action": "create_item_from_metadata",
            "metadata": {
                "title": row.get("title", ""),
                "authors": row.get("authors", []),
                "year": str(row.get("year", "") or ""),
                "journal": row.get("journal", ""),
                "doi": doi,
                "pmid": pmid,
                "abstractNote": row.get("abstract_short", ""),
            },
        }
    )
    return command


def sync_writeback_queue(paths: dict[str, Path], candidate_map: dict[str, dict]) -> tuple[list[dict], int]:
    existing_rows = read_jsonl(paths["queue"])
    existing_by_candidate = {
        str(row.get("source_candidate_id", "") or "").strip(): dict(row)
        for row in existing_rows
        if str(row.get("source_candidate_id", "") or "").strip()
    }
    queue_rows: list[dict] = []
    queued_candidates: set[str] = set()
    created = 0
    for candidate_id, row in candidate_map.items():
        decision = canonicalize_decision(row.get("decision", ""))
        if decision != "纳入":
            continue
        if str(row.get("import_status", "") or "").strip() == "imported":
            continue
        candidate_copy = dict(row)
        candidate_copy["final_collection"] = compute_final_collection(candidate_copy)
        final_collection = str(candidate_copy.get("final_collection", "") or "").strip()
        if not final_collection:
            candidate_copy["import_status"] = "needs_collection_resolution"
            candidate_map[candidate_id] = candidate_copy
            continue
        command = writeback_command_for_candidate(candidate_copy)
        if not command:
            candidate_copy["import_status"] = "blocked"
            candidate_map[candidate_id] = candidate_copy
            continue
        existing = existing_by_candidate.get(candidate_id)
        if existing and str(existing.get("status", "") or "").strip() in {"queued", "running", "processed"}:
            merged = dict(existing)
            merged["target_collection"] = command["target_collection"]
            merged["target_domain"] = command.get("target_domain", merged.get("target_domain", ""))
            if merged.get("status") != "processed":
                merged["requested_at"] = command["requested_at"]
            queue_rows.append(merged)
        else:
            queue_rows.append(command)
            created += 1
        candidate_copy["import_status"] = "queued_for_writeback"
        candidate_map[candidate_id] = candidate_copy
        queued_candidates.add(candidate_id)
    for row in existing_rows:
        candidate_id = str(row.get("source_candidate_id", "") or "").strip()
        status = str(row.get("status", "") or "").strip()
        if candidate_id in queued_candidates:
            continue
        if status == "processed":
            queue_rows.append(row)
    write_jsonl(paths["queue"], queue_rows)
    return (queue_rows, created)


def load_bridge_config(paths: dict[str, Path]) -> dict:
    config_path = paths["bridge_config"]
    if not config_path.exists():
        sample = read_json(paths["bridge_config_sample"])
        write_json(config_path, sample)
    return read_json(config_path)


def apply_writeback_log(paths: dict[str, Path], candidate_map: dict[str, dict]) -> int:
    log_rows = read_jsonl(paths["log"])
    changed = 0
    latest_by_candidate: dict[str, dict] = {}
    for row in log_rows:
        candidate_id = str(row.get("source_candidate_id", "") or "").strip()
        if candidate_id:
            latest_by_candidate[candidate_id] = row
    for candidate_id, log_row in latest_by_candidate.items():
        candidate = dict(candidate_map.get(candidate_id, {}))
        if not candidate:
            continue
        status = str(log_row.get("status", "") or "").strip()
        if status == "success":
            candidate["import_status"] = "imported"
            candidate["zotero_key"] = str(log_row.get("zotero_key", "") or "").strip()
            changed += 1
        elif status == "error":
            candidate["import_status"] = "writeback_error"
            changed += 1
        candidate_map[candidate_id] = candidate
    return changed


def invoke_native_bridge(paths: dict[str, Path], max_commands: int = 5) -> dict:
    config = load_bridge_config(paths)
    base_url = str(config.get("server_base_url", "http://127.0.0.1:23119")).rstrip("/")
    endpoint = str(config.get("process_endpoint", "/literaturePipeline/processQueue"))
    payload = {
        "queuePath": str(paths["queue"]).replace("\\", "/"),
        "logPath": str(paths["log"]).replace("\\", "/"),
        "configPath": str(paths["bridge_config"]).replace("\\", "/"),
        "maxCommands": max_commands,
    }
    response = requests.post(f"{base_url}{endpoint}", json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()
    if not result.get("ok", False):
        raise RuntimeError(result.get("error", "Native bridge returned non-ok result"))
    return result


def normalize_candidate_title(text: str) -> str:
    return re.sub("\\s+", " ", str(text or "").strip().lower())


def candidate_identity_keys(row: dict) -> dict[str, str]:
    doi = str(row.get("doi", "") or "").strip().lower()
    pmid = str(row.get("pmid", "") or "").strip()
    title = normalize_candidate_title(row.get("title", ""))
    return {"doi": doi, "pmid": pmid, "title": title}


def candidate_id_from_payload(row: dict) -> str:
    source = str(row.get("source", "") or "candidate").strip().lower()
    doi = re.sub("[^a-z0-9]+", "-", str(row.get("doi", "") or "").strip().lower()).strip("-")
    pmid = re.sub("[^0-9]+", "", str(row.get("pmid", "") or "").strip())
    fallback = re.sub("[^a-z0-9]+", "-", normalize_candidate_title(row.get("title", ""))).strip("-")[:80]
    suffix = doi or pmid or fallback or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{source}-{suffix}"


def _normalize_candidate_value(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return str(value).strip()


def _authors_from_pubmed(value) -> list[str] | str:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return str(value or "").strip()


def _authors_from_openalex(value) -> list[str]:
    authors = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                author = item.get("author") or {}
                name = author.get("display_name") or item.get("display_name") or ""
                if name:
                    authors.append(str(name).strip())
            elif str(item).strip():
                authors.append(str(item).strip())
    return authors


def _abstract_from_openalex(inverted_index) -> str:
    if not isinstance(inverted_index, dict):
        return ""
    tokens: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        if not isinstance(positions, list):
            continue
        for pos in positions:
            try:
                tokens.append((int(pos), str(word)))
            except Exception:
                continue
    if not tokens:
        return ""
    tokens.sort(key=lambda item: item[0])
    return " ".join((word for _, word in tokens))


def _authors_from_arxiv(value) -> list[str]:
    authors = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                name = item.get("name", "") or item.get("author", "")
                if name:
                    authors.append(str(name).strip())
            elif str(item).strip():
                authors.append(str(item).strip())
    return authors


def _authors_from_scholar(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split("\\s*,\\s*|\\s+and\\s+", value)
        return [part.strip() for part in parts if part.strip()]
    return []


def adapt_pubmed_candidate(row: dict) -> dict:
    payload = dict(row.get("payload") or {})
    adapted = {
        "candidate_id": row.get("candidate_id") or f"pubmed-{payload.get('pmid') or payload.get('PMID') or ''}",
        "domain": row.get("domain", ""),
        "title": payload.get("title", ""),
        "authors": _authors_from_pubmed(payload.get("authors", [])),
        "year": payload.get("year", ""),
        "journal": payload.get("journal", ""),
        "doi": payload.get("doi", ""),
        "pmid": payload.get("pmid") or payload.get("PMID", ""),
        "source": row.get("source", "") or "pubmed_search",
        "requester_skill": row.get("requester_skill", ""),
        "request_context": row.get("request_context", ""),
        "abstract_short": payload.get("abstract", "") or payload.get("abstract_short", ""),
        "decision": row.get("decision", ""),
        "recommended_collection": row.get("recommended_collection", ""),
        "recommend_confidence": row.get("recommend_confidence", ""),
        "recommend_reason": row.get("recommend_reason", ""),
        "user_collection": row.get("user_collection", ""),
        "final_collection": row.get("final_collection", ""),
        "duplicate_hint": row.get("duplicate_hint", ""),
        "import_status": row.get("import_status", ""),
        "note": row.get("note", ""),
        "candidate_source_type": row.get("candidate_source_type", "") or "external_search",
        "source_context": row.get("source_context", ""),
        "task_relevance_reason": row.get("task_relevance_reason", ""),
    }
    return adapted


def adapt_openalex_candidate(row: dict) -> dict:
    payload = dict(row.get("payload") or {})
    primary_location = payload.get("primary_location") or {}
    source_info = primary_location.get("source") or {}
    openalex_id = str(payload.get("id", "") or "").rstrip("/").split("/")[-1]
    adapted = {
        "candidate_id": row.get("candidate_id") or f"openalex-{openalex_id}",
        "domain": row.get("domain", ""),
        "title": payload.get("display_name", "") or payload.get("title", ""),
        "authors": _authors_from_openalex(payload.get("authorships", [])),
        "year": payload.get("publication_year", "") or payload.get("year", ""),
        "journal": source_info.get("display_name", "") or payload.get("journal", ""),
        "doi": str(payload.get("doi", "") or "").replace("https://doi.org/", ""),
        "pmid": "",
        "source": row.get("source", "") or "openalex_search",
        "requester_skill": row.get("requester_skill", ""),
        "request_context": row.get("request_context", ""),
        "abstract_short": _abstract_from_openalex(payload.get("abstract_inverted_index")),
        "decision": row.get("decision", ""),
        "recommended_collection": row.get("recommended_collection", ""),
        "recommend_confidence": row.get("recommend_confidence", ""),
        "recommend_reason": row.get("recommend_reason", ""),
        "user_collection": row.get("user_collection", ""),
        "final_collection": row.get("final_collection", ""),
        "duplicate_hint": row.get("duplicate_hint", ""),
        "import_status": row.get("import_status", ""),
        "note": row.get("note", ""),
        "candidate_source_type": row.get("candidate_source_type", "") or "external_search",
        "source_context": row.get("source_context", ""),
        "task_relevance_reason": row.get("task_relevance_reason", ""),
    }
    return adapted


def adapt_arxiv_candidate(row: dict) -> dict:
    payload = dict(row.get("payload") or {})
    arxiv_id = str(payload.get("id", "") or payload.get("entry_id", "")).rstrip("/").split("/")[-1]
    adapted = {
        "candidate_id": row.get("candidate_id") or f"arxiv-{arxiv_id}",
        "domain": row.get("domain", ""),
        "title": payload.get("title", ""),
        "authors": _authors_from_arxiv(payload.get("authors", [])),
        "year": str(payload.get("published", "") or "")[:4],
        "journal": payload.get("journal_ref", "") or "arXiv",
        "doi": payload.get("doi", ""),
        "pmid": "",
        "source": row.get("source", "") or "arxiv_search",
        "requester_skill": row.get("requester_skill", ""),
        "request_context": row.get("request_context", ""),
        "abstract_short": payload.get("summary", "") or payload.get("abstract", ""),
        "decision": row.get("decision", ""),
        "recommended_collection": row.get("recommended_collection", ""),
        "recommend_confidence": row.get("recommend_confidence", ""),
        "recommend_reason": row.get("recommend_reason", ""),
        "user_collection": row.get("user_collection", ""),
        "final_collection": row.get("final_collection", ""),
        "duplicate_hint": row.get("duplicate_hint", ""),
        "import_status": row.get("import_status", ""),
        "note": row.get("note", ""),
        "candidate_source_type": row.get("candidate_source_type", "") or "external_search",
        "source_context": row.get("source_context", ""),
        "task_relevance_reason": row.get("task_relevance_reason", ""),
    }
    return adapted


def adapt_google_scholar_candidate(row: dict) -> dict:
    payload = dict(row.get("payload") or {})
    adapted = {
        "candidate_id": row.get("candidate_id")
        or f"google-scholar-{re.sub('[^a-z0-9]+', '-', normalize_candidate_title(payload.get('title', ''))).strip('-')[:80]}",
        "domain": row.get("domain", ""),
        "title": payload.get("title", ""),
        "authors": _authors_from_scholar(payload.get("authors", [])),
        "year": str(payload.get("year", "") or ""),
        "journal": payload.get("journal", "") or payload.get("venue", ""),
        "doi": payload.get("doi", ""),
        "pmid": "",
        "source": row.get("source", "") or "google_scholar_search",
        "requester_skill": row.get("requester_skill", ""),
        "request_context": row.get("request_context", ""),
        "abstract_short": payload.get("abstract", "") or payload.get("snippet", ""),
        "decision": row.get("decision", ""),
        "recommended_collection": row.get("recommended_collection", ""),
        "recommend_confidence": row.get("recommend_confidence", ""),
        "recommend_reason": row.get("recommend_reason", ""),
        "user_collection": row.get("user_collection", ""),
        "final_collection": row.get("final_collection", ""),
        "duplicate_hint": row.get("duplicate_hint", ""),
        "import_status": row.get("import_status", ""),
        "note": row.get("note", ""),
        "candidate_source_type": row.get("candidate_source_type", "") or "external_search",
        "source_context": row.get("source_context", ""),
        "task_relevance_reason": row.get("task_relevance_reason", ""),
    }
    return adapted


def adapt_candidate_event(row: dict) -> dict:
    adapter = str(row.get("adapter", "") or "").strip()
    if adapter == "pubmed_search":
        return adapt_pubmed_candidate(row)
    if adapter == "openalex_search":
        return adapt_openalex_candidate(row)
    if adapter == "arxiv_search":
        return adapt_arxiv_candidate(row)
    if adapter == "google_scholar_search":
        return adapt_google_scholar_candidate(row)
    return dict(row)


def default_user_agent() -> str:
    return "ResearchLiteraturePipeline/1.0 (+local-vault)"


def build_search_event(base_task: dict, source: str, payload: dict) -> dict:
    return {
        "adapter": source,
        "payload": payload,
        "source": source,
        "requester_skill": base_task.get("requester_skill", ""),
        "request_context": base_task.get("request_context", ""),
        "domain": base_task.get("domain", ""),
        "recommended_collection": base_task.get("recommended_collection", ""),
        "recommend_confidence": base_task.get("recommend_confidence", ""),
        "recommend_reason": base_task.get("recommend_reason", "") or f"{source} 检索命中",
        "candidate_source_type": base_task.get("candidate_source_type", "") or "external_search",
        "task_relevance_reason": base_task.get("task_relevance_reason", ""),
        "note": base_task.get("note", ""),
    }


def _pubmed_abstract_and_doi_map(xml_text: str) -> dict[str, dict]:
    root = ET.fromstring(xml_text)
    result = {}
    for article in root.findall(".//PubmedArticle"):
        pmid = (article.findtext(".//MedlineCitation/PMID") or "").strip()
        if not pmid:
            continue
        abstract_parts = []
        for node in article.findall(".//Abstract/AbstractText"):
            label = (node.attrib.get("Label") or "").strip()
            text = " ".join("".join(node.itertext()).split())
            if not text:
                continue
            abstract_parts.append(f"{label}: {text}" if label else text)
        doi = ""
        for id_node in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
            if (id_node.attrib.get("IdType") or "").lower() == "doi":
                doi = "".join(id_node.itertext()).strip()
                if doi:
                    break
        if not doi:
            for id_node in article.findall(".//ELocationID"):
                if (id_node.attrib.get("EIdType") or "").lower() == "doi":
                    doi = "".join(id_node.itertext()).strip()
                    if doi:
                        break
        result[pmid] = {"abstract": "\n".join(abstract_parts).strip(), "doi": doi}
    return result


def search_pubmed(task: dict, limit: int) -> tuple[list[dict], dict]:
    query = str(task.get("query", "") or "").strip()
    if not query:
        return ([], {"count": 0, "ids": []})
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    headers = {"User-Agent": os.environ.get("LIT_PIPELINE_USER_AGENT", default_user_agent())}
    common_params = {}
    email = os.environ.get("NCBI_EMAIL", "").strip()
    api_key = os.environ.get("NCBI_API_KEY", "").strip()
    if email:
        common_params["email"] = email
    if api_key:
        common_params["api_key"] = api_key
    esearch = requests.get(
        f"{base_url}/esearch.fcgi",
        params={
            "db": "pubmed",
            "retmode": "json",
            "sort": "relevance",
            "term": query,
            "retmax": limit,
            **common_params,
        },
        headers=headers,
        timeout=60,
    )
    esearch.raise_for_status()
    search_payload = esearch.json().get("esearchresult", {})
    ids = [str(item).strip() for item in search_payload.get("idlist", []) if str(item).strip()]
    if not ids:
        return ([], {"count": 0, "ids": []})
    id_text = ",".join(ids)
    esummary = requests.get(
        f"{base_url}/esummary.fcgi",
        params={"db": "pubmed", "retmode": "json", "id": id_text, **common_params},
        headers=headers,
        timeout=60,
    )
    esummary.raise_for_status()
    summary_payload = esummary.json().get("result", {})
    efetch = requests.get(
        f"{base_url}/efetch.fcgi",
        params={"db": "pubmed", "retmode": "xml", "id": id_text, **common_params},
        headers=headers,
        timeout=90,
    )
    efetch.raise_for_status()
    abstract_map = _pubmed_abstract_and_doi_map(efetch.text)
    rows = []
    for pmid in ids:
        item = summary_payload.get(pmid, {}) or {}
        title = html.unescape(str(item.get("title", "") or "")).strip()
        if not title:
            continue
        article_ids = item.get("articleids", []) or []
        doi = ""
        for article_id in article_ids:
            if str(article_id.get("idtype", "")).lower() == "doi":
                doi = str(article_id.get("value", "")).strip()
                if doi:
                    break
        if not doi:
            doi = abstract_map.get(pmid, {}).get("doi", "")
        rows.append(
            {
                "pmid": pmid,
                "title": title,
                "authors": [author.get("name", "") for author in item.get("authors") or [] if author.get("name")],
                "year": _extract_year(str(item.get("pubdate", "") or "")),
                "journal": item.get("fulljournalname", "") or item.get("source", ""),
                "doi": doi,
                "abstract": abstract_map.get(pmid, {}).get("abstract", ""),
            }
        )
    return (rows, {"count": len(rows), "ids": ids})


def search_openalex(task: dict, limit: int) -> tuple[list[dict], dict]:
    query = str(task.get("query", "") or "").strip()
    if not query:
        return ([], {"count": 0})
    headers = {"User-Agent": os.environ.get("LIT_PIPELINE_USER_AGENT", default_user_agent())}
    params = {"search": query, "per-page": limit}
    api_key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if api_key:
        params["api_key"] = api_key
    mailto = os.environ.get("OPENALEX_MAILTO", "").strip()
    if mailto:
        params["mailto"] = mailto
    response = requests.get("https://api.openalex.org/works", params=params, headers=headers, timeout=60)
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results", []) or []
    return (results, {"count": len(results), "meta": payload.get("meta", {})})


def search_arxiv(task: dict, limit: int) -> tuple[list[dict], dict]:
    query = str(task.get("query", "") or "").strip()
    if not query:
        return ([], {"count": 0})
    encoded_query = urllib.parse.quote(f"all:{query}")
    url = f"https://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results={limit}&sortBy=relevance&sortOrder=descending"
    headers = {"User-Agent": os.environ.get("LIT_PIPELINE_USER_AGENT", default_user_agent())}
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(response.text)
    entries = []
    for entry in root.findall("atom:entry", ns):
        entries.append(
            {
                "id": (entry.findtext("atom:id", default="", namespaces=ns) or "").strip(),
                "title": " ".join((entry.findtext("atom:title", default="", namespaces=ns) or "").split()),
                "summary": " ".join((entry.findtext("atom:summary", default="", namespaces=ns) or "").split()),
                "published": (entry.findtext("atom:published", default="", namespaces=ns) or "").strip(),
                "authors": [
                    {"name": (node.findtext("atom:name", default="", namespaces=ns) or "").strip()}
                    for node in entry.findall("atom:author", ns)
                ],
                "doi": (entry.findtext("arxiv:doi", default="", namespaces=ns) or "").strip(),
                "journal_ref": (entry.findtext("arxiv:journal_ref", default="", namespaces=ns) or "").strip(),
            }
        )
    return (entries, {"count": len(entries)})


def _coerce_source_name(value: str) -> str:
    text = str(value or "").strip().lower()
    aliases = {
        "pubmed": "pubmed_search",
        "pubmed_search": "pubmed_search",
        "openalex": "openalex_search",
        "openalex_search": "openalex_search",
        "arxiv": "arxiv_search",
        "arxiv_search": "arxiv_search",
    }
    return aliases.get(text, text)


def run_search_command(vault: Path, args) -> int:
    paths = pipeline_paths(vault)
    paths["search_tasks"].mkdir(parents=True, exist_ok=True)
    task_id = f"search-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    sources = args.sources or ["pubmed_search", "openalex_search", "arxiv_search"]
    task = {
        "task_id": task_id,
        "query": args.query,
        "domain": args.domain,
        "recommended_collection": args.recommended_collection or "",
        "requester_skill": args.requester_skill or "",
        "request_context": args.request_context or "",
        "sources": sources,
        "limit": args.limit,
        "recommend_reason": args.recommend_reason or "围绕检索主题补充候选文献",
        "candidate_source_type": "external_search",
    }
    task_path = paths["search_tasks"] / f"{task_id}.json"
    write_json(task_path, task)
    print(f"search: task written -> {task_path}")
    code = run_search_sources(vault)
    if code:
        return code
    if not args.skip_ingest:
        return run_ingest_candidates(vault)
    return 0


def normalize_candidate_payload(row: dict) -> dict:
    normalized = {key: _normalize_candidate_value(value) for key, value in adapt_candidate_event(row).items()}
    normalized["candidate_id"] = str(normalized.get("candidate_id", "") or "").strip() or candidate_id_from_payload(
        normalized
    )
    normalized["title"] = str(normalized.get("title", "") or "").strip()
    normalized["domain"] = str(normalized.get("domain", "") or "").strip()
    normalized["source"] = str(normalized.get("source", "") or "").strip() or "candidate_ingest"
    normalized["candidate_source_type"] = (
        str(normalized.get("candidate_source_type", "") or "").strip() or normalized["source"]
    )
    normalized["decision"] = canonicalize_decision(normalized.get("decision", ""))
    normalized["import_status"] = str(normalized.get("import_status", "") or "").strip() or "pending"
    normalized["recommend_confidence"] = str(normalized.get("recommend_confidence", "") or "").strip() or "0"
    normalized["status"] = "candidate"
    return normalized


def merge_candidate_record(existing: dict | None, incoming: dict) -> dict:
    merged = dict(existing or {})
    preserve_if_existing = {"decision", "user_collection", "note", "import_status"}
    for key, value in incoming.items():
        if existing and key in preserve_if_existing:
            current = merged.get(key, "")
            if str(current).strip():
                continue
        merged[key] = value
    merged["decision"] = canonicalize_decision(merged.get("decision", ""))
    merged["final_collection"] = compute_final_collection(merged)
    return merged


def resolve_existing_candidate(candidate_map: dict[str, dict], incoming: dict) -> tuple[str | None, dict | None]:
    candidate_id = incoming.get("candidate_id", "")
    if candidate_id and candidate_id in candidate_map:
        return (candidate_id, candidate_map[candidate_id])
    incoming_keys = candidate_identity_keys(incoming)
    for existing_id, existing in candidate_map.items():
        existing_keys = candidate_identity_keys(existing)
        if incoming_keys["doi"] and incoming_keys["doi"] == existing_keys["doi"]:
            return (existing_id, existing)
        if incoming_keys["pmid"] and incoming_keys["pmid"] == existing_keys["pmid"]:
            return (existing_id, existing)
        if incoming_keys["title"] and incoming_keys["title"] == existing_keys["title"]:
            return (existing_id, existing)
    return (None, None)


def _harvest_csv_paths(paths: dict[str, Path]) -> list[Path]:
    root = paths["harvest_root"]
    if not root.exists():
        return []
    return sorted(root.rglob("*-05-reference-harvest-candidates.csv"))


def _normalize_harvest_value(value: str) -> str:
    text = str(value or "").strip()
    if text == "<inherit-from-task-context>":
        return ""
    return text


def _normalize_harvest_row(row: dict[str, str]) -> dict:
    normalized = normalize_candidate_payload({key: _normalize_harvest_value(value) for key, value in row.items()})
    normalized["source"] = normalized.get("source", "") or "reference_harvest"
    normalized["candidate_source_type"] = normalized.get("candidate_source_type", "") or "reference_harvest"
    return normalized


def _merge_harvest_candidate(existing: dict | None, incoming: dict) -> dict:
    return merge_candidate_record(existing, incoming)


def next_key(domain: str, export_rows: list[dict]) -> str:
    prefix = "ORTHO" if domain == "骨科" else "SPORT"
    existing = [row.get("key", "") for row in export_rows]
    max_num = 0
    for key in existing:
        if key.startswith(prefix):
            suffix = key[len(prefix) :]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return f"{prefix}{max_num + 1:03d}"


def frontmatter_note(entry: dict, existing_text: str = "") -> str:
    preserved_deep = extract_preserved_deep_reading(existing_text)
    first_author = entry.get("first_author", "")
    if not first_author:
        authors = entry.get("authors", [])
        first_author = authors[0] if authors else ""
    lines = [
        "---",
        f"title: {yaml_quote(entry.get('title', ''))}",
        f"year: {entry.get('year', '')}",
        f"journal: {yaml_quote(entry.get('journal', ''))}",
        f"first_author: {yaml_quote(first_author)}",
        f"zotero_key: {yaml_quote(entry.get('zotero_key', ''))}",
        f"domain: {yaml_quote(entry.get('domain', ''))}",
        f"doi: {yaml_quote(entry.get('doi', ''))}",
        f"pmid: {yaml_quote(entry.get('pmid', ''))}",
        f"collection_path: {yaml_quote(entry.get('collection_path', ''))}",
        f"impact_factor: {yaml_quote(entry.get('impact_factor', ''))}",
    ]
    lines.extend(yaml_block(entry.get("abstract", "")))
    lines.extend(
        [
            f"has_pdf: {('true' if entry.get('has_pdf') else 'false')}",
            f"do_ocr: {('true' if entry.get('do_ocr') else 'false')}",
            f"analyze: {('true' if entry.get('analyze') else 'false')}",
            f"ocr_status: {yaml_quote(entry.get('ocr_status', 'pending'))}",
            f"deep_reading_status: {yaml_quote(entry.get('deep_reading_status', 'pending'))}",
            f"pdf_path: {yaml_quote(entry.get('pdf_path', ''))}",
            f"fulltext_md_path: {yaml_quote('[[{}]]'.format(entry['fulltext_path']) if entry.get('ocr_status') == 'done' and entry.get('fulltext_path') else '')}",
            "tags:",
            "  - 文献阅读",
            f"  - {entry.get('domain', '')}",
            "---",
            "",
            f"# {entry.get('title', '')}",
            "",
            "## 📄 文献基本信息",
            "",
            f"- Zotero Key: `{entry.get('zotero_key', '')}`",
            f"- Collection: `{entry.get('collection_path', '')}`",
            f"- 作者：{', '.join(entry.get('authors', []))}",
            f"- PDF: {('已检测' if entry.get('has_pdf') else '未检测到')}",
            f"- OCR: {entry.get('ocr_status', 'pending')}",
            f"- 精读: {entry.get('deep_reading_status', 'pending')}",
            "",
            "## 摘要",
            "",
            entry.get("abstract", "") or "暂无摘要",
            "",
        ]
    )
    if preserved_deep:
        lines.extend(["", preserved_deep, ""])
    return "\n".join(lines)


def analyze_selected_keys(paths: dict[str, Path]) -> set[str]:
    return {key for key, row in load_control_actions(paths).items() if row.get("analyze")}


def migrate_to_workspace(vault: Path, paths: dict) -> int:
    """Migrate flat literature notes into paper workspace directories.

    Copies each flat note at <literature_dir>/<domain>/<key> - <Title>.md into:
      <literature_dir>/<domain>/<key> - <Title>/<key> - <Title>.md
    Extracts ## 🔍 精读 into:
      <literature_dir>/<domain>/<key> - <Title>/deep-reading.md
    Creates:
      <literature_dir>/<domain>/<key> - <Title>/ai/  (empty directory)

    Idempotent: skips papers whose workspace directory already exists.
    The original flat note is preserved (copy-not-move per D-12).

    Returns: number of papers migrated (0 means all are already workspace).
    """
    index = asset_index.read_index(vault)
    items = index.get("items", []) if isinstance(index, dict) else []
    indexed_entries: dict[str, dict] = {
        str(entry.get("zotero_key", "") or "").strip(): entry
        for entry in items
        if str(entry.get("zotero_key", "") or "").strip()
    }

    flat_notes: list[tuple[Path, str, str]] = []
    lit_root = paths.get("literature")
    if lit_root and lit_root.exists():
        for note_path in lit_root.rglob("*.md"):
            if note_path.name in ("fulltext.md", "deep-reading.md", "discussion.md"):
                continue
            relative = note_path.relative_to(lit_root)
            if len(relative.parts) != 2:
                continue
            domain = relative.parts[0]
            try:
                text = note_path.read_text(encoding="utf-8")
            except Exception:
                continue
            key_match = re.search(r'^zotero_key:\s*"?(\S+?)"?\s*$', text, re.MULTILINE)
            zotero_key = key_match.group(1) if key_match else ""
            if not zotero_key:
                stem = note_path.stem
                if " - " not in stem:
                    continue
                zotero_key = stem.split(" - ", 1)[0].strip()
            if not zotero_key:
                continue
            flat_notes.append((note_path, domain, zotero_key))

    if not indexed_entries and not flat_notes:
        return 0

    migrated = 0

    for flat_note_path, domain, key in flat_notes:
        entry = indexed_entries.get(key, {})
        title = str(entry.get("title", "") or "").strip()
        if not title:
            title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', flat_note_path.read_text(encoding="utf-8"), re.MULTILINE)
            title = title_match.group(1).strip() if title_match else ""
        stem = flat_note_path.stem
        if title:
            title_slug = slugify_filename(title)
        elif " - " in stem:
            title_slug = stem.split(" - ", 1)[1].strip()
        else:
            title_slug = stem.strip()
        workspace_dir = paths["literature"] / domain / f"{key} - {title_slug}"
        main_note_path = workspace_dir / f"{key} - {title_slug}.md"
        legacy_flags = _legacy_control_flags(paths, key)

        if workspace_dir.exists():
            if main_note_path.exists() and any(value is not None for value in legacy_flags.values()):
                try:
                    workspace_content = main_note_path.read_text(encoding="utf-8")
                    flat_content = flat_note_path.read_text(encoding="utf-8")
                    updated_content = workspace_content
                    for field in ("do_ocr", "analyze"):
                        legacy_value = legacy_flags[field]
                        if legacy_value is None:
                            continue
                        workspace_value = _read_frontmatter_optional_bool_from_text(workspace_content, field)
                        flat_value = _read_frontmatter_optional_bool_from_text(flat_content, field)
                        if workspace_value is None or workspace_value == flat_value:
                            updated_content = update_frontmatter_field(
                                updated_content,
                                field,
                                "true" if legacy_value else "false",
                            )
                    if updated_content != workspace_content:
                        main_note_path.write_text(updated_content, encoding="utf-8")
                except Exception:
                    pass
            continue

        # Create workspace directory
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Read flat note content
        content = flat_note_path.read_text(encoding="utf-8")
        if legacy_flags["do_ocr"] is not None:
            content = update_frontmatter_field(content, "do_ocr", "true" if legacy_flags["do_ocr"] else "false")
        if legacy_flags["analyze"] is not None:
            content = update_frontmatter_field(content, "analyze", "true" if legacy_flags["analyze"] else "false")

        # Write main note to workspace (copy of flat note)
        main_note_path.write_text(content, encoding="utf-8")

        # Extract deep-reading section and write to separate file
        preserved = extract_preserved_deep_reading(content)
        if preserved:
            deep_reading_path = workspace_dir / "deep-reading.md"
            deep_reading_path.write_text(preserved, encoding="utf-8")

        # Create ai/ directory
        ai_dir = workspace_dir / "ai"
        ai_dir.mkdir(exist_ok=True)

        # WS-04: Bridge OCR fulltext to workspace if available
        meta_path = paths.get("ocr", Path()) / key / "meta.json"
        if meta_path.exists():
            try:
                meta = read_json(meta_path)
                if meta.get("ocr_status") == "done":
                    source_fulltext = meta_path.parent / "fulltext.md"
                    target_fulltext = workspace_dir / "fulltext.md"
                    if source_fulltext.exists() and not target_fulltext.exists():
                        import shutil
                        shutil.copy2(str(source_fulltext), str(target_fulltext))
            except Exception:
                pass

        migrated += 1

    if migrated > 0:
        print(f"migrate_to_workspace: migrated {migrated} paper(s) to workspace structure")

    return migrated


def run_index_refresh(vault: Path, verbose: bool = False, rebuild_index: bool = False) -> int:
    """Refresh the canonical asset index.

    Default behavior: full rebuild. This is the safe default because
    selection-sync may affect many papers. Workers that modify individual
    papers (ocr, deep-reading, repair) use asset_index.refresh_index_entry()
    for incremental refresh by key.

    Args:
        vault: Path to the vault root.
        verbose: If True, print detailed progress.
        rebuild_index: If True, force full rebuild (default: True for sync).
    """
    from paperforge.worker.base_views import ensure_base_views
    from paperforge.worker.ocr import validate_ocr_meta

    paths = pipeline_paths(vault)
    config = load_domain_config(paths)
    ensure_base_views(vault, paths, config)
    domain_lookup = {entry["export_file"]: entry["domain"] for entry in config["domains"]}

    cfg = load_vault_config(vault)
    zotero_dir = vault / cfg.get("system_dir", "System") / "Zotero"
    exports = {}
    for export_path in sorted(paths["exports"].glob("*.json")):
        domain = domain_lookup.get(export_path.name, export_path.stem)
        export_rows = load_export_rows(export_path)
        exports[domain] = {row["key"]: row for row in export_rows}
    # Migrate flat notes to workspace before build_index (D-11: first-sync migration)
    migrate_to_workspace(vault, paths)
    # Delegate to asset_index.build_index() for the core build loop
    count = asset_index.build_index(vault, verbose)
    control_records_dir = paths["literature"]
    if control_records_dir.exists():
        for domain_dir in control_records_dir.iterdir():
            if not domain_dir.is_dir():
                continue
            domain = domain_dir.name
            domain_export_keys = set(exports.get(domain, {}).keys())
            records_by_title = {}
            records_info = {}
            for record_file in domain_dir.rglob("*.md"):
                if record_file.name in ("fulltext.md", "deep-reading.md", "discussion.md"):
                    continue
                try:
                    content = record_file.read_text(encoding="utf-8")
                    key_match = re.search(r"^zotero_key:\s*(.+)$", content, re.MULTILINE)
                    if not key_match:
                        continue
                    key = key_match.group(1).strip()
                    title_match = re.search("^title:\\s*[\"\\']?(.+)[\"\\']?\\s*$", content, re.MULTILINE)
                    title = title_match.group(1) if title_match else ""
                    has_pdf = "has_pdf: true" in content
                    normalized = re.sub("[^a-z0-9]", "", title.lower())[:20]
                    records_info[key] = {
                        "file": record_file,
                        "title": title,
                        "has_pdf": has_pdf,
                        "normalized": normalized,
                    }
                    if normalized not in records_by_title:
                        records_by_title[normalized] = []
                    records_by_title[normalized].append(key)
                except Exception:
                    continue
            to_delete = []
            for normalized, keys in records_by_title.items():
                keys_in_export = [k for k in keys if k in domain_export_keys]
                keys_not_in_export = [k for k in keys if k not in domain_export_keys]
                if keys_in_export and keys_not_in_export:
                    for k in keys_not_in_export:
                        if not records_info[k]["has_pdf"]:
                            to_delete.append(k)
            deleted_count = 0
            for key in to_delete:
                try:
                    records_info[key]["file"].unlink()
                    deleted_count += 1
                except Exception:
                    pass
            if deleted_count > 0:
                print(f"index-refresh: cleaned {deleted_count} orphaned records in {domain}")

    # Clean up flat notes: delete only if confirmed by canonical index + workspace
    index_data = asset_index.read_index(vault)
    ws_keys = set()
    if isinstance(index_data, dict):
        for item in index_data.get("items", []):
            ws_dir = paths["literature"] / item.get("domain", "") / (item.get("zotero_key", "") + " - " + slugify_filename(item.get("title", "")))
            if ws_dir.is_dir():
                ws_keys.add(item.get("zotero_key"))

    lit_dir = paths["literature"]
    cleaned_flat = 0
    if lit_dir.exists() and ws_keys:
        for domain_dir in sorted(lit_dir.iterdir()):
            if not domain_dir.is_dir():
                continue
            for flat_note in list(domain_dir.glob("*.md")):
                try:
                    text = flat_note.read_text(encoding="utf-8")
                    m = re.search(r"^zotero_key:\s*\"?(\S+?)\"?\s*$", text, re.MULTILINE)
                    key = m.group(1) if m else ""
                except Exception:
                    continue
                if key and key in ws_keys:
                    try:
                        flat_note.unlink()
                        cleaned_flat += 1
                    except Exception:
                        pass
    if cleaned_flat > 0:
        print(f"index-refresh: cleaned {cleaned_flat} flat note(s) (migrated to workspace)")

    if control_records_dir.exists():
        total = sum(1 for _ in control_records_dir.rglob("*.md"))
        print(f"index-refresh: {total} formal note(s) in literature")

    return 0
