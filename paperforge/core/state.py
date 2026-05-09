"""State machine enums and allowed transitions for PaperForge lifecycle."""

from __future__ import annotations

from enum import Enum
from typing import ClassVar


class OcrStatus(str, Enum):
    """OCR processing state for a paper."""
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"

    @classmethod
    def from_legacy(cls, value: str) -> OcrStatus:
        """Map legacy OCR state strings to canonical enum."""
        mapping = {
            "pending": cls.PENDING,
            "processing": cls.PROCESSING,
            "queued": cls.PENDING,
            "running": cls.PROCESSING,
            "done": cls.DONE,
            "failed": cls.FAILED,
            "error": cls.FAILED,
            "blocked": cls.FAILED,
            "nopdf": cls.FAILED,
            "done_incomplete": cls.DONE,
        }
        return mapping.get(value.strip().lower(), cls.PENDING)

    def __str__(self) -> str:
        return self.value


class PdfStatus(str, Enum):
    """PDF attachment health state."""
    HEALTHY = "healthy"
    BROKEN = "broken"
    MISSING = "missing"

    def __str__(self) -> str:
        return self.value


class Lifecycle(str, Enum):
    """Derived lifecycle stage summarizing the paper's overall progress."""
    PDF_READY = "pdf_ready"
    OCR_READY = "ocr_ready"
    ANALYZE_READY = "analyze_ready"
    DEEP_READ_DONE = "deep_read_done"
    ERROR_STATE = "error_state"

    def __str__(self) -> str:
        return self.value


class ALLOWED_TRANSITIONS:
    """Legal state migration tables.

    Workers MUST validate transitions via check() before writing state changes.
    """

    OCR_STATUS: ClassVar[dict[OcrStatus, list[OcrStatus]]] = {
        OcrStatus.PENDING: [OcrStatus.PROCESSING, OcrStatus.FAILED],
        OcrStatus.PROCESSING: [OcrStatus.DONE, OcrStatus.FAILED],
        OcrStatus.DONE: [OcrStatus.PENDING],  # re-run
        OcrStatus.FAILED: [OcrStatus.PENDING],  # retry
    }

    DEEP_READING_STATUS: ClassVar[dict[str, list[str]]] = {
        "pending": ["done"],
        "done": ["pending"],  # re-run with --force
    }

    LIFECYCLE: ClassVar[dict[Lifecycle, list[Lifecycle]]] = {
        Lifecycle.PDF_READY: [Lifecycle.OCR_READY, Lifecycle.ERROR_STATE],
        Lifecycle.OCR_READY: [Lifecycle.ANALYZE_READY, Lifecycle.ERROR_STATE],
        Lifecycle.ANALYZE_READY: [Lifecycle.DEEP_READ_DONE, Lifecycle.ERROR_STATE],
        Lifecycle.DEEP_READ_DONE: [Lifecycle.PDF_READY, Lifecycle.ERROR_STATE],  # re-run
        Lifecycle.ERROR_STATE: [Lifecycle.PDF_READY],  # recover
    }

    @staticmethod
    def check_ocr(current: OcrStatus, target: OcrStatus) -> tuple[bool, str]:
        """Validate OCR status transition."""
        allowed = ALLOWED_TRANSITIONS.OCR_STATUS.get(current, [])
        if target in allowed:
            return True, ""
        return False, (
            f"Illegal OCR transition: {current.value} -> {target.value}. "
            f"Allowed from '{current.value}': {[s.value for s in allowed]}"
        )

    @staticmethod
    def check_lifecycle(current: Lifecycle, target: Lifecycle) -> tuple[bool, str]:
        """Validate lifecycle transition."""
        allowed = ALLOWED_TRANSITIONS.LIFECYCLE.get(current, [])
        if target in allowed:
            return True, ""
        return False, (
            f"Illegal lifecycle transition: {current.value} -> {target.value}. "
            f"Allowed from '{current.value}': {[s.value for s in allowed]}"
        )
