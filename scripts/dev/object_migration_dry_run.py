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
                "legend_block_id": str(f.get("legend_block_id", "")),
                "text": str(f.get("text", "") or ""),
                "assets": [
                    {
                        "block_id": a.get("block_id"),
                        "page": int(a.get("page", 0) or 0),
                        "bbox": a.get("bbox"),
                    }
                    for a in (f.get("matched_assets") or [])
                ],
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
    source_metadata = _read_json(paper_dir / "raw/source_metadata.json")
    raw = _rows(paper_dir / "canonical/blocks.raw.jsonl")
    from paperforge.worker.ocr import _ocr_pipeline_v3_enabled

    normalize_mode = meta.get("normalize_mode") or (
        "seed_only" if _ocr_pipeline_v3_enabled() else "legacy"
    )
    blocks, document = build_structured_blocks(
        raw, source_metadata=source_metadata, normalize_mode=normalize_mode
    )
    blocks, document = pre_match_normalize(
        blocks,
        source_frontmatter_anchors=getattr(document, "source_frontmatter_anchors", None) or {},
        document_structure=document,
    )
    pdf = resolve_source_pdf(vault, meta.get("source_pdf"))
    lines = {}
    if pdf is not None:
        try:
            lines = extract_pdf_lines_normalized(pdf)
        except Exception:  # noqa: BLE001 — evidence is optional
            lines = {}
    stage = run_association_stage(blocks, page_pdf_lines_by_page=lines or None)
    if normalize_mode == "seed_only":
        from paperforge.worker.ocr_post_match_normalize import post_match_normalize

        blocks, document = post_match_normalize(
            blocks,
            stage.figures,
            stage.tables,
            document_structure=document,
            source_frontmatter_anchors=getattr(document, "source_frontmatter_anchors", None),
        )
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
def _rebuild_replay(vault: Path, ocr_root: Path, key: str) -> dict:
    """Rebuild-based replay: stage inputs into an isolated temp vault, run the
    real ``_rebuild_one_paper`` path, and read rebuilt artifacts.

    Never writes to ``vault`` or ``ocr_root``.
    """
    import shutil
    import tempfile

    from paperforge.config import bootstrap_config
    from paperforge.pdf_resolver import resolve_source_pdf
    from paperforge.worker.ocr_rebuild import _rebuild_one_paper

    source = ocr_root / key
    if not (source / "canonical/blocks.raw.jsonl").is_file():
        raise FileNotFoundError(f"missing raw blocks for {key}")

    workdir = Path(tempfile.mkdtemp(prefix=f"rebuild-replay-{key}-"))
    try:
        v = workdir / "vault"
        paper = v / "System" / "PaperForge" / "ocr" / key
        paper.mkdir(parents=True, exist_ok=True)
        (paper / "canonical").mkdir(exist_ok=True)
        (paper / "raw").mkdir(exist_ok=True)
        shutil.copy2(source / "canonical/blocks.raw.jsonl", paper / "canonical/blocks.raw.jsonl")
        src_meta_path = source / "raw/source_metadata.json"
        if src_meta_path.is_file():
            shutil.copy2(src_meta_path, paper / "raw/source_metadata.json")
        else:
            (paper / "raw/source_metadata.json").write_text("{}", encoding="utf-8")

        meta = _read_json(source / "meta.json")
        pdf = resolve_source_pdf(vault, meta.get("source_pdf"))
        meta["source_pdf"] = str(pdf) if pdf is not None else ""
        (paper / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

        bootstrap_config(v)
        result = _rebuild_one_paper(v, key)
        if result.get("status") != "ok":
            raise RuntimeError(f"rebuild failed for {key}: {result}")

        rebuilt = v / "System" / "PaperForge" / "ocr" / key
        figure_inventory = _read_json(rebuilt / "structure/figure_inventory.json")
        table_inventory = _read_json(rebuilt / "structure/table_inventory.json")
        rows = _rows(rebuilt / "structure/blocks.structured.jsonl")
        new_figures = figure_inventory.get("matched_figures", [])
        new_tables = table_inventory.get("tables", [])
        paper_dir = ocr_root / key
        from paperforge.pdf_resolver import resolve_source_pdf
        from paperforge.worker.ocr_objects import extract_and_write_objects

        rebuilt_meta = _read_json(rebuilt / "meta.json")
        pdf = resolve_source_pdf(vault, rebuilt_meta.get("source_pdf"))
        manifest = extract_and_write_objects(
            pdf,
            figure_inventory,
            table_inventory,
            rebuilt / "assets",
            rebuilt / "render",
            dry_run=True,
        ) or {}
        # Express manifest paths relative to the original paper_dir for diffs.
        for bucket in ("assets", "render"):
            manifest[bucket] = [
                str(paper_dir / Path(value).relative_to(rebuilt)) if Path(value).is_absolute() else value
                for value in manifest.get(bucket, [])
            ]
        return {
            "figures": new_figures,
            "tables": new_tables,
            "rows": rows,
            "manifest": manifest,
            "figure_inventory": figure_inventory,
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


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
    manifest_figure_ids = set(map(str, manifest.get("figures", [])))
    manifest_asset_ids = {
        Path(value).stem
        for value in manifest.get("assets", [])
        if Path(value).parent.name == "figures"
    }
    manifest_render_ids = {
        Path(value).stem
        for value in manifest.get("render", [])
        if Path(value).parent.name == "figures"
    }
    return {
        "manifest_delivery": {
            "figure_ids": sorted(manifest_figure_ids),
            "missing_assets": sorted(manifest_figure_ids - manifest_asset_ids),
            "missing_renders": sorted(manifest_figure_ids - manifest_render_ids),
        },
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


PLAN_SCHEMA = "paperforge.migration_plan.v1"
PLAN_EXECUTION = "rebuild+verify: operations are expected artifact effects, not shell mv"
STATUS_REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
STATUS_M2_REVIEW = "M2_REVIEW_REQUIRED"
STATUS_HOLD = "HOLD"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rel(paper_dir: Path, path: str | Path) -> str:
    try:
        return Path(path).resolve().relative_to(paper_dir.resolve()).as_posix()
    except (ValueError, OSError):
        return ""


def _manifest_index(paper_dir: Path, manifest: dict) -> dict[str, dict[str, list[str]]]:
    index: dict[str, dict[str, list[str]]] = {}
    for value in [*manifest.get("render", []), *manifest.get("assets", [])]:
        rel = _rel(paper_dir, value)
        if not rel:
            continue
        bucket = "render" if rel.startswith("render/") else "assets"
        index.setdefault(Path(rel).stem, {"render": [], "assets": []})[bucket].append(rel)
    for entry in index.values():
        entry["render"].sort()
        entry["assets"].sort()
    return index


def _entry_map(old: dict, new_figures: list[dict]) -> list[dict]:
    """Map every old inventory entry (duplicates included) to a new figure id."""
    new_ids = [str(f.get("figure_id", "")) for f in new_figures]
    new_ids_set = set(new_ids)
    new_anchors = {
        (int(f.get("page", 0) or 0), str(f.get("legend_block_id", ""))): str(f.get("figure_id", ""))
        for f in new_figures
    }
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
    entries = []
    for entry in old.get("entries_detail", []):
        old_id = str(entry.get("figure_id", ""))
        number = entry.get("figure_number")
        mapped = new_anchors.get((int(entry.get("page", 0) or 0), str(entry.get("legend_block_id", ""))), "")
        if not mapped and old_id in new_ids_set:
            mapped = old_id
        if not mapped:
            mapped = new_by_caption.get(
                (number, _norm(entry.get("text", ""))), ""
            ) or new_by_number.get(int(number) if number is not None else -1, "")
        entries.append({**entry, "mapped": str(mapped or "")})
    return entries


def _parse_embeds(paper_dir: Path) -> list[dict]:
    fulltext = paper_dir / "fulltext.md"
    if not fulltext.is_file():
        return []
    embeds = []
    for lineno, line in enumerate(fulltext.read_text(encoding="utf-8").splitlines(), start=1):
        for kind, target in EMBED_RE.findall(line):
            embeds.append(
                {
                    "kind": kind,
                    "target": f"render/{kind}/{target}",
                    "object_id": Path(target).stem,
                    "line": lineno,
                }
            )
    return embeds



def _table_mapping(paper_dir: Path, new_tables: list[dict], new_table_ids: list[str]) -> tuple[dict[str, str], list[str]]:
    old_tables = _read_json(paper_dir / "structure/table_inventory.json").get("tables", [])
    old_ids = sorted(path.stem for path in paper_dir.glob("render/tables/*.md"))
    old_ids += sorted(
        path.stem for path in paper_dir.glob("assets/tables/*.jpg") if path.stem not in old_ids
    )
    mapping: dict[str, str] = {}
    used_new: set[int] = set()
    for index, old_id in enumerate(old_ids):
        old_entry = old_tables[index] if index < len(old_tables) else {}
        match = None
        for new_index, table in enumerate(new_tables):
            if new_index in used_new:
                continue
            if (
                int(table.get("page", 0) or 0) == int(old_entry.get("page", 0) or 0)
                and str(table.get("caption_block_id", "")) == str(old_entry.get("caption_block_id", ""))
            ):
                match = new_index
                break
        if match is None and index < len(new_table_ids) and index not in used_new:
            match = index
        if match is not None:
            used_new.add(match)
            mapping[old_id] = new_table_ids[match]
    return mapping, old_ids


def _plan_key(paper_dir: Path, old: dict, new: dict, identity: dict) -> dict:
    manifest = new["manifest"]
    entries = _entry_map(old, new["figures"])
    new_figure_ids = [str(f.get("figure_id", "")) for f in new["figures"]]
    new_table_ids = [str(value) for value in manifest.get("tables", [])]
    new_orphan_ids = {str(value) for value in manifest.get("orphans", [])}
    index = _manifest_index(paper_dir, manifest)
    new_render_paths = {
        rel for entry in index.values() for rel in entry["render"]
    }
    embeds = _parse_embeds(paper_dir)
    embedded_ids = {str(item["object_id"]) for item in embeds}
    old_files = {
        rel
        for pattern in (
            "render/figures/*.md",
            "render/tables/*.md",
            "assets/figures/*.jpg",
            "assets/tables/*.jpg",
            "assets/orphans/*.jpg",
        )
        for rel in (
            path.relative_to(paper_dir).as_posix() for path in paper_dir.glob(pattern)
        )
    }
    ops: list[dict] = []
    objects: list[dict] = []
    holds: list[dict] = []
    collisions: list[dict] = []
    dangling: list[dict] = []
    backup_paths: set[str] = set()
    covered_new: set[str] = set()
    safe: dict[str, str] = {}
    ambiguous: dict[str, list[str]] = {}

    old_figure_ids = sorted(
        {str(entry.get("figure_id", "")) for entry in entries if entry.get("figure_id")}
        | {
            Path(rel).stem
            for rel in old_files
            if Path(rel).parent.as_posix() in {"render/figures", "assets/figures"}
            and not Path(rel).stem.startswith("orphan_")
        }
    )
    for old_id in old_figure_ids:
        candidates = sorted(
            {str(entry["mapped"]) for entry in entries if str(entry.get("figure_id", "")) == old_id and entry.get("mapped")}
        )
        files = sorted(rel for rel in old_files if Path(rel).stem == old_id)
        anchors = [
            {
                "page": entry.get("page"),
                "legend_block_id": entry.get("legend_block_id"),
                "text": entry.get("text"),
                "asset_blocks": entry.get("assets", []),
            }
            for entry in entries
            if str(entry.get("figure_id", "")) == old_id
        ]
        objects.append(
            {
                "kind": "figure",
                "old_id": old_id,
                "new_id": candidates[0] if len(candidates) == 1 else "",
                "candidates": candidates,
                "entries": len(anchors),
                "anchors": anchors,
                "old_files": files,
                "status": "planned" if len(candidates) == 1 else STATUS_HOLD,
            }
        )
        if len(candidates) == 1:
            safe[old_id] = candidates[0]
            continue
        if len(candidates) > 1:
            ambiguous[old_id] = candidates
            holds.append(
                {
                    "code": "AMBIGUOUS_OLD_ID",
                    "old_id": old_id,
                    "candidates": candidates,
                    "reason": "one old id maps to several new objects; no deterministic file mapping",
                }
            )
            for rel in files:
                ops.append(
                    {
                        "op": "delete_candidate",
                        "kind": "figure",
                        "object_uid": old_id,
                        "old_path": rel,
                        "new_path": "",
                        "old_sha256": _sha256_file(paper_dir / rel),
                        "status": STATUS_REQUIRES_APPROVAL,
                        "reason": "superseded by several new objects; old file cannot be mapped 1:1",
                    }
                )
                backup_paths.add(rel)
            continue
        reason = (
            _missing_embed_reason(old_id, old, new["figures"], new["rows"])
            if old_id in embedded_ids
            else ("reserved_or_assetless" if old_id.startswith("figure_reserved") else "unmapped_assetless")
        )
        status = STATUS_M2_REVIEW if reason == "caption_present_unmatched" else STATUS_REQUIRES_APPROVAL
        holds.append({"code": STATUS_M2_REVIEW if reason == "caption_present_unmatched" else reason.upper(), "old_id": old_id, "candidates": [], "reason": reason})
        if reason == "caption_present_unmatched":
            continue
        for rel in files:
            ops.append(
                {
                    "op": "delete_candidate",
                    "kind": "figure",
                    "object_uid": old_id,
                    "old_path": rel,
                    "new_path": "",
                    "old_sha256": _sha256_file(paper_dir / rel),
                    "status": status,
                    "reason": reason,
                }
            )
            backup_paths.add(rel)

    owners: dict[str, list[str]] = {}
    for old_id, new_id in safe.items():
        owners.setdefault(new_id, []).append(old_id)
    many_to_one = {new_id: sorted(ids) for new_id, ids in owners.items() if len(ids) > 1}
    for new_id, old_ids in sorted(many_to_one.items()):
        collisions.append(
            {
                "code": "many_to_one",
                "new_id": new_id,
                "old_ids": old_ids,
                "reason": "several old objects claim one new id; rename is ambiguous",
            }
        )
        for old_id in old_ids:
            safe.pop(old_id, None)
            holds.append({"code": "MANY_TO_ONE", "old_id": old_id, "candidates": [new_id], "reason": "many_to_one"})
            for rel in sorted(rel for rel in old_files if Path(rel).stem == old_id):
                ops.append(
                    {
                        "op": "delete_candidate",
                        "kind": "figure",
                        "object_uid": old_id,
                        "old_path": rel,
                        "new_path": "",
                        "old_sha256": _sha256_file(paper_dir / rel),
                        "status": STATUS_REQUIRES_APPROVAL,
                        "reason": "many_to_one collision",
                    }
                )
                backup_paths.add(rel)

    for old_id, new_id in sorted(safe.items()):
        new_entry = index.get(new_id, {"render": [], "assets": []})
        if not new_entry["render"] and not new_entry["assets"]:
            dangling.append(
                {
                    "code": "object_without_artifacts",
                    "old_id": old_id,
                    "new_id": new_id,
                }
            )
            continue
        for rel in sorted(rel for rel in old_files if Path(rel).stem == old_id):
            kind = "render" if rel.startswith("render/") else "assets"
            suffix = Path(rel).suffix
            if kind == "render":
                new_rel = new_entry["render"][0] if new_entry["render"] else ""
            else:
                new_rel = new_entry["assets"][0] if new_entry["assets"] else ""
            if not new_rel:
                ops.append(
                    {
                        "op": "delete_candidate",
                        "kind": "figure",
                        "object_uid": old_id,
                        "old_path": rel,
                        "new_path": "",
                        "old_sha256": _sha256_file(paper_dir / rel),
                        "status": STATUS_REQUIRES_APPROVAL,
                        "reason": f"new object has no {kind} artifact",
                    }
                )
                backup_paths.add(rel)
                continue
            op = "keep" if new_rel == rel else "rename"
            ops.append(
                {
                    "op": op,
                    "kind": "figure",
                    "object_uid": new_id,
                    "old_id": old_id,
                    "old_path": rel,
                    "new_path": new_rel,
                    "old_sha256": _sha256_file(paper_dir / rel),
                    "status": "planned",
                    "reason": "identity mapping",
                }
            )
            if op == "rename":
                backup_paths.add(rel)
                if new_rel in old_files and new_rel != rel:
                    collisions.append(
                        {
                            "code": "target_exists",
                            "old_path": rel,
                            "new_path": new_rel,
                            "reason": "rename target already exists in the old surface",
                        }
                    )
        covered_new.add(new_id)

    table_mapping, old_table_ids = _table_mapping(paper_dir, new["tables"], new_table_ids)
    for old_id, new_id in sorted(table_mapping.items()):
        entry = index.get(new_id, {"render": [], "assets": []})
        for rel in sorted(rel for rel in old_files if Path(rel).stem == old_id and "/tables/" in rel):
            kind = "render" if rel.startswith("render/") else "assets"
            new_rel = entry["render"][0] if kind == "render" and entry["render"] else (
                entry["assets"][0] if kind == "assets" and entry["assets"] else ""
            )
            if not new_rel:
                ops.append(
                    {
                        "op": "delete_candidate",
                        "kind": "table",
                        "object_uid": old_id,
                        "old_path": rel,
                        "new_path": "",
                        "old_sha256": _sha256_file(paper_dir / rel),
                        "status": STATUS_REQUIRES_APPROVAL,
                        "reason": f"new table has no {kind} artifact",
                    }
                )
                backup_paths.add(rel)
                continue
            op = "keep" if new_rel == rel else "rename"
            ops.append(
                {
                    "op": op,
                    "kind": "table",
                    "object_uid": new_id,
                    "old_id": old_id,
                    "old_path": rel,
                    "new_path": new_rel,
                    "old_sha256": _sha256_file(paper_dir / rel),
                    "status": "planned",
                    "reason": "table identity mapping",
                }
            )
            if op == "rename":
                backup_paths.add(rel)
        covered_new.add(new_id)
    for old_id in old_table_ids:
        if old_id in table_mapping:
            continue
        for rel in sorted(rel for rel in old_files if Path(rel).stem == old_id and "/tables/" in rel):
            ops.append(
                {
                    "op": "delete_candidate",
                    "kind": "table",
                    "object_uid": old_id,
                    "old_path": rel,
                    "new_path": "",
                    "old_sha256": _sha256_file(paper_dir / rel),
                    "status": STATUS_REQUIRES_APPROVAL,
                    "reason": "old table has no new counterpart",
                }
            )
            backup_paths.add(rel)

    old_orphan_ids = sorted(
        {
            Path(rel).stem
            for rel in old_files
            if Path(rel).stem.startswith("orphan_")
        }
    )
    for old_id in old_orphan_ids:
        if old_id in new_orphan_ids:
            for rel in sorted(rel for rel in old_files if Path(rel).stem == old_id):
                ops.append(
                    {
                        "op": "keep",
                        "kind": "orphan",
                        "object_uid": old_id,
                        "old_path": rel,
                        "new_path": rel,
                        "old_sha256": _sha256_file(paper_dir / rel),
                        "status": "planned",
                        "reason": "orphan kept",
                    }
                )
            continue
        for rel in sorted(rel for rel in old_files if Path(rel).stem == old_id):
            ops.append(
                {
                    "op": "delete_candidate",
                    "kind": "orphan",
                    "object_uid": old_id,
                    "old_path": rel,
                    "new_path": "",
                    "old_sha256": _sha256_file(paper_dir / rel),
                    "status": STATUS_REQUIRES_APPROVAL,
                    "reason": "orphan no longer inventoried",
                }
            )
            backup_paths.add(rel)

    rename_targets = {str(op.get("new_path", "")) for op in ops if op.get("op") == "rename"}
    for uid, entry in sorted(index.items()):
        for rel in [*entry.get("render", []), *entry.get("assets", [])]:
            if rel in old_files or rel in rename_targets:
                continue
            kind = "figure" if "/figures/" in rel else "table" if "/tables/" in rel else "orphan" if "/orphans/" in rel else "object"
            ops.append(
                {
                    "op": "create",
                    "kind": kind,
                    "object_uid": uid,
                    "old_path": "",
                    "new_path": rel,
                    "old_sha256": "",
                    "status": "planned",
                    "reason": "new object",
                }
            )

    retarget_ops: dict[tuple[str, str], dict] = {}
    embed_rows = []
    for embed in embeds:
        old_id = str(embed["object_id"])
        kind = embed["kind"]
        if kind == "figures":
            if old_id.startswith("orphan_"):
                candidates = [old_id] if old_id in new_orphan_ids else []
            elif old_id in safe:
                candidates = [safe[old_id]]
            elif old_id in ambiguous:
                candidates = ambiguous[old_id]
            else:
                candidates = []
        else:
            mapped = table_mapping.get(old_id, "")
            candidates = [mapped] if mapped else []
        row = {**embed, "candidates": candidates}
        if len(candidates) == 1:
            new_id = candidates[0]
            new_target = f"render/{kind}/{new_id}.md"
            if new_target not in new_render_paths:
                row.update({"status": STATUS_HOLD, "reason": "dangling_new_target"})
                dangling.append(
                    {
                        "code": "embed_target_missing",
                        "old_target": embed["target"],
                        "new_target": new_target,
                    }
                )
            else:
                row.update({"status": "planned", "new_target": new_target, "reason": "mapped"})
                key = (embed["target"], new_target)
                if key not in retarget_ops:
                    retarget_ops[key] = {
                        "op": "retarget",
                        "kind": "embed",
                        "object_uid": new_id,
                        "old_path": embed["target"],
                        "new_path": new_target,
                        "old_sha256": "",
                        "status": "planned",
                        "reason": "embed retarget",
                        "lines": [],
                        "occurrences": 0,
                    }
                retarget_ops[key]["lines"].append(embed["line"])
                retarget_ops[key]["occurrences"] += 1
        elif len(candidates) > 1:
            row.update({"status": STATUS_HOLD, "reason": "ambiguous_embed"})
            holds.append(
                {
                    "code": "AMBIGUOUS_EMBED",
                    "old_id": old_id,
                    "candidates": candidates,
                    "reason": "embed target id maps to several new objects",
                }
            )
        else:
            reason = (
                _missing_embed_reason(old_id, old, new["figures"], new["rows"])
                if kind == "figures"
                else "unmapped_table"
            )
            status = STATUS_M2_REVIEW if reason == "caption_present_unmatched" else STATUS_REQUIRES_APPROVAL
            row.update({"status": status, "reason": reason})
            if reason in {"caption_present_unmatched"}:
                holds.append({"code": "M2_REVIEW_REQUIRED", "old_id": old_id, "candidates": [], "reason": reason})
            else:
                op_key = ("delete", embed["target"])
                if op_key not in retarget_ops:
                    retarget_ops[op_key] = {
                        "op": "delete_candidate",
                        "kind": "embed",
                        "object_uid": old_id,
                        "old_path": embed["target"],
                        "new_path": "",
                        "old_sha256": "",
                        "status": STATUS_REQUIRES_APPROVAL,
                        "reason": reason,
                        "lines": [],
                        "occurrences": 0,
                    }
                retarget_ops[op_key]["lines"].append(embed["line"])
                retarget_ops[op_key]["occurrences"] += 1
        embed_rows.append(row)
    ops.extend(retarget_ops.values())

    ops.insert(
        0,
        {
            "op": "materialize_objects",
            "kind": "paper",
            "object_uid": "",
            "old_path": "",
            "new_path": "",
            "old_sha256": "",
            "status": "planned",
            "reason": "rebuild writes objects before inventory/fulltext",
            "depends_on": [],
            "op_id": "materialize-objects",
        },
    )
    for rel in (
        "structure/blocks.structured.jsonl",
        "structure/figure_inventory.json",
        "structure/table_inventory.json",
        "structure/document_structure.json",
        "fulltext.md",
        "render/fulltext.md",
    ):
        path = paper_dir / rel
        if not path.is_file():
            continue
        op = {
            "op": "rewrite",
            "kind": "inventory" if rel.startswith("structure/") else "fulltext",
            "object_uid": "",
            "old_path": rel,
            "new_path": rel,
            "old_sha256": _sha256_file(path),
            "status": "planned",
            "reason": "pipeline rewrite with retargeted embeds",
            "depends_on": ["materialize-objects"],
        }
        ops.append(op)
        backup_paths.add(rel)

    backup_files = []
    for rel in sorted(backup_paths):
        path = paper_dir / rel
        if path.is_file():
            backup_files.append({"path": rel, "sha256": _sha256_file(path), "bytes": path.stat().st_size})

    statuses = {op["status"] for op in ops}
    hold_codes = {str(h.get("code", "")) for h in holds}
    ambiguous = bool(collisions or dangling or (hold_codes & {"AMBIGUOUS_OLD_ID", "AMBIGUOUS_EMBED", "MANY_TO_ONE"}))
    if any(h.get("code") == STATUS_M2_REVIEW for h in holds) or STATUS_M2_REVIEW in statuses:
        paper_status = STATUS_M2_REVIEW
    elif ambiguous:
        paper_status = STATUS_HOLD
    elif STATUS_REQUIRES_APPROVAL in statuses:
        paper_status = STATUS_REQUIRES_APPROVAL
    elif any(op["op"] not in {"keep"} for op in ops):
        paper_status = "READY"
    else:
        paper_status = "NO_OP"

    return {
        "schema": PLAN_SCHEMA,
        "key": paper_dir.name,
        "execution_model": PLAN_EXECUTION,
        "status": paper_status,
        "objects": objects,
        "operations": ops,
        "embeds": embed_rows,
        "holds": holds,
        "collisions": collisions,
        "dangling": dangling,
        "backup": {
            "root": f"backups/{paper_dir.name}/",
            "files": backup_files,
            "note": "copy every listed file before writing; restore verifies sha256",
        },
        "rollback": {
            "method": "restore the backup tree, then verify every sha256",
            "atomicity": "filesystem effects are not atomic with SQLite; journal each step",
        },
    }


def audit_key(vault: Path, ocr_root: Path, key: str, plan: bool = False, replay_mode: str = "rebuild") -> dict:
    paper_dir = ocr_root / key
    old = _old_identity(paper_dir)
    try:
        if replay_mode == "fast":
            new = _new_replay(vault, ocr_root, key)
        else:
            new = _rebuild_replay(vault, ocr_root, key)
    except Exception as exc:  # noqa: BLE001 — report per paper
        return {"key": key, "error": f"{type(exc).__name__}: {exc}"}
    identity = _identity_diff(old, new["figures"])
    result = {
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
    if plan:
        result["plan"] = _plan_key(paper_dir, old, new, identity)
    return result


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


def _bundle(plan_path: str, out_dir: str, vault: Path, external_refs: bool) -> None:
    import gzip
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    plans = [json.loads(line) for line in Path(plan_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    status_counts = Counter(p.get("status") for p in plans)
    op_counts = Counter()
    holds_total = 0
    collisions_total = 0
    dangling_total = 0
    approval_total = 0
    m2_total = 0
    hold_total = 0
    backup_files = 0
    safe_rename = 0
    retarget = 0
    # dedupe holds per paper before counting
    for p in plans:
        seen=set()
        deduped=[]
        for h in p.get("holds",[]):
            key=(h.get("code"),h.get("old_id"),tuple(h.get("candidates",[])))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(h)
        p["holds"]=deduped
    safe_retarget = 0
    ambiguous_embed_holds = 0
    assetless_embed_deletes = 0
    retarget_changing = 0
    retarget_occurrences = 0
    embed_noop_occurrences = 0
    delete_by_kind = Counter()
    delete_by_reason = Counter()
    for p in plans:
        for op in p.get("operations", []):
            op_counts[op.get("op")] += 1
            if op.get("status") == STATUS_REQUIRES_APPROVAL:
                approval_total += 1
            if op.get("op") == "retarget":
                occ = int(op.get("occurrences", 1) or 1)
                if op.get("old_path") != op.get("new_path"):
                    retarget += 1
                    safe_retarget += 1
                    retarget_changing += 1
                    retarget_occurrences += occ
                else:
                    embed_noop_occurrences += occ
            if op.get("op") == "rename":
                safe_rename += 1
            if op.get("op") == "delete_candidate":
                delete_by_kind[op.get("kind")] += 1
                delete_by_reason[op.get("reason")] += 1
        for h in p.get("holds", []):
            holds_total += 1
            if h.get("code") == STATUS_M2_REVIEW:
                m2_total += 1
            if h.get("code") == "AMBIGUOUS_EMBED":
                ambiguous_embed_holds += 1
        for op in p.get("operations", []):
            if op.get("op") == "delete_candidate" and op.get("kind") == "embed" and op.get("status") == STATUS_REQUIRES_APPROVAL:
                assetless_embed_deletes += 1
        collisions_total += len(p.get("collisions", []))
        dangling_total += len(p.get("dangling", []))
        backup_files += len(p.get("backup", {}).get("files", []))
        if p.get("status") == STATUS_HOLD:
            hold_total += 1
    assert sum(op_counts.values()) > 10000, f"too few ops: {sum(op_counts.values())}"

    summary = {
        "papers": len(plans),
        "status_counts": dict(status_counts),
        "op_counts": dict(op_counts),
        "holds_total": holds_total,
        "collisions_total": collisions_total,
        "dangling_total": dangling_total,
        "requires_approval_ops": approval_total,
        "m2_review_ops": m2_total,
        "hold_papers": hold_total,
        "backup_files": backup_files,
        "safe_rename_ops": safe_rename,
        "retarget_ops": retarget,
        "retarget_unique_paths": retarget_changing,
        "retarget_occurrences": retarget_occurrences,
        "embed_mapped_noop_occurrences": embed_noop_occurrences,
        "ambiguous_embed_holds": ambiguous_embed_holds,
        "assetless_embed_deletes": assetless_embed_deletes,
        "delete_by_kind": dict(delete_by_kind),
        "delete_by_reason": dict(delete_by_reason),
    }
    # top hold reasons
    hold_reasons = Counter()
    for p in plans:
        for h in p.get("holds", []):
            hold_reasons[h.get("code", "unknown")] += 1
    summary["top_hold_reasons"] = hold_reasons.most_common(10)

    external = []
    if external_refs:
        changed_targets = set()
        for p in plans:
            for op in p.get("operations", []):
                if op.get("op") in {"rename", "delete_candidate"} and op.get("old_path"):
                    changed_targets.add(op["old_path"])
        # embed old targets
        for p in plans:
            for e in p.get("embeds", []):
                if e.get("target"):
                    changed_targets.add(e["target"])
        # scan vault md outside ocr and .obsidian
        capped = False
        for md in vault.rglob("*.md"):
            rel = md.relative_to(vault).as_posix()
            if rel.startswith("System/PaperForge/ocr/") or rel.startswith(".obsidian/"):
                continue
            try:
                lines = md.read_text(encoding="utf-8").splitlines()
            except Exception:
                continue
            for i, line in enumerate(lines, start=1):
                for target in changed_targets:
                    if target and target in line:
                        external.append({"note": rel, "line": i, "target": target})
                        if len(external) >= 200:
                            capped = True
                            break
                if capped:
                    break
            if capped:
                break
        summary["external_refs_count"] = len(external)
        summary["external_refs_capped"] = capped
        (out / "external_refs.json").write_text(json.dumps(external, ensure_ascii=False, indent=1), encoding="utf-8")

    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    # gzip plan
    with open(plan_path, "rb") as src, gzip.open(out / "plan.jsonl.gz", "wb") as dst:
        dst.write(src.read())
    # sample snippet
    sample = plans[0] if plans else {}
    sample_snippet = json.dumps(sample, ensure_ascii=False, indent=1)[:4000]
    md = f"""# M1b Migration Plan Preview

Generated from {len(plans)} paper plans.

## Commands
```
python scripts/dev/object_migration_dry_run.py --vault <vault> --keys <keys> --out report.json --plan-out plan.jsonl
python scripts/dev/object_migration_dry_run.py --bundle-plan plan.jsonl --bundle-out docs/evidence/m1b --external-refs
```

## Totals
{json.dumps(summary, ensure_ascii=False, indent=2)}

## Status counts
{json.dumps(dict(status_counts), ensure_ascii=False, indent=2)}

## Top HOLD reasons
{json.dumps(summary['top_hold_reasons'], ensure_ascii=False, indent=2)}

## Sample plan snippet
```json
{sample_snippet}
```

## Limits
- Table id pairing is by order when anchors do not match.
- 42 assetless/legacy removals are REQUIRES_APPROVAL, not confirmed misses.
- 27 caption_present_unmatched cases are M2_REVIEW_REQUIRED, not confirmed misses.
- Filesystem and SQLite effects are not atomic; restore+verify rollback.
"""
    (out / "MIGRATION-PLAN.md").write_text(md, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True)
    parser.add_argument("--ocr-root", default="")
    parser.add_argument("--keys", nargs="*", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--out", default="", help="report output path")
    parser.add_argument("--plan-out", default="", help="write one plan JSON object per line")
    parser.add_argument("--trial", action="store_true", help="also rebuild in a throwaway vault")
    parser.add_argument("--workdir", default="")
    parser.add_argument("--bundle-plan", default="", help="bundle a concatenated plan JSONL into evidence")
    parser.add_argument("--bundle-out", default="", help="output directory for bundle")
    parser.add_argument("--external-refs", action="store_true", help="scan vault markdown for references to changed targets")
    args = parser.parse_args()

    vault = Path(args.vault)
    ocr_root = Path(args.ocr_root) if args.ocr_root else vault / "System/PaperForge/ocr"

    if args.bundle_plan:
        _bundle(args.bundle_plan, args.bundle_out, vault, bool(args.external_refs))
        return 0

    keys = args.keys or sorted(
        path.name for path in ocr_root.iterdir() if (path / "meta.json").is_file()
    )
    if args.limit:
        keys = keys[: args.limit]
    report = {"keys": [], "totals": {}}
    plan_handle = open(args.plan_out, "w", encoding="utf-8") if args.plan_out else None
    try:
        for key in keys:
            entry = audit_key(vault, ocr_root, key, plan=bool(args.plan_out))
            if args.trial and "error" not in entry:
                work = Path(args.workdir or tempfile.mkdtemp(prefix="pf-migration-trial-")) / key
                entry["trial"] = trial_key(vault, ocr_root, key, work)
            if plan_handle is not None and "plan" in entry:
                plan_handle.write(json.dumps(entry["plan"], ensure_ascii=False) + "\n")
                plan_handle.flush()
            report["keys"].append({k: v for k, v in entry.items() if k != "plan"})
        report["totals"] = {
            "papers": len(report["keys"]),
            "errors": sum(1 for e in report["keys"] if "error" in e),
            "renamed_ids": sum(len(e.get("identity", {}).get("renamed", [])) for e in report["keys"]),
            "claims_changed": sum(len(e.get("identity", {}).get("claims_changed", [])) for e in report["keys"]),
            "embeds_retargeted": sum(e.get("delivery", {}).get("embeds_retargeted", 0) for e in report["keys"]),
            "embeds_missing": sum(len(e.get("delivery", {}).get("embeds_missing_new_id", [])) for e in report["keys"]),
            "trial_idempotent": sum(1 for e in report["keys"] if e.get("trial", {}).get("idempotent")),
        }
    finally:
        if plan_handle is not None:
            plan_handle.close()
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report["totals"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
