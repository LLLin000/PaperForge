"""Zotero annotation row normalization.

This module converts enriched Zotero annotation data (from the probe layer)
into PaperForge's source-agnostic annotation records that are ready for
insertion into ``annotations.db``.

**D-06 — Identity contract:**
The deterministic PaperForge id format is ``zotero:{library_id}:{attachment_key}:{annotation_key}``,
which encodes source + library scope + attachment + individual annotation key.
This avoids collision between annotations from different Zotero libraries.

**D-07 — Read-only contract:**
All Zotero-sourced normalized records have ``is_readonly=1`` and
``sync_state='imported'``.  PaperForge treats these as authoritative
source rows that should not be edited directly.

**D-09 — Preservation contract:**
Research-useful fields preserved: ``selected_text``, ``comment``, ``color``,
``page_label``, ``page_index``, ``sort_index``, ``tags_json``, ``position_json``,
``source_modified_at``, ``source_attachment_key``, ``source_parent_key``,
``source_library_id``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from paperforge.annotation.errors import AnnotationImportError


# ---------------------------------------------------------------------------
# Required identity fields that must be present in the raw row
# ---------------------------------------------------------------------------

_REQUIRED_IDENTITY_FIELDS = frozenset({
    "library_id",
    "annotation_key",
    "attachment_key",
    "type",
})
"""Fields that must be present and non-empty in every raw row."""


# ---------------------------------------------------------------------------
# Normalized annotation model
# ---------------------------------------------------------------------------


@dataclass
class NormalizedAnnotation:
    """A normalized PaperForge annotation record ready for DB insertion.

    Every field maps directly to a column in the ``annotations`` table.
    Zotero-sourced records are pre-configured with ``source="zotero"``,
    ``is_readonly=1``, and ``sync_state="imported"``.
    """

    # -- Identity / provenance ------------------------------------------------
    id: str
    """Deterministic PaperForge annotation id, e.g. ``zotero:1:ATTN1234:ANNT5678``."""

    paper_id: str
    """Foreign key to the owning paper record."""

    source: str = "zotero"
    """Always ``'zotero'`` for Zotero-imported records."""

    source_library_id: str = ""
    """Zotero library ID (stringified)."""

    source_annotation_key: str = ""
    """Zotero annotation item key (``items.key``)."""

    source_attachment_key: str = ""
    """Zotero attachment item key (``items.key`` for the PDF attachment)."""

    source_parent_key: str = ""
    """Zotero parent paper item key (``items.key`` for the parent item)."""

    source_version: int | None = None
    """Optional version number (not populated during initial import)."""

    source_modified_at: str = ""
    """Zotero ``dateModified`` timestamp string."""

    # -- Annotation content ---------------------------------------------------
    type: str = ""
    """Annotation type (highlight, note, underline, ink, etc.) — preserved from
    Zotero."""

    page_index: int | None = None
    """Zero-based page index (derived by caller from pageLabel)."""

    page_label: str = ""
    """Page label from Zotero (e.g. '1', '2', 'Appendix A')."""

    selected_text: str = ""
    """The highlighted text content (maps to Zotero ``text``)."""

    comment: str = ""
    """User's annotation comment."""

    color: str = ""
    """Highlight color hex code (e.g. ``#ffd400``)."""

    sort_index: str = ""
    """Sort order index from Zotero (converted to string for TEXT column)."""

    # -- JSON payloads --------------------------------------------------------
    tags_json: str = "[]"
    """Tags as a JSON array string."""

    position_json: str = "{}"
    """Position rectangle as a JSON object string."""

    selector_json: str = "{}"
    """Text selector as a JSON object string (reserved for Zotero 7)."""

    # -- Sync / lifecycle -----------------------------------------------------
    sync_state: str = "imported"
    """``'imported'`` for Zotero-sourced rows (never ``'local'``)."""

    is_readonly: int = 1
    """``1`` for Zotero-sourced rows — PaperForge should not edit them."""

    created_at: str = ""
    """ISO-8601 UTC timestamp of when this record was created."""

    updated_at: str = ""
    """ISO-8601 UTC timestamp of when this record was last updated."""

    deleted_at: str | None = None
    """Soft-delete timestamp — ``None`` for freshly imported records."""


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _now_utc() -> str:
    """Return the current UTC time as an ISO-8601 string (second precision)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_identity(raw: dict[str, Any]) -> None:
    """Validate that all required identity fields are present and non-empty.

    Args:
        raw: The raw annotation dict.

    Raises:
        AnnotationImportError: If any required field is missing or empty.
    """
    for field in _REQUIRED_IDENTITY_FIELDS:
        value = raw.get(field)
        if value is None or value == "":
            raise AnnotationImportError(
                f"Missing required field '{field}' in Zotero annotation raw row"
            )


# ---------------------------------------------------------------------------
# Main normalizer
# ---------------------------------------------------------------------------


def normalize_zotero_annotation(
    raw_row: dict[str, Any],
    paper_id: str,
) -> NormalizedAnnotation:
    """Normalize an enriched Zotero annotation row into a PaperForge record.

    The *raw_row* is expected to be a dict-like object containing:
      - Identity fields (resolved via SQL joins by the caller):
        ``library_id``, ``annotation_key``, ``attachment_key``, ``parent_key``
      - Annotation content (from ``itemAnnotations``):
        ``type``, ``text``, ``comment``, ``color``, ``pageLabel``, ``sortIndex``,
        ``position``, ``dateModified``
      - Tags (resolved via ``itemTags`` + ``tags`` by the caller):
        ``tags`` (list of strings)

    Args:
        raw_row: Enriched Zotero annotation data as a dict.
        paper_id: PaperForge paper identifier.

    Returns:
        A ``NormalizedAnnotation`` instance ready for DB insertion.

    Raises:
        AnnotationImportError: If a required identity field is missing.
    """
    _validate_identity(raw_row)

    # -- Build deterministic PaperForge id -----------------------------------
    ann_id = (
        f"zotero:{raw_row['library_id']}"
        f":{raw_row['attachment_key']}"
        f":{raw_row['annotation_key']}"
    )

    # -- String conversion helpers -------------------------------------------
    def _str(val: Any) -> str:
        if val is None:
            return ""
        if isinstance(val, str):
            return val
        return str(val)

    # -- JSON field construction ---------------------------------------------
    tags_raw = raw_row.get("tags")
    if isinstance(tags_raw, list):
        tags_json = json.dumps(tags_raw, ensure_ascii=False)
    else:
        tags_json = "[]"

    position_raw = raw_row.get("position", "{}")
    if isinstance(position_raw, str):
        position_json = position_raw
    else:
        position_json = json.dumps(position_raw, ensure_ascii=False)

    # -- Sort index (Zotero INTEGER → schema TEXT) ---------------------------
    sort_index_raw = raw_row.get("sortIndex")
    sort_index = str(sort_index_raw) if sort_index_raw is not None else ""

    # -- Timestamps ----------------------------------------------------------
    now = _now_utc()

    return NormalizedAnnotation(
        id=ann_id,
        paper_id=paper_id,
        source="zotero",
        source_library_id=_str(raw_row.get("library_id", "")),
        source_annotation_key=_str(raw_row.get("annotation_key", "")),
        source_attachment_key=_str(raw_row.get("attachment_key", "")),
        source_parent_key=_str(raw_row.get("parent_key", "")),
        source_modified_at=_str(raw_row.get("dateModified", "")),
        type=_str(raw_row.get("type", "")),
        page_index=raw_row.get("page_index") if raw_row.get("page_index") is not None else None,
        page_label=_str(raw_row.get("pageLabel", "")),
        selected_text=_str(raw_row.get("text", "")),
        comment=_str(raw_row.get("comment", "")),
        color=_str(raw_row.get("color", "")),
        sort_index=sort_index,
        tags_json=tags_json,
        position_json=position_json,
        selector_json="{}",
        sync_state="imported",
        is_readonly=1,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
