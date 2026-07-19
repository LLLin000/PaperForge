from __future__ import annotations

from enum import Enum


class ErrorCode(str, Enum):
    """Centralized error codes for PFResult contracts.

    Codes are grouped by subsystem.  When adding a new code, prefer a
    narrow, actionable code over a catch-all so that plugin UI can
    generate targeted fix-it guidance.
    """

    # ── Runtime ──
    PYTHON_NOT_FOUND = "PYTHON_NOT_FOUND"
    PYTHON_VERSION_TOO_OLD = "PYTHON_VERSION_TOO_OLD"
    PAPERFORGE_NOT_INSTALLED = "PAPERFORGE_NOT_INSTALLED"
    VERSION_MISMATCH = "VERSION_MISMATCH"

    # ── Config / Vault ──
    VAULT_NOT_FOUND = "VAULT_NOT_FOUND"
    CONFIG_NOT_FOUND = "CONFIG_NOT_FOUND"
    CONFIG_INVALID = "CONFIG_INVALID"
    PATH_NOT_FOUND = "PATH_NOT_FOUND"

    # ── BBT / Zotero ──
    BBT_EXPORT_NOT_FOUND = "BBT_EXPORT_NOT_FOUND"
    BBT_EXPORT_INVALID = "BBT_EXPORT_INVALID"
    BBT_CITATION_KEY_MISSING = "BBT_CITATION_KEY_MISSING"
    ZOTERO_DATA_NOT_FOUND = "ZOTERO_DATA_NOT_FOUND"
    PDF_PATH_UNRESOLVED = "PDF_PATH_UNRESOLVED"

    # ── OCR ──
    OCR_TOKEN_MISSING = "OCR_TOKEN_MISSING"
    OCR_UPLOAD_FAILED = "OCR_UPLOAD_FAILED"
    OCR_POLL_TIMEOUT = "OCR_POLL_TIMEOUT"
    OCR_RESULT_INVALID = "OCR_RESULT_INVALID"

    # ── Sync ──
    SYNC_FAILED = "SYNC_FAILED"
    CANDIDATE_BUILD_FAILED = "CANDIDATE_BUILD_FAILED"
    NOTE_WRITE_FAILED = "NOTE_WRITE_FAILED"

    # ── Schema ──
    FIELD_MISSING = "FIELD_MISSING"
    FIELD_TYPE_INVALID = "FIELD_TYPE_INVALID"
    INDEX_SCHEMA_INVALID = "INDEX_SCHEMA_INVALID"

    # ── Generic ──
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def _missing_(cls, value):
        """Gracefully handle unknown codes from newer plugin versions."""
        return cls.UNKNOWN

    def __str__(self) -> str:
        return self.value
