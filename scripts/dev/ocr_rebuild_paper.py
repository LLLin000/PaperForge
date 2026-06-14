"""Unified OCR paper rebuild entry point.

Rebuilds derived-layer artifacts (structured blocks, metadata, figures, render,
and block trace) for one or more papers from stored raw blocks.

Usage:
    python scripts/dev/ocr_rebuild_paper.py DWQQK2YB
    python scripts/dev/ocr_rebuild_paper.py DWQQK2YB CAQNW9Q2
    python scripts/dev/ocr_rebuild_paper.py --trace DWQQK2YB
    python scripts/dev/ocr_rebuild_paper.py --trace-only DWQQK2YB

This is the canonical entry point that will later be wired into the CLI.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

# Ensure paperforge is importable from the current repo root
_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[2]  # scripts/dev/ -> scripts/ -> repo root
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ---- constants (mirrors regenerate_traces.py field names) ----
_FIELD_NAMES = [
    "page", "block_id", "raw_label", "content_preview", "bbox",
    "role", "role_confidence", "evidence",
    "seed_role", "seed_confidence",
    "zone", "style_family", "marker_type",
    "render_default", "index_default",
]

_VAULT_OCR = Path("D:/L/OB/Literature-hub/System/PaperForge/ocr")
_FIXTURE_ROOT = _REPO_ROOT / "tests" / "fixtures" / "ocr_real_papers"


def _load_source_metadata(paper_dir: Path) -> dict | None:
    meta_json = paper_dir / "raw" / "source_metadata.json"
    if meta_json.exists():
        try:
            return json.loads(meta_json.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _write_block_trace(paper_key: str, blocks: list[dict], output_dir: Path | None = None) -> Path:
    """Write block_trace.csv from structured blocks."""
    if output_dir is None:
        output_dir = _FIXTURE_ROOT / paper_key
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / "block_trace.csv"

    rows = []
    for block in blocks:
        bbox = block.get("bbox") or block.get("block_bbox") or [0, 0, 0, 0]
        marker_sig = block.get("marker_signature") or {}
        row = {
            "page": block.get("page", ""),
            "block_id": block.get("block_id", ""),
            "raw_label": block.get("raw_label", ""),
            "content_preview": (block.get("text") or "")[:200],
            "bbox": json.dumps(bbox),
            "role": block.get("role", ""),
            "role_confidence": block.get("role_confidence", ""),
            "evidence": json.dumps(block.get("evidence", [])) if block.get("evidence") else "",
            "seed_role": block.get("seed_role", ""),
            "seed_confidence": block.get("seed_confidence", ""),
            "zone": block.get("zone", ""),
            "style_family": block.get("style_family", ""),
            "marker_type": marker_sig.get("type", ""),
            "render_default": block.get("render_default", True),
            "index_default": block.get("index_default", True),
        }
        rows.append(row)

    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_FIELD_NAMES)
        writer.writeheader()
        writer.writerows(rows)

    return out


def rebuild_paper(vault_ocr: Path, paper_key: str, *, trace: bool = False, trace_only: bool = False) -> dict:
    """Rebuild a single paper from stored raw blocks.

    Returns a dict with paper_key, rebuilt, trace_path, and errors.
    """
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    result: dict = {"paper_key": paper_key, "rebuilt": False, "trace_path": None, "errors": []}

    vault_root = vault_ocr.parents[2]  # ocr/ -> PaperForge/ -> System/ -> vault
    if vault_root.name == "System":
        vault_root = vault_root.parent  # System/ -> vault

    if not trace_only:
        try:
            rb_result = run_derived_rebuild_for_keys(vault_root, [paper_key])
            result["rebuilt"] = rb_result.get("rebuild_count", 0) > 0
            result["rebuild_result"] = rb_result
        except Exception as exc:
            result["errors"].append(f"rebuild failed: {exc}")

    if trace or trace_only:
        try:
            from paperforge.worker.ocr_blocks import build_structured_blocks

            paper_dir = vault_ocr / paper_key
            raw_jsonl = paper_dir / "canonical" / "blocks.raw.jsonl"
            if not raw_jsonl.exists():
                raise FileNotFoundError(f"blocks.raw.jsonl not found: {raw_jsonl}")

            raw_blocks = [json.loads(l) for l in raw_jsonl.read_text(encoding="utf-8").splitlines() if l.strip()]
            source_metadata = _load_source_metadata(paper_dir)
            structured, _doc = build_structured_blocks(
                raw_blocks,
                source_metadata=source_metadata,
                structure_output_dir=None,
            )

            trace_path = _write_block_trace(paper_key, structured)
            result["trace_path"] = str(trace_path)
            result["trace_blocks"] = len(structured)

            # Build role/zone distribution for summary
            role_dist: dict[str, int] = {}
            zone_dist: dict[str, int] = {}
            for b in structured:
                r = b.get("role", "")
                z = b.get("zone", "")
                role_dist[r] = role_dist.get(r, 0) + 1
                zone_dist[z or "(no zone)"] = zone_dist.get(z or "(no zone)", 0) + 1
            result["role_distribution"] = role_dist
            result["zone_distribution"] = zone_dist
        except Exception as exc:
            result["errors"].append(f"trace generation failed: {exc}")

    return result


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return 0

    trace = "--trace" in args
    trace_only = "--trace-only" in args
    args = [a for a in args if a not in ("--trace", "--trace-only")]

    if not args:
        print("Error: at least one paper key required", file=sys.stderr)
        return 1

    vault_ocr = _VAULT_OCR
    if not vault_ocr.exists():
        print(f"Error: vault OCR directory not found: {vault_ocr}", file=sys.stderr)
        return 1

    for paper_key in args:
        print(f"\n=== Rebuilding {paper_key} ===")
        result = rebuild_paper(vault_ocr, paper_key, trace=trace, trace_only=trace_only)

        if result["errors"]:
            for err in result["errors"]:
                print(f"  [!] {err}")

        if result["rebuilt"]:
            print(f"  [OK] Derived artifacts rebuilt")
            build_dir = vault_ocr / paper_key / "render" / "fulltext.md"
            compat_dir = vault_ocr / paper_key / "fulltext.md"
            for p in [build_dir, compat_dir]:
                if p.exists():
                    print(f"  [OK] {p} ({p.stat().st_size} bytes)")

        if result.get("trace_path"):
            print(f"  [OK] block_trace.csv written ({result.get('trace_blocks', 0)} blocks)")
            print(f"  [OK] {result['trace_path']}")

            role_dist = result.get("role_distribution", {})
            if role_dist:
                print("  Role distribution:")
                for role, cnt in sorted(role_dist.items(), key=lambda x: -x[1]):
                    print(f"    {role}: {cnt}")

            zone_dist = result.get("zone_distribution", {})
            if zone_dist:
                print("  Zone distribution:")
                for zone, cnt in sorted(zone_dist.items(), key=lambda x: -x[1]):
                    print(f"    {zone}: {cnt}")

        if not result["rebuilt"] and not result.get("trace_path") and not result["errors"]:
            print(f"  No actions taken for {paper_key}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
