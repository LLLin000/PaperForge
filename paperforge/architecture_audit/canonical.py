"""Canonical serialization, semantic digests, and stable deterministic IDs.

Canonicalization contract (#131):
- UTF-8 output.
- Object keys recursively sorted.
- Lists whose items carry a domain id are ordered by that id; other lists are
  ordered by their canonical JSON (fully deterministic).
- Paths stay POSIX-style and repository-relative.
- Run metadata (generated_at, revision, tool versions) never enters a digest.

`semantic_digest` therefore changes only when observed/declared semantics change.
"""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any

ID_SEPARATOR = "\x1f"


def _id_of(item: Any) -> str | None:
    if isinstance(item, dict):
        for key in (
            "id",
            "domain_id",
            "group_id",
            "rule_id",
            "unit_id",
            "operation_id",
            "interface_id",
            "trace_id",
            "signal_id",
            "unresolved_id",
            "candidate_id",
            "wrapper_id",
            "evidence_id",
            "finding_id",
        ):
            if key in item and isinstance(item[key], str):
                return item[key]
    return None


# Lists named by these keys are sequences, not sets.  In particular, Rule.scope
# has historically carried an ordered role selector; sorting every list would
# make two contracts with different reconciliation behavior share a digest.
_ORDERED_LIST_KEYS = frozenset({"scope"})


def _canonical(value: Any, *, key: str | None = None) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {
            str(name): _canonical(item, key=str(name))
            for name, item in sorted(value.items(), key=lambda kv: str(kv[0]))
        }
    if isinstance(value, (list, tuple)):
        items = [_canonical(item) for item in value]
        if key in _ORDERED_LIST_KEYS:
            return items
        return sorted(items, key=_list_sort_key)
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    return value


def _list_sort_key(item: Any) -> tuple[bool, str]:
    """Canonical list order: domain-id items by id, others by canonical JSON."""
    domain_id = _id_of(item)
    if domain_id is not None:
        return (False, domain_id)
    return (True, json.dumps(item, ensure_ascii=False, sort_keys=True))




def canonical_json(value: Any) -> str:
    """Deterministic JSON string for semantic content."""
    return json.dumps(_canonical(value), ensure_ascii=False, separators=(",", ":"))


def sha256_digest(payload: str) -> str:
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def semantic_digest(content: dict[str, Any]) -> str:
    """Digest of canonical semantic content. Run metadata must not be included."""
    return sha256_digest(canonical_json(content))


def stable_id(prefix: str, *parts: str) -> str:
    """Deterministic domain id: sha256 over normalized parts, stable under line moves."""
    payload = ID_SEPARATOR.join(parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{digest}"


def finding_id(
    rule_id: str,
    subjects: list[str],
    evidence_symbols: list[str | dict[str, str]],
) -> str:
    """Return a collision-resistant finding id.

    Subjects and evidence are separate named fields, and evidence identity
    includes its repository file.  Line numbers are intentionally absent.
    String evidence values remain supported for callers that only have a
    qualified symbol; reconciler callers pass ``{"file", "symbol"}`` objects.
    """
    evidence: list[dict[str, str]] = []
    for value in evidence_symbols:
        if isinstance(value, dict):
            evidence.append({
                "file": value.get("file", ""),
                "symbol": value.get("symbol", ""),
            })
        else:
            evidence.append({"file": "", "symbol": value})
    payload = {
        "rule_id": rule_id,
        "subjects": sorted(set(subjects)),
        "evidence": sorted(
            {json.dumps(item, ensure_ascii=False, sort_keys=True) for item in evidence}
        ),
    }
    return stable_id("finding", canonical_json(payload))
