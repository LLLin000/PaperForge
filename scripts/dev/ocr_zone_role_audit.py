"""Batch zone/role pattern audit — scan all rebuilt papers for systematic misclassification.

Scans by zone (frontmatter, body, backmatter, reference) and finds:
- Unknown_structural blocks (pipeline couldn't classify)
- Suspicious role-zone mismatches (e.g., body_paragraph in backmatter zone)
- Known problematic patterns (bio, disclaimer, conflict of interest)
- Reference zone intrusions
- Role distribution anomalies

Usage:
    python scripts/dev/ocr_zone_role_audit.py [--limit N] [--output PATH]
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── patterns ──────────────────────────────────────────────────────────

_AUTHOR_CONTRIBUTION = re.compile(
    r"^(author contributions?|credit authorship|CRediT authorship|contributors?\b)",
    re.IGNORECASE,
)
_CONFLICT_OF_INTEREST = re.compile(
    r"^(conflicts?\s+of\s+interest|declaration of competing|competing interests?\b|financial disclosure)",
    re.IGNORECASE,
)
_FUNDING = re.compile(
    r"^(funding|funders?\b|financial support|grants?\b|sponsored by)",
    re.IGNORECASE,
)
_DATA_AVAILABILITY = re.compile(
    r"^(data availability|availability of data|code availability|software availability)",
    re.IGNORECASE,
)
_ETHICS = re.compile(
    r"^(ethics?\s+statement|institutional review board|irb approval|animal ethics|ethical approval)",
    re.IGNORECASE,
)
_ACKNOWLEDGMENTS = re.compile(
    r"^(acknowledg(?:e)?ments?\b|acknowledg(?:e)?ment\b)", re.IGNORECASE,
)
_BIO = re.compile(
    r"(author\s+bio(?:graphy)?|biograph|about the author|meet the author|x\.\s+biograph)",
    re.IGNORECASE,
)
_SUPPLEMENTARY = re.compile(
    r"^(supplementary\s+(material|data|information|file)|online\s+supplement|"
    r"supporting\s+(information|material)|appendix\s+[a-z])",
    re.IGNORECASE,
)


# ── data ──────────────────────────────────────────────────────────────

@dataclass
class PaperFindings:
    key: str
    title: str = ""
    frontmatter_unknown: int = 0
    body_unknown: int = 0
    backmatter_unknown: int = 0
    ref_unknown: int = 0
    total_unknown: int = 0
    backmatter_body_in_ref_zone: int = 0
    body_para_in_backmatter_zone: int = 0
    ref_item_in_frontmatter: int = 0
    bio_blocks: list[dict] = field(default_factory=list)
    contribution_blocks: list[dict] = field(default_factory=list)
    conflict_blocks: list[dict] = field(default_factory=list)
    data_avail_blocks: list[dict] = field(default_factory=list)
    disclaimer_blocks: list[dict] = field(default_factory=list)
    ethics_blocks: list[dict] = field(default_factory=list)
    supplementary_blocks: list[dict] = field(default_factory=list)
    render_default_false: int = 0
    zone_role_matrix: dict[str, Counter] = field(default_factory=dict)
    suspicious_patterns: list[str] = field(default_factory=list)
    ref_number_gaps: list[str] = field(default_factory=list)
    figure_count: int = 0
    table_count: int = 0
    degraded_mode: bool = False
    block_count: int = 0

    def suspicious_score(self) -> int:
        return (
            self.total_unknown
            + self.backmatter_body_in_ref_zone
            + self.body_para_in_backmatter_zone
            + self.ref_item_in_frontmatter
            + len(self.bio_blocks)
            + len(self.disclaimer_blocks)
            + len(self.ref_number_gaps)
            + (1 if self.degraded_mode else 0)
        )


# ── helpers ────────────────────────────────────────────────────────────

def _text(block: dict) -> str:
    return str(block.get("text") or block.get("block_content") or "")


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_blocks_jsonl(path: Path) -> list[dict]:
    """Load blocks from JSONL file (one JSON dict per line)."""
    blocks: list[dict] = []
    if not path.exists():
        return blocks
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    blocks.append(json.loads(line))
    except Exception:
        return []
    return blocks


_EXPECTED_ROLES_BY_ZONE: dict[str, set[str]] = {
    "frontmatter_main_zone": {
        "paper_title", "authors", "affiliation", "abstract_heading", "abstract_body",
        "frontmatter_noise", "frontmatter_metadata", "frontmatter_support",
        "body_paragraph", "section_heading", "subsection_heading",
        "frontmatter_body", "noise", "unknown_structural",
        "figure_caption", "figure_asset", "table_caption", "media_asset",
        "keywords",
    },
    "body_flow": {
        "body_paragraph", "section_heading", "subsection_heading", "sub_subsection_heading",
        "figure_caption", "figure_asset", "table_caption", "media_asset",
        "figure_inner_text", "structured_insert", "non_body_insert",
        "noise", "unknown_structural", "table_html", "table_asset",
        "tail_candidate_body",
    },
    "backmatter": {
        "backmatter_body", "backmatter_heading", "backmatter_boundary_heading",
        "reference_heading", "reference_item", "reference_body",
        "body_paragraph", "noise", "footnote", "unknown_structural",
        "section_heading", "subsection_heading",
    },
    "reference_candidate": {
        "reference_heading", "reference_item", "reference_body",
        "body_paragraph", "backmatter_body", "noise", "unknown_structural",
    },
}


def _analyze_one_paper(ocr_root: Path, key: str) -> PaperFindings:
    pf = PaperFindings(key=key)
    paper_dir = ocr_root / key

    # load blocks from structured JSONL
    blocks_path = paper_dir / "structure" / "blocks.structured.jsonl"
    blocks = _load_blocks_jsonl(blocks_path)
    if not blocks:
        pf.suspicious_patterns.append("no_block_data")
        return pf

    pf.block_count = len(blocks)

    # load doc structure for metadata
    ds_path = paper_dir / "structure" / "document_structure.json"
    ds = _load_json(ds_path)
    if ds:
        pf.degraded_mode = ds.get("span_coverage", {}).get("degraded_mode_active", False)
        pf.figure_count = len(ds.get("figure_inventory", []))
        pf.table_count = len(ds.get("table_inventory", []))

    # fulltext for reference number analysis
    ft_path = paper_dir / "fulltext.md"
    ft_text = ft_path.read_text(encoding="utf-8") if ft_path.exists() else ""

    # extract title from first block if available
    for b in blocks[:20]:
        if b.get("role") == "paper_title":
            pf.title = _text(b)[:120]
            break
    if not pf.title and blocks:
        pf.title = _text(blocks[0])[:120]

    # ── zone-role analysis ──
    zone_roles: dict[str, Counter] = defaultdict(Counter)

    for block in blocks:
        role = str(block.get("role") or "unset")
        zone = str(block.get("zone") or "unzoned")
        text = _text(block)
        render_default = block.get("render_default", True)

        zone_roles[zone][role] += 1

        if role == "unknown_structural":
            pf.total_unknown += 1
            if "frontmatter" in zone:
                pf.frontmatter_unknown += 1
            elif "body" in zone:
                pf.body_unknown += 1
            elif "backmatter" in zone:
                pf.backmatter_unknown += 1
            elif "reference" in zone:
                pf.ref_unknown += 1

        if not render_default:
            pf.render_default_false += 1

        # ── zone-role mismatch patterns ──
        if role == "body_paragraph" and "backmatter" in zone:
            pf.body_para_in_backmatter_zone += 1

        if role == "reference_item" and "frontmatter" in zone:
            pf.ref_item_in_frontmatter += 1

        if role in ("backmatter_body", "body_paragraph") and "reference" in zone:
            pf.backmatter_body_in_ref_zone += 1

        # ── text-pattern detection ──
        text_lower = text.strip().lower()

        if _BIO.search(text_lower) and len(text) > 20:
            pf.bio_blocks.append({"role": role, "zone": zone, "text": text[:100]})

        if _AUTHOR_CONTRIBUTION.search(text_lower) and len(text) > 15:
            pf.contribution_blocks.append({"role": role, "zone": zone, "text": text[:80]})

        if _CONFLICT_OF_INTEREST.search(text_lower) and len(text) > 15:
            pf.conflict_blocks.append({"role": role, "zone": zone, "text": text[:80]})

        if _DATA_AVAILABILITY.search(text_lower) and len(text) > 15:
            pf.data_avail_blocks.append({"role": role, "zone": zone, "text": text[:80]})

        if _ETHICS.search(text_lower) and len(text) > 15:
            pf.ethics_blocks.append({"role": role, "zone": zone, "text": text[:80]})

        if _SUPPLEMENTARY.search(text_lower) and len(text) > 15:
            pf.supplementary_blocks.append({"role": role, "zone": zone, "text": text[:80]})

    # look for blocks that look like disclaimers (open access, copyright notice)
    for block in blocks:
        text = _text(block).lower()
        role = str(block.get("role") or "")
        if "this is an open access" in text and len(text) > 20:
            if role not in ("backmatter_body", "noise", "frontmatter_noise"):
                pf.disclaimer_blocks.append({
                    "role": role, "zone": str(block.get("zone", "")), "text": text[:80]
                })

    pf.zone_role_matrix = dict(zone_roles)

    # ── reference number gap analysis from fulltext ──
    if ft_text:
        ref_nums = re.findall(r"^(\d+)\.\s", ft_text, re.MULTILINE)
        if ref_nums:
            nums = sorted(int(n) for n in ref_nums)
            expected = list(range(1, nums[-1] + 1))
            missing = sorted(set(expected) - set(nums))
            if missing:
                pf.ref_number_gaps = [str(n) for n in missing[:10]]

    # ── build suspicious summary ──
    if pf.frontmatter_unknown > 0:
        pf.suspicious_patterns.append(f"frontmatter_unknown={pf.frontmatter_unknown}")
    if pf.body_unknown > 0:
        pf.suspicious_patterns.append(f"body_unknown={pf.body_unknown}")
    if pf.backmatter_unknown > 0:
        pf.suspicious_patterns.append(f"backmatter_unknown={pf.backmatter_unknown}")
    if pf.ref_unknown > 0:
        pf.suspicious_patterns.append(f"ref_unknown={pf.ref_unknown}")
    if pf.body_para_in_backmatter_zone > 3:
        pf.suspicious_patterns.append(f"body_in_backmatter={pf.body_para_in_backmatter_zone}")
    if pf.backmatter_body_in_ref_zone > 0:
        pf.suspicious_patterns.append(f"backmatter_leak_to_ref={pf.backmatter_body_in_ref_zone}")
    if pf.bio_blocks:
        pf.suspicious_patterns.append(f"bio_blocks={len(pf.bio_blocks)}")
    if pf.contribution_blocks:
        pf.suspicious_patterns.append(f"contrib={len(pf.contribution_blocks)}")
    if pf.conflict_blocks:
        pf.suspicious_patterns.append(f"conflict={len(pf.conflict_blocks)}")
    if pf.data_avail_blocks:
        pf.suspicious_patterns.append(f"data_avail={len(pf.data_avail_blocks)}")
    if pf.ethics_blocks:
        pf.suspicious_patterns.append(f"ethics={len(pf.ethics_blocks)}")
    if pf.disclaimer_blocks:
        pf.suspicious_patterns.append(f"disclaimer={len(pf.disclaimer_blocks)}")
    if pf.ref_number_gaps:
        pf.suspicious_patterns.append(f"ref_gaps={','.join(pf.ref_number_gaps[:5])}")
    if pf.degraded_mode:
        pf.suspicious_patterns.append("degraded")
    if pf.render_default_false > 10:
        pf.suspicious_patterns.append(f"render_blocked={pf.render_default_false}")

    return pf


# ── reporting ──────────────────────────────────────────────────────────

def _report_zone_role_anomalies(papers: list[PaperFindings], min_papers: int = 2) -> str:
    """Find roles that commonly appear in unexpected zones across papers."""
    zone_role_papers: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for pf in papers:
        for zone, roles in pf.zone_role_matrix.items():
            for role, count in roles.items():
                if count > 0:
                    zone_role_papers[zone][role] += 1

    lines = ["## Zone-Role Anomalies\n"]
    for zone, roles in sorted(zone_role_papers.items()):
        expected = _EXPECTED_ROLES_BY_ZONE.get(zone, set())
        unexpected = {
            r: c for r, c in sorted(roles.items(), key=lambda x: -x[1])
            if c >= min_papers and r not in expected
        }
        if unexpected:
            lines.append(f"### {zone}")
            lines.append(f"Unexpected roles (appearing in ≥{min_papers} papers):")
            for role, count in unexpected.items():
                lines.append(f"- **{role}**: {count} papers")
            lines.append("")

    return "\n".join(lines)


def _summarize_unknowns(papers: list[PaperFindings]) -> str:
    lines = ["## Unknown Structural Blocks\n"]
    total_unknown = sum(pf.total_unknown for pf in papers)
    papers_with_unknown = [pf for pf in papers if pf.total_unknown > 0]
    lines.append(f"Total papers with unknown_structural: {len(papers_with_unknown)}/{len(papers)}")
    lines.append(f"Total unknown blocks: {total_unknown}")
    lines.append("")
    if papers_with_unknown:
        by_zone: Counter = Counter()
        for pf in papers_with_unknown:
            by_zone["frontmatter"] += pf.frontmatter_unknown
            by_zone["body"] += pf.body_unknown
            by_zone["backmatter"] += pf.backmatter_unknown
            by_zone["reference"] += pf.ref_unknown
        lines.append("By zone:")
        for zone, count in by_zone.most_common():
            lines.append(f"- {zone}: {count}")
        lines.append("")
        lines.append("Worst papers:")
        for pf in sorted(papers_with_unknown, key=lambda x: -x.total_unknown)[:15]:
            lines.append(
                f"- **{pf.key}**: total={pf.total_unknown} "
                f"(fm={pf.frontmatter_unknown} body={pf.body_unknown} "
                f"bm={pf.backmatter_unknown} ref={pf.ref_unknown}) "
                f"{pf.title[:80]}"
            )
    return "\n".join(lines)


def _summarize_backmatter_patterns(papers: list[PaperFindings]) -> str:
    lines = ["## Backmatter Patterns\n"]

    bp_in_bm = [(pf, pf.body_para_in_backmatter_zone) for pf in papers if pf.body_para_in_backmatter_zone > 0]
    lines.append(f"### body_paragraph in backmatter zone: {len(bp_in_bm)} papers")
    for pf, cnt in sorted(bp_in_bm, key=lambda x: -x[1])[:15]:
        lines.append(f"- **{pf.key}**: {cnt} blocks — {pf.title[:80]}")
    lines.append("")

    pattern_sections = [
        ("Author Contributions", "contribution_blocks"),
        ("Conflict of Interest", "conflict_blocks"),
        ("Data Availability", "data_avail_blocks"),
        ("Ethics Statements", "ethics_blocks"),
        ("Author Bios", "bio_blocks"),
        ("Supplementary Material", "supplementary_blocks"),
        ("Disclaimer (Open Access misclassified)", "disclaimer_blocks"),
    ]
    for title, attr in pattern_sections:
        flagged = [pf for pf in papers if getattr(pf, attr)]
        lines.append(f"### {title}: {len(flagged)} papers")
        for pf in sorted(flagged, key=lambda x: -len(getattr(x, attr)))[:10]:
            blks = getattr(pf, attr)
            roles = Counter(b["role"] for b in blks)
            zones = Counter(b["zone"] for b in blks)
            lines.append(
                f"- **{pf.key}**: {len(blks)} blocks, "
                f"roles={dict(roles.most_common(3))}, zones={dict(zones.most_common(3))}"
            )
        lines.append("")

    return "\n".join(lines)


def _summarize_reference_patterns(papers: list[PaperFindings]) -> str:
    lines = ["## Reference Zone Patterns\n"]

    bm_in_ref = [(pf, pf.backmatter_body_in_ref_zone) for pf in papers if pf.backmatter_body_in_ref_zone > 0]
    lines.append(f"### Backmatter/body leaking into reference zone: {len(bm_in_ref)} papers")
    for pf, cnt in sorted(bm_in_ref, key=lambda x: -x[1])[:10]:
        lines.append(f"- **{pf.key}**: {cnt} blocks — {pf.title[:80]}")
    lines.append("")

    gap_papers = [pf for pf in papers if pf.ref_number_gaps]
    lines.append(f"### Reference number gaps: {len(gap_papers)} papers")
    for pf in sorted(gap_papers, key=lambda x: -len(x.ref_number_gaps))[:10]:
        lines.append(
            f"- **{pf.key}**: gaps at ref# {', '.join(pf.ref_number_gaps[:8])} — {pf.title[:80]}"
        )
    lines.append("")

    return "\n".join(lines)


def _summarize_degraded(papers: list[PaperFindings]) -> str:
    degraded = [pf for pf in papers if pf.degraded_mode]
    lines = ["## Degraded Mode Papers\n"]
    lines.append(f"{len(degraded)} papers in degraded mode (layout fallback):")
    for pf in sorted(degraded, key=lambda x: -x.suspicious_score())[:10]:
        lines.append(f"- **{pf.key}**: score={pf.suspicious_score()} — {pf.title[:80]}")
    lines.append("")
    return "\n".join(lines)


def _full_report(papers: list[PaperFindings]) -> str:
    suspicious = sum(1 for pf in papers if pf.suspicious_score() > 0)
    lines = [
        "# OCR Zone/Role Batch Audit Report\n",
        f"Scanned {len(papers)} papers\n",
        f"Total suspicious papers (score >= 1): {suspicious}\n",
    ]
    lines.append(_summarize_unknowns(papers))
    lines.append(_summarize_backmatter_patterns(papers))
    lines.append(_summarize_reference_patterns(papers))
    lines.append(_summarize_degraded(papers))
    lines.append(_report_zone_role_anomalies(papers))

    lines.append("## Top 30 Most Suspicious Papers\n")
    sorted_papers = sorted(papers, key=lambda x: -x.suspicious_score())
    for pf in sorted_papers[:30]:
        lines.append(
            f"- **{pf.key}** score={pf.suspicious_score()} "
            f"unknown={pf.total_unknown} "
            f"patterns={'|'.join(pf.suspicious_patterns[:4])} | {pf.title[:80]}"
        )
    lines.append("")
    lines.append("\n*Report generated by scripts/dev/ocr_zone_role_audit.py*\n")
    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Batch zone/role audit of OCR papers")
    parser.add_argument("--limit", type=int, default=0, help="Max papers to scan (0 = all)")
    parser.add_argument("--output", type=str, default="", help="Output report path")
    parser.add_argument("--source-root", type=str, default="",
                        help="OCR root (default: PAPERFORGE_OCR_ROOT env)")
    parser.add_argument("--paper-keys", type=str, nargs="*", default=[],
                        help="Specific paper keys to audit (overrides limit)")
    args = parser.parse_args(argv)

    ocr_root = Path(args.source_root) if args.source_root else Path(
        os.environ.get("PAPERFORGE_OCR_ROOT") or os.environ.get("PAPERFORGE_REAL_OCR_ROOT") or ""
    )
    if not ocr_root.exists():
        print(f"OCR root not found: {ocr_root}")
        return 1

    keys = args.paper_keys
    if not keys:
        all_dirs = sorted([d for d in ocr_root.iterdir() if d.is_dir() and not d.name.startswith(".")])
        # prefer recently modified papers (likely rebuilt)
        all_dirs.sort(key=lambda d: -d.stat().st_mtime)
        keys = [d.name for d in all_dirs if (d / "structure" / "blocks.structured.jsonl").exists()]
        if args.limit > 0:
            keys = keys[:args.limit]
    else:
        keys = [k for k in keys if (ocr_root / k).is_dir()]

    if not keys:
        print(f"No papers found at {ocr_root}")
        return 1

    print(f"Scanning {len(keys)} papers from {ocr_root}...")

    papers: list[PaperFindings] = []
    for i, key in enumerate(keys):
        if (i + 1) % 50 == 0:
            print(f"  ... {i + 1}/{len(keys)}")
        pf = _analyze_one_paper(ocr_root, key)
        papers.append(pf)

    report = _full_report(papers)

    output_path = args.output or str(Path.cwd() / "audit" / "zone-role-batch-audit-report.md")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(report, encoding="utf-8")
    print(f"\nReport written to {output_path}")

    # Print top suspicious to stdout
    sorted_papers = sorted(papers, key=lambda x: -x.suspicious_score())
    print(f"\nTop 10 most suspicious papers:")
    for pf in sorted_papers[:10]:
        print(f"  {pf.key:12s} score={pf.suspicious_score():3d}  {pf.title[:80]}")

    # Print pattern summary
    print(f"\nPattern summary:")
    for attr, label in [
        ("bio_blocks", "Author Bios"),
        ("contribution_blocks", "Author Contributions"),
        ("conflict_blocks", "Conflict of Interest"),
        ("data_avail_blocks", "Data Availability"),
        ("ethics_blocks", "Ethics Statements"),
        ("disclaimer_blocks", "Disclaimers (misclassified)"),
        ("supplementary_blocks", "Supplementary Material"),
    ]:
        count = sum(1 for pf in papers if getattr(pf, attr))
        print(f"  {label}: {count}/{len(papers)} papers flagged")

    unknown_count = sum(1 for pf in papers if pf.total_unknown > 0)
    print(f"  unknown_structural: {unknown_count}/{len(papers)} papers")
    print(f"  Body para in backmatter zone: {sum(1 for pf in papers if pf.body_para_in_backmatter_zone > 0)} papers")
    print(f"  Backmatter/body leak to ref zone: {sum(1 for pf in papers if pf.backmatter_body_in_ref_zone > 0)} papers")
    print(f"  Ref number gaps: {sum(1 for pf in papers if pf.ref_number_gaps)} papers")
    print(f"  Degraded mode: {sum(1 for pf in papers if pf.degraded_mode)} papers")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
