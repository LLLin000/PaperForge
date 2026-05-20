"""Tests for annotation CRUD, search, and export operations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def ann_db(tmp_path: Path):
    """Provide a fresh annotation database with schema applied."""
    from paperforge.annotation.db import get_annotations_db_path, get_annotations_connection
    from paperforge.annotation.schema import ensure_schema

    db_path = get_annotations_db_path(tmp_path)
    conn = get_annotations_connection(db_path, read_only=False)
    ensure_schema(conn)
    yield conn
    conn.close()


def _seed_annotation(conn, overrides: dict | None = None) -> str:
    """Insert a minimal annotation row and return its id."""
    import uuid
    from datetime import datetime, timezone

    aid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "id": aid,
        "paper_id": "PAPER001",
        "type": "highlight",
        "source": "paperforge",
        "sync_state": "local",
        "is_readonly": 0,
        "page_index": 2,
        "selected_text": "Test text",
        "comment": "Test comment",
        "color": "#ffd400",
        "sort_index": "00002|000000|00000",
        "position_json": '{"pageIndex":2,"rects":[[72,520,540,536]]}',
        "tags_json": '["tag1"]',
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides or {})
    placeholders = ", ".join(f":{k}" for k in data)
    cols = ", ".join(data.keys())
    conn.execute(f"INSERT INTO annotations ({cols}) VALUES ({placeholders})", data)
    conn.commit()
    return aid


class TestCreate:
    def test_create_local_annotation(self, ann_db):
        from paperforge.annotation.service import create_annotation

        ann = create_annotation(
            ann_db,
            paper_id="PAPER001",
            annotation_type="highlight",
            page_index=2,
            selected_text="Test",
            comment="My comment",
            color="#ffd400",
            sort_index="00002|000000|00000",
            position_json={"pageIndex": 2, "rects": [[72, 520, 540, 536]]},
        )
        assert ann["source"] == "paperforge"
        assert ann["sync_state"] == "local"
        assert ann["is_readonly"] == 0
        assert ann["comment"] == "My comment"

    def test_create_sets_id(self, ann_db):
        from paperforge.annotation.service import create_annotation

        ann = create_annotation(ann_db, paper_id="P001", annotation_type="note")
        assert ann["id"] is not None
        assert len(ann["id"]) > 0


class TestPatch:
    def test_patch_comment_and_color(self, ann_db):
        from paperforge.annotation.service import patch_annotation, get_annotation

        aid = _seed_annotation(ann_db)
        result = patch_annotation(ann_db, aid, comment="New comment", color="#ff6666")
        assert result["comment"] == "New comment"
        assert result["color"] == "#ff6666"

        # Verify persisted
        ann = get_annotation(ann_db, aid)
        assert ann["comment"] == "New comment"
        assert ann["color"] == "#ff6666"

    def test_patch_readonly_rejected(self, ann_db):
        from paperforge.annotation.service import patch_annotation

        aid = _seed_annotation(ann_db, {"is_readonly": 1})
        import pytest as _pt

        with _pt.raises(ValueError, match="readonly"):
            patch_annotation(ann_db, aid, comment="Should fail")

    def test_patch_nonexistent_raises(self, ann_db):
        from paperforge.annotation.service import patch_annotation
        import pytest as _pt

        with _pt.raises(ValueError, match="not found"):
            patch_annotation(ann_db, "nonexistent", comment="x")


class TestDelete:
    def test_soft_delete(self, ann_db):
        from paperforge.annotation.service import delete_annotation, get_annotation

        aid = _seed_annotation(ann_db)
        delete_annotation(ann_db, aid)
        ann = get_annotation(ann_db, aid)
        assert ann["deleted_at"] is not None

    def test_hard_delete(self, ann_db):
        from paperforge.annotation.service import hard_delete, get_annotation

        aid = _seed_annotation(ann_db)
        hard_delete(ann_db, aid)
        assert get_annotation(ann_db, aid) is None


class TestList:
    def test_list_by_paper(self, ann_db):
        from paperforge.annotation.service import list_annotations

        _seed_annotation(ann_db)
        _seed_annotation(ann_db, {"paper_id": "PAPER002"})
        result = list_annotations(ann_db, paper_id="PAPER001")
        assert len(result) == 1

    def test_list_by_page(self, ann_db):
        from paperforge.annotation.service import list_annotations

        _seed_annotation(ann_db, {"page_index": 2})
        _seed_annotation(ann_db, {"page_index": 5})
        result = list_annotations(ann_db, paper_id="PAPER001", page_index=5)
        assert len(result) == 1


class TestExport:
    def test_export_json(self, ann_db):
        from paperforge.annotation.service import export_annotations_json

        _seed_annotation(ann_db)
        exported = export_annotations_json(ann_db, paper_id="PAPER001")
        data = json.loads(exported)
        assert len(data) == 1
        assert data[0]["type"] == "highlight"
        assert data[0]["selected_text"] == "Test text"

    def test_export_markdown(self, ann_db):
        from paperforge.annotation.service import export_annotations_markdown

        _seed_annotation(ann_db)
        md = export_annotations_markdown(ann_db, paper_id="PAPER001")
        assert "Test text" in md
        assert "Test comment" in md
        assert "Highlight" in md
