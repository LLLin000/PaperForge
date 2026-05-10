from __future__ import annotations

import re
from pathlib import Path
from typing import Optional


def _yaml_quote(value: str) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return '"' + str(value or "").replace("\\", "\\\\").replace('"', '\\"') + '"'


def _yaml_block(value: str) -> list[str]:
    value = (value or "").strip()
    if not value:
        return ["abstract: |-", "  "]
    lines = ["abstract: |-"]
    for line in value.splitlines():
        lines.append(f"  {line}")
    return lines


def compute_final_collection(row: dict) -> str:
    user_raw = str(row.get("user_collection", "") or "").strip()
    user_resolved = str(row.get("user_collection_resolved", "") or "").strip()
    recommended = str(row.get("recommended_collection", "") or "").strip()
    if user_raw:
        return user_resolved
    return recommended


DEEP_READING_HEADER = "## 🔍 精读"


def _read_frontmatter_bool_from_text(text: str, key: str, default: bool = False) -> bool:
    match = re.search(rf"^{re.escape(key)}:\s*(?:[\"'])?(true|false)(?:[\"'])?\s*$", text, re.MULTILINE | re.IGNORECASE)
    if not match:
        return default
    return match.group(1).lower() == "true"


def read_frontmatter_bool(note_path: Path, key: str, default: bool = False) -> bool:
    """Read a boolean field from a formal note's YAML frontmatter (Path-based)."""
    if not note_path or not note_path.exists():
        return default
    try:
        text = note_path.read_text(encoding="utf-8")
        return _read_frontmatter_bool_from_text(text, key, default)
    except Exception:
        return default


def _read_frontmatter_optional_bool_from_text(text: str, key: str) -> Optional[bool]:
    match = re.search(rf"^{re.escape(key)}:\s*(?:[\"'])?(true|false)(?:[\"'])?\s*$", text, re.MULTILINE | re.IGNORECASE)
    if not match:
        return None
    return match.group(1).lower() == "true"


def read_frontmatter_optional_bool(note_path: Path, key: str) -> Optional[bool]:
    """Read an optional boolean field from a formal note's YAML frontmatter (Path-based)."""
    if not note_path or not note_path.exists():
        return None
    try:
        text = note_path.read_text(encoding="utf-8")
        return _read_frontmatter_optional_bool_from_text(text, key)
    except Exception:
        return None


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
                lines.append(f"  - {_yaml_quote(item)}")
        elif value == "":
            lines.append(f"{key}:")
        elif "\n" in str(value):
            lines.extend(
                _yaml_block(str(value)).copy()
                if key == "abstract"
                else [f"{key}: |-"] + [f"  {line}" for line in str(value).splitlines()]
            )
        else:
            lines.append(f"{key}: {_yaml_quote(value)}")
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


def extract_preserved_deep_reading(text: str) -> str:
    if not text:
        return ""
    match = re.search("^## 🔍 精读\\s*$", text, re.MULTILINE)
    if not match:
        return ""
    start = match.start()
    preserved = text[start:].strip()
    return preserved


def has_deep_reading_content(text: str) -> bool:
    preserved = extract_preserved_deep_reading(text)
    if not preserved:
        return False
    body = preserved.replace(DEEP_READING_HEADER, "").strip()
    if not body:
        return False

    clarity_ok = bool(re.search(r"-\s*\*\*Clarity\*\*（清晰度）：(.+)", body)) and not re.search(
        r"-\s*\*\*Clarity\*\*（清晰度）：\s*$", body, re.MULTILINE
    )

    figure_sec = _extract_section(body, r"\*\*Figure 导读\*\*")
    figure_ok = False
    if figure_sec:
        for line in figure_sec.splitlines():
            s = line.strip()
            if s.startswith("- ") and "：" in s:
                _, after = s.split("：", 1)
                if after.strip() and after.strip() != "（待补充）":
                    figure_ok = True
                    break

    issue_sec = _extract_section(body, r"\*\*遗留问题\*\*")
    if not issue_sec:
        issue_sec = _extract_section(body, r"####\s*遗留问题")
    issue_ok = False
    if issue_sec:
        dirty = [l.strip() for l in issue_sec.splitlines() if l.strip()]
        substantive = [l for l in dirty if l not in ("-", "（待补充）", "", "**遗留问题**")]
        issue_ok = bool(substantive)

    return clarity_ok and figure_ok and issue_ok


def _extract_section(body: str, section_header: str) -> str | None:
    m = re.search(
        section_header + r"\n*(.*?)(?=\n(?:#{1,3})\s|\Z)",
        body,
        re.DOTALL,
    )
    if m:
        return m.group(1).strip()
    return None


def _add_missing_frontmatter_fields(existing_content: str, new_fields: dict[str, str]) -> str:
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
            lines_to_add.append(f"{key}: {_yaml_quote(value)}")
    if not lines_to_add:
        return existing_content
    new_frontmatter = frontmatter.rstrip("\n") + "\n" + "\n".join(lines_to_add) + "\n"
    return f"---{new_frontmatter}---{body}"


def update_frontmatter_field(content: str, key: str, value: str) -> str:
    if not content.startswith("---"):
        return content
    pattern = "^" + re.escape(key) + "\\s*:.*$"
    replacement = f"{key}: {_yaml_quote(value)}"
    new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE, count=1)
    if count == 0:
        new_content = _add_missing_frontmatter_fields(content, {key: value})
    return new_content


def read_frontmatter_dict(text: str) -> dict:
    """Parse YAML frontmatter from markdown text using yaml.safe_load.

    Falls back to regex parsing if YAML parser fails (malformed frontmatter).
    Returns empty dict if no frontmatter.
    """
    import re
    import yaml

    fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not fm_match:
        return {}

    try:
        data = yaml.safe_load(fm_match.group(1))
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    result = {}
    for line in fm_match.group(1).splitlines():
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result
