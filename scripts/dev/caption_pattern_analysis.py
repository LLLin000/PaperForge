"""
Scan all 739 papers in the ocr vault for figure caption patterns.
Count each format, cross-reference against figure-map.json inventory,
and report matched/unmatched rates per pattern.

Output: scripts/dev/caption_pattern_analysis.json
"""

import json
import re
import sys
import traceback
from pathlib import Path
from collections import defaultdict, Counter

OCR_ROOT = Path("D:/L/OB/Literature-hub/System/PaperForge/ocr")

# Patterns for classification
# Order matters: more specific patterns first
PATTERNS = [
    # ---- Standard numeric ----
    ("figure_n_numeric", re.compile(
        r'\b(?:Figure|Fig\.?)\s+(\d+)\b', re.IGNORECASE
    )),
    # ---- Supplementary patterns ----
    ("figure_s_numeric", re.compile(
        r'\b(?:Figure|Fig\.?)\s+S(\d+)\b', re.IGNORECASE
    )),
    ("suppl_figure", re.compile(
        r'\b(?:Supplementary|Supplemental|Suppl\.?)\s+(?:Figure|Fig\.?)\s*(\d*)\b', re.IGNORECASE
    )),
    # ---- Appendix patterns ----
    ("figure_appendix_letter_number", re.compile(
        r'\b(?:Figure|Fig\.?)\s+([A-Z])(\d+)\b'
    )),
    ("appendix_figure", re.compile(
        r'\b(?:Appendix|Appx\.?|App\.?)\s+(?:Figure|Fig\.?)\s*([A-Z]?\d*)\b', re.IGNORECASE
    )),
    # ---- Letter-only (no number) ----
    ("figure_letter_only", re.compile(
        r'\b(?:Figure|Fig\.?)\s+([A-Z])\b(?!\s*\d)'
    )),
    # ---- Figure with alpha suffix (e.g. Figure 1A, Figure 1a) ----
    ("figure_numeric_alpha", re.compile(
        r'\b(?:Figure|Fig\.?)\s+(\d+)([A-Za-z])\b', re.IGNORECASE
    )),
    # ---- Box (not exactly a figure but some papers use it) ----
    ("box_pattern", re.compile(
        r'\bBox\s+(\d+)\b', re.IGNORECASE
    )),
]

# We'll classify captions into these categories
CATEGORIES = [
    "standard_numeric",       # Figure 1, Fig. 1, Fig 1
    "supplementary",          # Figure S1, Supplementary Figure 1, Suppl. Fig 1
    "appendix",               # Figure A1, Appendix Figure 1
    "letter_only",            # Figure A, Fig. B
    "numeric_alpha",          # Figure 1A, Figure 2b
    "box",                    # Box 1
    "unclassified",           # No figure pattern matched
]


def classify_caption(text):
    """Classify a caption text into one of the categories."""
    if not text or not text.strip():
        return "unclassified", None

    stripped = text.strip()

    # Try patterns in order; first match wins
    for cat, pat in PATTERNS:
        m = pat.search(stripped)
        if m:
            if cat == "figure_n_numeric":
                return "standard_numeric", m.group(1)
            elif cat in ("figure_s_numeric", "suppl_figure"):
                return "supplementary", m.group(0)
            elif cat in ("figure_appendix_letter_number", "appendix_figure"):
                return "appendix", m.group(0)
            elif cat == "figure_letter_only":
                return "letter_only", m.group(1)
            elif cat == "figure_numeric_alpha":
                return "numeric_alpha", m.group(0)
            elif cat == "box_pattern":
                return "box", m.group(0)

    return "unclassified", None


def extract_figure_number(text):
    """Extract best-effort figure label (e.g. '1', 'S1', 'A1', 'A') from text."""
    if not text:
        return None
    stripped = text.strip()

    # Figure S1 or Supplementary Figure 1
    m = re.search(r'\b(?:Figure|Fig\.?)\s+S(\d+)\b', stripped, re.IGNORECASE)
    if m:
        return f"S{m.group(1)}"

    m = re.search(r'\b(?:Supplementary|Supplemental|Suppl\.?)\s+(?:Figure|Fig\.?)\s*(\d+)', stripped, re.IGNORECASE)
    if m:
        return f"S{m.group(1)}"

    # Figure A1 (letter + number)
    m = re.search(r'\b(?:Figure|Fig\.?)\s+([A-Z])(\d+)\b', stripped)
    if m:
        return f"{m.group(1)}{m.group(2)}"

    # Figure 1A (number + alpha suffix)
    m = re.search(r'\b(?:Figure|Fig\.?)\s+(\d+)([A-Za-z])\b', stripped, re.IGNORECASE)
    if m:
        return f"{m.group(1)}{m.group(2).upper()}"

    # Figure N (plain number)
    m = re.search(r'\b(?:Figure|Fig\.?)\s+(\d+)\b', stripped, re.IGNORECASE)
    if m:
        return m.group(1)

    # Letter only
    m = re.search(r'\b(?:Figure|Fig\.?)\s+([A-Z])\b(?!\s*\d)', stripped)
    if m:
        return m.group(1)

    return None


