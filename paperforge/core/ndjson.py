"""#137 structured-stream emission — NDJSON events, exactly one terminal.

stdout carries machine output only (UTF-8, one JSON object per line,
``schema_version: 1``, ``event`` discriminator required); stderr carries
human logs.  A stream ends with EXACTLY ONE terminal event
(result | error | cancelled) then EOF.

The old colon-token family (EMBED_START/…, OCR_REBUILD_*, OCR_REDO_*,
DONE, NOTICE) is retired — no token + NDJSON dual parsing.

M2-E (Control Plane Closure): the STANDARDIZED event vocabulary — the
six core event types every long task emits; domain code renders nothing
itself, renderers (Rich/text, NDJSON, terminal) consume the same stream:

    start          — operation begins (total)
    preflight      — availability/applicability summary before work
    progress       — completed/total
    paper_settled  — one paper settled (key, outcome, reason_code?)
    heartbeat      — periodic liveness (active, pending)
    terminal       — EXACTLY ONE final result (result|error|cancelled)

``phase`` / ``item_result`` remain available as extensions; consumers
must tolerate unknown event types (forward compatibility).
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


def emit_preflight(
    operation: str,
    *,
    availability: str,
    needed: int = 0,
    noop: int = 0,
    blocked: int = 0,
    not_applicable: int = 0,
) -> None:
    """M2-E: availability + applicability summary before work starts."""
    emit(
        "preflight",
        operation,
        availability=availability,
        summary={"needed": needed, "noop": noop, "blocked": blocked, "not_applicable": not_applicable},
    )


def emit_paper_settled(
    operation: str,
    key: str,
    outcome: str,
    reason_code: str | None = None,
) -> None:
    """M2-E: one paper reached a terminal/non-terminal outcome."""
    fields: dict[str, Any] = {"key": key, "outcome": outcome}
    if reason_code:
        fields["reason_code"] = reason_code
    emit("paper_settled", operation, **fields)


def emit_heartbeat(operation: str, active: int, pending: int) -> None:
    """M2-E: periodic liveness while waiting on remote work."""
    emit("heartbeat", operation, active=active, pending=pending)


def emit_item_result(operation: str, item_id: str, status: str) -> None:
    emit("item_result", operation, item_id=item_id, status=status)


def emit_terminal(event: str, operation: str, pfresult: Any) -> None:
    """Exactly-one terminal event; payload is the existing PFResult."""
    from paperforge.core.result import PFResult

    result = pfresult.to_dict() if isinstance(pfresult, PFResult) else pfresult
    emit(event, operation, result=result)
