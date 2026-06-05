from __future__ import annotations

import re
from pathlib import Path

from paperforge.worker.ocr_roles import FRONTMATTER_NOISE


def _normalize_latex(text: str) -> str:
    text = re.sub(r'\$\s+', '$', text)
    text = re.sub(r'\s+\$', '$', text)
    text = re.sub(r'\$\^\{\s+', '$^{', text)
    text = re.sub(r'\s+\}\$', '}$', text)
    return text


def render_fulltext_markdown(
    *,
    structured_blocks: list[dict],
    resolved_metadata: dict,
    figure_inventory: dict,
    table_inventory: dict,
) -> str:
    lines: list[str] = []

    # --- title ---
    title = resolved_metadata.get("title", {}).get("value", "")
    if title:
        lines.append(f"# {title}")
        lines.append("")

    # --- authors ---
    authors = resolved_metadata.get("authors", {}).get("value", [])
    if authors:
        lines.append(f"**Authors:** {', '.join(authors)}")
        lines.append("")

    # --- metadata block ---
    journal = resolved_metadata.get("journal", {}).get("value", "")
    year = resolved_metadata.get("year", {}).get("value", 0)
    doi = resolved_metadata.get("doi", {}).get("value", "")
    meta_parts: list[str] = []
    if journal:
        meta_parts.append(f"**Journal:** {journal}")
    if year:
        meta_parts.append(f"**Year:** {year}")
    if doi:
        meta_parts.append(f"**DOI:** {doi}")
    if meta_parts:
        lines.extend(meta_parts)
        lines.append("")

    # --- abstract ---
    abstract_blocks = [
        b
        for b in structured_blocks
        if b.get("role") in ("abstract_heading", "abstract_body") and b.get("render_default", True)
    ]
    if abstract_blocks:
        lines.append("## Abstract")
        lines.append("")
        for block in abstract_blocks:
            if block.get("role") == "abstract_body":
                text = block.get("text", "")
                if text:
                    lines.append(_normalize_latex(text))
                    lines.append("")

    # Build per-page figure/table lookups
    figures_by_page: dict[int, list[str]] = {}
    for i, fig in enumerate(figure_inventory.get("matched_figures", [])):
        fig_id = fig.get("figure_id") or f"figure_{i + 1:03d}"
        page = fig.get("page", 0)
        figures_by_page.setdefault(page, []).append(fig_id)

    tables_by_page: dict[int, list[str]] = {}
    for i, tbl in enumerate(table_inventory.get("tables", [])):
        if tbl.get("has_asset"):
            tbl_id = tbl.get("table_id") or f"table_{i + 1:03d}"
            page = tbl.get("page", 0)
            tables_by_page.setdefault(page, []).append(tbl_id)

    emitted_pages: set[int] = set()

    # --- body with anchored figures/tables ---
    current_page: int | None = None
    for block in structured_blocks:
        if not block.get("render_default", True):
            continue
        role = block.get("role", "")
        if role in ("abstract_heading", "abstract_body", "figure_caption", "table_caption", "frontmatter_noise"):
            continue

        text = _normalize_latex(block.get("text", ""))
        block_page = block.get("page")

        if block_page is not None and block_page != current_page:
            # Emit objects for pages between old and new page
            # This handles pages that had no renderable blocks (e.g. only figure_caption)
            if current_page is not None:
                for p in range(current_page, block_page):
                    for fig_id in figures_by_page.get(p, []):
                        lines.append(f"![[render/figures/{fig_id}.md]]")
                        lines.append("")
                    for tbl_id in tables_by_page.get(p, []):
                        lines.append(f"![[render/tables/{tbl_id}.md]]")
                        lines.append("")
                    emitted_pages.add(p)
            current_page = block_page
            lines.append(f"<!-- page {block_page} -->")
            lines.append("")

        if role == "section_heading":
            if text.strip().lower() in FRONTMATTER_NOISE:
                continue
            lines.append(f"## {text}")
            lines.append("")
        elif role == "subsection_heading":
            lines.append(f"### {text}")
            lines.append("")
        elif role == "body_paragraph":
            if text:
                lines.append(text)
                lines.append("")
        else:
            if text:
                lines.append(text)
                lines.append("")

    # Emit objects for the last rendered page
    if current_page is not None:
        for fig_id in figures_by_page.get(current_page, []):
            lines.append(f"![[render/figures/{fig_id}.md]]")
            lines.append("")
        for tbl_id in tables_by_page.get(current_page, []):
            lines.append(f"![[render/tables/{tbl_id}.md]]")
            lines.append("")
        emitted_pages.add(current_page)

    # Emit any remaining pages not covered by body transitions
    all_object_pages = sorted(set(figures_by_page.keys()) | set(tables_by_page.keys()))
    for p in all_object_pages:
        if p not in emitted_pages:
            for fig_id in figures_by_page.get(p, []):
                lines.append(f"![[render/figures/{fig_id}.md]]")
                lines.append("")
            for tbl_id in tables_by_page.get(p, []):
                lines.append(f"![[render/tables/{tbl_id}.md]]")
                lines.append("")

    return "\n".join(lines).strip() + "\n"


def write_render_outputs(render_root: Path, compat_fulltext: Path, markdown: str) -> None:
    render_root.mkdir(parents=True, exist_ok=True)
    (render_root / "fulltext.md").write_text(markdown, encoding="utf-8")
    compat_fulltext.write_text(markdown, encoding="utf-8")
