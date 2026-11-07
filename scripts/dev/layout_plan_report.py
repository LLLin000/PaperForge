"""Read-only layout-plan evaluation over an OCR vault.

Usage: python scripts/dev/layout_plan_report.py --vault PATH [--keys KEY ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _paper_report(paper_dir: Path) -> dict[str, Any] | None:
    from paperforge.worker.layout.evaluate import evaluate_plan
    from paperforge.worker.layout.plan import build_layout_plan
    from paperforge.worker.ocr_blocks import build_structured_blocks
    from paperforge.worker.ocr_figures import build_figure_inventory
    from paperforge.worker.ocr_pre_match_normalize import pre_match_normalize
    from paperforge.worker.ocr_tables import build_table_inventory

    raw_path = paper_dir / "canonical" / "blocks.raw.jsonl"
    if not raw_path.is_file():
        return None
    raw_blocks = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    metadata_path = paper_dir / "raw" / "source_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    seeded, document = build_structured_blocks(raw_blocks, source_metadata=metadata, normalize_mode="seed_only")
    blocks, document = pre_match_normalize(
        seeded,
        source_frontmatter_anchors=getattr(document, "source_frontmatter_anchors", None),
        document_structure=document,
    )
    figures = build_figure_inventory(blocks)
    tables = build_table_inventory(blocks)
    plan = build_layout_plan(blocks)
    metrics = evaluate_plan(plan, blocks, figures, tables)
    return {
        "key": paper_dir.name,
        "plan": plan.to_dict(),
        "metrics": metrics,
    }


def _markdown(reports: list[dict[str, Any]]) -> str:
    headers = "| Key | Pages | Blocks | Regions | Containers | Holds | Conflicts by kind | Pair inversions |"
    separator = "|---|---:|---:|---:|---:|---:|---|---:|"
    rows = []
    for report in reports:
        plan, metrics = report["plan"], report["metrics"]
        rows.append(
            f"| {report['key']} | {metrics['pages']} | {metrics['blocks']} | "
            f"{plan['stats'].get('regions', 0)} | {plan['stats'].get('containers', 0)} | "
            f"{metrics['holds']['count']} | {json.dumps(metrics['conflicts']['by_kind'], sort_keys=True)} | "
            f"{len(metrics['pair_inversions'])} |"
        )
    return "\n".join([headers, separator, *rows])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path, help="OCR vault root")
    parser.add_argument("--keys", nargs="*", help="paper keys; defaults to vault subdirectories")
    parser.add_argument("--limit", type=int, help="maximum papers to process")
    parser.add_argument("--out", type=Path, help="write JSON report here")
    args = parser.parse_args(argv)
    keys = args.keys if args.keys else sorted(path.name for path in args.vault.iterdir() if path.is_dir())
    if args.limit is not None:
        keys = keys[:max(0, args.limit)]
    reports = []
    for key in keys:
        report = _paper_report(args.vault / key)
        if report is not None:
            reports.append(report)
    payload = {"papers": reports}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(_markdown(reports))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
