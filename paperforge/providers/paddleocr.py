"""PaddleOCR provider adapter (Control Plane Closure F1).

The network layer for the PaddleOCR AI Studio async API (v2).  Exposes
normalized operations and a normalized status enum; Paddle SDK / HTTP
types never leak into worker / probe / action / CLI, so a future provider
swap does not touch the control plane.

Batch identity (F2): one logical PaperForge OCR execution submits every
job with the same ``batchId``; ``get_batch_status`` observes the whole
batch in one request.  A job that fails and is resubmitted keeps the SAME
batch id (one logical execution) with a NEW job id.
"""

from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path
from typing import Any

import requests

from paperforge.providers.base import ProviderStatus

DEFAULT_JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"

# Provider payloads are dynamic JSON; expose them as object-valued dicts so
# callers cast at the boundary (no object leaking into annotations).
JobPayload = dict[str, object]


def normalize_provider_state(state: str) -> ProviderStatus:
    s = (state or "").strip().lower()
    if s in ("pending", "queued", "waiting"):
        return ProviderStatus.QUEUED
    if s == "running":
        return ProviderStatus.RUNNING
    if s == "done":
        return ProviderStatus.DONE
    if s in ("error", "failed"):
        return ProviderStatus.FAILED
    return ProviderStatus.UNKNOWN


class PaddleOCRProviderError(Exception):
    """Provider-level failure (transport / rejection / schema)."""


