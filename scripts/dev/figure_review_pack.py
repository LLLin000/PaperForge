"""Build a human visual-review pack from the reattribution Census.

The pack points at actual rebuilt evidence. It refreshes blank unmatched-legend labels only
when their source PDF and page/block still match the snapshot; human verdicts stay untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_CENSUS = ROOT / "docs" / "evidence" / "r3-reattribution" / "reattribution-census.json"
DEFAULT_SAMPLE = ROOT / "docs" / "evidence" / "r3" / "sample-manifest.json"
DEFAULT_PACK = ROOT / "docs" / "evidence" / "r3-review-pack"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _labels(evidence_dir: Path) -> list[dict[str, Any]]:
    path = evidence_dir / "labels.jsonl"
    if not path.is_file():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]

REVIEW_FIELDS = ("caption_ok", "panels_ok", "crop_ok", "delivery_ok")
BINDING_FIELDS = ("asset_sha256", "render_sha256", "fulltext_sha256")


def _has_human_review_data(label: dict[str, Any]) -> bool:
    reviewer = str(label.get("reviewer") or "").strip().lower()
    return (
        reviewer not in {"", "unreviewed"}
        or bool(str(label.get("reviewed_at") or "").strip())
        or bool(str(label.get("notes") or "").strip())
        or bool(str(label.get("expected_owner") or "").strip())
        or any(label.get(field) is not None for field in REVIEW_FIELDS)
    )


def _refresh_unreviewed_legends(
    labels: list[dict[str, Any]], rebuilt: dict[str, Any], snapshot_dir: Path | None,
    evidence_dir: Path,
) -> tuple[list[dict[str, Any]], int, set[tuple[int, str]]]:
    if not snapshot_dir or not labels or not any(
        row.get("kind") == "unmatched_legend" for row in labels
    ):
        return labels, 0, set()
    snapshot = rebuilt.get("snapshot_fingerprint")
    source = rebuilt.get("source_pdf_sha256")
    fulltext = rebuilt.get("snapshot_fulltext_sha256")
    blocks_path = snapshot_dir / "structure" / "blocks.structured.jsonl"
    if not snapshot or not source or not fulltext or not blocks_path.is_file():
        return labels, 0, set()

    current_blocks = set()
    for line in blocks_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        try:
            page = int(row.get("page", 0) or 0)
        except (TypeError, ValueError):
            continue
        raw_block_id = row.get("block_id")
        block_id = "" if raw_block_id is None else str(raw_block_id)
        if page > 0 and block_id:
            current_blocks.add((page, block_id))

    refreshed = 0
    current_labels = []
    for label in labels:
        if (
            label.get("kind") != "unmatched_legend"
            or _has_human_review_data(label)
            or label.get("source_pdf_sha256") != source
        ):
            current_labels.append(label)
            continue
        try:
            page = int(label.get("page", 0) or 0)
        except (TypeError, ValueError):
            current_labels.append(label)
            continue
        raw_block_id = label.get("block_id")
        block_id = "" if raw_block_id is None else str(raw_block_id)
        if (page, block_id) not in current_blocks:
            current_labels.append(label)
            continue
        if (
            label.get("snapshot_fingerprint") == snapshot
            and label.get("fulltext_sha256") == fulltext
        ):
            current_labels.append(label)
            continue
        current_labels.append({
            **label,
            "snapshot_fingerprint": snapshot,
            "source_pdf_sha256": source,
            "fulltext_sha256": fulltext,
        })
        refreshed += 1

    if refreshed:
        payload = "\n".join(json.dumps(row, ensure_ascii=False) for row in current_labels) + "\n"
        _write_text(evidence_dir / "labels.jsonl", payload)
    return current_labels, refreshed, current_blocks




def _label_is_bound(
    label: dict[str, Any], rebuilt: dict[str, Any], delivery: dict[str, Any],
    snapshot_blocks: set[tuple[int, str]],
) -> bool:
    snapshot = rebuilt.get("snapshot_fingerprint")
    source = rebuilt.get("source_pdf_sha256")
    if (
        not snapshot or label.get("snapshot_fingerprint") != snapshot
        or not source or label.get("source_pdf_sha256") != source
    ):
        return False
    if label.get("kind") == "matched_figure":
        figure_id = str(label.get("figure_id") or "")
        evidence = delivery.get(figure_id)
        return bool(figure_id and evidence) and all(
            isinstance(label.get(field), str)
            and label[field]
            and label[field] == evidence.get(field)
            for field in BINDING_FIELDS
        )
    if label.get("kind") == "unmatched_legend":
        try:
            page = int(label.get("page", 0) or 0)
        except (TypeError, ValueError):
            return False
        fulltext = label.get("fulltext_sha256")
        raw_block_id = label.get("block_id")
        block_id = "" if raw_block_id is None else str(raw_block_id)
        return bool(
            block_id
            and page > 0
            and (page, block_id) in snapshot_blocks
            and isinstance(fulltext, str)
            and fulltext
            and fulltext == rebuilt.get("snapshot_fulltext_sha256")
        )
    return False


def _authority(rows: list[dict[str, Any]]) -> str:
    sources = {
        str(row.get("review_source") or "human")
        for row in rows if _label_is_reviewed(row)
    }
    if not sources:
        return "none"
    if sources == {"human"}:
        return "human"
    return "agent_visual" if sources == {"agent_visual"} else "mixed"


def _rollup_authority(rows: list[dict[str, Any]]) -> str:
    authorities = {row["review_authority"] for row in rows if row.get("labels_reviewed")}
    if not authorities:
        return "none"
    if authorities == {"human"}:
        return "human"
    return "agent_visual" if authorities == {"agent_visual"} else "mixed"


def _label_is_reviewed(label: dict[str, Any]) -> bool:
    reviewer = str(label.get("reviewer") or "").strip().lower()
    return (
        reviewer not in {"", "unreviewed"}
        and all(type(label.get(field)) is bool for field in REVIEW_FIELDS)
    )


def _review_status(labels: list[dict[str, Any]], bound: list[dict[str, Any]],
                   reviewed: list[dict[str, Any]]) -> str:
    if not labels:
        return "UNKNOWN_NO_LABELS"
    if len(bound) != len(labels):
        return "UNKNOWN_STALE_LABELS"
    return "REVIEWED" if len(reviewed) == len(labels) else "UNKNOWN"



def _row_fails_delivery(label: dict[str, Any]) -> bool:
    """A reviewed row that proves delivery is wrong.

    ``matched_figure`` rows deliver an object, so any false verdict is a delivery failure.
    ``unmatched_legend`` rows deliver nothing: only a genuine figure left undelivered counts,
    which shows up as ``crop_ok`` or ``delivery_ok`` false. ``caption_ok`` false there means the
    candidate finder surfaced a non-caption block - recorded, but not a delivery failure.
    """
    if label.get("kind") == "matched_figure":
        return any(label.get(field) is False for field in REVIEW_FIELDS)
    return label.get("crop_ok") is False or label.get("delivery_ok") is False


def _review_outcome(
    labels: list[dict[str, Any]], bound: list[dict[str, Any]], reviewed: list[dict[str, Any]],
) -> str:
    if not labels or len(bound) != len(labels) or len(reviewed) != len(labels):
        return "UNKNOWN"
    return "FAIL" if any(_row_fails_delivery(row) for row in reviewed) else "PASS"


def _row_markdown(
    label: dict[str, Any], snapshot_dir: Path | None, review_dir: Path,
    delivery: dict[str, Any],
) -> str:
    fid = str(label.get("figure_id") or "")
    kind = label.get("kind")
    page = label.get("page")
    lines = [f"### {fid or '(unmatched legend)'} — page {page}", ""]
    if kind == "matched_figure":
        state = (delivery.get(fid) or {}).get("state", "UNKNOWN")
        lines.append(f"- delivery state: `{state}`")
        asset = (delivery.get(fid) or {}).get("asset_path")
        render = (delivery.get(fid) or {}).get("render_path")
        snapshot_base = str(snapshot_dir) if snapshot_dir else "(unrecorded)"
        if asset:
            lines.append(f"- crop: `{snapshot_base}/{asset}`")
            lines.append(f"  - asset_sha256 `{label.get('asset_sha256')}`")
        if render:
            lines.append(f"- render: `{snapshot_base}/{render}`")
            lines.append(f"  - render_sha256 `{label.get('render_sha256')}`")
        lines.append(f"- fulltext_sha256 `{label.get('fulltext_sha256')}`")
        lines.append(f"- claimed asset blocks: `{label.get('current_assets') or '(none)'}`")
    else:
        block_id = label.get("block_id")
        lines.append(f"- unmatched legend block `{block_id}` on page {page}")
        lines.append(f"- fulltext_sha256 `{label.get('fulltext_sha256')}`")
    page_image = review_dir / f"page_{int(page or 0):03d}.jpg"
    lines.append(f"- page preview: `{page_image}`")
    lines.append(f"- snapshot_fingerprint `{label.get('snapshot_fingerprint')}`")
    lines.append(f"- source_pdf_sha256 `{label.get('source_pdf_sha256')}`")
    lines.append("")
    lines.append("Verdict fields (leave blank until a human actually looks):")
    lines.append("")
    lines.append("| crop_ok | panels_ok | caption_ok | delivery_ok | reviewer | notes |")
    lines.append("|---|---|---|---|---|---|")
    lines.append(
        f"| {label.get('crop_ok')} | {label.get('panels_ok')} | {label.get('caption_ok')} "
        f"| {label.get('delivery_ok')} | {label.get('reviewer') or ''} | {label.get('notes') or ''} |"
    )
    return "\n".join(lines)


def build_pack(
    census_path: Path, sample_path: Path, pack_root: Path, work_root: Path | None,
) -> dict[str, Any]:
    census = _read_json(census_path)
    sample = _read_json(sample_path)
    frozen_keys = sorted(set(sample.get("selected_keys", [])))
    papers = {row["key"]: row for row in census["papers"]}
    missing = [key for key in frozen_keys if key not in papers]
    if missing:
        raise ValueError(f"frozen sample keys missing from Census: {missing}")

    pack_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for key in frozen_keys:
        paper = papers[key]
        rebuilt = paper.get("rebuilt_state", {})
        out_dir = Path(paper.get("evidence_dir") or (census_path.parent / key))
        snapshot_path = rebuilt.get("snapshot_path")
        snapshot_dir = Path(snapshot_path) if snapshot_path else None
        labels = _labels(out_dir)
        labels, labels_refreshed, snapshot_blocks = _refresh_unreviewed_legends(
            labels, rebuilt, snapshot_dir, out_dir
        )
        delivery = (rebuilt.get("delivery") or {}).get("figures") or {}
        review_dir = (work_root / key / "review_context") if work_root else out_dir / "review_context"
        bound = [
            row for row in labels if _label_is_bound(row, rebuilt, delivery, snapshot_blocks)
        ]
        reviewed = [row for row in bound if _label_is_reviewed(row)]
        review_status = _review_status(labels, bound, reviewed)
        source_provenance = rebuilt.get("source_provenance") or {}
        observed_source = source_provenance.get("observed") or {}

        page_lines = [
            f"# {key} — human visual review",
            "",
            f"- classification: `{paper.get('classification')}`",
            f"- migration_state: `{paper.get('migration_state')}`",
            f"- source_pdf_sha256 `{rebuilt.get('source_pdf_sha256')}`",
            f"- source_pdf_path `{observed_source.get('path')}`",
            f"- source_pdf_page_count `{observed_source.get('page_count')}`",
            f"- snapshot_fingerprint `{rebuilt.get('snapshot_fingerprint')}`",
            f"- labels total {len(labels)}, fully bound {len(bound)}, reviewed {len(reviewed)}",
            "",
            "Open the crop and page previews below. Do not infer a PASS from delivery state;",
            "a RESOLVED row can still be the wrong figure, wrong crop bounds, or wrong caption.",
            "",
        ]
        for label in labels:
            page_lines.append(_row_markdown(label, snapshot_dir, review_dir, delivery))
            page_lines.append("")
        _write_text(pack_root / f"{key}.md", "\n".join(page_lines))

        rows.append({
            "key": key,
            "classification": paper.get("classification"),
            "migration_state": paper.get("migration_state"),
            "source_pdf_sha256": rebuilt.get("source_pdf_sha256"),
            "source_pdf_path": observed_source.get("path"),
            "source_pdf_page_count": observed_source.get("page_count"),
            "snapshot_fingerprint": rebuilt.get("snapshot_fingerprint"),
            "labels_total": len(labels),
            "labels_snapshot_bound": len(bound),
            "labels_stale": len(labels) - len(bound),
            "labels_refreshed": labels_refreshed,
            "labels_reviewed": len(reviewed),
            "review_status": review_status,
            "review_outcome": _review_outcome(labels, bound, reviewed),
            "review_authority": _authority(reviewed),
            "review_sheet": str(pack_root / f"{key}.md"),
        })

    return {
        "schema": "paperforge.figure_visual_review_pack.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_census": str(census_path),
        "source_census_sha256": "sha256:" + hashlib.sha256(census_path.read_bytes()).hexdigest(),
        "frozen_sample_manifest": str(sample_path),
        "instructions": (
            "A row counts as PASS only when a reviewer fills reviewer plus all four verdict "
            "fields as booleans. UNKNOWN, zero-label, and stale-label papers are not PASS. "
            "Synthetic crops are not acceptable evidence."
        ),
        "review_authority": _rollup_authority(rows),
        "human_review_conducted": any(
            row["review_authority"] == "human" and row["labels_reviewed"] for row in rows
        ),
        "papers_reviewed_by_agent": sum(
            row["review_authority"] == "agent_visual" for row in rows
        ),
        "papers": rows,
        "totals": {
            "papers": len(rows),
            "refreshed": sum(row["labels_refreshed"] for row in rows),
            "reviewed": sum(row["review_status"] == "REVIEWED" for row in rows),
            "unknown": sum(row["review_status"] != "REVIEWED" for row in rows),
            "zero_label": sum(row["labels_total"] == 0 for row in rows),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--census", default=str(DEFAULT_CENSUS))
    parser.add_argument("--sample", default=str(DEFAULT_SAMPLE))
    parser.add_argument("--pack", default=str(DEFAULT_PACK))
    parser.add_argument("--work-root", default=str(ROOT / ".work" / "r3-reattribution"))
    args = parser.parse_args()

    pack_root = Path(args.pack)
    index = build_pack(
        Path(args.census), Path(args.sample), pack_root,
        Path(args.work_root) if args.work_root else None,
    )
    _write_text(pack_root / "index.json", json.dumps(index, ensure_ascii=False, indent=2))
    print(json.dumps(index["totals"], ensure_ascii=False))
    print(f"Wrote {pack_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
