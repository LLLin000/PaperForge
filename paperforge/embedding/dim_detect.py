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
    from paperforge.embedding._config import get_api_model, get_effective_api_base_url

    try:
        return f"{get_effective_api_base_url(vault)}|{get_api_model(vault)}"
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

    # Try reading from existing vec0 table DDL first — no API call needed.
    # RC UX Seam: the DDL dimension is ONLY trustworthy when the table was
    # built under the CURRENT embedding identity.  After a model/endpoint
    # switch the old table still says its old dim (e.g. 1536), so trusting
    # it would make ensure_vec_tables think the layout is compatible and
    # never recreate — then the new model's API returns 2560 and every
    # insert fails with Dimension mismatch.  Identity check (build_state
    # model/endpoint vs config) before honoring the DDL.
    if conn is not None:
        _ddl_identity_ok = False
        try:
            from paperforge.embedding._config import (
                get_api_model as _cfg_model,
                get_effective_api_base_url as _cfg_base,
            )

            _stored_model = ""
            _stored_endpoint = ""
            try:
                _row = conn.execute(
                    "SELECT value FROM build_state WHERE key='model'"
                ).fetchone()
                if _row:
                    _stored_model = str(_row[0] or "")
                _row = conn.execute(
                    "SELECT value FROM build_state WHERE key='vector_provider_endpoint'"
                ).fetchone()
                if _row:
                    _stored_endpoint = str(_row[0] or "")
            except Exception:
                pass
            # Identity matches only when BOTH model and endpoint agree.
            _ddl_identity_ok = bool(
                _stored_model
                and _stored_model == _cfg_model(vault)
                and _stored_endpoint
                and _stored_endpoint == _cfg_base(vault)
            )
        except Exception:  # noqa: BLE001
            _ddl_identity_ok = False
        if _ddl_identity_ok:
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
    unreadable: tuple[str, ...]
    dimensions: dict[str, int | None]     # vec table -> dim (None = absent/unknown)
    counts: dict[str, tuple[int, int]]    # vec table -> (vec_rows, meta_rows)
    compatible: bool
    reason: str

    @property
    def total_vec_rows(self) -> int:
        return sum(vc for vc, _ in self.counts.values())

    @property
    def total_meta_rows(self) -> int:
        return sum(mc for _, mc in self.counts.values())

    @property
    def has_any_rows(self) -> bool:
        """P0-2: EMPTY means vec AND meta are both zero everywhere.  A
        damaged state (vec has rows but meta is missing/unreadable) is NOT
        empty — it must never be treated as a fresh library."""
        return self.total_vec_rows > 0 or self.total_meta_rows > 0


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
    unreadable: list[str] = []
    dims: dict[str, int | None] = {}
    counts: dict[str, tuple[int, int]] = {}
    reasons: list[str] = []
    for vec, meta in VEC_PAIRS:
        # P0-2: vec and meta are read SEPARATELY — a failure reading one must
        # not zero out the other's already-read count (that would turn a
        # damaged library into a fake "empty" one).
        try:
            row = conn.execute(
                f"SELECT sql FROM sqlite_master WHERE name='{vec}' AND type='table'"
            ).fetchone()
        except Exception as exc:  # noqa: BLE001
            unreadable.append(vec)
            dims[vec] = None
            counts[vec] = (0, 0)
            reasons.append(f"{vec} unreadable: {exc}")
            continue
        if not row:
            missing.append(vec)
            dims[vec] = None
            counts[vec] = (0, 0)
            continue
        m = _re.search(r"float\[(\d+)\]", row[0])
        dims[vec] = int(m.group(1)) if m else None
        try:
            vc = conn.execute(f"SELECT COUNT(*) FROM {vec}").fetchone()[0]
        except Exception as exc:  # noqa: BLE001
            unreadable.append(vec)
            counts[vec] = (0, 0)
            reasons.append(f"{vec} count unreadable: {exc}")
            continue
        try:
            mc = conn.execute(f"SELECT COUNT(*) FROM {meta}").fetchone()[0]
        except Exception as exc:  # noqa: BLE001
            # vec rows exist but meta is broken → damaged, NOT empty.
            unreadable.append(meta)
            counts[vec] = (vc, 0)
            reasons.append(f"{meta} unreadable: {exc}")
            continue
        counts[vec] = (vc, mc)
        # NOTE: vec0 COUNT(*) includes deleted rows (rowid tombstones) — a
        # raw count comparison is meaningless on sqlite-vec.  The reliable
        # integrity signal is ORPHAN META: a meta row whose vec row is
        # missing means real corruption (dropped vec table, lost rows).
        #
        # The full orphan check (LEFT JOIN meta ⋈ vec0) is O(rows × vec0)
        # on sqlite-vec — measured 48–117 s at 16k/6.7k rows because vec0
        # rowid lookups are slow (asg017/sqlite-vec #37/#196).  It ran on
        # every probe/status call, so a fully built library made every
        # reader hang for minutes (2026-08-14: process pile-up, false
        # 'database is locked', embed build appearing to hang after
        # publish).  Replacement: meta rows whose rowid exceeds the vec0
        # max are provably orphaned — vec0 rowids are handed out by
        # INSERT (lastrowid) and only grow, so a table rebuilt/dropped
        # leaves every stale meta rowid above the new max.  This is O(1)
        # (3 ms) and catches the only realistic corruption mode (vec table
        # dropped/recreated).  A full 100% scan stays available as a
        # manual maintenance command.
        try:
            vec_max = conn.execute(
                f"SELECT COALESCE(MAX(rowid), 0) FROM {vec}"
            ).fetchone()[0]
            orphan = conn.execute(
                f"SELECT COUNT(*) FROM {meta} WHERE rowid > ?", (vec_max,)
            ).fetchone()[0]
            if orphan:
                reasons.append(f"{meta} has {orphan} rowids beyond vec0 max {vec_max}")
        except Exception as exc:  # noqa: BLE001
            unreadable.append(meta)
            reasons.append(f"{meta} orphan check unreadable: {exc}")
    tables_complete = not missing
    if missing:
        reasons.append(f"missing tables: {missing}")
    if unreadable:
        reasons.append(f"unreadable: {unreadable}")
    if required_dim is not None:
        for vec in ("vec_fulltext", "vec_body", "vec_objects"):
            d = dims.get(vec)
            if d is not None and d != required_dim:
                reasons.append(f"{vec} dimension {d} != required {required_dim}")
    return VectorLayout(
        tables_complete=tables_complete,
        missing=tuple(missing),
        unreadable=tuple(unreadable),
        dimensions=dims,
        counts=counts,
        compatible=not reasons,
        reason="; ".join(reasons) or "ok",
    )


