"""Digest lineage identities and the lineage probe read model (#162 / T1).

Content-addressed lineage per #159 §2.3: identities are digests, never
counters.  Identical rebuild → identical digest (change-prune basis).

    OCR identity        = result_hash (published per paper, #126)
    Retrieval identity  = sha256(ocr identity + retrieval policy identity
                                 + canonical produced-unit digests)
    Vector identity     = sha256(retrieval identity + embedding identity)

`probe lineage --json` fails closed: unknown/unobserved lineage is a
first-class state and is never interpreted as stale.  No auto-rebuild path
exists anywhere in this module.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paperforge.worker.ocr_hash import compute_ocr_result_hash

# The embedding provider is the openai-compatible provider seam; its endpoint
# is semantically identity-bearing (different endpoints → different embedding
# spaces), so it participates in the canonical identity.
EMBEDDING_PROVIDER = "openai_compatible"

LINEAGE_LAYER_VECTOR = "vector"

# Stable marker for vectors migrated from the legacy ChromaDB full-text
# collection (1.5.x-era products, no structure tree / manifest).  The
# derived_from column carries this sentinel instead of a retrieval identity;
# the probe treats it as the legacy-fulltext path (identity match ⇒ same
# embedding config ⇒ searchable; mismatch ⇒ model/config changed ⇒ rebuild).
LEGACY_FULLTEXT_RETRIEVAL_ID = "legacy-fulltext-v1"

LINEAGE_TABLE = """
CREATE TABLE IF NOT EXISTS lineage (
    paper_id            TEXT NOT NULL,
    layer               TEXT NOT NULL,
    identity            TEXT NOT NULL,
    derived_from        TEXT,
    embedding_identity  TEXT,
    updated_at          TEXT NOT NULL,
    PRIMARY KEY (paper_id, layer)
);
"""


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")


def compute_retrieval_identity(
    *,
    ocr_result_hash: str,
    retrieval_policy_version: str,
    structure_tree_hash: str,
    body_units_hash: str,
    object_units_hash: str,
) -> str:
    """Retrieval identity = hash(OCR identity + policy + produced-unit digests).

    The exact composition (structure/body/object digests) is the current
    implementation, not a frozen formula (#162).
    """
    raw = _canonical_json(
        {
            "ocr_result_hash": ocr_result_hash,
            "retrieval_policy_version": retrieval_policy_version,
            "structure_tree_hash": structure_tree_hash,
            "body_units_hash": body_units_hash,
            "object_units_hash": object_units_hash,
        }
    )
    return hashlib.sha256(raw).hexdigest()


def compute_embedding_identity(
    *, endpoint: str, model: str, dimension: int
) -> str:
    """Canonical semantic identity of the embedding substrate.

    provider + model + dimension, plus the endpoint because it is
    semantically identity-bearing for this provider.  A dimension change
    (1536 → 3072) necessarily changes the identity (#162 acceptance).
    """
    raw = _canonical_json(
        {
            "provider": EMBEDDING_PROVIDER,
            "endpoint": (endpoint or "").rstrip("/"),
            "model": model,
            "dimension": int(dimension),
        }
    )
    return hashlib.sha256(raw).hexdigest()


def compute_vector_identity(
    *, retrieval_identity: str, embedding_identity: str
) -> str:
    """Vector identity = sha256(retrieval identity + embedding identity)."""
    raw = _canonical_json(
        {
            "retrieval_identity": retrieval_identity,
            "embedding_identity": embedding_identity,
        }
    )
    return hashlib.sha256(raw).hexdigest()


def retrieval_identity_from_manifest(manifest: dict[str, Any]) -> str | None:
    """Recompute the retrieval identity from a manifest's own recorded fields.

    Returns None when the manifest lacks a required field (legacy manifest).
    """
    try:
        return compute_retrieval_identity(
            ocr_result_hash=manifest["ocr_result_hash"],
            retrieval_policy_version=manifest["retrieval_policy_version"],
            structure_tree_hash=manifest["structure_tree_hash"],
            body_units_hash=manifest["body_units_hash"],
            object_units_hash=manifest["object_units_hash"],
        )
    except (KeyError, TypeError):
        return None


# ── vector lineage write (atomic with the publish swap) ───────────────────

def write_vector_lineage(
    conn: sqlite3.Connection,
    vault: Path,
    *,
    endpoint: str,
    model: str,
    dimension: int,
    updated_at: str | None = None,
    paper_ids: set[str] | None = None,
) -> int:
    """Write one lineage row per embedded paper into ``conn`` (candidate or
    live).  Rows commit atomically with the shadow publish: the caller seals
    the candidate AFTER this call, so the swapped-in live DB already carries
    the lineage.

    A paper is eligible when it has vector rows in this connection AND its
    manifest carries a retrieval identity; papers with vectors but no
    identity (legacy manifests) get NO row — the probe reports them
    ``unknown``, never ``stale``.

    Returns the number of rows written.  ``paper_ids`` restricts the write
    to exactly those papers (T4: resume-skipped papers keep their rows
    byte-identical); None = every paper with vectors (T1 behavior).
    """
    if not dimension:
        # Dimension unknown (e.g. a mocked/detection-less build) — the
        # identity cannot be computed; nothing is written.
        return 0
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='lineage'"
    ).fetchone():
        conn.execute(LINEAGE_TABLE)
    embedding_identity = compute_embedding_identity(
        endpoint=endpoint, model=model, dimension=dimension
    )
    stamp = updated_at or datetime.now(timezone.utc).isoformat()

    # #165 corrective: the parameter must not be shadowed — the filter is
    # applied to the eligible set derived from the connection.
    eligible_paper_ids = _papers_with_vectors(conn)
    if paper_ids is not None:
        eligible_paper_ids = [p for p in eligible_paper_ids if p in paper_ids]
    written = 0
    for paper_id in eligible_paper_ids:
        row = conn.execute(
            "SELECT value FROM meta WHERE key = ?", (f"manifest:{paper_id}",)
        ).fetchone()
        if not row:
            continue
        try:
            manifest = json.loads(row[0])
        except (TypeError, ValueError):
            continue
        retrieval_identity = manifest.get("retrieval_identity")
        if not retrieval_identity:
            # Legacy manifest — unknown lineage, no row.
            continue
        identity = compute_vector_identity(
            retrieval_identity=retrieval_identity,
            embedding_identity=embedding_identity,
        )
        conn.execute(
            "INSERT OR REPLACE INTO lineage "
            "(paper_id, layer, identity, derived_from, embedding_identity, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                paper_id,
                LINEAGE_LAYER_VECTOR,
                identity,
                retrieval_identity,
                embedding_identity,
                stamp,
            ),
        )
        written += 1
    return written


def write_legacy_fulltext_lineage(
    conn: sqlite3.Connection,
    vault: Path,
    *,
    endpoint: str,
    model: str,
    dimension: int,
    updated_at: str | None = None,
    paper_ids: set[str] | None = None,
) -> int:
    """Write lineage rows for vectors migrated from the legacy ChromaDB
    full-text collection (1.5.x-era products without structure trees).

    The embedding_identity uses the CURRENT config's endpoint/model with the
    MIGRATED vectors' dimension — so the probe's identity comparison answers
    the real compatibility question: the migrated vectors are searchable
    exactly when the embedding config is unchanged (same model → same
    dimension → same semantic space → the query encodes into the same
    space).  A config change flips the identity → stale → rebuild.

    Papers that already carry a REAL lineage row (never downgrade a proper
    chain) are skipped.  Returns rows written.
    """
    if not dimension:
        return 0
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='lineage'"
    ).fetchone():
        conn.execute(LINEAGE_TABLE)
    embedding_identity = compute_embedding_identity(
        endpoint=endpoint, model=model, dimension=dimension
    )
    stamp = updated_at or datetime.now(timezone.utc).isoformat()
    try:
        candidates = [r[0] for r in conn.execute(
            "SELECT DISTINCT paper_id FROM vec_fulltext_meta"
        ).fetchall()]
    except sqlite3.OperationalError:
        return 0
    if paper_ids is not None:
        candidates = [p for p in candidates if p in paper_ids]
    written = 0
    for paper_id in candidates:
        row = conn.execute(
            "SELECT 1 FROM lineage WHERE paper_id = ? AND layer = ?",
            (paper_id, LINEAGE_LAYER_VECTOR),
        ).fetchone()
        if row:
            continue  # a real chain exists — never downgrade it
        identity = compute_vector_identity(
            retrieval_identity=LEGACY_FULLTEXT_RETRIEVAL_ID,
            embedding_identity=embedding_identity,
        )
        conn.execute(
            "INSERT OR REPLACE INTO lineage "
            "(paper_id, layer, identity, derived_from, embedding_identity, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                paper_id,
                LINEAGE_LAYER_VECTOR,
                identity,
                LEGACY_FULLTEXT_RETRIEVAL_ID,
                embedding_identity,
                stamp,
            ),
        )
        written += 1
    return written


def _papers_with_vectors(conn: sqlite3.Connection) -> list[str]:
    """Distinct paper ids that have at least one vector row in this DB.

    Missing vec tables (no vectors built yet) yield an empty list — the
    lineage write is a no-op, never an error."""
    try:
        rows = conn.execute(
            "SELECT paper_id FROM vec_fulltext_meta "
            "UNION SELECT paper_id FROM vec_body_meta "
            "UNION SELECT paper_id FROM vec_objects_meta"
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [r[0] for r in rows]


# ── probe read model ──────────────────────────────────────────────────────

def probe_lineage(vault: Path) -> dict[str, Any]:
    """Per-paper {ocr, retrieval, vector} lineage states.

    Fails closed: no memory DB → an ``unknown`` envelope response (never an
    exception); missing/legacy identities report ``unknown``, never ``stale``.
    """
    from paperforge.config import paperforge_paths

    paths = paperforge_paths(vault)
    db_path = paths["paperforge"] / "indexes" / "paperforge.db"
    ocr_root = paths.get("ocr")

    if not db_path.exists():
        return {
            "schema_version": 2,
            "module": "lineage",
            "capability_state": "unknown",
            "reason": {
                "code": "lineage.db_missing",
                "text": "Memory database not found — lineage is unobservable",
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "papers": {},
        }

    keys = _paper_keys(vault, db_path)
    papers: dict[str, dict[str, str]] = {}
    identities: dict[str, dict[str, str | None]] = {}
    summary = {"current": 0, "stale": 0, "missing": 0, "unknown": 0}

    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row  # P1-D: dict(row) must work for integrity judging
    try:
        has_lineage_table = (
            conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='lineage'"
            ).fetchone()
            is not None
        )
        embedding_identity = _current_embedding_identity(conn, vault)
        for key in keys:
            # #162 corrective: each layer observes (state, identity) so the
            # NEXT layer can detect a freshly published upstream identity —
            # enum-only propagation misses the normal publish transitions.
            _ocr_dir = (ocr_root / key) if ocr_root is not None else None
            _canonical_pdf = _resolve_canonical_pdf(vault, _ocr_dir)
            ocr_state, ocr_identity = _probe_ocr_state(
                _ocr_dir, canonical_pdf=_canonical_pdf
            )
            retrieval_state, retrieval_identity = _probe_retrieval_state(
                conn, key, ocr_state, ocr_identity
            )
            vector_state = _probe_vector_state(
                conn,
                key,
                retrieval_state,
                retrieval_identity,
                embedding_identity,
                has_lineage_table,
            )
            state = {
                "ocr": ocr_state,
                "retrieval": retrieval_state,
                "vector": vector_state,
                # Fine-grained WHY for each layer — the state machine keeps
                # the detail so next-step decisions and UI can distinguish
                # not_started / ran_but_empty / tree_missing / tree_empty.
                "details": {
                    "ocr": _ocr_detail(_ocr_dir, canonical_pdf=_canonical_pdf),
                    "retrieval": (
                        "manifest_missing"
                        if retrieval_state in ("missing", "incomplete")
                        and ocr_state == "current"
                        else None
                    ),
                    "vector": None,
                },
                # P1-D: orthogonal facts per carrier — snapshot integrity,
                # policy currency, lineage trust (ADR-0002 §6).  A verified
                # old snapshot is NOT corrupt.
                "integrity": _retrieval_integrity_facts(
                    conn, key, retrieval_state, ocr_state, retrieval_identity
                ),
                # Flags are non-failure facts (ADR-0002): a pipeline version
                # difference is not a materialization defect.
                "flags": {
                    "version_old": bool(
                        _ocr_version_old((ocr_root / key) if ocr_root is not None else None)
                    ),
                },
            }
            papers[key] = state
            for layer_state in (ocr_state, retrieval_state, vector_state):
                summary[layer_state] = summary.get(layer_state, 0) + 1
            # Internal digest material for reconcile's W2 gate (#166): the
            # identities that DROVE each facet state, so a stale caused by
            # R1 is distinguishable from one caused by R2.  Sibling of
            # ``papers`` (public read model schema untouched).
            identities[key] = {
                "ocr": ocr_identity,
                "retrieval": retrieval_identity,
                "vector": (
                    conn.execute(
                        "SELECT identity FROM lineage "
                        "WHERE paper_id = ? AND layer = ?",
                        (key, LINEAGE_LAYER_VECTOR),
                    ).fetchone() or (None,)
                )[0],
            }
        _orphan = _detect_orphans(vault)
        _residuals = _detect_residuals(vault)
    finally:
        conn.close()

    return {
        "schema_version": 2,
        "module": "lineage",
        "capability_state": "ok",
        "reason": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "papers": papers,
        "identities": identities,
        "summary": summary,
        # Library-level residual state — a paper absent from Zotero but
        # present in ANY carrier (workspace / full-text index / vectors /
        # OCR).  Part of the SAME state machine: reconcile turns it into a
        # single library.prune intent (one pass clears every carrier) and
        # the frontend pops the modal once (0→N) showing what is left.
        "residuals": _residuals,
        # Legacy workspace-only view, kept for compatibility.
        "orphan": _orphan,
    }


def _detect_orphans(vault: Path) -> dict[str, Any]:
    """Legacy workspace-orphan view — kept for compatibility.

    Returns the workspace-carrier subset of the unified residual report
    (papers with a workspace directory but absent from Zotero)."""
    res = _detect_residuals(vault)
    ws = [p for p in res["papers"] if p["workspace"]]
    return {
        "count": len(ws),
        "keys": [p["key"] for p in ws],
        "orphans": [{"key": p["key"], "title": p["title"]} for p in ws],
    }


def _detect_residuals(vault: Path) -> dict[str, Any]:
    """Unified residual detection — **Zotero is the authority**.

    A paper is residual when its key is ABSENT from Zotero but PRESENT in
    ANY carrier: workspace directory, papers table (full-text index),
    vector meta (vec_body/vec_objects/vec_fulltext), or OCR data.  Carriers
    are probed independently, so a removed paper is found even when its
    workspace directory is already gone (pure FTS/vector residuals).  The
    report is paper-level: one entry per residual paper with per-carrier
    flags — the frontend modal shows what is left, reconcile emits a single
    library.prune, and the prune clears every carrier in one pass.

    Safety (fail-closed, never a false deletion):
    - Zotero key set comes from the LIVE exports; when exports are
      unreadable we fall back to the sync-CONFIRMED missing keys (the
      orphan state file) and only inspect those — a paper we cannot prove
      is absent from Zotero is NEVER reported residual.
    - No authoritative baseline at all → report nothing.
    """
    ws_keys = _workspace_paper_keys(vault)
    db_keys = _db_paper_keys(vault)
    vec_keys = _vec_paper_keys(vault)
    ocr_keys = _ocr_paper_keys(vault)
    carrier_union = ws_keys | db_keys | vec_keys | ocr_keys

    zotero_keys = _zotero_keys_from_exports(vault)
    if zotero_keys:
        candidates = sorted(carrier_union - zotero_keys)
    else:
        confirmed_missing = _confirmed_missing_keys(vault)
        if not confirmed_missing:
            return {"count": 0, "keys": [], "papers": []}
        # Fail-closed: only keys Zotero is CONFIRMED not to have.
        candidates = sorted(carrier_union & confirmed_missing)

    papers = [
        {
            "key": k,
            "title": _residual_title(vault, k),
            "workspace": k in ws_keys,
            "fts": k in db_keys,
            "vectors": k in vec_keys,
            "ocr": k in ocr_keys,
        }
        for k in candidates
    ]
    return {
        "count": len(papers),
        "keys": [p["key"] for p in papers],
        "papers": papers,
    }


def _zotero_keys_from_exports(vault: Path) -> set[str]:
    """Authoritative Zotero key set — read from the LIVE BBT exports.

    Never derives from the index snapshot (a freshly added Zotero paper not
    yet synced would be falsely residual)."""
    try:
        from paperforge.config import paperforge_paths
        from paperforge.worker.sync import load_export_rows

        paths = paperforge_paths(vault)
        keys: set[str] = set()
        exports_dir = paths.get("exports")
        if exports_dir and exports_dir.exists():
            for export_path in sorted(exports_dir.glob("*.json")):
                for row in load_export_rows(export_path):
                    if row.get("key"):
                        keys.add(row["key"])
        return keys
    except Exception:  # noqa: BLE001 — unreadable exports = no authority
        return set()


def _confirmed_missing_keys(vault: Path) -> set[str]:
    """Keys Zotero is CONFIRMED not to have (sync's orphan state file)."""
    try:
        from paperforge.config import paperforge_paths

        paths = paperforge_paths(vault)
        state_path = paths.get("paperforge") / "indexes" / "sync-orphan-state.json"
        if state_path.exists():
            import json as _json

            data = _json.loads(state_path.read_text(encoding="utf-8"))
            return {
                o.get("key", "") for o in (data.get("orphans", []) or []) if o.get("key")
            }
    except Exception:  # noqa: BLE001
        pass
    return set()


def _workspace_paper_keys(vault: Path) -> set[str]:
    """Keys of workspace paper directories (all, not just orphans)."""
    try:
        from paperforge.config import paperforge_paths

        paths = paperforge_paths(vault)
        lit_dir = paths.get("literature")
        if not lit_dir or not lit_dir.exists():
            return set()
        keys: set[str] = set()
        for domain_dir in lit_dir.iterdir():
            if not domain_dir.is_dir():
                continue
            for entry in domain_dir.iterdir():
                if entry.is_dir() and " - " in entry.name:
                    keys.add(entry.name.split(" - ", 1)[0].strip())
        return keys
    except Exception:  # noqa: BLE001
        return set()


def _workspace_dir_for_key(vault: Path, key: str) -> Path | None:
    """Resolve a paper's workspace directory (Literature/<domain>/<key> - ...)
    for a key, or None when it does not exist.  Used by library.prune so a
    residual's workspace carrier is trashed with its real path — passing
    Path() would trip the fail-closed empty-path guard and silently skip
    every workspace delete."""
    try:
        from paperforge.config import paperforge_paths

        paths = paperforge_paths(vault)
        lit_dir = paths.get("literature")
        if not lit_dir or not lit_dir.exists():
            return None
        for domain_dir in lit_dir.iterdir():
            if not domain_dir.is_dir():
                continue
            for entry in domain_dir.iterdir():
                if entry.is_dir() and entry.name.startswith(key + " - "):
                    return entry
    except Exception:  # noqa: BLE001
        pass
    return None


def _db_paper_keys(vault: Path) -> set[str]:
    try:
        from paperforge.memory.db import get_memory_db_path, open_live_reader

        db_path = get_memory_db_path(vault)
        if not db_path.exists():
            return set()
        with open_live_reader(vault, db_path) as conn:
            rows = conn.execute("SELECT zotero_key FROM papers").fetchall()
            return {r["zotero_key"] for r in rows}
    except Exception:  # noqa: BLE001
        return set()


def _vec_paper_keys(vault: Path) -> set[str]:
    try:
        from paperforge.memory.db import get_memory_db_path, open_live_reader

        db_path = get_memory_db_path(vault)
        if not db_path.exists():
            return set()
        with open_live_reader(vault, db_path) as conn:
            keys: set[str] = set()
            for table in ("vec_body_meta", "vec_objects_meta", "vec_fulltext_meta"):
                try:
                    rows = conn.execute(
                        f"SELECT DISTINCT paper_id FROM {table}"
                    ).fetchall()
                    keys.update(r["paper_id"] for r in rows)
                except Exception:  # noqa: BLE001
                    continue
            return keys
    except Exception:  # noqa: BLE001
        return set()


def _ocr_paper_keys(vault: Path) -> set[str]:
    try:
        from paperforge.config import paperforge_paths

        paths = paperforge_paths(vault)
        ocr_dir = paths.get("ocr")
        if not ocr_dir or not ocr_dir.exists():
            return set()
        return {d.name for d in ocr_dir.iterdir() if d.is_dir()}
    except Exception:  # noqa: BLE001
        return set()


def _residual_title(vault: Path, key: str) -> str:
    try:
        from paperforge.memory.db import get_memory_db_path, open_live_reader

        db_path = get_memory_db_path(vault)
        if db_path.exists():
            with open_live_reader(vault, db_path) as conn:
                row = conn.execute(
                    "SELECT title FROM papers WHERE zotero_key = ?", (key,)
                ).fetchone()
                if row and row["title"]:
                    return str(row["title"])
    except Exception:  # noqa: BLE001
        pass
    try:
        from paperforge.config import paperforge_paths

        paths = paperforge_paths(vault)
        lit_dir = paths.get("literature")
        if lit_dir and lit_dir.exists():
            for domain_dir in lit_dir.iterdir():
                if not domain_dir.is_dir():
                    continue
                for entry in domain_dir.iterdir():
                    if entry.is_dir() and entry.name.startswith(key + " - "):
                        return entry.name.split(" - ", 1)[1].strip()
    except Exception:  # noqa: BLE001
        pass
    return ""


def _paper_keys(vault: Path, db_path: Path) -> list[str]:
    """Paper universe: the canonical library index; falls back to the union
    of memory manifests and OCR dirs when the index is unavailable."""
    from paperforge.worker.asset_index import read_index

    try:
        index = read_index(vault)
        items = index.get("items") if isinstance(index, dict) else index
        keys = [
            it.get("zotero_key", "")
            for it in items or []
            if it.get("zotero_key")
        ]
        if keys:
            return sorted(set(keys))
    except Exception:
        pass
    keys: set[str] = set()
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        for (key,) in conn.execute(
            "SELECT key FROM meta WHERE key LIKE 'manifest:%'"
        ).fetchall():
            keys.add(key.removeprefix("manifest:"))
    finally:
        conn.close()
    # OCR-only papers (memory not built yet) are part of the universe too.
    from paperforge.config import paperforge_paths

    ocr_root = paperforge_paths(vault).get("ocr")
    if ocr_root is not None and ocr_root.exists():
        for child in ocr_root.iterdir():
            if child.is_dir():
                keys.add(child.name)
    return sorted(keys)


# ── OCR state semantics — delegated to the materialization contract ──────
# The judging functions live in paperforge/materialization/ocr.py (ADR-0002
# unified DAG).  This module keeps thin wrappers so per-paper assembly and
# the tests keep working; the hash-identity step (current vs stale) stays
# here because it depends on compute_ocr_result_hash.

def _probe_ocr_state(
    paper_dir: Path | None, canonical_pdf: Path | None = None
) -> tuple[str, str | None]:
    """(state, ocr_identity) — current | stale | missing | unknown |
    incomplete | failed.

    State judging delegates to materialization.ocr.top_state; provenance
    ([2]) is checked when the chain is materialized; the hash identity
    (current vs stale) is computed here."""
    from paperforge.materialization.ocr import (
        PROVENANCE_UNKNOWN,
        provenance_state,
        top_state,
    )

    state = top_state(paper_dir)
    if state is not None:
        return state, None
    if paper_dir is None:
        return "missing", None
    prov = provenance_state(paper_dir, canonical_pdf)
    if prov is not None:
        if prov == PROVENANCE_UNKNOWN:
            return "unknown", None
        return "stale", None
    # [5] published identity vs recomputed — judged by materialization.
    from paperforge.materialization.ocr import identity_state

    istate, ihash = identity_state(paper_dir)
    if istate is None:
        return "unknown", None
    return istate, ihash


def _ocr_detail(paper_dir: Path | None, canonical_pdf: Path | None = None) -> str | None:
    """Fine-grained WHY for the ocr state — one namespace, each value one
    meaning (see materialization/ocr.py constants)."""
    from paperforge.materialization.ocr import detail

    return detail(paper_dir, canonical_pdf)


def _ocr_version_old(paper_dir: Path | None) -> bool:
    """Non-failure flag: the paper was produced by an older OCR pipeline
    version than current.  Not a materialization defect (ADR-0002)."""
    if paper_dir is None:
        return False
    from paperforge.materialization.ocr import is_old_pipeline

    return is_old_pipeline(paper_dir)


def _resolve_canonical_pdf(vault: Path, paper_dir: Path | None) -> Path | None:
    """Resolve the CANONICAL main PDF for provenance checking ([2b]).

    Authority = the current canonical library (formal-library.json main
    pdf_path) — NEVER meta.source_pdf, which is only a HISTORICAL locator
    and cannot prove the OCR's own claim (P0-B corrective: verifying OCR
    with OCR's own meta is fail-open).  The path is a LOCATOR; identity is
    the fingerprint bytes (ADR-0002 §5 #1)."""
    if paper_dir is None:
        return None
    key = paper_dir.name
    try:
        import re as _re

        from paperforge.worker.asset_index import read_index

        envelope = read_index(vault)
        items = envelope.get("items") if isinstance(envelope, dict) else (envelope or [])
        hit = next((i for i in items or [] if i.get("zotero_key") == key), None)
        if not hit:
            return None
        pdf = str(hit.get("pdf_path", "") or "")
        if not pdf:
            return None
        m = _re.match(r"\[\[([^\]]+)\]\]", pdf)
        rel = m.group(1) if m else pdf
        candidate = Path(rel)
        if candidate.is_absolute():
            return candidate if candidate.exists() else None
        resolved = vault / candidate
        return resolved if resolved.exists() else None
    except Exception:  # noqa: BLE001 — unreadable index → no evidence
        return None


def _retrieval_integrity_facts(
    conn: sqlite3.Connection,
    key: str,
    retrieval_state: str,
    ocr_state: str,
    retrieval_identity: str | None = None,
) -> dict[str, str]:
    """P1-D orthogonal retrieval facts: snapshot integrity, policy
    currency, lineage trust — independent of the flat current/stale state.

    Queries the DB per paper (counts + rows, cheap at paper scale) and
    judges via materialization/retrieval.py."""
    from paperforge.materialization.retrieval import (
        lineage_trust,
        policy_currency,
        snapshot_integrity,
    )

    facts: dict[str, str] = {
        "snapshot_integrity": "unknown",
        "policy_currency": "unknown",
        "lineage_trust": "unverified",
    }
    if ocr_state not in ("current",):
        return facts  # upstream not current — integrity of an old carrier
        # is still worth reporting, but the caller gates on OCR currency.
    row = conn.execute(
        "SELECT value FROM meta WHERE key = ?", (f"manifest:{key}",)
    ).fetchone()
    manifest = None
    if row:
        try:
            manifest = json.loads(row[0])
        except (TypeError, ValueError):
            manifest = None
    try:
        body_units = [
            dict(r) for r in conn.execute(
                "SELECT * FROM body_units WHERE paper_id = ?", (key,)
            )
        ]
        object_units = [
            dict(r) for r in conn.execute(
                "SELECT * FROM object_units WHERE paper_id = ?", (key,)
            )
        ]
        body_count = len(body_units)
        object_count = len(object_units)
    except Exception:  # noqa: BLE001
        body_units = None
        object_units = None
        body_count = object_count = -1
    facts["snapshot_integrity"] = snapshot_integrity(
        manifest, body_units, object_units,
        body_count=body_count, object_count=object_count,
    )
    facts["policy_currency"] = policy_currency(manifest)
    facts["lineage_trust"] = lineage_trust(manifest, retrieval_identity)
    return facts


def _probe_retrieval_state(
    conn: sqlite3.Connection,
    key: str,
    ocr_state: str,
    current_ocr_identity: str | None,
) -> tuple[str, str | None]:
    """(state, current_retrieval_identity) — current | stale | missing | unknown.

    The manifest is current only when ALL of:
      - it embeds the CURRENT published OCR identity (a normal OCR publish
        makes the old retrieval stale, #162 corrective P0-1);
      - it was built under the CURRENT retrieval policy (a policy bump is a
        global desired-state change, #159 §2.1);
      - its stored identity equals its own recomputed identity.
    """
    if ocr_state == "missing":
        return "missing", None
    if ocr_state == "incomplete":
        # Structure tree absent/empty → the derived materialization cannot
        # exist; report incomplete (distinct from quality), never stale.
        return "incomplete", None
    if ocr_state == "unknown":
        return "unknown", None
    if ocr_state == "stale":
        # Artifacts changed since the last publish — the published identity
        # is no longer materialized; the retrieval built on it is stale too.
        return "stale", None
    row = conn.execute(
        "SELECT value FROM meta WHERE key = ?", (f"manifest:{key}",)
    ).fetchone()
    if not row:
        return "missing", None
    try:
        manifest = json.loads(row[0])
    except (TypeError, ValueError):
        return "unknown", None
    stored = manifest.get("retrieval_identity")
    recomputed = retrieval_identity_from_manifest(manifest)
    if not stored or not recomputed:
        # Legacy manifest without a retrieval identity → unknown, never stale.
        return "unknown", None
    if manifest.get("ocr_result_hash") != current_ocr_identity:
        # Fresh OCR identity published since this manifest was built.
        return "stale", None
    from paperforge.retrieval.manifest import RETRIEVAL_POLICY_VERSION

    if manifest.get("retrieval_policy_version") != RETRIEVAL_POLICY_VERSION:
        # Global retrieval policy moved; this manifest predates it.
        # Carry the manifest's own recomputed identity as the CAUSE
        # fingerprint: a stale caused by R1 vs one caused by R2 must be
        # distinguishable in reconcile's W2 digest material (#166).
        return "stale", recomputed
    if stored != recomputed:
        return "stale", None
    return "current", recomputed


def _vec_dimension_from_ddl(conn: sqlite3.Connection) -> int | None:
    """Vector dimension from the vec0 table's own DDL — the substrate's
    self-declaration, authoritative and never external.  Reads any vec
    table; they all share the dimension."""
    try:
        row = conn.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type = 'table' AND name = 'vec_body'"
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    if not row or not row[0]:
        return None
    m = re.search(r"float\[(\d+)\]", row[0])
    return int(m.group(1)) if m else None


def _current_embedding_identity(
    conn: sqlite3.Connection, vault: Path
) -> str | None:
    """The embedding identity the live substrate currently serves, from
    config (endpoint/model) + the substrate's declared dimension.

    DAG principle: the dimension comes from the vec0 DDL (the artifact's own
    declaration), not from build_state — external keys must never gate the
    identity chain.  build_state.vector_dimension is a legacy fallback only.
    None when unobservable."""
    from paperforge.embedding._config import (
        get_api_model,
        get_effective_api_base_url,
    )

    endpoint = get_effective_api_base_url(vault)
    model = get_api_model(vault)
    dimension = _vec_dimension_from_ddl(conn)
    if not dimension:
        # Legacy fallback: published build state still carries the dim.
        row = conn.execute(
            "SELECT value FROM build_state WHERE key = 'vector_dimension'"
        ).fetchone()
        if row:
            with contextlib.suppress(TypeError, ValueError):
                dimension = json.loads(row[0])
    if not dimension:
        return None
    return compute_embedding_identity(
        endpoint=endpoint, model=model, dimension=int(dimension)
    )


def _probe_vector_state(
    conn: sqlite3.Connection,
    key: str,
    retrieval_state: str,
    current_retrieval_identity: str | None,
    embedding_identity: str | None,
    has_lineage_table: bool,
) -> str:
    """Vector: current | stale | missing | unknown."""
    try:
        has_vectors = (
            conn.execute(
                "SELECT 1 FROM vec_fulltext_meta WHERE paper_id = ? "
                "UNION SELECT 1 FROM vec_body_meta WHERE paper_id = ? "
                "UNION SELECT 1 FROM vec_objects_meta WHERE paper_id = ? "
                "LIMIT 1",
                (key, key, key),
            ).fetchone()
            is not None
        )
    except sqlite3.OperationalError:
        # No vec tables yet (DB exists, vectors never built) → missing.
        return "missing"
    if not has_vectors:
        return "missing"
    if not has_lineage_table:
        return "unknown"
    if retrieval_state == "incomplete":
        # The paper is an incomplete OCR product (missing/empty structure
        # tree): any vectors that exist are part of that incomplete
        # materialization — report incomplete, regardless of a lineage row.
        return "incomplete"
    row = conn.execute(
        "SELECT identity, derived_from, embedding_identity FROM lineage "
        "WHERE paper_id = ? AND layer = ?",
        (key, LINEAGE_LAYER_VECTOR),
    ).fetchone()
    if not row:
        # Vectors exist but no lineage row (legacy build) → unknown.
        return "unknown"
    stored_identity, derived_from, stored_embedding = row
    if derived_from == LEGACY_FULLTEXT_RETRIEVAL_ID:
        # Legacy full-text vectors (migrated ChromaDB, 1.5.x-era products):
        # no manifest/retrieval layer by design.  The ONLY compatibility
        # question is the embedding config: identity match means the query
        # model still matches the stored vectors (searchable, gate passes);
        # mismatch means model/config changed → stale (rebuild required —
        # a query under the new config would dimension-mismatch anyway).
        if not embedding_identity:
            return "unknown"
        if stored_embedding != embedding_identity:
            return "stale"
        return "current"
    if retrieval_state == "incomplete":
        # Derived layers cannot exist without a structure tree — the paper
        # is an incomplete OCR product; vectors (if any) are not structural.
        return "incomplete"
    if retrieval_state != "current":
        return "unknown" if retrieval_state == "unknown" else "stale"
    if not embedding_identity or not current_retrieval_identity:
        return "unknown"
    if derived_from != current_retrieval_identity:
        # A NEW retrieval identity was published since these vectors were
        # built (memory.build) — the old vectors are stale (#162 P0-2).
        return "stale"
    if stored_embedding != embedding_identity:
        # Substrate identity changed (model/endpoint/dimension) since build.
        return "stale"
    expected = compute_vector_identity(
        retrieval_identity=current_retrieval_identity,
        embedding_identity=embedding_identity,
    )
    if stored_identity != expected:
        return "stale"
    return "current"
