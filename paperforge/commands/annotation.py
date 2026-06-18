"""Annotation commands — CLI surface for PDF annotation operations.

Provides the ``paperforge annotation <import|list|status|export>``
namespace with PFResult JSON output.  Subcommand implementations
currently return placeholder data; real backend wiring is added in
subsequent waves.
"""

from __future__ import annotations

import argparse
import logging
import traceback

from paperforge import __version__
from paperforge.annotation.errors import (
    AnnotationImportError,
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
# Subcommand handlers (stubs — wired in subsequent waves)
# ---------------------------------------------------------------------------

def _cmd_import(args: argparse.Namespace) -> int:
    """Handle ``paperforge annotation import``."""
    json_output = getattr(args, "json", False)
    apply_mode = getattr(args, "apply", False)

    # Basic flag validation
    if not apply_mode and json_output:
        # Preview mode with JSON
        try:
            result = _success(
                command="annotation.import",
                data={
                    "dry_run": True,
                    "applied": False,
                    "paper": getattr(args, "paper", None),
                    "counts": {
                        "inserted": 0,
                        "updated": 0,
                        "unchanged": 0,
                        "stale": 0,
                        "skipped": 0,
                        "invalid": 0,
                    },
                },
            )
            print(result.to_json())
            return 0
        except AnnotationImportError as exc:
            result = _map_annotation_error("annotation.import", exc)
            print(result.to_json())
            return 1

    if not apply_mode:
        print("[DRY-RUN] paperforge annotation import -- would import annotations from Zotero")
        print("  Use --apply to perform the import")
        return 0

    # --apply mode (stub — will be wired to Phase 2 importer in Wave 2)
    if json_output:
        result = _success(
            command="annotation.import",
            data={
                "dry_run": False,
                "applied": True,
                "paper": getattr(args, "paper", None),
                "counts": {
                    "inserted": 0,
                    "updated": 0,
                    "unchanged": 0,
                    "stale": 0,
                    "skipped": 0,
                    "invalid": 0,
                },
            },
        )
        print(result.to_json())
        return 0

    print("Import completed (placeholder — Wave 2)")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    """Handle ``paperforge annotation list``."""
    json_output = getattr(args, "json", False)
    if json_output:
        try:
            result = _success(
                command="annotation.list",
                data={
                    "paper": getattr(args, "paper", None),
                    "annotations": [],
                    "total": 0,
                },
            )
            print(result.to_json())
            return 0
        except AnnotationImportError as exc:
            result = _map_annotation_error("annotation.list", exc)
            print(result.to_json())
            return 1

    print("Annotation list (placeholder — Wave 3)")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    """Handle ``paperforge annotation status``."""
    json_output = getattr(args, "json", False)
    if json_output:
        try:
            result = _success(
                command="annotation.status",
                data={
                    "db_configured": False,
                    "total_annotations": 0,
                    "total_papers_with_annotations": 0,
                    "zotero_import_available": True,
                },
            )
            print(result.to_json())
            return 0
        except AnnotationImportError as exc:
            result = _map_annotation_error("annotation.status", exc)
            print(result.to_json())
            return 1

    print("Annotation system status (placeholder — Wave 3)")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    """Handle ``paperforge annotation export``."""
    json_output = getattr(args, "json", False)
    if json_output:
        try:
            result = _success(
                command="annotation.export",
                data={
                    "paper": getattr(args, "paper", None),
                    "annotations": [],
                    "total": 0,
                },
            )
            print(result.to_json())
            return 0
        except AnnotationImportError as exc:
            result = _map_annotation_error("annotation.export", exc)
            print(result.to_json())
            return 1

    print("Annotation export (placeholder — Wave 3)")
    return 0


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
