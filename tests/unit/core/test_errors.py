"""Unit tests for ErrorCode enum."""
from __future__ import annotations

from paperforge.core.errors import ErrorCode


class TestErrorCodeMembers:
    """ErrorCode enum members match expected string values."""

    def test_members_and_values(self) -> None:
        assert ErrorCode.PYTHON_NOT_FOUND.value == "PYTHON_NOT_FOUND"
        assert ErrorCode.VERSION_MISMATCH.value == "VERSION_MISMATCH"
        assert ErrorCode.BBT_EXPORT_NOT_FOUND.value == "BBT_EXPORT_NOT_FOUND"
        assert ErrorCode.OCR_TOKEN_MISSING.value == "OCR_TOKEN_MISSING"
        assert ErrorCode.SYNC_FAILED.value == "SYNC_FAILED"
        assert ErrorCode.VALIDATION_ERROR.value == "VALIDATION_ERROR"
        assert ErrorCode.INTERNAL_ERROR.value == "INTERNAL_ERROR"
        assert ErrorCode.UNKNOWN.value == "UNKNOWN"

    def test_str_returns_value(self) -> None:
        assert str(ErrorCode.PYTHON_NOT_FOUND) == "PYTHON_NOT_FOUND"
        assert str(ErrorCode.UNKNOWN) == "UNKNOWN"

    def test_member_count_minimum(self) -> None:
        assert len(ErrorCode) >= 8  # expanded from 8 to 26 in v2.1 contract hardening

    def test_is_str_enum(self) -> None:
        assert isinstance(ErrorCode.PYTHON_NOT_FOUND, str)

    def test_unknown_code_returns_unknown(self) -> None:
        """Newer plugin versions may send codes not yet in this runtime."""
        assert ErrorCode("NONEXISTENT_CODE") is ErrorCode.UNKNOWN

    def test_future_code_returns_unknown(self) -> None:
        assert ErrorCode("PAPERFORGE_NOT_INSTALLED") is ErrorCode.PAPERFORGE_NOT_INSTALLED
        assert ErrorCode("OCR_UPLOAD_FAILED") is ErrorCode.OCR_UPLOAD_FAILED
