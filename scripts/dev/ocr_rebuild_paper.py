"""Unified OCR paper rebuild entry point.

Rebuilds derived-layer artifacts (structured blocks, metadata, figures, render,
and block trace) for one or more papers from stored raw blocks.

The rebuild reads from the vault's PaperForge OCR storage, not from git:
    D:/Zotero-Vault/System/PaperForge/ocr/<KEY>/

It re-runs: build_structured_blocks → resolve_metadata → build figures/tables →
extract objects → render_fulltext_markdown → write render/ + compat fulltext.

Usage:
    python scripts/dev/ocr_rebuild_paper.py DWQQK2YB
        # Full rebuild for a single paper

    python scripts/dev/ocr_rebuild_paper.py DWQQK2YB CAQNW9Q2
        # Rebuild multiple papers sequentially

    python scripts/dev/ocr_rebuild_paper.py --trace DWQQK2YB
        # Rebuild + regenerate block_trace.csv (for test fixture comparison)

    python scripts/dev/ocr_rebuild_paper.py --trace-only DWQQK2YB
        # Regenerate block_trace.csv only, skip fulltext/figures rebuild

    python scripts/dev/ocr_rebuild_paper.py --dump-stages-only --ocr-dir <ocr_root> DWQQK2YB
        # Dump per-stage V3 role transitions into .work/ocr-stage-dumps/<KEY>/stages_summary.json

This is the canonical entry point that will later be wired into the CLI:
    paperforge ocr rebuild <KEY>

Requires:
    - blocks.raw.jsonl in <vault>/System/PaperForge/ocr/<KEY>/canonical/
    - source_metadata.json in <vault>/System/PaperForge/ocr/<KEY>/raw/
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

_VAULT_OCR = Path("D:/Zotero-Vault/System/PaperForge/ocr")
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


def _role_counts(blocks: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for block in blocks:
        role = str(block.get("role") or "")
        counts[role] = counts.get(role, 0) + 1
    return counts


def _block_state_snapshot(block: dict) -> dict[str, object]:
    return {
        "role": block.get("role"),
        "role_candidate": block.get("role_candidate"),
        "_object_owner_id": block.get("_object_owner_id"),
        "_object_association_reason": block.get("_object_association_reason"),
    }


def _record_transitions(
    transitions: list[dict],
    from_stage: str,
    to_stage: str,
    prev_states: list[dict[str, object]],
    blocks: list[dict],
) -> list[dict[str, object]]:
    curr_states = [_block_state_snapshot(b) for b in blocks]
    for idx, (before, after) in enumerate(zip(prev_states, curr_states)):
        if before != after:
            block = blocks[idx]
            transitions.append({
                "from_stage": from_stage,
                "to_stage": to_stage,
                "block_index": idx,
                "page": block.get("page"),
                "block_id": block.get("block_id"),
                "text_preview": str(block.get("text") or "")[:120],
                "before": before,
                "after": after,
            })
    return curr_states


def dump_v3_stage_transitions(
    paper_key: str,
    raw_blocks: list[dict],
    *,
    source_metadata: dict | None = None,
    page_pdf_lines_by_page: dict[int, list[dict]] | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Run the 5 in-memory OCR V3 stages and record role/ownership transitions."""
    from paperforge.worker.ocr_blocks import build_structured_blocks
    from paperforge.worker.ocr_object_stage import commit_object_roles, run_association_stage
    from paperforge.worker.ocr_post_match_normalize import post_match_normalize
    from paperforge.worker.ocr_pre_match_normalize import pre_match_normalize

    out_dir = output_dir if output_dir is not None else (_REPO_ROOT / ".work" / "ocr-stage-dumps" / paper_key)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "stages_summary.json"

    stage_order = [
        "1_seed_roles",
        "2_pre_match_normalize",
        "3_object_matching",
        "4_post_match_normalize",
        "5_object_writebacks",
    ]
    stage_role_counts: dict[str, dict[str, int]] = {}
    transitions: list[dict] = []

    structured, doc_structure = build_structured_blocks(
        raw_blocks,
        source_metadata=source_metadata,
        structure_output_dir=None,
        normalize_mode="seed_only",
    )
    stage_role_counts["1_seed_roles"] = _role_counts(structured)
    prev_states = [_block_state_snapshot(b) for b in structured]

    structured, doc_structure = pre_match_normalize(
        structured,
        source_frontmatter_anchors=getattr(doc_structure, "source_frontmatter_anchors", None),
        document_structure=doc_structure,
    )
    stage_role_counts["2_pre_match_normalize"] = _role_counts(structured)
    prev_states = _record_transitions(
        transitions, "1_seed_roles", "2_pre_match_normalize", prev_states, structured
    )

    stage = run_association_stage(structured, page_pdf_lines_by_page=page_pdf_lines_by_page)
    stage_role_counts["3_object_matching"] = _role_counts(structured)
    prev_states = _record_transitions(
        transitions, "2_pre_match_normalize", "3_object_matching", prev_states, structured
    )

    structured, doc_structure = post_match_normalize(
        structured,
        stage.figures,
        stage.tables,
        document_structure=doc_structure,
        source_frontmatter_anchors=getattr(doc_structure, "source_frontmatter_anchors", None),
    )
    stage_role_counts["4_post_match_normalize"] = _role_counts(structured)
    prev_states = _record_transitions(
        transitions, "3_object_matching", "4_post_match_normalize", prev_states, structured
    )

    commit_object_roles(structured, stage.figures, stage.tables)
    stage_role_counts["5_object_writebacks"] = _role_counts(structured)
    _record_transitions(
        transitions, "4_post_match_normalize", "5_object_writebacks", prev_states, structured
    )

    payload = {
        "paper_key": paper_key,
        "block_count": len(structured),
        "stages": stage_order,
        "stage_role_counts": stage_role_counts,
        "transition_count": len(transitions),
        "transitions": transitions,
    }
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary_path


