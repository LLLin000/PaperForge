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


def pipeline_paths(vault: Path) -> dict[str, Path]:
    """Build complete PaperForge path inventory — delegates to shared resolver.

    Returns paths from paperforge.config.paperforge_paths() plus
    worker-only keys. Preserves all legacy keys for existing callers.
    """
    shared = paperforge_paths(vault)

    root = shared["paperforge"]
    control_root = shared["control"]

    return {
        **shared,
        # Worker-only keys (added on top of shared resolver output)
        "pipeline": root,
        "candidates": root / "candidates" / "candidates.json",
        "candidate_inbox": root / "candidates" / "inbox",
        "candidate_archive": root / "candidates" / "archive",
        "search_tasks": root / "search" / "tasks",
        "search_archive": root / "search" / "archive",
        "search_results": root / "search" / "results",
        "harvest_root": root / "skill-prototypes" / "zotero-review-manuscript-writer",
        "records": control_root / "candidate-records",
        "review": root / "candidates" / "review-latest.md",
        "config": root / "config" / "domain-collections.json",
        "queue": root / "writeback" / "writeback-queue.jsonl",
        "log": root / "writeback" / "writeback-log.jsonl",
        "bridge_config": root / "zotero-bridge" / "bridge-config.json",
        "bridge_config_sample": root / "zotero-bridge" / "bridge-config.sample.json",
        "index": root / "indexes" / "formal-library.json",
        "ocr_queue": root / "ocr" / "ocr-queue.json",
    }


def load_domain_config(paths: dict[str, Path]) -> dict:
    """Load or create the Lite domain mapping from export JSON files."""
    config_path = paths["config"]
    config = read_json(config_path) if config_path.exists() else {"domains": []}
    domains = config.setdefault("domains", [])
    known_exports = {str(entry.get("export_file", "")) for entry in domains}
    changed = not config_path.exists()
    for export_path in sorted(paths["exports"].glob("*.json")):
        if export_path.name in known_exports:
            continue
        domains.append({"domain": export_path.stem, "export_file": export_path.name, "allowed_collections": []})
        known_exports.add(export_path.name)
        changed = True
    if changed:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(config_path, config)
    return config


