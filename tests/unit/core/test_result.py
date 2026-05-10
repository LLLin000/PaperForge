"""Unit tests for PFResult / PFError round-trip serialization."""
from __future__ import annotations

import json

from paperforge.core.errors import ErrorCode
from paperforge.core.result import PFError, PFResult


class TestPFResultBool:
    """PFResult truthiness follows ok field."""

    def test_ok_is_true(self) -> None:
        result = PFResult(ok=True, command="sync", version="1.0.0")
        assert bool(result) is True

    def test_not_ok_is_false(self) -> None:
        error = PFError(code=ErrorCode.SYNC_FAILED, message="sync failed")
        result = PFResult(ok=False, command="sync", version="1.0.0", error=error)
        assert bool(result) is False


class TestPFResultRoundTrip:
    """PFResult serialization round-trip: to_dict -> from_dict."""

    def test_ok_with_data(self) -> None:
        original = PFResult(
            ok=True,
            command="sync",
            version="1.4.17rc3",
            data={"created": 5, "updated": 2},
        )
        d = original.to_dict()
        reconstructed = PFResult.from_dict(d)
        assert reconstructed.ok == original.ok
        assert reconstructed.command == original.command
        assert reconstructed.version == original.version
        assert reconstructed.data == original.data
        assert reconstructed.error is None

    def test_with_error(self) -> None:
        error = PFError(
            code=ErrorCode.SYNC_FAILED,
            message="Export file not found",
            details={"path": "/tmp/library.json"},
        )
        original = PFResult(
            ok=False,
            command="sync",
            version="1.4.17rc3",
            data=None,
            error=error,
        )
        d = original.to_dict()
        reconstructed = PFResult.from_dict(d)
        assert reconstructed.ok is False
        assert reconstructed.command == "sync"
        assert reconstructed.data is None
        assert reconstructed.error is not None
        assert reconstructed.error.code == ErrorCode.SYNC_FAILED
        assert reconstructed.error.message == "Export file not found"
        assert reconstructed.error.details == {"path": "/tmp/library.json"}

    def test_none_data_serializes_as_null(self) -> None:
        result = PFResult(ok=True, command="status", version="1.4.17rc3", data=None)
        d = result.to_dict()
        assert d["data"] is None
        assert d["ok"] is True

    def test_no_error_serializes_as_null(self) -> None:
        result = PFResult(ok=True, command="status", version="1.4.17rc3")
        d = result.to_dict()
        assert d["error"] is None

    def test_to_json_round_trip(self) -> None:
        original = PFResult(
            ok=True,
            command="sync",
            version="1.4.17rc3",
            data={"count": 42},
        )
        json_str = original.to_json()
        parsed = json.loads(json_str)
        reconstructed = PFResult.from_dict(parsed)
        assert reconstructed == original

    def test_to_json_indent_two(self) -> None:
        result = PFResult(ok=True, command="ping", version="1.0.0")
        json_str = result.to_json()
        lines = json_str.splitlines()
        for line in lines:
            if line.strip().startswith('"'):
                assert line.startswith("  ") or line.startswith("{")

    def test_from_dict_missing_error_returns_none(self) -> None:
        data = {
            "ok": True,
            "command": "test",
            "version": "1.0.0",
            "data": None,
            "error": None,
        }
        result = PFResult.from_dict(data)
        assert result.error is None
        assert result.ok is True


class TestPFResultV21Fields:
    """v2.1 contract hardening: warnings, next_actions, suggestions round-trip."""

    def test_warnings_round_trip(self) -> None:
        original = PFResult(
            ok=True,
            command="sync",
            version="2.1.0",
            warnings=["BBT export is stale; re-export recommended"],
        )
        d = original.to_dict()
        assert d["warnings"] == ["BBT export is stale; re-export recommended"]
        reconstructed = PFResult.from_dict(d)
        assert reconstructed.warnings == original.warnings
        assert reconstructed == original

    def test_warnings_empty_omitted_from_dict(self) -> None:
        result = PFResult(ok=True, command="sync", version="2.1.0")
        d = result.to_dict()
        assert "warnings" not in d

    def test_warnings_from_dict_missing_defaults_empty(self) -> None:
        data = {"ok": True, "command": "test", "version": "1.0.0"}
        result = PFResult.from_dict(data)
        assert result.warnings == []

    def test_next_actions_round_trip(self) -> None:
        original = PFResult(
            ok=False,
            command="sync",
            version="2.1.0",
            next_actions=[
                {"id": "open_exports_dir", "label": "Open exports folder"},
                {"id": "run_zotero", "label": "Launch Zotero"},
            ],
        )
        d = original.to_dict()
        assert len(d["next_actions"]) == 2
        assert d["next_actions"][0]["id"] == "open_exports_dir"
        reconstructed = PFResult.from_dict(d)
        assert reconstructed.next_actions == original.next_actions

    def test_next_actions_empty_omitted_from_dict(self) -> None:
        result = PFResult(ok=True, command="sync", version="2.1.0")
        d = result.to_dict()
        assert "next_actions" not in d

    def test_error_suggestions_round_trip(self) -> None:
        error = PFError(
            code=ErrorCode.BBT_EXPORT_NOT_FOUND,
            message="No BBT export found",
            suggestions=[
                "In Zotero, right-click collection → Export Collection",
                "Format: Better BibTeX JSON",
                "Tick 'Keep updated'",
            ],
        )
        result = PFResult(ok=False, command="sync", version="2.1.0", error=error)
        d = result.to_dict()
        assert "suggestions" in d["error"]
        assert len(d["error"]["suggestions"]) == 3
        reconstructed = PFResult.from_dict(d)
        assert reconstructed.error is not None
        assert reconstructed.error.suggestions == error.suggestions

    def test_error_suggestions_empty_omitted(self) -> None:
        error = PFError(code=ErrorCode.SYNC_FAILED, message="fail")
        result = PFResult(ok=False, command="sync", version="2.1.0", error=error)
        d = result.to_dict()
        assert "suggestions" not in d["error"]

    def test_from_dict_missing_suggestions_defaults_empty(self) -> None:
        data = {
            "ok": False,
            "command": "test",
            "version": "1.0.0",
            "error": {"code": "SYNC_FAILED", "message": "fail", "details": {}},
        }
        result = PFResult.from_dict(data)
        assert result.error is not None
        assert result.error.suggestions == []

    def test_from_dict_unknown_error_code_graceful(self) -> None:
        """Newer plugin may send error codes not yet in this runtime."""
        data = {
            "ok": False,
            "command": "sync",
            "version": "2.1.0",
            "error": {
                "code": "SOME_FUTURE_ERROR_CODE",
                "message": "Something new happened",
                "details": {},
            },
        }
        result = PFResult.from_dict(data)
        assert result.error is not None
        assert result.error.code is ErrorCode.UNKNOWN
        assert result.error.message == "Something new happened"
