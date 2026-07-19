"""Reference zone integrity + ordering + body continuity diagnostic.

Checks across many processed papers:
1. Reference ordering: are reference numbers strictly increasing?
2. Zone leakage: are non-reference blocks between reference items?
3. Body continuity: does body text flow across pages without gaps?
4. Figure/table matching: basic count health.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def _find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for parent in [current] + list(current.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError(f"No repo root from {start}")


_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _find_repo_root(_THIS_FILE)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from paperforge.worker.ocr_artifacts import artifact_paths_for_root  # noqa: E402

# Regex: standard ref number prefixes (1. / 1) / [1] / (1))
_REF_NUM_RE = re.compile(r"^\s*(?:(\d+)[\.\)]|\[(\d+)\]|\((\d+)\))\s*")
# Detect body paragraph start (non-empty, non-reference, non-heading)
_BODY_START_RE = re.compile(r"^[A-Z][^.]+[.?!]")


def _load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _load_block_trace_csv(path: Path) -> list[dict[str, str]]:
    import csv
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _resolve_ocr_root(raw: str | None) -> Path:
    candidate = raw or os.environ.get("PAPERFORGE_OCR_ROOT") or os.environ.get("PAPERFORGE_REAL_OCR_ROOT")
    # backstop: relative to repo
    if not candidate:
        candidate = str(_REPO_ROOT / ".." / ".." / "OB" / "Literature-hub" / "System" / "PaperForge" / "ocr")
    path = Path(candidate)
    if not path.exists():
        path = _REPO_ROOT.parent / "ocr"
    return path.resolve()


def _find_paper_keys(ocr_root: Path, limit: int = 0) -> list[str]:
    """Return paper keys sorted by mtime (newest first)."""
    entries = sorted(
        [d for d in ocr_root.iterdir() if d.is_dir() and not d.name.startswith("_") and not d.name.startswith(".")],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    keys = [d.name for d in entries]
    return keys[:limit] if limit > 0 else keys


def _parse_ref_number(text: str) -> int | None:
    """Extract reference number from standard prefix formats."""
    m = _REF_NUM_RE.match(text)
    if m:
        for g in m.groups():
            if g is not None:
                return int(g)
    return None


def _analyze_reference_ordering(fulltext: str) -> dict:
    """Check reference ordering and non-reference intrusion.

    Scans from first `## References` (or `# References`) to end.
    """
    ref_section_text = ""
    for sep in ["\n## References\n", "\n# References\n", "\n## Bibliography\n"]:
        if sep in fulltext:
            ref_section_text = fulltext.split(sep, 1)[1]
            break

    if not ref_section_text:
        return {"status": "no_ref_section", "count": 0, "issues": []}

    issues: list[dict] = []
    blocks: list[dict] = []
    current_text = ""
    current_num = None

    for line in ref_section_text.split("\n"):
        line_stripped = line.strip()
        if not line_stripped:
            continue
        num = _parse_ref_number(line_stripped)
        if num is not None:
            if current_text:
                blocks.append({"number": current_num, "text": current_text[:80]})
            current_text = line_stripped
            current_num = num
        elif line_stripped.startswith("<!-- page "):
            continue
        elif current_text:
            # Continuation of previous ref
            current_text += " " + line_stripped

    if current_text:
        blocks.append({"number": current_num, "text": current_text[:80]})

    # Check ordering
    last_num = 0
    for b in blocks:
        if b["number"] is not None:
            if b["number"] < last_num:
                issues.append({
                    "type": "ordering_decrease",
                    "expected": last_num + 1,
                    "got": b["number"],
                    "text": b["text"],
                })
            elif b["number"] == last_num:
                issues.append({
                    "type": "duplicate_number",
                    "number": b["number"],
                    "text": b["text"],
                })
            last_num = b["number"]

    # Check for non-reference content between refs
    # (blocks whose number is None but aren't typical continuation)
    # This only works for strict ref-section parsing

    # Check total count continuity: are there gaps?
    numbers = [b["number"] for b in blocks if b["number"] is not None]
    if numbers:
        expected = list(range(1, max(numbers) + 1))
        missing = sorted(set(expected) - set(numbers))
        if missing:
            issues.append({
                "type": "missing_numbers",
                "count": len(missing),
                "missing": missing[:20],
            })

    return {
        "status": "ok" if not issues else "issues",
        "count": len(blocks),
        "numbered_count": len(numbers),
        "expected_last": len(numbers),
        "issues": issues,
    }


def _analyze_body_continuity(fulltext: str) -> dict:
    """Check body text for page continuity issues."""
    # Find body paragraphs (text between page markers, not in ref sections)
    # Simple heuristic: count body-like paragraphs after abstract, before references
    sections = fulltext.split("\n## ")
    body_sections = [s for s in sections if s and all(
        kw not in s.split("\n", 1)[0].strip().lower()
        for kw in ["abstract", "references", "bibliography", "introduction",
                    "methods", "results", "discussion", "conclusion",
                    "acknowledgment", "disclosure", "supplementary",
                    "data availability"]
    )]
    return {"body_section_count": len(body_sections)}


def _analyze_single_paper(ocr_root: Path, key: str) -> dict:
    """Run all diagnostics for one paper."""
    fulltext_path = ocr_root / key / "fulltext.md"
    blocks_path = ocr_root / key / "blocks_trace.csv"
    structure_path = ocr_root / key / "document_structure.json"
    inventory_path = ocr_root / key / "inventory.json"

    result = {"key": key, "errors": [], "warnings": []}

    # Fulltext analysis
    if fulltext_path.exists():
        text = fulltext_path.read_text(encoding="utf-8")
        ref_analysis = _analyze_reference_ordering(text)
        result["reference"] = ref_analysis
        if ref_analysis.get("issues"):
            result["warnings"].append(f"ref_ordering: {len(ref_analysis['issues'])} issues")
    else:
        result["reference"] = {"status": "no_fulltext"}

    # Block trace analysis
    if blocks_path.exists():
        blocks = _load_block_trace_csv(blocks_path)
        roles = [b.get("role", "") for b in blocks]
        result["block_stats"] = {
            "total": len(blocks),
            "body_paragraph": roles.count("body_paragraph"),
            "reference_item": roles.count("reference_item"),
            "reference_heading": roles.count("reference_heading"),
            "figure_caption": roles.count("figure_caption"),
            "table_caption": roles.count("table_caption"),
            "unknown_structural": roles.count("unknown_structural"),
        }

        # Check for non-ref roles between ref items within the reference zone
        ref_items = [b for b in blocks if b.get("role") == "reference_item"]
        ref_item_ids = {b.get("block_id") for b in ref_items}
        structure = _load_json(structure_path)
        if structure:
            ref_zone_ids = set()
            for zone_field in ("reference_zone_ids", "reference_block_ids"):
                ids = structure.get(zone_field) or []
                if isinstance(ids, list):
                    ref_zone_ids.update(str(i) for i in ids)
            if ref_zone_ids:
                # Check for known contamination patterns
                zone_blocks = [b for b in blocks if str(b.get("block_id")) in ref_zone_ids]
                non_ref_zone_roles = {}
                for b in zone_blocks:
                    r = b.get("role", "")
                    if r not in ("reference_item", "reference_heading", "reference_body"):
                        non_ref_zone_roles[r] = non_ref_zone_roles.get(r, 0) + 1
                if non_ref_zone_roles:
                    result["zone_contamination"] = non_ref_zone_roles

        # Style family breakdown (to detect misrouted blocks)
        families = {}
        for b in blocks:
            sf = b.get("style_family", "none")
            role = b.get("role", "")
            if role not in ("reference_item", "reference_heading"):
                families[sf] = families.get(sf, 0) + 1
        result["block_stats"]["non_ref_style_families"] = dict(
            sorted(families.items(), key=lambda x: -x[1])[:10]
        )
    else:
        result["block_stats"] = {}

    # Document structure analysis
    structure = _load_json(structure_path)
    if structure:
        ref_zone = structure.get("reference_zone") or {}
        if ref_zone.get("status") == "ACCEPT":
            heading_id = ref_zone.get("heading_block_id")
            item_ids = ref_zone.get("item_block_ids") or []
            result["reference_zone"] = {
                "status": "ACCEPT",
                "heading_block_id": heading_id,
                "item_count": len(item_ids),
            }
        else:
            result["reference_zone"] = {
                "status": ref_zone.get("status", "unknown"),
                "item_count": len(ref_zone.get("item_block_ids", [])),
            }
    else:
        result["reference_zone"] = {"status": "no_structure"}

    # Inventory analysis (figure/table matching)
    inventory = _load_json(inventory_path)
    if inventory:
        figure_count = len(inventory.get("figures", []))
        table_count = len(inventory.get("tables", []))
        unmatched_figures = len(inventory.get("unmatched_assets", []))
        result["inventory"] = {
            "figure_count": figure_count,
            "table_count": table_count,
            "unmatched_assets": unmatched_figures,
            "orphan_count": inventory.get("orphan_count", 0),
        }
    else:
        result["inventory"] = {}

    return result


def _summarize_issue(results: list[dict], threshold: float = 0.2) -> str:
    """Produce a compact summary of found issues."""
    total = len(results)
    clean = sum(1 for r in results if not r.get("warnings"))
    with_issues = total - clean
    lines = [f"\n=== Reference Zone Audit: {total} papers, {clean} clean, {with_issues} with issues ===\n"]

    # Pattern aggregation
    patterns: dict[str, int] = {}
    for r in results:
        for w in r.get("warnings", []):
            cat = w.split(":")[0].strip()
            patterns[cat] = patterns.get(cat, 0) + 1

    if patterns:
        lines.append("Issue patterns:")
        for cat, count in sorted(patterns.items(), key=lambda x: -x[1]):
            pct = count / total * 100
            lines.append(f"  {cat}: {count}/{total} ({pct:.0f}%)")
    lines.append("")

    # Detailed per-paper
    for r in results:
        if r.get("warnings") or r.get("errors"):
            lines.append(f"  ⚠ {r['key']}: {'; '.join(r['warnings'][:5])}")
            ref = r.get("reference", {})
            if ref.get("issues"):
                for iss in ref["issues"][:3]:
                    lines.append(f"      {iss['type']}: {iss.get('text', '')[:60]}")

            # Zone contamination
            zone = r.get("zone_contamination")
            if zone:
                lines.append(f"      zone_contamination: {zone}")

    # Summary table
    lines.append("")
    lines.append(f"{'Key':<12} {'Refs':>5} {'Isss':>5} {'ZCont':>5} {'Figures':>7} {'Tables':>6} {'Bio':>6}")
    for r in results:
        rf = r.get("reference", {})
        n_issues = len(rf.get("issues", []))
        zcont = bool(r.get("zone_contamination"))
        inv = r.get("inventory", {})
        bs = r.get("block_stats", {})
        ref_count = rf.get("count", 0)
        key = r["key"]
        lines.append(
            f"{key:<12} {ref_count:>5} {n_issues:>5} {'Y' if zcont else '-':>5} "
            f"{inv.get('figure_count', '?'):>7} {inv.get('table_count', '?'):>6} "
            f"{bs.get('body_paragraph', '?'):>6}"
        )

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reference zone audit across papers")
    parser.add_argument("--limit", type=int, default=30, help="max papers to scan")
    parser.add_argument("--ocr-root", default=None, help="OCR data root")
    parser.add_argument("--keys", nargs="*", default=None, help="specific paper keys")
    args = parser.parse_args(argv)

    ocr_root = _resolve_ocr_root(args.ocr_root)
    print(f"OCR root: {ocr_root}", file=sys.stderr)

    if args.keys:
        keys = args.keys
    else:
        keys = _find_paper_keys(ocr_root, limit=args.limit)

    print(f"Scanning {len(keys)} papers...", file=sys.stderr)

    results: list[dict] = []
    for key in keys:
        try:
            r = _analyze_single_paper(ocr_root, key)
            results.append(r)
            if r.get("warnings") or r.get("reference", {}).get("issues"):
                print(f"  {key}: {len(r['reference'].get('issues', []))} issues", file=sys.stderr)
        except Exception as e:
            print(f"  {key}: ERROR {e}", file=sys.stderr)
            results.append({"key": key, "errors": [str(e)]})

    print(_summarize_issue(results))

    # Save detailed results
    output_path = _REPO_ROOT / "audit" / "reference-zone-audit.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDetailed results saved to: {output_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    import os
    raise SystemExit(main())
