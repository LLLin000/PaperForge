"""Detect embedding dimension from the configured model at runtime."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Optional

from paperforge.embedding.providers.openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

_DETECTED_DIM: Optional[int] = None
_DETECTED_DIM_KEY: Optional[str] = None


def _dim_cache_key(vault: Path) -> str:
    """Dimension cache key: provider endpoint + model (per #117 D4)."""
    from paperforge.embedding._config import get_api_base_url, get_api_model

    try:
        return f"{get_api_base_url(vault)}|{get_api_model(vault)}"
    except Exception:
        return f"{vault}"


def reset_dim_cache() -> None:
    """Clear the process-level dimension cache (model switch / tests)."""
    global _DETECTED_DIM, _DETECTED_DIM_KEY
    _DETECTED_DIM = None
    _DETECTED_DIM_KEY = None


def set_dim_cache(dim: int, vault: Path) -> None:
    """Pin the dimension cache (used with first real payload length)."""
    global _DETECTED_DIM, _DETECTED_DIM_KEY
    _DETECTED_DIM = dim
    _DETECTED_DIM_KEY = _dim_cache_key(vault)


def detect_embedding_dim(vault: Path, conn: sqlite3.Connection | None = None) -> int:
    """Detect the embedding dimension.

    Priority:
    1. Process-global cache keyed by (provider endpoint, model)
    2. Existing vec0 table DDL (no API needed)
    3. Embedding API call (fallback)
    """
    global _DETECTED_DIM, _DETECTED_DIM_KEY
    key = _dim_cache_key(vault)
    if _DETECTED_DIM is not None and _DETECTED_DIM_KEY == key:
        return _DETECTED_DIM

    # Try reading from existing vec0 table DDL first — no API call needed
    if conn is not None:
        try:
            row = conn.execute("SELECT sql FROM sqlite_master WHERE name='vec_body' AND type='table'").fetchone()
            if row:
                import re
                m = re.search(r"float\[(\d+)\]", row[0])
                if m:
                    dim = int(m.group(1))
                    _DETECTED_DIM = dim
                    _DETECTED_DIM_KEY = key
                    logger.info("Detected embedding dimension: %d (from vec0 DDL)", dim)
                    return dim
        except Exception:
            pass

    provider = OpenAICompatibleProvider(vault)
    test_vec = provider.encode_single("dimension detection probe")
    dim = len(test_vec)
    logger.info("Detected embedding dimension: %d (model: %s)", dim, getattr(provider, "model", "unknown"))
    _DETECTED_DIM = dim
    _DETECTED_DIM_KEY = key
    return dim

class VectorRebuildRequired(RuntimeError):
    """The live DB's vector layout is incompatible with the current model —
    an in-place drop would expose an empty/partial window.  Route through a
    shadow rebuild instead (P0-3)."""


@dataclass(frozen=True)
class VectorLayout:
    """Single source of truth for vec0 layout checks (P1-1).

    Used by requires_shadow routing, ensure_vec_tables, verify_candidate and
    status — one contract instead of three drifting ad-hoc checks.
    """

    tables_complete: bool
    missing: tuple[str, ...]
    dimensions: dict[str, int | None]     # vec table -> dim (None = absent/unknown)
    counts: dict[str, tuple[int, int]]    # vec table -> (vec_rows, meta_rows)
    compatible: bool
    reason: str

    @property
    def total_meta_rows(self) -> int:
        return sum(mc for _, mc in self.counts.values())


VEC_PAIRS: tuple[tuple[str, str], ...] = (
    ("vec_fulltext", "vec_fulltext_meta"),
    ("vec_body", "vec_body_meta"),
    ("vec_objects", "vec_objects_meta"),
)


def inspect_vector_layout(conn, required_dim: int | None = None) -> VectorLayout:
    """Inspect the six vec/meta tables: presence, per-table dimension, and
    vec==meta row counts.  Missing tables are NOT silently tolerated when
    required_dim is given (empty-but-complete schema is legal; absent schema
    is not)."""
    import re as _re

    from paperforge.memory.db import ensure_vec_extension

    ensure_vec_extension(conn)
    missing: list[str] = []
    dims: dict[str, int | None] = {}
    counts: dict[str, tuple[int, int]] = {}
    reasons: list[str] = []
    for vec, meta in VEC_PAIRS:
        try:
            row = conn.execute(
                f"SELECT sql FROM sqlite_master WHERE name='{vec}' AND type='table'"
            ).fetchone()
            if not row:
                missing.append(vec)
                dims[vec] = None
                counts[vec] = (0, 0)
                continue
            m = _re.search(r"float\[(\d+)\]", row[0])
            dims[vec] = int(m.group(1)) if m else None
            vc = conn.execute(f"SELECT COUNT(*) FROM {vec}").fetchone()[0]
            mc = conn.execute(f"SELECT COUNT(*) FROM {meta}").fetchone()[0]
            counts[vec] = (vc, mc)
            if vc != mc:
                reasons.append(f"{vec}/{meta} count mismatch {vc} vs {mc}")
        except Exception as exc:  # noqa: BLE001 — layout check must not crash
            missing.append(vec)
            dims[vec] = None
            counts[vec] = (0, 0)
            reasons.append(f"{vec} unreadable: {exc}")
    tables_complete = not missing
    if missing:
        reasons.append(f"missing tables: {missing}")
    if required_dim is not None:
        for vec in ("vec_fulltext", "vec_body", "vec_objects"):
            d = dims.get(vec)
            if d is not None and d != required_dim:
                reasons.append(f"{vec} dimension {d} != required {required_dim}")
    return VectorLayout(
        tables_complete=tables_complete,
        missing=tuple(missing),
        dimensions=dims,
        counts=counts,
        compatible=not reasons,
        reason="; ".join(reasons) or "ok",
    )


def ensure_vec_tables(conn, vault: Path, *, allow_recreate: bool = False) -> None:
    """Ensure vec0 virtual tables match the model's dimension.

    ``allow_recreate=True`` (shadow candidate, fresh DB) may drop/recreate
    the vec0 tables.  On the live incremental path (``allow_recreate=False``)
    a dimension mismatch raises :class:`VectorRebuildRequired` instead of
    destroying live vectors — the caller must route to a shadow rebuild.
    """
    from paperforge.memory.db import ensure_vec_extension

    ensure_vec_extension(conn)

    # Detect required dimension
    required_dim = detect_embedding_dim(vault)

    layout = inspect_vector_layout(conn, required_dim)
    if layout.compatible and layout.tables_complete:
        return  # already correct

    if not allow_recreate:
        # P1-2: an EMPTY library (no vector rows anywhere) is a first build —
        # safe to initialize the correct dimension in place under the writer
        # lock.  Only a library that ALREADY HAS vectors is protected from
        # in-place recreation (that would destroy them + orphan meta rows).
        if layout.total_meta_rows == 0:
            allow_recreate = True
        else:
            raise VectorRebuildRequired(
                f"vector layout incompatible: {layout.reason} — "
                "in-place recreate would destroy live vectors; shadow rebuild required"
            )

    # Drop and recreate with correct dimension (shadow candidate / fresh DB)
    for name in ("vec_fulltext", "vec_body", "vec_objects"):
        try:
            conn.execute(f"DROP TABLE IF EXISTS \"{name}\"")
        except Exception:
            pass
        ddl = f"CREATE VIRTUAL TABLE IF NOT EXISTS \"{name}\" USING vec0(embedding float[{required_dim}]);"
        conn.execute(ddl)

    logger.info("Recreated vec0 tables with dimension %d", required_dim)
