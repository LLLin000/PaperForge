"""Read-only per-paper end-to-end diagnostic inspection command."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from paperforge import __version__ as PF_VERSION
from paperforge.config import ConfigError, load_config, paperforge_paths
from paperforge.core.errors import ErrorCode
from paperforge.core.io import read_json
from paperforge.core.result import PFError, PFResult
from paperforge.memory.builder import compute_hash
from paperforge.memory.db import get_memory_db_path
from paperforge.memory.query import lookup_paper
from paperforge.memory.schema import CURRENT_SCHEMA_VERSION, get_schema_version
from paperforge.pdf_resolver import resolve_source_pdf
from paperforge.worker.asset_index import read_index
from paperforge.worker.ocr_artifacts import artifact_paths_for_root
from paperforge.worker.ocr_hash import compute_ocr_result_hash
from paperforge.worker.ocr_versions import OCR_PIPELINE_VERSION


def _safe_read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = read_json(path)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _load_index_items(vault: Path) -> list[dict[str, Any]]:
    raw = read_index(vault)
    if raw is None:
        return []
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        items = raw.get("items") or []
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return []


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table', 'view') AND name = ? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _open_readonly_db(db_path: Path) -> tuple[sqlite3.Connection | None, bool]:
    if not db_path.is_file():
        return None, False
    try:
        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn, False
    except sqlite3.Error:
        return None, True


def _resolve_vault_context(vault: Path) -> tuple[Path, Path, str | None]:
    from paperforge.config import fallback_paperforge_dir

    try:
        paths = paperforge_paths(vault)
        ocr_root = Path(paths["ocr"])
    except ConfigError:
        ocr_root = fallback_paperforge_dir(vault) / "ocr"

    try:
        db_path = get_memory_db_path(vault)
    except (ConfigError, FileNotFoundError):
        db_path = fallback_paperforge_dir(vault) / "indexes" / "paperforge.db"

    configured_model: str | None = None
    try:
        snap = load_config(vault)
        val = snap.values.get("vector_db_api_model")
        if val is not None and val.value:
            configured_model = str(val.value)
    except ConfigError:
        configured_model = None

    return ocr_root, db_path, configured_model


def _entry_key(entry: dict[str, Any]) -> str:
    return str(entry.get("zotero_key") or entry.get("key") or "").strip()


def _candidate_summary(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "zotero_key": _entry_key(entry),
        "title": entry.get("title") or "",
        "year": entry.get("year") or "",
        "citation_key": entry.get("citation_key") or "",
        "lifecycle": entry.get("lifecycle") or "",
    }


def _match_index_entry(
    items: list[dict[str, Any]], query: str
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    q_norm = query.strip().lower()
    if not q_norm:
        return None, []

    for field in ("zotero_key", "key", "citation_key", "doi"):
        exact = [
            item
            for item in items
            if str(item.get(field) or "").strip().lower() == q_norm
        ]
        if len(exact) == 1:
            return exact[0], []
        if len(exact) > 1:
            return None, exact

    title_matches = [
        item for item in items if q_norm in str(item.get("title") or "").lower()
    ]
    if len(title_matches) == 1:
        return title_matches[0], []
    if len(title_matches) > 1:
        return None, title_matches

    return None, []


def _read_pdf_page_count(pdf_path: Path | None) -> int | None:
    if pdf_path is None or not pdf_path.is_file():
        return None
    try:
        import pymupdf

        with pymupdf.open(str(pdf_path)) as doc:
            return len(doc)
    except Exception:
        return None


def _count_rows(
    conn: sqlite3.Connection | None, table_name: str, paper_id: str
) -> int:
    if conn is None or not _table_exists(conn, table_name):
        return 0
    try:
        row = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM {table_name} WHERE paper_id = ?",
            (paper_id,),
        ).fetchone()
        return int(row["cnt"]) if row else 0
    except sqlite3.Error:
        return 0


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def inspect_paper(vault: Path, query: str) -> dict[str, Any] | None:
    """Inspect end-to-end pipeline state and bottlenecks for one paper.

    Strictly read-only: never writes files, never acquires write/barrier locks,
    and only opens ``paperforge.db`` with SQLite ``?mode=ro`` when present.
    Returns ``None`` when no matching paper exists anywhere in index, DB, or OCR dir.
    """
    vault = Path(vault)
    ocr_root, db_path, configured_model = _resolve_vault_context(vault)
    index_items = _load_index_items(vault)

    conn, db_unreadable = _open_readonly_db(db_path)
    try:
        index_entry, candidates = _match_index_entry(index_items, query)
        db_entry: dict[str, Any] | None = None

        if candidates:
            return {
                "resolved": False,
                "query": query,
                "candidates": [_candidate_summary(c) for c in candidates],
            }

        if index_entry is None and conn is not None and _table_exists(conn, "papers"):
            if _table_exists(conn, "paper_aliases"):
                db_matches = lookup_paper(conn, query)
            else:
                q_norm = query.strip()
                row = conn.execute(
                    "SELECT * FROM papers WHERE LOWER(zotero_key) = LOWER(?) "
                    "OR LOWER(citation_key) = LOWER(?) OR LOWER(doi) = LOWER(?) LIMIT 1",
                    (q_norm, q_norm, q_norm),
                ).fetchone()
                db_matches = [dict(row)] if row else []

            if len(db_matches) > 1:
                return {
                    "resolved": False,
                    "query": query,
                    "candidates": [_candidate_summary(c) for c in db_matches],
                }
            if len(db_matches) == 1:
                db_entry = db_matches[0]

        if index_entry is not None:
            zotero_key = _entry_key(index_entry)
        elif db_entry is not None:
            zotero_key = _entry_key(db_entry)
        elif (ocr_root / query.strip()).is_dir():
            zotero_key = query.strip()
        else:
            return None

        if db_entry is None and conn is not None and _table_exists(conn, "papers"):
            row = conn.execute(
                "SELECT * FROM papers WHERE zotero_key = ?", (zotero_key,)
            ).fetchone()
            if row is not None:
                db_entry = dict(row)

        if index_entry is None and zotero_key:
            for item in index_items:
                if _entry_key(item) == zotero_key:
                    index_entry = item
                    break

        entry: dict[str, Any] = {}
        if db_entry:
            entry.update(db_entry)
        if index_entry:
            entry.update(index_entry)

        artifacts = artifact_paths_for_root(ocr_root, zotero_key)
        ocr_dir_exists = artifacts.paper_root.is_dir()
        ocr_meta = _safe_read_json(artifacts.meta_json)

        # Stage 1: source
        pdf_locator = (
            entry.get("pdf_path")
            or (db_entry or {}).get("pdf_path")
            or ocr_meta.get("source_pdf")
        )
        pdf_locator_str = str(pdf_locator).strip() if pdf_locator else None
        resolved_pdf = (
            resolve_source_pdf(vault, pdf_locator_str) if pdf_locator_str else None
        )
        if resolved_pdf is None and (artifacts.paper_root / "source.pdf").is_file():
            resolved_pdf = resolve_source_pdf(
                vault, str(artifacts.paper_root / "source.pdf")
            )
        source_page_count = _read_pdf_page_count(resolved_pdf)
        if source_page_count is None and isinstance(ocr_meta.get("page_count"), int):
            source_page_count = ocr_meta["page_count"]
        source_stage = {
            "in_index": index_entry is not None,
            "pdf_locator": pdf_locator_str,
            "pdf_exists": resolved_pdf is not None,
            "source_page_count": source_page_count,
        }

        # Stage 2: lineage
        note_relpath = entry.get("note_path") or entry.get("main_note_path")
        note_relpath_str = str(note_relpath).strip() if note_relpath else None
        note_exists = bool(
            note_relpath_str and (vault / note_relpath_str).is_file()
        )
        lineage_stage = {
            "note_relpath": note_relpath_str,
            "note_exists": note_exists,
            "index_ocr_status": entry.get("ocr_status"),
        }

        # Stage 3: ocr
        derived_meta = (
            ocr_meta.get("derived_version")
            if isinstance(ocr_meta.get("derived_version"), dict)
            else {}
        )
        pipeline_version = ocr_meta.get("ocr_pipeline_version") or derived_meta.get(
            "ocr_pipeline_version"
        )
        pipeline_stale = bool(
            ocr_dir_exists and pipeline_version != OCR_PIPELINE_VERSION
        )
        derived_stale = bool(ocr_meta.get("derived_stale", False)) or pipeline_stale
        has_raw_blocks = (
            artifacts.blocks_raw.is_file()
            and artifacts.blocks_raw.stat().st_size > 0
        )
        health_data = _safe_read_json(
            artifacts.paper_root / "health" / "ocr_health.json"
        )
        health_overall = health_data.get("overall") or health_data.get("status")
        ocr_stage = {
            "ocr_dir_exists": ocr_dir_exists,
            "status": ocr_meta.get("ocr_status") or ocr_meta.get("status"),
            "pipeline_version": pipeline_version,
            "expected_pipeline_version": OCR_PIPELINE_VERSION,
            "pipeline_stale": pipeline_stale,
            "derived_stale": derived_stale,
            "has_raw_blocks": has_raw_blocks,
            "can_rebuild_offline": has_raw_blocks,
            "health_overall": health_overall,
        }

        # Stage 4: objects_and_render
        render_fulltext = artifacts.paper_root / "render" / "fulltext.md"
        structure_dir = artifacts.paper_root / "structure"
        fig_inv = _safe_read_json(structure_dir / "figure_inventory.json")
        tbl_inv = _safe_read_json(structure_dir / "table_inventory.json")
        fig_list = (
            fig_inv.get("matched_figures")
            if fig_inv.get("matched_figures") is not None
            else (fig_inv.get("figures") or [])
        )
        tbl_list = tbl_inv.get("tables") or []
        consistency = _safe_read_json(
            artifacts.paper_root / "render" / "render.consistency.json"
        )
        consistency_issues = consistency.get("issues") or []
        objects_and_render_stage = {
            "render_fulltext_exists": render_fulltext.is_file(),
            "compat_fulltext_exists": artifacts.compat_fulltext.is_file(),
            "figure_count": len(fig_list) if isinstance(fig_list, list) else 0,
            "table_count": len(tbl_list) if isinstance(tbl_list, list) else 0,
            "consistency_status": consistency.get("state"),
            "consistency_issue_count": (
                len(consistency_issues) if isinstance(consistency_issues, list) else 0
            ),
        }

        # Stage 5: memory
        db_exists = db_path.is_file()
        schema_ok = False
        in_db = db_entry is not None
        body_unit_count = 0
        object_unit_count = 0
        db_fresh = False

        if conn is not None and not db_unreadable:
            if _table_exists(conn, "meta"):
                schema_ok = get_schema_version(conn) == CURRENT_SCHEMA_VERSION
            body_unit_count = _count_rows(conn, "body_units", zotero_key)
            object_unit_count = _count_rows(conn, "object_units", zotero_key)

            if in_db and schema_ok:
                db_fresh = True
                if _table_exists(conn, "meta"):
                    manifest_row = conn.execute(
                        "SELECT value FROM meta WHERE key = ?",
                        (f"manifest:{zotero_key}",),
                    ).fetchone()
                    tree_path = (
                        artifacts.paper_root / "index" / "structure-tree.json"
                    )
                    if manifest_row is not None:
                        try:
                            stored_manifest = json.loads(manifest_row["value"])
                        except (TypeError, ValueError):
                            stored_manifest = {}
                            db_fresh = False
                        disk_hash = None
                        result_hash_file = (
                            artifacts.paper_root / "index" / "result-hash.txt"
                        )
                        if result_hash_file.is_file():
                            disk_hash = result_hash_file.read_text(
                                encoding="utf-8"
                            ).strip()
                        if not disk_hash:
                            disk_hash = compute_ocr_result_hash(
                                artifacts.paper_root
                            )
                        stored_hash = stored_manifest.get("ocr_result_hash")
                        if disk_hash and stored_hash != disk_hash:
                            db_fresh = False
                    elif tree_path.is_file() and body_unit_count == 0:
                        db_fresh = False

                    if index_items and all(
                        isinstance(_entry_key(i), str) and _entry_key(i)
                        for i in index_items
                    ):
                        canon_row = conn.execute(
                            "SELECT value FROM meta WHERE key = 'canonical_index_hash'"
                        ).fetchone()
                        if canon_row and canon_row["value"]:
                            try:
                                if compute_hash(index_items) != canon_row["value"]:
                                    db_fresh = False
                            except KeyError:
                                pass

        memory_stage = {
            "db_exists": db_exists,
            "schema_ok": schema_ok,
            "in_db": in_db,
            "body_unit_count": body_unit_count,
            "object_unit_count": object_unit_count,
            "db_fresh": db_fresh,
        }

        # Stage 6: vectors
        vectors_stage = {
            "vector_body_count": _count_rows(conn, "vec_body_meta", zotero_key),
            "vector_object_count": _count_rows(
                conn, "vec_objects_meta", zotero_key
            ),
            "configured_model": configured_model,
        }
    finally:
        if conn is not None:
            conn.close()

    stages = {
        "source": source_stage,
        "lineage": lineage_stage,
        "ocr": ocr_stage,
        "objects_and_render": objects_and_render_stage,
        "memory": memory_stage,
        "vectors": vectors_stage,
    }

    findings: list[str] = []
    recommended_commands: list[str] = []
    hard_stages: list[str] = []
    soft_stages: list[str] = []

    if not source_stage["in_index"]:
        hard_stages.append("source")
        findings.append("Paper is missing from formal-library.json.")
        _append_unique(recommended_commands, "paperforge sync")
    if not source_stage["pdf_locator"]:
        hard_stages.append("source")
        findings.append("No source PDF locator recorded for this paper.")
        _append_unique(recommended_commands, "paperforge sync")
    elif not source_stage["pdf_exists"]:
        hard_stages.append("source")
        findings.append(
            f"Recorded PDF locator is missing or unreadable: {source_stage['pdf_locator']}"
        )
        _append_unique(recommended_commands, "paperforge sync")

    if not lineage_stage["note_relpath"] or not lineage_stage["note_exists"]:
        hard_stages.append("lineage")
        findings.append("Literature note is missing on disk.")
        _append_unique(recommended_commands, "paperforge sync")

    if not ocr_stage["ocr_dir_exists"]:
        hard_stages.append("ocr")
        findings.append("OCR artifact directory does not exist.")
        _append_unique(recommended_commands, f"paperforge ocr --key {zotero_key}")
    else:
        if not ocr_stage["has_raw_blocks"]:
            hard_stages.append("ocr")
            findings.append(
                "canonical/blocks.raw.jsonl is missing or empty; offline rebuild is unavailable."
            )
            _append_unique(
                recommended_commands, f"paperforge ocr --key {zotero_key}"
            )
        if ocr_stage["derived_stale"]:
            hard_stages.append("ocr")
            findings.append(
                "OCR derived artifacts are stale "
                f"(found pipeline_version={ocr_stage['pipeline_version']}, "
                f"expected={OCR_PIPELINE_VERSION})."
            )
            if ocr_stage["can_rebuild_offline"]:
                _append_unique(
                    recommended_commands,
                    f"paperforge action run ocr.rebuild_derived --scope papers --key {zotero_key} --json",
                )
                _append_unique(
                    recommended_commands,
                    f"python scripts/dev/ocr_rebuild_paper.py {zotero_key}",
                )
            else:
                _append_unique(
                    recommended_commands, f"paperforge ocr --key {zotero_key}"
                )
        if ocr_stage["health_overall"] in {"failed", "error"}:
            hard_stages.append("ocr")
            findings.append(
                f"OCR health report reported {ocr_stage['health_overall']}."
            )
        elif ocr_stage["health_overall"] == "degraded":
            soft_stages.append("ocr")
            findings.append("OCR health report is degraded.")

    if ocr_stage["ocr_dir_exists"] and (
        not objects_and_render_stage["render_fulltext_exists"]
        or not objects_and_render_stage["compat_fulltext_exists"]
    ):
        hard_stages.append("objects_and_render")
        findings.append("Rendered fulltext.md output is missing.")
        if ocr_stage["can_rebuild_offline"]:
            _append_unique(
                recommended_commands,
                f"paperforge action run ocr.rebuild_derived --scope papers --key {zotero_key} --json",
            )
            _append_unique(
                recommended_commands,
                f"python scripts/dev/ocr_rebuild_paper.py {zotero_key}",
            )
        else:
            _append_unique(
                recommended_commands, f"paperforge ocr --key {zotero_key}"
            )

    if objects_and_render_stage["consistency_status"] == "FAILED":
        hard_stages.append("objects_and_render")
        findings.append("Render consistency audit failed.")
    elif (
        objects_and_render_stage["consistency_status"] == "DEGRADED"
        or objects_and_render_stage["consistency_issue_count"] > 0
    ):
        soft_stages.append("objects_and_render")
        findings.append(
            "Render consistency audit reported "
            f"{objects_and_render_stage['consistency_issue_count']} issue(s)."
        )

    if not memory_stage["db_exists"]:
        hard_stages.append("memory")
        findings.append("Memory database paperforge.db does not exist.")
        _append_unique(recommended_commands, "paperforge memory build")
    elif not memory_stage["schema_ok"]:
        hard_stages.append("memory")
        findings.append("Memory database schema is outdated or unreadable.")
        _append_unique(recommended_commands, "paperforge memory build")
    elif not memory_stage["in_db"]:
        hard_stages.append("memory")
        findings.append("Paper is missing from paperforge.db.")
        _append_unique(recommended_commands, "paperforge memory build")
    elif not memory_stage["db_fresh"]:
        hard_stages.append("memory")
        findings.append("Memory database entry or units are stale.")
        _append_unique(recommended_commands, "paperforge memory build")

    if (
        memory_stage["in_db"]
        and memory_stage["body_unit_count"] > 0
        and vectors_stage["vector_body_count"] == 0
    ):
        soft_stages.append("vectors")
        findings.append("Body unit vector embeddings have not been built yet.")
        _append_unique(recommended_commands, "paperforge embed build")

    if hard_stages:
        overall = "action_needed"
        bottleneck_stage: str | None = hard_stages[0]
    elif soft_stages:
        overall = "degraded"
        bottleneck_stage = soft_stages[0]
    else:
        overall = "healthy"
        bottleneck_stage = None

    return {
        "resolved": True,
        "query": query,
        "zotero_key": zotero_key,
        "title": entry.get("title") or "",
        "citation_key": entry.get("citation_key") or "",
        "stages": stages,
        "diagnosis": {
            "overall": overall,
            "bottleneck_stage": bottleneck_stage,
            "findings": findings,
            "recommended_commands": recommended_commands,
        },
    }


def _print_text_report(data: dict[str, Any]) -> None:
    if not data.get("resolved"):
        candidates = data.get("candidates") or []
        print(f"Multiple candidates ({len(candidates)}) for '{data.get('query', '')}':")
        for c in candidates:
            print(f"  - {c.get('zotero_key', '')}: {c.get('title', '')} ({c.get('year', '')})")
        return

    diag = data.get("diagnosis") or {}
    stages = data.get("stages") or {}
    print(f"Paper:       {data.get('zotero_key', '')} ({data.get('citation_key', '')})")
    if data.get("title"):
        print(f"Title:       {data['title']}")
    print(f"Overall:     {diag.get('overall', 'unknown')}")
    if diag.get("bottleneck_stage"):
        print(f"Bottleneck:  {diag['bottleneck_stage']}")
    print("Stages:")
    for stage_name in ("source", "lineage", "ocr", "objects_and_render", "memory", "vectors"):
        stage_info = stages.get(stage_name) or {}
        print(f"  [{stage_name}] {json.dumps(stage_info, ensure_ascii=False)}")
    findings = diag.get("findings") or []
    if findings:
        print("Findings:")
        for item in findings:
            print(f"  - {item}")
    cmds = diag.get("recommended_commands") or []
    if cmds:
        print("Recommended:")
        for cmd in cmds:
            print(f"  $ {cmd}")


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    query = args.query

    try:
        report = inspect_paper(vault, query)
        if report is None:
            result = PFResult(
                ok=False,
                command="inspect",
                version=PF_VERSION,
                error=PFError(
                    code=ErrorCode.PATH_NOT_FOUND,
                    message=f"No paper found for: {query}",
                ),
            )
        else:
            result = PFResult(
                ok=True,
                command="inspect",
                version=PF_VERSION,
                data=report,
            )
    except Exception as exc:  # noqa: BLE001 — uniform CLI error envelope
        result = PFResult(
            ok=False,
            command="inspect",
            version=PF_VERSION,
            error=PFError(
                code=ErrorCode.INTERNAL_ERROR,
                message=str(exc),
            ),
        )

    if getattr(args, "json", False):
        print(result.to_json())
    else:
        if result.ok and result.data is not None:
            _print_text_report(result.data)
        else:
            msg = result.error.message if result.error else "Inspection failed"
            print(f"Error: {msg}", file=sys.stderr)

    return 0 if result.ok else 1
