"""paperforge annotation — CLI command family for PDF annotation management."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from paperforge.core.errors import ErrorCode

from paperforge import __version__ as PF_VERSION
from paperforge.annotation.cache import write_cache
from paperforge.annotation.db import get_annotations_db_path, get_annotations_connection
from paperforge.annotation.importer import run_import
from paperforge.annotation.probe import copy_db_to_temp, open_readonly, fetch_annotations
from paperforge.annotation.schema import ensure_schema, get_schema_version
from paperforge.annotation.service import (
    create_annotation,
    delete_annotation,
    export_annotations_json,
    export_annotations_markdown,
    get_annotation,
    hard_delete,
    list_annotations,
    patch_annotation,
)
from paperforge.config import paperforge_paths
from paperforge.core.result import PFError, PFResult


def _db_path(vault: Path) -> Path:
    return get_annotations_db_path(vault)


def _db_conn(vault: Path):
    db_path = _db_path(vault)
    conn = get_annotations_connection(db_path, read_only=False)
    ensure_schema(conn)
    return conn


def _probe_and_import(
    vault: Path,
    zotero_db: Path,
    paper_key: str,
    dry_run: bool,
    no_copy: bool,
) -> dict:
    """Core import pipeline: detect Zotero DB → probe → import."""
    probe_path = zotero_db
    if not no_copy:
        probe_path = copy_db_to_temp(zotero_db)

    probe_conn = open_readonly(probe_path)
    try:
        anns = fetch_annotations(probe_conn, limit=10000)
    finally:
        probe_conn.close()

    if paper_key:
        anns = [a for a in anns if a.get("parentItemKey") == paper_key]

    if dry_run:
        return {"paper_key": paper_key, "annotations_found": len(anns), "dry_run": True}

    conn = _db_conn(vault)
    try:
        result = run_import(conn, anns, source="zotero_db")
        result["annotations_found"] = len(anns)
        return result
    finally:
        conn.close()


def run(args: argparse.Namespace) -> int:
    vault = args.vault_path
    sub = getattr(args, "annotation_subcommand", "")
    json_output = getattr(args, "json", False)

    if sub == "import":
        return _cmd_import(vault, args, json_output)
    elif sub == "list":
        return _cmd_list(vault, args, json_output)
    elif sub == "create":
        return _cmd_create(vault, args, json_output)
    elif sub == "patch":
        return _cmd_patch(vault, args, json_output)
    elif sub == "delete":
        return _cmd_delete(vault, args, json_output)
    elif sub == "export":
        return _cmd_export(vault, args, json_output)
    elif sub == "status":
        return _cmd_status(vault, args, json_output)
    else:
        print(f"Unknown annotation subcommand: {sub}", file=sys.stderr)
        return 1


def _write_cache(vault: Path) -> None:
    """Open annotations.db, build JSON cache, write to indexes directory."""
    from paperforge.annotation.cache import write_cache as _wc
    conn = _db_conn(vault)
    try:
        _wc(conn, vault)
    finally:
        conn.close()


def _emit(result: PFResult, json_output: bool) -> int:
    if json_output:
        print(result.to_json())
    else:
        data = result.data or {}
        if result.ok:
            for k, v in data.items():
                if isinstance(v, list):
                    print(f"{k}: {len(v)}")
                else:
                    print(f"{k}: {v}")
        else:
            print(f"Error: {result.error.message}", file=sys.stderr)
    return 0 if result.ok else 1


def _cmd_import(vault, args, json_output):
    paths = paperforge_paths(vault)
    zotero_dir = paths.get("zotero_dir")
    zotero_db_raw = getattr(args, "zotero_db", None) or str(zotero_dir / "zotero.sqlite")
    zotero_db = Path(zotero_db_raw).expanduser().resolve()

    if not zotero_db.exists():
        result = PFResult(
            ok=False, command="annotation import", version=PF_VERSION,
            error=PFError(code="ZOTERO_DB_NOT_FOUND", message=f"Zotero SQLite not found: {zotero_db}"),
        )
        return _emit(result, json_output)

    try:
        data = _probe_and_import(
            vault, zotero_db,
            paper_key=getattr(args, "paper", ""),
            dry_run=getattr(args, "dry_run", False),
            no_copy=getattr(args, "no_copy", False),
        )
        if not getattr(args, "dry_run", False):
            try:
                _write_cache(vault)
            except Exception:
                pass
        result = PFResult(ok=True, command="annotation import", version=PF_VERSION, data=data)
        return _emit(result, json_output)
    except Exception as exc:
        result = PFResult(
            ok=False, command="annotation import", version=PF_VERSION,
            error=PFError(code=ErrorCode.INTERNAL_ERROR, message=str(exc)),
        )
        return _emit(result, json_output)


def _resolve_paper_key(vault, pdf_path):
    """Resolve a vault-relative PDF path to a paper zotero key via memory DB."""
    if not pdf_path:
        return ""
    import sqlite3
    db = Path(str(vault)) / "System" / "PaperForge" / "indexes" / "paperforge.db"
    if not db.exists():
        return ""
    try:
        mem = sqlite3.connect(str(db))
        mem.row_factory = sqlite3.Row
        pdf_name = Path(pdf_path).name
        # Memory DB stores pdf_path as wikilink: [[path/to/file.pdf]]
        # Match by filename inside wikilink, or by the raw path
        for like_pattern in [f"%/{pdf_name}]", f"%\\{pdf_name}]", f"%{pdf_name}%"]:
            row = mem.execute(
                "SELECT zotero_key FROM papers WHERE pdf_path LIKE ? LIMIT 1",
                (like_pattern,),
            ).fetchone()
            if row:
                mem.close()
                return row["zotero_key"]
        # Last resort: extract storage folder key (8-char HEX) from PDF path
        # e.g. System/Zotero/storage/XJSUZL8W/file.pdf -> XJSUZL8W
        m = __import__("re").search(r"storage[\\/]([A-Z0-9]{8})", pdf_path, __import__("re").IGNORECASE)
        if m:
            row = mem.execute(
                "SELECT zotero_key FROM papers WHERE pdf_path LIKE ? LIMIT 1",
                (f"%{m.group(1)}%",),
            ).fetchone()
            if row:
                mem.close()
                return row["zotero_key"]
        mem.close()
    except Exception:
        pass
    return ""


def _cmd_list(vault, args, json_output):
    paper_key = args.paper_key or ""
    if not paper_key and getattr(args, "pdf_path", None):
        paper_key = _resolve_paper_key(vault, args.pdf_path)
        if not paper_key:
            result = PFResult(
                ok=False, command="annotation list", version=PF_VERSION,
                error=PFError(code="PATH_NOT_FOUND", message=f"Could not resolve PDF path to paper key: {args.pdf_path}"),
            )
            return _emit(result, json_output)
    conn = _db_conn(vault)
    try:
        anns = list_annotations(
            conn,
            paper_id=paper_key,
            page_index=getattr(args, "page", None),
            annotation_type=getattr(args, "ann_type", ""),
            limit=getattr(args, "limit", 100),
        )
        result = PFResult(ok=True, command="annotation list", version=PF_VERSION, data={
            "paper_id": paper_key, "annotations": anns, "count": len(anns),
        })
        return _emit(result, json_output)
    finally:
        conn.close()


def _cmd_create(vault, args, json_output):
    paper_id = args.paper or ""
    if not paper_id and getattr(args, "pdf_path", None):
        paper_id = _resolve_paper_key(vault, args.pdf_path)
        if not paper_id:
            result = PFResult(
                ok=False, command="annotation create", version=PF_VERSION,
                error=PFError(code="PATH_NOT_FOUND", message=f"Could not resolve PDF path to paper key: {args.pdf_path}"),
            )
            return _emit(result, json_output)
    conn = _db_conn(vault)
    try:
        ann = create_annotation(
            conn,
            paper_id=paper_id,
            annotation_type=args.ann_type,
            page_index=getattr(args, "page_index", None),
            page_label=getattr(args, "page_label", ""),
            selected_text=getattr(args, "selected_text", ""),
            comment=getattr(args, "comment", ""),
            color=getattr(args, "color", "#ffd400"),
            sort_index=getattr(args, "sort_index", ""),
        )
        result = PFResult(ok=True, command="annotation create", version=PF_VERSION, data=ann)
        try:
            _write_cache(vault)
        except Exception:
            pass
        return _emit(result, json_output)
    except Exception as exc:
        result = PFResult(
            ok=False, command="annotation create", version=PF_VERSION,
            error=PFError(code="CREATE_FAILED", message=str(exc)),
        )
        return _emit(result, json_output)


def _cmd_patch(vault, args, json_output):
    conn = _db_conn(vault)
    try:
        kwargs = {}
        if getattr(args, "comment", None) is not None:
            kwargs["comment"] = args.comment
        if getattr(args, "color", None) is not None:
            kwargs["color"] = args.color
        ann = patch_annotation(conn, args.annotation_id, **kwargs)
        result = PFResult(ok=True, command="annotation patch", version=PF_VERSION, data=ann)
        try:
            _write_cache(vault)
        except Exception:
            pass
        return _emit(result, json_output)
    except Exception as exc:
        result = PFResult(
            ok=False, command="annotation patch", version=PF_VERSION,
            error=PFError(code="PATCH_FAILED", message=str(exc)),
        )
        return _emit(result, json_output)


def _cmd_delete(vault, args, json_output):
    conn = _db_conn(vault)
    try:
        ann = delete_annotation(conn, args.annotation_id, hard=getattr(args, "hard", False))
        result = PFResult(ok=True, command="annotation delete", version=PF_VERSION, data=ann)
        try:
            _write_cache(vault)
        except Exception:
            pass
        return _emit(result, json_output)
    except Exception as exc:
        result = PFResult(
            ok=False, command="annotation create", version=PF_VERSION,
            error=PFError(code="CREATE_FAILED", message=str(exc)),
        )
        return _emit(result, json_output)


def _cmd_patch(vault, args, json_output):
    conn = _db_conn(vault)
    try:
        kwargs = {}
        if getattr(args, "comment", None) is not None:
            kwargs["comment"] = args.comment
        if getattr(args, "color", None) is not None:
            kwargs["color"] = args.color
        ann = patch_annotation(conn, args.annotation_id, **kwargs)
        result = PFResult(ok=True, command="annotation patch", version=PF_VERSION, data=ann)
        return _emit(result, json_output)
    except ValueError as exc:
        result = PFResult(
            ok=False, command="annotation patch", version=PF_VERSION,
            error=PFError(code="PATCH_FAILED", message=str(exc)),
        )
        return _emit(result, json_output)


def _cmd_delete(vault, args, json_output):
    conn = _db_conn(vault)
    try:
        if getattr(args, "hard", False):
            hard_delete(conn, args.annotation_id)
        else:
            delete_annotation(conn, args.annotation_id)
        result = PFResult(ok=True, command="annotation delete", version=PF_VERSION, data={"id": args.annotation_id})
        return _emit(result, json_output)
    except ValueError as exc:
        result = PFResult(
            ok=False, command="annotation delete", version=PF_VERSION,
            error=PFError(code="DELETE_FAILED", message=str(exc)),
        )
        return _emit(result, json_output)


def _cmd_export(vault, args, json_output):
    conn = _db_conn(vault)
    try:
        fmt = getattr(args, "format", "json")
        paper_key = args.paper_key
        if fmt == "markdown":
            text = export_annotations_markdown(conn, paper_id=paper_key)
        else:
            text = export_annotations_json(conn, paper_id=paper_key)

        output_path = getattr(args, "output", None)
        if output_path:
            Path(output_path).write_text(text, encoding="utf-8")
            result = PFResult(ok=True, command="annotation export", version=PF_VERSION, data={"path": output_path})
        else:
            if json_output:
                print(text)
            else:
                result = PFResult(ok=True, command="annotation export", version=PF_VERSION, data={"text": text})
        return _emit(result, json_output)
    except Exception as exc:
        result = PFResult(
            ok=False, command="annotation export", version=PF_VERSION,
            error=PFError(code="EXPORT_FAILED", message=str(exc)),
        )
        return _emit(result, json_output)


def _cmd_status(vault, args, json_output):
    db_path = _db_path(vault)
    data = {
        "db_exists": db_path.exists(),
        "db_path": str(db_path),
    }
    if db_path.exists():
        conn = _db_conn(vault)
        try:
            count = conn.execute("SELECT COUNT(*) as cnt FROM annotations WHERE deleted_at IS NULL").fetchone()["cnt"]
            schema_ver = get_schema_version(conn)
            data["annotation_count"] = count
            data["schema_version"] = schema_ver
        finally:
            conn.close()
    result = PFResult(ok=True, command="annotation status", version=PF_VERSION, data=data)
    return _emit(result, json_output)
