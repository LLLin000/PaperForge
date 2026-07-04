"""Full vault v3 vs legacy corpus diff.

Runs legacy and v3 pipelines on every paper in the vault and compares:
- Role distribution
- render_default count
- index_default count
- Matched figure count
- Table count

Usage:
    python scripts/dev/corpus_v3_diff_full.py
    python scripts/dev/corpus_v3_diff_full.py --trace  # print each paper before/after
    python scripts/dev/corpus_v3_diff_full.py --report-only  # just show previous result
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[2]  # scripts/dev/ -> scripts/ -> repo root
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

VAULT_OCR = Path("D:/L/OB/Literature-hub/System/PaperForge/ocr")
RESULT_PATH = _REPO_ROOT / "docs" / "superpowers" / "analysis" / "2026-07-05-v3-full-vault-corpus-diff.json"


def _load_paper(key: str) -> tuple[list[dict], dict]:
    """Load raw blocks and source metadata from vault."""
    paper_dir = VAULT_OCR / key
    raw_jsonl = paper_dir / "canonical" / "blocks.raw.jsonl"
    meta_json = paper_dir / "raw" / "source_metadata.json"

    if not raw_jsonl.exists():
        raw_jsonl = paper_dir / "structure" / "blocks.raw.jsonl"
    if not raw_jsonl.exists():
        return None, None

    raw_blocks = []
    for line in raw_jsonl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            raw_blocks.append(json.loads(line))

    meta = {}
    if meta_json.exists():
        meta = json.loads(meta_json.read_text(encoding="utf-8"))

    return raw_blocks, meta


def _run_legacy(key: str) -> dict | None:
    from paperforge.worker.ocr_blocks import build_structured_blocks
    from paperforge.worker.ocr_figures import build_figure_inventory
    from paperforge.worker.ocr_tables import build_table_inventory

    raw_blocks, meta = _load_paper(key)
    if raw_blocks is None:
        return None

    try:
        rows, doc = build_structured_blocks(raw_blocks, source_metadata=meta)
        fig = build_figure_inventory(rows)
        tab = build_table_inventory(rows)
        return {"rows": rows, "fig": fig, "tab": tab}
    except Exception as exc:
        return {"error": str(exc)}


def _run_v3(key: str) -> dict | None:
    from paperforge.worker.ocr_blocks import build_structured_blocks
    from paperforge.worker.ocr_figures import build_figure_inventory
    from paperforge.worker.ocr_tables import build_table_inventory
    from paperforge.worker.ocr_pre_match_normalize import pre_match_normalize
    from paperforge.worker.ocr_post_match_normalize import post_match_normalize

    raw_blocks, meta = _load_paper(key)
    if raw_blocks is None:
        return None

    try:
        rows_seed, doc_seed = build_structured_blocks(
            raw_blocks,
            source_metadata=meta,
            normalize_mode="seed_only",
        )
        rows_pre, doc_pre = pre_match_normalize(
            rows_seed,
            source_frontmatter_anchors=getattr(doc_seed, "source_frontmatter_anchors", None),
            document_structure=doc_seed,
        )
        fig = build_figure_inventory(rows_pre)
        tab = build_table_inventory(rows_pre)
        rows_post, doc_post = post_match_normalize(
            rows_pre, fig, tab,
            document_structure=doc_pre,
            source_frontmatter_anchors=getattr(doc_pre, "source_frontmatter_anchors", None),
        )
        return {"rows": rows_post, "fig": fig, "tab": tab}
    except Exception as exc:
        return {"error": str(exc)}


def _role_counter(rows: list[dict]) -> dict:
    return dict(Counter(str(b.get("role") or "") for b in rows))


def _count_truthy(rows: list[dict], field: str) -> int:
    return sum(1 for b in rows if b.get(field))


def _compare(key: str, trace: bool = False) -> dict:
    legacy = _run_legacy(key)
    v3 = _run_v3(key)

    if legacy is None or v3 is None:
        return {"paper": key, "error": "missing raw data"}

    if "error" in legacy:
        return {"paper": key, "error": f"legacy: {legacy['error']}"}
    if "error" in v3:
        return {"paper": key, "error": f"v3: {v3['error']}"}

    l_rows = legacy["rows"]
    v_rows = v3["rows"]

    result = {"paper": key, "diff": False}

    l_roles = _role_counter(l_rows)
    v_roles = _role_counter(v_rows)
    if l_roles != v_roles:
        result["diff"] = True
        result["role_diff"] = {"legacy": l_roles, "v3": v_roles}

    l_render = _count_truthy(l_rows, "render_default")
    v_render = _count_truthy(v_rows, "render_default")
    if l_render != v_render:
        result["diff"] = True
        result["render_diff"] = {"legacy": l_render, "v3": v_render}

    l_index = _count_truthy(l_rows, "index_default")
    v_index = _count_truthy(v_rows, "index_default")
    if l_index != v_index:
        result["diff"] = True
        result["index_diff"] = {"legacy": l_index, "v3": v_index}

    l_fig = len(legacy["fig"].get("matched_figures", []))
    v_fig = len(v3["fig"].get("matched_figures", []))
    if l_fig != v_fig:
        result["diff"] = True
        result["figure_diff"] = {"legacy": l_fig, "v3": v_fig}

    l_tab = len(legacy["tab"].get("tables", []))
    v_tab = len(v3["tab"].get("tables", []))
    if l_tab != v_tab:
        result["diff"] = True
        result["table_diff"] = {"legacy": l_tab, "v3": v_tab}

    return result


def main() -> None:
    trace = "--trace" in sys.argv
    report_only = "--report-only" in sys.argv

    # Read previous result if exists
    if report_only and RESULT_PATH.exists():
        data = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        _print_report(data)
        return

    # Enumerate papers
    papers = sorted(
        d.name for d in VAULT_OCR.iterdir()
        if d.is_dir() and d.name[0].isupper() and len(d.name) == 8
    )
    print(f"Papers found: {len(papers)}")

    results: list[dict] = []
    diffs = 0
    errors = 0
    skipped = 0
    t0 = time.time()

    for i, key in enumerate(papers):
        result = _compare(key, trace=trace)
        results.append(result)

        if "error" in result:
            errors += 1
            print(f"  [{i+1}/{len(papers)}] {key}: ERROR {result['error']}")
        elif result.get("diff"):
            diffs += 1
            print(f"  [{i+1}/{len(papers)}] {key}: DIFF")
        else:
            status = "."
            if (i + 1) % 50 == 0:
                status = f"{i+1}/{len(papers)}"
            print(f"  [{i+1}/{len(papers)}] {key}: OK" if trace else f"  {status}", end="\n" if trace else "")

        # Save incrementally
        if (i + 1) % 50 == 0 or i == len(papers) - 1:
            _save_progress(results, diffs, errors, skipped, len(papers), t0)

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"Total: {len(papers)}, Diff: {diffs}, Error: {errors}, Skipped: {skipped}")
    print(f"Elapsed: {elapsed:.0f}s ({elapsed/len(papers):.2f}s/paper)")
    _save_progress(results, diffs, errors, skipped, len(papers), t0)
    _print_report({"papers": len(papers), "diff": diffs, "error": errors, "skipped": skipped, "results": results})


def _save_progress(results, diffs, errors, skipped, total, t0):
    data = {
        "papers": total,
        "diff": diffs,
        "error": errors,
        "skipped": skipped,
        "elapsed_seconds": time.time() - t0,
        "results": results,
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _print_report(data):
    print(f"\n=== Full Vault Corpus Diff ===")
    print(f"Papers:     {data.get('papers', '?')}")
    print(f"No diff:    {data.get('papers', 0) - data.get('diff', 0) - data.get('error', 0) - data.get('skipped', 0)}")
    print(f"Diff:       {data.get('diff', 0)}")
    print(f"Error:      {data.get('error', 0)}")
    print(f"Skipped:    {data.get('skipped', 0)}")
    for r in data.get("results", []):
        if r.get("diff") or "error" in r:
            print(f"  {'DIFF' if r.get('diff') else 'ERROR'} {r['paper']}: ", end="")
            for k in ("role_diff", "render_diff", "index_diff", "figure_diff", "table_diff"):
                if k in r:
                    print(f"{k}={r[k]} ", end="")
            if "error" in r:
                print(f"error={r['error']} ", end="")
            print()


if __name__ == "__main__":
    main()
