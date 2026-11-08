"""Read-only Figure/Table lifecycle audit for OCR artifacts."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

INVARIANTS = ("duplicate_identity", "broken_embed", "missing_delivery", "orphan_embedded")
FIGURE_EMBED = re.compile(r"!\[\[render/figures/([^]\|]+\.md)(?:\|[^\]]*)?\]\]")
TABLE_EMBED = re.compile(r"!\[\[render/tables/([^]\|]+\.md)(?:\|[^\]]*)?\]\]")


def _json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def _entries(inventory: Any, names: tuple[str, ...]) -> list[dict]:
    if not isinstance(inventory, dict):
        return []
    return [entry for name in names for entry in inventory.get(name, [])
            if isinstance(entry, dict)]


def _nonempty(value: Any) -> bool:
    return bool(value.strip()) if isinstance(value, str) else bool(value)


def audit_paper(paper_dir: Path) -> dict:
    paper_dir = Path(paper_dir)
    figure_inventory = _json(paper_dir / "structure/figure_inventory.json", {})
    table_inventory = _json(paper_dir / "structure/table_inventory.json", {})
    figures = _entries(figure_inventory, ("matched_figures", "held_figures", "ambiguous_figures"))
    tables = _entries(table_inventory, ("tables", "held_tables"))
    figure_counts = Counter(str(f.get("figure_id", "")) for f in figures if f.get("figure_id"))
    figure_ids = set(figure_counts)
    duplicate_ids = sorted(key for key, count in figure_counts.items() if count > 1)
    render_figures = paper_dir / "render/figures"
    render_tables = paper_dir / "render/tables"
    figure_mds = sorted(p.stem for p in render_figures.glob("*.md")) if render_figures.is_dir() else []
    table_mds = sorted(p.stem for p in render_tables.glob("*.md")) if render_tables.is_dir() else []
    fulltext_path = paper_dir / "render/fulltext.md"
    if not fulltext_path.is_file():
        fulltext_path = paper_dir / "fulltext.md"
    try:
        fulltext = fulltext_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        fulltext = ""
    embed_matches = list(FIGURE_EMBED.finditer(fulltext))
    embeds = [match.group(1)[:-3] for match in embed_matches]
    embedded = set(embeds)
    canonical_mds = [stem for stem in figure_mds if not stem.startswith("orphan_")]
    figure_md_set = set(canonical_mds)
    orphan_mds = [stem for stem in figure_mds if stem not in figure_ids]
    orphan_set = set(orphan_mds)
    orphan_embed_matches = [match for match in embed_matches if match.group(1)[:-3] in orphan_set]
    orphan_embeds = [{"paper": paper_dir.name, "text": match.group(0)} for match in orphan_embed_matches]
    tables_embeds = TABLE_EMBED.findall(fulltext)

    blocks_path = paper_dir / "structure/blocks.structured.jsonl"
    rows = []
    try:
        for line in blocks_path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    rows.append(item)
            except json.JSONDecodeError:
                continue
    except (OSError, UnicodeError):
        pass
    claims: set[str] = set()
    for figure in figures:
        claims.update(str(x) for x in figure.get("consumed_block_ids", []) if x is not None)
        for asset in figure.get("matched_assets", []) or []:
            if isinstance(asset, dict) and asset.get("block_id") is not None:
                claims.add(str(asset["block_id"]))
        claims.update(str(x) for x in figure.get("asset_block_ids", []) if x is not None)
    for table in tables:
        for key in ("consumed_block_ids", "asset_block_ids"):
            claims.update(str(x) for x in table.get(key, []) if x is not None)
        for key in ("asset_block_id", "caption_block_id"):
            if table.get(key) is not None:
                claims.add(str(table[key]))
        claims.update(str(x) for x in table.get("note_block_ids", []) if x is not None)
    inner_rows = [r for r in rows if r.get("role") == "figure_inner_text"]
    owned_inner = [r for r in inner_rows if _nonempty(r.get("_object_owner_id"))]
    owner_no_claim = [r for r in rows if _nonempty(r.get("_object_owner_id")) and
                      str(r.get("block_id")) not in claims]
    orphan_asset_dir = paper_dir / "assets/orphans"
    orphan_jpgs = list(orphan_asset_dir.glob("*.jpg")) if orphan_asset_dir.is_dir() else []

    table_md_content = {}
    if render_tables.is_dir():
        for path in render_tables.glob("*.md"):
            try:
                table_md_content[path.stem] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                table_md_content[path.stem] = ""
    def table_missing(field: str) -> int:
        return sum(not _nonempty(_json_table_field(content, field)) for content in table_md_content.values())
    def table_notes_missing() -> int:
        missing = 0
        for index, table in enumerate(_entries(table_inventory, ("tables",)), 1):
            if not _nonempty(table.get("note_texts")):
                continue
            content = table_md_content.get(f"table_{index:03d}", "")
            if not re.search(r"(?im)^## Notes\b", content):
                missing += 1
        return missing

    result = {
        "has_inventory": (paper_dir / "structure/figure_inventory.json").is_file() or
                         (paper_dir / "structure/table_inventory.json").is_file(),
        "paper": paper_dir.name,
        "identity": {
            "figures_total": len(figures), "unique_figure_ids": len(figure_ids),
            "duplicate_id_extra": sum(count - 1 for count in figure_counts.values() if count > 1),
            "duplicate_id_papers": int(bool(duplicate_ids)), "duplicate_id_paths": duplicate_ids,
            "figures_without_assets": sum(not _figure_has_assets(f) for f in figures),
            "figures_without_number": sum(f.get("figure_number") in (None, "") for f in figures),
        },
        "delivery": {
            "figure_md_count": len(canonical_mds), "canonical_figure_md_count": len(canonical_mds),
            "canonical_md_missing": sorted(figure_ids - figure_md_set), "figure_embeds": len(embeds),
            "unique_ids_not_embedded": sorted(figure_ids - embedded),
            "unique_ids_missing_md": sorted(figure_ids - figure_md_set),
            "embeds_missing_md": sorted(set(embeds) - figure_md_set),
            "md_never_embedded": sorted(set(canonical_mds) - embedded),
        },
        "orphans": {
            "orphan_md_count": len(orphan_mds), "orphan_jpg_count": len(orphan_jpgs),
            "embedded_orphan_count": len(orphan_embed_matches),
        },
        "orphan_embeds": orphan_embeds,
        "tables": {
            "tables_total": len(tables), "no_asset": sum(not _figure_has_assets(t) for t in tables),
            "with_html": sum(_nonempty(t.get("assistive_text")) for t in tables),
            "with_notes": sum(_nonempty(t.get("notes") or t.get("note_texts")) for t in tables),
            "continuation": sum(bool(t.get("continuation") or t.get("is_continuation")) for t in tables),
            "table_md_count": len(table_mds), "md_missing_caption": table_missing("caption"),
            "md_missing_image": table_missing("image"),
            "tables_with_notes_missing_md_notes": table_notes_missing(),
            "table_embeds_in_fulltext": len(tables_embeds),
        },
        "ownership": {
            "figure_inner_text_rows": len(inner_rows), "owned_figure_inner_text_rows": len(owned_inner),
            "rows_with_object_consumed": sum(bool(r.get("_object_consumed")) for r in rows),
            "rows_owner_without_inventory_claim": len(owner_no_claim),
            "rows_post_match_role_override": sum(_nonempty(r.get("_post_match_role_override")) for r in rows),
        },
    }
    result["violations"] = {
        "duplicate_identity": result["identity"]["duplicate_id_extra"] > 0,
        "broken_embed": bool(result["delivery"]["embeds_missing_md"]),
        "missing_delivery": bool(result["delivery"]["unique_ids_not_embedded"]),
        "orphan_embedded": result["orphans"]["embedded_orphan_count"] > 0,
    }
    return result


def _figure_has_assets(entry: dict) -> bool:
    if isinstance(entry.get("has_asset"), bool):
        return entry["has_asset"]
    return any(entry.get(key) for key in ("matched_assets", "assets", "asset_block_ids"))


def _json_table_field(markdown: str, field: str) -> Any:
    """Interpret the common rendered table markdown markers."""
    if field == "caption":
        return re.search(r"(?im)^\s*(?:#+\s*)?(?:Table\s+\S|表\s*\S)", markdown)
    if field == "image":
        return re.search(r"!\[[^]]*\]\([^)]*\)|!\[\[[^]]+\]\]", markdown)
    return re.search(r"(?im)^\s*(?:Notes?|注)\s*:", markdown)


def _totals(papers: list[dict]) -> dict:
    sections = ("identity", "delivery", "orphans", "tables", "ownership")
    totals: dict[str, Any] = {
        "papers_scanned": len(papers),
        "papers_with_inventory": sum(bool(paper["has_inventory"]) for paper in papers),
    }
    for section in sections:
        values: dict[str, Any] = {}
        keys = sorted({k for paper in papers for k, v in paper[section].items() if isinstance(v, int)})
        for key in keys:
            values[key] = sum(paper[section].get(key, 0) for paper in papers)
        totals[section] = values
    totals["violations"] = {name: any(p["violations"][name] for p in papers) for name in INVARIANTS}
    return totals


def audit_corpus(ocr_root: Path, keys: list[str] | None = None, limit: int | None = None) -> dict:
    root = Path(ocr_root)
    selected = sorted((root / key for key in keys), key=lambda p: p.name) if keys else sorted(
        (p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name) if root.is_dir() else []
    if limit is not None:
        selected = selected[:max(0, limit)]
    papers = [audit_paper(path) for path in selected]
    return {"papers": papers, "orphan_embeds": [item for paper in papers for item in paper["orphan_embeds"]],
            "totals": _totals(papers)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--vault", type=Path, help="Obsidian vault root")
    source.add_argument("--ocr-root", type=Path, help="OCR corpus root")
    parser.add_argument("--keys", nargs="+", help="Paper keys to audit")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--fail-on", default="", help="Comma-separated invariants")
    args = parser.parse_args(argv)
    root = args.ocr_root or args.vault / "System/PaperForge/ocr"
    report = audit_corpus(root, args.keys, args.limit)
    selected = {name.strip() for name in args.fail_on.split(",") if name.strip()}
    unknown = selected - set(INVARIANTS)
    if unknown:
        parser.error(f"unknown --fail-on invariant(s): {', '.join(sorted(unknown))}")
    report["selected_failures"] = sorted(name for name in selected if report["totals"]["violations"][name])
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return int(bool(report["selected_failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
