"""Structured domain exceptions for annotation import and Zotero probe operations.

Error hierarchy::

    AnnotationImportError
     +-- ZoteroDatabaseError     (missing / unreadable / invalid Zotero SQLite)
     +-- ZoteroSchemaError       (missing / unknown Zotero tables or columns)

These are designed to be caught by CLI code and converted to stable JSON
and user-facing Chinese messages.
"""

from __future__ import annotations


class AnnotationImportError(Exception):
    """Base error for PDF annotation import operations.

    All annotation-domain exceptions inherit from this class so callers
    can catch a single base type when they do not need fine-grained
    distinction.
    """


class ZoteroDatabaseError(AnnotationImportError):
    """The Zotero SQLite database is missing, unreadable, or invalid.

    Args:
        message: Human-readable description.
        db_path: The path that was being accessed (if available).
        original_error: The underlying Python/sqlite3 exception, if any.
    """

    def __init__(
        self,
        message: str,
        db_path: str | None = None,
        original_error: Exception | None = None,
    ) -> None:
        self.db_path = db_path
        self.original_error = original_error
        super().__init__(message)


class ZoteroSchemaError(AnnotationImportError):
    """The Zotero database is openable but missing expected tables or columns.

    Args:
        message: Human-readable description describing which table/column
                 is missing.
        table_name: The affected table (if known).
        column_name: The missing column (if known).
    """

    def __init__(
        self,
        message: str,
        table_name: str | None = None,
        column_name: str | None = None,
    ) -> None:
        self.table_name = table_name
        self.column_name = column_name
        super().__init__(message)
