"""paperforge.annotation — PDF annotation persistence layer.

This package provides the database path and connection helpers for
storing and retrieving PDF annotations (highlights, notes, stamps, etc.).
It has no dependency on Zotero code.

The schema is intentionally NOT defined here — this package only provides
the infrastructure to open ``annotations.db``.
"""

from __future__ import annotations

from paperforge.annotation.db import get_annotations_connection, get_annotations_db_path

__all__ = [
    "get_annotations_connection",
    "get_annotations_db_path",
]
