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
        for key in ("id", "domain_id", "rule_id", "unit_id", "signal_id", "operation_id", "finding_id"):
            if key in item and isinstance(item[key], str):
                return item[key]
    return None


def _canonical(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        items = [_canonical(item) for item in value]
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


def finding_id(rule_id: str, subjects: list[str], evidence_symbols: list[str]) -> str:
    """Finding identity derived from rule + normalized subjects + evidence symbols.

    Line numbers do not participate, so moving code keeps the finding id stable;
    renaming the rule or subject changes it.
    """
    return stable_id(
        "finding",
        rule_id,
        *sorted(set(subjects)),
        *sorted(set(evidence_symbols)),
    )
