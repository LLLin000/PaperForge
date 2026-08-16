"""M2-D (Control Plane Closure): standardized per-key settlement.

Every paper-scope action reports its outcome through ONE vocabulary and
ONE shape; summary and successful_keys are DERIVED from per_key (never a
second truth — a handler can no longer report 24 succeeded in per_key
while successful_keys lists 23).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Literal

SettlementOutcome = Literal[
    "succeeded",
    "noop",
    "pending",
    "blocked",
    "failed",
    "cancelled",
]

_OUTCOME_COUNTS = ("succeeded", "noop", "pending", "blocked", "failed", "cancelled")


def successful_keys(per_key: Mapping[str, str]) -> list[str]:
    """The ONLY source of successful_keys: derived from per_key outcomes."""
    return sorted(k for k, outcome in per_key.items() if outcome == "succeeded")


def settlement_payload(
    per_key: Mapping[str, str],
    *,
    reason_codes: Mapping[str, str] | None = None,
    execution_ids: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Build the standardized settlement payload.

    ``per_key``: {key: outcome}.  Optional per-key reason codes /
    execution ids ride along.  summary counts are derived here — callers
    must not supply their own summary.
    """
    counts = Counter(per_key.values())
    summary = {o: counts.get(o, 0) for o in _OUTCOME_COUNTS}
    per_key_out: dict[str, dict[str, object]] = {}
    for key, outcome in per_key.items():
        entry: dict[str, object] = {"outcome": outcome}
        if reason_codes and key in reason_codes:
            entry["reason_code"] = reason_codes[key]
        if execution_ids and key in execution_ids:
            entry["execution_id"] = execution_ids[key]
        per_key_out[key] = entry
    return {
        "summary": summary,
        "per_key": per_key_out,
        "successful_keys": successful_keys(per_key),
    }
