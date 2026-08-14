"""Vector substrate observation — the SINGLE source of truth for
global vs per-paper embedding operation classification (#159 §2.2).

Layer discipline (owner review 2026-08-11, #166 corrective):
    materialization/substrate  ≠  action availability

- Credential availability belongs to ActionPreflight (registry) — NEVER here.
  A missing/locked credential does NOT make the substrate incompatible, and
  must not block unrelated OCR/retrieval repair.
- This module observes DESIRED embedding identity (config) vs PUBLISHED
  substrate identity/layout (build_state + vec0 DDL), read-only, no side
  effects, no network.

Consumers (one contract, no drifting copies):
    T5 reconcile        — global vector observation
    T4 embed run_build  — requires_shadow routing
    embed.resume preflight — availability

Compatible substrate  → per-paper vector facets decide operation
                        (missing/stale → embed.resume(keys)).
Incompatible substrate → exactly one GLOBAL embed.build(all):
    model changed / endpoint changed / layout incompatible / legacy identity.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

# Legacy libraries (built before identity recording) have no
# vector_identity_version — rebuild once so endpoint/model are persisted
# and future comparisons are meaningful.
VECTOR_IDENTITY_VERSION = 1


@dataclass(frozen=True)
class VectorSubstrate:
    """Read-only assessment of the published vector substrate."""

    db_exists: bool
    has_any_rows: bool
    identity_changed: bool
    layout_incompatible: bool
    legacy_identity: bool
    compatible: bool
    reason_codes: tuple[str, ...]
    stored_model: str
    current_model: str
    stored_endpoint: str
    current_endpoint: str
    stored_dimension: int
    identity_version: int


def _read_build_state_ro(conn: sqlite3.Connection) -> dict:
    """Read build_state rows into a plain dict (read-only connection)."""
    try:
        rows = conn.execute("SELECT key, value FROM build_state").fetchall()
    except sqlite3.OperationalError:
        return {}
    out: dict = {}
    for key, value in rows:
        try:
            out[key] = json.loads(value) if not isinstance(value, str) or value == "" else value
        except (TypeError, ValueError):
            out[key] = value
    return out


def _has_any_rows(conn: sqlite3.Connection) -> bool:
    for table in ("vec_fulltext_meta", "vec_body_meta", "vec_objects_meta"):
        try:
            row = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()
        except sqlite3.OperationalError:
            continue
        if row and row[0] > 0:
            return True
    return False


def effective_vector_db(vault: Path) -> Path:
    """Return the DB that holds the CURRENT vector truth.

    RC UX Seam (single source): a shadow build writes ONLY to the candidate
    (.db.build) until publish swaps it into live — so during an
    interrupted/failed/in-flight shadow, the candidate is the ONLY place
    with real rows and a real build_state.  Every observer (substrate,
    build_state reads, embed status, probe) must look at the SAME file:
    candidate when it has rows, else live.

    Returns the candidate path when it exists AND has vector rows; live
    otherwise.  Never guesses — an empty/absent candidate falls back to live.
    """
    from paperforge.memory.db import get_memory_db_path

    live = get_memory_db_path(vault)
    candidate = live.with_suffix(".db.build")
    if candidate.exists():
        try:
            conn = sqlite3.connect(f"file:{candidate.as_posix()}?mode=ro", uri=True)
            try:
                if _has_any_rows(conn):
                    return candidate
            finally:
                conn.close()
        except Exception:  # noqa: BLE001 — unreadable candidate falls back
            pass
    return live


def assess_vector_substrate(vault: Path, *, db_path: Path | None = None) -> VectorSubstrate:
    """Pure observation of desired-vs-published embedding substrate.

    Fail-closed: an unreadable DB/layout is treated as incompatible (routes
    to global embed.build), never as compatible.
    """
    from paperforge.embedding._config import (
        DEFAULT_OPENAI_BASE_URL,
        get_api_model,
        get_effective_api_base_url,
    )

    from paperforge.memory.db import get_memory_db_path

    # RC UX Seam: observe the EFFECTIVE carrier (candidate-with-rows first,
    # else live) so an interrupted shadow is seen as the truth it is, not as
    # the stale live snapshot behind it.
    db_path = db_path or effective_vector_db(vault)
    db_exists = db_path.exists()
    reason_codes: list[str] = []

    stored_model = ""
    stored_endpoint = ""
    stored_dimension = 0
    identity_version = 0
    has_any_rows = False
    layout_incompatible = False

    if db_exists:
        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        try:
            bs = _read_build_state_ro(conn)
            stored_model = str(bs.get("model", "") or "")
            stored_endpoint = str(bs.get("vector_provider_endpoint", "") or "")
            stored_dimension = int(bs.get("vector_dimension", 0) or 0)
            identity_version = int(bs.get("vector_identity_version", 0) or 0)
            has_any_rows = _has_any_rows(conn)
            if stored_dimension:
                try:
                    from paperforge.memory.db import ensure_vec_extension

                    ensure_vec_extension(conn)
                except Exception:  # noqa: BLE001
                    # No vec0 capability (extension cannot load) == vec0
                    # never built — NOT a substrate incompatibility; the
                    # per-paper missing facet routes to embed.resume, which
                    # self-ensures vec0 when the extension is present.
                    pass
                else:
                    try:
                        from paperforge.embedding.dim_detect import inspect_vector_layout

                        layout = inspect_vector_layout(conn, stored_dimension)
                        # Owner review (#166): vec0 tables NEVER built is NOT
                        # a substrate incompatibility — that is a per-paper
                        # missing deficit (embed.resume repairs it,
                        # self-ensuring vec0).  Only a PARTIAL/incompatible
                        # layout (some tables exist but dims/counts
                        # disagree) is a global defect.
                        all_missing = len(layout.missing) >= len(layout.dimensions or ())
                        layout_incompatible = not all_missing and not layout.compatible
                        if layout_incompatible:
                            reason_codes.append(f"vector.layout({layout.reason or 'incompatible'})")
                    except Exception:  # noqa: BLE001 — fail-closed
                        layout_incompatible = True
                        reason_codes.append("vector.layout_unreadable")
        finally:
            conn.close()
    else:
        reason_codes.append("vector.db_missing")

    current_model = get_api_model(vault) or ""
    current_endpoint = (get_effective_api_base_url(vault) or "").rstrip("/")

    # P0-1 (#166): compare the EFFECTIVE endpoint (empty config = OpenAI
    # default) with NO truthiness guard — default→custom migration must
    # trigger global rebuild, and an empty stored value (old build before
    # endpoint recording) counts as "different" when a custom endpoint is
    # now configured.
    stored_endpoint_norm = (stored_endpoint or DEFAULT_OPENAI_BASE_URL).rstrip("/")
    identity_changed = bool(
        stored_model and current_model and stored_model != current_model
    ) or (stored_endpoint_norm != current_endpoint)
    if identity_changed:
        reason_codes.append(
            f"vector.identity_changed({stored_model}@{stored_endpoint_norm}->{current_model}@{current_endpoint})"
        )

    # #167 P0-4: legacy requires evidence of a PUBLISHED vector
    # materialization — a pristine substrate (no rows, no identity) is a
    # per-paper missing deficit, never a legacy global rebuild.
    legacy_identity = bool(
        identity_version != VECTOR_IDENTITY_VERSION
        and db_exists
        and has_any_rows
        and not layout_incompatible
    )
    if legacy_identity:
        reason_codes.append(f"vector.legacy_identity({identity_version}->{VECTOR_IDENTITY_VERSION})")

    compatible = db_exists and not (identity_changed or layout_incompatible or legacy_identity)
    if compatible:
        reason_codes.append("vector.compatible")

    return VectorSubstrate(
        db_exists=db_exists,
        has_any_rows=has_any_rows,
        identity_changed=identity_changed,
        layout_incompatible=layout_incompatible,
        legacy_identity=legacy_identity,
        compatible=compatible,
        reason_codes=tuple(reason_codes),
        stored_model=stored_model,
        current_model=current_model,
        stored_endpoint=stored_endpoint,
        current_endpoint=current_endpoint,
        stored_dimension=stored_dimension,
        identity_version=identity_version,
    )
