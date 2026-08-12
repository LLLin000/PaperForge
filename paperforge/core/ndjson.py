"""#137 structured-stream emission — NDJSON events, exactly one terminal.

stdout carries machine output only (UTF-8, one JSON object per line,
``schema_version: 1``, ``event`` discriminator required); stderr carries
human logs.  A stream ends with EXACTLY ONE terminal event
(result | error | cancelled) then EOF.

The old colon-token family (EMBED_START/…, OCR_REBUILD_*, OCR_REDO_*,
DONE, NOTICE) is retired — no token + NDJSON dual parsing.
"""

from __future__ import annotations

import json
from typing import Any


def emit(event: str, operation: str, **fields: Any) -> None:
    """Emit one NDJSON event line to stdout (machine output only)."""
    payload: dict[str, Any] = {
        "schema_version": 1,
        "event": event,
        "operation": operation,
        **fields,
    }
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def emit_start(operation: str, total: int | None = None, scope: Any = None) -> None:
    emit("start", operation, total=total, scope=scope)


def emit_phase(operation: str, phase: str) -> None:
    emit("phase", operation, phase=phase)


def emit_progress(operation: str, current: int, total: int, item_id: str | None = None) -> None:
    emit("progress", operation, current=current, total=total, item_id=item_id)


def emit_item_result(operation: str, item_id: str, status: str) -> None:
    emit("item_result", operation, item_id=item_id, status=status)


def emit_terminal(event: str, operation: str, pfresult: Any) -> None:
    """Exactly-one terminal event; payload is the existing PFResult."""
    from paperforge.core.result import PFResult

    result = pfresult.to_dict() if isinstance(pfresult, PFResult) else pfresult
    emit(event, operation, result=result)
