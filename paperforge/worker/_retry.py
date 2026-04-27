from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import tenacity

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (requests.ConnectionError, requests.Timeout)):
        return True
    if isinstance(exc, requests.HTTPError):
        return exc.response is not None and exc.response.status_code in (429, 503)
    return False


def configure_retry():
    max_str = os.environ.get("PAPERFORGE_RETRY_MAX", "5")
    backoff_str = os.environ.get("PAPERFORGE_RETRY_BACKOFF", "2.0")
    try:
        retry_max = int(max_str)
    except (ValueError, TypeError):
        retry_max = 5
    try:
        backoff = float(backoff_str)
    except (ValueError, TypeError):
        backoff = 2.0
    return tenacity.retry(
        stop=tenacity.stop_after_attempt(retry_max),
        wait=tenacity.wait_exponential(multiplier=backoff, min=1, max=30),
        retry=tenacity.retry_if_exception(_is_retryable),
        reraise=True,
        before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
    )


def retry_with_meta(fn: Callable, meta_path: Path, *args, **kwargs) -> Any:
    max_str = os.environ.get("PAPERFORGE_RETRY_MAX", "5")
    backoff_str = os.environ.get("PAPERFORGE_RETRY_BACKOFF", "2.0")
    try:
        retry_max = int(max_str)
    except (ValueError, TypeError):
        retry_max = 5
    try:
        backoff = float(backoff_str)
    except (ValueError, TypeError):
        backoff = 2.0

    def _update_meta(retry_state: tenacity.RetryCallState) -> None:
        attempt = retry_state.attempt_number
        outcome = retry_state.outcome
        meta = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        meta["retry_count"] = attempt
        meta["last_error"] = str(outcome.exception()) if outcome and outcome.failed else None
        meta["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    for attempt in tenacity.Retrying(
        stop=tenacity.stop_after_attempt(retry_max),
        wait=tenacity.wait_exponential(multiplier=backoff, min=1, max=30),
        retry=tenacity.retry_if_exception(_is_retryable),
        reraise=True,
        before_sleep=_update_meta,
    ):
        with attempt:
            return fn(*args, **kwargs)
