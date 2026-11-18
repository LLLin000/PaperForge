"""Normalized OCR provider protocol and status vocabulary.

Adapters in ``paperforge.providers`` translate provider-specific wire
formats (upload, polling, and page/block JSON schemas) into PaperForge's
canonical ``ProviderStatus`` and ``raw_blocks`` dictionaries so downstream
V3 OCR stages stay decoupled from any single vendor API.
"""

from __future__ import annotations

from collections.abc import Iterator
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


class ProviderStatus(str, Enum):
    """Normalized provider job state — the only status vocabulary the rest
    of PaperForge ever sees."""

    QUEUED = "queued"      # submitted, waiting in provider queue
    RUNNING = "running"    # provider processing
    DONE = "done"          # provider finished, result URL available
    FAILED = "failed"      # provider terminal failure
    UNKNOWN = "unknown"    # unrecognized / unreadable state


@runtime_checkable
class OCRProvider(Protocol):
    """Contract every OCR provider adapter implements."""

    def submit(self, pdf_path: str | Path, batch_id: str | None = None) -> str:
        """Submit a local PDF and return the provider job id."""
        ...

    def get_job_status(self, job_id: str) -> tuple[ProviderStatus, dict[str, object]]:
        """Return ``(normalized_status, raw_payload)`` for one job."""
        ...

    def get_batch_status(
        self, batch_id: str
    ) -> dict[str, tuple[ProviderStatus, dict[str, object]]]:
        """Return ``{job_id: (normalized_status, raw_payload)}`` for a batch."""
        ...

    def extract_result_url(self, job_payload: dict[str, Any]) -> str | None:
        """Return the downloadable JSONL/result URL from a completed job payload."""
        ...

    def iter_page_results(self, all_results: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
        """Yield provider page result objects in reading page order."""
        ...

    def parse_page_blocks(
        self, paper_id: str, page: int, page_result: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Normalize one page result into canonical ``ocr_raw`` block rows."""
        ...

    def parse_raw_blocks(
        self, paper_id: str, all_results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Normalize all result pages into canonical ``ocr_raw`` block rows."""
        ...
