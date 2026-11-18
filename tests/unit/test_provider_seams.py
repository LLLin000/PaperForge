"""Unit tests for pluggable OCR and Embedding provider boundaries."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from paperforge.embedding.preflight import _preflight_check
from paperforge.embedding.providers import (
    EmbeddingProvider,
    resolve_embedding_provider,
)
from paperforge.providers import (
    OCRProvider,
    PaddleOCRProvider,
    ProviderStatus,
    extract_paddleocr_result_url,
    parse_paddleocr_raw_blocks,
    resolve_ocr_provider,
)
from paperforge.worker.ocr_blocks import (
    build_raw_blocks_for_result_lines,
    build_structured_blocks,
)
from tests.conftest import canonical_test_config


def test_paddleocr_provider_implements_protocol() -> None:
    provider = PaddleOCRProvider("tok-123")
    assert isinstance(provider, OCRProvider)
    resolved = resolve_ocr_provider("paddleocr", token="tok-123")
    assert isinstance(resolved, PaddleOCRProvider)
    with pytest.raises(ValueError, match="Unsupported OCR provider"):
        resolve_ocr_provider("nonexistent-provider")


def test_extract_paddleocr_result_url() -> None:
    assert (
        extract_paddleocr_result_url({"resultUrl": {"jsonUrl": "https://x/out.jsonl"}})
        == "https://x/out.jsonl"
    )
    assert extract_paddleocr_result_url({"resultUrl": {}}) is None
    assert extract_paddleocr_result_url({}) is None


def test_ocr_raw_normalization_and_custom_provider_parity() -> None:
    raw_api_payloads: list[dict[str, Any]] = [
        {
            "layoutParsingResults": [
                {
                    "prunedResult": {
                        "width": 1000,
                        "height": 1400,
                        "parsing_res_list": [
                            {
                                "block_id": "b1",
                                "block_label": "doc_title",
                                "block_order": 0,
                                "block_bbox": [50, 50, 900, 110],
                                "block_content": "Sample Paper Title",
                            },
                            {
                                "block_id": "b2",
                                "block_label": "text",
                                "block_order": 1,
                                "block_bbox": [50, 140, 900, 260],
                                "block_content": "Body paragraph content.",
                            },
                        ],
                    }
                }
            ]
        }
    ]

    from_provider = parse_paddleocr_raw_blocks("PAPER1", raw_api_payloads)
    from_worker = build_raw_blocks_for_result_lines("PAPER1", raw_api_payloads)
    assert from_provider == from_worker
    assert len(from_provider) == 2
    assert from_provider[0]["source"] == "ocr_raw"
    assert from_provider[0]["raw_label"] == "doc_title"

    class CustomOCRProvider:
        def submit(self, pdf_path: str | Path, batch_id: str | None = None) -> str:
            return "job-custom"

        def get_job_status(self, job_id: str) -> tuple[ProviderStatus, dict[str, object]]:
            return ProviderStatus.DONE, {"result_url": "https://custom/result.json"}

        def get_batch_status(
            self, batch_id: str
        ) -> dict[str, tuple[ProviderStatus, dict[str, object]]]:
            return {"job-custom": (ProviderStatus.DONE, {})}

        def extract_result_url(self, job_payload: dict[str, Any]) -> str | None:
            url = job_payload.get("result_url")
            return str(url) if url else None

        def iter_page_results(
            self, all_results: list[dict[str, Any]]
        ) -> Iterator[dict[str, Any]]:
            yield from all_results

        def parse_page_blocks(
            self, paper_id: str, page: int, page_result: dict[str, Any]
        ) -> list[dict[str, Any]]:
            return [
                {
                    "paper_id": paper_id,
                    "page": page,
                    "block_id": item["id"],
                    "raw_label": item["kind"],
                    "raw_order": idx,
                    "bbox": item["box"],
                    "text": item["content"],
                    "page_width": page_result["w"],
                    "page_height": page_result["h"],
                    "source": "ocr_raw",
                }
                for idx, item in enumerate(page_result["items"])
            ]

        def parse_raw_blocks(
            self, paper_id: str, all_results: list[dict[str, Any]]
        ) -> list[dict[str, Any]]:
            rows: list[dict[str, Any]] = []
            for pno, page_res in enumerate(self.iter_page_results(all_results), start=1):
                rows.extend(self.parse_page_blocks(paper_id, pno, page_res))
            return rows

    custom: OCRProvider = CustomOCRProvider()
    assert isinstance(custom, OCRProvider)
    custom_raw = custom.parse_raw_blocks(
        "PAPER1",
        [
            {
                "w": 1000,
                "h": 1400,
                "items": [
                    {
                        "id": "b1",
                        "kind": "doc_title",
                        "box": [50, 50, 900, 110],
                        "content": "Sample Paper Title",
                    },
                    {
                        "id": "b2",
                        "kind": "text",
                        "box": [50, 140, 900, 260],
                        "content": "Body paragraph content.",
                    },
                ],
            }
        ],
    )
    assert custom_raw == from_provider
    structured, _ = build_structured_blocks(custom_raw, structure_output_dir=None)
    assert [b["role"] for b in structured] == ["paper_title", "unknown_structural"]


def test_requests_embedding_provider_works_without_openai_sdk(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    canonical_test_config(tmp_path)
    idx_dir = tmp_path / "System" / "PaperForge" / "indexes"
    idx_dir.mkdir(parents=True, exist_ok=True)
    (idx_dir / "formal-library.json").write_text(
        json.dumps({"items": [{"key": "P1", "ocr_status": "done"}]}),
        encoding="utf-8",
    )

    monkeypatch.setenv("PAPERFORGE_CREDENTIAL_EMBEDDING__DEFAULT", "test-key")
    monkeypatch.setenv("VECTOR_DB_PROVIDER_TYPE", "requests")
    monkeypatch.setitem(sys.modules, "openai", None)

    assert _preflight_check(tmp_path) == {"ok": True}

    provider = resolve_embedding_provider(tmp_path)
    assert isinstance(provider, EmbeddingProvider)
    with patch("paperforge.embedding.providers.requests_fallback.requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"data": [{"embedding": [0.25, 0.75]}]}
        mock_post.return_value.raise_for_status = lambda: None
        vec = provider.encode_single("query")
    assert vec == [0.25, 0.75]


def test_unknown_embedding_provider_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from paperforge.config import ConfigError

    canonical_test_config(tmp_path)
    monkeypatch.setenv("VECTOR_DB_PROVIDER_TYPE", "bogus_provider")
    with pytest.raises(ConfigError):
        _preflight_check(tmp_path)

    monkeypatch.delenv("VECTOR_DB_PROVIDER_TYPE", raising=False)
    monkeypatch.setattr(
        "paperforge.embedding.providers.get_provider_type",
        lambda _vault: "bogus_provider",
    )

    prereq = _preflight_check(tmp_path)
    assert prereq["ok"] is False
    assert "Unsupported embedding provider type" in prereq["error"]

    with pytest.raises(ValueError, match="Unsupported embedding provider type"):
        resolve_embedding_provider(tmp_path)
