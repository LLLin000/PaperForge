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

import json
from enum import Enum
from pathlib import Path

import requests

DEFAULT_JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"

# Provider payloads are dynamic JSON; expose them as object-valued dicts so
# callers cast at the boundary (no object leaking into annotations).
JobPayload = dict[str, object]


class ProviderStatus(str, Enum):
    """Normalized provider job state — the only status vocabulary the rest
    of PaperForge ever sees."""

    QUEUED = "queued"      # submitted, waiting in provider queue
    RUNNING = "running"    # provider processing
    DONE = "done"          # provider finished, result URL available
    FAILED = "failed"      # provider terminal failure
    UNKNOWN = "unknown"    # unrecognized / unreadable state


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

    # ── result fetch ────────────────────────────────────────────────────
    def fetch_result(self, result_url: str) -> list[dict[str, object]]:
        """Fetch a JSONL OCR result; one dict per page."""
        resp = self._session.get(result_url, timeout=self._timeout)
        resp.raise_for_status()
        return [json.loads(line) for line in resp.text.splitlines() if line.strip()]