def load_figure_map(paper_dir):
    """Load figure-map.json if it exists. Returns list of figure entries or None."""
    figmap_path = paper_dir / "figure-map.json"
    if not figmap_path.exists():
        return None
    try:
        with open(figmap_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = []
        for fig in data.get("figures", []):
            entries.append({
                "number": fig.get("number"),
                "label": fig.get("label", ""),
                "type": fig.get("type", "main_figure"),
            })
        for fig in data.get("supplementary_figures", []):
            entries.append({
                "number": fig.get("number"),
                "label": fig.get("label", ""),
                "type": "supplementary_figure",
            })
        return entries
    except Exception:
        return None


def figure_map_contains(fig_map_entries, fig_number):
    """Check if a figure number exists in the figure map entries."""
    if not fig_map_entries or not fig_number:
        return False
    for entry in fig_map_entries:
        if entry["number"] == fig_number:
            return True
        # Also match by label
        label_num = re.search(r'(\d+|[A-Z]\d*)$', entry.get("label", ""))
        if label_num and label_num.group(1) == fig_number:
            return True
    return False


def process_paper(paper_dir):
    """Process a single paper's blocks.structured.jsonl."""
    blocks_path = paper_dir / "structure" / "blocks.structured.jsonl"
    if not blocks_path.exists():
        return None

    paper_id = paper_dir.name
    captions = []
    fig_map = load_figure_map(paper_dir)

    try:
        with open(blocks_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    block = json.loads(line)
                except json.JSONDecodeError:
                    continue

                role = block.get("role")
                if role not in ("figure_caption", "figure_caption_candidate"):
                    continue

                text = block.get("text", "")
                category, matched_pattern = classify_caption(text)
                fig_number = extract_figure_number(text)
                in_inventory = figure_map_contains(fig_map, fig_number) if fig_map else None

                captions.append({
                    "paper_id": paper_id,
                    "role": role,
                    "text_preview": text[:120],
                    "category": category,
                    "fig_number": fig_number,
                    "fig_map_exists": fig_map is not None,
                    "in_inventory": in_inventory,
                })
    except Exception as e:
        print(f"  [WARN] Error reading {paper_id}: {e}", file=sys.stderr)
        return None

    return captions


def main():
    paper_dirs = sorted(OCR_ROOT.glob("*/structure/blocks.structured.jsonl"))
    total_papers = len(paper_dirs)
    print(f"Found {total_papers} papers with blocks.structured.jsonl", file=sys.stderr)

    all_captions = []
    papers_with_captions = 0
    papers_with_map = 0
    papers_with_both = 0
    errors = 0

    for i, blocks_path in enumerate(paper_dirs):
        paper_dir = blocks_path.parent.parent
        paper_id = paper_dir.name

        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{total_papers}...", file=sys.stderr)

        result = process_paper(paper_dir)
        if result is None:
            errors += 1
            continue

        if result:
            papers_with_captions += 1
            all_captions.extend(result)

        # Check if figure-map exists
        fig_map_path = paper_dir / "figure-map.json"
        if fig_map_path.exists():
            papers_with_map += 1

    print(f"\nProcessed: {total_papers} papers", file=sys.stderr)
    print(f"  Papers with captions: {papers_with_captions}", file=sys.stderr)
    print(f"  Papers with figure-map.json: {papers_with_map}", file=sys.stderr)
    print(f"  Total caption blocks: {len(all_captions)}", file=sys.stderr)
    print(f"  Errors: {errors}", file=sys.stderr)

    # ---- Analysis ----

    # 1. Distribution by category
    cat_counts = Counter(c["category"] for c in all_captions)
    cat_with_map = Counter(c["category"] for c in all_captions if c["fig_map_exists"])

    # 2. Per-category: matched vs unmatched in inventory
    # Only count captions from papers that HAVE a figure-map
    cat_matched = Counter()
    cat_unmatched = Counter()
    cat_without_map = Counter()
    for c in all_captions:
        cat = c["category"]
        if c["fig_map_exists"]:
            if c["in_inventory"] is True:
                cat_matched[cat] += 1
            elif c["in_inventory"] is False:
                cat_unmatched[cat] += 1
            else:
                cat_without_map[cat] += 1  # shouldn't happen since fig_map_exists is True
        else:
            cat_without_map[cat] += 1

    # 3. Detailed breakdown by role
    role_cat_counts = defaultdict(Counter)
    for c in all_captions:
        role_cat_counts[c["role"]][c["category"]] += 1

    # 4. Collect examples for each pattern
    examples_by_cat = defaultdict(list)
    for c in all_captions:
        cat = c["category"]
        if len(examples_by_cat[cat]) < 5:
            examples_by_cat[cat].append(c["text_preview"])

    # 5. Detailed unmatched analysis
    unmatched_by_cat = defaultdict(list)
    for c in all_captions:
        if c["fig_map_exists"] and c["in_inventory"] is False:
            unmatched_by_cat[c["category"]].append({
                "paper_id": c["paper_id"],
                "text_preview": c["text_preview"],
                "fig_number": c["fig_number"],
            })

    # Build result
    total_with_map = sum(cat_counts.get(c, 0) for c in CATEGORIES if c in cat_matched or c in cat_unmatched)

    distribution = {}
    for cat in CATEGORIES:
        total = cat_counts.get(cat, 0)
        matched = cat_matched.get(cat, 0)
        unmatched = cat_unmatched.get(cat, 0)
        no_map = cat_without_map.get(cat, 0)
        with_map = matched + unmatched
        distribution[cat] = {
            "total": total,
            "with_figure_map": with_map,
            "matched_in_inventory": matched,
            "unmatched_in_inventory": unmatched,
            "no_figure_map": no_map,
            "unmatched_rate": round(unmatched / with_map, 4) if with_map > 0 else None,
        }

    result = {
        "summary": {
            "total_papers": total_papers,
            "papers_with_captions": papers_with_captions,
            "papers_with_figure_map": papers_with_map,
            "total_caption_blocks": len(all_captions),
            "errors": errors,
        },
        "caption_role_breakdown": {
            role: dict(counts) for role, counts in sorted(role_cat_counts.items())
        },
        "pattern_distribution": distribution,
        "examples_by_category": dict(examples_by_cat),
        "unmatched_details": {
            cat: entries[:20] for cat, entries in sorted(unmatched_by_cat.items())
            if entries
        },
    }

    output_path = Path("scripts/dev/caption_pattern_analysis.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to {output_path}", file=sys.stderr)

    # ---- Print summary to stdout ----
    print("\n" + "=" * 70)
    print("  CAPTION PATTERN ANALYSIS RESULTS")
    print("=" * 70)
    print(f"  Papers scanned:      {total_papers}")
    print(f"  Papers w/ captions:  {papers_with_captions}")
    print(f"  Papers w/ figure-map:{papers_with_map}")
    print(f"  Total caption blocks: {len(all_captions)}")
    print(f"  Errors:               {errors}")
    print()

    # Role breakdown
    print("  --- Role Breakdown ---")
    for role, counts in sorted(role_cat_counts.items()):
        total_role = sum(counts.values())
        print(f"  {role}: {total_role}")
        for cat, cnt in sorted(counts.items()):
            print(f"      {cat}: {cnt}")
    print()

    # Pattern distribution
    print("  --- Pattern Distribution & Unmatched Rate ---")
    print(f"  {'Category':<25} {'Total':>8} {'WithMap':>8} {'Matched':>8} {'Unmatched':>8} {'UnmatchRate':>12}")
    print(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*12}")
    for cat in CATEGORIES:
        d = distribution[cat]
        rate_str = f"{d['unmatched_rate']*100:.1f}%" if d['unmatched_rate'] is not None else "N/A"
        print(f"  {cat:<25} {d['total']:>8} {d['with_figure_map']:>8} {d['matched_in_inventory']:>8} {d['unmatched_in_inventory']:>8} {rate_str:>12}")

    # Extra: unclassified examples
    if examples_by_cat.get("unclassified"):
        print(f"\n  --- Sample Unclassified Captions (first 5) ---")
        for ex in examples_by_cat["unclassified"][:5]:
            print(f"    \"{ex}\"")

    print("=" * 70)


if __name__ == "__main__":
    main()
