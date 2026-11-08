"""Read-only migration dry-run for the Figure/Table lifecycle (M1).

For each paper it compares the current on-disk artifacts with a replay of the
merged pipeline and reports:

- identity: old figure ids (and duplicates) vs new canonical ids, with an
  anchor-based mapping;
- association: figure/table asset claims that change;
- delivery: render/assets added or removed, and fulltext embeds that would need
  retargeting;
- content integrity: structured role counters and body text length;
- unresolved differences.

The OCR vault is never written. ``--trial DIR`` additionally rebuilds selected
papers inside a throwaway vault copy and checks repeatability; the real vault is
only read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EMBED_RE = re.compile(r"!\[\[render/(figures|tables)/([^\]]+?)\]\]")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _norm(text: str) -> str:
    return " ".join(str(text or "").split()).casefold()[:120]


def _old_identity(paper_dir: Path) -> dict:
    figures = _read_json(paper_dir / "structure" / "figure_inventory.json").get("matched_figures", [])
    ids = [str(f.get("figure_id", "")) for f in figures]
    counts = Counter(ids)
    return {
        "entries": len(figures),
        "ids": ids,
        "duplicate_extra": sum(v - 1 for v in counts.values() if v > 1),
        "anchors": {
            (int(f.get("page", 0) or 0), str(f.get("legend_block_id", ""))): str(f.get("figure_id", ""))
            for f in figures
        },
        "claims": {
            str(f.get("figure_id", "")): sorted(
                str(a.get("block_id", ""))
                for a in (f.get("matched_assets") or [])
                if a.get("block_id") is not None
            )
            for f in figures
        },
        "entries_detail": [
            {
                "figure_id": str(f.get("figure_id", "")),
                "figure_number": f.get("figure_number"),
                "page": int(f.get("page", 0) or 0),
                "text": str(f.get("text", "") or ""),
            }
            for f in figures
        ],
    }


def _new_replay(vault: Path, ocr_root: Path, key: str) -> dict:
    from paperforge.pdf_resolver import resolve_source_pdf
    from paperforge.worker.ocr_blocks import build_structured_blocks
    from paperforge.worker.ocr_object_stage import commit_object_roles, run_association_stage
    from paperforge.worker.ocr_objects import extract_and_write_objects
    from paperforge.worker.ocr_pdf_spans import extract_pdf_lines_normalized
    from paperforge.worker.ocr_pre_match_normalize import pre_match_normalize

    paper_dir = ocr_root / key
    meta = _read_json(paper_dir / "meta.json")
    raw = _rows(paper_dir / "canonical/blocks.raw.jsonl")
    blocks, document = build_structured_blocks(raw, source_metadata={}, normalize_mode="seed_only")
    blocks, document = pre_match_normalize(
        blocks, source_frontmatter_anchors={}, document_structure=document
    )
    pdf = resolve_source_pdf(vault, meta.get("source_pdf"))
    lines = {}
    if pdf is not None:
        try:
            lines = extract_pdf_lines_normalized(pdf)
        except Exception:  # noqa: BLE001 — evidence is optional
            lines = {}
    stage = run_association_stage(blocks, page_pdf_lines_by_page=lines or None)
    commit_object_roles(blocks, stage.figures, stage.tables)
    manifest = extract_and_write_objects(
        pdf,
        stage.figures,
        stage.tables,
        paper_dir / "assets",
        paper_dir / "render",
        structured_blocks=blocks,
        dry_run=True,
    )
    return {
        "figures": stage.figures.get("matched_figures", []),
        "tables": stage.tables.get("tables", []),
        "rows": blocks,
        "manifest": manifest or {},
        "figure_inventory": stage.figures,
    }


def _identity_diff(old: dict, new_figures: list[dict]) -> dict:
    new_ids = [str(f.get("figure_id", "")) for f in new_figures]
    new_anchors = {
        (int(f.get("page", 0) or 0), str(f.get("legend_block_id", ""))): str(f.get("figure_id", ""))
        for f in new_figures
    }
    new_ids_set = set(new_ids)
    new_by_number = {
        int(f.get("figure_number")): str(f.get("figure_id"))
        for f in new_figures
        if f.get("figure_number") is not None
    }
    new_by_caption = {
        (int(f.get("figure_number")) if f.get("figure_number") is not None else None, _norm(f.get("text", ""))): str(
            f.get("figure_id")
        )
        for f in new_figures
    }
    mapping = {}
    for anchor, old_id in old["anchors"].items():
        mapped = new_anchors.get(anchor, "")
        if not mapped and old_id in new_ids_set:
            mapped = old_id
        if not mapped:
            old_entry = next(
                (f for f in old.get("entries_detail", []) if str(f.get("figure_id")) == old_id),
                None,
            )
            if old_entry is not None:
                number = old_entry.get("figure_number")
                mapped = new_by_caption.get((number, _norm(old_entry.get("text", ""))), "") or new_by_number.get(
                    int(number) if number is not None else -1, ""
                )
        mapping[old_id] = mapped
    renamed = sorted({(old_id, new_id) for old_id, new_id in mapping.items() if new_id and new_id != old_id})
    unmapped = sorted({old_id for old_id, new_id in mapping.items() if not new_id})
    old_claims = old["claims"]
    new_claims = {
        str(f.get("figure_id", "")): sorted(
            str(a.get("block_id", ""))
            for a in (f.get("matched_assets") or [])
            if a.get("block_id") is not None
        )
        for f in new_figures
    }
    changed_claims = sorted(
        (old_id, old_claims.get(old_id, []), new_id, new_claims.get(new_id, []))
        for old_id, new_id in mapping.items()
        if new_id and old_claims.get(old_id) != new_claims.get(new_id)
    )
    return {
        "old": {"entries": old["entries"], "unique_ids": len(set(old["ids"])), "duplicate_extra": old["duplicate_extra"]},  # noqa: E501
        "new": {"entries": len(new_figures), "unique_ids": len(set(new_ids)), "duplicate_extra": len(new_ids) - len(set(new_ids))},  # noqa: E501
        "mapping": {k: v for k, v in sorted(mapping.items()) if k},
        "renamed": [list(item) for item in renamed],
        "unmapped_old_ids": unmapped,
        "claims_changed": [
            {"old_id": o, "old_assets": oa, "new_id": n, "new_assets": na}
            for o, oa, n, na in changed_claims
        ],
    }


def _missing_embed_reason(old_id: str, old: dict, new_figures: list[dict], new_rows: list[dict]) -> str:
    detail = next(
        (f for f in old.get("entries_detail", []) if str(f.get("figure_id")) == old_id), {}
    )
    if old_id.startswith("figure_reserved") or not old.get("claims", {}).get(old_id):
        return "reserved_or_assetless"
    text = _norm(detail.get("text", ""))
    if text:
        for figure in new_figures:
            other = _norm(figure.get("text", ""))
            if other and (text in other or other in text):
                return "identity_mapping_lost"
        for row in new_rows:
            if str(row.get("role")) in {"figure_caption", "figure_caption_candidate"}:
                other = _norm(row.get("text", ""))
                if other and (text in other or other in text):
                    return "caption_present_unmatched"
    return "caption_absent"


def _delivery_diff(
    paper_dir: Path,
    manifest: dict,
    mapping: dict[str, str],
    old: dict,
    new_figures: list[dict],
    new_rows: list[dict],
) -> dict:
    old_render = set()
    for pattern in (
        "render/figures/*.md",
        "render/tables/*.md",
        "assets/figures/*.jpg",
        "assets/tables/*.jpg",
        "assets/orphans/*.jpg",
    ):
        old_render.update(
            path.relative_to(paper_dir).as_posix() for path in paper_dir.glob(pattern) if path.is_file()
        )
    new_render = set()
    for value in [*manifest.get("render", []), *manifest.get("assets", [])]:
        try:
            new_render.add(Path(value).resolve().relative_to(paper_dir.resolve()).as_posix())
        except (ValueError, OSError):
            new_render.add(str(value))
    fulltext = paper_dir / "fulltext.md"
    embeds = []
    if fulltext.is_file():
        for kind, target in EMBED_RE.findall(fulltext.read_text(encoding="utf-8")):
            object_id = Path(target).stem
            embeds.append(
                {
                    "kind": kind,
                    "old_target": f"render/{kind}/{target}",
                    "new_id": mapping.get(object_id, object_id),
                }
            )
    return {
        "old_render_files": len(old_render),
        "new_render_files": len(new_render),
        "render_added": sorted(new_render - old_render),
        "render_removed": sorted(old_render - new_render),
        "embeds": len(embeds),
        "embeds_retargeted": sum(1 for e in embeds if e["new_id"] != Path(e["old_target"]).stem),
        "embeds_missing_new_id": [
            {
                **e,
                "reason": _missing_embed_reason(
                    Path(e["old_target"]).stem, old, new_figures, new_rows
                ),
            }
            for e in embeds
            if not e["new_id"]
        ],
    }


def _content_diff(paper_dir: Path, rows: list[dict]) -> dict:
    old_rows = _rows(paper_dir / "structure/blocks.structured.jsonl")
    old_roles = Counter(str(r.get("role")) for r in old_rows)
    new_roles = Counter(str(r.get("role")) for r in rows)
    old_body = sum(len(str(r.get("text", ""))) for r in old_rows if r.get("role") == "body_paragraph")
    new_body = sum(len(str(r.get("text", ""))) for r in rows if r.get("role") == "body_paragraph")
    old_text = sum(len(str(r.get("text", ""))) for r in old_rows)
    new_text = sum(len(str(r.get("text", ""))) for r in rows)
    fulltext = paper_dir / "fulltext.md"
    old_chars = len(fulltext.read_text(encoding="utf-8")) if fulltext.is_file() else 0
    return {
        "old_rows": len(old_rows),
        "new_rows": len(rows),
        "role_removed": {k: v - new_roles.get(k, 0) for k, v in old_roles.items() if v > new_roles.get(k, 0)},
        "role_added": {k: v - old_roles.get(k, 0) for k, v in new_roles.items() if v > old_roles.get(k, 0)},
        "old_body_chars": old_body,
        "new_body_chars": new_body,
        "old_text_chars": old_text,
        "new_text_chars": new_text,
        "old_fulltext_chars": old_chars,
    }


def _table_diff(paper_dir: Path, new_tables: list[dict]) -> dict:
    old = _read_json(paper_dir / "structure/table_inventory.json").get("tables", [])
    old_claims = {
        (int(t.get("page", 0) or 0), str(t.get("caption_block_id", ""))): (
            str(t.get("asset_block_id", "")) if t.get("has_asset") else ""
        )
        for t in old
    }
    new_claims = {
        (int(t.get("page", 0) or 0), str(t.get("caption_block_id", ""))): (
            str(t.get("asset_block_id", "")) if t.get("has_asset") else ""
        )
        for t in new_tables
    }
    return {
        "old_tables": len(old),
        "new_tables": len(new_tables),
        "claim_changes": [
            {"page": page, "caption": caption, "old": old_claims.get((page, caption)), "new": new}
            for (page, caption), new in new_claims.items()
            if old_claims.get((page, caption)) != new
        ],
    }


def audit_key(vault: Path, ocr_root: Path, key: str) -> dict:
    paper_dir = ocr_root / key
    old = _old_identity(paper_dir)
    try:
        new = _new_replay(vault, ocr_root, key)
    except Exception as exc:  # noqa: BLE001 — report per paper
        return {"key": key, "error": f"{type(exc).__name__}: {exc}"}
    identity = _identity_diff(old, new["figures"])
    return {
        "key": key,
        "identity": identity,
        "delivery": _delivery_diff(
            paper_dir, new["manifest"], identity["mapping"], old, new["figures"], new["rows"]
        ),
        "tables": _table_diff(paper_dir, new["tables"]),
        "content": _content_diff(paper_dir, new["rows"]),
        "new_manifest": {
            "figures": len(new["manifest"].get("figures", [])),
            "tables": len(new["manifest"].get("tables", [])),
            "orphans": len(new["manifest"].get("orphans", [])),
        },
        "new_orphans": len(new["figure_inventory"].get("unmatched_assets", [])),
    }


def trial_key(vault: Path, ocr_root: Path, key: str, workdir: Path) -> dict:
    """Rebuild one paper in a throwaway vault copy, twice, and check stability."""
    from paperforge.config import bootstrap_config
    from paperforge.pdf_resolver import resolve_source_pdf
    from paperforge.worker.ocr_rebuild import _rebuild_one_paper

    paper = workdir / "vault" / "System" / "PaperForge" / "ocr" / key
    paper.mkdir(parents=True, exist_ok=True)
    (paper / "canonical").mkdir(exist_ok=True)
    (paper / "raw").mkdir(exist_ok=True)
    source = ocr_root / key
    shutil.copy2(source / "canonical/blocks.raw.jsonl", paper / "canonical/blocks.raw.jsonl")
    shutil.copy2(source / "raw/source_metadata.json", paper / "raw/source_metadata.json")
    meta = _read_json(source / "meta.json")
    pdf = resolve_source_pdf(vault, meta.get("source_pdf"))
    meta["source_pdf"] = str(pdf) if pdf is not None else ""
    (paper / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    bootstrap_config(workdir / "vault")

    def snapshot() -> dict:
        digest = {}
        committed = (
            "structure/blocks.structured.jsonl",
            "structure/figure_inventory.json",
            "structure/table_inventory.json",
            "structure/document_structure.json",
            "render/fulltext.md",
            "fulltext.md",
        )
        for relative in committed:
            path = paper / relative
            if path.is_file():
                digest[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        for pattern in (
            "render/figures/*.md",
            "render/tables/*.md",
            "assets/figures/*.jpg",
            "assets/tables/*.jpg",
            "assets/orphans/*.jpg",
        ):
            for path in paper.glob(pattern):
                if path.is_file():
                    digest[path.relative_to(paper).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        return digest

    first = _rebuild_one_paper(workdir / "vault", key)
    snap1 = snapshot()
    second = _rebuild_one_paper(workdir / "vault", key)
    snap2 = snapshot()
    leftovers = [p.name for p in paper.iterdir() if p.name.startswith(".materialization-")]
    return {
        "key": key,
        "first_status": first.get("status"),
        "second_status": second.get("status"),
        "idempotent": snap1 == snap2,
        "files": len(snap2),
        "leftovers": leftovers,
        "has_outlier": [name for name in snap2 if name.endswith(".tmp")],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True)
    parser.add_argument("--ocr-root", default="")
    parser.add_argument("--keys", nargs="*", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--out", required=True)
    parser.add_argument("--trial", action="store_true", help="also rebuild in a throwaway vault")
    parser.add_argument("--workdir", default="")
    args = parser.parse_args()

    vault = Path(args.vault)
    ocr_root = Path(args.ocr_root) if args.ocr_root else vault / "System/PaperForge/ocr"
    keys = args.keys or sorted(
        path.name for path in ocr_root.iterdir() if (path / "meta.json").is_file()
    )
    if args.limit:
        keys = keys[: args.limit]
    report = {"keys": [], "totals": {}}
    for key in keys:
        entry = audit_key(vault, ocr_root, key)
        if args.trial and "error" not in entry:
            work = Path(args.workdir or tempfile.mkdtemp(prefix="pf-migration-trial-")) / key
            entry["trial"] = trial_key(vault, ocr_root, key, work)
        report["keys"].append(entry)
    report["totals"] = {
        "papers": len(report["keys"]),
        "errors": sum(1 for e in report["keys"] if "error" in e),
        "renamed_ids": sum(len(e.get("identity", {}).get("renamed", [])) for e in report["keys"]),
        "claims_changed": sum(len(e.get("identity", {}).get("claims_changed", [])) for e in report["keys"]),
        "embeds_retargeted": sum(e.get("delivery", {}).get("embeds_retargeted", 0) for e in report["keys"]),
        "embeds_missing": sum(len(e.get("delivery", {}).get("embeds_missing_new_id", [])) for e in report["keys"]),
        "trial_idempotent": sum(1 for e in report["keys"] if e.get("trial", {}).get("idempotent")),
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report["totals"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
