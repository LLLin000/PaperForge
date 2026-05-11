from __future__ import annotations

import logging
import os
from pathlib import Path

from paperforge.config import paperforge_paths
from paperforge.worker._utils import (
    read_json,
    slugify_filename,
    write_json,
)

logger = logging.getLogger(__name__)


def load_simple_env(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and (value[0] in {'"', "'"}):
            value = value[1:-1]
        os.environ[key] = value


def base_markdown_filter(path: Path, vault: Path) -> str:
    try:
        return str(path.relative_to(vault)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


PAPERFORGE_VIEW_PREFIX = "# PAPERFORGE_VIEW: "


def build_base_views(domain: str) -> list[dict]:
    """Build the 8-view list for a domain Base file.

    Uses workflow gate columns (has_pdf, do_ocr, analyze, ocr_status)
    matching the master version's Base views.  See REQUIREMENTS.md
    §Reference Vault Learnings for the ground-truth pattern.

    Args:
        domain: The domain name (e.g., "骨科").

    Returns:
        List of 8 view dicts, each with keys: name, order, filter, sort.
    """
    return [
        {
            "name": "控制面板",
            "order": [
                "file.name",
                "title",
                "year",
                "first_author",
                "journal",
                "impact_factor",
                "has_pdf",
                "do_ocr",
                "analyze",
                "ocr_status",
                "deep_reading_status",
                "pdf_path",
                "fulltext_md_path",
            ],
            "filter": None,
        },
        {
            "name": "推荐分析",
            "order": [
                "year",
                "title",
                "first_author",
                "journal",
                "impact_factor",
                "has_pdf",
                "do_ocr",
                "analyze",
                "ocr_status",
                "deep_reading_status",
                "pdf_path",
                "fulltext_md_path",
            ],
            "filter": "analyze = true AND has_pdf = true",
        },
        {
            "name": "待 OCR",
            "order": ["year", "first_author", "title", "has_pdf", "do_ocr", "ocr_status", "pdf_path"],
            "filter": "do_ocr = true AND ocr_status = 'pending'",
        },
        {
            "name": "OCR 完成",
            "order": ["year", "first_author", "title", "has_pdf", "do_ocr", "ocr_status", "pdf_path"],
            "filter": "ocr_status = 'done'",
        },
        {
            "name": "待深度阅读",
            "order": [
                "year",
                "first_author",
                "title",
                "has_pdf",
                "do_ocr",
                "analyze",
                "ocr_status",
                "deep_reading_status",
                "pdf_path",
            ],
            "filter": "analyze = true AND ocr_status = 'done' AND deep_reading_status = 'pending'",
        },
        {
            "name": "深度阅读完成",
            "order": [
                "year",
                "first_author",
                "title",
                "has_pdf",
                "do_ocr",
                "analyze",
                "ocr_status",
                "deep_reading_status",
                "pdf_path",
            ],
            "filter": "deep_reading_status = 'done'",
        },
        {
            "name": "正式卡片",
            "order": [
                "title",
                "year",
                "first_author",
                "journal",
                "impact_factor",
                "has_pdf",
                "deep_reading_status",
                "pdf_path",
            ],
            "filter": "deep_reading_status = 'done'",
        },
        {
            "name": "全记录",
            "order": [
                "title",
                "year",
                "first_author",
                "journal",
                "impact_factor",
                "has_pdf",
                "do_ocr",
                "analyze",
                "ocr_status",
                "deep_reading_status",
                "pdf_path",
                "fulltext_md_path",
            ],
            "filter": None,
        },
    ]


def substitute_config_placeholders(content: str, paths: dict[str, Path]) -> str:
    """Replace ${SCREAMING_SNAKE_CASE} path placeholders with vault-relative paths.

    Args:
        content: The Base file content string with ${PLACEHOLDER} tokens.
        paths: dict of path key -> Path objects (from paperforge_paths()).

    Returns:
        Content with placeholders replaced by vault-relative paths.
        Unrecognized placeholders are left unchanged.
    """
    substitutions = {
        "LITERATURE": paths.get("literature"),
        "CONTROL_DIR": paths.get("control"),
    }
    result = content
    for key, path in substitutions.items():
        if path is not None:
            vault = paths.get("vault")
            if vault is not None:
                try:
                    rel = path.relative_to(vault)
                    result = result.replace(f"${{{key}}}", str(rel).replace(chr(92), "/"))
                except ValueError:
                    result = result.replace(f"${{{key}}}", str(path).replace(chr(92), "/"))
    return result


def _render_views_section(views: list[dict]) -> str:
    """Render a list of view dicts to YAML views: section."""
    lines = []
    for v in views:
        lines.append("  - type: table")
        lines.append(f'    name: "{v["name"]}"')
        lines.append("    order:")
        for col in v["order"]:
            lines.append(f"      - {col}")
        if v["filter"]:
            lines.append(f'    filter: "{v["filter"]}"')
        if v.get("sort"):
            lines.append("    sort:")
            for sort_item in v["sort"]:
                lines.append(f"      - field: {sort_item['field']}")
                lines.append(f"        direction: {sort_item['direction']}")
    return "\n".join(lines)


def _extract_widths_from_block(text: str) -> dict[str, int] | None:
    """Extract column widths from an existing view block text.

    Args:
        text: Raw text of a single view block (PF prefix line through its last indented line).

    Returns:
        dict of column_name -> width_pixels, or None if no widths found.
    """
    in_widths = False
    widths = {}
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped == "widths:" and not in_widths:
            in_widths = True
            continue
        if in_widths:
            if not stripped:
                break
            if ":" not in stripped:
                break
            key, _, val = stripped.partition(":")
            try:
                widths[key.strip()] = int(val.strip())
            except ValueError:
                pass
    return widths if widths else None


def _inject_widths_into_block(text: str, widths: dict[str, int]) -> str:
    """Inject widths: section into a fresh PF view block after the name: line.

    Args:
        text: Fresh PF view block text (with PF prefix marker).
        widths: Column width mapping to inject.

    Returns:
        Block text with widths section inserted between name: and order:.
    """
    lines = text.split("\n")
    result = []
    injected = False
    for line in lines:
        result.append(line)
        if not injected and line.strip().startswith("name:"):
            result.append("    widths:")
            for col, w in sorted(widths.items()):
                result.append(f"      {col}: {w}")
            injected = True
    return "\n".join(result)


def merge_base_views(existing_content: str | None, new_views: list[dict]) -> str:
    """Incrementally merge standard PaperForge views into an existing .base file.

    Strategy:
    - PaperForge generates exactly 8 views with known names (STANDARD_VIEW_NAMES).
    - Any OTHER views in the existing file are user-defined and MUST be preserved.
    - Each PaperForge view is preceded by a PAPERFORGE_VIEW_PREFIX comment marker.
    - On refresh: replace ALL PaperForge views (identified by prefix) with fresh ones.
    - User views (no prefix) are left completely untouched.
    - User-adjusted column widths are preserved across refreshes.

    Args:
        existing_content: Raw text of existing .base file (or None/empty for fresh generation).
        new_views: List of 8 view dicts from build_base_views().

    Returns:
        Merged .base file content with PaperForge views updated, user views preserved.
    """
    import re

    PROPERTIES_YAML = """properties:
  zotero_key:
    displayName: "Zotero Key"
  title:
    displayName: "Title"
  year:
    displayName: "Year"
  first_author:
    displayName: "First Author"
  journal:
    displayName: "Journal"
  impact_factor:
    displayName: "IF"
  has_pdf:
    displayName: "PDF"
  do_ocr:
    displayName: "OCR"
  analyze:
    displayName: "Analyze"
  ocr_status:
    displayName: "OCR Status"
  deep_reading_status:
    displayName: "Deep Reading"
  pdf_path:
    displayName: "PDF Path"
  fulltext_md_path:
    displayName: "Fulltext"
"""

    if not existing_content or not existing_content.strip():
        fresh_views_yaml = _render_views_section(new_views)
        return f"""filters:
  and:
    - file.inFolder("{new_views[0]["name"]}")
    - file.ext == "md"
    - zotero_key != ""
{PROPERTIES_YAML}
views:
{fresh_views_yaml}"""

    lines = existing_content.split("\n")
    views_start_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("views:"):
            views_start_idx = i
            break

    if views_start_idx is None:
        fresh_views_yaml = _render_views_section(new_views)
        return f"""{existing_content}

# --- PaperForge views regenerated (views: section was missing) ---
{PROPERTIES_YAML}
views:
{fresh_views_yaml}"""

    header_lines = lines[: views_start_idx + 1]

    new_pf_blocks = []
    for v in new_views:
        rendered = f"{PAPERFORGE_VIEW_PREFIX}{v['name']}\n"
        rendered += "  - type: table\n"
        rendered += f'    name: "{v["name"]}"\n'
        rendered += "    order:\n"
        for col in v["order"]:
            rendered += f"      - {col}\n"
        if v["filter"]:
            rendered += f'    filter: "{v["filter"]}"\n'
        else:
            rendered += "\n"
        if v.get("sort"):
            rendered += "    sort:\n"
            for sort_item in v["sort"]:
                rendered += f"      - field: {sort_item['field']}\n"
                rendered += f"        direction: {sort_item['direction']}\n"
        new_pf_blocks.append((v["name"], rendered))

    rebuilt_views_lines = []
    pf_names_seen = set()
    i = views_start_idx + 1
    while i < len(lines):
        line = lines[i]

        if line.startswith(PAPERFORGE_VIEW_PREFIX):
            view_name = line[len(PAPERFORGE_VIEW_PREFIX) :].strip()
            pf_names_seen.add(view_name)
            # Collect the full existing PF view block (PF prefix + all its indented lines)
            old_block_lines = [line]
            i += 1
            type_table_count = 0
            while i < len(lines):
                next_line = lines[i]
                if next_line.strip().startswith(PAPERFORGE_VIEW_PREFIX):
                    break
                if next_line.strip().startswith("- type: table"):
                    if type_table_count >= 1:
                        break
                    type_table_count += 1
                old_block_lines.append(next_line)
                i += 1
            # Get fresh block and inject preserved column widths
            pf_block = next((b for n, b in new_pf_blocks if n == view_name), None)
            if pf_block:
                old_text = "\n".join(old_block_lines)
                widths = _extract_widths_from_block(old_text)
                if widths:
                    pf_block = _inject_widths_into_block(pf_block, widths)
                rebuilt_views_lines.append(pf_block)
            continue

        elif line.strip().startswith("- type: table"):
            view_block_lines = [line]
            i += 1
            while i < len(lines):
                next_line = lines[i]
                if next_line.strip().startswith(PAPERFORGE_VIEW_PREFIX):
                    break
                if next_line.strip().startswith("- type: table"):
                    break
                if next_line.strip() and not next_line.startswith(" ") and not next_line.startswith("\t"):
                    break
                view_block_lines.append(next_line)
                i += 1
            block_text = "\n".join(view_block_lines)
            rebuilt_views_lines.append(block_text)
            continue

        else:
            i += 1

    for view_name, pf_block in new_pf_blocks:
        if view_name not in pf_names_seen:
            rebuilt_views_lines.append(pf_block)

    result_lines = header_lines + rebuilt_views_lines
    return "\n".join(result_lines)


def _update_folder_filter(content: str, new_filter: str) -> str:
    """Update the folder filter in a .base file if it changed."""
    import re

    old_match = re.search(r'file\.inFolder\("([^"]+)"\)', content)
    if not old_match or old_match.group(1) == new_filter:
        return content
    return content.replace(old_match.group(1), new_filter, 1)


def _build_base_yaml(folder_filter: str, views: list[dict]) -> str:
    """Build complete .base YAML with PAPERFORGE_VIEW_PREFIX markers on each view."""
    views_yaml = ""
    for v in views:
        views_yaml += f"{PAPERFORGE_VIEW_PREFIX}{v['name']}\n"
        views_yaml += "  - type: table\n"
        views_yaml += f'    name: "{v["name"]}"\n'
        views_yaml += "    order:\n"
        for col in v["order"]:
            views_yaml += f"      - {col}\n"
        if v["filter"]:
            views_yaml += f'    filter: "{v["filter"]}"\n'
        else:
            views_yaml += "\n"
        if v.get("sort"):
            views_yaml += "    sort:\n"
            for sort_item in v["sort"]:
                views_yaml += f"      - field: {sort_item['field']}\n"
                views_yaml += f"        direction: {sort_item['direction']}\n"
    views_yaml = views_yaml.rstrip("\n")
    return f"""filters:
  and:
    - file.inFolder("{folder_filter}")
    - file.ext == "md"
    - zotero_key != ""
properties:
  zotero_key:
    displayName: "Zotero Key"
  title:
    displayName: "Title"
  year:
    displayName: "Year"
  first_author:
    displayName: "First Author"
  journal:
    displayName: "Journal"
  impact_factor:
    displayName: "IF"
  has_pdf:
    displayName: "PDF"
  do_ocr:
    displayName: "OCR"
  analyze:
    displayName: "Analyze"
  ocr_status:
    displayName: "OCR Status"
  deep_reading_status:
    displayName: "Deep Reading"
  pdf_path:
    displayName: "PDF Path"
  fulltext_md_path:
    displayName: "Fulltext"
views:
{views_yaml}"""


def ensure_base_views(vault: Path, paths: dict[str, Path], config: dict, force: bool = False) -> None:
    """Generate Domain Base files on first run; subsequent calls only update folder filter.

    Base views are static — Obsidian automatically reflects frontmatter changes.
    PaperForge should not regenerate views on every sync; it only ensures:
    1. Base files exist (create on first setup).
    2. Folder filter stays in sync with configured directory paths.
    3. force=True allows full regeneration when explicitly requested.
    """
    paths["bases"].mkdir(parents=True, exist_ok=True)

    def refresh_base(base_path: Path, folder_filter: str, views: list[dict]) -> None:
        resolved_filter = substitute_config_placeholders(folder_filter, paths)
        if base_path.exists() and not force:
            # File exists: only update folder filter if paths changed
            existing = base_path.read_text(encoding="utf-8")
            updated = _update_folder_filter(existing, resolved_filter)
            if updated != existing:
                base_path.write_text(updated, encoding="utf-8")
            return
        # File does not exist (or force=True): generate fresh
        merged = _build_base_yaml(resolved_filter, views)
        merged = substitute_config_placeholders(merged, paths)
        base_path.write_text(merged, encoding="utf-8")

    seen_domains = set()
    for entry in config.get("domains", []):
        domain = str(entry.get("domain", "") or "").strip()
        if not domain or domain in seen_domains:
            continue
        seen_domains.add(domain)

        domain_views = build_base_views(domain)
        folder_filter = f"${{LITERATURE}}/{domain}"
        base_path = paths["bases"] / f"{slugify_filename(domain)}.base"
        refresh_base(base_path, folder_filter, domain_views)

    hub_views = build_base_views("Literature Hub")
    hub_path = paths["bases"] / "Literature Hub.base"
    refresh_base(hub_path, "${LITERATURE}", hub_views)

    # PaperForge.base intentionally removed (v1.4.1) — duplicates Literature Hub
