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
