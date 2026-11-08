"""First parse vs derived rebuild equivalence, with the same PDF evidence.

For every paper the script builds a throwaway vault that holds the provider
result (``json/result.json``) and the paper metadata, then runs the two entry
points in the same vault in this order:

1. ``postprocess_ocr_result`` — the first-parse writer that runs when OCR is
   submitted;
2. ``_rebuild_one_paper`` — the derived rebuild.

The source PDF is kept resolvable the way production keeps it: an absolute
path, a ``storage:`` locator through ``paperforge.json``, or a ``[[vault]]``
wikilink whose file is copied into the throwaway vault.  The script compares
the final roles, render flags, object ownership, figure/table asset claims,
ownership resolutions/conflicts, rendered markdown and asset file hashes.

Read-only with respect to the real vault; it writes only to ``--workdir``
(default: a temp directory) and to ``--out`` when supplied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paperforge.config import bootstrap_config  # noqa: E402
from paperforge.worker.ocr import postprocess_ocr_result  # noqa: E402
from paperforge.worker.ocr_rebuild import _rebuild_one_paper  # noqa: E402

WIKILINK_RE = re.compile(r"^\[\[(.*?)\]\]$")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage_inputs(vault: Path, source_vault: Path, ocr_root: Path, key: str, zotero_dir: Path | None) -> dict:
    ocr = vault / "System" / "PaperForge" / "ocr" / key
    ocr.mkdir(parents=True, exist_ok=True)
    (ocr / "json").mkdir(exist_ok=True)
    (ocr / "raw").mkdir(exist_ok=True)
    source_paper = ocr_root / key
    shutil.copy2(source_paper / "json/result.json", ocr / "json/result.json")
    shutil.copy2(source_paper / "raw/source_metadata.json", ocr / "raw/source_metadata.json")
    meta = json.loads((source_paper / "meta.json").read_text(encoding="utf-8"))
    locator = str(meta.get("source_pdf") or "")
    copied_pdf = None
    match = WIKILINK_RE.match(locator)
    if match:
        source = source_vault / match.group(1)
        if source.exists():
            target = vault / match.group(1)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied_pdf = target
    (ocr / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    if zotero_dir is not None:
        config_path = vault / "paperforge.json"
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        config["zotero_data_dir"] = str(zotero_dir)
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return {"meta": meta, "pdf": copied_pdf, "locator": locator}


def _snapshot(ocr: Path) -> dict:
    rows = [
        json.loads(line)
        for line in (ocr / "structure/blocks.structured.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    roles = {
        (int(row.get("page", 0) or 0), str(row.get("block_id", ""))): (
            row.get("role"),
            bool(row.get("render_default")),
            bool(row.get("index_default")),
            row.get("_object_owner_id"),
            row.get("_object_owner_family"),
        )
        for row in rows
    }
    figures = json.loads((ocr / "structure/figure_inventory.json").read_text(encoding="utf-8"))
    tables = json.loads((ocr / "structure/table_inventory.json").read_text(encoding="utf-8"))
    claims = set()
    for figure in figures.get("matched_figures", []):
        page = int(figure.get("page", 0) or 0)
        for asset in figure.get("matched_assets") or []:
            claims.add(("figure_asset", str(figure.get("figure_id")), page, str(asset.get("block_id"))))
        for block_id in figure.get("asset_block_ids") or []:
            claims.add(("figure_asset_id", str(figure.get("figure_id")), page, str(block_id)))
    for table in tables.get("tables", []):
        if table.get("has_asset"):
            claims.add(
                (
                    "table_asset",
                    str(table.get("caption_block_id")),
                    int(table.get("page", 0) or 0),
                    str(table.get("asset_block_id")),
                )
            )
    render = ocr / "render/fulltext.md"
    assets = {}
    for path in sorted((ocr / "assets").rglob("*")) if (ocr / "assets").exists() else []:
        if path.is_file():
            assets[path.relative_to(ocr).as_posix()] = _sha(path)
    return {
        "rows": roles,
        "claims": claims,
        "resolutions": figures.get("ownership_resolutions") or [],
        "conflicts": figures.get("ownership_conflicts") or [],
        "markdown": render.read_text(encoding="utf-8") if render.exists() else "",
        "assets": assets,
        "figure_count": len(figures.get("matched_figures", [])),
        "table_count": len(tables.get("tables", [])),
    }


def _compare(first: dict, rebuilt: dict) -> dict:
    rows = sorted(set(first["rows"]) | set(rebuilt["rows"]))
    row_diffs = [
        {
            "page": page,
            "block_id": block_id,
            "first": first["rows"].get((page, block_id)),
            "rebuild": rebuilt["rows"].get((page, block_id)),
        }
        for page, block_id in rows
        if first["rows"].get((page, block_id)) != rebuilt["rows"].get((page, block_id))
    ]
    return {
        "row_diffs": len(row_diffs),
        "row_diff_sample": row_diffs[:10],
        "claim_diff": sorted(first["claims"] ^ rebuilt["claims"]),
        "resolutions_equal": first["resolutions"] == rebuilt["resolutions"],
        "conflicts_equal": first["conflicts"] == rebuilt["conflicts"],
        "markdown_equal": first["markdown"] == rebuilt["markdown"],
        "markdown_len": [len(first["markdown"]), len(rebuilt["markdown"])],
        "assets_equal": first["assets"] == rebuilt["assets"],
        "figure_count": [first["figure_count"], rebuilt["figure_count"]],
        "table_count": [first["table_count"], rebuilt["table_count"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True, help="Obsidian vault root (source of PDFs and papers)")
    parser.add_argument("--ocr-root", default="", help="OCR root; default <vault>/System/PaperForge/ocr")
    parser.add_argument("--keys", nargs="*", default=[], help="paper keys; default all with json/result.json")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workdir", default="")
    parser.add_argument("--out", default="")
    parser.add_argument("--zotero-dir", default="", help="Zotero data dir for storage: locators")
    args = parser.parse_args()

    vault = Path(args.vault)
    ocr_root = Path(args.ocr_root) if args.ocr_root else vault / "System/PaperForge/ocr"
    keys = args.keys or sorted(
        d.name for d in ocr_root.iterdir() if d.is_dir() and (d / "json/result.json").exists()
    )
    if args.limit:
        keys = keys[: args.limit]
    zotero_dir = Path(args.zotero_dir) if args.zotero_dir else None

    work = Path(args.workdir or tempfile.mkdtemp(prefix="pf-two-entry-"))
    work.mkdir(parents=True, exist_ok=True)
    reports = []
    for key in keys:
        paper_work = work / key
        if paper_work.exists():
            shutil.rmtree(paper_work)
        paper_work.mkdir(parents=True)
        vault_dir = paper_work / "vault"
        vault_dir.mkdir()
        bootstrap_config(vault_dir)
        staged = _stage_inputs(vault_dir, vault, ocr_root, key, zotero_dir)
        ocr = vault_dir / "System" / "PaperForge" / "ocr" / key
        try:
            all_results = json.loads((ocr / "json/result.json").read_text(encoding="utf-8"))
            first_meta = dict(staged["meta"])
            postprocess_ocr_result(vault_dir, key, all_results, first_meta)
            first = _snapshot(ocr)
            _rebuild_one_paper(vault_dir, key)
            rebuilt = _snapshot(ocr)
            report = {"key": key, "locator": staged["locator"][:120], "pdf_staged": bool(staged["pdf"])}
            report.update(_compare(first, rebuilt))
        except Exception as exc:  # noqa: BLE001 — report per paper, keep going
            report = {"key": key, "error": f"{type(exc).__name__}: {exc}"}
        reports.append(report)
        flagged = report.get("error") or report.get("row_diffs") or report.get("claim_diff") or not (
            report.get("markdown_equal") and report.get("assets_equal")
        )
        print(("FAIL " if flagged else "ok   ") + key, flush=True)

    bad = [r for r in reports if r.get("error") or r.get("row_diffs") or r.get("claim_diff") or not (
        r.get("markdown_equal") and r.get("assets_equal")
    )]
    print(f"papers={len(reports)} mismatched={len(bad)}")
    for report in bad[:10]:
        print(json.dumps(report, ensure_ascii=False)[:600])
    if args.out:
        Path(args.out).write_text(json.dumps(reports, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
