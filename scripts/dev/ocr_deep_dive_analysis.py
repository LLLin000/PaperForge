"""Deep-dive: analyze real OCR problems found by batch audit.

Investigates:
1. unknown_structural blocks — what content are they? (text samples)
2. Reference number gaps — are refs missing from fulltext or just misnumbered?
3. Backmatter leak to reference zone — which blocks and why?
4. Extreme outlier papers (9ZIJTI6J, WS6T79MU)
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


def _load_blocks_jsonl(path: Path) -> list[dict]:
    blocks: list[dict] = []
    if not path.exists():
        return blocks
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                blocks.append(json.loads(line))
    return blocks


def _text(block: dict) -> str:
    return str(block.get("text") or block.get("block_content") or "")


def _analyze_unknowns(ocr_root: Path, keys: list[str]) -> None:
    """Sample text content of unknown_structural blocks by zone."""
    print("=" * 70)
    print("ANALYSIS 1: unknown_structural blocks — content sampling")
    print("=" * 70)

    by_zone: dict[str, list[tuple[str, str]]] = defaultdict(list)  # zone -> [(key, text)]

    for key in keys:
        paper_dir = ocr_root / key
        blocks = _load_blocks_jsonl(paper_dir / "structure" / "blocks.structured.jsonl")
        for b in blocks:
            if b.get("role") == "unknown_structural":
                zone = str(b.get("zone", "unzoned"))
                txt = _text(b)[:150]
                by_zone[zone].append((key, txt))

    for zone, samples in sorted(by_zone.items(), key=lambda x: -len(x[1])):
        print(f"\n## Zone: {zone} ({len(samples)} blocks)")
        # Show unique text patterns
        patterns = Counter()
        for _, txt in samples:
            # First 60 chars as pattern key
            pattern = txt[:60].strip()
            if pattern:
                patterns[pattern] += 1
        print("Top text patterns:")
        for pat, cnt in patterns.most_common(20):
            print(f"  [{cnt}x] {pat}")
        # Show a few random full samples
        print("Sample entries:")
        for key, txt in samples[:5]:
            print(f"  [{key}] zone={zone} | {txt}"[:200])


def _analyze_ref_gaps(ocr_root: Path, keys: list[str]) -> None:
    """Analyze reference number gaps — check if refs are in blocks but not in fulltext."""
    print("\n" + "=" * 70)
    print("ANALYSIS 2: Reference number gaps — block vs fulltext comparison")
    print("=" * 70)

    for key in keys[:15]:  # top 15 gap papers
        paper_dir = ocr_root / key
        blocks = _load_blocks_jsonl(paper_dir / "structure" / "blocks.structured.jsonl")
        ft_path = paper_dir / "fulltext.md"
        ft_text = ft_path.read_text(encoding="utf-8") if ft_path.exists() else ""

        # Extract ref numbers from blocks
        block_refs: set[int] = set()
        for b in blocks:
            role = b.get("role", "")
            if role in ("reference_item",):
                txt = _text(b)
                m = re.match(r"^\s*(\d+)", txt)
                if m:
                    block_refs.add(int(m.group(1)))

        # Extract ref numbers from fulltext
        ft_refs = set()
        for m in re.finditer(r"^(\d+)\.\s", ft_text, re.MULTILINE):
            ft_refs.add(int(m.group(1)))

        # Which numbers are in blocks but missing from fulltext?
        in_blocks_not_ft = sorted(block_refs - ft_refs)
        # Which numbers are in fulltext but not as explicit refs?
        # (This checks the ref_item count vs fulltext count)
        n_block = len(block_refs)
        n_ft = len(ft_refs)

        if in_blocks_not_ft or n_block != n_ft:
            print(f"\n{key}: {n_block} refs in blocks, {n_ft} refs in fulltext")
            if in_blocks_not_ft:
                print(f"  Blocks not in fulltext: {in_blocks_not_ft[:20]}")
            # Show block roles around the gap
            max_ref = max(block_refs) if block_refs else 0
            gaps = sorted(set(range(1, max_ref + 1)) - block_refs)
            if gaps:
                print(f"  Missing ref numbers (neither block nor ft): {gaps[:20]}")
                # Are there body_paragraph blocks that look like refs?
                for b in blocks:
                    txt = _text(b)
                    if b.get("role") == "body_paragraph" and re.match(r"^\d+\.\s", txt.strip()):
                        print(f"  Possible unclassified ref in body_paragraph: {txt[:100]}")


def _analyze_backmatter_leak(ocr_root: Path, keys: list[str]) -> None:
    """Analyze papers with backmatter/body blocks leaking into reference zone."""
    print("\n" + "=" * 70)
    print("ANALYSIS 3: Backmatter/body leak to reference zone")
    print("=" * 70)

    for key in keys:
        paper_dir = ocr_root / key
        blocks = _load_blocks_jsonl(paper_dir / "structure" / "blocks.structured.jsonl")
        ft_path = paper_dir / "fulltext.md"
        ft_text = ft_path.read_text(encoding="utf-8") if ft_path.exists() else ""

        leak_blocks = []
        for b in blocks:
            zone = str(b.get("zone", ""))
            role = b.get("role", "")
            if "reference" in zone and role in ("backmatter_body", "body_paragraph"):
                leak_blocks.append(b)
                print(f"  [{key}] zone={zone} role={role} | {_text(b)[:100]}")

        if leak_blocks:
            print(f"\n{key}: {len(leak_blocks)} leak blocks")
            # Check if fulltext shows these blocks
            for b in leak_blocks:
                txt = _text(b)[:60].strip()
                if txt and txt not in ft_text:
                    print(f"  NOT in fulltext: {txt}")


def _analyze_catastrophic(ocr_root: Path, keys: list[str]) -> None:
    """Deep analysis of catastrophic failure papers."""
    print("\n" + "=" * 70)
    print("ANALYSIS 4: Catastrophic failure papers")
    print("=" * 70)

    for key in keys:
        paper_dir = ocr_root / key
        ds_path = paper_dir / "structure" / "document_structure.json"
        ds = json.loads(ds_path.read_text(encoding="utf-8")) if ds_path.exists() else {}
        blocks = _load_blocks_jsonl(paper_dir / "structure" / "blocks.structured.jsonl")
        ft_path = paper_dir / "fulltext.md"
        ft_text = ft_path.read_text(encoding="utf-8") if ft_path.exists() else ""

        print(f"\n## {key}")
        print(f"  Figures: {len(ds.get('figure_inventory', []))}")
        print(f"  Tables: {len(ds.get('table_inventory', []))}")
        print(f"  Total blocks: {len(blocks)}")
        print(f"  Fulltext length: {len(ft_text)} chars")

        # Role distribution
        role_counts = Counter(b.get("role", "") for b in blocks)
        print(f"  Top roles: {role_counts.most_common(10)}")

        # Zone distribution
        zone_counts = Counter(str(b.get("zone", "")) for b in blocks)
        print(f"  Top zones: {zone_counts.most_common(10)}")

        # Show blocks that are in body_zone but unknown
        unknowns = [b for b in blocks if b.get("role") == "unknown_structural"]
        if unknowns:
            print(f"  unknown_structural sample:")
            for b in unknowns[:10]:
                print(f"    zone={b.get('zone')} text={_text(b)[:100]}")

        # Show fulltext first 500 chars
        print(f"  Fulltext first 500 chars:")
        print(f"    {ft_text[:500].replace(chr(10), chr(10)+'    ')}")

        # Show last 500 chars
        print(f"  Fulltext last 500 chars:")
        print(f"    {ft_text[-500:].replace(chr(10), chr(10)+'    ')}")


def main() -> int:
    ocr_root = Path(
        os.environ.get("PAPERFORGE_OCR_ROOT") or os.environ.get("PAPERFORGE_REAL_OCR_ROOT")
        or "D:/L/OB/Literature-hub/System/PaperForge/ocr"
    )

    # Find the 200 most recent papers with data
    all_dirs = sorted([d for d in ocr_root.iterdir() if d.is_dir() and not d.name.startswith(".")],
                      key=lambda d: -d.stat().st_mtime)
    all_keys = [d.name for d in all_dirs if (d / "structure" / "blocks.structured.jsonl").exists()]
    print(f"Total available papers: {len(all_keys)}")
    sample_keys = all_keys[:200]

    # 1. unknown_structural deep-dive
    _analyze_unknowns(ocr_root, sample_keys)

    # 2. Find papers with ref gaps for deep analysis
    gap_papers = []
    for key in sample_keys[:200]:
        paper_dir = ocr_root / key
        ft_path = paper_dir / "fulltext.md"
        if not ft_path.exists():
            continue
        ft_text = ft_path.read_text(encoding="utf-8")
        ref_nums = re.findall(r"^(\d+)\.\s", ft_text, re.MULTILINE)
        if ref_nums:
            nums = sorted(int(n) for n in ref_nums)
            expected = list(range(1, nums[-1] + 1))
            if sorted(set(expected) - set(nums)):
                gap_papers.append(key)
    print(f"\nRef gap papers in top 200: {len(gap_papers)}")
    _analyze_ref_gaps(ocr_root, gap_papers[:15])

    # 3. Find papers with backmatter leak to ref zone
    leak_papers = []
    for key in sample_keys:
        paper_dir = ocr_root / key
        blocks = _load_blocks_jsonl(paper_dir / "structure" / "blocks.structured.jsonl")
        for b in blocks:
            zone = str(b.get("zone", ""))
            role = b.get("role", "")
            if "reference" in zone and role in ("backmatter_body", "body_paragraph"):
                leak_papers.append(key)
                break
    print(f"\nBackmatter leak to ref zone papers: {len(leak_papers)}")
    _analyze_backmatter_leak(ocr_root, leak_papers)

    # 4. Catastrophic papers
    _analyze_catastrophic(ocr_root, ["9ZIJTI6J", "WS6T79MU"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
