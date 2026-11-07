"""Shadow render: baseline vs layout-plan reading order, without publishing.

Read-only. It builds the *final* structured blocks (post-match + object
writebacks), asks the production acceptance gate whether a page may be
reordered, and renders the same document twice with the existing renderer:

- baseline: the renderer's own order (`layout_order=None`);
- shadow: accepted pages follow the plan's order, everything else unchanged.

Nothing is written to the OCR vault. The report is the only output.

Usage:
    python scripts/dev/layout_shadow_render.py \
        --vault D:/L/OB/Literature-hub/System/PaperForge/ocr \
        --keys 2HEUD5P9 2332GHPT --out shadow.json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Pages whose layout this shadow run must not touch yet.
_SCOPE_BLOCKED_ROLES = frozenset(
    {
        "reference_heading",
        "reference_item",
        "backmatter_heading",
        "backmatter_body",
        "backmatter_heading_candidate",
        "table_html",
        "structured_insert",
        "non_body_insert",
    }
)


def load_final_blocks(paper_dir: Path) -> tuple[list[dict], dict, dict, dict, dict]:
    """Rebuild the blocks the production renderer actually consumes."""
    from paperforge.worker.ocr_blocks import build_structured_blocks
    from paperforge.worker.ocr_figure_reader import synthesize_reader_figures
    from paperforge.worker.ocr_figures import build_figure_inventory
    from paperforge.worker.ocr_object_writeback import apply_object_writebacks
    from paperforge.worker.ocr_post_match_normalize import post_match_normalize
    from paperforge.worker.ocr_pre_match_normalize import pre_match_normalize
    from paperforge.worker.ocr_tables import build_table_inventory

    raw_path = paper_dir / "canonical" / "blocks.raw.jsonl"
    raw_blocks = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    metadata_path = paper_dir / "raw" / "source_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}

    blocks, document = build_structured_blocks(raw_blocks, source_metadata=metadata, normalize_mode="seed_only")
    anchors = getattr(document, "source_frontmatter_anchors", None)
    blocks, document = pre_match_normalize(
        blocks, source_frontmatter_anchors=anchors, document_structure=document
    )
    figures = build_figure_inventory(blocks)
    tables = build_table_inventory(blocks)
    blocks, document = post_match_normalize(
        blocks, figures, tables, document_structure=document, source_frontmatter_anchors=anchors
    )
    apply_object_writebacks(structured_blocks=blocks, figure_inventory=figures, table_inventory=tables)
    reader_payload = synthesize_reader_figures(figures, structured_blocks=blocks)
    return blocks, metadata, document, figures, tables, reader_payload


def page_in_scope(page, blocks_by_page: dict[int, list[dict]]) -> tuple[bool, str]:
    """Tail / references / backmatter and object-complex pages stay baseline."""
    if any(region.kind == "container" for region in page.regions):
        return False, "container_region"
    for block in blocks_by_page.get(page.page, []):
        if (block.get("role") or "") in _SCOPE_BLOCKED_ROLES:
            return False, f"role:{block.get('role')}"
        if block.get("_object_owner_id"):
            return False, "object_owner"
        if block.get("_container_text"):
            return False, "box_container"
    return True, ""


def layout_order_for(
    acceptance: list, plan, blocks_by_page: dict[int, list[dict]], min_confidence: float
) -> dict[int, list[int]]:
    """page → source indices, only for accepted and in-scope pages."""
    order: dict[int, list[int]] = {}
    for result in acceptance:
        if not result.accepted:
            continue
        page = next(item for item in plan.pages if item.page == result.page)
        in_scope, _ = page_in_scope(page, blocks_by_page)
        if not in_scope:
            continue
        indices = [result.source_mapping[uid] for uid in result.accepted_order or [] if uid in result.source_mapping]
        if len(indices) == len(result.source_mapping):
            order[result.page] = indices
    return order


def _render(
    blocks: list[dict],
    metadata: dict,
    document,
    figures: dict,
    tables: dict,
    reader_payload: dict,
    layout_order,
):
    from paperforge.worker.ocr_metadata import resolve_metadata
    from paperforge.worker.ocr_render import render_fulltext_markdown

    resolved = resolve_metadata(source_metadata=metadata, structured_blocks=blocks)
    return render_fulltext_markdown(
        structured_blocks=blocks,
        resolved_metadata=resolved,
        figure_inventory=figures,
        table_inventory=tables,
        page_count=max((int(block.get("page", 0) or 0) for block in blocks), default=0),
        document_structure=document,
        reader_payload=reader_payload,
        return_events=True,
        layout_order=layout_order,
    )


def _order_signature(output) -> list[tuple[int, str]]:
    return [(int(event.get("page", 0) or 0), str(event.get("block_id"))) for event in output.emitted_block_events]


def shadow_report(
    paper_dir: Path,
    *,
    min_confidence: float = 0.80,
    diagnostics: tuple[float, ...] = (),
) -> dict[str, Any] | None:
    from paperforge.worker.layout.acceptance import assess_plan
    from paperforge.worker.layout.plan import build_layout_plan

    raw_path = paper_dir / "canonical" / "blocks.raw.jsonl"
    if not raw_path.is_file():
        return None

    blocks, metadata, document, figures, tables, reader_payload = load_final_blocks(paper_dir)
    plan = build_layout_plan(blocks)
    acceptance = assess_plan(plan, blocks, min_confidence=min_confidence)

    blocks_by_page: dict[int, list[dict]] = {}
    for block in blocks:
        blocks_by_page.setdefault(int(block.get("page", 0) or 0), []).append(block)

    order = layout_order_for(acceptance, plan, blocks_by_page, min_confidence)

    baseline = _render(copy.deepcopy(blocks), metadata, document, figures, tables, reader_payload, None)
    shadow = _render(copy.deepcopy(blocks), metadata, document, figures, tables, reader_payload, order)
    # Empty override must be a no-op on the renderer.
    empty_override = _render(copy.deepcopy(blocks), metadata, document, figures, tables, reader_payload, {})

    baseline_order = _order_signature(baseline)
    shadow_order = _order_signature(shadow)

    changed_pages = sorted(
        {
            page
            for page in order
            if [item for item in baseline_order if item[0] == page]
            != [item for item in shadow_order if item[0] == page]
        }
    )
    body_counts_baseline = Counter(block_id for _, block_id in baseline_order)
    body_counts_shadow = Counter(block_id for _, block_id in shadow_order)

    diagnostic_results: dict[str, Any] = {}
    for threshold in diagnostics:
        diag_acceptance = assess_plan(plan, blocks, min_confidence=threshold)
        diag_order = layout_order_for(diag_acceptance, plan, blocks_by_page, threshold)
        diag_shadow = _render(copy.deepcopy(blocks), metadata, document, figures, tables, reader_payload, diag_order)
        diag_signature = _order_signature(diag_shadow)
        diagnostic_results[f"{threshold:.2f}"] = {
            "accepted_pages": sum(1 for result in diag_acceptance if result.accepted),
            "in_scope_pages": len(diag_order),
            "changed_pages": sorted(
                {
                    page
                    for page in diag_order
                    if [item for item in baseline_order if item[0] == page]
                    != [item for item in diag_signature if item[0] == page]
                }
            ),
            "markdown_equal": baseline.markdown == diag_shadow.markdown,
            "block_multiset_equal": body_counts_baseline == Counter(block_id for _, block_id in diag_signature),
            "heading_events_equal": [
                (event.get("title"), event.get("markdown_level")) for event in baseline.heading_events
            ]
            == [(event.get("title"), event.get("markdown_level")) for event in diag_shadow.heading_events],
            "text_length": {"baseline": len(baseline.markdown), "shadow": len(diag_shadow.markdown)},
        }

    return {
        "key": paper_dir.name,
        "min_confidence": min_confidence,
        "diagnostics": diagnostic_results,
        "pages": len(plan.pages),
        "accepted_pages": sum(1 for result in acceptance if result.accepted),
        "in_scope_pages": len(order),
        "changed_pages": changed_pages,
        "markdown_equal": baseline.markdown == shadow.markdown,
        "empty_override_is_noop": baseline.markdown == empty_override.markdown
        and baseline_order == _order_signature(empty_override),
        "block_multiset_equal": body_counts_baseline == body_counts_shadow,
        "heading_events_equal": [
            (event.get("title"), event.get("markdown_level")) for event in baseline.heading_events
        ]
        == [(event.get("title"), event.get("markdown_level")) for event in shadow.heading_events],
        "text_length": {"baseline": len(baseline.markdown), "shadow": len(shadow.markdown)},
        "accepted": [
            {
                "page": result.page,
                "reason": result.fallback_reason,
                "held": len(result.held_blocks),
                "evidence": result.evidence,
            }
            for result in acceptance
        ],
    }


def _markdown(reports: list[dict[str, Any]]) -> str:
    lines = [
        "| key | pages | accepted | in scope | changed | markdown equal | block multiset | headings |",
        "|---|---:|---:|---:|---:|---|---|---|",
    ]
    for report in reports:
        lines.append(
            f"| {report['key']} | {report['pages']} | {report['accepted_pages']} | {report['in_scope_pages']} | "
            f"{len(report['changed_pages'])} | {report['markdown_equal']} | {report['block_multiset_equal']} | "
            f"{report['heading_events_equal']} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--keys", nargs="*")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--diagnostic-thresholds", nargs="*", type=float, default=())
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    keys = args.keys or sorted(path.name for path in args.vault.iterdir() if path.is_dir())
    if args.limit is not None:
        keys = keys[: max(0, args.limit)]
    diagnostics = tuple(args.diagnostic_thresholds or ())
    reports = [
        report
        for key in keys
        if (report := shadow_report(args.vault / key, diagnostics=diagnostics)) is not None
    ]
    payload = {
        "papers": reports,
        "diagnostics_requested": list(diagnostics),
        "totals": {
            "pages": sum(report["pages"] for report in reports),
            "accepted_pages": sum(report["accepted_pages"] for report in reports),
            "in_scope_pages": sum(report["in_scope_pages"] for report in reports),
            "changed_pages": sum(len(report["changed_pages"]) for report in reports),
            "papers_with_markdown_change": sum(1 for report in reports if not report["markdown_equal"]),
            "block_multiset_regressions": sum(1 for report in reports if not report["block_multiset_equal"]),
            "heading_regressions": sum(1 for report in reports if not report["heading_events_equal"]),
            "empty_override_failures": sum(1 for report in reports if not report["empty_override_is_noop"]),
        },
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(_markdown(reports))
    print(f"\n{payload['totals']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
