from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """Centralized error codes for PFResult contracts."""

    PYTHON_NOT_FOUND = "PYTHON_NOT_FOUND"
    VERSION_MISMATCH = "VERSION_MISMATCH"
    BBT_EXPORT_NOT_FOUND = "BBT_EXPORT_NOT_FOUND"
    OCR_TOKEN_MISSING = "OCR_TOKEN_MISSING"
    SYNC_FAILED = "SYNC_FAILED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNKNOWN = "UNKNOWN"

    def __str__(self) -> str:
        return self.value
