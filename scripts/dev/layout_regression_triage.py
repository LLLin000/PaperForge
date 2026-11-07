"""List every place the layout plan disagrees with the OCR order, with context.

Read-only. The output is meant for a human verdict — the script never decides
who is right, it only makes each disagreement reviewable: texts, roles, the
regions and their confidences, the plan decision, and a few structural tags.

Usage:
    python scripts/dev/layout_regression_triage.py \
        --vault D:/L/OB/Literature-hub/System/PaperForge/ocr \
        --keys 27MFWJWJ 25K5KZAQ --out triage.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_PANEL_LABEL = re.compile(r"^\(?[A-Za-z]\)?$")


def _load_blocks(paper_dir: Path) -> tuple[list[dict], dict]:
    from paperforge.worker.ocr_blocks import build_structured_blocks
    from paperforge.worker.ocr_pre_match_normalize import pre_match_normalize

    raw_path = paper_dir / "canonical" / "blocks.raw.jsonl"
    raw_blocks = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    metadata_path = paper_dir / "raw" / "source_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    seeded, document = build_structured_blocks(raw_blocks, source_metadata=metadata, normalize_mode="seed_only")
    blocks, document = pre_match_normalize(
        seeded,
        source_frontmatter_anchors=getattr(document, "source_frontmatter_anchors", None),
        document_structure=document,
    )
    return blocks, metadata


def _tags(
    first_uid: str,
    second_uid: str,
    first_bbox: tuple[float, ...],
    second_bbox: tuple[float, ...],
    first_text: str,
    second_text: str,
    regions: list[dict],
    kind_by_uid: dict[str, str],
) -> list[str]:
    tags: list[str] = []
    if _PANEL_LABEL.match(first_text.strip()) or _PANEL_LABEL.match(second_text.strip()):
        tags.append("panel_label")
    if {kind_by_uid.get(first_uid), kind_by_uid.get(second_uid)} & {"margin"}:
        tags.append("margin_block")
    if {kind_by_uid.get(first_uid), kind_by_uid.get(second_uid)} & {"container"}:
        tags.append("container_member")
    if kind_by_uid.get(first_uid) != kind_by_uid.get(second_uid):
        tags.append("column_switch")
    top = min(first_bbox[1], second_bbox[1])
    bottom = max(first_bbox[3], second_bbox[3])
    if any(region["kind"] == "container" and top <= region["y_top"] <= bottom for region in regions):
        tags.append("container_between")
    return tags


def triage_paper(paper_dir: Path) -> dict[str, Any] | None:
    from paperforge.worker.layout.plan import build_layout_plan, collect_block_refs

    raw_path = paper_dir / "canonical" / "blocks.raw.jsonl"
    if not raw_path.is_file():
        return None
    blocks, _ = _load_blocks(paper_dir)
    plan = build_layout_plan(blocks)
    refs = collect_block_refs(blocks)
    by_uid = {ref.uid: ref for ref in refs}
    text_by_uid: dict[str, str] = {}
    by_key = {
        (int(block.get("page", 0) or 0), str(block.get("block_id") or "")): block
        for block in blocks
    }
    for ref in refs:
        block = by_key.get((ref.page, ref.block_id), {})
        text_by_uid[ref.uid] = (block.get("text") or "").strip()

    pairs: list[dict[str, Any]] = []
    for page in plan.pages:
        regions = [
            {
                "region_id": region.region_id,
                "kind": region.kind,
                "confidence": region.confidence,
                "x_left": region.x_left,
                "x_right": region.x_right,
                "y_top": region.y_top,
                "y_bottom": region.y_bottom,
            }
            for region in page.regions
        ]
        kind_by_uid = {uid: region.kind for region in page.regions for uid in region.members}
        for before_uid, after_uid in zip(page.order, page.order[1:], strict=False):
            first, second = by_uid.get(before_uid), by_uid.get(after_uid)
            if first is None or second is None or first.bbox is None or second.bbox is None:
                continue
            if first.raw_index < second.raw_index:
                continue
            decision = next(
                (d for d in page.decisions if d.before == before_uid and d.after == after_uid), None
            )
            pairs.append(
                {
                    "page": page.page,
                    "first": {
                        "uid": before_uid,
                        "text": text_by_uid[before_uid][:80],
                        "bbox": list(first.bbox),
                        "ocr_rank": first.raw_index,
                    },
                    "second": {
                        "uid": after_uid,
                        "text": text_by_uid[after_uid][:80],
                        "bbox": list(second.bbox),
                        "ocr_rank": second.raw_index,
                    },
                    "decision": None
                    if decision is None
                    else {"confidence": decision.confidence, "reason": decision.reason},
                    "tags": _tags(
                        before_uid,
                        after_uid,
                        first.bbox,
                        second.bbox,
                        text_by_uid[before_uid],
                        text_by_uid[after_uid],
                        regions,
                        kind_by_uid,
                    ),
                }
            )
    return {"key": paper_dir.name, "pairs": pairs}


_MEMBER_CACHE: dict[tuple[int, str], tuple[str, ...]] = {}


def _markdown(reports: list[dict[str, Any]]) -> str:
    lines = ["| key | page | first | second | tags | decision |", "|---|---:|---|---|---|---|"]
    for report in reports:
        for pair in report["pairs"]:
            decision = pair["decision"]
            conf = f"{decision['confidence']:.2f}" if decision else "-"
            lines.append(
                f"| {report['key']} | {pair['page']} | {pair['first']['text'][:38]} | "
                f"{pair['second']['text'][:38]} | {','.join(pair['tags'])} | {conf} |"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--keys", nargs="*")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    keys = args.keys or sorted(path.name for path in args.vault.iterdir() if path.is_dir())
    reports = [report for key in keys if (report := triage_paper(args.vault / key)) is not None]
    payload = {"papers": reports, "disagreements": sum(len(report["pairs"]) for report in reports)}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(_markdown(reports))
    print(f"\n{payload['disagreements']} disagreements over {len(reports)} papers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
