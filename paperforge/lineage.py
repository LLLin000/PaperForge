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
import re
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

def _ocr_detail(paper_dir: Path | None) -> str | None:
    """Fine-grained reason behind a paper's ocr state — the state machine
    captures WHY, not just WHAT, so the next-step decision and the UI can
    distinguish every distinct meaning:

    - not_started      OCR never ran (meta pending / no artifacts)
    - queued           OCR queued or in flight (meta processing/running)
    - failed           OCR run failed (meta ocr_status=failed)
    - no_pdf           No PDF source — OCR cannot run at all
    - ran_but_empty    OCR ran but produced zero blocks
    - tree_missing     OCR done, structure tree file absent
    - tree_empty       OCR done, structure tree has no nodes
    - version_old      Produced by an older OCR pipeline version
    - None             complete and current
    """
    if paper_dir is None or not paper_dir.exists():
        return "not_started"
    meta = _read_ocr_meta(paper_dir)
    meta_status = str(meta.get("ocr_status", "") or "") if meta else ""
    if meta_status == "failed":
        return "failed"
    if meta_status == "pending":
        return "not_started"
    if meta_status in ("processing", "running", "queued"):
        return "queued"
    if meta_status == "nopdf":
        return "no_pdf"
    blocks = paper_dir / "structure" / "blocks.structured.jsonl"
    if not blocks.exists():
        return "not_started"
    try:
        if blocks.stat().st_size == 0:
            return "ran_but_empty"
    except OSError:
        return "unreadable"
    if _is_structure_tree_incomplete(paper_dir):
        if not (paper_dir / "index" / "structure-tree.json").exists():
            return "tree_missing"
        return "tree_empty"
    if _is_old_pipeline(paper_dir):
        return "version_old"
    return None


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
                # Fine-grained WHY for each layer — the state machine keeps
                # the detail so next-step decisions and UI can distinguish
                # not_started / ran_but_empty / tree_missing / tree_empty.
                "details": {
                    "ocr": _ocr_detail(
                        (ocr_root / key) if ocr_root is not None else None
                    ),
                    "retrieval": (
                        "manifest_missing"
                        if retrieval_state in ("missing", "incomplete")
                        and ocr_state == "current"
                        else None
                    ),
                    "vector": None,
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


def _read_ocr_meta(paper_dir: Path) -> dict | None:
    """Read meta.json (the OCR lifecycle authority) defensively."""
    try:
        import json as _json

        return _json.loads((paper_dir / "meta.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _is_old_pipeline(paper_dir: Path) -> bool:
    """True when the paper was produced by an older OCR pipeline version
    than the current one — the product may be structurally fine (current)
    or incomplete, but the version fact is part of the state machine."""
    try:
        from paperforge.worker.ocr_versions import OCR_PIPELINE_VERSION
    except Exception:  # noqa: BLE001
        return False
    meta = _read_ocr_meta(paper_dir)
    if not meta:
        return False
    v = str(meta.get("ocr_pipeline_version", "") or "")
    return bool(v) and v != OCR_PIPELINE_VERSION


def _is_structure_tree_incomplete(paper_dir: Path) -> bool:
    """OCR completed but the structure tree is missing, unreadable, or EMPTY
    (``nodes: []``).  Without a tree the derived layers (body units,
    structural coordinates) cannot be built — the paper has NO searchable
    structure.

    This is an INCOMPLETE OCR product, semantically distinct from a QUALITY
    problem: the fix is a derived rebuild (`ocr rebuild`), not a quality
    re-run, and the state must never masquerade as ``current``.
    """
    tree_path = paper_dir / "index" / "structure-tree.json"
    if not tree_path.exists():
        return True
    try:
        import json as _json

        tree = _json.loads(tree_path.read_text(encoding="utf-8"))
        nodes = tree.get("nodes", []) if isinstance(tree, dict) else []
        return not nodes
    except Exception:  # noqa: BLE001 — unreadable tree = incomplete, never current
        return True


def _probe_ocr_state(paper_dir: Path | None) -> tuple[str, str | None]:
    """(state, ocr_identity) — current | stale | missing | unknown | incomplete.

    DAG principle: the OCR *artifacts* are the authority for the identity;
    ``result-hash.txt`` is a publish snapshot (cache) used only as a cheap
    stale detector.  A missing snapshot degrades to recomputing from the
    artifacts — never ``unknown`` while the artifacts are intact.  The
    caller (_probe_retrieval_state) cross-checks the recomputed identity
    against the manifest's recorded ``ocr_result_hash`` edge.

    ``incomplete``: artifacts exist but the structure tree is missing or
    empty — the OCR ran but its derived structure was never produced (or is
    unbuildable from the source content).  This is NOT a quality problem;
    it is an incomplete product and is reported distinctly.
    """
    if paper_dir is None or not paper_dir.exists():
        return "missing", None
    # meta.json is the OCR LIFECYCLE authority — it distinguishes "never
    # ran" (pending), "running" (queued), "failed", "no PDF" from the
    # artifact-integrity checks below.  Distinct semantics, never conflated.
    meta_status = None
    meta = _read_ocr_meta(paper_dir)
    if meta:
        meta_status = str(meta.get("ocr_status", "") or "")
    if meta_status == "failed":
        return "failed", None
    if meta_status in ("pending", "queued"):
        return "missing", None  # detail: not_started / queued
    if meta_status == "nopdf":
        return "missing", None  # detail: no_pdf — OCR cannot run
    if meta_status in ("processing", "running"):
        return "missing", None  # detail: queued (in flight)
    blocks_path = paper_dir / "structure" / "blocks.structured.jsonl"
    if not blocks_path.exists():
        return "missing", None
    if has_result_hash_pending(paper_dir):
        return "unknown", None
    # The structured blocks file exists but is EMPTY (0 bytes): the OCR run
    # never materialized any content.  That is an UNFINISHED OCR — the fix
    # is `ocr.run` (re-run OCR), NOT a derived rebuild.  Distinct from the
    # incomplete case below (blocks exist, tree does not).
    try:
        if blocks_path.stat().st_size == 0:
            return "missing", None
    except OSError:  # noqa: BLE001
        pass
    if _is_structure_tree_incomplete(paper_dir):
        return "incomplete", None
    current = compute_ocr_result_hash(paper_dir)
    if current is None:
        return "unknown", None
    hash_file = paper_dir / "index" / "result-hash.txt"
    if hash_file.exists():
        try:
            stored = hash_file.read_text(encoding="utf-8").strip()
        except OSError:
            stored = None
        if stored is not None and stored != current:
            # Artifacts changed since the snapshot was published → the
            # derived layers built on the old identity are stale.
            return "stale", stored
    return "current", current


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
