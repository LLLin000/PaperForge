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

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paperforge.worker.ocr_hash import (
    compute_ocr_result_hash,
    has_result_hash_pending,
)

# The embedding provider is the openai-compatible provider seam; its endpoint
# is semantically identity-bearing (different endpoints → different embedding
# spaces), so it participates in the canonical identity.
EMBEDDING_PROVIDER = "openai_compatible"

LINEAGE_LAYER_VECTOR = "vector"

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
) -> int:
    """Write one lineage row per embedded paper into ``conn`` (candidate or
    live).  Rows commit atomically with the shadow publish: the caller seals
    the candidate AFTER this call, so the swapped-in live DB already carries
    the lineage.

    A paper is eligible when it has vector rows in this connection AND its
    manifest carries a retrieval identity; papers with vectors but no
    identity (legacy manifests) get NO row — the probe reports them
    ``unknown``, never ``stale``.

    Returns the number of rows written.
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

    paper_ids = _papers_with_vectors(conn)
    written = 0
    for paper_id in paper_ids:
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
    summary = {"current": 0, "stale": 0, "missing": 0, "unknown": 0}

    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
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
            ocr_state, ocr_identity = _probe_ocr_state(
                (ocr_root / key) if ocr_root is not None else None
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
            }
            papers[key] = state
            for layer_state in state.values():
                summary[layer_state] = summary.get(layer_state, 0) + 1
    finally:
        conn.close()

    return {
        "schema_version": 2,
        "module": "lineage",
        "capability_state": "ok",
        "reason": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "papers": papers,
        "summary": summary,
    }


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


def _probe_ocr_state(paper_dir: Path | None) -> tuple[str, str | None]:
    """(state, published_ocr_identity) — current | stale | missing | unknown.

    Pending publication marker → unknown (#126 semantics).  Published
    result-hash equals the artifact hash → current; differs → stale.  The
    identity is the published result hash whenever readable.
    """
    if paper_dir is None or not paper_dir.exists():
        return "missing", None
    if not (paper_dir / "structure" / "blocks.structured.jsonl").exists():
        return "missing", None
    if has_result_hash_pending(paper_dir):
        return "unknown", None
    hash_file = paper_dir / "index" / "result-hash.txt"
    if not hash_file.exists():
        return "unknown", None
    try:
        stored = hash_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown", None
    current = compute_ocr_result_hash(paper_dir)
    if current is None:
        return "unknown", None
    if stored != current:
        return "stale", stored
    return "current", stored


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
        return "stale", None
    if stored != recomputed:
        return "stale", None
    return "current", recomputed


def _current_embedding_identity(
    conn: sqlite3.Connection, vault: Path
) -> str | None:
    """The embedding identity the live substrate currently serves, from
    config (endpoint/model) + the published build's dimension.  None when
    unobservable."""
    from paperforge.embedding._config import (
        get_api_model,
        get_effective_api_base_url,
    )

    endpoint = get_effective_api_base_url(vault)
    model = get_api_model(vault)
    # Build state lives in the build_state table (key/value), written by the
    # vector builder; the dimension there is the published substrate's.
    row = conn.execute(
        "SELECT value FROM build_state WHERE key = 'vector_dimension'"
    ).fetchone()
    dimension = None
    if row:
        try:
            dimension = json.loads(row[0])
        except (TypeError, ValueError):
            pass
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
    row = conn.execute(
        "SELECT identity, derived_from, embedding_identity FROM lineage "
        "WHERE paper_id = ? AND layer = ?",
        (key, LINEAGE_LAYER_VECTOR),
    ).fetchone()
    if not row:
        # Vectors exist but no lineage row (legacy build) → unknown.
        return "unknown"
    stored_identity, derived_from, stored_embedding = row
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
