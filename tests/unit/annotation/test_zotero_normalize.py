"""Tests for Zotero annotation normalization (TDD — RED first).

Tests verify:
- NormalizedAnnotation dataclass matches annotations table columns.
- normalize_zotero_annotation produces a deterministic PaperForge id.
- Identity fields (source, library, parent, attachment, annotation key) populated.
- Zotero annotation content fields preserved.
- JSON fields are valid JSON strings.
- Zotero-sourced records are read-only with imported sync_state.
- Missing required fields raise AnnotationImportError.
"""

from __future__ import annotations

import json

import pytest

from paperforge.annotation.errors import AnnotationImportError


# ---------------------------------------------------------------------------
# Sample Zotero raw row (enriched with identity fields from JOINs)
# ---------------------------------------------------------------------------

SAMPLE_RAW: dict = {
    # Identity (resolved from items + itemAttachments JOINs by caller)
    "library_id": 1,
    "annotation_key": "ANNT1234",
    "attachment_key": "ATTN5678",
    "parent_key": "PARNT000",
    # Annotation content (from itemAnnotations)
    "type": "highlight",
    "text": "significant result with p<0.05",
    "comment": "This is a key finding that supports our hypothesis.",
    "color": "#ffd400",
    "pageLabel": "3",
    "page_index": 2,
    "sortIndex": 0,
    "position": '{"x":0.1,"y":0.2,"width":0.8,"height":0.05}',
    "dateModified": "2024-06-01T12:00:00Z",
    # Tags (resolved from itemTags + tags JOINs by caller)
    "tags": ["important", "methodology"],
}


# ---------------------------------------------------------------------------
# 1. Normalized output has source='zotero'
# ---------------------------------------------------------------------------


def test_normalized_source_is_zotero():
    """Imported Zotero annotations must have source='zotero'."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    result = normalize_zotero_annotation(SAMPLE_RAW, paper_id="PAPER001")
    assert result.source == "zotero"


# ---------------------------------------------------------------------------
# 2. Identity fields are all populated
# ---------------------------------------------------------------------------


def test_identity_fields_populated():
    """source_library_id, source_parent_key, source_attachment_key, and
    source_annotation_key must all be present and non-empty."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    result = normalize_zotero_annotation(SAMPLE_RAW, paper_id="PAPER001")
    assert result.source_library_id == "1"
    assert result.source_annotation_key == "ANNT1234"
    assert result.source_attachment_key == "ATTN5678"
    assert result.source_parent_key == "PARNT000"


# ---------------------------------------------------------------------------
# 3. Deterministic id
# ---------------------------------------------------------------------------


def test_deterministic_id_format():
    """The annotation id must follow the zotero:library:attachment:annotation
    pattern and be deterministic for the same inputs."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    result = normalize_zotero_annotation(SAMPLE_RAW, paper_id="PAPER001")
    assert result.id == "zotero:1:ATTN5678:ANNT1234"


def test_deterministic_id_same_inputs():
    """Calling normalize_zotero_annotation twice with the same inputs must
    produce the same id."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    r1 = normalize_zotero_annotation(SAMPLE_RAW, paper_id="PAPER001")
    r2 = normalize_zotero_annotation(SAMPLE_RAW, paper_id="PAPER001")
    assert r1.id == r2.id


def test_deterministic_id_different_libraries():
    """The same annotation key in different libraries must produce different
    ids."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    r1 = normalize_zotero_annotation(
        {**SAMPLE_RAW, "library_id": 1}, paper_id="PAPER001"
    )
    r2 = normalize_zotero_annotation(
        {**SAMPLE_RAW, "library_id": 2}, paper_id="PAPER001"
    )
    assert r1.id != r2.id


# ---------------------------------------------------------------------------
# 4. Annotation content fields preserved
# ---------------------------------------------------------------------------


def test_content_fields_preserved():
    """selected_text, comment, color, page_label, page_index, sort_index,
    and source_modified_at must be preserved from the raw row."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    result = normalize_zotero_annotation(SAMPLE_RAW, paper_id="PAPER001")
    assert result.selected_text == "significant result with p<0.05"
    assert result.comment == "This is a key finding that supports our hypothesis."
    assert result.color == "#ffd400"
    assert result.page_label == "3"
    assert result.page_index == 2
    assert result.sort_index == "0"
    assert result.source_modified_at == "2024-06-01T12:00:00Z"


# ---------------------------------------------------------------------------
# 5. JSON fields are valid JSON strings
# ---------------------------------------------------------------------------