class PaddleOCRProvider:
    """Thin async-jobs client with normalized operations.

    Thread-safety: each instance owns one requests.Session; a run uses one
    provider instance (per-paper concurrency happens inside the worker).
    """

    def __init__(
        self,
        token: str,
        job_url: str = DEFAULT_JOB_URL,
        model: str = "PaddleOCR-VL-1.6",
        optional_payload: JobPayload | None = None,
        timeout: int = 120,
    ) -> None:
        self._token: str = token
        self._job_url: str = job_url.rstrip("/")
        self._model: str = model
        self._optional_payload: JobPayload = optional_payload or {}
        self._timeout: int = timeout
        self._session: requests.Session = requests.Session()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"bearer {self._token}"}

    # ── submit ──────────────────────────────────────────────────────────
    def submit(self, pdf_path: str | Path, batch_id: str | None = None) -> str:
        """Submit a local PDF; returns the provider job id.

        ``batch_id`` groups this job under one logical OCR execution
        (F2); a resubmit of the same paper keeps the batch id."""
        with open(pdf_path, "rb") as fh:
            data: dict[str, str] = {"model": self._model}
            if self._optional_payload:
                data["optionalPayload"] = json.dumps(self._optional_payload)
            if batch_id:
                data["batchId"] = batch_id
            resp = self._session.post(
                self._job_url,
                headers=self._headers(),
                data=data,
                files={"file": fh},
                timeout=self._timeout,
            )
        if resp.status_code not in (200, 201):
            raise PaddleOCRProviderError(
                f"upload rejected ({resp.status_code}): {resp.text[:300]}"
            )
        try:
            return str(resp.json()["data"]["jobId"])
        except (ValueError, KeyError) as exc:
            raise PaddleOCRProviderError(f"upload response missing jobId: {resp.text[:200]}") from exc

    # ── single-job observation ──────────────────────────────────────────
    def get_job_status(self, job_id: str) -> tuple[ProviderStatus, dict[str, object]]:
        """One job's normalized status + raw payload (fallback observer)."""
        resp = self._session.get(
            f"{self._job_url}/{job_id}", headers=self._headers(), timeout=self._timeout
        )
        if resp.status_code != 200:
            raise PaddleOCRProviderError(
                f"job status failed ({resp.status_code}): {resp.text[:200]}"
            )
        payload = resp.json().get("data", {})
        return normalize_provider_state(str(payload.get("state", ""))), payload

    # ── batch observation (F3) ──────────────────────────────────────────
    def get_batch_status(self, batch_id: str) -> dict[str, tuple[ProviderStatus, dict[str, object]]]:
        """One request for every job in a logical batch.

        Returns ``{job_id: (status, payload)}``.  The provider payload
        schema for a batch is not guaranteed to be a stable map — the
        normalizer accepts a list of job objects OR a {job_id: state} map
        and degrades to UNKNOWN entries rather than raising."""
        resp = self._session.get(
            f"{self._job_url}/batch/{batch_id}", headers=self._headers(), timeout=self._timeout
        )
        if resp.status_code != 200:
            raise PaddleOCRProviderError(
                f"batch status failed ({resp.status_code}): {resp.text[:200]}"
            )
        body = resp.json()
        data = body.get("data", body)
        out: dict[str, tuple[ProviderStatus, dict[str, object]]] = {}
        if isinstance(data, dict):
            # {job_id: "running"} or {job_id: {"state": ...}} map form
            for job_id, raw in data.items():
                if isinstance(raw, dict):
                    out[str(job_id)] = (
                        normalize_provider_state(str(raw.get("state", ""))),
                        raw,
                    )
                else:
                    out[str(job_id)] = (normalize_provider_state(str(raw)), {"state": str(raw)})
        elif isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                job_id = str(item.get("jobId") or item.get("job_id") or "")
                if not job_id:
                    continue
                out[job_id] = (
                    normalize_provider_state(str(item.get("state", ""))),
                    item,
                )
        return out

    # ── result fetch & inbound schema normalization ─────────────────────
    def fetch_result(self, result_url: str) -> list[dict[str, object]]:
        """Fetch a JSONL OCR result; one dict per page."""
        resp = self._session.get(result_url, timeout=self._timeout)
        resp.raise_for_status()
        return [json.loads(line) for line in resp.text.splitlines() if line.strip()]

    def extract_result_url(self, job_payload: dict[str, Any]) -> str | None:
        return extract_paddleocr_result_url(job_payload)

    def iter_page_results(
        self, all_results: list[dict[str, Any]]
    ) -> Iterator[dict[str, Any]]:
        return iter_paddleocr_page_results(all_results)

    def parse_page_blocks(
        self, paper_id: str, page: int, page_result: dict[str, Any]
    ) -> list[dict[str, Any]]:
        return parse_paddleocr_page_blocks(paper_id, page, page_result)

    def parse_raw_blocks(
        self, paper_id: str, all_results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return parse_paddleocr_raw_blocks(paper_id, all_results)


def extract_paddleocr_result_url(job_payload: dict[str, Any]) -> str | None:
    """Return the downloadable JSONL URL from a PaddleOCR job payload."""
    if not isinstance(job_payload, dict):
        return None
    result_url = job_payload.get("resultUrl")
    if not isinstance(result_url, dict):
        return None
    json_url = result_url.get("jsonUrl")
    return str(json_url) if json_url else None


def iter_paddleocr_page_results(
    all_results: list[dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    """Yield per-page PaddleOCR layout results across batched API payloads."""
    for payload in all_results:
        if not isinstance(payload, dict):
            continue
        for page_res in payload.get("layoutParsingResults", []) or []:
            if isinstance(page_res, dict):
                yield page_res


def parse_paddleocr_page_blocks(
    paper_id: str, page: int, page_result: dict[str, Any]
) -> list[dict[str, Any]]:
    """Normalize one PaddleOCR ``layoutParsingResults`` item into raw block rows."""
    pruned = page_result.get("prunedResult", {}) or {}
    width = pruned.get("width", 0)
    height = pruned.get("height", 0)
    blocks = pruned.get("parsing_res_list", []) or []
    rows: list[dict[str, Any]] = []
    for i, block in enumerate(blocks):
        rows.append(
            {
                "paper_id": paper_id,
                "page": page,
                "block_id": block.get("block_id", f"p{page}_b{i}"),
                "raw_label": block.get("block_label", "unknown"),
                "raw_order": block.get("block_order", i),
                "bbox": block.get("block_bbox", [0, 0, 0, 0]),
                "text": block.get("block_content", "") or "",
                "page_width": width,
                "page_height": height,
                "source": "ocr_raw",
            }
        )
    return rows


def parse_paddleocr_raw_blocks(
    paper_id: str, all_results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Normalize all PaddleOCR result payloads into canonical ``ocr_raw`` rows."""
    rows: list[dict[str, Any]] = []
    for page_num, res in enumerate(iter_paddleocr_page_results(all_results), start=1):
        rows.extend(parse_paddleocr_page_blocks(paper_id, page_num, res))
    return rows
