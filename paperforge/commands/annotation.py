"""Annotation commands — CLI surface for PDF annotation operations.

Provides the ``paperforge annotation <import|list|status|export>``
namespace with PFResult JSON output.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import traceback
from pathlib import Path

from paperforge import __version__
from paperforge.annotation.db import get_annotations_db_path
from paperforge.annotation.errors import (
    AnnotationImportError,
)
from paperforge.annotation.importer import (
    import_zotero_annotations_for_paper,
    ImportResult,
)
from paperforge.annotation.zotero_normalize import normalize_zotero_annotation
from paperforge.annotation.zotero_probe import (
    fetch_zotero_item_annotations,
    open_zotero_readonly,
    probe_zotero_annotation_schema,
    zotero_snapshot,
)
from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PFResult helpers
# ---------------------------------------------------------------------------

def _success(command: str, data: dict | None = None) -> PFResult:
    """Build a success PFResult for an annotation subcommand."""
    return PFResult(
        ok=True,
        command=command,
        version=__version__,
        data=data or {},
    )


def _error(
    command: str,
    code: ErrorCode,
    message: str,
    details: dict | None = None,
    suggestions: list[str] | None = None,
) -> PFResult:
    """Build an error PFResult for an annotation subcommand."""
    return PFResult(
        ok=False,
        command=command,
        version=__version__,
        data=None,
        error=PFError(
            code=code,
            message=message,
            details=details or {},
            suggestions=suggestions or [],
        ),
    )


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------

def _map_annotation_error(command: str, exc: AnnotationImportError) -> PFResult:
    """Map an ``AnnotationImportError`` (or subclass) to a structured PFResult.

    Returns a PFResult with an appropriate error code, actionable Chinese-friendly
    message, and suggestions when available.
    """
    from paperforge.annotation.errors import ZoteroDatabaseError, ZoteroSchemaError

    if isinstance(exc, ZoteroDatabaseError):
        msg = exc.args[0] if exc.args else "Zotero 数据库无法访问"
        details: dict = {}
        if exc.db_path:
            details["db_path"] = exc.db_path
        if exc.original_error:
            details["original_error"] = repr(exc.original_error)
        return _error(
            command=command,
            code=ErrorCode.ZOTERO_DATA_NOT_FOUND,
            message=msg,
            details=details,
            suggestions=[
                "检查 --zotero-db 路径是否正确",
                "确认 Zotero 正在运行且数据库未锁定",
            ],
        )

    if isinstance(exc, ZoteroSchemaError):
        msg = exc.args[0] if exc.args else "Zotero 注释表结构异常"
        return _error(
            command=command,
            code=ErrorCode.INDEX_SCHEMA_INVALID,
            message=msg,
            details={"table": exc.table_name, "column": exc.column_name} if exc.table_name else {},
            suggestions=[
                "检查 Zotero 是否为最新版本",
                "确认 Better BibTeX 插件已正确安装",
            ],
        )

    # Generic annotation error fallback
    return _error(
        command=command,
        code=ErrorCode.INTERNAL_ERROR,
        message=exc.args[0] if exc.args else "注释导入过程中发生未知错误",
        details={},
        suggestions=["查看日志文件了解详细信息"],
    )

# ---------------------------------------------------------------------------
# Paper key resolution helpers (Zotero SQLite lookup)
# ---------------------------------------------------------------------------


def _resolve_paper_key(
    conn: sqlite3.Connection, paper_key: str
) -> tuple[int, int, str]:
    """Look up a parent item by its Zotero ``items.key``.

    Returns:
        Tuple of (itemID, libraryID, key).
    """
    row = conn.execute(
        "SELECT itemID, libraryID, key FROM items WHERE key = ?",
        (paper_key,),
    ).fetchone()
    if not row:
        raise AnnotationImportError(
            f"Zotero 中未找到文献键值 '{paper_key}'"
        )
    return (row["itemID"], row["libraryID"], row["key"])


def _resolve_attachment(
    conn: sqlite3.Connection,
    parent_item_id: int,
    attachment_key_hint: str | None = None,
) -> tuple[int, str]:
    """Find the first PDF attachment for a parent item.

    If *attachment_key_hint* is given, filter by that attachment key.

    Returns:
        Tuple of (attachment_itemID, attachment_key).
    """
    if attachment_key_hint:
        row = conn.execute(
            """SELECT ia.itemID, i.key
                 FROM itemAttachments ia
                 JOIN items i ON ia.itemID = i.itemID
                WHERE ia.parentItemID = ? AND i.key = ?""",
            (parent_item_id, attachment_key_hint),
        ).fetchone()
        if not row:
            raise AnnotationImportError(
                f"未找到附件键值 '{attachment_key_hint}'"
            )
    else:
        rows = conn.execute(
            """SELECT ia.itemID, i.key
                 FROM itemAttachments ia
                 JOIN items i ON ia.itemID = i.itemID
                WHERE ia.parentItemID = ?
                ORDER BY ia.itemID""",
            (parent_item_id,),
        ).fetchall()
        if not rows:
            raise AnnotationImportError(
                "Zotero 中该文献没有 PDF 附件"
            )
        if len(rows) > 1:
            raise AnnotationImportError(
                "该文献有多个附件，请使用 --attachment-key 指定"
            )
        row = rows[0]
    return (row["itemID"], row["key"])


def _count_raw_annotations(
    conn: sqlite3.Connection, attachment_item_id: int
) -> int:
    """Count raw annotation rows for a given attachment."""
    rows = fetch_zotero_item_annotations(
        conn, parent_item_id=attachment_item_id
    )
    return len(rows)


def _run_import(
    zotero_conn: sqlite3.Connection,
    annotations_db_path: Path,
    paper_id: str,
    library_id: int,
    parent_item_id: int,
    parent_item_key: str,
    attachment_item_id: int,
    attachment_item_key: str,
) -> ImportResult:
    """Run the Phase 2 import pipeline, return counts."""
    return import_zotero_annotations_for_paper(
        zotero_conn=zotero_conn,
        annotations_db_path=annotations_db_path,
        paper_id=paper_id,
        library_id=library_id,
        parent_item_id=parent_item_id,
        parent_item_key=parent_item_key,
        attachment_item_id=attachment_item_id,
        attachment_item_key=attachment_item_key,
    )


def _counts_to_json(result: ImportResult) -> dict:
    """Convert ImportResult to a JSON-safe dict."""
    return {
        "inserted": result.inserted,
        "updated": result.updated,
        "unchanged": result.unchanged,
        "stale": result.stale,
        "skipped": result.skipped,
        "total": result.total,
    }


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def _cmd_import(args: argparse.Namespace) -> int:
    """Handle ``paperforge annotation import``.

    Defaults to preview mode (no mutations).  Requires ``--apply`` to write.
    """
    json_output = getattr(args, "json", False)
    apply_mode = getattr(args, "apply", False)
    paper_key = getattr(args, "paper", None)
    zotero_db_arg = getattr(args, "zotero_db", None)
    attachment_key_hint = getattr(args, "attachment_key", None)

    try:
        # --- Validate required flags ---
        if not paper_key:
            if json_output:
                    result = _error(
                        command="annotation.import",
                        code=ErrorCode.VALIDATION_ERROR,
                        message="缺少 --paper 参数，请指定文献键值",
                        details={"missing": "--paper"},
                        suggestions=["使用 --paper KEY 指定要导入文献的 Zotero 键值"],
                    )
                    print(result.to_json())
                    return 1
            print("Error: --paper is required for annotation import")
            return 1

        # --- Resolve Zotero DB path ---
        if zotero_db_arg:
            zotero_db_path = Path(zotero_db_arg)
        else:
            if json_output:
                result = _error(
                    command="annotation.import",
                    code=ErrorCode.VALIDATION_ERROR,
                    message="缺少 --zotero-db 参数",
                    details={"missing": "--zotero-db"},
                    suggestions=["使用 --zotero-db PATH 指定 Zotero SQLite 数据库路径"],
                )
                print(result.to_json())
                return 1
            print("Error: --zotero-db is required")
            return 1

        if not zotero_db_path.exists():
            if json_output:
                result = _error(
                    command="annotation.import",
                    code=ErrorCode.ZOTERO_DATA_NOT_FOUND,
                    message=f"Zotero 数据库不存在: {zotero_db_path}",
                    details={"db_path": str(zotero_db_path)},
                    suggestions=["检查 --zotero-db 路径是否正确"],
                )
                print(result.to_json())
                return 1
            print(f"Error: Zotero database not found: {zotero_db_path}")
            return 1

        # --- Snapshot + open + probe ---
        with zotero_snapshot(zotero_db_path) as snap_path:
            zotero_conn = open_zotero_readonly(snap_path)
            try:
                probe_zotero_annotation_schema(zotero_conn)

                # --- Resolve paper and attachment ---
                parent_item_id, library_id, parent_item_key = _resolve_paper_key(
                    zotero_conn, paper_key
                )
                attachment_item_id, attachment_item_key = _resolve_attachment(
                    zotero_conn, parent_item_id, attachment_key_hint
                )

                # --- Resolve annotations DB path ---
                vault = getattr(args, "vault_path", None)
                if vault:
                    annotations_db_path = get_annotations_db_path(vault)
                else:
                    annotations_db_path = None

                if apply_mode and annotations_db_path is None:
                    if json_output:
                        result = _error(
                            command="annotation.import",
                            code=ErrorCode.CONFIG_NOT_FOUND,
                            message="无法确定 annotations.db 路径",
                            suggestions=["检查 vault 配置是否正确"],
                        )
                        print(result.to_json())
                        return 1
                    print("Error: cannot resolve annotations.db path")
                    return 1

                # --- Preview mode ---
                if not apply_mode:
                    total_count = _count_raw_annotations(
                        zotero_conn, attachment_item_id
                    )
                    if json_output:
                        result = _success(
                            command="annotation.import",
                            data={
                                "dry_run": True,
                                "applied": False,
                                "paper": paper_key,
                                "attachment_key": attachment_item_key,
                                "source": "zotero",
                                "counts": {
                                    "total": total_count,
                                },
                            },
                        )
                        print(result.to_json())
                        return 0
                    print(
                        f"[DRY-RUN] Would import {total_count} annotation(s) "
                        f"for paper '{paper_key}'"
                    )
                    print("  Use --apply to perform the import")
                    return 0

                # --- Apply mode ---
                import_result = _run_import(
                    zotero_conn=zotero_conn,
                    annotations_db_path=annotations_db_path,
                    paper_id=paper_key,
                    library_id=library_id,
                    parent_item_id=parent_item_id,
                    parent_item_key=parent_item_key,
                    attachment_item_id=attachment_item_id,
                    attachment_item_key=attachment_item_key,
                )

                if json_output:
                    result = _success(
                        command="annotation.import",
                        data={
                            "dry_run": False,
                            "applied": True,
                            "paper": paper_key,
                            "attachment_key": attachment_item_key,
                            "source": "zotero",
                            "counts": _counts_to_json(import_result),
                        },
                    )
                    print(result.to_json())
                    return 0

                counts = import_result
                print(
                    f"Import complete for '{paper_key}': "
                    f"{counts.inserted} inserted, {counts.updated} updated, "
                    f"{counts.unchanged} unchanged, {counts.stale} stale, "
                    f"{counts.skipped} skipped"
                )
                return 0

            finally:
                zotero_conn.close()

    except AnnotationImportError as exc:
        if json_output:
            result = _map_annotation_error("annotation.import", exc)
            print(result.to_json())
            return 1
        print(f"Error: {exc}", file=__import__("sys").stderr)
        return 1
    except Exception as exc:
        logger.exception("Unexpected error in annotation import")
        if json_output:
            result = _error(
                command="annotation.import",
                code=ErrorCode.INTERNAL_ERROR,
                message=f"导入过程中发生未预期的错误: {exc}",
                details={"exception": repr(exc)},
                suggestions=["请检查日志文件了解详细信息"],
            )
            print(result.to_json())
            return 1
        print(f"Unexpected error: {exc}", file=__import__("sys").stderr)
        if getattr(args, "verbose", False):
            traceback.print_exc()
        return 1


# ---------------------------------------------------------------------------
# DB helpers for read-only commands
# ---------------------------------------------------------------------------


def _open_annotations_db(args: argparse.Namespace) -> sqlite3.Connection | None:
    """Open annotations.db in read-only mode, or None if unavailable."""
    vault = getattr(args, "vault_path", None)
    if not vault:
        return None
    try:
        db_path = get_annotations_db_path(vault)
        from paperforge.annotation.db import get_annotations_connection

        return get_annotations_connection(db_path, read_only=True)
    except (FileNotFoundError, sqlite3.OperationalError):
        return None


def _require_paper(args: argparse.Namespace, command: str) -> int | None:
    """Validate --paper is provided. Returns exit code if error, None if OK."""
    json_output = getattr(args, "json", False)
    paper = getattr(args, "paper", None)
    if not paper:
        if json_output:
            result = _error(
                command=command,
                code=ErrorCode.VALIDATION_ERROR,
                message="缺少 --paper 参数",
                details={"missing": "--paper"},
                suggestions=["使用 --paper KEY 指定文献键值"],
            )
            print(result.to_json())
            return 1
        print(f"Error: --paper is required for {command}")
        return 1
    return None


def _rows_to_list(rows: list[sqlite3.Row]) -> list[dict]:
    """Convert annotation rows to lightweight list format."""
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "type": row["type"],
            "page": row["page_index"],
            "page_label": row["page_label"],
            "selected_text": row["selected_text"],
            "comment": row["comment"],
            "color": row["color"],
            "source": row["source"],
            "is_readonly": bool(row["is_readonly"]),
        })
    return result


def _rows_to_export(rows: list[sqlite3.Row]) -> list[dict]:
    """Convert annotation rows to full export format."""
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "paper_id": row["paper_id"],
            "source": row["source"],
            "source_library_id": row["source_library_id"],
            "source_annotation_key": row["source_annotation_key"],
            "source_attachment_key": row["source_attachment_key"],
            "source_parent_key": row["source_parent_key"],
            "source_modified_at": row["source_modified_at"],
            "type": row["type"],
            "page_index": row["page_index"],
            "page_label": row["page_label"],
            "selected_text": row["selected_text"],
            "comment": row["comment"],
            "color": row["color"],
            "sort_index": row["sort_index"],
            "tags_json": row["tags_json"],
            "position_json": row["position_json"],
            "selector_json": row["selector_json"],
            "sync_state": row["sync_state"],
            "is_readonly": bool(row["is_readonly"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "deleted_at": row["deleted_at"],
        })
    return result


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def _cmd_list(args: argparse.Namespace) -> int:
    """Handle ``paperforge annotation list``."""
    json_output = getattr(args, "json", False)
    command = "annotation.list"

    try:
        # Require --paper
        error = _require_paper(args, command)
        if error is not None:
            return error

        paper_key = getattr(args, "paper", None)
        conn = _open_annotations_db(args)

        if conn is None:
            if json_output:
                result = _success(
                    command=command,
                    data={
                        "paper": paper_key,
                        "annotations": [],
                        "total": 0,
                    },
                )
                print(result.to_json())
                return 0
            print(f"No annotations for '{paper_key}' (annotations.db not available)")
            return 0

        try:
            rows = conn.execute(
                """SELECT * FROM annotations
                   WHERE paper_id = ? AND deleted_at IS NULL
                   ORDER BY page_index, sort_index, id""",
                (paper_key,),
            ).fetchall()

            if json_output:
                result = _success(
                    command=command,
                    data={
                        "paper": paper_key,
                        "annotations": _rows_to_list(rows),
                        "total": len(rows),
                    },
                )
                print(result.to_json())
                return 0

            print(f"Annotations for '{paper_key}': {len(rows)} found")
            return 0
        finally:
            conn.close()

    except Exception as exc:
        logger.exception("Error in annotation list")
        if json_output:
            result = _error(
                command=command,
                code=ErrorCode.INTERNAL_ERROR,
                message=f"列出注释时出错: {exc}",
            )
            print(result.to_json())
            return 1
        print(f"Error: {exc}", file=__import__("sys").stderr)
        return 1


def _cmd_status(args: argparse.Namespace) -> int:
    """Handle ``paperforge annotation status``."""
    json_output = getattr(args, "json", False)
    command = "annotation.status"

    try:
        vault = getattr(args, "vault_path", None)
        conn = _open_annotations_db(args)

        if conn is None:
            if json_output:
                result = _success(
                    command=command,
                    data={
                        "db_path": None,
                        "schema_version": 0,
                        "total_annotations": 0,
                        "source_counts": {},
                        "readonly_count": 0,
                        "deleted_count": 0,
                        "db_available": False,
                        "total_papers_with_annotations": 0,
                    },
                )
                print(result.to_json())
                return 0
            print("Annotation system status: annotations.db not available")
            return 0

        try:
            # Schema version
            from paperforge.annotation.schema import get_schema_version

            sv = get_schema_version(conn)

            # Total annotations (including deleted)
            total = conn.execute(
                "SELECT COUNT(*) as c FROM annotations"
            ).fetchone()["c"]

            # Source counts
            source_rows = conn.execute(
                "SELECT source, COUNT(*) as c FROM annotations GROUP BY source"
            ).fetchall()
            source_counts = {r["source"]: r["c"] for r in source_rows}

            # Read-only count
            ro = conn.execute(
                "SELECT COUNT(*) as c FROM annotations WHERE is_readonly = 1"
            ).fetchone()["c"]

            # Deleted count
            deleted = conn.execute(
                "SELECT COUNT(*) as c FROM annotations WHERE deleted_at IS NOT NULL"
            ).fetchone()["c"]

            # Papers with annotations
            papers = conn.execute(
                "SELECT COUNT(DISTINCT paper_id) as c FROM annotations"
            ).fetchone()["c"]

            # DB path
            db_path = None
            if vault:
                try:
                    db_path = str(get_annotations_db_path(vault))
                except (FileNotFoundError, KeyError):
                    pass

            if json_output:
                result = _success(
                    command=command,
                    data={
                        "db_path": db_path,
                        "schema_version": sv,
                        "total_annotations": total,
                        "source_counts": source_counts,
                        "readonly_count": ro,
                        "deleted_count": deleted,
                        "db_available": True,
                        "total_papers_with_annotations": papers,
                    },
                )
                print(result.to_json())
                return 0

            print(
                f"Annotation DB: {db_path or 'unknown'}, "
                f"schema v{sv}, {total} annotations, "
                f"{papers} papers"
            )
            return 0
        finally:
            conn.close()

    except Exception as exc:
        logger.exception("Error in annotation status")
        if json_output:
            result = _error(
                command=command,
                code=ErrorCode.INTERNAL_ERROR,
                message=f"获取注释状态时出错: {exc}",
            )
            print(result.to_json())
            return 1
        print(f"Error: {exc}", file=__import__("sys").stderr)
        return 1


def _cmd_export(args: argparse.Namespace) -> int:
    """Handle ``paperforge annotation export``."""
    json_output = getattr(args, "json", False)
    command = "annotation.export"

    try:
        # Require --paper
        error = _require_paper(args, command)
        if error is not None:
            return error

        paper_key = getattr(args, "paper", None)
        conn = _open_annotations_db(args)

        if conn is None:
            if json_output:
                result = _success(
                    command=command,
                    data={
                        "paper": paper_key,
                        "annotations": [],
                        "total": 0,
                        "format_version": "1.0",
                    },
                )
                print(result.to_json())
                return 0
            print(f"No export for '{paper_key}' (annotations.db not available)")
            return 0

        try:
            rows = conn.execute(
                """SELECT * FROM annotations
                   WHERE paper_id = ?
                   ORDER BY page_index, sort_index, id""",
                (paper_key,),
            ).fetchall()

            if json_output:
                result = _success(
                    command=command,
                    data={
                        "paper": paper_key,
                        "annotations": _rows_to_export(rows),
                        "total": len(rows),
                        "format_version": "1.0",
                    },
                )
                print(result.to_json())
                return 0

            print(f"Export for '{paper_key}': {len(rows)} annotations")
            return 0
        finally:
            conn.close()

    except Exception as exc:
        logger.exception("Error in annotation export")
        if json_output:
            result = _error(
                command=command,
                code=ErrorCode.INTERNAL_ERROR,
                message=f"导出注释时出错: {exc}",
            )
            print(result.to_json())
            return 1
        print(f"Error: {exc}", file=__import__("sys").stderr)
        return 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run(args: argparse.Namespace) -> int:
    """Dispatch to the appropriate annotation subcommand.

    Returns integer exit code (0 = success, 1 = error).
    """
    sub = getattr(args, "annotation_command", None)

    dispatch = {
        "import": _cmd_import,
        "list": _cmd_list,
        "status": _cmd_status,
        "export": _cmd_export,
    }

    handler = dispatch.get(sub)
    if handler is None:
        print(f"Error: unknown annotation subcommand {sub!r}", file=__import__("sys").stderr)
        return 1

    try:
        return handler(args)
    except AnnotationImportError as exc:
        json_output = getattr(args, "json", False)
        if json_output:
            result = _map_annotation_error(f"annotation.{sub}", exc)
            print(result.to_json())
            return 1
        print(f"Error: {exc}", file=__import__("sys").stderr)
        return 1
    except Exception as exc:
        json_output = getattr(args, "json", False)
        if json_output:
            result = _error(
                command=f"annotation.{sub}",
                code=ErrorCode.INTERNAL_ERROR,
                message=f"未预期的错误: {exc}",
                details={"exception": repr(exc)},
                suggestions=["请检查日志文件了解详细信息"],
            )
            print(result.to_json())
            return 1
        print(f"Unexpected error: {exc}", file=__import__("sys").stderr)
        if getattr(args, "verbose", False):
            traceback.print_exc()
        return 1