def base_markdown_filter(path: Path, vault: Path) -> str:
    try:
        return str(path.relative_to(vault)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


PAPERFORGE_VIEW_PREFIX = "# PAPERFORGE_VIEW: "


def build_base_views(domain: str) -> list[dict]:
    """Build the 8-view list for a domain Base file.

    Args:
        domain: The domain name (e.g., "骨科") — passed for compatibility but each view has fixed name/filter.

    Returns:
        List of 8 view dicts, each with keys: name (str), order (list), filter (str|None).
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
            "filter": "analyze = true AND recommend_analyze = true",
        },
        {
            "name": "待 OCR",
            "order": ["year", "first_author", "title", "has_pdf", "do_ocr", "ocr_status", "pdf_path"],
            "filter": 'do_ocr = true AND ocr_status = "pending"',
        },
        {
            "name": "OCR 完成",
            "order": ["year", "first_author", "title", "has_pdf", "do_ocr", "ocr_status", "pdf_path"],
            "filter": 'ocr_status = "done"',
        },
        {
            "name": "待深度阅读",
            "order": ["year", "first_author", "title", "has_pdf", "do_ocr", "analyze", "ocr_status", "deep_reading_status", "pdf_path"],
            "filter": 'analyze = true AND ocr_status = "done" AND deep_reading_status = "pending"',
        },
        {
            "name": "深度阅读完成",
            "order": ["year", "first_author", "title", "has_pdf", "do_ocr", "analyze", "ocr_status", "deep_reading_status", "pdf_path"],
            "filter": 'deep_reading_status = "done"',
        },
        {
            "name": "正式卡片",
            "order": ["title", "year", "first_author", "journal", "impact_factor", "has_pdf", "deep_reading_status", "pdf_path"],
            "filter": 'deep_reading_status = "done"',
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
        "LIBRARY_RECORDS": paths.get("library_records"),
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
            lines.append(f"    filter: '{v['filter']}'")
    return "\n".join(lines)


def merge_base_views(existing_content: str | None, new_views: list[dict]) -> str:
    """Incrementally merge standard PaperForge views into an existing .base file.

    Strategy:
    - PaperForge generates exactly 8 views with known names (STANDARD_VIEW_NAMES).
    - Any OTHER views in the existing file are user-defined and MUST be preserved.
    - Each PaperForge view is preceded by a PAPERFORGE_VIEW_PREFIX comment marker.
    - On refresh: replace ALL PaperForge views (identified by prefix) with fresh ones.
    - User views (no prefix) are left completely untouched.

    Args:
        existing_content: Raw text of existing .base file (or None/empty for fresh generation).
        new_views: List of 8 view dicts from build_base_views().

    Returns:
        Merged .base file content with PaperForge views updated, user views preserved.
    """
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
            rendered += f"    filter: '{v['filter']}'\n"
        else:
            rendered += "\n"
        new_pf_blocks.append((v["name"], rendered))

    rebuilt_views_lines = []
    pf_names_seen = set()
    i = views_start_idx + 1
    pending_pf_view_name = None
    while i < len(lines):
        line = lines[i]

        if line.startswith(PAPERFORGE_VIEW_PREFIX):
            pending_pf_view_name = line[len(PAPERFORGE_VIEW_PREFIX) :].strip()
            pf_names_seen.add(pending_pf_view_name)
            i += 1
            continue
        elif pending_pf_view_name is not None and line.strip().startswith("- type: table"):
            pf_block = next((b for n, b in new_pf_blocks if n == pending_pf_view_name), None)
            if pf_block:
                rebuilt_views_lines.append(pf_block)
            pending_pf_view_name = None
            i += 1
            continue
        elif line.strip().startswith("- type: table"):
            pending_pf_view_name = None
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
            rebuilt_views_lines.append("\n".join(view_block_lines))
            continue
        else:
            pending_pf_view_name = None
            i += 1

    for view_name, pf_block in new_pf_blocks:
        if view_name not in pf_names_seen:
            rebuilt_views_lines.append(pf_block)

    result_lines = header_lines + rebuilt_views_lines
    return "\n".join(result_lines)


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
            views_yaml += f"    filter: '{v['filter']}'\n"
        else:
            views_yaml += "\n"
    views_yaml = views_yaml.rstrip("\n")
    return f"""filters:
  and:
    - file.inFolder("{folder_filter}")
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
    """Generate/refresh Domain Base files with incremental merge (preserves user views).

    Each PaperForge standard view is marked with PAPERFORGE_VIEW_PREFIX. On refresh,
    only PaperForge views are replaced; user-defined views are preserved.
    """
    paths["bases"].mkdir(parents=True, exist_ok=True)

    def refresh_base(base_path: Path, folder_filter: str, views: list[dict]) -> None:
        """Refresh a single .base file: merge PaperForge views, preserve user views."""
        if base_path.exists() and not force:
            existing = base_path.read_text(encoding="utf-8")
            merged = merge_base_views(existing, views)
        else:
            merged = _build_base_yaml(folder_filter, views)
        merged = substitute_config_placeholders(merged, paths)
        base_path.write_text(merged, encoding="utf-8")

    seen_domains = set()
    for entry in config.get("domains", []):
        domain = str(entry.get("domain", "") or "").strip()
        if not domain or domain in seen_domains:
            continue
        seen_domains.add(domain)

        domain_views = build_base_views(domain)
        folder_filter = f"${{LIBRARY_RECORDS}}/{domain}"
        base_path = paths["bases"] / f"{slugify_filename(domain)}.base"
        refresh_base(base_path, folder_filter, domain_views)

    hub_views = build_base_views("Literature Hub")
    hub_path = paths["bases"] / "Literature Hub.base"
    refresh_base(hub_path, "${LIBRARY_RECORDS}", hub_views)

    # PaperForge.base intentionally removed (v1.4.1) — duplicates Literature Hub
