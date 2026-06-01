from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from paperforge.worker._utils import (
    slugify_filename,
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
    """Build the 4-view list for a domain Base file.

    Uses workflow gate columns (has_pdf, do_ocr, analyze, ocr_status)
    matching the master version's Base views.  See REQUIREMENTS.md
    §Reference Vault Learnings for the ground-truth pattern.

    Args:
        domain: The domain name (e.g., "骨科").

    Returns:
        List of 4 view dicts, each with keys: name, order, filter, sort.
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
            "name": "待 OCR",
            "order": ["year", "first_author", "title", "has_pdf", "do_ocr", "ocr_status", "pdf_path"],
            "filter": 'do_ocr == true && ocr_status == "pending"',
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
            "filter": 'analyze == true && ocr_status == "done" && deep_reading_status == "pending"',
        },
        {
            "name": "重做OCR",
            "order": ["year", "first_author", "title", "ocr_redo", "ocr_status"],
            "filter": 'ocr_status == "done"',
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
            lines.append(f"    filter: '{v['filter']}'")
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


def merge_base_views(existing_content: str | None, new_views: list[dict], folder_filter: str = "") -> str:
    """Incrementally merge standard PaperForge views into an existing .base file.

    Strategy:
    - PaperForge generates exactly 4 views with known names.
    - Any OTHER views in the existing file are user-defined and MUST be preserved.
    - Each PaperForge view is preceded by a PAPERFORGE_VIEW_PREFIX comment marker.
    - On refresh: replace ALL PaperForge views (identified by prefix) with fresh ones.
    - User views (no prefix) are left completely untouched.
    - User-adjusted column widths are preserved across refreshes.

    Args:
        existing_content: Raw text of existing .base file (or None/empty for fresh generation).
        new_views: List of 4 view dicts from build_base_views().
        folder_filter: Vault-relative folder path for file.inFolder() (used for fresh generation).

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
  ocr_redo:
    displayName: "重做OCR"
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
    - file.inFolder("{folder_filter}")
    - file.ext == "md"
    - !zotero_key.isEmpty()
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
        if v.get("sort"):
            rendered += "    sort:\n"
            for sort_item in v["sort"]:
                rendered += f"      - field: {sort_item['field']}\n"
                rendered += f"        direction: {sort_item['direction']}\n"
        new_pf_blocks.append((v["name"], rendered))

    rebuilt_views_lines = []
    pf_names_seen = set()
    pf_view_names = {name for name, _ in new_pf_blocks}
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
            name_match = re.search(r'name:\s*"([^"]*)"', block_text)
            if name_match and name_match.group(1) in pf_view_names:
                continue
            rebuilt_views_lines.append(block_text)
            continue

        else:
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
    - !zotero_key.isEmpty()
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
  ocr_redo:
    displayName: "重做OCR"
  deep_reading_status:
    displayName: "Deep Reading"
  pdf_path:
    displayName: "PDF Path"
  fulltext_md_path:
    displayName: "Fulltext"
views:
{views_yaml}"""


def _sanitize_base_file(content: str, views: list[dict], folder_filter: str) -> str:
    """Minimally sanitize a .base file: deduplicate views, fix syntax, ensure standard views exist.

    This function does NOT modify existing view content (columns, filters, widths, sort).
    It only:
    1. Removes duplicate views with the same name (keeps PF-prefixed, then first occurrence).
    2. Fixes common syntax issues (quoted !zotero_key.isEmpty(), broken ocr_redo placement).
    3. Updates the folder filter for file.inFolder().
    4. Ensures the 4 standard views exist (appends missing ones with PAPERFORGE_VIEW_PREFIX).
    5. Ensures ocr_redo property exists at the correct position in properties section.
    6. Other views are left completely untouched.
    """
    STANDARD_NAMES = {v["name"] for v in views}

    # --- Phase 1: split into header (pre-views:) and view blocks ---
    lines = content.split("\n")
    views_start_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("views:"):
            views_start_idx = i
            break

    if views_start_idx is None:
        # Missing views: section — treat whole file as header, append views
        header = content.rstrip("\n")
        if not header.endswith("\n"):
            header += "\n"
        fresh_views_yaml = _render_views_section(views)
        return f"{header}\nviews:\n{fresh_views_yaml}\n"

    header_lines = lines[: views_start_idx + 1]
    view_body_lines = lines[views_start_idx + 1 :]

    # --- Phase 2: parse view blocks ---
    # A view block is either: PAPERFORGE_VIEW_PREFIX + indented block, or - type: table + indented block
    view_blocks = []  # list of (is_pf: bool, view_name: str, block_text: str)
    i = 0
    while i < len(view_body_lines):
        line = view_body_lines[i]
        if not line.strip():
            i += 1
            continue

        if line.startswith(PAPERFORGE_VIEW_PREFIX):
            view_name = line[len(PAPERFORGE_VIEW_PREFIX):].strip()
            block_lines = [line]
            i += 1
            type_table_count = 0
            while i < len(view_body_lines):
                next_line = view_body_lines[i]
                if next_line.strip().startswith(PAPERFORGE_VIEW_PREFIX):
                    break
                if next_line.strip().startswith("- type: table"):
                    if type_table_count >= 1:
                        break
                    type_table_count += 1
                if next_line.strip() and not next_line.startswith(" ") and not next_line.startswith("\t"):
                    break
                block_lines.append(next_line)
                i += 1
            view_blocks.append((True, view_name, "\n".join(block_lines)))
            continue

        elif line.strip().startswith("- type: table"):
            block_lines = [line]
            i += 1
            while i < len(view_body_lines):
                next_line = view_body_lines[i]
                if next_line.strip().startswith(PAPERFORGE_VIEW_PREFIX):
                    break
                if next_line.strip().startswith("- type: table"):
                    break
                if next_line.strip() and not next_line.startswith(" ") and not next_line.startswith("\t"):
                    break
                block_lines.append(next_line)
                i += 1
            block_text = "\n".join(block_lines)
            name_match = re.search(r'name:\s*"?([^"]*)"?', block_text)
            view_name = name_match.group(1) if name_match else ""
            view_blocks.append((False, view_name, block_text))
            continue
        else:
            i += 1

    # --- Phase 3: deduplicate ---
    # For each view name, keep PF-prefixed if exists, otherwise first occurrence
    deduped: dict[str, str] = {}  # view_name -> block_text (NO prefix included for non-PF)
    for is_pf, view_name, block_text in view_blocks:
        if not view_name:
            continue
        if view_name in deduped:
            if is_pf:
                # PF block wins over user block
                deduped[view_name] = block_text
            # else: keep existing (first occurrence or existing PF)
        else:
            deduped[view_name] = block_text

    # --- Phase 4: ensure standard views exist ---
    # For each standard name NOT in deduped, generate a fresh PF view block
    # For existing standard views, keep them AS-IS (don't replace content)
    for v in views:
        if v["name"] not in deduped:
            block = f"{PAPERFORGE_VIEW_PREFIX}{v['name']}\n"
            block += "  - type: table\n"
            block += f'    name: "{v["name"]}"\n'
            block += "    order:\n"
            for col in v["order"]:
                block += f"      - {col}\n"
            if v["filter"]:
                block += f"    filter: '{v['filter']}'\n"
            deduped[v["name"]] = block

    # --- Phase 5: fix properties section ---
    header_text = "\n".join(header_lines)
    header_lines_fixed = header_text.split("\n")

    # 5a: Fix quoted !zotero_key.isEmpty()
    for j in range(len(header_lines_fixed)):
        stripped = header_lines_fixed[j].strip()
        if stripped in ('"!zotero_key.isEmpty()"', "'!zotero_key.isEmpty()'"):
            header_lines_fixed[j] = header_lines_fixed[j].replace('"!zotero_key.isEmpty()"', "!zotero_key.isEmpty()")
            header_lines_fixed[j] = header_lines_fixed[j].replace("'!zotero_key.isEmpty()'", "!zotero_key.isEmpty()")

    # 5b: Fix broken ocr_redo placement (between ocr_status: and its displayName)
    # Strip all existing ocr_redo blocks, then re-insert after ocr_status block
    cleaned = []
    skip_next = False
    for j, line in enumerate(header_lines_fixed):
        if skip_next:
            skip_next = False
            continue
        if line.strip() == "ocr_redo:" and (j + 1 < len(header_lines_fixed)):
            next_stripped = header_lines_fixed[j + 1].strip()
            if "displayName" in next_stripped or next_stripped.startswith("displayName"):
                skip_next = True
                continue
        cleaned.append(line)
    header_lines_fixed = cleaned

    # Find ocr_status block and insert ocr_redo after its displayName
    target_idx = None
    for j, line in enumerate(header_lines_fixed):
        if line.strip() == "ocr_status:":
            # Find the end of ocr_status block (its displayName line, if any)
            if j + 1 < len(header_lines_fixed) and "displayName" in header_lines_fixed[j + 1]:
                target_idx = j + 2  # After displayName
            else:
                target_idx = j + 1  # After ocr_status:
            break

    if target_idx is not None:
        has_redo = any(
            line.strip() == "ocr_redo:" for line in header_lines_fixed[target_idx : target_idx + 2]
        )
        if not has_redo:
            header_lines_fixed.insert(target_idx, "  ocr_redo:")
            header_lines_fixed.insert(target_idx + 1, '    displayName: "重做OCR"')

    # 5c: Update folder filter
    for j in range(len(header_lines_fixed)):
        if 'file.inFolder(' in header_lines_fixed[j]:
            header_lines_fixed[j] = re.sub(
                r'file\.inFolder\("[^"]*"\)',
                f'file.inFolder("{folder_filter}")',
                header_lines_fixed[j],
            )
            break

    # --- Phase 6: rebuild ---
    rebuilt = "\n".join(header_lines_fixed) + "\n"
    # Rebuild view blocks in order: standard views first, then non-standard (preserve original order)
    view_order = []
    seen = set()
    for v in views:
        if v["name"] in deduped and v["name"] not in seen:
            view_order.append(v["name"])
            seen.add(v["name"])
    for view_name in deduped:
        if view_name not in seen:
            view_order.append(view_name)
            seen.add(view_name)

    for view_name in view_order:
        rebuilt += deduped[view_name] + "\n"

    return rebuilt


def ensure_base_views(vault: Path, paths: dict[str, Path], config: dict, force: bool = False) -> None:
    """Generate and minimally sanitize domain Base files.

    For existing files (force=False): sanitizes — dedups views, fixes syntax,
    ensures 4 standard views exist. Does NOT modify existing view content.
    For new files or force=True: generates fresh from template.
    """
    paths["bases"].mkdir(parents=True, exist_ok=True)

    def refresh_base(base_path: Path, folder_filter: str, views: list[dict]) -> None:
        resolved_filter = substitute_config_placeholders(folder_filter, paths)
        if base_path.exists() and not force:
            existing = base_path.read_text(encoding="utf-8")
            sanitized = _sanitize_base_file(existing, views, folder_filter=resolved_filter)
            if sanitized != existing:
                base_path.write_text(sanitized, encoding="utf-8")
            return
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
