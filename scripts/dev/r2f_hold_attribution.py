#!/usr/bin/env python
"""R2f: attribute fulltext-only HOLD paragraphs for selected papers."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from paperforge.config import bootstrap_config  # noqa: E402
from paperforge.pdf_resolver import resolve_source_pdf  # noqa: E402
from paperforge.worker.ocr_rebuild import _rebuild_one_paper  # noqa: E402
from scripts.dev.r2_content_audit import norm, paragraphs, read_blocks, token_coverage  # noqa: E402

NON_BODY_ROLES = {"noise", "page_header", "page_footer", "frontmatter_noise"}


def best_block(paragraph: str, blocks: list[dict]) -> dict:
    best = {"coverage": 0.0}
    for block in blocks:
        text = norm(block.get("text"))
        if not text:
            continue
        coverage = token_coverage(paragraph, text)
        if coverage > best["coverage"]:
            best = {
                "coverage": round(coverage, 3),
                "page": block.get("page"),
                "block_id": block.get("block_id"),
                "role": block.get("role"),
                "text": text[:300],
            }
    return best


def audit_one(vault: Path, key: str) -> dict:
    source = vault / "System" / "PaperForge" / "ocr" / key
    old_text = (source / "fulltext.md").read_text(encoding="utf-8") if (source / "fulltext.md").is_file() else ""
    old_blocks = read_blocks(source / "structure" / "blocks.structured.jsonl")
    temp = Path(tempfile.mkdtemp(prefix=f"r2f-{key}-"))
    try:
        v = temp / "vault"
        paper = v / "System" / "PaperForge" / "ocr" / key
        shutil.copytree(source, paper, ignore=shutil.ignore_patterns("backups", "versions"))
        meta = json.loads((paper / "meta.json").read_text(encoding="utf-8"))
        pdf = resolve_source_pdf(vault, meta.get("source_pdf"))
        if pdf is not None:
            meta["source_pdf"] = str(pdf)
            (paper / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        bootstrap_config(v)
        result = _rebuild_one_paper(v, key)
        rebuilt = v / "System" / "PaperForge" / "ocr" / key
        new_text = (rebuilt / "fulltext.md").read_text(encoding="utf-8") if (rebuilt / "fulltext.md").is_file() else ""
        new_blocks = read_blocks(rebuilt / "structure" / "blocks.structured.jsonl")
        new_norm = norm(re.sub(r"(?m)^\s*#{1,6}\s*", "", re.sub(r"!?\[\[[^\]]+\]\]", "", new_text)))
        items = []
        for para in paragraphs(old_text):
            if para in new_norm:
                continue
            coverage = token_coverage(para, new_norm)
            if coverage >= 0.8:
                continue
            old_hits = [
                {
                    "page": b.get("page"),
                    "block_id": b.get("block_id"),
                    "role": b.get("role"),
                    "text": norm(b.get("text"))[:200],
                }
                for b in old_blocks
                if norm(b.get("text"))
                and (norm(b.get("text")) in para or para in norm(b.get("text")))
            ]
            roles = {str(h.get("role")) for h in old_hits}
            best = best_block(para, new_blocks)
            if para.startswith("<!-- page"):
                attribution = "page_marker_noise"
            elif roles and roles <= NON_BODY_ROLES:
                attribution = "non_body_old"
            elif best.get("coverage", 0) >= 0.8:
                attribution = "moved_to_block"
            elif best.get("role") == "figure_inner_text" and "figure_inner_text" in roles:
                attribution = "moved_to_figure_inner_text"
            else:
                attribution = "unresolved"
            items.append({
                "text": para[:500],
                "coverage_in_new_fulltext": round(coverage, 3),
                "old_roles": sorted(roles),
                "old_hits": old_hits[:3],
                "best_new_block": best,
                "attribution": attribution,
            })
        return {"key": key, "rebuild_status": result.get("status"), "items": items}
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default="D:/L/OB/Literature-hub")
    ap.add_argument("--keys", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    vault = Path(args.vault).resolve()
    keys = [k.strip() for k in args.keys.split(",") if k.strip()]
    results = [audit_one(vault, key) for key in keys]
    out = {"schema": "paperforge.r2f.attribution.v1", "results": results}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    for r in results:
        counts = {
            attribution: sum(1 for item in r["items"] if item["attribution"] == attribution)
            for attribution in {item["attribution"] for item in r["items"]}
        }
        print(r["key"], len(r["items"]), counts)


if __name__ == "__main__":
    main()
