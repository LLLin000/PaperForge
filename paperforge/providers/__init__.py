"""Pluggable OCR provider registry and normalized inbound schema boundary."""

from __future__ import annotations

from typing import Any

from paperforge.providers.base import OCRProvider, ProviderStatus
from paperforge.providers.paddleocr import (
    PaddleOCRProvider,
    PaddleOCRProviderError,
    extract_paddleocr_result_url,
    iter_paddleocr_page_results,
    normalize_provider_state,
    parse_paddleocr_page_blocks,
    parse_paddleocr_raw_blocks,
)

__all__ = [
    "OCRProvider",
    "PaddleOCRProvider",
    "PaddleOCRProviderError",
    "ProviderStatus",
    "extract_paddleocr_result_url",
    "iter_paddleocr_page_results",
    "normalize_provider_state",
    "parse_paddleocr_page_blocks",
    "parse_paddleocr_raw_blocks",
    "resolve_ocr_provider",
]


def resolve_ocr_provider(provider_name: str = "paddleocr", **kwargs: Any) -> OCRProvider:
    """Instantiate a configured OCR provider adapter by name."""
    normalized = (provider_name or "paddleocr").strip().lower()
    if normalized in ("paddleocr", "paddle"):
        return PaddleOCRProvider(**kwargs)
    raise ValueError(
        f"Unsupported OCR provider: {provider_name!r}. Supported: 'paddleocr'."
    )
