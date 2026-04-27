"""Unit tests for _utils.py JSON I/O functions.

Covers: read_json, write_json, read_jsonl, write_jsonl
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from paperforge.worker._utils import read_json, read_jsonl, write_json, write_jsonl


class TestReadJson:
    """read_json(path) -> dict|list"""

    def test_reads_valid_json(self, tmp_path: Path) -> None:
        p = tmp_path / "data.json"
        p.write_text('{"key": "value"}', encoding="utf-8")
        assert read_json(p) == {"key": "value"}

    def test_reads_list_json(self, tmp_path: Path) -> None:
        p = tmp_path / "list.json"
        p.write_text('[1, 2, 3]', encoding="utf-8")
        assert read_json(p) == [1, 2, 3]

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.json"
        p.write_text("{invalid}", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            read_json(p)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "nope.json"
        with pytest.raises(FileNotFoundError):
            read_json(p)

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.json"
        p.write_text("", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            read_json(p)


class TestWriteJson:
    """write_json(path, data)"""

    def test_writes_dict(self, tmp_path: Path) -> None:
        p = tmp_path / "out.json"
        write_json(p, {"a": 1, "b": 2})
        assert json.loads(p.read_text(encoding="utf-8")) == {"a": 1, "b": 2}

    def test_writes_nested_data(self, tmp_path: Path) -> None:
        p = tmp_path / "nested.json"
        data = {"items": [{"id": 1}, {"id": 2}]}
        write_json(p, data)
        assert json.loads(p.read_text(encoding="utf-8")) == data

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        p = tmp_path / "a" / "b" / "c" / "deep.json"
        write_json(p, {"key": "val"})
        assert p.exists()
        assert json.loads(p.read_text(encoding="utf-8")) == {"key": "val"}

    def test_writes_pretty_indent(self, tmp_path: Path) -> None:
        p = tmp_path / "pretty.json"
        write_json(p, {"x": 1})
        text = p.read_text(encoding="utf-8")
        assert "{\n" in text, "should be indented with newlines"
        assert "  " in text, "should use 2-space indent"

    def test_writes_empty_dict(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.json"
        write_json(p, {})
        assert json.loads(p.read_text(encoding="utf-8")) == {}


class TestReadJsonl:
    """read_jsonl(path) -> list[dict]"""

    def test_reads_valid_jsonl(self, tmp_path: Path) -> None:
        p = tmp_path / "data.jsonl"
        p.write_text('{"a": 1}\n{"b": 2}\n', encoding="utf-8")
        assert read_jsonl(p) == [{"a": 1}, {"b": 2}]

    def test_skips_empty_lines(self, tmp_path: Path) -> None:
        p = tmp_path / "sparse.jsonl"
        p.write_text('{"a": 1}\n\n{"b": 2}\n', encoding="utf-8")
        assert read_jsonl(p) == [{"a": 1}, {"b": 2}]

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "nope.jsonl"
        assert read_jsonl(p) == []

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.jsonl"
        p.write_text("", encoding="utf-8")
        assert read_jsonl(p) == []

    def test_malformed_line_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.jsonl"
        p.write_text('{"ok": 1}\n{broken}\n', encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            read_jsonl(p)


class TestWriteJsonl:
    """write_jsonl(path, rows)"""

    def test_writes_rows(self, tmp_path: Path) -> None:
        p = tmp_path / "out.jsonl"
        write_jsonl(p, [{"a": 1}, {"b": 2}])
        lines = p.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0]) == {"a": 1}
        assert json.loads(lines[1]) == {"b": 2}

    def test_handles_empty_list(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.jsonl"
        write_jsonl(p, [])
        text = p.read_text(encoding="utf-8")
        assert text == "" or text.strip() == ""

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        p = tmp_path / "x" / "y" / "out.jsonl"
        write_jsonl(p, [{"k": "v"}])
        assert p.exists()
        assert json.loads(p.read_text(encoding="utf-8").strip().splitlines()[0]) == {"k": "v"}