def ensure_vec_tables(conn, vault: Path, *, allow_recreate: bool = False) -> int:
    """Ensure vec0 virtual tables match the model's dimension.

    ``allow_recreate=True`` (shadow candidate, fresh DB) may drop/recreate
    the vec0 tables.  On the live incremental path (``allow_recreate=False``)
    a dimension mismatch raises :class:`VectorRebuildRequired` instead of
    destroying live vectors — the caller must route to a shadow rebuild.

    Returns the dimension actually in effect — callers MUST use this as
    the expected dimension for verification (never re-derive it from the
    candidate DDL, which would be self-verification, P1-2).
    """
    from paperforge.memory.db import ensure_vec_extension

    ensure_vec_extension(conn)

    # Detect required dimension
    required_dim = detect_embedding_dim(vault)

    layout = inspect_vector_layout(conn, required_dim)
    if layout.compatible and layout.tables_complete:
        return required_dim  # already correct

    if not allow_recreate:
        # P0-2: unreadable tables are unknown/corrupt — never treat them as
        # empty.  EMPTY means vec AND meta are both zero everywhere; only
        # that state may be initialized in place (a first build).  Any real
        # rows mean existing data that an in-place drop would destroy.
        if layout.unreadable:
            raise VectorRebuildRequired(
                f"vector layout unreadable: {layout.reason} — shadow rebuild required"
            )
        if layout.has_any_rows:
            raise VectorRebuildRequired(
                f"vector layout incompatible: {layout.reason} — "
                "in-place recreate would destroy live vectors; shadow rebuild required"
            )
        allow_recreate = True

    # Drop and recreate with correct dimension (shadow candidate / fresh DB)
    for name in ("vec_fulltext", "vec_body", "vec_objects"):
        try:
            conn.execute(f"DROP TABLE IF EXISTS \"{name}\"")
        except Exception:
            pass
        ddl = f"CREATE VIRTUAL TABLE IF NOT EXISTS \"{name}\" USING vec0(embedding float[{required_dim}]);"
        conn.execute(ddl)

    logger.info("Recreated vec0 tables with dimension %d", required_dim)
    return required_dim