def test_tags_json_valid():
    """tags_json must be a valid JSON string."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    result = normalize_zotero_annotation(SAMPLE_RAW, paper_id="PAPER001")
    parsed = json.loads(result.tags_json)
    assert isinstance(parsed, list)
    assert "important" in parsed
    assert "methodology" in parsed


def test_position_json_valid():
    """position_json must be a valid JSON string."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    result = normalize_zotero_annotation(SAMPLE_RAW, paper_id="PAPER001")
    parsed = json.loads(result.position_json)
    assert isinstance(parsed, dict)
    assert "x" in parsed
    assert "y" in parsed


def test_selector_json_default():
    """selector_json must default to a valid empty JSON object string."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    result = normalize_zotero_annotation(SAMPLE_RAW, paper_id="PAPER001")
    parsed = json.loads(result.selector_json)
    assert isinstance(parsed, dict)
    assert len(parsed) == 0


# ---------------------------------------------------------------------------
# 6. Zotero-sourced records are read-only
# ---------------------------------------------------------------------------


def test_is_readonly_set():
    """Zotero-sourced normalized records must have is_readonly=1."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    result = normalize_zotero_annotation(SAMPLE_RAW, paper_id="PAPER001")
    assert result.is_readonly == 1


def test_sync_state_imported():
    """Zotero-sourced normalized records must have sync_state='imported'."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    result = normalize_zotero_annotation(SAMPLE_RAW, paper_id="PAPER001")
    assert result.sync_state == "imported"


# ---------------------------------------------------------------------------
# 7. Invalid required fields raise AnnotationImportError
# ---------------------------------------------------------------------------


def test_missing_library_id_raises_error():
    """Missing library_id must raise AnnotationImportError."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    raw = {**SAMPLE_RAW}
    del raw["library_id"]
    with pytest.raises(AnnotationImportError):
        normalize_zotero_annotation(raw, paper_id="PAPER001")


def test_missing_annotation_key_raises_error():
    """Missing annotation_key must raise AnnotationImportError."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    raw = {**SAMPLE_RAW}
    del raw["annotation_key"]
    with pytest.raises(AnnotationImportError):
        normalize_zotero_annotation(raw, paper_id="PAPER001")


def test_missing_type_raises_error():
    """Missing type must raise AnnotationImportError."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    raw = {**SAMPLE_RAW}
    del raw["type"]
    with pytest.raises(AnnotationImportError):
        normalize_zotero_annotation(raw, paper_id="PAPER001")


def test_missing_attachment_key_raises_error():
    """Missing attachment_key must raise AnnotationImportError."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    raw = {**SAMPLE_RAW}
    del raw["attachment_key"]
    with pytest.raises(AnnotationImportError):
        normalize_zotero_annotation(raw, paper_id="PAPER001")


# ---------------------------------------------------------------------------
# 8. paper_id is passed through
# ---------------------------------------------------------------------------


def test_paper_id_passthrough():
    """The paper_id argument must appear verbatim in the normalized record."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    result = normalize_zotero_annotation(SAMPLE_RAW, paper_id="PAPER042")
    assert result.paper_id == "PAPER042"


# ---------------------------------------------------------------------------
# 9. Timestamps are set
# ---------------------------------------------------------------------------


def test_timestamps_set():
    """created_at and updated_at must be non-empty ISO-format strings."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    result = normalize_zotero_annotation(SAMPLE_RAW, paper_id="PAPER001")
    assert isinstance(result.created_at, str) and len(result.created_at) > 0
    assert isinstance(result.updated_at, str) and len(result.updated_at) > 0


# ---------------------------------------------------------------------------
# 10. deleted_at is None
# ---------------------------------------------------------------------------


def test_deleted_at_none():
    """Newly imported annotations must have deleted_at=None."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    result = normalize_zotero_annotation(SAMPLE_RAW, paper_id="PAPER001")
    assert result.deleted_at is None


# ---------------------------------------------------------------------------
# 11. Source version is null for new imports
# ---------------------------------------------------------------------------


def test_source_version_none():
    """source_version must be None for freshly imported annotations."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    result = normalize_zotero_annotation(SAMPLE_RAW, paper_id="PAPER001")
    assert result.source_version is None


# ---------------------------------------------------------------------------
# 12. Empty tags list produces '[]'
# ---------------------------------------------------------------------------


def test_empty_tags_produces_json_array():
    """When no tags are present, tags_json should be '[]'."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    raw = {**SAMPLE_RAW, "tags": []}
    result = normalize_zotero_annotation(raw, paper_id="PAPER001")
    assert result.tags_json == "[]"


# ---------------------------------------------------------------------------
# 13. Type passthrough
# ---------------------------------------------------------------------------


def test_type_passthrough():
    """The annotation type must pass through from raw row."""
    from paperforge.annotation.zotero_normalize import normalize_zotero_annotation

    for ann_type in ("highlight", "note", "underline", "ink"):
        raw = {**SAMPLE_RAW, "type": ann_type}
        result = normalize_zotero_annotation(raw, paper_id="PAPER001")
        assert result.type == ann_type
