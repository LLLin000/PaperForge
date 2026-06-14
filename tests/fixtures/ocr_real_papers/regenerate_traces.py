"""Regenerate block_trace.csv by re-running build_structured_blocks from vault data."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, r"D:\L\Med\Research\99_System\LiteraturePipeline\github-release")

from paperforge.worker.ocr_blocks import build_structured_blocks

VAULT_OCR = Path(r"D:\L\OB\Literature-hub\System\PaperForge\ocr")
FIXTURE_ROOT = Path(r"D:\L\Med\Research\99_System\LiteraturePipeline\github-release\tests\fixtures\ocr_real_papers")

FIELD_NAMES = [
    "page", "block_id", "raw_label", "content_preview", "bbox",
    "role", "role_confidence", "evidence",
    "seed_role", "seed_confidence",
    "zone", "style_family", "marker_type",
    "render_default", "index_default",
]


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def regenerate(paper_key: str) -> None:
    paper_dir = VAULT_OCR / paper_key
    raw_jsonl = paper_dir / "canonical" / "blocks.raw.jsonl"
    meta_json = paper_dir / "raw" / "source_metadata.json"
    result_json = paper_dir / "json" / "result.json"

    if not raw_jsonl.exists():
        print(f"Skipping {paper_key}: no blocks.raw.jsonl at {raw_jsonl}")
        return

    # Load raw blocks
    raw_blocks = load_jsonl(raw_jsonl)
    print(f"\n=== Regenerating {paper_key} ({len(raw_blocks)} raw blocks) ===")

    # Load source metadata
    source_metadata = None
    if meta_json.exists():
        try:
            source_metadata = load_json(meta_json)
            print(f"  Source metadata loaded")
        except Exception:
            pass

    # Run build_structured_blocks
    rows, doc_structure = build_structured_blocks(raw_blocks, source_metadata=source_metadata)

    if not rows:
        print(f"  ERROR: No rows returned")
        return

    # Also load raw block text for fuller content_preview
    raw_lookup: dict[tuple[int, int], str] = {}
    try:
        raw_data = load_json(result_json)
        for payload in raw_data:
            for res in payload.get("layoutParsingResults", []):
                for block in res.get("prunedResult", {}).get("parsing_res_list", []):
                    page = block.get("page", 0)
                    bid = block.get("block_id", 0)
                    if page and bid:
                        raw_lookup[(page, bid)] = str(block.get("block_content", ""))
    except Exception:
        pass

    # Write block_trace.csv
    out_path = FIXTURE_ROOT / paper_key / "block_trace.csv"
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELD_NAMES)
        writer.writeheader()
        for row in rows:
            page = row.get("page", 0)
            bid = row.get("block_id", "")
            bbox = row.get("bbox", [0, 0, 0, 0])

            raw_content = raw_lookup.get((page, bid), row.get("text", ""))
            content_preview = str(raw_content)[:100].replace("\n", " ")

            marker = row.get("marker_signature") or {}
            writer.writerow({
                "page": page,
                "block_id": bid,
                "raw_label": row.get("raw_label", ""),
                "content_preview": content_preview,
                "bbox": str(bbox),
                "role": row.get("role", ""),
                "role_confidence": row.get("role_confidence", 0),
                "evidence": "; ".join(row.get("evidence", [])[:3]) if row.get("evidence") else "",
                "seed_role": row.get("seed_role", ""),
                "seed_confidence": row.get("seed_confidence", 0),
                "zone": row.get("zone", ""),
                "style_family": row.get("style_family", ""),
                "marker_type": marker.get("type", ""),
                "render_default": row.get("render_default", False),
                "index_default": row.get("index_default", False),
            })

    # Print role/zone distribution
    role_counts: dict[str, int] = {}
    zone_counts: dict[str, int] = {}
    for row in rows:
        role = row.get("role", "unassigned")
        zone = row.get("zone", "")
        role_counts[role] = role_counts.get(role, 0) + 1
        zone_counts[zone] = zone_counts.get(zone, 0) + 1

    print(f"  Wrote {len(rows)} rows to {out_path.name}")
    print(f"  Role distribution:")
    for role, count in sorted(role_counts.items(), key=lambda x: -x[1]):
        print(f"    {role:40s} {count}")
    print(f"  Zone distribution:")
    for zone, count in sorted(zone_counts.items(), key=lambda x: -x[1]):
        print(f"    {zone:40s} {count}")


if __name__ == "__main__":
    for key in ["DWQQK2YB", "CAQNW9Q2"]:
        regenerate(key)
    print("\nDone. Run: python -m pytest tests/test_ocr_trace_vs_expectations.py -s")
