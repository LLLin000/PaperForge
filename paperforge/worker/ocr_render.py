from __future__ import annotations

from pathlib import Path
from typing import Any


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

    # --- metadata block: journal, year, DOI ---
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
        if b.get("role") in ("abstract_heading", "abstract_body")
        and b.get("render_default", True)
    ]
    if abstract_blocks:
        lines.append("## Abstract")
        lines.append("")
        for block in abstract_blocks:
            if block.get("role") == "abstract_body":
                text = block.get("text", "")
                if text:
                    lines.append(text)
                    lines.append("")

    # --- body ---
    current_page: int | None = None
    for block in structured_blocks:
        if not block.get("render_default", True):
            continue
        role = block.get("role", "")
        if role in ("abstract_heading", "abstract_body", "figure_caption", "table_caption"):
            continue

        text = block.get("text", "")

        block_page = block.get("page")
        if block_page is not None and block_page != current_page:
            current_page = block_page
            lines.append(f"<!-- page {block_page} -->")
            lines.append("")

        if role == "section_heading":
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

    # --- figures ---
    for i, fig in enumerate(figure_inventory.get("matched_figures", [])):
        fig_id = fig.get("figure_id") or f"figure_{i + 1:03d}"
        lines.append(f"![[render/figures/{fig_id}.md]]")
        lines.append("")

    # --- tables ---
    for i, tbl in enumerate(table_inventory.get("tables", [])):
        if tbl.get("has_asset"):
            tbl_id = tbl.get("table_id") or f"table_{i + 1:03d}"
            lines.append(f"![[render/tables/{tbl_id}.md]]")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def write_render_outputs(render_root: Path, compat_fulltext: Path, markdown: str) -> None:
    render_root.mkdir(parents=True, exist_ok=True)
    (render_root / "fulltext.md").write_text(markdown, encoding="utf-8")
    compat_fulltext.write_text(markdown, encoding="utf-8")