def rebuild_paper(
    vault_ocr: Path,
    paper_key: str,
    *,
    trace: bool = False,
    trace_only: bool = False,
    dump_stages: bool = False,
    dump_stages_only: bool = False,
    dump_output_dir: Path | None = None,
) -> dict:
    """Rebuild a single paper from stored raw blocks.

    Returns a dict with paper_key, rebuilt, trace_path, stage_dump_path, and errors.
    """
    from paperforge.worker.ocr_rebuild import run_derived_rebuild_for_keys

    result: dict = {
        "paper_key": paper_key,
        "rebuilt": False,
        "trace_path": None,
        "stage_dump_path": None,
        "errors": [],
    }

    vault_root = vault_ocr.parents[2]  # ocr/ -> PaperForge/ -> System/ -> vault
    if vault_root.name == "System":
        vault_root = vault_root.parent  # System/ -> vault

    if not trace_only and not dump_stages_only:
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

    if dump_stages or dump_stages_only:
        try:
            paper_dir = vault_ocr / paper_key
            raw_jsonl = paper_dir / "canonical" / "blocks.raw.jsonl"
            if not raw_jsonl.exists():
                raise FileNotFoundError(f"blocks.raw.jsonl not found: {raw_jsonl}")
            raw_blocks = [json.loads(l) for l in raw_jsonl.read_text(encoding="utf-8").splitlines() if l.strip()]
            source_metadata = _load_source_metadata(paper_dir)
            dump_path = dump_v3_stage_transitions(
                paper_key,
                raw_blocks,
                source_metadata=source_metadata,
                output_dir=dump_output_dir,
            )
            result["stage_dump_path"] = str(dump_path)
        except Exception as exc:
            result["errors"].append(f"stage dump failed: {exc}")

    return result


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return 0

    trace = False
    trace_only = False
    dump_stages = False
    dump_stages_only = False
    dump_output_dir: Path | None = None
    vault_ocr = _VAULT_OCR
    keys: list[str] = []
    idx = 0
    while idx < len(args):
        token = args[idx]
        if token == "--trace":
            trace = True
        elif token == "--trace-only":
            trace_only = True
        elif token == "--dump-stages":
            dump_stages = True
        elif token == "--dump-stages-only":
            dump_stages_only = True
        elif token == "--dump-dir":
            if idx + 1 >= len(args):
                print("Error: --dump-dir requires a path argument", file=sys.stderr)
                return 1
            dump_output_dir = Path(args[idx + 1])
            idx += 1
        elif token.startswith("--dump-dir="):
            dump_output_dir = Path(token.split("=", 1)[1])
        elif token == "--ocr-dir":
            if idx + 1 >= len(args):
                print("Error: --ocr-dir requires a path argument", file=sys.stderr)
                return 1
            vault_ocr = Path(args[idx + 1])
            idx += 1
        elif token.startswith("--ocr-dir="):
            vault_ocr = Path(token.split("=", 1)[1])
        else:
            keys.append(token)
        idx += 1

    if not keys:
        print("Error: at least one paper key required", file=sys.stderr)
        return 1

    if not vault_ocr.exists():
        print(f"Error: vault OCR directory not found: {vault_ocr}", file=sys.stderr)
        return 1

    for paper_key in keys:
        print(f"\n=== Rebuilding {paper_key} ===")
        result = rebuild_paper(
            vault_ocr,
            paper_key,
            trace=trace,
            trace_only=trace_only,
            dump_stages=dump_stages,
            dump_stages_only=dump_stages_only,
            dump_output_dir=dump_output_dir,
        )

        if result["errors"]:
            for err in result["errors"]:
                print(f"  [!] {err}")

        if result["rebuilt"]:
            print("  [OK] Derived artifacts rebuilt")
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

        if result.get("stage_dump_path"):
            print(f"  [OK] stages_summary.json written: {result['stage_dump_path']}")

        if (
            not result["rebuilt"]
            and not result.get("trace_path")
            and not result.get("stage_dump_path")
            and not result["errors"]
        ):
            print(f"  No actions taken for {paper_key}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
