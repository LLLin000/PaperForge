#!/usr/bin/env python
"""R2b: content-level audit for rebuild text decreases.

Runs the real rebuild in an isolated vault and compares old/new structured
blocks by (page, block_id) and by normalized text. It never writes the source
vault.

Usage:
  python scripts/dev/r2_content_audit.py --summary docs/evidence/r2/full-ready-summary.json \
      --vault D:/L/OB/Literature-hub --out docs/evidence/r2-audit/content.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from paperforge.config import bootstrap_config  # noqa: E402
from paperforge.pdf_resolver import resolve_source_pdf  # noqa: E402
from paperforge.worker.ocr_rebuild import _rebuild_one_paper  # noqa: E402


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


SECTION_NUMBER_RE = re.compile(r"^\s*(?:\d+(?:\.\d+)*\.?|[IVXLC]+\.?)\s+")


def strip_format(text: str) -> str:
    """Remove only syntax that cannot change semantic text: Markdown heading
    markers, wiki embeds, leading section numbering, and whitespace."""
    value = re.sub(r"(?m)^\s*#{1,6}\s*", "", str(text or ""))
    value = re.sub(r"!?\[\[[^\]]+\]\]", "", value)
    value = SECTION_NUMBER_RE.sub("", value)
    return norm(value)


def is_metadata_normalization(old: str, new: str) -> bool:
    old_l = old.lower()
    return old_l.startswith(("received", "accepted")) and bool(
        re.search(r"\b(?:19|20)\d{2}\b", new)
    )


def paragraphs(text: str) -> list[str]:
    value = re.sub(r"(?m)^\s*#{1,6}\s*", "", str(text or ""))
    value = re.sub(r"!?\[\[[^\]]+\]\]", "", value)
    return [norm(part) for part in re.split(r"\n\s*\n", value) if norm(part)]


def read_blocks(path: Path) -> list[dict]:
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def block_map(rows: list[dict]) -> dict[tuple[int, str], dict]:
    out = {}
    for row in rows:
        try:
            key = (int(row.get("page", 0) or 0), str(row.get("block_id", "")))
        except Exception:
            continue
        out[key] = row
    return out


def token_coverage(text: str, corpus: str) -> float:
    tokens = [t for t in re.findall(r"\w+", text.lower()) if len(t) > 1]
    if not tokens:
        return 1.0
    corpus_tokens = set(re.findall(r"\w+", corpus.lower()))
    return sum(1 for t in tokens if t in corpus_tokens) / len(tokens)


def audit_one(vault: Path, key: str, workdir: Path) -> dict:
    source = vault / "System" / "PaperForge" / "ocr" / key
    old_blocks = read_blocks(source / "structure" / "blocks.structured.jsonl")
    old_text = (source / "fulltext.md").read_text(encoding="utf-8") if (source / "fulltext.md").is_file() else ""
    old_norm = len(re.sub(r"(?m)^\s*#{1,6}\s*", "", re.sub(r"!?\[\[[^\]]+\]\]", "", old_text)))

    temp = Path(tempfile.mkdtemp(prefix=f"r2b-{key}-", dir=str(workdir)))
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
        new_blocks = read_blocks(rebuilt / "structure" / "blocks.structured.jsonl")
        new_text = (rebuilt / "fulltext.md").read_text(encoding="utf-8") if (rebuilt / "fulltext.md").is_file() else ""
        new_norm = len(re.sub(r"(?m)^\s*#{1,6}\s*", "", re.sub(r"!?\[\[[^\]]+\]\]", "", new_text)))
        old_map, new_map = block_map(old_blocks), block_map(new_blocks)
        new_by_text: dict[str, list[tuple[int, str]]] = {}
        for k, row in new_map.items():
            new_by_text.setdefault(norm(row.get("text")), []).append(k)

        retained = moved = changed = removed = 0
        true_loss = []
        changed_detail = []
        removed_detail = []
        moved_detail = []
        for k, old in old_map.items():
            old_text_block = norm(old.get("text"))
            if not old_text_block:
                continue
            if k in new_map and norm(new_map[k].get("text")) == old_text_block:
                retained += 1
                continue
            if k in new_map:
                changed += 1
                new_text_block = norm(new_map[k].get("text"))
                coverage = token_coverage(old_text_block, new_text_block)
                if strip_format(old_text_block) == strip_format(new_text_block):
                    attribution = "format_only"
                elif is_metadata_normalization(old_text_block, new_text_block):
                    attribution = "metadata_normalization"
                elif old_text_block in new_by_text:
                    attribution = "moved"
                else:
                    attribution = "text_change"
                item = {
                    "page": k[0], "block_id": k[1],
                    "old_role": old.get("role"), "new_role": new_map[k].get("role"),
                    "old_text": old_text_block[:500], "new_text": new_text_block[:500],
                    "old_sha256": sha256_text(old_text_block),
                    "new_sha256": sha256_text(new_text_block),
                    "coverage": round(coverage, 3),
                    "attribution": attribution,
                    "moved_to": new_by_text.get(old_text_block, []),
                }
                changed_detail.append(item)
                if attribution not in {"format_only", "moved"}:
                    true_loss.append({"kind": "changed", **item})
                continue
            if old_text_block in new_by_text:
                moved += 1
                moved_detail.append({
                    "page": k[0], "block_id": k[1], "role": old.get("role"),
                    "text": old_text_block[:500], "moved_to": new_by_text[old_text_block],
                })
                continue
            removed += 1
            item = {
                "page": k[0], "block_id": k[1], "role": old.get("role"),
                "text": old_text_block[:500],
                "old_sha256": sha256_text(old_text_block),
            }
            removed_detail.append(item)
            true_loss.append({"kind": "removed", **item})

        old_paras = paragraphs(old_text)
        new_norm_text = norm(re.sub(r"(?m)^\s*#{1,6}\s*", "", re.sub(r"!?\[\[[^\]]+\]\]", "", new_text)))
        fulltext_loss = []
        for para in old_paras:
            if para in new_norm_text:
                continue
            coverage = token_coverage(para, new_norm_text)
            if coverage < 0.8:
                fulltext_loss.append({"text": para[:500], "sha256": sha256_text(para), "coverage": round(coverage, 3)})
        if fulltext_loss:
            true_loss.extend({"kind": "fulltext", **item} for item in fulltext_loss)

        verdict = "HOLD" if true_loss else "PASS"

        return {
            "key": key,
            "rebuild_status": result.get("status"),
            "old_blocks": len(old_blocks), "new_blocks": len(new_blocks),
            "old_structured_chars": sum(len(str(r.get("text", ""))) for r in old_blocks),
            "new_structured_chars": sum(len(str(r.get("text", ""))) for r in new_blocks),
            "old_normalized_chars": old_norm, "new_normalized_chars": new_norm,
            "old_fulltext_sha256": sha256_text(old_text), "new_fulltext_sha256": sha256_text(new_text),
            "old_structured_sha256": sha256_text("\n".join(str(r.get("text", "")) for r in old_blocks)),
            "new_structured_sha256": sha256_text("\n".join(str(r.get("text", "")) for r in new_blocks)),
            "retained": retained, "moved": moved, "changed": changed, "removed": removed,
            "fulltext_loss": fulltext_loss,
            "true_loss_count": len(true_loss),
            "true_loss": true_loss,
            "changed_detail": changed_detail,
            "removed_detail": removed_detail,
            "moved_detail": moved_detail,
            "verdict": verdict,
        }
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def keys_from_summary(path: Path, classes: set[str]) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    keys = set()
    for failure in data.get("failures", []):
        for error in failure.get("errors", []):
            if error.split(":", 1)[0] in classes:
                keys.add(failure["key"])
    return sorted(keys)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default="D:/L/OB/Literature-hub")
    ap.add_argument("--summary", default=str(REPO / "docs/evidence/r2/full-ready-summary.json"))
    ap.add_argument(
        "--classes",
        default=(
            "historical_text_decrease,structured_text_decrease,"
            "historical_structured_chars_decrease,historical_object_missing"
        ),
    )
    ap.add_argument("--keys", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--workdir", default="")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--one", default="")
    args = ap.parse_args()

    vault = Path(args.vault).resolve()
    if not args.one and not args.out:
        ap.error("--out is required unless --one is used")
    if args.one:
        workdir = Path(args.workdir or tempfile.mkdtemp(prefix="r2b-parent-")).resolve()
        workdir.mkdir(parents=True, exist_ok=True)
        print(json.dumps(audit_one(vault, args.one, workdir), ensure_ascii=False))
        return

    classes = {c.strip() for c in args.classes.split(",") if c.strip()}
    keys = [k.strip() for k in args.keys.split(",") if k.strip()] or keys_from_summary(Path(args.summary), classes)
    workdir = Path(args.workdir or tempfile.mkdtemp(prefix="r2b-parent-")).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(
                subprocess.run,
                [sys.executable, str(Path(__file__).resolve()), "--one", key,
                 "--vault", str(vault), "--workdir", str(workdir)],
                capture_output=True, text=True,
            ): key for key in keys
        }
        for future in as_completed(futures):
            key = futures[future]
            proc = future.result()
            try:
                results.append(json.loads(proc.stdout.strip().splitlines()[-1]))
            except Exception:
                results.append({"key": key, "verdict": "HOLD", "error": proc.stderr[-1000:] or proc.stdout[-1000:]})
            print(f"{key}: {results[-1].get('verdict')}", flush=True)
    results.sort(key=lambda item: item["key"])
    out = {
        "schema": "paperforge.r2.content_audit.v1",
        "keys": len(keys),
        "pass": sum(1 for r in results if r.get("verdict") == "PASS"),
        "hold": sum(1 for r in results if r.get("verdict") == "HOLD"),
        "results": results,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"keys": out["keys"], "pass": out["pass"], "hold": out["hold"]}))


if __name__ == "__main__":
    main()
